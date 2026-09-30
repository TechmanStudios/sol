# sol_animation.py
import jax
import jax.numpy as jnp
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

class SOLDemo:
    def __init__(self, N=28):
        self.N = N
        self.n = N * N
        
        # Grid coordinates
        idx = jnp.arange(self.n)
        row = idx // N
        col = idx % N
        
        # 4-connected edges
        right = idx[row < N-1]
        down  = idx[col < N-1]
        ei = jnp.concatenate([right, down])
        ej = jnp.concatenate([right+1, down+N])
        
        m = len(ei)
        self.m = m
        
        # Incidence matrix B (m×n)
        rows = jnp.arange(m)
        B = jnp.zeros((m, self.n))
        B = B.at[rows, ei].set(-1)
        B = B.at[rows, ej].set(+1)
        self.B = B
        
        self.c = 4.0      # pressure strength
        self.alpha = 0.2  # damping
        self.dt = 0.035

    def pressure(self, rho):
        return self.c * jnp.log1p(rho / 0.3)

    def solve_poisson(self, rhs):
        L = self.B.T @ self.B  # graph Laplacian
        phi, _ = jax.scipy.sparse.linalg.cg(L + 1e-6*jnp.eye(self.n), rhs)
        return phi

    def step(self, rho, flux):
        p = self.pressure(rho)
        grad_p = self.B @ p
        phi = self.solve_poisson(self.B.T @ grad_p)
        grad_phi = self.B @ phi
        
        # momentum update
        force = -grad_p
        flux = flux + self.dt * (force - self.alpha * flux)
        
        # continuity
        rho = rho - self.dt * (self.B.T @ flux)
        rho = jnp.clip(rho, 1e-8, None)
        return rho, flux

# ========================================
# Run simulation
# ========================================
demo = SOLDemo(N=28)

# Initial Gaussian blob
x = jnp.linspace(-1, 1, demo.N)
X, Y = jnp.meshgrid(x, x)
rho = jnp.exp(-20 * (X**2 + Y**2)).flatten()
rho = rho * 140 / rho.sum()

flux = jnp.zeros(demo.m)
history = [rho]

for i in range(450):
    rho, flux = demo.step(rho, flux)
    history.append(rho)
    if i % 50 == 0:
        print(f"step {i} | mass {rho.sum():.2f} | max ρ {rho.max():.3f}")

history = jnp.stack(history)

# ========================================
# Animation
# ========================================
fig, ax = plt.subplots(figsize=(8,8))
vmax = float(history[:120].max().item())
im = ax.imshow(history[0].reshape(demo.N, demo.N), cmap='magma', vmin=0, vmax=vmax)
ax.set_axis_off()
plt.tight_layout()

def update(frame):
    im.set_array(history[frame].reshape(demo.N, demo.N))
    ax.set_title(f"SOL Self-Organization • step {frame} • max density {history[frame].max():.2f}", 
                 color='white', fontsize=14, pad=20,
                 bbox=dict(facecolor='black', alpha=0.8))
    return im,

ani = FuncAnimation(fig, update, frames=len(history), interval=70, repeat=True)
ani.save("sol_birth_of_meaning.gif", writer='pillow', fps=25, dpi=130)
print("Saved sol_birth_of_meaning.gif – open it!")