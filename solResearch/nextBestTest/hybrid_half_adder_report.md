# SOL Hybrid Sub-system Half-Adder Verification Report

This report verifies the Register-Based Half-Adder composite circuit on the Level 5 Manifold-Systems substrate.

## 1. Experimental Verdict

**Overall Suite Status**: **PASSED**

## 2. Half-Adder Truth Table & Measurements

| Input A | Input B | Exp Sum | Exp Carry | Got Reg C (XOR) | Got Reg D (AND) | Got Basin SUM | Got Basin CARRY | Status |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 0 | 0 | 0 | 0 | -1.0 | -1.0 | 0 | 0 | OK |
| 1 | 0 | 1 | 0 | 1.0 | -1.0 | 1 | 0 | OK |
| 0 | 1 | 1 | 0 | 1.0 | -1.0 | 1 | 0 | OK |
| 1 | 1 | 0 | 1 | -1.0 | 1.0 | 0 | 1 | OK |

## 3. Physical Substrate Metrics & Stability

| Input A | Input B | Mass Reg A | Mass Reg B | Mass Reg C | Mass Reg D |
| :---: | :---: | :---: | :---: | :---: | :---: |
| 0 | 0 | 4.9 | 4.8 | 4.8 | 4.8 |
| 1 | 0 | 230.6 | 6.4 | 208.2 | 6.6 |
| 0 | 1 | 4.9 | 226.0 | 235.8 | 6.4 |
| 1 | 1 | 231.2 | 230.0 | 8.0 | 206.1 |

## 4. Architectural Summary
- **Sequential Mixed-Signal Program**: XOR C computes the sum bit into Register C, and AND_MS D computes the carry bit into Register D. The system demonstrates absolute stability across all trials.
- **Semantic Insulation**: Source attractor basins `Basin_A` and `Basin_B` states are strictly insulated and unaltered by loading/execution cycles.
- **Mass Preservation**: Throughout the instruction flow, active registers maintained mass reservoirs $\ge 14.0$ units, preventing voltage/charge collapse.
