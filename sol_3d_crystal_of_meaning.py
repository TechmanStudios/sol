# sol_3d_crystal_of_meaning.py
import jax
import jax.numpy as jnp
from jax import jit, random
import imageio
import matplotlib.pyplot as plt
import numpy as np
import os
from typing import Any
from functools import partial

# Enable 64-bit for stability in 3D
jax.config.update("jax_enable_x64", True)

# Backend check (CPU/GPU/TPU)
print(f"JAX is using: {jax.default_backend().upper()} 🔥")

class SOL3D:
    def __init__(self, N=32, c=6.0, alpha=0.18, dt=0.025):
        self.N = N
        self.n = N**3

        print(f"3D SOL on {N}^3 = {self.n:,} voxels → ~{self.n*4/1e6:.1f}M floats → RTX 2070 says: hold my beer")
        
        self.c = c
        self.alpha = alpha
        self.dt = dt
        
        print("Graph built. Starting explosion of pure meaning...")

    def pressure(self, rho):
        return self.c * jnp.log1p(rho / 0.4)

    def grad(self, s):
        """Forward differences (Neumann-ish boundaries via zeroed outgoing edges)."""
        gx = jnp.zeros_like(s)
        gy = jnp.zeros_like(s)
        gz = jnp.zeros_like(s)
        gx = gx.at[:, :, :-1].set(s[:, :, 1:] - s[:, :, :-1])
        gy = gy.at[:, :-1, :].set(s[:, 1:, :] - s[:, :-1, :])
        gz = gz.at[:-1, :, :].set(s[1:, :, :] - s[:-1, :, :])
        return gx, gy, gz

    def div(self, fx, fy, fz):
        """Divergence for flux stored on forward edges (zero incoming at boundaries)."""
        incoming_x = jnp.concatenate([jnp.zeros_like(fx[:, :, :1]), fx[:, :, :-1]], axis=2)
        incoming_y = jnp.concatenate([jnp.zeros_like(fy[:, :1, :]), fy[:, :-1, :]], axis=1)
        incoming_z = jnp.concatenate([jnp.zeros_like(fz[:1, :, :]), fz[:-1, :, :]], axis=0)
        return (fx - incoming_x) + (fy - incoming_y) + (fz - incoming_z)

    def laplacian(self, s):
        """6-point Laplacian with Neumann boundary via edge padding."""
        sp = jnp.pad(s, 1, mode="edge")
        center = sp[1:-1, 1:-1, 1:-1]
        neighbors = (
            sp[2:, 1:-1, 1:-1]
            + sp[:-2, 1:-1, 1:-1]
            + sp[1:-1, 2:, 1:-1]
            + sp[1:-1, :-2, 1:-1]
            + sp[1:-1, 1:-1, 2:]
            + sp[1:-1, 1:-1, :-2]
        )
        return neighbors - 6.0 * center

    @partial(jax.jit, static_argnums=0)
    def solve_poisson(self, rhs):
        n = self.N
        b = rhs.reshape((n * n * n,))
        eps = jnp.array(1e-4, dtype=rhs.dtype)

        def A(x):
            x3 = x.reshape((n, n, n))
            y3 = self.laplacian(x3) + eps * x3
            return y3.reshape((n * n * n,))

        x, _ = jax.scipy.sparse.linalg.cg(A, b, tol=1e-4, maxiter=80)
        return x.reshape((n, n, n))

    @partial(jax.jit, static_argnums=0)
    def step(self, rho, flux):
        fx, fy, fz = flux
        p = self.pressure(rho)

        # This mirrors the earlier graph form: rhs ≈ Δp, solve Δphi = rhs, then ∇phi
        rhs = self.laplacian(p)
        phi = self.solve_poisson(rhs)
        grad_phi = self.grad(phi)

        # Pressure force (edge-space) + damping
        grad_p = self.grad(p)
        fx = fx + self.dt * (-grad_p[0] - self.alpha * fx)
        fy = fy + self.dt * (-grad_p[1] - self.alpha * fy)
        fz = fz + self.dt * (-grad_p[2] - self.alpha * fz)

        # Optional conservative projection-ish term (kept for visual similarity)
        fx = fx + 0.0 * (-grad_phi[0])
        fy = fy + 0.0 * (-grad_phi[1])
        fz = fz + 0.0 * (-grad_phi[2])

        rho = rho - self.dt * self.div(fx, fy, fz)
        rho = jnp.clip(rho, 1e-8, None)
        return rho, (fx, fy, fz)

