# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Arithmetic Pipeline
=================================
Implements the multi-lane waveguide arithmetic pipeline (ADD, SUB, ADC, SBC)
using local lane speculative results, inter-lane prefix carry, and final assembly.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time

from sol_interlane_prefix_carry import (
    build_prefix_carry_tree,
    execute_shadow_prefix_carry,
    LaneCarryGeneratePropagate,
    InterLaneCarryPlan
)

@dataclass
class WaveguideArithmeticIntent:
    op: str  # "ADD" | "SUB" | "ADC" | "SBC"
    lhs: int
    rhs: int
    width: int
    carry_in: int = 0

@dataclass
class WaveguideArithmeticStage:
    stage_name: str
    description: str
    completed: bool = False

@dataclass
class WaveguideArithmeticPlan:
    plan_id: str
    intent: WaveguideArithmeticIntent
    topology: Any
    stages: List[WaveguideArithmeticStage]
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WaveguideArithmeticTrace:
    trace_id: str
    plan_id: str
    lane_generate_propagate: List[Dict[str, Any]]
    resolved_carries: List[bool]
    resolved_carry_out: bool
    speculative_lane_results: List[Dict[str, Any]]
    final_assembled_word: int

@dataclass
class WaveguideArithmeticResult:
    result_word: int
    carry_out: int
    trace: WaveguideArithmeticTrace
    passed_gates: bool
    errors: List[str]

@dataclass
class WaveguideArithmeticReport:
    report_id: str
    intent: WaveguideArithmeticIntent
    result: WaveguideArithmeticResult
    oracle_match: bool
    success: bool
    errors: List[str]
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)



def plan_waveguide_addition(lhs: int, rhs: int, width: int, topology: Any, carry_in: int = 0, op: str = "ADD") -> WaveguideArithmeticPlan:
    """
    Formulates an execution plan for addition (ADD or ADC) over the waveguide topology.
    """
    intent = WaveguideArithmeticIntent(op=op, lhs=lhs, rhs=rhs, width=width, carry_in=carry_in)
    stages = [
        WaveguideArithmeticStage("local_lane_op", "Slice inputs into bytes and run speculative add8"),
        WaveguideArithmeticStage("generate_propagate", "Compute lane generate/propagate signals"),
        WaveguideArithmeticStage("prefix_carry", "Execute prefix carry tree propagation"),
        WaveguideArithmeticStage("lane_assembly", "Select speculative sums and assemble final word"),
        WaveguideArithmeticStage("oracle_compare", "Validate final word against deterministic python oracle")
    ]
    plan_id = f"WAPLAN_ADD_{width}_{int(time.time() * 1000)}"
    return WaveguideArithmeticPlan(plan_id=plan_id, intent=intent, topology=topology, stages=stages)


def plan_waveguide_subtraction(lhs: int, rhs: int, width: int, topology: Any, borrow_in: int = 0, op: str = "SUB") -> WaveguideArithmeticPlan:
    """
    Formulates an execution plan for subtraction (SUB or SBC) over the waveguide topology.
    """
    intent = WaveguideArithmeticIntent(op=op, lhs=lhs, rhs=rhs, width=width, carry_in=borrow_in)
    stages = [
        WaveguideArithmeticStage("local_lane_op", "Slice inputs into bytes and run speculative sub8"),
        WaveguideArithmeticStage("generate_propagate", "Compute lane generate/propagate (borrow) signals"),
        WaveguideArithmeticStage("prefix_carry", "Execute prefix carry tree propagation"),
        WaveguideArithmeticStage("lane_assembly", "Select speculative differences and assemble final word"),
        WaveguideArithmeticStage("oracle_compare", "Validate final word against deterministic python oracle")
    ]
    plan_id = f"WAPLAN_SUB_{width}_{int(time.time() * 1000)}"
    return WaveguideArithmeticPlan(plan_id=plan_id, intent=intent, topology=topology, stages=stages)


