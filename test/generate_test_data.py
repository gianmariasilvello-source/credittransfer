"""
Generate test data files for credit transfer analysis.

This script creates synthetic graph data for testing the credit runner.
"""

import sys
import os
import numpy as np
import argparse


def generate_citation_graph(n_nodes: int, edge_probability: float = 0.1,
                            type_distribution: list = None) -> tuple:
    """
    Generate a random citation graph (DAG).

    Args:
        n_nodes: Number of nodes
        edge_probability: Probability of edge between nodes
        type_distribution: List of (type_id, probability) tuples or None for default
                          Example: [(0, 0.5), (1, 0.3), (2, 0.2)] means
                          50% type 0, 30% type 1, 20% type 2

    Returns:
        Tuple of (adjacency_matrix, node_types)
    """
    adj_matrix = np.zeros((n_nodes, n_nodes), dtype=int)

    # Create edges only from lower to higher indices (ensures DAG)
    for i in range(n_nodes):
        for j in range(i + 1, n_nodes):
            if np.random.random() < edge_probability:
                adj_matrix[i, j] = 1

    # Assign node types
    if type_distribution is None:
        # Default: 80% papers (type 0), 20% datasets (type 1)
        type_distribution = [(0, 0.8), (1, 0.2)]

    # Extract types and probabilities
    types = [t[0] for t in type_distribution]
    probs = [t[1] for t in type_distribution]

    # Normalize probabilities if they don't sum to 1
    prob_sum = sum(probs)
    if abs(prob_sum - 1.0) > 1e-6:
        probs = [p / prob_sum for p in probs]

    node_types = np.random.choice(types, size=n_nodes, p=probs)

    return adj_matrix, node_types


def generate_authors(n_nodes: int, n_authors: int,
                     avg_authors_per_paper: int = 3) -> dict:
    """
    Generate random author assignments.

    Args:
        n_nodes: Number of nodes (papers/datasets)
        n_authors: Number of unique authors
        avg_authors_per_paper: Average number of authors per paper

    Returns:
        Dictionary mapping node_id -> list of author_ids
    """
    node_to_authors = {}

    for node_id in range(n_nodes):
        # Random number of authors (Poisson distribution)
        n_paper_authors = np.random.poisson(avg_authors_per_paper)
        n_paper_authors = max(1, min(n_paper_authors, n_authors))  # At least 1, at most all

        # Randomly select authors
        authors = np.random.choice(n_authors, size=n_paper_authors, replace=False)
        node_to_authors[node_id] = sorted(authors.tolist())

    return node_to_authors


def save_adjacency_matrix(filename: str, adj_matrix: np.ndarray):
    """Save adjacency matrix to file."""
    with open(filename, 'w') as f:
        f.write("# Adjacency matrix (space-separated)\n")
        f.write(f"# Generated graph: {adj_matrix.shape[0]} nodes, "
                f"{np.sum(adj_matrix)} edges\n")
        for row in adj_matrix:
            f.write(" ".join(map(str, row)) + "\n")
    print(f"Saved adjacency matrix to {filename}")


def save_node_types(filename: str, node_types: np.ndarray):
    """Save node types to file."""
    with open(filename, 'w') as f:
        f.write("# Node types (node_id node_type)\n")
        f.write("# Type 0 = paper, Type 1 = dataset\n")
        for node_id, node_type in enumerate(node_types):
            f.write(f"{node_id} {node_type}\n")
    print(f"Saved node types to {filename}")


def save_authors(filename: str, node_to_authors: dict):
    """Save author assignments to file."""
    with open(filename, 'w') as f:
        f.write("# Authors per node (node_id author_id1 author_id2 ...)\n")
        for node_id in sorted(node_to_authors.keys()):
            authors = node_to_authors[node_id]
            f.write(f"{node_id} " + " ".join(map(str, authors)) + "\n")
    print(f"Saved authors to {filename}")


def save_author_names(filename: str, n_authors: int):
    """Save synthetic author names to file."""
    first_names = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Henry",
                   "Ivy", "Jack", "Kate", "Leo", "Mary", "Noah", "Olivia", "Paul"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
                  "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez"]

    with open(filename, 'w') as f:
        f.write("# Author names (author_id author_name)\n")
        for author_id in range(n_authors):
            first = first_names[author_id % len(first_names)]
            last = last_names[author_id % len(last_names)]
            suffix = f" {author_id // (len(first_names) * len(last_names))}" if author_id >= (len(first_names) * len(last_names)) else ""
            f.write(f"{author_id} {first} {last}{suffix}\n")
    print(f"Saved author names to {filename}")


