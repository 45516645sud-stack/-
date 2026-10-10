# 놀코 (놀거리 코스): 전국 놀거리·데이트 코스 추천

전국 17개 시·도에서 **누구와(연인·친구·가족·혼자)**, **어떤 분위기로(야경·바다·비 오는 날…)**,
**얼마나 쓸지(예산·시간)** 를 고르면 맞는 놀거리·데이트 코스를 보여 주는 웹 앱이에요.
폰에서 '홈 화면에 추가'하면 앱처럼 쓸 수 있고(PWA), API 키 없이도 바로 돌아가요.

```
datecourse/
├─ index.html              앱 화면 전부 (HTML·CSS·JS 한 파일)
├─ manifest.webmanifest    홈 화면 추가용 정보
├─ sw.js                   오프라인에서도 마지막으로 본 코스 열기
├─ icon.svg
├─ data/
│  ├─ courses.json         직접 고른 기본 코스 (17개 시·도, 67개)
│  └─ tour_courses.json    한국관광공사 추천코스 수집 결과 (수집기를 돌리면 생김)
└─ scripts/
   ├─ collect_tour.py      TourAPI 추천코스 수집기 (Python 표준 라이브러리만)
   ├─ test_collect_tour.py 테스트
   └─ fixtures/            테스트용 가상 응답
```

## 기능

- 지역 · 누구와 · 분위기 태그 · 예산 · 반나절 필터, 검색 (`야경 부산`처럼 여러 단어도 가능)
- 🎲 **아무 코스나 골라줘**: 지금 필터 안에서 무작위로 하나 추천
- 📍 **내 주변 코스**: 내 위치에서 가까운 코스부터 정렬
- 코스 상세: 장소 순서, 머무는 시간, 다음 장소까지 거리·이동 방법, 지도(OpenStreetMap)
- 장소마다 **카카오맵 · 길찾기 · 네이버지도** 바로 열기 (키 없이 쓰는 공개 링크)
- ♡ 찜하기 (이 기기 브라우저에 저장), 🔗 공유하기 (`#c=코스id` 주소로 바로 열림)
- 밝게/어둡게 화면
- 🏘️ **우리 동네**: 맨 위에서 '우리 동네'로 바꾸면 관광지 대신 사는 동네의 일상 놀거리를 보여 줘요.
  지역 → 동네(예: 부산 서면·전포, 부산대 앞)를 고르면 노래방·보드게임카페·방탈출 같은 놀거리 19가지와
  동네마다 일상 코스 12가지가 나와요. 가게 이름은 자주 바뀌어서 넣지 않고, 누르면 '동네 + 놀거리'로
  카카오맵·네이버지도 검색을 열어요. 데이터는 `data/local.json` (17개 시·도, 동네 62곳)
- ⭐ **리뷰**: 코스마다 별점과 후기를 남기고, 카드에 평균 별점이 보여요
- ✏️ **코스 만들기**: 누구나 장소 2~6곳으로 자기 코스를 만들어 올리고, 👥 **모두가 만든 코스**에서 모아 봐요

리뷰와 직접 만든 코스는 claude.ai에 올린 앱 링크의 공유 저장소에 저장돼요. 모두가 읽을 수 있고
각자 자기 것만 고치거나 지울 수 있으며, 앱 주인은 관리용으로 남의 것도 지울 수 있어요.
다른 사람이 글을 쓰려면 앱 주인이 공유 메뉴에서 **참여자(Contributor)** 권한을 줘야 해요.
이 폴더를 다른 곳(GitHub Pages 등)에 올리면 공유 저장소가 없어서 리뷰·코스 만들기는 안내 문구만 보여요.
claude.ai용 파일은 `python3 scripts/build_artifact.py <출력 폴더>` 로 만들어요.

## 실행

`fetch`로 데이터를 읽기 때문에 파일을 더블클릭하지 말고 웹 서버로 여세요.

```bash
cd datecourse
python3 -m http.server 8000
# → http://localhost:8000
```

폴더째로 아무 정적 호스팅(GitHub Pages, Netlify, Vercel 등)에 올리면 그대로 공개돼요.
위치 찾기와 오프라인 기능은 **https** 주소에서만 동작해요.

## 코스 추가·수정

`data/courses.json`의 `courses` 배열에 아래 모양으로 넣으면 바로 보여요.

```json
{
  "id": "seoul-seongsu",            // 겹치지 않는 영문 id (공유 주소에 쓰임)
  "region": "서울",                 // 17개 시·도 이름 중 하나
  "area": "성수",
  "title": "성수 숲길 산책 + 카페 투어",
  "summary": "한두 문장 소개",
  "with": ["date", "friends"],      // date / friends / family / solo / student(학생)
  "tags": ["카페", "산책", "노을"],  // 필터 태그: 야경 바다 카페 맛집 산책 전통 실내 비오는날 액티비티 노을 자연 시장
  "budget": 2,                      // 0: 무료, 1: 1인 3만 원 안팎, 2: 3~7만 원, 3: 7만 원 이상
  "hours": 5,
  "best": "오후",
  "details": [                      // 소소한 디테일: photo(사진 명소) time(좋은 시간) move(이동) tip(꿀팁) snack(간식)
    { "kind": "photo", "text": "서울숲 은행나무길은 가을 오후 햇살에 사진이 잘 나와요." }
  ],
  "stops": [
    { "name": "서울숲", "kind": "walk", "stay": 60, "tip": "한 줄 팁", "lat": 37.5444, "lng": 127.0374 }
  ]
}
```

