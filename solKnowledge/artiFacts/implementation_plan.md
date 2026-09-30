# Stabilize Level 11 PDM & Refactor Level 7 Speculative Routing

This implementation plan focuses on resolving the parameter stability issues in **Level 11: Phase-Division Multiplexing (PDM) & Dual-Bus Crossbar (16-Bit Processing)**, integrating the **Basin_Page bank-switching scalability** pattern to handle larger register scales without physical bus widening, and refactoring **Level 7's carry-select multiplexing** from a sequential software instruction sequence into a physical phased/holographic routing process.

## User Review Required

> [!IMPORTANT]
> **Level 11 Basin_Page Bank Switching**: To solve the frequency crowding and register resonance mismatch in the 16-bit word recall, we are adopting the `Basin_Page` bank-switching pattern. Instead of multiplexing 8 bits (4 frequencies) per lane simultaneously, we page-switch the register word into two 8-bit blocks (Page 0 and Page 1), where each lane only multiplexes 4 bits (2 frequencies: periods 10 and 14). This reduces the frequency count per lane to 2, ensuring stable and robust calibration deltas.
>
> **Level 7 Refactoring**: Replacing the sequential carry-select routing loop in `CSELECT_PHYSICAL` with a unified physical wave-gated routing process. Both sum candidate paths will be connected, but their gate conductances will be physically biased by the carry basin `Basin_Carry0`'s `psi` value. This runs in a single settle phase for all bits concurrently, saving VM cycles and running faster.

## Open Questions

> [!NOTE]
> None. The paged register mapping pattern and physical carry-select bias controller resolve the stability and performance bottlenecks cleanly.

## Proposed Changes

---

### Component: Level 11 Parameter Tuning & Bank Switching

#### [MODIFY] [test_logos_vm_level11_pdm_final.py](file:///g:/docs/TechmanStudios/sol/scratch/test_logos_vm_level11_pdm_final.py)
- Refactor the processing manifold to define paged register nodes: `S_RX0_P0`, `S_RX0_P1`, `S_RX1_P0`, `S_RX1_P1`, and similarly for `Y`.
- Add a physical `Basin_Page` control basin in the semantic manifold to route to Page 0 when inactive and Page 1 when active.
- Reduce frequency channels per lane to 2 (periods 10 and 14) using Sine/Cosine orthogonal channels.
- Update `LOAD_16` and `QUERY_16` instructions in the sequencer to execute page-by-page based on the `Basin_Page` state.
- Ensure active register mass remains safe ($\ge 14.0$) and collapses cleanly at termination.

---

### Component: Level 7 Speculative Carry-Select Refactoring

#### [MODIFY] [test_logos_vm_level7_multiplexed.py](file:///g:/docs/TechmanStudios/sol/scratch/test_logos_vm_level7_multiplexed.py)
- Refactor `CSELECT_PHYSICAL` to perform physical wave-gated routing in parallel for all bits.
- Drive the gate nodes `Gate_Match_prime{i}` and `Gate_Match_double_prime{i}` using `Basin_Carry0`'s `psi` value as a physical bias controller during a single 35-step settle phase.
- Reduce the execution time and steps needed for verification.

---

### Component: Artifact Preservation

#### [NEW] [implementation_plan.md](file:///g:/docs/TechmanStudios/sol/solKnowledge/artiFacts/implementation_plan.md)
- Mirror copy of this implementation plan to ensure future agents can recover the context and design decisions.

## Verification Plan

### Automated Tests
- Run the Python verification scripts directly to verify correctness of Level 7 and Level 11.
  ```powershell
  .venv\Scripts\python.exe scratch\test_logos_vm_level7_multiplexed.py
  .venv\Scripts\python.exe scratch\test_logos_vm_level11_pdm_final.py
  ```

### Manual Verification
- Check output JSON reports in `solResearch/nextBestTest/` to verify deltas and active masses.
