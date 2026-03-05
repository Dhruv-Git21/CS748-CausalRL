# API Reference (v2)

## Core Modules

This document provides function and class signatures for the `src/` library.

---

## `src.envs`

### Classes

#### `GridworldConfig`
```python
class GridworldConfig:
    """Configuration for Gridworld environment."""
    width: int          # Grid width (default: 5)
    height: int         # Grid height (default: 5)
    goal: tuple[int, int]  # Goal position (default: (4, 4))
    slip: float         # Slip probability (default: 0.1)
```

#### `Gridworld`
```python
class Gridworld:
    \"\"\"Single-agent tabular gridworld environment.\"\"\"
    
    def __init__(self, cfg: GridworldConfig):
        \"\"\"Initialize Gridworld with config.\"\"\"
    
    @property
    def nS(self) -> int:
        \"\"\"Number of states.\"\"\"
    
    @property
    def nA(self) -> int:
        \"\"\"Number of actions (4: up, down, left, right).\"\"\"
    
    def reset(self) -> int:
        \"\"\"Reset to initial state (0).\"\"\"
        return: int  # Initial state
    
    def step(self, a: int, rng: np.random.Generator) -> tuple[int, float, bool, dict]:
        \"\"\"Execute action in environment.\"\"\"
        return: (next_state, reward, done, info)
            next_state: int
            reward: float  # +1 at goal, else 0
            done: bool  # True if at goal
            info: dict  # metadata
```

#### `MatrixGame`
```python
class MatrixGame:
    \"\"\"Two-player matrix game (zero/non-zero sum).\"\"\"
    
    def __init__(self, payoff_p0: np.ndarray, payoff_p1: np.ndarray = None):
        \"\"\"Initialize with payoff matrices.\"\"\"
        # Shape: (nA_p0, nA_p1)
        # If payoff_p1 is None, assumes zero-sum (payoff_p1 = -payoff_p0)
    
    @property
    def nA_p0(self) -> int:
        \"\"\"Actions for player 0.\"\"\"
    
    @property
    def nA_p1(self) -> int:
        \"\"\"Actions for player 1.\"\"\"
    
    def payoff(self, a0: int, a1: int) -> tuple[float, float]:
        \"\"\"Get payoffs for both players.\"\"\"
        return: (payoff_p0, payoff_p1)
```

### Factory Functions

```python
def matching_pennies() -> MatrixGame:
    \"\"\"Rock-Paper-Scissors game (symmetric, cyclic).\"\"\"

def rock_paper_scissors() -> MatrixGame:
    \"\"\"RPS game (symmetric, zero-sum, cyclic).\"\"\"

def battle_of_sexes() -> MatrixGame:
    \"\"\"2x2 coordination game (non-zero-sum).\"\"\"
```

---

## `src.policies`

### Classes

#### `TabularPolicy`
```python
class TabularPolicy:
    \"\"\"Policy for tabular environments (state → action distribution).\"\"\"
    
    def __init__(self, name: str, probs: np.ndarray):
        \"\"\"Initialize with action probabilities.\"\"\"
        # probs: (nS, nA), each row sums to 1
    
    def act(self, s: int, rng: np.random.Generator) -> int:
        \"\"\"Sample action from state.\"\"\"
        return: int  # Action index
    
    def prob(self, s: int, a: int) -> float:
        \"\"\"Probability of action in state.\"\"\"
        return: float  # π(a|s)
    
    @property
    def name(self) -> str:
        \"\"\"Human-readable name.\"\"\"
    
    @property
    def probs(self) -> np.ndarray:
        \"\"\"Full probability matrix (nS, nA).\"\"\"
```

#### `MatrixPolicy`
```python
class MatrixPolicy:
    \"\"\"Policy for matrix games (action distribution, no state).\"\"\"
    
    def __init__(self, name: str, probs: np.ndarray):
        \"\"\"Initialize with action probabilities.\"\"\"
        # probs: (nA,), sums to 1
    
    def act(self, rng: np.random.Generator) -> int:
        \"\"\"Sample action (no state argument).\"\"\"
        return: int  # Action index
    
    def prob(self, a: int) -> float:
        \"\"\"Probability of action.\"\"\"
        return: float  # π(a)
    
    @property
    def name(self) -> str:
        \"\"\"Human-readable name.\"\"\"
    
    @property
    def probs(self) -> np.ndarray:
        \"\"\"Full probability vector (nA,).\"\"\"
```

### Factory Functions

```python
def random_tabular_policy(name: str, nS: int, nA: int) -> TabularPolicy:
    \"\"\"Uniform random policy.\"\"\"

def epsilon_greedy_from_q(name: str, Q: np.ndarray, eps: float = 0.1) -> TabularPolicy:
    \"\"\"ε-greedy policy from Q-values.\"\"\"
    # Q shape: (nS, nA)

def uniform_matrix_policy(name: str, nA: int) -> MatrixPolicy:
    \"\"\"Uniform random policy for matrix games.\"\"\"

def biased_matrix_policy(name: str, probs: np.ndarray) -> MatrixPolicy:
    \"\"\"Custom probability distribution.\"\"\"
    # probs shape: (nA,)
```

