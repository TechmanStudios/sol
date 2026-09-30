(async () => {
  "use strict";

  // ============================================================
  // Helpers (UI-neutral)
  // ============================================================
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const safe = (x) => (Number.isFinite(x) ? x : 0);

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

  function inject(phy, id, { injectP = 0, injectRho = 0, injectPsi = 0 }) {
    const n = nodeByIdLoose(phy, id);
    if (!n) return false;
    if (injectP && typeof n.p === "number") n.p += injectP;
    if (injectRho && typeof n.rho === "number") n.rho += injectRho;
    if (injectPsi && typeof n.psi === "number") n.psi += injectPsi;
    return true;
  }

  function nowTag() {
    return new Date().toISOString().replace(/[:.]/g, "-");
  }

  function downloadCSV(filename, rows) {
    // Guaranteed output: if rows empty, write a 1-row CSV with status
    const out = (rows && rows.length) ? rows : [{ status: "no_rows" }];
    const cols = Object.keys(out[0]);
    const esc = (v) => {
      const s = String(v ?? "");
      return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
    };
    const lines = [cols.join(",")].concat(out.map((r) => cols.map((c) => esc(r[c])).join(",")));
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

  // Drift-compensated metronome with optional end-spin (does NOT freeze sim)
  async function waitUntil(targetMs, { timingMode = "tight", spinMs = 1.5 } = {}) {
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

  // ============================================================
  // Latch Controller V23 (block-search calibration)
  // ============================================================
  async function doLatchRun(cfg) {
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

      postSteps = 0, // after recording t0
    } = cfg;

    const phy = getPhysics();

    if (restoreBaseline) {
      if (!globalThis.SOLBaseline?.restore) {
        throw new Error("SOLBaseline.restore() missing. Install SOLBaseline Unified first.");
      }
      await globalThis.SOLBaseline.restore();
    }

    const totalTicks = blocks * strobeTicks;

    for (let tick = 0; tick < totalTicks; tick++) {
      const id = strobePick(injectorIds, tick, strobeTicks);
      inject(phy, id, { injectP, injectRho, injectPsi });

      for (let k = 0; k < stepPerTick; k++) stepOnce(phy, stepDt, pressC, damping);

      await sleep(dreamEveryMs);
    }

    // TRUE t0 sample: immediately after dream ends (no await between last tick and this line)
    const startId_t0 = rhoMaxId(phy);

    for (let k = 0; k < postSteps; k++) stepOnce(phy, stepDt, pressC, damping);
    const startId_post = rhoMaxId(phy);

    const lastBlockIdx = Math.max(0, blocks - 1);
    const lastInjectedId = injectorIds[lastBlockIdx % injectorIds.length];
    const lastBlockParity = lastBlockIdx % 2;

    return { startId_t0, startId_post, blocks, lastInjectedId, lastBlockParity };
  }

  const LC23 = (() => {
    const state = {
      calibrated: false,
      config: null,
      // blockToStartId: { [blocks]: startId_t0 }
      blockToStartId: {},
      // startIdToBestBlocks: { "82": 7, "90": 6, ... }
      startIdToBestBlocks: {},
      lastCalib: null,
    };

    function reset() {
      state.calibrated = false;
      state.config = null;
      state.blockToStartId = {};
      state.startIdToBestBlocks = {};
      state.lastCalib = null;
      console.log("[LatchControllerV23] reset()");
    }

    function rebuildBestBlocks() {
      const best = {};
      for (const [bStr, startId] of Object.entries(state.blockToStartId)) {
        const b = Number(bStr);
        const id = String(startId);
        if (!best[id] || b < best[id]) best[id] = b; // fastest block count wins
      }
      state.startIdToBestBlocks = best;
    }

    async function calibrate(opts = {}) {
      const cfg = {
        injectorIds: [82, 90],
        strobeTicks: 10,
        dreamEveryMs: 100,
        injectP: 0,
        injectRho: 400,
        injectPsi: 0,
        restoreBaseline: true,

        stepPerTick: 1,
        stepDt: 0.12,
        pressC: 20,
        damping: 4,

        postSteps: 0, // critical: keep t0 clean
        baseBlocksA: 5,
        baseBlocksB: 6,
        scanBlocks: [4, 5, 6, 7, 8, 9], // only used if needed
        ...opts,
      };

      state.config = cfg;
      state.blockToStartId = {};
      state.startIdToBestBlocks = {};

      // First try the fast pair.
      const rA = await doLatchRun({ ...cfg, blocks: cfg.baseBlocksA });
      const rB = await doLatchRun({ ...cfg, blocks: cfg.baseBlocksB });

      state.blockToStartId[rA.blocks] = String(rA.startId_t0);
      state.blockToStartId[rB.blocks] = String(rB.startId_t0);

      // If both starts are same, expand scan.
      if (String(rA.startId_t0) === String(rB.startId_t0)) {
        for (const b of cfg.scanBlocks) {
          if (state.blockToStartId[b] != null) continue;
          const r = await doLatchRun({ ...cfg, blocks: b });
          state.blockToStartId[r.blocks] = String(r.startId_t0);

          // early exit if we’ve found both 82 and 90
          const have82 = Object.values(state.blockToStartId).some((x) => String(x) === "82");
          const have90 = Object.values(state.blockToStartId).some((x) => String(x) === "90");
          if (have82 && have90) break;
        }
      }

      rebuildBestBlocks();
      state.calibrated = true;
      state.lastCalib = {
        injectorIds: cfg.injectorIds.slice(),
        strobeTicks: cfg.strobeTicks,
        dreamEveryMs: cfg.dreamEveryMs,
        injectRho: cfg.injectRho,
        stepPerTick: cfg.stepPerTick,
        postSteps: cfg.postSteps,
      };

      const have82 = state.startIdToBestBlocks["82"] != null;
      const have90 = state.startIdToBestBlocks["90"] != null;

      console.log("[LatchControllerV23] calibrated block→start(t0):", state.blockToStartId);
      console.log("[LatchControllerV23] best blocks per startId:", state.startIdToBestBlocks);

      if (!have82 || !have90) {
        console.warn(
          `[LatchControllerV23] WARNING: missing mode(s): have82=${have82} have90=${have90}. ` +
          `This baseline+dream config may be clipped.`
        );
      }

      return {
        blockToStartId: { ...state.blockToStartId },
        best: { ...state.startIdToBestBlocks },
      };
    }

    async function selectMode(opts = {}) {
      if (!state.calibrated) await calibrate(opts);

      const target = opts.target ?? "start90";
      const want = target === "start82" ? "82" : "90";
      const blocks = state.startIdToBestBlocks[want];

      if (!blocks) {
        console.warn(
          `[LatchControllerV23] want ${want} not in mapping. Available: ${JSON.stringify(state.startIdToBestBlocks)}`
        );
        return null;
      }

      const cfg = state.config;

      // One shot + verify; if mismatch, recalibrate+retry once (self-heal)
      const attempt = async () => {
        const r = await doLatchRun({ ...cfg, ...opts, blocks });
        return r;
      };

      let r = await attempt();
      if (String(r.startId_t0) !== want) {
        console.warn(
          `[LatchControllerV23] mismatch: wanted ${want} but got ${r.startId_t0}. Recalibrating + retrying once…`
        );
        await calibrate({ ...cfg, ...opts });
        const blocks2 = state.startIdToBestBlocks[want];
        if (!blocks2) return null;
        r = await doLatchRun({ ...state.config, ...opts, blocks: blocks2 });
        console.log(
          `[LatchControllerV23] retry result: startId_t0=${r.startId_t0} (want=${want}) blocks=${blocks2}`
        );
      }

      console.log(
        `[LatchControllerV23] selectMode(${target}) → startId_t0=${r.startId_t0} blocks=${r.blocks} lastInjected=${r.lastInjectedId} lastParity=${r.lastBlockParity}`
      );

      return {
        target,
        want,
        usedBlocks: r.blocks,
        lastInjectedId: r.lastInjectedId,
        lastBlockParity: r.lastBlockParity,
        observedStartId_t0: String(r.startId_t0),
        observedStartId_post: String(r.startId_post),
      };
    }

    return { reset, calibrate, selectMode, _state: state };
  })();

  // Aliases for older harnesses that expect specific names:
  globalThis.solLatchControllerV23 = LC23;
  globalThis.solLatchControllerV2 = LC23;
  globalThis.solLatchControllerV21 = LC23;
  globalThis.solLatchControllerV22 = LC23;

  console.log("solLatchControllerV23 installed. (Also aliased as V2/V21/V22)");
  console.log("Try: solLatchControllerV23.reset(); await solLatchControllerV23.calibrate();");

  // ============================================================
  // LatchWatch V3 (guaranteed output)
  // ============================================================
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
      if (r > rhoMax) {
        rhoMax = r;
        rhoMaxId = String(n?.id ?? "");
      }
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
      if (p > pMax) {
        pMax = p;
        pMaxId = String(n?.id ?? "");
      }
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

  const solLatchWatchV3 = {
    run: async (opts = {}) => {
      const {
        label = "LatchWatchV3",
        orderTag = "",
        injectorIds = [82, 90],

        target = "start90", // start90 | start82
        watchSeconds = 120,
        everyMs = 200,

        timingMode = "tight",
        spinMs = 1.5,

        // latch config
        latchController = globalThis.solLatchControllerV23,
        latchStepPerTick = 1,
        latchPostSteps = 0,
        latchRestoreBaseline = true,

        // output
        filenamePrefix = "sol_latchWatch",
        download = true,
        progressEverySamples = 50,
      } = opts;

      if (!latchController?.selectMode) throw new Error("Latch controller missing (expected solLatchControllerV23).");
      if (!globalThis.SOLBaseline?.restore) throw new Error("SOLBaseline.restore() missing.");

      const stamp = nowTag();
      const rows = [];
      let sel = null;

      // 1) mode select
      try {
        sel = await latchController.selectMode({
          target,
          injectorIds,
          stepPerTick: latchStepPerTick,
          postSteps: latchPostSteps,
          restoreBaseline: latchRestoreBaseline,
        });
      } catch (e) {
        sel = null;
        console.error("[LatchWatchV3] selectMode threw:", e);
      }

      // If select failed, still emit summary+trace (trace empty) and bail.
      if (!sel) {
        const summary = [{
          label,
          stamp,
          orderTag,
          injectorIds: injectorIds.join("|"),
          target,
          status: "selectMode_failed",
          timingMode,
          everyMs,
          watchSeconds,
        }];
        const summaryFile = `${filenamePrefix}_summary_${target}_${stamp}.csv`;
        const traceFile = `${filenamePrefix}_trace_${target}_${stamp}.csv`;

        if (download) {
          downloadCSV(summaryFile, summary);
          downloadCSV(traceFile, rows);
          console.log(`[LatchWatchV3] downloaded (failed select): ${summaryFile} + ${traceFile}`);
        }
        return { sel: null, summary, rows };
      }

      // 2) watch afterstate
      const phy = getPhysics();
      const startMs = performance.now();
      let nextTickMs = startMs;
      let prevSampleMs = startMs;

      const totalTicks = Math.max(1, Math.round((watchSeconds * 1000) / everyMs));
      let missedTicksTotal = 0;

      console.log(
        `[LatchWatchV3] watching ${watchSeconds}s (${totalTicks} ticks) after ${target}… ` +
        `timingMode=${timingMode} spinMs=${spinMs} focus=${document.hasFocus()} vis=${document.visibilityState}`
      );

      for (let tick = 0; tick < totalTicks; tick++) {
        await waitUntil(nextTickMs, { timingMode, spinMs });

        const nowMs = performance.now();
        const tSec = Number(((nowMs - startMs) / 1000).toFixed(3));
        const dtMs = tick === 0 ? 0 : (nowMs - prevSampleMs);

        const lateByMs = nowMs - nextTickMs;
        if (lateByMs > everyMs) missedTicksTotal++;

        const s = sample(phy);

        rows.push({
          label,
          stamp,
          orderTag,
          injectorIds: injectorIds.join("|"),
          target,
          tick,
          tSec,
          dtMs: Number(dtMs.toFixed(3)),
          lateByMs: Number(lateByMs.toFixed(3)),
          missedTicksTotal,
          visibilityState: document.visibilityState,
          hasFocus: document.hasFocus(),

          usedBlocks: sel.usedBlocks ?? "",
          lastInjectedId: sel.lastInjectedId ?? "",
          lastBlockParity: sel.lastBlockParity ?? "",
          observedStartId_t0: sel.observedStartId_t0 ?? "",
          observedStartId_post: sel.observedStartId_post ?? "",

          entropy: s.ent,
          rhoSum: s.rhoSum,
          rhoConc: s.rhoConc,
          rhoMaxId: s.rhoMaxId,
          meanP: s.meanP,
          pMax: s.pMax,
          pMaxId: s.pMaxId,
          maxAbsFlux: s.maxAbsFlux,
          sumAbsFlux: s.sumAbsFlux,
        });

        if (tick % progressEverySamples === 0) {
          console.log(
            `[LatchWatchV3] t=${tSec}s tick=${tick} lateBy=${Number(lateByMs.toFixed(1))}ms missed=${missedTicksTotal} rhoMaxId=${s.rhoMaxId}`
          );
        }

        prevSampleMs = nowMs;
        nextTickMs = startMs + (tick + 1) * everyMs;
      }

      const switches = computeSwitchMetrics(rows);
      const entropyPeak = Math.max(...rows.map((r) => r.entropy));
      const maxFlux = Math.max(...rows.map((r) => r.maxAbsFlux));
      const maxMeanP = Math.max(...rows.map((r) => r.meanP));
      const lateAbsAvg = rows.length > 1
        ? rows.slice(1).reduce((acc, r) => acc + Math.abs(r.lateByMs), 0) / (rows.length - 1)
        : 0;

      const summary = [{
        label,
        stamp,
        orderTag,
        injectorIds: injectorIds.join("|"),
        target,
        status: "ok",
        timingMode,
        everyMs,
        watchSeconds,
        samples: rows.length,
        missedTicksTotal,
        avgAbsLateByMs: Number(lateAbsAvg.toFixed(3)),
        rhoMaxId_mode: mode(rows.map((r) => String(r.rhoMaxId))),
        entropy_peak: entropyPeak,
        maxAbsFlux_peak: maxFlux,
        meanP_peak: maxMeanP,
        ...switches,
      }];

      const traceFile = `${filenamePrefix}_trace_${target}_${stamp}.csv`;
      const summaryFile = `${filenamePrefix}_summary_${target}_${stamp}.csv`;

      if (download) {
        downloadCSV(summaryFile, summary);
        downloadCSV(traceFile, rows);
        console.log(`[LatchWatchV3] downloaded: ${summaryFile} + ${traceFile}`);
      }

      return { sel, summary, rows };
    }
  };

  globalThis.solLatchWatchV3 = solLatchWatchV3;
  console.log("solLatchWatchV3 installed.");

  // ============================================================
  // LatchIdentity V2 (short + medium + long; guaranteed outputs)
  // ============================================================
  const solLatchIdentityV2 = {
    run: async (opts = {}) => {
      const runId = `latchIdentityV2_${nowTag()}`;

      const {
        orders = [
          { orderTag: "A_82-90", injectorIds: [82, 90] },
          { orderTag: "B_90-82", injectorIds: [90, 82] },
        ],

        durations = {
          short: 30,
          medium: 90,
          long: 120,
        },

        targets = ["start90", "start82"],

        everyMs = 200,
        timingMode = "tight",
        spinMs = 1.5,

        // latch/dream config
        strobeTicks = 10,
        dreamEveryMs = 100,
        injectRho = 400,
        stepPerTick = 1,
        postSteps = 0,

        filenamePrefix = "sol_latchIdentityV2",
        download = true,
      } = opts;

      if (!globalThis.SOLBaseline?.restore) throw new Error("SOLBaseline.restore() missing.");
      const baseMeta = globalThis.__SOL_BASELINE_META ?? {};

      const summaryRows = [];
      const traceRows = [];

      for (const ord of orders) {
        const orderTag = ord.orderTag;
        const injectorIds = ord.injectorIds;

        console.log(`[LatchIdentityV2] === ORDER ${orderTag} (${injectorIds.join(",")}) ===`);

        // Fresh calibration per order (so block-search learns this order)
        solLatchControllerV23.reset();
        const calib = await solLatchControllerV23.calibrate({
          injectorIds,
          strobeTicks,
          dreamEveryMs,
          injectRho,
          stepPerTick,
          postSteps,
          restoreBaseline: true,
        });

        summaryRows.push({
          runId,
          phase: "calibrate",
          orderTag,
          injectorIds: injectorIds.join("|"),
          baseline_createdAt: baseMeta.createdAt ?? "",
          baseline_v: baseMeta.v ?? "",
          strobeTicks,
          dreamEveryMs,
          injectRho,
          stepPerTick,
          postSteps,
          blockToStartId_json: JSON.stringify(calib.blockToStartId),
          best_json: JSON.stringify(calib.best),
        });

        // Watches
        for (const target of targets) {
          for (const [durationLabel, seconds] of Object.entries(durations)) {
            console.log(`[LatchIdentityV2] WATCH ${orderTag} ${target} ${durationLabel} (${seconds}s @ ${everyMs}ms)…`);

            const out = await solLatchWatchV3.run({
              label: "LatchIdentityV2",
              orderTag,
              injectorIds,
              target,
              watchSeconds: seconds,
              everyMs,
              timingMode,
              spinMs,
              latchController: solLatchControllerV23,
              latchStepPerTick: stepPerTick,
              latchPostSteps: postSteps,
              latchRestoreBaseline: true,
              filenamePrefix: "__internal_no_download__", // we’ll download once at end
              download: false,
              progressEverySamples: 25,
            });

            // summary row per segment
            const segSummary = out.summary?.[0] ?? {
              status: "no_summary",
              target,
            };

            summaryRows.push({
              runId,
              phase: "watch",
              orderTag,
              injectorIds: injectorIds.join("|"),
              target,
              durationLabel,
              watchSeconds: seconds,
              everyMs,
              timingMode,
              spinMs,
              baseline_createdAt: baseMeta.createdAt ?? "",
              baseline_v: baseMeta.v ?? "",
              ...segSummary,
            });

            // trace rows per segment
            for (const r of (out.rows || [])) {
              traceRows.push({
                runId,
                phase: "watch",
                orderTag,
                injectorIds: injectorIds.join("|"),
                target,
                durationLabel,
                watchSeconds: seconds,
                everyMs,
                timingMode,
                spinMs,
                ...r,
              });
            }
          }
        }
      }

      const stamp = nowTag();
      const summaryFile = `${filenamePrefix}_summary_${stamp}.csv`;
      const traceFile = `${filenamePrefix}_trace_${stamp}.csv`;

      if (download) {
        downloadCSV(summaryFile, summaryRows);
        downloadCSV(traceFile, traceRows);
        console.log(`[LatchIdentityV2] downloaded: ${summaryFile} + ${traceFile}`);
      }

      globalThis.__SOL_LATCHIDENTITYV2_SUMMARY__ = summaryRows;
      globalThis.__SOL_LATCHIDENTITYV2_TRACE__ = traceRows;

      return { runId, summaryRows, traceRows };
    }
  };

  globalThis.solLatchIdentityV2 = solLatchIdentityV2;

  console.log("solLatchIdentityV2 installed.");
  console.log("Run: await solLatchIdentityV2.run()");

})().catch((err) => console.error("❌ Latch pack error:", err));
