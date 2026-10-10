"""verify_hoods.py 테스트 (가짜 응답): python -m unittest discover -s scripts"""
import json
import unittest

import verify_hoods as vh


def fake(places_by_q):
    def fetch(params):
        return {"places": places_by_q(params)}
    return fetch


class VerifyTest(unittest.TestCase):
    def test_center_must_be_in_region(self):
        f = fake(lambda p: [{"address": "경기 용인시", "x": "127.1", "y": "37.3"}, {"address": "서울 강남구", "x": "127.03", "y": "37.5"}])
        self.assertEqual(vh.find_center(f, "서울", "강남역")["lat"], 37.5)
        self.assertIsNone(vh.find_center(fake(lambda p: [{"address": "부산 진구", "x": "1", "y": "2"}]), "서울", "x"))

    def test_server_error_is_retry_not_rejection(self):
        r = vh.verify_one(lambda p: {"error": "가게 목록을 가져오지 못했어요."}, "광주", ["suwan", "수완지구", "광주 수완지구", "x"])
        self.assertFalse(r["ok"])
        self.assertTrue(r.get("retry"))

    def test_judge(self):
        busy = {k: 5 for k in vh.PROBES}
        self.assertTrue(vh.judge(busy)[0])
        quiet = {k: 0 for k in vh.PROBES} | {"카페": 15, "노래방": 3}
        ok, why = vh.judge(quiet)
        self.assertFalse(ok)
        self.assertIn("2종류", why)

    def test_verify_and_merge(self):
        def places(p):
            if "lat" not in p:   # 위치 찾기
                return [{"address": "서울 관악구 신림동", "x": "126.9297", "y": "37.4842"}]
            return [{"address": "서울", "x": "0", "y": "0"}] * (3 if p["q"] != "VR" else 0)
        r = vh.verify_one(fake(places), "서울", ["sillim", "신림", "신림역", "서남부 최대 번화가"])
        self.assertTrue(r["ok"])
        self.assertEqual((r["lat"], r["lng"]), (37.4842, 126.9297))
        local = {"hoods": {"서울": [{"id": "hongdae"}]}}
        self.assertEqual(vh.merge(local, [r, dict(r, id="hongdae"), dict(r, id="x", ok=False)]), 1)
        self.assertEqual([h["id"] for h in local["hoods"]["서울"]], ["hongdae", "sillim"])

    def test_candidates_file(self):
        data = json.loads((vh.ROOT / "data" / "hood_candidates.json").read_text(encoding="utf-8"))
        local = json.loads((vh.ROOT / "data" / "local.json").read_text(encoding="utf-8"))
        # 통과한 후보는 local.json 에도 들어가므로, 후보끼리·local 끼리만 겹치지 않으면 된다
        cand_ids = [c[0] for cs in data["hoods"].values() for c in cs]
        local_ids = [h["id"] for hs in local["hoods"].values() for h in hs]
        self.assertEqual(len(cand_ids), len(set(cand_ids)), "후보 id 중복")
        self.assertEqual(len(local_ids), len(set(local_ids)), "동네 id 중복")
        for region, cs in data["hoods"].items():
            self.assertIn(region, local["hoods"])
            for c in cs:
                self.assertEqual(len(c), 4)
                self.assertRegex(c[0], r"^[a-z0-9]+$")


if __name__ == "__main__":
    unittest.main()
