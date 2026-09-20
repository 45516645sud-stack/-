# 박람회 찾기 (Fair Finder)

전국 박람회·전시회를 카테고리, 지역, 무료/유료 조건으로 검색하는 React + Vite 웹앱입니다. (MVP: 홈 / 카테고리 필터 / 상세 검색 / 상세페이지)

## 데이터 소스

공공데이터포털의 **한국관광공사_국문 관광정보 서비스_GW (TourAPI)** 를 사용합니다.

- `searchKeyword2`: "박람회" 키워드 + 지역코드로 목록 조회
- `detailIntro2`: 일정, 요금, 장소 등 상세 소개 조회
- `detailCommon2`: 상세페이지 개요, 대표 이미지, 주소 조회

API 키가 없거나 요청이 실패하면 화면 구성을 확인할 수 있도록 **샘플 데이터**로 자동 전환됩니다(배지로 표시).

## 시작하기

```bash
npm install
cp .env.example .env
# .env 파일에 VITE_TOUR_API_KEY=발급받은키 입력
npm run dev
```

### API 키 발급 방법

1. https://www.data.go.kr 회원가입 후 로그인
2. "한국관광공사_국문 관광정보 서비스_GW" 검색 → 활용신청 (승인은 보통 1~2시간 이내 자동 처리)
3. 마이페이지 > 개발계정에서 **일반 인증키(Decoding)** 값을 복사
4. `.env`의 `VITE_TOUR_API_KEY`에 붙여넣기

개발 서버는 `vite.config.js`의 프록시(`/tourapi` → `https://apis.data.go.kr/B551011/KorService2`)를 통해 API를 호출해 브라우저 CORS 문제를 피합니다. 배포 시에는 별도의 서버리스 프록시나 백엔드를 통해 서비스키를 노출하지 않도록 구성하는 것을 권장합니다.

## 폴더 구조

```
src/
  api/        TourAPI 클라이언트, 환경변수 설정
  data/       카테고리, 지역 코드, 샘플 데이터
  components/ 재사용 UI 컴포넌트
  pages/      홈, 상세 페이지
  utils/      날짜 포맷 등 유틸
```

## 다음 단계 (MVP 이후)

- 찜하기 (localStorage 기반)
- 예약/신청 폼 (모의 제출)
- 페이지네이션 / 무한 스크롤
- 지도 표시 (mapx/mapy 활용)
