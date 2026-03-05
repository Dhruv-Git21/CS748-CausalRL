"""
Policy representations for agents.

Classes:
  - TabularPolicy: State-based policy for single-agent domains
  - MatrixPolicy: Action-only policy for matrix games

Functions:
  - random_policy(nS, nA): Uniform random policy
  - epsilon_greedy_from_q(Q, eps): Epsilon-greedy from Q-values
  - uniform_matrix_policy(nA): Uniform policy for matrix games
  - biased_matrix_policy(nA, bias_action, bias_prob): Biased policy for matrix games
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np


# ===== Tabular Policy =====

@dataclass
class TabularPolicy:
    """Policy with state-based action probabilities."""

    name: str
    probs: np.ndarray  # (nS, nA)

    def act(self, s: int, rng: np.random.Generator) -> int:
        """Sample action from state s."""
        return rng.choice(len(self.probs[s]), p=self.probs[s])

    def prob(self, s: int, a: int) -> float:
        """Get probability of action a in state s."""
        return float(self.probs[s, a])


def random_policy(nS: int, nA: int) -> TabularPolicy:
    """Create uniformly random policy."""
    probs = np.ones((nS, nA)) / nA
    return TabularPolicy("random", probs)


def epsilon_greedy_from_q(q: np.ndarray, eps: float = 0.1) -> TabularPolicy:
    """Create epsilon-greedy policy from Q-values."""
    nS, nA = q.shape
    probs = np.ones((nS, nA)) * eps / nA
    greedy = np.argmax(q, axis=1)
    probs[np.arange(nS), greedy] += 1.0 - eps
    return TabularPolicy("eps_greedy", probs)


# ===== Matrix Policy =====

@dataclass
class MatrixPolicy:
    """Policy with fixed action probabilities (for matrix games)."""

    name: str
    probs: np.ndarray  # (nA,)

    def act(self, rng: np.random.Generator) -> int:
        """Sample action."""
        return rng.choice(len(self.probs), p=self.probs)

    def prob(self, a: int) -> float:
        """Get probability of action a."""
        return float(self.probs[a])


def uniform_matrix_policy(nA: int) -> MatrixPolicy:
    """Create uniformly random policy for matrix games."""
    probs = np.ones(nA) / nA
    return MatrixPolicy("uniform", probs)


def biased_matrix_policy(
    nA: int, bias_action: int = 0, bias_prob: float = 0.6
) -> MatrixPolicy:
    """Create biased policy for matrix games."""
    probs = np.ones(nA) * (1.0 - bias_prob) / (nA - 1)
    probs[bias_action] = bias_prob
    return MatrixPolicy(f"biased_a{bias_action}", probs)
