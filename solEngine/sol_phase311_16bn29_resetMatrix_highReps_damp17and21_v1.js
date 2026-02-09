// Phase 3.11 — 16BN29_resetMatrix_highReps_damp17and21_v1
// Goal: Resolve damp21 anomaly with higher reps + a richer between-pass operator set.
//
// For each damp in dampList and each dir (up/down), run sequences:
//
//   C (ASC_ONLY_CONTROL):
//     baseline restore + modeSelect + precondition(initial) -> ASC probe
//
//   A (NO_RESET):
//     baseline restore + modeSelect + precondition(initial) -> DESC full -> ASC probe
//
//   B (RESET_PRECONDITION_ONLY):
//     baseline restore + modeSelect + precondition(initial) -> DESC full -> (PRECONDITION ONLY) -> ASC probe
//
//   D (RESET_FULL_REPRIME):
//     baseline restore + modeSelect + precondition(initial) -> DESC full -> (MODESELECT + PRECONDITION) -> ASC probe
//
// DESC holds: 800,400,160,81,40,0
// ASC probe holds: 0,40,81,160
// repsPerCondition: 30
//
// Exports:
//   *_MASTER_summary.csv
//   *_MASTER_busTrace.csv   (sampled: first N reps per condition, stride in ticks)
//   *_repTransition_curve.csv
//
// UI-neutral: NO camera/graph movement.

