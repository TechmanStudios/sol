(async () => {
  "use strict";

  // ============================
  // LatchIdentityV4 (BATCH OUTPUT)
  // - Runs short/medium/long watches
  // - NO downloads until the end
  // - Produces 2 files total: MASTER summary + MASTER trace
  // ============================

  // ---------- helpers ----------
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const safe = (x) => (Number.isFinite(x) ? x : 0);
  const stamp = () => new Date().toISOString().replace(/[:.]/g, "-");
  const nowIso = () => new Date().toISOString();

  function downloadCSV(filename, rows) {
    rows = rows || [];
    if (!rows.length) {
      // still download an empty file with header "note" so you know it ran
      rows = [{ note: "no rows (run may have aborted early)" }];
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

  function getPhysics() {
    const s = globalThis.solver || window.solver;
    if (s?.nodes && s?.edges) return s;
    const p =
      globalThis.SOLDashboard?.state?.physics ??
      globalThis.App?.state?.physics ??
      globalThis.app?.state?.physics ??
      null;
    if (p?.nodes && p?.edges) return p;
    throw new Error("Physics not ready (no solver/nodes/edges). Let dashboard finish initializing.");
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

  function rhoMaxId(phy) {
    let best = -Infinity, bestId = "";
    for (const n of phy.nodes || []) {
      const r = safe(n?.rho);
      if (r > best) { best = r; bestId = String(n?.id ?? ""); }
    }
    return bestId;
  }

  function inject(phy, id, { injectP = 0, injectRho = 0, injectPsi = 0 }) {
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

  // Drift-compensated metronome with optional spin-wait near deadline
  async function waitUntil(targetMs, { timingMode = "tight", spinMs = 1.5 } = {}) {
    while (true) {
      const now = performance.now();
      const remaining = targetMs - now;
      if (remaining <= 0) return;

      if (timingMode === "tight") {
        // staged sleep to reduce overshoot
        if (remaining > 25) { await sleep(remaining - 12); continue; }
        if (remaining > 8)  { await sleep(remaining - 4);  continue; }
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
    return { meanP: count ? pSum / count : 0, pMax, pMaxId };
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

  function summarizeWatch(rows) {
    if (!rows.length) return null;

    const ids = rows.map((r) => String(r.rhoMaxId));
    const t = rows.map((r) => r.tSec);

    const start = ids[0];
    let firstSwitch = null;
    let switchCount = 0;

    for (let i = 1; i < ids.length; i++) {
      if (ids[i] !== ids[i - 1]) {
        switchCount++;
        if (firstSwitch == null && ids[i] !== start) firstSwitch = t[i];
      }
    }

    let rho90_dwell_s = 0;
    for (const r of rows) if (String(r.rhoMaxId) === "90") rho90_dwell_s += safe(r.dtMs) / 1000;

    const absLate = rows.slice(1).map((r) => Math.abs(safe(r.lateByMs)));
    const avgAbsLateByMs = absLate.length ? absLate.reduce((a, b) => a + b, 0) / absLate.length : 0;

    const entropyPeak = Math.max(...rows.map((r) => safe(r.entropy)));
    const maxFlux = Math.max(...rows.map((r) => safe(r.maxAbsFlux)));
    const maxMeanP = Math.max(...rows.map((r) => safe(r.meanP)));

    return {
      runTag: rows[0].runTag,
      label: rows[0].label,
      orderTag: rows[0].orderTag,
      target: rows[0].target,
      durationLabel: rows[0].durationLabel,

      blocks: rows[0].blocks,
      lastInjected: rows[0].lastInjected,
      lastBlockParity: rows[0].lastBlockParity,
      startId_t0: rows[0].startId_t0,

      ticks: rows.length,
      watchSeconds: safe(rows[rows.length - 1].tSec),

      avgAbsLateByMs: Number(avgAbsLateByMs.toFixed(3)),
      missedSoFar_end: rows[rows.length - 1].missedSoFar,

      rhoMaxId_t0: start,
      rhoMaxId_mode: mode(ids),
      rhoMaxId_firstSwitch_tSec: firstSwitch,
      rhoMaxId_switchCount: switchCount,
      rho90_dwell_s: rho90_dwell_s,

      entropy_peak: entropyPeak,
      maxAbsFlux_peak: maxFlux,
      meanP_peak: maxMeanP,
      rhoSum_end: rows[rows.length - 1].rhoSum,
      maxAbsFlux_end: rows[rows.length - 1].maxAbsFlux,
    };
  }

  // ---------- baseline requirement ----------
  if (!globalThis.SOLBaseline?.restore) {
    throw new Error("SOLBaseline not found. Install SOLBaseline Unified first, then rerun.");
  }

  // ---------- dream ----------
  async function doDream({
    orderTag,
    injectorIds,
    blocks,
    strobeTicks,
    dreamEveryMs,
    injectRho,
    injectP = 0,
    injectPsi = 0,
    stepPerTick,
    stepDt,
    pressC,
    damping,
    restoreBaseline = true,
  }) {
    const phy = getPhysics();
    if (restoreBaseline) await SOLBaseline.restore();

    const totalTicks = blocks * strobeTicks;
    let lastInjected = null;

    for (let tick = 0; tick < totalTicks; tick++) {
      const id = strobePick(injectorIds, tick, strobeTicks);
      lastInjected = id;
      inject(phy, id, { injectP, injectRho, injectPsi });

      for (let k = 0; k < stepPerTick; k++) stepOnce(phy, stepDt, pressC, damping);
      await sleep(dreamEveryMs);
    }

    return {
      orderTag,
      injectorIds: JSON.stringify(injectorIds),
      blocks,
      strobeTicks,
      dreamEveryMs,
      injectRho,
      stepPerTick,
      stepDt,
      pressC,
      damping,
      lastInjected: String(lastInjected),
      lastBlockParity: (blocks - 1) % 2,
      startId_t0: String(rhoMaxId(phy)),
    };
  }

  // ---------- watch ----------
  async function doWatch({
    runTag,
    label,
    orderTag,
    target,
    durationLabel,
    watchSeconds,
    everyMs,
    timingMode,
    spinMs,
    dreamMeta,
    progressEvery = 25,
  }) {
    const phy = getPhysics();

    const rows = [];
    const startMs = performance.now();
    let nextTickMs = startMs;
    let prevSampleMs = startMs;

    let missed = 0;
    const totalTicks = Math.max(1, Math.round((watchSeconds * 1000) / everyMs));

    console.log(`[LatchIdentityV4] WATCH ${label} (${watchSeconds}s @ ${everyMs}ms)…`);

    for (let tick = 0; tick < totalTicks; tick++) {
      await waitUntil(nextTickMs, { timingMode, spinMs });

      const nowMs = performance.now();
      const tSec = Number(((nowMs - startMs) / 1000).toFixed(3));
      const dtMs = tick === 0 ? 0 : (nowMs - prevSampleMs);
      const lateByMs = nowMs - nextTickMs;
      if (lateByMs > everyMs) missed++;

      const s = sample(phy);

      rows.push({
        runTag,
        label,
        orderTag,
        target,
        durationLabel,
        tsIso: nowIso(),
        hasFocus: document.hasFocus ? !!document.hasFocus() : "",
        visibility: document.visibilityState ?? "",

        // dream meta
        blocks: dreamMeta.blocks,
        lastInjected: dreamMeta.lastInjected,
        lastBlockParity: dreamMeta.lastBlockParity,
        startId_t0: dreamMeta.startId_t0,

        // watch timing
        tick,
        tSec,
        dtMs: Number(dtMs.toFixed(3)),
        lateByMs: Number(lateByMs.toFixed(3)),
        missedSoFar: missed,

        // telemetry
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

      prevSampleMs = nowMs;
      nextTickMs = startMs + (tick + 1) * everyMs;

      if (tick % progressEvery === 0) {
        console.log(`[LatchIdentityV4] t=${tSec}s tick=${tick} lateBy=${Number(lateByMs.toFixed(0))}ms missed=${missed} rhoMaxId=${s.rhoMaxId}`);
      }
    }

    return rows;
  }

  // ---------- calibration (block parity) ----------
  async function calibrateForOrder({
    orderTag,
    injectorIds,
    strobeTicks,
    dreamEveryMs,
    injectRho,
    stepPerTick,
    stepDt,
    pressC,
    damping,
    reps = 3,
    evenCandidates = [6, 4, 8, 10],
    oddCandidates = [5, 7, 9, 11],
  }) {
    async function score(blocks, want) {
      let ok = 0;
      for (let i = 0; i < reps; i++) {
        const d = await doDream({
          orderTag,
          injectorIds,
          blocks,
          strobeTicks,
          dreamEveryMs,
          injectRho,
          stepPerTick,
          stepDt,
          pressC,
          damping,
          restoreBaseline: true,
        });
        if (String(d.startId_t0) === String(want)) ok++;
      }
      return { blocks, want, ok, acc: ok / reps };
    }

    let bestEven = null;
    for (const b of evenCandidates) {
      const s = await score(b, "90");
      if (!bestEven || s.acc > bestEven.acc) bestEven = s;
      if (s.acc >= 0.9) break;
    }

    let bestOdd = null;
    for (const b of oddCandidates) {
      const s = await score(b, "82");
      if (!bestOdd || s.acc > bestOdd.acc) bestOdd = s;
      if (s.acc >= 0.7) break;
    }

    console.log(`[LatchIdentityV4] Calibrate ${orderTag}: even->90 blocks=${bestEven.blocks} acc=${bestEven.acc}, odd->82 blocks=${bestOdd.blocks} acc=${bestOdd.acc}`);
    return { even: bestEven, odd: bestOdd };
  }

  // ---------- main runner (BATCH OUTPUT) ----------
  async function run({
    strobeTicks = 10,
    dreamEveryMs = 100,
    injectRho = 400,
    stepPerTick = 1,
    stepDt = 0.12,
    pressC = 20,
    damping = 4,

    everyMs = 200,
    timingMode = "tight",
    spinMs = 1.5,

    shortS = 30,
    mediumS = 90,
    longS = 120,

    download = true,
    filenamePrefix = "sol_latchIdentityV4",
  } = {}) {
    const runTag = `latchIdentityV4_${stamp()}`;

    const orders = [
      { orderTag: "A_82-90", injectorIds: [82, 90] },
      { orderTag: "B_90-82", injectorIds: [90, 82] },
    ];

    const durations = [
      { durationLabel: "short", watchSeconds: shortS },
      { durationLabel: "medium", watchSeconds: mediumS },
      { durationLabel: "long", watchSeconds: longS },
    ];

    const masterTrace = [];
    const masterSummary = [];

    // Always attempt to dump whatever we have at the end
    try {
      await SOLBaseline.restore();

      masterSummary.push({
        runTag,
        kind: "note",
        tsIso: nowIso(),
        msg: `Baseline restored. meta=${JSON.stringify(globalThis.__SOL_BASELINE_META ?? {})}`,
        userAgent: navigator.userAgent,
        platform: navigator.platform,
        hwThreads: navigator.hardwareConcurrency ?? "",
      });

      for (const ord of orders) {
        const cal = await calibrateForOrder({
          orderTag: ord.orderTag,
          injectorIds: ord.injectorIds,
          strobeTicks,
          dreamEveryMs,
          injectRho,
          stepPerTick,
          stepDt,
          pressC,
          damping,
        });

        masterSummary.push({
          runTag,
          kind: "calibrate",
          orderTag: ord.orderTag,
          even_blocks: cal.even?.blocks ?? "",
          even_acc: cal.even?.acc ?? "",
          odd_blocks: cal.odd?.blocks ?? "",
          odd_acc: cal.odd?.acc ?? "",
          tsIso: nowIso(),
        });

        const blocksForTarget = (target) => (target === "start82" ? cal.odd?.blocks : cal.even?.blocks);

        for (const target of ["start90", "start82"]) {
          const blocks = blocksForTarget(target);

          if (!blocks) {
            masterSummary.push({
              runTag, kind: "skip", orderTag: ord.orderTag, target,
              tsIso: nowIso(),
              msg: `No blocks available from calibration for ${target}.`,
            });
            continue;
          }

          for (const dur of durations) {
            const label = `${ord.orderTag}_${target}_${dur.durationLabel}`;
            try {
              const dreamMeta = await doDream({
                orderTag: ord.orderTag,
                injectorIds: ord.injectorIds,
                blocks,
                strobeTicks,
                dreamEveryMs,
                injectRho,
                stepPerTick,
                stepDt,
                pressC,
                damping,
                restoreBaseline: true,
              });

              const want = target === "start82" ? "82" : "90";
              const landed = String(dreamMeta.startId_t0) === want;

              masterSummary.push({
                runTag,
                kind: "select",
                label,
                orderTag: ord.orderTag,
                target,
                durationLabel: dur.durationLabel,
                blocks,
                want,
                landed: landed ? 1 : 0,
                startId_t0: dreamMeta.startId_t0,
                lastInjected: dreamMeta.lastInjected,
                lastBlockParity: dreamMeta.lastBlockParity,
                tsIso: nowIso(),
              });

              const rows = await doWatch({
                runTag,
                label,
                orderTag: ord.orderTag,
                target,
                durationLabel: dur.durationLabel,
                watchSeconds: dur.watchSeconds,
                everyMs,
                timingMode,
                spinMs,
                dreamMeta,
              });

              masterTrace.push(...rows);

              const summ = summarizeWatch(rows);
              if (summ) masterSummary.push({ kind: "watch", ...summ });

            } catch (err) {
              console.error(`[LatchIdentityV4] ERROR in ${label}:`, err);
              masterSummary.push({
                runTag,
                kind: "error",
                label,
                orderTag: ord.orderTag,
                target,
                durationLabel: dur.durationLabel,
                tsIso: nowIso(),
                msg: String(err?.message ?? err),
              });
            }
          }
        }
      }

      masterSummary.push({ runTag, kind: "done", tsIso: nowIso(), msg: "LatchIdentityV4 completed normally." });

    } catch (fatal) {
      console.error("[LatchIdentityV4] FATAL:", fatal);
      masterSummary.push({
        runTag,
        kind: "fatal",
        tsIso: nowIso(),
        msg: String(fatal?.message ?? fatal),
      });
    } finally {
      // BATCH OUTPUT: only download here
      const outSummary = `${filenamePrefix}_MASTER_summary_${runTag}.csv`;
      const outTrace = `${filenamePrefix}_MASTER_trace_${runTag}.csv`;

      if (download) {
        downloadCSV(outSummary, masterSummary);
        downloadCSV(outTrace, masterTrace);
        console.log(`[LatchIdentityV4] downloaded (batch): ${outSummary} + ${outTrace}`);
      } else {
        console.log("[LatchIdentityV4] download=false; results left in globals.");
      }

      globalThis.__SOL_LATCHIDENTITYV4_SUMMARY__ = masterSummary;
      globalThis.__SOL_LATCHIDENTITYV4_TRACE__ = masterTrace;
    }

    return { runTag, masterSummary, masterTrace };
  }

  globalThis.solLatchIdentityV4 = { run };
  console.log("✅ solLatchIdentityV4 installed (batch output).");
  console.log("Run: await solLatchIdentityV4.run({ shortS:30, mediumS:90, longS:120, everyMs:200 })");

})().catch((e) => console.error("❌ LatchIdentityV4 install error:", e));
