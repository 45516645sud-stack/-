# 박람회 찾기 (Google Apps Script 버전)

`만들기/`의 순수 HTML·CSS·JS 페이지를 Google Apps Script 웹앱 구조로 옮긴 버전입니다.

## 파일 구성

| 파일 | 역할 |
| --- | --- |
| `Code.gs` | `doGet()` — 웹앱 진입점. `include()` — 다른 HTML 파일을 끼워 넣는 헬퍼 |
| `index.html` | 페이지 뼈대 (검색창 + 목록 영역), `Stylesheet`/`JavaScript`를 include |
| `Stylesheet.html` | `<style>...</style>`로 감싼 CSS |
| `JavaScript.html` | `<script>...</script>`로 감싼 JS (샘플 데이터 + 검색 필터링) |
| `appsscript.json` | 프로젝트 매니페스트 (웹앱 접근 권한 등) |

Apps Script의 `HtmlService`는 `.css`/`.js` 파일을 정적 파일로 직접 서빙하지 못하기 때문에,
CSS와 JS를 각각 `<style>`/`<script>` 태그로 감싼 `.html` 파일로 만들고
`index.html`에서 `<?!= include('Stylesheet'); ?>` 스크립틀릿으로 붙여 넣는 방식(GAS 표준 패턴)을 사용했습니다.

## 복사해서 넣는 방법

### 방법 A — script.google.com에서 직접 붙여넣기 (가장 간단)

1. https://script.google.com/ 접속 → **새 프로젝트**
2. 기본 생성된 `Code.gs`에 이 폴더의 `Code.gs` 내용을 그대로 덮어쓰기
3. 왼쪽 파일 목록에서 **+ → HTML** 로 `index`, `Stylesheet`, `JavaScript` 파일을 각각 만들고
   (확장자 `.html`은 자동으로 붙습니다) 같은 이름의 이 폴더 파일 내용을 그대로 붙여넣기
4. 상단 **배포 → 새 배포 → 웹 앱** 선택
   - 실행 권한: **나** (executeAs)
   - 액세스 권한: **모든 사용자** (필요에 따라 조정)
5. 배포 후 나오는 URL로 접속하면 바로 동작합니다.

### 방법 B — clasp CLI 사용 (버전 관리와 함께 쓰고 싶을 때)

```bash
npm install -g @google/clasp
clasp login
cd google-apps-script
clasp create --type webapp --title "박람회 찾기"
clasp push
clasp deploy
```

`clasp create`가 이 폴더에 `.clasp.json`을 만들어주므로, 이후에는 파일을 수정하고
`clasp push`만 실행하면 Apps Script 프로젝트에 반영됩니다.

## 다음 단계

- 지금은 `JavaScript.html` 안에 샘플 데이터 6건이 하드코딩되어 있습니다.
- 실제 데이터를 쓰려면 `Code.gs`에 `UrlFetchApp.fetch(...)`로 공공데이터포털 TourAPI를 호출하는
  서버 함수를 추가하고, 프런트에서 `google.script.run.함수이름()`으로 호출해 받아오는 방식으로 바꾸면 됩니다.
  (Apps Script는 브라우저에서 외부 API를 직접 fetch하는 대신, 서버 측 `UrlFetchApp`을 거치는 구조를 권장합니다.)
