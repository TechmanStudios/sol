// Phase 3.11 — Batch runner: 16BN10 + 16BN11A + 16BN11B + 16BN12
//
// 16BN10: BN9 protocol but M1 (odd prime) @ segmentTicks=201, multB band 0.96575→0.96700 step 0.00025
// 16BN11A: BN9 protocol, M0, but betweenRepTicks_hold=400 (tests cross-rep memory sensitivity)
// 16BN11B: BN9 protocol, M0, but HARD "restore per rep" (each rep re-baselines + re-preconditions)
// 16BN12: segmentTicks sweep {121,161,201,241} at multB=0.96625 (M0), to see whether the late flip tick is intrinsic
//
// Exports per subrun:
//   - *_MASTER_summary.csv
//   - *_MASTER_busTrace.csv
//   - *_curve.csv   (name differs by subrun)
//
// UI-neutral: NO camera/graph motion calls. Only direct node rho injection + physics stepping.

(async () => {
  "use strict";

  // ---------- Shared defaults ----------
  const DEFAULTS = {
    dt: 0.12,
    pressCBase: null,
    dampUsed: 20,

    // capture definition
    captureStreak: 5,
    captureStartTick: 5,
    lateStartTick: 120, // for "late flip" detection within long windows

    // read ticks (long window)
    readTicks: [10, 11, 12, 13, 14, 16, 18, 20],

    // precondition
    preLow_multB: 0.90,
    preLow_ticks: 320,
    preHigh_multB: 1.08,
    preHigh_ticks: 320,

    // mode select
    wantId: 82,
    injectorIds: [90, 82],
    dreamBlocks: 15,
    dreamBlockSteps: 2,
    injectAmount: 120,
    finalWriteMult: 1,

    // amplitudes
    baseAmpB: 4.0,
    baseAmpD: 5.75,
    gain: 22,
    multD: 1.0,

    // injection order
    injectTick136: 0,
    injectTick114: 1,
    handshakeTick: 2,
    nudgeMult: 0.20,

    includeBackgroundEdges: false,
    abortOnNonFinite: true,

    // idle timing
    betweenRepTicks_toggle: 80,
    betweenRepTicks_hold: 81
  };

  // ---------- Subruns ----------
  const makeSweep = (start, end, step) => {
    const xs = [];
    if (step === 0) throw new Error("step=0");
    const dir = Math.sign(step);
    let x = start;
    for (let k = 0; k < 5000; k++) {
      xs.push(Math.round(x * 100000) / 100000);
      x = x + step;
      if ((dir > 0 && x > end + 1e-12) || (dir < 0 && x < end - 1e-12)) break;
    }
    return xs.map(v => Math.round(v * 100000) / 100000);
  };

  const BAND = makeSweep(0.96575, 0.96700, 0.00025);

  const SUBRUNS = [
    // 16BN10
    {
      expId: "sol_phase311_16bn10_segmentExtend_M1_window_v1",
      curveName: "inversionTime_longWindow_curve",
      modeLabel: "M1_togglePrime",
      primeCount: 1,
      segmentTicks: 201,
      multBList: BAND,
      dirs: ["up", "down"],
      repsPerStep: 80,
      betweenRepTicks_hold: 81,
      restorePerRep: false
    },

    // 16BN11A
    {
      expId: "sol_phase311_16bn11a_hold400_M0_segmentExtend_v1",
      curveName: "inversionTime_longWindow_curve",
      modeLabel: "M0_noPrime",
      primeCount: 0,
      segmentTicks: 201,
      multBList: BAND,
      dirs: ["up", "down"],
      repsPerStep: 80,
      betweenRepTicks_hold: 400,
      restorePerRep: false
    },

    // 16BN11B
    {
      expId: "sol_phase311_16bn11b_restorePerRep_M0_segmentExtend_v1",
      curveName: "inversionTime_longWindow_curve",
      modeLabel: "M0_noPrime",
      primeCount: 0,
      segmentTicks: 201,
      multBList: BAND,
      dirs: ["up", "down"],
      repsPerStep: 80,
      betweenRepTicks_hold: 0, // irrelevant when restorePerRep=true
      restorePerRep: true
    },

    // 16BN12
    {
      expId: "sol_phase311_16bn12_segmentTicksSweep_M0_v1",
      curveName: "segmentTicks_sweep_curve",
      modeLabel: "M0_noPrime",
      primeCount: 0,
      segmentTicksList: [121, 161, 201, 241],
      multBList: [0.96625],
      dirs: ["up", "down"],
      repsPerStep: 80,
      betweenRepTicks_hold: 81,
      restorePerRep: false
    }
  ];

  // ---------- Utilities ----------
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
    throw new Error("[BN batch] timed out waiting for physics.");
  };

  const freezeLiveLoop = () => {
    const app = getApp();
    if (!app?.config) throw new Error("[BN batch] App not ready.");
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
    if (!n) throw new Error(`[BN batch] node not found: ${id}`);
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
      if (af > best1.af) { best2 = best1; best1 = { af, from: e.from, to: e.to, flux: f }; }
      else if (af > best2.af) { best2 = { af, from: e.from, to: e.to, flux: f }; }
    }
    return { best1, best2 };
  };

  const isFiniteNums = (nums) => nums.every((v) => typeof v === "number" && Number.isFinite(v));

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
      if (domSeq[i] === who) { run++; if (run >= streak) return i - streak + 1; }
      else run = 0;
    }
    return "";
  };

  const recomputeDerived = async (dt) => {
    try { if (window.SOLRuntime?.recomputeDerived) return await window.SOLRuntime.recomputeDerived({ dt }); }
    catch (e) {}
    return { capLawHash: "" };
  };

  const relax = async (phy, cfg, pressC, nTicks) => {
    for (let k = 0; k < Math.max(0, nTicks | 0); k++) phy.step(cfg.dt, pressC, cfg.dampUsed);
  };

  // ---------- Baseline restore (snapshot fallback) ----------
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
    catch (e) { console.warn("[BN batch] SOLBaseline.ensure failed (continuing):", e); }
  };

  const baselineRestore = async (phy, ctx) => {
    if (window.SOLBaseline?.restore) { await window.SOLBaseline.restore(); return "SOLBaseline.restore"; }
    if (!ctx._snap) ctx._snap = makeInternalSnapshot(phy);
    restoreInternalSnapshot(phy, ctx._snap);
    return "internal_snapshot_restored";
  };

  // ---------- Mode select + precondition ----------
  const modeSelectOnce = async (phy, cfg, pressC) => {
    let idx = 0;
    for (let b = 0; b < Math.max(0, cfg.dreamBlocks - 1); b++) {
      const injId = cfg.injectorIds[idx % cfg.injectorIds.length];
      idx++;
      injectRho(phy, injId, cfg.injectAmount);
      for (let s = 0; s < cfg.dreamBlockSteps; s++) phy.step(cfg.dt, pressC, cfg.dampUsed);
    }
    injectRho(phy, cfg.wantId, cfg.injectAmount * (cfg.finalWriteMult || 1));
    try { if (typeof phy.computePressure === "function") phy.computePressure(pressC); } catch (e) {}
  };

  const runPreconditionOnce = async (phy, cfg, pressC, dirTag, baseB, ampD) => {
    const multBUsed = (dirTag === "up") ? cfg.preLow_multB : cfg.preHigh_multB;
    const ticks = (dirTag === "up") ? cfg.preLow_ticks : cfg.preHigh_ticks;
    const ampB0 = baseB * multBUsed;
    const ampB_nudge = ampB0 * cfg.nudgeMult;

    for (let t = 0; t < ticks; t++) {
      if (t === cfg.injectTick136) injectRho(phy, 136, ampD);
      if (t === cfg.injectTick114) injectRho(phy, 114, ampB0);
      if (t === cfg.handshakeTick && ampB_nudge > 0) injectRho(phy, 114, ampB_nudge);
      phy.step(cfg.dt, pressC, cfg.dampUsed);
    }
  };

  const runPrimeToggleRep = async (phy, cfg, pressC, multBUsed, baseB, ampD) => {
    const ampB0 = baseB * multBUsed;
    const ampB_nudge = ampB0 * cfg.nudgeMult;
    for (let tick = 0; tick < cfg.segmentTicks; tick++) {
      if (tick === cfg.injectTick136) injectRho(phy, 136, ampD);
      if (tick === cfg.injectTick114) injectRho(phy, 114, ampB0);
      if (tick === cfg.handshakeTick && ampB_nudge > 0) injectRho(phy, 114, ampB_nudge);
      phy.step(cfg.dt, pressC, cfg.dampUsed);
    }
    await relax(phy, cfg, pressC, cfg.betweenRepTicks_toggle);
  };

  // ---------- Stats helpers ----------
  const meanNum = (arr) => {
    let s = 0, n = 0;
    for (const v of arr) { if (Number.isFinite(v)) { s += v; n++; } }
    return n ? (s / n) : "";
  };

  const quantile = (arr, q) => {
    const xs = arr.filter(v => Number.isFinite(v)).slice().sort((a,b)=>a-b);
    if (!xs.length) return "";
    const pos = (xs.length - 1) * q;
    const lo = Math.floor(pos), hi = Math.ceil(pos);
    if (lo === hi) return xs[lo];
    const t = pos - lo;
    return xs[lo] * (1 - t) + xs[hi] * t;
  };

  // ---------- One trial ----------
  const runOneTrial = async (
    phy, cfg, pressC, dirTag, cellId, modeLabel, primeCount, rep, multBUsed,
    baseB, ampD, edgeIdx, baselineModeUsed,
    summaryLines, traceLines, runTag
  ) => {
    const cap = await recomputeDerived(cfg.dt);

    const ampB0 = baseB * multBUsed;
    const ratioBD = ampB0 / ampD;
    const ampB_nudge = ampB0 * cfg.nudgeMult;

    let peakAbs114 = 0, peakAbs136 = 0;
    const readAbs = new Map(); // tick -> {abs114, abs136}

    const laneCounts = new Map();
    const busDomCounts = new Map([["114", 0], ["136", 0], ["tie", 0]]);
    const busDomSeq = [];
    let prevMax1 = "", max1_switchCount = 0;
    let prevBusDom = "", bus_switchCount = 0;

    let aborted = false;

    for (let tick = 0; tick < cfg.segmentTicks; tick++) {
      if (tick === cfg.injectTick136) injectRho(phy, 136, ampD);
      if (tick === cfg.injectTick114) injectRho(phy, 114, ampB0);
      if (tick === cfg.handshakeTick && ampB_nudge > 0) injectRho(phy, 114, ampB_nudge);

      phy.step(cfg.dt, pressC, cfg.dampUsed);

      const top2 = top2Edges(phy, cfg.includeBackgroundEdges);
      const max1Pair = `${top2.best1.from}->${top2.best1.to}`;
      laneCounts.set(max1Pair, (laneCounts.get(max1Pair) || 0) + 1);
      if (prevMax1 && max1Pair !== prevMax1) max1_switchCount++;
      prevMax1 = max1Pair;

      const f114_89 = edgeFlux(phy, edgeIdx.i114_89);
      const f114_79 = edgeFlux(phy, edgeIdx.i114_79);
      const f136_89 = edgeFlux(phy, edgeIdx.i136_89);
      const f136_79 = edgeFlux(phy, edgeIdx.i136_79);

      const abs114 = Math.max(Math.abs(f114_89), Math.abs(f114_79));
      const abs136 = Math.max(Math.abs(f136_89), Math.abs(f136_79));

      if (cfg.abortOnNonFinite) {
        const ok = isFiniteNums([top2.best1.af, top2.best2.af, f114_89, f114_79, f136_89, f136_79, abs114, abs136]);
        if (!ok) { aborted = true; break; }
      }

      if (abs114 > peakAbs114) peakAbs114 = abs114;
      if (abs136 > peakAbs136) peakAbs136 = abs136;

      if (cfg.readTicks.includes(tick)) readAbs.set(tick, { abs114, abs136 });

      const busDom = (abs114 > abs136) ? "114" : (abs136 > abs114) ? "136" : "tie";
      busDomSeq.push(busDom);
      busDomCounts.set(busDom, (busDomCounts.get(busDom) || 0) + 1);
      if (prevBusDom && busDom !== prevBusDom) bus_switchCount++;
      prevBusDom = busDom;

      traceLines.push(csvRow([
        cfg.expId, runTag, dirTag, cellId, modeLabel, primeCount, rep, multBUsed, tick,
        top2.best1.from, top2.best1.to, top2.best1.af,
        top2.best2.from, top2.best2.to, top2.best2.af,
        f114_89, f114_79, f136_89, f136_79,
        abs114, abs136, busDom,
        cfg.betweenRepTicks_hold
      ]));
    }

    const winner_peakBus = (peakAbs114 > peakAbs136) ? 114 : (peakAbs136 > peakAbs114) ? 136 : 0;

    let laneEdge = "", laneEdge_count = -1;
    for (const [k, v] of laneCounts.entries()) if (v > laneEdge_count) { laneEdge = k; laneEdge_count = v; }
    const laneEntropy = entropyFromCounts(laneCounts);

    const ticksTotal = busDomSeq.length || 1;
    const fracBus114 = (busDomCounts.get("114") || 0) / ticksTotal;
    const fracBus136 = (busDomCounts.get("136") || 0) / ticksTotal;
    const busEntropy = entropyFromCounts(busDomCounts);

    const cap114 = captureTick(busDomSeq, "114", cfg.captureStreak, cfg.captureStartTick);
    const cap136 = captureTick(busDomSeq, "136", cfg.captureStreak, cfg.captureStartTick);
    const lateCap114 = captureTick(busDomSeq, "114", cfg.captureStreak, cfg.lateStartTick);

    // summary row (adds lateCaptureTick_114, lateStartTickUsed at end)
    summaryLines.push(csvRow([
      cfg.expId, runTag, dirTag, cellId, modeLabel, primeCount, rep, multBUsed,
      pressC, cfg.dampUsed, (cap.capLawHash ?? ""),
      ampB0, ampD, ratioBD,
      peakAbs114, peakAbs136, winner_peakBus,
      "", "", "", // legacy t8 placeholders
      laneEdge, laneEdge_count, laneEntropy, max1_switchCount,
      fracBus114, fracBus136, busEntropy, bus_switchCount,
      cap114, cap136,
      baselineModeUsed,
      cfg.betweenRepTicks_hold,
      aborted ? 1 : 0,
      lateCap114, cfg.lateStartTick
    ]));

    const winnersByTick = {};
    for (const t of cfg.readTicks) {
      const rec = readAbs.get(t);
      if (!rec) { winnersByTick[t] = 0; continue; }
      winnersByTick[t] = (rec.abs114 > rec.abs136) ? 114 : (rec.abs136 > rec.abs114) ? 136 : 0;
    }

    return { aborted, winner_peakBus, cap114, cap136, lateCap114, winnersByTick };
  };

  // ---------- Runner for a subrun ----------
  const runSubrun = async (phy, baseCfg, sub) => {
    const cfg = { ...baseCfg, ...sub };
    const startTag = isoTag(new Date());
    const runTag = `${cfg.expId}_${startTag}`;
    const ctx = { _snap: null };

    const baseB = cfg.baseAmpB * cfg.gain;
    const baseD = cfg.baseAmpD * cfg.gain;
    const ampD = (baseD * cfg.multD);

    const edgeIndex = buildEdgeIndex(phy);
    const edgeIdx = {
      i114_89: edgeIndex.get("114->89"),
      i114_79: edgeIndex.get("114->79"),
      i136_89: edgeIndex.get("136->89"),
      i136_79: edgeIndex.get("136->79")
    };

    const uiPressC = readUiPressC();
    const invPressC = window.SOLRuntime?.getInvariants?.()?.pressC;
    const pressCUsed = (cfg.pressCBase != null) ? cfg.pressCBase : (invPressC ?? uiPressC ?? 2.0);

    // headers
    const summaryHeader = [
      "schema","runTag","dir","cellId","modeLabel","primeCount","rep","multBUsed",
      "pressCUsed","dampUsed","capLawHash",
      "ampB0","ampD","ratioBD",
      "peakAbs114_bus","peakAbs136_bus","winner_peakBus",
      "t8_abs114_bus","t8_abs136_bus","winner_t8",
      "laneEdge","laneEdge_count","laneEntropy_bits","max1_switchCount",
      "fracTicks_busDom114","fracTicks_busDom136","busDomEntropy_bits","busDom_switchCount",
      "captureTick_114","captureTick_136",
      "baselineModeUsed",
      "betweenRepTicks_hold",
      "aborted",
      "lateCaptureTick_114","lateStartTickUsed"
    ];

    const traceHeader = [
      "schema","runTag","dir","cellId","modeLabel","primeCount","rep","multBUsed","tick",
      "max1_from","max1_to","max1_absFlux",
      "max2_from","max2_to","max2_absFlux",
      "flux_114_89","flux_114_79","flux_136_89","flux_136_79",
      "abs114_bus","abs136_bus","busDom",
      "betweenRepTicks_hold"
    ];

    const curveHeader_long = [
      "schema","runTag","dir","segmentTicks","multB","modeLabel","primeCount","n",
      ...cfg.readTicks.map(t => `p114_t${t}`),
      "q25_cap114","q50_cap114","q75_cap114","mean_cap114","nanRate_cap114",
      "q25_cap136","q50_cap136","q75_cap136","mean_cap136","nanRate_cap136",
      "q25_lateCap114","q50_lateCap114","q75_lateCap114","mean_lateCap114","nanRate_lateCap114",
      "p114_peak"
    ];

    const curveHeader_segSweep = [
      "schema","runTag","dir","segmentTicks","multB","modeLabel","primeCount","n",
      "q25_lateCap114","q50_lateCap114","q75_lateCap114","mean_lateCap114","nanRate_lateCap114",
      "q25_cap114","q50_cap114","q75_cap114","mean_cap114","nanRate_cap114"
    ];

    const summaryLines = [csvRow(summaryHeader)];
    const traceLines = [csvRow(traceHeader)];
    const curveLines = [csvRow(cfg.curveName === "segmentTicks_sweep_curve" ? curveHeader_segSweep : curveHeader_long)];

    console.log(`\n[${cfg.expId}] START @ ${startTag}`);
    console.log(`[${cfg.expId}] mode=${cfg.modeLabel} primeCount=${cfg.primeCount} segmentTicks=${cfg.segmentTicks ?? "[varies]"} repsPerStep=${cfg.repsPerStep}`);
    console.log(`[${cfg.expId}] dirs=${cfg.dirs.join(",")} multBList=[${cfg.multBList.join(", ")}] restorePerRep=${!!cfg.restorePerRep} betweenRepHold=${cfg.betweenRepTicks_hold}`);

    const segmentTicksList = cfg.segmentTicksList ? cfg.segmentTicksList.slice() : [cfg.segmentTicks];

    try {
      for (const segTicks of segmentTicksList) {
        cfg.segmentTicks = segTicks;

        for (const dirTag of cfg.dirs) {
          for (const multBUsedRaw of cfg.multBList) {
            const multBUsed = Math.round(multBUsedRaw * 100000) / 100000;
            const cellId = `${dirTag}_B${multBUsed.toFixed(5)}_${cfg.modeLabel}_seg${cfg.segmentTicks}`;

            // Aggregators for curve row
            const wins = {};
            for (const t of cfg.readTicks) wins[t] = { n114: 0, n: 0 };

            let nPeak114 = 0, nPeak = 0;

            const cap114_list = [];
            const cap136_list = [];
            const lateCap114_list = [];
            let nCap114_nan = 0, nCap136_nan = 0, nLate_nan = 0;

            let abortedAny = false;

            // STEP INIT (unless restorePerRep)
            let baselineModeUsed = "N/A";
            if (!cfg.restorePerRep) {
              baselineModeUsed = await baselineRestore(phy, ctx);
              await modeSelectOnce(phy, cfg, pressCUsed);
              await runPreconditionOnce(phy, cfg, pressCUsed, dirTag, baseB, ampD);

              for (let k = 0; k < cfg.primeCount; k++) {
                await runPrimeToggleRep(phy, cfg, pressCUsed, multBUsed, baseB, ampD);
              }
            }

            for (let rep = 1; rep <= cfg.repsPerStep; rep++) {
              // RESTORE PER REP variant
              if (cfg.restorePerRep) {
                baselineModeUsed = await baselineRestore(phy, ctx);
                await modeSelectOnce(phy, cfg, pressCUsed);
                await runPreconditionOnce(phy, cfg, pressCUsed, dirTag, baseB, ampD);

                for (let k = 0; k < cfg.primeCount; k++) {
                  await runPrimeToggleRep(phy, cfg, pressCUsed, multBUsed, baseB, ampD);
                }
              }

              const r = await runOneTrial(
                phy, cfg, pressCUsed, dirTag, cellId, cfg.modeLabel, cfg.primeCount, rep, multBUsed,
                baseB, ampD, edgeIdx, baselineModeUsed,
                summaryLines, traceLines, runTag
              );

              if (r.aborted) { abortedAny = true; break; }

              // read ticks
              for (const t of cfg.readTicks) {
                const w = r.winnersByTick[t];
                wins[t].n++;
                if (w === 114) wins[t].n114++;
              }

              // peak
              nPeak++;
              if (r.winner_peakBus === 114) nPeak114++;

              // capture ticks
              const c114 = (r.cap114 === "" ? NaN : Number(r.cap114));
              const c136 = (r.cap136 === "" ? NaN : Number(r.cap136));
              const lc114 = (r.lateCap114 === "" ? NaN : Number(r.lateCap114));

              cap114_list.push(c114);
              cap136_list.push(c136);
              lateCap114_list.push(lc114);

              if (!Number.isFinite(c114)) nCap114_nan++;
              if (!Number.isFinite(c136)) nCap136_nan++;
              if (!Number.isFinite(lc114)) nLate_nan++;

              // Between-rep relax (unless restorePerRep; then each rep starts fresh anyway)
              if (!cfg.restorePerRep) await relax(phy, cfg, pressCUsed, cfg.betweenRepTicks_hold);
            }

            const n = Math.max(1, nPeak);
            const p114_peak = nPeak114 / n;
            const p114_t = (t) => (wins[t].n ? (wins[t].n114 / wins[t].n) : 0);

            // stats
            const q25_114 = quantile(cap114_list, 0.25);
            const q50_114 = quantile(cap114_list, 0.50);
            const q75_114 = quantile(cap114_list, 0.75);
            const mu_114 = meanNum(cap114_list);
            const nanRate114 = nCap114_nan / n;

            const q25_136 = quantile(cap136_list, 0.25);
            const q50_136 = quantile(cap136_list, 0.50);
            const q75_136 = quantile(cap136_list, 0.75);
            const mu_136 = meanNum(cap136_list);
            const nanRate136 = nCap136_nan / n;

            const q25_l = quantile(lateCap114_list, 0.25);
            const q50_l = quantile(lateCap114_list, 0.50);
            const q75_l = quantile(lateCap114_list, 0.75);
            const mu_l = meanNum(lateCap114_list);
            const nanRateL = nLate_nan / n;

            if (cfg.curveName === "segmentTicks_sweep_curve") {
              curveLines.push(csvRow([
                cfg.expId, runTag, dirTag, cfg.segmentTicks, multBUsed.toFixed(5), cfg.modeLabel, cfg.primeCount, n,
                q25_l, q50_l, q75_l, mu_l, nanRateL,
                q25_114, q50_114, q75_114, mu_114, nanRate114
              ]));
            } else {
              curveLines.push(csvRow([
                cfg.expId, runTag, dirTag, cfg.segmentTicks, multBUsed.toFixed(5), cfg.modeLabel, cfg.primeCount, n,
                ...cfg.readTicks.map(t => p114_t(t)),
                q25_114, q50_114, q75_114, mu_114, nanRate114,
                q25_136, q50_136, q75_136, mu_136, nanRate136,
                q25_l, q50_l, q75_l, mu_l, nanRateL,
                p114_peak
              ]));
            }

            console.log(
              `[${cfg.expId}] ${cellId} | p114@12=${p114_t(12).toFixed(3)} p114@20=${p114_t(20).toFixed(3)}`
              + ` | q50_cap114=${q50_114} q50_lateCap114=${q50_l} nanLate=${nanRateL.toFixed(2)}`
              + (abortedAny ? " [ABORT]" : "")
            );
          }
        }
      }
    } finally {
      const endTag = isoTag(new Date());
      const baseName = `${cfg.expId}_${startTag}_${endTag}`;
      downloadText(`${baseName}_MASTER_summary.csv`, summaryLines.join(""));
      downloadText(`${baseName}_MASTER_busTrace.csv`, traceLines.join(""));
      downloadText(`${baseName}_${cfg.curveName}.csv`, curveLines.join(""));
      console.log(`\n[${cfg.expId}] DONE @ ${endTag}`);
      console.log(`- ${baseName}_MASTER_summary.csv`);
      console.log(`- ${baseName}_MASTER_busTrace.csv`);
      console.log(`- ${baseName}_${cfg.curveName}.csv`);
    }
  };

  // ---------- Execute batch ----------
  const phy = await waitForPhysics();
  freezeLiveLoop();
  await ensureBaselineIfAvailable();

  try {
    for (const sub of SUBRUNS) {
      await runSubrun(phy, DEFAULTS, sub);
    }
  } finally {
    unfreezeLiveLoop();
    console.log("\n[BN batch] ALL SUBRUNS COMPLETE.");
  }
})();
