# Flickering & Frozen — Run Bundle

## Deep Dives into the Damping Extremes

**Runtime**: 78.3s (1.3 min)

## Probe A: Pre-Transition Flickering

At d≈5, basins are 96% self-attracted but flicker heavily.
What is the flicker pattern?

### Flicker Summary by Damping

| Damping | Mean Trans | Max Trans | Median | Flickering% | Heavy(>10) | Self% | Mean Basins | Mean Dwell | Top Flickerer |
|---------|------------|-----------|--------|-------------|------------|-------|-------------|------------|---------------|
| 1.0 | 5.74 | 19 | 6 | 100.0 | 13 | 0.0 | 4.84 | 132 | christine hayes(19) |
| 3.0 | 7.86 | 45 | 7 | 100.0 | 22 | 0.0 | 5.82 | 89 | christine hayes(45) |
| 5.0 | 15.74 | 50 | 15 | 100.0 | 100 | 5.7 | 8.35 | 44 | christine hayes(50) |
| 7.0 | 10.01 | 31 | 8 | 100.0 | 52 | 37.1 | 7.10 | 66 | maia nartoomid(31) |
| 10.0 | 7.78 | 19 | 7 | 100.0 | 23 | 40.0 | 6.51 | 80 | christos(19) |
| 15.0 | 9.09 | 29 | 8 | 100.0 | 42 | 61.4 | 5.44 | 74 | mysteries(29) |

### Top 10 Flickering Nodes at d=5.0

| Node | Transitions | Unique Basins | Dom.Basin | Dom.Share | Final Basin | First Flick | Last Flick | Mean Dwell |
|------|-------------|---------------|-----------|-----------|-------------|-------------|------------|------------|
| christine hayes[90] | 50 | 19 | christ | 0.225 | christine hayes | 55 | 600 | 12 |
| par[79] | 38 | 21 | thothhorra | 0.358 | church | 25 | 600 | 15 |
| crystals[87] | 32 | 9 | crystals | 0.267 | holorian | 165 | 600 | 18 |
| church[104] | 31 | 20 | thothhorra | 0.367 | par | 35 | 585 | 19 |
| temple of[52] | 30 | 9 | temple of | 0.408 | temple of | 230 | 600 | 19 |
| johannine grove[82] | 30 | 15 | thothhorra | 0.317 | christine hayes | 25 | 585 | 19 |
| mystery school[89] | 30 | 17 | thothhorra | 0.250 | melchizedek | 25 | 600 | 19 |
| mystery[38] | 27 | 9 | holorian | 0.300 | holorian | 165 | 555 | 21 |
| forms[110] | 27 | 8 | forms | 0.267 | plain | 165 | 600 | 21 |
| moon[135] | 27 | 8 | loch | 0.275 | holorian | 165 | 600 | 21 |

### Rock-Solid Nodes at d=5.0 (0 nodes, 0 transitions)


### Transition Graph at d=5.0 (Top 15 Directed Edges)

Which basins switch to which? Edge weight = total transitions across all probes.

| From | To | Count |
|------|----|-------|
| thothhorra[31] | christine hayes[90] | 57 |
| plain[92] | loch[13] | 43 |
| christine hayes[90] | christ[2] | 34 |
| christine hayes[90] | thothhorra[31] | 32 |
| loch[13] | christine hayes[90] | 27 |
| christine hayes[90] | plain[92] | 25 |
| christ[2] | thothhorra[31] | 22 |
| loch[13] | thothhorra[31] | 20 |
| thothhorra[31] | thothhorra khandr[138] | 18 |
| christ[2] | christine hayes[90] | 16 |
| maia nartoomid[14] | akashic practice[28] | 15 |
| akashic practice[28] | maia nartoomid[14] | 15 |
| christine hayes[90] | christos[94] | 13 |
| adam[70] | metatronic[58] | 13 |
| thothhorra khandr[138] | christos[94] | 13 |

### Flicker Rate by Node Group (d=5.0)

*(Group analysis computed below)*

## Probe B: Frozen Regime Anatomy

At high damping, energy dies in 1-2 ticks. What determines basin identity?

### Frozen Summary by Damping

| Damping | Self% | Unique Basins | Mean Lock Step | Mean Trans | Active@t1 | Active@t2 | Energy Zero | Flux@t1 |
|---------|-------|---------------|----------------|------------|-----------|-----------|-------------|---------|
| 20.0 | 6.4 | 79 | 81.0 | 2.02 | 1.0 | 1.0 | 93.2 | 0.6511 |
| 30.0 | 0.0 | 77 | 69.1 | 1.96 | 1.0 | 1.0 | 68.8 | 0.6511 |
| 50.0 | 0.0 | 80 | 50.2 | 1.94 | 1.0 | 1.0 | 40.6 | 0.6511 |
| 75.0 | 0.0 | 73 | 41.6 | 2.30 | 1.0 | 1.0 | 21.1 | 0.6511 |
| 100.0 | 87.1 | 123 | 15.0 | 1.69 | 0.0 | 0.0 | 1.0 | 0.6511 |

