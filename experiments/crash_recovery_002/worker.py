import json, os, signal, sqlite3, urllib.request, urllib.error

DB = os.environ['OWL_DB']; API = os.environ['OWL_API']; EVENT = 'github:karinasandorik-bit/OWL-CORE:issue:2'
BODY = {'event_id': EVENT, 'action': 'bounded_canary', 'source': 'https://github.com/karinasandorik-bit/OWL-CORE/issues/2'}

def connect():
    c=sqlite3.connect(DB,timeout=10,isolation_level=None)
    c.execute('PRAGMA journal_mode=WAL'); c.execute('PRAGMA synchronous=FULL')
    c.execute('CREATE TABLE IF NOT EXISTS outbox (event_id TEXT PRIMARY KEY, payload TEXT NOT NULL, state TEXT NOT NULL, remote_id TEXT)')
    return c

def remote(method,path,data=None):
    req=urllib.request.Request(API+path,data=json.dumps(data).encode() if data is not None else None,method=method,headers={'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=10) as resp:return resp.status,json.load(resp)
    except urllib.error.HTTPError as e:return e.code,json.load(e)

def run():
    c=connect()
    c.execute('INSERT OR IGNORE INTO outbox VALUES (?,?,?,NULL)',(EVENT,json.dumps(BODY,sort_keys=True),'pending'))
    status,payload=remote('GET','/effects/'+EVENT)
    if status==404:
        status,payload=remote('PUT','/effects/'+EVENT,BODY)
        if status not in (200,201):raise RuntimeError((status,payload))
        if os.environ.get('OWL_KILL_AFTER_WRITE')=='1':
            print('KILL_AFTER_REMOTE_WRITE',flush=True)
            os.kill(os.getpid(),signal.SIGKILL)
    elif status!=200:raise RuntimeError((status,payload))
    if payload.get('payload')!=BODY:raise RuntimeError('REMOTE_CONFLICT')
    c.execute('UPDATE outbox SET state=?,remote_id=? WHERE event_id=?',('verified',EVENT,EVENT))
    print('RECOVERED_VERIFIED',flush=True)

if __name__=='__main__':run()
