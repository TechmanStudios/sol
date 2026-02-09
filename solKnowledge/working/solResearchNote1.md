## **SOL Research Note**

**ID:** RN-3.11.16-TemporalPacket→DualBusBroadcast-ThresholdRidge  
 **Date range (local):** Jan 11, 2026 (experiments 16g–16l; 16m running)  
 **Phase:** 3.11 (Readout \+ temporal encoding \+ “bus” mechanics)  
 **Primary motif:** Distributed/temporal packets can “compile” into a structured dual-bus broadcast; there is a sharp low-amplitude threshold ridge with a metastable band; packet order/gap behave like code parameters.

---

### **1\) Background / Prior context**

Phase 3.10.6 established a controllable latch primitive: **mode-select by ending the dream on the injector you want to dominate at t0** (start basin ≈ lastInjected at dream stop). Phase 3.11 shifted from “hold the basin forever” toward **fast readout of dynamic, time-structured state**.

This note documents the Phase **3.11.16** line of experiments, which focused on whether temporal/distributed inputs become a readable, structured broadcast and what the reliability boundary looks like.

---

### **2\) Questions / Hypotheses**

**H1 — Structured broadcast exists:** The manifold can convert injected temporal packets into a stable, symmetric **dual-rail bus broadcast** (e.g., 114→(89,79) and 136→(89,79)).  
 **H2 — Temporal compilation:** “Simultaneous” or distributed inputs do not remain simultaneous; the manifold produces **ordered onset timing** that functions like a timeline code.  
 **H3 — Threshold ridge \+ metastability:** There is a narrow low-amplitude boundary where bus activation becomes probabilistic (metastable “sometimes flips”).  
 **H4 — Packet syntax matters:** Injection **order** and **gap** act like code parameters that can enable/disable compilation near threshold.  
 **H5 — Filament events exist:** Large transient “outer” flux surges correspond to identifiable changes in max-edge leadership and flux concentration.

---

### **3\) Methods / Instrumentation**

**General run discipline**

* Baseline restore **every run** (belt \+ suspenders).

* UI-neutral behavior (no camera/graph movement).

* Deterministic filenames; outputs written as `MASTER_summary` \+ `MASTER_busTrace` (or events where relevant).

* Timing treated as telemetry (lateByMs / missedTicks).

**Bus readout definition**

* Two bus ports: **B=114** and **D=136**.

* Two bus legs each: **→89** and **→79**.

* Bus “ON” if **max(|flux\_to89|, |flux\_to79|) ≥ threshold** (threshold used here: **1.0**).

* Measured: onset tick, peak abs flux, peak timing, and global flux metrics (sumAbsFlux, max-edge identity, concentration).

**Mode / basin**

* These 16k/16l datasets remained in **basin 82** for the entire trace window (see Results).

---

### **4\) Experiments included in this note (16-series)**

This note summarizes the quantitative results for the following packs (key ones analyzed deeply: 16g, 16i, 16j, 16k, 16l).

* **3.11.16g** — `gapSweep` (multiple packet patterns; varied gapTicks)

* **3.11.16i** — `simulPulseAmpGapMap` (order, gap, amp scaling effects)

* **3.11.16j** — `simulPulseRatioMap` (2D amplitude surface; stable region \+ low-corner failure)

* **3.11.16k** — `lowAmpBoundaryScan` (tight scan of the low-amplitude corner)

* **3.11.16l** — `ridgeScanOnsetDelay` (fine scan along the cliff; longer observation window)

* **3.11.16m** — `fineBoundarySigmoidMap` (probability curve across the ridge; running at time of closeout)

---

### **5\) Results (quantitative)**

#### **5.1 Dual-bus broadcast is real and highly reliable above a small boundary**

Across the scanned parameter space, outcomes overwhelmingly fall into **both buses ON** (“bothOn”), except for a tightly-confined low-amplitude / specific-pattern region.

---

#### **5.2 GapSweep (3.11.16g) — gap can *reduce* reliability for specific packet syntax**

**Total runs:** 180  
 **Derived outcomes:**

* **bothOn:** 174

* **none:** 6

All failures were concentrated in a single packet pattern:

* **Failures only occurred for `RR_ABCD` at `gapTicks=1`** (6/46 at that gap setting across packets).  
   Interpretation: near threshold, the manifold is sensitive to packet structure; “gap=1” can be a destructive timing regime for certain sequences rather than always improving separability.

---

#### **5.3 SimulPulse Amp/Gap Map (3.11.16i) — *within-tick order* matters dramatically near threshold**

