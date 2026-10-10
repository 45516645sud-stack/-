"""'이번 주말' 데이터 만들기 테스트 (네트워크 없음)"""
import datetime as dt
import json
import unittest

import build_events as be

TODAY = dt.date(2026, 10, 11)
END = TODAY + dt.timedelta(days=45)


class ShowsTest(unittest.TestCase):
    def test_from_fairs(self):
        items = [
            {"id": "kopis-1", "t": "연극 A", "cat": "theater", "region": "광주·전남", "venue": "극장", "s": "2026-10-01", "e": "2026-10-20", "fee": 30000, "poster": "posters/a.webp"},
            {"id": "kopis-2", "t": "끝난 공연", "cat": "music", "region": "서울", "s": "2026-09-01", "e": "2026-10-01"},
            {"id": "kopis-3", "t": "먼 공연", "cat": "music", "region": "서울", "s": "2027-01-01", "e": "2027-01-02"},
            {"id": "kopis-4", "t": "오픈런", "cat": "musical", "region": "서울", "s": "2014-01-01", "e": "2026-12-31", "openrun": True, "img": "http://www.kopis.or.kr/p.gif"},
            {"id": "kopis-5", "t": "지역 모름", "cat": "music", "region": "기타", "s": "2026-10-10", "e": "2026-10-12"},
        ]
        out = be.from_fairs(items, TODAY, END, "../")
        self.assertEqual([x["title"] for x in out], ["연극 A", "오픈런"])
        a, b = out
        self.assertEqual(a["regions"], ["광주", "전남"])
        self.assertEqual(a["cat"], "연극")
        self.assertEqual(a["poster"], "../posters/a.webp")
        self.assertEqual(a["price"], 30000)
        self.assertTrue(b["long"])
        self.assertEqual(b["poster"], "https://www.kopis.or.kr/p.gif")


class FestivalTest(unittest.TestCase):
    def test_addr_region(self):
        self.assertEqual(be.addr_region("경상북도 안동시 육사로"), ["경북"])
        self.assertEqual(be.addr_region("전남광주통합특별시 북구 무등로"), ["광주"])
        self.assertEqual(be.addr_region("전남광주통합특별시 순천시 x"), ["전남"])
        self.assertEqual(be.addr_region(""), [])

    def test_from_festivals(self):
        page = {"response": {"header": {"resultCode": "0000"}, "body": {"items": {"item": [
            {"contentid": "1", "title": "안동 탈춤축제", "addr1": "경상북도 안동시 탈춤공원길", "eventstartdate": "20261001", "eventenddate": "20261012", "firstimage": "http://tong.visitkorea.or.kr/a.jpg", "mapx": "128.7", "mapy": "36.5"},
            {"contentid": "2", "title": "끝난 축제", "addr1": "서울특별시 종로구", "eventstartdate": "20260901", "eventenddate": "20260910"},
        ]}}}}
        client = be.ct.Client("k", 6, fetch=lambda url: json.dumps(page), pause=0)
        out = be.from_festivals(client, TODAY, END)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["regions"], ["경북"])
        self.assertEqual(out[0]["cat"], "축제")
        self.assertEqual(out[0]["poster"], "")  # http 그림은 안 씀
        self.assertTrue(out[0]["link"].startswith("https://korean.visitkorea.or.kr/"))


if __name__ == "__main__":
    unittest.main()
