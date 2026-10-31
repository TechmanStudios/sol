"""
SOL Engine — Headless Core (Python)
===================================
Phase 0 of the Hippocampus Roadmap.

Pure-Python implementation of the SOL simulation engine, transcribed verbatim
from the SOLPhysics class in sol_dashboard_v3_7_2.html.

SACRED MATH: The core physics equations (pressure, flux, damping, psi
diffusion, conductance, CapLaw) are transcribed verbatim from the dashboard.
They must NOT be modified without updating the math foundation document.

Usage:
    from sol_engine import SOLEngine
    engine = SOLEngine.from_default_graph()
    engine.inject("grail", 50)
    for _ in range(100):
        metrics = engine.step(dt=0.12, c_press=0.1, damping=0.2)
    print(engine.compute_metrics())
"""
from __future__ import annotations

import contextlib
import json
import math
from pathlib import Path
from typing import Any

__all__ = [
    "SOLEngine",
    "SOLPhysics",
    "apply_cap_law",
    "compute_all_edges",
    "compute_metrics",
    "create_engine",
    "get_cap_law_signature",
    "restore_state",
    "snapshot_state",
]

DEFAULT_GRAPH_PATH = Path(__file__).parent / "default_graph.json"


# ---- Utility -----------------------------------------------------------

def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _hash_djb2(s: str) -> str:
    """DJB2 hash matching the dashboard's hashStringDjb2."""
    h = 5381
    for ch in s:
        h = (((h << 5) + h) + ord(ch)) & 0xFFFFFFFF
    return format(h, "x")


# ---- Mulberry32 deterministic PRNG ------------------------------------

class _Rng:
    """Mulberry32 — same seeded PRNG as the headless JS module."""

    def __init__(self, seed: int = 42):
        self._s = seed & 0xFFFFFFFF

    def __call__(self) -> float:
        self._s = (self._s + 0x6D2B79F5) & 0xFFFFFFFF
        t = ((self._s ^ (self._s >> 15)) * (1 | self._s)) & 0xFFFFFFFF
        t = ((t + ((t ^ (t >> 7)) * (61 | t)) & 0xFFFFFFFF) ^ t) & 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4_294_967_296


# ---- SOLPhysics --------------------------------------------------------

