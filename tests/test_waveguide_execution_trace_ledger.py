# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Tests for SOL Waveguide Execution Trace Registry / Rejection Ledger
"""

import os
import json
import pytest

from sol_waveguide_execution_trace_ledger import (
    build_waveguide_execution_trace_entry,
    validate_waveguide_execution_trace_entry,
    build_waveguide_execution_trace_ledger,
    validate_waveguide_execution_trace_ledger,
    summarize_waveguide_execution_trace_ledger,
    export_waveguide_execution_trace_ledger,
    compare_waveguide_execution_trace_ledgers,
    hash_waveguide_execution_trace_entry,
    hash_waveguide_execution_trace_ledger,
    index_waveguide_execution_trace_entries_by_status
)
from sol_waveguide_rc_promotion_ledger import REPO_ROOT


def test_trace_entry_builds():
    rec1_path = "docs/SOL_WAVEGUIDE_GOVERNED_PASS_EXECUTION_RC1.json"
    rec2_path = "docs/SOL_WAVEGUIDE_GOVERNED_PASS_EXECUTION_RC2.json"
    rej_path = "docs/SOL_WAVEGUIDE_GOVERNED_PASS_EXECUTION_REJECTION_EXAMPLE.json"

    entry1 = build_waveguide_execution_trace_entry(rec1_path, record_path=rec1_path)
    entry2 = build_waveguide_execution_trace_entry(rec2_path, record_path=rec2_path)
    entry3 = build_waveguide_execution_trace_entry(rej_path, record_path=rej_path)

    assert entry1.rc_id == "SOL-WAVEGUIDE-RC1"
    assert entry2.rc_id == "SOL-WAVEGUIDE-RC2"
    assert entry3.rc_id == "SOL-WAVEGUIDE-RC1"

    assert entry1.execution_status == "trace_executed"
    assert entry2.execution_status == "trace_executed"
    assert entry3.execution_status == "trace_rejected"


def test_trace_entry_digest_excludes_self():
    rec1_path = "docs/SOL_WAVEGUIDE_GOVERNED_PASS_EXECUTION_RC1.json"
    entry = build_waveguide_execution_trace_entry(rec1_path, record_path=rec1_path)

    e_dict = entry.__dict__.copy()
    e_dict["trace_entry_digest"] = "different_digest_value"

    h1 = hash_waveguide_execution_trace_entry(entry)
    h2 = hash_waveguide_execution_trace_entry(e_dict)
    assert h1 == h2


def test_trace_entry_validates():
    rec1_path = "docs/SOL_WAVEGUIDE_GOVERNED_PASS_EXECUTION_RC1.json"
    rec2_path = "docs/SOL_WAVEGUIDE_GOVERNED_PASS_EXECUTION_RC2.json"
    rej_path = "docs/SOL_WAVEGUIDE_GOVERNED_PASS_EXECUTION_REJECTION_EXAMPLE.json"

    entry1 = build_waveguide_execution_trace_entry(rec1_path, record_path=rec1_path)
    entry2 = build_waveguide_execution_trace_entry(rec2_path, record_path=rec2_path)
    entry3 = build_waveguide_execution_trace_entry(rej_path, record_path=rej_path)

    ok1, reasons1 = validate_waveguide_execution_trace_entry(entry1)
    ok2, reasons2 = validate_waveguide_execution_trace_entry(entry2)
    ok3, reasons3 = validate_waveguide_execution_trace_entry(entry3)

    assert ok1 is True
    assert ok2 is True
    assert ok3 is True

    assert "TRACE_LEDGER_EXECUTED_ENTRY_INDEXED" in reasons1
    assert "TRACE_LEDGER_EXECUTED_ENTRY_INDEXED" in reasons2
    assert "TRACE_LEDGER_REJECTED_ENTRY_INDEXED" in reasons3


def test_invalid_record_blocks():
    # Empty/Invalid execution record
    entry = build_waveguide_execution_trace_entry({}, record_path="dummy_path")
    assert entry.execution_status == "trace_invalid"
    
    ok, reasons = validate_waveguide_execution_trace_entry(entry)
    assert ok is False
    assert "TRACE_LEDGER_EXECUTION_RECORD_INVALID" in reasons


def test_tampered_digest_fails():
    rec1_path = "docs/SOL_WAVEGUIDE_GOVERNED_PASS_EXECUTION_RC1.json"
    entry = build_waveguide_execution_trace_entry(rec1_path, record_path=rec1_path)

    # Tamper with digest
    entry.trace_entry_digest = "tampered_digest_value"
    ok, reasons = validate_waveguide_execution_trace_entry(entry)
    assert ok is False
    assert "TRACE_LEDGER_ENTRY_DIGEST_INVALID" in reasons


def test_executed_entry_constraints():
    rec1_path = "docs/SOL_WAVEGUIDE_GOVERNED_PASS_EXECUTION_RC1.json"
    entry = build_waveguide_execution_trace_entry(rec1_path, record_path=rec1_path)

    # Violate handler id
    entry.handler_id = ""
    entry.trace_entry_digest = hash_waveguide_execution_trace_entry(entry)
    ok, reasons = validate_waveguide_execution_trace_entry(entry)
    assert ok is False


def test_rejected_entry_constraints():
    rej_path = "docs/SOL_WAVEGUIDE_GOVERNED_PASS_EXECUTION_REJECTION_EXAMPLE.json"
    entry = build_waveguide_execution_trace_entry(rej_path, record_path=rej_path)

    # False claim of pass executed
    entry.pass_executed = True
    entry.trace_entry_digest = hash_waveguide_execution_trace_entry(entry)
    ok, reasons = validate_waveguide_execution_trace_entry(entry)
    assert ok is False


def test_ledger_builds_and_validates():
    rec1_path = "docs/SOL_WAVEGUIDE_GOVERNED_PASS_EXECUTION_RC1.json"
    rec2_path = "docs/SOL_WAVEGUIDE_GOVERNED_PASS_EXECUTION_RC2.json"
    rej_path = "docs/SOL_WAVEGUIDE_GOVERNED_PASS_EXECUTION_REJECTION_EXAMPLE.json"

    entry1 = build_waveguide_execution_trace_entry(rec1_path, record_path=rec1_path)
    entry2 = build_waveguide_execution_trace_entry(rec2_path, record_path=rec2_path)
    entry3 = build_waveguide_execution_trace_entry(rej_path, record_path=rej_path)

    ledger = build_waveguide_execution_trace_ledger([entry1, entry2, entry3])
    assert ledger.ledger_status == "ledger_valid"
    
    ok, reasons = validate_waveguide_execution_trace_ledger(ledger)
    assert ok is True
    assert "TRACE_LEDGER_VALID" in reasons
    assert "TRACE_LEDGER_DIGEST_VALID" in reasons


def test_ledger_digest_excludes_self():
    rec1_path = "docs/SOL_WAVEGUIDE_GOVERNED_PASS_EXECUTION_RC1.json"
    entry = build_waveguide_execution_trace_entry(rec1_path, record_path=rec1_path)
    ledger = build_waveguide_execution_trace_ledger([entry])

    l_dict = ledger.__dict__.copy()
    l_dict["ledger_digest"] = "different_ledger_digest_value"

    h1 = hash_waveguide_execution_trace_ledger(ledger)
    h2 = hash_waveguide_execution_trace_ledger(l_dict)
    assert h1 == h2


def test_ledger_counters_are_correct():
    rec1_path = "docs/SOL_WAVEGUIDE_GOVERNED_PASS_EXECUTION_RC1.json"
    rec2_path = "docs/SOL_WAVEGUIDE_GOVERNED_PASS_EXECUTION_RC2.json"
    rej_path = "docs/SOL_WAVEGUIDE_GOVERNED_PASS_EXECUTION_REJECTION_EXAMPLE.json"

    entry1 = build_waveguide_execution_trace_entry(rec1_path, record_path=rec1_path)
    entry2 = build_waveguide_execution_trace_entry(rec2_path, record_path=rec2_path)
    entry3 = build_waveguide_execution_trace_entry(rej_path, record_path=rej_path)

    ledger = build_waveguide_execution_trace_ledger([entry1, entry2, entry3])

    assert ledger.executed_count == 2
    assert ledger.rejected_count == 1
    assert ledger.invalid_count == 0

    assert ledger.rc1_execution_count == 1
    assert ledger.rc2_execution_count == 1
    assert ledger.rc1_rejection_count == 1
    assert ledger.rc2_rejection_count == 0


def test_ledger_helper_lists_are_sorted():
    rec1_path = "docs/SOL_WAVEGUIDE_GOVERNED_PASS_EXECUTION_RC1.json"
    rec2_path = "docs/SOL_WAVEGUIDE_GOVERNED_PASS_EXECUTION_RC2.json"
    rej_path = "docs/SOL_WAVEGUIDE_GOVERNED_PASS_EXECUTION_REJECTION_EXAMPLE.json"

    entry1 = build_waveguide_execution_trace_entry(rec1_path, record_path=rec1_path)
    entry2 = build_waveguide_execution_trace_entry(rec2_path, record_path=rec2_path)
    entry3 = build_waveguide_execution_trace_entry(rej_path, record_path=rej_path)

    ledger = build_waveguide_execution_trace_ledger([entry1, entry2, entry3])

    assert ledger.approved_handler_ids == sorted(ledger.approved_handler_ids)
    assert ledger.artifact_paths == sorted(ledger.artifact_paths)
    assert ledger.source_execution_record_digests == sorted(ledger.source_execution_record_digests)


def test_summarize_and_compare_are_deterministic():
    rec1_path = "docs/SOL_WAVEGUIDE_GOVERNED_PASS_EXECUTION_RC1.json"
    entry = build_waveguide_execution_trace_entry(rec1_path, record_path=rec1_path)
    ledger1 = build_waveguide_execution_trace_ledger([entry])
    ledger2 = build_waveguide_execution_trace_ledger([entry])

    s1 = summarize_waveguide_execution_trace_ledger(ledger1)
    s2 = summarize_waveguide_execution_trace_ledger(ledger2)
    assert s1 == s2

    diff = compare_waveguide_execution_trace_ledgers(ledger1, ledger2)
    assert len(diff) == 0


def test_artifacts_exist_on_disk():
    ledger_json = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_EXECUTION_TRACE_LEDGER.json")
    doc_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_EXECUTION_TRACE_LEDGER.md")

    assert os.path.exists(ledger_json)
    assert os.path.exists(doc_path)
