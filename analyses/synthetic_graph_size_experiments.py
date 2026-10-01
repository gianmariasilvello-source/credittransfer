#!/usr/bin/env python3
"""Run synthetic graph size experiments and generate report artifacts."""

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

PROJECT_ROOT = str(Path(__file__).resolve().parents[1])
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from generators.generate_synthetic_graph import SyntheticCitationGraphGenerator


@dataclass
class ExperimentConfig:
    label: str
    config_relpath: str


EXPERIMENTS = [
    ExperimentConfig(label='Small (100)', config_relpath='config/synthetic_small.properties'),
    ExperimentConfig(label='Medium (1K)', config_relpath='config/synthetic_citation.properties'),
    ExperimentConfig(label='Large (10K)', config_relpath='config/synthetic_10K.properties'),
]


sns.set_theme(style='whitegrid', font_scale=1.0)


def _ensure_dirs(base_output_dir: str) -> tuple[str, str]:
    tables_dir = os.path.join(base_output_dir, 'tables')
    plots_dir = os.path.join(base_output_dir, 'plots')
    os.makedirs(tables_dir, exist_ok=True)
    os.makedirs(plots_dir, exist_ok=True)
    return tables_dir, plots_dir


def _safe_div(num: float, den: float) -> float:
    return num / den if den else 0.0


def _run_one_experiment(exp: ExperimentConfig) -> tuple[dict[str, Any], pd.DataFrame]:
    config_path = cast(str, os.path.join(PROJECT_ROOT, exp.config_relpath))
    generator = SyntheticCitationGraphGenerator(config_path)

    graph, node_types, node_to_authors, metadata = generator.generate()
    generator.save_to_files(graph, node_types, node_to_authors, metadata)

    n_nodes = int(metadata['n_nodes'])
    n_edges = int(metadata['n_edges'])
    density = _safe_div(n_edges, n_nodes * (n_nodes - 1))

    type_distribution = metadata.get('type_distribution', {})
    type_df = pd.DataFrame([
        {
            'experiment': exp.label,
            'type': type_name,
            'count': int(count),
            'pct': _safe_div(int(count), n_nodes) * 100.0,
        }
        for type_name, count in type_distribution.items()
    ])

    row = {
        'experiment': exp.label,
        'config': exp.config_relpath,
        'n_nodes': n_nodes,
        'n_edges': n_edges,
        'density': density,
        'avg_in_degree': float(metadata['avg_in_degree']),
        'avg_out_degree': float(metadata['avg_out_degree']),
        'max_in_degree': int(metadata['max_in_degree']),
        'max_out_degree': int(metadata['max_out_degree']),
        'transitivity': float(metadata['transitivity']),
        'n_types': int(len(type_distribution)),
        'n_authors': int(metadata.get('n_authors', 0)),
        'avg_authors_per_node': float(metadata.get('avg_authors_per_node', 0.0)),
        'community_modularity_proxy': int(metadata.get('config', {}).get('n_communities', 0)),
        'seed': generator.config.get('seed'),
    }

    return row, type_df


def _plot_nodes_edges(summary_df: pd.DataFrame, plots_dir: str):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))

    sns.barplot(data=summary_df, x='experiment', y='n_nodes', ax=axes[0], color='#4c72b0')
    axes[0].set_title('Nodes by Graph Size')
    axes[0].set_xlabel('')
    axes[0].set_ylabel('Nodes')

    sns.barplot(data=summary_df, x='experiment', y='n_edges', ax=axes[1], color='#55a868')
    axes[1].set_title('Edges by Graph Size')
    axes[1].set_xlabel('')
    axes[1].set_ylabel('Edges')

    plt.tight_layout()
    fig.savefig(os.path.join(plots_dir, 'nodes_edges_by_size.png'), dpi=160, bbox_inches='tight')
    fig.savefig(os.path.join(plots_dir, 'nodes_edges_by_size.pdf'), dpi=160, bbox_inches='tight')
    plt.close(fig)


def _plot_degree_transitivity(summary_df: pd.DataFrame, plots_dir: str):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))

    degree_df = summary_df.melt(
        id_vars=['experiment'],
        value_vars=['avg_in_degree', 'avg_out_degree'],
        var_name='metric',
        value_name='value',
    )
    sns.barplot(data=degree_df, x='experiment', y='value', hue='metric', ax=axes[0], palette='Set2')
    axes[0].set_title('Average Degree by Graph Size')
    axes[0].set_xlabel('')
    axes[0].set_ylabel('Average degree')
    axes[0].legend(title='')

    sns.lineplot(data=summary_df, x='n_nodes', y='transitivity', marker='o', linewidth=2.2, ax=axes[1])
    axes[1].set_title('Transitivity vs Graph Size')
    axes[1].set_xlabel('Nodes')
    axes[1].set_ylabel('Transitivity')
    axes[1].set_xscale('log')

    plt.tight_layout()
    fig.savefig(os.path.join(plots_dir, 'degree_transitivity_by_size.png'), dpi=160, bbox_inches='tight')
    fig.savefig(os.path.join(plots_dir, 'degree_transitivity_by_size.pdf'), dpi=160, bbox_inches='tight')
    plt.close(fig)


def _plot_type_mix(type_df: pd.DataFrame, plots_dir: str):
    pivot = type_df.pivot_table(index='experiment', columns='type', values='pct', fill_value=0.0)
    fig, ax = plt.subplots(figsize=(8.5, 5.0))

    bottom = np.zeros(len(pivot))
    x = np.arange(len(pivot.index))
    for col in pivot.columns:
        vals = pivot[col].values
        ax.bar(x, vals, bottom=bottom, label=col)
        bottom += vals

    ax.set_xticks(x)
    ax.set_xticklabels(pivot.index)
    ax.set_ylabel('Type share (%)')
    ax.set_title('Node Type Composition by Graph Size')
    ax.legend(title='Type', loc='best')

    plt.tight_layout()
    fig.savefig(os.path.join(plots_dir, 'type_composition_by_size.png'), dpi=160, bbox_inches='tight')
    fig.savefig(os.path.join(plots_dir, 'type_composition_by_size.pdf'), dpi=160, bbox_inches='tight')
    plt.close(fig)


def run(base_output_dir: str):
    tables_dir, plots_dir = _ensure_dirs(base_output_dir)

    summary_rows = []
    type_dfs = []

    for exp in EXPERIMENTS:
        print(f'Running experiment: {exp.label} ({exp.config_relpath})')
        row, type_df = _run_one_experiment(exp)
        summary_rows.append(row)
        type_dfs.append(type_df)

    summary_df = pd.DataFrame(summary_rows).sort_values('n_nodes').reset_index(drop=True)
    if not type_dfs:
        raise RuntimeError('No experiment outputs were generated.')
    type_df = cast(pd.DataFrame, pd.concat(type_dfs, ignore_index=True))

    summary_csv = os.path.join(tables_dir, 'synthetic_graph_size_summary.csv')
    type_csv = os.path.join(tables_dir, 'synthetic_graph_type_distribution.csv')
    summary_df.to_csv(summary_csv, index=False)
    type_df.to_csv(type_csv, index=False)

    _plot_nodes_edges(summary_df, plots_dir)
    _plot_degree_transitivity(summary_df, plots_dir)
    _plot_type_mix(type_df, plots_dir)

    print('Saved:')
    print(f'  {summary_csv}')
    print(f'  {type_csv}')
    print(f'  {plots_dir}')


def main():
    output_dir = cast(str, os.path.join(PROJECT_ROOT, 'analyses', 'synthetic_size_report'))
    run(output_dir)


if __name__ == '__main__':
    main()

