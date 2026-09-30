# SOL LogosVM Compiled 4-Bit Serial Adder Loop Report

This report verifies CFG-aware compiler generation of physical 2-bit pointers and loops.

## 1. Experimental Verdict

**Overall Suite Status**: **PASSED**

## 2. Serial Adder Loop Measurements

| Inputs (X + Y + Cin) | Expected SUM | Got SUM (S3, S2, S1, S0, Cout) | Status |
| :---: | :---: | :---: | :---: |
| 0 + 0 + 0 | 0 | 0000 (Cout=0) | OK |
| 5 + 3 + 0 | 8 | 1000 (Cout=0) | OK |
| 7 + 8 + 0 | 15 | 1111 (Cout=0) | OK |
| 15 + 1 + 0 | 16 | 0000 (Cout=1) | OK |
| 12 + 10 + 1 | 23 | 0111 (Cout=1) | OK |
| 15 + 15 + 1 | 31 | 1111 (Cout=1) | OK |
| 9 + 6 + 0 | 15 | 1111 (Cout=0) | OK |
| 2 + 2 + 0 | 4 | 0100 (Cout=0) | OK |

## 3. Analysis & Key Discoveries
- **CFG-Aware Iterative Liveness**: The compiler successfully resolved liveness sets across jumps and backward control loops, ensuring no registers were prematurely cleared or incorrectly allocated.
- **Unified Register Allocation**: Register allocations, evacuations, and context-saving (via PtrTempC/PtrTempD/LoopCounterBTemp) compiled cleanly and optimally.
- **Arithmetic Accuracy**: The compiled 4-iteration serial addition loop program executed flawlessly on the 21-basin semantic manifold, producing correct sums and carry bits across all 8 trials, and cleanly collapsing registers to `-1` at program exit.
