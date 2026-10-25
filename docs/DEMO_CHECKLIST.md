# Four-phone demo acceptance

These are device checks to perform, not claims of completed validation.

1. Start Docker, confirm `/api/health`, and open the same HTTPS URL on four phones. Include both iOS Safari and Android Chrome if those will be used at the demo.
2. Create a room, join all phones, select two players per team, enable motion/orientation, test-wave, complete three practice casts and ready. Verify only the host can start and a fifth browser watches.
3. Record at least ten samples of each spell per tester plus idle/random movement. Tune on a separate subset; run the evaluator on held-out recordings. Target ≥85% overall accuracy and inspect per-spell confusion.
4. Cast Bolt: verify mana drops by 20, then target HP by 20 after approximately 0.4s. Cast Ward before impact and verify absorption. Repeat to exhaust its 30-point capacity.
5. Cast Empower, then a Bolt: expect 28 damage. Hex the empowered caster and expect 18.2. Verify Empower expires after 10 seconds and Hex after 12 seconds.
6. Try a deliberate unclear shape: no mana spent, 0.25s cooldown, fizzle hint. Tiny accidental motions should be No cast with no penalty. Verify cooldown/mana prevent repeated rapid casts.
7. Check the optional arena screen, sound enable, kill feed, teammate targeting and responsive phone layout. Measure release-to-feedback latency on the actual network; target under 300ms excludes Bolt's intentional travel time.
8. Disconnect a phone and reconnect within 60 seconds: same identity and stats. Verify host transfer. Test expiry after 60 seconds separately.
9. Win two rounds and check scoreboard/MVP. Request rematch and verify all players remain and must ready again.
10. Test an equal-HP timeout: no point, new round. Ensure two ordinary decisive rounds and a three-round 1–1 match both work.
11. Confirm production has no direct spell buttons. Keep the development mode fallback on a separate trusted demo setup if necessary.
12. Publish a stable GitHub release, confirm CI and both platform images, then pull the release on the server. Verify the container is healthy and HTTPS/WebSockets work. Do this between matches because updates clear rooms.

Fallback if internet fails: a laptop hotspot and a certificate trusted by every phone (for example a locally configured mkcert setup). A self-signed browser warning is not a substitute for a trusted secure context. Certificate installation is not automated by this project.

## V2 acceptance additions

- Refresh every browser after updating; old acceleration payloads are not compatible.
- Verify iOS asks for both motion and orientation access on the same tap. Test battery-saver/low-rate, denied permissions and non-HTTPS messages. Check gyro fallback separately if fused events are absent.
- Use the new gestures: Bolt right, Ward circle, Empower up, Hex Z-shaped zigzag. Test small wrist sweeps and natural returns before and after releasing CAST. Verify tiny/short/slow movement is No cast (no cooldown or accuracy penalty) and deliberate misses have a quarter-second cooldown.
- On each teammate's phone, try each spell 20 times in Training Grounds. Target at least 85% accepted as intended, with at least one iPhone and one Android if available. During a four-player match, count deliberate fizzles; target under 15%.
- Before three successful prompted casts, Ready must remain disabled. Incorrect spells cannot unlock it. Confirm live trail, gray ghost, score, hint and optional recording consent. With consent off, no practice files should appear.
- Open an invite on a computer: go directly to the arena, no name/team prompt. Verify desktop creation is unavailable, `?player=1` cannot bypass spectator routing, and a fifth phone joins as audience. Verify a full audience gets a friendly error.
- Shuffle each team's name and check all phones and the arena update. Only teammates can shuffle, only in the lobby; names stay through a rematch.
- Verify gold-star and violet-diamond identities in lobby, HUD, arena and results. HP is green and mana blue for both teams; both are labeled. Check diagrams on iPhone Safari and Android Chrome and reduced-motion settings.
- Check pre/post-roll, interrupted/cancelled presses, long presses and screen wake/portrait lock support. Losing focus must cancel a stroke, not cast it.
- Measure release-to-result latency including the 100ms post-roll. Target under 300ms; synthetic recognition time alone does not prove this.
- The default is mixed (right/circle/up/Z). Optionally test legacy flicks and shapes modes, then reload config and refresh all clients so displayed instructions agree.

- First-time player check: ask someone who has not played to follow only the on-screen diagrams. Try curved sweeps, off-axis sweeps, and returns past the starting point. Record per-spell successes, fizzles, and wrong spells separately; synthetic percentages are not human accuracy.

- Verify incidental vertical twitching is reduced on a rightward Bolt, while Ward circles and Hex zigzags retain their vertical shape. Try oval circles from several starting points and loose Zs in both directions.

- Check 40 starting mana, 1.5 mana/s regeneration, and 65-second rounds. Test the timeout tie-break: team HP, then surviving players’ mana; exact ties replay.

- Open `/arena?demo=1` alone: confirm four animated cartoon mages and all four spell effects; check pause, fullscreen and mobile sizing.
- Watch a real match: verify each cast plays once, shields/buffs match the scorecards, KO/winner poses match the server, and reconnect does not replay old spells.
- Confirm the homepage has one spell gallery and direct Training Grounds links.
