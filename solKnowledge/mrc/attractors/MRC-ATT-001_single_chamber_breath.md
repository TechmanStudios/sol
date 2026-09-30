---
mrc_id: MRC-ATT-001
title: "Single-Chamber Thermodynamic Breathing Attractor"
type: "limit_cycle"
physics_version: "v3.8-nodal"
parameters:
  damping: 8.0
  pressure_c: 45.0
  inflow_rates: [50.0, 150.0]
metrics:
  50_inflow:
    nodes: [2223, 2429]
    mass: [469.59, 470.24]
    ke: [3.56e9, 7.71e10]
    period_ticks: 69
  150_inflow:
    nodes: [7521, 7976]
    mass: [1408.79, 1410.06]
    ke: [3.11e10, 6.23e10]
    period_ticks: 94
harness: "scratch/trace_breathing.py"
verification_command: "uv run --with selenium --with numpy python scratch/trace_breathing.py"
---

# Single-Chamber Thermodynamic Breathing Attractor

This limit cycle is an emergent macroscopic attractor. When mass is continuously injected into opposite corners of the Exciton lattice, momentum advection drives localized pressure surges. To dissipate this kinetic energy, the manifold dynamically splits edges to insert bridge nodes, expanding its volume. As mass decays via damping, the nodes contract and prune, leading to periodic "breathing" oscillations.

## 1. Phase-Space Properties

*   **Mass Variance Homogenization:** Under high load ($150.0$), the mean density variance drops to **0.1289**, showing that the expanding topology acts to homogenize and buffer extreme localized density surges.
*   **Orthogonal Phase Trajectory:** Correlation between Node Count and Kinetic Energy is near zero ($r \approx -0.15$ to $+0.08$), reflecting a $90^\circ$ phase lag in the cycle orbit (KE peaks during expansion, and drops during contraction).
*   **Scale-Dependent Period Stretching:** Higher inflow rates increase the limit cycle period ($69 \to 94$ ticks) because propagating momentum waves across larger graph sizes takes more steps.
