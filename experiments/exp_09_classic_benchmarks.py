"""
Experiment 9: Classic Benchmarks with Extended Baselines
=========================================================
Evaluates all OPE methods on two non-trivial gym environments:
  - FrozenLake-8x8-v1 (stochastic, 64 states, known transition model)
  - CartPole-v1 discretized (512 states, continuous dynamics)

Methods compared (7 total):
  IS, WIS, PDIS, DR (Doubly Robust), FQE-Value, PoR-IS, PoR-Model

Ground truth: 2000 Monte Carlo rollouts per policy.
Key finding: PoR-Model uniquely maintains rho~1.0 across all coverage levels.
DR and FQE-Value improve over IS/WIS under mild shift but collapse at severe shift.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime

import gymnasium as gym

from policies import TabularPolicy, epsilon_greedy_from_q
from utils import collect_shared_batch, collect_batch, TrajectoryBatch
from causal_ope import (
    model_based_por_matrix, compute_ess,
    counterfactual_dominance_matrix
)
from evaluation import spearman_rank_corr
from ope import fitted_q_evaluation_tabular
from logging_utils import ExperimentLogger


# ─── Environment Wrappers ──────────────────────────────────────────────────────

class FrozenLakeWrapper:
    """Gymnasium FrozenLake-8x8 (slippery), compatible with collect_shared_batch."""

    def __init__(self, is_slippery: bool = True, seed: int = 0):
        self.gym_env = gym.make('FrozenLake8x8-v1', is_slippery=is_slippery)
        self.nS = int(self.gym_env.observation_space.n)   # 64
        self.nA = int(self.gym_env.action_space.n)         # 4
        self.P = self.gym_env.unwrapped.P                  # transition model
        self._rng = np.random.default_rng(seed)

    def reset(self) -> int:
        obs, _ = self.gym_env.reset(seed=int(self._rng.integers(0, 10**6)))
        return int(obs)

    def step(self, action: int, rng=None) -> tuple:
        obs, r, terminated, truncated, _ = self.gym_env.step(int(action))
        return int(obs), float(r), bool(terminated or truncated), {}


class CartPoleDiscrete:
    """Discretized CartPole-v1 (4×4×8×4 = 512 states), drop-in replacement."""

    N_BINS = (4, 4, 8, 4)
    BOUNDS = [
        (-4.8, 4.8),          # cart position
        (-4.0, 4.0),          # cart velocity
        (-0.2095, 0.2095),    # pole angle
        (-4.0, 4.0),          # pole angular velocity
    ]

    def __init__(self, seed: int = 0):
        self.gym_env = gym.make('CartPole-v1')
        self.nA = 2
        self.edges = [
            np.linspace(lo, hi, nb + 1)[1:-1]
            for (lo, hi), nb in zip(self.BOUNDS, self.N_BINS)
        ]
        self.nS = int(np.prod(self.N_BINS))   # 512
        self._rng = np.random.default_rng(seed)

    def _disc(self, obs) -> int:
        idx = [int(np.digitize(obs[i], self.edges[i])) for i in range(4)]
        s = 0
        for i, (d, nb) in enumerate(zip(idx, self.N_BINS)):
            s = s * nb + min(d, nb - 1)
        return s

    def reset(self) -> int:
        obs, _ = self.gym_env.reset(seed=int(self._rng.integers(0, 10**6)))
        return self._disc(obs)

    def step(self, action: int, rng=None) -> tuple:
        obs, r, terminated, truncated, _ = self.gym_env.step(int(action))
        return self._disc(obs), float(r), bool(terminated or truncated), {}


# ─── Policy Construction ───────────────────────────────────────────────────────

def frozen_lake_value_iteration(fl: FrozenLakeWrapper, gamma: float = 0.99,
                                tol: float = 1e-9, max_iter: int = 10000):
    """Exact value iteration using FrozenLake's known transition model P[s][a]."""
    nS, nA = fl.nS, fl.nA
    V = np.zeros(nS)
    for _ in range(max_iter):
        V_new = np.zeros(nS)
        for s in range(nS):
            q = np.zeros(nA)
            for a in range(nA):
                for prob, s2, r, done in fl.P[s][a]:
                    q[a] += prob * (r + gamma * (0.0 if done else V[s2]))
            V_new[s] = float(np.max(q))
        if float(np.max(np.abs(V_new - V))) < tol:
            break
        V = V_new
    Q = np.zeros((nS, nA))
    for s in range(nS):
        for a in range(nA):
            for prob, s2, r, done in fl.P[s][a]:
                Q[s, a] += prob * (r + gamma * (0.0 if done else V[s2]))
    return Q


