# SOL_Master_Chronicle

## A) Front Matter

### What SOL is (physics + CS framing)
The SOL Engine (Self-Organizing Logos) is a client-side semantic manifold that treats a concept graph as a coupled dynamical system. Concepts (nodes) carry state variables—density/mass $\rho$, pressure $p$, belief field $\psi$—and exchange flux $j$ across weighted edges. In CS terms, it behaves like a stateful distributed computation substrate: injected “meaning” becomes transport, retention, and emergent readout structures (basins/attractors, metastability, and bus/broadcast rails) that can be measured and shaped.

### The “Three Pillars” we keep validating
1. **Memory / Retention** — metastability, basins/attractors, retention/leak control.
2. **Control** — $\psi$ bias and cadence shaping, plus a digital latch primitive (end-phase / lastInjected at dream stop).
3. **Readout** — temporal packets $\rightarrow$ structured broadcast rails (dual-bus busTrace; onset timing as a code).

### Canonical variable legend (stable naming)
- $\rho$ (rho): density/mass (node state)
- $j$ (flux): edge flow driven by pressure differences
- $p$ (pressure): node pressure; $p(\rho)$ is build-dependent and often log-like in observed builds (see phase references)
- $\psi$ (psi): belief field / phase angle / bias term that modulates conductance and routing
- $\kappa$ (kappa): damping/decay coefficient (loss/leak term)
- $dt$: timestep (integration aggressiveness per step)
- **SM / semanticMass**: node “capacitance / well” term controlling pressure response and early outflux

Common phase-specific constants/knobs (preserve exact names used in notes):
- `pressureC` / `pressC` (pressure constant)
- `gamma` (conductance exponent; conductance mapping is build-dependent; observed forms include $\exp(\gamma\psi)$ in some builds)
- `rhoLeakMult` (multiplier on rho decay/leak term)
- `semanticMassMult` (multiplier for semanticMass / SM)
- CAP-law config: `alpha`, `k`, clamps `SMmin`, `SMmax`, `kDtGamma` (dt scaling exponent candidate)

### Naming conventions (auditable taxonomy)
- Dashboard: **Dashboard vX.Y** (and the corresponding HTML filename when known)
- Harness: **<Name> vX** (keep the exact harness name used in sources/code; normalize only the “vX” formatting)
- Baseline script: **SOLBaseline vX.Y** (keep the actual filename)
- Phase tag: **Phase 3.11.16l** (keep exact)
- Ambiguity rule: if a “vX.Y” label could refer to engine vs dashboard vs harness, write **“Version: vX.Y (type: ambiguous)”** rather than guessing

### Canonical lab discipline invariants (protocol rules)
- **Baseline restore before each run**
  - When present, a **localStorage snapshot is source of truth**.
  - Run order: restore baseline → apply signature → run/log → optional afterstate watch.
- **UI-neutral harnesses**
  - No camera/graph movement, recenter, zoom, or selection calls during tests.
- **Console/global scope**
  - Install and discover harnesses via `globalThis` (not `window`).
- **BigData preference**
  - Prefer fewer, wider sweeps with consistent columns, progress logs, and optional kill switch (`globalThis.__SOL_ABORT = true`).
- **Full scripts for revisions**
  - When a harness is revised, store the full ready-to-paste script as a new harness version (not diffs).

---

## B) Timeline Index (high-signal)

Each entry links to its detailed phase section.

