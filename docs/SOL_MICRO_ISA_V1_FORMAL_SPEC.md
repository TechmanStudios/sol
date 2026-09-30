# SOL Micro-ISA v1 Formal Specification & Extension Compliance Matrix

This document provides the formal architecture specification, maturity framework, and extension compliance matrix for SOL Micro-ISA v1 candidates on the strict PDM/waveguide backend.

## Release Candidate Checkpoint (RC1)
For the comprehensive release candidate specifications, mappings, and proof ledger, see:
- [SOL Waveguide Optimization Research Dossier (RC1)](file:///G:/docs/TechmanStudios/sol/docs/SOL_WAVEGUIDE_OPTIMIZATION_RESEARCH_DOSSIER_RC1.md)
- [SOL Waveguide Architecture Map (RC1)](file:///G:/docs/TechmanStudios/sol/docs/SOL_WAVEGUIDE_ARCHITECTURE_MAP_RC1.md)
- [SOL Waveguide Proof Ledger (RC1)](file:///G:/docs/TechmanStudios/sol/docs/SOL_WAVEGUIDE_PROOF_LEDGER_RC1.md)
- [SOL Waveguide Release Candidate Manifest JSON](file:///G:/docs/TechmanStudios/sol/docs/SOL_WAVEGUIDE_RC1_MANIFEST.json)

---


## 1. Purpose & Separation from Micro-ISA v0

The Micro-ISA v1 candidate layer serves as an evolutionary design harness for proposed high-level native instructions. To maintain architectural stability:
- **Micro-ISA v0 Is the Default Compliance Target**: All compliance verifications and core capability claims target v0.
- **Strict Separation**: v1 candidates are optional, disabled by default, and evaluated in a separate **Extension Compliance Matrix**.
- **No v0 Downgrade**: Partially supported, proposed, or unsupported v1 candidates will never affect or downgrade the v0 `full_compliance` verification status.

---

## 2. Candidate Maturity Levels

The maturity of each candidate opcode in the spec is tracked using the following levels:
1. **`PROPOSED`**: Opcode defined in operand schema only; no implementation exists.
2. **`SCHEMA_VALIDATED`**: Structural operand types and schema constraints validated.
3. **`LOWERING_VALIDATED`**: Lowering compiler translations to v0 instructions validated.
4. **`TRACE_VALIDATED`**: Trace PC ranges and state transitions validated.
5. **`BENCHMARK_VALIDATED`**: Representative benchmark coverage and cycle savings measured.
6. **`EXTENSION_COMPLIANT`**: Fully integrated and validated across all pipeline passes, trace replay, and strict proof matrix.
7. **`UNSUPPORTED`**: Opcode explicitly marked as out-of-scope or rejected by design.
8. **`REJECTED`**: Opcode identified as violating safety policies (e.g. predicated store mutations).

---

## 3. Opcode Specification Table

| Opcode | Category | Status | Operand Schema | Semantics | Lowering Strategy |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`SELECT`** | `conditional_select` | `EXTENSION_COMPLIANT` | `dst, cond, src_true, src_false` | If `cond` is truthy, commit `src_true` to `dst`, else `src_false`. | `branchless_select_via_predication` |
| **`CMOVZ`** | `conditional_select` | `EXTENSION_COMPLIANT` | `dst, src` | Move `src` to `dst` if Zero flag is set, else preserve `dst`. | `conditional_select_via_skip_branch` |
| **`CMOVNZ`** | `conditional_select` | `EXTENSION_COMPLIANT` | `dst, src` | Move `src` to `dst` if Zero flag is clear, else preserve `dst`. | `conditional_select_via_skip_branch` |
| **`CMOVC`** | `conditional_select` | `EXTENSION_COMPLIANT` | `dst, src` | Move `src` to `dst` if Carry flag is set, else preserve `dst`. | `conditional_select_via_skip_branch` |
| **`CMOVNC`** | `conditional_select` | `EXTENSION_COMPLIANT` | `dst, src` | Move `src` to `dst` if Carry flag is clear, else preserve `dst`. | `conditional_select_via_skip_branch` |
| **`CMOVB`** | `conditional_select` | `EXTENSION_COMPLIANT` | `dst, src` | Move `src` to `dst` if Borrow flag is set, else preserve `dst`. | `conditional_select_via_skip_branch` |
| **`CMOVNB`** | `conditional_select` | `EXTENSION_COMPLIANT` | `dst, src` | Move `src` to `dst` if Borrow flag is clear, else preserve `dst`. | `conditional_select_via_skip_branch` |
| **`PLOAD_RO`** | `memory` | `EXTENSION_COMPLIANT` | `dst, predicate, addr_true, addr_false` | Read-only predicated load from static address `addr_true` or `addr_false`. | `conditional_load_via_predication` |
| **`LANE_ADD`** | `alu` | `EXTENSION_COMPLIANT` | `dst, src1, src2` | Per-lane wide-word register addition. | `direct_v0_alu_mapping` |
| **`LANE_SUB`** | `alu` | `EXTENSION_COMPLIANT` | `dst, src1, src2` | Per-lane wide-word register subtraction. | `direct_v0_alu_mapping` |
| **`PREFIX_ADD`** | `alu` | `EXTENSION_COMPLIANT` | `dst, src1, src2` | Prefix carry-routing aware wide-word addition. | `direct_v0_alu_mapping` |
| **`PREFIX_SUB`** | `alu` | `EXTENSION_COMPLIANT` | `dst, src1, src2` | Prefix borrow-routing aware wide-word subtraction. | `direct_v0_alu_mapping` |
| **`VEC_PACK`** | `vector_lane` | `EXTENSION_COMPLIANT` | `dst, lane0, lane1, lane2, lane3` | Pack scalar lane values into wide-word. | `vec_pack_via_shifts_and_ors` |
| **`VEC_UNPACK`** | `vector_lane` | `EXTENSION_COMPLIANT` | `src, dst0, dst1, dst2, dst3` | Unpack lanes into scalar registers. | `vec_unpack_via_shifts_and_masks` |
| **`VEC_BROADCAST`** | `vector_lane` | `EXTENSION_COMPLIANT` | `dst, src` | Broadcast scalar src into all lanes of dst. | `vec_broadcast_via_duplication_shifts` |
| **`VEC_EXTRACT`** | `vector_lane` | `EXTENSION_COMPLIANT` | `dst, src, lane_index` | Extract lane_index from src into dst. | `vec_extract_via_shift_and_mask` |
| **`VEC_INSERT`** | `vector_lane` | `EXTENSION_COMPLIANT` | `dst, src_vec, lane_idx, src_scalar` | Replace target lane with src_scalar. | `vec_insert_via_clear_mask_and_or` |
| **`VEC_LANE_ADD`** | `vector_lane` | `EXTENSION_COMPLIANT` | `dst, src_a, src_b, mask` | Carry-isolated per-lane addition. | `lane_add_via_lane_extraction` |
| **`VEC_LANE_SUB`** | `vector_lane` | `EXTENSION_COMPLIANT` | `dst, src_a, src_b, mask` | Borrow-isolated per-lane subtraction. | `lane_sub_via_lane_extraction` |
| **`VEC_MASK_SELECT`** | `vector_lane` | `EXTENSION_COMPLIANT` | `dst, mask, src_true, src_false` | Per-lane conditional select. | `vec_mask_select_via_lane_selection` |
| **`WG_CHAN_FENCE`** | `ordering_barrier` | `EXTENSION_COMPLIANT` | None | Candidate ordering barrier for channels. | `waveguide_channel_fence_barrier` |
| **`WG_CHAN_SEND`** | `waveguide_channel` | `TRACE_VALIDATED` (Conditional) | `channel, src` | Candidate channel send operation (sandbox-local). | `waveguide_channel_send_barrier` |
| **`WG_CHAN_RECV`** | `waveguide_channel` | `TRACE_VALIDATED` (Conditional) | `dst, channel` | Candidate channel receive operation (sandbox-local). | `waveguide_channel_recv_barrier` |
| **`WG_CHAN_ROUTE`** | `waveguide_channel` | `TRACE_VALIDATED` (Conditional) | `dst_ch, src_ch, route_mask` | Candidate channel routing operation (sandbox-local). | `waveguide_channel_route_barrier` |
| **`PSTORE_WO`** | `memory` | `UNSUPPORTED` | `predicate, addr, src` | Predicated store (write-only). | None (strictly rejected) |
| **`DUMMY_V1_OP`**| `control` | `PROPOSED` | `dst` | Specification validation placeholder. | None |

---

## 4. Operational Contracts & Safety Barriers

### Flags & Memory Behavior
- **Flag Updates**: `LANE_*` and `PREFIX_*` arithmetic operations update ALU status flags (Zero, Carry, Borrow, Sign, Overflow) identically to their v0 arithmetic counterparts. `SELECT` and `CMOV*` preserve status flags.
- **Predicated Stores**: Any store-like or memory-writing predicated instruction is strictly rejected (e.g. `PSTORE_WO`) to prevent illegal state mutations.
- **PLOAD_RO Address Safety**: Addresses must be static immediates. Dynamic memory addressing (via registers) causes compile-time lowering rejections with reason `dynamic_address_unknown_alias`.

### Trace Metadata Requirements
Every compliant candidate opcode must produce unified pass manager report entries containing:
- `micro_isa_v1_candidate`: boolean constant `True`.
- `candidate_opcode`: uppercase mnemonic string.
- `lowered_to_v0`: boolean lowering success indicator.
- `v0_pc_range`: list of resulting v0 instruction PCs.

---

## 5. v1 Capability & Extension Compliance Rules

### Extension Matrix Evaluation Tiers
Each candidate is evaluated across backends into standard capability tiers:
- **`emulated`**: Lowered successfully to v0 instruction sequences before execution.
- **`native`**: Executed directly by the backend without requiring translation layers.
- **`unsupported`**: Opcode not supported by the backend design, or marked unsupported/proposed.
- **`failed`**: Execution caused state mismatches or validation errors during strict proof.

### Verdict Resolution
- **`candidate_compliant`**: All candidate opcodes marked `EXTENSION_COMPLIANT` in the spec are evaluated as `emulated` or `native` on the target strict backend.
- **`partial`**: One or more compliant candidates report `unsupported` or `failed`.

---

## 6. How to Run v1 Extension Tests

Verify spec consistency, capability matrix builds, benchmark maps, and trace replay validations sequentially:
```bash
.venv/Scripts/pytest -v tests/test_micro_isa_v1_spec_matrix.py
```

---

## 7. Sandbox Caveat

All v1 candidate opcodes, lowering compilers, and compliance matrices are software-simulated sandboxes and do not interact with active/production system registers or hardware memory mutations.