class SOLPhysics:
    """
    Pure-Python port of class SOLPhysics from the dashboard.
    All math is transcribed verbatim — see the JS source for derivations.
    """

    def __init__(self, nodes: list[dict], edges: list[dict]):
        # ---- Node init ----
        self.nodes: list[dict] = []
        for n in nodes:
            base = dict(n)
            base.setdefault("rho", 0.0)
            base.setdefault("p", 0.0)
            if "psi_bias" not in base or not isinstance(base["psi_bias"], (int, float)):
                g = base.get("group", "")
                base["psi_bias"] = 1.0 if g == "spirit" else (-1.0 if g == "tech" else 0.0)
            if "psi" not in base or not isinstance(base["psi"], (int, float)):
                base["psi"] = base["psi_bias"]
            base.setdefault("semanticMass", 1.0)
            base.setdefault("semanticMass0", base["semanticMass"])
            base.setdefault("lastInteractionTime", 0.0)
            base.setdefault("isSingularity", False)
            base.setdefault("z_gate", 1.0)
            base.setdefault("r_gate", 1.0)
            base.setdefault("z_bias", 0.0)
            base.setdefault("r_bias", 0.0)

            if base.get("isBattery"):
                base.setdefault("b_q", 0.0)
                base.setdefault("b_charge", 0.0)
                if base.get("b_state") not in (1, -1):
                    base["b_state"] = 1 if base.get("b_q", 0) >= 0 else -1
                base["psi_bias"] = float(base["b_state"])
                base["psi"] = float(base["b_state"])
            self.nodes.append(base)

        self.node_by_id: dict[Any, dict] = {n["id"]: n for n in self.nodes}
        self.node_index_by_id: dict[Any, int] = {n["id"]: idx for idx, n in enumerate(self.nodes)}

        # ---- Edge init ----
        self.edges: list[dict] = []
        for e in edges:
            ed = dict(e)
            if not isinstance(ed.get("w0"), (int, float)):
                ed["w0"] = 1.0
            ed.setdefault("background", False)
            ed["background"] = bool(ed["background"])
            ed["flux"] = 0.0
            ed["conductance"] = 1.0
            # Pre-resolve source and destination node references/indices for speed
            from_id = ed["from"]
            to_id = ed["to"]
            ed["src_node"] = self.node_by_id.get(from_id)
            ed["dst_node"] = self.node_by_id.get(to_id)
            ed["from_idx"] = self.node_index_by_id.get(from_id)
            ed["to_idx"] = self.node_index_by_id.get(to_id)
            self.edges.append(ed)

        self.global_bias = 0.0

        # Psi evolution
        self.psi_diffusion = 0.6
        self.psi_relax_base = 0.12
        self.psi_global_nudge = 0.0
        self.psi_clamp = 1.0

        # Conductance
        self.conductance_base = 1.0
        self.conductance_gamma = 0.75
        self.conductance_min = 0.1
        self.conductance_max = 3.0

        # Battery
        self.battery_cfg = {
            "qMax": 40.0, "qThresh": 16.0, "leakLambda": 0.08,
            "chargeRateSame": 0.32, "chargeRateOpp": 0.18,
            "avalancheGain": 1.15, "resonanceBoost": 1.8,
            "dampingClamp": 0.35, "correctionSink": 0.22,
            "diodeResonanceOut": 1.25, "diodeResonanceIn": 0.80,
            "diodeDampingOut": 0.25, "diodeDampingIn": 1.00,
            "chargeDecayRate": 0.05, "flipThreshold": 0.85,
            "collapseFactor": 0.30, "resonanceDrive": 1.5,
            "dampingDrag": 0.5,
        }

        # Phase gating
        self.phase_cfg = {"omega": 0.15, "surfaceTension": 1.2, "deepViscosity": 0.8}

        # Semantic mass
        self.semantic_cfg = {
            "decayRate": 0.05, "minMass": 0.25,
            "singularityMass": 1000, "reinforceScale": 1.0,
        }

        # MHD
        self.mhd_cfg = {"bBuild": 0.10, "bDecay": 0.06, "bMax": 4.0, "bGamma": 0.35}

        # Jeans
        self.jeans_cfg = {
            "Jcrit": 18.0, "accreteRate": 0.55,
            "starDampingFactor": 0.18, "accreteToMass": 0.04,
        }

        # Vorticity
        self.vort_cfg = {
            "pairsPerNode": 6, "trianglesPerNode": 3, "topK": 10,
            "emaAlpha": 0.20, "leaderboardIntervalSec": 0.75,
            "zMuAlpha": 0.05, "zAbsDevAlpha": 0.05,
        }
        self.vort_norm_local: dict[Any, float] = {}
        self.vort_norm_ema: dict[Any, float] = {}
        self.circ_abs_ema: dict[Any, float] = {}
        self.flux_abs_ema: dict[Any, float] = {}
        self.vort_norm_z_state: dict = {}
        self.circ_abs_z_state: dict = {}
        self.vort_norm_global = 0.0
        self.vort_norm_global_ema = 0.0
        self._last_leaderboard_t = 0.0

        self._t = 0.0
        self._rng = _Rng(42)

        # Integration configuration (forward_euler or rk4)
        self.integration_mode = "forward_euler"

        # Gated Recurrent Manifold Node configuration
        self.gated_recurrent_cfg = {
            "enabled": False,
            "W_z": 0.0,
            "U_z": 0.0,
            "b_z": 10.0,
            "W_r": 0.0,
            "U_r": 0.0,
            "b_r": 10.0,
        }

    def seed_rng(self, seed: int):
        self._rng = _Rng(seed)

    # ---- Semantic Mass Decay ----
    def apply_semantic_mass_decay(self, dt: float):
        cfg = self.semantic_cfg
        if not cfg:
            return
        factor: float | None = None
        min_mass = 0.25
        axiom = 1000
        for n in self.nodes:
            if not n.get("isConstellation"):
                continue
            if n.get("isSingularity"):
                continue
            if factor is None:
                decay = cfg.get("decayRate", 0.05)
                min_mass = cfg.get("minMass", 0.25)
                axiom = cfg.get("singularityMass", 1000)
                factor = math.exp(-decay * max(0.0, dt))
            m = n.get("semanticMass", 1.0)
            n["semanticMass"] = max(min_mass, m * factor)
            if n["semanticMass"] > axiom:
                n["isSingularity"] = True

    def reinforce_semantic_star(self, node: dict, frequency_boost: float = 1.0):
        if not node.get("isConstellation") or not self.semantic_cfg or node.get("isSingularity"):
            return
        cfg = self.semantic_cfg
        decay = cfg.get("decayRate", 0.05)
        min_mass = cfg.get("minMass", 0.25)
        axiom = cfg.get("singularityMass", 1000)
        scale = cfg.get("reinforceScale", 1.0)
        last_t = node.get("lastInteractionTime", 0.0)
        elapsed = max(0.0, self._t - last_t)
        decay_factor = math.exp(-decay * elapsed)
        cur = node.get("semanticMass", 1.0)
        node["semanticMass"] = max(min_mass, cur * decay_factor)
        tension = node.get("tension", 0.0)
        inj = max(0.0, frequency_boost) * (1 + tension) * scale
        node["semanticMass"] += inj
        node["lastInteractionTime"] = self._t
        if node["semanticMass"] > axiom:
            node["isSingularity"] = True

    _DEFAULT_GATE_10 = 1.0 / (1.0 + math.exp(-10.0))

    # ---- Equation of State: P = c * log(1 + rho/m) ----
    def compute_pressure(self, c_press: float):
        _log = math.log
        for n in self.nodes:
            m = n.get("semanticMass", 1.0)
            if not ((m.__class__ is float or isinstance(m, int)) and m > 0.0 and 0.0 * m == 0.0):
                m = 1.0
            n["p"] = c_press * _log(1 + (n["rho"] / m))

    # ---- Psi (Belief Field) Diffusion ----
    def update_psi(self, dt: float):
        nodes = self.nodes
        lap = [0.0] * len(nodes)
        for e in self.edges:
            ia = e["from_idx"]
            ib = e["to_idx"]
            if ia is None or ib is None:
                continue
            d = nodes[ib]["psi"] - nodes[ia]["psi"]
            lap[ia] += d
            lap[ib] -= d

        psi_relax = self.psi_relax_base
        psi_nudge = self.psi_global_nudge
        g_bias = self.global_bias
        psi_diff = self.psi_diffusion
        p_clamp = self.psi_clamp
        neg_clamp = -p_clamp
        for idx, n in enumerate(nodes):
            if n.get("isBattery"):
                s = n.get("b_state", 1)
                if s not in (1, -1):
                    s = 1
                n["b_state"] = s
                s_f = float(s)
                n["psi_bias"] = s_f
                n["psi"] = s_f
                continue
            rho = n["rho"]
            rho_norm = rho / (rho + 40)
            relax_to_bias = (psi_relax * (0.35 + 0.65 * rho_norm)) * (n["psi_bias"] - n["psi"])
            relax_to_global = psi_nudge * (g_bias - n["psi"])
            diffusion = psi_diff * lap[idx]
            p_new = n["psi"] + dt * (diffusion + relax_to_bias + relax_to_global)
            if p_new <= neg_clamp:
                n["psi"] = neg_clamp
            elif p_new < p_clamp:
                n["psi"] = p_new
            else:
                n["psi"] = p_clamp

    def _update_batteries_indexed(
        self,
        dt: float,
        batteries: list[dict],
        bat_edges_by_id: dict[Any, list[tuple[dict, dict | None]]],
    ) -> None:
        cfg = self.battery_cfg
        if not cfg or not batteries:
            return
        res_drive = cfg.get("resonanceDrive", 1.5)
        damp_drag = cfg.get("dampingDrag", 0.5)
        leak_lambda = cfg.get("leakLambda", 0.05)
        leak_lambda_active = leak_lambda * 0.2
        tau = cfg.get("flipThreshold", 0.85)
        collapse_thresh = tau * cfg.get("collapseFactor", 0.3)
        q_max = cfg.get("qMax", 40)
        av_gain = cfg.get("avalancheGain", 1.15)
        _tanh = math.tanh
        _isfinite = math.isfinite

        for b in batteries:
            if b.get("b_state") not in (1, -1):
                b["b_state"] = -1
            b_chg = b.get("b_charge")
            if not (isinstance(b_chg, (float, int)) and _isfinite(b_chg)):
                b["b_charge"] = 0.0
                b_chg = 0.0

            b_id = b["id"]
            connected = bat_edges_by_id.get(b_id, ())
            incoming = 0.0
            drag_val = 0.0
            for e, nb in connected:
                if not nb:
                    continue
                w = e.get("conductance", 1.0)
                if nb.get("isBattery"):
                    nb_state = nb.get("b_state", 1)
                    if nb_state not in (1, -1):
                        nb_state = 1
                else:
                    nb_psi = nb.get("psi", 0)
                    nb_state = 1 if (nb_psi >= 0) else -1
                if nb_state == 1:
                    incoming += w * res_drive
                else:
                    drag_val += w * damp_drag

            net_flux = incoming - drag_val
            charge_delta = _tanh(net_flux) * dt

            b_state = b["b_state"]
            leakage = b_chg * (leak_lambda_active if b_state == 1 else leak_lambda)

            new_chg = b_chg + charge_delta - leakage
            if new_chg <= 0:
                b_chg = 0
            elif new_chg < 1:
                b_chg = new_chg
            else:
                b_chg = 1
            b["b_charge"] = b_chg

            if b_state == -1 and b_chg > tau:
                pulse_mass = q_max * b_chg * av_gain
                share = pulse_mass / max(1, len(connected))
                for _, nb in connected:
                    if nb:
                        nb["rho"] += share
                b["b_state"] = 1
                b["b_charge"] = 1.0
                b["psi"] = 1.0
            elif b_state == 1 and b_chg < collapse_thresh:
                b["b_state"] = -1
                b["psi"] = -1.0

            s_f = float(b["b_state"])
            b["psi"] = s_f
            b["psi_bias"] = s_f

    # ---- Battery (Lighthouse) Logic ----
    def update_batteries(self, dt: float):
        cfg = self.battery_cfg
        if not cfg:
            return
        batteries = [b for b in self.nodes if b.get("isBattery")]
        if not batteries:
            return

        node_by_id = self.node_by_id
        bat_edges_by_id: dict[Any, list[tuple[dict, dict | None]]] = {
            b["id"]: [] for b in batteries
        }
        for e in self.edges:
            u = e["from"]
            v = e["to"]
            u_in = u in bat_edges_by_id
            v_in = (v != u) and (v in bat_edges_by_id)
            if not (u_in or v_in) or e.get("background"):
                continue
            if u_in:
                bat_edges_by_id[u].append((e, node_by_id.get(v)))
            if v_in:
                bat_edges_by_id[v].append((e, node_by_id.get(u)))

        self._update_batteries_indexed(dt, batteries, bat_edges_by_id)

    # ---- Edge Conductance (psi-shaped) ----
    def update_conductance(self, _edges: list[dict] | None = None):
        target_edges = self.edges if _edges is None else _edges
        _exp = math.exp
        c_base = self.conductance_base
        c_gamma = self.conductance_gamma
        c_min = self.conductance_min
        c_max = self.conductance_max
        tight_max = max(c_min, min(c_max, 0.6))

        mhd_cfg = self.mhd_cfg
        has_mhd = bool(mhd_cfg)
        b_gamma = mhd_cfg.get("bGamma", 0.35) if has_mhd else 0.0

        bat_cfg = self.battery_cfg
        has_bat = bool(bat_cfg)
        res_boost = bat_cfg.get("resonanceBoost", 1.8) if has_bat else 1.0
        damp_clamp = bat_cfg.get("dampingClamp", 0.35) if has_bat else 1.0

        for e in target_edges:
            src = e["src_node"]
            dst = e["dst_node"]
            if not src or not dst:
                continue
            avg_psi = (src["psi"] + dst["psi"]) * 0.5
            w = (e["w0"] * c_base) * _exp(c_gamma * avg_psi)

            if has_mhd and "bMag" in e:
                b_mag = e["bMag"]
                if b_mag and (b_mag.__class__ is float or isinstance(b_mag, int)) and 0.0 * b_mag == 0.0:
                    w *= 1 + b_gamma * b_mag

            if has_bat:
                b_node = (
                    src
                    if src.get("isBattery")
                    else (dst if dst.get("isBattery") else None)
                )
                if b_node is not None:
                    s = b_node.get("b_state", 1)
                    if s not in (1, -1):
                        s = 1
                    if s == 1:
                        w *= res_boost
                    else:
                        w *= damp_clamp
                        if w <= c_min:
                            e["conductance"] = c_min
                        elif w < tight_max:
                            e["conductance"] = w
                        else:
                            e["conductance"] = tight_max
                        continue

            if w <= c_min:
                e["conductance"] = c_min
            elif w < c_max:
                e["conductance"] = w
            else:
                e["conductance"] = c_max

    # ---- MHD (Magnetic Frozen-In Field) ----
    def update_magnetic_field(self, dt: float, _edges: list[dict] | None = None):
        cfg = self.mhd_cfg
        if not cfg:
            return
        build = cfg.get("bBuild", 0.10)
        decay = cfg.get("bDecay", 0.06)
        b_max = cfg.get("bMax", 4.0)
        dt_pos = max(0.0, dt)
        decay_factor = math.exp(-decay * dt_pos)
        _abs = abs
        if _edges is None:
            for e in self.edges:
                if e.get("background"):
                    continue
                if "bMag" in e:
                    b_prev = e["bMag"]
                    if not ((b_prev.__class__ is float or isinstance(b_prev, int)) and 0.0 * b_prev == 0.0):
                        b_prev = 0.0
                else:
                    b_prev = 0.0
                f_val = e.get("flux", 0.0)
                b_next = (b_prev * decay_factor) + (build * _abs(f_val) * dt_pos)
                if b_next <= 0:
                    e["bMag"] = 0
                elif b_next < b_max:
                    e["bMag"] = b_next
                else:
                    e["bMag"] = b_max
        else:
            for e in _edges:
                if "bMag" in e:
                    b_prev = e["bMag"]
                    if not ((b_prev.__class__ is float or isinstance(b_prev, int)) and 0.0 * b_prev == 0.0):
                        b_prev = 0.0
                else:
                    b_prev = 0.0
                f_val = e.get("flux", 0.0)
                b_next = (b_prev * decay_factor) + (build * _abs(f_val) * dt_pos)
                if b_next <= 0:
                    e["bMag"] = 0
                elif b_next < b_max:
                    e["bMag"] = b_next
                else:
                    e["bMag"] = b_max

    def _build_tax_neighbors_by_star(self) -> dict[Any, list[dict]]:
        node_by_id = self.node_by_id
        tax_nb_by_star: dict[Any, list[dict]] = {}
        for e in self.edges:
            if e.get("background") or e.get("kind") != "tax":
                continue
            u = e["from"]
            v = e["to"]
            if u == v:
                nb_u = node_by_id.get(u)
                if nb_u and not nb_u.get("isBattery"):
                    if u in tax_nb_by_star:
                        tax_nb_by_star[u].append(nb_u)
                    else:
                        tax_nb_by_star[u] = [nb_u]
            else:
                nb_v = node_by_id.get(v)
                if nb_v and not nb_v.get("isBattery"):
                    if u in tax_nb_by_star:
                        tax_nb_by_star[u].append(nb_v)
                    else:
                        tax_nb_by_star[u] = [nb_v]
                nb_u = node_by_id.get(u)
                if nb_u and not nb_u.get("isBattery"):
                    if v in tax_nb_by_star:
                        tax_nb_by_star[v].append(nb_u)
                    else:
                        tax_nb_by_star[v] = [nb_u]
        return tax_nb_by_star

    # ---- Jeans Collapse and Accretion ----
    def jeans_collapse_and_accrete(
        self,
        dt: float,
        c_press: float,
        damping: float,
        _tax_nb_by_star: dict[Any, list[dict]] | None = None,
    ):
        cfg = self.jeans_cfg
        if not cfg:
            return
        j_crit = cfg.get("Jcrit", 18.0)
        acc_rate = cfg.get("accreteRate", 0.55)
        to_mass = cfg.get("accreteToMass", 0.04)
        tax_nb_map = _tax_nb_by_star
        dt_pos = max(0.0, dt)
        _log = math.log
        _abs = abs
        _min = min

        for star in self.nodes:
            rho = star["rho"]
            p = star.get("p")
            if not ((p.__class__ is float or isinstance(p, int)) and 0.0 * p == 0.0):
                p = c_press * _log(1 + rho)
            j_val = rho / (_abs(p) + 1e-6)

            if j_val >= j_crit:
                if not star.get("isConstellation"):
                    star["isConstellation"] = True
                    star["protoStar"] = True
                star["isStellar"] = True

            if not star.get("isStellar"):
                continue
            if tax_nb_map is None:
                tax_nb_map = self._build_tax_neighbors_by_star()
            if not tax_nb_map:
                continue

            star_id = star["id"]
            neighbors = tax_nb_map.get(star_id)
            if not neighbors:
                continue

            accreted = 0.0
            for nb in neighbors:
                nb_rho = nb["rho"]
                pull = _min(nb_rho, nb_rho * acc_rate * dt_pos)
                if pull <= 0:
                    continue
                nb["rho"] = nb_rho - pull
                star["rho"] += pull
                accreted += pull

            if accreted > 0:
                sm = star.get("semanticMass", 1.0)
                star["semanticMass"] = sm + (accreted * to_mass)

    # ==================================================================
    # MAIN TIME STEP — Lighthouse Protocol (Phase Gating)
    # ==================================================================
    # SACRED MATH — transcribed verbatim from the dashboard.
    # ==================================================================
    def _compute_derivatives(
        self,
        rho_vals: list[float],
        flux_vals: list[float],
        psi_vals: list[float],
        dt: float,
        c_press: float,
        damping: float,
        *,
        _restore: bool = True,
        _apply_state: bool = True,
        _active_edges: list[tuple[int, dict, int, int]] | None = None,
        _active_edge_dicts: list[dict] | None = None,
    ) -> tuple[list[float], list[float], list[float]]:
        nodes = self.nodes
        edges = self.edges
        n_nodes = len(nodes)
        n_edges = len(edges)

        if _restore:
            orig_rho = [n["rho"] for n in nodes]
            orig_flux = [e["flux"] for e in edges]
            orig_psi = [n["psi"] for n in nodes]

        if _apply_state:
            for idx, val in enumerate(rho_vals):
                nodes[idx]["rho"] = val
            if _active_edges is not None:
                for idx, e, _, _ in _active_edges:
                    e["flux"] = flux_vals[idx]
            else:
                for idx, val in enumerate(flux_vals):
                    edges[idx]["flux"] = val
            for idx, val in enumerate(psi_vals):
                nodes[idx]["psi"] = val

        # Recompute derived pressures and conductances based on new rho and psi
        self.compute_pressure(c_press)
        self.update_conductance(_active_edge_dicts if not _restore else None)

        # Phase active masks (based on self._t)
        phase = math.cos(self.phase_cfg["omega"] * self._t * 10)
        is_surface_active = phase > -0.2
        is_deep_active = phase < 0.2

        # Compute gates if GRMN is enabled
        default_gate = self._DEFAULT_GATE_10
        z_gates = [default_gate] * n_nodes
        r_gates = [default_gate] * n_nodes
        _exp = math.exp
        grmn_cfg = self.gated_recurrent_cfg
        if grmn_cfg and grmn_cfg.get("enabled"):
            def_wz = grmn_cfg.get("W_z", 0.0)
            def_uz = grmn_cfg.get("U_z", 0.0)
            def_bz = grmn_cfg.get("b_z", 10.0)
            def_wr = grmn_cfg.get("W_r", 0.0)
            def_ur = grmn_cfg.get("U_r", 0.0)
            def_br = grmn_cfg.get("b_r", 10.0)
            for idx, n in enumerate(nodes):
                w_z = n.get("W_z", def_wz)
                u_z = n.get("U_z", def_uz)
                b_z = n.get("b_z", def_bz)
                w_r = n.get("W_r", def_wr)
                u_r = n.get("U_r", def_ur)
                b_r = n.get("b_r", def_br)

                zb = n.get("z_bias", 0.0)
                rb = n.get("r_bias", 0.0)
                az = w_z * n["rho"] + u_z * n["psi"] + b_z + zb
                cz = _clamp(az, -20.0, 20.0)
                ar = w_r * n["rho"] + u_r * n["psi"] + b_r + rb
                cr = _clamp(ar, -20.0, 20.0)
                z = 1.0 / (1.0 + _exp(-cz))
                r = 1.0 / (1.0 + _exp(-cr))
                z_gates[idx] = z
                r_gates[idx] = r
                n["z_gate"] = z
                n["r_gate"] = r
        else:
            for idx, n in enumerate(nodes):
                rho = n["rho"]
                psi = n["psi"]
                finite_rp = (0.0 * rho == 0.0) and (0.0 * psi == 0.0)
                zb = n.get("z_bias", 0.0)
                if finite_rp and zb == 0.0 and "W_z" not in n and "U_z" not in n and "b_z" not in n:
                    z = default_gate
                else:
                    w_z = n.get("W_z", 0.0)
                    u_z = n.get("U_z", 0.0)
                    b_z = n.get("b_z", 10.0)
                    az = w_z * rho + u_z * psi + b_z + zb
                    z = 1.0 / (1.0 + _exp(-_clamp(az, -20.0, 20.0)))

                rb = n.get("r_bias", 0.0)
                if finite_rp and rb == 0.0 and "W_r" not in n and "U_r" not in n and "b_r" not in n:
                    r = default_gate
                else:
                    w_r = n.get("W_r", 0.0)
                    u_r = n.get("U_r", 0.0)
                    b_r = n.get("b_r", 10.0)
                    ar = w_r * rho + u_r * psi + b_r + rb
                    r = 1.0 / (1.0 + _exp(-_clamp(ar, -20.0, 20.0)))

                z_gates[idx] = z
                r_gates[idx] = r
                n["z_gate"] = z
                n["r_gate"] = r

        # Modulate pressure with reset gates
        for idx, n in enumerate(nodes):
            n["p"] = r_gates[idx] * n["p"]

        # Compute flux derivatives dF/dt
        d_flux = [0.0] * n_edges
        d_rho_transport = [0.0] * n_nodes

        surf_tension = self.phase_cfg["surfaceTension"]
        deep_visc = self.phase_cfg["deepViscosity"]
        bat_cfg = self.battery_cfg
        has_bat = bool(bat_cfg)

        if _active_edges is None:
            iter_edges = [
                (idx, e, e["from_idx"], e["to_idx"])
                for idx, e in enumerate(edges)
                if e["from_idx"] is not None and e["to_idx"] is not None
            ]
        else:
            iter_edges = _active_edges

        for idx, e, ia, ib in iter_edges:
            src = e["src_node"]
            dst = e["dst_node"]

            src_group = src.get("group", "bridge")
            dst_group = dst.get("group", "bridge")

            src_awake = not (
                (src_group == "tech" and not is_surface_active)
                or (src_group == "spirit" and not is_deep_active)
            )
            dst_awake = not (
                (dst_group == "tech" and not is_surface_active)
                or (dst_group == "spirit" and not is_deep_active)
            )

            e_flux = e["flux"]
            if not src_awake and not dst_awake:
                d_flux[idx] = -e_flux
                continue

            delta_p = src["p"] - dst["p"]

            tension = 1.0
            if src_group == "tech" or dst_group == "tech":
                tension = surf_tension
            if src_group == "spirit" or dst_group == "spirit":
                tension = deep_visc

            diode_gain = 1.0
            if has_bat and not e.get("background"):
                src_bat = bool(src.get("isBattery"))
                dst_bat = bool(dst.get("isBattery"))
                if src_bat or dst_bat:
                    b_node = src if src_bat else dst
                    b_s = b_node.get("b_state", 1)
                    if b_s not in (1, -1):
                        b_s = 1
                    outflow = (delta_p > 0) if src_bat else (delta_p < 0)
                    if b_s == 1:
                        diode_gain = bat_cfg["diodeResonanceOut"] if outflow else bat_cfg["diodeResonanceIn"]
                    else:
                        diode_gain = bat_cfg["diodeDampingOut"] if outflow else bat_cfg["diodeDampingIn"]

            target_flux = (e["conductance"] * tension * diode_gain) * delta_p
            d_flux[idx] = target_flux - e_flux

            flow_amt_rate = e_flux * 0.5
            if src_awake:
                d_rho_transport[ia] -= flow_amt_rate
            if dst_awake:
                d_rho_transport[ib] += flow_amt_rate

        # Compute drho/dt
        d_rho = [0.0] * n_nodes
        jeans_cfg = self.jeans_cfg
        has_jeans = bool(jeans_cfg)
        star_damp = jeans_cfg.get("starDampingFactor", 0.18) if has_jeans else 1.0
        damp_base = -damping * 0.1
        for idx, n in enumerate(nodes):
            star_factor = star_damp if (has_jeans and n.get("isStellar")) else 1.0
            decay_rate = damp_base * star_factor * n["rho"]
            d_rho[idx] = z_gates[idx] * (d_rho_transport[idx] + decay_rate)

        # Compute dpsi/dt
        lap = [0.0] * n_nodes
        for _, _, ia, ib in iter_edges:
            d = nodes[ib]["psi"] - nodes[ia]["psi"]
            lap[ia] += d
            lap[ib] -= d

        d_psi = [0.0] * n_nodes
        psi_relax = self.psi_relax_base
        psi_nudge = self.psi_global_nudge
        g_bias = self.global_bias
        psi_diff = self.psi_diffusion
        for idx, n in enumerate(nodes):
            if n.get("isBattery"):
                continue
            rho = n["rho"]
            rho_norm = rho / (rho + 40)
            relax_to_bias = (psi_relax * (0.35 + 0.65 * rho_norm)) * (n["psi_bias"] - n["psi"])
            relax_to_global = psi_nudge * (g_bias - n["psi"])
            diffusion = psi_diff * lap[idx]
            d_psi[idx] = diffusion + relax_to_bias + relax_to_global

        if _restore:
            for idx, val in enumerate(orig_rho):
                nodes[idx]["rho"] = val
            for idx, val in enumerate(orig_flux):
                edges[idx]["flux"] = val
            for idx, val in enumerate(orig_psi):
                nodes[idx]["psi"] = val
            self.compute_pressure(c_press)
            self.update_conductance()

        return d_rho, d_flux, d_psi

    def run_rk4_steps(
        self,
        steps: int,
        dt: float,
        c_press: float,
        damping: float,
        *,
        pre_step_node: dict | None = None,
        pre_step_rho: float = 500.0,
        pre_step_psi: float = 0.0,
    ) -> dict:
        nodes = self.nodes
        edges = self.edges
        if steps <= 0:
            return {
                "totalFlux": sum(abs(e["flux"]) for e in edges),
                "activeCount": sum(1 for n in nodes if n["rho"] > 0.1),
            }

        n_nodes = len(nodes)
        _log = math.log
        _exp = math.exp
        _cos = math.cos
        _max = max

        default_gate = self._DEFAULT_GATE_10
        grmn_cfg = self.gated_recurrent_cfg
        grmn_enabled = bool(grmn_cfg and grmn_cfg.get("enabled"))
        if grmn_enabled:
            def_wz = grmn_cfg.get("W_z", 0.0)
            def_uz = grmn_cfg.get("U_z", 0.0)
            def_bz = grmn_cfg.get("b_z", 10.0)
            def_wr = grmn_cfg.get("W_r", 0.0)
            def_ur = grmn_cfg.get("U_r", 0.0)
            def_br = grmn_cfg.get("b_r", 10.0)
            grmn_params: list[tuple[float, float, float, float, float, float, float, float]] = [
                (
                    n.get("W_z", def_wz),
                    n.get("U_z", def_uz),
                    n.get("b_z", def_bz),
                    n.get("z_bias", 0.0),
                    n.get("W_r", def_wr),
                    n.get("U_r", def_ur),
                    n.get("b_r", def_br),
                    n.get("r_bias", 0.0),
                )
                for n in nodes
            ]
            custom_z: list[tuple[int, float, float, float, float]] = []
            custom_r: list[tuple[int, float, float, float, float]] = []
        else:
            grmn_params = []
            custom_z = []
            custom_r = []
            for i, n in enumerate(nodes):
                zb = n.get("z_bias", 0.0)
                if zb != 0.0 or "W_z" in n or "U_z" in n or "b_z" in n:
                    custom_z.append(
                        (
                            i,
                            n.get("W_z", 0.0),
                            n.get("U_z", 0.0),
                            n.get("b_z", 10.0),
                            zb,
                        )
                    )
                rb = n.get("r_bias", 0.0)
                if rb != 0.0 or "W_r" in n or "U_r" in n or "b_r" in n:
                    custom_r.append(
                        (
                            i,
                            n.get("W_r", 0.0),
                            n.get("U_r", 0.0),
                            n.get("b_r", 10.0),
                            rb,
                        )
                    )

        jeans_cfg = self.jeans_cfg
        has_jeans = bool(jeans_cfg)
        star_damp = jeans_cfg.get("starDampingFactor", 0.18) if has_jeans else 1.0
        damp_base = -damping * 0.1

        c_base = self.conductance_base
        c_gamma = self.conductance_gamma
        c_min = self.conductance_min
        c_max = self.conductance_max
        tight_max = max(c_min, min(c_max, 0.6))

        mhd_cfg = self.mhd_cfg
        has_mhd = bool(mhd_cfg)
        b_gamma = mhd_cfg.get("bGamma", 0.35) if has_mhd else 0.0
        mhd_edges = [e for e in edges if not e.get("background")] if (has_mhd and steps > 1) else None

        bat_cfg = self.battery_cfg
        has_bat = bool(bat_cfg)
        res_boost = bat_cfg.get("resonanceBoost", 1.8) if has_bat else 1.0
        damp_clamp = bat_cfg.get("dampingClamp", 0.35) if has_bat else 1.0
        if has_bat:
            d_res_out = bat_cfg["diodeResonanceOut"]
            d_res_in = bat_cfg["diodeResonanceIn"]
            d_dmp_out = bat_cfg["diodeDampingOut"]
            d_dmp_in = bat_cfg["diodeDampingIn"]
            batteries = [b for b in nodes if b.get("isBattery")]
        else:
            d_res_out = 1.0
            d_res_in = 1.0
            d_dmp_out = 1.0
            d_dmp_in = 1.0
            batteries = []

        bat_edges_by_id: dict[Any, list[tuple[dict, dict | None]]] = {}
        unique_bat_edges: list[dict] = []
        if batteries:
            node_by_id = self.node_by_id
            bat_edges_by_id = {b["id"]: [] for b in batteries}
            seen_bat_edge_ids: set[int] = set()
            for e in edges:
                u = e["from"]
                v = e["to"]
                u_in = u in bat_edges_by_id
                v_in = (v != u) and (v in bat_edges_by_id)
                if not (u_in or v_in) or e.get("background"):
                    continue
                if u_in:
                    bat_edges_by_id[u].append((e, node_by_id.get(v)))
                if v_in:
                    bat_edges_by_id[v].append((e, node_by_id.get(u)))
                eid = id(e)
                if eid not in seen_bat_edge_ids:
                    seen_bat_edge_ids.add(eid)
                    unique_bat_edges.append(e)

        surf_tension = self.phase_cfg["surfaceTension"]
        deep_visc = self.phase_cfg["deepViscosity"]
        omega10 = self.phase_cfg["omega"] * 10

        is_bat_arr = [bool(n.get("isBattery")) for n in nodes]
        active_edge_refs: list[dict] = []
        edge_ia: list[int] = []
        edge_ib: list[int] = []
        edge_w0_base: list[float] = []
        edge_special: list[tuple[int, int, int, float, int, float, float] | None] = []
        bat_edge_specs: list[tuple[int, dict, bool, int, int, float, bool]] = []
        compiled_edges: list[tuple[int, int, float, float | None, tuple | None]] = []
        for e in edges:
            ia = e["from_idx"]
            ib = e["to_idx"]
            if ia is None or ib is None:
                continue
            src = e["src_node"]
            dst = e["dst_node"]
            src_group = src.get("group", "bridge")
            dst_group = dst.get("group", "bridge")
            sg_code = 1 if src_group == "tech" else (2 if src_group == "spirit" else 0)
            dg_code = 1 if dst_group == "tech" else (2 if dst_group == "spirit" else 0)
            tension = 1.0
            if sg_code == 1 or dg_code == 1:
                tension = surf_tension
            if sg_code == 2 or dg_code == 2:
                tension = deep_visc
            w0_base = e["w0"] * c_base
            is_bg = bool(e.get("background"))
            a_idx = len(active_edge_refs)
            active_edge_refs.append(e)
            edge_ia.append(ia)
            edge_ib.append(ib)
            edge_w0_base.append(w0_base)

            src_bat = is_bat_arr[ia]
            dst_bat = is_bat_arr[ib]
            if has_bat and (src_bat or dst_bat):
                b_node = src if src_bat else dst
                bat_edge_specs.append((a_idx, b_node, src_bat, sg_code, dg_code, tension, is_bg))
                spec: tuple[int, int, int, float, int, float, float] | None = None
            elif sg_code == 0 and dg_code == 0:
                spec = None
            else:
                spec = (0, sg_code, dg_code, tension, 0, 1.0, 1.0)
            edge_special.append(spec)
            compiled_edges.append((ia, ib, w0_base, None, spec))

        tax_nb_cache = self._build_tax_neighbors_by_star() if (has_jeans and steps > 1) else None
        n_active = len(active_edge_refs)
        psi_relax = self.psi_relax_base
        psi_nudge = self.psi_global_nudge
        g_bias = self.global_bias
        psi_diff = self.psi_diffusion
        p_clamp = self.psi_clamp
        neg_clamp = -p_clamp
        half_dt = 0.5 * dt
        dt6 = dt / 6.0

        rho_0 = [0.0] * n_nodes
        psi_0 = [0.0] * n_nodes
        m_arr = [1.0] * n_nodes
        damp_arr = [damp_base] * n_nodes
        psi_bias_arr = [0.0] * n_nodes
        rho_s = [0.0] * n_nodes
        psi_s = [0.0] * n_nodes
        flux_a0 = [0.0] * n_active
        flux_s = [0.0] * n_active

        def _eval_rk4_stage(
            rho_st: list[float],
            flux_st: list[float],
            psi_st: list[float],
            t_stage: float,
        ) -> tuple[list[float], list[float], list[float]]:
            p_arr = [0.0] * n_nodes
            z_arr: list[float] | None = None
            if grmn_enabled:
                z_arr = [default_gate] * n_nodes
                for i in range(n_nodes):
                    rho_i = rho_st[i]
                    psi_i = psi_st[i]
                    w_z, u_z, b_z, zb, w_r, u_r, b_r, rb = grmn_params[i]
                    az = w_z * rho_i + u_z * psi_i + b_z + zb
                    if az <= -20.0:
                        cz = -20.0
                    elif az < 20.0:
                        cz = az
                    else:
                        cz = 20.0
                    ar = w_r * rho_i + u_r * psi_i + b_r + rb
                    if ar <= -20.0:
                        cr = -20.0
                    elif ar < 20.0:
                        cr = ar
                    else:
                        cr = 20.0
                    z_arr[i] = 1.0 / (1.0 + _exp(-cz))
                    r_val = 1.0 / (1.0 + _exp(-cr))
                    p_arr[i] = r_val * (c_press * _log(1 + (rho_i / m_arr[i])))
            else:
                for i in range(n_nodes):
                    rho_i = rho_st[i]
                    psi_i = psi_st[i]
                    p_raw = c_press * _log(1 + (rho_i / m_arr[i]))
                    if (0.0 * rho_i == 0.0) and (0.0 * psi_i == 0.0):
                        p_arr[i] = default_gate * p_raw
                    else:
                        if z_arr is None:
                            z_arr = [default_gate] * n_nodes
                        az = 0.0 * rho_i + 0.0 * psi_i + 10.0 + 0.0
                        if az <= -20.0:
                            cz = -20.0
                        elif az < 20.0:
                            cz = az
                        else:
                            cz = 20.0
                        z_val = 1.0 / (1.0 + _exp(-cz))
                        z_arr[i] = z_val
                        p_arr[i] = z_val * p_raw
                if custom_r:
                    for i, w_r, u_r, b_r, rb in custom_r:
                        rho_i = rho_st[i]
                        ar = w_r * rho_i + u_r * psi_st[i] + b_r + rb
                        if ar <= -20.0:
                            cr = -20.0
                        elif ar < 20.0:
                            cr = ar
                        else:
                            cr = 20.0
                        r_val = 1.0 / (1.0 + _exp(-cr))
                        p_arr[i] = r_val * (c_press * _log(1 + (rho_i / m_arr[i])))
                if custom_z:
                    if z_arr is None:
                        z_arr = [default_gate] * n_nodes
                    for i, w_z, u_z, b_z, zb in custom_z:
                        az = w_z * rho_st[i] + u_z * psi_st[i] + b_z + zb
                        if az <= -20.0:
                            cz = -20.0
                        elif az < 20.0:
                            cz = az
                        else:
                            cz = 20.0
                        z_arr[i] = 1.0 / (1.0 + _exp(-cz))

            d_flux = [0.0] * n_active
            d_rho_tr = [0.0] * n_nodes
            lap = [0.0] * n_nodes

            phase = _cos(omega10 * t_stage)
            is_surf = phase > -0.2
            is_deep = phase < 0.2
            for a_idx, (ia, ib, w0_base, bmag_mul, special) in enumerate(compiled_edges):
                psi_a = psi_st[ia]
                psi_b = psi_st[ib]
                d_psi_e = psi_b - psi_a
                lap[ia] += d_psi_e
                lap[ib] -= d_psi_e

                if special is None:
                    w = w0_base * _exp(c_gamma * ((psi_a + psi_b) * 0.5))
                    if bmag_mul is not None:
                        w *= bmag_mul
                    if w <= c_min:
                        cond = c_min
                    elif w < c_max:
                        cond = w
                    else:
                        cond = c_max
                    e_flux = flux_st[a_idx]
                    d_flux[a_idx] = cond * (p_arr[ia] - p_arr[ib]) - e_flux
                    flow_amt = e_flux * 0.5
                    d_rho_tr[ia] -= flow_amt
                    d_rho_tr[ib] += flow_amt
                    continue

                (
                    bat_cond_mode,
                    sg_code,
                    dg_code,
                    tension,
                    diode_mode,
                    gain_out,
                    gain_in,
                ) = special
                src_awake = not ((sg_code == 1 and not is_surf) or (sg_code == 2 and not is_deep))
                dst_awake = not ((dg_code == 1 and not is_surf) or (dg_code == 2 and not is_deep))
                e_flux = flux_st[a_idx]
                if not src_awake and not dst_awake:
                    d_flux[a_idx] = -e_flux
                    continue

                w = w0_base * _exp(c_gamma * ((psi_a + psi_b) * 0.5))
                if bmag_mul is not None:
                    w *= bmag_mul
                if bat_cond_mode == 1:
                    w *= res_boost
                    if w <= c_min:
                        cond = c_min
                    elif w < c_max:
                        cond = w
                    else:
                        cond = c_max
                elif bat_cond_mode == -1:
                    w *= damp_clamp
                    if w <= c_min:
                        cond = c_min
                    elif w < tight_max:
                        cond = w
                    else:
                        cond = tight_max
                else:
                    if w <= c_min:
                        cond = c_min
                    elif w < c_max:
                        cond = w
                    else:
                        cond = c_max

                delta_p = p_arr[ia] - p_arr[ib]
                if diode_mode == 0:
                    diode_gain = 1.0
                elif diode_mode == 1:
                    diode_gain = gain_out if delta_p > 0 else gain_in
                else:
                    diode_gain = gain_out if delta_p < 0 else gain_in

                d_flux[a_idx] = (cond * tension * diode_gain) * delta_p - e_flux
                flow_amt = e_flux * 0.5
                if src_awake:
                    d_rho_tr[ia] -= flow_amt
                if dst_awake:
                    d_rho_tr[ib] += flow_amt

            d_rho = [0.0] * n_nodes
            if z_arr is None:
                for i in range(n_nodes):
                    d_rho[i] = default_gate * (d_rho_tr[i] + damp_arr[i] * rho_st[i])
            else:
                for i in range(n_nodes):
                    d_rho[i] = z_arr[i] * (d_rho_tr[i] + damp_arr[i] * rho_st[i])

            d_psi = [0.0] * n_nodes
            for i in range(n_nodes):
                if is_bat_arr[i]:
                    continue
                rho_i = rho_st[i]
                psi_i = psi_st[i]
                rho_norm = rho_i / (rho_i + 40)
                relax_to_bias = (psi_relax * (0.35 + 0.65 * rho_norm)) * (psi_bias_arr[i] - psi_i)
                relax_to_global = psi_nudge * (g_bias - psi_i)
                d_psi[i] = psi_diff * lap[i] + relax_to_bias + relax_to_global

            return d_rho, d_flux, d_psi

        for step_idx in range(steps):
            is_last = step_idx == (steps - 1)
            if pre_step_node is not None:
                pre_step_node["rho"] = pre_step_rho
                pre_step_node["psi"] = pre_step_psi

            self.apply_semantic_mass_decay(dt)
            if batteries:
                self._update_batteries_indexed(dt, batteries, bat_edges_by_id)

            for i, n in enumerate(nodes):
                rho_0[i] = n["rho"]
                psi_0[i] = n["psi"]
                m = n.get("semanticMass", 1.0)
                if not ((m.__class__ is float or isinstance(m, int)) and m > 0.0 and 0.0 * m == 0.0):
                    m = 1.0
                m_arr[i] = m
                damp_arr[i] = (
                    damp_base * star_damp
                    if (has_jeans and n.get("isStellar"))
                    else damp_base
                )
                if not is_bat_arr[i]:
                    psi_bias_arr[i] = n["psi_bias"]

            for a_idx, b_node, src_bat, sg_code, dg_code, tension, is_bg in bat_edge_specs:
                s_c = b_node.get("b_state", 1)
                if s_c not in (1, -1):
                    s_c = 1
                bat_cond_mode = 1 if s_c == 1 else -1
                if not is_bg:
                    diode_mode = 1 if src_bat else 2
                    if s_c == 1:
                        gain_out = d_res_out
                        gain_in = d_res_in
                    else:
                        gain_out = d_dmp_out
                        gain_in = d_dmp_in
                else:
                    diode_mode = 0
                    gain_out = 1.0
                    gain_in = 1.0
                b_spec = (bat_cond_mode, sg_code, dg_code, tension, diode_mode, gain_out, gain_in)
                edge_special[a_idx] = b_spec
                if not has_mhd:
                    compiled_edges[a_idx] = (
                        edge_ia[a_idx],
                        edge_ib[a_idx],
                        edge_w0_base[a_idx],
                        None,
                        b_spec,
                    )

            if has_mhd:
                for a_idx, e in enumerate(active_edge_refs):
                    flux_a0[a_idx] = e["flux"]
                    bmag_mul: float | None = None
                    if "bMag" in e:
                        b_mag = e["bMag"]
                        if b_mag and (b_mag.__class__ is float or isinstance(b_mag, int)) and 0.0 * b_mag == 0.0:
                            bmag_mul = 1 + b_gamma * b_mag
                    compiled_edges[a_idx] = (
                        edge_ia[a_idx],
                        edge_ib[a_idx],
                        edge_w0_base[a_idx],
                        bmag_mul,
                        edge_special[a_idx],
                    )
            else:
                for a_idx, e in enumerate(active_edge_refs):
                    flux_a0[a_idx] = e["flux"]

            orig_t = self._t

            # 1. k1 at t
            d_rho1, d_flux1, d_psi1 = _eval_rk4_stage(rho_0, flux_a0, psi_0, orig_t)

            # 2. k2 at t + 0.5*dt
            for i in range(n_nodes):
                rho_s[i] = _max(0.0, rho_0[i] + half_dt * d_rho1[i])
                vp = psi_0[i] + half_dt * d_psi1[i]
                if vp <= neg_clamp:
                    psi_s[i] = neg_clamp
                elif vp < p_clamp:
                    psi_s[i] = vp
                else:
                    psi_s[i] = p_clamp
            for a_idx in range(n_active):
                flux_s[a_idx] = flux_a0[a_idx] + half_dt * d_flux1[a_idx]
            t_mid = orig_t + half_dt
            d_rho2, d_flux2, d_psi2 = _eval_rk4_stage(rho_s, flux_s, psi_s, t_mid)

            # 3. k3 at t + 0.5*dt
            for i in range(n_nodes):
                rho_s[i] = _max(0.0, rho_0[i] + half_dt * d_rho2[i])
                vp = psi_0[i] + half_dt * d_psi2[i]
                if vp <= neg_clamp:
                    psi_s[i] = neg_clamp
                elif vp < p_clamp:
                    psi_s[i] = vp
                else:
                    psi_s[i] = p_clamp
            for a_idx in range(n_active):
                flux_s[a_idx] = flux_a0[a_idx] + half_dt * d_flux2[a_idx]
            d_rho3, d_flux3, d_psi3 = _eval_rk4_stage(rho_s, flux_s, psi_s, t_mid)

            # 4. k4 at t + dt
            for i in range(n_nodes):
                rho_s[i] = _max(0.0, rho_0[i] + dt * d_rho3[i])
                vp = psi_0[i] + dt * d_psi3[i]
                if vp <= neg_clamp:
                    psi_s[i] = neg_clamp
                elif vp < p_clamp:
                    psi_s[i] = vp
                else:
                    psi_s[i] = p_clamp
            for a_idx in range(n_active):
                flux_s[a_idx] = flux_a0[a_idx] + dt * d_flux3[a_idx]
            self._t = orig_t + dt
            d_rho4, d_flux4, d_psi4 = _eval_rk4_stage(rho_s, flux_s, psi_s, self._t)

            # Final RK4 update written back to nodes & active edges
            for i in range(n_nodes):
                n = nodes[i]
                r_new = rho_0[i] + dt6 * (d_rho1[i] + 2.0 * d_rho2[i] + 2.0 * d_rho3[i] + d_rho4[i])
                n["rho"] = _max(0.0, r_new)
                p_new = psi_0[i] + dt6 * (d_psi1[i] + 2.0 * d_psi2[i] + 2.0 * d_psi3[i] + d_psi4[i])
                if p_new <= neg_clamp:
                    n["psi"] = neg_clamp
                elif p_new < p_clamp:
                    n["psi"] = p_new
                else:
                    n["psi"] = p_clamp

            for a_idx, e in enumerate(active_edge_refs):
                e["flux"] = flux_a0[a_idx] + dt6 * (
                    d_flux1[a_idx] + 2.0 * d_flux2[a_idx] + 2.0 * d_flux3[a_idx] + d_flux4[a_idx]
                )

            self.compute_pressure(c_press)
            if is_last:
                self.update_conductance()
                if grmn_enabled:
                    for i, n in enumerate(nodes):
                        w_z, u_z, b_z, zb, w_r, u_r, b_r, rb = grmn_params[i]
                        az = w_z * n["rho"] + u_z * n["psi"] + b_z + zb
                        ar = w_r * n["rho"] + u_r * n["psi"] + b_r + rb
                        n["z_gate"] = 1.0 / (1.0 + _exp(-_clamp(az, -20.0, 20.0)))
                        n["r_gate"] = 1.0 / (1.0 + _exp(-_clamp(ar, -20.0, 20.0)))
                else:
                    for n in nodes:
                        rho_f = n["rho"]
                        psi_f = n["psi"]
                        if (0.0 * rho_f == 0.0) and (0.0 * psi_f == 0.0):
                            n["z_gate"] = default_gate
                            n["r_gate"] = default_gate
                        else:
                            az = 0.0 * rho_f + 0.0 * psi_f + 10.0 + 0.0
                            g_f = 1.0 / (1.0 + _exp(-_clamp(az, -20.0, 20.0)))
                            n["z_gate"] = g_f
                            n["r_gate"] = g_f
                    for i, w_z, u_z, b_z, zb in custom_z:
                        n = nodes[i]
                        az = w_z * n["rho"] + u_z * n["psi"] + b_z + zb
                        n["z_gate"] = 1.0 / (1.0 + _exp(-_clamp(az, -20.0, 20.0)))
                    for i, w_r, u_r, b_r, rb in custom_r:
                        n = nodes[i]
                        ar = w_r * n["rho"] + u_r * n["psi"] + b_r + rb
                        n["r_gate"] = 1.0 / (1.0 + _exp(-_clamp(ar, -20.0, 20.0)))
            elif unique_bat_edges:
                self.update_conductance(unique_bat_edges)

            self.update_magnetic_field(dt, mhd_edges)
            self.jeans_collapse_and_accrete(dt, c_press, damping, tax_nb_cache)

        _abs = abs
        total_flux = sum(_abs(e["flux"]) for e in edges)
        active_count = sum(1 for n in nodes if n["rho"] > 0.1)
        return {"totalFlux": total_flux, "activeCount": active_count}

    def step_rk4(self, dt: float, c_press: float, damping: float) -> dict:
        return self.run_rk4_steps(1, dt, c_press, damping)

    def step(self, dt: float, c_press: float, damping: float) -> dict:
        if self.integration_mode == "rk4":
            return self.step_rk4(dt, c_press, damping)

        # --- A. THE HEARTBEAT ---
        self._t += dt

        phase = math.cos(self.phase_cfg["omega"] * self._t * 10)
        is_surface_active = phase > -0.2
        is_deep_active = phase < 0.2

        # --- B. STANDARD UPDATES ---
        self.update_psi(dt)
        self.apply_semantic_mass_decay(dt)
        self.compute_pressure(c_press)
        self.update_conductance()
        self.update_batteries(dt)
        self.compute_pressure(c_press)

        # Compute gates if GRMN is enabled
        nodes = self.nodes
        n_nodes = len(nodes)
        default_gate = self._DEFAULT_GATE_10
        z_gates = [default_gate] * n_nodes
        r_gates = [default_gate] * n_nodes
        _exp = math.exp
        if self.gated_recurrent_cfg and self.gated_recurrent_cfg.get("enabled"):
            cfg = self.gated_recurrent_cfg
            def_wz = cfg.get("W_z", 0.0)
            def_uz = cfg.get("U_z", 0.0)
            def_bz = cfg.get("b_z", 10.0)
            def_wr = cfg.get("W_r", 0.0)
            def_ur = cfg.get("U_r", 0.0)
            def_br = cfg.get("b_r", 10.0)
            for idx, n in enumerate(nodes):
                w_z = n.get("W_z", def_wz)
                u_z = n.get("U_z", def_uz)
                b_z = n.get("b_z", def_bz)
                w_r = n.get("W_r", def_wr)
                u_r = n.get("U_r", def_ur)
                b_r = n.get("b_r", def_br)

                z = 1.0 / (1.0 + _exp(-_clamp(w_z * n["rho"] + u_z * n["psi"] + b_z + n.get("z_bias", 0.0), -20.0, 20.0)))
                r = 1.0 / (1.0 + _exp(-_clamp(w_r * n["rho"] + u_r * n["psi"] + b_r + n.get("r_bias", 0.0), -20.0, 20.0)))
                z_gates[idx] = z
                r_gates[idx] = r
                n["z_gate"] = z
                n["r_gate"] = r
        else:
            for idx, n in enumerate(nodes):
                rho = n["rho"]
                psi = n["psi"]
                finite_rp = (0.0 * rho == 0.0) and (0.0 * psi == 0.0)
                zb = n.get("z_bias", 0.0)
                if finite_rp and zb == 0.0 and "W_z" not in n and "U_z" not in n and "b_z" not in n:
                    z = default_gate
                else:
                    w_z = n.get("W_z", 0.0)
                    u_z = n.get("U_z", 0.0)
                    b_z = n.get("b_z", 10.0)
                    z = 1.0 / (1.0 + _exp(-_clamp(w_z * rho + u_z * psi + b_z + zb, -20.0, 20.0)))

                rb = n.get("r_bias", 0.0)
                if finite_rp and rb == 0.0 and "W_r" not in n and "U_r" not in n and "b_r" not in n:
                    r = default_gate
                else:
                    w_r = n.get("W_r", 0.0)
                    u_r = n.get("U_r", 0.0)
                    b_r = n.get("b_r", 10.0)
                    r = 1.0 / (1.0 + _exp(-_clamp(w_r * rho + u_r * psi + b_r + rb, -20.0, 20.0)))

                z_gates[idx] = z
                r_gates[idx] = r
                n["z_gate"] = z
                n["r_gate"] = r

        # --- C. PHASE-GATED FLUX TRANSPORT ---
        total_flux = 0.0
        d_rho = [0.0] * n_nodes
        surf_tension = self.phase_cfg["surfaceTension"]
        deep_visc = self.phase_cfg["deepViscosity"]
        bat_cfg = self.battery_cfg

        for e in self.edges:
            ia = e["from_idx"]
            ib = e["to_idx"]
            if ia is None or ib is None:
                continue

            src = nodes[ia]
            dst = nodes[ib]

            src_group = src.get("group", "bridge")
            dst_group = dst.get("group", "bridge")

            src_awake = True
            dst_awake = True

            if src_group == "tech" and not is_surface_active:
                src_awake = False
            if src_group == "spirit" and not is_deep_active:
                src_awake = False
            if dst_group == "tech" and not is_surface_active:
                dst_awake = False
            if dst_group == "spirit" and not is_deep_active:
                dst_awake = False

            if not src_awake and not dst_awake:
                continue

            # Modulate pressure with reset gates
            p_src = r_gates[ia] * src["p"]
            p_dst = r_gates[ib] * dst["p"]
            delta_p = p_src - p_dst

            tension = 1.0
            if src_group == "tech" or dst_group == "tech":
                tension = surf_tension
            if src_group == "spirit" or dst_group == "spirit":
                tension = deep_visc

            diode_gain = 1.0
            if bat_cfg and (src.get("isBattery") or dst.get("isBattery")) and not e.get("background"):
                b_node = src if src.get("isBattery") else dst
                b_s = b_node.get("b_state", 1)
                if b_s not in (1, -1):
                    b_s = 1
                batt_is_src = src.get("isBattery")
                outflow = (delta_p > 0) if batt_is_src else (delta_p < 0)
                if b_s == 1:
                    diode_gain = bat_cfg["diodeResonanceOut"] if outflow else bat_cfg["diodeResonanceIn"]
                else:
                    diode_gain = bat_cfg["diodeDampingOut"] if outflow else bat_cfg["diodeDampingIn"]

            target_flux = (e["conductance"] * tension * diode_gain) * delta_p
            e["flux"] = e["flux"] * (1 - dt) + target_flux * dt
            total_flux += abs(e["flux"])

            flow_amt = e["flux"] * dt * 0.5
            if src_awake:
                d_rho[ia] -= flow_amt
            if dst_awake:
                d_rho[ib] += flow_amt

        # Apply mass changes
        for idx, n in enumerate(nodes):
            n["rho"] += z_gates[idx] * d_rho[idx]
            star_factor = 1.0
            if n.get("isStellar") and self.jeans_cfg:
                star_factor = self.jeans_cfg.get("starDampingFactor", 0.18)
            decay_coeff = damping * dt * 0.1 * star_factor * z_gates[idx]
            n["rho"] *= 1.0 - decay_coeff
            if n["rho"] < 0:
                n["rho"] = 0.0

        # MHD + gravity coupling
        self.update_magnetic_field(dt)
        self.compute_pressure(c_press)
        self.jeans_collapse_and_accrete(dt, c_press, damping)

        active_count = sum(1 for n in nodes if n["rho"] > 0.1)
        return {"totalFlux": total_flux, "activeCount": active_count}

    # ---- Injection ----
    def inject(self, label: str, amount: float) -> bool:
        q = str(label).strip().lower()
        if not q:
            return False
        target = None
        for n in self.nodes:
            if n["label"].lower() == q:
                target = n
                break
        if not target and len(q) >= 2:
            matches = [n for n in self.nodes if q in n["label"].lower()]
            if len(matches) == 1:
                target = matches[0]
        if not target:
            return False

        # Event-horizon capture
        if target.get("isConcept"):
            best = None
            for e in self.edges:
                if e.get("kind") != "tax" or e.get("background"):
                    continue
                other_id = None
                if e["from"] == target["id"]:
                    other_id = e["to"]
                elif e["to"] == target["id"]:
                    other_id = e["from"]
                if other_id is None:
                    continue
                other = self.node_by_id.get(other_id)
                if not other or not other.get("isConstellation"):
                    continue
                if not best or other.get("semanticMass", 1) > best.get("semanticMass", 1):
                    best = other
            if best:
                target = best

        target["rho"] += amount

        if target.get("isConstellation"):
            freq_boost = amount / 50.0
            self.reinforce_semantic_star(target, freq_boost)
        return True

    def inject_by_id(self, node_id, amount: float) -> bool:
        node = self.node_by_id.get(node_id)
        if not node:
            return False
        node["rho"] += amount
        return True


