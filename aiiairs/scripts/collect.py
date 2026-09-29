#!/usr/bin/env python3
"""AIIairs 일정 수집기.

공공 API와 운영자 입력 파일에서 행사를 모아 페이지가 읽는 data/fairs.json 을 만든다.
표준 라이브러리만 쓴다 (Python 3.9+).

출처
  - KOPIS 공연예술통합전산망 오픈API      : 연극·뮤지컬·콘서트 등 공연 (환경변수 KOPIS_API_KEY)
  - 한국문화정보원 한눈에보는문화정보 API  : 공연·전시 (환경변수 DATA_GO_KR_KEY, 공공데이터포털 '디코딩' 키)
  - data/manual.csv                        : 박람회 등 운영자가 직접 넣는 행사 (키 필요 없음)

사용
  python3 aiiairs/scripts/collect.py                 # 실제 API 호출
  python3 aiiairs/scripts/collect.py --fixtures      # 저장된 예시 응답으로 동작 확인 (네트워크 없이)
  python3 aiiairs/scripts/collect.py --days 120 --max-kopis 300

키가 없는 출처는 건너뛴다. 모든 출처에서 한 건도 못 얻으면 기존 파일을 그대로 두고 1로 끝난다.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]          # aiiairs/
DATA_DIR = ROOT / "data"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
KST = dt.timezone(dt.timedelta(hours=9))
UA = "AIIairs-collector/1.0 (+https://expomoa.com/)"

KOPIS_BASE = "https://www.kopis.or.kr/openApi/restful"
CULTURE_URL = "https://apis.data.go.kr/B553457/nopenapi/rest/publicperformancedisplays/period"

# ------------------------------------------------------------------ 공통 매핑

REGION_PREFIX = [
    ("서울", "서울"), ("경기", "경기"), ("인천", "인천"), ("부산", "부산"), ("대구", "대구"),
    ("전남광주", "광주·전남"),  # 2026 통합 행정구역: 광주와 전남을 구분할 수 없어 함께 묶는다
    ("대전", "대전"), ("광주", "광주"), ("울산", "울산"), ("세종", "세종"), ("강원", "강원"),
    ("충청북", "충북"), ("충북", "충북"), ("충청남", "충남"), ("충남", "충남"),
    ("전라북", "전북"), ("전북", "전북"), ("전라남", "전남"), ("전남", "전남"),
    ("경상북", "경북"), ("경북", "경북"), ("경상남", "경남"), ("경남", "경남"), ("제주", "제주"),
]


def region_of(*texts: str) -> str:
    """'서울특별시', '경기도 고양시', '부산' 같은 표기를 페이지 지역명으로 바꾼다."""
    for text in texts:
        t = (text or "").strip()
        for prefix, name in REGION_PREFIX:
            if t.startswith(prefix):
                return name
    for text in texts:
        t = (text or "")
        for prefix, name in REGION_PREFIX:
            if prefix in t:
                return name
    return "기타"


# KOPIS 장르 → (페이지 분류, 포스터 대체 그림, 취향 태그)
KOPIS_GENRE = {
    "연극": ("stage", "img/daehakro-duo.webp", ["데이트", "친구", "영감"]),
    "뮤지컬": ("stage", "img/daegu-musical.webp", ["데이트", "친구", "활기"]),
    "대중음악": ("stage", "img/hongdae-indie.webp", ["활기", "친구", "데이트"]),
    "서양음악(클래식)": ("stage", "img/house-quartet.webp", ["조용한", "데이트"]),
    "한국음악(국악)": ("stage", "img/jeju-acoustic.webp", ["조용한", "가족"]),
    "무용": ("stage", "img/gwangju-mime.webp", ["영감", "조용한"]),
    "대중무용": ("stage", "img/gwangju-mime.webp", ["활기", "친구"]),
    "서커스/마술": ("stage", "img/gwangju-mime.webp", ["가족", "아이", "활기"]),
    "복합": ("stage", "img/daehakro-duo.webp", ["영감"]),
}

# 문화정보원 분야명 → 페이지 분류 (앞에서부터 처음 맞는 것)
CULTURE_REALM = [
    (("연극", "뮤지컬", "음악", "국악", "무용", "오페라", "콘서트", "공연"), "stage"),
    (("미술", "사진", "건축", "디자인", "공예", "전시"), "art"),
    (("아동", "가족", "어린이"), "family"),
    (("교육", "강연", "체험"), "career"),
    (("축제", "행사", "여행"), "travel"),
]

MANUAL_CAT = {
    # 한글 분류명 → 페이지 분류 키
    "식음료": "food", "먹거리": "food", "리빙": "living", "리빙·인테리어": "living", "인테리어": "living",
    "웨딩": "family", "육아": "family", "웨딩·육아": "family", "도서": "culture", "도서·문화": "culture",
    "문화": "culture", "아트": "art", "아트·공예": "art", "공예": "art", "미술": "art", "테크": "tech",
    "테크·IT": "tech", "IT": "tech", "취업": "career", "교육": "career", "취업·교육": "career",
    "여행": "travel", "레저": "travel", "여행·레저": "travel", "반려동물": "pet", "펫": "pet",
    "뷰티": "beauty", "패션": "beauty", "뷰티·패션": "beauty", "산업": "industry", "비즈니스": "industry",
    "산업·비즈니스": "industry", "공연": "stage", "소극장": "stage", "공연·소극장": "stage",
}
PAGE_CATS = set(MANUAL_CAT.values())


def realm_to_cat(realm: str) -> str:
    for words, cat in CULTURE_REALM:
        if any(w in (realm or "") for w in words):
            return cat
    return "culture"


def parse_fee(text: str | None) -> int | None:
    """'전석무료', '무료' → 0 / 'R석 50,000원, S석 30,000원' → 30000 (가장 싼 값) / 모르면 None."""
    if not text:
        return None
    t = text.replace(" ", "")
    if "무료" in t and not re.search(r"\d{1,3}(,\d{3})+원|\d{4,}원", t):
        return 0
    prices = [int(p.replace(",", "")) for p in re.findall(r"(\d{1,3}(?:,\d{3})+|\d{3,})\s*원", text)]
    prices = [p for p in prices if p >= 100]
    return min(prices) if prices else None


def parse_day(text: str | None) -> dt.date | None:
    """'2026.10.02', '20261002', '2026-10-02' 모두 받는다."""
    if not text:
        return None
    digits = re.sub(r"\D", "", text)[:8]
    if len(digits) != 8:
        return None
    try:
        return dt.date(int(digits[:4]), int(digits[4:6]), int(digits[6:8]))
    except ValueError:
        return None


def https(url: str | None) -> str | None:
    if not url:
        return None
    url = url.strip()
    if url.startswith("//"):
        url = "https:" + url
    if url.startswith("http://"):
        url = "https://" + url[len("http://"):]
    return url if url.startswith("https://") else None


def clip(text: str | None, n: int = 160) -> str:
    t = re.sub(r"<[^>]+>", " ", text or "")
    t = re.sub(r"\s+", " ", t).strip()
    return t if len(t) <= n else t[: n - 1].rstrip() + "…"


def slug(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:10]


# ------------------------------------------------------------------ HTTP / XML

def fetch(url: str, *, tries: int = 3, timeout: int = 20) -> bytes:
    last: Exception | None = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as res:
                return res.read()
        except (urllib.error.URLError, TimeoutError) as e:  # 네트워크 오류만 재시도
            last = e
            time.sleep(2 ** i)
    raise RuntimeError(f"요청 실패: {redact(url)} ({last})")


def redact(url: str) -> str:
    return re.sub(r"(service|serviceKey)=[^&]+", r"\1=***", url)


def records(xml_bytes: bytes, must: tuple[str, ...]) -> list[dict]:
    """응답 XML에서 `must` 필드를 모두 가진 요소를 한 건씩 dict 로 꺼낸다.

    출처마다 감싸는 태그 이름이 달라도(db, perforList, item …) 동작하도록 구조 대신 필드로 찾는다.
    """
    root = ET.fromstring(xml_bytes)
    check_api_error(root)
    out = []
    for el in root.iter():
        kids = {c.tag: c for c in el}
        if all(k in kids for k in must):
            rec = {}
            for c in el:
                if len(c):  # 하위 목록(예: relates) 은 그대로 둔다
                    rec[c.tag] = c
                else:
                    rec[c.tag] = (c.text or "").strip()
            out.append(rec)
    return out


def check_api_error(root: ET.Element) -> None:
    code = root.findtext(".//resultCode") or root.findtext(".//returnReasonCode") or root.findtext(".//ReturnCode")
    msg = root.findtext(".//resultMsg") or root.findtext(".//returnAuthMsg") or root.findtext(".//ErrMsg") or ""
    if code and code not in ("00", "0", "0000") and "NORMAL" not in msg.upper():
        raise RuntimeError(f"API 오류 {code}: {msg}")


def first(rec: dict, *names: str) -> str:
    for n in names:
        v = rec.get(n)
        if isinstance(v, str) and v:
            return v
    return ""


# ------------------------------------------------------------------ 출처: KOPIS

def windows(start: dt.date, end: dt.date, span: int = 31):
    """KOPIS 목록 조회는 기간을 31일 이하로 나눠 부른다."""
    cur = start
    while cur <= end:
        stop = min(end, cur + dt.timedelta(days=span - 1))
        yield cur, stop
        cur = stop + dt.timedelta(days=1)


def collect_kopis(key: str, start: dt.date, end: dt.date, limit: int, detail_limit: int, fixtures: bool) -> list[dict]:
    seen: dict[str, dict] = {}
    for a, b in windows(start, end):
        page = 1
        while len(seen) < limit:
            if fixtures:
                body = (FIXTURES / "kopis_list.xml").read_bytes()
            else:
                q = urllib.parse.urlencode({
                    "service": key, "stdate": a.strftime("%Y%m%d"), "eddate": b.strftime("%Y%m%d"),
                    "cpage": page, "rows": 100,
                })
                body = fetch(f"{KOPIS_BASE}/pblprfr?{q}")
            rows = records(body, ("mt20id", "prfnm"))
            for r in rows:
                if r["mt20id"] not in seen and len(seen) < limit:
                    seen[r["mt20id"]] = r
            if fixtures or len(rows) < 100:
                break
            page += 1
        if fixtures:
            break

    items = []
    for i, (pid, r) in enumerate(seen.items()):
        detail = {}
        if i < detail_limit:
            try:
                body = (FIXTURES / "kopis_detail.xml").read_bytes() if fixtures else \
                    fetch(f"{KOPIS_BASE}/pblprfr/{urllib.parse.quote(pid)}?" + urllib.parse.urlencode({"service": key}))
                got = records(body, ("mt20id", "prfnm"))
                # 다른 공연의 상세가 섞이지 않도록 ID가 같은 것만 쓴다.
                detail = next((g for g in got if g.get("mt20id") == pid), {})
            except Exception as e:  # 상세 한 건 실패는 목록 정보로 대신한다
                print(f"  · KOPIS 상세 건너뜀 {pid}: {e}", file=sys.stderr)
        item = kopis_item(r, detail)
        if item:
            items.append(item)
    return items


def kopis_item(r: dict, d: dict) -> dict | None:
    s, e = parse_day(first(r, "prfpdfrom")), parse_day(first(r, "prfpdto"))
    if not s or not e:
        return None
    genre = first(d, "genrenm") or first(r, "genrenm")
    cat, art, tags = KOPIS_GENRE.get(genre, ("stage", "img/daehakro-duo.webp", ["영감"]))
    tags = list(tags)
    if first(d, "child") == "Y" or first(r, "child") == "Y":
        tags += ["가족", "아이"]
    url = None
    relates = d.get("relates")
    if isinstance(relates, ET.Element):
        for rel in relates:
            url = https(rel.findtext("relateurl"))
            if url:
                break
    fee_text = first(d, "pcseguidance")
    venue = first(d, "fcltynm") or first(r, "fcltynm")
    summary = clip(first(d, "sty"))
    return {
        "id": "kopis-" + first(r, "mt20id").lower(),
        "t": first(r, "prfnm"),
        "cat": cat,
        "region": region_of(first(d, "area"), first(r, "area"), venue),
        "venue": venue,
        "s": s.isoformat(),
        "e": e.isoformat(),
        "fee": parse_fee(fee_text),
        "note": clip(fee_text, 60) if fee_text and parse_fee(fee_text) != 0 else "",
        "tags": sorted(set(tags)),
        "d": summary or f"{genre or '공연'} · {venue}",
        "img": https(first(d, "poster") or first(r, "poster")),
        "art": art,
        "url": url,
        "src": "kopis",
    }


# ------------------------------------------------------------------ 출처: 한국문화정보원

def collect_culture(key: str, start: dt.date, end: dt.date, limit: int, fixtures: bool) -> list[dict]:
    items: list[dict] = []
    page = 1
    while len(items) < limit:
        if fixtures:
            body = (FIXTURES / "culture_period.xml").read_bytes()
        else:
            q = urllib.parse.urlencode({
                "serviceKey": key, "from": start.strftime("%Y%m%d"), "to": end.strftime("%Y%m%d"),
                "cPage": page, "rows": 100,
            })
            body = fetch(f"{CULTURE_URL}?{q}")
        rows = records(body, ("title", "startDate"))
        for r in rows:
            item = culture_item(r)
            if item and len(items) < limit:
                items.append(item)
        if fixtures or len(rows) < 100:
            break
        page += 1
    return items


def culture_item(r: dict) -> dict | None:
    s, e = parse_day(first(r, "startDate")), parse_day(first(r, "endDate", "startDate"))
    title = first(r, "title")
    if not s or not e or not title:
        return None
    realm = first(r, "realmName", "realm")
    venue = first(r, "place", "placeName")
    cat = realm_to_cat(realm)
    fee_text = first(r, "price", "fee")
    return {
        "id": "kcisa-" + (first(r, "seq") or slug(title, s.isoformat(), venue)),
        "t": title,
        "cat": cat,
        "region": region_of(first(r, "area"), first(r, "sigungu"), venue, first(r, "placeAddr")),
        "venue": venue,
        "s": s.isoformat(),
        "e": e.isoformat(),
        "fee": parse_fee(fee_text),
        "note": "",
        "tags": ["영감"] if cat == "art" else [],
        "d": clip(first(r, "contents1", "description")) or f"{realm or '문화행사'} · {venue}",
        "img": https(first(r, "thumbnail", "imgUrl")),
        "url": https(first(r, "url", "placeUrl")),
        "src": "kcisa",
    }


# ------------------------------------------------------------------ 출처: 운영자 입력(CSV)

MANUAL_HEADER = ["행사명", "분류", "지역", "장소", "시작일", "종료일", "관람료", "설명", "포스터", "링크", "메모", "태그"]


def collect_manual(path: Path) -> list[dict]:
    if not path.exists():
        return []
    items = []
    with path.open(encoding="utf-8-sig", newline="") as fh:
        for n, row in enumerate(csv.DictReader(fh), start=2):
            title = (row.get("행사명") or "").strip()
            if not title or title.startswith("#"):
                continue
            s, e = parse_day(row.get("시작일")), parse_day(row.get("종료일") or row.get("시작일"))
            if not s or not e:
                print(f"  · manual.csv {n}행: 날짜를 읽을 수 없어 건너뜀 ({title})", file=sys.stderr)
                continue
            raw_cat = (row.get("분류") or "").strip()
            cat = raw_cat if raw_cat in PAGE_CATS else MANUAL_CAT.get(raw_cat, "industry")
            fee_raw = (row.get("관람료") or "").strip()
            fee = parse_fee(fee_raw) if not fee_raw.isdigit() else int(fee_raw)
            venue = (row.get("장소") or "").strip()
            items.append({
                "id": "manual-" + slug(title, s.isoformat(), venue),
                "t": title,
                "cat": cat,
                "region": region_of(row.get("지역") or "", venue),
                "venue": venue,
                "s": s.isoformat(),
                "e": e.isoformat(),
                "fee": fee,
                "note": (row.get("메모") or "").strip(),
                "tags": [t.strip() for t in (row.get("태그") or "").split("/") if t.strip()],
                "d": clip(row.get("설명")),
                "img": https(row.get("포스터")),
                "url": https(row.get("링크")),
                "src": "manual",
            })
    return items


# ------------------------------------------------------------------ 합치기

def norm_title(t: str) -> str:
    return re.sub(r"[\s\W_]+", "", t).lower()


def merge(groups: list[list[dict]], start: dt.date, end: dt.date) -> list[dict]:
    """먼저 온 출처가 우선. 제목·시작일이 같은 행사는 한 번만 남긴다."""
    seen, out = set(), []
    for group in groups:
        for it in group:
            if parse_day(it["e"]) < start or parse_day(it["s"]) > end:
                continue
            key = (norm_title(it["t"]), it["s"])
            if key in seen:
                continue
            seen.add(key)
            out.append({k: v for k, v in it.items() if v not in (None, "", [])} | {"fee": it.get("fee")})
    out.sort(key=lambda x: (x["s"], x["t"]))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="AIIairs 일정 수집")
    ap.add_argument("--out", default=str(DATA_DIR / "fairs.json"))
    ap.add_argument("--manual", default=str(DATA_DIR / "manual.csv"))
    ap.add_argument("--days", type=int, default=180, help="오늘부터 며칠 뒤까지 모을지")
    ap.add_argument("--past-days", type=int, default=0, help="이미 끝난 행사를 며칠 전까지 남길지")
    ap.add_argument("--max-kopis", type=int, default=400)
    ap.add_argument("--kopis-detail", type=int, default=150, help="요금·줄거리를 가져올 상세 조회 건수")
    ap.add_argument("--max-culture", type=int, default=400)
    ap.add_argument("--fixtures", action="store_true", help="저장된 예시 응답으로 실행 (네트워크·키 불필요)")
    args = ap.parse_args(argv)

    today = dt.datetime.now(KST).date()
    start, end = today - dt.timedelta(days=args.past_days), today + dt.timedelta(days=args.days)
    if args.fixtures:  # 예시 응답의 날짜에 맞춰 넓게 본다
        start, end = dt.date(2000, 1, 1), dt.date(2100, 1, 1)

    sources = []
    groups: list[list[dict]] = []

    def run(name: str, label: str, fn, needs_key: str | None = None):
        key = os.environ.get(needs_key, "").strip() if needs_key else ""
        if needs_key and not key and not args.fixtures:
            print(f"- {label}: {needs_key} 가 없어 건너뜀")
            sources.append({"name": name, "label": label, "count": 0, "ok": False, "error": "no key"})
            return
        try:
            got = fn(key or "FIXTURE")
            print(f"- {label}: {len(got)}건")
            sources.append({"name": name, "label": label, "count": len(got), "ok": True})
            groups.append(got)
        except Exception as e:
            print(f"- {label}: 실패 — {e}", file=sys.stderr)
            sources.append({"name": name, "label": label, "count": 0, "ok": False, "error": str(e)[:200]})

    run("manual", "운영자 입력", lambda _k: collect_manual(Path(args.manual)))
    run("kopis", "KOPIS 공연예술통합전산망", lambda k: collect_kopis(k, start, end, args.max_kopis, args.kopis_detail, args.fixtures), "KOPIS_API_KEY")
    run("kcisa", "한국문화정보원", lambda k: collect_culture(k, start, end, args.max_culture, args.fixtures), "DATA_GO_KR_KEY")

    items = merge(groups, start, end)
    if not items:
        print("모은 일정이 없어 기존 파일을 그대로 둡니다.", file=sys.stderr)
        return 1

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    try:  # 일정이 그대로면 파일을 건드리지 않는다 (매일 빈 커밋이 생기지 않게)
        prev = json.loads(out.read_text(encoding="utf-8"))
        if prev.get("items") == items:
            print(f"일정 {len(items)}건, 바뀐 것 없음")
            return 0
    except (OSError, ValueError):
        pass
    payload = {
        "generatedAt": dt.datetime.now(KST).isoformat(timespec="seconds"),
        "sample": False,
        "sources": sources,
        "items": items,
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{out} 에 {len(items)}건 저장")
    return 0


if __name__ == "__main__":
    sys.exit(main())