---

## `src.ope`

### Dataclasses

#### `OPEStats`
```python
@dataclass
class OPEStats:
    \"\"\"Statistics from OPE estimator.\"\"\"
    mean: float     # Estimated value
    std: float      # Standard error
    ess: float      # Effective Sample Size
    mse: float      # Mean Squared Error (if true value known)
```

#### `FQEResult`
```python
@dataclass
class FQEResult:
    \"\"\"Result from Fitted Q-Evaluation.\"\"\"
    Q: np.ndarray   # Learned Q-values (nS, nA)
    values: np.ndarray  # Estimated policy values (nS,)
    policy_value: float  # Integrated value estimate
```

### Functions

```python
def importance_sampling(
    returns: np.ndarray,
    ratios: np.ndarray,
    clip: float | None = None,
    true_value: float | None = None
) -> OPEStats:
    \"\"\"Importance Sampling estimator.\"\"\"
    # returns shape: (N,)  — episode returns
    # ratios shape: (N,)   — importance weights (product of π/μ)
    # clip: optional clipping threshold for weights
    # true_value: for computing MSE

def weighted_is(
    returns: np.ndarray,
    ratios: np.ndarray,
    clip: float | None = None,
    true_value: float | None = None
) -> OPEStats:
    \"\"\"Weighted Importance Sampling (normalized weights).\"\"\"

def per_decision_is(
    rewards: np.ndarray,
    step_ratios: np.ndarray,
    gamma: float = 0.99,
    clip: float | None = None
) -> float:
    \"\"\"Per-Decision Importance Sampling (step-wise weighting).\"\"\"
    # rewards shape: (N, T)  — per-step rewards
    # step_ratios shape: (N, T)  — per-step importance weights
    return: float  # Estimated value

def fitted_q_evaluation_tabular(
    batch,  # TrajectoryBatch
    env,    # Gridworld
    gamma: float = 0.99,
    iterations: int = 100
) -> FQEResult:
    \"\"\"Fitted Q-Evaluation (model-free value estimation).\"\"\"
```

---

## `src.evaluation`

### Dataclasses

#### `TournamentResult`
```python
@dataclass
class TournamentResult:
    \"\"\"Result from tournament play.\"\"\"
    win_matrix: np.ndarray   # (n_policies, n_policies)
    payoff_matrix: np.ndarray  # (n_policies, n_policies)
    policy_names: list[str]
```

### Functions

```python
def play_matrix_game_expected(
    game: MatrixGame,
    pi0: MatrixPolicy,
    pi1: MatrixPolicy
) -> float:
    \"\"\"Compute expected payoff for pi0 vs. pi1.\"\"\"
    return: float  # E[payoff_pi0]

def tournament_matrix(
    game: MatrixGame,
    policies: list[MatrixPolicy]
) -> TournamentResult:
    \"\"\"Play all-pairs tournament.\"\"\"
    # Plays each pair (i, j) both ways (i vs j, j vs i)

def spearman_rank_corr(a: np.ndarray, b: np.ndarray) -> float:
    \"\"\"Spearman rank correlation.\"\"\"
    # a, b shape: (n,)
    # Each element is a scalar value (will be ranked)
    return: float  # ρ ∈ [-1, 1]

def top1_mismatch(a: np.ndarray, b: np.ndarray) -> bool:
    \"\"\"Check if top-1 ranking differs.\"\"\"
    # a, b shape: (n,)
    return: bool  # True if argmax(a) != argmax(b)

def pareto_front(
    points: np.ndarray,
    maximize: bool = True
) -> np.ndarray:
    \"\"\"Compute Pareto front indices.\"\"\"
    # points shape: (n, d)  — d-dimensional objectives
    # maximize: True if maximizing, False if minimizing
    return: np.ndarray  # Boolean mask (n,) — True for Pareto-optimal points

def maximin_robustness(
    scores_vs_opponents: np.ndarray
) -> np.ndarray:
    \"\"\"Compute maximin robustness score for each policy.\"\"\"
    # scores shape: (n_policies, n_opponents)
    # Each row: policy's score against each opponent
    return: np.ndarray  # (n_policies,) — min score for each policy
```

---

## `src.utils`

### Dataclasses

#### `TrajectoryBatch`
```python
@dataclass
class TrajectoryBatch:
    \"\"\"Batch of offline trajectories.\"\"\"
    states: np.ndarray      # Shape: (N, T)
    actions: np.ndarray     # Shape: (N, T)
    rewards: np.ndarray     # Shape: (N, T)
    behavior_probs: np.ndarray  # Shape: (N, T)
    eval_probs: np.ndarray  # Shape: (N, T)
    
    def returns(self, gamma: float = 0.99) -> np.ndarray:
        \"\"\"Compute discounted returns for each trajectory.\"\"\"
        return: np.ndarray  # Shape: (N,)
    
    def traj_ratios(self) -> np.ndarray:
        \"\"\"Compute trajectory importance weights.\"\"\"
        return: np.ndarray  # Shape: (N,)
    
    def step_cum_ratios(self) -> np.ndarray:
        \"\"\"Compute cumulative step-wise importance ratios.\"\"\"
        return: np.ndarray  # Shape: (N, T)
```

