(async () => {
  // ============================================================
  // SOLBaseline Unified v1.3
  // Backward-compatible with:
  // - PersistedBaseline_v1: { v, createdAt, nodeCount, edgeCount, snap:{nodes[], edgeFlux[]} }
  // - Newer formats: { nodeSnap:{}, edgeFlux:[] } or { nodes:[], edgeFlux:[] }
  //
  // API:
  // - await SOLBaseline.ensure({ force?: boolean, exportJson?: boolean })
  // - await SOLBaseline.restore()
  // - SOLBaseline.clear()
  // - SOLBaseline.exportJson()
  // - SOLBaseline.importJsonText(jsonText)
  // - SOLBaseline.peek()
  // ============================================================

  const KEY = "__SOL_BASELINE_SNAP_V1";

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const nowTag = () => new Date().toISOString().replace(/[:.]/g, "") + "Z";

  function downloadText(filename, text, mime = "application/json") {
    const blob = new Blob([text], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 5000);
  }

  // Broad but UI-neutral discovery of physics
  function getPhysicsMaybe() {
    return (
      globalThis.solver ||
      window.solver ||
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
        rho: n.rho,
        p: n.p,
        psi: n.psi,
        psi_bias: n.psi_bias,
        semanticMass: n.semanticMass,
        semanticMass0: n.semanticMass0,
        isBattery: !!n.isBattery,
        b_q: n.b_q,
        b_charge: n.b_charge,
        b_state: n.b_state,
      });
    }

    const edgeFlux = (physics.edges || []).map((e) =>
      e && Number.isFinite(e.flux) ? e.flux : 0
    );

    return { nodes, edgeFlux };
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
      };
    }
    return nodeSnap;
  }

  // Accepts multiple historical shapes and returns a normalized "snap"
  // snap is one of:
  // - { nodeSnap:{}, edgeFlux:[] }  (preferred)
  // - { nodes:[], edgeFlux:[] }    (legacy)
  function normalizeFromStored(stored) {
    if (!stored || typeof stored !== "object") return null;

    // Case A: v1 blob with stored.snap
    if (stored.snap && typeof stored.snap === "object") {
      const s = stored.snap;

      if (s.nodeSnap && typeof s.nodeSnap === "object") {
        return { nodeSnap: s.nodeSnap, edgeFlux: Array.isArray(s.edgeFlux) ? s.edgeFlux : [] };
      }
      if (Array.isArray(s.nodes)) {
        return {
          nodeSnap: nodesArrayToNodeSnap(s.nodes),
          edgeFlux: Array.isArray(s.edgeFlux) ? s.edgeFlux : [],
          _legacyNodes: s.nodes, // keep for possible rewrite
        };
      }
    }

    // Case B: already in new top-level snap
    if (stored.nodeSnap && typeof stored.nodeSnap === "object") {
      return { nodeSnap: stored.nodeSnap, edgeFlux: Array.isArray(stored.edgeFlux) ? stored.edgeFlux : [] };
    }

    // Case C: raw legacy snap at top level
    if (Array.isArray(stored.nodes)) {
      return { nodeSnap: nodesArrayToNodeSnap(stored.nodes), edgeFlux: Array.isArray(stored.edgeFlux) ? stored.edgeFlux : [] };
    }

    return null;
  }

  function restoreState(physics, normalizedSnap) {
    if (!normalizedSnap?.nodeSnap) throw new Error("SOLBaseline Unified: invalid baseline (missing nodeSnap after normalize).");

    const byId = normalizedSnap.nodeSnap;

    for (const n of physics.nodes || []) {
      if (!n || n.id == null) continue;
      const s = byId[String(n.id)];
      if (!s) continue;

      n.rho = s.rho;
      n.p = s.p;
      n.psi = s.psi;
      n.psi_bias = s.psi_bias;
      n.semanticMass = s.semanticMass;
      n.semanticMass0 = s.semanticMass0;

      if (n.isBattery) {
        n.b_q = s.b_q;
        n.b_charge = s.b_charge;
        n.b_state = s.b_state;
      }
    }

    const edges = physics.edges || [];
    const ef = Array.isArray(normalizedSnap.edgeFlux) ? normalizedSnap.edgeFlux : [];
    for (let i = 0; i < edges.length; i++) {
      const e = edges[i];
      if (!e) continue;
      e.flux = Number.isFinite(ef[i]) ? ef[i] : 0;
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
        v: 2, // unified
        createdAt: new Date().toISOString(),
        nodeCount: (physics.nodes || []).length,
        edgeCount: (physics.edges || []).length,

        // Keep legacy shape for compatibility with old scripts:
        snap: snapLegacy,

        // Also store preferred map form (what newer tooling wants):
        nodeSnap,
        edgeFlux: snapLegacy.edgeFlux,
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

    // Always restore after ensure (fresh refresh lands same basin)
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
      edgeCount: blob.edgeCount,
      v: blob.v ?? 1,
    });
  }

  function peek() {
    return readBlob();
  }

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

  console.log("🧊 Installing SOLBaseline Unified v1.3…");
  // NOTE: does NOT auto-export unless you ask it to
  await ensure({ force: false, exportJson: false });
  console.log("✅ SOLBaseline ready. Use await SOLBaseline.restore() anytime.");
})().catch((err) => console.error("❌ SOLBaseline Unified error:", err));
