# Pocket Mages

**Four friends. Two teams. Your phone is your wand.**

Pocket Mages v2 implements the original game and the Improvement Design Document: a motion-controlled, 2v2 browser party game. FastAPI owns combat; mobile browsers send gesture windows over WebSockets. No accounts, database, frontend framework, or frontend build step.

## Play locally with Docker

```bash
docker compose up --build
```

The app listens on port **8000**. The included Cloudflare quick tunnel supplies HTTPS for phones. Find its URL:

```bash
docker compose logs tunnel
```

Open the printed `https://…trycloudflare.com` address on all four phones. It can change when the tunnel restarts. The desktop home page is also available at `http://localhost:8000`, but a plain LAN HTTP address will not enable phone motion sensors.

1. Enter a mage name and create a room.
2. Share the four-letter room code or **Copy invite** link with three friends.
3. Select a team (two mages each); teammates can shuffle their randomly assigned team name.
4. Tap **Enable motion & orientation**, grant both permissions, and wave at least 10 degrees at 30 Hz or faster. Complete three successful casts in the lobby Training Grounds, then tap **I’m ready**.
5. The host starts a three-second countdown.
6. Tap an enemy to aim attacks or a teammate to aim shields. Hold **CAST**, perform one gesture, and release.
7. Open `/arena?room=CODE` on a larger screen for spectators; click **Enable sound** once.

Keep a firm grip on the phone and room around you. Hold it with the screen facing you and the top edge pointing forward. Portrait orientation is the intended grip.

## Spells and rules

| Spell | Gesture | Mana | Result |
|---|---|---:|---|
| Bolt | Sweep right → | 20 | 20 damage after 0.4 seconds of travel |
| Ward | Loose circle, either direction | 22 | Absorb 28 damage for 7 seconds; self or ally |
| Empower | Sweep up ↑ | 28 | Both living teammates deal 40% more damage for 10 seconds |
| Hex | Loose Z-shaped zigzag | 24 | Enemy deals 35% less damage for 12 seconds |

- 100 HP and 40 starting mana per round, with a 100-mana cap; regenerate 1.5 mana/second.
- 1.25-second global cast cooldown. A deliberate but unmatched shape fizzles without spending mana and incurs a 0.25-second cooldown. Tiny, short, or slow movement is **No cast**, with no cooldown and no accuracy penalty.
- A round lasts 65 seconds or ends when a team is eliminated. At timeout, higher total team HP wins; tied HP is broken by the surviving players’ total mana.
- First team to two round wins takes the match. Exact ties in both health and surviving mana award no point and replay; simultaneous knockouts also replay.
- Damage modifiers are captured when a Bolt launches; Ward absorbs damage when it arrives. Effects refresh, never stack with themselves.
- Default offensive target is the lowest-health living enemy. Shields default to self. Attack and shield selections are independent.
- A defeated mage spectates until the next round; no resurrection within a round.
- Results include damage dealt, damage blocked, casts, gesture recognition accuracy, and MVP. MVP score is damage + half of damage blocked + 20 per knockout.
- Gesture accuracy = recognized gestures / deliberate attempted casts; No cast and practice are excluded. It is not hit accuracy; a Ward can block a correctly recognized Bolt.
- Host can request a rematch, preserving the four players and requiring readiness again. Team names and practice progress stay with the players.

## Match pacing

Best-of-three matches target about three minutes on average, with 65-second rounds, 5-second intermissions and 3-second countdowns. Two full rounds take 2m21s; three take 3m34s. Early knockouts shorten matches and exact ties can extend them. Starting mana is 40 and regeneration is 1.5/s (down from 8/s), so saving for a coordinated burst matters.

A seeded simulation of 200 matches using identical randomized policies for both teams averaged **179.8 seconds**, with 103 versus 97 wins and no unfinished matches. See `scripts/eval_balance.py` and `docs/balance-results.json`. This is a balance estimate, not a guarantee for human play.

## Publish Docker releases with GitHub Actions

Project repository: https://github.com/thoup99/wizard-duel. Container image: `ghcr.io/thoup99/wizard-duel`. The game is named Pocket Mages; the repository retains its existing wizard-duel name.

