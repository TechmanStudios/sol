# SOL LogosVM 4-Bit Serial Subtractor Exhaustive Verification Report

This report verifies exact arithmetic correctness and physical invariants of the 4-bit serial subtractor across the entire input space.

## 1. Experimental Verdict

- **Overall Suite Status**: **PASSED**
- **Passing Cases**: `512 / 512` (100.0%)
- **Failure Rate**: `0.0`
- **Total Runtime**: `5299.34 seconds`

## 2. Invariant Envelope Performance

| Invariant Metric | Measured Worst-Case | Limit / Threshold | Status |
| :--- | :---: | :---: | :---: |
| `min_active_register_mass` | 90.55 | $\ge 14.0$ | OK |
| `max_source_basin_delta` | 0.0000 | No sign flip & low drift | OK |
| `max_residual_flux_exit` | 0.000754 | $< 0.01$ | OK |
| `max_bus_rho_exit` | 0.0000 | $< 1.0$ | OK |

## 3. Analysis & Key Discoveries
- **Exhaustive Subtraction Correctness**: The 4-iteration subtractor loop computes borrow propagation and differences correctly across all 512 inputs.
- **Active Register Mass Stability**: Active register mass remains extremely stable throughout the loop, staying far above the minimum threshold of 14.0.
- **Clean Register State Termination**: All registers collapse cleanly back to -1 upon program completion, proving no residual memory retention.
