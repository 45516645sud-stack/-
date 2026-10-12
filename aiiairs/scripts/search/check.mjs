// 취향 검색 점검: cases.txt 의 문장을 진짜 브라우저(Playwright)로 하나씩 검색해 보고,
// 지난번에 맞다고 확인한 결과(snapshot.json)와 다르면 어디가 달라졌는지 보여주고 실패한다.
//
//   node aiiairs/scripts/search/check.mjs            점검
//   node aiiairs/scripts/search/check.mjs --update   지금 결과를 새 정답으로 저장 (일부러 바꾼 뒤에)
//
// 날짜는 2026-10-12 오전 10시(한국 시간)로, 공연 데이터는 fixture.json 으로 고정해서 매번 같은 결과가 나오게 한다.
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { execSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SITE = path.resolve(HERE, '../..');                 // aiiairs/
const SNAPSHOT = path.join(HERE, 'snapshot.json');
const UPDATE = process.argv.includes('--update');
const NOW = new Date('2026-10-12T10:00:00+09:00');

// playwright: 저장소 node_modules 에 있으면 그것을, 없으면 전역 설치본을 쓴다
const require = createRequire(import.meta.url);
let playwright;
try { playwright = require('playwright'); } catch {
  playwright = require(path.join(execSync('npm root -g').toString().trim(), 'playwright'));
}

const cases = fs.readFileSync(path.join(HERE, 'cases.txt'), 'utf8')
  .split('\n').map(s => s.trim()).filter(s => s && !s.startsWith('#'));
const fixture = fs.readFileSync(path.join(HERE, 'fixture.json'));

// aiiairs/ 폴더를 그대로 보여주는 작은 서버 (data/fairs.json 만 고정 데이터로 바꿔 준다)
const TYPES = { '.html': 'text/html; charset=utf-8', '.json': 'application/json', '.webp': 'image/webp', '.png': 'image/png', '.svg': 'image/svg+xml' };
const server = http.createServer((req, res) => {
  const url = decodeURIComponent(req.url.split('?')[0]);
  if (url === '/data/fairs.json') { res.writeHead(200, { 'content-type': TYPES['.json'] }); res.end(fixture); return; }
  const file = path.join(SITE, url === '/' ? 'index.html' : url);
  if (!file.startsWith(SITE) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) { res.writeHead(404); res.end(); return; }
  res.writeHead(200, { 'content-type': TYPES[path.extname(file)] || 'application/octet-stream' });
  fs.createReadStream(file).pipe(res);
});
await new Promise(r => server.listen(0, '127.0.0.1', r));
const base = `http://127.0.0.1:${server.address().port}/`;

const browser = await playwright.chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
const errors = [];
page.on('pageerror', e => errors.push(e.message));
// 바깥(글꼴·포스터·구글 기록)은 막는다. 점검은 검색 결과만 본다
await page.route(url => !url.href.startsWith(base), r => r.abort());
await page.clock.setFixedTime(NOW);
await page.goto(base);
await page.waitForSelector('.group');

const results = {};
for (const q of cases) {
  await page.evaluate(() => {
    const clear = [...document.querySelectorAll('#interp button')].find(b => /검색 지우기/.test(b.textContent));
    if (clear) clear.click();
  });
  await page.fill('#askInput', q);
  await page.keyboard.press('Enter');
  await page.waitForFunction(q => document.querySelector('#interp .interp-q')?.textContent.includes(q.slice(0, 10)), q);
  results[q] = await page.evaluate(() => {
    const box = document.getElementById('interp');
    const read = {};
    box.querySelectorAll('dt').forEach(dt => { read[dt.textContent.trim()] = dt.nextElementSibling.textContent.replace(/\s+/g, ' ').trim(); });
    return {
      read,
      note: (box.querySelector('.interp-note')?.textContent || '').replace(/\s+/g, ' ').trim(),
      count: (document.getElementById('sheetCount').textContent.match(/\d+/) || ['0'])[0] * 1,
      top: [...document.querySelectorAll('#sheet .card-btn[data-card], #sheet .row[data-id]')].slice(0, 5).map(b => b.dataset.card || b.dataset.id)
    };
  });
}
await browser.close();
server.close();

if (errors.length) { console.error('페이지 오류:', errors); process.exit(1); }
if (UPDATE) {
  fs.writeFileSync(SNAPSHOT, JSON.stringify(results, null, 1) + '\n');
  console.log(`정답 ${cases.length}개를 저장했어요: ${path.relative(process.cwd(), SNAPSHOT)}`);
  process.exit(0);
}

const expected = JSON.parse(fs.readFileSync(SNAPSHOT, 'utf8'));
let bad = 0;
for (const q of cases) {
  const a = expected[q], b = results[q];
  if (!a) { console.log(`새 문장 (정답 없음): ${q}  → --update 로 정답을 만들어 주세요`); bad++; continue; }
  const diffs = [];
  for (const k of new Set([...Object.keys(a.read), ...Object.keys(b.read)])) if (a.read[k] !== b.read[k]) diffs.push(`  ${k}: ${a.read[k] ?? '(없음)'}  →  ${b.read[k] ?? '(없음)'}`);
  if (a.note !== b.note) diffs.push(`  안내: ${a.note || '(없음)'}  →  ${b.note || '(없음)'}`);
  if (a.count !== b.count) diffs.push(`  건수: ${a.count}  →  ${b.count}`);
  if (a.top.join() !== b.top.join()) diffs.push(`  위 5개: ${a.top.join(', ')}  →  ${b.top.join(', ')}`);
  if (diffs.length) { bad++; console.log(`✗ ${q}\n${diffs.join('\n')}`); }
}
console.log(bad ? `\n${bad}/${cases.length}개가 지난번과 달라요. 일부러 바꾼 거라면 --update 로 정답을 새로 저장하세요.` : `✓ ${cases.length}개 모두 지난번과 같아요.`);
process.exit(bad ? 1 : 0);
