/* Phase 3.11.5 — TemporalCode Readout Pack v1 (Budgeted 20–30 min)
   - Many short runs back-to-back
   - Temporal message codes with equal total mass (per-basin totals equal)
   - Post-message features (decode from response, not from injection itself)
   - BasinHold stabilizer targets selected basin (sign flips with wantId)
   - Default cadence: 200ms (better timing fidelity than 100ms)

   Run:
     solPhase311_5.runPack()

   Stop early:
     solPhase311_5.stop()
*/
(() => {
  'use strict';

  const solPhase311_5 = {
    version: '3.11.5_temporalCodeReadoutPack_v1',
    _stopFlag: false,
    stop() { this._stopFlag = true; console.warn('🛑 solPhase311_5.stop(): stop flag set.'); },

    cfg: {
      // === PACK BUDGET ===
      // Set 20–30. With the default combos, 24 will land ~30min (ceil reps).
      targetMinutes: 24,
      repsPerCombo: null, // set a number to override budget logic

      // Dream mode-select (Order B)
      injectorIds: [90, 82],
      dreamBlocks: 15,
      dreamBlockSteps: 2,
      injectAmount: 120,
      finalWriteMult: 1, // keep fixed so codes are not amplitude-trivial
      dt: 0.12,

      // Sampling cadence (200ms is much more “honest” for timing + CPU)
      everyMs: 200,
      spinWaitMs: 1.5,

      // Windows (include a longer one to observe coherence window + flip dynamics)
      windowsMs: [2000, 4000, 8000, 16000],

      // Targets (we’ll test both basins, because 90 is a sink and we want symmetry)
      wantIds: [82, 90],

      // Stabilizers:
      // - none: natural dynamics
      // - basinHold: gentle mass-conserving transfer that holds the selected basin AFTER message ends
      stabilizers: ['none', 'basinHold'],

      // BasinHold law (mass-conserving between 82/90 only)
      basinHold: {
        absFTarget: 0.015,     // desired |fracDom| (sign determined by wantId)
        deadband: 0.006,
        k: 0.75,
        kSafety: 2.0,
        fSafetyMinSigned: -0.005, // safety region threshold (in signed coords)
        massGate: 3.0,
        maxDelta: 6.0,
        eps: 1e-9,
        engageAfterMs: 800,    // IMPORTANT: don’t fight the message; hold begins after message window
      },

      // Temporal message coding (equal totals to each basin)
      message: {
        // 4 “message ticks” at t = 0, 200, 400, 600ms (given everyMs=200)
        msgTicks: [0,1,2,3],
        // Total per basin over message = 20 (so total message mass = 40)
        pulseWant: 10,
        pulseOther: 10,
        pulseBoth: 5,          // for IN_PHASE (both each tick): 5*4 = 20 per basin
      },

      messageCodes: ['ALT_WANT', 'ALT_OTHER', 'IN_PHASE', 'BURST_EARLY', 'BURST_LATE'],

      // If null => read from UI sliders at pack start
      baseDamp: null,
      pressC: null,

      filenameBase: 'sol_phase311_5_temporalCodeReadoutPack_v1',
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
      throw new Error('solPhase311_5: timed out waiting for physics.');
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
      if (!app?.config) throw new Error('solPhase311_5: App not ready.');
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
      if (!n) throw new Error(`solPhase311_5: injector node not found: ${id}`);
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

    async _selectMode(phy, wantId, pressC, baseDamp) {
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

      // final write: land on wantId
      this._injectById(phy, wantId, c.injectAmount * (c.finalWriteMult || 1));
      try { if (typeof phy.computePressure === 'function') phy.computePressure(pressC); } catch(e) {}
    },

    _messagePlan({ code, tickIndex, wantId, otherId }) {
      const m = this.cfg.message;
      const mt = m.msgTicks;
      if (!mt.includes(tickIndex)) return { injWant: 0, injOther: 0 };

      switch (code) {
        case 'ALT_WANT': {
          // want, other, want, other
          const pos = mt.indexOf(tickIndex);
          return (pos % 2 === 0)
            ? { injWant: m.pulseWant, injOther: 0 }
            : { injWant: 0, injOther: m.pulseOther };
        }
        case 'ALT_OTHER': {
          // other, want, other, want
          const pos = mt.indexOf(tickIndex);
          return (pos % 2 === 0)
            ? { injWant: 0, injOther: m.pulseOther }
            : { injWant: m.pulseWant, injOther: 0 };
        }
        case 'IN_PHASE': {
          // both each message tick (smaller)
          return { injWant: m.pulseBoth, injOther: m.pulseBoth };
        }
        case 'BURST_EARLY': {
          // both at first two ticks, none later
          const pos = mt.indexOf(tickIndex);
          return (pos <= 1) ? { injWant: m.pulseWant, injOther: m.pulseOther } : { injWant: 0, injOther: 0 };
        }
        case 'BURST_LATE': {
          // none early, both at last two ticks
          const pos = mt.indexOf(tickIndex);
          return (pos >= 2) ? { injWant: m.pulseWant, injOther: m.pulseOther } : { injWant: 0, injOther: 0 };
        }
        default:
          return { injWant: 0, injOther: 0 };
      }
    },

    _applyBasinHoldPreStep(phy, pick, wantId, law, counters, tWallMs) {
      if (tWallMs < (law.engageAfterMs || 0)) { counters.holdOffEarlyTicks++; return { delta: 0, dir: 'hold_off_msg' }; }

      const eps = law.eps ?? 1e-9;
      const basinMass = pick.rho82 + pick.rho90;
      if (basinMass < law.massGate) { counters.gateOffTicks++; return { delta: 0, dir: 'off_cold' }; }

      const n82 = this._nodeByIdLoose(phy, 82);
      const n90 = this._nodeByIdLoose(phy, 90);
      if (!n82 || !n90) return { delta: 0, dir: 'missing_nodes' };

      const sign = (wantId === 82) ? +1 : -1;
      const f = (pick.rho82 - pick.rho90) / (basinMass + eps);
      const fSigned = sign * f; // target is positive in signed coords

      const fTargetSigned = Math.abs(law.absFTarget || 0);
      const err = fTargetSigned - fSigned;

      counters.absErrSum += Math.abs(err);
      counters.absErrN += 1;

      if (Math.abs(err) <= (law.deadband || 0)) { counters.inBandTicks++; return { delta: 0, dir: 'in_deadband' }; }

      const k = (fSigned < (law.fSafetyMinSigned || -0.005)) ? law.kSafety : law.k;
      let deltaSigned = k * 0.5 * basinMass * err; // positive means “push toward wantId” in signed frame

      const maxD = law.maxDelta || 0;
      if (deltaSigned >  maxD) deltaSigned =  maxD;
      if (deltaSigned < -maxD) deltaSigned = -maxD;

      // Convert signed delta into actual transfer direction:
      // Want82 (sign=+1): positive delta -> move mass 90->82
      // Want90 (sign=-1): positive delta -> move mass 82->90
      let delta = 0;
      let dir = 'none';

      if (deltaSigned > 0) {
        if (wantId === 82) {
          const take = Math.min(deltaSigned, Math.max(0, n90.rho));
          if (take <= 0) return { delta: 0, dir: 'dry_90' };
          n90.rho -= take; n82.rho += take;
          delta = take; dir = '90to82';
        } else {
          const take = Math.min(deltaSigned, Math.max(0, n82.rho));
          if (take <= 0) return { delta: 0, dir: 'dry_82' };
          n82.rho -= take; n90.rho += take;
          delta = take; dir = '82to90';
        }
      } else if (deltaSigned < 0) {
        // negative means “relax away” (rare with our targets) — we still allow it, mass-conserving
        const want = -deltaSigned;
        if (wantId === 82) {
          const take = Math.min(want, Math.max(0, n82.rho));
          if (take <= 0) return { delta: 0, dir: 'dry_82' };
          n82.rho -= take; n90.rho += take;
          delta = take; dir = '82to90';
        } else {
          const take = Math.min(want, Math.max(0, n90.rho));
          if (take <= 0) return { delta: 0, dir: 'dry_90' };
          n90.rho -= take; n82.rho += take;
          delta = take; dir = '90to82';
        }
      }

      if (delta > 0) {
        counters.ctrlTicks++;
        counters.ctrlTotal += delta;
        counters.ctrlMax = Math.max(counters.ctrlMax, delta);
        if (dir === '90to82') counters.ctrl90to82 += delta;
        if (dir === '82to90') counters.ctrl82to90 += delta;
      }

      return { delta, dir };
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

      const combos = (c.stabilizers.length * c.wantIds.length * c.messageCodes.length);
      const windowSecSum = c.windowsMs.reduce((a,b)=>a+b,0) / 1000.0;
      const secondsPerRep = combos * windowSecSum;

      const targetSec = Math.max(60, (c.targetMinutes || 24) * 60);
      let reps = Math.ceil(targetSec / secondsPerRep); // CEIL hits (or slightly exceeds) budget

      reps = Math.max(1, reps);
      reps = Math.min(20, reps); // sanity cap
      return reps;
    },

    _buildRunList(repsPerCombo) {
      const c = this.cfg;
      const runs = [];
      let idx = 0;

      for (const windowMs of c.windowsMs) {
        for (const stabilizer of c.stabilizers) {
          for (const wantId of c.wantIds) {
            for (const code of c.messageCodes) {
              for (let rep = 1; rep <= repsPerCombo; rep++) {
                runs.push({ runIndex: idx++, repIndex: rep, windowMs, stabilizer, wantId, code });
              }
            }
          }
        }
      }
      return runs;
    },

    async _runOne({ runIndex, repIndex, windowMs, stabilizer, wantId, code, pressC, baseDamp }) {
      const phy = await this._waitForPhysics();

      // restore baseline
      this._restoreState(phy, this._baselineSnap);

      // dream select basin
      await this._selectMode(phy, wantId, pressC, baseDamp);

      const otherId = (wantId === 82) ? 90 : 82;
      const eps = this.cfg.basinHold.eps ?? 1e-9;
      const msgEndMs = this.cfg.basinHold.engageAfterMs || 800;

      // t0 truth (before message)
      const t0Pick = this._pick(phy);
      const t0Totals = this._computeTotals(phy);
      const t0Frac = (t0Pick.rho82 - t0Pick.rho90) / (t0Pick.basinMass + eps);

      const ticks = Math.max(1, Math.round(windowMs / this.cfg.everyMs));

      // counters/features
      const counters = {
        ctrlTicks: 0, ctrlTotal: 0, ctrlMax: 0, ctrl90to82: 0, ctrl82to90: 0,
        inBandTicks: 0, gateOffTicks: 0, holdOffEarlyTicks: 0,
        absErrSum: 0, absErrN: 0,
        switchCount: 0,
        msgWantTotal: 0, msgOtherTotal: 0
      };

      let basinPrev = t0Pick.basinId;
      let firstFlipAtMs = '';

      // Peak tracking (whole window)
      let peakFlux = -Infinity;
      let peakFluxAtMs = 0;

      // Peak tracking (post-message only)
      let peakFlux_postMsg = -Infinity;
      let peakFluxAtMs_postMsg = 0;

      // Regression for post-message only (decode from response)
      const R_flux_post = this._regInit();
      const R_frac_post = this._regInit();
      const R_meanAbsP_post = this._regInit();

      // snapshot at ~1s (post-message signature early)
      let fluxAt1s = '';
      let fracAt1s = '';
      let basinIdAt1s = '';

      const runId =
        `${this._isoForFile()}_r${String(runIndex).padStart(5,'0')}` +
        `_rep${repIndex}` +
        `_w${windowMs}` +
        `_want${wantId}` +
        `_code${code}` +
        `_stab${stabilizer}`;

      // visibility telemetry
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

          // Message injection at tick start
          const msg = this._messagePlan({ code, tickIndex: i, wantId, otherId });
          if (msg.injWant > 0) { this._injectById(phy, wantId, msg.injWant); counters.msgWantTotal += msg.injWant; }
          if (msg.injOther > 0) { this._injectById(phy, otherId, msg.injOther); counters.msgOtherTotal += msg.injOther; }

          // Pre-step measures (after message injection)
          const prePick = this._pick(phy);
          const preTotals = this._computeTotals(phy);
          const preFrac = (prePick.rho82 - prePick.rho90) / (prePick.basinMass + eps);

          // BasinHold (only after message ends)
          let ctrlDelta = 0, ctrlDir = 'none';
          if (stabilizer === 'basinHold') {
            const out = this._applyBasinHoldPreStep(phy, prePick, wantId, this.cfg.basinHold, counters, tWallMs);
            ctrlDelta = out.delta;
            ctrlDir = out.dir;
          }

          // Integrate step
          phy.step(this.cfg.dt, pressC, baseDamp);

          // Post-step measures
          const postPick = this._pick(phy);
          const postTotals = this._computeTotals(phy);
          const postFrac = (postPick.rho82 - postPick.rho90) / (postPick.basinMass + eps);

          // switch tracking (post)
          if (postPick.basinId !== basinPrev) {
            counters.switchCount++;
            if (firstFlipAtMs === '' && postPick.basinId !== wantId) firstFlipAtMs = Math.round(tWallMs);
            basinPrev = postPick.basinId;
          }

          // peaks
          if (postTotals.sumAbsFlux > peakFlux) {
            peakFlux = postTotals.sumAbsFlux;
            peakFluxAtMs = Math.round(tWallMs);
          }
          if (tWallMs >= msgEndMs && postTotals.sumAbsFlux > peakFlux_postMsg) {
            peakFlux_postMsg = postTotals.sumAbsFlux;
            peakFluxAtMs_postMsg = Math.round(tWallMs);
          }

          // ~1s snapshots
          if (fluxAt1s === '' && tWallMs >= 1000) {
            fluxAt1s = postTotals.sumAbsFlux;
            fracAt1s = postFrac;
            basinIdAt1s = postPick.basinId;
          }

          // post-message regressors (decode from response)
          if (tWallMs >= msgEndMs) {
            const tSec = (tWallMs - msgEndMs) / 1000.0;
            this._regAdd(R_flux_post, tSec, postTotals.sumAbsFlux);
            this._regAdd(R_frac_post, tSec, postFrac);
            this._regAdd(R_meanAbsP_post, tSec, postTotals.meanAbsP);
          }

          traceRows.push(this._csvRow([
            runId, runIndex, repIndex, windowMs, wantId, code, stabilizer,
            i, tWallMs.toFixed(3), lateByMs.toFixed(3),
            msg.injWant, msg.injOther,
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

      const summary = {
        schema: this.version,
        runId,
        runIndex,
        repIndex,
        windowMs,
        wantId,
        code,
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

        // message totals (sanity: should be equal across codes)
        msgWantTotal: counters.msgWantTotal,
        msgOtherTotal: counters.msgOtherTotal,
        msgEndMs,

        // end
        end_basinId: endPick.basinId,
        end_margin: endPick.margin,
        end_basinMass: endPick.basinMass,
        end_fracDom: endFrac,
        end_sumAbsFlux: endTotals.sumAbsFlux,
        end_meanAbsP: endTotals.meanAbsP,

        // dynamics
        firstFlipAtMs,
        switchCount: counters.switchCount,
        peakFlux,
        peakFluxAtMs,
        peakFlux_postMsg,
        peakFluxAtMs_postMsg,

        // early signature (~1s)
        basinIdAt1s,
        fluxAt1s,
        fracAt1s,

        // post-message slopes (decode from response, not injection)
        slope_flux_postMsg: this._regSlope(R_flux_post),
        slope_frac_postMsg: this._regSlope(R_frac_post),
        slope_meanAbsP_postMsg: this._regSlope(R_meanAbsP_post),

        // stabilizer telemetry
        inBandTicks: (stabilizer === 'basinHold') ? counters.inBandTicks : '',
        gateOffTicks: (stabilizer === 'basinHold') ? counters.gateOffTicks : '',
        holdOffEarlyTicks: (stabilizer === 'basinHold') ? counters.holdOffEarlyTicks : '',
        absErrMean: (stabilizer === 'basinHold' && counters.absErrN > 0) ? (counters.absErrSum / counters.absErrN) : '',
        ctrlTicks: (stabilizer === 'basinHold') ? counters.ctrlTicks : '',
        ctrlTotalTransfer: (stabilizer === 'basinHold') ? counters.ctrlTotal : '',
        ctrlMaxTransfer: (stabilizer === 'basinHold') ? counters.ctrlMax : '',
        ctrl90to82: (stabilizer === 'basinHold') ? counters.ctrl90to82 : '',
        ctrl82to90: (stabilizer === 'basinHold') ? counters.ctrl82to90 : '',

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

    async runPack(userCfg = {}) {
      this._stopFlag = false;
      if (userCfg && typeof userCfg === 'object') this.cfg = { ...this.cfg, ...userCfg };

      const app = this._getApp();
      if (!app) throw new Error('solPhase311_5: SOLDashboard not found.');

      const phy = await this._waitForPhysics();
      this._freezeLiveLoop();

      if (!this._baselineSnap) this._baselineSnap = this._snapshotState(phy);

      const ui = this._readUiParams(app);
      const pressC = (this.cfg.pressC == null) ? ui.pressC : this.cfg.pressC;
      const baseDamp = (this.cfg.baseDamp == null) ? ui.damp : this.cfg.baseDamp;

      const reps = this._computeRepsFromBudget();
      const combos = (this.cfg.stabilizers.length * this.cfg.wantIds.length * this.cfg.messageCodes.length);
      const windowSecSum = this.cfg.windowsMs.reduce((a,b)=>a+b,0) / 1000.0;
      const estSec = reps * combos * windowSecSum;

      const startIso = this._isoForFile(new Date());
      const baseName = `${this.cfg.filenameBase}_${startIso}`;

      console.log(`🧪 Phase 3.11.5 TemporalCode Pack starting`);
      console.log(`Budget: targetMinutes=${this.cfg.targetMinutes} | repsPerCombo=${this.cfg.repsPerCombo ?? '(auto)'} -> reps=${reps}`);
      console.log(`Estimate: combos=${combos}, windowSum=${windowSecSum}s, estRuntime≈${(estSec/60).toFixed(1)} minutes`);
      console.log(`Params: pressC=${pressC}, baseDamp=${baseDamp}, everyMs=${this.cfg.everyMs}, dt=${this.cfg.dt}`);
      console.log(`Codes: ${this.cfg.messageCodes.join(', ')}`);

      const summaryHeader = [
        'schema','runId','runIndex','repIndex','windowMs','wantId','code','stabilizer',
        'dt','everyMs','pressC','baseDamp',
        't0_basinId','t0_margin','t0_basinMass','t0_fracDom','t0_sumAbsFlux','t0_meanAbsP',
        'msgWantTotal','msgOtherTotal','msgEndMs',
        'end_basinId','end_margin','end_basinMass','end_fracDom','end_sumAbsFlux','end_meanAbsP',
        'firstFlipAtMs','switchCount',
        'peakFlux','peakFluxAtMs','peakFlux_postMsg','peakFluxAtMs_postMsg',
        'basinIdAt1s','fluxAt1s','fracAt1s',
        'slope_flux_postMsg','slope_frac_postMsg','slope_meanAbsP_postMsg',
        'inBandTicks','gateOffTicks','holdOffEarlyTicks','absErrMean',
        'ctrlTicks','ctrlTotalTransfer','ctrlMaxTransfer','ctrl90to82','ctrl82to90',
        'visibilityStateStart','wasHidden',
        'lateAbsAvgMs','lateAbsP95Ms','lateAbsMaxMs','missedTicks'
      ];
      const summaryLines = [ this._csvRow(summaryHeader) ];

      const traceHeader = [
        'runId','runIndex','repIndex','windowMs','wantId','code','stabilizer',
        'tick','tWallMs','lateByMs',
        'msg_injWant','msg_injOther',
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

          if (i % 20 === 0) {
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

      console.log('✅ Phase 3.11.5 TemporalCode Pack complete:', base2);
      return { baseName: base2, runsPlanned: runList.length, repsPerCombo: reps, stopped: this._stopFlag };
    }
  };

  window.solPhase311_5 = solPhase311_5;
  console.log(`✅ solPhase311_5 installed (${solPhase311_5.version}). Run: solPhase311_5.runPack()`);

})();
