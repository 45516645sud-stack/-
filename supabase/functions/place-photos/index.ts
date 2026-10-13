import { createClient } from "jsr:@supabase/supabase-js@2";
import postgres from "npm:postgres@3.4.5";
import { SCHEMA } from "./schema.ts";
import { allowedOrigin, cleanCoord, cleanQuery, cleanRadius, cleanSize, toPhotos, toPlaces, postFreshness, toPostPhotos, toPosts } from "./photos.ts";
import { authorId, checkAdmin, cleanBody, cleanCol, cleanHit, cleanItem, cleanPlaceId, cleanPopupId, cleanPopupItem, cleanPick, cleanVoteId, closedIds, HIDE_AT, voteCounts, validToken, visiblePopups, withoutHidden, withoutItem } from "./community.ts";

// 놀코 '우리 동네'의 가게 목록과 가게 사진을 찾아 주는 엔드포인트.
// 카카오 REST API 키는 비밀이라 앱 화면에 둘 수 없어서, 이 함수가 대신 카카오에 물어본다.
//   사진: GET ?q=<가게 이름 + 구>&name=<가게 이름>&size=4 → { photos: [{ thumb, link, site }] }
//         name 이 있으면 블로그·카페 글 중 가게 이름이 나오는 글의 사진만 (없으면 예전처럼 이미지 검색)
//         + { latest, recent }: 가장 최근 후기 날짜, 1년 안 후기 수 (문 닫았을 수도 표시용)
//   닫은 가게: GET ?mode=closed → { ids: [카카오 장소 id] } (2명 넘게 '문 닫았어요' 한 곳)
//              POST { mode: "place_report", id, token } → { ok }
//   가게: GET ?mode=places&q=<동네 + 놀거리>&lat=&lng=&radius=2000&size=10[&page=2]
//                                                    → { places: [{ name, category, path, address, phone, url, distance, x, y }] }
//   최근 글:   GET ?mode=posts&q=<검색어>[&page=1~3] → { posts: [{ title, text, date, url, site, thumb }] } (블로그·카페, 최근 60일, 최신순)
//   리뷰·코스: GET ?mode=docs&col=rv|uc               → { docs: [{ id, data }] }
//              POST { mode: "set", col, token, body }   → { ok, id }   (자기 문서만)
//              POST { mode: "report", col, doc, item, token } → { ok }
//   통계:       POST { mode: "hit", ev, item }               → { ok }   (날짜별 횟수만)
//   팝업:       GET ?mode=popups → { popups: [{ id, name, place, address, region, start, end, url, lat, lng }] } (승인된 것, 안 끝난 것만)
//               POST { mode: "popup_report", id, token } → { ok }   (3명이 신고하면 숨김)
//   친구 투표:  GET ?mode=vote&id=v-<10자리>&me=<작성자 id> → { counts: [후보별 표 수], voters, mine }
//               POST { mode: "vote", id, pick, token } → 같은 모양 (한 사람 한 표, 다시 고르면 바뀜)
//   관리자:     POST { mode: "admin", pass, action: "stats" | "list" | "delete" | "popups" | "popup_set" | "closed" | "closed_set", col?, doc?, item?, id?, ok?, popup? }
// 사진은 썸네일과 출처(블로그 등) 링크뿐이다. 원본 사진은 내려주지 않는다.

const KAKAO_IMAGE_SEARCH = "https://dapi.kakao.com/v2/search/image";
const KAKAO_PLACE_SEARCH = "https://dapi.kakao.com/v2/local/search/keyword.json";
const KAKAO_BLOG_SEARCH = "https://dapi.kakao.com/v2/search/blog";
const KAKAO_CAFE_SEARCH = "https://dapi.kakao.com/v2/search/cafe";
const DEFAULT_ORIGINS = "https://45516645sud-stack.github.io,http://localhost:8000";

