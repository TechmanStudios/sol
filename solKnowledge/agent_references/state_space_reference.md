# SOL Engine: State Space Reference Manual
**Document Version:** 1.1  
**Audience:** AI Agents, System Architects, and Human Operators  

---

## 1. Core Paradigm: Semantic Manifold as a Coupled Dynamical System

The SOL Engine (Self-Organizing Logos) represents a concept graph not as a static network of nodes and edges, but as a continuous, stateful, and coupled physical manifold. 

Concepts (nodes) carry thermodynamic state variables such as mass density $\rho$, pressure $p$, and belief orientation $\psi$. These variables evolve over time under a set of integration equations governed by discrete time intervals ($dt$), damping coefficients ($\kappa$), and phase gates. Edges between concepts act as channels with variable conductance $g$, facilitating the flow of meaning (mass flux $j$) driven by pressure differentials.

```
                  [ Node A: ρ_A, p_A, ψ_A ]
                             │
                             │ (Flux j_AB across Edge conductance g_AB)
                             ▼
                  [ Node B: ρ_B, p_B, ψ_B ]
```

---

## 2. Node State Variables & Equations

Every node $i$ in the manifold possesses the following state variables:

### 2.1. Density / Mass ($\rho$)
* **Definition:** Represents the quantity of semantic energy, attention, or activation strength accumulated by a node.
* **Governing Dynamics:**
  $$\rho_i(t + dt) = \left( \rho_i(t) + \Delta \rho_{flux} \right) \cdot \left( 1 - \kappa \cdot dt \cdot 0.1 \cdot \text{star\_factor} \right)$$
  Where:
  * $\Delta \rho_{flux}$ is the net mass accumulated from incoming/outgoing edge fluxes.
  * $\kappa$ is the global damping/decay coefficient (loss term).
  * $\text{star\_factor}$ is a local multiplier that decreases damping for nodes that have undergone Jeans gravitational collapse (default: $0.18$).
* **Bounds:** $\rho_i \ge 0.0$. Mass is strictly non-negative. Underflow values are clamped to $0.0$ to prevent "ghost layers" ($< 10^{-16}$).

### 2.2. Pressure ($p$)
* **Definition:** The spatial gradient driver of mass flow. High density builds up pressure, which pushes mass outwards to connected nodes with lower pressure.
* **Equation of State:**
  $$p_i = c_{press} \cdot \ln\left(1 + \frac{\rho_i}{SM_i}\right)$$
  Where:
  * $c_{press}$ is the global pressure scaling constant.
  * $SM_i$ is the node's `semanticMass` (capacitance/well).
* **Significance:** The logarithmic form prevents infinite pressure spikes, modeling a saturating cognitive pressure curve.

### 2.3. Belief Field ($\psi$)
* **Definition:** A directional bias term representing semantic polarity or phase angle (e.g., Tech vs. Spirit, Affirmative vs. Skeptic). It acts as a routing controller by gating edge conductance.
* **Governing Dynamics:**
  $$\psi_i(t + dt) = \psi_i(t) + dt \cdot \left( \text{diffusion} + \text{relaxation\_to\_bias} + \text{relaxation\_to\_global} \right)$$
  * **Diffusion (Laplacian):** $\psi_{\text{diff}} = D_{\psi} \cdot \sum_{j \in \text{neighbors}} (\psi_j - \psi_i)$ where $D_{\psi}$ is the diffusion constant (default: $0.6$).
  * **Relaxation to Bias:** $R_{\text{bias}} = \left(\psi_{\text{relax\_base}} \cdot \left(0.35 + 0.65 \cdot \frac{\rho_i}{\rho_i + 40}\right)\right) \cdot \left(\psi_{bias, i} - \psi_i\right)$. The rate of relaxation to the native bias increases as density $\rho_i$ accumulates.
  * **Relaxation to Global:** $R_{\text{global}} = \psi_{\text{global\_nudge}} \cdot \left(\psi_{\text{global\_bias}} - \psi_i\right)$.
* **Bounds:** Clamped strictly to $[-1.0, 1.0]$.
* **Native Bias ($\psi_{bias}$):**
  * Tech Nodes: $\psi_{bias} = -1.0$ (drives surface phase routing)
  * Spirit Nodes: $\psi_{bias} = +1.0$ (drives deep phase routing)
  * Bridge/Neutral Nodes: $\psi_{bias} = 0.0$

