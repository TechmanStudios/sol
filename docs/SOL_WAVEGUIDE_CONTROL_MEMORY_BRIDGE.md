# SOL Waveguide Control-Memory Bridge

This document outlines the bridge support for memory execution and control flow inside the strict PDM/waveguide substrate.

## Bridge Support Summary

- **Bridge-Supported**: `JMP`, `JZ`, `JNZ`, `JC`, `JNC`, `JB`, `JNB`, `LOAD`, `STORE`, `MOV`, `LOAD_IMM`, `HALT`
- **Native ALU**: `ADD`, `SUB`, `AND`, `OR`, `XOR`, `NOT`, `SHL`, `SHR`
- **Microcoded**: `CMP` (lowers to `SUB`)

## Compliance Status

Strict PDM/waveguide Micro-ISA v0 full compliance is achieved via the `pdm_waveguide_microcoded_strict` execution path.

> [!IMPORTANT]
> **Shadow Sandbox Caveat**:
> Please note that this is still shadow/sandbox software validation and does not represent real production mutation or real quantum hardware execution.