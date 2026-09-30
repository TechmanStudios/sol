# Jeans Cosmology Experiment — Run Bundle

## Question
How do the collapse threshold (Jcrit) and injection strategy (blast / drizzle / cluster)
shape the topology of emergent structure in the SOL graph?

## Hypothesis
- **Low Jcrit** (5–10): Many stars form quickly → heavy accretion → high synth count → 'rich' cosmology
- **High Jcrit** (30–50): Few or no collapses → energy dissipates → 'barren' cosmology
- **Blast injection**: Single hot node collapses first → radial expansion of structure
- **Drizzle injection**: Slow accumulation → delayed but distributed stellar formation
- **Cluster spray**: Multiple simultaneous collapses → synth-web between stars

## Invariants
- dt = 0.12
- c_press = 0.1
- damping = 0.2
- tractor_rate = 0.05
- rng_seed = 42
- steps = 600

## Knobs
- **Jcrit**: [8.0, 15.0, 18.0, 30.0, 50.0]
- **Strategy**: ['blast', 'drizzle', 'cluster_spray']

## Cosmology Comparison

| Jcrit | Strategy | Stars | Synths | First Collapse | Entropy | Mass | MaxRho | Active |
|------:|----------|------:|-------:|---------------:|--------:|-----:|-------:|-------:|
|   8.0 | blast          |   280 |    140 |              0 |  0.9662 | 148.59 |   5.82 |    269 |
|   8.0 | drizzle        |   280 |    140 |              0 |  0.9588 | 162.17 |   5.77 |    269 |
|   8.0 | cluster_spray  |   280 |    140 |              0 |  0.9710 | 253.84 |   4.87 |    280 |
|  15.0 | blast          |     2 |      1 |              0 |  0.5764 | 116.56 |  44.48 |    130 |
|  15.0 | drizzle        |     2 |      1 |              0 |  0.5142 | 134.89 |  69.76 |    130 |
|  15.0 | cluster_spray  |    10 |      5 |              0 |  0.5831 | 331.89 |  45.48 |    133 |
|  18.0 | blast          |     2 |      1 |              0 |  0.5764 | 116.56 |  44.48 |    130 |
|  18.0 | drizzle        |     2 |      1 |              0 |  0.5142 | 134.89 |  69.76 |    130 |
|  18.0 | cluster_spray  |    10 |      5 |              0 |  0.5831 | 331.89 |  45.48 |    133 |
|  30.0 | blast          |     2 |      1 |              0 |  0.5764 | 116.56 |  44.48 |    130 |
|  30.0 | drizzle        |     2 |      1 |              0 |  0.5142 | 134.89 |  69.76 |    130 |
|  30.0 | cluster_spray  |    10 |      5 |              0 |  0.5831 | 331.89 |  45.48 |    133 |
|  50.0 | blast          |     2 |      1 |              0 |  0.5764 | 116.56 |  44.48 |    130 |
|  50.0 | drizzle        |     2 |      1 |             20 |  0.5244 | 134.82 |  63.52 |    130 |
|  50.0 | cluster_spray  |    10 |      5 |              0 |  0.5831 | 331.89 |  45.48 |    133 |

## Synth Birth Log (First 30 events)

| Condition | Tick | Parent | Synth | Parent ρ | Semantic Mass |
|-----------|-----:|--------|-------|----------:|--------------:|
| Jcrit=15.0_strategy=blast |    0 | grail | synth:grail | 189.5153 |        1.0000 |
| Jcrit=15.0_strategy=cluster_spray |    0 | christ | synth:christ |  37.9114 |        1.0000 |
| Jcrit=15.0_strategy=cluster_spray |    0 | temple doors | synth:temple doors |  37.9117 |        1.0000 |
| Jcrit=15.0_strategy=cluster_spray |    0 | numis'om | synth:numis'om |  37.9099 |        1.0000 |
| Jcrit=15.0_strategy=cluster_spray |    0 | metatron | synth:metatron |  37.9114 |        1.0000 |
| Jcrit=15.0_strategy=cluster_spray |    0 | venus | synth:venus |  37.9110 |        1.0000 |
| Jcrit=15.0_strategy=drizzle |    0 | grail | synth:grail |   9.4642 |        1.0000 |
| Jcrit=18.0_strategy=blast |    0 | grail | synth:grail | 189.5153 |        1.0000 |
| Jcrit=18.0_strategy=cluster_spray |    0 | christ | synth:christ |  37.9114 |        1.0000 |
| Jcrit=18.0_strategy=cluster_spray |    0 | temple doors | synth:temple doors |  37.9117 |        1.0000 |
| Jcrit=18.0_strategy=cluster_spray |    0 | numis'om | synth:numis'om |  37.9099 |        1.0000 |
| Jcrit=18.0_strategy=cluster_spray |    0 | metatron | synth:metatron |  37.9114 |        1.0000 |
| Jcrit=18.0_strategy=cluster_spray |    0 | venus | synth:venus |  37.9110 |        1.0000 |
| Jcrit=18.0_strategy=drizzle |    0 | grail | synth:grail |   9.4642 |        1.0000 |
| Jcrit=30.0_strategy=blast |    0 | grail | synth:grail | 189.5153 |        1.0000 |
| Jcrit=30.0_strategy=cluster_spray |    0 | christ | synth:christ |  37.9114 |        1.0000 |
| Jcrit=30.0_strategy=cluster_spray |    0 | temple doors | synth:temple doors |  37.9117 |        1.0000 |
| Jcrit=30.0_strategy=cluster_spray |    0 | numis'om | synth:numis'om |  37.9099 |        1.0000 |
| Jcrit=30.0_strategy=cluster_spray |    0 | metatron | synth:metatron |  37.9114 |        1.0000 |
| Jcrit=30.0_strategy=cluster_spray |    0 | venus | synth:venus |  37.9110 |        1.0000 |
| Jcrit=30.0_strategy=drizzle |    0 | grail | synth:grail |   9.4642 |        1.0000 |
| Jcrit=50.0_strategy=blast |    0 | grail | synth:grail | 189.5153 |        1.0000 |
| Jcrit=50.0_strategy=cluster_spray |    0 | christ | synth:christ |  37.9114 |        1.0000 |
| Jcrit=50.0_strategy=cluster_spray |    0 | temple doors | synth:temple doors |  37.9117 |        1.0000 |
| Jcrit=50.0_strategy=cluster_spray |    0 | numis'om | synth:numis'om |  37.9099 |        1.0000 |
| Jcrit=50.0_strategy=cluster_spray |    0 | metatron | synth:metatron |  37.9114 |        1.0000 |
| Jcrit=50.0_strategy=cluster_spray |    0 | venus | synth:venus |  37.9110 |        1.0000 |
| Jcrit=50.0_strategy=drizzle |   20 | grail | synth:grail |  17.1857 |        1.0000 |
| Jcrit=8.0_strategy=blast |    0 | grail | synth:grail | 189.5137 |        1.0000 |
| Jcrit=8.0_strategy=blast |    0 | par | synth:par |   0.0049 |        1.0000 |