### 2.4. Semantic Mass ($SM$) & The Capacitance Law (CAP-Law)
* **Definition:** Serves as the localized capacitance or "well depth" of a node. High $SM$ lowers pressure response for a given density $\rho$, effectively trapping mass and acting as a retention reservoir (memory).
* **Capacitance Law (CAP-Law):**
  In the canonical degree-power configuration, $SM$ is dynamically scaled relative to the node's connectivity (degree $d_i$) to balance retention across hubs and spokes:
  $$SM_i = \text{clip}\left( k \cdot d_i^{\alpha}, SM_{min}, SM_{max} \right)$$
  Where:
  * $k$ is the scaling multiplier: $k = k_0 \cdot \left(\frac{dt}{dt_0}\right)^{\gamma}$ (where $dt_0 = 0.12$ is the baseline timestep, and $\gamma$ is the time-step compensation exponent).
  * $k_0$ is anchored such that a reference node (e.g., node 89) matches a reference well depth ($SM_{ref}$), preserving pressure proportionality.
  * $\alpha$ is the power-law exponent (proven stable range: $0.75 - 0.85$, default: $0.8$).
  * Clamps prevent numerical instability: $SM_{min} = 0.25$, $SM_{max} = 5000$.
* **Decay and Reinforcement:**
  For dynamic constellation nodes, $SM$ decays exponentially when inactive:
  $$SM_i(t + dt) = \max\left( SM_{min}, SM_i(t) \cdot e^{-\lambda_{SM} \cdot dt} \right)$$
  And reinforces during active injections:
  $$SM_i \leftarrow SM_i + \text{reinforce\_scale} \cdot \text{inject\_boost} \cdot (1 + \text{tension})$$
  * **Singularity Limit:** If $SM_i > 1000$ (e.g., via extreme accumulation), the node collapses into a permanent `isSingularity` state, freezing flow.

---

## 3. Edge State Variables & Equations

Edges connect nodes and manage the transmission of semantic mass.

### 3.1. Base Weight ($w_0$)
* Represents structural topological strength. Background edges (minor cohesions) have low default weights (e.g., $0.14$), whereas taxon (strong taxonomic) edges have high defaults (e.g., $0.70$).

### 3.2. Conductance ($g$)
* **Definition:** The dynamically variable throughput capacity of the edge.
* **Equation:**
  $$g_{ij} = \text{clip}\left( (w_0 \cdot g_{base}) \cdot e^{\gamma_{cond} \cdot \psi_{avg}}, g_{min}, g_{max} \right)$$
  Where:
  * $\psi_{avg} = \frac{\psi_i + \psi_j}{2}$ is the average belief orientation across the edge.
  * $\gamma_{cond}$ is the conductance sensitivity exponent (default: $0.75$).
  * $g_{min} = 0.1$, $g_{max} = 3.0$.
* **Modulators:** 
  * Magnetohydrodynamic (MHD) frozen-in fields: $g_{ij}$ is scaled up by $(1 + \beta_{MHD} \cdot B_{ij})$.
  * Battery Resonance: Edges incident to active battery nodes are boosted by a factor of $1.8$ if the battery is active ($b\_state = 1$) or clamped to a tight max (e.g., $0.6$) if inactive.

### 3.3. Flux ($j$)
* **Definition:** The rate of mass flow passing through the edge.
* **Dynamic Momentum Equation:**
  $$j_{ij}(t + dt) = j_{ij}(t) \cdot (1 - dt) + j_{target} \cdot dt$$
  Where target flux is driven by the pressure differential:
  $$j_{target} = (g_{ij} \cdot \text{tension} \cdot \text{diode\_gain}) \cdot (p_i - p_j)$$
* **Mass Transport Execution:**
  $$\Delta \rho = j_{ij} \cdot dt \cdot 0.5$$
  This mass is deducted from the source node and added to the destination node.

### 3.4. Magnetic Field ($B$ or `bMag`)
* **Definition:** A metric of topological memory. High flux "freezes" a magnetic field into the edge, increasing future conductance (memristive behavior).
* **Dynamics:**
  $$B_{ij}(t + dt) = B_{ij}(t) \cdot e^{-bDecay \cdot dt} + bBuild \cdot |j_{ij}| \cdot dt$$
  Clamped to $[0, bMax]$ (default: $[0, 4.0]$).

---

## 4. Special Manifold Objects

