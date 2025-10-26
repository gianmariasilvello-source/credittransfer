#!/usr/bin/env python3
"""
Run Complete Synthetic Graph Workflow

This script:
1. Generates a synthetic citation graph
2. Runs credit transfer analysis
3. Displays results

Usage:
    python3 run_synthetic_workflow.py [generation_config] [analysis_config]

    If no configs specified, uses:
      - config/synthetic_citation.properties (generation)
      - config/run_synthetic.properties (analysis)
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from generators.generate_synthetic_graph import SyntheticCitationGraphGenerator
from graph.GraphUtils import Graph
from credit.generalFormulation import GeneralCreditTransfer
import numpy as np
import json


def load_synthetic_graph(data_dir: str, prefix: str):
    """Load synthetic graph from files."""
    print(f"\nLoading synthetic graph from {data_dir}/...")

    # Load adjacency matrix
    adj_file = os.path.join(data_dir, f'{prefix}_adjacency.txt')
    matrix = []
    with open(adj_file, 'r') as f:
        for line in f:
            if line.startswith('#'):
                continue
            row = [int(x) for x in line.strip().split()]
            matrix.append(row)

    n = len(matrix)
    nodes = list(range(n))

    # Load node types
    types_file = os.path.join(data_dir, f'{prefix}_node_types.txt')
    node_types = []
    with open(types_file, 'r') as f:
        for line in f:
            if line.startswith('#'):
                continue
            parts = line.strip().split()
            if len(parts) == 2:
                node_types.append(int(parts[1]))

    node_types = np.array(node_types, dtype=np.int32)

    # Build graph
    graph = Graph.from_matrix(nodes, matrix, is_directed=True)

    # Load metadata
    metadata_file = os.path.join(data_dir, f'{prefix}_metadata.json')
    with open(metadata_file, 'r') as f:
        metadata = json.load(f)

    print(f"  Loaded: {len(nodes)} nodes, {len(graph.edges())} edges")

    return graph, node_types, metadata


def run_credit_transfer(graph, node_types, retention_rates):
    """Run credit transfer analysis."""
    print("\nRunning credit transfer analysis...")

    gct = GeneralCreditTransfer(graph, node_types=node_types, use_integer_indices=True)
    gct.set_retention_by_type(retention_rates)

    total_credit, kudos, diagnostics = gct.compute_credit_distribution(
        check_convergence=False,
        use_sparse_eigensolver=True
    )

    print(f"  Total kudos: {np.sum(kudos):.2f}")
    print(f"  Mean kudos: {np.mean(kudos):.4f}")
    print(f"  Max kudos: {np.max(kudos):.4f}")
    print(f"  Conservation error: {diagnostics['conservation_error']:.2e}")

    return total_credit, kudos, diagnostics


def display_top_nodes(kudos, node_types, type_names, top_k=20):
    """Display top nodes by kudos."""
    print(f"\n{'='*80}")
    print(f"TOP {top_k} NODES BY KUDOS")
    print(f"{'='*80}")
    print(f"{'Rank':<6} {'Node ID':<10} {'Type':<12} {'Kudos':<15}")
    print(f"{'-'*80}")

    # Get top nodes
    top_indices = np.argsort(kudos)[::-1][:top_k]

    for rank, idx in enumerate(top_indices, 1):
        node_type = node_types[idx]
        type_name = type_names.get(node_type, f'type_{node_type}')
        print(f"{rank:<6} {idx:<10} {type_name:<12} {kudos[idx]:<15.4f}")


def display_summary(metadata, kudos, node_types, type_names):
    """Display summary statistics."""
    print(f"\n{'='*80}")
    print(f"SYNTHETIC GRAPH SUMMARY")
    print(f"{'='*80}")
    print(f"\nGraph Properties:")
    print(f"  Nodes: {metadata['n_nodes']}")
    print(f"  Edges: {metadata['n_edges']}")
    print(f"  Avg in-degree: {metadata['avg_in_degree']:.2f}")
    print(f"  Avg out-degree: {metadata['avg_out_degree']:.2f}")
    print(f"  Max in-degree: {metadata['max_in_degree']}")
    print(f"  Max out-degree: {metadata['max_out_degree']}")
    print(f"  Transitivity: {metadata['transitivity']:.3f}")

    print(f"\nType Distribution:")
    for type_name, count in metadata['type_distribution'].items():
        print(f"  {type_name}: {count} ({100*count/metadata['n_nodes']:.1f}%)")

    print(f"\nEdges by Generation Mechanism:")
    for mechanism, count in metadata['edges_by_mechanism'].items():
        print(f"  {mechanism}: {count}")

    print(f"\nKudos Distribution:")
    for i, type_name in type_names.items():
        type_mask = node_types == i
        type_kudos = kudos[type_mask]
        if len(type_kudos) > 0:
            print(f"  {type_name}:")
            print(f"    Mean: {np.mean(type_kudos):.4f}")
            print(f"    Median: {np.median(type_kudos):.4f}")
            print(f"    Max: {np.max(type_kudos):.4f}")
            print(f"    Total: {np.sum(type_kudos):.2f}")


def main():
    """Main workflow."""
    # Default config files
    gen_config = 'config/synthetic_citation.properties'
    analysis_config = 'config/run_synthetic.properties'

    if len(sys.argv) > 1:
        gen_config = sys.argv[1]
    if len(sys.argv) > 2:
        analysis_config = sys.argv[2]

    print("="*80)
    print("SYNTHETIC CITATION GRAPH WORKFLOW")
    print("="*80)

    # Step 1: Generate synthetic graph
    print(f"\nStep 1: Generating synthetic graph...")
    print(f"  Config: {gen_config}")

    generator = SyntheticCitationGraphGenerator(gen_config)
    graph, node_types, metadata = generator.generate()
    generator.save_to_files(graph, node_types, metadata)

    # Get type names
    type_names = generator.config['type_names']

    # Step 2: Load and analyze
    print(f"\nStep 2: Running credit transfer analysis...")

    data_dir = generator.config['output_dir']
    prefix = generator.config['output_prefix']

    # Reload to verify serialization works
    graph, node_types, metadata = load_synthetic_graph(data_dir, prefix)

    # Set retention rates
    retention_rates = np.array([0.2, 0.9, 0.7])  # Papers, Datasets, Software

    # Run analysis
    total_credit, kudos, diagnostics = run_credit_transfer(graph, node_types, retention_rates)

    # Step 3: Display results
    display_top_nodes(kudos, node_types, type_names, top_k=20)
    display_summary(metadata, kudos, node_types, type_names)

    print("\n" + "="*80)
    print("WORKFLOW COMPLETE")
    print("="*80)
    print(f"\nGenerated files in: {data_dir}/")
    print(f"  - {prefix}_adjacency.txt")
    print(f"  - {prefix}_node_types.txt")
    print(f"  - {prefix}_metadata.json")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()

