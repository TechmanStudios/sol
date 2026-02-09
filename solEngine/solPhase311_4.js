/* Phase 3.11.4 — Readout Fidelity Sweep v1
   Many short windows, back-to-back, big-data outputs.

   Measures: how well early-time telemetry encodes the input condition.
   Conditions vary:
     - wantId (mode select via lastInjected): 82 vs 90
     - finalWriteMult: 1 vs 2
     - stabilizer: none vs springHold (optional "coherence keeper")
     - windowMs: 1000, 2000, 4000, 8000

   Outputs:
     - MASTER_summary.csv : one row per short run, with features (slopes, peaks, stats)
     - MASTER_trace.csv   : per-tick telemetry for all runs (big but manageable)

   UI-neutral ✅
   Baseline restore per run ✅
   Deterministic filenames ✅
   Timing telemetry ✅
*/

(() => {
  'use strict';

  const solPhase311_4 = {
    version: '3.11.4_readoutFidelitySweep_v1',
    _stopFlag: false,
    stop() { this._stopFlag = true; console.warn('🛑 solPhase311_4.stop(): stop flag set.'); },

    cfg: {
      // Dream mode-select (Order B is stable)
      injectorIds: [90, 82],
      dreamBlocks: 15,
      dreamBlockSteps: 2,
      injectAmount: 120,
      dt: 0.12,

      // Awake sampling cadence (short windows -> tighter sampling)
      everyMs: 100,
      spinWaitMs: 1.5,

      // Windows and replicates
      windowsMs: [1000, 2000, 4000, 8000],
      repsPerCombo: 3,

      // Factors (classes we want to be able to read out)
      wantIds: [82, 90],
      finalWriteMults: [1, 2],

      // Run both to compare: raw transient vs coherence-kept transient
      stabilizers: ['none', 'springHold'],

      // springHold = v8-ish: pre-step equilibrium keeper, mass-conserving 82<->90 transfer only
      springHold: {
        fTarget: 0.015,
        deadband: 0.006,
        k: 0.75,
        kSafety: 2.0,
        fSafetyMin: -0.005,
        massGate: 3.0,
        maxDelta: 6.0,
        eps: 1e-9,
      },

      // If null => read from UI sliders each pack start
      baseDamp: null,
      pressC: null,

      // Filename base
      filenameBase: 'sol_phase311_4_readoutFidelitySweep_v1',
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
      throw new Error('solPhase311_4: timed out waiting for physics.');
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
      if (!app?.config) throw new Error('solPhase311_4: App not ready.');
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
      if (!n) throw new Error(`solPhase311_4: injector node not found: ${id}`);
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
      return { basinId, margin, rho82: a.rho, rho90: b.rho, p82: a.p, p90: b.p, basinMass };
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

    // drift-compensated metronome
    async _metronomeLoop({ everyMs, ticks, spinWaitMs, onTick }) {
      const start = performance.now();
      const absLates = [];
      let missedTicks = 0;

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
        const absLate = Math.abs(lateByMs);
        absLates.push(absLate);
        if (absLate > everyMs) missedTicks++;

        await onTick({ i, tWallMs: now2 - start, lateByMs });
      }

      absLates.sort((a,b)=>a-b);
      const n = Math.max(1, absLates.length);
      const p95 = absLates[Math.floor(0.95 * (n - 1))] ?? 0;
      const avg = absLates.reduce((a,b)=>a+b,0) / n;
      const max = absLates[n - 1] ?? 0;

      return { lateAbsAvg: avg, lateAbsP95: p95, lateAbsMax: max, missedTicks };
    },

    // mode select via lastInjected
    async _selectMode(phy, wantId, finalWriteMult, pressC, baseDamp) {
      const c = this.cfg;
      let injIndex = 0;

      for (let b = 0; b < Math.max(0, c.dreamBlocks - 1); b++) {
        const injId = c.injectorIds[injIndex % c.injectorIds.length];
        injIndex++;
        this._injectById(phy, injId, c.injectAmount);
        for (let s = 0; s < c.dreamBlockSteps; s++) {
          if (this._stopFlag) return;
          phy.step(c.dt, pressC, baseDamp);
        }
      }

      this._injectById(phy, wantId, c.injectAmount * (finalWriteMult || 1));
      try { if (typeof phy.computePressure === 'function') phy.computePressure(pressC); } catch(e) {}
    },

    _applySpringHoldPreStep(phy, pick, law, counters) {
      const eps = law.eps ?? 1e-9;
      const basinMass = pick.rho82 + pick.rho90;
      const f = (pick.rho82 - pick.rho90) / (basinMass + eps);

      if (basinMass < law.massGate) { counters.gateOffTicks++; return { f, delta: 0, dir: 'off_cold' }; }

      const n82 = this._nodeByIdLoose(phy, 82);
      const n90 = this._nodeByIdLoose(phy, 90);
      if (!n82 || !n90) return { f, delta: 0, dir: 'missing_nodes' };

      const k = (f < law.fSafetyMin) ? law.kSafety : law.k;
      const err = (law.fTarget - f);

      // error tracking (readout feature)
      counters.absErrSum += Math.abs(err);
      counters.absErrN += 1;

      if (Math.abs(err) <= (law.deadband || 0)) { counters.inBandTicks++; return { f, delta: 0, dir: 'in_deadband' }; }

      // fraction error -> mass transfer x = 0.5*T*df
      let delta = k * 0.5 * basinMass * err;

      if (!Number.isFinite(delta)) return { f, delta: 0, dir: 'nan' };
      const maxD = law.maxDelta || 0;
      if (delta >  maxD) delta =  maxD;
      if (delta < -maxD) delta = -maxD;

      if (Math.abs(delta) < 1e-12) return { f, delta: 0, dir: 'tiny' };

      if (delta > 0) {
        const take = Math.min(delta, Math.max(0, n90.rho));
        if (take <= 0) return { f, delta: 0, dir: 'dry_90' };
        n90.rho -= take; n82.rho += take;
        counters.ctrlTicks++; counters.ctrlTotal += take; counters.ctrlMax = Math.max(counters.ctrlMax, take);
        counters.ctrl90to82 += take;
        return { f, delta: take, dir: '90to82' };
      } else {
        const want = -delta;
        const take = Math.min(want, Math.max(0, n82.rho));
        if (take <= 0) return { f, delta: 0, dir: 'dry_82' };
        n82.rho -= take; n90.rho += take;
        counters.ctrlTicks++; counters.ctrlTotal += take; counters.ctrlMax = Math.max(counters.ctrlMax, take);
        counters.ctrl82to90 += take;
        return { f, delta: take, dir: '82to90' };
      }
    },

    // online regression stats for slope: y ~ a + b*t
    _regInit() { return { n:0, st:0, st2:0, sy:0, sty:0, y0:null, yEnd:null, tEnd:0 }; },
    _regAdd(R, tSec, y) {
      R.n++; R.st += tSec; R.st2 += tSec*tSec; R.sy += y; R.sty += tSec*y;
      if (R.y0 === null) R.y0 = y;
      R.yEnd = y;
      R.tEnd = tSec;
    },
    _regSlope(R) {
      // b = (n*Σ(t*y) - Σt*Σy) / (n*Σ(t^2) - (Σt)^2)
      const den = (R.n * R.st2 - R.st * R.st);
      if (!Number.isFinite(den) || Math.abs(den) < 1e-12) return 0;
      const num = (R.n * R.sty - R.st * R.sy);
      const b = num / den;
      return Number.isFinite(b) ? b : 0;
    },

    async _runOne({ runIndex, repIndex, wantId, finalWriteMult, stabilizer, windowMs, pressC, baseDamp }) {
      const phy = await this._waitForPhysics();

      // restore baseline
      this._restoreState(phy, this._baselineSnap);

      // dream select
      await this._selectMode(phy, wantId, finalWriteMult, pressC, baseDamp);

      const law = this.cfg.springHold;
      const eps = law.eps ?? 1e-9;

      // TRUE t0 snapshot
      const t0Pick = this._pick(phy);
      const t0Totals = this._computeTotals(phy);
      const t0Frac = (t0Pick.rho82 - t0Pick.rho90) / (t0Pick.basinMass + eps);

      const ticks = Math.max(1, Math.round(windowMs / this.cfg.everyMs));

      // per-run counters/features
      const counters = {
        ctrlTicks: 0, ctrlTotal: 0, ctrlMax: 0, ctrl90to82: 0, ctrl82to90: 0,
        inBandTicks: 0, gateOffTicks: 0,
        absErrSum: 0, absErrN: 0,
        switchCount: 0,
      };

      // track basin switches quickly
      let basinPrev = t0Pick.basinId;
      let firstFlipAtMs = '';

      // peak tracking
      let peakFlux = -Infinity;
      let peakFluxAtMs = 0;

      // frac stats
      let fracMin = Infinity, fracMax = -Infinity;
      let fracMean = 0, fracM2 = 0, fracN = 0;

      // regression stats
      const R_flux = this._regInit();
      const R_basinMass = this._regInit();
      const R_meanAbsP = this._regInit();
      const R_frac = this._regInit();

      const runId =
        `${this._isoForFile()}_r${String(runIndex).padStart(4,'0')}` +
        `_rep${repIndex}` +
        `_w${windowMs}` +
        `_want${wantId}` +
        `_fw${finalWriteMult}` +
        `_stab${stabilizer}`;

      // visibility telemetry
      const visStart = document.visibilityState;
      let wasHidden = false;
      const onVis = () => { if (document.hidden) wasHidden = true; };
      document.addEventListener('visibilitychange', onVis, { passive: true });

      // trace rows for this run
      const traceRows = [];

      const met = await this._metronomeLoop({
        everyMs: this.cfg.everyMs,
        ticks,
        spinWaitMs: this.cfg.spinWaitMs,
        onTick: async ({ i, tWallMs, lateByMs }) => {
          if (this._stopFlag) return;

          // PRE-step pick + totals (this is the "readout surface")
          const prePick = this._pick(phy);
          const preTotals = this._computeTotals(phy);
          const preFrac = (prePick.rho82 - prePick.rho90) / (prePick.basinMass + eps);

          // SpringHold is optional (coherence keeper)
          let ctrlDelta = 0, ctrlDir = 'none';
          if (stabilizer === 'springHold') {
            const out = this._applySpringHoldPreStep(phy, prePick, law, counters);
            ctrlDelta = out.delta;
            ctrlDir = out.dir;
          }

          // Integrate one step
          phy.step(this.cfg.dt, pressC, baseDamp);

          // POST-step measures (system response)
          const postPick = this._pick(phy);
          const postTotals = this._computeTotals(phy);
          const postFrac = (postPick.rho82 - postPick.rho90) / (postPick.basinMass + eps);

          // switch tracking (post)
          if (postPick.basinId !== basinPrev) {
            counters.switchCount++;
            if (firstFlipAtMs === '' && postPick.basinId !== wantId) firstFlipAtMs = Math.round(tWallMs);
            basinPrev = postPick.basinId;
          }

          // peak flux (post)
          if (postTotals.sumAbsFlux > peakFlux) {
            peakFlux = postTotals.sumAbsFlux;
            peakFluxAtMs = Math.round(tWallMs);
          }

          // frac stats (post)
          fracN++;
          const d = postFrac - fracMean;
          fracMean += d / fracN;
          fracM2 += d * (postFrac - fracMean);
          fracMin = Math.min(fracMin, postFrac);
          fracMax = Math.max(fracMax, postFrac);

          // regression stats vs t (post)
          const tSec = tWallMs / 1000.0;
          this._regAdd(R_flux, tSec, postTotals.sumAbsFlux);
          this._regAdd(R_basinMass, tSec, postPick.basinMass);
          this._regAdd(R_meanAbsP, tSec, postTotals.meanAbsP);
          this._regAdd(R_frac, tSec, postFrac);

          traceRows.push(this._csvRow([
            runId, runIndex, repIndex, windowMs, wantId, finalWriteMult, stabilizer,
            i, tWallMs.toFixed(3), lateByMs.toFixed(3),
            prePick.basinId, prePick.basinMass.toFixed(6), preFrac.toFixed(6), preTotals.sumAbsFlux.toFixed(6), preTotals.meanAbsP.toFixed(6),
            ctrlDelta.toFixed(6), ctrlDir,
            postPick.basinId, postPick.basinMass.toFixed(6), postFrac.toFixed(6), postTotals.sumAbsFlux.toFixed(6), postTotals.meanAbsP.toFixed(6),
            postTotals.rhoSum.toFixed(6)
          ]));
        }
      });

      document.removeEventListener('visibilitychange', onVis);

      // end snapshot
      const endPick = this._pick(phy);
      const endTotals = this._computeTotals(phy);
      const endFrac = (endPick.rho82 - endPick.rho90) / (endPick.basinMass + eps);

      const fracVar = (fracN > 1) ? (fracM2 / (fracN - 1)) : 0;
      const fracStd = Math.sqrt(Math.max(0, fracVar));

      const summary = {
        schema: this.version,
        runId,
        runIndex,
        repIndex,
        windowMs,
        wantId,
        finalWriteMult,
        stabilizer,

        dt: this.cfg.dt,
        everyMs: this.cfg.everyMs,
        pressC,
        baseDamp,

        // t0 truth
        t0_basinId: t0Pick.basinId,
        t0_margin: t0Pick.margin,
        t0_basinMass: t0Pick.basinMass,
        t0_fracDom: t0Frac,
        t0_sumAbsFlux: t0Totals.sumAbsFlux,
        t0_meanAbsP: t0Totals.meanAbsP,

        // end
        end_basinId: endPick.basinId,
        end_margin: endPick.margin,
        end_basinMass: endPick.basinMass,
        end_fracDom: endFrac,
        end_sumAbsFlux: endTotals.sumAbsFlux,
        end_meanAbsP: endTotals.meanAbsP,

        // primary readout features (window)
        firstFlipAtMs,
        switchCount: counters.switchCount,
        peakFlux,
        peakFluxAtMs,

        // slopes (per second)
        slope_sumAbsFlux: this._regSlope(R_flux),
        slope_basinMass: this._regSlope(R_basinMass),
        slope_meanAbsP: this._regSlope(R_meanAbsP),
        slope_fracDom: this._regSlope(R_frac),

        // frac distribution
        fracMin,
        fracMax,
        fracMean,
        fracStd,

        // stabilizer telemetry (if enabled)
        inBandTicks: (stabilizer === 'springHold') ? counters.inBandTicks : '',
        gateOffTicks: (stabilizer === 'springHold') ? counters.gateOffTicks : '',
        absErrMean: (stabilizer === 'springHold' && counters.absErrN > 0) ? (counters.absErrSum / counters.absErrN) : '',
        ctrlTicks: (stabilizer === 'springHold') ? counters.ctrlTicks : '',
        ctrlTotalTransfer: (stabilizer === 'springHold') ? counters.ctrlTotal : '',
        ctrlMaxTransfer: (stabilizer === 'springHold') ? counters.ctrlMax : '',
        ctrl90to82: (stabilizer === 'springHold') ? counters.ctrl90to82 : '',
        ctrl82to90: (stabilizer === 'springHold') ? counters.ctrl82to90 : '',

        // timing + visibility
        visibilityStateStart: visStart,
        wasHidden,
        lateAbsAvgMs: met.lateAbsAvg,
        lateAbsP95Ms: met.lateAbsP95,
        lateAbsMaxMs: met.lateAbsMax,
        missedTicks: met.missedTicks
      };

      return { summary, traceRows };
    },

    _buildRunList() {
      const c = this.cfg;
      const runs = [];
      let idx = 0;

      // Order: group by window -> stabilizer -> condition -> reps (easy to compare)
      for (const windowMs of c.windowsMs) {
        for (const stabilizer of c.stabilizers) {
          for (const wantId of c.wantIds) {
            for (const fw of c.finalWriteMults) {
              for (let rep = 1; rep <= c.repsPerCombo; rep++) {
                runs.push({ runIndex: idx++, repIndex: rep, wantId, finalWriteMult: fw, stabilizer, windowMs });
              }
            }
          }
        }
      }
      return runs;
    },

    async runPack(userCfg = {}) {
      this._stopFlag = false;
      if (userCfg && typeof userCfg === 'object') this.cfg = { ...this.cfg, ...userCfg };

      const app = this._getApp();
      if (!app) throw new Error('solPhase311_4: SOLDashboard not found.');

      const phy = await this._waitForPhysics();
      this._freezeLiveLoop();

      // snapshot baseline once
      if (!this._baselineSnap) this._baselineSnap = this._snapshotState(phy);

      // fixed params for pack (stable comparability)
      const ui = this._readUiParams(app);
      const pressC = (this.cfg.pressC == null) ? ui.pressC : this.cfg.pressC;
      const baseDamp = (this.cfg.baseDamp == null) ? ui.damp : this.cfg.baseDamp;

      const startIso = this._isoForFile(new Date());
      const baseName = `${this.cfg.filenameBase}_${startIso}`;

      // summary header
      const summaryHeader = [
        'schema','runId','runIndex','repIndex','windowMs','wantId','finalWriteMult','stabilizer',
        'dt','everyMs','pressC','baseDamp',
        't0_basinId','t0_margin','t0_basinMass','t0_fracDom','t0_sumAbsFlux','t0_meanAbsP',
        'end_basinId','end_margin','end_basinMass','end_fracDom','end_sumAbsFlux','end_meanAbsP',
        'firstFlipAtMs','switchCount','peakFlux','peakFluxAtMs',
        'slope_sumAbsFlux','slope_basinMass','slope_meanAbsP','slope_fracDom',
        'fracMin','fracMax','fracMean','fracStd',
        'inBandTicks','gateOffTicks','absErrMean','ctrlTicks','ctrlTotalTransfer','ctrlMaxTransfer','ctrl90to82','ctrl82to90',
        'visibilityStateStart','wasHidden',
        'lateAbsAvgMs','lateAbsP95Ms','lateAbsMaxMs','missedTicks'
      ];
      const summaryLines = [ this._csvRow(summaryHeader) ];

      // trace header (once)
      const traceHeader = [
        'runId','runIndex','repIndex','windowMs','wantId','finalWriteMult','stabilizer',
        'tick','tWallMs','lateByMs',
        'pre_basinId','pre_basinMass','pre_fracDom','pre_sumAbsFlux','pre_meanAbsP',
        'ctrlDelta','ctrlDir',
        'post_basinId','post_basinMass','post_fracDom','post_sumAbsFlux','post_meanAbsP',
        'rhoSum'
      ];
      const traceLines = [ this._csvRow(traceHeader) ];

      const runList = this._buildRunList();
      console.log(`🧪 Phase 3.11.4 Readout Sweep: ${runList.length} short runs`);
      console.log('Pack params:', { pressC, baseDamp, everyMs: this.cfg.everyMs, windowsMs: this.cfg.windowsMs, reps: this.cfg.repsPerCombo });
      console.log('Runs grouped by window -> stabilizer -> wantId -> fw -> reps');

      try {
        for (let i = 0; i < runList.length; i++) {
          if (this._stopFlag) break;
          const r = runList[i];

          if (i % 10 === 0) {
            console.log(`Progress: ${i}/${runList.length} (hidden=${document.hidden})`);
          }

          const out = await this._runOne({ ...r, pressC, baseDamp });

          // summary row
          const s = out.summary;
          summaryLines.push(this._csvRow(summaryHeader.map(k => (k in s ? s[k] : ''))));

          // trace rows
          for (const row of out.traceRows) traceLines.push(row);
        }
      } finally {
        this._unfreezeLiveLoop();
      }

      const endIso = this._isoForFile(new Date());
      const base2 = `${baseName}_${endIso}`;

      this._downloadText(`${base2}_MASTER_summary.csv`, summaryLines.join(''));
      this._downloadText(`${base2}_MASTER_trace.csv`, traceLines.join(''));

      console.log('✅ Phase 3.11.4 Readout Sweep complete:', base2);
      return { baseName: base2, runsPlanned: runList.length, stopped: this._stopFlag };
    }
  };

  window.solPhase311_4 = solPhase311_4;
  console.log(`✅ solPhase311_4 installed (${solPhase311_4.version}). Run: solPhase311_4.runPack()`);

})();
