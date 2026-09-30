# SOL Waveguide Release Certification Bundle

## Purpose

The **SOL Waveguide Release Certification Bundle** is a deterministic packaging layer. It bundles the complete sequence of release governance artifacts, approved release candidate data, runtime capability policy, and governed compiler session registries into a single release-level proof capsule (bundle artifact).

This establishes the following bridge:
```text
Governed Compiler Session Registry
→ Release Certification Bundle (This Step)
→ future Release Certification Validator / Independent Audit Verifier
```

This ensures that any third-party or downstream validator can independently confirm the validity, security, and governance of the release candidate using a single signed and verified proof registry.

---

## Required Artifact Chain

A release certification bundle is built by loading and referencing the following deterministic governance artifacts:

1. **RC Manifest** (`docs/SOL_WAVEGUIDE_RC1_MANIFEST.json` / `docs/SOL_WAVEGUIDE_RC2_MANIFEST.json`)
2. **Release Gate Delta Report** (`docs/SOL_WAVEGUIDE_RC_DELTA_AUDIT.json`)
3. **Promotion Record** (`docs/SOL_WAVEGUIDE_RC_PROMOTION_RECORD_RC1.json` / `docs/SOL_WAVEGUIDE_RC_PROMOTION_RECORD_RC2.json`)
4. **Promotion Court Verdict** (`docs/SOL_WAVEGUIDE_RC_COURT_VERDICT_RC1.json` / `docs/SOL_WAVEGUIDE_RC_COURT_VERDICT_RC2.json`)
5. **Release Registry** (`docs/SOL_WAVEGUIDE_RC_RELEASE_REGISTRY.json`)
6. **Runtime Capability Resolver Output** (`docs/SOL_WAVEGUIDE_RUNTIME_CAPABILITY_RESOLVER_RC1.json` / `docs/SOL_WAVEGUIDE_RUNTIME_CAPABILITY_RESOLVER_RC2.json`)
7. **Governed Compiler Session Registry** (`docs/SOL_WAVEGUIDE_GOVERNED_COMPILER_SESSION_REGISTRY.json`)

---

## Certification Bundle Schema

Each release certification bundle record contains the following fields:

| Field | Type | Description |
| :--- | :--- | :--- |
| `certification_bundle_id` | `str` | Unique identity prefix (e.g. `SOL-WAVEGUIDE-RELEASE-CERTIFICATION-BUNDLE-RC1`) |
| `certification_bundle_version` | `int` | Version identifier (currently `1`) |
| `certification_status` | `str` | Status (`certification_ready`, `certification_blocked`, `certification_warning`, `certification_invalid`) |
| `rc_id` | `str` | Target release candidate ID |
| `candidate_level` | `str` | Candidate level (`Foundation` or `Governed Execution Stack`) |
| `release_track` | `str` | Release track name |
| `manifest_digest` | `str` | SHA256 digest of the manifest |
| `release_gate_digest` | `str` | SHA256 digest of the delta audit report |
| `promotion_record_digest` | `str` | SHA256 digest of the promotion record |
| `promotion_court_verdict_digest` | `str` | SHA256 digest of the court verdict |
| `release_registry_digest` | `str` | SHA256 digest of the release registry |
| `runtime_capability_resolution_digest` | `str` | SHA256 digest of the runtime capability resolution |
| `compiler_session_registry_digest` | `str` | SHA256 digest of the session registry |
| `artifact_paths` | `List[str]` | List of relative paths included in the audit chain |
| `artifact_digests` | `Dict[str, str]` | Map from relative path to SHA256 digest |
| `approved_rcs` | `List[str]` | Approved RC IDs from the release registry |
| `governed_profiles` | `List[str]` | Governed profiles allowed/indexed |
| `governed_passes` | `List[str]` | Governed passes allowed/indexed |
| `registered_session_count` | `int` | Count of registered compiler sessions |
| `registered_rejection_session_count` | `int` | Count of registered rejection sessions |
| `blocked_session_count` | `int` | Count of blocked compiler sessions |
| `invalid_session_count` | `int` | Count of invalid compiler sessions |
| `rc1_session_count` | `int` | Count of registered RC1 compiler sessions |
| `rc2_session_count` | `int` | Count of registered RC2 compiler sessions |
| `compiler_profiles_indexed` | `List[str]` | Compiler profiles covered in the session registry |
| `pass_sequences_indexed` | `List[List[str]]` | Pass sequences covered in the session registry |
| `handler_ids_indexed` | `List[str]` | Handler IDs covered in the session registry |
| `final_output_payload_digests` | `List[str]` | Final output payload digests from session history |
| `reason_codes` | `List[str]` | List of reason/validation codes |
| `notes` | `List[str]` | Plaintext verification notes |
| `software_validation_caveat` | `str` | Non-production validation sandbox notice |
| `certification_bundle_digest` | `str` | Self-referencing SHA256 signature (computed excluding this field) |

---

## Validation Rules

A bundle reaches `certification_ready` only when:
- The target RC manifest exists, validates, and matches the target `rc_id`.
- The release gate boundary checks pass (`boundary_valid` is `true`).
- The promotion record exists, has status `promotion_ready`, and matches the target `rc_id`.
- The court verdict exists, has status `promotion_approved`, and matches the target `rc_id`.
- The release registry exists, is valid, and contains the target `rc_id` as approved.
- The capability resolution exists, validates, and matches the target `rc_id`.
- The governed compiler session registry validates and has status `session_registry_valid`.
- Blocked and invalid session counts in the session registry are zero.
- The software validation caveat is present.
- All artifact digests match the hashes of files found on disk.
- The bundle digest itself validates.

A bundle is marked `certification_blocked` or `certification_invalid` if any of these conditions fail.

---

## Deterministic Hashing & Self-Reference Exclusion

Like all prior governance layers, the certification bundle employs **canonical JSON serialization** to compute hashes:
- Struct keys are sorted.
- Lists are ordered deterministically.
- Absolute paths are normalized to repo-relative paths with forward slashes.
- Timestamps and machine-dependent parameters are excluded.
- The `certification_bundle_digest` field is excluded from its own signature input calculation.

---

## Sandbox Caveat & Limitations

> [!NOTE]
> All validation is shadow/sandbox software validation, not quantum hardware validation. No live deployment, production release mutations, or real cryptographic key signing are performed by this layer.

---

## Next Build Step

The next suggested governance bridge is:
```text
Release Certification Validator / Independent Audit Verifier
```
This future step will independently reload the certification bundle, recompute all nested digests, validate all governance components, and generate a final external-style audit report.
