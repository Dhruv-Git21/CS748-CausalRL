"""
Experiment 4: Non-Transitive Policy Rankings

Research Question: Can we have cyclic dominance where Policy A > B > C > A?

Hypothesis: In competitive multi-agent environments with non-zero-sum games or
mixed strategy equilibria, cyclic dominance is possible. This breaks any total
ordering of policies by performance.

Methods:
  - Create three custom policies for Rock-Paper-Scissors
  - Policy 1: Slight bias toward Rock (55% Rock, 25% Paper, 20% Scissors)
  - Policy 2: Slight bias toward Paper (20% Rock, 55% Paper, 25% Scissors)
  - Policy 3: Slight bias toward Scissors (25% Rock, 20% Paper, 55% Scissors)
  - Play tournament: each policy plays 1000 games against each opponent
  - Compute win rates in a round-robin tournament
  - Analyze tournament result matrix for cycles

Expected Result: A > B, B > C, C > A (cyclic ranking)
Implication: No single best policy; ranking depends on opponent
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import numpy as np
from envs import MatrixGame
from policies import MatrixPolicy
from utils import set_seed, save_json
from logging_utils import ExperimentLogger, validate_metric


def main():
    """Run Experiment 4: Non-Transitive Policy Rankings."""
    
    logger = ExperimentLogger("exp_04_nontransitivity", results_dir=Path("results"))
    
    try:
        # ===== SETUP =====
        logger.section("Setup & Configuration")
        set_seed(42)
        
        # Define Rock-Paper-Scissors payoff matrix
        payoff_p0 = np.array([
            [0.5, 0.0, 1.0],   # Rock: ties Rock, loses Paper, beats Scissors
            [1.0, 0.5, 0.0],   # Paper: beats Rock, ties Paper, loses Scissors
            [0.0, 1.0, 0.5]    # Scissors: loses Rock, beats Paper, ties Scissors
        ])
        payoff_p1 = -payoff_p0.copy()
        
        game = MatrixGame(
            name="rock_paper_scissors",
            payoff_p0=payoff_p0,
            payoff_p1=payoff_p1
        )
        logger.info("GAME", "Rock-Paper-Scissors, zero-sum game")
        
        # ===== BIASED POLICIES =====
        logger.section("Policy Creation (Biased Mixed Strategies)")
        
        policy_1 = MatrixPolicy(
            name="BiasRock",
            probs=np.array([0.55, 0.25, 0.20])
        )
        policy_2 = MatrixPolicy(
            name="BiasPaper",
            probs=np.array([0.20, 0.55, 0.25])
        )
        policy_3 = MatrixPolicy(
            name="BiasScissors",
            probs=np.array([0.25, 0.20, 0.55])
        )
        
        policies = [policy_1, policy_2, policy_3]
        policy_names = ["BiasRock", "BiasPaper", "BiasScissors"]
        
        logger.info("POLICIES", f"Created 3 biased policies: {policy_names}")
        logger.info("POLICIES", "  BiasRock: 55% Rock, 25% Paper, 20% Scissors")
        logger.info("POLICIES", "  BiasPaper: 20% Rock, 55% Paper, 25% Scissors")
        logger.info("POLICIES", "  BiasScissors: 25% Rock, 20% Paper, 55% Scissors")
        
        # ===== TOURNAMENT EVALUATION =====
        logger.section("Round-Robin Tournament")
        
        N_MATCHES = 1000
        rng = np.random.default_rng(42)
        
        win_matrix = np.zeros((len(policies), len(policies)))
        
        logger.info("TOURNAMENT", f"Each pair plays {N_MATCHES} matches")
        
        for i, policy_i in enumerate(policies):
            for j, policy_j in enumerate(policies):
                if i == j:
                    win_matrix[i, j] = 0.5
                else:
                    wins = 0
                    for _ in range(N_MATCHES):
                        action_i = policy_i.act(rng)
                        action_j = policy_j.act(rng)
                        
                        payoff = payoff_p0[action_i, action_j]
                        
                        if payoff > 0.5:
                            wins += 1
                    
                    win_matrix[i, j] = wins / N_MATCHES
                
                logger.metric(f"winrate_{policy_names[i]}_vs_{policy_names[j]}", 
                             win_matrix[i, j], "head-to-head win rate")
                logger.info("TOURNAMENT", 
                           f"  {policy_names[i]} vs {policy_names[j]}: {win_matrix[i, j]:.1%}")
        
        logger.data("win_matrix", win_matrix.tolist(), 
                   "Win rate matrix [i,j] = win rate of policy i vs j")
        
        # ===== RANKING ANALYSIS =====
        logger.section("Ranking Analysis (Detecting Cycles)")
        
        avg_wins = np.mean(win_matrix, axis=1)
        ranking_by_avg = np.argsort(-avg_wins)
        
        logger.info("RANKING", "Average win rates (strength):")
        for i in ranking_by_avg:
            logger.info("RANKING", f"  {policy_names[i]}: {avg_wins[i]:.2%}")
        
        for i, name in enumerate(policy_names):
            logger.metric(f"avg_winrate_{name}", avg_wins[i], 
                         "average win rate across all opponents")
        
        logger.info("RANKING", "Head-to-head matchups:")
        cycle_found = False
        
        if (win_matrix[0, 1] > 0.5 and 
            win_matrix[1, 2] > 0.5 and 
            win_matrix[2, 0] > 0.5):
            logger.info("CYCLE", f"FOUND: {policy_names[0]} > {policy_names[1]} > {policy_names[2]} > {policy_names[0]}")
            cycle_found = True
        
        if (win_matrix[0, 2] > 0.5 and 
            win_matrix[2, 1] > 0.5 and 
            win_matrix[1, 0] > 0.5):
            logger.info("CYCLE", f"FOUND: {policy_names[0]} > {policy_names[2]} > {policy_names[1]} > {policy_names[0]}")
            cycle_found = True
        
        if not cycle_found:
            logger.info("CYCLE", "No strict cycles detected")
        
        logger.metric("has_cycle", float(cycle_found), "whether cycle exists (1=yes)")
        
        # ===== VISUALIZATION =====
        logger.section("Visualization")
        
        fig, ax = plt.subplots(figsize=(10, 8))
        im = ax.imshow(win_matrix, cmap='RdYlGn', vmin=0, vmax=1)
        
        ax.set_xticks(np.arange(len(policy_names)))
        ax.set_yticks(np.arange(len(policy_names)))
        ax.set_xticklabels(policy_names)
        ax.set_yticklabels(policy_names)
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
        
        for i in range(len(policy_names)):
            for j in range(len(policy_names)):
                ax.text(j, i, f'{win_matrix[i, j]:.2f}',
                       ha="center", va="center", color="black", fontsize=12)
        
        ax.set_title("Tournament Results: Win Rates\\n(rows = player, cols = opponent)")
        ax.set_xlabel("Opponent Policy")
        ax.set_ylabel("Policy")
        
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label("Win Rate", rotation=270, labelpad=20)
        
        outpath = logger.exp_dir / "tournament_heatmap.png"
        plt.tight_layout()
        plt.savefig(outpath, dpi=180)
        plt.close()
        logger.info("VIZ", f"Saved: {outpath.name}")
        
        # ===== SUMMARY =====
        logger.section("Experiment Summary")
        
        logger.success("Non-transitivity analysis complete")
        if cycle_found:
            logger.info("FINDING", "Rock-Paper-Scissors cycle detected!")
            logger.info("FINDING", "  → No single best policy")
        else:
            logger.info("FINDING", "Linear ordering exists (transitive)")
        
        final_data = {
            "config": {
                "game": "Rock-Paper-Scissors",
                "policies": {
                    "BiasRock": [0.55, 0.25, 0.20],
                    "BiasPaper": [0.20, 0.55, 0.25],
                    "BiasScissors": [0.25, 0.20, 0.55]
                },
                "n_matches_per_pair": N_MATCHES
            },
            "policy_names": policy_names,
            "win_matrix": win_matrix.tolist(),
            "avg_win_rates": avg_wins.tolist(),
            "ranking": [policy_names[i] for i in ranking_by_avg],
            "has_cycle": bool(cycle_found)
        }
        logger.data("experiment_results", final_data, "Tournament analysis")
        
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
