# sol-core — Headless SOL Engine

Phase 0 deliverable of the **SOL Hippocampus Roadmap**.

A pure-Python implementation of the SOL simulation engine, transcribed verbatim
from `sol_dashboard_v3_7_2.html`'s `SOLPhysics` class, `CapLaw`, and metrics
computations. Zero browser/DOM dependencies — runs from Python scripts, agents,
or the command line.

## ⚠️ Sacred Math

The core physics equations (pressure, flux transport, psi diffusion,
conductance, CapLaw, Lighthouse Protocol) are transcribed **verbatim** from the
dashboard. They must NOT be modified without updating `sol_mathFoundation.md`.

---

## Files

| File | Purpose |
|---|---|
| `sol_engine.py` | Core physics engine (`SOLPhysics`, `SOLEngine`, CapLaw, metrics, snapshot/restore) |
| `sol_engine.mjs` | JavaScript ESM version (same physics, for future Node.js use) |
| `default_graph.json` | The canonical 140-node, 845-edge semantic graph |
| `cli.py` | Command-line interface for running simulations |
| `auto_run.py` | **Phase 1** — Protocol-driven pipeline: execute + analyze + emit run bundle |
| `protocol_schema.json` | JSON Schema for protocol files |
| `protocols/` | Sample protocol JSON files |
| `test_api.py` | Quick API verification script |
| `test_phase1.py` | Phase 1 end-to-end API test suite |

### Analysis Library (`../analysis/`)

| File | Purpose |
|---|---|
| `metrics.py` | Derived metrics: entropy/flux/mass stats, convergence rate, threshold bracketing |
| `sanity.py` | Invariant checks, sample size, mass conservation, NaN detection |
| `report.py` | Markdown run bundle + comparison table generation |

---

## Quick Start

### Smoke Test
```bash
cd tools/sol-core
python cli.py smoke
```

### Python API
```python
from sol_engine import SOLEngine

engine = SOLEngine.from_default_graph()
engine.inject("grail", 50)

for _ in range(200):
    engine.step()

metrics = engine.compute_metrics()
print(metrics)
# → {'entropy': 0.52, 'totalFlux': 5.8, 'mass': 40.1, 'activeCount': 128, ...}
```

### CLI Usage
```bash
# Basic run
python cli.py run --steps 200 --inject grail:50

# JSON output
python cli.py run --steps 200 --inject grail:50 --json

# Write per-step CSV
python cli.py run --steps 500 --inject grail:50 --csv results.csv --every 10

# Parameter sweep
python cli.py sweep --param damping --range 0.05,0.1,0.2,0.5 --steps 200 --inject grail:50
```

---

## API Reference

### `SOLEngine` (high-level wrapper)

| Method | Description |
|---|---|
| `SOLEngine.from_default_graph(**kwargs)` | Create engine with the canonical 140-node graph |
| `SOLEngine.from_graph(nodes, edges, **kwargs)` | Create engine from custom graph data |
| `engine.inject(label, amount)` | Inject density into a node by label (fuzzy match) |
| `engine.inject_by_id(node_id, amount)` | Inject density by node ID |
| `engine.step(dt, c_press, damping)` | Advance one tick; returns `{totalFlux, activeCount}` |
| `engine.run(steps)` | Run N steps; returns list of per-step results |
| `engine.compute_metrics()` | Full metric snapshot (entropy, flux, mass, etc.) |
| `engine.save_baseline()` | Save node+edge state for later restore |
| `engine.restore_baseline(snap?)` | Restore to saved state |
| `engine.get_node_states()` | Compact list of `{id, label, group, rho, p, psi}` |
| `engine.t` | Current simulation time |
| `engine.step_count` | Total steps executed |

### Constructor kwargs

| Param | Default | Description |
|---|---|---|
| `dt` | 0.12 | Time step |
| `c_press` | 0.1 | Pressure coefficient in P = c·log(1 + ρ/m) |
| `damping` | 0.2 | Density damping rate |
| `cap_law` | None | CapLaw config dict (see below) |
| `rng_seed` | 42 | Deterministic PRNG seed |

### Low-Level Functions

| Function | Description |
|---|---|
| `create_engine(nodes, edges, ...)` | Factory → `(SOLPhysics, cap_law_info)` |
| `compute_all_edges(nodes, edges, ...)` | Build edge list with optional all-to-all background |
| `apply_cap_law(physics, cap_law)` | Apply degree-power capacitance law |
| `compute_metrics(physics)` | Compute entropy, flux, mass, etc. |
| `snapshot_state(physics)` | Serialize current state |
| `restore_state(physics, snap)` | Restore from snapshot |

---

## Physics Summary

The engine simulates a **semantic graph** where nodes carry density (ρ), pressure
(P), and a belief field (ψ). The core loop per tick:

1. **Psi diffusion** — ψ evolves via graph Laplacian + bias relaxation
2. **Semantic mass decay** — constellation nodes lose mass over time
3. **Pressure** — P = c · log(1 + ρ/m) (equation of state)
4. **Conductance** — edges shaped by ψ, MHD field, and battery states
5. **Battery update** — Lighthouse nodes charge/discharge/flip
6. **Phase-gated flux** — Lighthouse Protocol: cos(ω·t·10) gates which
   domain layers (tech/spirit/bridge) can transport density
7. **Damping** — density decays each tick
8. **MHD** — magnetic field builds from flux, decays exponentially
9. **Jeans collapse** — high ρ/P nodes accrete mass from neighbors

---

## For Agents

This module is designed to be imported directly by SOL agents:

```python
# In an experiment runner or auto-mapper
from tools.sol_core.sol_engine import SOLEngine, compute_metrics

engine = SOLEngine.from_default_graph(damping=0.15)
engine.inject("consciousness", 50)
results = engine.run(300)
metrics = engine.compute_metrics()

# Compare against baseline
engine.save_baseline()
engine.inject("gravity", 25)
engine.run(100)
delta = engine.compute_metrics()
engine.restore_baseline()
```

### Protocol-Driven Experiments (Phase 1)

Agents can run full experiments via protocol JSON:

```python
from tools.sol_core.auto_run import execute_protocol

protocol = {
    "seriesName": "my_experiment",
    "question": "Does X affect Y?",
    "invariants": {"dt": 0.12, "c_press": 0.1, "rng_seed": 42},
    "knobs": {"damping": [0.1, 0.2, 0.5]},
    "injections": [{"label": "grail", "amount": 50}],
    "steps": 200,
    "reps": 5,
    "baseline": "fresh",
}

results = execute_protocol(protocol, out_dir="results/my_experiment")

# Results contain:
#   summary    — condition count, runtime, total steps
#   conditions — per-condition final metrics + analysis
#   comparison — cross-condition comparison table
#   sanity     — invariant checks, mass conservation, NaN detection
#   run_bundle — audit-ready Markdown run bundle
#   exports    — paths to CSV + Markdown files
```

### CLI
```bash
# Run a protocol
python auto_run.py protocols/damping_sweep_smoke.json

# Custom output directory + JSON output
python auto_run.py protocols/my_experiment.json --out-dir results/ --json
```

---

## Provenance

- **Source**: `sol_dashboard_v3_7_2.html`, lines 6355–10960
- **Extraction date**: 2025-02-07
- **Graph**: 140 nodes, 845 edges (canonical default graph)
- **Parity status**: Smoke-tested; full tick-by-tick parity with dashboard TBD
