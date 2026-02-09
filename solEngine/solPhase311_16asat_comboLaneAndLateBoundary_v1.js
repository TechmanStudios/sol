/* Phase 3.11 — Combo: 16AS (lane boundary) + 16AT (late/peak boundary)
   Baseline: assumes SOLBaseline v1.5 is loaded (falls back to internal snapshot if not)

   What it does:
     - Runs TWO sweeps back-to-back under identical conditions:
       16AS: lane transition microscope (0.92..1.00, 60 reps each)
       16AT: late/peak-bus threshold microscope (0.82..0.90, 80 reps each)

   Fixed:
     - dampUsed = 20
     - B2 order: 136@t0, 114@t1
     - Arbitration measured by BUS FLUX (not “bus edge is global max1”)
     - Also measures the dominant global lane by counting max1 edge occurrences per run

   Outputs (downloaded after BOTH sweeps finish):
     - ..._AS_laneBoundary_MASTER_summary.csv
     - ..._AS_laneBoundary_MASTER_busTrace.csv
     - ..._AT_lateBoundary_MASTER_summary.csv
     - ..._AT_lateBoundary_MASTER_busTrace.csv

   Run:
     await solPhase311_16asat_comboLaneAndLateBoundary_v1.run()

   Stop:
     solPhase311_16asat_comboLaneAndLateBoundary_v1.stop()
*/
(() => {
  "use strict";

  const X = {
    version: "sol_phase311_16asat_comboLaneAndLateBoundary_v1",
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

      // Handshake (kept consistent w/ 16AR)
      nudgeMult: 0.20,
      handshakeTick: 2,

      // Trace filtering
      includeBackgroundEdges: false,

      // Safety
      abortOnNonFinite: true,

      // Fixed damp + order (B2)
      dampUsed: 20,
      injectTick136: 0,
      injectTick114: 1,

      // Marker
      markerTick: 8,

      // Sweeps
      sweeps: [
        {
          tag: "AS_laneBoundary",
          label: "B2_d20_laneBoundaryMicroscope",
          multBUsedList: [0.92, 0.94, 0.96, 0.98, 1.00],
          repsPerCond: 60,
          shuffle: true
        },
        {
          tag: "AT_lateBoundary",
          label: "B2_d20_latePeakBoundaryMicroscope",
          multBUsedList: [0.82, 0.84, 0.86, 0.88, 0.90],
          repsPerCond: 80,
          shuffle: true
        }
      ]
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
      setTimeout(() => { try { URL.revokeObjectURL(url); } catch (e) {} }, 250);
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
      throw new Error("[16asat] timed out waiting for physics.");
    },

    _freezeLiveLoop() {
      const app = this._getApp();
      if (!app?.config) throw new Error("[16asat] App not ready.");
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
      if (!n) throw new Error(`[16asat] node not found: ${id}`);
      const a = Math.max(0, Number(amt) || 0);
      n.rho += a;

      // Keep reinforcement ON (baseline v1.5 should restore relevant state)
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
          b_q: n.b_q, b_charge: n.b_charge, b_state: n.b_state,
          x: n.x, y: n.y, vx: n.vx, vy: n.vy, fx: n.fx, fy: n.fy
        }]);
      }
      const edges = [];
      for (let i = 0; i < (phy.edges || []).length; i++) edges.push([i, { flux: phy.edges[i]?.flux }]);
      const t = (typeof phy._t === "number" && Number.isFinite(phy._t)) ? phy._t : 0;
      return { nodes, edges, t };
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
      try { phy._t = snap.t || 0; } catch (e) {}
    },

    async _baselineRestore(phy) {
      if (window.SOLBaseline?.restore) {
        await window.SOLBaseline.restore();
        return "SOLBaseline.restore";
      }
      if (!this._snap) { this._snap = this._snapshot(phy); return "internal_snapshot_created"; }
      this._restore(phy, this._snap);
      return "internal_snapshot_restored";
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

    _argmaxCount(mapObj) {
      let bestK = "";
      let bestV = -1;
      for (const [k, v] of mapObj.entries()) {
        if (v > bestV) { bestV = v; bestK = k; }
      }
      return { key: bestK, count: bestV };
    },

    async _runSweep(phy, edgeIndex, pressCUsed, sweep, globalRunOffset) {
      const g = this.cfg;

      // Indices for bus edges
      const i114_89 = edgeIndex.get("114->89");
      const i114_79 = edgeIndex.get("114->79");
      const i136_89 = edgeIndex.get("136->89");
      const i136_79 = edgeIndex.get("136->79");

      const baseB = g.baseAmpB * g.gain; // 88
      const baseD = g.baseAmpD * g.gain; // 126.5
      const ampD  = baseD * g.multD;

      const plan = [];
      for (const multBUsed of sweep.multBUsedList) {
        for (let r = 1; r <= sweep.repsPerCond; r++) plan.push({ multBUsed, rep: r });
      }
      if (sweep.shuffle) this._shuffle(plan);

      const summaryHeader = [
        "schema","sweepTag","runId","globalRunIndex","runIndex","repIndex","label",
        "baselineMode",
        "pressCUsed","dampUsed",
        "capLawHash",
        "gain","baseB","baseD","multBUsed","multD",
        "ampB0","ampD","ratioBD","ampDiff_BminusD",
        "injectTick136","injectTick114",
        "nudgeMult","handshakeTick",
        "peakAbs114_bus","peakAbs136_bus","ratioPeak_114over136","winner_peakBus","peakTick114","peakTick136",
        "t8_abs114_bus","t8_abs136_bus","winner_t8",
        "laneEdge","laneEdge_count",
        "runStatus","abort_tick","abort_reason"
      ];

      const traceHeader = [
        "schema","sweepTag","runId","globalRunIndex","runIndex","repIndex","capLawHash",
        "pressCUsed","dampUsed","multBUsed","ampB0","ampD",
        "tick","tMs","lateByMs",
        "max1_from","max1_to","max1_absFlux",
        "max2_from","max2_to","max2_absFlux",
        "flux_114_89","flux_114_79","flux_136_89","flux_136_79",
        "abs114_bus","abs136_bus",
        "handshake_applied_tick"
      ];

      const summaryLines = [this._csvRow(summaryHeader)];
      const traceLines = [this._csvRow(traceHeader)];

      console.log(`[16asat:${sweep.tag}] START runs=${plan.length} repsPerCond=${sweep.repsPerCond}`);

      let runIndex = 0;

      for (const item of plan) {
        if (this._stop) break;

        const repIndex = item.rep;
        const multBUsed = item.multBUsed;

        const ampB0 = baseB * multBUsed;
        const ratioBD = ampB0 / ampD;
        const ampDiff = ampB0 - ampD;
        const ampB_nudge = ampB0 * g.nudgeMult;

        const globalRunIndex = globalRunOffset + runIndex;
        const runId = `${this._iso(new Date())}_${sweep.tag}_g${String(globalRunIndex).padStart(6,"0")}_r${String(runIndex).padStart(6,"0")}_mB${multBUsed.toFixed(2)}_rep${repIndex}`;

        const baselineMode = await this._baselineRestore(phy);
        const cap = await this._recomputeDerived(g.dt);

        await this._modeSelect(phy, pressCUsed, g.dampUsed);
        for (let s = 0; s < g.settleTicks; s++) phy.step(g.dt, pressCUsed, g.dampUsed);

        let handshake_applied_tick = "";

        let peakAbs114 = 0, peakAbs136 = 0;
        let peakTick114 = "", peakTick136 = "";
        let t8_abs114 = "", t8_abs136 = "";

        const laneCounts = new Map();

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

          // Injections (B2)
          if (tick === g.injectTick136) this._inject(phy, 136, ampD);
          if (tick === g.injectTick114) this._inject(phy, 114, ampB0);

          // Handshake nudge at fixed tick (consistent with 16AR)
          if (tick === g.handshakeTick && ampB_nudge > 0) {
            this._inject(phy, 114, ampB_nudge);
            handshake_applied_tick = String(tick);
          }

          phy.step(g.dt, pressCUsed, g.dampUsed);

          const top2 = this._top2Edges(phy, g.includeBackgroundEdges);
          const max1Pair = `${top2.best1.from}->${top2.best1.to}`;
          laneCounts.set(max1Pair, (laneCounts.get(max1Pair) || 0) + 1);

          const f114_89 = this._edgeFlux(phy, i114_89);
          const f114_79 = this._edgeFlux(phy, i114_79);
          const f136_89 = this._edgeFlux(phy, i136_89);
          const f136_79 = this._edgeFlux(phy, i136_79);

          const abs114 = Math.max(Math.abs(f114_89), Math.abs(f114_79));
          const abs136 = Math.max(Math.abs(f136_89), Math.abs(f136_79));

          if (g.abortOnNonFinite) {
            const ok = this._isFiniteNums([
              top2.best1.af, top2.best2.af,
              f114_89, f114_79, f136_89, f136_79,
              abs114, abs136
            ]);
            if (!ok) {
              runStatus = "aborted";
              abort_tick = String(tick);
              abort_reason = "non_finite_flux";
              break;
            }
          }

          if (abs114 > peakAbs114) { peakAbs114 = abs114; peakTick114 = String(tick); }
          if (abs136 > peakAbs136) { peakAbs136 = abs136; peakTick136 = String(tick); }

          if (tick === g.markerTick) { t8_abs114 = abs114; t8_abs136 = abs136; }

          traceLines.push(this._csvRow([
            this.version, sweep.tag, runId, globalRunIndex, runIndex, repIndex, (cap.capLawHash ?? ""),
            pressCUsed, g.dampUsed, multBUsed, ampB0, ampD,
            tick, (now - startMs), lateByMs,
            top2.best1.from, top2.best1.to, top2.best1.af,
            top2.best2.from, top2.best2.to, top2.best2.af,
            f114_89, f114_79, f136_89, f136_79,
            abs114, abs136,
            handshake_applied_tick
          ]));
        }

        const winner_peakBus =
          (peakAbs114 > peakAbs136) ? "114" :
          (peakAbs136 > peakAbs114) ? "136" : "tie";

        const winner_t8 =
          (t8_abs114 === "" || t8_abs136 === "") ? "" :
          (t8_abs114 > t8_abs136) ? "114" :
          (t8_abs136 > t8_abs114) ? "136" : "tie";

        const ratioPeak = (peakAbs136 > 0) ? (peakAbs114 / peakAbs136) : "";

        const lane = this._argmaxCount(laneCounts);

        summaryLines.push(this._csvRow([
          this.version, sweep.tag, runId, globalRunIndex, runIndex, repIndex, sweep.label,
          baselineMode,
          pressCUsed, g.dampUsed,
          (cap.capLawHash ?? ""),
          g.gain, baseB, baseD, multBUsed, g.multD,
          ampB0, ampD, ratioBD, ampDiff,
          g.injectTick136, g.injectTick114,
          g.nudgeMult, g.handshakeTick,
          peakAbs114, peakAbs136, ratioPeak, winner_peakBus, peakTick114, peakTick136,
          t8_abs114, t8_abs136, winner_t8,
          lane.key, lane.count,
          runStatus, abort_tick, abort_reason
        ]));

        if ((runIndex + 1) % 25 === 0) console.log(`[16asat:${sweep.tag}] progress ${(runIndex + 1)}/${plan.length}`);
        runIndex += 1;
      }

      console.log(`[16asat:${sweep.tag}] DONE runs=${runIndex}`);
      return { summaryLines, traceLines, runs: runIndex, planned: plan.length };
    },

    async run(userCfg = {}) {
      this._stop = false;
      this.cfg = { ...this.cfg, ...userCfg };

      const g = this.cfg;
      const phy = await this._waitForPhysics();
      this._freezeLiveLoop();

      const ui = this._readUiParams();
      const inv = window.SOLRuntime?.getInvariants?.() || {};
      const pressCUsed = (g.pressCBase != null) ? g.pressCBase : (inv.pressC ?? ui.pressC ?? 2.0);

      const edgeIndex = this._buildEdgeIndex(phy);

      const startTag = this._iso(new Date());
      console.log(`[16asat] START ${this.version} @ ${startTag} | pressC=${pressCUsed} | damp=${g.dampUsed}`);

      const outs = [];
      let globalRunOffset = 0;

      for (const sweep of g.sweeps) {
        if (this._stop) break;

        // One extra restore at the start of each sweep (belt + suspenders)
        await this._baselineRestore(phy);

        const res = await this._runSweep(phy, edgeIndex, pressCUsed, sweep, globalRunOffset);
        outs.push({ sweep, ...res });
        globalRunOffset += res.runs;

        if (this._stop) break;
      }

      const endTag = this._iso(new Date());
      const baseName = `${this.version}_${startTag}_${endTag}`;

      this._unfreezeLiveLoop();

      for (const o of outs) {
        this._download(`${baseName}_${o.sweep.tag}_MASTER_summary.csv`, o.summaryLines.join(""));
        this._download(`${baseName}_${o.sweep.tag}_MASTER_busTrace.csv`, o.traceLines.join(""));
      }

      console.log(
        `[16asat] DONE @ ${endTag}\n` +
        outs.map(o => `- ${baseName}_${o.sweep.tag}_MASTER_summary.csv\n- ${baseName}_${o.sweep.tag}_MASTER_busTrace.csv`).join("\n")
      );

      return {
        baseName,
        pressCUsed,
        dampUsed: g.dampUsed,
        stopped: this._stop,
        sweeps: outs.map(o => ({ tag: o.sweep.tag, runs: o.runs, planned: o.planned }))
      };
    }
  };

  window.solPhase311_16asat_comboLaneAndLateBoundary_v1 = X;
  console.log(`✅ solPhase311_16asat_comboLaneAndLateBoundary_v1 installed (${X.version}). Run: await solPhase311_16asat_comboLaneAndLateBoundary_v1.run()`);
})();
