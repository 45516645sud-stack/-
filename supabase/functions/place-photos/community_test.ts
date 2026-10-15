import { assertEquals } from "jsr:@std/assert@1";
import { SCHEMA } from "./schema.ts";
import { authorId, checkAdmin, cleanBody, cleanCol, cleanHit, cleanNick, pbkdf2, validToken, withoutHidden, withoutItem, cleanPopupId, cleanPopupItem, visiblePopups, cleanPlaceId, closedIds, cleanVoteId, cleanPick, voteCounts, cleanWon, priceSummary } from "./community.ts";

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

Deno.test("팝업: id·항목 정리", () => {
  assertEquals(cleanPopupId("p-0123456789"), "p-0123456789");
  assertEquals(cleanPopupId("p-xyz"), null);
  const item = cleanPopupItem({ name: " 육구방앗간 <b>", place: "롯데백화점 잠실점", region: "서울", start: "2026-10-09", end: "2026-10-15",
    url: "https://blog.naver.com/a/1", lat: 37.51, lng: 127.1, extra: "x" });
  assertEquals(item, { name: "육구방앗간 b", place: "롯데백화점 잠실점", address: "", region: "서울", start: "2026-10-09", end: "2026-10-15",
    url: "https://blog.naver.com/a/1", lat: 37.51, lng: 127.1, kind: "etc" });
  assertEquals(cleanPopupItem({ name: "주술회전", end: "2026-11-30", kind: "anime" })?.kind, "anime");
  assertEquals(cleanPopupItem({ name: "주술회전", end: "2026-11-30", kind: "hack" })?.kind, "etc");
  assertEquals(cleanPopupItem({ name: "x", end: "2026-10-15" }), null);              // 이름 너무 짧음
  assertEquals(cleanPopupItem({ name: "팝업", end: "10월 15일" }), null);             // 날짜 모양
  assertEquals(cleanPopupItem({ name: "팝업", end: "2026-10-15", url: "javascript:alert(1)", region: "화성" })?.url, "");
});

Deno.test("팝업: 승인·안 끝남·신고 안 된 것만, 끝나는 날 순", () => {
  const it = (name: string, end: string) => ({ name, end });
  const rows = [
    { id: "p-0000000001", ok: true, item: it("늦게 끝남", "2026-10-30") },
    { id: "p-0000000002", ok: true, item: it("곧 끝남", "2026-10-12") },
    { id: "p-0000000003", ok: true, item: it("끝남", "2026-10-11") },
    { id: "p-0000000004", ok: false, item: it("거절", "2026-10-20") },
    { id: "p-0000000005", ok: true, item: it("신고됨", "2026-10-20") },
  ];
  const got = visiblePopups(rows, new Set(["p-0000000005"]), "2026-10-12");
  assertEquals(got.map((p) => p.name), ["곧 끝남", "늦게 끝남"]);
});

Deno.test("문 닫은 가게: 두 사람이 알리거나 관리자가 확인하면", () => {
  assertEquals(cleanPlaceId("1234567"), "1234567");
  assertEquals(cleanPlaceId(98765), "98765");
  assertEquals(cleanPlaceId("abc"), null);
  assertEquals(closedIds([
    { item_id: "111", reporter: "a" }, { item_id: "111", reporter: "b" },
    { item_id: "222", reporter: "a" },
    { item_id: "333", reporter: "admin" },
  ]), ["111", "333"]);
});

Deno.test("친구 투표: id·후보 번호 확인과 한 사람 한 표", () => {
  assertEquals(cleanVoteId("v-0123456789"), "v-0123456789");
  assertEquals(cleanVoteId("v-01234"), null);
  assertEquals(cleanVoteId("p-0123456789"), null);
  assertEquals(cleanPick(0), 0);
  assertEquals(cleanPick(4), 4);
  assertEquals(cleanPick(5), null);
  assertEquals(cleanPick(1.5), null);
  assertEquals(cleanPick("1"), null);
  const r = voteCounts([
    { item_id: "0", reporter: "a" }, { item_id: "2", reporter: "b" }, { item_id: "2", reporter: "c" },
    { item_id: "1", reporter: "a" },   // 같은 사람 두 번째 줄은 세지 않음
    { item_id: "9", reporter: "d" },   // 이상한 번호
  ]);
  assertEquals(r, { counts: [1, 0, 2, 0, 0], voters: 3 });
});

Deno.test("PC방 가격 알려 주기: 값 확인과 가게별 가운데 값", () => {
  assertEquals(cleanWon(1234), 1200);
  assertEquals(cleanWon(400), null);
  assertEquals(cleanWon(9000), null);
  assertEquals(cleanWon("1200"), null);
  assertEquals(priceSummary([
    { doc_id: "111", item_id: "1200" }, { doc_id: "111", item_id: "1000" }, { doc_id: "111", item_id: "1500" },
    { doc_id: "222", item_id: "1300" }, { doc_id: "222", item_id: "abc" },
  ]), { "111": { won: 1200, n: 3 }, "222": { won: 1300, n: 1 } });
});
