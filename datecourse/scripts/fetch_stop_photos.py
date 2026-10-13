#!/usr/bin/env python3
"""여행 코스 '코스 순서'의 장소마다 실제 사진을 한국관광공사 TourAPI 에서 받아 온다. GitHub Actions 에서 돌린다.

    DATA_GO_KR_KEY=… python scripts/fetch_stop_photos.py

장소 이름으로 검색해서(searchKeyword2) 장소 좌표에서 1km 안이고, 이름이 겹치고,
대표 사진이 공공누리 제1유형(출처 표시하면 자유 이용)인 첫 결과를 쓴다. (코스 썸네일보다 엄격하게: 다른 곳 사진이 붙지 않게)
사진은 320px WebP 로 줄여 img/stop/<코스id>-<번호>.webp 에, 출처는 data/stop_photos.json 에 남긴다.
이미 받은 장소는 다시 받지 않고, 못 찾은 장소는 30일 뒤에 다시 찾아본다. 키가 없으면 아무것도 하지 않는다.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import collect_tour as ct  # noqa: E402
from fetch_course_photos import download, https, norm, shrink  # noqa: E402
from verify_hoods import km  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
NEAR_KM = 1.0
SIZE = 320
RETRY_DAYS = 30
# 장소 이름에 없는데 결과 이름에 이런 말이 있으면 근처 숙소·가게 사진이다 (예: 월미도 → 'OO 월미도 호텔')
NOT_PLACE = ("호텔", "모텔", "펜션", "게스트하우스", "리조트", "스테이", "민박", "점")


def base_name(name: str) -> str:
    return name.split("(")[0].split("·")[0].strip()


def pick(items: list[dict], stop: dict) -> dict | None:
    """좌표가 1km 안이고 이름 앞부분이 겹치며 공공누리 1유형 사진이 있는 첫 결과"""
    want = norm(base_name(stop["name"]))
    if len(want) < 2:
        return None
    for it in items:
        if not it.get("firstimage") or str(it.get("cpyrhtDivCd", "")).lower() != "type1":
            continue
        title = norm(str(it.get("title", "")))
        if want[:4] not in title and title[:4] not in want:
            continue
        raw = str(it.get("title", ""))
        if any(w in raw and w not in stop["name"] for w in NOT_PLACE if w != "점") or (raw.endswith("점") and not stop["name"].endswith("점")):
            continue
        x, y = ct.to_float(it.get("mapx")), ct.to_float(it.get("mapy"))
        if "lat" in stop and (not x or not y or km(stop, {"lat": y, "lng": x}) > NEAR_KM):
            continue
        return it
    return None


def main(argv: list[str] | None = None, client: ct.Client | None = None, fetch=download, today: dt.date | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--max-calls", type=int, default=800)
    args = ap.parse_args(argv)
    key = os.environ.get("DATA_GO_KR_KEY", "").strip()
    if client is None:
        if not key:
            print("DATA_GO_KR_KEY 가 없어 건너뜀")
            return 0
        client = ct.Client(key, args.max_calls)
    today = today or dt.date.today()
    courses = json.loads((ROOT / "data" / "courses.json").read_text(encoding="utf-8"))["courses"]
    meta_path = ROOT / "data" / "stop_photos.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    meta["note"] = "코스 순서 장소 사진: 한국관광공사 TourAPI 대표 사진 (공공누리 제1유형, 출처 표시)"
    photos: dict = meta.setdefault("photos", {})   # 코스id → { 번호: { img, place } }
    misses: dict = meta.setdefault("misses", {})   # "코스id/번호" → 마지막으로 못 찾은 날
    folder = ROOT / "img" / "stop"
    folder.mkdir(parents=True, exist_ok=True)
    got = 0
    try:
        for c in courses:
            for i, stop in enumerate(c["stops"]):
                k = f"{c['id']}/{i}"
                if str(i) in photos.get(c["id"], {}):
                    continue
                last = misses.get(k)
                if last and (today - dt.date.fromisoformat(last)).days < RETRY_DAYS:
                    continue
                try:
                    items = client.get("searchKeyword2", keyword=base_name(stop["name"]), numOfRows=10, pageNo=1, arrange="A")
                except ct.CallBudget:
                    raise
                except Exception as e:  # noqa: BLE001
                    print(f"{k} {stop['name']}: 검색 실패 {e}")
                    continue
                it = pick(items, stop)
                if not it:
                    misses[k] = today.isoformat()
                    continue
                name = f"{c['id']}-{i}.webp"
                try:
                    (folder / name).write_bytes(shrink(fetch(https(str(it["firstimage"]))), SIZE))
                except Exception as e:  # noqa: BLE001
                    print(f"{k}: 사진 받기 실패 {e}")
                    continue
                photos.setdefault(c["id"], {})[str(i)] = {"img": f"img/stop/{name}", "place": ct.clean(it.get("title"), 40)}
                misses.pop(k, None)
                got += 1
                print(f"{k} {stop['name']}: {photos[c['id']][str(i)]['place']}")
    except ct.CallBudget:
        print("호출 한도에 닿아 여기서 멈춰요 (다음에 이어서)")
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    total = sum(len(v) for v in photos.values())
    print(f"새 사진 {got}장, 모두 {total}장, 못 찾은 곳 {len(misses)}곳 (호출 {client.calls}회)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
