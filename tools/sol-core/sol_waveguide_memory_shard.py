# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Memory Shard
==========================
Defines localized shadow memory cells, address bounds enforcement,
and read/write slot tracking for PDM/waveguide pipelines.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from sol_wideword_computation_validation import mask_for_width

@dataclass
class WaveguideMemoryAddress:
    address: int

@dataclass
class WaveguideMemoryCell:
    address: int
    value: int

@dataclass
class WaveguideMemoryShard:
    width: int
    cells: Dict[int, int] = field(default_factory=dict)
    slots: int = 1024  # default slots limit

@dataclass
class WaveguideMemoryRead:
    address: int
    value: int

@dataclass
class WaveguideMemoryWrite:
    address: int
    value: int

@dataclass
class WaveguideMemoryTrace:
    reads: List[WaveguideMemoryRead] = field(default_factory=list)
    writes: List[WaveguideMemoryWrite] = field(default_factory=list)

@dataclass
class WaveguideMemoryShardReport:
    reads: List[WaveguideMemoryRead] = field(default_factory=list)
    writes: List[WaveguideMemoryWrite] = field(default_factory=list)

def build_waveguide_memory_shard(width: int, slots: int = 1024) -> WaveguideMemoryShard:
    return WaveguideMemoryShard(width=width, cells={}, slots=slots)

def validate_waveguide_memory_address(address: int, shard: WaveguideMemoryShard) -> bool:
    return 0 <= address < shard.slots

def execute_waveguide_load(shard: WaveguideMemoryShard, address: int) -> int:
    if not validate_waveguide_memory_address(address, shard):
        raise IndexError(f"Address {address} is out of bounds [0, {shard.slots - 1}]")
    mask = mask_for_width(shard.width)
    return shard.cells.get(address, 0) & mask

def execute_waveguide_store(shard: WaveguideMemoryShard, address: int, value: int) -> None:
    if not validate_waveguide_memory_address(address, shard):
        raise IndexError(f"Address {address} is out of bounds [0, {shard.slots - 1}]")
    mask = mask_for_width(shard.width)
    shard.cells[address] = value & mask

def snapshot_waveguide_memory_shard(shard: WaveguideMemoryShard) -> Dict[int, int]:
    return dict(shard.cells)

def compare_waveguide_memory_shards(before: Dict[int, int], after: Dict[int, int]) -> Dict[str, Any]:
    mutations = {}
    all_keys = set(before.keys()).union(after.keys())
    for k in all_keys:
        val_before = before.get(k, 0)
        val_after = after.get(k, 0)
        if val_before != val_after:
            mutations[str(k)] = {
                "before": val_before,
                "after": val_after
            }
    return mutations

def summarize_waveguide_memory_report(report: WaveguideMemoryShardReport) -> Dict[str, Any]:
    return {
        "total_reads": len(report.reads),
        "total_writes": len(report.writes)
    }
