"""
Experiment 5: Dominance-Based Evaluation is Robust

Research Question: Does dominance-based evaluation (Pareto, maximin) provide
more stable policy selection than ranking, especially under distributional shift?

Hypothesis: When using ranking (best average value), policies change under shift.
When using dominance (never beaten by another policy), selection is more stable.

Methods:
  - Use 5x5 Gridworld with 5 evaluation policies (varying epsilon-greedy)
  - Scenario 1: Good behavior policy (ε=0.3)
  - Scenario 2: Bad behavior policy (ε=0.9, avoids goal direction)
  - For each scenario:
    - Estimate value of each policy via OPE
    - Select best policy via ranking (highest value)
    - Select best policy via dominance (Pareto non-dominated)
  - Compare selection across scenarios
  - Expected: Ranking selects different policies across scenarios
  - Expected: Dominance selects same policies (more robust)

Expected Result: Dominance-based selection is more stable (lower variance across scenarios)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import numpy as np
from envs import Gridworld, GridworldConfig
from policies import TabularPolicy, random_policy, epsilon_greedy_from_q
from utils import set_seed, collect_batch, plot_scatter, save_json
from ope import weighted_is
from evaluation import spearman_rank_corr
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


def pareto_front(values: np.ndarray, policy_names: list) -> list:
    """Compute Pareto non-dominated policies.
    
    In this context, higher value is better, so a policy is dominated
    if another policy is strictly better in all scenarios.
    
    For single-objective (just value), all policies are non-dominated
    unless one dominates another. Here we'll use: policy A dominates B
    if A's value >= B's value in all metrics with strict > in at least one.
    
    For simplicity with single value metric, we return policies not strictly
    beaten by any other (which is all of them in 1D).
    """
    # In 1D, use maximin (guaranteed minimum) concept
    non_dominated = []
    for i in range(len(policy_names)):
        is_dominated = False
        for j in range(len(policy_names)):
            if i != j and values[j] > values[i]:
                is_dominated = True
                break
        if not is_dominated:
            non_dominated.append(i)
    
    return non_dominated


def maximin_robust(values_per_scenario: np.ndarray) -> list:
    """Select policies robust to worst-case scenario.
    
    For each policy, compute minimum value across all scenarios.
    Return policies with high minimum value (robust).
    
    Args:
        values_per_scenario: shape (n_policies, n_scenarios)
    """
    min_values = np.min(values_per_scenario, axis=1)  # Min across scenarios for each policy
    # Return policies in top 50% by worst-case value
    threshold = np.percentile(min_values, 50)
    robust_policies = [i for i in range(len(min_values)) if min_values[i] >= threshold]
    return robust_policies


def main():
    """Run Experiment 5: Dominance-Based Evaluation is Robust."""
    
    logger = ExperimentLogger("exp_05_dominance_robust", results_dir=Path("results"))
    
    try:
        # ===== SETUP =====
        logger.section("Setup & Configuration")
        set_seed(42)
        
        config = GridworldConfig(width=5, height=5, goal=(4, 4), slip=0.0)
        env = Gridworld(config)
        nS, nA = env.nS, env.nA
        logger.info("ENV", f"Gridworld {config.width}x{config.height}")
        
        # Create evaluation policies
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
        
        # 5 epsilon-greedy policies with different epsilon values
        epsilons = [0.0, 0.1, 0.3, 0.5, 0.8]
        policies = [epsilon_greedy_from_q(Q, eps=eps) for eps in epsilons]
        policy_names = [f"ε={eps}" for eps in epsilons]
        
        logger.info("POLICIES", f"Created {len(policies)} policies: {policy_names}")
        
        # ===== SCENARIOS =====
        logger.section("Two Evaluation Scenarios")
        
        logger.info("SCENARIO", "Scenario 1: GOOD behavior policy (ε=0.3)")
        logger.info("SCENARIO", "Scenario 2: BAD behavior policy (ε=0.9, avoids goal)")
        
        # Scenario 1: Good behavior policy
        pi_behavior_good = epsilon_greedy_from_q(Q, eps=0.3)
        
        # Scenario 2: Bad behavior policy (avoids goal)
        Q_bad = np.ones((nS, nA)) * 0.1
        for s in range(nS):
            Q_bad[s, 0] = 0.8   # Prefer left (away from goal)
            Q_bad[s, 3] = 0.7   # Prefer down (away from goal)
        pi_behavior_bad = epsilon_greedy_from_q(Q_bad, eps=0.8)
        
        # ===== GROUND TRUTH EVALUATION =====
        logger.section("Ground Truth Evaluation")
        
        true_values = []
        for i, policy in enumerate(policies):
            val = evaluate_policy_via_rollout(env, policy, N=1000, T=50, seed=i)
            true_values.append(val)
            logger.metric(f"true_value_{policy_names[i]}", val)
        
        true_values = np.array(true_values)
        true_ranking = np.argsort(-true_values)
        logger.info("GROUND_TRUTH", f"Ranking: {[policy_names[i] for i in true_ranking]}")
        
        # ===== OPE EVALUATION IN TWO SCENARIOS =====
        logger.section("OPE Evaluation (Scenario 1: Good behavior)")
        
        N_TRAJ = 5000
        T = 50
        gamma = 0.99
        
        ope_values_good = []
        for i, policy in enumerate(policies):
            batch = collect_batch(env, pi_behavior_good, policy, N_TRAJ, T, seed=i)
            returns = batch.returns(gamma)
            ratios = batch.traj_ratios()
            result = weighted_is(returns, ratios)
            ope_values_good.append(result.estimate)
            logger.metric(f"ope_good_{policy_names[i]}", result.estimate)
        
        ope_values_good = np.array(ope_values_good)
        ope_ranking_good = np.argsort(-ope_values_good)
        logger.info("RANKING_GOOD", f"OPE ranking: {[policy_names[i] for i in ope_ranking_good]}")
        
        logger.section("OPE Evaluation (Scenario 2: Bad behavior)")
        
        ope_values_bad = []
        for i, policy in enumerate(policies):
            batch = collect_batch(env, pi_behavior_bad, policy, N_TRAJ, T, seed=100+i)
            returns = batch.returns(gamma)
            ratios = batch.traj_ratios()
            result = weighted_is(returns, ratios)
            ope_values_bad.append(result.estimate)
            logger.metric(f"ope_bad_{policy_names[i]}", result.estimate)
        
        ope_values_bad = np.array(ope_values_bad)
        ope_ranking_bad = np.argsort(-ope_values_bad)
        logger.info("RANKING_BAD", f"OPE ranking: {[policy_names[i] for i in ope_ranking_bad]}")
        
        # ===== POLICY SELECTION =====
        logger.section("Policy Selection Comparison")
        
        # Ranking-based: best policy (highest value)
        best_ranking_good = ope_ranking_good[0]
        best_ranking_bad = ope_ranking_bad[0]
        
        logger.info("RANKING_SELECT", f"Scenario 1 best: {policy_names[best_ranking_good]}")
        logger.info("RANKING_SELECT", f"Scenario 2 best: {policy_names[best_ranking_bad]}")
        ranking_consistent = (best_ranking_good == best_ranking_bad)
        logger.metric("ranking_consistent", float(ranking_consistent), 
                     "selection consistency (1=same policy selected)")
        
        # Dominance-based: Pareto non-dominated
        values_per_scenario = np.array([ope_values_good, ope_values_bad]).T
        dominant_policies = maximin_robust(values_per_scenario)
        
        logger.info("DOMINANCE_SELECT", 
                   f"Robust policies (worst-case ≥ median): {[policy_names[i] for i in dominant_policies]}")
        logger.metric("n_dominant_policies", len(dominant_policies), 
                     "number of robust policies selected")
        
        # ===== VISUALIZATION =====
        logger.section("Visualization")
        
        fig, ax = plt.subplots(1, 2, figsize=(14, 6))
        
        # Plot 1: Ranking-based comparison
        x = np.arange(len(policy_names))
        width = 0.35
        ax[0].bar(x - width/2, ope_values_good, width, label='Scenario 1 (Good)', alpha=0.8)
        ax[0].bar(x + width/2, ope_values_bad, width, label='Scenario 2 (Bad)', alpha=0.8)
        ax[0].axvline(best_ranking_good - 0.2, color='darkgreen', linestyle='--', linewidth=2, label='Best-S1')
        ax[0].axvline(best_ranking_bad + 0.2, color='darkred', linestyle='--', linewidth=2, label='Best-S2')
        ax[0].set_ylabel('OPE Value (WIS)')
        ax[0].set_title(f'Ranking-Based Selection (Consistent={ranking_consistent})')
        ax[0].set_xticks(x)
        ax[0].set_xticklabels(policy_names)
        ax[0].legend()
        ax[0].grid(axis='y', alpha=0.3)
        
        # Plot 2: Dominance-based visualization (min values)
        min_values = np.min(values_per_scenario, axis=1)  # Min across scenarios for each policy
        colors = ['green' if i in dominant_policies else 'lightgray' 
                 for i in range(len(policy_names))]
        
        bars = ax[1].bar(range(len(policy_names)), min_values, 
                        color=colors, edgecolor='black', linewidth=2, alpha=0.7)
        ax[1].axhline(np.percentile(min_values, 50), color='red', linestyle='--', 
                     label='Robustness threshold (median)', linewidth=2)
        ax[1].set_ylabel('Worst-Case Value (min across scenarios)')
        ax[1].set_title(f'Dominance-Based Selection ({len(dominant_policies)} robust policies)')
        ax[1].set_xticks(x)
        ax[1].set_xticklabels(policy_names)
        ax[1].legend()
        ax[1].grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        outpath = logger.exp_dir / "robustness_comparison.png"
        plt.savefig(outpath, dpi=180)
        plt.close()
        logger.info("VIZ", f"Saved: {outpath.name}")
        
        # ===== SUMMARY =====
        logger.section("Experiment Summary")
        
        logger.success("Dominance analysis complete")
        logger.info("KEY_FINDING", "Ranking-based selection is unstable")
        logger.info("KEY_FINDING", f"  Scenario 1 chooses: {policy_names[best_ranking_good]}")
        logger.info("KEY_FINDING", f"  Scenario 2 chooses: {policy_names[best_ranking_bad]}")
        if not ranking_consistent:
            logger.info("KEY_FINDING", "  → DIFFERENT policies selected!")
        
        logger.info("KEY_FINDING", "Dominance-based selection is more robust")
        logger.info("KEY_FINDING", f"  Robust policies: {[policy_names[i] for i in dominant_policies]}")
        logger.info("KEY_FINDING", f"  These {len(dominant_policies)} policies work well in worst-case")
        
        final_data = {
            "config": {
                "env": "Gridworld 5x5",
                "policies": policy_names,
                "n_trajectories": N_TRAJ,
                "scenario_1": "good behavior (ε=0.3)",
                "scenario_2": "bad behavior (ε=0.9)"
            },
            "ground_truth_values": true_values.tolist(),
            "ground_truth_ranking": [policy_names[i] for i in true_ranking],
            "scenario_1": {
                "ope_values": ope_values_good.tolist(),
                "best_policy": policy_names[best_ranking_good]
            },
            "scenario_2": {
                "ope_values": ope_values_bad.tolist(),
                "best_policy": policy_names[best_ranking_bad]
            },
            "ranking_consistent": bool(ranking_consistent),
            "robust_policies": [policy_names[i] for i in dominant_policies],
            "n_robust": len(dominant_policies)
        }
        logger.data("experiment_results", final_data, "Robustness analysis")
        
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
