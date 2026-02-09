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
    try { phy.step(dt, pressC, damping); return true; } catch (_) {}
    try { phy.step(dt); return true; } catch (_) {}
    try { phy.step(); return true; } catch (_) {}
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
    let pSum = 0, pMax = -Infinity, pMaxId = "", count = 0;
    for (const n of nodes) {
      const p = safe(n?.p);
      pSum += p; count++;
      if (p > pMax) { pMax = p; pMaxId = String(n?.id ?? ""); }
    }
    const meanP = count ? pSum / count : 0;
    return { meanP, pMax, pMaxId };
  }

  function fluxStats(edges) {
    let maxAbsFlux = 0, sumAbsFlux = 0;
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
    let best = null, bestC = -1;
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

    let rho90_dwell_s = 0;
    for (const r of rows) if (String(r.rhoMaxId) === "90") rho90_dwell_s += (safe(r.dtMs) / 1000);

    return { rhoMaxId_t0: start, rhoMaxId_firstSwitch_tSec: firstSwitchT, rhoMaxId_switchCount: switchCount, rho90_dwell_s };
  }

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

  async function waitUntil(targetMs, { timingMode = "relaxed", spinMs = 1.5 } = {}) {
    while (true) {
      const now = performance.now();
      const remaining = targetMs - now;
      if (remaining <= 0) return;

      if (timingMode === "tight") {
        const sleepMs = Math.max(0, remaining - spinMs);
        if (sleepMs > 0) await sleep(sleepMs);
        while (performance.now() < targetMs) {}
        return;
      } else {
        await sleep(remaining);
        return;
      }
    }
  }

  function pickController() {
    return globalThis.solLatchControllerV21 ?? globalThis.solLatchControllerV2 ?? null;
  }

  async function run(opts = {}) {
    const {
      label = "LatchWatchV3",
      target = "start90",

      latchStepPerTick = 1,
      latchPostSteps = 0,
      latchRestoreBaseline = true,

      watchSeconds = 120,
      everyMs = 200,

      timingMode = "tight",
      spinMs = 1.5,

      // drop-late policy:
      // if we're behind, we SKIP missed ticks and schedule the next one in the future.
      dropLate = true,

      autoStepIfFrozen = false,  // recommend OFF for timing validation
      frozenTol = 1e-14,
      frozenSamplesToTrigger = 10,
      restStepsPerTrigger = 10,
      stepDt = 0.12,
      pressC = 20,
      damping = 4,

      progressEverySamples = 25,
      filenamePrefix = "sol_latchWatch",
      download = true,
    } = opts;

    const controller = pickController();
    if (!controller?.selectMode) {
      throw new Error(`Latch controller missing. Have V21=${!!globalThis.solLatchControllerV21}, V2=${!!globalThis.solLatchControllerV2}`);
    }
    if (!globalThis.SOLBaseline?.restore) throw new Error("SOLBaseline.restore() not found.");

    const stamp = new Date().toISOString().replace(/[:.]/g, "-");

    const sel = await controller.selectMode({
      target,
      restoreBaseline: latchRestoreBaseline,
      stepPerTick: latchStepPerTick,
      postSteps: latchPostSteps,
    });
    if (!sel) throw new Error(`[LatchWatchV3] selectMode(${target}) returned null. Aborting.`);

    const phy = getPhysics();
    const rows = [];

    const startMs = performance.now();
    let targetMs = startMs;       // first sample at t=0
    let prevSampleMs = startMs;

    let prevRow = null;
    let frozenCount = 0;
    let missedTicksTotal = 0;

    const plannedTicks = Math.max(1, Math.round((watchSeconds * 1000) / everyMs));
    console.log(`[LatchWatchV3] watching ${watchSeconds}s plannedTicks=${plannedTicks} everyMs=${everyMs} dropLate=${dropLate}`);

    for (let tick = 0; tick < plannedTicks; tick++) {
      await waitUntil(targetMs, { timingMode, spinMs });

      const nowMs = performance.now();
      const tSec = Number(((nowMs - startMs) / 1000).toFixed(3));
      const dtMsRaw = tick === 0 ? 0 : (nowMs - prevSampleMs);
      const lateByMsRaw = nowMs - targetMs;

      const s = sample(phy);

      const row = {
        label,
        stamp,
        target,
        usedParity: sel.usedParity ?? "",
        observedStartId: sel.observedStartId ?? sel.observedStartId_t0 ?? "",

        tick,
        tSec,
        dtMs: Number(dtMsRaw.toFixed(3)),
        lateByMs: Number(lateByMsRaw.toFixed(3)),
        missedTicksTotal,

        visibilityState: document.visibilityState,
        hasFocus: document.hasFocus(),

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

      if (autoStepIfFrozen && prevRow) {
        const dR = Math.abs(row.rhoSum - prevRow.rhoSum);
        const dP = Math.abs(row.meanP - prevRow.meanP);
        const dF = Math.abs(row.maxAbsFlux - prevRow.maxAbsFlux);
        const frozen = dR < frozenTol && dP < frozenTol && dF < frozenTol;
        frozenCount = frozen ? frozenCount + 1 : 0;

        if (frozenCount >= frozenSamplesToTrigger) {
          console.warn(`[LatchWatchV3] frozen. Forcing ${restStepsPerTrigger} steps…`);
          for (let k = 0; k < restStepsPerTrigger; k++) stepOnce(phy, stepDt, pressC, damping);
          frozenCount = 0;
        }
      }

      prevRow = row;
      prevSampleMs = nowMs;

      if (tick % progressEverySamples === 0) {
        console.log(`[LatchWatchV3] t=${tSec}s tick=${tick} lateBy=${row.lateByMs}ms missedTicksTotal=${missedTicksTotal} focus=${row.hasFocus} vis=${row.visibilityState} rhoMaxId=${row.rhoMaxId}`);
      }

      // schedule next tick
      const idealNext = targetMs + everyMs;

      if (dropLate) {
        // if we're already past the next deadline, skip ahead
        if (nowMs >= idealNext) {
          const missed = Math.floor((nowMs - idealNext) / everyMs) + 1;
          missedTicksTotal += missed;
          targetMs = idealNext + missed * everyMs; // guaranteed in the future
        } else {
          targetMs = idealNext;
        }
      } else {
        // old catch-up behavior (not recommended for "fixed interval" semantics)
        targetMs = idealNext;
      }
    }

    const switches = computeSwitchMetrics(rows);
    const entropyPeak = Math.max(...rows.map((r) => r.entropy));
    const maxFlux = Math.max(...rows.map((r) => r.maxAbsFlux));
    const maxMeanP = Math.max(...rows.map((r) => r.meanP));
    const lateAbsAvg = rows.length > 1 ? rows.slice(1).reduce((s, r) => s + Math.abs(r.lateByMs), 0) / (rows.length - 1) : 0;

    const summary = [{
      label,
      stamp,
      target,
      usedParity: sel.usedParity ?? "",
      observedStartId: sel.observedStartId ?? sel.observedStartId_t0 ?? "",
      timingMode,
      everyMs,
      plannedTicks,
      actualTicks: rows.length,
      watchSeconds,
      dropLate,
      missedTicksTotal,
      avgAbsLateByMs: Number(lateAbsAvg.toFixed(3)),
      rhoMaxId_mode: mode(rows.map((r) => String(r.rhoMaxId))),
      entropy_peak: entropyPeak,
      maxAbsFlux_peak: maxFlux,
      meanP_peak: maxMeanP,
      rhoSum_end: rows[rows.length - 1].rhoSum,
      maxAbsFlux_end: rows[rows.length - 1].maxAbsFlux,
      ...switches,
    }];

    if (download) {
      downloadCSV(`${filenamePrefix}_summary_${target}_${stamp}.csv`, summary);
      downloadCSV(`${filenamePrefix}_trace_${target}_${stamp}.csv`, rows);
    }

    console.log("[LatchWatchV3] done.");
    return { sel, summary, rows };
  }

  globalThis.solLatchWatchV3 = { run };
  console.log("solLatchWatchV3 installed. Run: await solLatchWatchV3.run({ target:'start90', watchSeconds:120 })");
})();
