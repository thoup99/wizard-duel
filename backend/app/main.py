import asyncio
from collections import defaultdict, deque
from contextlib import asynccontextmanager, suppress
import hmac
import json
import logging
import os
from pathlib import Path
import secrets
import time
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, ValidationError

from .engine import Room, SPELLS
from .gestures import DEFAULT_CONFIG, load_config, recognize, validate_samples, SHAPES

ROOT = Path(__file__).resolve().parents[2]
DEV_MODE = os.getenv('DEV_MODE', 'false').lower() == 'true'
ADMIN_TOKEN = os.getenv('ADMIN_TOKEN', '')
CONFIG_PATH = os.getenv('GESTURE_CONFIG', str(DEFAULT_CONFIG))
SAMPLE_DIR = Path(os.getenv('SAMPLE_DIR', str(ROOT / 'samples')))
MAX_ROOMS = int(os.getenv('MAX_ROOMS', '100'))
ALLOWED_ORIGINS = set(filter(None, os.getenv('ALLOWED_ORIGINS', '').split(',')))
log = logging.getLogger('pocket-mages')

class Message(BaseModel):
    model_config = ConfigDict(extra='forbid')
    type: str = Field(max_length=30)
    name: str = Field(default='Mage', min_length=1, max_length=24)
    token: str | None = Field(default=None, max_length=100)
    team: StrictInt | None = Field(default=None, ge=0, le=1)
    ready: StrictBool | None = None
    sensors_ok: StrictBool = False
    target_id: str | None = Field(default=None, max_length=40)
    platform: str = Field(default='other', pattern='^(ios|android|other)$')
    samples: list = Field(default_factory=list, max_length=320)
    schema_version: StrictInt | None = None
    save_sample: StrictBool = False
    label: str | None = Field(default=None, pattern='^(bolt|ward|empower|hex|unknown)$')
    spell: str | None = Field(default=None, max_length=12)
    t: float | None = None

class Sample(BaseModel):
    schema_version: StrictInt = 2
    mode: str = Field(default="mixed", pattern="^(shapes|flicks|mixed)$")
    label: str = Field(pattern='^(bolt|ward|empower|hex|unknown)$')
    platform: str = Field(pattern='^(ios|android|other)$')
    samples: list = Field(max_length=320)

class Peer:
    def __init__(self, ws):
        self.ws = ws
        self.queue = asyncio.Queue(maxsize=32)
        self.player_id = None
        self.sender = asyncio.create_task(self.send_loop())

    async def send_loop(self):
        try:
            while True:
                await asyncio.wait_for(self.ws.send_json(await self.queue.get()), 3)
        except (Exception, asyncio.CancelledError):
            with suppress(Exception):
                await self.ws.close()

    def send(self, data):
        if self.queue.full():
            self.queue.get_nowait()
        self.queue.put_nowait(data)

class Manager:
    def __init__(self):
        self.rooms = {}
        self.peers = defaultdict(set)
        self.tasks = {}
        self.config = load_config(CONFIG_PATH)
        self.create_limits = {}
        self.practice_limits = {}

    def create(self):
        if len(self.rooms) >= MAX_ROOMS:
            raise HTTPException(503, 'The arena is busy. Try again shortly.')
        alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ'
        code = ''.join(secrets.choice(alphabet) for _ in range(4))
        while code in self.rooms:
            code = ''.join(secrets.choice(alphabet) for _ in range(4))
        now = time.monotonic()
        room = Room(code, now, last_activity=now, last_tick=now)
        self.rooms[code] = room
        self.tasks[code] = asyncio.create_task(self.loop(room))
        return room

    def broadcast(self, room):
        snap = room.snapshot(time.monotonic())
        for peer in list(self.peers[room.code]):
            peer.send(snap)

    async def loop(self, room):
        last_broadcast, last_seq = 0, -1
        try:
            while True:
                now = time.monotonic()
                room.tick(now)
                if now - last_broadcast >= .5 or room.sequence != last_seq:
                    self.broadcast(room)
                    last_broadcast, last_seq = now, room.sequence
                # Idle means no game/lobby action, not just an open browser tab.
                if now - room.last_activity > 1800:
                    break
                await asyncio.sleep(.05)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception('Room simulation failed: %s', room.code)
        finally:
            self.rooms.pop(room.code, None)
            self.tasks.pop(room.code, None)
            for peer in list(self.peers.pop(room.code, set())):
                with suppress(Exception):
                    await peer.ws.close(code=1001, reason='Room expired')

manager = Manager()

@asynccontextmanager
async def lifespan(app):
    yield
    tasks = list(manager.tasks.values())
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)

app = FastAPI(title='Pocket Mages', lifespan=lifespan)

@app.middleware('http')
async def headers(request, call_next):
    response = await call_next(request)
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'same-origin'
    response.headers['Permissions-Policy'] = 'accelerometer=(self), gyroscope=(self)'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'"
    return response

@app.get('/api/health')
async def health():
    return {'status': 'ok', 'game': 'Pocket Mages'}

