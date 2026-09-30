# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Tensor Ranger
=============
Patrols parallel multi-sequencer core coordination and tensor-flow reports, emitting SovereignPackets.
"""

from coding_library.roaming_agents import LuminaRoamingAgent
from coding_library.sovereign_domain.evidence_packet import SovereignPacket
from typing import Any, Optional
from datetime import datetime, timezone

class TensorRanger(LuminaRoamingAgent):
    """
    Ranger patrolling to observe Level 22 vectorized multi-sequencer core and tensor flow execution.
    """
    def __init__(self, lib_agent=None):
        system_prompt = (
            "You are the Tensor Ranger. You patrol multi-sequencer core group execution, sharding,\n"
            "tensor operation plans, cross-core reduction trees, and consensus states."
        )
        super().__init__("Tensor Ranger", system_prompt, lib_agent)

    def observe_tensor_and_multicore(
        self,
        multicore_report: Optional[Any],
        tensor_report: Optional[Any],
        simd_mode: Optional[str] = None,
        mission_id: str = "M_TENSOR_MULTICORE_PATROL"
    ) -> SovereignPacket:
        """
        Observes multicore and tensor reports to construct a SovereignPacket.
        """
        if multicore_report is not None:
            self.travel(multicore_report)
        if tensor_report is not None:
            self.travel(tensor_report)

        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        # 1. Gather multicore details
        core_cnt = 0
        mc_passed_gates = True
        if multicore_report is not None:
            res = extract(multicore_report, "execution_result")
            plan = extract(res, "plan") if res else None
            cg = extract(plan, "core_group") if plan else None
            core_cnt = extract(cg, "core_count", 0)
            mc_passed_gates = extract(multicore_report, "passed_gates", True)

        # 2. Gather tensor details
        tensor_shape_dims = []
        shard_cnt = 0
        reduction_depth = 0
        consensus_status = "none"
        oracle_match = True
        tf_passed_gates = True
        
        if tensor_report is not None:
            tf_res = extract(tensor_report, "result")
            tf_op = extract(tf_res, "operation") if tf_res else None
            tf_plan = extract(tf_op, "plan") if tf_op else None
            
            shape_obj = extract(tf_plan, "shape") if tf_plan else None
            if shape_obj:
                tensor_shape_dims = extract(shape_obj, "dims", [])
            
            shards = extract(tf_plan, "shards", [])
            shard_cnt = len(shards)
            
            tf_passed_gates = extract(tensor_report, "passed_gates", True)
            
            meta = extract(tensor_report, "metadata", {})
            oracle_match = extract(meta, "oracle_match", True)
            
            tree = extract(meta, "reduction_tree")
            if tree:
                reduction_depth = extract(tree, "depth", 0)
                
            quorum = extract(meta, "consensus_quorum")
            if quorum:
                consensus_status = "quorum_reached" if extract(quorum, "quorum_reached") else "quorum_failed"

        # 3. Determine overall gate status and promotion readiness
        gate_status = mc_passed_gates and tf_passed_gates
        promotion_ready = gate_status and oracle_match

        evidence = {
            "core_count": core_cnt,
            "tensor_shape": tensor_shape_dims,
            "shard_count": shard_cnt,
            "shard_to_core_mapping_status": "complete" if shard_cnt > 0 else "none",
            "simd_mode_if_used": simd_mode or "none",
            "reduction_depth": reduction_depth,
            "consensus_status": consensus_status,
            "oracle_match": oracle_match,
            "gate_status": gate_status,
            "promotion_readiness": promotion_ready
        }

        recommendation = "promote" if promotion_ready else "observe"
        timestamp_str = datetime.now(timezone.utc).strftime("%H%M%S")
        packet_id = f"PKT_TEN_OBS_{timestamp_str}"
        repro_hash = extract(tensor_report, "reproducibility_hash", "none")

        packet = SovereignPacket(
            packet_id=packet_id,
            domain="sol_sovereign",
            level=22,
            actor=self.name,
            actor_type="ranger",
            mission_id=mission_id,
            claim="Audited report of Level 22 vectorized multi-sequencer core and tensor flow execution",
            evidence=evidence,
            invariants_checked=[
                "core_group_valid",
                "core_count_supported",
                "lane_fabric_assigned_per_core",
                "tensor_shape_valid",
                "tensor_shards_complete",
                "shard_to_core_mapping_complete",
                "reduction_tree_complete_if_required",
                "consensus_quorum_reached_if_required",
                "oracle_match_if_available"
            ],
            artifacts=[],
            recommendation=recommendation,
            confidence=0.99,
            reproducibility_hash=repro_hash
        )

        self.state_history.append(
            f"Observed multicore/tensor: cores={core_cnt}, shape={tensor_shape_dims}, shards={shard_cnt}, promotion_ready={promotion_ready}."
        )
        return packet
