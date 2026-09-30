# SOL Waveguide Distribution Package Assembly Plan

## 1. Purpose

The `SOL Waveguide Distribution Package Assembly Plan` defines a side-effect-free blueprint describing how certified release artifacts (JSON proofs, markdown docs, python source modules, and pytest suites) would be mapped, organized, and arranged in a future distribution package.

It acts as the planning bridge between the Certified Artifact Catalog and the layout verification stage:

```text
Certified Artifact Catalog / Distribution Package Index
→ Distribution Package Assembly Plan (This Step)
→ future Package Assembly Plan Validator / Dry-Run Packager Auditor
```

---

## 2. Architecture & Design

The Package Assembly Plan operates strictly under sandbox boundaries:
* **No File Mutations**: It does not create physical directories, copy files, or compile packaging units.
* **No Cryptographic Signing**: Cryptographic validation uses deterministically generated hex-encoded `sha256` signatures of canonical representation inputs.
* **Preserved Digests**: Source artifact digests are carried forward unchanged.
* **Target Path Mapping**: Maps relative source repository paths into structured, relative target paths using specific sections.

---

## 3. Target Path Safety & Mapping Rules

### Target Package Sections
Target package contents are partitioned into:
* `proof/`: Encloses JSON proof capsules, promotion records, court verdicts, and audit reports.
* `docs/`: Narrative markdown documentation files.
* `source/`: Reproducibility implementation source modules.
* `tests/`: Automated test suite files verifying package components.
* `indexes/`: Indexes of planned target paths (if any).
* `metadata/`: Release gate and capabilities metadata.