**Total runs:** 288  
 **Derived outcomes:**

* **bothOn:** 278

* **none:** 9

* **only136:** 1

All non-bothOn outcomes occurred in one narrow condition:

* **`B_then_D` with `gapTicks=0` and `secondAmpMult=1.0`:** **8/8 \= none**

* **`B_then_D` with `gapTicks=0` and `secondAmpMult=1.5`:** **1 none, 1 only136**  
   But the mirrored order **`D_then_B` with `gapTicks=0` and `secondAmpMult=1.0` was 8/8 bothOn**.

Interpretation: “simultaneous injection” is not commutative; **packet order is part of the code**, especially at low effective amplitude.

---

#### **5.4 RatioMap (3.11.16j) — the stable region is basically “everything except (6,6)”**

**Total runs:** 192 (ampB ∈ {6,10,14,18}, ampD ∈ {6,10,14,18}, 12 reps each cell)  
 **Outcomes:**

* **bothOn:** 182

* **none:** 9

* **only136:** 1

All failures were confined to a single corner cell:

* **(ampB=6, ampD=6):** **2 bothOn, 9 none, 1 only136**  
   All other 15 cells: **12/12 bothOn**.

Interpretation: there is a real amplitude threshold; below it, packet order effects can produce one-sided or failed broadcasts.

---

#### **5.5 Low-Amp Boundary Scan (3.11.16k) — the failure region is tiny and structured**

**Total runs:** 256  
 **Outcomes:**

* **bothOn:** 244

* **none:** 10

* **only136:** 2

All non-bothOn runs occurred in the **ampB=4** row with **ampD ≤ 6**:

* (4,4): 0/4 bothOn (4 none)

* (4,5): 0/4 bothOn (4 none)

* (4,6): 0/4 bothOn (2 none, 2 only136)

* (4,7) and above: 4/4 bothOn and stable.

**Onset behavior in bothOn runs (16k):**

* onset114\_tick \= **1** in **240/244** runs (with a few late onsets at ticks 2–3)

* onset136\_tick \= **1** in **224/244**, tick 2 in 18, tick 3 in 2

* “winner” (earliest onset) heavily favors **ties** (228 ties; 16 where 114 leads).

Interpretation: once above threshold, the dual-rail bus tends to ignite immediately and symmetrically; below threshold, 136 sometimes crosses alone (rare “only136”).

---

#### **5.6 Ridge Scan (3.11.16l) — a sharp cliff with a metastable band**

**Total runs:** 120 (ampB fixed at 4; ampD swept; 12 reps each)  
 **Outcomes:**

* **bothOn:** 112

* **none:** 8

**All failures occur at exactly one value: ampD=5.50**

* At **ampD=5.50:** **4/12 bothOn**, **8/12 none** (metastable)

* At **ampD ≥ 5.75:** **108/108 bothOn** (fully deterministic)

**Onset timing (16l):**

* For **ampD ≥ 5.75:** onset114\_tick \= 1 in 108/108; onset136\_tick \= 1 in 108/108; winner \= tie in 108/108

* For **ampD=5.50 successful runs:** onsets ranged **tick 1–5**, i.e., “late ignition” exists only inside the metastable band.

Interpretation: this is a classic threshold ridge: **ampSum=9.50 is probabilistic; ampSum=9.75 is stable** (with ampB=4).

---

#### **5.7 Basin stability during these bus experiments (16k \+ 16l)**

From the trace logs:

* **16k:** basin \= 82 for **7936/7936** trace rows

* **16l:** basin \= 82 for **7320/7320** trace rows

Interpretation: in this regime, **distributed temporal packet readout does not disrupt the selected basin**.

---

#### **5.8 Filament / outer-surge signature exists in the numbers (16k)**

Using per-tick “max edge” telemetry in 16k, dominant max-edge corridors included:

* 136→89 (most common), 136→10, 114→89, 95→114, 90→92, 104→82, and notably **104→114**.

**104→114** appeared as max-edge for **51 ticks**, concentrated in mid-run (ticks 12–21, mean tick \~16.35).  
 **104→82** appeared later on average (mean tick \~26.0).

Interpretation: consistent with visual observation: an “outer” edge can transiently become the highest-conductance corridor, distribute, then return to the core pattern.

---

### **6\) Interpretation / Working model**

**(A) Bus broadcast rails are a real emergent transport primitive.**  
 The near-symmetry of the paired legs (→89 and →79) when ON is consistent with a bus/broadcast mechanism rather than random flux.