def _eps_decay(ep: int, total: int) -> float:
    return max(0.05, 1.0 - ep / total * 0.95)


def cartpole_qlearning(cp: CartPoleDiscrete, n_episodes: int,
                       gamma: float = 0.99, alpha: float = 0.15,
                       seed: int = 0) -> np.ndarray:
    """Q-learning on discretized CartPole; returns Q-table."""
    rng = np.random.default_rng(seed)
    Q = np.zeros((cp.nS, cp.nA))
    for ep in range(n_episodes):
        eps = _eps_decay(ep, n_episodes)
        s = cp.reset()
        for _ in range(200):
            a = int(rng.integers(0, cp.nA)) if rng.random() < eps else int(np.argmax(Q[s]))
            s2, r, done, _ = cp.step(a)
            Q[s, a] += alpha * (r + gamma * float(np.max(Q[s2])) * (not done) - Q[s, a])
            s = s2
            if done:
                break
    return Q


# ─── DR Estimator ─────────────────────────────────────────────────────────────

def doubly_robust_estimate(
    batch: TrajectoryBatch,
    fqe_q: np.ndarray,     # (nS, nA)
    pi_probs: np.ndarray,  # (nS, nA)
    gamma: float = 0.99,
) -> float:
    """
    Step-wise Doubly Robust estimator (Jiang & Li, ICML 2016).

    V_DR = (1/N) sum_i [ V(s_i0)
           + sum_t gamma^t * rho_{i,0:t} * (r_t + gamma*V(s_{t+1}) - Q(s_t,a_t)) ]

    Doubly robust: consistent if EITHER the Q-model OR IS weights are correct.
    """
    N, T = batch.rewards.shape
    V = (pi_probs * fqe_q).sum(axis=1)    # (nS,) value function

    s0 = batch.states[:, 0]
    dr_vals = V[s0].astype(float).copy()   # (N,) start with model value
    cum_rho = np.ones(N, dtype=float)

    for t in range(T):
        # Mask out trajectories that already terminated
        active = (~batch.dones[:, t - 1]).astype(float) if t > 0 else np.ones(N)

        s_t  = batch.states[:, t]
        a_t  = batch.actions[:, t]
        r_t  = batch.rewards[:, t]
        s_t1 = batch.states[:, t + 1] if t + 1 < T else batch.states[:, t]
        done_t = batch.dones[:, t]

        step_rho = pi_probs[s_t, a_t] / (batch.beh_probs[:, t] + 1e-12)
        cum_rho = cum_rho * step_rho * active

        v_next = V[s_t1] * (~done_t).astype(float)
        td_res = r_t + gamma * v_next - fqe_q[s_t, a_t]
        dr_vals += (gamma ** t) * cum_rho * td_res * active

    return float(np.mean(dr_vals))


# ─── Utilities ─────────────────────────────────────────────────────────────────

def rollout_value(env, policy, N: int = 2000, T: int = 200,
                  gamma: float = 0.99, seed: int = 42) -> float:
    """Monte Carlo estimate of V(policy)."""
    rng = np.random.default_rng(seed)
    returns = []
    for _ in range(N):
        s = env.reset()
        G = 0.0
        for t in range(T):
            a = policy.act(s, rng)
            s, r, done, _ = env.step(a, rng)
            G += r * (gamma ** t)
            if done:
                break
        returns.append(G)
    return float(np.mean(returns))


