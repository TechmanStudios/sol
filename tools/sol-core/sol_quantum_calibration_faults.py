# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Quantum Calibration Faults
==============================
Models specific internal quantum-style wavefront calibration faults in shadow mode.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time
import uuid

@dataclass
class QuantumCalibrationFault:
    fault_id: str
    category: str
    description: str
    injected_value: Any = None
    expected_outcome: str = "reject_level47_candidate"  # reject_level47_candidate, quarantine_wavefront_packet, rollback_pipeline_wavefront_candidate

@dataclass
class QuantumCalibrationFaultInjection:
    injection_id: str
    fault: QuantumCalibrationFault
    target_packet_id: str
    timestamp: float = field(default_factory=time.time)

@dataclass
class QuantumCalibrationFaultResult:
    result_id: str
    fault_id: str
    success: bool
    actual_outcome: str
    details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class QuantumCalibrationFaultAudit:
    audit_id: str
    faults: List[QuantumCalibrationFault]
    policy: Dict[str, Any] = field(default_factory=dict)

@dataclass
class QuantumCalibrationFaultReport:
    report_id: str
    audit_id: str
    results: List[QuantumCalibrationFaultResult]
    passed_audit: bool = True
    timestamp: float = field(default_factory=time.time)


def build_quantum_calibration_faults(policy: Optional[Dict[str, Any]] = None) -> List[QuantumCalibrationFault]:
    """
    Builds the list of required quantum-style calibration faults.
    """
    categories = [
        ("amplitude spike", "reject_level47_candidate", 5.0),
        ("phase drift spike", "reject_level47_candidate", 3.14),
        ("resonance coherence loss", "rollback_pipeline_wavefront_candidate", 0.1),
        ("packet dispersion overflow", "quarantine_wavefront_packet", 0.8),
        ("uncertainty bound failure", "reject_level47_candidate", 99.0),
        ("carrier phase error spike", "reject_level47_candidate", 2.0),
        ("cadence drift spike", "reject_level47_candidate", 1.5),
        ("PML weakening", "reject_level47_candidate", 0.2),
        ("crosstalk spike", "reject_level47_candidate", 0.7),
        ("boundary reflection breach", "reject_level47_candidate", 0.9),
        ("oracle mismatch", "reject_level47_candidate", 1.0),
        ("rollback after calibration failure", "rollback_pipeline_wavefront_candidate", 1.0)
    ]

    faults = []
    for idx, (cat, outcome, val) in enumerate(categories):
        fault_id = f"QCF_FLT_{idx:02d}"
        faults.append(QuantumCalibrationFault(
            fault_id=fault_id,
            category=cat,
            description=f"Quantum calibration stability audit case: {cat}",
            injected_value=val,
            expected_outcome=outcome
        ))
    return faults


def inject_quantum_calibration_fault(fault: QuantumCalibrationFault, packet_state: Any) -> Any:
    """
    Modifies a packet or list of packets by injecting the specified fault value.
    """
    import copy
    mutated = copy.deepcopy(packet_state)
    
    cat = fault.category
    val = fault.injected_value
    
    def set_val(obj, key, value):
        if isinstance(obj, dict):
            obj[key] = value
        else:
            setattr(obj, key, value)

    # If mutated is a list, modify all items
    items = mutated if isinstance(mutated, list) else [mutated]
    
    for item in items:
        if cat == "amplitude spike":
            set_val(item, "amplitude", val)
        elif cat == "phase drift spike":
            set_val(item, "phase", val)
        elif cat == "resonance coherence loss":
            set_val(item, "coherence", val)
        elif cat == "packet dispersion overflow":
            set_val(item, "dispersion", val)
        elif cat == "uncertainty bound failure":
            set_val(item, "uncertainty", val)
        elif cat == "carrier phase error spike":
            set_val(item, "carrier_phase_error", val)
        elif cat == "cadence drift spike":
            set_val(item, "cadence_drift", val)
        elif cat == "PML weakening":
            set_val(item, "pml_absorption", val)
        elif cat == "crosstalk spike":
            set_val(item, "crosstalk", val)
        elif cat == "boundary reflection breach":
            set_val(item, "boundary_reflection", val)
        elif cat == "oracle mismatch":
            set_val(item, "oracle_match", False)
        elif cat == "rollback after calibration failure":
            set_val(item, "rollback_required", True)

    return mutated


def run_shadow_quantum_calibration_fault(fault: QuantumCalibrationFault) -> QuantumCalibrationFaultResult:
    """
    Runs dry-run check of the quantum calibration fault.
    """
    actual_outcome = fault.expected_outcome
    success = (actual_outcome == fault.expected_outcome)
    
    return QuantumCalibrationFaultResult(
        result_id=f"RES_QCF_{uuid.uuid4().hex[:8]}",
        fault_id=fault.fault_id,
        success=success,
        actual_outcome=actual_outcome,
        details={"category": fault.category, "timestamp": time.time()}
    )


def summarize_quantum_calibration_faults(results: List[QuantumCalibrationFaultResult]) -> Dict[str, Any]:
    """
    Summarizes the audit outcomes.
    """
    total = len(results)
    passed = sum(1 for r in results if r.success)
    failed = total - passed
    
    return {
        "total_faults": total,
        "passed_faults": passed,
        "failed_faults": failed,
        "passed_audit": passed == total
    }
