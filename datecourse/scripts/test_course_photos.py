"""코스 사진 고르기 테스트 (네트워크 없음)"""
import unittest

import fetch_course_photos as fp


class PickTest(unittest.TestCase):
    stop = {"name": "서울숲", "lat": 37.5444, "lng": 127.0374}

    def test_pick_near_type1(self):
        items = [
            {"title": "서울숲", "firstimage": "http://tong.visitkorea.or.kr/a.jpg", "cpyrhtDivCd": "Type3", "mapx": "127.037", "mapy": "37.544"},
            {"title": "부산 서울숲", "firstimage": "http://tong.visitkorea.or.kr/b.jpg", "cpyrhtDivCd": "Type1", "mapx": "129.0", "mapy": "35.1"},
            {"title": "서울숲", "firstimage": "", "cpyrhtDivCd": "Type1", "mapx": "127.037", "mapy": "37.544"},
            {"title": "서울숲공원", "firstimage": "http://tong.visitkorea.or.kr/c.jpg", "cpyrhtDivCd": "Type1", "mapx": "127.038", "mapy": "37.545"},
        ]
        self.assertEqual(fp.pick(items, self.stop)["firstimage"], "http://tong.visitkorea.or.kr/c.jpg")

    def test_find_photo_tries_next_stop(self):
        course = {"stops": [{"name": "없는 곳 (2층)", "lat": 37.5, "lng": 127.0}, self.stop]}
        calls = []

        class Fake:
            def get(self, op, **kw):
                calls.append(kw["keyword"])
                if kw["keyword"] == "서울숲":
                    return [{"title": "서울숲", "firstimage": "http://x/a.jpg", "cpyrhtDivCd": "Type1", "mapx": "127.037", "mapy": "37.544"}]
                return []

        p = fp.find_photo(Fake(), course)
        self.assertEqual(calls, ["없는 곳", "서울숲"])
        self.assertEqual(p, {"url": "https://x/a.jpg", "place": "서울숲", "stop": "서울숲"})


if __name__ == "__main__":
    unittest.main()
