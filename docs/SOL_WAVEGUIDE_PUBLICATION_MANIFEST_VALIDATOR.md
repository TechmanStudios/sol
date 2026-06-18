# SOL Waveguide Publication Manifest Validator / Distribution Readiness Auditor

## 1. Purpose

The `SOL Waveguide Publication Manifest Validator / Distribution Readiness Auditor` serves as an independent, side-effect-free validation layer for publication-readiness claims. 

It reloads the publication manifest, recomputes digests for both the manifest and all publication entries, validates the source audit registry index, and verifies that allowed channels remain restricted to metadata-only parameters while forbidden channels (e.g. production deployment, external key signing) remain blocked.

This step establishes the following governance chain:
```text
Certified Release Publication Manifest
→ Publication Manifest Validator / Distribution Readiness Auditor (This Module)
→ future Certified Artifact Catalog / Distribution Package Index
```

---

## 2. Architecture & Design

The Distribution Readiness Auditor executes strictly within a side-effect-free sandbox boundary:
* **No Live Deployments**: It does not schedule or perform any package uploads, server hosting, or live release mutations.
* **No Cryptographic Key Signing**: Signing claims are validated through internal SHA256 digest calculations.
* **Deterministic Hashing**: All hashes are generated using standard `sha256` hashing on sorted JSON keys (canonical serialization).
* **Self-Referential Exclusions**:
  * For cases: `distribution_audit_case_digest` is excluded from the input when computing its own hash.
  * For the report: `distribution_audit_report_digest` is excluded from the input when computing its own hash.

---

## 3. Data Models

### Distribution Audit Case Schema
Each audit case captures the readiness details for a single release candidate:

