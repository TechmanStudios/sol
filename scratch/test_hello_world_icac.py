#!/usr/bin/env python3
"""
SOL ICAC "Hello, World." Demodulation Experiment
=================================================
1. Encodes each character in the string "Hello, World." as a unique frequency.
2. Compiles a physical tree-like waveguide network (Source -> Mixer -> Receiver bank).
3. Transmits character wave packets sequentially into the conduit from the Source.
4. Dynamically modulates Receiver edge conductances (parametric resonant gates).
5. Integrates net pressure flux at the Receivers to identify the transmitted symbols.
"""

import sys
import os
import math
import time
from pathlib import Path
import numpy as np

# Path configurations
_SOL_ROOT = Path(__file__).resolve().parent.parent

# Force bind tools/sol-core/telemetry.py to sys.modules['telemetry'] to prevent collisions
import importlib.util
telemetry_path = _SOL_ROOT / "tools" / "sol-core" / "telemetry.py"
spec = importlib.util.spec_from_file_location("telemetry", telemetry_path)
if spec and spec.loader:
    telemetry_mod = importlib.util.module_from_spec(spec)
    sys.modules["telemetry"] = telemetry_mod
    spec.loader.exec_module(telemetry_mod)
    telemetry_mod._TELEMETRY_ENABLED = False

sys.path.insert(0, str(_SOL_ROOT / "tools" / "sol-core"))
from sol_engine import SOLEngine

def run_hello_world_icac():
    print("==========================================================================")
    print("  HELLO WORLD IN-CONDUIT ANALOG COMPUTING (ICAC) DEMODULATOR")
    print("==========================================================================")
    
    target_string = "Hello, World."
    alphabet = sorted(list(set(target_string)))
    print(f"Target String: {target_string}")
    print(f"Alphabet: {alphabet}")
    
    # Map alphabet to distinct frequencies in range [2.5, 5.5] rad/s
    char_frequencies = {}
    for idx, char in enumerate(alphabet):
        char_frequencies[char] = 2.5 + (idx / max(1, len(alphabet) - 1)) * 3.0
        
    print("\nFrequency Mapping:")
    for char, freq in char_frequencies.items():
        print(f"  '{char}' -> {freq:.4f} rad/s (Period: {2*math.pi/freq:.2f}s)")
        
    # Build ICAC Graph
    raw_nodes = [
        {"id": "Source", "label": "Source", "group": "tech", "rho": 10.0},
        {"id": "Mixer", "label": "Mixer", "group": "bridge", "rho": 10.0}
    ]
    for char in alphabet:
        char_id = f"char_{ord(char)}"
        raw_nodes.append({
            "id": char_id,
            "label": f"Receiver_{char}",
            "group": "spirit",
            "rho": 10.0
        })
        
    raw_edges = [
        {"from": "Source", "to": "Mixer", "w0": 1.0}
    ]
    for char in alphabet:
        char_id = f"char_{ord(char)}"
        raw_edges.append({"from": "Mixer", "to": char_id, "w0": 1.0})
        
    # Setup engine
    c_press = 5.0
    damping = 0.02
    dt = 0.05
    steps = 400 # 20 seconds of simulation time
    
    engine = SOLEngine.from_graph(raw_nodes, raw_edges, c_press=c_press, damping=damping)
    engine.integration_mode = "forward_euler"
    engine.physics.psi_diffusion = 0.0
    engine.physics.psi_relax_base = 0.0
    engine.physics.conductance_gamma = 3.0
    engine.physics.conductance_base = 1.5
    engine.physics.mhd_cfg = None
    engine.physics.jeans_cfg = None
    engine.physics.vort_cfg = None
    engine.save_baseline()
    
    decoded_chars = []
    
    print(f"\nRunning sequential demodulation epoch loop...")
    for char_idx, target_char in enumerate(target_string):
        engine.restore_baseline()
        # Reset node states to exactly 10.0 and fluxes to 0.0
        for n in engine.physics.nodes:
            n["rho"] = 10.0
            n["p"] = 0.0
        for e in engine.physics.edges:
            e["flux"] = 0.0
            
        omega_target = char_frequencies[target_char]
        
        print(f"\n[Epoch {char_idx+1}/13] Transmitting '{target_char}' (freq: {omega_target:.4f} rad/s)...")
        
        for s in range(steps):
            t = s * dt
            # Drive Source wave
            engine.physics.node_by_id["Source"]["rho"] = 10.0 + 5.0 * math.sin(omega_target * t)
            
            # Parametrically gate the receiver nodes
            for char in alphabet:
                char_id = f"char_{ord(char)}"
                omega_c = char_frequencies[char]
                # Modulate belief field to drive conductance variation
                engine.physics.node_by_id[char_id]["psi"] = math.sin(omega_c * t)
                
            engine.step(dt=dt, c_press=c_press, damping=damping)
            
        # Analyze receiver deviation magnitudes
        deviations = {}
        for char in alphabet:
            char_id = f"char_{ord(char)}"
            final_rho = engine.physics.node_by_id[char_id]["rho"]
            deviations[char] = abs(final_rho - 10.0)
            
        # Determine the winner
        detected_char = max(deviations, key=deviations.get)
        decoded_chars.append(detected_char)
        
        # Print epoch summary
        print(f"  Deviations:")
        sorted_devs = sorted(deviations.items(), key=lambda x: x[1], reverse=True)
        for c, dev in sorted_devs[:3]:
            print(f"    '{c}': dev = {dev:.4f}")
        print(f"  -> Detected Character: '{detected_char}' (Expected: '{target_char}') - {'MATCH' if detected_char == target_char else 'FAIL'}")
        
    decoded_string = "".join(decoded_chars)
    print("\n==========================================================================")
    print(f"DEMODULATION COMPLETE: '{decoded_string}'")
    print("==========================================================================")
    
if __name__ == "__main__":
    run_hello_world_icac()
