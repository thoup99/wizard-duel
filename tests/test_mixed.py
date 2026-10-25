import numpy as np
import pytest
from backend.app.gestures import recognize,stabilize_horizontal,load_config
from scripts.synthetic_gestures import path_to_rows
from scripts.mixed_motions import motion

@pytest.mark.parametrize('spell',['bolt','ward','hex','empower'])
@pytest.mark.parametrize('facing,tilt,roll',[(0,10,0),(180,25,45),(350,-20,-60)])
def test_distinct_motions(spell,facing,tilt,roll):
    r=recognize(path_to_rows(motion(spell),facing=facing,tilt=tilt,roll=roll,jitter=.25))
    assert r['spell']==spell,r

@pytest.mark.parametrize('reverse',[False,True])
@pytest.mark.parametrize('start',[0,1,2,3,4,5])
@pytest.mark.parametrize('width',[.65,1.4])
def test_loose_circles_any_direction_start_and_oval(width,start,reverse):
    p=motion('ward',reverse=reverse,start=start);p[:,0]*=width
    r=recognize(path_to_rows(p,jitter=.3));assert r['spell']=='ward',r

@pytest.mark.parametrize('reverse',[False,True])
@pytest.mark.parametrize('width',[.7,1.3])
def test_loose_zigzag(width,reverse):
    p=motion('hex',reverse=reverse);p[:,0]*=width;p[:,1]+=[1,-2,2,-1]
    r=recognize(path_to_rows(p,jitter=.3));assert r['spell']=='hex',r

def test_horizontal_wobble_damped_without_flattening_shapes():
    p=np.array([[0,0],[10,2],[20,-3],[30,1]],float)
    q=stabilize_horizontal(p)
    np.testing.assert_allclose(q[:,0],p[:,0]);np.testing.assert_allclose(q[:,1],p[:,1]*.55)
    for spell in ['ward','hex','empower']:
        p=motion(spell);np.testing.assert_allclose(stabilize_horizontal(p),p)

def test_bolt_with_vertical_twitches():
    p=np.column_stack([np.linspace(0,24,60),3*np.sin(np.linspace(0,5*np.pi,60))])
    r=recognize(path_to_rows(p,jitter=.2));assert r['spell']=='bolt',r

@pytest.mark.parametrize('spell',['bolt','empower'])
def test_directional_return_is_not_a_circle_or_hex(spell):
    p=motion(spell);r=recognize(path_to_rows(np.vstack([p,-p[-1]*.2])))
    assert r['spell']==spell,r

@pytest.mark.parametrize('p',[[[0,0],[-20,0]],[[0,0],[0,-20]],[[0,0],[2,0]],[[0,0],[20,0],[-20,0],[20,0],[-20,0]]])
def test_old_left_down_and_shaking_do_not_cast(p):
    assert recognize(path_to_rows(p))['outcome']!='cast'

def test_settings_and_recording_schema(client):
    settings=client.get('/api/settings').json()
    assert settings['gesture_mode']=='mixed'
    assert 'circle' in settings['spells']['ward']['gesture']
    from backend.app.main import Sample
    assert Sample(label='ward',platform='other',samples=path_to_rows(motion('ward')),mode='mixed').mode=='mixed'

from test_api import client

def test_curved_upward_flick_with_return_is_still_empower():
    t=np.linspace(0,1,40)
    p=np.column_stack([6*np.sin(t*np.pi),24*t])
    r=recognize(path_to_rows(np.vstack([p,[0,-4.8]]),jitter=.3))
    assert r['spell']=='empower',r
