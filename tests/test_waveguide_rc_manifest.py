# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Tests for SOL Waveguide Release Candidate Manifest and Documentation Consistency
"""

import os
import json
import pytest
from sol_waveguide_rc_manifest import (
    build_waveguide_rc_manifest,
    summarize_waveguide_rc_manifest,
    validate_waveguide_rc_manifest_consistency
)

# 1. Manifest builds successfully
def test_manifest_builds_successfully():
    manifest = build_waveguide_rc_manifest()
    assert manifest is not None
    assert isinstance(manifest, dict)

# 2. Manifest names the strict backend
def test_manifest_names_strict_backend():
    manifest = build_waveguide_rc_manifest()
    assert manifest.get("backend") == "pdm_waveguide_microcoded_strict"

# 3. Manifest reports Micro-ISA v0 compliance separately from v1 extension status
def test_manifest_separates_compliance_and_extensions():
    manifest = build_waveguide_rc_manifest()
    assert "micro_isa_v0_compliance" in manifest
    assert "micro_isa_v1_extension_status" in manifest
    assert manifest.get("micro_isa_v0_compliance") == "full_compliance"
    assert manifest.get("micro_isa_v1_extension_status") == "candidate_compliant"

# 4. Manifest includes canonical optimization profiles
def test_manifest_includes_profiles():
    manifest = build_waveguide_rc_manifest()
    profiles = manifest.get("optimization_profiles", [])
    expected = [
        "RAW_STRICT", "SAFE_LOCAL", "SAFE_CONTROL", "SAFE_MEMORY",
        "FULL_SAFE_OPTIMIZED", "BENCHMARK_MATRIX", "DEBUG_TRACE_AUDIT",
        "V1_CANDIDATE_EXPERIMENTAL", "COST_MODEL_DEBUG", "AUTOTUNE_SAFE",
        "AUTOTUNE_LOWEST_CYCLES", "KERNEL_AUTOTUNE_SAFE"
    ]
    for p in expected:
        assert p in profiles

# 5. Manifest includes canonical pass order
def test_manifest_includes_canonical_pass_order():
    manifest = build_waveguide_rc_manifest()
    pass_order = manifest.get("canonical_pass_order", [])
    expected = [
        "program_adaptation",
        "v1_candidate_lowering",
        "memory_alias_analysis",
        "channel_dependency_analysis",
        "channel_kernel_recognition",
        "branch_predication",
        "pipeline_compaction",
        "scoreboard_scheduling",
        "execution_plan_validation",
        "cost_model_evaluation",
        "deterministic_policy_selection",
        "trace_metadata_preparation"
    ]
    assert len(pass_order) == len(expected)
    for p in expected:
        assert p in pass_order

# 6. Manifest lists v1 candidates and unsupported channel candidates
def test_manifest_lists_v1_candidates():
    manifest = build_waveguide_rc_manifest()
    v1_sum = manifest.get("v1_candidate_summary", {})
    supported = v1_sum.get("supported_candidates", [])
    unsupported = v1_sum.get("unsupported_candidates", [])
    
    assert "SELECT" in supported
    assert "WG_CHAN_FENCE" in supported
    assert "WG_CHAN_SEND" in unsupported
    assert "WG_CHAN_RECV" in unsupported
    assert "WG_CHAN_ROUTE" in unsupported
    assert "PSTORE_WO" in unsupported

# 7. Manifest includes sandbox caveat
def test_manifest_includes_sandbox_caveat():
    manifest = build_waveguide_rc_manifest()
    caveat = manifest.get("sandbox_caveat", "")
    assert "sandbox" in caveat.lower()
    assert "software-simulated" in caveat.lower()
    assert "no physical" in caveat.lower()

# 8. Manifest JSON is serializable
def test_manifest_json_serializable():
    manifest = build_waveguide_rc_manifest()
    # Should serialize without error
    serialized = json.dumps(manifest)
    deserialized = json.loads(serialized)
    assert deserialized["rc_id"] == manifest["rc_id"]

# 9 & 10. Dossier and proof ledger docs exist
def test_rc_documentation_files_exist():
    workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    docs_dir = os.path.join(workspace_dir, "docs")
    
    dossier1 = os.path.join(docs_dir, "SOL_WAVEGUIDE_OPTIMIZATION_RESEARCH_DOSSIER_RC1.md")
    ledger1 = os.path.join(docs_dir, "SOL_WAVEGUIDE_PROOF_LEDGER_RC1.md")
    map1 = os.path.join(docs_dir, "SOL_WAVEGUIDE_ARCHITECTURE_MAP_RC1.md")
    manifest1 = os.path.join(docs_dir, "SOL_WAVEGUIDE_RC1_MANIFEST.json")
    
    dossier2 = os.path.join(docs_dir, "SOL_WAVEGUIDE_OPTIMIZATION_RESEARCH_DOSSIER_RC2.md")
    ledger2 = os.path.join(docs_dir, "SOL_WAVEGUIDE_PROOF_LEDGER_RC2.md")
    map2 = os.path.join(docs_dir, "SOL_WAVEGUIDE_ARCHITECTURE_MAP_RC2.md")
    manifest2 = os.path.join(docs_dir, "SOL_WAVEGUIDE_RC2_MANIFEST.json")
    
    for path in (dossier1, ledger1, map1, manifest1, dossier2, ledger2, map2, manifest2):
        assert os.path.exists(path), f"Required documentation file is missing: {path}"

# 11. Consistency validator check
def test_manifest_consistency_validation():
    manifest = build_waveguide_rc_manifest()
    assert validate_waveguide_rc_manifest_consistency(manifest) is True
    
    # Check falsification: bad backend name
    bad_manifest = dict(manifest)
    bad_manifest["backend"] = "invalid_backend"
    with pytest.raises(ValueError, match="Invalid backend name"):
        validate_waveguide_rc_manifest_consistency(bad_manifest)
        
    # Check falsification: bad compliance
    bad_compliance = dict(manifest)
    bad_compliance["micro_isa_v0_compliance"] = "partial_compliance"
    with pytest.raises(ValueError, match="Backend compliance level must be"):
        validate_waveguide_rc_manifest_consistency(bad_compliance)

# 12. RC1 vs RC2 dynamic split verification
def test_manifest_rc1_rc2_split():
    # Test RC1 contents
    rc1 = build_waveguide_rc_manifest("SOL-WAVEGUIDE-RC1")
    assert rc1["rc_id"] == "SOL-WAVEGUIDE-RC1"
    assert "cost_model_and_autotuning" not in rc1
    assert "COST_MODEL_DEBUG" not in rc1["optimization_profiles"]
    assert "AUTOTUNE_SAFE" not in rc1["optimization_profiles"]
    assert "cost_model_evaluation" not in rc1["canonical_pass_order"]
    assert "deterministic_policy_selection" not in rc1["canonical_pass_order"]
    assert validate_waveguide_rc_manifest_consistency(rc1) is True

    # Test RC2 contents
    rc2 = build_waveguide_rc_manifest("SOL-WAVEGUIDE-RC2")
    assert rc2["rc_id"] == "SOL-WAVEGUIDE-RC2"
    assert "cost_model_and_autotuning" in rc2
    assert "COST_MODEL_DEBUG" in rc2["optimization_profiles"]
    assert "AUTOTUNE_SAFE" in rc2["optimization_profiles"]
    assert "cost_model_evaluation" in rc2["canonical_pass_order"]
    assert "deterministic_policy_selection" in rc2["canonical_pass_order"]
    assert validate_waveguide_rc_manifest_consistency(rc2) is True