Deno.serve(async (req) => {
  const origin = allowedOrigin(req.headers.get("Origin"), Deno.env.get("ALLOWED_ORIGINS") ?? DEFAULT_ORIGINS);
  const cors: Record<string, string> = {
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "content-type",
    Vary: "Origin",
  };
  if (origin) cors["Access-Control-Allow-Origin"] = origin;
  const json = (body: unknown, status: number, extra: Record<string, string> = {}) =>
    new Response(JSON.stringify(body), { status, headers: { ...cors, "Content-Type": "application/json", ...extra } });

  if (req.method === "OPTIONS") return new Response("ok", { headers: cors });
  if (req.method !== "GET" && req.method !== "POST") return json({ error: "GET·POST 요청만 지원합니다." }, 405);
  // 등록하지 않은 사이트에서 키를 빌려 쓰지 못하게 한다 (브라우저 요청 기준)
  if (!origin) return json({ error: "허용되지 않은 사이트입니다." }, 403);

  const url = new URL(req.url);
  if (req.method === "POST" || url.searchParams.get("mode") === "docs" || url.searchParams.get("mode") === "popups" || url.searchParams.get("mode") === "closed" || url.searchParams.get("mode") === "vote") return community(req, url, json);
  const q = cleanQuery(url.searchParams.get("q"));
  if (!q) return json({ error: "검색어는 2~60자로 보내 주세요." }, 400);
  const size = url.searchParams.get("mode") === "places"
    ? Math.min(15, Math.max(1, Math.round(Number(url.searchParams.get("size") ?? 10)) || 10))
    : cleanSize(url.searchParams.get("size"));

  const key = Deno.env.get("KAKAO_REST_API_KEY");
  if (!key) {
    console.error("KAKAO_REST_API_KEY 시크릿이 설정되지 않았습니다.");
    return json({ error: "사진 검색이 아직 설정되지 않았어요." }, 503);
  }

  // 가게 목록: 동네 가운데(또는 내 위치)에서 가까운 순
  if (url.searchParams.get("mode") === "places") {
    try {
      const api = new URL(KAKAO_PLACE_SEARCH);
      api.searchParams.set("query", q);
      api.searchParams.set("size", String(Math.min(15, Math.max(size, 1))));
      const at = cleanCoord(url.searchParams.get("lat"), url.searchParams.get("lng"));
      if (at) {
        api.searchParams.set("y", String(at.lat));
        api.searchParams.set("x", String(at.lng));
        api.searchParams.set("radius", String(cleanRadius(url.searchParams.get("radius"))));
        api.searchParams.set("sort", "distance");
      }
      const page = Math.round(Number(url.searchParams.get("page") ?? 1));
      if (page >= 2 && page <= 5) api.searchParams.set("page", String(page));
      const res = await fetch(api, { headers: { Authorization: `KakaoAK ${key}` } });
      if (!res.ok) {
        console.warn("kakao place search failed:", res.status, await res.text());
        return json({ error: "가게 목록을 가져오지 못했어요." }, 502);
      }
      const data = await res.json();
      const places = toPlaces(Array.isArray(data?.documents) ? data.documents : [], size);
      // 가게 목록은 자주 바뀌지 않으니 10분 캐시
      return json({ places }, 200, { "Cache-Control": "public, max-age=600" });
    } catch (error) {
      console.error("place search error:", error);
      return json({ error: "가게 목록을 가져오지 못했어요." }, 502);
    }
  }

  // 최근 블로그·카페 글 (팝업 소식 모으기 등): 제목·요약·날짜·링크만
  if (url.searchParams.get("mode") === "posts") {
    try {
      const page = Math.min(3, Math.max(1, Math.round(Number(url.searchParams.get("page") ?? 1)) || 1));
      const ask = async (base: string, n: number) => {
        const api = new URL(base);
        api.searchParams.set("query", q);
        api.searchParams.set("sort", "recency");
        api.searchParams.set("size", String(n));
        api.searchParams.set("page", String(page));
        const res = await fetch(api, { headers: { Authorization: `KakaoAK ${key}` } });
        if (!res.ok) { console.warn("kakao post search failed:", base, res.status); return []; }
        const data = await res.json();
        return Array.isArray(data?.documents) ? data.documents : [];
      };
      const [blog, cafe] = await Promise.all([ask(KAKAO_BLOG_SEARCH, 50), ask(KAKAO_CAFE_SEARCH, 25)]);
      return json({ posts: toPosts([...blog, ...cafe], 60) }, 200, { "Cache-Control": "public, max-age=3600" });
    } catch (error) {
      console.error("posts error:", error);
      return json({ error: "글을 가져오지 못했어요." }, 502);
    }
  }

  const name = cleanQuery(url.searchParams.get("name"));
  if (name) {
    try {
      const ask = async (base: string, n: number) => {
        const api = new URL(base);
        api.searchParams.set("query", q);
        api.searchParams.set("size", String(n));
        const res = await fetch(api, { headers: { Authorization: `KakaoAK ${key}` } });
        if (!res.ok) { console.warn("kakao post search failed:", base, res.status); return []; }
        const data = await res.json();
        return Array.isArray(data?.documents) ? data.documents : [];
      };
      const [blog, cafe] = await Promise.all([ask(KAKAO_BLOG_SEARCH, 30), ask(KAKAO_CAFE_SEARCH, 20)]);
      const docs = [...blog, ...cafe];
      const photos = toPostPhotos(docs, name, size);
      // latest·recent: 문 닫은 가게 짐작용 (가장 최근 후기 날짜, 1년 안 후기 수)
      return json({ photos, ...postFreshness(docs, name) }, 200, { "Cache-Control": "public, max-age=86400" });
    } catch (error) {
      console.error("post photos error:", error);
      return json({ error: "사진을 가져오지 못했어요." }, 502);
    }
  }

  try {
    const api = new URL(KAKAO_IMAGE_SEARCH);
    api.searchParams.set("query", q);
    api.searchParams.set("sort", "accuracy");
    api.searchParams.set("size", String(Math.min(30, size * 5))); // 걸러낼 것을 생각해 넉넉히
    const res = await fetch(api, { headers: { Authorization: `KakaoAK ${key}` } });
    if (!res.ok) {
      console.warn("kakao image search failed:", res.status, await res.text());
      return json({ error: "사진을 가져오지 못했어요." }, 502);
    }
    const data = await res.json();
    const photos = toPhotos(Array.isArray(data?.documents) ? data.documents : [], size);
    // 같은 가게는 하루 동안 다시 묻지 않게 브라우저·CDN 캐시
    return json({ photos }, 200, { "Cache-Control": "public, max-age=86400" });
  } catch (error) {
    console.error("place-photos error:", error);
    return json({ error: "사진을 가져오지 못했어요." }, 502);
  }
});

