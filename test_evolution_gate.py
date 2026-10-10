"""Offline regression tests for OWL evolution screening."""
import unittest
from evolution_gate import evaluate


def fixture():
    return {
        "candidate_id": "candidate-001", "baseline_id": "baseline-001",
        "cases": [{"id": "a", "expected": True}, {"id": "b", "expected": False}, {"id": "c", "expected": True}],
        "baseline_predictions": {"a": False, "b": False, "c": True},
        "candidate_predictions": {"a": True, "b": False, "c": True},
    }


class EvolutionGateTests(unittest.TestCase):
    def test_improvement_is_not_promotion(self):
        result = evaluate(fixture())
        self.assertTrue(result["screen_pass"])
        self.assertFalse(result["promotion_authorized"])
        self.assertEqual(result["status"], "AWAITING_INDEPENDENT_HELDOUT_PROOF")

    def test_regression_is_rejected(self):
        p = fixture()
        p["candidate_predictions"] = {"a": False, "b": True, "c": False}
        r = evaluate(p)
        self.assertFalse(r["screen_pass"])
        self.assertEqual(r["status"], "REJECTED_BY_SCREEN")

    def test_reject_missing_predictions(self):
        p = fixture()
        p["candidate_predictions"].pop("a")
        with self.assertRaises(ValueError):
            evaluate(p)

    def test_reject_duplicate_case_id(self):
        p = fixture()
        p["cases"][1]["id"] = "a"
        with self.assertRaises(ValueError):
            evaluate(p)

    def test_reject_non_boolean_values(self):
        p = fixture()
        p["candidate_predictions"]["a"] = 1
        with self.assertRaises(ValueError):
            evaluate(p)

    def test_deterministic_evidence_hash(self):
        self.assertEqual(evaluate(fixture()), evaluate(fixture()))


if __name__ == "__main__":
    unittest.main()
