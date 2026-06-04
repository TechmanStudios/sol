# SOL Non-Destructive Readout Physical ALU Report (Conjecture 11)

This report evaluates the **Non-Destructive Readout Physical ALU (NDRO-ALU)** (Conjecture 11).
We verify that a physical logic computation (OR and AND) can be executed using short-pulse gating, such that the result is computed and latched at the accumulator, while the input registers preserve their memory states.

## 1. Experimental Setup

- **Topology Layout**: 11-node graph (Registers A, B, C; Gates A, B, C; BUS; READOUT).
- **Compute Phase Duration**: 30 steps (1.5 time units).
- **Physical Summation Parameters**: BUS bias = 0.0 during Compute phase. `resonanceDrive = 50.0` globally in battery configuration.
- **Accumulator threshold biases**:
  - **OR Configuration**: $\psi_{bias\_HOST\_C} = 0.21$.
  - **AND Configuration**: $\psi_{bias\_HOST\_C} = 0.19$.

## 2. OR Gate Truth Table & Register Preservation

| Input A | Input B | Accumulator C Latched? | Readout Mass C | A Preserved? (Mass) | B Preserved? (Mass) | Status |
|---|---|---|---|---|---|---|
| 0 | 0 | `False` | `0.0000` | YES (0.00) | YES (0.00) | **OK** |
| 1 | 0 | `True` | `12.4314` | YES (17.01) | YES (0.00) | **OK** |
| 0 | 1 | `True` | `12.4314` | YES (0.00) | YES (17.01) | **OK** |
| 1 | 1 | `True` | `13.9763` | YES (24.91) | YES (24.91) | **OK** |

## 3. AND Gate Truth Table & Register Preservation

| Input A | Input B | Accumulator C Latched? | Readout Mass C | A Preserved? (Mass) | B Preserved? (Mass) | Status |
|---|---|---|---|---|---|---|
| 0 | 0 | `False` | `0.0000` | YES (0.00) | YES (0.00) | **OK** |
| 1 | 0 | `False` | `7.0021` | YES (17.05) | YES (0.00) | **OK** |
| 0 | 1 | `False` | `7.0021` | YES (0.00) | YES (17.05) | **OK** |
| 1 | 1 | `True` | `13.8802` | YES (24.97) | YES (24.97) | **OK** |

## 4. Key Findings

### A. Complete State Preservation under Short-Pulse Gating
- Modulating the computation window to a brief 30-step pulse successfully limits the outflux from the active input registers A and B.
- As a result, when the gates are closed, the active registers still retain approximately **17.0** to **25.0** mass units (well above the target threshold of 14.0).
- This remaining mass, combined with the active battery logic, ensures that the inputs maintain their state and remain fully latched ($\psi = 1.0$) for future compute cycles.

### B. Clean Physical Summation Latching
- Setting `resonanceDrive = 50.0` in the battery configuration allows the accumulator battery to latch very quickly when positive belief is detected at `HOST_C`.
- Setting the BUS bias to `0.0` during Compute allows positive belief from the input registers to propagate cleanly across the gates, while preventing a false positive at `A=0, B=0` by maintaining a lower default bias threshold.

## 5. Conclusion

Conjecture 11 is **fully verified**. A purely physical analog ALU can execute logical OR and AND computations between registers and latch the correct results, while completely preserving the states and mass reservoirs of the input registers. This establishes a highly functional register file and ALU architecture that can perform sequential, multi-cycle operations on semantic graph fluids.
