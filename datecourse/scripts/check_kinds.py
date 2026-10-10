#!/usr/bin/env python3
"""놀거리 종류 거르기 점검: 실제 카카오 검색 결과에 앱 규칙(fitsAct)을 그대로 적용해 본다.

    python scripts/check_kinds.py              # 동네 몇 곳 x 놀거리 전부
    python scripts/check_kinds.py --hood andongdowntown

놀코 서버 함수(Supabase)로 묻기 때문에 키가 필요 없다. 파일은 바꾸지 않고 결과만 출력한다.
  - 각 놀거리 검색 결과마다 가게 이름, 카카오 분류, 통과/제외
  - 이름난 체인(벌툰·놀숲 등)을 이름으로 찾아 카카오 분류와 어느 놀거리에 들어가는지
"""
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_hoods import ROOT, http_fetch  # noqa: E402

SAMPLE = ["andongdowntown", "andongokdong", "seomyeon", "hongdae", "dongseongro", "bupyeong", "chungjang",
          "eunhaeng", "seongan", "gumi", "gaeksa", "dujeong", "samsan"]
BRANDS = ["벌툰", "놀숲", "만화방", "놀숲 만화카페", "레드버튼", "홈즈앤루팡", "나인블럭", "인생네컷", "포토이즘", "하루필름", "코인노래방", "오락실",
          "만화카페", "보드게임카페", "방탈출", "스크린야구", "VR"]


def fits(a: dict, cat: str, name: str) -> bool:
    text = f"{cat} {name}".lower()
    has = lambda w: w.lower() in text  # noqa: E731
    return any(map(has, a.get("match", []))) and not any(map(has, a.get("not", [])))


def places(q: str, h: dict, page: int = 1, radius: int = 2000) -> list[dict]:
    d = http_fetch({"mode": "places", "q": q, "lat": h["lat"], "lng": h["lng"], "radius": radius, "size": 15, "page": page})
    return d.get("places", []) if isinstance(d, dict) else []


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hood", action="append")
    args = ap.parse_args(argv)
    local = json.loads((ROOT / "data" / "local.json").read_text(encoding="utf-8"))
    hoods = {h["id"]: h for hs in local["hoods"].values() for h in hs}
    ids = [i for i in (args.hood or SAMPLE) if i in hoods]
    acts = local["activities"]

    def run(job):
        h, a = job
        kws = a.get("kws") or [a["kw"]]
        got, seen = [], set()
        for kw in kws:
            for page in (1, 2):
                ps = places(f"{h['q']} {kw}", h, page)
                for p in ps:
                    k = (p["name"], p["address"])
                    if k not in seen:
                        seen.add(k)
                        got.append(p)
                if len(ps) < 15:
                    break
        return h, a, got

    jobs = [(hoods[i], a) for i in ids for a in acts]
    with ThreadPoolExecutor(max_workers=4) as ex:
        results = list(ex.map(run, jobs))
    from collections import defaultdict
    by_act = defaultdict(list)
    for h, a, got in results:
        by_act[a["id"]].append((h, a, got))
    for aid, rows in by_act.items():
        a = rows[0][1]
        print(f"\n## {a['name']}  " + " ".join(f"{h['name']}:{sum(fits(a, p.get('path') or p['category'], p['name']) for p in got)}/{len(got)}" for h, _, got in rows))
        paths = defaultdict(list)
        for h, _, got in rows:
            for p in got:
                path = p.get("path") or p["category"]
                paths[(fits(a, path, p["name"]), path)].append(p["name"])
        for (ok, path), names in sorted(paths.items(), key=lambda kv: (not kv[0][0], -len(kv[1]))):
            print(f"  {'O' if ok else 'X'} {len(names):3d} {path} | 예: {', '.join(names[:3])}")

    print("\n\n######## 체인 이름으로 찾기 (반경 5km) ########")
    def brand(job):
        h, b = job
        return h, b, places(b, h, 1, 5000)
    seen = set()
    with ThreadPoolExecutor(max_workers=4) as ex:
        for h, b, ps in ex.map(brand, [(hoods[i], b) for i in ids for b in BRANDS]):
            for p in ps[:8]:
                path = p.get("path") or p["category"]
                into = [a["name"] for a in acts if fits(a, path, p["name"])]
                key = (b, path, tuple(into))
                if key in seen:
                    continue
                seen.add(key)
                print(f"'{b}' {p['name']} ({h['name']}) | {path} | → {', '.join(into) or '어디에도 안 들어감'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
