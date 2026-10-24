# Pocket Mages protocol

The server is authoritative. `time.monotonic()` drives simulation; clients receive relative seconds, not server clock timestamps. The tick loop runs at 20Hz. State is sent after commands/events and at least twice per second.

## REST

| Method | Path | Response / behavior |
|---|---|---|
| GET | `/api/health` | Liveness |
| GET | `/api/settings` | Development flag and spell catalog |
| POST | `/api/rooms` | 201 `{ "code": "ABCD" }` |
| GET | `/api/rooms/{code}` | Phase, player count and joinability |
| GET | `/api/gestures/config` | Active thresholds |
| POST | `/api/gestures/reload` | Requires `Authorization: Bearer ADMIN_TOKEN` |
| POST | `/api/samples` | Protected; `{label, platform, samples}` |

## WebSocket `/ws/{code}`

Connect using WSS on HTTPS. Send `join` or `watch` within 15 seconds. Ping at least every 45 seconds; clients use 10 seconds. At most 30 messages/second and 64 KiB per WebSocket message. Bad commands return an `error` without crashing the room.

### Client messages

```json
{"type":"join","name":"Mage","token":null}
{"type":"watch"}
{"type":"set_team","team":0}
{"type":"ready","ready":true,"sensors_ok":true}
{"type":"start"}
{"type":"set_target","target_id":"player-id"}
{"type":"cast","platform":"ios","samples":[[0,0,1,0,0,0,0],[0.02,0,2,0,0,0,0]]}
{"type":"rematch"}
{"type":"ping","t":1234}
```

The short sample above illustrates the wire format; a valid cast needs 5–240 rows, strictly increasing timestamps covering at most two seconds. Recognition accepts the configured duration range. Seven finite numbers per row: time in seconds, three acceleration channels, three gyro channels. Platform is `ios`, `android`, or `other`.

`cast` may include `target_id`; ordinarily the client sends independent attack/ally selections using `set_target` and leaves recognition to choose the appropriate stored target. `dev_cast` with a `spell` field is accepted only with explicit server development mode.

### Server messages

- `joined`: player ID, private reconnect token, development flag. Never broadcast tokens.
- `spectator`: a watch-only connection; extra joins become spectators.
- `state`: full public state including players, phase, wins, round, countdown/time remaining, recent events and sequence, stats, effects and cooldown durations.
- `error`: human-readable `message`; `token_expired` code instructs the browser to discard an invalid reconnect credential.
- `pong`: echoes `t`.

The design's lobby/countdown/spell/round/match notifications are normalized into the `state` snapshot and its sequenced `events` array, rather than separate WebSocket envelopes. Event types include `countdown`, `round_start`, `spell_result`, `knockout`, `disconnect_forfeit`, `round_end`, and `match_end`. Clients track `seq` to avoid replaying audio and feedback on heartbeat snapshots.

Phases: `LOBBY → COUNTDOWN → DUEL → ROUND_END → COUNTDOWN … → MATCH_END`. Rematch returns to `LOBBY`. Tied rounds replay without a point.

## Trust and deployment

Browser WebSocket Origin must match Host unless `ALLOWED_ORIGINS` explicitly lists accepted origins. Non-browser clients may omit Origin. `sensors_ok` is a UX readiness check, not attestation. Motion samples can be fabricated; anti-cheat is deliberately outside scope.

Use exactly one worker/replica. Behind a proxy, enable WebSocket upgrade and preserve Host or configure allowed origins. No shared state/database exists. A process restart discards all rooms and tokens.
