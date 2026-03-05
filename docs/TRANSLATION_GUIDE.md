# v2 ↔ Original Repository: Translation Guide

**Purpose**: Map between original episode-based structure and new v2 experimentation structure.

---

## Side-by-Side Comparison

### Original Structure (scripts/)
```
scripts/
├── episode_01_project_setup.py
├── episode_02_single_agent_env.py
├── episode_03_single_agent_ope_rank.py
├── episode_04_stress_test_shift.py
├── episode_05_multiagent_matrix_games.py
├── episode_06_ope_rank_failure_multiagent.py
├── episode_07_nontransitivity.py
├── episode_08_dominance_based_eval.py
├── episode_09_midterm_checkpoint.py
└── run_all_midterm.py
```

**Philosophy**: Educational progression (YouTube playlist format)
- Each episode builds on previous
- Narrative arc: single-agent → multi-agent → failures → solutions
- Focus on explanation and exploration

---

### v2 Structure (experiments/)
```
experiments/
├── exp_01_ope_works.py
├── exp_02_ope_fails_shift.py
├── exp_03_opponent_shift.py
├── exp_04_nontransitivity.py
├── exp_05_dominance_robust.py
└── run_all_experiments.py
```

**Philosophy**: Research-focused (independent experiments)
- Each experiment answers a clear question
- Can be run in any order
- Focus on reproducibility and analysis

---

## Episode → Experiment Mapping

### Exp 01: OPE Works (Good Coverage)

**Source Episodes**: 02, 03
- `episode_02_single_agent_env.py` — Create Gridworld + policies
- `episode_03_single_agent_ope_rank.py` — Test OPE with good coverage

**v2 Purpose**: Show that OPE ranking works when behavior policy has good coverage

**What's the same**:
- Gridworld environment (5×5)
- 3-policy comparison (random, ε-greedy soft, ε-greedy hard)
- IS, WIS, PDIS estimators

**What's different**:
- **Standalone**: Exp 01 doesn't depend on Exp 02
- **Focused**: Only shows the "good case" of OPE
- **Metadata**: Saved as JSON with key metrics (ρ, ESS, MSE)
- **Structure**: Docstring with research question + hypothesis

**Key Outputs**:
```
Scatter plot (OPE vs. true value, tight diagonal)
Bar chart (OPE rank vs. true rank, aligned)
Metadata: spearman_rho ≈ 0.92, top1_mismatch = False
```

---

### Exp 02: OPE Fails (Distribution Shift)

**Source Episode**: 04
- `episode_04_stress_test_shift.py` — Stress test with deliberately bad behavior policy

**v2 Purpose**: Show that importance weight degeneracy breaks OPE under distribution shift

**What's the same**:
- Same Gridworld
- Same evaluation policies
- **Different** behavior policy (deliberately bad: always-move-right)
- Importance weight computation and analysis

**What's different**:
- **Standalone**: Can run without Exp 01
- **Isolation**: Only tests one failure mode (shift)
- **Visualization**: Heavy focus on weight histogram (log scale)
- **Metrics**: ESS collapse, MSE increase

**Key Outputs**:
```
Histogram (importance weights, log scale, heavy tails)
Bar chart (ESS by policy, showing collapse)
Scatter plot (OPE vs. true, loose with outliers)
Metadata: spearman_rho ≈ 0.18, ess_fraction ≈ 0.05
```

**Key Insight**: 
```
Weight degeneracy (max >> mean) → ESS collapses → OPE unreliable
```

---

### Exp 03: Opponent Shift (Multi-Agent)

**Source Episodes**: 05, 06
- `episode_05_multiagent_matrix_games.py` — Create RPS game + policies
- `episode_06_ope_rank_failure_multiagent.py` — Show opponent shift breaks ranking

**v2 Purpose**: Show that policy ranking flips when opponent pool changes

**What's the same**:
- Rock-Paper-Scissors game
- 3 policies (Rock, Paper, Scissors biased)
- Two opponent pools (A = mostly Rock, B = mostly Scissors)

**What's different**:
- **Focused**: Isolates "opponent shift" as a failure mode
- **Standalone**: Doesn't build on single-agent knowledge
- **Comparison**: Heatmaps side-by-side (Pool A vs. Pool B)
- **Metrics**: Rank correlation drops dramatically (0.8 → 0.3)

**Key Outputs**:
```
Win matrix heatmap (Pool A)
Win matrix heatmap (Pool B, different patterns)
Rank correlation plot (before/after shift)
Metadata: pool_a_rho = 0.80, pool_b_rho = 0.30, top1_mismatch = True
```

