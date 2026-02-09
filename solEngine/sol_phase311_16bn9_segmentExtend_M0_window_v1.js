// Phase 3.11 — 16BN9 (Segment-extended window, M0-only, seam microband)
// Goal: Separate "didn't invert in time" vs "inverts late" by extending segmentTicks.
// This run focuses ONLY on M0 (0 primes) in a tight multB band around the tick12 seam.
//
// Band: multB = 0.96575 → 0.96700 step +0.00025  (6 points)
// Directions: BOTH (up + down)
// Reps/step: 80
// segmentTicks: 201  (extended observation window)
//
// Measurements exported per multB × dir:
//   - p114 at readTicks {10,11,12,13,14,16,18,20}
//   - captureTick_114 distribution stats: q25/q50/q75, mean, nanRate
//   - captureTick_136 stats (sanity)
// Exports:
//   - MASTER_summary.csv
//   - MASTER_busTrace.csv
//   - inversionTime_longWindow_curve.csv
//
// UI-neutral: NO camera/graph motion calls. Only direct node rho injection.

(async () => {
  "use strict";

  const CFG = {
    expId: "sol_phase311_16bn9_segmentExtend_M0_window_v1",

    // timing
    segmentTicks: 201,
    betweenRepTicks_hold: 81,
    betweenRepTicks_toggle: 80, // unused (M0 only), kept for consistency

    dt: 0.12,
    pressCBase: null,
    dampUsed: 20,

    // read ticks (expanded since we have a longer window)
    readTicks: [10, 11, 12, 13, 14, 16, 18, 20],

    // capture definition
    captureStreak: 5,
    captureStartTick: 5,

    // seam microband
    multB_start: 0.96575,
    multB_end: 0.96700,
    multB_step: 0.00025,
    repsPerStep: 80,
    dirMode: "both",

    // condition: M0 only
    primeCount: 0,

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
    abortOnNonFinite: true
  };

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
    throw new Error("[16BN9] timed out waiting for physics.");
  };

  const freezeLiveLoop = () => {
    const app = getApp();
    if (!app?.config) throw new Error("[16BN9] App not ready.");
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
    if (!n) throw new Error(`[16BN9] node not found: ${id}`);
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
    catch (e) { console.warn("[16BN9] SOLBaseline.ensure failed (continuing):", e); }
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

  const relax = async (phy, cfg, pressC, nTicks) => {
    for (let k = 0; k < nTicks; k++) phy.step(cfg.dt, pressC, cfg.dampUsed);
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

  // ---------- Build sweep list ----------
  const buildSweep = (start, end, step) => {
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

  // ---------- One recorded trial ----------
  const runOneTrial = async (
    phy, cfg, pressC, dirTag, cellId, rep, multBUsed,
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

      if (cfg.readTicks.includes(tick)) {
        readAbs.set(tick, { abs114, abs136 });
      }

      const busDom = (abs114 > abs136) ? "114" : (abs136 > abs114) ? "136" : "tie";
      busDomSeq.push(busDom);
      busDomCounts.set(busDom, (busDomCounts.get(busDom) || 0) + 1);
      if (prevBusDom && busDom !== prevBusDom) bus_switchCount++;
      prevBusDom = busDom;

      traceLines.push(csvRow([
        cfg.expId, runTag, dirTag, cellId, "M0_noPrime", 0, rep, multBUsed, tick,
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

    // summary
    summaryLines.push(csvRow([
      cfg.expId, runTag, dirTag, cellId, "M0_noPrime", 0, rep, multBUsed,
      pressC, cfg.dampUsed, (cap.capLawHash ?? ""),
      ampB0, ampD, ratioBD,
      peakAbs114, peakAbs136, winner_peakBus,
      "", "", "", // legacy t8 slots unused
      laneEdge, laneEdge_count, laneEntropy, max1_switchCount,
      fracBus114, fracBus136, busEntropy, bus_switchCount,
      cap114, cap136,
      baselineModeUsed,
      cfg.betweenRepTicks_hold,
      aborted ? 1 : 0
    ]));

    // read winners
    const winnersByTick = {};
    for (const t of cfg.readTicks) {
      const rec = readAbs.get(t);
      if (!rec) { winnersByTick[t] = 0; continue; }
      winnersByTick[t] = (rec.abs114 > rec.abs136) ? 114 : (rec.abs136 > rec.abs114) ? 136 : 0;
    }

    return { aborted, winner_peakBus, cap114, cap136, winnersByTick };
  };

  // ---------- Main ----------
  const phy = await waitForPhysics();
  freezeLiveLoop();
  await ensureBaselineIfAvailable();

  const uiPressC = readUiPressC();
  const invPressC = window.SOLRuntime?.getInvariants?.()?.pressC;
  const pressCUsed = (CFG.pressCBase != null) ? CFG.pressCBase : (invPressC ?? uiPressC ?? 2.0);

  const baseB = CFG.baseAmpB * CFG.gain;
  const baseD = CFG.baseAmpD * CFG.gain;
  const ampD = (baseD * CFG.multD);

  const edgeIndex = buildEdgeIndex(phy);
  const edgeIdx = {
    i114_89: edgeIndex.get("114->89"),
    i114_79: edgeIndex.get("114->79"),
    i136_89: edgeIndex.get("136->89"),
    i136_79: edgeIndex.get("136->79")
  };

  const startTag = isoTag(new Date());
  const runTag = `${CFG.expId}_${startTag}`;
  const ctx = { _snap: null };

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
    "aborted"
  ];

  const traceHeader = [
    "schema","runTag","dir","cellId","modeLabel","primeCount","rep","multBUsed","tick",
    "max1_from","max1_to","max1_absFlux",
    "max2_from","max2_to","max2_absFlux",
    "flux_114_89","flux_114_79","flux_136_89","flux_136_79",
    "abs114_bus","abs136_bus","busDom",
    "betweenRepTicks_hold"
  ];

  const curveHeader = [
    "schema","runTag","dir","multB",
    "n",
    // p114 at read ticks
    ...CFG.readTicks.map(t => `p114_t${t}`),
    // capture stats for 114
    "q25_cap114","q50_cap114","q75_cap114","mean_cap114","nanRate_cap114",
    // capture stats for 136 (sanity)
    "q25_cap136","q50_cap136","q75_cap136","mean_cap136","nanRate_cap136",
    // peak preference
    "p114_peak"
  ];

  const summaryLines = [csvRow(summaryHeader)];
  const traceLines = [csvRow(traceHeader)];
  const curveLines = [csvRow(curveHeader)];

  const dirs = (CFG.dirMode === "both") ? ["up", "down"] : [CFG.dirMode];
  const sweep = buildSweep(CFG.multB_start, CFG.multB_end, CFG.multB_step);

  console.log(`\n[${CFG.expId}] START @ ${startTag}`);
  console.log(`[${CFG.expId}] segmentTicks=${CFG.segmentTicks} | sweep ${sweep[0].toFixed(5)} → ${sweep[sweep.length-1].toFixed(5)} step ${CFG.multB_step}`);
  console.log(`[${CFG.expId}] repsPerStep=${CFG.repsPerStep} | dirs=${dirs.join(",")} | readTicks=${CFG.readTicks.join(",")} | damp=${CFG.dampUsed}`);

  try {
    for (const dirTag of dirs) {
      for (const multBRaw of sweep) {
        const multBUsed = Math.round(multBRaw * 100000) / 100000;
        const cellId = `${dirTag}_B${multBUsed.toFixed(5)}_M0_noPrime_seg${CFG.segmentTicks}`;

        const baselineModeUsed = await baselineRestore(phy, ctx);
        await modeSelectOnce(phy, CFG, pressCUsed);
        await runPreconditionOnce(phy, CFG, pressCUsed, dirTag, baseB, ampD);

        const wins = {};
        for (const t of CFG.readTicks) wins[t] = { n114: 0, n: 0 };

        let nPeak114 = 0, nPeak = 0;

        const cap114_list = [];
        const cap136_list = [];
        let nCap114_nan = 0;
        let nCap136_nan = 0;

        let abortedAny = false;

        for (let rep = 1; rep <= CFG.repsPerStep; rep++) {
          const r = await runOneTrial(
            phy, CFG, pressCUsed, dirTag, cellId, rep, multBUsed,
            baseB, ampD, edgeIdx, baselineModeUsed,
            summaryLines, traceLines, runTag
          );

          if (r.aborted) { abortedAny = true; break; }

          for (const t of CFG.readTicks) {
            const w = r.winnersByTick[t];
            wins[t].n++;
            if (w === 114) wins[t].n114++;
          }

          nPeak++;
          if (r.winner_peakBus === 114) nPeak114++;

          const c114 = (r.cap114 === "" ? NaN : Number(r.cap114));
          const c136 = (r.cap136 === "" ? NaN : Number(r.cap136));
          cap114_list.push(c114);
          cap136_list.push(c136);
          if (!Number.isFinite(c114)) nCap114_nan++;
          if (!Number.isFinite(c136)) nCap136_nan++;

          await relax(phy, CFG, pressCUsed, CFG.betweenRepTicks_hold);
        }

        const n = Math.max(1, nPeak);
        const p114_peak = nPeak114 / n;

        const p114_t = (t) => (wins[t].n ? (wins[t].n114 / wins[t].n) : 0);

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

        curveLines.push(csvRow([
          CFG.expId, runTag, dirTag, multBUsed.toFixed(5),
          n,
          ...CFG.readTicks.map(t => p114_t(t)),
          q25_114, q50_114, q75_114, mu_114, nanRate114,
          q25_136, q50_136, q75_136, mu_136, nanRate136,
          p114_peak
        ]));

        console.log(
          `[${CFG.expId}] ${cellId} | p114@12=${p114_t(12).toFixed(3)} p114@14=${p114_t(14).toFixed(3)} p114@20=${p114_t(20).toFixed(3)}`
          + ` | q50_cap114=${q50_114} nan114=${nanRate114.toFixed(2)}`
          + (abortedAny ? " [ABORT]" : "")
        );
      }
    }
  } finally {
    const endTag = isoTag(new Date());
    const baseName = `${CFG.expId}_${startTag}_${endTag}`;
    unfreezeLiveLoop();

    downloadText(`${baseName}_MASTER_summary.csv`, summaryLines.join(""));
    downloadText(`${baseName}_MASTER_busTrace.csv`, traceLines.join(""));
    downloadText(`${baseName}_inversionTime_longWindow_curve.csv`, curveLines.join(""));

    console.log(`\n[${CFG.expId}] DONE @ ${endTag}`);
    console.log(`- ${baseName}_MASTER_summary.csv`);
    console.log(`- ${baseName}_MASTER_busTrace.csv`);
    console.log(`- ${baseName}_inversionTime_longWindow_curve.csv`);
  }
})();