1. Use the existing GitHub repository `thoup99/wizard-duel`.
2. From this extracted project directory:

   ```bash
   git init -b main
   git add .
   git commit -m "Build Pocket Mages"
   git remote add origin https://github.com/thoup99/wizard-duel.git
   git push -u origin main
   ```

3. Allow GitHub Actions in the repository. `.github/workflows/docker.yml` uses the built-in `GITHUB_TOKEN` with `packages: write`; no Docker Hub password is needed.
4. The first push runs tests, JavaScript syntax checks, Compose validation, and a built-container HTTP smoke test, then publishes an `edge` image.
5. In GitHub **Releases → Draft a new release**, choose a semantic version tag such as **`v1.0.0`**, target `main`, and publish it as a stable release.
6. The successful workflow publishes:

   ```text
   ghcr.io/thoup99/wizard-duel:1.0.0
   ghcr.io/thoup99/wizard-duel:latest
   ghcr.io/thoup99/wizard-duel:sha-<short-commit>
   ```

The image path is automatically derived from the actual owner/repository and lowercased. Builds support **linux/amd64** and **linux/arm64**. Main-branch pushes update `edge`, not `latest`. Prereleases get their version tag but do not move `latest`. Pull requests test and build without registry publishing.

The `latest` tag exists **after the first successful stable release**, not merely after uploading the project. If GHCR reports a permissions conflict, check whether a package with the same name already exists and grant this repository Actions access to it.

