# v2 Documentation Index

Complete guide to all v2 documentation files and how to use them.

---

## 📚 Documentation Files (in reading order)

### 1. **QUICKSTART.md** (5 minutes)
**Start here if you're in a hurry.**

What you get:
- Installation in 3 steps
- How to run experiments (1 command)
- Where outputs go
- Key documents reference

When to read:
- First time setup
- Rapid prototyping
- Just want to see plots

---

### 2. **README.md** (10 minutes)
**Main entry point — read this after QUICKSTART.**

What you get:
- Project goal (OPE failures in multi-agent RL)
- Visual results summary (what each experiment shows)
- Complete directory map
- Implementation checklist
- FAQ & troubleshooting

When to read:
- Understanding the big picture
- Before writing a report
- Explaining project to others

---

### 3. **V2_SUMMARY.md** (15 minutes)
**Overview of what was created in v2 reorganization.**

What you get:
- What was done (6 doc files created)
- What's ready vs. what needs conversion
- Key design decisions
- Statistics and file manifest
- Success criteria for verification

When to read:
- Assessing project completeness
- Planning next steps
- Understanding design philosophy

---

### 4. **docs/ACHIEVEMENTS.md** (20 minutes)
**Comprehensive checklist of Episodes 1-9.**

What you get:
- All 9 episodes completed (✓ checkmarks)
- 4 environments implemented
- 4 methods implemented
- Key insights achieved
- Post-midterm goals

When to read:
- Taking stock of what's been done
- Writing a midterm summary
- Planning Phase 2

---

### 5. **docs/EXPERIMENT_GUIDE.md** (30 minutes)
**How to run and interpret each of the 5 experiments.**

What you get:
- Exp 1: OPE Works (good coverage)
- Exp 2: OPE Fails (distribution shift)
- Exp 3: Opponent Shift (multi-agent)
- Exp 4: Non-Transitivity (cycles)
- Exp 5: Dominance Robust (robust to shift)
- Expected outputs for each
- Troubleshooting guide

When to read:
- Before running experiments
- Interpreting experiment results
- Modifying experiment parameters
- Understanding failure modes

---

### 6. **docs/ARCHITECTURE.md** (30 minutes)
**Code design, module organization, and extension patterns.**

What you get:
- Project philosophy (research-grade + beginner-friendly)
- Directory structure explained
- 5 core modules (`src/`) documented:
  - `envs.py` — Gridworld, MatrixGame
  - `policies.py` — TabularPolicy, MatrixPolicy
  - `ope.py` — IS/WIS/PDIS/FQE
  - `evaluation.py` — Tournament, dominance
  - `utils.py` — Seeding, logging, plotting
- How to add new environments/estimators/experiments
- Design principles
- Dependency minimalism

When to read:
- Adding new code to src/
- Creating a new experiment
- Understanding why code is structured this way
- Extending with new methods

---

### 7. **docs/API_REFERENCE.md** (30 minutes)
**Function signatures and class documentation.**

What you get:
- All public classes (GridworldConfig, Gridworld, MatrixGame, TabularPolicy, etc.)
- All public functions (importance_sampling, pareto_front, collect_batch, etc.)
- Type hints for every parameter
- Return types
- Usage examples
- Error handling patterns

When to read:
- Writing code that uses src/
- Understanding function signatures
- Copy-pasting examples
- Debugging import errors

---

### 8. **docs/RESULTS_FRAMEWORK.md** (40 minutes)
**How to read, interpret, and compare experimental results.**

What you get:
- Output directory structure
- Metadata JSON format
- Key metrics explained:
  - Spearman ρ (rank correlation)
  - ESS (effective sample size)
  - MSE (mean squared error)
  - Top-1 mismatch
  - Kendall τ
- 5 plot types explained:
  - Scatter (OPE vs. true)
  - Bar chart (ranking)
  - Heatmap (win matrix)
  - Network (cycles)
  - Pareto front
- How to interpret each
- Statistical significance
- Exporting results

When to read:
- Analyzing experiment outputs
- Writing a report
- Comparing two experiments
- Understanding a metric

---