# ---- CapLaw (Degree-Power Capacitance Law) ----------------------------

def apply_cap_law(physics: SOLPhysics, cap_law: dict, dt_override: float | None = None) -> dict:
    """Apply the canonical degree-power capacitance law. Transcribed verbatim."""
    if not cap_law or not cap_law.get("enabled"):
        return {"k0": None, "k": None, "alpha": None, "clampMin": None, "clampMax": None}

    alpha = cap_law.get("alpha", 0.8)
    clamp_min = cap_law.get("clampMin", 0.25)
    clamp_max = cap_law.get("clampMax", 5000)
    dt0 = cap_law.get("dt0", 0.12)
    gamma = cap_law.get("kDtGamma", 0.0)
    dt = dt_override if (dt_override is not None and dt_override > 0) else dt0
    include_bg = bool(cap_law.get("includeBackgroundEdges"))

    edges = physics.edges if include_bg else [e for e in physics.edges if not e.get("background")]
    deg_by_id: dict[str, int] = {}
    for n in physics.nodes:
        deg_by_id[str(n["id"])] = 0
    for e in edges:
        a, b = str(e["from"]), str(e["to"])
        if a in deg_by_id:
            deg_by_id[a] += 1
        if b in deg_by_id:
            deg_by_id[b] += 1

    law_family = str(cap_law.get("lawFamily", "power")).lower()

    def proxy_val(node):
        return deg_by_id.get(str(node["id"]), 0)

    anchor = cap_law.get("anchor", {})
    anchor_id = anchor.get("nodeId")
    anchor_node = physics.node_by_id.get(anchor_id)
    sm_ref = anchor.get("smRef")
    if not anchor_node:
        raise ValueError("applyCapLaw: anchor node not found")
    if sm_ref is None:
        raise ValueError("applyCapLaw: anchor smRef missing")

    x_anchor = max(0, proxy_val(anchor_node))
    if x_anchor <= 0:
        raise ValueError("applyCapLaw: anchor proxy is zero")

    k0 = cap_law.get("k0")
    if k0 is None:
        if law_family == "linear":
            k0 = sm_ref / x_anchor
        else:
            k0 = sm_ref / (x_anchor ** alpha)

    k = k0 * ((dt / dt0) ** gamma)

    def clip(v):
        return max(clamp_min, min(clamp_max, v))

    write_to = str(cap_law.get("writeTo", "both")).lower()
    for n in physics.nodes:
        x = max(0, proxy_val(n))
        if law_family == "linear":
            sm_raw = k * x
        else:
            sm_raw = k * (x ** alpha)
        sm = clip(sm_raw)
        if write_to in ("semanticmass", "both"):
            n["semanticMass"] = sm
        if write_to in ("semanticmass0", "both"):
            n["semanticMass0"] = sm

    return {"k0": k0, "k": k, "alpha": alpha, "clampMin": clamp_min, "clampMax": clamp_max}


