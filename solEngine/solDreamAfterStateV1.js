(() => {
  const sleep = (ms) => new Promise(r => setTimeout(r, ms));
  const safe = (x) => (Number.isFinite(x) ? x : 0);

  function getRoot() {
    return globalThis.SOLDashboard ?? globalThis.App ?? globalThis.app ?? null;
  }

  function entropyRhoNorm(nodes) {
    let sumRho = 0;
    for (const n of nodes) sumRho += safe(n?.rho);
    if (sumRho <= 0) return 0;

    let H = 0;
    for (const n of nodes) {
      const p = safe(n?.rho) / sumRho;
      if (p > 0) H -= p * Math.log(p);
    }
    const Hmax = Math.log(Math.max(1, nodes.length));
    return Hmax > 0 ? (H / Hmax) : 0;
  }

  function rhoStats(nodes) {
    let rhoSum = 0, rhoMax = -Infinity, rhoMaxId = "";
    for (const n of nodes) {
      const r = safe(n?.rho);
      rhoSum += r;
      if (r > rhoMax) { rhoMax = r; rhoMaxId = String(n?.id ?? ""); }
    }
    const rhoConc = rhoSum > 0 ? (rhoMax / rhoSum) : 0;
    return { rhoSum, rhoMax, rhoMaxId, rhoConc };
  }

  function pStats(nodes) {
    let pSum = 0, pMax = -Infinity, pMaxId = "";
    const ps = [];
    for (const n of nodes) {
      const p = safe(n?.p);
      ps.push(p);
      pSum += p;
      if (p > pMax) { pMax = p; pMaxId = String(n?.id ?? ""); }
    }
    const meanP = ps.length ? pSum / ps.length : 0;
    let varP = 0;
    for (const p of ps) varP += (p - meanP) * (p - meanP);
    varP = ps.length ? varP / ps.length : 0;
    return { meanP, varP, pMax, pMaxId };
  }

  function psiStats(nodes, topK = 5) {
    // use abs(psi) for concentration
    const arr = [];
    let sumAbs = 0;
    let maxAbs = -Infinity;
    let psiMaxId = "";
    for (const n of nodes) {
      const v = Math.abs(safe(n?.psi));
      arr.push([v, n?.id]);
      sumAbs += v;
      if (v > maxAbs) { maxAbs = v; psiMaxId = String(n?.id ?? ""); }
    }
    arr.sort((a,b) => b[0] - a[0]);
    const topSum = arr.slice(0, topK).reduce((s,[v]) => s+v, 0);
    const topFrac = sumAbs > 0 ? (topSum / sumAbs) : 0;
    const psiTopIds = arr.slice(0, topK).map(x => x[1]).join("|");
    // also mean abs
    const meanAbs = arr.length ? (sumAbs / arr.length) : 0;
    return { psiAbsSum: sumAbs, psiAbsMean: meanAbs, psiAbsMax: maxAbs, psiMaxId, psiTopFrac: topFrac, psiTopIds };
  }

  function fluxStats(edges) {
    let sumAbs = 0, maxAbs = 0;
    for (const e of edges) {
      const f = Math.abs(safe(e?.flux));
      sumAbs += f;
      if (f > maxAbs) maxAbs = f;
    }
    return { sumAbsFlux: sumAbs, maxAbsFlux: maxAbs };
  }

  function nodeById(physics, id) {
    const m = physics?.nodeById?.get?.(id);
    if (m) return m;
    const nodes = physics?.nodes || [];
    return nodes.find(n => n?.id === id) || null;
  }

  function injectRho(physics, id, amount) {
    const n = nodeById(physics, id);
    if (!n) return false;
    if (typeof n.rho !== "number") return false;
    n.rho += amount;
    return true;
  }

  function downloadCSV(filename, rows) {
    if (!rows.length) return;
    const cols = Object.keys(rows[0]);
    const esc = (v) => {
      const s = String(v ?? "");
      return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
    };
    const lines = [cols.join(",")].concat(rows.map(r => cols.map(c => esc(r[c])).join(",")));
    const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 5000);
  }

  async function run({
    // baseline
    restoreBaseline = true,

    // physics stepping (used for BOTH dream + afterstate watch so it works even if live loop is paused)
    dt = 0.12,
    damping = 4,
    pressC = 20,

    // dream phase (wall-clock)
    dreamMs = 4000,
    dreamTickMs = 100,       // how often we "fire an injector"
    dreamStepsPerTick = 5,   // how many physics steps between injections
    dreamInjectAmount = 25,  // rho mass per injector fire (tune if too strong/weak)

    // which injectors (node ids)
    injectorIds = [64, 82, 79, 90],

    // afterstate watch phase
    restSeconds = 120,
    restEveryMs = 200,
    restStepsPerSample = 5,

    // telemetry detail
    psiTopK = 5,

    // output
    filenamePrefix = "sol_dream_afterstate"
  } = {}) {
    const r = getRoot();
    if (!r?.state?.physics?.step) throw new Error("SOLDashboard physics not ready.");
    const physics = r.state.physics;

    if (restoreBaseline && globalThis.SOLBaseline?.restore) {
      await globalThis.SOLBaseline.restore();
    }

    const stamp = new Date().toISOString().replace(/[:.]/g, "-");
    const filename = `${filenamePrefix}_dt${dt}_d${damping}_${stamp}.csv`;

    const rows = [];
    let simStep = 0;

    const sampleRow = (phase, tSec) => {
      const nodes = physics.nodes || [];
      const edges = physics.edges || [];
      const ent = entropyRhoNorm(nodes);
      const rs = rhoStats(nodes);
      const ps = pStats(nodes);
      const qs = psiStats(nodes, psiTopK);
      const fs = fluxStats(edges);

      rows.push({
        phase,
        tSec,
        simStep,
        dt,
        damping,
        pressC,

        entropy: ent,
        rhoSum: rs.rhoSum,
        rhoConc: rs.rhoConc,
        rhoMaxId: rs.rhoMaxId,

        meanP: ps.meanP,
        varP: ps.varP,
        pMax: ps.pMax,
        pMaxId: ps.pMaxId,

        psiAbsSum: qs.psiAbsSum,
        psiAbsMean: qs.psiAbsMean,
        psiAbsMax: qs.psiAbsMax,
        psiMaxId: qs.psiMaxId,
        psiTopFrac: qs.psiTopFrac,
        psiTopIds: qs.psiTopIds,

        sumAbsFlux: fs.sumAbsFlux,
        maxAbsFlux: fs.maxAbsFlux
      });
    };

    console.log(`[DreamAfterstate] DREAM start: ${dreamMs}ms, injectors=${injectorIds.join(",")}, inject=${dreamInjectAmount} rho/fire`);
    const t0 = performance.now();
    let fireIx = 0;

    // Dream loop
    while ((performance.now() - t0) < dreamMs) {
      const nowSec = (performance.now() - t0) / 1000;

      const id = injectorIds[fireIx % injectorIds.length];
      const ok = injectRho(physics, id, dreamInjectAmount);
      if (!ok) console.warn(`[DreamAfterstate] inject failed for node ${id} (no node or no numeric rho)`);

      // step a bit so we actually create flux/pressure evolution
      for (let k = 0; k < dreamStepsPerTick; k++) {
        physics.step(dt, pressC, damping);
        simStep++;
      }

      sampleRow("dream", Number(nowSec.toFixed(3)));

      if (fireIx % Math.max(1, Math.floor(1000 / dreamTickMs)) === 0) {
        console.log(`[DreamAfterstate] t=${nowSec.toFixed(2)}s fired=${fireIx} lastId=${id} ok=${ok}`);
      }

      fireIx++;
      await sleep(dreamTickMs);
    }

    console.log(`[DreamAfterstate] DREAM end. Starting AFTERSTATE watch: ${restSeconds}s @ ${restEveryMs}ms`);
    const t1 = performance.now();

    // Afterstate watch (still stepping deterministically)
    while ((performance.now() - t1) < restSeconds * 1000) {
      for (let k = 0; k < restStepsPerSample; k++) {
        physics.step(dt, pressC, damping);
        simStep++;
      }

      const nowSec = (performance.now() - t1) / 1000;
      sampleRow("rest", Number(nowSec.toFixed(2)));

      const last = rows[rows.length - 1];
      console.log(
        `[Afterstate t=${last.tSec}s] ent=${last.entropy.toFixed(4)} rhoSum=${last.rhoSum.toExponential(2)} ` +
        `rhoConc=${last.rhoConc.toFixed(3)} maxAbsFlux=${last.maxAbsFlux.toExponential(2)} meanP=${last.meanP.toFixed(4)}`
      );

      await sleep(restEveryMs);
    }

    downloadCSV(filename, rows);
    console.log(`[DreamAfterstate] done. rows=${rows.length} → downloaded ${filename}`);
    globalThis.__SOL_DREAM_AFTERSTATE_ROWS__ = rows;
    return rows;
  }

  globalThis.solDreamAfterstateV1 = { run };
  console.log("✅ solDreamAfterstateV1 installed.");
  console.log("Run: await solDreamAfterstateV1.run({ dreamMs: 4000, restSeconds: 120, dt: 0.12, damping: 4, pressC: 20, injectorIds:[64,82,79,90], dreamInjectAmount:25 })");
})();