@app.get('/api/settings')
async def settings():
    spells={s['id']:dict(SPELLS[s['id']],gesture=s['mixed']['caption'] if manager.config['mode']=='mixed' else s['sweep_caption'] if manager.config['mode']=='flicks' else s['caption']) for s in SHAPES}
    return dict(dev_mode=DEV_MODE, spells=spells, shapes=SHAPES, gesture_mode=manager.config['mode'], schema_version=2)

@app.post('/api/rooms', status_code=201)
async def create_room(request: Request):
    now = time.monotonic()
    ip = request.client.host if request.client else 'unknown'
    manager.create_limits = {k:v for k,v in manager.create_limits.items() if now-v[-1] < 60}
    hits = [t for t in manager.create_limits.get(ip, []) if now-t < 60]
    if len(hits) >= 10:
        raise HTTPException(429, 'Please wait before creating another room.')
    manager.create_limits[ip] = hits + [now]
    room = manager.create()
    return {'code': room.code}

@app.get('/api/rooms/{code}')
async def room_info(code: str):
    room = manager.rooms.get(code.upper())
    if not room:
        raise HTTPException(404, 'Room not found or expired.')
    return dict(code=room.code, phase=room.phase, players=len(room.players), joinable=room.phase=='LOBBY' and len(room.players)<4)

@app.get('/api/gestures/config')
async def config():
    return manager.config

def require_admin(request):
    supplied = request.headers.get('authorization', '')
    if not ADMIN_TOKEN or not hmac.compare_digest(supplied, f'Bearer {ADMIN_TOKEN}'):
        raise HTTPException(403, 'Set ADMIN_TOKEN and provide it as a Bearer token to use tuning endpoints.')

@app.post('/api/gestures/reload')
async def reload_config(request: Request):
    require_admin(request)
    try:
        manager.config = load_config(CONFIG_PATH)
    except (ValueError, OSError) as exc:
        raise HTTPException(400, str(exc)) from exc
    return {'status': 'reloaded'}

@app.post('/api/samples', status_code=201)
async def save_sample(sample: Sample, request: Request):
    require_admin(request)
    try:
        validate_samples(sample.samples)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if sample.schema_version != 2:
        raise HTTPException(400, 'Orientation schema 2 is required.')
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    if len(list(SAMPLE_DIR.glob('*.json'))) >= 10000:
        raise HTTPException(507, 'Sample storage is full.')
    filename = f'{sample.label}-{secrets.token_hex(8)}.json'
    (SAMPLE_DIR / filename).write_text(sample.model_dump_json())
    return {'filename': filename}

def store_practice(message):
    """Explicit opt-in only. Labels are prompts, not claimed ground truth."""
    try:
        SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
        if len(list(SAMPLE_DIR.glob('*.json'))) >= 10000: return False
        payload = dict(schema_version=2, label=message.label, platform=message.platform,
                       samples=message.samples, source='practice_prompt', mode=manager.config['mode'])
        (SAMPLE_DIR / f'practice-{secrets.token_hex(12)}.json').write_text(json.dumps(payload))
        return True
    except OSError:
        log.warning('Could not save opted-in practice sample')
        return False

@app.post('/api/practice')
async def practice(message: Message, request: Request):
    now=time.monotonic();ip=request.client.host if request.client else 'unknown'
    manager.practice_limits={k:v for k,v in manager.practice_limits.items() if now-v[-1]<60}
    hits=[t for t in manager.practice_limits.get(ip,[]) if now-t<60]
    if len(hits)>=60: raise HTTPException(429,'Take a moment before practicing again.')
    manager.practice_limits[ip]=hits+[now]
    if message.label not in SPELLS: raise HTTPException(400,'Choose a practice spell.')
    try: result=recognize(message.samples,message.platform,manager.config,message.schema_version)
    except ValueError as exc: raise HTTPException(400,str(exc)) from exc
    return dict(type='practice_result', **result, expected=message.label,
                success=result['outcome']=='cast' and result['spell']==message.label,
                saved=store_practice(message) if message.save_sample else False)

def check_origin(ws):
    origin = ws.headers.get('origin')
    if not origin:  # Non-browser clients, including integration tests.
        return True
    if ALLOWED_ORIGINS:
        return origin in ALLOWED_ORIGINS
    return urlparse(origin).netloc == ws.headers.get('host')