def get_cap_law_signature(cap_law: dict | None) -> str:
    law = cap_law or {}
    anchor = law.get("anchor", {}) or {}
    sig = {
        "enabled": bool(law.get("enabled")),
        "lawFamily": str(law.get("lawFamily", "")),
        "proxy": str(law.get("proxy", "")),
        "alpha": law.get("alpha"),
        "k0": law.get("k0"),
        "dt0": law.get("dt0"),
        "kDtGamma": law.get("kDtGamma"),
        "lambda": law.get("lambda"),
        "clampMin": law.get("clampMin"),
        "clampMax": law.get("clampMax"),
        "anchor": {"nodeId": anchor.get("nodeId"), "smRef": anchor.get("smRef")},
        "includeBackgroundEdges": bool(law.get("includeBackgroundEdges")),
        "writeTo": str(law.get("writeTo", "")),
    }
    return json.dumps(sig)


# ---- Metrics -----------------------------------------------------------

def compute_metrics(physics: SOLPhysics) -> dict:
    """Compute metrics identically to the dashboard tick loop."""
    nodes = physics.nodes
    edges = physics.edges

    sum_rho = 0.0
    max_rho = 0.0
    rho_max_id = None
    for n in nodes:
        sum_rho += n["rho"]
        if n["rho"] > max_rho:
            max_rho = n["rho"]
            rho_max_id = n["id"]
    avg_rho = sum_rho / max(1, len(nodes))

    entropy = 0.0
    if sum_rho > 0:
        h = 0.0
        for n in nodes:
            p = n["rho"] / sum_rho
            if p > 0:
                h -= p * math.log(p)
        h_max = math.log(max(1, len(nodes)))
        entropy = h / h_max if h_max > 0 else 0.0

    max_flux_abs = 0.0
    total_flux = 0.0
    for e in edges:
        a = abs(e["flux"])
        total_flux += a
        max_flux_abs = max(max_flux_abs, a)

    active_count = sum(1 for n in nodes if n["rho"] > 0.1)

    return {
        "entropy": entropy,
        "totalFlux": total_flux,
        "maxFluxAbs": max_flux_abs,
        "mass": sum_rho,
        "avgRho": avg_rho,
        "maxRho": max_rho,
        "rhoMaxId": rho_max_id,
        "activeCount": active_count,
        "vortNorm_global": physics.vort_norm_global,
        "vortNorm_global_ema": physics.vort_norm_global_ema,
    }


