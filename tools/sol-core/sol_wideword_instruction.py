# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL WideWord Instruction and Commit Models
==========================================
Defines WideWord instructions, instruction results, commit packets, and gate reports.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class WideWordInstruction:
    instruction_id: str
    op: str  # e.g., "ADD_WORD", "SUB_WORD", "AND_WORD", "OR_WORD", "XOR_WORD", "NOT_WORD", "SHL_WORD", "SHR_WORD", "COMMIT_WORD", "LOAD_WORD", "STORE_WORD", "RECALL_WORD", "COMMIT_RECALL"
    width: int  # 16, 32, 64
    operands: List[int]
    lane_count: int
    dry_run: bool = True
    required_gates: List[str] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)

@dataclass
class InstructionGateReport:
    passed: bool
    checked_gates: Dict[str, bool]
    errors: List[str]

@dataclass
class WideWordInstructionResult:
    instruction: WideWordInstruction
    result: int
    carry_out: int
    lane_results: List[Any]  # List[ByteALUResult]
    carry_trace: List[bool]
    gate_report: InstructionGateReport
    passed_gates: bool
    evidence: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WordCommitPacket:
    instruction_id: str
    width: int
    op: str
    result: int
    lane_results: List[Dict[str, Any]]
    carry_trace: List[bool]
    gate_report: Dict[str, Any]
    timestamp: float
    reproducibility_hash: str
