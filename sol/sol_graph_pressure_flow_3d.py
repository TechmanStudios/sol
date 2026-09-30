"""SOL graph dynamics (3D animation): pressure → divergence → flow.

Implements the core discrete SOL equations from solMath_v2.tex:
- Pressure (equation of state): p = Π(ρ)
- Pressure-driven edge flux (momentum-lite): j̇ = -B p - α j
- Continuity: ρ̇ + Bᵀ j = 0

Visualization (3D):
- Nodes are placed on a 3D grid.
- Node size ~ pressure p.
- Node color ~ divergence (Bᵀ j): red = outflow, blue = inflow.
- A subset of highest-magnitude edge fluxes are drawn as arrows.

Outputs:
- sol_pressure_divergence_flow_3d.gif
- sol_pressure_divergence_flow_3d.mp4 (if ffmpeg writer is available)

Run:
  python sol_graph_pressure_flow_3d.py
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import numpy as np


@dataclass(frozen=True)
class Graph3D:
    positions: np.ndarray  # (n, 3)
    edge_u: np.ndarray  # (m,) tail indices (oriented)
    edge_v: np.ndarray  # (m,) head indices (oriented)


def build_3d_grid_graph(grid_n: int) -> Graph3D:
    """3D 6-neighbor lattice on a grid_n×grid_n×grid_n grid."""
    grid_n = int(grid_n)
    assert grid_n >= 2

    # Node indexing: i = x + grid_n*y + grid_n^2*z
    xs, ys, zs = np.meshgrid(
        np.arange(grid_n),
        np.arange(grid_n),
        np.arange(grid_n),
        indexing="ij",
    )

    # Center at origin and normalize to [-1, 1]
    pos = np.stack([xs, ys, zs], axis=-1).reshape(-1, 3).astype(np.float64)
    pos = pos - (grid_n - 1) / 2.0
    if grid_n > 1:
        pos = pos / ((grid_n - 1) / 2.0)

    def idx(x: np.ndarray, y: np.ndarray, z: np.ndarray) -> np.ndarray:
        return x + grid_n * y + (grid_n**2) * z

    # Oriented edges: +x, +y, +z
    edges_u: list[np.ndarray] = []
    edges_v: list[np.ndarray] = []

    # +x edges (x -> x+1)
    x = np.arange(grid_n - 1)
    y = np.arange(grid_n)
    z = np.arange(grid_n)
    X, Y, Z = np.meshgrid(x, y, z, indexing="ij")
    u = idx(X, Y, Z).ravel()
    v = idx(X + 1, Y, Z).ravel()
    edges_u.append(u)
    edges_v.append(v)

    # +y edges (y -> y+1)
    x = np.arange(grid_n)
    y = np.arange(grid_n - 1)
    z = np.arange(grid_n)
    X, Y, Z = np.meshgrid(x, y, z, indexing="ij")
    u = idx(X, Y, Z).ravel()
    v = idx(X, Y + 1, Z).ravel()
    edges_u.append(u)
    edges_v.append(v)

    # +z edges (z -> z+1)
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
    return Graph3D(positions=pos, edge_u=edge_u, edge_v=edge_v)


def pressure_eos_log(rho: np.ndarray, c: float = 4.0, rho0: float = 0.3) -> np.ndarray:
    """Π(ρ) = c log(1 + ρ/ρ0), monotone and stable (as in solMath_v2.tex)."""
    rho = np.asarray(rho)
    return float(c) * np.log1p(rho / float(rho0))


def grad_on_edges(values: np.ndarray, edge_u: np.ndarray, edge_v: np.ndarray) -> np.ndarray:
    """Graph gradient B*values on oriented edges: (value[v] - value[u])."""
    return values[edge_v] - values[edge_u]


def div_on_nodes(edge_flux: np.ndarray, edge_u: np.ndarray, edge_v: np.ndarray, n: int) -> np.ndarray:
    """Graph divergence Bᵀ j on nodes.

    For an oriented edge e=(u->v), contribution is:
      div[u] += -j[e]
      div[v] += +j[e]
    """
    div = np.zeros(n, dtype=np.float64)
    np.add.at(div, edge_u, -edge_flux)
    np.add.at(div, edge_v, +edge_flux)
    return div


def simulate(
    graph: Graph3D,
    steps: int,
    dt: float,
    c: float,
    rho0: float,
    alpha: float,
    seed: int = 7,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Returns (rho_hist, p_hist, div_hist)."""
    rng = np.random.default_rng(seed)

    n = graph.positions.shape[0]
    m = graph.edge_u.shape[0]

    rho = np.zeros(n, dtype=np.float64)
    j = np.zeros(m, dtype=np.float64)

    # Initial condition: a dense hotspot at the center + tiny background
    center = int(np.argmin(np.sum(graph.positions**2, axis=1)))
    rho[center] = 120.0
    rho += 0.02 * rng.random(n)

    rho_hist = np.zeros((steps, n), dtype=np.float64)
    p_hist = np.zeros((steps, n), dtype=np.float64)
    div_hist = np.zeros((steps, n), dtype=np.float64)

    for t in range(steps):
        p = pressure_eos_log(rho, c=c, rho0=rho0)
        grad_p = grad_on_edges(p, graph.edge_u, graph.edge_v)

        # Edge-momentum (pressure force + damping): j̇ = -B p - α j
        j = j + dt * (-grad_p - alpha * j)

        # Continuity: ρ̇ + Bᵀ j = 0  =>  ρ <- ρ - dt * (Bᵀ j)
        div = div_on_nodes(j, graph.edge_u, graph.edge_v, n=n)
        rho = rho - dt * div
        rho = np.clip(rho, 1e-10, None)

        rho_hist[t] = rho
        p_hist[t] = p
        div_hist[t] = div

    return rho_hist, p_hist, div_hist


