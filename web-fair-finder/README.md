# 박람회 찾기 (Fair Finder)

전국 박람회·전시회를 카테고리, 지역, 무료/유료 조건으로 검색하는 React + Vite 웹앱입니다. (MVP: 홈 / 카테고리 필터 / 상세 검색 / 상세페이지)

## 데이터 소스

공공데이터포털의 **한국관광공사_국문 관광정보 서비스_GW (TourAPI)** 를 사용합니다.

- `searchKeyword2`: "박람회" 키워드 + 지역코드로 목록 조회
- `detailIntro2`: 일정, 요금, 장소 등 상세 소개 조회
- `detailCommon2`: 상세페이지 개요, 대표 이미지, 주소 조회

API 키가 없거나 요청이 실패하면 화면 구성을 확인할 수 있도록 **샘플 데이터**로 자동 전환됩니다(배지로 표시).

## AI 자연어 검색

"아이랑 같이 갈만한 곳 있을까요?" 처럼 박람회 이름을 몰라도 편하게 물어보면,
Claude(Anthropic API)가 가장 알맞은 카테고리와 검색 키워드를 골라줍니다.

- 키는 **서버(Vite 개발 서버) 쪽에서만** 사용되고 브라우저로 내려가지 않습니다 (`vite-ai-plugin.js` 참고).
- `npm run dev`로 실행 중일 때만 동작합니다 (정적 빌드/배포본에는 포함되지 않음).
- 키가 없으면 "AI 검색을 쓰려면 키가 필요해요" 안내만 뜨고, 나머지 기능(카테고리/지역/요금 필터)은 그대로 씁니다.

## 시작하기

```bash
npm install
cp .env.example .env
# .env 파일에 VITE_TOUR_API_KEY=발급받은키 입력
# (선택) AI 검색을 쓰려면 ANTHROPIC_API_KEY=발급받은키 도 입력
npm run dev
```

### TourAPI 키 발급 방법

1. https://www.data.go.kr 회원가입 후 로그인
2. "한국관광공사_국문 관광정보 서비스_GW" 검색 → 활용신청 (승인은 보통 1~2시간 이내 자동 처리)
3. 마이페이지 > 개발계정에서 **일반 인증키(Decoding)** 값을 복사
4. `.env`의 `VITE_TOUR_API_KEY`에 붙여넣기

개발 서버는 `vite.config.js`의 프록시(`/tourapi` → `https://apis.data.go.kr/B551011/KorService2`)를 통해 API를 호출해 브라우저 CORS 문제를 피합니다. 배포 시에는 별도의 서버리스 프록시나 백엔드를 통해 서비스키를 노출하지 않도록 구성하는 것을 권장합니다.

### Anthropic API 키 발급 방법 (AI 검색용, 선택)

1. https://console.anthropic.com 가입/로그인
2. **Settings → API Keys → Create Key**
3. 생성된 키를 `.env`의 `ANTHROPIC_API_KEY`에 붙여넣기 (앞에 `VITE_` 붙이지 않기!)

## 폴더 구조

```
vite-ai-plugin.js   AI 검색용 서버 사이드 엔드포인트 (Vite 플러그인)
src/
  api/        TourAPI/AI 검색 클라이언트, 환경변수 설정
  data/       카테고리, 지역 코드, 샘플 데이터
  components/ 재사용 UI 컴포넌트 (AiSearchBox 포함)
  pages/      홈, 상세 페이지
  utils/      날짜 포맷 등 유틸
```

## 다음 단계 (MVP 이후)

- 찜하기 (localStorage 기반)
- 예약/신청 폼 (모의 제출)
- 페이지네이션 / 무한 스크롤
- 지도 표시 (mapx/mapy 활용)
