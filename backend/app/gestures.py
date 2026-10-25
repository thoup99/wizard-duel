"""Orientation schema v2: [seconds, alpha, beta, gamma, rx, ry, rz].

Only the fused pointing direction is matched; gyro channels are diagnostic.
Euler angles are never subtracted or interpolated. Shape up remains world up.
"""
import json
from functools import lru_cache
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / 'backend/config/gestures.json'
SHAPES = json.loads((ROOT / 'frontend/spells.json').read_text())
DEFAULTS = dict(mode='flicks', accept_score=.75, min_margin=.05, resample_points=64,
                sample_hz=50, min_extent_deg=8, max_extent_deg=120, min_stroke_ms=250,
                max_window_ms=2500, min_peak_speed_dps=40, fizzle_cooldown_s=.25)
HINTS = dict(too_small='Draw it bigger: aim for 20–40 degrees of wrist movement.',
             too_short='Hold CAST while you finish the whole shape.',
             too_slow='Draw with one steady, deliberate motion.',
             ambiguous='Make the corners clearer and keep up pointing up.',
             no_match='Trace the ghost shape in one continuous stroke.')

def load_config(path=DEFAULT_CONFIG):
    c = json.loads(Path(path).read_text())
    if set(c) != set(DEFAULTS) or c['mode'] not in ('shapes', 'flicks'):
        raise ValueError('Use the schema-v2 config keys and mode shapes or flicks.')
    for key, value in c.items():
        if key != 'mode' and (isinstance(value, bool) or not isinstance(value, (int,float)) or not np.isfinite(value) or value <= 0):
            raise ValueError(f'Invalid threshold: {key}')
    if not (0 < c['accept_score'] <= 1 and 0 < c['min_margin'] < 1
            and 16 <= c['resample_points'] <= 128 and int(c['resample_points']) == c['resample_points']
            and 20 <= c['sample_hz'] <= 100 and c['max_window_ms'] <= 2500
            and c['min_stroke_ms'] < c['max_window_ms']
            and c['min_extent_deg'] < c['max_extent_deg'] <= 160):
        raise ValueError('Gesture configuration is outside supported ranges.')
    return c

def validate_samples(samples):
    try: a = np.asarray(samples, dtype=float)
    except (TypeError, ValueError): raise ValueError('Samples must be numeric rows.') from None
    if a.ndim != 2 or a.shape[1] != 7 or not 2 <= len(a) <= 320:
        raise ValueError('Supply 2–320 rows of seven orientation values.')
    if not np.isfinite(a).all() or np.abs(a[:,1:]).max() > 5000:
        raise ValueError('Sensor values must be finite and in range.')
    a = a[np.argsort(a[:,0], kind='stable')]
    a = a[np.r_[True, np.diff(a[:,0]) > 1e-6]]
    if len(a) < 2 or not 0 < a[-1,0]-a[0,0] <= 2.501:
        raise ValueError('Supply distinct times covering no more than 2.5 seconds.')
    a = a.copy();a[:,0] -= a[0,0]
    return a

def unit(v):
    length = np.linalg.norm(v,axis=-1,keepdims=True)
    return v / np.maximum(length,1e-12)

def orientation_axes(rows):
    """Columns of Rz(alpha) Rx(beta) Ry(gamma), W3C intrinsic Z-X'-Y''."""
    a,b,g = np.deg2rad(np.asarray(rows)[:,1:4]).T
    ca,sa,cb,sb,cg,sg = np.cos(a),np.sin(a),np.cos(b),np.sin(b),np.cos(g),np.sin(g)
    pointing = np.column_stack((-sa*cb,ca*cb,sb))
    right = np.column_stack((ca*cg-sa*sb*sg,sa*cg+ca*sb*sg,-cb*sg))
    return pointing,right

def project_vectors(pointing, right):
    f = unit(pointing.mean(axis=0))
    if np.linalg.norm(f) < .5: raise ValueError('Wand direction is unstable.')
    up = np.array([0.,0.,1.]);u = up-f*np.dot(up,f)
    if np.linalg.norm(u) < np.sin(np.deg2rad(20)):
        r = right.mean(axis=0);r = unit(r-f*np.dot(r,f))
        if np.linalg.norm(r) < .5:
            axis=np.array([1.,0.,0.]);r=unit(axis-f*np.dot(axis,f))
        u = unit(np.cross(r,f))
    else:
        u = unit(u);r = unit(np.cross(f,u))
    forward = pointing@f
    return np.rad2deg(np.column_stack((np.arctan2(pointing@r,forward),np.arctan2(pointing@u,forward))))

