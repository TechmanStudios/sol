# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL PDM Byte Slice & Byte ALU
=============================
Defines the reusable 8-bit Phase-Division Multiplexed byte-slice cell and its
pure deterministic reference arithmetic/bitwise operations, modulation, and wave sampling.
"""

import math
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Callable
from sol_phase_alignment import PhaseAlignmentTable

@dataclass
class ByteALUResult:
    operation: str
    lane_id: int
    a: int
    b: Optional[int]
    result: int
    carry_out: int
    flags: Dict[str, bool]
    evidence: Dict[str, Any]

@dataclass
class PDMCarrier:
    period: float
    omega: float

@dataclass
class PDMQuadratureChannel:
    bit_index: int
    carrier_period: float
    angular_frequency: float
    quadrature: str  # "sin" or "cos"
    phase: float
    amplitude: float
    active: bool

@dataclass
class PDMEncodedByte:
    lane_id: int
    value: int
    channels: List[PDMQuadratureChannel]

class PDMByteSlice:
    """
    Represents an 8-bit PDM byte slice mapping 8 logical bit channels
    to 4 stable carrier periods across 2 quadratures (sine & cosine).
    """
    def __init__(
        self,
        lane_id: int,
        bit_offset: int,
        periods: Optional[List[float]] = None,
        quadratures: Optional[List[str]] = None,
        calibrated_phases: Optional[Dict[str, float]] = None,
        phase_table: Optional[PhaseAlignmentTable] = None
    ):
        self.lane_id = lane_id
        self.bit_offset = bit_offset
        self.phase_table = phase_table
        # Default stable periods [11.0, 13.0, 17.0, 19.0] to avoid resonance wall
        self.periods = periods if periods is not None else [11.0, 13.0, 17.0, 19.0]
        self.quadratures = quadratures if quadratures is not None else ["sin", "cos"]
        self.calibrated_phases = calibrated_phases if calibrated_phases is not None else {}
        self.channel_map_list = self._initialize_channel_map()

    def _initialize_channel_map(self) -> List[Dict[str, Any]]:
        """Maps each of the 8 bits in the slice to a period and quadrature."""
        mapping = []
        bit_idx = 0
        for period in self.periods:
            for quad in self.quadratures:
                mapping.append({
                    "bit_index": self.bit_offset + bit_idx,
                    "period": period,
                    "quadrature": quad
                })
                bit_idx += 1
        return mapping

    def channel_map(self) -> List[Dict[str, Any]]:
        """Exposes the internal channel mapping details."""
        return self.channel_map_list

    def modulate(self, byte_value: int) -> Dict[str, float]:
        """Modulates an 8-bit integer into carrier amplitudes (Phase 0/1 backward compatibility)."""
        amplitudes = {}
        for item in self.channel_map_list:
            bit_pos = item["bit_index"] - self.bit_offset
            bit_val = (byte_value >> bit_pos) & 1
            key = f"P_{item['period']}_{item['quadrature']}"
            amplitudes[key] = 1.0 if bit_val == 1 else -1.0
        return amplitudes

    def demodulate(self, amplitudes: Dict[str, float]) -> int:
        """Demodulates carrier amplitudes back to an 8-bit integer (Phase 0/1 backward compatibility)."""
        byte_value = 0
        for item in self.channel_map_list:
            key = f"P_{item['period']}_{item['quadrature']}"
            amp = amplitudes.get(key, 0.0)
            if amp > 0.0:
                bit_pos = item["bit_index"] - self.bit_offset
                byte_value |= (1 << bit_pos)
        return byte_value

    # ---- Phase 4: Deterministic wave encoding and decoding ----

    def encode_byte(self, value: int, amplitude: float = 1.0) -> PDMEncodedByte:
        """
        Encodes an 8-bit value into a PDMEncodedByte containing 8 logical quadrature channels.
        """
        val_masked = value & 0xFF
        channels = []
        
        for idx, item in enumerate(self.channel_map_list):
            bit_pos = item["bit_index"] - self.bit_offset
            bit_active = bool((val_masked >> bit_pos) & 1)
            
            period = item["period"]
            quad = item["quadrature"]
            
            # w = 2*pi/T
            omega = 2.0 * math.pi / period
            
            phase_offset = 0.0
            if self.phase_table is not None:
                for entry in self.phase_table.entries:
                    if abs(entry.carrier_period - period) < 1e-5 and entry.quadrature == quad:
                        phase_offset = entry.calibrated_phase
                        break
                else:
                    phase_offset = self.calibrated_phases.get(f"P_{period}_{quad}", 0.0)
            else:
                phase_offset = self.calibrated_phases.get(f"P_{period}_{quad}", 0.0)
            
            # Amplitude is gated by active bit state
            ch_amp = amplitude if bit_active else 0.0
            
            channels.append(PDMQuadratureChannel(
                bit_index=item["bit_index"],
                carrier_period=period,
                angular_frequency=omega,
                quadrature=quad,
                phase=phase_offset,
                amplitude=ch_amp,
                active=bit_active
            ))
            
        return PDMEncodedByte(lane_id=self.lane_id, value=val_masked, channels=channels)

    def decode_reference(self, encoded_byte: PDMEncodedByte) -> int:
        """
        Reconstructs the 8-bit byte value from the PDMEncodedByte channel states.
        """
        byte_value = 0
        for ch in encoded_byte.channels:
            if ch.active:
                bit_pos = ch.bit_index - self.bit_offset
                byte_value |= (1 << bit_pos)
        return byte_value

    # ---- Deterministic Byte ALU reference methods ----

    def add8(self, a: int, b: int, carry_in: int = 0) -> ByteALUResult:
        """Add two 8-bit integers with a carry-in."""
        a_masked = a & 0xFF
        b_masked = b & 0xFF
        c_in = carry_in & 1
        
        raw_sum = a_masked + b_masked + c_in
        result = raw_sum & 0xFF
        carry_out = 1 if raw_sum > 0xFF else 0
        
        flags = {
            "zero": result == 0,
            "negative": bool(result & 0x80),
            "overflow": bool(((a_masked ^ result) & (b_masked ^ result)) & 0x80)
        }
        
        evidence = {
            "raw_sum": raw_sum,
            "a_binary": bin(a_masked),
            "b_binary": bin(b_masked),
            "carry_in": c_in
        }
        
        return ByteALUResult(
            operation="add",
            lane_id=self.lane_id,
            a=a_masked,
            b=b_masked,
            result=result,
            carry_out=carry_out,
            flags=flags,
            evidence=evidence
        )

    def sub8(self, a: int, b: int, borrow_in: int = 0) -> ByteALUResult:
        """Subtract two 8-bit integers with a borrow-in."""
        a_masked = a & 0xFF
        b_masked = b & 0xFF
        b_in = borrow_in & 1
        
        raw_diff = a_masked - b_masked - b_in
        result = raw_diff & 0xFF
        carry_out = 1 if raw_diff < 0 else 0
        
        flags = {
            "zero": result == 0,
            "negative": bool(result & 0x80),
            "overflow": bool(((a_masked ^ b_masked) & (a_masked ^ result)) & 0x80)
        }
        
        evidence = {
            "raw_diff": raw_diff,
            "a_binary": bin(a_masked),
            "b_binary": bin(b_masked),
            "borrow_in": b_in
        }
        
        return ByteALUResult(
            operation="sub",
            lane_id=self.lane_id,
            a=a_masked,
            b=b_masked,
            result=result,
            carry_out=carry_out,
            flags=flags,
            evidence=evidence
        )

    def and8(self, a: int, b: int) -> ByteALUResult:
        """Bitwise AND of two 8-bit integers."""
        a_masked = a & 0xFF
        b_masked = b & 0xFF
        result = a_masked & b_masked
        
        flags = {
            "zero": result == 0,
            "negative": bool(result & 0x80)
        }
        
        return ByteALUResult(
            operation="and",
            lane_id=self.lane_id,
            a=a_masked,
            b=b_masked,
            result=result,
            carry_out=0,
            flags=flags,
            evidence={}
        )

    def or8(self, a: int, b: int) -> ByteALUResult:
        """Bitwise OR of two 8-bit integers."""
        a_masked = a & 0xFF
        b_masked = b & 0xFF
        result = a_masked | b_masked
        
        flags = {
            "zero": result == 0,
            "negative": bool(result & 0x80)
        }
        
        return ByteALUResult(
            operation="or",
            lane_id=self.lane_id,
            a=a_masked,
            b=b_masked,
            result=result,
            carry_out=0,
            flags=flags,
            evidence={}
        )

    def xor8(self, a: int, b: int) -> ByteALUResult:
        """Bitwise XOR of two 8-bit integers."""
        a_masked = a & 0xFF
        b_masked = b & 0xFF
        result = a_masked ^ b_masked
        
        flags = {
            "zero": result == 0,
            "negative": bool(result & 0x80)
        }
        
        return ByteALUResult(
            operation="xor",
            lane_id=self.lane_id,
            a=a_masked,
            b=b_masked,
            result=result,
            carry_out=0,
            flags=flags,
            evidence={}
        )

    def not8(self, a: int) -> ByteALUResult:
        """Bitwise NOT of an 8-bit integer."""
        a_masked = a & 0xFF
        result = (~a_masked) & 0xFF
        
        flags = {
            "zero": result == 0,
            "negative": bool(result & 0x80)
        }
        
        return ByteALUResult(
            operation="not",
            lane_id=self.lane_id,
            a=a_masked,
            b=None,
            result=result,
            carry_out=0,
            flags=flags,
            evidence={}
        )

# ---- Phase 4: Deterministic Wave Sampling Helpers ----

def sample_channel(channel: PDMQuadratureChannel, t: float, envelope_func: Optional[Callable[[float], float]] = None) -> float:
    """
    Returns the wave signal amplitude for a single quadrature channel at time t.
    Optionally modulated by a custom envelope function.
    """
    # Active state gates signal generation
    if not channel.active or channel.amplitude == 0.0:
        return 0.0
        
    angle = channel.angular_frequency * t + channel.phase
    if channel.quadrature == "sin":
        val = channel.amplitude * math.sin(angle)
    else:
        val = channel.amplitude * math.cos(angle)
        
    if envelope_func is not None:
        val *= envelope_func(t)
        
    return val

def sample_encoded_byte(encoded_byte: PDMEncodedByte, t: float, envelope_func: Optional[Callable[[float], float]] = None) -> float:
    """
    Combines the signal wave amplitudes of all 8 channels in an encoded byte at time t.
    """
    return sum(sample_channel(ch, t, envelope_func) for ch in encoded_byte.channels)

def sample_wave_packet(encoded_byte: PDMEncodedByte, t_values: List[float], envelope_func: Optional[Callable[[float], float]] = None) -> List[float]:
    """
    Generates combined wave packet signal samples over a sequence of time values.
    """
    return [sample_encoded_byte(encoded_byte, t, envelope_func) for t in t_values]
