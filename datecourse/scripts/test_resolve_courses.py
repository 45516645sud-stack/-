"""새 여행 코스 후보와 위치 찾기 테스트 (네트워크 없음)"""
import json
import unittest

import resolve_courses as rc

TAGS = {"놀이공원", "야경", "바다", "카페", "맛집", "산책", "전통", "실내", "비오는날", "액티비티", "노을", "자연", "시장"}
KINDS = {"walk", "cafe", "food", "view", "culture", "activity", "shop", "beach", "night", "stay"}
WITH = {"date", "friends", "family", "solo", "student"}
DETAILS = {"photo", "time", "move", "tip", "snack"}


def fake(places):
    def fetch(params):
        return {"places": places.get(params["q"], [])}
    return fetch


class CandidatesTest(unittest.TestCase):
    def test_candidates_shape(self):
        data = json.loads((rc.ROOT / "data" / "course_candidates.json").read_text(encoding="utf-8"))
        have = {c["id"] for c in json.loads((rc.ROOT / "data" / "courses.json").read_text(encoding="utf-8"))["courses"]}
        ids = [c["id"] for c in data["courses"]]
        self.assertEqual(len(ids), len(set(ids)))
        for c in data["courses"]:
            self.assertRegex(c["id"], r"^[a-z0-9-]+$")
            self.assertTrue(set(c["tags"]) <= TAGS, c["id"])
            self.assertTrue(set(c["with"]) <= WITH, c["id"])
            self.assertIn(c["budget"], (0, 1, 2, 3))
            self.assertTrue(c["stops"], c["id"])
            for s in c["stops"]:
                self.assertIn(s["kind"], KINDS, (c["id"], s["name"]))
                self.assertTrue(s["q"])
            for d in c["details"]:
                self.assertIn(d["kind"], DETAILS)
            if c["id"] in have:  # 이미 들어간 코스는 같은 내용이어야
                continue


class ResolveTest(unittest.TestCase):
    cand = {"id": "x", "region": "경북", "title": "t", "stops": [
        {"name": "회룡포", "q": "회룡포", "kind": "walk"}, {"name": "삼강주막", "q": "삼강주막", "kind": "food"}]}

    def test_ok(self):
        f = fake({"회룡포": [{"x": "128.35", "y": "36.64", "address": "경북 예천군 용궁면"}],
                  "삼강주막": [{"x": "128.30", "y": "36.57", "address": "경북 예천군 풍양면"}]})
        course, why = rc.resolve(f, self.cand)
        self.assertEqual(why, "통과")
        self.assertEqual(course["stops"][0], {"name": "회룡포", "kind": "walk", "lat": 36.64, "lng": 128.35})

    def test_wrong_region_or_far(self):
        f = fake({"회룡포": [{"x": "128.35", "y": "36.64", "address": "경북 예천군"}],
                  "삼강주막": [{"x": "126.9", "y": "37.5", "address": "서울 종로구"}]})
        course, why = rc.resolve(f, self.cand)
        self.assertIsNone(course)
        self.assertIn("못 찾음", why)
        f = fake({"회룡포": [{"x": "128.35", "y": "36.64", "address": "경북 예천군"}],
                  "삼강주막": [{"x": "129.4", "y": "35.9", "address": "경북 경주시"}]})
        self.assertIn("떨어져", rc.resolve(f, self.cand)[1])


if __name__ == "__main__":
    unittest.main()
