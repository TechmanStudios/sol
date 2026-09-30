# SOL — FULL Narrative Report (solResearch notes, original sources)

Generated: 2026-01-16

Second-pass narrative for the solResearch notes: readable glue plus verbatim anchor excerpts, sourced directly from the original note MD files.

---

## Coverage

- Included: solResearchNote1.md, solResearchNote2.md

---

## Narrative (per note)

## solResearchNote1.md — Narrative

This entry is organized around: ## **SOL Research Note**
It proceeds through sections like: ### **1\) Background / Prior context**; ### **2\) Questions / Hypotheses**; ### **3\) Methods / Instrumentation**; ### **4\) Experiments included in this note (16-series)**; ### **5\) Results (quantitative)**; #### **5.1 Dual-bus broadcast is real and highly reliable above a small boundar….
The summary below is a stitched narrative derived from the file’s own headings and verbatim anchor lines. No content is pulled from the consolidated report.

**Narrative summary (derived):**
This file documents the work performed in that session, including tooling/harness changes, experiments executed, and the key conclusions that were locked in for the next phase. The anchor excerpts below capture the specific claims, parameter sweeps, and rules adopted.

**Anchor excerpts (verbatim):**
- * Baseline restore **every run** (belt \+ suspenders).
- * UI-neutral behavior (no camera/graph movement).
- * Deterministic filenames; outputs written as `MASTER_summary` \+ `MASTER_busTrace` (or events where relevant).
- * Timing treated as telemetry (lateByMs / missedTicks).
- * Two bus ports: **B=114** and **D=136**.
- * Two bus legs each: **→89** and **→79**.
- * Bus “ON” if **max(|flux\_to89|, |flux\_to79|) ≥ threshold** (threshold used here: **1.0**).
- * Measured: onset tick, peak abs flux, peak timing, and global flux metrics (sumAbsFlux, max-edge identity, concentration).
- * These 16k/16l datasets remained in **basin 82** for the entire trace window (see Results).
- This note summarizes the quantitative results for the following packs (key ones analyzed deeply: 16g, 16i, 16j, 16k, 16l).
- * **3.11.16g** — `gapSweep` (multiple packet patterns; varied gapTicks)
- * **3.11.16i** — `simulPulseAmpGapMap` (order, gap, amp scaling effects)
- * **3.11.16j** — `simulPulseRatioMap` (2D amplitude surface; stable region \+ low-corner failure)
- * **3.11.16k** — `lowAmpBoundaryScan` (tight scan of the low-amplitude corner)
- * **3.11.16l** — `ridgeScanOnsetDelay` (fine scan along the cliff; longer observation window)
- * **3.11.16m** — `fineBoundarySigmoidMap` (probability curve across the ridge; running at time of closeout)
- ### **5\) Results (quantitative)**
- Across the scanned parameter space, outcomes overwhelmingly fall into **both buses ON** (“bothOn”), except for a tightly-confined low-amplitude / specific-pattern region.
- **Derived outcomes:**
- * **bothOn:** 174
- * **none:** 6
- * **Failures only occurred for `RR_ABCD` at `gapTicks=1`** (6/46 at that gap setting across packets).
- Interpretation: near threshold, the manifold is sensitive to packet structure; “gap=1” can be a destructive timing regime for certain sequences rather than always improving separability.
- * **bothOn:** 278
- * **none:** 9
- * **only136:** 1
- All non-bothOn outcomes occurred in one narrow condition:
- * **`B_then_D` with `gapTicks=0` and `secondAmpMult=1.0`:** **8/8 \= none**
- * **`B_then_D` with `gapTicks=0` and `secondAmpMult=1.5`:** **1 none, 1 only136**
- Interpretation: “simultaneous injection” is not commutative; **packet order is part of the code**, especially at low effective amplitude.
- **Outcomes:**
- * **bothOn:** 182
- * **(ampB=6, ampD=6):** **2 bothOn, 9 none, 1 only136**
- Interpretation: there is a real amplitude threshold; below it, packet order effects can produce one-sided or failed broadcasts.
- * **bothOn:** 244
- * **none:** 10
- * **only136:** 2
- * (4,4): 0/4 bothOn (4 none)
- * (4,5): 0/4 bothOn (4 none)
- * (4,6): 0/4 bothOn (2 none, 2 only136)
- Using per-tick “max edge” telemetry in 16k, dominant max-edge corridors included:
- ### **9\) Next steps**

