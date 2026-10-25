import pytest
from backend.app.engine import ROUND_SECONDS,START_MANA,MANA_REGEN,SPELLS
from test_engine import duel

def prepare():
    r,p=duel()
    for x in p:x.mana=100
    r.cast(p[0],'ward',1,3)
    r.cast(p[2],'bolt',1,3,p[0].id)
    r.tick(3.5)
    return r,p

def test_pacing_values_and_resource_budget():
    r,p=duel()
    assert ROUND_SECONDS==65 and r.deadline==68
    assert START_MANA==40 and MANA_REGEN==1.5
    assert 160 < 3+2.5*ROUND_SECONDS+1.5*8 < 195
    assert (START_MANA+ROUND_SECONDS*MANA_REGEN)//SPELLS['bolt']['cost']==6
    p[0].mana=0
    for frame in range(1,101):r.tick(3+frame*.1)
    assert p[0].mana==pytest.approx(15)

def test_effect_values_and_durations():
    r,p=duel()
    for x in p:x.mana=100
    r.cast(p[0],'ward',1,3);r.cast(p[1],'empower',1,3);r.cast(p[2],'hex',1,3,p[0].id)
    assert p[0].effects['ward']['amount']==28 and p[0].effects['ward']['until']==10
    assert p[1].effects['empower']['until']==13 and p[0].effects['hex']['until']==15

def test_echo_consumes_once_and_uses_server_target():
    r,p=prepare();r.cast(p[0],'hex',1,4.3,p[2].id)
    before=p[0].mana;r.cast(p[0],'bolt',1,5.6,p[2].id)
    assert p[0].mana==before-15 and r.projectiles[-1]['damage']==26
    before=p[0].mana;r.cast(p[0],'bolt',1,7,p[2].id)
    assert p[0].mana==before-20 and r.projectiles[-1]['damage']==20

@pytest.mark.parametrize('when,target_index',[(7.6,2),(4.3,3)])
def test_echo_requires_recent_matching_source(when,target_index):
    r,p=prepare();r.cast(p[0],'hex',1,when,p[target_index].id)
    r.cast(p[0],'bolt',1,when+1.3,p[target_index].id)
    assert r.projectiles[-1]['damage']==20

def test_echo_expires_and_cannot_be_reused_from_same_absorption():
    r,p=prepare();r.cast(p[0],'hex',1,4.3,p[2].id)
    r.cast(p[0],'bolt',1,10.4,p[2].id)
    assert r.projectiles[-1]['damage']==20
    assert p[0].caught_from is None

def test_capture_records_only_positive_absorption_once_per_ward():
    r,p=prepare();first=p[0].caught_until
    r.cast(p[2],'bolt',1,4.3,p[0].id);r.tick(4.8)
    assert p[0].caught_until==first

def test_private_state_resets_and_stays_out_of_snapshot():
    r,p=prepare();r.cast(p[0],'hex',1,4.3,p[2].id)
    snap=r.snapshot(4.3)['players'][0]
    assert not any(k in snap for k in ('caught_from','caught_until','echo_target','echo_until'))
    r.begin_round(8)
    assert p[0].caught_from is None and p[0].echo_target is None
    assert p[0].mana==40

def test_insufficient_mana_does_not_consume_echo():
    r,p=prepare();r.cast(p[0],'hex',1,4.3,p[2].id);p[0].mana=14
    with pytest.raises(ValueError):r.cast(p[0],'bolt',1,5.6,p[2].id)
    assert p[0].echo_target==p[2].id and p[0].mana==14

def test_timeout_breaks_health_tie_by_living_team_mana():
    r,p=duel();p[0].mana=10;r.tick(r.deadline)
    assert r.round_winner==1

def test_dead_players_mana_does_not_break_tie():
    r,p=duel();p[0].hp=p[2].hp=0;p[0].mana=100;p[2].mana=0
    r.tick(r.deadline)
    assert r.round_winner is None