def project(rows):
    """Raw projection used by the browser parity vectors (no cleaning)."""
    return project_vectors(*orientation_axes(np.asarray(rows,dtype=float)))

def smooth(values, size=5):
    pad=size//2
    return np.column_stack([np.convolve(np.pad(values[:,i],(pad,pad),mode='edge'),np.ones(size)/size,mode='valid') for i in range(values.shape[1])])

def clean_project(a,c):
    p,r=orientation_axes(a)
    times=np.arange(0,a[-1,0]+1e-6,1/c['sample_hz'])
    # Interpolate vectors, not Euler angles: safe across heading wraps and beta=90.
    p=unit(smooth(np.column_stack([np.interp(times,a[:,0],p[:,i]) for i in range(3)])))
    r=unit(smooth(np.column_stack([np.interp(times,a[:,0],r[:,i]) for i in range(3)])))
    return times, project_vectors(p,r)

def resample(path, count=64):
    path=np.asarray(path,dtype=float)
    lengths=np.r_[0,np.cumsum(np.linalg.norm(np.diff(path,axis=0),axis=1))]
    keep=np.r_[True,np.diff(lengths)>1e-8];path,lengths=path[keep],lengths[keep]
    if len(path)<2:return np.repeat(path[:1],count,axis=0)
    distances=np.linspace(0,lengths[-1],count)
    return np.column_stack([np.interp(distances,lengths,path[:,i]) for i in range(2)])

def normalize(path,count=64):
    p=resample(path,count);extent=np.ptp(p,axis=0).max()
    return (p-p.mean(axis=0))/max(extent,1e-8)

def shape_points(shape):
    if shape['shape']=='circle':
        angles=np.linspace(np.pi/2,np.pi/2-2*np.pi,129)
        return np.column_stack((np.cos(angles),np.sin(angles)))*shape['radius']
    p=np.array(shape['points'],dtype=float);p[:,1]*=-1
    return p

