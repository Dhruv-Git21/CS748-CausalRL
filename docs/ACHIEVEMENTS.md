# Midterm Achievements Checklist (Episodes 1-9)

## Project Foundation ✓
- [x] Established reproducible Python project structure with proper seeding
- [x] Set up virtual environment with minimal dependencies (numpy, matplotlib)
- [x] Implemented consistent logging and artifact saving patterns
- [x] Created `src/ope_ma/` package with modular architecture
- [x] Established figures/ and data/ directories for reproducible outputs

## Episode 1: Project Setup ✓
- [x] Initialize Git repo with proper .gitignore
- [x] Create virtual environment and requirements.txt
- [x] Set up directory structure (src/, scripts/, reports/, data/)
- [x] Implement seeding utility for reproducibility
- [x] Create initial README and documentation scaffold

## Episode 2: Single-Agent Environment ✓
- [x] Implement Gridworld environment (nS states, nA actions)
- [x] Create GridworldConfig for customizable grid size, slip probability, goal
- [x] Implement TabularPolicy base class
- [x] Create basic policy zoo (random_policy)
- [x] Visualize policy as heatmap

## Episode 3: Single-Agent OPE Ranking ✓
- [x] Implement Importance Sampling (IS) estimator
- [x] Implement Weighted Importance Sampling (WIS)
- [x] Implement Per-Decision Importance Sampling (PDIS)
- [x] Create trajectory batch collection with importance weight computation
- [x] Validate OPE estimates against ground truth rollouts
- [x] Compute Spearman rank correlation between OPE and true values
- [x] Show that OPE ranking works well under good coverage (behavior ≈ evaluation)

## Episode 4: Stress Test - Distribution Shift ✓
- [x] Introduce deliberately bad behavior policy with support mismatch
- [x] Demonstrate IS/WIS weight degeneracy under shift
- [x] Plot importance weight distribution (showing heavy tails)
- [x] Compute Effective Sample Size (ESS) collapse
- [x] Show MSE increase and rank correlation breakdown under shift
- [x] Visualize how poor coverage destroys OPE reliability

## Episode 5: Multi-Agent Matrix Games ✓
- [x] Implement MatrixGame environment (2-player, zero-sum)
- [x] Create Rock-Paper-Scissors game
- [x] Create Matching Pennies game
- [x] Create Battle of the Sexes game (non-zero-sum)
- [x] Implement MatrixPolicy with probability distributions
- [x] Create policy zoo with mixed strategies
- [x] Play_matrix_game_expected() for computing expected payoffs
- [x] Tournament results tracking

## Episode 6: OPE Ranking Failure in Multi-Agent ✓
- [x] Collect offline data under one opponent distribution (A)
- [x] Estimate policy values using OPE on that data
- [x] Validate against tournament results with opponent A
- [x] Deploy to different opponent distribution (B)
- [x] Show ranking mismatch (OPE top-1 ≠ true top-1 under B)
- [x] Prove "opponent shift" as failure mode
- [x] Visualize ranking correlations under different opponent pools

## Episode 7: Non-Transitivity (Cyclic Dominance) ✓
- [x] Show that policy A > B, B > C, C > A in pairwise comparisons
- [x] Demonstrate why a total ordering is impossible
- [x] Create pairwise win matrix showing cycles
- [x] Plot network showing non-transitive relationships
- [x] Prove that single-scalar ranking is fundamentally fragile

## Episode 8: Dominance-Based Evaluation ✓
- [x] Implement Pareto front computation
- [x] Implement Maximin robustness scoring
- [x] Compute survival under multiple opponent classes
- [x] Create dominance-based policy zoo
- [x] Show Pareto plots (e.g., win rate vs. robustness)
- [x] Compare "fragile top-1 ranking" vs. "robust set of survivors"
- [x] Demonstrate that dominance-based selection is opponent-shift robust

## Episode 9: Midterm Checkpoint ✓
- [x] Consolidate all figures into coherent narrative
- [x] Generate midterm summary (reports/midterm_summary.md)
- [x] Create reproducible pipeline (run_all_midterm.py)
- [x] Document key insights and failure modes
- [x] Prepare for next phase (post-midterm extensions)

## Key Insights Achieved
1. **OPE works in easy settings** when behavior policy covers evaluation policy
2. **Distribution shift breaks OPE** via importance weight degeneracy
3. **Multi-agent introduces opponent shift** as a new failure mode
4. **Cyclic dominance exists** making total ordering impossible
5. **Dominance-based evaluation is more robust** than ranking-based selection

## Environments Implemented
- Gridworld (tabular, single-agent)
- Rock-Paper-Scissors (multi-agent, zero-sum)
- Matching Pennies (multi-agent, zero-sum, symmetric)
- Battle of the Sexes (multi-agent, non-zero-sum, coordination)

## Methods Implemented
- **OPE Estimators**: IS, WIS, PDIS, FQE (tabular)
- **Evaluation**: Tournament play, ranking correlation, ESS
- **Dominance**: Pareto front, maximin robustness, win matrices
- **Utilities**: Seeding, logging, plotting, JSON I/O

## Reproducibility Guarantees
- [x] All experiments use fixed seeds
- [x] All figures auto-generated and saved to reports/figures/
- [x] All data logged to data/ with timestamps
- [x] Pipeline runnable via single command: `python scripts/run_all_midterm.py`
- [x] Episode scripts are independent and re-runnable

---

## Next Phase (Post-Midterm)

### Phase 2 Goals
- [ ] Add continuous control environments (MuJoCo light)
- [ ] Implement deep OPE estimators (neural FQE, MAGIC)
- [ ] Scale multi-agent to > 4 opponents
- [ ] Add causal inference analysis
- [ ] Write conference paper draft

