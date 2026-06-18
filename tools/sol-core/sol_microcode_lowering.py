# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Micro-ISA Lowering
======================
Implements microcode translation rules and structural validity checks
for decomposing high-level instructions to native hardware primitives.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from sol_micro_isa import MicroISASpec, MicroISAInstruction
from sol_backend_capability_contract import BackendCapabilityMatrix

@dataclass
class MicrocodeOp:
    op: str
    args: List[Any] = field(default_factory=list)

@dataclass
class MicrocodeSequence:
    ops: List[MicrocodeOp] = field(default_factory=list)

@dataclass
class MicrocodeLoweringRule:
    mnemonic: str
    rule_type: str  # "immediate_load", "register_transfer", "compare_subtraction", "blocked"
    description: str

@dataclass
class MicrocodeLoweringPlan:
    rule: MicrocodeLoweringRule
    sequence: Optional[MicrocodeSequence] = None
    status: str = "active"  # "active", "unsupported", "microcode_blocked"
    reason: Optional[str] = None

@dataclass
class MicrocodeLoweringReport:
    plans: Dict[str, MicrocodeLoweringPlan] = field(default_factory=dict)
    success: bool = True

def build_microcode_lowering_rules(isa_spec: MicroISASpec) -> Dict[str, MicrocodeLoweringRule]:
    rules = {}
    
    rules["LOAD_IMM"] = MicrocodeLoweringRule(
        mnemonic="LOAD_IMM",
        rule_type="immediate_load",
        description="Lowers immediate load to register initialization"
    )
    rules["MOV"] = MicrocodeLoweringRule(
        mnemonic="MOV",
        rule_type="register_transfer",
        description="Lowers register copy to register transfer"
    )
    rules["CMP"] = MicrocodeLoweringRule(
        mnemonic="CMP",
        rule_type="compare_subtraction",
        description="Lowers comparison to subtraction with discarded result"
    )
    
    # Blocked branches/control
    for op in ("JMP", "JZ", "JNZ", "JC", "JNC", "JB", "JNB", "LOAD", "STORE", "HALT"):
        rules[op] = MicrocodeLoweringRule(
            mnemonic=op,
            rule_type="blocked",
            description=f"Direct execution required; microcode blocked for {op}"
        )
        
    return rules

def lower_instruction_to_microcode(
    instruction: str,
    backend_capabilities: Dict[str, str]  # maps instruction -> tier for a specific backend
) -> MicrocodeLoweringPlan:
    is_alu = instruction in ("ADD", "SUB", "AND", "OR", "XOR", "NOT", "SHL", "SHR", "CMP")
    
    # 1. Check if the instruction is natively supported by the backend
    native_tier = backend_capabilities.get(instruction, "unsupported")
    if native_tier == "native":
        # Native instructions do not need microcoding decomposition; they execute directly
        rule = MicrocodeLoweringRule(instruction, "native", f"Direct native execution of {instruction}")
        return MicrocodeLoweringPlan(
            rule=rule,
            sequence=MicrocodeSequence(ops=[MicrocodeOp(instruction, [])]),
            status="active"
        )
        
    # 2. Check for microcode options
    if instruction == "CMP":
        # Lower CMP R1 R2 to SUB R0 R1 R2 (where R0 is a discard dummy, or using a subtraction rule)
        # Verify if SUB is native on the backend
        sub_tier = backend_capabilities.get("SUB", "unsupported")
        if sub_tier == "native":
            rule = MicrocodeLoweringRule("CMP", "compare_subtraction", "Decompose CMP to SUB with flags preserved")
            seq = MicrocodeSequence(ops=[
                MicrocodeOp("SUB", ["R_DUMMY", "src1", "src2"])
            ])
            return MicrocodeLoweringPlan(rule=rule, sequence=seq, status="active")
        else:
            rule = MicrocodeLoweringRule("CMP", "blocked", "CMP lowering blocked: SUB is not native")
            return MicrocodeLoweringPlan(rule=rule, status="microcode_blocked", reason="SUB is not native")
            
    elif instruction == "LOAD_IMM":
        # Check if backend supports immediate loading or if it's unsupported
        rule = MicrocodeLoweringRule("LOAD_IMM", "blocked", "LOAD_IMM microcoding blocked")
        return MicrocodeLoweringPlan(rule=rule, status="microcode_blocked", reason="Immediate load not supported by backend")
        
    elif instruction == "MOV":
        rule = MicrocodeLoweringRule("MOV", "blocked", "MOV microcoding blocked")
        return MicrocodeLoweringPlan(rule=rule, status="microcode_blocked", reason="Register transfer not supported by backend")
        
    # Branches, memory operations, halt are blocked from microcode lowering if not native
    if instruction in ("JMP", "JZ", "JNZ", "JC", "JNC", "JB", "JNB", "LOAD", "STORE", "HALT"):
        rule = MicrocodeLoweringRule(instruction, "blocked", f"Control flow or memory operation {instruction} is blocked")
        return MicrocodeLoweringPlan(
            rule=rule,
            status="microcode_blocked",
            reason=f"Backend does not support control flow/memory instruction {instruction} and branch/PC control is absent"
        )
        
    rule = MicrocodeLoweringRule(instruction, "blocked", f"Lowering rules for {instruction} are not defined")
    return MicrocodeLoweringPlan(rule=rule, status="unsupported", reason="No lowering rule defined")

