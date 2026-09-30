# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOLEngine Backend Adapter
=========================
Interfaces SOLEngine wrapper with vectorized Graph Stepper array operations.
"""

from typing import Any
from sol_graph_kernel import VectorizedGraphStepper, restore_graph_arrays

def step_vectorized_impl(engine: Any, dt: float = None, c_press: float = None, damping: float = None) -> dict:
    """
    Executes a vectorized simulation step by snapshotting state to arrays,
    stepping arrays, restoring results back to nodes/edges, and committing changes.
    """
    dt_val = dt if dt is not None else engine.dt
    c_press_val = c_press if c_press is not None else engine.c_press
    damping_val = damping if damping is not None else engine.damping

    orig_t = engine.physics._t
    
    # Build the stepper from current engine state
    stepper = VectorizedGraphStepper.from_engine(engine)
    
    # Step the arrays (increments time internally)
    report = stepper.step_arrays(dt_val, c_press_val, damping_val)

    # Restore the updated snapshot arrays back to engine nodes/edges in-place
    restore_graph_arrays(stepper.snapshot, engine.physics.nodes, engine.physics.edges)

    # Sync physics time
    engine.physics._t = orig_t + dt_val

    # Recompute pressure and conductance to commit changes
    engine.physics.compute_pressure(c_press_val)
    engine.physics.update_conductance()

    return {
        "totalFlux": report.total_flux,
        "activeCount": report.active_count
    }
