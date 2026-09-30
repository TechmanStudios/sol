// ============================================================================
// SOL Engine — Headless Core (sol-core)
// ============================================================================
// Extracted from sol_dashboard_v3_7_2.html — Phase 0 of the Hippocampus roadmap.
//
// This module contains the pure simulation logic with ZERO browser/DOM deps.
// It must produce identical results to the dashboard for any given inputs.
//
// SACRED MATH: The core physics equations (pressure, flux, damping, psi
// diffusion, conductance, CapLaw) are transcribed verbatim from the dashboard.
// They must NOT be modified without updating the math foundation document.
// ============================================================================

// ---------------------------------------------------------------------------
// Utility
// ---------------------------------------------------------------------------
function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

// DJB2 hash (deterministic, matches dashboard)
function hashStringDjb2(str) {
  const s = String(str == null ? '' : str);
  let hash = 5381;
  for (let i = 0; i < s.length; i++) {
    hash = ((hash << 5) + hash) + s.charCodeAt(i);
    hash |= 0;
  }
  return (hash >>> 0).toString(16);
}

// ---------------------------------------------------------------------------
// SOLPhysics — the core simulation class
// ---------------------------------------------------------------------------
// Transcribed verbatim from class SOLPhysics in sol_dashboard_v3_7_2.html
// Lines 6355–7210 of the dashboard.
// ---------------------------------------------------------------------------
export class SOLPhysics {
  constructor(nodes, edges) {
    this.nodes = nodes.map(n => {
      const base = {
        ...n,
        rho: 0,
        p: 0,
        psi_bias: (n && typeof n.psi_bias === 'number') ? n.psi_bias : (n.group === 'spirit' ? 1 : (n.group === 'tech' ? -1 : 0)),
        psi: (n && typeof n.psi === 'number') ? n.psi : (n.group === 'spirit' ? 1 : (n.group === 'tech' ? -1 : 0))
      };

      if (base && typeof base.semanticMass !== 'number') base.semanticMass = 1.0;
      if (base && typeof base.semanticMass0 !== 'number') base.semanticMass0 = base.semanticMass;
      if (base && typeof base.lastInteractionTime !== 'number') base.lastInteractionTime = 0;
      if (base && typeof base.isSingularity !== 'boolean') base.isSingularity = false;

      if (base && base.isBattery) {
        base.b_q = (typeof base.b_q === 'number') ? base.b_q : 0;
        base.b_charge = (typeof base.b_charge === 'number') ? base.b_charge : 0;
        base.b_state = (base.b_state === 1 || base.b_state === -1) ? base.b_state : (base.b_q >= 0 ? 1 : -1);
        base.psi_bias = base.b_state;
        base.psi = base.b_state;
      }
      return base;
    });

    this.nodeById = new Map(this.nodes.map(n => [n.id, n]));
    this.nodeIndexById = new Map(this.nodes.map((n, idx) => [n.id, idx]));

    this.edges = edges.map(e => ({
      ...e,
      w0: (typeof e.w0 === 'number' ? e.w0 : 1.0),
      background: !!e.background,
      flux: 0,
      conductance: 1.0
    }));

    this.globalBias = 0;

    // Per-node mode evolution
    this.psiDiffusion = 0.6;
    this.psiRelaxBase = 0.12;
    this.psiGlobalNudge = 0.0;
    this.psiClamp = 1.0;

    // Mode-shaped conductance
    this.conductanceBase = 1.0;
    this.conductanceGamma = 0.75;
    this.conductanceMin = 0.1;
    this.conductanceMax = 3.0;

    // Battery (memristive accumulator)
    this.batteryCfg = {
      qMax: 40.0,
      qThresh: 16.0,
      leakLambda: 0.08,
      chargeRateSame: 0.32,
      chargeRateOpp: 0.18,
      avalancheGain: 1.15,
      resonanceBoost: 1.8,
      dampingClamp: 0.35,
      correctionSink: 0.22,
      diodeResonanceOut: 1.25,
      diodeResonanceIn: 0.80,
      diodeDampingOut: 0.25,
      diodeDampingIn: 1.00,
      chargeDecayRate: 0.05,
      flipThreshold: 0.85,
      collapseFactor: 0.30,
      resonanceDrive: 1.5,
      dampingDrag: 0.5
    };

    // Lighthouse phase-gating
    this.phaseCfg = {
      omega: 0.15,
      surfaceTension: 1.2,
      deepViscosity: 0.8
    };

    // Semantic Mass & Decay
    this.semanticCfg = {
      decayRate: 0.05,
      minMass: 0.25,
      singularityMass: 1000,
      reinforceScale: 1.0
    };

    // Semantic MHD
    this.mhdCfg = {
      bBuild: 0.10,
      bDecay: 0.06,
      bMax: 4.0,
      bGamma: 0.35
    };

    // Jeans collapse
    this.jeansCfg = {
      Jcrit: 18.0,
      accreteRate: 0.55,
      starDampingFactor: 0.18,
      accreteToMass: 0.04
    };

    // Vorticity
    this.vortCfg = {
      pairsPerNode: 6,
      trianglesPerNode: 3,
      topK: 10,
      emaAlpha: 0.20,
      leaderboardIntervalSec: 0.75,
      zMuAlpha: 0.05,
      zAbsDevAlpha: 0.05
    };
    this.vortNorm_local = new Map();
    this.vortNorm_ema = new Map();
    this.circAbs_ema = new Map();
    this.fluxAbs_ema = new Map();
    this.vortNorm_zState = new Map();
    this.circAbs_zState = new Map();
    this.vortNorm_global = 0;
    this.vortNorm_global_ema = 0;

    this.topK_vortNorm = [];
    this.topK_circAbs = [];
    this.topK_vortNorm_hotNow = [];
    this.topK_vortNorm_hotSurge = [];
    this.topK_vortNorm_hotDrop = [];
    this.topK_circAbs_hotNow = [];
    this.topK_circAbs_hotSurge = [];
    this.topK_circAbs_hotDrop = [];
    this.topK_vortNorm_persistent = [];
    this.topK_circAbs_persistent = [];
    this.topK_vortNorm_hybrid = [];
    this.topK_circAbs_hybrid = [];

    this._lastLeaderboardUpdateT = 0;
    this._t = 0;

    // Deterministic RNG for headless reproducibility (vorticity triangle sampling)
    // Uses a simple mulberry32 seeded PRNG instead of Math.random()
    this._rngSeed = 42;
    this._rng = this._createRng(this._rngSeed);
  }

