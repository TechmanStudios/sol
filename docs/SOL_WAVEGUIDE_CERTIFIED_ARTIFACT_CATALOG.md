# SOL Waveguide Certified Artifact Catalog / Distribution Package Index

## 1. Purpose

The `SOL Waveguide Certified Artifact Catalog / Distribution Package Index` is a deterministic inventory layer designed to establish a stable bridge between distribution readiness audit verification and a future packaging plan:

```text
Publication Manifest Validator / Distribution Readiness Auditor
→ Certified Artifact Catalog / Distribution Package Index (This Module)
→ future Distribution Package Assembly Plan
```

It consumes the `SOL Waveguide Distribution Readiness Audit Report`, validates its integrity, and builds a catalog of repository files, JSON proof capsules, and markdown documentation files that are safe to include in a subsequent distribution package.

This layer is strictly an **inventory layer**; it does not compile code, package archives (ZIP/tarball), upload binaries, mutate live production state, sign packages externally, or deploy software.

---

## 2. Architectural Boundaries & Rules

To maintain high security and deterministic trace verification:
* **Sandbox Verification**: All file checks operate under local shadow/sandbox assumptions (software-level checks only).
* **Metadata-Only Allowed Channels**: Only metadata and documentation channels are marked as allowed.
* **Forbidden Channels Blocked**: All channels representing external cryptographic signing, live production deployment, or legal claims remain blocked.
* **Classification Separation**: Artifacts are classified into four distinct types (`json_proof_capsule`, `markdown_documentation`, `python_module`, `pytest_suite`) and assigned roles (`release_governance_proof`, `compiler_governance_proof`, `implementation_source`, `test_source`, `documentation`).
* **Self-Referential Pending State**: The catalog documents its own target path (`docs/SOL_WAVEGUIDE_CERTIFIED_ARTIFACT_CATALOG.json` and `docs/SOL_WAVEGUIDE_CERTIFIED_ARTIFACT_CATALOG.md`). Before generation, these are tracked as `artifact_distribution_pending`.

---

## 3. Data Models

### Artifact Catalog Entry Schema
Each entry inventories a specific file within the repository, validating its on-disk size, path, digest, and scope:

```json
{
  "artifact_catalog_entry_id": "SOL-WAVEGUIDE-ARTIFACT-SOL_WAVEGUIDE_RC1_MANIFEST_json",
  "artifact_path": "docs/SOL_WAVEGUIDE_RC1_MANIFEST.json",
  "artifact_name": "SOL_WAVEGUIDE_RC1_MANIFEST.json",
  "artifact_type": "release_manifest",
  "artifact_format": "json",
  "rc_scope": "RC1",
  "candidate_level": "Foundation",
  "package_role": "release_governance_proof",
  "distribution_status": "artifact_distribution_ready",
  "artifact_digest": "4cb8b9c8b3d6d5ef66432ab870bc1b9131cb5d3f04e0773a1f071a2c0c7b915bee",
  "artifact_size_bytes": 4056,
  "source_distribution_audit_report_digest": "ae5e683fef32a49aa09b75ae12972a81ee8b882fe91c33e597822020b06907df",
  "source_publication_manifest_digest": "c35971e704ba433259d7c5246921a14702ec529cfc385ef58433c17dae3cd480",
  "source_audit_registry_digest": "4802a42b80b2739da7a06b82a8d73a9c541f655f573bdd8342e6521daf2748f4",
  "related_rc_ids": ["SOL-WAVEGUIDE-RC1"],
  "related_bundle_digests": ["1902c9e2034e2f77f979a32eef5fbf4de68e0eed00c84d375ffa7c54715a21f6"],
  "related_audit_report_digests": ["f7724b0ee9b3871e6767489e0be43dc7b74a437b0fab22985dfb60bdc9f259ed"],
  "related_audit_case_digests": ["8947628ea46a9da8fef4162adca7cf652fb33ed8eb09260b919bea83960d8e8e"],
  "allowed_distribution_channels": [
    "artifact_catalog_publication",
    "documentation_publication",
    "internal_distribution"
  ],
  "blocked_distribution_channels": [
    "external_key_signing",
    "legal_certification_claim",
    "production_deployment",
    "quantum_hardware_certification"
  ],
  "is_required_for_distribution_package": true,
  "is_proof_artifact": true,
  "is_documentation_artifact": false,
  "is_code_artifact": false,
  "is_deployment_artifact": false,
  "is_signing_artifact": false,
  "reason_codes": [
    "ARTIFACT_CATALOG_ARTIFACT_DIGEST_MATCH",
    "ARTIFACT_CATALOG_ARTIFACT_EXISTS",
    "ARTIFACT_CATALOG_DISTRIBUTION_READY",
    "ARTIFACT_CATALOG_ENTRY_CANONICAL",
    "ARTIFACT_CATALOG_FORBIDDEN_CHANNELS_BLOCKED",
    "ARTIFACT_CATALOG_JSON_PROOF_INCLUDED",
    "ARTIFACT_CATALOG_SOFTWARE_CAVEAT_INCLUDED"
  ],
  "notes": [],
  "software_validation_caveat": "Validation is shadow/sandbox software validation, not quantum hardware validation.",
  "artifact_catalog_entry_digest": "782f9ee804c8f25b994721ecaf1b9131cb5d3f04e0773a1f071a2c0c7b915bee"
}
```

