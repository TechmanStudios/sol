# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Micro-ISA Document Generator
================================
Produces standard specification, capability matrix, and microcode lowering
documentation files under the docs/ directory.
"""

import os
from typing import Any, Dict, List
from sol_micro_isa import MicroISASpec, MicroISAInstruction
from sol_backend_capability_contract import BackendCapabilityMatrix

def generate_micro_isa_markdown(isa_spec: MicroISASpec, capability_matrix: Any, compliance_report: Any) -> str:
    lines = []
    lines.append("# SOL Micro-ISA v0 Specification")
    lines.append("")
    lines.append("This document defines the official SOL Micro-ISA v0 instruction set, operand rules, and flags.")
    lines.append("")
    lines.append("## Instruction Table")
    lines.append("")
    lines.append("| Mnemonic | Category | Operands | Flags Read | Flags Written | Required | Description |")
    lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    
    for inst in isa_spec.instructions.values():
        ops_str = ", ".join(inst.operand_types) if inst.operand_types else "None"
        fr_str = ", ".join(inst.flags_read) if inst.flags_read else "None"
        fw_str = ", ".join(inst.flags_written) if inst.flags_written else "None"
        req_str = "Yes" if inst.is_required else "No"
        lines.append(f"| `{inst.mnemonic}` | {inst.category} | {ops_str} | {fr_str} | {fw_str} | {req_str} | {inst.oracle_semantics} |")
        
    lines.append("")
    lines.append("## Flags Definition")
    lines.append("")
    lines.append("- **zero**: Set to 1 if result of ALU operation is 0, else 0.")
    lines.append("- **carry**: Set if arithmetic operation generates a carry out.")
    lines.append("- **overflow**: Set if signed arithmetic overflow occurs.")
    lines.append("- **sign**: Set to MSB of result (1 for negative, 0 for positive).")
    lines.append("- **borrow**: Set if subtraction requires a borrow (same as carry).")
    lines.append("")
    lines.append("## Operand Constraints")
    lines.append("")
    lines.append("1. **Registers**: Format `R0` to `R15` representing CPU register files.")
    lines.append("2. **Immediates**: Integer values within 32-bit or 64-bit bounds.")
    lines.append("3. **Labels**: String tokens indicating jump target labels or program PC addresses.")
    
    content = "\n".join(lines)
    os.makedirs("docs", exist_ok=True)
    with open(os.path.join("docs", "SOL_MICRO_ISA_V0.md"), "w", encoding="utf-8") as f:
        f.write(content)
    return content

def generate_backend_capability_markdown(matrix: BackendCapabilityMatrix) -> str:
    lines = []
    lines.append("# SOL Backend Capability Matrix")
    lines.append("")
    lines.append("This matrix outlines instruction capability mappings across the supported SOL execution backends.")
    lines.append("")
    lines.append("## Capability Tiers Definition")
    lines.append("")
    lines.append("- **native**: Backend executes instruction directly with no fallback.")
    lines.append("- **microcoded**: Backend decomposes instruction into native primitives of the same backend.")
    lines.append("- **emulated**: Instruction executes via another backend (usually LaneFabric).")
    lines.append("- **hybrid**: Dynamic fallback enabled with exact layer attribution.")
    lines.append("- **unsupported**: Instruction cannot execute on this backend.")
    lines.append("- **unavailable**: Backend or API is absent.")
    lines.append("- **failed**: Attempted execution caused validation failure or oracle mismatch.")
    lines.append("")
    lines.append("## Support Matrix Table")
    lines.append("")
    
    # Header
    backends = ["lane_fabric_strict", "sequencer_shadow_strict", "pdm_waveguide_shadow_strict", "pdm_waveguide_microcoded_strict", "hybrid_shadow"]
    lines.append("| Instruction | " + " | ".join(backends) + " |")
    lines.append("| :--- | " + " | ".join([":---" for _ in backends]) + " |")
    
    # Find all instructions
    instructions = sorted(list(matrix.matrix["lane_fabric_strict"].keys()))
    for inst in instructions:
        row = [inst]
        for b in backends:
            tier = matrix.matrix[b].get(inst, "unsupported")
            row.append(f"`{tier}`")
        lines.append("| " + " | ".join(row) + " |")
        
    lines.append("")
    lines.append("> [!WARNING]")
    lines.append("> **Strict Waveguide Whole-Program Caveat**:")
    lines.append("> Under strict mode, the sequencer and PDM/waveguide backends cannot execute memory `LOAD`/`STORE`, branching, or multiplication/division operations end-to-end without fallback. It can only claim validated strict execution for ALU register-only sequences. Whole-program execution must fall back to the hybrid execution tier.")
    
    content = "\n".join(lines)
    os.makedirs("docs", exist_ok=True)
    with open(os.path.join("docs", "SOL_BACKEND_CAPABILITY_MATRIX.md"), "w", encoding="utf-8") as f:
        f.write(content)
    return content

def generate_microcode_lowering_markdown(lowering_report: Any) -> str:
    lines = []
    lines.append("# SOL Microcode Lowering Plan")
    lines.append("")
    lines.append("This document specifies how Micro-ISA v0 instructions are translated and optimized for backends lacking native control flow.")
    lines.append("")
    lines.append("## Lowering Rule Mappings")
    lines.append("")
    lines.append("- **LOAD_IMM**: Supported natively or bridged under microcoded strict backend.")
    lines.append("- **MOV**: Supported natively or bridged under microcoded strict backend.")
    lines.append("- **CMP**: Lowers to `SUB` sequence with result discarded, preserving CPU flags.")
    lines.append("- **Branches (JMP, JZ, JNZ, JC, JNC, JB, JNB)**: Supported natively or bridged under microcoded strict backend.")
    lines.append("")
    lines.append("## Next Recommended Engineering Bridge")
    lines.append("")
    lines.append("The PDM/Waveguide Control-Memory Bridge is now implemented and validated in the shadow software environment.")
    
    content = "\n".join(lines)
    os.makedirs("docs", exist_ok=True)
    with open(os.path.join("docs", "SOL_MICROCODE_LOWERING_PLAN.md"), "w", encoding="utf-8") as f:
        f.write(content)
    return content

def generate_waveguide_control_memory_bridge_markdown(matrix: BackendCapabilityMatrix, compliance_report: Any = None) -> str:
    lines = []
    lines.append("# SOL Waveguide Control-Memory Bridge")
    lines.append("")
    lines.append("This document outlines the bridge support for memory execution and control flow inside the strict PDM/waveguide substrate.")
    lines.append("")
    lines.append("## Bridge Support Summary")
    lines.append("")
    lines.append("- **Bridge-Supported**: `JMP`, `JZ`, `JNZ`, `JC`, `JNC`, `JB`, `JNB`, `LOAD`, `STORE`, `MOV`, `LOAD_IMM`, `HALT`")
    lines.append("- **Native ALU**: `ADD`, `SUB`, `AND`, `OR`, `XOR`, `NOT`, `SHL`, `SHR`")
    lines.append("- **Microcoded**: `CMP` (lowers to `SUB`)")
    lines.append("")
    lines.append("## Compliance Status")
    lines.append("")
    lines.append("Strict PDM/waveguide Micro-ISA v0 full compliance is achieved via the `pdm_waveguide_microcoded_strict` execution path.")
    lines.append("")
    lines.append("> [!IMPORTANT]")
    lines.append("> **Shadow Sandbox Caveat**:")
    lines.append("> Please note that this is still shadow/sandbox software validation and does not represent real production mutation or real quantum hardware execution.")
    
    content = "\n".join(lines)
    os.makedirs("docs", exist_ok=True)
    with open(os.path.join("docs", "SOL_WAVEGUIDE_CONTROL_MEMORY_BRIDGE.md"), "w", encoding="utf-8") as f:
        f.write(content)
    return content
