#!/usr/bin/env python3
"""
Example: Load a graph from edgelist and run credit transfer analysis

This demonstrates how to efficiently load large graphs from edgelist files
instead of dense adjacency matrices.

Usage:
    python3 examples/load_edgelist_example.py
"""

import sys
import os
import numpy as np

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from graph.GraphUtils import Graph
from credit.generalFormulation import GeneralCreditTransfer
from credit.authorMetrics import AuthorMetrics


def load_graph_from_edgelist_demo():
    """Demonstrate loading a graph from edgelist and running analysis."""

    print("="*80)
    print("EDGELIST LOADING EXAMPLE")
    print("="*80)

    # First, generate a small test graph if it doesn't exist
    edgelist_path = 'data/synthetic_small/small_citation_edges.txt'
    node_types_path = 'data/synthetic_small/small_citation_node_types.txt'
    authors_path = 'data/synthetic_small/small_citation_authors.txt'

    if not os.path.exists(edgelist_path):
        print(f"\nGenerating test graph first...")
        print("Run: python3 generators/generate_synthetic_graph.py config/synthetic_small.properties\n")
        return

    # Step 1: Load graph from edgelist (FAST!)
    print("\n1. Loading graph from edgelist...")
    graph = Graph.from_edgelist(edgelist_path, is_directed=True)
    print(f"   ✓ Loaded {len(graph.nodes())} nodes, {len(graph.edges())} edges")

    # Step 2: Load node types
    print("\n2. Loading node types...")
    node_types = []
    with open(node_types_path, 'r') as f:
        for line in f:
            if line.startswith('#'):
                continue
            parts = line.strip().split()
            if len(parts) == 2:
                node_types.append(int(parts[1]))
    node_types = np.array(node_types)
    print(f"   ✓ Loaded {len(node_types)} node types")

    # Step 3: Load authors
    print("\n3. Loading author mappings...")
    node_to_authors = {}
    max_author_id = -1
    with open(authors_path, 'r') as f:
        for line in f:
            if line.startswith('#'):
                continue
            parts = line.strip().split()
            if len(parts) >= 2:
                node_id = int(parts[0])
                author_ids = [int(x) for x in parts[1:]]
                node_to_authors[node_id] = author_ids
                if author_ids:
                    max_author_id = max(max_author_id, max(author_ids))

    author_names = {i: f"Author_{i:04d}" for i in range(max_author_id + 1)}
    print(f"   ✓ Loaded {len(node_to_authors)} author mappings")
    print(f"   ✓ Total unique authors: {max_author_id + 1}")

    # Step 4: Run credit transfer analysis
    print("\n4. Running credit transfer analysis...")
    retention_rates = np.array([0.5, 0.7, 0.7])  # Papers, Datasets, Software
    print(f"   Retention rates: {retention_rates}")

    gct = GeneralCreditTransfer(graph, node_types=node_types, use_integer_indices=True)
    gct.set_retention_by_type(retention_rates)

    total_credit, kudos, diagnostics = gct.compute_credit_distribution(
        check_convergence=False,
        use_sparse_eigensolver=True
    )

    print(f"   ✓ Total kudos: {np.sum(kudos):.2f}")
    print(f"   ✓ Total credit: {np.sum(total_credit):.2f}")
    print(f"   ✓ Conservation error: {diagnostics['conservation_error']:.2e}")

    # Step 5: Compute author metrics
    print("\n5. Computing author h-indices...")
    metrics = AuthorMetrics(node_to_authors, author_names)

    h_indices_kudos = metrics.compute_all_h_indices(kudos)
    h_indices_credit = metrics.compute_h_index_from_total_credit(total_credit)
    direct_citations = metrics.compute_all_direct_citations(graph)

    # Step 6: Display top authors
    print("\n6. Top 10 Authors by H-Index (from kudos):")
    print(f"{'Rank':<6} {'Author':<15} {'h-kudos':<10} {'h-credit':<10} {'Pubs':<8} {'Citations':<10}")
    print("-"*80)

    sorted_authors = sorted(h_indices_kudos.items(), key=lambda x: (x[1], x[0]), reverse=True)[:10]

    for rank, (author_id, h_kudos) in enumerate(sorted_authors, 1):
        h_credit = h_indices_credit[author_id]
        citations = direct_citations[author_id]
        n_pubs = len(metrics.author_to_nodes.get(author_id, []))
        name = author_names[author_id]

        print(f"{rank:<6} {name:<15} {h_kudos:<10} {h_credit:<10} {n_pubs:<8} {citations:<10}")

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Graph loaded from edgelist: {edgelist_path}")
    print(f"Nodes: {len(graph.nodes())}, Edges: {len(graph.edges())}")
    print(f"Authors: {max_author_id + 1}")
    print(f"Retention strategy: Papers={retention_rates[0]}, Datasets={retention_rates[1]}, Software={retention_rates[2]}")
    print(f"Top author: {sorted_authors[0][1]} with h-index={sorted_authors[0][0]}")
    print("="*80)

    print("\n✅ Edgelist loading successful!")
    print("\nKey benefits:")
    print("  • Fast loading (no matrix parsing)")
    print("  • Memory efficient (only stores edges)")
    print("  • Scalable to millions of edges")
    print("  • Git-friendly (small file sizes)")


if __name__ == "__main__":
    load_graph_from_edgelist_demo()

