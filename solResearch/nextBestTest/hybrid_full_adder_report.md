# SOL Hybrid Sub-system 1-Bit Full-Adder Verification Report

This report verifies the Register-Based 1-Bit Full-Adder circuit on the Level 5 Manifold-Systems substrate.

## 1. Experimental Verdict

**Overall Suite Status**: **PASSED**

## 2. Full-Adder Truth Table & Measurements

| Input A | Input B | Input Cin | Exp Sum | Exp Cout | Got Reg C (SUM) | Got Reg D (COUT) | Got Basin SUM | Got Basin COUT | Status |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 0 | 0 | 0 | 0 | 0 | -1.0 | -1.0 | 0 | 0 | OK |
| 1 | 0 | 0 | 1 | 0 | 1.0 | -1.0 | 1 | 0 | OK |
| 0 | 1 | 0 | 1 | 0 | 1.0 | -1.0 | 1 | 0 | OK |
| 1 | 1 | 0 | 0 | 1 | -1.0 | 1.0 | 0 | 1 | OK |
| 0 | 0 | 1 | 1 | 0 | 1.0 | -1.0 | 1 | 0 | OK |
| 1 | 0 | 1 | 0 | 1 | -1.0 | 1.0 | 0 | 1 | OK |
| 0 | 1 | 1 | 0 | 1 | -1.0 | 1.0 | 0 | 1 | OK |
| 1 | 1 | 1 | 1 | 1 | 1.0 | 1.0 | 1 | 1 | OK |

## 3. Physical Substrate Metrics & Stability

| Input A | Input B | Input Cin | Mass Reg A | Mass Reg B | Mass Reg C | Mass Reg D |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 0 | 0 | 0 | 4.5 | 4.4 | 4.4 | 4.4 |
| 1 | 0 | 0 | 227.5 | 11.6 | 461.1 | 8.6 |
| 0 | 1 | 0 | 260.4 | 225.2 | 460.1 | 9.0 |
| 1 | 1 | 0 | 232.2 | 436.1 | 13.6 | 424.7 |
| 0 | 0 | 1 | 5.8 | 198.6 | 283.3 | 5.7 |
| 1 | 0 | 1 | 242.7 | 221.7 | 447.6 | 242.9 |
| 0 | 1 | 1 | 270.1 | 188.3 | 434.1 | 238.0 |
| 1 | 1 | 1 | 232.1 | 181.9 | 294.0 | 402.0 |

## 4. Architectural Summary
- **Register-Reuse Scheduling**: Successfully executed a 17-instruction program on only 4 physical registers by loading Cin into B after A AND B (intermediate Carry 1) was stored in D, and saving SUM to memory early to free up C for CARRY 2 computation.
- **Semantic Insulation**: All input basins (`Basin_A`, `Basin_B`, and `Basin_Cin`) successfully maintained their initial states without leakage or feedback drag.
- **Mass Preservation**: All active registers successfully preserved their mass reservoirs above the critical limit of `14.0` units, preventing voltage/charge collapse.