### Path Safety Checks
A mapped path is considered safe only when it is:
* **Relative**: Rejects absolute prefixes (e.g., `/` or drive letters).
* **Separator Normalized**: Rejects backslashes (`\`) and uses forward slashes (`/`).
* **Directory Traversal Safe**: Rejects parent directory traversal syntax (`..`).
* **Collision-Free**: No two layout entries can resolve to the same target package path.

### Target Mapping Rules
* `docs/*.json` $\to$ `proof/json/<filename>`
* `docs/*.md` $\to$ `docs/<filename>`
* `tools/sol-core/*.py` $\to$ `source/tools/sol-core/<filename>`
* `tests/*.py` $\to$ `tests/<filename>`

---

## 4. Data Models

### Layout Entry Schema
Describes the target placement and status of an individual artifact:

```json
{
  "package_layout_entry_id": "SOL-WAVEGUIDE-LAYOUT-SOL_WAVEGUIDE_RC1_MANIFEST_json",
  "source_artifact_path": "docs/SOL_WAVEGUIDE_RC1_MANIFEST.json",
  "source_artifact_name": "SOL_WAVEGUIDE_RC1_MANIFEST.json",
  "source_artifact_digest": "4cb8b9c8b3d6d5ef66432ab870bc1b9131cb5d3f04e0773a1f071a2c0c7b915bee",
  "source_artifact_type": "release_manifest",
  "source_artifact_format": "json",
  "source_package_role": "release_governance_proof",
  "rc_scope": "RC1",
  "candidate_level": "Foundation",
  "target_package_path": "proof/json/SOL_WAVEGUIDE_RC1_MANIFEST.json",
  "target_package_section": "proof/",
  "include_in_package_plan": true,
  "assembly_status": "package_layout_ready",
  "artifact_size_bytes": 4056,
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
  "is_test_artifact": false,
  "is_deployment_artifact": false,
  "is_signing_artifact": false,
  "reason_codes": [
    "PACKAGE_PLAN_LAYOUT_ENTRY_CANONICAL",
    "PACKAGE_PLAN_SOURCE_ARTIFACT_REFERENCED",
    "PACKAGE_PLAN_DIGEST_PRESERVED",
    "PACKAGE_PLAN_TARGET_PATH_MAPPED",
    "PACKAGE_PLAN_TARGET_PATH_RELATIVE",
    "PACKAGE_PLAN_TARGET_PATH_SAFE",
    "PACKAGE_PLAN_NO_ARCHIVE_CREATED",
    "PACKAGE_PLAN_NO_UPLOAD_PERFORMED",
    "PACKAGE_PLAN_NO_DEPLOYMENT_PERFORMED",
    "PACKAGE_PLAN_NO_SIGNING_PERFORMED",
    "PACKAGE_PLAN_PROOF_LAYOUT_INCLUDED",
    "PACKAGE_PLAN_SOFTWARE_CAVEAT_INCLUDED"
  ],
  "notes": [],
  "software_validation_caveat": "Validation is shadow/sandbox software validation, not quantum hardware validation.",
  "package_layout_entry_digest": "..."
}
```

### Top-Level Plan Schema
Groups layout entries, builds indexes, and hashes the canonical plan representation:

```json
{
  "package_assembly_plan_id": "SOL-WAVEGUIDE-DISTRIBUTION-PACKAGE-ASSEMBLY-PLAN",
  "package_assembly_plan_version": 1,
  "package_assembly_plan_status": "package_plan_ready",
  "source_artifact_catalog_digest": "208bcd8220a1ba5f1f696e1d00670fc7d4f6df4fd06b191524e0e93ae7bcdbd2",
  "planned_package_root": "package/",
  "layout_entries": [ ... ],
  "ready_layout_entries": [ ... ],
  "blocked_layout_entries": [],
  "pending_layout_entries": [],
  "invalid_layout_entries": [],
  "ready_layout_count": 28,
  "blocked_layout_count": 0,
  "pending_layout_count": 0,
  "invalid_layout_count": 0,
  "total_planned_file_count": 28,
  "rc1_layout_count": 6,
  "rc2_layout_count": 6,
  "shared_layout_count": 16,
  "target_package_sections": ["docs/", "proof/", "source/", "tests/"],
  "package_roles_indexed": [ ... ],
  "artifact_types_indexed": [ ... ],
  "artifact_formats_indexed": ["json", "markdown", "python"],
  "source_artifact_paths": [ ... ],
  "target_package_paths": [ ... ],
  "source_artifact_digests": [ ... ],
  "proof_artifact_layout": [ ... ],
  "documentation_artifact_layout": [ ... ],
  "source_module_layout": [ ... ],
  "test_source_layout": [ ... ],
  "package_file_map": [
    {
      "file_map_index": 1,
      "source_artifact_path": "docs/SOL_WAVEGUIDE_CERTIFIED_ARTIFACT_CATALOG.md",
      "target_package_path": "docs/SOL_WAVEGUIDE_CERTIFIED_ARTIFACT_CATALOG.md",
      "artifact_digest": "...",
      "artifact_type": "markdown_documentation",
      "package_role": "documentation",
      "rc_scope": "Shared"
    },
    ...
  ],
  "package_section_index": {
    "proof/": [ ... ],
    "docs/": [ ... ],
    "source/": [ ... ],
    "tests/": [ ... ],
    "indexes/": [],
    "metadata/": []
  },
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
    "PACKAGE_PLAN_COUNTS_VALID",
    "PACKAGE_PLAN_INDEXES_VALID",
    "PACKAGE_PLAN_FILE_MAP_CANONICAL",
    "PACKAGE_PLAN_SECTION_INDEX_CANONICAL",
    "PACKAGE_PLAN_SOURCE_CATALOG_VALID",
    "PACKAGE_PLAN_READY"
  ],
  "software_validation_caveat": "Validation is shadow/sandbox software validation, not quantum hardware validation.",
  "package_assembly_plan_digest": "73f07b7bc27659eeb5f1b0b36163daaced1cc7971bcf37f84e8ff8f87bfc9c0d"
}
```

---

## 5. Hashing & Exclusions

Deterministic hashing is enforced through sorted keys canonicalization:
* **Layout Entry**: `package_layout_entry_digest` is popped from the dictionary before computing its hash.
* **Assembly Plan**: `package_assembly_plan_digest` is popped from the dictionary before computing the top-level plan hash.

---

## 6. Caveats & Limitations

* **No Physical Bundles**: The tool plans layout mapping but does not output any physical ZIP file, tarball, or directory copies.
* **Software validation Caveat**: Validation is shadow/sandbox software validation, not quantum hardware validation.

---

## 7. Next Recommended Bridge

The next recommended bridge is:
```text
Package Assembly Plan Validator / Dry-Run Packager Auditor
```
This future step will independently reload the assembly plan, verify path collision safety and directory traversal rules, and dry-run evaluate the layout map without invoking network, archive-generation, or server deployment calls.
