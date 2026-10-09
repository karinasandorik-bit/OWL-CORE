import unittest
from experiments.discovery_ab_001 import evaluate, score

OBS = [{"title":t,"url":"https://github.com/example/repo/issues/"+str(i),"labels":"bug"}
       for i,t in enumerate(["scan drops value","scan drops array","rtl language layout",
       "rtl language component","incorrect runtime version","incorrect model version",
       "broken screw edges","broken geometry edges"])]

class DiscoveryABTests(unittest.TestCase):
    def test_budget_and_no_fake_success(self):
        x=evaluate(OBS)
        self.assertEqual(len(x["A0"]),8)
        self.assertLessEqual(len(x["A1"]),8)
        self.assertEqual(x["verdict"],"PENDING_BLINDED_EXTERNAL_VALIDATION")
        self.assertEqual(score(x["A0"]),0)
        self.assertEqual(score(x["A1"]),0)
    def test_duplicate_rejected(self):
        with self.assertRaises(ValueError):
            evaluate(OBS[:7]+[OBS[0]])
    def test_budget_change_rejected(self):
        with self.assertRaises(ValueError):
            evaluate(OBS,budget=7)
    def test_only_verified_counts(self):
        self.assertEqual(score([{"buyer_verified":True,"deliverable_feasible":False},
                                {"buyer_verified":True,"deliverable_feasible":True}]),1)

if __name__=="__main__":
    unittest.main()
