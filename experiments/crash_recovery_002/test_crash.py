import http.server, json, os, sqlite3, subprocess, sys, tempfile, threading, unittest
from pathlib import Path
ROOT=Path(__file__).parent
class Handler(http.server.BaseHTTPRequestHandler):
    effects={};writes=0
    def log_message(self,*args):pass
    def do_GET(self):
        key=self.path.removeprefix('/effects/')
        if key not in self.effects:
            self.send_response(404);self.end_headers();self.wfile.write(b'{}');return
        self.send_response(200);self.end_headers();self.wfile.write(json.dumps({'payload':self.effects[key]}).encode())
    def do_PUT(self):
        key=self.path.removeprefix('/effects/')
        value=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        if key in self.effects and self.effects[key]!=value:self.send_response(409)
        else:
            if key not in self.effects:type(self).writes+=1
            self.effects[key]=value;self.send_response(201)
        self.end_headers();self.wfile.write(json.dumps({'payload':self.effects[key]}).encode())
class Trial(unittest.TestCase):
    def test_sigkill_recovery(self):
        Handler.effects={};Handler.writes=0
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
        threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with tempfile.TemporaryDirectory() as d:
                env={**os.environ,'OWL_DB':str(Path(d)/'outbox.sqlite'),'OWL_API':f'http://127.0.0.1:{server.server_port}','OWL_KILL_AFTER_WRITE':'1'}
                first=subprocess.run([sys.executable,str(ROOT/'worker.py')],env=env,capture_output=True,text=True)
                self.assertEqual(first.returncode,-9,first.stderr)
                self.assertIn('KILL_AFTER_REMOTE_WRITE',first.stdout)
                db=sqlite3.connect(env['OWL_DB'])
                self.assertEqual(db.execute('select state from outbox').fetchone()[0],'pending')
                env.pop('OWL_KILL_AFTER_WRITE')
                second=subprocess.run([sys.executable,str(ROOT/'worker.py')],env=env,capture_output=True,text=True)
                self.assertEqual(second.returncode,0,second.stderr)
                self.assertIn('RECOVERED_VERIFIED',second.stdout)
                third=subprocess.run([sys.executable,str(ROOT/'worker.py')],env=env,capture_output=True,text=True)
                self.assertEqual(third.returncode,0,third.stderr)
                self.assertEqual(Handler.writes,1)
                self.assertEqual(db.execute('select state from outbox').fetchone()[0],'verified')
                print('PASS SIGKILL=-9; durable pending; recovery verified; remote side effects=1; rerun=1',flush=True)
        finally:server.shutdown();server.server_close()
if __name__=='__main__':unittest.main(verbosity=2)
