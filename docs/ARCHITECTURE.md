# Architecture Overview (v2)

## Project Philosophy

**Research-Grade + Beginner-Friendly**: Every module is independently understandable, with clear docstrings and test-able components. No magic. Every plot is reproducible.

---

## Directory Structure (v2)

```
v2/
├── src/                       # Core library (reusable across experiments)
│   ├── __init__.py
│   ├── envs.py               # Environments (Gridworld, MatrixGames)
│   ├── policies.py           # Policy classes (TabularPolicy, MatrixPolicy)
│   ├── ope.py                # OPE estimators (IS, WIS, PDIS, FQE)
│   ├── evaluation.py         # Tournament, Pareto, maximin
│   └── utils.py              # Seeding, logging, plotting, I/O
│
├── experiments/              # Runnable experiment scripts
│   ├── exp_01_ope_works.py          # Single-agent, good coverage
│   ├── exp_02_ope_fails_shift.py    # Distribution shift
│   ├── exp_03_opponent_shift.py     # Multi-agent, opponent pool change
│   ├── exp_04_nontransitivity.py    # Cyclic dominance
│   ├── exp_05_dominance_robust.py   # Dominance vs. ranking
│   └── run_all_experiments.py       # Execute all experiments
│
├── docs/                     # Documentation (non-code)
│   ├── ACHIEVEMENTS.md       # What was completed (episodes 1-9)
│   ├── ARCHITECTURE.md       # This file
│   ├── EXPERIMENT_GUIDE.md   # How to run and interpret experiments
│   ├── API_REFERENCE.md      # Function/class documentation
│   └── RESULTS_FRAMEWORK.md  # How to read and compare results
│
├── results/                  # Auto-generated outputs
│   ├── figures/             # PNG/PDF plots from experiments
│   ├── data/                # JSON/CSV data from runs
│   └── logs/                # Experiment logs and metadata
│
└── README.md                # Main entry point
```

---

## Core Modules (src/)

### `envs.py`
**Single-agent and multi-agent environments.**

Classes:
- `GridworldConfig`: Configuration (width, height, goal, slip probability)
- `Gridworld`: Tabular environment with deterministic transitions + slip
- `MatrixGame`: 2-player zero/non-zero-sum payoff matrix
- Factory functions: `matching_pennies()`, `rock_paper_scissors()`, `battle_of_sexes()`

Usage:
```python
from src.envs import Gridworld, GridworldConfig, rock_paper_scissors
env = Gridworld(GridworldConfig(width=5, height=5, slip=0.1))
game = rock_paper_scissors()
```

---

### `policies.py`
**Policy representations (probability distributions over actions).**

Classes:
- `TabularPolicy`: State → action probability distribution (for Gridworld)
- `MatrixPolicy`: Simple action probability distribution (for matrix games)

Factory functions:
- `random_tabular_policy(nS, nA)`
- `epsilon_greedy_from_q(Q, eps=0.1)`
- `uniform_matrix_policy(nA)`
- `biased_matrix_policy(probs)`

Usage:
```python
from src.policies import TabularPolicy, epsilon_greedy_from_q
Q = np.random.randn(nS, nA)
pi = epsilon_greedy_from_q(Q, eps=0.1)
a = pi.act(s, rng)
```

---

### `ope.py`
**Off-Policy Evaluation estimators.**

Functions:
- `importance_sampling(returns, ratios, clip=None)` → OPEStats(mean, std, ess)
- `weighted_is(returns, ratios, clip=None)` → OPEStats
- `per_decision_is(rewards, step_ratios, gamma=0.99, clip=None)` → float
- `fitted_q_evaluation_tabular(...)` → FQEResult

All estimators accept optional clipping to handle heavy-tailed weights.

Usage:
```python
from src.ope import importance_sampling, OPEStats
returns = np.array([...]
ratios = np.array([...]
stats = importance_sampling(returns, ratios, clip=10.0)
print(f"Value estimate: {stats.mean} ± {stats.std}")
```

---

### `evaluation.py`
**Tournament play, ranking metrics, dominance-based selection.**

Functions:
- `play_matrix_game_expected(game, pi0, pi1)` → payoff_pi0
- `tournament_matrix(game, policies)` → TournamentResult (win matrix)
- `spearman_rank_corr(a, b)` → float
- `top1_mismatch(a, b)` → bool
- `pareto_front(points, maximize=True)` → indices
- `maximin_robustness(scores_vs_opponents)` → robustness_scores

Usage:
```python
from src.evaluation import tournament_matrix, pareto_front
result = tournament_matrix(game, policies)
print(result.win_matrix)  # NxN matrix of pairwise wins
pareto_idx = pareto_front(result.payoffs, maximize=True)
```

---

### `utils.py`
**Reproducibility, logging, plotting, I/O.**

