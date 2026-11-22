import json
from pathlib import Path
import unittest

from pipeline import prepare, export


def fixture():
    return json.loads(
        Path(__file__).with_name("example.json").read_text(encoding="utf-8")
    )


class PipelineTests(unittest.TestCase):
    def test_shortest_proof_and_impossible_conjunction(self):
        d = fixture()
        r = prepare(d)
        p = r["candidates"][0]
        self.assertEqual(
            [s["action"] for s in p["steps"]],
            ["Collect badge", "Restore power", "Open gate"],
        )
        bad = next(x for x in r["records"] if x["id"] == "goal:Open sealed gate")
        self.assertFalse(bad["reachable"])
        self.assertTrue(bad["missing"])

    def test_zero_step_goal(self):
        r = prepare(fixture())
        self.assertEqual(r["candidates"][-1]["steps"], [])

    def test_cycle_terminates(self):
        d = {
            "flags": ["lamp"],
            "actions": [
                {"id": "On", "set": ["lamp"]},
                {"id": "Off", "clear": ["lamp"]},
            ],
            "goals": [{"id": "Lit", "requires": ["lamp"]}],
        }
        r = prepare(d)
        self.assertEqual(r["metrics"]["Reachable states"], 2)
        out = export(d, r, [r["candidates"][0]])
        self.assertEqual(
            json.loads(out["playthrough-proofs.json"])["goals"][0]["final"], ["lamp"]
        )
        self.assertIn(" -> ", out["playthroughs.dot"])

    def test_unknown_flags_and_empty_selection(self):
        d = fixture()
        r = prepare(d)
        self.assertEqual(
            json.loads(export(d, r, [])["playthrough-proofs.json"])["goals"], []
        )
        d["goals"][0]["requires"] = ["missing"]
        with self.assertRaises(ValueError):
            prepare(d)


if __name__ == "__main__":
    unittest.main()
