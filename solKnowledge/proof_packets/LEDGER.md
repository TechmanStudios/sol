# SOL Proof Ledger (Master)

The single source of truth for all SOL research claims and proof packets.

## Structure

```
solKnowledge/proof_packets/
├── LEDGER.md              ← this file (master index)
├── domains/               ← one packet per research domain
│   └── phonon_faraday.md  ← founding domain (C1-C37)
└── raw/                   ← audit trail (individual PP files from cortex/experiments)
    └── PP-*.md            ← 15 raw packets (pre-domain era)
```

## Domain Registry

| Domain | Packet | Claims | Open Qs | Trials | Compute (min) | Suites | Last Updated |
|--------|--------|-------:|--------:|-------:|---------------:|-------:|--------------|
| phonon_faraday | [phonon_faraday.md](domains/phonon_faraday.md) | 104 | 0 | 15,606 | 645 | 76 | 2026-02-11 |

**Totals:** 104 claims | 0 open questions | 15,606 trials | 645 min compute

## Global Claim Index

Claims are globally unique (C1, C2, ...) regardless of domain.

| Claim | Domain | Summary |
|------:|--------|---------|
| C1 | phonon_faraday | All 140 phonon modes survive d=0→82.5 despite amplitude ↓ >10³⁰ |
| C2 | phonon_faraday | Catastrophic mode extinction at d=83.35 is first-order phase transition |
| C3 | phonon_faraday | Collapse threshold d≈83.33 is a mathematical constant, topology-invariant |
| C4 | phonon_faraday | All transitions are 100% deterministic — zero RNG sensitivity |
| C5 | phonon_faraday | Coherence collapse, deepening, and resurrection in the critical zone |
| C6 | phonon_faraday | Directed energy transport ("itons") exists at low damping |
| C7 | phonon_faraday | Lattice is single-frequency; info encoded in phase coupling + amplitude hierarchy |
| C8 | phonon_faraday | Self-attractor phase transition: 112→0 across damping; 18 invariantly cold nodes |
| C9 | phonon_faraday | Basin destination programmable via w0 AND injection protocol (2D address space) |
| C10 | phonon_faraday | Cold-node injection generates 3× more iton transport |
| C11 | phonon_faraday | Uniform energy spread → perfect coherence (1.000) at all damping values |
| C12 | phonon_faraday | Sequential injection destroys coherence but sustains iton transport at high damping |
| C13 | phonon_faraday | Spirit-highway inversion implements deterministic NOT gate |
| C14 | phonon_faraday | AND gate: grail basin requires BOTH injection AND spirit-highway |
| C15 | phonon_faraday | All logic gates operate exclusively in turbulent regime (d < 10) |
| C16 | phonon_faraday | Four primitives compose into verified logic chain at d=0.2 |
| C17 | phonon_faraday | Multi-basin routing: 7 basins (d=0.2), 10 basins (d=5.0) via 3D control |
| C18 | phonon_faraday | Clock-signal re-injection sustains relay transport where single injection gives 0 |
| C19 | phonon_faraday | Gate cascading: 3 architectures all PASS — basin N controls stage N+1 |
| C20 | phonon_faraday | NOT gate extends to d=10.0; d=15-40 blocks; d=55.0 re-enables via basin shift |
| C21 | phonon_faraday | 5-instruction ISA + GATE reprogramming — 6 programs execute deterministically |
| C22 | phonon_faraday | Hardware-analog mapping R²=0.94 at low damping — linear conductance network |
| C23 | phonon_faraday | Basin 'grail[1]' deterministic attractor across d=5.0-20.0 |
| C24 | phonon_faraday | Basin 'christic[22]' deterministic attractor across d=15.0-40.0 |
| C25 | phonon_faraday | Entropy degradation curve: 99.6%→14.8%, cliff at d≈20.0 |
| C26 | phonon_faraday | Basin noise resilience at d=0.2: 100% stable up to σ=0.05 |
| C27 | phonon_faraday | Basin noise resilience at d=5.0: 100% stable up to σ=0.05 |
| C28 | phonon_faraday | Information capacity ~4.9 bits (30 basins); peaks at d=5.0 with 22 basins |
| C29 | phonon_faraday | NOT-gate cascades preserve alternation through 6 stages |
| C30 | phonon_faraday | Dead zone basin lock: standard injection → 'christic' invariantly d=12-40 |
| C31 | phonon_faraday | Dead zone basin lock: cold inject → 'christos' invariantly d=12-40 |
| C32 | phonon_faraday | Dead zone basin lock: clock assisted → 'grail' invariantly d=12-40 |
| C33 | phonon_faraday | Dead zone impervious to energy magnitude — topological trap not energy deficit |
| C34 | phonon_faraday | XOR-like gate functional at d=0.2 — three distinguishable output states |
| C35 | phonon_faraday | NAND gate (cascaded NOT+AND) functional at d=0.2 |
| C36 | phonon_faraday | NAND gate (cascaded NOT+AND) functional at d=5.0 |
| C37 | phonon_faraday | Basin control energy threshold: below E=50 dominant basin shifts |
| C38 | phonon_faraday | SR-latch third-state behavior: simultaneous input → simeon[98], sequential → numis'om[7] |
| C39 | phonon_faraday | Temporal injection diversity at d=5.0: 3 distinct basins from 4 timing patterns |
| C40 | phonon_faraday | Injection topology diversity at d=0.2: 4 distinct basins from 6 spatial configs |
| C41 | phonon_faraday | Injection topology diversity at d=5.0: 4 distinct basins from 6 spatial configs |
| C42 | phonon_faraday | Basin transition at d≈6.875 in zone 5.0-10.0: sharp phase boundary (3 basins) |
| C43 | phonon_faraday | Basin transition at d≈41.875 in zone 40.0-45.0: sharp phase boundary (2 basins) |
| C44 | phonon_faraday | Basin transition at d≈78.625 in zone 75.0-80.0: sharp phase boundary (2 basins) |
| C45 | phonon_faraday | Stochastic injection at d=0.2: 9–10 basins (3.2–3.3 bits) — high-entropy basin selector |
| C46 | phonon_faraday | Stochastic injection at d=5.0: 10 basins (3.3 bits) — high-entropy basin selector |
| C47 | phonon_faraday | Stochastic injection at d=10.0: 6–7 basins (2.6–2.8 bits) — high-entropy basin selector |
| C48 | phonon_faraday | Stochastic injection at d=15.0: 5–6 basins (2.3–2.6 bits) — high-entropy basin selector |
| C49 | phonon_faraday | Stochastic injection at d=20.0: 6–8 basins (2.6–3.0 bits) — high-entropy basin selector |
| C50 | phonon_faraday | Boundary cartography: 7 basins across 66 damping×w0 configs — 2D programmable surface |
| C51 | phonon_faraday | Basin 'metatron[9]' is w0-invariant at d=2.0 |
| C52 | phonon_faraday | Basin 'christic[22]' is w0-invariant at d=12.0 |
| C53 | phonon_faraday | Basin 'christic[22]' is w0-invariant at d=15.0 |
| C54 | phonon_faraday | Basin 'christic[22]' is w0-invariant at d=20.0 |
| C55 | phonon_faraday | Basin 'christic[22]' is w0-invariant at d=30.0 |
| C56 | phonon_faraday | Basin 'numis'om[7]' is w0-invariant at d=70.0 |
| C57 | phonon_faraday | Multi-zone sweep: 4 zones map to 2 basin families — discrete address space |
| C58 | phonon_faraday | Intra-zone coherence: 3/4 zones show single basin across ±2 perturbations |
| C59 | phonon_faraday | Symmetry breaking: 2/4 asymmetric injections shift basin — group-specific selector |
| C60 | phonon_faraday | Basin stability: all 7 dampings show ≥90% perturbation invariance under ±1.0 shifts |
| C61 | phonon_faraday | Minimum temporal resolution = 1 step at d=5.0: gap 3→4 switches basin |
| C62 | phonon_faraday | Gap sweep non-monotonic cycling: 8 distinct basins from 19 gap values at d=5.0 |
| C63 | phonon_faraday | Pulse count high-res channel: every ΔN=1 (N=1–6) produces different basin |
| C64 | phonon_faraday | Onset delay sensitivity: 6 basins from 12 delays, first transition at delay 10→20 |
| C65 | phonon_faraday | Injection ordering encodes basin: 4 basins from 9 temporal orderings |
| C66 | phonon_faraday | Temporal sensitivity regime-dependent: d=0.2 gap-invariant, d=5.0 has 11 transitions |
| C67 | phonon_faraday | Decision latency universally late (step 429–498): lattice holds potential ≥85.8% of runtime |
| C68 | phonon_faraday | Decision volatility non-monotonic: d=5.0 most exploratory (13 basins), d=40 most volatile (37 changes) |
| C69 | phonon_faraday | HHI reaches 95% uniformity (0.00754 vs 0.00714); 124-way superposition sustained 150+ steps, irreversible |
| C70 | phonon_faraday | 489/500 steps (97.8%) exhibit dual-peak conditions — system lives in multi-node parity |
| C71 | phonon_faraday | Regional settlement desynchrony: tech=step 0, bridge=step 487, spirit=step 497 (497-step spread) |
| C72 | phonon_faraday | Spirit group kingmaker: 18 nodes (12.1% energy) match global leader 77.6% of time vs bridge 22.4% |
| C73 | phonon_faraday | Perturbation reaches 22 basins (15.7% of nodes); peak sensitivity at step 350 (superposition maximum) |
| C74 | phonon_faraday | Spirit targets produce most flips (12/13); tech targets produce zero flips at any amplitude |
| C75 | phonon_faraday | KL-divergence gap=3 vs 4 peaks at step 272 then reconverges — basin information is transient |
| C76 | phonon_faraday | Gap parameter has single binary phase transition at gap=3→4: 2 basins across 10 gaps |
| C77 | phonon_faraday | Entropy plateau at d=5.0 spans 235 steps (47% of simulation) at H=0.976 |
| C78 | phonon_faraday | High damping entropy inversion: d≥25 peaks then declines 40–54%; speed/depth inversely related |
| C79 | phonon_faraday | Christ[2] injection singularity: removing christ injection breaks christic lock at d=20–40 |
| C80 | phonon_faraday | Christ–christic edge singularity: severing the single edge destroys dead zone lock |
| C81 | phonon_faraday | Mega-hub irrelevance: cutting 337 combined degree of mega-hub connections cannot break lock |
| C82 | phonon_faraday | Phase gating necessity: removing group distinctions breaks christic dominance |
| C83 | phonon_faraday | Heartbeat knockout (omega=0): metatron[9] captures all damping values universally |
| C84 | phonon_faraday | Viscous retention threshold: deepViscosity=1.5 breaks christic lock |
| C85 | phonon_faraday | Three-factor mechanism: injection adjacency + phase gating + viscous retention (Q2 RESOLVED) |
| C86 | phonon_faraday | Competitive bistability d=18.0–19.0: christic/ch.hayes alternate, lock-in d≥19.1 |
| C87 | phonon_faraday | Emergent attractor: christic first leads step 185/500 after 15 lead changes |
| C88 | phonon_faraday | Uniform spirit half-life: identical across 17 spirit nodes (topological not dynamical) |
| C89 | phonon_faraday | Half-adder partial generalization: distinguished basins at d≤5.5 and d≥30, dead zone d=6–29 (Q5 RESOLVED) |
| C90 | phonon_faraday | Damping-parametric truth table: A+B output shifts across dampings |
| C91 | phonon_faraday | Sharp collapse boundary at d≈5.75 with no gradual degradation |
| C92 | phonon_faraday | Absolute w0 dead zone: even w0=50 cannot rescue at d=10–20 |
| C93 | phonon_faraday | Orthogonal control: injection-based B-encodings breach w0 dead zone at d=10 |
| C94 | phonon_faraday | Four-channel info at d≤20; two channels at d≥30 (mass→0) |
| C95 | phonon_faraday | Partial full adder: 3 inputs → 3 basins at d=5.0; clock = asymmetric grail lock |
| C96 | phonon_faraday | Ghost-zone computation: distinct basins with mass→0 at d≥30 |
| C97 | phonon_faraday | Universal overriding: 11/11 non-standard groups shift basin from standard attractor |
| C98 | phonon_faraday | Damping-dependent group→basin mapping: 2–4 zones per overrider, sharp transitions |
| C99 | phonon_faraday | Spirit self-capture: 16/18 spirit nodes self-attract at d≤5 |
| C100 | phonon_faraday | High-damping spirit redirection: 6 bidirectional spirit pairs at d=20 |
| C101 | phonon_faraday | Cooperative emergence: 5/14 group×damping produce cooperative-only basins |
| C102 | phonon_faraday | Energy-stable group mapping: 9/12 combos stable across 6× energy range |
| C103 | phonon_faraday | 20-basin address space (4.3 bits) via injection group selection |
| C104 | phonon_faraday | Cross-group novelty: 2 mixture-only basins via constructive interference |