`kind`: walk(산책) cafe(카페) food(먹거리) view(전망) culture(문화) activity(놀거리) shop(쇼핑) beach(바다) night(밤)

좌표는 대략적인 값이에요. 정확한 위치는 카카오맵 등에서 확인해 고쳐 주세요.
`python3 -m unittest discover -s scripts` 로 모양이 맞는지 확인할 수 있어요.

## 실제 가게 목록 띄우기 (카카오 지도 키, 선택)

'우리 동네'에서 노래방 같은 놀거리를 누르면 그 동네 근처 실제 가게(이름·주소·거리·전화·길찾기)가 가까운 순으로 떠요.
키가 없으면 그 자리에 카카오맵·네이버지도 검색 버튼이 나와요.

1. [카카오 개발자](https://developers.kakao.com)에서 애플리케이션 추가 → **JavaScript 키** 복사
2. 앱 설정 → 플랫폼 → **Web** 에 앱을 올린 사이트 주소 등록 (예: `https://<계정>.github.io`)
3. `index.html`의 `<meta name="kakao-js-key" content="">` 에 키 넣기

claude.ai 링크에서는 보안 정책 때문에 카카오에 접속할 수 없어서, 실제 가게 목록은 GitHub Pages 같은 진짜 주소에 올렸을 때만 떠요.
별점·영업시간은 카카오 API가 주지 않아서 '가게 정보'를 눌러 카카오맵에서 봐야 해요.

## 가게 사진 띄우기 (카카오 이미지 검색, 선택)

가게 목록의 가게마다 '가게 이름 + 구'로 카카오 이미지 검색을 해서 사진을 최대 4장 붙여요.
사진은 블로그 등에 올라온 검색 결과라 다른 가게 사진이 섞일 수 있고, 누르면 원래 글로 가요.

카카오 **REST API 키**는 비밀 키라 화면 코드에 넣지 않고 Supabase 함수(`supabase/functions/place-photos`)에만 둬요.

```bash
supabase secrets set KAKAO_REST_API_KEY=<REST API 키>
# 사이트 주소가 바뀌면 (쉼표로 여러 개)
supabase secrets set ALLOWED_ORIGINS=https://45516645sud-stack.github.io,http://localhost:8000
supabase functions deploy place-photos
```

함수 주소는 `index.html`의 `<meta name="nolco-photo-endpoint">` 에 들어 있어요. 비우면 사진 없이 동작해요.
함수 테스트: `deno test supabase/functions/place-photos/photos_test.ts`

## 사이트 공개 (GitHub Pages)

`.github/workflows/aiiairs-pages.yml` 이 AIIairs 사이트와 함께 놀코를 `https://45516645sud-stack.github.io/-/nolco/` 에 올려요.
GitHub Actions의 Pages 배포는 **기본 브랜치**에 합쳐진 뒤에만 돌아가요.
카카오 개발자 사이트의 Web 플랫폼 사이트 도메인에는 `https://45516645sud-stack.github.io` 를 등록하세요.

## 한국관광공사 추천코스 더하기 (선택)

기본 코스만으로는 시·군 단위까지 다 채우기 어려워서, 한국관광공사 **TourAPI의 추천코스(관광타입 25)** 를
모아 `data/tour_courses.json`으로 저장하는 수집기를 넣어 뒀어요. 앱은 이 파일이 있으면 기본 코스와 합쳐 보여 줘요.

1. [공공데이터포털](https://www.data.go.kr/data/15101578/openapi.do)에서 '한국관광공사_국문 관광정보 서비스_GW' 활용신청
2. 실행 (공공데이터포털 **디코딩** 키):
   ```bash
   DATA_GO_KR_KEY=발급받은키 python3 scripts/collect_tour.py --per-region 5
   ```
   - 개발 계정은 하루 1,000회 제한이라 `--max-calls`(기본 900)에서 멈추고, 받은 만큼 저장해요.
     매일 돌리면 바뀐 코스만 다시 받으면서 조금씩 채워져요.
   - 키가 없거나 한 건도 못 받으면 기존 파일을 그대로 둬요.
3. 수집 결과에는 출처(한국관광공사, 공공누리)가 상세 화면에 표시돼요.

## 다음에 해 볼 만한 것

- 카카오 로컬 API로 코스 근처 맛집·카페 실시간 추천
- 날씨 API(기상청)로 비 오는 날엔 실내 코스 먼저 보여 주기
- 계정·서버 저장(이 저장소의 Supabase)으로 찜 목록을 기기 사이에 동기화
