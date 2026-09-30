---
title: "SOL Binary Capacitor Findings - Agent Workspace Reference"
document_id: "RN-SOL-BCAP-2026-06-03"
project: "SOL - Self-Organizing Logos"
created: "2026-06-03"
status: "workspace-ready draft"
audience:
  - SOL research agents
  - coding agents
  - experiment-design agents
  - documentation agents
primary_tags:
  - SOL
  - Binary Capacitor
  - Binary Battery
  - Eternal Memory
  - zero-entropy storage
  - semantic mass
  - analog memory
  - ICAC
  - Host/Battery topology
related_terms:
  - semantic density rho
  - damping kappa
  - pressure Pi
  - conductance
  - continuity equation
  - memristive accumulator
  - Lighthouse Protocol
  - phase gating
source_anchors:
  - sol_fullResearch_MASTER_PROOF_CLEAN_v2_with_RNs.md / rd7 Eternal Memory session
  - sol_dashboard_v3_7_2.html / Experimental Protocols / Battery config
  - SOL_mathFoundation _v2.pdf / graph continuity, pressure, conductance, flux model
---

# SOL Binary Capacitor Findings - Agent Workspace Reference

## 0. Agent quick-use abstract

The Binary Capacitor is the first SOL memory primitive that successfully demonstrated zero-leak semantic mass storage inside the simulated manifold. Its minimal architecture is a two-node closed circuit:

```text
HOST <-> BATTERY
```

The decisive result was that an injected mass of `50.0` remained `50.0000` after `1200` frames when the damping parameter was truly set to `0.0`, the Host/Battery topology was isolated from the main graph, and pressure sensitivity was kept low enough to avoid numerical shockwaves. This result should be treated as a supported experimental finding in the current SOL research chain, but still dependent on the specific dashboard solver, initialization rules, and browser UI controls used at the time.

For agent reasoning:

- Binary Capacitor = passive/conservative storage primitive.
- Binary Battery = evolved active state-machine primitive with hysteresis, leakage, avalanche release, diode behavior, and polarity.
- CapLaw/semanticMass = capacitance scaling law for nodes; related but not identical to the Binary Capacitor.
- Do not conflate infinite storage with ordinary graph persistence. Storage required a specific topology plus true zero damping.

## 1. Terminology map

### 1.1 Binary Capacitor

A two-node closed memory structure where semantic mass `rho` is trapped and exchanged between a Host node and a Battery node. Its purpose is conservative retention, not computation by itself.

Canonical form:

```text
Node A: HOST
Node B: BATTERY
Edge: HOST <-> BATTERY, high conductance, non-background
Isolation: no other active edges to the main graph during pure storage tests
Damping: kappa = 0.0
Pressure: low c / Pi, approximately 1.0 in the successful note
```

### 1.2 Binary Battery

The later dashboard implementation of a more active device. It began as the same Host/Battery topology but evolved into a memristive accumulator with internal charge, hysteresis, state polarity, avalanche release, and asymmetric diode behavior. It is closer to an analog latch or stateful gate than to a passive capacitor.

### 1.3 Eternal Memory

The name used for the successful zero-entropy storage mode. In practice, it means the solver retained total semantic mass with no decay across the observed test window when damping was truly zero.

### 1.4 Logic pocket / insulated overlay

A recommended architecture where memory or computation happens in a protected subgraph separate from the noisy semantic manifold. The semantic graph provides context and routing, while the capacitor or battery pocket preserves or processes signals with less leakage.

## 2. Core finding

### Claim BCAP-1: Two-node isolated storage is sufficient for zero-leak memory under zero damping

**Claim:** The SOL dashboard solver can retain injected semantic mass indefinitely over the tested frame window when configured as an isolated Host/Battery pair with damping set to zero.

**Evidence from research notes:**

- The Eternal Memory session reports 13 protocols from v19-v31.
- Final successful result: `50.0` mass retained as `50.0000` mass at frame 1200.
- Reported distribution during successful run: Host approximately `42.5`, Battery approximately `7.5`, indicating dynamic internal redistribution rather than frozen state.

