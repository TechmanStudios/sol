# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Pipeline Balance Faults
===========================
Defines specific pipeline balancing faults and validation checks.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time
import uuid

@dataclass
class PipelineBalanceFault:
    fault_id: str
    category: str
    stage_id: Optional[str] = None
    magnitude: float = 1.0

@dataclass
class PipelineBalanceFaultInjection:
    injection_id: str
    fault: PipelineBalanceFault
    timestamp: float = field(default_factory=time.time)

@dataclass
class PipelineBalanceFaultReport:
    report_id: str
    fault: PipelineBalanceFault
    success: bool = False
    blocks_promotion: bool = True
    quarantine_recommended: bool = False
    errors: List[str] = field(default_factory=list)


def inject_false_pipeline_balance_improvement(balance_report: Any) -> Any:
    """
    Simulates a false balance improvement report.
    """
    import copy
    mutated = copy.deepcopy(balance_report)
    
    # Mutate to show worse latency after than before, but claim success
    if hasattr(mutated, "result") and mutated.result:
        mutated.result.success = True
        mutated.result.metadata["false_improvement"] = True
    elif isinstance(mutated, dict):
        if "result" in mutated:
            mutated["result"]["success"] = True
            mutated["result"].setdefault("metadata", {})["false_improvement"] = True
            
    return mutated


def inject_core_queue_depth_spike(balance_report: Any, magnitude: float) -> Any:
    """
    Simulates a queue depth spike on the balanced cores.
    """
    import copy
    mutated = copy.deepcopy(balance_report)
    if hasattr(mutated, "result") and mutated.result:
        mutated.result.metadata["core_queue_depth_spike"] = magnitude
    elif isinstance(mutated, dict):
        mutated.setdefault("metadata", {})["core_queue_depth_spike"] = magnitude
    return mutated


def inject_stage_latency_spike(balance_report: Any, stage_id: str, magnitude: float) -> Any:
    """
    Simulates a latency spike in a specific stage.
    """
    import copy
    mutated = copy.deepcopy(balance_report)
    if hasattr(mutated, "result") and mutated.result:
        mutated.result.metadata[f"latency_spike_{stage_id}"] = magnitude
    elif isinstance(mutated, dict):
        mutated.setdefault("metadata", {})[f"latency_spike_{stage_id}"] = magnitude
    return mutated


def inject_cross_core_stall_spike(balance_report: Any, magnitude: float) -> Any:
    """
    Simulates cross-core stalls spiking post-balancing.
    """
    import copy
    mutated = copy.deepcopy(balance_report)
    if hasattr(mutated, "result") and mutated.result:
        mutated.result.metadata["cross_core_stall_spike"] = magnitude
    elif isinstance(mutated, dict):
        mutated.setdefault("metadata", {})["cross_core_stall_spike"] = magnitude
    return mutated


def inject_backpressure_breach(balance_report: Any, magnitude: float) -> Any:
    """
    Simulates a backpressure breach.
    """
    import copy
    mutated = copy.deepcopy(balance_report)
    if hasattr(mutated, "result") and mutated.result:
        mutated.result.metadata["backpressure_breach"] = magnitude
    elif isinstance(mutated, dict):
        mutated.setdefault("metadata", {})["backpressure_breach"] = magnitude
    return mutated


def validate_balance_fault_blocks_promotion(fault_report: PipelineBalanceFaultReport) -> bool:
    """
    Validates that a pipeline balance fault blocks promotion.
    """
    # Any fault report must block promotion
    return fault_report.blocks_promotion