### Functions

```python
def set_seed(seed: int) -> None:
    \"\"\"Set global random seed (numpy + random).\"\"\"

def collect_batch(
    env: Gridworld,
    beh: TabularPolicy,  # Behavior policy
    pi: TabularPolicy,   # Evaluation policy
    N: int,              # Number of trajectories
    T: int,              # Trajectory length
    seed: int = 0
) -> TrajectoryBatch:
    \"\"\"Collect offline trajectories from environment.\"\"\"

def save_json(path: str | Path, obj: dict) -> None:
    \"\"\"Save dictionary to JSON file.\"\"\"

def load_json(path: str | Path) -> dict:
    \"\"\"Load dictionary from JSON file.\"\"\"

def ensure_dir(path: str | Path) -> Path:
    \"\"\"Create directory if not exists (recursive).\"\"\"
    return: Path  # Directory path

def savefig(path: str | Path, dpi: int = 180) -> None:
    \"\"\"Save matplotlib figure (clear after saving).\"\"\"

def plot_heatmap(
    mat: np.ndarray,
    xlabels: list[str] | None = None,
    ylabels: list[str] | None = None,
    title: str = \"\",
    outpath: str | Path = \"heatmap.png\"
) -> None:
    \"\"\"Plot 2D heatmap and save.\"\"\"

def plot_hist(
    x: np.ndarray,
    title: str,
    xlabel: str,
    outpath: str | Path
) -> None:
    \"\"\"Plot histogram and save.\"\"\"

def plot_scatter(
    x: np.ndarray,
    y: np.ndarray,
    title: str,
    xlabel: str,
    ylabel: str,
    outpath: str | Path,
    labels: list[str] | None = None
) -> None:
    \"\"\"Plot scatter plot and save.\"\"\"
```

---

## Common Patterns

### Pattern 1: Collecting and Evaluating
```python
from src.envs import Gridworld, GridworldConfig
from src.policies import random_tabular_policy, epsilon_greedy_from_q
from src.utils import collect_batch, set_seed
from src.ope import importance_sampling

# Setup
set_seed(42)
env = Gridworld(GridworldConfig(width=5, height=5))
beh = random_tabular_policy("behavior", env.nS, env.nA)
pi = epsilon_greedy_from_q("eval", Q_values, eps=0.1)

# Collect data
batch = collect_batch(env, beh, pi, N=1000, T=50, seed=42)

# Evaluate
returns = batch.returns(gamma=0.99)
ratios = batch.traj_ratios()
stats = importance_sampling(returns, ratios, clip=10.0)
print(f"OPE estimate: {stats.mean:.3f} ± {stats.std:.3f}")
```

### Pattern 2: Matrix Game Tournament
```python
from src.envs import rock_paper_scissors
from src.policies import biased_matrix_policy
from src.evaluation import tournament_matrix, pareto_front

game = rock_paper_scissors()
policies = [
    biased_matrix_policy("Rock", [0.8, 0.1, 0.1]),
    biased_matrix_policy("Paper", [0.1, 0.8, 0.1]),
    biased_matrix_policy("Scissors", [0.1, 0.1, 0.8]),
    biased_matrix_policy("Uniform", [1/3, 1/3, 1/3])
]

result = tournament_matrix(game, policies)
pareto_idx = pareto_front(result.payoff_matrix, maximize=True)
print("Pareto-optimal policies:", [policies[i].name for i in range(len(policies)) if pareto_idx[i]])
```

### Pattern 3: Save & Load Metadata
```python
from src.utils import save_json, load_json
import datetime

metadata = {
    "experiment": "exp_01",
    "seed": 42,
    "timestamp": datetime.datetime.now().isoformat(),
    "results": {
        "spearman_rho": 0.92,
        "top1_mismatch": False,
        "mse": 0.045
    }
}

save_json("results/data/exp_01_metadata.json", metadata)
loaded = load_json("results/data/exp_01_metadata.json")
```

---

## Type Hints

All functions use Python 3.10+ type hints. Key types:

```python
np.ndarray          # NumPy array (type depends on context)
int | None          # Optional int (Python 3.10+ union syntax)
list[str]           # List of strings
tuple[int, int]     # Tuple of two ints
```

---

## Error Handling

### Common Errors

**ValueError: ratios must have same length as returns**
- Ensure `ratios.shape[0] == returns.shape[0]`

**IndexError: state out of bounds**
- Ensure `0 <= state < env.nS`

**ValueError: action out of bounds**
- Ensure `0 <= action < env.nA` (or `env.nA_p0` for matrix games)

**AssertionError in importance_sampling**
- Ensure all weights sum to > 0 (not all zero)
- Check for numerical underflow with `clip` parameter

---

## See Also

- [ARCHITECTURE.md](ARCHITECTURE.md) — Design rationale
- [EXPERIMENT_GUIDE.md](EXPERIMENT_GUIDE.md) — How to use in experiments

