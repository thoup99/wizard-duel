"""Seeded equal-policy combat simulation; timing estimates, not human playtests."""
import json,random,statistics,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.app.engine import Room,SPELLS

def simulate(seed):
    rng=random.Random(seed);r=Room('TEST',0);players=[r.add(str(i),0) for i in range(4)]
    for p in players:p.ready=True
    r.start(players[0],0);next_action={p.id:3+rng.uniform(0,1) for p in players}
    for frame in range(1,6001):
        now=frame*.1;r.tick(now)
        if r.phase=='MATCH_END':return now,r.winner,r.round_number
        if r.phase!='DUEL':continue
        order=players.copy();rng.shuffle(order)
        for p in order:
            if p.hp<=0 or now<next_action[p.id] or now<p.cooldown_until:continue
            next_action[p.id]=now+rng.uniform(1.5,3)
            if rng.random()<.1:
                r.cast(p,None,0,now);continue
            foes=[x for x in players if x.team!=p.team and x.hp>0]
            allies=[x for x in players if x.team==p.team and x.hp>0]
            if not foes:continue
            target=min(foes,key=lambda x:x.hp)
            choice=rng.choices(['bolt','ward','empower','hex'],[.65,.15,.1,.1])[0]
            if choice=='ward':
                target=min(allies,key=lambda x:x.hp)
                if 'ward' in target.effects:choice='bolt';target=min(foes,key=lambda x:x.hp)
            if choice=='empower' and ('empower' in p.effects or len(allies)<2):choice='bolt'
            if choice=='hex' and ('hex' in target.effects or target.mana<20):choice='bolt'
            if p.mana>=SPELLS[choice]['cost']:r.cast(p,choice,1,now,target.id)
    return 600,None,r.round_number

def evaluate(count=200):
    results=[simulate(i) for i in range(count)];times=sorted(r[0] for r in results)
    return dict(matches=count,mean_seconds=round(statistics.mean(times),1),median_seconds=round(statistics.median(times),1),p10_seconds=times[int(.1*count)],p90_seconds=times[int(.9*count)],team_wins=[sum(r[1]==t for r in results) for t in (0,1)],unfinished=sum(r[1] is None for r in results))
if __name__=='__main__':
    report=evaluate()
    report['passed']=150<=report['mean_seconds']<=210 and report['unfinished']==0 and min(report['team_wins'])>=.35*report['matches']
    print(json.dumps(report,indent=2))
    if len(sys.argv)>1:Path(sys.argv[1]).write_text(json.dumps(report,indent=2)+'\n')
    sys.exit(0 if report['passed'] else 1)
