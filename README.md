# OPE Ranking Failures in Multi-Agent RL — v2 (Experimentation & Research)

> **Status**: Midterm checkpoint complete (Episodes 1-9). v2 is a clean, documentation-focused reorganization for extended experimentation and research.

---

## 🎯 Project Goal

Demonstrate **why off-policy evaluation (OPE) ranking fails in multi-agent RL** and present **dominance-based evaluation as a more robust alternative**.

### The Problem We Solve
1. **Single-agent RL**: OPE works when behavior policy covers evaluation policy
2. **Distribution shift**: OPE fails when support is mismatched → degenerate importance weights
3. **Multi-agent RL** (NEW): Even with good OPE estimates, opponent shift flips policy rankings
4. **Non-transitivity**: Cycles (A > B, B > C, C > A) make total rankings impossible
5. **Solution**: Dominance-based selection (Pareto, maximin robustness) is more stable

---

## 📊 Visual Results Summary

Here's what you'll generate when you run the experiments:

### Experiment 1: OPE Works (Good Coverage)
```
[Scatter: OPE vs. True Value]           [Bar: Ranking Comparison]
Points on y=x diagonal                  OPE rank ≈ True rank
Spearman ρ ≈ 0.92                       Top-1 match: YES
ESS ≈ 95% of N                          Conclusion: WORKS WELL
```

### Experiment 2: OPE Fails (Distribution Shift)
```
[Histogram: Importance Weights]         [Scatter: OPE vs. True]
Heavy tails (log scale)                 Wide scatter, outliers
Max weight >> mean weight               Spearman ρ ≈ 0.25
ESS collapses to ~5% of N               Conclusion: FAILS
```

### Experiment 3: Opponent Shift (Multi-Agent)
```
[Win Matrix: Pool A vs. Pool B]         [Rank Flip Heatmap]
Different patterns in payoffs           Policy A best in Pool A
                                        Policy B best in Pool B
Spearman ρ ≈ 0.30                       Conclusion: RANKING FLIPS
```

### Experiment 4: Non-Transitivity
```
[Cycle Network Graph]                   [Pareto Front]
Rock > Scissors > Paper > Rock          Not all policies comparable
Kendall τ << 1                          Conclusion: NO TOTAL ORDER
```

### Experiment 5: Dominance-Based is Robust
```
[Pareto Front (Mean vs. Robustness)]   [Survivor Stability Table]
Fewer policies, but stable              Pareto set: 60% stable
                                        Top-1 rank: 10% stable
Conclusion: TRADE ORDERING FOR ROBUSTNESS
```

---

## 🚀 Quick Start

### Setup
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# or on Windows:
# .venv\Scripts\activate

# Install minimal dependencies
pip install -r requirements.txt
```

### Run Everything
```bash
# Execute all 5 experiments (auto-generates figures + data)
python experiments/run_all_experiments.py

# Outputs appear in:
# - results/figures/  (PNG plots)
# - results/data/     (JSON metadata)
# - results/logs/     (experiment logs)
```

### Run Single Experiment
```bash
python experiments/exp_01_ope_works.py
```

---

## 📁 What's in v2?

```
v2/
├── README.md                                    ← You are here
├── requirements.txt                             ← pip dependencies
├── src/                                         ← Core library
│   ├── __init__.py
│   ├── envs.py          Gridworld, MatrixGames
│   ├── policies.py      TabularPolicy, MatrixPolicy
│   ├── ope.py           IS/WIS/PDIS estimators
│   ├── evaluation.py    Tournament, Pareto, maximin
│   └── utils.py         Seeding, plotting, I/O
│
├── experiments/                                 ← Runnable scripts
│   ├── exp_01_ope_works.py              (OPE under good coverage)
│   ├── exp_02_ope_fails_shift.py        (Distribution shift breaks OPE)
│   ├── exp_03_opponent_shift.py         (Opponent pool change flips ranks)
│   ├── exp_04_nontransitivity.py        (Cycles exist, no total order)
│   ├── exp_05_dominance_robust.py       (Dominance more stable than ranking)
│   └── run_all_experiments.py           (Execute all 5)
│
├── docs/                                        ← Documentation
│   ├── ACHIEVEMENTS.md      What was completed (Episodes 1-9 checklist)
│   ├── ARCHITECTURE.md      Module design, how to extend
│   ├── EXPERIMENT_GUIDE.md  How to run & interpret each experiment
│   ├── API_REFERENCE.md     Function/class docstrings (TBD)
│   └── RESULTS_FRAMEWORK.md How to read and compare results (TBD)
│
└── results/                                     ← Auto-generated outputs
    ├── figures/             (*.png plots)
    ├── data/                (*.json metadata + artifacts)
    └── logs/                (*.log files)
