import unittest
from runtime_reconcile import reconcile
COMMIT="a"*40
DEPLOY="deploy-1"
ATT={"verified":True,"identity":{"deployment_id":DEPLOY,"commit_sha":COMMIT},"checks":{"arithmetic":True,"sqlite_readonly":True}}
RAIL={"id":DEPLOY,"status":"SUCCESS","meta":{"commitHash":COMMIT}}
class ReconcileTests(unittest.TestCase):
 def test_verified_candidate(self):
  self.assertEqual(reconcile(ATT,RAIL,COMMIT)["verdict"],"RECOVERED_CANDIDATE")
 def test_wrong_deployment_fails(self):
  self.assertEqual(reconcile(ATT,{**RAIL,"id":"other"},COMMIT)["verdict"],"UNVERIFIED")
 def test_wrong_commit_requires_rollback(self):
  self.assertEqual(reconcile(ATT,RAIL,"b"*40)["verdict"],"ROLLBACK_REQUIRED")
 def test_missing_attestation_fails(self):
  self.assertEqual(reconcile({},RAIL,COMMIT)["verdict"],"UNVERIFIED")
if __name__=="__main__":unittest.main()