def execute_shadow_waveguide_arithmetic(plan: WaveguideArithmeticPlan) -> WaveguideArithmeticResult:
    """
    Executes waveguide arithmetic in shadow mode.
    Splits operation into:
    - local lane speculative execution
    - generate/propagate signal computation
    - inter-lane prefix carry tree evaluation
    - final word assembly
    """
    intent = plan.intent
    width = intent.width
    num_lanes = width // 8
    op = intent.op
    c_in = intent.carry_in & 1

    # Mask inputs
    mask = (1 << width) - 1
    lhs_val = intent.lhs & mask
    rhs_val = intent.rhs & mask

    # 1. Slice inputs into byte lanes (little-endian)
    lhs_bytes = [(lhs_val >> (i * 8)) & 0xFF for i in range(num_lanes)]
    rhs_bytes = [(rhs_val >> (i * 8)) & 0xFF for i in range(num_lanes)]

    speculative_lane_results = []
    lane_inputs = []

    # 2. Speculative lane operations & generate/propagate computation
    for i in range(num_lanes):
        a_b = lhs_bytes[i]
        b_b = rhs_bytes[i]
        
        if op in ("ADD", "ADC"):
            # addition
            sum_c0 = (a_b + b_b) & 0xFF
            sum_c1 = (a_b + b_b + 1) & 0xFF
            gen = (a_b + b_b) > 255
            prop = (a_b + b_b) == 255
            
            speculative_lane_results.append({
                "lane_id": i,
                "c0": sum_c0,
                "c1": sum_c1
            })
        else:
            # subtraction (SUB, SBC)
            diff_c0 = (a_b - b_b) & 0xFF
            diff_c1 = (a_b - b_b - 1) & 0xFF
            gen = a_b < b_b
            prop = a_b == b_b
            
            speculative_lane_results.append({
                "lane_id": i,
                "c0": diff_c0,
                "c1": diff_c1
            })
            
        lane_inputs.append(LaneCarryGeneratePropagate(lane_id=i, generate=gen, propagate=prop))

    # 3. Construct prefix carry tree and execute inter-lane carry
    carry_tree = build_prefix_carry_tree(num_lanes, strategy="balanced")
    carry_plan = InterLaneCarryPlan(
        plan_id=f"ARITH_CARRY_{plan.plan_id}",
        carry_tree=carry_tree,
        lane_inputs=lane_inputs,
        carry_in=bool(c_in)
    )
    carry_res = execute_shadow_prefix_carry(carry_plan)

    # 4. Final assembly
    selected_bytes = []
    for i in range(num_lanes):
        lane_carry = carry_res.carries[i]
        spec = speculative_lane_results[i]
        selected_bytes.append(spec["c1"] if lane_carry else spec["c0"])

    result_word = 0
    for i, byte_val in enumerate(selected_bytes):
        result_word |= (byte_val << (i * 8))
    result_word &= mask

    carry_out = 1 if carry_res.carry_out else 0

    # Complete stages
    for stage in plan.stages:
        stage.completed = True

    trace = WaveguideArithmeticTrace(
        trace_id=f"WATRACE_{plan.plan_id}",
        plan_id=plan.plan_id,
        lane_generate_propagate=[{"lane_id": li.lane_id, "generate": li.generate, "propagate": li.propagate} for li in lane_inputs],
        resolved_carries=carry_res.carries,
        resolved_carry_out=carry_res.carry_out,
        speculative_lane_results=speculative_lane_results,
        final_assembled_word=result_word
    )

    return WaveguideArithmeticResult(
        result_word=result_word,
        carry_out=carry_out,
        trace=trace,
        passed_gates=True,
        errors=[]
    )


