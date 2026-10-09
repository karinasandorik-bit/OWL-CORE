"""Live GitHub Actions-only canary: SIGKILL after new remote create, two-worker recovery."""
import base64,hashlib,json,os,signal,subprocess,sys,time
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import psycopg
REPO=os.environ['OWL_REPO']; BRANCH=os.environ['OWL_BRANCH']; RUN=os.environ['OWL_RUN_ID']
PATH=f'experiments/pg_worker/live_canary/{RUN}.json'
OP=f'owl:live:{RUN}'
RAW=(json.dumps({'schema':'OWL_LIVE_CANARY_V1','run_id':RUN,'operation_id':OP},sort_keys=True)+'\n').encode()
DIGEST=hashlib.sha256(RAW).hexdigest()
def api(method,endpoint,data=None):
    headers={'Authorization':'Bearer '+os.environ['GITHUB_TOKEN'],'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'}
    payload=json.dumps(data).encode() if data is not None else None
    if payload:headers['Content-Type']='application/json'
    try:
        with urlopen(Request('https://api.github.com'+endpoint,method=method,headers=headers,data=payload),timeout=30) as r:return r.status,json.load(r)
    except HTTPError as e:return e.code,json.load(e)
def remote():
    code,obj=api('GET',f'/repos/{REPO}/contents/{PATH}?ref={BRANCH}')
    if code==404:return None
    if code!=200:raise RuntimeError(f'GET {code}: {obj}')
    if hashlib.sha256(base64.b64decode(obj['content'])).hexdigest()!=DIGEST:raise RuntimeError('REMOTE_TAINT')
    return obj['sha']
def work(kill=False):
    with psycopg.connect(os.environ['DATABASE_URL'],autocommit=True) as db:
        db.execute("CREATE TABLE IF NOT EXISTS owl_live_outbox(op text PRIMARY KEY, digest text NOT NULL, state text NOT NULL, attempts int NOT NULL DEFAULT 0, blob text)")
        # Session lock held throughout remote call; released automatically on SIGKILL.
        db.execute('SELECT pg_advisory_lock(hashtextextended(%s,0))',(OP,))
        try:
            db.execute('INSERT INTO owl_live_outbox(op,digest,state) VALUES(%s,%s,%s) ON CONFLICT DO NOTHING',(OP,DIGEST,'pending'))
            row=db.execute('SELECT digest FROM owl_live_outbox WHERE op=%s',(OP,)).fetchone()
            if row[0]!=DIGEST:raise RuntimeError('OUTBOX_TAINT')
            db.execute('UPDATE owl_live_outbox SET attempts=attempts+1 WHERE op=%s',(OP,))
            blob=remote()
            if blob is None:
                code,obj=api('PUT',f'/repos/{REPO}/contents/{PATH}',{'message':f'owl live canary {RUN}','content':base64.b64encode(RAW).decode(),'branch':BRANCH})
                if code not in (200,201):
                    blob=remote()
                    if blob is None:raise RuntimeError(f'PUT {code}: {obj}')
                else:
                    if kill:
                        print('GITHUB_WRITE_ACKNOWLEDGED_THEN_SIGKILL',flush=True)
                        os.kill(os.getpid(),signal.SIGKILL)
                    blob=remote()
            db.execute("UPDATE owl_live_outbox SET state='verified',blob=%s WHERE op=%s",(blob,OP))
            print('WORKER_VERIFIED',blob,flush=True)
        finally:db.execute('SELECT pg_advisory_unlock(hashtextextended(%s,0))',(OP,))
def orchestrate():
    if remote() is not None:raise RuntimeError('RUN_CANARY_ALREADY_EXISTS')
    first=subprocess.run([sys.executable,__file__,'worker','kill'],capture_output=True,text=True)
    print('first:',first.returncode,first.stdout,first.stderr,flush=True)
    if first.returncode!=-signal.SIGKILL or 'GITHUB_WRITE_ACKNOWLEDGED_THEN_SIGKILL' not in first.stdout:raise RuntimeError('NO_PROVEN_SIGKILL')
    with psycopg.connect(os.environ['DATABASE_URL']) as db:
        row=db.execute('SELECT state,attempts FROM owl_live_outbox WHERE op=%s',(OP,)).fetchone()
        if row!=('pending',1):raise RuntimeError(f'OUTBOX_NOT_PENDING {row}')
    children=[subprocess.Popen([sys.executable,__file__,'worker'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True) for _ in range(2)]
    for p in children:
        out,err=p.communicate(timeout=90);print('recovery:',p.returncode,out,err,flush=True)
        if p.returncode:raise RuntimeError('RECOVERY_FAILED')
    with psycopg.connect(os.environ['DATABASE_URL']) as db:
        row=db.execute('SELECT state,attempts,blob FROM owl_live_outbox WHERE op=%s',(OP,)).fetchone()
        if row[0]!='verified' or row[1]!=3:raise RuntimeError(f'BAD_OUTBOX {row}')
    blob=remote()
    if blob!=row[2]:raise RuntimeError('REMOTE_NOT_VERIFIED')
    code,obj=api('GET',f'/repos/{REPO}/commits?path={PATH}&sha={BRANCH}&per_page=100')
    if code!=200 or len(obj)!=1:raise RuntimeError(f'NOT_EXACTLY_ONE_REMOTE_COMMIT {code} {len(obj) if isinstance(obj,list) else obj}')
    print('LIVE_PROOF_PASS: SIGKILL=-9, durable pending, 2 workers, 1 remote path commit, verified SHA',blob,flush=True)
if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='worker':work(len(sys.argv)>2 and sys.argv[2]=='kill')
    else:orchestrate()
