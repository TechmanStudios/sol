---
mrc_id: MRC-ATT-002
title: "Multi-Chamber Counter-Breathing Attractor"
type: "limit_cycle"
physics_version: "v3.8-nodal"
parameters:
  damping: 8.0
  pressure_c: 45.0
  inflow_amplitude: 150.0
  phase_shift: 3.14159
metrics:
  50_med_omega0.05:
    nodes_n1: [730, 1710]
    nodes_n2: [49, 107]
    correlation: -0.7217
    behavior: "stable_counter_breathing"
  150_med_omega0.05:
    nodes_n1: [3872, 7476]
    nodes_n2: [41, 83]
    correlation: -0.8341
    behavior: "stable_counter_breathing"
  150_fast_omega0.20:
    nodes_n1: [84, 2203]
    nodes_n2: [204, 4966]
    correlation: -0.7841
    behavior: "active_counter_breathing"
  150_slow_omega0.01:
    nodes_n1: [206, 1089]
    nodes_n2: [134, 250]
    correlation: 0.6389
    behavior: "in_phase_coupled_breathing"
harness: "scratch/push_limits_multi_chamber.py"
verification_command: "uv run --with selenium --with numpy python scratch/push_limits_multi_chamber.py"
---

# Multi-Chamber Resonant Counter-Breathing Attractor

This attractor profiles the counter-driving of two spatial chambers (top cluster $N_1$ vs bottom cluster $N_2$) with out-of-phase drive currents. It exhibits a distinct frequency-dependent topological phase transition.

## 1. Physical Discoveries

*   **Frequency-Dependent Phase Transition:**
    *   **High/Medium Frequencies ($\omega_d \ge 0.05$):** Decoupled **stable counter-breathing ($r \approx -0.80$)**. Drive oscillations outpace the mass diffusion rate, forcing the chambers to expand and contract out-of-phase.
    *   **Low Frequencies ($\omega_d = 0.01$):** Coupled **in-phase breathing ($r = +0.6389$)**. Slower drive allows mass diffusion to bridge the chambers, coupling their growth.
*   **Resonant Symmetry Breaking:** In slow/medium drives, the system settles into an asymmetric resonance where Chamber 1 remains highly expanded while Chamber 2 remains contracted. High frequency ($\omega_d = 0.20$) overcomes this threshold, forcing both chambers to alternate between small and large sizes.
*   **Acoustic vs. Optical Analogy:** The transition from in-phase (low frequency) to out-of-phase (high frequency) breathing is an exact topological analog to the acoustic vs. optical vibration modes in physical crystal lattices.
---