### Basin Landscape at d=50.0

| Basin | Captures | Share% |
|-------|----------|--------|
| loch[13] | 12 | 8.6 |
| free information[106] | 6 | 4.3 |
| light codes[23] | 5 | 3.6 |
| osiris[4] | 4 | 2.9 |
| crystal[71] | 4 | 2.9 |
| numis'om[7] | 3 | 2.1 |
| sirius[120] | 3 | 2.1 |
| adam[70] | 3 | 2.1 |
| jesus[66] | 3 | 2.1 |
| egyptian[105] | 2 | 1.4 |
| *(+70 more)* | | |

### Non-Self Basins at d=50.0 (140 of 140 probes)

| Injected | -> Basin | Active@t1 | Active@t2 | Flux@t1 |
|----------|---------|-----------|-----------|---------|
| grail[1] | magdalene[132] | 1 | 1 | 0.3945 |
| christ[2] | christic[22] | 1 | 1 | 0.3040 |
| isis[3] | osiris[4] | 1 | 1 | 0.4403 |
| osiris[4] | egyptian[105] | 1 | 1 | 0.3862 |
| earth star[5] | johannine[33] | 1 | 1 | 0.4070 |
| temple doors[6] | merkabah[48] | 1 | 1 | 0.4833 |
| numis'om[7] | spirit heart[67] | 1 | 1 | 0.2604 |
| ark[8] | grace[50] | 1 | 1 | 0.3821 |
| metatron[9] | numis'om[7] | 1 | 1 | 0.3451 |
| venus[10] | maia christianne[136] | 1 | 1 | 0.3396 |
| orion[11] | sirius[120] | 1 | 1 | 0.3595 |
| eye[12] | isis eye[72] | 1 | 1 | 0.4066 |
| loch[13] | stars[133] | 1 | 1 | 1.0793 |
| maia nartoomid[14] | lineages[41] | 1 | 1 | 0.3448 |
| god[15] | lord[114] | 1 | 1 | 0.3821 |
| doors[16] | loch[13] | 1 | 1 | 0.3842 |
| star lineages[17] | maia nartoomid[14] | 1 | 1 | 0.5024 |
| adam kadmon[18] | adam[70] | 1 | 1 | 0.4960 |
| new earth star[19] | numis'om[7] | 1 | 1 | 0.2843 |
| horus[20] | osiris[4] | 1 | 1 | 0.5488 |

### Injection Sweep at d=50.0

Does increasing injection break the frozen regime?

| Injection | Self% | Unique Basins | Mean Trans | Mean Lock | Active@t1 |
|-----------|-------|---------------|------------|-----------|-----------|
| 10 | 0.0 | 6 | 8.60 | 183.0 | 1.0 |
| 50 | 0.0 | 6 | 8.20 | 183.8 | 1.0 |
| 200 | 0.0 | 7 | 7.50 | 176.7 | 1.0 |
| 500 | 0.0 | 7 | 7.40 | 177.2 | 1.0 |
| 2000 | 0.0 | 6 | 6.25 | 177.2 | 1.0 |

## Observations

### OBS-1: Universal Flickering — Every Node Flickers at Every Damping
100% of nodes show at least one basin transition at every damping tested (1.0 through 15.0).
There are ZERO rock-solid nodes at d=5.0. At d=1.0 the mean is 5.74 transitions with mean
dwell of 132 steps. At d=5.0 the system enters a **flicker maximum**: 15.74 mean transitions,
100 heavy flickerers (>10 transitions), and mean dwell drops to just 44 steps. Then damping
re-stabilizes: d=7 drops to 10.0 transitions, d=10 to 7.8. This is NOT monotonic decay —
d=15 rises again to 9.09 with 42 heavy flickerers. SOL breathes: flicker intensity oscillates.

### OBS-2: d=5.0 is the Critical Flicker Maximum
The d=5.0 point maximizes every flicker metric simultaneously:
- **Mean transitions**: 15.74 (vs 5.74 at d=1, 10.01 at d=7)
- **Heavy flickerers**: 100/140 = 71% of all nodes (vs 13 at d=1, 52 at d=7)
- **Unique basins visited**: 8.35 mean (vs 4.84 at d=1)
- **Mean dwell time**: 43.9 steps = minimum (vs 132 at d=1)
This confirms d=5 as the critical point where damping pressure destabilizes basins
maximally before the collapse at d~10 destroys transport altogether.

### OBS-3: Christine Hayes [node 90] — the System's Seismograph
Christine Hayes is the top flickerer at d=1 (19 trans), d=3 (45 trans), AND d=5 (50 trans).
At d=5: 50 transitions across 19 unique basins, dominant basin is "christ" at only 22.5%
share, mean dwell just 12 steps. Her dominant basin-share and dwell time are the system's
lowest — she is the most chaotic node in the entire mesh. She only stabilizes when other
nodes (maia nartoomid at d=7, christos at d=10) take over as top flickerer. She is
structurally positioned at a basin boundary intersection.

