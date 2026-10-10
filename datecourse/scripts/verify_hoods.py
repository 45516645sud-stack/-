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


def find_center(fetch: Fetch, region: str, q: str) -> dict | None:
    """검색어 첫 결과 중 그 시·도 주소인 곳의 위치"""
    data = fetch({"mode": "places", "q": q, "size": 5})
    if "places" not in data:   # 서버·카카오 오류: '못 찾음'이 아니라 다음에 다시
        raise RuntimeError(data.get("error", "응답 없음"))
    for p in data.get("places", []):
        if str(p.get("address", "")).startswith(region):
            return {"lat": round(float(p["y"]), 4), "lng": round(float(p["x"]), 4), "address": p["address"]}
    first = [p.get("address", "") for p in data.get("places", [])[:2]]
    print(f"  '{q}' 첫 결과 주소: {first or '없음'}")
    return None


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
            "lat": center["lat"], "lng": center["lng"], "counts": counts}


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
        local["hoods"].setdefault(r["region"], []).append(
            {"id": r["id"], "name": r["name"], "q": r["q"], "lat": r["lat"], "lng": r["lng"], "desc": r["desc"]})
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
