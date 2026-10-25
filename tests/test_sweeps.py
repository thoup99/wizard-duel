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

@pytest.mark.parametrize('path',[[[0,0],[2,0]]])
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

@pytest.mark.parametrize('spell',['bolt','ward','empower','hex'])
@pytest.mark.parametrize('error',[-.35,0,.35])
def test_beginner_curves_and_35_percent_return_overshoot(spell,error):
    forward=sweep(spell,18)[1];side=np.array([-forward[1],forward[0]])
    outward=np.array([forward*t+side*(error*np.sin(np.pi*t)) for t in np.linspace(0,1,30)])
    path=np.vstack([outward,forward*-.35])
    result=recognize(path_to_rows(path,duration=.9,jitter=.2,seed=42))
    assert result['spell']==spell,result

@pytest.mark.parametrize('spell',['bolt','ward','empower','hex'])
def test_larger_return_does_not_cast_opposite_spell(spell):
    forward=sweep(spell,15)[1]
    result=recognize(path_to_rows([[0,0],forward,-forward*1.2],duration=.9))
    assert result['spell'] in (spell,None)
    assert result['top_guess']==spell

@pytest.mark.parametrize('degrees',[40,-40])
def test_off_angle_sweep_is_accepted(degrees):
    # Test projected directions directly; projection itself has separate grip tests.
    from backend.app import gestures
    from unittest.mock import patch
    t=np.linspace(0,.8,41);angle=np.deg2rad(degrees)
    path=np.column_stack([t/.8*20*np.cos(angle),t/.8*20*np.sin(angle)])
    with patch.object(gestures,'clean_project',return_value=(t,path)):
        assert recognize(path_to_rows(sweep('bolt')))['spell']=='bolt'

def test_exact_diagonal_is_ambiguous():
    from backend.app import gestures
    from unittest.mock import patch
    t=np.linspace(0,.8,41);path=np.column_stack([t*20,t*20])
    with patch.object(gestures,'clean_project',return_value=(t,path)):
        assert recognize(path_to_rows(sweep('bolt')))['reason']=='ambiguous'

def test_old_config_inherits_tolerance(tmp_path):
    import json
    c=load_config();del c['sweep_error_tolerance'];p=tmp_path/'config.json';p.write_text(json.dumps(c))
    assert load_config(p)['sweep_error_tolerance']==.35

@pytest.mark.parametrize('value',[-.1,0,.5,True,float('nan')])
def test_invalid_sweep_tolerance_is_rejected(tmp_path,value):
    import json
    c=load_config();c['sweep_error_tolerance']=value;p=tmp_path/'config.json';p.write_text(json.dumps(c))
    with pytest.raises(ValueError):load_config(p)

def test_sweep_score_uses_35_percent_tolerance_not_legacy_shape_threshold():
    rows=path_to_rows([[0,0],[6,12],[14,-2],[20,6]],duration=1)
    config=dict(load_config(),accept_score=.9999)
    result=recognize(rows,config=config)
    assert result['spell']=='bolt' and .65<result['score']<.95,result
    # Crossing the reported fit threshold changes acceptance, not spell identity.
    stricter=dict(config,sweep_error_tolerance=1-result['score']-.001)
    looser=dict(config,sweep_error_tolerance=1-result['score']+.001)
    assert recognize(rows,config=stricter)['outcome']=='fizzle'
    assert recognize(rows,config=looser)['spell']=='bolt'
