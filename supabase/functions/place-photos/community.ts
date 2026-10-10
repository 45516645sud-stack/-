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
      const rating = Math.round(Number(r.rating));
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