Official references: [publishing Docker images](https://docs.github.com/en/actions/tutorials/publish-packages/publish-docker-images), [GitHub Container Registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry).

## Run the released image on your server

Copy `compose.production.yml`, `.env.example`, and `scripts/update.sh` (preserving its `scripts/` directory) to a server directory, or clone the repository there.

```bash
cp .env.example .env
```

Edit `.env` with the **real lowercase image path**:

```dotenv
POCKET_MAGES_IMAGE=ghcr.io/thoup99/wizard-duel:latest
PORT=8000
```

For a private package, log into GHCR with a personal access token that has `read:packages` and access to the package. Enter it interactively; do not commit it:

```bash
docker login ghcr.io -u YOUR-GITHUB-USERNAME
```

Alternatively, make the GHCR package public in its package settings so pulls need no credentials. A public repository does not by itself guarantee public package visibility.

Start production:

```bash
docker compose -f compose.production.yml pull app
docker compose -f compose.production.yml up -d --wait app
```

To pull and run the latest published release later:

```bash
bash scripts/update.sh
```

Or use the equivalent commands:

```bash
docker compose -f compose.production.yml pull app
docker compose -f compose.production.yml up -d --no-deps --wait app
```

This is an explicit pull/update workflow; GitHub Actions does not log into your server or silently replace running matches. Rooms are in memory, so an app restart or update ends active games. Update between sessions. To roll back, set `POCKET_MAGES_IMAGE` to a previous version tag and run the same script. For an immutable deployment use the image digest from GHCR.

### HTTPS using Nginx Proxy Manager

Create a Proxy Host with your game domain, scheme `http`, the Docker server's reachable IP, and forwarding port `8000` (or your chosen `PORT`). Enable **Websockets Support**. Add a valid SSL certificate and enable **Force SSL**. Preserve the original Host header, or set:

```dotenv
ALLOWED_ORIGINS=https://mages.example.com
```

Use your actual domain. If Nginx Proxy Manager itself runs in Docker, `127.0.0.1` inside its container is not the game server; use the server LAN address or attach both services to a shared Docker network and forward to `app:8000`. Set `BIND_ADDRESS` to an appropriate interface if limiting the published port.

For a temporary production HTTPS tunnel instead:

```bash
docker compose -f compose.production.yml --profile tunnel up -d
docker compose -f compose.production.yml logs tunnel
```

Phones need HTTPS and a browser supporting motion sensors. On iPhone, permission must be requested from a user tap. See [MDN's motion-permission documentation](https://developer.mozilla.org/en-US/docs/Web/API/DeviceMotionEvent/requestPermission_static).

### Operational constraints

- **Exactly one Uvicorn worker and one app replica.** In-memory rooms are not shared between processes.
- Room codes expire after 30 minutes without a game/lobby action. Pings do not extend idle lifetime.
- Reconnect tokens stay in localStorage on the same browser/origin. A slot is held for 60 seconds after disconnect; the next connected player becomes host.
- After 60 seconds, a disconnected lobby player is removed. During a match the mage is knocked out; their slot/stats remain until lobby cleanup. An expired token cannot reclaim that slot mid-match.
- Opening the same saved mage in a second tab takes over its connection. Use separate browser profiles for desktop testing.
- Each room has a bounded spectator count and WebSocket queues. Room creation and inbound message rates are limited.
- Samples persist in the named Docker `samples` volume. Match state intentionally does not persist.
- Production runs as non-root with a read-only root filesystem; `/app/samples` is writable through the volume.
- Docker health checks test `/api/health`. The update script waits for health; it does not implement automatic rollback.

## Development without Docker

Python 3.12 is the tested runtime. From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1` instead. An optional `npm run dev` launcher uses port 3000; Node is not needed to run the game itself. Phone sensors still require HTTPS.

For desktop/manual-spell testing only:

```bash
DEV_MODE=true uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

On PowerShell: `$env:DEV_MODE="true"` before running Uvicorn. Or use the development Compose override:

```bash
docker compose -f docker-compose.yml -f compose.dev.yml up --build
```

Development mode allows readiness without sensors and shows four direct spell buttons. Production Compose hard-disables it, and the server rejects `dev_cast` messages when disabled. Development reloads destroy active rooms.

## Orientation gestures and Training Grounds (v2)

The default `mixed` spellbook gives each spell a distinct motion: **Bolt** is a short wrist punch to the right, **Ward** is a loose circle, **Hex** is a Z-shaped zigzag with two turns, and **Empower** is a straight upward flick. Hold CAST for the entire motion and release to cast. Circles accept either direction and any starting point; zigzags accept either drawing direction. Aim the phone’s top edge like a wand: sideways translation without wrist rotation is not reliably measured by the orientation sensors.

Clearly horizontal motions have their incidental vertical movement reduced by 45%, both in recognition and the smoothed live preview. This applies only when horizontal extent is over 2.5 times vertical extent and the path is not a repeated horizontal zigzag. Circles and zigzags retain both axes.

`frontend/spells.json` is the shared source for spell names, costs, colors, captions and shape geometry. It drives server templates and frontend SVG diagrams. The browser shows a live trail; the server makes all recognition and combat decisions. Each result includes a score, closest spell, reason and projected path for the ghost overlay. The arena displays the latest stroke too.

Capture uses relative `deviceorientation` events with concurrent motion/orientation permission requests on iOS, about 150ms pre-roll and 100ms post-roll, and a 2.5-second maximum window. Gyro integration is a fallback when fused orientation is absent; its drift and initial grip assumptions still require device testing. A wake lock during a duel and portrait lock are requested where the browser supports them.

Rows are `[seconds, alpha, beta, gamma, rx, ry, rz]` with `schema_version: 2`. Old clients and old acceleration recordings are rejected; refresh all phones after deploying. The backend sorts timestamps, removes duplicates, resamples pointing vectors at 50Hz, smooths and projects into the stroke plane. It never subtracts or interpolates Euler angles. Directional recognition uses the first deliberate outward excursion and a coarse path to tolerate sensor jitter, curved sweeps, and a natural return to the starting position. It accepts strokes from 80ms and 8 degrees/second peak speed, with at least 4 degrees of travel. Sweeps up to 42 degrees away from a cardinal direction are eligible; the narrow band around an exact diagonal remains ambiguous. Repeated shaking is rejected. A return with up to 35% overshoot is supported. Circle and zigzag recognition compare 64-point paths against oval/start-point/direction variants, with geometry checks to prevent an incomplete multi-turn shape becoming an attack. Legacy shape mode remains available. Short/small/slow strokes are No cast; ambiguous or low-scoring deliberate shapes fizzle.

The default `sweep_error_tolerance: 0.35` accepts a normalized match score of at least 0.65. The score is `0.6 × direction alignment + 0.4 × path efficiency`: alignment is the cosine of the angle to the nearest arrow, and efficiency is outward displacement divided by smoothed outward path length. Circles and zigzags use normalized template-distance scores with the same 0.65 acceptance threshold. These are motion-fit measures, not probabilities or a guaranteed human success rate. Size, duration, diagonal ambiguity, and repeated-shake checks still apply. Legacy `accept_score` applies only to shape mode. Existing configs without the new key inherit 0.35.

- `/practice`: standalone Training Grounds, also linked from How to Play.
- Lobby Training Grounds: three server-confirmed matches unlock Ready. Standalone practice does not grant room readiness.
- Optional recording checkbox: defaults off, stores prompted labels and raw v2 windows in the samples volume without mage names or tokens. Prompted labels are not automatically verified ground truth; inspect recordings before evaluation.
- `/debug` and `/record`: orientation/gyro graphs and labeled JSON capture; downloads require no admin token.
- `backend/config/gestures.json`: reloadable matching/gating thresholds, including `accept_score`, `min_margin`, and `fizzle_cooldown_s`.

`mode: mixed` is the default. `mode: flicks` restores the previous four-arrow controls, and `mode: shapes` restores Z/circle/^/V. Refresh every browser after deployment or mode changes. If you bind-mount a custom config at `/app/backend/config/gestures.json:ro`, update its mode to `mixed`; an old mounted config overrides the image default. Reloading or saving manually from the lab requires `ADMIN_TOKEN`.

```bash
python scripts/eval_gestures.py recordings/ --minimum-accuracy 0.85
python scripts/eval_synthetic.py --count 1000
node scripts/check_frontend.mjs
python -m pytest -q
```

The current mixed-mode evaluation (`scripts/eval_mixed.py`, `docs/mixed-results.json`) tests 400 examples per spell with noise, varying grip, speed, size, oval circles, reverse drawing, curved flicks and returns. It matched all 1,600 intended spells and rejected 99.25% of 400 idle/random paths. These synthetic results are not real-phone or first-time-player accuracy. Test the four motions on your actual phones before judging usability.

CI also retains the earlier flick-mode evaluations (`eval_synthetic.py`, `eval_beginner.py`) explicitly in legacy flick mode to protect compatibility.

## Audience and team identity

Desktop invite/code joins go directly to the arena, without a name prompt. The audience view has **Join as a player instead** for tablets/developers. Room creation still creates a player; the first player is host. A fifth player or new mid-match join becomes audience automatically. Audience connections cannot cast, ready, practice or shuffle names.

Each room draws two names from `backend/config/team_names.json`. Players may shuffle only their own team's name in the lobby; names do not repeat until the shared shuffled deck is exhausted and remain through rematches. Team A uses a gold star; Team B uses a violet diamond. Both use green health and blue mana, with text labels. Team identity is separate from HP/mana colors.

## Verification

The expanded regression suite covers the original game rules and transport plus v2 projection, geometry matching, gating, practice readiness, recording consent, spectator authorization and team-name shuffling. CI also runs the 4,000-cast synthetic gate, shared JavaScript/Python projection checks, Compose validation and a built-container health check. Physical iPhone/Android tests and rendered browser QA still need to be completed on the deployed site.

## Project map

```text
backend/app/engine.py       Combat, phases, stats, time-based simulation
backend/app/main.py         REST API, WebSocket hub, rooms, rate limits
backend/app/gestures.py     Validation, preprocessing and rule recognition
backend/config/gestures.json
frontend/                  Home, phone, arena, motion lab; plain HTML/CSS/JS
scripts/eval_gestures.py    Recorded-sample evaluation
scripts/update.sh          Pull and start the released Docker image
.github/workflows/docker.yml
compose.production.yml     Pull-only server deployment
```

See `docs/PROTOCOL.md` for API/message details. Spell audio is synthesized in-browser; artwork is original SVG/CSS included in the source. No third-party image/font/CDN dependency is needed.

## Scope

The complete **core game** in the design is implemented. The explicitly optional stretch features—Heal, Counter, Combo Blast, per-player practice templates, custom team names, and DTW template matching—are not enabled or represented as finished features. No accounts, matchmaking, persistence, or anti-cheat system was added, matching the design's non-goals.
