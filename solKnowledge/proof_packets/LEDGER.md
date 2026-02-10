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
| phonon_faraday | [phonon_faraday.md](domains/phonon_faraday.md) | 41 | 1 | 11,337 | 487 | 27 | 2026-02-10 |

**Totals:** 41 claims | 1 open question | 11,337 trials | 487 min compute

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

## Open Questions

| # | Domain | Question | Status |
|--:|--------|----------|--------|
| Q1 | phonon_faraday | Higher-order analog correction R² ceiling | ~~RESOLVED~~ |
| Q2 | phonon_faraday | Dead zone physics — why christic[22] traps | **PARTIAL** |
| Q3 | phonon_faraday | Clock optimization — optimal period/pulse | ~~RESOLVED~~ |
| Q4 | phonon_faraday | Cascade depth limit — architecture-dependent | ~~RESOLVED~~ |
| Q5 | phonon_faraday | Half-adder generalization across damping regimes | OPEN |
| Q6 | phonon_faraday | SR-latch third-state reproducibility | ~~RESOLVED~~ |
| Q7 | phonon_faraday | Temporal injection minimum distinguishing cadence | OPEN |
| Q8 | phonon_faraday | Dream afterstate — rest-phase basin drift | OPEN |

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