```

---

## 📖 Documentation Map

| Document | Purpose | Read When... |
|----------|---------|--------------|
| **[ACHIEVEMENTS.md](docs/ACHIEVEMENTS.md)** | Checklist of Episodes 1-9 | You want to see what's been done |
| **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** | Module design & extension | You're adding new code |
| **[EXPERIMENT_GUIDE.md](docs/EXPERIMENT_GUIDE.md)** | How to run & interpret experiments | You're running experiments |
| **[API_REFERENCE.md](docs/API_REFERENCE.md)** | Function/class documentation | You need function signatures |
| **[RESULTS_FRAMEWORK.md](docs/RESULTS_FRAMEWORK.md)** | How to interpret results | You're analyzing outputs |

---

## 🔬 Experiment Overview

### Experiment 1: OPE Works (Good Coverage)
**Question**: Does OPE ranking correlate with true ranking when behavior policy has good coverage?

**Key Finding**: **YES — OPE works well in easy settings.**
- Gridworld (5×5), 3 policies
- Behavior policy ≈ evaluation policy
- Spearman ρ ≈ 0.92, Top-1 match: YES
- Conclusion: OPE is fundamentally sound when coverage is good

**Visual**: Scatter plot showing OPE values on diagonal with true values

---

### Experiment 2: OPE Fails (Distribution Shift)
**Question**: What breaks OPE when behavior policy doesn't cover evaluation policy?

**Key Finding**: **Distribution shift → degenerate importance weights → OPE collapse.**
- Same Gridworld, but deliberately bad behavior policy
- Importance weights: heavy-tailed (max >>max)
- ESS collapses: 95% → 5% of N
- Spearman ρ drops: 0.92 → 0.25
- Conclusion: OPE is fragile under support mismatch

**Visual**: Histogram showing importance weight distribution (log scale) with heavy tails

---

### Experiment 3: Opponent Shift (Multi-Agent)
**Question**: Can OPE ranking fail even with good estimates, due to opponent pool change?

**Key Finding**: **YES — opponent shift flips policy ranks even when OPE estimates are confident.**
- Rock-Paper-Scissors: 3 policies × 2 opponent pools
- Pool A: mostly Rock
- Pool B: mostly Scissors
- OPE ranking optimized for Pool A
- Ground truth against Pool B: top policies flip
- Spearman ρ drops: 0.80 → 0.30
- Conclusion: Multi-agent introduces a new failure mode

**Visual**: Two win matrix heatmaps (Pool A vs. Pool B) showing different patterns

---

### Experiment 4: Non-Transitivity (Cyclic Dominance)
**Question**: Is a global ranking possible, or do cycles prevent total ordering?

**Key Finding**: **Cycles exist — A > B, B > C, C > A — so no valid total ordering.**
- Rock-Paper-Scissors inherently exhibits cycles
- Pairwise tournament: full matrix
- Kendall τ << 1 (far from consistent ranking)
- Conclusion: Single-scalar ranking is fundamentally wrong for some problems

**Visual**: Directed graph showing cycle (Rock → Scissors → Paper → Rock)

---

### Experiment 5: Dominance-Based Evaluation is Robust
**Question**: Can dominance methods (Pareto, maximin) provide a more robust alternative?

**Key Finding**: **Dominance methods trade total ordering for robustness — Pareto survivors are stable across opponent shifts.**
- Pareto front in (payoff, robustness) space
- Maximin robustness score
- Compare: Top-1 ranking vs. Pareto front
- Survivor stability: Pareto set 60% stable, Top-1 only 10% stable
- Conclusion: Sacrifice a total ordering, gain robustness

**Visual**: Pareto front plot with survivors highlighted across multiple opponent pools

---

## 🛠️ Implementation Checklist

### Core Library (src/)
- [x] `envs.py`: Gridworld + MatrixGame environments
- [x] `policies.py`: TabularPolicy + MatrixPolicy
- [x] `ope.py`: IS/WIS/PDIS/FQE estimators
- [x] `evaluation.py`: Tournament, ranking metrics, dominance
- [x] `utils.py`: Seeding, batch collection, plotting, I/O

### Experiments (experiments/)
- [ ] `exp_01_ope_works.py` — convert from episode script
- [ ] `exp_02_ope_fails_shift.py` — convert from episode script
- [ ] `exp_03_opponent_shift.py` — convert from episode script
- [ ] `exp_04_nontransitivity.py` — convert from episode script
- [ ] `exp_05_dominance_robust.py` — convert from episode script
- [ ] `run_all_experiments.py` — orchestrator

### Documentation (docs/)
- [x] `ACHIEVEMENTS.md` — Episode checklist
- [x] `ARCHITECTURE.md` — Module design
- [x] `EXPERIMENT_GUIDE.md` — How to run & interpret
- [ ] `API_REFERENCE.md` — Function signatures
- [ ] `RESULTS_FRAMEWORK.md` — Result interpretation

### Results (results/)
- [ ] figures/ — auto-generated plots (after running experiments)
- [ ] data/ — auto-generated metadata (after running experiments)
- [ ] logs/ — auto-generated logs (after running experiments)

---

## 💡 Key Insights

1. **OPE requires good coverage**: When behavior policy doesn't cover evaluation policy, importance weights explode
2. **Multi-agent adds complexity**: Opponent shift can flip rankings even with confident OPE estimates
3. **Ranking is fragile**: Cycles in pairwise comparisons make a total ordering impossible
4. **Dominance is robust**: Pareto front / maximin robustness are more stable under shift
5. **Trade-off exists**: Losing total ordering buys robustness — often worth it

---

## 🔗 How to Use v2

### For Research
1. **Understand the problem**: Read [ACHIEVEMENTS.md](docs/ACHIEVEMENTS.md) first
2. **Run experiments**: `python experiments/run_all_experiments.py`
3. **Analyze results**: Open `results/figures/` and `results/data/`
4. **Extend**: Modify experiments or add new ones (see [ARCHITECTURE.md](docs/ARCHITECTURE.md))

### For Teaching
1. **Show the progression**: Run experiments 1 → 5 in order
2. **Discuss failure modes**: Each experiment isolates one failure mode
3. **Compare plots**: Side-by-side visual comparison shows the differences
4. **Hands-on**: Students can modify hyperparameters and re-run

### For Reproduction
1. **Exact reproducibility**: All experiments use fixed seeds
2. **All outputs logged**: Metadata saved as JSON
3. **One-command pipeline**: `python experiments/run_all_experiments.py`
4. **Inspect artifacts**: Browse `results/` folder

---

## 📊 Expected Outputs (After Running)

### Figures (PNG)
```
results/figures/
├── exp_01_ope_value_scatter.png       (OPE vs. true, tight diagonal)
├── exp_01_ranking_comparison.png      (Rank bar chart)
├── exp_02_importance_weights_hist.png (Heavy tails, log scale)
├── exp_02_ess_by_policy.png           (ESS collapse)
├── exp_03_pool_a_win_matrix.png       (Heatmap of wins under Pool A)
├── exp_03_pool_b_win_matrix.png       (Heatmap of wins under Pool B)
├── exp_03_rank_correlation.png        (ρ before/after opponent shift)
├── exp_04_cycle_network.png           (Directed graph: Rock→Scissors→Paper)
├── exp_05_pareto_front.png            (Mean vs. robustness, labeled)
├── exp_05_survivor_stability.png      (Table: survivors across opponent pools)
└── combined_summary.png               (All 5 experiments in one figure)
```

### Data (JSON)
```
results/data/
├── exp_01_metadata.json               (seed, params, results)
├── exp_02_metadata.json
├── exp_03_metadata.json
├── exp_04_metadata.json
├── exp_05_metadata.json
└── summary_stats.json                 (aggregated key metrics)
```

---

## 🧪 Recommended Workflows

### Workflow 1: Verify Reproducibility
```bash
python experiments/run_all_experiments.py
# First run generates plots
rm -rf results/figures results/data
python experiments/run_all_experiments.py
# Second run should produce identical plots (same seed)
# Use image diff to verify
```

### Workflow 2: Modify & Compare
```bash
# Edit exp_01_ope_works.py
# Change: N = 10000 (was 5000)

