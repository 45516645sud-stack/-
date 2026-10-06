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

    def test_venue(self):
        self.assertEqual(collect.clean_venue("예시소극장 (예시소극장)"), "예시소극장")
        self.assertEqual(collect.clean_venue("단막극장(구.대학로단막극장) (단막극장(구.대학로단막극장))"), "단막극장(구.대학로단막극장)")
        self.assertEqual(collect.clean_venue("롯데마트 [월드컵] (행복을 주는 가족극장)"), "롯데마트 [월드컵] (행복을 주는 가족극장)")
        self.assertEqual(collect.clean_venue("대학로 스카이씨어터"), "대학로 스카이씨어터")
        self.assertEqual(collect.clean_venue("K-POP STAGE (구. 윤형빈소극장 [홍대] ) (K-POP STAGE (구. 윤형빈소극장 [홍대] ) )"),
                         "K-POP STAGE (구. 윤형빈소극장 [홍대] )")
        self.assertEqual(collect.clean_venue("더퍼포머씨어터 [화성] (더퍼포머씨어터)"), "더퍼포머씨어터 [화성]")

    def test_small_stage(self):
        self.assertTrue(collect.is_small("예시소극장", 120, 300))
        self.assertFalse(collect.is_small("예시아트센터 (대극장)", 1200, 300))
        self.assertFalse(collect.is_small("예시아레나 (대공연장)", None, 300))
        self.assertTrue(collect.is_small("재즈클럽 그루브", None, 300))
        # 좌석 수를 모를 때 이름에 '라이브'가 있어도 아레나·경기장이면 큰 공연장
        self.assertFalse(collect.is_small("올림픽공원 (티켓링크 라이브 아레나 (핸드볼경기장))", None, 300))
        self.assertFalse(collect.is_small("엑스코(exco) (제1전시장(서관))", None, 300))
        self.assertFalse(collect.is_small("창원광장 (특설무대)", None, 300))
        self.assertFalse(collect.is_small("유니플렉스 (2관(중극장))", None, 300))
        self.assertFalse(collect.is_small("부산콘서트홀", None, 300))
        # 큰 공연장 안의 소극장·소공연장은 작은 무대
        self.assertTrue(collect.is_small("대구콘서트하우스 (챔버홀 (소공연장) )", None, 300))
        self.assertTrue(collect.is_small("대전평송청소년문화센터 (어울림홀(소극장))", None, 300))
        self.assertTrue(collect.is_small("KT&G 상상마당 라이브홀 [마포]", None, 300))
        self.assertEqual(collect.seats_for("예시아트센터 (소극장)", [("대극장", 1200), ("소극장", 180)]), 180)
        self.assertIsNone(collect.seats_for("예시아트센터 (야외)", [("대극장", 1200), ("소극장", 180)]))
        self.assertEqual(collect.seats_for("예시홀", [("예시홀", 90)]), 90)

    def test_cache_posters(self):
        gif = b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
        pages = {"https://a.kr/1.gif": gif, "https://a.kr/2.gif": b"<html>error</html>"}
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "posters"
            folder.mkdir()
            (folder / "old-show.webp").write_bytes(b"x")  # 지금 일정에 없는 파일은 지워진다
            items = [{"id": "kopis-pf1", "img": "https://a.kr/1.gif"},
                     {"id": "kopis-pf2", "img": "https://a.kr/2.gif"},
                     {"id": "manual-3"}]
            got = collect.cache_posters(items, folder, getter=lambda u: pages[u])
            self.assertEqual(got, 1)
            self.assertTrue(items[0]["poster"].startswith("posters/kopis-pf1."))
            self.assertTrue((folder / items[0]["poster"].split("/", 1)[1]).exists())
            self.assertNotIn("poster", items[1])  # 그림이 아닌 응답은 저장하지 않는다
            self.assertFalse((folder / "old-show.webp").exists())
            # 두 번째에는 다시 받지 않는다
            again = [{"id": "kopis-pf1", "img": "https://a.kr/1.gif"}]
            collect.cache_posters(again, folder, getter=lambda u: (_ for _ in ()).throw(AssertionError("다시 받음")))
            self.assertEqual(again[0]["poster"], items[0]["poster"])

    def test_genre(self):
        # KOPIS 가 실제로 보내는 이름 '무용(서양/한국무용)' 도 무용·마임으로
        self.assertEqual(collect.genre_info("무용(서양/한국무용)")[0], "dance")
        self.assertEqual(collect.genre_info("서커스/마술")[0], "dance")
        self.assertEqual(collect.genre_info("서양음악(클래식)")[0], "classic")
        self.assertEqual(collect.genre_info("한국음악(국악)")[0], "classic")
        self.assertEqual(collect.genre_info("대중음악")[0], "music")
        self.assertEqual(collect.genre_info("뮤지컬")[0], "musical")
        self.assertEqual(collect.genre_info("복합")[0], "theater")
        self.assertEqual(collect.genre_info("처음 보는 장르")[0], "theater")

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
            self.assertEqual(items["kopis-pf000001"]["venue"], "예시소극장")
            self.assertEqual(items["kcisa-900003"]["cat"], "kids")
            # 전시(사진전)는 소공연 사이트에 싣지 않는다
            self.assertNotIn("kcisa-900001", items)
            # 좌석 수를 알면 표시하고, 큰 공연장(대공연장)은 뺀다
            self.assertEqual(items["kopis-pf000001"]["seats"], 120)
            # 모든 KOPIS 공연에 공식 공연 페이지 링크가 붙는다 (예매처가 없어도)
            self.assertTrue(items["kopis-pf000002"]["info"].endswith("mt20Id=PF000002"))
            self.assertNotIn("url", items["kopis-pf000002"])
            self.assertEqual(items["kopis-pf000001"]["url"], "https://ticket.example.com/PF000001")
            self.assertNotIn("kopis-pf000003", items)
            self.assertEqual(items["kopis-pf000001"]["cat"], "theater")
            self.assertEqual(items["kopis-pf000002"]["cat"], "music")
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
