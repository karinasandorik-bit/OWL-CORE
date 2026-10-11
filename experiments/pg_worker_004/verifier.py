import argparse,json,os
import psycopg
p=argparse.ArgumentParser();p.add_argument('job_key');a=p.parse_args()
with psycopg.connect(os.environ['OWL_VERIFIER_DSN']) as c:
 row=c.execute('select job_key,state,fence,result,effect_count from owl_test.receipt(%s)',(a.job_key,)).fetchone()
assert row is not None,'missing job'
key,state,fence,result,effects=row
assert key==a.job_key and state=='done' and fence>=1 and effects==1
assert result['output']=='ACK:'+key and result['input']['value']==key
print(json.dumps({'verified':True,'job_key':key,'fence':fence,'effect_count':effects}))
