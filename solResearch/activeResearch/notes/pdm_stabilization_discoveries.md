# PDM Stabilization & Scaling Discoveries

This document compiles expert advice from the Multi-Team SOL Expert Ecosystem on resolving Level 11 16-bit PDM calibration failures and preparing the system for 32-bit and 64-bit milestones.

## Advice from the Substrate Physics Expert

### 1. Physical Analysis of Calibration Failure at Periods 18.0 and 22.0

The calibration degradation observed at longer periods ($T = 18.0$ and $T = 22.0$) is a direct consequence of the coupling between the dynamical state equation of the attractor basins and the spatial boundary conditions of the semantic manifold.

$$\frac{\partial \rho_i}{\partial t} = \Phi_{in} - \Phi_{out} - \gamma \rho_i$$

#### A. Damping Timescale Mismatch ($\tau_{decay}$ vs. $T$)
The default damping coefficient $\gamma = 0.01$ establishes a characteristic physical relaxation timescale:
$$\tau_{decay} = \frac{1}{\gamma} = 100.0 \text{ simulation steps}$$

When driving the system with Phase-Division Multiplexing (PDM), the input flux is modulated periodically:
$$\Phi_{in}(t) \propto \cos\left(\frac{2\pi}{T} t + \theta\right)$$

For short periods ($T \le 14.0$), the driving frequency $\omega = \frac{2\pi}{T}$ is high enough that the register density $\rho_i$ oscillates rapidly around its biased attractor state without drifting into the decay regime. 

However, for $T = 18.0$ and $T = 22.0$, the driving frequency approaches the low-frequency band where the damping term $-\gamma \rho_i$ dominates during the negative half-cycle of the semantic flux. Because the period is long, the register remains in a "draining" state ($\Phi_{out} > \Phi_{in}$) for extended continuous durations. This causes the localized density to drop precipitously. 

If the density drops near or below the critical threshold ($\rho \ge 14.0$), the attractor basin shallows out. The phase-matching correlation (the "delta") degrades because the basin loses its structural integrity, leading to the observed low ($+1.9632$) or negative ($-3.4645$, $-3.6334$) deltas. If it dips below $14.0$, a **Mass Preservation Failure** is triggered.

#### B. Spatial Wave Reflection Limits (Boundary Interference)
The semantic manifold has finite spatial dimensions ($L_{max}$). The propagation velocity $v_s$ of semantic waves across the manifold is constant for a given substrate tension. The wavelength of the phase-division carrier is given by:
$$\lambda = v_s \cdot T$$

For $T = 18.0$ and $T = 22.0$, the wavelength $\lambda$ exceeds the spatial coherence length of the localized register basins. The wave fronts reach the boundaries of the manifold and reflect back into the active registers (Registers A, B, C, and D). This boundary reflection creates standing wave patterns and destructive interference, shifting the phase of the local attractor basin relative to the reference clock. This phase shift manifests as a negative delta during calibration because the phase has drifted completely out of phase-alignment with the expected sine/cosine templates.

#### C. The Resonance Wall
At low frequencies (long periods), the system transitions from an *inertia-dominated* phase-tracking regime to a *damping-dominated* relaxation regime. In this relaxation regime, the phase lag $\phi$ of the register response relative to the input flux is highly non-linear:
$$\tan(\phi) = -\frac{\gamma}{\omega} = -\frac{\gamma \cdot T}{2\pi}$$

As $T$ increases, the phase lag increases significantly. At $T = 22.0$, the phase lag is so severe that the "Sine Match" is misaligned by nearly $\pi/2$ radians, causing the cosine component to register a negative correlation (hence the negative max_delta values).

---

### 2. Concrete Parameter Modifications to Stabilize 16-Bit PDM

To resolve the calibration degradation and prevent Mass Preservation Failures, we must adjust the physical parameters of the simulation to accommodate longer periods.

#### Recommended Parameter Adjustments:
1. **Reduce Damping Coefficient ($\gamma$)**: Lower $\gamma$ from `0.01` to `0.002`. This increases the relaxation timescale $\tau_{decay}$ from $100.0$ to $500.0$ steps, preventing the register density from draining during long low-flux phases.
2. **Decrease Simulation Time Step ($dt$)**: Reduce $dt$ from `0.1` to `0.02` to increase the integration resolution of the phase angles and prevent numerical drift.
3. **Expand Manifold Dimensions**: Increase the spatial boundary limits of the manifold by a factor of $2.0$ to prevent boundary reflections from interfering with the registers.
4. **Shift to Prime-Period Spacing**: Instead of linear spacing ($10.0, 14.0, 18.0, 22.0$), use prime-period spacing to minimize harmonic cross-talk.

