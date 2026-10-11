#!/usr/bin/env python3
"""여행 코스 장소가 아직 지도에 있는지 점검한다 (문 닫은 가게·바뀐 이름 찾기). GitHub Actions 에서 매주 돌린다.

    python scripts/check_courses.py

가게처럼 문을 닫을 수 있는 정류장(카페·먹거리·놀거리·문화·쇼핑·숙소)만, 저장된 좌표 1.5km 안에서
같은 이름의 장소가 카카오 지도에 나오는지 본다. 못 찾은 정류장은 data/course_check.json 에 남기고,
앱은 그 정류장에 '최근 지도에서 확인되지 않았어요'를 띄운다. 놀코 서버 함수로 묻기 때문에 키가 필요 없다.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_hoods import ROOT, Fetch, http_fetch  # noqa: E402

CHECK_KINDS = {"cafe", "food", "activity", "culture", "shop", "stay"}
RADIUS = 1500


def norm(s: str) -> str:
    return "".join(ch for ch in s.split("(")[0].lower() if ch.isalnum())


def exists(fetch: Fetch, stop: dict) -> bool | None:
    """있으면 True, 없으면 False, 확인 실패면 None"""
    name = stop["name"].split("(")[0].strip()
    try:
        data = fetch({"mode": "places", "q": name, "lat": stop["lat"], "lng": stop["lng"], "radius": RADIUS, "size": 15})
    except Exception:  # noqa: BLE001
        return None
    if "places" not in data:
        return None
    key = norm(name)[:4]
    return any(key in norm(p.get("name", "")) or norm(p.get("name", ""))[:4] in norm(name) for p in data["places"])


def check(fetch: Fetch, courses: list[dict]) -> tuple[dict[str, list[str]], int]:
    jobs = [(c["id"], s) for c in courses for s in c["stops"] if s.get("kind") in CHECK_KINDS and "lat" in s and "lng" in s]
    with ThreadPoolExecutor(max_workers=4) as ex:
        results = list(ex.map(lambda j: (j[0], j[1]["name"], exists(fetch, j[1])), jobs))
    missing: dict[str, list[str]] = {}
    failed = 0
    for cid, name, ok in results:
        if ok is None:
            failed += 1
        elif not ok:
            missing.setdefault(cid, []).append(name)
    return missing, failed


def main(fetch: Fetch = http_fetch) -> int:
    courses = json.loads((ROOT / "data" / "courses.json").read_text(encoding="utf-8"))["courses"]
    missing, failed = check(fetch, courses)
    total = sum(1 for c in courses for s in c["stops"] if s.get("kind") in CHECK_KINDS)
    if failed > total // 2:
        print(f"확인 실패가 너무 많아요 ({failed}/{total}). 서버를 확인해 주세요.", file=sys.stderr)
        return 1
    for cid, names in missing.items():
        print(f"확인 안 됨 {cid}: {', '.join(names)}")
    out = {"checked": dt.date.today().isoformat(), "note": "카카오 지도에서 1.5km 안에 같은 이름이 안 나온 정류장 (문을 닫았거나 이름이 바뀌었을 수 있음)",
           "missing": missing}
    (ROOT / "data" / "course_check.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"점검 {total}곳, 확인 안 됨 {sum(map(len, missing.values()))}곳, 실패 {failed}곳")
    return 0


if __name__ == "__main__":
    sys.exit(main())
