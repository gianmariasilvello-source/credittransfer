#!/usr/bin/env python3
"""
Synthetic Graph Ranking Stability Analysis

Compares author rankings across different retention rates to measure:
1. Ranking stability (how much do rankings change?)
2. Kendall's tau correlation between retention strategies
3. Top-20 author comparison across all experiments
4. Separate analysis for h-index from kudos vs total credit

High Kendall's tau = stable rankings (little change with retention rates)
Low Kendall's tau = unstable rankings (significant changes)

Usage:
    python3 experiments/run_ranking_comparison.py [config_file]
"""

import sys
import os
import numpy as np
import json
from datetime import datetime
from scipy.stats import kendalltau
from typing import Dict, List, Tuple

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from generators.generate_synthetic_graph import SyntheticCitationGraphGenerator
from graph.GraphUtils import Graph
from credit.generalFormulation import GeneralCreditTransfer
from credit.authorMetrics import AuthorMetrics


def compute_ranking(h_indices: Dict[int, int], author_names: Dict[int, str]) -> List[Tuple[int, int, str]]:
    """
    Compute ranking from h-indices.

    Returns:
        List of (rank, author_id, h_index, name) sorted by h-index descending
    """
    sorted_authors = sorted(
        [(author_id, h_idx, author_names[author_id]) for author_id, h_idx in h_indices.items()],
        key=lambda x: (x[1], -x[0]),  # Sort by h-index desc, then author_id asc for ties
        reverse=True
    )

    # Add ranks (handle ties)
    ranked = []
    current_rank = 1
    prev_h = None

    for i, (author_id, h_idx, name) in enumerate(sorted_authors):
        if h_idx != prev_h:
            current_rank = i + 1
        ranked.append((current_rank, author_id, h_idx, name))
        prev_h = h_idx

    return ranked


def compute_kendall_tau_for_rankings(ranking1: List[Tuple], ranking2: List[Tuple]) -> float:
    """
    Compute Kendall's tau between two rankings.

    Args:
        ranking1, ranking2: Lists of (rank, author_id, h_index, name)

    Returns:
        Kendall's tau correlation coefficient (-1 to 1)
    """
    # Extract author_id order from both rankings
    order1 = [item[1] for item in ranking1]  # author_id
    order2 = [item[1] for item in ranking2]

    # Create position mapping
    pos1 = {author_id: i for i, author_id in enumerate(order1)}
    pos2 = {author_id: i for i, author_id in enumerate(order2)}

    # Get common authors
    common_authors = set(order1) & set(order2)

    if len(common_authors) < 2:
        return 0.0

    # Create aligned position vectors
    positions1 = [pos1[aid] for aid in sorted(common_authors)]
    positions2 = [pos2[aid] for aid in sorted(common_authors)]

    # Compute Kendall's tau
    tau, p_value = kendalltau(positions1, positions2)

    return tau


def run_single_experiment(generator, retention_rates: np.ndarray, exp_name: str):
    """Run a single experiment and return all metrics."""
    print(f"\n{'='*80}")
    print(f"Running: {exp_name}")
    print(f"Retention rates: {retention_rates}")
    print(f"{'='*80}")

    # Generate graph (reuse same structure)
    graph, node_types, node_to_authors, metadata = generator.generate()

    # Get author names
    n_authors = metadata.get('n_authors', 0)
    author_names = {i: f"Author_{i:04d}" for i in range(n_authors)}

    # Run credit transfer
    gct = GeneralCreditTransfer(graph, node_types=node_types, use_integer_indices=True)
    gct.set_retention_by_type(retention_rates)

    total_credit, kudos, diagnostics = gct.compute_credit_distribution(
        check_convergence=False,
        use_sparse_eigensolver=True
    )

    # Compute author metrics
    metrics = AuthorMetrics(node_to_authors, author_names)

    h_indices_kudos = metrics.compute_all_h_indices(kudos)
    h_indices_credit = metrics.compute_h_index_from_total_credit(total_credit)
    direct_citations = metrics.compute_all_direct_citations(graph)

    # Compute rankings
    ranking_kudos = compute_ranking(h_indices_kudos, author_names)
    ranking_credit = compute_ranking(h_indices_credit, author_names)

    print(f"  ✓ H-index from kudos: max={max(h_indices_kudos.values())}, avg={np.mean(list(h_indices_kudos.values())):.2f}")
    print(f"  ✓ H-index from credit: max={max(h_indices_credit.values())}, avg={np.mean(list(h_indices_credit.values())):.2f}")

    return {
        'name': exp_name,
        'retention_rates': retention_rates,
        'graph': graph,
        'node_types': node_types,
        'node_to_authors': node_to_authors,
        'metadata': metadata,
        'kudos': kudos,
        'total_credit': total_credit,
        'h_indices_kudos': h_indices_kudos,
        'h_indices_credit': h_indices_credit,
        'direct_citations': direct_citations,
        'ranking_kudos': ranking_kudos,
        'ranking_credit': ranking_credit,
        'author_names': author_names
    }


