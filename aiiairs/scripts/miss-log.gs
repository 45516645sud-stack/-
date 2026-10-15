/**
 * AIIairs 검색 기록 받기 (Google Apps Script)
 *
 * 사이트에서 결과가 없던 검색(type: "miss"), 알림 신청(type: "alert"),
 * 5분 사용 뒤 묻는 사용 의견(type: "feedback")을 구글 시트에 한 줄씩 쌓는다.
 * 방문 통계(type: "stat")는 '방문' 탭에 하루 한 줄로 숫자를 더하고, 열어 본 공연은 '많이 본 공연' 탭에 센다.
 * 개인정보는 받지 않는다 (검색 조건, 별로예요/좋아요, 적어 준 의견만).
 *
 * 설치
 *  1. 구글 시트를 새로 만든다 → 확장 프로그램 → Apps Script
 *  2. 이 파일 내용을 붙여 넣고 저장
 *  3. 배포 → 새 배포 → 유형: 웹 앱
 *       실행 계정: 나 / 액세스 권한: 모든 사용자
 *  4. 나온 웹 앱 주소(https://script.google.com/macros/s/…/exec)를
 *     index.html 의 <meta name="aiiairs-log-endpoint" content="여기"> 에 넣는다
 *
 * 관리자 앱(admin.html)
 *  - 취향 검색에 쓴 문장(type: "search")은 '검색' 탭에 쌓는다.
 *  - doGet 은 비밀번호가 맞을 때만 시트 내용을 돌려준다. 비밀번호는 코드에 적지 않고
 *    Apps Script → 프로젝트 설정(톱니) → 스크립트 속성 → ADMIN_TOKEN 에 12자 이상으로 넣는다.
 */

var HEADER = ['시각', '종류', '어디서', '검색어', '조건', '조건을 풀면', '예시 데이터'];
var TYPES = { miss: '결과 없음', alert: '알림 신청', feedback: '의견', search: '검색' };
var FEEDBACK_HEADER = ['시각', '평가', '고른 이유', '의견', '사용 시간(분)', '화면'];
var SEARCH_HEADER = ['시각', '검색어', '결과 수', '화면'];
var STAT_HEADER = ['날짜', '방문', '모바일', 'PC', '공연 열기', '검색', '예매 클릭', 'KOPIS 정보', '지도', '링크 복사', '캘린더'];
var STAT_KEYS = ['visit', 'mobile', 'pc', 'open', 'search', 'book', 'info', 'map', 'share', 'cal'];

function doPost(e) {
  var data;
  try {
    data = JSON.parse(e.postData.contents);
  } catch (err) {
    return ContentService.createTextOutput('bad request');
  }
  if (data.type === 'stat') {
    addStat_(data);
    return ContentService.createTextOutput('ok');
  }
  if (!TYPES[data.type]) return ContentService.createTextOutput('ignored');

  var sheet = sheetFor_(data.type);
  if (data.type === 'search') {
    sheet.appendRow([new Date(), cut_(data.q, 200), count_(data.count), data.device === '모바일' ? '모바일' : 'PC']);
    return ContentService.createTextOutput('ok');
  }
  if (data.type === 'feedback') {
    sheet.appendRow([
      new Date(),
      data.rating === '좋아요' ? '2 좋아요' : data.rating === '피드백' ? '피드백 버튼' : '1 별로예요',
      cut_((data.reasons || []).join(', '), 200),
      cut_(data.text, 500),
      Number(data.minutes) || '',
      data.device === '모바일' ? '모바일' : 'PC'
    ]);
    return ContentService.createTextOutput('ok');
  }
  sheet.appendRow([
    new Date(),
    TYPES[data.type],
    data.source === 'search' ? '취향 검색' : data.source === 'filter' ? '필터' : '',
    cut_(data.q, 200),
    cut_(data.label, 200),
    cut_((data.relax || []).join(', '), 200),
    data.sample ? '예' : ''
  ]);
  return ContentService.createTextOutput('ok');
}

