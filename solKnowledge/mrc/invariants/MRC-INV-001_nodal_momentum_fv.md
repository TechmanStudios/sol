---
mrc_id: MRC-INV-001
title: "Nodal Momentum Finite-Volume Discretization"
formulation: "fv_discrete"
governing_equations:
  - "J_kl = [rho_bar_kl * (v_from - v_to) - (gamma1 / 2) * (rho_k - rho_l)] * w_kl"
  - "dm_from_dt = -[m_bar_kl * (v_from - v_to) - (gamma2 / 2) * (m_to - m_from)] * w_kl - w_kl * (p_to - p_from) - alpha * m_from"
  - "dm_to_dt = -[m_bar_kl * (v_to - v_from) - (gamma2 / 2) * (m_from - m_to)] * w_kl - w_kl * (p_from - p_to) - alpha * m_to"
verification_script: "scratch/stress_test_dynamic_scaling.py"
---

# Nodal Momentum Finite-Volume Formulation

This invariant defines the core physics solver that replaces the naive pressure-differential flux equations. It maintains momentum conservation and energy dissipation on undirected graphs.

## 1. Continuous Equations (Background)

The governing space-time continuous momentum and mass conservation equations on a manifold $M$ are:
$$\partial_t \rho + \nabla_M \cdot (\rho v) = s_\rho$$
$$\partial_t (\rho v) + \nabla_M \cdot (\rho v \otimes v) = -\nabla_M p - \alpha \rho v + \mu \Delta_M v + f$$

## 2. Discrete Nodal formulation

When discretized on an undirected graph $G = (V, E)$, each edge $e = (k, l)$ carries independent, directed momentum terms $m_l^{(k)}$ (representing flow $k \to l$, stored as `m_from`) and $m_k^{(l)}$ (representing flow $l \to k$, stored as `m_to`).

The discrete ODEs are integrated using Forward Euler at each step:

### Mass Transport Flux
$$J_{kl} = \left[ \overline{\rho}_{kl}(v_l^{(k)} - v_k^{(l)}) - \frac{\gamma_1}{2}(\rho_k - \rho_l) \right] w_{kl}$$
where:
*   $\overline{\rho}_{kl} = \frac{\rho_k + \rho_l}{2}$
*   $v_l^{(k)} = \frac{m_l^{(k)}}{\rho_k + \epsilon}$ and $v_k^{(l)} = \frac{m_k^{(l)}}{\rho_l + \epsilon}$
*   $\gamma_1$ is mass dissipation strength (default: 0.8)

### Momentum Derivatives
$$\frac{d}{dt} m_l^{(k)} = - \left[ \overline{m}_{kl}(v_l^{(k)} - v_k^{(l)}) - \frac{\gamma_2}{2}(m_k^{(l)} - m_l^{(k)}) \right] w_{kl} - w_{kl}(p_l - p_k) - \alpha m_l^{(k)}$$
$$\frac{d}{dt} m_k^{(l)} = - \left[ \overline{m}_{kl}(v_k^{(l)} - v_l^{(k)}) - \frac{\gamma_2}{2}(m_l^{(k)} - m_k^{(l)}) \right] w_{kl} - w_{kl}(p_k - p_l) - \alpha m_k^{(l)}$$
where:
*   $\overline{m}_{kl} = \frac{m_l^{(k)} + m_k^{(l)}}{2}$
*   $\gamma_2$ is momentum dissipation strength (default: 0.8)
*   $\alpha$ is damping drag coefficient

## 3. Conservation Verification

In the absence of external mass/momentum sources ($s_\rho = 0, \alpha = 0$), the discrete formulation guarantees:
1.  **Mass Conservation:** $\frac{d}{dt} \sum_k \rho_k = 0$
2.  **Momentum Conservation:** $\frac{d}{dt} \sum_{k,l} m_l^{(k)} = 0$
3.  **Dissipation Limits:** $\frac{1}{2} \frac{d}{dt} |\rho|^2 \le 0$ (for $\gamma_1 > 0$) and $\frac{1}{2} \frac{d}{dt} |m|^2 \le 0$ (for $\gamma_2 > 0$).