def run_single_experiment_with_graph(graph, node_types, node_to_authors, metadata,
                                     retention_rates: np.ndarray, exp_name: str):
    """Run a single experiment on a pre-generated graph and return all metrics."""
    print(f"\n{'='*80}")
    print(f"Running: {exp_name}")
    print(f"Retention rates: {retention_rates}")
    print(f"{'='*80}")

    # Get author names
    n_authors = metadata.get('n_authors', 0)
    author_names = {i: f"Author_{i:04d}" for i in range(n_authors)}

    # Run credit transfer
    gct = GeneralCreditTransfer(graph, node_types=node_types, use_integer_indices=True)
    gct.set_retention_by_type(retention_rates)

    total_credit, kudos, diagnostics = gct.compute_credit_distribution(
        check_convergence=False,
        use_sparse_eigensolver=True
    )

    # Compute author metrics
    metrics = AuthorMetrics(node_to_authors, author_names)

    h_indices_kudos = metrics.compute_all_h_indices(kudos)
    h_indices_credit = metrics.compute_h_index_from_total_credit(total_credit)
    direct_citations = metrics.compute_all_direct_citations(graph)

    # Compute rankings
    ranking_kudos = compute_ranking(h_indices_kudos, author_names)
    ranking_credit = compute_ranking(h_indices_credit, author_names)

    print(f"  ✓ H-index from kudos: max={max(h_indices_kudos.values()) if h_indices_kudos else 0}, avg={np.mean(list(h_indices_kudos.values())):.2f if h_indices_kudos else 0.0}")
    print(f"  ✓ H-index from credit: max={max(h_indices_credit.values()) if h_indices_credit else 0}, avg={np.mean(list(h_indices_credit.values())):.2f if h_indices_credit else 0.0}")

    return {
        'name': exp_name,
        'retention_rates': retention_rates,
        'graph': graph,
        'node_types': node_types,
        'node_to_authors': node_to_authors,
        'metadata': metadata,
        'kudos': kudos,
        'total_credit': total_credit,
        'h_indices_kudos': h_indices_kudos,
        'h_indices_credit': h_indices_credit,
        'direct_citations': direct_citations,
        'ranking_kudos': ranking_kudos,
        'ranking_credit': ranking_credit,
        'author_names': author_names
    }


