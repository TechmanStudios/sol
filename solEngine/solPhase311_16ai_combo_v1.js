/* Phase 3.11 — Combo Script (sequential sections, outputs at end)
   Section A: 16AI-A — "139-gate map" damp sweep (transition scan)
   Section B: 16AI-B — "114-steals-the-bus" hunt (damp=1, many reps, allow handshake even if 114 wins)

   Outputs (4 files total, downloaded after BOTH sections finish):
     - ..._A_gateMap_MASTER_summary.csv
     - ..._A_gateMap_MASTER_busTrace.csv
     - ..._B_busSteal_MASTER_summary.csv
     - ..._B_busSteal_MASTER_busTrace.csv

   Run:
     await solPhase311_16ai_combo_v1.run()

   Stop:
     solPhase311_16ai_combo_v1.stop()

   Notes:
     - Restores baseline at start of EVERY run via SOLBaseline.restore() when available.
     - UI-neutral: no camera moves.
*/
(() => {
  "use strict";

  const R = {
    version: "sol_phase311_16ai_comboGateMapAndBusSteal_v1",
    _stop: false,
    stop() { this._stop = true; },

    cfg: {
      // Shared timing
      dt: 0.12,
      everyMs: 200,
      spinWaitMs: 1.5,

      // Shared physics prep
      settleTicks: 3,

      // If null: auto from SOLRuntime invariants/UI fallback
      pressCBase: null,

      // Priming / mode-select (consistent with 16Y/16Z/16AH)
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
      offset: +1,          // 136 tick0, 114 tick1

      // Adaptive handshake defaults (section overrides allowed)
      nudgeMult: 0.20,
      nudgeOnlyIf136First: true,
      maxHandshakeDelay: 10,
      followWindowTicks: 6,

      // Bus-trace settings
      includeBackgroundEdges: false,

      // Marker / lane detection (tick8 is a known "marker moment" at high damp)
      markerTickToCheck: 8,
      markerEdges: ["136->139", "136->10"],

      // Safety
      abortOnNonFinite: true,

      // -------- Section A (Gate Map) --------
      sectionA: {
        tag: "A_gateMap",
        totalTicks: 41,
        dampUsedList: [10, 12, 15, 18, 20, 22],
        repsPerDamp: 50,
        shuffle: true,
        nudgeOnlyIf136First: true
      },

      // -------- Section B (Bus Steal Hunt) --------
      sectionB: {
        tag: "B_busSteal",
        totalTicks: 41,
        dampUsedList: [1.0],
        repsPerDamp: 500,
        shuffle: true,
        // allow handshake regardless of arbiter owner (important for inversion runs)
        nudgeOnlyIf136First: false
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
      throw new Error("[16ai] timed out waiting for physics.");
    },

    _freezeLiveLoop() {
      const app = this._getApp();
      if (!app?.config) throw new Error("[16ai] App not ready.");
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
      if (!n) throw new Error(`[16ai] node not found: ${id}`);
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

    async _modeSelect(phy, pressC, damp, cfg) {
      let idx = 0;
      for (let b = 0; b < Math.max(0, cfg.dreamBlocks - 1); b++) {
        const injId = cfg.injectorIds[idx % cfg.injectorIds.length];
        idx++;
        this._inject(phy, injId, cfg.injectAmount);
        for (let s = 0; s < cfg.dreamBlockSteps; s++) phy.step(cfg.dt, pressC, damp);
      }
      this._inject(phy, cfg.wantId, cfg.injectAmount * (cfg.finalWriteMult || 1));
      try { if (typeof phy.computePressure === "function") phy.computePressure(pressC); } catch(e) {}
    },

    _shuffle(arr) {
      for (let i = arr.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [arr[i], arr[j]] = [arr[j], arr[i]];
      }
      return arr;
    },

    _isFiniteEdgeSample(top2, arr) {
      // arr: additional numeric flux samples
      const vals = [top2.best1.af, top2.best2.af, ...arr];
      for (const v of vals) if (typeof v !== "number" || !Number.isFinite(v)) return false;
      return true;
    },

    _laneClassFromMarker(markerAtCheckTick) {
      if (markerAtCheckTick === "136->139") return "lane_A_136to139";
      if (markerAtCheckTick === "136->10") return "lane_B_136to10";
      if (markerAtCheckTick) return `lane_other_${markerAtCheckTick}`;
      return "lane_C_no_marker";
    },

    async _runSection(phy, edgeIndex, pressCBase, sectionCfg) {
      const g = this.cfg;
      const tag = sectionCfg.tag;

      // Offset -> injection ticks
      let injectTick114 = 0, injectTick136 = 0;
      if (g.offset === -1) { injectTick114 = 0; injectTick136 = 1; }
      else if (g.offset === +1) { injectTick114 = 1; injectTick136 = 0; }
      else { injectTick114 = 0; injectTick136 = 0; }

      // Bus edges
      const i114_89 = edgeIndex.get("114->89");
      const i114_79 = edgeIndex.get("114->79");
      const i136_89 = edgeIndex.get("136->89");
      const i136_79 = edgeIndex.get("136->79");
      const i89_79  = edgeIndex.get("89->79"); // tertiary stitch

      const busSet = new Set(["114->89","114->79","136->89","136->79"]);
      const is114Bus = (pair) => pair === "114->89" || pair === "114->79";
      const is136Bus = (pair) => pair === "136->89" || pair === "136->79";

      const baseB = g.baseAmpB * g.gain;
      const baseD = g.baseAmpD * g.gain;
      const ampB0 = baseB * g.multB;
      const ampD  = baseD * g.multD;
      const ratioBD = ampB0 / ampD;
      const ampB_nudge = ampB0 * g.nudgeMult;

      const plan = [];
      for (const dampUsed of sectionCfg.dampUsedList) {
        for (let r = 1; r <= sectionCfg.repsPerDamp; r++) plan.push({ dampUsed, rep: r });
      }
      if (sectionCfg.shuffle) this._shuffle(plan);

      const summaryHeader = [
        "schema","section","runId","runIndex","repIndex",
        "pressCBase","pressCUsed","dampUsed",
        "dt","everyMs","totalTicks","settleTicks",
        "capLawHash","capLawSig","capLawApplied","capLawDtUsed",
        "gain","multB","multD","offset",
        "ampB0","ampD","ratioBD",
        "injectTick114","injectTick136",
        "arbiter_tick","arbiter_edge","arbiter_owner",
        "handshake_tick","handshake_applied",
        "first114Max_tick","first136Max_tick","precedence",
        "deltaTicks","fastFollow","packetClass",
        "peak114_abs","peak136_abs",
        "cross_peakAbs_89_79",
        // Gate-map / lane fields (filled for both sections so schema stays stable)
        "max1_at_markerTick","laneClass","first_marker_tick",
        // Bus-steal flags (useful everywhere)
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
        `[16ai:${tag}] plan=${plan.length} runs | damp=[${sectionCfg.dampUsedList.join(", ")}] repsPerDamp=${sectionCfg.repsPerDamp}` +
        ` | ticks=${sectionCfg.totalTicks} everyMs=${g.everyMs} | nudgeOnlyIf136First=${sectionCfg.nudgeOnlyIf136First}`
      );

      let runIndex = 0;

      for (const item of plan) {
        if (this._stop) break;

        const repIndex = item.rep;
        const dampUsed = item.dampUsed;
        const pressCUsed = pressCBase;

        const runId =
          `${this._iso(new Date())}_r${String(runIndex).padStart(5,"0")}` +
          `_d${Number(dampUsed).toFixed(3)}_rep${repIndex}`;

        const visibilityStateStart = document.visibilityState || "";
        let wasHidden = !!document.hidden;
        const onVis = () => { if (document.hidden) wasHidden = true; };
        document.addEventListener("visibilitychange", onVis, { passive: true });

        await this._baselineRestore(phy);
        const cap = await this._recomputeDerived(g.dt);

        await this._modeSelect(phy, pressCUsed, dampUsed, g);
        for (let s = 0; s < g.settleTicks; s++) phy.step(g.dt, pressCUsed, dampUsed);

        // Arbiter/handshake state
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

        // Lane / marker tracking
        let max1_at_markerTick = "";
        let first_marker_tick = "";
        let laneClass = "";

        let runStatus = "ok";
        let abort_tick = "";
        let abort_reason = "";

        const startMs = performance.now();

        for (let tick = 0; tick < sectionCfg.totalTicks; tick++) {
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

          // Stage 0 injections (pre-step)
          if (tick === injectTick136) this._inject(phy, 136, ampD);
          if (tick === injectTick114) this._inject(phy, 114, ampB0);

          // Apply adaptive handshake if scheduled for this tick
          if (handshake_tick === tick && ampB_nudge > 0) {
            this._inject(phy, 114, ampB_nudge);
            handshake_applied = 1;
            handshake_applied_tick = String(tick);
          }

          phy.step(g.dt, pressCUsed, dampUsed);

          const basin = this._pickBasin(phy);
          const top2 = this._top2Edges(phy, g.includeBackgroundEdges);

          const max1Pair = `${top2.best1.from}->${top2.best1.to}`;

          // Marker tick capture
          if (tick === g.markerTickToCheck) {
            max1_at_markerTick = max1Pair;
            laneClass = this._laneClassFromMarker(max1Pair);
          }

          // First marker occurrence (any time)
          if (!first_marker_tick && g.markerEdges.includes(max1Pair)) {
            first_marker_tick = String(tick);
          }

          const f114_89 = (i114_89 != null) ? this._edgeFlux(phy, i114_89) : 0;
          const f114_79 = (i114_79 != null) ? this._edgeFlux(phy, i114_79) : 0;
          const f136_89 = (i136_89 != null) ? this._edgeFlux(phy, i136_89) : 0;
          const f136_79 = (i136_79 != null) ? this._edgeFlux(phy, i136_79) : 0;
          const f89_79  = this._edgeFlux(phy, i89_79);

          // Non-finite guard
          if (g.abortOnNonFinite && !this._isFiniteEdgeSample(top2, [f114_89,f114_79,f136_89,f136_79,f89_79])) {
            runStatus = "aborted";
            abort_tick = String(tick);
            abort_reason = "non_finite_flux";
            console.warn(`[16ai:${tag}] ABORT runIndex=${runIndex} damp=${dampUsed} rep=${repIndex} at tick=${tick}: non-finite flux sample.`);
            break;
          }

          peak114_abs = Math.max(peak114_abs, Math.max(Math.abs(f114_89), Math.abs(f114_79)));
          peak136_abs = Math.max(peak136_abs, Math.max(Math.abs(f136_89), Math.abs(f136_79)));
          cross_peakAbs_89_79 = Math.max(cross_peakAbs_89_79, Math.abs(f89_79));

          // Detect arbiter tick (first time max1 is a bus edge)
          if (arbiter_tick == null && busSet.has(max1Pair)) {
            arbiter_tick = tick;
            arbiter_edge = max1Pair;
            arbiter_owner = is136Bus(max1Pair) ? "136" : (is114Bus(max1Pair) ? "114" : "");

            // Schedule handshake on next tick (section-configurable owner gating)
            const okOwner = (!sectionCfg.nudgeOnlyIf136First) || (arbiter_owner === "136");
            const nextTick = tick + 1;
            const within = (nextTick < sectionCfg.totalTicks) && ((nextTick - tick) <= g.maxHandshakeDelay);
            if (okOwner && within) {
              handshake_tick = nextTick;
              handshake_pending = 1;
            }
          }

          // Onset ticks for each bus owner, based on max1 being a bus edge
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

        // precedence + packet class
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

        // If marker tick wasn't reached (abort), keep laneClass empty
        if (!laneClass && max1_at_markerTick) laneClass = this._laneClassFromMarker(max1_at_markerTick);

        summaryLines.push(this._csvRow([
          this.version, tag, runId, runIndex, repIndex,
          pressCBase, pressCUsed, dampUsed,
          g.dt, g.everyMs, sectionCfg.totalTicks, g.settleTicks,
          (cap.capLawHash ?? ""), (cap.capLawSig ?? ""), (cap.capLawApplied ?? ""), (cap.dtUsed ?? ""),
          g.gain, g.multB, g.multD, g.offset,
          ampB0, ampD, ratioBD,
          injectTick114, injectTick136,
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
          peak114_abs, peak136_abs,
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

        // Progress log (highlight bus-steal events)
        if (arbiterOwner114 || precedenceStarts114) {
          console.warn(
            `[16ai:${tag}] 🧲 114-event runIndex=${runIndex} damp=${Number(dampUsed).toFixed(2)} rep=${repIndex}` +
            ` | arb=${arbiter_owner}@${arbiter_tick} hs=${handshake_tick} | prec=${precedence} class=${packetClass}` +
            ` | marker@${this.cfg.markerTickToCheck}=${max1_at_markerTick}`
          );
        } else if ((runIndex + 1) % 25 === 0) {
          console.log(`[16ai:${tag}] progress ${(runIndex + 1)}/${plan.length} (latest damp=${Number(dampUsed).toFixed(2)} rep=${repIndex})`);
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
      console.log(`[16ai] START ${this.version} @ ${startTag} | pressCBase=${pressCBase}`);

      // Run Section A then Section B
      const A = await this._runSection(phy, edgeIndex, pressCBase, this.cfg.sectionA);
      if (this._stop) console.warn("[16ai] stopped after section A.");
      const B = this._stop ? { summaryLines: [""], traceLines: [""], runs: 0 } :
        await this._runSection(phy, edgeIndex, pressCBase, this.cfg.sectionB);

      const endTag = this._iso(new Date());
      const baseName = `${this.version}_${startTag}_${endTag}`;

      this._unfreezeLiveLoop();

      // Download after BOTH sections complete
      this._download(`${baseName}_A_gateMap_MASTER_summary.csv`, A.summaryLines.join(""));
      this._download(`${baseName}_A_gateMap_MASTER_busTrace.csv`, A.traceLines.join(""));
      this._download(`${baseName}_B_busSteal_MASTER_summary.csv`, B.summaryLines.join(""));
      this._download(`${baseName}_B_busSteal_MASTER_busTrace.csv`, B.traceLines.join(""));

      console.log(
        `✅ [16ai] DONE @ ${endTag}\n` +
        `- A runs: ${A.runs} | ${baseName}_A_gateMap_MASTER_summary.csv / _busTrace.csv\n` +
        `- B runs: ${B.runs} | ${baseName}_B_busSteal_MASTER_summary.csv / _busTrace.csv`
      );

      return { baseName, pressCUsed: pressCBase, runsA: A.runs, runsB: B.runs, stopped: this._stop };
    }
  };

  window.solPhase311_16ai_combo_v1 = R;
  console.log(`✅ solPhase311_16ai_combo_v1 installed (${R.version}). Run: await solPhase311_16ai_combo_v1.run()`);
})();
