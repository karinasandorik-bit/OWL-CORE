import os, tempfile, unittest
from kernel import Kernel
class Trial(unittest.TestCase):
    def setUp(self):
        f=tempfile.NamedTemporaryFile(delete=False);self.path=f.name;f.close()
        self.k=Kernel(self.path)
        self.event={'kind':'github_issue','issue':53,'source':'https://github.com/Augora-Labs/augora/issues/53'}
    def tearDown(self):
        self.k.db.close();os.unlink(self.path)
    def test_event_to_verified_outcome(self):
        self.k.ingest('github:augora:53',self.event)
        self.assertEqual(self.k.step('github:augora:53'),'verified')
        self.assertTrue(self.k.verify('github:augora:53'))
    def test_crash_recovery_and_deduplication(self):
        self.k.ingest('github:augora:53',self.event)
        with self.assertRaises(RuntimeError):self.k.step('github:augora:53',True)
        self.k.db.close();self.k=Kernel(self.path)
        self.k.ingest('github:augora:53',self.event)
        self.assertEqual(self.k.step('github:augora:53'),'verified')
        self.assertEqual(self.k.step('github:augora:53'),'verified')
        self.assertEqual(self.k.db.execute('select count(*) from jobs').fetchone()[0],1)
        self.assertTrue(self.k.verify('github:augora:53'))
    def test_tamper_detection(self):
        self.k.ingest('github:augora:53',self.event)
        self.k.step('github:augora:53')
        self.k.db.execute("update jobs set payload='{}' where event_id='github:augora:53'");self.k.db.commit()
        self.assertFalse(self.k.verify('github:augora:53'))
        self.assertEqual(self.k.step('github:augora:53'),'tainted')
    def test_outcome_tamper_detection(self):
        self.k.ingest('github:augora:53',self.event);self.k.step('github:augora:53')
        self.k.db.execute("update jobs set outcome='{}' where event_id='github:augora:53'");self.k.db.commit()
        self.assertFalse(self.k.verify('github:augora:53'))
if __name__=='__main__':unittest.main()
