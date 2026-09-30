// Phase 3.11 — 16BN (Latch Basin Boundary Map)
// Goal: Map where the odd-toggle latch (M1: toggleThenHold) stops pinning tick8 to 114.
// We sweep multB downward under HOLD sampling, with one toggle-stride prime per step,
// and measure p114_t8 per step. We stop after we clearly "break" the latch.
//
// Protocol per step:
//   1) SOLBaseline.restore (or internal snapshot fallback)
//   2) modeSelect once (wantId=82; dream blocks)
//   3) directional precondition once (default: "down" uses preHigh)
//   4) PRIME: run 1 rep with betweenRepTicks=80 (toggle stride), not recorded
//   5) HOLD: run N reps with betweenRepTicks=81 (hold stride), record + aggregate p114_t8
//
// Exports:
//   - MASTER_summary.csv
//   - MASTER_busTrace.csv
//   - rates_by_dir_multB.csv
//   - latch_break_estimate.csv
//
// UI-neutral: NO camera/graph motion calls. Only direct node rho injection.

(async () => {
  "use strict";

  const CFG = {
    expId: "sol_phase311_16bn_latchBasinBoundaryScan_v1",

    // --- Critical sampling controls ---
    segmentTicks: 121,
    betweenRepTicks_hold: 81,      // stride even => HOLD
    betweenRepTicks_toggle: 80,    // stride odd  => TOGGLE (prime)

    dt: 0.12,
    pressCBase: null,
    dampUsed: 20,
    markerTick: 8,

    // --- Sweep plan ---
    // Start where latch should be strong, then descend.
    // (Tune as needed; this range is designed to catch the break point even if it's low.)
    startMultB: 1.0160,
    endMultB: 0.9400,
    stepMultB: -0.0050,        // coarse step downward

    // Reps per step (HOLD reps)
    repsPerStep: 60,

    // Break detection:
    // "Pinned" means p114_t8 >= pinnedThreshold
    // "Broken" means p114_t8 <= brokenThreshold
    pinnedThreshold: 0.98,     // effectively pinned (>= 59/60)
    brokenThreshold: 0.85,     // clearly unpinned (<= 51/60)
    confirmBrokenSteps: 2,     // require this many consecutive broken steps before stopping

    // Directional precondition: choose "down" by default (more stressy historically).
    // Set to "both" if you want both up/down passes in one run.
    dirMode: "down", // "down" | "up" | "both"

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

    // Capture (kept for continuity with prior exports)
    captureStreak: 5,
    captureStartTick: 5,

    includeBackgroundEdges: false,
    abortOnNonFinite: true
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
    throw new Error("[16BN] timed out waiting for physics.");
  };

  const freezeLiveLoop = () => {
    const app = getApp();
    if (!app?.config) throw new Error("[16BN] App not ready.");
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
    if (!n) throw new Error(`[16BN] node not found: ${id}`);
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
      if (domSeq[i] === who) {
        run++;
        if (run >= streak) return i - streak + 1;
      } else run = 0;
    }
    return "";
  };

  const recomputeDerived = async (dt) => {
    try {
      if (window.SOLRuntime?.recomputeDerived) return await window.SOLRuntime.recomputeDerived({ dt });
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
    catch (e) { console.warn("[16BN] SOLBaseline.ensure failed (continuing):", e); }
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
  // Mode select + precondition
  // ----------------------------
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

  // ----------------------------
  // Single trial (rep) — records summary+trace
  // ----------------------------
  const runOneTrial = async (phy, cfg, pressC, dirTag, stepIndex, rep, multBUsed, baseB, ampD, edgeIdx, baselineModeUsed, summaryLines, traceLines, runTag) => {
    const cap = await recomputeDerived(cfg.dt);

    const ampB0 = baseB * multBUsed;
    const ratioBD = ampB0 / ampD;
    const ampB_nudge = ampB0 * cfg.nudgeMult;

    let peakAbs114 = 0, peakAbs136 = 0;
    let t8_abs114 = "", t8_abs136 = "";

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

      if (tick === cfg.markerTick) { t8_abs114 = abs114; t8_abs136 = abs136; }

      const busDom = (abs114 > abs136) ? "114" : (abs136 > abs114) ? "136" : "tie";
      busDomSeq.push(busDom);
      busDomCounts.set(busDom, (busDomCounts.get(busDom) || 0) + 1);
      if (prevBusDom && busDom !== prevBusDom) bus_switchCount++;
      prevBusDom = busDom;

      traceLines.push(csvRow([
        cfg.expId, runTag, dirTag, stepIndex, rep, multBUsed, tick,
        top2.best1.from, top2.best1.to, top2.best1.af,
        top2.best2.from, top2.best2.to, top2.best2.af,
        f114_89, f114_79, f136_89, f136_79,
        abs114, abs136, busDom,
        cfg.betweenRepTicks_hold
      ]));
    }

    const winner_peakBus = (peakAbs114 > peakAbs136) ? 114 : (peakAbs136 > peakAbs114) ? 136 : 0;
    const winner_t8 = (t8_abs114 === "" || t8_abs136 === "") ? 0 : (t8_abs114 > t8_abs136) ? 114 : (t8_abs136 > t8_abs114) ? 136 : 0;

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
      cfg.expId, runTag, dirTag, stepIndex, rep, multBUsed,
      pressC, cfg.dampUsed, (cap.capLawHash ?? ""),
      ampB0, ampD, ratioBD,
      peakAbs114, peakAbs136, winner_peakBus,
      t8_abs114, t8_abs136, winner_t8,
      laneEdge, laneEdge_count, laneEntropy, max1_switchCount,
      fracBus114, fracBus136, busEntropy, bus_switchCount,
      cap114, cap136,
      baselineModeUsed,
      cfg.betweenRepTicks_hold,
      aborted ? 1 : 0
    ]));

    return { aborted, winner_t8, t8_abs114, t8_abs136 };
  };

  // ----------------------------
  // Aggregation per step
  // ----------------------------
  const aggStep = (dirTag, multB, winners) => {
    const n = winners.length || 1;
    const n114 = winners.filter(w => w === 114).length;
    const n136 = winners.filter(w => w === 136).length;
    const nTie = winners.filter(w => w === 0).length;
    return {
      dir: dirTag,
      multB,
      n,
      p114_t8: n114 / n,
      p136_t8: n136 / n,
      pTie_t8: nTie / n
    };
  };

  // ----------------------------
  // Runner
  // ----------------------------
  const Runner = {
    async run(userCfg = {}) {
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
      const edgeIdx = {
        i114_89: edgeIndex.get("114->89"),
        i114_79: edgeIndex.get("114->79"),
        i136_89: edgeIndex.get("136->89"),
        i136_79: edgeIndex.get("136->79")
      };

      const summaryHeader = [
        "schema","runTag","dir","stepIndex","stepRep","multBUsed",
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
        "schema","runTag","dir","stepIndex","stepRep","multBUsed","tick",
        "max1_from","max1_to","max1_absFlux",
        "max2_from","max2_to","max2_absFlux",
        "flux_114_89","flux_114_79","flux_136_89","flux_136_79",
        "abs114_bus","abs136_bus","busDom",
        "betweenRepTicks_hold"
      ];

      const ratesHeader = [
        "dir","multB","n","p114_t8","p136_t8","pTie_t8",
        "pinnedFlag","brokenFlag"
      ];

      const breakHeader = [
        "schema","runTag","dir",
        "pinnedThreshold","brokenThreshold","confirmBrokenSteps",
        "lastPinned_multB","firstBroken_multB",
        "breakBracket_lo","breakBracket_hi",
        "note"
      ];

      const summaryLines = [csvRow(summaryHeader)];
      const traceLines = [csvRow(traceHeader)];
      const ratesLines = [csvRow(ratesHeader)];
      const breakLines = [csvRow(breakHeader)];

      const dirs =
        (cfg.dirMode === "both") ? ["up", "down"] :
        (cfg.dirMode === "up") ? ["up"] : ["down"];

      console.log(`\n[${cfg.expId}] START @ ${startTag}`);
      console.log(`[${cfg.expId}] dirMode=${cfg.dirMode} | repsPerStep=${cfg.repsPerStep}`);
      console.log(`[${cfg.expId}] sweep: ${cfg.startMultB} -> ${cfg.endMultB} step ${cfg.stepMultB}`);
      console.log(`[${cfg.expId}] pinned>=${cfg.pinnedThreshold} | broken<=${cfg.brokenThreshold} | confirm=${cfg.confirmBrokenSteps}`);
      console.log(`[${cfg.expId}] HOLD=${cfg.betweenRepTicks_hold} | PRIME(toggle)=${cfg.betweenRepTicks_toggle}`);

      for (const dirTag of dirs) {
        let stepIndex = 0;

        let lastPinned = "";
        let firstBroken = "";
        let brokenStreak = 0;

        // Descend multB
        for (let multB = cfg.startMultB; multB >= cfg.endMultB - 1e-12; multB += cfg.stepMultB) {
          // Normalize rounding to avoid floating drift in CSV keys
          const multBUsed = Math.round(multB * 10000) / 10000;

          // 1) baseline restore
          const baselineModeUsed = await baselineRestore(phy, ctx);

          // 2) modeSelect once
          await modeSelectOnce(phy, cfg, pressCUsed);

          // 3) precondition once
          await runPreconditionOnce(phy, cfg, pressCUsed, dirTag, baseB, ampD);

          // 4) PRIME (one toggle-stride rep, NOT recorded)
          //    We run a minimal rep loop (no trace/summary) to apply the prime.
          {
            const ampB0 = baseB * multBUsed;
            const ampB_nudge = ampB0 * cfg.nudgeMult;
            for (let tick = 0; tick < cfg.segmentTicks; tick++) {
              if (tick === cfg.injectTick136) injectRho(phy, 136, ampD);
              if (tick === cfg.injectTick114) injectRho(phy, 114, ampB0);
              if (tick === cfg.handshakeTick && ampB_nudge > 0) injectRho(phy, 114, ampB_nudge);
              phy.step(cfg.dt, pressCUsed, cfg.dampUsed);
            }
            await relax(phy, cfg, pressCUsed, cfg.betweenRepTicks_toggle);
          }

          // 5) HOLD reps (recorded)
          const winners = [];
          let abortedAny = false;

          for (let rep = 1; rep <= cfg.repsPerStep; rep++) {
            const r = await runOneTrial(
              phy, cfg, pressCUsed, dirTag, stepIndex, rep, multBUsed,
              baseB, ampD, edgeIdx, baselineModeUsed,
              summaryLines, traceLines, runTag
            );
            if (r.aborted) { abortedAny = true; break; }
            winners.push(r.winner_t8);
            await relax(phy, cfg, pressCUsed, cfg.betweenRepTicks_hold);
          }

          const a = aggStep(dirTag, multBUsed, winners);
          const pinnedFlag = (a.p114_t8 >= cfg.pinnedThreshold) ? 1 : 0;
          const brokenFlag = (a.p114_t8 <= cfg.brokenThreshold) ? 1 : 0;

          ratesLines.push(csvRow([
            dirTag, multBUsed, a.n, a.p114_t8, a.p136_t8, a.pTie_t8,
            pinnedFlag, brokenFlag
          ]));

          if (!abortedAny) {
            if (pinnedFlag) lastPinned = multBUsed;
            if (brokenFlag) {
              if (firstBroken === "") firstBroken = multBUsed;
              brokenStreak++;
            } else {
              brokenStreak = 0;
            }
          }

          console.log(
            `[${cfg.expId}] ${dirTag} step ${stepIndex} multB=${multBUsed.toFixed(4)} p114_t8=${a.p114_t8.toFixed(4)} ` +
            `(pinned=${pinnedFlag} broken=${brokenFlag} streak=${brokenStreak})`
          );

          stepIndex++;

          // Stop once we have a confirmed broken region AFTER having seen pinned
          if (lastPinned !== "" && brokenStreak >= cfg.confirmBrokenSteps) break;
          if (abortedAny) break;
        }

        const bracketLo = (lastPinned !== "" && firstBroken !== "") ? Math.min(lastPinned, firstBroken) : "";
        const bracketHi = (lastPinned !== "" && firstBroken !== "") ? Math.max(lastPinned, firstBroken) : "";

        breakLines.push(csvRow([
          cfg.expId, runTag, dirTag,
          cfg.pinnedThreshold, cfg.brokenThreshold, cfg.confirmBrokenSteps,
          lastPinned, firstBroken,
          bracketLo, bracketHi,
          (lastPinned === "" && firstBroken === "") ? "No pinned/broken detected in scan range" :
          (lastPinned !== "" && firstBroken === "") ? "Never reached brokenThreshold; extend lower multB" :
          (lastPinned === "" && firstBroken !== "") ? "Already broken at start; extend higher multB" :
          "Bracket found"
        ]));
      }

      // Export
      const endTag = isoTag(new Date());
      const baseName = `${cfg.expId}_${startTag}_${endTag}`;
      unfreezeLiveLoop();

      downloadText(`${baseName}_MASTER_summary.csv`, summaryLines.join(""));
      downloadText(`${baseName}_MASTER_busTrace.csv`, traceLines.join(""));
      downloadText(`${baseName}_rates_by_dir_multB.csv`, ratesLines.join(""));
      downloadText(`${baseName}_latch_break_estimate.csv`, breakLines.join(""));

      console.log(`\n[${cfg.expId}] DONE @ ${endTag}`);
      console.log(`- ${baseName}_MASTER_summary.csv`);
      console.log(`- ${baseName}_MASTER_busTrace.csv`);
      console.log(`- ${baseName}_rates_by_dir_multB.csv`);
      console.log(`- ${baseName}_latch_break_estimate.csv`);

      return { expId: cfg.expId, baseName, pressCUsed, dampUsed: cfg.dampUsed };
    }
  };

  window.solPhase311_16bn_latchBasinBoundaryScan_v1 = Runner;
  console.log("✅ Installed: solPhase311_16bn_latchBasinBoundaryScan_v1");
  await Runner.run();

})();