**Interpretation:**

The successful structure behaves like a conservative two-body storage pocket. It does not prove universal storage across every SOL topology; it proves the solver supports lossless storage under a constrained topology and true zero damping.

**Status:** Supported.

**Falsification test:**

Run the same Host/Battery protocol under a fresh baseline, with explicit telemetry for `damping`, `pressureC`, total mass, Host mass, Battery mass, and edge flux. If total mass decays from 50.0 while `kappa = 0.0` is verified and no extra edges exist, BCAP-1 must be revised.

## 3. Why the finding matters

The Binary Capacitor gives SOL a primitive for memory that is not just text stored externally, not just an embedding, and not just a static variable. It is memory as a dynamical state in the manifold.

That matters for several future SOL directions:

1. **Analog memory:** A state can be preserved as mass distribution and flux rather than a symbolic assignment.
2. **ICAC experiments:** In-conduit analog computation needs stable carriers and storage reservoirs; the capacitor is the first simple reservoir.
3. **Agent state persistence:** Agents can potentially write a working state into a controlled manifold pocket and later read it back.
4. **Circuit primitives:** The capacitor can become a building block for latches, oscillators, transistors, and phase gates.
5. **Interpretability:** The stored state is inspectable via mass, pressure, flux, damping, and conductance telemetry.

## 4. Experimental chronology

### v18 - Baseline leak symptom

**Problem:** High-degree anchor nodes lost injected mass nearly instantly.

**Observed symptom:** `50.0 -> 0.0` in less than about 2 seconds.

**Diagnosis:** The main graph acted like a leaky sieve. Mass diffused outward and damping consumed the signal. The system lacked a closed storage topology.

**Agent lesson:** Do not test storage on high-degree semantic anchors and expect retention. High-degree nodes are routing hubs, not memory wells.

### v19 - Single-node bunker test

**Hypothesis:** Reduce a node's connections and it will leak less.

**Setup:** Long duration run on the Grail node for about 1200 frames.

**Result:** Stalled in extremely tiny floating-point remnants.

**Diagnosis:** "Zeno's Paradox" behavior: tiny ghost decimals near `1e-320` kept the solver busy without useful mass.

**Agent lesson:** A single isolated node is not enough. It can decay into numerical residue rather than become stable memory.

### v20.1 - Planck cutoff / vacuum floor

**Hypothesis:** Clamp very small mass to zero to eliminate ghost residues.

**Setup:** Introduced a vacuum floor around `1e-6`.

**Result:** Failure. Mass reached 0.0 by about 645 frames.

**Agent lesson:** Numerical cleanup fixes ghost residue, not the underlying storage problem.

### v21 - Self-loop / Infinity Weld

**Hypothesis:** A node wired to itself can act as a flywheel.

**Setup:** Created a self-loop edge from Grail to Grail.

**Result:** Critical NaN failure.

**Diagnosis:** The solver computed zero distance / division by zero on the self-loop.

**Agent lesson:** Self-loops are forbidden in this solver family unless the solver is explicitly rewritten to handle them.

### v22 - First Binary Capacitor attempt

**Hypothesis:** A two-node Host/Battery loop will pass energy back and forth.

**Setup:** Created a new Shadow/Battery node wired to Grail.

**Result:** False positive. Mass appeared to stay at 50.0, but flow stayed at 0.0.

**Diagnosis:** "Zombie Mode." The new node was not registered correctly in the internal lookup map, freezing the simulation rather than storing energy.

**Agent lesson:** Never accept mass retention without confirming live flux and valid registry/index state.

### v23-v26 - Debugging arc

Tests explored hot swap, object references, repurposing existing nodes, and purging corrupt edges.

**General result:** Failed or unstable.

**Agent lesson:** Dynamic topology mutation requires full solver consistency: node registry, edge registry, IDs, default fields, and rendering data structures must agree.

