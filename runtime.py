"""Bounded OWL worker with one-shot, durable SIGKILL recovery trial."""
import json
import os
import signal
import subprocess
import sys
import time
from worker import connect, enqueue, run_once
from runtime_attestation import attest

running = True
def stop(*_):
    global running
    running = False
signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGINT, stop)

interval = max(1, int(os.environ.get("OWL_POLL_SECONDS", "10")))
canary_id = os.environ.get("OWL_CANARY_ID", "")
trial_id = os.environ.get("OWL_RECOVERY_TRIAL_ID", "")
print(json.dumps({"event":"runtime_attestation",**attest()},sort_keys=True),flush=True)
db = connect()
try:
    if canary_id:
        enqueue(db, canary_id, "healthcheck", {"purpose": "persistence-proof"})
        row = db.execute("SELECT id,status,result FROM jobs WHERE id=?", (canary_id,)).fetchone()
        print(json.dumps({"event":"canary_observed_at_start","id":row[0],"status":row[1],"result":row[2]}),flush=True)
    if trial_id:
        db.execute("CREATE TABLE IF NOT EXISTS recovery_trials (id TEXT PRIMARY KEY, state TEXT NOT NULL)")
        row = db.execute("SELECT state FROM recovery_trials WHERE id=?", (trial_id,)).fetchone()
        if row and row[0] == "kill_armed":
            check = subprocess.run([sys.executable, "recovery_verifier.py", canary_id],capture_output=True,text=True)
            print(check.stdout.strip(),flush=True)
            if check.returncode:
                print(json.dumps({"event":"recovery_verification_failed","stderr":check.stderr}),flush=True)
                sys.exit(2)
            db.execute("UPDATE recovery_trials SET state='verified' WHERE id=?", (trial_id,))
            print(json.dumps({"event":"recovery_trial_verified","trial_id":trial_id}),flush=True)
finally:
    db.close()

while running:
    db = connect()
    try:
        result = run_once(db)
        if result:
            print(json.dumps({"event":"job_completed",**result}),flush=True)
        if trial_id and canary_id:
            row = db.execute("SELECT state FROM recovery_trials WHERE id=?", (trial_id,)).fetchone()
            job = db.execute("SELECT status FROM jobs WHERE id=?", (canary_id,)).fetchone()
            if not row and job and job[0] == "done":
                db.execute("PRAGMA synchronous=FULL")
                db.execute("INSERT INTO recovery_trials(id,state) VALUES (?, 'kill_armed')",(trial_id,))
                print(json.dumps({"event":"sigkill_armed","trial_id":trial_id,"pid":os.getpid()}),flush=True)
                db.close()
                os.kill(os.getpid(),signal.SIGKILL)
    finally:
        try: db.close()
        except Exception: pass
    time.sleep(interval)