def validate_microcode_sequence(
    sequence: MicrocodeSequence,
    backend_capabilities: Dict[str, str]
) -> bool:
    if not sequence or not sequence.ops:
        return False
    # Every instruction in the sequence must be natively supported by the backend
    for op in sequence.ops:
        if backend_capabilities.get(op.op, "unsupported") != "native":
            return False
    return True

def summarize_microcode_lowering(report: MicrocodeLoweringReport) -> Dict[str, Any]:
    summary = {
        "active_plans": sum(1 for p in report.plans.values() if p.status == "active"),
        "blocked_plans": sum(1 for p in report.plans.values() if p.status == "microcode_blocked"),
        "unsupported_plans": sum(1 for p in report.plans.values() if p.status == "unsupported"),
        "success": report.success
    }
    return summary


def lower_for_pdm_waveguide_microcoded_strict(
    instruction: str,
    capabilities: Dict[str, str]
) -> MicrocodeLoweringPlan:
    is_alu = instruction in ("ADD", "SUB", "AND", "OR", "XOR", "NOT", "SHL", "SHR", "CMP")
    
    # Check if native
    native_tier = capabilities.get(instruction, "unsupported")
    if native_tier == "native":
        rule = MicrocodeLoweringRule(instruction, "native", f"Direct execution of {instruction}")
        return MicrocodeLoweringPlan(
            rule=rule,
            sequence=MicrocodeSequence(ops=[MicrocodeOp(instruction, [])]),
            status="active"
        )
        
    if instruction == "CMP":
        sub_tier = capabilities.get("SUB", "unsupported")
        if sub_tier in ("native", "microcoded"):
            rule = MicrocodeLoweringRule("CMP", "compare_subtraction", "Lower CMP to SUB with flags preserved")
            seq = MicrocodeSequence(ops=[MicrocodeOp("SUB", ["R_DUMMY", "src1", "src2"])])
            return MicrocodeLoweringPlan(rule=rule, sequence=seq, status="active")
        else:
            rule = MicrocodeLoweringRule("CMP", "blocked", "CMP lowering blocked: SUB not native")
            return MicrocodeLoweringPlan(rule=rule, status="microcode_blocked", reason="SUB is not native")
            
    # Under microcoded strict, the bridge supports MOV, LOAD_IMM, memory, branches, and HALT
    if instruction in ("LOAD_IMM", "MOV", "LOAD", "STORE", "JMP", "JZ", "JNZ", "JC", "JNC", "JB", "JNB", "HALT"):
        # These are bridge-supported and thus active
        rule = MicrocodeLoweringRule(instruction, "bridge", f"Decompose {instruction} to bridge operation")
        return MicrocodeLoweringPlan(
            rule=rule,
            sequence=MicrocodeSequence(ops=[MicrocodeOp(instruction, [])]),
            status="active"
        )
        
    rule = MicrocodeLoweringRule(instruction, "blocked", f"Lowering rule for {instruction} not supported")
    return MicrocodeLoweringPlan(rule=rule, status="unsupported", reason="Unsupported under microcoded strict backend")


def validate_waveguide_microcode_sequence(
    sequence: MicrocodeSequence,
    capabilities: Dict[str, str]
) -> bool:
    if not sequence or not sequence.ops:
        return False
    # Under waveguide microcoded strict, the allowed operations in sequence are:
    # 1. Native/ALU operations
    # 2. Bridge operations (MOV, LOAD_IMM, LOAD, STORE, JMP, JZ, JNZ, JC, JNC, JB, JNB, HALT)
    allowed_ops = ["ADD", "SUB", "AND", "OR", "XOR", "NOT", "SHL", "SHR", "CMP",
                   "LOAD_IMM", "MOV", "LOAD", "STORE", "JMP", "JZ", "JNZ", "JC", "JNC", "JB", "JNB", "HALT"]
    for op in sequence.ops:
        if op.op not in allowed_ops:
            return False
        tier = capabilities.get(op.op, "unsupported")
        if tier not in ("native", "microcoded", "hybrid", "emulated"):
            # Check if it is supported by the bridge
            if op.op not in ("LOAD_IMM", "MOV", "LOAD", "STORE", "JMP", "JZ", "JNZ", "JC", "JNC", "JB", "JNB", "HALT"):
                return False
    return True

