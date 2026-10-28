#!/usr/bin/env python3
"""공연마다 페이지(show/<공연id>.html)를 만든다. 사이트를 올릴 때(GitHub Pages 작업) 돌린다.

    python aiiairs/scripts/build_show_pages.py --site _site --base https://45516645sud-stack.github.io/-/

- 구글·네이버가 공연 이름으로 찾을 수 있게, 공연 하나에 주소 하나와 내용(기간·시간·장소·가격·출연)을 글로 담는다
- 검색 결과에 공연 정보가 예쁘게 나오도록 schema.org Event(JSON-LD)를 넣는다
- 카카오톡 미리보기(og:)에 공연 이름·포스터가 나온다
- 사람이 열어도 그대로 볼 수 있는 페이지다 (앱으로 몰래 넘기지 않는다. 검색엔진은 숨은 넘김을 싫어한다)
- 같은 지역·장르의 다른 공연으로 이어지는 링크, 전체 목록(show/index.html), sitemap.xml 도 만든다
"""
from __future__ import annotations

import argparse
import html
import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

KST = timezone(timedelta(hours=9))
CAT = {"theater": "연극", "musical": "뮤지컬", "music": "라이브 음악", "classic": "클래식·국악", "dance": "무용·마임", "kids": "아동·가족"}
# schema.org 의 공연 종류
EVENT_TYPE = {"theater": "TheaterEvent", "musical": "TheaterEvent", "music": "MusicEvent", "classic": "MusicEvent",
              "dance": "DanceEvent", "kids": "ChildrensEvent"}
WD = "월화수목금토일"


def e(s) -> str:
    return html.escape(str(s if s is not None else ""), quote=True)


def slug(fid: str) -> str:
    """파일 이름으로 쓸 공연 id (영문 소문자·숫자·-·_ 만)"""
    return re.sub(r"[^a-z0-9_-]+", "-", str(fid).lower()).strip("-") or "show"


def day(s: str) -> date:
    return date.fromisoformat(s)


def won(n) -> str:
    if n is None:
        return "관람료 확인"
    return "무료" if n == 0 else f"{n:,}원"


def span(f: dict) -> str:
    a, b = day(f["s"]), day(f["e"])
    left = f"{a.year}. {a.month}. {a.day}.({WD[a.weekday()]})"
    if f.get("openrun"):
        return left + " ~ 오픈런"
    if a == b:
        return left
    return f"{left} ~ {b.year}. {b.month}. {b.day}.({WD[b.weekday()]})"


def status(f: dict, today: date) -> str:
    a, b = day(f["s"]), day(f["e"])
    if b < today:
        return "종료"
    if a <= today:
        left = (b - today).days
        return "상시 공연" if f.get("openrun") else ("오늘 마감" if left == 0 else f"진행 중 · {left}일 남음")
    d = (a - today).days
    return "내일 시작" if d == 1 else f"D-{d}"


def poster_src(f: dict) -> str:
    """페이지에 보일 포스터: 사이트에 받아 둔 것 → 공식 포스터 → 그림"""
    p = f.get("poster")
    if isinstance(p, str) and re.fullmatch(r"posters/[\w.-]+", p):
        return "../" + p
    if str(f.get("img", "")).startswith("https://"):
        return f["img"]
    return "../" + str(f.get("art") or "og.png")


def og_image(f: dict, base: str) -> str:
    """카카오톡 미리보기 그림: WebP 를 못 읽는 곳이 있어 공식 포스터(jpg·gif) 주소를 먼저 쓴다"""
    img = str(f.get("img", ""))
    return img if img.startswith("https://") else base + "og.png"