/* ---------- 리뷰·직접 만든 코스 ---------- */
type Json = (body: unknown, status: number, extra?: Record<string, string>) => Response;
// 표 모양을 따로 정의하지 않아서 느슨한 타입으로 쓴다
// deno-lint-ignore no-explicit-any
type Sb = any;
let db: Sb = null;
function database() {
  const url = Deno.env.get("SUPABASE_URL");
  // 예전 키(service_role) 또는 새 키 체계(SUPABASE_SECRET_KEYS: {"default": "sb_secret_…"})
  let key = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "";
  if (!key) {
    try { key = String(Object.values(JSON.parse(Deno.env.get("SUPABASE_SECRET_KEYS") ?? "{}"))[0] ?? ""); } catch { key = ""; }
  }
  if (!url || !key) return null;
  db ??= createClient(url, key, { auth: { persistSession: false } });
  return db;
}

async function hidden(sb: Sb, col: string): Promise<Set<string>> {
  const { data } = await sb.from("nolco_reports").select("doc_id,item_id").eq("col", col).limit(5000);
  const count = new Map<string, number>();
  for (const r of (data ?? []) as { doc_id: string; item_id: string }[]) {
    const k = `${col}/${r.doc_id}/${r.item_id}`;
    count.set(k, (count.get(k) ?? 0) + 1);
  }
  return new Set([...count].filter(([, n]) => n >= HIDE_AT).map(([k]) => k));
}

// 같은 곳에서 10분에 40번 넘게 쓰면 잠시 막는다
async function tooMany(sb: Sb, req: Request): Promise<boolean> {
  const ip = (req.headers.get("x-forwarded-for") ?? "").split(",")[0].trim() || "unknown";
  const ipHash = await authorId("ip:" + ip);
  const since = new Date(Date.now() - 10 * 60 * 1000).toISOString();
  const { count } = await sb.from("nolco_hits").select("ip", { count: "exact", head: true }).eq("ip", ipHash).gte("at", since);
  if ((count ?? 0) >= 40) return true;
  await sb.from("nolco_hits").insert({ ip: ipHash });
  if (Math.random() < 0.05) await sb.from("nolco_hits").delete().lt("at", new Date(Date.now() - 86400000).toISOString());
  return false;
}

