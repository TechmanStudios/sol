# Basin Stability Under Jeans Collapse - Run Bundle

## Question
Does SOL's computational identity (its basin structure) survive
when Jeans collapse adds new nodes and edges to the graph?

C28 proves 30 basins (4.9 bits) on the fixed 140-node graph.
If basins persist after structural growth, SOL's identity is
physics-dependent, not topology-dependent.
If they shift, topology IS the program.

## Invariants
- dt = 0.12
- c_press = 0.1
- probe_steps = 500
- injection_amount = 50.0
- rng_seed = 42
- growth_steps = 200
- elapsed = 10249.9s

## Dampings Probed
- d = 0.2
- d = 5.0
- d = 20.0

## Structural Growth Conditions

| Condition | Jcrit | Strategy | Normalize | Stars | Synths | Total Nodes | Total Edges |
|-----------|------:|----------|-----------|------:|-------:|------------:|------------:|
| mild | 18.0 | blast | No | 2 | 1 | 141 | 849 |
| medium | 18.0 | cluster_spray | No | 10 | 5 | 145 | 865 |
| extreme | 8.0 | blast | No | 280 | 140 | 280 | 1405 |
| mild_norm | 18.0 | blast | Yes | 2 | 1 | 141 | 849 |
| medium_norm | 18.0 | cluster_spray | Yes | 10 | 5 | 145 | 865 |
| extreme_norm | 8.0 | blast | Yes | 280 | 140 | 280 | 1405 |

## Baseline Basin Summary

### d = 0.2
- Unique basins: 112 (6.81 bits)
- Top basins:
  - temple of[52]: 7/140 (5.0%)
  - metatronic[58]: 6/140 (4.3%)
  - thothhorra[31]: 6/140 (4.3%)
  - christ[2]: 4/140 (2.9%)
  - akashic practice[28]: 4/140 (2.9%)
  - free information[106]: 3/140 (2.1%)
  - ark[8]: 2/140 (1.4%)
  - merkabah[48]: 2/140 (1.4%)
  - christic[22]: 2/140 (1.4%)
  - spirit heart[67]: 2/140 (1.4%)

### d = 5.0
- Unique basins: 100 (6.64 bits)
- Top basins:
  - crystal[71]: 7/140 (5.0%)
  - free information[106]: 6/140 (4.3%)
  - maia nartoomid[14]: 5/140 (3.6%)
  - thothhorra[31]: 5/140 (3.6%)
  - osiris[4]: 3/140 (2.1%)
  - adam[70]: 3/140 (2.1%)
  - the sun[101]: 3/140 (2.1%)
  - christ[2]: 2/140 (1.4%)
  - orion[11]: 2/140 (1.4%)
  - lineages[41]: 2/140 (1.4%)

### d = 20.0
- Unique basins: 14 (3.81 bits)
- Top basins:
  - christ[2]: 60/140 (42.9%)
  - numis'om[7]: 30/140 (21.4%)
  - thothhorra khandr[138]: 11/140 (7.9%)
  - christos[94]: 9/140 (6.4%)
  - merkabah[48]: 8/140 (5.7%)
  - new earth star[19]: 6/140 (4.3%)
  - spirit heart[67]: 3/140 (2.1%)
  - temple doors[6]: 3/140 (2.1%)
  - thothhorra[31]: 3/140 (2.1%)
  - christic[22]: 2/140 (1.4%)

## Post-Jeans Comparison

| Condition | Damping | Stability% | Same | Shifted | Base Basins | Post Basins | Synth Basins | Surviving | Lost | New | Jaccard | Base Bits | Post Bits | +/- Bits |
|-----------|--------:|-----------:|-----:|--------:|-----------:|------------:|-------------:|----------:|-----:|----:|--------:|----------:|----------:|---------:|
| extreme | 0.2 | 26.4 | 37 | 103 | 112 | 140 | 103 | 37 | 75 | 0 | 0.3304 | 6.81 | 7.13 | +0.32 |
| extreme | 5.0 | 0.0 | 0 | 140 | 100 | 140 | 140 | 0 | 100 | 0 | 0.0 | 6.64 | 7.13 | +0.49 |
| extreme | 20.0 | 0.0 | 0 | 140 | 14 | 140 | 140 | 0 | 14 | 0 | 0.0 | 3.81 | 7.13 | +3.32 |
| extreme_norm | 0.2 | 62.1 | 87 | 53 | 112 | 136 | 49 | 86 | 26 | 1 | 0.7611 | 6.81 | 7.09 | +0.28 |
| extreme_norm | 5.0 | 10.7 | 15 | 125 | 100 | 128 | 114 | 14 | 86 | 0 | 0.14 | 6.64 | 7.0 | +0.36 |
| extreme_norm | 20.0 | 95.0 | 133 | 7 | 14 | 14 | 0 | 14 | 0 | 0 | 1.0 | 3.81 | 3.81 | +0.00 |
| medium | 0.2 | 82.9 | 116 | 24 | 112 | 119 | 4 | 108 | 4 | 7 | 0.9076 | 6.81 | 6.89 | +0.09 |
| medium | 5.0 | 3.6 | 5 | 135 | 100 | 12 | 5 | 7 | 93 | 0 | 0.07 | 6.64 | 3.58 | -3.06 |
| medium | 20.0 | 11.4 | 16 | 124 | 14 | 9 | 5 | 4 | 10 | 0 | 0.2857 | 3.81 | 3.17 | -0.64 |
| medium_norm | 0.2 | 95.7 | 134 | 6 | 112 | 112 | 0 | 110 | 2 | 2 | 0.9649 | 6.81 | 6.81 | +0.00 |
| medium_norm | 5.0 | 76.4 | 107 | 33 | 100 | 94 | 1 | 85 | 15 | 8 | 0.787 | 6.64 | 6.55 | -0.09 |
| medium_norm | 20.0 | 97.1 | 136 | 4 | 14 | 13 | 0 | 13 | 1 | 0 | 0.9286 | 3.81 | 3.7 | -0.11 |
| mild | 0.2 | 84.3 | 118 | 22 | 112 | 117 | 1 | 109 | 3 | 7 | 0.916 | 6.81 | 6.87 | +0.06 |
| mild | 5.0 | 0.0 | 0 | 140 | 100 | 1 | 1 | 0 | 100 | 0 | 0.0 | 6.64 | 0.0 | -6.64 |
| mild | 20.0 | 11.4 | 16 | 124 | 14 | 5 | 1 | 4 | 10 | 0 | 0.2857 | 3.81 | 2.32 | -1.49 |
| mild_norm | 0.2 | 99.3 | 139 | 1 | 112 | 112 | 1 | 111 | 1 | 0 | 0.9911 | 6.81 | 6.81 | +0.00 |
| mild_norm | 5.0 | 76.4 | 107 | 33 | 100 | 99 | 1 | 86 | 14 | 12 | 0.7679 | 6.64 | 6.63 | -0.01 |
| mild_norm | 20.0 | 98.6 | 138 | 2 | 14 | 14 | 0 | 14 | 0 | 0 | 1.0 | 3.81 | 3.81 | +0.00 |

