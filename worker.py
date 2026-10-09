"""Bounded OWL job runner: no network, payments, signing or shell execution."""
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone

DB = os.environ.get("OWL_DB", "owl_jobs.sqlite3")
def connect():
    db = sqlite3.connect(DB, timeout=30, isolation_level=None)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("""CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY, kind TEXT NOT NULL, payload TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'queued', result TEXT, updated_at TEXT NOT NULL
    )""")
    return db
def now():
    return datetime.now(timezone.utc).isoformat()
def enqueue(db, job_id, kind, payload):
    if kind not in ("healthcheck", "evaluate_candidate"):
        raise ValueError("capability denied")
    db.execute("INSERT OR IGNORE INTO jobs VALUES (?,?,?,?,?,?)",
               (job_id, kind, json.dumps(payload), "queued", None, now()))
def run_once(db):
    db.execute("BEGIN IMMEDIATE")
    try:
        row = db.execute("SELECT id,kind,payload FROM jobs WHERE status='queued' ORDER BY updated_at LIMIT 1").fetchone()
        if row is None:
            db.execute("COMMIT")
            return None
        job_id, kind, payload = row
        data = json.loads(payload)
        if kind == "healthcheck":
            result = {"ok": True, "mode": "bounded"}
        elif kind == "evaluate_candidate":
            result = {"accepted": False, "reason": "requires external independent proof", "candidate": str(data.get("candidate", ""))[:120]}
        else:
            raise ValueError("capability denied")
        db.execute("UPDATE jobs SET status='done',result=?,updated_at=? WHERE id=?",
                   (json.dumps(result), now(), job_id))
        db.execute("COMMIT")
        return {"id": job_id, "result": result}
    except BaseException:
        db.execute("ROLLBACK")
        raise
if __name__ == "__main__":
    db = connect()
    if len(sys.argv) > 1 and sys.argv[1] == "enqueue":
        enqueue(db, sys.argv[2], sys.argv[3], json.loads(sys.argv[4]))
    else:
        print(json.dumps(run_once(db)))
