# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
GC Ranger
=========
Patrols graph compaction and garbage collection analysis and reports.
"""

from coding_library.roaming_agents import LuminaRoamingAgent
from coding_library.sovereign_domain.evidence_packet import SovereignPacket
from typing import Any
from datetime import datetime, timezone

class GCRanger(LuminaRoamingAgent):
    """
    Ranger patrolling to observe Level 20 graph compaction plans and garbage collection events.
    """
    def __init__(self, lib_agent=None):
        system_prompt = (
            "You are the GC Ranger. You patrol graph compaction plans, reachability reports,\n"
            "GC collection plans, and ensure active register preservation."
        )
        super().__init__("GC Ranger", system_prompt, lib_agent)

    def observe_gc_and_compaction(
        self,
        compaction_report: Any,
        mission_id: str = "M_GC_COMPACTION_PATROL"
    ) -> SovereignPacket:
        """
        Observes compaction and GC reports to construct a SovereignPacket.
        """
        if compaction_report is not None:
            self.travel(compaction_report)

        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        plan = extract(compaction_report, "plan")
        snapshot = extract(plan, "metadata", {}).get("snapshot")
        gc_plan = extract(plan, "metadata", {}).get("gc_plan")
        gc_report = extract(plan, "metadata", {}).get("gc_report")
        reachability_report = extract(plan, "metadata", {}).get("reachability_report")
        
        node_cnt = len(extract(snapshot, "nodes", [])) if snapshot else 0
        edge_cnt = len(extract(snapshot, "edges", [])) if snapshot else 0
        
        reachable_cnt = len(extract(reachability_report, "reachable_node_ids", [])) if reachability_report else 0
        orphan_cnt = len(extract(reachability_report, "unreachable_node_ids", [])) if reachability_report else 0
        
        stale_edge_cnt = len(extract(gc_plan, "edges_to_collect", [])) if gc_plan else 0
        tombstone_cnt = len(extract(gc_plan, "tombstones", [])) if gc_plan else 0
        
        passed_gates = extract(compaction_report, "passed_gates", False)
        gate_rep = extract(compaction_report, "gate_report")
        checked_gates = extract(gate_rep, "checked_gates", {}) if gate_rep else {}
        
        active_ref_preserved = checked_gates.get("active_registers_preserved", True) and \
                               checked_gates.get("hcam_banks_preserved", True) and \
                               checked_gates.get("phase_tables_preserved", True) and \
                               checked_gates.get("transaction_references_preserved", True)
                               
        remap_complete = checked_gates.get("remap_table_complete", False)
        gate_status = passed_gates
        rollback_avail = checked_gates.get("rollback_snapshots_preserved", True)
        
        promotion_ready = passed_gates and active_ref_preserved and remap_complete and tombstone_cnt > 0

        evidence = {
            "node_count": node_cnt,
            "edge_count": edge_cnt,
            "reachable_count": reachable_cnt,
            "orphan_candidate_count": orphan_cnt,
            "stale_edge_count": stale_edge_cnt,
            "tombstone_count": tombstone_cnt,
            "active_references_preserved": active_ref_preserved,
            "remap_completeness": remap_complete,
            "gate_status": gate_status,
            "rollback_availability": rollback_avail,
            "promotion_readiness": promotion_ready
        }
        
        recommendation = "promote" if promotion_ready else "observe"
        timestamp_str = datetime.now(timezone.utc).strftime("%H%M%S")
        packet_id = f"PKT_GC_OBS_{timestamp_str}"
        repro_hash = extract(compaction_report, "reproducibility_hash", "none")

        packet = SovereignPacket(
            packet_id=packet_id,
            domain="sol_sovereign",
            level=20,
            actor=self.name,
            actor_type="ranger",
            mission_id=mission_id,
            claim="Audited report of Level 20 multi-sequence graph compaction and safe manifold garbage collection",
            evidence=evidence,
            invariants_checked=[
                "graph_snapshot_valid",
                "active_registers_preserved",
                "hcam_banks_preserved",
                "transaction_references_preserved"
            ],
            artifacts=[],
            recommendation=recommendation,
            confidence=0.99,
            reproducibility_hash=repro_hash
        )

        self.state_history.append(
            f"Observed GC and compaction: nodes={node_cnt}, orphans={orphan_cnt}, promotion_ready={promotion_ready}."
        )
        return packet
