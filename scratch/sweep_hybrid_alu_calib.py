import sys
from pathlib import Path

# Add sol-core path
sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root / "tools" / "sol-core"))

# Force bind telemetry to prevent collisions
import importlib.util
telemetry_path = sol_root / "tools" / "sol-core" / "telemetry.py"
spec = importlib.util.spec_from_file_location("telemetry", telemetry_path)
if spec and spec.loader:
    telemetry_mod = importlib.util.module_from_spec(spec)
    sys.modules["telemetry"] = telemetry_mod
    spec.loader.exec_module(telemetry_mod)
    telemetry_mod._TELEMETRY_ENABLED = False

import os
os.environ["SOL_TELEMETRY_ENABLED"] = "false"

from sol_engine import SOLEngine

def build_simple_graph(psi_bias_C):
    nodes = [
        {'id': 'S_RA', 'group': 'semantic', 'rho': 5.0, 'psi': -1.0, 'psi_bias': -1.0, 'semanticMass': 20.0},
        {'id': 'S_RA_B', 'group': 'semantic', 'rho': 0.0, 'isBattery': True, 'psi': -1.0, 'psi_bias': -1.0, 'semanticMass': 20.0},
        {'id': 'S_RB', 'group': 'semantic', 'rho': 5.0, 'psi': -1.0, 'psi_bias': -1.0, 'semanticMass': 20.0},
        {'id': 'S_RB_B', 'group': 'semantic', 'rho': 0.0, 'isBattery': True, 'psi': -1.0, 'psi_bias': -1.0, 'semanticMass': 20.0},
        {'id': 'S_RC', 'group': 'semantic', 'rho': 5.0, 'psi': -1.0, 'psi_bias': psi_bias_C, 'semanticMass': 20.0},
        {'id': 'S_RC_B', 'group': 'semantic', 'rho': 0.0, 'isBattery': True, 'psi': -1.0, 'psi_bias': -1.0, 'semanticMass': 20.0},
        {'id': 'GATE_A', 'group': 'bridge', 'rho': 0.0, 'psi': -1.0, 'psi_bias': -1.0},
        {'id': 'GATE_B', 'group': 'bridge', 'rho': 0.0, 'psi': -1.0, 'psi_bias': -1.0},
        {'id': 'GATE_C', 'group': 'bridge', 'rho': 0.0, 'psi': -1.0, 'psi_bias': -1.0},
        {'id': 'P_Sum', 'group': 'processing', 'rho': 0.0, 'psi': 0.0, 'psi_bias': 0.0, 'semanticMass': 1.0}
    ]
    edges = [
        {'from': 'S_RA', 'to': 'S_RA_B', 'w0': 20.0},
        {'from': 'S_RB', 'to': 'S_RB_B', 'w0': 20.0},
        {'from': 'S_RC', 'to': 'S_RC_B', 'w0': 20.0},
        {'from': 'S_RA', 'to': 'GATE_A', 'w0': 5.0},
        {'from': 'GATE_A', 'to': 'P_Sum', 'w0': 5.0},
        {'from': 'S_RB', 'to': 'GATE_B', 'w0': 5.0},
        {'from': 'GATE_B', 'to': 'P_Sum', 'w0': 5.0},
        {'from': 'P_Sum', 'to': 'GATE_C', 'w0': 5.0},
        {'from': 'GATE_C', 'to': 'S_RC', 'w0': 5.0}
    ]
    return nodes, edges

def run_trial(input_A, input_B, psi_bias_C):
    nodes, edges = build_simple_graph(psi_bias_C)
    engine = SOLEngine.from_graph(nodes, edges, c_press=1.0, damping=0.01)
    engine.physics.conductance_max = 200.0
    engine.physics.conductance_min = 1e-7
    engine.physics.conductance_gamma = 8.0
    engine.physics.psi_diffusion = 1.2
    engine.physics.psi_relax_base = 8.0
    engine.physics.battery_cfg = {
        'qMax': 80.0, 'qThresh': 5.0, 'leakLambda': 0.01, 'avalancheGain': 5.0, 'resonanceBoost': 4.0,
        'dampingClamp': 0.1, 'flipThreshold': 0.65, 'collapseFactor': 0.10, 'resonanceDrive': 50.0,
        'dampingDrag': 0.3, 'diodeResonanceOut': 1.0, 'diodeResonanceIn': 1.0, 'diodeDampingOut': 1.0, 'diodeDampingIn': 1.0
    }
    for n in ['S_RA', 'S_RA_B']:
        if input_A:
            engine.physics.node_by_id[n]['psi'] = 1.0
            engine.physics.node_by_id[n]['psi_bias'] = 1.0
            engine.physics.node_by_id[n]['rho'] = 40.0 if n=='S_RA' else 20.0
            engine.physics.node_by_id['S_RA_B']['b_state'] = 1
            engine.physics.node_by_id['S_RA_B']['b_charge'] = 1.0
        else:
            engine.physics.node_by_id[n]['psi'] = -1.0
            engine.physics.node_by_id[n]['psi_bias'] = -1.0
            engine.physics.node_by_id[n]['rho'] = 5.0 if n=='S_RA' else 0.0
            engine.physics.node_by_id['S_RA_B']['b_state'] = -1
            engine.physics.node_by_id['S_RA_B']['b_charge'] = 0.0
    for n in ['S_RB', 'S_RB_B']:
        if input_B:
            engine.physics.node_by_id[n]['psi'] = 1.0
            engine.physics.node_by_id[n]['psi_bias'] = 1.0
            engine.physics.node_by_id[n]['rho'] = 40.0 if n=='S_RB' else 20.0
            engine.physics.node_by_id['S_RB_B']['b_state'] = 1
            engine.physics.node_by_id['S_RB_B']['b_charge'] = 1.0
        else:
            engine.physics.node_by_id[n]['psi'] = -1.0
            engine.physics.node_by_id[n]['psi_bias'] = -1.0
            engine.physics.node_by_id[n]['rho'] = 5.0 if n=='S_RB' else 0.0
            engine.physics.node_by_id['S_RB_B']['b_state'] = -1
            engine.physics.node_by_id['S_RB_B']['b_charge'] = 0.0
            
    for s in range(160):
        if s < 50:
            for g in ['GATE_A', 'GATE_B', 'GATE_C']:
                engine.physics.node_by_id[g]['psi_bias'] = -1.0
        elif 50 <= s < 80:
            for g in ['GATE_A', 'GATE_B', 'GATE_C']:
                engine.physics.node_by_id[g]['psi_bias'] = 1.0
        else:
            for g in ['GATE_A', 'GATE_B', 'GATE_C']:
                engine.physics.node_by_id[g]['psi_bias'] = -1.0
            engine.physics.node_by_id['P_Sum']['rho'] = 0.0
            engine.physics.node_by_id['P_Sum']['psi'] = 0.0
            engine.physics.node_by_id['P_Sum']['psi_bias'] = 0.0
        engine.step(0.05)
    return engine.physics.node_by_id['S_RC_B']['b_state'] == 1

biases = [0.16, 0.165, 0.17, 0.175, 0.18]
for bias in biases:
    res = [run_trial(A, B, bias) for A, B in [(0,0), (1,0), (0,1), (1,1)]]
    print(f'bias: {bias:.3f} results: {res}')
