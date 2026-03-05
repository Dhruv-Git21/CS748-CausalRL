"""
Off-Policy Evaluation (OPE) estimators.

Classes:
  - OPEStats: Container for OPE results (estimate, ESS, weights)
  - FQEResult: Container for Fitted Q-Evaluation results

Functions:
  - importance_sampling(returns, weights): IS estimator
  - weighted_is(returns, weights): Weighted importance sampling
  - per_decision_is(returns, step_ratios): Per-decision IS
  - fitted_q_evaluation_tabular(...): FQE for tabular MDPs
"""
from __future__ import annotations
import numpy as np
from dataclasses import dataclass


# ===== Importance Sampling Estimators =====

@dataclass
class OPEStats:
    """Results from OPE estimation."""

    estimate: float
    ess: float  # Effective sample size
    weights: np.ndarray


def importance_sampling(returns: np.ndarray, weights: np.ndarray) -> OPEStats:
    """Standard importance sampling estimator."""
    estimate = float(np.mean(returns * weights))
    ess = float((weights.sum() ** 2) / (weights ** 2).sum())
    return OPEStats(estimate, ess, weights)


def weighted_is(returns: np.ndarray, weights: np.ndarray) -> OPEStats:
    """Weighted importance sampling (self-normalized)."""
    w_norm = weights / (weights.sum() + 1e-12)
    estimate = float(np.mean(returns * w_norm * len(weights)))
    ess = float((weights.sum() ** 2) / (weights ** 2).sum())
    return OPEStats(estimate, ess, w_norm)


def per_decision_is(returns: np.ndarray, step_ratios: np.ndarray) -> OPEStats:
    """Per-decision importance sampling.
    
    Args:
        returns: (N,) trajectory returns
        step_ratios: (N, T) cumulative importance ratios per step
    """
    t_max = step_ratios.shape[1]
    weights = np.mean(step_ratios, axis=1)
    estimate = float(np.mean(returns * weights))
    ess = (
        float((weights.sum() ** 2) / (weights ** 2).sum())
        if weights.sum() > 0
        else 0.0
    )
    return OPEStats(estimate, ess, weights)


# ===== Fitted Q-Evaluation =====

@dataclass
class FQEResult:
    """Results from FQE."""

    v0: float  # Estimated value from start state
    q: np.ndarray  # Q-values (nS, nA)


def fitted_q_evaluation_tabular(
    transitions: list[tuple[int, int, float, int, bool]],
    nS: int,
    nA: int,
    pi_probs: np.ndarray,  # (nS, nA)
    gamma: float = 0.99,
    n_iters: int = 200,
) -> FQEResult:
    """Tabular Fitted Q-Evaluation via Bellman backup.
    
    Args:
        transitions: List of (s, a, r, s_next, done) tuples
        nS: Number of states
        nA: Number of actions
        pi_probs: Policy probabilities (nS, nA)
        gamma: Discount factor
        n_iters: Number of iterations
    """
    q = np.zeros((nS, nA), dtype=float)

    # Group samples by (s, a)
    bucket = [[[] for _ in range(nA)] for __ in range(nS)]
    for s, a, r, s2, done in transitions:
        bucket[s][a].append((r, s2, done))

    for _ in range(n_iters):
        q_new = q.copy()
        v_next = (pi_probs * q).sum(axis=1)  # V(s) under pi
        for s in range(nS):
            for a in range(nA):
                samples = bucket[s][a]
                if not samples:
                    continue
                targets = []
                for r, s2, done in samples:
                    target = r + (0.0 if done else gamma * v_next[s2])
                    targets.append(target)
                q_new[s, a] = float(np.mean(targets))
        q = q_new

    v0 = float((pi_probs[0] * q[0]).sum())
    return FQEResult(v0=v0, q=q)
