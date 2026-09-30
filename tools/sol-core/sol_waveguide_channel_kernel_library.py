# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Channelized Kernel Library Module
===============================================
Defines descriptors, constraints, validation, and registry of
canonical channelized microprogram kernels.
"""

from typing import Dict, Any, List, Optional

def validate_waveguide_channel_kernel_descriptor(descriptor: Dict[str, Any]) -> None:
    """
    Validates that a kernel descriptor conforms to required schemas and constraints.
    """
    required_keys = {
        "kernel_id", "kernel_version", "pc_range", "input_channels", "output_channels",
        "input_registers", "output_registers", "contains_fence", "requires_channel_state",
        "requires_channel_dependency_analysis", "lowering_strategy", "scheduler_policy",
        "semantic_equivalence_required", "sandbox_only"
    }
    missing = required_keys - set(descriptor.keys())
    if missing:
        raise ValueError(f"Kernel descriptor missing required keys: {missing}")
        
    if not isinstance(descriptor["kernel_id"], str):
        raise TypeError("kernel_id must be a string")
    if not isinstance(descriptor["kernel_version"], str):
        raise TypeError("kernel_version must be a string")
    if not isinstance(descriptor["pc_range"], (list, tuple)) or len(descriptor["pc_range"]) != 2:
        raise TypeError("pc_range must be a list/tuple of two integers")
    if not isinstance(descriptor["input_channels"], list):
        raise TypeError("input_channels must be a list")
    if not isinstance(descriptor["output_channels"], list):
        raise TypeError("output_channels must be a list")
    if not isinstance(descriptor["input_registers"], list):
        raise TypeError("input_registers must be a list")
    if not isinstance(descriptor["output_registers"], list):
        raise TypeError("output_registers must be a list")
    if not isinstance(descriptor["contains_fence"], bool):
        raise TypeError("contains_fence must be a boolean")
    if descriptor["requires_channel_state"] is not True:
        raise ValueError("requires_channel_state must be True")
    if descriptor["requires_channel_dependency_analysis"] is not True:
        raise ValueError("requires_channel_dependency_analysis must be True")
    if descriptor["sandbox_only"] is not True:
        raise ValueError("sandbox_only must be True")

def build_waveguide_channel_kernel_descriptor(
    kernel_id: str,
    pc_range: List[int],
    input_channels: List[int],
    output_channels: List[int],
    input_registers: List[str],
    output_registers: List[str],
    contains_fence: bool = False,
    lowering_strategy: str = "existing_v1_channel_ops",
    scheduler_policy: str = "dependency_checked_wavefronts",
) -> Dict[str, Any]:
    """
    Constructs a validated kernel descriptor.
    """
    descriptor = {
        "kernel_id": kernel_id,
        "kernel_version": "v1.experimental",
        "pc_range": list(pc_range),
        "input_channels": list(input_channels),
        "output_channels": list(output_channels),
        "input_registers": list(input_registers),
        "output_registers": list(output_registers),
        "contains_fence": contains_fence,
        "requires_channel_state": True,
        "requires_channel_dependency_analysis": True,
        "lowering_strategy": lowering_strategy,
        "scheduler_policy": scheduler_policy,
        "semantic_equivalence_required": True,
        "sandbox_only": True
    }
    validate_waveguide_channel_kernel_descriptor(descriptor)
    return descriptor

# Canonical Kernel Registry
CANONICAL_KERNELS = {
    "channel_parallel_load": {
        "description": "Independent sends and receives executed in parallel.",
        "requires_fence": False
    },
    "channel_fanout": {
        "description": "Single channel send routed to multiple channels and received in parallel.",
        "requires_fence": False
    },
    "channel_fence_order": {
        "description": "Send followed by fence and receive to enforce strict channel ordering.",
        "requires_fence": True
    },
    "channel_gather": {
        "description": "Parallel channel load feeding a vector/lane assembly step.",
        "requires_fence": False
    },
    "channel_route_chain": {
        "description": "Sequential route dependency chain.",
        "requires_fence": False
    }
}

def get_waveguide_channel_kernel(kernel_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves the kernel details by ID.
    """
    return CANONICAL_KERNELS.get(kernel_id)

def summarize_waveguide_channel_kernel_library() -> Dict[str, Any]:
    """
    Returns library summary.
    """
    return {
        "supported_kernels": list(CANONICAL_KERNELS.keys()),
        "total_kernels": len(CANONICAL_KERNELS)
    }