def display_top20_comparison(all_results: List[Dict], metric: str = 'kudos'):
    """Display side-by-side top-20 rankings for all experiments."""
    print(f"\n{'='*120}")
    print(f"TOP-20 AUTHOR RANKINGS COMPARISON - H-INDEX FROM {metric.upper()}")
    print(f"{'='*120}")

    # Get experiment names
    exp_names = [r['name'] for r in all_results]

    # Build rank lookup maps for faster access: rank -> (aid, h_idx, name)
    rank_maps: List[Dict[int, Tuple[int, int, str]]] = []
    for result in all_results:
        ranking = result['ranking_kudos'] if metric == 'kudos' else result['ranking_credit']
        rank_map = {}
        for r, aid, h_idx, name in ranking:
            if r <= 20 and r not in rank_map:
                rank_map[r] = (aid, h_idx, name)
        rank_maps.append(rank_map)

    # Print header
    header_parts = [f"{'Rank':<6}"]
    for name in exp_names:
        short_name = name.split('(')[0].strip()[:20]
        header_parts.append(f"{short_name:<25}")
    print(' | '.join(header_parts))
    print('-' * 120)

    # Display top 20 for each experiment
    for rank in range(1, 21):
        row_parts = [f"{rank:<6}"]
        for rank_map in rank_maps:
            entry = "-"
            if rank in rank_map:
                _, h_idx, name = rank_map[rank]
                entry = f"{name[:12]} (h={h_idx})"
            row_parts.append(f"{entry:<25}")
        print(' | '.join(row_parts))


def compute_kendall_tau_matrix(all_results: List[Dict], metric: str = 'kudos'):
    """Compute Kendall's tau correlation matrix between all experiments."""
    n = len(all_results)
    tau_matrix = np.zeros((n, n))

    for i in range(n):
        for j in range(n):
            if metric == 'kudos':
                ranking_i = all_results[i]['ranking_kudos']
                ranking_j = all_results[j]['ranking_kudos']
            else:
                ranking_i = all_results[i]['ranking_credit']
                ranking_j = all_results[j]['ranking_credit']

            tau = compute_kendall_tau_for_rankings(ranking_i, ranking_j)
            tau_matrix[i, j] = tau

    return tau_matrix


def display_kendall_tau_matrix(all_results: List[Dict], tau_matrix: np.ndarray, metric: str):
    """Display Kendall's tau correlation matrix."""
    print(f"\n{'='*100}")
    print(f"KENDALL'S TAU CORRELATION MATRIX - H-INDEX FROM {metric.upper()}")
    print(f"{'='*100}")
    print("Values close to 1.0 = rankings are very similar (stable)")
    print("Values close to 0.0 = rankings are uncorrelated (unstable)")
    print("Values close to -1.0 = rankings are reversed\n")

    exp_names = [r['name'].split('(')[0].strip()[:20] for r in all_results]

    # Print header
    header = f"{'':25}"
    for name in exp_names:
        header += f" {name[:8]:<8}"
    print(header)
    print('-' * 100)

    # Print matrix
    for i, name in enumerate(exp_names):
        row = f"{name:<25}"
        for j in range(len(exp_names)):
            row += f" {tau_matrix[i, j]:8.3f}"
        print(row)


