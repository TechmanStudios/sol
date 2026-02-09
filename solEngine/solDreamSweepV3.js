(() => {
  // solDreamSweepV3 — Dream excitation + afterstate watch (summary + trace)
  // Fix vs V2: runOne can now download files directly (optional).
  //
  // Usage:
  //   await solDreamSweepV3.runOne({ label:"sanity", download:"both" })
  //   await solDreamSweepV3.runOneAndDownload({ label:"sanity2", injectorIds:[64,82], pattern:"strobe" })
  //   await solDreamSweepV3.quickSweep()  // still downloads summary+trace
  //   solDreamSweepV3.downloadLast("both") // export last run anytime

  const sleep = (ms) => new Promise(r => setTimeout(r, ms));
  const safe = (x) => (Number.isFinite(x) ? x : 0);

  const isoStamp = () => new Date().toISOString();
  const isoFileStamp = () => new Date().toISOString().replace(/[:.]/g, "-");

  function sanitizeForFile(s, maxLen = 80) {
    const out = String(s ?? "")
      .replace(/\s+/g, "_")
      .replace(/[^a-zA-Z0-9_\-]+/g, "_")
      .replace(/_+/g, "_")
      .replace(/^_+|_+$/g, "");
    return out.length > maxLen ? out.slice(0, maxLen) : out;
  }

  function getRoot() {
    return globalThis.SOLDashboard ?? globalThis.App ?? globalThis.app ?? null;
  }

  async function waitForPhysics({ timeoutMs = 8000, pollMs = 100 } = {}) {
    const t0 = performance.now();
    while ((performance.now() - t0) < timeoutMs) {
      const root = getRoot();
      const physics = root?.state?.physics;
      if (physics?.nodes && Array.isArray(physics.nodes) && physics.nodes.length) return physics;
      await sleep(pollMs);
    }
    throw new Error("Physics not ready. Make sure dashboard v3.6 is running and initialized.");
  }

  function nodeById(physics, id) {
    const m = physics?.nodeById?.get?.(id);
    if (m) return m;
    return (physics.nodes || []).find(n => n?.id === id) || null;
  }

  // ---------------- Telemetry ----------------
  function entropyRhoNorm(nodes) {
    let sumRho = 0;
    for (const n of nodes) sumRho += safe(n?.rho);
    if (sumRho <= 0) return 0;

    let H = 0;
    for (const n of nodes) {
      const p = safe(n?.rho) / sumRho;
      if (p > 0) H -= p * Math.log(p);
    }
    const Hmax = Math.log(Math.max(1, nodes.length));
    return Hmax > 0 ? (H / Hmax) : 0;
  }

  function rhoStats(nodes) {
    let rhoSum = 0, rhoMax = -Infinity, rhoMaxId = "";
    for (const n of nodes) {
      const r = safe(n?.rho);
      rhoSum += r;
      if (r > rhoMax) { rhoMax = r; rhoMaxId = String(n?.id ?? ""); }
    }
    const rhoConc = rhoSum > 0 ? (rhoMax / rhoSum) : 0;
    return { rhoSum, rhoMax, rhoMaxId, rhoConc };
  }

  function pStats(nodes) {
    let pSum = 0, pMax = -Infinity, pMaxId = "";
    const ps = [];
    for (const n of nodes) {
      const p = safe(n?.p);
      ps.push(p);
      pSum += p;
      if (p > pMax) { pMax = p; pMaxId = String(n?.id ?? ""); }
    }
    const meanP = ps.length ? (pSum / ps.length) : 0;
    let varP = 0;
    for (const p of ps) varP += (p - meanP) * (p - meanP);
    varP = ps.length ? (varP / ps.length) : 0;
    return { meanP, varP, pMax, pMaxId };
  }

  function psiStats(nodes, topK = 5) {
    const arr = [];
    let sumAbs = 0;
    let maxAbs = -Infinity;
    let psiMaxId = "";
    for (const n of nodes) {
      const v = Math.abs(safe(n?.psi));
      arr.push([v, n?.id]);
      sumAbs += v;
      if (v > maxAbs) { maxAbs = v; psiMaxId = String(n?.id ?? ""); }
    }
    arr.sort((a,b) => b[0] - a[0]);
    const topSum = arr.slice(0, topK).reduce((s,[v]) => s+v, 0);
    const topFrac = sumAbs > 0 ? (topSum / sumAbs) : 0;
    const psiTopIds = arr.slice(0, topK).map(x => x[1]).join("|");
    const meanAbs = arr.length ? (sumAbs / arr.length) : 0;
    return { psiAbsSum: sumAbs, psiAbsMean: meanAbs, psiAbsMax: maxAbs, psiMaxId, psiTopFrac: topFrac, psiTopIds };
  }

  function fluxStats(edges) {
    let sumAbs = 0, maxAbs = 0;
    for (const e of edges || []) {
      const f = Math.abs(safe(e?.flux));
      sumAbs += f;
      if (f > maxAbs) maxAbs = f;
    }
    return { sumAbsFlux: sumAbs, maxAbsFlux: maxAbs };
  }

  function sampleState(physics, psiTopK = 5) {
    const nodes = physics.nodes || [];
    const edges = physics.edges || [];
    const ent = entropyRhoNorm(nodes);
    const rs = rhoStats(nodes);
    const ps = pStats(nodes);
    const qs = psiStats(nodes, psiTopK);
    const fs = fluxStats(edges);
    return { ent, rs, ps, qs, fs };
  }

  // ---------------- CSV download ----------------
  function downloadCSV(filename, rows) {
    if (!rows?.length) return;
    const cols = Object.keys(rows[0]);
    const esc = (v) => {
      const s = String(v ?? "");
      return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
    };
    const lines = [cols.join(",")].concat(rows.map(r => cols.map(c => esc(r[c])).join(",")));
    const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    const url = URL.createObjectURL(blob);
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 5000);
  }

  // ---------------- Dream patterns ----------------
  const Patterns = {
    roundRobin: (injectorIds, tick) => [injectorIds[tick % injectorIds.length]],
    burstAll: (injectorIds) => injectorIds.slice(),
    strobe: (injectorIds, tick, strobeTicks=10) => {
      const idx = Math.floor(tick / strobeTicks) % injectorIds.length;
      return [injectorIds[idx]];
    },
    pairSwap: (injectorIds, tick) => {
      if (injectorIds.length < 2) return injectorIds.slice();
      const mid = Math.floor(injectorIds.length / 2);
      const a = injectorIds.slice(0, mid);
      const b = injectorIds.slice(mid);
      return (tick % 2 === 0) ? a : b;
    }
  };

  function applyInjection(physics, ids, { injectP=0, injectRho=0, injectPsi=0 }) {
    let ok = 0;
    for (const id of ids) {
      const n = nodeById(physics, id);
      if (!n) continue;
      if (typeof n.p === "number" && injectP) n.p += injectP;
      if (typeof n.rho === "number" && injectRho) n.rho += injectRho;
      if (typeof n.psi === "number" && injectPsi) n.psi += injectPsi;
      ok++;
    }
    return ok;
  }

  function mode(arr) {
    const m = new Map();
    for (const x of arr) m.set(x, (m.get(x) || 0) + 1);
    let best = "", bestC = -1;
    for (const [k,c] of m.entries()) if (c > bestC) { best = k; bestC = c; }
    return best;
  }

  function uniqCount(arr) {
    return new Set(arr).size;
  }

  function firstTimeBelow(rows, key, frac) {
    if (!rows.length) return NaN;
    const v0 = safe(rows[0][key]);
    if (v0 <= 0) return NaN;
    const thr = v0 * frac;
    for (const r of rows) if (safe(r[key]) <= thr) return safe(r.tSec);
    return NaN;
  }

  function argmax(rows, key) {
    let bestI = -1, bestV = -Infinity;
    for (let i = 0; i < rows.length; i++) {
      const v = safe(rows[i][key]);
      if (v > bestV) { bestV = v; bestI = i; }
    }
    return { i: bestI, v: bestV };
  }

  function countIdSwitches(rows, key) {
    let switches = 0;
    let prev = null;
    for (const r of rows) {
      const cur = String(r[key] ?? "");
      if (prev != null && cur !== prev) switches++;
      prev = cur;
    }
    return switches;
  }

  function firstSwitchTime(rows, key) {
    if (!rows.length) return NaN;
    const first = String(rows[0][key] ?? "");
    for (const r of rows) {
      if (String(r[key] ?? "") !== first) return safe(r.tSec);
    }
    return NaN;
  }

  function maybeDownloadRun({ summary, rows }, { download, filenamePrefix, label }) {
    const dl = (download ?? "none").toLowerCase();
    if (dl === "none") return;

    const stamp = isoFileStamp();
    const prefix = sanitizeForFile(filenamePrefix ?? "sol_dreamRun");
    const lab = sanitizeForFile(label ?? "run");
    const base = `${prefix}__${lab}__${stamp}`;

    if (dl === "summary" || dl === "both") {
      downloadCSV(`${base}__summary.csv`, [summary]);
    }
    if (dl === "trace" || dl === "both") {
      downloadCSV(`${base}__trace.csv`, rows);
    }
  }

  // ---------------- Core: runOne ----------------
  async function runOne(cfg) {
    const {
      // identity
      label = "run",
      runIndex = 0,

      // download
      download = "none",          // "none" | "summary" | "trace" | "both"
      filenamePrefix = "sol_dreamRun",

      // baseline
      restoreBaseline = true,

      // dream
      dreamSeconds = 4,
      dreamEveryMs = 100,
      pattern = "roundRobin",
      strobeTicks = 10,
      injectorIds = [64,82,79,90],

      // injection comparability:
      // - "perNode": inject* applied per fired node
      // - "budgetPerTick": dreamBudget* totals per tick divided across fired nodes
      dreamInjectMode = "budgetPerTick",
      injectP = 5,
      injectRho = 25,
      injectPsi = 0,
      dreamBudgetPPerTick = 10,
      dreamBudgetRhoPerTick = 120,
      dreamBudgetPsiPerTick = 0,

      dreamStepPerTick = 0,

      // rest watch
      restSeconds = 120,
      restEveryMs = 200,
      restMode = "live",      // "live" or "step"

      autoStepIfFrozen = false,
      frozenTolerance = 1e-10,
      frozenSamplesToTrigger = 10,

      // stepping params
      stepDt = 0.12,
      stepDamping = 4,
      stepPressC = 20,
      restStepsPerSample = 5,

      // telemetry
      psiTopK = 5,

      // logging
      progressEverySamples = 25,
      progressEveryDreamTicks = 10
    } = cfg;

    await waitForPhysics();

    if (restoreBaseline) {
      if (!globalThis.SOLBaseline?.restore) {
        throw new Error("SOLBaseline.restore() not found. Load your baseline script first.");
      }
      await globalThis.SOLBaseline.restore();
      await waitForPhysics(); // baseline restore might rebuild physics
    }

    const physics = await waitForPhysics();
    const stamp = isoStamp();

    const patFn = Patterns[pattern];
    if (!patFn) throw new Error(`Unknown pattern "${pattern}". Use: ${Object.keys(Patterns).join(", ")}`);

    const dreamTicks = Math.max(1, Math.round((dreamSeconds * 1000) / dreamEveryMs));
    let totalInjectedP = 0, totalInjectedRho = 0, totalInjectedPsi = 0;

    console.log(`🧠 [DreamSweepV3] START ${label} idx=${runIndex} pattern=${pattern} mode=${dreamInjectMode} ids=[${injectorIds.join(",")}]`);

    // DREAM phase
    for (let tick = 0; tick < dreamTicks; tick++) {
      const fireIds = (pattern === "strobe")
        ? Patterns.strobe(injectorIds, tick, strobeTicks)
        : patFn(injectorIds, tick);

      let pPer = injectP, rPer = injectRho, psiPer = injectPsi;

      if (dreamInjectMode === "budgetPerTick") {
        const k = Math.max(1, fireIds.length);
        pPer = dreamBudgetPPerTick / k;
        rPer = dreamBudgetRhoPerTick / k;
        psiPer = dreamBudgetPsiPerTick / k;
      }

      pPer = safe(pPer); rPer = safe(rPer); psiPer = safe(psiPer);

      const ok = applyInjection(physics, fireIds, { injectP: pPer, injectRho: rPer, injectPsi: psiPer });
      totalInjectedP += ok * pPer;
      totalInjectedRho += ok * rPer;
      totalInjectedPsi += ok * psiPer;

      if (dreamStepPerTick > 0) {
        if (typeof physics.step !== "function") throw new Error("physics.step is not a function; cannot dreamStepPerTick.");
        for (let k = 0; k < dreamStepPerTick; k++) physics.step(stepDt, stepPressC, stepDamping);
      }

      if (tick % progressEveryDreamTicks === 0) {
        console.log(`🧠 [DreamSweepV3] dream t=${(tick * dreamEveryMs / 1000).toFixed(2)}s fired=[${fireIds.join(",")}] pPer=${pPer.toFixed(2)} rPer=${rPer.toFixed(2)}`);
      }

      await sleep(dreamEveryMs);
    }

    const s0 = sampleState(physics, psiTopK);

    // REST WATCH phase
    const rows = [];
    const t0 = performance.now();
    let prev = null;
    let frozenCount = 0;

    const totalSamples = Math.max(1, Math.round((restSeconds * 1000) / restEveryMs));

    for (let i = 0; i < totalSamples; i++) {
      if (restMode === "step") {
        if (typeof physics.step !== "function") throw new Error("physics.step is not a function; cannot restMode:'step'.");
        for (let k = 0; k < restStepsPerSample; k++) physics.step(stepDt, stepPressC, stepDamping);
      }

      const tSec = (performance.now() - t0) / 1000;
      const s = sampleState(physics, psiTopK);

      const row = {
        label, runIndex, stamp,
        pattern,
        injectorIds: injectorIds.join("|"),
        dreamInjectMode,

        injectP, injectRho, injectPsi,
        dreamBudgetPPerTick, dreamBudgetRhoPerTick, dreamBudgetPsiPerTick,
        totalInjectedP, totalInjectedRho, totalInjectedPsi,

        dreamSeconds, dreamEveryMs, dreamStepPerTick,
        restMode, restSeconds, restEveryMs,
        stepDt, stepDamping, stepPressC, restStepsPerSample,

        tSec: Number(tSec.toFixed(3)),

        entropy: s.ent,

        rhoSum: s.rs.rhoSum,
        rhoConc: s.rs.rhoConc,
        rhoMaxId: s.rs.rhoMaxId,

        meanP: s.ps.meanP,
        varP: s.ps.varP,
        pMax: s.ps.pMax,
        pMaxId: s.ps.pMaxId,

        psiAbsSum: s.qs.psiAbsSum,
        psiAbsMean: s.qs.psiAbsMean,
        psiAbsMax: s.qs.psiAbsMax,
        psiMaxId: s.qs.psiMaxId,
        psiTopFrac: s.qs.psiTopFrac,
        psiTopIds: s.qs.psiTopIds,

        sumAbsFlux: s.fs.sumAbsFlux,
        maxAbsFlux: s.fs.maxAbsFlux
      };

      rows.push(row);

      if (autoStepIfFrozen && restMode === "live" && prev) {
        const dFlux = Math.abs(row.maxAbsFlux - prev.maxAbsFlux);
        const dRho = Math.abs(row.rhoSum - prev.rhoSum);
        const dP = Math.abs(row.meanP - prev.meanP);
        const dEnt = Math.abs(row.entropy - prev.entropy);

        const frozen = (dFlux < frozenTolerance) && (dRho < frozenTolerance) && (dP < frozenTolerance) && (dEnt < frozenTolerance);
        frozenCount = frozen ? (frozenCount + 1) : 0;

        if (frozenCount >= frozenSamplesToTrigger) {
          if (typeof physics.step !== "function") {
            console.warn("🧊 [DreamSweepV3] frozen detected, but physics.step unavailable. Recommend restMode:'step'.");
          } else {
            console.warn(`🧊 [DreamSweepV3] frozen detected (${frozenCount} samples). Stepping physics (restStepsPerSample=${restStepsPerSample}).`);
            for (let k = 0; k < restStepsPerSample; k++) physics.step(stepDt, stepPressC, stepDamping);
          }
          frozenCount = 0;
        }
      }

      prev = row;

      if (i % progressEverySamples === 0) {
        console.log(`[Rest ${label}] t=${row.tSec}s ent=${row.entropy.toFixed(4)} rhoSum=${row.rhoSum.toExponential(2)} rhoMaxId=${row.rhoMaxId} maxAbsFlux=${row.maxAbsFlux.toExponential(2)} meanP=${row.meanP.toFixed(4)}`);
      }

      await sleep(restEveryMs);
    }

    if (!rows.length) throw new Error("No rows recorded. If the live loop is paused, use restMode:'step'.");

    // summary features
    const entPeak = argmax(rows, "entropy");
    const fluxPeak = argmax(rows, "maxAbsFlux");
    const meanPPeak = argmax(rows, "meanP");

    const summary = {
      label, runIndex, stamp,
      pattern,
      injectorIds: injectorIds.join("|"),
      dreamInjectMode,

      injectP, injectRho, injectPsi,
      dreamBudgetPPerTick, dreamBudgetRhoPerTick, dreamBudgetPsiPerTick,
      totalInjectedP, totalInjectedRho, totalInjectedPsi,

      dreamSeconds, dreamEveryMs, dreamStepPerTick,
      restMode, restSeconds, restEveryMs,
      stepDt, stepDamping, stepPressC, restStepsPerSample,

      entropy_t0: s0.ent,
      rhoSum_t0: s0.rs.rhoSum,
      rhoConc_t0: s0.rs.rhoConc,
      rhoMaxId_t0: s0.rs.rhoMaxId,
      meanP_t0: s0.ps.meanP,
      pMax_t0: s0.ps.pMax,
      pMaxId_t0: s0.ps.pMaxId,
      maxAbsFlux_t0: s0.fs.maxAbsFlux,

      entropy_peak: entPeak.v,
      entropy_peak_tSec: entPeak.i >= 0 ? rows[entPeak.i].tSec : NaN,

      maxAbsFlux_peak: fluxPeak.v,
      maxAbsFlux_peak_tSec: fluxPeak.i >= 0 ? rows[fluxPeak.i].tSec : NaN,

      meanP_peak: meanPPeak.v,
      meanP_peak_tSec: meanPPeak.i >= 0 ? rows[meanPPeak.i].tSec : NaN,

      entropy_end: rows[rows.length - 1].entropy,
      rhoSum_end: rows[rows.length - 1].rhoSum,
      rhoConc_end: rows[rows.length - 1].rhoConc,
      rhoMaxId_end: rows[rows.length - 1].rhoMaxId,
      meanP_end: rows[rows.length - 1].meanP,
      pMax_end: rows[rows.length - 1].pMax,
      pMaxId_end: rows[rows.length - 1].pMaxId,
      maxAbsFlux_end: rows[rows.length - 1].maxAbsFlux,

      rhoMaxId_mode: mode(rows.map(r => String(r.rhoMaxId))),
      pMaxId_mode: mode(rows.map(r => String(r.pMaxId))),
      psiMaxId_mode: mode(rows.map(r => String(r.psiMaxId))),

      rhoMaxId_switches: countIdSwitches(rows, "rhoMaxId"),
      rhoMaxId_firstSwitch_tSec: firstSwitchTime(rows, "rhoMaxId"),

      pMaxId_switches: countIdSwitches(rows, "pMaxId"),
      pMaxId_firstSwitch_tSec: firstSwitchTime(rows, "pMaxId"),

      rhoSum_t50: firstTimeBelow(rows, "rhoSum", 0.5),
      rhoSum_t10: firstTimeBelow(rows, "rhoSum", 0.1),
      maxAbsFlux_t50: firstTimeBelow(rows, "maxAbsFlux", 0.5),
      maxAbsFlux_t10: firstTimeBelow(rows, "maxAbsFlux", 0.1),

      rhoMaxId_unique: uniqCount(rows.map(r => String(r.rhoMaxId))),
      pMaxId_unique: uniqCount(rows.map(r => String(r.pMaxId)))
    };

    const result = { summary, rows };

    // cache last run for manual export
    globalThis.__SOL_DREAMSWEEP_LAST__ = {
      cfg: { ...cfg },
      result
    };

    console.log(`✅ [DreamSweepV3] DONE ${label} idx=${runIndex} ent_peak=${summary.entropy_peak.toFixed(4)} rhoMaxId_mode=${summary.rhoMaxId_mode} switches=${summary.rhoMaxId_switches}`);

    // Optional auto-download for single run
    try {
      maybeDownloadRun(result, { download, filenamePrefix, label });
      if (String(download).toLowerCase() !== "none") {
        console.log(`⬇️ [DreamSweepV3] download requested (${download}). If no file appeared, check browser download/popup settings, or run: solDreamSweepV3.downloadLast("${download}")`);
      }
    } catch (e) {
      console.warn("⚠️ [DreamSweepV3] download failed (likely blocked). You can still export with: solDreamSweepV3.downloadLast('both')", e);
    }

    return result;
  }

  // ---------------- Sweep helpers ----------------
  function expandGrid(grid) {
    const {
      patterns = ["roundRobin"],
      injectorSets = [{ name: "A", ids: [64,82,79,90] }],
      dreamInjectModes = ["budgetPerTick"],

      injectPValues = [5],
      injectRhoValues = [25],
      injectPsiValues = [0],

      budgetPValues = [10],
      budgetRhoValues = [120],
      budgetPsiValues = [0]
    } = grid;

    const defs = [];
    for (const pat of patterns) {
      for (const set of injectorSets) {
        for (const mode of dreamInjectModes) {
          if (mode === "perNode") {
            for (const p of injectPValues) for (const r of injectRhoValues) for (const psi of injectPsiValues) {
              defs.push({ pattern: pat, injectorSetName: set.name, injectorIds: set.ids, dreamInjectMode: mode, injectP: p, injectRho: r, injectPsi: psi });
            }
          } else {
            for (const bp of budgetPValues) for (const br of budgetRhoValues) for (const bpsi of budgetPsiValues) {
              defs.push({ pattern: pat, injectorSetName: set.name, injectorIds: set.ids, dreamInjectMode: mode, dreamBudgetPPerTick: bp, dreamBudgetRhoPerTick: br, dreamBudgetPsiPerTick: bpsi });
            }
          }
        }
      }
    }
    return defs;
  }

  async function sweep(gridCfg) {
    const {
      label = "dreamSweep",
      maxRuns = 24,

      base = {
        restoreBaseline: true,

        dreamSeconds: 4,
        dreamEveryMs: 100,
        strobeTicks: 10,
        dreamInjectMode: "budgetPerTick",

        injectP: 5,
        injectRho: 25,
        injectPsi: 0,

        dreamBudgetPPerTick: 10,
        dreamBudgetRhoPerTick: 120,
        dreamBudgetPsiPerTick: 0,

        dreamStepPerTick: 0,

        restSeconds: 120,
        restEveryMs: 200,
        restMode: "live",
        autoStepIfFrozen: false,

        stepDt: 0.12,
        stepDamping: 4,
        stepPressC: 20,
        restStepsPerSample: 5,

        psiTopK: 5,
        progressEverySamples: 25,
        progressEveryDreamTicks: 10
      },

      patterns = ["roundRobin", "strobe", "burstAll"],
      injectorSets = [
        { name: "A_64_82_79_90", ids: [64,82,79,90] },
        { name: "B_64_82", ids: [64,82] },
        { name: "C_64_only", ids: [64] },
        { name: "D_82_only", ids: [82] },
        { name: "E_90_only", ids: [90] },
        { name: "F_64_90_no82", ids: [64,90] }
      ],

      dreamInjectModes = ["budgetPerTick"],

      budgetPValues = [0, 10],
      budgetRhoValues = [60, 120, 240],
      budgetPsiValues = [0],

      injectPValues = [0, 10],
      injectRhoValues = [25, 75, 150],
      injectPsiValues = [0],

      filenamePrefix = "sol_dreamSweepV3"
    } = gridCfg || {};

    const stamp = isoFileStamp();
    const summaryFile = `${filenamePrefix}_summary_${stamp}.csv`;
    const traceFile = `${filenamePrefix}_trace_${stamp}.csv`;

    const grid = expandGrid({
      patterns, injectorSets, dreamInjectModes,
      injectPValues, injectRhoValues, injectPsiValues,
      budgetPValues, budgetRhoValues, budgetPsiValues
    });

    const runDefs = grid.slice(0, maxRuns);

    console.log(`🧪 [DreamSweepV3] sweep label="${label}" runs=${runDefs.length}/${grid.length} (maxRuns=${maxRuns})`);
    console.log(`[DreamSweepV3] output → ${summaryFile} + ${traceFile}`);

    const allSummaries = [];
    const allRows = [];

    for (let i = 0; i < runDefs.length; i++) {
      const d = runDefs[i];
      const runLabel = `${label}__${i}__${d.injectorSetName}__${d.pattern}__${d.dreamInjectMode}`;

      const cfg = { ...base, ...d, label: runLabel, runIndex: i, download: "none" };

      const { summary, rows } = await runOne(cfg);

      summary.injectorSetName = d.injectorSetName;
      allSummaries.push(summary);

      for (const r of rows) {
        r.injectorSetName = d.injectorSetName;
        allRows.push(r);
      }

      console.log(`📦 [DreamSweepV3] completed ${i + 1}/${runDefs.length}`);
      await sleep(50);
    }

    downloadCSV(summaryFile, allSummaries);
    downloadCSV(traceFile, allRows);

    globalThis.__SOL_DREAMSWEEP_SUMMARY__ = allSummaries;
    globalThis.__SOL_DREAMSWEEP_TRACE__ = allRows;

    console.log(`✅ [DreamSweepV3] sweep done → downloaded ${summaryFile} + ${traceFile}`);
    return { summaries: allSummaries, rows: allRows };
  }

  function downloadLast(download = "both", filenamePrefix = "sol_dreamLast") {
    const last = globalThis.__SOL_DREAMSWEEP_LAST__;
    if (!last?.result) {
      console.warn("No last run cached. Run solDreamSweepV3.runOne(...) first.");
      return;
    }
    const label = last?.cfg?.label ?? "last";
    maybeDownloadRun(last.result, { download, filenamePrefix, label });
    console.log(`⬇️ [DreamSweepV3] downloaded last run (${download}).`);
  }

  async function runOneAndDownload(cfg = {}) {
    return await runOne({ ...cfg, download: cfg.download ?? "both" });
  }

  globalThis.solDreamSweepV3 = {
    runOne,
    runOneAndDownload,
    sweep,
    quickSweep: async () => {
      return await sweep({
        label: "dreamQuickV3",
        maxRuns: 18,
        patterns: ["roundRobin", "strobe", "burstAll"],
        dreamInjectModes: ["budgetPerTick"],
        injectorSets: [
          { name: "A_64_82_79_90", ids: [64,82,79,90] },
          { name: "B_64_82", ids: [64,82] },
          { name: "F_64_90_no82", ids: [64,90] },
          { name: "E_90_only", ids: [90] }
        ],
        budgetPValues: [0, 10],
        budgetRhoValues: [60, 120, 240],
        budgetPsiValues: [0],
        base: {
          restoreBaseline: true,
          dreamSeconds: 4,
          dreamEveryMs: 100,
          restSeconds: 120,
          restEveryMs: 200,
          restMode: "live",
          autoStepIfFrozen: false,
          stepDt: 0.12,
          stepDamping: 4,
          stepPressC: 20,
          restStepsPerSample: 5,
          psiTopK: 5,
          progressEverySamples: 25,
          progressEveryDreamTicks: 10
        },
        filenamePrefix: "sol_dreamQuickV3"
      });
    },
    downloadLast
  };

  console.log("✅ solDreamSweepV3 installed.");
  console.log("Single + download: await solDreamSweepV3.runOne({ label:'sanity', download:'both' })");
  console.log("Or: await solDreamSweepV3.runOneAndDownload({ label:'sanity2' })");
  console.log("Export last anytime: solDreamSweepV3.downloadLast('both')");
})();
