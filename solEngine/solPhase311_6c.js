/* Phase 3.11.6c — Flux Filament Hunter v1 (NO camera moves)
   Purpose:
     Catch "thick-arrow" events by logging which edge (from→to) becomes the dominant flux conduit.

   Run:
     solPhase311_6c.runPack()

   Stop:
     solPhase311_6c.stop()
*/
(() => {
  'use strict';

  const solPhase311_6c = {
    version: '3.11.6c_fluxFilamentHunter_v1',
    _stopFlag: false,
    stop() { this._stopFlag = true; console.warn('🛑 solPhase311_6c.stop(): stop flag set.'); },

    cfg: {
      // Target runtime ~24 min by default:
      // 180 runs × 8s ≈ 24 min (plus overhead)
      cyclesPerBlock: 45,

      // We focus on the "spiky" port set from your 6b:
      ports: [107, 114, 118, 136],

      // Mode-select (Order B)
      injectorIds: [90, 82],
      dreamBlocks: 15,
      dreamBlockSteps: 2,
      injectAmount: 120,
      finalWriteMult: 1,

      dt: 0.12,
      everyMs: 200,
      spinWaitMs: 1.5,
      windowMs: 8000,

      // Run two alternating blocks:
      // Block 1: SPLIT → RR_AB (the runIndex 45 family)
      // Block 2: SPLIT → RR_ABCD (the runIndex 51/72 family)
      wantIds: [82, 90], // keep both to see if 90 also filaments reliably

      // Event triggers (tuned to your observed outliers)
      trigger_sumAbsFlux: 95,      // typical ~70–78, outliers >100
      trigger_edgeAbsFlux: 20,     // fallback if sumAbsFlux doesn’t capture a single-edge spike

      // UI read if null
      baseDamp: null,
      pressC: null,

      filenameBase: 'sol_phase311_6c_fluxFilamentHunter_v1',
    },

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
      throw new Error('solPhase311_6c: timed out waiting for physics.');
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
      if (!app?.config) throw new Error('solPhase311_6c: App not ready.');
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

    // More complete baseline snapshot than 6b (to reduce “hidden-state” leakage)
    _snapshotState(phy) {
      const nodePairs = [];
      for (const n of (phy.nodes || [])) {
        if (!n || n.id == null) continue;
        const out = {};
        for (const k in n) {
          const v = n[k];
          if (typeof v === 'number' && Number.isFinite(v)) out[k] = v;
          if (typeof v === 'boolean' && (k === 'isBattery' || k === 'isConstellation')) out[k] = v;
        }
        nodePairs.push([String(n.id), out]);
      }

      const edgePairs = [];
      const edges = phy.edges || [];
      for (let i = 0; i < edges.length; i++) {
        const e = edges[i];
        if (!e) continue;
        const out = {};
        for (const k in e) {
          const v = e[k];
          if (typeof v === 'number' && Number.isFinite(v)) out[k] = v;
          // keep endpoints if present
          if ((k === 'from' || k === 'to') && (typeof v === 'number' || typeof v === 'string')) out[k] = v;
          if (k === 'background' && typeof v === 'boolean') out[k] = v;
        }
        edgePairs.push([i, out]);
      }

      return { nodePairs, edgePairs };
    },

    _restoreState(phy, snap) {
      if (!snap) return;
      const nodeMap = new Map(snap.nodePairs || []);
      for (const n of (phy.nodes || [])) {
        if (!n || n.id == null) continue;
        const s = nodeMap.get(String(n.id));
        if (!s) continue;
        for (const k in s) {
          try { n[k] = s[k]; } catch(e) {}
        }
      }

      const edges = phy.edges || [];
      const edgeMap = new Map(snap.edgePairs || []);
      for (let i = 0; i < edges.length; i++) {
        const e = edges[i];
        if (!e) continue;
        const s = edgeMap.get(i);
        if (!s) continue;
        for (const k in s) {
          try { e[k] = s[k]; } catch(e) {}
        }
      }
    },

    _injectById(phy, id, amount) {
      const n = this._nodeByIdLoose(phy, id);
      if (!n) throw new Error(`solPhase311_6c: injector node not found: ${id}`);
      const amt = Math.max(0, Number(amount) || 0);
      n.rho += amt;
      try {
        if (n.isConstellation && typeof phy.reinforceSemanticStar === 'function') {
          const freqBoost = amt / 50.0;
          phy.reinforceSemanticStar(n, freqBoost);
        }
      } catch(e) {}
    },

    _computeTotals(phy) {
      let meanAbsP = 0;
      const nodes = phy.nodes || [];
      for (const n of nodes) {
        const p = Number.isFinite(n?.p) ? n.p : 0;
        meanAbsP += Math.abs(p);
      }
      meanAbsP /= Math.max(1, nodes.length);

      let sumAbsFlux = 0;
      let maxAbsEdgeFlux = 0;
      let maxEdgeFrom = '';
      let maxEdgeTo = '';
      let maxEdgeFlux = 0;
      let maxEdgeIndex = -1;

      const edges = phy.edges || [];
      for (let i = 0; i < edges.length; i++) {
        const e = edges[i];
        if (!e || e.background) continue;
        const f = Number.isFinite(e.flux) ? e.flux : 0;
        const af = Math.abs(f);
        sumAbsFlux += af;
        if (af > maxAbsEdgeFlux) {
          maxAbsEdgeFlux = af;
          maxEdgeFlux = f;
          maxEdgeFrom = (e.from != null) ? e.from : '';
          maxEdgeTo = (e.to != null) ? e.to : '';
          maxEdgeIndex = i;
        }
      }

      const eps = 1e-9;
      const concentration = maxAbsEdgeFlux / (sumAbsFlux + eps);
      return { meanAbsP, sumAbsFlux, maxAbsEdgeFlux, maxEdgeFlux, maxEdgeFrom, maxEdgeTo, maxEdgeIndex, concentration };
    },

    _pickBasin(phy) {
      const n82 = this._nodeByIdLoose(phy, 82);
      const n90 = this._nodeByIdLoose(phy, 90);
      const r82 = Number.isFinite(n82?.rho) ? n82.rho : 0;
      const r90 = Number.isFinite(n90?.rho) ? n90.rho : 0;
      return (r90 > r82) ? 90 : 82;
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

    _messagePlan(code, tickIndex) {
      // 4 ticks (0..3) only
      const tickTotal = 10;
      const split2 = 5;

      if (tickIndex > 3) return [0,0,0,0];

      switch (code) {
        case 'SPLIT_AB_SIMUL':
          return [split2, split2, 0, 0]; // A+B simultaneous each tick
        case 'RR_AB':
          return (tickIndex % 2 === 0) ? [tickTotal, 0, 0, 0] : [0, tickTotal, 0, 0];
        case 'RR_ABCD': {
          const v = [0,0,0,0];
          v[tickIndex] = tickTotal;
          return v;
        }
        default:
          return [0,0,0,0];
      }
    },

    _topKEdges(phy, k=5) {
      const edges = phy.edges || [];
      const arr = [];
      for (let i = 0; i < edges.length; i++) {
        const e = edges[i];
        if (!e || e.background) continue;
        const f = Number.isFinite(e.flux) ? e.flux : 0;
        arr.push({ i, from: e.from, to: e.to, flux: f, abs: Math.abs(f) });
      }
      arr.sort((a,b)=>b.abs-a.abs);
      return arr.slice(0, k);
    },

    async _runOne({ runIndex, wantId, code, pressC, baseDamp }) {
      const phy = await this._waitForPhysics();
      this._restoreState(phy, this._baselineSnap);

      await this._selectMode(phy, wantId, pressC, baseDamp);

      const ticks = Math.max(1, Math.round(this.cfg.windowMs / this.cfg.everyMs));
      const ports = this.cfg.ports;

      const runId = `${this._isoForFile()}_r${String(runIndex).padStart(5,'0')}_want${wantId}_code${code}`;

      let peakSumAbsFlux = -1;
      let peakAtMs = 0;
      let peakMeanAbsP = 0;
      let peakMaxAbsEdgeFlux = 0;
      let peakEdgeFrom = '';
      let peakEdgeTo = '';
      let peakEdgeIndex = -1;
      let peakEdgeFlux = 0;
      let peakConcentration = 0;

      let firstTriggeredAtMs = '';
      let triggeredCount = 0;
      let pCrashAtMs = '';

      const events = [];

      const start = performance.now();
      for (let t = 0; t < ticks; t++) {
        if (this._stopFlag) break;

        const target = start + t * this.cfg.everyMs;
        while (performance.now() < target) {
          const remain = target - performance.now();
          if (this.cfg.spinWaitMs > 0 && remain <= this.cfg.spinWaitMs) break;
          if (remain > 2) await this._sleep(Math.min(50, remain - this.cfg.spinWaitMs));
        }
        if (this.cfg.spinWaitMs > 0) while (performance.now() < target) { /* spin */ }

        const inj = this._messagePlan(code, t);
        for (let k = 0; k < 4; k++) {
          const amt = inj[k] || 0;
          if (amt > 0) this._injectById(phy, ports[k], amt);
        }

        phy.step(this.cfg.dt, pressC, baseDamp);

        const nowMs = performance.now() - start;
        const basin = this._pickBasin(phy);
        const tot = this._computeTotals(phy);

        if (tot.sumAbsFlux > peakSumAbsFlux) {
          peakSumAbsFlux = tot.sumAbsFlux;
          peakAtMs = nowMs;
          peakMeanAbsP = tot.meanAbsP;
          peakMaxAbsEdgeFlux = tot.maxAbsEdgeFlux;
          peakEdgeFrom = tot.maxEdgeFrom;
          peakEdgeTo = tot.maxEdgeTo;
          peakEdgeIndex = tot.maxEdgeIndex;
          peakEdgeFlux = tot.maxEdgeFlux;
          peakConcentration = tot.concentration;
        }

        const triggered =
          (tot.sumAbsFlux >= this.cfg.trigger_sumAbsFlux) ||
          (tot.maxAbsEdgeFlux >= this.cfg.trigger_edgeAbsFlux);

        if (triggered) {
          triggeredCount++;
          if (firstTriggeredAtMs === '') firstTriggeredAtMs = Math.round(nowMs);

          // only compute top-K when triggered (expensive)
          const top = this._topKEdges(phy, 5)
            .map(e => `${e.i}:${e.from}->${e.to}:${e.flux.toFixed(4)}`)
            .join(' | ');

          events.push(this._csvRow([
            this.version,
            runId,
            runIndex,
            wantId,
            code,
            Math.round(nowMs),
            basin,
            tot.sumAbsFlux.toFixed(6),
            tot.meanAbsP.toFixed(6),
            tot.maxAbsEdgeFlux.toFixed(6),
            tot.maxEdgeIndex,
            tot.maxEdgeFrom,
            tot.maxEdgeTo,
            tot.maxEdgeFlux.toFixed(6),
            tot.concentration.toFixed(6),
            top
          ]));
        }

        if (pCrashAtMs === '' && tot.meanAbsP < 0.015 && nowMs > 500) {
          pCrashAtMs = Math.round(nowMs);
        }
      }

      const summary = {
        schema: this.version,
        runId,
        runIndex,
        wantId,
        code,
        portA: ports[0], portB: ports[1], portC: ports[2], portD: ports[3],
        pressC, baseDamp, dt: this.cfg.dt, everyMs: this.cfg.everyMs, windowMs: this.cfg.windowMs,
        peakSumAbsFlux, peakAtMs, peakMeanAbsP,
        peakMaxAbsEdgeFlux, peakEdgeIndex, peakEdgeFrom, peakEdgeTo, peakEdgeFlux,
        peakConcentration,
        firstTriggeredAtMs,
        triggeredCount,
        pCrashAtMs
      };

      return { summary, events };
    },

    async runPack(userCfg = {}) {
      this._stopFlag = false;
      if (userCfg && typeof userCfg === 'object') this.cfg = { ...this.cfg, ...userCfg };

      const app = this._getApp();
      if (!app) throw new Error('solPhase311_6c: SOLDashboard not found.');

      const phy = await this._waitForPhysics();
      this._freezeLiveLoop();

      if (!this._baselineSnap) this._baselineSnap = this._snapshotState(phy);

      const ui = this._readUiParams(app);
      const pressC = (this.cfg.pressC == null) ? ui.pressC : this.cfg.pressC;
      const baseDamp = (this.cfg.baseDamp == null) ? ui.damp : this.cfg.baseDamp;

      const startIso = this._isoForFile(new Date());
      const baseName = `${this.cfg.filenameBase}_${startIso}`;

      const summaryHeader = [
        'schema','runId','runIndex','wantId','code',
        'portA','portB','portC','portD',
        'pressC','baseDamp','dt','everyMs','windowMs',
        'peakSumAbsFlux','peakAtMs','peakMeanAbsP',
        'peakMaxAbsEdgeFlux','peakEdgeIndex','peakEdgeFrom','peakEdgeTo','peakEdgeFlux',
        'peakConcentration',
        'firstTriggeredAtMs','triggeredCount','pCrashAtMs'
      ];
      const eventHeader = [
        'schema','runId','runIndex','wantId','code','tMs','basin',
        'sumAbsFlux','meanAbsP','maxAbsEdgeFlux','maxEdgeIndex','maxEdgeFrom','maxEdgeTo','maxEdgeFlux',
        'concentration','top5Edges'
      ];

      const summaryLines = [ this._csvRow(summaryHeader) ];
      const eventLines = [ this._csvRow(eventHeader) ];

      // Build run plan:
      const plan = [];
      let idx = 0;

      const addBlock = (wantId, codeA, codeB, cycles) => {
        for (let c = 0; c < cycles; c++) {
          plan.push({ runIndex: idx++, wantId, code: codeA });
          plan.push({ runIndex: idx++, wantId, code: codeB });
        }
      };

      for (const wantId of this.cfg.wantIds) {
        // Block 1: SPLIT -> RR_AB
        addBlock(wantId, 'SPLIT_AB_SIMUL', 'RR_AB', this.cfg.cyclesPerBlock);
        // Block 2: SPLIT -> RR_ABCD
        addBlock(wantId, 'SPLIT_AB_SIMUL', 'RR_ABCD', this.cfg.cyclesPerBlock);
      }

      const estMin = (plan.length * (this.cfg.windowMs / 1000)) / 60;
      console.log(`🧪 Phase 3.11.6c starting (${this.version})`);
      console.log(`Runs: ${plan.length} | Estimated ≈ ${estMin.toFixed(1)} minutes`);
      console.log(`Ports: [${this.cfg.ports.join(', ')}] | pressC=${pressC} | baseDamp=${baseDamp}`);

      try {
        for (let i = 0; i < plan.length; i++) {
          if (this._stopFlag) break;
          if (i % 20 === 0) console.log(`Progress: ${i}/${plan.length} | hidden=${document.hidden}`);
          const r = plan[i];
          const out = await this._runOne({ ...r, pressC, baseDamp });

          const s = out.summary;
          summaryLines.push(this._csvRow(summaryHeader.map(k => (k in s ? s[k] : ''))));
          for (const row of out.events) eventLines.push(row);
        }
      } finally {
        this._unfreezeLiveLoop();
      }

      const endIso = this._isoForFile(new Date());
      const base2 = `${baseName}_${endIso}`;

      this._downloadText(`${base2}_MASTER_summary.csv`, summaryLines.join(''));
      this._downloadText(`${base2}_MASTER_events.csv`, eventLines.join(''));

      console.log('✅ Phase 3.11.6c complete:', base2);
      return { baseName: base2, runsPlanned: plan.length, stopped: this._stopFlag };
    }
  };

  window.solPhase311_6c = solPhase311_6c;
  console.log(`✅ solPhase311_6c installed (${solPhase311_6c.version}). Run: solPhase311_6c.runPack()`);

})();
