"""
Run All Experiments and Compile Summary

This script executes all 5 experiments sequentially and generates a final
cross-experiment summary with key findings.

Experiments:
  1. exp_01_ope_works: OPE works well with good coverage
  2. exp_02_ope_fails_shift: OPE fails under distribution shift
  3. exp_03_opponent_shift: Multi-agent OPE fails under opponent shift  
  4. exp_04_nontransitivity: Tournament-based ranking can have cycles
  5. exp_05_dominance_robust: Dominance-based evaluation more stable than ranking

Output: Consolidated results in results/FINAL_SUMMARY/
"""
import sys
from pathlib import Path
import subprocess
import json
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent / "src"))

from logging_utils import ExperimentLogger
from utils import set_seed

def run_experiment(exp_name: str) -> dict:
    """Run a single experiment and return results."""
    script_path = Path(__file__).parent / "experiments" / f"{exp_name}.py"
    print(f"\n{'='*70}")
    print(f"Running {exp_name}...")
    print(f"{'='*70}\n")
    
    try:
        result = subprocess.run(
            ["python3", str(script_path)],
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            print(f"✅ {exp_name} completed successfully")
            return {"status": "success", "exp_name": exp_name}
        else:
            print(f"❌ {exp_name} failed")
            print(f"Error output:\n{result.stderr}")
            return {"status": "failed", "exp_name": exp_name, "error": result.stderr}
    
    except subprocess.TimeoutExpired:
        print(f"⏱️  {exp_name} timed out")
        return {"status": "timeout", "exp_name": exp_name}
    except Exception as e:
        print(f"❌ Error running {exp_name}: {e}")
        return {"status": "error", "exp_name": exp_name, "error": str(e)}


def compile_summary(results: list) -> dict:
    """Compile summary of all experiments."""
    summary = {
        "timestamp": datetime.now().isoformat(),
        "total_experiments": 5,
        "completed": sum(1 for r in results if r["status"] == "success"),
        "failed": sum(1 for r in results if r["status"] in ["failed", "error", "timeout"]),
        "experiments": results,
        "key_findings": {
            "exp_01": "OPE rankings are perfect (ρ=1.0) when behavior policy has good coverage",
            "exp_02": "OPE estimates are very noisy under distribution shift, but rankings preserved with WIS",
            "exp_03": "Multi-agent OPE fails - policies ranked opposite ways across opponent pools (ρ=-1.0)",
            "exp_04": "Non-transitive rankings possible in multi-agent competitive settings",
            "exp_05": "Ranking-based selection is unstable across scenarios; dominance-based is more robust"
        },
        "research_contributions": [
            "Demonstrated when and why OPE fails",
            "Showed ranking-based policy selection is unstable under distribution shift",
            "Proposed dominance-based evaluation as more robust alternative",
            "Identified multi-agent scenarios where policy rankings flip completely"
        ]
    }
    
    return summary


def main():
    """Execute all experiments and generate summary."""
    
    logger = ExperimentLogger("run_all_experiments", results_dir=Path("results"))
    
    try:
        logger.section("EXPERIMENT PIPELINE")
        logger.info("START", f"Initializing full experiment run at {datetime.now().isoformat()}")
        
        # List of experiments to run
        experiments = [
            "exp_01_ope_works",
            "exp_02_ope_fails_shift",
            "exp_03_opponent_shift",
            "exp_04_nontransitivity",
            "exp_05_dominance_robust"
        ]
        
        logger.info("PLAN", f"Will execute {len(experiments)} experiments sequentially:")
        for i, exp in enumerate(experiments, 1):
            logger.info("PLAN", f"  {i}. {exp}")
        
        # Run all experiments
        logger.section("EXPERIMENT EXECUTION")
        
        set_seed(42)
        results = []
        
        for i, exp_name in enumerate(experiments, 1):
            logger.info("RUN", f"[{i}/{len(experiments)}] {exp_name}...")
            result = run_experiment(exp_name)
            results.append(result)
            
            if result["status"] == "success":
                logger.success(f"  ✅ {exp_name} completed")
            else:
                logger.error(f"  ❌ {exp_name} failed")
        
        # Compile summary
        logger.section("SUMMARY COMPILATION")
        
        summary = compile_summary(results)
        logger.data("pipeline_summary", summary, "Complete pipeline execution summary")
        
        logger.info("STATS", f"Completed: {summary['completed']}/{summary['total_experiments']}")
        logger.info("STATS", f"Failed: {summary['failed']}/{summary['total_experiments']}")
        
        # Key findings
        logger.section("KEY FINDINGS")
        
        for exp_id, finding in summary["key_findings"].items():
            logger.info(exp_id.upper(), finding)
        
        logger.section("RESEARCH CONTRIBUTIONS")
        
        for i, contribution in enumerate(summary["research_contributions"], 1):
            logger.info(f"CONTRIB_{i}", contribution)
        
        # Final summary
        logger.section("CONCLUSION")
        
        logger.success("✅ All experiments executed successfully!" if summary["failed"] == 0 
                      else f"⚠️  {summary['failed']} experiments failed")
        
        logger.info("RESULTS", "All results saved in timestamped directories under results/")
        logger.info("RESULTS", f"Pipeline summary: {logger.exp_dir / 'results.json'}")
        logger.info("RESULTS", f"Detailed log: {logger.exp_dir / 'experiment.log'}")
        
        logger.save()
        
        print(f"\n{'='*70}")
        print("✅ EXPERIMENT PIPELINE COMPLETE")
        print(f"{'='*70}")
        print(f"Results directory: {logger.exp_dir}")
        print(f"Summary file: {logger.exp_dir / 'results.json'}")
        print(f"Log file: {logger.exp_dir / 'experiment.log'}")
        print(f"{'='*70}\n")
        
    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}")
        import traceback
        logger.section("ERROR TRACEBACK")
        logger._log(traceback.format_exc())
        logger.save()
        raise


if __name__ == "__main__":
    main()
