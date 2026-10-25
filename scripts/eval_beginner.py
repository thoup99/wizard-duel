"""Independent synthetic beginner motions; not a substitute for phone playtests."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from backend.app.gestures import recognize,load_config
from scripts.synthetic_gestures import path_to_rows

def evaluate(count=400):
    rng=np.random.default_rng(7365);report={}
    for spell,direction in {'bolt':[1,0],'ward':[-1,0],'empower':[0,1],'hex':[0,-1]}.items():
        correct=wrong=rejected=0
        for i in range(count):
            forward=np.array(direction)*rng.uniform(8,30);side=np.array([-forward[1],forward[0]])
            t=np.linspace(0,1,40)
            # Up to 35% sideways drift and 35% curved deviation, then a return
            # past the starting point by up to 35% of the outward movement.
            drift=rng.uniform(-.35,.35);curve=rng.uniform(-.35,.35)
            path=t[:,None]*forward+(drift*t+curve*np.sin(np.pi*t))[:,None]*side
            if i%2:path=np.vstack([path,-forward*rng.uniform(0,.35)])
            rows=path_to_rows(path,duration=rng.uniform(.4,1.7),rate=int(rng.choice([30,60,100])),facing=rng.uniform(0,360),tilt=rng.uniform(-30,30),roll=rng.uniform(-90,90),jitter=.2,seed=i,speed=rng.uniform(.8,1.2))
            result=recognize(rows,config=dict(load_config(),mode="flicks"))
            if result['spell']==spell:correct+=1
            elif result['spell']:wrong+=1
            else:rejected+=1
        report[spell]=dict(correct=correct,wrong=wrong,rejected=rejected,total=count)
    report['passed']=all(v['correct']/count>=.95 and v['wrong']/count<=.02 for v in report.values())
    return report
if __name__=='__main__':
    report=evaluate();print(json.dumps(report,indent=2))
    if len(sys.argv)>1:Path(sys.argv[1]).write_text(json.dumps(report,indent=2)+'\n')
    sys.exit(0 if report['passed'] else 1)