# ---- Snapshot / Restore ------------------------------------------------

def snapshot_state(physics: SOLPhysics) -> dict:
    node_snap = {}
    for n in physics.nodes:
        snap_dict = {
            "rho": n["rho"], "p": n["p"], "psi": n["psi"],
            "psi_bias": n["psi_bias"],
            "semanticMass": n.get("semanticMass", 1.0),
            "semanticMass0": n.get("semanticMass0", 1.0),
            "b_q": n.get("b_q"), "b_charge": n.get("b_charge"),
            "b_state": n.get("b_state"),
            "z_gate": n.get("z_gate", 1.0),
            "r_gate": n.get("r_gate", 1.0),
            "z_bias": n.get("z_bias", 0.0),
            "r_bias": n.get("r_bias", 0.0),
        }
        for k in ["W_z", "U_z", "b_z", "W_r", "U_r", "b_r"]:
            if k in n:
                snap_dict[k] = n[k]
        node_snap[str(n["id"])] = snap_dict
    edge_flux = [e.get("flux", 0.0) for e in physics.edges]
    return {"nodeSnap": node_snap, "edgeFlux": edge_flux}


def restore_state(physics: SOLPhysics, snap: dict, cap_law: dict | None = None):
    if not snap:
        return
    for n in physics.nodes:
        s = snap["nodeSnap"].get(str(n["id"]))
        if not s:
            continue
        n["rho"] = s["rho"]
        n["p"] = s["p"]
        n["psi"] = s["psi"]
        n["psi_bias"] = s["psi_bias"]
        n["semanticMass"] = s["semanticMass"]
        n["semanticMass0"] = s["semanticMass0"]
        n["z_gate"] = s.get("z_gate", 1.0)
        n["r_gate"] = s.get("r_gate", 1.0)
        n["z_bias"] = s.get("z_bias", 0.0)
        n["r_bias"] = s.get("r_bias", 0.0)
        for k in ["W_z", "U_z", "b_z", "W_r", "U_r", "b_r"]:
            if k in s:
                n[k] = s[k]
            else:
                n.pop(k, None)
        if n.get("isBattery"):
            n["b_q"] = s.get("b_q")
            n["b_charge"] = s.get("b_charge")
            n["b_state"] = s.get("b_state")
    for i, e in enumerate(physics.edges):
        if i < len(snap["edgeFlux"]):
            e["flux"] = snap["edgeFlux"][i]
    if cap_law and cap_law.get("enabled"):
        with contextlib.suppress(Exception):
            apply_cap_law(physics, cap_law)