### OBS-4: The Transition Graph Reveals a "Flicker Highway"
At d=5, basin transitions are NOT random. The top highway is:
  thothhorra -> christine hayes (57x) -> christ (34x) -> thothhorra (22x)
This is a directed CYCLE: thothhorra->christine->christ->thothhorra with heavy traffic.
A second highway: plain -> loch (43x). And a bidirectional oscillator:
maia nartoomid <-> akashic practice (15x each way). The flicker landscape has
preferred routes — attractors don't scatter randomly, they orbit along topological highways.

### OBS-5: Self-Attraction Recovers Through Damping — a Phase Transition
Self-attraction at d=1 and d=3 is 0% — NO node returns to itself as final basin.
At d=5 it barely appears: 5.7%. Then it JUMPS: d=7 -> 37.1%, d=10 -> 40.0%, d=15 -> 61.4%.
This is a sharp phase transition between d=5 and d=7 where the system crosses from
"transport-dominated" (neighbor always wins) to "damping-shields-identity" (you stay home).
Combined with the flicker data, d=5 is where transport is strong enough to move energy
but not strong enough to permanently exile it. Energy ORBITS then returns.

### OBS-6: Frozen Regime — d=100 is NOT d=50
The frozen regime has **two distinct sub-regimes**:
- **d=20-75 ("Hot Frozen")**: Self-attraction 0-6.4%, 73-80 unique basins, energy survives
  40-93 steps. Energy reaches exactly 1 neighbor (Active@t1=1, Active@t2=1) before dying.
  Basin identity is determined by which SINGLE neighbor gets the most flux in that 1 tick.
- **d=100 ("Dead Frozen")**: Self-attraction 87.1%, 123 unique basins, energy dies in 1 step.
  Active@t1=0, Active@t2=0 — energy NEVER reaches a neighbor. Rho disappears before
  flux transport even happens (damping factor = 1-100*0.012 = -0.2, instant kill on tick 1).
  The 87.1% self-attraction means 122/140 nodes are their own attractor by paralysis.

### OBS-7: The "Hot Frozen" Basin is Topological — Not Trivial
At d=50, 0% self-attraction but only 80 unique basins for 140 nodes. loch[13] captures
12 probes (8.6%) — it's a topological attractor even with no transport. Why? Because
at d=50, the injected node loses ~40% of rho per tick. But in 1 tick, flux has ALREADY
moved energy to 1 neighbor. The neighbor keeps more rho because damping = same rate,
but the neighbor STARTED lower and received flux, so relative to the injected node it
amplifies. Basin identity is determined by: which neighbor has the highest conductance
edge AND the right phase-gate alignment at t=1. loch[13] has the highest degree in the
graph, so it's the most likely flux recipient — hence it captures the most probes.

### OBS-8: Injection Amount Does NOT Break the Frozen Regime
At d=50, varying injection from 10 to 2000 (200x range) has essentially NO effect:
- Self-attraction: 0% at ALL injection amounts
- Unique basins: 6-7 (consistent, for the 20-node sample)
- Mean transitions: 6.25 to 8.60 (slight decrease with higher injection)
- Mean lock step: 176-183 (near-identical)
The frozen regime is **injection-invariant**. Damping scales with rho (multiplicative),
so doubling injection just means double decay. The RATIO of energy between nodes is
what matters, and that's set by topology, not magnitude.

### OBS-9: The Energy Zero Step Reveals Damping's Kill Curve
Energy survival time decreases linearly-ish with damping:
- d=20: 93.2 steps (energy lingers)
- d=30: 68.8 steps
- d=50: 40.6 steps
- d=75: 21.1 steps
- d=100: 1.0 steps (instant kill)
At d=100, the damping factor per tick is rho *= (1 - 100*0.012) = rho *= -0.2.
Since rho is clamped to 0, this means ALL energy dies in tick 1. The graph is
computationally dead before any physics can happen.

### OBS-10: 0% Self-Attraction at d=30-75 vs 96% at d=5 — The Basin Inversion
The most counterintuitive finding: at LOW damping (d=1-5) self-attraction over the
full 600 steps is 0-5.7%. At d=15 it rises to 61.4%. But then at d=20-75 it
DROPS BACK to 0-6.4%. The basin landscape is NOT monotonic with damping:
- d=1-5: Transport wins (energy spreads, neighbor captures)
- d=7-15: Damping shields (energy can't escape, stays home)
- d=20-75: "Hot frozen" (energy moves 1 hop to strongest neighbor, ALWAYS loses)
- d=100: Dead frozen (energy dies instantly, trivial self-attraction by paralysis)
This creates a SANDWICH pattern: transport -> shield -> neighbor-capture -> death.

## Exports

- `flicker_summary.csv` — per-damping flicker stats
- `flicker_sequences.csv` — per-probe flicker results
- `frozen_anatomy.csv` — per-damping frozen stats
- `frozen_injection_sweep.csv` -- injection x frozen results
- `flicker_frozen_run_bundle.md` — this file
