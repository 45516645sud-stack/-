#!/usr/bin/env python3
"""한국관광공사 TourAPI '추천코스'(관광타입 25)를 모아 data/tour_courses.json 을 만든다.

Python 표준 라이브러리만 쓴다.

    DATA_GO_KR_KEY=<공공데이터포털 디코딩 키> python scripts/collect_tour.py
    python scripts/collect_tour.py --per-region 4 --max-calls 600

개발 계정 키는 하루 1,000회까지라서 --max-calls 로 호출 수를 묶어 둔다. 호출 수가 바닥나면
그때까지 받은 코스와 지난번 결과를 합쳐서 저장하므로, 매일 돌리면 조금씩 채워진다.
한 건도 못 받으면 기존 파일을 건드리지 않는다.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

BASE = "https://apis.data.go.kr/B551011/KorService2"
APP_NAME = "datecourse"
KST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent

# TourAPI 지역코드 → 앱의 지역 이름
AREAS = {
    "1": "서울", "2": "인천", "3": "대전", "4": "대구", "5": "광주", "6": "부산", "7": "울산", "8": "세종",
    "31": "경기", "32": "강원", "33": "충북", "34": "충남", "35": "경북", "36": "경남", "37": "전북", "38": "전남", "39": "제주",
}

# 코스 분류(cat2) → 누구와 / 분위기
CATEGORY = {
    "C0112": (["family", "date"], ["가족"]),
    "C0113": (["solo"], ["혼자"]),
    "C0114": (["date", "solo"], ["힐링", "자연"]),
    "C0115": (["friends", "date"], ["산책"]),
    "C0116": (["friends", "family"], ["캠핑", "자연"]),
    "C0117": (["date", "friends"], ["맛집"]),
}

# 장소 이름·설명에 이런 말이 있으면 분위기 태그를 붙인다
KEYWORD_TAGS = {
    "바다": ["해수욕장", "해변", "바다", "항구", "포구", "해안"],
    "야경": ["야경", "야간", "밤"],
    "전통": ["한옥", "궁", "사찰", "향교", "서원", "민속", "성곽", "고택"],
    "시장": ["시장"],
    "카페": ["카페", "커피"],
    "자연": ["숲", "수목원", "계곡", "산림", "휴양림", "국립공원"],
    "실내": ["박물관", "미술관", "전시관", "과학관", "아쿠아리움"],
}

Fetcher = Callable[[str], str]


class CallBudget(Exception):
    """오늘 쓸 호출 수를 다 썼다."""


class Client:
    def __init__(self, key: str, max_calls: int, fetch: Fetcher | None = None, pause: float = 0.1):
        self.key = key
        self.left = max_calls
        self.calls = 0
        self.fetch = fetch or http_get
        self.pause = pause

    def get(self, op: str, **params: Any) -> list[dict]:
        if self.left <= 0:
            raise CallBudget()
        self.left -= 1
        self.calls += 1
        q = {"serviceKey": self.key, "MobileOS": "ETC", "MobileApp": APP_NAME, "_type": "json", **params}
        url = f"{BASE}/{op}?{urllib.parse.urlencode(q)}"
        text = self.fetch(url)
        if self.pause:
            time.sleep(self.pause)
        return parse_items(text, op)


def http_get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": f"{APP_NAME}/1.0"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=20) as res:
                return res.read().decode("utf-8")
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("unreachable")


def parse_items(text: str, op: str) -> list[dict]:
    """TourAPI 응답에서 item 목록만 꺼낸다. 키 오류 등은 JSON 대신 XML 로 오기도 한다."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        msg = re.search(r"<(?:returnAuthMsg|resultMsg)>([^<]+)<", text)
        raise RuntimeError(f"{op}: JSON 이 아닌 응답 ({msg.group(1) if msg else text[:120]!r})")
    resp = data.get("response") or {}
    code = (resp.get("header") or {}).get("resultCode", "0000")
    if code not in ("0000", "00"):
        raise RuntimeError(f"{op}: resultCode={code} {(resp.get('header') or {}).get('resultMsg', '')}")
    items = ((resp.get("body") or {}).get("items")) or {}
    if not isinstance(items, dict):  # 결과가 없으면 "" 로 온다
        return []
    item = items.get("item") or []
    return [item] if isinstance(item, dict) else list(item)


