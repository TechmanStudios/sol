# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Control-Memory Execution Bridge
=============================================
Integrates strict PDM/waveguide ALU operations, localized memory shards,
and program-counter branch gates into a unified execution context.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from sol_wideword_computation_validation import (
    WideWordProgramInstruction,
    WideWordProgram,
    mask_for_width
)
from sol_wideword_waveguide_program import (
    build_waveguide_program_adapter,
    execute_waveguide_instruction
)
from sol_waveguide_branch_control import (
    execute_waveguide_branch_instruction,
    WaveguideBranchTrace
)
from sol_waveguide_memory_shard import (
    WaveguideMemoryShard,
    build_waveguide_memory_shard,
    execute_waveguide_load,
    execute_waveguide_store,
    WaveguideMemoryRead,
    WaveguideMemoryWrite
)

@dataclass
class WaveguideControlMemoryBridgeConfig:
    width: int
    memory_slots: int = 65536
    enable_pipeline_compaction: bool = True
    enable_scoreboard_scheduling: bool = True
    enable_branch_predication: bool = True
    enable_memory_alias_analysis: bool = True
    optimization_profile: Optional[str] = None
    enable_micro_isa_v1_candidates: bool = False
    micro_isa_version: str = "v0"
    enable_waveguide_channel_state: bool = False
    waveguide_channel_count: int = 8
    waveguide_channel_width_bits: int = 32
    waveguide_channel_recv_empty_policy: str = "zero_with_empty_flag"
    waveguide_channel_clear_on_recv: bool = False
    enable_simulation_acceleration: bool = False
    enable_compact_trace_mode: bool = False
    enable_trace_metadata_template_cache: bool = True
    enable_offline_benchmark_parallelism: bool = False
    enable_offline_trace_replay_parallelism: bool = False
    max_workers: int = 1
    deterministic_result_ordering: bool = True
    worker_state_isolation: bool = True
    enable_channel_independence_analysis: bool = False
    enable_channel_kernel_recognition: bool = False
    enable_cost_model: bool = False
    enable_deterministic_autotuning: bool = False
    autotuning_policy: Optional[str] = None

    def __post_init__(self):
        if self.optimization_profile is not None:
            from sol_waveguide_optimization_profile import build_waveguide_optimization_profile
            flags = build_waveguide_optimization_profile(self.optimization_profile)
            if "enable_pipeline_compaction" in flags:
                self.enable_pipeline_compaction = flags["enable_pipeline_compaction"]
            if "enable_scoreboard_scheduling" in flags:
                self.enable_scoreboard_scheduling = flags["enable_scoreboard_scheduling"]
            if "enable_branch_predication" in flags:
                self.enable_branch_predication = flags["enable_branch_predication"]
            if "enable_memory_alias_analysis" in flags:
                self.enable_memory_alias_analysis = flags["enable_memory_alias_analysis"]
            if "enable_micro_isa_v1_candidates" in flags:
                self.enable_micro_isa_v1_candidates = flags["enable_micro_isa_v1_candidates"]
            if "enable_waveguide_channel_state" in flags:
                self.enable_waveguide_channel_state = flags["enable_waveguide_channel_state"]
            if "enable_simulation_acceleration" in flags:
                self.enable_simulation_acceleration = flags["enable_simulation_acceleration"]
            if "enable_compact_trace_mode" in flags:
                self.enable_compact_trace_mode = flags["enable_compact_trace_mode"]
            if "enable_trace_metadata_template_cache" in flags:
                self.enable_trace_metadata_template_cache = flags["enable_trace_metadata_template_cache"]
            if "enable_offline_benchmark_parallelism" in flags:
                self.enable_offline_benchmark_parallelism = flags["enable_offline_benchmark_parallelism"]
            if "enable_offline_trace_replay_parallelism" in flags:
                self.enable_offline_trace_replay_parallelism = flags["enable_offline_trace_replay_parallelism"]
            if "max_workers" in flags:
                self.max_workers = flags["max_workers"]
            if "deterministic_result_ordering" in flags:
                self.deterministic_result_ordering = flags["deterministic_result_ordering"]
            if "worker_state_isolation" in flags:
                self.worker_state_isolation = flags["worker_state_isolation"]
            if "enable_channel_independence_analysis" in flags:
                self.enable_channel_independence_analysis = flags["enable_channel_independence_analysis"]
            if "enable_channel_kernel_recognition" in flags:
                self.enable_channel_kernel_recognition = flags["enable_channel_kernel_recognition"]
            if "enable_cost_model" in flags:
                self.enable_cost_model = flags["enable_cost_model"]
            if "enable_deterministic_autotuning" in flags:
                self.enable_deterministic_autotuning = flags["enable_deterministic_autotuning"]
            if "autotuning_policy" in flags:
                self.autotuning_policy = flags["autotuning_policy"]
        if self.micro_isa_version == "v1":
            self.enable_micro_isa_v1_candidates = True
        if self.enable_channel_independence_analysis:
            if not self.enable_waveguide_channel_state:
                raise ValueError("enable_channel_independence_analysis requires enable_waveguide_channel_state=True")
            if not self.enable_micro_isa_v1_candidates:
                raise ValueError("enable_channel_independence_analysis requires enable_micro_isa_v1_candidates=True")
        if self.enable_channel_kernel_recognition:
            if not self.enable_waveguide_channel_state:
                raise ValueError("enable_channel_kernel_recognition requires enable_waveguide_channel_state=True")
            if not self.enable_micro_isa_v1_candidates:
                raise ValueError("enable_channel_kernel_recognition requires enable_micro_isa_v1_candidates=True")