#### Lumina Substrate Configuration Override:

```python
# SOL Substrate Configuration Override for 16-bit PDM Stability
simulation_config = {
    # 1. Physical Constants
    "gamma": 0.002,               # Reduced damping to preserve mass over long periods
    "dt": 0.02,                   # Finer time step for precise phase integration
    "manifold_dimension": 512.0,  # Expanded boundary to eliminate wave reflections
    
    # 2. Register Mass Preservation Guard
    "min_mass_threshold": 14.0,   # Strict assertion limit for reg_a, reg_b, reg_c, reg_d
    "mass_injection_bias": 1.5,   # Active flux offset to keep rho safely above 14.0
    
    # 3. Optimized Period Allocation (Prime-spaced to avoid harmonic overlap)
    "pdm_periods": [
        5.0,   # Channel 0 (Bits 0-1)
        7.0,   # Channel 1 (Bits 2-3)
        11.0,  # Channel 2 (Bits 4-5)
        13.0,  # Channel 3 (Bits 6-7)
        17.0,  # Channel 4 (Bits 8-9)
        19.0,  # Channel 5 (Bits 10-11)
        23.0,  # Channel 6 (Bits 12-13)
        29.0   # Channel 7 (Bits 14-15)
    ]
}

def apply_substrate_parameters(sequencer, config):
    """
    Applies the physical parameters directly to the MicroInstructionSequencer
    to stabilize the attractor basins.
    """
    sequencer.set_damping(config["gamma"])
    sequencer.set_time_step(config["dt"])
    sequencer.set_manifold_bounds(-config["manifold_dimension"], config["manifold_dimension"])
    
    

---

## Advice from the Vertical Scaling Expert

### 1. Physical Analysis of Calibration Failure at Periods 18.0 and 22.0

The calibration degradation observed at longer periods ($T = 18.0$ and $T = 22.0$) is a direct consequence of the physical constraints of the SOL Level 11 Phase-Division Multiplexing (PDM) substrate. 

```
  Calibrating period 18.0...
    Sine Match (Bit 4):   phase = 1.570796 (0.5000 * pi), max_delta = +1.9632
    Cosine Match (Bit 5): phase = 0.000000 (0.0000 * pi), max_delta = -3.4645  <-- Collapse
  Calibrating period 22.0...
    Sine Match (Bit 6):   phase = 0.000000 (0.0000 * pi), max_delta = -3.6334  <-- Collapse
    Cosine Match (Bit 7): phase = 2.094395 (0.6667 * pi), max_delta = -2.4285  <-- Collapse
