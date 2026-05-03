"""
Causal Counterfactual OPE Estimators.

Novel contributions:
  - Probability of Regret (PoR): P(pi_A beats pi_B in same context)
  - Probability of Being Best (PoB): P(pi_k beats ALL others in same context)
  - Counterfactual Dominance Matrix: Pairwise PoR for a policy set
  - Misranking Probability Bound: Theoretical upper bound from Theorem 1

Core idea: For each observed trajectory i, we compare policies NOT by their
average estimated value, but by "who would have done better in THIS specific
context". This matched-pair comparison eliminates common context variance,
making the comparison more robust to distribution shift.

Mathematical foundation:
  PoR(A, B) = E_tau[ 1[G_A(tau) > G_B(tau)] ]
             ≈ (1/N) sum_i 1[ G_i * w_A^i > G_i * w_B^i ]   [IS version]
             ≈ (1/N) sum_i 1[ g_A^i > g_B^i ]               [WIS version]
  where g_A^i = G_i * w_A^i / mean(w_A) (WIS-normalized counterfactual score)

Reference: Kawakami and Tian, "Potential Outcome Rankings for Counterfactual
Decision Making", arXiv:2511.10776, 2025.
"""
from __future__ import annotations
import numpy as np
from dataclasses import dataclass


@dataclass
class PoRResult:
    """Results from Probability of Regret estimation."""
    por_matrix: np.ndarray   # (K, K) PoR[i,j] = P(pi_i beats pi_j)
    pob: np.ndarray          # (K,) PoB[k] = P(pi_k beats all others)
    por_ranking: np.ndarray  # (K,) indices sorted by PoR win-rate (descending)
    ev_ranking: np.ndarray   # (K,) indices sorted by E[V] (descending)
    method: str              # 'IS' or 'WIS'


def _counterfactual_scores_is(
    returns: np.ndarray,      # (N,) observed trajectory returns
    weights_list: list[np.ndarray],  # K arrays of (N,) importance weights
) -> np.ndarray:
    """
    IS counterfactual scores: g_k^i = G_i * w_k^i
    Returns: (K, N) matrix of IS counterfactual scores per policy per trajectory.
    """
    N = len(returns)
    K = len(weights_list)
    scores = np.zeros((K, N))
    for k, w in enumerate(weights_list):
        scores[k] = returns * w
    return scores


def _counterfactual_scores_wis(
    returns: np.ndarray,      # (N,) observed trajectory returns
    weights_list: list[np.ndarray],  # K arrays of (N,) importance weights
) -> np.ndarray:
    """
    WIS counterfactual scores: g_k^i = G_i * w_k^i / mean(w_k)
    Self-normalized to reduce variance. This is the preferred version.
    Returns: (K, N) matrix of WIS counterfactual scores per policy per trajectory.
    """
    N = len(returns)
    K = len(weights_list)
    scores = np.zeros((K, N))
    for k, w in enumerate(weights_list):
        w_norm = w / (w.mean() + 1e-12)
        scores[k] = returns * w_norm
    return scores


def probability_of_regret(
    returns: np.ndarray,
    weights_A: np.ndarray,
    weights_B: np.ndarray,
    method: str = 'WIS',
) -> float:
    """
    Estimate P(pi_A outperforms pi_B in same context) from offline data.

    For each observed trajectory tau_i collected under behavior beta:
      - IS estimate of what pi_A would get: G_i * w_A^i
      - IS estimate of what pi_B would get: G_i * w_B^i
      - pi_A wins trajectory i if its counterfactual score > pi_B's

    Args:
        returns: (N,) observed discounted returns under behavior policy
        weights_A: (N,) trajectory importance ratios pi_A / beta
        weights_B: (N,) trajectory importance ratios pi_B / beta
        method: 'IS' (raw) or 'WIS' (self-normalized, preferred)

    Returns:
        Estimated P(pi_A beats pi_B) in [0, 1]
    """
    if method == 'WIS':
        w_A_norm = weights_A / (weights_A.mean() + 1e-12)
        w_B_norm = weights_B / (weights_B.mean() + 1e-12)
        scores_A = returns * w_A_norm
        scores_B = returns * w_B_norm
    else:  # IS
        scores_A = returns * weights_A
        scores_B = returns * weights_B

    return float(np.mean(scores_A > scores_B))


def probability_of_being_best(
    returns: np.ndarray,
    weights_list: list[np.ndarray],
    method: str = 'WIS',
) -> np.ndarray:
    """
    Estimate P(pi_k beats all other policies in same context) for each k.

    PoB(pi_k) = E_tau[ 1[k = argmax_j G_j(tau)] ]
    where G_j(tau) is the counterfactual return of policy j in trajectory tau.

    Args:
        returns: (N,) observed returns under behavior policy
        weights_list: K arrays of (N,) importance weights
        method: 'IS' or 'WIS'

    Returns:
        (K,) array of PoB probabilities, summing approximately to 1
    """
    K = len(weights_list)
    if method == 'WIS':
        scores = _counterfactual_scores_wis(returns, weights_list)
    else:
        scores = _counterfactual_scores_is(returns, weights_list)

    # For each trajectory, which policy has the best counterfactual score?
    best_per_traj = np.argmax(scores, axis=0)  # (N,)
    pob = np.array([np.mean(best_per_traj == k) for k in range(K)])
    return pob


