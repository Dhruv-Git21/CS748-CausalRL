# Results Framework (v2)

## Overview

This document explains how to **read, interpret, and compare** experimental results in v2.

---

## Output Directory Structure

After running experiments, you'll have:

```
results/
├── figures/
│   ├── exp_01_ope_value_scatter.png
│   ├── exp_01_ranking_comparison.png
│   ├── exp_02_importance_weights_hist.png
│   ├── exp_02_ess_by_policy.png
│   ├── exp_03_pool_a_win_matrix.png
│   ├── exp_03_pool_b_win_matrix.png
│   ├── exp_03_rank_correlation.png
│   ├── exp_04_cycle_network.png
│   ├── exp_05_pareto_front.png
│   ├── exp_05_survivor_stability.png
│   └── summary_all_experiments.png
│
├── data/
│   ├── exp_01_metadata.json
│   ├── exp_02_metadata.json
│   ├── exp_03_metadata.json
│   ├── exp_04_metadata.json
│   ├── exp_05_metadata.json
│   ├── exp_01_raw_data.json       (optional: full trajectories)
│   ├── exp_02_raw_data.json
│   └── summary_stats.json          (aggregated metrics)
│
└── logs/
    ├── exp_01.log
    ├── exp_02.log
    ├── exp_03.log
    ├── exp_04.log
    ├── exp_05.log
    └── run_all_experiments.log
```

---

## Metadata File Format

Each experiment produces a metadata JSON file. Example:

```json
{
  "experiment": "exp_01_ope_works",
  "seed": 42,
  "timestamp": "2026-03-04T14:30:45Z",
  "parameters": {
    "env_type": "gridworld",
    "grid_size": 5,
    "slip_probability": 0.0,
    "num_policies": 3,
    "num_trajectories": 5000,
    "trajectory_length": 50,
    "gamma": 0.99
  },
  "ope_estimators": ["IS", "WIS", "PDIS"],
  "results": {
    "spearman_rho_is": 0.924,
    "spearman_rho_wis": 0.918,
    "spearman_rho_pdis": 0.911,
    "top1_mismatch_is": false,
    "top1_mismatch_wis": false,
    "top1_mismatch_pdis": false,
    "ess_fraction": 0.95,
    "mse_is": 0.045,
    "mse_wis": 0.052,
    "mse_pdis": 0.038
  },
  "key_findings": "OPE ranking correlates well with true ranking when behavior policy covers evaluation policy. All three estimators (IS/WIS/PDIS) agree.",
  "failure_modes": "None — OPE works well in this setting.",
  "notes": "This is the 'easy case' of OPE."
}
```

---

## Key Metrics Explained

### Spearman Rank Correlation (ρ)
**Definition**: Correlation between two rankings (OPE rank vs. true rank)

**Formula**: 
```
ρ = 1 - (6 * Σ d_i^2) / (n(n²-1))
```
where `d_i` = difference in rank for policy i, `n` = number of policies

**Interpretation**:
- **ρ ≈ 1.0**: Perfect agreement (same ranking order)
- **ρ ≈ 0.7+**: Good agreement (top policies match)
- **ρ ≈ 0.0**: No correlation (random disagreement)
- **ρ < 0.0**: Anti-correlation (opposite order)

**In Context**:
- Exp 1: expect ρ > 0.9
- Exp 2: expect ρ < 0.4
- Exp 3: expect ρ drops from ~0.8 to ~0.3

---

### Top-1 Mismatch
**Definition**: Boolean flag: True if OPE picks a different best policy than ground truth

**Interpretation**:
- **False**: Same best policy (good)
- **True**: Different best policy (bad — worst case of ranking failure)

**In Context**:
- Exp 1: expect always False
- Exp 2: expect often True
- Exp 3: expect True under opponent shift

---

### Effective Sample Size (ESS)
**Definition**: How many "effective" i.i.d. samples do we have after importance weighting?

**Formula** (for Weighted IS):
```
ESS = (Σ w_i)² / Σ w_i²
```

**Interpretation**:
- **ESS ≈ N**: All samples equally important (good coverage)
- **ESS ≈ N/10**: Only 10% of samples matter (poor coverage)
- **ESS ≈ 1**: Only one sample matters (catastrophic failure)

**Fraction**: Often reported as `ESS / N ∈ [0, 1]`
- Exp 1: expect ESS/N ≈ 0.95
- Exp 2: expect ESS/N ≈ 0.05
- Exp 3: less relevant (multi-agent tournaments, not importance weighting)

---

### Mean Squared Error (MSE)
**Definition**: Average squared difference between OPE estimate and true value

**Formula**:
```
MSE = (1/n) Σ (ŷ_i - y_i)²
```

**Interpretation**:
- **Small MSE** (< 0.1): Accurate estimates
- **Large MSE** (> 1.0): Inaccurate estimates
- **Relative increase**: Compare MSE before/after shift

**In Context**:
- Exp 1: expect MSE ≈ 0.04
- Exp 2: expect MSE >> Exp 1 (by 10x or more)

---

### Kendall's τ (Tau)
**Definition**: Rank correlation accounting for inversions (used in Exp 4)

