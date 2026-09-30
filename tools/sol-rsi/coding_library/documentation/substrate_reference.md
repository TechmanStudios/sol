# SOL Physical Substrate & Register Reference

The SOL engine executes coupled analog/dynamical simulations over a semantic attractor manifold. Lumina code compiles down to register-allocated micro-instructions executed by the `MicroInstructionSequencer` on this physical substrate.

## 1. Register Architecture

The VM maintains four registers representing localized field coordinates:
* **Register A (`reg_a_state`)**: Standard accumulator register 1.
* **Register B (`reg_b_state`)**: Standard accumulator register 2.
* **Register C (`reg_c_state`)**: ALU destination register.
* **Register D (`reg_d_state`)**: ALU destination register (specifically prioritized for `AND`/`AND_MS` gates and `COND_ASSIGN` operations).

### Mass Preservation Requirement
Active registers must retain a strict mass constraint ($\rho \ge 14.0$). If an active register's density falls below this threshold due to improper ALU operation, a **Mass Preservation Failure** assertion is raised, immediately terminating VM execution.

---

## 2. Attractor Memory Basins

Variables are bound to localized physical basins on the semantic manifold:
* **Basin_A**: Primed as Input Channel 1.
* **Basin_B**: Primed as Input Channel 2.
* **Basin_Cin**: Primed as Input Channel 3 (Carry-in / Auxiliary).
* **Basin_SUM**: Primed as Output Channel 1 (Result Accumulator).
* **Basin_Cout**: Primed as Output Channel 2 (Carry-out / Auxiliary).
* **Basin_Sel**: Primed as Selection Selector.
* **Basin_Out**: Primed as Multiplexer Output.
* **Basin_S** / **Basin_R**: Primed as Set/Reset inputs for latches.
* **Basin_Q** / **Basin_Qbar**: Primed as latch outputs.

---

## 3. Dynamical Equations

Basin density changes dynamically based on incoming semantic flux:
$$\frac{\partial \rho_i}{\partial t} = \Phi_{in} - \Phi_{out} - \gamma \rho_i$$
Where:
* $\rho_i$ is the density/mass of the attractor basin.
* $\Phi$ is the boundary edge semantic flux.
* $\gamma$ is the damping coefficient (default: `0.01`).
