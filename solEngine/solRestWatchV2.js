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
    return { meanP, pMax, pMaxId };
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

  async function watch({
    seconds = 90,
    everyMs = 1000,
    filenamePrefix = "sol_rest_watch",
    includeIds = true,      // include rhoMaxId/pMaxId
    quiet = false           // if true, no per-sample console logs
  } = {}) {
    const r = getRoot();
    if (!r?.state?.physics) throw new Error("SOLDashboard not ready.");
    const physics = r.state.physics;

    const stamp = new Date().toISOString().replace(/[:.]/g, "-");
    const filename = `${filenamePrefix}_${seconds}s_${everyMs}ms_${stamp}.csv`;

    console.log(`[RestWatch] watching for ${seconds}s, sampling every ${everyMs}ms → ${filename}`);

    const t0 = performance.now();
    const rows = [];
    let prevRhoSum = null;

    while ((performance.now() - t0) < seconds * 1000) {
      const nodes = physics.nodes || [];
      const edges = physics.edges || [];

      const ent = entropyRhoNorm(nodes);
      const rs = rhoStats(nodes);
      const ps = pStats(nodes);
      const fs = fluxStats(edges);
      const dRhoSum = (prevRhoSum == null) ? 0 : (rs.rhoSum - prevRhoSum);
      prevRhoSum = rs.rhoSum;

      const tSec = (performance.now() - t0) / 1000;

      const row = {
        tSec: Number(tSec.toFixed(2)),
        entropy: ent,
        rhoSum: rs.rhoSum,
        dRhoSum,
        rhoConc: rs.rhoConc,
        meanP: ps.meanP,
        pMax: ps.pMax,
        maxAbsFlux: fs.maxAbsFlux,
        sumAbsFlux: fs.sumAbsFlux,
      };

      if (includeIds) {
        row.rhoMaxId = rs.rhoMaxId;
        row.pMaxId = ps.pMaxId;
      }

      rows.push(row);

      if (!quiet) {
        console.log(
          `[RestWatch t=${row.tSec}s] ent=${ent.toFixed(4)} rhoSum=${rs.rhoSum.toFixed(4)} ` +
          `rhoConc=${rs.rhoConc.toFixed(3)} maxAbsFlux=${fs.maxAbsFlux.toExponential(2)} ` +
          `meanP=${ps.meanP.toFixed(4)} pMax=${ps.pMax.toFixed(4)}`
        );
      }

      await sleep(everyMs);
    }

    downloadCSV(filename, rows);
    console.log(`[RestWatch] done. samples=${rows.length} → downloaded ${filename}`);

    // also keep in memory for quick inspection
    globalThis.__SOL_RESTWATCH_ROWS__ = rows;
    return rows;
  }

  globalThis.solRestWatchV2 = { watch };
  console.log("✅ solRestWatchV2 installed.");
  console.log("Run: await solRestWatchV2.watch({ seconds: 90, everyMs: 1000 })");
})();
