"""Blind review for heldout opportunities: independent buyer proof required."""
import hashlib
import json
from experiments.discovery_ab_001 import evaluate

def blind_packet(observations):
    arms=evaluate(observations)
    entries=[]
    key={}
    for arm in ("A0","A1"):
        for p in arms[arm]:
            identifier=hashlib.sha256((arm+":"+p["review_id"]).encode()).hexdigest()[:16]
            entries.append({"id":identifier,"task":p["task"],"evidence":p["evidence"],
                "buyer_evidence_url":None,"buyer_payment_commitment":None,
                "deliverable_feasible":None,"verified_paid_usd":None})
            key[identifier]=arm
    entries.sort(key=lambda x:x["id"])
    return {"blind_review":entries,"sealed_arm_key":key,
            "verdict":"UNSCORED_PENDING_INDEPENDENT_BUYER_EVIDENCE"}

def adjudicate(packet, reviews):
    key=packet["sealed_arm_key"]
    score={"A0":0,"A1":0}
    for x in packet["blind_review"]:
        r=reviews.get(x["id"],{})
        # Require a reachable, independently corroborated buyer commitment.
        if (r.get("buyer_evidence_url") and r.get("buyer_payment_commitment") is True
            and r.get("deliverable_feasible") is True and r.get("independent_reviewer") is True):
            score[key[x["id"]]]+=1
    return {"qualified_buyer_opportunities":score,
            "verdict":"A1_WIN" if score["A1"]>score["A0"] else
              ("A0_WIN" if score["A0"]>score["A1"] else "TIE_OR_UNVERIFIED")}
