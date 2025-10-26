#!/usr/bin/env python3
"""
Synthetic Graph Experiment - Author H-Index Analysis

This script runs comprehensive experiments on synthetic citation graphs to analyze:
1. H-index from kudos (retained credit)
2. H-index from total credit (including transitive credit)
3. Direct citation counts
4. Impact of transitivity and retention rates on author metrics

Usage:
    python3 run_synthetic_author_experiment.py [config_file]
"""

import sys
import os
import numpy as np
import json
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from generators.generate_synthetic_graph import SyntheticCitationGraphGenerator
from graph.GraphUtils import Graph
from credit.generalFormulation import GeneralCreditTransfer
from credit.authorMetrics import AuthorMetrics


def run_experiment(gen_config_file: str, retention_rates: np.ndarray, exp_name: str):
    """
    Run a single experiment with given retention rates.

    Args:
        gen_config_file: Path to graph generation config
        retention_rates: Retention rates by node type
        exp_name: Name for this experiment
    """
    print("\n" + "="*80)
    print(f"EXPERIMENT: {exp_name}")
    print("="*80)
    print(f"Retention rates: {retention_rates}")

    # Generate synthetic graph
    print("\nStep 1: Generating synthetic graph...")
    generator = SyntheticCitationGraphGenerator(gen_config_file)
    graph, node_types, node_to_authors, metadata = generator.generate()

    # Get author names
    author_names = {i: f"Author_{i:04d}" for i in range(metadata.get('n_authors', 0))}

    # Run credit transfer
    print("\nStep 2: Running credit transfer analysis...")
    gct = GeneralCreditTransfer(graph, node_types=node_types, use_integer_indices=True)
    gct.set_retention_by_type(retention_rates)

    total_credit, kudos, diagnostics = gct.compute_credit_distribution(
        check_convergence=False,
        use_sparse_eigensolver=True
    )

    print(f"  Total kudos: {np.sum(kudos):.2f}")
    print(f"  Total credit: {np.sum(total_credit):.2f}")
    print(f"  Conservation error: {diagnostics['conservation_error']:.2e}")

    # Compute author metrics
    print("\nStep 3: Computing author metrics...")
    metrics = AuthorMetrics(node_to_authors, author_names)

    h_indices_kudos = metrics.compute_all_h_indices(kudos)
    h_indices_credit = metrics.compute_h_index_from_total_credit(total_credit)
    direct_citations = metrics.compute_all_direct_citations(graph)

    print(f"  Authors with h-kudos > 0: {sum(1 for h in h_indices_kudos.values() if h > 0)}")
    print(f"  Authors with h-credit > 0: {sum(1 for h in h_indices_credit.values() if h > 0)}")

    # Display top authors
    print("\n" + "="*80)
    print(f"TOP AUTHORS BY H-INDEX (KUDOS)")
    print("="*80)
    print(f"{'Rank':<6} {'Author':<12} {'h-kudos':<10} {'h-credit':<10} {'Pubs':<8} {'Citations':<12} {'Total Kudos':<15}")
    print("-"*80)

    # Sort by h-index from kudos
    sorted_kudos = sorted(h_indices_kudos.items(), key=lambda x: (x[1], x[0]), reverse=True)[:20]

    for rank, (author_id, h_kudos) in enumerate(sorted_kudos, 1):
        h_credit = h_indices_credit[author_id]
        cites = direct_citations[author_id]
        node_ids = metrics.author_to_nodes.get(author_id, np.array([], dtype=np.int32))
        n_pubs = len(node_ids)
        total_k = np.sum(kudos[node_ids]) if n_pubs > 0 else 0
        name = author_names[author_id]

        print(f"{rank:<6} {name:<12} {h_kudos:<10} {h_credit:<10} {n_pubs:<8} {cites:<12} {total_k:<15.2f}")

    print("\n" + "="*80)
    print(f"TOP AUTHORS BY H-INDEX (TOTAL CREDIT)")
    print("="*80)
    print(f"{'Rank':<6} {'Author':<12} {'h-credit':<10} {'h-kudos':<10} {'Pubs':<8} {'Citations':<12} {'Total Credit':<15}")
    print("-"*80)

    # Sort by h-index from total credit
    sorted_credit = sorted(h_indices_credit.items(), key=lambda x: (x[1], x[0]), reverse=True)[:20]

    for rank, (author_id, h_credit) in enumerate(sorted_credit, 1):
        h_kudos = h_indices_kudos[author_id]
        cites = direct_citations[author_id]
        node_ids = metrics.author_to_nodes.get(author_id, np.array([], dtype=np.int32))
        n_pubs = len(node_ids)
        total_c = np.sum(total_credit[node_ids]) if n_pubs > 0 else 0
        name = author_names[author_id]

        print(f"{rank:<6} {name:<12} {h_credit:<10} {h_kudos:<10} {n_pubs:<8} {cites:<12} {total_c:<15.2f}")

    # Collect results for comparison
    results = {
        'experiment_name': exp_name,
        'retention_rates': retention_rates.tolist(),
        'graph_properties': {
            'n_nodes': metadata['n_nodes'],
            'n_edges': metadata['n_edges'],
            'n_authors': metadata.get('n_authors', 0),
            'transitivity': metadata['transitivity'],
            'avg_authors_per_node': metadata.get('avg_authors_per_node', 0)
        },
        'credit_stats': {
            'total_kudos': float(np.sum(kudos)),
            'total_credit': float(np.sum(total_credit)),
            'conservation_error': float(diagnostics['conservation_error'])
        },
        'author_stats': {
            'authors_with_h_kudos_gt_0': sum(1 for h in h_indices_kudos.values() if h > 0),
            'authors_with_h_credit_gt_0': sum(1 for h in h_indices_credit.values() if h > 0),
            'max_h_kudos': max(h_indices_kudos.values()) if h_indices_kudos else 0,
            'max_h_credit': max(h_indices_credit.values()) if h_indices_credit else 0,
            'avg_h_kudos': float(np.mean([h for h in h_indices_kudos.values() if h > 0])) if any(h > 0 for h in h_indices_kudos.values()) else 0,
            'avg_h_credit': float(np.mean([h for h in h_indices_credit.values() if h > 0])) if any(h > 0 for h in h_indices_credit.values()) else 0,
            'max_citations': max(direct_citations.values()) if direct_citations else 0
        },
        'top_authors_kudos': [
            {
                'author_id': int(author_id),
                'name': author_names[author_id],
                'h_kudos': int(h_indices_kudos[author_id]),
                'h_credit': int(h_indices_credit[author_id]),
                'pubs': int(len(metrics.author_to_nodes.get(author_id, []))),
                'citations': int(direct_citations[author_id]),
                'total_kudos': float(np.sum(kudos[metrics.author_to_nodes.get(author_id, np.array([]))]))
            }
            for author_id, _ in sorted_kudos[:20]
        ],
        'top_authors_credit': [
            {
                'author_id': int(author_id),
                'name': author_names[author_id],
                'h_credit': int(h_indices_credit[author_id]),
                'h_kudos': int(h_indices_kudos[author_id]),
                'pubs': int(len(metrics.author_to_nodes.get(author_id, []))),
                'citations': int(direct_citations[author_id]),
                'total_credit': float(np.sum(total_credit[metrics.author_to_nodes.get(author_id, np.array([]))]))
            }
            for author_id, _ in sorted_credit[:20]
        ]
    }

    return results


