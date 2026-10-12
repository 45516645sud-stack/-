import unittest
from datetime import date

from check_popups import name_of, period, place_of


class PopupParse(unittest.TestCase):
    def test_period(self):
        p = date(2026, 10, 5)
        self.assertEqual(period("기간: 10.3(금) ~ 10.19(일)", p), (date(2026, 10, 3), date(2026, 10, 19)))
        self.assertEqual(period("2026.10.03 - 2026.10.19 운영", p), (date(2026, 10, 3), date(2026, 10, 19)))
        self.assertEqual(period("10월 3일~19일까지", p), (date(2026, 10, 3), date(2026, 10, 19)))
        self.assertEqual(period("12/20~1/5 겨울 팝업", date(2026, 12, 1)), (date(2026, 12, 20), date(2027, 1, 5)))
        self.assertIsNone(period("오픈 시간 10:30 ~ 20:00", p))
        self.assertIsNone(period("1.1~12.31 상시", p))   # 너무 긴 기간은 팝업 아님

    def test_name_place(self):
        self.assertEqual(name_of("[성수] 망그러진 곰 팝업스토어 후기"), "망그러진 곰")
        self.assertEqual(name_of("더현대 서울 산리오 팝업 오픈런"), "산리오")
        self.assertEqual(place_of("📍 서울 성동구 연무장길 45 · 기간"), "서울 성동구 연무장길 45")
        self.assertEqual(place_of("롯데월드몰 1층에서 열려요"), "롯데월드몰")


if __name__ == "__main__":
    unittest.main()
