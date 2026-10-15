// 놀코 리뷰·직접 만든 코스 저장 규칙 (네트워크 없음, 테스트 대상)
//   rv/<작성자> = { nick, reviews: { 코스id: { rating, text, at } } }
//   uc/<작성자> = { nick, courses: { 코스id: { title, region, stops, … } } }
// 로그인이 없어서 작성자는 브라우저가 만든 비밀 값(token)의 해시로 정한다. 같은 브라우저만 자기 글을 고칠 수 있다.

export type Col = "rv" | "uc";
export const MAX_REVIEWS = 300;
export const MAX_COURSES = 30;
export const MAX_BODY = 200_000; // 글자 수 (JSON)
export const HIDE_AT = 3;        // 서로 다른 사람 신고가 이만큼 모이면 숨김

export function cleanCol(raw: unknown): Col | null {
  return raw === "rv" || raw === "uc" ? raw : null;
}

export function validToken(raw: unknown): raw is string {
  return typeof raw === "string" && /^[a-f0-9]{32,64}$/.test(raw);
}

/** 작성자 id: 'nolco:' + 비밀 값의 sha256 앞 24자리 (앱도 같은 방법으로 자기 id를 안다) */
export async function authorId(token: string): Promise<string> {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode("nolco:" + token));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("").slice(0, 24);
}

const str = (v: unknown, max: number) => (typeof v === "string" ? v.trim().slice(0, max) : "");
const isObj = (v: unknown): v is Record<string, unknown> => !!v && typeof v === "object" && !Array.isArray(v);

/** 닉네임: 12자, 꺾쇠·제어 문자 빼기. 없으면 빈칸(앱이 '누군가'로 보여 줌) */
export function cleanNick(raw: unknown): string {
  return str(raw, 24).replace(/[<>\u0000-\u001f]/g, "").slice(0, 12);
}

/** 저장할 문서 모양 확인. 앱이 읽을 때 한 번 더 걸러내므로 여기서는 크기와 큰 틀만 */
export function cleanBody(col: Col, raw: unknown): { body: Record<string, unknown> } | { error: string } {
  if (!isObj(raw)) return { error: "내용이 비었어요." };
  if (JSON.stringify(raw).length > MAX_BODY) return { error: "내용이 너무 길어요." };
  const nick = cleanNick(raw.nick);
  if (col === "rv") {
    const reviews: Record<string, unknown> = {};
    const src = isObj(raw.reviews) ? raw.reviews : {};
    for (const [cid, r] of Object.entries(src).slice(0, MAX_REVIEWS)) {
      if (!/^[\w-]{1,60}$/.test(cid) || !isObj(r)) continue;
      const rating = Math.round(Number(r.rating) * 2) / 2; // 1~5점, 0.5점 단위
      if (!(rating >= 1 && rating <= 5)) continue;
      reviews[cid] = { rating, text: str(r.text, 500), at: str(r.at, 40) };
    }
    return { body: { nick, reviews } };
  }
  const courses: Record<string, unknown> = {};
  const src = isObj(raw.courses) ? raw.courses : {};
  for (const [id, c] of Object.entries(src).slice(0, MAX_COURSES)) {
    if (!/^u-[\w-]{4,40}$/.test(id) || !isObj(c)) continue;
    courses[id] = c;
  }
  return { body: { nick, courses } };
}

/** 신고 대상 한 개: 문서(작성자) 안의 코스id */
export function cleanItem(raw: unknown): string | null {
  return typeof raw === "string" && /^[\w-]{1,60}$/.test(raw) ? raw : null;
}

/** 신고가 쌓인 항목을 빼고 내보낸다. hidden: "col/문서id/항목id" 모음 */
export function withoutHidden(col: Col, id: string, body: unknown, hidden: Set<string>): Record<string, unknown> {
  const b = isObj(body) ? body : {};
  const key = col === "rv" ? "reviews" : "courses";
  const items = isObj(b[key]) ? b[key] as Record<string, unknown> : {};
  const kept = Object.fromEntries(Object.entries(items).filter(([item]) => !hidden.has(`${col}/${id}/${item}`)));
  return { nick: cleanNick(b.nick), [key]: kept };
}

/* ---------- 방문 통계 ---------- */
export const STAT_EVENTS = new Set(["visit", "course", "act", "event", "share", "eat", "near", "vote", "install"]);

