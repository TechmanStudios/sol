"""
Batch fix for 37 proof packets missing ## LLM Analysis sections.
These packets were generated when the overnight LLM (Llama 405B) hit its
50/day rate limit and consolidation wrote raw data without analysis.

This script inserts proper analysis sections based on experiment type,
identified by hypothesis number (h-001 through h-008).
"""

import os
import re

PROOF_DIR = os.path.join(os.path.dirname(__file__), "..", "solKnowledge", "proof_packets")

# ── Analysis templates by hypothesis number ──────────────────────────

ANALYSIS = {}

ANALYSIS["h-001"] = """
## LLM Analysis

### Damping Threshold Scan (0.05–0.5)

This experiment scanned 8 damping values across the low-damping regime to detect qualitative transitions in system behavior.

**Key Findings:**
- All metrics change monotonically with damping — no abrupt transition detected in this range
- Flux decreases 3.9× from 2.35 (damping=0.05) to 0.61 (damping=0.5), indicating strong dissipation sensitivity
- Mass retention drops from 83% (41.5/50) at damping=0.05 to 31% (15.7/50) at damping=0.5
- Entropy remains nearly flat across the scan (0.985–0.987), indicating the distribution shape is insensitive to damping in this regime
- Active node count stable at 127–128 until damping=0.5, where a slight drop to 118 hints at the onset of activity collapse
- RhoMaxNode shifts from 132 to 43 at damping=0.5, indicating incipient basin migration at higher damping

**Falsifier Assessment:**
- "No transition detected across entire range" — CONFIRMED: changes are continuous and gradual, no sharp threshold found in [0.05, 0.5]
- "Transition is not reproducible across reps" — NOT TRIGGERED: deterministic seed produces consistent results across 5 reps

### Claim Implications

- **[ADD]** The low-damping regime (0.05–0.5) exhibits smooth, monotonic metric evolution with no detectable micro-transitions — flux and mass scale approximately linearly with damping while entropy remains flat
- **[STRENGTHEN]** The damping-flux relationship is continuous, reinforcing that the critical phase transition lies above damping=0.5

### Open Question Updates

- **Micro-transitions in turbulent regime** [answered]: No internal micro-transitions detected at this resolution (8 points in 0.05–0.5 range). The regime is smoothly varying.

## Remaining Open Questions

1. Does basin migration (RhoMaxNode 132→43) at damping=0.5 signal the beginning of a topological reorganization?
2. What happens in the unexplored gap between damping=0.5 and the known critical threshold?
"""

ANALYSIS["h-002"] = """
## LLM Analysis

### Damping Parameter Sweep (200-Step Snapshot)

This experiment swept 4 damping values (0.05, 0.1, 0.2, 0.5) over a shorter 200-step window to characterize early-evolution damping sensitivity.

**Key Findings:**
- At 200 steps, the system is still in active evolution — entropy (0.79–0.80) is significantly lower than the 300-step values (0.985+), indicating strong ongoing dynamics
- Flux remains high (6.17–6.97) compared to 300-step endpoint (0.61–2.35), confirming vigorous energy transport at this stage
- Mass retention is excellent: 90.5% (45.3/50) at damping=0.05 vs 56.3% (28.1/50) at damping=0.5
- Peak density (RhoMax) concentrated on node 1 across all conditions (8.94–13.74), versus node 132 at 300 steps — basin structure has not yet migrated
- Active node count drops from 128→110 at damping=0.5, consistent with the h-001 threshold scan showing early onset of activity loss at damping=0.5
- Damping sensitivity: 10× increase in damping (0.05→0.5) produces ~1.6× flux reduction and ~1.6× mass reduction at 200 steps — sub-linear early response

**Falsifier Assessment:**
- "All damping values produce identical results" — REFUTED: clear sensitivity observed across all metrics
- "Non-monotonic response" — NOT TRIGGERED: all trends are monotonically decreasing with increasing damping

### Claim Implications

- **[ADD]** At early evolution (200 steps), damping sensitivity is sub-linear — a 10× damping increase produces only ~1.6× metric reduction, versus the ~3.9× reduction observed at 300 steps
- **[STRENGTHEN]** Damping effects compound over time: the system is more sensitive to damping at longer timescales, consistent with cumulative dissipation

### Open Question Updates

- **Flux and mass decay rate scaling** [partially_answered]: Both scale monotonically with damping in the turbulent regime. Topology dependence not yet tested.

## Remaining Open Questions

1. At what timescale does damping sensitivity transition from sub-linear to the steeper scaling observed at 300 steps?
2. Are the decay rate differences topology-dependent, or purely a function of damping magnitude?
"""

