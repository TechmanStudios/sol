# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Micro-ISA v0 Specification
==============================
Defines the instruction contract, categories, operands, flag reads/writes,
and validation utilities for the SOL wide-word CPU architecture.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class MicroISAOperandSpec:
    operand_index: int
    allowed_types: List[str]  # "register", "immediate", "label"
    description: str

@dataclass
class MicroISAFlagSpec:
    reads: List[str] = field(default_factory=list)
    writes: List[str] = field(default_factory=list)

@dataclass
class MicroISASemantics:
    category: str  # "data_movement", "memory", "alu", "bitwise", "shift", "compare", "branch", "control"
    memory_behavior: str  # "read", "write", "none"
    branch_behavior: str  # "conditional", "unconditional", "none"
    oracle_semantics_description: str
    allowed_microcode_lowering: List[str] = field(default_factory=list)

@dataclass
class MicroISAInstruction:
    mnemonic: str
    category: str
    operand_count: int
    operand_types: List[str]
    source_registers: List[str]
    destination_registers: List[str]
    memory_behavior: str
    branch_behavior: str
    flags_read: List[str]
    flags_written: List[str]
    width_behavior: str
    masking_behavior: str
    oracle_semantics: str
    allowed_microcode_lowering: List[str]
    is_required: bool = True
    operand_specs: List[MicroISAOperandSpec] = field(default_factory=list)

@dataclass
class MicroISAProgramContract:
    program_name: str
    supported_widths: List[int] = field(default_factory=lambda: [32, 64])
    requires_compliance: bool = True

@dataclass
class MicroISASpec:
    instructions: Dict[str, MicroISAInstruction] = field(default_factory=dict)
    version: str = "v0"

@dataclass
class MicroISAValidationReport:
    success: bool
    errors: List[str] = field(default_factory=list)

