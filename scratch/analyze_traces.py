# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
import numpy as np
import pandas as pd
from pathlib import Path

def analyze_file(csv_path):
    df = pd.read_csv(csv_path)
    # Focus on the last 150 ticks (steady state limit cycle)
    df_ss = df.iloc[-150:]
    
    # Calculate correlations
    corr_node_ke = df_ss['num_nodes'].corr(df_ss['kinetic_energy'])
    corr_node_pe = df_ss['num_nodes'].corr(df_ss['potential_energy'])
    corr_node_mass = df_ss['num_nodes'].corr(df_ss['total_mass'])
    
    # Standard deviation of metrics
    std_nodes = df_ss['num_nodes'].std()
    std_mass = df_ss['total_mass'].std()
    std_ke = df_ss['kinetic_energy'].std()
    
    # Mean of metrics
    mean_nodes = df_ss['num_nodes'].mean()
    mean_mass = df_ss['total_mass'].mean()
    mean_ke = df_ss['kinetic_energy'].mean()
    mean_pe = df_ss['potential_energy'].mean()
    mean_te = df_ss['total_energy'].mean()
    
    # Log variance of density
    mean_var_rho = df_ss['mass_variance'].mean()
    
    print(f"File: {csv_path.name}")
    print(f"  Mean Nodes: {mean_nodes:.1f} (std: {std_nodes:.2f})")
    print(f"  Mean Mass: {mean_mass:.2f} (std: {std_mass:.2f})")
    print(f"  Mean KE: {mean_ke:.2e} (std: {std_ke:.2e})")
    print(f"  Mean PE: {mean_pe:.2e}")
    print(f"  Mean TE: {mean_te:.2e}")
    print(f"  Mean Density Variance: {mean_var_rho:.4f}")
    print(f"  Correlations with Node Count:")
    print(f"    Node-KE Corr: {corr_node_ke:.4f}")
    print(f"    Node-PE Corr: {corr_node_pe:.4f}")
    print(f"    Node-Mass Corr: {corr_node_mass:.4f}")
    print()

def main():
    sol_root = Path(__file__).resolve().parents[1]
    data_dir = sol_root / "data"
    
    analyze_file(data_dir / "breathing_trace_50.csv")
    analyze_file(data_dir / "breathing_trace_150.csv")

if __name__ == "__main__":
    main()
