"""Exercise full protocol and actual recognized gestures through four WebSockets."""
from contextlib import ExitStack
import time
from fastapi.testclient import TestClient
from backend.app import main
from test_api import receive
from test_gestures import sample


def test_complete_match_via_motion_casts_then_rematch():
    main.manager.create_limits.clear()
    with TestClient(main.app) as client, ExitStack() as stack:
        code=client.post('/api/rooms').json()['code']
        sockets=[stack.enter_context(client.websocket_connect('/ws/'+code)) for _ in range(4)]
        identities=[]
        for i,ws in enumerate(sockets):
            ws.send_json({'type':'join','name':f'Mage {i}'})
            identities.append(receive(ws,'joined')['player_id'])
            for _ in range(3):
                ws.send_json({'type':'practice_cast','label':'bolt','schema_version':2,'samples':sample('bolt')});receive(ws,'practice_result')
            ws.send_json({'type':'ready','ready':True,'sensors_ok':True})
            ws.send_json({'type':'ping','t':0});receive(ws,'pong')
        sockets[0].send_json({'type':'start'})
        sockets[0].send_json({'type':'ping','t':0});receive(sockets[0],'pong')
        room=main.manager.rooms[code]
        assert room.phase=='COUNTDOWN'
        # Advance the simulation clock rather than making CI wait a full round.
        for round_index in range(2):
            room.begin_round(time.monotonic())
            for target_id in identities[2:]:
                room.players[target_id].hp=20
                room.players[identities[0]].cooldown_until=0
                sockets[0].send_json({'type':'cast','schema_version':2,'platform':'other','target_id':target_id,'samples':sample('bolt')})
                sockets[0].send_json({'type':'ping','t':1});receive(sockets[0],'pong')
                assert room.projectiles
                room.tick(time.monotonic()+.5)
            assert room.wins[0]==round_index+1
        assert room.phase=='MATCH_END'
        assert room.players[identities[0]].stats['damage']==80
        assert room.players[identities[0]].stats['casts']==4
        assert room.mvp()==identities[0]
        sockets[0].send_json({'type':'rematch'})
        sockets[0].send_json({'type':'ping','t':2});receive(sockets[0],'pong')
        assert room.phase=='LOBBY' and len(room.players)==4


def test_production_rejects_development_casts():
    main.manager.create_limits.clear()
    with TestClient(main.app) as client:
        code=client.post('/api/rooms').json()['code']
        with client.websocket_connect('/ws/'+code) as ws:
            ws.send_json({'type':'join','name':'Mage'});joined=receive(ws,'joined')
            room=main.manager.rooms[code];room.begin_round(time.monotonic())
            ws.send_json({'type':'dev_cast','spell':'bolt'})
            assert 'disabled' in receive(ws,'error')['message']


def test_room_isolation():
    from backend.app.engine import Room
    a,b=Room('AAAA',0),Room('BBBB',0)
    p=a.add('A',0);b.add('B',0)
    p.hp=1
    assert next(iter(b.players.values())).hp==100
