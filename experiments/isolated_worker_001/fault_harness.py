#!/usr/bin/env python3
"""Local SQLite fault harness; NOT a PostgreSQL or remote-runtime validation."""
import hashlib, json, os, sqlite3, sys, uuid
DB=os.environ.get("OWL_TEST_DB","/tmp/owl_worker_test.sqlite")
JOB="owl-core-test-003"
INPUT="OWL-CORE|isolated|003"
def connect():
 c=sqlite3.connect(DB,timeout=10,isolation_level=None)
 c.execute("PRAGMA busy_timeout=10000")
 c.execute("PRAGMA journal_mode=WAL")
 c.execute("CREATE TABLE IF NOT EXISTS ledger(job_key TEXT PRIMARY KEY,worker_id TEXT NOT NULL,input_sha256 TEXT NOT NULL,result TEXT NOT NULL,committed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
 return c
def worker():
 c=connect()
 payload=json.dumps({"input":INPUT,"output":"ACK:003","status":"COMPLETED"},sort_keys=True)
 c.execute("BEGIN IMMEDIATE")
 if os.environ.get("OWL_INJECT_FAILURE")=="before_commit":os._exit(17)
 c.execute("INSERT OR IGNORE INTO ledger(job_key,worker_id,input_sha256,result) VALUES (?,?,?,?)",(JOB,str(uuid.uuid4()),hashlib.sha256(INPUT.encode()).hexdigest(),payload))
 c.execute("COMMIT")
 if os.environ.get("OWL_INJECT_FAILURE")=="after_commit":os._exit(18)
 print(json.dumps({"rows":c.execute("SELECT count(*) FROM ledger WHERE job_key=?",(JOB,)).fetchone()[0]}))
def verify():
 rows=connect().execute("SELECT job_key,worker_id,input_sha256,result FROM ledger WHERE job_key=?",(JOB,)).fetchall()
 assert len(rows)==1
 key,worker,digest,raw=rows
 assert key==JOB and worker and digest==hashlib.sha256(INPUT.encode()).hexdigest()
 assert json.loads(raw)=={"input":INPUT,"output":"ACK:003","status":"COMPLETED"}
 print(json.dumps({"verified":True,"row_count":len(rows),"worker_id":worker,"sha256":digest}))
if __name__=="__main__": {"worker":worker,"verify":verify}[sys.argv[1]]()
