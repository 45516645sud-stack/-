// 사용법: node render.js [config.json]
// config.json 값을 template.html에 채워 1080x1920 PNG로 저장합니다.
const path = require("path");
const fs = require("fs");
const { chromium } = require("playwright");

(async () => {
  const configPath = path.resolve(process.argv[2] || path.join(__dirname, "config.json"));
  const config = JSON.parse(fs.readFileSync(configPath, "utf8"));
  const out = path.resolve(path.dirname(configPath), config.output || "place-promo.png");

  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  await page.goto("file://" + path.join(__dirname, "template.html"));
  await page.evaluate((c) => window.fill(c), config);
  await page.evaluate(() => document.fonts.ready);

  const overflow = await page.evaluate(() => document.body.scrollHeight - 1920);
  if (overflow > 0) console.warn(`경고: 내용이 ${overflow}px 넘칩니다. 고칠 점 문장을 줄여주세요.`);

  await page.screenshot({ path: out, clip: { x: 0, y: 0, width: 1080, height: 1920 } });
  await browser.close();
  console.log("저장:", out);
})();
