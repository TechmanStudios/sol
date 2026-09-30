/* Phase 3.11 — 16AX: Continuous Hysteresis Probe (NO baseline restore between multB steps)
   Purpose:
     Detect true hysteresis / path dependence by ramping multB up then down while preserving state.

   Key idea:
     - Restore baseline ONCE at the beginning
     - Mode-select ONCE at the beginning
     - Then for each step:
         inject 136@t0, 114@t1 with current multB
         optional handshake nudge
         run segmentTicks
         record metrics
       (no restore before next step)

   Default path:
     up:   0.90,0.92,0.94,0.95,0.96,0.97,0.98,0.99,1.00
     down: 1.00,0.99,0.98,0.97,0.96,0.95,0.94,0.92,0.90

   Outputs:
     - ..._MASTER_summary.csv  (one row per segment)
     - ..._MASTER_busTrace.csv (tick trace inside each segment)

   Run:
     await solPhase311_16ax_hysteresisContinuous_v1.run()

   Stop:
     solPhase311_16ax_hysteresisContinuous_v1.stop()
*/
(() => {
  "use strict";

  const H = {
    version: "sol_phase311_16ax_hysteresisContinuous_v1",
    _stop: false,
    stop(){ this._stop = true; },

    cfg: {
      // Timing
      dt: 0.12,
      segmentTicks: 41,      // ticks per multB step
      betweenStepTicks: 8,   // relax ticks between steps (no injections)

      // Pressure
      pressCBase: null,

      // Mode-select priming (only once)
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
      handshakeTick: 2,

      // Fixed damp + order (B2)
      dampUsed: 20,
      injectTick136: 0,
      injectTick114: 1,

      // Marker
      markerTick: 8,

      // Paths
      upList:   [0.90,0.92,0.94,0.95,0.96,0.97,0.98,0.99,1.00],
      downList: [1.00,0.99,0.98,0.97,0.96,0.95,0.94,0.92,0.90],

      // Repeat each step N times (still continuous, no restore) — keep 1 unless you want “dwell”
      repsPerStep: 1,

      // Trace
      includeBackgroundEdges: false,

      // Safety
      abortOnNonFinite: true,

      label: "B2_d20_hysteresis_continuous"
    },

    _sleep(ms){ return new Promise(r => setTimeout(r, ms)); },
    _p2(n){ return String(n).padStart(2,"0"); },
    _p3(n){ return String(n).padStart(3,"0"); },
    _iso(d = new Date()){
      return `${d.getUTCFullYear()}-${this._p2(d.getUTCMonth()+1)}-${this._p2(d.getUTCDate())}` +
             `T${this._p2(d.getUTCHours())}-${this._p2(d.getUTCMinutes())}-${this._p2(d.getUTCSeconds())}-${this._p3(d.getUTCMilliseconds())}Z`;
    },

    _csvCell(v){
      if (v === null || v === undefined) return "";
      const s = String(v);
      return /[",\n\r]/.test(s) ? `"${s.replace(/"/g,'""')}"` : s;
    },
    _csvRow(cols){ return cols.map(v => this._csvCell(v)).join(",") + "\n"; },

    _download(filename, text){
      const blob = new Blob([text], { type: "text/csv" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = filename;
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => { try { URL.revokeObjectURL(url); } catch(e){} }, 250);
    },

    _getApp(){ return window.SOLDashboard || window.solDashboard || window.App || null; },

    async _waitForPhysics(timeoutMs = 15000, pollMs = 50){
      const start = performance.now();
      while ((performance.now() - start) < timeoutMs){
        const app = this._getApp();
        const phy =
          (window.solver && window.solver.nodes && window.solver.edges) ? window.solver :
          (app && app.state && app.state.physics) ? app.state.physics :
          null;
        if (phy?.nodes?.length && phy?.edges?.length && typeof phy.step === "function") return phy;
        await this._sleep(pollMs);
      }
      throw new Error("[16ax] timed out waiting for physics.");
    },

    _freezeLiveLoop(){
      const app = this._getApp();
      if (!app?.config) throw new Error("[16ax] App not ready.");
      if (this._prevDtCap === undefined) this._prevDtCap = app.config.dtCap;
      app.config.dtCap = 0;
    },
    _unfreezeLiveLoop(){
      const app = this._getApp();
      if (!app?.config) return;
      if (this._prevDtCap !== undefined){
        app.config.dtCap = this._prevDtCap;
        this._prevDtCap = undefined;
      }
    },

    _readUiParams(){
      const app = this._getApp();
      const pressC = (app?.dom?.pressureSlider)
        ? (parseFloat(String(app.dom.pressureSlider.value)) * (app.config.pressureSliderScale || 1))
        : null;
      return { pressC: Number.isFinite(pressC) ? pressC : null };
    },

    _nodeById(phy, id){
      const want = String(id);
      for (const n of (phy.nodes || [])) if (n?.id != null && String(n.id) === want) return n;
      return null;
    },

    _inject(phy, id, amt){
      const n = this._nodeById(phy, id);
      if (!n) throw new Error(`[16ax] node not found: ${id}`);
      const a = Math.max(0, Number(amt) || 0);
      n.rho += a;
      try{
        if (n.isConstellation && typeof phy.reinforceSemanticStar === "function"){
          phy.reinforceSemanticStar(n, (a / 50.0));
        }
      }catch(e){}
    },

    _buildEdgeIndex(phy){
      const map = new Map();
      const edges = phy.edges || [];
      for (let i = 0; i < edges.length; i++){
        const e = edges[i];
        if (!e) continue;
        map.set(`${e.from}->${e.to}`, i);
      }
      return map;
    },

    _edgeFlux(phy, idx){
      if (idx == null) return 0;
      const e = (phy.edges || [])[idx];
      const f = (e && typeof e.flux === "number" && Number.isFinite(e.flux)) ? e.flux : 0;
      return f;
    },

    _top2Edges(phy){
      const edges = phy.edges || [];
      let best1 = { af: -1, from: "", to: "", flux: 0 };
      let best2 = { af: -1, from: "", to: "", flux: 0 };

      for (let i = 0; i < edges.length; i++){
        const e = edges[i];
        if (!e) continue;
        if (!this.cfg.includeBackgroundEdges && e.background) continue;
        const f = (typeof e.flux === "number" && Number.isFinite(e.flux)) ? e.flux : 0;
        const af = Math.abs(f);
        if (af > best1.af){
          best2 = best1;
          best1 = { af, from: e.from, to: e.to, flux: f };
        } else if (af > best2.af){
          best2 = { af, from: e.from, to: e.to, flux: f };
        }
      }
      return { best1, best2 };
    },

    async _recomputeDerived(dt){
      try{
        if (window.SOLRuntime?.recomputeDerived) return await window.SOLRuntime.recomputeDerived({ dt });
      }catch(e){}
      return { capLawHash: null };
    },

    async _baselineRestoreOnce(phy){
      if (window.SOLBaseline?.restore){
        await window.SOLBaseline.restore();
        return "SOLBaseline.restore";
      }
      // internal snapshot if baseline missing
      if (!this._snap){
        const nodes = (phy.nodes || []).map(n => [String(n.id), {
          rho:n.rho, p:n.p, psi:n.psi, psi_bias:n.psi_bias,
          semanticMass:n.semanticMass, semanticMass0:n.semanticMass0,
          b_q:n.b_q, b_charge:n.b_charge, b_state:n.b_state,
          x:n.x, y:n.y, vx:n.vx, vy:n.vy, fx:n.fx, fy:n.fy
        }]);
        const edges = (phy.edges || []).map((e,i) => [i, { flux: e?.flux }]);
        this._snap = { nodes, edges, t: (phy._t ?? 0) };
      }
      // restore from internal snapshot
      const nMap = new Map(this._snap.nodes);
      for (const n of (phy.nodes || [])){
        const s = nMap.get(String(n.id));
        if (!s) continue;
        for (const k in s){ try { n[k] = s[k]; } catch(e){} }
      }
      const eMap = new Map(this._snap.edges);
      for (let i = 0; i < (phy.edges || []).length; i++){
        const s = eMap.get(i);
        if (!s) continue;
        try { phy.edges[i].flux = s.flux; } catch(e){}
      }
      try { phy._t = this._snap.t || 0; } catch(e){}
      return "internal_snapshot_restored";
    },

    async _modeSelectOnce(phy, pressC, damp){
      const c = this.cfg;
      let idx = 0;
      for (let b = 0; b < Math.max(0, c.dreamBlocks - 1); b++){
        const injId = c.injectorIds[idx % c.injectorIds.length];
        idx++;
        this._inject(phy, injId, c.injectAmount);
        for (let s = 0; s < c.dreamBlockSteps; s++) phy.step(c.dt, pressC, damp);
      }
      this._inject(phy, c.wantId, c.injectAmount * (c.finalWriteMult || 1));
      try { if (typeof phy.computePressure === "function") phy.computePressure(pressC); } catch(e){}
    },

    _isFiniteNums(nums){
      for (const v of nums) if (typeof v !== "number" || !Number.isFinite(v)) return false;
      return true;
    },

    _argmaxCount(m){
      let bestK = "", bestV = -1;
      for (const [k,v] of m.entries()){
        if (v > bestV){ bestV = v; bestK = k; }
      }
      return { key: bestK, count: bestV };
    },

    async _runPath(phy, pressCUsed, edgeIndex, baseNameTag, dirTag, multList, baseB, ampD){
      const g = this.cfg;
      const i114_89 = edgeIndex.get("114->89");
      const i114_79 = edgeIndex.get("114->79");
      const i136_89 = edgeIndex.get("136->89");
      const i136_79 = edgeIndex.get("136->79");

      const summaryHeader = [
        "schema","runTag","dir","stepIndex","stepRep","multBUsed",
        "pressCUsed","dampUsed","capLawHash",
        "ampB0","ampD","ratioBD",
        "peakAbs114_bus","peakAbs136_bus","ratioPeak_114over136","winner_peakBus",
        "t8_abs114_bus","t8_abs136_bus","winner_t8",
        "laneEdge","laneEdge_count"
      ];

      const traceHeader = [
        "schema","runTag","dir","stepIndex","stepRep","multBUsed","tick",
        "max1_from","max1_to","max1_absFlux",
        "flux_114_89","flux_114_79","flux_136_89","flux_136_79",
        "abs114_bus","abs136_bus"
      ];

      const summaryLines = [this._csvRow(summaryHeader)];
      const traceLines = [this._csvRow(traceHeader)];

      for (let s = 0; s < multList.length; s++){
        if (this._stop) break;

        const multBUsed = multList[s];

        for (let rep = 1; rep <= g.repsPerStep; rep++){
          if (this._stop) break;

          const cap = await this._recomputeDerived(g.dt);

          const ampB0 = baseB * multBUsed;
          const ratioBD = ampB0 / ampD;
          const ampB_nudge = ampB0 * g.nudgeMult;

          let peakAbs114 = 0, peakAbs136 = 0;
          let t8_abs114 = "", t8_abs136 = "";
          const laneCounts = new Map();

          // Segment ticks
          let aborted = false;

          for (let tick = 0; tick < g.segmentTicks; tick++){
            if (this._stop) break;

            // injections (B2)
            if (tick === g.injectTick136) this._inject(phy, 136, ampD);
            if (tick === g.injectTick114) this._inject(phy, 114, ampB0);
            if (tick === g.handshakeTick && ampB_nudge > 0) this._inject(phy, 114, ampB_nudge);

            phy.step(g.dt, pressCUsed, g.dampUsed);

            const top2 = this._top2Edges(phy);
            const max1Pair = `${top2.best1.from}->${top2.best1.to}`;
            laneCounts.set(max1Pair, (laneCounts.get(max1Pair) || 0) + 1);

            const f114_89 = this._edgeFlux(phy, i114_89);
            const f114_79 = this._edgeFlux(phy, i114_79);
            const f136_89 = this._edgeFlux(phy, i136_89);
            const f136_79 = this._edgeFlux(phy, i136_79);

            const abs114 = Math.max(Math.abs(f114_89), Math.abs(f114_79));
            const abs136 = Math.max(Math.abs(f136_89), Math.abs(f136_79));

            if (g.abortOnNonFinite){
              const ok = this._isFiniteNums([top2.best1.af, top2.best2.af, f114_89,f114_79,f136_89,f136_79,abs114,abs136]);
              if (!ok){ aborted = true; break; }
            }

            if (abs114 > peakAbs114) peakAbs114 = abs114;
            if (abs136 > peakAbs136) peakAbs136 = abs136;

            if (tick === g.markerTick){ t8_abs114 = abs114; t8_abs136 = abs136; }

            traceLines.push(this._csvRow([
              this.version, baseNameTag, dirTag, s, rep, multBUsed, tick,
              top2.best1.from, top2.best1.to, top2.best1.af,
              f114_89, f114_79, f136_89, f136_79,
              abs114, abs136
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
            this.version, baseNameTag, dirTag, s, rep, multBUsed,
            pressCUsed, g.dampUsed, (cap.capLawHash ?? ""),
            ampB0, ampD, ratioBD,
            peakAbs114, peakAbs136, ratioPeak, winner_peakBus,
            t8_abs114, t8_abs136, winner_t8,
            lane.key, lane.count
          ]));

          // Relax between repeats (still continuous)
          for (let rlx = 0; rlx < g.betweenStepTicks; rlx++){
            if (this._stop) break;
            phy.step(g.dt, pressCUsed, g.dampUsed);
          }

          if (aborted) break;
        }
      }

      return { summaryLines, traceLines };
    },

    async run(userCfg = {}){
      this._stop = false;
      this.cfg = { ...this.cfg, ...userCfg };

      const g = this.cfg;
      const phy = await this._waitForPhysics();
      this._freezeLiveLoop();

      const ui = this._readUiParams();
      const inv = window.SOLRuntime?.getInvariants?.() || {};
      const pressCUsed = (g.pressCBase != null) ? g.pressCBase : (inv.pressC ?? ui.pressC ?? 2.0);

      const baseB = g.baseAmpB * g.gain; // 88
      const baseD = g.baseAmpD * g.gain; // 126.5
      const ampD  = baseD * g.multD;

      const startTag = this._iso(new Date());
      const baseNameTag = `${this.version}_${startTag}`;
      console.log(`[16ax] START ${this.version} @ ${startTag} | pressC=${pressCUsed} | damp=${g.dampUsed}`);

      // Restore baseline ONCE, then mode-select ONCE
      const baselineMode = await this._baselineRestoreOnce(phy);
      console.log(`[16ax] baselineMode=${baselineMode} (restore ONCE; then continuous evolution)`);

      await this._modeSelectOnce(phy, pressCUsed, g.dampUsed);

      // Edge index (stable)
      const edgeIndex = this._buildEdgeIndex(phy);

      // Up path
      const upRes = await this._runPath(phy, pressCUsed, edgeIndex, baseNameTag, "up", g.upList, baseB, ampD);

      // Small separator relax before down path (still continuous; no restore)
      for (let k = 0; k < g.betweenStepTicks * 2; k++){
        if (this._stop) break;
        phy.step(g.dt, pressCUsed, g.dampUsed);
      }

      // Down path
      const dnRes = await this._runPath(phy, pressCUsed, edgeIndex, baseNameTag, "down", g.downList, baseB, ampD);

      const endTag = this._iso(new Date());
      const baseName = `${this.version}_${startTag}_${endTag}`;

      this._unfreezeLiveLoop();

      // Download (2 files total, combined up+down)
      const summary = upRes.summaryLines.concat(dnRes.summaryLines.slice(1)); // drop duplicate header
      const trace   = upRes.traceLines.concat(dnRes.traceLines.slice(1));

      this._download(`${baseName}_MASTER_summary.csv`, summary.join(""));
      this._download(`${baseName}_MASTER_busTrace.csv`, trace.join(""));

      console.log(`[16ax] DONE @ ${endTag}\n- ${baseName}_MASTER_summary.csv\n- ${baseName}_MASTER_busTrace.csv`);
      return { baseName, pressCUsed, dampUsed: g.dampUsed, stopped: this._stop };
    }
  };

  window.solPhase311_16ax_hysteresisContinuous_v1 = H;
  console.log(`✅ solPhase311_16ax_hysteresisContinuous_v1 installed. Run: await solPhase311_16ax_hysteresisContinuous_v1.run()`);
})();
