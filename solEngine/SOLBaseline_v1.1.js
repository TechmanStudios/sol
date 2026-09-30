(() => {
  "use strict";

  const SNAP_KEY = "__SOL_BASELINE_SNAP_V1";
  const VERSION = "SOLBaseline_v1.1";

  const safeNum = (x) => (Number.isFinite(x) ? x : 0);

  function getRoot() {
    return globalThis.SOLDashboard ?? globalThis.App ?? globalThis.app ?? null;
  }

  function getPhysics() {
    // Prefer the dashboard’s exposed solver if present (v3.6 commonly exposes one),
    // else fall back to SOLDashboard/App state.
    const solver = globalThis.solver;
    if (solver?.nodes && solver?.edges) return solver;

    const root = getRoot();
    const physics = root?.state?.physics;
    if (physics?.nodes && physics?.edges) return physics;

    throw new Error("Physics not ready. Open/initialize the SOL dashboard first.");
  }

  async function waitForPhysics(timeoutMs = 12000) {
    const t0 = performance.now();
    while (performance.now() - t0 < timeoutMs) {
      try {
        const p = getPhysics();
        if (p?.nodes?.length) return p;
      } catch (_) {}
      await new Promise((r) => setTimeout(r, 100));
    }
    throw new Error("Timed out waiting for physics. Is the dashboard running?");
  }

  function snapshotPhysics(physics) {
    const nodeSnap = {};
    for (const n of (physics.nodes || [])) {
      if (!n || n.id == null) continue;
      const id = String(n.id);
      nodeSnap[id] = {
        rho: safeNum(n.rho),
        p: safeNum(n.p),
        psi: safeNum(n.psi),
        psi_bias: safeNum(n.psi_bias),
        semanticMass: safeNum(n.semanticMass),
        semanticMass0: safeNum(n.semanticMass0),
        // battery-ish internals if present
        isBattery: !!n.isBattery,
        b_q: safeNum(n.b_q),
        b_charge: safeNum(n.b_charge),
        b_state: safeNum(n.b_state),
      };
    }

    const edgeFlux = (physics.edges || []).map((e) => safeNum(e?.flux));

    return {
      version: VERSION,
      createdAt: new Date().toISOString(),
      nodeCount: (physics.nodes || []).length,
      edgeCount: (physics.edges || []).length,
      nodeSnap,
      edgeFlux,
    };
  }

  function restorePhysics(physics, snap) {
    if (!snap?.nodeSnap) throw new Error("Invalid baseline snapshot (missing nodeSnap).");

    for (const n of (physics.nodes || [])) {
      if (!n || n.id == null) continue;
      const s = snap.nodeSnap[String(n.id)];
      if (!s) continue;

      if (typeof n.rho === "number") n.rho = safeNum(s.rho);
      if (typeof n.p === "number") n.p = safeNum(s.p);
      if (typeof n.psi === "number") n.psi = safeNum(s.psi);
      if (typeof n.psi_bias === "number") n.psi_bias = safeNum(s.psi_bias);
      if (typeof n.semanticMass === "number") n.semanticMass = safeNum(s.semanticMass);
      if (typeof n.semanticMass0 === "number") n.semanticMass0 = safeNum(s.semanticMass0);

      if (n.isBattery) {
        if ("b_q" in n) n.b_q = safeNum(s.b_q);
        if ("b_charge" in n) n.b_charge = safeNum(s.b_charge);
        if ("b_state" in n) n.b_state = safeNum(s.b_state);
      }
    }

    const edges = physics.edges || [];
    const ef = Array.isArray(snap.edgeFlux) ? snap.edgeFlux : [];
    for (let i = 0; i < edges.length; i++) {
      const e = edges[i];
      if (!e) continue;
      e.flux = Number.isFinite(ef[i]) ? ef[i] : 0;
    }
  }

  function has() {
    return !!localStorage.getItem(SNAP_KEY);
  }

  async function capture({ force = false } = {}) {
    const physics = await waitForPhysics();
    if (has() && !force) {
      console.warn(`[SOLBaseline] Snapshot already exists at ${SNAP_KEY}. Use capture({force:true}) to overwrite.`);
      return { ok: true, key: SNAP_KEY, overwritten: false };
    }
    const snap = snapshotPhysics(physics);
    localStorage.setItem(SNAP_KEY, JSON.stringify(snap));
    console.log(`[SOLBaseline] Captured baseline → ${SNAP_KEY} (nodes=${snap.nodeCount}, edges=${snap.edgeCount})`);
    return { ok: true, key: SNAP_KEY, overwritten: force };
  }

  async function restore() {
    const physics = await waitForPhysics();
    const raw = localStorage.getItem(SNAP_KEY);
    if (!raw) throw new Error(`[SOLBaseline] No baseline snapshot found at ${SNAP_KEY}. Run SOLBaseline.capture() once.`);
    const snap = JSON.parse(raw);
    restorePhysics(physics, snap);
    return { ok: true, key: SNAP_KEY, version: snap?.version ?? "unknown" };
  }

  function peek() {
    const raw = localStorage.getItem(SNAP_KEY);
    return raw ? JSON.parse(raw) : null;
  }

  globalThis.SOLBaseline = {
    VERSION,
    SNAP_KEY,
    waitForPhysics,
    has,
    capture,
    restore,
    snapshotPhysics,
    restorePhysics,
    peek,
  };

  console.log(`SOLBaseline installed (${VERSION}). Key=${SNAP_KEY}`);
  console.log(`Try: await SOLBaseline.restore()`);
})();
