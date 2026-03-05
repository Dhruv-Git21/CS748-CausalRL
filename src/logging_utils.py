"""
Comprehensive logging infrastructure for experiments.

Provides:
  - Timestamped experiment logging
  - Metrics tracking and validation
  - Results serialization
  - Console + file output
"""
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List
import numpy as np


class ExperimentLogger:
    """Timestamped logger for experiments with metrics tracking."""

    def __init__(self, exp_name: str, results_dir: Path = Path("results")):
        """Initialize experiment logger.
        
        Args:
            exp_name: Name of experiment (e.g., 'exp_01_ope_works')
            results_dir: Base results directory
        """
        self.exp_name = exp_name
        self.results_dir = Path(results_dir)
        self.start_time = datetime.now()
        self.metrics = {}
        self.log_entries = []
        
        # Create timestamped subdirectories
        timestamp = self.start_time.strftime("%Y%m%d_%H%M%S")
        self.exp_dir = self.results_dir / self.exp_name / timestamp
        self.exp_dir.mkdir(parents=True, exist_ok=True)
        
        # Log file paths
        self.log_file = self.exp_dir / "experiment.log"
        self.metrics_file = self.exp_dir / "metrics.json"
        self.data_file = self.exp_dir / "results.json"
        
        self._log(f"{'='*70}")
        self._log(f"Experiment: {exp_name}")
        self._log(f"Started: {self.start_time.isoformat()}")
        self._log(f"Output Directory: {self.exp_dir}")
        self._log(f"{'='*70}\n")

    def _log(self, message: str) -> None:
        """Write message to console and log file."""
        print(message)
        self.log_entries.append({
            "timestamp": datetime.now().isoformat(),
            "message": message
        })

    def info(self, section: str, message: str) -> None:
        """Log info message with section header."""
        formatted = f"[{section}] {message}"
        self._log(formatted)

    def metric(self, name: str, value: float, description: str = "") -> None:
        """Record a metric.
        
        Args:
            name: Metric name (e.g., 'spearman_corr')
            value: Numeric value
            description: Optional description
        """
        self.metrics[name] = {
            "value": float(value),
            "description": description,
            "timestamp": datetime.now().isoformat()
        }
        desc_str = f" ({description})" if description else ""
        self._log(f"  → {name}: {value:.6f}{desc_str}")

    def data(self, name: str, data: Any, description: str = "") -> None:
        """Record structured data (arrays, dicts, etc).
        
        Args:
            name: Data name
            data: Data object (will be converted to JSON-serializable format)
            description: Optional description
        """
        # Convert numpy arrays to lists for JSON serialization
        if isinstance(data, np.ndarray):
            serializable = data.tolist()
        elif isinstance(data, (dict, list, str, int, float, bool, type(None))):
            serializable = data
        else:
            serializable = str(data)
        
        if name not in self.metrics:
            self.metrics[name] = {}
        
        self.metrics[name]["data"] = serializable
        self.metrics[name]["description"] = description
        self.metrics[name]["timestamp"] = datetime.now().isoformat()
        
        desc_str = f" ({description})" if description else ""
        self._log(f"  → {name} recorded{desc_str}")

    def section(self, title: str) -> None:
        """Log a section header."""
        self._log(f"\n{'─'*70}")
        self._log(f"  {title}")
        self._log(f"{'─'*70}\n")

    def error(self, message: str) -> None:
        """Log an error message."""
        self._log(f"❌ ERROR: {message}")

    def success(self, message: str) -> None:
        """Log a success message."""
        self._log(f"✅ {message}")

    def summary(self) -> Dict[str, Any]:
        """Get experiment summary."""
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        summary = {
            "experiment": self.exp_name,
            "started": self.start_time.isoformat(),
            "completed": end_time.isoformat(),
            "duration_seconds": duration,
            "metrics": self.metrics,
            "output_directory": str(self.exp_dir)
        }
        return summary

    def save(self) -> None:
        """Save all results to files."""
        # Save metrics
        summary = self.summary()
        with open(self.metrics_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        # Save raw metrics for easy access
        with open(self.data_file, 'w') as f:
            json.dump(self.metrics, f, indent=2)
        
        # Save log entries
        log_content = "\n".join([entry["message"] for entry in self.log_entries])
        with open(self.log_file, 'w') as f:
            f.write(log_content)
        
        self.section("Results Saved")
        self._log(f"✅ Metrics: {self.metrics_file}")
        self._log(f"✅ Data: {self.data_file}")
        self._log(f"✅ Log: {self.log_file}")


def validate_metric(name: str, value: float, expected_range: tuple = None, 
                   is_binary: bool = False) -> bool:
    """Validate metric value.
    
    Args:
        name: Metric name
        value: Metric value
        expected_range: (min, max) tuple for range validation
        is_binary: If True, value must be 0 or 1
        
    Returns:
        True if valid, False otherwise
    """
    if is_binary and value not in [0, 1]:
        print(f"❌ {name} must be 0 or 1, got {value}")
        return False
    
    if expected_range is not None:
        min_val, max_val = expected_range
        if not (min_val <= value <= max_val):
            print(f"❌ {name} out of range [{min_val}, {max_val}], got {value}")
            return False
    
    if np.isnan(value):
        print(f"❌ {name} is NaN")
        return False
    
    return True
