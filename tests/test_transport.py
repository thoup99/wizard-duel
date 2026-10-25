"""Real TCP smoke test: Uvicorn plus four WebSocket clients, including a gesture cast."""
from contextlib import ExitStack
import json
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request
from websockets.sync.client import connect
from test_gestures import sample
from test_api import MOBILE_UA,MOBILE_HEADERS


def test_real_uvicorn_four_phone_transport():
    with socket.socket() as reservation:
        reservation.bind(('127.0.0.1', 0));port=reservation.getsockname()[1]
    process=subprocess.Popen([sys.executable,'-m','uvicorn','backend.app.main:app','--host','127.0.0.1','--port',str(port),'--workers','1','--ws-max-size','65536'],cwd=Path(__file__).resolve().parents[1],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    def recv(ws, kind):
        for _ in range(100):
            data=json.loads(ws.recv(timeout=8))
            if data['type']==kind:return data
        raise AssertionError('No '+kind)
    try:
        root=f'http://127.0.0.1:{port}'
        for _ in range(100):
            try:
                with urllib.request.urlopen(root+'/api/health',timeout=.3) as response:
                    assert json.load(response)['status']=='ok';break
            except OSError:
                if process.poll() is not None:raise AssertionError(process.stderr.read().decode())
                time.sleep(.05)
        else:raise AssertionError('Uvicorn startup timed out')
        with urllib.request.urlopen(urllib.request.Request(root+'/api/rooms',method='POST',headers=MOBILE_HEADERS),timeout=2) as response:code=json.load(response)['code']
        with ExitStack() as stack:
            clients=[stack.enter_context(connect(f'ws://127.0.0.1:{port}/ws/{code}',user_agent_header=MOBILE_UA)) for _ in range(4)]
            identities=[]
            for i,ws in enumerate(clients):
                ws.send(json.dumps({'type':'join','name':f'Network mage {i}'}));identities.append(recv(ws,'joined')['player_id'])
                for _ in range(3):
                    ws.send(json.dumps({'type':'practice_cast','label':'bolt','schema_version':2,'samples':sample('bolt')}));recv(ws,'practice_result')
                ws.send(json.dumps({'type':'ready','ready':True,'sensors_ok':True}))
                ws.send(json.dumps({'type':'ping','t':1}));recv(ws,'pong')
            clients[0].send(json.dumps({'type':'start'}))
            while recv(clients[0],'state')['phase']!='DUEL':pass
            clients[0].send(json.dumps({'type':'cast','schema_version':2,'samples':sample('bolt'),'platform':'other','target_id':identities[2]}))
            for _ in range(20):
                state=recv(clients[0],'state')
                target=next(p for p in state['players'] if p['id']==identities[2])
                if target['hp']==80:break
            else:raise AssertionError('Bolt never hit over real WebSockets')
    finally:
        process.terminate()
        try:process.wait(timeout=5)
        except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
