# SOL Purely Physical Psi-Transistor Gated ALU Report (Conjecture 9)

This report evaluates the **Purely Physical Psi-Transistor Gated ALU (PTG-ALU)** (Conjecture 9).
We verify that a shared central BUS with Psi-Transistor gates can perform purely physical logical OR and AND computations between registers A and B, storing and recalling the result at Register C.

## 1. Experimental Setup

- **Topology Layout**: Three registers connected via transistor-like gates to a central routing `BUS` node.
- **Transistor Gate Channels**: $w_0 = 5.0$ (high-conductance ON coupling), $\gamma = 8.0$, conductance bounds $[10^{-7}, 200.0]$.
- **Physical Summation logic**: Gating is driven entirely physically. Logic gates are selected purely by adjusting a single physical parameter: the default belief bias ($\psi_{bias}$) of the Accumulator gate (`HOST_C`):
  - **OR Configuration**: $\psi_{bias\_HOST\_C} = 0.35$ (low threshold).
  - **AND Configuration**: $\psi_{bias\_HOST\_C} = 0.32$ (high threshold).

## 2. OR Gate Truth Table Verification

| Input A | Input B | Accumulator C Latched? | Recalled Mass C | Status |
|---|---|---|---|---|
| 0 | 0 | `False` | `0.0000` | OK |
| 1 | 0 | `True` | `5.7947` | OK |
| 0 | 1 | `True` | `5.7947` | OK |
| 1 | 1 | `True` | `7.9311` | OK |

## 3. AND Gate Truth Table Verification

| Input A | Input B | Accumulator C Latched? | Recalled Mass C | Status |
|---|---|---|---|---|
| 0 | 0 | `False` | `0.0000` | OK |
| 1 | 0 | `False` | `4.6700` | OK |
| 0 | 1 | `False` | `4.6700` | OK |
| 1 | 1 | `True` | `7.6411` | OK |

## 4. Key Findings

### A. Purely Physical Logic Summation
- The central `BUS` node behaves as an analog summing junction. When `GATE_A` and `GATE_B` are opened, they discharge their mass and positive/negative belief into `BUS`.
- By adjusting the default bias ($\psi_{bias}$) of `HOST_C` to $0.35$ (OR), a single active register discharges enough mass/belief to pull `HOST_C`'s belief above $0.0$, successfully trigger-latching the accumulator.
- By adjusting the bias to $0.32$ (AND), the combined discharge of *both* registers is required to pull `HOST_C`'s belief above $0.0$ and trigger the latch.

### B. Zero-Leak State Isolation
- During Hold phases, setting all gates to OFF ($\psi = -1.0$) isolates each register pocket with conductance $\approx 10^{-7}$.
- Flux resets successfully eliminate the Write-phase and Compute-phase advection momentum, preventing false-latching and ensuring clean, uncorrupted readouts.

## 5. Conclusion

Conjecture 9 is **fully verified**. A shared routing bus utilizing Psi-Transistor gates can perform purely physical logic operations (OR and AND) without any software-driven connection weight overrides. This establishes the viability of a purely physical analog microprocessor architecture built on self-organizing graph fluids.