@dataclass
class WaveguideControlMemoryState:
    width: int
    pc: int
    registers: Dict[str, int]
    memory: WaveguideMemoryShard
    flags: Dict[str, int]
    labels: Dict[str, int] = field(default_factory=dict)
    active_mutated: bool = False
    _cached_adapter: Optional[Any] = None
    channel_state: Optional[Dict[str, Any]] = None

@dataclass
class WaveguideControlMemoryInstructionTrace:
    step_index: int
    pc_before: int
    pc_after: int
    instruction: Any
    layer_used: str
    sol_result: int
    oracle_result: int
    sol_flags: Dict[str, int]
    oracle_flags: Dict[str, int]
    match: bool
    branch_trace: Optional[Any] = None
    memory_trace: Optional[Any] = None
    scheduler_metadata: Optional[Dict[str, Any]] = None
    waveguide_channel_metadata: Optional[Dict[str, Any]] = None
    simulation_acceleration_metadata: Optional[Dict[str, Any]] = None
    cost_model_metadata: Optional[Dict[str, Any]] = None
    autotuning_metadata: Optional[Dict[str, Any]] = None

@dataclass
class WaveguideControlMemoryProgramTrace:
    steps: List[WaveguideControlMemoryInstructionTrace] = field(default_factory=list)

@dataclass
class WaveguideControlMemoryExecutionReport:
    success: bool
    oracle_match: bool
    trace_steps: List[WaveguideControlMemoryInstructionTrace] = field(default_factory=list)
    mismatches: List[Dict[str, Any]] = field(default_factory=list)
    layers_used: Dict[str, int] = field(default_factory=dict)
    pipeline_compaction_report: Optional[Dict[str, Any]] = None
    scoreboard_scheduler_report: Optional[Dict[str, Any]] = None
    branch_predication_report: Optional[Dict[str, Any]] = None
    pass_manager_report: Optional[Dict[str, Any]] = None

def build_waveguide_control_memory_state(
    width: int,
    memory_slots: int = 65536,
    registers: Optional[Dict[str, int]] = None,
    config: Optional[WaveguideControlMemoryBridgeConfig] = None
) -> WaveguideControlMemoryState:
    if registers is None:
        registers = {f"R{i}": 0 for i in range(16)}
    memory = build_waveguide_memory_shard(width, slots=memory_slots)
    flags = {
        "zero": 0,
        "carry": 0,
        "overflow": 0,
        "sign": 0,
        "borrow": 0
    }
    state = WaveguideControlMemoryState(
        width=width,
        pc=0,
        registers=registers,
        memory=memory,
        flags=flags
    )
    if config and getattr(config, "enable_waveguide_channel_state", False):
        from sol_waveguide_channel_state import build_waveguide_channel_state
        state.channel_state = build_waveguide_channel_state(
            width_bits=getattr(config, "waveguide_channel_width_bits", 32),
            channel_count=getattr(config, "waveguide_channel_count", 8),
            recv_empty_policy=getattr(config, "waveguide_channel_recv_empty_policy", "zero_with_empty_flag"),
            clear_on_recv=getattr(config, "waveguide_channel_clear_on_recv", False)
        )
    return state

