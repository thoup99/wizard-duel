"""Deterministic synthetic orientations; independent of recognizer projection."""
import numpy as np

def path_to_rows(path,duration=1.3,rate=60,facing=0.,tilt=20.,roll=0.,jitter=0.,seed=0,speed=1.):
    rng=np.random.default_rng(seed);path=np.array(path,dtype=float)
    distances=np.r_[0,np.cumsum(np.linalg.norm(np.diff(path,axis=0),axis=1))]
    n=max(10,int(duration*rate)+1);times=np.linspace(0,duration,n);progress=(times/duration)**speed
    xy=np.column_stack([np.interp(progress*distances[-1],distances,path[:,i]) for i in range(2)])
    if jitter:xy+=rng.normal(0,jitter,xy.shape)
    az,el=np.deg2rad([facing,tilt]);f=np.array([np.sin(az)*np.cos(el),np.cos(az)*np.cos(el),np.sin(el)])
    right=np.array([np.cos(az),-np.sin(az),0]);up=np.cross(right,f)
    p=f+np.tan(np.deg2rad(xy[:,0,None]))*right+np.tan(np.deg2rad(xy[:,1,None]))*up
    p/=np.linalg.norm(p,axis=1,keepdims=True)
    alpha=np.rad2deg(np.arctan2(-p[:,0],p[:,1]))%360;beta=np.rad2deg(np.arcsin(np.clip(p[:,2],-1,1)))
    return np.column_stack([times,alpha,beta,np.full(n,roll),np.zeros((n,3))]).tolist()

def ideal(spell,extent=30,reverse=False,start=0):
    shapes={'bolt':[[-.5,.5],[.5,.5],[-.5,-.5],[.5,-.5]],'empower':[[-.5,-.4167],[0,.4167],[.5,-.4167]],'hex':[[-.5,.4167],[0,-.4167],[.5,.4167]]}
    if spell=='ward':
        a=np.linspace(start,start+2*np.pi,200);p=np.column_stack([np.cos(a),np.sin(a)])*.5
    else:p=np.array(shapes[spell],float)
    p*=extent
    return p[::-1] if reverse else p
