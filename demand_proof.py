"""Demand proof gate: posted reward != verified budget != payment."""
import json
import sqlite3

STAGES=("PROBLEM_OBSERVED","BUYER_IDENTIFIED","DEMAND_CONFIRMED",
        "PAYMENT_COMMITTED","REVENUE_SETTLED")

def classify(e):
    if not e.get("problem_url"):
        return {"stage":"UNVERIFIED","reason":"no_primary_problem"}
    stage=STAGES[0]
    if not (e.get("buyer_identity") and e.get("buyer_authority_evidence")):
        return {"stage":stage,"reason":"buyer_authority_unverified"}
    stage=STAGES[1]
    if not e.get("buyer_need_confirmation"):
        return {"stage":stage,"reason":"need_unconfirmed"}
    stage=STAGES[2]
    if not (e.get("payment_commitment_url") and e.get("payment_terms") and
            e.get("funding_or_escrow_evidence")):
        return {"stage":stage,"reason":"payment_not_committed"}
    stage=STAGES[3]
    if not (e.get("settlement_transaction") and e.get("settlement_independent_verification")
            and isinstance(e.get("net_received_usd"),(int,float))
            and e["net_received_usd"]>=0):
        return {"stage":stage,"reason":"settlement_unverified"}
    return {"stage":STAGES[4],"reason":"verified_settlement",
            "net_received_usd":e["net_received_usd"]}

def save(db, identifier, evidence):
    db.execute("""CREATE TABLE IF NOT EXISTS demand_proofs
        (id TEXT PRIMARY KEY, evidence_json TEXT NOT NULL, verdict_json TEXT NOT NULL)""")
    verdict=classify(evidence)
    db.execute("INSERT OR IGNORE INTO demand_proofs VALUES (?,?,?)",
        (identifier,json.dumps(evidence,sort_keys=True),json.dumps(verdict,sort_keys=True)))
    return verdict
