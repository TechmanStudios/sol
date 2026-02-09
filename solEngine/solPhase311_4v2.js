/* Phase 3.11.4 — Readout Fidelity Sweep v2 (20–30 minute packs)
   Upgrade vs v1:
   - targetMinutes -> auto computes repsPerCombo to hit runtime budget
   - prints estimated runtime before starting
   - otherwise identical semantics (lots of short runs back-to-back)

   UI-neutral ✅
   Baseline restore per run ✅
   Deterministic filenames ✅
   Timing telemetry ✅
*/
(() => {
  'use strict';

  const solPhase311_4v2 = {
    version: '3.11.4_readoutFidelitySweep_v2_budgeted',
    _stopFlag: false,
    stop() { this._stopFlag = true; console.warn('🛑 solPhase311_4v2.stop(): stop flag set.'); },

    cfg: {
      // === PACK BUDGET ===
      // Set this to 20–30 for the kind of run you want.
      targetMinutes: 24,

      // If you explicitly set repsPerCombo (number), it overrides targetMinutes.
      repsPerCombo: null,

      // Dream mode-select (Order B)
      injectorIds: [90, 82],
      dreamBlocks: 15,
      dreamBlockSteps: 2,
      injectAmount: 120,
      dt: 0.12,

      // Awake sampling (short windows → tighter sampling)
      everyMs: 100,
      spinWaitMs: 1.5,

      // Windows
      windowsMs: [1000, 2000, 4000, 8000],

      // Factors (labels we want “readable” from telemetry)
      wantIds: [82, 90],
      finalWriteMults: [1, 2],
      stabilizers: ['none', 'springHold'],

      // SpringHold (v8-ish)
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

      // If null => read from UI sliders at pack start
      baseDamp: null,
      pressC: null,

      filenameBase: 'sol_phase311_4_readoutFidelitySweep_v2',
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
      throw new Error('solPhase311_4v2: timed out waiting for physics.');
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
      if (!app?.config) throw new Error('solPhase311_4v2: App not ready.');
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
      if (!n) throw new Error(`solPhase311_4v2: injector node not found: ${id}`);
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

      counters.absErrSum += Math.abs(err);
      counters.absErrN += 1;

      if (Math.abs(err) <= (law.deadband || 0)) { counters.inBandTicks++; return { f, delta: 0, dir: 'in_deadband' }; }

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

    _regInit() { return { n:0, st:0, st2:0, sy:0, sty:0 }; },
    _regAdd(R, tSec, y) { R.n++; R.st += tSec; R.st2 += tSec*tSec; R.sy += y; R.sty += tSec*y; },
    _regSlope(R) {
      const den = (R.n * R.st2 - R.st * R.st);
      if (!Number.isFinite(den) || Math.abs(den) < 1e-12) return 0;
      const num = (R.n * R.sty - R.st * R.sy);
      const b = num / den;
      return Number.isFinite(b) ? b : 0;
    },

    _computeRepsFromBudget() {
      const c = this.cfg;
      if (Number.isFinite(c.repsPerCombo) && c.repsPerCombo > 0) return Math.floor(c.repsPerCombo);

      const combos = (c.stabilizers.length * c.wantIds.length * c.finalWriteMults.length);
      const windowSecSum = c.windowsMs.reduce((a,b)=>a+b,0) / 1000.0;
      const secondsPerRep = combos * windowSecSum; // metronome dominates wall time

      const targetSec = Math.max(60, (c.targetMinutes || 24) * 60);
      let reps = Math.round(targetSec / secondsPerRep);

      reps = Math.max(1, reps);
      reps = Math.min(30, reps); // sanity cap
      return reps;
    },

    _buildRunList(repsPerCombo) {
      const c = this.cfg;
      const runs = [];
      let idx = 0;

      for (const windowMs of c.windowsMs) {
        for (const stabilizer of c.stabilizers) {
          for (const wantId of c.wantIds) {
            for (const fw of c.finalWriteMults) {
              for (let rep = 1; rep <= repsPerCombo; rep++) {
                runs.push({ runIndex: idx++, repIndex: rep, wantId, finalWriteMult: fw, stabilizer, windowMs });
              }
            }
          }
        }
      }
      return runs;
    },

    async _runOne({ runIndex, repIndex, wantId, finalWriteMult, stabilizer, windowMs, pressC, baseDamp }) {
      const phy = await this._waitForPhysics();
      this._restoreState(phy, this._baselineSnap);

      await this._selectMode(phy, wantId, finalWriteMult, pressC, baseDamp);

      const law = this.cfg.springHold;
      const eps = law.eps ?? 1e-9;

      const t0Pick = this._pick(phy);
      const t0Totals = this._computeTotals(phy);
      const t0Frac = (t0Pick.rho82 - t0Pick.rho90) / (t0Pick.basinMass + eps);

      const ticks = Math.max(1, Math.round(windowMs / this.cfg.everyMs));

      const counters = {
        ctrlTicks: 0, ctrlTotal: 0, ctrlMax: 0, ctrl90to82: 0, ctrl82to90: 0,
        inBandTicks: 0, gateOffTicks: 0,
        absErrSum: 0, absErrN: 0,
        switchCount: 0,
      };

      let basinPrev = t0Pick.basinId;
      let firstFlipAtMs = '';

      let peakFlux = -Infinity;
      let peakFluxAtMs = 0;

      let fracMin = Infinity, fracMax = -Infinity;
      let fracMean = 0, fracM2 = 0, fracN = 0;

      const R_flux = this._regInit();
      const R_basinMass = this._regInit();
      const R_meanAbsP = this._regInit();
      const R_frac = this._regInit();

      const runId =
        `${this._isoForFile()}_r${String(runIndex).padStart(5,'0')}` +
        `_rep${repIndex}` +
        `_w${windowMs}` +
        `_want${wantId}` +
        `_fw${finalWriteMult}` +
        `_stab${stabilizer}`;

      const visStart = document.visibilityState;
      let wasHidden = false;
      const onVis = () => { if (document.hidden) wasHidden = true; };
      document.addEventListener('visibilitychange', onVis, { passive: true });

      const traceRows = [];

      const met = await this._metronomeLoop({
        everyMs: this.cfg.everyMs,
        ticks,
        spinWaitMs: this.cfg.spinWaitMs,
        onTick: async ({ i, tWallMs, lateByMs }) => {
          if (this._stopFlag) return;

          const prePick = this._pick(phy);
          const preTotals = this._computeTotals(phy);
          const preFrac = (prePick.rho82 - prePick.rho90) / (prePick.basinMass + eps);

          let ctrlDelta = 0, ctrlDir = 'none';
          if (stabilizer === 'springHold') {
            const out = this._applySpringHoldPreStep(phy, prePick, law, counters);
            ctrlDelta = out.delta;
            ctrlDir = out.dir;
          }

          phy.step(this.cfg.dt, pressC, baseDamp);

          const postPick = this._pick(phy);
          const postTotals = this._computeTotals(phy);
          const postFrac = (postPick.rho82 - postPick.rho90) / (postPick.basinMass + eps);

          if (postPick.basinId !== basinPrev) {
            counters.switchCount++;
            if (firstFlipAtMs === '' && postPick.basinId !== wantId) firstFlipAtMs = Math.round(tWallMs);
            basinPrev = postPick.basinId;
          }

          if (postTotals.sumAbsFlux > peakFlux) {
            peakFlux = postTotals.sumAbsFlux;
            peakFluxAtMs = Math.round(tWallMs);
          }

          fracN++;
          const d = postFrac - fracMean;
          fracMean += d / fracN;
          fracM2 += d * (postFrac - fracMean);
          fracMin = Math.min(fracMin, postFrac);
          fracMax = Math.max(fracMax, postFrac);

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

        t0_basinId: t0Pick.basinId,
        t0_margin: t0Pick.margin,
        t0_basinMass: t0Pick.basinMass,
        t0_fracDom: t0Frac,
        t0_sumAbsFlux: t0Totals.sumAbsFlux,
        t0_meanAbsP: t0Totals.meanAbsP,

        end_basinId: endPick.basinId,
        end_margin: endPick.margin,
        end_basinMass: endPick.basinMass,
        end_fracDom: endFrac,
        end_sumAbsFlux: endTotals.sumAbsFlux,
        end_meanAbsP: endTotals.meanAbsP,

        firstFlipAtMs,
        switchCount: counters.switchCount,
        peakFlux,
        peakFluxAtMs,

        slope_sumAbsFlux: this._regSlope(R_flux),
        slope_basinMass: this._regSlope(R_basinMass),
        slope_meanAbsP: this._regSlope(R_meanAbsP),
        slope_fracDom: this._regSlope(R_frac),

        fracMin,
        fracMax,
        fracMean,
        fracStd,

        inBandTicks: (stabilizer === 'springHold') ? counters.inBandTicks : '',
        gateOffTicks: (stabilizer === 'springHold') ? counters.gateOffTicks : '',
        absErrMean: (stabilizer === 'springHold' && counters.absErrN > 0) ? (counters.absErrSum / counters.absErrN) : '',
        ctrlTicks: (stabilizer === 'springHold') ? counters.ctrlTicks : '',
        ctrlTotalTransfer: (stabilizer === 'springHold') ? counters.ctrlTotal : '',
        ctrlMaxTransfer: (stabilizer === 'springHold') ? counters.ctrlMax : '',
        ctrl90to82: (stabilizer === 'springHold') ? counters.ctrl90to82 : '',
        ctrl82to90: (stabilizer === 'springHold') ? counters.ctrl82to90 : '',

        visibilityStateStart: visStart,
        wasHidden,
        lateAbsAvgMs: met.lateAbsAvg,
        lateAbsP95Ms: met.lateAbsP95,
        lateAbsMaxMs: met.lateAbsMax,
        missedTicks: met.missedTicks
      };

      return { summary, traceRows };
    },

    async runPack(userCfg = {}) {
      this._stopFlag = false;
      if (userCfg && typeof userCfg === 'object') this.cfg = { ...this.cfg, ...userCfg };

      const app = this._getApp();
      if (!app) throw new Error('solPhase311_4v2: SOLDashboard not found.');

      const phy = await this._waitForPhysics();
      this._freezeLiveLoop();

      if (!this._baselineSnap) this._baselineSnap = this._snapshotState(phy);

      const ui = this._readUiParams(app);
      const pressC = (this.cfg.pressC == null) ? ui.pressC : this.cfg.pressC;
      const baseDamp = (this.cfg.baseDamp == null) ? ui.damp : this.cfg.baseDamp;

      const reps = this._computeRepsFromBudget();
      const combos = (this.cfg.stabilizers.length * this.cfg.wantIds.length * this.cfg.finalWriteMults.length);
      const windowSecSum = this.cfg.windowsMs.reduce((a,b)=>a+b,0) / 1000.0;
      const estSec = reps * combos * windowSecSum;

      const startIso = this._isoForFile(new Date());
      const baseName = `${this.cfg.filenameBase}_${startIso}`;

      console.log(`🧪 Phase 3.11.4 v2 starting`);
      console.log(`Budget: targetMinutes=${this.cfg.targetMinutes} | repsPerCombo=${this.cfg.repsPerCombo ?? '(auto)'} -> reps=${reps}`);
      console.log(`Estimate: combos=${combos}, windowSum=${windowSecSum}s, estRuntime≈${(estSec/60).toFixed(1)} minutes`);
      console.log(`Params: pressC=${pressC}, baseDamp=${baseDamp}, everyMs=${this.cfg.everyMs}, dt=${this.cfg.dt}`);

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

      const traceHeader = [
        'runId','runIndex','repIndex','windowMs','wantId','finalWriteMult','stabilizer',
        'tick','tWallMs','lateByMs',
        'pre_basinId','pre_basinMass','pre_fracDom','pre_sumAbsFlux','pre_meanAbsP',
        'ctrlDelta','ctrlDir',
        'post_basinId','post_basinMass','post_fracDom','post_sumAbsFlux','post_meanAbsP',
        'rhoSum'
      ];
      const traceLines = [ this._csvRow(traceHeader) ];

      const runList = this._buildRunList(reps);
      console.log(`Total short runs: ${runList.length}`);

      try {
        for (let i = 0; i < runList.length; i++) {
          if (this._stopFlag) break;
          const r = runList[i];

          if (i % 25 === 0) {
            console.log(`Progress: ${i}/${runList.length} (hidden=${document.hidden})`);
          }

          const out = await this._runOne({ ...r, pressC, baseDamp });

          const s = out.summary;
          summaryLines.push(this._csvRow(summaryHeader.map(k => (k in s ? s[k] : ''))));

          for (const row of out.traceRows) traceLines.push(row);
        }
      } finally {
        this._unfreezeLiveLoop();
      }

      const endIso = this._isoForFile(new Date());
      const base2 = `${baseName}_${endIso}`;

      this._downloadText(`${base2}_MASTER_summary.csv`, summaryLines.join(''));
      this._downloadText(`${base2}_MASTER_trace.csv`, traceLines.join(''));

      console.log('✅ Phase 3.11.4 v2 complete:', base2);
      return { baseName: base2, runsPlanned: runList.length, repsPerCombo: reps, stopped: this._stopFlag };
    }
  };

  window.solPhase311_4v2 = solPhase311_4v2;
  console.log(`✅ solPhase311_4v2 installed (${solPhase311_4v2.version}). Run: solPhase311_4v2.runPack()`);

})();
