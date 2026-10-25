// Local spectator preview: never creates a room or sends gameplay messages.
export function startArenaDemo(onState) {
  let seq = 0,
    tick = 0,
    events = [];
  const players = ["Pip", "Juniper", "Mochi", "Nimbus"].map((name, i) => ({
    id: "demo-" + i,
    name,
    team: i < 2 ? 0 : 1,
    hp: 100,
    mana: 70,
    connected: true,
    ready: true,
    effects: {},
    stats: { damage: 0, blocked: 0, casts: 0, accuracy: 100 },
  }));
  function emit(data) {
    events.push({ ...data, seq: ++seq });
    events = events.slice(-12);
  }
  const timers = new Set();
  function state() {
    onState({
      type: "state",
      code: "DEMO",
      phase: "DUEL",
      round: 1,
      wins: [0, 0],
      remaining: 65 - (tick % 65),
      players,
      team_names: ["The Sunbeam Society", "Moonlight Mischief"],
      seq,
      events,
      mvp: players[0].id,
    });
  }
  function cast() {
    tick += 2;
    for (const p of players) {
      p.mana = Math.min(100, p.mana + 4);
      for (const [k, e] of Object.entries(p.effects))
        if (--e.remaining <= 0) delete p.effects[k];
    }
    const step = (tick / 2 - 1) % 6,
      caster = players[[0, 2, 1, 3, 2, 0][step]],
      target = players[[2, 2, 1, 0, 0, 2][step]],
      spell = ["bolt", "ward", "empower", "hex", "bolt", "bolt"][step];
    caster.mana = Math.max(15, caster.mana - 14);
    emit({
      type: "spell_result",
      outcome: "cast",
      caster: caster.id,
      target: target.id,
      spell,
    });
    if (spell === "ward") target.effects.ward = { remaining: 5, amount: 28 };
    if (spell === "empower")
      for (const p of players)
        if (p.team === caster.team) p.effects.empower = { remaining: 5 };
    if (spell === "hex") target.effects.hex = { remaining: 5 };
    state();
    if (spell === "bolt") {
      const timer = setTimeout(() => {
        timers.delete(timer);
        const blocked = !!target.effects.ward;
        if (!blocked) target.hp = target.hp <= 25 ? 100 : target.hp - 20;
        emit({
          type: "spell_result",
          outcome: blocked ? "blocked" : "hit",
          spell,
          caster: caster.id,
          target: target.id,
          damage: blocked ? 0 : 20,
        });
        state();
      }, 400);
      timers.add(timer);
    }
  }
  state();
  const interval = setInterval(cast, 2000);
  return () => {
    clearInterval(interval);
    timers.forEach(clearTimeout);
  };
}
