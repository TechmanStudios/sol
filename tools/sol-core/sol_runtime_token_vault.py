# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Runtime Token Vault
=======================
Manages sovereign capability tokens authorizing sandbox-mode execution steps.
Production mutation authorization is strictly prohibited.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time

@dataclass
class RuntimeTokenScope:
    allowed_level: int
    allowed_operation: str
    sandbox_scope: str
    allow_production: bool = False

@dataclass
class RuntimeToken:
    token_id: str
    court_authorization_id: Optional[str]
    scope: RuntimeTokenScope
    expires_at: float
    ranger_observer_id: str
    rollback_required: bool = True
    rollback_reference: Optional[str] = None
    active: bool = True
    revocation_reason: Optional[str] = None

@dataclass
class RuntimeTokenLease:
    lease_id: str
    token: RuntimeToken
    issued_at: float = field(default_factory=time.time)

@dataclass
class RuntimeTokenValidationReport:
    validated: bool
    errors: List[str] = field(default_factory=list)


def issue_shadow_token(scope: RuntimeTokenScope) -> RuntimeToken:
    """
    Issues a token valid only for shadow (dry-run) operations.
    """
    if scope.allow_production:
        raise ValueError("Cannot issue token: shadow tokens cannot authorize production mutation.")
        
    import uuid
    t_id = f"TOK_SHADOW_{uuid.uuid4().hex[:8]}"
    return RuntimeToken(
        token_id=t_id,
        court_authorization_id=None,
        scope=scope,
        expires_at=time.time() + 3600.0,
        ranger_observer_id="RNG_SHADOW_OBSERVER",
        rollback_required=False
    )


def validate_runtime_token(token: Optional[RuntimeToken], required_scope: RuntimeTokenScope) -> RuntimeTokenValidationReport:
    """
    Validates token lease status, scope bounds, and expiration constraints.
    """
    errors = []
    if not token:
        errors.append("Invalid or expired court token: token reference is missing.")
        return RuntimeTokenValidationReport(validated=False, errors=errors)
        
    if not token.active:
        errors.append(f"Token has been revoked or deactivated. Reason: {token.revocation_reason}")
        
    if token.expires_at <= time.time():
        errors.append("Token has expired.")
        
    if token.scope.allow_production or required_scope.allow_production:
        errors.append("Production mutation is strictly prohibited by token policies.")
        
    if token.scope.allowed_level < required_scope.allowed_level:
        errors.append(f"Insufficient authorization level: token level {token.scope.allowed_level} < required {required_scope.allowed_level}")
        
    if token.scope.allowed_operation != required_scope.allowed_operation:
        errors.append(f"Operation mismatch: token authorized for {token.scope.allowed_operation}, requested {required_scope.allowed_operation}")
        
    validated = len(errors) == 0
    return RuntimeTokenValidationReport(validated=validated, errors=errors)


def expire_runtime_token(token: RuntimeToken) -> None:
    """
    Forces immediate expiration of a runtime token.
    """
    token.expires_at = time.time() - 10.0


def revoke_runtime_token(token: RuntimeToken, reason: str) -> None:
    """
    Revokes authorization for a runtime token lease.
    """
    token.active = False
    token.revocation_reason = reason