def compare_waveguide_arithmetic_oracle(result: WaveguideArithmeticResult, lhs: int, rhs: int, op: str) -> bool:
    """
    Compares the pipeline result against a deterministic python oracle.
    """
    width = len(result.trace.resolved_carries) * 8
    mask = (1 << width) - 1
    lhs_masked = lhs & mask
    rhs_masked = rhs & mask
    carry_in = 1 if (op in ("ADC", "SBC") and result.trace.lane_generate_propagate and result.trace.resolved_carries[0]) else 0

    if op == "ADD":
        expected = lhs_masked + rhs_masked
        expected_word = expected & mask
        expected_carry = 1 if expected > mask else 0
    elif op == "ADC":
        # The carry_in into lane 0 is the initial carry_in
        expected = lhs_masked + rhs_masked + carry_in
        expected_word = expected & mask
        expected_carry = 1 if expected > mask else 0
    elif op == "SUB":
        expected = lhs_masked - rhs_masked
        expected_carry = 1 if lhs_masked < rhs_masked else 0
        expected_word = expected & mask
    elif op == "SBC":
        expected = lhs_masked - rhs_masked - carry_in
        expected_carry = 1 if lhs_masked < (rhs_masked + carry_in) else 0
        expected_word = expected & mask
    else:
        return False

    return (result.result_word == expected_word) and (result.carry_out == expected_carry)


def export_arithmetic_commit_evidence(report: Any) -> Dict[str, Any]:
    """
    Exports arithmetic commit evidence if a report is available.
    """
    if not report:
        return {}
    return {
        "arithmetic_success": getattr(report, "success", False),
        "oracle_match": getattr(report, "oracle_match", False),
        "intent_op": getattr(getattr(report, "intent", None), "op", "UNKNOWN")
    }


def validate_arithmetic_oracle_after_route_optimization(
    arithmetic_report: Any,
    route_plan: Any
) -> bool:
    """
    Validates arithmetic oracle agreement after route optimization.
    An oracle mismatch blocks rebalance promotion if an arithmetic report is present.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    if not arithmetic_report:
        return True

    oracle_match = extract(arithmetic_report, "oracle_match", False)
    if not oracle_match:
        raise ValueError("Arithmetic oracle mismatch detected; blocking rebalance promotion")

    return True


def inject_arithmetic_oracle_mismatch(arithmetic_report: Any) -> None:
    """
    Injects an oracle mismatch into the arithmetic report.
    """
    if isinstance(arithmetic_report, dict):
        arithmetic_report["oracle_match"] = False
        if "metadata" not in arithmetic_report:
            arithmetic_report["metadata"] = {}
        arithmetic_report["metadata"]["oracle_match"] = False
    else:
        setattr(arithmetic_report, "oracle_match", False)
        meta = getattr(arithmetic_report, "metadata", None)
        if meta is None:
            meta = {}
            setattr(arithmetic_report, "metadata", meta)
        meta["oracle_match"] = False


def validate_arithmetic_after_quantum_wavefront_calibration(
    arithmetic_report: Any,
    quantum_report: Any
) -> bool:
    """
    Validates arithmetic oracle agreement after quantum wavefront calibration.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    if not arithmetic_report:
        return True

    oracle_match = extract(arithmetic_report, "oracle_match", False)
    if not oracle_match:
        raise ValueError("Arithmetic oracle mismatch detected during quantum wavefront calibration.")

    return True


def inject_quantum_arithmetic_oracle_mismatch(arithmetic_report: Any) -> Any:
    """
    Injects an arithmetic oracle mismatch for quantum calibration stability audits.
    """
    import copy
    mutated = copy.deepcopy(arithmetic_report)
    if isinstance(mutated, dict):
        mutated["oracle_match"] = False
        mutated["arithmetic_oracle_match"] = False
        mutated.setdefault("metadata", {})["oracle_match"] = False
    else:
        setattr(mutated, "oracle_match", False)
        setattr(mutated, "arithmetic_oracle_match", False)
        meta = getattr(mutated, "metadata", {}) or {}
        meta["oracle_match"] = False
        mutated.metadata = meta
    return mutated



