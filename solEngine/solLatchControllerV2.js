(() => {
  "use strict";
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const safe = (x) => (Number.isFinite(x) ? x : 0);

  function getPhysics() {
    const solver = globalThis.solver;
    if (solver?.nodes && solver?.edges) return solver;
    const p = globalThis.SOLDashboard?.state?.physics ?? globalThis.App?.state?.physics ?? globalThis.app?.state?.physics;
    if (p?.nodes && p?.edges) return p;
    throw new Error("Physics not ready.");
  }

  function nodeById(phy, id) {
    const m = phy?.nodeById?.get?.(id);
    if (m) return m;
    return (phy.nodes || []).find((n) => n?.id === id) || null;
  }

  function stepOnce(phy, dt=0.12, pressC=20, damping=4) {
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

  function inject(phy, id, { injectP=0, injectRho=0, injectPsi=0 }) {
    const n = nodeById(phy, id);
    if (!n) return false;
    if (injectP && typeof n.p === "number") n.p += injectP;
    if (injectRho && typeof n.rho === "number") n.rho += injectRho;
    if (injectPsi && typeof n.psi === "number") n.psi += injectPsi;
    return true;
  }

  async function doLatchRun(cfg) {
    const {
      injectorIds=[82,90],
      blocks=6,
      strobeTicks=10,
      dreamEveryMs=100,
      injectP=0,
      injectRho=400,
      injectPsi=0,

      restoreBaseline=true,

      // NEW: stepping control (so it works even if dashboard loop is paused)
      stepPerTick=0,
      stepDt=0.12,
      pressC=20,
      damping=4,
      postSteps=0,
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

      await sleep(dreamEveryMs);
    }

    for (let k = 0; k < postSteps; k++) stepOnce(phy, stepDt, pressC, damping);

    return rhoMaxId(phy);
  }

  const state = { calibrated:false, parityToStart:null, config:null };

  async function calibrate(opts={}) {
    const cfg = {
      injectorIds:[82,90],
      strobeTicks:10,
      dreamEveryMs:100,
      blocksParity0:5,
      blocksParity1:6,
      injectP:0,
      injectRho:400,
      injectPsi:0,
      restoreBaseline:true,

      stepPerTick:0,
      stepDt:0.12,
      pressC:20,
      damping:4,
      postSteps:0,
      ...opts,
    };

    const start0 = await doLatchRun({ ...cfg, blocks: cfg.blocksParity0 });
    const start1 = await doLatchRun({ ...cfg, blocks: cfg.blocksParity1 });

    state.parityToStart = { 0:String(start0), 1:String(start1) };
    state.calibrated = true;
    state.config = cfg;

    console.log(`[LatchControllerV2] calibrated parity→start: 0→${state.parityToStart[0]}, 1→${state.parityToStart[1]}`);
    return { ...state.parityToStart };
  }

  function parityForStartId(startId) {
    if (!state.calibrated) throw new Error("Not calibrated.");
    const t = String(startId);
    if (state.parityToStart[0] === t) return 0;
    if (state.parityToStart[1] === t) return 1;
    return null;
  }

  async function selectMode(opts={}) {
    if (!state.calibrated) await calibrate(opts);

    const target = opts.target ?? "start90";
    const want = target === "start82" ? "82" : "90";
    const p = parityForStartId(want);

    if (p == null) {
      console.warn(`[LatchControllerV2] target ${want} not in mapping (0→${state.parityToStart[0]}, 1→${state.parityToStart[1]}).`);
      return null;
    }

    const cfg = state.config;
    const blocks = (p === 0) ? cfg.blocksParity0 : cfg.blocksParity1;

    const observed = await doLatchRun({
      ...cfg,
      ...opts,
      blocks,
    });

    console.log(`[LatchControllerV2] selectMode(${target}) → observed start rhoMaxId_t0=${observed} (used parity=${p})`);
    return { target, usedParity:p, observedStartId:String(observed) };
  }

  globalThis.solLatchControllerV2 = { calibrate, selectMode, _state: state };
  console.log("solLatchControllerV2 installed.");
  console.log("Run: await solLatchControllerV2.calibrate({ stepPerTick: 1, postSteps: 20 })");
})();