## Open Questions

| # | Domain | Question | Status |
|--:|--------|----------|--------|
| Q1 | phonon_faraday | Higher-order analog correction R² ceiling | ~~RESOLVED~~ |
| Q2 | phonon_faraday | Dead zone physics — why christic[22] traps | ~~RESOLVED~~ |
| Q3 | phonon_faraday | Clock optimization — optimal period/pulse | ~~RESOLVED~~ |
| Q4 | phonon_faraday | Cascade depth limit — architecture-dependent | ~~RESOLVED~~ |
| Q5 | phonon_faraday | Half-adder generalization across damping regimes | ~~RESOLVED~~ |
| Q6 | phonon_faraday | SR-latch third-state reproducibility | ~~RESOLVED~~ |
| Q7 | phonon_faraday | Temporal injection minimum distinguishing cadence | ~~RESOLVED~~ |
| Q8 | phonon_faraday | Dream afterstate — rest-phase basin drift | ~~RESOLVED~~ |
| Q9 | phonon_faraday | Stochastic injection basin entropy | ~~RESOLVED~~ |
| Q10 | phonon_faraday | Perturbation stability radius | ~~RESOLVED~~ |
| Q11 | phonon_faraday | Boundary cartography completeness | ~~RESOLVED~~ |
| Q12 | phonon_faraday | Symmetry-breaking group specificity | ~~RESOLVED~~ |

