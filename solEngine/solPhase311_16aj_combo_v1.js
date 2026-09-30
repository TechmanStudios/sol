/* Phase 3.11.16AJ — Combo Script (sequential sections, multi-output)
   What this runs (in order):

   SECTION A2: Gate transition refinement (damp cliff mapping)
     - dampUsedList: [15,16,17,18,19,20,21,22]
     - repsPerDamp: 30
     - injections: 136@t0, 114@t1 (classic)
     - nudgeOnlyIf136First: true (classic)

   SECTION C1: Inversion attempt — Order Swap
     - dampUsedList: [4,12,20]
     - repsPerDamp: 40
     - injections: 114@t0, 136@t1 (swapped)
     - nudgeOnlyIf136First: false (so handshake still applies if 114 wins)

   SECTION C2: Inversion attempt — Spacing Sweep (keep 136 first, stretch 114 timing)
     - dampUsed: 18 (the gate cliff)
     - spacingTicksList (114 tick): [1,2,4,8,12] with 136 fixed at tick 0
     - repsPerSpacing: 30
     - nudgeOnlyIf136First: false (don’t bias against 114 wins)

   Outputs (downloads AFTER all sections finish):
     - ..._A2_gateRefine_MASTER_summary.csv
     - ..._A2_gateRefine_MASTER_busTrace.csv
     - ..._C1_orderSwap_MASTER_summary.csv
     - ..._C1_orderSwap_MASTER_busTrace.csv
     - ..._C2_spacingSweep_MASTER_summary.csv
     - ..._C2_spacingSweep_MASTER_busTrace.csv

   Run:
     await solPhase311_16aj_combo_v1.run()

   Stop:
     solPhase311_16aj_combo_v1.stop()

   Baseline:
     - Restores baseline at the start of EVERY run via SOLBaseline.restore() when available.
     - UI-neutral: no camera moves.
*/
(() => {
  "use strict";

  const X = {
    version: "sol_phase311_16aj_comboGateRefine_OrderSwap_SpacingSweep_v1",
    _stop: false,
    stop() { this._stop = true; },

    cfg: {
      // Timing
      dt: 0.12,
      everyMs: 200,
      spinWaitMs: 1.5,
      settleTicks: 3,
      totalTicks: 41,

      // If null: auto from SOLRuntime invariants/UI fallback
      pressCBase: null,

      // Mode-select priming (consistent with prior phases)
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
      multB: 1.144,
      multD: 1.0,

      // Adaptive handshake
      nudgeMult: 0.20,
      maxHandshakeDelay: 10,
      followWindowTicks: 6,

      // Trace edge filtering
      includeBackgroundEdges: false,

      // Marker moment (useful for lane classification)
      markerTickToCheck: 8,
      markerEdges: ["136->139", "136->10"],

      // Safety
      abortOnNonFinite: true,

      // --- SECTION A2 ---
      sectionA2: {
        tag: "A2_gateRefine",
        dampUsedList: [15, 16, 17, 18, 19, 20, 21, 22],
        repsPerCond: 30,
        shuffle: true,
        injectTick136: 0,
        injectTick114: 1,
        nudgeOnlyIf136First: true,
        label: "classic_order_spacing1"
      },

      // --- SECTION C1 ---
      sectionC1: {
        tag: "C1_orderSwap",
        dampUsedList: [4, 12, 20],
        repsPerCond: 40,
        shuffle: true,
        injectTick136: 1,
        injectTick114: 0,
        nudgeOnlyIf136First: false,
        label: "order_swapped_spacing1"
      },

      // --- SECTION C2 ---
      sectionC2: {
        tag: "C2_spacingSweep",
        dampUsed: 18,
        spacingTicksList: [1, 2, 4, 8, 12], // 114 tick; 136 fixed at 0
        repsPerSpacing: 30,
        shuffle: true,
        injectTick136: 0,
        nudgeOnlyIf136First: false,
        label: "classic_order_spacingSweep"
      }
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
      throw new Error("[16aj] timed out waiting for physics.");
    },

    _freezeLiveLoop() {
      const app = this._getApp();
      if (!app?.config) throw new Error("[16aj] App not ready.");
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
      if (!n) throw new Error(`[16aj] node not found: ${id}`);
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

    _isFiniteNums(nums) {
      for (const v of nums) if (typeof v !== "number" || !Number.isFinite(v)) return false;
      return true;
    },

    _laneClassFromMarker(pair) {
      if (pair === "136->139") return "lane_A_136to139";
      if (pair === "136->10") return "lane_B_136to10";
      if (pair) return `lane_other_${pair}`;
      return "lane_C_no_marker";
    },

    async _runGridSection(phy, edgeIndex, pressCBase, sec) {
      const g = this.cfg;
      const tag = sec.tag;

      const baseB = g.baseAmpB * g.gain;
      const baseD = g.baseAmpD * g.gain;
      const ampB0 = baseB * g.multB;
      const ampD  = baseD * g.multD;
      const ratioBD = ampB0 / ampD;
      const ampB_nudge = ampB0 * g.nudgeMult;

      // Bus edges (plus stitch)
      const i114_89 = edgeIndex.get("114->89");
      const i114_79 = edgeIndex.get("114->79");
      const i136_89 = edgeIndex.get("136->89");
      const i136_79 = edgeIndex.get("136->79");
      const i89_79  = edgeIndex.get("89->79");

      const busSet = new Set(["114->89","114->79","136->89","136->79"]);
      const is114Bus = (pair) => pair === "114->89" || pair === "114->79";
      const is136Bus = (pair) => pair === "136->89" || pair === "136->79";

      const plan = [];
      for (const dampUsed of sec.dampUsedList) {
        for (let r = 1; r <= sec.repsPerCond; r++) {
          plan.push({ dampUsed, rep: r, injectTick136: sec.injectTick136, injectTick114: sec.injectTick114, spacingTicks: sec.injectTick114 - sec.injectTick136 });
        }
      }
      if (sec.shuffle) this._shuffle(plan);

      const summaryHeader = [
        "schema","section","runId","runIndex","repIndex",
        "label",
        "pressCBase","pressCUsed","dampUsed",
        "dt","everyMs","totalTicks","settleTicks",
        "capLawHash","capLawSig","capLawApplied","capLawDtUsed",
        "gain","multB","multD",
        "ampB0","ampD","ratioBD",
        "injectTick136","injectTick114","spacingTicks",
        "nudgeOnlyIf136First",
        "arbiter_tick","arbiter_edge","arbiter_owner",
        "handshake_tick","handshake_applied",
        "first114Max_tick","first136Max_tick","precedence",
        "deltaTicks","fastFollow","packetClass",
        "peak114_abs","peak136_abs",
        "cross_peakAbs_89_79",
        "max1_at_markerTick","laneClass","first_marker_tick",
        "arbiterOwner114","precedenceStarts114",
        "visibilityStateStart","wasHidden",
        "runStatus","abort_tick","abort_reason"
      ];

      const traceHeader = [
        "schema","section","runId","runIndex","repIndex",
        "capLawHash",
        "pressCUsed","dampUsed",
        "tick","tMs","lateByMs","basin",
        "max1_from","max1_to","max1_absFlux",
        "max2_from","max2_to","max2_absFlux",
        "flux_114_89","flux_114_79","flux_136_89","flux_136_79",
        "flux_89_79",
        "handshake_pending","handshake_applied_tick"
      ];

      const summaryLines = [this._csvRow(summaryHeader)];
      const traceLines = [this._csvRow(traceHeader)];

      console.log(
        `[16aj:${tag}] plan=${plan.length} | damps=[${sec.dampUsedList.join(",")}] reps=${sec.repsPerCond}` +
        ` | inject(136@${sec.injectTick136},114@${sec.injectTick114}) spacing=${sec.injectTick114 - sec.injectTick136}` +
        ` | nudgeOnlyIf136First=${sec.nudgeOnlyIf136First}`
      );

      let runIndex = 0;

      for (const item of plan) {
        if (this._stop) break;

        const repIndex = item.rep;
        const dampUsed = item.dampUsed;
        const pressCUsed = pressCBase;

        const runId =
          `${this._iso(new Date())}_r${String(runIndex).padStart(6,"0")}` +
          `_d${Number(dampUsed).toFixed(3)}_rep${repIndex}`;

        const visibilityStateStart = document.visibilityState || "";
        let wasHidden = !!document.hidden;
        const onVis = () => { if (document.hidden) wasHidden = true; };
        document.addEventListener("visibilitychange", onVis, { passive: true });

        await this._baselineRestore(phy);
        const cap = await this._recomputeDerived(g.dt);

        await this._modeSelect(phy, pressCUsed, dampUsed);
        for (let s = 0; s < g.settleTicks; s++) phy.step(g.dt, pressCUsed, dampUsed);

        let arbiter_tick = null;
        let arbiter_edge = "";
        let arbiter_owner = "";
        let handshake_tick = null;
        let handshake_applied = 0;
        let handshake_pending = 0;
        let handshake_applied_tick = "";

        let first114Max_tick = null;
        let first136Max_tick = null;

        let peak114_abs = 0;
        let peak136_abs = 0;
        let cross_peakAbs_89_79 = 0;

        let max1_at_markerTick = "";
        let laneClass = "";
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

          // Injections (pre-step)
          if (tick === item.injectTick136) this._inject(phy, 136, ampD);
          if (tick === item.injectTick114) this._inject(phy, 114, ampB0);

          // Handshake injection (pre-step, scheduled from arbiter_tick)
          if (handshake_tick === tick && ampB_nudge > 0) {
            this._inject(phy, 114, ampB_nudge);
            handshake_applied = 1;
            handshake_applied_tick = String(tick);
          }

          phy.step(g.dt, pressCUsed, dampUsed);

          const basin = this._pickBasin(phy);
          const top2 = this._top2Edges(phy, g.includeBackgroundEdges);
          const max1Pair = `${top2.best1.from}->${top2.best1.to}`;

          if (tick === g.markerTickToCheck) {
            max1_at_markerTick = max1Pair;
            laneClass = this._laneClassFromMarker(max1Pair);
          }

          if (!first_marker_tick && g.markerEdges.includes(max1Pair)) first_marker_tick = String(tick);

          const f114_89 = (i114_89 != null) ? this._edgeFlux(phy, i114_89) : 0;
          const f114_79 = (i114_79 != null) ? this._edgeFlux(phy, i114_79) : 0;
          const f136_89 = (i136_89 != null) ? this._edgeFlux(phy, i136_89) : 0;
          const f136_79 = (i136_79 != null) ? this._edgeFlux(phy, i136_79) : 0;
          const f89_79  = this._edgeFlux(phy, i89_79);

          if (g.abortOnNonFinite) {
            const ok = this._isFiniteNums([top2.best1.af, top2.best2.af, f114_89,f114_79,f136_89,f136_79,f89_79]);
            if (!ok) {
              runStatus = "aborted";
              abort_tick = String(tick);
              abort_reason = "non_finite_flux";
              console.warn(`[16aj:${tag}] ABORT runIndex=${runIndex} damp=${dampUsed} rep=${repIndex} tick=${tick}: non-finite sample`);
              break;
            }
          }

          peak114_abs = Math.max(peak114_abs, Math.max(Math.abs(f114_89), Math.abs(f114_79)));
          peak136_abs = Math.max(peak136_abs, Math.max(Math.abs(f136_89), Math.abs(f136_79)));
          cross_peakAbs_89_79 = Math.max(cross_peakAbs_89_79, Math.abs(f89_79));

          // Arbiter detection: first tick where max1 is on a bus edge
          if (arbiter_tick == null && busSet.has(max1Pair)) {
            arbiter_tick = tick;
            arbiter_edge = max1Pair;
            arbiter_owner = is136Bus(max1Pair) ? "136" : (is114Bus(max1Pair) ? "114" : "");

            const okOwner = (!sec.nudgeOnlyIf136First) || (arbiter_owner === "136");
            const nextTick = tick + 1;
            const within = (nextTick < g.totalTicks) && ((nextTick - tick) <= g.maxHandshakeDelay);
            if (okOwner && within) {
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
            this.version, tag, runId, runIndex, repIndex,
            (cap.capLawHash ?? ""),
            pressCUsed, dampUsed,
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

        const arbiterOwner114 = (arbiter_owner === "114") ? 1 : 0;
        const precedenceStarts114 = (precedence.startsWith("114")) ? 1 : 0;

        if (!laneClass && max1_at_markerTick) laneClass = this._laneClassFromMarker(max1_at_markerTick);

        summaryLines.push(this._csvRow([
          this.version, tag, runId, runIndex, repIndex,
          sec.label,
          pressCBase, pressCUsed, dampUsed,
          g.dt, g.everyMs, g.totalTicks, g.settleTicks,
          (cap.capLawHash ?? ""), (cap.capLawSig ?? ""), (cap.capLawApplied ?? ""), (cap.dtUsed ?? ""),
          g.gain, g.multB, g.multD,
          ampB0, ampD, ratioBD,
          item.injectTick136, item.injectTick114, item.spacingTicks,
          sec.nudgeOnlyIf136First ? 1 : 0,
          (arbiter_tick == null ? "" : arbiter_tick),
          arbiter_edge,
          arbiter_owner,
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
          laneClass,
          first_marker_tick,
          arbiterOwner114,
          precedenceStarts114,
          visibilityStateStart,
          wasHidden,
          runStatus,
          abort_tick,
          abort_reason
        ]));

        // Progress log: highlight any 114-first / 114-owner events immediately
        if (arbiterOwner114 || precedenceStarts114) {
          console.warn(
            `[16aj:${tag}] 🧲 114-event runIndex=${runIndex} damp=${Number(dampUsed).toFixed(2)} rep=${repIndex}` +
            ` | inject(136@${item.injectTick136},114@${item.injectTick114})` +
            ` | arb=${arbiter_owner}@${arbiter_tick} hs=${handshake_tick} prec=${precedence} class=${packetClass}`
          );
        } else if ((runIndex + 1) % 25 === 0) {
          console.log(`[16aj:${tag}] progress ${(runIndex + 1)}/${plan.length}`);
        }

        runIndex += 1;
      }

      return { summaryLines, traceLines, runs: runIndex };
    },

    async _runSpacingSection(phy, edgeIndex, pressCBase, sec) {
      const g = this.cfg;

      const plan = [];
      for (const spacing of sec.spacingTicksList) {
        for (let r = 1; r <= sec.repsPerSpacing; r++) {
          plan.push({
            dampUsed: sec.dampUsed,
            rep: r,
            injectTick136: sec.injectTick136,
            injectTick114: spacing, // 114 tick
            spacingTicks: spacing - sec.injectTick136
          });
        }
      }
      if (sec.shuffle) this._shuffle(plan);

      // Reuse the grid runner by temporarily mapping into its expected sec-shape
      const secAsGrid = {
        tag: sec.tag,
        dampUsedList: [sec.dampUsed],   // informational only; plan drives
        repsPerCond: 1,                 // not used (plan overrides)
        shuffle: false,
        injectTick136: sec.injectTick136,
        injectTick114: 1,
        nudgeOnlyIf136First: sec.nudgeOnlyIf136First,
        label: sec.label,
        _planOverride: plan
      };

      // Small hack: run the same core but with our own plan
      return await this._runCustomPlanSection(phy, edgeIndex, pressCBase, secAsGrid);
    },

    async _runCustomPlanSection(phy, edgeIndex, pressCBase, sec) {
      // Same as _runGridSection, but uses sec._planOverride (already shuffled)
      const g = this.cfg;
      const tag = sec.tag;
      const plan = sec._planOverride || [];

      const baseB = g.baseAmpB * g.gain;
      const baseD = g.baseAmpD * g.gain;
      const ampB0 = baseB * g.multB;
      const ampD  = baseD * g.multD;
      const ratioBD = ampB0 / ampD;
      const ampB_nudge = ampB0 * g.nudgeMult;

      const i114_89 = edgeIndex.get("114->89");
      const i114_79 = edgeIndex.get("114->79");
      const i136_89 = edgeIndex.get("136->89");
      const i136_79 = edgeIndex.get("136->79");
      const i89_79  = edgeIndex.get("89->79");

      const busSet = new Set(["114->89","114->79","136->89","136->79"]);
      const is114Bus = (pair) => pair === "114->89" || pair === "114->79";
      const is136Bus = (pair) => pair === "136->89" || pair === "136->79";

      const summaryHeader = [
        "schema","section","runId","runIndex","repIndex",
        "label",
        "pressCBase","pressCUsed","dampUsed",
        "dt","everyMs","totalTicks","settleTicks",
        "capLawHash","capLawSig","capLawApplied","capLawDtUsed",
        "gain","multB","multD",
        "ampB0","ampD","ratioBD",
        "injectTick136","injectTick114","spacingTicks",
        "nudgeOnlyIf136First",
        "arbiter_tick","arbiter_edge","arbiter_owner",
        "handshake_tick","handshake_applied",
        "first114Max_tick","first136Max_tick","precedence",
        "deltaTicks","fastFollow","packetClass",
        "peak114_abs","peak136_abs",
        "cross_peakAbs_89_79",
        "max1_at_markerTick","laneClass","first_marker_tick",
        "arbiterOwner114","precedenceStarts114",
        "visibilityStateStart","wasHidden",
        "runStatus","abort_tick","abort_reason"
      ];

      const traceHeader = [
        "schema","section","runId","runIndex","repIndex",
        "capLawHash",
        "pressCUsed","dampUsed",
        "tick","tMs","lateByMs","basin",
        "max1_from","max1_to","max1_absFlux",
        "max2_from","max2_to","max2_absFlux",
        "flux_114_89","flux_114_79","flux_136_89","flux_136_79",
        "flux_89_79",
        "handshake_pending","handshake_applied_tick"
      ];

      const summaryLines = [this._csvRow(summaryHeader)];
      const traceLines = [this._csvRow(traceHeader)];

      console.log(
        `[16aj:${tag}] plan=${plan.length} | damp=${sec._planOverride?.[0]?.dampUsed ?? "?"}` +
        ` | injectTick136=${this.cfg.sectionC2.injectTick136} | spacingTicks=[${this.cfg.sectionC2.spacingTicksList.join(",")}]` +
        ` | repsPerSpacing=${this.cfg.sectionC2.repsPerSpacing} | nudgeOnlyIf136First=${sec.nudgeOnlyIf136First}`
      );

      let runIndex = 0;

      for (const item of plan) {
        if (this._stop) break;

        const repIndex = item.rep;
        const dampUsed = item.dampUsed;
        const pressCUsed = pressCBase;

        const runId =
          `${this._iso(new Date())}_r${String(runIndex).padStart(6,"0")}` +
          `_d${Number(dampUsed).toFixed(3)}_rep${repIndex}_sp${item.spacingTicks}`;

        const visibilityStateStart = document.visibilityState || "";
        let wasHidden = !!document.hidden;
        const onVis = () => { if (document.hidden) wasHidden = true; };
        document.addEventListener("visibilitychange", onVis, { passive: true });

        await this._baselineRestore(phy);
        const cap = await this._recomputeDerived(g.dt);

        await this._modeSelect(phy, pressCUsed, dampUsed);
        for (let s = 0; s < g.settleTicks; s++) phy.step(g.dt, pressCUsed, dampUsed);

        let arbiter_tick = null;
        let arbiter_edge = "";
        let arbiter_owner = "";
        let handshake_tick = null;
        let handshake_applied = 0;
        let handshake_pending = 0;
        let handshake_applied_tick = "";

        let first114Max_tick = null;
        let first136Max_tick = null;

        let peak114_abs = 0;
        let peak136_abs = 0;
        let cross_peakAbs_89_79 = 0;

        let max1_at_markerTick = "";
        let laneClass = "";
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

          if (tick === item.injectTick136) this._inject(phy, 136, ampD);
          if (tick === item.injectTick114) this._inject(phy, 114, ampB0);

          if (handshake_tick === tick && ampB_nudge > 0) {
            this._inject(phy, 114, ampB_nudge);
            handshake_applied = 1;
            handshake_applied_tick = String(tick);
          }

          phy.step(g.dt, pressCUsed, dampUsed);

          const basin = this._pickBasin(phy);
          const top2 = this._top2Edges(phy, g.includeBackgroundEdges);
          const max1Pair = `${top2.best1.from}->${top2.best1.to}`;

          if (tick === g.markerTickToCheck) {
            max1_at_markerTick = max1Pair;
            laneClass = this._laneClassFromMarker(max1Pair);
          }
          if (!first_marker_tick && g.markerEdges.includes(max1Pair)) first_marker_tick = String(tick);

          const f114_89 = (i114_89 != null) ? this._edgeFlux(phy, i114_89) : 0;
          const f114_79 = (i114_79 != null) ? this._edgeFlux(phy, i114_79) : 0;
          const f136_89 = (i136_89 != null) ? this._edgeFlux(phy, i136_89) : 0;
          const f136_79 = (i136_79 != null) ? this._edgeFlux(phy, i136_79) : 0;
          const f89_79  = this._edgeFlux(phy, i89_79);

          if (g.abortOnNonFinite) {
            const ok = this._isFiniteNums([top2.best1.af, top2.best2.af, f114_89,f114_79,f136_89,f136_79,f89_79]);
            if (!ok) {
              runStatus = "aborted";
              abort_tick = String(tick);
              abort_reason = "non_finite_flux";
              console.warn(`[16aj:${tag}] ABORT runIndex=${runIndex} sp=${item.spacingTicks} rep=${repIndex} tick=${tick}: non-finite sample`);
              break;
            }
          }

          peak114_abs = Math.max(peak114_abs, Math.max(Math.abs(f114_89), Math.abs(f114_79)));
          peak136_abs = Math.max(peak136_abs, Math.max(Math.abs(f136_89), Math.abs(f136_79)));
          cross_peakAbs_89_79 = Math.max(cross_peakAbs_89_79, Math.abs(f89_79));

          if (arbiter_tick == null && busSet.has(max1Pair)) {
            arbiter_tick = tick;
            arbiter_edge = max1Pair;
            arbiter_owner = is136Bus(max1Pair) ? "136" : (is114Bus(max1Pair) ? "114" : "");

            const okOwner = (!sec.nudgeOnlyIf136First) || (arbiter_owner === "136");
            const nextTick = tick + 1;
            const within = (nextTick < g.totalTicks) && ((nextTick - tick) <= g.maxHandshakeDelay);
            if (okOwner && within) {
              handshake_tick = nextTick;
              handshake_pending = 1;
            }
          }

          if (busSet.has(max1Pair)) {
            if (is114Bus(max1Pair) && first114Max_tick == null) first114Max_tick = tick;
            if (is136Bus(max1Pair) && first136Max_tick == null) first136Max_tick = tick;
          }

          traceLines.push(this._csvRow([
            this.version, tag, runId, runIndex, repIndex,
            (cap.capLawHash ?? ""),
            pressCUsed, dampUsed,
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

        const arbiterOwner114 = (arbiter_owner === "114") ? 1 : 0;
        const precedenceStarts114 = (precedence.startsWith("114")) ? 1 : 0;

        if (!laneClass && max1_at_markerTick) laneClass = this._laneClassFromMarker(max1_at_markerTick);

        summaryLines.push(this._csvRow([
          this.version, tag, runId, runIndex, repIndex,
          sec.label,
          pressCBase, pressCUsed, dampUsed,
          g.dt, g.everyMs, g.totalTicks, g.settleTicks,
          (cap.capLawHash ?? ""), (cap.capLawSig ?? ""), (cap.capLawApplied ?? ""), (cap.dtUsed ?? ""),
          g.gain, g.multB, g.multD,
          ampB0, ampD, ratioBD,
          item.injectTick136, item.injectTick114, item.spacingTicks,
          sec.nudgeOnlyIf136First ? 1 : 0,
          (arbiter_tick == null ? "" : arbiter_tick),
          arbiter_edge,
          arbiter_owner,
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
          laneClass,
          first_marker_tick,
          arbiterOwner114,
          precedenceStarts114,
          visibilityStateStart,
          wasHidden,
          runStatus,
          abort_tick,
          abort_reason
        ]));

        if (arbiterOwner114 || precedenceStarts114) {
          console.warn(
            `[16aj:${tag}] 🧲 114-event runIndex=${runIndex} sp=${item.spacingTicks} rep=${repIndex}` +
            ` | inject(136@${item.injectTick136},114@${item.injectTick114})` +
            ` | arb=${arbiter_owner}@${arbiter_tick} hs=${handshake_tick} prec=${precedence} class=${packetClass}`
          );
        } else if ((runIndex + 1) % 25 === 0) {
          console.log(`[16aj:${tag}] progress ${(runIndex + 1)}/${plan.length}`);
        }

        runIndex += 1;
      }

      return { summaryLines, traceLines, runs: runIndex };
    },

    async run(userCfg = {}) {
      this._stop = false;
      this.cfg = { ...this.cfg, ...userCfg };

      const phy = await this._waitForPhysics();
      this._freezeLiveLoop();

      const ui = this._readUiParams();
      const inv = window.SOLRuntime?.getInvariants?.() || {};

      const pressCBase =
        (this.cfg.pressCBase != null) ? this.cfg.pressCBase :
        (inv.pressC ?? ui.pressC ?? 2.0);

      const edgeIndex = this._buildEdgeIndex(phy);

      const startTag = this._iso(new Date());
      console.log(`[16aj] START ${this.version} @ ${startTag} | pressCBase=${pressCBase}`);

      // SECTION A2
      const A2 = await this._runGridSection(phy, edgeIndex, pressCBase, this.cfg.sectionA2);
      if (this._stop) console.warn("[16aj] stopped after A2.");

      // SECTION C1
      const C1 = this._stop ? { summaryLines: [""], traceLines: [""], runs: 0 }
        : await this._runGridSection(phy, edgeIndex, pressCBase, this.cfg.sectionC1);
      if (this._stop) console.warn("[16aj] stopped after C1.");

      // SECTION C2
      const C2 = this._stop ? { summaryLines: [""], traceLines: [""], runs: 0 }
        : await this._runSpacingSection(phy, edgeIndex, pressCBase, this.cfg.sectionC2);

      const endTag = this._iso(new Date());
      const baseName = `${this.version}_${startTag}_${endTag}`;

      this._unfreezeLiveLoop();

      this._download(`${baseName}_A2_gateRefine_MASTER_summary.csv`, A2.summaryLines.join(""));
      this._download(`${baseName}_A2_gateRefine_MASTER_busTrace.csv`, A2.traceLines.join(""));

      this._download(`${baseName}_C1_orderSwap_MASTER_summary.csv`, C1.summaryLines.join(""));
      this._download(`${baseName}_C1_orderSwap_MASTER_busTrace.csv`, C1.traceLines.join(""));

      this._download(`${baseName}_C2_spacingSweep_MASTER_summary.csv`, C2.summaryLines.join(""));
      this._download(`${baseName}_C2_spacingSweep_MASTER_busTrace.csv`, C2.traceLines.join(""));

      console.log(
        `✅ [16aj] DONE @ ${endTag}\n` +
        `- A2 runs: ${A2.runs}\n` +
        `- C1 runs: ${C1.runs}\n` +
        `- C2 runs: ${C2.runs}\n` +
        `Files:\n` +
        `- ${baseName}_A2_gateRefine_MASTER_summary.csv\n` +
        `- ${baseName}_A2_gateRefine_MASTER_busTrace.csv\n` +
        `- ${baseName}_C1_orderSwap_MASTER_summary.csv\n` +
        `- ${baseName}_C1_orderSwap_MASTER_busTrace.csv\n` +
        `- ${baseName}_C2_spacingSweep_MASTER_summary.csv\n` +
        `- ${baseName}_C2_spacingSweep_MASTER_busTrace.csv`
      );

      return { baseName, pressCUsed: pressCBase, runsA2: A2.runs, runsC1: C1.runs, runsC2: C2.runs, stopped: this._stop };
    }
  };

  window.solPhase311_16aj_combo_v1 = X;
  console.log(`✅ solPhase311_16aj_combo_v1 installed (${X.version}). Run: await solPhase311_16aj_combo_v1.run()`);
})();