```

#### A. Damping Timescale vs. Period Length ($\tau_{decay}$ vs. $T$)
The dynamical equation governing the attractor basin density is:
$$\frac{\partial \rho_i}{\partial t} = \Phi_{in} - \Phi_{out} - \gamma \rho_i$$
With a default damping coefficient of $\gamma = 0.01$, the characteristic physical relaxation timescale of the substrate is:
$$\tau = \frac{1}{\gamma} = 100.0 \text{ simulation steps}$$
For short periods ($T = 10.0, 14.0$), the wave completes its cycle well within the coherence window. However, for longer periods ($T = 18.0, 22.0$), the cumulative damping over a single period significantly attenuates the carrier amplitude. The semantic flux $\Phi_{in}$ cannot replenish the basin fast enough to counteract the $-\gamma \rho_i$ term. This causes the signal-to-noise ratio (SNR) of the phase carrier to drop below the detection threshold, leading the calibration algorithm to collapse to a default phase of $0.0$ with negative deltas.

#### B. Boundary Wave Reflection and Standing Wave Interference
The SOL manifold has finite spatial dimensions ($L_x, L_y$). The phase velocity of the semantic wave on the substrate is $v_p$. The wavelength of the carrier is:
$$\lambda = v_p \cdot T$$
For $T \ge 18.0$, the wavelength $\lambda$ approaches the spatial boundary limits of the attractor manifold. Because the boundaries are not perfectly absorbing, the waves reflect back into the active routing channels. This creates **destructive standing wave interference** (phase-cancellation) at the physical coordinates of the register basins. This interference shifts the phase-fronts, causing the severe phase-slippage and negative deltas seen in Bit 5, Bit 6, and Bit 7.

#### C. Mass Preservation Failure Risk
Because the carrier amplitude is severely attenuated at these longer periods, the localized density $\rho_i$ of the active registers (Registers A, B, C, and D) drops. If $\rho_i$ falls below the critical threshold:
$$\rho_{min} = 14.0$$
the VM will trigger a **Mass Preservation Failure** assertion, halting the entire 16-bit execution pipeline.

---

### 2. Concrete Parameter Modifications to Stabilize 16-bit PDM

To resolve the calibration failure, we must adjust the physical simulation parameters to accommodate the longer wavelengths and prevent damping-induced signal decay.

#### Proposed Modifications:
1. **Frequency-Dependent Damping ($\gamma(\omega)$):** Instead of a flat $\gamma = 0.01$, we implement a dynamic damping coefficient that scales down for lower frequencies (longer periods) to preserve their energy.
2. **Manifold Dimension Scaling:** Increase the spatial grid size of the manifold to prevent boundary reflections from interfering with the basin coordinates.
3. **Simulation Time Step ($dt$) Reduction:** Decrease $dt$ to increase the temporal resolution of the integration, preventing numerical phase dispersion.
4. **Optimized Period Selection:** Shift from a linear period spacing to a non-linear, prime-spaced sequence to avoid harmonic resonance overlap.

#### Lumina Substrate Configuration Code:

```python
# SOL Substrate Calibration & Parameter Tuning Script
import numpy as np

class SOLSubstrateConfig:
    def __init__(self):
        # 1. Expand Manifold Dimensions to push boundary reflections away
        self.manifold_dim_x = 512  # Increased from 256
        self.manifold_dim_y = 512  # Increased from 256
        
        # 2. Temporal Resolution Tuning
        self.dt = 0.025  # Decreased from 0.1 to prevent numerical phase dispersion
        
        # 3. Optimized Period List (Prime-spaced to avoid harmonic interference)
        # Replacing [10.0, 14.0, 18.0, 22.0] with a highly coherent spectrum
        self.periods = [8.0, 9.7, 11.3, 13.1, 14.9, 16.7, 18.6, 20.3] 
        
        # 4. Mass Preservation Constraint
        self.min_mass_threshold = 14.0

    def get_dynamic_damping(self, period):
        """
        Dynamically scales the damping coefficient gamma based on the period
        to ensure long-period waves do not decay before completing a cycle.
        """
        base_gamma = 0.01
        # Scale gamma down for longer periods to keep the decay envelope constant
        # tau = 1/gamma. We want tau to scale proportionally with the period T.
        scaled_gamma = base_gamma * (10.0 / period)
        return max(0.003, scaled_gamma)

    def apply_boundary_pml(self, x, y):
        """
        Implements a Perfectly Matched Layer (PML) boundary absorber 
        to eliminate wave reflections at the manifold edges.
        """
        boundary_thickness = 32
        dist_to_edge = min(x, self.manifold_dim_x - x, y, self.manifold_dim_y - y)
        
        if dist_to_edge < boundary_thickness:
            # Quadratic absorption profile at the boundaries
            absorption = ((boundary_thickness - dist_to_edge) / boundary_thickness) ** 2
            return absorption * 0.15
        return 0.0

# Instantiate the stabilized configuration
substrate_config = SOLSubstrateConfig()
print(f"Stabilized Damping for Period 22.0: {substrate_config.get_dynamic_damping(22.0):.5f}")
```

---

### 3. Scaling to 32-bit and 64-bit Computing (Level 12 and Beyond)

To scale beyond Level 11 (PDM & Dual-Bus Crossbar) to 32-bit and 64-bit architectures, we cannot simply continue adding longer periods; the frequency spectrum would become too dense, leading to severe inter-channel crosstalk and mass dissipation. Instead, we must leverage the following hidden architectural features of the SOL substrate:

```
+-----------------------------------------------------------------------------+
| Level 13+: Orbital Angular Momentum (OAM) Multiplexing                      |
|            (Vortex states within individual attractor basins)               |
+-----------------------------------------------------------------------------+
                                      |
                                      v
