# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Governed Compiler Session Registry for SOL Waveguide.
Indexes verified compiler sessions into a canonical release-level history catalog,
tracking digests, counts, profiles, and sequences.
"""

import os
import json
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Tuple, Optional

from sol_waveguide_rc_promotion_ledger import (
    hash_data,
    normalize_to_repo_path,
    REPO_ROOT
)
from sol_waveguide_governed_compiler_session_verifier import (
    validate_waveguide_governed_compiler_session_verification_report
)

@dataclass
class WaveguideGovernedCompilerSessionRegistryEntry:
    session_registry_entry_id: str
    rc_id: str
    candidate_level: str
    compiler_profile: Optional[str]
    requested_pass_sequence: List[str]
    session_verification_status: str          # session_registered, session_rejection_registered, session_blocked, session_invalid
    invocation_status: str
    invocation_record_path: str
    invocation_record_digest: str
    session_case_digest: str
    trace_ledger_digest: str
    replay_report_digest: str
    final_output_payload_digest: str
    executed_pass_count: int
    rejected_pass_count: int
    verified_execution_count: int
    verified_rejection_count: int
    failed_replay_count: int
    handler_ids_used: List[str]
    reason_codes: List[str]
    software_validation_caveat: str
    registry_entry_digest: str = ""


@dataclass
class WaveguideGovernedCompilerSessionRegistry:
    registry_id: str
    registry_version: str
    registry_status: str                       # session_registry_valid, session_registry_blocked, session_registry_warning
    source_session_verifier_report_digest: str
    entries: List[Dict[str, Any]]
    registered_sessions: List[str]
    registered_rejection_sessions: List[str]
    blocked_sessions: List[str]
    invalid_sessions: List[str]
    registered_session_count: int
    registered_rejection_session_count: int
    blocked_session_count: int
    invalid_session_count: int
    rc1_session_count: int
    rc2_session_count: int
    compiler_profiles_indexed: List[str]
    pass_sequences_indexed: List[List[str]]
    handler_ids_indexed: List[str]
    invocation_record_digests: List[str]
    session_case_digests: List[str]
    trace_ledger_digests: List[str]
    replay_report_digests: List[str]
    final_output_payload_digests: List[str]
    software_validation_caveat: str
    reason_codes: List[str]
    registry_digest: str = ""


def hash_waveguide_governed_compiler_session_registry_entry(entry: Any) -> str:
    """
    Computes digest for a registry entry, excluding registry_entry_digest.
    """
    if hasattr(entry, "__dict__"):
        e_dict = asdict(entry)
    elif isinstance(entry, dict):
        e_dict = dict(entry)
    else:
        raise TypeError("entry must be a dictionary or a dataclass instance")

    e_dict_copy = dict(e_dict)
    e_dict_copy.pop("registry_entry_digest", None)
    return hash_data(e_dict_copy)


def hash_waveguide_governed_compiler_session_registry(registry: Any) -> str:
    """
    Computes digest for a registry catalog, excluding registry_digest.
    """
    if hasattr(registry, "__dict__"):
        r_dict = asdict(registry)
    elif isinstance(registry, dict):
        r_dict = dict(registry)
    else:
        raise TypeError("registry must be a dictionary or a dataclass instance")

    r_dict_copy = dict(r_dict)
    r_dict_copy.pop("registry_digest", None)
    return hash_data(r_dict_copy)


def build_waveguide_governed_compiler_session_registry_entry(
    case_dict: Dict[str, Any]
) -> WaveguideGovernedCompilerSessionRegistryEntry:
    """
    Constructs a session registry entry from a verifier verification case dictionary.
    """
    rc_id = case_dict.get("rc_id", "UNKNOWN")
    compiler_profile = case_dict.get("compiler_profile", "UNKNOWN")
    requested_pass_sequence = case_dict.get("requested_pass_sequence", [])
    status = case_dict.get("session_verification_status", "UNKNOWN")

    # Mapping status
    if status == "session_verified":
        reg_status = "session_registered"
    elif status == "session_rejection_verified":
        reg_status = "session_rejection_registered"
    elif status == "session_blocked":
        reg_status = "session_blocked"
    else:
        reg_status = "session_invalid"

    # Unique entry ID
    entry_id = f"SOL-WAVEGUIDE-SESSION-REGISTRY-ENTRY-{rc_id}-{compiler_profile or 'NONE'}"

    # Load invocation record to read handler_ids_used
    rec_path = case_dict.get("invocation_record_path", "")
    full_rec_path = os.path.join(REPO_ROOT, rec_path)
    handler_ids_used = []
    if os.path.exists(full_rec_path):
        try:
            with open(full_rec_path, "r", encoding="utf-8") as f:
                rec_data = json.load(f)
            handler_ids_used = rec_data.get("handler_ids_used", [])
        except Exception:
            pass

    # Map reasons
    reasons = ["SESSION_REGISTRY_ENTRY_CANONICAL"]
    if reg_status == "session_registered":
        reasons.append("SESSION_REGISTRY_SESSION_REGISTERED")
    elif reg_status == "session_rejection_registered":
        reasons.append("SESSION_REGISTRY_REJECTION_SESSION_REGISTERED")

    reasons.append("SESSION_REGISTRY_INVOCATION_DIGEST_REFERENCED")
    reasons.append("SESSION_REGISTRY_SESSION_CASE_DIGEST_REFERENCED")
    reasons.append("SESSION_REGISTRY_TRACE_LEDGER_DIGEST_REFERENCED")
    reasons.append("SESSION_REGISTRY_REPLAY_REPORT_DIGEST_REFERENCED")
    reasons.append("SESSION_REGISTRY_FINAL_OUTPUT_DIGEST_REFERENCED")

    entry = WaveguideGovernedCompilerSessionRegistryEntry(
        session_registry_entry_id=entry_id,
        rc_id=rc_id,
        candidate_level=case_dict.get("candidate_level", "UNKNOWN"),
        compiler_profile=compiler_profile,
        requested_pass_sequence=requested_pass_sequence,
        session_verification_status=reg_status,
        invocation_status=case_dict.get("invocation_status", "UNKNOWN"),
        invocation_record_path=case_dict.get("invocation_record_path", ""),
        invocation_record_digest=case_dict.get("invocation_record_digest", ""),
        session_case_digest=case_dict.get("session_case_digest", ""),
        trace_ledger_digest=case_dict.get("trace_ledger_digest", ""),
        replay_report_digest=case_dict.get("replay_report_digest", ""),
        final_output_payload_digest=case_dict.get("recorded_final_output_payload_digest", ""),
        executed_pass_count=case_dict.get("executed_pass_count", 0),
        rejected_pass_count=case_dict.get("rejected_pass_count", 0),
        verified_execution_count=case_dict.get("verified_execution_count", 0),
        verified_rejection_count=case_dict.get("verified_rejection_count", 0),
        failed_replay_count=case_dict.get("failed_replay_count", 0),
        handler_ids_used=handler_ids_used,
        reason_codes=sorted(list(set(reasons))),
        software_validation_caveat=case_dict.get("software_validation_caveat", "")
    )
    entry.registry_entry_digest = hash_waveguide_governed_compiler_session_registry_entry(entry)
    return entry


def validate_waveguide_governed_compiler_session_registry_entry(
    entry: Any
) -> Tuple[bool, List[str]]:
    """
    Validates entry constraints, counts, software validation caveats, and signatures.
    """
    if hasattr(entry, "__dict__"):
        e_dict = asdict(entry)
    else:
        e_dict = dict(entry)

    reasons = []
    is_ok = True

    # 1. Validate signature
    computed_digest = hash_waveguide_governed_compiler_session_registry_entry(e_dict)
    if e_dict.get("registry_entry_digest") == computed_digest and computed_digest != "":
        reasons.append("SESSION_REGISTRY_ENTRY_DIGEST_VALID")
    else:
        is_ok = False
        reasons.append("SESSION_REGISTRY_BLOCKED")
        return False, ["SESSION_REGISTRY_BLOCKED"]

    # 2. Check required digests
    if (not e_dict.get("invocation_record_digest") or
        not e_dict.get("session_case_digest") or
        not e_dict.get("trace_ledger_digest") or
        not e_dict.get("replay_report_digest") or
        not e_dict.get("final_output_payload_digest")):
        is_ok = False

    # 3. Check requested pass sequence and profile
    if not e_dict.get("requested_pass_sequence") or not e_dict.get("compiler_profile") or not e_dict.get("rc_id"):
        is_ok = False

    # 4. Check software validation caveat
    caveat = e_dict.get("software_validation_caveat", "")
    if caveat and ("sandbox" in caveat.lower() or "validation" in caveat.lower()):
        reasons.append("SESSION_REGISTRY_SOFTWARE_CAVEAT_INCLUDED")
    else:
        is_ok = False

    # 5. Check status constraints
    status = e_dict.get("session_verification_status")
    if status == "session_registered":
        reasons.append("SESSION_REGISTRY_SESSION_REGISTERED")
        if (e_dict.get("invocation_status") != "invocation_verified" or
            e_dict.get("executed_pass_count", 0) < 1 or
            e_dict.get("verified_execution_count", 0) < 1 or
            e_dict.get("failed_replay_count", 0) != 0):
            is_ok = False
    elif status == "session_rejection_registered":
        reasons.append("SESSION_REGISTRY_REJECTION_SESSION_REGISTERED")
        if (e_dict.get("invocation_status") != "invocation_rejected_verified" or
            e_dict.get("executed_pass_count", 0) != 0 or
            e_dict.get("rejected_pass_count", 0) < 1 or
            e_dict.get("verified_rejection_count", 0) < 1 or
            e_dict.get("failed_replay_count", 0) != 0):
            is_ok = False
    else:
        is_ok = False
        reasons.append("SESSION_REGISTRY_BLOCKED")

    return is_ok, sorted(list(set(reasons)))


def build_waveguide_governed_compiler_session_registry(
    verifier_report_path: str,
    report_data: Optional[Dict[str, Any]] = None
) -> WaveguideGovernedCompilerSessionRegistry:
    """
    Consumes the verifier report, builds registry entries, indexes sessions,
    and returns the top-level session registry.
    """
    norm_path = normalize_to_repo_path(verifier_report_path)
    full_path = os.path.join(REPO_ROOT, norm_path)

    if report_data is None:
        if os.path.exists(full_path):
            with open(full_path, "r", encoding="utf-8") as f:
                report_data = json.load(f)
        else:
            report_data = {}

    reasons = ["SESSION_REGISTRY_ENTRY_CANONICAL"]
    is_valid = True

    # 1. Validate verifier report
    rep_ok, rep_reasons = validate_waveguide_governed_compiler_session_verification_report(report_data)
    if rep_ok:
        reasons.append("SESSION_REGISTRY_SOURCE_REPORT_VALID")
    else:
        is_valid = False
        reasons.append("SESSION_REGISTRY_SOURCE_REPORT_INVALID")

    # 2. Build registry entries
    raw_cases = report_data.get("cases", [])
    entries = []
    for c in raw_cases:
        entry = build_waveguide_governed_compiler_session_registry_entry(c)
        entries.append(entry)

    # 3. Sort entries deterministically
    def sort_entries_key(e: WaveguideGovernedCompilerSessionRegistryEntry) -> Tuple[str, str, str, str]:
        return (
            e.rc_id,
            e.compiler_profile or "",
            e.session_verification_status,
            e.invocation_record_digest
        )

    entries_sorted = sorted(entries, key=sort_entries_key)
    entries_serialized = [asdict(e) for e in entries_sorted]

    # 4. Indexing & aggregation
    registered_sessions = []
    registered_rejection_sessions = []
    blocked_sessions = []
    invalid_sessions = []

    rc1_count = 0
    rc2_count = 0

    profiles = set()
    pass_seqs = {}
    handler_ids = set()

    invocation_record_digests = set()
    session_case_digests = set()
    trace_ledger_digests = set()
    replay_report_digests = set()
    final_output_payload_digests = set()

    for e in entries_sorted:
        eid = e.session_registry_entry_id
        status = e.session_verification_status
        if status == "session_registered":
            registered_sessions.append(eid)
        elif status == "session_rejection_registered":
            registered_rejection_sessions.append(eid)
        elif status == "session_blocked":
            blocked_sessions.append(eid)
        else:
            invalid_sessions.append(eid)

        if "RC1" in e.rc_id:
            rc1_count += 1
        elif "RC2" in e.rc_id:
            rc2_count += 1

        if e.compiler_profile:
            profiles.add(e.compiler_profile)
            reasons.append("SESSION_REGISTRY_PROFILE_INDEXED")

        # Index pass sequences by sorting their unique list
        seq_str = ",".join(e.requested_pass_sequence)
        pass_seqs[seq_str] = e.requested_pass_sequence
        reasons.append("SESSION_REGISTRY_PASS_SEQUENCE_INDEXED")

        for hid in e.handler_ids_used:
            handler_ids.add(hid)
            reasons.append("SESSION_REGISTRY_HANDLER_IDS_INDEXED")

        invocation_record_digests.add(e.invocation_record_digest)
        session_case_digests.add(e.session_case_digest)
        trace_ledger_digests.add(e.trace_ledger_digest)
        replay_report_digests.add(e.replay_report_digest)
        final_output_payload_digests.add(e.final_output_payload_digest)

    # Sort sequences by their joined string representation
    pass_seqs_sorted = [pass_seqs[k] for k in sorted(pass_seqs.keys())]

    # Overall validation status check
    if (len(blocked_sessions) == 0 and len(invalid_sessions) == 0 and
        rep_ok and is_valid):
        registry_status = "session_registry_valid"
        reasons.append("SESSION_REGISTRY_VALID")
        reasons.append("SESSION_REGISTRY_COUNTS_VALID")
    else:
        registry_status = "session_registry_blocked"
        reasons.append("SESSION_REGISTRY_BLOCKED")

    caveat = "Validation is shadow/sandbox software validation, not quantum hardware validation."
    if caveat:
        reasons.append("SESSION_REGISTRY_SOFTWARE_CAVEAT_INCLUDED")

    registry = WaveguideGovernedCompilerSessionRegistry(
        registry_id="SOL-WAVEGUIDE-GOVERNED-COMPILER-SESSION-REGISTRY",
        registry_version="1",
        registry_status=registry_status,
        source_session_verifier_report_digest=report_data.get("session_verification_report_digest", ""),
        entries=entries_serialized,
        registered_sessions=sorted(registered_sessions),
        registered_rejection_sessions=sorted(registered_rejection_sessions),
        blocked_sessions=sorted(blocked_sessions),
        invalid_sessions=sorted(invalid_sessions),
        registered_session_count=len(registered_sessions),
        registered_rejection_session_count=len(registered_rejection_sessions),
        blocked_session_count=len(blocked_sessions),
        invalid_session_count=len(invalid_sessions),
        rc1_session_count=rc1_count,
        rc2_session_count=rc2_count,
        compiler_profiles_indexed=sorted(list(profiles)),
        pass_sequences_indexed=pass_seqs_sorted,
        handler_ids_indexed=sorted(list(handler_ids)),
        invocation_record_digests=sorted(list(invocation_record_digests)),
        session_case_digests=sorted(list(session_case_digests)),
        trace_ledger_digests=sorted(list(trace_ledger_digests)),
        replay_report_digests=sorted(list(replay_report_digests)),
        final_output_payload_digests=sorted(list(final_output_payload_digests)),
        software_validation_caveat=caveat,
        reason_codes=sorted(list(set(reasons)))
    )
    registry.registry_digest = hash_waveguide_governed_compiler_session_registry(registry)
    return registry


def validate_waveguide_governed_compiler_session_registry(
    registry: Any
) -> Tuple[bool, List[str]]:
    """
    Confirms structural counts, aggregate lists sorting, entry validations, and signature.
    """
    if hasattr(registry, "__dict__"):
        r_dict = asdict(registry)
    else:
        r_dict = dict(registry)

    reasons = []
    is_ok = True

    # 1. Validate signature digest
    computed_digest = hash_waveguide_governed_compiler_session_registry(r_dict)
    if r_dict.get("registry_digest") == computed_digest and computed_digest != "":
        reasons.append("SESSION_REGISTRY_DIGEST_VALID")
    else:
        is_ok = False
        reasons.append("SESSION_REGISTRY_BLOCKED")
        return False, ["SESSION_REGISTRY_BLOCKED"]

    # 2. Validate all entries
    entries = r_dict.get("entries", [])
    for e in entries:
        ent_ok, ent_reasons = validate_waveguide_governed_compiler_session_registry_entry(e)
        if not ent_ok:
            is_ok = False

    # 3. Check counts match lists
    reg_sessions = r_dict.get("registered_sessions", [])
    reg_rej_sessions = r_dict.get("registered_rejection_sessions", [])
    blocked = r_dict.get("blocked_sessions", [])
    invalid = r_dict.get("invalid_sessions", [])

    if (r_dict.get("registered_session_count") != len(reg_sessions) or
        r_dict.get("registered_rejection_session_count") != len(reg_rej_sessions) or
        r_dict.get("blocked_session_count") != len(blocked) or
        r_dict.get("invalid_session_count") != len(invalid)):
        is_ok = False

    # 4. Check list sorting
    if (r_dict.get("compiler_profiles_indexed") != sorted(r_dict.get("compiler_profiles_indexed", [])) or
        r_dict.get("handler_ids_indexed") != sorted(r_dict.get("handler_ids_indexed", [])) or
        r_dict.get("invocation_record_digests") != sorted(r_dict.get("invocation_record_digests", [])) or
        r_dict.get("session_case_digests") != sorted(r_dict.get("session_case_digests", [])) or
        r_dict.get("trace_ledger_digests") != sorted(r_dict.get("trace_ledger_digests", [])) or
        r_dict.get("replay_report_digests") != sorted(r_dict.get("replay_report_digests", [])) or
        r_dict.get("final_output_payload_digests") != sorted(r_dict.get("final_output_payload_digests", []))):
        is_ok = False

    caveat = r_dict.get("software_validation_caveat", "")
    if caveat and ("sandbox" in caveat.lower() or "validation" in caveat.lower()):
        reasons.append("SESSION_REGISTRY_SOFTWARE_CAVEAT_INCLUDED")
    else:
        is_ok = False

    status = r_dict.get("registry_status")
    if status == "session_registry_valid" and is_ok:
        reasons.append("SESSION_REGISTRY_VALID")
    else:
        is_ok = False
        reasons.append("SESSION_REGISTRY_BLOCKED")

    return is_ok, sorted(list(set(reasons)))


def summarize_waveguide_governed_compiler_session_registry(registry: Any) -> str:
    """
    Generates a plaintext summary of the compiler session registry.
    """
    if hasattr(registry, "__dict__"):
        r_dict = asdict(registry)
    else:
        r_dict = dict(registry)

    lines = [
        "============================================================",
        "     SOL WAVEGUIDE GOVERNED COMPILER SESSION REGISTRY",
        "============================================================",
        f"Registry ID:     {r_dict.get('registry_id')}",
        f"Status:          {r_dict.get('registry_status')}",
        f"Version:         {r_dict.get('registry_version')}",
        "------------------------------------------------------------",
        f"Registered Sessions:           {r_dict.get('registered_session_count')}",
        f"Registered Rejection Sessions: {r_dict.get('registered_rejection_session_count')}",
        f"Blocked Sessions:              {r_dict.get('blocked_session_count')}",
        f"Invalid Sessions:              {r_dict.get('invalid_session_count')}",
        f"RC1 / RC2 Sessions:            {r_dict.get('rc1_session_count')} / {r_dict.get('rc2_session_count')}",
        "------------------------------------------------------------",
        "Profiles Indexed:",
    ]
    for p in r_dict.get("compiler_profiles_indexed", []):
        lines.append(f"  - {p}")

    lines.append("Pass Sequences Indexed:")
    for seq in r_dict.get("pass_sequences_indexed", []):
        lines.append(f"  - {', '.join(seq)}")

    lines.append("Handlers Indexed:")
    for h in r_dict.get("handler_ids_indexed", []):
        lines.append(f"  - {h}")

    lines.extend([
        "------------------------------------------------------------",
        f"Registry Digest: {r_dict.get('registry_digest')}",
        "============================================================"
    ])
    return "\n".join(lines)


def export_waveguide_governed_compiler_session_registry(registry: Any, filepath: str) -> None:
    """
    Saves the registry catalog to a key-sorted JSON file on disk.
    """
    if hasattr(registry, "__dict__"):
        r_dict = asdict(registry)
    else:
        r_dict = dict(registry)

    target_dir = os.path.dirname(filepath)
    if target_dir and not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(r_dict, f, indent=4, sort_keys=True)


def compare_waveguide_governed_compiler_session_registries(left: Any, right: Any) -> Dict[str, Any]:
    """
    Compares two registries and returns differences.
    """
    def to_dict(reg):
        if hasattr(reg, "__dict__"):
            return asdict(reg)
        return dict(reg)

    l_dict = to_dict(left)
    r_dict = to_dict(right)

    diffs = {}
    for key in set(l_dict.keys()) | set(r_dict.keys()):
        val_l = l_dict.get(key)
        val_r = r_dict.get(key)
        if val_l != val_r:
            diffs[key] = {
                "left": val_l,
                "right": val_r
            }
    return diffs


# Index helper functions as requested by API specifications
def index_waveguide_governed_compiler_sessions_by_status(
    entries: List[Dict[str, Any]]
) -> Dict[str, List[str]]:
    """
    Indexes session entries by verification status.
    """
    indexes = {}
    for e in entries:
        status = e.get("session_verification_status", "UNKNOWN")
        eid = e.get("session_registry_entry_id")
        indexes.setdefault(status, []).append(eid)
    return {k: sorted(v) for k, v in indexes.items()}


def index_waveguide_governed_compiler_sessions_by_rc(
    entries: List[Dict[str, Any]]
) -> Dict[str, List[str]]:
    """
    Indexes session entries by Release Candidate ID.
    """
    indexes = {}
    for e in entries:
        rc_id = e.get("rc_id", "UNKNOWN")
        eid = e.get("session_registry_entry_id")
        indexes.setdefault(rc_id, []).append(eid)
    return {k: sorted(v) for k, v in indexes.items()}


def index_waveguide_governed_compiler_sessions_by_profile(
    entries: List[Dict[str, Any]]
) -> Dict[str, List[str]]:
    """
    Indexes session entries by compiler profile.
    """
    indexes = {}
    for e in entries:
        prof = e.get("compiler_profile", "UNKNOWN") or "NONE"
        eid = e.get("session_registry_entry_id")
        indexes.setdefault(prof, []).append(eid)
    return {k: sorted(v) for k, v in indexes.items()}


if __name__ == "__main__":
    report_path = "docs/SOL_WAVEGUIDE_GOVERNED_COMPILER_SESSION_VERIFIER_REPORT.json"
    registry = build_waveguide_governed_compiler_session_registry(report_path)

    output_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_GOVERNED_COMPILER_SESSION_REGISTRY.json")
    export_waveguide_governed_compiler_session_registry(registry, output_path)

    print("Successfully generated and exported session registry:")
    print(f"  - {output_path}")
    print(summarize_waveguide_governed_compiler_session_registry(registry))
