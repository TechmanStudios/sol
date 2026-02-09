/* Phase 3.11.2b — BasinGuardHold Pack v3 (Fraction-Band, mass-conserving)
   Fixes v1 pathology: absolute-margin guard drained rho90 to ~0.
   New law: hold fractional dominance f=(rho82-rho90)/(rho82+rho90) in a band.

   UI-neutral ✅
   Baseline restore per run ✅
   t0 sampled immediately ✅
   Deterministic filenames ✅
   Timing telemetry ✅
*/
(() => {
  'use strict';

  const solPhase311_2b = {
    version: '3.11.2b_basinGuardHoldPack_v3_fracBand',
    _stopFlag: false,
    stop() { this._stopFlag = true; console.warn('🛑 solPhase311_2b.stop(): stop flag set.'); },

    cfg: {
      injectorIds: [90, 82],  // Order B
      wantId: 82,

      // Pack plan (6 runs): baseline + two gains for fw1 and fw2
      plan: [
        { dreamBlocks: 15, finalWriteMult: 1.0, stabilizer: 'none' },
        { dreamBlocks: 15, finalWriteMult: 1.0, stabilizer: 'fracBandHold', gain: 0.35 },
        { dreamBlocks: 15, finalWriteMult: 1.0, stabilizer: 'fracBandHold', gain: 0.55 },

        { dreamBlocks: 15, finalWriteMult: 2.0, stabilizer: 'none' },
        { dreamBlocks: 15, finalWriteMult: 2.0, stabilizer: 'fracBandHold', gain: 0.35 },
        { dreamBlocks: 15, finalWriteMult: 2.0, stabilizer: 'fracBandHold', gain: 0.55 },
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

      // Fraction-band guard settings
      fracBandHold: {
        fLow: 0.06,          // keep 82 at least ~6% ahead (scaled)
        fHigh: 0.22,         // but don’t let 82 “hog” everything (prevents rho90→0)
        deadband: 0.008,     // small quiet zone near boundaries to reduce chatter

        // Control only while basin still has energy
        massGate: 30.0,      // if rho82+rho90 < massGate, stop controlling

        // Maximum mass transfer per tick
        maxDelta: 10.0,      // clamp for safety

        // Numerical stability
        eps: 1e-9,
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
      throw new Error('solPhase311_2b: timed out waiting for physics.');
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
      if (!app?.config) throw new Error('solPhase311_2b: App not ready.');
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
      if (!n) throw new Error(`solPhase311_2b: injector node not found: ${id}`);
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
      const basinMass = a.rho + b.rho;
      const fracDom = (a.rho - b.rho) / (basinMass + 1e-9); // overwritten with cfg.eps in guard
      return {
        basinId, margin,
        rho82: a.rho, rho90: b.rho,
        p82: a.p, p90: b.p,
        basinMass, fracDom
      };
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

    _applyFracBandHold(phy, pick, guardCfg, gain, counters) {
      const eps = guardCfg.eps ?? 1e-9;
      const basinMass = pick.rho82 + pick.rho90;
      const f = (pick.rho82 - pick.rho90) / (basinMass + eps);

      // gate off when system is cold (prevents late-phase “drain to zero” behavior)
      if (basinMass < guardCfg.massGate) return { f, delta: 0, dir: 'off_cold' };

      const fLow = guardCfg.fLow;
      const fHigh = guardCfg.fHigh;
      const db = guardCfg.deadband || 0;

      // Mass transfer required to change f by df:
      // f' = (a-b+2x)/T => df = 2x/T => x = 0.5*T*df
      let dir = 'none';
      let df = 0;

      if (f < (fLow - db)) { dir = '90to82'; df = (fLow - f); }
      else if (f > (fHigh + db)) { dir = '82to90'; df = (f - fHigh); }
      else return { f, delta: 0, dir: 'in_band' };

      let delta = gain * 0.5 * basinMass * df;
      if (!Number.isFinite(delta) || delta <= 0) return { f, delta: 0, dir: 'nan' };
      delta = Math.min(guardCfg.maxDelta || 0, delta);

      const n82 = this._nodeByIdLoose(phy, 82);
      const n90 = this._nodeByIdLoose(phy, 90);
      if (!n82 || !n90) return { f, delta: 0, dir: 'missing_nodes' };

      if (dir === '90to82') {
        const take = Math.min(delta, Math.max(0, n90.rho));
        if (take <= 0) return { f, delta: 0, dir: 'dry_90' };
        n90.rho -= take;
        n82.rho += take;
        counters.guardTicks++;
        counters.guardTotal += take;
        counters.guardMax = Math.max(counters.guardMax, take);
        counters.guard90to82 += take;
        return { f, delta: take, dir };
      } else {
        const take = Math.min(delta, Math.max(0, n82.rho));
        if (take <= 0) return { f, delta: 0, dir: 'dry_82' };
        n82.rho -= take;
        n90.rho += take;
        counters.guardTicks++;
        counters.guardTotal += take;
        counters.guardMax = Math.max(counters.guardMax, take);
        counters.guard82to90 += take;
        return { f, delta: take, dir };
      }
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

      const gain = Number.isFinite(plan.gain) ? plan.gain : 0.35;

      const runId =
        `${this._isoForFile()}_run${String(runIndex).padStart(2,'0')}` +
        `_${plan.stabilizer}_db${plan.dreamBlocks}_fw${plan.finalWriteMult}` +
        (plan.stabilizer === 'fracBandHold' ? `_g${gain}` : '');

      const log = { runId, runIndex, wantId: runCfg.wantId, ...plan, lastInjected: null };

      await this._selectMode(phy, runCfg.wantId, runCfg, log);

      const t0Pick = this._pick(phy);
      const t0Totals = this._computeTotals(phy);

      const counters = {
        guardTicks: 0, guardTotal: 0, guardMax: 0,
        guard90to82: 0, guard82to90: 0
      };

      let minFrac = Infinity, minFracAtMs = 0;
      let maxFrac = -Infinity, maxFracAtMs = 0;
      let rho90_firstBelow1_s = '';
      let rho90_firstZero_s = '';

      const ticks = Math.max(1, Math.round(runCfg.durationMs / runCfg.everyMs));
      const trace = [];
      trace.push(this._csvRow([
        'runId','runIndex','wantId','stabilizer','dreamBlocks','finalWriteMult','gain',
        'tick','tWallMs','lateByMs',
        'basinId','margin',
        'rho82','rho90','basinMass','fracDom',
        'sumAbsFlux','meanAbsP','rhoSum',
        'guardDelta','guardDir'
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

          phy.step(runCfg.dt, runCfg.pressC, runCfg.baseDamp);

          let pick = this._pick(phy);
          let guardDelta = 0;
          let guardDir = 'none';

          // fractional dominance with proper eps
          const eps = runCfg.fracBandHold.eps ?? 1e-9;
          const basinMass = pick.rho82 + pick.rho90;
          let fracDom = (pick.rho82 - pick.rho90) / (basinMass + eps);

          if (plan.stabilizer === 'fracBandHold') {
            const out = this._applyFracBandHold(phy, pick, runCfg.fracBandHold, gain, counters);
            guardDelta = out.delta;
            guardDir = out.dir;

            // refresh after control
            pick = this._pick(phy);
            const basinMass2 = pick.rho82 + pick.rho90;
            fracDom = (pick.rho82 - pick.rho90) / (basinMass2 + eps);
          }

          if (fracDom < minFrac) { minFrac = fracDom; minFracAtMs = Math.round(tWallMs); }
          if (fracDom > maxFrac) { maxFrac = fracDom; maxFracAtMs = Math.round(tWallMs); }

          // when rho90 hits “almost gone”
          if (rho90_firstBelow1_s === '' && pick.rho90 <= 1.0) rho90_firstBelow1_s = (tWallMs/1000).toFixed(3);
          if (rho90_firstZero_s === '' && pick.rho90 <= 1e-6) rho90_firstZero_s = (tWallMs/1000).toFixed(3);

          const totals = this._computeTotals(phy);

          if (pick.basinId !== basinPrev) { switchCount++; basinPrev = pick.basinId; }
          if (flipAtMs == null && pick.basinId !== runCfg.wantId) flipAtMs = Math.round(tWallMs);

          trace.push(this._csvRow([
            runId, runIndex, runCfg.wantId, plan.stabilizer, plan.dreamBlocks, plan.finalWriteMult, (plan.stabilizer==='fracBandHold'?gain:''),
            i, tWallMs.toFixed(3), lateByMs.toFixed(3),
            pick.basinId, pick.margin.toFixed(6),
            pick.rho82.toFixed(6), pick.rho90.toFixed(6), (pick.rho82+pick.rho90).toFixed(6), fracDom.toFixed(6),
            totals.sumAbsFlux.toFixed(6), totals.meanAbsP.toFixed(6), totals.rhoSum.toFixed(6),
            guardDelta.toFixed(6), guardDir
          ]));
        }
      });

      const endPick = this._pick(phy);
      const endTotals = this._computeTotals(phy);

      const eps = runCfg.fracBandHold.eps ?? 1e-9;
      const endBasinMass = endPick.rho82 + endPick.rho90;
      const endFracDom = (endPick.rho82 - endPick.rho90) / (endBasinMass + eps);

      const summary = {
        schema: this.version,
        runId,
        runIndex,
        wantId: runCfg.wantId,
        stabilizer: plan.stabilizer,
        gain: (plan.stabilizer === 'fracBandHold') ? gain : '',

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

        endFracDom,
        minFracDom: minFrac,
        minFracAtMs,
        maxFracDom: maxFrac,
        maxFracAtMs,

        rho90_firstBelow1_s,
        rho90_firstZero_s,

        sumAbsFlux_end: endTotals.sumAbsFlux,
        meanAbsP_end: endTotals.meanAbsP,
        rhoSum_end: endTotals.rhoSum,

        guardTicks: counters.guardTicks,
        guardTotalTransfer: counters.guardTotal,
        guardMaxTransfer: counters.guardMax,
        guard90to82: counters.guard90to82,
        guard82to90: counters.guard82to90,

        lateAbsAvgMs: met.lateAbsAvg,
        lateAbsMaxMs: met.lateAbsMax,
      };

      return { summary, traceCsv: trace.join('') };
    },

    async runPack(userCfg = {}) {
      this._stopFlag = false;
      if (userCfg && typeof userCfg === 'object') this.cfg = { ...this.cfg, ...userCfg };

      const app = this._getApp();
      if (!app) throw new Error('solPhase311_2b: SOLDashboard not found.');

      const phy = await this._waitForPhysics();
      this._freezeLiveLoop();

      if (!this._baselineSnap) this._baselineSnap = this._snapshotState(phy);
      this._restoreState(phy, this._baselineSnap);

      const startIso = this._isoForFile(new Date());
      const baseName = `sol_phase311_2b_basinGuardHoldPack_v3_${startIso}`;

      const summaryHeader = [
        'schema','runId','runIndex','wantId','stabilizer','gain',
        'dreamBlocks','dreamBlockSteps','injectAmount','finalWriteMult',
        'everyMs','durationMs','dt','pressC','baseDamp',
        'lastInjected',
        'startId_t0','startMargin_t0','holdMs_toFlip','switchCount',
        'endId','endMargin',
        'endFracDom','minFracDom','minFracAtMs','maxFracDom','maxFracAtMs',
        'rho90_firstBelow1_s','rho90_firstZero_s',
        'sumAbsFlux_end','meanAbsP_end','rhoSum_end',
        'guardTicks','guardTotalTransfer','guardMaxTransfer','guard90to82','guard82to90',
        'lateAbsAvgMs','lateAbsMaxMs'
      ];
      const summaryLines = [ this._csvRow(summaryHeader) ];

      const traceLines = [];
      let traceHeaderWritten = false;

      const plan = this.cfg.plan || [];
      console.log(`🧪 Phase 3.11.2b Pack v3: ${plan.length} runs`, plan);
      console.log('FracBand params:', this.cfg.fracBandHold);

      for (let r = 0; r < plan.length; r++) {
        if (this._stopFlag) break;

        const p = plan[r];
        console.groupCollapsed(
          `▶ Run ${r+1}/${plan.length} — ${p.stabilizer} — db=${p.dreamBlocks} — fw=${p.finalWriteMult}` +
          (p.stabilizer === 'fracBandHold' ? ` — gain=${p.gain}` : '')
        );

        const out = await this._runOne({ runIndex: r, plan: p });

        const s = out.summary;
        summaryLines.push(this._csvRow(summaryHeader.map(k => (k in s ? s[k] : ''))));

        const tc = out.traceCsv || '';
        if (!traceHeaderWritten) { traceLines.push(tc); traceHeaderWritten = true; }
        else {
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

      console.log('✅ Phase 3.11.2b Pack v3 complete:', base2);
      this._unfreezeLiveLoop();
      return { baseName: base2, runsPlanned: plan.length, stopped: this._stopFlag };
    }
  };

  window.solPhase311_2b = solPhase311_2b;
  console.log(`✅ solPhase311_2b installed (${solPhase311_2b.version}). Run: solPhase311_2b.runPack()`);

})();