def analyze_ranking_changes(all_results: List[Dict], metric: str = 'kudos'):
    """Analyze how individual authors change rankings."""
    print(f"\n{'='*100}")
    print(f"RANKING VOLATILITY ANALYSIS - H-INDEX FROM {metric.upper()}")
    print(f"{'='*100}")

    # Track each author's ranks across experiments
    author_ranks = {}  # author_id -> list of ranks

    for result in all_results:
        if metric == 'kudos':
            ranking = result['ranking_kudos']
        else:
            ranking = result['ranking_credit']

        for rank, author_id, h_idx, name in ranking:
            if author_id not in author_ranks:
                author_ranks[author_id] = {
                    'name': name,
                    'ranks': [],
                    'h_values': []
                }
            author_ranks[author_id]['ranks'].append(rank)
            author_ranks[author_id]['h_values'].append(h_idx)

    # Calculate rank volatility for each author
    volatilities = []
    for author_id, data in author_ranks.items():
        if len(data['ranks']) >= 3:  # Must appear in at least 3 experiments
            ranks = np.array(data['ranks'])
            std_rank = np.std(ranks)
            mean_rank = np.mean(ranks)
            range_rank = np.max(ranks) - np.min(ranks)

            volatilities.append({
                'author_id': author_id,
                'name': data['name'],
                'mean_rank': mean_rank,
                'std_rank': std_rank,
                'range_rank': range_rank,
                'min_rank': np.min(ranks),
                'max_rank': np.max(ranks),
                'ranks': data['ranks'],
                'h_values': data['h_values']
            })

    # Sort by volatility (std deviation of ranks)
    volatilities.sort(key=lambda x: x['std_rank'], reverse=True)

    # Display most volatile (unstable) rankings
    print(f"\nMOST VOLATILE RANKINGS (Top 10 - rankings change most across retention rates):")
    print(f"{'Author':<15} {'Mean Rank':<12} {'Std Dev':<10} {'Range':<10} {'Min→Max':<15}")
    print('-' * 100)

    for v in volatilities[:10]:
        print(f"{v['name']:<15} {v['mean_rank']:<12.1f} {v['std_rank']:<10.2f} "
              f"{v['range_rank']:<10.0f} {v['min_rank']:.0f}→{v['max_rank']:.0f}")

    # Display most stable rankings
    print(f"\nMOST STABLE RANKINGS (Top 10 - rankings stay consistent):")
    print(f"{'Author':<15} {'Mean Rank':<12} {'Std Dev':<10} {'Range':<10} {'Ranks Across Experiments'}")
    print('-' * 100)

    stable = sorted(volatilities, key=lambda x: x['std_rank'])[:10]
    for v in stable:
        ranks_str = ', '.join(map(str, [int(r) for r in v['ranks']]))
        print(f"{v['name']:<15} {v['mean_rank']:<12.1f} {v['std_rank']:<10.2f} "
              f"{v['range_rank']:<10.0f} [{ranks_str}]")


