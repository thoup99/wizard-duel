import pytest
from backend.app import main
from backend.app.devices import mobile_browser
from test_api import client,receive,MOBILE_UA
DESKTOP='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0 Safari/537.36'

@pytest.mark.parametrize('ua,hint,allowed',[(MOBILE_UA,False,True),('Mozilla/5.0 (Linux; Android 15)',False,True),(DESKTOP,True,False),('Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit/605.1.15 Safari/605.1.15',True,True),('Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit/605.1.15 Safari/605.1.15',False,False),('testclient',False,False)])
def test_mobile_browser_policy(ua,hint,allowed):assert mobile_browser(ua,hint)==allowed

def test_desktop_cannot_create_room_even_with_touch_hint(client):
    before=len(main.manager.rooms)
    r=client.post('/api/rooms',headers={'user-agent':DESKTOP,'x-pocket-mages-mobile':'1'})
    assert r.status_code==403 and len(main.manager.rooms)==before

def test_desktop_join_becomes_spectator_and_cannot_control(client):
    code=client.post('/api/rooms').json()['code']
    with client.websocket_connect('/ws/'+code,headers={'user-agent':DESKTOP}) as ws:
        ws.send_json({'type':'join','name':'Desktop','mobile_device':True})
        receive(ws,'spectator');assert len(main.manager.rooms[code].players)==0
        ws.send_json({'type':'ready','ready':True,'sensors_ok':True})
        assert 'Spectators' in receive(ws,'error')['message']

def test_desktop_cannot_take_over_mobile_reconnect_token(client):
    code=client.post('/api/rooms').json()['code']
    with client.websocket_connect('/ws/'+code) as phone:
        phone.send_json({'type':'join','name':'Phone'});joined=receive(phone,'joined')
        with client.websocket_connect('/ws/'+code,headers={'user-agent':DESKTOP}) as desktop:
            desktop.send_json({'type':'join','token':joined['token']})
            receive(desktop,'spectator')
            phone.send_json({'type':'ping','t':1});assert receive(phone,'pong')['t']==1