// 종류별로 탭을 나눈다: '결과 없음', '알림 신청', '의견', '검색'
function sheetFor_(type) {
  var book = SpreadsheetApp.getActiveSpreadsheet();
  var name = TYPES[type];
  var sheet = book.getSheetByName(name) || book.insertSheet(name);
  if (sheet.getLastRow() === 0) {
    sheet.appendRow(type === 'feedback' ? FEEDBACK_HEADER : type === 'search' ? SEARCH_HEADER : HEADER);
    sheet.setFrozenRows(1);
  }
  return sheet;
}

function cut_(v, n) {
  var s = String(v == null ? '' : v);
  // 수식으로 해석되지 않도록 막는다
  if (/^[=+\-@]/.test(s)) s = "'" + s;
  return s.length > n ? s.slice(0, n) : s;
}

// 방문 통계: 오늘(한국 시간) 줄을 찾아 숫자를 더한다. 여러 사람이 동시에 보내도 꼬이지 않게 잠그고 쓴다.
function addStat_(data) {
  var lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    var book = SpreadsheetApp.getActiveSpreadsheet();
    var sheet = book.getSheetByName('방문') || book.insertSheet('방문');
    if (sheet.getLastRow() === 0) {
      sheet.appendRow(STAT_HEADER);
      sheet.setFrozenRows(1);
    }
    var today = Utilities.formatDate(new Date(), 'Asia/Seoul', 'yyyy-MM-dd');
    var row = findRow_(sheet, today, 60);
    if (row < 0) {
      sheet.appendRow([''].concat(STAT_KEYS.map(function () { return 0; })));
      row = sheet.getLastRow();
      sheet.getRange(row, 1).setNumberFormat('@').setValue(today);
    }
    var visit = num_(data.visit) > 0 ? 1 : 0;
    var add = {
      visit: visit,
      mobile: visit && data.device === '모바일' ? 1 : 0,
      pc: visit && data.device !== '모바일' ? 1 : 0,
      open: num_(data.open), search: num_(data.search), book: num_(data.book), info: num_(data.info),
      map: num_(data.map), share: num_(data.share), cal: num_(data.cal)
    };
    var range = sheet.getRange(row, 2, 1, STAT_KEYS.length);
    var vals = range.getValues()[0];
    for (var i = 0; i < STAT_KEYS.length; i++) vals[i] = (Number(vals[i]) || 0) + add[STAT_KEYS[i]];
    range.setValues([vals]);

    var shows = Array.isArray(data.shows) ? data.shows.slice(0, 30) : [];
    if (shows.length) {
      var top = book.getSheetByName('많이 본 공연') || book.insertSheet('많이 본 공연');
      if (top.getLastRow() === 0) {
        top.appendRow(['공연', '열어 본 횟수', '마지막으로 본 날']);
        top.setFrozenRows(1);
      }
      shows.forEach(function (pair) {
        var title = cut_(pair && pair[0], 120);
        var count = num_(pair && pair[1]);
        if (!title || !count) return;
        var at = findRow_(top, title, 0);
        if (at < 0) {
          top.appendRow([title, 0, '']);
          at = top.getLastRow();
        }
        var cell = top.getRange(at, 2);
        cell.setValue((Number(cell.getValue()) || 0) + count);
        top.getRange(at, 3).setNumberFormat('@').setValue(today);
      });
    }
  } finally {
    lock.releaseLock();
  }
}

// 첫 칸이 key 인 줄 번호 (없으면 -1). recent 가 0보다 크면 아래쪽 recent 줄만 본다.
function findRow_(sheet, key, recent) {
  var last = sheet.getLastRow();
  if (last < 2) return -1;
  var from = recent > 0 ? Math.max(2, last - recent + 1) : 2;
  var keys = sheet.getRange(from, 1, last - from + 1, 1).getDisplayValues();
  for (var i = keys.length - 1; i >= 0; i--) if (keys[i][0] === key) return from + i;
  return -1;
}

