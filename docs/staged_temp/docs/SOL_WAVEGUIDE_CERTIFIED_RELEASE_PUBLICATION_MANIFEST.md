# SOL Waveguide Certified Release Publication Manifest

## 1. Purpose

The `SOL Waveguide Certified Release Publication Manifest` represents a canonical, deterministic catalog of publication-ready release candidates. 

By consuming the verified release entries in the `Release Certification Index / RC Audit Registry`, the Certified Release Publication Manifest packages the verified RCs with their proven audit trail digests and maps them to allowed/blocked distribution channels.

This step establishes the following governance chain:
```text
Release Certification Index / RC Audit Registry
→ Certified Release Publication Manifest (This Module)
→ future Publication Manifest Validator / Distribution Readiness Auditor
```

---

## 2. Architecture & Design

The Certified Release Publication Manifest functions purely as a publication-readiness verification and catalog packaging layer:
* **No Live Deployments**: It does not execute live deployments or publish actual files to external distribution servers.
* **No External Signing**: Cryptographic signing is simulated through internal SHA256 digest validation of the source audit registry entries.
* **Deterministic Hashing**: All hashes are generated using standard `sha256` hashing on sorted JSON keys (canonical serialization).
* **Self-Referential Exclusions**:
  * For entries: `publication_entry_digest` is excluded from the input when computing its own hash.
  * For the manifest: `publication_manifest_digest` is excluded from the input when computing its own hash.

---

## 3. Data Models

### Publication Entry Schema
Each entry in the manifest details a single audited release candidate's publication status and channel allowance:

```json
{
  "publication_entry_id": "SOL-WAVEGUIDE-PUBLICATION-ENTRY-SOL-WAVEGUIDE-RC1",
  "rc_id": "SOL-WAVEGUIDE-RC1",
  "candidate_level": "Foundation",
  "publication_status": "publication_ready",
  "source_audit_registry_entry_digest": "0bf2dff7dce09f1a881599e7bc4e99987027692580fd3c17104eca5e58302a50",
  "certification_bundle_id": "SOL-WAVEGUIDE-RELEASE-CERTIFICATION-BUNDLE-RC1",
  "certification_bundle_digest": "1902c9e2034e2f77f979a32eef5fbf4de68e0eed00c84d375ffa7c54715a21f6",
  "audit_report_digest": "f7724b0ee9b3871e6767489e0be43dc7b74a437b0fab22985dfb60bdc9f259ed",
  "audit_case_digest": "8947628ea46a9da8fef4162adca7cf652fb33ed8eb09260b919bea83960d8e8e",
  "audit_status": "audit_registered",
  "audit_report_status": "audit_report_verified",
  "artifact_digest_mismatch_count": 0,
  "artifact_validation_failure_count": 0,
  "target_rc_approved": true,
  "runtime_capability_valid": true,
  "compiler_session_registry_valid": true,
  "registered_session_count": 2,
  "registered_rejection_session_count": 1,
  "final_output_payload_digests": [
    "0f09785f332627b50781c45055105e81a7b691aed354d0fdf9a593b2222ab03b",
    "197fd115a8162ddbf2c9aa84f68b84bd34ea07e92e0d26354bd6ba35bea92e80",
    "e118f75e0e7c0d4b21dffdd84fdeb322bdab07ca09285e73f3445c8cb8de2e65"
  ],
  "publication_channels_allowed": [
    "artifact_catalog_publication",
    "documentation_publication",
    "internal_distribution"
  ],
  "publication_channels_blocked": [
    "external_key_signing",
    "legal_certification_claim",
    "production_deployment",
    "quantum_hardware_certification"
  ],
  "publication_gate_reasons": [],
  "reason_codes": [
    "PUBLICATION_ARTIFACT_CATALOG_ALLOWED",
    "PUBLICATION_AUDIT_CASE_DIGEST_REFERENCED",
    "PUBLICATION_AUDIT_REPORT_DIGEST_REFERENCED",
    "PUBLICATION_BUNDLE_DIGEST_REFERENCED",
    "PUBLICATION_DOCUMENTATION_ALLOWED",
    "PUBLICATION_ENTRY_CANONICAL",
    "PUBLICATION_EXTERNAL_SIGNING_BLOCKED",
    "PUBLICATION_FINAL_OUTPUT_DIGESTS_REFERENCED",
    "PUBLICATION_INTERNAL_DISTRIBUTION_ALLOWED",
    "PUBLICATION_LEGAL_CLAIM_BLOCKED",
    "PUBLICATION_PRODUCTION_DEPLOYMENT_BLOCKED",
    "PUBLICATION_QUANTUM_HARDWARE_CLAIM_BLOCKED",
    "PUBLICATION_RC_AUDIT_VERIFIED",
    "PUBLICATION_RC_READY",
    "PUBLICATION_SOFTWARE_CAVEAT_INCLUDED",
    "PUBLICATION_SOURCE_AUDIT_ENTRY_REFERENCED"
  ],
  "notes": [],
  "software_validation_caveat": "Validation is shadow/sandbox software validation, not quantum hardware validation.",
  "publication_entry_digest": "fb9abd5b9cdbc25b994721ecaf1b9131cb5d3f04e0773a1f071a2c0c7b915bee"
}
```

### Top-Level Manifest Schema
The top-level manifest ties all publication entries together and summarizes publication-readiness counts and channel policies:

