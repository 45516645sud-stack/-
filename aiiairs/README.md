# AIIairs: 전국 박람회·소공연 통합 일정

정적 사이트 하나(`index.html`)와, 매일 일정을 모아 `data/fairs.json`을 만드는 수집기로 이루어져 있어요.
이 폴더(`aiiairs/`)를 그대로 웹 서버에 올리면 돼요.

```
aiiairs/
├─ index.html             페이지. data/fairs.json 을 읽고, 없으면 안에 든 예시 일정을 보여줌
├─ data/
│  ├─ fairs.json          수집 결과 (자동 생성, 직접 고치지 않음)
│  └─ manual.csv          박람회 등 직접 넣는 일정
├─ img/                   포스터가 없을 때 쓰는 그림 (Fluent Emoji, MIT)
└─ scripts/
   ├─ collect.py          수집기 (Python 표준 라이브러리만 사용)
   ├─ test_collect.py     수집기 테스트
   └─ fixtures/           테스트용 예시 응답 (가상 데이터)
```

## 일정이 들어오는 길

| 출처 | 무엇 | 필요한 것 |
|---|---|---|
| `data/manual.csv` | 박람회처럼 공개 API가 없는 행사 | 없음 (파일만 채우면 됨) |
| [KOPIS 공연예술통합전산망](https://kopis.or.kr/por/cs/openapi/openApiInfo.do?menuId=MNU_00074) | 연극·뮤지컬·콘서트 등 공연 | `KOPIS_API_KEY` |
| [한국문화정보원 한눈에보는문화정보](https://www.data.go.kr/data/15138937/openapi.do) | 공연·전시 | `DATA_GO_KR_KEY` (공공데이터포털 **디코딩** 키) |

같은 행사가 여러 출처에 있으면 한 번만 남기며, 위 표의 순서대로 먼저 온 출처를 우선해요.
키가 없는 출처는 건너뛰고, 모든 출처에서 한 건도 못 얻으면 기존 `fairs.json`을 그대로 둬요.

## 처음 설정

1. **API 키 신청**
   - KOPIS: kopis.or.kr → 고객지원 → Open API → 인증키 신청
   - 한국문화정보원: data.go.kr → '한국문화정보원_한눈에보는문화정보조회서비스' → 활용신청
2. **GitHub에 키 등록**: 저장소 Settings → Secrets and variables → Actions → New repository secret
   - `KOPIS_API_KEY`, `DATA_GO_KR_KEY`
3. **자동 실행**: `.github/workflows/aiiairs-collect.yml`이 매일 05:43(한국 시간)에 돌아요.
   Actions 탭에서 'AIIairs 일정 수집' → Run workflow 로 바로 돌려볼 수도 있어요.
   GitHub Actions의 예약 실행은 **기본 브랜치**에 있는 워크플로만 동작해요.
4. **예시 일정 끄기**: `data/fairs.json`이 생기면 페이지가 자동으로 실제 일정을 보여주고,
   상단의 '예시 일정' 표시 대신 갱신 시각과 출처를 보여줘요.

## 박람회 직접 넣기 (`data/manual.csv`)

엑셀·구글 시트에서 아래 열로 만든 뒤 CSV(UTF-8)로 저장하면 돼요. 예시는 `scripts/fixtures/manual_example.csv`.

| 열 | 예 | 설명 |
|---|---|---|
| 행사명 | 서울 리빙 디자인 페어 | 필수 |
| 분류 | 리빙·인테리어 | 식음료, 리빙·인테리어, 웨딩·육아, 도서·문화, 아트·공예, 테크·IT, 취업·교육, 여행·레저, 반려동물, 뷰티·패션, 산업·비즈니스, 공연·소극장 |
| 지역 | 서울 | 서울, 경기, 부산 … (비우면 장소에서 추측) |
| 장소 | 코엑스 A홀 | |
| 시작일 / 종료일 | 2026-11-05 | `2026-11-05`, `2026.11.05`, `20261105` 모두 됨 |
| 관람료 | 15000 / 무료 | 비우면 '관람료 확인'으로 표시 |
| 설명 | 가구와 조명 브랜드… | 160자 안쪽 |
| 포스터 | https://… | 실제 포스터 이미지 주소 (https) |
| 링크 | https://… | 공식 페이지 |
| 메모 | 사전등록 시 무료 | 관람료 옆에 표시 |
| 태그 | 데이트/쇼핑 | 취향 검색용, `/`로 구분 |

국내 박람회 일정은 [한국전시산업진흥회 국내전시 일정](https://www.akei.or.kr/bbs/board.php?bo_table=schedule)과
각 전시장(코엑스·킨텍스·벡스코 등) 공지를 참고해 옮겨 적는 것을 권해요.

## 직접 돌려보기

```bash
python3 aiiairs/scripts/collect.py --fixtures --manual aiiairs/scripts/fixtures/manual_example.csv --out /tmp/fairs.json  # 네트워크 없이 확인
KOPIS_API_KEY=... DATA_GO_KR_KEY=... python3 aiiairs/scripts/collect.py                                                  # 실제 수집
python3 -m unittest aiiairs/scripts/test_collect.py                                                                        # 테스트
```

주요 옵션: `--days 180`(오늘부터 며칠 뒤까지), `--max-kopis 400`, `--kopis-detail 150`(요금·줄거리를 가져올 건수), `--max-culture 400`.

## 알아둘 점

- 페이지는 `fetch('data/fairs.json')`로 읽기 때문에 웹 서버에 올려야 해요. 파일을 더블클릭해 열면 예시 일정이 나와요.
- 공공 API의 응답 형식은 문서를 기준으로 맞췄지만, 실제 키로는 아직 호출해 보지 못했어요.
  첫 실행 로그에서 건수가 0이거나 오류가 나오면 응답 필드 이름을 확인해 `collect.py`의 `kopis_item`, `culture_item`을 맞춰 주세요.
- KOPIS·공공데이터는 이용 시 출처 표시가 필요해서, 페이지 아래에 출처를 자동으로 적어요.
