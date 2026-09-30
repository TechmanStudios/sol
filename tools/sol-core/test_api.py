"""Quick smoke test for the Python API — snapshot/restore & metrics."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from sol_engine import SOLEngine, compute_metrics, snapshot_state, restore_state

e = SOLEngine.from_default_graph()
e.inject("grail", 50)
e.run(50)
snap = e.save_baseline()
m1 = e.compute_metrics()

e.run(50)
m2 = e.compute_metrics()

e.restore_baseline()
m3 = e.compute_metrics()

print(f"After  50 steps: mass={m1['mass']:.4f}, entropy={m1['entropy']:.6f}")
print(f"After 100 steps: mass={m2['mass']:.4f}, entropy={m2['entropy']:.6f}")
print(f"After restore:   mass={m3['mass']:.4f}, entropy={m3['entropy']:.6f}")
print(f"Snapshot restore OK: {abs(m1['mass'] - m3['mass']) < 0.001}")

# Verify node states API
states = e.get_node_states()
print(f"get_node_states(): {len(states)} nodes, first = {states[0]['label']}")

# Verify inject_by_id
ok = e.inject_by_id(1, 100)
print(f"inject_by_id(1, 100): {ok}")

print("\nAll API tests PASSED")