(async () => {
  "use strict";

  const CFG = {
    expIdBase: "sol_phase311_16bn29_resetMatrix_highReps_damp17and21_v1",

    dt: 0.12,
    pressCBase: null,

    // Target: damp21 anomaly + comparator
    dampList: [17, 21], // set to [21] if you want only damp21

    holdsDesc: [800, 400, 160, 81, 40, 0],
    holdsAscProbe: [0, 40, 81, 160],

    repsPerCondition: 30,
    dirs: ["up", "down"],

    betweenConditionSettleTicks: 0,

    // busTrace sampling (keeps files small while retaining shape)
    traceStride: 4,
    traceRepsPerCondition: 2,

    // Capture / detectors
    captureStreak: 5,
    captureStartTick: 5,
    lateStartTickPrimary: 80,
    lateStartTickLegacy: 120,

    readTicks: [
      10, 12, 14, 20,
      60, 70, 75, 80, 85, 90, 92, 94, 95, 96, 98, 100, 102, 104, 105, 106, 108, 110, 112, 115, 118, 120,
      125, 128, 129, 130, 132, 135, 140,
      150, 151, 154, 155, 156, 160,
      170, 175, 180, 190, 195, 200,
      210, 215, 216, 217, 220,
      240, 280, 320, 360, 400
    ],

    // Precondition band (dir-dependent)
    preLow_multB: 0.90,
    preLow_ticks: 320,
    preHigh_multB: 1.08,
    preHigh_ticks: 320,

    // Mode select (82 target, injectors [90,82])
    wantId: 82,
    injectorIds: [90, 82],
    dreamBlocks: 15,
    dreamBlockSteps: 2,
    injectAmount: 120,
    finalWriteMult: 1,

    // Amplitudes
    multBFixed: 0.96625,
    baseAmpB: 4.0,
    baseAmpD: 5.75,
    gain: 22,
    multD: 1.0,

    // Trial schedule
    segmentTicks: 401,
    injectTick136: 0,
    injectTick114: 1,
    handshakeTick: 2,
    nudgeMult: 0.20,

    includeBackgroundEdges: false,
    abortOnNonFinite: false
  };

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
    throw new Error("[BN29] timed out waiting for physics.");
  };

  const freezeLiveLoop = () => {
    const app = getApp();
    if (!app?.config) throw new Error("[BN29] App not ready.");
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
    if (!n) throw new Error(`[BN29] node not found: ${id}`);
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

  const relax = async (phy, pressC, dampUsed, nTicks) => {
    for (let k = 0; k < Math.max(0, nTicks | 0); k++) phy.step(CFG.dt, pressC, dampUsed);
  };

  const ensureBaselineIfAvailable = async () => {
    if (!window.SOLBaseline?.ensure) return;
    try { await window.SOLBaseline.ensure({ force: false, exportJson: false }); }
    catch (e) { console.warn("[BN29] SOLBaseline.ensure failed (continuing):", e); }
  };

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

  const baselineRestore = async (phy, ctx) => {
    if (window.SOLBaseline?.restore) { await window.SOLBaseline.restore(); return "SOLBaseline.restore"; }
    if (!ctx._snap) ctx._snap = makeInternalSnapshot(phy);
    restoreInternalSnapshot(phy, ctx._snap);
    return "internal_snapshot_restored";
  };

  const modeSelectOnce = async (phy, pressC, dampUsed) => {
    let idx = 0;
    for (let b = 0; b < Math.max(0, CFG.dreamBlocks - 1); b++) {
      const injId = CFG.injectorIds[idx % CFG.injectorIds.length];
      idx++;
      injectRho(phy, injId, CFG.injectAmount);
      for (let s = 0; s < CFG.dreamBlockSteps; s++) phy.step(CFG.dt, pressC, dampUsed);
    }
    injectRho(phy, CFG.wantId, CFG.injectAmount * (CFG.finalWriteMult || 1));
    try { if (typeof phy.computePressure === "function") phy.computePressure(pressC); } catch (e) {}
  };

  const runPreconditionOnce = async (phy, pressC, dampUsed, dirTag, baseB, ampD) => {
    const multBUsed = (dirTag === "up") ? CFG.preLow_multB : CFG.preHigh_multB;
    const ticks = (dirTag === "up") ? CFG.preLow_ticks : CFG.preHigh_ticks;
    const ampB0 = baseB * multBUsed;
    const ampB_nudge = ampB0 * CFG.nudgeMult;

    for (let t = 0; t < ticks; t++) {
      if (t === CFG.injectTick136) injectRho(phy, 136, ampD);
      if (t === CFG.injectTick114) injectRho(phy, 114, ampB0);
      if (t === CFG.handshakeTick && ampB_nudge > 0) injectRho(phy, 114, ampB_nudge);
      phy.step(CFG.dt, pressC, dampUsed);
    }
  };

  const runOneRep = async (
    phy, pressC, dampUsed,
    seqId, seqLabel,
    passId, passLabel, conditionIndex, holdTicks, orderLabel,
    dirTag, repWithinCondition, globalRepIndex,
    baseB, ampD, edgeIdx, baselineModeUsed,
    summaryLines, traceLines, curveLines, runTag
  ) => {
    const cap = await recomputeDerived(CFG.dt);

    const ampB0 = (baseB * CFG.multBFixed);
    const ratioBD = ampB0 / ampD;
    const ampB_nudge = ampB0 * CFG.nudgeMult;

    let peakAbs114 = 0, peakAbs136 = 0;
    const readWinner = new Map();

    const laneCounts = new Map();
    const busDomCounts = new Map([["114", 0], ["136", 0], ["tie", 0]]);
    const busDomSeq = [];
    let prevMax1 = "", max1_switchCount = 0;
    let prevBusDom = "", bus_switchCount = 0;

    let aborted = false;

    for (let tick = 0; tick < CFG.segmentTicks; tick++) {
      if (tick === CFG.injectTick136) injectRho(phy, 136, ampD);
      if (tick === CFG.injectTick114) injectRho(phy, 114, ampB0);
      if (tick === CFG.handshakeTick && ampB_nudge > 0) injectRho(phy, 114, ampB_nudge);

      phy.step(CFG.dt, pressC, dampUsed);

      const top2 = top2Edges(phy, CFG.includeBackgroundEdges);
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

      if (!isFiniteNums([top2.best1.af, top2.best2.af, f114_89, f114_79, f136_89, f136_79, abs114, abs136])) {
        aborted = true;
        if (CFG.abortOnNonFinite) break;
      }

      if (abs114 > peakAbs114) peakAbs114 = abs114;
      if (abs136 > peakAbs136) peakAbs136 = abs136;

      const busDom = (abs114 > abs136) ? "114" : (abs136 > abs114) ? "136" : "tie";
      busDomSeq.push(busDom);
      busDomCounts.set(busDom, (busDomCounts.get(busDom) || 0) + 1);
      if (prevBusDom && busDom !== prevBusDom) bus_switchCount++;
      prevBusDom = busDom;

      if (CFG.readTicks.includes(tick)) {
        const w = (abs114 > abs136) ? 114 : (abs136 > abs114) ? 136 : 0;
        readWinner.set(tick, w);
      }

      const wantTrace = (repWithinCondition <= CFG.traceRepsPerCondition) && (tick % CFG.traceStride === 0);
      if (wantTrace) {
        traceLines.push(csvRow([
          CFG.expIdBase, runTag,
          dampUsed,
          seqId, seqLabel,
          passId, passLabel, orderLabel, conditionIndex, holdTicks,
          dirTag, repWithinCondition, globalRepIndex,
          CFG.multBFixed, tick,
          top2.best1.from, top2.best1.to, top2.best1.af,
          top2.best2.from, top2.best2.to, top2.best2.af,
          f114_89, f114_79, f136_89, f136_79,
          abs114, abs136, busDom
        ]));
      }
    }

    const winner_peakBus = (peakAbs114 > peakAbs136) ? 114 : (peakAbs136 > peakAbs114) ? 136 : 0;

    let laneEdge = "", laneEdge_count = -1;
    for (const [k, v] of laneCounts.entries()) if (v > laneEdge_count) { laneEdge = k; laneEdge_count = v; }
    const laneEntropy = entropyFromCounts(laneCounts);

    const ticksTotal = busDomSeq.length || 1;
    const fracBus114 = (busDomCounts.get("114") || 0) / ticksTotal;
    const fracBus136 = (busDomCounts.get("136") || 0) / ticksTotal;
    const busEntropy = entropyFromCounts(busDomCounts);

    const cap114 = captureTick(busDomSeq, "114", CFG.captureStreak, CFG.captureStartTick);
    const cap136 = captureTick(busDomSeq, "136", CFG.captureStreak, CFG.captureStartTick);

    const lateUp114_80 = captureTick(busDomSeq, "114", CFG.captureStreak, CFG.lateStartTickPrimary);
    let lateDecay136_after114_80 = "";
    if (lateUp114_80 !== "") {
      const start = Math.max(CFG.lateStartTickPrimary, (Number(lateUp114_80) + 10) | 0);
      lateDecay136_after114_80 = captureTick(busDomSeq, "136", CFG.captureStreak, start);
    }

    const lateUp114_120 = captureTick(busDomSeq, "114", CFG.captureStreak, CFG.lateStartTickLegacy);
    let lateDecay136_after114_120 = "";
    if (lateUp114_120 !== "") {
      const start = Math.max(CFG.lateStartTickLegacy, (Number(lateUp114_120) + 10) | 0);
      lateDecay136_after114_120 = captureTick(busDomSeq, "136", CFG.captureStreak, start);
    }

    summaryLines.push(csvRow([
      CFG.expIdBase, runTag,
      dampUsed,
      seqId, seqLabel,
      passId, passLabel, orderLabel, conditionIndex, holdTicks,
      dirTag, repWithinCondition, globalRepIndex,
      CFG.multBFixed,
      pressC, dampUsed, (cap.capLawHash ?? ""),
      ampB0, ampD, ratioBD,
      peakAbs114, peakAbs136, winner_peakBus,
      laneEdge, laneEdge_count, laneEntropy, max1_switchCount,
      fracBus114, fracBus136, busEntropy, bus_switchCount,
      cap114, cap136,
      baselineModeUsed,
      CFG.betweenConditionSettleTicks,
      aborted ? 1 : 0,
      lateUp114_80, CFG.lateStartTickPrimary, lateDecay136_after114_80,
      lateUp114_120, CFG.lateStartTickLegacy, lateDecay136_after114_120
    ]));

    const p114_byTick = CFG.readTicks.map(t => ((readWinner.get(t) ?? 0) === 114 ? 1 : 0));
    curveLines.push(csvRow([
      CFG.expIdBase, runTag,
      dampUsed,
      seqId, seqLabel,
      passId, passLabel, orderLabel, conditionIndex, holdTicks,
      dirTag, repWithinCondition, globalRepIndex,
      CFG.multBFixed,
      ...p114_byTick,
      cap114, cap136,
      lateUp114_80, lateDecay136_after114_80,
      lateUp114_120, lateDecay136_after114_120,
      winner_peakBus,
      aborted ? 1 : 0
    ]));

    if (!aborted) await relax(phy, pressC, dampUsed, holdTicks);
    return { aborted };
  };

  const runAll = async (phy, pressCUsed) => {
    const startTag = isoTag(new Date());
    const runTag = `${CFG.expIdBase}_${startTag}`;

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

    const summaryHeader = [
      "schema","runTag",
      "dampSweepValue",
      "seqId","seqLabel",
      "passId","passLabel","orderLabel","conditionIndex","betweenRepTicks_hold",
      "dir","repWithinCondition","globalRepIndex",
      "multBUsed",
      "pressCUsed","dampUsed","capLawHash",
      "ampB0","ampD","ratioBD",
      "peakAbs114_bus","peakAbs136_bus","winner_peakBus",
      "laneEdge","laneEdge_count","laneEntropy_bits","max1_switchCount",
      "fracTicks_busDom114","fracTicks_busDom136","busDomEntropy_bits","busDom_switchCount",
      "captureTick_114","captureTick_136",
      "baselineModeUsed",
      "betweenConditionSettleTicks",
      "aborted",
      "lateCaptureTick_114_primary","lateStartTickPrimary",
      "lateDecayTick_136_after114_primary",
      "lateCaptureTick_114_legacy","lateStartTickLegacy",
      "lateDecayTick_136_after114_legacy"
    ];

    const traceHeader = [
      "schema","runTag",
      "dampSweepValue",
      "seqId","seqLabel",
      "passId","passLabel","orderLabel","conditionIndex","betweenRepTicks_hold",
      "dir","repWithinCondition","globalRepIndex",
      "multBUsed","tick",
      "max1_from","max1_to","max1_absFlux",
      "max2_from","max2_to","max2_absFlux",
      "flux_114_89","flux_114_79","flux_136_89","flux_136_79",
      "abs114_bus","abs136_bus","busDom"
    ];

    const curveHeader = [
      "schema","runTag",
      "dampSweepValue",
      "seqId","seqLabel",
      "passId","passLabel","orderLabel","conditionIndex","betweenRepTicks_hold",
      "dir","repWithinCondition","globalRepIndex",
      "multBUsed",
      ...CFG.readTicks.map(t => `p114_t${t}`),
      "captureTick_114","captureTick_136",
      "lateCaptureTick_114_primary","lateDecayTick_136_after114_primary",
      "lateCaptureTick_114_legacy","lateDecayTick_136_after114_legacy",
      "winner_peakBus",
      "aborted"
    ];

    const summaryLines = [csvRow(summaryHeader)];
    const traceLines = [csvRow(traceHeader)];
    const curveLines = [csvRow(curveHeader)];

    console.log("\n[BN29] START", runTag);
    console.log("[BN29] damps:", CFG.dampList.join(","));
    console.log("[BN29] repsPerCondition:", CFG.repsPerCondition);
    console.log("[BN29] trace sampling: stride=", CFG.traceStride, "repsPerCond=", CFG.traceRepsPerCondition);

    let globalRepIndex = 0;

    const sequences = [
      { seqId: "C", seqLabel: "ASC_ONLY_CONTROL", mode: "ASC_ONLY" },
      { seqId: "A", seqLabel: "NO_RESET", mode: "DESC_THEN_ASC" },
      { seqId: "B", seqLabel: "RESET_PRECONDITION_ONLY", mode: "DESC_RESET_ASC_PRE" },
      { seqId: "D", seqLabel: "RESET_FULL_REPRIME", mode: "DESC_RESET_ASC_REPRIME" }
    ];

    try {
      for (const dampUsed of CFG.dampList) {
        console.log(`\n[BN29] === dampUsed=${dampUsed} ===`);

        for (const dirTag of CFG.dirs) {
          console.log(`[BN29] DIR=${dirTag}`);

          for (const seq of sequences) {
            console.log(`[BN29]  SEQ ${seq.seqLabel} | baseline restore + modeSelect + precondition(initial)`);

            const ctx = { _snap: null };
            const baselineModeUsed = await baselineRestore(phy, ctx);
            await modeSelectOnce(phy, pressCUsed, dampUsed);
            await runPreconditionOnce(phy, pressCUsed, dampUsed, dirTag, baseB, ampD);

            const runASC = async () => {
              for (let ci = 0; ci < CFG.holdsAscProbe.length; ci++) {
                const holdTicks = CFG.holdsAscProbe[ci];
                const conditionIndex = ci + 1;
                for (let rep = 1; rep <= CFG.repsPerCondition; rep++) {
                  globalRepIndex++;
                  await runOneRep(
                    phy, pressCUsed, dampUsed,
                    seq.seqId, seq.seqLabel,
                    2, "ASC", conditionIndex, holdTicks, "ASC_" + CFG.holdsAscProbe.join("_"),
                    dirTag, rep, globalRepIndex,
                    baseB, ampD, edgeIdx, baselineModeUsed,
                    summaryLines, traceLines, curveLines, runTag
                  );
                }
              }
            };

            if (seq.mode === "ASC_ONLY") {
              console.log(`[BN29]   PASS ASC_ONLY | holds=${CFG.holdsAscProbe.join(",")} | reps=${CFG.repsPerCondition}`);
              await runASC();
              continue;
            }

            // PASS DESC
            console.log(`[BN29]   PASS DESC | holds=${CFG.holdsDesc.join(",")} | reps=${CFG.repsPerCondition}`);
            for (let ci = 0; ci < CFG.holdsDesc.length; ci++) {
              const holdTicks = CFG.holdsDesc[ci];
              const conditionIndex = ci + 1;
              for (let rep = 1; rep <= CFG.repsPerCondition; rep++) {
                globalRepIndex++;
                await runOneRep(
                  phy, pressCUsed, dampUsed,
                  seq.seqId, seq.seqLabel,
                  1, "DESC", conditionIndex, holdTicks, "DESC_" + CFG.holdsDesc.join("_"),
                  dirTag, rep, globalRepIndex,
                  baseB, ampD, edgeIdx, baselineModeUsed,
                  summaryLines, traceLines, curveLines, runTag
                );
              }
            }

            // BETWEEN
            if (seq.mode === "DESC_RESET_ASC_PRE") {
              console.log(`[BN29]   BETWEEN: Precondition ONLY`);
              await runPreconditionOnce(phy, pressCUsed, dampUsed, dirTag, baseB, ampD);
            } else if (seq.mode === "DESC_RESET_ASC_REPRIME") {
              console.log(`[BN29]   BETWEEN: ModeSelect + Precondition (full reprime)`);
              await modeSelectOnce(phy, pressCUsed, dampUsed);
              await runPreconditionOnce(phy, pressCUsed, dampUsed, dirTag, baseB, ampD);
            } else {
              console.log(`[BN29]   BETWEEN: (none)`);
            }

            // PASS ASC probe
            console.log(`[BN29]   PASS ASC(probe) | holds=${CFG.holdsAscProbe.join(",")} | reps=${CFG.repsPerCondition}`);
            await runASC();
          }
        }
      }
    } finally {
      const endTag = isoTag(new Date());
      const baseName = `${CFG.expIdBase}_${startTag}_${endTag}`;

      downloadText(`${baseName}_MASTER_summary.csv`, summaryLines.join(""));
      downloadText(`${baseName}_MASTER_busTrace.csv`, traceLines.join(""));
      downloadText(`${baseName}_repTransition_curve.csv`, curveLines.join(""));

      console.log("\n[BN29] DONE", endTag);
      console.log("- " + `${baseName}_MASTER_summary.csv`);
      console.log("- " + `${baseName}_MASTER_busTrace.csv`);
      console.log("- " + `${baseName}_repTransition_curve.csv`);
    }
  };

  const phy = await waitForPhysics();
  freezeLiveLoop();
  await ensureBaselineIfAvailable();

  const uiPressC = readUiPressC();
  const invPressC = window.SOLRuntime?.getInvariants?.()?.pressC;
  const pressCUsed = (CFG.pressCBase != null) ? CFG.pressCBase : (invPressC ?? uiPressC ?? 2.0);

  try {
    await runAll(phy, pressCUsed);
  } finally {
    unfreezeLiveLoop();
    console.log("\n[BN29] COMPLETE.");
  }
})();