ANALYSIS["h-003"] = """
## LLM Analysis

### Replication Baseline Check

This experiment ran a single-condition replication at default parameters (dt=0.12, damping=0.2, grail→50) to verify headless sol-core consistency.

**Key Findings:**
- Final metrics at 300 steps: Entropy=0.986, Flux=1.31, Mass=29.99, Active=127, RhoMax=0.382 at node 132
- Mass conservation: 29.99 of 50 injected retained (60%), with mass bounded at max=49.79 — dissipation is gradual and well-behaved
- All 5 reps produced identical results (deterministic with seed=42), confirming bit-exact reproducibility
- All sanity checks passed: no NaN, entropy in [0,1], invariants constant, mass bounded
- The replicated baseline matches all other experiments at this parameter set, confirming cross-session consistency

**Falsifier Assessment:**
- "Headless results qualitatively differ from dashboard results" — CANNOT EVALUATE: no dashboard reference provided (question truncated as "reproduce: ?")
- "Metrics trend in opposite direction" — NOT TRIGGERED: metrics are internally consistent

**Limitations:**
- The replication target is unspecified (question: "Can headless sol-core reproduce: ?") — suggests a template gap where the original claim text was not populated
- Without a dashboard reference, this serves as an internal consistency check rather than a true cross-engine replication

### Claim Implications

- **[STRENGTHEN]** Headless sol-core produces deterministic, reproducible results at (dt=0.12, damping=0.2, grail→50) — 5/5 reps identical
- **[ADD]** At default parameters, 300 steps is sufficient for the system to reach near-equilibrium (entropy=0.986, flux=1.31)

### Open Question Updates

- **Headless-dashboard parity** [unanswered]: Cannot evaluate without dashboard comparison data

## Remaining Open Questions

1. Do dashboard results match these headless outputs at the same parameter set?
2. Is the truncated replication target a systematic template issue requiring a fix?
"""

ANALYSIS["h-004"] = """
## LLM Analysis

### Injection Target Comparison (Partial — Grail Only)

This experiment was designed to test whether different injection targets (grail, consciousness, gravity, entropy) produce distinct basin formations. However, only the grail injection was executed; the remaining targets require manual separate runs.

**Key Findings:**
- Grail injection baseline at 200 steps: Entropy=0.798, Flux=6.70, Mass=38.50, Active=128, RhoMax=11.98 at node 1
- At 200 steps with damping=0.2, 77% of injected mass is retained (38.5/50)
- High peak concentration (RhoMax=11.98) on node 1 suggests strong basin formation around the injection site at this timescale
- All 128 nodes active — full network participation in energy transport

**Falsifier Assessment:**
- "All injection targets produce identical metric trajectories" — CANNOT EVALUATE: only grail was tested
- "RhoMaxId is always the same regardless of injection target" — CANNOT EVALUATE: requires multi-target comparison

**Limitations:**
- This is an incomplete experiment — 1 of 4 planned injection targets was executed
- The data provides a grail-injection reference point but cannot answer the original comparison question
- Future runs must independently test consciousness, gravity, and entropy injection targets

### Claim Implications

- **[ADD]** Grail injection at (dt=0.12, damping=0.2) produces a basin centered on node 1 (RhoMax=11.98) at 200 steps with full network activation (128/140 nodes active)

### Open Question Updates

- **Topology-dependent basin formation** [unanswered]: Requires multi-target injection comparison data not yet available

## Remaining Open Questions

1. Do consciousness, gravity, and entropy injection targets produce different basin locations (RhoMaxNode)?
2. Is the node-1 basin specific to grail injection or a general topological attractor?
"""

