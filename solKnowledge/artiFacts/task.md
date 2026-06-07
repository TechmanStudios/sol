# Task List

- [ ] Refactor and Stabilize Level 11 PDM (`test_logos_vm_level11_pdm_final.py`)
    - [ ] Add `Basin_Page` and define Page 0 and Page 1 register nodes (X0_P0, X0_P1, etc.)
    - [ ] Reduce frequencies to 2 channels (periods 10.0, 14.0) with Sine/Cosine
    - [ ] Update sequencer instructions (`LOAD_16`, `QUERY_16`) to use paged mapping
    - [ ] Calibrate and run verification suite (4 trials)
- [ ] Refactor Level 7 Carry-Select Multiplexing (`test_logos_vm_level7_multiplexed.py`)
    - [ ] Modify `CSELECT_PHYSICAL` to route all bits in a single 35-step settle phase
    - [ ] Dynamic bias of routing gates using `Basin_Carry0`'s actual `psi` value
    - [ ] Run and verify 128 multi-core arithmetic cases
- [ ] Synchronize and mirror all artifacts to `solKnowledge/artiFacts/`
