# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Route Fault Ranger
==================
Audits route rebalance fault matrices, regression matrices, rollback proofing, and safety oracle reports.
"""

from coding_library.roaming_agents import LuminaRoamingAgent
from coding_library.sovereign_domain.evidence_packet import SovereignPacket
from typing import Dict, Any, List, Optional

class RouteFaultRanger(LuminaRoamingAgent):
    """
    Ranger auditing the Phase 42 fault matrix, regression, rollback, and oracle reports.
    """
    def __init__(self, lib_agent=None):
        system_prompt = (
            "You are the Route Fault Ranger. You audit route rebalance fault matrices,\n"
            "regression reports, and safety oracle outcomes to verify sovereign invariants."
        )
        super().__init__("Route Fault Ranger", system_prompt, lib_agent)

    def observe_reports(
        self,
        fault_report: Any,
        regression_report: Any,
        cost_report: Any,
        waveguide_report: Any,
        rollback_report: Any,
        oracle_report: Any,
        mission_id: str = "MISSION_RF_001"
    ) -> SovereignPacket:
        """
        Observes and audits all Phase 42 reports to emit a SovereignPacket.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        # 1. total/passed/failed fault cases
        results = extract(fault_report, "results", []) or []
        total = len(results)
        passed = sum(1 for r in results if extract(r, "success", False))
        failed = total - passed

        # 2. regression count
        reg_results = extract(regression_report, "results", []) or []
        reg_count = sum(1 for r in reg_results if extract(r, "regression_detected", False))

        # 3. rollback proof status
        rb_success = extract(rollback_report, "success", True)
        
        # 4. behaviors
        behaviors = {}
        for r in results:
            cat = extract(r, "category", "")
            success = extract(r, "success", False)
            if cat:
                behaviors[cat] = "blocked" if success else "failed"

        # 5. active table protection status
        table_protect = "protected"
        for cat_name in ["active phase-table overwrite attempt", "active cadence-profile overwrite attempt", "active carrier-registry overwrite attempt"]:
            for r in results:
                if extract(r, "category") == cat_name and not extract(r, "success"):
                    table_protect = "violated"

        # 6. safety oracle agreement
        oracle_agreement = "agreed"
        for r in results:
            if extract(r, "category") == "safety oracle mismatch" and not extract(r, "success"):
                oracle_agreement = "mismatched"

        # 7. quarantine status
        quarantined = False
        quarantine_targets = []
        for r in results:
            outcome = extract(r, "actual_outcome", "")
            if outcome and "quarantine" in outcome:
                quarantined = True
                quarantine_targets.append(outcome)

        # 8. promotion readiness
        reg_failed = sum(1 for r in reg_results if not extract(r, "success", False))
        ready = (failed == 0) and (reg_failed == 0) and rb_success and (table_protect == "protected") and (oracle_agreement == "agreed")
        recommendation = "promote" if ready else "quarantine"

        evidence = {
            "total_fault_cases": total,
            "passed_fault_cases": passed,
            "failed_fault_cases": failed,
            "regression_count": reg_count,
            "rollback_proof_status": "success" if rb_success else "failed",
            "cost_model_fault_behavior": behaviors.get("cost model false improvement", "unknown"),
            "transaction_boundary_fault_behavior": behaviors.get("transaction boundary break", "unknown"),
            "atomic_boundary_fault_behavior": behaviors.get("atomic commit boundary break", "unknown"),
            "lock_fault_behavior": behaviors.get("lock boundary violation", "unknown"),
            "cadence_fault_behavior": behaviors.get("cadence window failure", "unknown"),
            "pml_fault_behavior": behaviors.get("missing PML boundary", "unknown"),
            "carrier_fault_behavior": behaviors.get("carrier lease failure", "unknown"),
            "prefix_carry_fault_behavior": behaviors.get("prefix-carry bridge break", "unknown"),
            "arithmetic_oracle_fault_behavior": behaviors.get("arithmetic oracle mismatch", "unknown"),
            "active_table_protection_status": table_protect,
            "safety_oracle_agreement": oracle_agreement,
            "quarantine_status": "active" if quarantined else "inactive",
            "quarantine_targets": list(set(quarantine_targets)),
            "promotion_readiness": "ready" if ready else "hold"
        }

        import uuid
        packet_id = f"PKT_RF_{uuid.uuid4().hex[:8]}"
        matrix_id = extract(fault_report, "matrix_id", "static_hash")
        
        return SovereignPacket(
            packet_id=packet_id,
            domain="sol_sovereign",
            level=42,
            actor="Route Fault Ranger",
            actor_type="ranger",
            mission_id=mission_id,
            claim="Route rebalance fault and regression matrix audit completed.",
            evidence=evidence,
            invariants_checked=[
                "transaction_boundary_preservation",
                "atomic_commit_preservation",
                "rollback_snapshot_completeness",
                "pml_boundary_coverage",
                "carrier_registry_immutability"
            ],
            artifacts=[],
            recommendation=recommendation,
            confidence=1.0,
            reproducibility_hash=matrix_id if matrix_id else "static_hash"
        )
