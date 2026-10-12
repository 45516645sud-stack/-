#!/usr/bin/env python3
"""팝업스토어 시험: 최근 블로그·카페 글에서 '지금 하는 팝업'을 얼마나 정확히 뽑아낼 수 있는지 본다.

    python scripts/check_popups.py            # 결과를 화면에 쓰고 popups.json 으로 저장

놀코 서버 함수(mode=posts, mode=places)로 묻기 때문에 키가 필요 없다. 앱 파일은 바꾸지 않는다.
  1) 지역별 '팝업' 검색어로 최근 글(60일 안)을 모은다
  2) 글 제목·요약에서 기간(10.3~10.19, '10/18까지' 등), 장소, 팝업 이름을 찾는다
     - 장소는 팝업 명소 목록(VENUES)과 먼저 맞춰 보고, 없으면 주소 모양 글자로
     - '이번 주', '가볼 만한' 같은 이름이 아닌 말은 거른다
  3) 같은 팝업(이름이 서로 포함되면)은 하나로 합친다
  4) 두 번 확인: 팝업 이름으로 다시 검색해서, 끝나는 날이 같은 글이 2개 이상이면 '확실'
  5) 장소를 카카오 장소 검색으로 찾되, 명소의 지역(예: 서울 영등포)과 맞는 주소만 쓴다
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_hoods import http_fetch  # noqa: E402

QUERIES = ["성수 팝업스토어", "성수동 팝업", "더현대 서울 팝업", "홍대 팝업스토어", "잠실 팝업스토어", "롯데월드몰 팝업",
           "여의도 팝업스토어", "강남 팝업스토어", "코엑스 팝업", "한남 팝업", "부산 팝업스토어", "대구 팝업스토어"]
MAX_DAYS = 120          # 이보다 긴 기간은 팝업이 아니라고 보고 버림
END_ONLY_POST_DAYS = 30  # '~까지'만 적힌 글은 이만큼 최근 글만 믿는다

# 팝업 명소: (글에 나오는 이름들, 보여 줄 이름, 장소 검색어, 주소가 이걸로 시작해야 함)
VENUES = [
    (["더현대 서울", "더현대서울", "더 현대 서울", "더현대 여의도", "더현대"], "더현대 서울", "더현대 서울", "서울 영등포"),
    (["더현대 대구", "더현대대구"], "더현대 대구", "더현대 대구", "대구 중구"),
    (["롯데월드몰", "롯데월드타워"], "롯데월드몰", "롯데월드몰", "서울 송파"),
    (["롯데백화점 잠실", "롯데 잠실", "잠실 롯데백화점"], "롯데백화점 잠실점", "롯데백화점 잠실점", "서울 송파"),
    (["스타필드 코엑스", "코엑스몰", "코엑스"], "코엑스", "코엑스몰", "서울 강남"),
    (["무신사 메가스토어 성수", "무신사 메가스토어"], "무신사 메가스토어 성수", "무신사 메가스토어 성수", "서울 성동"),
    (["무신사 스토어 성수", "무신사 성수"], "무신사 스토어 성수", "무신사 스토어 성수", "서울 성동"),
    (["무신사 스탠다드 성수"], "무신사 스탠다드 성수", "무신사 스탠다드 성수", "서울 성동"),
    (["무신사 스탠다드 한남"], "무신사 스탠다드 한남", "무신사 스탠다드 한남", "서울 용산"),
    (["무신사 스페이스 한남"], "무신사 스페이스 한남", "무신사 스페이스 한남", "서울 용산"),
    (["올리브영N 성수", "올리브영 N 성수", "올리브영N성수"], "올리브영N 성수", "올리브영N 성수", "서울 성동"),
    (["신세계 강남", "신세계백화점 강남"], "신세계백화점 강남점", "신세계백화점 강남점", "서울 서초"),
    (["신세계 센텀", "센텀시티"], "신세계 센텀시티", "신세계센텀시티", "부산 해운대"),
    (["현대백화점 판교", "판교 현대"], "현대백화점 판교점", "현대백화점 판교점", "경기 성남"),
    (["스타필드 하남"], "스타필드 하남", "스타필드 하남", "경기 하남"),
    (["스타필드 고양"], "스타필드 고양", "스타필드 고양", "경기 고양"),
    (["KREAM 도산", "크림 도산"], "KREAM 도산 플래그십", "KREAM 도산", "서울 강남"),
    (["케이팝 스퀘어 홍대", "케이팝스퀘어 홍대"], "케이팝스퀘어 홍대", "케이팝스퀘어 홍대", "서울 마포"),
    (["삼정타워"], "서면 삼정타워", "삼정타워", "부산 부산진"),
    (["스페이스비"], "스페이스비 (연남)", "스페이스비 연남", "서울 마포"),
    (["연무장길"], "성수 연무장길", "연무장길", "서울 성동"),
]
# 명소가 안 보일 때 동네만이라도
AREAS = [("성수", "서울 성동구 성수동"), ("서울숲", "서울 성동구 성수동"), ("연남", "서울 마포구 연남동"), ("홍대", "서울 마포구 홍대"),
         ("한남", "서울 용산구 한남동"), ("도산", "서울 강남구 신사동"), ("압구정", "서울 강남구 압구정동"), ("가로수길", "서울 강남구 신사동"),
         ("잠실", "서울 송파구 잠실동"), ("여의도", "서울 영등포구 여의도동"), ("명동", "서울 중구 명동"), ("서면", "부산 부산진구 서면"),
         ("동성로", "대구 중구 동성로")]

_D = r"(?:(20\d\d)\s*[.\-/년]\s*)?(\d{1,2})\s*[.\-/월]\s*(\d{1,2})\s*일?\.?\s*(?:\([^)]{1,4}\))?"
RANGE = re.compile(_D + r"\s*[~∼～\-–—]\s*(?:(20\d\d)\s*[.\-/년]\s*)?(?:(\d{1,2})\s*[.\-/월]\s*)?(\d{1,2})\s*일?")
UNTIL = re.compile(r"(?:[~∼～]\s*)?(?:(20\d\d)\s*[.\-/년]\s*)?(\d{1,2})\s*[.\-/월]\s*(\d{1,2})\s*일?\s*(?:\([^)]{1,4}\))?\s*(?:까지|종료|마감)"
                   r"|[~∼～]\s*(?:(20\d\d)\s*[.\-/년]\s*)?(\d{1,2})\s*[./월]\s*(\d{1,2})\s*일?(?!\s*[~∼～\-–—\d])")
ADDRESS = re.compile(r"(?:서울|부산|대구|인천|광주|대전|울산|경기|제주)\S*\s+\S+(?:구|군|시)\s+\S+(?:로|길)\s*\d+(?:-\d+)?")
PLACE = re.compile(r"(?:장소|위치|📍|📌)\s*[:：]?\s*([^\n|,·/()\[\]📅📆⏰]{3,60})")
NAME = re.compile(r"([0-9A-Za-z가-힣&'’ .x×]{2,30}?)\s*(?:팝업\s*스토어|팝업스토어|팝업|POP-?UP)", re.I)
QUOTED = re.compile(r"['‘\"“「『]([^'’\"”」』]{2,25})['’\"”」』]")
NOISE = re.compile(r"20\d\d년?|\[[^\]]*\]|【[^】]*】|<[^>]*>|\([^)]*\)|[#|]|후기|방문|리뷰|솔직|내돈내산|오픈런|주말|데이트|추천|가볼만한곳"
                   r"|서울|성수동?|더\s?현대|홍대|잠실|여의도|강남|부산|대구|코엑스|한남|롯데월드몰|롯데백화점|신세계백화점|현대백화점|백화점|점\b")
# 팝업 이름이 아닌 말이 들어 있으면 버린다
NOT_NAME = re.compile(r"주차|이번\s?주|가볼|까지|추천|정리|총정리|일정|무료|예약|오픈|요즘|핫플|모음|리스트|BEST|TOP|\d+곳|\d+월|이달|다음\s?주|근처|코스|투어|나들이")


def _date(y, m, d, posted: date) -> date | None:
    try:
        return date(int(y or posted.year), int(m), int(d))
    except ValueError:
        return None


def period(text: str, posted: date) -> tuple[date | None, date] | None:
    """(시작, 끝). 끝나는 날만 적혀 있으면 시작은 None"""
    for m in RANGE.finditer(text):
        y1, m1, d1, y2, m2, d2 = m.groups()
        start = _date(y1, m1, d1, posted)
        end = _date(y2 or (start.year if start else None), m2 or m1, d2, posted)
        if not start or not end:
            continue
        if end < start:
            end = _date(end.year + 1, end.month, end.day, posted)
        # 글 쓴 해를 기준으로 했는데 글보다 반년 넘게 앞이면 다음 해 일정
        if (posted - end).days > 180:
            start, end = _date(start.year + 1, start.month, start.day, posted), _date(end.year + 1, end.month, end.day, posted)
        if start and end and 0 <= (end - start).days <= MAX_DAYS:
            return start, end
    for m in UNTIL.finditer(RANGE.sub(" ", text)):   # 위에서 버린 '시작~끝'을 '~끝'으로 다시 읽지 않게
        g = m.groups()
        y, mo, d = (g[0], g[1], g[2]) if g[1] else (g[3], g[4], g[5])
        end = _date(y, mo, d, posted)
        if end and (posted - end).days > 180:
            end = _date(end.year + 1, end.month, end.day, posted)
        if end and -3 <= (end - posted).days <= MAX_DAYS:
            return None, end
    return None


def venue_of(text: str) -> tuple[str, str, str] | None:
    """(보여 줄 이름, 장소 검색어, 지역) — 명소 목록에서. 글자가 긴 것부터 맞춘다"""
    flat = [(alias, v) for v in VENUES for alias in v[0]]
    for alias, v in sorted(flat, key=lambda x: -len(x[0])):
        if alias.replace(" ", "") in text.replace(" ", ""):
            return v[1], v[2], v[3]
    return None


def place_of(text: str) -> tuple[str, str, str]:
    """(보여 줄 장소, 장소 검색어, 주소가 시작해야 할 글자)"""
    v = venue_of(text)
    if v:
        return v
    a = ADDRESS.search(text)
    if a:
        return a.group(0), a.group(0), a.group(0).split()[0][:2]
    m = PLACE.search(text)
    if m:
        p = re.split(r"\s(?:기간|운영|일정|시간|주소)\b", m.group(1))[0].strip(" :-.")
        if 3 <= len(p) <= 30 and not NOT_NAME.search(p):
            return p, p, ""
    for word, area in AREAS:
        if word in text:
            return area, "", ""
    return "", "", ""


def name_of(title: str) -> str:
    q = QUOTED.search(title)
    cands = [q.group(1)] if q and "팝업" not in q.group(1) else []
    m = NAME.search(title)
    if m:
        cands.append(m.group(1))
    for c in cands:
        n = NOISE.sub(" ", c)
        n = re.sub(r"\s+", " ", n).strip(" .-x×&")
        if len(n.replace(" ", "")) >= 2 and not NOT_NAME.search(n) and not re.fullmatch(r"[A-Za-z]{1,3}|\d+", n):
            return n
    return ""


def key_of(name: str) -> str:
    return re.sub(r"[\s.'’&x×]", "", name).lower()


def merge(found: list[dict]) -> list[list[dict]]:
    """이름이 서로 포함되는 것(3글자 이상)끼리 한 팝업으로"""
    groups: list[tuple[str, list[dict]]] = []
    for f in sorted(found, key=lambda f: len(key_of(f["name"]))):
        k = key_of(f["name"])
        for i, (gk, items) in enumerate(groups):
            if len(gk) >= 3 and (gk in k or k in gk):
                items.append(f)
                break
        else:
            groups.append((k, [f]))
    return [items for _, items in groups]


def posts(q: str, pages=(1,)) -> list[dict]:
    out = []
    for page in pages:
        try:
            got = http_fetch({"mode": "posts", "q": q, "page": page}).get("posts", [])
        except Exception as e:  # noqa: BLE001
            print(f"! {q} {page}쪽 실패: {e}")
            break
        out += got
        if len(got) < 20:
            break
    return out


def geocode(query: str, prefix: str) -> str:
    if not query:
        return ""
    try:
        hits = http_fetch({"mode": "places", "q": query, "size": 5}).get("places", [])
    except Exception:  # noqa: BLE001
        return ""
    for h in hits:
        if not prefix or h["address"].startswith(prefix):
            return h["address"]
    return ""


def read(p: dict) -> dict | None:
    text = f"{p['title']} {p['text']}"
    posted = date.fromisoformat(p["date"])
    per = period(text, posted)
    if not per:
        return None
    if per[0] is None and (date.today() - posted).days > END_ONLY_POST_DAYS:
        return None
    place, query, prefix = place_of(text)
    return {**p, "name": name_of(p["title"]), "start": per[0], "end": per[1], "place": place, "pq": query, "pp": prefix}


def main() -> int:
    today = date.today()
    all_posts, seen = [], set()
    for q in QUERIES:
        for p in posts(q, (1, 2, 3)):
            if p["url"] not in seen:
                seen.add(p["url"])
                all_posts.append({**p, "q": q})
    print(f"모은 글: {len(all_posts)}개 (검색어 {len(QUERIES)}개)")

    found = [f for f in map(read, all_posts) if f]
    named = [f for f in found if f["name"]]
    print(f"기간을 찾은 글: {len(found)}개 ({len(found) * 100 // max(1, len(all_posts))}%), 그중 팝업 이름까지 찾은 글: {len(named)}개")

    popups = []
    for items in merge(named):
        name = Counter(f["name"] for f in items).most_common(1)[0][0]
        # 두 번 확인: 팝업 이름으로 다시 검색해 같은 글 묶음에 더한다
        extra = [r for r in map(read, posts(f"{name} 팝업")) if r and r["url"] not in {i["url"] for i in items}]
        pool = items + [r for r in extra if key_of(name)[:3] in key_of(r["title"])]
        ends = Counter(f["end"] for f in pool)
        end, agree = ends.most_common(1)[0]
        # 끝나는 날이 하루 차이인 것도 같은 걸로
        agree += sum(n for e, n in ends.items() if e != end and abs((e - end).days) <= 1)
        starts = Counter(f["start"] for f in pool if f["start"] and f["start"] <= end)
        start = starts.most_common(1)[0][0] if starts else None
        places = Counter((f["place"], f["pq"], f["pp"]) for f in pool if f["place"])
        place, pq, pp = places.most_common(1)[0][0] if places else ("", "", "")
        popups.append({"name": name, "start": start, "end": end, "place": place, "pq": pq, "pp": pp, "agree": agree,
                       "posts": len(pool), "url": sorted(pool, key=lambda f: f["date"], reverse=True)[0]["url"]})

    now = [p for p in popups if (p["start"] or today) <= today <= p["end"]]
    sure = [p for p in now if p["agree"] >= 2]
    unsure = [p for p in now if p["agree"] < 2]
    soon = [p for p in popups if p["start"] and today < p["start"] <= today + timedelta(days=14) and p["agree"] >= 2]
    print(f"팝업으로 합친 것: {len(popups)}개 → 지금 하는 것 {len(now)}개 (확실 {len(sure)} · 글 하나뿐 {len(unsure)}), 2주 안에 시작(확실) {len(soon)}개\n")

    for p in sure + unsure + soon:
        p["address"] = geocode(p["pq"], p["pp"]) if p["pq"] else ""

    def show(p, mark):
        when = f"{p['start']:%m.%d}~{p['end']:%m.%d}" if p["start"] else f"~{p['end']:%m.%d}"
        print(f"{mark} {p['name']}  {when}  (같은 기간 글 {p['agree']}개 / 전체 {p['posts']}개)")
        print(f"    장소: {p['place'] or '(못 찾음)'}  →  주소: {p['address'] or '(못 찾음)'}")
        print(f"    {p['url']}")

    print("=== 지금 하는 팝업 · 확실 (글 2개 이상이 같은 기간) ===")
    for p in sorted(sure, key=lambda p: (-p["agree"], p["end"])):
        show(p, "●")
    print("\n=== 지금 하는 팝업 · 글 하나뿐 (앱에는 안 넣을 것) ===")
    for p in sorted(unsure, key=lambda p: p["end"])[:25]:
        show(p, "○")
    print("\n=== 2주 안에 시작 (확실) ===")
    for p in sorted(soon, key=lambda p: p["start"]):
        show(p, "◇")

    Path("popups.json").write_text(json.dumps({"today": str(today), "posts": len(all_posts), "found": len(found),
                                               "sure": sure, "unsure": unsure, "soon": soon},
                                              ensure_ascii=False, default=str, indent=1), encoding="utf-8")
    print("\n저장: popups.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
