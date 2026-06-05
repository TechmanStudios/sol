# SOL LogosVM 2-Bit Serial Adder Loop Report

This report verifies physical dynamic pointer memory addressing and serial looping arithmetic.

## 1. Experimental Verdict

**Overall Suite Status**: **PASSED**

## 2. Serial Adder Loop Measurements

| Inputs (X + Y + Cin) | Expected SUM | Got SUM (S1, S0, Cout) | Status |
| :---: | :---: | :---: | :---: |
| 1 + 1 + 0 | 2 | 10 (Cout=0) | OK |
| 2 + 1 + 0 | 3 | 11 (Cout=0) | OK |
| 3 + 1 + 0 | 4 | 00 (Cout=1) | OK |
| 3 + 3 + 0 | 6 | 10 (Cout=1) | OK |
| 2 + 2 + 1 | 5 | 01 (Cout=1) | OK |
| 0 + 0 + 0 | 0 | 00 (Cout=0) | OK |

## 3. Analysis & Key Discoveries
- **Dynamic Physical Addressing**: The sequencer successfully executes dynamic memory pointers (`LOAD_INDIRECT` and `STORE_INDIRECT`) driven by the physical state of the address register.
- **Procedural Carry Propagation**: The serial adder correctly preserves the carry bit across loop iteration boundaries by writing to and reading from a temporary carry basin, completing the addition without unrolling the program.
- **Hardware Mass Integrity**: Active registers consistently preserve semantic mass above the critical limit, ensuring no signal degradation during complex control loops.
