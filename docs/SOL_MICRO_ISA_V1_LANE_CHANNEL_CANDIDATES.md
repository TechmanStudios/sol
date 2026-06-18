# SOL Micro-ISA v1 Lane/Vector + Waveguide Channel Candidate Specification

This document specifies the experimental candidate operations for lane/vector processing and waveguide-channel routing under the **SOL Micro-ISA v1** framework.

## Release Candidate Checkpoint (RC1)
For the comprehensive release candidate specifications, mappings, and proof ledger, see:
- [SOL Waveguide Optimization Research Dossier (RC1)](file:///G:/docs/TechmanStudios/sol/docs/SOL_WAVEGUIDE_OPTIMIZATION_RESEARCH_DOSSIER_RC1.md)
- [SOL Waveguide Architecture Map (RC1)](file:///G:/docs/TechmanStudios/sol/docs/SOL_WAVEGUIDE_ARCHITECTURE_MAP_RC1.md)
- [SOL Waveguide Proof Ledger (RC1)](file:///G:/docs/TechmanStudios/sol/docs/SOL_WAVEGUIDE_PROOF_LEDGER_RC1.md)
- [SOL Waveguide Release Candidate Manifest JSON](file:///G:/docs/TechmanStudios/sol/docs/SOL_WAVEGUIDE_RC1_MANIFEST.json)

---


## 1. Core Principle & Safe Lowering

All v1 vector and channel candidate operations are macros. During program compilation:
1. **Schema Validation**: Verify instruction formats, types, and operands.
2. **Lowering Safety Analysis**: Ensure static addressing and reject dangerous/unsupported candidates.
3. **v0 Lowering Compilation**: Rewrite candidates into sequences of verified v0 operations.
4. **Carry/Borrow Isolation**: Ensure independent lanes do not bleed carry/borrow flags into each other.
5. **Trace Replay Audit**: Verify lowered PC ranges and check lane metadata boundaries at execution time.

---

## 2. Lane & Vector Candidates

Vector registers are treated as having **4 independent lanes**. The lane size depends on the register word width:
- **32-bit Width**: 8 bits per lane (byte lanes).
- **64-bit Width**: 16 bits per lane.

### Candidate Registry & Lowering Strategies

| Opcode | Category | Operands | Status | Lowering Strategy |
| :--- | :--- | :--- | :--- | :--- |
| `VEC_PACK` | `vector_lane` | `dst, lane0, lane1, lane2, lane3` | `EXTENSION_COMPLIANT` | Clear mask + shift + OR sequence |
| `VEC_UNPACK` | `vector_lane` | `src, dst0, dst1, dst2, dst3` | `EXTENSION_COMPLIANT` | Shift + mask extraction |
| `VEC_BROADCAST`| `vector_lane` | `dst, src` | `EXTENSION_COMPLIANT` | Duplication shifts + ORs |
| `VEC_EXTRACT` | `vector_lane` | `dst, src, lane_index` | `EXTENSION_COMPLIANT` | Shift + mask extraction |
| `VEC_INSERT` | `vector_lane` | `dst, src_vec, lane_idx, src_scalar` | `EXTENSION_COMPLIANT` | Clear lane mask + shift + OR |
| `VEC_LANE_ADD` | `vector_lane` | `dst, src_a, src_b, mask` | `EXTENSION_COMPLIANT` | Lane-by-lane extraction, add, mask, insert |
| `VEC_LANE_SUB` | `vector_lane` | `dst, src_a, src_b, mask` | `EXTENSION_COMPLIANT` | Lane-by-lane extraction, sub, mask, insert |
| `VEC_LANE_AND` | `vector_lane` | `dst, src_a, src_b, mask` | `EXTENSION_COMPLIANT` | Lane-by-lane extraction, AND, insert |
| `VEC_LANE_OR` | `vector_lane` | `dst, src_a, src_b, mask` | `EXTENSION_COMPLIANT` | Lane-by-lane extraction, OR, insert |
| `VEC_LANE_XOR` | `vector_lane` | `dst, src_a, src_b, mask` | `EXTENSION_COMPLIANT` | Lane-by-lane extraction, XOR, insert |
| `VEC_MASK_SELECT`| `vector_lane` | `dst, mask, src_true, src_false` | `EXTENSION_COMPLIANT` | Lane-by-lane select (via branch diamonds) |

### Carry/Borrow Isolation
Because native wide-word `ADD`/`SUB` operations do not prevent carry-over/borrow-under from bleeding between adjacent lanes, arithmetic lane operations (`VEC_LANE_ADD` and `VEC_LANE_SUB`) are compiled down into lane-by-lane extraction, scalar arithmetic, explicit lane-width masking, and insertion. This guarantees **zero carry/borrow bleed**.

---

## 3. Waveguide-Channel Candidates

Waveguide-channel operations represent proposed message-passing and channel-routing grammar.

| Opcode | Category | Operands | Status | Lowering Strategy / Behavior |
| :--- | :--- | :--- | :--- | :--- |
| `WG_CHAN_FENCE`| `ordering_barrier` | None | `EXTENSION_COMPLIANT` | Lowers to a no-op trace marker (`MOV R0, R0`) |
| `WG_CHAN_SEND` | `waveguide_channel`| `channel, src` | `TRACE_VALIDATED` (Conditional) | Lowers to `MOV R0, R0` (Enabled only under sandbox channel state config) |
| `WG_CHAN_RECV` | `waveguide_channel`| `dst, channel` | `TRACE_VALIDATED` (Conditional) | Lowers to `MOV dst, dst` (Enabled only under sandbox channel state config) |
| `WG_CHAN_ROUTE`| `waveguide_channel`| `dst_ch, src_ch, mask` | `TRACE_VALIDATED` (Conditional) | Lowers to `MOV R0, R0` (Enabled only under sandbox channel state config) |

### Scheduling & Independence Analysis
- `WG_CHAN_FENCE` acts as a hard global ordering barrier and superblock separator.
- When `enable_channel_independence_analysis` is active, the scheduler performs static hazard analysis. It batches independent waveguide channel operations (such as sends/receives on non-overlapping channels) into parallel wavefronts.
- Overlapping channel read/write sets or register output conflicts are classified as hazards and split into separate wavefronts.
- When `enable_channel_kernel_recognition` is active, the static pattern recognizer scans the instruction streams to group independent channel sequences into one of five canonical motifs (`channel_parallel_load`, `channel_fanout`, `channel_fence_order`, `channel_gather`, `channel_route_chain`), validating them against serial execution semantics. Refer to [SOL Waveguide Channelized Microprogram Kernels](file:///g:/docs/TechmanStudios/sol/docs/SOL_WAVEGUIDE_CHANNEL_KERNELS.md) for details.

---

## 4. Trace Replay Audit

Trace replay validates lane and channel metadata at audit time:
- **Lane Range**: Extract lane indices must be in `[0, 3]`.
- **Lane Masks**: Mask values must be valid 4-bit integers in `[0, 15]`.
- **Safety Rejection**: Attempting to execute trace steps corresponding to channel operations (`WG_CHAN_SEND`, `WG_CHAN_RECV`, `WG_CHAN_ROUTE`) triggers trace audit rejection when sandbox channel state is disabled.
- **Channel Bounds & Masking**: If enabled, audits verify channel IDs, correct value masking, empty receive policy compliance, and deterministic route propagation.
- **External I/O Check**: Verifies no channel operations claim external socket/network side effects.

---

## 5. How to Run Verification

To run all candidates and integration tests:
```bash
.venv/Scripts/pytest -v tests/test_micro_isa_v1_lane_channel_candidates.py
.venv/Scripts/pytest -v tests/test_micro_isa_v1_spec_matrix.py
.venv/Scripts/pytest -v tests/test_micro_isa_v1_candidate_lowering.py
.venv/Scripts/pytest -v tests/test_waveguide_optimization_benchmark.py
```
> [!IMPORTANT]
> Do not run tests in parallel. Do not use `-n` or pytest-xdist.
