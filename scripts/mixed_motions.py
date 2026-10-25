"""Independent motion fixtures for the four distinct controls (world y is up)."""
import numpy as np

def motion(spell,extent=24,reverse=False,start=0):
    if spell=='ward':
        a=np.linspace(start,start+2*np.pi,100)
        p=np.column_stack([np.cos(a),np.sin(a)])*.5
    else:p=np.array({'bolt':[[0,0],[1,0]],'empower':[[0,0],[0,1]],'hex':[[-.5,.35],[.5,.35],[-.5,-.35],[.5,-.35]]}[spell],float)
    p*=extent
    return p[::-1] if reverse else p
