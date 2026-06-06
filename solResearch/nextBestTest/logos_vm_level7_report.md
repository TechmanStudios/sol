# SOL LogosVM Level 7 Carry-Select Parallel Adder Verification Report

This report verifies the correctness and physical invariants of the three-lobe 8-bit Carry-Select Adder topology running on a parallel-gated multi-core substrate.

## 1. Experimental Verdict

| Metric | Value | Limit / Threshold | Status |
| :--- | :---: | :---: | :---: |
| **Overall Suite Status** | **PASSED** | Level 7.0 Parallel | OK |
| **Passing Cases** | `16 / 16` (100.0%) | 100.0% accuracy | OK |
| **Failure Rate** | `0.0` | 0.0 | OK |
| **Total Runtime** | `764.01 seconds` | N/A | OK |

## 2. Invariant Envelope Performance

| Invariant Metric | Measured Worst-Case | Limit / Threshold | Status |
| :--- | :---: | :---: | :---: |
| `min_active_register_mass` | 97.88 | $\ge 14.0$ | OK |
| `max_source_basin_delta` | 0.0000 | No sign flip & low drift | OK |
| `max_residual_flux_exit` | 0.000748 | $< 0.01$ | OK |
| `max_bus_rho_exit` | 0.0000 | $< 1.0$ | OK |

## 3. Analysis & Key Discoveries
- **Spatial Multi-Core Scaling**: Instantiating 12 registers organized as three independent cores (Core 0, 1, and 2) allows us to execute low and high nibble operations in parallel.
- **Speculative Execution Carry-Select**: High nibble computation is successfully evaluated in parallel for both potential carry values (0 and 1) simultaneously. Dynamic conditional moves (`CMOVE` selection sequence) choose the correct final output based on Lobe 0's actual $C_4$ carry-out.
- **Physics Invariant Compliance**: The parallel multi-core configuration maintains strict mass thresholds, low residual edge flux, and clean register collapse upon reset.
