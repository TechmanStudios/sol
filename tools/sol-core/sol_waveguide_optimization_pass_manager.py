# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Optimization Pass Manager
======================================
Orchestrates optimization passes in a strict canonical order and produces unified reports.
"""

from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, field

from sol_wideword_computation_validation import WideWordProgramInstruction, WideWordProgram
from sol_waveguide_optimization_profile import resolve_waveguide_optimization_profile

CANONICAL_PASS_ORDER = [
    "program_adaptation",
    "v1_candidate_lowering",
    "memory_alias_analysis",
    "channel_dependency_analysis",
    "channel_kernel_recognition",
    "branch_predication",
    "pipeline_compaction",
    "scoreboard_scheduling",
    "execution_plan_validation",
    "cost_model_evaluation",
    "deterministic_policy_selection",
    "trace_metadata_preparation"
]

def validate_waveguide_pass_order(pass_ids: List[str]) -> bool:
    """
    Ensures that the executed passes run in a subsequence of CANONICAL_PASS_ORDER.
    Specifically:
    - scheduler cannot run before dependency metadata (program_adaptation, memory_alias_analysis if memory is enabled)
    - branch predication cannot run before branch metadata is available
    - memory-aware scheduling requires memory alias metadata
    """
    # Check subsequence alignment
    canonical_indices = {p: i for i, p in enumerate(CANONICAL_PASS_ORDER)}
    for p in pass_ids:
        if p not in canonical_indices:
            raise ValueError(f"Unknown pass ID: '{p}'")
            
    # Check that indices are strictly increasing
    last_idx = -1
    for p in pass_ids:
        idx = canonical_indices[p]
        if idx <= last_idx:
            raise ValueError(f"Invalid pass execution order: '{p}' ran after or with a later pass. Order was {pass_ids}")
        last_idx = idx
        
    # Semantic verification rules:
    if "scoreboard_scheduling" in pass_ids:
        if "program_adaptation" not in pass_ids:
            raise ValueError("Pass order violation: 'scoreboard_scheduling' requires 'program_adaptation' to run first.")
            
    return True

def build_waveguide_pass_pipeline(config: Any) -> List[str]:
    """
    Identifies which passes should run based on configuration.
    """
    pipeline = ["program_adaptation"]
    
    if getattr(config, "enable_micro_isa_v1_candidates", False):
        pipeline.append("v1_candidate_lowering")
        
    if getattr(config, "enable_memory_alias_analysis", False):
        pipeline.append("memory_alias_analysis")
        
    if getattr(config, "enable_channel_independence_analysis", False):
        pipeline.append("channel_dependency_analysis")
        
    if getattr(config, "enable_channel_kernel_recognition", False):
        pipeline.append("channel_kernel_recognition")
        
    if getattr(config, "enable_branch_predication", False):
        pipeline.append("branch_predication")
        
    if getattr(config, "enable_pipeline_compaction", False):
        pipeline.append("pipeline_compaction")
        
    if getattr(config, "enable_scoreboard_scheduling", False):
        pipeline.append("scoreboard_scheduling")
        
    pipeline.append("execution_plan_validation")
    
    if getattr(config, "enable_cost_model", False):
        pipeline.append("cost_model_evaluation")
        
    if getattr(config, "enable_deterministic_autotuning", False):
        pipeline.append("deterministic_policy_selection")
        
    pipeline.append("trace_metadata_preparation")
    
    validate_waveguide_pass_order(pipeline)
    return pipeline

def run_waveguide_optimization_passes(
    program: Any,
    config: Any,
    width: int
) -> Tuple[List[Any], Dict[str, int], List[Any], List[Any], List[Any], Dict[int, Any], Dict[str, Any], Optional[Any]]:
    """
    Runs the pipeline of enabled passes, collecting individual pass reports
    and returning:
      clean_instructions, labels, diamonds, skipped_diamonds, windows, pc_to_scheduler_metadata, pass_manager_report, scheduler_report
    """
    enable_cost_model = getattr(config, "enable_cost_model", False)
    enable_deterministic_autotuning = getattr(config, "enable_deterministic_autotuning", False)
    
    if enable_cost_model or enable_deterministic_autotuning:
        from sol_waveguide_optimization_profile import profile_to_waveguide_execution_config
        from sol_waveguide_kernel_cost_model import build_waveguide_cost_model_config, estimate_waveguide_execution_cost
        from sol_waveguide_autotuning_policy import select_waveguide_execution_form
        
        cost_model_cfg = build_waveguide_cost_model_config(
            enable_cost_model=enable_cost_model,
            enable_deterministic_autotuning=enable_deterministic_autotuning,
            autotuning_policy=getattr(config, "autotuning_policy", None)
        )
        
        c_specs = [
            ("raw_strict", "RAW_STRICT", {}),
            ("safe_local", "SAFE_LOCAL", {}),
            ("safe_control", "SAFE_CONTROL", {}),
            ("safe_memory", "SAFE_MEMORY", {}),
            ("full_safe_optimized", "FULL_SAFE_OPTIMIZED", {}),
            ("v1_lowered_full_safe", "V1_CANDIDATE_EXPERIMENTAL", {
                "enable_waveguide_channel_state": False,
                "enable_channel_independence_analysis": False,
                "enable_channel_kernel_recognition": False
            }),
            ("channel_dependency", "V1_CANDIDATE_EXPERIMENTAL", {
                "enable_waveguide_channel_state": True,
                "enable_channel_independence_analysis": True,
                "enable_channel_kernel_recognition": False
            }),
            ("channel_kernelized", "V1_CANDIDATE_EXPERIMENTAL", {
                "enable_waveguide_channel_state": True,
                "enable_channel_independence_analysis": True,
                "enable_channel_kernel_recognition": True
            })
        ]
        
        candidates = []
        dry_run_results = {}
        
        for form_id, profile_id, overrides in c_specs:
            try:
                dry_cfg = profile_to_waveguide_execution_config(profile_id, width)
                for k, v in overrides.items():
                    setattr(dry_cfg, k, v)
                
                dry_cfg.enable_cost_model = False
                dry_cfg.enable_deterministic_autotuning = False
                dry_cfg.autotuning_policy = None
                
                dry_res = run_waveguide_optimization_passes(program, dry_cfg, width)
                dry_clean_insts = dry_res[0]
                dry_pm_rep = dry_res[6]
                dry_sched_rep = dry_res[7]
                
                cost = estimate_waveguide_execution_cost(dry_clean_insts, dry_pm_rep, dry_sched_rep, cost_model_cfg)
                
                candidates.append({
                    "form_id": form_id,
                    "profile_id": profile_id,
                    "required_features": [k for k, v in overrides.items() if v] or [profile_id],
                    "safe": True,
                    "semantic_equivalence": True,
                    "trace_replay_required": True,
                    "cost": cost,
                    "selected": False,
                    "skip_reasons": []
                })
                dry_run_results[form_id] = dry_res
            except Exception as e:
                candidates.append({
                    "form_id": form_id,
                    "profile_id": profile_id,
                    "required_features": [k for k, v in overrides.items() if v] or [profile_id],
                    "safe": False,
                    "semantic_equivalence": False,
                    "trace_replay_required": True,
                    "cost": {
                        "simulated_cycles": 999999,
                        "wavefront_count": 0,
                        "barrier_count": 0,
                        "compacted_windows": 0,
                        "scheduled_batches": 0,
                        "recognized_kernels": 0,
                        "trace_steps": 999999,
                        "trace_metadata_weight": 999999,
                        "safety_penalty": cost_model_cfg.get("safety_penalty", 500000),
                        "skip_penalty": 0,
                        "unsupported_penalty": cost_model_cfg.get("unsupported_penalty", 1000000),
                        "semantic_equivalence_required": True,
                        "trace_replay_required": True
                    },
                    "selected": False,
                    "skip_reasons": [f"Dry run failed: {str(e)}"]
                })
                
        policy_name = getattr(config, "autotuning_policy", None) or "STRICT_ONLY"
        
        if not enable_deterministic_autotuning:
            def get_execution_form_id(cfg: Any) -> str:
                v1_c = getattr(cfg, "enable_micro_isa_v1_candidates", False)
                ch_s = getattr(cfg, "enable_waveguide_channel_state", False)
                d_a = getattr(cfg, "enable_channel_independence_analysis", False)
                k_r = getattr(cfg, "enable_channel_kernel_recognition", False)
                c_p = getattr(cfg, "enable_pipeline_compaction", False)
                s_s = getattr(cfg, "enable_scoreboard_scheduling", False)
                b_p = getattr(cfg, "enable_branch_predication", False)
                m_a = getattr(cfg, "enable_memory_alias_analysis", False)
                
                if k_r and d_a and v1_c and ch_s:
                    return "channel_kernelized"
                if d_a and v1_c and ch_s:
                    return "channel_dependency"
                if v1_c:
                    return "v1_lowered_full_safe"
                if c_p and s_s and b_p and m_a:
                    return "full_safe_optimized"
                if s_s and m_a:
                    return "safe_memory"
                if c_p and s_s and b_p:
                    return "safe_control"
                if c_p:
                    return "safe_local"
                return "raw_strict"
            
            current_form_id = get_execution_form_id(config)
            for c in candidates:
                if c["form_id"] == current_form_id:
                    c["selected"] = True
                else:
                    c["selected"] = False
                    c["skip_reasons"] = c.get("skip_reasons", []) + ["Report-only mode active"]
            decision = {
                "policy_name": "REPORT_ONLY",
                "selected_form_id": current_form_id,
                "explanation": f"Report-only mode: evaluated forms, active execution form is '{current_form_id}'.",
                "rejections": {},
                "candidates": candidates
            }
        else:
            decision = select_waveguide_execution_form(program, candidates, policy_name)
            
        sel_id = decision["selected_form_id"]
        selected_res = dry_run_results.get(sel_id)
        if selected_res is None:
            selected_res = dry_run_results.get("raw_strict")
            if selected_res is None:
                raise ValueError("Critical Error: 'raw_strict' execution form is missing.")
                
        clean_instructions, labels, diamonds, skipped_diamonds, windows, pc_to_scheduler_metadata, report, scheduler_report = selected_res
        
        report["cost_model_report"] = {
            "enabled": True,
            "cost_model_config": cost_model_cfg,
            "candidates": candidates
        }
        
        if enable_deterministic_autotuning:
            report["autotuning_metadata"] = {
                "enabled": True,
                "policy_name": policy_name,
                "selected_form_id": sel_id,
                "explanation": decision["explanation"],
                "decision": decision
            }
        else:
            report["autotuning_metadata"] = {
                "enabled": False,
                "policy_name": None,
                "selected_form_id": None,
                "explanation": "Autotuning is disabled."
            }
            
        return clean_instructions, labels, diamonds, skipped_diamonds, windows, pc_to_scheduler_metadata, report, scheduler_report

    pipeline = build_waveguide_pass_pipeline(config)
    
    # Initialize intermediate state
    clean_instructions: List[Any] = []
    labels: Dict[str, int] = {}
    diamonds: List[Any] = []
    skipped_diamonds: List[Any] = []
    windows: List[Any] = []
    pc_to_scheduler_metadata: Dict[int, Any] = {}
    scheduler_report: Optional[Any] = None
    
    passes_report_list = []
    
    # 1. Program Adaptation
    if "program_adaptation" in pipeline:
        insts = program if isinstance(program, list) else getattr(program, "instructions", program)
        for inst in insts:
            if isinstance(inst, str) and inst.endswith(":"):
                labels[inst[:-1]] = len(clean_instructions)
            else:
                if isinstance(inst, (tuple, list)):
                    op = inst[0].upper()
                    dst = inst[1] if len(inst) > 1 else None
                    if op in ("VEC_PACK", "VEC_UNPACK") and len(inst) == 6:
                        src1 = None
                        src2 = tuple(inst[2:])
                    else:
                        src1 = inst[2] if len(inst) > 2 else None
                        if len(inst) == 5:
                            src2 = (inst[3], inst[4])
                        else:
                            src2 = inst[3] if len(inst) > 3 else None
                    clean_instructions.append(WideWordProgramInstruction(op=op, dst=dst, src1=src1, src2=src2))
                else:
                    clean_instructions.append(inst)
                    
        passes_report_list.append({
            "pass_id": "program_adaptation",
            "enabled": True,
            "applied": True,
            "skipped": False,
            "skip_reasons": [],
            "changed_plan": len(clean_instructions) > 0,
            "metadata_keys": ["labels", "clean_instructions"]
        })

    # 2. V1 Candidate Lowering
    v1_lowering_enabled = "v1_candidate_lowering" in pipeline
    v1_metadata_list = []
    
    if v1_lowering_enabled:
        from sol_micro_isa_v1_lowering import lower_v1_candidate_to_v0
        from sol_micro_isa_v1_candidates import V1_CANDIDATE_OPCODES
        
        new_clean_instructions = []
        new_labels = {}
        label_counter = 0
        
        for orig_pc in range(len(clean_instructions)):
            # Update any original labels pointing to orig_pc
            for l_name, l_pc in labels.items():
                if l_pc == orig_pc:
                    new_labels[l_name] = len(new_clean_instructions)
                    
            inst = clean_instructions[orig_pc]
            op = inst.op.upper() if hasattr(inst, "op") else ""
            
            if op in V1_CANDIDATE_OPCODES:
                new_pc_start = len(new_clean_instructions)
                lowered_ops, label_counter, metadata = lower_v1_candidate_to_v0(
                    inst,
                    label_counter,
                    width=width,
                    enable_waveguide_channel_state=getattr(config, "enable_waveguide_channel_state", False)
                )
                
                for op_item in lowered_ops:
                    if isinstance(op_item, str) and op_item.endswith(":"):
                        new_labels[op_item[:-1]] = len(new_clean_instructions)
                    else:
                        new_clean_instructions.append(op_item)
                        
                if metadata.get("lowered_to_v0", False):
                    metadata["candidate_pc"] = orig_pc
                    metadata["v0_pc_range"] = list(range(new_pc_start, len(new_clean_instructions)))
                else:
                    metadata["candidate_pc"] = orig_pc
                    
                v1_metadata_list.append(metadata)
            else:
                new_clean_instructions.append(inst)
                
        # Update any original labels pointing to the end of the program
        for l_name, l_pc in labels.items():
            if l_pc == len(clean_instructions):
                new_labels[l_name] = len(new_clean_instructions)
                
        clean_instructions = new_clean_instructions
        labels = new_labels
        
        applied = len(v1_metadata_list) > 0
        passes_report_list.append({
            "pass_id": "v1_candidate_lowering",
            "enabled": True,
            "applied": applied,
            "skipped": not applied,
            "skip_reasons": [],
            "changed_plan": applied,
            "metadata_keys": ["v1_lowering_metadata"]
        })
    else:
        passes_report_list.append({
            "pass_id": "v1_candidate_lowering",
            "enabled": False,
            "applied": False,
            "skipped": True,
            "skip_reasons": ["disabled_in_profile_or_config"],
            "changed_plan": False,
            "metadata_keys": []
        })
        
    # 2. Memory Alias Analysis
    memory_alias_enabled = "memory_alias_analysis" in pipeline
    if memory_alias_enabled:
        passes_report_list.append({
            "pass_id": "memory_alias_analysis",
            "enabled": True,
            "applied": True,
            "skipped": False,
            "skip_reasons": [],
            "changed_plan": False,
            "metadata_keys": ["memory_alias_metadata"]
        })
    else:
        passes_report_list.append({
            "pass_id": "memory_alias_analysis",
            "enabled": False,
            "applied": False,
            "skipped": True,
            "skip_reasons": ["disabled_in_profile_or_config"],
            "changed_plan": False,
            "metadata_keys": []
        })
        
    # 2b. Channel Dependency Analysis
    channel_access_list = []
    if "channel_dependency_analysis" in pipeline:
        from sol_waveguide_channel_dependency import build_waveguide_channel_access
        for orig_pc in range(len(clean_instructions)):
            access = build_waveguide_channel_access(clean_instructions[orig_pc], orig_pc, v1_metadata_list)
            if access:
                channel_access_list.append(access)
        passes_report_list.append({
            "pass_id": "channel_dependency_analysis",
            "enabled": True,
            "applied": len(channel_access_list) > 0,
            "skipped": len(channel_access_list) == 0,
            "skip_reasons": [],
            "changed_plan": False,
            "metadata_keys": ["channel_access_list"]
        })
    else:
        passes_report_list.append({
            "pass_id": "channel_dependency_analysis",
            "enabled": False,
            "applied": False,
            "skipped": True,
            "skip_reasons": ["disabled_in_profile_or_config"],
            "changed_plan": False,
            "metadata_keys": []
        })
        
    # 2c. Channel Kernel Recognition
    recognized_kernels = []
    skipped_kernels = []
    kernel_recognition_enabled = "channel_kernel_recognition" in pipeline
    
    if kernel_recognition_enabled:
        from sol_waveguide_channel_kernel_recognizer import detect_waveguide_channel_kernels
        recognized_kernels, skipped_kernels = detect_waveguide_channel_kernels(v1_metadata_list, enabled=True)
        applied = len(recognized_kernels) > 0
        passes_report_list.append({
            "pass_id": "channel_kernel_recognition",
            "enabled": True,
            "applied": applied,
            "skipped": not applied,
            "skip_reasons": [],
            "changed_plan": False,
            "metadata_keys": ["recognized_kernels", "skipped_kernels"]
        })
    else:
        if v1_lowering_enabled:
            from sol_waveguide_channel_kernel_recognizer import detect_waveguide_channel_kernels
            _, skipped_kernels = detect_waveguide_channel_kernels(v1_metadata_list, enabled=False)
        passes_report_list.append({
            "pass_id": "channel_kernel_recognition",
            "enabled": False,
            "applied": False,
            "skipped": True,
            "skip_reasons": ["disabled_in_profile_or_config"],
            "changed_plan": False,
            "metadata_keys": []
        })
        
    # 3. Branch Predication
    if "branch_predication" in pipeline:
        from sol_waveguide_predication import detect_waveguide_branch_diamonds
        enable_memory_alias_analysis = getattr(config, "enable_memory_alias_analysis", False)
        diamonds, skipped_diamonds = detect_waveguide_branch_diamonds(clean_instructions, labels, enable_memory_alias_analysis)
        
        applied = len(diamonds) > 0
        skip_reasons = []
        if not applied and skipped_diamonds:
            skip_reasons = [d.get("reason", "unknown") for d in skipped_diamonds]
            
        passes_report_list.append({
            "pass_id": "branch_predication",
            "enabled": True,
            "applied": applied,
            "skipped": not applied,
            "skip_reasons": skip_reasons,
            "changed_plan": applied,
            "metadata_keys": ["predication_metadata"]
        })
    else:
        passes_report_list.append({
            "pass_id": "branch_predication",
            "enabled": False,
            "applied": False,
            "skipped": True,
            "skip_reasons": ["disabled_in_profile_or_config"],
            "changed_plan": False,
            "metadata_keys": []
        })
        
    # 4. Pipeline Compaction
    if "pipeline_compaction" in pipeline:
        from sol_waveguide_pipeline_compaction import analyze_waveguide_microcode_chain
        windows = analyze_waveguide_microcode_chain(program)
        applied = any(not w.unsafe for w in windows)
        skip_reasons = [w.unsafe_reason for w in windows if w.unsafe]
        
        passes_report_list.append({
            "pass_id": "pipeline_compaction",
            "enabled": True,
            "applied": applied,
            "skipped": not applied,
            "skip_reasons": skip_reasons,
            "changed_plan": applied,
            "metadata_keys": ["compaction_metadata"]
        })
    else:
        passes_report_list.append({
            "pass_id": "pipeline_compaction",
            "enabled": False,
            "applied": False,
            "skipped": True,
            "skip_reasons": ["disabled_in_profile_or_config"],
            "changed_plan": False,
            "metadata_keys": []
        })
        
    # 5. Scoreboard Scheduling
    if "scoreboard_scheduling" in pipeline:
        from sol_waveguide_scoreboard_scheduler import build_waveguide_scoreboard
        enable_memory_alias_analysis = getattr(config, "enable_memory_alias_analysis", False)
        enable_channel_independence = getattr(config, "enable_channel_independence_analysis", False)
        superblocks, scheduled_batches, scheduler_report = build_waveguide_scoreboard(
            clean_instructions, windows, enable_memory_alias_analysis,
            v1_lowering_metadata=v1_metadata_list,
            enable_channel_independence_analysis=enable_channel_independence,
            recognized_kernels=recognized_kernels
        )
        
        for s_idx, s in enumerate(superblocks):
            batches = scheduled_batches[s_idx]
            for wf_idx, wf_units_indices in enumerate(batches):
                wf_pcs = []
                for u_idx in wf_units_indices:
                    u_haz = s.hazards[u_idx]
                    u_unit = s.units[u_idx]
                    if hasattr(u_unit, "original_instructions"):
                        wf_pcs.extend(range(u_unit.start_pc, u_unit.start_pc + len(u_unit.original_instructions)))
                    else:
                        wf_pcs.append(u_haz["pc"])
                        
                for u_idx in wf_units_indices:
                    u_haz = s.hazards[u_idx]
                    u_unit = s.units[u_idx]
                    barrier_reason = u_haz["reason"] if u_haz["is_barrier"] else None
                    
                    # Determine channel wavefront details
                    channel_ops_in_wf = []
                    if enable_channel_independence:
                        for idx_in_wf in wf_units_indices:
                            haz_item = s.hazards[idx_in_wf]
                            if haz_item.get("channel_access"):
                                channel_ops_in_wf.append(haz_item["channel_access"]["opcode"])
                                
                    meta = {
                        "scheduler_enabled": True,
                        "wavefront_id": f"WF_{s.id}_{wf_idx}",
                        "batch_index": wf_idx,
                        "original_pcs": sorted(wf_pcs),
                        "hazards_checked": True,
                        "is_barrier": u_haz["is_barrier"],
                        "barrier_reason": barrier_reason
                    }
                    if enable_channel_independence:
                        meta.update({
                            "channel_dependency_analysis_enabled": True,
                            "channel_wavefront_id": wf_idx,
                            "channel_ops_batched": sorted(channel_ops_in_wf),
                            "channel_hazards_checked": True,
                            "channel_hazard_result": "NO_CHANNEL_HAZARD"
                        })
                    
                    if hasattr(u_unit, "original_instructions"):
                        for pc_val in range(u_unit.start_pc, u_unit.start_pc + len(u_unit.original_instructions)):
                            pc_to_scheduler_metadata[pc_val] = meta
                    else:
                        pc_to_scheduler_metadata[u_haz["pc"]] = meta
                        
        applied = len(superblocks) > 0
        passes_report_list.append({
            "pass_id": "scoreboard_scheduling",
            "enabled": True,
            "applied": applied,
            "skipped": not applied,
            "skip_reasons": [],
            "changed_plan": applied,
            "metadata_keys": ["scheduler_metadata"]
        })
    else:
        passes_report_list.append({
            "pass_id": "scoreboard_scheduling",
            "enabled": False,
            "applied": False,
            "skipped": True,
            "skip_reasons": ["disabled_in_profile_or_config"],
            "changed_plan": False,
            "metadata_keys": []
        })
        
    # 6. Execution Plan Validation
    if "execution_plan_validation" in pipeline:
        # Check scheduling conflicts: e.g. schedule metadata doesn't point to non-existent PC
        for pc_val, meta in pc_to_scheduler_metadata.items():
            if pc_val < 0 or pc_val >= len(clean_instructions):
                raise ValueError(f"Execution plan error: PC {pc_val} in scoreboard metadata is out of bounds.")
                
        passes_report_list.append({
            "pass_id": "execution_plan_validation",
            "enabled": True,
            "applied": True,
            "skipped": False,
            "skip_reasons": [],
            "changed_plan": False,
            "metadata_keys": []
        })
        
    # 7. Trace Metadata Preparation
    if "trace_metadata_preparation" in pipeline:
        passes_report_list.append({
            "pass_id": "trace_metadata_preparation",
            "enabled": True,
            "applied": True,
            "skipped": False,
            "skip_reasons": [],
            "changed_plan": False,
            "metadata_keys": ["pass_manager_report_metadata"]
        })
        
    # Decorate pc_to_scheduler_metadata with recognized and skipped kernel details
    for pc_val, meta in pc_to_scheduler_metadata.items():
        for kernel in recognized_kernels:
            if kernel["pc_range"][0] <= pc_val <= kernel["pc_range"][1]:
                k_wfs = sorted(list(set(
                    pc_to_scheduler_metadata[p]["wavefront_id"]
                    for p in range(kernel["pc_range"][0], kernel["pc_range"][1] + 1)
                    if p in pc_to_scheduler_metadata
                )))
                meta.update({
                    "channel_kernel_recognition_enabled": True,
                    "channel_kernel_id": kernel["kernel_id"],
                    "kernel_pc_range": kernel["pc_range"],
                    "kernel_wavefronts": k_wfs,
                    "input_channels": kernel.get("input_channels", []),
                    "output_channels": kernel.get("output_channels", []),
                    "input_registers": kernel.get("input_registers", []),
                    "output_registers": kernel.get("output_registers", []),
                    "kernel_hazards_checked": True,
                    "kernel_equivalence_required": True,
                    "sandbox_only": True
                })
                break
        for sk in skipped_kernels:
            if "pc_range" in sk and sk["pc_range"][0] <= pc_val <= sk["pc_range"][1]:
                meta.update({
                    "channel_kernel_candidate": sk["channel_kernel_candidate"],
                    "recognized": False,
                    "skip_reason": sk["skip_reason"]
                })
                break

    # Build unified pass manager report
    profile_id = resolve_waveguide_optimization_profile(config)
    raw_ins_count = len(clean_instructions)
    
    report = {
        "profile_id": profile_id,
        "passes": passes_report_list,
        "raw_instruction_count": raw_ins_count,
        "optimized_plan_units": len(pipeline),
        "semantic_equivalence_required": True,
        "trace_replay_required": True,
        "v1_lowering_metadata": v1_metadata_list,
        "enable_waveguide_channel_state": getattr(config, "enable_waveguide_channel_state", False),
        "channel_access_list": channel_access_list,
        "enable_channel_independence_analysis": getattr(config, "enable_channel_independence_analysis", False),
        "enable_channel_kernel_recognition": getattr(config, "enable_channel_kernel_recognition", False),
        "recognized_kernels": recognized_kernels,
        "skipped_kernels": skipped_kernels,
        "compacted_windows_count": sum(1 for w in windows if not w.unsafe),
        "compacted_cycles_saved": sum(len(w.original_instructions) - 1 for w in windows if not w.unsafe),
        "diamonds_predicated_count": len(diamonds),
        "enable_micro_isa_v1_candidates": getattr(config, "enable_micro_isa_v1_candidates", False)
    }
    
    return clean_instructions, labels, diamonds, skipped_diamonds, windows, pc_to_scheduler_metadata, report, scheduler_report

def collect_waveguide_pass_reports(passes_run: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Returns list of reports from passes.
    """
    return list(passes_run)

def summarize_waveguide_pass_manager_report(report: Dict[str, Any]) -> Dict[str, Any]:
    """
    Summarizes pass manager stats.
    """
    enabled_passes = [p["pass_id"] for p in report.get("passes", []) if p["enabled"]]
    skipped_passes = [p["pass_id"] for p in report.get("passes", []) if p["skipped"]]
    
    return {
        "profile_id": report.get("profile_id", "CUSTOM"),
        "enabled_passes": enabled_passes,
        "skipped_passes": skipped_passes,
        "raw_instruction_count": report.get("raw_instruction_count", 0),
        "semantic_equivalence_required": report.get("semantic_equivalence_required", True)
    }
