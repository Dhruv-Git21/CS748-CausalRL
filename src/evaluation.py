"""
Evaluation methods for policies.

Functions:
  - play_matrix_game_expected(game, pi0, pi1): Expected payoff in matrix game
  - tournament_matrix(game, policies): All-vs-all tournament
  - spearman_rank_corr(a, b): Spearman rank correlation
  - top1_mismatch(a, b): Top-1 ranking error
  - pareto_front(points, maximize): Identify Pareto frontier
  - maximin(scores_vs_opponents): Worst-case robustness score
"""
from __future__ import annotations
import numpy as np
from dataclasses import dataclass
from envs import MatrixGame
from policies import MatrixPolicy


# ===== Tournament Play =====

@dataclass
class TournamentResult:
    """Results from matrix game tournament."""

    names: list[str]
    winrate: np.ndarray  # (P, P) winrate[i, j] = P(i beats j)
    mean_payoff: np.ndarray  # (P, P) expected payoff for player i vs j


def play_matrix_game_expected(
    game: MatrixGame, pi0: MatrixPolicy, pi1: MatrixPolicy
) -> float:
    """Expected payoff to player 0."""
    p0 = pi0.probs[:, None]  # (A0, 1)
    p1 = pi1.probs[None, :]  # (1, A1)
    joint = p0 * p1
    return float((joint * game.payoff_p0).sum())


def tournament_matrix(game: MatrixGame, policies: list[MatrixPolicy]) -> TournamentResult:
    """All-vs-all tournament among policies."""
    P = len(policies)
    pay = np.zeros((P, P), dtype=float)
    win = np.zeros((P, P), dtype=float)

    for i in range(P):
        for j in range(P):
            if i == j:
                pay[i, j] = 0.0
                win[i, j] = 0.5
            else:
                pay[i, j] = play_matrix_game_expected(game, policies[i], policies[j])
                # Winrate proxy: payoff > 0 => win
                win[i, j] = 1.0 if pay[i, j] > 0 else (0.5 if pay[i, j] == 0 else 0.0)

    return TournamentResult([p.name for p in policies], win, pay)


# ===== Ranking Metrics =====

def spearman_rank_corr(a: np.ndarray, b: np.ndarray) -> float:
    """Spearman rank correlation between two rankings."""
    ra = np.argsort(np.argsort(a))
    rb = np.argsort(np.argsort(b))
    ra = ra.astype(float)
    rb = rb.astype(float)
    ra -= ra.mean()
    rb -= rb.mean()
    denom = np.linalg.norm(ra) * np.linalg.norm(rb) + 1e-12
    return float((ra @ rb) / denom)


def top1_mismatch(a: np.ndarray, b: np.ndarray) -> int:
    """Check if top-1 elements differ (0 = same, 1 = different)."""
    return int(np.argmax(a) != np.argmax(b))


# ===== Dominance-Based Evaluation =====

def pareto_front(points: np.ndarray, maximize: bool = True) -> np.ndarray:
    """Identify Pareto frontier.
    
    Args:
        points: (N, K) objectives per policy
        maximize: If True, maximize all objectives; else minimize
        
    Returns:
        Boolean mask for non-dominated set
    """
    N = points.shape[0]
    mask = np.ones(N, dtype=bool)

    for i in range(N):
        if not mask[i]:
            continue
        for j in range(N):
            if i == j:
                continue
            if maximize:
                dominates = np.all(points[j] >= points[i]) and np.any(
                    points[j] > points[i]
                )
            else:
                dominates = np.all(points[j] <= points[i]) and np.any(
                    points[j] < points[i]
                )
            if dominates:
                mask[i] = False
                break

    return mask


def maximin(scores_vs_opponents: np.ndarray) -> np.ndarray:
    """Worst-case (maximin) robustness score.
    
    Args:
        scores_vs_opponents: (N, M) performance vs each opponent class
        
    Returns:
        (N,) minimum score for each policy (worst case)
    """
    return scores_vs_opponents.min(axis=1)