// 표가 없으면 만든다 (함수가 켜질 때 한 번). 만든 뒤 API 가 새 표를 알도록 스키마를 다시 읽게 한다
let tablesReady: Promise<void> | null = null;
function ensureTables(): Promise<void> {
  tablesReady ??= (async () => {
    const dbUrl = Deno.env.get("SUPABASE_DB_URL");
    if (!dbUrl) return;
    const sql = postgres(dbUrl, { max: 1, prepare: false });
    try {
      const [{ n }] = await sql`select count(*)::int as n from information_schema.tables where table_schema = 'public' and table_name in ('nolco_docs', 'nolco_reports', 'nolco_hits', 'nolco_stats', 'nolco_popups')`;
      if (n < 5) {
        await sql.unsafe(SCHEMA);
        await sql.unsafe("notify pgrst, 'reload schema'");
        await new Promise((r) => setTimeout(r, 1500));
      }
    } finally {
      await sql.end();
    }
  })().catch((e) => { console.error("ensureTables:", e); tablesReady = null; });
  return tablesReady;
}

async function community(req: Request, url: URL, json: Json): Promise<Response> {
  const sb = database();
  if (!sb) return json({ error: "저장소가 아직 설정되지 않았어요." }, 503);
  await ensureTables();
  try {
    if (req.method === "GET" && url.searchParams.get("mode") === "closed") {
      const { data, error } = await sb.from("nolco_reports").select("item_id,reporter").eq("col", "pc").limit(10000);
      if (error) throw error;
      return json({ ids: closedIds(data ?? []) }, 200, { "Cache-Control": "public, max-age=300" });
    }
    if (req.method === "GET" && url.searchParams.get("mode") === "vote") {
      const id = cleanVoteId(url.searchParams.get("id"));
      if (!id) return json({ error: "투표 id 가 이상해요." }, 400);
      const me = url.searchParams.get("me") ?? "";   // 내 표 표시용: 비밀 값이 아니라 그 해시(작성자 id)만 받는다
      return json(await voteResult(sb, id, /^[a-f0-9]{24}$/.test(me) ? me : ""), 200, { "Cache-Control": "no-store" });
    }
    if (req.method === "GET" && url.searchParams.get("mode") === "popups") {
      const [{ data, error }, hide] = await Promise.all([
        sb.from("nolco_popups").select("id,ok,item").eq("ok", true).limit(500),
        hidden(sb, "pp"),
      ]);
      if (error) throw error;
      const today = new Date(Date.now() + 9 * 3600000).toISOString().slice(0, 10);   // 한국 날짜
      const popups = visiblePopups(data ?? [], new Set([...hide].map((k) => k.split("/")[2])), today);
      return json({ popups }, 200, { "Cache-Control": "public, max-age=120" });
    }
    if (req.method === "GET") {
      const col = cleanCol(url.searchParams.get("col"));
      if (!col) return json({ error: "col 은 rv 또는 uc 예요." }, 400);
      const [{ data, error }, hide] = await Promise.all([
        sb.from("nolco_docs").select("id,body").eq("col", col).order("updated_at", { ascending: false }).limit(1000),
        hidden(sb, col),
      ]);
      if (error) throw error;
      const docs = ((data ?? []) as { id: string; body: unknown }[]).map((d) => ({ id: d.id, data: withoutHidden(col, d.id, d.body, hide) }));
      return json({ docs }, 200, { "Cache-Control": "no-store" });
    }

    const text = await req.text();
    if (text.length > 220_000) return json({ error: "내용이 너무 길어요." }, 413);
    let msg: Record<string, unknown>;
    try { msg = JSON.parse(text); } catch { return json({ error: "JSON 으로 보내 주세요." }, 400); }
    if (msg.mode === "hit") {
      const hit = cleanHit(msg);
      if (!hit) return json({ error: "잘못된 통계예요." }, 400);
      const sql = stats();
      if (sql) await sql`insert into public.nolco_stats (day, ev, item, n) values ((now() at time zone 'Asia/Seoul')::date, ${hit.ev}, ${hit.item}, 1)
        on conflict (day, ev, item) do update set n = public.nolco_stats.n + 1`;
      return json({ ok: true }, 200);
    }
    if (msg.mode === "admin") return admin(sb, req, msg, json);

    if (msg.mode === "place_report") {
      const id = cleanPlaceId(msg.id);
      if (!id || !validToken(msg.token)) return json({ error: "잘못된 신고예요." }, 400);
      if (await tooMany(sb, req)) return json({ error: "잠시 뒤에 다시 해 주세요." }, 429);
      const { error } = await sb.from("nolco_reports").upsert({ col: "pc", doc_id: "place", item_id: id, reporter: await authorId(msg.token) }, { ignoreDuplicates: true });
      if (error) throw error;
      return json({ ok: true }, 200);
    }
    if (msg.mode === "vote") {
      const id = cleanVoteId(msg.id);
      const pick = cleanPick(msg.pick);
      if (!id || pick === null || !validToken(msg.token)) return json({ error: "잘못된 투표예요." }, 400);
      if (await tooMany(sb, req)) return json({ error: "잠시 뒤에 다시 해 주세요." }, 429);
      const me = await authorId(msg.token);
      await sb.from("nolco_reports").delete().eq("col", "vt").eq("doc_id", id).eq("reporter", me);
      const { error } = await sb.from("nolco_reports").insert({ col: "vt", doc_id: id, item_id: String(pick), reporter: me });
      if (error) throw error;
      return json(await voteResult(sb, id, me), 200);
    }
    if (msg.mode === "popup_report") {
      const id = cleanPopupId(msg.id);
      if (!id || !validToken(msg.token)) return json({ error: "잘못된 신고예요." }, 400);
      if (await tooMany(sb, req)) return json({ error: "잠시 뒤에 다시 해 주세요." }, 429);
      const { error } = await sb.from("nolco_reports").upsert({ col: "pp", doc_id: "popup", item_id: id, reporter: await authorId(msg.token) }, { ignoreDuplicates: true });
      if (error) throw error;
      return json({ ok: true }, 200);
    }

    const col = cleanCol(msg.col);
    if (!col || !validToken(msg.token)) return json({ error: "잘못된 요청이에요." }, 400);
    const me = await authorId(msg.token);
    if (await tooMany(sb, req)) return json({ error: "잠시 뒤에 다시 해 주세요." }, 429);

    if (msg.mode === "set") {
      const clean = cleanBody(col, msg.body);
      if ("error" in clean) return json({ error: clean.error }, 400);
      const { error } = await sb.from("nolco_docs").upsert({ col, id: me, body: clean.body, updated_at: new Date().toISOString() });
      if (error) throw error;
      return json({ ok: true, id: me }, 200);
    }
    if (msg.mode === "report") {
      const doc = typeof msg.doc === "string" && /^[a-f0-9]{24}$/.test(msg.doc) ? msg.doc : null;
      const item = cleanItem(msg.item);
      if (!doc || !item || doc === me) return json({ error: "잘못된 신고예요." }, 400);
      const { error } = await sb.from("nolco_reports").upsert({ col, doc_id: doc, item_id: item, reporter: me }, { ignoreDuplicates: true });
      if (error) throw error;
      return json({ ok: true }, 200);
    }
    return json({ error: "mode 는 set 또는 report 예요." }, 400);
  } catch (error) {
    console.error("community error:", error);
    return json({ error: "저장소에 문제가 생겼어요." }, 502);
  }
}