/** 통계 한 건: 종류(ev)와 대상(item, 코스 id 등)만. 이상하면 null */
export function cleanHit(raw: unknown): { ev: string; item: string } | null {
  if (!isObj(raw)) return null;
  const ev = typeof raw.ev === "string" && STAT_EVENTS.has(raw.ev) ? raw.ev : null;
  const item = typeof raw.item === "string" ? raw.item.slice(0, 80) : "";
  if (!ev || !/^[\w.-]*$/.test(item)) return null;
  return { ev, item };
}

/* ---------- 관리자 ---------- */
// 관리자 비밀번호의 PBKDF2 해시 ("pbkdf2$반복수$소금$해시"). 비어 있으면 관리자 기능은 꺼져 있다.
// admin.html 의 '비밀번호 만들기'로 만든 값을 넣는다. 해시만 저장하므로 저장소에 올려도 비밀번호는 알 수 없다.
export const ADMIN_HASH = "pbkdf2$150000$9a1e14e97939d2d73eb15bffee208db7$4b3f0c5439b473a15c16e3d29df0e7f1069641cea05b87e982268265fff01516";

const hex = (b: ArrayBuffer) => [...new Uint8Array(b)].map((x) => x.toString(16).padStart(2, "0")).join("");
const unhex = (h: string) => new Uint8Array((h.match(/../g) ?? []).map((x) => parseInt(x, 16)));

export async function pbkdf2(pass: string, salt: Uint8Array, iterations: number): Promise<string> {
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(pass), "PBKDF2", false, ["deriveBits"]);
  return hex(await crypto.subtle.deriveBits({ name: "PBKDF2", hash: "SHA-256", salt: salt as BufferSource, iterations }, key, 256));
}

/** 비밀번호가 맞는지 (해시가 비어 있거나 모양이 이상하면 언제나 false) */
export async function checkAdmin(pass: unknown, stored: string = ADMIN_HASH): Promise<boolean> {
  const m = /^pbkdf2\$(\d{5,7})\$([0-9a-f]{32})\$([0-9a-f]{64})$/.exec(stored);
  if (!m || typeof pass !== "string" || pass.length < 12 || pass.length > 200) return false;
  const got = await pbkdf2(pass, unhex(m[2]), Number(m[1]));
  let diff = 0;
  for (let i = 0; i < 64; i++) diff |= got.charCodeAt(i) ^ m[3].charCodeAt(i);
  return diff === 0;
}

/** 문서에서 항목 하나 빼기 (관리자 지우기) */
export function withoutItem(col: Col, body: unknown, item: string): Record<string, unknown> {
  const b = isObj(body) ? { ...body } : {};
  const key = col === "rv" ? "reviews" : "courses";
  const items = isObj(b[key]) ? { ...(b[key] as Record<string, unknown>) } : {};
  delete items[item];
  return { ...b, [key]: items };
}

/* ---------- 팝업스토어 (관리자가 승인한 것만 앱에 나온다) ---------- */
export type PopupItem = {
  name: string; place: string; address: string; region: string; start: string; end: string;
  url: string; lat: number | null; lng: number | null; kind: string;
};
// 팝업 종류 (scripts/check_popups.py KINDS 와 같은 이름)
export const POPUP_KINDS = new Set(["anime", "idol", "sports", "character", "game", "beauty", "fashion", "food", "tech", "movie", "living", "art", "pet", "etc"]);
const REGIONS = new Set(["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"]);

export function cleanPopupId(raw: unknown): string | null {
  return typeof raw === "string" && /^p-[a-f0-9]{10}$/.test(raw) ? raw : null;
}

const day = (v: unknown) => (typeof v === "string" && /^20\d\d-\d\d-\d\d$/.test(v) ? v : "");
const coord = (v: unknown, lo: number, hi: number) => (typeof v === "number" && v >= lo && v <= hi ? Math.round(v * 1e6) / 1e6 : null);

