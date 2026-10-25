import json
from pathlib import Path
import pytest
from backend.app.engine import Room,TEAM_NAMES
from backend.app.gestures import recognize,project,load_config
from backend.app import main
from test_api import client,receive
from test_gestures import sample

def test_team_names_shuffle_unique_until_deck_exhausted():
    r=Room('TEST',0);p=r.add('A',0);seen=set(r.team_names)
    for _ in range(len(TEAM_NAMES)-2):
        r.shuffle_team_name(p,0);assert r.team_names[0] not in seen;seen.add(r.team_names[0]);assert len(set(r.team_names))==2
    for _ in range(50):r.shuffle_team_name(p,0);assert len(set(r.team_names))==2

def test_shuffle_permissions_and_rematch_persistence():
    r=Room('TEST',0);p=r.add('A',0)
    with pytest.raises(ValueError):r.shuffle_team_name(p,1)
    r.phase='DUEL'
    with pytest.raises(ValueError):r.shuffle_team_name(p,0)
    names=r.team_names.copy();r.phase='MATCH_END';r.rematch(p,1);assert r.team_names==names

def test_no_cast_has_no_penalty_and_fizzle_is_quarter_second():
    r=Room('TEST',0);p=r.add('A',0);r.begin_round(0)
    result=recognize(sample('idle'));r.cast(p,None,0,1,recognition=result)
    assert p.cooldown_until==0 and p.stats['attempts']==0 and p.mana==100
    result=dict(outcome='fizzle',score=.6,top_guess='hex',reason='no_match',path=[],hint='Try again')
    r.cast(p,None,.6,1,recognition=result);assert p.cooldown_until==1.25 and p.stats['attempts']==1 and p.mana==100

def test_ready_requires_three_server_confirmed_practice_casts(client):
    code=client.post('/api/rooms').json()['code']
    with client.websocket_connect('/ws/'+code) as ws:
        ws.send_json({'type':'join','name':'Practice Mage'});receive(ws,'joined')
        ws.send_json({'type':'ready','ready':True,'sensors_ok':True});assert 'three' in receive(ws,'error')['message']
        for i in range(3):
            ws.send_json({'type':'practice_cast','label':'bolt','schema_version':2,'samples':sample('bolt')})
            result=receive(ws,'practice_result');assert result['success'] and result['practice_successes']==i+1
        ws.send_json({'type':'ready','ready':True,'sensors_ok':True});ws.send_json({'type':'ping','t':1});receive(ws,'pong')
        assert next(iter(main.manager.rooms[code].players.values())).ready

def test_wrong_practice_spell_does_not_unlock(client):
    code=client.post('/api/rooms').json()['code']
    with client.websocket_connect('/ws/'+code) as ws:
        ws.send_json({'type':'join','name':'Mage'});receive(ws,'joined')
        ws.send_json({'type':'practice_cast','label':'ward','schema_version':2,'samples':sample('bolt')})
        r=receive(ws,'practice_result');assert not r['success'] and r['practice_successes']==0

def test_spectator_cannot_ready_cast_practice_or_shuffle(client):
    code=client.post('/api/rooms').json()['code']
    with client.websocket_connect('/ws/'+code) as ws:
        ws.send_json({'type':'watch'});receive(ws,'spectator')
        for kind in ['ready','cast','practice_cast','shuffle_team_name']:
            ws.send_json({'type':kind});assert 'Spectators' in receive(ws,'error')['message']

def test_underway_join_is_audience(client):
    code=client.post('/api/rooms').json()['code'];main.manager.rooms[code].phase='COUNTDOWN';main.manager.rooms[code].deadline=10**15
    with client.websocket_connect('/ws/'+code) as ws:
        ws.send_json({'type':'join','name':'Late Mage'});assert receive(ws,'spectator')

def test_practice_samples_are_opt_in(client,monkeypatch,tmp_path):
    monkeypatch.setattr(main,'SAMPLE_DIR',tmp_path);main.manager.practice_limits.clear()
    body=dict(type='practice_cast',schema_version=2,label='bolt',samples=sample('bolt'))
    assert client.post('/api/practice',json=body).json()['success'];assert not list(tmp_path.iterdir())
    body['save_sample']=True;assert client.post('/api/practice',json=body).json()['saved']
    saved=json.loads(next(tmp_path.iterdir()).read_text());assert saved['schema_version']==2 and saved['label']=='bolt' and 'name' not in saved

def test_shared_projection_vectors():
    import numpy as np
    vectors=json.loads((Path(__file__).parent/'fixtures/projection.json').read_text())
    for v in vectors:np.testing.assert_allclose(project(v['rows']),v['path'],atol=1e-7)

def test_invalid_config_is_rejected(tmp_path):
    c=load_config();c['resample_points']=1;p=tmp_path/'bad.json';p.write_text(json.dumps(c))
    with pytest.raises(ValueError):load_config(p)