# ---- Edge Computation --------------------------------------------------

def compute_all_edges(raw_nodes: list[dict], raw_edges: list[dict],
                      use_all_to_all: bool = False, bg_w0: float = 0.14) -> list[dict]:
    def edge_w0(e):
        if isinstance(e.get("w0"), (int, float)):
            return e["w0"]
        if e.get("kind") == "tax":
            return 0.70
        return 1.0

    if not use_all_to_all:
        return [{**e, "w0": edge_w0(e), "background": False} for e in raw_edges]

    strong = [{**e, "w0": edge_w0(e), "background": False} for e in raw_edges]

    def edge_key(a, b) -> str:
        return f"{min(a, b)}-{max(a, b)}"

    existing = {edge_key(e["from"], e["to"]) for e in strong}
    ids = [n["id"] for n in raw_nodes]
    background = []
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            k = edge_key(ids[i], ids[j])
            if k in existing:
                continue
            background.append({"from": ids[i], "to": ids[j], "w0": bg_w0, "background": True})
    return strong + background


# ---- Factory -----------------------------------------------------------

def create_engine(raw_nodes: list[dict], raw_edges: list[dict], *,
                  cap_law: dict | None = None,
                  use_all_to_all: bool = False,
                  bg_w0: float = 0.14,
                  rng_seed: int = 42) -> tuple[SOLPhysics, dict | None]:
    all_edges = compute_all_edges(raw_nodes, raw_edges, use_all_to_all, bg_w0)
    physics = SOLPhysics(raw_nodes, all_edges)
    physics.seed_rng(rng_seed)

    cap_law_info = None
    if cap_law and cap_law.get("enabled"):
        cap_law_info = apply_cap_law(physics, cap_law)
    return physics, cap_law_info