**Interpretation**:
- **τ ≈ 1.0**: Perfect ranking agreement
- **τ ≈ 0.0**: Random ranking
- **τ < 0.0**: Reversed ranking
- **0 < τ < 0.5**: Consistent but with cycles

**In Context**:
- Exp 4: expect τ << 1, indicating cycles

---

## Reading the Plots

### Plot Type 1: Scatter (OPE vs. True)
**Used in**: Exp 1, 2, 3

```
y-axis: Ground Truth Value
^
|     /  ← y = x (perfect line)
|    /
|   /
|  /
| /
|/ _______ x-axis: OPE Estimate
|
```

**What to look for**:
- **Points on diagonal**: Good (OPE matches truth)
- **Points above diagonal**: OPE underestimates
- **Points below diagonal**: OPE overestimates
- **Wide scatter**: High variance, unreliable
- **Outliers**: Catastrophic failures

**Good scatter** (Exp 1):
- All points close to y=x line
- Tight cluster, no outliers
- ρ > 0.9

**Bad scatter** (Exp 2):
- Points far from line
- Heavy outliers above/below
- Wide spread
- ρ < 0.4

---

### Plot Type 2: Bar Chart (Ranking Comparison)
**Used in**: Exp 1, 3

```
5 |     T    O
4 |     T    O
3 | O   T    O
2 | O   T    O
1 | T  OO    T
  |_________________________
    Pol_A Pol_B Pol_C

T = True rank, O = OPE rank
```

**What to look for**:
- **T and O at same height**: Correct ranking
- **T and O at different heights**: Ranking mismatch
- **Columns far apart**: Major disagreement

**Good ranking** (Exp 1):
- T and O align perfectly
- All mismatches < 1 position
- Top policy T and O overlap

**Bad ranking** (Exp 3 under shift):
- T and O completely different
- Top policy flips between experiments
- Spearman ρ << 1

---

### Plot Type 3: Heatmap (Win Matrix)
**Used in**: Exp 3, 4

```
        Policy 0  Policy 1  Policy 2
Policy 0   [?]     0.2       0.9
Policy 1   0.8     [?]       0.3
Policy 2   0.1     0.7       [?]
```

**What to look for**:
- **Symmetry**: (i,j) + (j,i) ≈ 1 (they play each other)
- **Dark cells**: Policy row wins often
- **Light cells**: Policy row loses often
- **Patterns**: Are same policies dominant in both matrices (Exp 3)?

**Pool A vs. Pool B** (Exp 3):
- Matrix A: Policy 0 (Rock) is dark in one column (beats many)
- Matrix B: Policy 2 (Scissors) is dark in same column (beats many)
- Conclusion: Opponent shift changes which policies win

---

### Plot Type 4: Network Graph (Cycles)
**Used in**: Exp 4

```
   Rock
   ↙  ↘
Paper   Scissors
   ↖  ↗
(Rock beats Scissors → Paper beats Rock → Scissors beats Paper)
```

**What to look for**:
- **Directed edges**: A → B means A beats B
- **Cycles**: Closed loops (A → B → C → A)
- **Strongly connected components**: Tightly connected groups of policies

**Acyclic** (perfect ranking exists):
- All edges point in one direction (top to bottom)
- No cycles

**Cyclic** (no valid total order):
- At least one cycle exists
- Kendall τ will be low

---

### Plot Type 5: Pareto Front
**Used in**: Exp 5

```
Robustness (y-axis)
^
|  ●  ← Pareto-optimal
|   ● ●  ← Interior (dominated)
|     ●  ← Pareto-optimal
|       ●  ← Pareto-optimal
|
+------ Mean Payoff (x-axis)
```

**What to look for**:
- **Points on the upper-right frontier**: Pareto-optimal (non-dominated)
- **Points in the interior**: Dominated (strictly worse)
- **Size of Pareto front**: Trade-off between objectives
- **Labeled names**: Which policies survive?

**Robust Pareto** (Exp 5):
- Front is stable across two plots (Pool A vs. Pool B)
- Same policies appear in both fronts
- Conclusion: Pareto set is robust to opponent shift

**Fragile ranking** (for comparison):
- Top-1 policy changes between pools
- Interior policies move to frontier
- Conclusion: Ranking is not robust

---

## Comparative Analysis

### Comparing Experiments

**Setup**: Run all 5 experiments, then compare outputs:

```bash
python experiments/run_all_experiments.py
```

**Comparison Matrix**:

| Metric | Exp 1 | Exp 2 | Exp 3 | Exp 4 | Exp 5 |
|--------|-------|-------|-------|-------|-------|
| Spearman ρ (same pool) | 0.92 | 0.92 | 0.80 | N/A | N/A |
| Spearman ρ (different pool) | N/A | 0.92 | 0.30 | N/A | N/A |
| Top-1 mismatch (same pool) | No | No | No | N/A | No |
| Top-1 mismatch (diff pool) | N/A | No | **Yes** | N/A | No |
| ESS / N | 0.95 | 0.05 | N/A | N/A | N/A |
| Pareto front stable? | N/A | N/A | N/A | N/A | **Yes** |
| Cycles exist? | No | No | No | **Yes** | No |

