// Phase 3.11 — 16BI (restore-per-step) Phase-Lock Breaker Sweep
// Purpose: test whether tick8 “parity alternation” is a phase-locked 2-cycle caused by betweenRepTicks aliasing.
// Method: hold multB at a couple representative points, vary betweenRepTicks across conditions.
// Readout: winner_t8 vs an inferred alternation predictor (based on rep1), slip counts/rates.
// UI-neutral: NO camera/graph motion calls. Injects by direct node rho only.
// Exports:
//   - MASTER_summary.csv
//   - MASTER_busTrace.csv
//   - condition_phaseLock_summary.csv  (derived per {cond,dir,multB})
//
// Notes:
// - Uses restore-per-step baseline, modeSelect once per step, directional precondition once per step.
// - Keeps dampUsed fixed at 20 (the “interesting” band).
// - Designed to be quick + decisive (few multB points, multiple betweenRepTicks).

(async () => {
  "use strict";

  const CFG = {
    expId: "sol_phase311_16bi_phaseLockBreakerSweep_v1",

    // Representative points inside the parity-lock zone (from 16BH region)
    multBPoints: [0.9850, 0.9870],

    // Conditions to test aliasing / phase drift
    betweenRepTicksList: [80, 81, 82, 100, 160],

    repsPerCondition: 121, // odd on purpose (breaks forced 50/50 if perfect alternation persists)
    segmentTicks: 121,

    dt: 0.12,
    pressCBase: null,
    dampUsed: 20,
    markerTick: 8,

    // Directional precondition ONCE per step (same family as 16BE–16BH)
    preLow_multB: 0.90,
    preLow_ticks: 320,
    preHigh_multB: 1.08,
    preHigh_ticks: 320,

    // Mode select ONCE per step
    wantId: 82,
    injectorIds: [90, 82],
    dreamBlocks: 15,
    dreamBlockSteps: 2,
    injectAmount: 120,
    finalWriteMult: 1,

    // Amps
    baseAmpB: 4.0,
    baseAmpD: 5.75,
    gain: 22,
    multD: 1.0,

    // Injection order / handshake (B2 order)
    injectTick136: 0,
    injectTick114: 1,
    handshakeTick: 2,
    nudgeMult: 0.20,

    // Capture
    captureStreak: 5,
    captureStartTick: 5,

    includeBackgroundEdges: false,
    abortOnNonFinite: true,
  };

  // ----------------------------
  // Utilities
  // ----------------------------
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const p2 = (n) => String(n).padStart(2, "0");
  const p3 = (n) => String(n).padStart(3, "0");
  const isoTag = (d = new Date()) =>
    `${d.getUTCFullYear()}-${p2(d.getUTCMonth() + 1)}-${p2(d.getUTCDate())}` +
    `T${p2(d.getUTCHours())}-${p2(d.getUTCMinutes())}-${p2(d.getUTCSeconds())}-${p3(d.getUTCMilliseconds())}Z`;

  const csvCell = (v) => {
    if (v === null || v === undefined) return "";
    const s = String(v);
    return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const csvRow = (cols) => cols.map(csvCell).join(",") + "\n";

  const downloadText = (filename, text) => {
    const blob = new Blob([text], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => { try { URL.revokeObjectURL(url); } catch (e) {} }, 250);
  };

  const getApp = () => window.SOLDashboard || window.solDashboard || window.App || window.app || null;

  const waitForPhysics = async (timeoutMs = 15000, pollMs = 50) => {
    const t0 = performance.now();
    while (performance.now() - t0 < timeoutMs) {
      const app = getApp();
      const phy =
        (window.solver && window.solver.nodes && window.solver.edges) ? window.solver :
        (app && app.state && app.state.physics) ? app.state.physics :
        (app && app.state && app.state.physics && app.state.physics.network) ? app.state.physics.network :
        null;
      if (phy?.nodes?.length && phy?.edges?.length && typeof phy.step === "function") return phy;
      await sleep(pollMs);
    }
    throw new Error("[16BI] timed out waiting for physics.");
  };

  const freezeLiveLoop = () => {
    const app = getApp();
    if (!app?.config) throw new Error("[16BI] App not ready.");
    if (freezeLiveLoop._prevDtCap === undefined) freezeLiveLoop._prevDtCap = app.config.dtCap;
    app.config.dtCap = 0;
  };

  const unfreezeLiveLoop = () => {
    const app = getApp();
    if (!app?.config) return;
    if (freezeLiveLoop._prevDtCap !== undefined) {
      app.config.dtCap = freezeLiveLoop._prevDtCap;
      freezeLiveLoop._prevDtCap = undefined;
    }
  };

  const readUiPressC = () => {
    const app = getApp();
    const pressC = (app?.dom?.pressureSlider)
      ? (parseFloat(String(app.dom.pressureSlider.value)) * (app.config.pressureSliderScale || 1))
      : null;
    return Number.isFinite(pressC) ? pressC : null;
  };

  const nodeById = (phy, id) => {
    const want = String(id);
    for (const n of (phy.nodes || [])) if (n?.id != null && String(n.id) === want) return n;
    return null;
  };

  const injectRho = (phy, id, amt) => {
    const n = nodeById(phy, id);
    if (!n) throw new Error(`[16BI] node not found: ${id}`);
    const a = Math.max(0, Number(amt) || 0);
    n.rho += a;
    try {
      if (n.isConstellation && typeof phy.reinforceSemanticStar === "function") {
        phy.reinforceSemanticStar(n, (a / 50.0));
      }
    } catch (e) {}
  };

  const buildEdgeIndex = (phy) => {
    const map = new Map();
    const edges = phy.edges || [];
    for (let i = 0; i < edges.length; i++) {
      const e = edges[i];
      if (!e) continue;
      map.set(`${e.from}->${e.to}`, i);
    }
    return map;
  };

  const edgeFlux = (phy, idx) => {
    if (idx == null) return 0;
    const e = (phy.edges || [])[idx];
    const f = (e && typeof e.flux === "number" && Number.isFinite(e.flux)) ? e.flux : 0;
    return f;
  };

  const top2Edges = (phy, includeBackgroundEdges) => {
    const edges = phy.edges || [];
    let best1 = { af: -1, from: "", to: "", flux: 0 };
    let best2 = { af: -1, from: "", to: "", flux: 0 };
    for (let i = 0; i < edges.length; i++) {
      const e = edges[i];
      if (!e) continue;
      if (!includeBackgroundEdges && e.background) continue;
      const f = (typeof e.flux === "number" && Number.isFinite(e.flux)) ? e.flux : 0;
      const af = Math.abs(f);
      if (af > best1.af) {
        best2 = best1;
        best1 = { af, from: e.from, to: e.to, flux: f };
      } else if (af > best2.af) {
        best2 = { af, from: e.from, to: e.to, flux: f };
      }
    }
    return { best1, best2 };
  };

  const entropyFromCounts = (countsMap) => {
    let total = 0;
    for (const v of countsMap.values()) total += v;
    if (total <= 0) return 0;
    let H = 0;
    for (const v of countsMap.values()) {
      const p = v / total;
      if (p > 0) H -= p * (Math.log(p) / Math.log(2));
    }
    return H;
  };

  const captureTick = (domSeq, who, streak, startTick) => {
    let run = 0;
    for (let i = Math.max(0, startTick | 0); i < domSeq.length; i++) {
      if (domSeq[i] === who) {
        run++;
        if (run >= streak) return i - streak + 1;
      } else run = 0;
    }
    return "";
  };

  const isFiniteNums = (nums) => nums.every((v) => typeof v === "number" && Number.isFinite(v));

  const recomputeDerived = async (dt) => {
    try {
      if (window.SOLRuntime?.recomputeDerived) return await window.SOLRuntime.recomputeDerived({ dt });
    } catch (e) {}
    try {
      const app = getApp();
      if (app?.sim?.recomputeDerivedFields) {
        const r = app.sim.recomputeDerivedFields((await waitForPhysics()), { dt });
        return { capLawHash: r?.capLawHash ?? "" };
      }
    } catch (e) {}
    return { capLawHash: "" };
  };

  // ----------------------------
  // Baseline restore (snapshot fallback)
  // ----------------------------
  const makeInternalSnapshot = (phy) => {
    const nodes = (phy.nodes || []).map((n) => [String(n.id), {
      rho: n.rho, p: n.p, psi: n.psi, psi_bias: n.psi_bias,
      semanticMass: n.semanticMass, semanticMass0: n.semanticMass0,
      b_q: n.b_q, b_charge: n.b_charge, b_state: n.b_state,
      x: n.x, y: n.y, vx: n.vx, vy: n.vy, fx: n.fx, fy: n.fy
    }]);
    const edges = (phy.edges || []).map((e, i) => [i, { flux: e?.flux }]);
    return { nodes, edges, t: (phy._t ?? 0), globalBias: (("globalBias" in phy) ? phy.globalBias : undefined) };
  };

  const restoreInternalSnapshot = (phy, snap) => {
    const nMap = new Map(snap.nodes);
    for (const n of (phy.nodes || [])) {
      const s = nMap.get(String(n.id));
      if (!s) continue;
      for (const k in s) { try { n[k] = s[k]; } catch (e) {} }
    }
    const eMap = new Map(snap.edges);
    for (let i = 0; i < (phy.edges || []).length; i++) {
      const s = eMap.get(i);
      if (!s) continue;
      try { phy.edges[i].flux = s.flux; } catch (e) {}
    }
    try { if ("_t" in phy) phy._t = snap.t || 0; } catch (e) {}
    try { if ("globalBias" in phy && snap.globalBias !== undefined) phy.globalBias = snap.globalBias; } catch (e) {}
  };

  const ensureBaselineIfAvailable = async () => {
    if (!window.SOLBaseline?.ensure) return;
    try { await window.SOLBaseline.ensure({ force: false, exportJson: false }); }
    catch (e) { console.warn("[16BI] SOLBaseline.ensure failed (continuing):", e); }
  };

  const baselineRestore = async (phy, ctx) => {
    if (window.SOLBaseline?.restore) {
      await window.SOLBaseline.restore();
      return "SOLBaseline.restore";
    }
    if (!ctx._snap) ctx._snap = makeInternalSnapshot(phy);
    restoreInternalSnapshot(phy, ctx._snap);
    return "internal_snapshot_restored";
  };

  // ----------------------------
  // Mode select + per-step precondition
  // ----------------------------
  const modeSelectOnce = async (phy, cfg, pressC, damp) => {
    let idx = 0;
    for (let b = 0; b < Math.max(0, cfg.dreamBlocks - 1); b++) {
      const injId = cfg.injectorIds[idx % cfg.injectorIds.length];
      idx++;
      injectRho(phy, injId, cfg.injectAmount);
      for (let s = 0; s < cfg.dreamBlockSteps; s++) phy.step(cfg.dt, pressC, damp);
    }
    injectRho(phy, cfg.wantId, cfg.injectAmount * (cfg.finalWriteMult || 1));
    try { if (typeof phy.computePressure === "function") phy.computePressure(pressC); } catch (e) {}
  };

  // ----------------------------
  // Phase-lock analytics helpers
  // ----------------------------
  const invertWinner = (w) => (w === 114 ? 136 : (w === 136 ? 114 : 0));

  const phasePredictorFromFirst = (firstWinner, repIndex1Based) => {
    // Perfect alternation model: rep1 = firstWinner, rep2 = other, rep3 = firstWinner, ...
    if (firstWinner !== 114 && firstWinner !== 136) return 0;
    return (repIndex1Based % 2 === 1) ? firstWinner : invertWinner(firstWinner);
  };

  const longestSameWinnerStreak = (winners) => {
    // winners is array of ints (114/136/0)
    let best = 0, run = 0, prev = null;
    for (const w of winners) {
      if (w !== 0 && w === prev) run++;
      else run = (w === 0 ? 0 : 1);
      if (run > best) best = run;
      prev = w;
    }
    return best;
  };

  // ----------------------------
  // Runner
  // ----------------------------
  const Runner = {
    stopFlag: false,
    stop() { this.stopFlag = true; },

    async run(userCfg = {}) {
      this.stopFlag = false;
      const cfg = { ...CFG, ...userCfg };

      const phy = await waitForPhysics();
      freezeLiveLoop();
      await ensureBaselineIfAvailable();

      const uiPressC = readUiPressC();
      const invPressC = window.SOLRuntime?.getInvariants?.()?.pressC;
      const pressCUsed = (cfg.pressCBase != null) ? cfg.pressCBase : (invPressC ?? uiPressC ?? 2.0);

      const baseB = cfg.baseAmpB * cfg.gain;
      const baseD = cfg.baseAmpD * cfg.gain;
      const ampD = baseD * cfg.multD;

      const startTag = isoTag(new Date());
      const runTag = `${cfg.expId}_${startTag}`;
      const ctx = { _snap: null };

      const edgeIndex = buildEdgeIndex(phy);
      const i114_89 = edgeIndex.get("114->89");
      const i114_79 = edgeIndex.get("114->79");
      const i136_89 = edgeIndex.get("136->89");
      const i136_79 = edgeIndex.get("136->79");

      const summaryHeader = [
        "schema","runTag",
        "condIndex","betweenRepTicks",
        "dir","multBUsed","rep",
        "pressCUsed","dampUsed","capLawHash",
        "ampB0","ampD","ratioBD",
        "peakAbs114_bus","peakAbs136_bus","winner_peakBus",
        "t8_abs114_bus","t8_abs136_bus","winner_t8",
        "t8_pred_alt","t8_slip_alt",
        "laneEdge","laneEdge_count","laneEntropy_bits","max1_switchCount",
        "fracTicks_busDom114","fracTicks_busDom136","busDomEntropy_bits","busDom_switchCount",
        "captureTick_114","captureTick_136",
        "baselineModeUsed"
      ];

      const traceHeader = [
        "schema","runTag",
        "condIndex","betweenRepTicks",
        "dir","multBUsed","rep","tick",
        "max1_from","max1_to","max1_absFlux",
        "max2_from","max2_to","max2_absFlux",
        "flux_114_89","flux_114_79","flux_136_89","flux_136_79",
        "abs114_bus","abs136_bus","busDom"
      ];

      const phaseHeader = [
        "schema","runTag",
        "condIndex","betweenRepTicks",
        "dir","multBUsed",
        "n",
        "p114_t8",
        "firstWinner_t8",
        "slips_alt","slipRate_alt",
        "longestSameWinnerStreak_t8",
        "cap114_rate","cap136_rate",
        "median_captureTick_114","median_captureTick_136",
        "mean_fracTicks_busDom114","mean_fracTicks_busDom136",
        "mean_busDom_switchCount",
        "baselineModeUsed"
      ];

      const summaryLines = [csvRow(summaryHeader)];
      const traceLines = [csvRow(traceHeader)];
      const phaseLines = [csvRow(phaseHeader)];

      // Simple median helper
      const median = (arr) => {
        const xs = arr.filter((v) => Number.isFinite(v)).slice().sort((a,b)=>a-b);
        if (!xs.length) return "";
        const m = Math.floor(xs.length / 2);
        return (xs.length % 2 === 1) ? xs[m] : (0.5 * (xs[m-1] + xs[m]));
      };

      const runPrecondition = async (multBUsed, ticks) => {
        const ampB0 = baseB * multBUsed;
        const ampB_nudge = ampB0 * cfg.nudgeMult;
        for (let t = 0; t < ticks; t++) {
          if (this.stopFlag) break;
          if (t === cfg.injectTick136) injectRho(phy, 136, ampD);
          if (t === cfg.injectTick114) injectRho(phy, 114, ampB0);
          if (t === cfg.handshakeTick && ampB_nudge > 0) injectRho(phy, 114, ampB_nudge);
          phy.step(cfg.dt, pressCUsed, cfg.dampUsed);
        }
      };

      const runOneTrial = async (condIndex, betweenRepTicks, dirTag, multBUsed, rep, baselineModeUsed, firstWinnerRef) => {
        const cap = await recomputeDerived(cfg.dt);

        const ampB0 = baseB * multBUsed;
        const ratioBD = ampB0 / ampD;
        const ampB_nudge = ampB0 * cfg.nudgeMult;

        let peakAbs114 = 0, peakAbs136 = 0;
        let t8_abs114 = "", t8_abs136 = "";

        const laneCounts = new Map();
        const busDomCounts = new Map([["114", 0], ["136", 0], ["tie", 0]]);
        const busDomSeq = [];

        let prevMax1 = "";
        let max1_switchCount = 0;

        let prevBusDom = "";
        let bus_switchCount = 0;

        let aborted = false;

        for (let tick = 0; tick < cfg.segmentTicks; tick++) {
          if (this.stopFlag) break;

          if (tick === cfg.injectTick136) injectRho(phy, 136, ampD);
          if (tick === cfg.injectTick114) injectRho(phy, 114, ampB0);
          if (tick === cfg.handshakeTick && ampB_nudge > 0) injectRho(phy, 114, ampB_nudge);

          phy.step(cfg.dt, pressCUsed, cfg.dampUsed);

          const top2 = top2Edges(phy, cfg.includeBackgroundEdges);
          const max1Pair = `${top2.best1.from}->${top2.best1.to}`;
          laneCounts.set(max1Pair, (laneCounts.get(max1Pair) || 0) + 1);
          if (prevMax1 && max1Pair !== prevMax1) max1_switchCount++;
          prevMax1 = max1Pair;

          const f114_89 = edgeFlux(phy, i114_89);
          const f114_79 = edgeFlux(phy, i114_79);
          const f136_89 = edgeFlux(phy, i136_89);
          const f136_79 = edgeFlux(phy, i136_79);

          const abs114 = Math.max(Math.abs(f114_89), Math.abs(f114_79));
          const abs136 = Math.max(Math.abs(f136_89), Math.abs(f136_79));

          if (cfg.abortOnNonFinite) {
            const ok = isFiniteNums([top2.best1.af, top2.best2.af, f114_89, f114_79, f136_89, f136_79, abs114, abs136]);
            if (!ok) { aborted = true; break; }
          }

          if (abs114 > peakAbs114) peakAbs114 = abs114;
          if (abs136 > peakAbs136) peakAbs136 = abs136;

          if (tick === cfg.markerTick) { t8_abs114 = abs114; t8_abs136 = abs136; }

          const busDom = (abs114 > abs136) ? "114" : (abs136 > abs114) ? "136" : "tie";
          busDomSeq.push(busDom);
          busDomCounts.set(busDom, (busDomCounts.get(busDom) || 0) + 1);

          if (prevBusDom && busDom !== prevBusDom) bus_switchCount++;
          prevBusDom = busDom;

          traceLines.push(csvRow([
            cfg.expId, runTag,
            condIndex, betweenRepTicks,
            dirTag, multBUsed, rep, tick,
            top2.best1.from, top2.best1.to, top2.best1.af,
            top2.best2.from, top2.best2.to, top2.best2.af,
            f114_89, f114_79, f136_89, f136_79,
            abs114, abs136, busDom
          ]));
        }

        const winner_peakBus = (peakAbs114 > peakAbs136) ? 114 : (peakAbs136 > peakAbs114) ? 136 : 0;
        const winner_t8 = (t8_abs114 === "" || t8_abs136 === "") ? 0 : (t8_abs114 > t8_abs136) ? 114 : (t8_abs136 > t8_abs114) ? 136 : 0;

        // Establish alternation model from rep1 (per {cond,dir,multB})
        if (rep === 1) firstWinnerRef.value = winner_t8;
        const t8_pred = phasePredictorFromFirst(firstWinnerRef.value, rep);
        const t8_slip = (winner_t8 !== t8_pred) ? 1 : 0;

        let laneEdge = "", laneEdge_count = -1;
        for (const [k, v] of laneCounts.entries()) if (v > laneEdge_count) { laneEdge = k; laneEdge_count = v; }
        const laneEntropy = entropyFromCounts(laneCounts);

        const ticksTotal = busDomSeq.length || 1;
        const fracBus114 = (busDomCounts.get("114") || 0) / ticksTotal;
        const fracBus136 = (busDomCounts.get("136") || 0) / ticksTotal;
        const busEntropy = entropyFromCounts(busDomCounts);

        const cap114 = captureTick(busDomSeq, "114", cfg.captureStreak, cfg.captureStartTick);
        const cap136 = captureTick(busDomSeq, "136", cfg.captureStreak, cfg.captureStartTick);

        summaryLines.push(csvRow([
          cfg.expId, runTag,
          condIndex, betweenRepTicks,
          dirTag, multBUsed, rep,
          pressCUsed, cfg.dampUsed, (cap.capLawHash ?? ""),
          (baseB * multBUsed), ampD, ((baseB * multBUsed) / ampD),
          peakAbs114, peakAbs136, winner_peakBus,
          t8_abs114, t8_abs136, winner_t8,
          t8_pred, t8_slip,
          laneEdge, laneEdge_count, laneEntropy, max1_switchCount,
          fracBus114, fracBus136, busEntropy, bus_switchCount,
          cap114, cap136,
          baselineModeUsed
        ]));

        return {
          aborted,
          winner_t8,
          t8_slip,
          cap114_present: (cap114 !== ""),
          cap136_present: (cap136 !== ""),
          cap114_tick: (cap114 === "" ? NaN : Number(cap114)),
          cap136_tick: (cap136 === "" ? NaN : Number(cap136)),
          fracBus114,
          fracBus136,
          bus_switchCount
        };
      };

      const runOneStep = async (condIndex, betweenRepTicks, dirTag, multBUsed) => {
        if (this.stopFlag) return;

        // Restore-per-step
        const baselineModeUsed = await baselineRestore(phy, ctx);

        // Mode select once
        await modeSelectOnce(phy, cfg, pressCUsed, cfg.dampUsed);

        // Directional precondition once
        if (dirTag === "up") await runPrecondition(cfg.preLow_multB, cfg.preLow_ticks);
        else await runPrecondition(cfg.preHigh_multB, cfg.preHigh_ticks);

        // Trial loop for this step
        const firstWinnerRef = { value: 0 };

        let n = 0, n114 = 0;
        let slips = 0;
        const t8Winners = [];
        let cap114_count = 0, cap136_count = 0;
        const cap114_ticks = [];
        const cap136_ticks = [];
        let sumFrac114 = 0, sumFrac136 = 0;
        let sumBusSwitch = 0;

        for (let rep = 1; rep <= cfg.repsPerCondition; rep++) {
          if (this.stopFlag) break;

          const r = await runOneTrial(condIndex, betweenRepTicks, dirTag, multBUsed, rep, baselineModeUsed, firstWinnerRef);
          if (r?.aborted) break;

          n++;
          if (r.winner_t8 === 114) n114++;
          slips += r.t8_slip;

          t8Winners.push(r.winner_t8);

          if (r.cap114_present) { cap114_count++; cap114_ticks.push(r.cap114_tick); }
          if (r.cap136_present) { cap136_count++; cap136_ticks.push(r.cap136_tick); }

          sumFrac114 += (Number.isFinite(r.fracBus114) ? r.fracBus114 : 0);
          sumFrac136 += (Number.isFinite(r.fracBus136) ? r.fracBus136 : 0);
          sumBusSwitch += (Number.isFinite(r.bus_switchCount) ? r.bus_switchCount : 0);

          // Relax stride (between reps)
          for (let k = 0; k < betweenRepTicks; k++) {
            if (this.stopFlag) break;
            phy.step(cfg.dt, pressCUsed, cfg.dampUsed);
          }
        }

        const p114_t8 = n ? (n114 / n) : "";
        const slipRate = n ? (slips / n) : "";
        const firstWinner = (t8Winners.length ? t8Winners[0] : 0);
        const streakSame = longestSameWinnerStreak(t8Winners);

        phaseLines.push(csvRow([
          cfg.expId, runTag,
          condIndex, betweenRepTicks,
          dirTag, multBUsed,
          n,
          p114_t8,
          firstWinner,
          slips, slipRate,
          streakSame,
          (n ? (cap114_count / n) : ""),
          (n ? (cap136_count / n) : ""),
          median(cap114_ticks),
          median(cap136_ticks),
          (n ? (sumFrac114 / n) : ""),
          (n ? (sumFrac136 / n) : ""),
          (n ? (sumBusSwitch / n) : ""),
          baselineModeUsed
        ]));
      };

      console.log(`\n[${cfg.expId}] START @ ${startTag}`);
      console.log(`[${cfg.expId}] pressCUsed=${pressCUsed} dampUsed=${cfg.dampUsed} dt=${cfg.dt}`);
      console.log(`[${cfg.expId}] multBPoints=${JSON.stringify(cfg.multBPoints)} betweenRepTicksList=${JSON.stringify(cfg.betweenRepTicksList)} repsPerCondition=${cfg.repsPerCondition}`);

      // Main experiment grid
      for (let c = 0; c < cfg.betweenRepTicksList.length; c++) {
        if (this.stopFlag) break;
        const betweenRepTicks = cfg.betweenRepTicksList[c];
        console.log(`\n[${cfg.expId}] COND ${c} betweenRepTicks=${betweenRepTicks}`);

        for (const multBUsed of cfg.multBPoints) {
          if (this.stopFlag) break;

          console.log(`[${cfg.expId}]  multB=${multBUsed} dir=up`);
          await runOneStep(c, betweenRepTicks, "up", multBUsed);

          console.log(`[${cfg.expId}]  multB=${multBUsed} dir=down`);
          await runOneStep(c, betweenRepTicks, "down", multBUsed);
        }
      }

      const endTag = isoTag(new Date());
      const baseName = `${cfg.expId}_${startTag}_${endTag}`;
      unfreezeLiveLoop();

      downloadText(`${baseName}_MASTER_summary.csv`, summaryLines.join(""));
      downloadText(`${baseName}_MASTER_busTrace.csv`, traceLines.join(""));
      downloadText(`${baseName}_condition_phaseLock_summary.csv`, phaseLines.join(""));

      console.log(`\n[${cfg.expId}] DONE @ ${endTag}`);
      console.log(`- ${baseName}_MASTER_summary.csv`);
      console.log(`- ${baseName}_MASTER_busTrace.csv`);
      console.log(`- ${baseName}_condition_phaseLock_summary.csv`);
      return { expId: cfg.expId, baseName, pressCUsed, dampUsed: cfg.dampUsed, stopped: this.stopFlag };
    }
  };

  window.solPhase311_16bi_phaseLockBreakerSweep_v1 = Runner;
  console.log("✅ Installed: solPhase311_16bi_phaseLockBreakerSweep_v1");
  await Runner.run();

})();
