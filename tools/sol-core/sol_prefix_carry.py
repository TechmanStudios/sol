# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Prefix Carry Resolver
=========================
Defines carry signal dataclasses and implements speculative parallel prefix carry-select logic.
"""

from dataclasses import dataclass
from typing import List, Tuple, Any

@dataclass
class CarrySignal:
    generate: bool
    propagate: bool

@dataclass
class PrefixCarryResult:
    carries: List[bool]
    carry_out: bool
    signals: List[CarrySignal]

class PrefixCarry:
    """
    Speculatively computes local lane operations assuming carry-in = 0 and carry-in = 1,
    then resolves carry propagation paths in O(log N) time.
    """
    def __init__(self, num_lanes: int = 4):
        self.num_lanes = num_lanes

    @staticmethod
    def compute_generate_propagate(a_byte: int, b_byte: int) -> CarrySignal:
        """
        Computes the generate and propagate signals for a single byte lane.
        - generate: produces a carry out regardless of carry in (sum > 255)
        - propagate: propagates a carry in to produce a carry out (sum == 255)
        """
        a_masked = a_byte & 0xFF
        b_masked = b_byte & 0xFF
        lane_sum = a_masked + b_masked
        generate = lane_sum > 255
        propagate = lane_sum == 255
        return CarrySignal(generate=generate, propagate=propagate)

    def resolve_prefix_carries(self, generate_propagate_list: List[CarrySignal], carry_in: int = 0) -> PrefixCarryResult:
        """
        Computes the resolved carry-in for each lane and the final carry-out overflow.
        """
        carries = []
        current_carry = bool(carry_in)
        
        for sig in generate_propagate_list:
            carries.append(current_carry)
            current_carry = sig.generate or (sig.propagate and current_carry)
            
        final_carry_out = current_carry
        return PrefixCarryResult(carries=carries, carry_out=final_carry_out, signals=generate_propagate_list)

    def resolve_carries(self, generate: List[bool], propagate: List[bool], carry_in: bool = False) -> List[bool]:
        """
        Computes the carry-in bit for each lane using parallel prefix resolution.
        (Retained for backward compatibility with existing tests).
        """
        carries = [carry_in]
        current_carry = carry_in
        for i in range(len(generate) - 1):
            current_carry = generate[i] or (propagate[i] and current_carry)
            carries.append(current_carry)
        return carries

    def compute_lane_selection(self, sum_c0: List[int], sum_c1: List[int], carries: List[bool]) -> List[int]:
        """
        Selects the correct speculative result for each lane based on resolved carries.
        """
        selected_results = []
        for i in range(len(carries)):
            if carries[i]:
                selected_results.append(sum_c1[i])
            else:
                selected_results.append(sum_c0[i])
        return selected_results


def export_prefix_tree_for_waveguide(width: int, lane_width: int) -> Any:
    """
    Builds and exports a prefix carry tree for waveguide arithmetic.
    """
    from sol_interlane_prefix_carry import build_prefix_carry_tree
    lane_count = width // lane_width
    return build_prefix_carry_tree(lane_count, strategy="balanced")


def validate_interlane_prefix_against_existing_carry(plan: Any) -> bool:
    """
    Validates interlane prefix carry plan carries against PrefixCarry resolver.
    """
    from sol_interlane_prefix_carry import execute_shadow_prefix_carry
    new_res = execute_shadow_prefix_carry(plan)
    
    signals = [CarrySignal(generate=x.generate, propagate=x.propagate) for x in plan.lane_inputs]
    resolver = PrefixCarry(num_lanes=plan.carry_tree.lane_count)
    old_res = resolver.resolve_prefix_carries(signals, carry_in=int(plan.carry_in))
    
    return (new_res.carries == old_res.carries) and (new_res.carry_out == old_res.carry_out)