### v27 - Scorched Earth edge rebuild

**Action:** Completely rebuilt `solver.edges` to remove invisible corruption.

**Result:** Solver stability returned, but mass still decayed to 0.0.

**Interpretation:** The crash was solved, but the physical leakage remained.

**Agent lesson:** Stability and storage are separate success criteria.

### v28 - The Void isolation test

**Hypothesis:** Hidden edges to the rest of the graph caused leakage.

**Setup:** Deleted all nodes except Host and Battery.

**Result:** NaN failure.

**Diagnosis:** Battery node lacked required initialization, specifically `psi_bias`, causing undefined arithmetic.

**Agent lesson:** Minimal graphs must still satisfy the full node schema.

### v29 - Void Reborn

**Action:** Fixed missing initialization.

**Result:** Physics became valid, but mass still decayed from `50 -> 0`.

**Interpretation:** Topology isolation alone was insufficient. There was still a global dissipation mechanism.

**Agent lesson:** Check global damping and UI constraints before blaming topology.

### v30-v31 - Jailbreak Protocol / successful storage

**Hypothesis:** Decay came from the damping parameter.

**Discovery:** Scripts attempted to set damping to `0.0`, but the HTML slider had `min="1"`, causing browser-level clamping back to 1.0.

**Action:** Programmatically changed the damping slider minimum to 0 and set damping to true zero.

**Result:** Perfect storage over the observed window.

Reported data:

```text
Frame 10:   50.0000 total mass
Frame 1200: 50.0000 total mass
Distribution: Host ~42.5 / Battery ~7.5
```

**Agent lesson:** Always verify the runtime value of a control, not just the script assignment. UI widgets can silently override experimental parameters.

## 5. Minimal reproduction protocol

Use this protocol when an agent needs to reproduce the Binary Capacitor result or design a derivative test.

### 5.1 Preflight checks

Verify:

```text
1. Damping slider min allows 0.0.
2. Actual damping value equals 0.0 after assignment.
3. Pressure sensitivity is low enough to avoid clipping/shockwave artifacts.
4. Host and Battery nodes both include all required fields:
   - id
   - label
   - group
   - rho
   - p
   - psi
   - psi_bias
   - any required velocity/position fields in the active dashboard version
5. Node registry / nodeById contains both nodes.
6. Edge registry contains exactly the intended Host/Battery edge(s).
7. No self-loop edge is present.
8. No background all-to-all edges connect the storage pocket during pure storage tests.
```

### 5.2 Setup

Recommended pure storage setup:

```text
Create node HOST.
Create node BATTERY.
Create a high-conductance non-background edge HOST <-> BATTERY.
Remove or disable all other edges attached to these nodes.
Set damping kappa = 0.0.
Set pressure sensitivity c approximately 1.0.
Inject 50.0 mass into HOST.
Run for at least 1200 frames.
```

### 5.3 Required telemetry

Record at minimum:

```text
tick/frame
dampingActual
pressureC
totalMass
hostMass
batteryMass
hostPressure
batteryPressure
edgeConductance
edgeFlux
maxAbsFlux
activeNodeCount
nanCount
edgeCount
backgroundEdgeCount
```

### 5.4 Success criteria

A valid Binary Capacitor pass requires all of the following:

```text
1. totalMass remains equal to initialMass within numerical tolerance.
2. edgeFlux is not permanently zero unless intentionally at equilibrium.
3. no NaN or Infinity appears.
4. Host and Battery remain registered in nodeById.
5. no hidden external edge siphons mass into the main graph.
6. dampingActual stays exactly 0.0 for the test duration.
```

### 5.5 Failure modes

