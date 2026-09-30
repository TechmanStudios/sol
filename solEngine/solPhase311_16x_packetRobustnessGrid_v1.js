/* Phase 3.11.16x — Packet Robustness Grid (env sensitivity spec)
   Locks the deterministic packet primitive discovered in 16w, then perturbs environment:

   Fixed protocol (WINNER):
     - multB = 1.144
     - baseAmpB=4.0, baseAmpD=5.75, gain=22
     - offset = +1   (136@tick0, 114@tick1)
     - nudgeTick = 14
     - nudgeMult = 0.20  (ampB_nudge = ampB0 * 0.20)
     - expected: 136_first @ tick13, 114 @ tick15 (Δ=2)

   Environment sweep:
     - dampUsed ∈ {base-1, base, base+1}
     - pressCUsed ∈ {base*0.8, base, base*1.2}
     (base values pulled from SOLRuntime invariants, else UI sliders, else defaults)

   Reps:
     repsPerCell = 16  => 9 cells * 16 = 144 runs (same scale as 16w)

   Run:
     await solPhase311_16x_packetRobustnessGrid_v1.run()

   Stop:
     solPhase311_16x_packetRobustnessGrid_v1.stop()

   Outputs:
     ...MASTER_summary.csv
     ...MASTER_busTrace.csv

   UI-neutral: no camera moves.
*/
(() => {
  "use strict";

  const T = {
    version: "sol_phase311_16x_packetRobustnessGrid_v1",
    _stop: false,
    stop() { this._stop = true; },

    cfg: {
      dt: 0.12,
      everyMs: 200,
      totalTicks: 61,
      settleTicks: 3,
      spinWaitMs: 1.5,

      // Base env (null => read from invariants/UI/fallback)
      pressCBase: null,
      dampBase: null,

      // Env sweep multipliers/offsets
      pressCMults: [0.8, 1.0, 1.2],
      dampOffsets: [-1, 0, +1],

      // Priming
      wantId: 82,
      injectorIds: [90, 82],
      dreamBlocks: 15,
      dreamBlockSteps: 2,
      injectAmount: 120,
      finalWriteMult: 1,

      // Protocol (locked)
      baseAmpB: 4.0,     // 114 port
      baseAmpD: 5.75,    // 136 port
      gain: 22,
      multB: 1.144,
      multD: 1.0,
      offset: +1,        // 136 tick0, 114 tick1

      nudgeTick: 14,
      nudgeMult: 0.20,

      repsPerCell: 16,

      includeBackgroundEdges: false,
      shuffle: true,

      followWindowTicks: 6
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
      throw new Error("[16x] timed out waiting for physics.");
    },

    _freezeLiveLoop() {
      const app = this._getApp();
      if (!app?.config) throw new Error("[16x] App not ready.");
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

    _nodeById(phy, id) {
      const want = String(id);
      for (const n of (phy.nodes || [])) if (n?.id != null && String(n.id) === want) return n;
      return null;
    },

    _inject(phy, id, amt) {
      const n = this._nodeById(phy, id);
      if (!n) throw new Error(`[16x] node not found: ${id}`);
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

    _pickBasin(phy) {
      const n82 = this._nodeById(phy, 82);
      const n90 = this._nodeById(phy, 90);
      const r82 = Number.isFinite(n82?.rho) ? n82.rho : 0;
      const r90 = Number.isFinite(n90?.rho) ? n90.rho : 0;
      return (r90 > r82) ? 90 : 82;
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

      const ui = this._readUiParams();
      const inv = window.SOLRuntime?.getInvariants?.() || {};

      const pressBase =
        (this.cfg.pressCBase != null) ? this.cfg.pressCBase :
        (inv.pressC ?? ui.pressC ?? 2.0);

      const dampBase =
        (this.cfg.dampBase != null) ? this.cfg.dampBase :
        (inv.damp ?? ui.damp ?? 5.0);

      // Build env grids
      const pressCList = this.cfg.pressCMults.map(m => pressBase * m);
      const dampList = this.cfg.dampOffsets.map(o => dampBase + o);

      // Build edge indices
      const edgeIndex = this._buildEdgeIndex(phy);

      const i114_89 = edgeIndex.get("114->89");
      const i114_79 = edgeIndex.get("114->79");
      const i136_89 = edgeIndex.get("136->89");
      const i136_79 = edgeIndex.get("136->79");

      const i89_79 = edgeIndex.get("89->79"); // the “tertiary stitch” we saw earlier

      const busSet = new Set(["114->89","114->79","136->89","136->79"]);
      const is114Bus = (pair) => pair === "114->89" || pair === "114->79";
      const is136Bus = (pair) => pair === "136->89" || pair === "136->79";

      // offset -> injection ticks
      let injectTick114 = 0, injectTick136 = 0;
      if (this.cfg.offset === -1) { injectTick114 = 0; injectTick136 = 1; }
      else if (this.cfg.offset === +1) { injectTick114 = 1; injectTick136 = 0; }
      else { injectTick114 = 0; injectTick136 = 0; }

      // Protocol amplitudes
      const baseB = this.cfg.baseAmpB * this.cfg.gain;
      const baseD = this.cfg.baseAmpD * this.cfg.gain;

      const ampB0 = baseB * this.cfg.multB;
      const ampD  = baseD * this.cfg.multD;
      const ratioBD = ampB0 / ampD;

      const ampB_nudge = ampB0 * this.cfg.nudgeMult;

      // Build plan
      const plan = [];
      for (const pressCUsed of pressCList) {
        for (const dampUsed of dampList) {
          for (let r = 1; r <= this.cfg.repsPerCell; r++) {
            plan.push({ pressCUsed, dampUsed, rep: r });
          }
        }
      }
      if (this.cfg.shuffle) this._shuffle(plan);

      const startTag = this._iso(new Date());

      const summaryHeader = [
        "schema","runId","runIndex","repIndex",
        "pressCBase","dampBase","pressCUsed","dampUsed",
        "dt","everyMs","totalTicks","settleTicks",
        "capLawHash","capLawSig","capLawApplied","capLawDtUsed",
        "gain","multB","multD","offset",
        "ampB0","ampD","ratioBD",
        "nudgeTick","nudgeMult","ampB_nudge",
        "injectTick114","injectTick136",
        "firstBusMax_tick","firstBusMax_edge",
        "first114Max_tick","first136Max_tick","precedence",
        "deltaTicks","fastFollow","packetClass",
        "peak114_abs","peak136_abs",
        "cross_peakAbs_89_79",
        "visibilityStateStart","wasHidden"
      ];

      const traceHeader = [
        "schema","runId","runIndex","repIndex",
        "capLawHash",
        "pressCUsed","dampUsed",
        "tick","tMs","lateByMs","basin",
        "max1_from","max1_to","max1_absFlux",
        "max2_from","max2_to","max2_absFlux",
        "flux_114_89","flux_114_79","flux_136_89","flux_136_79",
        "flux_89_79"
      ];

      const summaryLines = [this._csvRow(summaryHeader)];
      const traceLines = [this._csvRow(traceHeader)];

      console.log(
        `[16x] plan=${plan.length} | base pressC=${pressBase} base damp=${dampBase} | pressCList=${pressCList.map(x=>x.toFixed(3)).join("/")}` +
        ` | dampList=${dampList.map(x=>x.toFixed(3)).join("/")}` +
        ` | protocol: multB=${this.cfg.multB} ratioBD=${ratioBD.toFixed(6)} offset=${this.cfg.offset} nudge@${this.cfg.nudgeTick} nudgeMult=${this.cfg.nudgeMult}`
      );

      let runIndex = 0;

      for (const item of plan) {
        if (this._stop) break;

        const repIndex = item.rep;
        const pressCUsed = item.pressCUsed;
        const dampUsed = item.dampUsed;

        const runId =
          `${this._iso(new Date())}_r${String(runIndex).padStart(5,"0")}` +
          `_p${pressCUsed.toFixed(3)}_d${dampUsed.toFixed(3)}_rep${repIndex}`;

        const visibilityStateStart = document.visibilityState || "";
        let wasHidden = !!document.hidden;
        const onVis = () => { if (document.hidden) wasHidden = true; };
        document.addEventListener("visibilitychange", onVis, { passive: true });

        await this._baselineRestore(phy);
        const cap = await this._recomputeDerived(this.cfg.dt);

        await this._modeSelect(phy, pressCUsed, dampUsed);
        for (let s = 0; s < this.cfg.settleTicks; s++) phy.step(this.cfg.dt, pressCUsed, dampUsed);

        let firstBusMax_tick = null, firstBusMax_edge = "";
        let first114Max_tick = null;
        let first136Max_tick = null;

        let peak114_abs = 0;
        let peak136_abs = 0;
        let cross_peakAbs_89_79 = 0;

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

          // Inject before stepping
          if (tick === injectTick136) this._inject(phy, 136, ampD);
          if (tick === injectTick114) this._inject(phy, 114, ampB0);
          if (tick === this.cfg.nudgeTick && ampB_nudge > 0) this._inject(phy, 114, ampB_nudge);

          phy.step(this.cfg.dt, pressCUsed, dampUsed);

          const basin = this._pickBasin(phy);
          const top2 = this._top2Edges(phy, this.cfg.includeBackgroundEdges);

          const max1Pair = `${top2.best1.from}->${top2.best1.to}`;

          const f114_89 = this._edgeFlux(phy, i114_89);
          const f114_79 = this._edgeFlux(phy, i114_79);
          const f136_89 = this._edgeFlux(phy, i136_89);
          const f136_79 = this._edgeFlux(phy, i136_79);

          const f89_79 = this._edgeFlux(phy, i89_79);

          peak114_abs = Math.max(peak114_abs, Math.max(Math.abs(f114_89), Math.abs(f114_79)));
          peak136_abs = Math.max(peak136_abs, Math.max(Math.abs(f136_89), Math.abs(f136_79)));
          cross_peakAbs_89_79 = Math.max(cross_peakAbs_89_79, Math.abs(f89_79));

          if (busSet.has(max1Pair)) {
            if (firstBusMax_tick == null) {
              firstBusMax_tick = tick;
              firstBusMax_edge = max1Pair;
            }
            if (is114Bus(max1Pair) && first114Max_tick == null) first114Max_tick = tick;
            if (is136Bus(max1Pair) && first136Max_tick == null) first136Max_tick = tick;
          }

          traceLines.push(this._csvRow([
            this.version, runId, runIndex, repIndex,
            (cap.capLawHash ?? ""),
            pressCUsed, dampUsed,
            tick, (now - startMs), lateByMs, basin,
            top2.best1.from, top2.best1.to, top2.best1.af,
            top2.best2.from, top2.best2.to, top2.best2.af,
            f114_89, f114_79, f136_89, f136_79,
            f89_79
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
          (first114Max_tick != null && first136Max_tick != null && Math.abs(first114Max_tick - first136Max_tick) <= this.cfg.followWindowTicks)
            ? 1 : 0;

        let packetClass = "";
        if (precedence === "136_first" && fastFollow) packetClass = "136_then_114_fast";
        else if (precedence === "136_first") packetClass = "136_then_114_slow";
        else if (precedence === "114_first" && fastFollow) packetClass = "114_then_136_fast";
        else if (precedence === "114_first") packetClass = "114_then_136_slow";
        else if (precedence === "136_only") packetClass = "136_solo";
        else if (precedence === "114_only") packetClass = "114_solo";
        else packetClass = precedence;

        summaryLines.push(this._csvRow([
          this.version, runId, runIndex, repIndex,
          pressBase, dampBase, pressCUsed, dampUsed,
          this.cfg.dt, this.cfg.everyMs, this.cfg.totalTicks, this.cfg.settleTicks,
          (cap.capLawHash ?? ""), (cap.capLawSig ?? ""), (cap.capLawApplied ?? ""), (cap.dtUsed ?? ""),
          this.cfg.gain, this.cfg.multB, this.cfg.multD, this.cfg.offset,
          ampB0, ampD, ratioBD,
          this.cfg.nudgeTick, this.cfg.nudgeMult, ampB_nudge,
          injectTick114, injectTick136,
          (firstBusMax_tick == null ? "" : firstBusMax_tick),
          firstBusMax_edge,
          (first114Max_tick == null ? "" : first114Max_tick),
          (first136Max_tick == null ? "" : first136Max_tick),
          precedence,
          deltaTicks,
          fastFollow,
          packetClass,
          peak114_abs, peak136_abs,
          cross_peakAbs_89_79,
          visibilityStateStart, wasHidden
        ]));

        runIndex += 1;

        if (runIndex % 36 === 0) {
          console.log(
            `[16x] progress ${runIndex}/${plan.length} | p=${pressCUsed.toFixed(3)} d=${dampUsed.toFixed(3)} | prec=${precedence} class=${packetClass}` +
            ` | Δ=${deltaTicks} | cross89->79_peak=${cross_peakAbs_89_79.toExponential(3)}`
          );
        }
      }

      const endTag = this._iso(new Date());
      const baseName = `${this.version}_${startTag}_${endTag}`;

      this._unfreezeLiveLoop();

      this._download(`${baseName}_MASTER_summary.csv`, summaryLines.join(""));
      this._download(`${baseName}_MASTER_busTrace.csv`, traceLines.join(""));

      console.log(`✅ [16x] DONE. Upload:\n- ${baseName}_MASTER_summary.csv\n- ${baseName}_MASTER_busTrace.csv`);
      return { baseName, runs: runIndex, stopped: this._stop, pressCList, dampList };
    }
  };

  window.solPhase311_16x_packetRobustnessGrid_v1 = T;
  console.log(`✅ solPhase311_16x_packetRobustnessGrid_v1 installed (${T.version}). Run: await solPhase311_16x_packetRobustnessGrid_v1.run()`);
})();
