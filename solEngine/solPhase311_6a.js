/* Phase 3.11.6a — DistributedInputTemporalPacketPack v1 (NO basinHold)
   Purpose:
     - Test whether temporal packets remain decodable when input is spatially distributed
     - Simultaneous vs alternating vs round-robin vs burst-late patterns
     - Keep mode-select (want82/want90) but message enters via peripheral input nodes
     - Windows: 8s and 16s (coherence vs metastability)

   Run:
     solPhase311_6a.runPack()

   Stop early:
     solPhase311_6a.stop()
*/
(() => {
  'use strict';

  const solPhase311_6a = {
    version: '3.11.6a_distributedInputTemporalPacketPack_v1',
    _stopFlag: false,
    stop() { this._stopFlag = true; console.warn('🛑 solPhase311_6a.stop(): stop flag set.'); },

    cfg: {
      // Budget control (20–30min target)
      targetMinutes: 24,
      repsPerCombo: null, // override with a number if you want

      // Mode-select (Order B)
      injectorIds: [90, 82],
      dreamBlocks: 15,
      dreamBlockSteps: 2,
      injectAmount: 120,
      finalWriteMult: 1,

      dt: 0.12,
      everyMs: 200,
      spinWaitMs: 1.5,

      windowsMs: [8000, 16000],
      wantIds: [82, 90],

      // Input ports (auto-select 4 existing nodes; avoid 82/90 if possible)
      preferredInputIds: [79, 89, 92, 104, 107, 114, 118, 136, 64, 33, 22, 13, 9, 4, 3, 2, 1],
      inputPortCount: 4,

      // Message: 4 ticks (0..600ms). Total injected each tick = 10. Total per message = 40.
      message: {
        msgTicks: [0, 1, 2, 3],
        tickTotal: 10,
      },

      // Distributed codes (all preserve total message mass = 40)
      messageCodes: [
        'UNI_A',            // all mass through port A
        'RR_AB',            // A,B,A,B (alternating)
        'SPLIT_AB_SIMUL',   // A+B simultaneously every tick
        'RR_ABCD',          // A,B,C,D (spatial sweep)
        'SIMUL_ABCD',       // A+B+C+D simultaneously every tick
        'BURST_LATE_AB'     // nothing early; A+B at ticks 2,3
      ],

      // Read from UI at pack start if null
      baseDamp: null,
      pressC: null,

      filenameBase: 'sol_phase311_6a_distributedInputTemporalPacketPack_v1',
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
      throw new Error('solPhase311_6a: timed out waiting for physics.');
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
      if (!app?.config) throw new Error('solPhase311_6a: App not ready.');
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
      if (!n) throw new Error(`solPhase311_6a: injector node not found: ${id}`);
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
      return { rho: Number.isFinite(n.rho) ? n.rho : 0, p: Number.isFinite(n.p) ? n.p : 0 };
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
      this._injectById(phy, wantId, c.injectAmount * (c.finalWriteMult || 1));
      try { if (typeof phy.computePressure === 'function') phy.computePressure(pressC); } catch(e) {}
    },

    _pickInputPorts(phy) {
      const avoid = new Set([82, 90]);
      const ports = [];
      for (const id of this.cfg.preferredInputIds) {
        if (avoid.has(id)) continue;
        if (this._nodeByIdLoose(phy, id)) ports.push(id);
        if (ports.length >= this.cfg.inputPortCount) break;
      }
      // Fallbacks if graph doesn’t have enough preferred nodes
      if (ports.length < 2) {
        // last-resort: include basins
        if (!ports.includes(82) && this._nodeByIdLoose(phy, 82)) ports.push(82);
        if (!ports.includes(90) && this._nodeByIdLoose(phy, 90)) ports.push(90);
      }
      while (ports.length < this.cfg.inputPortCount) ports.push(ports[ports.length - 1] ?? 82);
      return ports.slice(0, this.cfg.inputPortCount);
    },

    _messagePlan({ code, tickIndex, ports }) {
      const mt = this.cfg.message.msgTicks;
      if (!mt.includes(tickIndex)) return [0,0,0,0];

      const tickTotal = this.cfg.message.tickTotal;
      const A = 0, B = 1, C = 2, D = 3;

      const split2 = tickTotal / 2;
      const split4 = tickTotal / 4;

      switch (code) {
        case 'UNI_A':
          return [tickTotal, 0, 0, 0];

        case 'RR_AB': {
          const pos = mt.indexOf(tickIndex);
          return (pos % 2 === 0) ? [tickTotal, 0, 0, 0] : [0, tickTotal, 0, 0];
        }

        case 'SPLIT_AB_SIMUL':
          return [split2, split2, 0, 0];

        case 'RR_ABCD': {
          const pos = mt.indexOf(tickIndex);
          const v = [0,0,0,0];
          v[pos] = tickTotal;
          return v;
        }

        case 'SIMUL_ABCD':
          return [split4, split4, split4, split4];

        case 'BURST_LATE_AB': {
          const pos = mt.indexOf(tickIndex);
          if (pos < 2) return [0,0,0,0];
          return [split2, split2, 0, 0];
        }

        default:
          return [0,0,0,0];
      }
    },

    _computeRepsFromBudget() {
      if (Number.isFinite(this.cfg.repsPerCombo) && this.cfg.repsPerCombo > 0) return Math.floor(this.cfg.repsPerCombo);

      const combos = this.cfg.windowsMs.length * this.cfg.wantIds.length * this.cfg.messageCodes.length;
      const winSumSec = this.cfg.windowsMs.reduce((a,b)=>a+b,0) / 1000;
      const secPerRep = this.cfg.wantIds.length * this.cfg.messageCodes.length * winSumSec;

      const targetSec = Math.max(300, (this.cfg.targetMinutes || 24) * 60);
      let reps = Math.ceil(targetSec / secPerRep);
      reps = Math.max(1, Math.min(20, reps));
      return reps;
    },

    async _runOne({ runIndex, repIndex, windowMs, wantId, code, pressC, baseDamp, ports }) {
      const phy = await this._waitForPhysics();
      this._restoreState(phy, this._baselineSnap);

      await this._selectMode(phy, wantId, pressC, baseDamp);

      const eps = 1e-9;
      const msgEndMs = 800; // 4 ticks * 200ms

      const t0Pick = this._pick(phy);
      const t0Totals = this._computeTotals(phy);
      const t0Frac = (t0Pick.rho82 - t0Pick.rho90) / (t0Pick.basinMass + eps);

      const ticks = Math.max(1, Math.round(windowMs / this.cfg.everyMs));

      let basinPrev = t0Pick.basinId;
      let firstFlipAtMs = '';
      let switchCount = 0;

      let fluxAt1s = '';
      let fracAt1s = '';
      let basinIdAt1s = '';

      let portRhoAt1s = ['', '', '', ''];
      let portRhoEnd = ['', '', '', ''];

      // post-message regressions
      const regInit = () => ({ n:0, st:0, st2:0, sy:0, sty:0 });
      const regAdd = (R,t,y)=>{ R.n++; R.st+=t; R.st2+=t*t; R.sy+=y; R.sty+=t*y; };
      const regSlope = (R)=>{
        const den = (R.n*R.st2 - R.st*R.st);
        if (!Number.isFinite(den) || Math.abs(den) < 1e-12) return 0;
        const num = (R.n*R.sty - R.st*R.sy);
        const b = num/den;
        return Number.isFinite(b)?b:0;
      };

      const R_flux = regInit();
      const R_frac = regInit();
      const R_meanAbsP = regInit();

      let msgTotal = 0;

      const runId =
        `${this._isoForFile()}_r${String(runIndex).padStart(5,'0')}` +
        `_rep${repIndex}` +
        `_w${windowMs}` +
        `_want${wantId}` +
        `_code${code}`;

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

          // Inject message via distributed ports
          const inj = this._messagePlan({ code, tickIndex: i, ports });
          for (let k = 0; k < 4; k++) {
            const amt = inj[k] || 0;
            if (amt > 0) { this._injectById(phy, ports[k], amt); msgTotal += amt; }
          }

          // Step
          phy.step(this.cfg.dt, pressC, baseDamp);

          // Measures
          const postPick = this._pick(phy);
          const postTotals = this._computeTotals(phy);
          const postFrac = (postPick.rho82 - postPick.rho90) / (postPick.basinMass + eps);

          if (postPick.basinId !== basinPrev) {
            switchCount++;
            if (firstFlipAtMs === '' && postPick.basinId !== wantId) firstFlipAtMs = Math.round(tWallMs);
            basinPrev = postPick.basinId;
          }

          if (fluxAt1s === '' && tWallMs >= 1000) {
            fluxAt1s = postTotals.sumAbsFlux;
            fracAt1s = postFrac;
            basinIdAt1s = postPick.basinId;
            for (let k = 0; k < 4; k++) {
              const n = this._nodeByIdLoose(phy, ports[k]);
              portRhoAt1s[k] = n ? n.rho : '';
            }
          }

          if (tWallMs >= msgEndMs) {
            const tSec = (tWallMs - msgEndMs) / 1000.0;
            regAdd(R_flux, tSec, postTotals.sumAbsFlux);
            regAdd(R_frac, tSec, postFrac);
            regAdd(R_meanAbsP, tSec, postTotals.meanAbsP);
          }

          traceRows.push(this._csvRow([
            runId, runIndex, repIndex, windowMs, wantId, code,
            ports[0], ports[1], ports[2], ports[3],
            i, tWallMs.toFixed(3), lateByMs.toFixed(3),
            inj[0], inj[1], inj[2], inj[3],
            postPick.basinId, postPick.basinMass.toFixed(6), postFrac.toFixed(6),
            postTotals.sumAbsFlux.toFixed(6), postTotals.meanAbsP.toFixed(6),
            postTotals.rhoSum.toFixed(6)
          ]));
        }
      });

      document.removeEventListener('visibilitychange', onVis);

      // End state
      const endPick = this._pick(phy);
      const endTotals = this._computeTotals(phy);
      const endFrac = (endPick.rho82 - endPick.rho90) / (endPick.basinMass + eps);

      for (let k = 0; k < 4; k++) {
        const n = this._nodeByIdLoose(phy, ports[k]);
        portRhoEnd[k] = n ? n.rho : '';
      }

      const summary = {
        schema: this.version,
        runId, runIndex, repIndex,
        windowMs, wantId, code,
        dt: this.cfg.dt,
        everyMs: this.cfg.everyMs,
        pressC, baseDamp,

        portA: ports[0], portB: ports[1], portC: ports[2], portD: ports[3],

        t0_basinId: t0Pick.basinId,
        t0_basinMass: t0Pick.basinMass,
        t0_fracDom: t0Frac,
        t0_sumAbsFlux: t0Totals.sumAbsFlux,
        t0_meanAbsP: t0Totals.meanAbsP,

        msgTotal,

        basinIdAt1s,
        fluxAt1s,
        fracAt1s,
        portA_rhoAt1s: portRhoAt1s[0],
        portB_rhoAt1s: portRhoAt1s[1],
        portC_rhoAt1s: portRhoAt1s[2],
        portD_rhoAt1s: portRhoAt1s[3],

        end_basinId: endPick.basinId,
        end_basinMass: endPick.basinMass,
        end_fracDom: endFrac,
        end_sumAbsFlux: endTotals.sumAbsFlux,
        end_meanAbsP: endTotals.meanAbsP,
        portA_rhoEnd: portRhoEnd[0],
        portB_rhoEnd: portRhoEnd[1],
        portC_rhoEnd: portRhoEnd[2],
        portD_rhoEnd: portRhoEnd[3],

        firstFlipAtMs,
        switchCount,

        slope_flux_postMsg: regSlope(R_flux),
        slope_frac_postMsg: regSlope(R_frac),
        slope_meanAbsP_postMsg: regSlope(R_meanAbsP),

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
      if (!app) throw new Error('solPhase311_6a: SOLDashboard not found.');

      const phy = await this._waitForPhysics();
      this._freezeLiveLoop();

      if (!this._baselineSnap) this._baselineSnap = this._snapshotState(phy);

      const ui = this._readUiParams(app);
      const pressC = (this.cfg.pressC == null) ? ui.pressC : this.cfg.pressC;
      const baseDamp = (this.cfg.baseDamp == null) ? ui.damp : this.cfg.baseDamp;

      // Choose input ports ONCE for the whole pack (apples-to-apples)
      const ports = this._pickInputPorts(phy);

      const reps = this._computeRepsFromBudget();
      const combos = this.cfg.windowsMs.length * this.cfg.wantIds.length * this.cfg.messageCodes.length;
      const winSumSec = this.cfg.windowsMs.reduce((a,b)=>a+b,0) / 1000.0;
      const estSec = reps * this.cfg.wantIds.length * this.cfg.messageCodes.length * winSumSec;

      const startIso = this._isoForFile(new Date());
      const baseName = `${this.cfg.filenameBase}_${startIso}`;

      console.log(`🧪 Phase 3.11.6a DistributedInput Pack starting`);
      console.log(`Ports: A=${ports[0]}, B=${ports[1]}, C=${ports[2]}, D=${ports[3]}`);
      console.log(`Budget: targetMinutes=${this.cfg.targetMinutes} -> reps=${reps}`);
      console.log(`Estimate: combos=${combos}, winSum=${winSumSec}s, estRuntime≈${(estSec/60).toFixed(1)} minutes`);
      console.log(`Params: pressC=${pressC}, baseDamp=${baseDamp}, everyMs=${this.cfg.everyMs}, dt=${this.cfg.dt}`);

      const summaryHeader = [
        'schema','runId','runIndex','repIndex','windowMs','wantId','code',
        'dt','everyMs','pressC','baseDamp',
        'portA','portB','portC','portD',
        't0_basinId','t0_basinMass','t0_fracDom','t0_sumAbsFlux','t0_meanAbsP',
        'msgTotal',
        'basinIdAt1s','fluxAt1s','fracAt1s',
        'portA_rhoAt1s','portB_rhoAt1s','portC_rhoAt1s','portD_rhoAt1s',
        'end_basinId','end_basinMass','end_fracDom','end_sumAbsFlux','end_meanAbsP',
        'portA_rhoEnd','portB_rhoEnd','portC_rhoEnd','portD_rhoEnd',
        'firstFlipAtMs','switchCount',
        'slope_flux_postMsg','slope_frac_postMsg','slope_meanAbsP_postMsg',
        'visibilityStateStart','wasHidden',
        'lateAbsAvgMs','lateAbsP95Ms','lateAbsMaxMs','missedTicks'
      ];
      const summaryLines = [ this._csvRow(summaryHeader) ];

      const traceHeader = [
        'runId','runIndex','repIndex','windowMs','wantId','code',
        'portA','portB','portC','portD',
        'tick','tWallMs','lateByMs',
        'injA','injB','injC','injD',
        'post_basinId','post_basinMass','post_fracDom',
        'post_sumAbsFlux','post_meanAbsP','rhoSum'
      ];
      const traceLines = [ this._csvRow(traceHeader) ];

      // Build runs
      const runList = [];
      let idx = 0;
      for (const windowMs of this.cfg.windowsMs) {
        for (const wantId of this.cfg.wantIds) {
          for (const code of this.cfg.messageCodes) {
            for (let rep = 1; rep <= reps; rep++) {
              runList.push({ runIndex: idx++, repIndex: rep, windowMs, wantId, code });
            }
          }
        }
      }

      console.log(`Total runs: ${runList.length}`);

      try {
        for (let i = 0; i < runList.length; i++) {
          if (this._stopFlag) break;
          if (i % 20 === 0) console.log(`Progress: ${i}/${runList.length} (hidden=${document.hidden})`);
          const r = runList[i];
          const out = await this._runOne({ ...r, pressC, baseDamp, ports });

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

      console.log('✅ Phase 3.11.6a complete:', base2);
      return { baseName: base2, runsPlanned: runList.length, repsPerCombo: reps, ports, stopped: this._stopFlag };
    }
  };

  window.solPhase311_6a = solPhase311_6a;
  console.log(`✅ solPhase311_6a installed (${solPhase311_6a.version}). Run: solPhase311_6a.runPack()`);

})();