## Basin Shifts (Detail)

### extreme, d=0.2 (103 shifts)

| Injected Node | Baseline Basin | Post-Jeans Basin |
|---------------|----------------|------------------|
| grail[1] | grail[1] | synth:grail[synth_9000] |
| isis[3] | isis[3] | synth:isis[synth_9008] |
| osiris[4] | osiris[4] | synth:osiris[synth_9009] |
| ark[8] | ark[8] | synth:ark[synth_9010] |
| orion[11] | orion[11] | synth:orion[synth_9011] |
| loch[13] | temple of[52] | synth:loch[synth_9120] |
| god[15] | god[15] | synth:god[synth_9013] |
| star lineages[17] | star lineages[17] | synth:star lineages[synth_9135] |
| adam kadmon[18] | metatronic[58] | synth:adam kadmon[synth_9015] |
| horus[20] | merkabah[48] | synth:horus[synth_9016] |
| skull[21] | thothhorra[31] | synth:skull[synth_9098] |
| inner earth[24] | inner earth[24] | synth:inner earth[synth_9017] |
| blue star[25] | blue star[25] | synth:blue star[synth_9018] |
| activation rite[27] | akashic practice[28] | synth:activation rite[synth_9129] |
| great pyramid[32] | temple of[52] | synth:great pyramid[synth_9021] |
| johannine[33] | free information[106] | synth:johannine[synth_9022] |
| crystal skull[34] | thothhorra[31] | synth:crystal skull[synth_9100] |
| mother[35] | mother[35] | synth:mother[synth_9023] |
| templa mar[36] | templa mar[36] | synth:templa mar[synth_9024] |
| master[37] | master[37] | synth:master[synth_9025] |
| mystery[38] | mystery[38] | synth:mystery[synth_9026] |
| yeshua[39] | yeshua[39] | synth:yeshua[synth_9027] |
| pure gem[40] | pure gem[40] | synth:pure gem[synth_9028] |
| gate[42] | gate[42] | synth:gate[synth_9029] |
| flame[43] | flame[43] | synth:flame[synth_9030] |
| dweller[44] | dweller[44] | synth:dweller[synth_9101] |
| crystal skulls[45] | thothhorra[31] | synth:crystal skulls[synth_9102] |
| atlantis[46] | atlantis[46] | synth:atlantis[synth_9031] |
| grace[50] | grace[50] | synth:grace[synth_9034] |
| lion[53] | lion[53] | synth:lion[synth_9035] |
| ... | (73 more) | |

### extreme, d=5.0 (140 shifts)

| Injected Node | Baseline Basin | Post-Jeans Basin |
|---------------|----------------|------------------|
| grail[1] | magdalene[132] | synth:grail[synth_9000] |
| christ[2] | christ[2] | synth:christ[synth_9107] |
| isis[3] | osiris[4] | synth:isis[synth_9008] |
| osiris[4] | osiris[4] | synth:osiris[synth_9009] |
| earth star[5] | earth star[5] | synth:earth star[synth_9097] |
| temple doors[6] | temple doors[6] | synth:temple doors[synth_9108] |
| numis'om[7] | numis'om[7] | synth:numis'om[synth_9126] |
| ark[8] | grace[50] | synth:ark[synth_9010] |
| metatron[9] | metatron[9] | synth:metatron[synth_9109] |
| venus[10] | venus[10] | synth:venus[synth_9110] |
| orion[11] | orion[11] | synth:orion[synth_9011] |
| eye[12] | eye[12] | synth:eye[synth_9012] |
| loch[13] | crystal[71] | synth:loch[synth_9120] |
| maia nartoomid[14] | lineages[41] | synth:maia nartoomid[synth_9134] |
| god[15] | lord[114] | synth:god[synth_9013] |
| doors[16] | doors[16] | synth:doors[synth_9014] |
| star lineages[17] | maia nartoomid[14] | synth:star lineages[synth_9135] |
| adam kadmon[18] | adam[70] | synth:adam kadmon[synth_9015] |
| new earth star[19] | new earth star[19] | synth:new earth star[synth_9111] |
| horus[20] | osiris[4] | synth:horus[synth_9016] |
| skull[21] | crystal[71] | synth:skull[synth_9098] |
| christic[22] | christic[22] | synth:christic[synth_9112] |
| light codes[23] | light codes[23] | synth:light codes[synth_9099] |
| inner earth[24] | central[75] | synth:inner earth[synth_9017] |
| blue star[25] | valley[121] | synth:blue star[synth_9018] |
| dna[26] | dna[26] | synth:dna[synth_9019] |
| activation rite[27] | maia nartoomid[14] | synth:activation rite[synth_9129] |
| akashic practice[28] | rite akashic[51] | synth:akashic practice[synth_9132] |
| pyramid[29] | temple of[52] | synth:pyramid[synth_9020] |
| templar[30] | lineages[41] | synth:templar[synth_9136] |
| ... | (110 more) | |