## Raw Audit Trail

15 individual proof packets from pre-domain era, preserved in `raw/`:

| File | Date | Source | Status |
|------|------|--------|--------|
| PP-2026-01-18-*-hold400-programs-bus-regime | 2026-01-18 | Manual | CANDIDATE |
| PP-2026-01-18-*-hold400-macro-outcomes-reversible | 2026-01-18 | Manual | CANDIDATE |
| PP-2026-01-18-*-lateCaptureTick-pass-position-drift | 2026-01-18 | Manual | CANDIDATE |
| PP-2026-01-18-*-repTransition-onset-t10-stable | 2026-01-18 | Manual | CANDIDATE |
| PP-2026-01-24-cogload-* | 2026-01-24 | Manual | CANDIDATE |
| PP-2026-01-24-dreamAfterstate-* | 2026-01-24 | Manual | CANDIDATE |
| PP-2026-01-24-latchIdentity-* | 2026-01-24 | Manual | CANDIDATE |
| PP-2026-01-24-phase311-16bc-* | 2026-01-24 | Manual | CANDIDATE |
| PP-2026-01-24-phase311-16l-* | 2026-01-24 | Manual | CANDIDATE |
| PP-2026-01-24-phase38-capLaw-* | 2026-01-24 | Manual | CANDIDATE |
| PP-2026-01-24-phase39-timeToFailure-* | 2026-01-24 | Manual | CANDIDATE |
| PP-2026-01-24-psiResonanceA-* | 2026-01-24 | Manual | CANDIDATE |
| PP-2026-01-25-cogload-damping-boundary-* | 2026-01-25 | Manual | CANDIDATE |
| PP-2026-02-08-cortex-*-040833-c_press | 2026-02-08 | Cortex | CANDIDATE |
| PP-2026-02-08-cortex-*-051904/055037-damping | 2026-02-08 | Cortex | CANDIDATE |

---

*Maintained by claim_compiler.py and rsi_engine.py. Last regenerated: 2026-02-10.*