// 숫자만, 0~5000 사이로 (검색 결과 수용). 통계는 아래 num_ 이 0~500 으로 자른다
function count_(v) {
  var n = Math.floor(Number(v) || 0);
  return n < 0 ? 0 : n > 5000 ? 5000 : n;
}

// 숫자만, 0~500 사이로 (가짜로 큰 숫자를 보내도 통계가 망가지지 않게)
function num_(v) {
  var n = Math.floor(Number(v) || 0);
  return n < 0 ? 0 : n > 500 ? 500 : n;
}

/* ---------------- 관리자 앱(admin.html)이 읽어 가는 곳 ----------------
   ?token=비밀번호 가 스크립트 속성 ADMIN_TOKEN 과 같을 때만 시트 내용을 JSON 으로 돌려준다. */
function doGet(e) {
  var want = PropertiesService.getScriptProperties().getProperty('ADMIN_TOKEN') || '';
  var got = String((e && e.parameter && e.parameter.token) || '');
  if (want.length < 12) return json_({ ok: false, error: 'setup', message: 'Apps Script 스크립트 속성에 ADMIN_TOKEN(12자 이상)을 넣어 주세요.' });
  if (!same_(got, want)) {
    Utilities.sleep(1500);  // 마구 넣어 보기 늦추기
    return json_({ ok: false, error: 'token', message: '비밀번호가 맞지 않아요.' });
  }
  var book = SpreadsheetApp.getActiveSpreadsheet();
  return json_({
    ok: true,
    now: Utilities.formatDate(new Date(), 'Asia/Seoul', "yyyy-MM-dd'T'HH:mm:ss"),
    visits: rows_(book, '방문', 120).map(function (r) {
      var o = { date: r[0] };
      STAT_KEYS.forEach(function (k, i) { o[k] = Number(r[i + 1]) || 0; });
      return o;
    }),
    top: rows_(book, '많이 본 공연', 0)
      .map(function (r) { return { title: r[0], count: Number(r[1]) || 0, last: r[2] }; })
      .sort(function (a, b) { return b.count - a.count; }).slice(0, 50),
    feedback: rows_(book, '의견', 300).map(function (r) {
      return { at: r[0], rating: r[1], reasons: r[2], text: r[3], minutes: r[4], device: r[5] };
    }).reverse(),
    searches: rows_(book, '검색', 2000).map(function (r) {
      return { at: r[0], q: r[1], count: Number(r[2]) || 0, device: r[3] };
    }).reverse(),
    misses: rows_(book, '결과 없음', 300).map(function (r) {
      return { at: r[0], source: r[2], q: r[3], label: r[4], relax: r[5] };
    }).reverse(),
    alerts: rows_(book, '알림 신청', 300).map(function (r) {
      return { at: r[0], q: r[3], label: r[4] };
    }).reverse()
  });
}

// 탭의 마지막 n 줄 (n 이 0 이면 전부). 날짜는 한국 시간 글자로 바꾼다.
function rows_(book, name, n) {
  var sheet = book.getSheetByName(name);
  if (!sheet || sheet.getLastRow() < 2) return [];
  var last = sheet.getLastRow();
  var from = n > 0 ? Math.max(2, last - n + 1) : 2;
  return sheet.getRange(from, 1, last - from + 1, sheet.getLastColumn()).getValues().map(function (r) {
    return r.map(function (v) {
      return v instanceof Date ? Utilities.formatDate(v, 'Asia/Seoul', 'yyyy-MM-dd HH:mm') : v;
    });
  });
}

function json_(o) {
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
}

// 길이와 글자를 끝까지 비교한다 (어디서 틀렸는지 시간으로 알 수 없게)
function same_(a, b) {
  if (a.length !== b.length) return false;
  var d = 0;
  for (var i = 0; i < a.length; i++) d |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return d === 0;
}
