# Getting Started with v2

This is your quick reference for setting up and running the v2 research codebase.

## Installation (1 minute)

```bash
# Navigate to v2 directory
cd v2

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

## Running Experiments (5 minutes)

```bash
# Run all 5 experiments (auto-generates plots + data)
python experiments/run_all_experiments.py

# Or run a single experiment
python experiments/exp_01_ope_works.py
```

Outputs go to:
- `results/figures/` — PNG plots
- `results/data/` — JSON metadata
- `results/logs/` — Experiment logs

## Next Steps

1. **Read [README.md](README.md)** — Project overview
2. **Browse [docs/](docs/)** — Detailed documentation
3. **Look at `results/figures/`** — See what experiments produced
4. **Try modifying an experiment** — Change parameters and re-run

## Key Documents

- **[README.md](README.md)** — Project goal and visual summary
- **[docs/ACHIEVEMENTS.md](docs/ACHIEVEMENTS.md)** — What's been completed (Episodes 1-9)
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — Code organization and design
- **[docs/EXPERIMENT_GUIDE.md](docs/EXPERIMENT_GUIDE.md)** — How to run and interpret each experiment
- **[docs/API_REFERENCE.md](docs/API_REFERENCE.md)** — Function signatures and docstrings
- **[docs/RESULTS_FRAMEWORK.md](docs/RESULTS_FRAMEWORK.md)** — How to read and compare results

## Dependencies

Minimal and focused:
- **numpy** ≥ 1.24 — Numerical computing
- **matplotlib** ≥ 3.7 — Plotting
- **scipy** ≥ 1.9 — Statistical functions (optional but recommended)

## Project Structure

```
v2/
├── README.md                   ← Start here
├── requirements.txt            ← Dependencies
├── src/                        ← Core library
│   ├── envs.py                (Environments)
│   ├── policies.py            (Policies)
│   ├── ope.py                 (OPE estimators)
│   ├── evaluation.py          (Tournament, dominance)
│   └── utils.py               (Utilities)
├── experiments/               ← Runnable scripts
│   ├── exp_01_ope_works.py
│   ├── exp_02_ope_fails_shift.py
│   ├── exp_03_opponent_shift.py
│   ├── exp_04_nontransitivity.py
│   ├── exp_05_dominance_robust.py
│   └── run_all_experiments.py
├── docs/                      ← Documentation
│   ├── ACHIEVEMENTS.md
│   ├── ARCHITECTURE.md
│   ├── EXPERIMENT_GUIDE.md
│   ├── API_REFERENCE.md
│   └── RESULTS_FRAMEWORK.md
└── results/                   ← Auto-generated outputs
    ├── figures/               (PNG plots)
    ├── data/                  (JSON metadata)
    └── logs/                  (Experiment logs)
```

## Quick Facts

- **Midterm Status**: Episodes 1-9 complete ✓
- **Experiments**: 5 focused experiments showing OPE failures and dominance solutions
- **Reproducibility**: All outputs seeded and deterministic
- **Documentation**: Comprehensive but beginner-friendly

## Example Workflow

```bash
# 1. Run all experiments
python experiments/run_all_experiments.py

# 2. Look at the plots
open results/figures/

# 3. Check the metadata
cat results/data/exp_01_metadata.json | head -20

# 4. Modify an experiment (edit exp_01_ope_works.py)
# Change N from 5000 to 10000

# 5. Re-run and compare
python experiments/exp_01_ope_works.py
# Did Spearman ρ improve?
```

## Questions?

Refer to the documentation:
- **What's been done**: [docs/ACHIEVEMENTS.md](docs/ACHIEVEMENTS.md)
- **How to run experiments**: [docs/EXPERIMENT_GUIDE.md](docs/EXPERIMENT_GUIDE.md)
- **How to read results**: [docs/RESULTS_FRAMEWORK.md](docs/RESULTS_FRAMEWORK.md)
- **Function details**: [docs/API_REFERENCE.md](docs/API_REFERENCE.md)

---

**Status**: Midterm Complete → v2 Reorganization  
**Last Updated**: March 4, 2026

