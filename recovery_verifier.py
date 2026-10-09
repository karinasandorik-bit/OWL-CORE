"""Read-only independent process: verify one completed canary after SIGKILL."""
import json
import os
import sqlite3
import sys

job_id = sys.argv[1]
db_path = os.environ["OWL_DB"]
db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
try:
    rows = db.execute("SELECT id,status,result FROM jobs WHERE id=?", (job_id,)).fetchall()
finally:
    db.close()
valid = len(rows) == 1 and rows[0][1] == "done" and json.loads(rows[0][2]) == {"ok": True, "mode": "bounded"}
print(json.dumps({"event":"independent_recovery_verification","job_id":job_id,"row_count":len(rows),"status":rows[0][1] if rows else None,"verified":valid}),flush=True)
sys.exit(0 if valid else 1)
