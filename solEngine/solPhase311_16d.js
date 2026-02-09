/* Phase 3.11.16d — Filament Threshold Sweep v1 (RR_ABCD, ports [107,114,118,136])
   Purpose:
     Map when/if the flux filament (edge 136→89, paired with 136→79) appears as a function of baseDamp and pressC.

   Run:
     solPhase311_16d.runPack()

   Stop:
     solPhase311_16d.stop()

   Notes:
     - UI-neutral (no camera/graph moves)
     - Full baseline restore each run
     - Filament-only events CSV to keep file sizes sane
*/
(() => {
  'use strict';

  const solPhase311_16d = {
    version: '3.11.16d_filamentThresholdSweep_v1',
    _stopFlag: false,
    stop() { this._stopFlag = true; console.warn('🛑 solPhase311_16d.stop(): stop flag set.'); },

    cfg: {
      // Target runtime ~24 min by default:
      // combos = 5 dampMults * 3 pressMults = 15
      // repsPerCombo = 12 => 180 runs * 8s ≈ 24 min (+ overhead)
      repsPerCombo: 12,

      // Fixed I/O topology (the one that produced the filament in 6c)
      ports: [107, 114, 118, 136],
      wantIds: [82], // default: focus on want82. (You can set to [82,90] if desired.)

      // Mode-select (Order B)
      injectorIds: [90, 82],
      dreamBlocks: 15,
      dreamBlockSteps: 2,
      injectAmount: 120,
      finalWriteMult: 1,

      // Timing / integration
      dt: 0.12,
      everyMs: 200,
      spinWaitMs: 1.5,
      windowMs: 8000,

      // Parameter sweep around observed baseline (pressC≈2, baseDamp≈5)
      dampMults: [0.6, 0.8, 1.0, 1.2, 1.4],
      pressMults: [0.75, 1.0, 1.25],

      // Filament definition (max-edge identity)
      filamentFrom: 136,
      filamentTos: [89, 79],  // paired rail (almost always both)
      // Optional: ignore extremely tiny “wins” (keeps noise down)
      filamentMinAbsFlux: 1.0,

      // If you want extra event logging beyond filament moments, raise/lower this
      logTopKEdges: 5,

      filenameBase: 'sol_phase311_16d_filamentThresholdSweep_v1',

      // UI read if null
      baseDamp: null,
      pressC: null,
    },

    // ---------- utils ----------
    _sleep(ms) { return new Promise(r => setTimeout(r, ms)); },
    _isoForFile(d = new Date()) {
      const p = (n) => String(n).padStart(2, '0');
      return `${d.getUTCFullYear()}-${p(d.getUTCMonth()+1)}-${p(d.getUTCDate())}T${p(d.getUTCHours())}-${p(d.getUTCMinutes())}-${p(d.getUTCSeconds())}-${String(d.getUTCMilliseconds()).padStart(3,'0')}Z`;
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
      setTimeout(() => { try { URL.revokeObjectURL(url); } catch(e){} }, 250);
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
      throw new Error('solPhase311_16d: timed out waiting for physics.');
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
      if (!app?.config) throw new Error('solPhase311_16d: App not ready.');
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
      for (const n of (phy?.nodes || [])) {
        if (n?.id != null && String(n.id) === want) return n;
      }
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
      if (!n) throw new Error(`solPhase311_16d: injector node not found: ${id}`);
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

    _topKEdges(phy, k = 5) {
      const edges = phy.edges || [];
      const arr = [];
      for (let i = 0; i < edges.length; i++) {
        const e = edges[i];
        if (!e || e.background) continue;
        const f = Number.isFinite(e.flux) ? e.flux : 0;
        arr.push({ i, from: e.from, to: e.to, flux: f, abs: Math.abs(f) });
      }
      arr.sort((a, b) => b.abs - a.abs);
      return arr.slice(0, k).map(e => `${e.i}:${e.from}->${e.to}:${e.flux.toFixed(4)}`).join(' | ');
    },

    _isFilamentEdge(from, to) {
      const c = this.cfg;
      if (!Number.isFinite(+from) || !Number.isFinite(+to)) return false;
      const f = +from, t = +to;
      if (f === c.filamentFrom && c.filamentTos.includes(t)) return true;
      // also allow reverse, just in case a parameter regime flips direction
      if (t === c.filamentFrom && c.filamentTos.includes(f)) return true;
      return false;
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

      const ports = this.cfg.ports;
      const ticks = Math.max(1, Math.round(this.cfg.windowMs / this.cfg.everyMs));
      const runId =
        `${this._isoForFile()}_r${String(runIndex).padStart(5,'0')}` +
        `_rep${repIndex}_want${wantId}_pM${pressMult}_dM${dampMult}`;

      const visStart = document.visibilityState;
      let wasHidden = false;
      const onVis = () => { if (document.hidden) wasHidden = true; };
      document.addEventListener('visibilitychange', onVis, { passive: true });

      // Peaks (global)
      let peakSumAbsFlux = -1, peakAtMs = 0, peakMeanAbsP = 0;
      let peakMaxAbsEdgeFlux = -1, peakEdgeIndex = -1, peakEdgeFrom = '', peakEdgeTo = '', peakEdgeFlux = 0, peakConcentration = 0;

      // Filament stats
      let filamentSeen = 0;
      let filamentFirstAtMs = '';
      let filamentEventCount = 0;
      let filamentPeakAbs = -1;
      let filamentPeakAtMs = 0;
      let filamentPeakEdgeFrom = '';
      let filamentPeakEdgeTo = '';
      let filamentPeakEdgeFlux = 0;
      let filamentPeakConcentration = 0;
      let filamentPeakSumAbsFlux = 0;
      let filamentPeakMeanAbsP = 0;

      let pCrashAtMs = '';
      let pMin = Infinity;

      const eventRows = [];

      const met = await this._metronome({
        everyMs: this.cfg.everyMs,
        ticks,
        spinWaitMs: this.cfg.spinWaitMs,
        onTick: async ({ tick, tMs, lateByMs }) => {
          // Inject message for first 4 ticks
          const inj = this._messagePlan_RR_ABCD(tick);
          for (let k = 0; k < 4; k++) {
            const amt = inj[k] || 0;
            if (amt > 0) this._injectById(phy, ports[k], amt);
          }

          phy.step(this.cfg.dt, pressC, baseDamp);

          const basin = this._pickBasin(phy);
          const tot = this._computeTotals(phy);

          // Global peaks
          if (tot.sumAbsFlux > peakSumAbsFlux) {
            peakSumAbsFlux = tot.sumAbsFlux;
            peakAtMs = tMs;
            peakMeanAbsP = tot.meanAbsP;
          }
          if (tot.maxAbsEdgeFlux > peakMaxAbsEdgeFlux) {
            peakMaxAbsEdgeFlux = tot.maxAbsEdgeFlux;
            peakEdgeIndex = tot.maxEdgeIndex;
            peakEdgeFrom = tot.maxEdgeFrom;
            peakEdgeTo = tot.maxEdgeTo;
            peakEdgeFlux = tot.maxEdgeFlux;
            peakConcentration = tot.concentration;
          }

          // Pressure min / crash
          pMin = Math.min(pMin, tot.meanAbsP);
          if (pCrashAtMs === '' && tot.meanAbsP < 0.015 && tMs > 500) {
            pCrashAtMs = Math.round(tMs);
          }

          // Filament detection (max-edge identity)
          const isFil = this._isFilamentEdge(tot.maxEdgeFrom, tot.maxEdgeTo) && (tot.maxAbsEdgeFlux >= this.cfg.filamentMinAbsFlux);

          if (isFil) {
            filamentSeen = 1;
            filamentEventCount++;
            if (filamentFirstAtMs === '') filamentFirstAtMs = Math.round(tMs);

            if (tot.maxAbsEdgeFlux > filamentPeakAbs) {
              filamentPeakAbs = tot.maxAbsEdgeFlux;
              filamentPeakAtMs = tMs;
              filamentPeakEdgeFrom = tot.maxEdgeFrom;
              filamentPeakEdgeTo = tot.maxEdgeTo;
              filamentPeakEdgeFlux = tot.maxEdgeFlux;
              filamentPeakConcentration = tot.concentration;
              filamentPeakSumAbsFlux = tot.sumAbsFlux;
              filamentPeakMeanAbsP = tot.meanAbsP;
            }

            // Log filament event row (optionally with topK edges)
            const top = this.cfg.logTopKEdges > 0 ? this._topKEdges(phy, this.cfg.logTopKEdges) : '';
            eventRows.push(this._csvRow([
              this.version, runId, runIndex, repIndex,
              wantId,
              pressC, baseDamp, pressMult, dampMult,
              tick, Math.round(tMs), lateByMs.toFixed(3),
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
        }
      });

      document.removeEventListener('visibilitychange', onVis);

      const summary = {
        schema: this.version,
        runId, runIndex, repIndex,
        wantId,
        portA: ports[0], portB: ports[1], portC: ports[2], portD: ports[3],
        pressC, baseDamp, pressMult, dampMult,
        dt: this.cfg.dt, everyMs: this.cfg.everyMs, windowMs: this.cfg.windowMs,

        // Global peaks
        peakSumAbsFlux, peakAtMs: Math.round(peakAtMs), peakMeanAbsP,
        peakMaxAbsEdgeFlux, peakEdgeIndex, peakEdgeFrom, peakEdgeTo, peakEdgeFlux, peakConcentration,

        // Filament stats
        filamentSeen,
        filamentFirstAtMs,
        filamentEventCount,
        filamentPeakAbs: (filamentPeakAbs < 0 ? '' : filamentPeakAbs),
        filamentPeakAtMs: (filamentPeakAbs < 0 ? '' : Math.round(filamentPeakAtMs)),
        filamentPeakEdgeFrom,
        filamentPeakEdgeTo,
        filamentPeakEdgeFlux: (filamentPeakAbs < 0 ? '' : filamentPeakEdgeFlux),
        filamentPeakConcentration: (filamentPeakAbs < 0 ? '' : filamentPeakConcentration),
        filamentPeakSumAbsFlux: (filamentPeakAbs < 0 ? '' : filamentPeakSumAbsFlux),
        filamentPeakMeanAbsP: (filamentPeakAbs < 0 ? '' : filamentPeakMeanAbsP),

        // Pressure stats
        pCrashAtMs,
        pMin,

        // Timing / visibility
        visibilityStateStart: visStart,
        wasHidden,
        lateAbsAvgMs: met.lateAbsAvg,
        lateAbsP95Ms: met.lateAbsP95,
        lateAbsMaxMs: met.lateAbsMax,
        missedTicks: met.missedTicks
      };

      return { summary, eventRows };
    },

    async runPack(userCfg = {}) {
      this._stopFlag = false;
      if (userCfg && typeof userCfg === 'object') this.cfg = { ...this.cfg, ...userCfg };

      const app = this._getApp();
      if (!app) throw new Error('solPhase311_16d: SOLDashboard not found.');

      const phy = await this._waitForPhysics();
      this._freezeLiveLoop();

      // Belt + suspenders: capture baseline at pack start, and restore it before each run
      this._baselineSnap = this._snapshotState(phy);

      const ui = this._readUiParams(app);
      const basePressC = (this.cfg.pressC == null) ? ui.pressC : this.cfg.pressC;
      const baseDamp0  = (this.cfg.baseDamp == null) ? ui.damp   : this.cfg.baseDamp;

      // Build run plan
      const plan = [];
      let idx = 0;

      for (const wantId of this.cfg.wantIds) {
        for (const dampMult of this.cfg.dampMults) {
          for (const pressMult of this.cfg.pressMults) {
            for (let rep = 1; rep <= this.cfg.repsPerCombo; rep++) {
              plan.push({
                runIndex: idx++,
                repIndex: rep,
                wantId,
                dampMult,
                pressMult,
              });
            }
          }
        }
      }

      const estMin = (plan.length * (this.cfg.windowMs / 1000)) / 60;
      const startIso = this._isoForFile(new Date());
      const baseName = `${this.cfg.filenameBase}_${startIso}`;

      console.log(`🧪 Phase 3.11.16d starting (${this.version})`);
      console.log(`Ports: [${this.cfg.ports.join(', ')}] | wantIds=${JSON.stringify(this.cfg.wantIds)}`);
      console.log(`Base UI: pressC≈${basePressC}, baseDamp≈${baseDamp0}`);
      console.log(`Sweep: dampMults=${JSON.stringify(this.cfg.dampMults)} | pressMults=${JSON.stringify(this.cfg.pressMults)} | repsPerCombo=${this.cfg.repsPerCombo}`);
      console.log(`Runs: ${plan.length} | Estimated ≈ ${estMin.toFixed(1)} minutes`);
      console.log(`Filament definition: max-edge from ${this.cfg.filamentFrom} to any of ${JSON.stringify(this.cfg.filamentTos)} (minAbsFlux=${this.cfg.filamentMinAbsFlux})`);

      const summaryHeader = [
        'schema','runId','runIndex','repIndex',
        'wantId',
        'portA','portB','portC','portD',
        'pressC','baseDamp','pressMult','dampMult',
        'dt','everyMs','windowMs',
        'peakSumAbsFlux','peakAtMs','peakMeanAbsP',
        'peakMaxAbsEdgeFlux','peakEdgeIndex','peakEdgeFrom','peakEdgeTo','peakEdgeFlux','peakConcentration',
        'filamentSeen','filamentFirstAtMs','filamentEventCount',
        'filamentPeakAbs','filamentPeakAtMs','filamentPeakEdgeFrom','filamentPeakEdgeTo','filamentPeakEdgeFlux',
        'filamentPeakConcentration','filamentPeakSumAbsFlux','filamentPeakMeanAbsP',
        'pCrashAtMs','pMin',
        'visibilityStateStart','wasHidden',
        'lateAbsAvgMs','lateAbsP95Ms','lateAbsMaxMs','missedTicks'
      ];

      const eventsHeader = [
        'schema','runId','runIndex','repIndex',
        'wantId',
        'pressC','baseDamp','pressMult','dampMult',
        'tick','tMs','lateByMs',
        'basin',
        'sumAbsFlux','meanAbsP',
        'maxAbsEdgeFlux','maxEdgeIndex','maxEdgeFrom','maxEdgeTo','maxEdgeFlux','concentration',
        'topKEdges'
      ];

      const summaryLines = [ this._csvRow(summaryHeader) ];
      const eventLines = [ this._csvRow(eventsHeader) ];

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
          for (const row of out.eventRows) eventLines.push(row);
        }
      } finally {
        this._unfreezeLiveLoop();
      }

      const endIso = this._isoForFile(new Date());
      const base2 = `${baseName}_${endIso}`;

      this._downloadText(`${base2}_MASTER_summary.csv`, summaryLines.join(''));
      this._downloadText(`${base2}_MASTER_filamentEvents.csv`, eventLines.join(''));

      console.log('✅ Phase 3.11.16d complete:', base2);
      return { baseName: base2, runsPlanned: plan.length, stopped: this._stopFlag };
    }
  };

  window.solPhase311_16d = solPhase311_16d;
  console.log(`✅ solPhase311_16d installed (${solPhase311_16d.version}). Run: solPhase311_16d.runPack()`);

})();