### Top-Level Artifact Catalog Schema
The top-level catalog groups all entries, aggregates metadata indexes, builds a sorted package inventory list, and hashes its canonical representation:

```json
{
  "artifact_catalog_id": "SOL-WAVEGUIDE-CERTIFIED-ARTIFACT-CATALOG",
  "artifact_catalog_version": 1,
  "artifact_catalog_status": "artifact_catalog_valid",
  "source_distribution_audit_report_digest": "ae5e683fef32a49aa09b75ae12972a81ee8b882fe91c33e597822020b06907df",
  "source_publication_manifest_digest": "c35971e704ba433259d7c5246921a14702ec529cfc385ef58433c17dae3cd480",
  "source_audit_registry_digest": "4802a42b80b2739da7a06b82a8d73a9c541f655f573bdd8342e6521daf2748f4",
  "entries": [ ... ],
  "distribution_ready_artifacts": [ ... ],
  "blocked_artifacts": [],
  "pending_artifacts": [
    "docs/SOL_WAVEGUIDE_CERTIFIED_ARTIFACT_CATALOG.json",
    "docs/SOL_WAVEGUIDE_CERTIFIED_ARTIFACT_CATALOG.md"
  ],
  "invalid_artifacts": [],
  "distribution_ready_artifact_count": 26,
  "blocked_artifact_count": 0,
  "pending_artifact_count": 2,
  "invalid_artifact_count": 0,
  "rc1_artifact_count": 6,
  "rc2_artifact_count": 6,
  "shared_artifact_count": 16,
  "artifact_types_indexed": [
    "audit_report",
    "certification_bundle",
    "documentation_index",
    "json_proof_capsule",
    "markdown_documentation",
    "pytest_suite",
    "python_module",
    "registry_index",
    "release_manifest"
  ],
  "artifact_formats_indexed": ["json", "markdown", "python"],
  "package_roles_indexed": [
    "audit_verification_proof",
    "compiler_governance_proof",
    "documentation",
    "implementation_source",
    "publication_readiness_proof",
    "release_governance_proof",
    "test_source"
  ],
  "rc_scopes_indexed": ["RC1", "RC2", "Shared"],
  "artifact_paths_indexed": [ ... ],
  "artifact_digests_indexed": [ ... ],
  "documentation_artifact_paths": [ ... ],
  "proof_artifact_paths": [ ... ],
  "code_artifact_paths": [ ... ],
  "test_artifact_paths": [ ... ],
  "distribution_package_inventory": [
    {
      "inventory_index": 1,
      "artifact_path": "docs/SOL_WAVEGUIDE_CERTIFIED_ARTIFACT_CATALOG.json",
      "artifact_type": "documentation_index",
      "artifact_format": "json",
      "package_role": "distribution_readiness_proof",
      "distribution_status": "artifact_distribution_pending",
      "artifact_digest": "",
      "rc_scope": "Shared"
    },
    ...
  ],
  "allowed_distribution_channels": [
    "artifact_catalog_publication",
    "documentation_publication",
    "internal_distribution"
  ],
  "blocked_distribution_channels": [
    "external_key_signing",
    "legal_certification_claim",
    "production_deployment",
    "quantum_hardware_certification"
  ],
  "reason_codes": [
    "ARTIFACT_CATALOG_COUNTS_VALID",
    "ARTIFACT_CATALOG_INDEXES_VALID",
    "ARTIFACT_CATALOG_PACKAGE_INVENTORY_CANONICAL",
    "ARTIFACT_CATALOG_SOURCE_DISTRIBUTION_AUDIT_VALID",
    "ARTIFACT_CATALOG_VALID"
  ],
  "software_validation_caveat": "Validation is shadow/sandbox software validation, not quantum hardware validation.",
  "artifact_catalog_digest": "5d3e385441f025fa4d974f282db424cf5f7328b1e1a0d62197f404eec1c52f96"
}
```

