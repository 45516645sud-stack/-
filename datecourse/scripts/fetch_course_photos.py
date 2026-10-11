#!/usr/bin/env python3
"""여행 코스 썸네일용 실제 장소 사진을 한국관광공사 TourAPI 에서 받아 온다. GitHub Actions 에서 돌린다.

    DATA_GO_KR_KEY=… python scripts/fetch_course_photos.py

코스마다 정류장을 차례로 '장소 이름'으로 검색해서(searchKeyword2), 정류장 좌표에서 3km 안에 있고
대표 사진이 공공누리 제1유형(출처 표시하면 자유 이용)인 첫 결과를 쓴다.
사진은 400px WebP 로 줄여 img/course/<코스id>.webp 에, 출처는 data/course_photos.json 에 남긴다.
이미 사진이 있는 코스는 다시 받지 않는다. 키가 없으면 아무것도 하지 않는다.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import collect_tour as ct  # noqa: E402
from verify_hoods import km  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
NEAR_KM = 3.0
SIZE = 400


def https(url: str) -> str:
    return "https://" + url[7:] if url.startswith("http://") else url


def norm(s: str) -> str:
    return "".join(ch for ch in s.lower() if ch.isalnum())


def pick(items: list[dict], stop: dict) -> dict | None:
    """좌표가 가깝고 공공누리 1유형 사진이 있는 첫 결과 (좌표가 없으면 이름이 겹치는 것)"""
    for it in items:
        if not it.get("firstimage") or str(it.get("cpyrhtDivCd", "")).lower() != "type1":
            continue
        x, y = ct.to_float(it.get("mapx")), ct.to_float(it.get("mapy"))
        if "lat" in stop and x and y:
            if km(stop, {"lat": y, "lng": x}) > NEAR_KM:
                continue
        elif norm(stop["name"])[:4] not in norm(str(it.get("title", ""))):
            continue
        return it
    return None


def find_photo(client: ct.Client, course: dict) -> dict | None:
    for stop in course["stops"]:
        name = stop["name"].split("(")[0].split("·")[0].strip()
        if len(name) < 2:
            continue
        items = client.get("searchKeyword2", keyword=name, numOfRows=10, pageNo=1, arrange="A")
        it = pick(items, stop)
        if it:
            return {"url": https(str(it["firstimage"])), "place": ct.clean(it.get("title"), 40), "stop": stop["name"]}
    return None


def shrink(data: bytes) -> bytes:
    from PIL import Image  # GitHub Actions 에서만 설치
    im = Image.open(io.BytesIO(data)).convert("RGB")
    w, h = im.size
    s = min(w, h)
    im = im.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s)).resize((SIZE, SIZE), Image.LANCZOS)
    out = io.BytesIO()
    im.save(out, "WEBP", quality=76, method=6)
    return out.getvalue()


def download(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "nolco/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def main(argv: list[str] | None = None, client: ct.Client | None = None, fetch=download) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--max-calls", type=int, default=500)
    args = ap.parse_args(argv)
    key = os.environ.get("DATA_GO_KR_KEY", "").strip()
    if client is None:
        if not key:
            print("DATA_GO_KR_KEY 가 없어 건너뜀")
            return 0
        client = ct.Client(key, args.max_calls)
    courses = json.loads((ROOT / "data" / "courses.json").read_text(encoding="utf-8"))["courses"]
    meta_path = ROOT / "data" / "course_photos.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {"note": "", "photos": {}}
    meta["note"] = "코스 썸네일 사진: 한국관광공사 TourAPI 대표 사진 (공공누리 제1유형, 출처 표시)"
    photos = meta["photos"]
    folder = ROOT / "img" / "course"
    folder.mkdir(parents=True, exist_ok=True)
    got = 0
    for c in courses:
        if c["id"] in photos:
            continue
        try:
            p = find_photo(client, c)
        except ct.CallBudget:
            print("호출 한도에 닿아 여기서 멈춰요")
            break
        except Exception as e:  # noqa: BLE001
            print(f"{c['id']}: 검색 실패 {e}")
            continue
        if not p:
            print(f"{c['id']} {c['title']}: 맞는 사진 없음")
            continue
        try:
            (folder / f"{c['id']}.webp").write_bytes(shrink(fetch(p["url"])))
        except Exception as e:  # noqa: BLE001
            print(f"{c['id']}: 사진 받기 실패 {e}")
            continue
        photos[c["id"]] = {"img": f"img/course/{c['id']}.webp", "place": p["place"], "stop": p["stop"], "credit": "한국관광공사"}
        got += 1
        print(f"{c['id']} {c['title']}: {p['place']}")
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"새 사진 {got}장, 모두 {len(photos)}장 (호출 {client.calls}회)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