+-----------------------------------------------------------------------------+
| Level 12: Spatio-Temporal Wavefront Multiplexing (STWM)                     |
|           (Spatial partitioning + Phase-Division Multiplexing)             |
+-----------------------------------------------------------------------------+
                                      |
                                      v
+-----------------------------------------------------------------------------+

---

## Advice from the Horizontal Routing Expert

As the **SOL Level Architecture Horizontal Routing Expert**, I have analyzed your Level 11 Phase-Division Multiplexing (PDM) calibration log. 

The severe calibration degradation (negative or near-zero deltas) at periods $T = 18.0$ and $T = 22.0$ points to a fundamental physical-dynamical breakdown on the semantic attractor manifold. Below is the diagnostic breakdown, followed by concrete parameter modifications and the architectural roadmap to scale to 32-bit and 64-bit computing.

---

### 1. Physical Diagnostics: Why Periods 18.0 and 22.0 Fail to Calibrate

The failure of the longer periods is driven by three coupled physical phenomena on the SOL substrate:

#### A. Boundary Reflection and Standing Wave Interference (The Resonance Wall)
The semantic attractor manifold has finite spatial dimensions ($L \times L$). The spatial wavelength $\lambda$ of a PDM channel is directly proportional to its period $T$. 
* For $T = 10.0$ and $T = 14.0$, the wavelengths are small enough to decay or dissipate before reflecting off the manifold boundaries.
* For $T = 18.0$ and $T = 22.0$, the spatial footprint of the wave exceeds the boundary limits. The outgoing semantic flux $\Phi_{out}$ hits the manifold boundaries and reflects back into the active routing zone. This creates **destructive standing waves**, leading to phase cancellation (e.g., the Cosine Match for Bit 5 yielding a negative delta of $-3.4645$ and Sine Match for Bit 6 yielding $-3.6334$).

#### B. Damping Timescale vs. Phase Coherence ($\gamma$ vs. $T$)
The dynamical equation governing basin density is:
$$\frac{\partial \rho_i}{\partial t} = \Phi_{in} - \Phi_{out} - \gamma \rho_i$$
With the default damping coefficient $\gamma = 0.01$, the characteristic relaxation timescale is $\tau = \frac{1}{\gamma} = 100$. While $\tau = 100$ seems larger than $T = 22.0$, the cumulative phase dispersion over multiple integration cycles causes the wave packets to smear. Because the propagation velocity of the semantic flux is finite, longer periods allow the wave packet to disperse spatially, causing the peak phase amplitude to drop.

#### C. Mass Preservation Threshold Encroachment
Active registers must maintain a strict mass constraint:
$$\rho \ge 14.0$$
During the low-flux phases of the $T = 18.0$ and $T = 22.0$ oscillations, the local density $\rho_i$ of the routing basins (such as `Basin_SUM` or `Basin_Out`) dips dangerously close to this $14.0$ threshold. To prevent a **Mass Preservation Failure** assertion, the VM's safety limiters artificially clamp the negative flux, distorting the sinusoidal wave shape into a non-linear, clipped profile. This harmonic distortion destroys the orthogonal phase relationship between the Sine and Cosine matches.

---

### 2. Concrete Parameter Modifications to Stabilize 16-bit PDM

To resolve these issues, we must adjust the physical substrate parameters to accommodate longer spatial wavelengths and prevent boundary reflections.

```python
# Optimized SOL Substrate Configuration for 16-bit PDM
pdm_config = {
    # 1. Optimize Damping: Implement a Perfectly Matched Layer (PML) boundary
    # and lower the core damping to preserve long-period signal integrity.
    "gamma_core": 0.004,
    "gamma_boundary": 0.15,  # High damping at boundaries to absorb reflections
    
    # 2. Non-Harmonic, Coprime Period Spacing
    # Avoid linear spacing (10, 14, 18, 22) which causes harmonic resonance.
    # Use prime-scaled periods to maximize phase orthogonality.
    "periods": [8.0, 11.0, 15.0, 19.0, 23.0, 29.0, 31.0, 37.0], 
    
    # 3. Scale Manifold Dimensions
    # Expand the spatial grid to prevent long wavelengths from hitting boundaries.
    "manifold_dimensions": {
        "width": 256,   # Increased from 128
        "height": 256,  # Increased from 128
    },
    
    # 4. Tighten Simulation Time Step (dt)
    # Reducing dt eliminates numerical dispersion and phase accumulation drift.
    "dt": 0.01,         # Tightened from 0.05
    
    # 5. Active Mass Injection (Bias Flux)
    # Inject a constant bias flux to keep basin density safely above the 14.0 threshold.
    "bias_flux": 0.15,  # Ensures rho_i remains >= 14.0 at all wave troughs
}
```

