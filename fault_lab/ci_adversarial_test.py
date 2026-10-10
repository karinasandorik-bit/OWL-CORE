import os,sys,json,uuid,time,signal,subprocess,sqlite3,tempfile,threading,hashlib
from pathlib import Path
import psycopg,requests
from fastapi import FastAPI,HTTPException
from pydantic import BaseModel
import uvicorn
DSN=os.environ["OWL_PG_DSN"]
ROOT=Path(os.environ.get("GITHUB_WORKSPACE","."))
OUT=ROOT/"owl005_evidence"; OUT.mkdir(exist_ok=True)
SCHEMA="owlfi_"+uuid.uuid4().hex[:12]
PORT=18375
URL=f"http://127.0.0.1:{PORT}"
def canonical(x):return json.dumps(x,sort_keys=True,separators=(",",":"))
def sha(x):return hashlib.sha256(canonical(x).encode()).hexdigest()
def conn():return psycopg.connect(DSN,options="-c search_path="+SCHEMA)
def get(c,q,p=()):
 with c.cursor() as cur:cur.execute(q,p);return cur.fetchall()
def execute(c,q,p=()):
 with c.cursor() as cur:cur.execute(q,p)
def capture(db):
 with db.cursor() as cur:
  cur.execute("SELECT id,state,fence,lease_owner,extract(epoch from lease_until),result FROM jobs")
  jobs=[dict(zip(["id","state","fence","lease_owner","lease_until_epoch","result"],r)) for r in cur.fetchall()]
  cur.execute("SELECT id,job_id,state,payload,external_receipt FROM actions")
  actions=[dict(zip(["id","job_id","state","payload","external_receipt"],r)) for r in cur.fetchall()]
  cur.execute("SELECT kind,detail FROM events ORDER BY seq")
  events=[dict(zip(["kind","detail"],r)) for r in cur.fetchall()]
 return dict(jobs=jobs,actions=actions,events=events)
def worker(name,ttl,crash=False):
 with conn() as db:
  with db.transaction():
   rows=get(db,"SELECT id,spec FROM jobs WHERE state='queued' OR (state='running' AND lease_until < clock_timestamp()) FOR UPDATE SKIP LOCKED LIMIT 1")
   assert len(rows)==1,("claim count",rows)
   jid,spec=rows[0]
   fence=get(db,"UPDATE jobs SET state='running',fence=fence+1,lease_owner=%s,lease_until=clock_timestamp()+(%s * interval '1 second') WHERE id=%s RETURNING fence",(name,ttl,jid))[0][0]
   execute(db,"INSERT INTO events(job_id,kind,detail) VALUES (%s,'claim',%s::jsonb)",(jid,canonical(dict(worker=name,fence=fence))))
  key=sha(dict(action_for=jid))[:32]
  payload=dict(kind="notification",message=spec["message"])
  with db.transaction():
   assert get(db,"SELECT 1 FROM jobs WHERE id=%s AND lease_owner=%s AND fence=%s AND lease_until>clock_timestamp() FOR UPDATE",(jid,name,fence))
   execute(db,"INSERT INTO actions (id,job_id,payload) VALUES (%s,%s,%s::jsonb) ON CONFLICT (job_id) DO NOTHING",(key,jid,canonical(payload)))
   assert get(db,"SELECT id,payload FROM actions WHERE job_id=%s",(jid,))[0]==(key,payload)
  db.commit()
  lookup=requests.get(URL+"/v1/effects/"+key,timeout=5)
  if lookup.status_code==404:
   response=requests.post(URL+"/v1/effects",json=dict(key=key,payload=payload),timeout=5)
   response.raise_for_status()
   receipt=response.json()
  else:
   lookup.raise_for_status()
   receipt=lookup.json()
  assert receipt["key"]==key and receipt["payload_sha256"]==sha(payload)
  if crash:
   (OUT/"crash_marker.json").write_text(canonical(dict(worker=name,stage="after_http_committed_before_postgres_receipt",key=key,receipt=receipt)))
   os.kill(os.getpid(),signal.SIGKILL)
  with db.transaction():
   assert get(db,"SELECT 1 FROM jobs WHERE id=%s AND lease_owner=%s AND fence=%s AND lease_until>clock_timestamp() FOR UPDATE",(jid,name,fence)), "stale fencing"
   assert get(db,"SELECT payload FROM actions WHERE id=%s",(key,))[0][0]==payload
   execute(db,"UPDATE actions SET state='done',external_receipt=%s::jsonb WHERE id=%s",(canonical(receipt),key))
   execute(db,"UPDATE jobs SET state='done',result=%s::jsonb WHERE id=%s",(canonical(receipt),jid))
   execute(db,"INSERT INTO events(job_id,kind,detail) VALUES (%s,'completed',%s::jsonb)",(jid,canonical(dict(fence=fence,key=key))))
  db.commit()
  print(canonical(dict(worker=name,status="done",job=jid,fence=fence)),flush=True)
