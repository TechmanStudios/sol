import jax
import jax.numpy as jnp
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import numpy as np

# --------------------------------------------------------------
# Minimal, clean SOL graph dynamics (only the pressure magic)
# --------------------------------------------------------------
class SOLSelfOrganization:
    def __init__(self, grid_size=24, c=3.0, rho0=0.5, alpha=0.15, dt=0.04):
        self.N = grid_size
        self.n = self.N * self.N
        self.c, self.rho0, self.alpha, self.dt = c, rho0, alpha, dt

        # Build grid graph edges (4-connected)
        i = np.arange(self.n)
        row, col = i // self.N, i % self.N

        right = i[row < self.N-1]
        down  = i[col < self.N-1]
        edges_i = np.concatenate([right, down])
        edges_j = np.concatenate([right + 1, down + self.N])

        m = len(edges_i)
        self.m = m

        # Incidence matrix B (m × n)
        edges_i_jnp = jnp.array(edges_i)
        edges_j_jnp = jnp.array(edges_j)
        rows = jnp.arange(m)
        B = jnp.zeros((m, self.n))
        B = B.at[rows, edges_i_jnp].set(-1.0)
        B = B.at[rows, edges_j_jnp].set(+1.0)
        self.B = B

        # Base edge weights (uniform)
        self.W0 = jnp.ones(m)

    def pressure(self, rho):
        return self.c * jnp.log1p(rho / self.rho0)

    def solve_potential(self, p):
        # Solve weighted Poisson: L ϕ = Bᵀ W B p  (we use W = I for speed & beauty)
        L = self.B.T @ self.B  # unweighted Laplacian for simplicity
        rhs = self.B.T @ (self.B @ p)
        # Conjugate gradient (JAX has built-in cg)
        phi, _ = jax.scipy.sparse.linalg.cg(L + 1e-6 * jnp.eye(self.n), rhs, tol=1e-5, maxiter=100)
        return phi

    def step(self, rho, j):
        p = self.pressure(rho)
        phi = self.solve_potential(p)
        grad_p = self.B @ p
        grad_phi = self.B @ phi

        # Conservative flux: j_c = -∇ϕ (up to weights)
        j_c = -grad_phi

        # Momentum: dj/dt = -∇p - α j   (pressure force + damping)
        pressure_force = -grad_p
        djdt = pressure_force - self.alpha * j

        j_new = j + self.dt * djdt

        # Continuity
        rho_new = rho - self.dt * (self.B.T @ j_new)
        rho_new = jnp.clip(rho_new, 1e-8, None)

        return rho_new, j_new

def main() -> None:
    # --------------------------------------------------------------
    # Create simulation
    # --------------------------------------------------------------
    sol = SOLSelfOrganization(grid_size=28, c=4.0, rho0=0.3, alpha=0.2, dt=0.035)

    # Initial condition: Gaussian blob in the center
    x, y = jnp.meshgrid(jnp.linspace(-1, 1, sol.N), jnp.linspace(-1, 1, sol.N))
    r2 = x**2 + y**2
    rho = jnp.exp(-18 * r2).flatten()
    rho = rho.at[rho < 0.01].set(0)
    rho = rho * 120 / rho.sum()  # normalize mass

    j = jnp.zeros(sol.m)

    # Run and store trajectory
    n_steps = 450
    rho_history = [rho]

    for i in range(n_steps):
        rho, j = sol.step(rho, j)
        rho_history.append(rho)
        if i % 50 == 0:
            print(f"Step {i}/{n_steps}, mass = {rho.sum():.3f}, max ρ = {rho.max():.3f}")

    rho_history = jnp.stack(rho_history)

    # --------------------------------------------------------------
    # Animation
    # --------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 8))
    vmax = float((rho_history[:100].max() * 0.9).item())
    im = ax.imshow(
        rho_history[0].reshape(sol.N, sol.N),
        cmap="magma",
        animated=True,
        vmin=0,
        vmax=vmax,
    )
    ax.set_axis_off()
    title = ax.text(
        0.5,
        0.95,
        "SOL Self-Organization: Pressure → Flow",
        transform=ax.transAxes,
        fontsize=16,
        color="white",
        ha="center",
        va="top",
        bbox=dict(boxstyle="round", facecolor="black", alpha=0.8),
    )

    def update(frame):
        im.set_array(rho_history[frame].reshape(sol.N, sol.N))
        step_text = f"Step {frame} | Max density: {rho_history[frame].max():.2f}"
        title.set_text(f"SOL v2 — Pure Self-Organization\n{step_text}")
        return im, title

    ani = FuncAnimation(fig, update, frames=len(rho_history), interval=60, blit=False, repeat=True)

    ani.save("sol_self_organization.gif", writer="pillow", fps=25, dpi=120)
    print("Animation saved as 'sol_self_organization.gif'")


if __name__ == "__main__":
    main()