import sqlite3
import unittest
from opportunity_controller import assess, record, report

C = {"id":"trial-1","source":"https://example.org/contract","source_observed_at":"2026-10-09T13:00:00Z","kind":"research","gross_usd":100,"cost_usd":5,"loss_if_failed_usd":10,"probability_success":0.8,"hours":3,"evidence":"external listing to verify"}

class OpportunityTests(unittest.TestCase):
    def test_review_is_not_execution(self):
        result = assess(C)
        self.assertEqual(result["decision"], "REVIEW")
        self.assertFalse(result["execution_authorized"])
    def test_missing_evidence_denied(self):
        self.assertEqual(assess({**C,"evidence":""})["decision"],"REJECT")
    def test_negative_value_denied(self):
        self.assertEqual(assess({**C,"gross_usd":1})["decision"],"REJECT")
    def test_nan_denied(self):
        self.assertEqual(assess({**C,"gross_usd":float("nan")})["decision"],"REJECT")
    def test_durable_idempotence_and_no_fake_revenue(self):
        db=sqlite3.connect(":memory:")
        record(db,C)
        record(db,C)
        self.assertEqual(db.execute("SELECT COUNT(*) FROM opportunities").fetchone()[0],1)
        self.assertEqual(report(db)["verified_realized_net_usd"],0)
        self.assertEqual(report(db)["unverified_count"],1)

if __name__=="__main__":
    unittest.main()
