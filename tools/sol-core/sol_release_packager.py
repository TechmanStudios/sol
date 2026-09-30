# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Release Packager
====================
Assembles and validates metadata-only release packages for Level 49 candidates.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import uuid
import time

@dataclass
class ReleasePackagePolicy:
    allow_production_switches: bool = False
    metadata_only: bool = True

@dataclass
class ReleasePackageArtifact:
    artifact_id: str
    artifact_type: str  # manifest, freeze_report, api_contract, etc.
    payload: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ReleasePackageManifest:
    package_id: str
    candidate_id: str
    artifacts: List[ReleasePackageArtifact] = field(default_factory=list)
    policy: ReleasePackagePolicy = field(default_factory=ReleasePackagePolicy)
    timestamp: float = field(default_factory=time.time)

@dataclass
class ReleasePackageReport:
    report_id: str
    package_manifest: ReleasePackageManifest
    success: bool
    errors: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


def build_release_package_manifest(rc_manifest: Any, freeze_report: Any, api_contract: Any) -> ReleasePackageManifest:
    """
    Constructs a release package manifest from metadata components.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    cand_id_obj = extract(rc_manifest, "candidate_id")
    cand_id = extract(cand_id_obj, "candidate_id", "unknown_candidate") if cand_id_obj else "unknown_candidate"
    
    artifacts = [
        ReleasePackageArtifact(
            artifact_id=f"ART_MAN_{uuid.uuid4().hex[:8]}",
            artifact_type="rc_manifest",
            payload={"candidate_id": cand_id}
        ),
        ReleasePackageArtifact(
            artifact_id=f"ART_FRZ_{uuid.uuid4().hex[:8]}",
            artifact_type="freeze_report",
            payload={"report_id": extract(freeze_report, "report_id")}
        ),
        ReleasePackageArtifact(
            artifact_id=f"ART_CON_{uuid.uuid4().hex[:8]}",
            artifact_type="api_contract",
            payload={"contract_id": extract(api_contract, "contract_id")}
        )
    ]
    
    return ReleasePackageManifest(
        package_id=f"PKG_{uuid.uuid4().hex[:8]}",
        candidate_id=cand_id,
        artifacts=artifacts
    )


def validate_release_package_manifest(package_manifest: ReleasePackageManifest) -> bool:
    """
    Ensures that the release package is metadata-only, with no production-enabling switches.
    """
    if not package_manifest.policy.metadata_only:
        return False
    if package_manifest.policy.allow_production_switches:
        return False
        
    for art in package_manifest.artifacts:
        payload = art.payload
        if payload.get("enable_production") or payload.get("bypass_sovereign_governance") or payload.get("production_switch"):
            return False
            
    return True


def generate_shadow_release_package(package_manifest: ReleasePackageManifest) -> ReleasePackageReport:
    """
    Validates and packs the metadata-only release package. Does not alter runtime behavior.
    """
    valid = validate_release_package_manifest(package_manifest)
    errors = []
    if not valid:
        errors.append("Release package manifest validation failed: package is not metadata-only or contains production switches.")
        
    return ReleasePackageReport(
        report_id=f"PKG_RPT_{uuid.uuid4().hex[:8]}",
        package_manifest=package_manifest,
        success=valid,
        errors=errors
    )
