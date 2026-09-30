(() => {
  "use strict";

  // ============================================================
  // LatchIdentityV1
  // - Tests whether latch mapping flips when injector order flips
  // - Runs short/medium/long afterstate watches per order
  // - Downloads ONLY 2 CSVs: summary + trace (all runs inside)
  //
  // Requires:
  // - SOLBaseline (Unified v1.3 is fine)
  // - solLatchControllerV22 preferred (falls back to V21/V2 if needed)
  // - window.solver / physics ready
  // ============================================================

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const safe = (x) => (Number.isFinite(x) ? x : 0);
  const isoTag = () => new Date().toISOString().replace(/[:.]/g, "-");

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

  function pickController() {
    // Prefer V22 (has reset + self-heal), but allow older.
    return (
      globalThis.solLatchControllerV22 ??
      globalThis.solLatchControllerV21 ??
      globalThis.solLatchControllerV2 ??
      null
    );
  }

  function hasBaseline() {
    return !!globalThis.SOLBaseline?.restore;
  }

  function lastInjectedId(injectorIds, blocks) {
    // With strobePick = floor(tick/strobeTicks) % len,
    // last block index = blocks-1, so last injector = injectorIds[(blocks-1)%len]
    const len = injectorIds.length;
    return String(injectorIds[(blocks - 1) % len]);
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
    return {
      entropy: entropyRhoNorm(nodes),
      ...rhoStats(nodes),
      ...pStats(nodes),
      ...fluxStats(edges),
    };
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

    return {
      rhoMaxId_t0: start,
      rhoMaxId_firstSwitch_tSec: firstSwitchT,
      rhoMaxId_switchCount: switchCount,
      rho90_dwell_s,
    };
  }

  function downloadCSV(filename, rows) {
    if (!rows?.length) {
      console.warn(`[LatchIdentityV1] no rows to write: ${filename}`);
      return;
    }

    // Union columns across all rows (stable-ish order)
    const colSet = new Set();
    for (const r of rows) Object.keys(r || {}).forEach((k) => colSet.add(k));
    const cols = Array.from(colSet);

    const esc = (v) => {
      const s = String(v ?? "");
      return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
    };

    const lines = [cols.join(",")];
    for (const r of rows) lines.push(cols.map((c) => esc(r[c])).join(","));

    const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 5000);
  }

  async function waitUntil(targetMs, { timingMode = "tight", spinMs = 8 } = {}) {
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

  async function watchAfterstate({
    runId,
    orderTag,
    injectorIds,
    target,
    durationLabel,
    watchSeconds,
    everyMs,
    timingMode,
    spinMs,
    selectionInfo,
    traceOut,
    progressEverySamples = 25,
  }) {
    const phy = getPhysics();

    const startMs = performance.now();
    const endMs = startMs + watchSeconds * 1000;

    let nextIndex = 0;
    let nextTime = startMs;
    let prevSampleMs = startMs;

    let missedTicksTotal = 0;
    let lateAbsSum = 0;
    let lateCount = 0;

    console.log(
      `[LatchIdentityV1] WATCH ${orderTag} ${target} ${durationLabel} (${watchSeconds}s @ ${everyMs}ms)…`
    );

    while (true) {
      await waitUntil(nextTime, { timingMode, spinMs });

      const nowMs = performance.now();
      if (nowMs >= endMs) break;

      const tSec = Number(((nowMs - startMs) / 1000).toFixed(3));
      const dtMs = traceOut.length === 0 ? 0 : (nowMs - prevSampleMs);
      const lateByMs = nowMs - nextTime;

      lateAbsSum += Math.abs(lateByMs);
      lateCount += 1;

      const s = sample(phy);

      const row = {
        runId,
        phase: "watch",
        orderTag,
        injectorIds: injectorIds.join("|"),
        target,
        durationLabel,
        watchSeconds,
        everyMs,
        timingMode,
        spinMs,

        tick: traceOut.length,
        tSec,
        dtMs: Number(dtMs.toFixed(3)),
        lateByMs: Number(lateByMs.toFixed(3)),
        missedTicksTotal,

        visibilityState: document.visibilityState,
        hasFocus: document.hasFocus(),

        usedParity: selectionInfo?.usedParity ?? "",
        observedStartId_t0: selectionInfo?.observedStartId_t0 ?? "",
        observedStartId_post: selectionInfo?.observedStartId_post ?? "",

        entropy: s.entropy,
        rhoSum: s.rhoSum,
        rhoConc: s.rhoConc,
        rhoMaxId: s.rhoMaxId,
        meanP: s.meanP,
        pMax: s.pMax,
        pMaxId: s.pMaxId,
        maxAbsFlux: s.maxAbsFlux,
        sumAbsFlux: s.sumAbsFlux,
      };

      traceOut.push(row);
      prevSampleMs = nowMs;

      if (traceOut.length % progressEverySamples === 0) {
        console.log(
          `[LatchIdentityV1] t=${tSec}s n=${traceOut.length} lateBy=${row.lateByMs}ms missed=${missedTicksTotal} rhoMaxId=${row.rhoMaxId}`
        );
      }

      // Drop-late schedule: skip missed slots so wall-clock stays correct.
      nextIndex += 1;
      nextTime = startMs + nextIndex * everyMs;

      if (nowMs >= nextTime) {
        const newIndex = Math.floor((nowMs - startMs) / everyMs) + 1;
        missedTicksTotal += Math.max(0, newIndex - nextIndex);
        nextIndex = newIndex;
        nextTime = startMs + nextIndex * everyMs;
      }

      if (nextTime >= endMs) break;
    }

    // Slice out the rows for just this segment (last N rows)
    // Caller knows where segment started; we’ll compute summary from those rows outside.
    const avgAbsLateByMs = lateCount ? lateAbsSum / lateCount : 0;
    return { avgAbsLateByMs };
  }

  async function run(opts = {}) {
    if (!hasBaseline()) throw new Error("SOLBaseline.restore() not found. Install SOLBaseline Unified first.");
    const controller = pickController();
    if (!controller?.calibrate || !controller?.selectMode) {
      throw new Error("No latch controller found. Need solLatchControllerV22 (preferred) or V21/V2.");
    }

    const runId = `latchIdentityV1_${isoTag()}`;
    const baselineMeta = globalThis.__SOL_BASELINE_META ?? {};

    // --- Configuration (edit here if you want) ---
    const cfg = {
      orders: [
        { orderTag: "A_82-90", injectorIds: [82, 90] },
        { orderTag: "B_90-82", injectorIds: [90, 82] },
      ],

      // Reason for medium: common switch boundary ~80–115s
      includeMedium: true,

      durations: {
        short: 30,
        medium: 90,
        long: 120,
      },

      // Which durations per target
      // start82 often "boring-stable" once latched; medium is most informative for start90.
      durationPlanByTarget: {
        start90: ["short", "medium", "long"],
        start82: ["short", "long"],
      },

      everyMs: 200,
      timingMode: "tight",
      spinMs: 8,

      // Latch/dream settings (match your current primitive)
      latch: {
        strobeTicks: 10,
        dreamEveryMs: 100,
        blocksParity0: 5,
        blocksParity1: 6,
        injectRho: 400,
        injectP: 0,
        injectPsi: 0,
        stepPerTick: 1,
        postSteps: 0,
      },
    };

    // Allow override
    const user = opts || {};
    if (typeof user.includeMedium === "boolean") cfg.includeMedium = user.includeMedium;
    if (user.everyMs) cfg.everyMs = user.everyMs;
    if (user.spinMs) cfg.spinMs = user.spinMs;
    if (user.timingMode) cfg.timingMode = user.timingMode;

    const summaryRows = [];
    const traceRows = [];

    console.log(`[LatchIdentityV1] RUN ${runId}`);
    console.log(`[LatchIdentityV1] baselineMeta`, baselineMeta);

    for (const ord of cfg.orders) {
      const { orderTag, injectorIds } = ord;

      // 1) Calibrate mapping for this injector order
      if (typeof controller.reset === "function") controller.reset();

      const cal = await controller.calibrate({
        injectorIds,
        strobeTicks: cfg.latch.strobeTicks,
        dreamEveryMs: cfg.latch.dreamEveryMs,
        blocksParity0: cfg.latch.blocksParity0,
        blocksParity1: cfg.latch.blocksParity1,
        injectRho: cfg.latch.injectRho,
        injectP: cfg.latch.injectP,
        injectPsi: cfg.latch.injectPsi,
        stepPerTick: cfg.latch.stepPerTick,
        postSteps: cfg.latch.postSteps,
        restoreBaseline: true,
      });

      const p0 = String(cal?.[0] ?? "");
      const p1 = String(cal?.[1] ?? "");
      const last0 = lastInjectedId(injectorIds, cfg.latch.blocksParity0);
      const last1 = lastInjectedId(injectorIds, cfg.latch.blocksParity1);

      summaryRows.push({
        runId,
        phase: "calibrate",
        orderTag,
        injectorIds: injectorIds.join("|"),
        baseline_createdAt: baselineMeta.createdAt ?? "",
        baseline_v: baselineMeta.v ?? "",
        baseline_nodeCount: baselineMeta.nodeCount ?? "",
        baseline_edgeCount: baselineMeta.edgeCount ?? "",

        strobeTicks: cfg.latch.strobeTicks,
        dreamEveryMs: cfg.latch.dreamEveryMs,
        blocksParity0: cfg.latch.blocksParity0,
        blocksParity1: cfg.latch.blocksParity1,

        parity0_startId_t0: p0,
        parity1_startId_t0: p1,
        parity0_lastInjectedId: last0,
        parity1_lastInjectedId: last1,

        parityTracksLastInjector_p0: p0 === last0,
        parityTracksLastInjector_p1: p1 === last1,
      });

      console.log(`[LatchIdentityV1] CAL ${orderTag} parity map: 0→${p0}, 1→${p1} (lastInjected p0=${last0}, p1=${last1})`);

      // 2) For each target+duration, latch select then watch
      for (const target of ["start90", "start82"]) {
        const plan = cfg.durationPlanByTarget[target] || ["short", "long"];

        for (const label of plan) {
          if (label === "medium" && !cfg.includeMedium) continue;

          const watchSeconds = cfg.durations[label];
          if (!watchSeconds) continue;

          // Latch select (restores baseline + runs dream)
          const sel = await controller.selectMode({
            target,
            injectorIds,
            strobeTicks: cfg.latch.strobeTicks,
            dreamEveryMs: cfg.latch.dreamEveryMs,
            blocksParity0: cfg.latch.blocksParity0,
            blocksParity1: cfg.latch.blocksParity1,
            injectRho: cfg.latch.injectRho,
            injectP: cfg.latch.injectP,
            injectPsi: cfg.latch.injectPsi,
            stepPerTick: cfg.latch.stepPerTick,
            postSteps: cfg.latch.postSteps,
            restoreBaseline: true,
          });

          if (!sel) {
            summaryRows.push({
              runId,
              phase: "watch",
              orderTag,
              injectorIds: injectorIds.join("|"),
              target,
              durationLabel: label,
              watchSeconds,
              status: "selectMode_failed",
            });
            console.warn(`[LatchIdentityV1] selectMode failed for ${orderTag} ${target} ${label}. Skipping watch.`);
            continue;
          }

          const segStartIdx = traceRows.length;

          const timing = await watchAfterstate({
            runId,
            orderTag,
            injectorIds,
            target,
            durationLabel: label,
            watchSeconds,
            everyMs: cfg.everyMs,
            timingMode: cfg.timingMode,
            spinMs: cfg.spinMs,
            selectionInfo: sel,
            traceOut: traceRows,
          });

          const segRows = traceRows.slice(segStartIdx);
          const switches = computeSwitchMetrics(segRows);

          const entropyPeak = segRows.length ? Math.max(...segRows.map((r) => r.entropy)) : 0;
          const maxFluxPeak = segRows.length ? Math.max(...segRows.map((r) => r.maxAbsFlux)) : 0;
          const meanPPeak = segRows.length ? Math.max(...segRows.map((r) => r.meanP)) : 0;
          const rhoMaxMode = mode(segRows.map((r) => String(r.rhoMaxId)));
          const tEnd = segRows.length ? segRows[segRows.length - 1].tSec : 0;
          const missedEnd = segRows.length ? segRows[segRows.length - 1].missedTicksTotal : 0;

          summaryRows.push({
            runId,
            phase: "watch",
            orderTag,
            injectorIds: injectorIds.join("|"),
            target,
            durationLabel: label,
            watchSeconds,
            everyMs: cfg.everyMs,
            timingMode: cfg.timingMode,
            spinMs: cfg.spinMs,

            usedParity: sel.usedParity ?? "",
            observedStartId_t0: sel.observedStartId_t0 ?? "",
            observedStartId_post: sel.observedStartId_post ?? "",

            samples: segRows.length,
            wallSecondsObserved: tEnd,
            missedTicksTotal: missedEnd,
            avgAbsLateByMs: Number(safe(timing.avgAbsLateByMs).toFixed(3)),

            rhoMaxId_mode: rhoMaxMode,
            entropy_peak: entropyPeak,
            maxAbsFlux_peak: maxFluxPeak,
            meanP_peak: meanPPeak,

            ...switches,
          });
        }
      }
    }

    // 3) Download two CSVs total
    const stamp = isoTag();
    const summaryFile = `sol_latchIdentityV1_summary_${stamp}.csv`;
    const traceFile = `sol_latchIdentityV1_trace_${stamp}.csv`;

    downloadCSV(summaryFile, summaryRows);
    downloadCSV(traceFile, traceRows);

    console.log(`[LatchIdentityV1] downloaded: ${summaryFile} + ${traceFile}`);
    globalThis.__SOL_LATCHIDENTITYV1_SUMMARY__ = summaryRows;
    globalThis.__SOL_LATCHIDENTITYV1_TRACE__ = traceRows;

    return { runId, summaryRows, traceRows };
  }

  globalThis.solLatchIdentityV1 = { run };

  console.log("solLatchIdentityV1 installed.");
  console.log("Run: await solLatchIdentityV1.run();");
  console.log("Options: await solLatchIdentityV1.run({ includeMedium:false, everyMs:200, timingMode:'tight', spinMs:8 });");
})();