def generate_config(filename: str, data_prefix: str, n_nodes: int,
                   type_config: list = None):
    """
    Generate configuration file for the data.

    Args:
        filename: Output configuration file path
        data_prefix: Prefix for data files
        n_nodes: Number of nodes in graph
        type_config: List of (type_id, type_name, retention_rate) tuples
                    Example: [(0, 'paper', 0.2), (1, 'dataset', 0.9)]
    """
    if type_config is None:
        type_config = [(0, 'paper', 0.2), (1, 'dataset', 0.9)]

    # Build retention rates section
    num_types = len(type_config)
    retention_lines = []
    for type_id, type_name, retention_rate in type_config:
        retention_lines.append(f"type_{type_id}_retention = {retention_rate}")

    # Build type names section
    type_name_lines = []
    for type_id, type_name, retention_rate in type_config:
        type_name_lines.append(f"type_{type_id}_name = {type_name}")

    config_content = f"""# Auto-generated configuration file
# Graph with {n_nodes} nodes

[input]
adjacency_matrix_file = data/{data_prefix}_adjacency.txt
node_ids_file = data/{data_prefix}_nodes.txt
authors_file = data/{data_prefix}_authors.txt
author_names_file = data/{data_prefix}_author_names.txt

[parameters]
use_integer_indices = true
check_convergence = {'false' if n_nodes > 1000 else 'true'}
use_sparse_eigensolver = true
num_types = {num_types}
{chr(10).join(retention_lines)}

[types]
{chr(10).join(type_name_lines)}

[output]
log_directory = logs
results_file = output/{data_prefix}_results.txt
top_nodes = 20
top_authors = 30
show_author_kudos_details = false
"""

    with open(filename, 'w') as f:
        f.write(config_content)
    print(f"Saved configuration to {filename}")


def main():
    parser = argparse.ArgumentParser(description='Generate test data for credit transfer analysis')
    parser.add_argument('--nodes', type=int, default=100, help='Number of nodes (default: 100)')
    parser.add_argument('--authors', type=int, default=50, help='Number of authors (default: 50)')
    parser.add_argument('--edge-prob', type=float, default=0.05,
                       help='Edge probability (default: 0.05)')
    parser.add_argument('--dataset-ratio', type=float, default=0.2,
                       help='Fraction of dataset nodes (default: 0.2) - ignored if --multi-type is used')
    parser.add_argument('--authors-per-paper', type=int, default=3,
                       help='Average authors per paper (default: 3)')
    parser.add_argument('--prefix', type=str, default='test',
                       help='Prefix for output files (default: test)')
    parser.add_argument('--seed', type=int, default=None,
                       help='Random seed for reproducibility')
    parser.add_argument('--multi-type', action='store_true',
                       help='Generate graph with 6 node types (papers, datasets, software, clinical trials, white papers, technical reports)')

    args = parser.parse_args()

    if args.seed is not None:
        np.random.seed(args.seed)

    print(f"Generating test data with {args.nodes} nodes, {args.authors} authors...")

    # Create directories
    os.makedirs('data', exist_ok=True)
    os.makedirs('config', exist_ok=True)
    os.makedirs('output', exist_ok=True)

    # Configure node types
    if args.multi_type:
        # 6 types: papers, datasets, software, clinical trials, white papers, technical reports
        type_distribution = [
            (0, 0.40),  # 40% papers
            (1, 0.15),  # 15% datasets
            (2, 0.15),  # 15% software
            (3, 0.10),  # 10% clinical trials
            (4, 0.10),  # 10% white papers
            (5, 0.10),  # 10% technical reports
        ]
        type_config = [
            (0, 'paper', 0.2),
            (1, 'dataset', 0.9),
            (2, 'software', 0.7),
            (3, 'clinical_trial', 0.85),
            (4, 'white_paper', 0.3),
            (5, 'technical_report', 0.4),
        ]
        print("Using multi-type mode with 6 node types")
    else:
        # 2 types: papers and datasets
        type_distribution = [
            (0, 1 - args.dataset_ratio),  # papers
            (1, args.dataset_ratio),      # datasets
        ]
        type_config = [
            (0, 'paper', 0.2),
            (1, 'dataset', 0.9),
        ]

    # Generate graph
    adj_matrix, node_types = generate_citation_graph(
        args.nodes, args.edge_prob, type_distribution
    )

    # Generate authors
    node_to_authors = generate_authors(
        args.nodes, args.authors, args.authors_per_paper
    )

    # Save files
    save_adjacency_matrix(f'data/{args.prefix}_adjacency.txt', adj_matrix)
    save_node_types(f'data/{args.prefix}_nodes.txt', node_types)
    save_authors(f'data/{args.prefix}_authors.txt', node_to_authors)
    save_author_names(f'data/{args.prefix}_author_names.txt', args.authors)
    generate_config(f'config/{args.prefix}.properties', args.prefix, args.nodes, type_config)

    # Print statistics
    n_edges = np.sum(adj_matrix)

    print("\nGenerated graph statistics:")
    print(f"  Total nodes: {args.nodes}")

    # Count nodes by type
    unique_types, type_counts = np.unique(node_types, return_counts=True)
    for type_id, count in zip(unique_types, type_counts):
        type_name = next((name for tid, name, _ in type_config if tid == type_id), f'type_{type_id}')
        print(f"  {type_name.replace('_', ' ').title()}: {count} ({count/args.nodes*100:.1f}%)")

    print(f"  Total edges: {n_edges}")
    print(f"  Average degree: {n_edges/args.nodes:.2f}")
    print(f"  Authors: {args.authors}")
    print(f"\nTo run analysis:")
    print(f"  python3 credit/creditRunner.py config/{args.prefix}.properties")


if __name__ == "__main__":
    main()

