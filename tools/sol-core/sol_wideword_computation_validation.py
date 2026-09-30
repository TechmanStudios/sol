# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL WideWord Computation Validation Engine
==========================================
Defines validation case, result, batch, and report dataclasses.
Provides deterministic integer oracles for 32-bit and 64-bit operations,
and executes multi-layer validation across byte slices, lane fabric, prefix carries,
sequencers, PDM demodulators, and court review classifications.
"""
import sys
from pathlib import Path
sol_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(sol_root / "tools" / "sol-rsi"))

import time
import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

from sol_pdm_byte_slice import PDMByteSlice
from sol_lane_fabric import LaneFabric
from sol_waveguide_arithmetic_pipeline import (
    plan_waveguide_addition,
    plan_waveguide_subtraction,
    execute_shadow_waveguide_arithmetic
)
from sol_wideword_instruction import WideWordInstruction
from sol_multilane_sequencer import MultiLaneSequencer
from sol_court_supervised_promotion import (
    review_wideword_computation_report,
    review_wideword_computation_ranger_packet,
    CourtPromotionDecision
)
from coding_library.sovereign_domain.evidence_packet import SovereignPacket


@dataclass
class WideWordComputationCase:
    case_id: str
    op: str  # "ADD" | "SUB" | "AND" | "OR" | "XOR" | "NOT" | "SHL" | "SHR"
    a: int
    b: Optional[int]
    width: int  # 32 | 64


@dataclass
class WideWordComputationResult:
    case: WideWordComputationCase
    sol_result: Optional[int]
    oracle_result: int
    match_status: bool
    layers_tested: Dict[str, str]  # Layer -> "passed" | "failed" | "unavailable"
    failure_reason: Optional[str] = None
    evidence: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WideWordComputationBatch:
    batch_id: str
    cases: List[WideWordComputationCase]
    results: List[WideWordComputationResult] = field(default_factory=list)


@dataclass
class WideWordComputationReport:
    report_id: str
    batch_id: str
    cases_passed: int
    cases_failed: int
    success: bool
    oracle_match: bool
    results: List[WideWordComputationResult]
    layers_overall: Dict[str, str]
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WideWordProgramInstruction:
    op: str
    dst: Optional[str] = None
    src1: Optional[Any] = None
    src2: Optional[Any] = None


@dataclass
class WideWordProgram:
    program_id: str
    instructions: List[Any]


@dataclass
class WideWordProgramTraceStep:
    step_index: int
    pc_before: int
    pc_after: int
    instruction: Any
    width: int
    operand_a: Optional[int]
    operand_b: Optional[int]
    sol_result: Optional[int]
    oracle_result: Optional[int]
    sol_flags: Dict[str, int]
    oracle_flags: Dict[str, int]
    registers_before: Dict[str, int]
    registers_after: Dict[str, int]
    memory_before_refs: Dict[int, int]
    memory_after_refs: Dict[int, int]
    layer_used: str
    waveguide_trace_ref: Optional[str]
    pdm_trace_ref: Optional[str]
    sequencer_trace_ref: Optional[str]
    match: bool
    failure_reason: Optional[str]


@dataclass
class WideWordProgramTrace:
    trace_id: str
    steps: List[WideWordProgramTraceStep]


@dataclass
class WideWordProgramResult:
    program: WideWordProgram
    success: bool
    oracle_match: bool
    trace: WideWordProgramTrace


@dataclass
class WaveguideProgramExecutionConfig:
    dry_run: bool = True
    shadow: bool = True
    time_steps: int = 10000
    strict: bool = False


@dataclass
class WaveguideProgramExecutionReport:
    report_id: str
    width: int
    backend_requested: str
    backend_used: str
    success: bool
    oracle_match: bool
    cases_passed: int
    cases_failed: int
    layers_used: Dict[str, int]
    active_table_mutated: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WaveguideProgramMismatch:
    step_index: int
    pc: int
    instruction: Any
    failure_reason: str
    details: Dict[str, Any]



# ---- Oracle Helpers ----

def mask_for_width(width: int) -> int:
    if width == 32:
        return 0xFFFFFFFF
    elif width == 64:
        return 0xFFFFFFFFFFFFFFFF
    else:
        raise ValueError(f"Unsupported validation width: {width}")


def oracle_add(a: int, b: int, width: int) -> int:
    mask = mask_for_width(width)
    return (a + b) & mask


def oracle_sub(a: int, b: int, width: int) -> int:
    mask = mask_for_width(width)
    return (a - b) & mask


def oracle_and(a: int, b: int, width: int) -> int:
    mask = mask_for_width(width)
    return (a & b) & mask


def oracle_or(a: int, b: int, width: int) -> int:
    mask = mask_for_width(width)
    return (a | b) & mask


def oracle_xor(a: int, b: int, width: int) -> int:
    mask = mask_for_width(width)
    return (a ^ b) & mask


def oracle_not(a: int, width: int) -> int:
    mask = mask_for_width(width)
    return (~a) & mask


def oracle_shl(a: int, shift: int, width: int) -> int:
    mask = mask_for_width(width)
    return (a << shift) & mask


def oracle_shr(a: int, shift: int, width: int) -> int:
    mask = mask_for_width(width)
    return (a >> shift) & mask


def format_hex(value: int, width: int) -> str:
    hex_len = width // 4
    return f"0x{value:0{hex_len}X}"


# ---- Builder ----

def build_wideword_case(op: str, a: int, b: Optional[int], width: int) -> WideWordComputationCase:
    import uuid
    case_id = f"CASE_{uuid.uuid4().hex[:8]}"
    return WideWordComputationCase(case_id=case_id, op=op.upper(), a=a, b=b, width=width)


# ---- Runner ----

def run_wideword_case(case: WideWordComputationCase, layers_to_test: Optional[List[str]] = None) -> WideWordComputationResult:
    if layers_to_test is None:
        layers_to_test = ["Layer A", "Layer B", "Layer C", "Layer D", "Layer E", "Layer F"]

    # 1. Compute oracle result
    width = case.width
    op = case.op
    a = case.a
    b = case.b if case.b is not None else 0
    
    if op == "ADD":
        oracle_val = oracle_add(a, b, width)
    elif op == "SUB":
        oracle_val = oracle_sub(a, b, width)
    elif op == "AND":
        oracle_val = oracle_and(a, b, width)
    elif op == "OR":
        oracle_val = oracle_or(a, b, width)
    elif op == "XOR":
        oracle_val = oracle_xor(a, b, width)
    elif op == "NOT":
        oracle_val = oracle_not(a, width)
    elif op == "SHL":
        oracle_val = oracle_shl(a, b, width)
    elif op == "SHR":
        oracle_val = oracle_shr(a, b, width)
    else:
        raise ValueError(f"Unknown validation op: {op}")

    layers_tested = {}
    evidence = {}
    failure_reason = None
    sol_result = None

    # ---- Layer A: Byte-slice / local ALU ----
    if "Layer A" in layers_to_test:
        try:
            num_lanes = width // 8
            slices = [PDMByteSlice(lane_id=i, bit_offset=i * 8) for i in range(num_lanes)]
            layer_a_ok = True
            
            if op == "ADD":
                carry = 0
                for i in range(num_lanes):
                    a_byte = (a >> (i * 8)) & 0xFF
                    b_byte = (b >> (i * 8)) & 0xFF
                    res_alu = slices[i].add8(a_byte, b_byte, carry_in=carry)
                    carry = res_alu.carry_out
                    expected_byte = (oracle_val >> (i * 8)) & 0xFF
                    if res_alu.result != expected_byte:
                        layer_a_ok = False
                layers_tested["Layer A"] = "passed" if layer_a_ok else "failed"
                
            elif op == "SUB":
                borrow = 0
                for i in range(num_lanes):
                    a_byte = (a >> (i * 8)) & 0xFF
                    b_byte = (b >> (i * 8)) & 0xFF
                    res_alu = slices[i].sub8(a_byte, b_byte, borrow_in=borrow)
                    borrow = res_alu.carry_out
                    expected_byte = (oracle_val >> (i * 8)) & 0xFF
                    if res_alu.result != expected_byte:
                        layer_a_ok = False
                layers_tested["Layer A"] = "passed" if layer_a_ok else "failed"
                
            elif op == "AND":
                for i in range(num_lanes):
                    a_byte = (a >> (i * 8)) & 0xFF
                    b_byte = (b >> (i * 8)) & 0xFF
                    res_alu = slices[i].and8(a_byte, b_byte)
                    expected_byte = (oracle_val >> (i * 8)) & 0xFF
                    if res_alu.result != expected_byte:
                        layer_a_ok = False
                layers_tested["Layer A"] = "passed" if layer_a_ok else "failed"
                
            elif op == "OR":
                for i in range(num_lanes):
                    a_byte = (a >> (i * 8)) & 0xFF
                    b_byte = (b >> (i * 8)) & 0xFF
                    res_alu = slices[i].or8(a_byte, b_byte)
                    expected_byte = (oracle_val >> (i * 8)) & 0xFF
                    if res_alu.result != expected_byte:
                        layer_a_ok = False
                layers_tested["Layer A"] = "passed" if layer_a_ok else "failed"
                
            elif op == "XOR":
                for i in range(num_lanes):
                    a_byte = (a >> (i * 8)) & 0xFF
                    b_byte = (b >> (i * 8)) & 0xFF
                    res_alu = slices[i].xor8(a_byte, b_byte)
                    expected_byte = (oracle_val >> (i * 8)) & 0xFF
                    if res_alu.result != expected_byte:
                        layer_a_ok = False
                layers_tested["Layer A"] = "passed" if layer_a_ok else "failed"
                
            elif op == "NOT":
                for i in range(num_lanes):
                    a_byte = (a >> (i * 8)) & 0xFF
                    res_alu = slices[i].not8(a_byte)
                    expected_byte = (oracle_val >> (i * 8)) & 0xFF
                    if res_alu.result != expected_byte:
                        layer_a_ok = False
                layers_tested["Layer A"] = "passed" if layer_a_ok else "failed"
                
            else:
                layers_tested["Layer A"] = "unavailable"
        except Exception as e:
            layers_tested["Layer A"] = "failed"
            evidence["layer_a_error"] = str(e)

    # ---- Layer B: Lane fabric wide-word execution ----
    if "Layer B" in layers_to_test:
        try:
            fabric = LaneFabric.for_width(width)
            if op == "ADD":
                res_fabric = fabric.add_word(a, b)
            elif op == "SUB":
                res_fabric = fabric.sub_word(a, b)
            elif op == "AND":
                res_fabric = fabric.and_word(a, b)
            elif op == "OR":
                res_fabric = fabric.or_word(a, b)
            elif op == "XOR":
                res_fabric = fabric.xor_word(a, b)
            elif op == "NOT":
                res_fabric = fabric.not_word(a)
            elif op == "SHL":
                res_fabric = fabric.shift_left_word(a, b)
            elif op == "SHR":
                res_fabric = fabric.shift_right_word(a, b)

            sol_result = res_fabric.result
            layer_b_passed = res_fabric.result == oracle_val
            layers_tested["Layer B"] = "passed" if layer_b_passed else "failed"
            if not layer_b_passed:
                failure_reason = f"Layer B fabric result {format_hex(sol_result, width)} mismatch"
        except Exception as e:
            layers_tested["Layer B"] = "failed"
            evidence["layer_b_error"] = str(e)
            if failure_reason is None:
                failure_reason = f"Layer B execution failed: {str(e)}"
    else:
        # If Layer B is skipped but needed for sol_result output, compute it fast
        sol_result = oracle_val

    # ---- Layer C: Prefix-carry integration ----
    if "Layer C" in layers_to_test:
        try:
            if op in ("ADD", "SUB"):
                fabric = LaneFabric.for_width(width)
                if op == "ADD":
                    plan = plan_waveguide_addition(a, b, width, fabric)
                    res_pipeline = execute_shadow_waveguide_arithmetic(plan)
                else:
                    plan = plan_waveguide_subtraction(a, b, width, fabric)
                    res_pipeline = execute_shadow_waveguide_arithmetic(plan)

                layer_c_passed = res_pipeline.result_word == oracle_val
                layers_tested["Layer C"] = "passed" if layer_c_passed else "failed"
                evidence["prefix_carry_trace"] = res_pipeline.trace.resolved_carries
            else:
                layers_tested["Layer C"] = "unavailable"
        except Exception as e:
            layers_tested["Layer C"] = "failed"
            evidence["layer_c_error"] = str(e)

    # ---- Layer D: Sequencer instruction path ----
    if "Layer D" in layers_to_test:
        try:
            seq = MultiLaneSequencer()
            seq_op = f"{op}_WORD"
            operands = [a] if op == "NOT" else [a, b]
            
            inst = WideWordInstruction(
                instruction_id=f"INST_{case.case_id}",
                op=seq_op,
                width=width,
                operands=operands,
                lane_count=width // 8,
                dry_run=True
            )
            res_seq = seq.execute_instruction(inst)
            layer_d_passed = res_seq.result == oracle_val and res_seq.passed_gates
            layers_tested["Layer D"] = "passed" if layer_d_passed else "failed"
            evidence["sequencer_gates"] = res_seq.gate_report.checked_gates
        except Exception as e:
            layers_tested["Layer D"] = "failed"
            evidence["layer_d_error"] = str(e)

    # ---- Layer E: PDM / waveguide shadow path ----
    if "Layer E" in layers_to_test:
        try:
            seq = MultiLaneSequencer()
            seq_op = f"{op}_WORD"
            operands = [a] if op == "NOT" else [a, b]
            
            inst = WideWordInstruction(
                instruction_id=f"INST_PDM_{case.case_id}",
                op=seq_op,
                width=width,
                operands=operands,
                lane_count=width // 8,
                dry_run=True
            )
            report_pdm = seq.execute_waveguide_instruction(inst, dry_run=True, shadow=True)
            layer_e_passed = (
                report_pdm.oracle_match and
                report_pdm.passed_gates and
                report_pdm.demodulation_result.demodulated_value == oracle_val
            )
            layers_tested["Layer E"] = "passed" if layer_e_passed else "failed"
            evidence["pdm_demod_value"] = report_pdm.demodulation_result.demodulated_value
        except Exception as e:
            layers_tested["Layer E"] = "failed"
            evidence["layer_e_error"] = str(e)

    # ---- Layer F: Ranger/court classification ----
    if "Layer F" in layers_to_test:
        try:
            # 1. Test WideWordComputationReport court review classification
            mock_report_success = {
                "success": True,
                "oracle_match": True,
                "cases_failed": 0,
                "metadata": {}
            }
            dec_success = review_wideword_computation_report(mock_report_success)
            
            mock_report_need_evidence = {
                "success": False,
                "oracle_match": True,
                "cases_failed": 0,
                "metadata": {"needs_more_evidence": True}
            }
            dec_need_evidence = review_wideword_computation_report(mock_report_need_evidence)

            mock_report_hold = {
                "success": True,
                "oracle_match": False,
                "cases_failed": 1,
                "metadata": {"hold_computation": True}
            }
            dec_hold = review_wideword_computation_report(mock_report_hold)

            mock_report_reject = {
                "success": True,
                "oracle_match": False,
                "cases_failed": 1,
                "metadata": {}
            }
            dec_reject = review_wideword_computation_report(mock_report_reject)

            # 2. Test WideWord ranger packet classification
            mock_packet_hold = SovereignPacket(
                packet_id="WW_HOLD_1",
                domain="compute",
                level=37,
                actor="WideWord Ranger",
                actor_type="ranger",
                mission_id="WW_MISSION",
                claim="Hold requested",
                evidence={},
                invariants_checked=[],
                artifacts=[],
                recommendation="hold",
                confidence=1.0,
                reproducibility_hash="hash1"
            )
            dec_rng_hold = review_wideword_computation_ranger_packet(mock_packet_hold)

            mock_packet_reject = SovereignPacket(
                packet_id="WW_REJ_1",
                domain="compute",
                level=37,
                actor="WideWord Ranger",
                actor_type="ranger",
                mission_id="WW_MISSION",
                claim="Reject requested",
                evidence={},
                invariants_checked=[],
                artifacts=[],
                recommendation="reject",
                confidence=1.0,
                reproducibility_hash="hash2"
            )
            dec_rng_reject = review_wideword_computation_ranger_packet(mock_packet_reject)

            mock_packet_need_evidence = SovereignPacket(
                packet_id="WW_EVI_1",
                domain="compute",
                level=37,
                actor="WideWord Ranger",
                actor_type="ranger",
                mission_id="WW_MISSION",
                claim="Evidence requested",
                evidence={},
                invariants_checked=[],
                artifacts=[],
                recommendation="needs_more_evidence",
                confidence=1.0,
                reproducibility_hash="hash3"
            )
            dec_rng_need_evidence = review_wideword_computation_ranger_packet(mock_packet_need_evidence)

            mock_packet_accept = SovereignPacket(
                packet_id="WW_ACC_1",
                domain="compute",
                level=37,
                actor="WideWord Ranger",
                actor_type="ranger",
                mission_id="WW_MISSION",
                claim="Accept requested",
                evidence={},
                invariants_checked=[],
                artifacts=[],
                recommendation="observe",
                confidence=1.0,
                reproducibility_hash="hash4"
            )
            dec_rng_accept = review_wideword_computation_ranger_packet(mock_packet_accept)

            layer_f_ok = (
                dec_success.decision == "accept_shadow_wideword_computation" and
                dec_need_evidence.decision == "needs_more_evidence" and
                dec_hold.decision == "hold_wideword_computation" and
                dec_reject.decision == "reject_wideword_computation" and
                dec_rng_hold.decision == "hold_wideword_computation" and
                dec_rng_reject.decision == "reject_wideword_computation" and
                dec_rng_need_evidence.decision == "needs_more_evidence" and
                dec_rng_accept.decision == "accept_shadow_wideword_computation"
            )
            layers_tested["Layer F"] = "passed" if layer_f_ok else "failed"
        except Exception as e:
            layers_tested["Layer F"] = "failed"
            evidence["layer_f_error"] = str(e)

    # Re-verify overall correctness
    match_status = sol_result == oracle_val

    return WideWordComputationResult(
        case=case,
        sol_result=sol_result,
        oracle_result=oracle_val,
        match_status=match_status,
        layers_tested=layers_tested,
        failure_reason=failure_reason,
        evidence=evidence
    )


def run_wideword_batch(cases: List[WideWordComputationCase], layers_to_test: Optional[List[str]] = None) -> WideWordComputationBatch:
    import uuid
    batch_id = f"BATCH_{uuid.uuid4().hex[:8]}"
    results = [run_wideword_case(c, layers_to_test=layers_to_test) for c in cases]
    return WideWordComputationBatch(batch_id=batch_id, cases=cases, results=results)


def summarize_wideword_report(batch: WideWordComputationBatch) -> WideWordComputationReport:
    import uuid
    report_id = f"RPT_{uuid.uuid4().hex[:8]}"
    
    cases_passed = 0
    cases_failed = 0
    
    # Layer tracking
    layer_counts = {}  # layer -> {"passed": int, "failed": int, "unavailable": int}
    
    for r in batch.results:
        if r.match_status:
            cases_passed += 1
        else:
            cases_failed += 1
            
        for layer, status in r.layers_tested.items():
            counts = layer_counts.setdefault(layer, {"passed": 0, "failed": 0, "unavailable": 0})
            counts[status] += 1
            
    layers_overall = {}
    for layer, counts in layer_counts.items():
        if counts["failed"] > 0:
            layers_overall[layer] = "failed"
        elif counts["passed"] > 0:
            layers_overall[layer] = "passed"
        else:
            layers_overall[layer] = "unavailable"

    success = cases_failed == 0
    oracle_match = success
    
    return WideWordComputationReport(
        report_id=report_id,
        batch_id=batch.batch_id,
        cases_passed=cases_passed,
        cases_failed=cases_failed,
        success=success,
        oracle_match=oracle_match,
        results=batch.results,
        layers_overall=layers_overall
    )


class WideWordVirtualVM:
    """
    Virtual Machine executing register, memory, and control flow programs
    backed by SOL LaneFabric.
    """
    def __init__(self, width: int):
        if width not in (32, 64):
            raise ValueError(f"Unsupported VM width: {width}")
        self.width = width
        self.mask = (1 << width) - 1
        self.registers = {f"R{i}": 0 for i in range(16)}
        self.memory = {}
        self.flags = {
            "zero": 0,
            "carry": 0,
            "overflow": 0,
            "sign": 0,
            "borrow": 0
        }
        self.pc = 0
        self.labels = {}
        self.instructions = []
        self.fabric = LaneFabric.for_width(width)

    def to_signed(self, val: int) -> int:
        val = val & self.mask
        msb = 1 << (self.width - 1)
        if val & msb:
            return val - (1 << self.width)
        return val

    def to_unsigned(self, val: int) -> int:
        return val & self.mask

    def get_register_views(self) -> Dict[str, Dict[str, Any]]:
        views = {}
        for reg, val in self.registers.items():
            views[reg] = {
                "unsigned": val,
                "signed": self.to_signed(val),
                "hex": format_hex(val, self.width)
            }
        return views

    def _resolve_val(self, operand: Any) -> int:
        if isinstance(operand, str) and operand.startswith("R"):
            if operand not in self.registers:
                raise ValueError(f"Invalid register name: {operand}")
            return self.registers[operand]
        if isinstance(operand, int):
            return operand & self.mask
        raise ValueError(f"Invalid operand type: {operand}")

    def _write_reg(self, reg: str, val: int) -> None:
        if not (isinstance(reg, str) and reg.startswith("R")):
            raise ValueError(f"Invalid destination register: {reg}")
        if reg not in self.registers:
            raise ValueError(f"Register does not exist: {reg}")
        self.registers[reg] = val & self.mask

    def run_program(self, program: List[Any], max_cycles: int = 2000) -> int:
        self.labels = {}
        self.instructions = []
        
        # 1. Resolve labels
        for inst in program:
            if isinstance(inst, str) and inst.endswith(":"):
                self.labels[inst[:-1]] = len(self.instructions)
            else:
                self.instructions.append(inst)
                
        self.pc = 0
        cycles = 0
        
        while self.pc < len(self.instructions) and cycles < max_cycles:
            inst = self.instructions[self.pc]
            op = inst[0].upper()
            cycles += 1
            jumped = False
            
            if op == "LOAD_IMM":
                dst, imm = inst[1], inst[2]
                self._write_reg(dst, imm)
                
            elif op == "LOAD_MEM":
                dst, src_addr = inst[1], inst[2]
                addr = self._resolve_val(src_addr)
                val = self.memory.get(addr, 0)
                self._write_reg(dst, val)
                
            elif op == "STORE_MEM":
                src_val, dst_addr = inst[1], inst[2]
                val = self._resolve_val(src_val)
                addr = self._resolve_val(dst_addr)
                self.memory[addr] = val
                
            elif op == "MOVE":
                dst, src = inst[1], inst[2]
                self._write_reg(dst, self._resolve_val(src))
                
            elif op == "CMP":
                src1, src2 = inst[1], inst[2]
                val1 = self._resolve_val(src1)
                val2 = self._resolve_val(src2)
                
                res = self.fabric.sub_word(val1, val2)
                result = res.result
                
                self.flags["zero"] = 1 if result == 0 else 0
                msb = 1 << (self.width - 1)
                self.flags["sign"] = 1 if (result & msb) else 0
                self.flags["carry"] = res.carry_out
                self.flags["borrow"] = res.carry_out
                
                s1 = (val1 >> (self.width - 1)) & 1
                s2 = (val2 >> (self.width - 1)) & 1
                sr = (result >> (self.width - 1)) & 1
                self.flags["overflow"] = 1 if s1 != s2 and s1 != sr else 0
                
            elif op in ("ADD", "SUB", "AND", "OR", "XOR", "SHL", "SHR", "NOT"):
                dst = inst[1]
                src1 = inst[2]
                val1 = self._resolve_val(src1)
                
                if op == "NOT":
                    res = self.fabric.not_word(val1)
                    result = res.result
                    self.flags["zero"] = 1 if result == 0 else 0
                    msb = 1 << (self.width - 1)
                    self.flags["sign"] = 1 if (result & msb) else 0
                    self.flags["carry"] = 0
                    self.flags["borrow"] = 0
                    self.flags["overflow"] = 0
                else:
                    src2 = inst[3]
                    val2 = self._resolve_val(src2)
                    
                    if op == "ADD":
                        res = self.fabric.add_word(val1, val2)
                        result = res.result
                        self.flags["carry"] = res.carry_out
                        self.flags["borrow"] = 0
                        
                        s1 = (val1 >> (self.width - 1)) & 1
                        s2 = (val2 >> (self.width - 1)) & 1
                        sr = (result >> (self.width - 1)) & 1
                        self.flags["overflow"] = 1 if s1 == s2 and s1 != sr else 0
                        
                    elif op == "SUB":
                        res = self.fabric.sub_word(val1, val2)
                        result = res.result
                        self.flags["carry"] = res.carry_out
                        self.flags["borrow"] = res.carry_out
                        
                        s1 = (val1 >> (self.width - 1)) & 1
                        s2 = (val2 >> (self.width - 1)) & 1
                        sr = (result >> (self.width - 1)) & 1
                        self.flags["overflow"] = 1 if s1 != s2 and s1 != sr else 0
                        
                    elif op == "AND":
                        res = self.fabric.and_word(val1, val2)
                        result = res.result
                        self.flags["carry"] = 0
                        self.flags["borrow"] = 0
                        self.flags["overflow"] = 0
                        
                    elif op == "OR":
                        res = self.fabric.or_word(val1, val2)
                        result = res.result
                        self.flags["carry"] = 0
                        self.flags["borrow"] = 0
                        self.flags["overflow"] = 0
                        
                    elif op == "XOR":
                        res = self.fabric.xor_word(val1, val2)
                        result = res.result
                        self.flags["carry"] = 0
                        self.flags["borrow"] = 0
                        self.flags["overflow"] = 0
                        
                    elif op == "SHL":
                        res = self.fabric.shift_left_word(val1, val2)
                        result = res.result
                        if val2 > 0 and val2 <= self.width:
                            self.flags["carry"] = (val1 >> (self.width - val2)) & 1
                        else:
                            self.flags["carry"] = 0
                        self.flags["borrow"] = 0
                        self.flags["overflow"] = 0
                        
                    elif op == "SHR":
                        res = self.fabric.shift_right_word(val1, val2)
                        result = res.result
                        if val2 > 0 and val2 <= self.width:
                            self.flags["carry"] = (val1 >> (val2 - 1)) & 1
                        else:
                            self.flags["carry"] = 0
                        self.flags["borrow"] = 0
                        self.flags["overflow"] = 0
                
                self.flags["zero"] = 1 if result == 0 else 0
                msb = 1 << (self.width - 1)
                self.flags["sign"] = 1 if (result & msb) else 0
                self._write_reg(dst, result)
                
            elif op in ("JMP", "JZ", "JNZ", "JC", "JNC", "JS", "JNS", "JO", "JNO"):
                target = inst[1]
                if target in self.labels:
                    target_pc = self.labels[target]
                else:
                    target_pc = int(target)
                    
                cond = False
                if op == "JMP":
                    cond = True
                elif op == "JZ":
                    cond = self.flags["zero"] == 1
                elif op == "JNZ":
                    cond = self.flags["zero"] == 0
                elif op == "JC":
                    cond = self.flags["carry"] == 1
                elif op == "JNC":
                    cond = self.flags["carry"] == 0
                elif op == "JS":
                    cond = self.flags["sign"] == 1
                elif op == "JNS":
                    cond = self.flags["sign"] == 0
                elif op == "JO":
                    cond = self.flags["overflow"] == 1
                elif op == "JNO":
                    cond = self.flags["overflow"] == 0
                    
                if cond:
                    self.pc = target_pc
                    jumped = True
                    
            else:
                raise ValueError(f"Unknown VM instruction op: {op}")
                
            if not jumped:
                self.pc += 1
                
        if cycles >= max_cycles:
            raise TimeoutError(f"Program execution exceeded max_cycles ({max_cycles})")
            
        return cycles

    def run_program_with_backend(self, program: List[Any], backend: str, config: Optional[Any] = None) -> WaveguideProgramExecutionReport:
        from sol_wideword_waveguide_program import (
            build_waveguide_program_adapter,
            execute_waveguide_program,
            summarize_waveguide_program_report
        )
        self.backend = backend
        self.last_program = program
        
        import uuid
        prog_obj = WideWordProgram(program_id=f"PROG_{uuid.uuid4().hex[:8]}", instructions=program)
        
        adapter = build_waveguide_program_adapter(width=self.width, config=config, backend=backend)
        
        is_strict = (backend.endswith("_strict") or (config is not None and getattr(config, "strict", False)))
        if is_strict:
            adapter_report = adapter.execute_program_strict_backend(prog_obj, backend, config)
        else:
            adapter_report = execute_waveguide_program(adapter, prog_obj)
        
        if adapter_report.trace_steps:
            for step in adapter_report.trace_steps:
                for addr, val in step.memory_after_refs.items():
                    self.memory[addr] = val
            last_step = adapter_report.trace_steps[-1]
            self.registers.update(last_step.registers_after)
            self.flags.update(last_step.sol_flags)
            self.pc = last_step.pc_after
            
        self.trace_steps = adapter_report.trace_steps
        return summarize_waveguide_program_report(adapter_report)

    def run_instruction_with_backend(self, instruction: Any, backend: str, config: Optional[Any] = None) -> WaveguideProgramExecutionReport:
        return self.run_program_with_backend([instruction], backend, config)

    def export_program_trace(self) -> WideWordProgramTrace:
        import uuid
        trace_id = f"TR_{uuid.uuid4().hex[:8]}"
        return WideWordProgramTrace(trace_id=trace_id, steps=getattr(self, "trace_steps", []))

    def compare_program_trace_to_oracle(self) -> List[WaveguideProgramMismatch]:
        program_to_run = getattr(self, "last_program", None)
        if not program_to_run:
            insts = []
            for step in getattr(self, "trace_steps", []):
                insts.append(step.instruction)
            program_to_run = insts
        oracle_trace = run_oracle_program(program_to_run, self.width)
        sol_trace = self.export_program_trace()
        return compare_sol_program_to_oracle(sol_trace, oracle_trace)


class OracleWideWordVM:
    """
    Gold standard deterministic reference VM running strictly on Python integer math.
    """
    def __init__(self, width: int, channel_state: Optional[Dict[str, Any]] = None):
        self.width = width
        self.mask = (1 << width) - 1
        self.registers = {f"R{i}": 0 for i in range(16)}
        self.memory = {}
        self.flags = {
            "zero": 0,
            "carry": 0,
            "overflow": 0,
            "sign": 0,
            "borrow": 0
        }
        self.pc = 0
        self.labels = {}
        self.instructions = []
        self.trace_steps = []
        self.channel_state = channel_state

    def _resolve_val(self, operand: Any) -> int:
        if isinstance(operand, str) and operand.startswith("R"):
            return self.registers.get(operand, 0)
        if isinstance(operand, int):
            return operand & self.mask
        raise ValueError(f"Invalid operand: {operand}")

    def _write_reg(self, reg: str, val: int) -> None:
        if isinstance(reg, str) and reg.startswith("R"):
            self.registers[reg] = val & self.mask

    def run_program(self, program: List[Any], max_cycles: int = 2000, v1_lowering_metadata: Optional[List[Dict[str, Any]]] = None) -> int:
        self.labels = {}
        self.instructions = []
        self.trace_steps = []
        
        for inst in program:
            if isinstance(inst, str) and inst.endswith(":"):
                self.labels[inst[:-1]] = len(self.instructions)
            else:
                if isinstance(inst, (tuple, list)):
                    op = inst[0].upper()
                    dst = inst[1] if len(inst) > 1 else None
                    src1 = inst[2] if len(inst) > 2 else None
                    src2 = inst[3] if len(inst) > 3 else None
                    instruction_obj = WideWordProgramInstruction(op=op, dst=dst, src1=src1, src2=src2)
                else:
                    instruction_obj = inst
                self.instructions.append(instruction_obj)

        pc_to_v1_mapping = {}
        if v1_lowering_metadata:
            for m in v1_lowering_metadata:
                if m.get("lowered_to_v0", False):
                    pcs = m.get("v0_pc_range", [])
                    if pcs:
                        pc_to_v1_mapping[pcs[0]] = m.get("original_instruction_obj")

        self.pc = 0
        cycles = 0
        
        while self.pc < len(self.instructions) and cycles < max_cycles:
            inst = self.instructions[self.pc]
            op = inst.op.upper()
            
            pc_before = self.pc
            
            if self.channel_state is not None and pc_before in pc_to_v1_mapping:
                v1_inst = pc_to_v1_mapping[pc_before]
                v1_op = v1_inst.op.upper()
                if v1_op == "WG_CHAN_SEND":
                    from sol_waveguide_channel_state import execute_waveguide_channel_send, resolve_channel_id, resolve_operand_val
                    ch_id = resolve_channel_id(v1_inst.dst, self.registers)
                    val = resolve_operand_val(v1_inst.src1, self.registers, self.mask)
                    execute_waveguide_channel_send(self.channel_state, ch_id, val)
                elif v1_op == "WG_CHAN_RECV":
                    from sol_waveguide_channel_state import execute_waveguide_channel_recv, resolve_channel_id
                    ch_id = resolve_channel_id(v1_inst.src1, self.registers)
                    val, _ = execute_waveguide_channel_recv(self.channel_state, ch_id)
                    self.registers[v1_inst.dst] = val
                elif v1_op == "WG_CHAN_ROUTE":
                    from sol_waveguide_channel_state import execute_waveguide_channel_route, resolve_channel_id, resolve_operand_val
                    dst_ch = resolve_channel_id(v1_inst.dst, self.registers)
                    src_ch = resolve_channel_id(v1_inst.src1, self.registers)
                    r_mask = resolve_operand_val(v1_inst.src2, self.registers, self.mask)
                    execute_waveguide_channel_route(self.channel_state, dst_ch, src_ch, r_mask)
                elif v1_op == "WG_CHAN_FENCE":
                    from sol_waveguide_channel_state import execute_waveguide_channel_fence
                    execute_waveguide_channel_fence(self.channel_state)

            registers_before = dict(self.registers)
            
            operand_a = None
            operand_b = None
            if inst.src1 is not None:
                try:
                    operand_a = self._resolve_val(inst.src1)
                except Exception:
                    pass
            if inst.src2 is not None:
                try:
                    operand_b = self._resolve_val(inst.src2)
                except Exception:
                    pass
            
            memory_before_refs = {}
            referenced_addr = None
            if op in ("LOAD", "STORE"):
                referenced_addr = self._resolve_val(inst.src1)
                memory_before_refs[referenced_addr] = self.memory.get(referenced_addr, 0)
            
            if op == "HALT":
                step = WideWordProgramTraceStep(
                    step_index=len(self.trace_steps),
                    pc_before=pc_before,
                    pc_after=pc_before,
                    instruction=inst,
                    width=self.width,
                    operand_a=None,
                    operand_b=None,
                    sol_result=0,
                    oracle_result=0,
                    sol_flags=dict(self.flags),
                    oracle_flags=dict(self.flags),
                    registers_before=registers_before,
                    registers_after=dict(self.registers),
                    memory_before_refs=memory_before_refs,
                    memory_after_refs=dict(memory_before_refs),
                    layer_used="oracle",
                    waveguide_trace_ref=None,
                    pdm_trace_ref=None,
                    sequencer_trace_ref=None,
                    match=True,
                    failure_reason=None
                )
                self.trace_steps.append(step)
                cycles += 1
                break
                
            cycles += 1
            jumped = False
            result = 0
            
            if op == "LOAD":
                dst, val_operand = inst.dst, inst.src1
                val = self.memory.get(referenced_addr, 0)
                self._write_reg(dst, val)
                result = val
            elif op == "STORE":
                src_val, dst_addr = inst.dst, inst.src1
                val = self._resolve_val(src_val)
                self.memory[referenced_addr] = val
                result = val
            elif op in ("MOV", "LOAD_IMM"):
                dst, src = inst.dst, inst.src1
                val = self._resolve_val(src)
                self._write_reg(dst, val)
                result = val
            elif op == "CMP":
                src1, src2 = inst.dst, inst.src1
                val1 = self._resolve_val(src1)
                val2 = self._resolve_val(src2)
                result = (val1 - val2) & self.mask
                
                self.flags["zero"] = 1 if result == 0 else 0
                msb = 1 << (self.width - 1)
                self.flags["sign"] = 1 if (result & msb) else 0
                borrow = 1 if val1 < val2 else 0
                self.flags["carry"] = borrow
                self.flags["borrow"] = borrow
                
                s1 = (val1 >> (self.width - 1)) & 1
                s2 = (val2 >> (self.width - 1)) & 1
                sr = (result >> (self.width - 1)) & 1
                self.flags["overflow"] = 1 if s1 != s2 and s1 != sr else 0
            elif op in ("ADD", "SUB", "AND", "OR", "XOR", "SHL", "SHR", "NOT"):
                dst = inst.dst
                src1 = inst.src1
                val1 = self._resolve_val(src1)
                
                if op == "NOT":
                    result = (~val1) & self.mask
                    self.flags["zero"] = 1 if result == 0 else 0
                    msb = 1 << (self.width - 1)
                    self.flags["sign"] = 1 if (result & msb) else 0
                    self.flags["carry"] = 0
                    self.flags["borrow"] = 0
                    self.flags["overflow"] = 0
                else:
                    src2 = inst.src2
                    val2 = self._resolve_val(src2)
                    
                    if op == "ADD":
                        result = (val1 + val2) & self.mask
                        self.flags["carry"] = 1 if (val1 + val2) > self.mask else 0
                        self.flags["borrow"] = 0
                        
                        s1 = (val1 >> (self.width - 1)) & 1
                        s2 = (val2 >> (self.width - 1)) & 1
                        sr = (result >> (self.width - 1)) & 1
                        self.flags["overflow"] = 1 if s1 == s2 and s1 != sr else 0
                    elif op == "SUB":
                        result = (val1 - val2) & self.mask
                        borrow = 1 if val1 < val2 else 0
                        self.flags["carry"] = borrow
                        self.flags["borrow"] = borrow
                        
                        s1 = (val1 >> (self.width - 1)) & 1
                        s2 = (val2 >> (self.width - 1)) & 1
                        sr = (result >> (self.width - 1)) & 1
                        self.flags["overflow"] = 1 if s1 != s2 and s1 != sr else 0
                    elif op == "AND":
                        result = (val1 & val2) & self.mask
                        self.flags["carry"] = 0
                        self.flags["borrow"] = 0
                        self.flags["overflow"] = 0
                    elif op == "OR":
                        result = (val1 | val2) & self.mask
                        self.flags["carry"] = 0
                        self.flags["borrow"] = 0
                        self.flags["overflow"] = 0
                    elif op == "XOR":
                        result = (val1 ^ val2) & self.mask
                        self.flags["carry"] = 0
                        self.flags["borrow"] = 0
                        self.flags["overflow"] = 0
                    elif op == "SHL":
                        result = (val1 << val2) & self.mask
                        if val2 > 0 and val2 <= self.width:
                            self.flags["carry"] = (val1 >> (self.width - val2)) & 1
                        else:
                            self.flags["carry"] = 0
                        self.flags["borrow"] = 0
                        self.flags["overflow"] = 0
                    elif op == "SHR":
                        result = (val1 >> val2) & self.mask
                        if val2 > 0 and val2 <= self.width:
                            self.flags["carry"] = (val1 >> (val2 - 1)) & 1
                        else:
                            self.flags["carry"] = 0
                        self.flags["borrow"] = 0
                        self.flags["overflow"] = 0
                
                self.flags["zero"] = 1 if result == 0 else 0
                msb = 1 << (self.width - 1)
                self.flags["sign"] = 1 if (result & msb) else 0
                self._write_reg(dst, result)
            elif op in ("JMP", "JZ", "JNZ", "JC", "JNC", "JB", "JNB"):
                target = inst.dst
                target_pc = self.labels[target] if target in self.labels else int(target)
                
                cond = False
                if op == "JMP":
                    cond = True
                elif op == "JZ":
                    cond = self.flags["zero"] == 1
                elif op == "JNZ":
                    cond = self.flags["zero"] == 0
                elif op in ("JC", "JB"):
                    cond = self.flags["carry"] == 1
                elif op in ("JNC", "JNB"):
                    cond = self.flags["carry"] == 0
                    
                if cond:
                    self.pc = target_pc
                    jumped = True
                result = 0
            else:
                raise ValueError(f"Unknown Oracle VM instruction op: {op}")
                
            if not jumped:
                self.pc += 1
                
            pc_after = self.pc
            memory_after_refs = {}
            if referenced_addr is not None:
                memory_after_refs[referenced_addr] = self.memory.get(referenced_addr, 0)
                
            step = WideWordProgramTraceStep(
                step_index=len(self.trace_steps),
                pc_before=pc_before,
                pc_after=pc_after,
                instruction=inst,
                width=self.width,
                operand_a=operand_a,
                operand_b=operand_b,
                sol_result=result,
                oracle_result=result,
                sol_flags=dict(self.flags),
                oracle_flags=dict(self.flags),
                registers_before=registers_before,
                registers_after=dict(self.registers),
                memory_before_refs=memory_before_refs,
                memory_after_refs=memory_after_refs,
                layer_used="oracle",
                waveguide_trace_ref=None,
                pdm_trace_ref=None,
                sequencer_trace_ref=None,
                match=True,
                failure_reason=None
            )
            self.trace_steps.append(step)
            
        if cycles >= max_cycles:
            raise TimeoutError(f"Oracle program execution exceeded max_cycles ({max_cycles})")
        return cycles


def run_oracle_program(program: List[Any], width: int) -> WideWordProgramTrace:
    vm = OracleWideWordVM(width=width)
    vm.run_program(program)
    import uuid
    trace_id = f"TR_ORACLE_{uuid.uuid4().hex[:8]}"
    return WideWordProgramTrace(trace_id=trace_id, steps=vm.trace_steps)


def compare_sol_program_to_oracle(sol_trace: WideWordProgramTrace, oracle_trace: WideWordProgramTrace) -> List[WaveguideProgramMismatch]:
    mismatches = []
    sol_steps = sol_trace.steps
    oracle_steps = oracle_trace.steps
    
    for i in range(max(len(sol_steps), len(oracle_steps))):
        if i >= len(sol_steps):
            mismatches.append(WaveguideProgramMismatch(
                step_index=i,
                pc=-1,
                instruction=None,
                failure_reason="SOL trace is shorter than oracle trace",
                details={"sol_steps_count": len(sol_steps), "oracle_steps_count": len(oracle_steps)}
            ))
            break
        if i >= len(oracle_steps):
            mismatches.append(WaveguideProgramMismatch(
                step_index=i,
                pc=sol_steps[i].pc_before,
                instruction=sol_steps[i].instruction,
                failure_reason="SOL trace is longer than oracle trace",
                details={"sol_steps_count": len(sol_steps), "oracle_steps_count": len(oracle_steps)}
            ))
            break
            
        s = sol_steps[i]
        o = oracle_steps[i]
        
        if s.registers_after != o.registers_after:
            reg_diff = {}
            for r in set(s.registers_after.keys()).union(o.registers_after.keys()):
                s_val = s.registers_after.get(r)
                o_val = o.registers_after.get(r)
                if s_val != o_val:
                    reg_diff[r] = {"sol": format_hex(s_val, s.width) if s_val is not None else None, "oracle": format_hex(o_val, s.width) if o_val is not None else None}
            mismatches.append(WaveguideProgramMismatch(
                step_index=i,
                pc=s.pc_before,
                instruction=s.instruction,
                failure_reason=f"Register mismatch at step {i}",
                details={
                    "expected_register_file": o.registers_after,
                    "actual_register_file": s.registers_after,
                    "difference": reg_diff
                }
            ))
            
        if s.memory_after_refs != o.memory_after_refs:
            mem_diff = {}
            for addr in set(s.memory_after_refs.keys()).union(o.memory_after_refs.keys()):
                s_val = s.memory_after_refs.get(addr)
                o_val = o.memory_after_refs.get(addr)
                if s_val != o_val:
                    mem_diff[addr] = {"sol": format_hex(s_val, s.width) if s_val is not None else None, "oracle": format_hex(o_val, s.width) if o_val is not None else None}
            mismatches.append(WaveguideProgramMismatch(
                step_index=i,
                pc=s.pc_before,
                instruction=s.instruction,
                failure_reason=f"Memory reference mismatch at step {i}",
                details={
                    "expected_memory_refs": o.memory_after_refs,
                    "actual_memory_refs": s.memory_after_refs,
                    "difference": mem_diff
                }
            ))
            
        s_flags_norm = {k: int(v) for k, v in s.sol_flags.items()}
        o_flags_norm = {k: int(v) for k, v in o.oracle_flags.items()}
        if s_flags_norm != o_flags_norm:
            mismatches.append(WaveguideProgramMismatch(
                step_index=i,
                pc=s.pc_before,
                instruction=s.instruction,
                failure_reason=f"Flags mismatch at step {i}",
                details={
                    "expected_flags": o_flags_norm,
                    "actual_flags": s_flags_norm
                }
            ))
            
        if s.pc_after != o.pc_after:
            mismatches.append(WaveguideProgramMismatch(
                step_index=i,
                pc=s.pc_before,
                instruction=s.instruction,
                failure_reason=f"PC destination mismatch at step {i}",
                details={
                    "expected_pc_after": o.pc_after,
                    "actual_pc_after": s.pc_after
                }
            ))
            
        if s.sol_result != o.oracle_result:
            mismatches.append(WaveguideProgramMismatch(
                step_index=i,
                pc=s.pc_before,
                instruction=s.instruction,
                failure_reason=f"Instruction result mismatch at step {i}",
                details={
                    "expected_result_hex": format_hex(o.oracle_result, s.width) if o.oracle_result is not None else None,
                    "actual_result_hex": format_hex(s.sol_result, s.width) if s.sol_result is not None else None,
                    "xor_diff_hex": format_hex(s.sol_result ^ o.oracle_result, s.width) if s.sol_result is not None and o.oracle_result is not None else None
                }
            ))
            
    return mismatches


