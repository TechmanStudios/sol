/* Phase 3.11.16e — Dual-Bus Timeline Map v1
   Purpose:
     Map the choreography of two bus families into (79,89):
       - 114→89 and 114→79
       - 136→89 and 136→79
     across a small (pressC, baseDamp) sweep.

   Outputs:
     - MASTER_summary.csv   (per run: onset/peak/duration for each bus + global peaks)
     - MASTER_busTrace.csv  (per tick: four bus fluxes + global telemetry)

   Run:
     solPhase311_16e.runPack()

   Stop:
     solPhase311_16e.stop()

   Notes:
     - UI-neutral (no camera/graph moves)
     - Full baseline restore before each run
     - RR_ABCD packet on ports [107,114,118,136]
*/
(() => {
  'use strict';

  const solPhase311_16e = {
    version: '3.11.16e_dualBusTimelineMap_v1',
    _stopFlag: false,
    stop() { this._stopFlag = true; console.warn('🛑 solPhase311_16e.stop(): stop flag set.'); },

    cfg: {
      // Runtime target:
      // combos = 5 dampMults * 3 pressMults = 15
      // repsPerCombo = 12 => 180 runs × 8s ≈ 24 min (+ overhead)
      repsPerCombo: 12,

      // Fixed I/O topology
      ports: [107, 114, 118, 136],
      wantIds: [82], // set to [82,90] if you want both

      // Mode-select (Order B)
      injectorIds: [90, 82],
      dreamBlocks: 15,
      dreamBlockSteps: 2,
      injectAmount: 120,
      finalWriteMult: 1,

      // Integration + metronome
      dt: 0.12,
      everyMs: 200,
      spinWaitMs: 1.5,
      windowMs: 8000,

      // Sweep (around observed baseline pressC≈2, baseDamp≈5)
      dampMults: [0.6, 0.8, 1.0, 1.2, 1.4],
      pressMults: [0.75, 1.0, 1.25],

      // “Bus” edges we track explicitly
      busPairs: [
        { name: 'bus114_89', from: 114, to: 89 },
        { name: 'bus114_79', from: 114, to: 79 },
        { name: 'bus136_89', from: 136, to: 89 },
        { name: 'bus136_79', from: 136, to: 79 },
      ],

      // For onset/duration logic
      busOnAbsFluxThresh: 1.0, // “bus is active” if |flux| >= this

      // UI read if null
      baseDamp: null,
      pressC: null,

      filenameBase: 'sol_phase311_16e_dualBusTimelineMap_v1',
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
      throw new Error('solPhase311_16e: timed out waiting for physics.');
    },

    _readUiParams(app) {
      const pressC = (app?.dom?.pressureSlider)
        ? (parseFloat(String(app.dom.pressureSlider.value)) * (app.config.pressureSliderScale || 1))
        : 2;
      const damp = (app?.dom?.dampSlider)
        ? parseFloat(String(app.dom.dampSlider.value))
        : 5;
      return {
        pressC: Number.isFinite(pressC) ? pressC : 2,
        damp: Number.isFinite(damp) ? damp : 5
      };
    },

    _freezeLiveLoop() {
      const app = this._getApp();
      if (!app?.config) throw new Error('solPhase311_16e: App not ready.');
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

    // Full numeric snapshot for stability across runs
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
        for (const k in s) { try { n[k] = s[k]; } catch(e) {} }
      }

      const edges = phy.edges || [];
      const edgeMap = new Map(snap.edgePairs || []);
      for (let i = 0; i < edges.length; i++) {
        const e = edges[i];
        if (!e) continue;
        const s = edgeMap.get(i);
        if (!s) continue;
        for (const k in s) { try { e[k] = s[k]; } catch(e) {} }
      }
    },

    _injectById(phy, id, amount) {
      const n = this._nodeByIdLoose(phy, id);
      if (!n) throw new Error(`solPhase311_16e: injector node not found: ${id}`);
      const amt = Math.max(0, Number(amount) || 0);
      n.rho += amt;
      try {
        if (n.isConstellation && typeof phy.reinforceSemanticStar === 'function') {
          const freqBoost = amt / 50.0;
          phy.reinforceSemanticStar(n, freqBoost);
        }
      } catch(e) {}
    },

    _pickBasin(phy) {
      const n82 = this._nodeByIdLoose(phy, 82);
      const n90 = this._nodeByIdLoose(phy, 90);
      const r82 = Number.isFinite(n82?.rho) ? n82.rho : 0;
      const r90 = Number.isFinite(n90?.rho) ? n90.rho : 0;
      return (r90 > r82) ? 90 : 82;
    },

    // Map bus edge (from,to) -> edgeIndex (first match)
    _buildEdgeIndexMap(phy) {
      const map = new Map();
      const edges = phy.edges || [];
      for (let i = 0; i < edges.length; i++) {
        const e = edges[i];
        if (!e || e.background) continue;
        const key = `${e.from}->${e.to}`;
        if (!map.has(key)) map.set(key, i);
      }
      return map;
    },

    _getEdgeFluxByIndex(phy, idx) {
      const e = (phy.edges || [])[idx];
      if (!e) return 0;
      const f = Number.isFinite(e.flux) ? e.flux : 0;
      return f;
    },

    _computeGlobal(phy) {
      let meanAbsP = 0;
      const nodes = phy.nodes || [];
      for (const n of nodes) {
        const p = Number.isFinite(n?.p) ? n.p : 0;
        meanAbsP += Math.abs(p);
      }
      meanAbsP /= Math.max(1, nodes.length);

      let sumAbsFlux = 0;
      let maxAbsEdgeFlux = 0;
      let maxEdgeIndex = -1;
      let maxEdgeFrom = '';
      let maxEdgeTo = '';
      let maxEdgeFlux = 0;

      const edges = phy.edges || [];
      for (let i = 0; i < edges.length; i++) {
        const e = edges[i];
        if (!e || e.background) continue;
        const f = Number.isFinite(e.flux) ? e.flux : 0;
        const af = Math.abs(f);
        sumAbsFlux += af;
        if (af > maxAbsEdgeFlux) {
          maxAbsEdgeFlux = af;
          maxEdgeIndex = i;
          maxEdgeFrom = e.from;
          maxEdgeTo = e.to;
          maxEdgeFlux = f;
        }
      }

      const eps = 1e-9;
      const concentration = maxAbsEdgeFlux / (sumAbsFlux + eps);
      return { meanAbsP, sumAbsFlux, maxAbsEdgeFlux, maxEdgeIndex, maxEdgeFrom, maxEdgeTo, maxEdgeFlux, concentration };
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

    // RR_ABCD message: ticks 0..3 inject on A,B,C,D with 10 each (total 40)
    _messagePlan_RR_ABCD(tickIndex) {
      const tickTotal = 10;
      if (tickIndex > 3) return [0,0,0,0];
      const v = [0,0,0,0];
      v[tickIndex] = tickTotal;
      return v;
    },

    async _metronome({ everyMs, ticks, spinWaitMs, onTick }) {
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

        await onTick({ tick: i, tMs: now2 - start, lateByMs });
      }

      absLates.sort((a,b)=>a-b);
      const n = Math.max(1, absLates.length);
      const p95 = absLates[Math.floor(0.95 * (n - 1))] ?? 0;
      const avg = absLates.reduce((a,b)=>a+b,0) / n;
      const max = absLates[n - 1] ?? 0;

      return { lateAbsAvg: avg, lateAbsP95: p95, lateAbsMax: max, missedTicks };
    },

    async _runOne({ runIndex, repIndex, wantId, pressC, baseDamp, pressMult, dampMult }) {
      const phy = await this._waitForPhysics();
      this._restoreState(phy, this._baselineSnap);

      await this._selectMode(phy, wantId, pressC, baseDamp);

      const edgeMap = this._buildEdgeIndexMap(phy);
      const bus = this.cfg.busPairs.map(b => ({
        ...b,
        key: `${b.from}->${b.to}`,
        idx: edgeMap.has(`${b.from}->${b.to}`) ? edgeMap.get(`${b.from}->${b.to}`) : -1
      }));

      const ports = this.cfg.ports;
      const ticks = Math.max(1, Math.round(this.cfg.windowMs / this.cfg.everyMs));
      const runId =
        `${this._isoForFile()}_r${String(runIndex).padStart(5,'0')}` +
        `_rep${repIndex}_want${wantId}_pM${pressMult}_dM${dampMult}`;

      const visStart = document.visibilityState;
      let wasHidden = false;
      const onVis = () => { if (document.hidden) wasHidden = true; };
      document.addEventListener('visibilitychange', onVis, { passive: true });

      // Per-bus onset/peak/duration
      const thresh = this.cfg.busOnAbsFluxThresh;
      const busStats = {};
      for (const b of bus) {
        busStats[b.name] = {
          idx: b.idx,
          from: b.from, to: b.to,
          onFirstAtMs: '',
          onTicks: 0,
          peakAbs: -1,
          peakAtMs: 0,
          peakFlux: 0
        };
      }

      // Global peaks
      let peakSumAbsFlux = -1, peakAtMs = 0, peakMeanAbsP = 0;
      let peakMaxAbsEdgeFlux = -1, peakEdgeIndex = -1, peakEdgeFrom = '', peakEdgeTo = '', peakEdgeFlux = 0, peakConcentration = 0;

      // Trace lines
      const traceRows = [];

      // Pressure stats
      let pCrashAtMs = '';
      let pMin = Infinity;

      const met = await this._metronome({
        everyMs: this.cfg.everyMs,
        ticks,
        spinWaitMs: this.cfg.spinWaitMs,
        onTick: async ({ tick, tMs, lateByMs }) => {
          // inject RR_ABCD packet first 4 ticks
          const inj = this._messagePlan_RR_ABCD(tick);
          for (let k = 0; k < 4; k++) {
            const amt = inj[k] || 0;
            if (amt > 0) this._injectById(phy, ports[k], amt);
          }

          phy.step(this.cfg.dt, pressC, baseDamp);

          const basin = this._pickBasin(phy);
          const g = this._computeGlobal(phy);

          // Global peaks
          if (g.sumAbsFlux > peakSumAbsFlux) {
            peakSumAbsFlux = g.sumAbsFlux;
            peakAtMs = tMs;
            peakMeanAbsP = g.meanAbsP;
          }
          if (g.maxAbsEdgeFlux > peakMaxAbsEdgeFlux) {
            peakMaxAbsEdgeFlux = g.maxAbsEdgeFlux;
            peakEdgeIndex = g.maxEdgeIndex;
            peakEdgeFrom = g.maxEdgeFrom;
            peakEdgeTo = g.maxEdgeTo;
            peakEdgeFlux = g.maxEdgeFlux;
            peakConcentration = g.concentration;
          }

          // Pressure crash/min
          pMin = Math.min(pMin, g.meanAbsP);
          if (pCrashAtMs === '' && g.meanAbsP < 0.015 && tMs > 500) pCrashAtMs = Math.round(tMs);

          // Bus flux sampling
          const busFlux = {};
          for (const b of bus) {
            const f = (b.idx >= 0) ? this._getEdgeFluxByIndex(phy, b.idx) : 0;
            busFlux[b.name] = f;

            const st = busStats[b.name];
            const af = Math.abs(f);

            if (af >= thresh) {
              st.onTicks++;
              if (st.onFirstAtMs === '') st.onFirstAtMs = Math.round(tMs);
            }
            if (af > st.peakAbs) {
              st.peakAbs = af;
              st.peakAtMs = tMs;
              st.peakFlux = f;
            }
          }

          // Bus trace row (always)
          traceRows.push(this._csvRow([
            this.version,
            runId,
            runIndex,
            repIndex,
            wantId,
            pressC, baseDamp, pressMult, dampMult,
            tick, Math.round(tMs), lateByMs.toFixed(3),
            basin,
            g.sumAbsFlux.toFixed(6),
            g.meanAbsP.toFixed(6),
            g.maxAbsEdgeFlux.toFixed(6),
            g.maxEdgeIndex,
            g.maxEdgeFrom,
            g.maxEdgeTo,
            g.maxEdgeFlux.toFixed(6),
            g.concentration.toFixed(6),
            // 4 tracked buses
            busFlux.bus114_89?.toFixed(6) ?? '0',
            busFlux.bus114_79?.toFixed(6) ?? '0',
            busFlux.bus136_89?.toFixed(6) ?? '0',
            busFlux.bus136_79?.toFixed(6) ?? '0'
          ]));
        }
      });

      document.removeEventListener('visibilitychange', onVis);

      // Summarize buses
      const summarizeBus = (name) => {
        const st = busStats[name];
        const onFrac = st.onTicks / Math.max(1, ticks);
        return {
          [`${name}_idx`]: st.idx,
          [`${name}_onFirstAtMs`]: st.onFirstAtMs,
          [`${name}_onTicks`]: st.onTicks,
          [`${name}_onFrac`]: onFrac,
          [`${name}_peakAbs`]: (st.peakAbs < 0 ? '' : st.peakAbs),
          [`${name}_peakAtMs`]: (st.peakAbs < 0 ? '' : Math.round(st.peakAtMs)),
          [`${name}_peakFlux`]: (st.peakAbs < 0 ? '' : st.peakFlux),
        };
      };

      const b114_89 = summarizeBus('bus114_89');
      const b114_79 = summarizeBus('bus114_79');
      const b136_89 = summarizeBus('bus136_89');
      const b136_79 = summarizeBus('bus136_79');

      const summary = {
        schema: this.version,
        runId, runIndex, repIndex,
        wantId,
        portA: ports[0], portB: ports[1], portC: ports[2], portD: ports[3],
        pressC, baseDamp, pressMult, dampMult,
        dt: this.cfg.dt, everyMs: this.cfg.everyMs, windowMs: this.cfg.windowMs,

        // Global peaks
        peakSumAbsFlux,
        peakAtMs: Math.round(peakAtMs),
        peakMeanAbsP,
        peakMaxAbsEdgeFlux,
        peakEdgeIndex,
        peakEdgeFrom,
        peakEdgeTo,
        peakEdgeFlux,
        peakConcentration,

        // Pressure stats
        pCrashAtMs,
        pMin,

        // Bus summaries
        ...b114_89, ...b114_79, ...b136_89, ...b136_79,

        // Timing/visibility
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
      if (!app) throw new Error('solPhase311_16e: SOLDashboard not found.');

      const phy = await this._waitForPhysics();
      this._freezeLiveLoop();

      // baseline at pack start
      this._baselineSnap = this._snapshotState(phy);

      const ui = this._readUiParams(app);
      const basePressC = (this.cfg.pressC == null) ? ui.pressC : this.cfg.pressC;
      const baseDamp0  = (this.cfg.baseDamp == null) ? ui.damp   : this.cfg.baseDamp;

      // Plan
      const plan = [];
      let idx = 0;
      for (const wantId of this.cfg.wantIds) {
        for (const dampMult of this.cfg.dampMults) {
          for (const pressMult of this.cfg.pressMults) {
            for (let rep = 1; rep <= this.cfg.repsPerCombo; rep++) {
              plan.push({ runIndex: idx++, repIndex: rep, wantId, dampMult, pressMult });
            }
          }
        }
      }

      const estMin = (plan.length * (this.cfg.windowMs / 1000)) / 60;
      const startIso = this._isoForFile(new Date());
      const baseName = `${this.cfg.filenameBase}_${startIso}`;

      console.log(`🧪 Phase 3.11.16e starting (${this.version})`);
      console.log(`Ports: [${this.cfg.ports.join(', ')}] | wantIds=${JSON.stringify(this.cfg.wantIds)}`);
      console.log(`Base UI: pressC≈${basePressC}, baseDamp≈${baseDamp0}`);
      console.log(`Sweep: dampMults=${JSON.stringify(this.cfg.dampMults)} | pressMults=${JSON.stringify(this.cfg.pressMults)} | repsPerCombo=${this.cfg.repsPerCombo}`);
      console.log(`Runs: ${plan.length} | Estimated ≈ ${estMin.toFixed(1)} minutes`);
      console.log(`Bus thresh: |flux| >= ${this.cfg.busOnAbsFluxThresh}`);

      const summaryHeader = [
        'schema','runId','runIndex','repIndex',
        'wantId',
        'portA','portB','portC','portD',
        'pressC','baseDamp','pressMult','dampMult',
        'dt','everyMs','windowMs',
        'peakSumAbsFlux','peakAtMs','peakMeanAbsP',
        'peakMaxAbsEdgeFlux','peakEdgeIndex','peakEdgeFrom','peakEdgeTo','peakEdgeFlux','peakConcentration',
        'pCrashAtMs','pMin',

        // bus114_89
        'bus114_89_idx','bus114_89_onFirstAtMs','bus114_89_onTicks','bus114_89_onFrac','bus114_89_peakAbs','bus114_89_peakAtMs','bus114_89_peakFlux',
        // bus114_79
        'bus114_79_idx','bus114_79_onFirstAtMs','bus114_79_onTicks','bus114_79_onFrac','bus114_79_peakAbs','bus114_79_peakAtMs','bus114_79_peakFlux',
        // bus136_89
        'bus136_89_idx','bus136_89_onFirstAtMs','bus136_89_onTicks','bus136_89_onFrac','bus136_89_peakAbs','bus136_89_peakAtMs','bus136_89_peakFlux',
        // bus136_79
        'bus136_79_idx','bus136_79_onFirstAtMs','bus136_79_onTicks','bus136_79_onFrac','bus136_79_peakAbs','bus136_79_peakAtMs','bus136_79_peakFlux',

        // timing/vis
        'visibilityStateStart','wasHidden',
        'lateAbsAvgMs','lateAbsP95Ms','lateAbsMaxMs','missedTicks'
      ];

      const traceHeader = [
        'schema','runId','runIndex','repIndex',
        'wantId',
        'pressC','baseDamp','pressMult','dampMult',
        'tick','tMs','lateByMs',
        'basin',
        'sumAbsFlux','meanAbsP',
        'maxAbsEdgeFlux','maxEdgeIndex','maxEdgeFrom','maxEdgeTo','maxEdgeFlux','concentration',
        'flux_114_89','flux_114_79','flux_136_89','flux_136_79'
      ];

      const summaryLines = [ this._csvRow(summaryHeader) ];
      const traceLines = [ this._csvRow(traceHeader) ];

      try {
        for (let i = 0; i < plan.length; i++) {
          if (this._stopFlag) break;
          if (i % 20 === 0) console.log(`Progress: ${i}/${plan.length} | hidden=${document.hidden}`);

          const r = plan[i];
          const pressC = basePressC * r.pressMult;
          const baseDamp = baseDamp0 * r.dampMult;

          const out = await this._runOne({
            runIndex: r.runIndex,
            repIndex: r.repIndex,
            wantId: r.wantId,
            pressC,
            baseDamp,
            pressMult: r.pressMult,
            dampMult: r.dampMult
          });

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
      this._downloadText(`${base2}_MASTER_busTrace.csv`, traceLines.join(''));

      console.log('✅ Phase 3.11.16e complete:', base2);
      return { baseName: base2, runsPlanned: plan.length, stopped: this._stopFlag };
    }
  };

  window.solPhase311_16e = solPhase311_16e;
  console.log(`✅ solPhase311_16e installed (${solPhase311_16e.version}). Run: solPhase311_16e.runPack()`);

})();
