"""Actual loopback HTTP provider, durable independent SQLite ledger, PostgreSQL workers.
Only localhost CI provider; no real-world side effects.
"""
import json, os, signal, sqlite3, subprocess, sys, tempfile, time, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from multiprocessing import Process
from pathlib import Path
from urllib.request import Request, urlopen
from worker import connect, enqueue, claim, complete
from reconcile import reconcile, Verdict

def serve(db_path, port_path):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_POST(self):
            key=self.headers.get("Idempotency-Key")
            if self.path!="/commit" or not key:
                self.send_error(400);return
            with sqlite3.connect(db_path,timeout=10) as db:
                db.execute("INSERT OR IGNORE INTO effects(key,receipt) VALUES (?,?)",
                           (key,json.dumps({"idempotency_key":key,"provider_tx":"tx-"+key})))
                row=db.execute("SELECT receipt FROM effects WHERE key=?",(key,)).fetchone()
                db.commit()
            body=row[0].encode()
            self.send_response(200);self.send_header("Content-Length",str(len(body)))
            self.end_headers();self.wfile.write(body)
        def do_GET(self):
            key=self.path.removeprefix("/lookup/")
            if not self.path.startswith("/lookup/"):
                self.send_error(404);return
            with sqlite3.connect(db_path) as db:
                row=db.execute("SELECT receipt FROM effects WHERE key=?",(key,)).fetchone()
            if not row:self.send_error(404);return
            body=row[0].encode()
            self.send_response(200);self.send_header("Content-Length",str(len(body)))
            self.end_headers();self.wfile.write(body)
    server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
    Path(port_path).write_text(str(server.server_address[1]))
    server.serve_forever()

def http_lookup(base,key):
    from urllib.error import HTTPError
    try:
        with urlopen(base+"/lookup/"+key,timeout=3) as r:return json.load(r)
    except HTTPError as e:
        if e.code==404:return None
        raise

def test_real_http_commit_kill_before_receipt_and_recover():
    with tempfile.TemporaryDirectory() as tmp:
        db_path=str(Path(tmp)/"provider.sqlite")
        port_path=str(Path(tmp)/"port")
        with sqlite3.connect(db_path) as db:
            db.execute("CREATE TABLE effects(key TEXT PRIMARY KEY,receipt TEXT NOT NULL)")
        provider=Process(target=serve,args=(db_path,port_path))
        provider.start()
        try:
            deadline=time.monotonic()+5
            while not Path(port_path).exists() and time.monotonic()<deadline:time.sleep(.03)
            assert Path(port_path).exists()
            base="http://127.0.0.1:"+Path(port_path).read_text()
            jid="http-"+uuid.uuid4().hex
            key="effect-"+uuid.uuid4().hex
            with connect() as c:enqueue(c,jid,"healthcheck",{})
            script="""import os,sys,json,signal
from urllib.request import Request,urlopen
from worker import connect,claim
base,jid,key=sys.argv[1:]
with connect() as c:
 row=claim(c,'crash-worker',1)
 assert row and row['id']==jid
 req=Request(base+'/commit',data=b'{}',headers={'Idempotency-Key':key},method='POST')
 with urlopen(req,timeout=5) as r:
  assert r.status==200
  assert json.load(r)['idempotency_key']==key
 os.kill(os.getpid(),signal.SIGKILL)
"""
            p=subprocess.run([sys.executable,"-c",script,base,jid,key],
                             cwd=str(Path(__file__).parent),timeout=10)
            assert p.returncode==-signal.SIGKILL
            with connect() as c:
                assert c.execute("SELECT status FROM owl_worker.jobs WHERE id=%s",(jid,)).fetchone()["status"]=="leased"
            time.sleep(1.3)
            with connect() as c:
                row=claim(c,"recovery-worker",30)
                assert row and row["id"]==jid and row["fencing_token"]==2
                verdict,receipt=reconcile(key,lambda k:http_lookup(base,k),
                                           lambda r:r.get("provider_tx")=="tx-"+key)
                assert verdict==Verdict.CONFIRMED
                assert not complete(c,jid,"crash-worker",1,{"unsafe":True})
                assert complete(c,jid,"recovery-worker",2,{"provider_receipt":receipt})
            # Adversarial duplicate POST: provider must return same receipt and keep one effect.
            for _ in range(2):
                req=Request(base+"/commit",data=b"{}",headers={"Idempotency-Key":key},method="POST")
                with urlopen(req,timeout=3) as r:assert json.load(r)==receipt
            with sqlite3.connect(db_path) as db:
                assert db.execute("SELECT count(*) FROM effects WHERE key=?",(key,)).fetchone()[0]==1
                assert db.execute("SELECT count(*) FROM effects").fetchone()[0]==1
            with connect() as c:
                assert c.execute("SELECT status FROM owl_worker.jobs WHERE id=%s",(jid,)).fetchone()["status"]=="done"
        finally:
            provider.terminate();provider.join(timeout=5)
            if provider.is_alive():provider.kill();provider.join()