**Artifacts mentioned (from this file):**
- /mnt/data/sol_phase311_16g_gapSweep_v1_2026-01-11T07-14-58-939Z_2026-01-11T07-36-37-298Z_MASTER_summary.csv
- /mnt/data/sol_phase311_16i_simulPulseAmpGapMap_v1_2026-01-11T16-55-59-158Z_2026-01-11T17-24-40-224Z_MASTER_busTrace.csv
- /mnt/data/sol_phase311_16i_simulPulseAmpGapMap_v1_2026-01-11T16-55-59-158Z_2026-01-11T17-24-40-224Z_MASTER_summary.csv
- /mnt/data/sol_phase311_16j_simulPulseRatioMap_v1_2026-01-11T17-48-01-398Z_2026-01-11T18-11-33-114Z_MASTER_busTrace.csv
- /mnt/data/sol_phase311_16j_simulPulseRatioMap_v1_2026-01-11T17-48-01-398Z_2026-01-11T18-11-33-114Z_MASTER_summary.csv
- /mnt/data/sol_phase311_16k_lowAmpBoundaryScan_v1_2026-01-11T18-32-24-962Z_2026-01-11T18-58-39-166Z_MASTER_busTrace.csv
- /mnt/data/sol_phase311_16k_lowAmpBoundaryScan_v1_2026-01-11T18-32-24-962Z_2026-01-11T18-58-39-166Z_MASTER_summary.csv
- /mnt/data/sol_phase311_16l_ridgeScanOnsetDelay_v1_2026-01-11T19-18-35-047Z_2026-01-11T19-43-03-964Z_MASTER_busTrace.csv
- /mnt/data/sol_phase311_16l_ridgeScanOnsetDelay_v1_2026-01-11T19-18-35-047Z_2026-01-11T19-43-03-964Z_MASTER_summary.csv
- MASTER_busTrace.csv
- MASTER_summary.csv
- sol_phase311_16g_gapSweep_v1_2026-01-11T07-14-58-939Z_2026-01-11T07-36-37-298Z_MASTER_summary.csv
- sol_phase311_16i_simulPulseAmpGapMap_v1_2026-01-11T16-55-59-158Z_2026-01-11T17-24-40-224Z_MASTER_busTrace.csv
- sol_phase311_16i_simulPulseAmpGapMap_v1_2026-01-11T16-55-59-158Z_2026-01-11T17-24-40-224Z_MASTER_summary.csv
- sol_phase311_16j_simulPulseRatioMap_v1_2026-01-11T17-48-01-398Z_2026-01-11T18-11-33-114Z_MASTER_busTrace.csv
- sol_phase311_16j_simulPulseRatioMap_v1_2026-01-11T17-48-01-398Z_2026-01-11T18-11-33-114Z_MASTER_summary.csv
- sol_phase311_16k_lowAmpBoundaryScan_v1_2026-01-11T18-32-24-962Z_2026-01-11T18-58-39-166Z_MASTER_busTrace.csv
- sol_phase311_16k_lowAmpBoundaryScan_v1_2026-01-11T18-32-24-962Z_2026-01-11T18-58-39-166Z_MASTER_summary.csv
- sol_phase311_16l_ridgeScanOnsetDelay_v1_2026-01-11T19-18-35-047Z_2026-01-11T19-43-03-964Z_MASTER_busTrace.csv
- sol_phase311_16l_ridgeScanOnsetDelay_v1_2026-01-11T19-18-35-047Z_2026-01-11T19-43-03-964Z_MASTER_summary.csv

