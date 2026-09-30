/* Phase 3.11.16AP — Hard-Baseline History Probe (GlobalBias + Reinforcement Controls)
   Purpose:
     Repeat 16AO, but “hard reset” likely-leaking globals after SOLBaseline.restore(),
     and optionally disable reinforceSemanticStar to test persistence leaks.

   Design (all at damp=20, B2 order: 136@t0, 114@t1):
     Block A:  mB=1.195  reps=60
     Block S:  mB=1.440  reps=30   (stress)
     Block B:  mB=1.195  reps=60   (repeat)

   Hard-baseline controls:
     - hardResetGlobals: true
       * sets physics.globalBias = globalBiasBaseline (default 0)
     - disableReinforceStar: true
       * prevents reinforceSemanticStar from being called during injections

   Outputs (downloaded AFTER all blocks finish):
     - ..._A_pre195_MASTER_summary.csv
     - ..._A_pre195_MASTER_busTrace.csv
     - ..._S_stress144_MASTER_summary.csv
     - ..._S_stress144_MASTER_busTrace.csv
     - ..._B_post195_MASTER_summary.csv
     - ..._B_post195_MASTER_busTrace.csv

   Run:
     await solPhase311_16ap_hardBaselineHistoryProbe_v1.run()

   Stop:
     solPhase311_16ap_hardBaselineHistoryProbe_v1.stop()

   UI-neutral:
     - no camera moves
     - freezes live loop via dtCap
*/
(() => {
  "use strict";

  const P = {
    version: "sol_phase311_16ap_hardBaselineHistoryProbe_v1",
    _stop: false,
    stop() { this._stop = true; },

    cfg: {
      // Timing
      dt: 0.12,
      everyMs: 200,
      spinWaitMs: 1.5,
      totalTicks: 41,
      settleTicks: 3,

      // Pressure
      pressCBase: null,

      // Mode-select priming
      wantId: 82,
      injectorIds: [90, 82],
      dreamBlocks: 15,
      dreamBlockSteps: 2,
      injectAmount: 120,
      finalWriteMult: 1,

      // Protocol constants
      baseAmpB: 4.0,
      baseAmpD: 5.75,
      gain: 22,
      multD: 1.0,

      // Handshake
      nudgeMult: 0.20,
      nudgeOnlyIf136First: false,
      maxHandshakeDelay: 10,
      followWindowTicks: 6,

      // Lane/marker tracking
      markerTickToCheck: 8,
      markerEdges: ["136->139", "136->10", "95->114"],

      // Trace filtering
      includeBackgroundEdges: false,

      // Safety
      abortOnNonFinite: true,

      // Fixed damp + order (B2)
      dampUsed: 20,
      injectTick136: 0,
      injectTick114: 1,

      // Hard baseline controls
      hardResetGlobals: true,
      globalBiasBaseline: 0,
      disableReinforceStar: true,

      // Blocks
      blocks: [
        { tag: "A_pre195",    label: "B2_d20_mB1.195_pre_hardReset",   multBUsed: 1.195, reps: 60 },
        { tag: "S_stress144", label: "B2_d20_mB1.440_stress_hardReset",multBUsed: 1.440, reps: 30 },
        { tag: "B_post195",   label: "B2_d20_mB1.195_post_hardReset",  multBUsed: 1.195, reps: 60 }
      ],

      // Order inside blocks
      shuffleWithinBlock: true
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
    _csvRow(cols) { return cols.map(v => this._csvCell(v)).join(",") + "\n"; },

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

    _getApp() { return window.SOLDashboard || window.solDashboard || window.App || null; },

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
      throw new Error("[16ap] timed out waiting for physics.");
    },

    _freezeLiveLoop() {
      const app = this._getApp();
      if (!app?.config) throw new Error("[16ap] App not ready.");
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
      return { pressC: Number.isFinite(pressC) ? pressC : null };
    },

    _nodeById(phy, id) {
      const want = String(id);
      for (const n of (phy.nodes || [])) if (n?.id != null && String(n.id) === want) return n;
      return null;
    },

    _inject(phy, id, amt) {
      const n = this._nodeById(phy, id);
      if (!n) throw new Error(`[16ap] node not found: ${id}`);
      const a = Math.max(0, Number(amt) || 0);
      n.rho += a;

      // Optional: disable reinforcement as a persistence-control
      if (this.cfg.disableReinforceStar) return;

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
      if (idx == null) return 0;
      const e = (phy.edges || [])[idx];
      const f = (e && typeof e.flux === "number" && Number.isFinite(e.flux)) ? e.flux : 0;
      return f;
    },

    _top2Edges(phy, includeBackgroundEdges) {
      const edges = phy.edges || [];
      let best1 = { af: -1, from: "", to: "", flux: 0 };
      let best2 = { af: -1, from: "", to: "", flux: 0 };

      for (let i = 0; i < edges.length; i++) {
        const e = edges[i];
        if (!e) continue;
        if (!includeBackgroundEdges && e.background) continue;
        const f = (typeof e.flux === "number" && Number.isFinite(e.flux)) ? e.flux : 0;
        const af = Math.abs(f);
        if (af > best1.af) {
          best2 = best1;
          best1 = { af, from: e.from, to: e.to, flux: f };
        } else if (af > best2.af) {
          best2 = { af, from: e.from, to: e.to, flux: f };
        }
      }
      return { best1, best2 };
    },

    _pickBasin(phy) {
      const n82 = this._nodeById(phy, 82);
      const n90 = this._nodeById(phy, 90);
      const r82 = Number.isFinite(n82?.rho) ? n82.rho : 0;
      const r90 = Number.isFinite(n90?.rho) ? n90.rho : 0;
      return (r90 > r82) ? 90 : 82;
    },

    async _recomputeDerived(dt) {
      try {
        if (window.SOLRuntime?.recomputeDerived) return await window.SOLRuntime.recomputeDerived({ dt });
      } catch(e) {}
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

    _getGlobalBias(phy) {
      const gb = phy?.globalBias;
      return (typeof gb === "number" && Number.isFinite(gb)) ? gb : "";
    },

    _hardResetGlobals(phy) {
      if (!this.cfg.hardResetGlobals) return { didReset: 0, postHardReset: this._getGlobalBias(phy) };
      try {
        // The main suspect: globalBias as a slowly-accumulating hidden state
        phy.globalBias = this.cfg.globalBiasBaseline;
      } catch(e) {}
      return { didReset: 1, postHardReset: this._getGlobalBias(phy) };
    },

    async _baselineRestore(phy) {
      const pre = this._getGlobalBias(phy);

      let baselineMode = "";
      if (window.SOLBaseline?.restore) {
        await window.SOLBaseline.restore();
        baselineMode = "SOLBaseline.restore";
      } else {
        if (!this._snap) {
          this._snap = this._snapshot(phy);
          baselineMode = "internal_snapshot_created";
        } else {
          this._restore(phy, this._snap);
          baselineMode = "internal_snapshot_restored";
        }
      }

      const post = this._getGlobalBias(phy);
      const hr = this._hardResetGlobals(phy);
      const postHR = hr.postHardReset;

      return { baselineMode, globalBias_preRestore: pre, globalBias_postRestore: post, hardResetDidRun: hr.didReset, globalBias_postHardReset: postHR };
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

    _isFiniteNums(nums) {
      for (const v of nums) if (typeof v !== "number" || !Number.isFinite(v)) return false;
      return true;
    },

    async _runBlock(phy, edgeIndex, pressCUsed, block, globalRunBaseIndex) {
      const g = this.cfg;

      // Bus edges (+ stitch)
      const i114_89 = edgeIndex.get("114->89");
      const i114_79 = edgeIndex.get("114->79");
      const i136_89 = edgeIndex.get("136->89");
      const i136_79 = edgeIndex.get("136->79");
      const i89_79  = edgeIndex.get("89->79");

      const busSet = new Set(["114->89","114->79","136->89","136->79"]);
      const is114Bus = (pair) => pair === "114->89" || pair === "114->79";
      const is136Bus = (pair) => pair === "136->89" || pair === "136->79";

      const baseB = g.baseAmpB * g.gain; // 88
      const baseD = g.baseAmpD * g.gain; // 126.5
      const ampD  = baseD * g.multD;

      const ampB0 = baseB * block.multBUsed;
      const ampB_nudge = ampB0 * g.nudgeMult;

      const plan = [];
      for (let r = 1; r <= block.reps; r++) plan.push({ rep: r });
      if (g.shuffleWithinBlock) this._shuffle(plan);

      const summaryHeader = [
        "schema","blockTag","runId","globalRunIndex","blockRunIndex","repIndex",
        "label",
        "baselineMode","hardResetGlobals","globalBiasBaseline","hardResetDidRun",
        "globalBias_preRestore","globalBias_postRestore","globalBias_postHardReset","globalBias_end",
        "disableReinforceStar",
        "pressCUsed","dampUsed",
        "capLawHash","capLawSig","capLawApplied","capLawDtUsed",
        "gain","baseB","baseD","multBUsed","multD",
        "ampB0","ampD","ratioBD","ampDiff_BminusD",
        "injectTick136","injectTick114",
        "nudgeMult","nudgeOnlyIf136First",
        "arbiter_tick","arbiter_edge","arbiter_owner",
        "abs114_89_atArb","abs136_89_atArb","deltaAbs_114minus136_atArb",
        "handshake_tick","handshake_applied",
        "first114Max_tick","first136Max_tick","precedence",
        "deltaTicks","fastFollow","packetClass",
        "peak114_abs","peak136_abs","cross_peakAbs_89_79",
        "max1_at_markerTick","first_marker_tick",
        "visibilityStateStart","wasHidden",
        "runStatus","abort_tick","abort_reason"
      ];

      const traceHeader = [
        "schema","blockTag","runId","globalRunIndex","blockRunIndex","repIndex",
        "capLawHash",
        "pressCUsed","dampUsed","multBUsed","ampB0","ampD",
        "globalBias",
        "tick","tMs","lateByMs","basin",
        "max1_from","max1_to","max1_absFlux",
        "max2_from","max2_to","max2_absFlux",
        "flux_114_89","flux_114_79","flux_136_89","flux_136_79",
        "flux_89_79",
        "handshake_pending","handshake_applied_tick"
      ];

      const summaryLines = [this._csvRow(summaryHeader)];
      const traceLines = [this._csvRow(traceHeader)];

      console.log(`[16ap:${block.tag}] reps=${block.reps} mB=${block.multBUsed} ampB0=${ampB0.toFixed(2)} ampD=${ampD.toFixed(2)} (damp=${g.dampUsed})`);

      let blockRunIndex = 0;

      for (const item of plan) {
        if (this._stop) break;

        const repIndex = item.rep;
        const globalRunIndex = globalRunBaseIndex + blockRunIndex;

        const runId =
          `${this._iso(new Date())}_${block.tag}_g${String(globalRunIndex).padStart(6,"0")}_b${String(blockRunIndex).padStart(4,"0")}_rep${repIndex}`;

        const visibilityStateStart = document.visibilityState || "";
        let wasHidden = !!document.hidden;
        const onVis = () => { if (document.hidden) wasHidden = true; };
        document.addEventListener("visibilitychange", onVis, { passive: true });

        const baseInfo = await this._baselineRestore(phy);
        const cap = await this._recomputeDerived(g.dt);

        await this._modeSelect(phy, pressCUsed, g.dampUsed);
        for (let s = 0; s < g.settleTicks; s++) phy.step(g.dt, pressCUsed, g.dampUsed);

        let arbiter_tick = null;
        let arbiter_edge = "";
        let arbiter_owner = "";
        let handshake_tick = null;
        let handshake_applied = 0;
        let handshake_pending = 0;
        let handshake_applied_tick = "";

        let abs114_89_atArb = "";
        let abs136_89_atArb = "";
        let deltaAbs_atArb = "";

        let first114Max_tick = null;
        let first136Max_tick = null;

        let peak114_abs = 0;
        let peak136_abs = 0;
        let cross_peakAbs_89_79 = 0;

        let max1_at_markerTick = "";
        let first_marker_tick = "";

        let runStatus = "ok";
        let abort_tick = "";
        let abort_reason = "";

        const startMs = performance.now();

        for (let tick = 0; tick < g.totalTicks; tick++) {
          if (this._stop) break;

          const target = startMs + tick * g.everyMs;

          while (true) {
            const now = performance.now();
            const remain = target - now;
            if (remain <= 0) break;
            if (g.spinWaitMs > 0 && remain <= g.spinWaitMs) break;
            await this._sleep(Math.min(10, Math.max(0, remain - (g.spinWaitMs || 0))));
          }
          while (performance.now() < target) {}

          const now = performance.now();
          const lateByMs = now - target;

          // Injections (B2 order): 136 first, 114 second
          if (tick === g.injectTick136) this._inject(phy, 136, ampD);
          if (tick === g.injectTick114) this._inject(phy, 114, ampB0);

          // Handshake injection (pre-step)
          if (handshake_tick === tick && ampB_nudge > 0) {
            this._inject(phy, 114, ampB_nudge);
            handshake_applied = 1;
            handshake_applied_tick = String(tick);
          }

          phy.step(g.dt, pressCUsed, g.dampUsed);

          const basin = this._pickBasin(phy);
          const top2 = this._top2Edges(phy, g.includeBackgroundEdges);
          const max1Pair = `${top2.best1.from}->${top2.best1.to}`;

          if (tick === g.markerTickToCheck) max1_at_markerTick = max1Pair;
          if (!first_marker_tick && g.markerEdges.includes(max1Pair)) first_marker_tick = String(tick);

          const f114_89 = (i114_89 != null) ? this._edgeFlux(phy, i114_89) : 0;
          const f114_79 = (i114_79 != null) ? this._edgeFlux(phy, i114_79) : 0;
          const f136_89 = (i136_89 != null) ? this._edgeFlux(phy, i136_89) : 0;
          const f136_79 = (i136_79 != null) ? this._edgeFlux(phy, i136_79) : 0;
          const f89_79  = (i89_79  != null) ? this._edgeFlux(phy, i89_79)  : 0;

          if (g.abortOnNonFinite) {
            const ok = this._isFiniteNums([top2.best1.af, top2.best2.af, f114_89,f114_79,f136_89,f136_79,f89_79]);
            if (!ok) {
              runStatus = "aborted";
              abort_tick = String(tick);
              abort_reason = "non_finite_flux";
              break;
            }
          }

          peak114_abs = Math.max(peak114_abs, Math.max(Math.abs(f114_89), Math.abs(f114_79)));
          peak136_abs = Math.max(peak136_abs, Math.max(Math.abs(f136_89), Math.abs(f136_79)));
          cross_peakAbs_89_79 = Math.max(cross_peakAbs_89_79, Math.abs(f89_79));

          // Arbiter detection: first tick where max1 is a bus edge
          if (arbiter_tick == null && busSet.has(max1Pair)) {
            arbiter_tick = tick;
            arbiter_edge = max1Pair;
            arbiter_owner = is136Bus(max1Pair) ? "136" : (is114Bus(max1Pair) ? "114" : "");

            // record margin at arb tick for the main contest edge pair
            const a114 = Math.abs(f114_89);
            const a136 = Math.abs(f136_89);
            abs114_89_atArb = a114;
            abs136_89_atArb = a136;
            deltaAbs_atArb = (a114 - a136);

            const nextTick = tick + 1;
            const within = (nextTick < g.totalTicks) && ((nextTick - tick) <= g.maxHandshakeDelay);
            if (within) {
              handshake_tick = nextTick;
              handshake_pending = 1;
            }
          }

          // Onset ticks for each bus owner based on max1 being a bus edge
          if (busSet.has(max1Pair)) {
            if (is114Bus(max1Pair) && first114Max_tick == null) first114Max_tick = tick;
            if (is136Bus(max1Pair) && first136Max_tick == null) first136Max_tick = tick;
          }

          traceLines.push(this._csvRow([
            this.version, block.tag, runId, globalRunIndex, blockRunIndex, repIndex,
            (cap.capLawHash ?? ""),
            pressCUsed, g.dampUsed, block.multBUsed, ampB0, ampD,
            this._getGlobalBias(phy),
            tick, (now - startMs), lateByMs, basin,
            top2.best1.from, top2.best1.to, top2.best1.af,
            top2.best2.from, top2.best2.to, top2.best2.af,
            f114_89, f114_79, f136_89, f136_79,
            f89_79,
            handshake_pending,
            handshake_applied_tick
          ]));
        }

        document.removeEventListener("visibilitychange", onVis);

        // Precedence + packet class
        let precedence = "";
        if (first114Max_tick != null && first136Max_tick != null) {
          if (first114Max_tick < first136Max_tick) precedence = "114_first";
          else if (first136Max_tick < first114Max_tick) precedence = "136_first";
          else precedence = "tie";
        } else if (first114Max_tick != null) precedence = "114_only";
        else if (first136Max_tick != null) precedence = "136_only";
        else precedence = "none";

        const deltaTicks =
          (first114Max_tick != null && first136Max_tick != null)
            ? Math.abs(first114Max_tick - first136Max_tick)
            : "";

        const fastFollow =
          (first114Max_tick != null && first136Max_tick != null && Math.abs(first114Max_tick - first136Max_tick) <= g.followWindowTicks)
            ? 1 : 0;

        let packetClass = "";
        if (precedence === "136_first" && fastFollow) packetClass = "136_then_114_fast";
        else if (precedence === "136_first") packetClass = "136_then_114_slow";
        else if (precedence === "114_first" && fastFollow) packetClass = "114_then_136_fast";
        else if (precedence === "114_first") packetClass = "114_then_136_slow";
        else if (precedence === "136_only") packetClass = "136_solo";
        else if (precedence === "114_only") packetClass = "114_solo";
        else packetClass = precedence;

        const globalBias_end = this._getGlobalBias(phy);

        summaryLines.push(this._csvRow([
          this.version, block.tag, runId, globalRunIndex, blockRunIndex, repIndex,
          block.label,
          baseInfo.baselineMode, (g.hardResetGlobals ? 1 : 0), g.globalBiasBaseline, baseInfo.hardResetDidRun,
          baseInfo.globalBias_preRestore, baseInfo.globalBias_postRestore, baseInfo.globalBias_postHardReset, globalBias_end,
          (g.disableReinforceStar ? 1 : 0),
          pressCUsed, g.dampUsed,
          (cap.capLawHash ?? ""), (cap.capLawSig ?? ""), (cap.capLawApplied ?? ""), (cap.dtUsed ?? ""),
          g.gain, baseB, baseD, block.multBUsed, g.multD,
          ampB0, ampD, (ampB0 / ampD), (ampB0 - ampD),
          g.injectTick136, g.injectTick114,
          g.nudgeMult, (g.nudgeOnlyIf136First ? 1 : 0),
          (arbiter_tick == null ? "" : arbiter_tick),
          arbiter_edge,
          arbiter_owner,
          abs114_89_atArb,
          abs136_89_atArb,
          deltaAbs_atArb,
          (handshake_tick == null ? "" : handshake_tick),
          handshake_applied,
          (first114Max_tick == null ? "" : first114Max_tick),
          (first136Max_tick == null ? "" : first136Max_tick),
          precedence,
          deltaTicks,
          fastFollow,
          packetClass,
          peak114_abs,
          peak136_abs,
          cross_peakAbs_89_79,
          max1_at_markerTick,
          first_marker_tick,
          visibilityStateStart,
          wasHidden,
          runStatus,
          abort_tick,
          abort_reason
        ]));

        if ((blockRunIndex + 1) % 20 === 0) console.log(`[16ap:${block.tag}] progress ${blockRunIndex + 1}/${block.reps}`);

        blockRunIndex += 1;
      }

      return { summaryLines, traceLines, runs: blockRunIndex };
    },

    async run(userCfg = {}) {
      this._stop = false;
      this.cfg = { ...this.cfg, ...userCfg };

      const g = this.cfg;
      const phy = await this._waitForPhysics();
      this._freezeLiveLoop();

      const ui = this._readUiParams();
      const inv = window.SOLRuntime?.getInvariants?.() || {};
      const pressCUsed =
        (g.pressCBase != null) ? g.pressCBase :
        (inv.pressC ?? ui.pressC ?? 2.0);

      const edgeIndex = this._buildEdgeIndex(phy);

      const startTag = this._iso(new Date());
      console.log(
        `[16ap] START ${this.version} @ ${startTag} | pressC=${pressCUsed} | damp=${g.dampUsed} | ` +
        `hardResetGlobals=${g.hardResetGlobals} globalBiasBaseline=${g.globalBiasBaseline} disableReinforceStar=${g.disableReinforceStar}`
      );

      const out = [];
      let globalRunBaseIndex = 0;

      for (const block of g.blocks) {
        if (this._stop) break;

        // Extra baseline restore at the start of each block (belt + suspenders)
        await this._baselineRestore(phy);

        const res = await this._runBlock(phy, edgeIndex, pressCUsed, block, globalRunBaseIndex);
        out.push({ block, ...res });
        globalRunBaseIndex += res.runs;

        if (this._stop) break;
      }

      const endTag = this._iso(new Date());
      const baseName = `${this.version}_${startTag}_${endTag}`;

      this._unfreezeLiveLoop();

      for (const o of out) {
        this._download(`${baseName}_${o.block.tag}_MASTER_summary.csv`, o.summaryLines.join(""));
        this._download(`${baseName}_${o.block.tag}_MASTER_busTrace.csv`, o.traceLines.join(""));
      }

      const blockStats = out.map(o => `${o.block.tag}:${o.runs}`).join(" | ");
      console.log(
        `[16ap] DONE @ ${endTag} | ${blockStats}\n` +
        `BaseName: ${baseName}\n` +
        out.map(o => `- ${baseName}_${o.block.tag}_MASTER_summary.csv\n- ${baseName}_${o.block.tag}_MASTER_busTrace.csv`).join("\n")
      );

      return {
        baseName,
        pressCUsed,
        dampUsed: g.dampUsed,
        hardResetGlobals: g.hardResetGlobals,
        globalBiasBaseline: g.globalBiasBaseline,
        disableReinforceStar: g.disableReinforceStar,
        blocks: out.map(o => ({ tag: o.block.tag, runs: o.runs, multBUsed: o.block.multBUsed })),
        stopped: this._stop
      };
    }
  };

  window.solPhase311_16ap_hardBaselineHistoryProbe_v1 = P;
  console.log(`✅ solPhase311_16ap_hardBaselineHistoryProbe_v1 installed (${P.version}). Run: await solPhase311_16ap_hardBaselineHistoryProbe_v1.run()`);
})();
