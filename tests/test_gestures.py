import numpy as np
import pytest
from backend.app.gestures import recognize, validate_samples

def sample(spell):
    t=np.arange(0,1.01,.02);data=np.zeros((len(t),7));data[:,0]=t
    if spell=='bolt':data[:,2]=18*np.exp(-((t-.18)/.05)**2)-9*np.exp(-((t-.32)/.05)**2)
    elif spell=='ward':data[:,4]=130*np.sin(2*np.pi*t);data[:,6]=130*np.cos(2*np.pi*t)
    elif spell=='empower':data[:,4]=130*np.sin(np.pi*t)
    elif spell=='hex':data[:,6]=220*np.sin(8*np.pi*t)
    return data.tolist()

@pytest.mark.parametrize('spell',['bolt','ward','empower','hex'])
def test_synthetic_signatures(spell):assert recognize(sample(spell))[0]==spell

def test_idle_fizzles():assert recognize(sample('idle'))==(None,0)

@pytest.mark.parametrize('rows',[[],[[0]*7]*5,[[float('nan')]*7]*5,[[0,1]]*10])
def test_bad_data_rejected(rows):
    with pytest.raises(ValueError):validate_samples(rows)

def test_high_frequency_noise_not_empower():
    rows=np.array(sample('empower'));rows[:,4]=200*np.sin(30*np.pi*rows[:,0]);assert recognize(rows.tolist())[0]!='empower'
