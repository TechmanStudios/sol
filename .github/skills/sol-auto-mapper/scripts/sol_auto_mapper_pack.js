(async () => {
  "use strict";

  // ============================================================
  // SOL Auto Mapper Pack v1
  // Paste into SOL dashboard console.
  // Then run:
  //   const plan = { ... }  // see mapping_plan.example.json
  //   await solAutoMap.runPlan(plan);
  //
  // Produces 3 downloads:
  //   solAutoMap__<plan>__<iso>__summary.csv
  //   solAutoMap__<plan>__<iso>__trace.csv
  //   solAutoMap__<plan>__<iso>__manifest.json
  // ============================================================

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const safe = (x) => (Number.isFinite(x) ? x : 0);
  const isoTag = () => new Date().toISOString().replace(/[:.]/g, "-");

  function clamp(x, lo, hi) {
    const v = Number(x);
    if (!Number.isFinite(v)) return lo;
    return Math.max(lo, Math.min(hi, v));
  }

  function applyDottedOverrides(rootObj, overrides, { label = "overrides" } = {}) {
    const changed = [];
    const entries = Object.entries(overrides || {});
    if (!rootObj || !entries.length) return { restore() {}, appliedKeys: [] };

    for (const [path, nextValue] of entries) {
      const parts = String(path).split(".").filter(Boolean);
      if (!parts.length) continue;
      let obj = rootObj;

      for (let i = 0; i < parts.length - 1; i++) {
        const k = parts[i];
        if (!obj || typeof obj !== "object") { obj = null; break; }
        if (!(k in obj)) {
          console.warn(`[solAutoMap] ${label}: path not found (missing '${k}') for '${path}'`);
          obj = null;
          break;
        }
        obj = obj[k];
      }

      if (!obj || typeof obj !== "object") continue;
      const leaf = parts[parts.length - 1];
      const existed = Object.prototype.hasOwnProperty.call(obj, leaf);
      const prevValue = obj[leaf];
      obj[leaf] = nextValue;
      changed.push({ obj, leaf, existed, prevValue, path });
    }

    return {
      appliedKeys: changed.map((c) => c.path),
      restore() {
        for (let i = changed.length - 1; i >= 0; i--) {
          const c = changed[i];
          if (!c?.obj) continue;
          if (c.existed) c.obj[c.leaf] = c.prevValue;
          else {
            try { delete c.obj[c.leaf]; } catch (_) { /* no-op */ }
          }
        }
      },
    };
  }

  function readModelKnobs(app, phy) {
    return {
      // Belief / conductance gating
      globalBias: safe(phy?.globalBias),
      conductanceBase: safe(phy?.conductanceBase),
      conductanceGamma: safe(phy?.conductanceGamma),
      conductanceMin: safe(phy?.conductanceMin),
      conductanceMax: safe(phy?.conductanceMax),

      // Psi dynamics
      psiDiffusion: safe(phy?.psiDiffusion),
      psiRelaxBase: safe(phy?.psiRelaxBase),
      psiGlobalNudge: safe(phy?.psiGlobalNudge),
      psiClamp: safe(phy?.psiClamp),

      // Phase gating
      phaseOmega: safe(phy?.phaseCfg?.omega),
      phaseSurfaceTension: safe(phy?.phaseCfg?.surfaceTension),
      phaseDeepViscosity: safe(phy?.phaseCfg?.deepViscosity),

      // Semantic mass dynamics
      semanticDecayRate: safe(phy?.semanticCfg?.decayRate),
      semanticMinMass: safe(phy?.semanticCfg?.minMass),
      semanticReinforceScale: safe(phy?.semanticCfg?.reinforceScale),

      // MHD + Jeans collapse
      mhdBGamma: safe(phy?.mhdCfg?.bGamma),
      mhdBMax: safe(phy?.mhdCfg?.bMax),
      jeansJcrit: safe(phy?.jeansCfg?.Jcrit),

      // Vorticity summary
      vortNormGlobal: safe(phy?.vortNorm_global),
      vortNormGlobalEMA: safe(phy?.vortNorm_global_ema),

      // App-level model knobs (rarely swept, but useful to record)
      beliefGammaMax: safe(app?.config?.beliefGammaMax),
      dtCap: safe(app?.config?.dtCap),
      capLawEnabled: app?.config?.capLaw?.enabled ? 1 : 0,
      capLawAlpha: safe(app?.config?.capLaw?.alpha),
    };
  }

  function getApp() {
    return globalThis.SOLDashboard || window.SOLDashboard || globalThis.App || window.App || null;
  }

  function getPhysics() {
    const solver = globalThis.solver || window.solver;
    if (solver?.nodes && solver?.edges) return solver;

    const p =
      globalThis.SOLDashboard?.state?.physics ??
      globalThis.App?.state?.physics ??
      globalThis.app?.state?.physics ??
      null;

    if (p?.nodes && p?.edges) return p;
    throw new Error("Physics not ready (no nodes/edges found). Ensure the dashboard is initialized.");
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

  function stepOnce(phy, dt, pressC, damping, { strictParams = true } = {}) {
    if (typeof phy.step !== "function") return false;
    // Prefer explicit signature.
    try { phy.step(dt, pressC, damping); return true; } catch (err) {
      if (strictParams) throw err;
    }

    // Fallbacks are allowed only when explicitly opted in.
    try { phy.step(dt); return true; } catch (_) {}
    try { phy.step(); return true; } catch (_) {}
    return false;
  }

  function injectRho(phy, id, amount) {
    const n = nodeByIdLoose(phy, id);
    if (!n) throw new Error(`Injector node not found: ${id}`);
    const amt = Math.max(0, Number(amount) || 0);
    if (typeof n.rho === "number") n.rho += amt;
    // Preserve SOL constellation semantics when present.
    try {
      if (n.isConstellation && typeof phy.reinforceSemanticStar === "function") {
        phy.reinforceSemanticStar(n, amt / 50.0);
      }
    } catch (_) {}
  }

  function entropyRhoNorm(nodes) {
    let sum = 0;
    for (const n of nodes) sum += safe(n?.rho);
    if (sum <= 0) return 0;

    let H = 0;
    for (const n of nodes) {
      const p = safe(n?.rho) / sum;
      if (p > 0) H -= p * Math.log(p);
    }
    const Hmax = Math.log(Math.max(1, nodes.length));
    return Hmax > 0 ? H / Hmax : 0;
  }

  function rhoStats(nodes) {
    let rhoSum = 0, rhoMax = -Infinity, rhoMaxId = "";
    for (const n of nodes) {
      const r = safe(n?.rho);
      rhoSum += r;
      if (r > rhoMax) { rhoMax = r; rhoMaxId = String(n?.id ?? ""); }
    }
    const rhoConc = rhoSum > 0 ? rhoMax / rhoSum : 0;
    return { rhoSum, rhoMax, rhoMaxId, rhoConc };
  }

  function pStats(nodes) {
    let pSum = 0, meanAbsP = 0, pMax = -Infinity, pMaxId = "", count = 0;
    for (const n of nodes) {
      const p = safe(n?.p);
      pSum += p;
      meanAbsP += Math.abs(p);
      count++;
      if (p > pMax) { pMax = p; pMaxId = String(n?.id ?? ""); }
    }
    const meanP = count ? pSum / count : 0;
    meanAbsP = count ? meanAbsP / count : 0;
    return { meanP, meanAbsP, pSum, pMax, pMaxId };
  }

  function scalarFieldStats(nodes, fieldName) {
    let sum = 0, absSum = 0, count = 0;
    let max = -Infinity, maxId = "";
    let min = Infinity, minId = "";
    for (const n of nodes || []) {
      const v = safe(n?.[fieldName]);
      sum += v;
      absSum += Math.abs(v);
      count++;
      if (v > max) { max = v; maxId = String(n?.id ?? ""); }
      if (v < min) { min = v; minId = String(n?.id ?? ""); }
    }
    const mean = count ? sum / count : 0;
    const meanAbs = count ? absSum / count : 0;
    return {
      [`${fieldName}Sum`]: sum,
      [`${fieldName}Mean`]: mean,
      [`${fieldName}MeanAbs`]: meanAbs,
      [`${fieldName}Max`]: Number.isFinite(max) ? max : 0,
      [`${fieldName}MaxId`]: maxId,
      [`${fieldName}Min`]: Number.isFinite(min) ? min : 0,
      [`${fieldName}MinId`]: minId,
    };
  }

  function basinTelemetry(phy, a = 82, b = 90) {
    const nA = nodeByIdLoose(phy, a);
    const nB = nodeByIdLoose(phy, b);
    const rhoA = safe(nA?.rho);
    const rhoB = safe(nB?.rho);
    const pA = safe(nA?.p);
    const pB = safe(nB?.p);
    const winnerId = rhoB > rhoA ? b : a;
    const marginRho = Math.abs(rhoB - rhoA);
    return {
      basinA: a,
      basinB: b,
      basinA_rho: rhoA,
      basinB_rho: rhoB,
      basinA_p: pA,
      basinB_p: pB,
      basinWinnerId: winnerId,
      basinMarginRho: marginRho,
    };
  }

  function fluxStats(edges, includeBackgroundEdges) {
    let maxAbsFlux = 0, sumAbsFlux = 0;
    for (const e of edges || []) {
      if (!e) continue;
      if (!includeBackgroundEdges && e.background) continue;
      const f = Math.abs(safe(e?.flux));
      sumAbsFlux += f;
      if (f > maxAbsFlux) maxAbsFlux = f;
    }
    return { maxAbsFlux, sumAbsFlux };
  }

  function sample(phy, includeBackgroundEdges) {
    const nodes = phy.nodes || [];
    const edges = phy.edges || [];
    return {
      nodeCount: nodes.length,
      edgeCount: edges.length,
      entropy: entropyRhoNorm(nodes),
      ...rhoStats(nodes),
      ...pStats(nodes),
      ...scalarFieldStats(nodes, "psi"),
      ...scalarFieldStats(nodes, "psi_bias"),
      ...scalarFieldStats(nodes, "semanticMass"),
      ...scalarFieldStats(nodes, "semanticMass0"),
      ...fluxStats(edges, includeBackgroundEdges),
      ...basinTelemetry(phy, 82, 90),
    };
  }

  function pickOverride(gridPoint, key, fallback) {
    // Treat null/undefined as "not provided"; allow 0.
    return (gridPoint && gridPoint[key] !== undefined && gridPoint[key] !== null)
      ? gridPoint[key]
      : fallback;
  }

  function downloadText(filename, text, mime = "text/plain") {
    const blob = new Blob([String(text)], { type: mime });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 5000);
  }

  function downloadCSVUnion(filename, rows) {
    if (!rows?.length) {
      console.warn(`[solAutoMap] no rows to write: ${filename}`);
      return;
    }
    const colSet = new Set();
    for (const r of rows) for (const k of Object.keys(r || {})) colSet.add(k);
    const cols = Array.from(colSet);

    const esc = (v) => {
      const s = String(v ?? "");
      return /[\",\n]/.test(s) ? `"${s.replace(/\"/g, '""')}"` : s;
    };

    const lines = [cols.join(",")].concat(
      rows.map((r) => cols.map((c) => esc(r?.[c])).join(","))
    );

    downloadText(filename, lines.join("\n"), "text/csv;charset=utf-8");
  }

  async function waitUntil(targetMs, { timingMode = "tight", spinWaitMs = 2.0 } = {}) {
    while (true) {
      const now = performance.now();
      const remaining = targetMs - now;
      if (remaining <= 0) return;

      if (timingMode !== "tight") {
        await sleep(remaining);
        return;
      }

      const guard = (Number(spinWaitMs) || 0) + 2.0;
      if (remaining > guard) {
        await sleep(Math.max(0, remaining - guard));
        continue;
      }

      // Busy-wait near the deadline.
      while (performance.now() < targetMs) {}
      return;
    }
  }

  function freezeLiveLoop() {
    const app = getApp();
    if (!app?.config) return { ok: false, reason: "No app.config" };
    const prev = app.config.dtCap;
    app.config.dtCap = 0;
    return { ok: true, prevDtCap: prev };
  }

  function unfreezeLiveLoop(prevDtCap) {
    const app = getApp();
    if (!app?.config) return;
    if (prevDtCap !== undefined) app.config.dtCap = prevDtCap;
  }

  function snapshotState(phy) {
    const nodePairs = [];
    for (const n of (phy.nodes || [])) {
      if (!n || n.id == null) continue;
      nodePairs.push([String(n.id), {
        rho: n.rho, p: n.p, psi: n.psi, psi_bias: n.psi_bias,
        semanticMass: n.semanticMass, semanticMass0: n.semanticMass0,
        b_q: n.b_q, b_charge: n.b_charge, b_state: n.b_state,
        isBattery: !!n.isBattery,
        isConstellation: !!n.isConstellation,
      }]);
    }
    const edgeFlux = (phy.edges || []).map((e) => (e && Number.isFinite(e.flux)) ? e.flux : 0);
    return { nodePairs, edgeFlux };
  }

  function restoreState(phy, snap) {
    if (!snap) return;
    const map = new Map(snap.nodePairs || []);
    for (const n of (phy.nodes || [])) {
      if (!n || n.id == null) continue;
      const s = map.get(String(n.id));
      if (!s) continue;
      n.rho = s.rho;
      n.p = s.p;
      n.psi = s.psi;
      n.psi_bias = s.psi_bias;
      n.semanticMass = s.semanticMass;
      n.semanticMass0 = s.semanticMass0;
      if (n.isBattery || s.isBattery) {
        n.b_q = s.b_q;
        n.b_charge = s.b_charge;
        n.b_state = s.b_state;
      }
    }
    const edges = phy.edges || [];
    for (let i = 0; i < edges.length; i++) {
      const e = edges[i];
      if (!e) continue;
      e.flux = (snap.edgeFlux && Number.isFinite(snap.edgeFlux[i])) ? snap.edgeFlux[i] : 0;
    }
  }

  function cartesianGrid(gridObj) {
    const keys = Object.keys(gridObj || {});
    if (!keys.length) return [{}];

    const out = [];
    const rec = (idx, acc) => {
      if (idx >= keys.length) {
        out.push({ ...acc });
        return;
      }
      const k = keys[idx];
      const vals = Array.isArray(gridObj[k]) ? gridObj[k] : [gridObj[k]];
      for (const v of vals) {
        acc[k] = v;
        rec(idx + 1, acc);
      }
      delete acc[k];
    };

    rec(0, {});
    return out;
  }

  async function runSingle({
    phy,
    runId,
    planName,
    basinId,
    replicate,
    gridPoint,
    scenario,
    measurement,
    timing,
    baselineSnap,
    appOverrides,
    phyOverrides,
    engine,
  }) {
    const includeBackgroundEdges = !!pickOverride(gridPoint, "includeBackgroundEdges", measurement?.includeBackgroundEdges);

    const app = getApp();

    // Restore baseline for every run.
    restoreState(phy, baselineSnap);

    // Apply per-run config overrides (and revert after the run).
    // Supports:
    // - sweep-level: { appConfigOverrides, physicsOverrides }
    // - grid-point: { appConfig, physics }
    // - belief slider semantics: beliefBias in [-1, 1]
    const mergedAppOverrides = {
      ...(appOverrides || {}),
      ...(gridPoint?.appConfig || {}),
    };

    const mergedPhyOverrides = {
      ...(phyOverrides || {}),
      ...(gridPoint?.physics || {}),
    };

    const beliefBias = (gridPoint && gridPoint.beliefBias !== undefined && gridPoint.beliefBias !== null)
      ? clamp(gridPoint.beliefBias, -1, 1)
      : null;

    if (beliefBias !== null) {
      const beliefGammaMax = Number(app?.config?.beliefGammaMax);
      const gMax = Number.isFinite(beliefGammaMax) ? beliefGammaMax : 1.25;
      // Mirrors dashboard v3_7_2 onBeliefInput(): globalBias=bias; conductanceGamma=bias*beliefGammaMax
      mergedPhyOverrides.globalBias = beliefBias;
      mergedPhyOverrides.conductanceGamma = beliefBias * gMax;
    }

    const appPatch = applyDottedOverrides(app?.config, mergedAppOverrides, { label: "appConfigOverrides" });
    const phyPatch = applyDottedOverrides(phy, mergedPhyOverrides, { label: "physicsOverrides" });

    // Extract parameters (gridPoint can override nearly everything).
    const pressC = Number(
      pickOverride(gridPoint, "pressureC",
        pickOverride(gridPoint, "pressC", 20)
      )
    );
    const damping = Number(
      pickOverride(gridPoint, "damping",
        pickOverride(gridPoint, "baseDamp",
          pickOverride(gridPoint, "damp", 8)
        )
      )
    );

    const dt = Number(pickOverride(gridPoint, "dt", measurement?.dt ?? 0.12));
    const everyMs = Number(pickOverride(gridPoint, "everyMs", measurement?.everyMs ?? 200));
    const durationMs = Number(pickOverride(gridPoint, "durationMs", measurement?.durationMs ?? 60000));

    const scenarioType = String(pickOverride(gridPoint, "scenarioType", scenario?.type ?? "inject_then_watch"));
    const injectAmount = Number(pickOverride(gridPoint, "injectAmount", scenario?.injectAmount ?? 120));
    const preSteps = Number(pickOverride(gridPoint, "preSteps", scenario?.preSteps ?? 2));
    const preDt = Number(pickOverride(gridPoint, "preDt", scenario?.preDt ?? dt));

    const strictStepParams = (engine && engine.strictStepParams !== undefined && engine.strictStepParams !== null)
      ? !!engine.strictStepParams
      : true;

    try {
      // Scenario: optional pre-steps before injection.
      for (let i = 0; i < Math.max(0, preSteps | 0); i++) {
        stepOnce(phy, preDt, pressC, damping, { strictParams: strictStepParams });
      }

      if (scenarioType === "inject_then_watch") {
        injectRho(phy, basinId, injectAmount);
      } else {
        throw new Error(`[solAutoMap] Unknown scenario.type: ${scenarioType}`);
      }

      // Ensure pressure is computed if the engine exposes a helper.
      try { if (typeof phy.computePressure === "function") phy.computePressure(pressC); } catch (_) {}

      const traceRows = [];
      const t0 = performance.now();
      const tickCount = Math.max(1, Math.floor(durationMs / everyMs));

      let next = t0;
      for (let tick = 0; tick < tickCount; tick++) {
        next += everyMs;
        await waitUntil(next, timing || {});

        const didStep = stepOnce(phy, dt, pressC, damping, { strictParams: strictStepParams });
        try { if (typeof phy.computePressure === "function") phy.computePressure(pressC); } catch (_) {}
        const s = sample(phy, includeBackgroundEdges);
        const knobs = readModelKnobs(app, phy);

        const tNow = performance.now();
        traceRows.push({
          planName,
          runId,
          basinId,
          replicate,
          sweepClass: String(gridPoint?.sweepName ?? gridPoint?.sweepClass ?? ""),
          sweepName: String(gridPoint?.sweepName ?? ""),
          tick,
          tSec: (tNow - t0) / 1000,
          dt,
          pressC,
          damping,
          includeBackgroundEdges: includeBackgroundEdges ? 1 : 0,
          injectAmount,
          preSteps,
          preDt,
          strictStepParams: strictStepParams ? 1 : 0,
          beliefBias: beliefBias === null ? "" : beliefBias,
          didStep: didStep ? 1 : 0,
          ...knobs,
          ...s,
        });
      }

      // Summary row: take last sample + a few rollups.
      const last = traceRows[traceRows.length - 1] || {};
      const first = traceRows[0] || {};

      const summaryRow = {
        planName,
        runId,
        basinId,
        replicate,
        pressC,
        damping,
        includeBackgroundEdges: includeBackgroundEdges ? 1 : 0,
        scenarioType,
        injectAmount,
        durationMs,
        everyMs,
        dt,
        preSteps,
        preDt,
        strictStepParams: strictStepParams ? 1 : 0,
        beliefBias: beliefBias === null ? "" : beliefBias,
        appOverridesKeys: appPatch.appliedKeys.join(";"),
        phyOverridesKeys: phyPatch.appliedKeys.join(";"),
        rhoSum_t0: safe(first.rhoSum),
        rhoSum_tEnd: safe(last.rhoSum),
        rhoSum_delta: safe(last.rhoSum) - safe(first.rhoSum),
        rhoMaxId_tEnd: String(last.rhoMaxId ?? ""),
        rhoConc_tEnd: safe(last.rhoConc),
        entropy_tEnd: safe(last.entropy),
        maxAbsFlux_tEnd: safe(last.maxAbsFlux),
        sumAbsFlux_tEnd: safe(last.sumAbsFlux),
        psiMean_tEnd: safe(last.psiMean),
        psiMax_tEnd: safe(last.psiMax),
        psiMaxId_tEnd: String(last.psiMaxId ?? ""),
        semanticMassMean_tEnd: safe(last.semanticMassMean),
        basinWinnerId_tEnd: safe(last.basinWinnerId),
        basinMarginRho_tEnd: safe(last.basinMarginRho),
        // record knob state (from last tick)
        globalBias: safe(last.globalBias),
        conductanceGamma: safe(last.conductanceGamma),
        psiDiffusion: safe(last.psiDiffusion),
        psiRelaxBase: safe(last.psiRelaxBase),
        phaseOmega: safe(last.phaseOmega),
        semanticDecayRate: safe(last.semanticDecayRate),
        vortNormGlobalEMA: safe(last.vortNormGlobalEMA),
      };

      return { traceRows, summaryRow };
    } finally {
      phyPatch.restore();
      appPatch.restore();
    }
  }

  const solAutoMap = {
    version: "auto_mapper_pack_v1",
    _stopFlag: false,
    stop() { this._stopFlag = true; console.warn("[solAutoMap] stop flag set (halts before next run)"); },

    _sanitizeName(s) {
      return String(s ?? "")
        .trim()
        .replace(/\s+/g, "_")
        .replace(/[^A-Za-z0-9_\-\.]/g, "-")
        .slice(0, 120) || "unnamed";
    },

    async runPlan(plan) {
      const planName = this._sanitizeName(plan?.planName ?? "unnamed_plan");
      const runIso = isoTag();
      const phy = getPhysics();

      const freeze = freezeLiveLoop();
      if (freeze.ok) console.log("[solAutoMap] live loop frozen (dtCap=0)");

      const baselineSnap = snapshotState(phy);

      const basins = Array.isArray(plan?.basins) && plan.basins.length ? plan.basins : [90, 82];
      const scenario = plan?.scenario || { type: "inject_then_watch", injectAmount: 120, preSteps: 2, preDt: 0.12 };
      const measurement = plan?.measurement || { durationMs: 60000, everyMs: 200, dt: 0.12, includeBackgroundEdges: false };
      const timing = plan?.timing || { timingMode: "tight", spinWaitMs: 2.0 };
      const replicates = Math.max(1, Number(plan?.replicates ?? 1) | 0);
      const engine = plan?.engine || { strictStepParams: true };

      const appOverrides = plan?.appConfigOverrides || null;
      const phyOverrides = plan?.physicsOverrides || null;

      const gridPoints = cartesianGrid(plan?.grid || {});
      console.log(`[solAutoMap] plan=${planName} gridPoints=${gridPoints.length} basins=${basins.length} replicates=${replicates}`);

      const summaryRows = [];
      const traceRows = [];
      const runMeta = {
        planName,
        runIso,
        version: this.version,
        basins,
        replicates,
        grid: plan?.grid || {},
        scenario,
        measurement,
        timing,
        notes: plan?.notes ?? "",
      };

      try {
        let runIdx = 0;
        for (const gp of gridPoints) {
          for (const basinId of basins) {
            for (let rep = 1; rep <= replicates; rep++) {
              if (this._stopFlag) throw new Error("Stopped by user.");

              runIdx++;
              const runId = `${planName}__${runIso}__r${String(runIdx).padStart(4, "0")}`;
              console.log(`[solAutoMap] run ${runIdx}: basin=${basinId} rep=${rep} params=${JSON.stringify(gp)}`);

              const out = await runSingle({
                phy,
                runId,
                planName,
                basinId,
                replicate: rep,
                gridPoint: gp,
                scenario,
                measurement,
                timing,
                baselineSnap,
                appOverrides,
                phyOverrides,
                engine,
              });

              summaryRows.push(out.summaryRow);
              traceRows.push(...out.traceRows);
            }
          }
        }
      } finally {
        // Always restore UI loop state.
        if (freeze.ok) unfreezeLiveLoop(freeze.prevDtCap);
      }

      // Legacy single-plan naming (kept for backwards compatibility):
      // solAutoMap__<planName>__<iso>__summary.csv
      const base = `solAutoMap__${planName}__${runIso}`;
      downloadCSVUnion(`${base}__summary.csv`, summaryRows);
      downloadCSVUnion(`${base}__trace.csv`, traceRows);
      downloadText(
        `${base}__manifest.json`,
        JSON.stringify({ ...runMeta, summaryRows: summaryRows.length, traceRows: traceRows.length }, null, 2),
        "application/json"
      );

      console.log(`[solAutoMap] complete. downloads: ${base}__summary.csv, ${base}__trace.csv, ${base}__manifest.json`);
      return { summaryRows, traceRows, manifest: runMeta };
    },

    // Master runner: sequential sweeps (classes) -> per-sweep bundles + combined MASTER bundle.
    // Naming:
    //   solAutoMap__<masterName>__<masterIso>__<sweepName>__summary.csv
    //   solAutoMap__<masterName>__<masterIso>__<sweepName>__trace.csv
    //   solAutoMap__<masterName>__<masterIso>__<sweepName>__manifest.json
    // And combined:
    //   solAutoMap__<masterName>__<masterIso>__MASTER__summary.csv
    //   solAutoMap__<masterName>__<masterIso>__MASTER__trace.csv
    //   solAutoMap__<masterName>__<masterIso>__MASTER__manifest.json
    async runMaster(masterPlan) {
      const masterName = this._sanitizeName(masterPlan?.masterName ?? masterPlan?.planName ?? "master_map");
      const masterIso = isoTag();
      const phy = getPhysics();

      const freeze = freezeLiveLoop();
      if (freeze.ok) console.log("[solAutoMap] live loop frozen (dtCap=0)");

      const baselineSnap = snapshotState(phy);

      const defaultScenario = masterPlan?.defaults?.scenario || { type: "inject_then_watch", injectAmount: 120, preSteps: 2, preDt: 0.12 };
      const defaultMeasurement = masterPlan?.defaults?.measurement || { durationMs: 60000, everyMs: 200, dt: 0.12, includeBackgroundEdges: false };
      const defaultTiming = masterPlan?.defaults?.timing || { timingMode: "tight", spinWaitMs: 2.0 };
      const defaultEngine = masterPlan?.defaults?.engine || { strictStepParams: true };
      const defaultBasins = Array.isArray(masterPlan?.defaults?.basins) && masterPlan.defaults.basins.length
        ? masterPlan.defaults.basins
        : [90, 82];
      const defaultReplicates = Math.max(1, Number(masterPlan?.defaults?.replicates ?? 1) | 0);

      const sweeps = Array.isArray(masterPlan?.sweeps) ? masterPlan.sweeps : [];
      if (!sweeps.length) throw new Error("[solAutoMap] masterPlan.sweeps is empty. Add at least one sweep.");

      const masterSummaryRows = [];
      const masterTraceRows = [];
      const sweepManifests = [];

      try {
        for (let sweepIdx = 0; sweepIdx < sweeps.length; sweepIdx++) {
          if (this._stopFlag) throw new Error("Stopped by user.");

          const sweep = sweeps[sweepIdx] || {};
          const sweepName = this._sanitizeName(sweep?.sweepName ?? sweep?.name ?? `sweep_${sweepIdx + 1}`);
          console.log(`[solAutoMap] sweep ${sweepIdx + 1}/${sweeps.length}: ${sweepName}`);

          const basins = Array.isArray(sweep?.basins) && sweep.basins.length ? sweep.basins : defaultBasins;
          const scenario = sweep?.scenario || defaultScenario;
          const measurement = sweep?.measurement || defaultMeasurement;
          const timing = sweep?.timing || defaultTiming;
          const engine = sweep?.engine || defaultEngine;
          const replicates = Math.max(1, Number(sweep?.replicates ?? defaultReplicates) | 0);
          const gridPoints = cartesianGrid(sweep?.grid || {});

          const appOverrides = sweep?.appConfigOverrides || masterPlan?.defaults?.appConfigOverrides || null;
          const phyOverrides = sweep?.physicsOverrides || masterPlan?.defaults?.physicsOverrides || null;

          const summaryRows = [];
          const traceRows = [];

          let runIdx = 0;
          for (const gp of gridPoints) {
            for (const basinId of basins) {
              for (let rep = 1; rep <= replicates; rep++) {
                if (this._stopFlag) throw new Error("Stopped by user.");
                runIdx++;

                const runId = `${masterName}__${masterIso}__${sweepName}__r${String(runIdx).padStart(4, "0")}`;
                const out = await runSingle({
                  phy,
                  runId,
                  planName: masterName,
                  basinId,
                  replicate: rep,
                  gridPoint: gp,
                  scenario,
                  measurement,
                  timing,
                  baselineSnap,
                  appOverrides,
                  phyOverrides,
                  engine,
                });

                // Tag rows with sweep class.
                out.summaryRow.masterName = masterName;
                out.summaryRow.masterIso = masterIso;
                out.summaryRow.sweepName = sweepName;
                summaryRows.push(out.summaryRow);

                for (const tr of out.traceRows) {
                  tr.masterName = masterName;
                  tr.masterIso = masterIso;
                  tr.sweepName = sweepName;
                  traceRows.push(tr);
                }
              }
            }
          }

          const sweepMeta = {
            masterName,
            masterIso,
            sweepName,
            sweepIndex: sweepIdx + 1,
            version: this.version,
            basins,
            replicates,
            grid: sweep?.grid || {},
            scenario,
            measurement,
            timing,
            notes: sweep?.notes ?? "",
            masterNotes: masterPlan?.notes ?? "",
            summaryRows: summaryRows.length,
            traceRows: traceRows.length,
          };
          sweepManifests.push(sweepMeta);

          const base = `solAutoMap__${masterName}__${masterIso}__${sweepName}`;
          downloadCSVUnion(`${base}__summary.csv`, summaryRows);
          downloadCSVUnion(`${base}__trace.csv`, traceRows);
          downloadText(`${base}__manifest.json`, JSON.stringify(sweepMeta, null, 2), "application/json");

          masterSummaryRows.push(...summaryRows);
          masterTraceRows.push(...traceRows);
        }
      } finally {
        if (freeze.ok) unfreezeLiveLoop(freeze.prevDtCap);
      }

      const masterMeta = {
        masterName,
        masterIso,
        version: this.version,
        notes: masterPlan?.notes ?? "",
        defaults: masterPlan?.defaults || {},
        sweeps: sweepManifests,
        summaryRows: masterSummaryRows.length,
        traceRows: masterTraceRows.length,
      };

      const masterBase = `solAutoMap__${masterName}__${masterIso}__MASTER`;
      downloadCSVUnion(`${masterBase}__summary.csv`, masterSummaryRows);
      downloadCSVUnion(`${masterBase}__trace.csv`, masterTraceRows);
      downloadText(`${masterBase}__manifest.json`, JSON.stringify(masterMeta, null, 2), "application/json");

      console.log(`[solAutoMap] master complete. base=${masterBase}`);
      return { masterMeta, masterSummaryRows, masterTraceRows };
    },
  };

  globalThis.solAutoMap = solAutoMap;
  console.log("[solAutoMap] loaded:", solAutoMap.version);
})();
