from contextlib import ExitStack
import json
import pytest
from fastapi.testclient import TestClient
from backend.app import main
from test_gestures import sample

def receive(ws, kind):
    for _ in range(40):
        m=ws.receive_json()
        if m['type']==kind:return m
    raise AssertionError('Message not received: '+kind)

@pytest.fixture
def client():
    main.manager.create_limits.clear()
    with TestClient(main.app) as c:yield c

def test_health_pages_and_config(client):
    assert client.get('/api/health').json()['game']=='Pocket Mages'
    for path in ('/','/phone','/arena','/debug','/record','/static/js/phone.js'):assert client.get(path).status_code==200
    assert client.get('/api/rooms/NOPE').status_code==404
    assert client.post('/api/gestures/reload').status_code==403
    assert client.get('/api/gestures/config').json()['sample_hz']==50

def test_four_players_spectator_and_authority(client):
    code=client.post('/api/rooms').json()['code']
    with ExitStack() as stack:
        sockets=[stack.enter_context(client.websocket_connect('/ws/'+code)) for _ in range(5)]
        for i,ws in enumerate(sockets[:4]):
            ws.send_json({'type':'join','name':str(i)});receive(ws,'joined')
        sockets[4].send_json({'type':'join','name':'spectator'});assert receive(sockets[4],'spectator')
        sockets[4].send_json({'type':'start'});assert 'Spectators' in receive(sockets[4],'error')['message']
        sockets[1].send_json({'type':'start'});assert 'host' in receive(sockets[1],'error')['message']
        for ws in sockets[:4]:
            for _ in range(3):
                ws.send_json({'type':'practice_cast','label':'bolt','schema_version':2,'samples':sample('bolt')});receive(ws,'practice_result')
            ws.send_json({'type':'ready','ready':True,'sensors_ok':True})
        for ws in sockets[:4]:ws.send_json({'type':'ping','t':1});receive(ws,'pong')
        sockets[0].send_json({'type':'start'})
        state=receive(sockets[0],'state')
        while state['phase']!='COUNTDOWN':state=receive(sockets[0],'state')
        assert len(state['players'])==4 and 'token' not in json.dumps(state)

def test_rejoin_preserves_player(client):
    code=client.post('/api/rooms').json()['code']
    with client.websocket_connect('/ws/'+code) as ws:
        ws.send_json({'type':'join','name':'Returning Mage'});joined=receive(ws,'joined')
    with client.websocket_connect('/ws/'+code) as ws:
        ws.send_json({'type':'join','name':'ignored','token':joined['token']});assert receive(ws,'joined')['player_id']==joined['player_id']

def test_invalid_payload_does_not_kill_room(client):
    code=client.post('/api/rooms').json()['code']
    with client.websocket_connect('/ws/'+code) as ws:
        ws.send_json({'type':'join','name':'Mage'});receive(ws,'joined')
        ws.send_text('{broken');assert receive(ws,'error')
        ws.send_json({'type':'set_team','team':9});assert receive(ws,'error')
        ws.send_json({'type':'ping','t':10});assert receive(ws,'pong')['t']==10

def test_sample_save_auth_and_validation(client,monkeypatch,tmp_path):
    monkeypatch.setattr(main,'ADMIN_TOKEN','test-secret');monkeypatch.setattr(main,'SAMPLE_DIR',tmp_path)
    payload={'label':'bolt','platform':'other','samples':[[i*.02,0,0,0,0,0,0] for i in range(20)]}
    assert client.post('/api/samples',json=payload).status_code==403
    r=client.post('/api/samples',json=payload,headers={'Authorization':'Bearer test-secret'})
    assert r.status_code==201 and (tmp_path/r.json()['filename']).exists()
