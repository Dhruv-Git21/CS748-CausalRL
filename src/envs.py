"""
Environments for RL experiments.

Classes:
  - GridworldConfig: Configuration for tabular gridworld
  - Gridworld: Tabular gridworld environment

Functions:
  - matching_pennies(): Rock-Paper-Scissors style game
  - rock_paper_scissors(): RPS game
  - battle_of_sexes(): Coordination game
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np


# ===== Gridworld =====

@dataclass
class GridworldConfig:
    """Configuration for gridworld environment."""
    width: int = 5
    height: int = 5
    start: tuple[int, int] = (0, 0)
    goal: tuple[int, int] = (4, 4)
    slip: float = 0.0


class Gridworld:
    """Simple gridworld environment with tabular representation."""

    def __init__(self, cfg: GridworldConfig = GridworldConfig()):
        self.cfg = cfg
        self.nS = cfg.width * cfg.height
        self.nA = 4  # up, right, down, left
        self._state = None

    def reset(self) -> int:
        """Reset to start state."""
        self._state = self.cfg.start[0] * self.cfg.width + self.cfg.start[1]
        return self._state

    def step(self, action: int, rng: np.random.Generator = None) -> tuple:
        """Execute action and return (next_state, reward, done, info)."""
        if rng is None:
            rng = np.random.default_rng()

        if rng.random() < self.cfg.slip:
            action = rng.integers(0, self.nA)

        x, y = self._state // self.cfg.width, self._state % self.cfg.width

        if action == 0:  # up
            x = max(0, x - 1)
        elif action == 1:  # right
            y = min(self.cfg.width - 1, y + 1)
        elif action == 2:  # down
            x = min(self.cfg.height - 1, x + 1)
        elif action == 3:  # left
            y = max(0, y - 1)

        self._state = x * self.cfg.width + y
        done = (x, y) == self.cfg.goal
        reward = 1.0 if done else -0.01

        return self._state, reward, done, {}


# ===== Matrix Games =====

@dataclass
class MatrixGame:
    """Two-player matrix game."""
    name: str
    payoff_p0: np.ndarray  # (A0, A1) payoff to player 0
    payoff_p1: np.ndarray  # (A0, A1) payoff to player 1


def matching_pennies() -> MatrixGame:
    """Zero-sum matching pennies game."""
    payoff_p0 = np.array([[1.0, -1.0], [-1.0, 1.0]])
    payoff_p1 = -payoff_p0.copy()
    return MatrixGame("matching_pennies", payoff_p0, payoff_p1)


def rock_paper_scissors() -> MatrixGame:
    """Classic cyclic zero-sum game."""
    payoff_p0 = np.array(
        [[0.0, -1.0, 1.0], [1.0, 0.0, -1.0], [-1.0, 1.0, 0.0]]
    )
    payoff_p1 = -payoff_p0.copy()
    return MatrixGame("rock_paper_scissors", payoff_p0, payoff_p1)


def battle_of_sexes() -> MatrixGame:
    """Coordination game (non zero-sum)."""
    payoff_p0 = np.array([[2.0, 0.0], [0.0, 1.0]])
    payoff_p1 = np.array([[1.0, 0.0], [0.0, 2.0]])
    return MatrixGame("battle_of_sexes", payoff_p0, payoff_p1)