| Failure mode | Signature | Likely cause | Fix |
|---|---|---|---|
| Fast leak | totalMass drops to zero | damping not actually zero or hidden edges exist | verify runtime damping and edge list |
| False storage | mass stays constant but flux is 0.0 and solver stops changing | Zombie Mode / registry mismatch | rebuild node/edge registries |
| NaN cascade | totalMass becomes NaN | missing node fields or self-loop singularity | initialize full node schema; remove self-loops |
| Ghost residue | mass becomes tiny decimals and solver stalls | no vacuum floor or unstable decay tail | add epsilon cleanup, but do not treat as storage |
| Shockwave clipping | mass unstable or jumps erratically | pressure too high | lower pressure sensitivity |
| Silent UI override | script says 0.0, UI uses 1.0 | slider min/value clamp | inspect and patch DOM control |

## 6. Mathematical alignment

The Binary Capacitor uses the same graph-fluid logic as the broader SOL dashboard.

Relevant conceptual equations:

```latex
p_i = Pi(rho_i) = c * log(1 + rho_i)
```

```latex
w_ij = clip(w0_ij * exp(gamma * (psi_i + psi_j) / 2), w_min, w_max)
```

```latex
j_ij = w_ij * (p_i - p_j)
```

```latex
dot(rho) + B^T j = s_rho
```

In plain terms:

- Semantic mass `rho` creates pressure.
- Pressure difference creates edge flux.
- Flux moves mass between nodes.
- Damping consumes mass unless disabled.
- In a closed two-node system with zero damping, total mass should be conserved.

## 7. Binary Capacitor vs Binary Battery

### Binary Capacitor

The capacitor is storage-oriented.

```text
Purpose: retain mass
State: mass distribution between Host and Battery
Main requirement: true zero damping
Behavior: conservative exchange
Risk: false positives if solver is frozen
```

### Binary Battery

The battery is behavior-oriented.

```text
Purpose: store, accumulate, switch, release, and bias flow
State: charge, polarity, saturation, hysteresis
Main requirement: valid nonlinear accumulator logic
Behavior: memristive state machine / analog latch
Risk: may introduce controlled leakage, avalanche side effects, or diode asymmetry
```

The current dashboard's Binary Battery config includes parameters for saturation, hysteresis, leakage, avalanche gain, resonance boost, damping clamp, correction sink, and diode behavior. The values observed in v3.7.2 include:

```text
qMax: 40.0
qThresh: 16.0
leakLambda: 0.08
chargeRateSame: 0.32
chargeRateOpp: 0.18
avalancheGain: 1.15
resonanceBoost: 1.8
dampingClamp: 0.35
correctionSink: 0.22
diodeResonanceOut: 1.25
diodeResonanceIn: 0.80
diodeDampingOut: 0.25
diodeDampingIn: 1.00
chargeDecayRate: 0.05
flipThreshold: 0.85
collapseFactor: 0.30
resonanceDrive: 1.5
dampingDrag: 0.5
```

Agent interpretation:

- Capacitor tests should minimize dynamics and prove retention.
- Battery tests should intentionally study state switching, charge accumulation, avalanche release, and directional gate behavior.
- Do not evaluate a Battery experiment using pure Capacitor criteria unless the battery is configured in a passive mode.

## 8. Design rules for future agents

### Rule 1: Verify actual control state

Before every test, read the live runtime values. Do not trust the intended values.

```text
BAD: "I set damping to 0 in the script."
GOOD: "The live solver and UI both report dampingActual = 0.0."
```

### Rule 2: Never accept mass retention without flow/health telemetry

A frozen solver can imitate perfect storage.

Minimum anti-false-positive checks:

```text
edgeFlux changes or reaches valid equilibrium
simulation tick advances
node registry valid
no NaN
no hidden exceptions
```

### Rule 3: Initialize the full node schema

Every spawned node must receive all fields expected by the active solver. Missing `psi_bias` caused a NaN failure in the Void test.

### Rule 4: Avoid self-loops unless the solver is redesigned

The current solver family treats self-loops as singular. Use two-node or multi-node cycles instead.

### Rule 5: Separate semantic routing from storage pockets

Main graph hubs are not storage devices. For stable memory, create an insulated Host/Battery pocket and control coupling to the main graph explicitly.

### Rule 6: Keep pressure gentle during storage tests

