import { assertEquals } from "jsr:@std/assert@1";
import { SCHEMA } from "./schema.ts";
import { authorId, checkAdmin, cleanBody, cleanCol, cleanHit, cleanNick, pbkdf2, validToken, withoutHidden, withoutItem } from "./community.ts";

Deno.test("col·token 확인", () => {
  assertEquals(cleanCol("rv"), "rv");
  assertEquals(cleanCol("x"), null);
  assertEquals(validToken("a".repeat(32)), true);
  assertEquals(validToken("xyz"), false);
});

Deno.test("작성자 id 는 비밀 값마다 같고 24자리", async () => {
  const a = await authorId("0".repeat(32));
  assertEquals(a.length, 24);
  assertEquals(a, await authorId("0".repeat(32)));
});

Deno.test("리뷰 문서 정리", () => {
  const r = cleanBody("rv", { nick: "<b>민지</b>", reviews: { "busan-x": { rating: 9, text: "좋아요" }, "ok-1": { rating: 4, text: " 굿 ", at: "2026" }, "half-1": { rating: 3.5 }, "odd-1": { rating: 2.3 }, "low-1": { rating: 0.5 }, "bad id!": { rating: 3 } } });
  assertEquals(r, { body: { nick: "b민지/b", reviews: { "ok-1": { rating: 4, text: "굿", at: "2026" }, "half-1": { rating: 3.5, text: "", at: "" }, "odd-1": { rating: 2.5, text: "", at: "" } } } });
});

Deno.test("코스 문서는 u- 로 시작하는 id만", () => {
  const r = cleanBody("uc", { courses: { "u-abcd1234": { title: "t" }, "x": {} } });
  assertEquals(r, { body: { nick: "", courses: { "u-abcd1234": { title: "t" } } } });
  assertEquals("error" in cleanBody("uc", "x"), true);
});

Deno.test("신고 쌓인 항목 숨기기", () => {
  const out = withoutHidden("rv", "d1", { nick: "a", reviews: { c1: { rating: 5 }, c2: { rating: 1 } } }, new Set(["rv/d1/c2"]));
  assertEquals(out, { nick: "a", reviews: { c1: { rating: 5 } } });
  assertEquals(cleanNick("가나다라마바사아자차카타파하"), "가나다라마바사아자차카타");
});

Deno.test("함수 안 표 정의가 migrations SQL 과 같음", async () => {
  const file = await Deno.readTextFile(new URL("../../migrations/20261011000000_nolco_community.sql", import.meta.url));
  assertEquals(SCHEMA, file);
});

Deno.test("통계 한 건 정리", () => {
  assertEquals(cleanHit({ ev: "course", item: "seoul-seongsu" }), { ev: "course", item: "seoul-seongsu" });
  assertEquals(cleanHit({ ev: "visit" }), { ev: "visit", item: "" });
  assertEquals(cleanHit({ ev: "hack", item: "x" }), null);
  assertEquals(cleanHit({ ev: "course", item: "<script>" }), null);
});

Deno.test("관리자 비밀번호 확인", async () => {
  const salt = new Uint8Array(16).fill(7);
  const saltHex = [...salt].map((x) => x.toString(16).padStart(2, "0")).join("");
  const stored = `pbkdf2$100000$${saltHex}$${await pbkdf2("correct horse battery", salt, 100000)}`;
  assertEquals(await checkAdmin("correct horse battery", stored), true);
  assertEquals(await checkAdmin("wrong password 123", stored), false);
  assertEquals(await checkAdmin("correct horse battery", ""), false); // 정하지 않으면 꺼짐
  assertEquals(await checkAdmin("short", stored), false);
});

Deno.test("관리자 지우기는 그 항목만", () => {
  assertEquals(withoutItem("rv", { nick: "a", reviews: { c1: { rating: 5 }, c2: { rating: 1 } } }, "c2"), { nick: "a", reviews: { c1: { rating: 5 } } });
});