def counterfactual_dominance_matrix(
    returns: np.ndarray,
    weights_list: list[np.ndarray],
    method: str = 'WIS',
) -> PoRResult:
    """
    Compute full pairwise PoR matrix and PoB for a set of K policies.

    PoR[i, j] = P(pi_i beats pi_j in same context)
    PoR[i, j] + PoR[j, i] should approximately equal 1 (with ties).

    PoR-based ranking: sort policies by total "wins" = sum_j PoR[i, j]

    Args:
        returns: (N,) observed returns under behavior policy
        weights_list: K arrays of (N,) importance weights
        method: 'IS' or 'WIS'

    Returns:
        PoRResult with full matrix and rankings
    """
    K = len(weights_list)
    if method == 'WIS':
        scores = _counterfactual_scores_wis(returns, weights_list)
    else:
        scores = _counterfactual_scores_is(returns, weights_list)

    # Build PoR matrix
    por_matrix = np.zeros((K, K))
    for i in range(K):
        for j in range(K):
            if i != j:
                por_matrix[i, j] = float(np.mean(scores[i] > scores[j]))
            else:
                por_matrix[i, j] = 0.5  # tie with itself

    # PoB
    pob = probability_of_being_best(returns, weights_list, method)

    # PoR-based ranking: by total win rate (sum of row, excluding diagonal)
    win_rates = np.array([
        np.sum([por_matrix[i, j] for j in range(K) if j != i]) / (K - 1)
        for i in range(K)
    ])
    por_ranking = np.argsort(-win_rates)

    # E[V] ranking for comparison
    ev_ranking = _ev_ranking(returns, weights_list, method)

    return PoRResult(
        por_matrix=por_matrix,
        pob=pob,
        por_ranking=por_ranking,
        ev_ranking=ev_ranking,
        method=method,
    )


def _ev_ranking(
    returns: np.ndarray,
    weights_list: list[np.ndarray],
    method: str = 'WIS',
) -> np.ndarray:
    """Rank policies by estimated expected value."""
    K = len(weights_list)
    ev_estimates = np.zeros(K)
    for k, w in enumerate(weights_list):
        if method == 'WIS':
            w_norm = w / (w.mean() + 1e-12)
            ev_estimates[k] = float(np.mean(returns * w_norm))
        else:
            ev_estimates[k] = float(np.mean(returns * w))
    return np.argsort(-ev_estimates)


# ===== Theoretical Bound (Theorem 1) =====

def misranking_bound(n_eff: float, delta: float, C: float = 1.0) -> float:
    """
    Upper bound on P(OPE mis-ranks pi_A vs pi_B) from Theorem 1.

    Theorem 1: Under the IS estimator with N i.i.d. trajectories and effective
    sample size n_eff = N * ESS (with ESS = (sum w)^2 / sum(w^2)), for bounded
    returns G_i in [0, C], assuming true values V_A > V_B with gap delta:

        P(V_hat_B >= V_hat_A) <= 2 * exp(-n_eff * delta^2 / (2 * C^2))

    Proof sketch:
      By Hoeffding's inequality on G_i * w_i (bounded in [0, C * max_w] but
      normalized by n_eff effective samples):
        P(V_hat_A <= V_A - delta/2) <= exp(-n_eff * delta^2 / (2C^2))
        P(V_hat_B >= V_B + delta/2) <= exp(-n_eff * delta^2 / (2C^2))
      Union bound gives the 2x factor.

    Args:
        n_eff: Effective sample size (N * ESS fraction)
        delta: True performance gap V_A - V_B > 0
        C: Bound on trajectory returns (assumed G_i in [0, C])

    Returns:
        Upper bound on misranking probability in [0, 1]
    """
    exponent = -n_eff * (delta ** 2) / (2.0 * C ** 2)
    return min(1.0, 2.0 * np.exp(exponent))


def por_misranking_bound(n_eff: float, por_gap: float) -> float:
    """
    Bound on P(PoR mis-ranks pi_A vs pi_B).

    For PoR estimator, misranking occurs when P_hat(A beats B) < 0.5
    despite true PoR(A, B) > 0.5.

    Since PoR is estimated as a mean of Bernoulli(PoR(A,B)) random variables
    (each trajectory contributes 0 or 1), by Hoeffding:

        P(P_hat_oR < 0.5) <= exp(-2 * n_eff * por_gap^2)

    where por_gap = PoR(A, B) - 0.5 is the true dominance margin.

    Key insight: PoR bound depends only on n_eff and the probability gap,
    NOT on C (the return range). This makes PoR more robust to heavy-tailed
    rewards than E[V]-based comparisons.

    Args:
        n_eff: Effective sample size
        por_gap: PoR(A, B) - 0.5 (must be > 0 for A to truly dominate)

    Returns:
        Upper bound on PoR misranking probability
    """
    if por_gap <= 0:
        return 1.0
    return float(np.exp(-2.0 * n_eff * (por_gap ** 2)))


