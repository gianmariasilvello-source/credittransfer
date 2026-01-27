"""
Extract large-scale citation data from SQL database
Memory-efficient batch processing with streaming to disk
"""

import psycopg2
import numpy as np
import scipy.sparse as sp
from typing import Dict, List, Tuple
import os
from collections import defaultdict


class SQLDataExtractor:
    """
    Extract citation graph data from SQL database in memory-efficient batches.
    """

    def __init__(self, db_config: Dict[str, str], output_dir: str):
        """
        Args:
            db_config: Database connection parameters
                {'host': 'localhost', 'database': 'citations',
                 'user': 'user', 'password': 'pass'}
            output_dir: Directory to save serialized data
        """
        self.db_config = db_config
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        # ID mappings (in-memory)
        self.external_to_index = {}  # (node_id, node_type) -> matrix_index
        self.index_counter = 0

        # Node metadata
        self.node_types = []  # Will convert to numpy array
        self.node_external_ids = []  # Original IDs

        # Author mappings
        self.node_to_authors = defaultdict(list)
        self.author_id_map = {}  # external_author_id -> internal_id
        self.author_names = {}
        self.author_counter = 0

        # Edge lists (will convert to sparse matrix)
        self.edge_sources = []
        self.edge_targets = []

    def connect(self):
        """Establish database connection."""
        self.conn = psycopg2.connect(**self.db_config)
        self.cursor = self.conn.cursor()
        print("✓ Connected to database")

    def close(self):
        """Close database connection."""
        if hasattr(self, 'cursor'):
            self.cursor.close()
        if hasattr(self, 'conn'):
            self.conn.close()
        print("✓ Database connection closed")

    def _get_or_create_node_index(self, external_id: int, node_type: str) -> int:
        """Map external node ID to internal matrix index."""
        key = (external_id, node_type)
        if key not in self.external_to_index:
            idx = self.index_counter
            self.external_to_index[key] = idx
            self.node_external_ids.append(external_id)

            # Map type string to integer
            type_map = {'paper': 0, 'patent': 1, 'clinical_trial': 2}
            self.node_types.append(type_map[node_type])

            self.index_counter += 1
            return idx
        return self.external_to_index[key]

    def _get_or_create_author_id(self, external_author_id: int, author_name: str = None) -> int:
        """Map external author ID to internal ID."""
        if external_author_id not in self.author_id_map:
            internal_id = self.author_counter
            self.author_id_map[external_author_id] = internal_id
            if author_name:
                self.author_names[internal_id] = author_name
            self.author_counter += 1
            return internal_id
        return self.author_id_map[external_author_id]

    def extract_nodes(self, batch_size: int = 100000):
        """
        Extract all nodes from database in batches.
        """
        print("\n" + "="*80)
        print("EXTRACTING NODES")
        print("="*80)

        # Extract papers
        print("\n[1/3] Extracting publications...")
        query = """
            SELECT id, type 
            FROM publications 
            ORDER BY id
        """
        self.cursor.execute(query)

        batch_count = 0
        while True:
            rows = self.cursor.fetchmany(batch_size)
            if not rows:
                break

            for node_id, pub_type in rows:
                self._get_or_create_node_index(node_id, 'paper')

            batch_count += len(rows)
            print(f"  Processed {batch_count:,} publications", end='\r')

        print(f"\n  ✓ Total publications: {batch_count:,}")

        # Extract patents
        print("\n[2/3] Extracting patents...")
        query = "SELECT id FROM patents ORDER BY id"
        self.cursor.execute(query)

        batch_count = 0
        while True:
            rows = self.cursor.fetchmany(batch_size)
            if not rows:
                break

            for (node_id,) in rows:
                self._get_or_create_node_index(node_id, 'patent')

            batch_count += len(rows)
            print(f"  Processed {batch_count:,} patents", end='\r')

        print(f"\n  ✓ Total patents: {batch_count:,}")

        # Extract clinical trials
        print("\n[3/3] Extracting clinical trials...")
        query = "SELECT id FROM clinical_trials ORDER BY id"
        self.cursor.execute(query)

        batch_count = 0
        while True:
            rows = self.cursor.fetchmany(batch_size)
            if not rows:
                break

            for (node_id,) in rows:
                self._get_or_create_node_index(node_id, 'clinical_trial')

            batch_count += len(rows)
            print(f"  Processed {batch_count:,} clinical trials", end='\r')

        print(f"\n  ✓ Total clinical trials: {batch_count:,}")
        print(f"\n✓ Total nodes: {self.index_counter:,}")

    def extract_citations(self, batch_size: int = 100000):
        """
        Extract citation edges from database in batches.
        """
        print("\n" + "="*80)
        print("EXTRACTING CITATIONS")
        print("="*80 + "\n")

        # Query with relationship semantics
        query = """
            SELECT source_id, target_id, source_type, target_type, relationship
            FROM citations
            ORDER BY source_id
        """

        self.cursor.execute(query)

        edge_count = 0
        skipped = 0

        while True:
            rows = self.cursor.fetchmany(batch_size)
            if not rows:
                break

            for source_id, target_id, source_type, target_type, relationship in rows:
                # Map to internal indices
                key_source = (source_id, source_type)
                key_target = (target_id, target_type)

                if key_source not in self.external_to_index or key_target not in self.external_to_index:
                    skipped += 1
                    continue

                idx_source = self.external_to_index[key_source]
                idx_target = self.external_to_index[key_target]

                # Handle different relationship semantics
                # 'cites', 'references' -> source to target
                # 'isCitedBy', 'isReferencedBy' -> target to source
                if relationship in ['cites', 'references', 'documents']:
                    self.edge_sources.append(idx_source)
                    self.edge_targets.append(idx_target)
                elif relationship in ['isCitedBy', 'isReferencedBy']:
                    self.edge_sources.append(idx_target)
                    self.edge_targets.append(idx_source)
                else:
                    # Default: source to target
                    self.edge_sources.append(idx_source)
                    self.edge_targets.append(idx_target)

                edge_count += 1

            print(f"  Processed {edge_count:,} edges ({skipped:,} skipped)", end='\r')

        print(f"\n✓ Total edges: {edge_count:,}")
        if skipped > 0:
            print(f"  (Skipped {skipped:,} edges with missing nodes)")

    def extract_authors(self, batch_size: int = 100000):
        """
        Extract author mappings from database in batches.
        """
        print("\n" + "="*80)
        print("EXTRACTING AUTHORS")
        print("="*80 + "\n")

        # First, get all authors
        print("[1/2] Loading author names...")
        query = "SELECT id, name FROM authors ORDER BY id"
        self.cursor.execute(query)

        author_count = 0
        while True:
            rows = self.cursor.fetchmany(batch_size)
            if not rows:
                break

            for author_id, name in rows:
                self._get_or_create_author_id(author_id, name)
                author_count += 1

            print(f"  Processed {author_count:,} authors", end='\r')

        print(f"\n  ✓ Total authors: {author_count:,}")

        # Extract authorships
        print("\n[2/2] Loading authorship mappings...")
        query = """
            SELECT node_id, node_type, author_id
            FROM authorships
            ORDER BY node_id
        """
        self.cursor.execute(query)

        mapping_count = 0
        skipped = 0

        while True:
            rows = self.cursor.fetchmany(batch_size)
            if not rows:
                break

            for node_id, node_type, author_id in rows:
                key = (node_id, node_type)
                if key not in self.external_to_index:
                    skipped += 1
                    continue

                node_idx = self.external_to_index[key]

                if author_id not in self.author_id_map:
                    # Create author without name
                    author_internal_id = self._get_or_create_author_id(author_id)
                else:
                    author_internal_id = self.author_id_map[author_id]

                self.node_to_authors[node_idx].append(author_internal_id)
                mapping_count += 1

            print(f"  Processed {mapping_count:,} mappings ({skipped:,} skipped)", end='\r')

        print(f"\n✓ Total authorship mappings: {mapping_count:,}")
        if skipped > 0:
            print(f"  (Skipped {skipped:,} mappings with missing nodes)")

    def serialize_to_disk(self, prefix: str = 'graph'):
        """
        Serialize all data structures to disk in efficient formats.
        """
        print("\n" + "="*80)
        print("SERIALIZING TO DISK")
        print("="*80 + "\n")

        n_nodes = self.index_counter
        n_edges = len(self.edge_sources)

        # 1. Create sparse adjacency matrix (CSR format - most efficient for matrix operations)
        print("[1/6] Creating sparse adjacency matrix...")
        edge_data = np.ones(n_edges, dtype=np.float32)
        adjacency = sp.csr_matrix(
            (edge_data, (self.edge_sources, self.edge_targets)),
            shape=(n_nodes, n_nodes),
            dtype=np.float32
        )
        print(f"  ✓ Sparse matrix: {n_nodes:,} × {n_nodes:,} with {n_edges:,} edges")
        print(f"  ✓ Sparsity: {100 * (1 - n_edges / (n_nodes * n_nodes)):.6f}%")
        print(f"  ✓ Memory: ~{(adjacency.data.nbytes + adjacency.indices.nbytes + adjacency.indptr.nbytes) / 1e9:.2f} GB")

        # 2. Save adjacency matrix (compressed)
        print("\n[2/6] Saving adjacency matrix...")
        adj_file = os.path.join(self.output_dir, f'{prefix}_adjacency.npz')
        sp.save_npz(adj_file, adjacency, compressed=True)
        file_size = os.path.getsize(adj_file) / 1e9
        print(f"  ✓ Saved to: {adj_file}")
        print(f"  ✓ File size: {file_size:.2f} GB")

        # 3. Save node types (uint8 for memory efficiency)
        print("\n[3/6] Saving node types...")
        node_types_array = np.array(self.node_types, dtype=np.uint8)
        types_file = os.path.join(self.output_dir, f'{prefix}_node_types.npy')
        np.save(types_file, node_types_array)
        print(f"  ✓ Saved to: {types_file}")
        print(f"  ✓ Memory: {node_types_array.nbytes / 1e6:.2f} MB")

        # 4. Save external node IDs
        print("\n[4/6] Saving node ID mappings...")
        node_ids_array = np.array(self.node_external_ids, dtype=np.int64)
        ids_file = os.path.join(self.output_dir, f'{prefix}_node_ids.npy')
        np.save(ids_file, node_ids_array)
        print(f"  ✓ Saved to: {ids_file}")
        print(f"  ✓ Memory: {node_ids_array.nbytes / 1e6:.2f} MB")

        # 5. Save author mappings (compressed numpy format)
        print("\n[5/6] Saving author mappings...")

        # Convert to arrays for efficient storage
        author_node_indices = []
        author_ids_list = []
        author_counts = []

        for node_idx in sorted(self.node_to_authors.keys()):
            authors = self.node_to_authors[node_idx]
            author_node_indices.append(node_idx)
            author_counts.append(len(authors))
            author_ids_list.extend(authors)

        authors_file = os.path.join(self.output_dir, f'{prefix}_authors.npz')
        np.savez_compressed(
            authors_file,
            node_indices=np.array(author_node_indices, dtype=np.int32),
            author_counts=np.array(author_counts, dtype=np.int32),
            author_ids=np.array(author_ids_list, dtype=np.int32)
        )
        file_size = os.path.getsize(authors_file) / 1e6
        print(f"  ✓ Saved to: {authors_file}")
        print(f"  ✓ File size: {file_size:.2f} MB")
        print(f"  ✓ Nodes with authors: {len(author_node_indices):,}")
        print(f"  ✓ Total author assignments: {len(author_ids_list):,}")

        # 6. Save author names (optional, only if needed)
        if self.author_names:
            print("\n[6/6] Saving author names...")
            import json
            names_file = os.path.join(self.output_dir, f'{prefix}_author_names.json')
            # Convert integer keys to strings for JSON
            author_names_str = {str(k): v for k, v in self.author_names.items()}
            with open(names_file, 'w') as f:
                json.dump(author_names_str, f)
            file_size = os.path.getsize(names_file) / 1e6
            print(f"  ✓ Saved to: {names_file}")
            print(f"  ✓ File size: {file_size:.2f} MB")
        else:
            print("\n[6/6] Skipping author names (not extracted)")

        # 7. Save metadata
        print("\nSaving metadata...")
        metadata = {
            'n_nodes': n_nodes,
            'n_edges': n_edges,
            'n_papers': int(np.sum(node_types_array == 0)),
            'n_patents': int(np.sum(node_types_array == 1)),
            'n_clinical_trials': int(np.sum(node_types_array == 2)),
            'n_authors': len(self.author_id_map),
            'prefix': prefix
        }

        import json
        metadata_file = os.path.join(self.output_dir, f'{prefix}_metadata.json')
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        print(f"  ✓ Saved to: {metadata_file}")

        print("\n" + "="*80)
        print("SERIALIZATION COMPLETE")
        print("="*80)
        print(f"\n  Total nodes: {n_nodes:,}")
        print(f"    - Papers: {metadata['n_papers']:,}")
        print(f"    - Patents: {metadata['n_patents']:,}")
        print(f"    - Clinical Trials: {metadata['n_clinical_trials']:,}")
        print(f"  Total edges: {n_edges:,}")
        print(f"  Total authors: {metadata['n_authors']:,}")
        print(f"\n  Output directory: {self.output_dir}/")

        return metadata


def extract_from_database(db_config: Dict[str, str], output_dir: str, prefix: str = 'graph'):
    """
    Main function to extract data from SQL database.

    Args:
        db_config: Database connection parameters
        output_dir: Directory to save serialized files
        prefix: Prefix for output files

    Returns:
        metadata: Dictionary with extraction statistics
    """
    extractor = SQLDataExtractor(db_config, output_dir)

    try:
        # Connect to database
        extractor.connect()

        # Extract data in order
        extractor.extract_nodes()
        extractor.extract_citations()
        extractor.extract_authors()

        # Serialize to disk
        metadata = extractor.serialize_to_disk(prefix)

        return metadata

    finally:
        extractor.close()


if __name__ == "__main__":
    # Example usage
    db_config = {
        'host': 'localhost',
        'database': 'citations_db',
        'user': 'your_username',
        'password': 'your_password',
        'port': 5432
    }

    output_dir = 'data/large_scale_experiment'

    metadata = extract_from_database(db_config, output_dir, prefix='nature_data')

    print("\n✓ Extraction complete!")
    print(f"  Files saved to: {output_dir}/")