@app.websocket('/ws/{code}')
async def socket(ws: WebSocket, code: str):
    code = code.upper()
    room = manager.rooms.get(code)
    if not room or not check_origin(ws):
        await ws.close(code=1008)
        return
    await ws.accept()
    if len(manager.peers[code]) >= 40:
        await ws.send_json(dict(type='error', code='audience_full', message='The audience is full. Try again when someone leaves.'))
        await ws.close(code=1013, reason='Audience full')
        return
    peer = Peer(ws)
    player = None
    rate = deque()
    joined = False
    try:
        while True:
            raw = await asyncio.wait_for(ws.receive_text(), timeout=15 if not joined else 45)
            if len(raw) > 65536:
                await ws.close(code=1009)
                break
            now = time.monotonic()
            while rate and now-rate[0] > 1:
                rate.popleft()
            rate.append(now)
            if len(rate) > 30:
                await ws.close(code=1008, reason='Message rate exceeded')
                break
            try:
                message = Message.model_validate_json(raw)
                if message.type in ('join', 'watch'):
                    if joined:
                        raise ValueError('Already joined.')
                    if message.type == 'join':
                        if message.token:
                            player = next((p for p in room.players.values() if hmac.compare_digest(p.token, message.token)), None)
                            if player is None or (player.disconnected_at is not None and now-player.disconnected_at > 60):
                                player = None
                                peer.send(dict(type='error', code='token_expired', message='Your reconnect slot expired. Return home to join again.'))
                                continue
                            for old in list(manager.peers[code]):
                                if old.player_id == player.id:
                                    manager.peers[code].discard(old)
                                    await old.ws.close(code=4001, reason='Opened on another tab')
                        else:
                            if len(room.players) >= 4 or room.phase != 'LOBBY':
                                peer.send(dict(type='spectator', message='Duel full or underway. You are watching.'))
                            else:
                                name = ''.join(ch for ch in message.name.strip() if ch.isprintable())[:24]
                                player = room.add(name or 'Mage', now)
                        if player:
                            player.connected, player.disconnected_at = True, None
                            peer.player_id = player.id
                            if room.host_id is None:
                                room.host_id = player.id
                            peer.send(dict(type='joined', player_id=player.id, token=player.token, dev_mode=DEV_MODE))
                    else:
                        peer.send(dict(type='spectator'))
                    joined = True
                    manager.peers[code].add(peer)
                    manager.broadcast(room)
                    continue
                if not joined:
                    raise ValueError('Join the room first.')
                if message.type == 'ping':
                    peer.send(dict(type='pong', t=message.t))
                    continue
                if player is None:
                    raise ValueError('Spectators cannot control a duel.')
                if peer not in manager.peers[code]:
                    break
                if message.type == 'set_team' and message.team is not None:
                    room.set_team(player, message.team)
                elif message.type == 'ready' and message.ready is not None:
                    if room.phase != 'LOBBY':
                        raise ValueError('Ready is available in the lobby.')
                    if message.ready and not DEV_MODE and (not message.sensors_ok or player.practice_successes < 3):
                        raise ValueError('Enable sensors and complete three successful practice casts first.')
                    player.ready = message.ready
                elif message.type == 'shuffle_team_name' and message.team is not None:
                    room.shuffle_team_name(player, message.team)
                elif message.type == 'practice_cast':
                    if room.phase != 'LOBBY': raise ValueError('Practice is available in the lobby.')
                    if message.label not in SPELLS: raise ValueError('Choose a practice spell.')
                    result = recognize(message.samples, message.platform, manager.config, message.schema_version)
                    success = result['outcome'] == 'cast' and result['spell'] == message.label
                    if success: player.practice_successes += 1
                    saved = store_practice(message) if message.save_sample else False
                    peer.send(dict(type='practice_result', **result, success=success, expected=message.label,
                                   practice_successes=player.practice_successes, saved=saved))
                elif message.type == 'start':
                    room.start(player, now)
                elif message.type == 'rematch':
                    room.rematch(player, now)
                elif message.type == 'set_target':
                    target = room.players.get(message.target_id)
                    if not target:
                        raise ValueError('Unknown target.')
                    if target.team == player.team:
                        player.ally_id = target.id
                    else:
                        player.target_id = target.id
                elif message.type in ('cast', 'dev_cast'):
                    if room.phase != 'DUEL' or now < player.cooldown_until or player.hp <= 0:
                        raise ValueError('Wait until you are alive and your wand is ready.')
                    if message.type == 'dev_cast':
                        if not DEV_MODE:
                            raise ValueError('Development casts are disabled.')
                        spell, confidence, result = message.spell, 1.0, None
                    else:
                        result = recognize(message.samples, message.platform, manager.config, message.schema_version)
                        spell, confidence = result['spell'], result['score']
                    room.cast(player, spell, confidence, now, message.target_id, result, manager.config['fizzle_cooldown_s'])
                else:
                    raise ValueError('Unknown or incomplete command.')
                room.last_activity = now
                manager.broadcast(room)
            except (ValidationError, ValueError) as exc:
                peer.send(dict(type='error', message='Invalid message format.' if isinstance(exc, ValidationError) else str(exc)))
    except (WebSocketDisconnect, asyncio.TimeoutError, RuntimeError):
        pass
    finally:
        manager.peers[code].discard(peer)
        if player and not any(p.player_id == player.id for p in manager.peers[code]):
            player.connected, player.disconnected_at, player.ready = False, time.monotonic(), False
            room.tick(time.monotonic())
            manager.broadcast(room)
        peer.sender.cancel()
        with suppress(asyncio.CancelledError):
            await peer.sender

@app.get('/')
async def index():
    return FileResponse(ROOT / 'frontend/index.html')

@app.get('/{page}')
async def page(page: str):
    name = page.removesuffix('.html')
    if name not in ('phone', 'arena', 'debug', 'record', 'practice'):
        raise HTTPException(404)
    return FileResponse(ROOT / f'frontend/{name}.html')

app.mount('/static', StaticFiles(directory=ROOT / 'frontend'), name='static')
