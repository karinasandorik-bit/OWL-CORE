import http.server, os, subprocess, sys, tempfile, threading
from pathlib import Path
from test_crash import Handler
ROOT=Path(__file__).parent
class RaceHandler(Handler):
    lock=threading.Lock()
    barrier=threading.Barrier(2,timeout=8)
    puts=0
    def do_GET(self):
        try:self.barrier.wait()
        except threading.BrokenBarrierError:pass
        super().do_GET()
    def do_PUT(self):
        with self.lock:type(self).puts+=1
        super().do_PUT()
def main():
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),RaceHandler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        with tempfile.TemporaryDirectory() as d:
            env={**os.environ,'OWL_DB':str(Path(d)/'db.sqlite'),'OWL_API':f'http://127.0.0.1:{server.server_port}'}
            subprocess.run([sys.executable,str(ROOT/'worker.py')],env={**env,'OWL_API':'http://127.0.0.1:1'},capture_output=True)
            processes=[subprocess.Popen([sys.executable,str(ROOT/'worker.py')],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True) for _ in range(2)]
            results=[p.communicate(timeout=15) for p in processes]
            print('process_exit_codes:',[p.returncode for p in processes])
            print('remote_PUT_requests:',RaceHandler.puts)
            print('mock_unique_effects:',RaceHandler.writes)
            assert RaceHandler.puts==2 and RaceHandler.writes==1
            print('KNOWN DEFECT: two workers race to remote PUT; mock idempotency masks duplicate attempts')
    finally:server.shutdown();server.server_close()
if __name__=='__main__':main()