async function voteResult(sb: Sb, id: string, me: string) {
  const { data, error } = await sb.from("nolco_reports").select("item_id,reporter").eq("col", "vt").eq("doc_id", id).limit(500);
  if (error) throw error;
  const rows = (data ?? []) as { item_id: string; reporter: string }[];
  const mine = rows.find((r) => me && r.reporter === me);
  return { ...voteCounts(rows), mine: mine ? Number(mine.item_id) : null };
}

// 통계용 데이터베이스 연결 (함수가 켜져 있는 동안 하나를 같이 쓴다)
// deno-lint-ignore no-explicit-any
let statsSql: any = null;
function stats() {
  const dbUrl = Deno.env.get("SUPABASE_DB_URL");
  if (!dbUrl) return null;
  statsSql ??= postgres(dbUrl, { max: 2, prepare: false, idle_timeout: 20 });
  return statsSql;
}

async function admin(sb: Sb, req: Request, msg: Record<string, unknown>, json: Json): Promise<Response> {
  if (await tooMany(sb, req)) return json({ error: "잠시 뒤에 다시 해 주세요." }, 429);
  if (!(await checkAdmin(msg.pass))) return json({ error: "관리자 비밀번호가 맞지 않거나 아직 정하지 않았어요." }, 403);
  if (msg.action === "stats") {
    const sql = stats();
    if (!sql) return json({ error: "통계 저장소가 없어요." }, 503);
    const days = await sql`select day::text as day, ev, sum(n)::int as n from public.nolco_stats
      where day >= (now() at time zone 'Asia/Seoul')::date - 29 group by day, ev order by day`;
    const top = await sql`select ev, item, sum(n)::int as n from public.nolco_stats
      where day >= (now() at time zone 'Asia/Seoul')::date - 29 and item <> '' group by ev, item order by n desc limit 60`;
    return json({ days, top }, 200, { "Cache-Control": "no-store" });
  }
  if (msg.action === "list") {
    const [{ data: docs }, { data: reports }] = await Promise.all([
      sb.from("nolco_docs").select("col,id,body,updated_at").order("updated_at", { ascending: false }).limit(1000),
      sb.from("nolco_reports").select("col,doc_id,item_id").in("col", ["rv", "uc"]).limit(5000),
    ]);
    return json({ docs: docs ?? [], reports: reports ?? [] }, 200, { "Cache-Control": "no-store" });
  }
  if (msg.action === "delete") {
    const col = cleanCol(msg.col);
    const doc = typeof msg.doc === "string" && /^[a-f0-9]{24}$/.test(msg.doc) ? msg.doc : null;
    const item = cleanItem(msg.item);
    if (!col || !doc || !item) return json({ error: "지울 대상이 이상해요." }, 400);
    const { data } = await sb.from("nolco_docs").select("body").eq("col", col).eq("id", doc).maybeSingle();
    if (!data) return json({ error: "글을 찾지 못했어요." }, 404);
    const { error } = await sb.from("nolco_docs").update({ body: withoutItem(col, data.body, item), updated_at: new Date().toISOString() }).eq("col", col).eq("id", doc);
    if (error) throw error;
    await sb.from("nolco_reports").delete().eq("col", col).eq("doc_id", doc).eq("item_id", item);
    return json({ ok: true }, 200);
  }
  if (msg.action === "closed") {   // '문 닫았어요' 신고 목록
    const { data } = await sb.from("nolco_reports").select("item_id,reporter,created_at").eq("col", "pc").order("created_at", { ascending: false }).limit(5000);
    return json({ reports: data ?? [] }, 200, { "Cache-Control": "no-store" });
  }
  if (msg.action === "closed_set") {   // 관리자: 확실히 닫음(바로 숨김) / 아님(신고 지우기)
    const id = cleanPlaceId(msg.id);
    if (!id || typeof msg.closed !== "boolean") return json({ error: "가게 id 가 이상해요." }, 400);
    await sb.from("nolco_reports").delete().eq("col", "pc").eq("item_id", id);
    if (msg.closed) await sb.from("nolco_reports").insert({ col: "pc", doc_id: "place", item_id: id, reporter: "admin" });
    return json({ ok: true }, 200);
  }
  if (msg.action === "popups") {
    const [{ data: rows }, { data: reports }] = await Promise.all([
      sb.from("nolco_popups").select("id,ok,item,updated_at").limit(2000),
      sb.from("nolco_reports").select("item_id").eq("col", "pp").limit(5000),
    ]);
    const counts: Record<string, number> = {};
    for (const r of (reports ?? []) as { item_id: string }[]) counts[r.item_id] = (counts[r.item_id] ?? 0) + 1;
    return json({ rows: rows ?? [], reports: counts }, 200, { "Cache-Control": "no-store" });
  }
  if (msg.action === "popup_set") {
    const id = cleanPopupId(msg.id);
    if (!id) return json({ error: "팝업 id 가 이상해요." }, 400);
    if (msg.ok === null) {   // 다시 '확인 전'으로
      await sb.from("nolco_popups").delete().eq("id", id);
      return json({ ok: true }, 200);
    }
    const item = cleanPopupItem(msg.popup);
    if (typeof msg.ok !== "boolean" || (msg.ok && !item)) return json({ error: "이름과 끝나는 날을 확인해 주세요." }, 400);
    const { error } = await sb.from("nolco_popups").upsert({ id, ok: msg.ok, item: item ?? {}, updated_at: new Date().toISOString() });
    if (error) throw error;
    if (msg.ok) await sb.from("nolco_reports").delete().eq("col", "pp").eq("item_id", id);   // 고쳐서 다시 승인하면 신고는 비운다
    return json({ ok: true }, 200);
  }
  return json({ error: "action 은 stats, list, delete, popups, popup_set, closed, closed_set 예요." }, 400);
}
