"""
MES Experiment - Run Credit Transfer and H-Index Calculation

This script runs credit transfer analysis on the MES (Marine Ecosystem Studies) dataset
and calculates author h-indices using configuration from a properties file.

Usage:
    python run_mes_experiment.py [config_file]

    If no config file is specified, uses config/mes_experiment.properties
"""

import sys
import os
import json
import numpy as np
from datetime import datetime
import configparser

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from graph.GraphUtils import Graph
from credit.generalFormulation import GeneralCreditTransfer
from credit.authorMetrics import AuthorMetrics


def load_config(config_file: str) -> configparser.ConfigParser:
    """
    Load configuration from properties file.

    Args:
        config_file: Path to configuration file

    Returns:
        ConfigParser object with loaded configuration
    """
    config = configparser.ConfigParser()

    if not os.path.exists(config_file):
        raise FileNotFoundError(f"Configuration file not found: {config_file}")

    config.read(config_file)

    print(f"Loaded configuration from: {config_file}")
    if config.has_option('experiment', 'name'):
        print(f"  Experiment: {config.get('experiment', 'name')}")
    if config.has_option('experiment', 'description'):
        print(f"  Description: {config.get('experiment', 'description')}")

    return config


def load_mes_data(config: configparser.ConfigParser):
    """
    Load serialized MES data from files using configuration.

    Args:
        config: ConfigParser with loaded configuration

    Returns:
        Tuple of (node_labels, adjacency_matrix, node_types, node_to_authors, author_names, metadata)
    """
    # Get paths from config
    data_dir = config.get('input', 'data_directory')
    prefix = config.get('input', 'data_prefix', fallback='mes')

    # Make path absolute if relative
    if not os.path.isabs(data_dir):
        data_dir = os.path.join(project_root, data_dir)

    print(f"\nLoading MES data from {data_dir}...")

    # Load metadata
    metadata_file = os.path.join(data_dir, f'{prefix}_metadata.json')
    with open(metadata_file, 'r') as f:
        metadata = json.load(f)

    print(f"  Dataset: {metadata['dataset']}")
    print(f"  Nodes: {metadata['total_nodes']:,}")
    print(f"  Edges: {metadata['total_edges']:,}")
    print(f"  Authors: {metadata['total_authors']:,}")

    # Load node labels
    node_labels = []
    with open(os.path.join(data_dir, f'{prefix}_node_labels.txt'), 'r') as f:
        for line in f:
            if line.startswith('#'):
                continue
            parts = line.strip().split(maxsplit=1)
            if len(parts) >= 1:
                node_labels.append(int(parts[0]))

    # Load adjacency matrix
    adjacency_matrix = []
    with open(os.path.join(data_dir, f'{prefix}_adjacency.txt'), 'r') as f:
        for line in f:
            if line.startswith('#'):
                continue
            row = [int(x) for x in line.strip().split()]
            adjacency_matrix.append(row)

    # Load node types
    node_types = []
    with open(os.path.join(data_dir, f'{prefix}_node_types.txt'), 'r') as f:
        for line in f:
            if line.startswith('#'):
                continue
            parts = line.strip().split()
            if len(parts) == 2:
                node_types.append(int(parts[1]))

    node_types = np.array(node_types, dtype=np.int32)

    # Load node to authors mapping
    node_to_authors = {}
    with open(os.path.join(data_dir, f'{prefix}_authors.txt'), 'r') as f:
        for line in f:
            if line.startswith('#'):
                continue
            parts = line.strip().split()
            if len(parts) >= 2:
                node_id = int(parts[0])
                author_ids = [int(x) for x in parts[1:]]
                node_to_authors[node_id] = author_ids

    # Load author names
    author_names = {}
    with open(os.path.join(data_dir, f'{prefix}_author_names.txt'), 'r') as f:
        for line in f:
            if line.startswith('#'):
                continue
            parts = line.strip().split(maxsplit=1)
            if len(parts) == 2:
                author_id = int(parts[0])
                author_name = parts[1]
                author_names[author_id] = author_name

    print(f"  Loaded: {len(node_labels)} nodes, {len(node_to_authors)} with authors")

    return node_labels, adjacency_matrix, node_types, node_to_authors, author_names, metadata


