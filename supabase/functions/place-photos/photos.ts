// 카카오 이미지 검색 결과를 놀코 화면에 필요한 모양으로 줄인다. (네트워크 없음, 테스트 대상)

export type KakaoImageDoc = {
  thumbnail_url?: string;
  image_url?: string;
  doc_url?: string;
  display_sitename?: string;
};

export type Photo = { thumb: string; link: string; site: string };

export const MAX_QUERY = 60;
export const MAX_SIZE = 8;

/** 검색어 정리: 앞뒤 공백·연속 공백을 줄이고, 너무 짧거나 길면 null */
export function cleanQuery(raw: string | null): string | null {
  const q = (raw ?? "").replace(/\s+/g, " ").trim();
  if (q.length < 2 || q.length > MAX_QUERY) return null;
  return q;
}

/** 몇 장 받을지: 1~MAX_SIZE, 기본 4 */
export function cleanSize(raw: string | null): number {
  const n = Math.round(Number(raw ?? 4));
  return Number.isFinite(n) ? Math.min(MAX_SIZE, Math.max(1, n)) : 4;
}

const isHttps = (u: unknown): u is string => typeof u === "string" && /^https:\/\//.test(u);
const isHttp = (u: unknown): u is string => typeof u === "string" && /^https?:\/\//.test(u);

/** https 썸네일과 http(s) 출처가 있는 것만, 같은 썸네일은 한 번만 */
export function toPhotos(docs: KakaoImageDoc[], size: number): Photo[] {
  const seen = new Set<string>();
  const out: Photo[] = [];
  for (const d of docs) {
    if (!isHttps(d.thumbnail_url) || !isHttp(d.doc_url) || seen.has(d.thumbnail_url)) continue;
    seen.add(d.thumbnail_url);
    out.push({ thumb: d.thumbnail_url, link: d.doc_url, site: String(d.display_sitename ?? "").slice(0, 40) });
    if (out.length >= size) break;
  }
  return out;
}

/** 허용한 사이트에서 온 요청인지. ALLOWED_ORIGINS 는 쉼표로 구분 */
export function allowedOrigin(origin: string | null, allowList: string): string | null {
  if (!origin) return null;
  const list = allowList.split(",").map((s) => s.trim().replace(/\/$/, "")).filter(Boolean);
  return list.includes(origin.replace(/\/$/, "")) ? origin : null;
}
