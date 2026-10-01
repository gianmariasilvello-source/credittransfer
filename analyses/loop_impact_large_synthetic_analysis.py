#!/usr/bin/env python3
"""Ad-hoc analysis of loop handling and loop impact on large synthetic graphs."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import eigs

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns


PROJECT_ROOT = str(Path(__file__).resolve().parents[1])
DEFAULT_EDGES_PATH = cast(str, str(Path(PROJECT_ROOT) / 'data' / 'synthetic_10K' / '10K_citation_edges.txt'))
OUTPUT_DIR = cast(str, str(Path(PROJECT_ROOT) / 'analyses' / 'loop_impact_report'))
TABLES_DIR = cast(str, str(Path(OUTPUT_DIR) / 'tables'))
PLOTS_DIR = cast(str, str(Path(OUTPUT_DIR) / 'plots'))

sns.set_theme(style='whitegrid', font_scale=1.0)


@dataclass
class ScenarioResult:
    scenario: str
    n_nodes: int
    n_edges: int
    self_loops: int
    reciprocal_pairs: int
    temporal_violations: int
    spectral_radius: float
    converges_rho_lt_1: bool


def load_edges(path: str) -> tuple[np.ndarray, int]:
    edges = []
    max_node = -1
    with open(path, 'r') as f:
        for line in f:
            if not line.strip() or line.startswith('#'):
                continue
            s, t = line.strip().split()
            u, v = int(s), int(t)
            edges.append((u, v))
            if u > max_node:
                max_node = u
            if v > max_node:
                max_node = v
    arr = np.array(edges, dtype=np.int64)
    return arr, max_node + 1


def structural_metrics(edges: np.ndarray) -> dict[str, int]:
    edge_set = set(map(tuple, edges.tolist()))
    self_loops = int(np.sum(edges[:, 0] == edges[:, 1]))

    reciprocal = 0
    for u, v in edge_set:
        if u < v and (v, u) in edge_set:
            reciprocal += 1

    # For this generator, DAG direction should satisfy source > target.
    temporal_violations = int(np.sum(edges[:, 0] <= edges[:, 1]))

    return {
        'self_loops': self_loops,
        'reciprocal_pairs': reciprocal,
        'temporal_violations': temporal_violations,
    }


def build_transfer_matrix(edges: np.ndarray, n_nodes: int) -> csr_matrix:
    out_deg = np.bincount(edges[:, 0], minlength=n_nodes).astype(np.float64)

    rows = edges[:, 0]
    cols = edges[:, 1]

    weights = np.zeros(len(edges), dtype=np.float64)
    nz = out_deg[rows] > 0
    weights[nz] = 1.0 / out_deg[rows[nz]]

    return csr_matrix((weights, (rows, cols)), shape=(n_nodes, n_nodes))


def compute_spectral_radius(A: csr_matrix, temporal_violations: int) -> float:
    # If all edges satisfy source > target, A is strictly lower triangular
    # in node-id order, so all eigenvalues are exactly zero.
    if temporal_violations == 0:
        return 0.0

    if A.nnz == 0:
        return 0.0

    vals, _ = eigs(A.T, k=1, which='LM')
    rho = float(np.max(np.abs(vals)))
    return rho


def add_self_loops(edges: np.ndarray, n_nodes: int, fraction_nodes: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n_pick = max(1, int(n_nodes * fraction_nodes))
    chosen = rng.choice(np.arange(n_nodes), size=n_pick, replace=False)
    loop_edges = np.column_stack([chosen, chosen]).astype(np.int64)
    return np.vstack([edges, loop_edges])


def add_back_edges(edges: np.ndarray, fraction_edges: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n_pick = max(1, int(len(edges) * fraction_edges))
    idx = rng.choice(np.arange(len(edges)), size=n_pick, replace=False)
    picked = edges[idx]
    back = np.column_stack([picked[:, 1], picked[:, 0]]).astype(np.int64)
    return np.vstack([edges, back])


def run_analysis(edges_path: str = DEFAULT_EDGES_PATH):
    os.makedirs(TABLES_DIR, exist_ok=True)
    os.makedirs(PLOTS_DIR, exist_ok=True)

    edges, n_nodes = load_edges(edges_path)

    scenarios: list[tuple[str, np.ndarray]] = [
        ('baseline', edges),
        ('add_self_loops_1pct_nodes', add_self_loops(edges, n_nodes, fraction_nodes=0.01, seed=7)),
        ('add_back_edges_1pct_edges', add_back_edges(edges, fraction_edges=0.01, seed=11)),
        ('add_back_edges_5pct_edges', add_back_edges(edges, fraction_edges=0.05, seed=13)),
    ]

    results: list[ScenarioResult] = []
    for scenario_name, e in scenarios:
        m = structural_metrics(e)
        A = build_transfer_matrix(e, n_nodes)
        rho = compute_spectral_radius(A, m['temporal_violations'])

        results.append(
            ScenarioResult(
                scenario=scenario_name,
                n_nodes=n_nodes,
                n_edges=len(e),
                self_loops=m['self_loops'],
                reciprocal_pairs=m['reciprocal_pairs'],
                temporal_violations=m['temporal_violations'],
                spectral_radius=rho,
                converges_rho_lt_1=bool(rho < 1.0),
            )
        )

    df = pd.DataFrame([r.__dict__ for r in results])
    out_csv = os.path.join(TABLES_DIR, 'loop_impact_scenarios.csv')
    df.to_csv(out_csv, index=False)

    # Plot 1: loop-related violations
    fig, ax = plt.subplots(figsize=(9, 5))
    plot_df = df.melt(
        id_vars=['scenario'],
        value_vars=['self_loops', 'reciprocal_pairs', 'temporal_violations'],
        var_name='metric',
        value_name='count',
    )
    sns.barplot(data=plot_df, x='scenario', y='count', hue='metric', ax=ax, palette='Set2')
    ax.set_title('Loop/Cycle Structural Indicators by Scenario')
    ax.set_xlabel('Scenario')
    ax.set_ylabel('Count')
    ax.tick_params(axis='x', rotation=18)
    ax.legend(title='')
    plt.tight_layout()
    fig.savefig(os.path.join(PLOTS_DIR, 'loop_indicators_by_scenario.png'), dpi=160, bbox_inches='tight')
    fig.savefig(os.path.join(PLOTS_DIR, 'loop_indicators_by_scenario.pdf'), dpi=160, bbox_inches='tight')
    plt.close(fig)

    # Plot 2: spectral radius and convergence threshold
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    sns.barplot(data=df, x='scenario', y='spectral_radius', ax=ax, color='#4c72b0')
    ax.axhline(1.0, color='red', linestyle='--', linewidth=1.2, label='convergence threshold (rho=1)')
    ax.set_title('Spectral Radius of Transfer Matrix by Scenario')
    ax.set_xlabel('Scenario')
    ax.set_ylabel('Spectral radius rho(A^T)')
    ax.tick_params(axis='x', rotation=18)
    ax.legend(loc='upper left')
    plt.tight_layout()
    fig.savefig(os.path.join(PLOTS_DIR, 'spectral_radius_by_scenario.png'), dpi=160, bbox_inches='tight')
    fig.savefig(os.path.join(PLOTS_DIR, 'spectral_radius_by_scenario.pdf'), dpi=160, bbox_inches='tight')
    plt.close(fig)

    print(df.to_string(index=False))
    print(f'Wrote: {out_csv}')
    print(f'Wrote plots in: {PLOTS_DIR}')


if __name__ == '__main__':
    run_analysis()

