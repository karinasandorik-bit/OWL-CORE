import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from runner import baseline,candidate,evaluate,HOLDOUT,digest_cases
class TestRunner(unittest.TestCase):
 def test_expected_improvement(self):
  self.assertEqual(evaluate(baseline,HOLDOUT),{"passed":3,"total":6})
  self.assertEqual(evaluate(candidate,HOLDOUT),{"passed":6,"total":6})
 def test_stable_digest(self):
  self.assertEqual(len(digest_cases(HOLDOUT)),64)
 def test_no_arbitrary_execution(self):
  self.assertFalse(candidate("python -c 'import os'"))
if __name__=="__main__":unittest.main()
