import numpy as np
import pytest
from backend.app.gestures import recognize,validate_samples,project,load_config
from scripts.synthetic_gestures import path_to_rows,ideal

def sample(spell):
    return path_to_rows([[0,0],[0,0]] if spell=='idle' else ideal(spell))

@pytest.mark.parametrize('spell',['bolt','ward','empower','hex'])
def test_synthetic_signatures(spell):assert recognize(sample(spell))['spell']==spell

def test_idle_no_cast():assert recognize(sample('idle'))['outcome']=='no_cast'

@pytest.mark.parametrize('rows',[[],[[0]*7]*5,[[float('nan')]*7]*5,[[0,1]]*10])
def test_bad_data_rejected(rows):
    with pytest.raises(ValueError):validate_samples(rows)

@pytest.mark.parametrize('spell',['bolt','ward','empower','hex'])
@pytest.mark.parametrize('facing,tilt,roll',[(0,0,0),(180,30,45),(359,-30,120),(80,45,-90)])
def test_facing_grip_roll_and_reverse(spell,facing,tilt,roll):
    for reverse in [False,True]:
        r=recognize(path_to_rows(ideal(spell,30,reverse),facing=facing,tilt=tilt,roll=roll));assert r['spell']==spell,r

def test_caret_never_becomes_v():
    assert recognize(sample('empower'))['spell']!='hex';assert recognize(sample('hex'))['spell']!='empower'

def test_schema_rejects_old_clients():
    with pytest.raises(ValueError):recognize(sample('bolt'),schema_version=1)

def test_cleaning_sorts_and_deduplicates():
    rows=sample('bolt');assert recognize(rows[::-1]+rows[10:14])['spell']=='bolt'

def test_small_short_and_slow_reason_codes():
    assert recognize(path_to_rows(ideal('bolt',2)))['reason']=='too_small'
    assert recognize(path_to_rows(ideal('bolt'),duration=.15))['reason']=='too_short'
    assert recognize(path_to_rows([[-5,0],[5,0]],duration=2.3))['reason']=='too_slow'

def test_flick_fallback():
    c=load_config();c['mode']='flicks'
    for end,spell in [([25,0],'bolt'),([-25,0],'ward'),([0,25],'empower'),([0,-25],'hex')]:
        assert recognize(path_to_rows([[0,0],end],duration=.5),config=c)['spell']==spell