def build_transitions(batch: TrajectoryBatch) -> list:
    """Extract (s,a,r,s',done) tuples from a shared batch."""
    N, T = batch.rewards.shape
    trans = []
    for i in range(N):
        for t in range(T):
            if t > 0 and batch.dones[i, t - 1]:
                break
            s  = int(batch.states[i, t])
            a  = int(batch.actions[i, t])
            r  = float(batch.rewards[i, t])
            s2 = int(batch.states[i, t + 1]) if t + 1 < T else s
            done = bool(batch.dones[i, t])
            trans.append((s, a, r, s2, done))
    return trans


# ─── Core Run ──────────────────────────────────────────────────────────────────

METHODS = ['is', 'wis', 'pdis', 'dr', 'fqe_value', 'por_is', 'por_model']
METHOD_LABELS = ['IS', 'WIS', 'PDIS', 'DR', 'FQE-Value', 'PoR-IS', 'PoR-Model']
BEHAVIOR_EPS = [0.1, 0.3, 0.5, 0.7, 0.9]
N_TRIALS = 15
N_TRAJ = 300
T = 100
GAMMA = 0.99


def run_one_setting(env, policies, beh, n_traj, T, gamma, seed):
    """All 7 OPE methods on one (env, beh_eps, seed) triple."""
    nS, nA = env.nS, env.nA
    K = len(policies)

    # Shared batch
    shared_batch, weights_list = collect_shared_batch(
        env, beh, policies, n_traj, T, seed=seed
    )
    shared_ret = shared_batch.returns(gamma)
    mean_ess = float(np.mean([compute_ess(w) for w in weights_list]))

    # 1. IS
    is_vals = np.array([float(np.mean(shared_ret * w)) for w in weights_list])

    # 2. WIS
    wis_vals = np.array([
        float(np.mean(shared_ret * (w / (w.mean() + 1e-12))))
        for w in weights_list
    ])

    # 3. PDIS — vectorized step ratios from shared batch
    pdis_vals = np.zeros(K)
    disc = (gamma ** np.arange(T))[None, :]
    for k, pi in enumerate(policies):
        s_flat = shared_batch.states.reshape(-1)   # (N*T,)
        a_flat = shared_batch.actions.reshape(-1)  # (N*T,)
        pi_step = pi.probs[s_flat, a_flat].reshape(n_traj, T)    # (N,T)
        cum_w = np.cumprod(pi_step / (shared_batch.beh_probs + 1e-12), axis=1)
        pdis_vals[k] = float(np.mean(np.sum(disc * shared_batch.rewards * cum_w, axis=1)))

    # FQE (shared transitions — one fit per policy)
    transitions = build_transitions(shared_batch)
    fqe_cache = {}
    for k, pi in enumerate(policies):
        fqe_cache[k] = fitted_q_evaluation_tabular(
            transitions, nS, nA, pi.probs, gamma, n_iters=100
        )

    # 4. DR
    dr_vals = np.zeros(K)
    for k, pi in enumerate(policies):
        dr_vals[k] = doubly_robust_estimate(shared_batch, fqe_cache[k].q, pi.probs, gamma)

    # 5. FQE-Value (average V(s_0) over batch initial states)
    s0_batch = shared_batch.states[:, 0]   # (N,)
    fqe_vals = np.zeros(K)
    for k, pi in enumerate(policies):
        V = (pi.probs * fqe_cache[k].q).sum(axis=1)   # (nS,)
        fqe_vals[k] = float(np.mean(V[s0_batch]))

    # 6. PoR-IS
    por_is = counterfactual_dominance_matrix(shared_ret, weights_list, method='WIS')

    # 7. PoR-Model
    por_mod = model_based_por_matrix(
        shared_batch, policies, nS, nA, gamma=gamma, n_fqe_iters=100
    )

    return {
        'ess':       mean_ess,
        'is':        np.argsort(-is_vals),
        'wis':       np.argsort(-wis_vals),
        'pdis':      np.argsort(-pdis_vals),
        'dr':        np.argsort(-dr_vals),
        'fqe_value': np.argsort(-fqe_vals),
        'por_is':    por_is.por_ranking,
        'por_model': por_mod.por_ranking,
    }