### extreme, d=20.0 (140 shifts)

| Injected Node | Baseline Basin | Post-Jeans Basin |
|---------------|----------------|------------------|
| grail[1] | numis'om[7] | synth:grail[synth_9000] |
| christ[2] | christic[22] | synth:christ[synth_9107] |
| isis[3] | numis'om[7] | synth:isis[synth_9008] |
| osiris[4] | numis'om[7] | synth:osiris[synth_9009] |
| earth star[5] | spirit heart[67] | synth:earth star[synth_9097] |
| temple doors[6] | merkabah[48] | synth:temple doors[synth_9108] |
| numis'om[7] | new earth star[19] | synth:numis'om[synth_9126] |
| ark[8] | christ[2] | synth:ark[synth_9010] |
| metatron[9] | numis'om[7] | synth:metatron[synth_9109] |
| venus[10] | maia christianne[136] | synth:venus[synth_9110] |
| orion[11] | christ[2] | synth:orion[synth_9011] |
| eye[12] | spirit heart[67] | synth:eye[synth_9012] |
| loch[13] | christ[2] | synth:loch[synth_9120] |
| maia nartoomid[14] | numis'om[7] | synth:maia nartoomid[synth_9134] |
| god[15] | christ[2] | synth:god[synth_9013] |
| doors[16] | merkabah[48] | synth:doors[synth_9014] |
| star lineages[17] | numis'om[7] | synth:star lineages[synth_9135] |
| adam kadmon[18] | numis'om[7] | synth:adam kadmon[synth_9015] |
| new earth star[19] | numis'om[7] | synth:new earth star[synth_9111] |
| horus[20] | temple doors[6] | synth:horus[synth_9016] |
| skull[21] | thothhorra khandr[138] | synth:skull[synth_9098] |
| christic[22] | christ[2] | synth:christic[synth_9112] |
| light codes[23] | numis'om[7] | synth:light codes[synth_9099] |
| inner earth[24] | christ[2] | synth:inner earth[synth_9017] |
| blue star[25] | numis'om[7] | synth:blue star[synth_9018] |
| dna[26] | merkabah[48] | synth:dna[synth_9019] |
| activation rite[27] | numis'om[7] | synth:activation rite[synth_9129] |
| akashic practice[28] | rite akashic[51] | synth:akashic practice[synth_9132] |
| pyramid[29] | christ[2] | synth:pyramid[synth_9020] |
| templar[30] | numis'om[7] | synth:templar[synth_9136] |
| ... | (110 more) | |

### extreme_norm, d=0.2 (53 shifts)

| Injected Node | Baseline Basin | Post-Jeans Basin |
|---------------|----------------|------------------|
| isis[3] | isis[3] | synth:isis[synth_9008] |
| loch[13] | temple of[52] | synth:loch[synth_9120] |
| adam kadmon[18] | metatronic[58] | synth:adam kadmon[synth_9015] |
| horus[20] | merkabah[48] | synth:horus[synth_9016] |
| skull[21] | thothhorra[31] | skull[21] |
| activation rite[27] | akashic practice[28] | maia nartoomid[14] |
| great pyramid[32] | temple of[52] | synth:great pyramid[synth_9021] |
| johannine[33] | free information[106] | synth:free information[synth_9122] |
| crystal skull[34] | thothhorra[31] | synth:crystal skull[synth_9100] |
| templa mar[36] | templa mar[36] | synth:templa mar[synth_9024] |
| yeshua[39] | yeshua[39] | synth:yeshua[synth_9027] |
| dweller[44] | dweller[44] | synth:dweller[synth_9101] |
| crystal skulls[45] | thothhorra[31] | synth:crystal skulls[synth_9102] |
| skulls[56] | thothhorra[31] | synth:skulls[synth_9103] |
| king[62] | king[62] | synth:king[synth_9042] |
| john[64] | christ[2] | synth:john[synth_9044] |
| jesus[66] | christic[22] | synth:jesus[synth_9046] |
| adam[70] | adam[70] | synth:adam[synth_9048] |
| isis eye[72] | free information[106] | synth:free information[synth_9122] |
| mari[73] | mari[73] | synth:mari[synth_9050] |
| central[75] | central[75] | synth:central[synth_9052] |
| temporal alchemy[77] | akashic practice[28] | maia nartoomid[14] |
| par[79] | temple of[52] | synth:christic[synth_9112] |
| city[80] | city[80] | synth:city[synth_9055] |
| johannine grove[82] | temple of[52] | synth:numis'om[synth_9002] |
| rose[83] | rose[83] | synth:rose[synth_9056] |
| tehuti[85] | tehuti[85] | synth:tehuti[synth_9058] |
| prima matra[88] | prima matra[88] | synth:prima matra[synth_9061] |
| mystery school[89] | temple of[52] | synth:metatron[synth_9003] |
| christine hayes[90] | christ[2] | synth:christine hayes[synth_9117] |
| ... | (23 more) | |

### extreme_norm, d=5.0 (125 shifts)