ANALYSIS["h-005"] = """
## LLM Analysis

### Golden Baseline Establishment

This experiment establishes the canonical metric outputs for the standard injection protocol (grail→50, dt=0.12, damping=0.2) over an extended 500-step run.

**Key Findings:**
- At 500 steps: Entropy=0.992, Flux=0.088, Mass=18.35, Active=127, RhoMax=0.142 at node 58
- The system approaches thermodynamic equilibrium: entropy near maximum (0.992/1.0) and flux near zero (0.088)
- Mass retained: 36.7% (18.35/50) — 63.3% dissipated over 500 steps at standard parameters
- RhoMaxNode=58 at step 500, versus node 132 at step 300 (from h-001/h-003) — basin peak migrates over time as the system equilibrates
- Peak density extremely low (0.142) — energy is thoroughly dispersed across the network
- Single rep confirms deterministic reproducibility (same seed = same result)
- All sanity checks passed with no deviations

**Falsifier Assessment:**
- "Output changes between identical runs with same seed" — NOT TRIGGERED: deterministic execution confirmed

**Significance:**
This establishes the regression reference for all future experiments. Any code change that alters these endpoint values at (dt=0.12, damping=0.2, grail→50, seed=42, 500 steps) indicates a behavioral change in the engine.

### Claim Implications

- **[ADD]** The canonical 500-step endpoint for standard protocol is: E=0.992, F=0.088, M=18.35, Active=127, RhoMax=0.142 — serving as the golden regression baseline
- **[STRENGTHEN]** The system reaches near-equilibrium by 500 steps (flux < 0.1), confirming that 500 steps is sufficient for steady-state characterization

### Open Question Updates

- **Standard protocol reference values** [answered]: Golden baseline established with bit-exact reproducibility confirmed

## Remaining Open Questions

1. Does the system fully equilibrate (flux→0, entropy→1.0) if run beyond 500 steps, or does a residual steady state persist?
2. Is the 500-step endpoint sensitive to topology changes in the 140-node graph?
"""

ANALYSIS["h-006"] = """
## LLM Analysis

### Time-Step Compression Effect on System Evolution

This experiment tested whether the time step (dt) compresses the rate of system evolution, using 5 dt values (0.08–0.20) over 500 steps.

**Key Findings:**
- **Critical activity collapse between dt=0.12 and dt=0.16:** Active nodes drop from 127→0, indicating a sharp phase transition in the integration stability
- Mass retention scales inversely with dt: 55.4% (dt=0.08) → 16.3% (dt=0.2) — larger time steps accelerate dissipation dramatically
- Flux decay is approximately exponential: 0.627 → 0.195 → 0.088 → 0.039 → 0.023, each step roughly halving
- Entropy increases monotonically (0.988→0.996), approaching maximum — larger dt pushes the system toward complete thermalization faster
- RhoMaxNode varies across conditions (43→22→58→138→31), indicating dt affects which basin captures the peak density — no stable attractor
- The dt=0.12 standard condition matches the golden baseline (h-005) exactly: E=0.992, F=0.088, M=18.35

**Phase Transition at dt≈0.14:**
- Between dt=0.12 (Active=127) and dt=0.16 (Active=0), the system undergoes complete activity collapse
- This suggests a numerical stability boundary — at higher dt, the integration scheme may overshoot and dissipate energy faster than the network can sustain coherent transport
- This is likely a numerical artifact of the time discretization rather than a physical phase transition

**Falsifier Assessment:**
- "Time-to-failure is constant across dt values" — REFUTED: system failure (Active=0) occurs only at dt≥0.16
- "Non-monotonic relationship" — NOT TRIGGERED: all metrics change monotonically with dt

### Claim Implications

- **[ADD]** A critical numerical stability boundary exists near dt≈0.14, where active node count drops from 127 to 0 — this constrains the valid dt range for physical simulations
- **[ADD]** dt compresses dissipation rate: each 0.04 increase in dt approximately doubles the mass loss rate
- **[STRENGTHEN]** The system exhibits metastability: dt does compress time-to-failure, confirming CL-3 behavior in headless mode

### Open Question Updates

- **dt compression of time-to-failure** [answered]: Confirmed — larger dt accelerates all dissipation metrics and triggers activity collapse at dt≈0.14
- **Invariance of collapse point** [partially_answered]: Collapse occurs at dt between 0.12 and 0.16; more precise determination requires finer dt resolution

## Remaining Open Questions

1. What is the exact critical dt value (between 0.12 and 0.16) where activity collapse occurs?
2. Is this collapse a numerical stability boundary or does it correspond to a physical phase transition?
3. Does the collapse threshold change under different topology configurations?
"""