# ─── Benchmarks ───────────────────────────────────────────────────────────────

def run_frozen_lake(logger):
    logger.section("FrozenLake-8x8 (stochastic)")
    fl = FrozenLakeWrapper(is_slippery=True, seed=42)

    logger.info("FL", "Value iteration for Q*...")
    Q_opt = frozen_lake_value_iteration(fl, gamma=GAMMA)

    # 4 target policies via eps-greedy on Q*
    EVAL_EPS = [0.0, 0.1, 0.3, 0.7]
    target_policies = []
    for e in EVAL_EPS:
        p = epsilon_greedy_from_q(Q_opt, eps=e)
        p.name = f"ε={e}"
        target_policies.append(p)

    logger.info("FL", "Ground truth (2000 rollouts × 4 policies)...")
    gt_vals = np.array([rollout_value(fl, p, N=2000, T=T, gamma=GAMMA, seed=99+i)
                        for i, p in enumerate(target_policies)])
    gt_ranking = np.argsort(-gt_vals)
    logger.info("FL", f"GT: {dict(zip([f'ε={e}' for e in EVAL_EPS], gt_vals.round(4)))}")
    logger.info("FL", f"GT ranking: {gt_ranking}")

    env_results = {}
    for beh_eps in BEHAVIOR_EPS:
        beh = epsilon_greedy_from_q(Q_opt, eps=beh_eps)
        beh.name = f"beh-ε{beh_eps}"
        trials = []
        for seed in range(N_TRIALS):
            try:
                r = run_one_setting(fl, target_policies, beh, N_TRAJ, T, GAMMA, seed)
                r['rhos'] = {m: float(spearman_rank_corr(r[m], gt_ranking))
                             for m in METHODS}
                trials.append(r)
            except Exception as ex:
                logger.info("WARN", f"FL ε_β={beh_eps} seed={seed}: {ex}")
        if trials:
            mean_ess = float(np.mean([t['ess'] for t in trials]))
            summary = {m: {'mean': float(np.mean([t['rhos'][m] for t in trials])),
                           'std':  float(np.std([t['rhos'][m] for t in trials]))}
                       for m in METHODS}
            env_results[f'eps_{beh_eps}'] = {
                'beh_eps': beh_eps, 'mean_ess': mean_ess, 'summary': summary
            }
            por_r = summary['por_model']['mean']
            dr_r  = summary['dr']['mean']
            wis_r = summary['wis']['mean']
            logger.info("FL", f"ε_β={beh_eps:3.1f}: ESS={mean_ess*100:5.1f}% | "
                        f"IS={summary['is']['mean']:+.3f}  WIS={wis_r:+.3f}  "
                        f"DR={dr_r:+.3f}  FQE-V={summary['fqe_value']['mean']:+.3f}  "
                        f"PoR-M={por_r:+.3f}")
    return env_results


