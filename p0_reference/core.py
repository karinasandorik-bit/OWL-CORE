"""OWL Core P0 local reference; versioned registry, grants, execution events."""
from __future__ import annotations
import hashlib, json, sqlite3, time, uuid
from dataclasses import dataclass
from typing import Callable

@dataclass(frozen=True)
class Skill:
    name: str
    version: str
    actuator: str
    handler: Callable[[dict],dict]

class Core:
    def __init__(self,path=':memory:'):
        self.db=sqlite3.connect(path)
        self.db.row_factory=sqlite3.Row
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS grants (id TEXT PRIMARY KEY, actuator TEXT NOT NULL, target_prefix TEXT NOT NULL, expires REAL NOT NULL, enabled INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS skills (name TEXT, version TEXT, actuator TEXT, PRIMARY KEY(name,version));
        CREATE TABLE IF NOT EXISTS actions (id TEXT PRIMARY KEY, key TEXT UNIQUE NOT NULL, skill TEXT NOT NULL, version TEXT NOT NULL, target TEXT NOT NULL, payload TEXT NOT NULL, status TEXT NOT NULL, result TEXT, verified INTEGER NOT NULL DEFAULT 0, created REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY AUTOINCREMENT, action_id TEXT NOT NULL, type TEXT NOT NULL, body TEXT NOT NULL, at REAL NOT NULL);
        """)
        self.skills={}
    def register(self,s):
        self.skills[(s.name,s.version)]=s
        self.db.execute('INSERT OR IGNORE INTO skills VALUES(?,?,?)',(s.name,s.version,s.actuator));self.db.commit()
    def grant(self,actuator,prefix,lifetime=3600):
        gid=str(uuid.uuid4())
        self.db.execute('INSERT INTO grants VALUES(?,?,?,?,1)',(gid,actuator,prefix,time.time()+lifetime))
        self.db.commit();return gid
    def authorized(self,actuator,target):
        return bool(self.db.execute('SELECT 1 FROM grants WHERE actuator=? AND enabled=1 AND expires>? AND substr(?,1,length(target_prefix))=target_prefix',(actuator,time.time(),target)).fetchone())
    def event(self,aid,kind,data):
        self.db.execute('INSERT INTO events(action_id,type,body,at) VALUES(?,?,?,?)',(aid,kind,json.dumps(data,sort_keys=True),time.time()))
    def submit(self,name,version,target,payload):
        key=hashlib.sha256(json.dumps([name,version,target,payload],sort_keys=True).encode()).hexdigest()
        old=self.db.execute('SELECT id FROM actions WHERE key=?',(key,)).fetchone()
        if old:return old['id']
        aid=str(uuid.uuid4())
        self.db.execute('INSERT INTO actions(id,key,skill,version,target,payload,status,created) VALUES(?,?,?,?,?,?,?,?)',(aid,key,name,version,target,json.dumps(payload,sort_keys=True),'proposed',time.time()))
        self.event(aid,'proposed',{});self.db.commit();return aid
    def run(self,aid,verifier):
        a=self.db.execute('SELECT * FROM actions WHERE id=?',(aid,)).fetchone()
        if a is None:raise KeyError(aid)
        if a['status'] in ('verified','failed','rejected'):return a['status']
        skill=self.skills.get((a['skill'],a['version']))
        if not skill or not self.authorized(skill.actuator,a['target']):
            self.db.execute("UPDATE actions SET status='rejected' WHERE id=?",(aid,))
            self.event(aid,'rejected',{});self.db.commit();return 'rejected'
        try:
            self.db.execute("UPDATE actions SET status='authorized' WHERE id=?",(aid,))
            self.event(aid,'authorized',{});self.db.commit()
            payload=json.loads(a['payload']);result=skill.handler(payload)
            self.db.execute("UPDATE actions SET status='executed',result=? WHERE id=?",(json.dumps(result),aid))
            self.event(aid,'executed',result);self.db.commit()
            ok=bool(verifier(payload,result));status='verified' if ok else 'failed'
            self.db.execute('UPDATE actions SET status=?,verified=? WHERE id=?',(status,int(ok),aid))
            self.event(aid,'verified' if ok else 'verification_failed',{});self.db.commit();return status
        except Exception as exc:
            self.db.execute("UPDATE actions SET status='failed' WHERE id=?",(aid,))
            self.event(aid,'failed',{'exception':type(exc).__name__});self.db.commit();return 'failed'
    def close(self):self.db.close()
