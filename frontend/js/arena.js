import { $, escape, api, teamName, symbols, toast } from "./common.js";
import { trail, setGestureMode } from "./spells.js";
import { Connection } from "./connection.js";
const settings = await api("/api/settings");
setGestureMode(settings.gesture_mode);
let audio = null,
  sound = false,
  lastSeq = null,
  scene = null,
  latestState = null,
  liveConnected = true;
const demo = new URLSearchParams(location.search).get("demo") === "1";
let stopDemo;
function sceneFailure(message) {
  $("#sceneStatus").hidden = false;
  $("#sceneStatus").textContent = message;
  $("#sceneMotion").disabled = true;
}
async function startScene() {
  $("#theater").hidden = false;
  try {
    const { ArenaScene } = await import("./arena-scene.js");
    scene = new ArenaScene($("#arenaViewport"), { onFailure: sceneFailure });
    $("#sceneStatus").hidden = true;
    scene.setConnected(liveConnected);
    if (latestState) scene.update(latestState);
    $("#sceneMotion").textContent = scene.paused
      ? "Play animation"
      : "Pause animation";
    $("#sceneMotion").setAttribute("aria-pressed", String(!scene.paused));
  } catch (error) {
    scene?.dispose();
    scene = null;
    sceneFailure(
      "3D is unavailable in this browser. Live scores and spell results are shown below.",
    );
    console.warn("Arena graphics unavailable:", error);
  }
}
$("#sceneMotion").onclick = () => {
  if (!scene) return;
  scene.setPaused(!scene.paused);
  $("#sceneMotion").textContent = scene.paused
    ? "Play animation"
    : "Pause animation";
  $("#sceneMotion").setAttribute("aria-pressed", String(!scene.paused));
};
$("#sceneFullscreen").disabled = !document.fullscreenEnabled;
$("#sceneFullscreen").onclick = async () => {
  try {
    if (document.fullscreenElement) await document.exitFullscreen();
    else await $("#theater").requestFullscreen();
  } catch {
    toast("Fullscreen is unavailable in this browser.");
  }
};
window.addEventListener("pagehide", () => {
  scene?.dispose();
  stopDemo?.();
});
function stateReceived(m) {
  latestState = m;
  render(m);
  scene?.update(m);
  if (lastSeq !== null)
    for (const e of m.events.filter(
      (x) =>
        x.seq > lastSeq && x.type === "spell_result" && x.outcome === "cast",
    ))
      tone(e.spell);
  lastSeq = m.seq;
}
$("#sound").onclick = async () => {
  audio = audio || new AudioContext();
  await audio.resume();
  sound = !sound;
  $("#sound").textContent = sound ? "Sound on ♫" : "Sound off ♫";
};
function tone(spell) {
  if (!sound || !audio) return;
  const o = audio.createOscillator(),
    g = audio.createGain();
  o.type = "sine";
  o.frequency.setValueAtTime(
    { bolt: 500, ward: 330, empower: 660, hex: 180 }[spell] || 440,
    audio.currentTime,
  );
  o.frequency.exponentialRampToValueAtTime(110, audio.currentTime + 0.25);
  g.gain.setValueAtTime(0.06, audio.currentTime);
  g.gain.exponentialRampToValueAtTime(0.001, audio.currentTime + 0.3);
  o.connect(g);
  g.connect(audio.destination);
  o.start();
  o.stop(audio.currentTime + 0.3);
}
$("#watchForm").onsubmit = async (e) => {
  e.preventDefault();
  try {
    const code = $("#room").value.trim().toUpperCase();
    await api("/api/rooms/" + code);
    location.href = "/arena?room=" + code;
  } catch (err) {
    $("#status").textContent = err.message;
  }
};
const code = (
  new URLSearchParams(location.search).get("room") || ""
).toUpperCase();
if (demo) {
  $("#arenaRoom").textContent = "DEMO · no room or players connected";
  $("#sceneBadge").textContent = "Demo preview";
  $("#connection").textContent = "Local preview";
  $("#sceneNote").textContent =
    "Demo animations only. Open a real room to watch your friends.";
  startScene();
  const { startArenaDemo } = await import("./arena-demo.js");
  stopDemo = startArenaDemo(stateReceived);
} else if (code) {
  $("#arenaRoom").textContent = "ROOM " + code + " · Join on your phone";
  startScene();
  new Connection(code, {
    watch: true,
    onStatus: (ok) => {
      liveConnected = ok;
      scene?.setConnected(ok);
      if (!ok) lastSeq = null;
      $("#connection").textContent = ok
        ? "● Live arena"
        : "○ Connecting / room unavailable";
      $("#sceneBadge").textContent = ok ? "Live match" : "Reconnecting…";
    },
    onMessage: (m) => {
      if (m.type === "error") {
        toast(m.message);
        if (m.code === "audience_full") {
          scene?.dispose();
          $("#theater").hidden = true;
          $("#app").innerHTML =
            '<section class="panel"><h2>Audience full</h2><p>Try again when someone leaves.</p><a href="/">Return home</a></section>';
        }
      }
      if (m.type === "state") stateReceived(m);
    },
  });
}
function render(s) {
  const name = (id) =>
    escape(s.players.find((p) => p.id === id)?.name || "Mage");
  const winner = s.phase === "MATCH_END" ? s.winner : s.round_winner;
  let subtitle =
    s.phase === "LOBBY"
      ? "The party is assembling"
      : s.phase === "COUNTDOWN"
        ? "Wands ready in " + Math.max(1, Math.ceil(s.remaining))
        : s.phase === "ROUND_END" || s.phase === "MATCH_END"
          ? winner === null
            ? "A magical stalemate"
            : escape(teamName(s, winner)) + " wins!"
          : "Round " + s.round + " · first to two wins";
  $("#arenaHud").innerHTML =
    `<div class="battle-header"><div class="eyebrow">${subtitle}</div><div class="score"><b>${s.wins[0]}</b><div class="timer">${s.phase === "DUEL" ? Math.floor(s.remaining / 60) + ":" + String(Math.floor(s.remaining % 60)).padStart(2, "0") : "✧"}</div><b>${s.wins[1]}</b></div></div>`;
  $("#app").innerHTML = `<div class="arena-teams">${[0, 1]
    .map(
      (t) =>
        `${t === 1 ? '<div class="versus">vs.</div>' : ""}<section><div class="eyebrow" style="color:${t ? "var(--team-b)" : "var(--team-a)"};margin-bottom:20px">${t ? "◆" : "✦"} ${escape(teamName(s, t))}</div>${s.players
          .filter((p) => p.team === t)
          .map(
            (p) =>
              `<div class="fighter ${t ? "enemy" : ""} ${p.hp <= 0 ? "dead" : ""}"><div class="avatar team-text-${t}">${t ? "◆" : "✦"}</div><div class="name"><strong>${escape(p.name)}</strong><span>${Math.ceil(p.hp)} <small>HP</small></span></div><div class="bar"><i style="width:${p.hp}%"></i></div><div class="tiny muted" style="margin-top:8px">MANA ${Math.floor(p.mana)} / 100</div><div class="bar mana"><i style="width:${p.mana}%"></i></div><div class="effects">${
                s.phase === "LOBBY"
                  ? p.ready
                    ? "✓ Ready"
                    : "Preparing their wand…"
                  : p.hp <= 0
                    ? "Knocked out"
                    : Object.keys(p.effects)
                        .map((e) => symbols[e] + " " + e)
                        .join(" · ") || "Wand ready"
              }${p.connected ? "" : " · Reconnecting"}</div></div>`,
          )
          .join(
            "",
          )}${Array.from({ length: 2 - s.players.filter((p) => p.team === t).length }, () => '<div class="fighter muted">Waiting for a mage…</div>').join("")}</section>`,
    )
    .join("")}</div>${
    s.phase === "MATCH_END"
      ? `<section class="panel arena-feed"><div class="eyebrow">Most valuable mage</div><h2 style="margin-top:10px">✦ ${name(s.mvp)}</h2><table class="result-table"><thead><tr><th>Mage</th><th>Damage</th><th>Blocked</th><th>Casts</th><th>Accuracy</th></tr></thead><tbody>${s.players.map((p) => `<tr><td>${escape(p.name)}<div class="tiny team-text-${p.team}">${p.team ? "◆" : "✦"} ${escape(teamName(s, p.team))}</div></td><td>${Math.round(p.stats.damage)}</td><td>${p.stats.blocked}</td><td>${p.stats.casts}</td><td>${p.stats.accuracy}%</td></tr>`).join("")}</tbody></table></section>`
      : `<section class="panel arena-feed"><div class="eyebrow">The spell feed</div><div class="feed">${
          s.events
            .slice()
            .reverse()
            .filter((e) =>
              ["spell_result", "knockout", "disconnect_forfeit"].includes(
                e.type,
              ),
            )
            .slice(0, 8)
            .map(
              (e) =>
                `<div>${e.type === "knockout" ? `✦ <strong>${name(e.caster)}</strong> knocked out ${name(e.target)}` : e.type === "disconnect_forfeit" ? name(e.player) + " lost connection" : `${symbols[e.spell] || "·"} <strong>${name(e.caster)}</strong> · ${escape(e.spell || "spell")} ${escape(e.outcome)} ${e.damage ? "· " + e.damage + " damage" : ""}`}</div>`,
            )
            .join("") ||
          '<p style="margin:15px 0 0">The calm before the spellstorm.</p>'
        }</div></section>`
  }<div id="arenaStroke" class="arena-feed"></div><p class="center tiny" style="margin:25px">${demo ? 'Preview only · <a href="/">Return home</a>' : `Join on your phone at <strong>${escape(location.host)}</strong> · Room <strong>${escape(code)}</strong>`}</p>`;
  const last = s.events
    .filter((e) => e.type === "spell_result" && e.path?.length)
    .at(-1);
  if (last) {
    $("#arenaStroke").innerHTML =
      `<div class="stroke-feedback"><canvas id="arenaTrail" width="280" height="220" aria-label="Last spell trail and ghost shape"></canvas><p>${name(last.caster)} · ${escape(last.outcome)} · ${Math.round(last.score * 100)}%<br>${escape(last.hint || "")}</p></div>`;
    trail($("#arenaTrail"), last.path, last.top_guess);
  }
}
