"""Independent OWL judge. Run outside worker trust domain.

Private fixture JSON: {"dataset_id":"...", "cases":[{"id":"...","expected":true},...]}
Fixture MUST be stored outside repository and worker filesystem.
Requires psycopg 3, PostgreSQL schema from sql/evolution_ledger.sql.
"""
import argparse
import hashlib
import json
import os
import sqlite3
from pathlib import Path

def packed(v):
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def sha(v):
    return hashlib.sha256(packed(v).encode()).hexdigest()

def grade(request, fixture):
    if request["dataset_id"] != fixture["dataset_id"]:
        raise ValueError("dataset mismatch")
    cases = fixture["cases"]
    if not isinstance(cases, list) or not 2 <= len(cases) <= 10000:
        raise ValueError("invalid heldout fixture")
    truth = {}
    for case in cases:
        if not isinstance(case, dict) or not isinstance(case.get("id"), str) or type(case.get("expected")) is not bool or case["id"] in truth:
            raise ValueError("invalid heldout case")
        truth[case["id"]] = case["expected"]
    scores = {}
    for kind in ("candidate", "baseline"):
        pred = request[kind + "_predictions"]
        if set(pred) != set(truth) or not all(type(v) is bool for v in pred.values()):
            raise ValueError("prediction coverage/type mismatch")
        scores[kind] = sum(pred[k] == truth[k] for k in truth) / len(truth)
    delta = round(scores["candidate"] - scores["baseline"], 12)
    return {"dataset_sha256": sha(fixture), "candidate_accuracy": scores["candidate"],
            "baseline_accuracy": scores["baseline"], "delta_accuracy": delta,
            "screen_pass": delta > 0, "promotion_authorized": False,
            "status": "AWAITING_AUTHORITY_REVIEW" if delta > 0 else "REJECTED_BY_JUDGE"}

def run(db_path, fixture_path, pg_dsn):
    import psycopg
    fixture = json.loads(Path(fixture_path).read_text(encoding="utf-8"))
    uri = Path(db_path).resolve().as_uri() + "?mode=ro"
    with sqlite3.connect(uri, uri=True) as source, psycopg.connect(pg_dsn) as pg:
        # The judge's PostgreSQL credential must only have SELECT and INSERT privileges.
        for request_id, body in source.execute("SELECT id,request_json FROM evaluation_outbox ORDER BY created_at"):
            req = json.loads(body)
            request_hash = sha(req)
            with pg.transaction():
                existing = pg.execute("SELECT request_hash FROM owl_evaluation_events WHERE request_id=%s",
                                      (request_id,)).fetchone()
                if existing:
                    if existing[0] != request_hash:
                        raise ValueError("duplicate request ID with changed payload")
                    continue
                try:
                    result = grade(req, fixture)
                except (KeyError, ValueError, TypeError) as exc:
                    result = {"status": "REJECTED_INVALID_REQUEST", "promotion_authorized": False,
                              "reason": type(exc).__name__}
                pg.execute("""INSERT INTO owl_evaluation_events
                    (request_id, request_hash, dataset_id, candidate_id, baseline_id, verdict)
                    VALUES (%s,%s,%s,%s,%s,%s::jsonb)""",
                    (request_id, request_hash, str(req.get("dataset_id", "")),
                     str(req.get("candidate_id", "")), str(req.get("baseline_id", "")), packed(result)))
                print(packed({"request_id": request_id, "verdict": result["status"]}), flush=True)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--worker-db", required=True)
    p.add_argument("--heldout", required=True)
    args = p.parse_args()
    run(args.worker_db, args.heldout, os.environ["OWL_JUDGE_DATABASE_URL"])
