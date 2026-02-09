/* ============================================================================
   SOL Engine — Phase 3.10
   Mechanism Trace Sweep v1.7 (adds HOTSPOT RHO BLEED scopes)
   - Baseline restore (localStorage/SOLBaseline)
   - Telemetry: psi/p/rho + top-k + hotspots + flux around 64 + probes
   - Guardrails:
       * pLeak / rhoLeak => adaptive damping
       * bleed => can apply to "rho" or "p"
         NEW (applyTo:"rho"):
           - scope:"pMaxNode"  (bleed rho only at current pMax node)
           - scope:"topKp"     (bleed rho on top-K p nodes)
   ============================================================================ */

(() => {
  const NOW = () => new Date().toISOString().replace(/[:.]/g, "-");
  const sleep = (ms) => new Promise(r => setTimeout(r, ms));

  const getApp = () => globalThis.SOLDashboard || window.SOLDashboard;

  async function waitForAppPhysics({ timeoutMs = 20000, pollMs = 50 } = {}) {
    const t0 = performance.now();
    while (performance.now() - t0 < timeoutMs) {
      const app = getApp();
      const physics = app?.state?.physics;
      if (app && physics && Array.isArray(physics.nodes) && Array.isArray(physics.edges) && typeof physics.step === "function") {
        return { app, physics };
      }
      await sleep(pollMs);
    }
    throw new Error("solMechanismTraceSweepV1: App.state.physics not ready. Let dashboard finish initializing, then retry.");
  }

  function freezeLiveLoop(app) {
    if (!app?.config) return { didFreeze: false, prevDtCap: null };
    const prevDtCap = app.config.dtCap;
    app.config.dtCap = 0;
    return { didFreeze: true, prevDtCap };
  }

  function unfreezeLiveLoop(app, prevDtCap) {
    if (!app?.config) return;
    if (prevDtCap != null) app.config.dtCap = prevDtCap;
  }

  // ----------------------------
  // Math utils
  // ----------------------------
  const safeNum = (x) => (Number.isFinite(x) ? x : 0);
  const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
  const mean = (arr) => (arr.length ? arr.reduce((s, v) => s + v, 0) / arr.length : 0);
  const variance = (arr, m = mean(arr)) =>
    (arr.length ? arr.reduce((s, v) => s + (v - m) * (v - m), 0) / arr.length : 0);

  function pearsonCorr(xs, ys) {
    const n = Math.min(xs.length, ys.length);
    if (n < 2) return 0;
    const x = xs.slice(0, n).map(safeNum);
    const y = ys.slice(0, n).map(safeNum);
    const mx = mean(x), my = mean(y);
    let num = 0, dx = 0, dy = 0;
    for (let i = 0; i < n; i++) {
      const a = x[i] - mx;
      const b = y[i] - my;
      num += a * b;
      dx += a * a;
      dy += b * b;
    }
    const den = Math.sqrt(dx * dy);
    return den > 0 ? (num / den) : 0;
  }

  function smoothstep01(x) {
    const t = clamp(x, 0, 1);
    return t * t * (3 - 2 * t);
  }

  // ----------------------------
  // CSV download
  // ----------------------------
  function downloadCSV(filename, rows) {
    if (!rows.length) {
      console.warn("No rows to download:", filename);
      return;
    }
    const cols = Object.keys(rows[0]);
    const esc = (v) => {
      const s = String(v ?? "");
      return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
    };
    const lines = [cols.join(",")].concat(rows.map(r => cols.map(c => esc(r[c])).join(",")));
    const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 5000);
  }

  // ----------------------------
  // Baseline restore
  // ----------------------------
  function captureBaselineSnapshot(physics) {
    const snap = {
      nodes: (physics.nodes || []).map(n => {
        const out = {
          id: n?.id,
          rho: safeNum(n?.rho),
          p: safeNum(n?.p),
          psi: safeNum(n?.psi),
          psi_bias: safeNum(n?.psi_bias),
          semanticMass: safeNum(n?.semanticMass),
          semanticMass0: safeNum(n?.semanticMass0)
        };
        if (n?.isBattery) {
          out.b_q = safeNum(n?.b_q);
          out.b_charge = safeNum(n?.b_charge);
          out.b_state = (n?.b_state ?? null);
        }
        return out;
      }),
      edgeFlux: (physics.edges || []).map(e => safeNum(e?.flux))
    };

    return {
      schema: "__SOL_BASELINE_SNAP_V1",
      createdAt: NOW(),
      snap
    };
  }

  async function restoreBaseline({ baselineKey = "__SOL_BASELINE_SNAP_V1" } = {}) {
    if (globalThis.SOLBaseline?.restore && typeof globalThis.SOLBaseline.restore === "function") {
      await globalThis.SOLBaseline.restore();
      return { source: "SOLBaseline.restore()" };
    }
    if (globalThis.SOLBaseline?.ensure && typeof globalThis.SOLBaseline.ensure === "function") {
      await globalThis.SOLBaseline.ensure();
      return { source: "SOLBaseline.ensure()" };
    }

    const { physics } = await waitForAppPhysics();
    let raw = localStorage.getItem(baselineKey);
    if (!raw) {
      // Automation-friendly fallback: capture a baseline from the current initialized state.
      // This makes sweeps runnable out-of-the-box while keeping baseline explicit and reusable.
      const blob0 = captureBaselineSnapshot(physics);
      try { localStorage.setItem(baselineKey, JSON.stringify(blob0)); } catch (e) { /* no-op */ }
      raw = localStorage.getItem(baselineKey);
    }
    if (!raw) throw new Error(`No baseline found in localStorage["${baselineKey}"]. Install/run your SOLBaseline script first.`);
    const blob = JSON.parse(raw);
    const snap = blob?.snap;
    if (!snap?.nodes || !snap?.edgeFlux) throw new Error("Baseline blob missing snap.nodes or snap.edgeFlux");

    const byId = new Map((snap.nodes || []).map(s => [String(s.id), s]));
    for (const n of (physics.nodes || [])) {
      const s = byId.get(String(n.id));
      if (!s) continue;
      n.rho = s.rho;
      n.p = s.p;
      n.psi = s.psi;
      n.psi_bias = s.psi_bias;
      n.semanticMass = s.semanticMass;
      n.semanticMass0 = s.semanticMass0;
      if (n.isBattery) {
        n.b_q = s.b_q;
        n.b_charge = s.b_charge;
        n.b_state = s.b_state;
      }
    }
    const edges = physics.edges || [];
    for (let i = 0; i < edges.length; i++) {
      const e = edges[i];
      if (!e) continue;
      e.flux = (snap.edgeFlux && Number.isFinite(snap.edgeFlux[i])) ? snap.edgeFlux[i] : 0;
    }
    return { source: `localStorage["${baselineKey}"] (direct restore)` };
  }

  function getNodeByIdLoose(physics, id) {
    const want = String(id);
    for (const n of (physics.nodes || [])) {
      if (n && n.id != null && String(n.id) === want) return n;
    }
    return null;
  }

  function normalizeIdList(targetId, targetIds) {
    if (Array.isArray(targetIds) && targetIds.length) {
      return targetIds.map(x => String(x)).filter(s => s !== "");
    }
    if (typeof targetIds === "string" && targetIds.trim()) {
      return targetIds
        .split(/[|,]/g)
        .map(s => s.trim())
        .filter(s => s !== "");
    }
    return [String(targetId)];
  }

  function getPMaxNode(physics) {
    let best = null;
    let bestP = -Infinity;
    for (const n of (physics.nodes || [])) {
      const p = safeNum(n?.p);
      if (p > bestP) { bestP = p; best = n; }
    }
    return best;
  }

  function getTopKPNodes(physics, k = 3) {
    const nodes = (physics.nodes || []).slice();
    nodes.sort((a, b) => safeNum(b?.p) - safeNum(a?.p));
    return nodes.slice(0, Math.max(1, k));
  }

  // ----------------------------
  // Telemetry
  // ----------------------------
  function getEdgeEndpoints(edge) {
    const a = edge?.from ?? edge?.a ?? edge?.i ?? edge?.src ?? edge?.source;
    const b = edge?.to   ?? edge?.b ?? edge?.j ?? edge?.dst ?? edge?.target;
    return { a, b };
  }

  function topKAbs(values, ids, k) {
    const arr = values.map((v, i) => ({ v: Math.abs(safeNum(v)), id: ids[i] }));
    arr.sort((x, y) => y.v - x.v);
    const top = arr.slice(0, k);
    const sumTop = top.reduce((s, x) => s + x.v, 0);
    return { topIds: top.map(x => x.id), sumTop };
  }

  function computeIncidentFluxStats(physics, targetId) {
    const want = String(targetId);
    const fluxAbs = [];
    const neighborPsi = [];
    const neighborP = [];

    const nodeById = new Map((physics.nodes || []).map(n => [String(n.id), n]));

    for (const e of (physics.edges || [])) {
      if (!e) continue;
      const { a, b } = getEdgeEndpoints(e);
      if (a == null || b == null) continue;

      const sa = String(a), sb = String(b);
      if (sa !== want && sb !== want) continue;

      const f = Math.abs(safeNum(e.flux));
      fluxAbs.push(f);

      const otherId = (sa === want) ? sb : sa;
      const n = nodeById.get(otherId);
      if (n) {
        neighborPsi.push(safeNum(n.psi));
        neighborP.push(safeNum(n.p));
      }
    }

    const incidentFluxAbs = fluxAbs.reduce((s, x) => s + x, 0);
    return {
      incidentFluxAbs,
      fluxCorrPsi: pearsonCorr(neighborPsi, fluxAbs),
      fluxCorrP: pearsonCorr(neighborP, fluxAbs),
    };
  }

  function probeTelemetry(physics, probeIds) {
    const out = {};
    for (const id of (probeIds || [])) {
      const n = getNodeByIdLoose(physics, id);
      out[`p_${id}`] = n ? safeNum(n.p) : 0;
      out[`rho_${id}`] = n ? safeNum(n.rho) : 0;
      out[`psi_${id}`] = n ? safeNum(n.psi) : 0;
    }
    return out;
  }

  function computeTelemetry(physics, { psiTopK = 5, pTopK = 5, targetId = 64, probeIds = [] } = {}) {
    const nodes = physics.nodes || [];
    const ids = nodes.map(n => String(n.id));

    const psis = nodes.map(n => safeNum(n.psi));
    const psisAbs = psis.map(Math.abs);
    const psiMean = mean(psis);
    const psiVar = variance(psis, psiMean);
    const psiAbsSum = psisAbs.reduce((s, x) => s + x, 0);

    let psiMax = -Infinity, psiMaxId = "";
    for (const n of nodes) {
      const v = safeNum(n.psi);
      if (v > psiMax) { psiMax = v; psiMaxId = String(n.id); }
    }

    const psiTop = topKAbs(psis, ids, psiTopK);
    const psiTopFrac = psiAbsSum > 0 ? (psiTop.sumTop / psiAbsSum) : 0;

    const ps = nodes.map(n => safeNum(n.p));
    const meanP = mean(ps);
    const pVar = variance(ps, meanP);

    let pMax = -Infinity, pMaxId = "";
    for (const n of nodes) {
      const v = safeNum(n.p);
      if (v > pMax) { pMax = v; pMaxId = String(n.id); }
    }
    const pTop = topKAbs(ps, ids, pTopK);

    const rhos = nodes.map(n => safeNum(n.rho));
    const rhoSum = rhos.reduce((s, x) => s + x, 0);
    const rhoEps = 1e-9;
    const rhoActiveCount = rhos.reduce((c, x) => c + (x > rhoEps ? 1 : 0), 0);
    const rhoEntropy = (rhoSum > 0)
      ? -rhos.reduce((s, x) => {
          const p = x / rhoSum;
          return (p > 0) ? (s + p * Math.log(p)) : s;
        }, 0)
      : 0;
    const rhoEffN = Math.exp(rhoEntropy);
    let rhoMax = -Infinity, rhoMaxId = "";
    for (const n of nodes) {
      const v = safeNum(n.rho);
      if (v > rhoMax) { rhoMax = v; rhoMaxId = String(n.id); }
    }

    const { incidentFluxAbs, fluxCorrPsi, fluxCorrP } = computeIncidentFluxStats(physics, targetId);

    return {
      meanP,
      pVar,
      pMax,
      pMaxId,
      pTopSum: pTop.sumTop,
      pTopIds: pTop.topIds.join("|"),

      psiMean,
      psiVar,
      psiMax,
      psiMaxId,
      psiAbsSum,
      psiTopSum: psiTop.sumTop,
      psiTopFrac,
      psiTopIds: psiTop.topIds.join("|"),

      rhoSum,
      rhoActiveCount,
      rhoEntropy,
      rhoEffN,
      rhoMax,
      rhoMaxId,

      incidentFluxAbs64: incidentFluxAbs,
      fluxCorrPsi64: fluxCorrPsi,
      fluxCorrP64: fluxCorrP,

      ...probeTelemetry(physics, probeIds),
    };
  }

  // ----------------------------
  // Guardrails
  // ----------------------------
  function dampFromDrive(baseDamp, drive, soft, span, gain) {
    const x = (safeNum(drive) - safeNum(soft)) / Math.max(1e-12, safeNum(span));
    return baseDamp * (1 + safeNum(gain) * smoothstep01(x));
  }

  function computeDampEff(step, baseDamp, tel, guardrail, guardrailStartStep) {
    if (!guardrail || guardrail.type === "none") return baseDamp;
    if (step < guardrailStartStep) return baseDamp;

    const gain = safeNum(guardrail.gain ?? 6.0);

    if (guardrail.type === "pLeak") {
      return dampFromDrive(baseDamp, tel.meanP, guardrail.meanPSoft ?? 0.003, guardrail.meanPSpan ?? 0.01, gain);
    }
    if (guardrail.type === "rhoLeak") {
      return dampFromDrive(baseDamp, tel.rhoSum, guardrail.rhoSumSoft ?? 3.0, guardrail.rhoSumSpan ?? 8.0, gain);
    }
    return baseDamp;
  }

  // bleedCfg.type chooses the DRIVE (what triggers bleed)
  // bleedCfg.applyTo chooses the STATE VARIABLE we modify ("rho" default, or "p")
  // bleedCfg.scope chooses WHERE we apply it
  function computeBleedFrac(step, tel, bleedCfg, guardrailStartStep) {
    if (!bleedCfg || bleedCfg.type === "none") return 0;
    if (step < guardrailStartStep) return 0;

    const bleedMax = clamp(safeNum(bleedCfg.bleedMax ?? 0.02), 0, 0.2);
    let drive = 0, soft = 0, span = 1;

    if (bleedCfg.type === "p") {
      drive = tel.meanP;
      soft = safeNum(bleedCfg.meanPSoft ?? 0.003);
      span = safeNum(bleedCfg.meanPSpan ?? 0.02);
    } else if (bleedCfg.type === "pMax") {
      drive = tel.pMax;
      soft = safeNum(bleedCfg.pMaxSoft ?? 2.0);
      span = safeNum(bleedCfg.pMaxSpan ?? 6.0);
    } else if (bleedCfg.type === "rhoSum") {
      drive = tel.rhoSum;
      soft = safeNum(bleedCfg.rhoSumSoft ?? 10);
      span = safeNum(bleedCfg.rhoSumSpan ?? 20);
    } else if (bleedCfg.type === "rho82") {
      drive = safeNum(tel.rho_82 ?? 0);
      soft = safeNum(bleedCfg.rho82Soft ?? 2);
      span = safeNum(bleedCfg.rho82Span ?? 6);
    } else if (bleedCfg.type === "psiTopFrac") {
      drive = tel.psiTopFrac;
      soft = safeNum(bleedCfg.psiTopSoft ?? 0.20);
      span = safeNum(bleedCfg.psiTopSpan ?? 0.10);
    } else {
      return 0;
    }

    const x = (safeNum(drive) - soft) / Math.max(1e-12, span);
    return bleedMax * smoothstep01(x);
  }

  function applyBleed(physics, bleedCfg, bleedFrac) {
    if (!bleedCfg || bleedCfg.type === "none") return;
    if (bleedFrac <= 0) return;

    const applyTo = (bleedCfg.applyTo || "rho"); // "rho" (default) or "p"
    const scope = (bleedCfg.scope || "global");  // "global", "nodeId", "pMaxNode", "topKp"

    // -------- RHO BLEED --------
    if (applyTo === "rho") {
      if (bleedCfg.type === "rho82") {
        const n = getNodeByIdLoose(physics, 82);
        if (n) n.rho = safeNum(n.rho) * (1 - bleedFrac);
        return;
      }

      if (scope === "nodeId") {
        const n = getNodeByIdLoose(physics, bleedCfg.nodeId);
        if (n) n.rho = safeNum(n.rho) * (1 - bleedFrac);
        return;
      }

      if (scope === "pMaxNode") {
        const n = getPMaxNode(physics);
        if (n) n.rho = safeNum(n.rho) * (1 - bleedFrac);
        return;
      }

      if (scope === "topKp") {
        const k = Math.max(1, safeNum(bleedCfg.k ?? 3));
        const nodes = getTopKPNodes(physics, k);
        for (const n of nodes) {
          n.rho = safeNum(n.rho) * (1 - bleedFrac);
        }
        return;
      }

      // default global
      for (const n of (physics.nodes || [])) {
        n.rho = safeNum(n.rho) * (1 - bleedFrac);
      }
      return;
    }

    // -------- PRESSURE BLEED --------
    // Optional local gate so we only bleed high-p nodes (less sedation).
    const pSoft = safeNum(bleedCfg.pNodeSoft ?? 1.0);
    const pSpan = Math.max(1e-12, safeNum(bleedCfg.pNodeSpan ?? 5.0));

    const bleedNodeP = (n) => {
      const p = safeNum(n.p);
      const localGate = smoothstep01((p - pSoft) / pSpan);
      const eff = clamp(bleedFrac * localGate, 0, 0.5);
      if (eff > 0) n.p = p * (1 - eff);
    };

    if (scope === "nodeId") {
      const n = getNodeByIdLoose(physics, bleedCfg.nodeId);
      if (n) bleedNodeP(n);
      return;
    }

    if (scope === "pMaxNode") {
      const n = getPMaxNode(physics);
      if (n) bleedNodeP(n);
      return;
    }

    if (scope === "topKp") {
      const k = Math.max(1, safeNum(bleedCfg.k ?? 3));
      const nodes = getTopKPNodes(physics, k);
      for (const n of nodes) bleedNodeP(n);
      return;
    }

    // default global
    for (const n of (physics.nodes || [])) bleedNodeP(n);
  }

  // ----------------------------
  // Main API
  // ----------------------------
  const API = {
    version: "sol_phase310_mechanismTraceSweep_v1_7",
    abort: false,

    async mechanismTraceSweep({
      dts = [0.12, 0.16],
      dampings = [2, 3, 4, 5, 6],
      modes = ["pulse100"],

      pressSliderVal = 200,
      pressCOverride = null,
      steps = 4000,

      failureMeanP = 0.5,
      failureHoldSteps = 20,

      traceEvery = 75,
      progressEvery = 250,

      adaptiveTrace = true,
      traceEveryHot = 5,
      hotStartStep = 200,
      hotMeanP = 0.05,
      hotPMax = 2.0,
      hotRhoSum = 5.0,

      guardrailStartStep = 200,

      targetId = 64,
      targetIds = null,
      injectAmount = 10,
      pulseStep = 100,
      pulseEvery = 0,
      pulseCount = 0,
      targetsPerPulse = 1,

      probeIds = [64, 82, 79],

      guardrail = { type: "none" },
      baselineKey = "__SOL_BASELINE_SNAP_V1",
      outPrefix = "sol_phase310_mechTrace",
    } = {}) {
      this.abort = false;

      const runId = NOW();
      const guardrailLabel = guardrail?.type || "none";
      const bleedLabel = guardrail?.bleed?.type || "none";
      const bleedTo = guardrail?.bleed?.applyTo || "rho";
      const bleedScope = guardrail?.bleed?.scope || "global";

      const summaryRows = [];
      const traceRows = [];

      const { app, physics } = await waitForAppPhysics();
      const fr = freezeLiveLoop(app);

      const pressScale = safeNum(app?.config?.pressureSliderScale ?? 0.1);
      const pressC = (pressCOverride != null) ? safeNum(pressCOverride) : safeNum(pressSliderVal) * pressScale;

      console.log(`[P3.10 v1.7] pressSliderVal=${pressSliderVal} scale=${pressScale} => pressC=${pressC}` +
                  (pressCOverride != null ? " (override)" : ""));

      for (const dt of dts) {
        for (const baseDamp of dampings) {
          for (const mode of modes) {
            if (this.abort) break;

            const baselineInfo = await restoreBaseline({ baselineKey });

            let consecHigh = 0;
            let failStep = "";
            let failReason = "";

            let tel0 = computeTelemetry(physics, { targetId, probeIds });
            let peakMeanP = tel0.meanP;
            let peakPMax = tel0.pMax;
            let peakPsiVar = tel0.psiVar;

            let didPulse = false;
            let pulseIdx = 0;
            let rrIdx = 0;
            let hot = false;

            const injTargets = normalizeIdList(targetId, targetIds);
            const injTargetsPerPulse = Math.max(1, Math.min(injTargets.length, Math.floor(safeNum(targetsPerPulse) || 1)));
            const injEvery = Math.max(0, Math.floor(safeNum(pulseEvery) || 0));
            const injCountMax = Math.max(0, Math.floor(safeNum(pulseCount) || 0));

            function shouldPulse(step) {
              if (mode === "pulse100") return (!didPulse && step === pulseStep);
              if (mode === "pulseTrain" || mode === "multiAgentTrain") {
                if (step < pulseStep) return false;
                if (injCountMax > 0 && pulseIdx >= injCountMax) return false;
                const every = injEvery > 0 ? injEvery : 1;
                return ((step - pulseStep) % every) === 0;
              }
              return false;
            }

            function doPulse(physics) {
              if (!injTargets.length) return;
              const k = (mode === "multiAgentTrain" || mode === "pulseTrain") ? injTargetsPerPulse : 1;
              for (let j = 0; j < k; j++) {
                const id = injTargets[(rrIdx + j) % injTargets.length];
                const n = getNodeByIdLoose(physics, id);
                if (n) n.rho = safeNum(n.rho) + safeNum(injectAmount);
              }
              rrIdx = (rrIdx + k) % injTargets.length;
              pulseIdx++;
            }

            traceRows.push({
              runId, dt, damping: baseDamp, mode,
              dampingSource: "physics.step",
              dampSliderVal: (app?.dom?.dampSlider?.value ?? ""),
              dampSliderStep: (app?.dom?.dampSlider?.step ?? ""),
              guardrail: guardrailLabel,
              bleed: bleedLabel,
              bleedTo,
              bleedScope,
              step: 0, pressSliderVal, pressC, targetId,
              injectAmount, pulseStep, pulseEvery: injEvery, pulseCount: injCountMax, targetsPerPulse: injTargetsPerPulse,
              injectTargets: injTargets.join("|"),
              probeIds: probeIds.join("|"),
              baselineSource: baselineInfo.source,
              dampEff: baseDamp,
              bleedFrac: 0,
              hot: 0,
              ...tel0
            });

            for (let step = 1; step <= steps; step++) {
              if (this.abort) break;

              if (shouldPulse(step)) {
                doPulse(physics);
                didPulse = didPulse || (mode === "pulse100");
              }

              // telemetry BEFORE applying guardrail
              const telPre = computeTelemetry(physics, { targetId, probeIds });

              if (adaptiveTrace && step >= hotStartStep) {
                hot = hot || (telPre.meanP > hotMeanP) || (telPre.pMax > hotPMax) || (telPre.rhoSum > hotRhoSum);
              }

              // BLEED (constitutive) — pre-step
              const bleedFrac = computeBleedFrac(step, telPre, guardrail?.bleed, guardrailStartStep);
              applyBleed(physics, guardrail?.bleed, bleedFrac);

              // DAMPING guardrail
              const dampEff = computeDampEff(step, baseDamp, telPre, guardrail, guardrailStartStep);

              physics.step(dt, pressC, dampEff);

              const tel = computeTelemetry(physics, { targetId, probeIds });

              peakMeanP = Math.max(peakMeanP, safeNum(tel.meanP));
              peakPMax = Math.max(peakPMax, safeNum(tel.pMax));
              peakPsiVar = Math.max(peakPsiVar, safeNum(tel.psiVar));

              if (safeNum(tel.meanP) > failureMeanP) consecHigh++;
              else consecHigh = 0;

              const cadence = (adaptiveTrace && hot) ? traceEveryHot : traceEvery;
              const shouldTrace =
                (step % cadence === 0) ||
                (consecHigh === failureHoldSteps) ||
                (step === steps);

              if (shouldTrace) {
                traceRows.push({
                  runId, dt, damping: baseDamp, mode,
                  dampingSource: "physics.step",
                  dampSliderVal: (app?.dom?.dampSlider?.value ?? ""),
                  dampSliderStep: (app?.dom?.dampSlider?.step ?? ""),
                  guardrail: guardrailLabel,
                  bleed: bleedLabel,
                  bleedTo,
                  bleedScope,
                  step, pressSliderVal, pressC, targetId,
                  injectAmount, pulseStep, pulseEvery: injEvery, pulseCount: injCountMax, targetsPerPulse: injTargetsPerPulse,
                  injectTargets: injTargets.join("|"),
                  probeIds: probeIds.join("|"),
                  baselineSource: baselineInfo.source,
                  dampEff,
                  bleedFrac,
                  hot: hot ? 1 : 0,
                  ...tel
                });
              }

              if (step % progressEvery === 0) {
                console.log(
                  `[P3.10 v1.7] dt=${dt} damp=${baseDamp} step=${step}/${steps}` +
                  ` meanP=${safeNum(tel.meanP).toFixed(4)} pMax=${safeNum(tel.pMax).toFixed(4)}` +
                  ` rhoSum=${safeNum(tel.rhoSum).toFixed(3)} rho82=${safeNum(tel.rho_82).toFixed(3)} rho79=${safeNum(tel.rho_79).toFixed(3)}` +
                  ` hot=${hot?1:0} dampEff=${safeNum(dampEff).toFixed(2)} bleedFrac=${safeNum(bleedFrac).toFixed(4)}`
                );
              }

              if (consecHigh >= failureHoldSteps) {
                failStep = step;
                failReason = `meanP>${failureMeanP} for ${failureHoldSteps} steps`;
                console.warn(`[P3.10 v1.7] FAIL dt=${dt} damp=${baseDamp} @ step=${step} (${failReason})`);
                break;
              }
            }

            summaryRows.push({
              runId, dt, damping: baseDamp, mode,
              dampingSource: "physics.step",
              dampSliderVal: (app?.dom?.dampSlider?.value ?? ""),
              dampSliderStep: (app?.dom?.dampSlider?.step ?? ""),
              guardrail: guardrailLabel,
              bleed: bleedLabel,
              bleedTo,
              bleedScope,
              pressSliderVal, pressC, targetId,
              injectAmount, pulseStep, pulseEvery: injEvery, pulseCount: injCountMax, targetsPerPulse: injTargetsPerPulse,
              injectTargets: injTargets.join("|"),
              probeIds: probeIds.join("|"),
              stepsPlanned: steps,
              failed: failStep !== "" ? 1 : 0,
              failStep: failStep === "" ? steps : failStep,
              failReason,
              peakMeanP,
              peakPMax,
              peakPsiVar
            });

            if (this.abort) break;
          }
          if (this.abort) break;
        }
        if (this.abort) break;
      }

      if (fr.didFreeze) unfreezeLiveLoop(app, fr.prevDtCap);

      const stamp = NOW();
      downloadCSV(`${outPrefix}_summary_${stamp}.csv`, summaryRows);
      downloadCSV(`${outPrefix}_trace_${stamp}.csv`, traceRows);

      console.log(`[P3.10 v1.7] Done. Rows: summary=${summaryRows.length}, trace=${traceRows.length}`);
      return { summaryRows, traceRows };
    }
  };

  globalThis.solMechanismTraceSweepV1 = API;

  (async () => {
    try {
      const { app, physics } = await waitForAppPhysics();
      console.log("[P3.10 v1.7] Installed:", API.version);
      console.log("[P3.10 v1.7] Physics diagnostics:", {
        nodes: physics.nodes?.length,
        edges: physics.edges?.length,
        pressureSliderScale: app?.config?.pressureSliderScale,
        dtCap: app?.config?.dtCap
      });
    } catch (e) {
      console.warn("[P3.10 v1.7] Installed, but physics not ready yet:", e?.message || e);
    }
  })();
})();
