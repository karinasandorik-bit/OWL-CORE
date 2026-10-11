import concurrent.futures,json,os,subprocess,sys,time,uuid
import psycopg
def run(*args,expect=0):
 p=subprocess.run([sys.executable,'worker.py',*args],capture_output=True,text=True,env=os.environ.copy())
 assert p.returncode==expect,(args,p.returncode,p.stdout,p.stderr)
 return p.stdout
def verify(k):
 p=subprocess.run([sys.executable,'verifier.py',k],capture_output=True,text=True,env=os.environ.copy())
 assert p.returncode==0,(p.stdout,p.stderr)
 return json.loads(p.stdout)
def case(label):return 'owl004-'+label+'-'+uuid.uuid4().hex[:8]
k=case('concurrent')
assert json.loads(run('--submit',k))['submitted']
assert not json.loads(run('--submit',k))['submitted']
with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
 results=list(pool.map(lambda i:json.loads(run('--once','--worker-id',f'c{i}')),range(12)))
assert sum(x.get('committed',False) for x in results)==1,results
assert verify(k)['effect_count']==1
print('PASS concurrent 12, dedupe, independent verifier')
k=case('before')
run('--submit',k)
run('--once','--lease','1','--crash','before_commit',expect=17)
time.sleep(1.3)
assert json.loads(run('--once','--worker-id','recovery'))['committed']
assert verify(k)['fence']==2
print('PASS before_commit crash, lease recovery, fencing')
k=case('after')
run('--submit',k)
run('--once','--crash','after_commit',expect=18)
assert not json.loads(run('--once'))['claimed']
assert verify(k)['effect_count']==1
print('PASS after_commit crash, idempotent effect')
with psycopg.connect(os.environ['OWL_WORKER_DSN']) as c:
 try:c.execute('select count(*) from owl_test.jobs')
 except psycopg.errors.InsufficientPrivilege:c.rollback()
 else:raise AssertionError('worker can read base table')
with psycopg.connect(os.environ['OWL_VERIFIER_DSN']) as c:
 try:c.execute('select owl_test.claim(%s,%s)',('forbidden',1))
 except psycopg.errors.InsufficientPrivilege:c.rollback()
 else:raise AssertionError('verifier can claim')
print('PASS privilege isolation')


# A stale lease owner must not commit after a different worker reclaims the job.
k=case('stale')
run('--submit',k)
with psycopg.connect(os.environ['OWL_WORKER_DSN'],autocommit=True) as c:
    first=c.execute('select job_key,payload,fence from owl_test.claim(%s,%s)',('stale-owner',1)).fetchone()
assert first is not None and first[0]==k
time.sleep(1.3)
with psycopg.connect(os.environ['OWL_WORKER_DSN'],autocommit=True) as c:
    second=c.execute('select job_key,payload,fence from owl_test.claim(%s,%s)',('new-owner',10)).fetchone()
    assert second is not None and second[0]==k and second[2]==first[2]+1
    stale_ok=c.execute('select owl_test.complete(%s,%s,%s,%s::jsonb)',(k,'stale-owner',first[2],json.dumps({'output':'stale'}))).fetchone()[0]
    assert stale_ok is False
    good={'input':second[1],'output':'ACK:'+k,'worker':'new-owner'}
    assert c.execute('select owl_test.complete(%s,%s,%s,%s::jsonb)',(k,'new-owner',second[2],json.dumps(good))).fetchone()[0] is True
assert verify(k)['fence']==2
print('PASS stale owner rejected after lease takeover')
