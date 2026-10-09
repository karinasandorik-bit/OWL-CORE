"""Continuous bounded OWL runner. Durable state requires OWL_DB on persistent volume."""
import json
import os
import signal
import time
from worker import connect, run_once
running = True
def stop(*_):
    global running
    running = False
signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGINT, stop)
interval = max(1, int(os.environ.get("OWL_POLL_SECONDS", "10")))
while running:
    db = connect()
    try:
        result = run_once(db)
        if result:
            print(json.dumps({"event":"job_completed", **result}), flush=True)
    finally:
        db.close()
    time.sleep(interval)