/** 승인할 때 저장하는 팝업 한 개. 이름과 끝나는 날은 꼭 있어야 한다 */
export function cleanPopupItem(raw: unknown): PopupItem | null {
  if (!isObj(raw)) return null;
  const name = str(raw.name, 40).replace(/[<>]/g, "");
  const end = day(raw.end);
  if (name.length < 2 || !end) return null;
  const start = day(raw.start);
  const url = typeof raw.url === "string" && /^https?:\/\/[^\s"'<>]{4,300}$/.test(raw.url) ? raw.url : "";
  const region = typeof raw.region === "string" && REGIONS.has(raw.region) ? raw.region : "";
  return {
    name, place: str(raw.place, 60).replace(/[<>]/g, ""), address: str(raw.address, 80).replace(/[<>]/g, ""), region,
    start: start && start <= end ? start : "", end, url, lat: coord(raw.lat, 33, 39), lng: coord(raw.lng, 124, 132),
    kind: typeof raw.kind === "string" && POPUP_KINDS.has(raw.kind) ? raw.kind : "etc",
  };
}

/** 앱에 보여 줄 팝업: 승인됐고, 아직 안 끝났고(오늘 포함), 신고로 숨겨지지 않은 것. 끝나는 날이 가까운 순 */
export function visiblePopups(rows: { id: string; ok: boolean; item: unknown }[], hidden: Set<string>, today: string) {
  return rows
    .flatMap((r) => {
      const item = r.ok && !hidden.has(r.id) ? cleanPopupItem(r.item) : null;
      return item && item.end >= today ? [{ id: r.id, ...item }] : [];
    })
    .sort((a, b) => a.end.localeCompare(b.end));
}

/* ---------- 문 닫은 가게 ('문 닫았어요' 신고) ---------- */
export const CLOSE_AT = 2;   // 서로 다른 두 사람이 알리면(또는 관리자가 확인하면) 숨긴다

/** 카카오 장소 id (place.map.kakao.com/<숫자>) */
export function cleanPlaceId(raw: unknown): string | null {
  const s = typeof raw === "number" ? String(raw) : raw;
  return typeof s === "string" && /^\d{3,15}$/.test(s) ? s : null;
}

export function closedIds(rows: { item_id: string; reporter: string }[]): string[] {
  const n = new Map<string, number>();
  for (const r of rows) n.set(r.item_id, (n.get(r.item_id) ?? 0) + (r.reporter === "admin" ? CLOSE_AT : 1));
  return [...n].filter(([, c]) => c >= CLOSE_AT).map(([id]) => id).sort();
}

/* ---------- 친구 투표 (단톡방에 '어디 갈래?' 링크) ----------
   후보(코스·가게 이름)는 링크 안에 들어 있고, 서버는 투표 id 별로 누가 몇 번째 후보를 골랐는지만 둔다.
   한 사람은 한 표: 다시 고르면 바꾼다. 저장은 nolco_reports (col 'vt', doc_id 투표 id, item_id 후보 번호) */
export const VOTE_MAX = 5;   // 후보는 최대 5개

export function cleanVoteId(raw: unknown): string | null {
  return typeof raw === "string" && /^v-[a-f0-9]{10}$/.test(raw) ? raw : null;
}

export function cleanPick(raw: unknown): number | null {
  return typeof raw === "number" && Number.isInteger(raw) && raw >= 0 && raw < VOTE_MAX ? raw : null;
}

/** 후보별 표 수와 참여한 사람 수 (한 사람이 여러 줄이면 하나만 센다) */
export function voteCounts(rows: { item_id: string; reporter: string }[]): { counts: number[]; voters: number } {
  const counts = Array(VOTE_MAX).fill(0);
  const seen = new Set<string>();
  for (const r of rows) {
    const i = Number(r.item_id);
    if (seen.has(r.reporter) || !Number.isInteger(i) || i < 0 || i >= VOTE_MAX) continue;
    seen.add(r.reporter);
    counts[i]++;
  }
  return { counts, voters: seen.size };
}

/* ---------- PC방 1시간 가격 (이용자가 알려 주기) ----------
   한 사람이 한 가게에 하나 (다시 알려 주면 바뀜). 저장은 nolco_reports (col 'pr', doc_id 가게 id, item_id 가격) */
export function cleanWon(raw: unknown): number | null {
  if (typeof raw !== "number" || !Number.isFinite(raw)) return null;
  const won = Math.round(raw / 100) * 100;
  return won >= 500 && won <= 5000 ? won : null;
}

/** 가게별 알려 준 가격의 가운데 값과 사람 수 */
export function priceSummary(rows: { doc_id: string; item_id: string }[]): Record<string, { won: number; n: number }> {
  const by = new Map<string, number[]>();
  for (const r of rows) {
    const won = cleanWon(Number(r.item_id));
    if (won === null) continue;
    if (!by.has(r.doc_id)) by.set(r.doc_id, []);
    by.get(r.doc_id)!.push(won);
  }
  const out: Record<string, { won: number; n: number }> = {};
  for (const [id, list] of by) {
    list.sort((a, b) => a - b);
    out[id] = { won: list[Math.floor((list.length - 1) / 2)], n: list.length };
  }
  return out;
}