def execute_waveguide_control_memory_instruction(
    state: WaveguideControlMemoryState,
    instruction: Any
) -> tuple[int, str, Dict[str, int], Optional[Any], Optional[Any]]:
    width = state.width
    mask = mask_for_width(width)
    op = instruction.op.upper()
    
    layer_used = "unsupported_instruction"
    sol_result = 0
    sol_flags = dict(state.flags)
    branch_trace = None
    mem_trace = None
    
    # helper to resolve operands
    def resolve_val(operand: Any) -> int:
        if isinstance(operand, str) and operand.startswith("R"):
            return state.registers.get(operand, 0)
        if isinstance(operand, int):
            return operand & mask
        return 0

    is_alu = op in ("ADD", "SUB", "AND", "OR", "XOR", "NOT", "SHL", "SHR", "CMP")
    
    if is_alu:
        # Route ALU operations directly through the strict PDM/waveguide shadow logic
        if getattr(state, "_cached_adapter", None) is None:
            state._cached_adapter = build_waveguide_program_adapter(width, backend="pdm_waveguide_shadow")
        adapter = state._cached_adapter
        
        # We must populate adapter memory/registers/flags with the current state
        # Create standard memory dict from shard cells
        temp_mem = dict(state.memory.cells)
        
        try:
            res = execute_waveguide_instruction(adapter, instruction, state.registers, temp_mem, state.flags)
            sol_result = res.sol_result
            sol_flags = res.sol_flags
            layer_used = res.layer_used
            
            if op != "CMP":
                state.registers[instruction.dst] = sol_result
            
            # If the backend fell back to lane_fabric_vm under strict command, raise error
            if layer_used == "lane_fabric_vm":
                layer_used = "unsupported_instruction"
        except Exception:
            layer_used = "backend_error"
            
    elif op in ("JMP", "JZ", "JNZ", "JC", "JNC", "JB", "JNB"):
        # Route branch operations through waveguide_branch_control
        dec, b_trace = execute_waveguide_branch_instruction(instruction, state.pc, state.flags, state.labels)
        state.pc = dec.target_pc
        sol_result = 0
        layer_used = "waveguide_branch_control"
        branch_trace = b_trace
        
    elif op == "LOAD":
        addr = resolve_val(instruction.src1)
        try:
            val = execute_waveguide_load(state.memory, addr)
            sol_result = val
            state.registers[instruction.dst] = val
            layer_used = "waveguide_memory_shard"
            mem_trace = WaveguideMemoryRead(address=addr, value=val)
        except IndexError:
            layer_used = "unsupported_memory_op"
            
    elif op == "STORE":
        val = resolve_val(instruction.dst)
        addr = resolve_val(instruction.src1)
        try:
            execute_waveguide_store(state.memory, addr, val)
            sol_result = val
            layer_used = "waveguide_memory_shard"
            mem_trace = WaveguideMemoryWrite(address=addr, value=val)
        except IndexError:
            layer_used = "unsupported_memory_op"
            
    elif op == "MOV":
        val = resolve_val(instruction.src1)
        state.registers[instruction.dst] = val
        sol_result = val
        layer_used = "waveguide_register_transfer"
        
    elif op == "LOAD_IMM":
        val = resolve_val(instruction.src1)
        state.registers[instruction.dst] = val
        sol_result = val
        layer_used = "waveguide_register_init"
        
    elif op == "HALT":
        layer_used = "waveguide_control_stop"
        sol_result = 0
        
    return sol_result, layer_used, sol_flags, branch_trace, mem_trace

