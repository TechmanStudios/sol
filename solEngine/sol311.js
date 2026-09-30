(async () => {
  "use strict";

  // ============================================================
  // SOL Phase 3.11 Kickoff Pack v1
  // - Latch mode-select (lastInjected rule, with mismatch scan+retry)
  // - Drift-compensated, timing-stable watch loop (tight mode w/ optional spin)
  // - Flux "stuck" detector + constitutive stabilizer hooks (law-shaped)
  // - Outputs ONLY at end: MASTER summary + MASTER trace (union header)
  // UI-neutral: no camera moves.
  //
  // Install: paste this whole script.
  // Run:
  //   await sol311.runPack();
  // or:
  //   await sol311.run({ target:"start90", stabilizer:"none", watchSeconds:120 });
  // ============================================================

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const safe = (x) => (Number.isFinite(x) ? x : 0);
  const isoTag = () => new Date().toISOString().replace(/[:.]/g, "-");
  const clamp01 = (x) => Math.max(0, Math.min(1, x));

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

  function strobePick(injectorIds, blockIdx) {
    // blockIdx = 0..blocks-1
    return injectorIds[blockIdx % injectorIds.length];
  }

  function rhoMaxId(phy) {
    let best = -Infinity, bestId = "";
    for (const n of phy.nodes || []) {
      const r = safe(n?.rho);
      if (r > best) { best = r; bestId = String(n?.id ?? ""); }
    }
    return bestId;
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
      pSum += p;
      count++;
      if (p > pMax) { pMax = p; pMaxId = String(n?.id ?? ""); }
    }
    const meanP = count ? pSum / count : 0;
    return { meanP, pSum, pMax, pMaxId };
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

  // ---------- CSV download (UNION header) ----------
  function downloadCSVUnion(filename, rows) {
    if (!rows?.length) {
      console.warn(`[sol311] no rows to write: ${filename}`);
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

  // ---------- Timing metronome ----------
  async function waitUntil(targetMs, { timingMode = "tight", spinMs = 2.0 } = {}) {
    while (true) {
      const now = performance.now();
      const remaining = targetMs - now;
      if (remaining <= 0) return;

      if (timingMode !== "tight") {
        await sleep(remaining);
        return;
      }

      const guard = spinMs + 2.0;
      if (remaining > guard) {
        await sleep(Math.max(0, remaining - guard));
        continue;
      }

      while (performance.now() < targetMs) {}
      return;
    }
  }

  // ---------- Wake lock (best-effort) ----------
  async function tryWakeLock() {
    try {
      if (!("wakeLock" in navigator)) return { ok: false, reason: "no wakeLock API" };
      const lock = await navigator.wakeLock.request("screen");
      return { ok: true, lock };
    } catch (e) {
      return { ok: false, reason: String(e?.message || e) };
    }
  }

  // ============================================================
  // LATCH: mode select via "lastInjected"
  // ============================================================

  async function dreamLatch(cfg) {
    const {
      injectorIds = [90, 82],      // default: order B (more stable in V5)
      blocks = 5,                  // controls lastInjected via parity
      strobeTicks = 10,
      dreamEveryMs = 100,          // per tick
      injectRho = 400,
      injectPsi = 0,
      injectP = 0,

      stepPerTick = 1,
      stepDt = 0.12,
      pressC = 20,
      damping = 4,

      restoreBaseline = true,

      // dream timing: relaxed is fine; we care more about watch timing
      dreamTimingMode = "relaxed",
      dreamSpinMs = 1.0,
    } = cfg;

    const phy = getPhysics();

    if (restoreBaseline) {
      if (!globalThis.SOLBaseline?.restore) {
        throw new Error("SOLBaseline.restore() not found. Install SOLBaseline Unified first.");
      }
      await globalThis.SOLBaseline.restore();
    }

    const totalTicks = blocks * strobeTicks;
    const t0 = performance.now();

    for (let tick = 0; tick < totalTicks; tick++) {
      const targetMs = t0 + tick * dreamEveryMs;
      await waitUntil(targetMs, { timingMode: dreamTimingMode, spinMs: dreamSpinMs });

      const blockIdx = Math.floor(tick / strobeTicks);
      const id = strobePick(injectorIds, blockIdx);

      inject(phy, id, { injectRho, injectPsi, injectP });
      for (let k = 0; k < stepPerTick; k++) stepOnce(phy, stepDt, pressC, damping);
    }

    const startId_t0 = rhoMaxId(phy);
    const lastBlockIdx = blocks - 1;
    const lastInjected = strobePick(injectorIds, lastBlockIdx);
    const lastBlockParity = lastBlockIdx % 2;

    return {
      startId_t0: String(startId_t0),
      lastInjected: String(lastInjected),
      blocks,
      strobeTicks,
      injectorIds_json: JSON.stringify(injectorIds),
      lastBlockParity,
    };
  }

  function blocksForLastInjected({ injectorIds, wantId, preferBlocks = 5 }) {
    // lastInjected = injectorIds[(blocks-1) % 2] for 2 injectors
    // so choose blocks parity to land wantId.
    const a = String(injectorIds[0]);
    const b = String(injectorIds[1]);
    const want = String(wantId);

    if (want !== a && want !== b) return null;

    // If want = injectorIds[0], need (blocks-1)%2 = 0 => blocks odd.
    // If want = injectorIds[1], need (blocks-1)%2 = 1 => blocks even.
    const needOdd = (want === a);
    const preferOdd = (preferBlocks % 2 === 1);

    if (needOdd === preferOdd) return preferBlocks;
    return preferBlocks + 1; // flip parity by +1
  }

  async function selectMode(cfg = {}) {
    const {
      target = "start90",
      injectorIds = [90, 82],   // default order B
      preferBlocks90 = 5,
      preferBlocks82 = 4,
      scanOffsets = [-2, -1, 0, 1, 2, 3],

      // dream config
      strobeTicks = 10,
      dreamEveryMs = 100,
      injectRho = 400,
      injectPsi = 0,
      injectP = 0,

      stepPerTick = 1,
      stepDt = 0.12,
      pressC = 20,
      damping = 4,
    } = cfg;

    const wantId = (target === "start82") ? "82" : "90";
    const preferBlocks = (wantId === "90") ? preferBlocks90 : preferBlocks82;

    // Primary guess based on lastInjected rule
    const primary = blocksForLastInjected({ injectorIds, wantId, preferBlocks });
    if (primary == null) throw new Error(`[sol311] wantId ${wantId} not in injectorIds ${JSON.stringify(injectorIds)}`);

    // Try primary, then scan nearby blocks if mismatch
    const tried = [];
    const candidates = [primary].concat(
      scanOffsets.map((d) => primary + d).filter((b) => b >= 1)
    );

    for (const blocks of candidates) {
      if (tried.includes(blocks)) continue;
      tried.push(blocks);

      const res = await dreamLatch({
        injectorIds, blocks, strobeTicks, dreamEveryMs,
        injectRho, injectPsi, injectP,
        stepPerTick, stepDt, pressC, damping,
        restoreBaseline: true,
      });

      const ok = (String(res.startId_t0) === wantId);
      if (ok) {
        console.log(`[sol311] selectMode(${target}) OK: startId_t0=${res.startId_t0} blocks=${blocks} lastInjected=${res.lastInjected}`);
        return { target, wantId, ok: true, ...res, triedBlocks_json: JSON.stringify(tried) };
      }

      console.warn(`[sol311] selectMode(${target}) mismatch: wanted ${wantId}, got ${res.startId_t0} blocks=${blocks} lastInjected=${res.lastInjected}`);
    }

    console.error(`[sol311] selectMode(${target}) FAILED. Tried blocks=${JSON.stringify(tried)} injectorIds=${JSON.stringify(injectorIds)}`);
    return { target, wantId, ok: false, injectorIds_json: JSON.stringify(injectorIds), triedBlocks_json: JSON.stringify(tried) };
  }

  // ============================================================
  // 3.11 Constitutive stabilizers (law-shaped, minimal)
  // ============================================================

  function sigmoid(x) {
    // stable-ish sigmoid
    if (x > 20) return 1;
    if (x < -20) return 0;
    return 1 / (1 + Math.exp(-x));
  }

  function getTopKNodesBy(nodes, key, k = 10) {
    const arr = (nodes || []).slice().filter(Boolean);
    arr.sort((a, b) => safe(b?.[key]) - safe(a?.[key]));
    return arr.slice(0, k);
  }

  function stabilizer_none() {
    return { name: "none", onTick: () => ({ did: false }) };
  }

  function stabilizer_softLeak(opts = {}) {
    // Smooth "leak law" that only engages when system shows potential/flux buildup.
    // No caps; just gentle state-dependent dissipation on top-K nodes.
    const {
      meanP_on = 0.05,     // start engaging above this
      maxFlux_on = 0.25,   // or if flux spikes
      kP = 0.004,          // per-tick scale for pressure bleed
      kRho = 0.0015,       // per-tick scale for rho bleed
      pScale = 0.15,       // slope of sigmoid vs p
      rhoScale = 0.25,
      topK = 12,
    } = opts;

    return {
      name: "softLeak",
      onTick: ({ phy, s }) => {
        const engage = (s.meanP > meanP_on) || (s.maxAbsFlux > maxFlux_on);
        if (!engage) return { did: false };

        // Law-shaped: bleed proportionally to how far above "typical" we are
        const hotP = getTopKNodesBy(phy.nodes, "p", topK);
        const hotR = getTopKNodesBy(phy.nodes, "rho", topK);

        let touched = 0;

        for (const n of hotP) {
          const p = safe(n.p);
          const g = sigmoid((p - meanP_on) / pScale);   // 0..1
          const leak = kP * g;
          if (leak > 0 && Number.isFinite(n.p)) {
            n.p *= (1 - leak);
            touched++;
          }
        }

        for (const n of hotR) {
          const r = safe(n.rho);
          const g = sigmoid((r - 0.001) / rhoScale);
          const leak = kRho * g;
          if (leak > 0 && Number.isFinite(n.rho)) {
            n.rho *= (1 - leak);
            touched++;
          }
        }

        return { did: true, touched };
      }
    };
  }

  function stabilizer_dampingPulse(opts = {}) {
    // When flux looks "stuck" (sustained positive slope), do a short pulse of extra steps
    // with higher damping / smaller dt. This is like a "shock absorber" law.
    const {
      flux_on = 0.2,
      pulseSteps = 6,
      pulseDt = 0.08,
      pulseDamping = 6,
      pressC = 20,
    } = opts;

    return {
      name: "dampingPulse",
      onTick: ({ phy, s, fluxStuck }) => {
        if (!fluxStuck) return { did: false };
        if (s.sumAbsFlux < flux_on) return { did: false };

        for (let k = 0; k < pulseSteps; k++) stepOnce(phy, pulseDt, pressC, pulseDamping);
        return { did: true, pulseSteps };
      }
    };
  }

  function makeStabilizer(name, opts = {}) {
    if (name === "softLeak") return stabilizer_softLeak(opts);
    if (name === "dampingPulse") return stabilizer_dampingPulse(opts);
    return stabilizer_none();
  }

  // ============================================================
  // WATCH: timing-stable loop + flux-stuck detector
  // ============================================================

  async function watch(cfg = {}) {
    const {
      runId = `sol311_${isoTag()}`,
      label = "watch",
      target = "start90",

      // latch
      injectorIds = [90, 82],
      preferBlocks90 = 5,
      preferBlocks82 = 4,
      strobeTicks = 10,
      dreamEveryMs = 100,
      injectRho = 400,
      injectPsi = 0,
      injectP = 0,
      stepPerTick = 1,
      stepDt = 0.12,
      pressC = 20,
      damping = 4,

      // watch timing
      watchSeconds = 120,
      everyMs = 200,
      timingMode = "tight",
      spinMs = 2.0,

      // freeze safety
      autoStepIfFrozen = true,
      frozenTol = 1e-14,
      frozenSamplesToTrigger = 10,
      restStepsPerTrigger = 10,

      // flux stuck detector (slope on sumAbsFlux)
      stuckWindow = 12,          // ticks window for slope (~2.4s at 200ms)
      stuckMinSlope = 0.002,     // per-second slope threshold (tunable)
      stuckMinFlux = 0.05,       // require some flux inventory
      stuckMinTicks = 6,         // sustained stuck flags before "event"

      // stabilizer
      stabilizer = "none",       // "none" | "softLeak" | "dampingPulse"
      stabilizerOpts = {},

      // logging
      progressEveryTicks = 25,
    } = cfg;

    const phy = getPhysics();

    // 1) mode select (restore baseline inside selectMode)
    const sel = await selectMode({
      target, injectorIds, preferBlocks90, preferBlocks82,
      strobeTicks, dreamEveryMs,
      injectRho, injectPsi, injectP,
      stepPerTick, stepDt, pressC, damping,
    });

    // If select failed, still return a "summary" record; don't watch stale state.
    if (!sel?.ok) {
      return {
        runId,
        sel,
        rows: [],
        summary: [{
          runId,
          kind: "watchSummary",
          label,
          target,
          stabilizer,
          ok: false,
          reason: "selectMode failed",
          injectorIds_json: JSON.stringify(injectorIds),
          triedBlocks_json: sel?.triedBlocks_json ?? "",
        }]
      };
    }

    const stab = makeStabilizer(stabilizer, stabilizerOpts);

    // 2) watch (NO baseline restore here)
    const rows = [];
    const startMs = performance.now();
    let prevMs = startMs;
    let nextTickMs = startMs;

    const totalTicks = Math.max(1, Math.round((watchSeconds * 1000) / everyMs));

    const ua = navigator.userAgent;
    let missed = 0;
    let frozenCount = 0;

    // for flux stuck slope detection
    const fluxHist = []; // {tSec, sumAbsFlux}
    let stuckRun = 0;
    let stuckEvents = 0;

    console.log(`[sol311] WATCH ${label} target=${target} stabilizer=${stab.name} ${watchSeconds}s @ ${everyMs}ms timingMode=${timingMode} spinMs=${spinMs}`);

    for (let tick = 0; tick < totalTicks; tick++) {
      await waitUntil(nextTickMs, { timingMode, spinMs });

      const nowMs = performance.now();
      const tSec = Number(((nowMs - startMs) / 1000).toFixed(3));
      const dtMs = tick === 0 ? 0 : (nowMs - prevMs);
      const lateByMs = nowMs - nextTickMs;
      if (lateByMs > everyMs) missed++;

      const s = sample(phy);

      // flux stuck detection (slope of sumAbsFlux over window)
      fluxHist.push({ tSec, sumAbsFlux: s.sumAbsFlux });
      if (fluxHist.length > stuckWindow) fluxHist.shift();

      let fluxSlopePerSec = 0;
      if (fluxHist.length >= 2) {
        const a = fluxHist[0];
        const b = fluxHist[fluxHist.length - 1];
        const dt = Math.max(1e-6, (b.tSec - a.tSec));
        fluxSlopePerSec = (b.sumAbsFlux - a.sumAbsFlux) / dt;
      }

      const fluxStuck =
        (s.sumAbsFlux >= stuckMinFlux) &&
        (fluxSlopePerSec >= stuckMinSlope);

      stuckRun = fluxStuck ? (stuckRun + 1) : 0;
      const stuckEvent = (stuckRun === stuckMinTicks);
      if (stuckEvent) stuckEvents++;

      // stabilizer tick
      const stabRes = stab.onTick({ phy, s, tSec, tick, fluxStuck: (stuckRun >= stuckMinTicks) });

      // freeze safety (optional)
      if (autoStepIfFrozen && rows.length) {
        const prev = rows[rows.length - 1];
        const dR = Math.abs(s.rhoSum - safe(prev.rhoSum));
        const dP = Math.abs(s.meanP - safe(prev.meanP));
        const dF = Math.abs(s.maxAbsFlux - safe(prev.maxAbsFlux));
        const frozen = dR < frozenTol && dP < frozenTol && dF < frozenTol;

        frozenCount = frozen ? (frozenCount + 1) : 0;

        if (frozenCount >= frozenSamplesToTrigger) {
          console.warn(`[sol311] frozen (${frozenCount} samples). Forcing ${restStepsPerTrigger} steps…`);
          for (let k = 0; k < restStepsPerTrigger; k++) stepOnce(phy, stepDt, pressC, damping);
          frozenCount = 0;
        }
      }

      rows.push({
        runId,
        label,
        target,
        stabilizer: stab.name,

        // latch metadata
        injectorIds_json: sel.injectorIds_json,
        blocks: sel.blocks,
        lastInjected: sel.lastInjected,
        startId_t0: sel.startId_t0,
        wantId: sel.wantId,
        triedBlocks_json: sel.triedBlocks_json,

        // timing
        tick,
        tSec,
        dtMs: Number(dtMs.toFixed(3)),
        lateByMs: Number(lateByMs.toFixed(3)),
        missedSoFar: missed,
        focus: (document.hasFocus ? document.hasFocus() : null),
        visibility: document.visibilityState,
        ua,

        // state
        entropy: s.entropy,
        rhoSum: s.rhoSum,
        rhoConc: s.rhoConc,
        rhoMaxId: s.rhoMaxId,
        meanP: s.meanP,
        pSum: s.pSum,
        pMax: s.pMax,
        pMaxId: s.pMaxId,
        maxAbsFlux: s.maxAbsFlux,
        sumAbsFlux: s.sumAbsFlux,

        // flux stuck / stabilizer telemetry
        fluxSlopePerSec: Number(fluxSlopePerSec.toFixed(6)),
        fluxStuckFlag: (stuckRun >= stuckMinTicks) ? 1 : 0,
        fluxStuckEvent: stuckEvent ? 1 : 0,
        stabDid: stabRes?.did ? 1 : 0,
        stabInfo: stabRes ? JSON.stringify(stabRes) : "",
      });

      if (tick % progressEveryTicks === 0) {
        console.log(`[sol311] t=${tSec}s tick=${tick} lateBy=${Number(lateByMs.toFixed(1))}ms rhoMaxId=${s.rhoMaxId} fluxSum=${s.sumAbsFlux.toExponential(2)} slope=${fluxSlopePerSec.toExponential(2)} stuckEvents=${stuckEvents}`);
      }

      prevMs = nowMs;
      nextTickMs = startMs + (tick + 1) * everyMs;
    }

    // summary metrics
    const sw = computeSwitchMetrics(rows);
    const entropyPeak = Math.max(...rows.map((r) => safe(r.entropy)));
    const maxFluxPeak = Math.max(...rows.map((r) => safe(r.maxAbsFlux)));
    const sumFluxPeak = Math.max(...rows.map((r) => safe(r.sumAbsFlux)));
    const maxMeanP = Math.max(...rows.map((r) => safe(r.meanP)));
    const avgAbsLate = rows.length > 1 ? rows.slice(1).reduce((a, r) => a + Math.abs(safe(r.lateByMs)), 0) / (rows.length - 1) : 0;

    const fluxStart = safe(rows[0]?.sumAbsFlux);
    const fluxEnd = safe(rows[rows.length - 1]?.sumAbsFlux);
    const fluxGrowthRatio = (fluxStart > 0) ? (fluxEnd / fluxStart) : null;

    const summary = [{
      runId,
      kind: "watchSummary",
      label,
      target,
      stabilizer: stab.name,

      ok: true,

      injectorIds_json: sel.injectorIds_json,
      blocks: sel.blocks,
      lastInjected: sel.lastInjected,
      startId_t0: sel.startId_t0,
      wantId: sel.wantId,
      triedBlocks_json: sel.triedBlocks_json,

      watchSeconds,
      everyMs,
      timingMode,
      spinMs,
      ticks: rows.length,
      missedTicksTotal: missed,
      avgAbsLateByMs: Number(avgAbsLate.toFixed(3)),

      rhoMaxId_mode: mode(rows.map((r) => String(r.rhoMaxId))),
      entropy_peak: entropyPeak,
      maxAbsFlux_peak: maxFluxPeak,
      sumAbsFlux_peak: sumFluxPeak,
      meanP_peak: maxMeanP,

      rhoSum_end: safe(rows[rows.length - 1]?.rhoSum),
      meanP_end: safe(rows[rows.length - 1]?.meanP),
      maxAbsFlux_end: safe(rows[rows.length - 1]?.maxAbsFlux),
      sumAbsFlux_end: fluxEnd,
      sumAbsFlux_start: fluxStart,
      sumAbsFlux_growthRatio: fluxGrowthRatio,

      fluxStuckEvents: stuckEvents,

      ...sw,
    }];

    return { runId, sel, rows, summary };
  }

  // ============================================================
  // RUN PACK: the default 3.11 kickoff experiment set
  // ============================================================

  async function runPack(opts = {}) {
    const runId = opts.runId ?? `sol_phase311_kickoff_${isoTag()}`;

    const {
      // Latch config (default stable order B)
      injectorIds = [90, 82],
      preferBlocks90 = 5,
      preferBlocks82 = 4,
      strobeTicks = 10,
      dreamEveryMs = 100,
      injectRho = 400,
      injectPsi = 0,
      injectP = 0,
      stepPerTick = 1,
      stepDt = 0.12,
      pressC = 20,
      damping = 4,

      // Watch config
      watchSeconds = 120,
      everyMs = 200,
      timingMode = "tight",
      spinMs = 2.0,

      // Stabilizer suite
      stabilizers = [
        { name: "none", opts: {} },
        { name: "softLeak", opts: {} },
        { name: "dampingPulse", opts: {} },
      ],

      // Targets to test
      targets = ["start90", "start82"],

      // Output
      download = true,
      filenamePrefix = "sol_phase311_kickoffPack_v1",
    } = opts;

    if (!globalThis.SOLBaseline?.restore) {
      throw new Error("SOLBaseline.restore() not found. Install SOLBaseline Unified first.");
    }

    // Baseline restore once up front (we restore inside selectMode too, but this verifies readiness)
    await globalThis.SOLBaseline.restore();
    console.log(`[sol311] runPack runId=${runId} baseline meta:`, globalThis.__SOL_BASELINE_META ?? "(no meta)");

    const wl = await tryWakeLock();
    console.log(`[sol311] wakeLock:`, wl.ok ? "OK" : `no/failed (${wl.reason})`);

    const masterSummary = [];
    const masterTrace = [];

    for (const target of targets) {
      for (const stab of stabilizers) {
        const label = `${runId}_${target}_${stab.name}`;

        const res = await watch({
          runId,
          label,
          target,
          stabilizer: stab.name,
          stabilizerOpts: stab.opts,

          injectorIds,
          preferBlocks90,
          preferBlocks82,
          strobeTicks,
          dreamEveryMs,
          injectRho,
          injectPsi,
          injectP,
          stepPerTick,
          stepDt,
          pressC,
          damping,

          watchSeconds,
          everyMs,
          timingMode,
          spinMs,
        });

        masterSummary.push(...res.summary);
        masterTrace.push(...res.rows);
      }
    }

    if (wl.ok && wl.lock) {
      try { wl.lock.release(); } catch (_) {}
    }

    if (download) {
      const stamp = isoTag();
      const fSum = `${filenamePrefix}_MASTER_summary_${runId}_${stamp}.csv`;
      const fTrace = `${filenamePrefix}_MASTER_trace_${runId}_${stamp}.csv`;
      downloadCSVUnion(fSum, masterSummary);
      downloadCSVUnion(fTrace, masterTrace);
      console.log(`[sol311] downloaded: ${fSum} + ${fTrace}`);
    }

    globalThis.__SOL_PHASE311_PACK__ = { runId, masterSummary, masterTrace };
    return { runId, masterSummary, masterTrace };
  }

  // Expose API
  globalThis.sol311 = {
    dreamLatch,
    selectMode,
    watch,
    run: watch,
    runPack,
  };

  console.log("✅ sol311 installed.");
  console.log("Run: await sol311.runPack()");
  console.log("Alt: await sol311.run({ target:'start90', stabilizer:'none', watchSeconds:120 })");

})().catch((err) => console.error("❌ sol311 error:", err));
