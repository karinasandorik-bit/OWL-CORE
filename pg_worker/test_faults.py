"""Independent process-level tests against isolated CI PostgreSQL.
No live HTTP request is sent. Provider is a separate durable SQLite oracle.
"""
import json
import os
import signal
import sqlite3
import subprocess
import sys
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from worker import connect,enqueue,claim,complete
from reconcile import reconcile,Verdict

def test_two_independent_connections_compete():
    jid="compete-"+str(uuid.uuid4())
    with connect() as c: enqueue(c,jid,"healthcheck",{})
    def attempt(owner):
        with connect() as c:
            row=claim(c,owner,30)
            return row if row and row["id"]==jid else None
    with ThreadPoolExecutor(max_workers=2) as pool:
        a,b=list(pool.map(attempt,["a","b"]))
    assert (a is None)!=(b is None)

def test_sigkill_then_lease_takeover():
    jid="kill-"+str(uuid.uuid4())
    with connect() as c: enqueue(c,jid,"healthcheck",{})
    script="""import sys,time
from worker import connect,claim
with connect() as c:
 row=claim(c,'victim',1)
 print(row['id'] if row else 'NONE',flush=True)
 time.sleep(60)
"""
    proc=subprocess.Popen([sys.executable,"-c",script],cwd=str(Path(__file__).parent),
                          stdout=subprocess.PIPE,text=True)
    try:
        assert proc.stdout.readline().strip()==jid
        os.kill(proc.pid,signal.SIGKILL)
        proc.wait(timeout=5)
        import time
        time.sleep(1.3)
        with connect() as c:
            row=claim(c,"survivor",30)
            assert row and row["id"]==jid and row["fencing_token"]==2
            assert not complete(c,jid,"victim",1,{"stale":True})
            assert complete(c,jid,"survivor",2,{"ok":True})
    finally:
        if proc.poll() is None: proc.kill();proc.wait()

def test_provider_commit_before_receipt_crash():
    # Independent provider journal: durable commit in SQLite, not worker DB.
    with tempfile.TemporaryDirectory() as tmp:
        path=str(Path(tmp)/"provider.sqlite")
        key="effect-"+str(uuid.uuid4())
        script="""import sqlite3,sys,json,os
p,k=sys.argv[1:]; db=sqlite3.connect(p)
db.execute('CREATE TABLE effects (key TEXT PRIMARY KEY, receipt TEXT NOT NULL)')
db.execute('INSERT INTO effects VALUES (?,?)',(k,json.dumps({'idempotency_key':k,'provider_tx':'tx-1'})))
db.commit()
os.kill(os.getpid(),9)
"""
        p=subprocess.run([sys.executable,"-c",script,path,key])
        assert p.returncode != 0
        def lookup(k):
            with sqlite3.connect(path) as db:
                row=db.execute("SELECT receipt FROM effects WHERE key=?",(k,)).fetchone()
            return json.loads(row[0]) if row else None
        verdict,receipt=reconcile(key,lookup,lambda r:r.get("provider_tx")=="tx-1")
        assert verdict==Verdict.CONFIRMED and receipt["provider_tx"]=="tx-1"
        with sqlite3.connect(path) as db:
            assert db.execute("SELECT count(*) FROM effects").fetchone()[0]==1
        assert reconcile(key,lambda k:None,lambda r:True)[0]==Verdict.NOT_FOUND
        assert reconcile(key,lambda k: (_ for _ in ()).throw(OSError()),lambda r:True)[0]==Verdict.UNKNOWN
