(() => {
  "use strict";

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const safe = (x) => (Number.isFinite(x) ? x : 0);

  function getPhysics() {
    const solver = globalThis.solver;
    if (solver?.nodes && solver?.edges) return solver;

    const p =
      globalThis.SOLDashboard?.state?.physics ??
      globalThis.App?.state?.physics ??
      globalThis.app?.state?.physics ??
      null;

    if (p?.nodes && p?.edges) return p;
    throw new Error("Physics not ready (no nodes/edges found).");
  }

  function stepOnce(phy, dt = 0.12, pressC = 20, damping = 4) {
    if (typeof phy.step !== "function") return false;
    try {
      phy.step(dt, pressC, damping);
      return true;
    } catch (_) {}
    try {
      phy.step(dt);
      return true;
    } catch (_) {}
    try {
      phy.step();
      return true;
    } catch (_) {}
    return false;
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
    let count = 0;
    for (const n of nodes) {
      const p = safe(n?.p);
      pSum += p;
      count++;
      if (p > pMax) {
        pMax = p;
        pMaxId = String(n?.id ?? "");
      }
    }
    const meanP = count ? pSum / count : 0;
    return { meanP, pMax, pMaxId };
  }

  function fluxStats(edges) {
    let maxAbsFlux = 0,
      sumAbsFlux = 0;
    for (const e of edges || []) {
      const f = Math.abs(safe(e?.flux));
      sumAbsFlux += f;
      if (f > maxAbsFlux) maxAbsFlux = f;
    }
    return { maxAbsFlux, sumAbsFlux };
  }

  function sample(phy) {
    const nodes = phy.nodes || [];
    const edges = phy.edges || [];
    const ent = entropyRhoNorm(nodes);
    const rs = rhoStats(nodes);
    const ps = pStats(nodes);
    const fs = fluxStats(edges);
    return { ent, ...rs, ...ps, ...fs };
  }

  function mode(arr) {
    const m = new Map();
    for (const x of arr) m.set(x, (m.get(x) || 0) + 1);
    let best = null,
      bestC = -1;
    for (const [k, c] of m.entries()) if (c > bestC) (best = k), (bestC = c);
    return best ?? "";
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

    // 90 dwell (approx by sample dt)
    const dt = rows.length > 1 ? Math.max(1e-6, rows[1].tSec - rows[0].tSec) : 0;
    let rho90_dwell_s = 0;
    for (let i = 0; i < ids.length; i++) if (ids[i] === "90") rho90_dwell_s += dt;

    return {
      rhoMaxId_t0: start,
      rhoMaxId_firstSwitch_tSec: firstSwitchT,
      rhoMaxId_switchCount: switchCount,
      rho90_dwell_s,
    };
  }

  function downloadCSV(filename, rows) {
    if (!rows?.length) {
      console.warn(`[LatchWatch] no rows to write: ${filename}`);
      return;
    }
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

  async function run(opts = {}) {
    const {
      label = "LatchWatchV1",
      target = "start90", // "start90" | "start82"

      // latch controller options (pass-through)
      latchStepPerTick = 1,
      latchPostSteps = 20,
      latchRestoreBaseline = true,

      // watch options
      watchSeconds = 120,
      everyMs = 200,

      // frozen handling
      autoStepIfFrozen = true,
      frozenTol = 1e-14,
      frozenSamplesToTrigger = 10,
      restStepsPerTrigger = 10,

      // step params
      stepDt = 0.12,
      pressC = 20,
      damping = 4,

      // logging / output
      progressEverySamples = 25,
      filenamePrefix = "sol_latchWatch",
      download = true,
    } = opts;

    if (!globalThis.solLatchControllerV2?.selectMode) {
      throw new Error("solLatchControllerV2 not found. Paste/install it first.");
    }

    const stamp = new Date().toISOString().replace(/[:.]/g, "-");

    // 1) set mode (this is the "digital control" action)
    const sel = await globalThis.solLatchControllerV2.selectMode({
      target,
      restoreBaseline: latchRestoreBaseline,
      stepPerTick: latchStepPerTick,
      postSteps: latchPostSteps,
    });

    // 2) watch afterstate (NO restore here!)
    const phy = getPhysics();
    const rows = [];
    const t0 = performance.now();

    let prev = null;
    let frozenCount = 0;

    const totalSamples = Math.max(1, Math.round((watchSeconds * 1000) / everyMs));
    console.log(`[LatchWatch] watching ${watchSeconds}s (${totalSamples} samples) after ${target}…`);

    for (let i = 0; i < totalSamples; i++) {
      const tSec = Number(((performance.now() - t0) / 1000).toFixed(3));
      const s = sample(phy);

      const row = {
        label,
        stamp,
        target,
        usedParity: sel?.usedParity ?? "",
        observedStartId: sel?.observedStartId ?? "",
        tSec,
        entropy: s.ent,
        rhoSum: s.rhoSum,
        rhoConc: s.rhoConc,
        rhoMaxId: s.rhoMaxId,
        meanP: s.meanP,
        pMax: s.pMax,
        pMaxId: s.pMaxId,
        maxAbsFlux: s.maxAbsFlux,
        sumAbsFlux: s.sumAbsFlux,
      };

      rows.push(row);

      // Frozen detection + step kick
      if (autoStepIfFrozen && prev) {
        const dR = Math.abs(row.rhoSum - prev.rhoSum);
        const dP = Math.abs(row.meanP - prev.meanP);
        const dF = Math.abs(row.maxAbsFlux - prev.maxAbsFlux);
        const frozen = dR < frozenTol && dP < frozenTol && dF < frozenTol;
        frozenCount = frozen ? frozenCount + 1 : 0;

        if (frozenCount >= frozenSamplesToTrigger) {
          console.warn(`[LatchWatch] frozen (${frozenCount} samples). Forcing ${restStepsPerTrigger} steps…`);
          for (let k = 0; k < restStepsPerTrigger; k++) stepOnce(phy, stepDt, pressC, damping);
          frozenCount = 0;
        }
      }

      prev = row;

      if (i % progressEverySamples === 0) {
        console.log(
          `[LatchWatch] t=${tSec}s rhoMaxId=${row.rhoMaxId} rhoSum=${row.rhoSum.toExponential(2)} flux=${row.maxAbsFlux.toExponential(2)} meanP=${row.meanP.toFixed(6)}`
        );
      }

      await sleep(everyMs);
    }

    const switches = computeSwitchMetrics(rows);
    const summary = [{
      label,
      stamp,
      target,
      usedParity: sel?.usedParity ?? "",
      observedStartId: sel?.observedStartId ?? "",
      samples: rows.length,
      watchSeconds,
      rhoMaxId_mode: mode(rows.map((r) => String(r.rhoMaxId))),
      entropy_peak: Math.max(...rows.map((r) => r.entropy)),
      maxAbsFlux_peak: Math.max(...rows.map((r) => r.maxAbsFlux)),
      meanP_peak: Math.max(...rows.map((r) => r.meanP)),
      rhoSum_end: rows[rows.length - 1].rhoSum,
      ...switches,
    }];

    const traceFile = `${filenamePrefix}_trace_${target}_${stamp}.csv`;
    const summaryFile = `${filenamePrefix}_summary_${target}_${stamp}.csv`;

    if (download) {
      downloadCSV(summaryFile, summary);
      downloadCSV(traceFile, rows);
      console.log(`[LatchWatch] downloaded: ${summaryFile} + ${traceFile}`);
    } else {
      console.log("[LatchWatch] download=false (no CSV written).");
    }

    globalThis.__SOL_LATCHWATCH_SUMMARY__ = summary;
    globalThis.__SOL_LATCHWATCH_TRACE__ = rows;

    return { sel, summary, rows };
  }

  globalThis.solLatchWatchV1 = { run };
  console.log("solLatchWatchV1 installed.");
  console.log("Run: await solLatchWatchV1.run({ target:'start90', watchSeconds:120 })");
})();
