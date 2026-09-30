"""
SOL Diagnostics: sol-lens Telemetry Emitter & Schema Bridge
File: sol/diagnostics/telemetry_emitter.py

Bridges continuous Riemannian manifold states (metric tensor g_ij, Ricci scalar R,
eigenvalue spectrum, dynamic damping gamma) and active Exciton geodesic trajectories
into canonical SolLensPacketV02 JSON telemetry streams consumed by sol-lens.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np


PACKET_SCHEMA_V02 = "techman.sol-lens.proof-packet/v0.2"


@dataclass
class ManifoldNodeTelemetry:
    node_id: str
    label: str
    coords: np.ndarray
    metric_tensor: np.ndarray
    ricci_scalar: float
    attention_heat: float = 0.0
    kinetic_energy: float = 0.0
    damping_gamma: float = 0.05
    is_divergent: bool = False
    is_active_exciton: bool = False
    group_id: Optional[str] = None


class SolLensTelemetryEmitter:
    """
    Synthesizes and emits telemetry packets conforming to sol-lens SolLensPacketV02.
    """
    def __init__(
        self,
        packet_id_prefix: str = "sol-kernel-manifold",
        source_label: str = "SOL Kernel / Ricci Flow"
    ):
        self.packet_id_prefix = packet_id_prefix
        self.source_label = source_label
        self.packet_sequence = 0

    def synthesize_packet(
        self,
        nodes: List[ManifoldNodeTelemetry],
        adjacency_edges: Optional[List[Tuple[str, str, float]]] = None,
        geodesic_flow_edges: Optional[List[Tuple[str, str, float]]] = None,
        candidate_label: str = "SOL Dynamic Metric Engine",
        baseline_label: str = "Reference Euclidean Baseline"
    ) -> Dict[str, Any]:
        """
        Constructs a complete SolLensPacketV02 compliant dictionary.
        """
        self.packet_sequence += 1
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        packet_id = f"{self.packet_id_prefix}-{self.packet_sequence:04d}"

        logons = []
        edge_id_counter = 1
        edges = []

        total_nodes = len(nodes)
        divergent_count = 0

        for idx, node in enumerate(nodes):
            # Compute geometric health measures
            eigenvals = np.linalg.eigvalsh(node.metric_tensor)
            min_ev = float(np.min(eigenvals))
            max_ev = float(np.max(eigenvals))
            cond_num = max_ev / max(min_ev, 1e-8)
            det_g = float(np.linalg.det(node.metric_tensor))

            # Status derivation
            if node.is_divergent or min_ev <= 0 or cond_num > 50.0:
                status = "contradiction"
                divergent_count += 1
            elif node.is_active_exciton:
                status = "inferred"
            else:
                status = "supported"

            # Measure normalization to [0.0, 1.0]
            # rho: Normalized metric density / spatial volume
            raw_rho = 0.5 * (1.0 + np.tanh(det_g - 1.0))
            rho = float(np.clip(raw_rho, 0.05, 0.99))

            # psi: Attention excitation / wavefunction phase
            psi = float(np.clip(node.attention_heat, 0.05, 0.99))

            # pressure: Semantic pressure / kinetic energy strain
            raw_pressure = 0.1 + 0.8 * (1.0 - np.exp(-node.kinetic_energy))
            if status == "contradiction":
                raw_pressure = max(raw_pressure, 0.75)
            pressure = float(np.clip(raw_pressure, 0.05, 0.99))

            # evidence: Stability confidence based on metric condition number
            evidence = float(np.clip(1.0 / (1.0 + 0.05 * np.log1p(cond_num)), 0.1, 0.99))

            detail_str = (
                f"Node {node.node_id} | det(g)={det_g:.3f} | R={node.ricci_scalar:.3f} | "
                f"cond={cond_num:.2f} | gamma={node.damping_gamma:.2f}"
            )

            logon_dict: Dict[str, Any] = {
                "id": node.node_id,
                "label": node.label,
                "status": status,
                "evidence": round(evidence, 3),
                "rho": round(rho, 3),
                "psi": round(psi, 3),
                "pressure": round(pressure, 3),
                "detail": detail_str,
                "source": self.source_label
            }
            if node.group_id:
                logon_dict["group_id"] = node.group_id

            logons.append(logon_dict)

        # Build Graph Adjacency Edges
        if adjacency_edges:
            for u, v, weight in adjacency_edges:
                edges.append({
                    "id": f"E{edge_id_counter:04d}",
                    "from": u,
                    "to": v,
                    "status": "supported",
                    "kind": "constraint",
                    "weight": round(float(np.clip(weight, 0.01, 1.0)), 3),
                    "active": False
                })
                edge_id_counter += 1

        # Build Dynamic Geodesic Flow Edges
        if geodesic_flow_edges:
            for u, v, weight in geodesic_flow_edges:
                edges.append({
                    "id": f"E{edge_id_counter:04d}",
                    "from": u,
                    "to": v,
                    "status": "inferred",
                    "kind": "flow",
                    "weight": round(float(np.clip(weight, 0.01, 1.0)), 3),
                    "active": True
                })
                edge_id_counter += 1

        # Calculate SolMetrics
        contradiction_ratio = divergent_count / max(total_nodes, 1)
        avg_evidence = float(np.mean([lg["evidence"] for lg in logons])) if logons else 0.8
        coherence = round(float(np.clip(1.0 - contradiction_ratio, 0.1, 0.99)), 3)
        continuity = round(float(np.clip(0.98 - 0.5 * contradiction_ratio, 0.1, 0.99)), 3)

        metrics = {
            "evidence": round(avg_evidence, 3),
            "coherence": coherence,
            "contradiction": round(contradiction_ratio, 3),
            "continuity": continuity,
            "authority": 0.92,
            "faithfulness": round(float(np.clip(1.0 - 0.8 * contradiction_ratio, 0.1, 0.99)), 3)
        }

        # Calculate Verdict
        if contradiction_ratio > 0.2:
            verdict = "QUARANTINE"
        elif contradiction_ratio > 0.05:
            verdict = "HOLD"
        else:
            verdict = "PROMOTE"

        # Baseline Evaluation
        baseline_eval = {
            "label": baseline_label,
            "logon_count": total_nodes,
            "source": "Observable baseline metric",
            "metrics": {
                "evidence": 0.80,
                "coherence": 0.75,
                "contradiction": 0.10,
                "continuity": 0.75,
                "authority": 0.85,
                "faithfulness": 0.80
            },
            "verdict": "HOLD"
        }

        packet = {
            "schema": PACKET_SCHEMA_V02,
            "packet_id": packet_id,
            "generated_at": now_iso,
            "observable_trace_only": True,
            "fixture": packet_id,
            "models": {
                "baseline": baseline_label,
                "candidate": candidate_label
            },
            "baseline_evaluation": baseline_eval,
            "logons": logons,
            "edges": edges,
            "metrics": metrics,
            "verdict": verdict
        }

        return packet

    def save_packet(self, packet: Dict[str, Any], filepath: Path | str) -> Path:
        """
        Serializes and writes the packet as UTF-8 JSON.
        """
        p = Path(filepath)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(packet, f, indent=2)
        return p
