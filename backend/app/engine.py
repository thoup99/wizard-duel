"""Authoritative, clock-injected duel simulation. No network or wall-clock dependencies."""
from dataclasses import dataclass, field
import secrets

import json
import random
from pathlib import Path
from .gestures import SHAPES

SPELLS = {s['id']: dict(cost=s['cost'], gesture=s['caption'], description=s['description']) for s in SHAPES}
TEAM_NAMES = json.loads((Path(__file__).resolve().parents[1] / 'config/team_names.json').read_text())


@dataclass
class Wizard:
    name: str
    team: int
    id: str = field(default_factory=lambda: secrets.token_hex(8))
    token: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    connected: bool = True
    disconnected_at: float | None = None
    ready: bool = False
    practice_successes: int = 0
    hp: float = 100
    mana: float = 100
    cooldown_until: float = 0
    effects: dict = field(default_factory=dict)
    target_id: str | None = None
    ally_id: str | None = None
    stats: dict = field(default_factory=lambda: dict(damage=0, blocked=0, casts=0, attempts=0, recognized=0, kills=0))

@dataclass
class Room:
    code: str
    created_at: float
    players: dict = field(default_factory=dict)
    host_id: str | None = None
    phase: str = 'LOBBY'
    wins: list = field(default_factory=lambda: [0, 0])
    round_number: int = 1
    deadline: float = 0
    last_tick: float = 0
    last_activity: float = 0
    projectiles: list = field(default_factory=list)
    events: list = field(default_factory=list)
    sequence: int = 0
    winner: int | None = None
    round_winner: int | None = None
    team_names: list = field(default_factory=list)
    name_deck: list = field(default_factory=list)
    name_position: int = 0

    def __post_init__(self):
        self.name_deck = list(dict.fromkeys(TEAM_NAMES))
        if len(self.name_deck) < 3: raise ValueError('At least three distinct team names are required.')
        random.SystemRandom().shuffle(self.name_deck)
        self.team_names = self.name_deck[:2]
        self.name_position = 2

    def shuffle_team_name(self, player, team):
        if self.phase != 'LOBBY' or player.team != team:
            raise ValueError('Only teammates can shuffle their name in the lobby.')
        previous = self.team_names[team]
        for _ in range(len(self.name_deck) * 2):
            if self.name_position >= len(self.name_deck):
                random.SystemRandom().shuffle(self.name_deck)
                self.name_position = 0
            name = self.name_deck[self.name_position]
            self.name_position += 1
            if name not in self.team_names:
                self.team_names[team] = name
                self.emit('team_name_changed', team=team, name=name)
                return
        raise ValueError('No alternative team name available.')

    def emit(self, kind, **data):
        self.sequence += 1
        self.events.append(dict(type=kind, seq=self.sequence, **data))
        self.events = self.events[-40:]

    def add(self, name, now):
        if self.phase != 'LOBBY' or len(self.players) >= 4:
            raise ValueError('This duel is full or underway. Watch it in the arena.')
        team = 0 if sum(p.team == 0 for p in self.players.values()) < 2 else 1
        player = Wizard(name=name, team=team)
        self.players[player.id] = player
        self.host_id = self.host_id or player.id
        self.last_activity = now
        return player

    def set_team(self, player, team):
        if self.phase != 'LOBBY':
            raise ValueError('Teams are locked during a match.')
        if team != player.team and sum(p.team == team for p in self.players.values()) >= 2:
            raise ValueError('That team already has two mages.')
        player.team, player.ready = team, False

    def start(self, player, now):
        if player.id != self.host_id or self.phase != 'LOBBY':
            raise ValueError('Only the host can start from the lobby.')
        if len(self.players) != 4 or any(not p.ready or not p.connected for p in self.players.values()):
            raise ValueError('Four connected, ready mages are required.')
        if sum(p.team == 0 for p in self.players.values()) != 2:
            raise ValueError('Choose two mages per team.')
        self.phase, self.deadline = 'COUNTDOWN', now + 3
        self.emit('countdown', seconds=3)

    def begin_round(self, now):
        self.phase, self.deadline, self.last_tick = 'DUEL', now + 90, now
        self.projectiles.clear()
        for p in self.players.values():
            p.hp = 0 if p.disconnected_at is not None and now - p.disconnected_at >= 60 else 100
            p.mana, p.cooldown_until, p.effects = 100, 0, {}
        self.emit('round_start', round=self.round_number)

    def cast(self, player, spell, confidence, now, target_id=None, recognition=None, fizzle_cooldown=.25):
        if self.phase != 'DUEL' or player.hp <= 0:
            raise ValueError('You can cast only while alive in a duel.')
        if now < player.cooldown_until:
            raise ValueError('Your wand is cooling down.')
        details = {k: recognition[k] for k in ('score','top_guess','reason','path','hint') if k in recognition} if recognition else {}
        if recognition and recognition['outcome'] == 'no_cast':
            self.emit('spell_result', caster=player.id, spell=None, outcome='no_cast', **details)
            return
        player.stats['attempts'] += 1
        if spell not in SPELLS:
            player.cooldown_until = now + fizzle_cooldown
            self.emit('spell_result', caster=player.id, spell=None, outcome='fizzle', confidence=confidence,
                      **(details or dict(hint='Hold CAST and trace the full shape.')))
            return
        player.stats['recognized'] += 1
        if player.mana < SPELLS[spell]['cost']:
            raise ValueError('Not enough mana. Let your wand recharge.')
        enemies = [p for p in self.players.values() if p.team != player.team and p.hp > 0]
        if spell in ('bolt', 'hex'):
            target = self.players.get(target_id or player.target_id)
            if target is None or target.team == player.team or target.hp <= 0:
                target = min(enemies, key=lambda p: p.hp, default=None)
        else:
            target = self.players.get(target_id or player.ally_id) or player
            if target.team != player.team or target.hp <= 0:
                target = player
        if target is None:
            raise ValueError('No living target.')
        player.mana -= SPELLS[spell]['cost']
        player.cooldown_until = now + 1
        player.stats['casts'] += 1
        if spell == 'bolt':
            damage = 20 * (1.5 if player.effects.get('empower', {}).get('until', 0) > now else 1)
            damage *= .6 if player.effects.get('hex', {}).get('until', 0) > now else 1
            self.projectiles.append(dict(at=now + .4, source=player.id, target=target.id, damage=damage))
        elif spell == 'ward':
            target.effects['ward'] = dict(until=now + 4.5, amount=30)
        elif spell == 'empower':
            for ally in self.players.values():
                if ally.team == player.team and ally.hp > 0:
                    ally.effects['empower'] = dict(until=now + 6)
        elif spell == 'hex':
            target.effects['hex'] = dict(until=now + 6)
        self.emit('spell_result', caster=player.id, target=target.id, spell=spell,
                  outcome='cast', confidence=round(confidence, 2), **details)

    def tick(self, now):
        for p in list(self.players.values()):
            if not p.connected and p.disconnected_at is not None and now - p.disconnected_at >= 60:
                if self.phase == 'LOBBY':
                    del self.players[p.id]
                elif p.hp > 0:
                    p.hp = 0
                    self.emit('disconnect_forfeit', player=p.id)
        if self.host_id not in self.players or not self.players[self.host_id].connected:
            self.host_id = next((p.id for p in self.players.values() if p.connected), None)
        if self.phase == 'COUNTDOWN' and now >= self.deadline:
            self.begin_round(now)
        elif self.phase == 'ROUND_END' and now >= self.deadline:
            self.round_number += 1
            self.phase, self.deadline = 'COUNTDOWN', now + 3
            self.emit('countdown', seconds=3)
        if self.phase != 'DUEL':
            self.last_tick = now
            return
        dt = max(0, min(now - self.last_tick, 1))
        self.last_tick = now
        for p in self.players.values():
            if p.hp > 0:
                p.mana = min(100, p.mana + 8 * dt)
            p.effects = {k: v for k, v in p.effects.items() if v['until'] > now}
        due = [b for b in self.projectiles if b['at'] <= now]
        self.projectiles = [b for b in self.projectiles if b['at'] > now]
        for bolt in due:
            target, source = self.players.get(bolt['target']), self.players.get(bolt['source'])
            if target is None or source is None or target.hp <= 0:
                continue
            damage, absorbed = bolt['damage'], 0
            ward = target.effects.get('ward')
            if ward:
                absorbed = min(damage, ward['amount'])
                damage -= absorbed
                ward['amount'] -= absorbed
                target.stats['blocked'] += absorbed
                if ward['amount'] <= 0:
                    del target.effects['ward']
            damage = min(target.hp, damage)
            target.hp -= damage
            source.stats['damage'] += damage
            if target.hp <= 0:
                source.stats['kills'] += 1
                self.emit('knockout', caster=source.id, target=target.id)
            self.emit('spell_result', caster=source.id, target=target.id, spell='bolt',
                      outcome='blocked' if damage == 0 else 'hit', damage=round(damage, 1), absorbed=absorbed)
        hp = [sum(p.hp for p in self.players.values() if p.team == team) for team in (0, 1)]
        if min(hp) <= 0 or now >= self.deadline:
            winner = None if abs(hp[0] - hp[1]) < .001 else int(hp[1] > hp[0])
            self.round_winner = winner
            if winner is not None:
                self.wins[winner] += 1
            self.projectiles.clear()
            if max(self.wins) >= 2:
                self.phase, self.winner = 'MATCH_END', winner
                self.emit('match_end', winner=winner, mvp=self.mvp())
            else:
                self.phase, self.deadline = 'ROUND_END', now + 5
                self.emit('round_end', winner=winner, wins=self.wins.copy())

    def mvp(self):
        return max(self.players.values(), key=lambda p: p.stats['damage'] + .5 * p.stats['blocked'] + 20 * p.stats['kills'], default=None).id if self.players else None

    def rematch(self, player, now):
        if player.id != self.host_id or self.phase != 'MATCH_END':
            raise ValueError('Only the host can request a rematch after the match.')
        self.phase, self.wins, self.round_number = 'LOBBY', [0, 0], 1
        self.winner = self.round_winner = None
        self.events.clear()
        for p in self.players.values():
            p.ready, p.hp, p.mana, p.effects, p.cooldown_until = False, 100, 100, {}, 0
            p.stats = dict(damage=0, blocked=0, casts=0, attempts=0, recognized=0, kills=0)
        self.last_activity = now

    def snapshot(self, now):
        return dict(type='state', code=self.code, phase=self.phase, host_id=self.host_id,
                    wins=self.wins, round=self.round_number, remaining=max(0, self.deadline - now),
                    winner=self.winner, round_winner=self.round_winner, mvp=self.mvp(), seq=self.sequence,
                    team_names=self.team_names.copy(), name_position=self.name_position,
                    events=self.events[-12:], spells=SPELLS,
                    players=[dict(id=p.id, name=p.name, team=p.team, connected=p.connected, ready=p.ready,
                                  practice_successes=p.practice_successes, hp=round(p.hp, 1), mana=round(p.mana, 1), cooldown=max(0, p.cooldown_until-now),
                                  effects={k: dict(remaining=max(0, v['until']-now), amount=v.get('amount')) for k,v in p.effects.items()},
                                  stats={**p.stats, 'accuracy': round(100*p.stats['recognized']/p.stats['attempts']) if p.stats['attempts'] else 0})
                             for p in self.players.values()])
