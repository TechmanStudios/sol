/* Phase 3.11.16p — Gain Scan (find bus activation threshold under v3.7.2 + CapLaw)
   Run:
     await solPhase311_16p_gainScan_v1.run()

   Stop:
     solPhase311_16p_gainScan_v1.stop()

   Outputs:
     ...MASTER_summary.csv
     ...MASTER_busTrace.csv

   UI-neutral: no camera moves.
*/
(() => {
  "use strict";

  const T = {
    version: "sol_phase311_16p_gainScan_v1",
    _stop: false,
    stop() { this._stop = true; },

    cfg: {
      // Prefer UI/runtime invariants if available; else defaults
      pressCUsed: null,
      baseDampUsed: null,

      dt: 0.12,
      everyMs: 200,
      totalTicks: 61,
      settleTicks: 3,

      // Old bus threshold (from 16m). We’ll keep it as a detector.
      busThreshUsed: 1.0,

      // Dream priming (same family as 16o)
      wantId: 82,
      injectorIds: [90, 82],
      dreamBlocks: 15,
      dreamBlockSteps: 2,
      injectAmount: 120,
      finalWriteMult: 1,

      // Base amplitudes (the “known” ridge neighborhood from earlier work)
      baseAmpB: 4.0,
      baseAmpD: 5.75,

      // Gain factors (scan these)
      gains: [1, 2, 4, 8, 16, 32],

      // Reps per gain factor
      repsPerGain: 6,

      // bus edges to read out
      busEdges: [
        { key: "flux_114_89", from: 114, to: 89 },
        { key: "flux_114_79", from: 114, to: 79 },
        { key: "flux_136_89", from: 136, to: 89 },
        { key: "flux_136_79", from: 136, to: 79 },
      ],

      includeBackgroundEdges: false,
      shuffle: true,
    },

    _sleep(ms) { return new Promise(r => setTimeout(r, ms)); },
    _p2(n) { return String(n).padStart(2, "0"); },
    _p3(n) { return String(n).padStart(3, "0"); },

    _isoForId(d = new Date()) {
      return `${d.getUTCFullYear()}-${this._p2(d.getUTCMonth()+1)}-${this._p2(d.getUTCDate())}` +
        `T${this._p2(d.getUTCHours())}-${this._p2(d.getUTCMinutes())}-${this._p2(d.getUTCSeconds())}-${this._p3(d.getUTCMilliseconds())}Z`;
    },

    _csvCell(v) {
      if (v === null || v === undefined) return "";
      const s = String(v);
      return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
    },
    _csvRow(cols) { return cols.map(this._csvCell).join(",") + "\n"; },

    _downloadText(filename, text) {
      const blob = new Blob([text], { type: "text/csv" });
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
      throw new Error("[16p] timed out waiting for physics.");
    },

    _freezeLiveLoop() {
      const app = this._getApp();
      if (!app?.config) throw new Error("[16p] App not ready (no config).");
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

    _readUiParams() {
      const app = this._getApp();
      const pressC = (app?.dom?.pressureSlider)
        ? (parseFloat(String(app.dom.pressureSlider.value)) * (app.config.pressureSliderScale || 1))
        : null;
      const damp = (app?.dom?.dampSlider)
        ? parseFloat(String(app.dom.dampSlider.value))
        : null;
      return {
        pressC: Number.isFinite(pressC) ? pressC : null,
        damp: Number.isFinite(damp) ? damp : null
      };
    },

    _nodeByIdLoose(phy, id) {
      const want = String(id);
      for (const n of (phy.nodes || [])) {
        if (n?.id != null && String(n.id) === want) return n;
      }
      return null;
    },

    _injectById(phy, id, amount) {
      const n = this._nodeByIdLoose(phy, id);
      if (!n) throw new Error(`[16p] injector node not found: ${id}`);
      const amt = Math.max(0, Number(amount) || 0);
      n.rho += amt;

      // optional semantic reinforcement if available
      try {
        if (n.isConstellation && typeof phy.reinforceSemanticStar === "function") {
          const freqBoost = amt / 50.0;
          phy.reinforceSemanticStar(n, freqBoost);
        }
      } catch (e) {}
    },

    _pickBasin(phy) {
      const n82 = this._nodeByIdLoose(phy, 82);
      const n90 = this._nodeByIdLoose(phy, 90);
      const r82 = Number.isFinite(n82?.rho) ? n82.rho : 0;
      const r90 = Number.isFinite(n90?.rho) ? n90.rho : 0;
      return (r90 > r82) ? 90 : 82;
    },

    _buildEdgeIndex(phy) {
      const map = new Map();
      const edges = phy.edges || [];
      for (let i = 0; i < edges.length; i++) {
        const e = edges[i];
        if (!e) continue;
        map.set(`${e.from}->${e.to}`, i);
      }
      return map;
    },

    _edgeFlux(phy, idx) {
      const e = (phy.edges || [])[idx];
      const f = (e && typeof e.flux === "number" && Number.isFinite(e.flux)) ? e.flux : 0;
      return f;
    },

    _frameMetrics(phy, includeBackgroundEdges) {
      const edges = phy.edges || [];
      const nodes = phy.nodes || [];

      let sumAbsFlux = 0;
      let maxAbsEdgeFlux = 0;
      let maxEdgeIndex = -1, maxEdgeFrom = "", maxEdgeTo = "", maxEdgeFlux = 0;

      for (let i = 0; i < edges.length; i++) {
        const e = edges[i];
        if (!e) continue;
        if (!includeBackgroundEdges && e.background) continue;
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

      let meanAbsP = 0;
      for (const n of nodes) {
        const p = (typeof n?.p === "number" && Number.isFinite(n.p)) ? n.p : 0;
        meanAbsP += Math.abs(p);
      }
      meanAbsP /= Math.max(1, nodes.length);

      const concentration = (sumAbsFlux > 0) ? (maxAbsEdgeFlux / sumAbsFlux) : 0;
      return { sumAbsFlux, meanAbsP, maxAbsEdgeFlux, maxEdgeIndex, maxEdgeFrom, maxEdgeTo, maxEdgeFlux, concentration };
    },

    async _recomputeDerived(dt) {
      try {
        if (window.SOLRuntime?.recomputeDerived) {
          return await window.SOLRuntime.recomputeDerived({ dt });
        }
      } catch (e) {}

      try {
        const app = this._getApp();
        const phy = await this._waitForPhysics();
        if (app?.sim?.recomputeDerivedFields) return app.sim.recomputeDerivedFields(phy, { dt });
      } catch (e) {}

      return { capLawApplied: null, dtUsed: dt, capLawSig: null, capLawHash: null };
    },

    async _baselineRestore(phy) {
      if (window.SOLBaseline?.restore) {
        await window.SOLBaseline.restore();
        return { mode: "SOLBaseline.restore" };
      }
      return { mode: "noBaseline" };
    },

    async _modeSelect(phy, pressC, damp) {
      const c = this.cfg;
      let injIndex = 0;

      for (let b = 0; b < Math.max(0, c.dreamBlocks - 1); b++) {
        const injId = c.injectorIds[injIndex % c.injectorIds.length];
        injIndex++;
        this._injectById(phy, injId, c.injectAmount);
        for (let s = 0; s < c.dreamBlockSteps; s++) {
          phy.step(c.dt, pressC, damp);
        }
      }
      this._injectById(phy, c.wantId, c.injectAmount * (c.finalWriteMult || 1));
      try { if (typeof phy.computePressure === "function") phy.computePressure(pressC); } catch (e) {}
    },

    _shuffleInPlace(arr) {
      for (let i = arr.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [arr[i], arr[j]] = [arr[j], arr[i]];
      }
      return arr;
    },

    async run(userCfg = {}) {
      this._stop = false;
      this.cfg = { ...this.cfg, ...userCfg };

      const phy = await this._waitForPhysics();
      this._freezeLiveLoop();

      const ui = this._readUiParams();
      const inv = window.SOLRuntime?.getInvariants?.() || {};
      const pressCUsed = (this.cfg.pressCUsed != null) ? this.cfg.pressCUsed : (inv.pressC ?? ui.pressC ?? 2.0);
      const baseDampUsed = (this.cfg.baseDampUsed != null) ? this.cfg.baseDampUsed : (inv.damp ?? ui.damp ?? 5.0);

      const startTag = this._isoForId(new Date());

      // Build run plan
      const plan = [];
      for (const g of this.cfg.gains) {
        for (let rep = 1; rep <= this.cfg.repsPerGain; rep++) {
          plan.push({ gain: g, rep });
        }
      }
      if (this.cfg.shuffle) this._shuffleInPlace(plan);

      const summaryHeader = [
        "schema","runId","runIndex","repIndex",
        "pressCUsed","baseDampUsed","dt","everyMs","totalTicks","settleTicks",
        "busThreshUsed","capLawHash","capLawSig","capLawApplied","capLawDtUsed",
        "gain","ampB","ampD","ampSum",
        "peak114_tick","peak114_abs",
        "peak136_tick","peak136_abs",
        "busOverMaxEdge",
        "anyBusEdgeAsMax","firstBusMax_tick","firstBusMax_edge",
        "peakMaxAbsEdgeFlux","peakEdgeFrom","peakEdgeTo",
        "baselineMode","stepMode",
        "visibilityStateStart","wasHidden"
      ];

      const traceHeader = [
        "schema","runId","runIndex","repIndex",
        "gain","ampB","ampD",
        "tick","tMs","lateByMs","basin",
        "sumAbsFlux","meanAbsP",
        "maxAbsEdgeFlux","maxEdgeFrom","maxEdgeTo",
        "flux_114_89","flux_114_79","flux_136_89","flux_136_79"
      ];

      const summaryLines = [this._csvRow(summaryHeader)];
      const traceLines = [this._csvRow(traceHeader)];

      // Edge index once (assumes stable graph)
      const edgeIndex = this._buildEdgeIndex(phy);
      const idx114_89 = edgeIndex.get("114->89");
      const idx114_79 = edgeIndex.get("114->79");
      const idx136_89 = edgeIndex.get("136->89");
      const idx136_79 = edgeIndex.get("136->79");

      let runIndex = 0;

      for (const item of plan) {
        if (this._stop) break;

        const gain = item.gain;
        const repIndex = item.rep;

        const ampB = this.cfg.baseAmpB * gain;
        const ampD = this.cfg.baseAmpD * gain;
        const ampSum = ampB + ampD;

        const rid = `${this._isoForId(new Date())}_r${String(runIndex).padStart(5,"0")}_g${gain}_rep${repIndex}`;

        const visibilityStateStart = document.visibilityState || "";
        let wasHidden = !!document.hidden;
        const onVis = () => { if (document.hidden) wasHidden = true; };
        document.addEventListener("visibilitychange", onVis, { passive: true });

        const baselineInfo = await this._baselineRestore(phy);
        const cap = await this._recomputeDerived(this.cfg.dt);

        // Mode select
        await this._modeSelect(phy, pressCUsed, baseDampUsed);

        // settle
        let stepMode = "dt_press_damp";
        for (let s = 0; s < this.cfg.settleTicks; s++) {
          try { phy.step(this.cfg.dt, pressCUsed, baseDampUsed); }
          catch (e) { phy.step(this.cfg.dt); stepMode = "dt_only"; }
        }

        // Inject payload tick 0
        this._injectById(phy, 114, ampB);
        this._injectById(phy, 136, ampD);

        const bus114Abs = [];
        const bus136Abs = [];
        let peak114 = { tick: 0, abs: 0 };
        let peak136 = { tick: 0, abs: 0 };
        let maxEdgePeak = { abs: 0, from: "", to: "" };

        let anyBusEdgeAsMax = 0;
        let firstBusMax_tick = null;
        let firstBusMax_edge = "";

        const startMs = performance.now();
        const lateAbs = [];

        for (let tick = 0; tick < this.cfg.totalTicks; tick++) {
          if (this._stop) break;

          const target = startMs + tick * this.cfg.everyMs;

          while (true) {
            const now = performance.now();
            const remain = target - now;
            if (remain <= 0) break;
            await this._sleep(Math.min(10, Math.max(0, remain)));
          }
          while (performance.now() < target) {}

          const now = performance.now();
          const lateByMs = now - target;
          lateAbs.push(Math.abs(lateByMs));

          // step
          if (stepMode === "dt_press_damp") {
            try { phy.step(this.cfg.dt, pressCUsed, baseDampUsed); }
            catch (e) { phy.step(this.cfg.dt); stepMode = "dt_only"; }
          } else {
            phy.step(this.cfg.dt);
          }

          const basin = this._pickBasin(phy);
          const fm = this._frameMetrics(phy, this.cfg.includeBackgroundEdges);

          if (Math.abs(fm.maxAbsEdgeFlux) > Math.abs(maxEdgePeak.abs)) {
            maxEdgePeak = { abs: fm.maxAbsEdgeFlux, from: fm.maxEdgeFrom, to: fm.maxEdgeTo };
          }

          const f114_89 = (idx114_89 != null) ? this._edgeFlux(phy, idx114_89) : 0;
          const f114_79 = (idx114_79 != null) ? this._edgeFlux(phy, idx114_79) : 0;
          const f136_89 = (idx136_89 != null) ? this._edgeFlux(phy, idx136_89) : 0;
          const f136_79 = (idx136_79 != null) ? this._edgeFlux(phy, idx136_79) : 0;

          const a114 = Math.max(Math.abs(f114_89), Math.abs(f114_79));
          const a136 = Math.max(Math.abs(f136_89), Math.abs(f136_79));

          bus114Abs.push(a114);
          bus136Abs.push(a136);

          if (a114 > peak114.abs) peak114 = { tick, abs: a114 };
          if (a136 > peak136.abs) peak136 = { tick, abs: a136 };

          // Detect if bus edge becomes max-edge
          const maxPair = `${fm.maxEdgeFrom}->${fm.maxEdgeTo}`;
          if (maxPair === "114->89" || maxPair === "114->79" || maxPair === "136->89" || maxPair === "136->79") {
            anyBusEdgeAsMax = 1;
            if (firstBusMax_tick == null) {
              firstBusMax_tick = tick;
              firstBusMax_edge = maxPair;
            }
          }

          traceLines.push(this._csvRow([
            this.version, rid, runIndex, repIndex,
            gain, ampB, ampD,
            tick, (now - startMs), lateByMs, basin,
            fm.sumAbsFlux, fm.meanAbsP,
            fm.maxAbsEdgeFlux, fm.maxEdgeFrom, fm.maxEdgeTo,
            f114_89, f114_79, f136_89, f136_79
          ]));
        }

        document.removeEventListener("visibilitychange", onVis);

        const busPeak = Math.max(peak114.abs, peak136.abs);
        const busOverMaxEdge = (maxEdgePeak.abs > 0) ? (busPeak / maxEdgePeak.abs) : 0;

        summaryLines.push(this._csvRow([
          this.version, rid, runIndex, repIndex,
          pressCUsed, baseDampUsed, this.cfg.dt, this.cfg.everyMs, this.cfg.totalTicks, this.cfg.settleTicks,
          this.cfg.busThreshUsed,
          (cap.capLawHash ?? ""), (cap.capLawSig ?? ""), (cap.capLawApplied ?? ""), (cap.dtUsed ?? ""),
          gain, ampB, ampD, ampSum,
          peak114.tick, peak114.abs,
          peak136.tick, peak136.abs,
          busOverMaxEdge,
          anyBusEdgeAsMax,
          (firstBusMax_tick == null ? "" : firstBusMax_tick),
          firstBusMax_edge,
          maxEdgePeak.abs, maxEdgePeak.from, maxEdgePeak.to,
          baselineInfo.mode, stepMode,
          visibilityStateStart, wasHidden
        ]));

        runIndex += 1;

        if (runIndex % 12 === 0) {
          console.log(`[16p] progress ${runIndex}/${plan.length} | gain=${gain} | peak114=${peak114.abs.toFixed(3)} peak136=${peak136.abs.toFixed(3)} | busMax=${anyBusEdgeAsMax}`);
        }
      }

      const endTag = this._isoForId(new Date());
      const baseName = `${this.version}_${startTag}_${endTag}`;

      this._unfreezeLiveLoop();

      this._downloadText(`${baseName}_MASTER_summary.csv`, summaryLines.join(""));
      this._downloadText(`${baseName}_MASTER_busTrace.csv`, traceLines.join(""));

      console.log(`✅ [16p] DONE. Upload:\n- ${baseName}_MASTER_summary.csv\n- ${baseName}_MASTER_busTrace.csv`);
      return { baseName, runs: runIndex, stopped: this._stop };
    }
  };

  window.solPhase311_16p_gainScan_v1 = T;
  console.log(`✅ solPhase311_16p_gainScan_v1 installed (${T.version}). Run: await solPhase311_16p_gainScan_v1.run()`);
})();
