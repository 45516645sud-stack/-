#!/usr/bin/env python3
"""코스마다 공유·검색용 페이지(c/<코스id>.html)를 만든다. 사이트를 올릴 때(GitHub Pages 작업) 돌린다.

    python scripts/build_share_pages.py --site _site/nolco --base https://45516645sud-stack.github.io/-/nolco/

- 카카오톡·SNS 미리보기(og:title·og:description·og:image)에 코스 제목·장소·사진이 나온다
- 검색 로봇이 읽을 수 있게 코스 내용(장소 순서·팁)을 글로 담는다
- 사람이 열면 곧바로 놀코 앱의 그 코스로 넘어간다 (검색 로봇은 넘기지 않음)
- sitemap.xml 도 만든다. 사진은 Pillow 가 있으면 미리보기용 JPEG 로 바꾼다 (없으면 기본 그림)
"""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from urllib.parse import quote

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from collect_tour import is_recent  # noqa: E402  (앱과 같은 규칙: 3년 넘게 안 고친 관광공사 코스는 빼기)

ROOT = Path(__file__).resolve().parent.parent
KIND = {"walk": "산책", "cafe": "카페", "food": "먹거리", "view": "전망", "culture": "문화", "activity": "놀거리",
        "shop": "쇼핑", "beach": "바다", "night": "밤", "stay": "숙소"}


def load(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def og_image(site: Path, cid: str, src: Path | None) -> str | None:
    """미리보기 그림: 코스 사진을 JPEG 로 (카카오톡 미리보기가 WebP 를 못 읽을 수 있어서)"""
    if not src or not src.exists():
        return None
    try:
        from PIL import Image
    except ImportError:
        return None
    out = site / "og" / f"{cid}.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    Image.open(src).convert("RGB").save(out, "JPEG", quality=82)
    return f"og/{cid}.jpg"


def default_og(site: Path) -> str:
    """사진이 없는 코스용 기본 그림 (노란 바탕에 3D 지도 핀)"""
    out = site / "og" / "default.jpg"
    try:
        from PIL import Image
        pin = Image.open(ROOT / "img" / "3d" / "pin.webp").convert("RGBA").resize((300, 300))
        bg = Image.new("RGBA", (600, 600), (255, 210, 63, 255))
        bg.alpha_composite(pin, (150, 150))
        out.parent.mkdir(parents=True, exist_ok=True)
        bg.convert("RGB").save(out, "JPEG", quality=85)
        return "og/default.jpg"
    except Exception:  # noqa: BLE001
        return "icon.svg"


def page(c: dict, base: str, image: str) -> str:
    e = lambda s: html.escape(str(s or ""), quote=True)  # noqa: E731
    stops = c.get("stops", [])
    route = " → ".join(s["name"] for s in stops)
    where = f"{c.get('region', '')} {c.get('area', '')}".strip()
    desc = (c.get("summary") or "") + (f" {route}" if route else "")
    url = f"{base}c/{quote(c['id'])}.html"
    app = f"../#c={quote(c['id'])}"
    items = "\n".join(
        f"<li><b>{e(s['name'])}</b> <small>{e(KIND.get(s.get('kind'), ''))}{' · ' + str(s['stay']) + '분' if s.get('stay') else ''}</small>"
        + (f"<br>{e(s['tip'])}" if s.get("tip") else "") + "</li>" for s in stops)
    details = "\n".join(f"<li>{e(d.get('text'))}</li>" for d in c.get("details", []) if d.get("text"))
    return f'''<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(c['title'])} · {e(where)} 코스 | 놀코</title>
<meta name="description" content="{e(desc[:150])}">
<link rel="canonical" href="{e(url)}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="놀코">
<meta property="og:title" content="{e(c['title'])} ({e(where)})">
<meta property="og:description" content="{e(desc[:150])}">
<meta property="og:image" content="{e(image if image.startswith("https://") else base + image)}">
<meta property="og:url" content="{e(url)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#ffd23f">
<link rel="icon" href="../icon.svg">
<style>
body {{ margin: 0; font: 15px/1.7 system-ui, sans-serif; color: #1f1c15; background: #fff; }}
header {{ background: #ffd23f; padding: 16px; font-weight: 800; }}
main {{ max-width: 720px; margin: 0 auto; padding: 16px; }}
img.hero {{ width: 100%; max-height: 360px; object-fit: cover; border-radius: 14px; }}
a.go {{ display: block; text-align: center; background: #ffd23f; color: #1f1c15; font-weight: 800; padding: 14px; border-radius: 12px; text-decoration: none; margin: 16px 0; }}
small {{ color: #6b6455; }}
</style>
</head>
<body>
<header>놀코 · 놀거리 코스</header>
<main>
<p><small>{e(where)}</small></p>
<h1>{e(c['title'])}</h1>
{f'<img class="hero" src="../{e(image)}" alt="">' if image.startswith("og/") and image != "og/default.jpg" else ""}
<p>{e(c.get('summary'))}</p>
<a class="go" id="go" href="{e(app)}">놀코에서 이 코스 보기</a>
<h2>코스 순서</h2>
<ol>
{items}
</ol>
{f'<h2>소소한 디테일</h2><ul>{details}</ul>' if details else ''}
<p><small>운영 시간·요금은 바뀔 수 있으니 가기 전에 확인하세요.</small></p>
</main>
<script>
// 사람이 열면 앱의 그 코스로 바로 (검색 로봇은 이 페이지 내용을 읽게 둔다)
if (!/bot|crawl|spider|slurp|kakaotalk-scrap|facebookexternalhit|yeti|daum/i.test(navigator.userAgent)) location.replace(document.getElementById("go").href);
</script>
</body>
</html>
'''


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--site", required=True, help="사이트에 올릴 놀코 폴더 (예: _site/nolco)")
    ap.add_argument("--base", required=True, help="놀코 주소, / 로 끝나게")
    args = ap.parse_args(argv)
    site, base = Path(args.site), args.base if args.base.endswith("/") else args.base + "/"
    data = site / "data"
    photos = load(data / "course_photos.json").get("photos", {})
    courses = load(data / "courses.json").get("courses", []) + load(data / "tour_courses.json").get("courses", [])
    fallback = default_og(site)
    (site / "c").mkdir(parents=True, exist_ok=True)
    urls, seen = [], set()
    for c in courses:
        if not c.get("id") or c["id"] in seen or not c.get("stops"):
            continue
        if c.get("source") == "tourapi" and not is_recent(c.get("modified", "")):
            continue
        seen.add(c["id"])
        p = photos.get(c["id"])
        tour_img = str(c.get("image") or "")
        image = og_image(site, c["id"], site / p["img"] if p else None) or (
            "https://" + tour_img[7:] if tour_img.startswith("http://tong.visitkorea.or.kr/") else fallback)
        (site / "c" / f"{c['id']}.html").write_text(page(c, base, image), encoding="utf-8")
        urls.append(f"{base}c/{quote(c['id'])}.html")
    sitemap = "\n".join(f"  <url><loc>{html.escape(u)}</loc></url>" for u in [base] + urls)
    (site / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{sitemap}\n</urlset>\n', encoding="utf-8")
    print(f"공유 페이지 {len(urls)}개, sitemap.xml")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
