"""
Experiment 1: OPE Works (Good Coverage)

Research Question: Does OPE ranking correlate with true rollout ranking when 
the behavior policy has good coverage?

Hypothesis: When behavior policy approximates evaluation policy distribution,
IS/WIS estimates should rank policies correctly.

Methods:
  - Single-agent Gridworld (5x5, goal at corner)
  - Create 3 policies: random, ε-greedy (ε=0.5), ε-greedy (ε=0.1)
  - Collect N=5000 trajectories under "good" behavior policy
  - Estimate value of each policy using IS, WIS, PDIS
  - Compare OPE ranking vs. ground truth rollout ranking
  - Compute Spearman rank correlation

Expected Result: Spearman ρ ≈ 0.9+, tight scatter, Top-1 match
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
import matplotlib.pyplot as plt
from envs import Gridworld, GridworldConfig
from policies import TabularPolicy, random_policy, epsilon_greedy_from_q
from utils import set_seed, collect_batch, plot_scatter, plot_hist, save_json
from ope import importance_sampling, weighted_is, per_decision_is
from evaluation import spearman_rank_corr, top1_mismatch
from logging_utils import ExperimentLogger, validate_metric


def evaluate_policy_via_rollout(env: Gridworld, policy: TabularPolicy, 
                                N: int = 1000, T: int = 50, seed: int = 0) -> float:
    """Evaluate policy via direct rollout.
    
    Args:
        env: Environment
        policy: Policy to evaluate
        N: Number of trajectories
        T: Trajectory length
        seed: Random seed
        
    Returns:
        Average return
    """
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


def main():
    """Run Experiment 1: OPE Works with Good Coverage."""
    
    logger = ExperimentLogger("exp_01_ope_works", results_dir=Path("results"))
    
    try:
        # ===== SETUP =====
        logger.section("Setup & Configuration")
        set_seed(42)
        
        # Environment config
        config = GridworldConfig(width=5, height=5, goal=(4, 4), slip=0.0)
        env = Gridworld(config)
        nS, nA = env.nS, env.nA
        logger.info("ENV", f"Gridworld {config.width}x{config.height}, "
                   f"goal={config.goal}, nS={nS}, nA={nA}")
        
        # Parameters
        N_TRAJ = 5000  # trajectories for OPE
        T = 50  # trajectory length
        N_ROLLOUT = 1000  # trajectories for true value
        gamma = 0.99
        
        logger.info("PARAMS", f"N_trajectories={N_TRAJ}, T={T}, "
                   f"N_rollout={N_ROLLOUT}, gamma={gamma}")
        
        # ===== CREATE POLICIES =====
        logger.section("Policy Creation")
        
        # Create Q-values for epsilon-greedy policies
        # Use a simple approximation: reward for moving towards goal
        Q = np.zeros((nS, nA))
        for s in range(nS):
            x, y = s // config.width, s % config.width
            # Reward for moving towards goal
            for a in range(nA):
                if a == 0 and x > config.goal[0]:  # up towards goal
                    Q[s, a] = 0.5
                elif a == 1 and y < config.goal[1]:  # right towards goal
                    Q[s, a] = 0.5
                elif a == 2 and x < config.goal[0]:  # down towards goal
                    Q[s, a] = 0.5
                elif a == 3 and y > config.goal[1]:  # left towards goal
                    Q[s, a] = 0.5
                else:
                    Q[s, a] = np.random.uniform(0, 0.1)
        
        # Create policies
        pi_random = random_policy(nS, nA)
        pi_eps05 = epsilon_greedy_from_q(Q, eps=0.5)
        pi_eps01 = epsilon_greedy_from_q(Q, eps=0.1)
        
        policies = [pi_random, pi_eps05, pi_eps01]
        policy_names = ["random", "eps=0.5", "eps=0.1"]
        
        logger.info("POLICIES", f"Created {len(policies)} policies: {policy_names}")
        
        # ===== BEHAVIOR POLICY =====
        logger.section("Behavior Policy (Good Coverage)")
        
        # Use epsilon-greedy as behavior (good coverage)
        pi_behavior = epsilon_greedy_from_q(Q, eps=0.3)
        logger.info("BEHAVIOR", "eps-greedy with eps=0.3 (good coverage)")
        
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
        true_ranks = np.argsort(-true_values)  # descending order
        logger.info("GROUND_TRUTH", f"Ranking (best to worst): "
                   f"{[policy_names[i] for i in true_ranks]}")
        
        # ===== OPE ESTIMATION =====
        logger.section("Off-Policy Evaluation")
        
        ope_methods = {
            "IS": importance_sampling,
            "WIS": weighted_is,
            "PDIS": per_decision_is
        }
        
        ope_values_by_method = {}
        
        for method_name, estimator in ope_methods.items():
            logger.info("OPE", f"Method: {method_name}")
            method_values = []
            
            for i, batch in enumerate(batches):
                returns = batch.returns(gamma)
                
                if method_name == "PDIS":
                    step_ratios = batch.step_cum_ratios()
                    result = estimator(returns, step_ratios)
                else:
                    ratios = batch.traj_ratios()
                    result = estimator(returns, ratios)
                
                method_values.append(result.estimate)
                ess_pct = (result.ess / len(returns)) * 100
                logger.info("OPE", f"  {policy_names[i]}: "
                           f"value={result.estimate:.4f}, ESS={ess_pct:.1f}%")
            
            ope_values_by_method[method_name] = np.array(method_values)
        
        # ===== RANKING COMPARISON =====
        logger.section("Ranking Comparison")
        
        ranking_results = {}
        
        for method_name, ope_values in ope_values_by_method.items():
            ope_ranks = np.argsort(-ope_values)  # descending order
            
            # Compute metrics
            spearman = spearman_rank_corr(true_values, ope_values)
            top1_error = top1_mismatch(true_values, ope_values)
            
            ranking_results[method_name] = {
                "ope_values": ope_values,
                "ope_ranks": ope_ranks,
                "spearman": spearman,
                "top1_error": top1_error
            }
            
            logger.info("RANKING", f"{method_name}:")
            logger.info("RANKING", f"  OPE ranking: {[policy_names[i] for i in ope_ranks]}")
            logger.info("RANKING", f"  Spearman ρ: {spearman:.6f}")
            logger.info("RANKING", f"  Top-1 mismatch: {top1_error}")
            
            # Validate metrics
            validate_metric(f"{method_name}_spearman", spearman, 
                          expected_range=[-1.0, 1.0])
            validate_metric(f"{method_name}_top1_error", top1_error, 
                          is_binary=True)
            
            logger.metric(f"spearman_{method_name}", spearman, 
                         "rank correlation")
            logger.metric(f"top1_error_{method_name}", top1_error, 
                         "0=correct, 1=mismatch")
        
        # ===== VISUALIZATION =====
        logger.section("Visualization")
        
        for method_name, results in ranking_results.items():
            ope_values = results["ope_values"]
            spearman = results["spearman"]
            
            # Scatter plot: OPE vs True value
            outpath = logger.exp_dir / f"scatter_{method_name.lower()}.png"
            plot_scatter(true_values, ope_values, 
                        title=f"{method_name}: OPE vs True Value (ρ={spearman:.3f})",
                        xlabel="True Value (Rollout)",
                        ylabel="OPE Estimate",
                        outpath=outpath,
                        labels=policy_names)
            logger.info("VIZ", f"Saved: {outpath.name}")
        
        # ===== SUMMARY =====
        logger.section("Experiment Summary")
        
        logger.success("All metrics computed successfully")
        logger.info("SUMMARY", f"Ground truth ranking: {[policy_names[i] for i in true_ranks]}")
        logger.info("SUMMARY", "OPE Spearman correlations:")
        for method_name, results in ranking_results.items():
            logger.info("SUMMARY", f"  {method_name}: {results['spearman']:.4f}")
        
        # Store final data
        final_data = {
            "config": {
                "width": config.width,
                "height": config.height,
                "goal": config.goal,
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
                    "top1_error": int(results["top1_error"])
                }
                for method, results in ranking_results.items()
            }
        }
        logger.data("experiment_results", final_data, "Complete results")
        
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
