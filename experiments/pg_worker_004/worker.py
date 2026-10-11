import argparse,json,os
import psycopg
def main():
 p=argparse.ArgumentParser()
 p.add_argument('--submit');p.add_argument('--once',action='store_true')
 p.add_argument('--worker-id',default='worker-004');p.add_argument('--lease',type=int,default=2)
 p.add_argument('--crash',choices=['none','before_commit','after_commit'],default='none')
 a=p.parse_args()
 with psycopg.connect(os.environ['OWL_WORKER_DSN'],autocommit=True) as c:
  if a.submit:
   row=c.execute('select owl_test.submit(%s,%s::jsonb)',(a.submit,json.dumps({'value':a.submit}))).fetchone()
   print(json.dumps({'submitted':row[0]}),flush=True)
  if a.once:
   row=c.execute('select job_key,payload,fence from owl_test.claim(%s,%s)',(a.worker_id,a.lease)).fetchone()
   if row is None: print(json.dumps({'claimed':False}),flush=True);return
   key,payload,fence=row
   if a.crash=='before_commit':os._exit(17)
   result={'input':payload,'output':'ACK:'+key,'worker':a.worker_id}
   ok=c.execute('select owl_test.complete(%s,%s,%s,%s::jsonb)',(key,a.worker_id,fence,json.dumps(result))).fetchone()[0]
   if a.crash=='after_commit':os._exit(18)
   print(json.dumps({'job_key':key,'fence':fence,'committed':ok}),flush=True)
if __name__=='__main__':main()
