# **SOL Research Note — Phase 3.11 “Temporal Packet → Bus Broadcast Protocol”**

**Working title:** *3.11 — From Threshold Ridge to Handshaked Bus Protocol (16m–16x; 16y queued)*  
 **Date range:** Jan 11–12, 2026 (America/New\_York)

## **Objective**

Convert the observed “temporal packet becomes structured bus broadcast” phenomenon into:

1. a repeatable **encoding/readout protocol**

2. a **boundary/robustness spec** (environment sensitivity)

3. instrumentation and workflow guardrails for apples-to-apples comparisons

## **Key concepts (current working theory)**

* The SOL manifold performs **space → time compilation**: distributed/simultaneous pulses become ordered bus events.

* The “memory” relevant for AI readout is a **time-structured broadcast window**, not static persistence.

* System appears **multistage**:

  * Stage 1 arbitration timing shifts with damping

  * Stage 2 handshake stabilizes dual-rail engagement

  * Stage 3 receiver-rail stitching (89→79) may be part of stabilization

## **Canonical bus rails**

Mirrored broadcast legs:

* 114→89 and 114→79

* 136→89 and 136→79  
   High symmetry in successful regimes suggests coherent broadcast, not random flux.

## **Cross-coupler (“tertiary connection”)**

* Only consistent crosslink detected: **89→79**

* Port-to-port links do not appear (114↔136 remain zero)

* 89→79 correlates strongly with 114 rail peak activity (suggesting receiver-side coupling)

## **Protocol v1: Handshaked packet primitive (from 16w)**

**Fixed parameters (winning cell):**

* baseAmpB=4.0 (114), baseAmpD=5.75 (136)

* gain=22

* multB=1.144 → ampB0=100.672

* ampD=126.5

* ratioBD≈0.795826

* offset=+1 (136 tick0, 114 tick1)

* nudgeTick=14, nudgeMult=0.20 → ampB\_nudge=20.1344

**Observed timing rails (damp 4–5 regime):**

* 136 first at tick 13

* 114 follows at tick 15

* Δ=2 (deterministic in best cell)

## **Robustness findings (16x)**

Sweeps: pressC ∈ {1.6, 2.0, 2.4}, damp ∈ {4, 5, 6}, 16 reps per cell

* Handshake survives across all cells (no collapse)

* **Damping shifts timing regime**

  * damp 4: perfect Δ=2 rail in all pressC cases

  * damp 6: dominant Δ=4, plus occasional slow-follow (Δ 7–17) at higher pressC

* Interpretation: timing regime shift implies multistage internal computation rather than single continuous scaling.

## **16y queued: Adaptive handshake damp sweep (multistage probe)**

Purpose: test stability up to damp 20 by self-timing the handshake:

* detect arbiter tick \= first bus max-edge

* nudge 114 at arbiter+1 tick

This is intended to follow regime shifts automatically and reveal whether the system has discrete timing bands.

## **Apples-to-apples invariants (required in every summary going forward)**

Record explicitly:

* pressCUsed

* baseDampUsed / dampUsed

* dt

* busThreshUsed (if a threshold is being used anywhere)

* visibility state / hidden flag

* capLawHash (CAP-law version fingerprint)

## **Files produced/used this chat (high relevance)**

Data:

* `sol_phase311_16m_*_MASTER_summary.csv`, `*_MASTER_busTrace.csv`

* `sol_phase311_16v_*_MASTER_summary.csv`, `*_MASTER_busTrace.csv`

* `sol_phase311_16w_*_MASTER_summary.csv`, `*_MASTER_busTrace.csv`

* `sol_phase311_16x_*_MASTER_summary.csv`, `*_MASTER_busTrace.csv`  
   (plus 16n/16o/16p/16q/16r/16s/16t/16u runs captured earlier in the chat)

Code baselines/infrastructure:

* `SOLBaseline_v1.3.js` (baseline restore)

* `solPhase311_16m.js` (reference for 16m harness style)

* dashboard upgrades: `sol_dashboard_v3_7_2.html` (current)

## **Next actions (next chat)**

1. Load and analyze 16y summary \+ trace

2. Determine if arbiter timing is continuous drift vs discrete regime bands

3. Decide whether v1 protocol can be made fully self-clocked (adaptive handshake), or whether we need a “two-pulse” handshake / regime detector.

