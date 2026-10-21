"""Synthetic clickstream ingestion with transactional daily checkpoints."""
import argparse
import os
import subprocess
import sys
from datetime import date,timedelta
from pathlib import Path
import psycopg
LOCK=7249103
ROOT=Path(__file__).resolve().parent

def connect():
    return psycopg.connect(host=os.getenv('PGHOST','127.0.0.1'),port=os.getenv('PGPORT','15432'),
                          dbname=os.getenv('PGDATABASE','demo'),user=os.getenv('PGUSER','demo'),
                          password=os.getenv('PGPASSWORD','demo'),autocommit=True)
def rows(day, count=4):
    visits=[];hits=[]
    for i in range(1,count+1):
        vid=day.toordinal()*100+i
        visits.append((vid,day,'mobile' if i%2 else 'desktop'))
        for j,(event,referrer) in enumerate([('page_view','organic'),('cart_entry','product'),('cart_entry','search'),('order','cart')]):
            if event=='order' and i%2: continue
            hits.append((vid*10+j,vid,day,j,event,referrer))
    return visits,hits

def setup(c):
    c.execute('CREATE SCHEMA IF NOT EXISTS raw')
    c.execute('CREATE TABLE IF NOT EXISTS raw.visits(visit_id bigint PRIMARY KEY,day date NOT NULL,device text NOT NULL)')
    c.execute('CREATE TABLE IF NOT EXISTS raw.hits(hit_id bigint PRIMARY KEY,visit_id bigint REFERENCES raw.visits,day date NOT NULL,seq int,event text,referrer text)')
    c.execute('CREATE TABLE IF NOT EXISTS raw.checkpoints(batch text,day date,PRIMARY KEY(batch,day))')

def load(c,start,end,batch,resume=False,fail_after=None,count=4):
    setup(c);day=start;completed=0
    while day<=end:
        if resume and c.execute('SELECT 1 FROM raw.checkpoints WHERE batch=%s AND day=%s',(batch,day)).fetchone():
            day+=timedelta(days=1);continue
        v,h=rows(day,count)
        with c.transaction():
            c.execute('DELETE FROM raw.hits WHERE day=%s',(day,))
            c.execute('DELETE FROM raw.visits WHERE day=%s',(day,))
            with c.cursor() as cur:
                cur.executemany('INSERT INTO raw.visits VALUES (%s,%s,%s)',v)
                cur.executemany('INSERT INTO raw.hits VALUES (%s,%s,%s,%s,%s,%s)',h)
            c.execute('INSERT INTO raw.checkpoints VALUES (%s,%s) ON CONFLICT DO NOTHING',(batch,day))
        completed+=1
        if completed==fail_after:raise RuntimeError('simulated interruption after committed day')
        day+=timedelta(days=1)

def run(start,end,batch='demo',resume=False,fail_after=None,count=4):
    if start>end:raise ValueError('start must not exceed end')
    with connect() as c:
        if not c.execute('SELECT pg_try_advisory_lock(%s)',(LOCK,)).fetchone()[0]:raise RuntimeError('another pipeline is running')
        try:
            load(c,start,end,batch,resume,fail_after,count)
            env=dict(os.environ,DBT_SEND_ANONYMOUS_USAGE_STATS='false')
            import json
            subprocess.run([str(Path(sys.executable).parent/'dbt'),'build','--project-dir',str(ROOT/'dbt'),'--profiles-dir',str(ROOT/'dbt'),'--vars',json.dumps({'start':str(start),'end':str(end)})],check=True,env=env)
        finally:c.execute('SELECT pg_advisory_unlock(%s)',(LOCK,))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--start',type=date.fromisoformat,default=date(2026,1,1));p.add_argument('--end',type=date.fromisoformat,default=date(2026,1,3));p.add_argument('--batch',default='demo');p.add_argument('--resume',action='store_true');p.add_argument('--fail-after',type=int);a=p.parse_args()
    run(a.start,a.end,a.batch,a.resume,a.fail_after)
if __name__=='__main__':main()
