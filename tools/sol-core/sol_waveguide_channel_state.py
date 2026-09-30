# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Sandbox Channel State Module
==========================================
Implements deterministic, sandbox-local waveguide channel state and semantics
for v1 channel candidate operations.
"""

from typing import Dict, Any, Tuple, Optional

def build_waveguide_channel_state(
    width_bits: int = 32,
    channel_count: int = 8,
    recv_empty_policy: str = "zero_with_empty_flag",
    clear_on_recv: bool = False
) -> Dict[str, Any]:
    """
    Initializes a sandbox-local channel state dictionary.
    """
    return {
        "channels": {
            i: {"valid": False, "value": 0} for i in range(channel_count)
        },
        "width_bits": width_bits,
        "channel_count": channel_count,
        "overflow_policy": "mask",
        "recv_empty_policy": recv_empty_policy,
        "clear_on_recv": clear_on_recv,
        "empty_flag_triggered": False
    }

def validate_waveguide_channel_id(state: Dict[str, Any], channel_id: int) -> None:
    """
    Validates if a channel ID is within the configured bounds.
    """
    count = state.get("channel_count", 8)
    if not isinstance(channel_id, int) or not (0 <= channel_id < count):
        raise ValueError(f"Invalid channel ID: {channel_id}. Bounded count is {count}")

def execute_waveguide_channel_send(state: Dict[str, Any], channel_id: int, value: int) -> Dict[str, Any]:
    """
    Executes WG_CHAN_SEND: updates channel state deterministically.
    """
    validate_waveguide_channel_id(state, channel_id)
    width = state.get("width_bits", 32)
    mask = (1 << width) - 1
    value_masked = value & mask
    
    channels = state["channels"]
    valid_before = channels[channel_id]["valid"]
    
    channels[channel_id]["valid"] = True
    channels[channel_id]["value"] = value_masked
    
    return {
        "waveguide_channel_state_enabled": True,
        "channel_opcode": "WG_CHAN_SEND",
        "channel_id": channel_id,
        "value_masked": value_masked,
        "channel_valid_before": valid_before,
        "channel_valid_after": True,
        "external_io": False,
        "deterministic": True
    }

def execute_waveguide_channel_recv(state: Dict[str, Any], channel_id: int) -> Tuple[int, Dict[str, Any]]:
    """
    Executes WG_CHAN_RECV: reads from channel state.
    """
    validate_waveguide_channel_id(state, channel_id)
    channels = state["channels"]
    valid_before = channels[channel_id]["valid"]
    val_before = channels[channel_id]["value"]
    
    if valid_before:
        value = val_before
        if state.get("clear_on_recv", False):
            channels[channel_id]["valid"] = False
            channels[channel_id]["value"] = 0
        valid_after = channels[channel_id]["valid"]
    else:
        value = 0
        valid_after = False
        state["empty_flag_triggered"] = True
        
    meta = {
        "waveguide_channel_state_enabled": True,
        "channel_opcode": "WG_CHAN_RECV",
        "channel_id": channel_id,
        "value_masked": value,
        "channel_valid_before": valid_before,
        "channel_valid_after": valid_after,
        "external_io": False,
        "deterministic": True,
        "empty_recv_triggered": not valid_before
    }
    
    return value, meta

def execute_waveguide_channel_route(
    state: Dict[str, Any],
    dst_channel: int,
    src_channel: int,
    route_mask: int
) -> Dict[str, Any]:
    """
    Executes WG_CHAN_ROUTE: copies source channel to destination if route_mask is non-zero.
    """
    validate_waveguide_channel_id(state, dst_channel)
    validate_waveguide_channel_id(state, src_channel)
    
    enabled = (route_mask != 0)
    channels = state["channels"]
    dst_valid_before = channels[dst_channel]["valid"]
    dst_val_before = channels[dst_channel]["value"]
    
    if enabled:
        src_valid = channels[src_channel]["valid"]
        src_val = channels[src_channel]["value"]
        channels[dst_channel]["valid"] = src_valid
        channels[dst_channel]["value"] = src_val
        
    dst_valid_after = channels[dst_channel]["valid"]
    dst_val_after = channels[dst_channel]["value"]
    
    return {
        "waveguide_channel_state_enabled": True,
        "channel_opcode": "WG_CHAN_ROUTE",
        "dst_channel": dst_channel,
        "src_channel": src_channel,
        "route_mask": route_mask,
        "route_enabled": enabled,
        "value_masked": dst_val_after,
        "channel_valid_before": dst_valid_before,
        "channel_valid_after": dst_valid_after,
        "external_io": False,
        "deterministic": True
    }

def execute_waveguide_channel_fence(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes WG_CHAN_FENCE: returns ordering barrier metadata.
    """
    return {
        "waveguide_channel_state_enabled": True,
        "channel_opcode": "WG_CHAN_FENCE",
        "external_io": False,
        "deterministic": True
    }

def snapshot_waveguide_channel_state(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Returns a copy of the channel values and valid statuses.
    """
    return {
        "channels": {
            i: dict(state["channels"][i]) for i in state["channels"]
        },
        "empty_flag_triggered": state.get("empty_flag_triggered", False)
    }

def compare_waveguide_channel_states(state1: Dict[str, Any], state2: Dict[str, Any]) -> bool:
    """
    Compares two channel states for equivalence.
    """
    ch1 = state1.get("channels", {})
    ch2 = state2.get("channels", {})
    if len(ch1) != len(ch2):
        return False
        
    for k in ch1:
        if k not in ch2:
            return False
        if ch1[k]["valid"] != ch2[k]["valid"]:
            return False
        if ch1[k]["valid"] and ch1[k]["value"] != ch2[k]["value"]:
            return False
            
    return state1.get("empty_flag_triggered", False) == state2.get("empty_flag_triggered", False)

def summarize_waveguide_channel_report(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Provides a summary report of the channel state.
    """
    active_count = sum(1 for i in state["channels"] if state["channels"][i]["valid"])
    return {
        "active_channels": active_count,
        "empty_flag_triggered": state.get("empty_flag_triggered", False),
        "channel_snapshot": snapshot_waveguide_channel_state(state)
    }

def resolve_channel_id(operand: Any, registers: Dict[str, int]) -> int:
    """
    Resolves channel ID operand to an integer.
    """
    if isinstance(operand, str) and operand.startswith("R"):
        return registers.get(operand, 0)
    if isinstance(operand, int):
        return operand
    if isinstance(operand, str):
        try:
            return int(operand)
        except ValueError:
            pass
    return 0

def resolve_operand_val(operand: Any, registers: Dict[str, int], mask: int) -> int:
    """
    Resolves arbitrary source/mask operand value to an integer.
    """
    if isinstance(operand, str) and operand.startswith("R"):
        return registers.get(operand, 0)
    if isinstance(operand, int):
        return operand & mask
    return 0
