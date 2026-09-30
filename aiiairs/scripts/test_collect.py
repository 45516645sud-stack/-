"""collect.py 테스트. 실행: python3 -m unittest aiiairs/scripts/test_collect.py"""
import datetime as dt
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import collect  # noqa: E402

HERE = Path(__file__).resolve().parent


class ParseTest(unittest.TestCase):
    def test_fee(self):
        self.assertEqual(collect.parse_fee("전석무료"), 0)
        self.assertEqual(collect.parse_fee("무료 (사전예약)"), 0)
        self.assertEqual(collect.parse_fee("R석 50,000원, S석 30,000원"), 30000)
        self.assertEqual(collect.parse_fee("전석 20000원"), 20000)
        self.assertIsNone(collect.parse_fee(""))
        self.assertIsNone(collect.parse_fee("현장 문의"))
        # '무료'가 들어 있어도 금액이 같이 있으면 유료로 본다
        self.assertEqual(collect.parse_fee("일반 15,000원 / 어린이 무료"), 15000)

    def test_day(self):
        self.assertEqual(collect.parse_day("2026.10.02"), dt.date(2026, 10, 2))
        self.assertEqual(collect.parse_day("20261002"), dt.date(2026, 10, 2))
        self.assertEqual(collect.parse_day("2026-10-02"), dt.date(2026, 10, 2))
        self.assertIsNone(collect.parse_day("10월 2일"))

    def test_region(self):
        self.assertEqual(collect.region_of("서울특별시"), "서울")
        self.assertEqual(collect.region_of("전라남도 여수시"), "전남")
        self.assertEqual(collect.region_of("", "경상북도 경주시 보문로"), "경북")
        self.assertEqual(collect.region_of("충청북도"), "충북")
        self.assertEqual(collect.region_of("전남광주통합특별시"), "광주·전남")
        self.assertEqual(collect.region_of("전라남도 여수시"), "전남")
        self.assertEqual(collect.region_of("광주광역시"), "광주")
        self.assertEqual(collect.region_of("알 수 없음"), "기타")

    def test_https(self):
        self.assertEqual(collect.https("http://a.kr/x.gif"), "https://a.kr/x.gif")
        self.assertIsNone(collect.https("javascript:alert(1)"))


class FixtureRunTest(unittest.TestCase):
    def test_fixture_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "fairs.json"
            code = collect.main(["--fixtures", "--manual", str(HERE / "fixtures" / "manual_example.csv"), "--out", str(out)])
            self.assertEqual(code, 0)
            data = json.loads(out.read_text(encoding="utf-8"))
            items = {i["id"]: i for i in data["items"]}
            # 두 출처에 같은 연극이 있으면 한 번만 남는다
            self.assertEqual(sum(1 for i in data["items"] if "빈 방" in i["t"]), 1)
            # 상세가 없는 공연에 다른 공연의 상세가 섞이지 않는다
            self.assertEqual(items["kopis-pf000002"]["venue"], "예시재즈홀")
            self.assertEqual(items["kopis-pf000002"]["region"], "부산")
            self.assertEqual(items["kopis-pf000001"]["fee"], 20000)
            self.assertEqual(items["kcisa-900003"]["cat"], "family")
            for it in data["items"]:
                self.assertRegex(it["s"], r"^\d{4}-\d{2}-\d{2}$")
                self.assertIn("fee", it)

    def test_unchanged_items_keep_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "fairs.json"
            args = ["--fixtures", "--manual", str(HERE / "fixtures" / "manual_example.csv"), "--out", str(out)]
            self.assertEqual(collect.main(args), 0)
            first = out.read_text(encoding="utf-8")
            self.assertEqual(collect.main(args), 0)
            self.assertEqual(out.read_text(encoding="utf-8"), first)

    def test_no_sources_keeps_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "fairs.json"
            out.write_text("KEEP", encoding="utf-8")
            empty = Path(tmp) / "manual.csv"
            empty.write_text(",".join(collect.MANUAL_HEADER) + "\n", encoding="utf-8")
            code = collect.main(["--manual", str(empty), "--out", str(out)])
            self.assertEqual(code, 1)
            self.assertEqual(out.read_text(encoding="utf-8"), "KEEP")


if __name__ == "__main__":
    unittest.main()
