---
mrc_id: MRC-CHN-001
title: "Topological Mass-Wave Three-Channel Communication Protocol"
type: "mass_wave"
topological_regime: "dynamic"
parameters:
  direct_w: 1.0
  crosstalk_w: [0.0, 0.2, 0.5]
  damping: [2.0, 8.0, 15.0]
  t_pulse: 5
  t_silent: [15, 25]
metrics:
  high_inj_ideal:
    ser: 58.3%
    throughput: 0.0330 bits/tick
    splitted: "Yes (9 -> 227 nodes)"
  low_inj_ideal:
    ser: 50.0%
    throughput: 0.0396 bits/tick
    splitted: "Yes (9 -> 67 nodes)"
  low_inj_med_crosstalk_sil25:
    ser: 50.0%
    throughput: 0.0264 bits/tick
    splitted: "Yes (9 -> 47 nodes)"
  low_inj_med_crosstalk_hidamp_sil25:
    ser: 41.7%
    throughput: 0.0308 bits/tick
    splitted: "Yes (9 -> 22 nodes)"
harness: "scratch/agent_communication_test.py"
verification_command: "uv run --with selenium --with numpy python scratch/agent_communication_test.py"
---

# Topological Mass-Wave Three-Channel Communication Protocol

This profile logs the performance of agent-to-agent communication through continuous mass-wave signaling. Senders inject mass pulses, relays propagate density waves, and receivers decode symbols via integrated density max-detection.

## 1. Core Discoveries & Channel Limits

*   **Topological Channel Dispersion:** Mass pulses accumulate density, causing edge flux to exceed the `EXPANSION_LIMIT` of `25.0`. This triggers topological splitting, diluting the signal among dynamic bridge nodes and causing decoding errors.
*   **Damping vs. Inter-Symbol Interference (ISI):**
    *   **Low Damping ($\alpha=2.0$):** Massive splitting (542 nodes) and severe ISI (SER = 66.7%). Residual mass remains in the channel, garbling subsequent symbols.
    *   **High Damping ($\alpha=15.0$):** Restricts splitting (22 nodes) and rapidly decays residual mass, improving communication fidelity (SER drops to 41.7%).
*   **Propagation Delay & Shannon Capacity:** The continuous state-space acts as a dispersive medium. Symbol windows must be tuned to match the transmission delay and damping to prevent signal spillover.

## 2. Parameter Sensitivity Summary

*   **Longer Silence Windows ($T_{\text{silent}} = 25$):** Consistently outperforms shorter windows by allowing more mass decay, reducing inter-symbol crosstalk.
*   **Low Inflows ($I_0 = 15.0$):** Restricts the expansion size compared to high inflows ($I_0 = 120.0$), but still triggers dynamic splitting due to accumulation. Static-regime communication requires inflows strictly below the accumulation flux thresholds.
