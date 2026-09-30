# SOL Hybrid ALU Expanded Truth Tables Report

This report verifies the full 7-gate universal logic suite on the stateful hybrid register ALU.

## 1. Experimental Verdict

**Overall Suite Status**: **PASSED**

## 2. Truth Tables & Measurements

### Gate: OR

| Input A | Input B | Expected Out | Got C (Comp) | Got C (Stored) | Status |
| :---: | :---: | :---: | :---: | :---: | :---: |
| 0 | 0 | 0 | -1.0 | 0 | OK |
| 1 | 0 | 1 | 1.0 | 1 | OK |
| 0 | 1 | 1 | 1.0 | 1 | OK |
| 1 | 1 | 1 | 1.0 | 1 | OK |

### Gate: AND

| Input A | Input B | Expected Out | Got C (Comp) | Got C (Stored) | Status |
| :---: | :---: | :---: | :---: | :---: | :---: |
| 0 | 0 | 0 | -1.0 | 0 | OK |
| 1 | 0 | 0 | -1.0 | 0 | OK |
| 0 | 1 | 0 | -1.0 | 0 | OK |
| 1 | 1 | 1 | 1.0 | 1 | OK |

### Gate: OR_MS

| Input A | Input B | Expected Out | Got C (Comp) | Got C (Stored) | Status |
| :---: | :---: | :---: | :---: | :---: | :---: |
| 0 | 0 | 0 | -1.0 | 0 | OK |
| 1 | 0 | 1 | 1.0 | 1 | OK |
| 0 | 1 | 1 | 1.0 | 1 | OK |
| 1 | 1 | 1 | 1.0 | 1 | OK |

### Gate: AND_MS

| Input A | Input B | Expected Out | Got C (Comp) | Got C (Stored) | Status |
| :---: | :---: | :---: | :---: | :---: | :---: |
| 0 | 0 | 0 | -1.0 | 0 | OK |
| 1 | 0 | 0 | -1.0 | 0 | OK |
| 0 | 1 | 0 | -1.0 | 0 | OK |
| 1 | 1 | 1 | 1.0 | 1 | OK |

### Gate: NOT

| Input A | Input B | Expected Out | Got C (Comp) | Got C (Stored) | Status |
| :---: | :---: | :---: | :---: | :---: | :---: |
| 0 | 0 | 1 | 1.0 | 1 | OK |
| 1 | 0 | 0 | -1.0 | 0 | OK |

### Gate: NAND

| Input A | Input B | Expected Out | Got C (Comp) | Got C (Stored) | Status |
| :---: | :---: | :---: | :---: | :---: | :---: |
| 0 | 0 | 1 | 1.0 | 1 | OK |
| 1 | 0 | 1 | 1.0 | 1 | OK |
| 0 | 1 | 1 | 1.0 | 1 | OK |
| 1 | 1 | 0 | -1.0 | 0 | OK |

### Gate: NOR

| Input A | Input B | Expected Out | Got C (Comp) | Got C (Stored) | Status |
| :---: | :---: | :---: | :---: | :---: | :---: |
| 0 | 0 | 1 | 1.0 | 1 | OK |
| 1 | 0 | 0 | -1.0 | 0 | OK |
| 0 | 1 | 0 | -1.0 | 0 | OK |
| 1 | 1 | 0 | -1.0 | 0 | OK |

### Gate: XOR

| Input A | Input B | Expected Out | Got C (Comp) | Got C (Stored) | Status |
| :---: | :---: | :---: | :---: | :---: | :---: |
| 0 | 0 | 0 | -1.0 | 0 | OK |
| 1 | 0 | 1 | 1.0 | 1 | OK |
| 0 | 1 | 1 | 1.0 | 1 | OK |
| 1 | 1 | 0 | -1.0 | 0 | OK |

### Gate: XNOR

| Input A | Input B | Expected Out | Got C (Comp) | Got C (Stored) | Status |
| :---: | :---: | :---: | :---: | :---: | :---: |
| 0 | 0 | 1 | 1.0 | 1 | OK |
| 1 | 0 | 0 | -1.0 | 0 | OK |
| 0 | 1 | 0 | -1.0 | 0 | OK |
| 1 | 1 | 1 | 1.0 | 1 | OK |

## 3. Key Physical Observations
- **Mixed-Signal Mode**: Enabling the sequencer to read register battery states and drive target nodes allows execution of non-threshold logic (e.g. inversion gates like NOT, NAND, NOR, XOR, XNOR) with 100% precision.
- **Mass Preservation**: Throughout all compute, copy, and store sequences, active registers successfully preserved their mass reservoirs above the critical limit of `14.0` units, preventing voltage/charge collapse.
- **Backward Compatibility**: The physical threshold configurations for `OR` and `AND` remain fully verified and backward-compatible.
