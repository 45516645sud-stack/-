#!/usr/bin/env python3
"""AIIairs 일정 수집기.

공공 API와 운영자 입력 파일에서 행사를 모아 페이지가 읽는 data/fairs.json 을 만든다.
표준 라이브러리만 쓴다 (Python 3.9+).

출처
  - KOPIS 공연예술통합전산망 오픈API      : 연극·뮤지컬·콘서트 등 공연 (환경변수 KOPIS_API_KEY)
  - 한국문화정보원 한눈에보는문화정보 API  : 공연 (환경변수 DATA_GO_KR_KEY, 공공데이터포털 '디코딩' 키, 전시 등은 제외)
  - data/manual.csv                        : API에 없는 소공연을 운영자가 직접 넣는 곳 (키 필요 없음)

소극장 사이트이므로 KOPIS 공연은 공연장 좌석 수가 --max-seats(기본 300) 이하인 것만 싣는다.

사용
  python3 aiiairs/scripts/collect.py                 # 실제 API 호출
  python3 aiiairs/scripts/collect.py --fixtures      # 저장된 예시 응답으로 동작 확인 (네트워크 없이)
  python3 aiiairs/scripts/collect.py --days 120 --max-kopis 300

키가 없는 출처는 건너뛴다. 모든 출처에서 한 건도 못 얻으면 기존 파일을 그대로 두고 1로 끝난다.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import csv
import datetime as dt
import hashlib
import io
import json
import math
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
POSTER_DIR = ROOT / "posters"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
KST = dt.timezone(dt.timedelta(hours=9))
UA = "AIIairs-collector/1.0 (+https://expomoa.com/)"

KOPIS_BASE = "https://www.kopis.or.kr/openApi/restful"
# 공연마다 있는 KOPIS 공식 상세 페이지 (예매처 링크가 없을 때도 늘 붙일 수 있다)
KOPIS_PAGE = "https://www.kopis.or.kr/por/db/pblprfr/pblprfrView.do?menuId=MNU_00020&mt20Id={}"
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


# 페이지 분류(장르): theater 연극 / musical 뮤지컬 / music 라이브 음악 / classic 클래식·국악 / dance 무용·마임 / kids 아동·가족
PAGE_CATS = {"theater", "musical", "music", "classic", "dance", "kids"}

# KOPIS 장르 → (페이지 분류, 포스터 대체 그림, 취향 태그)
KOPIS_GENRE = {
    "연극": ("theater", "img/daehakro-duo.webp", ["데이트", "친구", "영감"]),
    "뮤지컬": ("musical", "img/daegu-musical.webp", ["데이트", "친구", "활기"]),
    "대중음악": ("music", "img/hongdae-indie.webp", ["활기", "친구", "데이트"]),
    "서양음악(클래식)": ("classic", "img/house-quartet.webp", ["조용한", "데이트"]),
    "한국음악(국악)": ("classic", "img/jeju-acoustic.webp", ["조용한", "가족"]),
    "무용": ("dance", "img/gwangju-mime.webp", ["영감", "조용한"]),
    "무용(서양/한국무용)": ("dance", "img/gwangju-mime.webp", ["영감", "조용한"]),
    "대중무용": ("dance", "img/gwangju-mime.webp", ["활기", "친구"]),
    "서커스/마술": ("dance", "img/gwangju-mime.webp", ["가족", "아이", "활기"]),
    "복합": ("theater", "img/daehakro-duo.webp", ["영감"]),
}
KIDS_ART = "img/gwangju-mime.webp"
# KOPIS 장르 이름은 '무용(서양/한국무용)'처럼 바뀌거나 길어질 수 있어, 정확히 맞지 않으면 낱말로 찾는다.
GENRE_WORDS = [
    (("뮤지컬",), "뮤지컬"),
    (("무용", "발레", "댄스"), "무용"),
    (("서커스", "마술"), "서커스/마술"),
    (("클래식", "서양음악", "오페라"), "서양음악(클래식)"),
    (("국악", "한국음악"), "한국음악(국악)"),
    (("대중음악", "콘서트"), "대중음악"),
    (("연극",), "연극"),
]


def genre_info(genre: str) -> tuple[str, str, list[str]]:
    """KOPIS 장르 이름 → (페이지 분류, 대체 그림, 취향 태그)"""
    g = (genre or "").strip()
    if g in KOPIS_GENRE:
        return KOPIS_GENRE[g]
    for words, key in GENRE_WORDS:
        if any(w in g for w in words):
            return KOPIS_GENRE[key]
    return ("theater", "img/daehakro-duo.webp", ["영감"])

# 문화정보원 분야명 → 페이지 분류 (앞에서부터 처음 맞는 것). 공연이 아닌 분야(전시 등)는 버린다.
CULTURE_REALM = [
    (("아동", "가족", "어린이"), "kids"),
    (("뮤지컬",), "musical"),
    (("연극",), "theater"),
    (("클래식", "오페라", "국악", "실내악"), "classic"),
    (("무용", "발레", "마임", "서커스"), "dance"),
    (("음악", "콘서트", "공연"), "music"),
]

MANUAL_CAT = {
    # 한글 분류명 → 페이지 분류 키
    "연극": "theater", "낭독": "theater", "뮤지컬": "musical",
    "음악": "music", "라이브": "music", "라이브 음악": "music", "콘서트": "music", "재즈": "music", "인디": "music", "밴드": "music",
    "클래식": "classic", "국악": "classic", "클래식·국악": "classic",
    "무용": "dance", "마임": "dance", "서커스": "dance", "무용·마임": "dance",
    "아동": "kids", "가족": "kids", "아동·가족": "kids",
}

def realm_to_cat(realm: str) -> str | None:
    for words, cat in CULTURE_REALM:
        if any(w in (realm or "") for w in words):
            return cat
    return None


# ------------------------------------------------------------------ 소극장 판별

# 좌석 수를 모를 때 공연장 이름으로 판단한다.
BIG_WORDS = ("대극장", "대공연장", "체육관", "아레나", "경기장", "올림픽홀", "돔", "컨벤션", "대강당", "세종문화회관", "예술의전당 오페라")
SMALL_WORDS = ("소극장", "소공연장", "블랙박스", "라이브", "클럽", "스튜디오", "살롱", "카페", "갤러리")


def is_small(venue: str, seats: int | None, max_seats: int) -> bool:
    """좌석 수가 있으면 그것으로, 없으면 이름으로 소극장인지 정한다."""
    if seats is not None:
        return seats <= max_seats
    v = venue or ""
    if any(w in v for w in SMALL_WORDS):
        return True
    return not any(w in v for w in BIG_WORDS)


def hall_of(venue: str) -> str:
    """'대학로 아트원씨어터 (2관)' → '2관'. 괄호가 없으면 빈 문자열."""
    m = re.search(r"\(([^()]*)\)\s*$", venue or "")
    return m.group(1).strip() if m else ""


def clean_venue(name: str) -> str:
    """KOPIS 시설명 '공연장 (시설)'에서 같은 이름이 괄호로 반복되면 한 번만 남긴다.
    '예시소극장 (예시소극장)' → '예시소극장', '롯데마트 [월드컵] (행복을 주는 가족극장)' → 그대로"""
    name = (name or "").strip()
    if " (" not in name or not name.endswith(")"):
        return name
    squash = lambda t: re.sub(r"\s+", "", t)
    cuts = [m.start() for m in re.finditer(r" \(", name)]
    # 1) 이름 안에도 괄호가 있을 수 있어, 모든 자리에서 '앞 == 괄호 속'인지 본다
    for i in cuts:
        head, tail = name[:i].strip(), name[i + 2:-1].strip()
        if head and squash(head) == squash(tail):
            return head
    # 2) 마지막 괄호 속이 앞 이름의 일부일 때 ('더퍼포머씨어터 [화성] (더퍼포머씨어터)')
    head, tail = name[:cuts[-1]].strip(), name[cuts[-1] + 2:-1].strip()
    if "(" not in tail and tail and squash(tail) in squash(head):
        return head
    return name


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


def collect_kopis(key: str, start: dt.date, end: dt.date, limit: int, detail_limit: int, fixtures: bool,
                  max_seats: int = 300) -> list[dict]:
    seen: dict[str, dict] = {}
    spans = list(windows(start, end))
    # 첫 달에서 한도가 다 차지 않도록 기간마다 한도를 나눠 쓴다.
    per = limit if fixtures else max(1, math.ceil(limit / len(spans)))
    for a, b in spans:
        page = 1
        cap = min(limit, len(seen) + per)
        while len(seen) < cap:
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
                if r["mt20id"] not in seen and len(seen) < cap:
                    seen[r["mt20id"]] = r
            if fixtures or len(rows) < 100:
                break
            page += 1
        if fixtures:
            break

    def detail_of(pid: str) -> dict:
        try:
            body = (FIXTURES / "kopis_detail.xml").read_bytes() if fixtures else \
                fetch(f"{KOPIS_BASE}/pblprfr/{urllib.parse.quote(pid)}?" + urllib.parse.urlencode({"service": key}))
            got = records(body, ("mt20id", "prfnm"))
            # 다른 공연의 상세가 섞이지 않도록 ID가 같은 것만 쓴다.
            return next((g for g in got if g.get("mt20id") == pid), {})
        except Exception as e:  # 상세 한 건 실패는 목록 정보로 대신한다
            print(f"  · KOPIS 상세 건너뜀 {pid}: {e}", file=sys.stderr)
            return {}

    ids = list(seen)
    wanted = ids[:detail_limit]
    details: dict[str, dict] = {}
    # 상세 조회는 한 건씩이라 느리다. 몇 건씩 동시에 부른다.
    with cf.ThreadPoolExecutor(max_workers=6) as pool:
        for pid, d in zip(wanted, pool.map(detail_of, wanted)):
            details[pid] = d

    # 공연장(시설) 좌석 수: 같은 시설은 한 번만 조회한다.
    def place_of(fid: str) -> list[tuple[str, int]]:
        try:
            body = (FIXTURES / "kopis_place.xml").read_bytes() if fixtures else \
                fetch(f"{KOPIS_BASE}/prfplc/{urllib.parse.quote(fid)}?" + urllib.parse.urlencode({"service": key}))
            halls = [(h.get("prfplcnm", ""), int(re.sub(r"\D", "", h.get("seatscale", "")) or 0))
                     for h in records(body, ("prfplcnm", "seatscale"))]
            if not halls:  # 공연장 목록이 없으면 시설 전체 좌석 수
                whole = records(body, ("fcltynm", "seatscale"))
                halls = [("", int(re.sub(r"\D", "", whole[0].get("seatscale", "")) or 0))] if whole else []
            return [h for h in halls if h[1] > 0]
        except Exception as e:
            print(f"  · KOPIS 시설 건너뜀 {fid}: {e}", file=sys.stderr)
            return []

    fids = sorted({first(d, "mt10id") for d in details.values() if first(d, "mt10id")})
    with cf.ThreadPoolExecutor(max_workers=6) as pool:
        places = dict(zip(fids, pool.map(place_of, fids)))

    items, dropped = [], 0
    for pid in ids:
        d = details.get(pid, {})
        item = kopis_item(seen[pid], d)
        if not item:
            continue
        seats = seats_for(item["venue"], places.get(first(d, "mt10id"), []))
        if not is_small(item["venue"], seats, max_seats):
            dropped += 1
            continue
        if seats:
            item["seats"] = seats
        items.append(item)
    print(f"  · {max_seats}석이 넘는 공연장 {dropped}건 제외")
    return items


def seats_for(venue: str, halls: list[tuple[str, int]]) -> int | None:
    """공연 장소 '시설 (공연장)'에 맞는 공연장 좌석 수. 모르면 None."""
    if not halls:
        return None
    if len(halls) == 1:
        return halls[0][1]
    want = re.sub(r"\s+", "", hall_of(venue))
    if want:
        for name, seats in halls:
            n = re.sub(r"\s+", "", name)
            if n and (n == want or want in n or n in want):
                return seats
    return None


def kopis_item(r: dict, d: dict) -> dict | None:
    s, e = parse_day(first(r, "prfpdfrom")), parse_day(first(r, "prfpdto"))
    if not s or not e:
        return None
    genre = first(d, "genrenm") or first(r, "genrenm")
    cat, art, tags = genre_info(genre)
    tags = list(tags)
    if first(d, "child") == "Y" or first(r, "child") == "Y":
        cat, art = "kids", KIDS_ART
        tags += ["가족", "아이"]
    url = None
    relates = d.get("relates")
    if isinstance(relates, ET.Element):
        for rel in relates:
            url = https(rel.findtext("relateurl"))
            if url:
                break
    fee_text = first(d, "pcseguidance")
    venue = clean_venue(first(d, "fcltynm") or first(r, "fcltynm"))
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
        "url": url,                                        # 예매처 (없을 수 있음)
        "info": KOPIS_PAGE.format(urllib.parse.quote(first(r, "mt20id"))),  # KOPIS 공식 공연 페이지
        "openrun": True if (first(d, "openrun") or first(r, "openrun")) == "Y" else None,
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
    if not cat:  # 전시·축제 등 공연이 아닌 것은 싣지 않는다
        return None
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
        "tags": ["가족", "아이"] if cat == "kids" else [],
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
            cat = raw_cat if raw_cat in PAGE_CATS else MANUAL_CAT.get(raw_cat, "theater")
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


# ------------------------------------------------------------------ 포스터 내려받기

def image_ext(data: bytes) -> str | None:
    """그림 파일인지 머리 바이트로 확인한다 (오류 페이지 HTML 등을 걸러낸다)."""
    if data[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return ".gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    return None


def cache_posters(items: list[dict], folder: Path, width: int = 360, getter=None) -> int:
    """공식 포스터(img)를 내려받아 작게 줄여 folder 에 저장하고, 각 행사에 poster 경로를 단다.

    - 이미 받은 포스터는 다시 받지 않는다.
    - Pillow 가 있으면 가로 width 픽셀 WebP 로 줄이고, 없으면 원본을 그대로 저장한다.
    - 지금 일정에 없는 포스터 파일은 지운다 (저장소가 커지지 않게).
    """
    getter = getter or (lambda url: fetch(url, tries=2, timeout=15))
    try:
        from PIL import Image  # 선택 사항
    except ImportError:
        Image = None
    folder.mkdir(parents=True, exist_ok=True)
    have = {p.name for p in folder.iterdir() if p.is_file()}

    def one(it: dict) -> str | None:
        url = it.get("img")
        if not url:
            return None
        base = re.sub(r"[^a-z0-9_-]+", "-", it["id"].lower())
        for ext in (".webp", ".jpg", ".png", ".gif"):
            if base + ext in have:
                return base + ext
        try:
            data = getter(url)
        except Exception as e:
            print(f"  · 포스터 건너뜀 {it['id']}: {e}", file=sys.stderr)
            return None
        ext = image_ext(data)
        if not ext or len(data) > 8_000_000:
            return None
        if Image is not None:
            try:
                im = Image.open(io.BytesIO(data))
                im = im.convert("RGB")
                if im.width > width:
                    im = im.resize((width, max(1, round(im.height * width / im.width))), Image.LANCZOS)
                im.save(folder / (base + ".webp"), "WEBP", quality=72, method=6)
                return base + ".webp"
            except Exception as e:
                print(f"  · 포스터 줄이기 실패, 원본 저장 {it['id']}: {e}", file=sys.stderr)
        (folder / (base + ext)).write_bytes(data)
        return base + ext

    with cf.ThreadPoolExecutor(max_workers=6) as pool:
        names = list(pool.map(one, items))
    got = 0
    for it, name in zip(items, names):
        if name:
            it["poster"] = f"{folder.name}/{name}"
            got += 1
    used = {n for n in names if n}
    for p in folder.iterdir():
        if p.is_file() and p.name not in used and not p.name.startswith("."):
            p.unlink()
    return got


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
    ap.add_argument("--max-kopis", type=int, default=1200, help="KOPIS에서 가져올 최대 공연 수 (기간마다 나눠 씀)")
    ap.add_argument("--kopis-detail", type=int, default=1200, help="요금·줄거리를 가져올 상세 조회 건수")
    ap.add_argument("--max-culture", type=int, default=400)
    ap.add_argument("--max-seats", type=int, default=300, help="이 좌석 수 이하 공연장만 싣는다 (소극장 기준)")
    ap.add_argument("--fixtures", action="store_true", help="저장된 예시 응답으로 실행 (네트워크·키 불필요)")
    ap.add_argument("--posters-dir", default=str(POSTER_DIR), help="공식 포스터를 내려받아 둘 폴더 (페이지 기준 상대 경로로 쓰임)")
    ap.add_argument("--no-posters", action="store_true", help="포스터를 내려받지 않는다")
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
    run("kopis", "KOPIS 공연예술통합전산망", lambda k: collect_kopis(k, start, end, args.max_kopis, args.kopis_detail, args.fixtures, args.max_seats), "KOPIS_API_KEY")
    run("kcisa", "한국문화정보원", lambda k: collect_culture(k, start, end, args.max_culture, args.fixtures), "DATA_GO_KR_KEY")

    items = merge(groups, start, end)
    if not items:
        print("모은 일정이 없어 기존 파일을 그대로 둡니다.", file=sys.stderr)
        return 1

    if not args.no_posters and not args.fixtures:
        got = cache_posters(items, Path(args.posters_dir))
        print(f"- 포스터: {got}건 저장")

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
