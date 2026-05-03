"""
Experiment 6: Probability of Regret (PoR) vs Expected Value (E[V]) Ranking

Research Question: Is PoR-based policy ranking more robust to distribution
shift than standard expected-value OPE ranking?

Key Insight (why PoR should be more robust):
  - E[V] ranking: each policy estimated independently → different batches →
    common context removed → noise adds up
  - PoR ranking: all policies compared on SAME batch → same context for all →
    common noise cancels (matched-pair comparison)
  - Under extreme distribution shift, E[V] estimates explode or collapse,
    but PoR just counts "who would have done better in each context"

Experimental Design:
  - One SHARED batch of N trajectories under behavior β (for PoR)
  - Separate batches for E[V] (IS/WIS) estimation (standard approach)
  - Ground truth from 2000 rollouts
  - Two scenarios: S1 (good coverage, eps=0.3), S2 (poor coverage, eps=0.9)

Policies: eps ∈ {0.0, 0.1, 0.5, 0.8} — good, near-good, moderate, bad

Expected:
  - S1: IS, WIS, PoR all agree with GT (ρ = 1.0)
  - S2: IS explodes; WIS partially preserved; PoR more robust than both IS and
        potentially more stable than WIS under severe shift
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
from envs import Gridworld, GridworldConfig
from policies import epsilon_greedy_from_q
from utils import set_seed, collect_batch, collect_shared_batch
from ope import importance_sampling, weighted_is
from evaluation import spearman_rank_corr, top1_mismatch
from causal_ope import counterfactual_dominance_matrix, compute_ess, model_based_por_matrix
from logging_utils import ExperimentLogger


def evaluate_policy_rollout(env, policy, N=2000, T=50, seed=0):
    rng = np.random.default_rng(seed)
    returns = []
    for _ in range(N):
        s = env.reset()
        G = 0.0
        for t in range(T):
            a = policy.act(s, rng)
            s, r, done, _ = env.step(a, rng)
            G += r * (0.99 ** t)
            if done:
                break
        returns.append(G)
    return float(np.mean(returns)), np.array(returns)


def build_q(env, config):
    """Build heuristic Q-values toward goal."""
    nS, nA = env.nS, env.nA
    Q = np.zeros((nS, nA))
    for s in range(nS):
        x, y = s // config.width, s % config.width
        gx, gy = config.goal
        if x < gx:
            Q[s, 2] = 1.0  # down (towards goal)
        if y < gy:
            Q[s, 1] = 1.0  # right (towards goal)
        if x > gx:
            Q[s, 0] = 0.05  # up (away from goal)
        if y > gy:
            Q[s, 3] = 0.05  # left (away from goal)
    return Q


def evaluate_ope_scenario(env, policies, policy_names, pi_behavior, N_TRAJ, T, gamma,
                           seed_offset, logger, label):
    """
    Evaluate all policies under behavior pi_behavior using:
      (1) Separate batches for IS/WIS (standard OPE)
      (2) Shared batch for PoR (matched-pair counterfactual)
    """
    K = len(policies)

    # --- Standard OPE (separate batches per policy) ---
    is_values = np.zeros(K)
    wis_values = np.zeros(K)
    ess_values = np.zeros(K)

    for k, pi in enumerate(policies):
        batch = collect_batch(env, pi_behavior, pi, N_TRAJ, T, seed=seed_offset + k)
        returns = batch.returns(gamma)
        w = batch.traj_ratios()

        # IS estimate (unbiased, high variance)
        is_val = float(np.mean(returns * w))
        is_values[k] = is_val if np.isfinite(is_val) else np.nan

        # WIS estimate (biased, lower variance)
        w_norm = w / (w.mean() + 1e-12)
        wis_values[k] = float(np.mean(returns * w_norm))

        ess_values[k] = compute_ess(w)

    # --- PoR (shared batch — all policies on SAME trajectories) ---
    shared_batch, shared_weights = collect_shared_batch(
        env, pi_behavior, policies, N_TRAJ, T, seed=seed_offset + 1000
    )
    shared_returns = shared_batch.returns(gamma)
    por_is_result = counterfactual_dominance_matrix(shared_returns, shared_weights, method='WIS')
    por_model_result = model_based_por_matrix(shared_batch, policies, env.nS, env.nA, gamma)

    # Log results
    logger.info(label, f"ESS (mean): {ess_values.mean()*100:.2f}%")
    logger.info(label, f"IS values: {dict(zip(policy_names, np.where(np.isnan(is_values), float('nan'), is_values.round(3)).tolist()))}")
    logger.info(label, f"WIS values: {dict(zip(policy_names, wis_values.round(4).tolist()))}")
    por_is_win_rates = np.array([
        np.mean([por_is_result.por_matrix[k, j] for j in range(K) if j != k])
        for k in range(K)
    ])
    por_model_win_rates = np.array([
        np.mean([por_model_result.por_matrix[k, j] for j in range(K) if j != k])
        for k in range(K)
    ])
    logger.info(label, f"PoR-IS win rates: {dict(zip(policy_names, por_is_win_rates.round(3).tolist()))}")
    logger.info(label, f"PoR-Model win rates: {dict(zip(policy_names, por_model_win_rates.round(3).tolist()))}")

    return {
        'is_values': is_values,
        'wis_values': wis_values,
        'ess_values': ess_values,
        'mean_ess': float(ess_values.mean()),
        'por_is_result': por_is_result,
        'por_model_result': por_model_result,
        'por_is_win_rates': por_is_win_rates,
        'por_model_win_rates': por_model_win_rates,
        'shared_returns': shared_returns,
        'shared_weights': shared_weights,
        'shared_batch': shared_batch,
    }


def main():
    logger = ExperimentLogger("exp_06_por_comparison", results_dir=Path("results"))

    try:
        logger.section("Setup & Configuration")
        set_seed(42)

        config = GridworldConfig(width=5, height=5, goal=(4, 4), slip=0.0)
        env = Gridworld(config)
        Q = build_q(env, config)

        epsilons = [0.0, 0.1, 0.5, 0.8]
        policies = [epsilon_greedy_from_q(Q, eps=eps) for eps in epsilons]
        policy_names = [f"eps={eps}" for eps in epsilons]
        K = len(policies)
        logger.info("POLICIES", f"4 epsilon-greedy policies: {policy_names}")
        logger.info("CONFIG", "Gridworld 5x5, goal=(4,4)")

        N_TRAJ = 5000
        T = 50
        gamma = 0.99

        # ===== GROUND TRUTH =====
        logger.section("Ground Truth Evaluation (2000 rollouts per policy)")
        true_values = []
        for i, pi in enumerate(policies):
            v, _ = evaluate_policy_rollout(env, pi, N=2000, T=T, seed=200 + i)
            true_values.append(v)
            logger.info("GT", f"  {policy_names[i]}: {v:.4f}")

        true_values = np.array(true_values)
        true_ranking = np.argsort(-true_values)
        logger.info("GT", f"Ground truth ranking: {[policy_names[i] for i in true_ranking]}")
        logger.info("GT", f"Value gaps between adjacent pairs: {np.diff(true_values[true_ranking]).round(4).tolist()}")

        # ===== SCENARIO 1: GOOD BEHAVIOR POLICY =====
        logger.section("Scenario 1: Good Behavior (eps=0.3)")
        pi_good = epsilon_greedy_from_q(Q, eps=0.3)
        res1 = evaluate_ope_scenario(env, policies, policy_names, pi_good,
                                     N_TRAJ, T, gamma, 0, logger, "S1")

        # ===== SCENARIO 2: POOR BEHAVIOR POLICY =====
        logger.section("Scenario 2: Poor Behavior (eps=0.9, biased AWAY from goal)")
        # Biased toward exploring the wrong direction (away from goal corner)
        Q_bad = np.zeros_like(Q)
        for s in range(env.nS):
            x, y = s // config.width, s % config.width
            gx, gy = config.goal
            # Prefer directions AWAY from goal
            Q_bad[s, 0] = 1.0 if x > gx else 0.1   # up (away if already below goal)
            Q_bad[s, 3] = 1.0 if y > gy else 0.1   # left (away if already right of goal)
            Q_bad[s, 1] = 0.05                       # rarely go right
            Q_bad[s, 2] = 0.05                       # rarely go down
        pi_bad = epsilon_greedy_from_q(Q_bad, eps=0.9)
        res2 = evaluate_ope_scenario(env, policies, policy_names, pi_bad,
                                     N_TRAJ, T, gamma, 100, logger, "S2")

        # ===== RANKING COMPARISON =====
        logger.section("Ranking Accuracy Comparison")

        # Clip IS for ranking (treat nan as -inf)
        def safe_is(v):
            return np.where(np.isnan(v), -np.inf, np.clip(v, -1e6, 1e6))

        metrics = {}
        for label, res in [("S1 (good)", res1), ("S2 (bad)", res2)]:
            sp_is = spearman_rank_corr(true_values, safe_is(res['is_values']))
            sp_wis = spearman_rank_corr(true_values, res['wis_values'])
            sp_por_is = spearman_rank_corr(true_values, res['por_is_win_rates'])
            sp_por_model = spearman_rank_corr(true_values, res['por_model_win_rates'])

            t1_is = top1_mismatch(true_values, safe_is(res['is_values']))
            t1_wis = top1_mismatch(true_values, res['wis_values'])
            t1_por_is = top1_mismatch(true_values, res['por_is_win_rates'])
            t1_por_model = top1_mismatch(true_values, res['por_model_win_rates'])

            logger.info("RANKING", f"  {label}:")
            logger.info("RANKING", f"    ESS = {res['mean_ess']*100:.2f}%")
            logger.info("RANKING", f"    IS        Spearman={sp_is:.3f}, Top1-err={t1_is}")
            logger.info("RANKING", f"    WIS       Spearman={sp_wis:.3f}, Top1-err={t1_wis}")
            logger.info("RANKING", f"    PoR-IS    Spearman={sp_por_is:.3f}, Top1-err={t1_por_is}")
            logger.info("RANKING", f"    PoR-Model Spearman={sp_por_model:.3f}, Top1-err={t1_por_model}")

            metrics[label] = {
                'ess': float(res['mean_ess']),
                'IS': {'spearman': float(sp_is), 'top1': int(t1_is)},
                'WIS': {'spearman': float(sp_wis), 'top1': int(t1_wis)},
                'PoR-IS': {'spearman': float(sp_por_is), 'top1': int(t1_por_is)},
                'PoR-Model': {'spearman': float(sp_por_model), 'top1': int(t1_por_model)},
            }

        # ===== VISUALIZATION =====
        logger.section("Visualization")
        fig = plt.figure(figsize=(20, 12))
        gs = gridspec.GridSpec(2, 4, figure=fig, hspace=0.45, wspace=0.38)

        method_colors = {'IS': '#e74c3c', 'WIS': '#3498db', 'PoR-IS': '#e67e22', 'PoR-Model': '#27ae60'}
        scenario_keys = list(metrics.keys())

        # --- Plot 1: Spearman ρ bar chart ---
        ax1 = fig.add_subplot(gs[0, :2])
        x = np.arange(2)
        n_methods = len(method_colors)
        width = 0.18
        offsets = np.linspace(-width * 1.5, width * 1.5, n_methods)
        for m_idx, (m_name, m_color) in enumerate(method_colors.items()):
            vals = [metrics[s][m_name]['spearman'] for s in scenario_keys]
            bars = ax1.bar(x + offsets[m_idx], vals, width, label=m_name,
                           color=m_color, alpha=0.85, edgecolor='black', linewidth=0.8)
            for bar, v in zip(bars, vals):
                ax1.text(bar.get_x() + bar.get_width()/2, v + 0.04 * np.sign(v),
                         f'{v:.2f}', ha='center', va='bottom' if v >= 0 else 'top',
                         fontsize=7, fontweight='bold', color='black')
        ax1.axhline(0, color='black', linewidth=0.8, linestyle='--')
        ax1.axhline(1, color='gray', linewidth=0.5, linestyle=':')
        ax1.set_ylabel('Spearman ρ vs Ground Truth', fontsize=11)
        ax1.set_title('Ranking Accuracy: IS / WIS / PoR-IS / PoR-Model\n(Higher = better)', fontsize=10)
        ax1.set_xticks(x)
        ax1.set_xticklabels(['S1: Good Coverage\n(ε=0.3)', 'S2: Poor Coverage\n(ε=0.9 biased)'])
        ax1.legend(fontsize=8)
        ax1.set_ylim([-1.2, 1.5])
        ax1.grid(axis='y', alpha=0.3)

        # --- Plot 2: Top-1 error ---
        ax2 = fig.add_subplot(gs[0, 2:])
        for m_idx, (m_name, m_color) in enumerate(method_colors.items()):
            vals = [metrics[s][m_name]['top1'] for s in scenario_keys]
            ax2.bar(x + offsets[m_idx], vals, width, label=m_name,
                    color=m_color, alpha=0.85, edgecolor='black', linewidth=0.8)
        ax2.set_ylabel('Top-1 Mismatch (0=correct, 1=wrong)', fontsize=11)
        ax2.set_title('Best Policy Selection Error\n(Lower = more reliable selection)', fontsize=10)
        ax2.set_xticks(x)
        ax2.set_xticklabels(['S1: Good Coverage\n(ε=0.3)', 'S2: Poor Coverage\n(ε=0.9 biased)'])
        ax2.legend(fontsize=8)
        ax2.set_ylim([0, 1.3])
        ax2.grid(axis='y', alpha=0.3)

        # --- Plot 3 & 4: PoR-Model matrices ---
        for plot_idx, (res, title) in enumerate([(res1, 'S1: Good Coverage'), (res2, 'S2: Poor Coverage')]):
            ax = fig.add_subplot(gs[1, plot_idx*2:plot_idx*2+2])
            pm = res['por_model_result'].por_matrix
            im = ax.imshow(pm, cmap='RdYlGn', vmin=0, vmax=1, aspect='auto')
            ax.set_xticks(range(K))
            ax.set_yticks(range(K))
            ax.set_xticklabels(policy_names, fontsize=8, rotation=20)
            ax.set_yticklabels(policy_names, fontsize=8)
            ax.set_xlabel('Policy j', fontsize=9)
            ax.set_ylabel('Policy i', fontsize=9)
            ax.set_title(f'PoR-Model Matrix ({title})\nPoR[i,j] = P(Q_i(s₀) > Q_j(s₀))', fontsize=9)
            for i in range(K):
                for j in range(K):
                    v = pm[i, j]
                    ax.text(j, i, f'{v:.2f}', ha='center', va='center', fontsize=9,
                            color='white' if v < 0.3 or v > 0.7 else 'black', fontweight='bold')
            plt.colorbar(im, ax=ax, shrink=0.8)

        plt.suptitle(
            'Experiment 6: Causal PoR vs Expected Value Ranking\n'
            f'Gridworld 5×5 | N={N_TRAJ} trajectories | γ={gamma} | Policies: ε ∈ {epsilons}',
            fontsize=12, fontweight='bold'
        )

        outpath = logger.exp_dir / "por_vs_ev_comparison.png"
        plt.savefig(outpath, dpi=200, bbox_inches='tight')
        plt.close()
        logger.info("VIZ", f"Saved: {outpath}")

        # Second figure: detailed per-policy comparison
        fig2, axes2 = plt.subplots(1, 3, figsize=(15, 5))

        # Plot estimated values under S1 and S2
        x_idx = np.arange(K)
        for ax_idx, (m_name, m_vals_fn, ax) in enumerate([
            ('WIS', lambda r: r['wis_values'], axes2[0]),
            ('PoR-Model win-rate', lambda r: r['por_model_win_rates'], axes2[1]),
        ]):
            v1 = m_vals_fn(res1)
            v2 = m_vals_fn(res2)
            # Normalize for visual comparison
            v1_n = (v1 - v1.min()) / (v1.max() - v1.min() + 1e-12)
            v2_n = (v2 - v2.min()) / (v2.max() - v2.min() + 1e-12)
            gt_n = (true_values - true_values.min()) / (true_values.max() - true_values.min() + 1e-12)

            ax.plot(x_idx, gt_n, 'k^-', linewidth=2, markersize=8, label='Ground Truth')
            ax.plot(x_idx, v1_n, 'o--', color='#27ae60', linewidth=2, markersize=7, label='S1 (good β)')
            ax.plot(x_idx, v2_n, 's--', color='#e74c3c', linewidth=2, markersize=7, label='S2 (bad β)')
            ax.set_xticks(x_idx)
            ax.set_xticklabels(policy_names, fontsize=9)
            ax.set_ylabel('Normalized Score', fontsize=10)
            ax.set_title(f'{m_name} Estimates\n(normalized for comparison)', fontsize=10)
            ax.legend(fontsize=9)
            ax.grid(alpha=0.3)
            sp1 = spearman_rank_corr(true_values, m_vals_fn(res1))
            sp2 = spearman_rank_corr(true_values, m_vals_fn(res2))
            ax.set_xlabel(f'S1 ρ={sp1:.2f} | S2 ρ={sp2:.2f}', fontsize=10, color='purple', fontweight='bold')

        # ESS comparison
        ax3 = axes2[2]
        ax3.bar(x_idx - 0.2, res1['ess_values'] * 100, 0.35,
                label='S1 (good β)', color='#27ae60', alpha=0.85)
        ax3.bar(x_idx + 0.2, res2['ess_values'] * 100, 0.35,
                label='S2 (bad β)', color='#e74c3c', alpha=0.85)
        ax3.set_ylabel('ESS (%)', fontsize=10)
        ax3.set_title('Effective Sample Size Per Policy', fontsize=10)
        ax3.set_xticks(x_idx)
        ax3.set_xticklabels(policy_names, fontsize=9)
        ax3.legend(fontsize=9)
        ax3.set_yscale('log')
        ax3.grid(axis='y', alpha=0.3)

        plt.suptitle('Exp 6: Method Comparison — Normalized Rankings Under Distribution Shift', fontsize=11, fontweight='bold')
        plt.tight_layout()
        outpath2 = logger.exp_dir / "method_comparison_detail.png"
        plt.savefig(outpath2, dpi=200, bbox_inches='tight')
        plt.close()
        logger.info("VIZ", f"Saved: {outpath2}")

        # ===== SUMMARY =====
        logger.section("Experiment 6 Summary")
        for label, m in metrics.items():
            logger.info("SUMMARY", f"  {label} (ESS={m['ess']*100:.2f}%):")
            for method in ['IS', 'WIS', 'PoR-IS', 'PoR-Model']:
                logger.info("SUMMARY", f"    {method}: ρ={m[method]['spearman']:.3f}, Top1-err={m[method]['top1']}")

        final_data = {
            "config": {"env": "Gridworld 5x5", "policies": policy_names,
                        "N_traj": N_TRAJ, "gamma": gamma},
            "ground_truth_values": true_values.tolist(),
            "ground_truth_ranking": [policy_names[i] for i in true_ranking],
            "ranking_metrics": metrics,
            "por_matrix_s1": res1['por_model_result'].por_matrix.tolist(),
            "por_matrix_s2": res2['por_model_result'].por_matrix.tolist(),
        }
        logger.data("experiment_results", final_data, "PoR vs E[V] comparison with shared batch")
        logger.save()
        logger.success(f"Experiment 6 complete! Results in {logger.exp_dir}")

    except Exception as e:
        logger.error(f"Experiment failed: {str(e)}")
        import traceback
        logger.section("ERROR TRACEBACK")
        logger._log(traceback.format_exc())
        logger.save()
        raise


if __name__ == "__main__":
    main()
