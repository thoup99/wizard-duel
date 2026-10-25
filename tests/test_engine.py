import pytest
from backend.app.engine import Room

def duel():
    room = Room('ABCD', 0)
    players = [room.add(f'Mage {i}', 0) for i in range(4)]
    for p in players:p.ready = True
    room.start(players[0], 0);room.tick(3)
    return room, players

def test_four_ready_players_required_and_capacity():
    room=Room('ABCD',0);a=room.add('A',0)
    with pytest.raises(ValueError): room.start(a,0)
    for i in range(3): room.add(str(i),0)
    with pytest.raises(ValueError): room.add('Full',0)
    with pytest.raises(ValueError): room.set_team(a,1)

def test_countdown_and_bolt_travel():
    r,p=duel();assert r.phase=='DUEL'
    r.cast(p[0],'bolt',1,3,p[2].id)
    assert p[0].mana==20 and p[2].hp==100
    r.tick(3.39);assert p[2].hp==100
    r.tick(3.41);assert p[2].hp==80 and p[0].stats['damage']==20

def test_ward_absorbs_and_exhausts():
    r,p=duel();r.cast(p[2],'ward',1,3);r.cast(p[0],'bolt',1,3,p[2].id);r.tick(3.5)
    assert p[2].hp==100 and p[2].effects['ward']['amount']==8
    r.cast(p[0],'bolt',1,4.3,p[2].id);r.tick(4.8)
    assert p[2].hp==88 and 'ward' not in p[2].effects and p[2].stats['blocked']==28

def test_empower_hex_modifiers_and_expiry():
    r,p=duel();r.cast(p[0],'empower',1,3);assert 'empower' in p[1].effects
    r.cast(p[2],'hex',1,3,p[1].id);r.cast(p[1],'bolt',1,3,p[3].id);r.tick(3.5)
    assert p[3].hp==pytest.approx(81.8)
    r.tick(15.1);assert not p[1].effects

def test_cooldown_fizzle_mana_and_dead_player():
    r,p=duel();r.cast(p[0],None,0,3)
    assert p[0].mana==40 and p[0].cooldown_until==3.25
    with pytest.raises(ValueError): r.cast(p[0],'bolt',1,3.1)
    p[0].mana=1
    with pytest.raises(ValueError): r.cast(p[0],'ward',1,4)
    assert p[0].mana==1
    p[0].hp=0
    with pytest.raises(ValueError): r.cast(p[0],'bolt',1,5)

def test_mana_regen_and_cap():
    r,p=duel();p[0].mana=50;r.tick(3.5);assert p[0].mana==50.75
    p[0].mana=99.5;r.tick(4);assert p[0].mana==100

def test_best_of_three_and_rematch():
    r,p=duel();p[2].hp=p[3].hp=0;r.tick(4)
    assert r.phase=='ROUND_END' and r.wins==[1,0]
    r.tick(9);assert r.phase=='COUNTDOWN'
    r.tick(12);assert r.phase=='DUEL' and p[2].hp==100
    p[2].hp=p[3].hp=0;r.tick(13);assert r.phase=='MATCH_END' and r.winner==0
    r.rematch(p[0],14);assert r.phase=='LOBBY' and r.wins==[0,0]
    assert all(not p.ready and p.hp==100 for p in r.players.values())

def test_timeout_tie_replays_without_point():
    r,p=duel();r.tick(68)
    assert r.phase=='ROUND_END' and r.round_winner is None and r.wins==[0,0]

def test_timeout_total_hp_winner():
    r,p=duel();p[0].hp=99;r.tick(68);assert r.round_winner==1

def test_disconnect_host_transfer_grace_and_forfeit():
    r,p=duel();p[0].connected=False;p[0].disconnected_at=4;r.tick(4)
    assert r.host_id==p[1].id and p[0].hp==100
    r.tick(63);assert p[0].hp==100
    r.tick(64);assert p[0].hp==0

def test_target_fallback_and_friendly_ward():
    r,p=duel();p[3].hp=70;r.cast(p[0],'bolt',1,3,p[1].id);r.tick(3.5)
    assert p[3].hp==50 and p[1].hp==100
    r.cast(p[1],'ward',1,3.5,p[0].id);assert 'ward' in p[0].effects

def test_snapshot_never_exposes_tokens():
    r,p=duel();assert all('token' not in entry for entry in r.snapshot(3)['players'])

def test_simultaneous_knockout_is_draw():
    r,p=duel();p[1].hp=p[3].hp=0;p[0].hp=p[2].hp=20
    r.cast(p[0],'bolt',1,3,p[2].id);r.cast(p[2],'bolt',1,3,p[0].id);r.tick(3.5)
    assert r.phase=='ROUND_END' and r.round_winner is None
