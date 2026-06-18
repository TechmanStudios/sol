# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Trace Replay Harness
==================================
Audits and replays execution traces to verify state transition accuracy,
correct register/flag/memory states, and trace metadata consistency.
"""

from typing import List, Dict, Any, Tuple, Optional
from sol_wideword_computation_validation import mask_for_width

def validate_prefix_carry_trace_metadata(step: Any, width: int) -> Tuple[bool, str]:
    """
    Validates parallel prefix carry routing metadata structure and consistency.
    """
    meta = getattr(step, "prefix_carry_metadata", None)
    if meta is None:
        return True, ""
        
    if not isinstance(meta, dict):
        return False, "prefix_carry_metadata is not a dictionary"
        
    required_keys = {"strategy", "lanes", "resolved_carries", "final_carry_out", "signals"}
    missing = required_keys - set(meta.keys())
    if missing:
        return False, f"Missing required prefix-carry metadata keys: {missing}"
        
    if meta["strategy"] != "prefix_carry_group_routing":
        return False, f"Invalid prefix-carry strategy: {meta['strategy']}"
        
    expected_lanes = width // 8
    if meta["lanes"] != expected_lanes:
        return False, f"Lanes count {meta['lanes']} does not match expected {expected_lanes} for width {width}"
        
    if not isinstance(meta["resolved_carries"], list) or len(meta["resolved_carries"]) != expected_lanes:
        return False, f"Invalid resolved_carries list of length {len(meta['resolved_carries']) if isinstance(meta['resolved_carries'], list) else 'non-list'}, expected {expected_lanes}"
        
    if meta["final_carry_out"] not in (0, 1):
        return False, f"Invalid final_carry_out value: {meta['final_carry_out']}"
        
    if not isinstance(meta["signals"], list) or len(meta["signals"]) != expected_lanes:
        return False, f"Invalid signals list of length {len(meta['signals']) if isinstance(meta['signals'], list) else 'non-list'}, expected {expected_lanes}"
        
    for idx, sig in enumerate(meta["signals"]):
        if not isinstance(sig, dict) or "generate" not in sig or "propagate" not in sig:
            return False, f"Malformed carry signal dict at index {idx}"
        if sig["generate"] not in (0, 1) or sig["propagate"] not in (0, 1):
            return False, f"Invalid signal values at index {idx}: generate={sig['generate']}, propagate={sig['propagate']}"
            
    return True, ""

def validate_scheduler_trace_metadata(step: Any) -> Tuple[bool, str]:
    """
    Validates scoreboard scheduler wavefront metadata structure and consistency.
    """
    meta = getattr(step, "scheduler_metadata", None)
    if meta is None:
        return True, ""
        
    if not isinstance(meta, dict):
        return False, "scheduler_metadata is not a dictionary"
        
    required_keys = {"scheduler_enabled", "wavefront_id", "batch_index", "original_pcs", "hazards_checked", "barrier_reason"}
    missing = required_keys - set(meta.keys())
    if missing:
        return False, f"Missing required scheduler metadata keys: {missing}"
        
    if meta["scheduler_enabled"] is not True:
        return False, "scheduler_enabled flag must be True when metadata is present"
        
    if not isinstance(meta["original_pcs"], list):
        return False, f"original_pcs must be a list, got {type(meta['original_pcs'])}"
        
    if step.pc_before not in meta["original_pcs"]:
        return False, f"Current instruction PC {step.pc_before} is not present in original_pcs {meta['original_pcs']}"
        
    return True, ""

def validate_predication_trace_metadata(step: Any) -> Tuple[bool, str]:
    """
    Validates predication metadata structure and consistency.
    """
    meta = getattr(step, "predication_metadata", None)
    if meta is None:
        return True, ""
        
    if not isinstance(meta, dict):
        return False, "predication_metadata is not a dictionary"
        
    required_keys = {
        "predication_enabled", "diamond_id", "condition_opcode", "predicate_value",
        "original_condition_pc", "then_pc_range", "else_pc_range", "merge_pc",
        "lowering_strategy", "registers_merged", "flags_merged", "memory_effects"
    }
    missing = required_keys - set(meta.keys())
    if missing:
        return False, f"Missing required predication metadata keys: {missing}"
        
    if meta["predication_enabled"] is not True:
        return False, "predication_enabled flag must be True"
        
    if meta["lowering_strategy"] != "conditional_select":
        return False, f"Invalid predication lowering strategy: {meta['lowering_strategy']}"
        
    if meta["memory_effects"] is not False:
        return False, "Predicated diamonds must not have memory effects"
        
    if step.instruction.op.upper() == "STORE":
        return False, "STORE instruction not allowed in predicated diamond"
        
    pc = step.pc_before
    if pc != meta["original_condition_pc"]:
        in_then = pc in meta["then_pc_range"]
        in_else = pc in meta["else_pc_range"]
        is_jmp = (step.instruction.op.upper() == "JMP" and meta["else_pc_range"] and pc + 1 == meta["else_pc_range"][0])
        if not (in_then or in_else or is_jmp):
            return False, f"Instruction PC {pc} is not within then/else ranges or valid JMP for diamond {meta['diamond_id']}"
            
    return True, ""

def validate_memory_alias_trace_metadata(step: Any, trace_steps: List[Any]) -> Tuple[bool, str]:
    """
    Validates range boundaries, reorder safety, and alias claims in memory trace steps.
    """
    meta = getattr(step, "memory_alias_metadata", None)
    if meta is None:
        return True, ""
        
    if not isinstance(meta, dict):
        return False, "memory_alias_metadata is not a dictionary"
        
    required_keys = {"memory_alias_analysis_enabled", "memory_reorder_safe"}
    missing = required_keys - set(meta.keys())
    if missing:
        return False, f"Missing required memory alias keys: {missing}"
        
    if meta["memory_alias_analysis_enabled"] is True and meta["memory_reorder_safe"] is True:
        more_keys = {"memory_accesses", "alias_classification", "shard_id", "range_start", "range_end"}
        missing_more = more_keys - set(meta.keys())
        if missing_more:
            return False, f"Missing required memory alias keys for reorder safe access: {missing_more}"
            
        if not isinstance(meta["memory_accesses"], list) or len(meta["memory_accesses"]) == 0:
            return False, "memory_accesses must be a non-empty list"
            
        if meta["alias_classification"] != "NO_ALIAS":
            return False, f"Reorder-safe memory access cannot have alias classification {meta['alias_classification']}"
            
        for acc in meta["memory_accesses"]:
            if acc.get("address_kind") == "dynamic":
                return False, "Dynamic memory access cannot be marked reorder-safe"
            start = acc.get("range_start")
            end = acc.get("range_end")
            if start is None or end is None or not (0 <= start <= end):
                return False, f"Invalid memory access range: [{start}, {end}]"
                
        # Verify NO_ALIAS claim against all other memory accesses in the execution trace
        from sol_waveguide_memory_alias import classify_waveguide_memory_alias
        this_acc = meta["memory_accesses"][0]
        for other_step in trace_steps:
            if other_step is not step:
                other_meta = getattr(other_step, "memory_alias_metadata", None)
                if other_meta and other_meta.get("memory_alias_analysis_enabled"):
                    other_accs = other_meta.get("memory_accesses", [])
                    if other_accs:
                        other_acc = other_accs[0]
                        # If at least one is a write, they must not overlap
                        if this_acc["access_kind"] == "write" or other_acc["access_kind"] == "write":
                            alias = classify_waveguide_memory_alias(this_acc, other_acc)
                            if alias != "NO_ALIAS":
                                return False, f"Overlap/conflict detected with step at PC {other_step.pc_before}: alias classification is {alias} but claimed NO_ALIAS"
                                
    return True, ""

def validate_waveguide_pass_manager_trace_metadata(
    trace_steps: List[Any],
    pass_manager_report: Optional[Dict[str, Any]],
    width: int,
    enforce_missing_report: bool = False
) -> Tuple[bool, str]:
    """
    Validates consistency of the overall pass manager execution report and individual step metadata.
    """
    if pass_manager_report is None:
        if enforce_missing_report:
            # If no report, ensure no optimization metadata is present on any step (raw strict execution)
            for i, step in enumerate(trace_steps):
                if getattr(step, "scheduler_metadata", None) is not None:
                    return False, f"Step {i} has scheduler_metadata but pass manager report is missing."
                if getattr(step, "predication_metadata", None) is not None:
                    return False, f"Step {i} has predication_metadata but pass manager report is missing."
                if getattr(step, "memory_alias_metadata", None) is not None:
                    ma = getattr(step, "memory_alias_metadata", None)
                    if ma and ma.get("memory_alias_analysis_enabled"):
                        return False, f"Step {i} has enabled memory_alias_metadata but pass manager report is missing."
        return True, ""
        
    if not isinstance(pass_manager_report, dict):
        return False, "pass_manager_report is not a dictionary"
        
    required_keys = {"profile_id", "passes", "raw_instruction_count", "optimized_plan_units"}
    missing = required_keys - set(pass_manager_report.keys())
    if missing:
        return False, f"Missing required pass manager report keys: {missing}"
        
    # Check passes list
    passes = pass_manager_report["passes"]
    if not isinstance(passes, list):
        return False, "passes in pass_manager_report must be a list"
        
    # Map from pass_id to enabled state
    pass_enabled = {}
    for idx, p in enumerate(passes):
        if not isinstance(p, dict) or "pass_id" not in p or "enabled" not in p:
            return False, f"Malformed pass dict at index {idx} in passes list"
        pass_enabled[p["pass_id"]] = p["enabled"]
        
    # Check that pass order is valid
    from sol_waveguide_optimization_pass_manager import validate_waveguide_pass_order
    run_passes = [p["pass_id"] for p in passes if p["enabled"]]
    try:
        validate_waveguide_pass_order(run_passes)
    except ValueError as e:
        return False, f"Invalid pass order in pass manager report: {e}"
        
    # Check trace steps vs enabled passes
    for i, step in enumerate(trace_steps):
        # 1. Scoreboard Scheduling
        sch_meta = getattr(step, "scheduler_metadata", None)
        if sch_meta is not None:
            if not pass_enabled.get("scoreboard_scheduling", False):
                return False, f"Step {i} has scheduler_metadata but scoreboard_scheduling pass is disabled."
                
        # 2. Branch Predication
        pred_meta = getattr(step, "predication_metadata", None)
        if pred_meta is not None:
            if not pass_enabled.get("branch_predication", False):
                return False, f"Step {i} has predication_metadata but branch_predication pass is disabled."
                
        # 3. Memory Alias
        ma_meta = getattr(step, "memory_alias_metadata", None)
        if ma_meta is not None:
            if ma_meta.get("memory_alias_analysis_enabled") and not pass_enabled.get("memory_alias_analysis", False):
                return False, f"Step {i} has enabled memory_alias_metadata but memory_alias_analysis pass is disabled."
                
    return True, ""

def validate_v1_candidate_lowering_metadata(
    step: Any,
    pass_manager_report: Optional[Dict[str, Any]]
) -> Tuple[bool, str]:
    """
    Validates that if v1 lowering metadata is attached to the step or present in the report,
    it is consistent, well-formed, and matches compliance rules.
    """
    if pass_manager_report is None:
        v1_meta = getattr(step, "v1_lowering_metadata", None)
        if v1_meta is not None:
            return False, "Step has v1_lowering_metadata but pass manager report is missing."
        return True, ""
        
    v1_metadata = pass_manager_report.get("v1_lowering_metadata", [])
    v1_enabled = any(p.get("pass_id") == "v1_candidate_lowering" and p.get("enabled") for p in pass_manager_report.get("passes", []))
    
    if not v1_enabled:
        if v1_metadata:
            return False, "v1_lowering_metadata is present in report but v1_candidate_lowering pass is disabled."
        return True, ""
        
    # Check that all metadata items in the report are well-formed
    for m in v1_metadata:
        if not isinstance(m, dict):
            return False, "v1 lowering metadata entry is not a dictionary"
        required_keys = {"micro_isa_v1_candidate", "candidate_opcode", "lowered_to_v0", "lowering_safe", "skip_reason"}
        missing = required_keys - set(m.keys())
        if missing:
            return False, f"Missing keys in v1 lowering metadata entry: {missing}"
            
        if m.get("lowered_to_v0"):
            if "candidate_pc" not in m or "v0_pc_range" not in m:
                return False, "Lowered candidate metadata missing candidate_pc or v0_pc_range"
            if not isinstance(m["v0_pc_range"], list) or not all(isinstance(x, int) for x in m["v0_pc_range"]):
                return False, "v0_pc_range must be a list of integers"
        else:
            if m.get("lowering_safe") is not False:
                return False, "Rejected candidate must have lowering_safe=False"
            if not m.get("skip_reason"):
                return False, "Rejected candidate must have a non-empty skip_reason"
                
    return True, ""

def validate_v1_trace_metadata_against_spec(
    step: Any,
    pass_manager_report: Optional[Dict[str, Any]],
    spec: Optional[Dict[str, Any]] = None
) -> Tuple[bool, str]:
    """
    Validates trace metadata for v1 candidate instructions against the formal spec.
    """
    if spec is None:
        from sol_micro_isa_v1_spec import build_micro_isa_v1_opcode_spec
        spec = build_micro_isa_v1_opcode_spec()

    # Reject v1 metadata emitted when v1 mode is disabled
    v1_enabled = False
    if pass_manager_report:
        v1_enabled = any(p.get("pass_id") == "v1_candidate_lowering" and p.get("enabled") for p in pass_manager_report.get("passes", []))

    v1_meta = getattr(step, "v1_lowering_metadata", None)
    if not v1_enabled:
        if v1_meta is not None:
            return False, "v1 candidate metadata emitted when v1 mode is disabled"
        if pass_manager_report and pass_manager_report.get("v1_lowering_metadata"):
            return False, "v1_lowering_metadata present in report when v1 mode is disabled"
        return True, ""

    if pass_manager_report:
        v1_metadata = pass_manager_report.get("v1_lowering_metadata", [])
        for m in v1_metadata:
            op = m.get("candidate_opcode")
            if op not in spec:
                return False, f"v1 metadata found for unknown candidate opcode: {op}"
            
            record = spec[op]
            status = record["status"]
            
            # Reject candidate marked unsupported/rejected but executed (lowered/safe)
            if status in ("UNSUPPORTED", "REJECTED"):
                if m.get("lowered_to_v0") or m.get("lowering_safe"):
                    return False, f"Candidate {op} is marked unsupported/rejected but was lowered or marked safe"
            
            # Reject missing required trace metadata keys
            required_keys = set(record.get("trace_metadata", []))
            missing = required_keys - set(m.keys())
            if missing:
                return False, f"Missing required trace metadata keys {missing} for candidate {op}"

    return True, ""

def replay_v1_lowering_trace_mapping(
    step: Any,
    pass_manager_report: Optional[Dict[str, Any]]
) -> Tuple[bool, str]:
    """
    Verifies that if a step executes a PC that belongs to a lowered v1 candidate's v0 PC range,
    it behaves consistently and that rejected candidates are never successfully executed.
    """
    if pass_manager_report is None:
        return True, ""
        
    v1_metadata = pass_manager_report.get("v1_lowering_metadata", [])
    pc = step.pc_before
    
    # Verify that if this PC corresponds to a rejected candidate's PC, the step must not be a success
    for m in v1_metadata:
        if not m.get("lowered_to_v0") and m.get("candidate_pc") == pc:
            if step.layer_used != "unsupported_instruction":
                return False, f"Step executed rejected candidate PC {pc} but layer used was {step.layer_used} (expected unsupported_instruction)"
                
    return True, ""

def validate_v1_lane_vector_trace_metadata(
    step: Any,
    pass_manager_report: Optional[Dict[str, Any]]
) -> Tuple[bool, str]:
    """
    Validates trace metadata specifically for lane/vector candidate operations.
    """
    if pass_manager_report is None:
        return True, ""
        
    v1_metadata = pass_manager_report.get("v1_lowering_metadata", [])
    pc = step.pc_before
    
    for m in v1_metadata:
        op = m.get("candidate_opcode", "")
        if m.get("lowered_to_v0") and pc in m.get("v0_pc_range", []):
            from sol_micro_isa_v1_spec import get_micro_isa_v1_opcode_record
            record = get_micro_isa_v1_opcode_record(op)
            if record and record.get("category") == "vector_lane":
                src2 = m.get("src2")
                
                # Check extract lane index
                if op == "VEC_EXTRACT":
                    if not isinstance(src2, int) or not (0 <= src2 <= 3):
                        return False, f"VEC_EXTRACT lane index {src2} is out of bounds [0, 3]"
                        
                # Check insert lane index
                elif op == "VEC_INSERT":
                    if not isinstance(src2, (tuple, list)) or len(src2) != 2:
                        return False, f"VEC_INSERT src2 must be a 2-tuple (lane_index, src_scalar)"
                    lane_index = src2[0]
                    if not isinstance(lane_index, int) or not (0 <= lane_index <= 3):
                        return False, f"VEC_INSERT lane index {lane_index} is out of bounds [0, 3]"
                        
                # Check lane add/sub/and/or/xor mask
                elif op in {"VEC_LANE_ADD", "VEC_LANE_SUB", "VEC_LANE_AND", "VEC_LANE_OR", "VEC_LANE_XOR"}:
                    if not isinstance(src2, (tuple, list)) or len(src2) != 2:
                        return False, f"{op} src2 must be a 2-tuple (src_b, mask)"
                    mask = src2[1]
                    if not isinstance(mask, int) or not (0 <= mask <= 15):
                        return False, f"{op} mask {mask} is out of bounds [0, 15]"
                        
                # Check mask select mask
                elif op == "VEC_MASK_SELECT":
                    mask = m.get("src1")
                    if isinstance(mask, int) and not (0 <= mask <= 15):
                        return False, f"VEC_MASK_SELECT mask {mask} is out of bounds [0, 15]"
                        
    return True, ""

def validate_v1_waveguide_channel_trace_metadata(
    step: Any,
    pass_manager_report: Optional[Dict[str, Any]]
) -> Tuple[bool, str]:
    """
    Validates trace metadata for waveguide-channel candidate operations.
    """
    if pass_manager_report is None:
        return True, ""
        
    v1_metadata = pass_manager_report.get("v1_lowering_metadata", [])
    pc = step.pc_before
    
    channel_state_enabled = pass_manager_report.get("enable_waveguide_channel_state", False)
    step_meta = getattr(step, "waveguide_channel_metadata", None)
    if step_meta is not None and step_meta.get("waveguide_channel_state_enabled", False):
        channel_state_enabled = True
        
    for m in v1_metadata:
        op = m.get("candidate_opcode", "")
        # Reject if unsupported channel candidate (SEND, RECV, ROUTE) has execute metadata
        if op in {"WG_CHAN_SEND", "WG_CHAN_RECV", "WG_CHAN_ROUTE"}:
            if pc in m.get("v0_pc_range", []):
                if not channel_state_enabled:
                    return False, f"Unsupported channel operation {op} attempted execution"
                
        # Validate channel fence metadata
        if op == "WG_CHAN_FENCE":
            if pc in m.get("v0_pc_range", []):
                if m.get("lowering_strategy") != "waveguide_channel_fence_barrier":
                    return False, f"Invalid lowering strategy for WG_CHAN_FENCE: {m.get('lowering_strategy')}"
                    
    return True, ""

def validate_waveguide_channel_kernel_metadata(
    step: Any,
    trace_steps: List[Any],
    pass_manager_report: Optional[Dict[str, Any]],
    width: int
) -> Tuple[bool, str]:
    """
    Validates recognized and skipped kernel trace metadata.
    """
    meta = getattr(step, "scheduler_metadata", None)
    if meta is None:
        return True, ""
        
    kernel_enabled = pass_manager_report.get("enable_channel_kernel_recognition", False) if pass_manager_report else False
    
    # 1. If kernel recognition is disabled, verify that no active kernel metadata is present
    if not kernel_enabled:
        if meta.get("channel_kernel_recognition_enabled", False):
            return False, "Active channel kernel metadata present but kernel recognition is disabled in config"
            
    # 2. If active kernel metadata is present:
    if meta.get("channel_kernel_recognition_enabled", False):
        k_id = meta.get("channel_kernel_id")
        pc_range = meta.get("kernel_pc_range")
        wfs = meta.get("kernel_wavefronts")
        
        if not k_id or not pc_range or not wfs:
            return False, f"Malformed recognized kernel metadata: k_id={k_id}, pc_range={pc_range}, wfs={wfs}"
            
        if not isinstance(pc_range, (list, tuple)) or len(pc_range) != 2:
            return False, f"Invalid kernel pc_range {pc_range} in metadata"
            
        if pc_range[0] < 0 or pc_range[1] < pc_range[0]:
            return False, f"Invalid kernel pc_range bounds {pc_range}"
            
        if step.pc_before < pc_range[0] or step.pc_before > pc_range[1]:
            return False, f"Step PC {step.pc_before} is outside kernel pc_range {pc_range}"
            
        if meta.get("sandbox_only") is not True:
            return False, "Kernel must claim sandbox_only=True"
        if meta.get("kernel_equivalence_required") is not True:
            return False, "Kernel must claim kernel_equivalence_required=True"
            
        # We validate the entire kernel region once when processing the start PC of the kernel
        if step.pc_before == pc_range[0]:
            actual_inputs = []
            actual_outputs = []
            fence_pcs = []
            routes_in_kernel = []
            
            for p in range(pc_range[0], pc_range[1] + 1):
                for s_step in trace_steps:
                    if s_step.pc_before == p:
                        ch_m = getattr(s_step, "waveguide_channel_metadata", None)
                        s_meta = getattr(s_step, "scheduler_metadata", None)
                        if ch_m:
                            op = ch_m.get("channel_opcode")
                            if op == "WG_CHAN_SEND":
                                actual_outputs.append(ch_m.get("channel_id"))
                            elif op == "WG_CHAN_RECV":
                                actual_inputs.append(ch_m.get("channel_id"))
                            elif op == "WG_CHAN_ROUTE":
                                actual_outputs.append(ch_m.get("dst_channel"))
                                actual_inputs.append(ch_m.get("src_channel"))
                                routes_in_kernel.append({
                                    "pc": p,
                                    "dst": ch_m.get("dst_channel"),
                                    "src": ch_m.get("src_channel"),
                                    "wf": s_meta.get("wavefront_id") if s_meta else None
                                })
                            elif op == "WG_CHAN_FENCE":
                                fence_pcs.append(p)
                                
            # Compare input/output channels
            meta_inputs = sorted(meta.get("input_channels", []))
            meta_outputs = sorted(meta.get("output_channels", []))
            if sorted(list(set(actual_inputs))) != meta_inputs:
                return False, f"Kernel input channels mismatch: expected {meta_inputs}, got actual {sorted(list(set(actual_inputs)))}"
            if sorted(list(set(actual_outputs))) != meta_outputs:
                return False, f"Kernel output channels mismatch: expected {meta_outputs}, got actual {sorted(list(set(actual_outputs)))}"
                
            # Verify fences split wavefronts
            for f_pc in fence_pcs:
                before_wfs = set()
                after_wfs = set()
                for s_step in trace_steps:
                    s_meta = getattr(s_step, "scheduler_metadata", None)
                    if s_meta and s_meta.get("wavefront_id"):
                        if s_step.pc_before < f_pc:
                            before_wfs.add(s_meta["wavefront_id"])
                        elif s_step.pc_before > f_pc:
                            after_wfs.add(s_meta["wavefront_id"])
                overlap = before_wfs.intersection(after_wfs)
                if overlap:
                    return False, f"Fences ordering violation: wavefronts {overlap} crossed fence at PC {f_pc}"
                    
            # Verify route dependencies are preserved in wavefront scheduling
            for i in range(len(routes_in_kernel)):
                for j in range(i + 1, len(routes_in_kernel)):
                    r1 = routes_in_kernel[i]
                    r2 = routes_in_kernel[j]
                    if r1["dst"] == r2["src"]:
                        if r1["wf"] and r2["wf"] and r1["wf"] == r2["wf"]:
                            return False, f"Route dependency violation: dependent routes PC {r1['pc']} and PC {r2['pc']} scheduled in same wavefront {r1['wf']}"
            
    # 3. If skipped kernel metadata is present:
    if "channel_kernel_candidate" in meta:
        cand = meta["channel_kernel_candidate"]
        recognized = meta.get("recognized", True)
        reason = meta.get("skip_reason")
        
        if recognized is not False:
            return False, f"Skipped kernel {cand} must declare recognized=False"
        if not reason:
            return False, f"Skipped kernel {cand} must declare skip_reason"
            
    return True, ""

def validate_waveguide_trace_metadata(
    trace_steps: List[Any],
    program_len: int,
    width: int,
    pass_manager_report: Optional[Dict[str, Any]] = None
) -> Tuple[bool, str]:
    """
    Validates consistency of trace steps, checking boundaries and metadata formats.
    """
    pm_ok, pm_err = validate_waveguide_pass_manager_trace_metadata(trace_steps, pass_manager_report, width)
    if not pm_ok:
        return False, f"Pass manager metadata error: {pm_err}"
    diamond_runs = {}
    
    for i, step in enumerate(trace_steps):
        if step.pc_before < 0 or step.pc_before >= program_len:
            return False, f"Step {i} pc_before ({step.pc_before}) is out of bounds for program length {program_len}"
        if step.pc_after < 0 or step.pc_after > program_len:
            return False, f"Step {i} pc_after ({step.pc_after}) is out of bounds for program length {program_len}"
            
        pc_ok, pc_err = validate_prefix_carry_trace_metadata(step, width)
        if not pc_ok:
            return False, f"Step {i} prefix-carry error: {pc_err}"
            
        sch_ok, sch_err = validate_scheduler_trace_metadata(step)
        if not sch_ok:
            return False, f"Step {i} scheduler error: {sch_err}"
            
        pred_ok, pred_err = validate_predication_trace_metadata(step)
        if not pred_ok:
            return False, f"Step {i} predication error: {pred_err}"
            
        ma_ok, ma_err = validate_memory_alias_trace_metadata(step, trace_steps)
        if not ma_ok:
            return False, f"Step {i} memory alias error: {ma_err}"
            
        v1_ok, v1_err = validate_v1_candidate_lowering_metadata(step, pass_manager_report)
        if not v1_ok:
            return False, f"Step {i} v1 lowering metadata error: {v1_err}"
            
        v1_spec_ok, v1_spec_err = validate_v1_trace_metadata_against_spec(step, pass_manager_report)
        if not v1_spec_ok:
            return False, f"Step {i} v1 spec validation error: {v1_spec_err}"
            
        v1_map_ok, v1_map_err = replay_v1_lowering_trace_mapping(step, pass_manager_report)
        if not v1_map_ok:
            return False, f"Step {i} v1 trace mapping error: {v1_map_err}"

        v1_lane_ok, v1_lane_err = validate_v1_lane_vector_trace_metadata(step, pass_manager_report)
        if not v1_lane_ok:
            return False, f"Step {i} v1 lane/vector error: {v1_lane_err}"
            
        v1_chan_ok, v1_chan_err = validate_v1_waveguide_channel_trace_metadata(step, pass_manager_report)
        if not v1_chan_ok:
            return False, f"Step {i} v1 waveguide channel error: {v1_chan_err}"

        v1_kernel_ok, v1_kernel_err = validate_waveguide_channel_kernel_metadata(step, trace_steps, pass_manager_report, width)
        if not v1_kernel_ok:
            return False, f"Step {i} v1 waveguide channel kernel error: {v1_kernel_err}"

        cost_ok, cost_err = validate_waveguide_cost_model_metadata(step, pass_manager_report)
        if not cost_ok:
            return False, f"Step {i} cost model metadata error: {cost_err}"
            
        tune_ok, tune_err = validate_waveguide_autotuning_metadata(step, pass_manager_report)
        if not tune_ok:
            return False, f"Step {i} autotuning metadata error: {tune_err}"

            
        meta = getattr(step, "predication_metadata", None)
        if meta:
            d_id = meta["diamond_id"]
            if d_id not in diamond_runs:
                diamond_runs[d_id] = []
            diamond_runs[d_id].append(step)
            
    for d_id, steps in diamond_runs.items():
        meta = steps[0].predication_metadata
        pred_val = meta["predicate_value"]
        then_range = meta["then_pc_range"]
        else_range = meta["else_pc_range"]
        
        if pred_val:
            for step in steps:
                if step.pc_before in then_range:
                    return False, f"Step {step.step_index} executed PC {step.pc_before} in skipped then-arm of diamond {d_id}"
        else:
            for step in steps:
                if step.pc_before in else_range:
                    return False, f"Step {step.step_index} executed PC {step.pc_before} in skipped else-arm of diamond {d_id}"
                    
    return True, ""

def replay_waveguide_execution_trace(
    width: int,
    trace_steps: List[Any],
    initial_registers: Optional[Dict[str, int]] = None,
    initial_flags: Optional[Dict[str, int]] = None,
    initial_memory: Optional[Dict[int, int]] = None,
    enable_channel_independence_analysis: bool = False
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Reconstructs execution step-by-step and asserts correctness against the recorded trace.
    Returns (success, error_message, final_state_dict).
    """
    mask = mask_for_width(width)
    
    # Initialize VM state
    registers = {f"R{i}": 0 for i in range(16)}
    if initial_registers:
        for k, v in initial_registers.items():
            registers[k] = v & mask
            
    flags = {"zero": 0, "carry": 0, "overflow": 0, "sign": 0, "borrow": 0}
    if initial_flags:
        flags.update(initial_flags)
        
    memory = {}
    if initial_memory:
        for k, v in initial_memory.items():
            memory[k] = v & mask
            
    pc = 0
    if trace_steps:
        pc = trace_steps[0].pc_before

    channel_state_enabled = any(getattr(step, "waveguide_channel_metadata", None) is not None for step in trace_steps)
    ch_state = None
    if channel_state_enabled:
        from sol_waveguide_channel_state import build_waveguide_channel_state
        ch_state = build_waveguide_channel_state(width_bits=width)
        
    def resolve_val(operand: Any) -> int:
        if isinstance(operand, str) and operand.startswith("R"):
            return registers.get(operand, 0)
        if isinstance(operand, int):
            return operand & mask
        return 0

    for i, step in enumerate(trace_steps):
        if pc != step.pc_before:
            return False, f"Replay step {i}: PC mismatch (local pc={pc}, trace pc_before={step.pc_before})", {}
            
        c_ok, c_err = validate_waveguide_channel_trace_metadata(step, channel_state_enabled, width)
        if not c_ok:
            return False, f"Replay step {i}: channel metadata validation error: {c_err}", {}

        d_ok, d_err = validate_waveguide_channel_dependency_metadata(
            step, trace_steps, enable_channel_independence_analysis
        )
        if not d_ok:
            return False, f"Replay step {i}: channel dependency validation error: {d_err}", {}

        if channel_state_enabled and getattr(step, "waveguide_channel_metadata", None):
            c_ok, c_err = replay_waveguide_channel_trace_step(step, ch_state, width)
            if not c_ok:
                return False, f"Replay step {i}: channel replay error: {c_err}", {}
                
            meta = step.waveguide_channel_metadata
            if meta.get("channel_opcode") == "WG_CHAN_RECV":
                dst = step.instruction.dst
                registers[dst] = meta["value_masked"]
            
        inst = step.instruction
        op = inst.op.upper()
        
        # Track memory operations
        if op == "LOAD":
            addr = resolve_val(inst.src1)
            val = memory.get(addr, 0)
            if val != step.sol_result:
                return False, f"Replay step {i} (LOAD): Replayed value {val} at address {addr} does not match trace sol_result {step.sol_result}", {}
            registers[inst.dst] = val
            
        elif op == "STORE":
            val = resolve_val(inst.dst)
            addr = resolve_val(inst.src1)
            memory[addr] = val
            if val != step.sol_result:
                return False, f"Replay step {i} (STORE): Replayed value {val} stored at address {addr} does not match trace sol_result {step.sol_result}", {}
                
        elif op in ("MOV", "LOAD_IMM"):
            val = resolve_val(inst.src1)
            registers[inst.dst] = val
            if val != step.sol_result:
                return False, f"Replay step {i} ({op}): Replayed value {val} does not match trace sol_result {step.sol_result}", {}
                
        elif op in ("ADD", "SUB", "CMP", "AND", "OR", "XOR", "NOT", "SHL", "SHR"):
            # Check register destinations and ALU operations
            if op == "CMP":
                val1 = resolve_val(inst.dst)
                val2 = resolve_val(inst.src1)
            elif op == "NOT":
                val1 = resolve_val(inst.src1)
                val2 = 0
            else:
                val1 = resolve_val(inst.src1)
                val2 = resolve_val(inst.src2)
                
            local_res = 0
            local_carry = 0
            local_overflow = 0
            local_sign = 0
            local_borrow = 0
            
            # Simple simulation of ALU operations for verification
            if op == "ADD":
                local_res = (val1 + val2) & mask
                local_carry = 1 if (val1 + val2) > mask else 0
                s1 = (val1 >> (width - 1)) & 1
                s2 = (val2 >> (width - 1)) & 1
                sr = (local_res >> (width - 1)) & 1
                local_overflow = 1 if s1 == s2 and s1 != sr else 0
            elif op in ("SUB", "CMP"):
                local_res = (val1 - val2) & mask
                local_carry = 1 if val1 < val2 else 0
                local_borrow = local_carry
                s1 = (val1 >> (width - 1)) & 1
                s2 = (val2 >> (width - 1)) & 1
                sr = (local_res >> (width - 1)) & 1
                local_overflow = 1 if s1 != s2 and s1 != sr else 0
            elif op == "AND":
                local_res = (val1 & val2) & mask
            elif op == "OR":
                local_res = (val1 | val2) & mask
            elif op == "XOR":
                local_res = (val1 ^ val2) & mask
            elif op == "NOT":
                local_res = (~val1) & mask
            elif op == "SHL":
                local_res = (val1 << val2) & mask
                if val2 > 0 and val2 <= width:
                    local_carry = (val1 >> (width - val2)) & 1
            elif op == "SHR":
                local_res = (val1 >> val2) & mask
                
            local_zero = 1 if local_res == 0 else 0
            msb = 1 << (width - 1)
            local_sign = 1 if (local_res & msb) else 0
            
            # Verify result matches
            if op != "CMP" and local_res != step.sol_result:
                return False, f"Replay step {i} ({op}): Local result {local_res} does not match trace sol_result {step.sol_result}", {}
                
            # Verify flags match (within standard ALU scope)
            expected_flags = {
                "zero": local_zero,
                "sign": local_sign,
            }
            if op in ("ADD", "SUB", "CMP"):
                expected_flags["carry"] = local_carry
                expected_flags["borrow"] = local_borrow
                expected_flags["overflow"] = local_overflow
            elif op == "SHL":
                expected_flags["carry"] = local_carry
                
            for k, val in expected_flags.items():
                if step.sol_flags.get(k) != val:
                    return False, f"Replay step {i} ({op}): Flag '{k}' mismatch (local={val}, trace={step.sol_flags.get(k)})", {}
                    
            if op != "CMP":
                registers[inst.dst] = local_res
            flags.update(step.sol_flags)
            
        elif op in ("JMP", "JZ", "JNZ", "JC", "JNC", "JB", "JNB"):
            # Control flow updates PC directly to step.pc_after
            pass
            
        elif op == "HALT":
            pass
            
        # Transition PC
        pc = step.pc_after
        
    final_snapshot = None
    if ch_state:
        from sol_waveguide_channel_state import snapshot_waveguide_channel_state
        final_snapshot = snapshot_waveguide_channel_state(ch_state)
        
    return True, "", {
        "registers": registers,
        "flags": flags,
        "memory": memory,
        "pc": pc,
        "channel_snapshot": final_snapshot
    }

