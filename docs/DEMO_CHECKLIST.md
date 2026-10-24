# Four-phone demo acceptance

These are device checks to perform, not claims of completed validation.

1. Start Docker, confirm `/api/health`, and open the same HTTPS URL on four phones. Include both iOS Safari and Android Chrome if those will be used at the demo.
2. Create a room, join all phones, select two players per team, enable motion, test-wave and ready. Verify only the host can start and a fifth browser watches.
3. Record at least ten samples of each spell per tester plus idle/random movement. Tune on a separate subset; run the evaluator on held-out recordings. Target ≥85% overall accuracy and inspect per-spell confusion.
4. Cast Bolt: verify mana drops by 20, then target HP by 20 after approximately 0.4s. Cast Ward before impact and verify absorption. Repeat to exhaust its 30-point capacity.
5. Cast Empower, then a Bolt: expect 30 damage. Hex the empowered caster and expect 18. Verify effects expire after six seconds.
6. Try an unclear gesture: no mana spent, short cooldown, fizzle hint. Verify cooldown/mana prevent repeated rapid casts.
7. Check the optional arena screen, sound enable, kill feed, teammate targeting and responsive phone layout. Measure release-to-feedback latency on the actual network; target under 300ms excludes Bolt's intentional travel time.
8. Disconnect a phone and reconnect within 60 seconds: same identity and stats. Verify host transfer. Test expiry after 60 seconds separately.
9. Win two rounds and check scoreboard/MVP. Request rematch and verify all players remain and must ready again.
10. Test an equal-HP timeout: no point, new round. Ensure two ordinary decisive rounds and a three-round 1–1 match both work.
11. Confirm production has no direct spell buttons. Keep the development mode fallback on a separate trusted demo setup if necessary.
12. Publish a stable GitHub release, confirm CI and both platform images, then pull the release on the server. Verify the container is healthy and HTTPS/WebSockets work. Do this between matches because updates clear rooms.

Fallback if internet fails: a laptop hotspot and a certificate trusted by every phone (for example a locally configured mkcert setup). A self-signed browser warning is not a substitute for a trusted secure context. Certificate installation is not automated by this project.
