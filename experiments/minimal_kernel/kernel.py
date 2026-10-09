import hashlib, json, sqlite3

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

class Kernel:
    def __init__(self,path):
        self.db=sqlite3.connect(path)
        self.db.execute('create table if not exists jobs (event_id text primary key, payload text not null, evidence_hash text not null, status text not null, outcome text, outcome_hash text)')
        self.db.commit()
    def ingest(self,event_id,payload):
        raw=json.dumps(payload,sort_keys=True)
        self.db.execute('insert or ignore into jobs(event_id,payload,evidence_hash,status) values (?,?,?,?)',(event_id,raw,digest(payload),'pending'))
        self.db.commit()
    def step(self,event_id,fail_after_decision=False):
        row=self.db.execute('select payload,evidence_hash,status from jobs where event_id=?',(event_id,)).fetchone()
        if not row: raise ValueError('unknown event')
        raw,expected,status=row
        if digest(json.loads(raw))!=expected:
            self.db.execute('update jobs set status=? where event_id=?',('tainted',event_id));self.db.commit();return 'tainted'
        if status=='verified': return 'verified'
        if status=='tainted': return 'tainted'
        event=json.loads(raw)
        if event.get('kind')!='github_issue' or not isinstance(event.get('issue'),int): raise ValueError('untrusted event')
        if fail_after_decision: raise RuntimeError('injected crash')
        outcome={'event_id':event_id,'decision':'inspect','action':'local_validation','result':'eligible','source_hash':expected}
        self.db.execute('update jobs set status=?,outcome=?,outcome_hash=? where event_id=?',('verified',json.dumps(outcome,sort_keys=True),digest(outcome),event_id));self.db.commit()
        return 'verified'
    def verify(self,event_id):
        row=self.db.execute('select payload,evidence_hash,status,outcome,outcome_hash from jobs where event_id=?',(event_id,)).fetchone()
        if not row:return False
        raw,eh,status,out,oh=row
        if digest(json.loads(raw))!=eh or status!='verified' or not out:return False
        obj=json.loads(out)
        return digest(obj)==oh and obj['source_hash']==eh and obj['event_id']==event_id
