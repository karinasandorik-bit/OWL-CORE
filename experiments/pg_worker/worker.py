import os,json,hashlib,uuid,base64
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import psycopg
REPO='karinasandorik-bit/OWL-CORE'
BRANCH='trial/minimal-kernel-001'
PATH='experiments/minimal_kernel/canary/issue-2.json'
OP='owl:github:issue:2:canary:v1'
EXPECTED={'schema':'OWL_GITHUB_CANARY_V1','source_issue':f'https://github.com/{REPO}/issues/2','event_id':f'github:{REPO}:issue:2','action':'write_deterministic_marker','authorized_branch':BRANCH}
RAW=(json.dumps(EXPECTED,indent=2)+'\n').encode()
HASH=hashlib.sha256(RAW).hexdigest()
def api(method,path,payload=None):
    headers={'Authorization':'Bearer '+os.environ['GITHUB_TOKEN'],'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'}
    data=json.dumps(payload).encode() if payload is not None else None
    if data:headers['Content-Type']='application/json'
    try:
        with urlopen(Request('https://api.github.com'+path,data=data,headers=headers,method=method),timeout=20) as r:return r.status,json.load(r)
    except HTTPError as e:return e.code,json.load(e)
def observed():
    code,obj=api('GET',f'/repos/{REPO}/contents/{PATH}?ref={BRANCH}')
    if code==404:return None
    if code!=200:raise RuntimeError(f'GitHub read failed {code}')
    raw=base64.b64decode(obj['content'].replace('\n',''))
    if hashlib.sha256(raw).hexdigest()!=HASH:raise RuntimeError('REMOTE_CONFLICT')
    return obj['sha']
def run():
    with psycopg.connect(os.environ['DATABASE_URL'],autocommit=True) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS owl_canary_outbox(
        op_id text PRIMARY KEY,expected_sha256 text NOT NULL,status text NOT NULL DEFAULT 'pending',
        attempts integer NOT NULL DEFAULT 0,claim_id uuid,lease_until timestamptz,
        observed_blob_sha text,updated_at timestamptz NOT NULL DEFAULT now())""")
        db.execute('SELECT pg_advisory_lock(hashtextextended(%s,0))',(OP,))
        try:
            db.execute('INSERT INTO owl_canary_outbox(op_id,expected_sha256) VALUES(%s,%s) ON CONFLICT DO NOTHING',(OP,HASH))
            row=db.execute('SELECT expected_sha256 FROM owl_canary_outbox WHERE op_id=%s',(OP,)).fetchone()
            if row[0]!=HASH:raise RuntimeError('OUTBOX_CONFLICT')
            claim=str(uuid.uuid4())
            db.execute("UPDATE owl_canary_outbox SET claim_id=%s,lease_until=now()+interval '90 seconds',attempts=attempts+1 WHERE op_id=%s",(claim,OP))
            blob=observed()
            if blob is None:
                code,obj=api('PUT',f'/repos/{REPO}/contents/{PATH}',{'message':'owl bounded canary','content':base64.b64encode(RAW).decode(),'branch':BRANCH})
                if code not in (200,201):
                    blob=observed()
                    if blob is None:raise RuntimeError(f'GitHub write failed {code}')
                else:
                    if os.getenv('OWL_KILL_AFTER_GITHUB_WRITE')=='1':
                        print('KILL_AFTER_GITHUB_WRITE',flush=True);os.kill(os.getpid(),9)
                    blob=observed()
            db.execute("UPDATE owl_canary_outbox SET status='verified',observed_blob_sha=%s,lease_until=NULL,updated_at=now() WHERE op_id=%s AND claim_id=%s",(blob,OP,claim))
            print(json.dumps({'status':'verified','blob_sha':blob}),flush=True)
        finally:db.execute('SELECT pg_advisory_unlock(hashtextextended(%s,0))',(OP,))
if __name__=='__main__':run()