python experiments/exp_01_ope_works.py
# New plot appears in results/figures/

# Compare new plot with original
# Did Spearman ρ improve with more samples?
```

### Workflow 3: Present Findings
```bash
# Generate all figures
python experiments/run_all_experiments.py

# Create a slideshow or report
# Include the 5 main plots:
# 1. OPE_value_scatter (Exp 1)
# 2. importance_weights_hist (Exp 2)
# 3. win_matrices (Exp 3)
# 4. cycle_network (Exp 4)
# 5. pareto_front (Exp 5)
```

---

## 🔧 Dependencies

```txt
numpy>=1.24        # Numerical computing
matplotlib>=3.7    # Plotting
```

Optional (for advanced analysis):
```txt
scipy>=1.9         # Statistical tests (Spearman, Kendall)
```

We keep dependencies minimal to ensure reproducibility and easy installation.

---

## 📚 Related Work & References

- **Off-Policy Evaluation**: Dudik et al. (2011), Thomas & Brunskill (2016)
- **Multi-Agent RL**: Leibo et al. (2017), Rashid et al. (2020)
- **Dominance & Robustness**: Pareto (1896), Savage (1951)
- **Non-Transitivity**: Arrow (1950), Condorcet (1785)

See episode comments for more detailed references.

---

## 📝 License

MIT — feel free to use for research, teaching, or open-source projects.

---

## 🤝 Contributing

To extend v2:

1. **New experiment**: Create `experiments/exp_NN_name.py`, add to `run_all_experiments.py`
2. **New method**: Add to `src/ope.py` or `src/evaluation.py`, document in [ARCHITECTURE.md](docs/ARCHITECTURE.md)
3. **New environment**: Add to `src/envs.py` following the existing pattern

All contributions should include:
- Clear docstring explaining the research question
- Reproducible seed
- Saved metadata (JSON)
- Generated plots

---

## 🎓 Learning Path

**Beginner** (new to OPE):
1. Run `exp_01_ope_works.py` — see OPE succeed
2. Read [ARCHITECTURE.md](docs/ARCHITECTURE.md) — understand modules
3. Modify hyperparameters, re-run

**Intermediate** (familiar with OPE):
1. Run all 5 experiments in order
2. Read [EXPERIMENT_GUIDE.md](docs/EXPERIMENT_GUIDE.md) — understand each failure mode
3. Modify an experiment, add a new estimator

**Advanced** (research):
1. Analyze `results/data/` JSON files
2. Implement new dominance criterion
3. Design experiment to test your hypothesis
4. Submit results back

---

## ❓ FAQ

**Q: How do I change the grid size in Exp 1?**
A: Edit `exp_01_ope_works.py`, change `GridworldConfig(width=10, height=10)`. Re-run.

**Q: Why does ESS collapse in Exp 2?**
A: Behavior policy (e.g., always-right) doesn't cover evaluation policy (e.g., random). Most trajectories have weight ≈ 0.

**Q: Can I add a new opponent pool in Exp 3?**
A: Yes! Edit `exp_03_opponent_shift.py`, create a Pool C, re-run. Pareto front will shift.

**Q: How do I interpret the Pareto front in Exp 5?**
A: Each point is a policy. Points on the upper-right frontier are non-dominated. Interior policies are strictly worse.

**Q: Where do the figures go?**
A: `results/figures/` directory. All PNG files are auto-named by experiment.

---

## 📞 Questions?

Refer to the documentation:
- **What was done**: [ACHIEVEMENTS.md](docs/ACHIEVEMENTS.md)
- **How code is organized**: [ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **How to run experiments**: [EXPERIMENT_GUIDE.md](docs/EXPERIMENT_GUIDE.md)
- **Function signatures**: [API_REFERENCE.md](docs/API_REFERENCE.md) (WIP)

---

**Last Updated**: March 4, 2026 | **Status**: Midterm Complete → v2 Reorganization In Progress