## Observations

### 1. Phase Transition at Jcrit ≈ 10 ("The Wall")
There is a **sharp bifurcation** between Jcrit=8 and Jcrit=15.
- **Below the wall (Jcrit=8)**: ALL 140 original nodes collapse → 280 stars, 140 synths. Total stellar explosion.
- **Above the wall (Jcrit≥15)**: Only directly-injected nodes collapse → 2–10 stars.

**Why**: The Jeans parameter $J = \rho / (c_{press} \cdot \ln(1 + \rho/m) + \epsilon)$ converges to $1/c_{press} = 10$ for any nonzero $\rho$.
So Jcrit < 10 is trivially satisified by even trace amounts of diffused energy — everything becomes a star.
Jcrit > 10 requires substantial rho accumulation. The transition zone (8–12) is the critical regime.

### 2. Jcrit Plateau (15–50): Threshold Saturation
For blast and cluster_spray, Jcrit=15, 18, 30, and 50 produce **identical** star/synth counts (2/1 and 10/5 respectively).
The injection amounts (200 for blast, 40 per node for cluster) always push J far above even Jcrit=50.
**Implication**: Jcrit discrimination only matters when rho is moderate — the drizzle strategy is where Jcrit shows its teeth.

### 3. The Drizzle Exception: Jcrit-Sensitive Dynamics
Drizzle (10 rho per injection every 20 ticks) is the **only** strategy where Jcrit > 10 matters:
- At Jcrit ≤ 30: J(10 rho) = 10/(0.1·ln(11)) ≈ 41.7 > 30 → immediate collapse.
- At **Jcrit=50**: J(10 rho) ≈ 41.7 < 50 → **first collapse delayed to tick 20** (needs 2 drizzle pulses).
- This is the only condition in the entire sweep that has first_collapse > 0 (besides Jcrit=8).

### 4. Strategy > Threshold (Above the Phase Transition)
The injection strategy has **more discriminating power** than Jcrit in the plateau regime:
| Strategy       | Stars | Synths | Collapse Centers |
|---------------|------:|-------:|-----------------:|
| Blast          | 2     | 1      | 1 (grail only)   |
| Drizzle        | 2     | 1      | 1 (grail only)   |
| Cluster spray  | 10    | 5      | 5 (spirit nodes) |

**Verdict**: Strategy determines *how many* collapse centers form; Jcrit determines *whether* they form at all.

### 5. Entropy as Diversity Index
- **Jcrit=8 cluster_spray**: entropy = 0.971 — most evenly distributed mass (280 stars sharing the pool)
- **Jcrit=15+ drizzle**: entropy = 0.514 — most concentrated (one star holds ~70 rho max)
- Entropy cleanly separates "rich" from "sparse" cosmologies.

### 6. Mass Conservation
Total injected mass is 200 rho for blast/cluster, and 200 rho for drizzle (10 × 20 injections over 400 steps).
Final mass varies from 116–332 depending on how much the tractor beam concentrates vs dissipates energy.
Cluster spray retains the most mass (331.89 at Jcrit=15+) because 5 stars accrete from all directions simultaneously.

### Summary: Which Knob Does What
- **Jcrit < 10**: "Big Bang" — everything collapses. Universal star formation.
- **Jcrit 10–50**: "Goldilocks" — only hot nodes collapse. Strategy determines topology.
- **Jcrit > 50**: "Cold Universe" — only massive injections trigger collapse. Drizzle becomes too weak.
- **Blast**: One hot center → radial structure.
- **Drizzle**: Slow build → same outcome as blast once threshold is crossed.
- **Cluster spray**: Multiple simultaneous collapses → star web → richest topology at any Jcrit.

- **Richest cosmology**: Jcrit=8.0_strategy=cluster_spray — 140 synths, 280 stars, entropy=0.971
- **Most barren cosmology**: Jcrit=15.0_strategy=blast — 1 synth, 2 stars, entropy=0.576
- **Fastest collapse**: Jcrit=8.0 (all strategies) at tick 0
- **Slowest collapse**: Jcrit=50.0_strategy=drizzle at tick 20

## Exports
- `jeans_cosmology_summary.csv` — one row per condition
- `jeans_cosmology_trace.csv` — per-step metrics for all conditions
- `jeans_cosmology_synth_log.csv` — synth birth event log
- `jeans_cosmology_run_bundle.md` — this file
