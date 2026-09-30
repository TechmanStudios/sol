/* Phase 3.11.16r — Readout Robustness @ gain≈19.3 (CapLaw-stable boundary test)
   Run:
     await solPhase311_16r_readoutRobustness_v1.run()

   Stop:
     solPhase311_16r_readoutRobustness_v1.stop()

   Outputs:
     ...MASTER_summary.csv
     ...MASTER_busTrace.csv

   UI-neutral: no camera moves.
*/
(() => {
  "use strict";

  const T = {
    version: "sol_phase311_16r_readoutRobustness_v1",
    _stop: false,
    stop() { this._stop = true; },

    cfg: {
      // Base timing
      dt: 0.12,
      everyMs: 200,
      totalTicks: 61,
      settleTicks: 3,
      spinWaitMs: 1.5,

      // Priming (same family as 16o/16p/16q)
      wantId: 82,
      injectorIds: [90, 82],
      dreamBlocks: 15,
      dreamBlockSteps: 2,
      injectAmount: 120,
      finalWriteMult: 1,

      // Payload definition (keeps the proven ratio)
      baseAmpB: 4.0,
      baseAmpD: 5.75,

      // Boundary gain (from 16q: gain50 ~ 19.3)
      gain: 19.3,

      // Environment sweep spec (built from base values)
      pressCMults: [0.8, 1.0, 1.2], // ±20%
      dampOffsets: [-1, 0, +1],     // ±1

      repsPerCell: 8,

      // Detectors
      earlyCutoffTick: 15,
      busThreshAlt: 0.5,           // since 1.0 is usually unreachable now

      includeBackgroundEdges: false,
      shuffle: true,
    },

    _sleep(ms) { return new Promise(r => setTimeout(r, ms)); },
    _p2(n) { return String(n).padStart(2, "0"); },
    _p3(n) { return String(n).padStart(3, "0"); },

    _iso(d = new Date()) {
      return `${d.getUTCFullYear()}-${this._p2(d.getUTCMonth()+1)}-${this._p2(d.getUTCDate())}` +
        `T${this._p2(d.getUTCHours())}-${this._p2(d.getUTCMinutes())}-${this._p2(d.getUTCSeconds())}-${this._p3(d.getUTCMilliseconds())}Z`;
    },

    _csvCell(v) {
      if (v === null || v === undefined) return "";
      const s = String(v);
      return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
    },
    _csvRow(cols) { return cols.map(this._csvCell).join(",") + "\n"; },

    _download(filename, text) {
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
      throw new Error("[16r] timed out waiting for physics.");
    },

    _freezeLiveLoop() {
      const app = this._getApp();
      if (!app?.config) throw new Error("[16r] App not ready.");
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

    _readUiBaseParams() {
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

    _nodeById(phy, id) {
      const want = String(id);
      for (const n of (phy.nodes || [])) if (n?.id != null && String(n.id) === want) return n;
      return null;
    },

    _inject(phy, id, amt) {
      const n = this._nodeById(phy, id);
      if (!n) throw new Error(`[16r] node not found: ${id}`);
      const a = Math.max(0, Number(amt) || 0);
      n.rho += a;
      try {
        if (n.isConstellation && typeof phy.reinforceSemanticStar === "function") {
          phy.reinforceSemanticStar(n, (a / 50.0));
        }
      } catch(e) {}
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

    _pickBasin(phy) {
      const n82 = this._nodeById(phy, 82);
      const n90 = this._nodeById(phy, 90);
      const r82 = Number.isFinite(n82?.rho) ? n82.rho : 0;
      const r90 = Number.isFinite(n90?.rho) ? n90.rho : 0;
      return (r90 > r82) ? 90 : 82;
    },

    _frame(phy, includeBackgroundEdges) {
      const edges = phy.edges || [];
      const nodes = phy.nodes || [];

      let sumAbsFlux = 0;
      let maxAbsEdgeFlux = 0, maxEdgeFrom = "", maxEdgeTo = "", maxEdgeFlux = 0;

      for (let i = 0; i < edges.length; i++) {
        const e = edges[i];
        if (!e) continue;
        if (!includeBackgroundEdges && e.background) continue;
        const f = (typeof e.flux === "number" && Number.isFinite(e.flux)) ? e.flux : 0;
        const af = Math.abs(f);
        sumAbsFlux += af;
        if (af > maxAbsEdgeFlux) {
          maxAbsEdgeFlux = af;
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
      return { sumAbsFlux, meanAbsP, maxAbsEdgeFlux, maxEdgeFrom, maxEdgeTo, maxEdgeFlux, concentration };
    },

    async _recomputeDerived(dt) {
      try {
        if (window.SOLRuntime?.recomputeDerived) return await window.SOLRuntime.recomputeDerived({ dt });
      } catch (e) {}
      try {
        const app = this._getApp();
        const phy = await this._waitForPhysics();
        if (app?.sim?.recomputeDerivedFields) return app.sim.recomputeDerivedFields(phy, { dt });
      } catch (e) {}
      return { capLawApplied: null, dtUsed: dt, capLawSig: null, capLawHash: null };
    },

    _snapshot(phy) {
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
      for (let i = 0; i < (phy.edges || []).length; i++) edges.push([i, { flux: phy.edges[i]?.flux }]);
      const globalBias = (typeof phy.globalBias === "number" && Number.isFinite(phy.globalBias)) ? phy.globalBias : 0;
      return { nodes, edges, globalBias };
    },

    _restore(phy, snap) {
      const nMap = new Map(snap.nodes || []);
      for (const n of (phy.nodes || [])) {
        const s = nMap.get(n?.id);
        if (!s) continue;
        for (const k in s) { try { n[k] = s[k]; } catch(e) {} }
      }
      const eMap = new Map(snap.edges || []);
      for (let i = 0; i < (phy.edges || []).length; i++) {
        const e = phy.edges[i];
        const s = eMap.get(i);
        if (!s) continue;
        for (const k in s) { try { e[k] = s[k]; } catch(e) {} }
      }
      try { phy.globalBias = snap.globalBias || 0; } catch(e) {}
    },

    async _baselineRestore(phy) {
      if (window.SOLBaseline?.restore) {
        await window.SOLBaseline.restore();
        return { mode: "SOLBaseline.restore" };
      }
      if (!this._snap) {
        this._snap = this._snapshot(phy);
        return { mode: "internal_snapshot_created" };
      }
      this._restore(phy, this._snap);
      return { mode: "internal_snapshot_restored" };
    },

    async _modeSelect(phy, pressC, damp) {
      const c = this.cfg;
      let idx = 0;
      for (let b = 0; b < Math.max(0, c.dreamBlocks - 1); b++) {
        const injId = c.injectorIds[idx % c.injectorIds.length];
        idx++;
        this._inject(phy, injId, c.injectAmount);
        for (let s = 0; s < c.dreamBlockSteps; s++) phy.step(c.dt, pressC, damp);
      }
      this._inject(phy, c.wantId, c.injectAmount * (c.finalWriteMult || 1));
      try { if (typeof phy.computePressure === "function") phy.computePressure(pressC); } catch(e) {}
    },

    _shuffle(arr) {
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

      const ui = this._readUiBaseParams();
      const inv = window.SOLRuntime?.getInvariants?.() || {};
      const basePressC = inv.pressC ?? ui.pressC ?? 2.0;
      const baseDamp = inv.damp ?? ui.damp ?? 5.0;

      const pressCGrid = this.cfg.pressCMults.map(m => +(basePressC * m).toFixed(6));
      const dampGrid = this.cfg.dampOffsets.map(d => +(baseDamp + d).toFixed(6));

      const ampB = this.cfg.baseAmpB * this.cfg.gain;
      const ampD = this.cfg.baseAmpD * this.cfg.gain;

      const edgeIndex = this._buildEdgeIndex(phy);
      const i114_89 = edgeIndex.get("114->89");
      const i114_79 = edgeIndex.get("114->79");
      const i136_89 = edgeIndex.get("136->89");
      const i136_79 = edgeIndex.get("136->79");

      const busSet = new Set(["114->89","114->79","136->89","136->79"]);

      const startTag = this._iso(new Date());

      // plan
      const plan = [];
      for (const pC of pressCGrid) {
        for (const d of dampGrid) {
          for (let r = 1; r <= this.cfg.repsPerCell; r++) {
            plan.push({ pressCUsed: pC, dampUsed: d, rep: r });
          }
        }
      }
      if (this.cfg.shuffle) this._shuffle(plan);

      const summaryHeader = [
        "schema","runId","runIndex","repIndex",
        "basePressC","baseDamp",
        "pressCUsed","dampUsed",
        "dt","everyMs","totalTicks","settleTicks",
        "capLawHash","capLawSig","capLawApplied","capLawDtUsed",
        "gain","ampB","ampD","ampSum",
        "peak114_tick","peak114_abs","peak136_tick","peak136_abs",
        "onset114_alt","onset136_alt",
        "anyBusEdgeAsMax","firstBusMax_tick","firstBusMax_edge",
        "earlyBusMax",
        "peakMaxAbsEdgeFlux","peakEdgeFrom","peakEdgeTo",
        "visibilityStateStart","wasHidden",
        "lateAbsAvgMs","lateAbsP95Ms","lateAbsMaxMs","missedTicks",
        "baselineMode","stepMode"
      ];

      const traceHeader = [
        "schema","runId","runIndex","repIndex",
        "capLawHash",
        "pressCUsed","dampUsed",
        "gain","ampB","ampD",
        "tick","tMs","lateByMs","basin",
        "sumAbsFlux","meanAbsP",
        "maxAbsEdgeFlux","maxEdgeFrom","maxEdgeTo",
        "flux_114_89","flux_114_79","flux_136_89","flux_136_79"
      ];

      const summaryLines = [this._csvRow(summaryHeader)];
      const traceLines = [this._csvRow(traceHeader)];

      const findOnset = (arr, thr) => {
        for (let i = 0; i < arr.length; i++) if (arr[i] >= thr) return i;
        return null;
      };

      const percentile = (arr, p) => {
        if (!arr.length) return 0;
        const a = arr.slice().sort((x,y)=>x-y);
        const idx = (p/100) * (a.length - 1);
        const lo = Math.floor(idx), hi = Math.ceil(idx);
        if (lo === hi) return a[lo];
        const t = idx - lo;
        return a[lo]*(1-t) + a[hi]*t;
      };

      let runIndex = 0;

      console.log(`[16r] Running grid: pressC=${pressCGrid.join(", ")} | damp=${dampGrid.join(", ")} | reps=${this.cfg.repsPerCell} | gain=${this.cfg.gain}`);

      for (const item of plan) {
        if (this._stop) break;

        const pressCUsed = item.pressCUsed;
        const dampUsed = item.dampUsed;
        const repIndex = item.rep;

        const runId = `${this._iso(new Date())}_r${String(runIndex).padStart(5,"0")}_pC${pressCUsed}_d${dampUsed}_rep${repIndex}`;

        const visibilityStateStart = document.visibilityState || "";
        let wasHidden = !!document.hidden;
        const onVis = () => { if (document.hidden) wasHidden = true; };
        document.addEventListener("visibilitychange", onVis, { passive: true });

        const baselineInfo = await this._baselineRestore(phy);
        const cap = await this._recomputeDerived(this.cfg.dt);

        await this._modeSelect(phy, pressCUsed, dampUsed);

        // settle
        let stepMode = "dt_press_damp";
        for (let s = 0; s < this.cfg.settleTicks; s++) {
          try { phy.step(this.cfg.dt, pressCUsed, dampUsed); }
          catch (e) { phy.step(this.cfg.dt); stepMode = "dt_only"; }
        }

        // inject
        this._inject(phy, 114, ampB);
        this._inject(phy, 136, ampD);

        const bus114Abs = [];
        const bus136Abs = [];
        let peak114 = { tick: 0, abs: 0 };
        let peak136 = { tick: 0, abs: 0 };

        let anyBusEdgeAsMax = 0;
        let firstBusMax_tick = null;
        let firstBusMax_edge = "";

        let peakMaxAbsEdgeFlux = 0;
        let peakEdgeFrom = "", peakEdgeTo = "";

        const lateAbs = [];
        let missedTicks = 0;

        const startMs = performance.now();

        for (let tick = 0; tick < this.cfg.totalTicks; tick++) {
          if (this._stop) break;

          const target = startMs + tick * this.cfg.everyMs;

          while (true) {
            const now = performance.now();
            const remain = target - now;
            if (remain <= 0) break;
            if (this.cfg.spinWaitMs > 0 && remain <= this.cfg.spinWaitMs) break;
            await this._sleep(Math.min(10, Math.max(0, remain - (this.cfg.spinWaitMs || 0))));
          }
          while (performance.now() < target) {}

          const now = performance.now();
          const lateByMs = now - target;
          lateAbs.push(Math.abs(lateByMs));

          // crude missed tick detector (for “big” slips)
          if (tick > 0 && Math.abs(lateByMs) > this.cfg.everyMs * 0.75) missedTicks++;

          // step
          if (stepMode === "dt_press_damp") {
            try { phy.step(this.cfg.dt, pressCUsed, dampUsed); }
            catch (e) { phy.step(this.cfg.dt); stepMode = "dt_only"; }
          } else {
            phy.step(this.cfg.dt);
          }

          const basin = this._pickBasin(phy);
          const fm = this._frame(phy, this.cfg.includeBackgroundEdges);

          if (fm.maxAbsEdgeFlux > peakMaxAbsEdgeFlux) {
            peakMaxAbsEdgeFlux = fm.maxAbsEdgeFlux;
            peakEdgeFrom = fm.maxEdgeFrom;
            peakEdgeTo = fm.maxEdgeTo;
          }

          const f114_89 = (i114_89 != null) ? this._edgeFlux(phy, i114_89) : 0;
          const f114_79 = (i114_79 != null) ? this._edgeFlux(phy, i114_79) : 0;
          const f136_89 = (i136_89 != null) ? this._edgeFlux(phy, i136_89) : 0;
          const f136_79 = (i136_79 != null) ? this._edgeFlux(phy, i136_79) : 0;

          const a114 = Math.max(Math.abs(f114_89), Math.abs(f114_79));
          const a136 = Math.max(Math.abs(f136_89), Math.abs(f136_79));

          bus114Abs.push(a114);
          bus136Abs.push(a136);

          if (a114 > peak114.abs) peak114 = { tick, abs: a114 };
          if (a136 > peak136.abs) peak136 = { tick, abs: a136 };

          const maxPair = `${fm.maxEdgeFrom}->${fm.maxEdgeTo}`;
          if (busSet.has(maxPair)) {
            anyBusEdgeAsMax = 1;
            if (firstBusMax_tick == null) {
              firstBusMax_tick = tick;
              firstBusMax_edge = maxPair;
            }
          }

          traceLines.push(this._csvRow([
            this.version, runId, runIndex, repIndex,
            (cap.capLawHash ?? ""),
            pressCUsed, dampUsed,
            this.cfg.gain, ampB, ampD,
            tick, (now - startMs), lateByMs, basin,
            fm.sumAbsFlux, fm.meanAbsP,
            fm.maxAbsEdgeFlux, fm.maxEdgeFrom, fm.maxEdgeTo,
            f114_89, f114_79, f136_89, f136_79
          ]));
        }

        document.removeEventListener("visibilitychange", onVis);

        const onset114_alt = findOnset(bus114Abs, this.cfg.busThreshAlt);
        const onset136_alt = findOnset(bus136Abs, this.cfg.busThreshAlt);

        const earlyBusMax = (anyBusEdgeAsMax === 1 && firstBusMax_tick != null && firstBusMax_tick <= this.cfg.earlyCutoffTick) ? 1 : 0;

        const lateAbsAvgMs = lateAbs.length ? lateAbs.reduce((a,b)=>a+b,0)/lateAbs.length : 0;
        const lateAbsP95Ms = percentile(lateAbs, 95);
        const lateAbsMaxMs = lateAbs.length ? Math.max(...lateAbs) : 0;

        summaryLines.push(this._csvRow([
          this.version, runId, runIndex, repIndex,
          basePressC, baseDamp,
          pressCUsed, dampUsed,
          this.cfg.dt, this.cfg.everyMs, this.cfg.totalTicks, this.cfg.settleTicks,
          (cap.capLawHash ?? ""), (cap.capLawSig ?? ""), (cap.capLawApplied ?? ""), (cap.dtUsed ?? ""),
          this.cfg.gain, ampB, ampD, (ampB + ampD),
          peak114.tick, peak114.abs, peak136.tick, peak136.abs,
          (onset114_alt == null ? "" : onset114_alt),
          (onset136_alt == null ? "" : onset136_alt),
          anyBusEdgeAsMax,
          (firstBusMax_tick == null ? "" : firstBusMax_tick),
          firstBusMax_edge,
          earlyBusMax,
          peakMaxAbsEdgeFlux, peakEdgeFrom, peakEdgeTo,
          visibilityStateStart, wasHidden,
          lateAbsAvgMs, lateAbsP95Ms, lateAbsMaxMs, missedTicks,
          baselineInfo.mode, stepMode
        ]));

        runIndex += 1;

        if (runIndex % 18 === 0) {
          console.log(`[16r] progress ${runIndex}/${plan.length} | pC=${pressCUsed} damp=${dampUsed} | early=${earlyBusMax} firstTick=${firstBusMax_tick}`);
        }
      }

      const endTag = this._iso(new Date());
      const baseName = `${this.version}_${startTag}_${endTag}`;

      this._unfreezeLiveLoop();

      this._download(`${baseName}_MASTER_summary.csv`, summaryLines.join(""));
      this._download(`${baseName}_MASTER_busTrace.csv`, traceLines.join(""));

      console.log(`✅ [16r] DONE. Upload:\n- ${baseName}_MASTER_summary.csv\n- ${baseName}_MASTER_busTrace.csv`);
      return { baseName, runs: runIndex, stopped: this._stop };
    }
  };

  window.solPhase311_16r_readoutRobustness_v1 = T;
  console.log(`✅ solPhase311_16r_readoutRobustness_v1 installed (${T.version}). Run: await solPhase311_16r_readoutRobustness_v1.run()`);
})();