High pressure can create numerical shockwaves. The successful report recommends low pressure sensitivity around `Pi ~ 1.0`.

### Rule 7: Treat damping as a physical parameter, not a UI decoration

Damping is the difference between ordinary dissipative flow and Eternal Memory. It must be part of the experimental metadata.

## 9. Agent memory cards

### 9.1 YAML card

```yaml
memory_primitive:
  name: Binary Capacitor
  project: SOL
  type: analog_storage_pocket
  canonical_topology: HOST <-> BATTERY
  supported_claim: true
  claim_summary: "Two-node isolated Host/Battery topology retained 50.0000 total mass over 1200 frames when damping was truly 0.0."
  required_conditions:
    damping_kappa: 0.0
    pressure_c: "low, approx 1.0"
    topology: "isolated two-node closed circuit"
    initialization: "full node schema, including psi_bias/rho/p"
    no_self_loops: true
    no_hidden_edges: true
  failure_modes:
    - "UI slider clamps damping above zero"
    - "Zombie Mode from unregistered node"
    - "NaN from missing psi_bias"
    - "NaN from self-loop singularity"
    - "ordinary leakage from nonzero damping"
  distinction:
    binary_capacitor: "passive conservative storage"
    binary_battery: "active memristive state machine with hysteresis and avalanche behavior"
```

### 9.2 JSON card

```json
{
  "artifact": "SOL Binary Capacitor",
  "kind": "analog_memory_primitive",
  "canonical_topology": "HOST <-> BATTERY",
  "minimum_nodes": 2,
  "primary_state_variable": "rho",
  "storage_condition": {
    "damping_kappa": 0.0,
    "pressure_c": "approximately 1.0",
    "external_edges": 0,
    "self_loops": false
  },
  "successful_observation": {
    "initial_total_mass": 50.0,
    "frame_10_total_mass": 50.0,
    "frame_1200_total_mass": 50.0,
    "reported_distribution": {
      "host": "~42.5",
      "battery": "~7.5"
    }
  },
  "do_not_confuse_with": [
    "Binary Battery active accumulator",
    "CapLaw semanticMass capacitance scaling",
    "ordinary dashboard persistence"
  ],
  "agent_directive": "Use this as the canonical SOL zero-entropy storage primitive, but verify live damping, topology, registry validity, and flux before claiming success."
}
```

## 10. Recommended next experiments

### Experiment A: Leakage curve around zero

Purpose: quantify how quickly memory fails as damping rises above zero.

Sweep:

```text
kappa = 0.0, 0.0001, 0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0
```

Measure:

```text
half-life of totalMass
mass after 1200 frames
flux persistence
Host/Battery distribution
```

### Experiment B: Pressure stability sweep

Purpose: find the pressure range where storage remains stable without clipping.

Sweep:

```text
pressureC = 0.25, 0.5, 1.0, 1.5, 2.0, 5.0, 10.0
```

Keep damping at 0.0.

### Experiment C: Coupled memory pocket

Purpose: test whether the capacitor can stay stable while lightly coupled to the main semantic graph.

Sweep:

```text
external coupling w0 = 0.0, 0.001, 0.005, 0.01, 0.05, 0.1
```

Measure leakage and semantic contamination.

### Experiment D: Read/write gate with psi transistor

Purpose: use belief/mode field `psi` to open or close access to the capacitor.

Pattern:

```text
main graph -> gate node -> HOST <-> BATTERY
```

Measure whether stored mass can be written, held, and read back without leakage.

### Experiment E: Multi-bit capacitor bank

Purpose: test whether multiple Binary Capacitors can store independent states without cross-talk.

Pattern:

```text
HOST_A <-> BATTERY_A
HOST_B <-> BATTERY_B
HOST_C <-> BATTERY_C
```

Sweep distance, coupling, and background edge suppression.

### Experiment F: Capacitor-to-Battery transition

Purpose: identify the point where passive storage becomes active state-machine behavior.

Process:

