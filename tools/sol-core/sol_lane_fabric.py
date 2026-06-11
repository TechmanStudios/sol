# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Lane Fabric
===============
Coordinates spatial multi-lane PDM byte-slice configurations for WideWord compute.
Now incorporates HCAM associative memory banking mapping, word encoding, and multi-lane wave sampling.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Callable
from sol_pdm_byte_slice import PDMByteSlice, ByteALUResult, PDMEncodedByte, sample_wave_packet
from sol_hcam_banking import HCAMBank, HCAMAddressMap, HCAMRecallPlan

@dataclass
class WordALUResult:
    operation: str
    width: int
    lane_count: int
    a: int
    b: int
    result: int
    carry_out: int
    lane_results: List[ByteALUResult]
    carry_trace: List[bool]
    evidence: Dict[str, Any]

class LaneFabric:
    """
    Coordinates spatial byte slice lanes for 16-bit, 32-bit, and 64-bit WideWord compute.
    """
    def __init__(self, num_lanes: int = 4):
        self.num_lanes = num_lanes
        self.lanes = [
            PDMByteSlice(lane_id=i, bit_offset=i * 8)
            for i in range(num_lanes)
        ]
        
        # Initialize optional HCAM memory banking map metadata
        total_bits = num_lanes * 8
        self.hcam_banks = HCAMBank.for_width(total_bits)
        self.hcam_map = HCAMAddressMap(
            width=total_bits,
            lane_count=num_lanes,
            banks=self.hcam_banks
        )

    @classmethod
    def for_width(cls, width: int) -> "LaneFabric":
        """
        Constructs a LaneFabric instance configured for the given bit width:
        - 16-bit -> 2 byte slices
        - 32-bit -> 4 byte slices
        - 64-bit -> 8 byte slices
        """
        if width == 16:
            return cls(num_lanes=2)
        elif width == 32:
            return cls(num_lanes=4)
        elif width == 64:
            return cls(num_lanes=8)
        else:
            raise ValueError(f"Unsupported WideWord width: {width}")

    def add_word(self, a: int, b: int, carry_in: int = 0) -> WordALUResult:
        """
        Performs WideWord addition by splitting inputs into byte slices, speculatively
        computing sums for carry-in=0/1 on each lane, and selecting results using prefix carry.
        """
        # Mask inputs to the fabric's total bit width
        total_bits = self.num_lanes * 8
        mask = (1 << total_bits) - 1
        a_masked = a & mask
        b_masked = b & mask
        c_in = carry_in & 1

        # 1. Split inputs into little-endian bytes
        a_bytes = [(a_masked >> (i * 8)) & 0xFF for i in range(self.num_lanes)]
        b_bytes = [(b_masked >> (i * 8)) & 0xFF for i in range(self.num_lanes)]

        # 2. Speculatively compute sums for carry_in=0 and carry_in=1
        sum_c0_list = []
        sum_c1_list = []
        for i in range(self.num_lanes):
            sum_c0_list.append(self.lanes[i].add8(a_bytes[i], b_bytes[i], carry_in=0))
            sum_c1_list.append(self.lanes[i].add8(a_bytes[i], b_bytes[i], carry_in=1))

        # 3. Resolve generate/propagate signals and prefix carries
        from sol_prefix_carry import PrefixCarry
        resolver = PrefixCarry(num_lanes=self.num_lanes)
        signals = [resolver.compute_generate_propagate(a_bytes[i], b_bytes[i]) for i in range(self.num_lanes)]
        prefix_result = resolver.resolve_prefix_carries(signals, carry_in=c_in)

        # 4. Select correct speculative sum per lane
        lane_results = []
        result_word = 0
        for i in range(self.num_lanes):
            lane_carry = prefix_result.carries[i]
            selected_res = sum_c1_list[i] if lane_carry else sum_c0_list[i]
            lane_results.append(selected_res)
            result_word |= (selected_res.result << (i * 8))

        carry_out = 1 if prefix_result.carry_out else 0

        evidence = {
            "speculative_sums_c0": [r.result for r in sum_c0_list],
            "speculative_sums_c1": [r.result for r in sum_c1_list],
            "generate_propagate": [{"generate": s.generate, "propagate": s.propagate} for s in signals],
            "prefix_carries": prefix_result.carries
        }

        return WordALUResult(
            operation="add",
            width=total_bits,
            lane_count=self.num_lanes,
            a=a_masked,
            b=b_masked,
            result=result_word,
            carry_out=carry_out,
            lane_results=lane_results,
            carry_trace=prefix_result.carries,
            evidence=evidence
        )

    def memory_plan_for_address(self, address: int) -> HCAMRecallPlan:
        """
        Generates a non-mutating HCAM memory recall plan for the specified address,
        mapping recall operations to the configured byte lane memory banks.
        """
        steps = [
            f"Set active H-CAM address query registers to {hex(address)}",
            "Broadcast associative address wave packet across waveguide fabric"
        ]
        
        for bank in self.hcam_banks:
            steps.append(f"Open recall gate '{bank.recall_gate}' for Bank {bank.bank_id}")
            steps.append(f"Precipitate target basin '{bank.value_basin}' density into register '{bank.commit_register}'")

        steps.append("Synchronize lane commits and trigger gated WideWord memory barrier")

        evidence = {
            "address": address,
            "mapped_lanes": self.num_lanes,
            "mapped_banks": len(self.hcam_banks),
            "step_count": len(steps)
        }

        return HCAMRecallPlan(
            address=address,
            address_map=self.hcam_map,
            execution_steps=steps,
            evidence=evidence
        )

    # ---- Phase 4: Deterministic wave encoding and multi-lane wave sampling ----

    def encode_word(self, value: int) -> List[PDMEncodedByte]:
        """
        Splits a WideWord value into little-endian byte lanes and encodes each byte
        into a PDMEncodedByte containing 8 quadrature carrier channels.
        """
        total_bits = self.num_lanes * 8
        mask = (1 << total_bits) - 1
        val_masked = value & mask

        encoded_lanes = []
        for i, lane in enumerate(self.lanes):
            byte_val = (val_masked >> (i * 8)) & 0xFF
            encoded_lanes.append(lane.encode_byte(byte_val))
        return encoded_lanes

    def sample_word_wave_packet(
        self,
        encoded_word: List[PDMEncodedByte],
        t_values: List[float],
        envelope_func: Optional[Callable[[float], float]] = None
    ) -> List[List[float]]:
        """
        Samples the wave packet signals for each lane in an encoded word over t_values.
        Returns a list of float lists (one list of signal values per byte lane).
        """
        sampled_lanes = []
        for i in range(self.num_lanes):
            if i < len(encoded_word):
                sampled_lanes.append(sample_wave_packet(encoded_word[i], t_values, envelope_func))
            else:
                # Fallback to zero signal values
                sampled_lanes.append([0.0] * len(t_values))
        return sampled_lanes

    def modulate_word(self, word_value: int) -> List[Dict[str, float]]:
        """Splits a wide word into byte lanes and modulates each lane."""
        modulated_lanes = []
        for i, lane in enumerate(self.lanes):
            byte_val = (word_value >> (i * 8)) & 0xFF
            modulated_lanes.append(lane.modulate(byte_val))
        return modulated_lanes

    def demodulate_word(self, modulated_lanes: List[Dict[str, float]]) -> int:
        """Demodulates amplitudes from each lane and commits a single wide word."""
        word_value = 0
        for i, lane in enumerate(self.lanes):
            if i < len(modulated_lanes):
                byte_val = lane.demodulate(modulated_lanes[i])
                word_value |= (byte_val << (i * 8))
        return word_value

    def sub_word(self, a: int, b: int, borrow_in: int = 0) -> WordALUResult:
        """
        Performs WideWord subtraction by splitting inputs into byte slices, speculatively
        computing differences for borrow-in=0/1 on each lane, and selecting results using prefix carry.
        """
        total_bits = self.num_lanes * 8
        mask = (1 << total_bits) - 1
        a_masked = a & mask
        b_masked = b & mask
        b_in = borrow_in & 1

        a_bytes = [(a_masked >> (i * 8)) & 0xFF for i in range(self.num_lanes)]
        b_bytes = [(b_masked >> (i * 8)) & 0xFF for i in range(self.num_lanes)]

        sub_c0_list = []
        sub_c1_list = []
        for i in range(self.num_lanes):
            sub_c0_list.append(self.lanes[i].sub8(a_bytes[i], b_bytes[i], borrow_in=0))
            sub_c1_list.append(self.lanes[i].sub8(a_bytes[i], b_bytes[i], borrow_in=1))

        from sol_prefix_carry import PrefixCarry, CarrySignal
        resolver = PrefixCarry(num_lanes=self.num_lanes)
        
        signals = []
        for i in range(self.num_lanes):
            gen = a_bytes[i] < b_bytes[i]
            prop = a_bytes[i] == b_bytes[i]
            signals.append(CarrySignal(generate=gen, propagate=prop))

        prefix_result = resolver.resolve_prefix_carries(signals, carry_in=b_in)

        lane_results = []
        result_word = 0
        for i in range(self.num_lanes):
            lane_borrow = prefix_result.carries[i]
            selected_res = sub_c1_list[i] if lane_borrow else sub_c0_list[i]
            lane_results.append(selected_res)
            result_word |= (selected_res.result << (i * 8))

        borrow_out = 1 if prefix_result.carry_out else 0

        evidence = {
            "speculative_diffs_c0": [r.result for r in sub_c0_list],
            "speculative_diffs_c1": [r.result for r in sub_c1_list],
            "borrow_signals": [{"generate": s.generate, "propagate": s.propagate} for s in signals],
            "prefix_borrows": prefix_result.carries
        }

        return WordALUResult(
            operation="sub",
            width=total_bits,
            lane_count=self.num_lanes,
            a=a_masked,
            b=b_masked,
            result=result_word,
            carry_out=borrow_out,
            lane_results=lane_results,
            carry_trace=prefix_result.carries,
            evidence=evidence
        )

    def and_word(self, a: int, b: int) -> WordALUResult:
        """Performs WideWord bitwise AND across all byte lanes."""
        total_bits = self.num_lanes * 8
        mask = (1 << total_bits) - 1
        a_masked = a & mask
        b_masked = b & mask
        result_word = a_masked & b_masked

        a_bytes = [(a_masked >> (i * 8)) & 0xFF for i in range(self.num_lanes)]
        b_bytes = [(b_masked >> (i * 8)) & 0xFF for i in range(self.num_lanes)]

        lane_results = []
        for i in range(self.num_lanes):
            lane_results.append(self.lanes[i].and8(a_bytes[i], b_bytes[i]))

        return WordALUResult(
            operation="and",
            width=total_bits,
            lane_count=self.num_lanes,
            a=a_masked,
            b=b_masked,
            result=result_word,
            carry_out=0,
            lane_results=lane_results,
            carry_trace=[],
            evidence={}
        )

    def or_word(self, a: int, b: int) -> WordALUResult:
        """Performs WideWord bitwise OR across all byte lanes."""
        total_bits = self.num_lanes * 8
        mask = (1 << total_bits) - 1
        a_masked = a & mask
        b_masked = b & mask
        result_word = a_masked | b_masked

        a_bytes = [(a_masked >> (i * 8)) & 0xFF for i in range(self.num_lanes)]
        b_bytes = [(b_masked >> (i * 8)) & 0xFF for i in range(self.num_lanes)]

        lane_results = []
        for i in range(self.num_lanes):
            lane_results.append(self.lanes[i].or8(a_bytes[i], b_bytes[i]))

        return WordALUResult(
            operation="or",
            width=total_bits,
            lane_count=self.num_lanes,
            a=a_masked,
            b=b_masked,
            result=result_word,
            carry_out=0,
            lane_results=lane_results,
            carry_trace=[],
            evidence={}
        )

    def xor_word(self, a: int, b: int) -> WordALUResult:
        """Performs WideWord bitwise XOR across all byte lanes."""
        total_bits = self.num_lanes * 8
        mask = (1 << total_bits) - 1
        a_masked = a & mask
        b_masked = b & mask
        result_word = a_masked ^ b_masked

        a_bytes = [(a_masked >> (i * 8)) & 0xFF for i in range(self.num_lanes)]
        b_bytes = [(b_masked >> (i * 8)) & 0xFF for i in range(self.num_lanes)]

        lane_results = []
        for i in range(self.num_lanes):
            lane_results.append(self.lanes[i].xor8(a_bytes[i], b_bytes[i]))

        return WordALUResult(
            operation="xor",
            width=total_bits,
            lane_count=self.num_lanes,
            a=a_masked,
            b=b_masked,
            result=result_word,
            carry_out=0,
            lane_results=lane_results,
            carry_trace=[],
            evidence={}
        )

    def not_word(self, a: int) -> WordALUResult:
        """Performs WideWord bitwise NOT across all byte lanes."""
        total_bits = self.num_lanes * 8
        mask = (1 << total_bits) - 1
        a_masked = a & mask
        result_word = (~a_masked) & mask

        a_bytes = [(a_masked >> (i * 8)) & 0xFF for i in range(self.num_lanes)]

        lane_results = []
        for i in range(self.num_lanes):
            lane_results.append(self.lanes[i].not8(a_bytes[i]))

        return WordALUResult(
            operation="not",
            width=total_bits,
            lane_count=self.num_lanes,
            a=a_masked,
            b=0,
            result=result_word,
            carry_out=0,
            lane_results=lane_results,
            carry_trace=[],
            evidence={}
        )

    def shift_left_word(self, a: int, shift: int) -> WordALUResult:
        """Performs WideWord logical shift left."""
        total_bits = self.num_lanes * 8
        mask = (1 << total_bits) - 1
        a_masked = a & mask
        result_word = (a_masked << shift) & mask

        a_bytes = [(a_masked >> (i * 8)) & 0xFF for i in range(self.num_lanes)]
        res_bytes = [(result_word >> (i * 8)) & 0xFF for i in range(self.num_lanes)]
        
        from sol_pdm_byte_slice import ByteALUResult
        lane_results = []
        for i in range(self.num_lanes):
            lane_results.append(ByteALUResult(
                operation="shl",
                lane_id=i,
                a=a_bytes[i],
                b=shift,
                result=res_bytes[i],
                carry_out=0,
                flags={"zero": res_bytes[i] == 0, "negative": bool(res_bytes[i] & 0x80)},
                evidence={}
            ))

        return WordALUResult(
            operation="shl",
            width=total_bits,
            lane_count=self.num_lanes,
            a=a_masked,
            b=shift,
            result=result_word,
            carry_out=0,
            lane_results=lane_results,
            carry_trace=[],
            evidence={}
        )

    def shift_right_word(self, a: int, shift: int) -> WordALUResult:
        """Performs WideWord logical shift right."""
        total_bits = self.num_lanes * 8
        mask = (1 << total_bits) - 1
        a_masked = a & mask
        result_word = (a_masked >> shift) & mask

        a_bytes = [(a_masked >> (i * 8)) & 0xFF for i in range(self.num_lanes)]
        res_bytes = [(result_word >> (i * 8)) & 0xFF for i in range(self.num_lanes)]
        
        from sol_pdm_byte_slice import ByteALUResult
        lane_results = []
        for i in range(self.num_lanes):
            lane_results.append(ByteALUResult(
                operation="shr",
                lane_id=i,
                a=a_bytes[i],
                b=shift,
                result=res_bytes[i],
                carry_out=0,
                flags={"zero": res_bytes[i] == 0, "negative": bool(res_bytes[i] & 0x80)},
                evidence={}
            ))

        return WordALUResult(
            operation="shr",
            width=total_bits,
            lane_count=self.num_lanes,
            a=a_masked,
            b=shift,
            result=result_word,
            carry_out=0,
            lane_results=lane_results,
            carry_trace=[],
            evidence={}
        )

    def simd_plan(self, mode: str):
        """
        Generates a SIMD execution plan for the current fabric width and target mode.
        """
        from sol_simd_modes import plan_simd_mode
        total_bits = self.num_lanes * 8
        return plan_simd_mode(total_bits, mode)

    def fabric_topology(self) -> Any:
        """
        Returns the WideWordFabricTopology for the current LaneFabric.
        """
        from sol_wideword_fabric import build_wideword_fabric
        return build_wideword_fabric(self.num_lanes * 8)

    def boundary_plan(self) -> Dict[str, Any]:
        """
        Returns the boundary absorption parameters including isolation and crosstalk limits.
        """
        return {
            "num_lanes": self.num_lanes,
            "isolation_gap": 0.05,
            "crosstalk_threshold": 0.05,
            "boundary_gamma": 0.15,
            "core_gamma": 0.002
        }

    def wideword_execution_plan(self, instruction_result: Any) -> Any:
        """
        Generates a WideWordFabricExecutionPlan wrapping hierarchical topology, instruction,
        and PDM plan details.
        """
        from sol_wideword_fabric import WideWordFabricExecutionPlan
        from sol_pdm_executor import build_execution_plan
        
        topology = self.fabric_topology()
        pdm_plan = build_execution_plan(instruction_result, self)
        t_values = [0.1 * i for i in range(10000)]
        
        return WideWordFabricExecutionPlan(
            topology=topology,
            instruction=instruction_result.instruction,
            pdm_plan=pdm_plan,
            t_values=t_values,
            envelope_func=None,
            metadata={"sandbox_trial": True}
        )

    def hcam_topology(self) -> Any:
        """
        Returns the Hierarchical HCAM Topology configuration for the fabric's current width.
        """
        from sol_hcam_banking import build_hcam_topology
        return build_hcam_topology(self.num_lanes * 8)

    def build_memory_query(self, address: int) -> Any:
        """
        Constructs an HCAMQuery object targeting the given address.
        """
        from sol_hcam_banking import build_query_plan
        return build_query_plan(address, self.num_lanes * 8)

    def plan_hcam_recall(self, address: int) -> Any:
        """
        Plans H-CAM banked recall for the specified address, routing query and response routes.
        """
        from sol_hcam_banking import (
            build_query_plan,
            route_query_to_banks,
            build_response_routes,
            HCAMBankedRecallPlan
        )
        topo = self.hcam_topology()
        query = build_query_plan(address, self.num_lanes * 8)
        q_routes = route_query_to_banks(query, topo)
        
        plan = HCAMBankedRecallPlan(
            query=query,
            topology=topo,
            query_routes=q_routes,
            response_routes=[],
            metadata={}
        )
        resp_routes = build_response_routes(plan, topo)
        plan.response_routes = resp_routes
        
        return plan

    def assemble_recall_word(self, bank_values: Any) -> int:
        """
        Assembles a wide integer word from the given bank byte values.
        """
        from sol_hcam_banking import assemble_word_from_bank_values
        return assemble_word_from_bank_values(bank_values, self.num_lanes * 8)

    def export_waveguide_synthesis_spec(self, topology: Any = None, simd_plan: Optional[Any] = None) -> Any:
        """
        Exports a WaveguideFabricSpec candidate.
        """
        from sol_waveguide_fabric_synthesis import build_waveguide_fabric_spec
        topo = topology if topology is not None else {"width": self.num_lanes * 8, "lane_groups": []}
        return build_waveguide_fabric_spec(topo, self, simd_plan)

    def validate_fabric_against_synthesized_waveguide(self, candidate: Any) -> bool:
        """
        Validates the logic fabric bindings against the synthesized candidate fabric.
        """
        from sol_waveguide_fabric_synthesis import validate_waveguide_fabric_candidate
        return validate_waveguide_fabric_candidate(candidate)


