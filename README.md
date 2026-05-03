# Causal Counterfactual Policy Ranking in Offline RL

**CS748 Project — IIT Bombay**

Research paper and experiments for *"When Ranking Fails: Causal Counterfactual Policy Evaluation for Offline Reinforcement Learning"* (NeurIPS 2026 format).

---

## Problem

Standard off-policy evaluation (IS, WIS, PDIS) ranks policies correctly when behavior and target policies are close, but **fails catastrophically** under distribution shift — even when value estimates are individually accurate. This is the **policy misranking** problem.

## Solution: PoR-Model

We introduce **Probability of Regret (PoR)** with model-based estimation via **Fitted Q-Evaluation (FQE)**. By comparing policies at the *trajectory level* (matched-pair comparison) rather than by average value, PoR-Model:

- Achieves **ρ = 1.000** across all 25 tabular gridworld benchmark settings
- Achieves **ρ = 1.000** on FrozenLake-8×8 (stochastic) and CartPole-v1 (discretized) at worst coverage
- Requires **100× fewer trajectories** than WIS for correct ranking
- Outperforms IS, WIS, PDIS, DR, and FQE-Value under severe distribution shift

---

## Repository Structure

```
src/                        Core library
├── causal_ope.py           PoR estimators (PoR-IS, PoR-Model, PoB)
├── envs.py                 Gridworld + matrix game environments
├── ope.py                  IS, WIS, PDIS, FQE implementations
├── policies.py             TabularPolicy, epsilon-greedy
├── utils.py                Trajectory collection, TrajectoryBatch
├── evaluation.py           Spearman ρ, tournament metrics
└── logging_utils.py        Experiment logging

experiments/                Reproducible experiments
├── exp_01_ope_works.py     Baseline: IS works under good coverage
├── exp_02_ope_fails_shift.py  IS fails under distribution shift
├── exp_03_opponent_shift.py   MARL: opponent shift causes ranking reversal
├── exp_04_nontransitivity.py  Non-transitivity in policy rankings
├── exp_05_dominance_robust.py Maximin selection stability
├── exp_06_por_comparison.py   PoR-IS vs PoR-Model comparison
├── exp_07_bound_validation.py Theorem 1 & 3 bound validation
├── exp_08_multibenchmark.py   5-environment gridworld benchmark
├── exp_09_classic_benchmarks.py  FrozenLake + CartPole + DR/FQE-Value
└── run_all_experiments.py  Run all experiments sequentially

paper/
├── main.tex                NeurIPS 2026 submission (LaTeX)
├── references.bib          33 verified references
├── neurips_2026.sty        Style file
├── gen_figures.py          Generates all paper figures
├── main.pdf                Compiled paper (19 pages)
└── figures/                Publication-quality PDFs
```

---

## Setup

```bash
pip install -r requirements.txt
pip install gymnasium
```

## Running Experiments

```bash
cd experiments

# Individual experiments
python3 exp_07_bound_validation.py   # theorem validation
python3 exp_08_multibenchmark.py     # 5-env gridworld benchmark
python3 exp_09_classic_benchmarks.py # FrozenLake + CartPole

# Generate paper figures
cd ../paper && python3 gen_figures.py
```

## Compile Paper

```bash
cd paper && tectonic main.tex
```

---

## Key Results

| Method | GW-5×5 (ESS≈0%) | FL-8×8 (ESS=0.4%) | CartPole (ESS=3.2%) |
|--------|-----------------|-------------------|---------------------|
| IS | −0.15 | −0.00 | −0.20 |
| WIS | −0.15 | −0.07 | −0.92 |
| PDIS | −0.62 | −0.07 | −0.92 |
| DR | — | +0.47 | +0.68 |
| FQE-Value | — | +0.44 | **+1.00** |
| **PoR-Model** | **+1.00** | **+1.00** | **+1.00** |

*Spearman ρ vs ground truth at worst behavior coverage.*

---

## Theoretical Contributions

- **Theorem 1**: IS misranking bound ≤ 2exp(−n_eff·Δ²/2C²)
- **Theorem 2**: MARL OPE impossibility under opponent shift
- **Theorem 3**: PoR misranking bound ≤ exp(−2·n_eff·ρ²) — no C dependence
- **Theorem 4**: Maximin selection stability

**Reference**: Kawakami & Tian, "Potential Outcome Rankings for Counterfactual Decision Making", arXiv:2511.10776, 2025.