def event_ld(f: dict, url: str, base: str, today: date) -> dict:
    ld = {
        "@context": "https://schema.org",
        "@type": EVENT_TYPE.get(f.get("cat"), "Event"),
        "name": f["t"],
        "startDate": f["s"],
        "endDate": f["e"],
        "eventStatus": "https://schema.org/EventScheduled",
        "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
        "url": url,
        "image": [og_image(f, base)],
        "description": f"{CAT.get(f.get('cat'), '공연')} · {f.get('venue', '')} · {span(f)}",
        "location": {
            "@type": "Place",
            "name": f.get("venue") or "",
            "address": {"@type": "PostalAddress", "streetAddress": f.get("addr") or "", "addressRegion": f.get("region") or "",
                        "addressCountry": "KR"},
        },
    }
    if f.get("fee") is not None:
        ld["offers"] = {"@type": "Offer", "price": f["fee"], "priceCurrency": "KRW",
                        "availability": "https://schema.org/InStock" if day(f["e"]) >= today else "https://schema.org/SoldOut",
                        "url": f.get("url") or url}
        if f.get("fee") == 0:
            ld["isAccessibleForFree"] = True
    if f.get("cast"):
        ld["performer"] = [{"@type": "Person", "name": n.strip()} for n in str(f["cast"]).split(",")[:10] if n.strip()]
    return ld


STYLE = """
:root{--ink:#14110f;--muted:#7a7068;--hair:#e7e2db;--wash:#f6f4f1;--accent:#c2410c}
*{box-sizing:border-box}
body{margin:0;background:#fff;color:var(--ink);font:16px/1.65 "Pretendard Variable",Pretendard,system-ui,sans-serif;word-break:keep-all;overflow-wrap:anywhere}
a{color:inherit}
header{display:flex;align-items:center;gap:8px;max-width:760px;margin:0 auto;padding:14px 16px;border-bottom:1px solid var(--hair)}
header a{display:flex;align-items:center;gap:8px;text-decoration:none;font-weight:800;font-size:20px;letter-spacing:-.03em}
header img{width:26px;height:26px}
main{max-width:760px;margin:0 auto;padding:16px 16px 48px}
.top{display:grid;grid-template-columns:minmax(0,180px) 1fr;gap:18px;align-items:start}
.poster{width:100%;aspect-ratio:3/4;object-fit:cover;border-radius:14px;background:var(--wash);border:1px solid var(--hair)}
.tags{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 8px;padding:0;list-style:none}
.tags li{padding:2px 10px;border-radius:999px;background:var(--wash);font-size:13px;font-weight:600}
.tags .hot{background:var(--accent);color:#fff}.tags .cat{background:#fdeee6;color:var(--accent)}.tags .free{background:#e8f5ec;color:#1b7a3d}
h1{margin:0 0 6px;font-size:26px;line-height:1.3;letter-spacing:-.02em}
.sub{margin:0;color:var(--muted);font-size:15px}
dl{display:grid;grid-template-columns:5.5rem 1fr;gap:6px 14px;margin:22px 0;padding:16px;border:1px solid var(--hair);border-radius:14px;font-size:15px}
dt{color:var(--muted)}dd{margin:0}
.btns{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 28px}
.btn{flex:1 1 200px;display:block;text-align:center;padding:13px 16px;border-radius:12px;font-weight:700;text-decoration:none;border:1px solid var(--ink)}
.btn.main{background:var(--ink);color:#fff}
h2{font-size:18px;margin:28px 0 10px}
ul.more{list-style:none;margin:0;padding:0;border:1px solid var(--hair);border-radius:14px;overflow:hidden}
ul.more li+li{border-top:1px solid var(--hair)}
ul.more a{display:block;padding:12px 14px;text-decoration:none}
ul.more small{display:block;color:var(--muted);font-size:13px}
.note{color:var(--muted);font-size:13px}
footer{max-width:760px;margin:0 auto;padding:20px 16px 40px;color:var(--muted);font-size:13px;border-top:1px solid var(--hair)}
@media (max-width:520px){.top{grid-template-columns:120px 1fr;gap:14px}h1{font-size:21px}dl{grid-template-columns:4.6rem 1fr}}
"""