| Injected Node | Baseline Basin | Post-Jeans Basin |
|---------------|----------------|------------------|
| grail[1] | magdalene[132] | synth:grail[synth_9000] |
| isis[3] | osiris[4] | synth:isis[synth_9008] |
| osiris[4] | osiris[4] | synth:osiris[synth_9009] |
| earth star[5] | earth star[5] | synth:earth star[synth_9097] |
| ark[8] | grace[50] | synth:ark[synth_9010] |
| orion[11] | orion[11] | synth:orion[synth_9011] |
| eye[12] | eye[12] | synth:eye[synth_9012] |
| loch[13] | crystal[71] | synth:loch[synth_9120] |
| maia nartoomid[14] | lineages[41] | synth:maia nartoomid[synth_9134] |
| god[15] | lord[114] | synth:god[synth_9013] |
| doors[16] | doors[16] | synth:doors[synth_9014] |
| star lineages[17] | maia nartoomid[14] | synth:star lineages[synth_9135] |
| adam kadmon[18] | adam[70] | synth:adam kadmon[synth_9015] |
| horus[20] | osiris[4] | synth:horus[synth_9016] |
| skull[21] | crystal[71] | synth:skull[synth_9098] |
| light codes[23] | light codes[23] | synth:maia nartoomid[synth_9134] |
| inner earth[24] | central[75] | synth:inner earth[synth_9017] |
| blue star[25] | valley[121] | synth:blue star[synth_9018] |
| dna[26] | dna[26] | synth:dna[synth_9019] |
| activation rite[27] | maia nartoomid[14] | synth:maia nartoomid[synth_9134] |
| pyramid[29] | temple of[52] | synth:pyramid[synth_9020] |
| templar[30] | lineages[41] | synth:templar[synth_9136] |
| great pyramid[32] | pyramid[29] | synth:great pyramid[synth_9021] |
| johannine[33] | free information[106] | synth:free information[synth_9122] |
| crystal skull[34] | crystal[71] | synth:crystal skull[synth_9100] |
| mother[35] | goddess[91] | synth:mother[synth_9023] |
| templa mar[36] | grid[99] | synth:templa mar[synth_9024] |
| master[37] | master[37] | synth:master[synth_9025] |
| mystery[38] | mystery[38] | synth:mystery[synth_9026] |
| yeshua[39] | yeshua[39] | synth:yeshua[synth_9027] |
| ... | (95 more) | |

### extreme_norm, d=20.0 (7 shifts)

| Injected Node | Baseline Basin | Post-Jeans Basin |
|---------------|----------------|------------------|
| grail[1] | numis'om[7] | christ[2] |
| osiris[4] | numis'om[7] | christ[2] |
| adam kadmon[18] | numis'om[7] | merkabah[48] |
| adam[70] | numis'om[7] | christ[2] |
| mysteries[84] | christ[2] | christos[94] |
| plain[92] | christ[2] | thothhorra khandr[138] |
| kadmon[96] | numis'om[7] | merkabah[48] |

### medium, d=0.2 (24 shifts)

| Injected Node | Baseline Basin | Post-Jeans Basin |
|---------------|----------------|------------------|
| loch[13] | temple of[52] | synth:grail[synth_9000] |
| adam kadmon[18] | metatronic[58] | adam kadmon[18] |
| horus[20] | merkabah[48] | horus[20] |
| great pyramid[32] | temple of[52] | great pyramid[32] |
| johannine[33] | free information[106] | johannine[33] |
| john[64] | christ[2] | synth:grail[synth_9000] |
| jesus[66] | christic[22] | synth:grail[synth_9000] |
| isis eye[72] | free information[106] | isis eye[72] |
| mari[73] | mari[73] | synth:grail[synth_9000] |
| par[79] | temple of[52] | synth:grail[synth_9000] |
| johannine grove[82] | temple of[52] | synth:grail[synth_9000] |
| tehuti[85] | tehuti[85] | synth:numis'om[synth_9002] |
| mystery school[89] | temple of[52] | synth:grail[synth_9000] |
| christine hayes[90] | christ[2] | synth:grail[synth_9000] |
| plain[92] | metatronic[58] | synth:grail[synth_9000] |
| kadmon[96] | metatronic[58] | kadmon[96] |
| simeon[98] | spirit heart[67] | simeon[98] |
| church[104] | christ[2] | synth:grail[synth_9000] |
| holorian[107] | ark[8] | synth:grail[synth_9000] |
| lord[114] | temple of[52] | synth:grail[synth_9000] |
| mazur[118] | metatronic[58] | synth:temple doors[synth_9001] |
| sirius[120] | sirius[120] | synth:venus[synth_9004] |
| melchizedek[126] | metatronic[58] | synth:venus[synth_9004] |
| magdalene[132] | magdalene[132] | synth:grail[synth_9000] |

### medium, d=5.0 (135 shifts)

| Injected Node | Baseline Basin | Post-Jeans Basin |
|---------------|----------------|------------------|
| grail[1] | magdalene[132] | synth:venus[synth_9004] |
| christ[2] | christ[2] | synth:grail[synth_9000] |
| isis[3] | osiris[4] | synth:grail[synth_9000] |
| osiris[4] | osiris[4] | synth:grail[synth_9000] |
| earth star[5] | earth star[5] | synth:metatron[synth_9003] |
| temple doors[6] | temple doors[6] | synth:temple doors[synth_9001] |
| numis'om[7] | numis'om[7] | synth:numis'om[synth_9002] |
| ark[8] | grace[50] | synth:grail[synth_9000] |
| metatron[9] | metatron[9] | synth:metatron[synth_9003] |
| venus[10] | venus[10] | synth:venus[synth_9004] |
| orion[11] | orion[11] | synth:venus[synth_9004] |
| eye[12] | eye[12] | synth:metatron[synth_9003] |
| loch[13] | crystal[71] | synth:grail[synth_9000] |
| maia nartoomid[14] | lineages[41] | synth:grail[synth_9000] |
| god[15] | lord[114] | synth:grail[synth_9000] |
| doors[16] | doors[16] | synth:temple doors[synth_9001] |
| star lineages[17] | maia nartoomid[14] | synth:grail[synth_9000] |
| adam kadmon[18] | adam[70] | synth:venus[synth_9004] |
| new earth star[19] | new earth star[19] | synth:numis'om[synth_9002] |
| horus[20] | osiris[4] | synth:grail[synth_9000] |
| skull[21] | crystal[71] | synth:grail[synth_9000] |
| christic[22] | christic[22] | synth:grail[synth_9000] |
| inner earth[24] | central[75] | synth:grail[synth_9000] |
| blue star[25] | valley[121] | synth:grail[synth_9000] |
| dna[26] | dna[26] | synth:temple doors[synth_9001] |
| activation rite[27] | maia nartoomid[14] | synth:grail[synth_9000] |
| akashic practice[28] | rite akashic[51] | akashic practice[28] |
| pyramid[29] | temple of[52] | synth:grail[synth_9000] |
| templar[30] | lineages[41] | synth:grail[synth_9000] |
| great pyramid[32] | pyramid[29] | synth:grail[synth_9000] |
| ... | (105 more) | |