## solResearchNote2.md — Narrative

This entry is organized around: # **SOL Research Note — Phase 3.11 “Temporal Packet → Bus Broadcast Protocol”**
It proceeds through sections like: ## **Objective**; ## **Key concepts (current working theory)**; ## **Canonical bus rails**; ## **Cross-coupler (“tertiary connection”)**; ## **Protocol v1: Handshaked packet primitive (from 16w)**; ## **Robustness findings (16x)**.
The summary below is a stitched narrative derived from the file’s own headings and verbatim anchor lines. No content is pulled from the consolidated report.

**Narrative summary (derived):**
This file documents the work performed in that session, including tooling/harness changes, experiments executed, and the key conclusions that were locked in for the next phase. The anchor excerpts below capture the specific claims, parameter sweeps, and rules adopted.

**Anchor excerpts (verbatim):**
- * The SOL manifold performs **space → time compilation**: distributed/simultaneous pulses become ordered bus events.
- * The “memory” relevant for AI readout is a **time-structured broadcast window**, not static persistence.
- * System appears **multistage**:
- * Stage 1 arbitration timing shifts with damping
- * Stage 2 handshake stabilizes dual-rail engagement
- * Stage 3 receiver-rail stitching (89→79) may be part of stabilization
- * 114→89 and 114→79
- * 136→89 and 136→79
- * Only consistent crosslink detected: **89→79**
- * Port-to-port links do not appear (114↔136 remain zero)
- * 89→79 correlates strongly with 114 rail peak activity (suggesting receiver-side coupling)
- * baseAmpB=4.0 (114), baseAmpD=5.75 (136)
- * gain=22
- * multB=1.144 → ampB0=100.672
- * ampD=126.5
- * ratioBD≈0.795826
- * offset=+1 (136 tick0, 114 tick1)
- * nudgeTick=14, nudgeMult=0.20 → ampB\_nudge=20.1344
- * 136 first at tick 13
- * 114 follows at tick 15
- * Δ=2 (deterministic in best cell)
- ## **Robustness findings (16x)**
- * Handshake survives across all cells (no collapse)
- * **Damping shifts timing regime**
- * damp 4: perfect Δ=2 rail in all pressC cases
- * Interpretation: timing regime shift implies multistage internal computation rather than single continuous scaling.
- * detect arbiter tick \= first bus max-edge
- * nudge 114 at arbiter+1 tick
- * pressCUsed
- * baseDampUsed / dampUsed
- * busThreshUsed (if a threshold is being used anywhere)
- * visibility state / hidden flag
- * capLawHash (CAP-law version fingerprint)
- * `sol_phase311_16m_*_MASTER_summary.csv`, `*_MASTER_busTrace.csv`
- * `sol_phase311_16v_*_MASTER_summary.csv`, `*_MASTER_busTrace.csv`
- * `sol_phase311_16w_*_MASTER_summary.csv`, `*_MASTER_busTrace.csv`
- * `sol_phase311_16x_*_MASTER_summary.csv`, `*_MASTER_busTrace.csv`
- * `SOLBaseline_v1.3.js` (baseline restore)
- * dashboard upgrades: `sol_dashboard_v3_7_2.html` (current)
- * damp 6: dominant Δ=4, plus occasional slow-follow (Δ 7–17) at higher pressC
- **Working title:** *3.11 — From Threshold Ridge to Handshaked Bus Protocol (16m–16x; 16y queued)*
- ## **16y queued: Adaptive handshake damp sweep (multistage probe)**

**Artifacts mentioned (from this file):**
- *_MASTER_busTrace.csv
- sol_dashboard_v3_7_2.html
- sol_phase311_16m_*_MASTER_summary.csv
- sol_phase311_16v_*_MASTER_summary.csv
- sol_phase311_16w_*_MASTER_summary.csv
- sol_phase311_16x_*_MASTER_summary.csv
