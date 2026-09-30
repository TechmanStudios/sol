(async () => {
  "use strict";

  // ============================================================
  // SOL — Phase 3.10 Regression Pack v1
  //
  // Goal:
  //   Re-run a minimal, high-signal subset of Phase 3.10 under
  //   Firefox Dev Edition (or any stable browser) with consistent
  //   timing semantics + guaranteed CSV outputs.
  //
  // What it runs:
  //   0) Timing sanity (Latch watch): start90 + start82 (30s each)
  //   1) EndPhase latch determinism: parity blocks A/B (10 reps each)
  //   2) Cadence regime A/B/C mini-replication (3 reps each)
  //   3) ψ trim check: ψΔ ∈ {-1,0,+1} inside each latched mode (60s)
  //
  // Output:
  //   Exactly 2 downloads:
  //     - sol_phase310_regPack_v1_summary_<stamp>.csv
  //     - sol_phase310_regPack_v1_trace_<stamp>.csv
  //
  // Requirements:
  //   - SOLBaseline Unified installed (globalThis.SOLBaseline.restore exists)
  //   - Dashboard physics ready (window.solver or SOLDashboard/App physics)
  //
  // UI-neutral:
  //   No camera moves, no view changes.
  // ============================================================

  // ---------------------------
  // Small utilities
  // ---------------------------
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const safe = (x) => (Number.isFinite(x) ? x : 0);
  const stampTag = () => new Date().toISOString().replace(/[:.]/g, "-");
  const nowISO = () => new Date().toISOString();

  function assert(cond, msg) {
    if (!cond) throw new Error(msg);
  }

  function getPhysicsMaybe() {
    return (
      globalThis.solver ||
      window.solver ||
      globalThis.SOLDashboard?.state?.physics?.network ||
      globalThis.SOLDashboard?.state?.physics ||
      globalThis.App?.state?.physics?.network ||
      globalThis.App?.state?.physics ||
      globalThis.app?.state?.physics?.network ||
      globalThis.app?.state?.physics ||
      null
    );
  }

  function getPhysics() {
    const phy = getPhysicsMaybe();
    if (phy?.nodes && phy?.edges && typeof phy.step === "function") return phy;
    if (phy?.nodes && phy?.edges) return phy;
    throw new Error("Physics not ready (no nodes/edges found). Let the dashboard finish initializing.");
  }

  async function waitForPhysics({ timeoutMs = 20000, pollMs = 50 } = {}) {
    const t0 = performance.now();
    while (performance.now() - t0 < timeoutMs) {
      const phy = getPhysicsMaybe();
      if (phy?.nodes && phy?.edges) return phy;
      await sleep(pollMs);
    }
    throw new Error("Timed out waiting for physics. Refresh and try again after dashboard fully loads.");
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

  function stepOnce(phy, dt = 0.12, pressC = 20, damping = 4) {
    if (typeof phy.step !== "function") return false;
    try { phy.step(dt, pressC, damping); return true; } catch (_) {}
    try { phy.step(dt); return true; } catch (_) {}
    try { phy.step(); return true; } catch (_) {}
    return false;
  }

  function strobePick(injectorIds, tick, strobeTicks) {
    const idx = Math.floor(tick / strobeTicks) % injectorIds.length;
    return injectorIds[idx];
  }

  function rhoMaxId(phy) {
    let best = -Infinity, bestId = "";
    for (const n of phy.nodes || []) {
      const r = safe(n?.rho);
      if (r > best) { best = r; bestId = String(n?.id ?? ""); }
    }
    return bestId;
  }

  function inject(phy, id, { injectP = 0, injectRho = 0, injectPsi = 0 } = {}) {
    const n = nodeByIdLoose(phy, id);
    if (!n) return false;
    if (injectP && typeof n.p === "number") n.p += injectP;
    if (injectRho && typeof n.rho === "number") n.rho += injectRho;
    if (injectPsi && typeof n.psi === "number") n.psi += injectPsi;
    return true;
  }

  function applyPsiBiasDelta(phy, delta) {
    let c = 0;
    for (const n of phy.nodes || []) {
      if (!n) continue;
      if (typeof n.psi_bias === "number") n.psi_bias += delta;
      else n.psi_bias = delta;
      c++;
    }
    return c;
  }

  // ---------------------------
  // Stats sampling for traces
  // ---------------------------
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
    let rhoSum = 0, rhoMax = -Infinity, rhoMaxId_ = "";
    for (const n of nodes) {
      const r = safe(n?.rho);
      rhoSum += r;
      if (r > rhoMax) { rhoMax = r; rhoMaxId_ = String(n?.id ?? ""); }
    }
    const rhoConc = rhoSum > 0 ? rhoMax / rhoSum : 0;
    return { rhoSum, rhoMax, rhoMaxId: rhoMaxId_, rhoConc };
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

  // ---------------------------
  // CSV writer (union columns)
  // ---------------------------
  function downloadCSV(filename, rows) {
    const out = (rows && rows.length) ? rows : [{ status: "no_rows" }];
    const colSet = new Set();
    for (const r of out) Object.keys(r || {}).forEach((k) => colSet.add(k));
    const cols = Array.from(colSet);

    const esc = (v) => {
      const s = String(v ?? "");
      return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
    };

    const lines = [cols.join(",")];
    for (const r of out) lines.push(cols.map((c) => esc(r[c])).join(","));

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

  // ---------------------------
  // Timing: drift-compensated metronome + optional spin
  // ---------------------------
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

  // "Wall-clock watch": runs until t >= watchSeconds, and drops late ticks
  async function watchWallClock({
    runId,
    phase,
    segment,
    target,
    watchSeconds,
    everyMs,
    timingMode,
    spinMs,
    meta = {},
    traceRows,
    progressEverySamples = 50,
  }) {
    const phy = getPhysics();

    const startMs = performance.now();
    const endMs = startMs + watchSeconds * 1000;

    let tick = 0;
    let nextTickMs = startMs;
    let prevSampleMs = startMs;

    let missedTicksTotal = 0;
    let lateAbsSum = 0;
    let lateCount = 0;

    console.log(
      `[RegPack] WATCH ${segment} (${watchSeconds}s @ ${everyMs}ms) timingMode=${timingMode} spinMs=${spinMs} focus=${document.hasFocus()} vis=${document.visibilityState}`
    );

    while (true) {
      await waitUntil(nextTickMs, { timingMode, spinMs });

      const nowMs = performance.now();
      if (nowMs >= endMs) break;

      const tSec = Number(((nowMs - startMs) / 1000).toFixed(3));
      const dtMs = tick === 0 ? 0 : (nowMs - prevSampleMs);
      const lateByMs = nowMs - nextTickMs;

      lateAbsSum += Math.abs(lateByMs);
      lateCount++;

      const s = sample(phy);

      traceRows.push({
        runId,
        phase,
        segment,
        target,

        tick,
        tSec,
        dtMs: Number(dtMs.toFixed(3)),
        lateByMs: Number(lateByMs.toFixed(3)),
        missedTicksTotal,

        visibilityState: document.visibilityState,
        hasFocus: document.hasFocus(),

        ...meta,

        entropy: s.entropy,
        rhoSum: s.rhoSum,
        rhoConc: s.rhoConc,
        rhoMaxId: s.rhoMaxId,
        meanP: s.meanP,
        pMax: s.pMax,
        pMaxId: s.pMaxId,
        maxAbsFlux: s.maxAbsFlux,
        sumAbsFlux: s.sumAbsFlux,
      });

      // Progress
      if (tick % progressEverySamples === 0) {
        console.log(
          `[RegPack] t=${tSec}s tick=${tick} lateBy=${Number(lateByMs.toFixed(1))}ms missed=${missedTicksTotal} rhoMaxId=${s.rhoMaxId}`
        );
      }

      // Schedule next tick (drop-late)
      tick++;
      prevSampleMs = nowMs;
      nextTickMs = startMs + tick * everyMs;

      // If we're already past the next scheduled time, drop ticks to catch up.
      if (nowMs > nextTickMs) {
        const idealTick = Math.floor((nowMs - startMs) / everyMs) + 1;
        const dropped = Math.max(0, idealTick - tick);
        missedTicksTotal += dropped;
        tick = idealTick;
        nextTickMs = startMs + tick * everyMs;
      }
    }

    const avgAbsLateByMs = lateCount ? (lateAbsSum / lateCount) : 0;
    return { avgAbsLateByMs };
  }

  // ---------------------------
  // Dream runner (fixed ticks OR fixed seconds)
  // ---------------------------
  async function runDreamFixedTicks({
    injectorIds,
    blocks,
    strobeTicks,
    dreamEveryMs,
    injectRho,
    injectP = 0,
    injectPsi = 0,
    stepPerTick = 1,
    stepDt = 0.12,
    pressC = 20,
    damping = 4,
    timingMode = "tight",
    spinMs = 8,
    restoreBaseline = true,
    psiBiasDelta = 0,
  }) {
    const phy = getPhysics();

    if (restoreBaseline) {
      await globalThis.SOLBaseline.restore();
    }

    if (psiBiasDelta !== 0) {
      applyPsiBiasDelta(phy, psiBiasDelta);
    }

    const totalTicks = blocks * strobeTicks;
    const startMs = performance.now();

    let tick = 0;
    let nextMs = startMs;
    let missedTicksTotal = 0;
    let lateAbsSum = 0;
    let lateCount = 0;

    for (tick = 0; tick < totalTicks; tick++) {
      await waitUntil(nextMs, { timingMode, spinMs });

      const nowMs = performance.now();
      const lateByMs = nowMs - nextMs;
      lateAbsSum += Math.abs(lateByMs);
      lateCount++;

      const id = strobePick(injectorIds, tick, strobeTicks);
      inject(phy, id, { injectP, injectRho, injectPsi });

      for (let k = 0; k < stepPerTick; k++) stepOnce(phy, stepDt, pressC, damping);

      nextMs = startMs + (tick + 1) * dreamEveryMs;

      if (nowMs > nextMs) {
        const idealTick = Math.floor((nowMs - startMs) / dreamEveryMs) + 1;
        const dropped = Math.max(0, idealTick - (tick + 1));
        missedTicksTotal += dropped;
        nextMs = startMs + (tick + 1 + dropped) * dreamEveryMs;
      }
    }

    const startId_t0 = rhoMaxId(phy);

    const lastBlockIdx = Math.max(0, blocks - 1);
    const lastInjectedId = String(injectorIds[lastBlockIdx % injectorIds.length]);
    const lastBlockParity = lastBlockIdx % 2;

    const avgAbsLateByMs = lateCount ? lateAbsSum / lateCount : 0;

    return {
      blocks,
      totalTicks,
      dreamEveryMs,
      injectRho,
      missedTicksTotal,
      avgAbsLateByMs: Number(avgAbsLateByMs.toFixed(3)),
      lastInjectedId,
      lastBlockParity,
      startId_t0: String(startId_t0),
    };
  }

  async function runDreamFixedSeconds({
    injectorIds,
    strobeTicks,
    dreamEveryMs,
    dreamSeconds,
    injectRho,
    injectP = 0,
    injectPsi = 0,
    stepPerTick = 1,
    stepDt = 0.12,
    pressC = 20,
    damping = 4,
    timingMode = "tight",
    spinMs = 8,
    restoreBaseline = true,
    psiBiasDelta = 0,
  }) {
    const phy = getPhysics();

    if (restoreBaseline) {
      await globalThis.SOLBaseline.restore();
    }

    if (psiBiasDelta !== 0) {
      applyPsiBiasDelta(phy, psiBiasDelta);
    }

    const startMs = performance.now();
    const endMs = startMs + dreamSeconds * 1000;

    let tick = 0;
    let nextMs = startMs;
    let missedTicksTotal = 0;
    let lateAbsSum = 0;
    let lateCount = 0;

    while (true) {
      await waitUntil(nextMs, { timingMode, spinMs });

      const nowMs = performance.now();
      if (nowMs >= endMs) break;

      const lateByMs = nowMs - nextMs;
      lateAbsSum += Math.abs(lateByMs);
      lateCount++;

      const id = strobePick(injectorIds, tick, strobeTicks);
      inject(phy, id, { injectP, injectRho, injectPsi });

      for (let k = 0; k < stepPerTick; k++) stepOnce(phy, stepDt, pressC, damping);

      tick++;
      nextMs = startMs + tick * dreamEveryMs;

      // Drop-late for cadence accuracy
      if (nowMs > nextMs) {
        const idealTick = Math.floor((nowMs - startMs) / dreamEveryMs) + 1;
        const dropped = Math.max(0, idealTick - tick);
        missedTicksTotal += dropped;
        tick = idealTick;
        nextMs = startMs + tick * dreamEveryMs;
      }
    }

    const startId_t0 = rhoMaxId(phy);
    const avgAbsLateByMs = lateCount ? lateAbsSum / lateCount : 0;

    return {
      dreamSeconds,
      dreamEveryMs,
      ticks: tick,
      injectRho,
      missedTicksTotal,
      avgAbsLateByMs: Number(avgAbsLateByMs.toFixed(3)),
      startId_t0: String(startId_t0),
    };
  }

  // ---------------------------
  // Robust latch mapping (block scan)
  // ---------------------------
  async function calibrateLatchBlocks({
    injectorIds,
    strobeTicks,
    dreamEveryMs,
    injectRho,
    stepPerTick,
    timingMode,
    spinMs,
    baseBlocks = [5, 6],
    scanBlocks = [4, 5, 6, 7, 8, 9],
  }) {
    const blockToStart = {};

    // Try base first
    for (const b of baseBlocks) {
      const r = await runDreamFixedTicks({
        injectorIds,
        blocks: b,
        strobeTicks,
        dreamEveryMs,
        injectRho,
        stepPerTick,
        timingMode,
        spinMs,
        restoreBaseline: true,
      });
      blockToStart[b] = r.startId_t0;
    }

    const have82 = Object.values(blockToStart).some((x) => String(x) === "82");
    const have90 = Object.values(blockToStart).some((x) => String(x) === "90");

    // If clipped, expand scan
    if (!(have82 && have90)) {
      for (const b of scanBlocks) {
        if (blockToStart[b] != null) continue;
        const r = await runDreamFixedTicks({
          injectorIds,
          blocks: b,
          strobeTicks,
          dreamEveryMs,
          injectRho,
          stepPerTick,
          timingMode,
          spinMs,
          restoreBaseline: true,
        });
        blockToStart[b] = r.startId_t0;

        const h82 = Object.values(blockToStart).some((x) => String(x) === "82");
        const h90 = Object.values(blockToStart).some((x) => String(x) === "90");
        if (h82 && h90) break;
      }
    }

    // Best blocks = smallest block count that yields that startId
    const best = {};
    for (const [bStr, startId] of Object.entries(blockToStart)) {
      const b = Number(bStr);
      const id = String(startId);
      if (!best[id] || b < best[id]) best[id] = b;
    }

    return { blockToStart, best };
  }

  // ---------------------------
  // Main pack runner
  // ---------------------------
  const solPhase310RegressionPackV1 = {
    version: "1.0.0",
    async run(userOpts = {}) {
      await waitForPhysics();

      assert(globalThis.SOLBaseline?.restore, "SOLBaseline.restore() not found. Install SOLBaseline Unified first.");

      // ---- Default config ----
      const cfg = {
        // General
        everyMs: 200,
        timingMode: "tight", // "tight" | "relaxed"
        spinMs: 8,           // Firefox likes 6–10ms; Chrome often needs 1–2ms (but still throttles)

        // Latch/dream core
        injectorIds: [82, 90],
        strobeTicks: 10,
        latchDreamEveryMs: 100,
        latchInjectRho: 400,
        stepPerTick: 1,

        // Watch durations
        timingSanityWatchSeconds: 30,

        // EndPhase determinism
        parityBlocksA: 5,
        parityBlocksB: 6,
        parityReps: 10,

        // Cadence regime A/B/C
        cadenceReps: 3,
        cadenceDreamSeconds: 20,
        cadenceWatchSeconds: 120, // catches the ~95–110s firstSwitch band
        cadenceA: { dreamEveryMs: 40, injectRho: 400 },
        cadenceB: { dreamEveryMs: 80, injectRho: 400 },
        cadenceC: { dreamEveryMs: 80, injectRho: 800 }, // iso-dose: doubled rho at half tick rate

        // ψ trim check
        psiDeltas: [-1, 0, +1],
        psiWatchSeconds: 60,

        // Output
        filenamePrefix: "sol_phase310_regPack_v1",
        progressEverySamples: 50,
      };

      // Override
      Object.assign(cfg, userOpts || {});

      const runId = `phase310_regPack_v1_${stampTag()}`;
      const env = {
        runId,
        startedAt: nowISO(),
        userAgent: navigator.userAgent,
        platform: navigator.platform,
        language: navigator.language,
        hardwareConcurrency: navigator.hardwareConcurrency ?? "",
        deviceMemoryGB: navigator.deviceMemory ?? "",
        timezoneOffsetMin: new Date().getTimezoneOffset(),
        visibilityState: document.visibilityState,
        hasFocus: document.hasFocus(),
        baselineMeta_createdAt: globalThis.__SOL_BASELINE_META?.createdAt ?? "",
        baselineMeta_v: globalThis.__SOL_BASELINE_META?.v ?? "",
        baselineMeta_nodeCount: globalThis.__SOL_BASELINE_META?.nodeCount ?? "",
        baselineMeta_edgeCount: globalThis.__SOL_BASELINE_META?.edgeCount ?? "",
      };

      const summaryRows = [];
      const traceRows = [];

      console.log(`[RegPack] RUN ${runId}`);
      console.log("[RegPack] env:", env);
      console.log("[RegPack] cfg:", cfg);

      // -----------------------
      // 0) Timing sanity (LatchWatch)
      // -----------------------
      summaryRows.push({
        ...env,
        phase: "0_timingSanity",
        segment: "meta",
        note: "LatchWatch sanity: start90 + start82 (30s each)",
      });

      // Calibrate best blocks for start90/start82 under current baseline
      const latchMap = await calibrateLatchBlocks({
        injectorIds: cfg.injectorIds,
        strobeTicks: cfg.strobeTicks,
        dreamEveryMs: cfg.latchDreamEveryMs,
        injectRho: cfg.latchInjectRho,
        stepPerTick: cfg.stepPerTick,
        timingMode: cfg.timingMode,
        spinMs: cfg.spinMs,
      });

      summaryRows.push({
        ...env,
        phase: "0_timingSanity",
        segment: "latchCalibrateBlocks",
        injectorIds: cfg.injectorIds.join("|"),
        strobeTicks: cfg.strobeTicks,
        dreamEveryMs: cfg.latchDreamEveryMs,
        injectRho: cfg.latchInjectRho,
        blockToStart_json: JSON.stringify(latchMap.blockToStart),
        best_json: JSON.stringify(latchMap.best),
        have82: latchMap.best["82"] != null,
        have90: latchMap.best["90"] != null,
      });

      async function latchSelectThenWatch({ target, watchSeconds, segment, psiBiasDelta = 0 }) {
        const want = target === "start82" ? "82" : "90";
        const blocks = latchMap.best[want];

        if (!blocks) {
          summaryRows.push({
            ...env,
            phase: "latchWatch",
            segment,
            target,
            status: "selectMode_failed",
            reason: `want ${want} not in best blocks mapping`,
            best_json: JSON.stringify(latchMap.best),
          });
          return;
        }

        // Restore baseline; apply psiBiasDelta if requested; run dream fixed ticks to land t0
        const dream = await runDreamFixedTicks({
          injectorIds: cfg.injectorIds,
          blocks,
          strobeTicks: cfg.strobeTicks,
          dreamEveryMs: cfg.latchDreamEveryMs,
          injectRho: cfg.latchInjectRho,
          stepPerTick: cfg.stepPerTick,
          timingMode: cfg.timingMode,
          spinMs: cfg.spinMs,
          restoreBaseline: true,
          psiBiasDelta,
        });

        const observedStart = dream.startId_t0;
        const ok = String(observedStart) === want;

        // Record dream result
        summaryRows.push({
          ...env,
          phase: "latchSelect",
          segment,
          target,
          want,
          usedBlocks: blocks,
          psiBiasDelta,
          dreamEveryMs: cfg.latchDreamEveryMs,
          injectRho: cfg.latchInjectRho,
          strobeTicks: cfg.strobeTicks,
          stepPerTick: cfg.stepPerTick,
          dream_startId_t0: dream.startId_t0,
          dream_lastInjectedId: dream.lastInjectedId,
          dream_lastBlockParity: dream.lastBlockParity,
          dream_avgAbsLateByMs: dream.avgAbsLateByMs,
          dream_missedTicksTotal: dream.missedTicksTotal,
          status: ok ? "ok" : "mismatch",
        });

        // Watch (no restore here)
        const meta = {
          injectorIds: cfg.injectorIds.join("|"),
          strobeTicks: cfg.strobeTicks,
          latchDreamEveryMs: cfg.latchDreamEveryMs,
          latchInjectRho: cfg.latchInjectRho,
          usedBlocks: blocks,
          want,
          observedStartId_t0: dream.startId_t0,
          lastInjectedId: dream.lastInjectedId,
          lastBlockParity: dream.lastBlockParity,
          psiBiasDelta,
          timingMode: cfg.timingMode,
          spinMs: cfg.spinMs,
          everyMs: cfg.everyMs,
        };

        const timing = await watchWallClock({
          runId,
          phase: "latchWatch",
          segment,
          target,
          watchSeconds,
          everyMs: cfg.everyMs,
          timingMode: cfg.timingMode,
          spinMs: cfg.spinMs,
          meta,
          traceRows,
          progressEverySamples: cfg.progressEverySamples,
        });

        // Segment summary
        const segRows = traceRows.filter((r) => r.segment === segment);
        const switches = computeSwitchMetrics(segRows);
        const entropyPeak = segRows.length ? Math.max(...segRows.map((r) => r.entropy)) : 0;
        const maxFluxPeak = segRows.length ? Math.max(...segRows.map((r) => r.maxAbsFlux)) : 0;
        const meanPPeak = segRows.length ? Math.max(...segRows.map((r) => r.meanP)) : 0;

        summaryRows.push({
          ...env,
          phase: "latchWatch_summary",
          segment,
          target,
          watchSeconds,
          everyMs: cfg.everyMs,
          timingMode: cfg.timingMode,
          spinMs: cfg.spinMs,
          avgAbsLateByMs: Number(timing.avgAbsLateByMs.toFixed(3)),
          samples: segRows.length,
          rhoMaxId_mode: mode(segRows.map((r) => String(r.rhoMaxId))),
          entropy_peak: entropyPeak,
          maxAbsFlux_peak: maxFluxPeak,
          meanP_peak: meanPPeak,
          ...switches,
        });
      }

      // Run timing sanity watches
      await latchSelectThenWatch({
        target: "start90",
        watchSeconds: cfg.timingSanityWatchSeconds,
        segment: "0_timingSanity_start90",
      });

      await latchSelectThenWatch({
        target: "start82",
        watchSeconds: cfg.timingSanityWatchSeconds,
        segment: "0_timingSanity_start82",
      });

      // -----------------------
      // 1) EndPhase latch determinism (parity blocks A/B reps)
      // -----------------------
      summaryRows.push({
        ...env,
        phase: "1_endPhaseDeterminism",
        segment: "meta",
        note: "Run blocksParityA/B once to define mapping, then repeat each N times and measure accuracy.",
        parityBlocksA: cfg.parityBlocksA,
        parityBlocksB: cfg.parityBlocksB,
        reps: cfg.parityReps,
      });

      // Define mapping from single-shot A/B
      const mapA = await runDreamFixedTicks({
        injectorIds: cfg.injectorIds,
        blocks: cfg.parityBlocksA,
        strobeTicks: cfg.strobeTicks,
        dreamEveryMs: cfg.latchDreamEveryMs,
        injectRho: cfg.latchInjectRho,
        stepPerTick: cfg.stepPerTick,
        timingMode: cfg.timingMode,
        spinMs: cfg.spinMs,
        restoreBaseline: true,
      });

      const mapB = await runDreamFixedTicks({
        injectorIds: cfg.injectorIds,
        blocks: cfg.parityBlocksB,
        strobeTicks: cfg.strobeTicks,
        dreamEveryMs: cfg.latchDreamEveryMs,
        injectRho: cfg.latchInjectRho,
        stepPerTick: cfg.stepPerTick,
        timingMode: cfg.timingMode,
        spinMs: cfg.spinMs,
        restoreBaseline: true,
      });

      const parityMap = {
        [cfg.parityBlocksA]: mapA.startId_t0,
        [cfg.parityBlocksB]: mapB.startId_t0,
      };

      summaryRows.push({
        ...env,
        phase: "1_endPhaseDeterminism",
        segment: "parityMap",
        parityMap_json: JSON.stringify(parityMap),
        blocksA_lastInjectedId: mapA.lastInjectedId,
        blocksA_lastParity: mapA.lastBlockParity,
        blocksB_lastInjectedId: mapB.lastInjectedId,
        blocksB_lastParity: mapB.lastBlockParity,
      });

      // Repeat trials; write per-trial to traceRows (phase=determinismTrial)
      async function determinismTrials(blocks, reps) {
        const want = String(parityMap[blocks] ?? "");
        let okCount = 0;

        for (let i = 0; i < reps; i++) {
          const r = await runDreamFixedTicks({
            injectorIds: cfg.injectorIds,
            blocks,
            strobeTicks: cfg.strobeTicks,
            dreamEveryMs: cfg.latchDreamEveryMs,
            injectRho: cfg.latchInjectRho,
            stepPerTick: cfg.stepPerTick,
            timingMode: cfg.timingMode,
            spinMs: cfg.spinMs,
            restoreBaseline: true,
          });

          const got = String(r.startId_t0);
          const ok = want ? (got === want) : false;
          if (ok) okCount++;

          traceRows.push({
            ...env,
            phase: "1_endPhaseDeterminism_trial",
            segment: `determinism_blocks_${blocks}`,
            trial: i,
            blocks,
            want,
            got,
            ok,
            lastInjectedId: r.lastInjectedId,
            lastBlockParity: r.lastBlockParity,
            dreamEveryMs: cfg.latchDreamEveryMs,
            injectRho: cfg.latchInjectRho,
            strobeTicks: cfg.strobeTicks,
            dream_avgAbsLateByMs: r.avgAbsLateByMs,
            dream_missedTicksTotal: r.missedTicksTotal,
          });

          if ((i + 1) % 5 === 0) {
            console.log(`[RegPack] determinism blocks=${blocks} ${i + 1}/${reps} ok=${okCount}`);
          }
        }

        return { blocks, reps, want, okCount, acc: reps ? okCount / reps : 0 };
      }

      const detA = await determinismTrials(cfg.parityBlocksA, cfg.parityReps);
      const detB = await determinismTrials(cfg.parityBlocksB, cfg.parityReps);

      summaryRows.push({
        ...env,
        phase: "1_endPhaseDeterminism",
        segment: "results",
        blocksA: detA.blocks,
        blocksA_want: detA.want,
        blocksA_ok: detA.okCount,
        blocksA_reps: detA.reps,
        blocksA_acc: Number(detA.acc.toFixed(3)),
        blocksB: detB.blocks,
        blocksB_want: detB.want,
        blocksB_ok: detB.okCount,
        blocksB_reps: detB.reps,
        blocksB_acc: Number(detB.acc.toFixed(3)),
      });

      // -----------------------
      // 2) Cadence A/B/C mini-replication (3 reps each)
      // -----------------------
      summaryRows.push({
        ...env,
        phase: "2_cadenceABC",
        segment: "meta",
        note: "Fixed dream seconds; cadence varies tick spacing; iso-dose doubles rho at slower cadence.",
        reps: cfg.cadenceReps,
        dreamSeconds: cfg.cadenceDreamSeconds,
        watchSeconds: cfg.cadenceWatchSeconds,
      });

      const cadenceConds = [
        { key: "A_40ms", dreamEveryMs: cfg.cadenceA.dreamEveryMs, injectRho: cfg.cadenceA.injectRho },
        { key: "B_80ms", dreamEveryMs: cfg.cadenceB.dreamEveryMs, injectRho: cfg.cadenceB.injectRho },
        { key: "C_80ms_isoDose", dreamEveryMs: cfg.cadenceC.dreamEveryMs, injectRho: cfg.cadenceC.injectRho },
      ];

      for (const cond of cadenceConds) {
        for (let rep = 0; rep < cfg.cadenceReps; rep++) {
          const segment = `2_cadence_${cond.key}_rep${rep + 1}`;

          const dream = await runDreamFixedSeconds({
            injectorIds: cfg.injectorIds,
            strobeTicks: cfg.strobeTicks,
            dreamEveryMs: cond.dreamEveryMs,
            dreamSeconds: cfg.cadenceDreamSeconds,
            injectRho: cond.injectRho,
            stepPerTick: cfg.stepPerTick,
            timingMode: cfg.timingMode,
            spinMs: cfg.spinMs,
            restoreBaseline: true,
          });

          summaryRows.push({
            ...env,
            phase: "2_cadenceABC_dream",
            segment,
            cond: cond.key,
            rep: rep + 1,
            dreamSeconds: cfg.cadenceDreamSeconds,
            dreamEveryMs: cond.dreamEveryMs,
            injectRho: cond.injectRho,
            ticks: dream.ticks,
            dream_startId_t0: dream.startId_t0,
            dream_avgAbsLateByMs: dream.avgAbsLateByMs,
            dream_missedTicksTotal: dream.missedTicksTotal,
          });

          const meta = {
            cond: cond.key,
            rep: rep + 1,
            injectorIds: cfg.injectorIds.join("|"),
            strobeTicks: cfg.strobeTicks,
            dreamSeconds: cfg.cadenceDreamSeconds,
            dreamEveryMs: cond.dreamEveryMs,
            injectRho: cond.injectRho,
            dream_startId_t0: dream.startId_t0,
            timingMode: cfg.timingMode,
            spinMs: cfg.spinMs,
            everyMs: cfg.everyMs,
          };

          const timing = await watchWallClock({
            runId,
            phase: "2_cadenceABC_watch",
            segment,
            target: "afterstate",
            watchSeconds: cfg.cadenceWatchSeconds,
            everyMs: cfg.everyMs,
            timingMode: cfg.timingMode,
            spinMs: cfg.spinMs,
            meta,
            traceRows,
            progressEverySamples: cfg.progressEverySamples,
          });

          const segRows = traceRows.filter((r) => r.segment === segment && r.phase === "2_cadenceABC_watch");
          const switches = computeSwitchMetrics(segRows);
          const entropyPeak = segRows.length ? Math.max(...segRows.map((r) => r.entropy)) : 0;
          const maxFluxPeak = segRows.length ? Math.max(...segRows.map((r) => r.maxAbsFlux)) : 0;
          const meanPPeak = segRows.length ? Math.max(...segRows.map((r) => r.meanP)) : 0;

          summaryRows.push({
            ...env,
            phase: "2_cadenceABC_summary",
            segment,
            cond: cond.key,
            rep: rep + 1,
            watchSeconds: cfg.cadenceWatchSeconds,
            everyMs: cfg.everyMs,
            timingMode: cfg.timingMode,
            spinMs: cfg.spinMs,
            avgAbsLateByMs: Number(timing.avgAbsLateByMs.toFixed(3)),
            samples: segRows.length,
            rhoMaxId_mode: mode(segRows.map((r) => String(r.rhoMaxId))),
            entropy_peak: entropyPeak,
            maxAbsFlux_peak: maxFluxPeak,
            meanP_peak: meanPPeak,
            ...switches,
          });
        }
      }

      // -----------------------
      // 3) ψ trim check (ψΔ inside each latched mode)
      // -----------------------
      summaryRows.push({
        ...env,
        phase: "3_psiTrim",
        segment: "meta",
        note: "Apply psi_bias delta BEFORE latch dream, then watch afterstate. Uses best blocks mapping from latch calibration.",
        psiDeltas_json: JSON.stringify(cfg.psiDeltas),
        psiWatchSeconds: cfg.psiWatchSeconds,
      });

      for (const target of ["start90", "start82"]) {
        for (const psiDelta of cfg.psiDeltas) {
          const segment = `3_psiTrim_${target}_psiDelta_${psiDelta}`;
          await latchSelectThenWatch({
            target,
            watchSeconds: cfg.psiWatchSeconds,
            segment,
            psiBiasDelta: psiDelta,
          });
        }
      }

      // -----------------------
      // Download outputs (2 files)
      // -----------------------
      const stamp = stampTag();
      const summaryFile = `${cfg.filenamePrefix}_summary_${stamp}.csv`;
      const traceFile = `${cfg.filenamePrefix}_trace_${stamp}.csv`;

      downloadCSV(summaryFile, summaryRows);
      downloadCSV(traceFile, traceRows);

      console.log(`[RegPack] downloaded: ${summaryFile} + ${traceFile}`);
      globalThis.__SOL_PHASE310_REGPACK_V1_SUMMARY__ = summaryRows;
      globalThis.__SOL_PHASE310_REGPACK_V1_TRACE__ = traceRows;

      return { runId, summaryRows, traceRows };
    },
  };

  globalThis.solPhase310RegressionPackV1 = solPhase310RegressionPackV1;

  console.log(`✅ solPhase310RegressionPackV1 installed (v${solPhase310RegressionPackV1.version}).`);
  console.log("Run later with:");
  console.log("  await solPhase310RegressionPackV1.run()");
  console.log("Optional overrides example:");
  console.log("  await solPhase310RegressionPackV1.run({ spinMs: 8, timingMode: 'tight', cadenceReps: 2 })");

})().catch((err) => console.error("❌ Phase 3.10 Regression Pack v1 error:", err));