```json
{
  "distribution_audit_case_id": "SOL-WAVEGUIDE-DISTRIBUTION-AUDIT-CASE-SOL-WAVEGUIDE-RC1",
  "publication_manifest_id": "SOL-WAVEGUIDE-CERTIFIED-RELEASE-PUBLICATION-MANIFEST",
  "publication_manifest_path": "",
  "publication_manifest_digest_recorded": "c35971e704ba433259d7c5246921a14702ec529cfc385ef58433c17dae3cd480",
  "publication_manifest_digest_recomputed": "c35971e704ba433259d7c5246921a14702ec529cfc385ef58433c17dae3cd480",
  "publication_manifest_digest_match": true,
  "publication_entry_id": "SOL-WAVEGUIDE-PUBLICATION-ENTRY-SOL-WAVEGUIDE-RC1",
  "publication_entry_digest_recorded": "fb9abd5b9cdbc25b994721ecaf1b9131cb5d3f04e0773a1f071a2c0c7b915bee",
  "publication_entry_digest_recomputed": "fb9abd5b9cdbc25b994721ecaf1b9131cb5d3f04e0773a1f071a2c0c7b915bee",
  "publication_entry_digest_match": true,
  "rc_id": "SOL-WAVEGUIDE-RC1",
  "candidate_level": "Foundation",
  "publication_status": "publication_ready",
  "distribution_readiness_status": "distribution_ready",
  "source_audit_registry_digest_recorded": "4802a42b80b2739da7a06b82a8d73a9c541f655f573bdd8342e6521daf2748f4",
  "source_audit_registry_digest_recomputed": "4802a42b80b2739da7a06b82a8d73a9c541f655f573bdd8342e6521daf2748f4",
  "source_audit_registry_digest_match": true,
  "source_audit_registry_valid": true,
  "source_audit_registry_entry_digest": "0bf2dff7dce09f1a881599e7bc4e99987027692580fd3c17104eca5e58302a50",
  "certification_bundle_id": "SOL-WAVEGUIDE-RELEASE-CERTIFICATION-BUNDLE-RC1",
  "certification_bundle_digest": "1902c9e2034e2f77f979a32eef5fbf4de68e0eed00c84d375ffa7c54715a21f6",
  "audit_report_digest": "f7724b0ee9b3871e6767489e0be43dc7b74a437b0fab22985dfb60bdc9f259ed",
  "audit_case_digest": "8947628ea46a9da8fef4162adca7cf652fb33ed8eb09260b919bea83960d8e8e",
  "audit_status": "audit_registered",
  "audit_report_status": "audit_report_verified",
  "target_rc_approved": true,
  "runtime_capability_valid": true,
  "compiler_session_registry_valid": true,
  "artifact_digest_mismatch_count": 0,
  "artifact_validation_failure_count": 0,
  "registered_session_count": 2,
  "registered_rejection_session_count": 1,
  "final_output_payload_digests": [
    "0f09785f332627b50781c45055105e81a7b691aed354d0fdf9a593b2222ab03b",
    "197fd115a8162ddbf2c9aa84f68b84bd34ea07e92e0d26354bd6ba35bea92e80",
    "e118f75e0e7c0d4b21dffdd84fdeb322bdab07ca09285e73f3445c8cb8de2e65"
  ],
  "allowed_channels": [
    "artifact_catalog_publication",
    "documentation_publication",
    "internal_distribution"
  ],
  "blocked_channels": [
    "external_key_signing",
    "legal_certification_claim",
    "production_deployment",
    "quantum_hardware_certification"
  ],
  "metadata_only_channels_verified": true,
  "forbidden_channels_blocked": true,
  "publication_gate_reasons": [],
  "reason_codes": [
    "DISTRIBUTION_ARTIFACT_CATALOG_METADATA_ONLY",
    "DISTRIBUTION_AUDIT_CASE_CANONICAL",
    "DISTRIBUTION_AUDIT_CASE_DIGEST_REFERENCED",
    "DISTRIBUTION_AUDIT_REPORT_DIGEST_REFERENCED",
    "DISTRIBUTION_BUNDLE_DIGEST_REFERENCED",
    "DISTRIBUTION_DOCUMENTATION_PUBLICATION_METADATA_ONLY",
    "DISTRIBUTION_EXTERNAL_SIGNING_BLOCKED",
    "DISTRIBUTION_FINAL_OUTPUT_DIGESTS_REFERENCED",
    "DISTRIBUTION_FORBIDDEN_CHANNELS_BLOCKED",
    "DISTRIBUTION_INTERNAL_DISTRIBUTION_METADATA_ONLY",
    "DISTRIBUTION_LEGAL_CLAIM_BLOCKED",
    "DISTRIBUTION_PRODUCTION_DEPLOYMENT_BLOCKED",
    "DISTRIBUTION_PUBLICATION_ENTRY_DIGEST_MATCH",
    "DISTRIBUTION_PUBLICATION_ENTRY_DIGEST_REFERENCED",
    "DISTRIBUTION_PUBLICATION_MANIFEST_DIGEST_MATCH",
    "DISTRIBUTION_PUBLICATION_MANIFEST_LOADED",
    "DISTRIBUTION_PUBLICATION_MANIFEST_VALID",
    "DISTRIBUTION_QUANTUM_HARDWARE_CLAIM_BLOCKED",
    "DISTRIBUTION_RC_AUDIT_VERIFIED",
    "DISTRIBUTION_RC_PUBLICATION_READY",
    "DISTRIBUTION_RC_READY",
    "DISTRIBUTION_READINESS_VERIFIED",
    "DISTRIBUTION_SOFTWARE_CAVEAT_INCLUDED",
    "DISTRIBUTION_SOURCE_AUDIT_ENTRY_REFERENCED",
    "DISTRIBUTION_SOURCE_AUDIT_REGISTRY_DIGEST_MATCH",
    "DISTRIBUTION_SOURCE_AUDIT_REGISTRY_VALID"
  ],
  "notes": [],
  "software_validation_caveat": "Validation is shadow/sandbox software validation, not quantum hardware validation.",
  "distribution_audit_case_digest": "1371967e740d22c538291de8b7375aab6f6c19daa5dc7e66c52404ead6252f93"
}
```

### Top-Level Report Schema
The top-level report summarizes the audit results across all release candidates:

