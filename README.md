# Pocket Mages

**Four friends. Two teams. Your phone is your wand.**

A complete core implementation of the supplied Wizard Duel design, renamed Pocket Mages: a motion-controlled, 2v2 browser party game. FastAPI owns combat; mobile browsers send gesture windows over WebSockets. No accounts, database, frontend framework, or frontend build step.

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
3. Select teams: Jade Coven and Rose Order, two mages each.
4. Tap **Enable motion sensors**, grant access, and make a test wave. Then tap **I’m ready**.
5. The host starts a three-second countdown.
6. Tap an enemy to aim attacks or a teammate to aim shields. Hold **CAST**, perform one gesture, and release.
7. Open `/arena?room=CODE` on a larger screen for spectators; click **Enable sound** once.

Keep a firm grip on the phone and room around you. Hold it with the screen facing you and the top edge pointing forward. Portrait orientation is the intended grip.

## Spells and rules

| Spell | Gesture | Mana | Result |
|---|---|---:|---|
| Bolt | A sharp forward thrust | 20 | 20 damage after 0.4 seconds of travel |
| Ward | Draw a circle in the air | 25 | Absorb 30 damage for 4.5 seconds; self or ally |
| Empower | A smooth upward sweep | 30 | Both living teammates deal 50% more damage for 6 seconds |
| Hex | Side-to-side zigzag | 30 | Enemy deals 40% less damage for 6 seconds |

- 100 HP and 100 mana per round; regenerate 8 mana/second.
- One-second global cast cooldown. An unrecognized gesture fizzles without spending mana and incurs a half-second cooldown.
- A round lasts 90 seconds or ends when a team is eliminated. At timeout, higher total team HP wins.
- First team to two round wins takes the match. The design leaves ties unspecified: tied rounds award no point and replay, so a match can exceed three rounds when tied.
- Damage modifiers are captured when a Bolt launches; Ward absorbs damage when it arrives. Effects refresh, never stack with themselves.
- Default offensive target is the lowest-health living enemy. Shields default to self. Attack and shield selections are independent.
- A defeated mage spectates until the next round; no resurrection within a round.
- Results include damage dealt, damage blocked, casts, gesture recognition accuracy, and MVP. MVP score is damage + half of damage blocked + 20 per knockout.
- Gesture accuracy = recognized gestures / attempted casts. It is not hit accuracy; a Ward can block a correctly recognized Bolt.
- Host can request a rematch, preserving the four players and requiring readiness again.

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

## Gesture validation and tuning

Recognition is rule-based and **not calibrated against your phones yet**. Synthetic tests prove that the implemented patterns classify as intended; they do not establish the document's 85% real-world recognition target or the under-300ms network latency target.

- `/debug`: live acceleration/rotation graphs.
- `/record`: labeled capture with local JSON download, optional protected server upload, and threshold reload.
- `backend/config/gestures.json`: thresholds and per-platform six-axis sign multipliers.
- `scripts/eval_gestures.py`: a confusion matrix over real recordings, including negative `unknown` examples.

Capture at least 10 examples per spell per tester, on the actual iOS/Android phones. Record negative examples too. Keep tuning and evaluation recordings separate; evaluate held-out recordings to avoid tuning to the test set.

```bash
python scripts/eval_gestures.py recordings/ --minimum-accuracy 0.85
```

The script returns a nonzero status for an unmet target, no samples, or malformed files. Samples are rows `[seconds, ax, ay, az, rx, ry, rz]`; browser rotation beta/gamma/alpha map to x/y/z. The server resamples at 50Hz, smooths, trims idle sections, and demeans dynamic channels. It deliberately preserves raw gyro for Empower's signed integrated angle, since demeaning would erase the signal.

Platform sign multipliers default to +1 until actual measurements justify a flip; there is no unverified blanket iOS inversion. Most rules are direction-independent. The client uses linear acceleration where available, otherwise a low-pass gravity estimate. Hold the phone consistently during calibration.

For server-side saving/reloading, set a long random `ADMIN_TOKEN` in `.env`, restart the app, and enter it on the lab page. It is held only in that page's memory, not localStorage. Samples can always be downloaded locally without a token. For live file tuning, bind-mount your config into `/app/backend/config/gestures.json` read-only, edit the host file, then use the reload button. Invalid thresholds leave the previous config active.

## Tests

```bash
python -m pytest -q
```

32 automated tests cover engine rules, gesture signatures and malformed samples, API access, four-player joins, spectators, reconnect identity, full-match recognized-motion casts, rematch, and production rejection of direct spell buttons. A full match uses real protocol handlers with the simulation clock advanced for fast execution. A separate TCP test starts Uvicorn, connects four real WebSocket clients, completes the countdown, and verifies a recognized Bolt damages its target.

Verification performed during delivery:

- 32 tests passed.
- All browser JavaScript passed `node --check`.
- Python source compiled and the update script passed `bash -n`.
- Docker and real-phone/browser rendering were unavailable for local verification. GitHub CI performs the Docker build, Compose validation and health smoke test when uploaded.

Before the first demo, run the four-phone checklist in `docs/DEMO_CHECKLIST.md`.

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

The complete **core game** in the design is implemented. The explicitly optional stretch features—Heal, Counter, Combo Blast, and DTW template matching—are not enabled or represented as finished features. No accounts, matchmaking, persistence, or anti-cheat system was added, matching the design's non-goals.
