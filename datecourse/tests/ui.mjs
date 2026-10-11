// 놀코 화면 자동 테스트 (Playwright). 서버·카카오는 가짜로 대신하고, 주요 흐름이 깨지지 않았는지 본다.
//   cd datecourse && python3 -m http.server 8765 &   그리고   node tests/ui.mjs
// 환경 변수 CHROME 으로 브라우저 위치를 줄 수 있다 (없으면 Playwright 기본 Chromium)
import { chromium } from "playwright";
import { createHash } from "node:crypto";

const BASE = process.env.BASE || "http://localhost:8765/";
const browser = await chromium.launch(process.env.CHROME ? { executablePath: process.env.CHROME } : {});
let failed = 0;
const ok = (cond, msg) => { console.log((cond ? "  ✓ " : "  ✗ ") + msg); if (!cond) failed++; };

const P = (name, path, d) => ({ name, category: path.split(">").pop().trim(), path, address: "부산 부산진구 " + name, phone: "", url: "https://place.map.kakao.com/" + d, distance: d, x: 129.06, y: 35.15 });
const PLACES = {
  "보드게임카페": [P("레드버튼 서면점", "가정,생활 > 여가시설 > 보드카페 > 레드버튼", 120), P("어느 호프", "음식점 > 술집 > 호프,요리주점", 50)],
  "디저트카페": [P("설빙 서면점", "음식점 > 카페 > 테마카페 > 디저트카페 > 설빙", 200)],
};
const EVENTS = { events: [{ id: "s-1", kind: "show", cat: "연극", title: "테스트 연극", regions: ["부산"], place: "어느 극장",
  start: "2000-01-01", end: "2100-01-01", long: false, price: 20000, note: "", poster: "", link: "https://example.com", info: "" }] };

async function page(store = { rv: {}, uc: {} }) {
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const p = await ctx.newPage();
  const errors = [];
  p.on("pageerror", (e) => errors.push(e.message));
  await p.route("https://dapi.kakao.com/**", (r) => r.abort());
  await p.route("https://tile.openstreetmap.org/**", (r) => r.abort());
  await p.route("**/data/events.json", (r) => r.fulfill({ contentType: "application/json", body: JSON.stringify(EVENTS) }));
  await p.route("https://hzomhheyccapnzuwtzxh.supabase.co/**", async (r) => {
    const req = r.request(); const u = new URL(req.url());
    const send = (o) => r.fulfill({ contentType: "application/json", headers: { "Access-Control-Allow-Origin": "*" }, body: JSON.stringify(o) });
    if (req.method() === "POST") {
      const m = JSON.parse(req.postData() || "{}");
      if (m.mode === "set") { const id = createHash("sha256").update("nolco:" + m.token).digest("hex").slice(0, 24); store[m.col][id] = m.body; return send({ ok: true, id }); }
      return send({ ok: true });
    }
    const mode = u.searchParams.get("mode");
    if (mode === "docs") return send({ docs: Object.entries(store[u.searchParams.get("col")] || {}).map(([id, data]) => ({ id, data })) });
    if (mode === "places") return send({ places: PLACES[u.searchParams.get("q")] || [] });
    return send({ photos: [] });
  });
  return { p, errors, store };
}

console.log("여행 코스");
{
  const { p, errors } = await page();
  await p.goto(BASE, { waitUntil: "networkidle" });
  ok(await p.locator("#grid .item").count() > 50, "코스 목록이 나온다");
  await p.locator("#grid .item").first().click();
  await p.waitForTimeout(300);
  ok((await p.locator("#sheetTitle").textContent()).length > 2, "코스를 열면 상세가 나온다");
  const star = p.locator('.star[data-n="4"]'); await star.scrollIntoViewIfNeeded();
  const box = await star.boundingBox();
  await p.mouse.click(box.x + box.width * 0.25, box.y + box.height / 2);
  ok((await p.locator("#starLabel").textContent()).includes("3.5"), "별 왼쪽 반을 누르면 반 개 (3.5점)");
  ok(errors.length === 0, "오류 없음 " + errors.join(" / "));
}

console.log("리뷰 쓰기 (서버 저장)");
{
  const { p, errors, store } = await page();
  await p.goto(BASE, { waitUntil: "networkidle" });
  await p.locator("#grid .item").first().click(); await p.waitForTimeout(300);
  await p.fill("#reviewNick", "테스터");
  const star = p.locator('.star[data-n="5"]'); await star.scrollIntoViewIfNeeded(); await star.click();
  await p.fill("#reviewText", "좋아요");
  await p.click("#reviewSave"); await p.waitForTimeout(500);
  const saved = Object.values(store.rv)[0];
  ok(saved && saved.nick === "테스터" && Object.values(saved.reviews)[0].rating === 5, "닉네임·별점이 저장된다");
  ok(await p.locator("#reviewList .review").count() === 1, "목록에 내 리뷰가 보인다");
  ok(errors.length === 0, "오류 없음 " + errors.join(" / "));
}

console.log("우리 동네");
{
  const { p, errors } = await page();
  await p.addInitScript(() => { localStorage.setItem("datecourse.mode", '"local"'); localStorage.setItem("datecourse.hood", '"seomyeon"'); });
  await p.goto(BASE, { waitUntil: "networkidle" });
  await p.click('.act[data-a="boardgame"]'); await p.waitForTimeout(400);
  const names = await p.locator(".place b").allTextContents();
  ok(names.includes("레드버튼 서면점") && !names.includes("어느 호프"), "보드게임카페에 술집이 안 섞인다");
  ok(errors.length === 0, "오류 없음 " + errors.join(" / "));
}

console.log("이번 주말");
{
  const { p, errors } = await page();
  await p.goto(BASE, { waitUntil: "networkidle" });
  await p.click("#weekendBtn"); await p.waitForTimeout(300);
  ok(await p.locator(".ev").count() >= 1, "공연이 나온다");
  await p.locator(".ev").first().click(); await p.waitForTimeout(200);
  ok((await p.locator("#sheetTitle").textContent()) === "테스트 연극", "공연 상세가 열린다");
  ok(errors.length === 0, "오류 없음 " + errors.join(" / "));
}

console.log("약관 페이지");
{
  const { p } = await page();
  for (const f of ["privacy.html", "terms.html"]) {
    const res = await p.goto(BASE + f);
    ok(res.ok() && (await p.locator("h1").textContent()).length > 2, f + " 가 열린다");
  }
}

await browser.close();
console.log(failed ? `\n실패 ${failed}개` : "\n모두 통과");
process.exit(failed ? 1 : 0);
