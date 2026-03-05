"""
Orchestrator: Run all 5 experiments

Executes:
  1. exp_01_ope_works.py
  2. exp_02_ope_fails_shift.py
  3. exp_03_opponent_shift.py
  4. exp_04_nontransitivity.py
  5. exp_05_dominance_robust.py

All outputs go to results/figures/ and results/data/
"""
import subprocess
import sys
from pathlib import Path


def main():
    """Run all experiments."""
    exp_dir = Path(__file__).parent
    experiments = [
        "exp_01_ope_works.py",
        "exp_02_ope_fails_shift.py",
        "exp_03_opponent_shift.py",
        "exp_04_nontransitivity.py",
        "exp_05_dominance_robust.py",
    ]
    
    print("=" * 70)
    print("Running all 5 experiments...")
    print("=" * 70)
    
    for i, exp_file in enumerate(experiments, 1):
        exp_path = exp_dir / exp_file
        print(f"\n[{i}/5] Running {exp_file}...")
        print("-" * 70)
        
        result = subprocess.run(
            [sys.executable, str(exp_path)],
            cwd=str(exp_dir.parent),
        )
        
        if result.returncode != 0:
            print(f"ERROR: {exp_file} failed with exit code {result.returncode}")
            sys.exit(1)
        
        print(f"✓ {exp_file} completed")
    
    print("\n" + "=" * 70)
    print("All experiments completed successfully!")
    print("=" * 70)
    print("\nOutputs:")
    print("  - Figures: v2/results/figures/")
    print("  - Data: v2/results/data/")
    print("  - Logs: v2/results/logs/")


if __name__ == "__main__":
    main()
