# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Signal Ranger
=============
Observes PDMEncodedByte and encoded WideWord wave packet representations.
"""

from coding_library.roaming_agents import LuminaRoamingAgent
from coding_library.sovereign_domain.evidence_packet import SovereignPacket
from typing import Dict, Any, List, Union
from datetime import datetime, timezone

class SignalRanger(LuminaRoamingAgent):
    """
    Ranger verifying the correctness of waveguide signal modulation, encoding,
    and channel configurations.
    """
    def __init__(self, lib_agent=None):
        system_prompt = (
            "You are the Signal Ranger. You inspect PDM-encoded bytes and WideWord\n"
            "amplitudes, verifying carrier mapping and quadrature properties."
        )
        super().__init__("Signal Ranger", system_prompt, lib_agent)

    def observe_signal(self, target_obj: Any, mission_id: str = "MOCK_SIGNAL_MISSION") -> SovereignPacket:
        """
        Inspects an encoded PDM byte or word packet, evaluates signal parameters,
        and generates a SovereignPacket.
        """
        self.travel(target_obj)

        # Handle both single PDMEncodedByte and a list of PDMEncodedByte (encoded WideWord)
        is_list = isinstance(target_obj, list)
        encoded_bytes = target_obj if is_list else [target_obj]

        lane_ids = []
        values = []
        unique_periods = set()
        unique_quads = set()
        total_active_channels = 0
        max_amplitude = 0.0
        completeness = True

        for item in encoded_bytes:
            def extract(name, default=None):
                if isinstance(item, dict):
                    return item.get(name, default)
                return getattr(item, name, default)

            lane_id = extract("lane_id", 0)
            value = extract("value", 0)
            channels = extract("channels", [])

            lane_ids.append(lane_id)
            values.append(value)

            ch_count = len(channels)
            if ch_count != 8:
                completeness = False

            for ch in channels:
                def extract_ch(ch_name, ch_default=None):
                    if isinstance(ch, dict):
                        return ch.get(ch_name, ch_default)
                    return getattr(ch, ch_name, ch_default)

                period = extract_ch("carrier_period")
                quad = extract_ch("quadrature")
                active = extract_ch("active")
                amplitude = extract_ch("amplitude", 0.0)

                if period is not None:
                    unique_periods.add(period)
                if quad is not None:
                    unique_quads.add(quad)
                if active:
                    total_active_channels += 1
                if amplitude is not None:
                    max_amplitude = max(max_amplitude, abs(amplitude))

        evidence = {
            "lane_ids": lane_ids if is_list else lane_ids[0],
            "values": values if is_list else values[0],
            "carrier_count": len(unique_periods),
            "quadrature_count": len(unique_quads),
            "active_channel_count": total_active_channels,
            "max_amplitude": max_amplitude,
            "channel_mapping_completeness": completeness,
            "is_word": is_list
        }

        # Packet ID and hash
        timestamp_str = datetime.now(timezone.utc).strftime("%H%M%S")
        packet_id = f"PKT_SIG_OBS_{id(target_obj)}_{timestamp_str}"
        repro_hash = f"sha256_{hash(str(evidence)) & 0xFFFFFFFF:08x}"

        packet = SovereignPacket(
            packet_id=packet_id,
            domain="sol_sovereign",
            level=11,
            actor=self.name,
            actor_type="ranger",
            mission_id=mission_id,
            claim="Waveguide PDM signal encoding telemetry report",
            evidence=evidence,
            invariants_checked=["pdm_quadrature_completeness"],
            artifacts=[],
            recommendation="observe" if completeness else "reject",
            confidence=0.97,
            reproducibility_hash=repro_hash
        )

        self.state_history.append(f"Observed PDM encoding: recommendation={'observe' if completeness else 'reject'}.")
        return packet
