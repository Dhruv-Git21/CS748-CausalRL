# Experiment Guide (v2)

This document explains how to understand, run, and interpret each of the v2 experiments.

---

## Quick Start

```bash
# Run all experiments (generates figures + data)
python experiments/run_all_experiments.py

# Run a single experiment
python experiments/exp_01_ope_works.py
```

All outputs go to `results/figures/` (plots) and `results/data/` (metadata/data).

---

## Experiments Explained

### Experiment 1: OPE Works (Good Coverage)
**File**: `exp_01_ope_works.py`

**Research Question**: Does OPE ranking correlate with true rollout ranking when the behavior policy has good coverage?

**Hypothesis**: When behavior policy ≈ evaluation policy, IS/WIS estimates should rank policies correctly.

**Methods**:
- Single-agent Gridworld (5×5 grid, goal at corner)
- Create 3 policies: random, ε-greedy (ε=0.5), ε-greedy (ε=0.1)
- Collect N=5000 trajectories under "good" behavior policy (covers all policies)
- Estimate value of each policy using IS, WIS, PDIS
- Compare OPE ranking vs. ground truth rollout ranking
- Compute Spearman rank correlation

**Expected Outputs**:
- Figure: Correlation plot (OPE value vs. true value) — should be tight scatter
- Figure: Rank bar chart (OPE rank vs. true rank) — should match
- Metric: Spearman ρ ≈ 0.9+ (strong correlation)
- Metric: Top-1 mismatch = 0 (same best policy)

**Key Insight**: OPE *can* work well when coverage is good. This is the "easy case."

---

### Experiment 2: OPE Fails (Distribution Shift)
**File**: `exp_02_ope_fails_shift.py`

**Research Question**: What happens to OPE when behavior policy has poor coverage (support mismatch)?

**Hypothesis**: When behavior policy is very different from evaluation policy, importance weights become degenerate (heavy-tailed, high variance), and OPE estimates collapse.

**Methods**:
- Single-agent Gridworld (same as Exp 1)
- Use a deliberately bad behavior policy (e.g., always move right)
- Collect trajectories under bad behavior policy
- Compute importance weights for each evaluation policy
- Plot histogram of weights (show heavy tails)
- Compute Effective Sample Size (ESS) — should collapse
- Estimate values and compare to true values
- Compute rank correlation — should drop significantly

**Expected Outputs**:
- Figure: Histogram of importance weights (log scale) — shows heavy tails
- Figure: ESS vs. policy (bar chart) — all policies have low ESS
- Figure: OPE value vs. true value (scatter) — loose, with outliers
- Figure: Rank correlation (before/after shift) — drops from ~0.9 to ~0.3
- Metric: MSE increases by 10x or more
- Metric: Top-1 mismatch often occurs

**Key Insight**: Distribution shift breaks OPE through importance weight degeneracy. This is a fundamental challenge in offline RL.

---

### Experiment 3: Opponent Shift (Multi-Agent)
**File**: `exp_03_opponent_shift.py`

**Research Question**: In multi-agent settings, does OPE ranking break when the opponent pool changes?

**Hypothesis**: OPE estimates a policy's value against opponent pool A. When deployed against pool B, the policy ordering can flip — even though OPE had high confidence in its ranking.

**Methods**:
- Rock-Paper-Scissors game (3 policies per player)
- Create 2 opponent pools:
  - **Pool A** (training): mostly Rock players
  - **Pool B** (deployment): mostly Scissors players
- Collect data: play agent policies against Pool A
- Estimate each policy's value using OPE (IS/WIS)
- Rank policies by OPE estimate
- Play tournament: evaluate each policy against Pool B
- Rank policies by true tournament results
- Compare ranks (should mismatch)

**Expected Outputs**:
- Figure: OPE value vs. true value (colored by opponent pool) — will show two clusters
- Figure: Rank correlation (pool A vs. pool B) — should be poor (ρ < 0.5)
- Figure: Win matrix heatmap (pool A vs. pool B) — visually different
- Metric: Top-1 mismatch often occurs
- Metric: Spearman ρ drops from ~0.8 (vs. pool A) to ~0.3 (vs. pool B)

**Key Insight**: Multi-agent introduces opponent shift as a new failure mode beyond distribution shift. The same policy can be best against one opponent pool and worst against another.

---

### Experiment 4: Non-Transitivity (Cyclic Dominance)
**File**: `exp_04_nontransitivity.py`

**Research Question**: Is there a global ranking, or do cycles exist (A > B, B > C, C > A)?

**Hypothesis**: In multi-agent games, non-transitive relationships exist, making a single total ordering impossible.

**Methods**:
- Rock-Paper-Scissors or custom designed payoff matrix
- Create policy zoo (≥5 policies)
- Play full tournament: all pairs, both perspectives
- Construct pairwise win matrix W[i,j] = P(pi_i beats pi_j)
- Look for cycles: i > j, j > k, k > i
- Compute Kendall tau or other rank-invariant metrics
- Visualize as directed graph

**Expected Outputs**:
- Figure: Win matrix heatmap (with diagonal = 0.5 by symmetry)
- Figure: Directed graph showing cycles (cycles highlighted in red)
- Figure: Pareto front in 2D (if applicable)
- Metric: Kendall tau << 1 (inconsistent rankings)
- Metric: Number of cycles found

