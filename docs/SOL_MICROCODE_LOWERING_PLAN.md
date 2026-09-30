# SOL Microcode Lowering Plan

This document specifies how Micro-ISA v0 instructions are translated and optimized for backends lacking native control flow.

## Lowering Rule Mappings

- **LOAD_IMM**: Supported natively or bridged under microcoded strict backend.
- **MOV**: Supported natively or bridged under microcoded strict backend.
- **CMP**: Lowers to `SUB` sequence with result discarded, preserving CPU flags.
- **Branches (JMP, JZ, JNZ, JC, JNC, JB, JNB)**: Supported natively or bridged under microcoded strict backend.

## Next Recommended Engineering Bridge

The PDM/Waveguide Control-Memory Bridge is now implemented and validated in the shadow software environment.