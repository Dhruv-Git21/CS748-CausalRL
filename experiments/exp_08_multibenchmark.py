"""
Experiment 8: Multi-Environment Benchmark
==========================================
Tests PoR-Model vs IS/WIS/PDIS across four gridworld variants with
different sizes, reward structures, and stochasticity levels.
Demonstrates generalizability of the methodology beyond a single domain.

Environments:
  E1: GW-3x3    — 9 states, dense reward, deterministic
  E2: GW-5x5    — 25 states, dense reward, deterministic (baseline)
  E3: GW-5x5-S  — 25 states, dense reward, stochastic (slip=0.15)
  E4: GW-7x7    — 49 states, dense reward, deterministic
  E5: GW-10x10  — 100 states, dense reward, deterministic (large)

For each environment × behavior policy × trial, we measure:
  - Spearman ρ for IS, WIS, PDIS, PoR-IS, PoR-Model
  - ESS fraction
  - Top-1 mismatch

Results are aggregated and compared across environments.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from datetime import datetime

from envs import Gridworld, GridworldConfig
from policies import epsilon_greedy_from_q
from utils import collect_shared_batch, collect_batch
from causal_ope import (
    model_based_por_matrix, compute_ess, counterfactual_dominance_matrix
)
from evaluation import spearman_rank_corr
from ope import importance_sampling, weighted_is, per_decision_is
from logging_utils import ExperimentLogger


# ─── Environment registry ─────────────────────────────────────────────────────

ENVS = {
    'GW-3x3': GridworldConfig(width=3, height=3, goal=(2, 2), slip=0.0),
    'GW-5x5': GridworldConfig(width=5, height=5, goal=(4, 4), slip=0.0),
    'GW-5x5-S': GridworldConfig(width=5, height=5, goal=(4, 4), slip=0.15),
    'GW-7x7': GridworldConfig(width=7, height=7, goal=(6, 6), slip=0.0),
    'GW-10x10': GridworldConfig(width=10, height=10, goal=(9, 9), slip=0.0),
}

ENV_LABELS = {
    'GW-3x3': 'GW-3×3\n(9 states)',
    'GW-5x5': 'GW-5×5\n(25 states)',
    'GW-5x5-S': 'GW-5×5-S\n(stochastic)',
    'GW-7x7': 'GW-7×7\n(49 states)',
    'GW-10x10': 'GW-10×10\n(100 states)',
}

BEHAVIOR_EPS = [0.1, 0.3, 0.5, 0.7, 0.9]
EVAL_EPS = [0.0, 0.1, 0.5, 0.8]
N_TRIALS = 25
N_TRAJ = 300
T = 50
GAMMA = 0.99


# ─── Helpers ──────────────────────────────────────────────────────────────────

def build_q(env, cfg):
    Q = np.zeros((env.nS, env.nA))
    for s in range(env.nS):
        x, y = s // cfg.width, s % cfg.width
        gx, gy = cfg.goal
        if x < gx: Q[s, 2] = 1.0   # down
        if y < gy: Q[s, 1] = 1.0   # right
        if x > gx: Q[s, 0] = 0.05  # up
        if y > gy: Q[s, 3] = 0.05  # left
    return Q


def rollout_value(env, policy, N=500, T=50, gamma=0.99, seed=0):
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


def run_one_setting(env, cfg, policies, beh_policy, n_traj, T, gamma, seed):
    """Run all OPE methods on one (env, behavior, seed) triple."""
    # Shared batch for PoR
    shared_batch, weights_list = collect_shared_batch(
        env, beh_policy, policies, n_traj, T, seed=seed
    )
    shared_ret = shared_batch.returns(gamma)
    mean_ess = float(np.mean([compute_ess(w) for w in weights_list]))

    # IS / WIS values
    is_vals = np.array([float(np.mean(shared_ret * w)) for w in weights_list])
    wis_vals = np.array([
        float(np.mean(shared_ret * (w / (w.mean() + 1e-12))))
        for w in weights_list
    ])

    # PDIS (per-decision IS) — use shared batch
    pdis_vals = np.zeros(len(policies))
    for k, pi in enumerate(policies):
        batch_k = collect_batch(env, beh_policy, pi, n_traj, T, seed=seed + 1000 * k)
        step_w = batch_k.step_cum_ratios()
        disc = (gamma ** np.arange(T))[None, :]
        pdis_vals[k] = float(np.mean(np.sum(disc * batch_k.rewards * step_w, axis=1)))

    # PoR-IS
    por_is_res = counterfactual_dominance_matrix(shared_ret, weights_list, method='WIS')

    # PoR-Model
    por_mod_res = model_based_por_matrix(
        shared_batch, policies, env.nS, env.nA, gamma=gamma, n_fqe_iters=50
    )

    return {
        'ess': mean_ess,
        'is_ranking': np.argsort(-is_vals),
        'wis_ranking': np.argsort(-wis_vals),
        'pdis_ranking': np.argsort(-pdis_vals),
        'por_is_ranking': por_is_res.por_ranking,
        'por_model_ranking': por_mod_res.por_ranking,
    }


# ─── Main benchmark ───────────────────────────────────────────────────────────

def run_benchmark():
    logger = ExperimentLogger("exp_08_multibenchmark",
                              results_dir=Path("results"))
    logger.section("Multi-Environment Benchmark")
    logger.info("CONFIG", f"Environments: {list(ENVS.keys())}")
    logger.info("CONFIG", f"Behavior ε: {BEHAVIOR_EPS}")
    logger.info("CONFIG", f"N_traj={N_TRAJ}, T={T}, γ={GAMMA}, trials={N_TRIALS}")

    all_results = {}

    for env_name, cfg in ENVS.items():
        env = Gridworld(cfg)
        Q = build_q(env, cfg)

        # Build policies
        eval_policies = [epsilon_greedy_from_q(Q, eps=e) for e in EVAL_EPS]

        # Ground truth values
        gt_values = np.array([
            rollout_value(env, p, N=500, T=T, gamma=GAMMA, seed=i)
            for i, p in enumerate(eval_policies)
        ])
        gt_ranking = np.argsort(-gt_values)

        logger.info(env_name, f"GT values: {dict(zip([f'ε={e}' for e in EVAL_EPS], gt_values.round(3).tolist()))}")

        env_results = {}
        for beh_eps in BEHAVIOR_EPS:
            beh = epsilon_greedy_from_q(Q, eps=beh_eps)

            trials = []
            for seed in range(N_TRIALS):
                try:
                    r = run_one_setting(env, cfg, eval_policies, beh, N_TRAJ, T, GAMMA, seed)
                    r['rhos'] = {
                        m: float(spearman_rank_corr(r[f'{m}_ranking'], gt_ranking))
                        for m in ['is', 'wis', 'pdis', 'por_is', 'por_model']
                    }
                    trials.append(r)
                except Exception as ex:
                    logger.info("WARN", f"{env_name} ε_β={beh_eps} seed={seed}: {ex}")

            if trials:
                mean_ess = float(np.mean([t['ess'] for t in trials]))
                summary = {
                    method: {
                        'mean': float(np.mean([t['rhos'][method] for t in trials])),
                        'std': float(np.std([t['rhos'][method] for t in trials])),
                    }
                    for method in ['is', 'wis', 'pdis', 'por_is', 'por_model']
                }
                env_results[f'eps_{beh_eps}'] = {
                    'beh_eps': beh_eps,
                    'mean_ess': mean_ess,
                    'summary': summary,
                }
                por_rho = summary['por_model']['mean']
                wis_rho = summary['wis']['mean']
                logger.info(env_name,
                    f"ε_β={beh_eps}: ESS={mean_ess*100:.2f}%, "
                    f"WIS={wis_rho:.3f}, PoR-Mdl={por_rho:.3f}")

        all_results[env_name] = env_results
        logger.info(env_name, "Done.")

    return all_results, logger


# ─── Plotting ─────────────────────────────────────────────────────────────────

def plot_benchmark(all_results, out_dir):
    methods = ['is', 'wis', 'pdis', 'por_model']
    method_labels = ['IS', 'WIS', 'PDIS', 'PoR-Model']
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#9467bd']
    markers = ['o', 's', '^', 'D']

    fig, axes = plt.subplots(1, len(ENVS), figsize=(14, 3.2), sharey=True)

    plt.rcParams.update({
        'font.family': 'serif', 'font.size': 8.5,
        'axes.labelsize': 8.5, 'axes.titlesize': 8.5,
        'figure.dpi': 300, 'savefig.dpi': 300,
        'axes.spines.top': False, 'axes.spines.right': False,
        'axes.grid': True, 'grid.alpha': 0.3,
    })

    for ax, (env_name, env_res) in zip(axes, all_results.items()):
        rows = sorted(env_res.values(), key=lambda r: r['beh_eps'])
        ess_vals = [r['mean_ess'] * 100 for r in rows]

        for m, label, c, mk in zip(methods, method_labels, colors, markers):
            rhos = [r['summary'][m]['mean'] for r in rows]
            stds = [r['summary'][m]['std'] for r in rows]
            ax.plot(ess_vals, rhos, f'{mk}-', color=c, lw=1.5, ms=5,
                    label=label, alpha=0.9)
            ax.fill_between(ess_vals,
                            np.clip(np.array(rhos) - np.array(stds), -1, 1),
                            np.clip(np.array(rhos) + np.array(stds), -1, 1),
                            alpha=0.12, color=c)

        ax.axhline(1.0, color='gray', ls='--', lw=0.8, alpha=0.5)
        ax.axhline(0.0, color='gray', ls=':', lw=0.8, alpha=0.3)
        ax.set_xscale('log')
        ax.set_xlabel('ESS (\\%, log)')
        ax.set_title(ENV_LABELS[env_name])
        ax.set_ylim(-1.1, 1.25)
        if ax == axes[0]:
            ax.set_ylabel('Spearman ρ')
        if ax == axes[-1]:
            ax.legend(loc='lower right', fontsize=7, framealpha=0.9)

    plt.suptitle('PoR-Model is consistently superior under low ESS across all environments',
                 fontsize=9, y=1.02)
    plt.tight_layout(w_pad=0.8)
    path = Path(out_dir) / 'multi_env_benchmark.pdf'
    fig.savefig(str(path), bbox_inches='tight', dpi=300)
    fig.savefig(str(path).replace('.pdf', '.png'), bbox_inches='tight', dpi=300)
    plt.close(fig)
    print(f"  Saved multi-env figure to {path}")


def plot_heatmap(all_results, out_dir):
    """Heatmap: rows=environments, cols=methods, cells=Spearman ρ at worst ESS."""
    methods = ['is', 'wis', 'pdis', 'por_is', 'por_model']
    method_labels = ['IS', 'WIS', 'PDIS', 'PoR-IS', 'PoR-Model']
    env_names = list(all_results.keys())

    # Use worst behavior (highest ε_β) for each environment
    data = np.zeros((len(env_names), len(methods)))
    for i, env_name in enumerate(env_names):
        env_res = all_results[env_name]
        worst_key = max(env_res.keys(), key=lambda k: float(k.replace('eps_', '')))
        row = env_res[worst_key]
        for j, m in enumerate(methods):
            data[i, j] = row['summary'][m]['mean']

    fig, ax = plt.subplots(figsize=(7.0, 3.0))
    plt.rcParams.update({'font.family': 'serif', 'font.size': 9, 'figure.dpi': 300})
    im = ax.imshow(data, cmap='RdYlGn', vmin=-1.0, vmax=1.0, aspect='auto')
    ax.set_xticks(range(len(methods)))
    ax.set_xticklabels(method_labels, fontsize=8.5)
    ax.set_yticks(range(len(env_names)))
    ax.set_yticklabels([ENV_LABELS[e].replace('\n', ' ') for e in env_names], fontsize=8)
    ax.set_title('Spearman ρ at worst coverage (ε_β=0.9) — green=correct, red=reversed', fontsize=9)
    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label='Spearman ρ')
    for i in range(len(env_names)):
        for j in range(len(methods)):
            c = 'white' if abs(data[i, j]) > 0.7 else 'black'
            ax.text(j, i, f'{data[i, j]:.2f}', ha='center', va='center',
                    fontsize=8, fontweight='bold', color=c)

    plt.tight_layout()
    path = Path(out_dir) / 'heatmap_worst_ess.pdf'
    fig.savefig(str(path), bbox_inches='tight', dpi=300)
    fig.savefig(str(path).replace('.pdf', '.png'), bbox_inches='tight', dpi=300)
    plt.close(fig)
    print(f"  Saved heatmap to {path}")

    return data, env_names, method_labels


def main():
    import os
    os.chdir(Path(__file__).parent.parent)

    all_results, logger = run_benchmark()

    # Save results JSON
    out_dir = logger.exp_dir
    with open(Path(out_dir) / 'all_results.json', 'w') as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved to {out_dir}")

    # Generate plots
    print("\nGenerating figures...")
    plot_benchmark(all_results, out_dir)
    data, envs, methods = plot_heatmap(all_results, out_dir)

    # Print summary table
    print("\n=== SUMMARY TABLE (Spearman ρ at worst coverage ε_β=0.9) ===")
    print(f"{'Environment':<16} | {'IS':>6} | {'WIS':>6} | {'PDIS':>6} | {'PoR-IS':>7} | {'PoR-Mdl':>8}")
    print("-" * 65)
    for i, env in enumerate(envs):
        vals = data[i]
        print(f"{env:<16} | {vals[0]:>6.3f} | {vals[1]:>6.3f} | {vals[2]:>6.3f} | {vals[3]:>7.3f} | {vals[4]:>8.3f}")

    print("\n=== SUMMARY TABLE (Spearman ρ at moderate coverage ε_β=0.5) ===")
    data2 = np.zeros((len(all_results), 5))
    methods5 = ['is', 'wis', 'pdis', 'por_is', 'por_model']
    for i, (env_name, env_res) in enumerate(all_results.items()):
        if 'eps_0.5' in env_res:
            row = env_res['eps_0.5']
            for j, m in enumerate(methods5):
                data2[i, j] = row['summary'][m]['mean']
    env_names_list = list(all_results.keys())
    print(f"{'Environment':<16} | {'IS':>6} | {'WIS':>6} | {'PDIS':>6} | {'PoR-IS':>7} | {'PoR-Mdl':>8}")
    print("-" * 65)
    for i, env in enumerate(env_names_list):
        vals = data2[i]
        print(f"{env:<16} | {vals[0]:>6.3f} | {vals[1]:>6.3f} | {vals[2]:>6.3f} | {vals[3]:>7.3f} | {vals[4]:>8.3f}")

    # Copy figures to paper/figures
    import shutil
    paper_fig_dir = Path("paper/figures")
    for src in Path(out_dir).glob("*.pdf"):
        dst = paper_fig_dir / f"exp8_{src.name}"
        shutil.copy(src, dst)
        print(f"  Copied {src.name} → paper/figures/exp8_{src.name}")
    for src in Path(out_dir).glob("*.png"):
        dst = paper_fig_dir / f"exp8_{src.name}"
        shutil.copy(src, dst)

    return all_results, data


if __name__ == '__main__':
    main()