### 9. **docs/TRANSLATION_GUIDE.md** (25 minutes)
**Map between original episodes and v2 experiments.**

What you get:
- Side-by-side comparison (episodes vs. experiments)
- Episode → Experiment mapping (detailed)
- What's the same, what's different for each exp
- Information flow diagram
- Conversion checklist
- Coexistence strategy

When to read:
- Converting episode scripts to experiments
- Understanding relationship between original and v2
- Explaining to others why v2 exists
- Running both in parallel

---

## 📖 Reading Paths

### Path 1: "Just Run It" (5 minutes)
For: Quick demo, see what happens
1. [QUICKSTART.md](QUICKSTART.md) — Installation
2. Run `python experiments/run_all_experiments.py`
3. Open `results/figures/` → Done!

### Path 2: "Understand & Extend" (60 minutes)
For: Researchers wanting to modify experiments
1. [QUICKSTART.md](QUICKSTART.md) — Setup
2. [README.md](README.md) — Big picture
3. [docs/EXPERIMENT_GUIDE.md](docs/EXPERIMENT_GUIDE.md) — Each experiment
4. Run experiments, analyze with [docs/RESULTS_FRAMEWORK.md](docs/RESULTS_FRAMEWORK.md)
5. Modify an experiment, re-run

### Path 3: "Implement & Contribute" (120 minutes)
For: Adding new methods or environments
1. [QUICKSTART.md](QUICKSTART.md) — Setup
2. [V2_SUMMARY.md](V2_SUMMARY.md) — Project structure
3. [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — Code design
4. [docs/API_REFERENCE.md](docs/API_REFERENCE.md) — Function signatures
5. Write code in `src/`
6. Create new experiment using [docs/EXPERIMENT_GUIDE.md](docs/EXPERIMENT_GUIDE.md) as template

### Path 4: "Write a Paper" (180 minutes)
For: Academic publication
1. [README.md](README.md) — Motivation
2. [docs/ACHIEVEMENTS.md](docs/ACHIEVEMENTS.md) — What's been done
3. [V2_SUMMARY.md](V2_SUMMARY.md) — Project organization
4. Run `python experiments/run_all_experiments.py`
5. Analyze with [docs/RESULTS_FRAMEWORK.md](docs/RESULTS_FRAMEWORK.md)
6. Create figures/tables for paper
7. Write methods section using [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

### Path 5: "Teach This" (150 minutes)
For: Course instructors or mentors
1. [README.md](README.md) — Explain goal
2. [docs/ACHIEVEMENTS.md](docs/ACHIEVEMENTS.md) — What's done
3. [docs/EXPERIMENT_GUIDE.md](docs/EXPERIMENT_GUIDE.md) — Detailed explanations
4. [docs/TRANSLATION_GUIDE.md](docs/TRANSLATION_GUIDE.md) — Link to original episodes
5. Create assignments: "Modify exp_01 to use N=10000, what changes?"

---

## 🎯 By User Type

### For **Beginners** (new to OPE)
Start here:
1. [QUICKSTART.md](QUICKSTART.md) — 5 min
2. [README.md](README.md) — 10 min
3. [docs/EXPERIMENT_GUIDE.md](docs/EXPERIMENT_GUIDE.md) → Run exp_01

### For **Researchers** (extending this work)
Start here:
1. [README.md](README.md) — Big picture
2. [docs/EXPERIMENT_GUIDE.md](docs/EXPERIMENT_GUIDE.md) — What each does
3. [docs/RESULTS_FRAMEWORK.md](docs/RESULTS_FRAMEWORK.md) — How to interpret
4. [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — How to extend

### For **Developers** (adding code)
Start here:
1. [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — Code organization
2. [docs/API_REFERENCE.md](docs/API_REFERENCE.md) — Function signatures
3. Read source code in `src/`
4. Create new experiment/method

### For **Instructors** (teaching with this)
Start here:
1. [README.md](README.md) — Project goal
2. [docs/ACHIEVEMENTS.md](docs/ACHIEVEMENTS.md) — What's implemented
3. [docs/EXPERIMENT_GUIDE.md](docs/EXPERIMENT_GUIDE.md) — Detailed explanations
4. [docs/TRANSLATION_GUIDE.md](docs/TRANSLATION_GUIDE.md) — Link to episodes

### For **Managers** (assessing project)
Start here:
1. [V2_SUMMARY.md](V2_SUMMARY.md) — What was created
2. [docs/ACHIEVEMENTS.md](docs/ACHIEVEMENTS.md) — Completion status
3. [README.md](README.md) — Visual results

---

## 📊 Document Statistics

| Document | Lines | Type | Est. Reading Time |
|----------|-------|------|-------------------|
| QUICKSTART.md | 150+ | Quick ref | 5 min |
| README.md | 600+ | Overview | 10 min |
| V2_SUMMARY.md | 350+ | Meta-docs | 15 min |
| ACHIEVEMENTS.md | 220+ | Checklist | 20 min |
| EXPERIMENT_GUIDE.md | 350+ | Tutorial | 30 min |
| ARCHITECTURE.md | 400+ | Reference | 30 min |
| API_REFERENCE.md | 250+ | Reference | 30 min |
| RESULTS_FRAMEWORK.md | 300+ | Tutorial | 40 min |
| TRANSLATION_GUIDE.md | 300+ | Mapping | 25 min |
| INDEX (this file) | 400+ | Navigation | 15 min |
| **TOTAL** | **3,320+** | **9 files** | **220 min (3.5 hours)** |

---

## 🔍 Quick Lookup

### "How do I..."

**...run experiments?**
→ [QUICKSTART.md](QUICKSTART.md) or [docs/EXPERIMENT_GUIDE.md](docs/EXPERIMENT_GUIDE.md)

**...understand what each experiment does?**
→ [docs/EXPERIMENT_GUIDE.md](docs/EXPERIMENT_GUIDE.md)

**...interpret the plots?**
→ [docs/RESULTS_FRAMEWORK.md](docs/RESULTS_FRAMEWORK.md)

**...add a new method?**
→ [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) or [docs/API_REFERENCE.md](docs/API_REFERENCE.md)

**...convert an episode script?**
→ [docs/TRANSLATION_GUIDE.md](docs/TRANSLATION_GUIDE.md)

**...understand the design philosophy?**
→ [V2_SUMMARY.md](V2_SUMMARY.md) or [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

**...explain this project to someone?**
→ [README.md](README.md)

**...know what's been completed?**
→ [docs/ACHIEVEMENTS.md](docs/ACHIEVEMENTS.md)

---

## 📋 Checklist Before You Start

- [ ] Read [QUICKSTART.md](QUICKSTART.md) ← You are here
- [ ] Install: `pip install -r requirements.txt`
- [ ] Run: `python experiments/run_all_experiments.py`
- [ ] Check: `v2/results/figures/` and `v2/results/data/` created?
- [ ] Read [README.md](README.md) to understand results
- [ ] Pick a reading path above based on your goal
- [ ] Deep-dive into relevant documentation

---

## 🎓 Learning Objectives

After reading this documentation, you should be able to:

✅ Install and run the v2 experiments  
✅ Understand what each experiment tests  
✅ Interpret the plots and metrics  
✅ Add a new experiment or method  
✅ Reproduce results exactly  
✅ Explain the research contribution  
✅ Extend for your own research  

---

## 📝 How to Use This Index

1. **Find your use case** in "By User Type" above
2. **Follow the reading path** suggested
3. **Use "Quick Lookup"** when you need specific information
4. **Refer back** to document statistics if you need timing estimates

---

## 🔗 Document Interdependencies

```
QUICKSTART.md
    └── README.md
        ├── docs/EXPERIMENT_GUIDE.md
        ├── docs/ARCHITECTURE.md
        │   └── docs/API_REFERENCE.md
        ├── docs/RESULTS_FRAMEWORK.md
        └── V2_SUMMARY.md
            └── docs/ACHIEVEMENTS.md
                └── docs/TRANSLATION_GUIDE.md
```

Read in this order for maximum comprehension, or jump to what you need.

---

**Index Status**: Complete ✓  
**Total v2 Documentation**: 3,320+ lines across 9 files  
**Coverage**: Setup, experiments, code, results, architecture, teaching, extension  