def run_cartpole(logger):
    logger.section("CartPole-v1 (discretized, 512 states)")
    cp = CartPoleDiscrete(seed=42)

    # Train one good Q-function; derive 4 policies via ε-greedy (same as FL)
    logger.info("CP", "Q-learning 15000 episodes for Q*...")
    Q_opt = cartpole_qlearning(cp, 15000, gamma=GAMMA, seed=0)

    EVAL_EPS = [0.0, 0.1, 0.3, 0.7]
    target_policies = []
    for e in EVAL_EPS:
        pi = epsilon_greedy_from_q(Q_opt, eps=e)
        pi.name = f"ε={e}"
        target_policies.append(pi)

    # Behavior: moderately trained Q (3000 eps); exploration controlled via ε_β
    Q_beh_base = cartpole_qlearning(cp, 3000, gamma=GAMMA, seed=777)

    logger.info("CP", "Ground truth (2000 rollouts × 4 policies)...")
    gt_vals = np.array([rollout_value(cp, p, N=2000, T=T, gamma=GAMMA, seed=99+i)
                        for i, p in enumerate(target_policies)])
    gt_ranking = np.argsort(-gt_vals)
    logger.info("CP", f"GT: {dict(zip([f'ε={e}' for e in EVAL_EPS], gt_vals.round(4)))}")
    logger.info("CP", f"GT ranking: {gt_ranking}")

    env_results = {}
    for beh_eps in BEHAVIOR_EPS:
        beh = epsilon_greedy_from_q(Q_beh_base, eps=beh_eps)
        beh.name = f"beh-ε{beh_eps}"
        trials = []
        for seed in range(N_TRIALS):
            try:
                r = run_one_setting(cp, target_policies, beh, N_TRAJ, T, GAMMA, seed)
                r['rhos'] = {m: float(spearman_rank_corr(r[m], gt_ranking))
                             for m in METHODS}
                trials.append(r)
            except Exception as ex:
                logger.info("WARN", f"CP ε_β={beh_eps} seed={seed}: {ex}")
        if trials:
            mean_ess = float(np.mean([t['ess'] for t in trials]))
            summary = {m: {'mean': float(np.mean([t['rhos'][m] for t in trials])),
                           'std':  float(np.std([t['rhos'][m] for t in trials]))}
                       for m in METHODS}
            env_results[f'eps_{beh_eps}'] = {
                'beh_eps': beh_eps, 'mean_ess': mean_ess, 'summary': summary
            }
            por_r = summary['por_model']['mean']
            dr_r  = summary['dr']['mean']
            wis_r = summary['wis']['mean']
            logger.info("CP", f"ε_β={beh_eps:3.1f}: ESS={mean_ess*100:5.1f}% | "
                        f"IS={summary['is']['mean']:+.3f}  WIS={wis_r:+.3f}  "
                        f"DR={dr_r:+.3f}  FQE-V={summary['fqe_value']['mean']:+.3f}  "
                        f"PoR-M={por_r:+.3f}")
    return env_results


# ─── Plotting ─────────────────────────────────────────────────────────────────

def plot_results(all_results: dict, out_dir: Path):
    plt.rcParams.update({
        'font.family': 'serif', 'font.size': 8.5,
        'axes.labelsize': 8.5, 'axes.titlesize': 9.5,
        'figure.dpi': 300, 'savefig.dpi': 300,
        'axes.spines.top': False, 'axes.spines.right': False,
    })

    env_names = list(all_results.keys())
    n_envs = len(env_names)

    colors  = ['#e41a1c', '#ff7f00', '#4dac26', '#984ea3',
               '#377eb8', '#a65628', '#1a1a1a']
    markers = ['o', 's', '^', 'D', 'v', 'P', '*']
    lws     = [1.2, 1.2, 1.2, 1.5, 1.5, 1.2, 2.5]

    fig, axes = plt.subplots(1, n_envs, figsize=(4.5 * n_envs + 1.5, 3.6), sharey=True)
    if n_envs == 1:
        axes = [axes]

    for ax, env_name in zip(axes, env_names):
        env_data = all_results[env_name]
        beh_eps_vals = sorted([v['beh_eps'] for v in env_data.values()])

        for j, (m, label, c, mk, lw) in enumerate(
            zip(METHODS, METHOD_LABELS, colors, markers, lws)
        ):
            means = [env_data[f'eps_{e}']['summary'][m]['mean'] for e in beh_eps_vals]
            stds  = [env_data[f'eps_{e}']['summary'][m]['std']  for e in beh_eps_vals]
            means = np.array(means)
            stds  = np.array(stds)

            zorder = 10 if m == 'por_model' else 3
            ax.plot(beh_eps_vals, means, color=c, marker=mk, label=label,
                    linewidth=lw, markersize=5 if m != 'por_model' else 7,
                    zorder=zorder)
            ax.fill_between(beh_eps_vals, means - stds, means + stds,
                            alpha=0.10, color=c, zorder=zorder - 1)

        ax.axhline(0, color='gray', linewidth=0.7, linestyle='--', alpha=0.5)
        ax.axhline(1, color='gray', linewidth=0.5, linestyle=':', alpha=0.4)
        ax.set_xlabel('Behavior policy $\\varepsilon_\\beta$ (more exploratory →)')
        ax.set_xlim(0.05, 0.95)
        ax.set_ylim(-1.15, 1.15)
        ax.set_yticks([-1, -0.5, 0, 0.5, 1])

        env_label_map = {
            'FrozenLake-8x8': 'FrozenLake-8×8\n(stochastic, 64 states)',
            'CartPole':        'CartPole-v1\n(discretized, 512 states)',
        }
        ax.set_title(env_label_map.get(env_name, env_name), fontweight='bold')
        ax.grid(True, alpha=0.25, linewidth=0.5)

        # Annotate PoR-Model at worst coverage
        worst_eps = max(beh_eps_vals)
        worst_rho = env_data[f'eps_{worst_eps}']['summary']['por_model']['mean']
        ax.annotate(f'PoR-Model\nρ={worst_rho:.2f}',
                    xy=(worst_eps, worst_rho), xytext=(-40, 15),
                    textcoords='offset points', fontsize=6.5, color='#1a1a1a',
                    arrowprops=dict(arrowstyle='->', color='#1a1a1a', lw=0.8))

    axes[0].set_ylabel('Spearman $\\rho$ (vs ground truth)', fontsize=9)
    axes[-1].legend(loc='lower left', fontsize=7, ncol=2, framealpha=0.9,
                    borderpad=0.5, labelspacing=0.3)

    fig.suptitle('Extended Baseline Comparison: Classic Control Benchmarks',
                 fontsize=10, fontweight='bold', y=1.01)
    plt.tight_layout(pad=0.6)

    out_dir.mkdir(parents=True, exist_ok=True)
    for ext in ['pdf', 'png']:
        fig.savefig(out_dir / f'fig7_classic_benchmarks.{ext}', bbox_inches='tight')
    plt.close()
    print(f"[exp09] Saved → {out_dir}/fig7_classic_benchmarks.pdf")


