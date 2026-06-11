# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Quantum Wavefront Calibration Protocol
==========================================
State machine coordinating the preparation, shadow calibration, verification,
and final commit or abort of the quantum wavefront calibration protocol.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time
import uuid

@dataclass
class QuantumWavefrontPrepareState:
    baseline_captured: bool = False
    rollback_ref_captured: bool = False
    cadence_valid: bool = False
    pml_valid: bool = False
    carrier_bindings_valid: bool = False
    core_assembly_valid: bool = False
    errors: List[str] = field(default_factory=list)

@dataclass
class QuantumWavefrontCalibrateState:
    shadow_run_complete: bool = False
    oracle_match: bool = True
    errors: List[str] = field(default_factory=list)

@dataclass
class QuantumWavefrontVerifyState:
    uncertainty_bounded: bool = False
    errors: List[str] = field(default_factory=list)

@dataclass
class QuantumWavefrontCommitState:
    committed: bool = False
    ranger_packet_emitted: bool = False
    timestamp: float = 0.0

@dataclass
class QuantumWavefrontAbortState:
    aborted: bool = False
    reason: str = ""
    timestamp: float = 0.0

@dataclass
class QuantumWavefrontProtocol:
    protocol_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    prepare_state: QuantumWavefrontPrepareState = field(default_factory=QuantumWavefrontPrepareState)
    calibrate_state: QuantumWavefrontCalibrateState = field(default_factory=QuantumWavefrontCalibrateState)
    verify_state: QuantumWavefrontVerifyState = field(default_factory=QuantumWavefrontVerifyState)
    commit_state: QuantumWavefrontCommitState = field(default_factory=QuantumWavefrontCommitState)
    abort_state: QuantumWavefrontAbortState = field(default_factory=QuantumWavefrontAbortState)
    current_stage: str = "init"  # "init", "prepared", "calibrated", "verified", "committed", "aborted"

@dataclass
class QuantumWavefrontProtocolReport:
    report_id: str
    protocol: QuantumWavefrontProtocol
    success: bool
    errors: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


def prepare_quantum_wavefront_protocol(
    protocol: QuantumWavefrontProtocol
) -> QuantumWavefrontProtocol:
    """
    Executes preparation checks: baseline, rollback refs, cadence, PML, carriers, assembly.
    """
    meta = protocol.metadata or {}
    prep = protocol.prepare_state
    
    # 1. Capture baseline & rollback snapshot refs
    prep.baseline_captured = bool(meta.get("baseline"))
    prep.rollback_ref_captured = bool(meta.get("rollback_snapshot"))

    # 2. Validate cadence profile
    prep.cadence_valid = not meta.get("unstable_cadence") and bool(meta.get("cadence_profile"))

    # 3. Validate PML
    prep.pml_valid = not meta.get("pml_weakened") and bool(meta.get("pml_state"))

    # 4. Validate Carrier bindings
    prep.carrier_bindings_valid = not meta.get("carrier_identity_broken") and bool(meta.get("carrier_registry"))

    # 5. Validate Core Assembly
    prep.core_assembly_valid = not meta.get("invalid_core_group") and bool(meta.get("core_assembly_report"))

    prep.errors = []
    if not prep.baseline_captured:
        prep.errors.append("Prepare failed: missing calibration baseline.")
    if not prep.rollback_ref_captured:
        prep.errors.append("Prepare failed: missing rollback reference snapshot.")
    if not prep.cadence_valid:
        prep.errors.append("Prepare failed: unstable or invalid cadence.")
    if not prep.pml_valid:
        prep.errors.append("Prepare failed: invalid or weakened PML boundary.")
    if not prep.carrier_bindings_valid:
        prep.errors.append("Prepare failed: carrier bindings broken or missing registry.")
    if not prep.core_assembly_valid:
        prep.errors.append("Prepare failed: invalid core assembly reference.")

    if not prep.errors:
        protocol.current_stage = "prepared"
    else:
        protocol.current_stage = "aborted"
        protocol.abort_state.aborted = True
        protocol.abort_state.reason = f"Prepare failure: {'; '.join(prep.errors)}"
        protocol.abort_state.timestamp = time.time()

    return protocol


def calibrate_quantum_wavefront_shadow(
    protocol: QuantumWavefrontProtocol
) -> QuantumWavefrontProtocol:
    """
    Executes dry-run shadow calibration and checks oracle match.
    """
    if protocol.current_stage != "prepared":
        protocol.current_stage = "aborted"
        protocol.abort_state.aborted = True
        protocol.abort_state.reason = f"Calibration failed: protocol is not prepared. Current stage: {protocol.current_stage}"
        protocol.abort_state.timestamp = time.time()
        return protocol

    meta = protocol.metadata or {}
    cal = protocol.calibrate_state
    
    cal.shadow_run_complete = True
    cal.oracle_match = meta.get("oracle_match", True)
    
    cal.errors = []
    if not cal.oracle_match:
        cal.errors.append("Calibration failed: simulator-oracle arithmetic mismatch.")

    if not cal.errors:
        protocol.current_stage = "calibrated"
    else:
        protocol.current_stage = "aborted"
        protocol.abort_state.aborted = True
        protocol.abort_state.reason = f"Calibration failure: {'; '.join(cal.errors)}"
        protocol.abort_state.timestamp = time.time()

    return protocol


def verify_quantum_wavefront_protocol(
    protocol: QuantumWavefrontProtocol
) -> QuantumWavefrontProtocol:
    """
    Verifies calibrated states, checking uncertainty boundaries.
    """
    if protocol.current_stage != "calibrated":
        protocol.current_stage = "aborted"
        protocol.abort_state.aborted = True
        protocol.abort_state.reason = f"Verification failed: protocol is not calibrated. Current stage: {protocol.current_stage}"
        protocol.abort_state.timestamp = time.time()
        return protocol

    meta = protocol.metadata or {}
    ver = protocol.verify_state
    
    # Check if uncertainty report indicates bounded/valid uncertainty
    ver.uncertainty_bounded = not meta.get("unbounded_uncertainty") and meta.get("uncertainty_bounded", True)
    
    ver.errors = []
    if not ver.uncertainty_bounded:
        ver.errors.append("Verification failed: unbounded wavefront uncertainty detected.")

    if not ver.errors:
        protocol.current_stage = "verified"
    else:
        protocol.current_stage = "aborted"
        protocol.abort_state.aborted = True
        protocol.abort_state.reason = f"Verification failure: {'; '.join(ver.errors)}"
        protocol.abort_state.timestamp = time.time()

    return protocol


def commit_quantum_wavefront_shadow(
    protocol: QuantumWavefrontProtocol
) -> QuantumWavefrontProtocol:
    """
    Finalizes the protocol in shadow/sandbox mode. Emits ranger packet reference.
    """
    if protocol.current_stage != "verified":
        protocol.current_stage = "aborted"
        protocol.abort_state.aborted = True
        protocol.abort_state.reason = f"Commit failed: protocol is not verified. Current stage: {protocol.current_stage}"
        protocol.abort_state.timestamp = time.time()
        return protocol

    com = protocol.commit_state
    com.committed = True
    com.ranger_packet_emitted = True
    com.timestamp = time.time()

    protocol.current_stage = "committed"
    return protocol


def abort_quantum_wavefront_protocol(
    protocol: QuantumWavefrontProtocol,
    reason: str
) -> QuantumWavefrontProtocol:
    """
    Aborts execution, recording reason.
    """
    protocol.abort_state.aborted = True
    protocol.abort_state.reason = reason
    protocol.abort_state.timestamp = time.time()
    protocol.current_stage = "aborted"
    return protocol
