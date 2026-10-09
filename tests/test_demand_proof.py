import sqlite3
import unittest
from demand_proof import classify,save

BASE={"problem_url":"https://github.com/example/repo/issues/1"}
class DemandProofTests(unittest.TestCase):
    def test_public_bounty_not_payment(self):
        self.assertEqual(classify({**BASE,"advertised_reward_usd":100})["stage"],"PROBLEM_OBSERVED")
    def test_buyer_requires_authority(self):
        self.assertEqual(classify({**BASE,"buyer_identity":"org"})["stage"],"PROBLEM_OBSERVED")
    def test_commitment_requires_funding(self):
        x={**BASE,"buyer_identity":"org","buyer_authority_evidence":"primary-source",
           "buyer_need_confirmation":"yes","payment_commitment_url":"https://example.com",
           "payment_terms":"100 USD"}
        self.assertEqual(classify(x)["stage"],"DEMAND_CONFIRMED")
    def test_settlement_requires_independent_proof(self):
        x={**BASE,"buyer_identity":"org","buyer_authority_evidence":"primary-source",
           "buyer_need_confirmation":"yes","payment_commitment_url":"https://example.com",
           "payment_terms":"100 USD","funding_or_escrow_evidence":"escrow-ref",
           "settlement_transaction":"txid","net_received_usd":100}
        self.assertEqual(classify(x)["stage"],"PAYMENT_COMMITTED")
    def test_idempotent_ledger(self):
        db=sqlite3.connect(":memory:")
        save(db,"one",BASE);save(db,"one",BASE)
        self.assertEqual(db.execute("SELECT COUNT(*) FROM demand_proofs").fetchone()[0],1)
if __name__=="__main__":
    unittest.main()
