import { assertEquals } from "jsr:@std/assert@1";
import { allowedOrigin, cleanQuery, cleanSize, toPhotos } from "./photos.ts";

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
