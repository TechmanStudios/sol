"""
SOL Intuition Subroutine
========================
Provides a callable 'gut feeling' mechanism for SOL agents.
Injects a complex, multi-variable signal into the manifold and runs it forward
to find the natural low-entropy basin (the 'hunch').
"""

from typing import List, Dict, Any
from sol_engine import SOLEngine

def get_intuition(engine: SOLEngine, context_nodes: List[str], signal_strength: float = 50.0, max_steps: int = 200, entropy_threshold: float = 0.1) -> Dict[str, Any]:
    """
    Injects a signal into a set of context nodes and runs the engine forward 
    to find the natural 'hunch' or low-entropy basin.
    
    Args:
        engine: The SOLEngine instance to use.
        context_nodes: List of node labels or IDs to inject the signal into.
        signal_strength: Total amount of signal to inject, divided evenly among context nodes.
        max_steps: Maximum number of steps to run the engine forward.
        entropy_threshold: The entropy level at which the system is considered to have 'made up its mind'.
        
    Returns:
        dict: The top nodes that the signal resonated with (the 'hunch'), confidence, and steps taken.
    """
    if not context_nodes:
        return {"hunch": [], "confidence": 0.0, "steps_to_coherence": 0}

    # 1. Snapshot current state so we don't ruin the main simulation
    state_backup = engine.save_baseline()
    
    # 2. Inject the 'question' or 'context' as a signal
    injection_amount = signal_strength / len(context_nodes)
    for node_id in context_nodes:
        # Try injecting by label first, if it fails (returns False), try by ID
        success = engine.inject(node_id, injection_amount)
        if not success:
            try:
                engine.inject_by_id(int(node_id), injection_amount)
            except ValueError:
                pass # Ignore if it's not a valid int ID and label failed
        
    # 3. Run forward until entropy drops (the system 'makes up its mind')
    steps_taken = 0
    final_metrics = {}
    for step in range(max_steps):
        engine.step()
        steps_taken += 1
        final_metrics = engine.compute_metrics()
        if final_metrics.get("entropy", 1.0) < entropy_threshold: # Basin found!
            break
            
    # 4. Read the 'hunch' (where did the signal pool?)
    # We look at the nodes with the highest absolute psi or semanticMass
    node_states = engine.get_node_states()
    
    # Sort nodes by absolute psi (resonance strength)
    sorted_nodes = sorted(node_states, key=lambda n: abs(n.get("psi", 0.0)), reverse=True)
    
    # Filter out the nodes we injected into to find the *resulting* resonance
    hunch_nodes = []
    for node in sorted_nodes:
        node_identifier = str(node.get("id", ""))
        node_label = node.get("label", "")
        if node_identifier not in context_nodes and node_label not in context_nodes:
            hunch_nodes.append({
                "id": node.get("id"),
                "label": node.get("label"),
                "psi": node.get("psi", 0.0),
                "semanticMass": node.get("semanticMass", 0.0)
            })
        if len(hunch_nodes) >= 3:
            break
    
    # 5. Restore state
    engine.restore_baseline(state_backup)
    
    return {
        "hunch": hunch_nodes,
        "confidence": max(0.0, 1.0 - final_metrics.get("entropy", 1.0)),
        "steps_to_coherence": steps_taken,
        "final_entropy": final_metrics.get("entropy", 1.0)
    }