# ---- Metrics & Telemetry Setup -----------------------------------------

_meter = None
_entropy_gauge = None
_flux_counter = None
_mass_gauge = None
_active_count_gauge = None

def _get_metrics():
    global _meter, _entropy_gauge, _flux_counter, _mass_gauge, _active_count_gauge
    if _meter is None:
        import telemetry
        _meter = telemetry.get_meter("sol-engine")
        _entropy_gauge = _meter.create_gauge("sol.engine.entropy", unit="1", description="Entropy of semantic manifold density distribution")
        _flux_counter = _meter.create_counter("sol.engine.flux_total", unit="1", description="Cumulative sum of absolute fluxes along edges")
        _mass_gauge = _meter.create_gauge("sol.engine.mass", unit="1", description="Total mass/density in the system")
        _active_count_gauge = _meter.create_gauge("sol.engine.active_count", unit="1", description="Number of nodes with density > 0.1")
    return _entropy_gauge, _flux_counter, _mass_gauge, _active_count_gauge


# ---- High-Level Convenience Wrapper ------------------------------------

class SOLEngine:
    """
    High-level wrapper that makes it easy for agents to run simulations.

    Example::

        engine = SOLEngine.from_default_graph()
        engine.inject("grail", 50)
        for _ in range(100):
            result = engine.step()
        metrics = engine.compute_metrics()
    """

    def __init__(self, physics: SOLPhysics, *,
                 dt: float = 0.12, c_press: float = 0.1, damping: float = 0.2,
                 cap_law: dict | None = None):
        self.physics = physics
        self.dt = dt
        self.c_press = c_press
        self.damping = damping
        self.cap_law = cap_law
        self._step_count = 0
        self._baseline: dict | None = None
        self.backend = "dict"

    def set_backend(self, backend: str):
        if backend not in ("dict", "vectorized"):
            raise ValueError(f"Invalid backend: {backend}. Must be 'dict' or 'vectorized'.")
        self.backend = backend

    def step_vectorized(self, dt=None, c_press=None, damping=None) -> dict:
        from sol_engine_backend_adapter import step_vectorized_impl
        result = step_vectorized_impl(self, dt, c_press, damping)
        self._step_count += 1
        return result


    @classmethod
    def from_default_graph(cls, *, dt=0.12, c_press=0.1, damping=0.2,
                           cap_law=None, rng_seed=42, graph_path=None) -> SOLEngine:
        path = Path(graph_path) if graph_path else DEFAULT_GRAPH_PATH
        with open(path, "r") as f:
            data = json.load(f)
        physics, _ = create_engine(
            data["rawNodes"], data["rawEdges"],
            cap_law=cap_law, rng_seed=rng_seed,
        )
        return cls(physics, dt=dt, c_press=c_press, damping=damping, cap_law=cap_law)

    @classmethod
    def from_graph(cls, raw_nodes, raw_edges, **kwargs) -> SOLEngine:
        physics, _ = create_engine(raw_nodes, raw_edges,
                                   cap_law=kwargs.get("cap_law"),
                                   rng_seed=kwargs.get("rng_seed", 42))
        return cls(physics, dt=kwargs.get("dt", 0.12),
                   c_press=kwargs.get("c_press", 0.1),
                   damping=kwargs.get("damping", 0.2),
                   cap_law=kwargs.get("cap_law"))

    def step(self, dt=None, c_press=None, damping=None) -> dict:
        if getattr(self, "backend", "dict") == "vectorized":
            return self.step_vectorized(dt, c_press, damping)
        import telemetry
        if not telemetry._TELEMETRY_ENABLED:
            result = self.physics.step(
                dt or self.dt,
                c_press if c_press is not None else self.c_press,
                damping if damping is not None else self.damping,
            )
            self._step_count += 1
            return result

        with telemetry.trace_span("sol.engine.step") as span:
            result = self.physics.step(
                dt or self.dt,
                c_press if c_press is not None else self.c_press,
                damping if damping is not None else self.damping,
            )
            self._step_count += 1

            # Compute current metrics
            metrics = self.compute_metrics()

            # Record metrics
            with contextlib.suppress(Exception):
                entropy_gauge, flux_counter, mass_gauge, active_count_gauge = _get_metrics()
                entropy_gauge.set(metrics.get("entropy", 0.0))
                flux_counter.add(result.get("totalFlux", 0.0))
                mass_gauge.set(metrics.get("mass", 0.0))
                active_count_gauge.set(result.get("activeCount", 0))

            # Set span attributes
            span.set_attribute("sol.step_count", self._step_count)
            span.set_attribute("sol.t", self.t)
            span.set_attribute("sol.metrics.entropy", metrics.get("entropy", 0.0))
            span.set_attribute("sol.metrics.total_flux", result.get("totalFlux", 0.0))
            span.set_attribute("sol.metrics.mass", metrics.get("mass", 0.0))
            span.set_attribute("sol.metrics.active_count", result.get("activeCount", 0))

            # Serialise and append compact graph state snapshot for the live visualizer
            with contextlib.suppress(Exception):
                node_states = self.get_node_states()
                edge_states = [
                    {"from": e["from"], "to": e["to"], "flux": e.get("flux", 0.0), "conductance": e.get("conductance", 1.0)}
                    for e in self.physics.edges if abs(e.get("flux", 0.0)) > 1e-4 or not e.get("background")
                ]
                span.set_attribute("sol.graph.nodes", json.dumps(node_states))
                span.set_attribute("sol.graph.edges", json.dumps(edge_states))

            return result

    def run_steps(
        self,
        steps: int,
        *,
        dt=None,
        c_press=None,
        damping=None,
        pre_step_node: dict | None = None,
        pre_step_rho: float = 500.0,
        pre_step_psi: float = 0.0,
    ) -> dict:
        """Execute ``steps`` consecutive simulation steps, returning the final step metrics."""
        if steps <= 0:
            return {
                "totalFlux": 0.0,
                "activeCount": sum(1 for n in self.physics.nodes if n["rho"] > 0.1),
            }
        dt_val = dt or self.dt
        c_press_val = c_press if c_press is not None else self.c_press
        damping_val = damping if damping is not None else self.damping
        import telemetry

        if (
            getattr(self, "backend", "dict") != "vectorized"
            and not telemetry._TELEMETRY_ENABLED
            and self.physics.integration_mode == "rk4"
        ):
            result = self.physics.run_rk4_steps(
                steps,
                dt_val,
                c_press_val,
                damping_val,
                pre_step_node=pre_step_node,
                pre_step_rho=pre_step_rho,
                pre_step_psi=pre_step_psi,
            )
            self._step_count += steps
            return result

        last_res = {"totalFlux": 0.0, "activeCount": 0}
        for _ in range(steps):
            if pre_step_node is not None:
                pre_step_node["rho"] = pre_step_rho
                pre_step_node["psi"] = pre_step_psi
            last_res = self.step(dt_val, c_press_val, damping_val)
        return last_res

    def run(self, steps: int, *, dt=None, c_press=None, damping=None) -> list[dict]:
        """Run multiple steps, return list of per-step results."""
        results = []
        for _ in range(steps):
            results.append(self.step(dt, c_press, damping))
        return results

    def run_until_halt(self, max_steps: int, flux_threshold: float = 1e-3, *,
                       dt=None, c_press=None, damping=None) -> dict:
        """
        Runs simulation steps until total flux falls below flux_threshold,
        indicating that self-routing logic has halted the thought loop.
        
        Returns a dict with:
          - "steps_run": number of steps executed
          - "halted": True if it halted before max_steps, False otherwise
          - "final_flux": total flux at the last step
        """
        dt_val = dt or self.dt
        c_press_val = c_press if c_press is not None else self.c_press
        damping_val = damping if damping is not None else self.damping
        
        flux = 0.0
        for step_idx in range(1, max_steps + 1):
            res = self.step(dt_val, c_press_val, damping_val)
            flux = res.get("totalFlux", 0.0)
            if flux < flux_threshold:
                return {
                    "steps_run": step_idx,
                    "halted": True,
                    "final_flux": flux
                }
        return {
            "steps_run": max_steps,
            "halted": False,
            "final_flux": flux
        }

    def inject(self, label: str, amount: float = 50.0) -> bool:
        import telemetry
        with telemetry.trace_span("sol.engine.inject", {"sol.inject.label": label, "sol.inject.amount": amount}) as span:
            success = self.physics.inject(label, amount)
            span.set_attribute("sol.inject.success", success)
            return success

    def inject_by_id(self, node_id, amount: float = 50.0) -> bool:
        import telemetry
        with telemetry.trace_span("sol.engine.inject_by_id", {"sol.inject.node_id": node_id, "sol.inject.amount": amount}) as span:
            success = self.physics.inject_by_id(node_id, amount)
            span.set_attribute("sol.inject.success", success)
            return success

    def compute_metrics(self) -> dict:
        return compute_metrics(self.physics)

    def save_baseline(self) -> dict:
        self._baseline = snapshot_state(self.physics)
        return self._baseline

    def restore_baseline(self, snap=None):
        restore_state(self.physics, snap or self._baseline, self.cap_law)

    def get_node_states(self) -> list[dict]:
        """Return a compact summary of all node states."""
        return [
            {"id": n["id"], "label": n["label"], "group": n.get("group", ""),
             "rho": n["rho"], "p": n["p"], "psi": n["psi"]}
            for n in self.physics.nodes
        ]

    @property
    def t(self) -> float:
        return self.physics._t

    @property
    def step_count(self) -> int:
        return self._step_count

    @property
    def integration_mode(self) -> str:
        return self.physics.integration_mode

    @integration_mode.setter
    def integration_mode(self, val: str):
        self.physics.integration_mode = val

    @property
    def gated_recurrent_cfg(self) -> dict:
        return self.physics.gated_recurrent_cfg

    @gated_recurrent_cfg.setter
    def gated_recurrent_cfg(self, val: dict):
        self.physics.gated_recurrent_cfg = val

    def _find_node(self, label_or_id) -> dict | None:
        if label_or_id in self.physics.node_by_id:
            return self.physics.node_by_id[label_or_id]
        q = str(label_or_id).strip().lower()
        if not q:
            return None
        for n in self.physics.nodes:
            if n["label"].lower() == q:
                return n
        if len(q) >= 2:
            matches = [n for n in self.physics.nodes if q in n["label"].lower()]
            if len(matches) == 1:
                return matches[0]
        return None

    def write_enable(self, label_or_id) -> bool:
        node = self._find_node(label_or_id)
        if not node:
            return False
        node["z_bias"] = 10.0
        node["r_bias"] = 0.0
        return True

    def write_lock(self, label_or_id) -> bool:
        node = self._find_node(label_or_id)
        if not node:
            return False
        node["z_bias"] = -20.0
        node["r_bias"] = -20.0
        return True

    def read_enable(self, label_or_id) -> bool:
        node = self._find_node(label_or_id)
        if not node:
            return False
        node["z_bias"] = 0.0
        node["r_bias"] = 10.0
        return True
