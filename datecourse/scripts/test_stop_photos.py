"""코스 순서 장소 사진 고르기 테스트 (네트워크 없음)"""
import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import collect_tour as ct
import fetch_stop_photos as sp

T1 = "Type1"


def item(title, x, y, img="http://tong.visitkorea.or.kr/a.jpg", c=T1):
    return {"title": title, "firstimage": img, "cpyrhtDivCd": c, "mapx": str(x), "mapy": str(y)}


class PickTest(unittest.TestCase):
    stop = {"name": "송도 센트럴파크", "lat": 37.3925, "lng": 126.6386}

    def test_near_same_name_type1(self):
        items = [
            item("송도 센트럴파크", 126.6386, 37.3925, c="Type3"),           # 공공누리 1유형 아님
            item("트라이보울", 126.6390, 37.3930),                            # 가깝지만 다른 곳
            item("송도 센트럴파크", 126.70, 37.45),                           # 이름은 같지만 멀다
            item("송도센트럴파크 수상택시", 126.6388, 37.3927, img="http://x/ok.jpg"),
        ]
        self.assertEqual(sp.pick(items, self.stop)["firstimage"], "http://x/ok.jpg")

    def test_none_when_nothing_fits(self):
        self.assertIsNone(sp.pick([item("트라이보울", 126.6390, 37.3930)], self.stop))
        self.assertIsNone(sp.pick([item("아무", 1, 1)], {"name": "A", "lat": 1, "lng": 1}))

    def test_skips_hotels_and_branches_nearby(self):
        stop = {"name": "월미도", "lat": 37.4750, "lng": 126.5970}
        items = [item("베니키아 월미도 더블리스 호텔", 126.5972, 37.4752), item("월미도 문화의거리", 126.5975, 37.4751, img="http://x/ok.jpg")]
        self.assertEqual(sp.pick(items, stop)["firstimage"], "http://x/ok.jpg")
        stop = {"name": "앨리웨이 광교", "lat": 37.29, "lng": 127.05}
        self.assertIsNone(sp.pick([item("티크닉 앨리웨이 광교점", 127.05, 37.29)], stop))

    def test_name_with_parentheses(self):
        stop = {"name": "경의선숲길 (연트럴파크)", "lat": 37.5600, "lng": 126.9250}
        self.assertIsNotNone(sp.pick([item("경의선숲길", 126.9252, 37.5602)], stop))


class MainTest(unittest.TestCase):
    def test_saves_skips_and_retries_later(self):
        courses = {"courses": [{"id": "c1", "stops": [
            {"name": "송도 센트럴파크", "lat": 37.3925, "lng": 126.6386},
            {"name": "없는 곳", "lat": 37.0, "lng": 127.0}]}]}
        calls = []

        class Fake:
            calls_n = 0

            @property
            def calls(self):
                return len(calls)

            def get(self, op, **kw):
                calls.append(kw["keyword"])
                return [item("송도 센트럴파크", 126.6386, 37.3925)] if kw["keyword"] == "송도 센트럴파크" else []

        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "data").mkdir()
            (root / "data" / "courses.json").write_text(json.dumps(courses), encoding="utf-8")
            with mock.patch.object(sp, "ROOT", root), mock.patch.object(sp, "shrink", lambda b, size: b):
                day = dt.date(2026, 10, 1)
                sp.main([], client=Fake(), fetch=lambda u: b"img", today=day)
                meta = json.loads((root / "data" / "stop_photos.json").read_text(encoding="utf-8"))
                self.assertEqual(meta["photos"], {"c1": {"0": {"img": "img/stop/c1-0.webp", "place": "송도 센트럴파크"}}})
                self.assertEqual(meta["misses"], {"c1/1": "2026-10-01"})
                self.assertTrue((root / "img" / "stop" / "c1-0.webp").exists())
                # 다음 주: 받은 곳도, 못 찾은 지 30일 안 된 곳도 다시 묻지 않는다
                sp.main([], client=Fake(), fetch=lambda u: b"img", today=day + dt.timedelta(days=7))
                self.assertEqual(calls, ["송도 센트럴파크", "없는 곳"])
                # 30일 뒤에는 못 찾은 곳만 다시 찾아본다
                sp.main([], client=Fake(), fetch=lambda u: b"img", today=day + dt.timedelta(days=31))
                self.assertEqual(calls, ["송도 센트럴파크", "없는 곳", "없는 곳"])

    def test_stops_at_call_budget(self):
        courses = {"courses": [{"id": "c1", "stops": [{"name": "가나다", "lat": 37.0, "lng": 127.0}]}]}

        class Broke:
            calls = 0

            def get(self, op, **kw):
                raise ct.CallBudget()

        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "data").mkdir()
            (root / "data" / "courses.json").write_text(json.dumps(courses), encoding="utf-8")
            with mock.patch.object(sp, "ROOT", root):
                self.assertEqual(sp.main([], client=Broke()), 0)
                meta = json.loads((root / "data" / "stop_photos.json").read_text(encoding="utf-8"))
                self.assertEqual(meta["misses"], {})


if __name__ == "__main__":
    unittest.main()
