(() => {
  "use strict";

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const safe = (x) => (Number.isFinite(x) ? x : 0);

  function getRoot() {
    return globalThis.SOLDashboard ?? globalThis.App ?? globalThis.app ?? null;
  }

  function getPhysics() {
    const solver = globalThis.solver;
    if (solver?.nodes && solver?.edges) return solver;

    const root = getRoot();
    const physics = root?.state?.physics;
    if (!physics?.nodes) throw new Error("Physics not ready. Make sure the dashboard is running.");
    return physics;
  }

  function nodeById(physics, id) {
    const m = physics?.nodeById?.get?.(id);
    if (m) return m;
    return (physics.nodes || []).find((n) => n?.id === id) || null;
  }

  // --- telemetry ---
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
    return Hmax > 0 ? H / Hmax : 0;
  }

  function rhoStats(nodes) {
    let rhoSum = 0,
      rhoMax = -Infinity,
      rhoMaxId = "";
    for (const n of nodes) {
      const r = safe(n?.rho);
      rhoSum += r;
      if (r > rhoMax) {
        rhoMax = r;
        rhoMaxId = String(n?.id ?? "");
      }
    }
    const rhoConc = rhoSum > 0 ? rhoMax / rhoSum : 0;
    return { rhoSum, rhoMax, rhoMaxId, rhoConc };
  }

  function pStats(nodes) {
    let pSum = 0,
      pMax = -Infinity,
      pMaxId = "";
    const ps = [];
    for (const n of nodes) {
      const p = safe(n?.p);
      ps.push(p);
      pSum += p;
      if (p > pMax) {
        pMax = p;
        pMaxId = String(n?.id ?? "");
      }
    }
    const meanP = ps.length ? pSum / ps.length : 0;
    let varP = 0;
    for (const p of ps) varP += (p - meanP) * (p - meanP);
    varP = ps.length ? varP / ps.length : 0;
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
      if (v > maxAbs) {
        maxAbs = v;
        psiMaxId = String(n?.id ?? "");
      }
    }
    arr.sort((a, b) => b[0] - a[0]);
    const topSum = arr.slice(0, topK).reduce((s, [v]) => s + v, 0);
    const topFrac = sumAbs > 0 ? topSum / sumAbs : 0;
    const psiTopIds = arr.slice(0, topK).map((x) => x[1]).join("|");
    const meanAbs = arr.length ? sumAbs / arr.length : 0;
    return {
      psiAbsSum: sumAbs,
      psiAbsMean: meanAbs,
      psiAbsMax: maxAbs,
      psiMaxId,
      psiTopFrac: topFrac,
      psiTopIds,
    };
  }

  function fluxStats(edges) {
    let sumAbs = 0,
      maxAbs = 0;
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

  // --- CSV download ---
  function downloadCSV(filename, rows) {
    if (!rows?.length) return;
    const cols = Object.keys(rows[0]);
    const esc = (v) => {
      const s = String(v ?? "");
      return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
    };
    const lines = [cols.join(",")].concat(rows.map((r) => cols.map((c) => esc(r[c])).join(",")));
    const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 5000);
  }

  // --- dream patterns ---
  const Patterns = {
    roundRobin: (injectorIds, tick) => [injectorIds[tick % injectorIds.length]],
    burstAll: (injectorIds, tick) => injectorIds.slice(),
    strobe: (injectorIds, tick, strobeTicks = 10) => {
      const idx = Math.floor(tick / strobeTicks) % injectorIds.length;
      return [injectorIds[idx]];
    },
    pairSwap: (injectorIds, tick) => {
      if (injectorIds.length < 2) return injectorIds.slice();
      const mid = Math.floor(injectorIds.length / 2);
      const a = injectorIds.slice(0, mid);
      const b = injectorIds.slice(mid);
      return tick % 2 === 0 ? a : b;
    },
  };

  function applyInjection(physics, ids, { injectP = 0, injectRho = 0, injectPsi = 0 }) {
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
    let best = null,
      bestC = -1;
    for (const [k, c] of m.entries()) if (c > bestC) (best = k), (bestC = c);
    return best ?? "";
  }

  function uniqCount(arr) {
    return new Set(arr).size;
  }

  function computeSwitchMetrics(rows) {
    if (!rows.length) return {};
    const ids = rows.map((r) => String(r.rhoMaxId));
    const t = rows.map((r) => r.tSec);

    const start = ids[0];
    let firstSwitchT = null;
    let switchCount = 0;
    for (let i = 1; i < ids.length; i++) {
      if (ids[i] !== ids[i - 1]) {
        switchCount++;
        if (firstSwitchT == null && ids[i] !== start) firstSwitchT = t[i];
      }
    }

    // 90 window metrics (approximate using sample cadence)
    let rho90_enter_tSec = null;
    let rho90_exit_tSec = null;
    let rho90_segments = 0;
    let rho90_dwell_s = 0;

    const dt = rows.length > 1 ? Math.max(1e-6, rows[1].tSec - rows[0].tSec) : 0;

    let in90 = false;
    for (let i = 0; i < ids.length; i++) {
      const is90 = ids[i] === "90";
      if (is90 && !in90) {
        in90 = true;
        rho90_segments++;
        if (rho90_enter_tSec == null) rho90_enter_tSec = t[i];
      }
      if (!is90 && in90) {
        in90 = false;
        if (rho90_exit_tSec == null) rho90_exit_tSec = t[i];
      }
      if (is90) rho90_dwell_s += dt;
    }

    return {
      rhoMaxId_t0: start,
      rhoMaxId_firstSwitch_tSec: firstSwitchT,
      rhoMaxId_switchCount: switchCount,
      rho90_enter_tSec,
      rho90_exit_tSec,
      rho90_dwell_s,
      rho90_segments,
    };
  }

  async function runOne(cfg) {
    const {
      label = "run",
      runIndex = 0,

      restoreBaseline = true,

      dreamSeconds = 4,
      dreamEveryMs = 100,
      pattern = "roundRobin",
      strobeTicks = 10,
      injectorIds = [64, 82, 79, 90],
      injectP = 5,
      injectRho = 25,
      injectPsi = 0,
      dreamStepPerTick = 0,

      restSeconds = 120,
      restEveryMs = 200,
      restMode = "live", // "live" or "step"
      autoStepIfFrozen = false,
      frozenTolerance = 1e-12,
      frozenSamplesToTrigger = 8,

      stepDt = 0.12,
      stepDamping = 4,
      stepPressC = 20,
      restStepsPerSample = 5,

      psiTopK = 5,
      progressEverySamples = 25,
    } = cfg;

    const physics = getPhysics();

    if (restoreBaseline) {
      if (!globalThis.SOLBaseline?.restore) {
        throw new Error("SOLBaseline.restore() not found. Load your baseline script first.");
      }
      await globalThis.SOLBaseline.restore();
    }

    const stamp = new Date().toISOString();
    console.log(
      `[DreamSweep] START ${label} idx=${runIndex} pattern=${pattern} injectP=${injectP} injectRho=${injectRho} injectPsi=${injectPsi} ids=[${injectorIds.join(",")}]`
    );

    // DREAM
    const dreamTicks = Math.max(1, Math.round((dreamSeconds * 1000) / dreamEveryMs));
    const patFn = Patterns[pattern];
    if (!patFn) throw new Error(`Unknown pattern "${pattern}". Use: ${Object.keys(Patterns).join(", ")}`);

    const logEveryTicks = Math.max(1, Math.floor(1000 / dreamEveryMs));

    for (let tick = 0; tick < dreamTicks; tick++) {
      const fireIds =
        pattern === "strobe" ? Patterns.strobe(injectorIds, tick, strobeTicks) : patFn(injectorIds, tick);

      applyInjection(physics, fireIds, { injectP, injectRho, injectPsi });

      if (dreamStepPerTick > 0 && typeof physics.step === "function") {
        for (let k = 0; k < dreamStepPerTick; k++) physics.step(stepDt, stepPressC, stepDamping);
      }

      if (tick % logEveryTicks === 0) {
        console.log(`[DreamSweep] dream t=${(tick * dreamEveryMs / 1000).toFixed(2)}s fired=[${fireIds.join(",")}]`);
      }
      await sleep(dreamEveryMs);
    }

    // REST t=0 snapshot
    const s0 = sampleState(physics, psiTopK);

    // REST WATCH
    const rows = [];
    const t0 = performance.now();
    let prev = null;
    let frozenCount = 0;

    const totalSamples = Math.max(1, Math.round((restSeconds * 1000) / restEveryMs));

    for (let i = 0; i < totalSamples; i++) {
      if (restMode === "step") {
        for (let k = 0; k < restStepsPerSample; k++) physics.step(stepDt, stepPressC, stepDamping);
      }

      const tSec = (performance.now() - t0) / 1000;
      const s = sampleState(physics, psiTopK);

      const row = {
        label,
        runIndex,
        stamp,
        pattern,
        injectorIds: injectorIds.join("|"),
        injectP,
        injectRho,
        injectPsi,
        dreamSeconds,
        dreamEveryMs,
        dreamStepPerTick,
        restMode,
        restSeconds,
        restEveryMs,
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
        maxAbsFlux: s.fs.maxAbsFlux,
      };

      rows.push(row);

      // auto-step if frozen (optional)
      if (autoStepIfFrozen && restMode === "live" && prev && typeof physics.step === "function") {
        const dFlux = Math.abs(row.maxAbsFlux - prev.maxAbsFlux);
        const dRho = Math.abs(row.rhoSum - prev.rhoSum);
        const dP = Math.abs(row.meanP - prev.meanP);

        const frozen = dFlux < frozenTolerance && dRho < frozenTolerance && dP < frozenTolerance;
        frozenCount = frozen ? frozenCount + 1 : 0;

        if (frozenCount >= frozenSamplesToTrigger) {
          console.warn(
            `[DreamSweep] detected frozen evolution (${frozenCount} samples). Stepping physics now (restStepsPerSample=${restStepsPerSample}).`
          );
          for (let k = 0; k < restStepsPerSample; k++) physics.step(stepDt, stepPressC, stepDamping);
          frozenCount = 0;
        }
      }

      prev = row;

      if (i % progressEverySamples === 0) {
        console.log(
          `[Rest ${label}] t=${row.tSec}s ent=${row.entropy.toFixed(4)} rhoSum=${row.rhoSum.toExponential(
            2
          )} rhoMaxId=${row.rhoMaxId} maxAbsFlux=${row.maxAbsFlux.toExponential(2)} meanP=${row.meanP.toFixed(4)}`
        );
      }

      await sleep(restEveryMs);
    }

    const maxMeanP = Math.max(...rows.map((r) => r.meanP));
    const maxPMax = Math.max(...rows.map((r) => r.pMax));
    const maxFlux = Math.max(...rows.map((r) => r.maxAbsFlux));
    const entropyPeak = Math.max(...rows.map((r) => r.entropy));
    const rhoSumEnd = rows[rows.length - 1].rhoSum;

    const switches = computeSwitchMetrics(rows);

    const summary = {
      label,
      runIndex,
      stamp,
      pattern,
      injectorIds: injectorIds.join("|"),
      injectP,
      injectRho,
      injectPsi,
      dreamSeconds,
      dreamEveryMs,
      dreamStepPerTick,
      restMode,
      restSeconds,
      restEveryMs,

      // rest t=0 snapshot
      entropy_t0: s0.ent,
      rhoSum_t0: s0.rs.rhoSum,
      rhoConc_t0: s0.rs.rhoConc,
      rhoMaxId_t0: s0.rs.rhoMaxId,
      meanP_t0: s0.ps.meanP,
      pMax_t0: s0.ps.pMax,
      maxAbsFlux_t0: s0.fs.maxAbsFlux,

      // rest peaks/ends
      entropy_peak: entropyPeak,
      maxMeanP,
      maxPMax,
      maxAbsFlux: maxFlux,
      rhoSum_end: rhoSumEnd,
      entropy_end: rows[rows.length - 1].entropy,
      rhoMaxId_mode: mode(rows.map((r) => String(r.rhoMaxId))),
      pMaxId_unique: uniqCount(rows.map((r) => String(r.pMaxId))),

      // basin signature extras
      ...switches,
    };

    console.log(
      `[DreamSweep] DONE ${label} idx=${runIndex} entropy_peak=${summary.entropy_peak.toFixed(
        4
      )} maxAbsFlux=${summary.maxAbsFlux.toExponential(2)} rhoMaxId_mode=${summary.rhoMaxId_mode}`
    );

    return { summary, rows };
  }

  function expandGrid(grid) {
    const {
      patterns = ["roundRobin"],
      injectorSets = [{ name: "A", ids: [64, 82, 79, 90] }],
      injectPValues = [5],
      injectRhoValues = [25],
      injectPsiValues = [0],
    } = grid;

    const defs = [];
    for (const pat of patterns) {
      for (const set of injectorSets) {
        for (const p of injectPValues) {
          for (const r of injectRhoValues) {
            for (const psi of injectPsiValues) {
              defs.push({
                pattern: pat,
                injectorSetName: set.name,
                injectorIds: set.ids,
                injectP: p,
                injectRho: r,
                injectPsi: psi,
              });
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
      },

      patterns = ["roundRobin", "burstAll", "strobe"],
      injectorSets = [
        { name: "A_64_82_79_90", ids: [64, 82, 79, 90] },
        { name: "B_64_82", ids: [64, 82] },
        { name: "C_64_only", ids: [64] },
        { name: "D_82_only", ids: [82] },
        { name: "E_90_only", ids: [90] },
      ],
      injectPValues = [0, 5, 15],
      injectRhoValues = [10, 25, 50],
      injectPsiValues = [0],

      filenamePrefix = "sol_dreamSweep",
    } = gridCfg || {};

    const stamp = new Date().toISOString().replace(/[:.]/g, "-");
    const summaryFile = `${filenamePrefix}_summary_${stamp}.csv`;
    const traceFile = `${filenamePrefix}_trace_${stamp}.csv`;

    const grid = expandGrid({ patterns, injectorSets, injectPValues, injectRhoValues, injectPsiValues });
    const runDefs = grid.slice(0, maxRuns);

    console.log(`[DreamSweep] sweep label="${label}" runs=${runDefs.length}/${grid.length} (maxRuns=${maxRuns})`);
    console.log(`[DreamSweep] output → ${summaryFile} + ${traceFile}`);

    const allSummaries = [];
    const allRows = [];

    for (let i = 0; i < runDefs.length; i++) {
      const d = runDefs[i];
      const runLabel = `${label}__${i}__${d.injectorSetName}__${d.pattern}__p${d.injectP}__r${d.injectRho}__psi${d.injectPsi}`;

      const cfg = {
        ...base,
        label: runLabel,
        runIndex: i,
        pattern: d.pattern,
        injectorIds: d.injectorIds,
        injectP: d.injectP,
        injectRho: d.injectRho,
        injectPsi: d.injectPsi,
      };

      const { summary, rows } = await runOne(cfg);
      summary.injectorSetName = d.injectorSetName;
      allSummaries.push(summary);

      for (const r of rows) {
        r.injectorSetName = d.injectorSetName;
        allRows.push(r);
      }

      console.log(`[DreamSweep] completed ${i + 1}/${runDefs.length}`);
    }

    downloadCSV(summaryFile, allSummaries);
    downloadCSV(traceFile, allRows);

    console.log(`[DreamSweep] sweep done → downloaded ${summaryFile} + ${traceFile}`);

    globalThis.__SOL_DREAMSWEEP_SUMMARY__ = allSummaries;
    globalThis.__SOL_DREAMSWEEP_TRACE__ = allRows;

    return { summaries: allSummaries, rows: allRows };
  }

  globalThis.solDreamSweepV4 = {
    runOne,
    sweep,
    quickSweep: async () => {
      return await sweep({
        label: "dreamQuick",
        maxRuns: 18,
        patterns: ["roundRobin", "strobe"],
        injectorSets: [
          { name: "A_64_82_79_90", ids: [64, 82, 79, 90] },
          { name: "B_64_82", ids: [64, 82] },
          { name: "E_90_only", ids: [90] },
        ],
        injectPValues: [0, 10],
        injectRhoValues: [25, 75, 150],
        injectPsiValues: [0],
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
        },
        filenamePrefix: "sol_dreamQuick",
      });
    },
  };

  // Back-compat alias (your earlier docs installed solDreamSweepV1)
  globalThis.solDreamSweepV1 = globalThis.solDreamSweepV4;

  console.log("solDreamSweepV4 installed.");
  console.log("Try: await solDreamSweepV4.quickSweep()");
})();
