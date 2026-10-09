"""Continuous OWL runner with persistent, idempotent startup canary."""
import json
import os
import signal
import time
from worker import connect, enqueue, run_once

running = True
def stop(*_):
    global running
    running = False
signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGINT, stop)

interval = max(1, int(os.environ.get("OWL_POLL_SECONDS", "10")))
canary_id = os.environ.get("OWL_CANARY_ID", "")
db = connect()
try:
    if canary_id:
        enqueue(db, canary_id, "healthcheck", {"purpose": "persistence-proof"})
        row = db.execute("SELECT id,status,result FROM jobs WHERE id=?", (canary_id,)).fetchone()
        print(json.dumps({"event": "canary_observed_at_start", "id": row[0], "status": row[1], "result": row[2]}), flush=True)
finally:
    db.close()
while running:
    db = connect()
    try:
        result = run_once(db)
        if result:
            print(json.dumps({"event": "job_completed", **result}), flush=True)
    finally:
        db.close()
    time.sleep(interval)