def save_comparison_results(all_results: List[Dict],
                           tau_matrix_kudos: np.ndarray,
                           tau_matrix_credit: np.ndarray,
                           output_dir: str):
    """Save detailed comparison results to JSON."""
    os.makedirs(output_dir, exist_ok=True)

    # Prepare data for JSON
    comparison_data = {
        'timestamp': datetime.now().isoformat(),
        'experiments': [],
        'kendall_tau_kudos': tau_matrix_kudos.tolist(),
        'kendall_tau_credit': tau_matrix_credit.tolist(),
        'experiment_names': [r['name'] for r in all_results]
    }

    for result in all_results:
        exp_data = {
            'name': result['name'],
            'retention_rates': result['retention_rates'].tolist(),
            'top_20_kudos': [
                {
                    'rank': int(rank),
                    'author_id': int(aid),
                    'h_index': int(h_idx),
                    'name': name
                }
                for rank, aid, h_idx, name in result['ranking_kudos'][:20]
            ],
            'top_20_credit': [
                {
                    'rank': int(rank),
                    'author_id': int(aid),
                    'h_index': int(h_idx),
                    'name': name
                }
                for rank, aid, h_idx, name in result['ranking_credit'][:20]
            ]
        }
        comparison_data['experiments'].append(exp_data)

    output_file = os.path.join(output_dir, f'ranking_comparison_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
    with open(output_file, 'w') as f:
        json.dump(comparison_data, f, indent=2)

    print(f"\nComparison results saved to: {output_file}")


def main():
    """Main entry point."""
    gen_config = 'config/synthetic_citation.properties'

    if len(sys.argv) > 1:
        gen_config = sys.argv[1]

    print("="*100)
    print("AUTHOR RANKING COMPARISON ACROSS RETENTION RATES")
    print("="*100)
    print(f"\nConfiguration: {gen_config}")
    print("\nAnalyzing:")
    print("  1. Top-20 rankings for each retention strategy")
    print("  2. Kendall's tau correlation between strategies")
    print("  3. Ranking volatility (which authors' ranks change most)")
    print("  4. Separate analysis for h-kudos and h-credit")

    # Initialize generator (use same graph structure for all experiments)
    generator = SyntheticCitationGraphGenerator(gen_config)

    # Generate once and reuse
    graph, node_types, node_to_authors, metadata = generator.generate()

    # Define retention strategies to compare
    strategies = [
        {
            'name': 'Direct Citations Only (1.0, 1.0, 1.0)',
            'rates': np.array([1.0, 1.0, 1.0])
        },
        {
            'name': 'High Retention (0.8, 0.9, 0.9)',
            'rates': np.array([0.8, 0.9, 0.9])
        },
        {
            'name': 'Medium Retention (0.5, 0.7, 0.7)',
            'rates': np.array([0.5, 0.7, 0.7])
        },
        {
            'name': 'Low Retention (0.2, 0.5, 0.5)',
            'rates': np.array([0.2, 0.5, 0.5])
        },
        {
            'name': 'Papers Only (0.5, 1.0, 1.0)',
            'rates': np.array([0.5, 1.0, 1.0])
        },
        {
            'name': 'Datasets Only (0.0, 0.9, 0.0)',
            'rates': np.array([0.0, 0.9, 0.0])
        }
    ]

    # Run all experiments
    all_results = []
    for strategy in strategies:
        result = run_single_experiment_with_graph(graph, node_types, node_to_authors, metadata,
                                                  strategy['rates'], strategy['name'])
        all_results.append(result)

    # Display top-20 comparisons
    display_top20_comparison(all_results, metric='kudos')
    display_top20_comparison(all_results, metric='credit')

    # Compute and display Kendall's tau matrices
    tau_matrix_kudos = compute_kendall_tau_matrix(all_results, metric='kudos')
    tau_matrix_credit = compute_kendall_tau_matrix(all_results, metric='credit')

    display_kendall_tau_matrix(all_results, tau_matrix_kudos, metric='kudos')
    display_kendall_tau_matrix(all_results, tau_matrix_credit, metric='credit')

    # Analyze ranking changes
    analyze_ranking_changes(all_results, metric='kudos')
    analyze_ranking_changes(all_results, metric='credit')

    # Summary statistics
    print(f"\n{'='*100}")
    print("SUMMARY STATISTICS")
    print(f"{'='*100}")

    # Average Kendall's tau (excluding diagonal)
    n = len(all_results)
    mask = ~np.eye(n, dtype=bool)
    avg_tau_kudos = np.mean(tau_matrix_kudos[mask])
    avg_tau_credit = np.mean(tau_matrix_credit[mask])

    print(f"\nAverage Kendall's Tau (across all strategy pairs):")
    print(f"  H-index from kudos:        τ = {avg_tau_kudos:.3f}")
    print(f"  H-index from total credit: τ = {avg_tau_credit:.3f}")

    if avg_tau_kudos > 0.8:
        stability_kudos = "VERY STABLE"
    elif avg_tau_kudos > 0.6:
        stability_kudos = "MODERATELY STABLE"
    elif avg_tau_kudos > 0.4:
        stability_kudos = "SOMEWHAT UNSTABLE"
    else:
        stability_kudos = "VERY UNSTABLE"

    if avg_tau_credit > 0.8:
        stability_credit = "VERY STABLE"
    elif avg_tau_credit > 0.6:
        stability_credit = "MODERATELY STABLE"
    elif avg_tau_credit > 0.4:
        stability_credit = "SOMEWHAT UNSTABLE"
    else:
        stability_credit = "VERY UNSTABLE"

    print(f"\nRanking Stability:")
    print(f"  H-index from kudos:        {stability_kudos}")
    print(f"  H-index from total credit: {stability_credit}")

    print(f"\nInterpretation:")
    print(f"  • Kendall's τ close to 1.0 = rankings are similar across retention rates")
    print(f"  • Kendall's τ close to 0.0 = rankings are uncorrelated (very different)")
    print(f"  • Higher τ = retention rate choice matters less for author rankings")
    print(f"  • Lower τ = retention rate choice significantly affects rankings")

    # Save results
    output_dir = 'output/ranking_comparison'
    save_comparison_results(all_results, tau_matrix_kudos, tau_matrix_credit, output_dir)

    print(f"\n{'='*100}")
    print("ANALYSIS COMPLETE")
    print(f"{'='*100}\n")


if __name__ == "__main__":
    main()