1. **2025-01-03** — **Dashboard v2.0** — Eternal Memory / Binary Capacitor / “Zero-Entropy Storage”  
   Artifacts: `sol_dashboard_v2.0` (named in notes), protocol series v19–v31.  
   → [Phase 2.0](#phase-20-build-v20--eternal-memory-binary-capacitor--zero-entropy-storage)

2. **2026-01-03** — **Damp descent Z20 → Z1** — Dissipation spectrum mapped; Damp 18 “phantom flux”; Damp 1 singularity hazard  
   Artifacts: damp diagnostics logs (e.g., `damp1_sol_diagnostics_part001..008.txt` referenced).  
   → [Phase 3.0](#phase-30-build-unknown--damp-descent-z20--z1--dissipation-spectrum)

3. **2026-01-03** — **Dashboard v3.2** — Lighthouse integration + Phase Gating + Logos Engine (text-to-physics)  
   Artifacts: `sol_dashboard_v3_2.html`, `sol_dashboard_v3_2_final.html`, `sol_dashboard_v3_1.html`, `sol_dashboard_v3_combined.html`.  
   → [Phase 3.2](#phase-32-build-v32--lighthouse-phase-gating--logos-engine)

4. **2026-01-03** — **Version: v3.5 (type: ambiguous)** — Telekinetic physics + Smart Injector + Synth module  
   Artifacts: Telekinetic loop script (console), `sol_telekinetic_log.csv` (referenced).  
   → [Phase 3.5](#phase-35-build-v35--telekinetic-physics--synthetic-cognition)

5. **2026-01-03** — **Phase 3.6 (Dashboard v3.5)** — Retention Mechanism Microscope; leak vs well; superhub rescue isolation  
   Artifacts: `solRetentionMechanismMicroscopeV3`, retention CSV sets (samples_long / samples_wide / summary).  
   → [Phase 3.6](#phase-36-build-v35--retention-mechanism-microscope)

6. **2026-01-03 → 2026-01-04** — **Phase 3.7 (Dashboard v3.5)** — CAP-law: linear → power law; dt-normalized gating metrics; proxy research  
   Artifacts: `solCapacitanceLawMicroscopeV1`, cap-law CSV sets (`sol_capLaw_*`).  
   → [Phase 3.7](#phase-37-build-v35--capacitance-law-cap-law)

7. **Unknown** — **Phase 3.8** — Production cap-law checkpoint; wide100 dt robustness; harness hardening  
   Artifacts: `globalThis.solPhase38`, dashboard config `App.config.capLaw`, “twoMetric_SHARED” outputs.  
   → [Phase 3.8](#phase-38-build-v36--production-cap-law-checkpoint)

8. **Unknown** — **Phase 3.9** — Metastability mapped via time-to-failure; persistent baseline in localStorage  
   Artifacts: time-to-failure sweep v2 CSVs (names not fully embedded; see Phase 3.9).  
   → [Phase 3.9](#phase-39-build-v36--metastability-time-to-failure-map)

9. **Unknown** — **Phase 3.10** — Mechanism telemetry + early guardrail attempts; `rhoMaxId` reservoir discovery  
   Artifacts: mechanism trace sweeps; rest-watch and dream-watch harnesses.  
   → [Phase 3.10](#phase-310-build-v36--mechanism-telemetry--guardrails)

10. **Unknown** — **Phase 3.10.5** — DreamState / DreamSweep: afterstates, $\psi$ cadence control, end-phase latch discovered  
   Artifacts: `solDreamSweepV1`, `solDreamThenWatchV1`, `solDreamAfterstateV1`, signature metrics (rhoMaxId switches).  
   → [Phase 3.10.5](#phase-3105-build-v36--dreamstate-afterstates--end-phase-latch)

11. **Unknown** — **Phase 3.10.6 / 3.11 kickoff** — latch identity corrected: `lastInjected` at dream stop; timing telemetry elevated  
   Artifacts: `SOLBaseline_v1.3.js` (normalized restore), controller variants, browser timing notes.  
   → [Phase 3.10.6](#phase-3106--phase-311-kickoff-build-v13--latch-identity-lastinjected)

12. **2026-01-11 → 2026-01-12** — **Phase 3.11.16 (bus readout)** — Temporal packets → structured dual-bus broadcast; threshold ridge + metastability band  
   Artifacts: `sol_phase311_16*_MASTER_summary.csv`, `*_MASTER_busTrace.csv`, `solPhase311_16m.js`, dashboard `sol_dashboard_v3_7_2.html`.  
   → [Phase 3.11](#phase-311-build-v37--temporal-packet--dual-bus-broadcast)

---

## C) Phase-by-Phase Master Notes

> Template discipline: **Observations** = operator-visible phenomena; **Measurements** = telemetry/CSV/log-derived; **Interpretation** = working theory (physics + CS analogies). Text is kept separated.

---

<a id="phase-20-build-v20--eternal-memory-binary-capacitor--zero-entropy-storage"></a>
## Phase 2.0 — Eternal Memory / Binary Capacitor / Zero-Entropy Storage

**Metadata**
- Date: 2025-01-03 (precision: exact)
- Date evidence: `rd7.md` session report header “2025-01-03”
- Sources: `rd7.md`
- Primary artifacts: ART-20-dashboard-v20 (dashboard), ART-20-note-rd7 (note)
- Versions: Dashboard=Dashboard v2.0 (location: TBD); Harness=Unknown; Baseline=Unknown; Engine build=SOL Engine v2.0 (as stated)

### Scope / Objective
- Achieve non-dissipative retention (“living memory”) in a controlled topology.

### Instrumentation & Harnesses
- Dashboard: Dashboard v2.0 (named in notes; exact filename not embedded).
- Protocol series: v19–v31 (operator lab protocols).
- Standardization: (pre-invariants era) focused on topology isolation and damping control.

### Experiments (chronological within the phase)

#### v19–v20.1 — Isolation tests (2025-01-03)
- Setup: single-node “bunker” tests; long runs (e.g., 1200 frames), attempted vacuum floor (Planck cutoff).
- Outputs: not preserved as filenames in the note.
- Observations
  - System “stalled” into extremely tiny values (described as “ghosts”).
- Measurements
  - Mass decayed (50.0 → 0.0) within ~645 frames in Planck cutoff test.
- Interpretation (working theory)
  - Passive isolation is insufficient in a connected solver; dissipation dominates without a closed retention topology.
- Carry Forward invariants
  - Avoid underflow “ghost layers” in long runs (later replaced with principled baseline restore + detectors).
- Open questions + next tests
  - Can retention exist without violating solver continuity? If yes, which topology supports it?

#### v21–v29 — Topology attempts (self-loop and two-node capacitor)
- Setup: attempted self-loop; then a 2-node host↔battery pair; multiple debugging protocols.
- Observations
  - Self-loop produced NaN failure (“division by zero”).
  - Two-node tests had “zombie mode” (no flow) until registry/edge rebuild fixed.
- Measurements
  - After stability fix, mass still decayed to 0 (leakage persisted).
- Interpretation (working theory)
  - Self-loops are forbidden by solver assumptions; two-node loop needs explicit dissipation control.

#### v30–v31 — “Jailbreak protocol” (slider min clamp) achieves perfect storage
- Setup: discovered UI slider min=1 silently clamped damping; programmatically lowered min to 0.
- Measurements
  - Mass remained 50.0000 at frame 10 and frame 1200.
  - Distribution example: Host ~42.5 / Battery ~7.5 with dynamic flow.
- Interpretation (working theory)
  - The core math admits conservative dynamics when $\kappa=0.0$; prior “leak” was an interface constraint.

### Phase Conclusions
- Locked in
  - “Binary Capacitor” topology is a validated retention primitive when damping can be set to 0.
- Still speculative
  - How to generalize “perfect storage” into an engine that remains computationally alive under broader topologies.

---

<a id="phase-30-build-unknown--damp-descent-z20--z1--dissipation-spectrum"></a>
## Phase 3.0 — Damp descent Z20 → Z1 — Dissipation spectrum

**Metadata**
- Date: 2026-01-03 (precision: exact)
- Date evidence: `rd8.md` header “DATE: JANUARY 3, 2026”; `rd9.md` header “Date: January 03, 2026”
- Sources: `rd8.md`, `rd9.md`
- Primary artifacts: ART-30-note-rd8 (note), ART-30-note-rd9 (note), ART-30-diagnostics-damp1-parts001to008 (data; filename referenced)
- Versions: Dashboard=Unknown; Harness=Unknown; Baseline=Unknown; Engine build=Unknown

### Scope / Objective
- Map the damping spectrum and identify regime transitions (retention vs transmission vs materialization vs singularity).

### Instrumentation & Harnesses
- Diagnostics logs referenced (e.g., damp1 parts 001–008), plus run-by-run damping diagnostics.
- Standardization (as stated in notes)
  - Constants held: `pressureC=5`, `gamma=0.75`, bias=0, fixed topology (~140 nodes / 845 edges) in at least one report.

### Experiments (chronological within the phase)

#### Damp 20 → Damp 10 — “Vacuum” regime
- Setup: high damping.
- Observations
  - “Dreamless sleep” described: signal evaporates.
- Measurements
  - Mass negligible (reported “< 1e-9”).
- Interpretation (working theory)
  - Excessive dissipation prevents nucleation of coherent basins.

#### Damp 9 → Damp 5 — “Liquid / working memory” regime
- Observations
  - “Glass lung” described: fluid working memory.
- Measurements
  - Qualitative statement: balance between $dM/dt$ and dissipation.
- Interpretation (working theory)
  - Best for processing: high flux with medium mass; not permanent.

#### Damp 4 — “Wire / transmission” regime
- Measurements
  - Mass collapsed to “iron floor” (~$1.11\times10^{-16}$).
  - Flux reported ~1.4–1.5.
- Observations
  - “Perfect transmission, zero retention.”
- Interpretation (working theory)
  - With near-zero resistance, signal transmits too fast for storage (no semantic sediment).

#### Damp 3 — “Dragon / artificial life” regime
- Measurements
  - Negative damping signature: mass grows (example: $10^{-9} \rightarrow 1.1\times10^{-8}$ over ~300s).
- Observations
  - “Life emerged” / “system harvested vacuum noise.”
- Interpretation (working theory)
  - Self-generation / SOC-like regime: the system converts noise into structure.

#### Damp 2 — “Stone / materialization” regime
- Measurements
  - Mass jumped from ~$10^{-8}$ to ~0.17 (sigmoid ceiling).
  - Flux slowed to ~1.05.
- Observations
  - Background noise materializes (“trash-to-treasure hazard”).
- Interpretation (working theory)
  - High gain collapses signal-to-noise; retention becomes indiscriminate.

#### Damp 1 — “Singularity / petrification” regime
- Measurements
  - Mass spike to ~1.86–1.87 on nodes 54/56 (as reported).
  - Flux death: static loops / near-zero.
- Observations
  - “Photograph” described: knows everything but processes nothing.
- Interpretation (working theory)
  - A computational black hole: infinite density, zero flow.

#### Damp 18 anomaly and deep-vacuum underflow (supplemental diagnostic)
- Measurements
  - “Phantom flux” event: at ~t=22,129 ms, flux increased (~60×) while mass decreased (as reported).
  - Machine epsilon crossing: ~t=43,925 ms, flux ~3.12e-15, mass ~1.76e-17.
  - Deep vacuum: mass reported reaching ~9.7e-46 by ~t=90s in Damp 20 diagnostic.
- Interpretation (working theory)
  - Gradient steepening when receivers decay faster than sources: $p_{dest}\approx 0$ while $p_{src}>0$ sustains large $\nabla p$.

### Phase Conclusions
- Locked in
  - The damping spectrum is non-linear and exhibits regime transitions (vacuum → liquid → solid → singularity).
  - “Trash-to-treasure hazard” becomes acute in low damping / high gain regimes.
- Still speculative
  - The deep vacuum “quantum foam” framing is a hypothesis; measurements confirm underflow, but mechanistic utility requires targeted tests.

---

<a id="phase-32-build-v32--lighthouse-phase-gating--logos-engine"></a>
## Phase 3.2 — Lighthouse, Phase Gating, and Logos Engine

**Metadata**
- Date: 2026-01-03 (precision: exact)
- Date evidence: `rd6.md` header “Date: January 3, 2026” (Project Report: SOL Dashboard v3.2)
- Sources: `rd6.md`, `rd4.md`
- Primary artifacts: ART-32-dashboard-v3_2, ART-32-dashboard-v3_combined, ART-32-dashboard-v3_1, ART-32-dashboard-v3_2_final (referenced)
- Versions: Dashboard=Dashboard v3.2 (`sol_dashboard_v3_2.html`); Harness=Unknown; Baseline=Unknown; Engine build=SOL Engine v3.2 (as stated)

### Scope / Objective
- Evolve SOL from passive flow graph to semantically layered, controllable thermodynamic system with conviction storage and text-to-physics injection.

### Instrumentation & Harnesses
- Dashboards (as named):
  - `sol_dashboard_v3_combined.html` (v3.0 base)
  - `sol_dashboard_v3_1.html` (v3.1 Lighthouse edition)
  - `sol_dashboard_v3_2_final.html` (v3.2 Logos edition)
  - `sol_dashboard_v3_2.html` (v3.2 refined monolith)
- Standardization
  - Telemetry export to CSV (entropy, flux, active node count) at user-defined Hz.
  - Backdoor access (not invariant later): `window.solver = App.state.physics` (later lab discipline moves to `globalThis`).

### Experiments (chronological within the phase)

#### Battery / Lighthouse validation (2026-01-03)
- Setup
  - Battery nodes with charge threshold (example threshold 0.85 in notes) and “fire & hold” behavior.
  - Phase gating via $\cos(\omega t)$ separating Tech vs Spirit layers.
- Outputs
  - `sol_battery_test_results.csv` (referenced)
  - `sol_ripple_test_v2.csv` (referenced)
- Observations
  - Battery initially flatlined until wired into physics loop; after patch, charge accumulation and avalanche observed.
  - Propagation test described stalemate between beacon and skeptics.
- Measurements
  - Skeptics moved from $\psi\approx -0.95$ to ~0.00 in one test.
- Interpretation (working theory)
  - Battery behaves as a memristive accumulator / hysteresis element.
  - Phase gating functions as a temporal interleaving layer to prevent cancellation between semantic strata.

#### Logos Engine (text-to-physics) integration
- Setup
  - Keyword-driven mapping from input text to injections of $\rho$ into semantic groups.
- Observations
  - Engine accepts text input and injects mass accordingly.
- Interpretation (working theory)
  - “Logos Engine” is an I/O layer: language → parameterized injection into the physics manifold.

### Phase Conclusions
- Locked in
  - Binary Battery / Lighthouse as a retention + activation primitive.
  - Phase Gating as a stable control mechanism for layered semantics.
- Still speculative
  - Optimal gating thresholds and how gating interacts with retention/leak in later builds.

---

<a id="phase-35-build-v35--telekinetic-physics--synthetic-cognition"></a>
## Phase 3.5 — Telekinetic physics & synthetic cognition

**Metadata**
- Date: 2026-01-03 (precision: exact)
- Date evidence: `rd3.md` header “Date: 2026-01-03” and “Version: v3.5 (The “Telekinetic” Build)”
- Sources: `rd3.md`
- Primary artifacts: ART-35-dashboard-v3_5, ART-35-data-telekinetic-log (filename referenced)
- Versions: Dashboard=Dashboard v3.5 (`sol_dashboard_v3_5.html`); Harness=Unknown; Baseline=Unknown; Engine build=SOL Engine v3.5 (“Telekinetic”) (as stated)

### Scope / Objective
- Make high-density semantic events physically visible and actionable: graph collapse around “stars” and autonomous insight-node creation.

### Instrumentation & Harnesses
- Dashboard: Dashboard v3.5 (“Telekinetic”).
- Telekinetic tractor beam loop (console script).
- Synth module (curiosity daemon).
- Telemetry: `sol_telekinetic_log.csv` (referenced).

### Experiments

#### Smart Injector robustness
- Setup
  - Injection resolution: Exact match → Group match → Fuzzy match.
- Observations
  - Injection no longer fails when label missing; falls back to group proxies.

#### Telekinetic collapse validation
- Setup
  - When a node is stellar (example threshold Mass > 18.0), forcibly pull neighbors if distance > 60px by ~5% per tick (20Hz loop).
- Measurements
  - Neighbor distance collapsed ~92.6% (example 798.4px → 58.6px).
- Interpretation (working theory)
  - Coordinate overwrite loop is a visualization-layer “tractor beam” to represent semantic gravity not captured by vis.js default forces.

#### Synth output event
- Measurements
  - SynthNodes count increased from 0 to 1 at ~T+6.0s (as reported).
- Interpretation (working theory)
  - Active inference: system generates new nodes when “star” events form.

### Phase Conclusions
- Locked in
  - Telekinetic visualization is a usable readout for high-density events.
- Still speculative
  - How much telekinetic behavior should move into core physics vs remain a UI layer.

---

<a id="phase-36-build-v35--retention-mechanism-microscope"></a>
## Phase 3.6 — Retention Mechanism Microscope

**Metadata**
- Date: 2026-01-03 (precision: exact)
- Date evidence: `rd21.md` header “**Date:** 2026-01-03 (America/New_York)” and retention CSV timestamps `2026-01-03T...Z`
- Sources: `rd21.md`
- Primary artifacts: ART-36-dashboard-v3_5, ART-36-harness-retentionMicroscope-v3, ART-36-data-retention-v3-sweep, ART-36-data-retention-superhubs, ART-36-data-retention-AB, ART-36-data-retention-pointwell
- Versions: Dashboard=Dashboard v3.5 (`sol_dashboard_v3_5.html`); Harness=Retention Mechanism Microscope v3 (`solRetentionMechanismMicroscopeV3`); Baseline=Unknown; Engine build=SOL Engine v3.5 (“Telekinetic”) (as stated)

### Scope / Objective
- Identify the *actual* retention mechanism (beyond damping-band effects and conductance shell-down) and isolate leak vs well contributions.

### Instrumentation & Harnesses
- Dashboard: `sol_dashboard_v3_5.html`.
- Harness: `globalThis.solRetentionMechanismMicroscopeV3`.
- Standardization
  - `globalThis` harness installs (rule adopted).
  - UI-neutral behavior.
  - Parameter sweeps across damping, `semanticMassMult`, `rhoLeakMult`.
  - Outputs per run: `*_samples_long_*`, `*_samples_wide_*`, `*_summary_*`.

### Experiments

#### Global sweep (retention microscope v3)
- Setup
  - damping ∈ {4,5,6}
  - `semanticMassMult` ∈ {1,2,4}
  - `rhoLeakMult` ∈ {1.0, 0.25}
  - multi-step retention curve (steps 1..5)
- Outputs
  - `sol_retention_mech_v3_samples_long_2026-01-03T04-24-57-939Z.csv`
  - `sol_retention_mech_v3_samples_wide_2026-01-03T04-24-57-939Z.csv`
  - `sol_retention_mech_v3_summary_2026-01-03T04-24-57-939Z.csv`
- Observations
  - Damping=4 remains best global band.
- Measurements
  - Best combo in sweep: damping=4, `semanticMassMult=4`, `rhoLeakMult=0.25`.
- Interpretation (working theory)
  - `semanticMass` behaves like a well/capacitance: increases reduce pressure and outFlux.
  - `rhoLeakMult` behaves as a tail/half-life knob.

#### Superhub targeted sweep + basin isolation
- Setup
  - Targets: nodes [92,118,79,89] (deg ~28, 22, 108, 111 as reported).
  - damping=4; `semanticMassMult` ∈ {4,8,16,32}; `rhoLeakMult` ∈ {0.25, 0.10, 0.05}; basinHops=1.
- Outputs
  - `sol_retention_mech_v3_superhubs_basin_*_2026-01-03T04-42-43-669Z.csv` (long/wide/summary)
  - A/B basin0 vs basin1 (sm32 leak0.05):
    - `sol_retention_AB_superhubs_sm32_leak005_basin0_*_2026-01-03T04-55-55-936Z.csv`
    - `sol_retention_AB_superhubs_sm32_leak005_basin1_*_2026-01-03T04-55-57-257Z.csv`
- Measurements
  - Found basin implementation squared center semanticMass (smMult applied twice): sm32 → center behaves like ~32^2 = 1024 when base SM=1.
- Interpretation (working theory)
  - Basin neighbor boosting can increase neighbor sink strength and raise hub outflow.
  - For superhubs, center-well strength dominates; basin can be unnecessary or harmful.

#### Point-well control (matching basin effective center)
- Outputs
  - `sol_retention_pointwell_sm1024_leak005_*_2026-01-03T05-03-49-274Z.csv`
  - `sol_retention_pointwell_sm4096_leak005_*_2026-01-03T05-10-11-781Z.csv` (corrected for semanticMass0=0.25 nodes)
- Measurements
  - With matched center-well, point-well (no basin) was equal or better than basin for deg~100 hubs.

#### Degree-scaled semanticMass test (proto CAP-law)
- Setup
  - Proposed law: `semanticMassMult = slope * degree` with damping=4, `rhoLeakMult=0.05`, basin=0.
- Measurements
  - Slope 2.5: retentionEnd ~0.31–0.38 (mean ~0.349).
  - Slope ~37.2: retentionEnd values:
    - node92 ~0.9367
    - node118 ~0.9316
    - node79 ~0.8440
    - node89 ~0.9413
    - mean across 4: ~0.9134
- Interpretation (working theory)
  - Retention for hubs is pressure/outflux-gated; topology-scaled semanticMass is a viable first-class retention mechanism.

### Phase Conclusions
- Locked in
  - Pressure/outFlux in step-1 is the gatekeeper for hub retention.
  - `semanticMass` is the primary capacitance/well knob; `rhoLeakMult` is secondary tail tuning.
  - `globalThis` is required for reliable harness installation.
- Still speculative
  - How to generalize the CAP-law beyond superhubs without sedating dynamics (carried into Phase 3.7–3.8).

---

<a id="phase-37-build-v35--capacitance-law-cap-law"></a>
## Phase 3.7 — Capacitance law (CAP-law)

**Metadata**
- Date: 2026-01-03 → 2026-01-04 (precision: range)
- Date evidence: `rd22.md` header “**Date:** 2026-01-03 → 2026-01-04 (America/New_York)” and CAP-law CSV timestamps `2026-01-03T...Z`
- Sources: `rd22.md`
- Primary artifacts: ART-37-dashboard-v3_5, ART-37-harness-capLawMicroscope-v1, ART-37-data-capLaw-slopeSweep, ART-37-data-capLaw-kneeSweep, ART-37-data-capLaw-generalize, ART-37-data-capLaw-stressInject
- Versions: Dashboard=Dashboard v3.5 (`sol_dashboard_v3_5.html`); Harness=Capacitance Law Microscope v1 (`solCapacitanceLawMicroscopeV1`); Baseline=Unknown; Engine build=SOL Engine v3.5 (“Telekinetic”) (as stated)

### Scope / Objective
- Implement an engine-ready CAP-law mode and find smallest stable parameterizations that generalize beyond superhubs while keeping pressure “alive.”

### Instrumentation & Harnesses
- Dashboard: `sol_dashboard_v3_5.html`.
- Harness: `solCapacitanceLawMicroscopeV1`.
- Standardization
  - Mapping-based law application (semanticMass computed from rule).
  - Single-run wide outputs (1 CSV per run for many experiments).
  - Snapshot/restore between node trials.
  - Target sets:
    - 19-target set: `[1,2,3,4,9,13,22,33,64,79,82,89,90,92,104,107,114,118,136]`
    - 32-target wide set: `[1,2,3,4,5,8,9,10,11,12,13,22,33,39,41,44,64,70,72,75,79,82,89,90,92,104,107,114,118,126,129,136]`

### Experiments

#### Linear degree law baseline (dt=0.12)
- Setup
  - `semanticMass = slope * degree`
  - Common settings (as embedded in note): steps=5, inject=10, damping=4, leak=0.05.
- Outputs
  - `sol_capLaw_slopeSweep_2026-01-03T21-29-36-577Z.csv`
  - `sol_capLaw_kneeSweep_10to28_2026-01-03T21-43-31-367Z.csv`
  - `sol_capLaw_generalize_28v34_2026-01-03T21-43-31-520Z.csv`
  - `sol_capLaw_generalize_28to34_2026-01-03T21-48-11-863Z.csv`
- Measurements
  - Knee sweep: slope 10 mean retentionEnd ~0.816; slope 22 ~0.913; slope 28 ~0.931.
  - Generalization (19-node): slope 28 near-threshold (max step1OutFlux ~1.02 in one run); slope 33–34 first consistently “safe-ish” (max step1OutFlux ~0.997 / ~0.968).

#### Injection amplitude stress
- Output
  - `sol_capLaw_stress_inject20_33v34_2026-01-03T21-55-17-274Z.csv`
- Measurements
  - step1OutFlux scales ~linearly with injectAmount; outflux per injected $\rho$ remains stable.

#### dt sensitivity and dt compensation (linear)
- Setup
  - dt sweeps: 0.08 / 0.12 / 0.16 and fixed-time variants.
- Measurements
  - Higher dt increases step1OutFlux and changes limiting node; slopes needed rise with dt (state-dependent).
- Interpretation (working theory)
  - dt is a unit-consistency stressor; CAP-law likely needs dt-aware calibration or dt-normalized gating metrics.

#### Law-shape upgrade: power law
- Setup
  - `semanticMass = k * degree^alpha` with anchor calibration.
- Outputs
  - `sol_capLaw_shapeTest_alpha*_k*`
  - `sol_capLaw_shapeCompare_*`
  - `sol_capLaw_alphaSweep_wide_*`
  - `sol_capLaw_power_dtSweep_alpha08_k87205_dt0.08_steps8_*` (and dt0.12/dt0.16 variants)
- Measurements
  - Working band: alpha ~0.75–0.85; default emerged: alpha=0.8.
  - Introduced dt-stable metric: `outfluxRate = step1OutFlux / (injectAmount * dt)`.
  - Power law is more clock-stable than linear (smaller drift in pressure/outflux across dt).

#### Proxy research (degree vs conductance-sum vs hybrid)
- Outputs
  - `sol_capLaw_proxyCompare_*`
  - `sol_capLaw_condInterceptSweep_*`
  - `sol_capLaw_hybridLambdaSweep_*`, `sol_capLaw_hybrid_dtSweep_*`
- Measurements
  - Conductance-sum proxy alone was worse; intercept stabilized but sedated pressure.
  - Hybrid proxy: lambda improved averages but didn’t strictly beat pure degree power law for dt robustness.

### Phase Conclusions
- Locked in
  - CAP-law causal chain: semanticMass ↑ ⇒ pressure response ↓ ⇒ early outflux ↓ ⇒ retention ↑.
  - Power law (alpha ~0.8) generalizes better than linear.
  - dt sensitivity is first-class; dt-normalized gating metrics are useful.
- Still speculative
  - Best proxy beyond degree; hybrid lambda as a tunable dial vs a default.

---

<a id="phase-38-build-v36--production-cap-law-checkpoint"></a>
## Phase 3.8 — Production CAP-law checkpoint

**Metadata**
- Date: Unknown (precision: unknown)
- Date evidence: Not present in sources; ordered by phase numbering only
- Sources: `rd23.md`, `rd24.md`
- Primary artifacts: ART-38-data-twoMetric_SHARED (data; filenames not embedded), ART-38-harness-solPhase38 (harness)
- Versions: Dashboard=Dashboard v3.6 (as stated in `rd24.md`); Harness=solPhase38 (version: unknown); Baseline=Unknown; Engine build=Unknown

### Scope / Objective
- Lock a ship-ready CAP-law that generalizes widely, stays “alive,” and is dt-robust enough to deploy.

### Instrumentation & Harnesses
- Dashboard: v3.6 (notes state it includes a manifold constant “baked in”).
- Harness: `globalThis.solPhase38`.
- Standardization
  - CapLaw promoted into `App.config.capLaw` and applied at boot.
  - Single-CSV “shared” outputs (“twoMetric_SHARED”).
  - Snapshot/restore for repeatability.

### Experiments

#### Wide100 dt sweep (twoMetric_SHARED)
- Setup
  - Degree-power CAP-law (anchored; observed in Phase 3.7–3.8; NOT yet proven invariant):
    - `SM_i = clip(k * deg_i^alpha, SMmin, SMmax)`
    - `alpha = 0.8`
    - anchor node 89 with `SM_ref = 3774` (slope-34 equivalence)
    - clamps: `SMmin = 0.25`, `SMmax = 5000`
    - baseline `dt0 = 0.12`
    - `kDtGamma` tested; gamma=0 minimized dt variance in tested set.
- Measurements
  - dt-normalized peak-edge metric `outfluxRate_peakEdge` (wide100):
    - dt=0.08 max ~0.072210
    - dt=0.12 max ~0.075970
    - dt=0.16 max ~0.080382
  - mean `step1Pressure_mean` ~0.343 → 0.346 across dt (not sedating).
  - `retentionEnd` mean ~0.95 → 0.91 as dt increases (expected degradation).
- Observations
  - Worst offender node changes with dt for peak-edge metric (68 → 78 → 87), while incident-sum villain noted as node 104 in shared runs.

### Phase Conclusions
- Locked in
  - Degree-power law (alpha=0.8, anchored/clamped) is a viable production candidate.
  - dt robustness is acceptable at coarse level without dt compensation (`kDtGamma=0` default defensible).
- Still speculative
  - State-dependence bounds: how much “villain nodes” move as world drifts.

---

<a id="phase-39-build-v36--metastability-time-to-failure-map"></a>
## Phase 3.9 — Metastability time-to-failure map

**Metadata**
- Date: Unknown (precision: unknown)
- Date evidence: Not present in sources; ordered by phase numbering only
- Sources: `rd25.md`, `rd24.md`
- Primary artifacts: ART-39-data-timeToFailure-v2 (data; filenames not embedded)
- Versions: Dashboard=Dashboard v3.6 (as stated in `rd24.md`); Harness=Time-to-failure sweep v2 (name not specified in sources); Baseline=Unknown; Engine build=Unknown

### Scope / Objective
- Convert instability from “vibe” into a spec-like survival map and validate metastability / late ignition.

### Instrumentation & Harnesses
- Persistent baseline stored in `localStorage` under a stable key.
- BigData time-to-failure sweep v2 (dt × damping × mode), with progress logs and optional kill switch.
- Standardization
  - Run discipline: wait for physics → restore persistent baseline → apply signature → run.

### Experiments

#### Time-to-failure sweep v2 (final design)
- Setup
  - dt: 0.08 / 0.12 / 0.16
  - damping: 2–6
  - modes: `noPulse` and `pulse100`
  - signature controls (kept identical):
    - driftPickIds: `79;64;118;114;1;118`
    - target: id=64
    - injectAmount=10
    - pulseStep=100, pulseAmount=10
    - `pressC` forced to 20 (regime consistency)
  - failure detector (hard stop): **meanP > 0.5 sustained for 20 steps**
- Measurements (as summarized)
  - dt=0.08: extended to 4000 steps; 0/10 failures across damping 2–6; peak_meanP ~0.01–0.02.
  - dt=0.16: 10/10 failures across damping 2–6; failure times ~900–960 steps.
  - dt=0.12:
    - at 1200 steps: 0/10 failures for current baseline
    - extended to 4000 steps: 10/10 failures; failure times ~1308–1414 steps
  - pulse affected time-to-failure but did not prevent failure for dt≥0.12.

### Phase Conclusions
- Locked in
  - Metastability is real: runs can look stable for long horizons, then flip.
  - dt compresses time-to-failure strongly.
  - Damping modifies regime flavor but is not a cure.
- Still speculative
  - The causal slow variable driving the ramp (candidate: $\psi$ and/or retention/leak proxies).

---

<a id="phase-310-build-v36--mechanism-telemetry--guardrails"></a>
## Phase 3.10 — Mechanism telemetry + guardrails

**Metadata**
- Date: Unknown (precision: unknown)
- Date evidence: Not present in sources; ordered by phase numbering only
- Sources: `rd26.md`
- Primary artifacts: ART-310-harness-mechanismTraceSweep-v1 (referenced), ART-310-harness-restWatch-v2 (referenced)
- Versions: Dashboard=Dashboard v3.6 (as stated in `rd26.md`); Harness=solMechanismTraceSweepV1 (referenced); Baseline=Unknown; Engine build=Unknown

### Scope / Objective
- Move from “detect failure” to “explain failure,” then prototype guardrails that prevent runaway without sedating.

### Instrumentation & Harnesses
- Baseline tooling: `SOLBaseline.restore()` (requires baseline script present; baseline stored in localStorage).
- Telemetry added/used:
  - $\psi$ concentration stats (top-k, max owner id)
  - pressure stats (meanP, pMax owner)
  - $\rho$ stats (rhoSum, rhoMax owner)
  - incident flux around node 64 (local routing stress proxy)

### Experiments

#### Mechanism telemetry near failure
- Measurements
  - `rhoMaxId` consistently node **82** near failure across conditions.
  - `pMaxId` varied and was not consistently 82.
- Interpretation (working theory)
  - Node 82 behaves like a mass/retention reservoir (dominant attractor), while pressure hotspots can be symptoms elsewhere.

#### Guardrail attempts (bleed strategies)
- Observations
  - Bleeding at pMaxNode reduced spikes but did not improve survival.
  - Bleeding at rhoMaxNode smoothed spikes but sometimes failed earlier.
- Interpretation (working theory)
  - Stop condition is sustained meanP; reducing peaks may not reduce mean accumulation.

#### Retention/leak observability limitation (v3.6)
- Measurements
  - ret/leak keys not exposed (`[]` for node and physics ret/leak-ish keys).
- Working approach
  - Use proxies: $\rho$ entropy, concentration (rhoMax/rhoSum), rhoSum drift, flux decay metrics.

### Phase Conclusions
- Locked in
  - “Who owns the runaway” is measurable: rho reservoir at node 82.
  - Need guardrails shaped against meanP accumulation, not just pMax spikes.
- Still speculative
  - Which constitutive law prevents the metastable ramp without killing “awake dynamics.”

---

<a id="phase-3105-build-v36--dreamstate-afterstates--end-phase-latch"></a>
## Phase 3.10.5 — DreamState afterstates + end-phase latch

**Metadata**
- Date: Unknown (precision: unknown)
- Date evidence: Not present in sources; ordered by phase numbering only
- Sources: `rd26.md`, `rd27.md`
- Primary artifacts: ART-3105-harness-dreamSweep (referenced), ART-3105-harness-dreamThenWatch (referenced), ART-3105-harness-dreamAfterstate (referenced)
- Versions: Dashboard=Dashboard v3.6 (as implied in `rd26.md`); Harness=solDreamSweepV1 / solDreamThenWatchV1 / solDreamAfterstateV1 (as named); Baseline=Unknown; Engine build=Unknown

### Scope / Objective
- Build repeatable excitation + readout signatures (“afterstates”), identify control knobs (ψ mean/waveform/cadence), and discover a deterministic control primitive.

### Instrumentation & Harnesses
- Dream/afterstate harness family (installed via `globalThis`):
  - `solRestWatchV2`
  - `solDreamThenWatchV1`
  - `solDreamAfterstateV1`
  - `solDreamSweepV1` (grid; summary + trace)
- Standard signature metrics (afterstate classification):
  - `rhoMaxId_t0`, `rhoMaxId_mode`
  - `rhoMaxId_firstSwitch_tSec`
  - “90 window” metrics: enter/exit/dwell/segments
  - supporting: entropy, rhoSum, meanP, flux peaks

### Experiments

#### RestWatch baseline signature
- Measurements
  - entropy ~0.44 (stable)
  - `rhoMaxId` stays 82
  - `rhoConc` ~0.176
  - rhoSum half-life ~9–10s; flux half-life ~6–7s
- Interpretation (working theory)
  - Distribution shape persists while amplitude shrinks; entropy is scale-invariant.

#### ψ polarity effects (DC sweeps)
- Measurements
  - Negative ψ generally delays 90→82 failover (90 holds longer).
  - ψ≈+1 repeatedly a worse spot.
- Interpretation (working theory)
  - ψ is more routing/bias than energy.

#### ψ waveform / cadence effects (ChaosMap, Resonance A/B/C, CadenceHzBig)
- Observations
  - Cadence changes qualitative regime (start-90 failover vs window mode).
  - Iso-dose does not restore behavior: burst timing matters, not only total dose.
- Interpretation (working theory)
  - Cadence is a true control knob; waveform relative to cadence shows phase-lock-like behavior.

#### EndPhaseV1 — digital latch primitive discovered
- Measurements
  - `end_lastBlockParity` predicted `rhoMaxId_t0` perfectly in that regime:
    - parity 0 → starts in 90
    - parity 1 → starts in 82
- Interpretation (working theory)
  - Edge-triggered latch: the moment dream stops samples the state; parity was the visible proxy under fixed injector order.

### Phase Conclusions
- Locked in
  - Afterstates are classifiable with consistent signature metrics.
  - ψ and cadence move regimes.
  - A deterministic latch primitive exists.
- Still speculative
  - The internal state variable implementing the latch.

---

<a id="phase-3106--phase-311-kickoff-build-v13--latch-identity-lastinjected"></a>
## Phase 3.10.6 / Phase 3.11 Kickoff — Latch identity: `lastInjected`

**Metadata**
- Date: Unknown (precision: unknown)
- Date evidence: Not present in sources; ordered by phase numbering only
- Sources: `rd28.md`
- Primary artifacts: ART-3106-baseline-solbaseline-v1_3
- Versions: Dashboard=Unknown; Harness=Unknown (LatchIdentity runs referenced); Baseline=SOLBaseline v1.3 (`SOLBaseline_v1.3.js`); Engine build=Unknown

### Scope / Objective
- Turn latch from “parity pattern” into a controller primitive with correct identity variable and robust timing semantics.

### Instrumentation & Harnesses
- Baseline: `SOLBaseline_v1.3.js` (normalizes legacy formats; restores baseline from localStorage).
- Controller runs: multiple identity + watch sequences across browser/timing strategies.
- Standardization
  - Timing telemetry becomes first-class: `lateByMs`, missed ticks.
  - Use `globalThis.SOLDashboard` root (v3.6) rather than `App`.

### Experiments

#### LatchIdentity runs
- Measurements
  - Parity is not the root variable; injector order flips break parity-only explanation.
  - Canonical rule:
    - **Mode select = end the dream on the injector you want to dominate at t0.**
    - `start basin at t0 ≈ lastInjected` at dream stop.
  - Order B (`injectorIds=[90,82]`) more stable than Order A in described runs.
- Observations
  - start82 sometimes flips to 90 quickly; start90 often stays 90 (afterstate asymmetry).

### Phase Conclusions
- Locked in
  - Latch identity is `lastInjected` at dream stop.
  - t0 sampling must be immediate (`postSteps=0`) to avoid drift.
- Still speculative
  - Stabilizers needed to preserve selected basin against asymmetry without sedation.

---

<a id="phase-311-build-v37--temporal-packet--dual-bus-broadcast"></a>
## Phase 3.11 — Temporal packet → dual-bus broadcast

**Metadata**
- Date: 2026-01-11 → 2026-01-12 (precision: range)
- Date evidence: `solResearchNote1.md` “Date range (local): Jan 11, 2026”; `solResearchNote2.md` “Date range: Jan 11–12, 2026”
- Sources: `solResearchNote1.md`, `solResearchNote2.md`, `rd29.md`, `rd30.md`
- Primary artifacts: ART-311-dashboard-v3_7_2, ART-31116g-summaryCSV, ART-31116i-summaryCSV, ART-31116i-busTraceCSV, ART-31116j-summaryCSV, ART-31116j-busTraceCSV, ART-31116k-summaryCSV, ART-31116k-busTraceCSV, ART-31116l-summaryCSV, ART-31116l-busTraceCSV
- Versions: Dashboard=Dashboard v3.7.2 (`sol_dashboard_v3_7_2.html`); Harness=solPhase311_16m.js (style reference; 16m running); Baseline=SOLBaseline v1.3 (`SOLBaseline_v1.3.js`); Engine build=Unknown

### Scope / Objective
- Establish readout as a structured bus/broadcast mechanism: distributed temporal packets compile into deterministic rail timing and traceable boundary physics.

### Instrumentation & Harnesses
- Baseline discipline: `SOLBaseline_v1.3.js` (restore every run).
- Dashboard: `sol_dashboard_v3_7_2.html` (current at time of note).
- Outputs: deterministic `MASTER_summary.csv` + `MASTER_busTrace.csv`.
- Canonical bus rails
  - Ports: B=114, D=136
  - Legs: to 89 and 79 (mirrored)
  - Threshold: bus “ON” if `max(|flux_to89|, |flux_to79|) ≥ 1.0` (as stated for Phase 3.11.16 note)

### Experiments (chronological within the phase)

#### RN-3.11.16 (Jan 11, 2026) — Boundary + compilation mapping
- Setup
  - Bus threshold = 1.0
  - Basin in this regime observed stable (82)
  - Packs analyzed: 16g, 16i, 16j, 16k, 16l; 16m running.
- Outputs (portable references; filenames captured; locations TBD)
  - ART-31116g-summaryCSV — `sol_phase311_16g_gapSweep_v1_2026-01-11T07-14-58-939Z_2026-01-11T07-36-37-298Z_MASTER_summary.csv`
  - ART-31116i-summaryCSV — `sol_phase311_16i_simulPulseAmpGapMap_v1_2026-01-11T16-55-59-158Z_2026-01-11T17-24-40-224Z_MASTER_summary.csv`
  - ART-31116i-busTraceCSV — `sol_phase311_16i_simulPulseAmpGapMap_v1_2026-01-11T16-55-59-158Z_2026-01-11T17-24-40-224Z_MASTER_busTrace.csv`
  - ART-31116j-summaryCSV — `sol_phase311_16j_simulPulseRatioMap_v1_2026-01-11T17-48-01-398Z_2026-01-11T18-11-33-114Z_MASTER_summary.csv`
  - ART-31116j-busTraceCSV — `sol_phase311_16j_simulPulseRatioMap_v1_2026-01-11T17-48-01-398Z_2026-01-11T18-11-33-114Z_MASTER_busTrace.csv`
  - ART-31116k-summaryCSV — `sol_phase311_16k_lowAmpBoundaryScan_v1_2026-01-11T18-32-24-962Z_2026-01-11T18-58-39-166Z_MASTER_summary.csv`
  - ART-31116k-busTraceCSV — `sol_phase311_16k_lowAmpBoundaryScan_v1_2026-01-11T18-32-24-962Z_2026-01-11T18-58-39-166Z_MASTER_busTrace.csv`
  - ART-31116l-summaryCSV — `sol_phase311_16l_ridgeScanOnsetDelay_v1_2026-01-11T19-18-35-047Z_2026-01-11T19-43-03-964Z_MASTER_summary.csv`
  - ART-31116l-busTraceCSV — `sol_phase311_16l_ridgeScanOnsetDelay_v1_2026-01-11T19-18-35-047Z_2026-01-11T19-43-03-964Z_MASTER_busTrace.csv`
  - 16m expected: `MASTER_summary.csv` + `MASTER_busTrace.csv` from `solPhase311_16m` (filenames TBD).

##### 3.11.16g — GapSweep
- Setup: 180 runs; packet patterns varied; `gapTicks` varied.
- Measurements
  - bothOn: 174; none: 6.
  - Failures concentrated: pattern `RR_ABCD` at `gapTicks=1` (6/46 at that gap setting across packets).
- Interpretation (working theory)
  - Packet syntax matters; certain gaps can reduce reliability near threshold.

##### 3.11.16i — SimulPulse Amp/Gap map
- Setup: 288 runs.
- Measurements
  - bothOn: 278; none: 9; only136: 1.
  - Narrow failure condition: `B_then_D` with `gapTicks=0` and `secondAmpMult=1.0` → 8/8 none.
  - Mirror order `D_then_B` with `gapTicks=0` and `secondAmpMult=1.0` → 8/8 bothOn.
- Interpretation (working theory)
  - Within-tick injection order is part of the code; “simultaneous” is not commutative.

##### 3.11.16j — RatioMap (amp surface)
- Setup: ampB ∈ {6,10,14,18}, ampD ∈ {6,10,14,18}, 12 reps/cell.
- Measurements
  - bothOn: 182; none: 9; only136: 1.
  - Failures confined to (ampB=6, ampD=6): 2 bothOn, 9 none, 1 only136.
- Interpretation (working theory)
  - Threshold exists; above it, behavior becomes deterministic.

##### 3.11.16k — Low-amp boundary scan
- Setup: 256 runs.
- Measurements
  - bothOn: 244; none: 10; only136: 2.
  - All non-bothOn in row ampB=4 with ampD ≤ 6:
    - (4,4): 0/4 bothOn (4 none)
    - (4,5): 0/4 bothOn (4 none)
    - (4,6): 0/4 bothOn (2 none, 2 only136)
    - (4,7)+: 4/4 bothOn.
  - Onset behavior: onset114_tick=1 in 240/244; onset136_tick=1 in 224/244.
  - Basin stability: basin=82 for 7936/7936 trace rows.
- Interpretation (working theory)
  - Above threshold, bus ignites immediately and symmetrically.

##### 3.11.16l — Ridge scan (metastable band)
- Setup: 120 runs; ampB fixed at 4; ampD swept; longer window.
- Measurements
  - bothOn: 112; none: 8.
  - All failures at ampD=5.50: 4/12 bothOn, 8/12 none.
  - ampD ≥ 5.75: 108/108 bothOn; onset ticks fixed at 1/1; winner=tie 108/108.
  - Basin stability: basin=82 for 7320/7320 trace rows.
- Interpretation (working theory)
  - Threshold ridge with metastable band; late ignition exists only inside metastable band.

##### Filament / outer-surge signature (from 16k max-edge telemetry)
- Measurements
  - Dominant max edges included: 136→89, 136→10, 114→89, 95→114, 90→92, 104→82, and 104→114.
  - Edge 104→114 appeared as max-edge for 51 ticks (mean tick ~16.35), concentrated mid-run.
- Interpretation (working theory)
  - “Outer filament events” correspond to transient route-capture corridors.

#### Phase 3.11 continuation — handshake protocol (Jan 11–12, 2026) and robustness
- From closeout note (Phase 3.11 continuation):
  - Dashboard upgraded v3.6 → v3.7, CAP-law integrated, invariants tightened.
  - Handshaked packet primitive (16w) and robustness sweeps (16x) defined.
- Key measurements (handshake v1 from 16w; as stated)
  - baseAmpB=4.0 (114), baseAmpD=5.75 (136)
  - gain=22
  - multB=1.144 → ampB0=100.672
  - ampD=126.5
  - ratioBD≈0.795826
  - offset=+1 (136 tick0, 114 tick1)
  - nudgeTick=14, nudgeMult=0.20 → ampB_nudge=20.1344
  - Observed rails (damp 4–5): 136@13, 114@15, Δ=2.

### Phase Conclusions
- Locked in
  - Dual-bus broadcast rails are real, measurable, and highly reliable above a small boundary.
  - Temporal packets compile (space → time): order and gap are encoding parameters.
  - Threshold ridge with metastability exists and can be mapped.
  - Basin is stable during these readout experiments (in this regime).
- Still speculative
  - Full “protocol spec” for robust readout under wider environment drift (pressC/damp/dt) is pending 16m and beyond.

---

## D) Canonical Mechanisms Glossary

Each mechanism is defined consistently and includes “first validated in” and “best measurement proxy.”

1. **Retention / leak**
   - Definition: Persistence of injected $\rho$ over steps/time; loss governed by damping/decay and topology.
   - First validated in: Phase 2.0 (as a conservative limit when $\kappa=0$) and operationally in Phase 3.6.
   - Best measurement proxy: `retentionEnd`, stepwise retention curve; tail/half-life; early `step1OutFlux` as gatekeeper for hubs.

2. **Basin / attractor**
   - Definition: Stable mode/region of state space the system falls into (often tracked via dominant node identity, e.g., rhoMaxId, or basin classifier fields).
   - First validated in: Phase 3.10.5–3.10.6 (afterstate basin signatures + latch control).
   - Best measurement proxy: `rhoMaxId_t0`, mode classifier, switch timing (e.g., 90→82), basin fields in busTrace (e.g., basin=82 rows).

3. **Metastability**
   - Definition: Long transient stability followed by delayed flip into a different regime (late ignition / late failure).
   - First validated in: Phase 3.9.
   - Best measurement proxy: `timeToFailure` under criterion `meanP > 0.5 sustained 20 steps`; long-horizon traces (800–4000+ steps).

4. **Phase transition**
   - Definition: Qualitative regime shift as a control parameter (notably damping) crosses a narrow boundary (vacuum/liquid/solid/singularity).
   - First validated in: Phase 3.0 (damp descent).
   - Best measurement proxy: regime-specific ranges of $\rho$ and $j$ (mass floor/ceiling, flux collapse), plus qualitative survivorship shifts.

5. **Limit cycle**
   - Definition: Repeating oscillatory dynamics (heartbeat / breathing) rather than convergence.
   - First validated in: Phase 3.2 (phase gating heartbeat) and implied in cadence-driven DreamState regimes.
   - Best measurement proxy: periodicity in telemetry (pressure/flux/psi) at known cadence/Hz.

6. **Criticality / SOC**
   - Definition: Near-threshold regime where small perturbations can trigger large events (avalanches) and boundary ridges create probabilistic outcomes.
   - First validated in: Phase 3.2 (battery avalanche) and Phase 3.11.16 (threshold ridge).
   - Best measurement proxy: avalanche/threshold crossing events; metastable boundary probabilities; event counts near ridge.

7. **Phase gating**
   - Definition: Temporal interleaving using $\cos(\omega t)$ to alternate semantic layers (Tech vs Spirit), avoiding direct cancellation.
   - First validated in: Phase 3.2.
   - Best measurement proxy: gated layer activity patterns and stable alternation under fixed omega.

8. **Binary Battery / Capacitor / Lighthouse**
   - Definition: A retention + activation primitive: accumulation to threshold then release/hold (“fire & hold”) acting as a paradigm beacon.
   - First validated in: Phase 3.2.
   - Best measurement proxy: charge curve, threshold crossing, avalanche timing, sustained saturated state.

9. **Capacitance law (CAP-law)**
   - Definition: A constitutive rule mapping topology (degree, etc.) to semanticMass / SM so nodes behave like capacitors scaled to connectivity.
   - First validated in: Phase 3.6 (degree-linear proof) and Phase 3.7–3.8 (generalized power law).
   - Best measurement proxy: dt-normalized `outfluxRate` / `outfluxRate_peakEdge`, `step1Pressure_mean`, `retentionEnd` across wide target sets.

10. **DreamState / DreamSweep harnesses**
   - Definition: Controlled excitation protocol + afterstate watch used to generate and classify basin signatures.
   - First validated in: Phase 3.10.5.
   - Best measurement proxy: afterstate signature metrics (rhoMaxId switches, dwell windows), entropy trajectory, rhoSum half-life.

11. **Latch primitive (end-phase latch)**
   - Definition: Digital control primitive: stopping the dream on a specific injector selects the t0 basin (mode select).
   - First validated in: Phase 3.10.5 (parity proxy) and corrected in Phase 3.10.6 (lastInjected identity).
   - Best measurement proxy: `rhoMaxId_t0` determinism under controlled stop timing (`postSteps=0`).

12. **Dual-bus broadcast rails**
   - Definition: Emergent readout primitive where injected packets compile into mirrored flux legs from ports (114/136) to receiver rails (89/79).
   - First validated in: Phase 3.11.16.
   - Best measurement proxy: `MASTER_busTrace.csv` threshold crossing, onset ticks, symmetry between legs.

13. **Outer filament event**
   - Definition: Transient route-capture where an “outer” edge becomes dominant max-edge corridor, distributes, then returns to core pattern.
   - First validated in: Phase 3.11.16 (telemetry evidence aligned with observation).
   - Best measurement proxy: max-edge identity timeline and concentration metrics (e.g., 104→114 max-edge window).

---

## E) Artifact Catalog (future retrieval + consolidation)

> Canonical naming pattern recommendation: `sol_phase{PHASE}_{RUNID}_{harness}_v{N}_{startISO}_{endISO}_{KIND}.csv` where KIND ∈ {`MASTER_summary`, `MASTER_busTrace`, `summary`, `trace`}.

### Dashboards (HTML)
- Key: ART-20-dashboard-v20
  - Type: dashboard
  - Location: TBD
  - Filename: `sol_dashboard_v2.0` (referenced)
- Key: ART-32-dashboard-v3_combined
  - Type: dashboard
  - Location: `sol_dashboard_v3_combined.html`
- Key: ART-32-dashboard-v3_1
  - Type: dashboard
  - Location: `sol_dashboard_v3_1.html`
- Key: ART-32-dashboard-v3_2
  - Type: dashboard
  - Location: `sol_dashboard_v3_2.html`
- Key: ART-32-dashboard-v3_2_final
  - Type: dashboard
  - Location: TBD
  - Filename: `sol_dashboard_v3_2_final.html` (referenced)
- Key: ART-35-dashboard-v3_5
  - Type: dashboard
  - Location: `sol_dashboard_v3_5.html`
- Key: ART-dashboard-v3_6
  - Type: dashboard
  - Location: TBD
  - Filename: `sol_dashboard_v3_6` (referenced)
- Key: ART-311-dashboard-v3_7_2
  - Type: dashboard
  - Location: `sol_dashboard_v3_7_2.html`

### Harness scripts / globals (JS)
- Key: ART-3106-baseline-solbaseline-v1_3
  - Type: baseline
  - Location: `solEngine/SOLBaseline_v1.3.js`
- Key: ART-36-harness-retentionMicroscope-v3
  - Type: harness
  - Location: TBD
  - Name: `solRetentionMechanismMicroscopeV3`
- Key: ART-37-harness-capLawMicroscope-v1
  - Type: harness
  - Location: TBD
  - Name: `solCapacitanceLawMicroscopeV1`
- Key: ART-38-harness-solPhase38
  - Type: harness
  - Location: TBD
  - Name: `solPhase38`
- Key: ART-310-harness-mechanismTraceSweep-v1
  - Type: harness
  - Location: TBD
  - Name: `solMechanismTraceSweepV1` (referenced)
- Key: ART-310-harness-restWatch-v2
  - Type: harness
  - Location: TBD
  - Name: `solRestWatchV2` (referenced)
- Key: ART-3105-harness-dreamThenWatch
  - Type: harness
  - Location: TBD
  - Name: `solDreamThenWatchV1` (referenced)
- Key: ART-3105-harness-dreamAfterstate
  - Type: harness
  - Location: TBD
  - Name: `solDreamAfterstateV1` (referenced)
- Key: ART-3105-harness-dreamSweep
  - Type: harness
  - Location: TBD
  - Name: `solDreamSweepV1` (referenced)
- Key: ART-311-harness-solPhase311-16m
  - Type: harness
  - Location: TBD
  - Name: `solPhase311_16m.js` (referenced)

### Data outputs (CSVs)
- Key: ART-36-data-retention-v3-sweep
  - Type: data
  - Location: TBD
  - Filenames: `sol_retention_mech_v3_*_2026-01-03T04-24-57-939Z.csv`
- Key: ART-36-data-retention-superhubs
  - Type: data
  - Location: TBD
  - Filenames: `sol_retention_mech_v3_superhubs_basin_*_2026-01-03T04-42-43-669Z.csv`
- Key: ART-36-data-retention-AB
  - Type: data
  - Location: TBD
  - Filenames: `sol_retention_AB_superhubs_sm32_leak005_basin{0|1}_*_2026-01-03T04-55-55-936Z.csv`
- Key: ART-36-data-retention-pointwell
  - Type: data
  - Location: TBD
  - Filenames: `sol_retention_pointwell_sm{1024|4096}_leak005_*_2026-01-03T05-03-49-274Z.csv`
- Key: ART-37-data-capLaw-slopeSweep
  - Type: data
  - Location: TBD
  - Filename: `sol_capLaw_slopeSweep_2026-01-03T21-29-36-577Z.csv`
- Key: ART-37-data-capLaw-kneeSweep
  - Type: data
  - Location: TBD
  - Filename: `sol_capLaw_kneeSweep_10to28_2026-01-03T21-43-31-367Z.csv`
- Key: ART-37-data-capLaw-generalize
  - Type: data
  - Location: TBD
  - Filenames: `sol_capLaw_generalize_28v34_2026-01-03T21-43-31-520Z.csv`, `sol_capLaw_generalize_28to34_2026-01-03T21-48-11-863Z.csv`
- Key: ART-37-data-capLaw-stressInject
  - Type: data
  - Location: TBD
  - Filename: `sol_capLaw_stress_inject20_33v34_2026-01-03T21-55-17-274Z.csv`
- Key: ART-38-data-twoMetric_SHARED
  - Type: data
  - Location: TBD
  - Filenames: Unknown (not embedded in sources; described as “twoMetric_SHARED” wide100)
- Key: ART-39-data-timeToFailure-v2
  - Type: data
  - Location: TBD
  - Filenames: Unknown (not embedded in sources)
- Key: ART-31116g-summaryCSV
  - Type: data
  - Location: TBD
  - Filename: `sol_phase311_16g_gapSweep_v1_2026-01-11T07-14-58-939Z_2026-01-11T07-36-37-298Z_MASTER_summary.csv`
- Key: ART-31116i-summaryCSV
  - Type: data
  - Location: TBD
  - Filename: `sol_phase311_16i_simulPulseAmpGapMap_v1_2026-01-11T16-55-59-158Z_2026-01-11T17-24-40-224Z_MASTER_summary.csv`
- Key: ART-31116i-busTraceCSV
  - Type: data
  - Location: TBD
  - Filename: `sol_phase311_16i_simulPulseAmpGapMap_v1_2026-01-11T16-55-59-158Z_2026-01-11T17-24-40-224Z_MASTER_busTrace.csv`
- Key: ART-31116j-summaryCSV
  - Type: data
  - Location: TBD
  - Filename: `sol_phase311_16j_simulPulseRatioMap_v1_2026-01-11T17-48-01-398Z_2026-01-11T18-11-33-114Z_MASTER_summary.csv`
- Key: ART-31116j-busTraceCSV
  - Type: data
  - Location: TBD
  - Filename: `sol_phase311_16j_simulPulseRatioMap_v1_2026-01-11T17-48-01-398Z_2026-01-11T18-11-33-114Z_MASTER_busTrace.csv`
- Key: ART-31116k-summaryCSV
  - Type: data
  - Location: TBD
  - Filename: `sol_phase311_16k_lowAmpBoundaryScan_v1_2026-01-11T18-32-24-962Z_2026-01-11T18-58-39-166Z_MASTER_summary.csv`
- Key: ART-31116k-busTraceCSV
  - Type: data
  - Location: TBD
  - Filename: `sol_phase311_16k_lowAmpBoundaryScan_v1_2026-01-11T18-32-24-962Z_2026-01-11T18-58-39-166Z_MASTER_busTrace.csv`
- Key: ART-31116l-summaryCSV
  - Type: data
  - Location: TBD
  - Filename: `sol_phase311_16l_ridgeScanOnsetDelay_v1_2026-01-11T19-18-35-047Z_2026-01-11T19-43-03-964Z_MASTER_summary.csv`
- Key: ART-31116l-busTraceCSV
  - Type: data
  - Location: TBD
  - Filename: `sol_phase311_16l_ridgeScanOnsetDelay_v1_2026-01-11T19-18-35-047Z_2026-01-11T19-43-03-964Z_MASTER_busTrace.csv`

### Notes (inputs)
- Key: ART-20-note-rd7
  - Type: note
  - Location: `solArchive/MD/rd7.md`
- Key: ART-30-note-rd8
  - Type: note
  - Location: `solArchive/MD/rd8.md`
- Key: ART-30-note-rd9
  - Type: note
  - Location: `solArchive/MD/rd9.md`
- Key: ART-32-note-rd6
  - Type: note
  - Location: `solArchive/MD/rd6.md`
- Key: ART-35-note-rd3
  - Type: note
  - Location: `solArchive/MD/rd3.md`
- Key: ART-36-note-rd21
  - Type: note
  - Location: `solArchive/MD/rd21.md`
- Key: ART-37-note-rd22
  - Type: note
  - Location: `solArchive/MD/rd22.md`
- Key: ART-38-note-rd23
  - Type: note
  - Location: `solArchive/MD/rd23.md`
- Key: ART-38-note-rd24
  - Type: note
  - Location: `solArchive/MD/rd24.md`
- Key: ART-39-note-rd25
  - Type: note
  - Location: `solArchive/MD/rd25.md`
- Key: ART-310-note-rd26
  - Type: note
  - Location: `solArchive/MD/rd26.md`
- Key: ART-3105-note-rd27
  - Type: note
  - Location: `solArchive/MD/rd27.md`
- Key: ART-3106-note-rd28
  - Type: note
  - Location: `solArchive/MD/rd28.md`
- Key: ART-311-note-solResearchNote1
  - Type: note
  - Location: `solArchive/MD/solResearchNote1.md`
- Key: ART-311-note-solResearchNote2
  - Type: note
  - Location: `solArchive/MD/solResearchNote2.md`

### Duplicates / near-duplicates & recommended consolidation targets
- Many cap-law runs differ only by sweep range; consolidate into:
  - `caplaw/linear/`, `caplaw/power/`, `caplaw/proxy/`, `caplaw/dt/` subfolders with an index CSV.
- Dream harness variants evolved rapidly; consolidate by naming the latest canonical harness per family:
  - `SOLBaseline`, `solDreamSweep`, `solRestWatch`, `solMechanismTraceSweep`.
- Preserve the MASTER_* convention for Phase 3.11 and adopt it across earlier phases.

---

## F) What We Think We Know vs What We Need to Prove Next

### 1) Locked Findings (strongest evidence)
- **Retention is pressure/outflux-gated for hubs**: reducing early outflux (step-1) is the dominant determinant of retention success (Phase 3.6–3.7).
- **CAP-law is a real constitutive mechanism**: degree-power (alpha~0.8, anchored/clamped) yields wide-set stability and is reasonably dt-robust (Phase 3.8).
- **Metastability exists and dt compresses time-to-failure**: long-horizon flips occur even after hundreds/thousands of steps; dt≥0.12 is high risk under the Phase 3.9 signature (Phase 3.9).
- **Afterstates are classifiable and controllable**: DreamState produces reproducible basin signatures; latch identity `lastInjected` selects t0 basin (Phases 3.10.5–3.10.6).
- **Readout rails exist**: temporal packets compile into a coherent dual-bus broadcast with a sharp ridge and a metastable band (Phase 3.11.16).

### 2) Active Hypotheses (with falsification tests)
- **Hψ (ψ as slow-variable ramp driver):** $\psi$ concentration/structure is the hidden variable that drifts and triggers metastable flips (Phase 3.9→3.10 suspicion).
  - Falsification: in otherwise identical time-to-failure sweeps, clamp/hold ψ stats constant (or drive ψ in controlled ways) and show time-to-failure no longer depends on dt as observed.
- **Hfilament (filament events as computation stages):** max-edge “outer filament” captures correspond to internal stage transitions (arbitration/handshake/broadcast).
  - Falsification: correlate max-edge capture windows with bus onsets across runs; if no correlation, filament events are incidental.
- **Hprotocol (encoding syntax is robust):** packet order/gap/offset can be turned into an engineerable encoding alphabet with clear tolerance bounds.
  - Falsification: run robustness sweeps (pressC, damp, dt) around the 50% ridge point; if small environment drift collapses reliability, protocol needs adaptive handshake/self-clocking.

### Next 3 experiments (short plan, methodology-preserving)
1. **Finish 3.11.16m probability curve**
   - Goal: P(bothOn | ampD) across 5.50→5.75; compute onset distributions and “pre-flip glow” evidence.
   - Discipline: baseline restore; UI-neutral; MASTER_summary + MASTER_busTrace; log pressCUsed/dampUsed/dt/busThreshUsed.

2. **Adaptive handshake (16y) across high damping**
   - Goal: test multistage timing bands up to damp 20 using self-timed nudge (arbiter+1).
   - Readout: Δ timing modes, cross-coupler behavior (89→79), and failure modes.

3. **Bridge control: latch + ψ trim into readout**
   - Goal: combine deterministic mode-select (lastInjected latch) with packet readout; check whether basin selection alters bus reliability or ridge location.
   - Readout: ridge shift, onset stability, basin integrity under readout.

---

## Uncertainty Notes (explicit)
- Several early notes (Phase 3.0 and rd0) contain mixed analysis and metaphor; where raw filenames/CSVs were not preserved, placement is anchored by the shared date (Jan 3, 2026) and the internal damping/zone ladder.
- Some dates appear as “2025-01-03” while the broader phase cluster is “2026-01-03.” This is preserved as written; treat Phase 2.0 as earlier-session lineage unless corrected by external metadata.
