"""Emergence check for SOL "pressure → divergence → flow" dynamics.

Goal
----
Fast checklist for whether the final pattern is stable ("same up to symmetry") vs a one-off:
- vary seed / initial noise
- vary (c, rho0, alpha, dt)
- measure similarity of final density pattern under rotation/reflection symmetries

This script runs two systems:
1) 2D grid graph (like sol_animation1.py, but using the 3D script's core dynamics)
2) 3D grid graph (like sol_graph_pressure_flow_3d.py)

Core dynamics (from solMath_v2.tex, graph discretization)
--------------------------------------------------------
- Pressure:        p = Π(ρ) = c log(1 + ρ/rho0)
- Edge momentum:   j̇ = -B p - α j
- Continuity:      ρ̇ + Bᵀ j = 0

Similarity metric
-----------------
We compare final ρ fields using max normalized correlation over symmetries:
- 2D: dihedral D4 (8 symmetries)
- 3D: axis permutations × axis flips (48 symmetries, includes reflections)

Outputs
-------
- emergence_check_results.csv
- (optional) emergence_check_summary.txt

Run
---
  G:/docs/TechmanStudios/sol/.venv/Scripts/python.exe sol_emergence_check.py
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations, product
from typing import Callable, Iterable, List, Tuple

import csv
import math

import numpy as np


@dataclass(frozen=True)
class GridGraph:
    grid_n: int
    edge_u: np.ndarray  # (m,)
    edge_v: np.ndarray  # (m,)


def build_grid_graph_2d(grid_n: int) -> GridGraph:
    grid_n = int(grid_n)
    assert grid_n >= 2

    # Node index: i = x + N*y  with x,y in [0,N)
    def idx(x: np.ndarray, y: np.ndarray) -> np.ndarray:
        return x + grid_n * y

    edges_u: List[np.ndarray] = []
    edges_v: List[np.ndarray] = []

    # +x edges
    x = np.arange(grid_n - 1)
    y = np.arange(grid_n)
    X, Y = np.meshgrid(x, y, indexing="ij")
    u = idx(X, Y).ravel()
    v = idx(X + 1, Y).ravel()
    edges_u.append(u)
    edges_v.append(v)

    # +y edges
    x = np.arange(grid_n)
    y = np.arange(grid_n - 1)
    X, Y = np.meshgrid(x, y, indexing="ij")
    u = idx(X, Y).ravel()
    v = idx(X, Y + 1).ravel()
    edges_u.append(u)
    edges_v.append(v)

    edge_u = np.concatenate(edges_u).astype(np.int64)
    edge_v = np.concatenate(edges_v).astype(np.int64)
    return GridGraph(grid_n=grid_n, edge_u=edge_u, edge_v=edge_v)


def build_grid_graph_3d(grid_n: int) -> GridGraph:
    grid_n = int(grid_n)
    assert grid_n >= 2

    # Node index: i = x + N*y + N^2*z with x,y,z in [0,N)
    def idx(x: np.ndarray, y: np.ndarray, z: np.ndarray) -> np.ndarray:
        return x + grid_n * y + (grid_n**2) * z

    edges_u: List[np.ndarray] = []
    edges_v: List[np.ndarray] = []

    # +x edges
    x = np.arange(grid_n - 1)
    y = np.arange(grid_n)
    z = np.arange(grid_n)
    X, Y, Z = np.meshgrid(x, y, z, indexing="ij")
    u = idx(X, Y, Z).ravel()
    v = idx(X + 1, Y, Z).ravel()
    edges_u.append(u)
    edges_v.append(v)

    # +y edges
    x = np.arange(grid_n)
    y = np.arange(grid_n - 1)
    z = np.arange(grid_n)
    X, Y, Z = np.meshgrid(x, y, z, indexing="ij")
    u = idx(X, Y, Z).ravel()
    v = idx(X, Y + 1, Z).ravel()
    edges_u.append(u)
    edges_v.append(v)

    # +z edges
    x = np.arange(grid_n)
    y = np.arange(grid_n)
    z = np.arange(grid_n - 1)
    X, Y, Z = np.meshgrid(x, y, z, indexing="ij")
    u = idx(X, Y, Z).ravel()
    v = idx(X, Y, Z + 1).ravel()
    edges_u.append(u)
    edges_v.append(v)

    edge_u = np.concatenate(edges_u).astype(np.int64)
    edge_v = np.concatenate(edges_v).astype(np.int64)
    return GridGraph(grid_n=grid_n, edge_u=edge_u, edge_v=edge_v)


def pressure_eos_log(rho: np.ndarray, c: float, rho0: float) -> np.ndarray:
    return float(c) * np.log1p(rho / float(rho0))


def grad_on_edges(values: np.ndarray, edge_u: np.ndarray, edge_v: np.ndarray) -> np.ndarray:
    return values[edge_v] - values[edge_u]


def div_on_nodes(edge_flux: np.ndarray, edge_u: np.ndarray, edge_v: np.ndarray, n: int) -> np.ndarray:
    div = np.zeros(n, dtype=np.float64)
    np.add.at(div, edge_u, -edge_flux)
    np.add.at(div, edge_v, +edge_flux)
    return div


def simulate_core(
    graph: GridGraph,
    dims: int,
    steps: int,
    dt: float,
    c: float,
    rho0: float,
    alpha: float,
    seed: int,
    init_noise: float,
    init_mass: float,
) -> np.ndarray:
    """Return final rho shaped (N,N) or (N,N,N) using the same indexing as graph build."""
    rng = np.random.default_rng(seed)
    n = graph.grid_n**dims
    m = graph.edge_u.shape[0]

    rho = np.zeros(n, dtype=np.float64)
    j = np.zeros(m, dtype=np.float64)

    # Center-hotspot + small noise
    if dims == 2:
        cx = cy = graph.grid_n // 2
        center = cx + graph.grid_n * cy
    elif dims == 3:
        cx = cy = cz = graph.grid_n // 2
        center = cx + graph.grid_n * cy + (graph.grid_n**2) * cz
    else:
        raise ValueError("dims must be 2 or 3")

    rho[center] = init_mass
    rho += float(init_noise) * rng.random(n)

    for _ in range(steps):
        p = pressure_eos_log(rho, c=c, rho0=rho0)
        grad_p = grad_on_edges(p, graph.edge_u, graph.edge_v)

        j = j + dt * (-grad_p - alpha * j)
        div = div_on_nodes(j, graph.edge_u, graph.edge_v, n=n)
        rho = rho - dt * div
        rho = np.clip(rho, 1e-12, None)

    if dims == 2:
        return rho.reshape((graph.grid_n, graph.grid_n))
    return rho.reshape((graph.grid_n, graph.grid_n, graph.grid_n))


def normalize_for_compare(a: np.ndarray) -> np.ndarray:
    x = np.asarray(a, dtype=np.float64).ravel()
    x = x - x.mean()
    s = x.std()
    if s < 1e-12:
        return x * 0.0
    return x / s


def corr(a: np.ndarray, b: np.ndarray) -> float:
    an = normalize_for_compare(a)
    bn = normalize_for_compare(b)
    return float(np.dot(an, bn) / max(1, an.size))


def radial_profile_2d(a: np.ndarray, bins: int | None = None) -> np.ndarray:
    """Radial mean of a 2D field about the grid center (rotation-invariant descriptor)."""
    n = a.shape[0]
    assert a.shape == (n, n)
    cx = cy = (n - 1) / 2.0
    xs, ys = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
    r = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2)
    rmax = float(r.max())
    nb = int(bins or max(8, int(math.ceil(rmax))))
    edges = np.linspace(0.0, rmax + 1e-9, nb + 1)
    out = np.zeros(nb, dtype=np.float64)
    for i in range(nb):
        m = (r >= edges[i]) & (r < edges[i + 1])
        out[i] = float(a[m].mean()) if np.any(m) else 0.0
    return out


def radial_profile_3d(a: np.ndarray, bins: int | None = None) -> np.ndarray:
    """Radial mean of a 3D field about the grid center (rotation-invariant descriptor)."""
    n = a.shape[0]
    assert a.shape == (n, n, n)
    c = (n - 1) / 2.0
    xs, ys, zs = np.meshgrid(np.arange(n), np.arange(n), np.arange(n), indexing="ij")
    r = np.sqrt((xs - c) ** 2 + (ys - c) ** 2 + (zs - c) ** 2)
    rmax = float(r.max())
    nb = int(bins or max(8, int(math.ceil(rmax))))
    edges = np.linspace(0.0, rmax + 1e-9, nb + 1)
    out = np.zeros(nb, dtype=np.float64)
    for i in range(nb):
        m = (r >= edges[i]) & (r < edges[i + 1])
        out[i] = float(a[m].mean()) if np.any(m) else 0.0
    return out


def quantile_mask(a: np.ndarray, q: float) -> np.ndarray:
    """Binary mask of the top-q mass (q in (0,1)), returned as float array."""
    thr = float(np.quantile(a, q))
    return (a >= thr).astype(np.float64)


def symmetries_2d(a: np.ndarray) -> Iterable[np.ndarray]:
    """Dihedral group D4 (8 symmetries)."""
    a0 = a
    a1 = np.rot90(a0, 1)
    a2 = np.rot90(a0, 2)
    a3 = np.rot90(a0, 3)
    b0 = np.fliplr(a0)
    b1 = np.rot90(b0, 1)
    b2 = np.rot90(b0, 2)
    b3 = np.rot90(b0, 3)
    yield a0
    yield a1
    yield a2
    yield a3
    yield b0
    yield b1
    yield b2
    yield b3


def symmetries_3d(a: np.ndarray) -> Iterable[np.ndarray]:
    """48 symmetries: axis permutations × axis flips (includes reflections)."""
    for perm_axes in permutations((0, 1, 2)):
        ap = np.transpose(a, axes=perm_axes)
        for flips in product((False, True), repeat=3):
            out = ap
            for axis, do_flip in enumerate(flips):
                if do_flip:
                    out = np.flip(out, axis=axis)
            yield out


def max_corr_up_to_symmetry(a: np.ndarray, b: np.ndarray, sym_fn: Callable[[np.ndarray], Iterable[np.ndarray]]) -> Tuple[float, int]:
    best = -1.0
    best_i = -1
    for i, bt in enumerate(sym_fn(b)):
        cval = corr(a, bt)
        if cval > best:
            best = cval
            best_i = i
    return best, best_i


def sample_params(rng: np.random.Generator) -> Tuple[float, float, float, float]:
    # Ranges chosen to keep dynamics stable for explicit Euler.
    c = float(rng.uniform(3.0, 8.0))
    rho0 = float(rng.uniform(0.20, 0.70))
    alpha = float(rng.uniform(0.05, 0.45))
    dt = float(rng.uniform(0.02, 0.08))
    return c, rho0, alpha, dt


def main() -> None:
    # Configuration (fast but informative)
    grid2 = 28
    grid3 = 5

    steps2 = 260
    steps3 = 140

    init_noise = 0.02
    init_mass2 = 120.0
    init_mass3 = 120.0

    base = dict(c=5.0, rho0=0.35, alpha=0.25, dt=0.05)

    g2 = build_grid_graph_2d(grid2)
    g3 = build_grid_graph_3d(grid3)

    # Baselines
    base2 = simulate_core(g2, dims=2, steps=steps2, seed=0, init_noise=init_noise, init_mass=init_mass2, **base)
    base3 = simulate_core(g3, dims=3, steps=steps3, seed=0, init_noise=init_noise, init_mass=init_mass3, **base)

    base2_log = np.log1p(base2)
    base3_log = np.log1p(base3)
    base2_mask = quantile_mask(base2, 0.80)
    base3_mask = quantile_mask(base3, 0.80)
    base2_rad = radial_profile_2d(base2)
    base3_rad = radial_profile_3d(base3)

    rng = np.random.default_rng(20251212)

    rows = []

    # 1) Seed/noise robustness at fixed params
    for seed in range(1, 8):
        fin2 = simulate_core(g2, dims=2, steps=steps2, seed=seed, init_noise=init_noise, init_mass=init_mass2, **base)
        fin3 = simulate_core(g3, dims=3, steps=steps3, seed=seed, init_noise=init_noise, init_mass=init_mass3, **base)

        c2, _ = max_corr_up_to_symmetry(base2, fin2, symmetries_2d)
        c3, _ = max_corr_up_to_symmetry(base3, fin3, symmetries_3d)

        c2_log, _ = max_corr_up_to_symmetry(base2_log, np.log1p(fin2), symmetries_2d)
        c3_log, _ = max_corr_up_to_symmetry(base3_log, np.log1p(fin3), symmetries_3d)

        c2_mask, _ = max_corr_up_to_symmetry(base2_mask, quantile_mask(fin2, 0.80), symmetries_2d)
        c3_mask, _ = max_corr_up_to_symmetry(base3_mask, quantile_mask(fin3, 0.80), symmetries_3d)

        c2_rad = corr(base2_rad, radial_profile_2d(fin2, bins=base2_rad.size))
        c3_rad = corr(base3_rad, radial_profile_3d(fin3, bins=base3_rad.size))

        rows.append(
            {
                "kind": "seed",
                "seed": seed,
                "c": base["c"],
                "rho0": base["rho0"],
                "alpha": base["alpha"],
                "dt": base["dt"],
                "corr2d": c2,
                "corr3d": c3,
                "corr2d_log": c2_log,
                "corr3d_log": c3_log,
                "corr2d_mask80": c2_mask,
                "corr3d_mask80": c3_mask,
                "corr2d_radial": c2_rad,
                "corr3d_radial": c3_rad,
            }
        )

    # 2) Parameter robustness (random samples)
    for i in range(14):
        c, rho0, alpha, dt = sample_params(rng)
        fin2 = simulate_core(
            g2,
            dims=2,
            steps=steps2,
            dt=dt,
            c=c,
            rho0=rho0,
            alpha=alpha,
            seed=int(rng.integers(0, 1_000_000)),
            init_noise=init_noise,
            init_mass=init_mass2,
        )
        fin3 = simulate_core(
            g3,
            dims=3,
            steps=steps3,
            dt=dt,
            c=c,
            rho0=rho0,
            alpha=alpha,
            seed=int(rng.integers(0, 1_000_000)),
            init_noise=init_noise,
            init_mass=init_mass3,
        )

        c2, _ = max_corr_up_to_symmetry(base2, fin2, symmetries_2d)
        c3, _ = max_corr_up_to_symmetry(base3, fin3, symmetries_3d)

        c2_log, _ = max_corr_up_to_symmetry(base2_log, np.log1p(fin2), symmetries_2d)
        c3_log, _ = max_corr_up_to_symmetry(base3_log, np.log1p(fin3), symmetries_3d)

        c2_mask, _ = max_corr_up_to_symmetry(base2_mask, quantile_mask(fin2, 0.80), symmetries_2d)
        c3_mask, _ = max_corr_up_to_symmetry(base3_mask, quantile_mask(fin3, 0.80), symmetries_3d)

        c2_rad = corr(base2_rad, radial_profile_2d(fin2, bins=base2_rad.size))
        c3_rad = corr(base3_rad, radial_profile_3d(fin3, bins=base3_rad.size))

        rows.append(
            {
                "kind": "param",
                "seed": "",
                "c": c,
                "rho0": rho0,
                "alpha": alpha,
                "dt": dt,
                "corr2d": c2,
                "corr3d": c3,
                "corr2d_log": c2_log,
                "corr3d_log": c3_log,
                "corr2d_mask80": c2_mask,
                "corr3d_mask80": c3_mask,
                "corr2d_radial": c2_rad,
                "corr3d_radial": c3_rad,
            }
        )

    # Write CSV
    out_csv = "emergence_check_results.csv"
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # Quick summary
    seed_rows = [r for r in rows if r["kind"] == "seed"]
    param_rows = [r for r in rows if r["kind"] == "param"]

    def stats(vals: List[float]) -> Tuple[float, float, float]:
        return float(np.min(vals)), float(np.median(vals)), float(np.max(vals))

    s2 = stats([r["corr2d"] for r in seed_rows])
    s3 = stats([r["corr3d"] for r in seed_rows])
    s2l = stats([r["corr2d_log"] for r in seed_rows])
    s3l = stats([r["corr3d_log"] for r in seed_rows])
    s2m = stats([r["corr2d_mask80"] for r in seed_rows])
    s3m = stats([r["corr3d_mask80"] for r in seed_rows])
    s2r = stats([r["corr2d_radial"] for r in seed_rows])
    s3r = stats([r["corr3d_radial"] for r in seed_rows])

    p2 = stats([r["corr2d"] for r in param_rows])
    p3 = stats([r["corr3d"] for r in param_rows])
    p2l = stats([r["corr2d_log"] for r in param_rows])
    p3l = stats([r["corr3d_log"] for r in param_rows])
    p2m = stats([r["corr2d_mask80"] for r in param_rows])
    p3m = stats([r["corr3d_mask80"] for r in param_rows])
    p2r = stats([r["corr2d_radial"] for r in param_rows])
    p3r = stats([r["corr3d_radial"] for r in param_rows])

    summary = (
        "Emergence check (max correlation up to symmetry)\n"
        "------------------------------------------------\n"
        f"Baseline params: c={base['c']}, rho0={base['rho0']}, alpha={base['alpha']}, dt={base['dt']}\n\n"
        f"Seed sweep (2D) raw:     {s2[0]:.3f} / {s2[1]:.3f} / {s2[2]:.3f}\n"
        f"Seed sweep (2D) log1p:   {s2l[0]:.3f} / {s2l[1]:.3f} / {s2l[2]:.3f}\n"
        f"Seed sweep (2D) mask80:  {s2m[0]:.3f} / {s2m[1]:.3f} / {s2m[2]:.3f}\n"
        f"Seed sweep (2D) radial:  {s2r[0]:.3f} / {s2r[1]:.3f} / {s2r[2]:.3f}\n\n"
        f"Seed sweep (3D) raw:     {s3[0]:.3f} / {s3[1]:.3f} / {s3[2]:.3f}\n"
        f"Seed sweep (3D) log1p:   {s3l[0]:.3f} / {s3l[1]:.3f} / {s3l[2]:.3f}\n"
        f"Seed sweep (3D) mask80:  {s3m[0]:.3f} / {s3m[1]:.3f} / {s3m[2]:.3f}\n"
        f"Seed sweep (3D) radial:  {s3r[0]:.3f} / {s3r[1]:.3f} / {s3r[2]:.3f}\n\n"
        f"Param sweep (2D) raw:    {p2[0]:.3f} / {p2[1]:.3f} / {p2[2]:.3f}\n"
        f"Param sweep (2D) log1p:  {p2l[0]:.3f} / {p2l[1]:.3f} / {p2l[2]:.3f}\n"
        f"Param sweep (2D) mask80: {p2m[0]:.3f} / {p2m[1]:.3f} / {p2m[2]:.3f}\n"
        f"Param sweep (2D) radial: {p2r[0]:.3f} / {p2r[1]:.3f} / {p2r[2]:.3f}\n\n"
        f"Param sweep (3D) raw:    {p3[0]:.3f} / {p3[1]:.3f} / {p3[2]:.3f}\n"
        f"Param sweep (3D) log1p:  {p3l[0]:.3f} / {p3l[1]:.3f} / {p3l[2]:.3f}\n"
        f"Param sweep (3D) mask80: {p3m[0]:.3f} / {p3m[1]:.3f} / {p3m[2]:.3f}\n"
        f"Param sweep (3D) radial: {p3r[0]:.3f} / {p3r[1]:.3f} / {p3r[2]:.3f}\n\n"
        f"Wrote: {out_csv}\n"
    )

    out_txt = "emergence_check_summary.txt"
    with open(out_txt, "w", encoding="utf-8") as f:
        f.write(summary)

    print(summary)

    # Interpretive rule-of-thumb (not a proof, but fast signal)
    # corr ~ 1.0  => essentially same pattern (after symmetry)
    # corr ~ 0.0  => unrelated
    # corr < 0.5  => weak stability / likely parameter-regime change


if __name__ == "__main__":
    main()
