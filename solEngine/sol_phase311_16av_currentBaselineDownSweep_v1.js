/* Phase 3.11 — 16AV: Current-baseline down-sweep + baseline fingerprint (busFlux arbitration)
   Goal: Map the bus-flux threshold *within the current basin* (whatever baseline v1.5 restored).

   Key outputs:
     - baselineFp: short hash of (x,y,vx,vy) for key nodes + physics.globalBias (if present)
     - winner_peakBus, winner_t8 (bus arbitration)
     - laneEdge mode + laneEdge_count (basin indicator)

   Fixed:
     - dampUsed = 20
     - order = B2 (136@t0, 114@t1)
     - pressC inferred (usually 2)

   Sweep defaults:
     multBUsedList = [0.78,0.80,0.82,0.84,0.86,0.88,0.90,0.92,0.94,0.96,0.98,1.00]
     repsPerCond   = 60
     shuffle       = true

   Run:
     await solPhase311_16av_currentBaselineDownSweep_v1.run()

   Stop:
     solPhase311_16av_currentBaselineDownSweep_v1.stop()
*/
(() => {
  "use strict";

  const T = {
    version: "sol_phase311_16av_currentBaselineDownSweep_v1",
    _stop: false,
    stop() { this._stop = true; },

    cfg: {
      // Timing
      dt: 0.12,
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

      // Handshake (kept consistent)
      nudgeMult: 0.20,
      handshakeTick: 2,

      // Fixed damp + order (B2)
      dampUsed: 20,
      injectTick136: 0,
      injectTick114: 1,

      // Marker
      markerTick: 8,

      // Run quality (lane stability)
      laneEdgeCountGoodMin: 30,

      // Safety
      abortOnNonFinite: true,

      // Sweep
      multBUsedList: [0.78,0.80,0.82,0.84,0.86,0.88,0.90,0.92,0.94,0.96,0.98,1.00],
      repsPerCond: 60,
      shuffle: true,

      label: "B2_d20_downSweep_currentBaseline"
    },

    _sleep(ms){ return new Promise(r=>setTimeout(r,ms)); },
    _p2(n){ return String(n).padStart(2,"0"); },
    _p3(n){ return String(n).padStart(3,"0"); },
    _iso(d=new Date()){
      return `${d.getUTCFullYear()}-${this._p2(d.getUTCMonth()+1)}-${this._p2(d.getUTCDate())}` +
             `T${this._p2(d.getUTCHours())}-${this._p2(d.getUTCMinutes())}-${this._p2(d.getUTCSeconds())}-${this._p3(d.getUTCMilliseconds())}Z`;
    },

    _csvCell(v){
      if (v===null || v===undefined) return "";
      const s = String(v);
      return /[",\n\r]/.test(s) ? `"${s.replace(/"/g,'""')}"` : s;
    },
    _csvRow(cols){ return cols.map(v=>this._csvCell(v)).join(",") + "\n"; },

    _download(filename, text){
      const blob = new Blob([text], { type:"text/csv" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = filename;
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(()=>{ try{ URL.revokeObjectURL(url);}catch(e){} }, 250);
    },

    _getApp(){ return window.SOLDashboard || window.solDashboard || window.App || null; },

    async _waitForPhysics(timeoutMs=15000, pollMs=50){
      const start = performance.now();
      while ((performance.now()-start) < timeoutMs){
        const app = this._getApp();
        const phy =
          (window.solver && window.solver.nodes && window.solver.edges) ? window.solver :
          (app && app.state && app.state.physics) ? app.state.physics :
          null;
        if (phy?.nodes?.length && phy?.edges?.length && typeof phy.step === "function") return phy;
        await this._sleep(pollMs);
      }
      throw new Error("[16av] timed out waiting for physics.");
    },

    _freezeLiveLoop(){
      const app = this._getApp();
      if (!app?.config) throw new Error("[16av] App not ready.");
      if (this._prevDtCap === undefined) this._prevDtCap = app.config.dtCap;
      app.config.dtCap = 0;
    },
    _unfreezeLiveLoop(){
      const app = this._getApp();
      if (!app?.config) return;
      if (this._prevDtCap !== undefined){ app.config.dtCap = this._prevDtCap; this._prevDtCap = undefined; }
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
      if (!n) throw new Error(`[16av] node not found: ${id}`);
      const a = Math.max(0, Number(amt) || 0);
      n.rho += a;
      try{
        if (n.isConstellation && typeof phy.reinforceSemanticStar === "function"){
          phy.reinforceSemanticStar(n, (a/50.0));
        }
      }catch(e){}
    },

    _buildEdgeIndex(phy){
      const map = new Map();
      const edges = phy.edges || [];
      for (let i=0;i<edges.length;i++){
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
      let best1 = { af:-1, from:"", to:"", flux:0 };
      let best2 = { af:-1, from:"", to:"", flux:0 };
      for (let i=0;i<edges.length;i++){
        const e = edges[i];
        if (!e || e.background) continue;
        const f = (typeof e.flux === "number" && Number.isFinite(e.flux)) ? e.flux : 0;
        const af = Math.abs(f);
        if (af > best1.af){
          best2 = best1;
          best1 = { af, from:e.from, to:e.to, flux:f };
        } else if (af > best2.af){
          best2 = { af, from:e.from, to:e.to, flux:f };
        }
      }
      return { best1, best2 };
    },

    async _recomputeDerived(dt){
      try{
        if (window.SOLRuntime?.recomputeDerived) return await window.SOLRuntime.recomputeDerived({ dt });
      }catch(e){}
      return { capLawHash:null };
    },

    async _baselineRestore(phy){
      if (window.SOLBaseline?.restore){
        await window.SOLBaseline.restore();
        return "SOLBaseline.restore";
      }
      if (!this._snap){
        const nodes = (phy.nodes||[]).map(n => [String(n.id), {
          rho:n.rho, p:n.p, psi:n.psi, psi_bias:n.psi_bias,
          semanticMass:n.semanticMass, semanticMass0:n.semanticMass0,
          b_q:n.b_q, b_charge:n.b_charge, b_state:n.b_state,
          x:n.x, y:n.y, vx:n.vx, vy:n.vy, fx:n.fx, fy:n.fy
        }]);
        const edges = (phy.edges||[]).map((e,i)=>[i,{ flux:e?.flux }]);
        this._snap = { nodes, edges, t:(phy._t ?? 0) };
        return "internal_snapshot_created";
      }
      const nMap = new Map(this._snap.nodes);
      for (const n of (phy.nodes||[])){
        const s = nMap.get(String(n.id));
        if (!s) continue;
        for (const k in s){ try{ n[k]=s[k]; }catch(e){} }
      }
      const eMap = new Map(this._snap.edges);
      for (let i=0;i<(phy.edges||[]).length;i++){
        const s = eMap.get(i);
        if (!s) continue;
        try{ phy.edges[i].flux = s.flux; }catch(e){}
      }
      try{ phy._t = this._snap.t || 0; }catch(e){}
      return "internal_snapshot_restored";
    },

    async _modeSelect(phy, pressC, damp){
      const c = this.cfg;
      let idx = 0;
      for (let b=0;b<Math.max(0,c.dreamBlocks-1);b++){
        const injId = c.injectorIds[idx % c.injectorIds.length];
        idx++;
        this._inject(phy, injId, c.injectAmount);
        for (let s=0;s<c.dreamBlockSteps;s++) phy.step(c.dt, pressC, damp);
      }
      this._inject(phy, c.wantId, c.injectAmount*(c.finalWriteMult||1));
      try{ if (typeof phy.computePressure === "function") phy.computePressure(pressC); }catch(e){}
    },

    _shuffle(arr){
      for (let i=arr.length-1;i>0;i--){
        const j = Math.floor(Math.random()*(i+1));
        [arr[i],arr[j]] = [arr[j],arr[i]];
      }
      return arr;
    },

    _fnv1a32(str){
      let h = 0x811c9dc5;
      for (let i=0;i<str.length;i++){
        h ^= str.charCodeAt(i);
        h = (h + ((h<<1)+(h<<4)+(h<<7)+(h<<8)+(h<<24))) >>> 0;
      }
      return ("00000000" + h.toString(16)).slice(-8);
    },

    _baselineFingerprint(phy){
      const ids = [114,136,89,79,126,7,82,90];
      const parts = [];
      for (const id of ids){
        const n = this._nodeById(phy, id);
        if (!n){ parts.push(`${id}:NA`); continue; }
        const vals = [
          n.x, n.y, n.vx, n.vy,
          (typeof n.fx === "number" ? n.fx : 0),
          (typeof n.fy === "number" ? n.fy : 0),
        ].map(v => (Number.isFinite(v) ? v.toFixed(6) : "NA"));
        parts.push(`${id}:${vals.join("|")}`);
      }
      const gb = ("globalBias" in phy) ? String(phy.globalBias) : "NA";
      const s = `gb=${gb}::` + parts.join("::");
      return this._fnv1a32(s);
    },

    _isFiniteNums(nums){
      for (const v of nums) if (typeof v !== "number" || !Number.isFinite(v)) return false;
      return true;
    },

    _argmaxCount(mapObj){
      let bestK="", bestV=-1;
      for (const [k,v] of mapObj.entries()){
        if (v>bestV){ bestV=v; bestK=k; }
      }
      return { key:bestK, count:bestV };
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

      const edgeIndex = this._buildEdgeIndex(phy);
      const i114_89 = edgeIndex.get("114->89");
      const i114_79 = edgeIndex.get("114->79");
      const i136_89 = edgeIndex.get("136->89");
      const i136_79 = edgeIndex.get("136->79");

      const baseB = g.baseAmpB * g.gain; // 88
      const baseD = g.baseAmpD * g.gain; // 126.5
      const ampD  = baseD * g.multD;

      const plan = [];
      for (const multBUsed of g.multBUsedList){
        for (let r=1;r<=g.repsPerCond;r++) plan.push({ multBUsed, rep:r });
      }
      if (g.shuffle) this._shuffle(plan);

      const startTag = this._iso(new Date());
      console.log(`[16av] START ${this.version} @ ${startTag} | pressC=${pressCUsed} | damp=${g.dampUsed} | runs=${plan.length}`);

      // fingerprint the current restored baseline (without changing it)
      await this._baselineRestore(phy);
      const baselineFp = this._baselineFingerprint(phy);
      console.log(`[16av] baselineFp=${baselineFp} (use this to compare basins across sessions)`);

      const summaryHeader = [
        "schema","baselineFp","runId","runIndex","repIndex","label",
        "pressCUsed","dampUsed","capLawHash",
        "multBUsed","ampB0","ampD","ratioBD",
        "peakAbs114_bus","peakAbs136_bus","ratioPeak_114over136","winner_peakBus",
        "t8_abs114_bus","t8_abs136_bus","winner_t8",
        "laneEdge","laneEdge_count","runQuality"
      ];
      const traceHeader = [
        "schema","baselineFp","runId","runIndex","repIndex","multBUsed","tick",
        "max1_from","max1_to","max1_absFlux",
        "flux_114_89","flux_114_79","flux_136_89","flux_136_79",
        "abs114_bus","abs136_bus"
      ];

      const summaryLines = [this._csvRow(summaryHeader)];
      const traceLines = [this._csvRow(traceHeader)];

      for (let runIndex=0; runIndex<plan.length; runIndex++){
        if (this._stop) break;

        const { multBUsed, rep } = plan[runIndex];

        const ampB0 = baseB * multBUsed;
        const ratioBD = ampB0 / ampD;
        const ampB_nudge = ampB0 * g.nudgeMult;

        const runId = `${this._iso(new Date())}_fp${baselineFp}_r${String(runIndex).padStart(6,"0")}_mB${multBUsed.toFixed(2)}_rep${rep}`;

        await this._baselineRestore(phy);
        const cap = await this._recomputeDerived(g.dt);

        await this._modeSelect(phy, pressCUsed, g.dampUsed);
        for (let s=0;s<g.settleTicks;s++) phy.step(g.dt, pressCUsed, g.dampUsed);

        let peakAbs114=0, peakAbs136=0;
        let t8_abs114="", t8_abs136="";
        const laneCounts = new Map();

        for (let tick=0; tick<g.totalTicks; tick++){
          if (this._stop) break;

          if (tick === g.injectTick136) this._inject(phy, 136, ampD);
          if (tick === g.injectTick114) this._inject(phy, 114, ampB0);
          if (tick === g.handshakeTick && ampB_nudge>0) this._inject(phy, 114, ampB_nudge);

          phy.step(g.dt, pressCUsed, g.dampUsed);

          const top2 = this._top2Edges(phy);
          const max1Pair = `${top2.best1.from}->${top2.best1.to}`;
          laneCounts.set(max1Pair, (laneCounts.get(max1Pair)||0)+1);

          const f114_89 = this._edgeFlux(phy, i114_89);
          const f114_79 = this._edgeFlux(phy, i114_79);
          const f136_89 = this._edgeFlux(phy, i136_89);
          const f136_79 = this._edgeFlux(phy, i136_79);

          const abs114 = Math.max(Math.abs(f114_89), Math.abs(f114_79));
          const abs136 = Math.max(Math.abs(f136_89), Math.abs(f136_79));

          if (g.abortOnNonFinite){
            const ok = this._isFiniteNums([top2.best1.af, f114_89,f114_79,f136_89,f136_79,abs114,abs136]);
            if (!ok) break;
          }

          if (abs114 > peakAbs114) peakAbs114 = abs114;
          if (abs136 > peakAbs136) peakAbs136 = abs136;

          if (tick === g.markerTick){ t8_abs114 = abs114; t8_abs136 = abs136; }

          traceLines.push(this._csvRow([
            this.version, baselineFp, runId, runIndex, rep, multBUsed, tick,
            top2.best1.from, top2.best1.to, top2.best1.af,
            f114_89, f114_79, f136_89, f136_79,
            abs114, abs136
          ]));
        }

        const winner_peakBus =
          (peakAbs114 > peakAbs136) ? "114" :
          (peakAbs136 > peakAbs114) ? "136" : "tie";

        const winner_t8 =
          (t8_abs114==="" || t8_abs136==="") ? "" :
          (t8_abs114 > t8_abs136) ? "114" :
          (t8_abs136 > t8_abs114) ? "136" : "tie";

        const ratioPeak = (peakAbs136>0) ? (peakAbs114/peakAbs136) : "";

        const lane = this._argmaxCount(laneCounts);
        const runQuality = (lane.count >= g.laneEdgeCountGoodMin) ? "good" : "unstable";

        summaryLines.push(this._csvRow([
          this.version, baselineFp, runId, runIndex, rep, g.label,
          pressCUsed, g.dampUsed, (cap.capLawHash ?? ""),
          multBUsed, ampB0, ampD, ratioBD,
          peakAbs114, peakAbs136, ratioPeak, winner_peakBus,
          t8_abs114, t8_abs136, winner_t8,
          lane.key, lane.count, runQuality
        ]));

        if ((runIndex+1) % 50 === 0) console.log(`[16av] progress ${(runIndex+1)}/${plan.length}`);
      }

      const endTag = this._iso(new Date());
      const baseName = `${this.version}_${startTag}_${endTag}_fp${baselineFp}`;

      this._unfreezeLiveLoop();

      this._download(`${baseName}_MASTER_summary.csv`, summaryLines.join(""));
      this._download(`${baseName}_MASTER_busTrace.csv`, traceLines.join(""));

      console.log(`[16av] DONE @ ${endTag}\n- ${baseName}_MASTER_summary.csv\n- ${baseName}_MASTER_busTrace.csv`);
      return { baseName, baselineFp, runsPlanned: plan.length, stopped: this._stop };
    }
  };

  window.solPhase311_16av_currentBaselineDownSweep_v1 = T;
  console.log(`✅ solPhase311_16av_currentBaselineDownSweep_v1 installed. Run: await solPhase311_16av_currentBaselineDownSweep_v1.run()`);
})();
