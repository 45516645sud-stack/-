#!/usr/bin/env python3
"""팝업스토어 시험: 최근 블로그·카페 글에서 '지금 하는 팝업'을 얼마나 뽑아낼 수 있는지 본다.

    python scripts/check_popups.py            # 결과를 화면에 쓰고 popups.json 으로 저장

놀코 서버 함수(mode=posts, mode=places)로 묻기 때문에 키가 필요 없다. 앱 파일은 바꾸지 않는다.
  1) 지역별 '팝업' 검색어로 최근 글(60일 안)을 모은다
  2) 글 제목·요약에서 기간(10.3~10.19 등)과 장소(📍, 장소: 등)를 찾는다
  3) 오늘이 기간 안에 있는 것만 '지금 하는 팝업'으로, 이름이 같은 것은 하나로 합친다
  4) 장소를 카카오 장소 검색으로 찾아 주소를 붙인다
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_hoods import http_fetch  # noqa: E402

QUERIES = ["성수 팝업스토어", "성수동 팝업", "더현대 서울 팝업", "홍대 팝업스토어", "잠실 팝업스토어", "롯데월드몰 팝업",
           "여의도 팝업스토어", "강남 팝업스토어", "코엑스 팝업", "한남 팝업", "부산 팝업스토어", "대구 팝업스토어"]
MAX_DAYS = 120   # 이보다 긴 기간은 팝업이 아니라고 보고 버림
SPOTS = ["더현대 서울", "더현대서울", "롯데월드몰", "롯데월드타워", "코엑스", "스타필드", "연무장길", "성수동", "성수", "홍대", "연남",
         "합정", "잠실", "여의도", "한남", "압구정", "도산", "가로수길", "명동", "신세계", "현대백화점", "롯데백화점", "부산", "대구"]

_D = r"(?:(20\d\d)\s*[.\-/년]\s*)?(\d{1,2})\s*[.\-/월]\s*(\d{1,2})\s*일?\.?\s*(?:\([^)]{1,4}\))?"
RANGE = re.compile(_D + r"\s*[~∼～\-–—]\s*(?:(20\d\d)\s*[.\-/년]\s*)?(?:(\d{1,2})\s*[.\-/월]\s*)?(\d{1,2})\s*일?")
PLACE = re.compile(r"(?:장소|위치|주소|📍|📌)\s*[:：]?\s*([^\n|,·/()\[\]]{3,40})")
NAME = re.compile(r"([0-9A-Za-z가-힣&'’ .x×]{2,30}?)\s*(?:팝업\s*스토어|팝업스토어|팝업)")
NOISE = re.compile(r"20\d\d년?|\[[^\]]*\]|【[^】]*】|<[^>]*>|\([^)]*\)|[#]|후기|방문|리뷰|솔직|내돈내산|오픈런|주말|데이트|추천|가볼만한곳|서울|성수동?|더현대|홍대|잠실|여의도|강남|부산|대구|코엑스|한남|롯데월드몰")


def period(text: str, posted: date) -> tuple[date, date] | None:
    for m in RANGE.finditer(text):
        y1, m1, d1, y2, m2, d2 = m.groups()
        try:
            y1 = int(y1 or posted.year)
            start = date(y1, int(m1), int(d1))
            end = date(int(y2 or y1), int(m2 or m1), int(d2))
        except ValueError:
            continue
        if end < start:
            try:
                end = end.replace(year=end.year + 1)
            except ValueError:
                continue
        # 글 쓴 해를 기준으로 했는데 글보다 반년 넘게 앞이면 다음 해 일정
        if (posted - end).days > 180:
            start, end = start.replace(year=start.year + 1), end.replace(year=end.year + 1)
        if 0 <= (end - start).days <= MAX_DAYS:
            return start, end
    return None


def place_of(text: str) -> str:
    m = PLACE.search(text)
    if m:
        return m.group(1).strip(" :-")
    for s in SPOTS:
        if s in text:
            return s
    return ""


def name_of(title: str) -> str:
    m = NAME.search(title)
    if not m:
        return ""
    n = NOISE.sub(" ", m.group(1))
    n = re.sub(r"\s+", " ", n).strip(" .-x×")
    return n if len(n.replace(" ", "")) >= 2 else ""


def main() -> int:
    today = date.today()
    posts, seen = [], set()
    for q in QUERIES:
        for page in (1, 2, 3):
            try:
                got = http_fetch({"mode": "posts", "q": q, "page": page}).get("posts", [])
            except Exception as e:  # noqa: BLE001
                print(f"! {q} {page}쪽 실패: {e}")
                break
            for p in got:
                if p["url"] not in seen:
                    seen.add(p["url"])
                    posts.append({**p, "q": q})
            if len(got) < 20:
                break
    print(f"모은 글: {len(posts)}개 (검색어 {len(QUERIES)}개)")

    found, no_period, no_name = [], [], 0
    for p in posts:
        text = f"{p['title']} {p['text']}"
        posted = date.fromisoformat(p["date"])
        per = period(text, posted)
        name = name_of(p["title"])
        if not name:
            no_name += 1
        if not per:
            no_period.append(p)
            continue
        found.append({**p, "name": name, "start": per[0], "end": per[1], "place": place_of(text)})
    print(f"기간을 찾은 글: {len(found)}개 ({len(found) * 100 // max(1, len(posts))}%), 이름을 못 찾은 글: {no_name}개")

    groups: dict[str, list[dict]] = defaultdict(list)
    for f in found:
        if f["name"]:
            groups[re.sub(r"[\s.'’]", "", f["name"]).lower()].append(f)
    popups = []
    for key, fs in groups.items():
        start, end = Counter((f["start"], f["end"]) for f in fs).most_common(1)[0][0]
        places = Counter(f["place"] for f in fs if f["place"])
        popups.append({"name": Counter(f["name"] for f in fs).most_common(1)[0][0], "start": start, "end": end,
                       "place": places.most_common(1)[0][0] if places else "", "posts": len(fs),
                       "url": sorted(fs, key=lambda f: f["date"], reverse=True)[0]["url"], "q": fs[0]["q"]})
    now = [p for p in popups if p["start"] <= today <= p["end"]]
    soon = [p for p in popups if today < p["start"] <= today + timedelta(days=14)]
    print(f"팝업 이름으로 합친 것: {len(popups)}개 → 지금 하는 것 {len(now)}개, 2주 안에 시작 {len(soon)}개\n")

    for p in sorted(now, key=lambda p: -p["posts"])[:40]:
        addr = ""
        if p["place"]:
            try:
                hit = http_fetch({"mode": "places", "q": p["place"], "size": 1}).get("places", [])
                addr = hit[0]["address"] if hit else ""
            except Exception:  # noqa: BLE001
                addr = ""
        p["address"] = addr
        print(f"● {p['name']}  {p['start']:%m.%d}~{p['end']:%m.%d}  글 {p['posts']}개")
        print(f"    장소: {p['place'] or '(못 찾음)'}  →  주소: {addr or '(못 찾음)'}   [{p['q']}]")
        print(f"    {p['url']}")

    print("\n— 2주 안에 시작 —")
    for p in sorted(soon, key=lambda p: p["start"])[:15]:
        print(f"○ {p['name']}  {p['start']:%m.%d}~{p['end']:%m.%d}  {p['place']}")

    print("\n— 기간을 못 찾은 글 예시 (왜 못 찾았는지 보려고) —")
    for p in no_period[:15]:
        print(f"· {p['title'][:60]}  |  {p['text'][:90]}")

    out = Path("popups.json")
    out.write_text(json.dumps({"today": str(today), "posts": len(posts), "found": len(found),
                               "now": now, "soon": soon}, ensure_ascii=False, default=str, indent=1), encoding="utf-8")
    print(f"\n저장: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
