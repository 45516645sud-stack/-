import { createClient } from "jsr:@supabase/supabase-js@2";
import { allowedOrigin, cleanCoord, cleanQuery, cleanRadius, cleanSize, toPhotos, toPlaces, toPostPhotos } from "./photos.ts";
import { authorId, cleanBody, cleanCol, cleanItem, HIDE_AT, validToken, withoutHidden } from "./community.ts";

// 놀코 '우리 동네'의 가게 목록과 가게 사진을 찾아 주는 엔드포인트.
// 카카오 REST API 키는 비밀이라 앱 화면에 둘 수 없어서, 이 함수가 대신 카카오에 물어본다.
//   사진: GET ?q=<가게 이름 + 구>&name=<가게 이름>&size=4 → { photos: [{ thumb, link, site }] }
//         name 이 있으면 블로그·카페 글 중 가게 이름이 나오는 글의 사진만 (없으면 예전처럼 이미지 검색)
//   가게: GET ?mode=places&q=<동네 + 놀거리>&lat=&lng=&radius=2000&size=10[&page=2]
//                                                    → { places: [{ name, category, path, address, phone, url, distance, x, y }] }
//   리뷰·코스: GET ?mode=docs&col=rv|uc               → { docs: [{ id, data }] }
//              POST { mode: "set", col, token, body }   → { ok, id }   (자기 문서만)
//              POST { mode: "report", col, doc, item, token } → { ok }
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
  if (req.method === "POST" || url.searchParams.get("mode") === "docs") return community(req, url, json);
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
      const photos = toPostPhotos([...blog, ...cafe], name, size);
      return json({ photos }, 200, { "Cache-Control": "public, max-age=86400" });
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

async function community(req: Request, url: URL, json: Json): Promise<Response> {
  const sb = database();
  if (!sb) return json({ error: "저장소가 아직 설정되지 않았어요." }, 503);
  try {
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
