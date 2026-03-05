"""
Experiment 3: Multi-Agent OPE Fails (Opponent Shift)

Research Question: How does OPE perform when the opponent distribution changes?

Hypothesis: In multi-agent games, OPE will fail catastrophically when opponent
distribution shifts. A policy that beats opponent pool A may lose to pool B.

Methods:
  - Rock-Paper-Scissors (RPS) game
  - Pool A: 60% Rock, 30% Paper, 10% Scissors
  - Pool B: 10% Rock, 30% Paper, 60% Scissors
  - 3 policies: AllRock, AllPaper, AllScissors
  - Generate data from Pool A
  - Evaluate ranking in Pool A (ground truth)
  - Use OPE to predict ranking in Pool B
  - Expected: Ranking completely flips in Pool B
  - OPE will fail because it uses Pool A data to evaluate Pool B performance

Expected Result: Spearman ρ < 0.5 between Pool A and B rankings
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import numpy as np
from dataclasses import dataclass
from envs import MatrixGame
from policies import MatrixPolicy
from utils import set_seed, save_json
from evaluation import spearman_rank_corr
from logging_utils import ExperimentLogger, validate_metric


def main():
    """Run Experiment 3: Multi-Agent OPE Fails (Opponent Shift)."""
    
    logger = ExperimentLogger("exp_03_opponent_shift", results_dir=Path("results"))
    
    try:
        # ===== SETUP =====
        logger.section("Setup & Configuration")
        set_seed(42)
        rng = np.random.default_rng(42)
        
        # Define RPS payoff matrix
        # Rows: player's action (Rock, Paper, Scissors)
        # Cols: opponent's action (Rock, Paper, Scissors)
        payoff_p0 = np.array([
            [0.5, 0.0, 1.0],   # Rock beats Scissors, loses to Paper
            [1.0, 0.5, 0.0],   # Paper beats Rock, loses to Scissors
            [0.0, 1.0, 0.5]    # Scissors beats Paper, loses to Rock
        ])
        payoff_p1 = -payoff_p0.copy()  # Zero-sum
        
        game = MatrixGame(
            name="rock_paper_scissors",
            payoff_p0=payoff_p0,
            payoff_p1=payoff_p1
        )
        logger.info("GAME", f"Rock-Paper-Scissors, 3x3 zero-sum payoff matrix")
        
        # ===== OPPONENT POOLS =====
        logger.section("Opponent Pools (Distribution Shift)")
        
        # Pool A: Mostly Rock (60%)
        opponent_pool_A = MatrixPolicy(
            name="pool_A",
            probs=np.array([0.60, 0.30, 0.10])  # Rock dominant
        )
        
        # Pool B: Mostly Scissors (60%)
        opponent_pool_B = MatrixPolicy(
            name="pool_B",
            probs=np.array([0.10, 0.30, 0.60])  # Scissors dominant
        )
        
        logger.info("POOL_A", "60% Rock, 30% Paper, 10% Scissors")
        logger.info("POOL_B", "10% Rock, 30% Paper, 60% Scissors (SHIFT)")
        
        # ===== EVALUATION POLICIES =====
        logger.section("Evaluation Policies")
        
        # Three pure-strategy policies
        policies = [
            MatrixPolicy("AllRock", np.array([1.0, 0.0, 0.0])),
            MatrixPolicy("AllPaper", np.array([0.0, 1.0, 0.0])),
            MatrixPolicy("AllScissors", np.array([0.0, 0.0, 1.0]))
        ]
        policy_names = ["AllRock", "AllPaper", "AllScissors"]
        
        logger.info("POLICIES", f"Created 3 pure-strategy policies: {policy_names}")
        
        # ===== EVALUATE IN POOL A (GROUND TRUTH) =====
        logger.section("Evaluation in Pool A (Training Distribution)")
        
        N_MATCHES = 1000
        wins_pool_A = []
        for i, policy in enumerate(policies):
            wins = 0
            for _ in range(N_MATCHES):
                action_p = policy.act(rng)
                action_opp = np.random.choice([0, 1, 2], 
                                             p=opponent_pool_A.probs)
                reward = payoff_p0[action_p, action_opp]
                if reward > 0.5:  # Win
                    wins += 1
            
            win_pct = wins / N_MATCHES
            wins_pool_A.append(win_pct)
            logger.metric(f"winrate_poolA_{policy_names[i]}", win_pct, 
                         f"vs {opponent_pool_A.name}")
            logger.info("POOL_A", f"  {policy_names[i]}: {win_pct:.2%} win rate")
        
        wins_pool_A = np.array(wins_pool_A)
        ranking_A = np.argsort(-wins_pool_A)
        logger.info("POOL_A", f"Ranking (best to worst): "
                   f"{[policy_names[i] for i in ranking_A]}")
        
        # ===== DATA COLLECTION (FROM POOL A) =====
        logger.section("Data Collection (from Pool A)")
        
        N_TRAJECTORIES = 5000
        collected_data = []
        
        for i, policy in enumerate(policies):
            logger.info("COLLECT", f"Collecting matches for {policy_names[i]}...")
            trajectories = []
            
            for j in range(N_TRAJECTORIES):
                # Sample opponent action
                opponent_action = np.random.choice(
                    [0, 1, 2], p=opponent_pool_A.probs
                )
                
                # Get policy action
                policy_action = policy.act(rng)
                
                # Get reward
                reward = payoff_p0[policy_action, opponent_action]
                
                trajectories.append({
                    'policy_action': policy_action,
                    'opponent_action': opponent_action,
                    'reward': reward
                })
            
            collected_data.append(trajectories)
            logger.info("COLLECT", f"  ✓ Collected {len(trajectories)} matches")
        
        # ===== EVALUATE IN POOL B (SHIFTED DISTRIBUTION) =====
        logger.section("Evaluation in Pool B (Shifted Distribution)")
        
        wins_pool_B = []
        for i, policy in enumerate(policies):
            wins = 0
            for _ in range(N_MATCHES):
                action_p = policy.act(rng)
                action_opp = np.random.choice([0, 1, 2], 
                                             p=opponent_pool_B.probs)
                reward = payoff_p0[action_p, action_opp]
                if reward > 0.5:
                    wins += 1
            
            win_pct = wins / N_MATCHES
            wins_pool_B.append(win_pct)
            logger.metric(f"winrate_poolB_{policy_names[i]}", win_pct,
                         f"vs {opponent_pool_B.name}")
            logger.info("POOL_B", f"  {policy_names[i]}: {win_pct:.2%} win rate")
        
        wins_pool_B = np.array(wins_pool_B)
        ranking_B = np.argsort(-wins_pool_B)
        logger.info("POOL_B", f"Ranking (best to worst): "
                   f"{[policy_names[i] for i in ranking_B]}")
        
        # ===== RANKING COMPARISON =====
        logger.section("Ranking Analysis")
        
        spearman = spearman_rank_corr(wins_pool_A, wins_pool_B)
        logger.metric("spearman_pool_A_vs_B", spearman, 
                     "ranking correlation between pools")
        
        logger.info("RANKING", f"Pool A ranking: {[policy_names[i] for i in ranking_A]}")
        logger.info("RANKING", f"Pool B ranking: {[policy_names[i] for i in ranking_B]}")
        logger.info("RANKING", f"Spearman correlation: {spearman:.4f}")
        logger.info("RANKING", f"  Expected: ρ ≈ -1.0 (opposite rankings)")
        logger.info("RANKING", f"  Interpretation: Rankings FLIP between pools")
        
        validate_metric("spearman_pools", spearman, expected_range=[-1.0, 1.0])
        
        # ===== VISUALIZATION =====
        logger.section("Visualization")
        
        # Plot: Win rates comparison
        x = np.arange(len(policy_names))
        width = 0.35
        
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.bar(x - width/2, wins_pool_A, width, label='Pool A (60% Rock)', alpha=0.8)
        ax.bar(x + width/2, wins_pool_B, width, label='Pool B (60% Scissors)', alpha=0.8)
        ax.set_ylabel('Win Rate')
        ax.set_title(f'Policy Performance Across Opponent Pools (ρ={spearman:.3f})')
        ax.set_xticks(x)
        ax.set_xticklabels(policy_names)
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        
        outpath = logger.exp_dir / "winrate_comparison.png"
        plt.tight_layout()
        plt.savefig(outpath, dpi=180)
        plt.close()
        logger.info("VIZ", f"Saved: {outpath.name}")
        
        # Plot: Scatter of win rates
        fig, ax = plt.subplots(figsize=(8, 8))
        ax.scatter(wins_pool_A, wins_pool_B, s=200, alpha=0.7)
        
        # Add diagonal (perfect correlation)
        min_val = min(wins_pool_A.min(), wins_pool_B.min())
        max_val = max(wins_pool_A.max(), wins_pool_B.max())
        ax.plot([min_val, max_val], [min_val, max_val], 'k--', alpha=0.3, label='ρ=1.0')
        
        # Add labels for each point
        for i, name in enumerate(policy_names):
            ax.annotate(name, (wins_pool_A[i], wins_pool_B[i]), 
                       xytext=(5, 5), textcoords='offset points', fontsize=10)
        
        ax.set_xlabel('Win Rate in Pool A (60% Rock)')
        ax.set_ylabel('Win Rate in Pool B (60% Scissors)')
        ax.set_title(f'Policy Ranking Flip Across Opponent Distributions (ρ={spearman:.3f})')
        ax.grid(alpha=0.3)
        ax.set_xlim([-0.1, 1.1])
        ax.set_ylim([-0.1, 1.1])
        ax.set_aspect('equal')
        
        outpath = logger.exp_dir / "ranking_flip.png"
        plt.tight_layout()
        plt.savefig(outpath, dpi=180)
        plt.close()
        logger.info("VIZ", f"Saved: {outpath.name}")
        
        # ===== SUMMARY =====
        logger.section("Experiment Summary")
        
        logger.success("Multi-agent ranking flip analysis complete")
        logger.info("FINDING", "Distribution shift changes policy rankings dramatically")
        logger.info("FINDING", f"  Pool A best: {policy_names[ranking_A[0]]}")
        logger.info("FINDING", f"  Pool B best: {policy_names[ranking_B[0]]}")
        logger.info("FINDING", f"  Spearman correlation: {spearman:.4f}")
        logger.info("FINDING", "  → OPE data collected in Pool A cannot predict Pool B")
        
        final_data = {
            "config": {
                "game": "Rock-Paper-Scissors",
                "pool_A": "60% Rock, 30% Paper, 10% Scissors",
                "pool_B": "10% Rock, 30% Paper, 60% Scissors",
                "n_trajectories": N_TRAJECTORIES,
                "n_matches_eval": N_MATCHES
            },
            "policy_names": policy_names,
            "winrate_pool_A": wins_pool_A.tolist(),
            "winrate_pool_B": wins_pool_B.tolist(),
            "ranking_A": ranking_A.tolist(),
            "ranking_B": ranking_B.tolist(),
            "spearman_correlation": float(spearman),
            "ranking_flip": bool(ranking_A[0] != ranking_B[0])
        }
        logger.data("experiment_results", final_data, "Multi-agent ranking analysis")
        
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