### 4.1. Batteries / Lighthouses (Hysteresis Latches)
Special accumulator nodes designed to store charge and fire semantic impulses when full.
* **State Variables:**
  * Polarity State ($b\_state \in \{1, -1\}$): Sets $\psi = \psi_{bias} = b\_state$.
  * Charge ($b\_charge \in [0.0, 1.0]$): Accumulates based on resonance of neighboring nodes:
    $$\Delta \text{charge} = \tanh\left( \text{resonance\_drive} \cdot \sum w \cdot \text{awake\_neighbors} - \text{damping\_drag} \cdot \sum w \cdot \text{skeptic\_neighbors} \right) \cdot dt$$
  * Leakage: $b\_charge \leftarrow b\_charge - b\_charge \cdot \lambda_{leak} \cdot dt$ (leak rate is $5\times$ slower when state is $+1$).
* **Hysteresis Thresholds:**
  * **Avalanche Firing:** When $b\_state = -1$ and $b\_charge > \tau_{flip}$ ($0.85$):
    * Fuses an avalanche of mass: $\rho_{pulse} = qMax \cdot b\_charge \cdot 1.15$.
    * Distributes $\rho_{pulse}$ equally among all non-background neighbors.
    * Flips state: $b\_state \leftarrow 1$, $b\_charge \leftarrow 1.0$.
  * **Collapse Reset:** When $b\_state = 1$ and $b\_charge < \tau_{collapse}$ ($\tau_{flip} \cdot 0.3 = 0.255$):
    * Resets state: $b\_state \leftarrow -1$.

### 4.2. Stars (Jeans Gravitational Collapse)
Simulates concept condensation when local semantic density exceeds pressure limits.
* **Criterion:** A node collapses into a star if the local Jeans ratio exceeds a critical threshold:
  $$J = \frac{\rho_i}{|p_i| + 10^{-6}} \ge J_{crit} \quad (\text{default: } 18.0)$$
* **Accretion Behavior:** A stellar node pulls mass from its taxonomical neighbors:
  $$\Delta \rho_{\text{pull}} = \min\left(\rho_{neighbor}, \rho_{neighbor} \cdot \text{accrete\_rate} \cdot dt\right)$$
  And grows its well depth proportionately:
  $$SM_i \leftarrow SM_i + \Delta \rho_{\text{pull}} \cdot 0.04$$
* **Damping Shield:** The node's effective damping decay is reduced by $82\%$ ($\text{star\_factor} = 0.18$), rendering it highly stable.

---

## 5. Phase Gating & Strata

The manifold divides its concepts into semantic layers using a global temporal clock:
$$\theta_{\text{phase}} = \cos\left( \omega \cdot t \cdot 10 \right) \quad (\omega = 0.15)$$
* **Surface Active Layer (Tech):** Fully awake when $\theta_{\text{phase}} > -0.2$.
* **Deep Active Layer (Spirit):** Fully awake when $\theta_{\text{phase}} < 0.2$.
* **Gated Transport:** If a node's native group is tech and the surface layer is asleep, it cannot receive or transmit mass. If both nodes on an edge are asleep, flux drops to zero.
* **Tension Parameters:** Modulates conductance across layers:
  * Tech Edges: Conductance scaled by `surfaceTension` ($1.2$)
  * Spirit Edges: Conductance scaled by `deepViscosity` ($0.8$)

---

## 6. Attractors, Latching, & Metastability

### 6.1. Metastability & The Failure Basin
Although the system can appear stable under normal inputs, it possesses metastable horizons. Under high-discretization stress (large $dt$) or prolonged injections, the system undergoes a phase transition, collapsing its mass into a dominant attractor reservoir—specifically, **Node 82** (the global mass sink).
* **Instability Indicator:** Mean pressure ($\bar{p} > 0.5$) sustained for more than $20$ consecutive steps marks system failure.

### 6.2. The Digital Latch Primitive
The engine supports digital-style mode selection at the boundary between dream and wake states. 
* **The Last-Injected Rule:** The attractor basin into which the system relaxes at $t_0$ is determined deterministically by the node that received the *last injection* immediately prior to halting the dream phase:
  $$\text{attractor\_basin}(t_0) \approx \text{lastInjectedNode}(\text{dream\_stop})$$
* **Asymmetry:** Basins have asymmetric stability (e.g., node 90 holds longer under negative belief fields, whereas node 82 is the dominant default sink).

---

## 7. Observable Metrics

To monitor the state space, agents must inspect these global metrics:

