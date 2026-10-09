import unittest
from experiments.blind_review_002 import blind_packet,adjudicate

def o(i,t):
    return {"title":t,"url":"https://github.com/x/y/issues/"+str(i),"labels":"good-first-issue"}
DATA=[o(i,t) for i,t in enumerate(["add missing help","new navaid changes","new waypoint changes",
"add new theme","add new learner mistake","add new example","add new etiquette","add new pair"])]

class TestBlind(unittest.TestCase):
    def test_no_payment_without_buyer(self):
        p=blind_packet(DATA)
        self.assertEqual(adjudicate(p,{})["qualified_buyer_opportunities"],{"A0":0,"A1":0})
    def test_reviewer_must_be_independent(self):
        p=blind_packet(DATA)
        id=p["blind_review"][0]["id"]
        r={id:{"buyer_evidence_url":"https://example.com","buyer_payment_commitment":True,
               "deliverable_feasible":True,"independent_reviewer":False}}
        self.assertEqual(sum(adjudicate(p,r)["qualified_buyer_opportunities"].values()),0)
    def test_origin_hidden_from_reviewer_packet(self):
        p=blind_packet(DATA)
        self.assertTrue(all("arm" not in x for x in p["blind_review"]))
if __name__=="__main__":
    unittest.main()
