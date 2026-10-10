import unittest
from controller import Observation, decide, verify
class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.o = Observation('owl:live:123','github-contents-api','sha256:abc',404)
        self.result = dict(operation_id=self.o.operation_id,remote_digest=self.o.observed_digest,remote_commit_count=1,outbox_state='verified',recovery_workers=2,kill_exit=-9,remote_sha='gitblob')
    def test_missing_canary_creates(self):
        self.assertEqual(decide(self.o).action,'CREATE_CANARY')
    def test_existing_canary_reconciles(self):
        self.assertEqual(decide(Observation('op','api','digest',200)).action,'RECONCILE')
    def test_unknown_http_fails_closed(self):
        self.assertEqual(decide(Observation('op','api','digest',403)).action,'BLOCK')
    def test_proof_verified(self):
        self.assertEqual(verify(self.o,decide(self.o),self.result)['outcome'],'VERIFIED')
    def test_false_remote_count_rejected(self):
        self.result['remote_commit_count']=2
        with self.assertRaises(ValueError):verify(self.o,decide(self.o),self.result)
    def test_false_digest_rejected(self):
        self.result['remote_digest']='bad'
        with self.assertRaises(ValueError):verify(self.o,decide(self.o),self.result)
    def test_missing_kill_rejected(self):
        self.result['kill_exit']=0
        with self.assertRaises(ValueError):verify(self.o,decide(self.o),self.result)
    def test_missing_sha_rejected(self):
        self.result['remote_sha']=''
        with self.assertRaises(ValueError):verify(self.o,decide(self.o),self.result)
if __name__=='__main__':unittest.main()
