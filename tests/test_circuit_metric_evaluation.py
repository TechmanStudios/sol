"""Metric optimization must preserve geometry and observe subsequent damage."""

import numpy as np
import pytest
import scipy.linalg as la

from sol.kernel.synthesis.circuit_topology import CircuitNode, CircuitNodeType, SelfAssembledCircuit


@pytest.mark.parametrize("bias", [
    [[0.0, 0.0], [0.0, 0.0]],
    [[1.2, 0.4], [-0.1, -0.7]],
    [[-12.0, 0.0], [0.0, 8.0]],
    [[20.0, -18.0], [12.0, -20.0]],
])
def test_metric_matches_matrix_exponential(bias):
    bias = np.array(bias, dtype=float)
    node = CircuitNode("n", CircuitNodeType.BASIN, np.zeros(2), metric_bias=bias)
    reference = la.expm(np.clip(0.5 * (bias + bias.T), -15.0, 15.0))
    values, vectors = la.eigh(0.5 * (reference + reference.T))
    reference = (vectors * np.clip(values, 1e-4, 100.0)) @ vectors.T

    np.testing.assert_allclose(node.compute_local_metric(), reference, rtol=1e-8, atol=1e-7)


def test_evaluation_observes_in_place_metric_changes():
    circuit = SelfAssembledCircuit("metric-drift")
    circuit.add_node("A", CircuitNodeType.INPUT, [0.0, 0.0])
    output = circuit.add_node("Y", CircuitNodeType.BASIN, [2.0, 0.0])
    circuit.add_edge("A", "Y")
    before = circuit.evaluate({"A": 1.0})

    output.metric_bias[0, 0] = 1.0
    after = circuit.evaluate({"A": 1.0})

    assert after.binary_outputs == before.binary_outputs == {"Y": 1}
    assert after.total_dissipated_energy > before.total_dissipated_energy
    assert after.max_condition_number > before.max_condition_number
    assert after.is_stable
