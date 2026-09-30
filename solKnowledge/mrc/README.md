# Manifold Resonance Codex (MRC)

Welcome to the **Manifold Resonance Codex (MRC)**—the recursive agentic library for the continuous state-space SOL engine. 

Unlike static documentation, the MRC represents insights as **reproducible attractors, channels, and physical invariants** of a Riemann manifold network. It provides a machine-readable directory structure and schemas that allow future agents to read, write, and programmatically verify discoveries through simulation harnesses.

---

## 1. Directory Structure

The Codex is organized into three core divisions:
*   `invariants/`: The mathematical foundations, governing conservation equations, and core physics solvers.
*   `attractors/`: Profiles of dynamic attractors, steady states, and periodic limit cycles (such as single and multi-chamber breathing).
*   `channels/`: Empirical evaluations of information transmission protocols, propagation limits, and Shannon boundaries.

---

## 2. Agentic Schema Standards

To ensure entries are readable by both human engineers and AI sub-agents, every document in the Codex must begin with a YAML frontmatter section.

### Attractor Profile Template (`attractors/`)
```yaml
---
mrc_id: MRC-ATT-XXX
title: "[Attractor Name]"
type: "limit_cycle | stable_equilibrium | chaotic_attractor"
physics_version: "v3.8-nodal"
parameters:
  damping: 8.0
  pressure_c: 45.0
  inflow: 150.0
metrics:
  nodes: [min_n, max_n]
  mass: [min_m, max_m]
  te_scale: 1e10
  period_ticks: 94
harness: "scratch/[test_script].py"
verification_command: "uv run --with selenium --with numpy python scratch/[test_script].py"
---
```

### Channel Profile Template (`channels/`)
```yaml
---
mrc_id: MRC-CHN-XXX
title: "[Channel Name]"
type: "mass_wave | belief_drift"
topological_regime: "static | dynamic"
parameters:
  damping: 8.0
  crosstalk: 0.2
  inflow: 15.0
  t_pulse: 5
  t_silent: 25
metrics:
  symbol_error_rate: 0.417
  throughput_bits_per_tick: 0.0308
harness: "scratch/[test_script].py"
verification_command: "uv run --with selenium --with numpy python scratch/[test_script].py"
---
```

### Invariant Profile Template (`invariants/`)
```yaml
---
mrc_id: MRC-INV-XXX
title: "[Invariant Name]"
formulation: "fv_discrete | continuous"
governing_equations:
  - "equation_1"
  - "equation_2"
verification_script: "scratch/[verification_script].py"
---
```

---

## 3. Recursive Verification Protocol (The Agentic Loop)

When a sub-agent is spawned to work on the SOL engine, it should execute the following verification loop:
1.  **Read:** Parse the MRC documents to understand current capabilities, parameters, and baseline metrics.
2.  **Verify:** Run the `verification_command` listed in the frontmatter of any attractor or channel under study.
3.  **Validate:** Load the output CSV files and check if the computed nodes, mass, and energy ranges match the recorded `metrics` within a $\pm 5\%$ tolerance window.
    *   *If validation passes:* The codebase remains stable.
    *   *If validation fails:* A regression has occurred. Stop and alert the parent agent.
4.  **Log:** If a new attractor or channel behavior is discovered through R&D, write a new profile using the templates above and append it to the index.