def start_provider():
 dbpath=os.environ["OWL_PROVIDER_DB"]
 app=FastAPI()
 class Effect(BaseModel):
  key:str
  payload:dict
 lock=threading.Lock()
 def open_db():
  c=sqlite3.connect(dbpath,timeout=15)
  c.execute("CREATE TABLE IF NOT EXISTS effects(key TEXT PRIMARY KEY,payload_hash TEXT,receipt TEXT)")
  return c
 @app.get("/healthz")
 def health():return dict(ok=True)
 @app.get("/v1/effects/{key}")
 def lookup(key:str):
  with open_db() as c:
   row=c.execute("SELECT receipt FROM effects WHERE key=?",(key,)).fetchone()
  if row is None:raise HTTPException(404,"not found")
  return json.loads(row[0])
 @app.post("/v1/effects")
 def effect(b:Effect):
  with lock:
   with open_db() as c:
    c.execute("BEGIN IMMEDIATE")
    row=c.execute("SELECT payload_hash,receipt FROM effects WHERE key=?",(b.key,)).fetchone()
    if row:
     if row[0]!=sha(b.payload):raise HTTPException(409,"conflicting payload")
     return json.loads(row[1])
    receipt=dict(key=b.key,payload_sha256=sha(b.payload),accepted=True,provider_ref="provider-"+b.key)
    c.execute("INSERT INTO effects VALUES (?,?,?)",(b.key,sha(b.payload),canonical(receipt)))
    return receipt
 uvicorn.run(app,host="127.0.0.1",port=PORT,log_level="warning")
def run_sub(*args):
 proc=subprocess.run([sys.executable,__file__,*args],capture_output=True,text=True,timeout=40,env=dict(os.environ,OWL_SCHEMA=SCHEMA))
 return dict(args=list(args),pid=None,exit_code=proc.returncode,stdout=proc.stdout,stderr=proc.stderr)
