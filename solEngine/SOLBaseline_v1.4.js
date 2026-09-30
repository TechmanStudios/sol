/* SOLBaseline Unified v1.4
   Patch goals:
     - Make baseline restore actually baseline under Phase-Gated + Semantic-Star physics.
     - Extend snapshot/restore to include:
         * solver time: physics._t (phase gating depends on it)
         * semantic/star mutable fields used by reinforce/decay/promotion:
             - lastInteractionTime
             - isConstellation, protoStar, isStellar, isSingularity
             - tension (safe)
     - Backward compatible with v1.0–v1.3 baseline blobs.

   Usage:
     - Load this script once in the dashboard console.
     - It auto-runs ensure({force:false}) on install.
     - If you want to recapture with the new fields: await SOLBaseline.ensure({force:true})
     - Restore anytime: await SOLBaseline.restore()
*/

(async () => {
  const KEY = "SOL_BASELINE_UNIFIED";

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  function nowTag() {
    const d = new Date();
    const p2 = (n) => String(n).padStart(2, "0");
    const p3 = (n) => String(n).padStart(3, "0");
    return (
      `${d.getUTCFullYear()}-${p2(d.getUTCMonth() + 1)}-${p2(d.getUTCDate())}` +
      `T${p2(d.getUTCHours())}-${p2(d.getUTCMinutes())}-${p2(d.getUTCSeconds())}-${p3(d.getUTCMilliseconds())}Z`
    );
  }

  function downloadText(filename, text) {
    const blob = new Blob([text], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => {
      try { URL.revokeObjectURL(url); } catch (e) {}
    }, 250);
  }

  function getPhysicsMaybe() {
    return (
      globalThis.solver ||
      globalThis.SOLDashboard?.state?.physics?.network ||
      globalThis.SOLDashboard?.state?.physics ||
      globalThis.App?.state?.physics?.network ||
      globalThis.App?.state?.physics ||
      globalThis.app?.state?.physics?.network ||
      globalThis.app?.state?.physics ||
      null
    );
  }

  async function waitForPhysics({ timeoutMs = 20000, pollMs = 50 } = {}) {
    const t0 = performance.now();
    while (performance.now() - t0 < timeoutMs) {
      const phy = getPhysicsMaybe();
      if (phy && phy.nodes && phy.edges && typeof phy.step === "function") return phy;
      await sleep(pollMs);
    }
    throw new Error("SOLBaseline Unified: physics not ready. Let dashboard finish initializing, then rerun.");
  }

  function snapshotState(physics) {
    const nodes = [];
    for (const n of physics.nodes || []) {
      if (!n || n.id == null) continue;
      nodes.push({
        id: String(n.id),

        // Core fields
        rho: n.rho,
        p: n.p,
        psi: n.psi,
        psi_bias: n.psi_bias,
        semanticMass: n.semanticMass,
        semanticMass0: n.semanticMass0,

        // Battery
        isBattery: !!n.isBattery,
        b_q: n.b_q,
        b_charge: n.b_charge,
        b_state: n.b_state,

        // Semantic/star mutable state (baseline v1.3 missed these)
        lastInteractionTime: (typeof n.lastInteractionTime === "number" && Number.isFinite(n.lastInteractionTime)) ? n.lastInteractionTime : 0,
        isConstellation: !!n.isConstellation,
        protoStar: !!n.protoStar,
        isStellar: !!n.isStellar,
        isSingularity: !!n.isSingularity,
        tension: (typeof n.tension === "number" && Number.isFinite(n.tension)) ? n.tension : 0,
      });
    }

    const edgeFlux = (physics.edges || []).map((e) =>
      e && Number.isFinite(e.flux) ? e.flux : 0
    );

    const t = (typeof physics._t === "number" && Number.isFinite(physics._t)) ? physics._t : 0;

    return { nodes, edgeFlux, t };
  }

  function nodesArrayToNodeSnap(nodesArr) {
    const nodeSnap = {};
    for (const s of nodesArr || []) {
      if (!s || s.id == null) continue;
      nodeSnap[String(s.id)] = {
        rho: s.rho,
        p: s.p,
        psi: s.psi,
        psi_bias: s.psi_bias,
        semanticMass: s.semanticMass,
        semanticMass0: s.semanticMass0,
        isBattery: !!s.isBattery,
        b_q: s.b_q,
        b_charge: s.b_charge,
        b_state: s.b_state,

        lastInteractionTime: (typeof s.lastInteractionTime === "number" && Number.isFinite(s.lastInteractionTime)) ? s.lastInteractionTime : 0,
        isConstellation: !!s.isConstellation,
        protoStar: !!s.protoStar,
        isStellar: !!s.isStellar,
        isSingularity: !!s.isSingularity,
        tension: (typeof s.tension === "number" && Number.isFinite(s.tension)) ? s.tension : 0,
      };
    }
    return nodeSnap;
  }

  function normalizeFromStored(stored) {
    if (!stored || typeof stored !== "object") return null;

    // Case A: v1 blob with stored.snap
    if (stored.snap && typeof stored.snap === "object") {
      const s = stored.snap;

      // Preferred (nodeSnap)
      if (s.nodeSnap && typeof s.nodeSnap === "object") {
        return {
          nodeSnap: s.nodeSnap,
          edgeFlux: Array.isArray(s.edgeFlux) ? s.edgeFlux : [],
          t: (typeof s.t === "number" && Number.isFinite(s.t)) ? s.t : ((typeof stored.t === "number" && Number.isFinite(stored.t)) ? stored.t : null),
        };
      }

      // Legacy (nodes array)
      if (Array.isArray(s.nodes)) {
        return {
          nodeSnap: nodesArrayToNodeSnap(s.nodes),
          edgeFlux: Array.isArray(s.edgeFlux) ? s.edgeFlux : [],
          t: (typeof s.t === "number" && Number.isFinite(s.t)) ? s.t : ((typeof stored.t === "number" && Number.isFinite(stored.t)) ? stored.t : null),
          _legacyNodes: s.nodes,
        };
      }
    }

    // Case B: already in new top-level snap
    if (stored.nodeSnap && typeof stored.nodeSnap === "object") {
      return {
        nodeSnap: stored.nodeSnap,
        edgeFlux: Array.isArray(stored.edgeFlux) ? stored.edgeFlux : [],
        t: (typeof stored.t === "number" && Number.isFinite(stored.t)) ? stored.t : null,
      };
    }

    // Case C: raw legacy snap at top level
    if (Array.isArray(stored.nodes)) {
      return {
        nodeSnap: nodesArrayToNodeSnap(stored.nodes),
        edgeFlux: Array.isArray(stored.edgeFlux) ? stored.edgeFlux : [],
        t: (typeof stored.t === "number" && Number.isFinite(stored.t)) ? stored.t : null,
      };
    }

    return null;
  }

  function restoreState(physics, normalizedSnap) {
    if (!normalizedSnap?.nodeSnap) {
      throw new Error("SOLBaseline Unified: invalid baseline (missing nodeSnap after normalize).");
    }

    const byId = normalizedSnap.nodeSnap;

    for (const n of physics.nodes || []) {
      if (!n || n.id == null) continue;
      const s = byId[String(n.id)];
      if (!s) continue;

      // Core
      n.rho = s.rho;
      n.p = s.p;
      n.psi = s.psi;
      n.psi_bias = s.psi_bias;
      n.semanticMass = s.semanticMass;
      n.semanticMass0 = s.semanticMass0;

      // Battery
      if (n.isBattery) {
        n.b_q = s.b_q;
        n.b_charge = s.b_charge;
        n.b_state = s.b_state;
      }

      // Semantic/star state
      n.lastInteractionTime = (typeof s.lastInteractionTime === "number" && Number.isFinite(s.lastInteractionTime)) ? s.lastInteractionTime : 0;
      n.isConstellation = !!s.isConstellation;
      n.protoStar = !!s.protoStar;
      n.isStellar = !!s.isStellar;
      n.isSingularity = !!s.isSingularity;
      if (typeof s.tension === "number" && Number.isFinite(s.tension)) n.tension = s.tension;
      else if (typeof n.tension === "number") n.tension = 0;
    }

    // Edge flux
    const edges = physics.edges || [];
    const ef = Array.isArray(normalizedSnap.edgeFlux) ? normalizedSnap.edgeFlux : [];
    for (let i = 0; i < edges.length; i++) {
      const e = edges[i];
      if (!e) continue;
      e.flux = Number.isFinite(ef[i]) ? ef[i] : 0;
    }

    // Solver time (phase-gating)
    if (normalizedSnap.t != null) {
      try { physics._t = normalizedSnap.t; } catch (e) {}
    }
  }

  function readBlob() {
    const raw = localStorage.getItem(KEY);
    return raw ? JSON.parse(raw) : null;
  }

  function writeBlob(blob) {
    localStorage.setItem(KEY, JSON.stringify(blob));
  }

  async function ensure({ force = false, exportJson = false } = {}) {
    const physics = await waitForPhysics();
    let blob = readBlob();

    if (!blob || force) {
      const snapLegacy = snapshotState(physics);
      const nodeSnap = nodesArrayToNodeSnap(snapLegacy.nodes);

      blob = {
        v: 1.4,
        createdAt: new Date().toISOString(),
        nodeCount: (physics.nodes || []).length,
        edgeCount: (physics.edges || []).length,

        // Legacy-compatible
        snap: snapLegacy,

        // Preferred format
        nodeSnap,
        edgeFlux: snapLegacy.edgeFlux,
        t: snapLegacy.t,
      };

      writeBlob(blob);

      console.log(`🧊 Baseline CAPTURED → localStorage["${KEY}"]`, {
        createdAt: blob.createdAt,
        nodeCount: blob.nodeCount,
        edgeCount: blob.edgeCount,
        v: blob.v,
      });

      if (exportJson) {
        downloadText(`sol_baseline_snap_${nowTag()}.json`, JSON.stringify(blob));
        console.log("📦 Baseline JSON downloaded.");
      }
    } else {
      console.log(`🧊 Baseline FOUND → localStorage["${KEY}"]`, {
        createdAt: blob.createdAt,
        nodeCount: blob.nodeCount,
        edgeCount: blob.edgeCount,
        v: blob.v ?? 1,
      });
    }

    const normalized = normalizeFromStored(blob);
    if (!normalized) throw new Error("SOLBaseline Unified: stored baseline exists but is unrecognized. Clear + recapture.");
    restoreState(physics, normalized);

    globalThis.__SOL_BASELINE_META = {
      createdAt: blob.createdAt,
      nodeCount: blob.nodeCount,
      edgeCount: blob.edgeCount,
      v: blob.v ?? 1,
    };

    return blob;
  }

  async function restore() {
    const physics = await waitForPhysics();
    const blob = readBlob();
    if (!blob) throw new Error(`SOLBaseline Unified: no baseline found at localStorage["${KEY}"]`);

    const normalized = normalizeFromStored(blob);
    if (!normalized) {
      throw new Error(
        "SOLBaseline Unified: baseline exists but can't be normalized. Run SOLBaseline.clear(); then await SOLBaseline.ensure({force:true})."
      );
    }

    restoreState(physics, normalized);

    globalThis.__SOL_BASELINE_META = {
      createdAt: blob.createdAt,
      nodeCount: blob.nodeCount,
      edgeCount: blob.edgeCount,
      v: blob.v ?? 1,
    };

    console.log(`🧊 Baseline RESTORED (created ${blob.createdAt}, v=${blob.v ?? 1})`);
    return blob;
  }

  function clear() {
    localStorage.removeItem(KEY);
    delete globalThis.__SOL_BASELINE_META;
    console.log(`🗑️ Baseline CLEARED → localStorage["${KEY}"] removed`);
  }

  function exportJson() {
    const blob = readBlob();
    if (!blob) throw new Error(`SOLBaseline Unified: no baseline found at localStorage["${KEY}"]`);
    downloadText(`sol_baseline_snap_${nowTag()}.json`, JSON.stringify(blob));
    console.log("📦 Baseline JSON downloaded.");
  }

  function importJsonText(jsonText) {
    const blob = JSON.parse(jsonText);
    if (!blob || (!blob.snap && !blob.nodeSnap) || !blob.createdAt) {
      throw new Error("SOLBaseline Unified: invalid baseline JSON");
    }
    writeBlob(blob);
    console.log(`📥 Baseline JSON imported → localStorage["${KEY}"]`, {
      createdAt: blob.createdAt,
      nodeCount: blob.nodeCount,
      v: blob.v ?? 1,
    });
  }

  function peek() { return readBlob(); }

  globalThis.SOLBaseline = {
    key: KEY,
    waitForPhysics,
    ensure,
    restore,
    clear,
    exportJson,
    importJsonText,
    peek,
  };

  console.log("🧊 Installing SOLBaseline Unified v1.4…");
  await ensure({ force: false, exportJson: false });
  console.log("✅ SOLBaseline ready. Use await SOLBaseline.restore() anytime.");
})().catch((err) => console.error("❌ SOLBaseline Unified error:", err));