  // ---- Deterministic RNG (mulberry32) ----
  _createRng(seed) {
    let s = seed | 0;
    return () => {
      s = (s + 0x6D2B79F5) | 0;
      let t = Math.imul(s ^ (s >>> 15), 1 | s);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  /** Seed the deterministic RNG (call before a run for reproducibility). */
  seedRng(seed) {
    this._rngSeed = seed;
    this._rng = this._createRng(seed);
  }

  clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

  // ---- Semantic Mass Decay ----
  applySemanticMassDecay(dt) {
    const cfg = this.semanticCfg;
    if (!cfg) return;
    const decay = (typeof cfg.decayRate === 'number' && Number.isFinite(cfg.decayRate)) ? cfg.decayRate : 0.05;
    const minMass = (typeof cfg.minMass === 'number' && Number.isFinite(cfg.minMass)) ? cfg.minMass : 0.25;
    const axiom = (typeof cfg.singularityMass === 'number' && Number.isFinite(cfg.singularityMass)) ? cfg.singularityMass : 1000;
    const factor = Math.exp(-decay * Math.max(0, dt));

    for (const n of this.nodes) {
      if (!n || !n.isConstellation) continue;
      if (n.isSingularity) continue;
      const m = (typeof n.semanticMass === 'number' && Number.isFinite(n.semanticMass)) ? n.semanticMass : 1.0;
      const next = Math.max(minMass, m * factor);
      n.semanticMass = next;
      if (n.semanticMass > axiom) n.isSingularity = true;
    }
  }

  reinforceSemanticStar(node, frequencyBoost = 1.0) {
    const n = node;
    if (!n || !n.isConstellation) return;
    if (!this.semanticCfg) return;
    if (n.isSingularity) return;

    const cfg = this.semanticCfg;
    const decay = (typeof cfg.decayRate === 'number' && Number.isFinite(cfg.decayRate)) ? cfg.decayRate : 0.05;
    const minMass = (typeof cfg.minMass === 'number' && Number.isFinite(cfg.minMass)) ? cfg.minMass : 0.25;
    const axiom = (typeof cfg.singularityMass === 'number' && Number.isFinite(cfg.singularityMass)) ? cfg.singularityMass : 1000;
    const scale = (typeof cfg.reinforceScale === 'number' && Number.isFinite(cfg.reinforceScale)) ? cfg.reinforceScale : 1.0;

    const lastT = (typeof n.lastInteractionTime === 'number' && Number.isFinite(n.lastInteractionTime)) ? n.lastInteractionTime : 0;
    const elapsed = Math.max(0, (this._t || 0) - lastT);
    const decayFactor = Math.exp(-decay * elapsed);

    const cur = (typeof n.semanticMass === 'number' && Number.isFinite(n.semanticMass)) ? n.semanticMass : 1.0;
    n.semanticMass = Math.max(minMass, cur * decayFactor);

    const tension = (typeof n.tension === 'number' && Number.isFinite(n.tension)) ? n.tension : 0;
    const inj = Math.max(0, Number(frequencyBoost) || 0) * (1 + tension) * scale;
    n.semanticMass += inj;
    n.lastInteractionTime = (this._t || 0);

    if (n.semanticMass > axiom) n.isSingularity = true;
  }

  // ---- Equation of State: P = c * log(1 + rho / m) ----
  computePressure(c_press) {
    this.nodes.forEach(n => {
      const m = (n && typeof n.semanticMass === 'number' && Number.isFinite(n.semanticMass) && n.semanticMass > 0)
        ? n.semanticMass
        : 1.0;
      n.p = c_press * Math.log(1 + (n.rho / m));
    });
  }

  // ---- Psi (Belief Field) Diffusion ----
  updatePsi(dt) {
    const lap = new Array(this.nodes.length).fill(0);

    this.edges.forEach(e => {
      const ia = this.nodeIndexById.get(e.from);
      const ib = this.nodeIndexById.get(e.to);
      if (ia === undefined || ib === undefined) return;
      const a = this.nodes[ia];
      const b = this.nodes[ib];
      const d = b.psi - a.psi;
      lap[ia] += d;
      lap[ib] -= d;
    });

    this.nodes.forEach((n, idx) => {
      if (n && n.isBattery) {
        const s = (n.b_state === 1 || n.b_state === -1) ? n.b_state : 1;
        n.b_state = s;
        n.psi_bias = s;
        n.psi = s;
        return;
      }

      const rhoNorm = n.rho / (n.rho + 40);
      const relaxToBias = (this.psiRelaxBase * (0.35 + 0.65 * rhoNorm)) * (n.psi_bias - n.psi);
      const relaxToGlobal = this.psiGlobalNudge * (this.globalBias - n.psi);
      const diffusion = this.psiDiffusion * lap[idx];

      n.psi += dt * (diffusion + relaxToBias + relaxToGlobal);
      n.psi = this.clamp(n.psi, -this.psiClamp, this.psiClamp);
    });
  }

  // ---- Battery (Lighthouse) Logic ----
  updateBatteries(dt) {
    const cfg = this.batteryCfg;
    if (!cfg) return;

    for (const b of this.nodes) {
      if (!b || !b.isBattery) continue;
      if (b.b_state !== 1 && b.b_state !== -1) b.b_state = -1;
      if (!Number.isFinite(b.b_charge)) b.b_charge = 0;

      let incoming = 0;
      let drag = 0;

      for (const e of this.edges) {
        if (!e || e.background) continue;
        if (e.from !== b.id && e.to !== b.id) continue;

        const nbId = (e.from === b.id) ? e.to : e.from;
        const nb = this.nodeById.get(nbId);
        if (!nb) continue;

        const w = (typeof e.conductance === 'number' && Number.isFinite(e.conductance)) ? e.conductance : 1.0;
        const nbState = (nb && nb.isBattery)
          ? ((nb.b_state === 1 || nb.b_state === -1) ? nb.b_state : 1)
          : (((typeof nb.psi === 'number' ? nb.psi : 0) >= 0) ? 1 : -1);

        if (nbState === 1) incoming += w * (cfg.resonanceDrive || 1.5);
        else drag += w * (cfg.dampingDrag || 0.5);
      }

      const netFlux = incoming - drag;
      const chargeDelta = Math.tanh(netFlux) * dt;

      let leakage = 0;
      if (b.b_state === 1) leakage = b.b_charge * ((cfg.leakLambda || 0.05) * 0.2);
      else leakage = b.b_charge * (cfg.leakLambda || 0.05);

      b.b_charge = this.clamp(b.b_charge + chargeDelta - leakage, 0, 1);

      const tau = cfg.flipThreshold || 0.85;
      const collapse = tau * (cfg.collapseFactor || 0.3);

      if (b.b_state === -1 && b.b_charge > tau) {
        const pulseMass = (cfg.qMax || 40) * b.b_charge * (cfg.avalancheGain || 1.15);
        const connectedEdges = this.edges.filter(e => !e.background && (e.from === b.id || e.to === b.id));
        const share = pulseMass / Math.max(1, connectedEdges.length);

        connectedEdges.forEach(e => {
          const nbId = (e.from === b.id) ? e.to : e.from;
          const nb = this.nodeById.get(nbId);
          if (nb) nb.rho += share;
        });

        b.b_state = 1;
        b.b_charge = 1.0;
        b.psi = 1.0;
      } else if (b.b_state === 1 && b.b_charge < collapse) {
        b.b_state = -1;
        b.psi = -1;
      }

      b.psi = b.b_state;
      b.psi_bias = b.b_state;
    }
  }

  // ---- Edge Conductance (ψ-shaped) ----
  updateConductance() {
    this.edges.forEach(e => {
      const src = this.nodeById.get(e.from);
      const dst = this.nodeById.get(e.to);

      const avgPsi = (src.psi + dst.psi) / 2;
      let w = (e.w0 * this.conductanceBase) * Math.exp(this.conductanceGamma * avgPsi);

      if (this.mhdCfg) {
        const bGamma = (typeof this.mhdCfg.bGamma === 'number' && Number.isFinite(this.mhdCfg.bGamma)) ? this.mhdCfg.bGamma : 0.35;
        const b = (typeof e.bMag === 'number' && Number.isFinite(e.bMag)) ? e.bMag : 0;
        w *= (1 + bGamma * b);
      }

      const bNode = (src && src.isBattery) ? src : ((dst && dst.isBattery) ? dst : null);
      if (bNode && this.batteryCfg) {
        const s = (bNode.b_state === 1 || bNode.b_state === -1) ? bNode.b_state : 1;
        if (s === 1) {
          w *= (typeof this.batteryCfg.resonanceBoost === 'number' ? this.batteryCfg.resonanceBoost : 1.8);
        } else {
          w *= (typeof this.batteryCfg.dampingClamp === 'number' ? this.batteryCfg.dampingClamp : 0.35);
          const tightMax = Math.max(this.conductanceMin, Math.min(this.conductanceMax, 0.6));
          e.conductance = this.clamp(w, this.conductanceMin, tightMax);
          return;
        }
      }

      e.conductance = this.clamp(w, this.conductanceMin, this.conductanceMax);
    });
  }

  // ---- MHD (Magnetic Frozen-In Field) ----
  updateMagneticField(dt) {
    const cfg = this.mhdCfg;
    if (!cfg) return;
    const build = (typeof cfg.bBuild === 'number' && Number.isFinite(cfg.bBuild)) ? cfg.bBuild : 0.10;
    const decay = (typeof cfg.bDecay === 'number' && Number.isFinite(cfg.bDecay)) ? cfg.bDecay : 0.06;
    const bMax = (typeof cfg.bMax === 'number' && Number.isFinite(cfg.bMax)) ? cfg.bMax : 4.0;

    for (const e of this.edges) {
      if (!e || e.background) continue;
      const bPrev = (typeof e.bMag === 'number' && Number.isFinite(e.bMag)) ? e.bMag : 0;
      const fluxAbs = Math.abs((typeof e.flux === 'number' && Number.isFinite(e.flux)) ? e.flux : 0);
      const bNext = (bPrev * Math.exp(-decay * Math.max(0, dt))) + (build * fluxAbs * Math.max(0, dt));
      e.bMag = this.clamp(bNext, 0, bMax);
    }
  }

  // ---- Mean Abs Dev (variance-aware surprise for vorticity) ----
  updateMeanAbsDev(state, x, a = 0.05, b = 0.05) {
    if (!state || typeof state !== 'object') state = { mu: NaN, absDev: NaN };
    if (!Number.isFinite(state.mu)) state.mu = x;
    const muPrev = state.mu;
    state.mu = muPrev + a * (x - muPrev);

    const d = Math.abs(x - state.mu);
    if (!Number.isFinite(state.absDev)) state.absDev = Math.max(d, 1e-3);
    state.absDev = state.absDev + b * (d - state.absDev);

    const sigma = Math.max(1e-6, 1.2533 * state.absDev);
    const z = (x - state.mu) / sigma;
    return { z, mu: state.mu, sigma, state };
  }

  // ---- Vorticity (graph-native cycle circulation) ----
  updateVorticityFromFlux(dt) {
    const cfg = this.vortCfg || {};
    const pairsPerNode = Math.max(1, Math.min(parseInt(cfg.pairsPerNode, 10) || 6, 50));
    const trianglesPerNode = Math.max(1, Math.min(parseInt(cfg.trianglesPerNode, 10) || 3, 25));
    const topK = Math.max(1, Math.min(parseInt(cfg.topK, 10) || 10, 20));
    const alpha = (typeof cfg.emaAlpha === 'number' && Number.isFinite(cfg.emaAlpha)) ? cfg.emaAlpha : 0.20;
    const leaderboardIntervalSec = (typeof cfg.leaderboardIntervalSec === 'number' && Number.isFinite(cfg.leaderboardIntervalSec))
      ? Math.max(0.10, cfg.leaderboardIntervalSec)
      : 0.75;
    const zMuAlpha = (typeof cfg.zMuAlpha === 'number' && Number.isFinite(cfg.zMuAlpha)) ? cfg.zMuAlpha : 0.05;
    const zAbsDevAlpha = (typeof cfg.zAbsDevAlpha === 'number' && Number.isFinite(cfg.zAbsDevAlpha)) ? cfg.zAbsDevAlpha : 0.05;

    const edges = Array.isArray(this.edges) ? this.edges.filter(e => e && !e.background) : [];
    if (!edges.length || !Array.isArray(this.nodes) || !this.nodes.length) {
      this.vortNorm_global = 0;
      this.vortNorm_global_ema = this.vortNorm_global_ema + alpha * (0 - this.vortNorm_global_ema);
      return;
    }

    const adj = new Map();
    const fluxDir = new Map();
    const incidentFluxAbs = new Map();
    const und = new Set();
    const undKey = (a, b) => {
      const A = String(a);
      const B = String(b);
      return (A < B) ? `${A}|${B}` : `${B}|${A}`;
    };

    for (const e of edges) {
      const a = e.from;
      const b = e.to;
      if (a == null || b == null) continue;
      const f = (typeof e.flux === 'number' && Number.isFinite(e.flux)) ? e.flux : 0;
      const af = Math.abs(f);
      if (!adj.has(a)) adj.set(a, []);
      if (!adj.has(b)) adj.set(b, []);
      adj.get(a).push(b);
      adj.get(b).push(a);
      fluxDir.set(`${a}->${b}`, f);
      fluxDir.set(`${b}->${a}`, -f);
      und.add(undKey(a, b));

      incidentFluxAbs.set(a, (incidentFluxAbs.get(a) || 0) + af);
      incidentFluxAbs.set(b, (incidentFluxAbs.get(b) || 0) + af);
    }

    this.vortNorm_local = new Map();
    for (const n of this.nodes) {
      if (!n) continue;
      const i = n.id;
      const neigh = adj.get(i) || [];
      if (neigh.length < 2) {
        n.vortNorm_local = 0;
        this.vortNorm_local.set(i, 0);

        const prevV = this.vortNorm_ema.get(i) || 0;
        const prevC = this.circAbs_ema.get(i) || 0;
        const prevF = this.fluxAbs_ema.get(i) || 0;
        this.vortNorm_ema.set(i, prevV + alpha * (0 - prevV));
        this.circAbs_ema.set(i, prevC + alpha * (0 - prevC));
        this.fluxAbs_ema.set(i, prevF + alpha * ((incidentFluxAbs.get(i) || 0) - prevF));
        continue;
      }

      let sumAbs = 0;
      let cnt = 0;

      for (let t = 0; t < trianglesPerNode; t++) {
        let found = false;
        for (let p = 0; p < pairsPerNode; p++) {
          // Use deterministic RNG instead of Math.random()
          const j = neigh[Math.floor(this._rng() * neigh.length)];
          let k = neigh[Math.floor(this._rng() * neigh.length)];
          if (k === j) continue;
          if (!und.has(undKey(j, k))) continue;

          const cij = fluxDir.get(`${i}->${j}`) || 0;
          const cjk = fluxDir.get(`${j}->${k}`) || 0;
          const cki = fluxDir.get(`${k}->${i}`) || 0;
          const circ = cij + cjk + cki;
          sumAbs += Math.abs(circ);
          cnt++;
          found = true;
          break;
        }
      }

      n.vortNorm_local = cnt ? (sumAbs / cnt) : 0;
      this.vortNorm_local.set(i, n.vortNorm_local);

      const circAbs_local = n.vortNorm_local;
      const fluxAbs_local = incidentFluxAbs.get(i) || 0;

      const prevV = this.vortNorm_ema.get(i);
      const prevC = this.circAbs_ema.get(i);
      const prevF = this.fluxAbs_ema.get(i);
      this.vortNorm_ema.set(i, (typeof prevV === 'number' && Number.isFinite(prevV)) ? (prevV + alpha * (n.vortNorm_local - prevV)) : n.vortNorm_local);
      this.circAbs_ema.set(i, (typeof prevC === 'number' && Number.isFinite(prevC)) ? (prevC + alpha * (circAbs_local - prevC)) : circAbs_local);
      this.fluxAbs_ema.set(i, (typeof prevF === 'number' && Number.isFinite(prevF)) ? (prevF + alpha * (fluxAbs_local - prevF)) : fluxAbs_local);
    }

    const vals = this.nodes
      .map(n => (n && typeof n.vortNorm_local === 'number' && Number.isFinite(n.vortNorm_local)) ? n.vortNorm_local : 0)
      .filter(v => v > 0)
      .sort((a, b) => b - a);

    const take = vals.slice(0, topK);
    const meanTopK = take.length ? (take.reduce((s, v) => s + v, 0) / take.length) : 0;
    this.vortNorm_global = meanTopK;
    if (!Number.isFinite(this.vortNorm_global_ema)) this.vortNorm_global_ema = meanTopK;
    this.vortNorm_global_ema = this.vortNorm_global_ema + alpha * (meanTopK - this.vortNorm_global_ema);

    // Periodic leaderboards
    const tNow = (typeof this._t === 'number' && Number.isFinite(this._t)) ? this._t : 0;
    if (!Number.isFinite(this._lastLeaderboardUpdateT)) this._lastLeaderboardUpdateT = tNow;
    if ((tNow - this._lastLeaderboardUpdateT) >= leaderboardIntervalSec) {
      const wEma = 0.65;
      const wCur = 0.35;
      const zCap = 50;

      const vortHot = [], vortSurge = [], vortDrop = [], vortPersist = [], vortHybrid = [];
      const circHot = [], circSurge = [], circDrop = [], circPersist = [], circHybrid = [];

      for (const n of this.nodes) {
        if (!n) continue;
        const id = n.id;

        const vCur = this.vortNorm_local.get(id) || 0;
        const vE = this.vortNorm_ema.get(id) || 0;
        const vHybridScore = wEma * vE + wCur * vCur;
        let vState = this.vortNorm_zState.get(id);
        if (!vState || !Number.isFinite(vState.mu)) {
          vState = vState && typeof vState === 'object' ? vState : { mu: NaN, absDev: NaN };
          vState.mu = (typeof vE === 'number' && Number.isFinite(vE) && vE > 0) ? vE : vCur;
        }
        const vMad = this.updateMeanAbsDev(vState, vCur, zMuAlpha, zAbsDevAlpha);
        this.vortNorm_zState.set(id, vMad.state);
        const vZ = Math.min(zCap, Math.max(-zCap, vMad.z));
        const vZpos = Math.max(0, vZ);
        const vZneg = Math.max(0, -vZ);
        const vZabs = Math.abs(vZ);
        const vHotScore = vZabs;

        const cCur = vCur;
        const cE = this.circAbs_ema.get(id) || 0;
        const cHybridScore = wEma * cE + wCur * cCur;
        let cState = this.circAbs_zState.get(id);
        if (!cState || !Number.isFinite(cState.mu)) {
          cState = cState && typeof cState === 'object' ? cState : { mu: NaN, absDev: NaN };
          cState.mu = (typeof cE === 'number' && Number.isFinite(cE) && cE > 0) ? cE : cCur;
        }
        const cMad = this.updateMeanAbsDev(cState, cCur, zMuAlpha, zAbsDevAlpha);
        this.circAbs_zState.set(id, cMad.state);
        const cZ = Math.min(zCap, Math.max(-zCap, cMad.z));
        const cZpos = Math.max(0, cZ);
        const cZneg = Math.max(0, -cZ);
        const cZabs = Math.abs(cZ);
        const cHotScore = cZabs;

        if (vE > 0) vortPersist.push({ id, current: vCur, ema: vE, score: vE });
        if (vHybridScore > 0) vortHybrid.push({ id, score: vHybridScore });
        if (vHotScore > 0) vortHot.push({ id, score: vHotScore });
        if (vZpos > 0) vortSurge.push({ id, score: vZpos });
        if (vZneg > 0) vortDrop.push({ id, score: vZneg });

        if (cE > 0) circPersist.push({ id, score: cE });
        if (cHybridScore > 0) circHybrid.push({ id, score: cHybridScore });
        if (cHotScore > 0) circHot.push({ id, score: cHotScore });
        if (cZpos > 0) circSurge.push({ id, score: cZpos });
        if (cZneg > 0) circDrop.push({ id, score: cZneg });
      }

      const sortDesc = arr => arr.sort((a, b) => b.score - a.score);
      [vortPersist, vortHybrid, vortHot, vortSurge, vortDrop,
       circPersist, circHybrid, circHot, circSurge, circDrop].forEach(sortDesc);

      this.topK_vortNorm_persistent = vortPersist.slice(0, topK);
      this.topK_circAbs_persistent = circPersist.slice(0, topK);
      this.topK_vortNorm_hybrid = vortHybrid.slice(0, topK);
      this.topK_circAbs_hybrid = circHybrid.slice(0, topK);
      this.topK_vortNorm_hotNow = vortHot.slice(0, topK);
      this.topK_circAbs_hotNow = circHot.slice(0, topK);
      this.topK_vortNorm_hotSurge = vortSurge.slice(0, topK);
      this.topK_vortNorm_hotDrop = vortDrop.slice(0, topK);
      this.topK_circAbs_hotSurge = circSurge.slice(0, topK);
      this.topK_circAbs_hotDrop = circDrop.slice(0, topK);

      this.topK_vortNorm = this.topK_vortNorm_persistent.map(x => ({ id: x.id, value: x.score }));
      this.topK_circAbs = this.topK_circAbs_persistent.map(x => ({ id: x.id, value: x.score }));
      this._lastLeaderboardUpdateT = tNow;
    }
  }

  // ---- Jeans Collapse and Accretion ----
  jeansCollapseAndAccrete(dt, c_press, damping) {
    const cfg = this.jeansCfg;
    if (!cfg) return;
    const Jcrit = (typeof cfg.Jcrit === 'number' && Number.isFinite(cfg.Jcrit)) ? cfg.Jcrit : 18.0;
    const accRate = (typeof cfg.accreteRate === 'number' && Number.isFinite(cfg.accreteRate)) ? cfg.accreteRate : 0.55;
    const toMass = (typeof cfg.accreteToMass === 'number' && Number.isFinite(cfg.accreteToMass)) ? cfg.accreteToMass : 0.04;

    for (const star of this.nodes) {
      if (!star) continue;

      const eps = 1e-6;
      const p = (typeof star.p === 'number' && Number.isFinite(star.p)) ? star.p : (c_press * Math.log(1 + star.rho));
      const J = star.rho / (Math.abs(p) + eps);

      if (!star.isConstellation && J >= Jcrit) {
        star.isConstellation = true;
        star.protoStar = true;
      }
      if (J >= Jcrit) star.isStellar = true;

      if (!star.isStellar) continue;

      let accreted = 0;
      for (const e of this.edges) {
        if (!e || e.background) continue;
        if (e.kind !== 'tax') continue;
        const otherId = (e.from === star.id) ? e.to : ((e.to === star.id) ? e.from : null);
        if (!otherId) continue;
        const nb = this.nodeById.get(otherId);
        if (!nb) continue;
        if (nb.isBattery) continue;

        const pull = Math.min(nb.rho, nb.rho * accRate * Math.max(0, dt));
        if (pull <= 0) continue;
        nb.rho -= pull;
        star.rho += pull;
        accreted += pull;
      }

      if (accreted > 0) {
        const sm = (typeof star.semanticMass === 'number' && Number.isFinite(star.semanticMass)) ? star.semanticMass : 1.0;
        star.semanticMass = sm + (accreted * toMass);
      }
    }
  }

  // ======================================================================
  // MAIN TIME STEP — Lighthouse Protocol (Phase Gating)
  // ======================================================================
  // This is the SACRED MATH — transcribed verbatim from the dashboard.
  // ======================================================================
  step(dt, c_press, damping) {

    // --- A. THE HEARTBEAT (The On-Off Code) ---
    this._t = (this._t || 0) + dt;

    const phase = Math.cos(this.phaseCfg.omega * this._t * 10);

    const isSurfaceActive = phase > -0.2;
    const isDeepActive = phase < 0.2;

    // --- B. STANDARD UPDATES ---
    this.updatePsi(dt);
    this.applySemanticMassDecay(dt);
    this.computePressure(c_press);
    this.updateConductance();

    if (this.updateBatteries) this.updateBatteries(dt);

    this.computePressure(c_press);

    // --- C. PHASE-GATED FLUX TRANSPORT ---
    let totalFlux = 0;
    const dRho = new Array(this.nodes.length).fill(0);

    this.edges.forEach(e => {
      const ia = this.nodeIndexById.get(e.from);
      const ib = this.nodeIndexById.get(e.to);
      if (ia === undefined || ib === undefined) return;

      const src = this.nodes[ia];
      const dst = this.nodes[ib];

      const srcGroup = src.group || 'bridge';
      const dstGroup = dst.group || 'bridge';

      let srcAwake = true;
      let dstAwake = true;

      if (srcGroup === 'tech' && !isSurfaceActive) srcAwake = false;
      if (srcGroup === 'spirit' && !isDeepActive) srcAwake = false;
      if (dstGroup === 'tech' && !isSurfaceActive) dstAwake = false;
      if (dstGroup === 'spirit' && !isDeepActive) dstAwake = false;

      if (!srcAwake && !dstAwake) return;

      const deltaP = src.p - dst.p;

      let tension = 1.0;
      if (srcGroup === 'tech' || dstGroup === 'tech') tension = this.phaseCfg.surfaceTension;
      if (srcGroup === 'spirit' || dstGroup === 'spirit') tension = this.phaseCfg.deepViscosity;

      let diodeGain = 1.0;
      if (this.batteryCfg && (src.isBattery || dst.isBattery) && !e.background) {
        const bNode = (src.isBattery) ? src : dst;
        const s = (bNode.b_state === 1 || bNode.b_state === -1) ? bNode.b_state : 1;
        const battIsSrc = (src.isBattery);
        const outflow = battIsSrc ? (deltaP > 0) : (deltaP < 0);

        if (s === 1) diodeGain = outflow ? this.batteryCfg.diodeResonanceOut : this.batteryCfg.diodeResonanceIn;
        else diodeGain = outflow ? this.batteryCfg.diodeDampingOut : this.batteryCfg.diodeDampingIn;
      }

      const targetFlux = (e.conductance * tension * diodeGain) * deltaP;

      e.flux = e.flux * (1 - dt) + targetFlux * dt;
      totalFlux += Math.abs(e.flux);

      const flowAmt = e.flux * dt * 0.5;

      if (srcAwake) dRho[ia] -= flowAmt;
      if (dstAwake) dRho[ib] += flowAmt;
    });

    // Engine vorticity
    try { this.updateVorticityFromFlux(dt); } catch (_) { /* no-op */ }

    // Apply mass changes
    this.nodes.forEach((n, idx) => {
      n.rho += dRho[idx];

      const starFactor = (n && n.isStellar && this.jeansCfg)
        ? (typeof this.jeansCfg.starDampingFactor === 'number' ? this.jeansCfg.starDampingFactor : 0.18)
        : 1.0;
      n.rho *= (1.0 - (damping * dt * 0.1 * starFactor));
      if (n.rho < 0) n.rho = 0;
    });

    // MHD + gravity coupling
    this.updateMagneticField(dt);
    this.computePressure(c_press);
    this.jeansCollapseAndAccrete(dt, c_press, damping);

    let activeCount = 0;
    this.nodes.forEach(n => { if (n.rho > 0.1) activeCount++; });

    return { totalFlux, activeCount };
  }

  // ---- Injection ----
  inject(label, amount) {
    const q = String(label ?? '').trim().toLowerCase();
    if (!q) return false;

    let target = this.nodes.find(n => n.label.toLowerCase() === q);
    if (!target && q.length >= 2) {
      const matches = this.nodes.filter(n => n.label.toLowerCase().includes(q));
      if (matches.length === 1) target = matches[0];
    }

    if (!target) return false;

    // Event-horizon capture
    try {
      if (target && target.isConcept) {
        let best = null;
        for (const e of this.edges) {
          if (!e || e.kind !== 'tax' || e.background) continue;
          const otherId = (e.from === target.id) ? e.to : ((e.to === target.id) ? e.from : null);
          if (!otherId) continue;
          const other = this.nodeById.get(otherId);
          if (!other || !other.isConstellation) continue;
          if (!best) best = other;
          else {
            const bm = (typeof best.semanticMass === 'number' ? best.semanticMass : 1);
            const om = (typeof other.semanticMass === 'number' ? other.semanticMass : 1);
            if (om > bm) best = other;
          }
        }
        if (best) target = best;
      }
    } catch (_) { /* no-op */ }

    target.rho += amount;

    try {
      if (target && target.isConstellation) {
        const freqBoost = (Number(amount) || 0) / 50.0;
        this.reinforceSemanticStar(target, freqBoost);
      }
    } catch (_) { /* no-op */ }
    return true;
  }

  /** Inject by node ID (direct, no label lookup). */
  injectById(nodeId, amount) {
    const node = this.nodeById.get(nodeId);
    if (!node) return false;
    node.rho += amount;
    return true;
  }
}

// ---------------------------------------------------------------------------
// CapLaw — Degree-power capacitance law (canonical)
// ---------------------------------------------------------------------------
// Transcribed verbatim from App.sim.applyCapLaw in the dashboard.
// ---------------------------------------------------------------------------
export function applyCapLaw(physics, capLaw, dtOverride) {
  if (!capLaw || !capLaw.enabled) return { k0: null, k: null, alpha: null, clampMin: null, clampMax: null };
  if (!physics || !Array.isArray(physics.nodes) || !Array.isArray(physics.edges)) {
    throw new Error('applyCapLaw: physics missing nodes/edges');
  }

  const alpha = (typeof capLaw.alpha === 'number' && Number.isFinite(capLaw.alpha)) ? capLaw.alpha : 0.8;
  const clampMin = (typeof capLaw.clampMin === 'number' && Number.isFinite(capLaw.clampMin)) ? capLaw.clampMin : 0.25;
  const clampMax = (typeof capLaw.clampMax === 'number' && Number.isFinite(capLaw.clampMax)) ? capLaw.clampMax : 5000;
  const dt0 = (typeof capLaw.dt0 === 'number' && Number.isFinite(capLaw.dt0) && capLaw.dt0 > 0) ? capLaw.dt0 : 0.12;
  const gamma = (typeof capLaw.kDtGamma === 'number' && Number.isFinite(capLaw.kDtGamma)) ? capLaw.kDtGamma : 0.0;
  const lambda = (typeof capLaw.lambda === 'number' && Number.isFinite(capLaw.lambda)) ? capLaw.lambda : 0.0;
  const dt = (typeof dtOverride === 'number' && Number.isFinite(dtOverride) && dtOverride > 0) ? dtOverride : dt0;
  const includeBg = !!capLaw.includeBackgroundEdges;

  const edges = includeBg ? physics.edges : physics.edges.filter(e => e && !e.background);
  const degById = new Map();
  for (const n of physics.nodes) {
    if (!n || n.id == null) continue;
    degById.set(String(n.id), 0);
  }
  for (const e of edges) {
    if (!e || e.from == null || e.to == null) continue;
    const a = String(e.from);
    const b = String(e.to);
    if (degById.has(a)) degById.set(a, (degById.get(a) || 0) + 1);
    if (degById.has(b)) degById.set(b, (degById.get(b) || 0) + 1);
  }

  const getNodeLoose = (id) => {
    if (id == null) return null;
    const direct = (physics.nodeById && typeof physics.nodeById.get === 'function') ? physics.nodeById.get(id) : null;
    if (direct) return direct;
    const want = String(id);
    for (const n of physics.nodes) {
      if (n && n.id != null && String(n.id) === want) return n;
    }
    return null;
  };

  const proxyMode = String(capLaw.proxy || 'degree').toLowerCase();
  const lawFamily = String(capLaw.lawFamily || 'power').toLowerCase();

  const proxyVal = (node) => {
    if (!node || node.id == null) return 0;
    const deg = degById.get(String(node.id)) || 0;
    if (proxyMode === 'degree') return deg;
    if (proxyMode === 'condsum') {
      const v = node.condSumNorm;
      if (typeof v !== 'number' || !Number.isFinite(v)) {
        throw new Error('applyCapLaw: proxy=condSum requested but node.condSumNorm missing');
      }
      return v;
    }
    if (proxyMode === 'hybrid') {
      const v = node.condSumNorm;
      if (typeof v !== 'number' || !Number.isFinite(v)) {
        throw new Error('applyCapLaw: proxy=hybrid requested but node.condSumNorm missing');
      }
      return deg + lambda * v;
    }
    return deg;
  };

  const anchor = capLaw.anchor || { nodeId: null, smRef: null };
  const anchorNode = getNodeLoose(anchor.nodeId);
  const smRef = (anchor && typeof anchor.smRef === 'number' && Number.isFinite(anchor.smRef)) ? anchor.smRef : null;
  if (!anchorNode || anchorNode.id == null) throw new Error('applyCapLaw: anchor node not found');
  if (smRef == null) throw new Error('applyCapLaw: anchor smRef missing');

  const xAnchor = Math.max(0, Number(proxyVal(anchorNode)) || 0);
  if (!(xAnchor > 0)) {
    throw new Error('applyCapLaw: anchor proxy is zero; cannot derive k0');
  }

  let k0 = (typeof capLaw.k0 === 'number' && Number.isFinite(capLaw.k0)) ? capLaw.k0 : null;
  if (k0 == null) {
    if (lawFamily === 'linear') k0 = smRef / xAnchor;
    else k0 = smRef / Math.pow(xAnchor, alpha);
  }

  const k = k0 * Math.pow(dt / dt0, gamma);
  const clip = (v) => Math.max(clampMin, Math.min(clampMax, v));

  const writeTo = String(capLaw.writeTo || 'both').toLowerCase();
  for (const n of physics.nodes) {
    if (!n || n.id == null) continue;
    const x = Math.max(0, Number(proxyVal(n)) || 0);
    let smRaw;
    if (lawFamily === 'linear') smRaw = k * x;
    else smRaw = k * Math.pow(x, alpha);
    const sm = clip(smRaw);
    if (writeTo === 'semanticmass' || writeTo === 'both') n.semanticMass = sm;
    if (writeTo === 'semanticmass0' || writeTo === 'both') n.semanticMass0 = sm;
  }

  return { k0, k, alpha, clampMin, clampMax };
}

// ---------------------------------------------------------------------------
// CapLaw Signature (for comparability)
// ---------------------------------------------------------------------------
export function getCapLawSignature(capLaw) {
  const law = capLaw || {};
  const anchor = (law && typeof law.anchor === 'object' && law.anchor) ? law.anchor : {};
  const numOrNull = (v) => (typeof v === 'number' && Number.isFinite(v)) ? v : null;
  const sigObj = {
    enabled: !!law.enabled,
    lawFamily: (law.lawFamily != null) ? String(law.lawFamily) : '',
    proxy: (law.proxy != null) ? String(law.proxy) : '',
    alpha: numOrNull(law.alpha),
    k0: numOrNull(law.k0),
    dt0: numOrNull(law.dt0),
    kDtGamma: numOrNull(law.kDtGamma),
    lambda: numOrNull(law.lambda),
    clampMin: numOrNull(law.clampMin),
    clampMax: numOrNull(law.clampMax),
    anchor: {
      nodeId: (anchor && anchor.nodeId != null) ? anchor.nodeId : null,
      smRef: numOrNull(anchor.smRef)
    },
    includeBackgroundEdges: !!law.includeBackgroundEdges,
    writeTo: (law.writeTo != null) ? String(law.writeTo) : ''
  };
  return JSON.stringify(sigObj);
}

// ---------------------------------------------------------------------------
// Metrics — computed exactly as the dashboard loop does
// ---------------------------------------------------------------------------
export function computeMetrics(physics) {
  const nodes = physics.nodes;
  const edges = physics.edges;

  let sumRho = 0;
  let maxRho = 0;
  let rhoMaxId = null;
  for (const n of nodes) {
    sumRho += n.rho;
    if (n.rho > maxRho) {
      maxRho = n.rho;
      rhoMaxId = n.id;
    }
  }
  const avgRho = sumRho / Math.max(1, nodes.length);

  // Normalized Shannon entropy (0..1)
  let entropy = 0;
  if (sumRho > 0) {
    let H = 0;
    for (const n of nodes) {
      const p = n.rho / sumRho;
      if (p > 0) H -= p * Math.log(p);
    }
    const Hmax = Math.log(Math.max(1, nodes.length));
    entropy = Hmax > 0 ? (H / Hmax) : 0;
  }

  let maxFluxAbs = 0;
  let totalFlux = 0;
  for (const e of edges) {
    const a = Math.abs(e.flux);
    totalFlux += a;
    if (a > maxFluxAbs) maxFluxAbs = a;
  }

  let activeCount = 0;
  for (const n of nodes) {
    if (n.rho > 0.1) activeCount++;
  }

  return {
    entropy,
    totalFlux,
    maxFluxAbs,
    mass: sumRho,
    avgRho,
    maxRho,
    rhoMaxId,
    activeCount,
    vortNorm_global: physics.vortNorm_global,
    vortNorm_global_ema: physics.vortNorm_global_ema
  };
}

// ---------------------------------------------------------------------------
// Snapshot / Restore (baseline save/restore)
// ---------------------------------------------------------------------------
export function snapshotState(physics) {
  const nodeSnap = new Map();
  for (const n of (physics.nodes || [])) {
    if (!n || n.id == null) continue;
    nodeSnap.set(String(n.id), {
      rho: n.rho,
      p: n.p,
      psi: n.psi,
      psi_bias: n.psi_bias,
      semanticMass: n.semanticMass,
      semanticMass0: n.semanticMass0,
      b_q: n.b_q,
      b_charge: n.b_charge,
      b_state: n.b_state
    });
  }
  const edgeFlux = (physics.edges || []).map(e => (e && typeof e.flux === 'number' && Number.isFinite(e.flux)) ? e.flux : 0);
  return { nodeSnap, edgeFlux };
}

export function restoreState(physics, snap, capLaw) {
  if (!snap) return;
  for (const n of (physics.nodes || [])) {
    if (!n || n.id == null) continue;
    const s = snap.nodeSnap.get(String(n.id));
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
  for (let i = 0; i < edges.length; i++) {
    const e = edges[i];
    if (!e) continue;
    e.flux = (snap.edgeFlux && Number.isFinite(snap.edgeFlux[i])) ? snap.edgeFlux[i] : 0;
  }

  // Recompute derived fields after restore
  if (capLaw && capLaw.enabled) {
    try { applyCapLaw(physics, capLaw); } catch (_) { /* no-op */ }
  }
}

// ---------------------------------------------------------------------------
// Edge computation helpers (graph construction)
// ---------------------------------------------------------------------------
export function computeAllEdges(rawNodes, rawEdges, opts = {}) {
  const useAllToAll = !!opts.useAllToAll;
  const bgW0 = (typeof opts.backgroundW0 === 'number') ? opts.backgroundW0 : 0.14;

  function edgeW0(e) {
    if (e && Number.isFinite(e.w0)) return e.w0;
    if (e && e.kind === 'tax') return 0.70;
    return 1.0;
  }

  if (!useAllToAll) return rawEdges.map(e => ({ ...e, w0: edgeW0(e), background: false }));

  const strong = rawEdges.map(e => ({ ...e, w0: edgeW0(e), background: false }));
  const edgeKey = (a, b) => {
    const lo = Math.min(a, b);
    const hi = Math.max(a, b);
    return `${lo}-${hi}`;
  };
  const existing = new Set(strong.map(e => edgeKey(e.from, e.to)));

  const ids = rawNodes.map(n => n.id);
  const background = [];
  for (let i = 0; i < ids.length; i++) {
    for (let j = i + 1; j < ids.length; j++) {
      const a = ids[i];
      const b = ids[j];
      const k = edgeKey(a, b);
      if (existing.has(k)) continue;
      background.push({ from: a, to: b, w0: bgW0, background: true });
    }
  }
  return strong.concat(background);
}

// ---------------------------------------------------------------------------
// Default export: convenience factory
// ---------------------------------------------------------------------------
export { hashStringDjb2 };

/**
 * Create a SOLPhysics instance from raw node/edge definitions.
 *
 * @param {Object} opts
 * @param {Array} opts.rawNodes - Array of { id, label, group, ... }
 * @param {Array} opts.rawEdges - Array of { from, to, ... }
 * @param {Object} [opts.capLaw] - CapLaw configuration (applied after construction)
 * @param {boolean} [opts.useAllToAll] - Include background all-to-all edges
 * @param {number} [opts.backgroundW0] - Background edge weight (default 0.14)
 * @param {number} [opts.rngSeed] - Deterministic RNG seed (default 42)
 * @returns {{ physics: SOLPhysics, capLawInfo: Object|null }}
 */
export function createEngine(opts) {
  const { rawNodes, rawEdges, capLaw, useAllToAll, backgroundW0, rngSeed } = opts;

  const allEdges = computeAllEdges(rawNodes, rawEdges, { useAllToAll, backgroundW0 });
  const physics = new SOLPhysics(rawNodes, allEdges);

  if (typeof rngSeed === 'number') physics.seedRng(rngSeed);

  let capLawInfo = null;
  if (capLaw && capLaw.enabled) {
    capLawInfo = applyCapLaw(physics, capLaw);
  }

  return { physics, capLawInfo };
}
