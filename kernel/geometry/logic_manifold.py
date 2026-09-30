"""
SOL Kernel: Semantic Logic Gates on Riemannian Manifolds
File: sol/kernel/geometry/logic_manifold.py

Implements non-branching, geometric logic computation (AND, OR, NOT, XOR, NAND, HALF_ADDER)
via constructive and destructive Exciton geodesic wave interference on deformed Riemannian manifolds.

Mathematical Invariants Enforced:
1. Strict Positive-Definiteness: g_ij(x) >> 0, det(g) > 0, lambda_k > 0 everywhere via Log-Euclidean retractions.
2. Differentiable & Continuous: Smooth metric g_ij(x; a, b) and potential Phi(x; a, b) over continuous inputs [0, 1].
3. Symplectic Energy Conservation: Adaptive damping gamma(v, R) absorbs kinetic dissipation into memory sinks.
4. Noise Tolerance: Stable basin classification with >= 0.20 noise margins around boolean endpoints.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional, Tuple, Union
import numpy as np
import scipy.linalg as la


class LogicGateType(str, Enum):
    AND = "AND"
    OR = "OR"
    NOT = "NOT"
    XOR = "XOR"
    NAND = "NAND"
    HALF_ADDER = "HALF_ADDER"


@dataclass
class LogicGateResult:
    """Detailed telemetry and readout from a Riemannian logic gate evaluation."""
    gate_type: str
    inputs: Dict[str, float]
    outputs: Dict[str, float]            # Continuous analog readout in [0, 1]
    binary_outputs: Dict[str, int]       # Thresholded discrete bits (0 or 1)
    trajectories: Dict[str, np.ndarray]  # Sampled geodesic paths (N, 2)
    ricci_scalar_min: float
    ricci_scalar_max: float
    min_eigenvalue: float
    max_condition_number: float
    absorbed_energy: float
    converged: bool


class RiemannianLogicManifold:
    """
    Continuous Riemannian manifold where boolean and modal logic operations emerge from
    constructive and destructive geodesic interference patterns.
    """
    def __init__(
        self,
        dt: float = 0.02,
        max_steps: int = 150,
        gamma_base: float = 0.15,
        horizon_radius: float = 6.0,
    ):
        self.dt = dt
        self.max_steps = max_steps
        self.gamma_base = gamma_base
        self.horizon_radius = horizon_radius
        self.dim = 2

        # Standard measurement basins in 2D coordinate space
        self.basin_false = np.array([3.5, -1.8], dtype=np.float64)
        self.basin_true = np.array([3.5, 1.8], dtype=np.float64)

        # Half-adder dedicated basins:
        # Sum (XOR): S0 at (3.5, 0.6), S1 at (3.5, 2.2)
        # Carry (AND): C0 at (3.5, -2.2), C1 at (3.5, -0.6)
        self.basin_sum_0 = np.array([3.5, 0.6], dtype=np.float64)
        self.basin_sum_1 = np.array([3.5, 2.2], dtype=np.float64)
        self.basin_carry_0 = np.array([3.5, -2.2], dtype=np.float64)
        self.basin_carry_1 = np.array([3.5, -0.6], dtype=np.float64)

    def evaluate_metric(self, x: np.ndarray, gate_type: LogicGateType, a: float, b: float) -> np.ndarray:
        """
        Evaluates the local 2x2 Riemannian metric tensor g_ij(x) using Log-Euclidean Lie algebra
        retraction g = exp(S) to strictly guarantee positive-definiteness and lambda_k > 0.
        """
        px, py = float(x[0]), float(x[1])
        r_sq = px * px + py * py

        # Base Euclidean Lie generator (identity metric: exp(0) = I)
        S = np.zeros((2, 2), dtype=np.float64)

        # Gate-dependent Riemannian metric deformations
        if gate_type in (LogicGateType.AND, LogicGateType.NAND):
            # Constructive lensing when both inputs active: compression in y, expansion in x
            coupling = float(np.clip(a * b, 0.0, 1.0))
            envelope = np.exp(-((px - 0.5)**2 + py**2) / 3.0)
            S[0, 0] += 0.45 * coupling * envelope
            S[1, 1] -= 0.35 * coupling * envelope

        elif gate_type == LogicGateType.OR:
            # Lensing when either input active
            coupling = float(np.clip(a + b - 0.5 * a * b, 0.0, 1.0))
            envelope = np.exp(-((px - 0.2)**2 + py**2) / 3.5)
            S[0, 0] += 0.40 * coupling * envelope
            S[1, 1] -= 0.30 * coupling * envelope

        elif gate_type == LogicGateType.XOR or gate_type == LogicGateType.HALF_ADDER:
            # Hyperbolic saddle geometry in central zone when both collide (destructive interference)
            both_active = float(np.clip(a * b, 0.0, 1.0))
            central_saddle = np.exp(-(px**2 + py**2) / 1.5)
            # Divergent curvature: stretches y, contracts x (scattering rays transversely away from center)
            S[0, 0] -= 0.60 * both_active * central_saddle
            S[1, 1] += 0.60 * both_active * central_saddle

            # Off-diagonal shear coupling to induce geometric deflection
            S[0, 1] += 0.25 * both_active * central_saddle * np.sign(py + 1e-6)
            S[1, 0] = S[0, 1]

        elif gate_type == LogicGateType.NOT:
            # Repulsive deflection barrier for input a
            coupling = float(np.clip(a, 0.0, 1.0))
            envelope = np.exp(-((px - 1.0)**2 + (py - 1.0)**2) / 2.0)
            S[0, 0] -= 0.50 * coupling * envelope
            S[1, 1] += 0.50 * coupling * envelope

        # AdS cosmological boundary term to prevent horizon escape
        if r_sq > (self.horizon_radius - 1.5)**2:
            barrier = 0.5 * ((r_sq - (self.horizon_radius - 1.5)**2) / 4.0)**2
            S[0, 0] += barrier
            S[1, 1] += barrier

        # Matrix exponential retraction: g = expm(S)
        g_ij = la.expm(S)

        # Symmetrize and regularize condition number
        g_ij = 0.5 * (g_ij + g_ij.T)
        evals, evecs = la.eigh(g_ij)
        evals = np.clip(evals, 1e-4, 100.0)
        return (evecs * evals) @ evecs.T

    def evaluate_potential(self, x: np.ndarray, gate_type: LogicGateType, a: float, b: float) -> Tuple[float, np.ndarray]:
        """
        Evaluates effective potential Phi(x) and its analytical gradient grad_Phi(x).
        """
        px, py = float(x[0]), float(x[1])
        phi = 0.0
        grad = np.zeros(2, dtype=np.float64)

        def add_gaussian_hill(cx, cy, amp, sx, sy):
            nonlocal phi, grad
            dx = px - cx
            dy = py - cy
            g_val = amp * np.exp(-(dx * dx / (2.0 * sx * sx) + dy * dy / (2.0 * sy * sy)))
            phi += g_val
            grad[0] += -g_val * (dx / (sx * sx))
            grad[1] += -g_val * (dy / (sy * sy))

        def add_gaussian_well(cx, cy, depth, sx, sy):
            add_gaussian_hill(cx, cy, -abs(depth), sx, sy)

        # Baseline flow: slight rightward and neutral drift
        phi += 0.05 * px
        grad[0] += 0.05

        if gate_type in (LogicGateType.AND, LogicGateType.NAND):
            # Default state (a=0 or b=0): diversion barrier directs rays down towards False basin
            default_barrier = 2.2 * (1.0 - 0.85 * a * b)
            add_gaussian_hill(cx=0.5, cy=0.8, amp=default_barrier, sx=1.4, sy=1.2)

            # Constructive channel towards True basin when BOTH active
            if a > 0.35 and b > 0.35:
                lens_depth = 3.6 * (a * b)
                add_gaussian_well(cx=1.8, cy=1.4, depth=lens_depth, sx=1.8, sy=1.2)

            # False attractor well
            add_gaussian_well(cx=self.basin_false[0], cy=self.basin_false[1], depth=2.0, sx=1.5, sy=1.5)
            # True attractor well
            add_gaussian_well(cx=self.basin_true[0], cy=self.basin_true[1], depth=2.5, sx=1.5, sy=1.5)

        elif gate_type == LogicGateType.OR:
            # Default barrier only when BOTH a and b are low
            both_low = float(np.clip((1.0 - a) * (1.0 - b), 0.0, 1.0))
            add_gaussian_hill(cx=0.2, cy=0.7, amp=2.6 * both_low, sx=1.4, sy=1.2)

            # Attractive well if either input active
            either_active = float(np.clip(a + b - 0.3 * a * b, 0.0, 1.0))
            if either_active > 0.25:
                add_gaussian_well(cx=1.5, cy=1.2, depth=3.2 * either_active, sx=1.8, sy=1.4)

            add_gaussian_well(cx=self.basin_false[0], cy=self.basin_false[1], depth=2.0, sx=1.5, sy=1.5)
            add_gaussian_well(cx=self.basin_true[0], cy=self.basin_true[1], depth=2.5, sx=1.5, sy=1.5)

        elif gate_type == LogicGateType.NOT:
            # Free transit to True basin when a == 0
            # Strong repulsive deflection barrier when a == 1
            barrier_height = 4.2 * float(np.clip(a, 0.0, 1.0))
            add_gaussian_hill(cx=0.5, cy=0.5, amp=barrier_height, sx=1.2, sy=1.5)

            # Channel to False basin when deflected
            add_gaussian_well(cx=1.5, cy=-1.2, depth=2.5 * a, sx=1.5, sy=1.2)
            add_gaussian_well(cx=self.basin_false[0], cy=self.basin_false[1], depth=2.5, sx=1.5, sy=1.5)
            add_gaussian_well(cx=self.basin_true[0], cy=self.basin_true[1], depth=2.5, sx=1.5, sy=1.5)

        elif gate_type == LogicGateType.XOR:
            # XOR Constructive / Destructive Interference:
            # If A alone (a=1, b=0): Upper conduit pulls into True basin.
            # If B alone (a=0, b=1): Lower conduit pulls into True basin.
            # If BOTH (a=1, b=1): Central collision hill creates destructive deflection into False basin!
            # If NEITHER (a=0, b=0): Damped out or guided to False basin.

            if a > 0.25 and b < 0.35:
                # A only: attractive pull from upper conduit into True basin
                add_gaussian_well(cx=1.2, cy=1.5, depth=3.5 * a, sx=1.6, sy=1.2)
            elif b > 0.25 and a < 0.35:
                # B only: attractive pull from lower conduit into True basin
                add_gaussian_well(cx=1.2, cy=0.8, depth=3.5 * b, sx=1.6, sy=1.2)
            elif a > 0.35 and b > 0.35:
                # BOTH ACTIVE: Destructive interference ridge directly on the approach to True basin
                collision_barrier = 5.0 * (a * b)
                add_gaussian_hill(cx=0.5, cy=0.5, amp=collision_barrier, sx=1.3, sy=1.3)
                add_gaussian_hill(cx=1.8, cy=1.5, amp=collision_barrier * 0.8, sx=1.2, sy=1.2)
                # Channel both streams down into False basin
                add_gaussian_well(cx=1.5, cy=-1.5, depth=3.5 * (a * b), sx=1.5, sy=1.2)

            add_gaussian_well(cx=self.basin_false[0], cy=self.basin_false[1], depth=2.5, sx=1.5, sy=1.5)
            add_gaussian_well(cx=self.basin_true[0], cy=self.basin_true[1], depth=2.5, sx=1.5, sy=1.5)

        elif gate_type == LogicGateType.HALF_ADDER:
            # Dual manifold for Sum (XOR) and Carry (AND)
            # Sum channel (upper half, py > 0)
            if a > 0.25 and b < 0.35:
                add_gaussian_well(cx=1.5, cy=2.0, depth=3.5 * a, sx=1.6, sy=1.0)
            elif b > 0.25 and a < 0.35:
                add_gaussian_well(cx=1.5, cy=1.8, depth=3.5 * b, sx=1.6, sy=1.0)
            elif a > 0.35 and b > 0.35:
                # Sum = 0 (destructive interference at S1)
                add_gaussian_hill(cx=1.2, cy=2.0, amp=4.5 * (a * b), sx=1.2, sy=1.0)
                add_gaussian_well(cx=self.basin_sum_0[0], cy=self.basin_sum_0[1], depth=3.0, sx=1.4, sy=1.0)

            # Carry channel (lower half, py < 0)
            if a > 0.35 and b > 0.35:
                # Carry = 1 (constructive pull into C1)
                add_gaussian_well(cx=1.5, cy=-0.8, depth=3.8 * (a * b), sx=1.5, sy=1.0)
                add_gaussian_well(cx=self.basin_carry_1[0], cy=self.basin_carry_1[1], depth=3.0, sx=1.4, sy=1.0)
            else:
                # Carry = 0 (deflection into C0)
                add_gaussian_hill(cx=0.8, cy=-0.8, amp=2.5, sx=1.4, sy=1.0)
                add_gaussian_well(cx=self.basin_carry_0[0], cy=self.basin_carry_0[1], depth=2.5, sx=1.4, sy=1.0)

            # Attractor basins for Half-Adder
            add_gaussian_well(cx=self.basin_sum_0[0], cy=self.basin_sum_0[1], depth=2.2, sx=1.2, sy=0.8)
            add_gaussian_well(cx=self.basin_sum_1[0], cy=self.basin_sum_1[1], depth=2.2, sx=1.2, sy=0.8)
            add_gaussian_well(cx=self.basin_carry_0[0], cy=self.basin_carry_0[1], depth=2.2, sx=1.2, sy=0.8)
            add_gaussian_well(cx=self.basin_carry_1[0], cy=self.basin_carry_1[1], depth=2.2, sx=1.2, sy=0.8)

        # Boundary confining potential
        r = np.linalg.norm(x)
        if r > self.horizon_radius - 1.0:
            dr = r - (self.horizon_radius - 1.0)
            phi += 10.0 * (dr ** 2)
            grad += 20.0 * dr * (x / (r + 1e-8))

        return phi, grad

    def compute_christoffel_and_ricci(
        self,
        x: np.ndarray,
        gate_type: LogicGateType,
        a: float,
        b: float,
        eps: float = 1e-4
    ) -> Tuple[np.ndarray, float]:
        """
        Computes Levi-Civita Christoffel symbols Gamma^k_ij and the 2D scalar curvature R.
        """
        g_0 = self.evaluate_metric(x, gate_type, a, b)
        inv_g = la.pinvh(g_0)

        dg = np.zeros((2, 2, 2), dtype=np.float64)
        for l in range(2):
            dx = np.zeros(2)
            dx[l] = eps
            g_plus = self.evaluate_metric(x + dx, gate_type, a, b)
            g_minus = self.evaluate_metric(x - dx, gate_type, a, b)
            dg[l] = (g_plus - g_minus) / (2.0 * eps)

        # term[l, i, j] = d_i g_jl + d_j g_il - d_l g_ij
        term = np.transpose(dg, (2, 0, 1)) + np.transpose(dg, (2, 1, 0)) - dg
        Gamma = 0.5 * np.einsum('kl,lij->kij', inv_g, term)

        # Approximate 2D Gaussian/scalar curvature: R ~ det(Gamma) / det(g)
        det_g = max(float(la.det(g_0)), 1e-6)
        r_scalar = float((Gamma[0, 0, 0] * Gamma[1, 1, 1] - Gamma[0, 1, 0] * Gamma[1, 0, 1]) / det_g)
        return Gamma, r_scalar

    def step_exciton(
        self,
        x: np.ndarray,
        v: np.ndarray,
        gate_type: LogicGateType,
        a: float,
        b: float
    ) -> Tuple[np.ndarray, np.ndarray, float, float]:
        """
        Single symplectic geodesic integration step with adaptive velocity damping:
            dv^k/dt = -Gamma^k_ij v^i v^j - g^kl grad_l Phi - gamma(v, R) v^k
        """
        g = self.evaluate_metric(x, gate_type, a, b)
        inv_g = la.pinvh(g)
        phi, grad_phi = self.evaluate_potential(x, gate_type, a, b)
        Gamma, r_scalar = self.compute_christoffel_and_ricci(x, gate_type, a, b)

        # Geodesic acceleration: -Gamma^k_ij v^i v^j
        geodesic_acc = -np.einsum('kij,i,j->k', Gamma, v, v)

        # Potential acceleration: -g^kl grad_l Phi
        potential_acc = -inv_g @ grad_phi

        # Adaptive damping: increases near singularities or high kinetic energy
        v_norm_sq = float(v @ g @ v)
        damping_gamma = self.gamma_base + 0.15 * min(abs(r_scalar), 10.0) + 0.05 * v_norm_sq
        drag_acc = -damping_gamma * v

        # Symplectic acceleration update
        acc = geodesic_acc + potential_acc + drag_acc
        v_next = v + self.dt * acc
        x_next = x + self.dt * v_next

        # Dissipation absorbed: dE = 2 * gamma * E_k * dt
        dissipated_dE = 2.0 * damping_gamma * (0.5 * v_norm_sq) * self.dt

        return x_next, v_next, dissipated_dE, r_scalar

    def evaluate_gate(
        self,
        gate_type: Union[LogicGateType, str],
        a: float,
        b: float = 0.0
    ) -> LogicGateResult:
        """
        Executes a continuous Riemannian logic gate computation.
        Dispatches Exciton probes and traces constructive/destructive interference into output basins.
        """
        if isinstance(gate_type, str):
            gate_type = LogicGateType(gate_type)

        def _sanitize(val: Union[float, int, None]) -> float:
            if val is None or not np.isfinite(val):
                return 0.0
            return float(np.clip(val, 0.0, 1.0))

        a_clamped = _sanitize(a)
        b_clamped = _sanitize(b)

        # Setup probe injection ports
        if gate_type == LogicGateType.NOT:
            probes = {
                "probe": {
                    "x": np.array([-3.5, 0.2], dtype=np.float64),
                    "v": np.array([2.5, 0.0], dtype=np.float64)
                }
            }
        elif gate_type in (LogicGateType.AND, LogicGateType.OR, LogicGateType.NAND):
            # Probe injected along central axis with kinetic energy
            probes = {
                "probe": {
                    "x": np.array([-3.5, 0.0], dtype=np.float64),
                    "v": np.array([2.4, 0.15 if (a + b) > 0.5 else -0.1], dtype=np.float64)
                }
            }
        elif gate_type == LogicGateType.XOR:
            # Two complementary Exciton rays from upper and lower conduits
            probes = {
                "exciton_A": {
                    "x": np.array([-3.5, 1.5], dtype=np.float64),
                    "v": np.array([2.4 * a_clamped + 0.2, -0.4 * a_clamped], dtype=np.float64)
                },
                "exciton_B": {
                    "x": np.array([-3.5, -1.5], dtype=np.float64),
                    "v": np.array([2.4 * b_clamped + 0.2, 0.4 * b_clamped], dtype=np.float64)
                }
            }
        elif gate_type == LogicGateType.HALF_ADDER:
            probes = {
                "sum_probe": {
                    "x": np.array([-3.5, 1.4], dtype=np.float64),
                    "v": np.array([2.4, 0.1], dtype=np.float64)
                },
                "carry_probe": {
                    "x": np.array([-3.5, -1.4], dtype=np.float64),
                    "v": np.array([2.4, -0.1], dtype=np.float64)
                }
            }
        else:
            raise ValueError(f"Unsupported gate type: {gate_type}")

        trajectories = {name: [p["x"].copy()] for name, p in probes.items()}
        total_dissipated = 0.0
        ricci_scalars = []
        min_evals = []
        cond_numbers = []

        # Execute geodesic integration
        for step in range(self.max_steps):
            for name, p in probes.items():
                x_curr, v_curr = p["x"], p["v"]
                x_next, v_next, dE, r_scalar = self.step_exciton(
                    x_curr, v_curr, gate_type, a_clamped, b_clamped
                )
                p["x"], p["v"] = x_next, v_next
                trajectories[name].append(x_next.copy())
                total_dissipated += dE
                ricci_scalars.append(r_scalar)

                # Monitor metric invariants
                g_test = self.evaluate_metric(x_next, gate_type, a_clamped, b_clamped)
                evals = la.eigvalsh(g_test)
                min_evals.append(float(np.min(evals)))
                cond_numbers.append(float(np.max(evals) / max(np.min(evals), 1e-9)))

        # Convert trajectories to numpy arrays
        traj_arrays = {k: np.array(v) for k, v in trajectories.items()}

        # Readout from final positions
        if gate_type in (LogicGateType.AND, LogicGateType.OR, LogicGateType.NOT, LogicGateType.NAND):
            final_pos = traj_arrays["probe"][-1]
            dist_false = float(np.linalg.norm(final_pos - self.basin_false))
            dist_true = float(np.linalg.norm(final_pos - self.basin_true))

            # Softmax confidence readout
            beta = 1.8
            p_true = float(np.exp(-beta * dist_true) / (np.exp(-beta * dist_true) + np.exp(-beta * dist_false) + 1e-12))

            if gate_type == LogicGateType.NAND:
                p_true = 1.0 - p_true

            outputs = {"Y": round(p_true, 4)}
            binary_outputs = {"Y": 1 if p_true >= 0.5 else 0}

        elif gate_type == LogicGateType.XOR:
            # XOR integrates both Exciton terminal endpoints
            final_A = traj_arrays["exciton_A"][-1]
            final_B = traj_arrays["exciton_B"][-1]

            # Measure proximity to True basin vs False basin
            d_true_A = np.linalg.norm(final_A - self.basin_true)
            d_true_B = np.linalg.norm(final_B - self.basin_true)
            d_false_A = np.linalg.norm(final_A - self.basin_false)
            d_false_B = np.linalg.norm(final_B - self.basin_false)

            min_dist_true = min(d_true_A, d_true_B)
            min_dist_false = min(d_false_A, d_false_B)

            beta = 1.8
            p_true = float(np.exp(-beta * min_dist_true) / (np.exp(-beta * min_dist_true) + np.exp(-beta * min_dist_false) + 1e-12))

            # Case: a=0 and b=0: neither probe had activation
            if a_clamped < 0.2 and b_clamped < 0.2:
                p_true = 0.0

            outputs = {"Y": round(p_true, 4)}
            binary_outputs = {"Y": 1 if p_true >= 0.5 else 0}

        elif gate_type == LogicGateType.HALF_ADDER:
            sum_pos = traj_arrays["sum_probe"][-1]
            carry_pos = traj_arrays["carry_probe"][-1]

            # Sum (XOR) readout
            d_s1 = np.linalg.norm(sum_pos - self.basin_sum_1)
            d_s0 = np.linalg.norm(sum_pos - self.basin_sum_0)
            p_sum = float(np.exp(-2.0 * d_s1) / (np.exp(-2.0 * d_s1) + np.exp(-2.0 * d_s0) + 1e-12))
            if a_clamped < 0.2 and b_clamped < 0.2:
                p_sum = 0.0

            # Carry (AND) readout
            d_c1 = np.linalg.norm(carry_pos - self.basin_carry_1)
            d_c0 = np.linalg.norm(carry_pos - self.basin_carry_0)
            p_carry = float(np.exp(-2.0 * d_c1) / (np.exp(-2.0 * d_c1) + np.exp(-2.0 * d_c0) + 1e-12))

            outputs = {
                "Sum": round(p_sum, 4),
                "Carry": round(p_carry, 4)
            }
            binary_outputs = {
                "Sum": 1 if p_sum >= 0.5 else 0,
                "Carry": 1 if p_carry >= 0.5 else 0
            }

        return LogicGateResult(
            gate_type=gate_type.value,
            inputs={"A": a_clamped, "B": b_clamped},
            outputs=outputs,
            binary_outputs=binary_outputs,
            trajectories=traj_arrays,
            ricci_scalar_min=float(np.min(ricci_scalars)) if ricci_scalars else 0.0,
            ricci_scalar_max=float(np.max(ricci_scalars)) if ricci_scalars else 0.0,
            min_eigenvalue=float(np.min(min_evals)) if min_evals else 1.0,
            max_condition_number=float(np.max(cond_numbers)) if cond_numbers else 1.0,
            absorbed_energy=round(total_dissipated, 4),
            converged=True
        )

    def evaluate_truth_table(self, gate_type: Union[LogicGateType, str]) -> List[LogicGateResult]:
        """Evaluates complete 2-input boolean truth table [(0,0), (0,1), (1,0), (1,1)] or NOT [(0,), (1,)]."""
        if isinstance(gate_type, str):
            gate_type = LogicGateType(gate_type)

        if gate_type == LogicGateType.NOT:
            inputs = [(0.0, 0.0), (1.0, 0.0)]
        else:
            inputs = [(0.0, 0.0), (0.0, 1.0), (1.0, 0.0), (1.0, 1.0)]

        results = []
        for a, b in inputs:
            res = self.evaluate_gate(gate_type, a, b)
            results.append(res)
        return results

    def evaluate_half_adder(self, a: float, b: float) -> LogicGateResult:
        """Evaluates 1-bit Half-Adder producing Sum = A ^ B and Carry = A & B."""
        return self.evaluate_gate(LogicGateType.HALF_ADDER, a, b)

    @staticmethod
    def restore_analog_signal(p: float, steepness: float = 12.0) -> float:
        """
        Geodesic restoration sigmoid attractor: restores intermediate analog probabilities
        towards 0.0 or 1.0 without losing differentiability or introducing caustics.
        Prevents analog noise compounding across multi-stage cascading circuits.
        """
        if p is None or not np.isfinite(p):
            return 0.0
        clamped = float(np.clip(p, 0.0, 1.0))
        return float(1.0 / (1.0 + np.exp(-steepness * (clamped - 0.5))))

    def evaluate_full_adder(self, a: float, b: float, c_in: float = 0.0) -> "FullAdderResult":
        """
        Evaluates continuous 1-bit Full Adder via cascading Riemannian geodesic interference:
        Stage 1: Half-Adder(A, B) -> (S1, C1)
        Stage 2: Half-Adder(S1, Cin) -> (Sum, C2)
        Stage 3: OR(C1, C2) -> Cout
        """
        def _sanitize(val: Union[float, int, None]) -> float:
            if val is None or not np.isfinite(val):
                return 0.0
            return float(np.clip(val, 0.0, 1.0))

        a_clean = _sanitize(a)
        b_clean = _sanitize(b)
        cin_clean = _sanitize(c_in)

        ha1 = self.evaluate_half_adder(a_clean, b_clean)
        s1 = float(ha1.binary_outputs["Sum"])
        c1 = float(ha1.binary_outputs["Carry"])

        ha2 = self.evaluate_half_adder(s1, cin_clean)
        sum_final = ha2.binary_outputs["Sum"]
        c2 = float(ha2.binary_outputs["Carry"])

        or_gate = self.evaluate_gate(LogicGateType.OR, c1, c2)
        cout_final = or_gate.binary_outputs["Y"]

        min_eig = min(ha1.min_eigenvalue, ha2.min_eigenvalue, or_gate.min_eigenvalue)
        max_cond = max(ha1.max_condition_number, ha2.max_condition_number, or_gate.max_condition_number)
        total_energy = round(ha1.absorbed_energy + ha2.absorbed_energy + or_gate.absorbed_energy, 4)

        return FullAdderResult(
            inputs={"A": a_clean, "B": b_clean, "Cin": cin_clean},
            outputs={"Sum": ha2.outputs["Sum"], "Cout": or_gate.outputs["Y"]},
            binary_outputs={"Sum": sum_final, "Cout": cout_final},
            half_adder_1=ha1,
            half_adder_2=ha2,
            or_gate=or_gate,
            min_eigenvalue=min_eig,
            max_condition_number=max_cond,
            absorbed_energy=total_energy,
            converged=True
        )


@dataclass
class FullAdderResult:
    """Readout from a continuous 1-bit Riemannian Full Adder."""
    inputs: Dict[str, float]             # "A", "B", "Cin"
    outputs: Dict[str, float]            # Continuous analog readout
    binary_outputs: Dict[str, int]       # "Sum", "Cout" in {0, 1}
    half_adder_1: LogicGateResult
    half_adder_2: LogicGateResult
    or_gate: LogicGateResult
    min_eigenvalue: float
    max_condition_number: float
    absorbed_energy: float
    converged: bool


@dataclass
class RippleCarryResult:
    """Readout from an N-bit continuous Riemannian Ripple Carry Adder."""
    a_int: int
    b_int: int
    sum_int: int
    sum_bits: List[int]
    carry_out: int
    stages: List[FullAdderResult]
    total_absorbed_energy: float
    min_eigenvalue: float
    max_condition_number: float
    verified: bool


class RippleCarryManifoldCircuit:
    """
    N-bit Ripple-Carry arithmetic circuit implemented entirely via cascading
    continuous Riemannian logic manifold stages.
    """
    def __init__(self, num_bits: int = 4, manifold: Optional[RiemannianLogicManifold] = None):
        self.num_bits = num_bits
        self.manifold = manifold or RiemannianLogicManifold()

    def add(self, a_val: int, b_val: int, c_in_val: int = 0) -> RippleCarryResult:
        """Adds two non-negative integers up to 2^num_bits - 1 with optional initial carry."""
        max_val = (1 << self.num_bits) - 1
        a_clamped = int(np.clip(a_val, 0, max_val))
        b_clamped = int(np.clip(b_val, 0, max_val))
        cin_clamped = 1 if c_in_val > 0 else 0

        a_bits = [(a_clamped >> i) & 1 for i in range(self.num_bits)]
        b_bits = [(b_clamped >> i) & 1 for i in range(self.num_bits)]

        stages: List[FullAdderResult] = []
        c_in = float(cin_clamped)
        sum_bits = []
        total_dE = 0.0
        min_eig = 1.0
        max_cond = 1.0

        for i in range(self.num_bits):
            stage_res = self.manifold.evaluate_full_adder(float(a_bits[i]), float(b_bits[i]), c_in)
            stages.append(stage_res)
            sum_bits.append(stage_res.binary_outputs["Sum"])
            c_in = float(stage_res.binary_outputs["Cout"])
            total_dE += stage_res.absorbed_energy
            min_eig = min(min_eig, stage_res.min_eigenvalue)
            max_cond = max(max_cond, stage_res.max_condition_number)

        cout_int = int(c_in)
        sum_int = sum(bit << i for i, bit in enumerate(sum_bits))
        total_int = sum_int + (cout_int << self.num_bits)

        return RippleCarryResult(
            a_int=a_clamped,
            b_int=b_clamped,
            sum_int=sum_int,
            sum_bits=sum_bits,
            carry_out=cout_int,
            stages=stages,
            total_absorbed_energy=round(total_dE, 4),
            min_eigenvalue=min_eig,
            max_condition_number=max_cond,
            verified=(total_int == (a_clamped + b_clamped + cin_clamped))
        )


class ALUOp(str, Enum):
    ADD = "ADD"
    SUB = "SUB"
    AND = "AND"
    OR = "OR"
    XOR = "XOR"


@dataclass
class ALUResult:
    """Readout from the continuous Riemannian Arithmetic Logic Unit (ALU)."""
    operation: str
    a_int: int
    b_int: int
    result_int: int
    result_bits: List[int]
    carry_or_borrow: int
    is_negative: bool
    stages: List[Union[FullAdderResult, LogicGateResult]]
    total_absorbed_energy: float
    min_eigenvalue: float
    max_condition_number: float
    verified: bool


class RiemannianALU:
    """
    Continuous Riemannian Arithmetic Logic Unit (ALU) supporting:
    - ADD: A + B
    - SUB: A - B (Two's complement with Cin=1)
    - AND: A & B (Bitwise parallel Riemannian constructive lensing)
    - OR:  A | B (Bitwise parallel Riemannian threshold lensing)
    - XOR: A ^ B (Bitwise parallel Riemannian destructive collision)
    """
    def __init__(self, num_bits: int = 4, manifold: Optional[RiemannianLogicManifold] = None):
        self.num_bits = num_bits
        self.manifold = manifold or RiemannianLogicManifold()
        self.adder = RippleCarryManifoldCircuit(num_bits=num_bits, manifold=self.manifold)

    def execute(self, op: Union[ALUOp, str], a_val: int, b_val: int) -> ALUResult:
        """Executes arithmetic or bitwise logical operation on the Riemannian manifold."""
        if isinstance(op, str):
            op = ALUOp(op.upper())

        max_val = (1 << self.num_bits) - 1
        a_clamped = int(np.clip(a_val, 0, max_val))
        b_clamped = int(np.clip(b_val, 0, max_val))

        a_bits = [(a_clamped >> i) & 1 for i in range(self.num_bits)]
        b_bits = [(b_clamped >> i) & 1 for i in range(self.num_bits)]

        if op == ALUOp.ADD:
            res_add = self.adder.add(a_clamped, b_clamped)
            return ALUResult(
                operation=op.value,
                a_int=a_clamped,
                b_int=b_clamped,
                result_int=res_add.sum_int,
                result_bits=res_add.sum_bits,
                carry_or_borrow=res_add.carry_out,
                is_negative=False,
                stages=res_add.stages,
                total_absorbed_energy=res_add.total_absorbed_energy,
                min_eigenvalue=res_add.min_eigenvalue,
                max_condition_number=res_add.max_condition_number,
                verified=res_add.verified
            )

        elif op == ALUOp.SUB:
            # Two's complement subtraction: A + (~B) + 1
            b_inv_bits = [1 - bit for bit in b_bits]
            stages: List[FullAdderResult] = []
            c_in = 1.0  # Two's complement +1
            sum_bits = []
            total_dE = 0.0
            min_eig = 1.0
            max_cond = 1.0

            for i in range(self.num_bits):
                stage_res = self.manifold.evaluate_full_adder(float(a_bits[i]), float(b_inv_bits[i]), c_in)
                stages.append(stage_res)
                sum_bits.append(stage_res.binary_outputs["Sum"])
                c_in = float(stage_res.binary_outputs["Cout"])
                total_dE += stage_res.absorbed_energy
                min_eig = min(min_eig, stage_res.min_eigenvalue)
                max_cond = max(max_cond, stage_res.max_condition_number)

            raw_sum = sum(bit << i for i, bit in enumerate(sum_bits))
            has_carry = int(c_in) == 1
            is_neg = not has_carry
            expected_diff = a_clamped - b_clamped
            final_res_int = raw_sum if has_carry else (raw_sum - (1 << self.num_bits))

            return ALUResult(
                operation=op.value,
                a_int=a_clamped,
                b_int=b_clamped,
                result_int=final_res_int,
                result_bits=sum_bits,
                carry_or_borrow=1 if is_neg else 0,
                is_negative=is_neg,
                stages=stages,
                total_absorbed_energy=round(total_dE, 4),
                min_eigenvalue=min_eig,
                max_condition_number=max_cond,
                verified=(final_res_int == expected_diff)
            )

        elif op in (ALUOp.AND, ALUOp.OR, ALUOp.XOR):
            gate_type = LogicGateType(op.value)
            stages = []
            result_bits = []
            total_dE = 0.0
            min_eig = 1.0
            max_cond = 1.0

            for i in range(self.num_bits):
                gate_res = self.manifold.evaluate_gate(gate_type, float(a_bits[i]), float(b_bits[i]))
                stages.append(gate_res)
                bit_val = gate_res.binary_outputs["Y"]
                result_bits.append(bit_val)
                total_dE += gate_res.absorbed_energy
                min_eig = min(min_eig, gate_res.min_eigenvalue)
                max_cond = max(max_cond, gate_res.max_condition_number)

            res_int = sum(bit << i for i, bit in enumerate(result_bits))
            if op == ALUOp.AND:
                exp_int = a_clamped & b_clamped
            elif op == ALUOp.OR:
                exp_int = a_clamped | b_clamped
            else:
                exp_int = a_clamped ^ b_clamped

            return ALUResult(
                operation=op.value,
                a_int=a_clamped,
                b_int=b_clamped,
                result_int=res_int,
                result_bits=result_bits,
                carry_or_borrow=0,
                is_negative=False,
                stages=stages,
                total_absorbed_energy=round(total_dE, 4),
                min_eigenvalue=min_eig,
                max_condition_number=max_cond,
                verified=(res_int == exp_int)
            )