```json
{
  "publication_manifest_id": "SOL-WAVEGUIDE-CERTIFIED-RELEASE-PUBLICATION-MANIFEST",
  "publication_manifest_version": 1,
  "publication_manifest_status": "publication_manifest_ready",
  "source_audit_registry_digest": "4802a42b80b2739da7a06b82a8d73a9c541f655f573bdd8342e6521daf2748f4",
  "publication_entries": [ ... ],
  "publishable_rcs": [
    "SOL-WAVEGUIDE-RC1",
    "SOL-WAVEGUIDE-RC2"
  ],
  "blocked_rcs": [],
  "pending_rcs": [],
  "invalid_rcs": [],
  "publishable_rc_count": 2,
  "blocked_rc_count": 0,
  "pending_rc_count": 0,
  "invalid_rc_count": 0,
  "rc1_publication_count": 1,
  "rc2_publication_count": 1,
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
  "final_output_payload_digests": [
    "0f09785f332627b50781c45055105e81a7b691aed354d0fdf9a593b2222ab03b",
    "197fd115a8162ddbf2c9aa84f68b84bd34ea07e92e0d26354bd6ba35bea92e80",
    "e118f75e0e7c0d4b21dffdd84fdeb322bdab07ca09285e73f3445c8cb8de2e65"
  ],
  "publication_channel_policy": {
    "allowed": [
      "artifact_catalog_publication",
      "documentation_publication",
      "internal_distribution"
    ],
    "blocked": [
      "external_key_signing",
      "legal_certification_claim",
      "production_deployment",
      "quantum_hardware_certification"
    ]
  },
  "publication_readiness_catalog": [
    {
      "catalog_index": 1,
      "rc_id": "SOL-WAVEGUIDE-RC1",
      "candidate_level": "Foundation",
      "publication_status": "publication_ready",
      "certification_bundle_id": "SOL-WAVEGUIDE-RELEASE-CERTIFICATION-BUNDLE-RC1",
      "certification_bundle_digest": "1902c9e2034e2f77f979a32eef5fbf4de68e0eed00c84d375ffa7c54715a21f6",
      "audit_report_digest": "f7724b0ee9b3871e6767489e0be43dc7b74a437b0fab22985dfb60bdc9f259ed",
      "audit_case_digest": "8947628ea46a9da8fef4162adca7cf652fb33ed8eb09260b919bea83960d8e8e",
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
      ]
    },
    {
      "catalog_index": 2,
      "rc_id": "SOL-WAVEGUIDE-RC2",
      "candidate_level": "Governed Execution Stack",
      "publication_status": "publication_ready",
      "certification_bundle_id": "SOL-WAVEGUIDE-RELEASE-CERTIFICATION-BUNDLE-RC2",
      "certification_bundle_digest": "a4a0cb70a080ee51f01dd4aacc905e6cdc880b5420382e8e471a33c1012424f4",
      "audit_report_digest": "ca1d1278c3ebbb41aad86858aa5a9e1d6a2b5a5f8f772a64802d0f585cd69dcc",
      "audit_case_digest": "e7dc6f4fdd139c3e04d8a633e9232ffeba582810608ab94f3380717ff79e81a0",
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
      ]
    }
  ],
  "reason_codes": [
    "PUBLICATION_COUNTS_VALID",
    "PUBLICATION_READINESS_CATALOG_CANONICAL",
    "PUBLICATION_SOURCE_AUDIT_REGISTRY_VALID",
    "PUBLICATION_MANIFEST_READY"
  ],
  "software_validation_caveat": "Validation is shadow/sandbox software validation, not quantum hardware validation.",
  "publication_manifest_digest": "c35971e704ba433259d7c5246921a14702ec529cfc385ef58433c17dae3cd480"
}
```

---

## 4. Allowed & Blocked Channels

During software validation, specific channels are assigned to release candidates to document allowed distribution parameters:
* **Allowed Channels**:
  * `internal_distribution`: Authorized for local testing and developer integration.
  * `documentation_publication`: Cleared for catalog indexing and manual generation.
  * `artifact_catalog_publication`: Approved for publication in the internal software registry.
* **Blocked Channels**:
  * `production_deployment`: Blocked from live production pipelines.
  * `external_key_signing`: Blocked from being signed with production-grade certificate keys.
  * `legal_certification_claim`: Cannot be used for formal legal or hardware compliance statements.
  * `quantum_hardware_certification`: Cannot be used for certifying live quantum-physical executions.

---

## 5. Verification & Regression

To run focused verification on the publication manifest layer:
```bash
pytest tests/test_waveguide_certified_release_publication_manifest.py
```
This suite verifies that RC1 and RC2 entries compile successfully to `publication_ready` status, that the manifest registry digest is computed deterministically, and that any non-zero errors or mismatches on bundle files correctly block the publication gate.

---

## 6. Limitations & Software Caveat

* **Sandbox Scope**: The manifest does not perform deployment, public distribution, or live cryptographic signing.
* **No Real-Time Timestamps**: Wall-clock timestamps are omitted to ensure total parity and determinism across repeated catalog builds.

---

## 7. Next Recommended Bridge

The next logical component in the SOL Waveguide publication governance pipeline is:
* **Publication Manifest Validator / Distribution Readiness Auditor**: This module will independently reload the publication manifest, validate its entries against the source audit registry, and produce a sealed distribution-readiness audit report.