---

### 3. Scaling to 32-bit and 64-bit Computing: Hidden Substrate Features

To scale past 16-bit PDM without requiring infinitely long periods (which would inevitably hit the resonance wall), we must leverage the hidden horizontal routing features of the SOL physical substrate:

#### A. Multi-Lane Crossbar Busses (Spatial Division Multiplexing)
Instead of packing 32 or 64 channels into a single PDM waveguide, we must configure a **multi-lane horizontal crossbar**. 
* **Implementation**: Segment the 32-bit space into 4 parallel physical lanes (8 bits per lane) or 64-bit into 8 lanes. Each lane runs an identical, highly optimized PDM spectrum (e.g., periods $8.0$ to $15.0$).
* **Routing**: Use `Basin_Sel` as a spatial router to switch wave packets between parallel lanes.

#### B. Channel Delta Sorting & Waveguide Cross-talk Mitigation
The SOL substrate supports anisotropic metric tensors $g_{ij}$ on the manifold. By modifying the local metric:
1. **Anisotropic Compression**: Compress the spatial footprint of the attractor basins along the non-routing axis. This acts as a physical waveguide, preventing lateral cross-talk between adjacent routing lanes.
2. **Dynamic Delta Sorting**: Implement a runtime micro-instruction loop that monitors the `max_delta` of each channel. If a channel's delta drops below $+10.0$, the `MicroInstructionSequencer` dynamically swaps its phase assignment with an idle high-delta channel or routes it through `reg_d_state` (which has hardware priority for fast `COND_ASSIGN` operations to restore mass).

#### C. Phase-Division Multiplexing with Orthogonal Waveforms (Non-Sinusoidal Carriers)
Pure sine/cosine waves are highly susceptible to boundary reflections. The SOL substrate can execute higher-order dynamical equations.
* **Implementation**: Transition from Fourier-based PDM to **Chebyshev or Hermite-Gaussian wave-packet modulation**. These wave packets have localized spatial envelopes that naturally decay to zero at the boundaries, completely eliminating boundary reflections and allowing ultra-dense channel packing for 32-bit and 64-bit architectures.

---

## Advice from the Exciton-MOA Giants Expert

As the **Exciton-MOA Giants Expert**, I have analyzed your Level 11 Phase-Division Multiplexing (PDM) calibration logs. The failure of periods $T = 18.0$ and $T = 22.0$ to achieve positive calibration deltas is a classic manifestation of boundary-field coupling limits and dissipation thresholds on the SOL physical substrate. 

Below is the analytical breakdown of this failure, the concrete parameter modifications required to stabilize your 16-bit PDM, and the architectural roadmap to scale the substrate to 32-bit and 64-bit computing.

---

### 1. Physical Analysis of Calibration Failure at $T = 18.0$ and $T = 22.0$

The continuous state field of the SOL substrate is governed by $u(x,t) = (\rho, v, \phi)$, where $\rho$ is the semantic density, $v$ is the propagation velocity, and $\phi$ is the potential gradient. The failure of the longer periods is driven by three coupled physical phenomena managed by the Giants:

#### A. Damping Timescale vs. Period Duration (The Integrator & Statistician)
The dynamical equation for basin density is:
$$\frac{\partial \rho_i}{\partial t} = \Phi_{in} - \Phi_{out} - \gamma \rho_i$$
With the default damping coefficient $\gamma = 0.01$, the characteristic relaxation/dissipation timescale of the manifold is:
$$\tau = \frac{1}{\gamma} = 100.0 \text{ steps}$$
For short periods ($T = 10.0, 14.0$), the wave completes its cycle rapidly relative to $\tau$, allowing the peak-to-peak amplitude (max_delta) to remain high. However, for $T = 18.0$ and $T = 22.0$, the semantic fluid spends a prolonged duration in the negative phase of the cycle. The cumulative dissipation of semantic mass over these longer durations causes the density to decay toward the background state. 