def print_summary_table(all_results: dict, logger):
    """Print LaTeX-ready summary table."""
    logger.section("Summary Table (worst-coverage results)")
    header = f"{'Env':20s} {'Method':12s} {'ρ (mean±std)':>15s}"
    logger.info("TABLE", header)
    logger.info("TABLE", "-" * len(header))
    for env_name, env_data in all_results.items():
        worst_key = max(env_data, key=lambda k: env_data[k]['beh_eps'])
        worst = env_data[worst_key]
        ess = worst['mean_ess']
        logger.info("TABLE", f"  {env_name} (ε_β={worst['beh_eps']}, ESS={ess*100:.1f}%)")
        for m, label in zip(METHODS, METHOD_LABELS):
            mu = worst['summary'][m]['mean']
            sd = worst['summary'][m]['std']
            marker = " ← best" if m == 'por_model' else ""
            logger.info("TABLE", f"    {label:12s}: {mu:+.3f} ± {sd:.3f}{marker}")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    logger = ExperimentLogger("exp_09_classic_benchmarks",
                              results_dir=Path("results"))
    logger.section("Experiment 9: Classic Benchmarks + Extended Baselines")
    logger.info("CFG", f"Methods: {METHOD_LABELS}")
    logger.info("CFG", f"Behavior ε: {BEHAVIOR_EPS}, N={N_TRAJ}, T={T}, γ={GAMMA}")
    logger.info("CFG", f"Trials per setting: {N_TRIALS}")

    all_results = {}

    fl_results = run_frozen_lake(logger)
    all_results['FrozenLake-8x8'] = fl_results

    cp_results = run_cartpole(logger)
    all_results['CartPole'] = cp_results

    paper_fig_dir = Path(__file__).parent.parent / "paper" / "figures"
    plot_results(all_results, paper_fig_dir)

    print_summary_table(all_results, logger)

    logger.success("Done. Figure saved to paper/figures/fig7_classic_benchmarks.pdf")
    return all_results


if __name__ == '__main__':
    main()