---

## 4. Classifications & Status Rules

### Artifact Types
1. `release_manifest`: Declares release assets (e.g. `docs/SOL_WAVEGUIDE_RC1_MANIFEST.json`).
2. `audit_report`: Confirms validation outcome (e.g. `docs/SOL_WAVEGUIDE_RELEASE_CERTIFICATION_AUDIT_REPORT_RC1.json`).
3. `certification_bundle`: Proof container enclosing source evidence (e.g. `docs/SOL_WAVEGUIDE_RELEASE_CERTIFICATION_BUNDLE_RC1.json`).
4. `registry_index`: Catalogs all verified audit reports (e.g. `docs/SOL_WAVEGUIDE_RELEASE_CERTIFICATION_INDEX.json`).
5. `json_proof_capsule`: Individual court verdict or promotion record.
6. `markdown_documentation`: Narrative documentation file explaining system architecture.
7. `documentation_index`: Top-level index of the documentation and catalog.
8. `python_module`: Executable code implementing waveguide core logic.
9. `pytest_suite`: Tests verifying waveguide core logic.

### Distribution Status Rules
* **Ready** (`artifact_distribution_ready`): The file exists on disk, its computed digest matches its cataloged entry, it is classified appropriately, and it is not a forbidden deployment or signing payload.
* **Blocked** (`artifact_distribution_blocked`): The file exists but represents a forbidden action (e.g., deployment scripts, external keys), or it is missing and does not match self-referential paths.
* **Pending** (`artifact_distribution_pending`): Self-referential paths (`docs/SOL_WAVEGUIDE_CERTIFIED_ARTIFACT_CATALOG.*`) that are generated dynamically.
* **Invalid** (`artifact_distribution_invalid`): The file exists but does not pass validation (e.g., digest mismatch or missing required properties).

---

## 5. Deterministic Hashing Strategy

All validation structures are serialized canonically to guarantee identical hash signatures across runs and host environments:
* **Sorted Keys**: Dictionaries are dumped with keys sorted lexicographically.
* **Self-Referential Exclusions**:
  * `artifact_catalog_entry_digest` is popped before hashing a single entry.
  * `artifact_catalog_digest` is popped before hashing the top-level catalog.
* **Stable Field Ordering**: Aggregated lists (paths, digests, channels) are sorted before hashing.
* **Separators**: JSON output uses uniform spacing (`indent=4`) and platform-independent Unix path separators.

---

## 6. Limitations & Caveats

* **No Physical Packaging**: This tool maintains an index of safe artifacts, but it does *not* group them into a compressed archive.
* **Shadow Sandbox Verification**: All checks verify the static configuration and on-disk files. They do not guarantee the runtime execution correctness on target hardware.
* **Quantum Claims Blocked**: The caveat explicitly disclaims any physical quantum-level validation.

---

## 7. Next Recommended Bridge

The next bridge in the release governance pipeline is:
```text
Distribution Package Assembly Plan
```
This future step will define the exact layout, structure, and configuration to assemble the cataloged ready artifacts into a package payload without performing live publishing, deployment, or network uploads.