def main() -> None:
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation

    try:
        import imageio
    except Exception as exc:  # pragma: no cover
        raise SystemExit(
            "Missing dependency 'imageio'. Install it (pip install imageio imageio-ffmpeg)."
        ) from exc

    # Keep defaults intentionally small so rendering completes quickly on CPU.
    graph = build_3d_grid_graph(grid_n=5)  # 5^3 = 125 nodes

    steps = 140
    dt = 0.05
    c = 5.0
    rho0 = 0.35
    alpha = 0.25

    rho_hist, p_hist, div_hist = simulate(
        graph,
        steps=steps,
        dt=dt,
        c=c,
        rho0=rho0,
        alpha=alpha,
        seed=7,
    )

    # Normalize for visuals
    p95_div = float(np.percentile(np.abs(div_hist), 95))
    p95_div = max(p95_div, 1e-9)

    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection="3d")
    fig.patch.set_facecolor("black")
    ax.set_facecolor("black")

    pos = graph.positions

    def draw_frame(frame: int):
        ax.cla()

        rho = rho_hist[frame]
        p = p_hist[frame]
        div = div_hist[frame]

        # Node size from pressure (keeps “pressure” explicitly visible)
        p_scaled = (p - p.min())
        if p_scaled.max() > 0:
            p_scaled = p_scaled / p_scaled.max()
        sizes = 10 + 120 * (p_scaled**1.2)

        # Node color from divergence: red = outflow, blue = inflow
        divn = np.clip(div / p95_div, -1.0, 1.0)
        cmap = plt.get_cmap("seismic")
        colors = cmap((divn + 1.0) / 2.0)

        ax.scatter(  # type: ignore[arg-type]
            pos[:, 0],
            pos[:, 1],
            pos[:, 2],  # type: ignore[arg-type]
            s=sizes,
            c=colors,
            depthshade=True,
            linewidths=0,
            alpha=0.95,
        )

        # Edge arrows: show only strongest flows
        # Compute edge flux implied by j in the last update:
        # We can reconstruct j approximately by using the continuity div and previous rho,
        # but we also stored only div; for animation we recompute a representative flux field:
        # Use current pressure gradient as “instantaneous” flow proxy.
        grad_p = grad_on_edges(p, graph.edge_u, graph.edge_v)
        j_proxy = -grad_p

        k = 70  # arrows to draw (keep small for fast 3D renders)
        idx = np.argpartition(np.abs(j_proxy), -k)[-k:]

        u = graph.edge_u[idx]
        v = graph.edge_v[idx]
        jv = j_proxy[idx]

        tail = np.where(jv >= 0, u, v)
        head = np.where(jv >= 0, v, u)

        start = pos[tail]
        direction = pos[head] - pos[tail]

        mag = np.abs(jv)
        if mag.max() > 0:
            mag = mag / mag.max()
        # Scale arrows by magnitude; keep arrows short so the graph stays readable
        vec = direction * (0.45 * mag[:, None])

        ax.quiver(
            start[:, 0],
            start[:, 1],
            start[:, 2],
            vec[:, 0],
            vec[:, 1],
            vec[:, 2],
            color="white",
            linewidth=0.6,
            alpha=0.65,
            arrow_length_ratio=0.25,
        )

        ax.set_title(
            "SOL Graph Dynamics (3D) — Pressure → Divergence → Flow\n"
            f"step={frame:03d} | mass={rho.sum():.1f} | max ρ={rho.max():.2f} | max p={p.max():.2f}",
            color="white",
            pad=14,
        )

        ax.set_xlim(-1.2, 1.2)
        ax.set_ylim(-1.2, 1.2)
        ax.set_zlim(-1.2, 1.2)
        ax.set_xticks([])  # type: ignore[misc]
        ax.set_yticks([])  # type: ignore[misc]
        ax.set_zticks([])  # type: ignore[misc]

        # Subtle rotation for 3D legibility
        ax.view_init(elev=18, azim=35 + 0.35 * frame)

        return ()

    ani = FuncAnimation(fig, draw_frame, frames=steps, interval=60, blit=False)

    gif_path = "sol_pressure_divergence_flow_3d.gif"
    mp4_path = "sol_pressure_divergence_flow_3d.mp4"

    print(f"Rendering GIF → {gif_path}")
    ani.save(gif_path, writer="pillow", fps=18, dpi=90)

    # MP4 is optional; if ffmpeg isn't available, we just skip.
    try:
        print(f"Rendering MP4 → {mp4_path}")
        ani.save(mp4_path, writer="ffmpeg", fps=24, dpi=110)
    except Exception as exc:  # pragma: no cover
        print("MP4 render skipped (ffmpeg not available or misconfigured):", exc)

    plt.close(fig)
    print("Done.")


if __name__ == "__main__":
    main()
