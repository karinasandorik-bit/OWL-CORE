"""True HTTP timeout after durable commit, separate provider SQLite and PostgreSQL ledger.
An isolated adversarial substitute, NOT a Stripe sandbox verification.
"""
import json
import os
import sqlite3
import tempfile
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from multiprocessing import Process
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from worker import connect, enqueue, claim, complete
from reconcile import reconcile, Verdict

def provider_main(db_path, port_path):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_POST(self):
            if self.path != "/commit": self.send_error(404);return
            key = self.headers.get("Idempotency-Key")
            if not key: self.send_error(400);return
            with sqlite3.connect(db_path, timeout=10) as db:
                db.execute("INSERT OR IGNORE INTO effects(key, receipt) VALUES (?,?)",
                           (key, json.dumps({"idempotency_key":key, "provider_tx":"tx-"+key})))
                result=db.execute("SELECT receipt FROM effects WHERE key=?",(key,)).fetchone()[0]
                db.commit()
            # Provably committed, but never deliver the response within client timeout.
            time.sleep(1)
            try:
                body=result.encode()
                self.send_response(200)
                self.send_header("Content-Length",str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError): pass
        def do_GET(self):
            if not self.path.startswith("/lookup/"):self.send_error(404);return
            key=self.path[len("/lookup/"):]
            with sqlite3.connect(db_path) as db:
                row=db.execute("SELECT receipt FROM effects WHERE key=?",(key,)).fetchone()
            if row is None:self.send_error(404);return
            body=row[0].encode()
            self.send_response(200)
            self.send_header("Content-Length",str(len(body)))
            self.end_headers()
            self.wfile.write(body)
    http=ThreadingHTTPServer(("127.0.0.1",0),Handler)
    Path(port_path).write_text(str(http.server_address[1]))
    http.serve_forever()

def test_timeout_after_commit_two_independent_ledgers_no_duplicate():
    with tempfile.TemporaryDirectory() as directory:
        db_path=str(Path(directory)/"provider.sqlite")
        port_path=str(Path(directory)/"port")
        with sqlite3.connect(db_path) as db:
            db.execute("CREATE TABLE effects (key TEXT PRIMARY KEY, receipt TEXT NOT NULL)")
        server=Process(target=provider_main,args=(db_path,port_path))
        server.start()
        try:
            deadline=time.monotonic()+5
            while not Path(port_path).exists() and time.monotonic()<deadline:time.sleep(.02)
            assert Path(port_path).exists()
            base="http://127.0.0.1:"+Path(port_path).read_text()
            job_id="lost-response-"+uuid.uuid4().hex
            key="key-"+uuid.uuid4().hex
            with connect() as c:
                enqueue(c,job_id,"healthcheck",{})
                job=claim(c,"worker-A",1)
                assert job and job["id"]==job_id
            req=Request(base+"/commit",data=b"{}",headers={"Idempotency-Key":key},method="POST")
            try:
                with urlopen(req,timeout=.15):pass
                assert False,"The response must time out AFTER provider commit"
            except TimeoutError:pass
            # Oracle 1: independent durable provider ledger, no receipt in worker DB yet.
            with sqlite3.connect(db_path) as db:
                provider_before=db.execute("SELECT receipt FROM effects WHERE key=?",(key,)).fetchone()
            assert provider_before is not None
            with connect() as c:
                worker_before=c.execute("SELECT status,result FROM owl_worker.jobs WHERE id=%s",(job_id,)).fetchone()
                assert worker_before["status"]=="leased" and worker_before["result"] is None
            time.sleep(1.3)
            with connect() as c:
                taken=claim(c,"worker-B",30)
                assert taken and taken["id"]==job_id and taken["fencing_token"]==2
                def lookup(k):
                    with urlopen(base+"/lookup/"+k,timeout=3) as response:
                        return json.load(response)
                verdict,receipt=reconcile(key,lookup,
                                           lambda r:r.get("provider_tx")=="tx-"+key)
                assert verdict==Verdict.CONFIRMED
                assert not complete(c,job_id,"worker-A",1,{"unsafe":True})
                assert complete(c,job_id,"worker-B",2,{"provider_receipt":receipt})
            # Deliberately replay the original ambiguous POST with the SAME key.
            # This tests the actual idempotency behavior, not merely absence of retry.
            replay=Request(base+"/commit",data=b"{}",headers={"Idempotency-Key":key},method="POST")
            with urlopen(replay,timeout=3) as response:
                replay_receipt=json.load(response)
            assert replay_receipt==receipt
            # A second reconciliation must not cause a new operation.
            assert reconcile(key,lookup,lambda r:r==receipt)[0]==Verdict.CONFIRMED
            # Oracle 2: PostgreSQL independently persisted the reconciled receipt.
            with connect() as c:
                worker_after=c.execute("SELECT status,result FROM owl_worker.jobs WHERE id=%s",(job_id,)).fetchone()
            assert worker_after["status"]=="done"
            assert worker_after["result"]["provider_receipt"]==receipt
            with sqlite3.connect(db_path) as db:
                effect_count=db.execute("SELECT COUNT(*) FROM effects WHERE key=?",(key,)).fetchone()[0]
                total_effects=db.execute("SELECT COUNT(*) FROM effects").fetchone()[0]
                provider_after=json.loads(db.execute("SELECT receipt FROM effects WHERE key=?",(key,)).fetchone()[0])
            assert effect_count==total_effects==1
            assert provider_after==worker_after["result"]["provider_receipt"]
        finally:
            server.terminate()
            server.join(timeout=5)
            if server.is_alive():server.kill();server.join()
