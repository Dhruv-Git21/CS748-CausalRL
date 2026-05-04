"""
Experiment 10: Non-Uniform Reward Landscape — Gold Mine Gridworld
=================================================================
Tests PoR-Model under heterogeneous reward distributions where localized
cells yield large intermediate rewards (gold mines), creating qualitatively
distinct policy behaviors (mine-seeking vs. goal-seeking).

Motivation: Reviews raised the concern that uniform step-reward (-0.01/step,
+1 at goal) might trivially advantage PoR. With gold mines, different policies
rationally prefer different trajectories, and PoR-Model must use FQE to learn
the full reward landscape.

Three configurations (all on GW-5x5):
  GM-Center  : single mine at (2,2), reward=+0.5  — on the diagonal path
  GM-Corner  : single mine at (0,4), reward=+1.0  — top-right corner detour
  GM-2mines  : mines at (1,3) and (3,1), reward=+0.4 each — two off-diagonal

Four evaluation policies per config:
  P0: ε=0.0 on Q_mine  (deterministic mine-seeker — best GT value)
  P1: ε=0.1 on Q_mine  (mostly mine-seeking)
  P2: ε=0.0 on Q_goal  (right-first goal-seeker — ignores mine)
  P3: ε=0.3 on Q_goal  (exploratory goal-seeker)

Seven OPE methods compared: IS, WIS, PDIS, DR, FQE-Value, PoR-IS, PoR-Model
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime

from envs import Gridworld, GridworldConfig
from policies import epsilon_greedy_from_q, TabularPolicy
from utils import collect_shared_batch, collect_batch, TrajectoryBatch
from causal_ope import (
    model_based_por_matrix, compute_ess, counterfactual_dominance_matrix
)
from evaluation import spearman_rank_corr
from ope import importance_sampling, weighted_is, per_decision_is
from logging_utils import ExperimentLogger


# ─── Gold-mine configurations ─────────────────────────────────────────────────

GOLD_CONFIGS = {
    'GM-Center': {
        'gold_mines': {(2, 2): 0.5},
        'label': 'GM-Center\nMine at (2,2), r=+0.5',
    },
    'GM-Corner': {
        'gold_mines': {(0, 4): 1.0},
        'label': 'GM-Corner\nMine at (0,4), r=+1.0',
    },
    'GM-2mines': {
        'gold_mines': {(1, 3): 0.4, (3, 1): 0.4},
        'label': 'GM-2mines\nMines at (1,3)+(3,1), r=+0.4',
    },
}

BEHAVIOR_EPS = [0.1, 0.3, 0.5, 0.7, 0.9]
N_TRIALS = 15
N_TRAJ = 300
T = 50
GAMMA = 0.99
BASE_CFG = GridworldConfig(width=5, height=5, goal=(4, 4), slip=0.0)


# ─── Policy construction ──────────────────────────────────────────────────────

def build_q_goal_rightfirst(cfg):
    """Right-first path: go right until y=4, then down. Avoids diagonal."""
    W, H = cfg.width, cfg.height
    nS = W * H
    Q = np.zeros((nS, 4))
    gx, gy = cfg.goal
    for s in range(nS):
        x, y = s // W, s % W
        if y < gy:
            Q[s, 1] = 2.0  # right (strong preference)
        if x < gx:
            Q[s, 2] = 1.0  # down (secondary)
        if x > gx:
            Q[s, 0] = 0.1
        if y > gy:
            Q[s, 3] = 0.1
    return Q


def build_q_mine_seeker(cfg):
    """Mine-then-goal: go toward nearest mine first (if closer than goal), then goal."""
    W, H = cfg.width, cfg.height
    nS = W * H
    Q = np.zeros((nS, 4))
    gx, gy = cfg.goal
    mines = list(cfg.gold_mines.keys()) if cfg.gold_mines else []

    for s in range(nS):
        x, y = s // W, s % W
        dist_goal = abs(x - gx) + abs(y - gy)

        # Find nearest mine that's not at current cell
        nearest_mine, min_mine_dist = None, float('inf')
        for mx, my in mines:
            d = abs(x - mx) + abs(y - my)
            if d > 0 and d < min_mine_dist:
                min_mine_dist = d
                nearest_mine = (mx, my)

        if nearest_mine and min_mine_dist < dist_goal:
            mx, my = nearest_mine
            if x < mx: Q[s, 2] += 2.0   # down toward mine
            elif x > mx: Q[s, 0] += 2.0  # up toward mine
            if y < my: Q[s, 1] += 2.0   # right toward mine
            elif y > my: Q[s, 3] += 2.0  # left toward mine
        else:
            # Head to goal
            if x < gx: Q[s, 2] += 2.0
            elif x > gx: Q[s, 0] += 0.1
            if y < gy: Q[s, 1] += 2.0
            elif y > gy: Q[s, 3] += 0.1
    return Q


def build_policies(cfg):
    """Build 4 evaluation policies for a gold mine config."""
    Q_mine = build_q_mine_seeker(cfg)
    Q_goal = build_q_goal_rightfirst(cfg)
    return [
        epsilon_greedy_from_q(Q_mine, eps=0.0),   # P0: pure mine-seeker
        epsilon_greedy_from_q(Q_mine, eps=0.1),   # P1: mostly mine-seeking
        epsilon_greedy_from_q(Q_goal, eps=0.0),   # P2: pure goal-seeker (right-first)
        epsilon_greedy_from_q(Q_goal, eps=0.3),   # P3: exploratory goal-seeker
    ]


def build_behavior_policy(cfg, beh_eps):
    """Behavior policy: ε-greedy on goal-directed Q (right-first)."""
    Q_goal = build_q_goal_rightfirst(cfg)
    return epsilon_greedy_from_q(Q_goal, eps=beh_eps)


# ─── Ground truth ─────────────────────────────────────────────────────────────

def rollout_value(env, policy, N=1000, T=50, gamma=0.99, seed=0):
    rng = np.random.default_rng(seed)
    returns = []
    for _ in range(N):
        s = env.reset()
        G, disc = 0.0, 1.0
        for t in range(T):
            a = policy.act(s, rng)
            s, r, done, _ = env.step(a, rng)
            G += disc * r
            disc *= gamma
            if done:
                break
        returns.append(G)
    return float(np.mean(returns))


# ─── FQE utility ──────────────────────────────────────────────────────────────

def run_fqe(shared_batch, nS, nA, gamma=0.99, n_iters=100):
    """Standalone FQE: returns Q-table estimated from shared_batch."""
    N, T = shared_batch.rewards.shape
    bucket = [[[] for _ in range(nA)] for _ in range(nS)]
    for i in range(N):
        for t in range(T):
            if t > 0 and shared_batch.dones[i, t - 1]:
                break
            s = int(shared_batch.states[i, t])
            a = int(shared_batch.actions[i, t])
            r = float(shared_batch.rewards[i, t])
            done = bool(shared_batch.dones[i, t])
            s2 = int(shared_batch.states[i, t + 1]) if t + 1 < T else s
            bucket[s][a].append((r, s2, done))

    Q = np.zeros((nS, nA))
    for _ in range(n_iters):
        Q_new = Q.copy()
        V_next = Q.max(axis=1)
        for s in range(nS):
            for a in range(nA):
                if bucket[s][a]:
                    targets = [r + (0. if d else gamma * V_next[s2])
                               for r, s2, d in bucket[s][a]]
                    Q_new[s, a] = float(np.mean(targets))
        Q = Q_new
    return Q


# ─── DR estimate ──────────────────────────────────────────────────────────────

def dr_estimate(shared_batch, pi_probs, Q_fqe, gamma=0.99):
    """Step-wise doubly robust OPE estimate."""
    N, T = shared_batch.rewards.shape
    nS, nA = Q_fqe.shape
    V_pi = (pi_probs * Q_fqe).sum(axis=1)   # (nS,)
    s0 = shared_batch.states[:, 0].astype(int)
    dr_v = V_pi[s0].copy().astype(float)
    cum_rho = np.ones(N)
    for t in range(T):
        active = (~shared_batch.dones[:, t - 1]).astype(float) if t > 0 else np.ones(N)
        s_t = shared_batch.states[:, t].astype(int)
        a_t = shared_batch.actions[:, t].astype(int)
        r_t = shared_batch.rewards[:, t]
        s_tp1 = shared_batch.states[:, min(t + 1, T - 1)].astype(int)
        step_rho = pi_probs[s_t, a_t] / (shared_batch.beh_probs[:, t] + 1e-12)
        cum_rho = cum_rho * step_rho * active
        td_res = r_t + gamma * V_pi[s_tp1] - Q_fqe[s_t, a_t]
        dr_v += (gamma ** t) * cum_rho * td_res * active
    return float(np.mean(np.clip(dr_v, -1e3, 1e3)))


# ─── One setting ──────────────────────────────────────────────────────────────

def run_one_setting(env, policies, beh_policy, n_traj, T, gamma, seed):
    nS, nA = env.nS, env.nA
    K = len(policies)

    shared_batch, weights_list = collect_shared_batch(
        env, beh_policy, policies, n_traj, T, seed=seed
    )
    shared_ret = shared_batch.returns(gamma)
    mean_ess = float(np.mean([compute_ess(w) for w in weights_list]))

    # IS / WIS
    is_vals = np.array([float(np.mean(shared_ret * w)) for w in weights_list])
    wis_vals = np.array([
        float(np.mean(shared_ret * (w / (w.mean() + 1e-12))))
        for w in weights_list
    ])

    # PDIS
    pdis_vals = np.zeros(K)
    for k, pi in enumerate(policies):
        bk = collect_batch(env, beh_policy, pi, n_traj, T, seed=seed + 1000 * k)
        sw = bk.step_cum_ratios()
        disc = (gamma ** np.arange(T))[None, :]
        pdis_vals[k] = float(np.mean(np.sum(disc * bk.rewards * sw, axis=1)))

    # FQE (shared table)
    Q_fqe = run_fqe(shared_batch, nS, nA, gamma, n_iters=100)

    # Policy probs
    pi_probs_all = np.array([pi.probs for pi in policies])  # (K, nS, nA)

    # FQE-Value
    s0 = shared_batch.states[:, 0].astype(int)
    Q_s0 = Q_fqe[s0, :]  # (N, nA)
    fqev_vals = np.einsum('kna,na->kn', pi_probs_all[:, s0, :], Q_s0).mean(axis=1)

    # DR
    dr_vals = np.array([
        dr_estimate(shared_batch, pi_probs_all[k], Q_fqe, gamma)
        for k in range(K)
    ])

    # PoR-IS
    por_is_res = counterfactual_dominance_matrix(shared_ret, weights_list, method='WIS')

    # PoR-Model
    por_mod_res = model_based_por_matrix(
        shared_batch, policies, nS, nA, gamma=gamma, n_fqe_iters=100
    )

    return {
        'ess': mean_ess,
        'is_ranking': np.argsort(-is_vals),
        'wis_ranking': np.argsort(-wis_vals),
        'pdis_ranking': np.argsort(-pdis_vals),
        'dr_ranking': np.argsort(-dr_vals),
        'fqev_ranking': np.argsort(-fqev_vals),
        'por_is_ranking': por_is_res.por_ranking,
        'por_model_ranking': por_mod_res.por_ranking,
    }


# ─── Main benchmark ───────────────────────────────────────────────────────────

def run_goldmine_benchmark():
    logger = ExperimentLogger("exp_10_goldmine", results_dir=Path("results"))
    logger.section("Gold Mine Gridworld — Non-Uniform Reward Landscape")
    logger.info("CFG", f"Configs: {list(GOLD_CONFIGS.keys())}")
    logger.info("CFG", f"Behavior ε: {BEHAVIOR_EPS}, N={N_TRAJ}, T={T}, trials={N_TRIALS}")

    all_results = {}

    for cfg_name, cfg_info in GOLD_CONFIGS.items():
        cfg = GridworldConfig(
            width=BASE_CFG.width, height=BASE_CFG.height,
            goal=BASE_CFG.goal, slip=BASE_CFG.slip,
            gold_mines=cfg_info['gold_mines']
        )
        env = Gridworld(cfg)
        policies = build_policies(cfg)

        # Ground truth
        logger.info(cfg_name, "Computing ground truth (1000 rollouts × 4 policies)...")
        gt_values = np.array([
            rollout_value(env, p, N=1000, T=T, gamma=GAMMA, seed=i)
            for i, p in enumerate(policies)
        ])
        gt_ranking = np.argsort(-gt_values)
        gt_str = {f'P{i}': f'{v:.3f}' for i, v in enumerate(gt_values)}
        logger.info(cfg_name, f"GT values: {gt_str}")
        logger.info(cfg_name, f"GT ranking: {gt_ranking}")

        cfg_results = {}
        for beh_eps in BEHAVIOR_EPS:
            beh = build_behavior_policy(cfg, beh_eps)
            trials = []
            for seed in range(N_TRIALS):
                try:
                    r = run_one_setting(env, policies, beh, N_TRAJ, T, GAMMA, seed)
                    r['rhos'] = {
                        m: float(spearman_rank_corr(r[f'{m}_ranking'], gt_ranking))
                        for m in ['is', 'wis', 'pdis', 'dr', 'fqev', 'por_is', 'por_model']
                    }
                    trials.append(r)
                except Exception as ex:
                    logger.info("WARN", f"{cfg_name} ε_β={beh_eps} seed={seed}: {ex}")

            if trials:
                mean_ess = float(np.mean([t['ess'] for t in trials]))
                summary = {
                    method: {
                        'mean': float(np.mean([t['rhos'][method] for t in trials])),
                        'std':  float(np.std([t['rhos'][method] for t in trials])),
                    }
                    for method in ['is', 'wis', 'pdis', 'dr', 'fqev', 'por_is', 'por_model']
                }
                cfg_results[f'eps_{beh_eps}'] = {
                    'beh_eps': beh_eps, 'mean_ess': mean_ess, 'summary': summary
                }
                logger.info(cfg_name,
                    f"ε_β={beh_eps}: ESS={mean_ess*100:5.1f}% | "
                    f"IS={summary['is']['mean']:+.3f}  "
                    f"WIS={summary['wis']['mean']:+.3f}  "
                    f"DR={summary['dr']['mean']:+.3f}  "
                    f"FQE-V={summary['fqev']['mean']:+.3f}  "
                    f"PoR-M={summary['por_model']['mean']:+.3f}"
                )

        all_results[cfg_name] = {'gt_values': gt_values.tolist(),
                                  'gt_ranking': gt_ranking.tolist(),
                                  'results': cfg_results}
        logger.info(cfg_name, "Done.\n")

    return all_results, logger


# ─── Plotting ─────────────────────────────────────────────────────────────────

def plot_goldmine(all_results, out_dir):
    plt.rcParams.update({
        'font.family': 'serif', 'font.size': 8.5,
        'axes.labelsize': 8.5, 'axes.titlesize': 8.5,
        'figure.dpi': 300, 'savefig.dpi': 300,
        'axes.spines.top': False, 'axes.spines.right': False,
        'axes.grid': True, 'grid.alpha': 0.3,
    })

    methods = ['is', 'wis', 'pdis', 'dr', 'fqev', 'por_model']
    labels  = ['IS', 'WIS', 'PDIS', 'DR', 'FQE-V', 'PoR-Model']
    colors  = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
    markers = ['o', 's', '^', 'D', 'v', 'P']

    cfg_names = list(all_results.keys())
    fig, axes = plt.subplots(1, len(cfg_names), figsize=(13, 3.5), sharey=True)
    if len(cfg_names) == 1:
        axes = [axes]

    for ax, cfg_name in zip(axes, cfg_names):
        cfg_info = GOLD_CONFIGS[cfg_name]
        res = all_results[cfg_name]['results']
        rows = sorted(res.values(), key=lambda r: r['beh_eps'])
        ess_vals = [r['mean_ess'] * 100 for r in rows]

        for m, lab, c, mk in zip(methods, labels, colors, markers):
            rhos = [r['summary'][m]['mean'] for r in rows]
            stds = [r['summary'][m]['std'] for r in rows]
            ax.plot(ess_vals, rhos, f'{mk}-', color=c, lw=1.5, ms=5,
                    label=lab, alpha=0.9)
            ax.fill_between(ess_vals,
                np.clip(np.array(rhos) - np.array(stds), -1, 1),
                np.clip(np.array(rhos) + np.array(stds), -1, 1),
                alpha=0.12, color=c)

        ax.axhline(1.0, color='gray', ls='--', lw=0.8, alpha=0.5)
        ax.axhline(0.0, color='gray', ls=':', lw=0.8, alpha=0.3)
        ax.set_xscale('log')
        ax.set_xlabel('ESS (\\%, log)')
        ax.set_title(cfg_info['label'], fontsize=8)
        ax.set_ylim(-1.1, 1.25)
        if ax == axes[0]:
            ax.set_ylabel('Spearman ρ')
        if ax == axes[-1]:
            ax.legend(loc='lower right', fontsize=7, framealpha=0.9)

    plt.suptitle('PoR-Model robustness under non-uniform (gold mine) reward landscapes',
                 fontsize=9, y=1.02)
    plt.tight_layout(w_pad=0.8)
    path = Path(out_dir) / 'goldmine_benchmark.pdf'
    fig.savefig(str(path), bbox_inches='tight', dpi=300)
    fig.savefig(str(path).replace('.pdf', '.png'), bbox_inches='tight', dpi=300)
    plt.close(fig)
    print(f"  Saved gold mine figure to {path}")


def plot_goldmine_heatmap(all_results, out_dir):
    """Heatmap: configs × methods at worst ESS."""
    methods = ['is', 'wis', 'pdis', 'dr', 'fqev', 'por_is', 'por_model']
    method_labels = ['IS', 'WIS', 'PDIS', 'DR', 'FQE-V', 'PoR-IS', 'PoR-M']
    cfg_names = list(all_results.keys())

    data = np.zeros((len(cfg_names), len(methods)))
    for i, cfg_name in enumerate(cfg_names):
        res = all_results[cfg_name]['results']
        worst_key = max(res.keys(), key=lambda k: float(k.replace('eps_', '')))
        row = res[worst_key]
        for j, m in enumerate(methods):
            data[i, j] = row['summary'][m]['mean']

    plt.rcParams.update({'font.family': 'serif', 'font.size': 9, 'figure.dpi': 300})
    fig, ax = plt.subplots(figsize=(8, 2.8))
    im = ax.imshow(data, cmap='RdYlGn', vmin=-1.0, vmax=1.0, aspect='auto')
    ax.set_xticks(range(len(methods)))
    ax.set_xticklabels(method_labels, fontsize=8.5)
    ax.set_yticks(range(len(cfg_names)))
    ax.set_yticklabels(cfg_names, fontsize=8)
    ax.set_title('Spearman ρ at worst coverage (ε_β=0.9) — gold mine configs',
                 fontsize=9)
    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label='Spearman ρ')
    for i in range(len(cfg_names)):
        for j in range(len(methods)):
            c = 'white' if abs(data[i, j]) > 0.7 else 'black'
            ax.text(j, i, f'{data[i, j]:.2f}', ha='center', va='center',
                    fontsize=8, fontweight='bold', color=c)
    plt.tight_layout()
    path = Path(out_dir) / 'goldmine_heatmap.pdf'
    fig.savefig(str(path), bbox_inches='tight', dpi=300)
    fig.savefig(str(path).replace('.pdf', '.png'), bbox_inches='tight', dpi=300)
    plt.close(fig)
    print(f"  Saved heatmap to {path}")
    return data, cfg_names, method_labels


# ─── Entry point ──────────────────────────────────────────────────────────────

def main():
    import os
    os.chdir(Path(__file__).parent.parent)

    all_results, logger = run_goldmine_benchmark()

    out_dir = logger.exp_dir
    with open(Path(out_dir) / 'all_results.json', 'w') as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved to {out_dir}")

    print("\nGenerating figures...")
    plot_goldmine(all_results, out_dir)
    data, cfg_names, method_labels = plot_goldmine_heatmap(all_results, out_dir)

    # Summary table
    print("\n=== SUMMARY TABLE (Spearman ρ at worst coverage ε_β=0.9) ===")
    print(f"{'Config':<14} | {'IS':>6} | {'WIS':>6} | {'PDIS':>6} | "
          f"{'DR':>6} | {'FQE-V':>6} | {'PoR-IS':>7} | {'PoR-M':>7}")
    print("-" * 80)
    for i, cfg_name in enumerate(cfg_names):
        vals = data[i]
        print(f"{cfg_name:<14} | {vals[0]:>+6.3f} | {vals[1]:>+6.3f} | {vals[2]:>+6.3f} | "
              f"{vals[3]:>+6.3f} | {vals[4]:>+6.3f} | {vals[5]:>+7.3f} | {vals[6]:>+7.3f}")

    # Print GT values
    print("\n=== GROUND TRUTH VALUES ===")
    for cfg_name in cfg_names:
        gt = all_results[cfg_name]['gt_values']
        gt_r = all_results[cfg_name]['gt_ranking']
        print(f"{cfg_name}: {[f'P{i}={v:.3f}' for i, v in enumerate(gt)]} | "
              f"Ranking: {['P'+str(r) for r in gt_r]}")

    # Copy figures to paper/figures
    import shutil
    paper_fig_dir = Path("paper/figures")
    paper_fig_dir.mkdir(exist_ok=True)
    for src in Path(out_dir).glob("*.pdf"):
        dst = paper_fig_dir / f"exp10_{src.name}"
        shutil.copy(src, dst)
        print(f"  Copied → paper/figures/exp10_{src.name}")
    for src in Path(out_dir).glob("*.png"):
        dst = paper_fig_dir / f"exp10_{src.name}"
        shutil.copy(src, dst)

    return all_results, data


if __name__ == '__main__':
    main()
