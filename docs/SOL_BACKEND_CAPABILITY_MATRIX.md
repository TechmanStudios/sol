# SOL Backend Capability Matrix

This matrix outlines instruction capability mappings across the supported SOL execution backends.

## Capability Tiers Definition

- **native**: Backend executes instruction directly with no fallback.
- **microcoded**: Backend decomposes instruction into native primitives of the same backend.
- **emulated**: Instruction executes via another backend (usually LaneFabric).
- **hybrid**: Dynamic fallback enabled with exact layer attribution.
- **unsupported**: Instruction cannot execute on this backend.
- **unavailable**: Backend or API is absent.
- **failed**: Attempted execution caused validation failure or oracle mismatch.

## Support Matrix Table

| Instruction | lane_fabric_strict | sequencer_shadow_strict | pdm_waveguide_shadow_strict | pdm_waveguide_microcoded_strict | hybrid_shadow |
| :--- | :--- | :--- | :--- | :--- | :--- |
| ADD | `native` | `native` | `native` | `native` | `hybrid` |
| AND | `native` | `native` | `native` | `native` | `hybrid` |
| CMP | `native` | `native` | `native` | `microcoded` | `hybrid` |
| HALT | `native` | `unsupported` | `unsupported` | `microcoded` | `hybrid` |
| JB | `native` | `unsupported` | `unsupported` | `microcoded` | `hybrid` |
| JC | `native` | `unsupported` | `unsupported` | `microcoded` | `hybrid` |
| JMP | `native` | `unsupported` | `unsupported` | `microcoded` | `hybrid` |
| JNB | `native` | `unsupported` | `unsupported` | `microcoded` | `hybrid` |
| JNC | `native` | `unsupported` | `unsupported` | `microcoded` | `hybrid` |
| JNZ | `native` | `unsupported` | `unsupported` | `microcoded` | `hybrid` |
| JZ | `native` | `unsupported` | `unsupported` | `microcoded` | `hybrid` |
| LOAD | `native` | `unsupported` | `unsupported` | `microcoded` | `hybrid` |
| LOAD_IMM | `native` | `unsupported` | `unsupported` | `microcoded` | `hybrid` |
| MOV | `native` | `unsupported` | `unsupported` | `microcoded` | `hybrid` |
| NOT | `native` | `native` | `native` | `native` | `hybrid` |
| OR | `native` | `native` | `native` | `native` | `hybrid` |
| SHL | `native` | `native` | `native` | `native` | `hybrid` |
| SHR | `native` | `native` | `native` | `native` | `hybrid` |
| STORE | `native` | `unsupported` | `unsupported` | `microcoded` | `hybrid` |
| SUB | `native` | `native` | `native` | `native` | `hybrid` |
| XOR | `native` | `native` | `native` | `native` | `hybrid` |

> [!WARNING]
> **Strict Waveguide Whole-Program Caveat**:
> Under strict mode, the sequencer and PDM/waveguide backends cannot execute memory `LOAD`/`STORE`, branching, or multiplication/division operations end-to-end without fallback. It can only claim validated strict execution for ALU register-only sequences. Whole-program execution must fall back to the hybrid execution tier.