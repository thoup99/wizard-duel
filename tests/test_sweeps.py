import numpy as np
import pytest
from backend.app.gestures import recognize, load_config
from scripts.synthetic_gestures import path_to_rows, sweep

@pytest.mark.parametrize('spell',['bolt','ward','empower','hex'])
@pytest.mark.parametrize('duration',[.2,.5,1.5])
def test_default_sweeps_allow_short_slow_and_curved_motion(spell,duration):
    path=np.linspace(*sweep(spell,24),40)
    axis=1 if spell in ('bolt','ward') else 0
    path[:,axis]=4*np.sin(np.linspace(0,np.pi,40))
    result=recognize(path_to_rows(path,duration=duration,jitter=.3,facing=235,roll=35))
    assert result['spell']==spell,result

@pytest.mark.parametrize('path',[[[0,0],[25,25]],[[0,0],[-25,25]],[[0,0],[30,0],[0,0]],[[0,0],[2,0]]])
def test_diagonals_return_strokes_and_tiny_movements_do_not_cast(path):
    assert recognize(path_to_rows(path,duration=.6))['outcome']!='cast'

def test_reversing_sweep_casts_opposite_spell():
    assert load_config()['mode']=='flicks'
    assert recognize(path_to_rows(sweep('bolt')[::-1],duration=.5))['spell']=='ward'
