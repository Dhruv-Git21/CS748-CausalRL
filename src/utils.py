"""
Utility functions for experiments.

Classes:
  - TrajectoryBatch: Container for trajectory data

Functions:
  - set_seed(seed): Set random seeds for reproducibility
  - collect_batch(env, beh, pi, N, T, seed): Collect trajectories
  - ensure_dir(path): Create directory if it doesn't exist
  - savefig(path, dpi): Save matplotlib figure
  - plot_heatmap(...): Plot heatmap
  - plot_hist(...): Plot histogram
  - plot_scatter(...): Plot scatter
  - save_json(path, obj): Save JSON
  - load_json(path): Load JSON
"""
from __future__ import annotations
import random
import json
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Dict
import numpy as np
import matplotlib.pyplot as plt
from envs import Gridworld
from policies import TabularPolicy


# ===== Reproducibility =====

def set_seed(seed: int) -> None:
    """Set random seeds for reproducibility."""
    random.seed(seed)
    np.random.seed(seed)


# ===== Trajectory Collection =====

@dataclass
class TrajectoryBatch:
    """Batch of trajectories for OPE."""

    rewards: np.ndarray  # (N, T)
    actions: np.ndarray  # (N, T)
    states: np.ndarray  # (N, T)
    beh_probs: np.ndarray  # (N, T) behavior policy prob
    pi_probs: np.ndarray  # (N, T) eval policy prob
    dones: np.ndarray  # (N, T)

    def returns(self, gamma: float = 0.99) -> np.ndarray:
        """Compute discounted returns for each trajectory."""
        disc = (gamma ** np.arange(self.rewards.shape[1]))[None, :]
        return np.sum(disc * self.rewards, axis=1)

    def traj_ratios(self) -> np.ndarray:
        """Compute importance ratios (product over steps)."""
        r = self.pi_probs / (self.beh_probs + 1e-12)
        return np.prod(r, axis=1)

    def step_cum_ratios(self) -> np.ndarray:
        """Compute cumulative importance ratios per step."""
        r = self.pi_probs / (self.beh_probs + 1e-12)
        return np.cumprod(r, axis=1)


def collect_batch(
    env: Gridworld,
    beh: TabularPolicy,
    pi: TabularPolicy,
    N: int,
    T: int,
    seed: int = 0,
) -> TrajectoryBatch:
    """Collect trajectories under behavior policy.
    
    Args:
        env: Gridworld environment
        beh: Behavior policy
        pi: Evaluation policy
        N: Number of trajectories
        T: Trajectory length
        seed: Random seed
        
    Returns:
        TrajectoryBatch with collected data
    """
    rng = np.random.default_rng(seed)
    rewards = np.zeros((N, T), dtype=float)
    actions = np.zeros((N, T), dtype=int)
    states = np.zeros((N, T), dtype=int)
    beh_p = np.zeros((N, T), dtype=float)
    pi_p = np.zeros((N, T), dtype=float)
    dones = np.zeros((N, T), dtype=bool)

    for i in range(N):
        s = env.reset()
        for t in range(T):
            a = beh.act(s, rng)
            s2, r, done, _ = env.step(a, rng)
            rewards[i, t] = r
            actions[i, t] = a
            states[i, t] = s
            beh_p[i, t] = beh.prob(s, a)
            pi_p[i, t] = pi.prob(s, a)
            dones[i, t] = done
            s = s2
            if done:
                for tt in range(t + 1, T):
                    states[i, tt] = s
                    actions[i, tt] = a
                    beh_p[i, tt] = beh_p[i, t]
                    pi_p[i, tt] = pi_p[i, t]
                    rewards[i, tt] = 0.0
                    dones[i, tt] = True
                break

    return TrajectoryBatch(rewards, actions, states, beh_p, pi_p, dones)


# ===== Plotting Utilities =====

def ensure_dir(p: str | Path) -> Path:
    """Create directory if it doesn't exist."""
    p = Path(p)
    p.mkdir(parents=True, exist_ok=True)
    return p


