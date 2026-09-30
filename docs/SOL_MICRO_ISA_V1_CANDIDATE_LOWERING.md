# SOL Micro-ISA v1 Candidate Opcode & v0 Lowering Bridge

This document details the engineering specification, safety boundaries, and compliance framework for the SOL Micro-ISA v1 Candidate Opcode and v0 Lowering Bridge.

## Release Candidate Checkpoint (RC1)
For the comprehensive release candidate specifications, mappings, and proof ledger, see:
- [SOL Waveguide Optimization Research Dossier (RC1)](file:///G:/docs/TechmanStudios/sol/docs/SOL_WAVEGUIDE_OPTIMIZATION_RESEARCH_DOSSIER_RC1.md)
- [SOL Waveguide Architecture Map (RC1)](file:///G:/docs/TechmanStudios/sol/docs/SOL_WAVEGUIDE_ARCHITECTURE_MAP_RC1.md)
- [SOL Waveguide Proof Ledger (RC1)](file:///G:/docs/TechmanStudios/sol/docs/SOL_WAVEGUIDE_PROOF_LEDGER_RC1.md)
- [SOL Waveguide Release Candidate Manifest JSON](file:///G:/docs/TechmanStudios/sol/docs/SOL_WAVEGUIDE_RC1_MANIFEST.json)

---


## 1. Overview & Purpose

The Micro-ISA v1 Candidate Layer acts as an evolutionary design harness for proposed high-level native opcodes. It allows the definition of experimental candidate opcodes and emulation of their execution by lowering them early into verified Micro-ISA v0 instructions.

### Core Principle
- **Default Compliance**: Micro-ISA v0 remains the default compliance target.
- **Optional Extensions**: v1 candidates are optional, experimental, and disabled by default.
- **Lowering Emulation**: Every candidate opcode is translated to v0 instructions before strict waveguide execution, allowing subsequent passes (compaction, scheduling, predication) to optimize them as standard v0 code.

```text
v1 candidate opcode
→ v0 lowering plan
→ strict waveguide execution
→ optimization profile / pass manager
→ trace replay audit
→ equivalence proof
```

---

## 2. Candidate Opcode Specification

### Conditional Select Family

#### 1. `SELECT dst, cond, src_true, src_false`
- **Semantics**: If `cond` evaluates truthy, commit `src_true` to `dst`. Otherwise, commit `src_false` to `dst`.
- **Lowering Strategy**: Translates to a branch diamond. If `cond` is a register, performs `CMP cond, 0` and conditional skip. If `cond` is a CPU flag name (`Z`, `NZ`, `C`, `NC`, `B`, `NB`), uses the corresponding conditional jump directly.

#### 2. CMOV Family (`CMOVZ`, `CMOVNZ`, `CMOVC`, `CMOVNC`, `CMOVB`, `CMOVNB`)
- **Semantics**: `CMOV<flag> dst, src`. If the corresponding CPU flag is set (e.g. `Z` flag for `CMOVZ`), copy `src` into `dst`. Otherwise, preserve `dst`.
- **Lowering Strategy**: Translates to a single conditional skip branch diamond (e.g., `CMOVZ` jumps over the `MOV` if `NZ`).

### Read-Only Predicated Load Candidate

#### 3. `PLOAD_RO dst, predicate, addr_true, addr_false`
- **Semantics**: Read-only conditional load. Loads value from memory address `addr_true` if `predicate` evaluates true; otherwise from `addr_false`.
- **Safety Boundary**: Must remain read-only. Unsafe dynamic addresses (registers) are rejected at compile-time during lowering. Only static addresses (immediates) are allowed.

### Lane & Prefix Arithmetic Candidates

#### 4. Lane Arithmetic (`LANE_ADD`, `LANE_SUB`)
- **Semantics**: Per-lane arithmetic operation. Lowers directly to standard v0 wide-word `ADD`/`SUB` operations.

#### 5. Prefix Arithmetic (`PREFIX_ADD`, `PREFIX_SUB`)
- **Semantics**: Prefix carry/borrow-aware wide-word arithmetic. Lowers to v0 `ADD`/`SUB` instructions to leverage the validated prefix carry/borrow routing path.

### Lane/Vector Candidates (`VEC_PACK`, `VEC_UNPACK`, `VEC_BROADCAST`, `VEC_EXTRACT`, `VEC_INSERT`, `VEC_LANE_ADD`, `VEC_LANE_SUB`, `VEC_LANE_AND`, `VEC_LANE_OR`, `VEC_LANE_XOR`, `VEC_MASK_SELECT`)
- **Semantics**: Byte-lane, mask-lane, and lane-conditional selection on 4-lane registers (8 bits per lane for 32-bit registers, 16 bits per lane for 64-bit).
- **Lowering Strategy**: Lowered safely to shifts, bitwise masks, and OR sequences. Arithmetic operations (`VEC_LANE_ADD`/`SUB`) execute lane-by-lane to guarantee strict carry/borrow isolation. `VEC_MASK_SELECT` lowers to branch diamonds using mask-bit check.

### Waveguide-Channel Candidates (`WG_CHAN_FENCE`, `WG_CHAN_SEND`, `WG_CHAN_RECV`, `WG_CHAN_ROUTE`)
- **Semantics**: Message-passing and routing ordering grammar.
- **Lowering Strategy**: `WG_CHAN_FENCE` lowers to no-op trace marker (`MOV R0, R0`) and acts as a superblock scheduling barrier. All other channel candidates (`WG_CHAN_SEND`, `RECV`, `ROUTE`) are unsupported and rejected at lowering time.

---

## 3. Configuration & Optimization Profiles

To enable v1 candidate support:
- Set `enable_micro_isa_v1_candidates=True` or use `micro_isa_version="v1"` in `WaveguideControlMemoryBridgeConfig`.
- Or select the **`V1_CANDIDATE_EXPERIMENTAL`** optimization profile.

*Note: If v1 mode is disabled, encountering any v1 candidate opcode in the instruction stream causes an immediate execution mismatch/unsupported instruction error.*

---

## 4. Safety Barriers & Rejections

If a candidate opcode cannot be lowered safely or violates schemas, it is **rejected** during the lowering pass:
- **PLOAD_RO Address Safety**: If `addr_true` or `addr_false` is a register (dynamic address), it is rejected with reason `dynamic_address_unknown_alias` and remains unlowered, failing during strict execution.
- **Predicated Stores**: Any store-like predicated candidates are strictly rejected to prevent illegal memory mutation.

---

## 5. Trace Metadata & Auditor Integration

Lowered candidates generate pass manager metadata stored in the unified optimization report:
```json
{
    "micro_isa_v1_candidate": true,
    "candidate_opcode": "SELECT",
    "candidate_pc": 3,
    "lowered_to_v0": true,
    "v0_pc_range": [10, 11, 12],
    "lowering_strategy": "branchless_select_via_predication",
    "semantic_equivalence_required": true,
    "lowering_safe": true,
    "skip_reason": null
}
```

The Trace Replay Auditor verifies:
1. Candidate metadata matches the configuration.
2. Lowered candidates map to valid v0 PC ranges.
3. Rejected candidates do not execute successfully.
4. Final execution state matches the reference v0 equivalent execution plan.

---

## 6. Strict Capability Proof & Compliance

v1 candidate capability flags are registered separately as experimental extensions in `StrictBackendSupportMatrix` to preserve clean separation from v0 core compliance:
- `supports_micro_isa_v1_candidate_lowering`
- `supports_v1_select_candidate`
- `supports_v1_cmov_candidate`
- `supports_v1_prefix_arithmetic_candidate`
- `supports_v1_candidate_trace_mapping`
- `supports_v1_vector_lane_candidate_lowering`
- `supports_v1_vec_pack_candidate`
- `supports_v1_vec_unpack_candidate`
- `supports_v1_vec_mask_select_candidate`
- `supports_v1_waveguide_channel_candidate_schema`
- `supports_v1_waveguide_channel_fence_candidate`

For the complete candidate maturity table, opcode specifications, and extension capability matrix, see [SOL_MICRO_ISA_V1_FORMAL_SPEC.md](file:///g:/docs/TechmanStudios/sol/docs/SOL_MICRO_ISA_V1_FORMAL_SPEC.md).

---

## 7. Sandbox Caveat

All v1 candidate opcodes and lowering strategies are software-simulated sandboxes and do not interact with active/production system registers or hardware memory mutations.
