"""Generate falsifiable task hypotheses from independent observations.
No orders, outreach, payments, or unbounded external actions.
"""
import hashlib
import json
from collections import defaultdict

def discover(observations, min_independent_sources=2):
    """Each observation: {id, source, observed_at, problem_key, description, evidence_url}.
    The problem_key is a pre-existing normalized label: this baseline does not invent categories.
    """
    groups = defaultdict(list)
    seen = set()
    for o in observations:
        if not isinstance(o, dict) or not all(o.get(k) for k in
            ("id", "source", "observed_at", "problem_key", "description", "evidence_url")):
            continue
        if o["id"] in seen:
            continue
        seen.add(o["id"])
        groups[str(o["problem_key"])].append(o)
    hypotheses = []
    for key, items in sorted(groups.items()):
        sources = {x["source"] for x in items}
        if len(sources) < min_independent_sources:
            continue
        fingerprint = hashlib.sha256(key.encode()).hexdigest()[:16]
        hypotheses.append({
            "id": "DISCOVERY-" + fingerprint,
            "problem_key": key,
            "supporting_observations": sorted(x["id"] for x in items),
            "independent_source_count": len(sources),
            "hypothesis": "Repeated observed problem may justify a reusable solution",
            "cheap_test": "Verify independent demand and a reachable buyer before building",
            "falsification": "No independent buyer or evidence of willingness to pay",
            "status": "HYPOTHESIS",
            "execution_authorized": False,
            "expected_revenue_usd": None,
        })
    return hypotheses

def discover_jsonl(lines):
    return discover([json.loads(line) for line in lines if line.strip()])