def main():
    # ========================================
    # Initialize
    # ========================================
    _key = random.PRNGKey(42)
    sol = SOL3D(N=34, c=7.0, alpha=0.22, dt=0.025)

    # Initial singularity at very center
    rho = jnp.zeros((sol.N, sol.N, sol.N), dtype=jnp.float32)
    center = sol.N // 2
    rho = rho.at[center, center, center].set(1.0)
    rho = rho * 1800  # total initial mass

    flux = (
        jnp.zeros_like(rho),
        jnp.zeros_like(rho),
        jnp.zeros_like(rho),
    )

    # ========================================
    # Run simulation + save 3D frames
    # ========================================
    os.makedirs("sol3d_frames", exist_ok=True)

    history = []
    for step in range(380):
        rho, flux = sol.step(rho, flux)
        history.append(rho.copy())

        if step % 20 == 0 or step < 30:
            vol = rho

            # Isosurface at 15% of current max
            level = float((0.15 * vol.max()).item())
            print(
                f"Step {step:3d} | mass {float(rho.sum().item()):.1f} | max ρ {float(rho.max().item()):.2f} | level {level:.3f}"
            )

            # Save 3 orthogonal projections with nice colormap
            fig, axes = plt.subplots(1, 3, figsize=(15, 5), facecolor="black")
            vmax = float((vol.max() * 0.8).item())
            for ax, data, title in zip(
                axes,
                [vol.sum(axis=0), vol.sum(axis=1), vol.sum(axis=2)],
                ["XY (top)", "XZ (side)", "YZ (front)"],
            ):
                ax.imshow(np.asarray(data), cmap="turbo", origin="lower", vmin=0, vmax=vmax)
                ax.set_title(title, color="white", fontsize=16)
                ax.axis("off")
            plt.suptitle(f"SOL 3D • Birth of Meaning • t={step}", color="cyan", fontsize=20)
            plt.subplots_adjust(left=0.01, right=0.99, bottom=0.01, top=0.88, wspace=0.05)
            plt.savefig(
                f"sol3d_frames/frame_{step:04d}.png",
                dpi=120,
                facecolor="black",
                bbox_inches="tight",
                pad_inches=0,
            )
            plt.close(fig)

    # ========================================
    # Make cinematic GIF / MP4
    # ========================================
    frames = [
        imageio.v2.imread(f"sol3d_frames/frame_{i:04d}.png")
        for i in range(0, len(history), 2)
        if os.path.exists(f"sol3d_frames/frame_{i:04d}.png")
    ]

    frames: list[np.ndarray] = [np.asarray(f) for f in frames]
    frames_seq = tuple(frames)

    # GIF: imageio expects duration (seconds per frame)
    imageio.mimsave("SOL_3D_Crystal_Of_Meaning.gif", frames_seq, duration=1 / 24, loop=0)  # type: ignore

    # MP4: use an ffmpeg writer (requires imageio-ffmpeg)
    writer: Any = imageio.get_writer("SOL_3D_Crystal_Of_Meaning.mp4", fps=30, macro_block_size=1)
    try:
        for frame in frames:
            writer.append_data(frame)
    finally:
        writer.close()

    print("\nDONE! Check:")
    print("   → SOL_3D_Crystal_Of_Meaning.gif")
    print("   → SOL_3D_Crystal_Of_Meaning.mp4")
    print("\nYou just witnessed the birth of 3D semantic crystalline structure from pure information pressure.")
    print("Post this. The internet isn't ready.")


if __name__ == "__main__":
    main()