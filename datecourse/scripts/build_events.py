#!/usr/bin/env python3
"""놀코 '이번 주말' 데이터(data/events.json) 만들기. 사이트를 올릴 때(GitHub Pages 작업) 돌린다.

    python scripts/build_events.py --fairs ../aiiairs/data/fairs.json --out data/events.json
    DATA_GO_KR_KEY=… python scripts/build_events.py --fairs … --out …   # 지역 축제도 더하기

- 공연: AIIairs 가 매일 KOPIS 에서 모으는 일정(fairs.json)에서 앞으로 N일 안에 볼 수 있는 것만 놀코 모양으로 옮긴다.
  AIIairs 파일은 읽기만 한다.
- 축제: 공공데이터포털 키(DATA_GO_KR_KEY)가 있으면 한국관광공사 TourAPI 행사 정보(searchFestival2)를 더한다.
키가 없거나 축제를 못 받아도 공연만으로 만든다. Python 표준 라이브러리만 쓴다.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import urllib.parse
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import collect_tour as ct  # noqa: E402

KST = dt.timezone(dt.timedelta(hours=9))
SHOW_CAT = {"theater": "연극", "musical": "뮤지컬", "music": "콘서트", "classic": "클래식", "dance": "무용", "kids": "아이와"}
REGIONS = ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"]
# 주소 첫 마디 → 지역
ADDR_REGION = {
    "서울특별시": "서울", "부산광역시": "부산", "대구광역시": "대구", "인천광역시": "인천", "광주광역시": "광주", "대전광역시": "대전",
    "울산광역시": "울산", "세종특별자치시": "세종", "경기도": "경기", "강원특별자치도": "강원", "강원도": "강원", "충청북도": "충북",
    "충청남도": "충남", "전북특별자치도": "전북", "전라북도": "전북", "전라남도": "전남", "경상북도": "경북", "경상남도": "경남",
    "제주특별자치도": "제주", "전남광주통합특별시": "",
}


def regions_of(raw: str) -> list[str]:
    """'광주·전남' 처럼 묶인 지역은 둘 다"""
    return [r for r in str(raw or "").replace("/", "·").split("·") if r in REGIONS]


def addr_region(addr: str) -> list[str]:
    first = addr.split(" ")[0] if addr else ""
    if first in REGIONS:
        return [first]
    r = ADDR_REGION.get(first)
    if r == "" and len(addr.split()) > 1:  # 통합특별시: 구 이름이면 광주, 아니면 전남
        return ["광주"] if addr.split()[1] in ("동구", "서구", "남구", "북구", "광산구") else ["전남"]
    return [r] if r else []


def https(url: Any) -> str:
    u = str(url or "")
    return u if u.startswith("https://") else ("https://" + u[7:] if u.startswith("http://www.kopis.or.kr") else "")


def from_fairs(items: list[dict], start: dt.date, end: dt.date, poster_prefix: str) -> list[dict]:
    out = []
    for it in items:
        try:
            s, e = dt.date.fromisoformat(it["s"]), dt.date.fromisoformat(it["e"])
        except (KeyError, ValueError):
            continue
        regs = regions_of(it.get("region", ""))
        if e < start or s > end or not regs or not it.get("t"):
            continue
        poster = poster_prefix + it["poster"] if it.get("poster") else https(it.get("img"))
        out.append({
            "id": "s-" + str(it.get("id", ""))[:40], "kind": "show", "cat": SHOW_CAT.get(it.get("cat"), "공연"),
            "title": str(it["t"])[:80], "regions": regs, "place": str(it.get("venue", ""))[:60],
            "start": s.isoformat(), "end": e.isoformat(), "long": bool(it.get("openrun")) or (e - s).days > 120,
            "price": it.get("fee") if isinstance(it.get("fee"), int) else None, "note": str(it.get("note", ""))[:60],
            "poster": poster, "link": it.get("url") or it.get("info") or "", "info": it.get("info") or "",
        })
    return out


def ymd(v: Any) -> dt.date | None:
    try:
        return dt.datetime.strptime(str(v), "%Y%m%d").date()
    except ValueError:
        return None


def from_festivals(client: ct.Client, start: dt.date, end: dt.date) -> list[dict]:
    """진행 중이거나 N일 안에 시작하는 축제 (시작일이 90일 전부터인 것까지 받아 끝난 것은 뺀다)"""
    out, seen = [], set()
    since = (start - dt.timedelta(days=90)).strftime("%Y%m%d")
    for page in range(1, 6):
        items = client.get("searchFestival2", eventStartDate=since, numOfRows=300, pageNo=page, arrange="A")
        for it in items:
            s, e = ymd(it.get("eventstartdate")), ymd(it.get("eventenddate"))
            addr = ct.clean(it.get("addr1"))
            regs = addr_region(addr)
            cid = str(it.get("contentid", ""))
            if not s or not e or e < start or s > end or not regs or cid in seen:
                continue
            seen.add(cid)
            title = ct.clean(it.get("title"), 80)
            out.append({
                "id": "f-" + cid, "kind": "festival", "cat": "축제", "title": title, "regions": regs,
                "place": " ".join(addr.split(" ")[:3])[:60], "start": s.isoformat(), "end": e.isoformat(), "long": (e - s).days > 120,
                "price": None, "note": "", "poster": https(it.get("firstimage")),
                "link": "https://korean.visitkorea.or.kr/search/search_list.do?keyword=" + urllib.parse.quote(title),
                "info": "", "lat": ct.to_float(it.get("mapy")), "lng": ct.to_float(it.get("mapx")),
            })
        if len(items) < 300:
            break
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--fairs", required=True, help="AIIairs 일정 파일 (읽기만)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--days", type=int, default=45, help="오늘부터 며칠 안의 일정까지 (기본 45)")
    ap.add_argument("--poster-prefix", default="../", help="놀코 페이지에서 AIIairs 포스터 경로 앞에 붙일 것")
    ap.add_argument("--today", default="")
    args = ap.parse_args(argv)
    today = dt.date.fromisoformat(args.today) if args.today else dt.datetime.now(KST).date()
    end = today + dt.timedelta(days=args.days)

    events: list[dict] = []
    sources = []
    try:
        fairs = json.loads(Path(args.fairs).read_text(encoding="utf-8")).get("items", [])
        shows = from_fairs(fairs, today, end, args.poster_prefix)
        events += shows
        sources.append({"name": "공연", "label": "KOPIS 공연예술통합전산망", "count": len(shows)})
    except (OSError, json.JSONDecodeError) as e:
        print(f"공연 일정을 못 읽음: {e}", file=sys.stderr)

    key = os.environ.get("DATA_GO_KR_KEY", "").strip()
    if key:
        try:
            fests = from_festivals(ct.Client(key, 6), today, end)
            events += fests
            sources.append({"name": "축제", "label": "한국관광공사 TourAPI", "count": len(fests)})
        except Exception as e:  # noqa: BLE001 — 축제는 없어도 된다
            print(f"축제를 못 받음: {e}", file=sys.stderr)
    else:
        print("DATA_GO_KR_KEY 가 없어 축제는 건너뜀")

    events.sort(key=lambda x: (x["long"], x["start"], x["title"]))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"generated": dt.datetime.now(KST).isoformat(timespec="minutes"), "today": today.isoformat(),
                               "sources": sources, "events": events}, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"이번 주말 데이터: {len(events)}건 → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
