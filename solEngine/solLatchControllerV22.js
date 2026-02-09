(() => {
  "use strict";
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const safe = (x) => (Number.isFinite(x) ? x : 0);

  function getPhysics() {
    const solver = globalThis.solver;
    if (solver?.nodes && solver?.edges) return solver;
    const p =
      globalThis.SOLDashboard?.state?.physics ??
      globalThis.App?.state?.physics ??
      globalThis.app?.state?.physics ??
      null;
    if (p?.nodes && p?.edges) return p;
    throw new Error("Physics not ready.");
  }

  function nodeByIdLoose(phy, id) {
    const asStr = String(id);
    const m = phy?.nodeById;
    if (m?.get) {
      let n = m.get(id);
      if (n) return n;
      n = m.get(asStr);
      if (n) return n;
    }
    return (phy.nodes || []).find((n) => String(n?.id) === asStr) || null;
  }

  function stepOnce(phy, dt = 0.12, pressC = 20, damping = 4) {
    if (typeof phy.step !== "function") return false;
    try { phy.step(dt, pressC, damping); return true; } catch (_) {}
    try { phy.step(dt); return true; } catch (_) {}
    try { phy.step(); return true; } catch (_) {}
    return false;
  }

  function strobePick(injectorIds, tick, strobeTicks) {
    const idx = Math.floor(tick / strobeTicks) % injectorIds.length;
    return injectorIds[idx];
  }

  function rhoMaxId(phy) {
    let best = -Infinity, bestId = "";
    for (const n of phy.nodes || []) {
      const r = safe(n?.rho);
      if (r > best) { best = r; bestId = String(n?.id ?? ""); }
    }
    return bestId;
  }

  function inject(phy, id, { injectP = 0, injectRho = 0, injectPsi = 0 }) {
    const n = nodeByIdLoose(phy, id);
    if (!n) return false;
    if (injectP && typeof n.p === "number") n.p += injectP;
    if (injectRho && typeof n.rho === "number") n.rho += injectRho;
    if (injectPsi && typeof n.psi === "number") n.psi += injectPsi;
    return true;
  }

  async function doLatchRun(cfg) {
    const {
      injectorIds = [82, 90],
      blocks = 6,
      strobeTicks = 10,
      dreamEveryMs = 100,
      injectP = 0,
      injectRho = 400,
      injectPsi = 0,

      restoreBaseline = true,

      stepPerTick = 0,
      stepDt = 0.12,
      pressC = 20,
      damping = 4,

      // postSteps happen AFTER we record t0
      postSteps = 0,
    } = cfg;

    const phy = getPhysics();

    if (restoreBaseline) {
      if (!globalThis.SOLBaseline?.restore) throw new Error("SOLBaseline.restore() missing.");
      await globalThis.SOLBaseline.restore();
    }

    const totalTicks = blocks * strobeTicks;

    for (let tick = 0; tick < totalTicks; tick++) {
      const id = strobePick(injectorIds, tick, strobeTicks);
      inject(phy, id, { injectP, injectRho, injectPsi });

      for (let k = 0; k < stepPerTick; k++) stepOnce(phy, stepDt, pressC, damping);

      // CRITICAL FIX: do NOT sleep after the final tick.
      if (tick < totalTicks - 1) await sleep(dreamEveryMs);
    }

    // TRUE t0 sample: immediately after dream stops (right after last injection)
    const startId_t0 = rhoMaxId(phy);

    for (let k = 0; k < postSteps; k++) stepOnce(phy, stepDt, pressC, damping);
    const startId_post = rhoMaxId(phy);

    return { startId_t0, startId_post };
  }

  const state = { calibrated: false, parityToStart: null, config: null };

  function reset() {
    state.calibrated = false;
    state.parityToStart = null;
    state.config = null;
    console.log("[LatchControllerV22] reset()");
  }

  async function calibrate(opts = {}) {
    const cfg = {
      injectorIds: [82, 90],
      strobeTicks: 10,
      dreamEveryMs: 100,
      blocksParity0: 5,
      blocksParity1: 6,
      injectP: 0,
      injectRho: 400,
      injectPsi: 0,
      restoreBaseline: true,

      stepPerTick: 1,
      stepDt: 0.12,
      pressC: 20,
      damping: 4,

      postSteps: 0,
      ...opts,
    };

    const r0 = await doLatchRun({ ...cfg, blocks: cfg.blocksParity0 });
    const r1 = await doLatchRun({ ...cfg, blocks: cfg.blocksParity1 });

    state.parityToStart = { 0: String(r0.startId_t0), 1: String(r1.startId_t0) };
    state.calibrated = true;
    state.config = cfg;

    console.log(`[LatchControllerV22] calibrated parity→start(t0): 0→${state.parityToStart[0]}, 1→${state.parityToStart[1]} (postSteps=${cfg.postSteps})`);
    console.log(`[LatchControllerV22] post-step starts: parity0→${r0.startId_post}, parity1→${r1.startId_post}`);
    return { ...state.parityToStart };
  }

  function parityForStartId(startId) {
    if (!state.calibrated) return null;
    const t = String(startId);
    if (state.parityToStart[0] === t) return 0;
    if (state.parityToStart[1] === t) return 1;
    return null;
  }

  async function selectMode(opts = {}) {
    const target = opts.target ?? "start90";
    const want = target === "start82" ? "82" : "90";

    if (!state.calibrated) await calibrate(opts);

    let p = parityForStartId(want);

    // If mapping doesn't include want, force recalibrate once
    if (p == null) {
      console.warn(`[LatchControllerV22] want ${want} not in mapping (0→${state.parityToStart[0]}, 1→${state.parityToStart[1]}). Recalibrating…`);
      reset();
      await calibrate(opts);
      p = parityForStartId(want);
      if (p == null) {
        console.warn(`[LatchControllerV22] still no ${want} after recalibrate. Giving up.`);
        return null;
      }
    }

    const cfg = state.config;
    const blocks = p === 0 ? cfg.blocksParity0 : cfg.blocksParity1;

    const r = await doLatchRun({ ...cfg, ...opts, blocks });

    // Self-heal: if observedStartId_t0 doesn't match want, recalibrate + retry once
    if (String(r.startId_t0) !== want) {
      console.warn(`[LatchControllerV22] mismatch: wanted ${want} but got ${r.startId_t0}. Recalibrating + retrying once…`);
      reset();
      await calibrate(opts);
      const p2 = parityForStartId(want);
      if (p2 == null) return null;
      const blocks2 = p2 === 0 ? state.config.blocksParity0 : state.config.blocksParity1;
      const r2 = await doLatchRun({ ...state.config, ...opts, blocks: blocks2 });
      console.log(`[LatchControllerV22] retry result: startId_t0=${r2.startId_t0} (want=${want}) parity=${p2}`);
      return { target, usedParity: p2, observedStartId_t0: r2.startId_t0, observedStartId_post: r2.startId_post };
    }

    console.log(`[LatchControllerV22] selectMode(${target}) → startId_t0=${r.startId_t0} (parity=${p}), startId_post=${r.startId_post}`);
    return { target, usedParity: p, observedStartId_t0: r.startId_t0, observedStartId_post: r.startId_post };
  }

  globalThis.solLatchControllerV22 = { reset, calibrate, selectMode, _state: state };

  // Optional: make existing watchers pick it up without edits
  globalThis.solLatchControllerV21 = globalThis.solLatchControllerV22;

  console.log("solLatchControllerV22 installed. (Also aliased to solLatchControllerV21 for watcher compatibility.)");
  console.log("Run: solLatchControllerV22.reset(); await solLatchControllerV22.calibrate({ postSteps:0 });");
})();
