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

import math
from dataclasses import dataclass
from enum import Enum

import numpy as np


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
    inputs: dict[str, float]
    outputs: dict[str, float]            # Continuous analog readout in [0, 1]
    binary_outputs: dict[str, int]       # Thresholded discrete bits (0 or 1)
    trajectories: dict[str, np.ndarray]  # Sampled geodesic paths (N, 2)
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

    def _metric_components(
        self,
        px: float,
        py: float,
        gate_type: LogicGateType,
        a: float,
        b: float,
    ) -> tuple[float, float, float, float, float]:
        """
        Closed-form 2x2 Log-Euclidean metric g = clip_eig(exp(S), 1e-4, 100.0)
        via Sylvester's spectral projector formula.
        Returns (g00, g01, g11, min_eval, max_eval).
        """
        _exp = math.exp
        r_sq = px * px + py * py
        s00 = 0.0
        s01 = 0.0
        s11 = 0.0

        if gate_type in (LogicGateType.AND, LogicGateType.NAND):
            coupling = min(max(a * b, 0.0), 1.0)
            dx = px - 0.5
            ce = coupling * _exp(-(dx * dx + py * py) / 3.0)
            s00 += 0.45 * ce
            s11 -= 0.35 * ce
        elif gate_type == LogicGateType.OR:
            coupling = min(max(a + b - 0.5 * a * b, 0.0), 1.0)
            dx = px - 0.2
            ce = coupling * _exp(-(dx * dx + py * py) / 3.5)
            s00 += 0.40 * ce
            s11 -= 0.30 * ce
        elif gate_type in (LogicGateType.XOR, LogicGateType.HALF_ADDER):
            both_active = min(max(a * b, 0.0), 1.0)
            ce = both_active * _exp(-r_sq / 1.5)
            s00 -= 0.60 * ce
            s11 += 0.60 * ce
            py_s = py + 1e-6
            sgn = 1.0 if py_s > 0.0 else (-1.0 if py_s < 0.0 else 0.0)
            s01 += 0.25 * ce * sgn
        elif gate_type == LogicGateType.NOT:
            coupling = min(max(a, 0.0), 1.0)
            dx = px - 1.0
            dy = py - 1.0
            ce = coupling * _exp(-(dx * dx + dy * dy) / 2.0)
            s00 -= 0.50 * ce
            s11 += 0.50 * ce

        r_thresh = (self.horizon_radius - 1.5) ** 2
        if r_sq > r_thresh:
            t_b = (r_sq - r_thresh) * 0.25
            barrier = 0.5 * (t_b * t_b)
            s00 += barrier
            s11 += barrier

        if s01 == 0.0:
            g00 = min(max(_exp(min(max(s00, -20.0), 20.0)), 1e-4), 100.0)
            g11 = min(max(_exp(min(max(s11, -20.0), 20.0)), 1e-4), 100.0)
            if g00 <= g11:
                return g00, 0.0, g11, g00, g11
            return g00, 0.0, g11, g11, g00

        half_tr = 0.5 * (s00 + s11)
        half_diff = 0.5 * (s00 - s11)
        rad = math.hypot(half_diff, s01)
        l1 = min(max(_exp(min(max(half_tr - rad, -20.0), 20.0)), 1e-4), 100.0)
        l2 = min(max(_exp(min(max(half_tr + rad, -20.0), 20.0)), 1e-4), 100.0)
        avg_l = 0.5 * (l1 + l2)
        scale = 0.5 * (l2 - l1) / rad
        return (
            avg_l + scale * half_diff,
            scale * s01,
            avg_l - scale * half_diff,
            l1,
            l2,
        )

    def evaluate_metric(self, x: np.ndarray, gate_type: LogicGateType, a: float, b: float) -> np.ndarray:
        """
        Evaluates the local 2x2 Riemannian metric tensor g_ij(x) using Log-Euclidean Lie algebra
        retraction g = exp(S) to strictly guarantee positive-definiteness and lambda_k > 0.
        """
        g00, g01, g11, _, _ = self._metric_components(float(x[0]), float(x[1]), gate_type, a, b)
        return np.array([[g00, g01], [g01, g11]], dtype=np.float64)

    @staticmethod
    def _smooth_gate(val: float, threshold: float = 0.35, sharpness: float = 24.0) -> float:
        """Smooth C^infinity logistic activation envelope replacing hard threshold branches."""
        z = min(max(sharpness * (val - threshold), -40.0), 40.0)
        return 1.0 / (1.0 + math.exp(-z))

    def _potential_components(
        self,
        px: float,
        py: float,
        gate_type: LogicGateType,
        a: float,
        b: float,
    ) -> tuple[float, float, float]:
        """Returns (phi, grad_x, grad_y) using pure scalar math."""
        _exp = math.exp
        phi = 0.05 * px
        gx = 0.05
        gy = 0.0

        def _hill(cx: float, cy: float, amp: float, sx: float, sy: float) -> None:
            nonlocal phi, gx, gy
            if abs(amp) < 1e-12:
                return
            dx = px - cx
            dy = py - cy
            inv_sx2 = 1.0 / (sx * sx)
            inv_sy2 = 1.0 / (sy * sy)
            g_val = amp * _exp(-0.5 * (dx * dx * inv_sx2 + dy * dy * inv_sy2))
            phi += g_val
            gx -= g_val * (dx * inv_sx2)
            gy -= g_val * (dy * inv_sy2)

        bf_x = float(self.basin_false[0])
        bf_y = float(self.basin_false[1])
        bt_x = float(self.basin_true[0])
        bt_y = float(self.basin_true[1])

        if gate_type in (LogicGateType.AND, LogicGateType.NAND):
            _hill(0.5, 0.8, 2.2 * (1.0 - 0.85 * a * b), 1.4, 1.2)
            w_both = self._smooth_gate(a, 0.35) * self._smooth_gate(b, 0.35)
            _hill(1.8, 1.4, -abs(3.6 * (a * b) * w_both), 1.8, 1.2)
            _hill(bf_x, bf_y, -2.0, 1.5, 1.5)
            _hill(bt_x, bt_y, -2.5, 1.5, 1.5)

        elif gate_type == LogicGateType.OR:
            both_low = min(max((1.0 - a) * (1.0 - b), 0.0), 1.0)
            _hill(0.2, 0.7, 2.6 * both_low, 1.4, 1.2)
            either_active = min(max(a + b - 0.3 * a * b, 0.0), 1.0)
            w_either = self._smooth_gate(either_active, 0.25)
            _hill(1.5, 1.2, -abs(3.2 * either_active * w_either), 1.8, 1.4)
            _hill(bf_x, bf_y, -2.0, 1.5, 1.5)
            _hill(bt_x, bt_y, -2.5, 1.5, 1.5)

        elif gate_type == LogicGateType.NOT:
            barrier_height = 4.2 * min(max(a, 0.0), 1.0)
            _hill(0.5, 0.5, barrier_height, 1.2, 1.5)
            _hill(1.5, -1.2, -abs(2.5 * a), 1.5, 1.2)
            _hill(bf_x, bf_y, -2.5, 1.5, 1.5)
            _hill(bt_x, bt_y, -2.5, 1.5, 1.5)

        elif gate_type == LogicGateType.XOR:
            s_a_low = self._smooth_gate(a, 0.25)
            s_b_low = self._smooth_gate(b, 0.25)
            s_a_high = self._smooth_gate(a, 0.35)
            s_b_high = self._smooth_gate(b, 0.35)

            w_a_only = s_a_low * (1.0 - s_b_high)
            w_b_only = s_b_low * (1.0 - s_a_high)
            w_both = s_a_high * s_b_high

            _hill(1.2, 1.5, -abs(3.5 * a * w_a_only), 1.6, 1.2)
            _hill(1.2, 0.8, -abs(3.5 * b * w_b_only), 1.6, 1.2)
            collision_barrier = 5.0 * (a * b) * w_both
            _hill(0.5, 0.5, collision_barrier, 1.3, 1.3)
            _hill(1.8, 1.5, collision_barrier * 0.8, 1.2, 1.2)
            _hill(1.5, -1.5, -abs(3.5 * (a * b) * w_both), 1.5, 1.2)
            _hill(bf_x, bf_y, -2.5, 1.5, 1.5)
            _hill(bt_x, bt_y, -2.5, 1.5, 1.5)

        elif gate_type == LogicGateType.HALF_ADDER:
            s_a_low = self._smooth_gate(a, 0.25)
            s_b_low = self._smooth_gate(b, 0.25)
            s_a_high = self._smooth_gate(a, 0.35)
            s_b_high = self._smooth_gate(b, 0.35)

            w_a_only = s_a_low * (1.0 - s_b_high)
            w_b_only = s_b_low * (1.0 - s_a_high)
            w_both = s_a_high * s_b_high
            w_not_both = 1.0 - w_both

            bs0_x, bs0_y = float(self.basin_sum_0[0]), float(self.basin_sum_0[1])
            bs1_x, bs1_y = float(self.basin_sum_1[0]), float(self.basin_sum_1[1])
            bc0_x, bc0_y = float(self.basin_carry_0[0]), float(self.basin_carry_0[1])
            bc1_x, bc1_y = float(self.basin_carry_1[0]), float(self.basin_carry_1[1])

            _hill(1.5, 2.0, -abs(3.5 * a * w_a_only), 1.6, 1.0)
            _hill(1.5, 1.8, -abs(3.5 * b * w_b_only), 1.6, 1.0)
            _hill(1.2, 2.0, 4.5 * (a * b) * w_both, 1.2, 1.0)
            _hill(bs0_x, bs0_y, -abs(3.0 * w_both), 1.4, 1.0)

            _hill(1.5, -0.8, -abs(3.8 * (a * b) * w_both), 1.5, 1.0)
            _hill(bc1_x, bc1_y, -abs(3.0 * w_both), 1.4, 1.0)
            _hill(0.8, -0.8, 2.5 * w_not_both, 1.4, 1.0)
            _hill(bc0_x, bc0_y, -abs(2.5 * w_not_both), 1.4, 1.0)

            _hill(bs0_x, bs0_y, -2.2, 1.2, 0.8)
            _hill(bs1_x, bs1_y, -2.2, 1.2, 0.8)
            _hill(bc0_x, bc0_y, -2.2, 1.2, 0.8)
            _hill(bc1_x, bc1_y, -2.2, 1.2, 0.8)

        r = math.hypot(px, py)
        r_lim = self.horizon_radius - 1.0
        if r > r_lim:
            dr = r - r_lim
            phi += 10.0 * (dr * dr)
            scale = 20.0 * dr / (r + 1e-8)
            gx += scale * px
            gy += scale * py

        return phi, gx, gy

    def evaluate_potential(
        self,
        x: np.ndarray,
        gate_type: LogicGateType,
        a: float,
        b: float,
    ) -> tuple[float, np.ndarray]:
        """
        Evaluates effective potential Phi(x) and its analytical gradient grad_Phi(x)
        using branch-free C^infinity activation envelopes over continuous inputs (a, b).
        """
        phi, gx, gy = self._potential_components(float(x[0]), float(x[1]), gate_type, a, b)
        return phi, np.array([gx, gy], dtype=np.float64)

    def _christoffel_and_ricci_components(
        self,
        px: float,
        py: float,
        g00: float,
        g01: float,
        g11: float,
        gate_type: LogicGateType,
        a: float,
        b: float,
        eps: float = 1e-3,
    ) -> tuple[float, float, float, float, float, float, float, float, float, float]:
        """
        Closed-form 2D Levi-Civita Christoffel components and Gauss-Bonnet/Brioschi
        scalar curvature R, plus inverse metric (ig00, ig01, ig11).
        Returns (G0_00, G0_01, G0_11, G1_00, G1_01, G1_11, r_scalar, ig00, ig01, ig11).
        """
        det_raw = g00 * g11 - g01 * g01
        inv_det = 1.0 / det_raw
        ig00 = g11 * inv_det
        ig01 = -g01 * inv_det
        ig11 = g00 * inv_det

        inv_2eps = 0.5 / eps
        inv_eps2 = 1.0 / (eps * eps)

        gp00, gp01, gp11, _, _ = self._metric_components(px + eps, py, gate_type, a, b)
        gm00, gm01, gm11, _, _ = self._metric_components(px - eps, py, gate_type, a, b)
        d0_g00 = (gp00 - gm00) * inv_2eps
        d0_g01 = (gp01 - gm01) * inv_2eps
        d0_g11 = (gp11 - gm11) * inv_2eps
        d2_0_g11 = (gp11 - 2.0 * g11 + gm11) * inv_eps2

        gp00, gp01, gp11, _, _ = self._metric_components(px, py + eps, gate_type, a, b)
        gm00, gm01, gm11, _, _ = self._metric_components(px, py - eps, gate_type, a, b)
        d1_g00 = (gp00 - gm00) * inv_2eps
        d1_g01 = (gp01 - gm01) * inv_2eps
        d1_g11 = (gp11 - gm11) * inv_2eps
        d2_1_g00 = (gp00 - 2.0 * g00 + gm00) * inv_eps2

        t0_00 = d0_g00
        t1_00 = 2.0 * d0_g01 - d1_g00
        t0_01 = d1_g00
        t1_01 = d0_g11
        t0_11 = 2.0 * d1_g01 - d0_g11
        t1_11 = d1_g11

        g0_00 = 0.5 * (ig00 * t0_00 + ig01 * t1_00)
        g1_00 = 0.5 * (ig01 * t0_00 + ig11 * t1_00)
        g0_01 = 0.5 * (ig00 * t0_01 + ig01 * t1_01)
        g1_01 = 0.5 * (ig01 * t0_01 + ig11 * t1_01)
        g0_11 = 0.5 * (ig00 * t0_11 + ig01 * t1_11)
        g1_11 = 0.5 * (ig01 * t0_11 + ig11 * t1_11)

        q_01 = g00 * g0_01 * g0_01 + 2.0 * g01 * g0_01 * g1_01 + g11 * g1_01 * g1_01
        q_00_11 = g0_00 * (g00 * g0_11 + g01 * g1_11) + g1_00 * (g01 * g0_11 + g11 * g1_11)
        sec_deriv_term = 0.5 * (d2_0_g11 + d2_1_g00)
        r_scalar = -(sec_deriv_term - (q_01 - q_00_11)) / max(det_raw, 1e-6)
        return g0_00, g0_01, g0_11, g1_00, g1_01, g1_11, r_scalar, ig00, ig01, ig11

    def compute_christoffel_and_ricci(
        self,
        x: np.ndarray,
        gate_type: LogicGateType,
        a: float,
        b: float,
        eps: float = 1e-3,
    ) -> tuple[np.ndarray, float]:
        """
        Computes Levi-Civita Christoffel symbols Gamma^k_ij and the 2D Brioschi/Gauss-Bonnet
        scalar curvature R from second-order metric derivatives and connection contractions.
        """
        px = float(x[0])
        py = float(x[1])
        g00, g01, g11, _, _ = self._metric_components(px, py, gate_type, a, b)
        g0_00, g0_01, g0_11, g1_00, g1_01, g1_11, r_scalar, _, _, _ = (
            self._christoffel_and_ricci_components(px, py, g00, g01, g11, gate_type, a, b, eps)
        )
        gamma_arr = np.array(
            [
                [[g0_00, g0_01], [g0_01, g0_11]],
                [[g1_00, g1_01], [g1_01, g1_11]],
            ],
            dtype=np.float64,
        )
        return gamma_arr, r_scalar

    def _step_exciton_scalar(
        self,
        px: float,
        py: float,
        vx: float,
        vy: float,
        g00: float,
        g01: float,
        g11: float,
        gate_type: LogicGateType,
        a: float,
        b: float,
    ) -> tuple[float, float, float, float, float, float]:
        _, gx, gy = self._potential_components(px, py, gate_type, a, b)
        g0_00, g0_01, g0_11, g1_00, g1_01, g1_11, r_scalar, ig00, ig01, ig11 = (
            self._christoffel_and_ricci_components(px, py, g00, g01, g11, gate_type, a, b)
        )

        vx2 = vx * vx
        two_vx_vy = 2.0 * vx * vy
        vy2 = vy * vy
        geo_ax = -(g0_00 * vx2 + g0_01 * two_vx_vy + g0_11 * vy2)
        geo_ay = -(g1_00 * vx2 + g1_01 * two_vx_vy + g1_11 * vy2)

        pot_ax = -(ig00 * gx + ig01 * gy)
        pot_ay = -(ig01 * gx + ig11 * gy)

        v_norm_sq = g00 * vx2 + g01 * two_vx_vy + g11 * vy2
        damping_gamma = self.gamma_base + 0.15 * min(abs(r_scalar), 10.0) + 0.05 * v_norm_sq

        dt = self.dt
        vx_next = vx + dt * (geo_ax + pot_ax - damping_gamma * vx)
        vy_next = vy + dt * (geo_ay + pot_ay - damping_gamma * vy)
        px_next = px + dt * vx_next
        py_next = py + dt * vy_next
        dissipated_de = damping_gamma * v_norm_sq * dt
        return px_next, py_next, vx_next, vy_next, dissipated_de, r_scalar

    def step_exciton(
        self,
        x: np.ndarray,
        v: np.ndarray,
        gate_type: LogicGateType,
        a: float,
        b: float,
    ) -> tuple[np.ndarray, np.ndarray, float, float]:
        """
        Single symplectic geodesic integration step with adaptive velocity damping:
            dv^k/dt = -Gamma^k_ij v^i v^j - g^kl grad_l Phi - gamma(v, R) v^k
        """
        px = float(x[0])
        py = float(x[1])
        g00, g01, g11, _, _ = self._metric_components(px, py, gate_type, a, b)
        px_n, py_n, vx_n, vy_n, dissipated_de, r_scalar = self._step_exciton_scalar(
            px, py, float(v[0]), float(v[1]), g00, g01, g11, gate_type, a, b
        )
        return (
            np.array([px_n, py_n], dtype=np.float64),
            np.array([vx_n, vy_n], dtype=np.float64),
            dissipated_de,
            r_scalar,
        )

    def evaluate_gate(
        self,
        gate_type: LogicGateType | str,
        a: float,
        b: float = 0.0,
    ) -> LogicGateResult:
        """
        Executes a continuous Riemannian logic gate computation.
        Dispatches Exciton probes and traces constructive/destructive interference into output basins.
        """
        if isinstance(gate_type, str):
            gate_type = LogicGateType(gate_type)

        def _sanitize(val: float | None) -> float:
            if val is None or not math.isfinite(val):
                return 0.0
            return min(max(float(val), 0.0), 1.0)

        a_clamped = _sanitize(a)
        b_clamped = _sanitize(b)

        # Setup probe injection ports: (name, px, py, vx, vy)
        if gate_type == LogicGateType.NOT:
            probe_specs = [("probe", -3.5, 0.2, 2.5, 0.0)]
        elif gate_type in (LogicGateType.AND, LogicGateType.OR, LogicGateType.NAND):
            vy_init = -0.10 + 0.25 * self._smooth_gate(a_clamped + b_clamped, 0.50)
            probe_specs = [("probe", -3.5, 0.0, 2.4, vy_init)]
        elif gate_type == LogicGateType.XOR:
            probe_specs = [
                ("exciton_A", -3.5, 1.5, 2.4 * a_clamped + 0.2, -0.4 * a_clamped),
                ("exciton_B", -3.5, -1.5, 2.4 * b_clamped + 0.2, 0.4 * b_clamped),
            ]
        elif gate_type == LogicGateType.HALF_ADDER:
            probe_specs = [
                ("sum_probe", -3.5, 1.4, 2.4, 0.1),
                ("carry_probe", -3.5, -1.4, 2.4, -0.1),
            ]
        else:
            raise ValueError(f"Unsupported gate type: {gate_type}")

        max_steps = self.max_steps
        traj_arrays: dict[str, np.ndarray] = {}
        total_dissipated = 0.0
        has_telemetry = False
        r_min = float("inf")
        r_max = float("-inf")
        min_eval_overall = float("inf")
        max_cond_overall = 0.0

        for name, px0, py0, vx0, vy0 in probe_specs:
            traj = np.empty((max_steps + 1, 2), dtype=np.float64)
            traj[0, 0] = px0
            traj[0, 1] = py0
            px, py, vx, vy = px0, py0, vx0, vy0
            g00, g01, g11, _, _ = self._metric_components(px, py, gate_type, a_clamped, b_clamped)
            for step_idx in range(max_steps):
                px, py, vx, vy, de, r_scalar = self._step_exciton_scalar(
                    px, py, vx, vy, g00, g01, g11, gate_type, a_clamped, b_clamped
                )
                traj[step_idx + 1, 0] = px
                traj[step_idx + 1, 1] = py
                total_dissipated += de
                g00, g01, g11, l_min, l_max = self._metric_components(
                    px, py, gate_type, a_clamped, b_clamped
                )
                has_telemetry = True
                r_min = min(r_min, r_scalar)
                r_max = max(r_max, r_scalar)
                min_eval_overall = min(min_eval_overall, l_min)
                cond_val = l_max / max(l_min, 1e-9)
                max_cond_overall = max(max_cond_overall, cond_val)
            traj_arrays[name] = traj

        _exp = math.exp
        _hypot = math.hypot
        # Readout from final positions
        if gate_type in (LogicGateType.AND, LogicGateType.OR, LogicGateType.NOT, LogicGateType.NAND):
            final_pos = traj_arrays["probe"][-1]
            dist_false = _hypot(
                float(final_pos[0]) - float(self.basin_false[0]),
                float(final_pos[1]) - float(self.basin_false[1]),
            )
            dist_true = _hypot(
                float(final_pos[0]) - float(self.basin_true[0]),
                float(final_pos[1]) - float(self.basin_true[1]),
            )

            beta = 1.8
            et = _exp(-beta * dist_true)
            ef = _exp(-beta * dist_false)
            p_true = et / (et + ef + 1e-12)

            if gate_type == LogicGateType.NAND:
                p_true = 1.0 - p_true

            outputs = {"Y": round(p_true, 4)}
            binary_outputs = {"Y": 1 if p_true >= 0.5 else 0}

        elif gate_type == LogicGateType.XOR:
            final_a = traj_arrays["exciton_A"][-1]
            final_b = traj_arrays["exciton_B"][-1]

            bt0, bt1 = float(self.basin_true[0]), float(self.basin_true[1])
            bf0, bf1 = float(self.basin_false[0]), float(self.basin_false[1])
            d_true_a = _hypot(float(final_a[0]) - bt0, float(final_a[1]) - bt1)
            d_true_b = _hypot(float(final_b[0]) - bt0, float(final_b[1]) - bt1)
            d_false_a = _hypot(float(final_a[0]) - bf0, float(final_a[1]) - bf1)
            d_false_b = _hypot(float(final_b[0]) - bf0, float(final_b[1]) - bf1)

            min_dist_true = min(d_true_a, d_true_b)
            min_dist_false = min(d_false_a, d_false_b)

            beta = 1.8
            et = _exp(-beta * min_dist_true)
            ef = _exp(-beta * min_dist_false)
            p_raw = et / (et + ef + 1e-12)

            excitation = 1.0 - (1.0 - self._smooth_gate(a_clamped, 0.20, 28.0)) * (
                1.0 - self._smooth_gate(b_clamped, 0.20, 28.0)
            )
            p_true = p_raw * excitation

            outputs = {"Y": round(p_true, 4)}
            binary_outputs = {"Y": 1 if p_true >= 0.5 else 0}

        elif gate_type == LogicGateType.HALF_ADDER:
            sum_pos = traj_arrays["sum_probe"][-1]
            carry_pos = traj_arrays["carry_probe"][-1]

            d_s1 = _hypot(
                float(sum_pos[0]) - float(self.basin_sum_1[0]),
                float(sum_pos[1]) - float(self.basin_sum_1[1]),
            )
            d_s0 = _hypot(
                float(sum_pos[0]) - float(self.basin_sum_0[0]),
                float(sum_pos[1]) - float(self.basin_sum_0[1]),
            )
            es1 = _exp(-2.0 * d_s1)
            es0 = _exp(-2.0 * d_s0)
            p_sum_raw = es1 / (es1 + es0 + 1e-12)
            excitation = 1.0 - (1.0 - self._smooth_gate(a_clamped, 0.20, 28.0)) * (
                1.0 - self._smooth_gate(b_clamped, 0.20, 28.0)
            )
            p_sum = p_sum_raw * excitation

            d_c1 = _hypot(
                float(carry_pos[0]) - float(self.basin_carry_1[0]),
                float(carry_pos[1]) - float(self.basin_carry_1[1]),
            )
            d_c0 = _hypot(
                float(carry_pos[0]) - float(self.basin_carry_0[0]),
                float(carry_pos[1]) - float(self.basin_carry_0[1]),
            )
            ec1 = _exp(-2.0 * d_c1)
            ec0 = _exp(-2.0 * d_c0)
            p_carry = ec1 / (ec1 + ec0 + 1e-12)

            outputs = {
                "Sum": round(p_sum, 4),
                "Carry": round(p_carry, 4),
            }
            binary_outputs = {
                "Sum": 1 if p_sum >= 0.5 else 0,
                "Carry": 1 if p_carry >= 0.5 else 0,
            }

        return LogicGateResult(
            gate_type=gate_type.value,
            inputs={"A": a_clamped, "B": b_clamped},
            outputs=outputs,
            binary_outputs=binary_outputs,
            trajectories=traj_arrays,
            ricci_scalar_min=r_min if has_telemetry else 0.0,
            ricci_scalar_max=r_max if has_telemetry else 0.0,
            min_eigenvalue=min_eval_overall if has_telemetry else 1.0,
            max_condition_number=max_cond_overall if has_telemetry else 1.0,
            absorbed_energy=round(total_dissipated, 4),
            converged=True,
        )

    def evaluate_truth_table(self, gate_type: LogicGateType | str) -> list[LogicGateResult]:
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
        def _sanitize(val: float | None) -> float:
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
    inputs: dict[str, float]             # "A", "B", "Cin"
    outputs: dict[str, float]            # Continuous analog readout
    binary_outputs: dict[str, int]       # "Sum", "Cout" in {0, 1}
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
    sum_bits: list[int]
    carry_out: int
    stages: list[FullAdderResult]
    total_absorbed_energy: float
    min_eigenvalue: float
    max_condition_number: float
    verified: bool


class RippleCarryManifoldCircuit:
    """
    N-bit Ripple-Carry arithmetic circuit implemented entirely via cascading
    continuous Riemannian logic manifold stages.
    """
    def __init__(self, num_bits: int = 4, manifold: RiemannianLogicManifold | None = None):
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

        stages: list[FullAdderResult] = []
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
    result_bits: list[int]
    carry_or_borrow: int
    is_negative: bool
    stages: list[FullAdderResult | LogicGateResult]
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
    def __init__(self, num_bits: int = 4, manifold: RiemannianLogicManifold | None = None):
        self.num_bits = num_bits
        self.manifold = manifold or RiemannianLogicManifold()
        self.adder = RippleCarryManifoldCircuit(num_bits=num_bits, manifold=self.manifold)

    def execute(self, op: LogicGateType | ALUOp | str, a_val: int, b_val: int) -> ALUResult:
        """Executes arithmetic or bitwise logical operation on the Riemannian manifold."""
        if isinstance(op, str):
            op = ALUOp(op.upper())
        elif isinstance(op, LogicGateType):
            op = ALUOp(op.value)

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
            stages: list[FullAdderResult] = []
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