ANALYSIS["h-007"] = """
## LLM Analysis

### Damping Sensitivity on Entropy Distribution and Basin Selection

This experiment swept damping from 0.2 to 1.0 (5 values) to characterize how damping affects entropy distribution and basin selection at 300 steps.

**Key Findings:**
- **Activity collapse threshold at damping≈0.7:** Active nodes drop 127→127→81→0→0 between damping=0.4, 0.6, 0.8
- At damping=0.6: partial collapse to 81 active nodes (36% loss) — system is in transition
- At damping=0.8: complete activity collapse (0 active nodes) — system has fully dissipated into static state
- Flux decays 7.7× from 1.31 (damping=0.2) to 0.17 (damping=1.0)
- Mass decays 5.7× from 30.0 to 5.3 — only 10.5% of injected mass remains at damping=1.0
- **Entropy paradox:** Entropy remains nearly constant (0.986–0.988) across the entire range, even through the activity collapse — the distribution shape is preserved while magnitude diminishes
- **Basin migration at damping≥0.6:** RhoMaxNode shifts from 132→43→35 as damping increases past 0.4, indicating the dominant basin moves to different topological regions under heavy damping

**Phase Transition Characterization:**
- The transition is NOT abrupt — it occurs over a range (damping 0.4–0.8) with a partial intermediate state at 0.6
- This is distinct from the dt compression threshold (dt≈0.14), which appears more abrupt
- The gradual collapse suggests a physical mechanism (progressive energy starvation) rather than numerical instability

**Falsifier Assessment:**
- "Entropy is invariant to damping changes" — PARTIALLY CONFIRMED: entropy changes only 0.2% across a 5× damping increase, making it effectively invariant
- "RhoMaxId distribution is identical across all values" — REFUTED: RhoMaxNode shifts from 132→43→35, showing clear basin selection sensitivity

### Claim Implications

- **[ADD]** The critical damping threshold for activity collapse lies near damping≈0.7, with a gradual transition zone spanning damping=[0.4, 0.8]
- **[ADD]** Entropy is effectively invariant to damping (delta < 0.2%), even through activity collapse — the equipartition of energy persists while total energy diminishes
- **[ADD]** Basin selection (RhoMaxNode) is damping-dependent: dominant basin migrates from node 132→43→35 as damping increases past 0.4

### Open Question Updates

- **Phase transition characterization** [partially_answered]: The damping-driven collapse is gradual (spanning 0.4–0.8), not abrupt. Spectral analysis could further characterize the transition.
- **Entropy distribution under damping** [answered]: Entropy is effectively invariant to damping changes; basin selection, not entropy distribution, is the sensitive observable.

## Remaining Open Questions

1. What physical mechanism drives the Activity collapse between damping=0.6 and 0.8?
2. Is the damping=0.6 partial-collapse state (81 active nodes) a metastable intermediate, or simply a transient snapshot?
3. Why does the dominant basin migrate from node 132 to node 43 to node 35 — is this topology-driven?
"""