def export_waveguide_synthesis_spec(topology: Any, lane_fabric: Any, simd_plan: Optional[Any] = None) -> Any:
    """
    Exports a WaveguideFabricSpec candidate from a given topology and lane fabric.
    """
    from sol_waveguide_fabric_synthesis import build_waveguide_fabric_spec
    return build_waveguide_fabric_spec(topology, lane_fabric, simd_plan)


def validate_fabric_against_synthesized_waveguide(candidate: Any) -> bool:
    """
    Validates the logic fabric bindings against the synthesized candidate fabric.
    """
    from sol_waveguide_fabric_synthesis import validate_waveguide_fabric_candidate
    return validate_waveguide_fabric_candidate(candidate)


def build_hierarchical_waveguide_plan(width: int) -> Any:
    """
    Constructs a hierarchical waveguide plan for the given width.
    """
    from sol_wideword_fabric import build_hierarchical_waveguide_plan as _build_plan
    return _build_plan(width)


def attach_interlane_prefix_carry(plan: Any) -> Any:
    """
    Attaches inter-lane prefix carry metadata to a WideWordFabricExecutionPlan.
    """
    from sol_wideword_fabric import attach_interlane_prefix_carry as _attach
    return _attach(plan)


def validate_wideword_arithmetic_fabric(plan: Any) -> bool:
    """
    Validates that the WideWordFabricExecutionPlan has valid hierarchical topology
    and interlane prefix carry tree bindings.
    """
    from sol_wideword_fabric import validate_wideword_arithmetic_fabric as _validate
    return _validate(plan)