def summarize_waveguide_trace_replay(replay_report: Dict[str, Any]) -> Dict[str, Any]:
    """
    Serializes trace replay verification statistics.
    """
    return {
        "verified": replay_report.get("verified", False),
        "steps_replayed": replay_report.get("steps_replayed", 0),
        "metadata_valid": replay_report.get("metadata_valid", False),
        "error_message": replay_report.get("error_message", "")
    }

def validate_waveguide_channel_trace_metadata(
    step: Any,
    channel_state_enabled: bool,
    width: int
) -> Tuple[bool, str]:
    """
    Validates that a step's waveguide channel metadata is correct and conforms to safety rules.
    """
    meta = getattr(step, "waveguide_channel_metadata", None)
    if not channel_state_enabled:
        if meta is not None:
            return False, "Channel metadata present but channel state is disabled"
        return True, ""
        
    if meta is None:
        return True, ""
        
    if not meta.get("waveguide_channel_state_enabled", False):
        return False, "waveguide_channel_state_enabled is not True in metadata"
        
    if meta.get("external_io", False) is not False:
        return False, "External I/O is not allowed in sandbox channel state"
        
    if meta.get("deterministic", False) is not True:
        return False, "Channel metadata must claim determinism"
        
    opcode = meta.get("channel_opcode", "")
    if opcode not in ("WG_CHAN_SEND", "WG_CHAN_RECV", "WG_CHAN_ROUTE", "WG_CHAN_FENCE"):
        return False, f"Invalid channel opcode in metadata: {opcode}"
        
    mask = (1 << width) - 1
    
    if opcode == "WG_CHAN_SEND":
        ch_id = meta.get("channel_id")
        if not isinstance(ch_id, int):
            return False, "channel_id must be integer"
        val = meta.get("value_masked")
        if val is None or not (0 <= val <= mask):
            return False, f"value_masked {val} is invalid or out of bounds for width {width}"
            
    elif opcode == "WG_CHAN_RECV":
        ch_id = meta.get("channel_id")
        if not isinstance(ch_id, int):
            return False, "channel_id must be integer"
        val = meta.get("value_masked")
        if val is None or not (0 <= val <= mask):
            return False, f"value_masked {val} is invalid or out of bounds for width {width}"
            
    elif opcode == "WG_CHAN_ROUTE":
        dst_ch = meta.get("dst_channel")
        src_ch = meta.get("src_channel")
        if not isinstance(dst_ch, int) or not isinstance(src_ch, int):
            return False, "dst_channel and src_channel must be integers"
            
    return True, ""