def execute_waveguide_control_memory_program(
    program: Any,
    state: WaveguideControlMemoryState,
    config: WaveguideControlMemoryBridgeConfig
) -> WaveguideControlMemoryExecutionReport:
    from sol_micro_isa_v1_spec import set_waveguide_channel_state_enabled
    set_waveguide_channel_state_enabled(config is not None and getattr(config, "enable_waveguide_channel_state", False))

    # Build clean instructions list and labels map using Pass Manager
    from sol_waveguide_optimization_pass_manager import run_waveguide_optimization_passes
    from sol_waveguide_pipeline_compaction import compact_waveguide_microcode_sequence

    insts = program if isinstance(program, list) else getattr(program, "instructions", program)
    clean_instructions, labels, diamonds, skipped_diamonds, windows, pc_to_scheduler_metadata, pass_manager_report, scheduler_report = run_waveguide_optimization_passes(
        program, config, state.width
    )
    
    state.labels = labels
    state.pc = 0
    
    if config and getattr(config, "enable_waveguide_channel_state", False) and state.channel_state is None:
        from sol_waveguide_channel_state import build_waveguide_channel_state
        state.channel_state = build_waveguide_channel_state(
            width_bits=getattr(config, "waveguide_channel_width_bits", 32),
            channel_count=getattr(config, "waveguide_channel_count", 8),
            recv_empty_policy=getattr(config, "waveguide_channel_recv_empty_policy", "zero_with_empty_flag"),
            clear_on_recv=getattr(config, "waveguide_channel_clear_on_recv", False)
        )
        
    pc_to_v1_mapping = {}
    if config and getattr(config, "enable_micro_isa_v1_candidates", False):
        v1_metadata = pass_manager_report.get("v1_lowering_metadata", []) if pass_manager_report else []
        for m in v1_metadata:
            if m.get("lowered_to_v0", False):
                pcs = m.get("v0_pc_range", [])
                if pcs:
                    pc_to_v1_mapping[pcs[0]] = m.get("original_instruction_obj")

    trace_steps = []
    mismatches = []
    layers_used = {}
    
    max_cycles = 2000
    cycles = 0
    success = True
    oracle_match = True
    
    compaction_enabled = getattr(config, "enable_pipeline_compaction", True)
    predication_enabled = getattr(config, "enable_branch_predication", True)
    scoreboard_enabled = getattr(config, "enable_scoreboard_scheduling", True)
    enable_memory_alias_analysis = getattr(config, "enable_memory_alias_analysis", True)
    attach_scheduler_metadata = scoreboard_enabled or getattr(config, "enable_channel_kernel_recognition", False)
    
    pc_to_diamond = {}
    if predication_enabled:
        for d in diamonds:
            pc_to_diamond[d.cond_pc] = d
            
    diamonds_predicated_count = 0
    total_pred_original_cycles = 0
    total_pred_cycles = 0

    windows_compacted_count = 0
    unsafe_skipped = []
    total_original_cycles = 0
    total_compacted_cycles = 0
    
    for w in windows:
        if w.unsafe:
            unsafe_skipped.append({
                "start_pc": w.start_pc,
                "end_pc": w.end_pc,
                "reason": w.unsafe_reason
            })

    # We run a reference python oracle to match state
    import copy
    from sol_wideword_computation_validation import OracleWideWordVM
    oracle_channel_state = copy.deepcopy(state.channel_state) if state.channel_state is not None else None
    oracle_vm = OracleWideWordVM(width=state.width, channel_state=oracle_channel_state)
    # Convert program instructions to WideWordProgramInstruction format for oracle
    oracle_prog = WideWordProgram(program_id="ORACLE_TEMP", instructions=clean_instructions)
    
    oracle_traces = []
    v1_metadata_list = pass_manager_report.get("v1_lowering_metadata", []) if pass_manager_report else []
    try:
        if getattr(config, "enable_micro_isa_v1_candidates", False):
            # Reconstruct instruction list with label strings for the Oracle VM
            oracle_program = []
            pc_to_labels = {}
            for name, target_pc in labels.items():
                if target_pc not in pc_to_labels:
                    pc_to_labels[target_pc] = []
                pc_to_labels[target_pc].append(f"{name}:")
                
            for pc_idx in range(len(clean_instructions) + 1):
                if pc_idx in pc_to_labels:
                    for lbl in pc_to_labels[pc_idx]:
                        oracle_program.append(lbl)
                if pc_idx < len(clean_instructions):
                    oracle_program.append(clean_instructions[pc_idx])
            oracle_report = oracle_vm.run_program(oracle_program, v1_lowering_metadata=v1_metadata_list)
        else:
            oracle_report = oracle_vm.run_program(insts)
        oracle_traces = getattr(oracle_vm, "trace_steps", [])
    except Exception as e:
        if isinstance(e, TimeoutError) or "TimeoutError" in type(e).__name__:
            raise
        oracle_report = None
        oracle_traces = []
    
    # Track cycles in compaction vs scheduled batches
    scheduled_cycles = 0
    executed_batches = set()
    
    while state.pc < len(clean_instructions) and cycles < max_cycles:
        # Check if we are at the start of a predicated diamond
        active_diamond = pc_to_diamond.get(state.pc) if predication_enabled else None
        if active_diamond:
            from sol_waveguide_predication import execute_waveguide_predicated_diamond
            success_dia, orig_c, pred_c = execute_waveguide_predicated_diamond(
                active_diamond,
                state,
                config,
                oracle_traces,
                clean_instructions,
                trace_steps,
                mismatches
            )
            diamonds_predicated_count += 1
            total_pred_original_cycles += orig_c
            total_pred_cycles += pred_c
            cycles += orig_c
            scheduled_cycles += pred_c
            
            # Map layers_used counts from the new steps appended
            new_steps = trace_steps[len(trace_steps) - orig_c:]
            for step in new_steps:
                layers_used[step.layer_used] = layers_used.get(step.layer_used, 0) + 1
                
            if not success_dia:
                success = False
                oracle_match = False
                break
            continue
        # Check if we are at the start of a safe compacted window
        active_window = None
        if compaction_enabled:
            for w in windows:
                if not w.unsafe and w.start_pc == state.pc:
                    active_window = w
                    break
                    
        if active_window:
            comp_success, orig_c, comp_c = compact_waveguide_microcode_sequence(
                active_window,
                state,
                config,
                oracle_traces,
                clean_instructions,
                trace_steps,
                mismatches
            )
            windows_compacted_count += 1
            total_original_cycles += orig_c
            total_compacted_cycles += comp_c
            cycles += orig_c
            
            # Map scheduler wavefront for compaction window
            meta = pc_to_scheduler_metadata.get(active_window.start_pc) if attach_scheduler_metadata else None
            if meta and "wavefront_id" in meta:
                wf_key = (meta["wavefront_id"], meta["batch_index"])
                executed_batches.add(wf_key)
            scheduled_cycles += comp_c
            
            # Update layers_used counts from the new steps appended, and attach scheduler metadata
            new_steps = trace_steps[len(trace_steps) - orig_c:]
            for step in new_steps:
                layers_used[step.layer_used] = layers_used.get(step.layer_used, 0) + 1
                if attach_scheduler_metadata:
                    step.scheduler_metadata = pc_to_scheduler_metadata.get(step.pc_before)
                if config and getattr(config, "enable_cost_model", False):
                    step.cost_model_metadata = pass_manager_report.get("cost_model_report")
                if config and getattr(config, "enable_deterministic_autotuning", False):
                    step.autotuning_metadata = pass_manager_report.get("autotuning_metadata")
                
            if not comp_success:
                success = False
                oracle_match = False
                break
            continue
            
        inst = clean_instructions[state.pc]
        pc_before = state.pc
        op = inst.op.upper()
        
        # Run step on oracle VM trace
        expected_res = 0
        expected_flags = dict(state.flags)
        
        if cycles < len(oracle_traces):
            oracle_step = oracle_traces[cycles]
            expected_res = getattr(oracle_step, "oracle_result", 0)
            expected_flags = dict(getattr(oracle_step, "oracle_flags", {}))
            
        mask = mask_for_width(state.width)
        channel_meta = None
        if state.channel_state is not None and pc_before in pc_to_v1_mapping:
            v1_inst = pc_to_v1_mapping[pc_before]
            v1_op = v1_inst.op.upper()
            if v1_op == "WG_CHAN_SEND":
                from sol_waveguide_channel_state import execute_waveguide_channel_send, resolve_channel_id, resolve_operand_val
                ch_id = resolve_channel_id(v1_inst.dst, state.registers)
                val = resolve_operand_val(v1_inst.src1, state.registers, mask)
                channel_meta = execute_waveguide_channel_send(state.channel_state, ch_id, val)
            elif v1_op == "WG_CHAN_RECV":
                from sol_waveguide_channel_state import execute_waveguide_channel_recv, resolve_channel_id
                ch_id = resolve_channel_id(v1_inst.src1, state.registers)
                val, channel_meta = execute_waveguide_channel_recv(state.channel_state, ch_id)
                state.registers[v1_inst.dst] = val
            elif v1_op == "WG_CHAN_ROUTE":
                from sol_waveguide_channel_state import execute_waveguide_channel_route, resolve_channel_id, resolve_operand_val
                dst_ch = resolve_channel_id(v1_inst.dst, state.registers)
                src_ch = resolve_channel_id(v1_inst.src1, state.registers)
                r_mask = resolve_operand_val(v1_inst.src2, state.registers, mask)
                channel_meta = execute_waveguide_channel_route(state.channel_state, dst_ch, src_ch, r_mask)
            elif v1_op == "WG_CHAN_FENCE":
                from sol_waveguide_channel_state import execute_waveguide_channel_fence
                channel_meta = execute_waveguide_channel_fence(state.channel_state)

        sol_result, layer_used, sol_flags, branch_trace, mem_trace = execute_waveguide_control_memory_instruction(state, inst)
        
        # update state flags
        state.flags.update(sol_flags)
        
        # Increment PC if not jump instruction
        if op not in ("JMP", "JZ", "JNZ", "JC", "JNC", "JB", "JNB"):
            state.pc += 1
            
        pc_after = state.pc
        cycles += 1
        
        layers_used[layer_used] = layers_used.get(layer_used, 0) + 1
        
        # Look up scheduler metadata for normal step
        meta = pc_to_scheduler_metadata.get(pc_before) if attach_scheduler_metadata else None
        if meta:
            if "wavefront_id" in meta:
                wf_key = (meta["wavefront_id"], meta["batch_index"])
                if wf_key not in executed_batches:
                    executed_batches.add(wf_key)
                    scheduled_cycles += 1
            else:
                # If kernel recognition only, don't increment scheduled cycles based on wavefronts
                scheduled_cycles += 1
        else:
            scheduled_cycles += 1
            
        # Check if error layer was hit
        if layer_used in ("unsupported_instruction", "unsupported_memory_op", "backend_error"):
            success = False
            oracle_match = False
            mismatches.append({
                "step_index": len(trace_steps),
                "pc": pc_before,
                "op": op,
                "failure_reason": f"Execution error: {layer_used}"
            })
            step = WaveguideControlMemoryInstructionTrace(
                step_index=len(trace_steps),
                pc_before=pc_before,
                pc_after=pc_after,
                instruction=inst,
                layer_used=layer_used,
                sol_result=sol_result,
                oracle_result=expected_res,
                sol_flags=sol_flags,
                oracle_flags=expected_flags,
                match=False,
                branch_trace=branch_trace,
                memory_trace=mem_trace,
                scheduler_metadata=meta,
                waveguide_channel_metadata=channel_meta
            )
            if op in ("LOAD", "STORE"):
                from sol_waveguide_memory_alias import get_instruction_memory_alias_metadata
                setattr(step, "memory_alias_metadata", get_instruction_memory_alias_metadata(inst, pc_before, clean_instructions, enable_memory_alias_analysis, state.width))
            if config and getattr(config, "enable_cost_model", False):
                step.cost_model_metadata = pass_manager_report.get("cost_model_report")
            if config and getattr(config, "enable_deterministic_autotuning", False):
                step.autotuning_metadata = pass_manager_report.get("autotuning_metadata")
            trace_steps.append(step)
            break
            
        # Match checks
        match = (sol_result == expected_res) and (sol_flags == expected_flags)
        if not match:
            success = False
            oracle_match = False
            mismatches.append({
                "step_index": len(trace_steps),
                "pc": pc_before,
                "op": op,
                "failure_reason": "Result or flags mismatch",
                "details": {
                    "expected_result": expected_res,
                    "actual_result": sol_result,
                    "expected_flags": expected_flags,
                    "actual_flags": sol_flags
                }
            })
            
        step = WaveguideControlMemoryInstructionTrace(
            step_index=len(trace_steps),
            pc_before=pc_before,
            pc_after=pc_after,
            instruction=inst,
            layer_used=layer_used,
            sol_result=sol_result,
            oracle_result=expected_res,
            sol_flags=sol_flags,
            oracle_flags=expected_flags,
            match=match,
            branch_trace=branch_trace,
            memory_trace=mem_trace,
            scheduler_metadata=meta,
            waveguide_channel_metadata=channel_meta
        )
        if op in ("LOAD", "STORE"):
            from sol_waveguide_memory_alias import get_instruction_memory_alias_metadata
            setattr(step, "memory_alias_metadata", get_instruction_memory_alias_metadata(inst, pc_before, clean_instructions, enable_memory_alias_analysis, state.width))
        if config and getattr(config, "enable_cost_model", False):
            step.cost_model_metadata = pass_manager_report.get("cost_model_report")
        if config and getattr(config, "enable_deterministic_autotuning", False):
            step.autotuning_metadata = pass_manager_report.get("autotuning_metadata")
        trace_steps.append(step)
        
        if op == "HALT":
            break
            
    # Verify final registers/memory/flags against oracle final state
    if cycles < len(oracle_traces) and success:
        # If oracle didn't halt but we did
        success = False
        oracle_match = False
        
    compaction_report = None
    if compaction_enabled:
        cycle_savings = total_original_cycles - total_compacted_cycles
        compaction_report = {
            "enabled": True,
            "windows_detected": len(windows),
            "windows_compacted": windows_compacted_count,
            "original_cycles": total_original_cycles,
            "compacted_cycles": total_compacted_cycles,
            "cycle_savings": max(0, cycle_savings),
            "semantic_equivalence": success and (len(mismatches) == 0),
            "unsafe_windows_skipped": unsafe_skipped
        }
        
    scoreboard_report = None
    if scoreboard_enabled:
        from sol_waveguide_scoreboard_scheduler import summarize_waveguide_scheduler_report
        scheduler_report.serial_cycle_estimate = cycles
        scheduler_report.scheduled_cycle_estimate = scheduled_cycles
        scheduler_report.cycle_savings = max(0, cycles - scheduled_cycles)
        scheduler_report.semantic_equivalence = success and (len(mismatches) == 0)
        scoreboard_report = summarize_waveguide_scheduler_report(scheduler_report)
        
    predication_report = None
    if predication_enabled:
        predication_report = {
            "enabled": True,
            "diamonds_detected": len(diamonds),
            "diamonds_predicated": diamonds_predicated_count,
            "original_cycles": total_pred_original_cycles,
            "predicated_cycles": total_pred_cycles,
            "cycle_savings": max(0, total_pred_original_cycles - total_pred_cycles),
            "skipped_diamonds": skipped_diamonds
        }

    if pass_manager_report is not None:
        pass_manager_report["estimated_raw_cycles"] = cycles
        pass_manager_report["estimated_optimized_cycles"] = scheduled_cycles
        pass_manager_report["cycle_savings"] = max(0, cycles - scheduled_cycles)

    accel_config = {
        "enable_simulation_acceleration": getattr(config, "enable_simulation_acceleration", False),
        "enable_compact_trace_mode": getattr(config, "enable_compact_trace_mode", False),
        "enable_trace_metadata_template_cache": getattr(config, "enable_trace_metadata_template_cache", True)
    }
    from sol_waveguide_simulation_acceleration import optimize_waveguide_trace_allocation
    trace_steps = optimize_waveguide_trace_allocation(trace_steps, accel_config)

    return WaveguideControlMemoryExecutionReport(
        success=success,
        oracle_match=oracle_match,
        trace_steps=trace_steps,
        mismatches=mismatches,
        layers_used=layers_used,
        pipeline_compaction_report=compaction_report,
        scoreboard_scheduler_report=scoreboard_report,
        branch_predication_report=predication_report,
        pass_manager_report=pass_manager_report
    )

def compare_waveguide_control_memory_to_oracle(trace: Any, oracle_trace: Any) -> bool:
    if len(trace.steps) != len(oracle_trace.steps):
        return False
    for i in range(len(trace.steps)):
        t_step = trace.steps[i]
        o_step = oracle_trace.steps[i]
        if t_step.sol_result != o_step.oracle_result:
            return False
    return True

def summarize_waveguide_control_memory_report(report: WaveguideControlMemoryExecutionReport) -> Dict[str, Any]:
    return {
        "success": report.success,
        "oracle_match": report.oracle_match,
        "total_instructions": len(report.trace_steps),
        "layers_used": report.layers_used
    }
