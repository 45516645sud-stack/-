/**
 * AIIairs 검색 기록 받기 (Google Apps Script)
 *
 * 사이트에서 결과가 없던 검색(type: "miss")과 알림 신청(type: "alert")을
 * 구글 시트에 한 줄씩 쌓는다. 개인정보는 받지 않고 검색 조건만 받는다.
 *
 * 설치
 *  1. 구글 시트를 새로 만든다 → 확장 프로그램 → Apps Script
 *  2. 이 파일 내용을 붙여 넣고 저장
 *  3. 배포 → 새 배포 → 유형: 웹 앱
 *       실행 계정: 나 / 액세스 권한: 모든 사용자
 *  4. 나온 웹 앱 주소(https://script.google.com/macros/s/…/exec)를
 *     index.html 의 <meta name="aiiairs-log-endpoint" content="여기"> 에 넣는다
 */

var HEADER = ['시각', '종류', '어디서', '검색어', '조건', '조건을 풀면', '예시 데이터'];
var TYPES = { miss: '결과 없음', alert: '알림 신청' };

function doPost(e) {
  var data;
  try {
    data = JSON.parse(e.postData.contents);
  } catch (err) {
    return ContentService.createTextOutput('bad request');
  }
  if (!TYPES[data.type]) return ContentService.createTextOutput('ignored');

  var sheet = sheetFor_(data.type);
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

// 종류별로 탭을 나눈다: '결과 없음', '알림 신청'
function sheetFor_(type) {
  var book = SpreadsheetApp.getActiveSpreadsheet();
  var name = TYPES[type];
  var sheet = book.getSheetByName(name) || book.insertSheet(name);
  if (sheet.getLastRow() === 0) {
    sheet.appendRow(HEADER);
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
