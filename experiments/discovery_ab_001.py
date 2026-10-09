"""OWL DISCOVERY AB-001: deterministic, preregistered, budget-matched baseline.
This harness evaluates candidate novelty; buyer validation is external and pending.
"""
import hashlib
import json
import re
from collections import Counter

FIXED_CATEGORIES = ("bug", "feature", "research", "design")
BUDGET = 8

def tokenize(text):
    return set(re.findall(r"[a-z]{4,}", text.lower())) - {
        "with","from","that","this","when","into","have","does","after",
        "issue","request","update","error","using","only","more","same"}

def evaluate(observations, budget=BUDGET):
    if budget != BUDGET:
        raise ValueError("preregistered budget cannot change")
    if len(observations) < budget:
        raise ValueError("insufficient observations")
    sample = observations[:budget]
    if len({x["url"] for x in sample}) != budget:
        raise ValueError("duplicate evidence")
    a0 = []
    for o in sample:
        category = next((c for c in FIXED_CATEGORIES if c in (o["title"]+" "+o.get("labels","")).lower()), "bug")
        a0.append({"category":category,"evidence":[o["url"]],"task":"Resolve reported "+category,"status":"HYPOTHESIS"})
    a1 = []
    for i,left in enumerate(sample):
        for right in sample[i+1:]:
            overlap = sorted(tokenize(left["title"]) & tokenize(right["title"]))
            if overlap:
                a1.append({"category":"emergent:"+",".join(overlap[:3]),
                    "evidence":sorted([left["url"],right["url"]]),
                    "task":"Test reusable solution for shared problem: "+", ".join(overlap[:3]),
                    "status":"HYPOTHESIS"})
    a1.sort(key=lambda x:(x["category"],x["evidence"]))
    # Equal proposal budget; ranking and threshold fixed before human validation.
    a1 = a1[:budget]
    for items in (a0,a1):
        for item in items:
            item["review_id"] = hashlib.sha256(json.dumps(item,sort_keys=True).encode()).hexdigest()[:12]
            item["buyer_verified"] = None
            item["deliverable_feasible"] = None
            item["net_revenue_verified_usd"] = None
    return {"protocol":"DISCOVERY-AB-001","budget_observations_per_arm":budget,
            "fixed_categories":list(FIXED_CATEGORIES),"A0":a0,"A1":a1,
            "verdict":"PENDING_BLINDED_EXTERNAL_VALIDATION"}

def score(reviewed):
    # Do not reward proposal count, hallucinated revenue, or unreviewed ideas.
    return sum(1 for x in reviewed if x.get("buyer_verified") is True
               and x.get("deliverable_feasible") is True)
