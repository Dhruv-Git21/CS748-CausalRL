"""
Experiment 7: Empirical Validation of Misranking Probability Bound

Research Question: Does the theoretical misranking bound from Theorem 1 hold
empirically? Does PoR's bound provide a tighter guarantee than IS?

Theorem 1 (OPE Misranking Bound, IS estimator):
  For N i.i.d. trajectories with ESS = n_eff/N and bounded returns G in [0, C]:
  P(V_hat_B >= V_hat_A | V_A > V_B, gap = delta) <= 2 * exp(-n_eff * delta^2 / (2*C^2))
  where n_eff = N * ESS.

Theorem 2 (PoR Misranking Bound):
  P(PoR_hat(A,B) < 0.5 | PoR(A,B) > 0.5, margin = rho) <= exp(-2 * n_eff * rho^2)
  Note: PoR bound has NO dependence on C (return range).

Experimental Validation:
  - Fix two policies pi_A (eps=0.0, greedy) and pi_B (eps=0.8, random)
    with true performance gap delta known from ground truth
  - Vary behavior policy over 7 settings (inducing different ESS levels)
  - For each setting: run 500 Monte Carlo trials, measure:
      * Empirical misranking rate for WIS
      * Empirical misranking rate for PoR
      * Effective sample size (ESS)
  - Compare empirical rates to theoretical bounds
  - Show PoR bound is tighter (less conservative) than IS bound

Setup:
  - Gridworld 5×5
  - pi_A: greedy (eps=0.0), pi_B: mostly random (eps=0.8)
  - True gap delta measured from 5000-rollout ground truth
  - Behavior policies: eps ∈ {0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9}
  - N=500 trajectories per trial, 300 Monte Carlo trials per behavior policy
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from envs import Gridworld, GridworldConfig
from policies import epsilon_greedy_from_q
from utils import set_seed, collect_batch, collect_shared_batch
from ope import weighted_is, importance_sampling
from causal_ope import probability_of_regret, compute_ess, misranking_bound, por_misranking_bound, model_based_por_matrix
from logging_utils import ExperimentLogger


def evaluate_policy_rollout(env, policy, N=5000, T=50, seed=0):
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
    return float(np.mean(returns)), np.std(returns)


def run_trial(env, pi_A, pi_B, pi_beh, N, T, gamma, rng_seed, nS, nA):
    """Single Monte Carlo trial: returns (wis_misrank, por_model_misrank, ess)."""
    # Separate batches for WIS comparison (standard approach)
    batch_A = collect_batch(env, pi_beh, pi_A, N, T, seed=rng_seed)
    batch_B = collect_batch(env, pi_beh, pi_B, N, T, seed=rng_seed + 10000)

    returns_A = batch_A.returns(gamma)
    returns_B = batch_B.returns(gamma)
    w_A = batch_A.traj_ratios()
    w_B = batch_B.traj_ratios()

    # WIS estimate (using separate batches — standard approach)
    res_A = weighted_is(returns_A, w_A)
    res_B = weighted_is(returns_B, w_B)
    wis_misrank = int(res_B.estimate >= res_A.estimate)

    # PoR-Model: use shared batch + FQE to avoid IS zero-weight problem
    shared_batch, shared_weights = collect_shared_batch(
        env, pi_beh, [pi_A, pi_B], N, T, seed=rng_seed + 20000
    )
    por_result = model_based_por_matrix(shared_batch, [pi_A, pi_B], nS, nA, gamma, n_fqe_iters=50)
    # PoR(A, B) = por_matrix[0, 1]
    por_A_beats_B = por_result.por_matrix[0, 1]
    por_misrank = int(por_A_beats_B <= 0.5)

    # ESS from shared batch weights for pi_A (as reference)
    ess = float(np.mean([compute_ess(shared_weights[0]), compute_ess(shared_weights[1])]))

    return wis_misrank, por_misrank, ess


def main():
    logger = ExperimentLogger("exp_07_bound_validation", results_dir=Path("results"))

    try:
        logger.section("Setup & Configuration")
        set_seed(42)

        config = GridworldConfig(width=5, height=5, goal=(4, 4), slip=0.0)
        env = Gridworld(config)
        nS, nA = env.nS, env.nA

        Q = np.zeros((nS, nA))
        for s in range(nS):
            x, y = s // config.width, s % config.width
            for a in range(nA):
                if a == 1 and y < config.goal[1]:
                    Q[s, a] = 1.0
                elif a == 2 and x < config.goal[0]:
                    Q[s, a] = 1.0
                elif a == 0 and x > 0:
                    Q[s, a] = 0.1
                elif a == 3 and y > 0:
                    Q[s, a] = 0.1

        pi_A = epsilon_greedy_from_q(Q, eps=0.0)   # greedy: best policy
        pi_B = epsilon_greedy_from_q(Q, eps=0.8)   # mostly random: worse policy

        T = 50
        gamma = 0.99
        N_TRAJ = 300       # per trial (moderate size to make ESS impact visible)
        N_TRIALS = 100     # Monte Carlo trials per behavior setting (fast version)
        C = 1.0            # return range bound (rewards in [-0.01, 1.0], clip to [0,1])

        # ===== GROUND TRUTH =====
        logger.section("Ground Truth: True Performance Gap")
        v_A, std_A = evaluate_policy_rollout(env, pi_A, N=5000, T=T, seed=1)
        v_B, std_B = evaluate_policy_rollout(env, pi_B, N=5000, T=T, seed=2)
        delta = v_A - v_B
        logger.info("GT", f"V(pi_A) = {v_A:.4f} ± {std_A:.4f}")
        logger.info("GT", f"V(pi_B) = {v_B:.4f} ± {std_B:.4f}")
        logger.info("GT", f"True gap delta = {delta:.4f}")
        assert delta > 0, f"pi_A should be better! Got delta={delta}"

        # True PoR: compute from large rollout samples
        # PoR(A, B) = fraction of trajectories where A gets higher return than B
        rng_gt = np.random.default_rng(999)
        returns_A_gt = []
        returns_B_gt = []
        for _ in range(2000):
            s = env.reset()
            G = 0.0
            for t in range(T):
                a = pi_A.act(s, rng_gt)
                s, r, done, _ = env.step(a, rng_gt)
                G += r * (0.99 ** t)
                if done:
                    break
            returns_A_gt.append(G)

        rng_gt2 = np.random.default_rng(998)
        for _ in range(2000):
            s = env.reset()
            G = 0.0
            for t in range(T):
                a = pi_B.act(s, rng_gt2)
                s, r, done, _ = env.step(a, rng_gt2)
                G += r * (0.99 ** t)
                if done:
                    break
            returns_B_gt.append(G)

        true_por = float(np.mean(np.array(returns_A_gt) > np.array(returns_B_gt)))
        por_margin = true_por - 0.5
        logger.info("GT", f"True PoR(A, B) = {true_por:.4f}")
        logger.info("GT", f"PoR margin rho = {por_margin:.4f}")

        # ===== BEHAVIOR POLICIES =====
        behavior_epsilons = [0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9]
        behavior_names = [f"ε={e}" for e in behavior_epsilons]

        # ===== MONTE CARLO VALIDATION =====
        logger.section(f"Monte Carlo Validation ({N_TRIALS} trials per behavior policy)")

        results = []
        for beh_idx, (beh_eps, beh_name) in enumerate(zip(behavior_epsilons, behavior_names)):
            Q_beh = Q.copy()
            if beh_eps >= 0.7:
                # Biased behavior policy: prefers going away from goal
                for s in range(nS):
                    x, y = s // config.width, s % config.width
                    Q_beh[s, :] = 0.1
                    if beh_eps >= 0.9:
                        Q_beh[s, 0] = 0.8  # prefer up (away from goal if start at top)
                        Q_beh[s, 3] = 0.8  # prefer left

            pi_beh = epsilon_greedy_from_q(Q_beh, eps=beh_eps)

            wis_misranks = []
            por_misranks = []
            ess_vals = []

            for trial in range(N_TRIALS):
                wm, pm, ess = run_trial(env, pi_A, pi_B, pi_beh, N_TRAJ, T, gamma,
                                         rng_seed=beh_idx * 10000 + trial,
                                         nS=env.nS, nA=env.nA)
                wis_misranks.append(wm)
                por_misranks.append(pm)
                ess_vals.append(ess)

            empirical_wis_mr = float(np.mean(wis_misranks))
            empirical_por_mr = float(np.mean(por_misranks))
            mean_ess = float(np.mean(ess_vals))
            n_eff = N_TRAJ * mean_ess

            # Theoretical bounds
            bound_is = misranking_bound(n_eff, delta, C=C)
            bound_por = por_misranking_bound(n_eff, por_margin)

            logger.info(beh_name, f"  ESS={mean_ess*100:.2f}% | n_eff={n_eff:.1f}")
            logger.info(beh_name, f"  WIS misrank rate: {empirical_wis_mr:.3f} (bound: {bound_is:.3f})")
            logger.info(beh_name, f"  PoR misrank rate: {empirical_por_mr:.3f} (bound: {bound_por:.3f})")

            results.append({
                'beh_eps': beh_eps,
                'beh_name': beh_name,
                'mean_ess': mean_ess,
                'n_eff': n_eff,
                'empirical_wis_mr': empirical_wis_mr,
                'empirical_por_mr': empirical_por_mr,
                'bound_is': bound_is,
                'bound_por': bound_por,
            })

        # ===== VISUALIZATION =====
        logger.section("Visualization")

        ess_pcts = np.array([r['mean_ess'] * 100 for r in results])
        emp_wis = np.array([r['empirical_wis_mr'] for r in results])
        emp_por = np.array([r['empirical_por_mr'] for r in results])
        bound_is_arr = np.array([r['bound_is'] for r in results])
        bound_por_arr = np.array([r['bound_por'] for r in results])
        n_effs = np.array([r['n_eff'] for r in results])

        fig, axes = plt.subplots(1, 2, figsize=(14, 6))

        # Plot 1: Misranking rate vs ESS
        ax = axes[0]
        ax.plot(ess_pcts, emp_wis, 'o-', color='#e74c3c', linewidth=2,
                markersize=8, label='WIS Empirical', zorder=3)
        ax.plot(ess_pcts, emp_por, 's-', color='#27ae60', linewidth=2,
                markersize=8, label='PoR Empirical', zorder=3)
        ax.plot(ess_pcts, bound_is_arr, '--', color='#e74c3c', linewidth=1.5,
                alpha=0.7, label='WIS Bound (Thm 1)')
        ax.plot(ess_pcts, bound_por_arr, '--', color='#27ae60', linewidth=1.5,
                alpha=0.7, label='PoR Bound (Thm 2)')
        ax.axhline(0.5, color='gray', linestyle=':', alpha=0.5, label='Random (0.5)')
        ax.set_xlabel('Effective Sample Size (%)', fontsize=11)
        ax.set_ylabel('Misranking Probability', fontsize=11)
        ax.set_title('Misranking Rate vs ESS\nEmpirical vs Theoretical Bound', fontsize=11)
        ax.legend(fontsize=9)
        ax.set_ylim([0, 1.05])
        ax.set_xscale('log')
        ax.grid(alpha=0.3)
        for i, r in enumerate(results):
            ax.annotate(r['beh_name'], (ess_pcts[i], emp_wis[i]),
                        textcoords='offset points', xytext=(5, 5), fontsize=7)

        # Plot 2: Bound tightness (ratio of empirical to bound)
        ax2 = axes[1]
        tightness_wis = emp_wis / (bound_is_arr + 1e-10)
        tightness_por = emp_por / (bound_por_arr + 1e-10)
        x = np.arange(len(results))
        width = 0.35
        ax2.bar(x - width/2, tightness_wis, width, label='WIS bound tightness',
                color='#e74c3c', alpha=0.8)
        ax2.bar(x + width/2, tightness_por, width, label='PoR bound tightness',
                color='#27ae60', alpha=0.8)
        ax2.axhline(1.0, color='black', linestyle='--', linewidth=1.5, label='Bound = Empirical')
        ax2.set_ylabel('Empirical Rate / Theoretical Bound\n(< 1 means bound holds)', fontsize=10)
        ax2.set_title('Bound Tightness Verification\n(All bars < 1 validates theorems)', fontsize=11)
        ax2.set_xticks(x)
        ax2.set_xticklabels(behavior_names, fontsize=8, rotation=30)
        ax2.legend(fontsize=9)
        ax2.set_ylim([0, 1.5])
        ax2.grid(axis='y', alpha=0.3)

        plt.suptitle(
            f'Experiment 7: Theoretical Misranking Bound Validation\n'
            f'True gap Δ={delta:.3f} | True PoR(A,B)={true_por:.3f} | '
            f'N={N_TRAJ} traj, {N_TRIALS} Monte Carlo trials',
            fontsize=12, fontweight='bold'
        )
        plt.tight_layout()

        outpath = logger.exp_dir / "bound_validation.png"
        plt.savefig(outpath, dpi=200, bbox_inches='tight')
        plt.close()
        logger.info("VIZ", f"Saved: {outpath}")

        # ===== SUMMARY =====
        logger.section("Experiment Summary")

        bound_violations_wis = sum(1 for r in results if r['empirical_wis_mr'] > r['bound_is'])
        bound_violations_por = sum(1 for r in results if r['empirical_por_mr'] > r['bound_por'])

        logger.info("SUMMARY", f"True performance gap: {delta:.4f}")
        logger.info("SUMMARY", f"True PoR margin: {por_margin:.4f}")
        logger.info("SUMMARY", f"WIS bound violations: {bound_violations_wis}/{len(results)}")
        logger.info("SUMMARY", f"PoR bound violations: {bound_violations_por}/{len(results)}")
        logger.info("SUMMARY", "Result table (ESS% | WIS_mr | WIS_bound | PoR_mr | PoR_bound):")
        for r in results:
            logger.info("SUMMARY",
                f"  {r['beh_name']:8s}: ESS={r['mean_ess']*100:5.2f}% | "
                f"WIS: {r['empirical_wis_mr']:.3f}/{r['bound_is']:.3f} | "
                f"PoR: {r['empirical_por_mr']:.3f}/{r['bound_por']:.3f}")

        final_data = {
            "config": {"env": "Gridworld 5x5", "N_traj": N_TRAJ,
                       "N_trials": N_TRIALS, "gamma": gamma, "C": C},
            "true_gap_delta": float(delta),
            "true_por": float(true_por),
            "por_margin": float(por_margin),
            "results": results,
            "bound_violations_wis": int(bound_violations_wis),
            "bound_violations_por": int(bound_violations_por),
        }
        logger.data("experiment_results", final_data, "Bound validation results")
        logger.save()
        logger.success(f"Experiment 7 complete! Results in {logger.exp_dir}")

    except Exception as e:
        logger.error(f"Experiment failed: {str(e)}")
        import traceback
        logger.section("ERROR TRACEBACK")
        logger._log(traceback.format_exc())
        logger.save()
        raise


if __name__ == "__main__":
    main()
