# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Simulation Performance Acceleration Bridge
========================================================
Implements safe performance acceleration tools for simulation, benchmark,
and trace-replay workflows without violating the sequential regression harness.
"""

import copy
import sys
from typing import List, Dict, Any, Tuple, Optional, Callable
from concurrent.futures import ThreadPoolExecutor

def build_waveguide_acceleration_config(
    enable_simulation_acceleration: bool = False,
    enable_compact_trace_mode: bool = False,
    enable_trace_metadata_template_cache: bool = True,
    enable_offline_benchmark_parallelism: bool = False,
    enable_offline_trace_replay_parallelism: bool = False,
    max_workers: int = 1,
    deterministic_result_ordering: bool = True,
    worker_state_isolation: bool = True
) -> Dict[str, Any]:
    """
    Constructs a conservative simulation acceleration configuration object.
    """
    return {
        "enable_simulation_acceleration": enable_simulation_acceleration,
        "enable_compact_trace_mode": enable_compact_trace_mode,
        "enable_trace_metadata_template_cache": enable_trace_metadata_template_cache,
        "enable_offline_benchmark_parallelism": enable_offline_benchmark_parallelism,
        "enable_offline_trace_replay_parallelism": enable_offline_trace_replay_parallelism,
        "max_workers": max_workers,
        "deterministic_result_ordering": deterministic_result_ordering,
        "worker_state_isolation": worker_state_isolation
    }

def optimize_waveguide_trace_allocation(trace_steps: List[Any], config: Dict[str, Any]) -> List[Any]:
    """
    Optimizes trace allocation without changing trace semantics.
    Interns common strings, reuses metadata templates, and applies compact trace modes.
    """
    if not config.get("enable_simulation_acceleration", False):
        return trace_steps

    optimized_steps = []
    metadata_cache = {}

    for step in trace_steps:
        # Intern repeated string keys / opcodes
        if hasattr(step, "instruction") and step.instruction:
            inst = step.instruction
            if hasattr(inst, "op") and isinstance(inst.op, str):
                inst.op = sys.intern(inst.op)
            if hasattr(inst, "dst") and isinstance(inst.dst, str):
                inst.dst = sys.intern(inst.dst)
            if hasattr(inst, "src1") and isinstance(inst.src1, str):
                inst.src1 = sys.intern(inst.src1)
            if hasattr(inst, "src2") and isinstance(inst.src2, str):
                inst.src2 = sys.intern(inst.src2)
        
        if hasattr(step, "layer_used") and isinstance(step.layer_used, str):
            step.layer_used = sys.intern(step.layer_used)

        # Cache/deduplicate waveguide_channel_metadata or scheduler_metadata
        if config.get("enable_trace_metadata_template_cache", True):
            for meta_attr in ("waveguide_channel_metadata", "scheduler_metadata", "memory_alias_metadata"):
                meta_val = getattr(step, meta_attr, None)
                if isinstance(meta_val, dict):
                    # Freeze dict as a key
                    frozen_key = tuple(sorted((k, str(v)) for k, v in meta_val.items()))
                    if frozen_key in metadata_cache:
                        setattr(step, meta_attr, metadata_cache[frozen_key])
                    else:
                        metadata_cache[frozen_key] = meta_val

        # Compact Trace Mode: Strip massive debug dumps if not needed
        if config.get("enable_compact_trace_mode", False):
            # Strip scheduler_metadata, branch_trace, memory_trace, memory_alias_metadata, and other debug/trace references
            for attr in ("scheduler_metadata", "branch_trace", "memory_trace", "memory_alias_metadata", "registers_before", "registers_after", "memory_before_refs", "memory_after_refs"):
                if hasattr(step, attr):
                    setattr(step, attr, None)

        optimized_steps.append(step)

    return optimized_steps

def run_waveguide_benchmark_batch_serial(
    cases: List[Any],
    run_func: Callable[[Any], Any]
) -> List[Any]:
    """
    Evaluates benchmark cases sequentially in a serial-safe harness.
    """
    results = []
    for case in cases:
        # Run isolated input copy
        case_copy = copy.deepcopy(case)
        result = run_func(case_copy)
        results.append(result)
    return results

def run_waveguide_benchmark_batch_accelerated(
    cases: List[Any],
    run_func: Callable[[Any], Any],
    max_workers: int = 1
) -> List[Any]:
    """
    Evaluates benchmark cases concurrently in an isolated ThreadPool.
    """
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit deep-copied cases for worker state isolation
        futures = {executor.submit(run_func, copy.deepcopy(case)): case for case in cases}
        for future in futures:
            results.append(future.result())
    return results

def run_waveguide_trace_replay_batch_serial(
    cases: List[Any],
    replay_func: Callable[[Any], Any]
) -> List[Any]:
    """
    Evaluates trace replay cases sequentially.
    """
    results = []
    for case in cases:
        case_copy = copy.deepcopy(case)
        result = replay_func(case_copy)
        results.append(result)
    return results

def run_waveguide_trace_replay_batch_accelerated(
    cases: List[Any],
    replay_func: Callable[[Any], Any],
    max_workers: int = 1
) -> List[Any]:
    """
    Evaluates trace replay cases concurrently.
    """
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(replay_func, copy.deepcopy(case)): case for case in cases}
        for future in futures:
            results.append(future.result())
    return results

def summarize_waveguide_acceleration_report(
    config: Dict[str, Any],
    acceleration_scope: str = "offline_benchmark_batch"
) -> Dict[str, Any]:
    """
    Builds the metadata dictionary detailing acceleration execution profiles.
    """
    return {
        "simulation_acceleration_enabled": config.get("enable_simulation_acceleration", False),
        "acceleration_scope": acceleration_scope,
        "parallel_workers": config.get("max_workers", 1),
        "deterministic_result_ordering": config.get("deterministic_result_ordering", True),
        "core_execution_parallelized": False,
        "pytest_parallelism_used": False
    }

def validate_waveguide_acceleration_equivalence(
    serial_results: List[Dict[str, Any]],
    accelerated_results: List[Dict[str, Any]],
    key_field: str = "case_id"
) -> bool:
    """
    Ensures parallel execution outputs match sequential results exactly for semantic fields.
    """
    if len(serial_results) != len(accelerated_results):
        return False

    # Map results by key_field
    serial_map = {r[key_field]: r for r in serial_results if isinstance(r, dict) and key_field in r}
    accel_map = {r[key_field]: r for r in accelerated_results if isinstance(r, dict) and key_field in r}

    if len(serial_map) != len(serial_results) or len(accel_map) != len(accelerated_results):
        # Fallback to index-based comparison if key_field is missing/not unique
        for i in range(len(serial_results)):
            s = serial_results[i]
            a = accelerated_results[i]
            if s != a:
                return False
        return True

    if set(serial_map.keys()) != set(accel_map.keys()):
        return False

    for k, s_val in serial_map.items():
        a_val = accel_map[k]
        # Compare semantic fields, ignoring timing metrics like elapsed time
        s_clean = copy.deepcopy(s_val)
        a_clean = copy.deepcopy(a_val)
        
        # Remove timing fields
        for d in (s_clean, a_clean):
            for field in ("elapsed_time", "wall_clock_time", "speedup_ratio", "time_taken"):
                d.pop(field, None)
                # Check nested dictionaries
                if "modes" in d:
                    for mode in d["modes"]:
                        if isinstance(d["modes"][mode], dict):
                            d["modes"][mode].pop("time_taken", None)
                            d["modes"][mode].pop("elapsed", None)
                            
        if s_clean != a_clean:
            return False

    return True
