"""
Efficient loader for large-scale serialized graph data
"""

import numpy as np
import scipy.sparse as sp
from typing import Dict, List, Tuple
import os
import json


class LargeScaleDataLoader:
    """
    Memory-efficient loader for large-scale graph data.
    """

    def __init__(self, data_dir: str, prefix: str):
        """
        Args:
            data_dir: Directory containing serialized files
            prefix: File prefix (e.g., 'nature_data')
        """
        self.data_dir = data_dir
        self.prefix = prefix

        # Load metadata first
        metadata_file = os.path.join(data_dir, f'{prefix}_metadata.json')
        with open(metadata_file, 'r') as f:
            self.metadata = json.load(f)

        print("="*80)
        print("LARGE-SCALE DATA LOADER")
        print("="*80)
        print(f"\nDataset: {prefix}")
        print(f"  Nodes: {self.metadata['n_nodes']:,}")
        print(f"    - Papers: {self.metadata['n_papers']:,}")
        print(f"    - Patents: {self.metadata['n_patents']:,}")
        print(f"    - Clinical Trials: {self.metadata['n_clinical_trials']:,}")
        print(f"  Edges: {self.metadata['n_edges']:,}")
        print(f"  Authors: {self.metadata['n_authors']:,}")

    def load_adjacency_matrix(self) -> sp.csr_matrix:
        """Load sparse adjacency matrix."""
        print("\nLoading adjacency matrix...")
        adj_file = os.path.join(self.data_dir, f'{self.prefix}_adjacency.npz')
        adjacency = sp.load_npz(adj_file)
        print(f"  ✓ Loaded: {adjacency.shape[0]:,} × {adjacency.shape[1]:,}")
        print(f"  ✓ Non-zero elements: {adjacency.nnz:,}")
        print(f"  ✓ Memory: ~{(adjacency.data.nbytes + adjacency.indices.nbytes + adjacency.indptr.nbytes) / 1e9:.2f} GB")
        return adjacency

    def load_node_types(self) -> np.ndarray:
        """Load node types array."""
        print("\nLoading node types...")
        types_file = os.path.join(self.data_dir, f'{self.prefix}_node_types.npy')
        node_types = np.load(types_file)
        print(f"  ✓ Loaded: {len(node_types):,} nodes")
        print(f"  ✓ Memory: {node_types.nbytes / 1e6:.2f} MB")
        return node_types

    def load_node_ids(self) -> np.ndarray:
        """Load external node IDs."""
        print("\nLoading node IDs...")
        ids_file = os.path.join(self.data_dir, f'{self.prefix}_node_ids.npy')
        node_ids = np.load(ids_file)
        print(f"  ✓ Loaded: {len(node_ids):,} IDs")
        print(f"  ✓ Memory: {node_ids.nbytes / 1e6:.2f} MB")
        return node_ids

    def load_authors(self, load_names: bool = False) -> Tuple[Dict[int, List[int]], Dict[int, str]]:
        """
        Load author mappings.

        Args:
            load_names: Whether to load author names (slower)

        Returns:
            (node_to_authors, author_names)
        """
        print("\nLoading author mappings...")
        authors_file = os.path.join(self.data_dir, f'{self.prefix}_authors.npz')
        data = np.load(authors_file)

        node_indices = data['node_indices']
        author_counts = data['author_counts']
        author_ids = data['author_ids']

        # Reconstruct dictionary
        node_to_authors = {}
        idx = 0
        for i, node_idx in enumerate(node_indices):
            count = author_counts[i]
            node_to_authors[int(node_idx)] = author_ids[idx:idx+count].tolist()
            idx += count

        print(f"  ✓ Loaded: {len(node_to_authors):,} nodes with authors")
        print(f"  ✓ Total author assignments: {len(author_ids):,}")

        author_names = {}
        if load_names:
            names_file = os.path.join(self.data_dir, f'{self.prefix}_author_names.json')
            if os.path.exists(names_file):
                print("  Loading author names...")
                with open(names_file, 'r') as f:
                    author_names_str = json.load(f)
                # Convert string keys back to integers
                author_names = {int(k): v for k, v in author_names_str.items()}
                print(f"  ✓ Loaded: {len(author_names):,} author names")
            else:
                print("  ⚠ Author names file not found")

        return node_to_authors, author_names

    def create_retention_rates(self,
                              paper_rate: float = 0.5,
                              patent_rate: float = 0.5,
                              clinical_trial_rate: float = 0.5) -> np.ndarray:
        """
        Create retention rates array for all nodes.

        Args:
            paper_rate: Retention rate for papers (0.0-1.0)
            patent_rate: Retention rate for patents (0.0-1.0)
            clinical_trial_rate: Retention rate for clinical trials (0.0-1.0)

        Returns:
            retention_rates: Array of shape (n_nodes,)
        """
        print("\nCreating retention rates...")
        node_types = self.load_node_types()

        retention_rates = np.zeros(len(node_types), dtype=np.float32)
        retention_rates[node_types == 0] = paper_rate
        retention_rates[node_types == 1] = patent_rate
        retention_rates[node_types == 2] = clinical_trial_rate

        print(f"  ✓ Paper retention: {paper_rate}")
        print(f"  ✓ Patent retention: {patent_rate}")
        print(f"  ✓ Clinical trial retention: {clinical_trial_rate}")

        return retention_rates

    def load_all(self, load_author_names: bool = False):
        """
        Load all data structures.

        Returns:
            (adjacency, node_types, node_ids, node_to_authors, author_names, metadata)
        """
        adjacency = self.load_adjacency_matrix()
        node_types = self.load_node_types()
        node_ids = self.load_node_ids()
        node_to_authors, author_names = self.load_authors(load_author_names)

        print("\n" + "="*80)
        print("ALL DATA LOADED")
        print("="*80 + "\n")

        return adjacency, node_types, node_ids, node_to_authors, author_names, self.metadata


# Usage example
if __name__ == "__main__":
    loader = LargeScaleDataLoader('data/large_scale_experiment', 'nature_data')

    # Load everything
    adjacency, node_types, node_ids, node_to_authors, author_names, metadata = loader.load_all(
        load_author_names=True
    )

    # Create retention rates
    retention_rates = loader.create_retention_rates(
        paper_rate=0.5,
        patent_rate=0.7,
        clinical_trial_rate=0.3
    )

    print("Ready for credit transfer calculation!")
