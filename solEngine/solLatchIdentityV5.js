(async () => {
  "use strict";

  // ============================================================
  // LatchIdentityV5
  // - Phase-scan latch controller (blocks->start mapping, not parity assumption)
  // - Runs A (82→90) and B (90→82), start90 & start82, short/medium/long
  // - Outputs ONLY at end: MASTER summary + MASTER trace
  // - UI-neutral (no camera moves)
  // ============================================================

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const safe = (x) => (Number.isFinite(x) ? x : 0);
  const isoTag = () => new Date().toISOString().replace(/[:.]/g, "-");

  function getPhysics() {
    const solver = globalThis.solver || window.solver;
    if (solver?.nodes && solver?.edges) return solver;

    const p =
      globalThis.SOLDashboard?.state?.physics ??
      globalThis.App?.state?.physics ??
      globalThis.app?.state?.physics ??
      null;

    if (p?.nodes && p?.edges) return p;
    throw new Error("Physics not ready (no nodes/edges found).");
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

  function inject(phy, id, { injectP = 0, injectRho = 0, injectPsi = 0 } = {}) {
    const n = nodeByIdLoose(phy, id);
    if (!n) return false;
    if (injectP && typeof n.p === "number") n.p += injectP;
    if (injectRho && typeof n.rho === "number") n.rho += injectRho;
    if (injectPsi && typeof n.psi === "number") n.psi += injectPsi;
    return true;
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

  // ---------- CSV download with UNION header (critical fix) ----------
  function downloadCSVUnion(filename, rows) {
    if (!rows?.length) {
      console.warn(`[LatchIdentityV5] no rows to write: ${filename}`);
      return;
    }
    const colSet = new Set();
    for (const r of rows) for (const k of Object.keys(r || {})) colSet.add(k);
    const cols = Array.from(colSet);

    const esc = (v) => {
      const s = String(v ?? "");
      return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
    };

    const lines = [cols.join(",")].concat(
      rows.map((r) => cols.map((c) => esc(r?.[c])).join(","))
    );

    const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 5000);
  }

  // ---------- Drift-compensated metronome w/ tighter behavior ----------
  async function waitUntil(targetMs, { timingMode = "tight", spinMs = 2.0 } = {}) {
    while (true) {
      const now = performance.now();
      const remaining = targetMs - now;
      if (remaining <= 0) return;

      if (timingMode !== "tight") {
        await sleep(remaining);
        return;
      }

      // Tight mode: iterative sleeps, then spin for last spinMs.
      const guard = spinMs + 2.0; // keep a little safety margin
      if (remaining > guard) {
        await sleep(Math.max(0, remaining - guard));
        continue;
      }

      while (performance.now() < targetMs) {}
      return;
    }
  }

  // ---------- Sampling ----------
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
      pSum += p;
      count++;
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
    for (const r of rows) {
      if (String(r.rhoMaxId) === "90") rho90_dwell_s += (safe(r.dtMs) / 1000);
    }

    return {
      rhoMaxId_t0: start,
      rhoMaxId_firstSwitch_tSec: firstSwitchT,
      rhoMaxId_switchCount: switchCount,
      rho90_dwell_s,
    };
  }

  // ---------- Dream run (no watch) ----------
  async function doDreamRun(cfg) {
    const {
      injectorIds = [82, 90],
      blocks = 6,
      strobeTicks = 10,
      dreamEveryMs = 100,

      injectP = 0,
      injectRho = 400,
      injectPsi = 0,

      restoreBaseline = true,

      stepPerTick = 1,
      stepDt = 0.12,
      pressC = 20,
      damping = 4,

      timingMode = "relaxed",
      spinMs = 1.0,
    } = cfg;

    const phy = getPhysics();

    if (restoreBaseline) {
      if (!globalThis.SOLBaseline?.restore) throw new Error("SOLBaseline.restore() missing.");
      await globalThis.SOLBaseline.restore();
    }

    const totalTicks = blocks * strobeTicks;

    // drift-compensated dream ticks
    const t0 = performance.now();
    for (let tick = 0; tick < totalTicks; tick++) {
      const targetMs = t0 + tick * dreamEveryMs;
      await waitUntil(targetMs, { timingMode, spinMs });

      const id = strobePick(injectorIds, tick, strobeTicks);
      inject(phy, id, { injectP, injectRho, injectPsi });

      for (let k = 0; k < stepPerTick; k++) stepOnce(phy, stepDt, pressC, damping);
    }

    const startId_t0 = rhoMaxId(phy);
    const lastInjectedId = strobePick(injectorIds, totalTicks - 1, strobeTicks);
    const lastBlockParity = (blocks - 1) % 2;

    return { startId_t0, lastInjectedId, lastBlockParity };
  }

  // ---------- Phase-scan calibration ----------
  async function calibratePhaseMap(opts) {
    const {
      orderTag = "A",
      injectorIds = [82, 90],
      blocksList = [4,5,6,7,8,9,10],
      reps = 2,
      dreamCfg = {},
    } = opts;

    const map = {};  // blocks -> { counts:{id:count}, reps, modeId }
    for (const b of blocksList) {
      const counts = {};
      for (let r = 0; r < reps; r++) {
        const res = await doDreamRun({ injectorIds, blocks: b, restoreBaseline: true, ...dreamCfg });
        const id = String(res.startId_t0);
        counts[id] = (counts[id] || 0) + 1;
      }
      const keys = Object.keys(counts);
      let modeId = "";
      let best = -1;
      for (const k of keys) if (counts[k] > best) { best = counts[k]; modeId = k; }
      map[String(b)] = { counts, reps, modeId };
    }

    // pick best blocks for 90 and 82 based on modeId frequency
    function bestFor(wantId) {
      let bestB = null, bestAcc = -1;
      for (const b of blocksList) {
        const rec = map[String(b)];
        const acc = (rec.counts?.[String(wantId)] || 0) / rec.reps;
        if (acc > bestAcc) { bestAcc = acc; bestB = b; }
      }
      return { blocks: bestB, acc: bestAcc };
    }

    const best90 = bestFor("90");
    const best82 = bestFor("82");

    return { orderTag, injectorIds, blocksList, reps, map, best90, best82 };
  }

  // ---------- Mode select using calibrated blocks ----------
  async function selectModePhase(cfg) {
    const {
      target = "start90",
      calib,
      dreamCfg = {},
      verify = true,
      verifyRetry = true,
      minAcc = 0.5, // require at least this confidence from calibration
    } = cfg;

    const wantId = target === "start82" ? "82" : "90";
    const best = wantId === "82" ? calib.best82 : calib.best90;

    if (best.blocks == null || best.acc < minAcc) {
      console.warn(`[LatchIdentityV5] ${calib.orderTag} cannot reliably land ${wantId} (best acc=${best.acc}).`);
      return null;
    }

    const blocks = best.blocks;
    const res = await doDreamRun({ injectorIds: calib.injectorIds, blocks, restoreBaseline: true, ...dreamCfg });

    if (verify && String(res.startId_t0) !== wantId) {
      console.warn(`[LatchIdentityV5] mismatch: wanted ${wantId} got ${res.startId_t0} (blocks=${blocks}).`);
      if (verifyRetry) {
        // One rescan with same settings
        const rescanned = await calibratePhaseMap({
          orderTag: calib.orderTag,
          injectorIds: calib.injectorIds,
          blocksList: calib.blocksList,
          reps: calib.reps,
          dreamCfg,
        });
        const best2 = wantId === "82" ? rescanned.best82 : rescanned.best90;

        if (best2.blocks == null || best2.acc < minAcc) return null;

        const blocks2 = best2.blocks;
        const res2 = await doDreamRun({ injectorIds: rescanned.injectorIds, blocks: blocks2, restoreBaseline: true, ...dreamCfg });
        if (String(res2.startId_t0) !== wantId) return null;

        return { ...res2, target, usedBlocks: blocks2, usedAcc: best2.acc, recalibrated: true, calib: rescanned };
      }
      return null;
    }

    return { ...res, target, usedBlocks: blocks, usedAcc: best.acc, recalibrated: false, calib };
  }

  // ---------- Watch afterstate ----------
  async function watchAfter(opts) {
    const {
      label = "watch",
      orderTag = "A",
      durationLabel = "short",
      target = "start90",
      dreamMeta = null,

      watchSeconds = 30,
      everyMs = 200,
      timingMode = "tight",
      spinMs = 2.0,

      progressEveryTicks = 25,
    } = opts;

    const phy = getPhysics();
    const rows = [];

    const startMs = performance.now();
    let prevMs = startMs;

    const totalTicks = Math.max(1, Math.round((watchSeconds * 1000) / everyMs));
    console.log(`[LatchIdentityV5] WATCH ${label} (${watchSeconds}s @ ${everyMs}ms) timingMode=${timingMode} spinMs=${spinMs}`);

    let missed = 0;

    for (let tick = 0; tick < totalTicks; tick++) {
      const targetMs = startMs + tick * everyMs;
      await waitUntil(targetMs, { timingMode, spinMs });

      const nowMs = performance.now();
      const tSec = Number(((nowMs - startMs) / 1000).toFixed(3));
      const dtMs = tick === 0 ? 0 : (nowMs - prevMs);
      const lateByMs = nowMs - targetMs;
      if (lateByMs > everyMs) missed++;

      const s = sample(phy);

      const row = {
        label,
        orderTag,
        durationLabel,
        target,
        watchSeconds,
        everyMs,
        timingMode,
        spinMs,

        tick,
        tSec,
        dtMs: Number(dtMs.toFixed(3)),
        lateByMs: Number(lateByMs.toFixed(3)),
        missedSoFar: missed,

        entropy: s.ent,
        rhoSum: s.rhoSum,
        rhoConc: s.rhoConc,
        rhoMaxId: s.rhoMaxId,
        meanP: s.meanP,
        pMax: s.pMax,
        pMaxId: s.pMaxId,
        maxAbsFlux: s.maxAbsFlux,
        sumAbsFlux: s.sumAbsFlux,

        // dream metadata (copied into every row for easy filtering)
        blocks: dreamMeta?.usedBlocks ?? "",
        startId_t0: dreamMeta?.startId_t0 ?? "",
        lastInjected: dreamMeta?.lastInjectedId ?? "",
        lastBlockParity: dreamMeta?.lastBlockParity ?? "",
        usedAcc: dreamMeta?.usedAcc ?? "",
      };

      rows.push(row);
      prevMs = nowMs;

      if (tick % progressEveryTicks === 0) {
        console.log(`[LatchIdentityV5] t=${tSec}s tick=${tick} lateBy=${row.lateByMs}ms missed=${missed} rhoMaxId=${row.rhoMaxId}`);
      }
    }

    const sw = computeSwitchMetrics(rows);
    const entropyPeak = Math.max(...rows.map((r) => r.entropy));
    const maxFlux = Math.max(...rows.map((r) => r.maxAbsFlux));
    const maxMeanP = Math.max(...rows.map((r) => r.meanP));
    const avgAbsLate = rows.length > 1 ? rows.slice(1).reduce((a, r) => a + Math.abs(r.lateByMs), 0) / (rows.length - 1) : 0;

    const summary = {
      label,
      orderTag,
      durationLabel,
      target,
      watchSeconds,
      everyMs,
      timingMode,
      spinMs,
      ticks: rows.length,
      avgAbsLateByMs: Number(avgAbsLate.toFixed(3)),
      missedTicksTotal: missed,

      blocks: dreamMeta?.usedBlocks ?? "",
      startId_t0: dreamMeta?.startId_t0 ?? "",
      lastInjected: dreamMeta?.lastInjectedId ?? "",
      lastBlockParity: dreamMeta?.lastBlockParity ?? "",
      usedAcc: dreamMeta?.usedAcc ?? "",

      rhoMaxId_mode: mode(rows.map((r) => String(r.rhoMaxId))),
      entropy_peak: entropyPeak,
      maxAbsFlux_peak: maxFlux,
      meanP_peak: maxMeanP,

      rhoSum_end: rows[rows.length - 1].rhoSum,
      maxAbsFlux_end: rows[rows.length - 1].maxAbsFlux,
      meanP_end: rows[rows.length - 1].meanP,

      ...sw,
    };

    return { rows, summary };
  }

  // ---------- Main runner ----------
  async function run(opts = {}) {
    const runId = `latchIdentityV5_${isoTag()}`;

    const {
      orders = [
        { orderTag: "A_82-90", injectorIds: [82, 90] },
        { orderTag: "B_90-82", injectorIds: [90, 82] },
      ],

      durations = [
        { durationLabel: "short", watchSeconds: 30 },
        { durationLabel: "medium", watchSeconds: 90 },
        { durationLabel: "long", watchSeconds: 120 },
      ],

      everyMs = 200,
      timingMode = "tight",
      spinMs = 2.0,

      // Dream config
      strobeTicks = 10,
      dreamEveryMs = 100,
      blocksList = [4,5,6,7,8,9,10],
      reps = 2,

      injectRho = 400,
      injectPsi = 0,       // keep 0 for identity runs (psi can be trim AFTER)
      stepPerTick = 1,
      stepDt = 0.12,
      pressC = 20,
      damping = 4,

      minAcc = 0.5,        // require at least 50% hit-rate in calibration
      download = true,
      filenamePrefix = "sol_latchIdentityV5",
    } = opts;

    if (!globalThis.SOLBaseline?.restore) {
      throw new Error("SOLBaseline.restore() not found. Install SOLBaseline Unified first.");
    }

    // Baseline sanity restore
    await globalThis.SOLBaseline.restore();
    console.log(`[LatchIdentityV5] runId=${runId} baseline:`, globalThis.__SOL_BASELINE_META ?? "(no meta)");

    const masterSummary = [];
    const masterTrace = [];

    const dreamCfg = {
      strobeTicks,
      dreamEveryMs,
      injectRho,
      injectPsi,
      stepPerTick,
      stepDt,
      pressC,
      damping,
      timingMode: "relaxed", // dream timing doesn't need spin-burn
      spinMs: 1.0,
    };

    for (const ord of orders) {
      console.log(`[LatchIdentityV5] Calibrating order ${ord.orderTag} injectorIds=${JSON.stringify(ord.injectorIds)} blocksList=${blocksList} reps=${reps}`);
      const calib = await calibratePhaseMap({
        orderTag: ord.orderTag,
        injectorIds: ord.injectorIds,
        blocksList,
        reps,
        dreamCfg,
      });

      masterSummary.push({
        runId,
        kind: "calibration",
        orderTag: calib.orderTag,
        injectorIds_json: JSON.stringify(calib.injectorIds),
        blocksList_json: JSON.stringify(calib.blocksList),
        reps: calib.reps,
        phaseMap_json: JSON.stringify(calib.map),
        best90_blocks: calib.best90.blocks,
        best90_acc: calib.best90.acc,
        best82_blocks: calib.best82.blocks,
        best82_acc: calib.best82.acc,
      });

      for (const target of ["start90", "start82"]) {
        // Select mode once per duration (we restore baseline for every dream)
        for (const dur of durations) {
          const label = `${ord.orderTag}_${target}_${dur.durationLabel}`;

          const dreamMeta = await selectModePhase({
            target,
            calib,
            dreamCfg,
            verify: true,
            verifyRetry: true,
            minAcc,
          });

          if (!dreamMeta) {
            console.warn(`[LatchIdentityV5] selectMode failed for ${label}. Skipping watch.`);
            masterSummary.push({
              runId,
              kind: "selectFail",
              label,
              orderTag: ord.orderTag,
              target,
              durationLabel: dur.durationLabel,
              reason: "cannot land target reliably under current calibration",
              best90_blocks: calib.best90.blocks,
              best90_acc: calib.best90.acc,
              best82_blocks: calib.best82.blocks,
              best82_acc: calib.best82.acc,
            });
            continue;
          }

          // Watch (NO restore)
          const w = await watchAfter({
            label,
            orderTag: ord.orderTag,
            durationLabel: dur.durationLabel,
            target,
            dreamMeta,
            watchSeconds: dur.watchSeconds,
            everyMs,
            timingMode,
            spinMs,
          });

          // Append master outputs
          masterSummary.push({ runId, kind: "watchSummary", ...w.summary });
          masterTrace.push(...w.rows);
        }
      }
    }

    if (download) {
      const stamp = isoTag();
      const fSum = `${filenamePrefix}_MASTER_summary_${runId}_${stamp}.csv`;
      const fTrace = `${filenamePrefix}_MASTER_trace_${runId}_${stamp}.csv`;
      downloadCSVUnion(fSum, masterSummary);
      downloadCSVUnion(fTrace, masterTrace);
      console.log(`[LatchIdentityV5] downloaded: ${fSum} + ${fTrace}`);
    }

    globalThis.__SOL_LATCHIDENTITYV5__ = { runId, masterSummary, masterTrace };
    return { runId, masterSummary, masterTrace };
  }

  globalThis.solLatchIdentityV5 = { run };
  console.log("solLatchIdentityV5 installed.");
  console.log("Run: await solLatchIdentityV5.run({ reps:2, blocksList:[4,5,6,7,8,9,10], everyMs:200, timingMode:'tight', spinMs:2.0 })");
})();