def head(title: str, desc: str, url: str, image: str, extra: str = "") -> str:
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc[:160])}">
<link rel="canonical" href="{e(url)}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="소극콕">
<meta property="og:locale" content="ko_KR">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc[:160])}">
<meta property="og:image" content="{e(image)}">
<meta property="og:url" content="{e(url)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#efe8da">
<link rel="icon" href="../favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="show.css">
{extra}</head>
<body>
<header><a href="../"><img src="../favicon.svg" alt="" width="26" height="26">소극콕</a></header>
"""


FOOT = """<footer>소극콕 · 전국 소극장·소공연 일정. 공연 정보 출처: 공연예술통합전산망(KOPIS). 일정·가격은 바뀔 수 있으니 예매처에서 한 번 더 확인하세요.</footer>
</body>
</html>
"""


def show_page(f: dict, base: str, today: date, related: list[dict]) -> str:
    url = f"{base}show/{slug(f['id'])}.html"
    cat = CAT.get(f.get("cat"), "공연")
    st = status(f, today)
    title = f"{f['t']} | {f.get('region', '')} {cat} 일정·가격 · 소극콕"
    desc = f"{f['t']} — {f.get('venue', '')} · {span(f)} · {f.get('note') or won(f.get('fee'))}" + (
        f" · {f['runtime']}" if f.get("runtime") else "") + (f" · {f['age']}" if f.get("age") else "")
    ld = json.dumps(event_ld(f, url, base, today), ensure_ascii=False).replace("<", "\\u003c")  # 공연 이름의 < 가 <script> 를 끊지 않게
    tags = [f'<li class="{"hot" if st in ("오늘 마감", "내일 시작") else ""}">{e(st)}</li>', f'<li class="cat">{e(cat)}</li>',
            f"<li>{e(f.get('region'))}</li>"] + (['<li class="free">무료</li>'] if f.get("fee") == 0 else [])
    rows = [("기간", span(f))]
    if f.get("time"):
        rows.append(("시간", f["time"]))
    if f.get("runtime"):
        rows.append(("공연 길이", f["runtime"]))
    rows.append(("장소", f.get("venue")))
    addr = ""
    if f.get("addr"):
        addr = f'{e(f["addr"])} · <a href="https://map.naver.com/p/search/{e(quote(f["addr"]))}" rel="nofollow">네이버 지도</a>'
    rows.append(("관람료", f.get("note") or won(f.get("fee"))))
    if f.get("age"):
        rows.append(("관람 나이", f["age"]))
    if f.get("cast"):
        rows.append(("출연", f["cast"]))
    if f.get("seats"):
        rows.append(("좌석", f"{f['seats']}석"))
    dl = "".join(f"<dt>{e(k)}</dt><dd>{e(v)}</dd>" for k, v in rows)
    if addr:
        dl = dl.replace("<dt>관람료</dt>", f"<dt>주소</dt><dd>{addr}</dd><dt>관람료</dt>", 1)
    btns = []
    if f.get("url"):
        btns.append(f'<a class="btn main" href="{e(f["url"])}" rel="nofollow noopener" target="_blank">예매하러 가기</a>')
    btns.append(f'<a class="btn" href="../?id={e(f["id"])}">소극콕에서 비슷한 공연 보기</a>')
    more = "".join(
        f'<li><a href="{slug(r["id"])}.html">{e(r["t"])}<small>{e(r.get("venue"))} · {e(span(r))}</small></a></li>' for r in related)
    return (head(title, desc, url, og_image(f, base), f'<script type="application/ld+json">{ld}</script>\n') +
            f"""<main>