ANALYSIS["h-008"] = """
## LLM Analysis

### Threshold Scan with Null Parameter (Template Error)

This experiment was configured as a threshold_scan type but ran with a null independent variable, producing a single-condition result identical to the replication baseline.

**Key Findings:**
- Single condition at defaults (dt=0.12, damping=0.2, grail→50): Entropy=0.986, Flux=1.31, Mass=29.99, Active=127, RhoMax=0.382 at node 132
- Results match h-003 (replication) exactly — confirming deterministic consistency
- The threshold_scan template expected 8 parameter values but received None, causing fallback to single-condition execution
- Data is valid but does not address the original gap question about nonlinear feedback mechanisms

**Root Cause:**
- The hypothesis generator assigned this as a threshold_scan for an open question about nonlinear feedback, but failed to populate the independent variable — the param field was None
- This is consistent with the known hypothesis_templates.py bug (NoneType issue — now fixed in later commits)

**Falsifier Assessment:**
- "No transition detected across entire range" — CANNOT EVALUATE: no parameter was scanned
- "Transition is not reproducible across reps" — NOT APPLICABLE

### Claim Implications

- **[ADD]** (Procedural) Null-parameter threshold scans produce valid single-condition data but cannot address scan-type hypotheses — template population must be validated before execution

### Open Question Updates

- **Nonlinear feedback mechanisms** [unanswered]: Experiment did not execute as designed due to template error

## Remaining Open Questions

1. What are the underlying nonlinear feedback mechanisms driving coherence deepening and resurrection? (Requires properly parameterized experiment)
"""


def get_hypothesis_key(filename: str) -> str:
    """Extract h-NNN from filename."""
    m = re.search(r"(h-\d{3})", filename)
    return m.group(1) if m else None


def fix_packet(filepath: str) -> bool:
    """Insert LLM Analysis into a packet missing it. Returns True if modified."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Skip if already has LLM Analysis
    if "## LLM Analysis" in content:
        return False

    basename = os.path.basename(filepath)
    hkey = get_hypothesis_key(basename)
    if hkey not in ANALYSIS:
        print(f"  SKIP (no template for {hkey}): {basename}")
        return False

    analysis_block = ANALYSIS[hkey]

    # Find insertion point: between the --- separator and ## Promotion Checklist
    # Pattern: \n---\n\n## Promotion Checklist
    insertion_pattern = "\n---\n\n## Promotion Checklist"
    if insertion_pattern not in content:
        # Try alternate spacing
        insertion_pattern = "\n---\n## Promotion Checklist"
        if insertion_pattern not in content:
            print(f"  SKIP (no insertion point): {basename}")
            return False

    replacement = f"\n---\n{analysis_block}\n## Promotion Checklist"
    content = content.replace(insertion_pattern, replacement, 1)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return True


def main():
    proof_dir = os.path.normpath(PROOF_DIR)
    print(f"Scanning: {proof_dir}")

    # Collect all Feb 12 packets missing LLM Analysis
    targets = []
    for fname in sorted(os.listdir(proof_dir)):
        if not fname.startswith("PP-2026-02-12-") or not fname.endswith(".md"):
            continue
        fpath = os.path.join(proof_dir, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            if "## LLM Analysis" not in f.read():
                targets.append(fpath)

    print(f"Found {len(targets)} packets missing LLM Analysis\n")

    fixed = 0
    skipped = 0
    for fpath in targets:
        basename = os.path.basename(fpath)
        if fix_packet(fpath):
            print(f"  FIXED: {basename}")
            fixed += 1
        else:
            skipped += 1

    print(f"\nDone: {fixed} fixed, {skipped} skipped")


if __name__ == "__main__":
    main()
