/* Phase 3.11.2 — BasinGuardHold Pack v1
   Goal: hold want82 without sedation using a margin-conditional, mass-conserving guard.

   UI-neutral ✅
   Baseline restore per run ✅
   t0 sampled immediately ✅
   Deterministic filenames ✅
   Timing telemetry ✅
*/
(() => {
  'use strict';

  const solPhase311_2 = {
    version: '3.11.2_basinGuardHoldPack_v1',
    _stopFlag: false,
    stop() { this._stopFlag = true; console.warn('🛑 solPhase311_2.stop(): stop flag set.'); },

    cfg: {
      injectorIds: [90, 82], // Order B
      wantId: 82,

      // Pack plan (4 runs)
      plan: [
        { dreamBlocks: 15, finalWriteMult: 1.0, stabilizer: 'none' },
        { dreamBlocks: 15, finalWriteMult: 1.0, stabilizer: 'basinGuardHold' },
        { dreamBlocks: 15, finalWriteMult: 2.0, stabilizer: 'none' },
        { dreamBlocks: 15, finalWriteMult: 2.0, stabilizer: 'basinGuardHold' },
      ],

      // Dream
      dreamBlockSteps: 2,
      injectAmount: 120,
      dt: 0.12,

      // Awake
      durationMs: 120_000,
      everyMs: 200,

      // null => read from UI sliders (recommended)
      baseDamp: null,
      pressC: null,

      // Timing fidelity
      spinWaitMs: 2.0,

      // Stabilizer: BasinGuardHold (mass-conserving transfer near boundary)
      basinGuardHold: {
        // Guard activates when margin82minus90 < M_hi
        M_hi: 60.0,            // start pushing back when margin < 60
        k: 0.033,              // delta ≈ k*(M_hi - margin); ~2 when margin~0
        maxDelta: 2.5,         // clamp per tick transfer
        // Optional “deadband” so we don’t micro-chatter when margin is healthy
        deadband: 5.0,         // if margin >= M_hi - deadband, do nothing
      },

      basins: [82, 90],
    },

    // ---------- utils ----------
    _sleep(ms) { return new Promise(r => setTimeout(r, ms)); },
    _isoForFile(d = new Date()) {
      const p = (n) => String(n).padStart(2,'0');
      return `${d.getUTCFullYear()}-${p(d.getUTCMonth()+1)}-${p(d.getUTCDate())}T${p(d.getUTCHours())}-${p(d.getUTCMinutes())}-${p(d.getUTCSeconds())}-${String(d.getUTCMilliseconds()).padStart(3,'0')}Z`;
    },
    _csvCell(v) {
      if (v === null || v === undefined) return '';
      const s = String(v);
      return /[",\n\r]/.test(s) ? `"${s.replace(/"/g,'""')}"` : s;
    },
    _csvRow(cols) { return cols.map(this._csvCell).join(',') + '\n'; },
    _downloadText(filename, text, mime='text/csv') {
      const blob = new Blob([String(text)], { type: mime });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => { try { URL.revokeObjectURL(url); } catch(e){} }, 250);
    },
    _getApp() { return globalThis.SOLDashboard || window.SOLDashboard || null; },

    async _waitForPhysics({ timeoutMs=15000, pollMs=50 } = {}) {
      const t0 = Date.now();
      while (Date.now() - t0 < timeoutMs) {
        const app = this._getApp();
        const phy = app?.state?.physics || window.solver || null;
        if (phy?.nodes?.length && phy?.edges?.length) return phy;
        await this._sleep(pollMs);
      }
      throw new Error('solPhase311_2: timed out waiting for physics.');
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
      if (!app?.config) throw new Error('solPhase311_2: App not ready.');
      if (this._prevDtCap === undefined) this._prevDtCap = app.config.dtCap;
      app.config.dtCap = 0;
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
      if (!n) throw new Error(`solPhase311_2: injector node not found: ${id}`);
      const amt = Math.max(0, Number(amount) || 0);
      n.rho += amt;
      try {
        if (n.isConstellation && typeof phy.reinforceSemanticStar === 'function') {
          const freqBoost = amt / 50.0;
          phy.reinforceSemanticStar(n, freqBoost);
        }
      } catch(e) {}
    },

    _basinScore(phy, id) {
      const n = this._nodeByIdLoose(phy, id);
      if (!n) return { rho: 0, p: 0 };
      return {
        rho: Number.isFinite(n.rho) ? n.rho : 0,
        p: Number.isFinite(n.p) ? n.p : 0
      };
    },

    _pick(phy) {
      const a = this._basinScore(phy, 82);
      const b = this._basinScore(phy, 90);
      const basinId = (b.rho > a.rho) ? 90 : 82;
      const margin = Math.abs(a.rho - b.rho);
      const margin82minus90 = a.rho - b.rho;
      return { basinId, margin, margin82minus90, rho82: a.rho, rho90: b.rho, p82: a.p, p90: b.p };
    },

    _computeTotals(phy) {
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
        if (!e || e.background) continue;
        const f = Number.isFinite(e.flux) ? e.flux : 0;
        sumAbsFlux += Math.abs(f);
      }
      return { rhoSum, meanAbsP, sumAbsFlux };
    },

    async _metronomeLoop({ everyMs, ticks, spinWaitMs, onTick }) {
      const start = performance.now();
      let lateAbsSum = 0;
      let lateAbsMax = 0;

      for (let i = 0; i < ticks; i++) {
        if (this._stopFlag) break;
        const target = start + i * everyMs;

        while (true) {
          const now = performance.now();
          const remain = target - now;
          if (remain <= 0) break;
          if (spinWaitMs > 0 && remain <= spinWaitMs) break;
          await this._sleep(Math.min(50, Math.max(0, remain - (spinWaitMs > 0 ? spinWaitMs : 0))));
        }
        if (spinWaitMs > 0) while (performance.now() < target) { /* spin */ }

        const now2 = performance.now();
        const lateByMs = now2 - target;
        lateAbsSum += Math.abs(lateByMs);
        lateAbsMax = Math.max(lateAbsMax, Math.abs(lateByMs));

        await onTick({ i, tWallMs: now2 - start, lateByMs });
      }

      const ran = Math.max(1, ticks);
      return { lateAbsAvg: lateAbsSum / ran, lateAbsMax };
    },

    async _selectMode(phy, wantId, runCfg, log) {
      const { injectorIds, dreamBlocks, dreamBlockSteps, injectAmount, dt, pressC, baseDamp, finalWriteMult } = runCfg;

      let injIndex = 0;
      for (let b = 0; b < Math.max(0, dreamBlocks - 1); b++) {
        const injId = injectorIds[injIndex % injectorIds.length];
        injIndex++;
        this._injectById(phy, injId, injectAmount);
        for (let s = 0; s < dreamBlockSteps; s++) {
          if (this._stopFlag) return;
          phy.step(dt, pressC, baseDamp);
        }
      }

      // final forced write = wantId (amplified)
      this._injectById(phy, wantId, injectAmount * (finalWriteMult || 1));

      // refresh pressure for clean t0 sampling
      try { if (typeof phy.computePressure === 'function') phy.computePressure(pressC); } catch(e) {}
      log.lastInjected = wantId;
    },

    _applyBasinGuardHold(phy, guardCfg, pick, counters) {
      // We only care about want82 holding vs 90
      const margin = pick.margin82minus90; // positive = 82 ahead
      const M_hi = guardCfg.M_hi;
      const deadband = guardCfg.deadband || 0;

      // no action if margin is comfortably above threshold
      if (margin >= (M_hi - deadband)) return 0;

      const error = (M_hi - margin); // grows as margin shrinks; also grows if margin negative
      let delta = guardCfg.k * error;
      if (!Number.isFinite(delta) || delta <= 0) return 0;

      delta = Math.min(guardCfg.maxDelta, delta);

      const n82 = this._nodeByIdLoose(phy, 82);
      const n90 = this._nodeByIdLoose(phy, 90);
      if (!n82 || !n90) return 0;

      // mass-conserving transfer: 90 -> 82
      const take = Math.min(delta, Math.max(0, n90.rho));
      if (take <= 0) return 0;

      n90.rho -= take;
      n82.rho += take;

      counters.guardTicks++;
      counters.guardTotal += take;
      counters.guardMax = Math.max(counters.guardMax, take);
      return take;
    },

    async _runOne({ runIndex, plan }) {
      const app = this._getApp();
      const phy = await this._waitForPhysics();

      const ui = this._readUiParams(app);
      const runCfg = {
        ...this.cfg,
        ...plan,
        wantId: this.cfg.wantId,
        pressC: (this.cfg.pressC == null) ? ui.pressC : this.cfg.pressC,
        baseDamp: (this.cfg.baseDamp == null) ? ui.damp : this.cfg.baseDamp,
      };

      // baseline restore
      if (!this._baselineSnap) this._baselineSnap = this._snapshotState(phy);
      this._restoreState(phy, this._baselineSnap);

      const runId = `${this._isoForFile()}_run${String(runIndex).padStart(2,'0')}_${plan.stabilizer}_db${plan.dreamBlocks}_fw${plan.finalWriteMult}`;
      const log = { runId, runIndex, wantId: runCfg.wantId, ...plan, lastInjected: null };

      await this._selectMode(phy, runCfg.wantId, runCfg, log);

      // t0 truth sample
      const t0Pick = this._pick(phy);
      const t0Totals = this._computeTotals(phy);

      const counters = { guardTicks: 0, guardTotal: 0, guardMax: 0 };

      const ticks = Math.max(1, Math.round(runCfg.durationMs / runCfg.everyMs));
      const trace = [];
      trace.push(this._csvRow([
        'runId','runIndex','wantId','stabilizer','dreamBlocks','finalWriteMult',
        'tick','tWallMs','lateByMs',
        'basinId','margin','margin82minus90',
        'rho82','rho90','p82','p90',
        'sumAbsFlux','meanAbsP','rhoSum',
        'guardTransfer'
      ]));

      let flipAtMs = null;
      let basinPrev = t0Pick.basinId;
      let switchCount = 0;

      const met = await this._metronomeLoop({
        everyMs: runCfg.everyMs,
        ticks,
        spinWaitMs: runCfg.spinWaitMs,
        onTick: async ({ i, tWallMs, lateByMs }) => {
          if (this._stopFlag) return;

          // step
          phy.step(runCfg.dt, runCfg.pressC, runCfg.baseDamp);

          let pick = this._pick(phy);
          let guardTransfer = 0;

          if (plan.stabilizer === 'basinGuardHold') {
            guardTransfer = this._applyBasinGuardHold(phy, runCfg.basinGuardHold, pick, counters);
            if (guardTransfer > 0) pick = this._pick(phy); // refresh after control
          }

          const totals = this._computeTotals(phy);

          if (pick.basinId !== basinPrev) {
            switchCount++;
            basinPrev = pick.basinId;
          }
          if (flipAtMs == null && pick.basinId !== runCfg.wantId) flipAtMs = Math.round(tWallMs);

          trace.push(this._csvRow([
            runId, runIndex, runCfg.wantId, plan.stabilizer, plan.dreamBlocks, plan.finalWriteMult,
            i, tWallMs.toFixed(3), lateByMs.toFixed(3),
            pick.basinId, pick.margin.toFixed(6), pick.margin82minus90.toFixed(6),
            pick.rho82.toFixed(6), pick.rho90.toFixed(6), pick.p82.toFixed(6), pick.p90.toFixed(6),
            totals.sumAbsFlux.toFixed(6), totals.meanAbsP.toFixed(6), totals.rhoSum.toFixed(6),
            guardTransfer.toFixed(6)
          ]));
        }
      });

      const endPick = this._pick(phy);
      const endTotals = this._computeTotals(phy);

      const summary = {
        schema: this.version,
        runId,
        runIndex,
        wantId: runCfg.wantId,
        stabilizer: plan.stabilizer,

        dreamBlocks: plan.dreamBlocks,
        dreamBlockSteps: runCfg.dreamBlockSteps,
        injectAmount: runCfg.injectAmount,
        finalWriteMult: plan.finalWriteMult,

        everyMs: runCfg.everyMs,
        durationMs: runCfg.durationMs,
        dt: runCfg.dt,
        pressC: runCfg.pressC,
        baseDamp: runCfg.baseDamp,

        lastInjected: log.lastInjected,

        startId_t0: t0Pick.basinId,
        startMargin_t0: t0Pick.margin,

        holdMs_toFlip: (flipAtMs == null) ? '' : flipAtMs,
        switchCount,

        endId: endPick.basinId,
        endMargin: endPick.margin,

        sumAbsFlux_end: endTotals.sumAbsFlux,
        meanAbsP_end: endTotals.meanAbsP,
        rhoSum_end: endTotals.rhoSum,

        guardTicks: counters.guardTicks,
        guardTotalTransfer: counters.guardTotal,
        guardMaxTransfer: counters.guardMax,

        lateAbsAvgMs: met.lateAbsAvg,
        lateAbsMaxMs: met.lateAbsMax,
      };

      return { summary, traceCsv: trace.join('') };
    },

    async runPack(userCfg = {}) {
      this._stopFlag = false;
      if (userCfg && typeof userCfg === 'object') this.cfg = { ...this.cfg, ...userCfg };

      const app = this._getApp();
      if (!app) throw new Error('solPhase311_2: SOLDashboard not found.');

      const phy = await this._waitForPhysics();
      this._freezeLiveLoop();

      if (!this._baselineSnap) this._baselineSnap = this._snapshotState(phy);
      this._restoreState(phy, this._baselineSnap);

      const startIso = this._isoForFile(new Date());
      const baseName = `sol_phase311_2_basinGuardHoldPack_v1_${startIso}`;

      const summaryHeader = [
        'schema','runId','runIndex','wantId','stabilizer',
        'dreamBlocks','dreamBlockSteps','injectAmount','finalWriteMult',
        'everyMs','durationMs','dt','pressC','baseDamp',
        'lastInjected',
        'startId_t0','startMargin_t0','holdMs_toFlip','switchCount',
        'endId','endMargin','sumAbsFlux_end','meanAbsP_end','rhoSum_end',
        'guardTicks','guardTotalTransfer','guardMaxTransfer',
        'lateAbsAvgMs','lateAbsMaxMs'
      ];
      const summaryLines = [ this._csvRow(summaryHeader) ];

      const traceLines = [];
      let traceHeaderWritten = false;

      const plan = this.cfg.plan || [];
      console.log(`🧪 Phase 3.11.2 Pack: ${plan.length} runs`, plan);

      for (let r = 0; r < plan.length; r++) {
        if (this._stopFlag) break;

        const p = plan[r];
        console.groupCollapsed(`▶ Run ${r+1}/${plan.length} — ${p.stabilizer} — db=${p.dreamBlocks} — fw=${p.finalWriteMult}`);
        const out = await this._runOne({ runIndex: r, plan: p });

        const s = out.summary;
        summaryLines.push(this._csvRow(summaryHeader.map(k => (k in s ? s[k] : ''))));

        const tc = out.traceCsv || '';
        if (!traceHeaderWritten) {
          traceLines.push(tc);
          traceHeaderWritten = true;
        } else {
          const nl = tc.indexOf('\n');
          traceLines.push(nl >= 0 ? tc.slice(nl + 1) : tc);
        }

        console.log('Summary:', s);
        console.groupEnd();
      }

      const endIso = this._isoForFile(new Date());
      const base2 = `${baseName}_${endIso}`;

      this._downloadText(`${base2}_MASTER_summary.csv`, summaryLines.join(''));
      this._downloadText(`${base2}_MASTER_trace.csv`, traceLines.join(''));

      console.log('✅ Phase 3.11.2 Pack complete:', base2);
      this._unfreezeLiveLoop();
      return { baseName: base2, runsPlanned: plan.length, stopped: this._stopFlag };
    }
  };

  window.solPhase311_2 = solPhase311_2;
  console.log(`✅ solPhase311_2 installed (${solPhase311_2.version}). Run: solPhase311_2.runPack()`);

})();