### medium, d=20.0 (124 shifts)

| Injected Node | Baseline Basin | Post-Jeans Basin |
|---------------|----------------|------------------|
| grail[1] | numis'om[7] | synth:venus[synth_9004] |
| christ[2] | christic[22] | synth:grail[synth_9000] |
| isis[3] | numis'om[7] | synth:grail[synth_9000] |
| osiris[4] | numis'om[7] | synth:grail[synth_9000] |
| earth star[5] | spirit heart[67] | synth:metatron[synth_9003] |
| temple doors[6] | merkabah[48] | synth:temple doors[synth_9001] |
| numis'om[7] | new earth star[19] | synth:numis'om[synth_9002] |
| ark[8] | christ[2] | synth:grail[synth_9000] |
| metatron[9] | numis'om[7] | synth:metatron[synth_9003] |
| venus[10] | maia christianne[136] | synth:venus[synth_9004] |
| orion[11] | christ[2] | synth:grail[synth_9000] |
| eye[12] | spirit heart[67] | synth:metatron[synth_9003] |
| loch[13] | christ[2] | synth:grail[synth_9000] |
| god[15] | christ[2] | synth:grail[synth_9000] |
| doors[16] | merkabah[48] | synth:temple doors[synth_9001] |
| adam kadmon[18] | numis'om[7] | synth:venus[synth_9004] |
| new earth star[19] | numis'om[7] | synth:numis'om[synth_9002] |
| horus[20] | temple doors[6] | synth:grail[synth_9000] |
| skull[21] | thothhorra khandr[138] | synth:grail[synth_9000] |
| christic[22] | christ[2] | synth:grail[synth_9000] |
| light codes[23] | numis'om[7] | synth:venus[synth_9004] |
| inner earth[24] | christ[2] | synth:grail[synth_9000] |
| blue star[25] | numis'om[7] | synth:grail[synth_9000] |
| dna[26] | merkabah[48] | synth:temple doors[synth_9001] |
| pyramid[29] | christ[2] | synth:grail[synth_9000] |
| great pyramid[32] | christ[2] | synth:grail[synth_9000] |
| johannine[33] | numis'om[7] | synth:grail[synth_9000] |
| crystal skull[34] | thothhorra khandr[138] | synth:grail[synth_9000] |
| mother[35] | christ[2] | synth:grail[synth_9000] |
| templa mar[36] | christ[2] | synth:grail[synth_9000] |
| ... | (94 more) | |

### medium_norm, d=0.2 (6 shifts)

| Injected Node | Baseline Basin | Post-Jeans Basin |
|---------------|----------------|------------------|
| loch[13] | temple of[52] | loch[13] |
| templa mar[36] | templa mar[36] | free information[106] |
| mari[73] | mari[73] | christic[22] |
| christine hayes[90] | christ[2] | christos[94] |
| simeon[98] | spirit heart[67] | simeon[98] |
| church[104] | christ[2] | temple of[52] |

### medium_norm, d=5.0 (33 shifts)

| Injected Node | Baseline Basin | Post-Jeans Basin |
|---------------|----------------|------------------|
| ark[8] | grace[50] | ark[8] |
| god[15] | lord[114] | god[15] |
| pyramid[29] | temple of[52] | pyramid[29] |
| mother[35] | goddess[91] | mother[35] |
| master[37] | master[37] | jesus[66] |
| pure gem[40] | gem[117] | pure gem[40] |
| flame[43] | rose[83] | flame[43] |
| atlantis[46] | atlantean[65] | atlantis[46] |
| grace[50] | ark[8] | grace[50] |
| lion[53] | lords[122] | lion[53] |
| matter[54] | prima matra[88] | matter[54] |
| sun[55] | the sun[101] | sun[55] |
| blood[57] | blood[57] | king[62] |
| old[61] | age[127] | old[61] |
| set[63] | set[63] | loch[13] |
| jesus[66] | jesus[66] | love[49] |
| tehuti[85] | tehuti[85] | yeshua[39] |
| prima matra[88] | dragon[124] | prima matra[88] |
| mystery school[89] | crystal skull[34] | thothhorra[31] |
| christine hayes[90] | christ[2] | knowledge[78] |
| plain[92] | thothhorra[31] | pyramid[29] |
| book[95] | lord[114] | book[95] |
| queen[97] | queen[97] | kyi[119] |
| simeon[98] | spirit heart[67] | simeon[98] |
| grid[99] | templa mar[36] | grid[99] |
| name[100] | name[100] | king[62] |
| lord[114] | lion[53] | thothhorra[31] |
| gem[117] | pure gem[40] | gem[117] |
| sirius[120] | sirius[120] | gate[42] |
| dragon[124] | prima matra[88] | dragon[124] |
| ... | (3 more) | |

### medium_norm, d=20.0 (4 shifts)

| Injected Node | Baseline Basin | Post-Jeans Basin |
|---------------|----------------|------------------|
| adam[70] | numis'om[7] | christ[2] |
| mysteries[84] | christ[2] | christos[94] |
| plain[92] | christ[2] | thothhorra khandr[138] |
| maia christianne[136] | venus[10] | new earth star[19] |

### mild, d=0.2 (22 shifts)

