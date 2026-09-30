/* Phase 3.11.16o_v2 — Ridge Reacquisition (CapLawHash + baseline-safe)
   Purpose:
     Reacquire P(bothOn | ampD) under dashboard v3.7.2 invariants,
     then estimate the true 50% point for the next robustness grid.

   Run:
     await solPhase311_16o_v2.run()

   Stop:
     solPhase311_16o_v2.stop()

   Notes:
     - UI-neutral (no camera moves)
     - Uses SOLBaseline.restore() if present (wrapped by dashboard interop), else internal snapshot restore
     - Forces SOLRuntime.recomputeDerived({dt}) after restore (derived fields canonical)
*/
(() => {
  "use strict";

  const T = {
    version: "sol_phase311_16o_v2_ridgeReacquire_capLawHash_v1",
    _stop: false,
    stop() { this._stop = true; },

    cfg: {
      // environment (null => read from UI / SOLRuntime)
      pressCUsed: null,
      baseDampUsed: null,

      dt: 0.12,
      everyMs: 200,
      totalTicks: 61,         // observation ticks
      settleTicks: 3,         // pre-roll steps after priming and before main injection
      busThreshUsed: 1.0,

      wantId: 82,
      injectorIds: [90, 82],
      dreamBlocks: 15,
      dreamBlockSteps: 2,
      injectAmount: 120,
      finalWriteMult: 1,

      ampB: 4.0,
      ampDList: [
        5.45, 5.475, 5.50, 5.5125, 5.525, 5.55, 5.575, 5.60,
        5.625, 5.65, 5.675, 5.70, 5.725, 5.75
      ],
      repsPerAmpD: 12,

      // bus edges to read out
      busEdges: [
        { key: "flux_114_89", from: 114, to: 89 },
        { key: "flux_114_79", from: 114, to: 79 },
        { key: "flux_136_89", from: 136, to: 89 },
        { key: "flux_136_79", from: 136, to: 79 },
      ],

      // glow band for preflip glow detection (no onset but close peak)
      glowLo: 0.95,
      glowHi: 0.999,

      // include background edges in max-edge search?
      includeBackgroundEdges: false,

      // shuffle run order to reduce drift confounds
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
      throw new Error("[16o_v2] timed out waiting for physics.");
    },

    _freezeLiveLoop() {
      const app = this._getApp();
      if (!app?.config) throw new Error("[16o_v2] App not ready (no config).");
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
      if (!n) throw new Error(`[16o_v2] injector node not found: ${id}`);
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

    _snapshotState(phy) {
      const nodePairs = [];
      for (const n of (phy.nodes || [])) {
        if (!n || n.id == null) continue;
        nodePairs.push([n.id, {
          rho: n.rho, p: n.p, psi: n.psi, psi_bias: n.psi_bias,
          semanticMass: n.semanticMass, semanticMass0: n.semanticMass0,
          b_q: n.b_q, b_charge: n.b_charge, b_state: n.b_state
        }]);
      }
      const edgePairs = [];
      for (let i = 0; i < (phy.edges || []).length; i++) {
        const e = phy.edges[i];
        edgePairs.push([i, { flux: e?.flux }]);
      }
      const globalBias = (typeof phy.globalBias === "number" && Number.isFinite(phy.globalBias)) ? phy.globalBias : 0;
      return { nodePairs, edgePairs, globalBias };
    },

    _restoreState(phy, snap) {
      const nodeMap = new Map(snap.nodePairs || []);
      for (const n of (phy.nodes || [])) {
        if (!n || n.id == null) continue;
        const s = nodeMap.get(n.id);
        if (!s) continue;
        for (const k in s) { try { n[k] = s[k]; } catch(e) {} }
      }
      const edgeMap = new Map(snap.edgePairs || []);
      for (let i = 0; i < (phy.edges || []).length; i++) {
        const e = phy.edges[i];
        if (!e) continue;
        const s = edgeMap.get(i);
        if (!s) continue;
        for (const k in s) { try { e[k] = s[k]; } catch(e) {} }
      }
      try { phy.globalBias = snap.globalBias || 0; } catch(e) {}
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
      // Prefer dashboard canonical API
      try {
        if (window.SOLRuntime?.recomputeDerived) {
          return await window.SOLRuntime.recomputeDerived({ dt });
        }
      } catch (e) {}

      // fallback
      try {
        const app = this._getApp();
        const phy = await this._waitForPhysics();
        if (app?.sim?.recomputeDerivedFields) return app.sim.recomputeDerivedFields(phy, { dt });
      } catch (e) {}

      return { capLawApplied: null, dtUsed: dt, capLawSig: null, capLawHash: null };
    },

    async _baselineRestoreOrSnapshot(phy) {
      // If SOLBaseline exists, use it (dashboard v3.7 interop should already recompute derived)
      if (window.SOLBaseline?.restore) {
        await window.SOLBaseline.restore();
        return { mode: "SOLBaseline.restore" };
      }

      // Otherwise internal snapshot restore
      if (!this._baselineSnap) {
        this._baselineSnap = this._snapshotState(phy);
        return { mode: "internal_snapshot_created" };
      }
      this._restoreState(phy, this._baselineSnap);
      return { mode: "internal_snapshot_restored" };
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
      const pressCUsed = (this.cfg.pressCUsed != null) ? this.cfg.pressCUsed : (window.SOLRuntime?.getInvariants?.().pressC ?? ui.pressC ?? 2.0);
      const baseDampUsed = (this.cfg.baseDampUsed != null) ? this.cfg.baseDampUsed : (window.SOLRuntime?.getInvariants?.().damp ?? ui.damp ?? 5.0);

      const startTag = this._isoForId(new Date());
      const plan = [];
      for (const ampD of this.cfg.ampDList) {
        for (let rep = 1; rep <= this.cfg.repsPerAmpD; rep++) {
          plan.push({ ampD, rep });
        }
      }
      if (this.cfg.shuffle) this._shuffleInPlace(plan);

      const summaryHeader = [
        "schema","runId","runIndex","repIndex",
        "pressCUsed","baseDampUsed","dt","everyMs","totalTicks","settleTicks",
        "busThreshUsed","capLawHash","capLawSig","capLawApplied","capLawDtUsed",
        "ampB","ampD","ampSum",
        "onset114_tick","peak114_tick","peak114_abs",
        "onset136_tick","peak136_tick","peak136_abs",
        "outcome","winner",
        "glow114","glow136",
        "peakSumAbsFlux","peakSumAtTick","peakSumAtMs","peakSumMeanAbsP",
        "peakMaxAbsEdgeFlux","peakEdgeIndex","peakEdgeFrom","peakEdgeTo","peakEdgeFlux","peakConcentration",
        "leader0_from","leader0_to",
        "visibilityStateStart","wasHidden",
        "lateAbsAvgMs","lateAbsP95Ms","lateAbsMaxMs","missedTicks",
        "baselineMode","stepMode"
      ];

      const traceHeader = [
        "schema","runId","runIndex","repIndex",
        "pressCUsed","baseDampUsed","dt","everyMs",
        "busThreshUsed","capLawHash",
        "ampB","ampD","ampSum",
        "tick","tMs","lateByMs","basin",
        "sumAbsFlux","meanAbsP",
        "maxAbsEdgeFlux","maxEdgeIndex","maxEdgeFrom","maxEdgeTo","maxEdgeFlux","concentration",
        "flux_114_89","flux_114_79","flux_136_89","flux_136_79"
      ];

      const summaryLines = [this._csvRow(summaryHeader)];
      const traceLines = [this._csvRow(traceHeader)];

      // preflight sanity: do we see bus turn-on at a "should be on" ampD?
      console.log(`[16o_v2] Preflight: ampD=5.75 x3 @ pressC=${pressCUsed}, damp=${baseDampUsed}, dt=${this.cfg.dt}`);
      for (let i = 0; i < 3; i++) {
        if (this._stop) break;
        await this._baselineRestoreOrSnapshot(phy);
        const cap = await this._recomputeDerived(this.cfg.dt);
        await this._modeSelect(phy, pressCUsed, baseDampUsed);
        // inject once, step a bit, see peak
        this._injectById(phy, 114, this.cfg.ampB);
        this._injectById(phy, 136, 5.75);
        let p114 = 0, p136 = 0;
        const edgeIndex = this._buildEdgeIndex(phy);
        const i114_89 = edgeIndex.get("114->89"); const i114_79 = edgeIndex.get("114->79");
        const i136_89 = edgeIndex.get("136->89"); const i136_79 = edgeIndex.get("136->79");
        for (let t = 0; t < 15; t++) {
          phy.step(this.cfg.dt, pressCUsed, baseDampUsed);
          const f114 = Math.max(Math.abs(this._edgeFlux(phy, i114_89)), Math.abs(this._edgeFlux(phy, i114_79)));
          const f136 = Math.max(Math.abs(this._edgeFlux(phy, i136_89)), Math.abs(this._edgeFlux(phy, i136_79)));
          p114 = Math.max(p114, f114); p136 = Math.max(p136, f136);
        }
        console.log(`[16o_v2] Preflight rep ${i+1}: peak114≈${p114.toFixed(3)}, peak136≈${p136.toFixed(3)}, capLawHash=${cap.capLawHash}`);
      }
      console.log("[16o_v2] Preflight done. If those peaks are ~0.02 again, stop and we’ll fix the manifold before wasting runs.");

      const statsByAmpD = new Map();

      let runIndex = 0;

      const percentile = (arr, p) => {
        if (!arr.length) return 0;
        const a = arr.slice().sort((x,y)=>x-y);
        const idx = (p/100) * (a.length - 1);
        const lo = Math.floor(idx), hi = Math.ceil(idx);
        if (lo === hi) return a[lo];
        const t = idx - lo;
        return a[lo]*(1-t) + a[hi]*t;
      };

      for (const item of plan) {
        if (this._stop) break;

        const ampD = item.ampD;
        const repIndex = item.rep;
        const ampB = this.cfg.ampB;
        const ampSum = ampB + ampD;

        const rid = `${this._isoForId(new Date())}_r${String(runIndex).padStart(5,"0")}_rep${repIndex}_aD${ampD}`;

        const visibilityStateStart = document.visibilityState || "";
        let wasHidden = !!document.hidden;
        const onVis = () => { if (document.hidden) wasHidden = true; };
        document.addEventListener("visibilitychange", onVis, { passive: true });

        // baseline restore
        const baselineInfo = await this._baselineRestoreOrSnapshot(phy);

        // force derived recompute (caplaw)
        const cap = await this._recomputeDerived(this.cfg.dt);

        // mode select
        await this._modeSelect(phy, pressCUsed, baseDampUsed);

        // settle steps
        let stepMode = "dt_press_damp";
        for (let s = 0; s < this.cfg.settleTicks; s++) {
          try { phy.step(this.cfg.dt, pressCUsed, baseDampUsed); }
          catch (e) { phy.step(this.cfg.dt); stepMode = "dt_only"; }
        }

        // inject payload at tick 0
        this._injectById(phy, 114, ampB);
        this._injectById(phy, 136, ampD);

        const edgeIndex = this._buildEdgeIndex(phy);

        const idx114_89 = edgeIndex.get("114->89");
        const idx114_79 = edgeIndex.get("114->79");
        const idx136_89 = edgeIndex.get("136->89");
        const idx136_79 = edgeIndex.get("136->79");

        const bus114Abs = [];
        const bus136Abs = [];
        const sumAbsArr = [];
        const meanAbsPArr = [];
        const maxMeta = [];

        let leader0_from = "", leader0_to = "";

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
          while (true) { if (performance.now() >= target) break; }

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

          if (tick === 0) { leader0_from = fm.maxEdgeFrom; leader0_to = fm.maxEdgeTo; }

          const f114_89 = (idx114_89 != null) ? this._edgeFlux(phy, idx114_89) : 0;
          const f114_79 = (idx114_79 != null) ? this._edgeFlux(phy, idx114_79) : 0;
          const f136_89 = (idx136_89 != null) ? this._edgeFlux(phy, idx136_89) : 0;
          const f136_79 = (idx136_79 != null) ? this._edgeFlux(phy, idx136_79) : 0;

          const a114 = Math.max(Math.abs(f114_89), Math.abs(f114_79));
          const a136 = Math.max(Math.abs(f136_89), Math.abs(f136_79));

          bus114Abs.push(a114);
          bus136Abs.push(a136);
          sumAbsArr.push(fm.sumAbsFlux);
          meanAbsPArr.push(fm.meanAbsP);
          maxMeta.push({ tick, tMs: (now - startMs), ...fm });

          traceLines.push(this._csvRow([
            this.version, rid, runIndex, repIndex,
            pressCUsed, baseDampUsed, this.cfg.dt, this.cfg.everyMs,
            this.cfg.busThreshUsed, (cap.capLawHash ?? ""),
            ampB, ampD, ampSum,
            tick, (now - startMs), lateByMs, basin,
            fm.sumAbsFlux, fm.meanAbsP,
            fm.maxAbsEdgeFlux, fm.maxEdgeIndex, fm.maxEdgeFrom, fm.maxEdgeTo, fm.maxEdgeFlux, fm.concentration,
            f114_89, f114_79, f136_89, f136_79
          ]));

          // missed tick crude detector
          if (tick > 0) {
            const prevTarget = startMs + (tick - 1) * this.cfg.everyMs;
            const prevNow = now - this.cfg.everyMs; // rough
            if ((target - prevTarget) > this.cfg.everyMs * 1.5 || (now - prevNow) > this.cfg.everyMs * 1.5) missedTicks++;
          }
        }

        document.removeEventListener("visibilitychange", onVis);

        const findOnset = (arr) => {
          for (let i = 0; i < arr.length; i++) if (arr[i] >= this.cfg.busThreshUsed) return i;
          return null;
        };

        const onset114 = findOnset(bus114Abs);
        const onset136 = findOnset(bus136Abs);

        const peakOf = (arr) => {
          let best = -Infinity, bestTick = 0;
          for (let i = 0; i < arr.length; i++) if (arr[i] > best) { best = arr[i]; bestTick = i; }
          return { tick: bestTick, abs: (best === -Infinity ? 0 : best) };
        };

        const peak114 = peakOf(bus114Abs);
        const peak136 = peakOf(bus136Abs);

        let outcome = "none";
        if (onset114 != null && onset136 != null) outcome = "bothOn";
        else if (onset114 != null) outcome = "only114";
        else if (onset136 != null) outcome = "only136";

        let winner = "none";
        if (onset114 != null && onset136 != null) {
          if (onset114 < onset136) winner = "114";
          else if (onset136 < onset114) winner = "136";
          else winner = "tie";
        }

        const glow114 = (outcome === "none" && peak114.abs >= this.cfg.glowLo && peak114.abs <= this.cfg.glowHi) ? 1 : 0;
        const glow136 = (outcome === "none" && peak136.abs >= this.cfg.glowLo && peak136.abs <= this.cfg.glowHi) ? 1 : 0;

        // peak sumAbs
        let peakSumAbsFlux = -1, peakSumAtTick = 0;
        for (let i = 0; i < sumAbsArr.length; i++) if (sumAbsArr[i] > peakSumAbsFlux) { peakSumAbsFlux = sumAbsArr[i]; peakSumAtTick = i; }
        const peakSumMeta = maxMeta[peakSumAtTick] || {};

        // peak maxAbsEdgeFlux
        let peakEdge = null;
        for (const m of maxMeta) if (!peakEdge || m.maxAbsEdgeFlux > peakEdge.maxAbsEdgeFlux) peakEdge = m;
        peakEdge = peakEdge || {};

        const lateAbsAvgMs = lateAbs.length ? lateAbs.reduce((a,b)=>a+b,0)/lateAbs.length : 0;
        const lateAbsP95Ms = percentile(lateAbs, 95);
        const lateAbsMaxMs = lateAbs.length ? Math.max(...lateAbs) : 0;

        summaryLines.push(this._csvRow([
          this.version, rid, runIndex, repIndex,
          pressCUsed, baseDampUsed, this.cfg.dt, this.cfg.everyMs, this.cfg.totalTicks, this.cfg.settleTicks,
          this.cfg.busThreshUsed, (cap.capLawHash ?? ""), (cap.capLawSig ?? ""), (cap.capLawApplied ?? ""), (cap.dtUsed ?? ""),
          ampB, ampD, ampSum,
          (onset114 == null ? "" : onset114), peak114.tick, peak114.abs,
          (onset136 == null ? "" : onset136), peak136.tick, peak136.abs,
          outcome, winner,
          glow114, glow136,
          peakSumAbsFlux, peakSumAtTick, (peakSumMeta.tMs ?? ""), (peakSumMeta.meanAbsP ?? ""),
          (peakEdge.maxAbsEdgeFlux ?? ""), (peakEdge.maxEdgeIndex ?? ""), (peakEdge.maxEdgeFrom ?? ""), (peakEdge.maxEdgeTo ?? ""), (peakEdge.maxEdgeFlux ?? ""), (peakEdge.concentration ?? ""),
          leader0_from, leader0_to,
          visibilityStateStart, wasHidden,
          lateAbsAvgMs, lateAbsP95Ms, lateAbsMaxMs, missedTicks,
          baselineInfo.mode,
          stepMode
        ]));

        // update ampD stats
        const s = statsByAmpD.get(ampD) || { bothOn: 0, only114: 0, only136: 0, none: 0, glow: 0, n: 0 };
        s.n += 1;
        s[outcome] = (s[outcome] || 0) + 1;
        if (glow114 || glow136) s.glow += 1;
        statsByAmpD.set(ampD, s);

        runIndex += 1;

        if (runIndex % 25 === 0) {
          console.log(`[16o_v2] progress ${runIndex}/${plan.length} | hidden=${document.hidden} | capLawHash=${cap.capLawHash}`);
        }
      }

      const endTag = this._isoForId(new Date());
      const baseName = `${this.version}_${startTag}_${endTag}`;

      this._unfreezeLiveLoop();

      this._downloadText(`${baseName}_MASTER_summary.csv`, summaryLines.join(""));
      this._downloadText(`${baseName}_MASTER_busTrace.csv`, traceLines.join(""));

      // console quick summary
      const amps = Array.from(statsByAmpD.keys()).sort((a,b)=>a-b);
      console.log("%c[16o_v2] P(bothOn | ampD) quick table:", "color:#ffeb3b;font-weight:bold;");
      for (const a of amps) {
        const s = statsByAmpD.get(a);
        const p = s.n ? (s.bothOn / s.n) : 0;
        console.log(`ampD=${a}  P(bothOn)=${p.toFixed(3)}  (bothOn=${s.bothOn}, only114=${s.only114}, only136=${s.only136}, none=${s.none}, glow=${s.glow})`);
      }

      console.log("%c[16o_v2] DONE. Upload the MASTER_summary + MASTER_busTrace.", "color:#4caf50;font-weight:bold;");
      return { baseName, runs: runIndex, stopped: this._stop };
    }
  };

  window.solPhase311_16o_v2 = T;
  console.log(`✅ solPhase311_16o_v2 installed (${T.version}). Run: await solPhase311_16o_v2.run()`);
})();