```json
{
  "distribution_audit_report_id": "SOL-WAVEGUIDE-DISTRIBUTION-READINESS-AUDIT-REPORT",
  "distribution_audit_report_version": 1,
  "distribution_audit_report_status": "distribution_readiness_verified",
  "source_publication_manifest_digest": "c35971e704ba433259d7c5246921a14702ec529cfc385ef58433c17dae3cd480",
  "source_audit_registry_digest": "4802a42b80b2739da7a06b82a8d73a9c541f655f573bdd8342e6521daf2748f4",
  "audited_cases": [ ... ],
  "distribution_ready_rcs": [
    "SOL-WAVEGUIDE-RC1",
    "SOL-WAVEGUIDE-RC2"
  ],
  "distribution_blocked_rcs": [],
  "distribution_pending_rcs": [],
  "distribution_invalid_rcs": [],
  "distribution_ready_count": 2,
  "distribution_blocked_count": 0,
  "distribution_pending_count": 0,
  "distribution_invalid_count": 0,
  "rc1_distribution_count": 1,
  "rc2_distribution_count": 1,
  "candidate_levels_indexed": [
    "Foundation",
    "Governed Execution Stack"
  ],
  "certification_bundle_ids": [
    "SOL-WAVEGUIDE-RELEASE-CERTIFICATION-BUNDLE-RC1",
    "SOL-WAVEGUIDE-RELEASE-CERTIFICATION-BUNDLE-RC2"
  ],
  "certification_bundle_digests": [
    "1902c9e2034e2f77f979a32eef5fbf4de68e0eed00c84d375ffa7c54715a21f6",
    "a4a0cb70a080ee51f01dd4aacc905e6cdc880b5420382e8e471a33c1012424f4"
  ],
  "audit_report_digests": [
    "ca1d1278c3ebbb41aad86858aa5a9e1d6a2b5a5f8f772a64802d0f585cd69dcc",
    "f7724b0ee9b3871e6767489e0be43dc7b74a437b0fab22985dfb60bdc9f259ed"
  ],
  "audit_case_digests": [
    "8947628ea46a9da8fef4162adca7cf652fb33ed8eb09260b919bea83960d8e8e",
    "e7dc6f4fdd139c3e04d8a633e9232ffeba582810608ab94f3380717ff79e81a0"
  ],
  "audit_registry_entry_digests": [
    "0bf2dff7dce09f1a881599e7bc4e99987027692580fd3c17104eca5e58302a50",
    "f2d15709e7d3ff14a00ca5b5d9b51ebcda359637220c6b4a7d1449cba0ca1206"
  ],
  "publication_entry_digests": [
    "fb9abd5b9cdbc25b994721ecaf1b9131cb5d3f04e0773a1f071a2c0c7b915bee",
    "97f26fc99ca82662c161a0eb1bfe48cf5ee1f8680fa35bf7bf659e51cde5fa21"
  ],
  "final_output_payload_digests": [
    "0f09785f332627b50781c45055105e81a7b691aed354d0fdf9a593b2222ab03b",
    "197fd115a8162ddbf2c9aa84f68b84bd34ea07e92e0d26354bd6ba35bea92e80",
    "e118f75e0e7c0d4b21dffdd84fdeb322bdab07ca09285e73f3445c8cb8de2e65"
  ],
  "allowed_channels_indexed": [
    "artifact_catalog_publication",
    "documentation_publication",
    "internal_distribution"
  ],
  "blocked_channels_indexed": [
    "external_key_signing",
    "legal_certification_claim",
    "production_deployment",
    "quantum_hardware_certification"
  ],
  "metadata_only_channels_verified": true,
  "forbidden_channels_blocked": true,
  "reason_codes": [
    "DISTRIBUTION_COUNTS_VALID",
    "DISTRIBUTION_FORBIDDEN_CHANNELS_BLOCKED",
    "DISTRIBUTION_SOURCE_AUDIT_REGISTRY_VALID",
    "DISTRIBUTION_READINESS_VERIFIED"
  ],
  "software_validation_caveat": "Validation is shadow/sandbox software validation, not quantum hardware validation.",
  "distribution_audit_report_digest": "ae5e683fef32a49aa09b75ae12972a81ee8b882fe91c33e597822020b06907df"
}
```

---

## 4. Distribution Channel Policy Verification

The auditor strictly enforces the separation of channels:
* **Allowed Metadata-Only Channels**: Allowed list must only contain metadata distribution identifiers (`internal_distribution`, `documentation_publication`, `artifact_catalog_publication`).
* **Blocked Forbidden Channels**: Blocked list must contain forbidden production deployment markers (`production_deployment`, `external_key_signing`, `legal_certification_claim`, `quantum_hardware_certification`).
* Any entry violating these rules defaults to `distribution_blocked` state.

---

## 5. Verification Command

To run focused verification on the auditor layer:
```bash
pytest tests/test_waveguide_publication_manifest_validator.py
```

---

## 6. Limitations & Software Caveat

* **Sandbox Scope**: The verifier operates as a sandbox verification layer, not a real package indexing pipeline.
* **No Chronological Timestamps**: Timestamps are excluded from catalog indexing to keep digests stable.

---

## 7. Next Recommended Step

The next logical component in the SOL Waveguide release publication governance pipeline is:
* **Certified Artifact Catalog / Distribution Package Index**: This future step will package the actual verified filesystem files, markdown documents, and JSON manifests into a single, cohesive distribution index catalog for release packaging, still without triggering deployment actions.