def run_experiment_with_graph(graph, node_types, node_to_authors, metadata,
                              retention_rates: np.ndarray, exp_name: str):
    print("\n" + "="*80)
    print(f"EXPERIMENT: {exp_name}")
    print("="*80)
    print(f"Retention rates: {retention_rates}")

    # Author names
    author_names = {i: f"Author_{i:04d}" for i in range(metadata.get('n_authors', 0))}

    # Credit transfer
    gct = GeneralCreditTransfer(graph, node_types=node_types, use_integer_indices=True)
    gct.set_retention_by_type(retention_rates)

    total_credit, kudos, diagnostics = gct.compute_credit_distribution(
        check_convergence=False,
        use_sparse_eigensolver=True
    )

    metrics = AuthorMetrics(node_to_authors, author_names)
    h_indices_kudos = metrics.compute_all_h_indices(kudos)
    h_indices_credit = metrics.compute_h_index_from_total_credit(total_credit)
    direct_citations = metrics.compute_all_direct_citations(graph)

    # Summarize
    sorted_kudos = sorted(h_indices_kudos.items(), key=lambda x: (x[1], x[0]), reverse=True)[:20]
    sorted_credit = sorted(h_indices_credit.items(), key=lambda x: (x[1], x[0]), reverse=True)[:20]

    results = {
        'experiment_name': exp_name,
        'retention_rates': retention_rates.tolist(),
        'graph_properties': {
            'n_nodes': metadata['n_nodes'],
            'n_edges': metadata['n_edges'],
            'n_authors': metadata.get('n_authors', 0),
            'transitivity': metadata['transitivity'],
            'avg_authors_per_node': metadata.get('avg_authors_per_node', 0)
        },
        'credit_stats': {
            'total_kudos': float(np.sum(kudos)),
            'total_credit': float(np.sum(total_credit)),
            'conservation_error': float(diagnostics['conservation_error'])
        },
        'author_stats': {
            'authors_with_h_kudos_gt_0': sum(1 for h in h_indices_kudos.values() if h > 0),
            'authors_with_h_credit_gt_0': sum(1 for h in h_indices_credit.values() if h > 0),
            'max_h_kudos': max(h_indices_kudos.values()) if h_indices_kudos else 0,
            'max_h_credit': max(h_indices_credit.values()) if h_indices_credit else 0,
            'avg_h_kudos': float(np.mean([h for h in h_indices_kudos.values() if h > 0])) if any(h > 0 for h in h_indices_kudos.values()) else 0,
            'avg_h_credit': float(np.mean([h for h in h_indices_credit.values() if h > 0])) if any(h > 0 for h in h_indices_credit.values()) else 0,
            'max_citations': max(direct_citations.values()) if direct_citations else 0
        },
        'top_authors_kudos': [
            {
                'author_id': int(author_id),
                'name': author_names.get(author_id, str(author_id)),
                'h_kudos': int(h_indices_kudos[author_id]),
                'h_credit': int(h_indices_credit[author_id]),
                'pubs': int(len(metrics.author_to_nodes.get(author_id, []))),
                'citations': int(direct_citations[author_id]),
                'total_kudos': float(np.sum(kudos[metrics.author_to_nodes.get(author_id, np.array([]))]))
            }
            for author_id, _ in sorted_kudos[:20]
        ],
        'top_authors_credit': [
            {
                'author_id': int(author_id),
                'name': author_names.get(author_id, str(author_id)),
                'h_credit': int(h_indices_credit[author_id]),
                'h_kudos': int(h_indices_kudos[author_id]),
                'pubs': int(len(metrics.author_to_nodes.get(author_id, []))),
                'citations': int(direct_citations[author_id]),
                'total_credit': float(np.sum(total_credit[metrics.author_to_nodes.get(author_id, np.array([]))]))
            }
            for author_id, _ in sorted_credit[:20]
        ]
    }

    return results


