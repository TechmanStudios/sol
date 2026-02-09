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

import json
import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

__all__ = [
    "SOLEngine",
    "SOLPhysics",
    "apply_cap_law",
    "get_cap_law_signature",
    "compute_metrics",
    "snapshot_state",
    "restore_state",
    "compute_all_edges",
    "create_engine",
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

    def seed_rng(self, seed: int):
        self._rng = _Rng(seed)

    # ---- Semantic Mass Decay ----
    def apply_semantic_mass_decay(self, dt: float):
        cfg = self.semantic_cfg
        if not cfg:
            return
        decay = cfg.get("decayRate", 0.05)
        min_mass = cfg.get("minMass", 0.25)
        axiom = cfg.get("singularityMass", 1000)
        factor = math.exp(-decay * max(0.0, dt))
        for n in self.nodes:
            if not n.get("isConstellation"):
                continue
            if n.get("isSingularity"):
                continue
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

    # ---- Equation of State: P = c * log(1 + rho/m) ----
    def compute_pressure(self, c_press: float):
        for n in self.nodes:
            m = n.get("semanticMass", 1.0)
            if not (isinstance(m, (int, float)) and math.isfinite(m) and m > 0):
                m = 1.0
            n["p"] = c_press * math.log(1 + (n["rho"] / m))

    # ---- Psi (Belief Field) Diffusion ----
    def update_psi(self, dt: float):
        lap = [0.0] * len(self.nodes)
        for e in self.edges:
            ia = self.node_index_by_id.get(e["from"])
            ib = self.node_index_by_id.get(e["to"])
            if ia is None or ib is None:
                continue
            d = self.nodes[ib]["psi"] - self.nodes[ia]["psi"]
            lap[ia] += d
            lap[ib] -= d

        for idx, n in enumerate(self.nodes):
            if n.get("isBattery"):
                s = n.get("b_state", 1)
                if s not in (1, -1):
                    s = 1
                n["b_state"] = s
                n["psi_bias"] = float(s)
                n["psi"] = float(s)
                continue
            rho_norm = n["rho"] / (n["rho"] + 40)
            relax_to_bias = (self.psi_relax_base * (0.35 + 0.65 * rho_norm)) * (n["psi_bias"] - n["psi"])
            relax_to_global = self.psi_global_nudge * (self.global_bias - n["psi"])
            diffusion = self.psi_diffusion * lap[idx]
            n["psi"] += dt * (diffusion + relax_to_bias + relax_to_global)
            n["psi"] = _clamp(n["psi"], -self.psi_clamp, self.psi_clamp)

    # ---- Battery (Lighthouse) Logic ----
    def update_batteries(self, dt: float):
        cfg = self.battery_cfg
        if not cfg:
            return
        for b in self.nodes:
            if not b.get("isBattery"):
                continue
            if b.get("b_state") not in (1, -1):
                b["b_state"] = -1
            if not isinstance(b.get("b_charge"), (int, float)) or not math.isfinite(b["b_charge"]):
                b["b_charge"] = 0.0

            incoming = 0.0
            drag_val = 0.0
            for e in self.edges:
                if e.get("background"):
                    continue
                if e["from"] != b["id"] and e["to"] != b["id"]:
                    continue
                nb_id = e["to"] if e["from"] == b["id"] else e["from"]
                nb = self.node_by_id.get(nb_id)
                if not nb:
                    continue
                w = e.get("conductance", 1.0)
                if nb.get("isBattery"):
                    nb_state = nb.get("b_state", 1)
                    if nb_state not in (1, -1):
                        nb_state = 1
                else:
                    nb_state = 1 if (nb.get("psi", 0) >= 0) else -1
                if nb_state == 1:
                    incoming += w * cfg.get("resonanceDrive", 1.5)
                else:
                    drag_val += w * cfg.get("dampingDrag", 0.5)

            net_flux = incoming - drag_val
            charge_delta = math.tanh(net_flux) * dt

            if b["b_state"] == 1:
                leakage = b["b_charge"] * (cfg.get("leakLambda", 0.05) * 0.2)
            else:
                leakage = b["b_charge"] * cfg.get("leakLambda", 0.05)

            b["b_charge"] = _clamp(b["b_charge"] + charge_delta - leakage, 0, 1)

            tau = cfg.get("flipThreshold", 0.85)
            collapse_thresh = tau * cfg.get("collapseFactor", 0.3)

            if b["b_state"] == -1 and b["b_charge"] > tau:
                pulse_mass = cfg.get("qMax", 40) * b["b_charge"] * cfg.get("avalancheGain", 1.15)
                connected = [e for e in self.edges if not e.get("background") and (e["from"] == b["id"] or e["to"] == b["id"])]
                share = pulse_mass / max(1, len(connected))
                for e in connected:
                    nb_id = e["to"] if e["from"] == b["id"] else e["from"]
                    nb = self.node_by_id.get(nb_id)
                    if nb:
                        nb["rho"] += share
                b["b_state"] = 1
                b["b_charge"] = 1.0
                b["psi"] = 1.0
            elif b["b_state"] == 1 and b["b_charge"] < collapse_thresh:
                b["b_state"] = -1
                b["psi"] = -1.0

            b["psi"] = float(b["b_state"])
            b["psi_bias"] = float(b["b_state"])

    # ---- Edge Conductance (psi-shaped) ----
    def update_conductance(self):
        for e in self.edges:
            src = self.node_by_id.get(e["from"])
            dst = self.node_by_id.get(e["to"])
            if not src or not dst:
                continue
            avg_psi = (src["psi"] + dst["psi"]) / 2
            w = (e["w0"] * self.conductance_base) * math.exp(self.conductance_gamma * avg_psi)

            if self.mhd_cfg:
                b_gamma = self.mhd_cfg.get("bGamma", 0.35)
                b_mag = e.get("bMag", 0.0)
                if isinstance(b_mag, (int, float)) and math.isfinite(b_mag):
                    w *= (1 + b_gamma * b_mag)

            b_node = src if src.get("isBattery") else (dst if dst.get("isBattery") else None)
            if b_node and self.battery_cfg:
                s = b_node.get("b_state", 1)
                if s not in (1, -1):
                    s = 1
                if s == 1:
                    w *= self.battery_cfg.get("resonanceBoost", 1.8)
                else:
                    w *= self.battery_cfg.get("dampingClamp", 0.35)
                    tight_max = max(self.conductance_min, min(self.conductance_max, 0.6))
                    e["conductance"] = _clamp(w, self.conductance_min, tight_max)
                    continue

            e["conductance"] = _clamp(w, self.conductance_min, self.conductance_max)

    # ---- MHD (Magnetic Frozen-In Field) ----
    def update_magnetic_field(self, dt: float):
        cfg = self.mhd_cfg
        if not cfg:
            return
        build = cfg.get("bBuild", 0.10)
        decay = cfg.get("bDecay", 0.06)
        b_max = cfg.get("bMax", 4.0)
        for e in self.edges:
            if e.get("background"):
                continue
            b_prev = e.get("bMag", 0.0)
            if not isinstance(b_prev, (int, float)) or not math.isfinite(b_prev):
                b_prev = 0.0
            flux_abs = abs(e.get("flux", 0.0))
            b_next = (b_prev * math.exp(-decay * max(0.0, dt))) + (build * flux_abs * max(0.0, dt))
            e["bMag"] = _clamp(b_next, 0, b_max)

    # ---- Jeans Collapse and Accretion ----
    def jeans_collapse_and_accrete(self, dt: float, c_press: float, damping: float):
        cfg = self.jeans_cfg
        if not cfg:
            return
        j_crit = cfg.get("Jcrit", 18.0)
        acc_rate = cfg.get("accreteRate", 0.55)
        to_mass = cfg.get("accreteToMass", 0.04)

        for star in self.nodes:
            eps = 1e-6
            p = star.get("p", c_press * math.log(1 + star["rho"]))
            if not isinstance(p, (int, float)) or not math.isfinite(p):
                p = c_press * math.log(1 + star["rho"])
            j_val = star["rho"] / (abs(p) + eps)

            if not star.get("isConstellation") and j_val >= j_crit:
                star["isConstellation"] = True
                star["protoStar"] = True
            if j_val >= j_crit:
                star["isStellar"] = True

            if not star.get("isStellar"):
                continue

            accreted = 0.0
            for e in self.edges:
                if e.get("background") or e.get("kind") != "tax":
                    continue
                other_id = None
                if e["from"] == star["id"]:
                    other_id = e["to"]
                elif e["to"] == star["id"]:
                    other_id = e["from"]
                if other_id is None:
                    continue
                nb = self.node_by_id.get(other_id)
                if not nb or nb.get("isBattery"):
                    continue
                pull = min(nb["rho"], nb["rho"] * acc_rate * max(0.0, dt))
                if pull <= 0:
                    continue
                nb["rho"] -= pull
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
    def step(self, dt: float, c_press: float, damping: float) -> dict:
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

        # --- C. PHASE-GATED FLUX TRANSPORT ---
        total_flux = 0.0
        d_rho = [0.0] * len(self.nodes)

        for e in self.edges:
            ia = self.node_index_by_id.get(e["from"])
            ib = self.node_index_by_id.get(e["to"])
            if ia is None or ib is None:
                continue

            src = self.nodes[ia]
            dst = self.nodes[ib]

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

            delta_p = src["p"] - dst["p"]

            tension = 1.0
            if src_group == "tech" or dst_group == "tech":
                tension = self.phase_cfg["surfaceTension"]
            if src_group == "spirit" or dst_group == "spirit":
                tension = self.phase_cfg["deepViscosity"]

            diode_gain = 1.0
            if self.battery_cfg and (src.get("isBattery") or dst.get("isBattery")) and not e.get("background"):
                b_node = src if src.get("isBattery") else dst
                b_s = b_node.get("b_state", 1)
                if b_s not in (1, -1):
                    b_s = 1
                batt_is_src = src.get("isBattery")
                outflow = (delta_p > 0) if batt_is_src else (delta_p < 0)
                if b_s == 1:
                    diode_gain = self.battery_cfg["diodeResonanceOut"] if outflow else self.battery_cfg["diodeResonanceIn"]
                else:
                    diode_gain = self.battery_cfg["diodeDampingOut"] if outflow else self.battery_cfg["diodeDampingIn"]

            target_flux = (e["conductance"] * tension * diode_gain) * delta_p
            e["flux"] = e["flux"] * (1 - dt) + target_flux * dt
            total_flux += abs(e["flux"])

            flow_amt = e["flux"] * dt * 0.5
            if src_awake:
                d_rho[ia] -= flow_amt
            if dst_awake:
                d_rho[ib] += flow_amt

        # Apply mass changes
        for idx, n in enumerate(self.nodes):
            n["rho"] += d_rho[idx]
            star_factor = 1.0
            if n.get("isStellar") and self.jeans_cfg:
                star_factor = self.jeans_cfg.get("starDampingFactor", 0.18)
            n["rho"] *= (1.0 - (damping * dt * 0.1 * star_factor))
            if n["rho"] < 0:
                n["rho"] = 0.0

        # MHD + gravity coupling
        self.update_magnetic_field(dt)
        self.compute_pressure(c_press)
        self.jeans_collapse_and_accrete(dt, c_press, damping)

        active_count = sum(1 for n in self.nodes if n["rho"] > 0.1)
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
                if not best:
                    best = other
                elif other.get("semanticMass", 1) > best.get("semanticMass", 1):
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
    lam = cap_law.get("lambda", 0.0)
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

    proxy_mode = str(cap_law.get("proxy", "degree")).lower()
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
        if a > max_flux_abs:
            max_flux_abs = a

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
        node_snap[str(n["id"])] = {
            "rho": n["rho"], "p": n["p"], "psi": n["psi"],
            "psi_bias": n["psi_bias"],
            "semanticMass": n.get("semanticMass", 1.0),
            "semanticMass0": n.get("semanticMass0", 1.0),
            "b_q": n.get("b_q"), "b_charge": n.get("b_charge"),
            "b_state": n.get("b_state"),
        }
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
        if n.get("isBattery"):
            n["b_q"] = s.get("b_q")
            n["b_charge"] = s.get("b_charge")
            n["b_state"] = s.get("b_state")
    for i, e in enumerate(physics.edges):
        if i < len(snap["edgeFlux"]):
            e["flux"] = snap["edgeFlux"][i]
    if cap_law and cap_law.get("enabled"):
        try:
            apply_cap_law(physics, cap_law)
        except Exception:
            pass


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
    edge_key = lambda a, b: f"{min(a,b)}-{max(a,b)}"
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

    @classmethod
    def from_default_graph(cls, *, dt=0.12, c_press=0.1, damping=0.2,
                           cap_law=None, rng_seed=42, graph_path=None) -> "SOLEngine":
        path = Path(graph_path) if graph_path else DEFAULT_GRAPH_PATH
        with open(path, "r") as f:
            data = json.load(f)
        physics, cap_info = create_engine(
            data["rawNodes"], data["rawEdges"],
            cap_law=cap_law, rng_seed=rng_seed,
        )
        return cls(physics, dt=dt, c_press=c_press, damping=damping, cap_law=cap_law)

    @classmethod
    def from_graph(cls, raw_nodes, raw_edges, **kwargs) -> "SOLEngine":
        physics, _ = create_engine(raw_nodes, raw_edges,
                                   cap_law=kwargs.get("cap_law"),
                                   rng_seed=kwargs.get("rng_seed", 42))
        return cls(physics, dt=kwargs.get("dt", 0.12),
                   c_press=kwargs.get("c_press", 0.1),
                   damping=kwargs.get("damping", 0.2),
                   cap_law=kwargs.get("cap_law"))

    def step(self, dt=None, c_press=None, damping=None) -> dict:
        result = self.physics.step(
            dt or self.dt,
            c_press if c_press is not None else self.c_press,
            damping if damping is not None else self.damping,
        )
        self._step_count += 1
        return result

    def run(self, steps: int, *, dt=None, c_press=None, damping=None) -> list[dict]:
        """Run multiple steps, return list of per-step results."""
        results = []
        for _ in range(steps):
            results.append(self.step(dt, c_press, damping))
        return results

    def inject(self, label: str, amount: float = 50.0) -> bool:
        return self.physics.inject(label, amount)

    def inject_by_id(self, node_id, amount: float = 50.0) -> bool:
        return self.physics.inject_by_id(node_id, amount)

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
