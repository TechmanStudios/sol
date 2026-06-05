# Task Checklist: CFG-Aware Compiler Expansion & Symbolic Loops

- [x] Implement CFG-Aware Liveness Analysis in `scratch/logos_compiler.py`
  - [x] Parse label indices and build instruction successors list
  - [x] Implement backward dataflow iterative solver for `live_in` and `live_out` sets
- [x] Implement Unified Register Allocator & Instruction Compiling
  - [x] Add `_allocate_to_register(var, target_reg)` helper
  - [x] Update `OP`, `COND_ASSIGN`, `LOAD_INDIRECT`, `STORE_INDIRECT` to use unified allocator
  - [x] Support lists of address registers (2-bit MSB/LSB indirect mapping)
  - [x] Implement statement handlers for `LABEL`, `JUMP`, `JUMP_IF_ACTIVE`, and `CLEAR_VAR`
- [x] Verify via Symbolic 4-Bit Serial Adder Loop
  - [x] Create `scratch/test_compiled_4bit_adder.py`
  - [x] Define high-level symbolic statements for 4-iteration serial addition
  - [x] Compile and verify results against 8 test configurations
  - [x] Confirm clean register collapse to -1
- [x] Regression Testing & Documentation
  - [x] Run all existing test files to ensure zero regressions
  - [x] Update chronicle and walkthrough records, commit, and push