def build_micro_isa_v0_spec() -> MicroISASpec:
    spec = MicroISASpec()
    
    # 1. LOAD_IMM
    spec.instructions["LOAD_IMM"] = MicroISAInstruction(
        mnemonic="LOAD_IMM",
        category="data_movement",
        operand_count=2,
        operand_types=["register", "immediate"],
        source_registers=[],
        destination_registers=["dst"],
        memory_behavior="none",
        branch_behavior="none",
        flags_read=[],
        flags_written=[],
        width_behavior="32_64",
        masking_behavior="standard",
        oracle_semantics="Load immediate value into destination register",
        allowed_microcode_lowering=["register_init"],
        is_required=True,
        operand_specs=[
            MicroISAOperandSpec(0, ["register"], "Destination register"),
            MicroISAOperandSpec(1, ["immediate"], "Immediate integer value")
        ]
    )

    # 2. LOAD
    spec.instructions["LOAD"] = MicroISAInstruction(
        mnemonic="LOAD",
        category="memory",
        operand_count=2,
        operand_types=["register", "register"],
        source_registers=["src1"],
        destination_registers=["dst"],
        memory_behavior="read",
        branch_behavior="none",
        flags_read=[],
        flags_written=[],
        width_behavior="32_64",
        masking_behavior="standard",
        oracle_semantics="Load value from memory address stored in src1 into dst",
        allowed_microcode_lowering=[],
        is_required=True,
        operand_specs=[
            MicroISAOperandSpec(0, ["register"], "Destination register"),
            MicroISAOperandSpec(1, ["register"], "Source address register")
        ]
    )

    # 3. STORE
    spec.instructions["STORE"] = MicroISAInstruction(
        mnemonic="STORE",
        category="memory",
        operand_count=2,
        operand_types=["register", "register"],
        source_registers=["dst", "src1"],
        destination_registers=[],
        memory_behavior="write",
        branch_behavior="none",
        flags_read=[],
        flags_written=[],
        width_behavior="32_64",
        masking_behavior="standard",
        oracle_semantics="Store value from register dst into memory address stored in src1",
        allowed_microcode_lowering=[],
        is_required=True,
        operand_specs=[
            MicroISAOperandSpec(0, ["register"], "Source register holding value"),
            MicroISAOperandSpec(1, ["register"], "Destination address register")
        ]
    )

    # 4. MOV
    spec.instructions["MOV"] = MicroISAInstruction(
        mnemonic="MOV",
        category="data_movement",
        operand_count=2,
        operand_types=["register", "register_or_immediate"],
        source_registers=["src1"],
        destination_registers=["dst"],
        memory_behavior="none",
        branch_behavior="none",
        flags_read=[],
        flags_written=[],
        width_behavior="32_64",
        masking_behavior="standard",
        oracle_semantics="Copy value from src1 to dst register",
        allowed_microcode_lowering=["register_transfer"],
        is_required=True,
        operand_specs=[
            MicroISAOperandSpec(0, ["register"], "Destination register"),
            MicroISAOperandSpec(1, ["register", "immediate"], "Source register or immediate value")
        ]
    )

    # 5. ADD
    spec.instructions["ADD"] = MicroISAInstruction(
        mnemonic="ADD",
        category="alu",
        operand_count=3,
        operand_types=["register", "register", "register_or_immediate"],
        source_registers=["src1", "src2"],
        destination_registers=["dst"],
        memory_behavior="none",
        branch_behavior="none",
        flags_read=[],
        flags_written=["zero", "carry", "overflow", "sign"],
        width_behavior="32_64",
        masking_behavior="standard",
        oracle_semantics="Add src1 and src2, store in dst, update flags",
        allowed_microcode_lowering=[],
        is_required=True,
        operand_specs=[
            MicroISAOperandSpec(0, ["register"], "Destination register"),
            MicroISAOperandSpec(1, ["register"], "Source register 1"),
            MicroISAOperandSpec(2, ["register", "immediate"], "Source register 2 or immediate value")
        ]
    )

    # 6. SUB
    spec.instructions["SUB"] = MicroISAInstruction(
        mnemonic="SUB",
        category="alu",
        operand_count=3,
        operand_types=["register", "register", "register_or_immediate"],
        source_registers=["src1", "src2"],
        destination_registers=["dst"],
        memory_behavior="none",
        branch_behavior="none",
        flags_read=[],
        flags_written=["zero", "carry", "overflow", "sign", "borrow"],
        width_behavior="32_64",
        masking_behavior="standard",
        oracle_semantics="Subtract src2 from src1, store in dst, update flags",
        allowed_microcode_lowering=[],
        is_required=True,
        operand_specs=[
            MicroISAOperandSpec(0, ["register"], "Destination register"),
            MicroISAOperandSpec(1, ["register"], "Source register 1"),
            MicroISAOperandSpec(2, ["register", "immediate"], "Source register 2 or immediate value")
        ]
    )

    # 7. AND
    spec.instructions["AND"] = MicroISAInstruction(
        mnemonic="AND",
        category="bitwise",
        operand_count=3,
        operand_types=["register", "register", "register_or_immediate"],
        source_registers=["src1", "src2"],
        destination_registers=["dst"],
        memory_behavior="none",
        branch_behavior="none",
        flags_read=[],
        flags_written=["zero", "sign", "carry", "overflow", "borrow"],
        width_behavior="32_64",
        masking_behavior="standard",
        oracle_semantics="Bitwise AND src1 and src2, store in dst, update flags",
        allowed_microcode_lowering=[],
        is_required=True,
        operand_specs=[
            MicroISAOperandSpec(0, ["register"], "Destination register"),
            MicroISAOperandSpec(1, ["register"], "Source register 1"),
            MicroISAOperandSpec(2, ["register", "immediate"], "Source register 2 or immediate value")
        ]
    )

    # 8. OR
    spec.instructions["OR"] = MicroISAInstruction(
        mnemonic="OR",
        category="bitwise",
        operand_count=3,
        operand_types=["register", "register", "register_or_immediate"],
        source_registers=["src1", "src2"],
        destination_registers=["dst"],
        memory_behavior="none",
        branch_behavior="none",
        flags_read=[],
        flags_written=["zero", "sign", "carry", "overflow", "borrow"],
        width_behavior="32_64",
        masking_behavior="standard",
        oracle_semantics="Bitwise OR src1 and src2, store in dst, update flags",
        allowed_microcode_lowering=[],
        is_required=True,
        operand_specs=[
            MicroISAOperandSpec(0, ["register"], "Destination register"),
            MicroISAOperandSpec(1, ["register"], "Source register 1"),
            MicroISAOperandSpec(2, ["register", "immediate"], "Source register 2 or immediate value")
        ]
    )

    # 9. XOR
    spec.instructions["XOR"] = MicroISAInstruction(
        mnemonic="XOR",
        category="bitwise",
        operand_count=3,
        operand_types=["register", "register", "register_or_immediate"],
        source_registers=["src1", "src2"],
        destination_registers=["dst"],
        memory_behavior="none",
        branch_behavior="none",
        flags_read=[],
        flags_written=["zero", "sign", "carry", "overflow", "borrow"],
        width_behavior="32_64",
        masking_behavior="standard",
        oracle_semantics="Bitwise XOR src1 and src2, store in dst, update flags",
        allowed_microcode_lowering=[],
        is_required=True,
        operand_specs=[
            MicroISAOperandSpec(0, ["register"], "Destination register"),
            MicroISAOperandSpec(1, ["register"], "Source register 1"),
            MicroISAOperandSpec(2, ["register", "immediate"], "Source register 2 or immediate value")
        ]
    )

    # 10. NOT
    spec.instructions["NOT"] = MicroISAInstruction(
        mnemonic="NOT",
        category="bitwise",
        operand_count=2,
        operand_types=["register", "register"],
        source_registers=["src1"],
        destination_registers=["dst"],
        memory_behavior="none",
        branch_behavior="none",
        flags_read=[],
        flags_written=["zero", "sign", "carry", "overflow", "borrow"],
        width_behavior="32_64",
        masking_behavior="standard",
        oracle_semantics="Bitwise NOT src1, store in dst, update flags",
        allowed_microcode_lowering=[],
        is_required=True,
        operand_specs=[
            MicroISAOperandSpec(0, ["register"], "Destination register"),
            MicroISAOperandSpec(1, ["register"], "Source register 1")
        ]
    )

    # 11. SHL
    spec.instructions["SHL"] = MicroISAInstruction(
        mnemonic="SHL",
        category="shift",
        operand_count=3,
        operand_types=["register", "register", "register_or_immediate"],
        source_registers=["src1", "src2"],
        destination_registers=["dst"],
        memory_behavior="none",
        branch_behavior="none",
        flags_read=[],
        flags_written=["zero", "sign", "carry", "overflow", "borrow"],
        width_behavior="32_64",
        masking_behavior="standard",
        oracle_semantics="Logical shift left src1 by src2, store in dst, update flags",
        allowed_microcode_lowering=[],
        is_required=True,
        operand_specs=[
            MicroISAOperandSpec(0, ["register"], "Destination register"),
            MicroISAOperandSpec(1, ["register"], "Source register 1"),
            MicroISAOperandSpec(2, ["register", "immediate"], "Shift count register or immediate value")
        ]
    )

    # 12. SHR
    spec.instructions["SHR"] = MicroISAInstruction(
        mnemonic="SHR",
        category="shift",
        operand_count=3,
        operand_types=["register", "register", "register_or_immediate"],
        source_registers=["src1", "src2"],
        destination_registers=["dst"],
        memory_behavior="none",
        branch_behavior="none",
        flags_read=[],
        flags_written=["zero", "sign", "carry", "overflow", "borrow"],
        width_behavior="32_64",
        masking_behavior="standard",
        oracle_semantics="Logical shift right src1 by src2, store in dst, update flags",
        allowed_microcode_lowering=[],
        is_required=True,
        operand_specs=[
            MicroISAOperandSpec(0, ["register"], "Destination register"),
            MicroISAOperandSpec(1, ["register"], "Source register 1"),
            MicroISAOperandSpec(2, ["register", "immediate"], "Shift count register or immediate value")
        ]
    )

    # 13. CMP
    spec.instructions["CMP"] = MicroISAInstruction(
        mnemonic="CMP",
        category="compare",
        operand_count=2,
        operand_types=["register", "register_or_immediate"],
        source_registers=["dst", "src1"],
        destination_registers=[],
        memory_behavior="none",
        branch_behavior="none",
        flags_read=[],
        flags_written=["zero", "carry", "overflow", "sign", "borrow"],
        width_behavior="32_64",
        masking_behavior="standard",
        oracle_semantics="Compare dst and src1 by subtraction (dst - src1), discard result, update flags",
        allowed_microcode_lowering=["subtraction_discard"],
        is_required=True,
        operand_specs=[
            MicroISAOperandSpec(0, ["register"], "First compare operand register"),
            MicroISAOperandSpec(1, ["register", "immediate"], "Second compare operand register or immediate")
        ]
    )

    # 14. JMP
    spec.instructions["JMP"] = MicroISAInstruction(
        mnemonic="JMP",
        category="branch",
        operand_count=1,
        operand_types=["label"],
        source_registers=[],
        destination_registers=[],
        memory_behavior="none",
        branch_behavior="unconditional",
        flags_read=[],
        flags_written=[],
        width_behavior="32_64",
        masking_behavior="none",
        oracle_semantics="Unconditionally branch to target label",
        allowed_microcode_lowering=[],
        is_required=True,
        operand_specs=[
            MicroISAOperandSpec(0, ["label"], "Target label or instruction address")
        ]
    )

    # 15. JZ
    spec.instructions["JZ"] = MicroISAInstruction(
        mnemonic="JZ",
        category="branch",
        operand_count=1,
        operand_types=["label"],
        source_registers=[],
        destination_registers=[],
        memory_behavior="none",
        branch_behavior="conditional",
        flags_read=["zero"],
        flags_written=[],
        width_behavior="32_64",
        masking_behavior="none",
        oracle_semantics="Branch to target label if zero flag is 1",
        allowed_microcode_lowering=[],
        is_required=True,
        operand_specs=[
            MicroISAOperandSpec(0, ["label"], "Target label or instruction address")
        ]
    )

    # 16. JNZ
    spec.instructions["JNZ"] = MicroISAInstruction(
        mnemonic="JNZ",
        category="branch",
        operand_count=1,
        operand_types=["label"],
        source_registers=[],
        destination_registers=[],
        memory_behavior="none",
        branch_behavior="conditional",
        flags_read=["zero"],
        flags_written=[],
        width_behavior="32_64",
        masking_behavior="none",
        oracle_semantics="Branch to target label if zero flag is 0",
        allowed_microcode_lowering=[],
        is_required=True,
        operand_specs=[
            MicroISAOperandSpec(0, ["label"], "Target label or instruction address")
        ]
    )

    # 17. JC
    spec.instructions["JC"] = MicroISAInstruction(
        mnemonic="JC",
        category="branch",
        operand_count=1,
        operand_types=["label"],
        source_registers=[],
        destination_registers=[],
        memory_behavior="none",
        branch_behavior="conditional",
        flags_read=["carry"],
        flags_written=[],
        width_behavior="32_64",
        masking_behavior="none",
        oracle_semantics="Branch to target label if carry flag is 1",
        allowed_microcode_lowering=[],
        is_required=True,
        operand_specs=[
            MicroISAOperandSpec(0, ["label"], "Target label or instruction address")
        ]
    )

    # 18. JNC
    spec.instructions["JNC"] = MicroISAInstruction(
        mnemonic="JNC",
        category="branch",
        operand_count=1,
        operand_types=["label"],
        source_registers=[],
        destination_registers=[],
        memory_behavior="none",
        branch_behavior="conditional",
        flags_read=["carry"],
        flags_written=[],
        width_behavior="32_64",
        masking_behavior="none",
        oracle_semantics="Branch to target label if carry flag is 0",
        allowed_microcode_lowering=[],
        is_required=True,
        operand_specs=[
            MicroISAOperandSpec(0, ["label"], "Target label or instruction address")
        ]
    )

    # 19. JB
    spec.instructions["JB"] = MicroISAInstruction(
        mnemonic="JB",
        category="branch",
        operand_count=1,
        operand_types=["label"],
        source_registers=[],
        destination_registers=[],
        memory_behavior="none",
        branch_behavior="conditional",
        flags_read=["borrow"],
        flags_written=[],
        width_behavior="32_64",
        masking_behavior="none",
        oracle_semantics="Branch to target label if borrow flag is 1",
        allowed_microcode_lowering=[],
        is_required=True,
        operand_specs=[
            MicroISAOperandSpec(0, ["label"], "Target label or instruction address")
        ]
    )

    # 20. JNB
    spec.instructions["JNB"] = MicroISAInstruction(
        mnemonic="JNB",
        category="branch",
        operand_count=1,
        operand_types=["label"],
        source_registers=[],
        destination_registers=[],
        memory_behavior="none",
        branch_behavior="conditional",
        flags_read=["borrow"],
        flags_written=[],
        width_behavior="32_64",
        masking_behavior="none",
        oracle_semantics="Branch to target label if borrow flag is 0",
        allowed_microcode_lowering=[],
        is_required=True,
        operand_specs=[
            MicroISAOperandSpec(0, ["label"], "Target label or instruction address")
        ]
    )

    # 21. HALT
    spec.instructions["HALT"] = MicroISAInstruction(
        mnemonic="HALT",
        category="control",
        operand_count=0,
        operand_types=[],
        source_registers=[],
        destination_registers=[],
        memory_behavior="none",
        branch_behavior="none",
        flags_read=[],
        flags_written=[],
        width_behavior="none",
        masking_behavior="none",
        oracle_semantics="Terminate program execution",
        allowed_microcode_lowering=[],
        is_required=True,
        operand_specs=[]
    )
    
    return spec

