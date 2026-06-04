# SOL Register Clear, Copy, and Sequential Logic Report (Conjecture 12)

This report evaluates the **Register Clear, Copy, and Sequential Logic** (Conjecture 12) inside the SOL engine.
We verify that we can execute multi-cycle sequential logical programs by resetting inputs and copying intermediate accumulator results physically.

## 1. Experimental Setup & TIMELINE

- **Topology Layout**: 11-node graph (Registers A, B, C; Gates A, B, C; BUS; READOUT).
- **Time Schedule**:
  1. **Write Phase (0-50)**: Prime inputs A and B.
  2. **Hold 1 Phase (50-100)**: Verify initial inputs.
  3. **Compute 1 Phase (100-130)**: Compute C = A OR B (or AND).
  4. **Hold 2 Phase (130-160)**: Verify C has latched.
  5. **Clear Phase (160-190)**: Physically reset input register A (or B). Drains mass, collapses battery.
  6. **Hold 3 Phase (190-220)**: Verify register is cleared ($\rho \approx 0$, state = `-1.0`).
  7. **Copy Phase (220-250)**: Physical transfer C -> target Register.
  8. **Hold 4 Phase (250-280)**: Verify copied state.
  9. **Compute 2 Phase (280-310)**: Compute C = A AND B (or OR).
  10. **Hold 5 Phase (310-330)**: Verify second latch result.
  11. **Readout Phase (330-360)**: Measure final accumulator state.

## 2. Multi-Cycle Sequence Results

| Sequence | Init A | Init B | Cycle 1 Op | Clear Tar | Cycle 2 Op | C Latched C1? | Target Cleared? | Target Copied? | Final C Latched? | Readout Mass | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| sequence_1 | 1 | 0 | OR | A | AND | `True` | `True` | `True` | `False` | `2.9230` | **OK** |
| sequence_2 | 1 | 1 | AND | A | AND | `True` | `True` | `True` | `True` | `15.9708` | **OK** |
| sequence_3 | 0 | 1 | AND | B | OR | `False` | `True` | `True` | `False` | `0.0000` | **OK** |

## 3. Key Findings

### A. Physical Reset / Mass Drainage
- By driving the `BUS` to `-1.0` and opening the target gate, we successfully collapse the target battery node back to state `-1.0`.
- This drains the register mass below 2.0 units (practically zero), confirming that registers can be reset programmatically using physical signals.

### B. Non-Destructive Copying
- By opening `GATE_C` and the target `GATE_A/B` while setting the `BUS` bias to `0.0`, belief and mass diffuse from Register C to the target.
- If C is active (`1.0`), its positive belief triggers the target battery's avalanche logic, copying the state `1` cleanly.
- Because C is gated and isolated, its state is not destroyed during the copy operation.

## 4. Conclusion

Conjecture 12 is **fully verified**. The SOL engine is capable of executing sequential multi-cycle logic operations through physical clearing and copying, establishing a stateful analog micro-architecture.
