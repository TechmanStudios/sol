# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Production Gateway
======================
Sealed, default-deny production gateway checks. Production behavior is never activated.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import time
import uuid

@dataclass
class ProductionGatewayId:
    gateway_id: str
    created_at: float = field(default_factory=time.time)

@dataclass
class ProductionGatewayPolicy:
    allow_production_mutation: bool = False
    allow_default_mutation: bool = False
    allowed_modes: list = field(default_factory=lambda: ["shadow", "sandbox"])

@dataclass
class ProductionGatewayRequest:
    request_id: str
    target_operation: str
    payload: Dict[str, Any] = field(default_factory=dict)
    mode: str = "shadow"

@dataclass
class ProductionGatewayAuthorization:
    auth_token: str
    issued_at: float = field(default_factory=time.time)

@dataclass
class ProductionGatewayDecision:
    decision: str  # deny, hold, needs_more_evidence, shadow_only_approved, sandbox_trial_authorized
    justification: str
    timestamp: float = field(default_factory=time.time)

@dataclass
class ProductionGatewayReport:
    report_id: str
    request: ProductionGatewayRequest
    policy: ProductionGatewayPolicy
    decision: ProductionGatewayDecision
    timestamp: float = field(default_factory=time.time)


def build_production_gateway(policy: ProductionGatewayPolicy) -> ProductionGatewayReport:
    """
    Builds a baseline gateway report.
    """
    req = ProductionGatewayRequest(
        request_id=f"REQ_INIT_{uuid.uuid4().hex[:8]}",
        target_operation="initialize_gateway"
    )
    dec = ProductionGatewayDecision(
        decision="deny",
        justification="Baseline initialization."
    )
    return ProductionGatewayReport(
        report_id=f"GW_RPT_{uuid.uuid4().hex[:8]}",
        request=req,
        policy=policy,
        decision=dec
    )


def validate_production_gateway_policy(policy: ProductionGatewayPolicy) -> bool:
    """
    Validates that the gateway policy remains default-deny.
    """
    if policy.allow_production_mutation or policy.allow_default_mutation:
        return False
    if "production" in policy.allowed_modes:
        return False
    return True


def evaluate_production_gateway_request(
    request: ProductionGatewayRequest,
    policy: ProductionGatewayPolicy
) -> ProductionGatewayDecision:
    """
    Evaluates gateway request. Any production or default mutation request is denied.
    """
    if not validate_production_gateway_policy(policy):
        return ProductionGatewayDecision(
            decision="deny",
            justification="Gateway policy is invalid; must be default-deny."
        )

    payload = request.payload or {}
    mutate_prod = payload.get("production_execution") or payload.get("mutate_default") or payload.get("enable_production")
    overwrite_active = payload.get("overwrite_active") or payload.get("mutate_active_profiles") or payload.get("overwrite_active_cadence")
    
    if request.mode == "production" or mutate_prod or overwrite_active:
        return ProductionGatewayDecision(
            decision="deny",
            justification="Production mutation and active parameter overwrite requests are strictly denied."
        )

    if request.mode == "sandbox":
        token = payload.get("court_token")
        if not token or token == "INVALID_TOKEN":
            return ProductionGatewayDecision(
                decision="needs_more_evidence",
                justification="Sandbox execution requires a valid court token."
            )
        return ProductionGatewayDecision(
            decision="sandbox_trial_authorized",
            justification="Sandbox execution request authorized under court token."
        )

    if request.mode == "shadow":
        return ProductionGatewayDecision(
            decision="shadow_only_approved",
            justification="Shadow execution request authorized."
        )

    return ProductionGatewayDecision(
        decision="hold",
        justification="Request held for unknown configuration mode."
    )


def execute_shadow_production_gateway_check(
    request: ProductionGatewayRequest,
    policy: ProductionGatewayPolicy
) -> ProductionGatewayReport:
    """
    Executes a shadow production gateway check.
    """
    decision = evaluate_production_gateway_request(request, policy)
    return ProductionGatewayReport(
        report_id=f"GW_VAL_{uuid.uuid4().hex[:8]}",
        request=request,
        policy=policy,
        decision=decision
    )


def summarize_production_gateway_report(report: ProductionGatewayReport) -> Dict[str, Any]:
    """
    Returns summary stats for the production gateway check.
    """
    return {
        "report_id": report.report_id,
        "request_id": report.request.request_id,
        "target_operation": report.request.target_operation,
        "decision": report.decision.decision,
        "justification": report.decision.justification
    }