**Key Insight**:
```
Opponent shift (Pool A → Pool B) → same policies ranked differently
OPE confident but wrong for new deployment target
```

---

### Exp 04: Non-Transitivity (Cyclic Dominance)

**Source Episode**: 07
- `episode_07_nontransitivity.py` — Show RPS exhibits cycles (A > B > C > A)

**v2 Purpose**: Prove that a valid total ranking is impossible due to cycles

**What's the same**:
- Rock-Paper-Scissors (inherently non-transitive)
- Pairwise tournament results
- Win matrix

**What's different**:
- **Standalone**: Can understand without prior experiments
- **Focus**: Proves impossibility of total ordering
- **Visualization**: Network graph showing cycles
- **Metrics**: Kendall τ (measure of ranking consistency)

**Key Outputs**:
```
Win matrix heatmap (showing cycles)
Network graph (Rock → Scissors → Paper → Rock)
Kendall τ metric (will be << 1)
Metadata: kendall_tau ≈ 0.2, num_cycles = 1+
```

**Key Insight**:
```
Cycles prove: No valid total ranking exists
Ranking depends on how you aggregate pairwise results
```

---

### Exp 05: Dominance-Based Evaluation is Robust

**Source Episode**: 08
- `episode_08_dominance_based_eval.py` — Show Pareto + maximin are stable

**v2 Purpose**: Demonstrate that dominance methods trade ordering for robustness

**What's the same**:
- Same RPS game + policies
- Pareto front computation
- Maximin robustness scoring
- Evaluation across multiple opponent pools

**What's different**:
- **Standalone**: Doesn't require understanding of ranking failures
- **Focus**: Dominance as alternative (not just consequence)
- **Comparison**: Tables showing survivor stability
- **Metrics**: Pareto front stability vs. Top-1 rank stability

**Key Outputs**:
```
Pareto front plot (mean vs. robustness)
Survivor stability table (policies, pools A/B, ranked?)
Comparison: Top-1 rank 10% stable, Pareto front 60% stable
Metadata: pareto_stable = True, top1_stable = False
```

**Key Insight**:
```
Dominance methods ≠ total ranking
Pareto set: smaller but stable
Top-1 rank: fragile, changes with opponent
Trade ordering for robustness
```

---

## How Original Episodes → v2 Experiments

### Information Flow

```
Original Episodes (Educational)
└── Extract core experiments
    └── v2 Experiments (Research)
        └── Independent, focused, reproducible

episode_02 + 03 ─────────→ exp_01 (OPE works)
episode_04 ───────────────→ exp_02 (OPE fails)
episode_05 + 06 ──────────→ exp_03 (Opponent shift)
episode_07 ───────────────→ exp_04 (Non-transitivity)
episode_08 ───────────────→ exp_05 (Dominance robust)
```

### Conversion Checklist

For each experiment, when converting from episodes:

- [ ] **Docstring**: Add research question + hypothesis
- [ ] **Metadata**: Prepare JSON template with all parameters
- [ ] **Plots**: Use same figures but save to `results/figures/`
- [ ] **Seeds**: Keep fixed seed from episode
- [ ] **Standalone**: Ensure no dependencies on other experiments
- [ ] **Testing**: Run and verify metadata is saved

---

## Running Both in Parallel

### Original (for Teaching)
```bash
# Educational videos / interactive exploration
python scripts/run_all_midterm.py
# Output: reports/figures/, reports/midterm_summary.md
```

### v2 (for Research)
```bash
# Reproducible research / publication
python v2/experiments/run_all_experiments.py
# Output: v2/results/figures/, v2/results/data/
```

### Coexistence Strategy

Both can coexist:
- **Original** (`/scripts/`) — Use for understanding, teaching, YouTube
- **v2** (`/v2/`) — Use for research, publication, extension

They share the same `src/ope_ma/` library!

```
src/ope_ma/
│
├── scripts/episode_*.py  (original, educational)
│
└── v2/experiments/exp_*.py  (v2, research-focused)
```

---

## Differences in Focus

### Original Episodes (scripts/)

| Aspect | Original |
|--------|----------|
| **Structure** | Linear progression (1→2→...→9) |
| **Audience** | Learners, YouTube viewers |
| **Emphasis** | "What" + "Why" (explanation) |
| **Outputs** | `reports/figures/`, `reports/midterm_summary.md` |
| **Dependencies** | Episodes depend on prior episodes |
| **Re-runnable** | Yes, but built to run all together |
| **Narrative** | Story arc (single-agent → multi-agent → insights) |

