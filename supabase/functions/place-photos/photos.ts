// 카카오 이미지 검색 결과를 놀코 화면에 필요한 모양으로 줄인다. (네트워크 없음, 테스트 대상)

export type KakaoImageDoc = {
  thumbnail_url?: string;
  image_url?: string;
  doc_url?: string;
  display_sitename?: string;
  collection?: string;
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

// 뉴스·관공서 사진은 사건 사고·단속 사진이 많아 가게 이미지를 해칠 수 있어 뺀다 (블로그·카페 후기 위주로)
const NEWS_SITE = /뉴스|news|일보|신문|방송|기자|타임스|타임즈|times|press|헤럴드|투데이|매일|경제|KBS|MBC|SBS|YTN|JTBC|MBN|채널A|TV조선|연합|뉴시스|노컷|시청|군청|구청|도청|경찰|소방|정부|공사|위키/i;
const NEWS_URL = /news|v\.daum\.net|\/article|\.go\.kr|\.or\.kr|police|wiki/i;

/** 가게 사진으로 쓰기 괜찮은 출처인지 */
export function goodSource(d: KakaoImageDoc): boolean {
  if (d.collection === "news") return false;
  if (NEWS_SITE.test(String(d.display_sitename ?? ""))) return false;
  return !NEWS_URL.test(String(d.doc_url ?? ""));
}

/** https 썸네일과 http(s) 출처가 있는 것만, 뉴스·관공서 사진은 빼고, 같은 썸네일은 한 번만 */
export function toPhotos(docs: KakaoImageDoc[], size: number): Photo[] {
  const seen = new Set<string>();
  const out: Photo[] = [];
  for (const d of docs) {
    if (!isHttps(d.thumbnail_url) || !isHttp(d.doc_url) || seen.has(d.thumbnail_url) || !goodSource(d)) continue;
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

/* ---------- 가게 목록 (카카오 로컬 키워드 검색) ---------- */

export type KakaoPlaceDoc = {
  place_name?: string;
  category_name?: string;
  road_address_name?: string;
  address_name?: string;
  phone?: string;
  place_url?: string;
  distance?: string;
  x?: string;
  y?: string;
};

export type Place = {
  name: string;
  category: string;
  path: string;
  address: string;
  phone: string;
  url: string;
  distance: number | null;
  x: number;
  y: number;
};

/** 한국 안의 좌표만 (위도 33~39, 경도 124~132) */
export function cleanCoord(lat: string | null, lng: string | null): { lat: number; lng: number } | null {
  const a = Number(lat), b = Number(lng);
  if (!Number.isFinite(a) || !Number.isFinite(b)) return null;
  if (a < 33 || a > 39 || b < 124 || b > 132) return null;
  return { lat: a, lng: b };
}

/** 검색 반경(m): 100~20000, 기본 2000 */
export function cleanRadius(raw: string | null): number {
  const n = Math.round(Number(raw ?? 2000));
  return Number.isFinite(n) ? Math.min(20000, Math.max(100, n)) : 2000;
}

/** 이름·좌표가 있는 가게만, 가게 페이지 주소는 카카오 장소 페이지만 (https로) */
export function toPlaces(docs: KakaoPlaceDoc[], size: number): Place[] {
  const out: Place[] = [];
  for (const d of docs) {
    const name = String(d.place_name ?? "").trim().slice(0, 60);
    const x = Number(d.x), y = Number(d.y);
    if (!name || !Number.isFinite(x) || !Number.isFinite(y)) continue;
    const url = /^https?:\/\/place\.map\.kakao\.com\/\d+$/.test(String(d.place_url ?? ""))
      ? String(d.place_url).replace(/^http:/, "https:")
      : "";
    const dist = d.distance === undefined || d.distance === "" ? null : Number(d.distance);
    out.push({
      name,
      category: String(d.category_name ?? "").split(">").pop()!.trim().slice(0, 30),
      path: String(d.category_name ?? "").slice(0, 80), // 전체 분류 (예: 음식점 > 카페 > 테마카페 > 보드카페) — 앱이 종류를 가려낼 때 씀
      address: String(d.road_address_name || d.address_name || "").slice(0, 80),
      phone: String(d.phone ?? "").replace(/[^\d-]/g, "").slice(0, 20),
      url,
      distance: Number.isFinite(dist) ? dist : null,
      x,
      y,
    });
    if (out.length >= size) break;
  }
  return out;
}