Functions:
- `set_seed(seed)` → Set numpy/random seeds globally
- `TrajectoryBatch`: Dataclass holding offline trajectories
- `collect_batch(env, beh_policy, eval_policy, N, T, seed)` → TrajectoryBatch
- `save_json(path, obj)`, `load_json(path)` → JSON I/O
- `ensure_dir(path)` → Create directory if needed
- `plot_heatmap(mat, title, outpath)`
- `plot_hist(x, title, xlabel, outpath)`
- `plot_scatter(x, y, title, xlabel, ylabel, outpath, labels=None)`

Usage:
```python
from src.utils import set_seed, collect_batch, plot_heatmap
set_seed(42)
batch = collect_batch(env, beh, pi, N=1000, T=50, seed=42)
plot_heatmap(batch.step_cum_ratios, title="Importance Weights", outpath="weights.png")
```

---

## Experiments (experiments/)

Each experiment is a **standalone script** that:
1. Sets a seed and loads/creates data
2. Runs a self-contained simulation
3. Generates plots and saves metadata to `results/`
4. Is **independent** — can be run in any order

### Experiment Naming Convention
- `exp_NN_name.py` where NN is a 2-digit number (01, 02, ...)
- Each file has a clear docstring explaining the research question
- Each file has a `main()` function that runs the full pipeline

### Standard Experiment Structure
```python
"""
exp_01_ope_works.py

Research Question: Does OPE ranking correlate with true ranking in simple settings?

Hypothesis: When behavior policy covers evaluation policy, IS/WIS ranking 
should match true rollout ranking.

Methods: 
  - Single-agent Gridworld with 3 policies
  - Collect trajectories under different behavior policies
  - Compare OPE rank vs. true rank
"""

from pathlib import Path
from src.utils import set_seed, ensure_dir
import numpy as np
import json

def main():
    root = Path(__file__).resolve().parents[1]
    ensure_dir(root / "results" / "figures")
    ensure_dir(root / "results" / "data")
    
    seed = 42
    set_seed(seed)
    rng = np.random.default_rng(seed)
    
    # Your experiment code here...
    
    # Always save metadata
    metadata = {
        "experiment": "exp_01_ope_works",
        "seed": seed,
        "timestamp": ...,
        "key_findings": {...}
    }
    
    (root / "results" / "data" / "exp_01_metadata.json").write_text(
        json.dumps(metadata, indent=2)
    )

if __name__ == "__main__":
    main()
```

---

## Running Experiments

### Single Experiment
```bash
python experiments/exp_01_ope_works.py
```

### All Experiments
```bash
python experiments/run_all_experiments.py
```

### With Logging
```bash
python experiments/exp_01_ope_works.py 2>&1 | tee results/logs/exp_01.log
```

---

## Results Output Structure

After running experiments, you'll find:

```
results/
├── figures/
│   ├── exp_01_ope_correlation.png
│   ├── exp_02_ess_collapse.png
│   ├── exp_03_opponent_shift_heatmap.png
│   ├── exp_04_cycle_network.png
│   └── exp_05_pareto_dominance.png
├── data/
│   ├── exp_01_metadata.json
│   ├── exp_02_ess_values.json
│   ├── exp_03_rankings.json
│   └── exp_04_win_matrices.json
└── logs/
    ├── exp_01.log
    ├── exp_02.log
    └── run_all_experiments.log
```

Every output file includes:
- Timestamp
- Seed used
- Key metrics (correlation, MSE, etc.)
- Hyperparameters

---

## Design Principles

### 1. **Modularity**
- Each `src/` module is independent
- Each experiment uses only the functions it needs
- Easy to add new estimators, environments, or metrics

### 2. **Reproducibility**
- All randomness seeded
- All plots self-generated with seed info in filename
- All hyperparameters logged as metadata

### 3. **Clarity Over Cleverness**
- Prefer explicit loops over vectorized operations (when clarity matters)
- Use descriptive variable names
- Include docstrings on all public functions

### 4. **Research Transparency**
- Each experiment answers a clear research question
- Methods are documented in file docstrings
- Results are interpretable (plots, tables, not just numbers)

---

## Extension Points

### Adding a New Environment
1. Create class in `src/envs.py` (inherit the pattern)
2. Implement `reset()`, `step()`, and property accessors
3. Add a factory function

### Adding a New OPE Estimator
1. Implement in `src/ope.py`
2. Return an `OPEStats` dataclass
3. Add docstring with algorithm description

### Adding a New Experiment
1. Create `experiments/exp_NN_name.py`
2. Follow the standard structure above
3. Add to `run_all_experiments.py` in the `EXPERIMENTS` list

---

## Dependencies

- **numpy** ≥ 1.24 — numerical computing
- **matplotlib** ≥ 3.7 — plotting
- **scipy** (optional) — for statistical tests

Keep this list minimal. If you need a new dependency, justify it in a comment.

