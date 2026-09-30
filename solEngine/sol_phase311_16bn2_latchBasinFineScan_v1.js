// Phase 3.11 — 16BN2 (High-precision latch basin edge scan, step=-0.0005)
// Goal: Fine-map the odd-toggle latch break region inside the 16BN bracket.
//
// Based on 16BN (dir=down) bracket: lastPinned=0.986, firstBroken=0.971.
// Here we scan 0.9860 → 0.9710 in -0.0005 steps (31 points), with MORE reps.
// We run BOTH directions (up + down) to see if the basin edge itself has hysteresis.
//
// Protocol per step:
//   1) baseline restore (SOLBaseline.restore or internal snapshot fallback)
//   2) modeSelect once (wantId=82; dream blocks)
//   3) directional precondition once (up uses preLow, down uses preHigh)
//   4) PRIME: 1 toggle-stride rep (betweenRepTicks=80), NOT recorded
//   5) HOLD: repsPerStep reps (betweenRepTicks=81), recorded
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
    expId: "sol_phase311_16bn2_latchBasinFineScan_v1",

    // --- Critical sampling controls ---
    segmentTicks: 121,
    betweenRepTicks_hold: 81,      // HOLD stride even
    betweenRepTicks_toggle: 80,    // TOGGLE stride odd (prime)

    dt: 0.12,
    pressCBase: null,
    dampUsed: 20,
    markerTick: 8,

    // --- Fine sweep plan (inside bracket) ---
    startMultB: 0.9860,
    endMultB: 0.9710,
    stepMultB: -0.0005,            // HIGH PRECISION

    repsPerStep: 80,               // more signal than 16BN

    // Classification thresholds (same semantics as 16BN)
    pinnedThreshold: 0.98,         // >= 79/80 => pinned
    brokenThreshold: 0.85,         // <= 68/80 => clearly broken

    // Directions
    dirMode: "both",               // "up" | "down" | "both"

    // Precondition
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

    // Capture (continuity)
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
    throw new Error("[16BN2] timed out waiting for physics.");
  };

  const freezeLiveLoop = () => {
    const app = getApp();
    if (!app?.config) throw new Error("[16BN2] App not ready.");
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
    if (!n) throw new Error(`[16BN2] node not found: ${id}`);
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
    catch (e) { console.warn("[16BN2] SOLBaseline.ensure failed (continuing):", e); }
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
  // PRIME (one toggle-stride rep, not recorded)
  // ----------------------------
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

  // ----------------------------
  // Single trial (rep) — records summary+trace
  // ----------------------------
  const runOneTrial = async (
    phy, cfg, pressC, dirTag, stepIndex, rep, multBUsed, baseB, ampD, edgeIdx, baselineModeUsed,
    summaryLines, traceLines, runTag
  ) => {
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

    return { aborted, winner_t8 };
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
      const ampD = (baseD * cfg.multD);

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
        "pinnedThreshold","brokenThreshold",
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

      // Build the multB list explicitly (to avoid float drift)
      const multBList = [];
      const nSteps = Math.round((cfg.startMultB - cfg.endMultB) / Math.abs(cfg.stepMultB)) + 1;
      for (let i = 0; i < nSteps; i++) {
        const x = cfg.startMultB + i * cfg.stepMultB;
        const multBUsed = Math.round(x * 10000) / 10000; // 4 decimals supports 0.0005 grid
        multBList.push(multBUsed);
      }

      console.log(`\n[${cfg.expId}] START @ ${startTag}`);
      console.log(`[${cfg.expId}] dirMode=${cfg.dirMode} | repsPerStep=${cfg.repsPerStep}`);
      console.log(`[${cfg.expId}] sweep points=${multBList.length} | ${multBList[0].toFixed(4)} -> ${multBList[multBList.length-1].toFixed(4)} step ${cfg.stepMultB}`);
      console.log(`[${cfg.expId}] thresholds: pinned>=${cfg.pinnedThreshold} | broken<=${cfg.brokenThreshold}`);
      console.log(`[${cfg.expId}] HOLD=${cfg.betweenRepTicks_hold} | PRIME(toggle)=${cfg.betweenRepTicks_toggle}`);

      for (const dirTag of dirs) {
        let lastPinned = "";
        let firstBroken = "";

        for (let stepIndex = 0; stepIndex < multBList.length; stepIndex++) {
          const multBUsed = multBList[stepIndex];

          // 1) baseline restore
          const baselineModeUsed = await baselineRestore(phy, ctx);

          // 2) modeSelect once
          await modeSelectOnce(phy, cfg, pressCUsed);

          // 3) directional precondition once
          await runPreconditionOnce(phy, cfg, pressCUsed, dirTag, baseB, ampD);

          // 4) PRIME (odd-toggle write)
          await runPrimeToggleRep(phy, cfg, pressCUsed, multBUsed, baseB, ampD);

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
            if (brokenFlag && firstBroken === "") firstBroken = multBUsed;
          }

          console.log(
            `[${cfg.expId}] ${dirTag} step ${stepIndex}/${multBList.length-1} multB=${multBUsed.toFixed(4)} p114_t8=${a.p114_t8.toFixed(4)} (pinned=${pinnedFlag} broken=${brokenFlag})`
          );

          if (abortedAny) break;
        }

        const bracketLo = (lastPinned !== "" && firstBroken !== "") ? Math.min(lastPinned, firstBroken) : "";
        const bracketHi = (lastPinned !== "" && firstBroken !== "") ? Math.max(lastPinned, firstBroken) : "";

        breakLines.push(csvRow([
          cfg.expId, runTag, dirTag,
          cfg.pinnedThreshold, cfg.brokenThreshold,
          lastPinned, firstBroken,
          bracketLo, bracketHi,
          (lastPinned === "" && firstBroken === "") ? "No pinned/broken detected in scan window" :
          (lastPinned !== "" && firstBroken === "") ? "Never reached brokenThreshold; extend lower multB window" :
          (lastPinned === "" && firstBroken !== "") ? "Already broken at top of window; extend higher multB window" :
          "Bracket found inside window"
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

  window.solPhase311_16bn2_latchBasinFineScan_v1 = Runner;
  console.log("✅ Installed: solPhase311_16bn2_latchBasinFineScan_v1");
  await Runner.run();

})();
