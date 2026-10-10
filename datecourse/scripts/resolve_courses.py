#!/usr/bin/env python3
"""새 여행 코스 후보(data/course_candidates.json)의 장소 위치를 카카오 지도로 찾아 data/courses.json 에 넣는다.

    python scripts/resolve_courses.py              # 놀코 서버(Supabase 함수)로 확인
    python scripts/resolve_courses.py --dry-run

정류장마다 검색어(q)로 찾은 첫 결과 중 그 시·도 주소인 곳의 좌표를 쓴다.
한 곳이라도 못 찾거나, 정류장끼리 60km 넘게 떨어져 있으면(엉뚱한 곳을 찾은 것) 그 코스는 넣지 않고
data/course_rejected.json 에 이유를 남긴다. 이미 courses.json 에 있는 코스는 건드리지 않는다.
"""
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_hoods import ROOT, Fetch, find_center, http_fetch, km  # noqa: E402

MAX_SPREAD_KM = 60


def resolve(fetch: Fetch, cand: dict) -> tuple[dict | None, str]:
    stops = []
    for s in cand["stops"]:
        try:
            at = find_center(fetch, cand["region"], s.get("q") or s["name"])
        except Exception as e:  # 서버 오류: 다음에 다시
            return None, f"확인 실패: {e}"
        if not at:
            return None, f"'{s['name']}' 위치를 {cand['region']}에서 못 찾음"
        stop = {k: v for k, v in s.items() if k != "q"}
        stop.update(lat=at["lat"], lng=at["lng"])
        stops.append(stop)
    far = max((km(a, b) for a in stops for b in stops), default=0)
    if far > MAX_SPREAD_KM:
        return None, f"정류장끼리 {far:.0f}km 떨어져 있음 (잘못 찾았을 수 있음)"
    return {**cand, "stops": stops}, "통과"


def main(argv: list[str] | None = None, fetch: Fetch = http_fetch) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    path = ROOT / "data" / "courses.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    have = {c["id"] for c in data["courses"]}
    cands = [c for c in json.loads((ROOT / "data" / "course_candidates.json").read_text(encoding="utf-8"))["courses"] if c["id"] not in have]
    print(f"확인할 코스 {len(cands)}개 (이미 있는 코스 {len(have)}개)")
    with ThreadPoolExecutor(max_workers=4) as ex:
        results = list(ex.map(lambda c: (c, *resolve(fetch, c)), cands))
    added, rejected = [], []
    for cand, course, why in results:
        print(("통과 " if course else "제외 ") + f"{cand['region']} {cand['title']}: {why}")
        if course:
            added.append(course)
        else:
            rejected.append({"id": cand["id"], "title": cand["title"], "why": why})
    if cands and not added and all(r["why"].startswith("확인 실패") for r in rejected):
        print("모든 확인이 실패했어요. 서버나 네트워크를 확인해 주세요.", file=sys.stderr)
        return 1
    print(f"추가 {len(added)}개, 제외 {len(rejected)}개")
    if args.dry_run:
        return 0
    data["courses"].extend(added)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (ROOT / "data" / "course_rejected.json").write_text(
        json.dumps({"note": "카카오 지도로 위치를 확인하지 못해 뺀 코스 후보", "courses": rejected}, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