<div class="top">
<img class="poster" src="{e(poster_src(f))}" alt="{e(f['t'])} 포스터" width="360" height="480" onerror="this.onerror=null;this.src='../{e(f.get('art') or 'og.png')}'">
<div>
<ul class="tags">{''.join(tags)}</ul>
<h1>{e(f['t'])}</h1>
<p class="sub">{e(f.get('venue'))}</p>
</div>
</div>
<dl>{dl}</dl>
<div class="btns">{''.join(btns)}</div>
<p class="note">공연 정보는 <a href="{e(f.get('info') or 'https://www.kopis.or.kr/')}" rel="nofollow">공연예술통합전산망(KOPIS)</a>에서 가져와 매일 새로 고쳐요.</p>
{f'<h2>{e(f.get("region"))} {e(cat)} 더 보기</h2><ul class="more">{more}</ul>' if more else ''}
<p><a href="./">전체 공연 목록</a></p>
</main>
""" + FOOT)


def index_page(items: list[dict], base: str) -> str:
    url = f"{base}show/"
    by = {}
    for f in items:
        by.setdefault(f.get("region") or "기타", []).append(f)
    order = sorted(by, key=lambda r: (-len(by[r]), r))
    parts = []
    for r in order:
        lis = "".join(
            f'<li><a href="{slug(f["id"])}.html">{e(f["t"])}<small>{e(CAT.get(f.get("cat"), ""))} · {e(f.get("venue"))} · {e(span(f))}</small></a></li>'
            for f in sorted(by[r], key=lambda f: (f["s"], f["t"])))
        parts.append(f'<h2 id="{e(r)}">{e(r)} <small class="note">{len(by[r])}개</small></h2><ul class="more">{lis}</ul>')
    toc = " · ".join(f'<a href="#{e(r)}">{e(r)}</a>' for r in order)
    title = "전국 소극장·소공연 전체 목록 · 소극콕"
    desc = f"지금 열리거나 곧 열리는 전국 소극장·소공연 {len(items)}개. 연극·뮤지컬·라이브 음악·클래식·국악·무용·어린이 공연을 지역별로."
    return head(title, desc, url, base + "og.png") + f"""<main>
<h1>전국 소극장·소공연 {len(items)}개</h1>
<p class="sub">{toc}</p>
{''.join(parts)}
</main>
""" + FOOT


def related_for(f: dict, items: list[dict], n: int = 6) -> list[dict]:
    same = [x for x in items if x is not f and x.get("region") == f.get("region") and x.get("cat") == f.get("cat")]
    if len(same) < n:
        same += [x for x in items if x is not f and x not in same and x.get("region") == f.get("region")]
    return same[:n]


def build(site: Path, base: str, today: date) -> tuple[int, int]:
    data = json.loads((site / "data" / "fairs.json").read_text(encoding="utf-8"))
    items = [f for f in data.get("items", []) if f.get("id") and f.get("t") and f.get("s") and f.get("e")]
    upcoming = sorted((f for f in items if day(f["e"]) >= today), key=lambda f: (f["s"], f["t"]))
    out = site / "show"
    out.mkdir(parents=True, exist_ok=True)
    (out / "show.css").write_text(STYLE.strip() + "\n", encoding="utf-8")
    for f in items:
        (out / f"{slug(f['id'])}.html").write_text(show_page(f, base, today, related_for(f, upcoming)), encoding="utf-8")
    (out / "index.html").write_text(index_page(upcoming, base), encoding="utf-8")
    # sitemap: 첫 화면·전체 목록·아직 끝나지 않은 공연 (끝난 공연은 페이지만 남기고 지도에서는 뺀다)
    stamp = today.isoformat()
    urls = [(base, "daily"), (base + "show/", "daily"), (base + "privacy.html", "yearly")] + [
        (f"{base}show/{slug(f['id'])}.html", "weekly") for f in upcoming]
    body = "\n".join(f"  <url><loc>{e(u)}</loc><lastmod>{stamp}</lastmod><changefreq>{c}</changefreq></url>" for u, c in urls)
    (site / "sitemap.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{body}\n</urlset>\n',
        encoding="utf-8")
    return len(items), len(upcoming)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--site", required=True, help="사이트에 올릴 폴더 (예: _site)")
    ap.add_argument("--base", required=True, help="사이트 주소, / 로 끝나게")
    ap.add_argument("--today", help="오늘 날짜 YYYY-MM-DD (시험용, 기본은 한국 오늘)")
    args = ap.parse_args(argv)
    base = args.base if args.base.endswith("/") else args.base + "/"
    today = date.fromisoformat(args.today) if args.today else datetime.now(KST).date()
    pages, listed = build(Path(args.site), base, today)
    print(f"공연 페이지 {pages}개, sitemap.xml 에 {listed}개")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