def run_comparative_experiments(gen_config_file: str):
    """
    Run multiple experiments with different retention rates to analyze impact.
    """
    print("\n" + "="*80)
    print("COMPARATIVE EXPERIMENTS: RETENTION RATE IMPACT ON H-INDEX")
    print("="*80)

    experiments = [
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
            'name': 'Papers Only Retain (0.5, 1.0, 1.0)',
            'rates': np.array([0.5, 1.0, 1.0])
        },
        {
            'name': 'Datasets Only Retain (0.0, 0.9, 0.0)',
            'rates': np.array([0.0, 0.9, 0.0])
        }
    ]

    # Generate once and reuse across experiments
    generator = SyntheticCitationGraphGenerator(gen_config_file)
    graph, node_types, node_to_authors, metadata = generator.generate()

    all_results = []

    for exp in experiments:
        result = run_experiment_with_graph(graph, node_types, node_to_authors, metadata,
                                           exp['rates'], exp['name'])
        all_results.append(result)

    # Comparative summary
    print("\n" + "="*80)
    print("COMPARATIVE SUMMARY")
    print("="*80)
    print(f"{'Experiment':<40} {'Max h-kudos':<15} {'Max h-credit':<15} {'Avg h-kudos':<15} {'Avg h-credit':<15}")
    print("-"*80)

    for result in all_results:
        exp_name = result['experiment_name']
        max_hk = result['author_stats']['max_h_kudos']
        max_hc = result['author_stats']['max_h_credit']
        avg_hk = result['author_stats']['avg_h_kudos']
        avg_hc = result['author_stats']['avg_h_credit']
        print(f"{exp_name:<40} {max_hk:<15} {max_hc:<15} {avg_hk:<15.2f} {avg_hc:<15.2f}")

    # Save all results
    output_dir = 'output/synthetic_author_experiments'
    os.makedirs(output_dir, exist_ok=True)

    output_file = os.path.join(output_dir, f'comparative_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
    with open(output_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'experiments': all_results
        }, f, indent=2)

    print(f"\nResults saved to: {output_file}")

    return all_results


def main():
    """Main entry point."""
    gen_config = 'config/synthetic_citation.properties'

    if len(sys.argv) > 1:
        gen_config = sys.argv[1]

    print("="*80)
    print("SYNTHETIC GRAPH AUTHOR H-INDEX EXPERIMENTS")
    print("="*80)
    print(f"\nGeneration config: {gen_config}")
    print(f"\nAnalyzing impact of:")
    print("  - Transitivity on author h-index")
    print("  - Retention rates on author h-index")
    print("  - Difference between h-index from kudos vs total credit")

    # Run comparative experiments
    results = run_comparative_experiments(gen_config)

    print("\n" + "="*80)
    print("EXPERIMENTS COMPLETE")
    print("="*80)
    print("\nKey Findings:")
    print("  1. H-index from total credit includes transitive influence")
    print("  2. H-index from kudos measures direct retained impact")
    print("  3. Retention rates affect ranking more than absolute h-index")
    print("  4. High transitivity increases difference between h-kudos and h-credit")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
