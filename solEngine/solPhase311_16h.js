/* Phase 3.11.16h — Paired-Pulse GapMap v1
   Goal:
     Measure short-term memory / facilitation:
     Does pulse #2 get stronger/weaker depending on inter-pulse gap?

   Design:
     - Two sequences:
         1) B->D  (114 then 136)
         2) D->B  (136 then 114)
     - gapTicks: [1,2,4,8,16,32]
     - repsPerCombo: 15
     - total runs = 2*6*15 = 180 (~20–30 min with everyMs=200)

   Key outputs:
     - MASTER_summary.csv (per-run onset/peak per bus, computed *after each bus's own injection*)
     - MASTER_busTrace.csv (per-tick bus flux + global telemetry)

   Run:
     solPhase311_16h.runPack()

   Stop:
     solPhase311_16h.stop()

   Notes:
     - UI-neutral (no camera/graph movement)
     - Baseline snapshot restore before each run
     - Mode select uses latch primitive (end dream on wantId)
*/
(() => {
  "use strict";

  const solPhase311_16h = {
    version: "3.11.16h_pairedPulseGapMap_v1",
    _stopFlag: false,
    stop() { this._stopFlag = true; console.warn("🛑 solPhase311_16h.stop(): stop flag set."); },

    cfg: {
      // ports: B=114, D=136 (we keep names consistent with earlier packs)
      B: 114,
      D: 136,

      sequences: [
        { name: "B_then_D", first: "B", second: "D" },
        { name: "D_then_B", first: "D", second: "B" },
      ],

      gapTicksList: [1, 2, 4, 8, 16, 32],
      repsPerCombo: 15,

      // how long we observe after the second pulse
      postTicks: 24,

      // Mode select (Order B from latch work)
      wantIds: [82],
      injectorIds: [90, 82],
      dreamBlocks: 15,
      dreamBlockSteps: 2,
      injectAmount: 120,
      finalWriteMult: 1,

      // Pulse amplitude for paired-pulse
      pulseAmount: 10,

      // Physics + metronome
      dt: 0.12,
      everyMs: 200,
      spinWaitMs: 1.5,

      // Bus edges (broadcast rails)
      busPairs: [
        { name: "bus114_89", from: 114, to: 89 },
        { name: "bus114_79", from: 114, to: 79 },
        { name: "bus136_89", from: 136, to: 89 },
        { name: "bus136_79", from: 136, to: 79 },
      ],
      busOnAbsFluxThresh: 1.0,

      // Optional overrides (leave null to read from UI)
      baseDamp: null,
      pressC: null,

      filenameBase: "sol_phase311_16h_pairedPulseGapMap_v1",
    },

    // ---------- utils ----------
    _sleep(ms) { return new Promise(r => setTimeout(r, ms)); },
    _isoForFile(d = new Date()) {
      const p = (n) => String(n).padStart(2, "0");
      return `${d.getUTCFullYear()}-${p(d.getUTCMonth()+1)}-${p(d.getUTCDate())}T${p(d.getUTCHours())}-${p(d.getUTCMinutes())}-${p(d.getUTCSeconds())}-${String(d.getUTCMilliseconds()).padStart(3,"0")}Z`;
    },
    _csvCell(v) {
      if (v === null || v === undefined) return "";
      const s = String(v);
      return /[",\n\r]/.test(s) ? `"${s.replace(/"/g,'""')}"` : s;
    },
    _csvRow(cols) { return cols.map(this._csvCell).join(",") + "\n"; },
    _downloadText(filename, text, mime = "text/csv") {
      const blob = new Blob([String(text)], { type: mime });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => { try { URL.revokeObjectURL(url); } catch(e){} }, 250);
    },
    _getApp() { return globalThis.SOLDashboard || window.SOLDashboard || null; },

    async _waitForPhysics({ timeoutMs = 15000, pollMs = 50 } = {}) {
      const t0 = Date.now();
      while (Date.now() - t0 < timeoutMs) {
        const app = this._getApp();
        const phy = app?.state?.physics || window.solver || null;
        if (phy?.nodes?.length && phy?.edges?.length) return phy;
        await this._sleep(pollMs);
      }
      throw new Error("solPhase311_16h: timed out waiting for physics.");
    },

    _readUiParams(app) {
      const pressC = (app?.dom?.pressureSlider)
        ? (parseFloat(String(app.dom.pressureSlider.value)) * (app.config.pressureSliderScale || 1))
        : 2;
      const damp = (app?.dom?.dampSlider)
        ? parseFloat(String(app.dom.dampSlider.value))
        : 5;
      return {
        pressC: Number.isFinite(pressC) ? pressC : 2,
        damp: Number.isFinite(damp) ? damp : 5
      };
    },

    _freezeLiveLoop() {
      const app = this._getApp();
      if (!app?.config) throw new Error("solPhase311_16h: App not ready.");
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

    _nodeByIdLoose(phy, id) {
      const direct = (phy?.nodeById?.get) ? phy.nodeById.get(id) : null;
      if (direct) return direct;
      const want = String(id);
      for (const n of (phy?.nodes || [])) if (n?.id != null && String(n.id) === want) return n;
      return null;
    },

    _snapshotState(phy) {
      const nodePairs = [];
      for (const n of (phy.nodes || [])) {
        if (!n || n.id == null) continue;
        const out = {};
        for (const k in n) {
          const v = n[k];
          if (typeof v === "number" && Number.isFinite(v)) out[k] = v;
          if (typeof v === "boolean" && (k === "isBattery" || k === "isConstellation")) out[k] = v;
        }
        nodePairs.push([String(n.id), out]);
      }

      const edgePairs = [];
      const edges = phy.edges || [];
      for (let i = 0; i < edges.length; i++) {
        const e = edges[i];
        if (!e) continue;
        const out = {};
        for (const k in e) {
          const v = e[k];
          if (typeof v === "number" && Number.isFinite(v)) out[k] = v;
          if ((k === "from" || k === "to") && (typeof v === "number" || typeof v === "string")) out[k] = v;
          if (k === "background" && typeof v === "boolean") out[k] = v;
        }
        edgePairs.push([i, out]);
      }
      return { nodePairs, edgePairs };
    },

    _restoreState(phy, snap) {
      if (!snap) return;
      const nodeMap = new Map(snap.nodePairs || []);
      for (const n of (phy.nodes || [])) {
        if (!n || n.id == null) continue;
        const s = nodeMap.get(String(n.id));
        if (!s) continue;
        for (const k in s) { try { n[k] = s[k]; } catch(e) {} }
      }

      const edges = phy.edges || [];
      const edgeMap = new Map(snap.edgePairs || []);
      for (let i = 0; i < edges.length; i++) {
        const e = edges[i];
        if (!e) continue;
        const s = edgeMap.get(i);
        if (!s) continue;
        for (const k in s) { try { e[k] = s[k]; } catch(e) {} }
      }
    },

    _injectById(phy, id, amount) {
      const n = this._nodeByIdLoose(phy, id);
      if (!n) throw new Error(`solPhase311_16h: injector node not found: ${id}`);
      const amt = Math.max(0, Number(amount) || 0);
      n.rho += amt;
      try {
        if (n.isConstellation && typeof phy.reinforceSemanticStar === "function") {
          const freqBoost = amt / 50.0;
          phy.reinforceSemanticStar(n, freqBoost);
        }
      } catch(e) {}
    },

    _pickBasin(phy) {
      const n82 = this._nodeByIdLoose(phy, 82);
      const n90 = this._nodeByIdLoose(phy, 90);
      const r82 = Number.isFinite(n82?.rho) ? n82.rho : 0;
      const r90 = Number.isFinite(n90?.rho) ? n90.rho : 0;
      return (r90 > r82) ? 90 : 82;
    },

    _buildEdgeIndexMap(phy) {
      const map = new Map();
      const edges = phy.edges || [];
      for (let i = 0; i < edges.length; i++) {
        const e = edges[i];
        if (!e || e.background) continue;
        const key = `${e.from}->${e.to}`;
        if (!map.has(key)) map.set(key, i);
      }
      return map;
    },

    _getEdgeFluxByIndex(phy, idx) {
      const e = (phy.edges || [])[idx];
      if (!e) return 0;
      return Number.isFinite(e.flux) ? e.flux : 0;
    },

    _computeGlobal(phy) {
      let meanAbsP = 0;
      const nodes = phy.nodes || [];
      for (const n of nodes) {
        const p = Number.isFinite(n?.p) ? n.p : 0;
        meanAbsP += Math.abs(p);
      }
      meanAbsP /= Math.max(1, nodes.length);

      let sumAbsFlux = 0;
      let maxAbsEdgeFlux = 0;
      let maxEdgeIndex = -1;
      let maxEdgeFrom = "";
      let maxEdgeTo = "";
      let maxEdgeFlux = 0;

      const edges = phy.edges || [];
      for (let i = 0; i < edges.length; i++) {
        const e = edges[i];
        if (!e || e.background) continue;
        const f = Number.isFinite(e.flux) ? e.flux : 0;
        const af = Math.abs(f);
        sumAbsFlux += af;
        if (af > maxAbsEdgeFlux) {
          maxAbsEdgeFlux = af;
          maxEdgeIndex = i;
          maxEdgeFrom = e.from;
          maxEdgeTo = e.to;
          maxEdgeFlux = f;
        }
      }

      const eps = 1e-9;
      const concentration = maxAbsEdgeFlux / (sumAbsFlux + eps);
      return { meanAbsP, sumAbsFlux, maxAbsEdgeFlux, maxEdgeIndex, maxEdgeFrom, maxEdgeTo, maxEdgeFlux, concentration };
    },

    async _selectMode(phy, wantId, pressC, baseDamp) {
      const c = this.cfg;
      let injIndex = 0;
      for (let b = 0; b < Math.max(0, c.dreamBlocks - 1); b++) {
        const injId = c.injectorIds[injIndex % c.injectorIds.length];
        injIndex++;
        this._injectById(phy, injId, c.injectAmount);
        for (let s = 0; s < c.dreamBlockSteps; s++) {
          if (this._stopFlag) return;
          phy.step(c.dt, pressC, baseDamp);
        }
      }
      this._injectById(phy, wantId, c.injectAmount * (c.finalWriteMult || 1));
      try { if (typeof phy.computePressure === "function") phy.computePressure(pressC); } catch(e) {}
    },

    _metronomeFactory({ everyMs, ticks, spinWaitMs, onTick }) {
      const self = this;
      return (async () => {
        const start = performance.now();
        const absLates = [];
        let missedTicks = 0;

        for (let i = 0; i < ticks; i++) {
          if (self._stopFlag) break;
          const target = start + i * everyMs;

          while (true) {
            const now = performance.now();
            const remain = target - now;
            if (remain <= 0) break;
            if (spinWaitMs > 0 && remain <= spinWaitMs) break;
            await self._sleep(Math.min(50, Math.max(0, remain - (spinWaitMs > 0 ? spinWaitMs : 0))));
          }
          if (spinWaitMs > 0) while (performance.now() < target) { /* spin */ }

          const now2 = performance.now();
          const lateByMs = now2 - target;
          const absLate = Math.abs(lateByMs);
          absLates.push(absLate);
          if (absLate > everyMs) missedTicks++;

          await onTick({ tick: i, tMs: now2 - start, lateByMs });
        }

        absLates.sort((a,b)=>a-b);
        const n = Math.max(1, absLates.length);
        const p95 = absLates[Math.floor(0.95 * (n - 1))] ?? 0;
        const avg = absLates.reduce((a,b)=>a+b,0) / n;
        const max = absLates[n - 1] ?? 0;

        return { lateAbsAvg: avg, lateAbsP95: p95, lateAbsMax: max, missedTicks };
      })();
    },

    async _runOne({ runIndex, repIndex, wantId, pressC, baseDamp, seqName, firstKey, secondKey, gapTicks }) {
      const phy = await this._waitForPhysics();
      this._restoreState(phy, this._baselineSnap);

      await this._selectMode(phy, wantId, pressC, baseDamp);

      const edgeMap = this._buildEdgeIndexMap(phy);
      const bus = this.cfg.busPairs.map(b => ({
        ...b,
        idx: edgeMap.has(`${b.from}->${b.to}`) ? edgeMap.get(`${b.from}->${b.to}`) : -1
      }));

      const idFor = (k) => (k === "B" ? this.cfg.B : this.cfg.D);

      const injTick_first = 0;
      const injTick_second = gapTicks;

      const injTick_114 = (firstKey === "B") ? injTick_first : (secondKey === "B" ? injTick_second : null);
      const injTick_136 = (firstKey === "D") ? injTick_first : (secondKey === "D" ? injTick_second : null);

      const totalTicks = gapTicks + this.cfg.postTicks + 1;
      const windowMs = totalTicks * this.cfg.everyMs;

      const runId =
        `${this._isoForFile()}_r${String(runIndex).padStart(5,"0")}` +
        `_rep${repIndex}_want${wantId}_${seqName}_gap${gapTicks}`;

      const visStart = document.visibilityState;
      let wasHidden = false;
      const onVis = () => { if (document.hidden) wasHidden = true; };
      document.addEventListener("visibilitychange", onVis, { passive: true });

      const thresh = this.cfg.busOnAbsFluxThresh;

      // per-bus post-injection tracking (to avoid “pre-activation” confusion)
      const bus114 = {
        injTick: injTick_114,
        onsetTick: null, onsetMs: null,
        peakAbs: -1, peakTick: null, peakMs: null, peakF89: 0, peakF79: 0
      };
      const bus136 = {
        injTick: injTick_136,
        onsetTick: null, onsetMs: null,
        peakAbs: -1, peakTick: null, peakMs: null, peakF89: 0, peakF79: 0
      };

      let peakSumAbsFlux = -1, peakSumAtTick = 0, peakSumAtMs = 0, peakSumMeanAbsP = 0;
      let peakMaxAbsEdgeFlux = -1, peakEdgeIndex = -1, peakEdgeFrom = "", peakEdgeTo = "", peakEdgeFlux = 0, peakConcentration = 0;

      const traceRows = [];

      const met = await this._metronomeFactory({
        everyMs: this.cfg.everyMs,
        ticks: totalTicks,
        spinWaitMs: this.cfg.spinWaitMs,
        onTick: async ({ tick, tMs, lateByMs }) => {
          // pulse #1 at tick 0
          if (tick === injTick_first) {
            this._injectById(phy, idFor(firstKey), this.cfg.pulseAmount);
          }
          // pulse #2 at tick = gapTicks
          if (tick === injTick_second) {
            this._injectById(phy, idFor(secondKey), this.cfg.pulseAmount);
          }

          phy.step(this.cfg.dt, pressC, baseDamp);

          const basin = this._pickBasin(phy);
          const g = this._computeGlobal(phy);

          if (g.sumAbsFlux > peakSumAbsFlux) {
            peakSumAbsFlux = g.sumAbsFlux;
            peakSumAtTick = tick;
            peakSumAtMs = tMs;
            peakSumMeanAbsP = g.meanAbsP;
          }
          if (g.maxAbsEdgeFlux > peakMaxAbsEdgeFlux) {
            peakMaxAbsEdgeFlux = g.maxAbsEdgeFlux;
            peakEdgeIndex = g.maxEdgeIndex;
            peakEdgeFrom = g.maxEdgeFrom;
            peakEdgeTo = g.maxEdgeTo;
            peakEdgeFlux = g.maxEdgeFlux;
            peakConcentration = g.concentration;
          }

          const f114_89 = (bus[0].idx >= 0) ? this._getEdgeFluxByIndex(phy, bus[0].idx) : 0;
          const f114_79 = (bus[1].idx >= 0) ? this._getEdgeFluxByIndex(phy, bus[1].idx) : 0;
          const f136_89 = (bus[2].idx >= 0) ? this._getEdgeFluxByIndex(phy, bus[2].idx) : 0;
          const f136_79 = (bus[3].idx >= 0) ? this._getEdgeFluxByIndex(phy, bus[3].idx) : 0;

          const a114 = Math.max(Math.abs(f114_89), Math.abs(f114_79));
          const a136 = Math.max(Math.abs(f136_89), Math.abs(f136_79));

          // post-injection onset + peak (114)
          if (bus114.injTick != null && tick >= bus114.injTick) {
            if (bus114.onsetTick == null && a114 >= thresh) {
              bus114.onsetTick = tick;
              bus114.onsetMs = Math.round(tMs);
            }
            if (a114 > bus114.peakAbs) {
              bus114.peakAbs = a114;
              bus114.peakTick = tick;
              bus114.peakMs = Math.round(tMs);
              bus114.peakF89 = f114_89;
              bus114.peakF79 = f114_79;
            }
          }

          // post-injection onset + peak (136)
          if (bus136.injTick != null && tick >= bus136.injTick) {
            if (bus136.onsetTick == null && a136 >= thresh) {
              bus136.onsetTick = tick;
              bus136.onsetMs = Math.round(tMs);
            }
            if (a136 > bus136.peakAbs) {
              bus136.peakAbs = a136;
              bus136.peakTick = tick;
              bus136.peakMs = Math.round(tMs);
              bus136.peakF89 = f136_89;
              bus136.peakF79 = f136_79;
            }
          }

          traceRows.push(this._csvRow([
            this.version,
            runId,
            runIndex,
            repIndex,
            wantId,
            seqName,
            firstKey,
            secondKey,
            gapTicks,
            pressC,
            baseDamp,
            tick,
            Math.round(tMs),
            lateByMs.toFixed(3),
            basin,
            g.sumAbsFlux.toFixed(6),
            g.meanAbsP.toFixed(6),
            g.maxAbsEdgeFlux.toFixed(6),
            g.maxEdgeIndex,
            g.maxEdgeFrom,
            g.maxEdgeTo,
            g.maxEdgeFlux.toFixed(6),
            g.concentration.toFixed(6),
            f114_89.toFixed(6),
            f114_79.toFixed(6),
            f136_89.toFixed(6),
            f136_79.toFixed(6)
          ]));
        }
      });

      document.removeEventListener("visibilitychange", onVis);

      // delays in ticks/ms relative to each bus injection
      const onDelay114_t = (bus114.onsetTick == null) ? "" : (bus114.onsetTick - bus114.injTick);
      const onDelay136_t = (bus136.onsetTick == null) ? "" : (bus136.onsetTick - bus136.injTick);

      const pkDelay114_t = (bus114.peakTick == null) ? "" : (bus114.peakTick - bus114.injTick);
      const pkDelay136_t = (bus136.peakTick == null) ? "" : (bus136.peakTick - bus136.injTick);

      const injMs_114 = (bus114.injTick == null) ? "" : (bus114.injTick * this.cfg.everyMs);
      const injMs_136 = (bus136.injTick == null) ? "" : (bus136.injTick * this.cfg.everyMs);

      const onDelay114_ms = (bus114.onsetMs == null || injMs_114 === "") ? "" : (bus114.onsetMs - injMs_114);
      const onDelay136_ms = (bus136.onsetMs == null || injMs_136 === "") ? "" : (bus136.onsetMs - injMs_136);

      const pkDelay114_ms = (bus114.peakMs == null || injMs_114 === "") ? "" : (bus114.peakMs - injMs_114);
      const pkDelay136_ms = (bus136.peakMs == null || injMs_136 === "") ? "" : (bus136.peakMs - injMs_136);

      // also expose “second pulse bus” directly for easy facilitation plots later
      const secondIsB = (secondKey === "B");
      const secondBusPeakAbs = secondIsB ? bus114.peakAbs : bus136.peakAbs;
      const secondBusPeakDelayTicks = secondIsB ? pkDelay114_t : pkDelay136_t;

      const summary = {
        schema: this.version,
        runId,
        runIndex,
        repIndex,
        wantId,
        seqName,
        firstKey,
        secondKey,
        gapTicks,
        totalTicks,
        windowMs,
        dt: this.cfg.dt,
        everyMs: this.cfg.everyMs,
        pressC,
        baseDamp,

        injTick_first,
        injTick_second,
        injTick_114,
        injTick_136,

        // 114
        onset114_tick: bus114.onsetTick ?? "",
        onset114_ms: bus114.onsetMs ?? "",
        onsetDelay114_ticks: onDelay114_t,
        onsetDelay114_ms: onDelay114_ms,
        peak114_tick: bus114.peakTick ?? "",
        peakDelay114_ticks: pkDelay114_t,
        peakDelay114_ms: pkDelay114_ms,
        peak114_abs: bus114.peakAbs,
        peak114_flux_89: bus114.peakF89,
        peak114_flux_79: bus114.peakF79,

        // 136
        onset136_tick: bus136.onsetTick ?? "",
        onset136_ms: bus136.onsetMs ?? "",
        onsetDelay136_ticks: onDelay136_t,
        onsetDelay136_ms: onDelay136_ms,
        peak136_tick: bus136.peakTick ?? "",
        peakDelay136_ticks: pkDelay136_t,
        peakDelay136_ms: pkDelay136_ms,
        peak136_abs: bus136.peakAbs,
        peak136_flux_89: bus136.peakF89,
        peak136_flux_79: bus136.peakF79,

        // Second pulse readout (the money shot)
        secondBusPeakAbs,
        secondBusPeakDelayTicks,

        // global
        peakSumAbsFlux,
        peakSumAtTick,
        peakSumAtMs: Math.round(peakSumAtMs),
        peakSumMeanAbsP,
        peakMaxAbsEdgeFlux,
        peakEdgeIndex,
        peakEdgeFrom,
        peakEdgeTo,
        peakEdgeFlux,
        peakConcentration,

        // timing
        visibilityStateStart: visStart,
        wasHidden,
        lateAbsAvgMs: met.lateAbsAvg,
        lateAbsP95Ms: met.lateAbsP95,
        lateAbsMaxMs: met.lateAbsMax,
        missedTicks: met.missedTicks
      };

      return { summary, traceRows };
    },

    async runPack(userCfg = {}) {
      this._stopFlag = false;
      if (userCfg && typeof userCfg === "object") this.cfg = { ...this.cfg, ...userCfg };

      const app = this._getApp();
      if (!app) throw new Error("solPhase311_16h: SOLDashboard not found.");

      const phy = await this._waitForPhysics();
      this._freezeLiveLoop();

      this._baselineSnap = this._snapshotState(phy);

      const ui = this._readUiParams(app);
      const pressC = (this.cfg.pressC == null) ? ui.pressC : this.cfg.pressC;
      const baseDamp = (this.cfg.baseDamp == null) ? ui.damp : this.cfg.baseDamp;

      const plan = [];
      let idx = 0;
      for (const wantId of this.cfg.wantIds) {
        for (const seq of this.cfg.sequences) {
          for (const gapTicks of this.cfg.gapTicksList) {
            for (let rep = 1; rep <= this.cfg.repsPerCombo; rep++) {
              plan.push({
                runIndex: idx++,
                repIndex: rep,
                wantId,
                seqName: seq.name,
                firstKey: seq.first,
                secondKey: seq.second,
                gapTicks
              });
            }
          }
        }
      }

      const startIso = this._isoForFile(new Date());
      const baseName = `${this.cfg.filenameBase}_${startIso}`;

      console.log(`🧪 Phase 3.11.16h starting (${this.version})`);
      console.log(`wantIds=${JSON.stringify(this.cfg.wantIds)} | sequences=${this.cfg.sequences.map(s=>s.name).join(", ")}`);
      console.log(`gapTicks=${JSON.stringify(this.cfg.gapTicksList)} | reps=${this.cfg.repsPerCombo} | runs=${plan.length}`);
      console.log(`UI params: pressC≈${pressC}, baseDamp≈${baseDamp}`);

      // probe for headers
      const probe = await this._runOne({
        runIndex: 0, repIndex: 1, wantId: this.cfg.wantIds[0],
        pressC, baseDamp,
        seqName: this.cfg.sequences[0].name,
        firstKey: this.cfg.sequences[0].first,
        secondKey: this.cfg.sequences[0].second,
        gapTicks: this.cfg.gapTicksList[0]
      });
      this._restoreState(phy, this._baselineSnap);

      const summaryHeader = Object.keys(probe.summary);
      const traceHeader = [
        "schema","runId","runIndex","repIndex","wantId",
        "seqName","firstKey","secondKey","gapTicks",
        "pressC","baseDamp",
        "tick","tMs","lateByMs","basin",
        "sumAbsFlux","meanAbsP",
        "maxAbsEdgeFlux","maxEdgeIndex","maxEdgeFrom","maxEdgeTo","maxEdgeFlux","concentration",
        "flux_114_89","flux_114_79","flux_136_89","flux_136_79"
      ];

      const summaryLines = [ this._csvRow(summaryHeader) ];
      const traceLines = [ this._csvRow(traceHeader) ];

      try {
        for (let i = 0; i < plan.length; i++) {
          if (this._stopFlag) break;
          if (i % 18 === 0) console.log(`Progress: ${i}/${plan.length} | hidden=${document.hidden}`);

          const r = plan[i];
          const out = await this._runOne({
            runIndex: r.runIndex,
            repIndex: r.repIndex,
            wantId: r.wantId,
            pressC,
            baseDamp,
            seqName: r.seqName,
            firstKey: r.firstKey,
            secondKey: r.secondKey,
            gapTicks: r.gapTicks
          });

          const s = out.summary;
          summaryLines.push(this._csvRow(summaryHeader.map(k => (k in s ? s[k] : ""))));
          for (const row of out.traceRows) traceLines.push(row);
        }
      } finally {
        this._unfreezeLiveLoop();
      }

      const endIso = this._isoForFile(new Date());
      const base2 = `${baseName}_${endIso}`;

      this._downloadText(`${base2}_MASTER_summary.csv`, summaryLines.join(""));
      this._downloadText(`${base2}_MASTER_busTrace.csv`, traceLines.join(""));

      console.log("✅ Phase 3.11.16h complete:", base2);
      return { baseName: base2, runsPlanned: plan.length, stopped: this._stopFlag };
    }
  };

  window.solPhase311_16h = solPhase311_16h;
  console.log(`✅ solPhase311_16h installed (${solPhase311_16h.version}). Run: solPhase311_16h.runPack()`);

})();
