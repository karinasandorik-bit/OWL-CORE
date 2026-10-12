"""Bounded PostgreSQL worker. No HTTP actuator, shell, payments or signing."""
import json
import os
import uuid
from datetime import timedelta
import psycopg
from psycopg.rows import dict_row

ALLOWED = {"healthcheck", "evaluate_candidate"}

def connect():
    return psycopg.connect(os.environ["OWL_TEST_DATABASE_URL"], row_factory=dict_row, autocommit=True)

def enqueue(conn, job_id, kind, payload):
    if kind not in ALLOWED:
        raise ValueError("capability denied")
    with conn.transaction():
        conn.execute("""INSERT INTO owl_worker.jobs(id,kind,payload) VALUES (%s,%s,%s)
            ON CONFLICT(id) DO NOTHING""", (job_id,kind,json.dumps(payload)))

def claim(conn, owner, ttl_seconds=30):
    if not owner or not 1 <= ttl_seconds <= 3600:
        raise ValueError("invalid lease")
    with conn.transaction():
        return conn.execute("""
          WITH picked AS (
            SELECT id FROM owl_worker.jobs
            WHERE status='queued' OR (status='leased' AND lease_until < clock_timestamp())
            ORDER BY updated_at,id FOR UPDATE SKIP LOCKED LIMIT 1
          )
          UPDATE owl_worker.jobs j SET status='leased',lease_owner=%s,
            lease_until=clock_timestamp()+(%s * interval '1 second'),
            fencing_token=j.fencing_token+1,updated_at=clock_timestamp()
          FROM picked WHERE j.id=picked.id
          RETURNING j.id,j.kind,j.payload,j.fencing_token,j.lease_owner
        """, (owner,ttl_seconds)).fetchone()

def evaluate(kind,payload):
    if kind=="healthcheck":
        return {"ok":True,"mode":"bounded-postgres"}
    if kind=="evaluate_candidate":
        return {"accepted":False,"reason":"requires independent proof",
                "candidate":str(payload.get("candidate",""))[:120]}
    raise ValueError("capability denied")

def complete(conn, job_id, owner, token, result):
    with conn.transaction():
        row=conn.execute("""
          UPDATE owl_worker.jobs SET status='done',result=%s,
            lease_owner=NULL,lease_until=NULL,updated_at=clock_timestamp()
          WHERE id=%s AND status='leased' AND lease_owner=%s
            AND fencing_token=%s AND lease_until>clock_timestamp()
          RETURNING id
        """,(json.dumps(result),job_id,owner,token)).fetchone()
        return row is not None

def run_once(conn, owner=None):
    owner=owner or str(uuid.uuid4())
    job=claim(conn,owner)
    if job is None: return None
    result=evaluate(job["kind"],job["payload"])
    if not complete(conn,job["id"],owner,job["fencing_token"],result):
        raise RuntimeError("fenced or expired; result discarded")
    return {"id":job["id"],"result":result}

if __name__=="__main__":
    with connect() as conn:
        print(json.dumps(run_once(conn)))
