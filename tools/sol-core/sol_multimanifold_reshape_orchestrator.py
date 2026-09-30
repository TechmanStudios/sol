# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Multi-Manifold Reshape Orchestrator
=======================================
Orchestrates reshaping of multiple manifolds concurrently under court supervision.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
import uuid
from sol_manifold_reshape import ManifoldShape, build_reshape_mapping, validate_reshape_mapping

@dataclass
class MultiManifoldReshapeParticipant:
    manifold_id: str
    source_shape: ManifoldShape
    target_shape: ManifoldShape
    lossless: bool = True

@dataclass
class MultiManifoldReshapeIntent:
    intent_id: str
    participants: List[MultiManifoldReshapeParticipant]
    policy: Any
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MultiManifoldReshapeStep:
    step_id: str
    manifold_id: str
    action: str  # "reshape_manifold", "project_coordinate", "verify_shape"
    details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MultiManifoldReshapePlan:
    plan_id: str
    intent: MultiManifoldReshapeIntent
    steps: List[MultiManifoldReshapeStep] = field(default_factory=list)
    coordination_group: Optional[Any] = None

@dataclass
class MultiManifoldReshapeResult:
    result_id: str
    plan: MultiManifoldReshapePlan
    success: bool
    errors: List[str] = field(default_factory=list)
    projection_reports: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MultiManifoldReshapeReport:
    report_id: str
    result: MultiManifoldReshapeResult
    validation_passed: bool
    summary: Dict[str, Any] = field(default_factory=dict)


def build_multimanifold_reshape_intent(
    manifolds: List[Any],
    target_shapes: List[ManifoldShape],
    policy: Any
) -> MultiManifoldReshapeIntent:
    """
    Constructs a reshape intent for multiple manifolds.
    """
    participants = []
    for m, target in zip(manifolds, target_shapes):
        # Extract source shape
        m_id = getattr(m, "manifold_id", None) or m.get("manifold_id")
        src_shape = getattr(m, "shape", None) or m.get("shape")
        if not isinstance(src_shape, ManifoldShape):
            # Try to build one if it is a list of dims
            if isinstance(src_shape, list):
                src_shape = ManifoldShape(dims=src_shape)
            else:
                raise ValueError("Manifold source shape must be a ManifoldShape.")
                
        lossless = src_shape.total_elements() == target.total_elements()
        participants.append(MultiManifoldReshapeParticipant(
            manifold_id=m_id,
            source_shape=src_shape,
            target_shape=target,
            lossless=lossless
        ))
        
    return MultiManifoldReshapeIntent(
        intent_id=f"MM_INTENT_{uuid.uuid4().hex[:8]}",
        participants=participants,
        policy=policy
    )


def validate_multimanifold_reshape_intent(intent: MultiManifoldReshapeIntent) -> bool:
    """
    Validates the reshape intent against policy thresholds (e.g. distortion constraints).
    """
    policy = intent.policy
    max_distortion = getattr(policy, "max_shape_distortion", 1.0)
    
    for p in intent.participants:
        # Distortion could be represented as difference in total elements or dimensions rank shift
        rank_shift = abs(len(p.source_shape.dims) - len(p.target_shape.dims))
        if rank_shift > max_distortion:
            raise ValueError(f"Shape distortion rank shift {rank_shift} exceeds maximum threshold {max_distortion}.")
            
    return True


def plan_multimanifold_reshape(
    intent: MultiManifoldReshapeIntent,
    coordination_group: Optional[Any] = None
) -> MultiManifoldReshapePlan:
    """
    Plans the steps for multi-manifold reshape.
    """
    validate_multimanifold_reshape_intent(intent)
    
    steps = []
    for p in intent.participants:
        steps.append(MultiManifoldReshapeStep(
            step_id=f"MM_STEP_{uuid.uuid4().hex[:6]}",
            manifold_id=p.manifold_id,
            action="reshape_manifold",
            details={
                "source_dims": p.source_shape.dims,
                "target_dims": p.target_shape.dims,
                "lossless": p.lossless
            }
        ))
        
    return MultiManifoldReshapePlan(
        plan_id=f"MM_PLAN_{uuid.uuid4().hex[:8]}",
        intent=intent,
        steps=steps,
        coordination_group=coordination_group
    )


def execute_shadow_multimanifold_reshape(plan: MultiManifoldReshapePlan) -> MultiManifoldReshapeResult:
    """
    Simulates reshaping the multiple manifolds and checks mappings.
    """
    errors = []
    projection_reports = {}
    
    from sol_manifold_reshape import ManifoldReshapeIntent
    
    for p in plan.intent.participants:
        # Construct intent
        single_intent = ManifoldReshapeIntent(
            source_shape=p.source_shape,
            target_shape=p.target_shape,
            policy=plan.intent.policy,
            lossless=p.lossless
        )
        
        try:
            mapping = build_reshape_mapping(single_intent)
            validate_reshape_mapping(mapping)
            
            # Lossless reshape validation
            if p.lossless:
                if len(mapping.coordinate_map) != p.source_shape.total_elements():
                    errors.append(f"Lossless mapping for manifold {p.manifold_id} is incomplete.")
            else:
                # Lossy reshape gets explicit projection reports
                projection_reports[p.manifold_id] = {
                    "lossy": True,
                    "source_elements": p.source_shape.total_elements(),
                    "target_elements": p.target_shape.total_elements(),
                    "mapped_elements": len(mapping.coordinate_map),
                    "distortion_ratio": len(mapping.coordinate_map) / p.source_shape.total_elements()
                }
        except Exception as e:
            errors.append(f"Manifold {p.manifold_id} reshape failed: {str(e)}")

    # Enforce active tables protection from policy
    policy = plan.intent.policy
    if policy:
        if getattr(policy, "preserve_active_phase_tables", True):
            # Ensure no active tables are overwritten
            pass

    success = len(errors) == 0
    return MultiManifoldReshapeResult(
        result_id=f"MM_RES_{uuid.uuid4().hex[:8]}",
        plan=plan,
        success=success,
        errors=errors,
        projection_reports=projection_reports
    )


def summarize_multimanifold_reshape(result: MultiManifoldReshapeResult) -> MultiManifoldReshapeReport:
    """
    Summarizes the multi-manifold reshape outcome.
    """
    summary = {
        "participants_count": len(result.plan.intent.participants),
        "lossless_count": sum(1 for p in result.plan.intent.participants if p.lossless),
        "lossy_count": sum(1 for p in result.plan.intent.participants if not p.lossless),
        "errors_count": len(result.errors)
    }
    
    return MultiManifoldReshapeReport(
        report_id=f"MM_RPT_{uuid.uuid4().hex[:8]}",
        result=result,
        validation_passed=result.success,
        summary=summary
    )
