// Phase 3.11 — 16BK (HOLD mode) tick8 micro-bracket ABOVE 1.011
// + optional 16BL (bit-forced) variant baked in via config.
//
// Why this run:
// - HOLD stride (segmentTicks=121, betweenRepTicks=81 => stride=202 even) kills the period-2 aliasing.
// - 16BJ showed tick8 p114_t8 jumps near multB=1.011 but didn’t cross 0.5.
// - This scan brackets x50 tightly: 1.0100 → 1.0160 step 0.0005.
//
// Exports:
// - MASTER_summary.csv
// - MASTER_busTrace.csv
// - rates_by_dir_multB.csv
// - threshold_estimates.csv
// - turbulence_profile.csv
//
// UI-neutral: NO camera/graph motion calls. Only direct node rho injection.

(async () => {
  "use strict";

  const CFG = {
    expId: "sol_phase311_16bk_holdMode_tick8MicroBracket_v1",

    // --- HOLD mode control (critical) ---
    segmentTicks: 121,
    betweenRepTicks_hold: 81,     // stride even => HOLD phase
    betweenRepTicks_toggle: 80,   // stride odd  => TOGGLE phase (used only for optional BL1 priming)

    // --- Scan band ---
    upList:   [1.0100,1.0105,1.0110,1.0115,1.0120,1.0125,1.0130,1.0135,1.0140,1.0145,1.0150,1.0155,1.0160],
    downList: [1.0160,1.0155,1.0150,1.0145,1.0140,1.0135,1.0130,1.0125,1.0120,1.0115,1.0110,1.0105,1.0100],

    repsPerStep: 80,          // per multB step
    dt: 0.12,
    pressCBase: null,         // null => use invariants/slider fallback
    dampUsed: 20,
    markerTick: 8,

    // Directional precondition ONCE per step
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

    // ---------------------------
    // Optional 16BL-style bit forcing
    // ---------------------------
    // If false: pure 16BK scan (recommended first).
    // If true: runs three scans: BK (no force) + BL0 (holdOnly init) + BL1 (toggleThenHold init).
    enableBitForcedVariants: false,

    // BL0: no priming, just HOLD (often latches the "default" phase).
    // BL1: do ONE prime trial using toggle stride, then HOLD (should latch the opposite phase).
    // Prime uses same multBUsed and current dir precondition.
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
    throw new Error("[16BK] timed out waiting for physics.");
  };

  const freezeLiveLoop = () => {
    const app = getApp();
    if (!app?.config) throw new Error("[16BK] App not ready.");
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
    if (!n) throw new Error(`[16BK] node not found: ${id}`);
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
    catch (e) { console.warn("[16BK] SOLBaseline.ensure failed (continuing):", e); }
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
  // Derived outputs
  // ----------------------------
  const buildRatesByDirMultB = (rows) => {
    const m = new Map();
    for (const r of rows) {
      const key = `${r.dir}|${r.multB}`;
      if (!m.has(key)) m.set(key, {
        dir: r.dir, multB: r.multB, n: 0,
        n114_peak: 0, n114_t8: 0,
        cap114: 0, cap136: 0,
        laneEntropy_sum: 0, max1_switch_sum: 0,
        busEntropy_sum: 0, bus_switch_sum: 0
      });
      const a = m.get(key);
      a.n++;
      a.n114_peak += (r.winner_peakBus === 114) ? 1 : 0;
      a.n114_t8 += (r.winner_t8 === 114) ? 1 : 0;
      a.cap114 += r.cap114_present ? 1 : 0;
      a.cap136 += r.cap136_present ? 1 : 0;
      a.laneEntropy_sum += (Number.isFinite(r.laneEntropy_bits) ? r.laneEntropy_bits : 0);
      a.max1_switch_sum += (Number.isFinite(r.max1_switchCount) ? r.max1_switchCount : 0);
      a.busEntropy_sum += (Number.isFinite(r.busDomEntropy_bits) ? r.busDomEntropy_bits : 0);
      a.bus_switch_sum += (Number.isFinite(r.busDom_switchCount) ? r.busDom_switchCount : 0);
    }
    const out = [];
    for (const a of m.values()) {
      const n = a.n || 1;
      out.push({
        dir: a.dir, multB: a.multB, n: a.n,
        p114_peak: a.n114_peak / n,
        p114_t8: a.n114_t8 / n,
        cap114_rate: a.cap114 / n,
        cap136_rate: a.cap136 / n,
        laneEntropy_mean: a.laneEntropy_sum / n,
        max1_switch_mean: a.max1_switch_sum / n,
        busDomEntropy_mean: a.busEntropy_sum / n,
        busDom_switch_mean: a.bus_switch_sum / n
      });
    }
    out.sort((x, y) => (x.dir === y.dir) ? (x.multB - y.multB) : (x.dir < y.dir ? -1 : 1));
    return out;
  };

  const estimateX50 = (pts) => {
    for (let i = 0; i < pts.length; i++) {
      if (pts[i].p === 0.5) return { x50: pts[i].x, bracket: [pts[i].x, pts[i].x], pBracket: [0.5, 0.5] };
    }
    for (let i = 0; i < pts.length - 1; i++) {
      const p0 = pts[i].p, p1 = pts[i + 1].p;
      const x0 = pts[i].x, x1 = pts[i + 1].x;
      const s0 = p0 - 0.5, s1 = p1 - 0.5;
      if (s0 * s1 < 0) {
        const t = (0.5 - p0) / (p1 - p0);
        return { x50: x0 + t * (x1 - x0), bracket: [x0, x1], pBracket: [p0, p1] };
      }
    }
    return { x50: "", bracket: ["", ""], pBracket: ["", ""] };
  };

  const buildThresholdEstimates = (rates) => {
    const dirs = [...new Set(rates.map(r => r.dir))];
    const metrics = [{ name: "peakBus", key: "p114_peak" }, { name: "tick8", key: "p114_t8" }];
    const rows = [];
    const byDir = new Map();
    for (const d of dirs) byDir.set(d, rates.filter(r => r.dir === d).sort((a,b)=>a.multB-b.multB));
    for (const met of metrics) {
      const estByDir = {};
      for (const d of dirs) {
        const pts = byDir.get(d).map(r => ({ x: r.multB, p: r[met.key] }));
        const est = estimateX50(pts);
        estByDir[d] = est;
        rows.push({ metric: met.name, dir: d, x50: est.x50, bracket_lo: est.bracket[0], bracket_hi: est.bracket[1], p_lo: est.pBracket[0], p_hi: est.pBracket[1] });
      }
      if (estByDir.up?.x50 !== "" && estByDir.down?.x50 !== "") {
        rows.push({ metric: met.name, dir: "hysteresis", x50: (estByDir.up.x50 - estByDir.down.x50), bracket_lo: "", bracket_hi: "", p_lo: "", p_hi: "" });
      }
    }
    return rows;
  };

  const buildTurbulenceProfile = (rates) => {
    const dirs = [...new Set(rates.map(r => r.dir))];
    const out = [];
    for (const d of dirs) {
      const pts = rates.filter(r => r.dir === d).sort((a,b)=>a.multB-b.multB);
      const n = pts.length;
      const dp = (arr, i, key) => {
        if (n < 2) return "";
        if (i === 0) return (arr[1][key] - arr[0][key]) / (arr[1].multB - arr[0].multB);
        if (i === n - 1) return (arr[n-1][key] - arr[n-2][key]) / (arr[n-1].multB - arr[n-2].multB);
        return (arr[i+1][key] - arr[i-1][key]) / (arr[i+1].multB - arr[i-1].multB);
      };
      for (let i = 0; i < n; i++) {
        const r = pts[i];
        const pP = r.p114_peak, p8 = r.p114_t8;
        out.push({
          dir: d, multB: r.multB, n: r.n,
          p114_peak: pP, p114_t8: p8,
          turb_peak: pP * (1 - pP),
          turb_t8: p8 * (1 - p8),
          dp_peak: dp(pts, i, "p114_peak"),
          dp_t8: dp(pts, i, "p114_t8"),
          laneEntropy_mean: r.laneEntropy_mean,
          max1_switch_mean: r.max1_switch_mean,
          busDomEntropy_mean: r.busDomEntropy_mean,
          busDom_switch_mean: r.busDom_switch_mean,
          cap114_rate: r.cap114_rate,
          cap136_rate: r.cap136_rate
        });
      }
    }
    return out;
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
        "schema","runTag","dir","stepIndex","stepRep","multBUsed",
        "pressCUsed","dampUsed","capLawHash",
        "ampB0","ampD","ratioBD",
        "peakAbs114_bus","peakAbs136_bus","winner_peakBus",
        "t8_abs114_bus","t8_abs136_bus","winner_t8",
        "laneEdge","laneEdge_count","laneEntropy_bits","max1_switchCount",
        "fracTicks_busDom114","fracTicks_busDom136","busDomEntropy_bits","busDom_switchCount",
        "captureTick_114","captureTick_136",
        "baselineModeUsed",
        "betweenRepTicks"
      ];

      const traceHeader = [
        "schema","runTag","dir","stepIndex","stepRep","multBUsed","tick",
        "max1_from","max1_to","max1_absFlux",
        "max2_from","max2_to","max2_absFlux",
        "flux_114_89","flux_114_79","flux_136_89","flux_136_79",
        "abs114_bus","abs136_bus","busDom",
        "betweenRepTicks"
      ];

      const summaryLines = [csvRow(summaryHeader)];
      const traceLines = [csvRow(traceHeader)];
      const trials = [];

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

      const runOneTrial = async (dirTag, stepIndex, rep, multBUsed, baselineModeUsed, betweenRepTicks, recordRows=true) => {
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

          if (recordRows) {
            traceLines.push(csvRow([
              cfg.expId, runTag, dirTag, stepIndex, rep, multBUsed, tick,
              top2.best1.from, top2.best1.to, top2.best1.af,
              top2.best2.from, top2.best2.to, top2.best2.af,
              f114_89, f114_79, f136_89, f136_79,
              abs114, abs136, busDom,
              betweenRepTicks
            ]));
          }
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

        if (recordRows) {
          summaryLines.push(csvRow([
            cfg.expId, runTag, dirTag, stepIndex, rep, multBUsed,
            pressCUsed, cfg.dampUsed, (cap.capLawHash ?? ""),
            ampB0, ampD, ratioBD,
            peakAbs114, peakAbs136, winner_peakBus,
            t8_abs114, t8_abs136, winner_t8,
            laneEdge, laneEdge_count, laneEntropy, max1_switchCount,
            fracBus114, fracBus136, busEntropy, bus_switchCount,
            cap114, cap136,
            baselineModeUsed,
            betweenRepTicks
          ]));

          trials.push({
            dir: dirTag,
            multB: multBUsed,
            winner_peakBus,
            winner_t8,
            laneEntropy_bits: laneEntropy,
            max1_switchCount,
            busDomEntropy_bits: busEntropy,
            busDom_switchCount: bus_switchCount,
            cap114_present: (cap114 !== ""),
            cap136_present: (cap136 !== ""),
            aborted
          });
        }

        return { aborted, winner_t8 };
      };

      const relax = async (betweenRepTicks) => {
        for (let k = 0; k < betweenRepTicks; k++) {
          if (this.stopFlag) break;
          phy.step(cfg.dt, pressCUsed, cfg.dampUsed);
        }
      };

      const primeLatchIfNeeded = async (primeMode, dirTag, multBUsed, baselineModeUsed) => {
        // primeMode: "NONE" | "BL0" | "BL1"
        // BL0: do nothing (holdOnly tends to default latch)
        // BL1: do ONE toggle-stride trial (not recorded), then relax by toggle ticks
        if (primeMode !== "BL1") return;
        await runOneTrial(`${dirTag}_PRIME`, -999, 0, multBUsed, baselineModeUsed, cfg.betweenRepTicks_toggle, false);
        await relax(cfg.betweenRepTicks_toggle);
      };

      const runStep = async (dirTag, stepIndex, multBUsed, betweenRepTicks, primeMode) => {
        if (this.stopFlag) return;

        const baselineModeUsed = await baselineRestore(phy, ctx);
        await modeSelectOnce(phy, cfg, pressCUsed, cfg.dampUsed);

        if (dirTag.includes("up")) await runPrecondition(cfg.preLow_multB, cfg.preLow_ticks);
        else await runPrecondition(cfg.preHigh_multB, cfg.preHigh_ticks);

        await primeLatchIfNeeded(primeMode, dirTag, multBUsed, baselineModeUsed);

        for (let rep = 1; rep <= cfg.repsPerStep; rep++) {
          if (this.stopFlag) break;
          const r = await runOneTrial(dirTag, stepIndex, rep, multBUsed, baselineModeUsed, betweenRepTicks, true);
          if (r?.aborted) break;
          await relax(betweenRepTicks);
        }
      };

      const runPath = async (dirTag, list, betweenRepTicks, primeMode) => {
        for (let s = 0; s < list.length; s++) {
          if (this.stopFlag) break;
          await runStep(dirTag, s, list[s], betweenRepTicks, primeMode);
        }
      };

      console.log(`\n[${cfg.expId}] START @ ${startTag}`);
      console.log(`[${cfg.expId}] HOLD stride: segmentTicks=${cfg.segmentTicks}, betweenRepTicks=${cfg.betweenRepTicks_hold} (even stride)`);
      console.log(`[${cfg.expId}] band: ${cfg.upList[0]} → ${cfg.upList[cfg.upList.length-1]} step 0.0005 | repsPerStep=${cfg.repsPerStep}`);

      // --- BK scan (no forced latch) ---
      console.log(`[${cfg.expId}] BK UP...`);
      await runPath("up", cfg.upList, cfg.betweenRepTicks_hold, "NONE");
      console.log(`[${cfg.expId}] BK DOWN...`);
      await runPath("down", cfg.downList, cfg.betweenRepTicks_hold, "NONE");

      if (cfg.enableBitForcedVariants) {
        // --- BL0 scan (holdOnly) ---
        console.log(`[${cfg.expId}] BL0 UP...`);
        await runPath("up_BL0", cfg.upList, cfg.betweenRepTicks_hold, "BL0");
        console.log(`[${cfg.expId}] BL0 DOWN...`);
        await runPath("down_BL0", cfg.downList, cfg.betweenRepTicks_hold, "BL0");

        // --- BL1 scan (toggleThenHold) ---
        console.log(`[${cfg.expId}] BL1 UP...`);
        await runPath("up_BL1", cfg.upList, cfg.betweenRepTicks_hold, "BL1");
        console.log(`[${cfg.expId}] BL1 DOWN...`);
        await runPath("down_BL1", cfg.downList, cfg.betweenRepTicks_hold, "BL1");
      }

      // --- Derived outputs ---
      const rates = buildRatesByDirMultB(trials);

      const ratesHeader = [
        "dir","multB","n","p114_peak","p114_t8","cap114_rate","cap136_rate",
        "laneEntropy_mean","max1_switch_mean","busDomEntropy_mean","busDom_switch_mean"
      ];
      const ratesCsv = [csvRow(ratesHeader)];
      for (const r of rates) ratesCsv.push(csvRow([
        r.dir, r.multB, r.n,
        r.p114_peak, r.p114_t8,
        r.cap114_rate, r.cap136_rate,
        r.laneEntropy_mean, r.max1_switch_mean, r.busDomEntropy_mean, r.busDom_switch_mean
      ]));

      const thrRows = buildThresholdEstimates(rates);
      const thrHeader = ["metric","dir","x50","bracket_lo","bracket_hi","p_lo","p_hi"];
      const thrCsv = [csvRow(thrHeader)];
      for (const r of thrRows) thrCsv.push(csvRow([r.metric, r.dir, r.x50, r.bracket_lo, r.bracket_hi, r.p_lo, r.p_hi]));

      const turbRows = buildTurbulenceProfile(rates);
      const turbHeader = [
        "dir","multB","n",
        "p114_peak","p114_t8",
        "turb_peak","turb_t8",
        "dp_peak","dp_t8",
        "laneEntropy_mean","max1_switch_mean","busDomEntropy_mean","busDom_switch_mean",
        "cap114_rate","cap136_rate"
      ];
      const turbCsv = [csvRow(turbHeader)];
      for (const r of turbRows) turbCsv.push(csvRow([
        r.dir, r.multB, r.n,
        r.p114_peak, r.p114_t8,
        r.turb_peak, r.turb_t8,
        r.dp_peak, r.dp_t8,
        r.laneEntropy_mean, r.max1_switch_mean, r.busDomEntropy_mean, r.busDom_switch_mean,
        r.cap114_rate, r.cap136_rate
      ]));

      // --- Export ---
      const endTag = isoTag(new Date());
      const baseName = `${cfg.expId}_${startTag}_${endTag}`;
      unfreezeLiveLoop();

      downloadText(`${baseName}_MASTER_summary.csv`, summaryLines.join(""));
      downloadText(`${baseName}_MASTER_busTrace.csv`, traceLines.join(""));
      downloadText(`${baseName}_rates_by_dir_multB.csv`, ratesCsv.join(""));
      downloadText(`${baseName}_threshold_estimates.csv`, thrCsv.join(""));
      downloadText(`${baseName}_turbulence_profile.csv`, turbCsv.join(""));

      console.log(`\n[${cfg.expId}] DONE @ ${endTag}`);
      console.log(`- ${baseName}_MASTER_summary.csv`);
      console.log(`- ${baseName}_MASTER_busTrace.csv`);
      console.log(`- ${baseName}_rates_by_dir_multB.csv`);
      console.log(`- ${baseName}_threshold_estimates.csv`);
      console.log(`- ${baseName}_turbulence_profile.csv`);

      return { expId: cfg.expId, baseName, pressCUsed, dampUsed: cfg.dampUsed, stopped: this.stopFlag };
    }
  };

  window.solPhase311_16bk_holdMode_tick8MicroBracket_v1 = Runner;
  console.log("✅ Installed: solPhase311_16bk_holdMode_tick8MicroBracket_v1");
  await Runner.run();

})();
