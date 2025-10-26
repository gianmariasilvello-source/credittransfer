"""
Credit Transfer Runner - Wrapper for running credit distribution from configuration files.

This module provides a high-level interface for running credit distribution analysis
by reading parameters from configuration files and data from text files.

Author: Gianmaria Silvello
Date: October 2025
"""

import os
import sys
import configparser
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import numpy as np

from credit.generalFormulation import GeneralCreditTransfer
from credit.authorMetrics import AuthorMetrics
from graph.GraphUtils import Graph


class CreditRunner:
    """
    High-level runner for credit distribution analysis from configuration files.

    Reads configuration from a properties file and data from separate text files,
    computes credit distribution, and outputs results to console and log file.
    """

    def __init__(self, config_path: str):
        """
        Initialize runner with configuration file.

        Args:
            config_path: Path to the configuration properties file
        """
        self.config_path = config_path
        self.config = configparser.ConfigParser()
        self.config.read(config_path)

        # Setup logging
        self._setup_logging()

        self.logger.info(f"Initialized CreditRunner with config: {config_path}")

    def _setup_logging(self):
        """Setup logging to both console and file."""
        log_dir = self.config.get('output', 'log_directory', fallback='logs')
        os.makedirs(log_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = os.path.join(log_dir, f'credit_run_{timestamp}.log')

        # Create logger
        self.logger = logging.getLogger('CreditRunner')
        self.logger.setLevel(logging.INFO)

        # Clear existing handlers
        self.logger.handlers = []

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(message)s')
        console_handler.setFormatter(console_formatter)

        # File handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)

        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)

        self.logger.info("=" * 80)
        self.logger.info("Credit Transfer Analysis Run")
        self.logger.info("=" * 80)
        self.logger.info(f"Log file: {log_file}")

    def _load_adjacency_matrix(self) -> Tuple[List, np.ndarray]:
        """
        Load adjacency matrix from file.

        File format: Space-separated values, one row per line.
        Example:
            0 1 1 0
            0 0 1 1
            0 0 0 1
            0 0 0 0

        Returns:
            Tuple of (node_labels, adjacency_matrix)
        """
        adj_file = self.config.get('input', 'adjacency_matrix_file')
        self.logger.info(f"Loading adjacency matrix from: {adj_file}")

        with open(adj_file, 'r') as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]

        # Parse matrix
        adj_matrix = []
        for line in lines:
            row = [int(x) for x in line.split()]
            adj_matrix.append(row)

        adj_matrix = np.array(adj_matrix)
        n = adj_matrix.shape[0]

        self.logger.info(f"Loaded adjacency matrix: {n}x{n} ({np.sum(adj_matrix)} edges)")

        return list(range(n)), adj_matrix

    def _load_node_ids(self, n_nodes: int) -> Tuple[Optional[List], Optional[np.ndarray]]:
        """
        Load node IDs/labels and types from file.

        File format: Each line contains: node_id node_type
        Example:
            0 0
            1 1
            2 0
            3 0
            4 1

        Where node_type: 0=paper, 1=dataset (or as configured)

        Returns:
            Tuple of (node_labels, node_types)
        """
        node_file = self.config.get('input', 'node_ids_file', fallback=None)

        if not node_file or not os.path.exists(node_file):
            self.logger.info("No node IDs file provided, using integer indices")
            return None, None

        self.logger.info(f"Loading node IDs from: {node_file}")

        node_labels = []
        node_types = []

        with open(node_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                parts = line.split()
                if len(parts) >= 2:
                    node_labels.append(int(parts[0]))
                    node_types.append(int(parts[1]))
                else:
                    node_labels.append(int(parts[0]))
                    node_types.append(0)  # Default type

        if len(node_labels) != n_nodes:
            self.logger.warning(
                f"Node IDs file has {len(node_labels)} entries, "
                f"but adjacency matrix has {n_nodes} nodes. Using defaults."
            )
            return None, None

        node_types_array = np.array(node_types, dtype=np.int32)

        self.logger.info(f"Loaded {len(node_labels)} node IDs with types")
        type_counts = np.bincount(node_types_array)
        for type_id, count in enumerate(type_counts):
            type_name = self._get_type_name(type_id)
            self.logger.info(f"  Type {type_id} ({type_name}): {count} nodes")

        return node_labels, node_types_array

    def _load_authors(self, n_nodes: int) -> Tuple[Optional[Dict], Optional[Dict]]:
        """
        Load author information from file.

        File format: Each line contains: node_id author_id1 author_id2 ...
        Example:
            0 10 25 30
            1 10 25
            2 25
            3 25
            4 42

        Optionally, an author names file can be provided with format:
            author_id author_name
        Example:
            10 Alice Smith
            25 Bob Johnson
            30 Charlie Brown
            42 Diana Prince

        Returns:
            Tuple of (node_to_authors, author_names)
        """
        authors_file = self.config.get('input', 'authors_file', fallback=None)

        if not authors_file or not os.path.exists(authors_file):
            self.logger.info("No authors file provided, skipping author metrics")
            return None, None

        self.logger.info(f"Loading authors from: {authors_file}")

        node_to_authors = {}

        with open(authors_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                parts = line.split()
                if len(parts) >= 2:
                    node_id = int(parts[0])
                    author_ids = [int(x) for x in parts[1:]]
                    node_to_authors[node_id] = author_ids

        self.logger.info(f"Loaded authors for {len(node_to_authors)} nodes")

        # Load author names if available
        author_names = {}
        author_names_file = self.config.get('input', 'author_names_file', fallback=None)

        if author_names_file and os.path.exists(author_names_file):
            self.logger.info(f"Loading author names from: {author_names_file}")

            with open(author_names_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue

                    parts = line.split(maxsplit=1)
                    if len(parts) == 2:
                        author_id = int(parts[0])
                        author_name = parts[1]
                        author_names[author_id] = author_name

            self.logger.info(f"Loaded {len(author_names)} author names")

        return node_to_authors, author_names if author_names else None

    def _get_type_name(self, type_id: int) -> str:
        """Get human-readable name for node type."""
        type_name = self.config.get('types', f'type_{type_id}_name', fallback=None)
        if type_name:
            return type_name
        # Fallback to legacy config
        if type_id == 0:
            return self.config.get('types', 'type_0_name', fallback='paper')
        elif type_id == 1:
            return self.config.get('types', 'type_1_name', fallback='dataset')
        else:
            return f'type_{type_id}'

    def _get_retention_rates(self) -> np.ndarray:
        """Get retention rates from configuration, supporting multiple types."""
        # Check if num_types is specified, otherwise detect from config
        num_types = self.config.getint('parameters', 'num_types', fallback=None)

        if num_types is None:
            # Auto-detect number of types from configuration
            num_types = 0
            for i in range(100):  # Check up to 100 types
                if self.config.has_option('parameters', f'type_{i}_retention'):
                    num_types = i + 1
                else:
                    break

            # If no types found, use legacy default (2 types)
            if num_types == 0:
                num_types = 2

        retention_rates = []
        self.logger.info("Retention rates:")

        for type_id in range(num_types):
            # Try to get retention rate, with legacy fallbacks for types 0 and 1
            if type_id == 0:
                rate = self.config.getfloat('parameters', 'type_0_retention', fallback=0.2)
            elif type_id == 1:
                rate = self.config.getfloat('parameters', 'type_1_retention', fallback=0.9)
            else:
                rate = self.config.getfloat('parameters', f'type_{type_id}_retention', fallback=0.5)

            retention_rates.append(rate)
            self.logger.info(f"  {self._get_type_name(type_id)}: {rate}")

        return np.array(retention_rates, dtype=np.float64)

    def run(self):
        """
        Main execution method - loads data, runs credit distribution, outputs results.
        """
        try:
            self.logger.info("")
            self.logger.info("=" * 80)
            self.logger.info("LOADING DATA")
            self.logger.info("=" * 80)

            # Load data files
            node_labels, adj_matrix = self._load_adjacency_matrix()
            n_nodes = adj_matrix.shape[0]

            _, node_types = self._load_node_ids(n_nodes)
            node_to_authors, author_names = self._load_authors(n_nodes)

            # Get optimization parameters
            use_integer_indices = self.config.getboolean('parameters', 'use_integer_indices', fallback=True)
            check_convergence = self.config.getboolean('parameters', 'check_convergence', fallback=False)
            use_sparse_eigensolver = self.config.getboolean('parameters', 'use_sparse_eigensolver', fallback=True)

            self.logger.info("")
            self.logger.info("=" * 80)
            self.logger.info("BUILDING GRAPH")
            self.logger.info("=" * 80)

            # Build graph
            g = Graph.from_matrix(node_labels, adj_matrix.tolist(), is_directed=True)
            self.logger.info(f"Graph: {len(g.nodes())} nodes, {len(g.edges())} edges")

            # Initialize credit transfer
            self.logger.info("")
            self.logger.info("=" * 80)
            self.logger.info("INITIALIZING CREDIT TRANSFER")
            self.logger.info("=" * 80)

            gct = GeneralCreditTransfer(
                graph=g,
                node_types=node_types,
                use_integer_indices=use_integer_indices
            )

            self.logger.info(f"Using integer indexing: {gct.use_integer_indices}")
            self.logger.info(f"Sparse matrix format: {gct.transfer_matrix.format}")
            memory_mb = gct.transfer_matrix.data.nbytes / 1024 / 1024
            self.logger.info(f"Memory usage: ~{memory_mb:.2f} MB")

            # Set retention rates
            if node_types is not None:
                retention_rates = self._get_retention_rates()
                gct.set_retention_by_type(retention_rates)
            else:
                uniform_retention = self.config.getfloat('parameters', 'uniform_retention', fallback=0.2)
                gct.set_uniform_retention(uniform_retention)
                self.logger.info(f"Uniform retention rate: {uniform_retention}")

            # Compute credit distribution
            self.logger.info("")
            self.logger.info("=" * 80)
            self.logger.info("COMPUTING CREDIT DISTRIBUTION")
            self.logger.info("=" * 80)
            self.logger.info(f"Check convergence: {check_convergence}")
            self.logger.info(f"Use sparse eigensolver: {use_sparse_eigensolver}")

            total_credit, kudos, diagnostics = gct.compute_credit_distribution(
                check_convergence=check_convergence,
                use_sparse_eigensolver=use_sparse_eigensolver
            )

            # Output results
            self.logger.info("")
            self.logger.info("=" * 80)
            self.logger.info("RESULTS - CREDIT DISTRIBUTION")
            self.logger.info("=" * 80)

            # Summary statistics
            self.logger.info(f"Total kudos: {np.sum(kudos):.6f}")
            self.logger.info(f"Total credit: {np.sum(total_credit):.6f}")
            self.logger.info(f"Mean kudos: {np.mean(kudos):.6f}")
            self.logger.info(f"Max kudos: {np.max(kudos):.6f}")
            self.logger.info(f"Min kudos: {np.min(kudos):.6f}")

            # Conservation check
            if 'conservation_error' in diagnostics:
                self.logger.info(f"Conservation error: {diagnostics['conservation_error']:.2e}")

            # Convergence diagnostics
            if check_convergence and 'spectral_radius' in diagnostics and diagnostics['spectral_radius'] is not None:
                self.logger.info("")
                self.logger.info("Convergence diagnostics:")
                self.logger.info(f"  Spectral radius: {diagnostics['spectral_radius']:.6f}")
                if 'converges' in diagnostics:
                    self.logger.info(f"  Converges: {diagnostics['converges']}")
                if 'determinant' in diagnostics:
                    self.logger.info(f"  Determinant det(I-A^T): {diagnostics['determinant']:.6e}")
                if 'used_sparse_eigensolver' in diagnostics:
                    self.logger.info(f"  Used sparse eigensolver: {diagnostics['used_sparse_eigensolver']}")

            # Output top nodes if requested
            output_top_nodes = self.config.getint('output', 'top_nodes', fallback=10)
            if output_top_nodes > 0:
                self.logger.info("")
                self.logger.info(f"Top {output_top_nodes} nodes by kudos:")
                top_indices = np.argsort(kudos)[::-1][:output_top_nodes]
                for rank, idx in enumerate(top_indices, 1):
                    node_label = gct.nodes_list[idx]
                    node_type = node_types[idx] if node_types is not None else None
                    type_str = f"({self._get_type_name(node_type)})" if node_type is not None else ""
                    self.logger.info(
                        f"  {rank}. Node {node_label} {type_str}: "
                        f"kudos={kudos[idx]:.6f}, total_credit={total_credit[idx]:.6f}"
                    )

            # Compute and output author metrics
            if node_to_authors is not None:
                self.logger.info("")
                self.logger.info("=" * 80)
                self.logger.info("AUTHOR METRICS")
                self.logger.info("=" * 80)

                author_metrics = AuthorMetrics(node_to_authors, author_names)
                h_indices = author_metrics.compute_all_h_indices(kudos)

                self.logger.info(f"Total authors: {len(h_indices)}")
                self.logger.info("")

                # Sort authors by h-index (descending) then by total kudos
                author_data = []
                for author_id in h_indices.keys():
                    author_kudos = author_metrics.get_author_kudos(author_id, kudos)
                    total_kudos = np.sum(author_kudos)
                    h_idx = h_indices[author_id]
                    author_data.append((author_id, h_idx, total_kudos, author_kudos))

                author_data.sort(key=lambda x: (-x[1], -x[2]))  # Sort by h-index desc, then total kudos desc

                output_top_authors = self.config.getint('output', 'top_authors', fallback=20)
                display_authors = author_data[:output_top_authors] if output_top_authors > 0 else author_data

                for rank, (author_id, h_idx, total_kudos, author_kudos) in enumerate(display_authors, 1):
                    name = author_metrics.get_author_name(author_id)
                    self.logger.info(f"{rank}. {name} (ID: {author_id})")
                    self.logger.info(f"   Publications: {len(author_kudos)}")
                    self.logger.info(f"   h-index: {h_idx}")
                    self.logger.info(f"   Total kudos: {total_kudos:.6f}")

                    # Show individual kudos values if requested
                    if self.config.getboolean('output', 'show_author_kudos_details', fallback=False):
                        sorted_kudos = np.sort(author_kudos)[::-1]
                        kudos_str = ", ".join([f"{k:.4f}" for k in sorted_kudos[:10]])
                        if len(sorted_kudos) > 10:
                            kudos_str += ", ..."
                        self.logger.info(f"   Kudos values: [{kudos_str}]")

                    self.logger.info("")

            # Save detailed results if requested
            output_file = self.config.get('output', 'results_file', fallback=None)
            if output_file:
                self._save_results(output_file, total_credit, kudos, gct.nodes_list, node_types)

            self.logger.info("=" * 80)
            self.logger.info("ANALYSIS COMPLETE")
            self.logger.info("=" * 80)

        except Exception as e:
            self.logger.error(f"Error during execution: {str(e)}", exc_info=True)
            raise

    def _save_results(self, output_file: str, total_credit: np.ndarray,
                     kudos: np.ndarray, nodes_list: List, node_types: Optional[np.ndarray]):
        """Save detailed results to file."""
        self.logger.info(f"Saving detailed results to: {output_file}")

        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        with open(output_file, 'w') as f:
            f.write("# Credit Transfer Results\n")
            f.write(f"# Generated: {datetime.now().isoformat()}\n")
            f.write("#\n")
            f.write("# Format: node_id node_type total_credit kudos\n")
            f.write("#\n")

            for idx, node in enumerate(nodes_list):
                node_type = node_types[idx] if node_types is not None else -1
                f.write(f"{node} {node_type} {total_credit[idx]:.8f} {kudos[idx]:.8f}\n")

        self.logger.info(f"Results saved successfully")


def run_from_config(config_path: str):
    """
    Convenience function to run credit distribution from configuration file.

    Args:
        config_path: Path to configuration properties file
    """
    runner = CreditRunner(config_path)
    runner.run()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python creditRunner.py <config_file>")
        print("Example: python creditRunner.py config/example.properties")
        sys.exit(1)

    config_file = sys.argv[1]

    if not os.path.exists(config_file):
        print(f"Error: Configuration file not found: {config_file}")
        sys.exit(1)

    run_from_config(config_file)

