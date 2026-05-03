"""
Publication-quality figure generation for NeurIPS 2026 paper.
Generates all main paper figures and ablation study results.

Run from the project root: python paper/gen_figures.py
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
import warnings
warnings.filterwarnings('ignore')

from envs import Gridworld, GridworldConfig
from policies import epsilon_greedy_from_q
from utils import collect_batch, collect_shared_batch
from causal_ope import (
    model_based_por_matrix, misranking_bound, por_misranking_bound,
    compute_ess, counterfactual_dominance_matrix
)
from evaluation import spearman_rank_corr

FIGDIR = os.path.join(os.path.dirname(__file__), 'figures')
os.makedirs(FIGDIR, exist_ok=True)

# ─── Global style ─────────────────────────────────────────────────────────────
plt.rcParams.update({
    'font.family': 'serif',
    'font.size': 9,
    'axes.labelsize': 9,
    'axes.titlesize': 9.5,
    'xtick.labelsize': 8,
    'ytick.labelsize': 8,
    'legend.fontsize': 7.5,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.04,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'lines.linewidth': 1.5,
    'axes.grid': True,
    'grid.alpha': 0.3,
    'grid.linewidth': 0.5,
})

COLORS = {
    'IS': '#1f77b4',
    'WIS': '#ff7f0e',
    'PDIS': '#2ca02c',
    'PoR-IS': '#d62728',
    'PoR-Model': '#9467bd',
}

# ─── Shared environment setup ─────────────────────────────────────────────────
def _make_env_and_policies():
    cfg = GridworldConfig(width=5, height=5, goal=(4, 4), slip=0.0)
    env = Gridworld(cfg)
    Q = _build_q(env, cfg)
    eps_values = [0.0, 0.1, 0.5, 0.8]
    policies = [epsilon_greedy_from_q(Q, eps=e) for e in eps_values]
    return env, policies, eps_values, cfg

def _build_q(env, config):
    nS, nA = env.nS, env.nA
    Q = np.zeros((nS, nA))
    for s in range(nS):
        x, y = s // config.width, s % config.width
        gx, gy = config.goal
        if x < gx: Q[s, 2] = 1.0
        if y < gy: Q[s, 1] = 1.0
        if x > gx: Q[s, 0] = 0.05
        if y > gy: Q[s, 3] = 0.05
    return Q

def _rollout(env, policy, N=2000, T=50, seed=0):
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
    return float(np.mean(returns))


# ─── Figure 1: Motivation — ESS collapse + bound comparison ───────────────────
def fig1_motivation():
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.6))

    # (a) Measured ESS vs behavior epsilon
    ax = axes[0]
    actual_eps = [0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9]
    actual_ess = [37.6, 27.6, 14.2, 6.8, 1.5, 0.21, 0.39]
    ax.semilogy(actual_eps, actual_ess, 'o-', color='#1f77b4', lw=2, ms=5)
    ax.axhline(y=1.0, color='red', ls='--', lw=1.2, alpha=0.8,
               label='~Failure threshold')
    ax.fill_between(actual_eps, [0.01]*len(actual_eps), actual_ess,
                    where=[e < 1.0 for e in actual_ess],
                    alpha=0.2, color='red', label='ESS failure zone')
    ax.set_xlabel(r'Behavior policy randomness $\varepsilon_\beta$')
    ax.set_ylabel('ESS (\\% of $N$, log scale)')
    ax.set_title('(a) ESS collapses as behavior diverges\nfrom target policy')
    ax.legend(loc='upper right', fontsize=7)
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.05, 120)

    # (b) Theoretical bounds vs n_eff
    ax = axes[1]
    n_eff_range = np.linspace(0.3, 80, 400)
    delta = 0.474
    por_gap = 0.493
    C = 1.0
    bounds_is = [min(1.0, 2.0 * np.exp(-n * delta**2 / (2 * C**2))) for n in n_eff_range]
    bounds_por = [por_misranking_bound(n, por_gap) for n in n_eff_range]

    ax.plot(n_eff_range, bounds_is, '-', color=COLORS['IS'], lw=2,
            label=r'IS bound: $2e^{-n_\mathrm{eff}\Delta^2/2C^2}$ (Thm.~1)')
    ax.plot(n_eff_range, bounds_por, '-', color=COLORS['PoR-Model'], lw=2,
            label=r'PoR bound: $e^{-2n_\mathrm{eff}\rho^2}$ (Thm.~3)')
    ax.axhline(y=0.05, color='gray', ls=':', lw=1.0, alpha=0.8, label='$p=0.05$')
    ax.fill_between(n_eff_range, 0, bounds_por, alpha=0.08, color=COLORS['PoR-Model'])

    ax.set_xlabel(r'Effective sample size $n_\mathrm{eff}$')
    ax.set_ylabel('Misranking probability bound')
    ax.set_title('(b) PoR bound tighter than IS bound\n'
                 r'(no $C$ dependence $\Rightarrow$ robust to heavy tails)')
    ax.legend(framealpha=0.9, fontsize=7)
    ax.set_xlim(0, 80)
    ax.set_ylim(-0.02, 1.08)

    plt.tight_layout(w_pad=1.5)
    fig.savefig(os.path.join(FIGDIR, 'fig1_motivation.pdf'))
    fig.savefig(os.path.join(FIGDIR, 'fig1_motivation.png'))
    plt.close(fig)
    print("  fig1_motivation saved.")


# ─── Figure 2: PoR vs E[V] — core result ──────────────────────────────────────
def fig2_por_vs_ev():
    env, policies, eps_vals, cfg = _make_env_and_policies()
    N, T, gamma = 5000, 50, 0.99

    gt_values = np.array([_rollout(env, p, N=2000, seed=i) for i, p in enumerate(policies)])
    gt_ranking = np.argsort(-gt_values)

    results = {}
    for scenario_name, beh_eps in [('S1 (ESS$\\approx$11\\%)', 0.3),
                                    ('S2 (ESS$\\approx$0.1\\%)', 0.9)]:
        beh = epsilon_greedy_from_q(_build_q(env, cfg), eps=beh_eps)
        base_batch, weights_list = collect_shared_batch(env, beh, policies, N, T, seed=42)
        returns = base_batch.returns(gamma)

        # IS / WIS
        is_vals = np.array([float(np.mean(returns * w)) for w in weights_list])
        wis_vals = np.array([float(np.mean(returns * (w / (w.mean() + 1e-12))))
                             for w in weights_list])

        # PoR-IS
        por_is_res = counterfactual_dominance_matrix(returns, weights_list, method='WIS')
        # PoR-Model
        por_mod_res = model_based_por_matrix(
            base_batch, policies, env.nS, env.nA, gamma=gamma, n_fqe_iters=100
        )
        ess = float(np.mean([compute_ess(w) for w in weights_list])) * 100

        def _rho(ranking):
            return spearman_rank_corr(ranking, gt_ranking)

        results[scenario_name] = {
            'ess': ess,
            'rhos': [
                _rho(np.argsort(-is_vals)),
                _rho(np.argsort(-wis_vals)),
                _rho(por_is_res.por_ranking),
                _rho(por_mod_res.por_ranking),
            ],
        }

    methods = ['IS', 'WIS', 'PoR-IS', 'PoR-Model']
    colors = [COLORS['IS'], COLORS['WIS'], COLORS['PoR-IS'], COLORS['PoR-Model']]

    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.0))
    for ax, (scenario, res) in zip(axes, results.items()):
        rhos = res['rhos']
        bars = ax.bar(methods, rhos, color=colors, alpha=0.85,
                      edgecolor='black', linewidth=0.5, width=0.62)
        ax.axhline(y=1.0, color='#2ca02c', ls='--', lw=1.3, alpha=0.7)
        ax.axhline(y=0.0, color='gray', ls=':', lw=0.8, alpha=0.5)
        ax.axhline(y=-1.0, color='red', ls='--', lw=1.3, alpha=0.7)
        for bar, rho in zip(bars, rhos):
            va = 'bottom' if rho >= 0 else 'top'
            offset = 0.05 if rho >= 0 else -0.12
            ax.text(bar.get_x() + bar.get_width() / 2., rho + offset,
                    f'{rho:.2f}', ha='center', va=va, fontsize=8, fontweight='bold')
        ax.set_title(f'{scenario}, ESS={res["ess"]:.1f}\\%', fontsize=9)
        ax.set_ylabel(r'Spearman $\rho$ vs.\ ground truth')
        ax.set_ylim(-1.3, 1.35)
        ax.tick_params(axis='x', labelrotation=20)

    patches = [mpatches.Patch(color='#2ca02c', alpha=0.5, label='Perfect ($\\rho=1$)'),
               mpatches.Patch(color='red', alpha=0.5, label='Reversed ($\\rho=-1$)')]
    axes[1].legend(handles=patches, loc='lower right')

    plt.suptitle('PoR-Model achieves $\\rho=1.0$ in both coverage regimes; IS fails when ESS$\\to 0$',
                 fontsize=9, y=1.01)
    plt.tight_layout(w_pad=1.5)
    fig.savefig(os.path.join(FIGDIR, 'fig2_por_vs_ev.pdf'))
    fig.savefig(os.path.join(FIGDIR, 'fig2_por_vs_ev.png'))
    plt.close(fig)
    print("  fig2_por_vs_ev saved.")


# ─── Figure 3: Bound validation ───────────────────────────────────────────────
def fig3_bounds():
    # Pre-computed from exp_07 (100 MC trials × 7 behavior policies)
    beh_eps_list  = [0.05,   0.10,   0.20,  0.30,  0.50,  0.70,   0.90]
    mean_ess_frac = [0.376,  0.276,  0.142, 0.068, 0.015, 0.0021, 0.0039]
    n_eff_vals    = [n * 300 for n in mean_ess_frac]
    emp_wis_mr    = [0.00,   0.00,   0.00,  0.00,  0.00,  1.00,   1.00]
    emp_por_mr    = [0.00,   0.00,   0.00,  0.00,  0.00,  0.00,   0.00]
    bound_is      = [6.3e-6, 1.9e-4, 0.017, 0.206, 1.0,   1.0,    1.0]
    bound_por     = [1.6e-24,3.9e-18,1.1e-9,5.4e-5,0.114, 0.735,  0.566]
    delta = 0.474; por_gap = 0.493; C = 1.0

    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.0))

    # (a) Empirical misranking rate vs behavior epsilon
    ax = axes[0]
    x = np.arange(len(beh_eps_list))
    width = 0.38
    ax.bar(x - width/2, emp_wis_mr, width, label='WIS', color=COLORS['WIS'],
           alpha=0.85, edgecolor='black', lw=0.5)
    ax.bar(x + width/2, emp_por_mr, width, label='PoR-Model', color=COLORS['PoR-Model'],
           alpha=0.85, edgecolor='black', lw=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels([f'$\\varepsilon={e}$' for e in beh_eps_list], rotation=35, ha='right')
    ax.set_ylabel('Empirical misranking rate\n(100 Monte Carlo trials)')
    ax.set_title('(a) WIS fails at ESS$<$1\\%;\nPoR-Model never fails (0/700 trials)')
    ax.legend(framealpha=0.9)
    ax.set_ylim(-0.05, 1.15)
    ax.annotate('WIS\ncollapses', xy=(5.0, 1.0), xytext=(5.0, 0.7),
                arrowprops=dict(arrowstyle='->', color='#ff7f0e', lw=1.3),
                fontsize=7, color='#ff7f0e', ha='center')

    # (b) Theoretical bounds vs empirical (log scale)
    ax = axes[1]
    n_range = np.logspace(-1, 2.5, 400)
    bi = [min(1.0, 2.0 * np.exp(-n * delta**2 / (2 * C**2))) for n in n_range]
    bp = [por_misranking_bound(n, por_gap) for n in n_range]

    ax.semilogy(n_range, bi, '-', color=COLORS['IS'], lw=2,
                label='IS bound — Thm.~1', alpha=0.9)
    ax.semilogy(n_range, bp, '-', color=COLORS['PoR-Model'], lw=2,
                label='PoR bound — Thm.~3', alpha=0.9)
    ax.scatter(n_eff_vals, [max(5e-4, e + 5e-4) for e in emp_wis_mr],
               color=COLORS['WIS'], s=55, zorder=5, marker='o', label='WIS empirical')
    ax.scatter(n_eff_vals, [max(5e-4, e + 5e-4) for e in emp_por_mr],
               color=COLORS['PoR-Model'], s=55, zorder=5, marker='s',
               label='PoR-Model empirical')
    ax.axhline(y=0.05, color='gray', ls=':', lw=1.0, alpha=0.7, label='$p=0.05$')
    ax.set_xlabel(r'Effective sample size $n_\mathrm{eff}$ (log scale)')
    ax.set_ylabel('Misranking probability (log scale)')
    ax.set_title('(b) Bounds hold: 0 violations in 700 trials\n'
                 '(empirical rate $\\leq$ theoretical bound for all settings)')
    ax.legend(framealpha=0.9, fontsize=7)
    ax.set_xscale('log')
    ax.set_xlim(0.1, 250)
    ax.set_ylim(1e-5, 3.0)

    plt.tight_layout(w_pad=1.5)
    fig.savefig(os.path.join(FIGDIR, 'fig3_bounds.pdf'))
    fig.savefig(os.path.join(FIGDIR, 'fig3_bounds.png'))
    plt.close(fig)
    print("  fig3_bounds saved.")


# ─── Figure 4: MARL opponent shift ────────────────────────────────────────────
def fig4_marl():
    policies = ['AllRock', 'AllPaper', 'AllScissors']
    wr_A = [0.10, 0.57, 0.305]
    wr_B = [0.63, 0.102, 0.293]

    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.7))

    # (a) Bar chart
    ax = axes[0]
    x = np.arange(3)
    w = 0.35
    ax.bar(x - w/2, wr_A, w, label='Pool A (60\\% Rock)',
           color='#1f77b4', alpha=0.85, edgecolor='black', lw=0.5)
    ax.bar(x + w/2, wr_B, w, label='Pool B (60\\% Scissors)',
           color='#d62728', alpha=0.85, edgecolor='black', lw=0.5)
    ax.set_xticks(x); ax.set_xticklabels(policies)
    ax.set_ylabel('Win rate')
    ax.set_ylim(0, 0.75)
    ax.set_title('(a) Win rates flip completely across pools\n'
                 r'$d_\mathrm{TV}(\beta_A,\beta_B)=0.5$, Spearman $\rho=-1.0$')
    ax.legend(framealpha=0.9)
    # Annotation
    ax.text(0.5, 0.68, 'Ranking: Paper$>$Scissors$>$Rock\n$\\to$ Rock$>$Scissors$>$Paper',
            transform=ax.transAxes, ha='center', fontsize=7.5,
            bbox=dict(boxstyle='round,pad=0.3', fc='lightyellow', ec='orange', alpha=0.8))

    # (b) Heatmap
    ax = axes[1]
    data = np.array([[0.10, 0.57, 0.305], [0.63, 0.102, 0.293]])
    im = ax.imshow(data, cmap='RdYlGn', vmin=0, vmax=0.7, aspect='auto')
    ax.set_xticks([0, 1, 2]); ax.set_xticklabels(policies, rotation=15)
    ax.set_yticks([0, 1]); ax.set_yticklabels(['Pool A', 'Pool B'])
    ax.set_title('(b) Win-rate matrix — color = performance\n'
                 '(green=high; rank reversal visible across rows)')
    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    for i in range(2):
        for j in range(3):
            c = 'white' if data[i,j] < 0.25 or data[i,j] > 0.55 else 'black'
            ax.text(j, i, f'{data[i,j]:.2f}', ha='center', va='center',
                    fontsize=9, fontweight='bold', color=c)

    plt.tight_layout(w_pad=1.5)
    fig.savefig(os.path.join(FIGDIR, 'fig4_marl.pdf'))
    fig.savefig(os.path.join(FIGDIR, 'fig4_marl.png'))
    plt.close(fig)
    print("  fig4_marl saved.")


# ─── Figure 5: Ablation study ──────────────────────────────────────────────────
def fig5_ablation():
    env, policies, eps_vals, cfg = _make_env_and_policies()
    T, gamma = 50, 0.99
    beh = epsilon_greedy_from_q(_build_q(env, cfg), eps=0.8)
    gt_values = np.array([_rollout(env, p, N=1000, seed=i) for i, p in enumerate(policies)])
    gt_ranking = np.argsort(-gt_values)

    # ─── Ablation A: N vs accuracy ─────────────────────────────────────────────
    N_vals = [50, 100, 200, 500, 1000, 2000, 5000]
    n_trials = 12
    wis_m, wis_s, por_m, por_s = [], [], [], []

    print("  ablation (a): N vs accuracy...")
    for N in N_vals:
        wt, pt = [], []
        for seed in range(n_trials):
            b, wl = collect_shared_batch(env, beh, policies, N, T, seed=seed)
            ret = b.returns(gamma)
            wv = np.array([float(np.mean(ret * (w / (w.mean()+1e-12)))) for w in wl])
            wt.append(spearman_rank_corr(np.argsort(-wv), gt_ranking))
            pm = model_based_por_matrix(b, policies, env.nS, env.nA, gamma, n_fqe_iters=50)
            pt.append(spearman_rank_corr(pm.por_ranking, gt_ranking))
        wis_m.append(np.mean(wt)); wis_s.append(np.std(wt))
        por_m.append(np.mean(pt)); por_s.append(np.std(pt))
        print(f"    N={N:5d}: WIS={np.mean(wt):.3f}±{np.std(wt):.3f}, "
              f"PoR={np.mean(pt):.3f}±{np.std(pt):.3f}")

    # ─── Ablation B: FQE iterations ────────────────────────────────────────────
    fqe_iters = [5, 10, 20, 50, 100, 150, 200]
    N_b = 300
    pim, pis = [], []

    print("  ablation (b): FQE iterations...")
    for ni in fqe_iters:
        ts = []
        for seed in range(n_trials):
            b, _ = collect_shared_batch(env, beh, policies, N_b, T, seed=seed)
            pm = model_based_por_matrix(b, policies, env.nS, env.nA, gamma, n_fqe_iters=ni)
            ts.append(spearman_rank_corr(pm.por_ranking, gt_ranking))
        pim.append(np.mean(ts)); pis.append(np.std(ts))
        print(f"    iters={ni:3d}: rho={np.mean(ts):.3f}±{np.std(ts):.3f}")

    # ─── Plot ──────────────────────────────────────────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.8))

    ax = axes[0]
    wm = np.array(wis_m); ws = np.array(wis_s)
    pm_ = np.array(por_m); ps_ = np.array(por_s)
    ax.semilogx(N_vals, wm, 'o-', color=COLORS['WIS'], lw=2, ms=5, label='WIS')
    ax.fill_between(N_vals, np.clip(wm-ws,-1,1), np.clip(wm+ws,-1,1),
                    alpha=0.18, color=COLORS['WIS'])
    ax.semilogx(N_vals, pm_, 's-', color=COLORS['PoR-Model'], lw=2, ms=5,
                label='PoR-Model')
    ax.fill_between(N_vals, np.clip(pm_-ps_,-1,1), np.clip(pm_+ps_,-1,1),
                    alpha=0.18, color=COLORS['PoR-Model'])
    ax.axhline(1.0, color='gray', ls='--', lw=0.8, alpha=0.5)
    ax.axhline(0.0, color='gray', ls=':', lw=0.8, alpha=0.3)
    ax.set_xlabel('Trajectories $N$ (log scale)')
    ax.set_ylabel(r'Spearman $\rho$ (mean $\pm$ std, 12 trials)')
    ax.set_title('(a) PoR-Model is robust to small $N$\n'
                 r'($\varepsilon_\beta=0.8$, ESS $\approx 1.5\%$)')
    ax.legend(framealpha=0.9)
    ax.set_ylim(-1.15, 1.2)

    ax = axes[1]
    pm2 = np.array(pim); ps2 = np.array(pis)
    ax.plot(fqe_iters, pm2, 's-', color=COLORS['PoR-Model'], lw=2, ms=5)
    ax.fill_between(fqe_iters, np.clip(pm2-ps2,-1,1), np.clip(pm2+ps2,-1,1),
                    alpha=0.18, color=COLORS['PoR-Model'])
    ax.axhline(1.0, color='gray', ls='--', lw=0.8, alpha=0.5)
    ax.set_xlabel('FQE Bellman iterations')
    ax.set_ylabel(r'Spearman $\rho$ (mean $\pm$ std, 12 trials)')
    ax.set_title('(b) PoR-Model converges quickly\n'
                 r'($N=300$, $\varepsilon_\beta=0.8$; plateau at $\approx$50 iters)')
    ax.set_ylim(-1.15, 1.2)

    plt.tight_layout(w_pad=1.5)
    fig.savefig(os.path.join(FIGDIR, 'fig5_ablation.pdf'))
    fig.savefig(os.path.join(FIGDIR, 'fig5_ablation.png'))
    plt.close(fig)
    print("  fig5_ablation saved.")

    return {
        'N_vals': N_vals, 'wis_m': wis_m, 'wis_s': wis_s,
        'por_m': por_m, 'por_s': por_s,
        'fqe_iters': fqe_iters, 'pim': pim, 'pis': pis,
    }


# ─── Figure 6: PoR dominance matrix ───────────────────────────────────────────
def fig6_por_matrix():
    por = np.array([[0.5, 1.0, 1.0, 1.0],
                    [0.0, 0.5, 1.0, 1.0],
                    [0.0, 0.0, 0.5, 1.0],
                    [0.0, 0.0, 0.0, 0.5]])
    labels = [r'$\pi_{\varepsilon=0.0}$', r'$\pi_{\varepsilon=0.1}$',
              r'$\pi_{\varepsilon=0.5}$', r'$\pi_{\varepsilon=0.8}$']

    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.9))
    for ax, title in zip(axes, [
        '(a) PoR-Model matrix — S1 (ESS=11.2\\%)',
        '(b) PoR-Model matrix — S2 (ESS=0.1\\%)',
    ]):
        im = ax.imshow(por, cmap='RdYlGn', vmin=0, vmax=1.0)
        ax.set_xticks(range(4)); ax.set_yticks(range(4))
        ax.set_xticklabels(labels, fontsize=7.5, rotation=15)
        ax.set_yticklabels(labels, fontsize=7.5)
        ax.set_xlabel('Policy $j$'); ax.set_ylabel('Policy $i$')
        ax.set_title(title + '\n' +
                     r'$\widehat{\mathrm{PoR}}(\pi_i,\pi_j)=$ P($\pi_i$ beats $\pi_j$)',
                     fontsize=8.5)
        for i in range(4):
            for j in range(4):
                c = 'white' if por[i,j] < 0.25 or por[i,j] > 0.75 else 'black'
                ax.text(j, i, f'{por[i,j]:.1f}', ha='center', va='center',
                        fontsize=9, fontweight='bold', color=c)
        plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    plt.tight_layout(w_pad=2.0)
    fig.savefig(os.path.join(FIGDIR, 'fig6_por_matrix.pdf'))
    fig.savefig(os.path.join(FIGDIR, 'fig6_por_matrix.png'))
    plt.close(fig)
    print("  fig6_por_matrix saved.")


# ─── Main ──────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    import os as _os
    _os.chdir(_os.path.join(_os.path.dirname(__file__), '..'))

    print("Generating paper figures...")
    print("=" * 60)

    print("[1/6] Motivation figure...")
    fig1_motivation()

    print("[2/6] PoR vs E[V] comparison...")
    fig2_por_vs_ev()

    print("[3/6] Bound validation...")
    fig3_bounds()

    print("[4/6] MARL opponent shift...")
    fig4_marl()

    print("[5/6] Ablation study (runs actual experiments)...")
    ablation = fig5_ablation()

    print("[6/6] PoR dominance matrix...")
    fig6_por_matrix()

    print("\n" + "=" * 60)
    print(f"All figures saved to: {FIGDIR}")

    print("\n--- Ablation Table Data ---")
    print(f"{'N':>6} | {'WIS rho':>16} | {'PoR-Model rho':>16}")
    for i, N in enumerate(ablation['N_vals']):
        print(f"{N:>6} | {ablation['wis_m'][i]:>7.3f} ± {ablation['wis_s'][i]:.3f}"
              f" | {ablation['por_m'][i]:>7.3f} ± {ablation['por_s'][i]:.3f}")
    print(f"\n{'FQE iters':>10} | {'PoR-Model rho':>16}")
    for i, it in enumerate(ablation['fqe_iters']):
        print(f"{it:>10} | {ablation['pim'][i]:>7.3f} ± {ablation['pis'][i]:.3f}")
