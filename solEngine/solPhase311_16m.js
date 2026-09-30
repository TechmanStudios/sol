/* Phase 3.11.16m — Fine Boundary Sigmoid Map v1

Goal:
  Precisely map the metastable boundary (ampB=4 fixed) by scanning ampD
  in fine steps and measuring:
   - outcome (none vs bothOn)
   - onset ticks (delay distribution)
   - peak magnitudes
  PLUS: log pressC/baseDamp used so runs are apples-to-apples across packs.

Design (~22–23 min):
  - ampB_fixed = 4
  - ampD_list = 5.50..5.75 step 0.025  (11 values)
  - repsPerAmp = 10  => 110 runs
  - postTicks = 60   => 61 ticks/run
  - everyMs = 200 => 12.2 s/run => ~22.4 min

Outputs:
  - MASTER_summary.csv
  - MASTER_busTrace.csv

Run:
  solPhase311_16m.runPack()

Stop:
  solPhase311_16m.stop()
*/
(() => {
  "use strict";

  const solPhase311_16m = {
    version: "3.11.16m_fineBoundarySigmoidMap_v1",
    _stopFlag: false,
    stop() { this._stopFlag = true; console.warn("🛑 solPhase311_16m.stop(): stop flag set."); },

    cfg: {
      // ports
      B: 114,
      D: 136,

      // fine boundary scan
      ampB_fixed: 4,
      ampD_list: (() => {
        const vals = [];
        for (let x = 5.50; x <= 5.7500001; x += 0.025) vals.push(Number(x.toFixed(3)));
        return vals;
      })(),
      repsPerAmp: 10,

      // longer observation window for late onsets
      postTicks: 60,

      // physics + metronome
      dt: 0.12,
      everyMs: 200,
      spinWaitMs: 1.5,

      // Mode select (Order B latch)
      wantIds: [82],
      injectorIds: [90, 82],
      dreamBlocks: 15,
      dreamBlockSteps: 2,
      injectAmount: 120,
      finalWriteMult: 1,

      // bus edges (broadcast rails)
      busPairs: [
        { name: "bus114_89", from: 114, to: 89 },
        { name: "bus114_79", from: 114, to: 79 },
        { name: "bus136_89", from: 136, to: 89 },
        { name: "bus136_79", from: 136, to: 79 },
      ],
      busOnAbsFluxThresh: 1.0,

      // optional overrides (null reads from UI)
      baseDamp: null,
      pressC: null,

      filenameBase: "sol_phase311_16m_fineBoundarySigmoidMap_v1",
    },

    _sleep(ms) { return new Promise(r => setTimeout(r, ms)); },
    _isoForFile(d = new Date()) {
      const p = (n) => String(n).padStart(2, "0");
      return `${d.getUTCFullYear()}-${p(d.getUTCMonth()+1)}-${p(d.getUTCDate())}T${p(d.getUTCHours())}-${p(d.getUTCMinutes())}-${p(d.getUTCSeconds())}-${String(d.getUTCMilliseconds()).padStart(3,"0")}Z`;
    },
    _csvCell(v) {
      if (v === null || v === undefined) return "";
      const s = String(v);
      return /[",\n\r]/.test(s) ? `"${s.replace(/"/g,'""')}"` : s;
    },
    _csvRow(cols) { return cols.map(this._csvCell).join(",") + "\n"; },
    _downloadText(filename, text, mime = "text/csv") {
      const blob = new Blob([String(text)], { type: mime });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
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
      throw new Error("solPhase311_16m: timed out waiting for physics.");
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
      if (!app?.config) throw new Error("solPhase311_16m: App not ready.");
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
        const out = {};
        for (const k in n) {
          const v = n[k];
          if (typeof v === "number" && Number.isFinite(v)) out[k] = v;
          if (typeof v === "boolean" && (k === "isBattery" || k === "isConstellation")) out[k] = v;
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
          if (typeof v === "number" && Number.isFinite(v)) out[k] = v;
          if ((k === "from" || k === "to") && (typeof v === "number" || typeof v === "string")) out[k] = v;
          if (k === "background" && typeof v === "boolean") out[k] = v;
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
      if (!n) throw new Error(`solPhase311_16m: injector node not found: ${id}`);
      const amt = Math.max(0, Number(amount) || 0);
      n.rho += amt;
      try {
        if (n.isConstellation && typeof phy.reinforceSemanticStar === "function") {
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
      return Number.isFinite(e.flux) ? e.flux : 0;
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
      let maxEdgeFrom = "";
      let maxEdgeTo = "";
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
      try { if (typeof phy.computePressure === "function") phy.computePressure(pressC); } catch(e) {}
    },

    _metronomeFactory({ everyMs, ticks, spinWaitMs, onTick }) {
      const self = this;
      return (async () => {
        const start = performance.now();
        const absLates = [];
        let missedTicks = 0;

        for (let i = 0; i < ticks; i++) {
          if (self._stopFlag) break;
          const target = start + i * everyMs;

          while (true) {
            const now = performance.now();
            const remain = target - now;
            if (remain <= 0) break;
            if (spinWaitMs > 0 && remain <= spinWaitMs) break;
            await self._sleep(Math.min(50, Math.max(0, remain - (spinWaitMs > 0 ? spinWaitMs : 0))));
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
      })();
    },

    async _runOne({ runIndex, repIndex, wantId, pressC, baseDamp, ampB, ampD }) {
      const phy = await this._waitForPhysics();
      this._restoreState(phy, this._baselineSnap);

      await this._selectMode(phy, wantId, pressC, baseDamp);

      const edgeMap = this._buildEdgeIndexMap(phy);
      const bus = this.cfg.busPairs.map(b => ({
        ...b,
        idx: edgeMap.has(`${b.from}->${b.to}`) ? edgeMap.get(`${b.from}->${b.to}`) : -1
      }));

      const totalTicks = this.cfg.postTicks + 1;
      const windowMs = totalTicks * this.cfg.everyMs;

      const ampSum = ampB + ampD;
      const runId =
        `${this._isoForFile()}_r${String(runIndex).padStart(5,"0")}` +
        `_rep${repIndex}_want${wantId}_simul_ampB${ampB}_ampD${ampD}`;

      const visStart = document.visibilityState;
      let wasHidden = false;
      const onVis = () => { if (document.hidden) wasHidden = true; };
      document.addEventListener("visibilitychange", onVis, { passive: true });

      const thresh = this.cfg.busOnAbsFluxThresh;

      const bus114 = { onsetTick: null, peakAbs: -1, peakTick: null };
      const bus136 = { onsetTick: null, peakAbs: -1, peakTick: null };

      let peakSumAbsFlux = -1, peakSumAtTick = 0, peakSumAtMs = 0, peakSumMeanAbsP = 0;
      let peakMaxAbsEdgeFlux = -1, peakEdgeIndex = -1, peakEdgeFrom = "", peakEdgeTo = "", peakEdgeFlux = 0, peakConcentration = 0;

      const traceRows = [];

      const met = await this._metronomeFactory({
        everyMs: this.cfg.everyMs,
        ticks: totalTicks,
        spinWaitMs: this.cfg.spinWaitMs,
        onTick: async ({ tick, tMs, lateByMs }) => {
          if (tick === 0) {
            this._injectById(phy, this.cfg.B, ampB);
            this._injectById(phy, this.cfg.D, ampD);
          }

          phy.step(this.cfg.dt, pressC, baseDamp);

          const basin = this._pickBasin(phy);
          const g = this._computeGlobal(phy);

          if (g.sumAbsFlux > peakSumAbsFlux) {
            peakSumAbsFlux = g.sumAbsFlux;
            peakSumAtTick = tick;
            peakSumAtMs = tMs;
            peakSumMeanAbsP = g.meanAbsP;
          }
          if (g.maxAbsEdgeFlux > peakMaxAbsEdgeFlux) {
            peakMaxAbsEdgeFlux = g.maxAbsEdgeFlux;
            peakEdgeIndex = g.maxEdgeIndex;
            peakEdgeFrom = g.maxEdgeFrom;
            peakEdgeTo = g.maxEdgeTo;
            peakEdgeFlux = g.maxEdgeFlux;
            peakConcentration = g.concentration;
          }

          const f114_89 = (bus[0].idx >= 0) ? this._getEdgeFluxByIndex(phy, bus[0].idx) : 0;
          const f114_79 = (bus[1].idx >= 0) ? this._getEdgeFluxByIndex(phy, bus[1].idx) : 0;
          const f136_89 = (bus[2].idx >= 0) ? this._getEdgeFluxByIndex(phy, bus[2].idx) : 0;
          const f136_79 = (bus[3].idx >= 0) ? this._getEdgeFluxByIndex(phy, bus[3].idx) : 0;

          const a114 = Math.max(Math.abs(f114_89), Math.abs(f114_79));
          const a136 = Math.max(Math.abs(f136_89), Math.abs(f136_79));

          if (bus114.onsetTick == null && a114 >= thresh) bus114.onsetTick = tick;
          if (bus136.onsetTick == null && a136 >= thresh) bus136.onsetTick = tick;

          if (a114 > bus114.peakAbs) { bus114.peakAbs = a114; bus114.peakTick = tick; }
          if (a136 > bus136.peakAbs) { bus136.peakAbs = a136; bus136.peakTick = tick; }

          traceRows.push(this._csvRow([
            this.version, runId, runIndex, repIndex, wantId,
            pressC, baseDamp, thresh,
            ampB, ampD, ampSum,
            tick, Math.round(tMs), lateByMs.toFixed(3),
            basin,
            g.sumAbsFlux.toFixed(6), g.meanAbsP.toFixed(6),
            g.maxAbsEdgeFlux.toFixed(6), g.maxEdgeIndex, g.maxEdgeFrom, g.maxEdgeTo, g.maxEdgeFlux.toFixed(6), g.concentration.toFixed(6),
            f114_89.toFixed(6), f114_79.toFixed(6), f136_89.toFixed(6), f136_79.toFixed(6)
          ]));
        }
      });

      document.removeEventListener("visibilitychange", onVis);

      const on114 = (bus114.onsetTick != null);
      const on136 = (bus136.onsetTick != null);
      const outcome = on114 && on136 ? "bothOn" : (on114 ? "only114" : (on136 ? "only136" : "none"));

      const winner = (!on114 && !on136) ? "none"
        : (on114 && !on136) ? "114"
        : (!on114 && on136) ? "136"
        : (bus114.onsetTick < bus136.onsetTick) ? "114"
        : (bus136.onsetTick < bus114.onsetTick) ? "136"
        : "tie";

      const summary = {
        schema: this.version,
        runId,
        runIndex,
        repIndex,
        wantId,

        pressCUsed: pressC,
        baseDampUsed: baseDamp,
        busThreshUsed: thresh,

        ampB,
        ampD,
        ampSum,

        totalTicks,
        windowMs,
        dt: this.cfg.dt,
        everyMs: this.cfg.everyMs,

        onset114_tick: bus114.onsetTick ?? "",
        peak114_tick: bus114.peakTick ?? "",
        peak114_abs: bus114.peakAbs,

        onset136_tick: bus136.onsetTick ?? "",
        peak136_tick: bus136.peakTick ?? "",
        peak136_abs: bus136.peakAbs,

        outcome,
        winner,

        peakSumAbsFlux,
        peakSumAtTick,
        peakSumAtMs: Math.round(peakSumAtMs),
        peakSumMeanAbsP,
        peakMaxAbsEdgeFlux,
        peakEdgeIndex,
        peakEdgeFrom,
        peakEdgeTo,
        peakEdgeFlux,
        peakConcentration,

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
      if (userCfg && typeof userCfg === "object") this.cfg = { ...this.cfg, ...userCfg };

      const app = this._getApp();
      if (!app) throw new Error("solPhase311_16m: SOLDashboard not found.");

      const phy = await this._waitForPhysics();
      this._freezeLiveLoop();

      this._baselineSnap = this._snapshotState(phy);

      const ui = this._readUiParams(app);
      const pressC = (this.cfg.pressC == null) ? ui.pressC : this.cfg.pressC;
      const baseDamp = (this.cfg.baseDamp == null) ? ui.damp : this.cfg.baseDamp;

      const plan = [];
      let idx = 0;
      for (const wantId of this.cfg.wantIds) {
        for (const ampD of this.cfg.ampD_list) {
          for (let rep = 1; rep <= this.cfg.repsPerAmp; rep++) {
            plan.push({
              runIndex: idx++,
              repIndex: rep,
              wantId,
              ampB: this.cfg.ampB_fixed,
              ampD
            });
          }
        }
      }

      const startIso = this._isoForFile(new Date());
      const baseName = `${this.cfg.filenameBase}_${startIso}`;

      console.log(`🧪 Phase 3.11.16m starting (${this.version})`);
      console.log(`runs=${plan.length} | ampB_fixed=${this.cfg.ampB_fixed} | ampD_list=${JSON.stringify(this.cfg.ampD_list)} | reps=${this.cfg.repsPerAmp}`);
      console.log(`UI params used: pressC≈${pressC}, baseDamp≈${baseDamp}, busThresh=${this.cfg.busOnAbsFluxThresh}`);

      // probe
      const probe = await this._runOne({
        runIndex: 0, repIndex: 1, wantId: this.cfg.wantIds[0],
        pressC, baseDamp,
        ampB: this.cfg.ampB_fixed,
        ampD: this.cfg.ampD_list[0]
      });
      this._restoreState(phy, this._baselineSnap);

      const summaryHeader = Object.keys(probe.summary);
      const traceHeader = [
        "schema","runId","runIndex","repIndex","wantId",
        "pressCUsed","baseDampUsed","busThreshUsed",
        "ampB","ampD","ampSum",
        "tick","tMs","lateByMs","basin",
        "sumAbsFlux","meanAbsP",
        "maxAbsEdgeFlux","maxEdgeIndex","maxEdgeFrom","maxEdgeTo","maxEdgeFlux","concentration",
        "flux_114_89","flux_114_79","flux_136_89","flux_136_79"
      ];

      const summaryLines = [ this._csvRow(summaryHeader) ];
      const traceLines = [ this._csvRow(traceHeader) ];

      try {
        for (let i = 0; i < plan.length; i++) {
          if (this._stopFlag) break;
          if (i % 20 === 0) console.log(`Progress: ${i}/${plan.length} | hidden=${document.hidden}`);

          const r = plan[i];
          const out = await this._runOne({
            runIndex: r.runIndex,
            repIndex: r.repIndex,
            wantId: r.wantId,
            pressC,
            baseDamp,
            ampB: r.ampB,
            ampD: r.ampD
          });

          const s = out.summary;
          summaryLines.push(this._csvRow(summaryHeader.map(k => (k in s ? s[k] : ""))));
          for (const row of out.traceRows) traceLines.push(row);
        }
      } finally {
        this._unfreezeLiveLoop();
      }

      const endIso = this._isoForFile(new Date());
      const base2 = `${baseName}_${endIso}`;

      this._downloadText(`${base2}_MASTER_summary.csv`, summaryLines.join(""));
      this._downloadText(`${base2}_MASTER_busTrace.csv`, traceLines.join(""));

      console.log("✅ Phase 3.11.16m complete:", base2);
      return { baseName: base2, runsPlanned: plan.length, stopped: this._stopFlag };
    }
  };

  window.solPhase311_16m = solPhase311_16m;
  console.log(`✅ solPhase311_16m installed (${solPhase311_16m.version}). Run: solPhase311_16m.runPack()`);

})();
