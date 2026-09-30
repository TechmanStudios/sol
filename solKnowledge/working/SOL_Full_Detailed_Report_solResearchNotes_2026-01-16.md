# SOL — FULL Detailed Report (solResearch notes, original sources)

Generated: 2026-01-16

This report is generated directly from the original `solArchive/MD/solResearchNote1.md` and `solArchive/MD/solResearchNote2.md` files.

---

## Notes coverage

- Included: solResearchNote1.md, solResearchNote2.md

---

## Per-note extracted detail

## solResearchNote1.md — ## **SOL Research Note**

### Structure (headings)
- ## **SOL Research Note**
- ### **1\) Background / Prior context**
- ### **2\) Questions / Hypotheses**
- ### **3\) Methods / Instrumentation**
- ### **4\) Experiments included in this note (16-series)**
- ### **5\) Results (quantitative)**
- #### **5.1 Dual-bus broadcast is real and highly reliable above a small boundary**
- #### **5.2 GapSweep (3.11.16g) — gap can *reduce* reliability for specific packet syntax**
- #### **5.3 SimulPulse Amp/Gap Map (3.11.16i) — *within-tick order* matters dramatically near threshold**
- #### **5.4 RatioMap (3.11.16j) — the stable region is basically “everything except (6,6)”**
- #### **5.5 Low-Amp Boundary Scan (3.11.16k) — the failure region is tiny and structured**
- #### **5.6 Ridge Scan (3.11.16l) — a sharp cliff with a metastable band**
- #### **5.7 Basin stability during these bus experiments (16k \+ 16l)**
- #### **5.8 Filament / outer-surge signature exists in the numbers (16k)**
- ### **6\) Interpretation / Working model**
- ### **7\) Implications for SOL → AI integration**
- ### **8\) Known confounds / Controls**
- ### **9\) Next steps**
- ### **10\) Data artifacts (key files)**

### Extracted key points (verbatim lines)
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
- * (4,7) and above: 4/4 bothOn and stable.
- * onset114\_tick \= **1** in **240/244** runs (with a few late onsets at ticks 2–3)
- * onset136\_tick \= **1** in **224/244**, tick 2 in 18, tick 3 in 2
- * “winner” (earliest onset) heavily favors **ties** (228 ties; 16 where 114 leads).
- Interpretation: once above threshold, the dual-rail bus tends to ignite immediately and symmetrically; below threshold, 136 sometimes crosses alone (rare “only136”).
- * **bothOn:** 112
- * **none:** 8
- * At **ampD=5.50:** **4/12 bothOn**, **8/12 none** (metastable)
- * At **ampD ≥ 5.75:** **108/108 bothOn** (fully deterministic)
- * For **ampD ≥ 5.75:** onset114\_tick \= 1 in 108/108; onset136\_tick \= 1 in 108/108; winner \= tie in 108/108
- * For **ampD=5.50 successful runs:** onsets ranged **tick 1–5**, i.e., “late ignition” exists only inside the metastable band.
- Interpretation: this is a classic threshold ridge: **ampSum=9.50 is probabilistic; ampSum=9.75 is stable** (with ampB=4).
- * **16k:** basin \= 82 for **7936/7936** trace rows
- * **16l:** basin \= 82 for **7320/7320** trace rows
- Interpretation: in this regime, **distributed temporal packet readout does not disrupt the selected basin**.
- * 136→89 (most common), 136→10, 114→89, 95→114, 90→92, 104→82, and notably **104→114**.
- Interpretation: consistent with visual observation: an “outer” edge can transiently become the highest-conductance corridor, distribute, then return to the core pattern.
- ### **6\) Interpretation / Working model**
- * Long basin-hold may not be required for readout: the manifold naturally provides a **dynamic window** where a packet is readable as structured bus activity.
- * Encoding can be richer than “inject one node”: **distributed / multi-port / ordered pulses** act like a compositional code.

### Errors / fixes captured
- Using per-tick “max edge” telemetry in 16k, dominant max-edge corridors included:

### Artifacts mentioned
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

### Next steps cues captured
- ### **9\) Next steps**

## solResearchNote2.md — # **SOL Research Note — Phase 3.11 “Temporal Packet → Bus Broadcast Protocol”**

### Structure (headings)
- # **SOL Research Note — Phase 3.11 “Temporal Packet → Bus Broadcast Protocol”**
- ## **Objective**
- ## **Key concepts (current working theory)**
- ## **Canonical bus rails**
- ## **Cross-coupler (“tertiary connection”)**
- ## **Protocol v1: Handshaked packet primitive (from 16w)**
- ## **Robustness findings (16x)**
- ## **16y queued: Adaptive handshake damp sweep (multistage probe)**
- ## **Apples-to-apples invariants (required in every summary going forward)**
- ## **Files produced/used this chat (high relevance)**
- ## **Next actions (next chat)**

### Extracted key points (verbatim lines)
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

### Errors / fixes captured
- * damp 6: dominant Δ=4, plus occasional slow-follow (Δ 7–17) at higher pressC

### Scripts / harness notes captured
- * `solPhase311_16m.js` (reference for 16m harness style)

### Artifacts mentioned
- *_MASTER_busTrace.csv
- sol_dashboard_v3_7_2.html
- sol_phase311_16m_*_MASTER_summary.csv
- sol_phase311_16v_*_MASTER_summary.csv
- sol_phase311_16w_*_MASTER_summary.csv
- sol_phase311_16x_*_MASTER_summary.csv

### Next steps cues captured
- **Working title:** *3.11 — From Threshold Ridge to Handshaked Bus Protocol (16m–16x; 16y queued)*
- ## **16y queued: Adaptive handshake damp sweep (multistage probe)**