if __name__=="__main__":
 if len(sys.argv)>1:
  SCHEMA=os.environ["OWL_SCHEMA"]
  if sys.argv[1]=="provider":start_provider()
  elif sys.argv[1]=="worker":worker(sys.argv[2],int(sys.argv[3]),sys.argv[4]=="crash")
  sys.exit()
 import traceback
 provider=None
 try:
  with psycopg.connect(DSN,autocommit=True) as c:execute(c,'CREATE SCHEMA "'+SCHEMA+'"')
  with conn() as db:
   execute(db,"CREATE TABLE jobs(id text PRIMARY KEY,spec jsonb NOT NULL,state text NOT NULL DEFAULT 'queued',lease_owner text,lease_until timestamptz,fence bigint NOT NULL DEFAULT 0,result jsonb)")
   execute(db,"CREATE TABLE actions(id text PRIMARY KEY,job_id text UNIQUE REFERENCES jobs(id),payload jsonb NOT NULL,state text NOT NULL DEFAULT 'pending',external_receipt jsonb)")
   execute(db,"CREATE TABLE events(seq bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,job_id text REFERENCES jobs(id),kind text,detail jsonb)")
   jid=sha(dict(message="OWL fault test "+SCHEMA))[:24]
   execute(db,"INSERT INTO jobs(id,spec) VALUES (%s,%s::jsonb)",(jid,canonical(dict(message="OWL fault test "+SCHEMA))))
   db.commit()
  tmp=tempfile.TemporaryDirectory()
  os.environ["OWL_PROVIDER_DB"]=str(Path(tmp.name)/"effects.sqlite")
  provider=subprocess.Popen([sys.executable,__file__,"provider"],env=dict(os.environ,OWL_SCHEMA=SCHEMA),stdout=(OUT/"provider_stdout.log").open("w"),stderr=(OUT/"provider_stderr.log").open("w"))
  for i in range(80):
   try:
    if requests.get(URL+"/healthz",timeout=.25).ok:break
   except requests.RequestException:pass
   time.sleep(.1)
  else:raise RuntimeError("provider unavailable")
  first=run_sub("worker","worker-A","2","crash")
  (OUT/"worker_a_exit.json").write_text(canonical(first))
  assert first["exit_code"]==-signal.SIGKILL,first
  assert (OUT/"crash_marker.json").exists(),"crash not at expected point"
  with conn() as db:
   before=capture(db);db.commit()
  (OUT/"postgres_before.json").write_text(json.dumps(before,indent=2,default=str))
  assert before["jobs"][0]["state"]=="running" and before["jobs"][0]["fence"]==1
  assert before["actions"][0]["external_receipt"] is None
  marker=json.loads((OUT/"crash_marker.json").read_text())
  observed=requests.get(URL+"/v1/effects/"+marker["key"],timeout=5).json()
  assert observed==marker["receipt"],"provider did not commit receipt"
  # Restart BOTH independent durable systems after the committed effect and SIGKILL.
  provider.terminate()
  provider.wait(timeout=6)
  container_id=os.environ["OWL_TEST_POSTGRES_CONTAINER"]
  restart=subprocess.run(["docker","restart",container_id],capture_output=True,text=True,timeout=50)
  (OUT/"postgres_restart.json").write_text(canonical(dict(exit_code=restart.returncode,stdout=restart.stdout,stderr=restart.stderr)))
  assert restart.returncode==0, restart.stderr
  for attempt in range(100):
   try:
    with conn() as check:check.execute("SELECT 1")
    break
   except Exception:time.sleep(.1)
  else:raise RuntimeError("Postgres did not recover")
  provider=subprocess.Popen([sys.executable,__file__,"provider"],env=dict(os.environ,OWL_SCHEMA=SCHEMA),
                            stdout=(OUT/"provider_restarted_stdout.log").open("w"),
                            stderr=(OUT/"provider_restarted_stderr.log").open("w"))
  for attempt in range(80):
   try:
    if requests.get(URL+"/healthz",timeout=.25).ok:break
   except requests.RequestException:pass
   time.sleep(.1)
  else:raise RuntimeError("provider restart failure")
  time.sleep(2.7)
  # Eight distinct OS worker processes race for ONE expired job.
  contenders=[subprocess.Popen([sys.executable,__file__,"worker",f"worker-{i}", "15", "recover"],
                 env=dict(os.environ,OWL_SCHEMA=SCHEMA),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
              for i in range(8)]
  exits=[]
  for idx,p in enumerate(contenders):
   stdout,stderr=p.communicate(timeout=30)
   exits.append(dict(worker=idx,pid=p.pid,exit_code=p.returncode,stdout=stdout,stderr=stderr))
  (OUT/"worker_contenders.json").write_text(json.dumps(exits,indent=2))
  successful=[x for x in exits if x["exit_code"]==0]
  assert len(successful)==1,exits
  second=successful[0]
  (OUT/"worker_b_exit.json").write_text(canonical(second))
  with conn() as db:
   after=capture(db);db.commit()
  (OUT/"postgres_after.json").write_text(json.dumps(after,indent=2,default=str))
  with sqlite3.connect(os.environ["OWL_PROVIDER_DB"]) as c:
   effects=[dict(zip(["key","payload_hash","receipt"],r)) for r in c.execute("SELECT key,payload_hash,receipt FROM effects")]
  (OUT/"provider_ledger.json").write_text(json.dumps(effects,indent=2))
  assert len(effects)==1
  job=after["jobs"][0];action=after["actions"][0]
  assert job["state"]=="done" and job["fence"]==2
  assert action["state"]=="done" and action["external_receipt"]==job["result"]
  assert json.loads(effects[0]["receipt"])==job["result"]
  assert [x["kind"] for x in after["events"]].count("claim")==2
  assert [x["kind"] for x in after["events"]].count("completed")==1
  report=dict(status="PASS",scenario="provider_restart_and_postgres_restart_after_SIGKILL_then_eight_worker_race",worker_a_exit=first["exit_code"],worker_b_exit=second["exit_code"],contenders=8,successful_workers=1,postgres_fence=job["fence"],provider_effects=len(effects),pg_completion_events=1,receipt_match=True)
  (OUT/"report.json").write_text(json.dumps(report,indent=2))
  print(json.dumps(report,indent=2))
 except BaseException as exc:
  (OUT/"report.json").write_text(json.dumps(dict(status="FAIL",error=str(exc),traceback=traceback.format_exc()),indent=2))
  raise
 finally:
  if provider:
   provider.terminate()
   try:provider.wait(timeout=3)
   except subprocess.TimeoutExpired:provider.kill()
  try:
   with psycopg.connect(DSN,autocommit=True) as c:execute(c,'DROP SCHEMA IF EXISTS "'+SCHEMA+'" CASCADE')
  except Exception as exc:print("cleanup",repr(exc),file=sys.stderr)
