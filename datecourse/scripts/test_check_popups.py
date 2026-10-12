import unittest
from datetime import date

from check_popups import kind_of, merge, name_of, period, place_of, popup_id, young_ok


class PopupParse(unittest.TestCase):
    def test_period(self):
        p = date(2026, 10, 5)
        self.assertEqual(period("기간: 10.3(금) ~ 10.19(일)", p), (date(2026, 10, 3), date(2026, 10, 19)))
        self.assertEqual(period("2026.10.03 - 2026.10.19 운영", p), (date(2026, 10, 3), date(2026, 10, 19)))
        self.assertEqual(period("10월 3일~19일까지", p), (date(2026, 10, 3), date(2026, 10, 19)))
        self.assertEqual(period("12/20~1/5 겨울 팝업", date(2026, 12, 1)), (date(2026, 12, 20), date(2027, 1, 5)))
        self.assertIsNone(period("오픈 시간 10:30 ~ 20:00", p))
        self.assertIsNone(period("1.1~12.31 상시", p))   # 너무 긴 기간은 팝업 아님

    def test_end_only(self):
        p = date(2026, 10, 5)
        self.assertEqual(period("블랙업 성수 팝업은 10/18 까지만 진행", p), (None, date(2026, 10, 18)))
        self.assertEqual(period("10월 31일까지 올리브영N 성수에서", p), (None, date(2026, 10, 31)))
        self.assertIsNone(period("9월 1일까지 했던 팝업", p))   # 이미 끝남

    def test_name(self):
        self.assertEqual(name_of("[성수] 망그러진 곰 팝업스토어 후기"), "망그러진 곰")
        self.assertEqual(name_of("더현대 서울 산리오 팝업 오픈런"), "산리오")
        self.assertEqual(name_of("🎀 2026 산리오 팝업 | 10.10~10.26"), "산리오")
        self.assertEqual(name_of("이번 주 가볼 만한 성수 팝업 정리"), "")
        self.assertEqual(name_of("10월 2주차 예약없이 가는 팝업"), "")
        self.assertEqual(name_of("마르디 메크르디 '정한의 프라이빗 아틀리에' 팝업"), "정한의 프라이빗 아틀리에")

    def test_name_not_place(self):
        self.assertEqual(name_of("용산 아이파크몰 해리포터 팝업스토어"), "해리포터")
        self.assertEqual(name_of("롯데 팝업 다녀왔어요"), "")
        self.assertEqual(name_of("신세계 팝업"), "")
        self.assertEqual(name_of("점서 국내 첫 팝업"), "")
        self.assertEqual(name_of("피카츄 얼굴을 어떻게 먹어? 팝업"), "")
        self.assertEqual(popup_id("육구 방앗간"), popup_id("육구방앗간"))

    def test_kind(self):
        self.assertEqual(kind_of("주술회전", "AK플라자 홍대 굿즈"), "anime")
        self.assertEqual(kind_of("노브랜드 버거 × 애니모", "홍대점 팝업"), "character")   # '애니모'는 애니가 아님
        self.assertEqual(kind_of("NCT 위시 아이 스파이", ""), "idol")
        self.assertEqual(kind_of("킥둥쓰", "킥플립 킥둥쓰 성수 팝업 솔직히"), "idol")
        self.assertEqual(kind_of("호아킨 바스코", "진정한 인생 치즈타르트 커피"), "food")
        self.assertEqual(kind_of("메디힐", "토너패드 화장품"), "beauty")
        self.assertEqual(kind_of("에얼스", "사전예약"), "etc")
        self.assertEqual(kind_of("로키드 AI 글래스", "exclusive 체험"), "tech")   # 'ive'가 아이브로 잡히지 않음

    def test_young(self):
        self.assertTrue(young_ok("주술회전", "굿즈 오픈런"))
        self.assertFalse(young_ok("잉글레시나", "유모차 팝업"))
        self.assertFalse(young_ok("창업 박람회", ""))
        self.assertTrue(young_ok("베이비몬스터 팝업", ""))

    def test_place(self):
        self.assertEqual(place_of("📍 더현대 서울 B2 아이코닉존")[0], "더현대 서울")
        self.assertEqual(place_of("무신사 메가스토어 성수 1F 📅 9.30")[0], "무신사 메가스토어 성수")
        self.assertEqual(place_of("서울특별시 성동구 연무장길 99 1층")[0], "성수 연무장길")
        self.assertEqual(place_of("주소: 서울 용산구 이태원로 255 기간")[0], "서울 용산구 이태원로 255")
        self.assertEqual(place_of("성수에서 열려요")[0], "서울 성동구 성수동")

    def test_merge(self):
        f = lambda n: {"name": n}  # noqa: E731
        groups = merge([f("육구방앗간"), f("속초 육구방앗간"), f("롯데 육구방앗간"), f("룩백")])
        self.assertEqual(sorted(len(g) for g in groups), [1, 3])


if __name__ == "__main__":
    unittest.main()