@lru_cache(maxsize=8)
def templates(count):
    result={}
    for shape in SHAPES:
        p=resample(shape_points(shape),count)
        variants=[]
        for width,skew in [(1,0),(.8,0),(1.2,0),(1,.176),(1,-.176),(.8,.176),(1.2,-.176)]:
            q=p.copy();q[:,0]=q[:,0]*width+q[:,1]*skew
            starts=range(0,count-1,max(1,(count-1)//8)) if shape['id']=='ward' else [0]
            for start in starts:
                stroke=np.vstack((np.roll(q[:-1],-start,axis=0),np.roll(q[:-1],-start,axis=0)[:1])) if shape['id']=='ward' else q
                variants.extend([normalize(stroke,count),normalize(stroke[::-1],count)])
        result[shape['id']]=np.array(variants)
    return result

def simplify(path,epsilon=.10):
    if len(path)<3:return path
    start,end=path[0],path[-1];line=end-start
    if np.linalg.norm(line)<1e-9:dist=np.linalg.norm(path-start,axis=1)
    else:
        t=np.clip(((path-start)@line)/(line@line),0,1)
        dist=np.linalg.norm(path-(start+t[:,None]*line),axis=1)
    index=int(np.argmax(dist))
    if dist[index]<=epsilon:return np.array([start,end])
    return np.vstack((simplify(path[:index+1],epsilon)[:-1],simplify(path[index:],epsilon)))

def geometry(path):
    length=np.linalg.norm(np.diff(path,axis=0),axis=1).sum()
    closure=np.linalg.norm(path[-1]-path[0])/max(np.ptp(path,axis=0).max(),1e-8)
    simple=simplify(path,.11)
    segments=np.diff(simple,axis=0)
    angles=np.unwrap(np.arctan2(segments[:,1],segments[:,0]))
    turns=np.rad2deg(np.diff(angles))
    corners=int(np.count_nonzero(np.abs(turns)>45))
    turn=float(abs(turns.sum()))
    return closure,corners,turn,length

def match_path(path,c):
    count=int(c['resample_points']);p=normalize(path,count)
    closure,corners,turn,length=geometry(p)
    scores={}
    for spell,group in templates(count).items():
        distance=np.linalg.norm(group-p[None,:,:],axis=2).mean(axis=1).min()
        score=max(0.,1-float(distance)/(2**.5/2))
        if spell=='ward':
            if closure>.4 or not 245<=turn<=470:score=0.
        elif closure<.35:score=0.
        else:
            expected=2 if spell=='bolt' else 1
            score-=min(.35,.12*abs(corners-expected))
        scores[spell]=max(0.,score)
    ranked=sorted(scores,key=scores.get,reverse=True)
    best,second=ranked[:2]
    return best,scores[best],scores[best]-scores[second],scores

def recognize(samples, platform='other', config=None, schema_version=2):
    if schema_version!=2:raise ValueError('This server needs orientation schema_version 2. Refresh the page.')
    c=config or load_config();a=validate_samples(samples)
    result=dict(outcome='no_cast',spell=None,score=0.,top_guess=None,reason=None,path=[],scores={})
    def reject(reason,outcome='no_cast'):
        hint=HINTS[reason]
        if c['mode']=='flicks':
            hint=dict(too_small='Aim the top of your phone a little farther in the arrow direction.', too_short='Hold CAST, make one short sweep, then release.', too_slow='Make one comfortable sweep in the arrow direction.', ambiguous='Follow one arrow: right, left, up or down.', no_match='Sweep once in the arrow direction. Release before returning to the start.')[reason]
        result.update(reason=reason,outcome=outcome,hint=hint);return result
    minimum_ms=min(c['min_stroke_ms'],150) if c['mode']=='flicks' else c['min_stroke_ms']
    if a[-1,0]*1000<minimum_ms:return reject('too_short')
    if a[-1,0]*1000>c['max_window_ms']:return reject('no_match','fizzle')
    try:times,path=clean_project(a,c)
    except ValueError:return reject('no_match','fizzle')
    result['path']=np.round(path,3).tolist()
    extent=np.ptp(path,axis=0).max()
    if extent<c['min_extent_deg']:return reject('too_small')
    if extent>c['max_extent_deg']:return reject('no_match','fizzle')
    speeds=np.linalg.norm(np.diff(path,axis=0),axis=1)*c['sample_hz']
    minimum_speed=min(c['min_peak_speed_dps'],15) if c['mode']=='flicks' else c['min_peak_speed_dps']
    if speeds.max(initial=0)<minimum_speed:return reject('too_slow')
    active=np.flatnonzero(speeds>max(6.,speeds.max()*.08))
    if len(active):
        start=max(0,active[0]-2);end=min(len(path),active[-1]+4)
        path=path[start:end];times=times[start:end]
    if (times[-1]-times[0])*1000<minimum_ms:return reject('too_short')
    result['path']=np.round(path,3).tolist()
    if c['mode']=='flicks':
        delta=path[-1]-path[0];axis=int(np.argmax(abs(delta)))
        # Coarse arc length ignores sensor jitter while retaining deliberate reversals.
        coarse=np.column_stack([np.interp(np.linspace(0,len(path)-1,12),np.arange(len(path)),path[:,i]) for i in range(2)])
        length=np.linalg.norm(np.diff(coarse,axis=0),axis=1).sum()
        straight=np.linalg.norm(delta)/max(length,1e-8)
        if abs(delta[axis])<c['min_extent_deg'] or straight<.6:return reject('no_match','fizzle')
        if abs(delta[axis])<1.25*abs(delta[1-axis]):return reject('ambiguous','fizzle')
        spell=('bolt' if delta[0]>0 else 'ward') if axis==0 else ('empower' if delta[1]>0 else 'hex')
        score=min(1.,.75+.25*straight);margin=1.
    else:spell,score,margin,scores=match_path(path,c);result['scores']=scores
    result.update(score=round(score,4),top_guess=spell)
    if score<c['accept_score']:return reject('no_match','fizzle')
    if margin<c['min_margin']:return reject('ambiguous','fizzle')
    result.update(outcome='cast',spell=spell,hint='Spell recognized.',reason=None)
    return result
