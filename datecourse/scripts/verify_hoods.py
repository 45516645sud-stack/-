#!/usr/bin/env python3
"""'우리 동네' 후보를 실제 카카오 지도로 확인해서 data/local.json 에 넣는다.

    python scripts/verify_hoods.py                 # 놀코 서버(Supabase 함수)로 확인
    python scripts/verify_hoods.py --dry-run       # 결과만 출력, 파일은 그대로

data/hood_candidates.json 의 후보(hoods: 번화가, towns: 전국 시·군·구청 주변)마다
  1) 검색어로 동네 가운데 위치를 찾고 (주소가 그 시·도인지 확인)
  2) 반경 2km 안에 코인노래방이나 오락실이 실제로 있는지 센다.
하나라도 있으면 local.json 의 hoods 에 더한다. 이미 있는 동네와 1.2km 안이면 같은 동네로 보고 뺀다.
빠진 곳은 data/hood_rejected.json 에 이유를 남긴다.
이미 local.json 에 있는 동네는 건드리지 않는다. Python 표준 라이브러리만 쓴다.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent.parent
ENDPOINT = "https://hzomhheyccapnzuwtzxh.supabase.co/functions/v1/bright-action"
ORIGIN = "https://45516645sud-stack.github.io"

# 놀거리 기준: 코인노래방이나 오락실이 한 곳이라도 있으면 '놀 데가 있는 동네'
PROBES = ["코인노래방", "오락실"]
RADIUS = 2000
SAME_HOOD_KM = 1.2     # 이미 있는 동네와 이보다 가까우면 중복

Fetch = Callable[[dict], dict]


def http_fetch(params: dict) -> dict:
    url = f"{ENDPOINT}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Origin": ORIGIN, "User-Agent": "nolco-verify/1.0"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=20) as res:
                return json.loads(res.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            if attempt == 2:
                raise
            time.sleep(1.5 * (attempt + 1))
    return {}


# 카카오 주소의 시·도 표기가 앱의 지역 이름과 다른 경우
# (광주·전남은 '전남광주통합특별시'로 나온다: 광주 쪽은 동·서·남·북·광산구)
REGION_PREFIXES = {
    "광주": ["광주", *[f"전남광주통합특별시 {g}" for g in ("동구", "서구", "남구", "북구", "광산구")]],
}


def in_region(address: str, region: str) -> bool:
    return any(address.startswith(p) for p in REGION_PREFIXES.get(region, [region]))


def find_center(fetch: Fetch, region: str, q: str) -> dict | None:
    """검색어 첫 결과 중 그 시·도 주소인 곳의 위치"""
    data = fetch({"mode": "places", "q": q, "size": 5})
    if "places" not in data:   # 서버·카카오 오류: '못 찾음'이 아니라 다음에 다시
        raise RuntimeError(data.get("error", "응답 없음"))
    for p in data.get("places", []):
        if in_region(str(p.get("address", "")), region):
            return {"lat": round(float(p["y"]), 4), "lng": round(float(p["x"]), 4), "address": p["address"]}
    first = [p.get("address", "") for p in data.get("places", [])[:2]]
    print(f"  '{q}' 첫 결과 주소: {first or '없음'}")
    return None


def city_from(address: str, region: str) -> str:
    """주소에서 시·군·구: '경북 포항시 북구 …' → 포항시, '서울 관악구 …' → 관악구, 세종 → 세종"""
    parts = address.split()
    if len(parts) > 1 and parts[1][-1:] in ("시", "군", "구"):
        return parts[1]
    return region


def fill_cities(fetch: Fetch, local: dict) -> int:
    """city 가 없는 동네에 시·군·구를 채운다 (동네 고르기 창에서 묶어 보여 주려고)"""
    filled = 0
    for region, hs in local["hoods"].items():
        for h in hs:
            if h.get("city"):
                continue
            try:
                center = find_center(fetch, region, h.get("q") or h["name"])
            except Exception as e:
                print(f"  시·군·구 못 채움 {region} {h['name']}: {e}")
                continue
            if center:
                h["city"] = city_from(center["address"], region)
                filled += 1
    return filled


def count_fun(fetch: Fetch, center: dict) -> dict[str, int]:
    out = {}
    for kw in PROBES:
        data = fetch({"mode": "places", "q": kw, "lat": center["lat"], "lng": center["lng"], "radius": RADIUS, "size": 15})
        if "places" not in data:
            raise RuntimeError(data.get("error", "응답 없음"))
        out[kw] = len(data["places"])
    return out


def judge(counts: dict[str, int]) -> tuple[bool, str]:
    ok = any(n > 0 for n in counts.values())
    found = ", ".join(f"{k} {n}곳" for k, n in counts.items())
    return ok, found + ("" if ok else " (코인노래방·오락실 없음)")


def km(a: dict, b: dict) -> float:
    import math
    r = math.pi / 180
    h = math.sin((b["lat"] - a["lat"]) * r / 2) ** 2 + math.cos(a["lat"] * r) * math.cos(b["lat"] * r) * math.sin((b["lng"] - a["lng"]) * r / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def verify_one(fetch: Fetch, region: str, cand: list) -> dict:
    hid, name, q, desc = cand
    try:
        center = find_center(fetch, region, q)
    except Exception as e:  # 네트워크 등: 다음 실행 때 다시
        return {"id": hid, "region": region, "name": name, "ok": False, "why": f"확인 실패: {e}", "retry": True}
    if not center:
        return {"id": hid, "region": region, "name": name, "ok": False, "why": f"'{q}' 위치를 {region}에서 못 찾음"}
    try:
        counts = count_fun(fetch, center)
    except Exception as e:
        return {"id": hid, "region": region, "name": name, "ok": False, "why": f"확인 실패: {e}", "retry": True}
    ok, why = judge(counts)
    return {"id": hid, "region": region, "name": name, "q": q, "desc": desc, "ok": ok, "why": why,
            "lat": center["lat"], "lng": center["lng"], "counts": counts, "city": city_from(center["address"], region)}


def merge(local: dict, results: list[dict]) -> int:
    """통과한 후보를 지역별로 뒤에 붙인다. 이미 있는 id, 이미 있는 동네와 가까운 곳은 건너뛴다."""
    have = {h["id"] for hs in local["hoods"].values() for h in hs}
    added = 0
    for r in results:
        if not r["ok"] or r["id"] in have:
            continue
        near = [h for h in local["hoods"].get(r["region"], []) if "lat" in h and km(h, r) < SAME_HOOD_KM]
        if near:
            r["ok"] = False
            r["why"] = f"이미 있는 '{near[0]['name']}'와 같은 동네"
            continue
        name = r["name"]
        if any(h["name"] == name for h in local["hoods"].get(r["region"], [])):
            office = r["q"].split()[-1]
            name += " (시청 주변)" if office.endswith("시청") else " (군청 주변)" if office.endswith("군청") else " (구청 주변)"
        local["hoods"].setdefault(r["region"], []).append(
            {"id": r["id"], "name": name, "q": r["q"], "lat": r["lat"], "lng": r["lng"], "desc": r["desc"], "city": r.get("city", "")})
        have.add(r["id"])
        added += 1
    return added


def main(argv: list[str] | None = None, fetch: Fetch = http_fetch) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args(argv)

    local_path = ROOT / "data" / "local.json"
    local = json.loads(local_path.read_text(encoding="utf-8"))
    data = json.loads((ROOT / "data" / "hood_candidates.json").read_text(encoding="utf-8"))
    have = {h["id"] for hs in local["hoods"].values() for h in hs}
    todo = [(region, c) for group in ("hoods", "towns") for region, cs in data.get(group, {}).items()
            for c in cs if c[0] not in have]
    print(f"확인할 후보 {len(todo)}곳 (이미 있는 동네 {len(have)}곳은 그대로)")

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
        results = list(ex.map(lambda rc: verify_one(fetch, *rc), todo))
    for r in results:
        print(("통과 " if r["ok"] else "제외 ") + f"{r['region']} {r['name']}: {r['why']}")

    if any(r.get("retry") for r in results) and all(r.get("retry") for r in results if not r["ok"]) and not any(r["ok"] for r in results):
        print("모든 확인이 실패했어요. 서버나 네트워크를 확인해 주세요.", file=sys.stderr)
        return 1

    added = merge(local, results)
    filled = fill_cities(fetch, local)
    print(f"시·군·구 채움 {filled}곳")
    rejected = [{k: r[k] for k in ("region", "id", "name", "why")} for r in results if not r["ok"]]
    for r in results:
        if not r["ok"] and r["why"].startswith("이미 있는"):
            print(f"중복 {r['region']} {r['name']}: {r['why']}")
    print(f"추가 {added}곳, 제외 {len(rejected)}곳")
    if args.dry_run:
        return 0
    local_path.write_text(json.dumps(local, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (ROOT / "data" / "hood_rejected.json").write_text(
        json.dumps({"note": "카카오 지도로 확인했을 때 놀거리가 부족하거나 위치를 못 찾아 뺀 후보", "hoods": rejected},
                   ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
