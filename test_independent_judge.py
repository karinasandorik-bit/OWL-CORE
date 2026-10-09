"""Offline tests for worker-to-independent-judge boundary (no secrets/network)."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import worker
from independent_judge import grade, sha


class JudgeTests(unittest.TestCase):
    def fixture(self):
        return {"dataset_id": "hidden-v1", "cases": [
            {"id": "a", "expected": True}, {"id": "b", "expected": False},
            {"id": "c", "expected": True}]}

    def request(self):
        return {"dataset_id": "hidden-v1", "candidate_id": "c1", "baseline_id": "b1",
                "candidate_predictions": {"a": True, "b": False, "c": True},
                "baseline_predictions": {"a": False, "b": False, "c": True}}

    def test_judge_keeps_promotion_false(self):
        result = grade(self.request(), self.fixture())
        self.assertTrue(result["screen_pass"])
        self.assertFalse(result["promotion_authorized"])

    def test_judge_rejects_bad_labels_and_coverage(self):
        r = self.request()
        r["candidate_predictions"].pop("a")
        with self.assertRaises(ValueError):
            grade(r, self.fixture())

    def test_dataset_is_bound(self):
        r = self.request()
        r["dataset_id"] = "other"
        with self.assertRaises(ValueError):
            grade(r, self.fixture())

    def test_evidence_hash_is_stable_and_tamper_sensitive(self):
        a, b = self.request(), self.request()
        self.assertEqual(sha(a), sha(b))
        b["candidate_predictions"]["a"] = False
        self.assertNotEqual(sha(a), sha(b))

    def test_real_worker_outbox_once_and_no_promotion(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(worker, "DB", str(Path(d) / "test.sqlite3")):
                db = worker.connect()
                worker.enqueue(db, "case-001", "evaluate_candidate", self.request())
                worker.enqueue(db, "case-001", "evaluate_candidate", self.request())
                completed = worker.run_once(db)
                self.assertEqual(completed["result"]["status"], "PENDING_INDEPENDENT_JUDGE")
                self.assertFalse(completed["result"]["accepted"])
                self.assertIsNone(worker.run_once(db))
                rows = db.execute("SELECT request_json FROM evaluation_outbox").fetchall()
                self.assertEqual(len(rows), 1)
                self.assertEqual(json.loads(rows[0][0]), self.request())
                db.close()

    def test_worker_rejects_unbounded_payload(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(worker, "DB", str(Path(d) / "test.sqlite3")):
                db = worker.connect()
                bad = self.request()
                bad["unexpected"] = "shell"
                worker.enqueue(db, "bad", "evaluate_candidate", bad)
                with self.assertRaises(ValueError):
                    worker.run_once(db)
                self.assertEqual(db.execute("SELECT COUNT(*) FROM evaluation_outbox").fetchone()[0], 0)
                db.close()


if __name__ == "__main__":
    unittest.main()