**Key Insight**: Cycles prove that a single scalar ranking is fundamentally fragile. Different aggregation methods (average, pairwise) can give conflicting answers.

---

### Experiment 5: Dominance-Based Evaluation is Robust
**File**: `exp_05_dominance_robust.py`

**Research Question**: Can dominance-based methods (Pareto, maximin) provide a more robust alternative to ranking-based selection?

**Hypothesis**: Dominance sets are **smaller** than total rankings but **more robust** to opponent shift and non-transitivity.

**Methods**:
- Use the same Rock-Paper-Scissors setup from Exp 3
- Compute policy payoffs against multiple opponent pools
- Extract Pareto front in (mean payoff, robustness) space
- Compute maximin robustness score for each policy
- Compare:
  - **Ranking-based**: top-1 policy, top-3 policies
  - **Dominance-based**: Pareto front, maximin survivors
- Evaluate on test opponent pool
- Measure stability (do survivors change with opponent pool?)

**Expected Outputs**:
- Figure: Pareto front (mean vs. robustness, with policy names)
- Figure: Comparison table: ranking survivors vs. dominance survivors
- Figure: Robustness heatmap (policy vs. opponent pool) — Pareto set stable
- Metric: Survivor stability: % of Pareto front policies remaining across pools
- Metric: Top-1 churn: % of time #1 ranking changes (high), Pareto front changes (low)

**Key Insight**: Dominance-based selection sacrifices a total ordering for **robustness**. The Pareto front is smaller but doesn't flip unexpectedly under opponent shift.

---

## How to Interpret Results

### Reading the Plots

#### **Scatter Plots (Value Estimates)**
- **X-axis**: OPE estimate
- **Y-axis**: Ground truth (rollout or tournament result)
- **Good**: Points lie on the y=x diagonal, tight cluster
- **Bad**: Points scattered, heavy outliers, far from diagonal

#### **Heatmaps (Win Matrices)**
- **[i,j]**: win rate of policy i vs. policy j
- **Diagonal = 0.5**: symmetric games
- **Dark = wins, Light = losses**
- Compare 2 heatmaps to see opponent shift effect

#### **Bar Charts (Rankings)**
- **X-axis**: Policy name or index
- **Y-axis**: Rank (1 = best) or Value (higher = better)
- **Compare side-by-side**: OPE rank vs. true rank — should align
- **Mismatches**: positions where bars don't align

#### **Correlation Plots**
- **Spearman ρ ∈ [-1, 1]**: measure of ranking consistency
- **ρ > 0.7**: good ranking agreement
- **ρ < 0.5**: ranking failure
- **ρ < 0**: anti-correlated (worst-case failure)

### Reading the Metadata

Each experiment outputs a JSON metadata file:

```json
{
  "experiment": "exp_01_ope_works",
  "seed": 42,
  "timestamp": "2026-03-04T10:15:30Z",
  "parameters": {
    "gridworld_size": 5,
    "num_trajectories": 5000,
    "traj_length": 50
  },
  "results": {
    "spearman_rho": 0.92,
    "top1_mismatch": false,
    "ess": 4500.0,
    "mse": 0.045
  },
  "key_findings": "OPE ranking correlates well with true ranking under good coverage."
}
```

---

## Reproducing Results

Each experiment uses a fixed seed (printed at start). To reproduce exactly:

```bash
# Single experiment
python experiments/exp_01_ope_works.py

# All experiments
python experiments/run_all_experiments.py
```

All outputs are deterministic given the seed.

---

## Extending Experiments

### Modify an Existing Experiment

Edit the `main()` function. Example: increase sample size in Exp 1:

```python
def main():
    ...
    N = 10000  # was 5000
    batch = collect_batch(env, beh, pi, N=N, T=50, seed=seed)
    ...
```

Re-run and compare outputs.

### Add a New Experiment

1. Create `experiments/exp_NN_new_name.py`
2. Copy structure from an existing experiment
3. Add to `run_all_experiments.py`

### Compare Two Experiments

Generate both, then compare plots:

```bash
python experiments/exp_01_ope_works.py
python experiments/exp_02_ope_fails_shift.py

# Compare results/figures/exp_01_* vs. results/figures/exp_02_*
```

---

## Troubleshooting

### Plots Look Different From Expected

1. **Check the seed**: Ensure `set_seed(seed)` is called at the start
2. **Check sample size**: Smaller N = more noise
3. **Check environment**: Grid size, slip probability, etc.

### ESS is 0

This means **all weights are ~0 except a few**. This is evidence of severe support mismatch:
- Behavior policy covers < 1% of evaluation policy support
- Only a handful of trajectories contribute meaningfully to the estimate
- The estimate is essentially one data point — unreliable

### Correlation is Negative

Ranking is **anti-correlated** with truth. This is catastrophic failure:
- OPE ranks policies in opposite order from true ranking
- Selection based on OPE will choose worst policies
- Indicates severe methodological mismatch

---

## Next Steps

After running experiments:

1. **Visualize Results**: Open `results/figures/` and browse plots
2. **Read Metadata**: Check `results/data/exp_*.json` for key metrics
3. **Interpret**: Use "Reading the Plots" section above
4. **Modify**: Change hyperparameters and re-run to see sensitivity
5. **Write**: Summarize findings in a report or blog post

