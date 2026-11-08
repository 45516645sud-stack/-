import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import find_videos as fv  # noqa: E402


def item(vid, title, ch="극단"):
    return {"id": {"videoId": vid}, "snippet": {"title": title, "channelTitle": ch}}


class FindVideos(unittest.TestCase):
    def test_core_title(self):
        self.assertEqual(fv.core_title("난세: 정도전과 이방원의 이야기 [대학로]"), "난세: 정도전과 이방원의 이야기")
        self.assertEqual(fv.core_title("제5회 서울시니어연극제: 어린노인"), "서울시니어연극제: 어린노인")

    def test_match(self):
        self.assertGreater(fv.match_score("빨간 모자 [대구]", "뮤지컬 <빨간모자> 티저"), 0)
        # 하이라이트·티저 같은 말이 없으면(리뷰·커튼콜 팬 영상) 쓰지 않는다
        self.assertEqual(fv.match_score("빨간 모자 [대구]", "빨간모자 리뷰"), 0)
        self.assertEqual(fv.match_score("남주를 부탁해", "251024 연극 남주를 부탁해 커튼콜"), 0)
        # 짧은 이름은 연극·뮤지컬 같은 말이 있어야 한다
        self.assertEqual(fv.match_score("아이브", "아이브 콘서트 하이라이트"), fv.match_score("아이브", "아이브 콘서트 하이라이트"))
        self.assertEqual(fv.match_score("세리", "세리 하이라이트 브이로그"), 0)
        # 같은 이름의 영화 예고편은 빼기
        self.assertEqual(fv.match_score("빨간 모자 [대구]", "한글자막 | 「빨간 모자, 여행을 떠나 시체를 만났습니다」 티저 예고편"), 0)
        self.assertEqual(fv.match_score("빨간 모자 [대구]", "오늘의 날씨"), 0)
        # 축제 이름만 같고 공연 이름이 다르면 쓰지 않는다
        self.assertGreater(fv.match_score("제5회 서울시니어연극제: 어린노인", "연극 어린노인 하이라이트"), 0)
        self.assertGreater(fv.match_score("옹알스", "(Wow) 옹알스 공연 하이라이트"), 0)

    def test_pick(self):
        got = fv.pick("빨간 모자 [대구]", [item("aaaaaaaaaaa", "다른 영상"), item("bbbbbbbbbbb", "빨간 모자 공식 트레일러"), item("ddddddddddd", "빨간 모자 리뷰"),
                                          item("bad", "빨간 모자 티저")])
        self.assertEqual(got["vid"], "bbbbbbbbbbb")
        self.assertIsNone(fv.pick("빨간 모자", [item("ccccccccccc", "파란 바다")]))

    def test_candidates(self):
        today = dt.date(2026, 11, 8)
        items = [
            {"id": "a", "t": "가", "s": "2026-11-01", "e": "2026-11-09"},
            {"id": "b", "t": "나", "s": "2026-10-01", "e": "2026-11-01"},   # 끝남
            {"id": "c", "t": "다", "s": "2027-03-01", "e": "2027-03-05"},   # 너무 먼 공연
            {"id": "d", "t": "라", "s": "2026-11-20", "e": "2026-11-30"},
            {"id": "e", "t": "마", "s": "2026-11-01", "e": "2026-12-01"},
        ]
        known = {"e": {"vid": None, "at": "2026-11-01"}}   # 일주일 전에 찾아봄 → 건너뜀
        self.assertEqual([f["id"] for f in fv.candidates(items, known, today, 10)], ["a", "d"])


if __name__ == "__main__":
    unittest.main()
