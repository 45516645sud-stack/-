"""코스 장소 점검 테스트 (네트워크 없음)"""
import unittest

import check_courses as cc


class CheckTest(unittest.TestCase):
    def test_check(self):
        courses = [{"id": "c1", "stops": [
            {"name": "성심당 본점", "kind": "food", "lat": 36.3, "lng": 127.4},
            {"name": "없어진 카페", "kind": "cafe", "lat": 36.3, "lng": 127.4},
            {"name": "한밭수목원", "kind": "walk", "lat": 36.3, "lng": 127.4},   # 산책길은 점검 안 함
            {"name": "서버 오류 가게", "kind": "shop", "lat": 36.3, "lng": 127.4},
        ]}]

        def fetch(p):
            if p["q"] == "서버 오류 가게":
                return {"error": "x"}
            return {"places": [{"name": "성심당 본점"}] if p["q"].startswith("성심당") else [{"name": "다른 가게"}]}

        missing, failed = cc.check(fetch, courses)
        self.assertEqual(missing, {"c1": ["없어진 카페"]})
        self.assertEqual(failed, 1)


if __name__ == "__main__":
    unittest.main()