def model_based_por_matrix(
    shared_batch,
    policies: list,
    nS: int,
    nA: int,
    gamma: float = 0.99,
    n_fqe_iters: int = 150,
) -> PoRResult:
    """
    Model-based PoR using Fitted Q-Evaluation (FQE).

    Avoids the IS zero-weight problem for deterministic/near-deterministic
    policies by using a Q-function model estimated via FQE.

    Algorithm:
      1. Collect shared batch under behavior policy β
      2. Fit Q(s, a) using FQE on the shared batch
      3. For each trajectory initial state s_0^i:
         Q_k(s_0^i) = Σ_a π_k(a|s_0^i) * Q(s_0^i, a)  [value of π_k at s_0^i]
      4. PoR(A, B) = fraction of contexts where Q_A(s_0) > Q_B(s_0)

    This is unbiased under the assumption that the Q-function is correctly
    estimated. It has NO dependence on trajectory-level IS weights.

    Args:
        shared_batch: TrajectoryBatch collected under β
        policies: K evaluation policies (TabularPolicy)
        nS, nA: State/action space sizes
        gamma: Discount factor
        n_fqe_iters: FQE Bellman iteration count

    Returns:
        PoRResult with model-based estimates
    """
    K = len(policies)
    N = shared_batch.rewards.shape[0]
    T = shared_batch.rewards.shape[1]

    # Build transition tuples for FQE
    transitions = []
    for i in range(N):
        for t in range(T):
            if t > 0 and shared_batch.dones[i, t - 1]:
                break
            s = int(shared_batch.states[i, t])
            a = int(shared_batch.actions[i, t])
            r = float(shared_batch.rewards[i, t])
            done = bool(shared_batch.dones[i, t])
            # Next state
            if t + 1 < T:
                s2 = int(shared_batch.states[i, t + 1])
            else:
                s2 = s
            transitions.append((s, a, r, s2, done))

    # Use UNIFORM Q (neutral prior) — FQE will converge to behavior-policy value
    Q = np.zeros((nS, nA), dtype=float)
    bucket = [[[] for _ in range(nA)] for _ in range(nS)]
    for s, a, r, s2, done in transitions:
        bucket[s][a].append((r, s2, done))

    # FQE with uniform policy (estimates Q-values for all (s,a))
    for _ in range(n_fqe_iters):
        Q_new = Q.copy()
        V_next = Q.max(axis=1)  # greedy V — estimates model-based Q
        for s in range(nS):
            for a in range(nA):
                samples = bucket[s][a]
                if not samples:
                    continue
                targets = []
                for r, s2, done in samples:
                    target = r + (0.0 if done else gamma * V_next[s2])
                    targets.append(target)
                Q_new[s, a] = float(np.mean(targets))
        Q = Q_new

    # Compute policy values at each trajectory's starting state
    start_states = shared_batch.states[:, 0].astype(int)  # (N,)

    # For each policy, compute expected value at each start state
    policy_probs = np.array([pi.probs for pi in policies])  # (K, nS, nA)
    Q_states = Q[start_states, :]  # (N, nA)

    # V_k(s_0) = Σ_a π_k(a|s_0) * Q(s_0, a)
    # policy_probs[:, start_states, :] has shape (K, N, nA)
    V_policies = np.einsum('kna,na->kn', policy_probs[:, start_states, :], Q_states)  # (K, N)

    # Build PoR matrix
    por_matrix = np.zeros((K, K))
    for i in range(K):
        for j in range(K):
            if i != j:
                por_matrix[i, j] = float(np.mean(V_policies[i] > V_policies[j]))
            else:
                por_matrix[i, j] = 0.5

    # PoB
    best_per_context = np.argmax(V_policies, axis=0)  # (N,)
    pob = np.array([float(np.mean(best_per_context == k)) for k in range(K)])

    # PoR win rates
    win_rates = np.array([
        np.mean([por_matrix[i, j] for j in range(K) if j != i]) / max(K - 1, 1)
        for i in range(K)
    ])
    por_ranking = np.argsort(-win_rates)

    # EV ranking (from Q values)
    ev_estimates = V_policies.mean(axis=1)
    ev_ranking = np.argsort(-ev_estimates)

    return PoRResult(
        por_matrix=por_matrix,
        pob=pob,
        por_ranking=por_ranking,
        ev_ranking=ev_ranking,
        method='model_FQE',
    )


def compute_ess(weights: np.ndarray) -> float:
    """
    Compute effective sample size: ESS = (sum w)^2 / sum(w^2).

    Returns ESS as fraction of N (in [0, 1]).
    ESS = 1 when all weights equal (perfect coverage).
    ESS -> 0 when weights are highly unequal (poor coverage).
    """
    N = len(weights)
    if N == 0 or weights.sum() == 0:
        return 0.0
    return float((weights.sum() ** 2) / (weights ** 2).sum()) / N
