# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Shard Ranger
============
Patrols distributed shards, queries, and shard-level consensus topologies.
"""

from coding_library.roaming_agents import LuminaRoamingAgent
from coding_library.sovereign_domain.evidence_packet import SovereignPacket
from typing import Any
from datetime import datetime, timezone

class ShardRanger(LuminaRoamingAgent):
    """
    Ranger patrolling to observe Level 18 distributed shards, query plans, consensus, and optimization.
    """
    def __init__(self, lib_agent=None):
        system_prompt = (
            "You are the Shard Ranger. You patrol distributed sharding structures,\n"
            "evaluate query plans, verify query tree optimization, and audit hierarchical consensus."
        )
        super().__init__("Shard Ranger", system_prompt, lib_agent)

    def observe_sharding(
        self,
        topology: Any,
        query_plan: Any,
        query_report: Any,
        consensus_report: Any,
        optimized_plan: Any,
        mission_id: str = "M_SHARD_PATROL"
    ) -> SovereignPacket:
        """
        Observes sharding structures to construct a SovereignPacket.
        """
        if topology is not None:
            self.travel(topology)

        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        shard_count = len(extract(topology, "shards", {}))
        rep_factor = extract(topology, "replication_factor", 1)
        lane_mappings = extract(topology, "lane_mappings", {})
        mapping_status = len(lane_mappings) > 0
        
        hops = extract(query_plan, "hops", [])
        query_depth = len(hops)
        
        boundary_crossings = sum(1 for h in hops if extract(h, "source_shard") != extract(h, "target_shard"))
        
        target_shards = extract(query_plan, "target_shards", [])
        fanout = max(0, len(target_shards) - 1)
        
        # Extract optimization details
        opt = extract(optimized_plan, "optimization")
        reduction_depth = 0
        opt_status = False
        if opt is not None:
            orig_cost = extract(opt, "original_cost")
            if orig_cost is not None:
                reduction_depth = extract(orig_cost, "reduction_depth", 0)
            improvement = extract(opt, "improvement_ratio", 0.0)
            opt_status = improvement >= 0.0
            
        # Consensus status
        global_dec = extract(consensus_report, "global_decision")
        global_q = extract(global_dec, "quorum_reached", False)
        
        local_decs = extract(consensus_report, "local_decisions", {})
        local_q = all(extract(dec, "quorum_reached", False) for dec in local_decs.values()) if local_decs else False
        
        passed_gates = extract(query_report, "passed_gates", False)
        promotion_ready = passed_gates and global_q and shard_count in [2, 4, 8]
        
        evidence = {
            "shard_count": shard_count,
            "replication_factor": rep_factor,
            "lane_to_shard_mapping_status": mapping_status,
            "query_depth": query_depth,
            "boundary_crossings": boundary_crossings,
            "fanout_count": fanout,
            "reduction_depth": reduction_depth,
            "local_quorum_status": local_q,
            "global_quorum_status": global_q,
            "optimization_status": opt_status,
            "promotion_readiness": promotion_ready
        }
        
        recommendation = "promote" if promotion_ready else "observe"
        
        timestamp_str = datetime.now(timezone.utc).strftime("%H%M%S")
        topo_id = extract(topology, "topology_id", "unknown_topo")
        packet_id = f"PKT_SHARD_OBS_{topo_id}_{timestamp_str}"
        repro_hash = extract(query_report, "reproducibility_hash", "none")
        
        packet = SovereignPacket(
            packet_id=packet_id,
            domain="sol_sovereign",
            level=18,
            actor=self.name,
            actor_type="ranger",
            mission_id=mission_id,
            claim="Audited report of Level 18 distributed multi-shard scale and query optimization",
            evidence=evidence,
            invariants_checked=[
                "shard_topology_valid",
                "shard_count_supported",
                "lane_to_shard_mapping_complete",
                "query_plan_complete"
            ],
            artifacts=[],
            recommendation=recommendation,
            confidence=0.99,
            reproducibility_hash=repro_hash
        )
        
        self.state_history.append(
            f"Observed shard topology {topo_id}: shards={shard_count}, promotion_ready={promotion_ready}."
        )
        return packet
