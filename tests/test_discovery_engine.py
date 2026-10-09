import unittest
from discovery_engine import discover

def obs(i,source,key="repeated-build-failure"):
    return {"id":i,"source":source,"observed_at":"2026-10-09T13:00:00Z",
            "problem_key":key,"description":"Repeated failure","evidence_url":"https://example.org/"+i}

class DiscoveryTests(unittest.TestCase):
    def test_independent_sources_create_hypothesis(self):
        result=discover([obs("1","a"),obs("2","b")])
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]["status"],"HYPOTHESIS")
        self.assertFalse(result[0]["execution_authorized"])
        self.assertIsNone(result[0]["expected_revenue_usd"])
    def test_one_source_is_not_independent(self):
        self.assertEqual(discover([obs("1","a"),obs("2","a")]),[])
    def test_duplicates_do_not_manufacture_support(self):
        self.assertEqual(discover([obs("1","a"),obs("1","b")]),[])
    def test_distinct_problems_do_not_merge(self):
        self.assertEqual(discover([obs("1","a","x"),obs("2","b","y")]),[])
    def test_missing_provenance_is_rejected(self):
        self.assertEqual(discover([obs("1","a"),{**obs("2","b"),"evidence_url":""}]),[])

if __name__=="__main__":
    unittest.main()
