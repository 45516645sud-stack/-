"""collect_tour.py 테스트: python -m unittest discover -s scripts"""
import json
import unittest
import urllib.parse
from pathlib import Path

import collect_tour as ct

FIX = json.loads((Path(__file__).parent / "fixtures" / "tourapi.json").read_text(encoding="utf-8"))


def wrap(items):
    body = {"items": {"item": items}} if items not in (None, []) else {"items": ""}
    return json.dumps({"response": {"header": {"resultCode": "0000"}, "body": body}})


def fake_fetch(url):
    parsed = urllib.parse.urlparse(url)
    op = parsed.path.rsplit("/", 1)[-1]
    q = dict(urllib.parse.parse_qsl(parsed.query))
    assert q["serviceKey"] == "k" and q["_type"] == "json"
    key = q.get("areaCode") if op == "areaBasedList2" else q["contentId"]
    return wrap(FIX[op].get(key, []))


class CollectTest(unittest.TestCase):
    def run_collect(self, previous=(), max_calls=100):
        client = ct.Client("k", max_calls, fetch=fake_fetch, pause=0)
        return client, ct.collect(client, 5, list(previous), log=lambda *_: None)

    def test_builds_courses_in_app_schema(self):
        _, courses = self.run_collect()
        self.assertEqual([c["id"] for c in courses], ["tour-9001", "tour-9002"])
        seoul = courses[0]
        self.assertEqual(seoul["region"], "서울")
        self.assertEqual(seoul["area"], "종로구")
        self.assertEqual(seoul["with"], ["friends", "date"])
        self.assertIn("전통", seoul["tags"])
        self.assertIn("시장", seoul["tags"])
        self.assertEqual(seoul["hours"], 4)
        self.assertEqual(seoul["summary"], "서울 도심을 걷는 코스.")
        # subnum 순서대로, HTML 은 벗겨서
        self.assertEqual([s["name"] for s in seoul["stops"]], ["가상 시장", "가상 궁궐"])
        self.assertEqual(seoul["stops"][1]["tip"], "조선의 & 궁궐이다. 한옥이 아름답다.")
        self.assertEqual((seoul["stops"][0]["lat"], seoul["stops"][0]["lng"]), (37.57, 126.99))

    def test_missing_coords_and_overnight(self):
        _, courses = self.run_collect()
        jeju = courses[1]
        self.assertIsNone(jeju["hours"])
        self.assertNotIn("lat", jeju["stops"][1])  # 좌표 0 은 없는 것으로 본다
        self.assertIn("바다", jeju["tags"])

    def test_unchanged_course_is_not_refetched(self):
        _, first = self.run_collect()
        client, second = self.run_collect(previous=first)
        self.assertEqual(client.calls, len(ct.AREAS))  # 목록 호출만
        self.assertEqual(first, second)

    def test_budget_keeps_previous(self):
        old = {"id": "tour-1", "region": "부산", "stops": [{"name": "a"}, {"name": "b"}]}
        client, courses = self.run_collect(previous=[old], max_calls=1)
        self.assertEqual(client.calls, 1)
        self.assertIn("tour-1", [c["id"] for c in courses])

    def test_error_response(self):
        bad = json.dumps({"response": {"header": {"resultCode": "30", "resultMsg": "SERVICE KEY ERROR"}}})
        with self.assertRaises(RuntimeError):
            ct.parse_items(bad, "x")
        with self.assertRaises(RuntimeError):
            ct.parse_items("<OpenAPI_ServiceResponse><returnAuthMsg>SERVICE_KEY_IS_NOT_REGISTERED_ERROR</returnAuthMsg>", "x")

    def test_parse_hours(self):
        self.assertEqual(ct.parse_hours("당일"), 8)
        self.assertEqual(ct.parse_hours("약 2.5시간"), 2.5)
        self.assertIsNone(ct.parse_hours("2박3일"))
        self.assertIsNone(ct.parse_hours(""))


class SeedDataTest(unittest.TestCase):
    """직접 고른 기본 코스가 앱이 기대하는 모양인지 확인한다."""

    def test_seed(self):
        data = json.loads((ct.ROOT / "data" / "courses.json").read_text(encoding="utf-8"))
        courses = data["courses"]
        self.assertEqual({c["region"] for c in courses}, set(ct.AREAS.values()))  # 17개 시·도 모두
        self.assertEqual(len({c["id"] for c in courses}), len(courses))
        for c in courses:
            self.assertIn(c["budget"], (0, 1, 2, 3), c["id"])
            self.assertTrue(set(c["with"]) <= {"date", "friends", "family", "solo", "student"}, c["id"])
            self.assertTrue(c["details"], c["id"])
            for d in c["details"]:
                self.assertIn(d["kind"], ("photo", "time", "move", "tip", "snack"), c["id"])
            for s in c["stops"]:
                self.assertTrue(33 < s["lat"] < 39 and 124 < s["lng"] < 132, (c["id"], s["name"]))


if __name__ == "__main__":
    unittest.main()