def savefig(path: str | Path, dpi: int = 180) -> None:
    """Save matplotlib figure and close."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=dpi)
    plt.close()


def plot_heatmap(
    mat: np.ndarray,
    xlabels=None,
    ylabels=None,
    title: str = "",
    outpath: str | Path = "heatmap.png",
):
    """Plot heatmap."""
    plt.figure(figsize=(6, 5))
    plt.imshow(mat, aspect="auto")
    plt.colorbar()
    if xlabels is not None:
        plt.xticks(range(len(xlabels)), xlabels, rotation=45, ha="right")
    if ylabels is not None:
        plt.yticks(range(len(ylabels)), ylabels)
    plt.title(title)
    savefig(outpath)


def plot_hist(
    x: np.ndarray, title: str, xlabel: str, outpath: str | Path
):
    """Plot histogram."""
    plt.figure(figsize=(6, 4))
    plt.hist(x, bins=40)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel("count")
    savefig(outpath)


def plot_scatter(
    x,
    y,
    title: str,
    xlabel: str,
    ylabel: str,
    outpath: str | Path,
    labels=None,
):
    """Plot scatter."""
    plt.figure(figsize=(6, 4))
    plt.scatter(x, y)
    if labels is not None:
        for xi, yi, lab in zip(x, y, labels):
            plt.text(xi, yi, str(lab), fontsize=8)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    savefig(outpath)


# ===== File I/O =====

def save_json(path: str | Path, obj: Dict[str, Any]) -> None:
    """Save object as JSON."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def load_json(path: str | Path) -> Dict[str, Any]:
    """Load JSON file."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def collect_shared_batch(
    env: Gridworld,
    beh: TabularPolicy,
    policies: list,
    N: int,
    T: int,
    seed: int = 0,
) -> tuple:
    """
    Collect ONE shared batch under behavior policy and compute importance weights
    for all evaluation policies on the SAME trajectories.

    This is the correct setup for counterfactual PoR estimation: all policies
    are compared in the same trajectory contexts, enabling matched-pair comparison.

    Args:
        env: Gridworld environment
        beh: Behavior policy (data collection)
        policies: List of K evaluation policies
        N: Number of shared trajectories
        T: Trajectory length
        seed: Random seed

    Returns:
        (base_batch, weights_list) where:
          - base_batch: TrajectoryBatch collected under beh (pi_probs = beh probs)
          - weights_list: K arrays of (N,) trajectory IS ratios pi_k/beh for shared batch
    """
    rng = np.random.default_rng(seed)
    K = len(policies)

    rewards = np.zeros((N, T), dtype=float)
    actions = np.zeros((N, T), dtype=int)
    states = np.zeros((N, T), dtype=int)
    beh_p = np.zeros((N, T), dtype=float)
    dones = np.zeros((N, T), dtype=bool)
    # Store all policy probs for shared trajectories
    pi_p_all = np.zeros((K, N, T), dtype=float)

    for i in range(N):
        s = env.reset()
        for t in range(T):
            a = beh.act(s, rng)
            s2, r, done, _ = env.step(a, rng)
            rewards[i, t] = r
            actions[i, t] = a
            states[i, t] = s
            beh_p[i, t] = beh.prob(s, a)
            for k, pi in enumerate(policies):
                pi_p_all[k, i, t] = pi.prob(s, a)
            dones[i, t] = done
            s = s2
            if done:
                for tt in range(t + 1, T):
                    states[i, tt] = s
                    actions[i, tt] = a
                    beh_p[i, tt] = beh_p[i, t]
                    for k in range(K):
                        pi_p_all[k, i, tt] = pi_p_all[k, i, t]
                    rewards[i, tt] = 0.0
                    dones[i, tt] = True
                break

    # Build shared batch (pi_probs = beh for reference)
    base_batch = TrajectoryBatch(rewards, actions, states, beh_p, beh_p.copy(), dones)

    # Compute trajectory-level IS ratios pi_k / beh for each policy
    weights_list = []
    for k in range(K):
        ratio = pi_p_all[k] / (beh_p + 1e-12)  # (N, T)
        traj_ratio = np.prod(ratio, axis=1)       # (N,)
        weights_list.append(traj_ratio)

    return base_batch, weights_list
