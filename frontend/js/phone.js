import { enableSound, spellSound } from "./sound.js";
import {
  $,
  escape,
  toast,
  teamName,
  spellGuide,
  isLikelyPhone,
  api,
} from "./common.js";
import { Connection } from "./connection.js";
import { Motion, keepAwake, releaseAwake } from "./motion.js";
import { SPELLS, diagram, trail, setGestureMode } from "./spells.js";
import { project, preview } from "./projection.js";
import {
  Training,
  trainingHTML,
  StrokeControl,
  feedbackHTML,
  showFeedback,
} from "./training.js";
async function main() {
  const params = new URLSearchParams(location.search),
    code = (params.get("room") || "").toUpperCase();
  if (!/^[A-HJ-NP-Z]{4}$/.test(code)) {
    location.replace("/");
    return;
  }
  if (!isLikelyPhone()) {
    location.replace("/arena?room=" + code);
    return;
  }
  const settings = await api("/api/settings");
  setGestureMode(settings.gesture_mode);
  let me = null,
    state = null,
    phase = "",
    dev = settings.dev_mode,
    enemyTarget = null,
    allyTarget = null,
    lastSeq = null,
    online = false,
    training = null,
    castControl = null,
    lastPaint = 0;
  const motion = new Motion(() => {
    if ($("#motionStatus")) $("#motionStatus").textContent = motion.status();
    updateReady();
    if (performance.now() - lastPaint > 50) {
      training?.live();
      if (motion.capturing && phase === "DUEL")
        trail($("#liveTrail"), preview(motion.buffer));
      lastPaint = performance.now();
    }
  });
  const conn = new Connection(code, {
    onMessage: message,
    onStatus: (ok, e) => {
      online = ok;
      $("#connection").textContent = ok ? "● Connected" : "○ Disconnected";
      $("#connection").classList.toggle("off", !ok);
      $("#connectionBanner").hidden = ok;
      if (!ok) {
        training?.control.cancel();
        castControl?.cancel();
        if (e?.code === 4001)
          $("#connectionBanner").textContent =
            "This mage is open in another tab.";
        if (e?.code === 1008)
          $("#connectionBanner").textContent =
            "Room unavailable. Return home and check the room code.";
      }
      if ($("#cast")) $("#cast").disabled = !ok;
    },
  });
  function send(type, fields = {}) {
    if (!conn.send({ type, ...fields }))
      throw Error("Not connected. Reconnecting to the arena…");
  }
  function message(m) {
    if (m.type === "joined") me = m.player_id;
    if (m.type === "spectator") {
      conn.close();
      location.replace("/arena?room=" + code);
    }
    if (m.type === "error") toast(m.message);
    if (m.type === "practice_result") {
      training?.result(m);
      spellSound(m.spell, m.outcome);
    }
    if (m.type === "state") {
      state = m;
      render();
      if (lastSeq !== null)
        for (const e of m.events.filter((e) => e.seq > lastSeq)) feedback(e);
      lastSeq = m.seq;
    }
  }
  const mine = () => state?.players.find((p) => p.id === me);
  const name = (id) =>
    escape(state.players.find((p) => p.id === id)?.name || "Mage");
  function teamLabel(t) {
    return `${t ? "◆" : "✦"} ${escape(teamName(state, t))}`;
  }
  function updateReady() {
    if ($("#ready"))
      $("#ready").disabled =
        !dev && (!motion.tested || (mine()?.practice_successes || 0) < 3);
  }
  async function enableMotion() {
    try {
      const permission = motion.enable();
      enableSound();
      await permission;
      toast("Sensors enabled. Make a 10° test wave.");
      setTimeout(() => {
        if ($("#motionStatus"))
          $("#motionStatus").textContent = motion.status();
      }, 1800);
    } catch (e) {
      toast(e.message);
    }
  }
  function render() {
    const p = mine();
    if (!p) return;
    const changed = phase !== state.phase;
    phase = state.phase;
    if (changed) {
      training?.destroy();
      training = null;
      castControl?.destroy();
      castControl = null;
      if (phase === "DUEL") keepAwake();
      else releaseAwake();
    }
    if (phase === "LOBBY") {
      if (changed) {
        $("#app").innerHTML =
          `<div class="room-head"><div><div class="eyebrow">Room <span class="room-code">${escape(code)}</span></div><h1>Assemble your coven.</h1></div><button id="share" class="small outline">Copy invite ↗</button></div><div id="teams" class="teams"></div><section class="panel sensor-panel"><h3>Awaken your wand</h3><button id="motion" class="wide">Enable motion & orientation</button><p id="motionStatus" class="status-line">${motion.status()}</p><a href="/arena?room=${code}" class="tiny">No usable sensors? Join the audience →</a></section>${trainingHTML()}<button id="ready" class="primary wide">I’m ready</button><button id="start" class="wide" hidden>Start duel →</button><p id="lobbyHint" class="tiny center"></p>${spellGuide()}`;
        $("#motion").onclick = enableMotion;
        $("#ready").onclick = () =>
          send("ready", { ready: !mine().ready, sensors_ok: motion.tested });
        $("#start").onclick = () => send("start");
        $("#share").onclick = async () => {
          try {
            await navigator.clipboard.writeText(
              location.origin + "/?room=" + code,
            );
            toast("Invite copied.");
          } catch {
            toast(location.origin + "/?room=" + code);
          }
        };
        training = new Training($("#app"), motion, (payload) =>
          send("practice_cast", payload),
        );
      }
      const teamHTML = [0, 1]
        .map(
          (t) =>
            `<section class="team team-${t}"><div class="team-title">${teamLabel(t)} ${p.team === t ? `<button class="shuffle small" data-shuffle="${t}" aria-label="Shuffle your team name">↻</button>` : ""}</div>${state.players
              .filter((x) => x.team === t)
              .map(
                (x) =>
                  `<div class="player-row"><div class="avatar">${t ? "◆" : "✦"}</div><div class="meta"><strong>${escape(x.name)}${x.id === me ? " · you" : ""}</strong><small>${x.id === state.host_id ? "Host · " : ""}${x.connected ? "Connected" : "Reconnecting"}</small></div><span class="check">${x.ready ? "✓ Ready" : "…"}</span></div>`,
              )
              .join(
                "",
              )}${Array.from({ length: 2 - state.players.filter((x) => x.team === t).length }, () => '<div class="player-row tiny muted">Waiting for a mage…</div>').join("")}<div class="player-row"><button class="small wide" data-team="${t}">${p.team === t ? "Your team" : "Join team"}</button></div></section>`,
        )
        .join("");
      if ($("#teams").innerHTML !== teamHTML) {
        $("#teams").innerHTML = teamHTML;
        document
          .querySelectorAll("[data-team]")
          .forEach(
            (b) =>
              (b.onclick = () => send("set_team", { team: +b.dataset.team })),
          );
        document
          .querySelectorAll("[data-shuffle]")
          .forEach(
            (b) =>
              (b.onclick = () =>
                send("shuffle_team_name", { team: +b.dataset.shuffle })),
          );
      }
      training.progress(p.practice_successes);
      updateReady();
      $("#ready").textContent = p.ready ? "Not ready" : "I’m ready";
      $("#start").hidden = me !== state.host_id;
      $("#start").disabled =
        state.players.length !== 4 ||
        state.players.some((x) => !x.ready || !x.connected);
      $("#lobbyHint").textContent = dev
        ? "Development mode · practice and sensors optional"
        : "Four ready mages are needed. Practice first, then ready up.";
      return;
    }
    if (phase === "COUNTDOWN") {
      $("#app").innerHTML =
        `<div class="countdown"><div class="eyebrow team-text-${p.team}">Round ${state.round} · ${teamLabel(p.team)}</div><div class="number">${Math.max(1, Math.ceil(state.remaining))}</div><h2>Wands at the ready.</h2></div>`;
      return;
    }
    if (phase === "DUEL") {
      if (changed) {
        $("#app").innerHTML =
          `<div class="battle-header"><div id="roundLabel" class="eyebrow"></div><div class="score"><b id="score0"></b><div class="timer" id="clock"></div><b id="score1"></b></div><div id="teamLabels" class="team-labels"></div></div><div class="target-label">Rivals · attack target</div><div id="enemies" class="battle-grid"></div><div class="target-label">Your team · shield target</div><div id="allies" class="battle-grid"></div><div class="hud"><div><label>YOUR HEALTH <b id="hpValue"></b></label><div class="bar"><i id="hpBar"></i></div></div><div><label>YOUR MANA · +1.5/s <b id="manaValue"></b></label><div class="bar mana"><i id="manaBar"></i></div></div><div class="spell-chips">${SPELLS.map((s) => `<div>${diagram(s.id, false)}<small>${s.name} · ${s.cost}</small></div>`).join("")}</div><div class="cast-area"><canvas id="liveTrail" width="280" height="180" aria-label="Live wand stroke"></canvas><button id="cast" class="cast-button">CAST<span>HOLD · DRAW · RELEASE</span></button><p id="castHint" class="cast-hint"></p><button id="duelMotion" class="small outline">Enable sensors</button></div>${feedbackHTML()}${dev ? `<div class="dev-controls"><p>DEVELOPMENT ONLY</p><div class="actions">${SPELLS.map((s) => `<button data-spell="${s.id}">${s.name}</button>`).join("")}</div></div>` : ""}<div id="feed" class="feed"></div>${spellGuide()}`;
        castControl = new StrokeControl($("#cast"), motion, (payload) =>
          send("cast", payload),
        );
        $("#duelMotion").onclick = enableMotion;
        document
          .querySelectorAll("[data-spell]")
          .forEach(
            (b) =>
              (b.onclick = () => send("dev_cast", { spell: b.dataset.spell })),
          );
      }
      $("#roundLabel").textContent = `Round ${state.round} · first to two wins`;
      $("#score0").textContent = state.wins[0];
      $("#score1").textContent = state.wins[1];
      $("#clock").textContent =
        `${Math.floor(state.remaining / 60)}:${String(Math.floor(state.remaining % 60)).padStart(2, "0")}`;
      $("#teamLabels").innerHTML =
        `<span class="team-text-0">${teamLabel(0)}</span><span class="team-text-1">${teamLabel(1)}</span>`;
      const enemies = state.players.filter((x) => x.team !== p.team),
        allies = state.players.filter((x) => x.team === p.team);
      if (!enemies.some((x) => x.id === enemyTarget && x.hp > 0))
        enemyTarget = enemies
          .filter((x) => x.hp > 0)
          .sort((a, b) => a.hp - b.hp)[0]?.id;
      if (!allies.some((x) => x.id === allyTarget && x.hp > 0)) allyTarget = me;
      $("#enemies").innerHTML = enemies
        .map((x) => fighter(x, x.id === enemyTarget))
        .join("");
      $("#allies").innerHTML = allies
        .map((x) => fighter(x, x.id === allyTarget))
        .join("");
      document.querySelectorAll("[data-target]").forEach(
        (b) =>
          (b.onclick = () => {
            const t = state.players.find((x) => x.id === b.dataset.target);
            if (t.team === p.team) allyTarget = t.id;
            else enemyTarget = t.id;
            send("set_target", { target_id: t.id });
            render();
          }),
      );
      $("#hpValue").textContent = Math.ceil(p.hp) + "/100";
      $("#manaValue").textContent = Math.floor(p.mana) + "/100";
      $("#hpBar").style.width = p.hp + "%";
      $("#manaBar").style.width = p.mana + "%";
      $("#cast").disabled = !online || p.hp <= 0 || p.cooldown > 0;
      $("#duelMotion").hidden = motion.available;
      $("#castHint").textContent =
        p.hp <= 0
          ? "Knocked out. Cheer your ally on!"
          : p.cooldown > 0
            ? "Wand cooling down…"
            : motion.capturing
              ? "Finish your motion, then release…"
              : "Hold CAST. Sweep. Release.";
      if (p.hp <= 0) castControl.cancel();
      $("#feed").innerHTML = state.events
        .filter(
          (e) =>
            ["spell_result", "knockout"].includes(e.type) &&
            e.outcome !== "no_cast",
        )
        .slice(-5)
        .reverse()
        .map((e) => `<div>${eventText(e)}</div>`)
        .join("");
      return;
    }
    if (phase === "ROUND_END" || phase === "MATCH_END") {
      const end = phase === "MATCH_END",
        winner = end ? state.winner : state.round_winner;
      $("#app").innerHTML =
        `<section class="results"><div class="eyebrow">${end ? "Match complete" : "Round " + state.round + " complete"}</div><h2 class="${winner === null ? "" : "team-text-" + winner}" style="margin-top:25px">${winner === null ? "A magical stalemate." : teamLabel(winner) + " wins!"}</h2><p>${end ? "Good spells. Better rivals." : `Next round in ${Math.ceil(state.remaining)} seconds.`}</p><div class="team-labels"><span class="team-text-0">${teamLabel(0)} · ${state.wins[0]}</span><span class="team-text-1">${teamLabel(1)} · ${state.wins[1]}</span></div>${statsTable()}${end && me === state.host_id ? '<button id="rematch" class="primary wide">One more duel →</button>' : ""}<p class="tiny" style="margin-top:20px"><a href="/">Return home</a></p></section>`;
      if ($("#rematch")) $("#rematch").onclick = () => send("rematch");
    }
  }
  function fighter(p, selected) {
    return `<button class="fighter ${selected ? "selected" : ""} ${p.hp <= 0 ? "dead" : ""}" data-target="${p.id}" ${p.hp <= 0 ? "disabled" : ""} aria-pressed="${selected}"><div class="name"><strong>${escape(p.name)}${p.id === me ? " · you" : ""}</strong><span>${Math.ceil(p.hp)} HP</span></div><div class="tiny team-text-${p.team}">${teamLabel(p.team)}</div><div class="bar"><i style="width:${p.hp}%"></i></div><div class="effects">${p.hp <= 0 ? "KNOCKED OUT" : Object.keys(p.effects).join(" · ") || (selected ? "SELECTED" : "Tap to target")}</div></button>`;
  }
  function statsTable() {
    return `<table class="result-table"><thead><tr><th>Mage / team</th><th>Damage</th><th>Blocked</th><th>Casts</th><th>Accuracy</th></tr></thead><tbody>${state.players.map((p) => `<tr><td>${escape(p.name)} ${state.mvp === p.id ? '<span class="badge">MVP</span>' : ""}<div class="tiny team-text-${p.team}">${teamLabel(p.team)}</div></td><td>${Math.round(p.stats.damage)}</td><td>${Math.round(p.stats.blocked)}</td><td>${p.stats.casts}</td><td>${p.stats.accuracy}%</td></tr>`).join("")}</tbody></table>`;
  }
  function eventText(e) {
    if (e.type === "knockout")
      return `${name(e.caster)} knocked out ${name(e.target)}.`;
    if (e.outcome === "fizzle") return `${name(e.caster)} · near miss`;
    return `${name(e.caster)} · ${escape(e.spell || "spell")} ${e.outcome === "hit" ? "hit " + name(e.target) + " for " + e.damage : e.outcome === "blocked" ? "blocked" : escape(e.outcome)}`;
  }
  function feedback(e) {
    if (
      e.type === "spell_result" &&
      e.caster === me &&
      ["cast", "fizzle", "no_cast"].includes(e.outcome)
    ) {
      if ($("#resultTrail")) showFeedback($(".stroke-feedback"), e);
      spellSound(e.spell, e.outcome);
      if (e.outcome === "cast") navigator.vibrate?.(25);
    }
    if (e.target === me && e.outcome === "hit") navigator.vibrate?.(70);
  }
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden && phase === "DUEL") keepAwake();
  });
}
main().catch((error) => {
  toast(error.message);
  $("#app").innerHTML =
    '<section class="panel"><h2>Unable to load your wand.</h2><p>Refresh the page or return home to try again.</p><a href="/">Return home</a></section>';
});