def replay_waveguide_channel_trace_step(
    step: Any,
    current_channel_state: Dict[str, Any],
    width: int
) -> Tuple[bool, str]:
    """
    Replays the channel transition in trace replay and validates compliance with channel semantics.
    """
    meta = getattr(step, "waveguide_channel_metadata", None)
    if not meta:
        return True, ""
        
    from sol_waveguide_channel_state import (
        validate_waveguide_channel_id,
        execute_waveguide_channel_send,
        execute_waveguide_channel_recv,
        execute_waveguide_channel_route,
        execute_waveguide_channel_fence
    )
    
    opcode = meta.get("channel_opcode", "")
    
    try:
        if opcode == "WG_CHAN_SEND":
            ch_id = meta["channel_id"]
            val = meta["value_masked"]
            ref_meta = execute_waveguide_channel_send(current_channel_state, ch_id, val)
            if ref_meta["channel_valid_after"] != meta.get("channel_valid_after"):
                return False, "channel_valid_after mismatch on SEND"
                
        elif opcode == "WG_CHAN_RECV":
            ch_id = meta["channel_id"]
            val, ref_meta = execute_waveguide_channel_recv(current_channel_state, ch_id)
            if val != meta["value_masked"]:
                return False, f"Replay RECV value {val} mismatch with metadata value {meta['value_masked']}"
            if ref_meta["channel_valid_after"] != meta.get("channel_valid_after"):
                return False, "channel_valid_after mismatch on RECV"
            if ref_meta["empty_recv_triggered"] != meta.get("empty_recv_triggered"):
                return False, "empty_recv_triggered mismatch on RECV"
                
        elif opcode == "WG_CHAN_ROUTE":
            dst_ch = meta["dst_channel"]
            src_ch = meta["src_channel"]
            route_mask = meta["route_mask"]
            ref_meta = execute_waveguide_channel_route(current_channel_state, dst_ch, src_ch, route_mask)
            if ref_meta["route_enabled"] != meta.get("route_enabled"):
                return False, "route_enabled mismatch on ROUTE"
            if ref_meta["channel_valid_after"] != meta.get("channel_valid_after"):
                return False, "channel_valid_after mismatch on ROUTE"
                
        elif opcode == "WG_CHAN_FENCE":
            ref_meta = execute_waveguide_channel_fence(current_channel_state)
            
    except Exception as e:
        return False, f"Exception during channel transition replay: {str(e)}"
        
    return True, ""