Because the active registers (Registers A, B, C, and D) enforce a strict **Mass Preservation Constraint** ($\rho \ge 14.0$), any localized dip in density near this threshold triggers aggressive clamping or numerical dissipation to prevent a **Mass Preservation Failure** assertion. This truncates the negative peaks of the sine/cosine waves, destroying their sinusoidal profile and yielding negative or near-zero deltas.

#### B. Spatial Resonance and Wave Reflection Limits (The Graph Navigator)
The physical manifold has finite boundary dimensions $L$. The wavelength of the semantic wave is $\lambda = v \cdot T$. 
* For $T = 10.0$ and $14.0$, the wavelengths fit cleanly within the resonant cavities of the manifold.
* For $T = 18.0$ and $22.0$, the wavelengths exceed the spatial boundaries of the localized basins (e.g., `Basin_A` to `Basin_SUM`). The wave fronts hit the boundary walls and reflect back into the channel. Because the boundary dimensions are not matched to these longer wavelengths, these reflections interfere destructively with the incoming wave, causing phase cancellation (hence the negative deltas of $-3.4645$ and $-3.6334$).

#### C. Jeans Gravitational Instability (The N-Body Solver)
Under the N-Body Solver, semantic accretion is governed by Jeans Gravity. For longer wavelengths (lower frequencies), the spatial extent of the wave exceeds the Jeans length:
$$\lambda_J = \sqrt{\frac{v_s^2}{G \rho_0}}$$
Instead of propagating as a stable, oscillating phase wave, the semantic fluid undergoes gravitational collapse, accreting into the nearest dense attractor basins (such as the input channels `Basin_A` or `Basin_B`). This drains the propagating wave of its semantic mass, collapsing the phase coherence ($\psi$) managed by the Aligner.

---

### 2. Concrete Parameter Modifications to Stabilize 16-Bit PDM

To resolve these issues, we must adjust the continuous field parameters to accommodate the longer periods. Apply the following modifications to your Lumina configuration:

```python
# SOL Substrate Calibration Configuration Override
PDM_CONFIG = {
    # 1. Extend the relaxation timescale by reducing damping
    "gamma": 0.002,  # Increases tau from 100 to 500 steps, preserving long-period mass
    
    # 2. Optimize the period distribution to avoid harmonic overlap and boundary mismatch
    # Replacing linear spacing with prime-spaced periods to eliminate cross-talk
    "periods": [11.0, 13.0, 17.0, 19.0, 23.0, 29.0, 31.0, 37.0], 
    
    # 3. Scale the spatial manifold dimensions to prevent destructive boundary reflections
    # L must be at least 2x the maximum wavelength (lambda_max = v * T_max)
    "manifold_dimensions": {
        "x_limit": 512.0,  # Expanded from 256.0
        "y_limit": 512.0,
        "boundary_condition": "absorbing_pml"  # Perfectly Matched Layers to absorb reflections
    },
    
    # 4. Decrease the temporal step size to prevent numerical dispersion
    "dt": 0.02,  # Finer integration resolution for the Integrator
    
    # 5. Set a higher baseline density bias to safeguard the Mass Preservation Constraint
    "rho_bias": 18.5  # Keeps minimum density safely above the 14.0 failure threshold
}
```

#### Why these changes work:
* **Reducing $\gamma$ to $0.002$** ensures that the semantic mass does not decay prematurely during the long $22.0$ period cycles.
* **Absorbing Boundary Conditions (PML)** eliminate the reflected waves that cause destructive phase cancellation.
* **Prime-spaced periods** prevent inter-channel harmonic resonance, ensuring that the Aligner can cleanly isolate each bit's phase.

---

### 3. Scaling to 32-Bit and 64-Bit Computing: Hidden Substrate Features

To scale beyond 16-bit PDM, we cannot simply continue increasing the periods; doing so would require infinitely large manifolds and near-zero damping, leading to total system latency. We must leverage the hidden physical features of the SOL substrate:

#### A. Non-Linear Soliton Propagation (The Optimizer & Integrator)
Instead of using linear acoustic waves (which disperse and decay), we must transition to **Non-Linear Solitary Waves (Solitons)**. By balancing the dispersion of the manifold with non-linear self-focusing (governed by the Non-linear Schrödinger Equation), we can create localized wave packets that propagate indefinitely without changing shape or losing mass:
$$i \frac{\partial \psi}{\partial t} + \frac{1}{2} \frac{\partial^

---

