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

@pytest.mark.parametrize('path',[[[0,0],[25,25]],[[0,0],[-25,25]],[[0,0],[2,0]]])
def test_diagonals_and_tiny_movements_do_not_cast(path):
    assert recognize(path_to_rows(path,duration=.6))['outcome']!='cast'

def test_reversing_sweep_casts_opposite_spell():
    assert load_config()['mode']=='flicks'
    assert recognize(path_to_rows(sweep('bolt')[::-1],duration=.5))['spell']=='ward'

@pytest.mark.parametrize('spell',['bolt','ward','empower','hex'])
@pytest.mark.parametrize('extent,duration',[(7,.2),(7,.8),(15,.4),(30,1.2)])
def test_outward_sweep_survives_return_to_start(spell,extent,duration):
    path=np.vstack([sweep(spell,extent),[0,0]])
    result=recognize(path_to_rows(path,duration=duration,jitter=.15))
    assert result['spell']==spell,result

@pytest.mark.parametrize('spell',['bolt','ward','empower','hex'])
def test_small_slow_wrist_sweeps(spell):
    assert recognize(path_to_rows(sweep(spell,6),duration=.6))['spell']==spell

def test_repeated_shaking_is_not_a_spell():
    path=[[0,0],[20,0],[-20,0],[20,0],[-20,0],[0,0]]
    assert recognize(path_to_rows(path,duration=1.5))['outcome']!='cast'
