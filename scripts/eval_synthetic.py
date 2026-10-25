#!/usr/bin/env python3
import argparse,json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from backend.app.gestures import recognize,load_config
from scripts.synthetic_gestures import path_to_rows,ideal

def evaluate(count=1000):
    rng=np.random.default_rng(452);report={};timings=[];config=load_config()
    for spell in ['bolt','ward','empower','hex']:
        counts={k:0 for k in ['bolt','ward','empower','hex','rejected']}
        for i in range(count):
            extent=rng.uniform(20,40)*rng.uniform(.5,2);p=ideal(spell,extent,bool(i%2),rng.uniform(0,2*np.pi))
            p[:,0]=p[:,0]*rng.uniform(.8,1.2)+p[:,1]*rng.uniform(-.176,.176)
            rows=path_to_rows(p,duration=rng.uniform(.7,2.15),rate=int(rng.integers(30,101)),facing=rng.uniform(0,360),tilt=rng.uniform(-45,45),roll=rng.uniform(-180,180),jitter=rng.uniform(1,2),seed=i+10000*len(report),speed=rng.uniform(.7,1.4))
            t=time.perf_counter();result=recognize(rows,config=config);timings.append((time.perf_counter()-t)*1000);counts[result['spell'] or 'rejected']+=1
        report[spell]=dict(counts=counts,accuracy=counts[spell]/count,wrong=sum(v for k,v in counts.items() if k not in (spell,'rejected'))/count)
    rejected=0
    for i in range(count):
        p=rng.normal(0,1,(20,2)) if i%2 else rng.uniform(-30,30,(int(rng.integers(6,16)),2))
        result=recognize(path_to_rows(p,duration=rng.uniform(.3,2),jitter=.5,seed=i));rejected+=result['outcome']!='cast'
    report['negative_rejection']=rejected/count;report['latency_ms']={'p95':float(np.percentile(timings,95)),'max':max(timings)}
    report['passed']=all(report[s]['accuracy']>=.95 and report[s]['wrong']<=.02 for s in ['bolt','ward','empower','hex']) and report['negative_rejection']>=.9
    return report
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--count',type=int,default=1000);parser.add_argument('--output');a=parser.parse_args();result=evaluate(a.count);text=json.dumps(result,indent=2);print(text)
    if a.output:Path(a.output).write_text(text+'\n')
    sys.exit(0 if result['passed'] else 1)
