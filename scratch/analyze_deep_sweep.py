import json
import numpy as np
from pathlib import Path

results_path = Path("solResearch/nextBestTest/fractal_deep_sweep_results.json")
with open(results_path, "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"Total Trials Parsed: {len(data)}")

# 1. Find configurations with positive decay rates (meaningful decay fitting)
valid_decays = [r for r in data if r["fmsm"]["decay_rate"] > 0]
print(f"Trials with valid positive decay rates in FMSM: {len(valid_decays)}")

# 2. Resonance Analysis: Group by frequency and average SNR
freq_groups = {}
for r in data:
    f = r["frequency"]
    if f not in freq_groups:
        freq_groups[f] = []
    freq_groups[f].append(r["fmsm"]["snr_active"])
    
print("\n--- FREQUENCY RESPONSE (FMSM Average Active SNR) ---")
for f in sorted(freq_groups.keys()):
    avg_snr = np.mean(freq_groups[f])
    print(f"  Freq {f:.2f} rad/s: Avg SNR = {avg_snr:.2f}")

# 3. Linearity Analysis: Group by amplitude and average mixer active amplitude
amp_groups = {}
for r in data:
    a = r["amplitude"]
    if a not in amp_groups:
        amp_groups[a] = []
    amp_groups[a].append(r["fmsm"]["mixer_amp_active"])
    
print("\n--- LINEARITY RESPONSE (FMSM Mixer Amplitude vs Input Amplitude) ---")
for a in sorted(amp_groups.keys()):
    avg_mixer_amp = np.mean(amp_groups[a])
    ratio = avg_mixer_amp / a
    print(f"  Input Amp {a:.2f}: Avg Mixer Amp = {avg_mixer_amp:.2f} (Ratio = {ratio:.4f})")

# 4. Persistence Analysis: Group by damping and find trials with valid decays
damp_decays = {}
for r in data:
    d = r["damping"]
    if d not in damp_decays:
        damp_decays[d] = []
    damp_decays[d].append(r["fmsm"]["decay_rate"])
    
print("\n--- DAMPING RESPONSE (FMSM Decay Rates) ---")
for d in sorted(damp_decays.keys()):
    all_decays = damp_decays[d]
    positive_decays = [v for v in all_decays if v > 0]
    negative_decays = [v for v in all_decays if v < 0]
    zero_decays = [v for v in all_decays if v == 0]
    print(f"  Damping {d:.2f}: Positive={len(positive_decays)}, Negative={len(negative_decays)}, Zero={len(zero_decays)} | Mean Positive Decay = {np.mean(positive_decays) if positive_decays else 0.0:.4f}")

# 5. Let's look at the negative decay trials: where do they cluster?
neg_trials = [r for r in data if r["fmsm"]["decay_rate"] < 0]
print(f"\nTotal negative decay trials: {len(neg_trials)}")
freq_neg = {}
for r in neg_trials:
    f = r["frequency"]
    freq_neg[f] = freq_neg.get(f, 0) + 1
print("Negative decay distribution by frequency:")
for f in sorted(freq_neg.keys()):
    print(f"  Freq {f:.2f}: {freq_neg[f]} occurrences")