| Injected Node | Baseline Basin | Post-Jeans Basin |
|---------------|----------------|------------------|
| grail[1] | grail[1] | synth:grail[synth_9000] |
| loch[13] | temple of[52] | synth:grail[synth_9000] |
| adam kadmon[18] | metatronic[58] | adam kadmon[18] |
| horus[20] | merkabah[48] | horus[20] |
| great pyramid[32] | temple of[52] | great pyramid[32] |
| johannine[33] | free information[106] | johannine[33] |
| john[64] | christ[2] | synth:grail[synth_9000] |
| jesus[66] | christic[22] | jesus[66] |
| isis eye[72] | free information[106] | isis eye[72] |
| mari[73] | mari[73] | synth:grail[synth_9000] |
| par[79] | temple of[52] | synth:grail[synth_9000] |
| johannine grove[82] | temple of[52] | synth:grail[synth_9000] |
| mystery school[89] | temple of[52] | synth:grail[synth_9000] |
| christine hayes[90] | christ[2] | synth:grail[synth_9000] |
| plain[92] | metatronic[58] | synth:grail[synth_9000] |
| kadmon[96] | metatronic[58] | kadmon[96] |
| church[104] | christ[2] | synth:grail[synth_9000] |
| holorian[107] | ark[8] | synth:grail[synth_9000] |
| lord[114] | temple of[52] | synth:grail[synth_9000] |
| mazur[118] | metatronic[58] | synth:grail[synth_9000] |
| melchizedek[126] | metatronic[58] | synth:grail[synth_9000] |
| magdalene[132] | magdalene[132] | synth:grail[synth_9000] |

### mild, d=5.0 (140 shifts)

| Injected Node | Baseline Basin | Post-Jeans Basin |
|---------------|----------------|------------------|
| grail[1] | magdalene[132] | synth:grail[synth_9000] |
| christ[2] | christ[2] | synth:grail[synth_9000] |
| isis[3] | osiris[4] | synth:grail[synth_9000] |
| osiris[4] | osiris[4] | synth:grail[synth_9000] |
| earth star[5] | earth star[5] | synth:grail[synth_9000] |
| temple doors[6] | temple doors[6] | synth:grail[synth_9000] |
| numis'om[7] | numis'om[7] | synth:grail[synth_9000] |
| ark[8] | grace[50] | synth:grail[synth_9000] |
| metatron[9] | metatron[9] | synth:grail[synth_9000] |
| venus[10] | venus[10] | synth:grail[synth_9000] |
| orion[11] | orion[11] | synth:grail[synth_9000] |
| eye[12] | eye[12] | synth:grail[synth_9000] |
| loch[13] | crystal[71] | synth:grail[synth_9000] |
| maia nartoomid[14] | lineages[41] | synth:grail[synth_9000] |
| god[15] | lord[114] | synth:grail[synth_9000] |
| doors[16] | doors[16] | synth:grail[synth_9000] |
| star lineages[17] | maia nartoomid[14] | synth:grail[synth_9000] |
| adam kadmon[18] | adam[70] | synth:grail[synth_9000] |
| new earth star[19] | new earth star[19] | synth:grail[synth_9000] |
| horus[20] | osiris[4] | synth:grail[synth_9000] |
| skull[21] | crystal[71] | synth:grail[synth_9000] |
| christic[22] | christic[22] | synth:grail[synth_9000] |
| light codes[23] | light codes[23] | synth:grail[synth_9000] |
| inner earth[24] | central[75] | synth:grail[synth_9000] |
| blue star[25] | valley[121] | synth:grail[synth_9000] |
| dna[26] | dna[26] | synth:grail[synth_9000] |
| activation rite[27] | maia nartoomid[14] | synth:grail[synth_9000] |
| akashic practice[28] | rite akashic[51] | synth:grail[synth_9000] |
| pyramid[29] | temple of[52] | synth:grail[synth_9000] |
| templar[30] | lineages[41] | synth:grail[synth_9000] |
| ... | (110 more) | |

### mild, d=20.0 (124 shifts)

| Injected Node | Baseline Basin | Post-Jeans Basin |
|---------------|----------------|------------------|
| grail[1] | numis'om[7] | synth:grail[synth_9000] |
| christ[2] | christic[22] | synth:grail[synth_9000] |
| isis[3] | numis'om[7] | synth:grail[synth_9000] |
| osiris[4] | numis'om[7] | synth:grail[synth_9000] |
| earth star[5] | spirit heart[67] | synth:grail[synth_9000] |
| temple doors[6] | merkabah[48] | synth:grail[synth_9000] |
| numis'om[7] | new earth star[19] | synth:grail[synth_9000] |
| ark[8] | christ[2] | synth:grail[synth_9000] |
| metatron[9] | numis'om[7] | synth:grail[synth_9000] |
| venus[10] | maia christianne[136] | synth:grail[synth_9000] |
| orion[11] | christ[2] | synth:grail[synth_9000] |
| eye[12] | spirit heart[67] | synth:grail[synth_9000] |
| loch[13] | christ[2] | synth:grail[synth_9000] |
| god[15] | christ[2] | synth:grail[synth_9000] |
| doors[16] | merkabah[48] | synth:grail[synth_9000] |
| adam kadmon[18] | numis'om[7] | synth:grail[synth_9000] |
| new earth star[19] | numis'om[7] | synth:grail[synth_9000] |
| horus[20] | temple doors[6] | synth:grail[synth_9000] |
| skull[21] | thothhorra khandr[138] | synth:grail[synth_9000] |
| christic[22] | christ[2] | synth:grail[synth_9000] |
| light codes[23] | numis'om[7] | synth:grail[synth_9000] |
| inner earth[24] | christ[2] | synth:grail[synth_9000] |
| blue star[25] | numis'om[7] | synth:grail[synth_9000] |
| dna[26] | merkabah[48] | synth:grail[synth_9000] |
| pyramid[29] | christ[2] | synth:grail[synth_9000] |
| great pyramid[32] | christ[2] | synth:grail[synth_9000] |
| johannine[33] | numis'om[7] | synth:grail[synth_9000] |
| crystal skull[34] | thothhorra khandr[138] | synth:grail[synth_9000] |
| mother[35] | christ[2] | synth:grail[synth_9000] |
| templa mar[36] | christ[2] | synth:grail[synth_9000] |
| ... | (94 more) | |

### mild_norm, d=0.2 (1 shifts)