def run_mes_experiment(config: configparser.ConfigParser):
    """
    Run credit transfer experiment on MES data using configuration.

    Args:
        config: ConfigParser with loaded configuration
    """

    print("\n" + "="*80)
    print("MES CREDIT TRANSFER EXPERIMENT")
    print("="*80 + "\n")

    # Get output directory from config
    output_dir = config.get('output', 'output_directory')
    if not os.path.isabs(output_dir):
        output_dir = os.path.join(project_root, output_dir)

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Load data
    node_labels, adj_matrix, node_types, node_to_authors, author_names, metadata = \
        load_mes_data(config)

    # Build graph
    print("\nBuilding graph...")
    graph = Graph.from_matrix(node_labels, adj_matrix, is_directed=True)
    print(f"  Graph: {len(graph.nodes())} nodes, {len(graph.edges())} edges")

    # Initialize credit transfer
    print("\nInitializing credit transfer model...")
    use_integer_indices = config.getboolean('parameters', 'use_integer_indices', fallback=True)

    gct = GeneralCreditTransfer(
        graph=graph,
        node_types=node_types,
        use_integer_indices=use_integer_indices
    )

    print(f"  Using integer indexing: {gct.use_integer_indices}")
    print(f"  Sparse matrix format: {gct.transfer_matrix.format}")
    memory_mb = gct.transfer_matrix.data.nbytes / 1024 / 1024
    print(f"  Memory usage: ~{memory_mb:.2f} MB")

    # Set retention rates from config
    print("\nSetting retention rates...")
    num_types = config.getint('parameters', 'num_types', fallback=3)
    retention_rates = []
    type_names = {}

    for i in range(num_types):
        rate = config.getfloat('parameters', f'type_{i}_retention', fallback=0.5)
        retention_rates.append(rate)
        type_name = config.get('types', f'type_{i}_name', fallback=f'type_{i}')
        type_names[i] = type_name
        print(f"  {type_name}: {rate}")

    retention_rates = np.array(retention_rates, dtype=np.float64)
    gct.set_retention_by_type(retention_rates)

    # Compute credit distribution
    print("\nComputing credit distribution...")
    check_convergence = config.getboolean('parameters', 'check_convergence', fallback=False)
    use_sparse_eigensolver = config.getboolean('parameters', 'use_sparse_eigensolver', fallback=True)

    total_credit, kudos, diagnostics = gct.compute_credit_distribution(
        check_convergence=check_convergence,
        use_sparse_eigensolver=use_sparse_eigensolver
    )

    # Print diagnostics
    print("\nCredit distribution results:")
    print(f"  Total kudos: {np.sum(kudos):.2f}")
    print(f"  Total credit: {np.sum(total_credit):.2f}")
    print(f"  Mean kudos: {np.mean(kudos):.4f}")
    print(f"  Max kudos: {np.max(kudos):.4f}")
    print(f"  Min kudos: {np.min(kudos):.4f}")
    print(f"  Conservation error: {diagnostics['conservation_error']:.6e}")

    # Compute author metrics
    print("\nComputing author h-indices...")
    author_metrics = AuthorMetrics(node_to_authors, author_names)
    h_indices = author_metrics.compute_all_h_indices(kudos)

    print(f"  Total authors: {len(h_indices)}")

    # Get author statistics
    author_data = []
    for author_id in h_indices.keys():
        author_kudos = author_metrics.get_author_kudos(author_id, kudos)
        total_kudos = np.sum(author_kudos)
        h_idx = h_indices[author_id]
        author_data.append({
            'author_id': author_id,
            'h_index': h_idx,
            'total_kudos': total_kudos,
            'num_publications': len(author_kudos),
            'name': author_names.get(author_id, 'Unknown')
        })

    # Sort by h-index (descending), then by total kudos
    author_data.sort(key=lambda x: (-x['h_index'], -x['total_kudos']))

    # Save results based on config
    print("\nSaving results...")
    results_prefix = config.get('output', 'results_prefix', fallback='mes')

    # 1. Save kudos and credit (if enabled)
    if config.getboolean('output', 'save_credit_results', fallback=True):
        results_file = os.path.join(output_dir, f'{results_prefix}_credit_results.txt')
        with open(results_file, 'w') as f:
            f.write("# MES Credit Transfer Results\n")
            f.write(f"# Generated: {datetime.now().isoformat()}\n")
            f.write("#\n")
            f.write("# node_id node_type total_credit kudos\n")
            f.write("#\n")
            for idx in range(len(node_types)):
                node_type = node_types[idx]
                f.write(f"{idx} {node_type} {total_credit[idx]:.8f} {kudos[idx]:.8f}\n")

        print(f"  Saved credit results to {results_file}")

    # 2. Save author h-indices (if enabled)
    if config.getboolean('output', 'save_author_hindices', fallback=True):
        author_results_file = os.path.join(output_dir, f'{results_prefix}_author_hindices.txt')
        with open(author_results_file, 'w') as f:
            f.write("# MES Author H-Indices\n")
            f.write(f"# Generated: {datetime.now().isoformat()}\n")
            f.write("#\n")
            f.write("# author_id h_index total_kudos num_publications author_name\n")
            f.write("#\n")
            for author in author_data:
                f.write(f"{author['author_id']} {author['h_index']} "
                       f"{author['total_kudos']:.8f} {author['num_publications']} "
                       f"{author['name']}\n")

        print(f"  Saved author h-indices to {author_results_file}")

    # 3. Save summary JSON (if enabled)
    summary = {}  # Initialize to avoid uninitialized variable warning

    if config.getboolean('output', 'save_summary_json', fallback=True):
        top_authors_count = config.getint('output', 'top_authors', fallback=100)

        summary = {
            "experiment": config.get('experiment', 'name', fallback='MES Credit Transfer'),
            "date": datetime.now().isoformat(),
            "config_file": config.get('experiment', 'date', fallback='N/A'),
            "dataset": metadata['dataset'],
            "parameters": {
                "use_integer_indices": use_integer_indices,
                "check_convergence": check_convergence,
                "use_sparse_eigensolver": use_sparse_eigensolver,
                "retention_rates": {
                    type_names.get(i, f'type_{i}'): float(retention_rates[i])
                    for i in range(num_types)
                }
            },
            "graph_stats": {
                "total_nodes": int(metadata['total_nodes']),
                "total_edges": int(metadata['total_edges']),
                "node_counts": metadata['node_counts']
            },
            "results": {
                "total_kudos": float(np.sum(kudos)),
                "total_credit": float(np.sum(total_credit)),
                "mean_kudos": float(np.mean(kudos)),
                "max_kudos": float(np.max(kudos)),
                "min_kudos": float(np.min(kudos)),
                "conservation_error": float(diagnostics['conservation_error'])
            },
            "author_metrics": {
                "total_authors": len(h_indices),
                "max_h_index": int(max(h_indices.values())) if h_indices else 0,
                "mean_h_index": float(np.mean(list(h_indices.values()))) if h_indices else 0,
                "authors_with_h_gt_0": sum(1 for h in h_indices.values() if h > 0)
            },
            "top_authors": [
                {
                    "rank": i + 1,
                    "author_id": author['author_id'],
                    "name": author['name'],
                    "h_index": author['h_index'],
                    "total_kudos": float(author['total_kudos']),
                    "num_publications": author['num_publications']
                }
                for i, author in enumerate(author_data[:top_authors_count])
            ]
        }

        summary_file = os.path.join(output_dir, f'{results_prefix}_experiment_summary.json')
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)

        print(f"  Saved summary to {summary_file}")

    # Display top authors
    top_nodes_display = config.getint('output', 'top_authors', fallback=20)
    print("\n" + "="*80)
    print(f"TOP {min(top_nodes_display, len(author_data))} AUTHORS BY H-INDEX")
    print("="*80)

    for i, author in enumerate(author_data[:top_nodes_display], 1):
        print(f"{i:2d}. {author['name'][:50]:<50} (ID: {author['author_id']})")
        print(f"    H-index: {author['h_index']}, Publications: {author['num_publications']}, "
              f"Total kudos: {author['total_kudos']:.4f}")

    print("\n" + "="*80)
    print("EXPERIMENT COMPLETE")
    print("="*80)
    print(f"\nResults saved to: {output_dir}/")
    if config.getboolean('output', 'save_credit_results', fallback=True):
        print(f"  - {results_prefix}_credit_results.txt")
    if config.getboolean('output', 'save_author_hindices', fallback=True):
        print(f"  - {results_prefix}_author_hindices.txt")
    if config.getboolean('output', 'save_summary_json', fallback=True):
        print(f"  - {results_prefix}_experiment_summary.json")
    print("="*80 + "\n")

    return summary


if __name__ == "__main__":
    # Default config file
    default_config = os.path.join(project_root, 'config', 'mes_experiment.properties')

    # Check if config file provided as argument
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    else:
        config_file = default_config

    # Make path absolute if relative
    if not os.path.isabs(config_file):
        config_file = os.path.join(project_root, config_file)

    print(f"Using configuration file: {config_file}")

    try:
        # Load configuration
        config = load_config(config_file)

        # Run experiment
        summary = run_mes_experiment(config)

    except FileNotFoundError as e:
        print(f"\nERROR: {str(e)}")
        print(f"\nUsage: python run_mes_experiment.py [config_file]")
        print(f"  If no config file is specified, uses: {default_config}")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

