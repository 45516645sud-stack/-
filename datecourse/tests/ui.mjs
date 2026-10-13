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
  "보드게임카페": [P("오래된 보드게임 서면점", "가정,생활 > 여가시설 > 보드카페", 90), P("레드버튼 서면점", "가정,생활 > 여가시설 > 보드카페 > 레드버튼", 120),
    P("어느 호프", "음식점 > 술집 > 호프,요리주점", 50), P("닫은 보드게임 서면점", "가정,생활 > 여가시설 > 보드카페", 400)],
  "디저트카페": [P("설빙 서면점", "음식점 > 카페 > 테마카페 > 디저트카페 > 설빙", 200)],
  "고기집": [P("서면 삼겹살", "음식점 > 한식 > 육류,고기 > 삼겹살", 150), P("고기 카페", "음식점 > 카페", 80), P("고기 호프", "음식점 > 술집 > 호프,요리주점", 90)],
};
const POPUPS = [{ id: "p-0123456789", name: "테스트 팝업", place: "더현대 서울", address: "서울 영등포구 여의대로 108", region: "서울",
  start: "2000-01-01", end: "2100-01-01", url: "https://blog.naver.com/a/1", lat: 37.52, lng: 126.92 },
  // 열흘 뒤 시작: '이번 주말' 기간 밖이어도 '곧 시작'으로 보여야 한다
  { id: "p-0123456780", name: "곧 여는 팝업", place: "성수", address: "", region: "서울",
    start: new Date(Date.now() + 10 * 86400000).toISOString().slice(0, 10), end: "2100-01-01", url: "", lat: null, lng: null }];
const EVENTS = { events: [{ id: "s-1", kind: "show", cat: "연극", title: "테스트 연극", regions: ["부산"], place: "어느 극장",
  start: "2000-01-01", end: "2100-01-01", long: false, price: 20000, note: "", poster: "", link: "https://example.com", info: "" }] };

// 앱을 열고 목록(또는 동네 놀거리)이 그려질 때까지 기다린다. networkidle 은 바깥 요청 때문에 가끔 30초를 넘겨서 쓰지 않는다
async function open(p, url = BASE) {
  await p.goto(url, { waitUntil: "load" });
  await p.waitForFunction(() => document.querySelector("#grid .item") || document.querySelector("#localBox:not([hidden]) .act"), null, { timeout: 20000 });
  await p.waitForTimeout(400);
}

async function page(store = { rv: {}, uc: {} }, opts = {}) {
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, ...opts });
  const p = await ctx.newPage();
  const errors = [];
  p.on("pageerror", (e) => errors.push(e.message));
  await p.route("https://dapi.kakao.com/**", (r) => r.abort());
  // 바깥 글꼴(CDN)은 테스트 기계에서 느릴 때가 있어 받지 않는다 (화면 흐름과 상관없음)
  await p.route("https://cdn.jsdelivr.net/**", (r) => r.abort());
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
    if (mode === "popups") return send({ popups: POPUPS });
    if (mode === "closed") return send({ ids: ["400"] });   // '닫은 보드게임'은 두 사람이 알린 곳
    if (u.searchParams.get("name")) return send({ photos: [], ...(u.searchParams.get("name").startsWith("오래된") ? { latest: "2022-01-01", recent: 0 } : { latest: "2026-09-01", recent: 3 }) });
    return send({ photos: [] });
  });
  return { p, errors, store };
}

console.log("여행 코스");
{
  const { p, errors } = await page();
  await open(p);
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
  await open(p);
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
  await open(p);
  await p.click('.act[data-a="boardgame"]'); await p.waitForTimeout(400);
  const names = await p.locator(".place b").allTextContents();
  ok(names.includes("레드버튼 서면점") && !names.includes("어느 호프"), "보드게임카페에 술집이 안 섞인다");
  ok(!names.includes("닫은 보드게임 서면점"), "'문 닫았어요'가 쌓인 가게는 안 나온다");
  await p.waitForTimeout(300);
  const after = await p.locator(".place b").allTextContents();
  ok(after[after.length - 1] === "오래된 보드게임 서면점" && await p.locator(".place.stale .stale-note").count() === 1, "1년 넘게 후기 없는 가게는 '문 닫았을 수도'로 뒤로 간다");
  ok(errors.length === 0, "오류 없음 " + errors.join(" / "));
}

console.log("이번 주말");
{
  const { p, errors } = await page();
  await open(p);
  await p.click("#weekendBtn"); await p.waitForTimeout(300);
  ok(await p.locator(".ev").count() >= 1, "공연이 나온다");
  await p.locator(".ev", { hasText: "테스트 연극" }).click(); await p.waitForTimeout(200);
  ok((await p.locator("#sheetTitle").textContent()) === "테스트 연극", "공연 상세가 열린다");
  ok(errors.length === 0, "오류 없음 " + errors.join(" / "));
}

