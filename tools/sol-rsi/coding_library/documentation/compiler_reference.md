# Lumina Language & Compiler Reference

Lumina compiles a subset of Python AST directly into register-allocated Logos instructions for the SOL VM substrate.

## 1. Syntax & Core Operators

Lumina supports standard boolean logical operations over variables bound to semantic basins:
* **XOR (`^`)**: Translates to the `XOR` instruction.
* **AND (`&`)**: Translates to the `AND_MS` (mixed-signal AND) instruction.
* **OR (`|`)**: Translates to the `OR_MS` (mixed-signal OR) instruction.
* **NOT (`~` / `not`)**: Translates to the `NOT` instruction.

### Ternary Expressions
Conditionals are supported via Python ternary syntax:
`self.out = self.b if self.sel else self.a`
Translates to `COPY` and conditional move (`CMOVE`) instructions.

---

## 2. Analog Helper Functions

To directly modulate or verify the substrate, the following helper methods are available:
* **`self.nudge(basin_name, amount)`**: Adds `amount` density directly to `basin_name`.
  * *Example*: `self.nudge("Basin_SUM", 5.0)`
* **`self.settle(steps)`**: Steps the physical simulator forward by `steps` steps without any register ALU updates, letting semantic waves stabilize.
  * *Example*: `self.settle(10)`
* **`self.assert_mass(register_name, min_mass)`**: Asserts that the register's current mass is $\ge$ `min_mass`.
  * *Example*: `self.assert_mass("C", 14.0)`

---

## 3. Stateful Feedback Loops

Sequential logic (like latches and flip-flops) requires referencing an output basin's previous state in the logical equation:
`self.q = self.s | (self.q & ~self.r)`
The compiler automatically translates read accesses of the destination variable (`self.q`) into a `LOAD` instruction from that output's attractor basin prior to the logical operation.