def validate_waveguide_channel_dependency_metadata(
    step: Any,
    trace_steps: List[Any],
    enable_channel_independence_analysis: bool = False
) -> Tuple[bool, str]:
    """
    Validates that a step's channel dependency metadata is safe and conflict-free.
    """
    meta = getattr(step, "scheduler_metadata", None)
    if meta is None:
        return True, ""
        
    enabled = meta.get("channel_dependency_analysis_enabled", False)
    if enabled and not enable_channel_independence_analysis:
        return False, "Channel dependency analysis metadata is active but feature is disabled"
        
    if not enabled:
        return True, ""
        
    # Verify metadata is well-formed
    required_keys = {"channel_dependency_analysis_enabled", "channel_wavefront_id", "channel_ops_batched", "channel_hazards_checked", "channel_hazard_result"}
    missing = required_keys - set(meta.keys())
    if missing:
        return False, f"Missing required channel dependency metadata keys: {missing}"
        
    if meta["channel_hazard_result"] != "NO_CHANNEL_HAZARD":
        return False, f"Invalid channel hazard result in scheduled wavefront: {meta['channel_hazard_result']}"
        
    wf_id = meta["channel_wavefront_id"]
    
    # Collect all trace steps in the same wavefront
    wf_steps = [s for s in trace_steps if getattr(s, "scheduler_metadata", None) and s.scheduler_metadata.get("channel_wavefront_id") == wf_id]
    
    from sol_waveguide_channel_dependency import classify_waveguide_channel_hazard
    
    accesses = []
    for ws in wf_steps:
        c_meta = getattr(ws, "waveguide_channel_metadata", None)
        if c_meta:
            opcode = c_meta.get("channel_opcode")
            reads_ch = []
            writes_ch = []
            reads_regs = []
            writes_regs = []
            is_global = False
            
            if opcode == "WG_CHAN_FENCE":
                is_global = True
            elif opcode == "WG_CHAN_SEND":
                writes_ch.append(c_meta.get("channel_id"))
            elif opcode == "WG_CHAN_RECV":
                reads_ch.append(c_meta.get("channel_id"))
                writes_regs.append(ws.instruction.dst)
            elif opcode == "WG_CHAN_ROUTE":
                dst_ch = c_meta.get("dst_channel")
                src_ch = c_meta.get("src_channel")
                writes_ch.append(dst_ch)
                reads_ch.append(src_ch)
                
            accesses.append({
                "pc": ws.pc_before,
                "opcode": opcode,
                "reads_channels": reads_ch,
                "writes_channels": writes_ch,
                "reads_registers": reads_regs,
                "writes_registers": writes_regs,
                "is_global_barrier": is_global
            })
            
    # Verify no hazards exist between any two accesses in the wavefront
    for idx_i in range(len(accesses)):
        for idx_j in range(idx_i + 1, len(accesses)):
            hazard = classify_waveguide_channel_hazard(accesses[idx_i], accesses[idx_j])
            if hazard != "NO_CHANNEL_HAZARD":
                return False, f"Hazard conflict {hazard} detected in scheduled wavefront {wf_id} between PC {accesses[idx_i]['pc']} and PC {accesses[idx_j]['pc']}"
                
    # Verify that if WG_CHAN_FENCE is in the wavefront, it is the ONLY instruction in it
    has_fence = any(a["is_global_barrier"] for a in accesses)
    if has_fence and len(wf_steps) > 1:
        return False, f"WG_CHAN_FENCE splits scheduling regions and cannot share a wavefront (wavefront {wf_id} has size {len(wf_steps)})"
        
    return True, ""

