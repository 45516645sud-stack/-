#!/usr/bin/env python3
"""놀코 그림을 실제 사진으로 바꾸기 위한 후보 모으기 (한 번 쓰고 지우는 도구).

위키미디어 공용(Commons)에서 다시 써도 되는 사진(CC0·퍼블릭 도메인·CC BY·CC BY-SA)만 찾아
photo_candidates/<이름>/<번호>.jpg 와 meta.json(출처·저작자·라이선스)으로 저장한다.
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

UA = "nolco-photo-candidates/1.0 (https://github.com/45516645sud-stack/-)"
API = "https://commons.wikimedia.org/w/api.php"
OK_LICENSE = re.compile(r"^(CC0|Public domain|PD|CC BY(-SA)? [0-9.]+)", re.I)
QUERIES = {
    "coinsing": "karaoke microphone", "karaoke": "karaoke room", "boardgame": "board game dice table",
    "escape": "escape room", "bowling": "bowling ball pins", "billiards": "billiard balls table",
    "arcade": "claw crane machine", "manga": "manga comic books shelf", "photo": "photo booth",
    "class": "pottery wheel hands", "climbing": "indoor climbing wall", "screenbase": "baseball bat ball",
    "pc": "internet cafe computers", "vr": "virtual reality headset", "jjim": "jjimjilbang",
    "cinema": "popcorn", "meal": "bibimbap", "snack": "tteokbokki", "cafe": "strawberry cake slice",
    "cup": "latte art coffee cup", "spark": "ferris wheel", "wave": "beach parasol sea",
    "moon": "Seoul night skyline", "roof": "hanok", "leaf": "forest trail", "pin": "Korea travel map",
    "show": "theatre stage audience", "festival": "fireworks festival",
}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def strip(html):
    return re.sub(r"<[^>]+>", "", html or "").strip()


def main(out="photo_candidates", per=8):
    root = Path(out)
    for name, q in QUERIES.items():
        params = {"action": "query", "format": "json", "generator": "search", "gsrnamespace": 6, "gsrsearch": f"{q} filetype:bitmap",
                  "gsrlimit": 30, "prop": "imageinfo", "iiprop": "url|extmetadata|size", "iiurlwidth": 480}
        try:
            data = json.loads(get(API + "?" + urllib.parse.urlencode(params)))
        except Exception as e:  # noqa: BLE001
            print(name, "검색 실패", e)
            continue
        pages = sorted((data.get("query") or {}).get("pages", {}).values(), key=lambda p: p.get("index", 99))
        d = root / name
        d.mkdir(parents=True, exist_ok=True)
        meta, n = [], 0
        for p in pages:
            ii = (p.get("imageinfo") or [{}])[0]
            m = ii.get("extmetadata") or {}
            lic = strip((m.get("LicenseShortName") or {}).get("value"))
            if not OK_LICENSE.match(lic) or ii.get("width", 0) < 600 or not ii.get("thumburl"):
                continue
            try:
                (d / f"{n}.jpg").write_bytes(get(ii["thumburl"]))
            except Exception:  # noqa: BLE001
                continue
            meta.append({"n": n, "title": p["title"], "page": ii.get("descriptionurl"), "license": lic,
                         "license_url": strip((m.get("LicenseUrl") or {}).get("value")),
                         "artist": strip((m.get("Artist") or {}).get("value"))[:120]})
            n += 1
            time.sleep(0.3)
            if n >= per:
                break
        (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
        print(name, q, n, "장")


if __name__ == "__main__":
    main(*sys.argv[1:])
