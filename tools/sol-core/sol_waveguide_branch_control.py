# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Branch Control
============================
Handles program-counter redirection, conditional/unconditional branch gates,
and status flag evaluations for strict waveguide branch-control pathways.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class WaveguideProgramCounter:
    pc: int
    width: int

@dataclass
class WaveguideBranchCondition:
    flag_name: str
    expected_value: int

@dataclass
class WaveguideBranchGate:
    condition: Optional[WaveguideBranchCondition]
    target_pc: int

@dataclass
class WaveguideBranchTarget:
    label: str
    address: int

@dataclass
class WaveguideBranchDecision:
    taken: bool
    target_pc: int

@dataclass
class WaveguideBranchTrace:
    pc_before: int
    pc_after: int
    condition: Optional[str]
    flags_read: Dict[str, int]
    target: str
    taken: bool

@dataclass
class WaveguideBranchControlReport:
    traces: List[WaveguideBranchTrace] = field(default_factory=list)

def build_waveguide_program_counter(width: int, initial_pc: int = 0) -> WaveguideProgramCounter:
    return WaveguideProgramCounter(pc=initial_pc, width=width)

def build_waveguide_branch_gate(condition: Optional[WaveguideBranchCondition], target_pc: int) -> WaveguideBranchGate:
    return WaveguideBranchGate(condition=condition, target_pc=target_pc)

def evaluate_waveguide_branch_condition(flags: Dict[str, int], condition: Optional[WaveguideBranchCondition]) -> bool:
    if condition is None:
        return True
    flag = condition.flag_name
    expected = condition.expected_value
    return flags.get(flag, 0) == expected

def apply_waveguide_branch_decision(pc: WaveguideProgramCounter, decision: WaveguideBranchDecision) -> WaveguideProgramCounter:
    pc.pc = decision.target_pc
    return pc

def execute_waveguide_branch_instruction(
    instruction: Any,  # WideWordProgramInstruction
    pc: int,
    flags: Dict[str, int],
    labels: Dict[str, int]
) -> tuple[WaveguideBranchDecision, WaveguideBranchTrace]:
    op = instruction.op.upper()
    target_label = str(instruction.dst)
    
    # Resolve target address
    if target_label in labels:
        target_pc = labels[target_label]
    else:
        try:
            target_pc = int(target_label)
        except ValueError:
            target_pc = pc + 1
            
    # Determine branch condition
    condition = None
    cond_desc = None
    
    if op == "JZ":
        condition = WaveguideBranchCondition("zero", 1)
        cond_desc = "zero==1"
    elif op == "JNZ":
        condition = WaveguideBranchCondition("zero", 0)
        cond_desc = "zero==0"
    elif op in ("JC", "JB"):
        # JC and JB are carry/borrow jumps
        flag_name = "borrow" if op == "JB" else "carry"
        condition = WaveguideBranchCondition(flag_name, 1)
        cond_desc = f"{flag_name}==1"
    elif op in ("JNC", "JNB"):
        flag_name = "borrow" if op == "JNB" else "carry"
        condition = WaveguideBranchCondition(flag_name, 0)
        cond_desc = f"{flag_name}==0"
    elif op == "JMP":
        condition = None
        cond_desc = "unconditional"
        
    taken = evaluate_waveguide_branch_condition(flags, condition)
    dest_pc = target_pc if taken else pc + 1
    
    decision = WaveguideBranchDecision(taken=taken, target_pc=dest_pc)
    
    # Read only flags relevant to this conditional branch
    flags_read = {}
    if condition is not None:
        flags_read[condition.flag_name] = flags.get(condition.flag_name, 0)
        
    trace = WaveguideBranchTrace(
        pc_before=pc,
        pc_after=dest_pc,
        condition=cond_desc,
        flags_read=flags_read,
        target=target_label,
        taken=taken
    )
    
    return decision, trace

def summarize_waveguide_branch_control(report: WaveguideBranchControlReport) -> Dict[str, Any]:
    total = len(report.traces)
    taken = sum(1 for t in report.traces if t.taken)
    return {
        "total_branches_executed": total,
        "branches_taken": taken,
        "branches_not_taken": total - taken
    }