def validate_waveguide_acceleration_metadata(
    replay_report: Dict[str, Any],
    acceleration_metadata: Optional[Dict[str, Any]]
) -> Tuple[bool, str]:
    """
    Validates acceleration metadata constraints.
    """
    if not acceleration_metadata:
        return True, ""
        
    if acceleration_metadata.get("core_execution_parallelized", False) is not False:
        return False, "Core execution must not claim parallelization"
        
    if acceleration_metadata.get("pytest_parallelism_used", False) is not False:
        return False, "Pytest parallelism must not be used"
        
    return True, ""

def run_waveguide_trace_replay_batch(
    replay_cases: List[Dict[str, Any]],
    acceleration_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Evaluates trace replay cases sequentially or in parallel based on acceleration_config.
    """
    from sol_waveguide_simulation_acceleration import (
        build_waveguide_acceleration_config,
        run_waveguide_trace_replay_batch_serial,
        run_waveguide_trace_replay_batch_accelerated,
        summarize_waveguide_acceleration_report,
        validate_waveguide_acceleration_equivalence
    )
    
    cfg = acceleration_config if acceleration_config else build_waveguide_acceleration_config()
    
    def run_single_replay(case: Dict[str, Any]) -> Dict[str, Any]:
        width = case["width"]
        trace_steps = case["trace_steps"]
        init_regs = case.get("initial_registers")
        init_flags = case.get("initial_flags")
        init_mem = case.get("initial_memory")
        
        # Determine if channel state is enabled in this case
        chan_enabled = any(getattr(step, "waveguide_channel_metadata", None) is not None for step in trace_steps)
        
        ch_state = None
        if chan_enabled:
            from sol_waveguide_channel_state import build_waveguide_channel_state
            ch_state = build_waveguide_channel_state(width_bits=width)
            
        success = True
        err_msg = ""
        
        registers = {f"R{i}": 0 for i in range(16)}
        if init_regs:
            registers.update(init_regs)
        flags = {"zero": 0, "carry": 0, "overflow": 0, "sign": 0, "borrow": 0}
        if init_flags:
            flags.update(init_flags)
        memory = {}
        if init_mem:
            memory.update(init_mem)
            
        # Replay step by step
        for idx, step in enumerate(trace_steps):
            c_ok, c_err = validate_waveguide_channel_trace_metadata(step, chan_enabled, width)
            if not c_ok:
                success = False
                err_msg = f"Step {idx} channel metadata validation failure: {c_err}"
                break
                
            pm_rep = {
                "enable_channel_kernel_recognition": case.get("enable_channel_kernel_recognition", False)
            }
            k_ok, k_err = validate_waveguide_channel_kernel_metadata(step, trace_steps, pm_rep, width)
            if not k_ok:
                success = False
                err_msg = f"Step {idx} channel kernel validation failure: {k_err}"
                break
                
            if ch_state and getattr(step, "waveguide_channel_metadata", None):
                c_ok, c_err = replay_waveguide_channel_trace_step(step, ch_state, width)
                if not c_ok:
                    success = False
                    err_msg = f"Step {idx} channel replay failure: {c_err}"
                    break
                    
                meta = step.waveguide_channel_metadata
                if meta.get("channel_opcode") == "WG_CHAN_RECV":
                    dst = step.instruction.dst
                    registers[dst] = meta["value_masked"]
                    
        if success:
            ok, msg, _ = replay_waveguide_execution_trace(
                width, trace_steps, init_regs, init_flags, init_mem,
                enable_channel_independence_analysis=case.get("enable_channel_independence_analysis", False)
            )
            if not ok:
                success = False
                err_msg = msg
                
        if success and ch_state and case.get("expected_final_channel_snapshot"):
            from sol_waveguide_channel_state import compare_waveguide_channel_states
            match_ch = compare_waveguide_channel_states(ch_state, case["expected_final_channel_snapshot"])
            if not match_ch:
                success = False
                err_msg = "Final channel state snapshot mismatch"
                
        return {
            "case_id": case["case_id"],
            "success": success,
            "error_message": err_msg,
            "verdict": "passed" if success else "failed"
        }

    serial_results = run_waveguide_trace_replay_batch_serial(replay_cases, run_single_replay)
    
    parallel_used = False
    workers = 1
    if cfg.get("enable_offline_trace_replay_parallelism", False):
        workers = cfg.get("max_workers", 1)
        if workers > 1:
            parallel_used = True
            accel_results = run_waveguide_trace_replay_batch_accelerated(replay_cases, run_single_replay, max_workers=workers)
            eq = validate_waveguide_acceleration_equivalence(serial_results, accel_results)
            if not eq:
                raise ValueError("Serial and Accelerated trace replay results are not equivalent!")
            results = accel_results
        else:
            results = serial_results
    else:
        results = serial_results
        
    if cfg.get("deterministic_result_ordering", True):
        results.sort(key=lambda x: x["case_id"])
        
    accel_report = summarize_waveguide_acceleration_report(cfg, "offline_trace_replay_batch")
    
    return {
        "success": all(r["success"] for r in results),
        "results": results,
        "acceleration_metadata": accel_report
    }

def validate_waveguide_cost_model_metadata(
    step: Any,
    pass_manager_report: Optional[Dict[str, Any]]
) -> Tuple[bool, str]:
    """
    Validates cost model trace metadata and report consistency.
    """
    meta = getattr(step, "cost_model_metadata", None)
    
    # If the pass manager report has cost_model_report enabled, then cost_model_metadata MUST be present in the trace step
    has_report = False
    if pass_manager_report and "cost_model_report" in pass_manager_report:
        has_report = pass_manager_report["cost_model_report"].get("enabled", False)
        
    if has_report and meta is None:
        return False, "cost_model_metadata is missing from step but cost model was enabled in pass manager report"
        
    if meta is None:
        return True, ""
        
    if not isinstance(meta, dict):
        return False, "cost_model_metadata is not a dictionary"
        
    required_keys = {"enabled", "cost_model_config", "candidates"}
    missing = required_keys - set(meta.keys())
    if missing:
        return False, f"Missing required cost model metadata keys: {missing}"
        
    candidates = meta["candidates"]
    if not isinstance(candidates, list) or len(candidates) != 8:
        return False, f"Expected 8 candidate forms in cost model metadata, got {len(candidates) if isinstance(candidates, list) else type(candidates)}"
        
    selected_candidates = [c for c in candidates if c.get("selected", False)]
    if len(selected_candidates) != 1:
        return False, f"Expected exactly 1 selected candidate in cost model metadata, got {len(selected_candidates)}"
        
    from sol_waveguide_kernel_cost_model import compare_waveguide_execution_forms
    try:
        compare_waveguide_execution_forms(candidates)
    except Exception as e:
        return False, f"Cost ordering comparison check failed: {e}"
        
    return True, ""

def validate_waveguide_autotuning_metadata(
    step: Any,
    pass_manager_report: Optional[Dict[str, Any]]
) -> Tuple[bool, str]:
    """
    Validates autotuning trace metadata and policy decision consistency.
    """
    meta = getattr(step, "autotuning_metadata", None)
    
    # If the pass manager report has autotuning_metadata enabled, then autotuning_metadata MUST be present in the trace step
    has_report = False
    if pass_manager_report and "autotuning_metadata" in pass_manager_report:
        has_report = pass_manager_report["autotuning_metadata"].get("enabled", False)
        
    if has_report and meta is None:
        return False, "autotuning_metadata is missing from step but autotuning was enabled in pass manager report"
        
    if not has_report:
        if meta is not None and meta.get("enabled", False):
            return False, "Disabled autotuning emitted active selection metadata in step"
            
    if meta is None:
        return True, ""
        
    if not isinstance(meta, dict):
        return False, "autotuning_metadata is not a dictionary"
        
    required_keys = {"enabled", "policy_name", "selected_form_id", "explanation"}
    missing = required_keys - set(meta.keys())
    if missing:
        return False, f"Missing required autotuning metadata keys: {missing}"
        
    if meta["enabled"]:
        policy = meta["policy_name"]
        from sol_waveguide_autotuning_policy import VALID_POLICIES
        if policy not in VALID_POLICIES:
            return False, f"Invalid policy name: '{policy}'"
            
        selected_form = meta["selected_form_id"]
        cost_meta = getattr(step, "cost_model_metadata", None)
        if cost_meta:
            candidates = cost_meta["candidates"]
            selected_c = next((c for c in candidates if c["form_id"] == selected_form), None)
            if selected_c is None:
                return False, f"Selected form ID '{selected_form}' not found in candidate list"
            if not selected_c.get("safe", True) or selected_c.get("cost", {}).get("unsupported_penalty", 0) > 0:
                return False, f"Unsafe or unsupported form '{selected_form}' was selected under policy '{policy}'"
                
    return True, ""
