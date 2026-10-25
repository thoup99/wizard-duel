# Pocket Mages v2 protocol

Single authoritative process, 20Hz simulation, immediate event snapshots and 500ms heartbeat. Relative durations are sent to clients. Rooms and progress are in memory; update between matches.

## REST

- `GET /api/health`: liveness.
- `GET /api/settings`: dev mode, spells, shared shapes, gesture_mode and schema version.
- `POST /api/rooms`: create room; `GET /api/rooms/{code}`: joinability.
- `GET /api/gestures/config`: thresholds. `POST /api/gestures/reload`: protected by Bearer ADMIN_TOKEN.
- `POST /api/samples`: manual v2 recording, protected by Bearer ADMIN_TOKEN; fields label, platform, schema_version, mode, samples.
- `POST /api/practice`: standalone practice. Same practice_cast payload as below. Rate limited to 60 requests/minute per source IP. Opt-in recordings are bounded by the shared 10,000-file sample quota; a full/unwritable volume returns saved=false without breaking practice.

## WebSocket /ws/{code}

Join/watch within 15 seconds; ping every 10 seconds (45-second idle timeout). Maximum 30 messages/second, 64KiB per message. Fields are validated; v1 acceleration casts are rejected.

```json
{"type":"join","name":"Mage","token":null}
{"type":"watch"}
{"type":"set_team","team":0}
{"type":"shuffle_team_name","team":0}
{"type":"practice_cast","label":"bolt","schema_version":2,"platform":"ios","save_sample":false,"samples":[]}
{"type":"ready","ready":true,"sensors_ok":true}
{"type":"start"}
{"type":"set_target","target_id":"player-id"}
{"type":"cast","schema_version":2,"platform":"ios","samples":[]}
{"type":"rematch"}
{"type":"ping","t":1234}
```

Empty sample arrays above are placeholders. Real windows contain 2–320 rows `[seconds, alpha, beta, gamma, rx, ry, rz]`, finite values over at most 2.5 seconds. Duplicate timestamps are removed, unsorted rows sorted. Platform is ios/android/other, retained as metadata, not a sign-flip rule.

Practice is lobby-only and does not change combat stats. Three accepted casts matching the requested label unlock Ready; `sensors_ok` also must be true unless DEV_MODE. This quality assertion is a UX check, not anti-cheat. Successful progress persists across rematches. A team may shuffle its own name only in the lobby; names persist across rematches.

`joined` contains the private token and player ID. `spectator` identifies watch-only/overflow joins. Audience receives no player controls and cannot send gameplay or practice messages. `error` contains a friendly message; `audience_full` stops reconnect retries. `pong` echoes t.

`state` contains phase, round, wins, team_names, name_position, public players (including practice_successes), effects, relative cooldowns, stats and recent sequenced events. The shuffled deck itself remains server-only. Never broadcast reconnect tokens.

`practice_result` is sent only to the practicing player: outcome, spell, score, top_guess, reason, hint, path, expected, success, practice_successes, saved. The standalone endpoint omits room practice progress.

Recognition results are `spell_result` entries in state.events:

- outcome `cast`: accepted and applied/launched; one-second cooldown, normal mana cost.
- outcome `fizzle`: deliberate unmatched shape; no mana cost, configurable 0.25s cooldown; counts in accuracy.
- outcome `no_cast`: too_short, too_small or too_slow; no mana/cooldown/stat penalty.
- score, top_guess, reason (`too_small`, `too_short`, `too_slow`, `ambiguous`, `no_match`), hint and angular path accompany recognition feedback.
- Later projectile events still use `hit` or `blocked` and damage/absorbed values.

Other events: team_name_changed, countdown, round_start, knockout, disconnect_forfeit, round_end, match_end. Track seq to avoid replaying sound. Phases and combat rules are unchanged. No cast doesn't advance attempt counters; practice is excluded from match accuracy.

Config mode `flicks` uses net path direction rather than shape templates; refresh pages after switching mode to load matching diagrams. Keep server and clients on the same release. The sensor adapter prefers fused relative orientation and falls back to short-window body-rate integration when unavailable.
