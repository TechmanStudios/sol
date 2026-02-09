(() => {
  "use strict";

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const safe = (x) => (Number.isFinite(x) ? x : 0);

  function getRoot() {
    return globalThis.SOLDashboard ?? globalThis.App ?? globalThis.app ?? null;
  }

  function getPhysics() {
    const solver = globalThis.solver;
    if (solver?.nodes && solver?.edges) return solver;
    const root = getRoot();
    const physics = root?.state?.physics;
    if (!physics?.nodes) throw new Error("Physics not ready. Make sure the dashboard is running.");
    return physics;
  }

  function nodeById(physics, id) {
    const m = physics?.nodeById?.get?.(id);
    if (m) return m;
    return (physics.nodes || []).find((n) => n?.id === id) || null;
  }

  function rhoMaxId(physics) {
    let bestId = "";
    let best = -Infinity;
    for (const n of physics.nodes || []) {
      const r = safe(n?.rho);
      if (r > best) {
        best = r;
        bestId = String(n?.id ?? "");
      }
    }
    return bestId;
  }

  function applyInjection(physics, id, { injectP = 0, injectRho = 0, injectPsi = 0 }) {
    const n = nodeById(physics, id);
    if (!n) return false;
    if (typeof n.p === "number" && injectP) n.p += injectP;
    if (typeof n.rho === "number" && injectRho) n.rho += injectRho;
    if (typeof n.psi === "number" && injectPsi) n.psi += injectPsi;
    return true;
  }

  function strobePick(injectorIds, tick, strobeTicks) {
    const idx = Math.floor(tick / strobeTicks) % injectorIds.length;
    return injectorIds[idx];
  }

  async function doLatchRun({
    injectorIds,
    blocks,
    strobeTicks,
    dreamEveryMs,
    injectP,
    injectRho,
    injectPsi,
    restoreBaseline,
  }) {
    const physics = getPhysics();

    if (restoreBaseline) {
      if (!globalThis.SOLBaseline?.restore) throw new Error("SOLBaseline.restore() not found. Load baseline script first.");
      await globalThis.SOLBaseline.restore();
    }

    const totalTicks = blocks * strobeTicks;

    for (let tick = 0; tick < totalTicks; tick++) {
      const id = strobePick(injectorIds, tick, strobeTicks);
      applyInjection(physics, id, { injectP, injectRho, injectPsi });
      await sleep(dreamEveryMs);
    }

    // immediate sample
    return rhoMaxId(physics);
  }

  const state = {
    calibrated: false,
    parityToStart: null, // {0:"90", 1:"82"} etc
    config: null,
  };

  async function calibrate(opts = {}) {
    const {
      injectorIds = [82, 90],
      strobeTicks = 10,
      dreamEveryMs = 100,
      blocksParity0 = 5,
      blocksParity1 = 6,
      injectP = 0,
      injectRho = 400,
      injectPsi = 0,
      restoreBaseline = true,
    } = opts;

    const start0 = await doLatchRun({
      injectorIds,
      blocks: blocksParity0,
      strobeTicks,
      dreamEveryMs,
      injectP,
      injectRho,
      injectPsi,
      restoreBaseline,
    });

    const start1 = await doLatchRun({
      injectorIds,
      blocks: blocksParity1,
      strobeTicks,
      dreamEveryMs,
      injectP,
      injectRho,
      injectPsi,
      restoreBaseline,
    });

    // blocksParity0 => lastBlockIndex even => parity 0 (for 2 injectors)
    // blocksParity1 => lastBlockIndex odd  => parity 1
    state.parityToStart = { 0: String(start0), 1: String(start1) };
    state.calibrated = true;
    state.config = {
      injectorIds: injectorIds.slice(),
      strobeTicks,
      dreamEveryMs,
      blocksParity0,
      blocksParity1,
      injectP,
      injectRho,
      injectPsi,
      restoreBaseline,
    };

    console.log(`[LatchController] calibrated parity→start: 0→${state.parityToStart[0]}, 1→${state.parityToStart[1]}`);
    return { ...state.parityToStart };
  }

  function parityForTargetStart(targetStartId) {
    if (!state.calibrated) throw new Error("LatchController not calibrated. Run await solLatchControllerV1.calibrate() first.");
    const t = String(targetStartId);
    if (state.parityToStart[0] === t) return 0;
    if (state.parityToStart[1] === t) return 1;
    return null;
  }

  async function selectMode(opts = {}) {
    if (!state.calibrated) await calibrate(opts);

    const {
      target = "start90", // "start90" | "start82"
      restoreBaseline = state.config.restoreBaseline,
    } = opts;

    const wantStartId = target === "start82" ? "82" : "90";
    const p = parityForTargetStart(wantStartId);

    if (p == null) {
      console.warn(`[LatchController] Target ${wantStartId} not observed in calibration mapping. Returning null.`);
      return null;
    }

    const cfg = state.config;
    const blocks = p === 0 ? cfg.blocksParity0 : cfg.blocksParity1;

    const startId = await doLatchRun({
      injectorIds: cfg.injectorIds,
      blocks,
      strobeTicks: cfg.strobeTicks,
      dreamEveryMs: cfg.dreamEveryMs,
      injectP: cfg.injectP,
      injectRho: cfg.injectRho,
      injectPsi: cfg.injectPsi,
      restoreBaseline,
    });

    console.log(`[LatchController] selectMode(${target}) → observed start rhoMaxId_t0=${startId} (used parity=${p})`);
    return { target, usedParity: p, observedStartId: String(startId) };
  }

  globalThis.solLatchControllerV1 = {
    calibrate,
    selectMode,
    _state: state, // for inspection
  };

  console.log("solLatchControllerV1 installed.");
  console.log("Run: await solLatchControllerV1.calibrate()");
  console.log("Then: await solLatchControllerV1.selectMode({ target:'start90' })");
})();
