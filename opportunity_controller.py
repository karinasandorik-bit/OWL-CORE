"""ATHENA/OWL: bounded opportunity decision engine, no financial actuators."""
import hashlib
import json
import sqlite3
from datetime import datetime, timezone

REQUIRED = ("id", "source", "source_observed_at", "kind", "gross_usd", "cost_usd",
            "loss_if_failed_usd", "probability_success", "hours", "evidence")
KINDS = {"research", "software", "design", "content", "bug_bounty", "market_shadow", "other"}

def canonical(x):
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def assess(candidate, min_usd_per_hour=5):
    missing = [k for k in REQUIRED if k not in candidate]
    if missing:
        return {"decision": "REJECT", "reason": "missing_fields", "fields": missing}
    if candidate["kind"] not in KINDS or not candidate["id"] or not candidate["source"] or not candidate["evidence"]:
        return {"decision": "REJECT", "reason": "invalid_provenance"}
    try:
        p = float(candidate["probability_success"])
        gross = float(candidate["gross_usd"])
        cost = float(candidate["cost_usd"])
        loss = float(candidate["loss_if_failed_usd"])
        hours = float(candidate["hours"])
    except (ValueError, TypeError):
        return {"decision": "REJECT", "reason": "invalid_numbers"}
    if not (0 <= p <= 1 and gross >= 0 and cost >= 0 and loss >= 0 and hours > 0):
        return {"decision": "REJECT", "reason": "out_of_bounds"}
    if any(v != v or abs(v) == float("inf") for v in (p, gross, cost, loss, hours)):
        return {"decision": "REJECT", "reason": "non_finite"}
    expected = p * gross - cost - (1 - p) * loss
    hourly = expected / hours
    decision = "REVIEW" if expected > 0 and hourly >= min_usd_per_hour else "REJECT"
    return {"decision": decision, "expected_net_usd": round(expected, 4),
            "expected_usd_per_hour": round(hourly, 4),
            "reason": "human_authorization_required" if decision == "REVIEW" else "insufficient_expected_value",
            "execution_authorized": False}

def record(db, candidate):
    db.execute("""CREATE TABLE IF NOT EXISTS opportunities (
        id TEXT PRIMARY KEY, observed_at TEXT NOT NULL, candidate_json TEXT NOT NULL,
        candidate_sha256 TEXT NOT NULL, decision_json TEXT NOT NULL,
        realized_net_usd REAL, settlement_evidence TEXT
    )""")
    result = assess(candidate)
    payload = canonical(candidate)
    digest = hashlib.sha256(payload.encode()).hexdigest()
    db.execute("INSERT OR IGNORE INTO opportunities VALUES (?,?,?,?,?,?,?)",
        (str(candidate.get("id", digest)), datetime.now(timezone.utc).isoformat(),
         payload, digest, canonical(result), None, None))
    return result

def report(db):
    rows = db.execute("SELECT realized_net_usd,settlement_evidence FROM opportunities").fetchall()
    verified = [r[0] for r in rows if r[0] is not None and r[1]]
    return {"settled_count": len(verified), "verified_realized_net_usd": round(sum(verified), 2),
            "unverified_count": len(rows) - len(verified)}
