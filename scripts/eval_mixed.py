"""Noisy, independent trajectories for the mixed spellbook; no phone accuracy claim."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from backend.app.gestures import recognize
from scripts.synthetic_gestures import path_to_rows
from scripts.mixed_motions import motion

def evaluate(count=400):
    rng=np.random.default_rng(9042);report={}
    for spell in ['bolt','ward','hex','empower']:
        counts=dict(correct=0,wrong=0,rejected=0,total=count)
        for i in range(count):
            p=motion(spell,rng.uniform(16,36),reverse=bool(i%2) if spell in ('ward','hex') else False,start=rng.uniform(0,2*np.pi))
            p[:,0]*=rng.uniform(.75,1.3);p[:,0]+=p[:,1]*rng.uniform(-.15,.15)
            if spell in ('bolt','empower'):
                t=np.linspace(0,1,40);end=p[-1];side=np.array([-end[1],end[0]])
                p=t[:,None]*end+np.sin(t*np.pi)[:,None]*side*rng.uniform(-.30,.30)
                if i%2:p=np.vstack([p,-end*.2])
            rows=path_to_rows(p,duration=rng.uniform(.65,1.8),rate=int(rng.choice([30,60,100])),facing=rng.uniform(0,360),tilt=rng.uniform(-30,30),roll=rng.uniform(-90,90),jitter=.4,seed=i)
            result=recognize(rows)
            counts['correct' if result['spell']==spell else 'wrong' if result['spell'] else 'rejected']+=1
        report[spell]=counts
    negatives=0
    for i in range(count):
        p=rng.normal(0,.5,(15,2)) if i%2 else rng.uniform(-25,25,(12,2))
        negatives+=recognize(path_to_rows(p,duration=1.2))['outcome']!='cast'
    report['negative_rejection']=negatives/count
    report['passed']=all(report[s]['correct']/count>=.95 and report[s]['wrong']/count<=.02 for s in ['bolt','ward','hex','empower']) and negatives/count>=.9
    return report
if __name__=='__main__':
    report=evaluate();print(json.dumps(report,indent=2))
    if len(sys.argv)>1:Path(sys.argv[1]).write_text(json.dumps(report,indent=2)+'\n')
    sys.exit(0 if report['passed'] else 1)