| Injected Node | Baseline Basin | Post-Jeans Basin |
|---------------|----------------|------------------|
| magdalene[132] | magdalene[132] | synth:grail[synth_9000] |

### mild_norm, d=5.0 (33 shifts)

| Injected Node | Baseline Basin | Post-Jeans Basin |
|---------------|----------------|------------------|
| grail[1] | magdalene[132] | synth:grail[synth_9000] |
| isis[3] | osiris[4] | isis[3] |
| ark[8] | grace[50] | ark[8] |
| god[15] | lord[114] | god[15] |
| pyramid[29] | temple of[52] | great pyramid[32] |
| mother[35] | goddess[91] | mother[35] |
| mystery[38] | mystery[38] | holorian[107] |
| pure gem[40] | gem[117] | pure gem[40] |
| flame[43] | rose[83] | flame[43] |
| atlantis[46] | atlantean[65] | atlantis[46] |
| grace[50] | ark[8] | grace[50] |
| lion[53] | lords[122] | lion[53] |
| matter[54] | prima matra[88] | matter[54] |
| sun[55] | the sun[101] | sun[55] |
| blood[57] | blood[57] | king[62] |
| old[61] | age[127] | old[61] |
| set[63] | set[63] | loch[13] |
| mysteries[84] | mysteries[84] | john[64] |
| prima matra[88] | dragon[124] | prima matra[88] |
| christine hayes[90] | christ[2] | knowledge[78] |
| plain[92] | thothhorra[31] | pyramid[29] |
| book[95] | lord[114] | book[95] |
| queen[97] | queen[97] | kyi[119] |
| simeon[98] | spirit heart[67] | simeon[98] |
| grid[99] | templa mar[36] | grid[99] |
| name[100] | name[100] | king[62] |
| gem[117] | pure gem[40] | gem[117] |
| sirius[120] | sirius[120] | gate[42] |
| lords[122] | lion[53] | lords[122] |
| dragon[124] | prima matra[88] | dragon[124] |
| ... | (3 more) | |

### mild_norm, d=20.0 (2 shifts)

| Injected Node | Baseline Basin | Post-Jeans Basin |
|---------------|----------------|------------------|
| adam[70] | numis'om[7] | christ[2] |
| plain[92] | christ[2] | thothhorra khandr[138] |

## Synth Nodes as Attractors

