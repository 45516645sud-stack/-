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


class LocalDataTest(unittest.TestCase):
    """'우리 동네' 데이터: 17개 시·도 모두 동네가 있고, 코스 틀이 있는 놀거리만 쓴다."""

    def test_local(self):
        data = json.loads((ct.ROOT / "data" / "local.json").read_text(encoding="utf-8"))
        acts = {a["id"] for a in data["activities"]}
        self.assertEqual(set(data["hoods"]), set(ct.AREAS.values()))
        ids = [h["id"] for hs in data["hoods"].values() for h in hs]
        self.assertEqual(len(ids), len(set(ids)))
        for hs in data["hoods"].values():
            self.assertTrue(hs)
            for h in hs:
                self.assertTrue(33 < h["lat"] < 39 and 124 < h["lng"] < 132, h["id"])
                self.assertRegex(h["id"], r"^[a-z0-9]+$")
        for t in data["templates"]:
            self.assertIn("{hood}", t["title"])
            self.assertTrue(set(t["stops"]) <= acts, t["id"])
            self.assertIn(t["budget"], (0, 1, 2, 3))

    def test_activity_kinds(self):
        """놀거리마다 가게 종류를 가려낼 규칙이 있고, 서로 헷갈리기 쉬운 가게를 제대로 나눈다."""
        data = json.loads((ct.ROOT / "data" / "local.json").read_text(encoding="utf-8"))
        acts = {a["id"]: a for a in data["activities"]}

        def fits(a, cat, name):  # index.html 의 fitsAct 와 같은 규칙
            text = f"{cat} {name}".lower()
            has = lambda w: all(part in text for part in w.lower().split("+"))
            return any(map(has, a["match"])) and not any(map(has, a["not"]))

        for a in acts.values():
            self.assertTrue(a["match"], a["id"])
        board = ("음식점 > 카페 > 테마카페 > 보드카페", "레드버튼")
        dessert = ("음식점 > 카페 > 디저트카페", "설빙")
        pub = ("음식점 > 술집 > 호프,요리주점", "구미펍코로나")
        coin = ("가정,생활 > 여가시설 > 노래방", "세븐스타코인노래연습장")
        sing = ("가정,생활 > 여가시설 > 노래방", "럭셔리 노래방")
        self.assertTrue(fits(acts["boardgame"], *board))
        self.assertFalse(fits(acts["boardgame"], *pub))
        self.assertFalse(fits(acts["boardgame"], *dessert))
        self.assertTrue(fits(acts["cafe"], *dessert))
        self.assertFalse(fits(acts["cafe"], *board))
        self.assertTrue(fits(acts["coinsing"], *coin))
        self.assertFalse(fits(acts["coinsing"], *sing))
        self.assertTrue(fits(acts["karaoke"], *sing))
        self.assertFalse(fits(acts["karaoke"], *coin))
        self.assertFalse(fits(acts["meal"], *pub))
        # 실제 카카오 결과에서 찾은 경우들 (scripts/check_kinds.py)
        self.assertTrue(fits(acts["boardgame"], "가정,생활 > 여가시설 > 보드카페", "명탐정보드게임카페 광주점"))  # '주점' 오해 X
        self.assertTrue(fits(acts["boardgame"], "가정,생활 > 여가시설 > 만화방 > 만화카페 > 벌툰", "벌툰 인더스트리얼 안동남문로점"))
        self.assertTrue(fits(acts["manga"], "가정,생활 > 여가시설 > 만화방 > 만화카페 > 놀숲", "놀숲 안동점"))
        self.assertTrue(fits(acts["cafe"], "음식점 > 카페 > 테마카페 > 디저트카페 > 설빙", "설빙 안동옥동점"))
        self.assertFalse(fits(acts["cafe"], "가정,생활 > 여가시설 > 만화방 > 만화카페 > 벌툰", "벌툰"))
        self.assertTrue(fits(acts["coinsing"], "가정,생활 > 여가시설 > 노래방", "동띵동COIN노래연습장"))
        self.assertFalse(fits(acts["karaoke"], "가정,생활 > 유흥시설 > 유흥주점", "세연가요방"))
        self.assertTrue(fits(acts["arcade"], "가정,생활 > 여가시설 > 게임방,PC방", "궁전경품오락실"))
        self.assertTrue(fits(acts["class"], "문화,예술 > 미술,공예", "글라앙글라"))
        self.assertFalse(fits(acts["pc"], "가정,생활 > 여가시설 > 게임방,PC방", "VR스카이가상현실체험"))
        self.assertTrue(fits(acts["bowling"], "스포츠,레저 > 볼링 > 볼링장", "K1볼링장 전주점"))


if __name__ == "__main__":
    unittest.main()
