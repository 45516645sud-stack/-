import { allowedOrigin, cleanCoord, cleanQuery, cleanRadius, cleanSize, toPhotos, toPlaces } from "./photos.ts";

// 놀코 '우리 동네'의 가게 목록과 가게 사진을 찾아 주는 엔드포인트.
// 카카오 REST API 키는 비밀이라 앱 화면에 둘 수 없어서, 이 함수가 대신 카카오에 물어본다.
//   사진: GET ?q=<가게 이름 + 구>&size=4            → { photos: [{ thumb, link, site }] }
//   가게: GET ?mode=places&q=<동네 + 놀거리>&lat=&lng=&radius=2000&size=10[&page=2]
//                                                    → { places: [{ name, category, path, address, phone, url, distance, x, y }] }
// 사진은 썸네일과 출처(블로그 등) 링크뿐이다. 원본 사진은 내려주지 않는다.

const KAKAO_IMAGE_SEARCH = "https://dapi.kakao.com/v2/search/image";
const KAKAO_PLACE_SEARCH = "https://dapi.kakao.com/v2/local/search/keyword.json";
const DEFAULT_ORIGINS = "https://45516645sud-stack.github.io,http://localhost:8000";

Deno.serve(async (req) => {
  const origin = allowedOrigin(req.headers.get("Origin"), Deno.env.get("ALLOWED_ORIGINS") ?? DEFAULT_ORIGINS);
  const cors: Record<string, string> = {
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Headers": "content-type",
    Vary: "Origin",
  };
  if (origin) cors["Access-Control-Allow-Origin"] = origin;
  const json = (body: unknown, status: number, extra: Record<string, string> = {}) =>
    new Response(JSON.stringify(body), { status, headers: { ...cors, "Content-Type": "application/json", ...extra } });

  if (req.method === "OPTIONS") return new Response("ok", { headers: cors });
  if (req.method !== "GET") return json({ error: "GET 요청만 지원합니다." }, 405);
  // 등록하지 않은 사이트에서 키를 빌려 쓰지 못하게 한다 (브라우저 요청 기준)
  if (!origin) return json({ error: "허용되지 않은 사이트입니다." }, 403);

  const url = new URL(req.url);
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
