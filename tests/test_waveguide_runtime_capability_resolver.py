# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Tests for SOL Waveguide Runtime Capability Resolver
"""

import os
import json
import pytest

from sol_waveguide_rc_manifest import build_waveguide_rc_manifest
from sol_waveguide_runtime_capability_resolver import (
    build_waveguide_runtime_capability_request,
    resolve_waveguide_runtime_capabilities,
    validate_waveguide_runtime_capability_resolution,
    summarize_waveguide_runtime_capability_resolution,
    export_waveguide_runtime_capability_resolution,
    compare_waveguide_runtime_capability_resolutions,
    hash_waveguide_runtime_capability_request,
    hash_waveguide_runtime_capability_resolution
)


def test_capability_request_build():
    req1 = build_waveguide_runtime_capability_request("SOL-WAVEGUIDE-RC1")
    req2 = build_waveguide_runtime_capability_request("SOL-WAVEGUIDE-RC2")

    assert req1 is not None
    assert req2 is not None
    assert req1.rc_id == "SOL-WAVEGUIDE-RC1"
    assert req2.rc_id == "SOL-WAVEGUIDE-RC2"


def test_request_digest_excludes_self():
    req = build_waveguide_runtime_capability_request("SOL-WAVEGUIDE-RC1")
    req_dict = req.__dict__.copy()
    req_dict["request_digest"] = "different_request_digest_value"

    h1 = hash_waveguide_runtime_capability_request(req)
    h2 = hash_waveguide_runtime_capability_request(req_dict)
    assert h1 == h2


def test_resolution_digest_excludes_self():
    req = build_waveguide_runtime_capability_request("SOL-WAVEGUIDE-RC1")
    res = resolve_waveguide_runtime_capabilities(req)

    res_dict = res.__dict__.copy()
    res_dict["resolution_digest"] = "different_resolution_digest_value"

    h1 = hash_waveguide_runtime_capability_resolution(res)
    h2 = hash_waveguide_runtime_capability_resolution(res_dict)
    assert h1 == h2


def test_rc1_resolves_to_foundation_policy():
    req = build_waveguide_runtime_capability_request("SOL-WAVEGUIDE-RC1")
    res = resolve_waveguide_runtime_capabilities(req)

    assert res.capability_status == "capability_resolved"
    assert res.candidate_level == "foundation"
    assert res.governed_stack_enabled is False
    assert res.cost_model_enabled is False
    assert res.autotuning_enabled is False
    assert res.kernel_recognition_enabled is False
    assert res.deterministic_policy_selection_enabled is False

    # Check disallowed profiles and passes
    assert "COST_MODEL_DEBUG" in res.disallowed_profiles
    assert "channel_kernel_recognition" in res.disallowed_passes
    assert "COST_MODEL_DEBUG" not in res.allowed_profiles
    assert "channel_kernel_recognition" not in res.allowed_passes


def test_rc2_resolves_to_governed_stack_policy():
    req = build_waveguide_runtime_capability_request("SOL-WAVEGUIDE-RC2")
    res = resolve_waveguide_runtime_capabilities(req)

    assert res.capability_status == "capability_resolved"
    assert res.candidate_level == "governed_execution_stack"
    assert res.governed_stack_enabled is True
    assert res.cost_model_enabled is True
    assert res.autotuning_enabled is True
    assert res.kernel_recognition_enabled is True
    assert res.deterministic_policy_selection_enabled is True

    # Check allowed profiles and passes
    assert "COST_MODEL_DEBUG" in res.allowed_profiles
    assert "channel_kernel_recognition" in res.allowed_passes
    assert "COST_MODEL_DEBUG" not in res.disallowed_profiles
    assert "channel_kernel_recognition" not in res.disallowed_passes


def test_prohibitions_enforced_on_both():
    for rc_id in ("SOL-WAVEGUIDE-RC1", "SOL-WAVEGUIDE-RC2"):
        req = build_waveguide_runtime_capability_request(rc_id)
        res = resolve_waveguide_runtime_capabilities(req)

        assert res.strict_waveguide_required is True
        assert res.lane_fabric_fallback_allowed is False
        assert res.hybrid_execution_allowed is False
        assert res.production_mutation_allowed is False


def test_unapproved_rc_returns_blocked():
    req = build_waveguide_runtime_capability_request("SOL-WAVEGUIDE-UNAPPROVED")
    res = resolve_waveguide_runtime_capabilities(req)

    assert res.capability_status == "capability_blocked"
    assert "RUNTIME_CAPABILITY_BLOCKED" in res.reason_codes
    assert "RUNTIME_CAPABILITY_RC_NOT_APPROVED" in res.reason_codes


def test_resolution_validation_works():
    req = build_waveguide_runtime_capability_request("SOL-WAVEGUIDE-RC1")
    res = resolve_waveguide_runtime_capabilities(req)

    ok, reasons = validate_waveguide_runtime_capability_resolution(res)
    assert ok is True
    assert "RUNTIME_CAPABILITY_RESOLUTION_DIGEST_VALID" in reasons
    assert "RUNTIME_CAPABILITY_FOUNDATION_POLICY_SELECTED" in reasons


def test_summarize_and_compare_are_deterministic():
    req = build_waveguide_runtime_capability_request("SOL-WAVEGUIDE-RC1")
    res1 = resolve_waveguide_runtime_capabilities(req)
    res2 = resolve_waveguide_runtime_capabilities(req)

    s1 = summarize_waveguide_runtime_capability_resolution(res1)
    s2 = summarize_waveguide_runtime_capability_resolution(res2)
    assert s1 == s2

    diff = compare_waveguide_runtime_capability_resolutions(res1, res2)
    assert len(diff) == 0


def test_artifacts_exist_on_disk():
    from sol_waveguide_runtime_capability_resolver import REPO_ROOT

    rc1_json = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RUNTIME_CAPABILITY_RESOLVER_RC1.json")
    rc2_json = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RUNTIME_CAPABILITY_RESOLVER_RC2.json")
    doc_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RUNTIME_CAPABILITY_RESOLVER.md")

    assert os.path.exists(rc1_json)
    assert os.path.exists(rc2_json)
    assert os.path.exists(doc_path)
