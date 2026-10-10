import { assertEquals } from "jsr:@std/assert@1";
import { allowedOrigin, cleanCoord, cleanQuery, cleanRadius, cleanSize, toPhotos, toPlaces } from "./photos.ts";

Deno.test("검색어 정리", () => {
  assertEquals(cleanQuery("  서면   OO노래방  부산진구 "), "서면 OO노래방 부산진구");
  assertEquals(cleanQuery("a"), null);
  assertEquals(cleanQuery("가".repeat(61)), null);
  assertEquals(cleanQuery(null), null);
});

Deno.test("장수 제한", () => {
  assertEquals(cleanSize(null), 4);
  assertEquals(cleanSize("100"), 8);
  assertEquals(cleanSize("0"), 1);
  assertEquals(cleanSize("x"), 4);
});

Deno.test("https 썸네일만, 중복 없이", () => {
  const docs = [
    { thumbnail_url: "https://t1.daumcdn.net/a", doc_url: "https://blog.naver.com/1", display_sitename: "네이버블로그" },
    { thumbnail_url: "https://t1.daumcdn.net/a", doc_url: "https://blog.naver.com/2" },
    { thumbnail_url: "http://insecure/b", doc_url: "https://x" },
    { thumbnail_url: "https://t1.daumcdn.net/c", doc_url: "javascript:alert(1)" },
    { thumbnail_url: "https://t1.daumcdn.net/d", doc_url: "http://cafe.daum.net/3" },
  ];
  assertEquals(toPhotos(docs, 4), [
    { thumb: "https://t1.daumcdn.net/a", link: "https://blog.naver.com/1", site: "네이버블로그" },
    { thumb: "https://t1.daumcdn.net/d", link: "http://cafe.daum.net/3", site: "" },
  ]);
  assertEquals(toPhotos(docs, 1).length, 1);
});

Deno.test("허용한 사이트만", () => {
  const list = "https://45516645sud-stack.github.io, http://localhost:8000/";
  assertEquals(allowedOrigin("https://45516645sud-stack.github.io", list), "https://45516645sud-stack.github.io");
  assertEquals(allowedOrigin("http://localhost:8000", list), "http://localhost:8000");
  assertEquals(allowedOrigin("https://evil.example", list), null);
  assertEquals(allowedOrigin(null, list), null);
});

Deno.test("좌표·반경 정리", () => {
  assertEquals(cleanCoord("35.158", "129.06"), { lat: 35.158, lng: 129.06 });
  assertEquals(cleanCoord("40", "129"), null);
  assertEquals(cleanCoord("abc", "129"), null);
  assertEquals(cleanRadius(null), 2000);
  assertEquals(cleanRadius("50"), 100);
  assertEquals(cleanRadius("99999"), 20000);
});

Deno.test("가게 목록 모양 맞추기", () => {
  const docs = [
    { place_name: "세븐스타코인노래연습장 서면점", category_name: "가정,생활 > 여가시설 > 노래방", road_address_name: "부산 부산진구 중앙대로680번가길 47",
      address_name: "부산 부산진구 부전동 168-94", phone: "051-000-0000", place_url: "http://place.map.kakao.com/123456", distance: "85", x: "129.06", y: "35.158" },
    { place_name: "", x: "1", y: "2" },
    { place_name: "좌표 없음" },
    { place_name: "이상한 링크", place_url: "javascript:alert(1)", x: "129", y: "35", distance: "" },
  ];
  assertEquals(toPlaces(docs, 10), [
    { name: "세븐스타코인노래연습장 서면점", category: "노래방", address: "부산 부산진구 중앙대로680번가길 47", phone: "051-000-0000",
      url: "https://place.map.kakao.com/123456", distance: 85, x: 129.06, y: 35.158 },
    { name: "이상한 링크", category: "", address: "", phone: "", url: "", distance: null, x: 129, y: 35 },
  ]);
  assertEquals(toPlaces(docs, 1).length, 1);
});