| Metric | Equation / Description | Utility |
|---|---|---|
| **System Mass** | $M = \sum \rho_i$ | Verifies mass conservation (no leak/creation bugs). |
| **Entropy** | $H = -\sum \left(\frac{\rho_i}{M} \cdot \ln \frac{\rho_i}{M}\right) / \ln(N)$ | Measures attention spread ($0.0$ = single node spike, $1.0$ = uniform spread). |
| **Total Flux** | $J_{total} = \sum |j_{ij}|$ | Measures information throughput activity. |
| **Active Count** | Count of nodes where $\rho_i > 0.1$ | Tracks semantic activation breadth. |
| **rhoMaxId** | $\text{argmax}_i(\rho_i)$ | Identifies the currently active attractor/state basin. |
| **outfluxRate** | $J_{out} / (\text{Inject} \cdot dt)$ | DT-normalized stress metric for boundary detection. |

---

## 8. Blank Manifold Dynamics

In high-performance agentic routing applications where historic bias must be minimized, the manifold is initialized in a pristine, unweighted state:

* **Topological Vacuum:** The substrate initializes a 1,024-node lattice (`BlankManifoldCore`) in a non-Euclidean geometry (e.g. uniform hyperbolic space, `topology_type: "hyperbolic_uniform"`) with zero baseline semantic pressure.
* **Hyperbolic Ricci Flow:** 
  To accommodate large amounts of recursive network data without congestion or path collisions, negative spatial curvature ($R_{ij}$) is actively injected to generate a saddle geometry:
  $$\frac{\partial g_{ij}}{\partial t} = -2R_{ij}$$
  This negative curvature provides infinite internal surface area, preventing early path saturation.

---

## 9. Manifold Wormhole Dynamics (Entangled Pairs)

In the two-manifold entangled configuration (`EntangledSOLPair`), two independent manifolds (Manifold A and Manifold B) run in parallel, communicating through a deterministic wormhole registry.

* **Wormhole Registry:** A set of $K$ entry and exit nodes (e.g. 12 nodes) are designated as "wormholes" connecting matching indices on Manifold A and B.
* **Damped Flux Injections:** Rather than transferring data algorithmically, the system calculates a wormhole signature based on node states and injects a damped, reciprocal flux ($j_{\text{entangled}}$) across the connection:
  $$j_{\text{entangled}} \propto \text{aperture} \cdot \mathbf{W}_{\text{wormhole}} \cdot (\rho_{A, i} - \rho_{B, i})$$
  Where $\mathbf{W}_{\text{wormhole}}$ is the `wormhole_weight_map`.
* **Coherence Feedback Loop:** The aperture (conductance size) of the wormhole registry expands and contracts dynamically based on phase synchronization:
  * **Resonance/In-Phase:** If both manifolds are in phase ($\psi_A \approx \psi_B$), the aperture dilates, increasing flux exchange.
  * **Cancellation/Out-of-Phase:** If they drift out of phase, the aperture constricts, isolating the manifolds.
  * This creates an entangled double-well potential, allowing the two systems to spontaneously collapse into a shared consensus basin.

---

## 10. The n+1 Event (Threshold Bursts)

An **n+1 Event** represents the spontaneous projection of the next cognitive state from the physics manifold.

* **Hotspot Functional ($H_i$):**
  The Ontological Orchestrator monitors the manifold by computing the tri-axial hotspot score per node:
  $$H_{i}(t) = \alpha_{1}||(B\rho)_{\text{incident}}|| + \alpha_{2}||(B\phi)_{\text{incident}}|| + \alpha_{3}||(Cj)_{\text{cycles}}||$$
  Where:
  * $B\rho$ is the gradient of density (Jeans Gravity).
  * $B\phi$ is the gradient of scalar potential (Epistemic Friction / Shear).
  * $Cj$ is the cycle flux (Vorticity / Magnetic Curl).
* **Threshold Burst:** When a local node's hotspot functional crosses the dynamically calibrated threshold $H_i \ge \tau_t$:
  * The system triggers a **Threshold Burst** event.
  * Computation resources (rendering and agentic priority) are dynamically routed directly to the collapsing basin.
  * The system unrolls the state variables of the collapsing basin and projects the machine-readable **n+1 sequence** (the subsequent sequence of thought actions) to be executed by external agents.
* **Adaptive Threshold Calibration:**
  To prevent threshold chatter under fluctuating load, $\tau_t$ is smoothed over time using robust distribution statistics of the active hotspot field:
  $$\tau_t = \text{smooth}\left( \max\left(\tau_{\min}, \tau_0, Q_p(H), \text{median}(H) + \lambda \cdot \text{MAD}(H)\right) \right)$$
  Where $Q_p$ is a quantile check, and $\text{MAD}$ is the Median Absolute Deviation.