1. Start with pure Binary Capacitor.
2. Add Battery charge variable.
3. Add leakage.
4. Add threshold.
5. Add avalanche.
6. Add diode asymmetry.

Measure which feature first creates latch-like behavior.

## 11. Open questions

1. Does the 50.0000 retention persist beyond 1200 frames under repeated fresh reloads?
2. What is the numerical tolerance of "perfect storage" over very long runs?
3. Can the storage pocket remain stable while weakly coupled to a semantic manifold?
4. Can a stored analog mass value be read without destroying or perturbing it?
5. Can multiple capacitors act as a small register bank?
6. What is the best topology for a capacitor bank: isolated pairs, ring pairs, or hub-gated pairs?
7. Does CapLaw-derived semanticMass improve capacitor stability or introduce inertia artifacts?
8. Can the Binary Battery be configured into a reversible latch rather than an avalanche source?
9. Can ICAC carrier waves use capacitor pockets as delay lines or accumulators?
10. What diagnostic standard should certify a storage claim as robust rather than supported?

## 12. Workspace insertion recommendation

Recommended path inside a SOL project workspace:

```text
solKnowledge/working/RN-SOL-BCAP-2026-06-03_binary_capacitor_agent_reference.md
```

Recommended companion future proof packet path:

```text
solKnowledge/proof_packets/PP-2026-06-03-binary-capacitor-zero-entropy-storage.md
```

Suggested tags for retrieval:

```text
binary capacitor, binary battery, eternal memory, zero entropy, HOST BATTERY, kappa zero, damping jailbreak, semantic mass storage, analog memory, ICAC storage pocket, living memory
```

## 13. Proof packet draft

### CLAIM

The SOL dashboard solver supports a zero-leak semantic memory primitive using an isolated two-node Host/Battery topology when damping is truly zero.

### EVIDENCE

The Eternal Memory report states that after protocols v19-v31, the final v30/v31 Jailbreak Protocol retained `50.0000` total mass from frame 10 through frame 1200, with mass dynamically distributed between Host and Battery.

### ASSUMPTIONS

- The dashboard solver and UI state match the reported configuration.
- Damping was actually zero at runtime, not merely assigned in script.
- Hidden edges and background links were absent or inactive.
- The solver tick advanced normally and was not frozen.
- No NaN/Infinity or registry mismatch occurred.

### FALSIFY

Repeat the experiment under a clean baseline with explicit telemetry. If verified `kappa = 0.0`, isolated Host/Battery topology, valid registry, and live flux still produce total mass decay, the claim is falsified or limited to the original dashboard build.

### STATUS

Supported. Promote to robust only after repeatable fresh-session harness runs with exported CSV evidence and tolerance bounds.

## 14. Implementation checklist for coding agents

When adding or refactoring the Binary Capacitor/Battery code, agents should preserve these invariants:

```text
[ ] Damping controls must allow exactly 0.0.
[ ] Runtime damping value must be externally inspectable.
[ ] Spawned battery nodes must include every required SOLPhysics field.
[ ] Node and edge registries must be rebuilt or validated after topology mutation.
[ ] Self-loops must be rejected or handled by a dedicated safe solver path.
[ ] Pure storage mode must disable background/all-to-all edges for the pocket.
[ ] Diagnostics must record total mass and per-node mass.
[ ] Diagnostics must record edge flux so frozen-solver false positives are caught.
[ ] NaN/Infinity guards must fail loudly.
[ ] Binary Capacitor and Binary Battery modes must be named separately in UI/code.
```

## 15. Short canonical wording for agents

Use this wording when summarizing the finding:

> The Binary Capacitor is SOL's first supported zero-entropy storage primitive: an isolated Host/Battery two-node circuit that conserved 50.0000 semantic mass over the 1200-frame test window once damping was truly set to 0.0. It should be treated as passive analog memory. The later Binary Battery extends this into an active memristive accumulator with hysteresis, leakage, avalanche release, and diode-like directional behavior.