console.log("뭐 먹지? · 지금 근처");
{
  const { p, errors } = await page(undefined, { geolocation: { latitude: 35.157, longitude: 129.059 }, permissions: ["geolocation"], reducedMotion: "reduce", timezoneId: "Asia/Seoul" });
  await p.clock.setFixedTime(new Date("2026-10-10T15:00:00+09:00"));   // 토요일 오후 3시 (가게 대부분 영업 중)
  await open(p);
  ok(await p.locator("#eatBtn").isVisible(), "홈에 '뭐 먹지?' 버튼이 있다");
  await p.click("#eatBtn"); await p.waitForTimeout(300);
  await p.locator("#eatMenus .chip", { hasText: "고기" }).click();
  await p.click("#eatGo"); await p.waitForTimeout(400);
  ok((await p.locator(".eat-result .roll").textContent()) === "서면 삼겹살", "고기를 고르면 고깃집만 골라 준다 (카페·술집 빼고)");
  ok((await p.locator("#eatRoute").getAttribute("href")).startsWith("https://map.naver.com/p/search/"), "길찾기는 네이버지도로 간다");
  ok(await p.locator("#eatAfter .act").count() > 5, "밥 먹고 나서 갈 놀거리가 이어서 나온다");
  await p.locator('#eatAfter [data-near-a="boardgame"]').click(); await p.waitForTimeout(400);
  const names = await p.locator(".place b").allTextContents();
  ok((await p.locator("#sheetTitle").textContent()) === "근처 보드게임카페" && names.includes("레드버튼 서면점"), "내 근처 보드게임카페가 나온다");
  await p.locator("#closeBtn").click(); await p.waitForTimeout(200);
  await p.click("#nearBtn"); await p.waitForTimeout(400);
  ok((await p.locator("#nowWhere").textContent()) === "내 위치 근처" && await p.locator("#nearBody .act").count() > 5, "'지금 근처'에서 놀거리를 고를 수 있다");
  ok(errors.length === 0, "오류 없음 " + errors.join(" / "));
}

console.log("이번 주말 · 팝업");
{
  const { p, errors } = await page();
  const reports = [];
  p.on("request", (r) => { if (r.method() === "POST" && (r.postData() || "").includes("popup_report")) reports.push(JSON.parse(r.postData())); });
  p.on("dialog", (d) => d.accept());
  await open(p);
  await p.click("#weekendBtn"); await p.waitForTimeout(300);
  ok(await p.locator(".ev-cat.popup").count() === 2, "승인된 팝업이 이번 주말에 나온다 (2주 안에 시작하는 것도)");
  await p.locator(".ev", { hasText: "테스트 팝업" }).click(); await p.waitForTimeout(200);
  ok((await p.locator("#sheetTitle").textContent()) === "테스트 팝업", "팝업 상세가 열린다");
  await p.click("#popReport"); await p.waitForTimeout(300);
  ok(reports.length === 1 && reports[0].id === "p-0123456789" && /^[a-f0-9]{32}$/.test(reports[0].token), "'정보가 틀렸어요'로 신고가 간다");
  ok(errors.length === 0, "오류 없음 " + errors.join(" / "));
}

console.log("아이폰처럼: 시트 열면 뒤 화면 고정, 아래로 쓸어내려 닫기");
{
  const { p, errors } = await page(undefined, { hasTouch: true, isMobile: true });
  await open(p);
  await p.evaluate(() => scrollTo(0, 400));
  await p.locator("#grid .item").nth(2).tap(); await p.waitForTimeout(400);
  ok(await p.evaluate(() => document.body.classList.contains("sheet-lock")), "시트가 열리면 뒤 화면이 고정된다");
  const cdp = await p.context().newCDPSession(p);
  const touch = (type, y) => cdp.send("Input.dispatchTouchEvent", { type, touchPoints: type === "touchEnd" ? [] : [{ x: 200, y }] });
  await touch("touchStart", 300); for (let y = 300; y <= 650; y += 25) await touch("touchMove", y); await touch("touchEnd"); await p.waitForTimeout(500);
  ok(!(await p.evaluate(() => document.getElementById("sheet").open)), "아래로 쓸어내리면 닫힌다");
  ok(await p.evaluate(() => Math.abs(scrollY - 400) < 2 && !document.body.classList.contains("sheet-lock")), "닫으면 보던 자리로 돌아온다");
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