### v2 Experiments (experiments/)

| Aspect | v2 |
|--------|-----|
| **Structure** | Independent experiments (can run any order) |
| **Audience** | Researchers, extension developers |
| **Emphasis** | "How" + "Proof" (methodology) |
| **Outputs** | `results/figures/`, `results/data/` (JSON) |
| **Dependencies** | Each experiment is self-contained |
| **Re-runnable** | Yes, always reproducible with seed |
| **Narrative** | Modular (each answers one question) |

---

## File Reuse Strategy

### Code Reuse
✅ **YES** — All five experiments use `src/ope_ma/`:
- Same `Gridworld` environment
- Same `MatrixGame` environments
- Same OPE estimators (IS, WIS, PDIS)
- Same dominance methods (Pareto, maximin)

### Plot Reuse
⚠️ **SIMILAR** — Same concepts but different presentation:
- **Original**: Narrative flow (build context before showing failure)
- **v2**: Isolation (show one thing per experiment)

### Data Reuse
❌ **NO** — Use separate directories:
- Original: `data/`, `reports/figures/`, `reports/slides/`
- v2: `v2/results/figures/`, `v2/results/data/`

Keeps experiments independent and doesn't overwrite original outputs.

---

## Quality Assurance

### Before Declaring v2 Complete

- [ ] All 5 experiments runnable independently
- [ ] All plots save to correct locations
- [ ] All metadata JSON files created
- [ ] Reproducibility verified (run twice, identical output)
- [ ] Documentation complete and tested

### Testing Checklist

```bash
# Test 1: Run single experiment
python v2/experiments/exp_01_ope_works.py
# Check: v2/results/figures/exp_01_*.png exists

# Test 2: Run all experiments
python v2/experiments/run_all_experiments.py
# Check: All 5 exp_*.json files in v2/results/data/

# Test 3: Reproducibility
rm -rf v2/results
python v2/experiments/run_all_experiments.py  # First run
cp -r v2/results v2/results_run1
rm -rf v2/results
python v2/experiments/run_all_experiments.py  # Second run
diff v2/results/figures v2/results_run1/figures
# Check: No differences (files identical)

# Test 4: Documentation accuracy
# Open README.md, EXPERIMENT_GUIDE.md
# Run examples from docs
# Verify outputs match descriptions
```

---

## Using This Translation Guide

### "I have an episode script, how do I convert it?"
1. Find the episode in left column above
2. Find corresponding experiment in right column
3. Read "What's the same" and "What's different"
4. Use "Conversion Checklist" to guide rewrite

### "I want to understand what an experiment does"
1. Read the experiment filename: `exp_NN_name.py`
2. Look up in "Episode → Experiment Mapping" above
3. Read "v2 Purpose" section
4. Cross-reference with [EXPERIMENT_GUIDE.md](docs/EXPERIMENT_GUIDE.md)

### "I want to extend an experiment"
1. Read the experiment's docstring (research question)
2. Read [ARCHITECTURE.md](docs/ARCHITECTURE.md) for design patterns
3. Read [API_REFERENCE.md](docs/API_REFERENCE.md) for available functions
4. Modify the `main()` function
5. Re-run and check `v2/results/data/exp_NN_metadata.json`

---

## Summary Table

| Episode | Topic | → | Experiment | Focus |
|---------|-------|---|-----------|-------|
| 01 | Setup | → | (setup only) | Infrastructure |
| 02, 03 | Single-agent + OPE | → | exp_01 | OPE works (good coverage) |
| 04 | Stress test | → | exp_02 | OPE fails (shift) |
| 05, 06 | Multi-agent + failure | → | exp_03 | Opponent shift flips ranks |
| 07 | Non-transitivity | → | exp_04 | Cycles exist, no ordering |
| 08 | Dominance-based | → | exp_05 | Dominance is robust |
| 09 | Checkpoint | → | (summary) | All experiments together |

---

## Next Steps (After Reading This Guide)

1. **For understanding**: Read [ACHIEVEMENTS.md](docs/ACHIEVEMENTS.md) for what's been done
2. **For conversion**: Use the mapping above to rewrite episodes as experiments
3. **For running**: Use [QUICKSTART.md](QUICKSTART.md) and [EXPERIMENT_GUIDE.md](docs/EXPERIMENT_GUIDE.md)
4. **For analysis**: Use [RESULTS_FRAMEWORK.md](docs/RESULTS_FRAMEWORK.md) to interpret outputs

---

**Guide Status**: Complete ✓  
**Last Updated**: March 4, 2026

