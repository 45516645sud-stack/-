"""공연 홍보 영상(유튜브) 자동 찾기.

fairs.json 의 공연 중 지금·곧 하는 공연을 골라, 공연 이름으로 유튜브를 검색해
제목이 맞는 영상을 aiiairs/data/videos.json 에 적어 둔다.

- 사이트에는 바로 나오지 않는다. 관리자 페이지에서 '맞아요'를 누른 영상만 스토리에 나온다.
- 유튜브 검색은 하루 사용량이 정해져 있어(검색 1번 = 100점, 하루 10,000점) 한 번에 --limit 개까지만 찾는다.
- 이미 찾아본 공연은 14일 동안 다시 찾지 않는다 (못 찾은 공연도).

YOUTUBE_API_KEY 가 없으면 아무것도 하지 않고 끝난다.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
API = "https://www.googleapis.com/youtube/v3/search"
RECHECK_DAYS = 14
PROMO = ("티저", "트레일러", "teaser", "trailer", "하이라이트", "highlight", "스팟", "spot", "예고", "프리뷰", "preview",
         "프레스콜", "콜", "공연 영상", "홍보")
ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def core_title(title: str) -> str:
    """'난세: 정도전과 이방원의 이야기 [대학로]' → '난세: 정도전과 이방원의 이야기' (꼬리표·괄호 빼기)."""
    t = re.sub(r"\s*[\[(（〈<].*?[\])）〉>]\s*", " ", title)
    t = re.sub(r"^제\s*\d+\s*회\s*", "", t)
    return re.sub(r"\s+", " ", t).strip(" -·,")


def squash(s: str) -> str:
    """비교용: 소문자, 글자·숫자만."""
    return re.sub(r"[^0-9a-z가-힣]", "", s.lower())


def match_score(show_title: str, video_title: str) -> int:
    """영상 제목이 공연 이름과 얼마나 맞는지. 0 이면 쓰지 않는다."""
    core = core_title(show_title)
    # 쉼표·콜론 앞부분(축제 이름 등)보다 뒷부분이 진짜 공연 이름인 경우가 많아 둘 다 본다
    parts = [p for p in re.split(r"[,:：]", core) if len(squash(p)) >= 2] or [core]
    v = squash(video_title)
    best = 0
    for p in [core, *parts]:
        k = squash(p)
        if len(k) >= 3 and k in v:
            best = max(best, 2 + (len(k) >= 6))
    if not best:
        return 0
    if any(w in video_title.lower() for w in PROMO):
        best += 2
    return best


def pick(show_title: str, items: list[dict]) -> dict | None:
    best, top = 0, None
    for it in items:
        vid = (it.get("id") or {}).get("videoId") or ""
        sn = it.get("snippet") or {}
        if not ID_RE.match(vid):
            continue
        sc = match_score(show_title, sn.get("title") or "")
        if sc > best:
            best, top = sc, {"vid": vid, "t": (sn.get("title") or "")[:120], "ch": (sn.get("channelTitle") or "")[:60], "score": sc}
    return top


def search(key: str, q: str) -> list[dict]:
    params = urllib.parse.urlencode({"part": "snippet", "type": "video", "maxResults": 6, "q": q, "regionCode": "KR",
                                     "relevanceLanguage": "ko", "videoEmbeddable": "true", "safeSearch": "strict", "key": key})
    with urllib.request.urlopen(f"{API}?{params}", timeout=20) as r:
        return json.load(r).get("items") or []


def candidates(items: list[dict], known: dict, today: dt.date, limit: int) -> list[dict]:
    out = []
    for f in items:
        if not f.get("id") or not f.get("t"):
            continue
        try:
            s, e = dt.date.fromisoformat(f["s"]), dt.date.fromisoformat(f["e"])
        except (KeyError, ValueError):
            continue
        if e < today or s > today + dt.timedelta(days=45):
            continue
        k = known.get(f["id"])
        if k:
            try:
                if (today - dt.date.fromisoformat(k.get("at", "2000-01-01"))).days < RECHECK_DAYS:
                    continue
            except ValueError:
                pass
        out.append(f)
    # 이미 하고 있고 곧 끝나는 공연부터 (스토리 '오늘 마감'·'이번 주말'에 먼저 나오는 공연)
    out.sort(key=lambda f: (f["s"] > today.isoformat(), f["e"]))
    return out[:limit]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fairs", default=str(DATA / "fairs.json"))
    ap.add_argument("--out", default=str(DATA / "videos.json"))
    ap.add_argument("--limit", type=int, default=80)
    a = ap.parse_args(argv)
    key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    if not key:
        print("YOUTUBE_API_KEY 없음: 영상 찾기를 건너뜀")
        return 0
    items = json.loads(Path(a.fairs).read_text(encoding="utf-8")).get("items") or []
    out = Path(a.out)
    try:
        known = json.loads(out.read_text(encoding="utf-8")).get("videos") or {}
    except (OSError, ValueError):
        known = {}
    today = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date()
    live_ids = {f.get("id") for f in items}
    known = {k: v for k, v in known.items() if k in live_ids}   # 목록에서 빠진 공연은 지운다
    found = tried = 0
    for f in candidates(items, known, today, a.limit):
        try:
            res = search(key, f"{core_title(f['t'])} 공연")
        except Exception as e:  # 사용량 초과 등: 지금까지 찾은 것만 저장하고 멈춘다
            print(f"검색 멈춤: {e}", file=sys.stderr)
            break
        tried += 1
        hit = pick(f["t"], res)
        known[f["id"]] = {**(hit or {"vid": None}), "at": today.isoformat()}
        found += bool(hit)
    out.write_text(json.dumps({"updated": today.isoformat(), "videos": dict(sorted(known.items()))}, ensure_ascii=False, indent=1) + "\n",
                   encoding="utf-8")
    print(f"영상 찾기: {tried}건 검색, {found}건 찾음, 모두 {sum(1 for v in known.values() if v.get('vid'))}건 기억")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