- **extreme, d=0.2**: 103 synth basin(s): synth_9000, synth_9001, synth_9002, synth_9003, synth_9004, synth_9005, synth_9006, synth_9007, synth_9008, synth_9009, synth_9010, synth_9011, synth_9013, synth_9015, synth_9016, synth_9017, synth_9018, synth_9021, synth_9022, synth_9023, synth_9024, synth_9025, synth_9026, synth_9027, synth_9028, synth_9029, synth_9030, synth_9031, synth_9034, synth_9035, synth_9036, synth_9037, synth_9038, synth_9039, synth_9040, synth_9041, synth_9042, synth_9043, synth_9044, synth_9045, synth_9046, synth_9048, synth_9049, synth_9050, synth_9051, synth_9052, synth_9053, synth_9054, synth_9055, synth_9056, synth_9057, synth_9058, synth_9059, synth_9060, synth_9061, synth_9062, synth_9063, synth_9064, synth_9065, synth_9066, synth_9067, synth_9068, synth_9069, synth_9070, synth_9071, synth_9072, synth_9073, synth_9074, synth_9075, synth_9076, synth_9077, synth_9078, synth_9079, synth_9080, synth_9081, synth_9082, synth_9083, synth_9084, synth_9085, synth_9086, synth_9087, synth_9088, synth_9089, synth_9090, synth_9091, synth_9092, synth_9093, synth_9094, synth_9095, synth_9096, synth_9098, synth_9100, synth_9101, synth_9102, synth_9103, synth_9105, synth_9106, synth_9117, synth_9120, synth_9129, synth_9130, synth_9131, synth_9135
- **extreme, d=5.0**: 140 synth basin(s): synth_9000, synth_9001, synth_9002, synth_9003, synth_9004, synth_9005, synth_9006, synth_9007, synth_9008, synth_9009, synth_9010, synth_9011, synth_9012, synth_9013, synth_9014, synth_9015, synth_9016, synth_9017, synth_9018, synth_9019, synth_9020, synth_9021, synth_9022, synth_9023, synth_9024, synth_9025, synth_9026, synth_9027, synth_9028, synth_9029, synth_9030, synth_9031, synth_9032, synth_9033, synth_9034, synth_9035, synth_9036, synth_9037, synth_9038, synth_9039, synth_9040, synth_9041, synth_9042, synth_9043, synth_9044, synth_9045, synth_9046, synth_9047, synth_9048, synth_9049, synth_9050, synth_9051, synth_9052, synth_9053, synth_9054, synth_9055, synth_9056, synth_9057, synth_9058, synth_9059, synth_9060, synth_9061, synth_9062, synth_9063, synth_9064, synth_9065, synth_9066, synth_9067, synth_9068, synth_9069, synth_9070, synth_9071, synth_9072, synth_9073, synth_9074, synth_9075, synth_9076, synth_9077, synth_9078, synth_9079, synth_9080, synth_9081, synth_9082, synth_9083, synth_9084, synth_9085, synth_9086, synth_9087, synth_9088, synth_9089, synth_9090, synth_9091, synth_9092, synth_9093, synth_9094, synth_9095, synth_9096, synth_9097, synth_9098, synth_9099, synth_9100, synth_9101, synth_9102, synth_9103, synth_9104, synth_9105, synth_9106, synth_9107, synth_9108, synth_9109, synth_9110, synth_9111, synth_9112, synth_9113, synth_9114, synth_9115, synth_9116, synth_9117, synth_9118, synth_9119, synth_9120, synth_9121, synth_9122, synth_9123, synth_9124, synth_9125, synth_9126, synth_9127, synth_9128, synth_9129, synth_9130, synth_9131, synth_9132, synth_9133, synth_9134, synth_9135, synth_9136, synth_9137, synth_9138, synth_9139
- **extreme, d=20.0**: 140 synth basin(s): synth_9000, synth_9001, synth_9002, synth_9003, synth_9004, synth_9005, synth_9006, synth_9007, synth_9008, synth_9009, synth_9010, synth_9011, synth_9012, synth_9013, synth_9014, synth_9015, synth_9016, synth_9017, synth_9018, synth_9019, synth_9020, synth_9021, synth_9022, synth_9023, synth_9024, synth_9025, synth_9026, synth_9027, synth_9028, synth_9029, synth_9030, synth_9031, synth_9032, synth_9033, synth_9034, synth_9035, synth_9036, synth_9037, synth_9038, synth_9039, synth_9040, synth_9041, synth_9042, synth_9043, synth_9044, synth_9045, synth_9046, synth_9047, synth_9048, synth_9049, synth_9050, synth_9051, synth_9052, synth_9053, synth_9054, synth_9055, synth_9056, synth_9057, synth_9058, synth_9059, synth_9060, synth_9061, synth_9062, synth_9063, synth_9064, synth_9065, synth_9066, synth_9067, synth_9068, synth_9069, synth_9070, synth_9071, synth_9072, synth_9073, synth_9074, synth_9075, synth_9076, synth_9077, synth_9078, synth_9079, synth_9080, synth_9081, synth_9082, synth_9083, synth_9084, synth_9085, synth_9086, synth_9087, synth_9088, synth_9089, synth_9090, synth_9091, synth_9092, synth_9093, synth_9094, synth_9095, synth_9096, synth_9097, synth_9098, synth_9099, synth_9100, synth_9101, synth_9102, synth_9103, synth_9104, synth_9105, synth_9106, synth_9107, synth_9108, synth_9109, synth_9110, synth_9111, synth_9112, synth_9113, synth_9114, synth_9115, synth_9116, synth_9117, synth_9118, synth_9119, synth_9120, synth_9121, synth_9122, synth_9123, synth_9124, synth_9125, synth_9126, synth_9127, synth_9128, synth_9129, synth_9130, synth_9131, synth_9132, synth_9133, synth_9134, synth_9135, synth_9136, synth_9137, synth_9138, synth_9139
- **extreme_norm, d=0.2**: 49 synth basin(s): synth_9002, synth_9003, synth_9004, synth_9005, synth_9006, synth_9007, synth_9008, synth_9015, synth_9016, synth_9021, synth_9024, synth_9027, synth_9042, synth_9044, synth_9046, synth_9048, synth_9050, synth_9052, synth_9055, synth_9056, synth_9058, synth_9061, synth_9062, synth_9063, synth_9065, synth_9066, synth_9067, synth_9070, synth_9072, synth_9073, synth_9074, synth_9078, synth_9079, synth_9080, synth_9082, synth_9083, synth_9084, synth_9088, synth_9089, synth_9100, synth_9101, synth_9102, synth_9103, synth_9105, synth_9112, synth_9117, synth_9120, synth_9122, synth_9127
- **extreme_norm, d=5.0**: 114 synth basin(s): synth_9000, synth_9004, synth_9005, synth_9006, synth_9007, synth_9008, synth_9009, synth_9010, synth_9011, synth_9012, synth_9013, synth_9014, synth_9015, synth_9016, synth_9017, synth_9018, synth_9019, synth_9020, synth_9021, synth_9023, synth_9024, synth_9025, synth_9026, synth_9027, synth_9028, synth_9029, synth_9030, synth_9031, synth_9032, synth_9033, synth_9034, synth_9035, synth_9036, synth_9037, synth_9038, synth_9039, synth_9040, synth_9041, synth_9042, synth_9043, synth_9044, synth_9045, synth_9046, synth_9047, synth_9048, synth_9050, synth_9051, synth_9052, synth_9053, synth_9054, synth_9055, synth_9056, synth_9057, synth_9058, synth_9059, synth_9060, synth_9061, synth_9062, synth_9063, synth_9064, synth_9065, synth_9066, synth_9068, synth_9069, synth_9070, synth_9071, synth_9072, synth_9073, synth_9074, synth_9075, synth_9076, synth_9077, synth_9078, synth_9079, synth_9080, synth_9081, synth_9082, synth_9083, synth_9084, synth_9085, synth_9086, synth_9087, synth_9088, synth_9090, synth_9091, synth_9092, synth_9093, synth_9094, synth_9096, synth_9097, synth_9098, synth_9100, synth_9101, synth_9102, synth_9103, synth_9104, synth_9105, synth_9114, synth_9115, synth_9117, synth_9120, synth_9121, synth_9122, synth_9123, synth_9124, synth_9126, synth_9127, synth_9128, synth_9134, synth_9135, synth_9136, synth_9137, synth_9138, synth_9139
- **medium, d=0.2**: 4 synth basin(s): synth_9000, synth_9001, synth_9002, synth_9004
- **medium, d=5.0**: 5 synth basin(s): synth_9000, synth_9001, synth_9002, synth_9003, synth_9004
- **medium, d=20.0**: 5 synth basin(s): synth_9000, synth_9001, synth_9002, synth_9003, synth_9004
- **medium_norm, d=5.0**: 1 synth basin(s): synth_9002
- **mild, d=0.2**: 1 synth basin(s): synth_9000
- **mild, d=5.0**: 1 synth basin(s): synth_9000
- **mild, d=20.0**: 1 synth basin(s): synth_9000
- **mild_norm, d=0.2**: 1 synth basin(s): synth_9000
- **mild_norm, d=5.0**: 1 synth basin(s): synth_9000

## Observations

*(To be filled after analysis)*

## Exports
- `baseline_basins.csv` - baseline probe results
- `post_jeans_basins.csv` - post-Jeans probe results
- `comparison_summary.csv` - condition x damping comparison
- `basin_jeans_stability_run_bundle.md` - this file