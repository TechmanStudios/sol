/* Phase 3.11 — 16AZ: Late-boundary Hysteresis Zoom (preconditioned, continuous)
   Focus: multB in [0.94..0.96] with fine spacing.
   - dampUsed = 20
   - B2 order: 136@t0, 114@t1
   - Precondition LOW then UP path
   - Precondition HIGH then DOWN path
   - Continuous within each path (NO restore between steps)
*/
(() => {
  "use strict";

  const R = {
    version: "sol_phase311_16az_lateBoundaryHysteresisZoom_v1",
    _stop: false,
    stop(){ this._stop = true; },

    cfg: {
      dt: 0.12,
      segmentTicks: 121,
      betweenStepTicks: 50,
      repsPerStep: 15,

      pressCBase: null,

      // Mode select (once)
      wantId: 82,
      injectorIds: [90, 82],
      dreamBlocks: 15,
      dreamBlockSteps: 2,
      injectAmount: 120,
      finalWriteMult: 1,

      // Amps
      baseAmpB: 4.0,
      baseAmpD: 5.75,
      gain: 22,
      multD: 1.0,

      // Handshake
      nudgeMult: 0.20,
      handshakeTick: 2,

      // Fixed
      dampUsed: 20,
      injectTick136: 0,
      injectTick114: 1,
      markerTick: 8,

      // Preconditioning (stronger separation)
      preLow_multB: 0.90,
      preLow_ticks: 320,
      preHigh_multB: 1.08,
      preHigh_ticks: 320,

      // Zoom lists (late boundary band)
      upList:   [0.940,0.943,0.945,0.947,0.949,0.950,0.951,0.952,0.953,0.954,0.955,0.956,0.957,0.958,0.959,0.960],
      downList: [0.960,0.959,0.958,0.957,0.956,0.955,0.954,0.953,0.952,0.951,0.950,0.949,0.947,0.945,0.943,0.940],

      // Capture definition (ignore the very early injection transient)
      captureStreak: 5,
      captureStartTick: 5,

      includeBackgroundEdges: false,
      abortOnNonFinite: true,

      label: "B2_d20_lateBoundary_hysteresis_zoom"
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
      throw new Error("[16az] timed out waiting for physics.");
    },

    _freezeLiveLoop(){
      const app = this._getApp();
      if (!app?.config) throw new Error("[16az] App not ready.");
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
      if (!n) throw new Error(`[16az] node not found: ${id}`);
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

    _entropyFromCounts(counts){
      let total = 0;
      for (const v of counts.values()) total += v;
      if (total <= 0) return 0;
      let H = 0;
      for (const v of counts.values()){
        const p = v / total;
        if (p > 0) H -= p * (Math.log(p) / Math.log(2));
      }
      return H;
    },

    _captureTick(domSeq, who, streak, startTick){
      let run = 0;
      for (let i = Math.max(0, startTick|0); i < domSeq.length; i++){
        if (domSeq[i] === who){
          run++;
          if (run >= streak) return i - streak + 1;
        } else run = 0;
      }
      return "";
    },

    async _runPrecondition(phy, pressCUsed, multBUsed, ticks, baseB, ampD){
      const g = this.cfg;
      const ampB0 = baseB * multBUsed;
      const ampB_nudge = ampB0 * g.nudgeMult;

      for (let t = 0; t < ticks; t++){
        if (this._stop) break;

        if (t === g.injectTick136) this._inject(phy, 136, ampD);
        if (t === g.injectTick114) this._inject(phy, 114, ampB0);
        if (t === g.handshakeTick && ampB_nudge > 0) this._inject(phy, 114, ampB_nudge);

        phy.step(g.dt, pressCUsed, g.dampUsed);
      }
      for (let r = 0; r < g.betweenStepTicks; r++){
        if (this._stop) break;
        phy.step(g.dt, pressCUsed, g.dampUsed);
      }
    },

    async _runPath(phy, pressCUsed, edgeIndex, runTag, dirTag, multList, baseB, ampD, summaryLines, traceLines){
      const g = this.cfg;
      const i114_89 = edgeIndex.get("114->89");
      const i114_79 = edgeIndex.get("114->79");
      const i136_89 = edgeIndex.get("136->89");
      const i136_79 = edgeIndex.get("136->79");

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
          const busDomCounts = new Map([["114",0],["136",0],["tie",0]]);
          const busDomSeq = [];

          let prevMax1 = "";
          let max1_switchCount = 0;

          let prevBusDom = "";
          let bus_switchCount = 0;

          let aborted = false;

          for (let tick = 0; tick < g.segmentTicks; tick++){
            if (this._stop) break;

            if (tick === g.injectTick136) this._inject(phy, 136, ampD);
            if (tick === g.injectTick114) this._inject(phy, 114, ampB0);
            if (tick === g.handshakeTick && ampB_nudge > 0) this._inject(phy, 114, ampB_nudge);

            phy.step(g.dt, pressCUsed, g.dampUsed);

            const top2 = this._top2Edges(phy);
            const max1Pair = `${top2.best1.from}->${top2.best1.to}`;
            laneCounts.set(max1Pair, (laneCounts.get(max1Pair) || 0) + 1);
            if (prevMax1 && max1Pair !== prevMax1) max1_switchCount++;
            prevMax1 = max1Pair;

            const f114_89 = this._edgeFlux(phy, i114_89);
            const f114_79 = this._edgeFlux(phy, i114_79);
            const f136_89 = this._edgeFlux(phy, i136_89);
            const f136_79 = this._edgeFlux(phy, i136_79);

            const abs114 = Math.max(Math.abs(f114_89), Math.abs(f114_79));
            const abs136 = Math.max(Math.abs(f136_89), Math.abs(f136_79));

            if (g.abortOnNonFinite){
              const ok = this._isFiniteNums([top2.best1.af, top2.best2.af, f114_89,f114_79,f136_89,f136_79, abs114, abs136]);
              if (!ok){ aborted = true; break; }
            }

            if (abs114 > peakAbs114) peakAbs114 = abs114;
            if (abs136 > peakAbs136) peakAbs136 = abs136;

            if (tick === g.markerTick){ t8_abs114 = abs114; t8_abs136 = abs136; }

            const busDom = (abs114 > abs136) ? "114" : (abs136 > abs114) ? "136" : "tie";
            busDomSeq.push(busDom);
            busDomCounts.set(busDom, (busDomCounts.get(busDom) || 0) + 1);

            if (prevBusDom && busDom !== prevBusDom) bus_switchCount++;
            prevBusDom = busDom;

            traceLines.push(this._csvRow([
              this.version, runTag, dirTag, s, rep, multBUsed, tick,
              top2.best1.from, top2.best1.to, top2.best1.af,
              top2.best2.from, top2.best2.to, top2.best2.af,
              f114_89, f114_79, f136_89, f136_79,
              abs114, abs136, busDom
            ]));
          }

          const winner_peakBus =
            (peakAbs114 > peakAbs136) ? 114 :
            (peakAbs136 > peakAbs114) ? 136 : 0;

          const winner_t8 =
            (t8_abs114 === "" || t8_abs136 === "") ? 0 :
            (t8_abs114 > t8_abs136) ? 114 :
            (t8_abs136 > t8_abs114) ? 136 : 0;

          const ratioPeak = (peakAbs136 > 0) ? (peakAbs114 / peakAbs136) : "";

          // lane mode
          let laneEdge = "", laneEdge_count = -1;
          for (const [k,v] of laneCounts.entries()){
            if (v > laneEdge_count){ laneEdge = k; laneEdge_count = v; }
          }
          const laneEntropy = this._entropyFromCounts(laneCounts);

          const ticksTotal = busDomSeq.length || 1;
          const fracBus114 = (busDomCounts.get("114") || 0) / ticksTotal;
          const fracBus136 = (busDomCounts.get("136") || 0) / ticksTotal;
          const busEntropy = this._entropyFromCounts(busDomCounts);

          const cap114 = this._captureTick(busDomSeq, "114", g.captureStreak, g.captureStartTick);
          const cap136 = this._captureTick(busDomSeq, "136", g.captureStreak, g.captureStartTick);

          summaryLines.push(this._csvRow([
            this.version, runTag, dirTag, s, rep, multBUsed,
            pressCUsed, g.dampUsed, (cap.capLawHash ?? ""),
            ampB0, ampD, ratioBD,
            peakAbs114, peakAbs136, ratioPeak, winner_peakBus,
            t8_abs114, t8_abs136, winner_t8,
            laneEdge, laneEdge_count, laneEntropy, max1_switchCount,
            fracBus114, fracBus136, busEntropy, bus_switchCount,
            cap114, cap136
          ]));

          for (let rlx = 0; rlx < g.betweenStepTicks; rlx++){
            if (this._stop) break;
            phy.step(g.dt, pressCUsed, g.dampUsed);
          }

          if (aborted) break;
        }
      }
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
      const runTag = `${this.version}_${startTag}`;
      console.log(`[16az] START ${this.version} @ ${startTag} | pressC=${pressCUsed} | damp=${g.dampUsed}`);

      const baselineMode = await this._baselineRestoreOnce(phy);
      console.log(`[16az] baselineMode=${baselineMode} (restore ONCE; then continuous per path)`);

      await this._modeSelectOnce(phy, pressCUsed, g.dampUsed);

      const edgeIndex = this._buildEdgeIndex(phy);

      const summaryHeader = [
        "schema","runTag","dir","stepIndex","stepRep","multBUsed",
        "pressCUsed","dampUsed","capLawHash",
        "ampB0","ampD","ratioBD",
        "peakAbs114_bus","peakAbs136_bus","ratioPeak_114over136","winner_peakBus",
        "t8_abs114_bus","t8_abs136_bus","winner_t8",
        "laneEdge","laneEdge_count","laneEntropy_bits","max1_switchCount",
        "fracTicks_busDom114","fracTicks_busDom136","busDomEntropy_bits","busDom_switchCount",
        "captureTick_114","captureTick_136"
      ];

      const traceHeader = [
        "schema","runTag","dir","stepIndex","stepRep","multBUsed","tick",
        "max1_from","max1_to","max1_absFlux",
        "max2_from","max2_to","max2_absFlux",
        "flux_114_89","flux_114_79","flux_136_89","flux_136_79",
        "abs114_bus","abs136_bus","busDom"
      ];

      const summaryLines = [this._csvRow(summaryHeader)];
      const traceLines = [this._csvRow(traceHeader)];

      // LOW precondition -> UP
      console.log(`[16az] preLow multB=${g.preLow_multB} for ${g.preLow_ticks} ticks`);
      await this._runPrecondition(phy, pressCUsed, g.preLow_multB, g.preLow_ticks, baseB, ampD);

      console.log("[16az] UP path...");
      await this._runPath(phy, pressCUsed, edgeIndex, runTag, "up", g.upList, baseB, ampD, summaryLines, traceLines);

      // HIGH precondition -> DOWN
      console.log(`[16az] preHigh multB=${g.preHigh_multB} for ${g.preHigh_ticks} ticks`);
      await this._runPrecondition(phy, pressCUsed, g.preHigh_multB, g.preHigh_ticks, baseB, ampD);

      console.log("[16az] DOWN path...");
      await this._runPath(phy, pressCUsed, edgeIndex, runTag, "down", g.downList, baseB, ampD, summaryLines, traceLines);

      const endTag = this._iso(new Date());
      const baseName = `${this.version}_${startTag}_${endTag}`;

      this._unfreezeLiveLoop();

      this._download(`${baseName}_MASTER_summary.csv`, summaryLines.join(""));
      this._download(`${baseName}_MASTER_busTrace.csv`, traceLines.join(""));

      console.log(`[16az] DONE @ ${endTag}\n- ${baseName}_MASTER_summary.csv\n- ${baseName}_MASTER_busTrace.csv`);
      return { baseName, pressCUsed, dampUsed: g.dampUsed, stopped: this._stop };
    }
  };

  window.solPhase311_16az_lateBoundaryHysteresisZoom_v1 = R;
  console.log(`✅ solPhase311_16az_lateBoundaryHysteresisZoom_v1 installed.\nRun: await solPhase311_16az_lateBoundaryHysteresisZoom_v1.run()`);
})();