def clean(text: Any, limit: int = 0) -> str:
    s = html.unescape(re.sub(r"<[^>]+>", " ", str(text or "")))
    s = re.sub(r"\s+", " ", s).strip()
    if limit and len(s) > limit:
        cut = s[:limit]
        end = max(cut.rfind(". "), cut.rfind("다. "), cut.rfind("요. "))
        s = (cut[: end + 1] if end > limit // 2 else cut.rstrip() + "…").strip()
    return s


def to_float(v: Any) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f else None


def parse_hours(taketime: str) -> float | None:
    t = clean(taketime)
    if not t:
        return None
    if "박" in t:
        return None  # 숙박 코스는 시간으로 나타내지 않는다
    if "당일" in t or "하루" in t:
        return 8
    m = re.search(r"(\d+(?:\.\d+)?)\s*시간", t)
    if m:
        return float(m.group(1)) if "." in m.group(1) else int(m.group(1))
    return None


def guess_tags(texts: list[str]) -> list[str]:
    joined = " ".join(texts)
    return [tag for tag, words in KEYWORD_TAGS.items() if any(w in joined for w in words)]


def build_course(item: dict, region: str, subs: list[dict], common: dict, intro: dict,
                 coords: dict[str, tuple[float, float]]) -> dict | None:
    stops = []
    for s in sorted(subs, key=lambda x: int(x.get("subnum") or 0)):
        name = clean(s.get("subname"))
        if not name:
            continue
        cid = str(s.get("subcontentid") or "")
        stop: dict[str, Any] = {"name": name, "kind": "", "stay": 0, "tip": clean(s.get("subdetailoverview"), 90)}
        if cid:
            stop["cid"] = cid
            if cid in coords:
                stop["lat"], stop["lng"] = coords[cid]
        stops.append(stop)
    if len(stops) < 2:
        return None

    # 코스 대표 좌표는 첫 장소에 없을 때만 빌려 쓴다
    lat, lng = to_float(item.get("mapy")), to_float(item.get("mapx"))
    if lat and lng and "lat" not in stops[0]:
        stops[0]["lat"], stops[0]["lng"] = lat, lng

    who, tags = CATEGORY.get(str(item.get("cat2") or ""), (["date", "friends"], []))
    tags = list(dict.fromkeys(tags + guess_tags([s["name"] + " " + s["tip"] for s in stops])))
    title = clean(item.get("title"))
    summary = clean(common.get("overview"), 110) or " → ".join(s["name"] for s in stops)
    area = clean(item.get("addr1")).split(" ")[1:2]
    return {
        "id": f"tour-{item['contentid']}",
        "region": region,
        "area": area[0] if area else "",
        "title": title,
        "summary": summary,
        "with": who,
        "tags": tags,
        "budget": 2,
        "hours": parse_hours(intro.get("taketime", "")),
        "best": "",
        "stops": stops,
        "source": "tourapi",
        "image": item.get("firstimage") or "",
        "modified": str(item.get("modifiedtime") or ""),
    }


def known_coords(previous: list[dict]) -> dict[str, tuple[float, float]]:
    out = {}
    for c in previous:
        for s in c.get("stops", []):
            if s.get("cid") and to_float(s.get("lat")) and to_float(s.get("lng")):
                out[s["cid"]] = (s["lat"], s["lng"])
    return out


def collect(client: Client, per_region: int, previous: list[dict], log=print) -> list[dict]:
    coords = known_coords(previous)
    prev_by_id = {c["id"]: c for c in previous}
    fresh: dict[str, dict] = {}
    try:
        for code, region in AREAS.items():
            items = client.get("areaBasedList2", contentTypeId=25, areaCode=code, numOfRows=per_region, pageNo=1, arrange="Q")
            log(f"{region}: 코스 {len(items)}개")
            for item in items:
                cid = str(item.get("contentid") or "")
                if not cid:
                    continue
                old = prev_by_id.get(f"tour-{cid}")
                if old and old.get("modified") and old.get("modified") == str(item.get("modifiedtime") or ""):
                    fresh[old["id"]] = old  # 바뀐 게 없으면 다시 묻지 않는다
                    continue
                subs = client.get("detailInfo2", contentId=cid, contentTypeId=25)
                common = (client.get("detailCommon2", contentId=cid) or [{}])[0]
                intro = (client.get("detailIntro2", contentId=cid, contentTypeId=25) or [{}])[0]
                for s in subs:
                    sid = str(s.get("subcontentid") or "")
                    if sid and sid not in coords:
                        try:
                            got = (client.get("detailCommon2", contentId=sid) or [{}])[0]
                        except RuntimeError as e:
                            log(f"  좌표 건너뜀 {sid}: {e}")
                            continue
                        la, ln = to_float(got.get("mapy")), to_float(got.get("mapx"))
                        if la and ln:
                            coords[sid] = (la, ln)
                course = build_course(item, region, subs, common, intro, coords)
                if course:
                    fresh[course["id"]] = course
    except CallBudget:
        log(f"호출 한도에 닿아 여기서 멈춰요 (사용 {client.calls}회)")
    # 이번에 못 다시 받은 지난 코스는 그대로 둔다
    for c in previous:
        fresh.setdefault(c["id"], c)
    return sorted(fresh.values(), key=lambda c: (list(AREAS.values()).index(c["region"]) if c["region"] in AREAS.values() else 99, c["id"]))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(ROOT / "data" / "tour_courses.json"))
    ap.add_argument("--per-region", type=int, default=5, help="지역마다 받을 코스 수 (기본 5)")
    ap.add_argument("--max-calls", type=int, default=900, help="이번 실행에서 쓸 최대 호출 수 (기본 900)")
    args = ap.parse_args(argv)

    key = os.environ.get("DATA_GO_KR_KEY", "").strip()
    if not key:
        print("DATA_GO_KR_KEY 가 없어 건너뛰어요. (공공데이터포털 '한국관광공사_국문 관광정보 서비스' 디코딩 키)")
        return 0

    out = Path(args.out)
    previous = []
    if out.exists():
        try:
            previous = json.loads(out.read_text(encoding="utf-8")).get("courses", [])
        except (json.JSONDecodeError, OSError):
            previous = []

    client = Client(key, args.max_calls)
    try:
        courses = collect(client, args.per_region, previous)
    except (RuntimeError, urllib.error.URLError) as e:
        print(f"수집 실패: {e}", file=sys.stderr)
        return 1

    if not courses:
        print("받은 코스가 없어 기존 파일을 그대로 둬요.")
        return 0
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "updated": datetime.now(KST).isoformat(timespec="minutes"),
        "source": "한국관광공사 TourAPI 추천코스 (공공누리)",
        "courses": courses,
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(courses)}개 코스 저장 → {out} (호출 {client.calls}회)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
