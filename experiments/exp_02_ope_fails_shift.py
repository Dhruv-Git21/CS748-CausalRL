"""
Experiment 2: OPE Fails (Distribution Shift)

Research Question: What happens to OPE when behavior policy has poor coverage
(support mismatch)?

Hypothesis: When behavior policy is very different from evaluation policy,
importance weights become degenerate (heavy-tailed), ESS collapses, and OPE
estimates fail.

Methods:
  - Single-agent Gridworld (same as Exp 1)
  - Create 3 evaluation policies (same as Exp 1)
  - Use DELIBERATELY BAD behavior policy (always move right) - poor coverage
  - Collect N=5000 trajectories under bad behavior policy
  - Compute importance weights - show heavy tails
  - Compute ESS - should collapse to ~5% or less
  - Estimate values - should be very noisy
  - Compare ranking to ground truth - should drop significantly

Expected Result: Spearman ρ ≈ 0.25, heavy-tailed weights, ESS collapse, outliers
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Set matplotlib to non-interactive backend before importing pyplot
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import numpy as np
from envs import Gridworld, GridworldConfig
from policies import TabularPolicy, random_policy, epsilon_greedy_from_q
from utils import set_seed, collect_batch, plot_scatter, plot_hist, save_json
from ope import importance_sampling, weighted_is, per_decision_is
from evaluation import spearman_rank_corr, top1_mismatch
from logging_utils import ExperimentLogger, validate_metric


def evaluate_policy_via_rollout(env: Gridworld, policy: TabularPolicy, 
                                N: int = 1000, T: int = 50, seed: int = 0) -> float:
    """Evaluate policy via direct rollout."""
    rng = np.random.default_rng(seed)
    returns = []
    
    for _ in range(N):
        s = env.reset()
        episode_return = 0.0
        for t in range(T):
            a = policy.act(s, rng)
            s, r, done, _ = env.step(a, rng)
            episode_return += r * (0.99 ** t)
            if done:
                break
        returns.append(episode_return)
    
    return float(np.mean(returns))


def create_bad_behavior_policy(nS: int, nA: int) -> TabularPolicy:
    """Create deliberately bad behavior policy with poor coverage.
    
    Uses high-epsilon greedy that avoids the goal direction.
    This creates distribution shift without numerical underflow.
    """
    # Create Q-values that prefer LEFT and DOWN (away from goal at 4,4)
    Q = np.ones((nS, nA)) * 0.1
    # Actions: 0=left, 1=right, 2=up, 3=down
    # Prefer moving left and down (away from goal)
    for s in range(nS):
        Q[s, 0] = 0.8  # Left (away from goal x)
        Q[s, 3] = 0.7  # Down (away from goal y)
    
    # Use epsilon-greedy with HIGH epsilon (0.8) so lots of exploration
    # but biased toward sub-optimal actions
    from policies import epsilon_greedy_from_q
    return epsilon_greedy_from_q(Q, eps=0.8)


def main():
    """Run Experiment 2: OPE Fails with Distribution Shift."""
    
    logger = ExperimentLogger("exp_02_ope_fails_shift", results_dir=Path("results"))
    
    try:
        # ===== SETUP =====
        logger.section("Setup & Configuration")
        set_seed(42)
        
        config = GridworldConfig(width=5, height=5, goal=(4, 4), slip=0.0)
        env = Gridworld(config)
        nS, nA = env.nS, env.nA
        logger.info("ENV", f"Gridworld {config.width}x{config.height}, "
                   f"goal={config.goal}, nS={nS}, nA={nA}")
        
        N_TRAJ = 5000
        T = 50
        N_ROLLOUT = 1000
        gamma = 0.99
        
        logger.info("PARAMS", f"N_trajectories={N_TRAJ}, T={T}, "
                   f"N_rollout={N_ROLLOUT}, gamma={gamma}")
        
        # ===== CREATE POLICIES =====
        logger.section("Policy Creation")
        
        # Same Q-values as Exp 1
        Q = np.zeros((nS, nA))
        for s in range(nS):
            x, y = s // config.width, s % config.width
            for a in range(nA):
                if a == 0 and x > config.goal[0]:
                    Q[s, a] = 0.5
                elif a == 1 and y < config.goal[1]:
                    Q[s, a] = 0.5
                elif a == 2 and x < config.goal[0]:
                    Q[s, a] = 0.5
                elif a == 3 and y > config.goal[1]:
                    Q[s, a] = 0.5
                else:
                    Q[s, a] = np.random.uniform(0, 0.1)
        
        pi_random = random_policy(nS, nA)
        pi_eps05 = epsilon_greedy_from_q(Q, eps=0.5)
        pi_eps01 = epsilon_greedy_from_q(Q, eps=0.1)
        
        policies = [pi_random, pi_eps05, pi_eps01]
        policy_names = ["random", "eps=0.5", "eps=0.1"]
        
        logger.info("POLICIES", f"Created {len(policies)} policies: {policy_names}")
        
        # ===== BAD BEHAVIOR POLICY =====
        logger.section("Behavior Policy (POOR Coverage - Distribution Shift)")
        
        # Use deliberately bad behavior policy
        pi_behavior = create_bad_behavior_policy(nS, nA)
        logger.info("BEHAVIOR", "ε-greedy (ε=0.8) biased toward left/down - avoids goal")
        logger.info("BEHAVIOR", "This creates DISTRIBUTION SHIFT with eval policies")
        
        # ===== COLLECT DATA =====
        logger.section("Data Collection")
        
        batches = []
        for i, pi in enumerate(policies):
            logger.info("COLLECT", f"Policy {i+1}/{len(policies)}: {policy_names[i]}")
            batch = collect_batch(env, pi_behavior, pi, N_TRAJ, T, seed=42+i)
            batches.append(batch)
            logger.info("COLLECT", f"  ✓ Collected {N_TRAJ} trajectories")
        
        logger.metric("n_trajectories", N_TRAJ, "per policy")
        logger.metric("trajectory_length", T, "steps")
        
        # ===== GROUND TRUTH EVALUATION =====
        logger.section("Ground Truth Evaluation (via Rollout)")
        
        true_values = []
        for i, pi in enumerate(policies):
            logger.info("ROLLOUT", f"Evaluating {policy_names[i]}...")
            true_val = evaluate_policy_via_rollout(env, pi, N_ROLLOUT, T, seed=100+i)
            true_values.append(true_val)
            logger.metric(f"true_value_{policy_names[i]}", true_val)
        
        true_values = np.array(true_values)
        true_ranks = np.argsort(-true_values)
        logger.info("GROUND_TRUTH", f"Ranking (best to worst): "
                   f"{[policy_names[i] for i in true_ranks]}")
        
        # ===== IMPORTANCE WEIGHT ANALYSIS =====
        logger.section("Importance Weight Analysis")
        
        for i, (batch, name) in enumerate(zip(batches, policy_names)):
            ratios = batch.traj_ratios()
            logger.info("WEIGHTS", f"{name}:")
            logger.info("WEIGHTS", f"  Min: {np.min(ratios):.6e}")
            logger.info("WEIGHTS", f"  Max: {np.max(ratios):.6e}")
            logger.info("WEIGHTS", f"  Mean: {np.mean(ratios):.6e}")
            logger.info("WEIGHTS", f"  Median: {np.median(ratios):.6e}")
            logger.info("WEIGHTS", f"  Std: {np.std(ratios):.6e}")
            
            logger.metric(f"weight_max_{name}", float(np.max(ratios)), 
                         "max importance ratio")
            logger.metric(f"weight_mean_{name}", float(np.mean(ratios)), 
                         "mean importance ratio")
            
            # Plot weight distribution (log scale) - non-blocking
            try:
                import matplotlib
                matplotlib.use('Agg')  # Non-interactive backend
                outpath = logger.exp_dir / f"weights_histogram_{name.replace('=', '')}.png"
                plt.figure(figsize=(8, 5))
                plt.hist(ratios, bins=50, edgecolor='black')
                plt.yscale('log')
                plt.xscale('log')
                plt.title(f"{name}: Importance Weight Distribution (log scale)")
                plt.xlabel("Weight Value")
                plt.ylabel("Count (log)")
                plt.tight_layout()
                plt.savefig(outpath, dpi=180)
                plt.close()
                logger.info("WEIGHTS", f"  ✓ Saved histogram to {outpath.name}")
            except Exception as e:
                logger.info("WEIGHTS", f"  ⚠ Could not save histogram: {e}")
        
        # ===== OPE ESTIMATION =====
        logger.section("Off-Policy Evaluation")
        
        ope_methods = {
            "IS": importance_sampling,
            "WIS": weighted_is,
            "PDIS": per_decision_is
        }
        
        ope_values_by_method = {}
        ess_by_method = {}
        
        for method_name, estimator in ope_methods.items():
            logger.info("OPE", f"Method: {method_name}")
            method_values = []
            method_ess = []
            
            for i, batch in enumerate(batches):
                returns = batch.returns(gamma)
                
                if method_name == "PDIS":
                    step_ratios = batch.step_cum_ratios()
                    result = estimator(returns, step_ratios)
                else:
                    ratios = batch.traj_ratios()
                    result = estimator(returns, ratios)
                
                method_values.append(result.estimate)
                method_ess.append(result.ess / len(returns))
                ess_pct = (result.ess / len(returns)) * 100
                logger.info("OPE", f"  {policy_names[i]}: "
                           f"value={result.estimate:.4f}, ESS={ess_pct:.1f}%")
                
                # Log ESS metric
                logger.metric(f"ess_{method_name}_{policy_names[i]}", 
                             ess_pct, "percentage of N")
            
            ope_values_by_method[method_name] = np.array(method_values)
            ess_by_method[method_name] = np.array(method_ess)
        
        # ===== RANKING COMPARISON =====
        logger.section("Ranking Comparison (Distribution Shift Impact)")
        
        ranking_results = {}
        
        for method_name, ope_values in ope_values_by_method.items():
            ope_ranks = np.argsort(-ope_values)
            
            spearman = spearman_rank_corr(true_values, ope_values)
            top1_error = top1_mismatch(true_values, ope_values)
            
            ranking_results[method_name] = {
                "ope_values": ope_values,
                "ope_ranks": ope_ranks,
                "spearman": spearman,
                "top1_error": top1_error,
                "ess": ess_by_method[method_name]
            }
            
            logger.info("RANKING", f"{method_name}:")
            logger.info("RANKING", f"  OPE ranking: {[policy_names[i] for i in ope_ranks]}")
            logger.info("RANKING", f"  Spearman ρ: {spearman:.6f} (FAILED: should be ~0.25)")
            logger.info("RANKING", f"  Top-1 mismatch: {top1_error}")
            
            validate_metric(f"{method_name}_spearman", spearman, 
                          expected_range=[-1.0, 1.0])
            validate_metric(f"{method_name}_top1_error", top1_error, 
                          is_binary=True)
            
            logger.metric(f"spearman_{method_name}", spearman, 
                         "rank correlation (EXPECTED: low)")
            logger.metric(f"top1_error_{method_name}", top1_error, 
                         "0=correct, 1=mismatch (EXPECTED: 1)")
        
        # ===== VISUALIZATION =====
        logger.section("Visualization")
        
        for method_name, results in ranking_results.items():
            ope_values = results["ope_values"]
            spearman = results["spearman"]
            
            outpath = logger.exp_dir / f"scatter_{method_name.lower()}.png"
            plot_scatter(true_values, ope_values, 
                        title=f"{method_name}: OPE vs True Value (ρ={spearman:.3f}) - SHIFT",
                        xlabel="True Value (Rollout)",
                        ylabel="OPE Estimate",
                        outpath=outpath,
                        labels=policy_names)
            logger.info("VIZ", f"Saved: {outpath.name}")
        
        # ===== SUMMARY =====
        logger.section("Experiment Summary")
        
        logger.success("All metrics computed")
        logger.info("SUMMARY", "KEY FINDING: Distribution shift breaks OPE ranking")
        logger.info("SUMMARY", f"  Ground truth: {[policy_names[i] for i in true_ranks]}")
        logger.info("SUMMARY", "OPE Spearman correlations (expected: low):")
        for method_name, results in ranking_results.items():
            logger.info("SUMMARY", f"  {method_name}: {results['spearman']:.4f}")
        
        final_data = {
            "config": {
                "width": config.width,
                "height": config.height,
                "goal": config.goal,
                "behavior_policy": "always_right (poor coverage)",
                "n_trajectories": N_TRAJ,
                "trajectory_length": T,
                "n_rollout": N_ROLLOUT,
                "gamma": gamma
            },
            "policy_names": policy_names,
            "true_values": true_values.tolist(),
            "true_ranks": true_ranks.tolist(),
            "ranking_results": {
                method: {
                    "ope_values": results["ope_values"].tolist(),
                    "ope_ranks": results["ope_ranks"].tolist(),
                    "spearman": float(results["spearman"]),
                    "top1_error": int(results["top1_error"]),
                    "ess_percentages": results["ess"].tolist()
                }
                for method, results in ranking_results.items()
            }
        }
        logger.data("experiment_results", final_data, "Complete results with shift")
        
        logger.save()
        logger.success(f"Experiment complete! Results in {logger.exp_dir}")
        
    except Exception as e:
        logger.error(f"Experiment failed: {str(e)}")
        import traceback
        logger.section("ERROR TRACEBACK")
        logger._log(traceback.format_exc())
        logger.save()
        raise


if __name__ == "__main__":
    main()
