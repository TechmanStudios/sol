/* Phase 3.11.16AM — Boundary Microscope (multB in the flip-band)
   Purpose:
     Pin the arbitration threshold in multB ∈ [1.144, 1.200) and test order-dependence near boundary.

   Two sections run back-to-back; downloads 4 CSVs at the end.

   SECTION B1 (114-first near-boundary):
     - Order: 114@t0, 136@t1
     - dampUsed: [12, 20]
     - multBUsed: [1.144, 1.155, 1.165, 1.175, 1.185, 1.195]
     - repsPerCond: 40
     - nudgeOnlyIf136First: false

   SECTION B2 (136-first near-boundary):
     - Order: 136@t0, 114@t1
     - dampUsed: [12, 20]
     - multBUsed: [1.144, 1.155, 1.165, 1.175, 1.185, 1.195]
     - repsPerCond: 40
     - nudgeOnlyIf136First: false

   Outputs:
     - ..._B1_114first_MASTER_summary.csv
     - ..._B1_114first_MASTER_busTrace.csv
     - ..._B2_136first_MASTER_summary.csv
     - ..._B2_136first_MASTER_busTrace.csv

   Run:
     await solPhase311_16am_boundaryMicroscope_v1.run()

   Stop:
     solPhase311_16am_boundaryMicroscope_v1.stop()

   Baseline:
     - Uses SOLBaseline.restore() per run if available; otherwise internal snapshot.
     - UI-neutral (no camera moves).
*/
(() => {
  "use strict";

  const S = {
    version: "sol_phase311_16am_boundaryMicroscope_v1",
    _stop: false,
    stop() { this._stop = true; },

    cfg: {
      // Timing
      dt: 0.12,
      everyMs: 200,
      spinWaitMs: 1.5,
      totalTicks: 41,
      settleTicks: 3,

      // If null: auto from SOLRuntime invariants/UI fallback
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

      // Sweep band
      dampUsedList: [12, 20],
      multBUsedList: [1.144, 1.155, 1.165, 1.175, 1.185, 1.195],
      repsPerCond: 40,
      shuffle: true,

      // Sections
      sectionB1: {
        tag: "B1_114first",
        label: "nearBoundary_114first",
        injectTick114: 0,
        injectTick136: 1
      },
      sectionB2: {
        tag: "B2_136first",
        label: "nearBoundary_136first",
        injectTick114: 1,
        injectTick136: 0
      }
    },

    _sleep(ms) { return new Promise(r => setTimeout(r, ms)); },
    _p2(n) { return String(n).padStart(2, "0"); },
    _p3(n) { return String(n).padStart(3, "0"); },

    _iso(d = new Date()) {
      return `${d.getUTCFullYear()}-${this._p2(d.getUTCMonth() + 1)}-${this._p2(d.getUTCDate())}` +
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
      setTimeout(() => { try { URL.revokeObjectURL(url); } catch (e) {} }, 250);
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
      throw new Error("[16am] timed out waiting for physics.");
    },

    _freezeLiveLoop() {
      const app = this._getApp();
      if (!app?.config) throw new Error("[16am] App not ready.");
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
      if (!n) throw new Error(`[16am] node not found: ${id}`);
      const a = Math.max(0, Number(amt) || 0);
      n.rho += a;
      try {
        if (n.isConstellation && typeof phy.reinforceSemanticStar === "function") {
          phy.reinforceSemanticStar(n, (a / 50.0));
        }
      } catch (e) {}
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
        for (const k in s) { try { n[k] = s[k]; } catch (e) {} }
      }
      const eMap = new Map(snap.edges || []);
      for (let i = 0; i < (phy.edges || []).length; i++) {
        const e = phy.edges[i];
        const s = eMap.get(i);
        if (!s) continue;
        for (const k in s) { try { e[k] = s[k]; } catch (e) {} }
      }
      try { phy.globalBias = snap.globalBias || 0; } catch (e) {}
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
      try { if (typeof phy.computePressure === "function") phy.computePressure(pressC); } catch (e) {}
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
      if (pair === "95->114") return "lane_P_95to114";
      if (pair) return `lane_other_${pair}`;
      return "lane_C_no_marker";
    },

    async _runSection(phy, edgeIndex, pressCBase, sec) {
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

      const plan = [];
      for (const dampUsed of g.dampUsedList) {
        for (const multBUsed of g.multBUsedList) {
          for (let r = 1; r <= g.repsPerCond; r++) plan.push({ dampUsed, multBUsed, rep: r });
        }
      }
      if (g.shuffle) this._shuffle(plan);

      const summaryHeader = [
        "schema","section","runId","runIndex","repIndex",
        "label",
        "pressCBase","pressCUsed","dampUsed",
        "dt","everyMs","totalTicks","settleTicks",
        "capLawHash","capLawSig","capLawApplied","capLawDtUsed",
        "gain","baseB","baseD","multBUsed","multD",
        "ampB0","ampD","ratioBD","ampDiff_BminusD",
        "injectTick114","injectTick136","spacingTicks",
        "nudgeMult","nudgeOnlyIf136First",
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
        "multBUsed","ampB0","ampD",
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
        `[16am:${sec.tag}] plan=${plan.length} | damps=[${g.dampUsedList.join(",")}] | multB=[${g.multBUsedList.join(",")}] reps=${g.repsPerCond}` +
        ` | inject(114@${sec.injectTick114},136@${sec.injectTick136})`
      );

      let runIndex = 0;

      for (const item of plan) {
        if (this._stop) break;

        const repIndex = item.rep;
        const dampUsed = item.dampUsed;
        const multBUsed = item.multBUsed;
        const pressCUsed = pressCBase;

        const ampB0 = baseB * multBUsed;
        const ratioBD = ampB0 / ampD;
        const ampDiff = ampB0 - ampD;
        const ampB_nudge = ampB0 * g.nudgeMult;

        const spacingTicks = sec.injectTick114 - sec.injectTick136;

        const runId =
          `${this._iso(new Date())}_r${String(runIndex).padStart(6, "0")}` +
          `_d${Number(dampUsed).toFixed(3)}_mB${Number(multBUsed).toFixed(3)}_rep${repIndex}`;

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
          if (tick === sec.injectTick114) this._inject(phy, 114, ampB0);
          if (tick === sec.injectTick136) this._inject(phy, 136, ampD);

          // Handshake injection (pre-step)
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
          const f89_79  = (i89_79 != null) ? this._edgeFlux(phy, i89_79) : 0;

          if (g.abortOnNonFinite) {
            const ok = this._isFiniteNums([top2.best1.af, top2.best2.af, f114_89, f114_79, f136_89, f136_79, f89_79]);
            if (!ok) {
              runStatus = "aborted";
              abort_tick = String(tick);
              abort_reason = "non_finite_flux";
              console.warn(`[16am:${sec.tag}] ABORT runIndex=${runIndex} damp=${dampUsed} mB=${multBUsed} rep=${repIndex} tick=${tick}: non-finite sample`);
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

            const okOwner = (!g.nudgeOnlyIf136First) || (arbiter_owner === "136");
            const nextTick = tick + 1;
            const within = (nextTick < g.totalTicks) && ((nextTick - tick) <= g.maxHandshakeDelay);
            if (okOwner && within) {
              handshake_tick = nextTick;
              handshake_pending = 1;
            }
          }

          // Onset ticks for each bus owner
          if (busSet.has(max1Pair)) {
            if (is114Bus(max1Pair) && first114Max_tick == null) first114Max_tick = tick;
            if (is136Bus(max1Pair) && first136Max_tick == null) first136Max_tick = tick;
          }

          traceLines.push(this._csvRow([
            this.version, sec.tag, runId, runIndex, repIndex,
            (cap.capLawHash ?? ""),
            pressCUsed, dampUsed,
            multBUsed, ampB0, ampD,
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
          this.version, sec.tag, runId, runIndex, repIndex,
          sec.label,
          pressCBase, pressCUsed, dampUsed,
          g.dt, g.everyMs, g.totalTicks, g.settleTicks,
          (cap.capLawHash ?? ""), (cap.capLawSig ?? ""), (cap.capLawApplied ?? ""), (cap.dtUsed ?? ""),
          g.gain, baseB, baseD, multBUsed, g.multD,
          ampB0, ampD, ratioBD, ampDiff,
          sec.injectTick114, sec.injectTick136, spacingTicks,
          g.nudgeMult, (g.nudgeOnlyIf136First ? 1 : 0),
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

        if ((runIndex + 1) % 25 === 0) {
          console.log(`[16am:${sec.tag}] progress ${(runIndex + 1)}/${plan.length}`);
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
      console.log(`[16am] START ${this.version} @ ${startTag} | pressCBase=${pressCBase}`);

      const B1 = await this._runSection(phy, edgeIndex, pressCBase, this.cfg.sectionB1);
      if (this._stop) console.warn("[16am] stopped after B1.");

      const B2 = this._stop ? { summaryLines: [""], traceLines: [""], runs: 0 }
        : await this._runSection(phy, edgeIndex, pressCBase, this.cfg.sectionB2);

      const endTag = this._iso(new Date());
      const baseName = `${this.version}_${startTag}_${endTag}`;

      this._unfreezeLiveLoop();

      this._download(`${baseName}_B1_114first_MASTER_summary.csv`, B1.summaryLines.join(""));
      this._download(`${baseName}_B1_114first_MASTER_busTrace.csv`, B1.traceLines.join(""));

      this._download(`${baseName}_B2_136first_MASTER_summary.csv`, B2.summaryLines.join(""));
      this._download(`${baseName}_B2_136first_MASTER_busTrace.csv`, B2.traceLines.join(""));

      console.log(
        `[16am] DONE @ ${endTag}\n` +
        `- B1 runs: ${B1.runs}\n` +
        `- B2 runs: ${B2.runs}\n` +
        `Files:\n` +
        `- ${baseName}_B1_114first_MASTER_summary.csv\n` +
        `- ${baseName}_B1_114first_MASTER_busTrace.csv\n` +
        `- ${baseName}_B2_136first_MASTER_summary.csv\n` +
        `- ${baseName}_B2_136first_MASTER_busTrace.csv`
      );

      return { baseName, pressCUsed: pressCBase, runsB1: B1.runs, runsB2: B2.runs, stopped: this._stop };
    }
  };

  window.solPhase311_16am_boundaryMicroscope_v1 = S;
  console.log(`✅ solPhase311_16am_boundaryMicroscope_v1 installed (${S.version}). Run: await solPhase311_16am_boundaryMicroscope_v1.run()`);
})();