**Key Observations**:
1. Exp 1 & 2: Same method, different coverage → OPE reliability depends on coverage
2. Exp 2 & 3: Different domains (single vs. multi-agent) → Both exhibit failures
3. Exp 4: Proves impossibility of total ordering
4. Exp 5: Shows Pareto sets are more stable than rankings

---

## Aggregated Metrics

The `summary_stats.json` file summarizes all experiments:

```json
{
  "timestamp": "2026-03-04T14:45:00Z",
  "experiments": {
    "exp_01": {
      "status": "success",
      "key_metric": "spearman_rho = 0.924",
      "interpretation": "OPE works well"
    },
    "exp_02": {
      "status": "success",
      "key_metric": "spearman_rho = 0.182",
      "interpretation": "OPE fails under shift"
    },
    "exp_03": {
      "status": "success",
      "key_metric": "pool_a_rho = 0.802, pool_b_rho = 0.291",
      "interpretation": "Opponent shift flips ranks"
    },
    "exp_04": {
      "status": "success",
      "key_metric": "cycles_found = 1",
      "interpretation": "No valid total order"
    },
    "exp_05": {
      "status": "success",
      "key_metric": "pareto_stable = true",
      "interpretation": "Dominance is robust"
    }
  },
  "overall_narrative": "OPE ranking fails due to (1) distribution shift, (2) opponent shift in multi-agent, and (3) non-transitivity. Dominance-based methods are more robust."
}
```

---

## Reproducing + Comparing

### Same Seed, Same Results
```bash
# First run
python experiments/run_all_experiments.py
cp -r results results_run1

# Second run (same seed)
rm -rf results
python experiments/run_all_experiments.py
cp -r results results_run2

# Compare (should be identical)
diff results_run1/figures results_run2/figures  # Should be empty
diff results_run1/data results_run2/data        # Should be identical JSON
```

### Different Hyperparameters
Edit an experiment:
```python
# exp_01_ope_works.py
N = 10000  # was 5000
```

Re-run and compare:
```bash
python experiments/exp_01_ope_works.py
# Check if Spearman ρ improved with more samples
```

---

## Statistical Interpretation

### Significance of Differences

**When comparing two Spearman correlations**:

- Difference > 0.3: Likely significant (large effect)
- Difference 0.1–0.3: Moderate effect
- Difference < 0.1: Small effect (might be noise)

**Example**: Exp 3 with opponent shift
- Pool A: ρ = 0.80
- Pool B: ρ = 0.30
- Difference: 0.50 (very large) → **definitely significant**

### Confidence in Results

- **Single run with seed**: No confidence intervals (deterministic)
- **Multiple runs with different seeds**: Can compute std dev of metrics

To estimate uncertainty:

```python
# Run same experiment with different seeds
metrics = []
for seed in [42, 123, 456]:
    # Run exp_01 with this seed
    metrics.append(spearman_rho)

mean_rho = np.mean(metrics)
std_rho = np.std(metrics)
print(f"Spearman ρ = {mean_rho:.3f} ± {std_rho:.3f}")
```

---

## Exporting Results

### For a Report
```bash
# Copy figures to your report folder
cp results/figures/*.png ~/my_report/figures/

# Copy metadata for citations
cp results/data/summary_stats.json ~/my_report/data/
```

### For a Presentation
1. Open `results/figures/` in a file explorer
2. Drag PNG files into your slides
3. Use the metadata JSON to populate tables/captions

### For a Paper
1. Use high-DPI figures (saved at 300 DPI by default)
2. Cite the metadata JSON in supplementary materials
3. Include experimental details (seed, hyperparameters) in caption

---

## Troubleshooting Results

### Problem: All Spearman ρ values are very low
**Possible causes**:
1. Seed wasn't set → experiment is random each time
2. Sample size N too small → high variance
3. Environment/policy setup is wrong → no meaningful signal

**Fix**:
1. Check `set_seed(seed)` is called first in script
2. Increase N in metadata
3. Run a simple sanity check (e.g., OPE of optimal policy should be highest)

### Problem: Scatter plot shows outliers
**Possible causes**:
1. A few policies have degenerate importance weights
2. Clipping threshold too high or not set
3. Rare events in trajectories

**Fix**:
1. Check ESS for affected policies
2. Try `clip=10.0` or `clip=5.0`
3. Inspect raw data JSON for trajectory lengths

### Problem: Plots look different than expected
**Possible causes**:
1. Hyperparameters changed from defaults
2. Environment config different (e.g., slip=0.2 vs. 0.0)
3. Policy zoo changed

**Fix**:
1. Check metadata JSON for parameter values
2. Re-run with defaults from docs
3. Compare with example results from ACHIEVEMENTS.md

---

## See Also

- [ACHIEVEMENTS.md](ACHIEVEMENTS.md) — What was done
- [EXPERIMENT_GUIDE.md](EXPERIMENT_GUIDE.md) — How to run experiments
- [ARCHITECTURE.md](ARCHITECTURE.md) — How code is organized

