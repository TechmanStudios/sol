/* Phase 3.11.16v — Crosslink Probe + Post-Arb Nudge
   Purpose:
     - Quantify the “tertiary connection” (crosslink) you observed in UI.
     - Reduce 136_only cases by nudging 114 AFTER the arbiter tick (~13),
       so we don’t change who wins first—just whether the follower appears.

   Based on 16u environment:
     dt=0.12, everyMs=200, totalTicks=61, gain=22, pressC=2, damp=5 (pulled from invariants/UI)

   Key idea:
     - offset=+1 => 136 inject tick0, 114 inject tick1
     - optional nudge to 114 at tick14 (after arbiter moment) with nudgeMult ∈ [0..]
     - log crosslink flux if edges exist:
         114->136, 136->114, 79->89, 89->79

   Run:
     await solPhase311_16v_crosslinkNudge_v1.run()

   Stop:
     solPhase311_16v_crosslinkNudge_v1.stop()

   Outputs:
     ...MASTER_summary.csv
     ...MASTER_busTrace.csv

   UI-neutral: no camera moves.
*/
(() => {
  "use strict";

  const T = {
    version: "sol_phase311_16v_crosslinkNudge_v1",
    _stop: false,
    stop() { this._stop = true; },

    cfg: {
      dt: 0.12,
      everyMs: 200,
      totalTicks: 61,
      settleTicks: 3,
      spinWaitMs: 1.5,

      pressCUsed: null,
      baseDampUsed: null,

      // Priming
      wantId: 82,
      injectorIds: [90, 82],
      dreamBlocks: 15,
      dreamBlockSteps: 2,
      injectAmount: 120,
      finalWriteMult: 1,

      // Payload
      baseAmpB: 4.0,     // 114 port
      baseAmpD: 5.75,    // 136 port
      gain: 22,

      // Fix multB in the “safe” zone (no 114_first in 16u up through 1.146)
      // You can tweak later; this is a solid anchor.
      multB: 1.146,
      multD: 1.0,

      // Offset: +1 => 136 at tick0, 114 at tick1
      offset: +1,

      // Nudge AFTER arbiter tick (~13). This should not change who wins first.
      nudgeTick: 14,
      nudgeMultList: [0.00, 0.10, 0.20, 0.30, 0.40],
      repsPerCell: 24,

      includeBackgroundEdges: false,
      shuffle: true,

      // packet detection
      followWindowTicks: 6,

      // optional: if you want to see more crosslink dynamics, you can log more ticks or raise reps.
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
      throw new Error("[16v] timed out waiting for physics.");
    },

    _freezeLiveLoop() {
      const app = this._getApp();
      if (!app?.config) throw new Error("[16v] App not ready.");
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
      if (!n) throw new Error(`[16v] node not found: ${id}`);
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

    _frame(phy, includeBackgroundEdges) {
      const edges = phy.edges || [];
      let maxAbsEdgeFlux = 0, maxEdgeFrom = "", maxEdgeTo = "";
      for (let i = 0; i < edges.length; i++) {
        const e = edges[i];
        if (!e) continue;
        if (!includeBackgroundEdges && e.background) continue;
        const f = (typeof e.flux === "number" && Number.isFinite(e.flux)) ? e.flux : 0;
        const af = Math.abs(f);
        if (af > maxAbsEdgeFlux) {
          maxAbsEdgeFlux = af;
          maxEdgeFrom = e.from;
          maxEdgeTo = e.to;
        }
      }
      return { maxAbsEdgeFlux, maxEdgeFrom, maxEdgeTo };
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
      const pressCUsed = (this.cfg.pressCUsed != null) ? this.cfg.pressCUsed : (inv.pressC ?? ui.pressC ?? 2.0);
      const baseDampUsed = (this.cfg.baseDampUsed != null) ? this.cfg.baseDampUsed : (inv.damp ?? ui.damp ?? 5.0);

      const edgeIndex = this._buildEdgeIndex(phy);

      // Bus edges
      const i114_89 = edgeIndex.get("114->89");
      const i114_79 = edgeIndex.get("114->79");
      const i136_89 = edgeIndex.get("136->89");
      const i136_79 = edgeIndex.get("136->79");

      // Crosslink candidates (for your “tertiary connection”)
      const i114_136 = edgeIndex.get("114->136");
      const i136_114 = edgeIndex.get("136->114");
      const i79_89   = edgeIndex.get("79->89");
      const i89_79   = edgeIndex.get("89->79");

      const busSet = new Set(["114->89","114->79","136->89","136->79"]);
      const is114Bus = (pair) => pair === "114->89" || pair === "114->79";
      const is136Bus = (pair) => pair === "136->89" || pair === "136->79";

      // offset -> injection ticks
      let injectTick114 = 0, injectTick136 = 0;
      if (this.cfg.offset === -1) { injectTick114 = 0; injectTick136 = 1; }
      else if (this.cfg.offset === +1) { injectTick114 = 1; injectTick136 = 0; }
      else { injectTick114 = 0; injectTick136 = 0; }

      const baseB = this.cfg.baseAmpB * this.cfg.gain;
      const baseD = this.cfg.baseAmpD * this.cfg.gain;
      const ampB0 = baseB * this.cfg.multB;
      const ampD  = baseD * this.cfg.multD;
      const ratioBD = ampB0 / ampD;

      const startTag = this._iso(new Date());

      const plan = [];
      for (const nudgeMult of this.cfg.nudgeMultList) {
        for (let r = 1; r <= this.cfg.repsPerCell; r++) {
          plan.push({ nudgeMult, rep: r });
        }
      }
      if (this.cfg.shuffle) this._shuffle(plan);

      const summaryHeader = [
        "schema","runId","runIndex","repIndex",
        "pressCUsed","baseDampUsed","dt","everyMs","totalTicks","settleTicks",
        "capLawHash","capLawSig","capLawApplied","capLawDtUsed",
        "gain","multB","multD","offset",
        "ampB0","ampD","ratioBD",
        "nudgeTick","nudgeMult","ampB_nudge",
        "injectTick114","injectTick136",
        "firstBusMax_tick","firstBusMax_edge",
        "first114Max_tick","first136Max_tick","precedence",
        "deltaTicks","fastFollow","packetClass",
        "peak114_abs","peak136_abs",
        "cross_peakAbs_114_136","cross_peakAbs_136_114","cross_peakAbs_79_89","cross_peakAbs_89_79",
        "visibilityStateStart","wasHidden"
      ];

      const traceHeader = [
        "schema","runId","runIndex","repIndex",
        "capLawHash",
        "multB","offset",
        "nudgeMult",
        "tick","tMs","lateByMs","basin",
        "maxEdgeFrom","maxEdgeTo","maxAbsEdgeFlux",
        "flux_114_89","flux_114_79","flux_136_89","flux_136_79",
        "flux_114_136","flux_136_114","flux_79_89","flux_89_79"
      ];

      const summaryLines = [this._csvRow(summaryHeader)];
      const traceLines = [this._csvRow(traceHeader)];

      let runIndex = 0;

      console.log(`[16v] plan=${plan.length} | pressC=${pressCUsed} damp=${baseDampUsed} | gain=${this.cfg.gain} | multB=${this.cfg.multB} ratioBD=${ratioBD.toFixed(6)} | offset=${this.cfg.offset}`);

      for (const item of plan) {
        if (this._stop) break;

        const repIndex = item.rep;
        const nudgeMult = item.nudgeMult;
        const ampB_nudge = ampB0 * nudgeMult;

        const runId = `${this._iso(new Date())}_r${String(runIndex).padStart(5,"0")}_nM${nudgeMult}_rep${repIndex}`;

        const visibilityStateStart = document.visibilityState || "";
        let wasHidden = !!document.hidden;
        const onVis = () => { if (document.hidden) wasHidden = true; };
        document.addEventListener("visibilitychange", onVis, { passive: true });

        await this._baselineRestore(phy);
        const cap = await this._recomputeDerived(this.cfg.dt);

        await this._modeSelect(phy, pressCUsed, baseDampUsed);
        for (let s = 0; s < this.cfg.settleTicks; s++) phy.step(this.cfg.dt, pressCUsed, baseDampUsed);

        let firstBusMax_tick = null, firstBusMax_edge = "";
        let first114Max_tick = null;
        let first136Max_tick = null;

        let peak114_abs = 0;
        let peak136_abs = 0;

        let cross_peakAbs_114_136 = 0;
        let cross_peakAbs_136_114 = 0;
        let cross_peakAbs_79_89   = 0;
        let cross_peakAbs_89_79   = 0;

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

          phy.step(this.cfg.dt, pressCUsed, baseDampUsed);

          const basin = this._pickBasin(phy);
          const fm = this._frame(phy, this.cfg.includeBackgroundEdges);

          const f114_89 = this._edgeFlux(phy, i114_89);
          const f114_79 = this._edgeFlux(phy, i114_79);
          const f136_89 = this._edgeFlux(phy, i136_89);
          const f136_79 = this._edgeFlux(phy, i136_79);

          const f114_136 = this._edgeFlux(phy, i114_136);
          const f136_114 = this._edgeFlux(phy, i136_114);
          const f79_89   = this._edgeFlux(phy, i79_89);
          const f89_79   = this._edgeFlux(phy, i89_79);

          peak114_abs = Math.max(peak114_abs, Math.max(Math.abs(f114_89), Math.abs(f114_79)));
          peak136_abs = Math.max(peak136_abs, Math.max(Math.abs(f136_89), Math.abs(f136_79)));

          cross_peakAbs_114_136 = Math.max(cross_peakAbs_114_136, Math.abs(f114_136));
          cross_peakAbs_136_114 = Math.max(cross_peakAbs_136_114, Math.abs(f136_114));
          cross_peakAbs_79_89   = Math.max(cross_peakAbs_79_89,   Math.abs(f79_89));
          cross_peakAbs_89_79   = Math.max(cross_peakAbs_89_79,   Math.abs(f89_79));

          const maxPair = `${fm.maxEdgeFrom}->${fm.maxEdgeTo}`;
          if (busSet.has(maxPair)) {
            if (firstBusMax_tick == null) {
              firstBusMax_tick = tick;
              firstBusMax_edge = maxPair;
            }
            if (is114Bus(maxPair) && first114Max_tick == null) first114Max_tick = tick;
            if (is136Bus(maxPair) && first136Max_tick == null) first136Max_tick = tick;
          }

          traceLines.push(this._csvRow([
            this.version, runId, runIndex, repIndex,
            (cap.capLawHash ?? ""),
            this.cfg.multB, this.cfg.offset,
            nudgeMult,
            tick, (now - startMs), lateByMs, basin,
            fm.maxEdgeFrom, fm.maxEdgeTo, fm.maxAbsEdgeFlux,
            f114_89, f114_79, f136_89, f136_79,
            f114_136, f136_114, f79_89, f89_79
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
          pressCUsed, baseDampUsed, this.cfg.dt, this.cfg.everyMs, this.cfg.totalTicks, this.cfg.settleTicks,
          (cap.capLawHash ?? ""), (cap.capLawSig ?? ""), (cap.capLawApplied ?? ""), (cap.dtUsed ?? ""),
          this.cfg.gain, this.cfg.multB, this.cfg.multD, this.cfg.offset,
          ampB0, ampD, ratioBD,
          this.cfg.nudgeTick, nudgeMult, ampB_nudge,
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
          cross_peakAbs_114_136, cross_peakAbs_136_114, cross_peakAbs_79_89, cross_peakAbs_89_79,
          visibilityStateStart, wasHidden
        ]));

        runIndex += 1;

        if (runIndex % 40 === 0) {
          console.log(`[16v] progress ${runIndex}/${plan.length} | nudgeMult=${nudgeMult} | prec=${precedence} | class=${packetClass} | cross(114->136)peak=${cross_peakAbs_114_136.toFixed(3)}`);
        }
      }

      const endTag = this._iso(new Date());
      const baseName = `${this.version}_${startTag}_${endTag}`;

      this._unfreezeLiveLoop();

      this._download(`${baseName}_MASTER_summary.csv`, summaryLines.join(""));
      this._download(`${baseName}_MASTER_busTrace.csv`, traceLines.join(""));

      console.log(`✅ [16v] DONE. Upload:\n- ${baseName}_MASTER_summary.csv\n- ${baseName}_MASTER_busTrace.csv`);
      return { baseName, runs: runIndex, stopped: this._stop };
    }
  };

  window.solPhase311_16v_crosslinkNudge_v1 = T;
  console.log(`✅ solPhase311_16v_crosslinkNudge_v1 installed (${T.version}). Run: await solPhase311_16v_crosslinkNudge_v1.run()`);
})();
