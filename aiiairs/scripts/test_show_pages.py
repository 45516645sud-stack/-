"""공연별 페이지 만들기 점검: python -m unittest aiiairs/scripts/test_show_pages.py"""
import json
import re
import sys
import tempfile
import unittest
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_show_pages as b  # noqa: E402

BASE = "https://example.github.io/-/"
ITEMS = [
    {"id": "kopis-pf1", "t": "행오버 <대학로>", "cat": "theater", "region": "서울", "venue": "정극장", "s": "2026-01-01", "e": "2026-12-31",
     "fee": 50000, "note": "전석 50,000원", "img": "https://www.kopis.or.kr/a.gif", "art": "img/a.webp", "url": "https://ticket.example/1",
     "info": "https://www.kopis.or.kr/x", "time": "토요일(15:00)", "runtime": "90분", "age": "만 16세 이상", "cast": "가, 나", "addr": "서울 종로구 대학로 1"},
    {"id": "kopis-pf2", "t": "무료 음악회", "cat": "classic", "region": "서울", "venue": "홀", "s": "2026-10-30", "e": "2026-10-30", "fee": 0,
     "img": "", "art": "img/b.webp", "url": "", "info": "", "addr": ""},
    {"id": "Manual/한글", "t": "끝난 공연", "cat": "music", "region": "부산", "venue": "클럽", "s": "2026-01-01", "e": "2026-02-01", "fee": None,
     "img": "", "art": "img/c.webp", "url": "", "info": "", "addr": ""},
]


class ShowPages(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.site = Path(self.tmp.name)
        (self.site / "data").mkdir()
        (self.site / "data" / "fairs.json").write_text(json.dumps({"items": ITEMS}, ensure_ascii=False), encoding="utf-8")
        self.pages, self.listed = b.build(self.site, BASE, date(2026, 10, 28))

    def tearDown(self):
        self.tmp.cleanup()

    def test_counts_and_sitemap(self):
        self.assertEqual((self.pages, self.listed), (3, 2))
        sm = (self.site / "sitemap.xml").read_text(encoding="utf-8")
        self.assertIn(f"{BASE}show/kopis-pf1.html", sm)
        self.assertNotIn("manual-", sm)  # 끝난 공연은 지도에서 뺀다
        self.assertTrue((self.site / "show" / f"{b.slug('Manual/한글')}.html").exists())  # 끝난 공연도 페이지는 남긴다

    def test_page_content(self):
        s = (self.site / "show" / "kopis-pf1.html").read_text(encoding="utf-8")
        self.assertIn("<title>행오버 &lt;대학로&gt; | 서울 연극 일정·가격 · 소극콕</title>", s)
        self.assertIn('rel="canonical" href="https://example.github.io/-/show/kopis-pf1.html"', s)
        self.assertNotIn("<대학로>", s)  # 이름은 글자로 바꿔 넣는다
        ld = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', s, re.S).group(1))
        self.assertEqual(ld["@type"], "TheaterEvent")
        self.assertEqual(ld["offers"]["price"], 50000)
        self.assertEqual(ld["location"]["address"]["addressCountry"], "KR")
        self.assertIn("예매하러 가기", s)
        self.assertIn("../?id=kopis-pf1", s)
        HTMLParser().feed(s)

    def test_free_and_missing(self):
        s = (self.site / "show" / "kopis-pf2.html").read_text(encoding="utf-8")
        self.assertIn('<li class="free">무료</li>', s)
        self.assertNotIn("예매하러 가기", s)  # 예매 주소가 없으면 버튼도 없다
        self.assertIn("D-2", s)
        ld = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', s, re.S).group(1))
        self.assertTrue(ld["isAccessibleForFree"])

    def test_slug(self):
        self.assertEqual(b.slug("kopis-PF1"), "kopis-pf1")
        self.assertRegex(b.slug("Manual/한글 공연"), r"^[a-z0-9_-]+$")


if __name__ == "__main__":
    unittest.main()
