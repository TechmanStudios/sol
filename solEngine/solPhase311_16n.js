/* Phase 3.11.16n_v2 — Readout Robustness (16m-core)
   Fixes:
     - Uses 16m-style _injectById (node.rho += amt) instead of physics.inject()
     - Uses 16m-style _selectMode (dreamBlocks priming) before each run
     - Uses 16m-style metronome timing loop

   Goal:
     Hold ampD near the boundary (default 5.5125), sweep:
       - baseDampUsed ± 1
       - pressCUsed × [0.8, 1.0, 1.2]
     reps per cell to estimate sensitivity.

   Outputs:
     - ..._MASTER_summary.csv
     - ..._MASTER_busTrace.csv

   Run:
     solPhase311_16n_v2.runPack()

   Stop:
     solPhase311_16n_v2.stop()
*/
(() => {
  "use strict";

  const solPhase311_16n_v2 = {
    version: "3.11.16n_v2_readoutRobustness_v1",

    cfg: {
      // ports
      B: 114,
      D: 136,

      // hold point (override if needed)
      ampB_fixed: 4.0,
      ampD_fixed: 5.5125,

      // robustness grid
      pressCMults: [0.8, 1.0, 1.2],
      dampOffsets: [-1, 0, 1],
      repsPerCell: 20,

      // observation window
      postTicks: 60,     // => 61 ticks
      everyMs: 200,
      spinWaitMs: 1.5,

      // mode select (copied from 16m)
      wantIds: [82],
      injectorIds: [90, 82],
      dreamBlocks: 15,
      dreamBlockSteps: 2,
      injectAmount: 120,
      finalWriteMult: 1,

      // bus rails
      busPairs: [
        { name: "bus114_89", from: 114, to: 89 },
        { name: "bus114_79", from: 114, to: 79 },
        { name: "bus136_89", from: 136, to: 89 },
        { name: "bus136_79", from: 136, to: 79 },
      ],
      busOnAbsFluxThresh: 1.0,

      // dt + optional overrides (null reads UI)
      dt: 0.12,
      baseDamp: null,
      pressC: null,

      // filename
      filenameBase: "sol_phase311_16n_v2_readoutRobustness_v1",

      // quick preflight (saves you from burning an hour in the wrong regime)
      preflight: {
        enabled: true,
        reps: 3,
        testAmpD: 5.525, // should be "sure on" in the 16m regime
      }
    },

    _stopFlag: false,
    stop() { this._stopFlag = true; },

    _sleep(ms) { return new Promise(r => setTimeout(r, ms)); },

    _isoForFile(d = new Date()) {
      const p2 = (n) => String(n).padStart(2, "0");
      const p3 = (n) => String(n).padStart(3, "0");
      return `${d.getUTCFullYear()}-${p2(d.getUTCMonth()+1)}-${p2(d.getUTCDate())}T${p2(d.getUTCHours())}-${p2(d.getUTCMinutes())}-${p2(d.getUTCSeconds())}-${p3(d.getUTCMilliseconds())}Z`;
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
      setTimeout(() => { try { URL.revokeObjectURL(url); } catch(e) {} }, 250);
    },

    _getApp() {
      return window.SOLDashboard || window.solDashboard || window.App || null;
    },

    async _waitForPhysics(timeoutMs = 15000, pollMs = 50) {
      const start = performance.now();
      while ((performance.now() - start) < timeoutMs) {
        const app = this._getApp();
        const phy =
          (window.solver && window.solver.nodes && window.solver.edges) ? window.solver :
          (app && app.state && app.state.physics) ? app.state.physics :
          null;
        if (phy?.nodes?.length && phy?.edges?.length) return phy;
        await this._sleep(pollMs);
      }
      throw new Error("solPhase311_16n_v2: timed out waiting for physics.");
    },

    _freezeLiveLoop() {
      const app = this._getApp();
      if (!app?.config) throw new Error("solPhase311_16n_v2: App not ready.");
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

    _readUiParams(app) {
      const pressC = (app?.dom?.pressureSlider)
        ? (parseFloat(String(app.dom.pressureSlider.value)) * (app.config.pressureSliderScale || 1))
        : 2;
      const damp = (app?.dom?.dampSlider)
        ? parseFloat(String(app.dom.dampSlider.value))
        : 5;
      return {
        pressC: Number.isFinite(pressC) ? pressC : 2,
        damp: Number.isFinite(damp) ? damp : 5,
      };
    },

    _nodeByIdLoose(phy, id) {
      const direct = (phy?.nodeById?.get) ? phy.nodeById.get(id) : null;
      if (direct) return direct;
      const want = String(id);
      for (const n of (phy?.nodes || [])) if (n?.id != null && String(n.id) === want) return n;
      return null;
    },

    _snapshotState(phy) {
      // minimal, robust snapshot (same style as 16m)
      const nodes = [];
      for (const n of (phy.nodes || [])) {
        if (!n || n.id == null) continue;
        nodes.push([n.id, {
          rho: n.rho, p: n.p, psi: n.psi, psi_bias: n.psi_bias,
          semanticMass: n.semanticMass, semanticMass0: n.semanticMass0,
          b_q: n.b_q, b_charge: n.b_charge, b_state: n.b_state
        }]);
      }
      const edges = [];
      for (let i = 0; i < (phy.edges || []).length; i++) {
        const e = phy.edges[i];
        if (!e) { edges.push([i, {}]); continue; }
        edges.push([i, { flux: e.flux }]);
      }
      return {
        nodePairs: nodes,
        edgePairs: edges,
        globalBias: (typeof phy.globalBias === "number" && Number.isFinite(phy.globalBias)) ? phy.globalBias : 0,
      };
    },

    _restoreState(phy, snap) {
      if (!snap) return;

      const nodeMap = new Map(snap.nodePairs || []);
      for (const n of (phy.nodes || [])) {
        if (!n || n.id == null) continue;
        const s = nodeMap.get(n.id);
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

      try { phy.globalBias = snap.globalBias || 0; } catch(e) {}
    },

    _injectById(phy, id, amount) {
      const n = this._nodeByIdLoose(phy, id);
      if (!n) throw new Error(`solPhase311_16n_v2: injector node not found: ${id}`);
      const amt = Math.max(0, Number(amount) || 0);
      n.rho += amt;

      // optional semantic reinforcement (matches 16m behavior)
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
      const f = (e && typeof e.flux === "number" && Number.isFinite(e.flux)) ? e.flux : 0;
      return f;
    },

    _computeGlobal(phy) {
      const edges = phy.edges || [];
      const nodes = phy.nodes || [];

      let meanAbsP = 0;
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

      for (let i = 0; i < edges.length; i++) {
        const e = edges[i];
        if (!e || e.background) continue;
        const f = (typeof e.flux === "number" && Number.isFinite(e.flux)) ? e.flux : 0;
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
      const concentration = (sumAbsFlux > 0) ? (maxAbsEdgeFlux / sumAbsFlux) : 0;

      return { sumAbsFlux, meanAbsP, maxAbsEdgeFlux, maxEdgeIndex, maxEdgeFrom, maxEdgeTo, maxEdgeFlux, concentration };
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
            await self._sleep(Math.min(10, Math.max(0, remain - (spinWaitMs || 0))));
          }

          // spin-wait near target
          while (true) {
            const now = performance.now();
            if (now >= target) break;
          }

          const now = performance.now();
          const lateByMs = now - target;
          absLates.push(Math.abs(lateByMs));

          // crude missed tick indicator
          if (i > 0 && absLates.length >= 2) {
            const prevTarget = start + (i - 1) * everyMs;
            const prevLate = absLates[absLates.length - 2];
            const prevActual = prevTarget + (prevLate * (lateByMs >= 0 ? 1 : 1));
            const gap = (target + lateByMs) - prevActual;
            if (gap > everyMs * 1.5) missedTicks += 1;
          }

          await onTick({ tick: i, tMs: (now - start), lateByMs });
        }

        // late stats
        const a = absLates.slice().sort((x,y)=>x-y);
        const avg = a.length ? a.reduce((s,v)=>s+v,0)/a.length : 0;
        const p95 = a.length ? a[Math.floor(0.95 * (a.length - 1))] : 0;
        const max = a.length ? a[a.length - 1] : 0;

        return { lateAbsAvg: avg, lateAbsP95: p95, lateAbsMax: max, missedTicks };
      })();
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
        `_rep${repIndex}_want${wantId}_robust_pC${pressC}_d${baseDamp}_ampD${ampD}`;

      const visStart = document.visibilityState;
      let wasHidden = false;
      const onVis = () => { if (document.hidden) wasHidden = true; };
      document.addEventListener("visibilitychange", onVis, { passive: true });

      const thresh = this.cfg.busOnAbsFluxThresh;

      const bus114 = { onsetTick: null, peakAbs: -1, peakTick: null };
      const bus136 = { onsetTick: null, peakAbs: -1, peakTick: null };

      let peakSumAbsFlux = -1, peakSumAtTick = null, peakSumAtMs = null, peakSumMeanAbsP = null;
      let peakMaxAbsEdgeFlux = -1, peakEdgeIndex = null, peakEdgeFrom = "", peakEdgeTo = "", peakEdgeFlux = 0, peakConcentration = 0;

      const traceRows = [];
      let leader0_from = "", leader0_to = "";

      const timing = await this._metronomeFactory({
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

          if (tick === 0) { leader0_from = g.maxEdgeFrom; leader0_to = g.maxEdgeTo; }

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
            tick, tMs, lateByMs, basin,
            g.sumAbsFlux, g.meanAbsP,
            g.maxAbsEdgeFlux, g.maxEdgeIndex, g.maxEdgeFrom, g.maxEdgeTo, g.maxEdgeFlux, g.concentration,
            f114_89, f114_79, f136_89, f136_79
          ]));
        }
      });

      document.removeEventListener("visibilitychange", onVis);

      const has114 = (bus114.onsetTick != null);
      const has136 = (bus136.onsetTick != null);

      let outcome = "none";
      if (has114 && has136) outcome = "bothOn";
      else if (has114) outcome = "only114";
      else if (has136) outcome = "only136";

      let winner = "none";
      if (has114 && has136) {
        if (bus114.onsetTick < bus136.onsetTick) winner = "114";
        else if (bus136.onsetTick < bus114.onsetTick) winner = "136";
        else winner = "tie";
      }

      const summary = {
        schema: this.version,
        runId, runIndex, repIndex, wantId,
        pressCUsed: pressC, baseDampUsed: baseDamp, busThreshUsed: thresh,
        ampB, ampD, ampSum,
        totalTicks, windowMs, dt: this.cfg.dt, everyMs: this.cfg.everyMs,
        onset114_tick: bus114.onsetTick,
        peak114_tick: bus114.peakTick, peak114_abs: bus114.peakAbs,
        onset136_tick: bus136.onsetTick,
        peak136_tick: bus136.peakTick, peak136_abs: bus136.peakAbs,
        outcome, winner,
        peakSumAbsFlux, peakSumAtTick, peakSumAtMs, peakSumMeanAbsP,
        peakMaxAbsEdgeFlux, peakEdgeIndex, peakEdgeFrom, peakEdgeTo, peakEdgeFlux, peakConcentration,
        visibilityStateStart: visStart, wasHidden,
        lateAbsAvgMs: timing.lateAbsAvg, lateAbsP95Ms: timing.lateAbsP95, lateAbsMaxMs: timing.lateAbsMax,
        missedTicks: timing.missedTicks,
        leader0_from, leader0_to
      };

      return { summary, traceRows };
    },

    _buildPlan({ pressCBase, dampBase, ampD, repsPerCell }) {
      const plan = [];
      let runIndex = 0;
      for (const wantId of this.cfg.wantIds) {
        for (const pcM of this.cfg.pressCMults) {
          for (const dO of this.cfg.dampOffsets) {
            const pressC = pressCBase * pcM;
            const damp = dampBase + dO;
            for (let r = 1; r <= repsPerCell; r++) {
              plan.push({ runIndex, repIndex: r, wantId, pressC, damp, ampD });
              runIndex++;
            }
          }
        }
      }
      // shuffle to reduce time-drift confound
      for (let i = plan.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [plan[i], plan[j]] = [plan[j], plan[i]];
      }
      // reassign runIndex to keep sequential IDs
      for (let i = 0; i < plan.length; i++) plan[i].runIndex = i;
      return plan;
    },

    async runPack(userCfg = {}) {
      this._stopFlag = false;
      if (userCfg && typeof userCfg === "object") this.cfg = { ...this.cfg, ...userCfg };

      const app = this._getApp();
      if (!app) throw new Error("solPhase311_16n_v2: SOLDashboard not found.");

      const phy = await this._waitForPhysics();
      this._freezeLiveLoop();

      // baseline snapshot at pack start (matches 16m)
      this._baselineSnap = this._snapshotState(phy);

      const ui = this._readUiParams(app);
      const pressCBase = (this.cfg.pressC == null) ? ui.pressC : this.cfg.pressC;
      const dampBase = (this.cfg.baseDamp == null) ? ui.damp : this.cfg.baseDamp;

      const ampB = this.cfg.ampB_fixed;
      const ampD = this.cfg.ampD_fixed;
      const thresh = this.cfg.busOnAbsFluxThresh;

      const baseName = `${this.cfg.filenameBase}_${this._isoForFile()}`;

      const summaryHeader = [
        "schema","runId","runIndex","repIndex","wantId",
        "pressCUsed","baseDampUsed","busThreshUsed",
        "ampB","ampD","ampSum",
        "totalTicks","windowMs","dt","everyMs",
        "onset114_tick","peak114_tick","peak114_abs",
        "onset136_tick","peak136_tick","peak136_abs",
        "outcome","winner",
        "peakSumAbsFlux","peakSumAtTick","peakSumAtMs","peakSumMeanAbsP",
        "peakMaxAbsEdgeFlux","peakEdgeIndex","peakEdgeFrom","peakEdgeTo","peakEdgeFlux","peakConcentration",
        "visibilityStateStart","wasHidden",
        "lateAbsAvgMs","lateAbsP95Ms","lateAbsMaxMs","missedTicks",
        "leader0_from","leader0_to"
      ];

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

      // --- preflight: confirm we're in the bus regime before burning time
      if (this.cfg.preflight?.enabled) {
        console.log("[16n_v2] Preflight…");
        let hits = 0;
        for (let r = 1; r <= this.cfg.preflight.reps; r++) {
          if (this._stopFlag) break;
          const out = await this._runOne({
            runIndex: r - 1,
            repIndex: r,
            wantId: this.cfg.wantIds[0],
            pressC: pressCBase,
            baseDamp: dampBase,
            ampB,
            ampD: this.cfg.preflight.testAmpD
          });
          const s = out.summary;
          if (s.outcome !== "none") hits++;
        }
        console.log(`[16n_v2] Preflight outcome: ${hits}/${this.cfg.preflight.reps} non-none @ ampD=${this.cfg.preflight.testAmpD}`);
        if (hits === 0) {
          console.warn("[16n_v2] Preflight saw ZERO bus activations. Likely not in the 16m bus-broadcast regime. Consider rerunning after refresh + baseline reload, or switch to ridge reacquire sweep.");
        }
      }

      const plan = this._buildPlan({
        pressCBase,
        dampBase,
        ampD,
        repsPerCell: this.cfg.repsPerCell
      });

      console.log(`✅ [16n_v2] Plan: ${plan.length} runs | ampD=${ampD} | pressCBase=${pressCBase} | dampBase=${dampBase} | thresh=${thresh}`);

      try {
        for (let i = 0; i < plan.length; i++) {
          if (this._stopFlag) break;
          if (i % 30 === 0) console.log(`Progress: ${i}/${plan.length} | hidden=${document.hidden}`);

          const r = plan[i];
          const out = await this._runOne({
            runIndex: r.runIndex,
            repIndex: r.repIndex,
            wantId: r.wantId,
            pressC: r.pressC,
            baseDamp: r.damp,
            ampB,
            ampD: r.ampD
          });

          const s = out.summary;
          summaryLines.push(this._csvRow(summaryHeader.map(k => (k in s ? s[k] : ""))));
          for (const row of out.traceRows) traceLines.push(row);
        }
      } finally {
        this._unfreezeLiveLoop();
      }

      const endIso = this._isoForFile();
      const base2 = `${baseName}_${endIso}`;

      this._downloadText(`${base2}_MASTER_summary.csv`, summaryLines.join(""));
      this._downloadText(`${base2}_MASTER_busTrace.csv`, traceLines.join(""));

      console.log("✅ Phase 3.11.16n_v2 complete:", base2);
      return { baseName: base2, runsPlanned: plan.length, stopped: this._stopFlag };
    }
  };

  window.solPhase311_16n_v2 = solPhase311_16n_v2;
  console.log(`✅ solPhase311_16n_v2 installed (${solPhase311_16n_v2.version}). Run: solPhase311_16n_v2.runPack()`);
})();