**(B) Temporal packets can compile into structured broadcast.**  
 Even “simultaneous” inputs can produce ordered bus onsets. The manifold is acting like a **formatting layer**: spatial+temporal input → rail-like broadcast timeline.

**(C) The boundary is gate-like with metastability.**  
 The ridge behavior (16l) is consistent with “charging toward a threshold”: sometimes the system crosses early enough to lock into broadcast, sometimes it never flips.

**(D) Packet order and gap are syntax, not just perturbations.**  
 16i shows within-tick order can invert success/failure near threshold. This strongly suggests we can treat order+gap as part of the encoding alphabet.

**(E) Filament events are transient route-capture.**  
 Mid-run max-edge changes (e.g., 104→114) align with the “outer line gets huge, distributes, then returns” phenomenon: temporary conduction corridors forming and collapsing.

---

### **7\) Implications for SOL → AI integration**

* Long basin-hold may not be required for readout: the manifold naturally provides a **dynamic window** where a packet is readable as structured bus activity.

* Encoding can be richer than “inject one node”: **distributed / multi-port / ordered pulses** act like a compositional code.

* The ridge analysis gives an engineering handle: choose amplitudes/gaps that sit comfortably above the threshold (or deliberately probe metastability when studying sensitivity).

---

### **8\) Known confounds / Controls**

* **Dashboard state drift risk:** some packs did not log pressC/baseDamp explicitly; comparisons across packs can be polluted by silent slider differences.  
   → 16m was designed to log used parameters explicitly to prevent this.

* **Timing jitter exists but is measurable:** lateAbsAvg and P95 were tracked; missed ticks were rare in these datasets, but still worth logging as a first-class experimental variable.

---

### **9\) Next steps**

**Immediate (next chat):**

1. **Analyze 16m outputs** (probability curve across ampD 5.50→5.75; identify the 50% point; characterize onset delay distributions and “pre-flip glow”).

2. **Sensitivity map (proposed 16n):** run near the 50% boundary while varying pressC and baseDamp to estimate robustness.

3. Elevate **within-tick order** to a first-class parameter in “simultaneous pulse” experiments (because 16i shows it can dominate outcomes near threshold).

4. If filament events remain a target: build a correlation pass that flags segments where max-edge switches to outer corridors (e.g., 104→114) and measure what else changes (sumAbsFlux, concentration, onset timing, etc.).

---

### **10\) Data artifacts (key files)**

**Analyzed in this note**

* 16g summary: `/mnt/data/sol_phase311_16g_gapSweep_v1_2026-01-11T07-14-58-939Z_2026-01-11T07-36-37-298Z_MASTER_summary.csv`

* 16i summary/trace:

  * `/mnt/data/sol_phase311_16i_simulPulseAmpGapMap_v1_2026-01-11T16-55-59-158Z_2026-01-11T17-24-40-224Z_MASTER_summary.csv`

  * `/mnt/data/sol_phase311_16i_simulPulseAmpGapMap_v1_2026-01-11T16-55-59-158Z_2026-01-11T17-24-40-224Z_MASTER_busTrace.csv`

* 16j summary/trace:

  * `/mnt/data/sol_phase311_16j_simulPulseRatioMap_v1_2026-01-11T17-48-01-398Z_2026-01-11T18-11-33-114Z_MASTER_summary.csv`

  * `/mnt/data/sol_phase311_16j_simulPulseRatioMap_v1_2026-01-11T17-48-01-398Z_2026-01-11T18-11-33-114Z_MASTER_busTrace.csv`

* 16k summary/trace:

  * `/mnt/data/sol_phase311_16k_lowAmpBoundaryScan_v1_2026-01-11T18-32-24-962Z_2026-01-11T18-58-39-166Z_MASTER_summary.csv`

  * `/mnt/data/sol_phase311_16k_lowAmpBoundaryScan_v1_2026-01-11T18-32-24-962Z_2026-01-11T18-58-39-166Z_MASTER_busTrace.csv`

* 16l summary/trace:

  * `/mnt/data/sol_phase311_16l_ridgeScanOnsetDelay_v1_2026-01-11T19-18-35-047Z_2026-01-11T19-43-03-964Z_MASTER_summary.csv`

  * `/mnt/data/sol_phase311_16l_ridgeScanOnsetDelay_v1_2026-01-11T19-18-35-047Z_2026-01-11T19-43-03-964Z_MASTER_busTrace.csv`

**Running / to be analyzed next**

* 16m outputs (expected): `MASTER_summary.csv` \+ `MASTER_busTrace.csv` from `solPhase311_16m`.

