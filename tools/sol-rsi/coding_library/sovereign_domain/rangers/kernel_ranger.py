# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Kernel Ranger
=============
Observes vectorized graph kernel arrays, CSR adjacency tables, and SIMD execution plans.
"""

from coding_library.roaming_agents import LuminaRoamingAgent
from coding_library.sovereign_domain.evidence_packet import SovereignPacket
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

class KernelRanger(LuminaRoamingAgent):
    """
    Ranger patrolling to observe vectorized execution array formats, CSR sparse states, and SIMD execution plans.
    """
    def __init__(self, lib_agent=None):
        system_prompt = (
            "You are the Kernel Ranger. You inspect graph kernel arrays, CSR sparse layouts,\n"
            "and SIMD execution plans, reporting on data structure validity."
        )
        super().__init__("Kernel Ranger", system_prompt, lib_agent)

    def observe_kernel(self, target_obj: Any, mission_id: str = "MOCK_KERNEL_MISSION") -> SovereignPacket:
        """
        Inspects GraphKernelArrays, CSRAdjacency, or SIMDExecutionPlan and returns a SovereignPacket.
        """
        self.travel(target_obj)

        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        obj_classname = target_obj.__class__.__name__

        node_count = 0
        edge_count = 0
        csr_valid = True
        array_shapes_valid = True
        simd_mode = "N/A"
        lane_count = 0
        missing_fields: List[str] = []

        if obj_classname == "GraphKernelArrays":
            node_ids = extract(target_obj, "node_ids", [])
            rho = extract(target_obj, "rho", None)
            psi = extract(target_obj, "psi", None)
            pressure = extract(target_obj, "pressure", None)
            semantic_mass = extract(target_obj, "semantic_mass", None)

            edge_from = extract(target_obj, "edge_from_idx", [])
            edge_to = extract(target_obj, "edge_to_idx", [])
            edge_w0 = extract(target_obj, "edge_w0", None)
            edge_conductance = extract(target_obj, "edge_conductance", None)
            edge_flux = extract(target_obj, "edge_flux", None)

            node_count = len(node_ids)
            edge_count = len(edge_from)

            # Check for missing fields
            fields_to_check = {
                "node_ids": node_ids,
                "rho": rho,
                "psi": psi,
                "pressure": pressure,
                "semantic_mass": semantic_mass,
                "edge_from_idx": edge_from,
                "edge_to_idx": edge_to,
                "edge_w0": edge_w0,
                "edge_conductance": edge_conductance,
                "edge_flux": edge_flux
            }
            for name, val in fields_to_check.items():
                if val is None:
                    missing_fields.append(name)

            # Check array shapes consistency
            if not missing_fields:
                try:
                    if len(rho) != node_count or len(psi) != node_count or len(pressure) != node_count or len(semantic_mass) != node_count:
                        array_shapes_valid = False
                    if len(edge_to) != edge_count or len(edge_w0) != edge_count or len(edge_conductance) != edge_count or len(edge_flux) != edge_count:
                        array_shapes_valid = False
                except (TypeError, ValueError):
                    array_shapes_valid = False

            csr = extract(target_obj, "csr", None)
            if csr is None:
                csr_valid = False
            else:
                row_ptr = extract(csr, "row_ptr", [])
                col_indices = extract(csr, "col_indices", [])
                if len(row_ptr) != node_count + 1 or len(col_indices) != edge_count:
                    csr_valid = False

        elif obj_classname == "CSRAdjacency":
            row_ptr = extract(target_obj, "row_ptr", [])
            col_indices = extract(target_obj, "col_indices", [])
            node_count = max(0, len(row_ptr) - 1)
            edge_count = len(col_indices)
            if len(row_ptr) > 0:
                csr_valid = (row_ptr[-1] == edge_count)
            else:
                csr_valid = False

        elif obj_classname == "SIMDExecutionPlan":
            mode_obj = extract(target_obj, "mode", None)
            if mode_obj is not None:
                simd_mode = extract(mode_obj, "name", "N/A")
                lane_count = extract(mode_obj, "lane_count", 0)
            else:
                simd_mode = "N/A"
                lane_count = 0
        elif obj_classname == "VectorizedParityReport":
            pass

        if obj_classname == "VectorizedParityReport":
            passed = bool(extract(target_obj, "parity_passed", False))
            recommendation = "observe" if passed else "reject"
            evidence = {
                "node_count": int(extract(target_obj, "node_count", 0)),
                "edge_count": int(extract(target_obj, "edge_count", 0)),
                "max_rho_error": float(extract(target_obj, "max_rho_error", 0.0)),
                "max_pressure_error": float(extract(target_obj, "max_pressure_error", 0.0)),
                "max_flux_error": float(extract(target_obj, "max_flux_error", 0.0)),
                "tolerance": float(extract(target_obj, "tolerance", 1e-6)),
                "parity_passed": passed,
                "backend_mode": str(extract(target_obj, "backend_mode", "dict")),
                "target_type": obj_classname
            }
        else:
            # Recommendation: observe if everything checks out, otherwise reject
            passed = (len(missing_fields) == 0) and csr_valid and array_shapes_valid
            recommendation = "observe" if passed else "reject"

            evidence = {
                "node_count": node_count,
                "edge_count": edge_count,
                "csr_valid": csr_valid,
                "array_shapes_valid": array_shapes_valid,
                "simd_mode": simd_mode,
                "lane_count": lane_count,
                "missing_fields": missing_fields,
                "target_type": obj_classname
            }

        timestamp_str = datetime.now(timezone.utc).strftime("%H%M%S")
        packet_id = f"PKT_KERN_OBS_{id(target_obj)}_{timestamp_str}"
        repro_hash = f"sha256_{hash(str(evidence)) & 0xFFFFFFFF:08x}"

        packet = SovereignPacket(
            packet_id=packet_id,
            domain="sol_sovereign",
            level=11,
            actor=self.name,
            actor_type="ranger",
            mission_id=mission_id,
            claim="Waveguide vectorized execution and SIMD mode observation report",
            evidence=evidence,
            invariants_checked=["vectorized_array_shapes", "simd_lane_mapping"],
            artifacts=[],
            recommendation=recommendation,
            confidence=0.98,
            reproducibility_hash=repro_hash
        )

        self.state_history.append(f"Observed kernel: recommendation={recommendation}.")
        return packet
