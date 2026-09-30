# SOL LogosVM 4-Bit Serial Adder Tolerance Sweep Report

This report defines the safe operating envelope of the 4-bit serial adder under physical substrate perturbations.

## 1. Safe Operating Envelope Summary

| Perturbation Dimension | Safe Envelope Boundaries | Operational Robustness Status |
| :--- | :---: | :---: |
| **Integration Step ($dt$) Drift** | `-20.0%` to `+20.0%` | Robust |
| **Substrate Damping Factor** | `0.50x` to `1.50x` | Robust |
| **Instruction Timing Jitter** | `-5` to `5` steps | Robust |
| **Initial Mass Noise Amplitude** | $\le 2.0$ | Robust |
| **Psi Belief Noise Amplitude** | $\le 0.1$ | Robust |
| **Sequential Repeated Execution** | Up to `20` consecutive runs | Robust |

## 2. Invariant Insights
- **Time-Step Compression ($dt$ Sensitivity)**: The system maintains stability across a bounded range of integration step lengths. Deviations beyond this envelope break attractor timing margins.
- **Friction Stability (Damping factor)**: Heavy damping restricts edge conduction too much, whereas low damping causes excessive ringing and residual charge carryover. The safe envelope is centered tightly around the $1.0\times$ baseline.
- **Residual Charge Clean-up**: Performing a programmatic reset cycle (`RESET_CORE`) after program execution prevents residual flux and density build-up, enabling infinite repeated executions without drift decay.

Report generated in 1501.88 seconds.