def validate_instruction_semantics(spec: MicroISASpec, inst_mnemonic: str, operand_values: List[Any]) -> MicroISAValidationReport:
    errors = []
    if inst_mnemonic not in spec.instructions:
        return MicroISAValidationReport(success=False, errors=[f"Unknown instruction: {inst_mnemonic}"])
        
    inst = spec.instructions[inst_mnemonic]
    if len(operand_values) != inst.operand_count:
        errors.append(f"Instruction {inst_mnemonic} expects {inst.operand_count} operands, got {len(operand_values)}")
        
    # Check operand type rules
    for idx, val in enumerate(operand_values):
        if idx >= len(inst.operand_specs):
            break
        spec_op = inst.operand_specs[idx]
        # Match type
        val_type = "unknown"
        if isinstance(val, str):
            if val.startswith("R"):
                val_type = "register"
            else:
                val_type = "label"
        elif isinstance(val, int):
            val_type = "immediate"
            
        # Register or immediate check
        allowed = spec_op.allowed_types
        if val_type not in allowed:
            # Check register_or_immediate fallback
            if "register_or_immediate" in inst.operand_types[idx] and val_type in ("register", "immediate"):
                continue
            errors.append(f"Operand {idx} for {inst_mnemonic} must be of type {allowed}, got {val_type} ({val})")
            
    return MicroISAValidationReport(success=(len(errors) == 0), errors=errors)
