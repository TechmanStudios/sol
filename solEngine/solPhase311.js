/* Phase 3.11 — Constitutive Stabilizers Pack v1
   UI-neutral, baseline restore per run, drift-compensated metronome, CSV outputs.
*/
(() => {
  'use strict';

  const solPhase311 = {
    version: '3.11_stabilizersPack_v1',
    _stopFlag: false,
    stop() { this._stopFlag = true; console.warn('🛑 solPhase311.stop(): stop flag set (will halt after current tick).'); },

    cfg: {
      // Core experiment shape
      injectorIds: [90, 82],      // Order B (stable)
      wantIds: [90, 82],          // run both
      stabilizers: ['none', 'softLeak', 'dampingPulse', 'holdLeak'],

      // Dream (controller) parameters
      dreamBlocks: 14,            // blocks before final forced injector
      dreamBlockSteps: 2,         // steps per block (except final injector)
      injectAmount: 120,

      // Awake (measurement) parameters
      durationMs: 120_000,
      everyMs: 200,               // metronome tick
      dt: 0.12,                   // physics dt per tick
      baseDamp: null,             // null => read from UI slider
      pressC: null,               // null => read from UI slider*scale
      includeBackgroundEdges: false,

      // Timing fidelity
      spinWaitMs: 2.0,            // 0 disables busy-wait near deadlines
      maxLateClampMs: 2000,       // if lateByMs is insane, clamp so stats don’t explode

      // Stuck signature detection (simple windowed slope)
      stuckWindowTicks: 25,       // 25 ticks @ 200ms = 5s window
      fluxSlopeThresh: 0.6,       // absFlux per second (tune)
      pDecayMin: -0.01,           // meanAbsP should NOT be decaying fast if “stuck”
      rhoDecayMin: -0.05,         // rhoSum should NOT be decaying fast if “stuck”

      // Stabilizer: softLeak (law-shaped dissipation)
      softLeak: {
        rhoFloor: 1.0,
        leakK: 0.0025,            // per tick leak on excess rho
        topK: 14,                 // only leak hottest nodes by rho
        neverLeakIds: [90, 82],   // keep basins “pure” for diagnosis; change later if needed
      },

      // Stabilizer: holdLeak (anisotropic “hold the selected basin”)
      holdLeak: {
        margin: 2.0,              // if opponent rho exceeds target by margin, leak opponent
        leakK: 0.006,             // per tick leak applied to opponent excess
      },

      // Stabilizer: dampingPulse (shock absorber when stuck signature appears)
      dampingPulse: {
        boost: 6.0,               // add to damping while pulsing
        pulseTicks: 18,           // 18 ticks @ 200ms = 3.6s pulse
        cooldownTicks: 25,        // min ticks between pulses
        fluxBleed: 0.85,          // multiply edge flux by this during pulse (gentle drain)
      },

      // Sampling / summary
      sampleOffsetsMs: [0, 2000, 5000, 10000], // t0, 2s, 5s, 10s
      basins: [82, 90],
    },

    // -----------------------------
    // Utilities
    // -----------------------------
    _sleep(ms) { return new Promise(r => setTimeout(r, ms)); },

    _isoForFile(d = new Date()) {
      // safe-ish filename timestamp
      const pad = (n) => String(n).padStart(2, '0');
      return `${d.getUTCFullYear()}-${pad(d.getUTCMonth()+1)}-${pad(d.getUTCDate())}T${pad(d.getUTCHours())}-${pad(d.getUTCMinutes())}-${pad(d.getUTCSeconds())}-${String(d.getUTCMilliseconds()).padStart(3,'0')}Z`;
    },

    _csvCell(v) {
      if (v === null || v === undefined) return '';
      const s = String(v);
      return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
    },
    _csvRow(cols) { return cols.map(this._csvCell).join(',') + '\n'; },

    _downloadText(filename, text, mime = 'text/csv') {
      const blob = new Blob([String(text)], { type: mime });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => { try { URL.revokeObjectURL(url); } catch (e) {} }, 250);
    },

    _getApp() { return globalThis.SOLDashboard || window.SOLDashboard || null; },

    async _waitForPhysics({ timeoutMs = 15000, pollMs = 50 } = {}) {
      const t0 = Date.now();
      while (Date.now() - t0 < timeoutMs) {
        const app = this._getApp();
        const phy = app?.state?.physics || window.solver || null;
        if (phy?.nodes?.length && phy?.edges?.length) return phy;
        await this._sleep(pollMs);
      }
      throw new Error('solPhase311: timed out waiting for physics. Is the dashboard fully initialized?');
    },

    _readUiParams(app) {
      const pressC = (app?.dom?.pressureSlider)
        ? (parseFloat(String(app.dom.pressureSlider.value)) * (app.config.pressureSliderScale || 1))
        : 0.1;
      const damp = (app?.dom?.dampSlider)
        ? parseFloat(String(app.dom.dampSlider.value))
        : 0.2;
      return {
        pressC: Number.isFinite(pressC) ? pressC : 0.1,
        damp: Number.isFinite(damp) ? damp : 0.2
      };
    },

    _freezeLiveLoop() {
      const app = this._getApp();
      if (!app?.config) throw new Error('solPhase311: App not ready (no config).');
      if (this._prevDtCap === undefined) this._prevDtCap = app.config.dtCap;
      app.config.dtCap = 0; // UI loop still runs but dt=0 => physics static unless we step manually
    },

    _unfreezeLiveLoop() {
      const app = this._getApp();
      if (!app?.config) return;
      if (this._prevDtCap !== undefined) {
        app.config.dtCap = this._prevDtCap;
        this._prevDtCap = undefined;
      }
    },

    _nodeByIdLoose(phy, id) {
      const direct = (phy?.nodeById?.get) ? phy.nodeById.get(id) : null;
      if (direct) return direct;
      const want = String(id);
      for (const n of (phy?.nodes || [])) if (n?.id != null && String(n.id) === want) return n;
      return null;
    },

    _snapshotState(phy) {
      const nodePairs = [];
      for (const n of (phy.nodes || [])) {
        if (!n || n.id == null) continue;
        nodePairs.push([String(n.id), {
          rho: n.rho, p: n.p, psi: n.psi, psi_bias: n.psi_bias,
          semanticMass: n.semanticMass, semanticMass0: n.semanticMass0,
          b_q: n.b_q, b_charge: n.b_charge, b_state: n.b_state,
          isBattery: !!n.isBattery
        }]);
      }
      const edgeFlux = (phy.edges || []).map(e => (e && Number.isFinite(e.flux)) ? e.flux : 0);
      return { nodePairs, edgeFlux };
    },

    _restoreState(phy, snap) {
      if (!snap) return;
      const map = new Map(snap.nodePairs || []);
      for (const n of (phy.nodes || [])) {
        if (!n || n.id == null) continue;
        const s = map.get(String(n.id));
        if (!s) continue;
        n.rho = s.rho;
        n.p = s.p;
        n.psi = s.psi;
        n.psi_bias = s.psi_bias;
        n.semanticMass = s.semanticMass;
        n.semanticMass0 = s.semanticMass0;
        if (n.isBattery || s.isBattery) {
          n.b_q = s.b_q;
          n.b_charge = s.b_charge;
          n.b_state = s.b_state;
        }
      }
      const edges = phy.edges || [];
      for (let i = 0; i < edges.length; i++) {
        const e = edges[i];
        if (!e) continue;
        e.flux = (snap.edgeFlux && Number.isFinite(snap.edgeFlux[i])) ? snap.edgeFlux[i] : 0;
      }
    },

    _injectById(phy, id, amount) {
      const n = this._nodeByIdLoose(phy, id);
      if (!n) throw new Error(`solPhase311: injector node not found: ${id}`);
      const amt = Math.max(0, Number(amount) || 0);
      n.rho += amt;

      // preserve “constellation barycenter reinforcement” semantics when applicable
      try {
        if (n.isConstellation && typeof phy.reinforceSemanticStar === 'function') {
          const freqBoost = amt / 50.0;
          phy.reinforceSemanticStar(n, freqBoost);
        }
      } catch (e) {}
      return true;
    },

    _computeTotals(phy, includeBackgroundEdges = false) {
      let rhoSum = 0;
      let meanAbsP = 0;
      const nodes = phy.nodes || [];
      for (const n of nodes) {
        const rho = Number.isFinite(n?.rho) ? n.rho : 0;
        const p = Number.isFinite(n?.p) ? n.p : 0;
        rhoSum += rho;
        meanAbsP += Math.abs(p);
      }
      meanAbsP /= Math.max(1, nodes.length);

      let sumAbsFlux = 0;
      for (const e of (phy.edges || [])) {
        if (!e) continue;
        if (!includeBackgroundEdges && e.background) continue;
        const f = Number.isFinite(e.flux) ? e.flux : 0;
        sumAbsFlux += Math.abs(f);
      }
      return { rhoSum, meanAbsP, sumAbsFlux };
    },

    _basinScore(phy, id) {
      const n = this._nodeByIdLoose(phy, id);
      if (!n) return { rho: 0, p: 0 };
      return {
        rho: Number.isFinite(n.rho) ? n.rho : 0,
        p: Number.isFinite(n.p) ? n.p : 0
      };
    },

    _pickBasinId(phy, a = 82, b = 90) {
      const A = this._basinScore(phy, a);
      const B = this._basinScore(phy, b);
      const id = (B.rho > A.rho) ? b : a;
      const margin = Math.abs(B.rho - A.rho);
      return { basinId: id, margin, rhoA: A.rho, rhoB: B.rho, pA: A.p, pB: B.p };
    },

    _rankHotNodesByRho(phy, topK = 10, excludeIds = []) {
      const ex = new Set((excludeIds || []).map(x => String(x)));
      const arr = [];
      for (const n of (phy.nodes || [])) {
        if (!n || n.id == null) continue;
        if (ex.has(String(n.id))) continue;
        const rho = Number.isFinite(n.rho) ? n.rho : 0;
        if (rho <= 0) continue;
        arr.push({ id: n.id, rho });
      }
      arr.sort((x, y) => y.rho - x.rho);
      return arr.slice(0, Math.max(0, topK | 0));
    },

    _applySoftLeak(phy, cfg, counters) {
      const hot = this._rankHotNodesByRho(phy, cfg.topK, cfg.neverLeakIds || []);
      let leaked = 0;
      for (const h of hot) {
        const n = this._nodeByIdLoose(phy, h.id);
        if (!n) continue;
        const excess = Math.max(0, (Number.isFinite(n.rho) ? n.rho : 0) - (cfg.rhoFloor || 0));
        if (excess <= 0) continue;
        const delta = (cfg.leakK || 0) * excess;
        if (delta > 0) {
          n.rho = Math.max(0, n.rho - delta);
          leaked += delta;
        }
      }
      if (leaked > 0) counters.softLeakTicks++;
      return leaked;
    },

    _applyHoldLeak(phy, wantId, cfg, counters) {
      const otherId = (wantId === 82) ? 90 : 82;
      const w = this._basinScore(phy, wantId);
      const o = this._basinScore(phy, otherId);
      if (o.rho > w.rho + (cfg.margin || 0)) {
        const n = this._nodeByIdLoose(phy, otherId);
        if (n) {
          const excess = Math.max(0, o.rho - (w.rho + (cfg.margin || 0)));
          const delta = (cfg.leakK || 0) * excess;
          if (delta > 0) {
            n.rho = Math.max(0, n.rho - delta);
            counters.holdLeakTicks++;
            return delta;
          }
        }
      }
      return 0;
    },

    _bleedFlux(phy, mult = 0.9) {
      const m = Math.max(0, Math.min(1, Number(mult) || 1));
      for (const e of (phy.edges || [])) {
        if (!e || e.background) continue;
        if (!Number.isFinite(e.flux)) continue;
        e.flux *= m;
      }
    },

    _slopeOverWindow(buf) {
      // buf = [{t, x}] oldest..newest ; simple slope = (xN - x0) / (tN - t0)
      if (!buf || buf.length < 2) return 0;
      const a = buf[0], b = buf[buf.length - 1];
      const dt = (b.t - a.t);
      if (!Number.isFinite(dt) || dt <= 1e-9) return 0;
      return (b.x - a.x) / dt;
    },

    async _metronomeLoop({ everyMs, ticks, spinWaitMs, onTick }) {
      const start = performance.now();
      let missedTicks = 0;
      let lateAbsSum = 0;
      let lateMax = 0;

      for (let i = 0; i < ticks; i++) {
        if (this._stopFlag) break;

        const target = start + i * everyMs;

        // coarse sleep until near the deadline
        while (true) {
          const now = performance.now();
          const remain = target - now;
          if (remain <= 0) break;
          if (spinWaitMs > 0 && remain <= spinWaitMs) break;
          await this._sleep(Math.min(50, Math.max(0, remain - (spinWaitMs > 0 ? spinWaitMs : 0))));
        }

        // optional micro spin-wait for fidelity
        if (spinWaitMs > 0) {
          while (performance.now() < target) { /* busy */ }
        }

        const now2 = performance.now();
        let lateByMs = now2 - target;
        if (!Number.isFinite(lateByMs)) lateByMs = 0;
        lateByMs = Math.max(-this.cfg.maxLateClampMs, Math.min(this.cfg.maxLateClampMs, lateByMs));

        if (lateByMs > everyMs) {
          const missed = Math.floor(lateByMs / everyMs);
          missedTicks += missed;
        }

        const lateAbs = Math.abs(lateByMs);
        lateAbsSum += lateAbs;
        lateMax = Math.max(lateMax, lateAbs);

        await onTick({ i, tWallMs: now2 - start, lateByMs });

      }

      const ranTicks = Math.max(0, ticks - (this._stopFlag ? 1 : 0));
      const lateAbsAvg = ranTicks > 0 ? (lateAbsSum / ranTicks) : 0;
      return { missedTicks, lateAbsAvg, lateAbsMax: lateMax };
    },

    // -----------------------------
    // Dream controller (mode select)
    // -----------------------------
    async _selectModeViaLastInjected(phy, wantId, runCfg, log) {
      const { injectorIds, dreamBlocks, dreamBlockSteps, injectAmount } = runCfg;

      // run dream blocks-1 with cyclic injectors + stepping
      let injIndex = 0;
      for (let b = 0; b < Math.max(0, dreamBlocks - 1); b++) {
        const injId = injectorIds[injIndex % injectorIds.length];
        injIndex++;

        this._injectById(phy, injId, injectAmount);

        // step between blocks (dream dynamics)
        for (let s = 0; s < dreamBlockSteps; s++) {
          if (this._stopFlag) return;
          phy.step(runCfg.dt, runCfg.pressC, runCfg.baseDamp);
        }
      }

      // final forced injector = wantId (the actual latch primitive)
      this._injectById(phy, wantId, injectAmount);

      // ensure pressures are up to date for t0 sampling (no postSteps drift)
      try { if (typeof phy.computePressure === 'function') phy.computePressure(runCfg.pressC); } catch (e) {}

      log.lastInjected = wantId;
    },

    // -----------------------------
    // Single run
    // -----------------------------
    async _runOne({ runIndex, wantId, stabilizer }) {
      const app = this._getApp();
      const phy = await this._waitForPhysics();

      // Resolve UI params (unless explicitly set)
      const ui = this._readUiParams(app);
      const runCfg = {
        ...this.cfg,
        wantId,
        stabilizer,
        pressC: (this.cfg.pressC == null) ? ui.pressC : this.cfg.pressC,
        baseDamp: (this.cfg.baseDamp == null) ? ui.damp : this.cfg.baseDamp,
      };

      // Restore baseline (belt + suspenders)
      if (!this._baselineSnap) {
        this._baselineSnap = this._snapshotState(phy);
        try {
          localStorage.setItem(`SOLBaseline_${this.version}`, JSON.stringify(this._baselineSnap));
        } catch (e) {}
      }
      this._restoreState(phy, this._baselineSnap);

      // Clear stop flag for run safety
      if (this._stopFlag) return null;

      const runId = `${this._isoForFile()}_run${String(runIndex).padStart(2, '0')}_${stabilizer}_want${wantId}`;
      const log = { runId, runIndex, wantId, stabilizer, lastInjected: null };

      // ---- DREAM (controller) ----
      await this._selectModeViaLastInjected(phy, wantId, runCfg, log);

      // ---- t0 sampling (truth) ----
      const t0Pick = this._pickBasinId(phy, 82, 90);
      const t0Totals = this._computeTotals(phy, runCfg.includeBackgroundEdges);

      // offset sampling cache
      const offsetMap = new Map();
      offsetMap.set(0, { ...t0Pick, ...t0Totals });

      // ---- AWAKE RUN ----
      const ticks = Math.max(1, Math.round(runCfg.durationMs / runCfg.everyMs));
      const fluxBuf = [];
      const pBuf = [];
      const rhoBuf = [];

      const counters = {
        softLeakTicks: 0,
        holdLeakTicks: 0,
        pulseEvents: 0,
        pulseTicks: 0,
        stuckEvents: 0,
        pulseTicksRemaining: 0,
        pulseCooldown: 0,
      };

      // track switching
      let basinPrev = t0Pick.basinId;
      let firstSwitchAtMs = null;
      let switchCount = 0;

      const traceRows = [];
      const traceHeader = [
        'runId','runIndex','wantId','stabilizer',
        'tick','tWallMs','tSimS','lateByMs',
        'dt','pressC','dampUsed',
        'sumAbsFlux','fluxSlope',
        'meanAbsP','pSlope',
        'rhoSum','rhoSlope',
        'rho82','rho90','p82','p90',
        'basinId','basinMargin',
        'stuckFlag','pulseActive',
        'softLeakDelta','holdLeakDelta','fluxBleedApplied'
      ];
      traceRows.push(this._csvRow(traceHeader));

      const tSimPerTick = runCfg.dt; // simulation seconds advanced each tick
      const sampleOffsets = new Set((runCfg.sampleOffsetsMs || []).map(x => Number(x) || 0));

      const met = await this._metronomeLoop({
        everyMs: runCfg.everyMs,
        ticks,
        spinWaitMs: runCfg.spinWaitMs,
        onTick: async ({ i, tWallMs, lateByMs }) => {
          if (this._stopFlag) return;

          // step physics (base or pulsed damping)
          let dampUsed = runCfg.baseDamp;
          let pulseActive = 0;
          let fluxBleedApplied = 0;

          if (counters.pulseCooldown > 0) counters.pulseCooldown--;

          if (counters.pulseTicksRemaining > 0) {
            pulseActive = 1;
            dampUsed = runCfg.baseDamp + (runCfg.dampingPulse.boost || 0);
            counters.pulseTicksRemaining--;
            counters.pulseTicks++;
            // gentle bleed of edge flux inventory while pulsing
            if (runCfg.dampingPulse.fluxBleed != null) {
              this._bleedFlux(phy, runCfg.dampingPulse.fluxBleed);
              fluxBleedApplied = 1;
            }
            if (counters.pulseTicksRemaining === 0) counters.pulseCooldown = runCfg.dampingPulse.cooldownTicks || 0;
          }

          phy.step(runCfg.dt, runCfg.pressC, dampUsed);

          const totals = this._computeTotals(phy, runCfg.includeBackgroundEdges);
          const pick = this._pickBasinId(phy, 82, 90);

          // update buffers for slope detection
          const tSec = (i * runCfg.everyMs) / 1000;
          fluxBuf.push({ t: tSec, x: totals.sumAbsFlux });
          pBuf.push({ t: tSec, x: totals.meanAbsP });
          rhoBuf.push({ t: tSec, x: totals.rhoSum });
          while (fluxBuf.length > runCfg.stuckWindowTicks) fluxBuf.shift();
          while (pBuf.length > runCfg.stuckWindowTicks) pBuf.shift();
          while (rhoBuf.length > runCfg.stuckWindowTicks) rhoBuf.shift();

          const fluxSlope = this._slopeOverWindow(fluxBuf);
          const pSlope = this._slopeOverWindow(pBuf);
          const rhoSlope = this._slopeOverWindow(rhoBuf);

          // stuck signature (windowed)
          let stuckFlag = 0;
          if (fluxBuf.length >= Math.max(2, runCfg.stuckWindowTicks)) {
            const fluxUp = fluxSlope >= (runCfg.fluxSlopeThresh || 0);
            const pNotDecaying = pSlope >= (runCfg.pDecayMin || 0);
            const rhoNotDecaying = rhoSlope >= (runCfg.rhoDecayMin || 0);
            if (fluxUp && pNotDecaying && rhoNotDecaying) stuckFlag = 1;
          }

          // Stabilizers (law-shaped, minimal)
          let softLeakDelta = 0;
          let holdLeakDelta = 0;

          if (runCfg.stabilizer === 'softLeak') {
            softLeakDelta = this._applySoftLeak(phy, runCfg.softLeak, counters);
          } else if (runCfg.stabilizer === 'holdLeak') {
            // optional gentle global leak as well (keeps it honest)
            softLeakDelta = this._applySoftLeak(phy, runCfg.softLeak, counters);
            holdLeakDelta = this._applyHoldLeak(phy, wantId, runCfg.holdLeak, counters);
          } else if (runCfg.stabilizer === 'dampingPulse') {
            if (stuckFlag && counters.pulseTicksRemaining === 0 && counters.pulseCooldown === 0) {
              counters.stuckEvents++;
              counters.pulseEvents++;
              counters.pulseTicksRemaining = runCfg.dampingPulse.pulseTicks || 1;
              // pulse starts next tick (keeps logging causal order clean)
            }
          } else {
            // none: do nothing
          }

          // switching bookkeeping
          if (pick.basinId !== basinPrev) {
            switchCount++;
            if (firstSwitchAtMs == null) firstSwitchAtMs = tWallMs;
            basinPrev = pick.basinId;
          }

          // store offset samples if requested
          const roundedMs = Math.round(tWallMs);
          for (const offMs of sampleOffsets) {
            if (!offsetMap.has(offMs) && roundedMs >= offMs) {
              offsetMap.set(offMs, { ...pick, ...totals, tWallMs: roundedMs });
            }
          }

          // write trace row
          traceRows.push(this._csvRow([
            runId, runIndex, wantId, stabilizer,
            i, tWallMs.toFixed(3), (i * tSimPerTick).toFixed(4), lateByMs.toFixed(3),
            runCfg.dt, runCfg.pressC, dampUsed,
            totals.sumAbsFlux.toFixed(6), fluxSlope.toFixed(6),
            totals.meanAbsP.toFixed(6), pSlope.toFixed(6),
            totals.rhoSum.toFixed(6), rhoSlope.toFixed(6),
            pick.rhoA.toFixed(6), pick.rhoB.toFixed(6), pick.pA.toFixed(6), pick.pB.toFixed(6),
            pick.basinId, pick.margin.toFixed(6),
            stuckFlag, pulseActive,
            softLeakDelta.toFixed(6), holdLeakDelta.toFixed(6), fluxBleedApplied
          ]));
        }
      });

      // end-of-run sample
      const endTotals = this._computeTotals(phy, runCfg.includeBackgroundEdges);
      const endPick = this._pickBasinId(phy, 82, 90);

      // Collect offset samples in a consistent set
      const offGet = (ms) => offsetMap.get(ms) || null;

      const summary = {
        schema: this.version,
        runId,
        runIndex,
        wantId,
        stabilizer,

        injectorIds_json: JSON.stringify(runCfg.injectorIds),
        dreamBlocks: runCfg.dreamBlocks,
        dreamBlockSteps: runCfg.dreamBlockSteps,
        injectAmount: runCfg.injectAmount,

        everyMs: runCfg.everyMs,
        durationMs: runCfg.durationMs,
        dt: runCfg.dt,
        pressC: runCfg.pressC,
        baseDamp: runCfg.baseDamp,

        lastInjected: log.lastInjected,

        startId_t0: t0Pick.basinId,
        startMargin_t0: t0Pick.margin,

        startId_2s: offGet(2000)?.basinId ?? '',
        startId_5s: offGet(5000)?.basinId ?? '',
        startId_10s: offGet(10000)?.basinId ?? '',

        firstSwitchAtMs: firstSwitchAtMs ?? '',
        switchCount,

        endId: endPick.basinId,
        endMargin: endPick.margin,

        sumAbsFlux_end: endTotals.sumAbsFlux,
        meanAbsP_end: endTotals.meanAbsP,
        rhoSum_end: endTotals.rhoSum,

        softLeakTicks: counters.softLeakTicks,
        holdLeakTicks: counters.holdLeakTicks,
        fluxStuckEvents: counters.stuckEvents,
        dampingPulseEvents: counters.pulseEvents,
        dampingPulseTicks: counters.pulseTicks,

        missedTicks: met.missedTicks,
        lateAbsAvgMs: met.lateAbsAvg,
        lateAbsMaxMs: met.lateAbsMax,
      };

      return { summary, traceCsv: traceRows.join('') };
    },

    // -----------------------------
    // Pack runner
    // -----------------------------
    async runPack(userCfg = {}) {
      this._stopFlag = false;

      // allow override cfg
      if (userCfg && typeof userCfg === 'object') {
        this.cfg = { ...this.cfg, ...userCfg };
      }

      const app = this._getApp();
      if (!app) throw new Error('solPhase311: SOLDashboard not found on window.');

      const phy = await this._waitForPhysics();
      this._freezeLiveLoop();

      // Load baseline from localStorage if present (optional)
      if (!this._baselineSnap) {
        try {
          const raw = localStorage.getItem(`SOLBaseline_${this.version}`);
          if (raw) this._baselineSnap = JSON.parse(raw);
        } catch (e) {}
      }
      if (!this._baselineSnap) this._baselineSnap = this._snapshotState(phy);

      // restore once at pack start
      this._restoreState(phy, this._baselineSnap);

      const startIso = this._isoForFile(new Date());
      const baseName = `sol_phase311_stabilizersPack_v1_${startIso}`;

      const summaryHeader = [
        'schema','runId','runIndex','wantId','stabilizer',
        'injectorIds_json','dreamBlocks','dreamBlockSteps','injectAmount',
        'everyMs','durationMs','dt','pressC','baseDamp',
        'lastInjected',
        'startId_t0','startMargin_t0','startId_2s','startId_5s','startId_10s',
        'firstSwitchAtMs','switchCount',
        'endId','endMargin',
        'sumAbsFlux_end','meanAbsP_end','rhoSum_end',
        'softLeakTicks','holdLeakTicks','fluxStuckEvents','dampingPulseEvents','dampingPulseTicks',
        'missedTicks','lateAbsAvgMs','lateAbsMaxMs'
      ];

      const summaryLines = [];
      summaryLines.push(this._csvRow(summaryHeader));

      // big trace file: append run CSV bodies, but keep only one header overall
      const traceLines = [];
      let traceHeaderWritten = false;

      const runPlan = [];
      for (const wantId of this.cfg.wantIds) {
        for (const st of this.cfg.stabilizers) {
          runPlan.push({ wantId, stabilizer: st });
        }
      }

      console.log(`🧪 Phase 3.11 Pack: ${runPlan.length} runs`);
      console.log('Run plan:', runPlan);

      const tPack0 = performance.now();

      for (let r = 0; r < runPlan.length; r++) {
        if (this._stopFlag) break;

        const { wantId, stabilizer } = runPlan[r];
        console.groupCollapsed(`▶ Run ${r + 1}/${runPlan.length} — want ${wantId} — ${stabilizer}`);
        console.log('Config snapshot:', { ...this.cfg, wantId, stabilizer });

        const out = await this._runOne({ runIndex: r, wantId, stabilizer });
        if (!out) { console.warn('Run returned null (likely stopped).'); console.groupEnd(); break; }

        // summary row
        const s = out.summary;
        summaryLines.push(this._csvRow(summaryHeader.map(k => (k in s ? s[k] : ''))));

        // trace: drop per-run header if present
        const traceCsv = out.traceCsv || '';
        if (!traceHeaderWritten) {
          traceLines.push(traceCsv);
          traceHeaderWritten = true;
        } else {
          const firstNewline = traceCsv.indexOf('\n');
          if (firstNewline >= 0) traceLines.push(traceCsv.slice(firstNewline + 1));
        }

        // small checkpoint (summary only) to localStorage (avoid 5MB blowup)
        try {
          localStorage.setItem(`${baseName}_checkpoint_runIndex`, String(r));
          localStorage.setItem(`${baseName}_checkpoint_summaryRows`, String(summaryLines.length));
        } catch (e) {}

        console.log('Summary:', s);
        console.groupEnd();
      }

      const endIso = this._isoForFile(new Date());
      const base2 = `${baseName}_${endIso}`;

      const summaryCsv = summaryLines.join('');
      const traceCsv = traceLines.join('');

      this._downloadText(`${base2}_MASTER_summary.csv`, summaryCsv);
      this._downloadText(`${base2}_MASTER_trace.csv`, traceCsv);

      const dtPack = ((performance.now() - tPack0) / 1000).toFixed(2);
      console.log(`✅ Phase 3.11 Pack complete in ${dtPack}s. Files downloaded:`);
      console.log(` - ${base2}_MASTER_summary.csv`);
      console.log(` - ${base2}_MASTER_trace.csv`);

      this._unfreezeLiveLoop();
      return { baseName: base2, runsPlanned: runPlan.length, stopped: this._stopFlag };
    }
  };

  // Expose globally
  window.solPhase311 = solPhase311;
  console.log(`✅ solPhase311 installed (${solPhase311.version}). Run: solPhase311.runPack()`);

})();
