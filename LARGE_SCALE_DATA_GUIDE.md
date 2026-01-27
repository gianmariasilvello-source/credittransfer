# Large-Scale Credit Transfer from SQL Databases

**Complete guide for processing multi-type citation graphs from SQL databases with efficient serialization for very large datasets (50GB+)**

---

## Table of Contents
1. [Overview](#overview)
2. [Data Model for Multi-Type Graphs](#data-model-for-multi-type-graphs)
3. [SQL Database Schema](#sql-database-schema)
4. [Efficient Data Extraction](#efficient-data-extraction)
5. [Memory-Efficient Serialization](#memory-efficient-serialization)
6. [Loading and Processing](#loading-and-processing)
7. [Complete Workflow Example](#complete-workflow-example)
8. [Performance Optimization](#performance-optimization)
9. [Troubleshooting](#troubleshooting)

---

## Overview

This guide covers processing large-scale citation data (papers, patents, clinical trials) from SQL databases into efficient matrix formats for credit transfer calculations.

**Key Features:**
- Handle 50GB+ datasets with millions of nodes
- Multi-type graphs: papers, patents, clinical trials
- Author attribution and h-index calculation
- Memory-efficient sparse matrix formats
- Batch processing from SQL queries
- Fast serialization with numpy's `.npz` format

**Required Libraries:**
```bash
pip install numpy scipy pandas psycopg2-binary tables
```

---

## Data Model for Multi-Type Graphs

### Node Types

For papers, patents, and clinical trials:

```python
TYPE_PAPER = 0
TYPE_PATENT = 1
TYPE_CLINICAL_TRIAL = 2
```

### Core Data Structures

```python
# 1. Adjacency Matrix (sparse CSR format)
adjacency_matrix: scipy.sparse.csr_matrix  # shape: (n_nodes, n_nodes)

# 2. Node Types Array (memory-efficient)
node_types: np.ndarray  # dtype=np.uint8, shape: (n_nodes,)

# 3. Node Metadata (integer IDs only)
node_ids: np.ndarray  # dtype=np.int64, external IDs
node_id_to_index: Dict[int, int]  # external_id -> matrix_index

# 4. Retention Rates Array
retention_rates: np.ndarray  # dtype=np.float32, shape: (n_nodes,)

# 5. Author Mappings (sparse format)
node_to_authors: Dict[int, List[int]]  # node_index -> [author_ids]
author_names: Dict[int, str]  # author_id -> name (optional)
```

### Memory Optimization

**For 10M nodes:**
- `node_types` (uint8): 10 MB
- `retention_rates` (float32): 40 MB  
- `node_ids` (int64): 80 MB
- Total metadata: ~130 MB

**For adjacency matrix (100M edges):**
- Sparse CSR format: ~1.2 GB
- Dense format would be: ~800 TB (infeasible!)

---

## SQL Database Schema

### Expected Database Structure

Based on the Nature Scientific Data paper format:

```sql
-- Publications table
CREATE TABLE publications (
    id BIGINT PRIMARY KEY,
    title TEXT,
    pub_year INT,
    doi TEXT,
    type VARCHAR(50)  -- 'journal-article', 'proceedings-article', etc.
);

-- Patents table
CREATE TABLE patents (
    id BIGINT PRIMARY KEY,
    title TEXT,
    grant_date DATE,
    patent_number TEXT,
    country_code VARCHAR(2)
);

-- Clinical Trials table
CREATE TABLE clinical_trials (
    id BIGINT PRIMARY KEY,
    title TEXT,
    nct_id TEXT,  -- ClinicalTrials.gov identifier
    start_date DATE,
    status VARCHAR(50)
);

-- Citations/Relations table
CREATE TABLE citations (
    source_id BIGINT,
    target_id BIGINT,
    source_type VARCHAR(50),  -- 'paper', 'patent', 'clinical_trial'
    target_type VARCHAR(50),
    relationship VARCHAR(50),  -- 'cites', 'references', 'documents', etc.
    PRIMARY KEY (source_id, target_id, source_type, target_type)
);

-- Authors table
CREATE TABLE authors (
    id BIGINT PRIMARY KEY,
    name TEXT,
    orcid TEXT
);

-- Authorship mapping
CREATE TABLE authorships (
    node_id BIGINT,
    node_type VARCHAR(50),
    author_id BIGINT,
    position INT,  -- author order
    PRIMARY KEY (node_id, node_type, author_id)
);

-- Indexes for efficient queries
CREATE INDEX idx_citations_source ON citations(source_id, source_type);
CREATE INDEX idx_citations_target ON citations(target_id, target_type);
CREATE INDEX idx_authorships_node ON authorships(node_id, node_type);
CREATE INDEX idx_authorships_author ON authorships(author_id);
```

---

## Efficient Data Extraction

### Step 1: SQL Data Extractor Script

Create `extract_from_sql.py`:

```python
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
```

### Step 2: Configuration File

Create `config/sql_extraction.properties`:

```ini
[database]
host = localhost
port = 5432
database = citations_db
user = your_username
password = your_password

[extraction]
batch_size = 100000
output_dir = data/large_scale_experiment
prefix = nature_data

[options]
extract_author_names = true
compress_output = true
```

---

## Memory-Efficient Serialization

### File Formats Comparison

| Format | Read Speed | Write Speed | Compression | Use Case |
|--------|-----------|-------------|-------------|----------|
| **`.npz` (compressed)** | Fast | Medium | Excellent | Large sparse matrices |
| **`.npy`** | Fastest | Fastest | None | Small arrays, metadata |
| **HDF5 (`.h5`)** | Medium | Medium | Good | Very large datasets, streaming |
| **Pickle** | Slow | Slow | Poor | ❌ Avoid for large data |
| **JSON** | Very Slow | Slow | Poor | Metadata only |

### Recommended Structure

```
data/large_scale_experiment/
├── nature_data_adjacency.npz          # Sparse CSR matrix (compressed)
├── nature_data_node_types.npy         # uint8 array
├── nature_data_node_ids.npy           # int64 array
├── nature_data_authors.npz            # Compressed author mappings
├── nature_data_author_names.json      # Optional: human-readable names
└── nature_data_metadata.json          # Graph statistics
```

### File Size Estimates

**For 10M nodes, 100M edges:**
- Adjacency matrix (`.npz`): ~1.2 GB
- Node types (`.npy`): 10 MB
- Node IDs (`.npy`): 80 MB
- Authors (`.npz`): ~200 MB
- **Total: ~1.5 GB**

**For 50M nodes, 1B edges:**
- Adjacency matrix (`.npz`): ~12 GB
- Node types (`.npy`): 50 MB
- Node IDs (`.npy`): 400 MB
- Authors (`.npz`): ~1 GB
- **Total: ~13.5 GB**

---

## Loading and Processing

### Efficient Data Loader

Create `load_large_scale_data.py`:

```python
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
```

---

## Complete Workflow Example

### Full Pipeline Script

Create `run_large_scale_experiment.py`:

```python
"""
Complete workflow for large-scale credit transfer from SQL database
"""

import sys
import os
import numpy as np
import time

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from extract_from_sql import extract_from_database
from load_large_scale_data import LargeScaleDataLoader
from credit.generalFormulation import GeneralCreditTransfer
from credit.authorMetrics import calculate_h_index_from_kudos


def run_large_scale_experiment(
    db_config: dict,
    output_dir: str,
    paper_retention: float = 0.5,
    patent_retention: float = 0.5,
    clinical_trial_retention: float = 0.5,
    extract_data: bool = True
):
    """
    Complete large-scale credit transfer experiment.
    
    Args:
        db_config: Database connection parameters
        output_dir: Directory for data and results
        paper_retention: Retention rate for papers
        patent_retention: Retention rate for patents
        clinical_trial_retention: Retention rate for clinical trials
        extract_data: Whether to extract from SQL (or use existing files)
    """
    
    print("\n" + "="*80)
    print("LARGE-SCALE CREDIT TRANSFER EXPERIMENT")
    print("="*80 + "\n")
    
    prefix = 'nature_data'
    
    # Step 1: Extract data from SQL (if needed)
    if extract_data:
        print("STEP 1: Extracting data from SQL database...")
        print("-"*80 + "\n")
        
        start_time = time.time()
        metadata = extract_from_database(db_config, output_dir, prefix)
        elapsed = time.time() - start_time
        
        print(f"\n✓ Extraction completed in {elapsed/60:.1f} minutes")
    else:
        print("STEP 1: Skipping extraction (using existing files)")
    
    # Step 2: Load data
    print("\n" + "="*80)
    print("STEP 2: Loading serialized data...")
    print("-"*80 + "\n")
    
    start_time = time.time()
    loader = LargeScaleDataLoader(output_dir, prefix)
    adjacency, node_types, node_ids, node_to_authors, author_names, metadata = loader.load_all(
        load_author_names=True
    )
    elapsed = time.time() - start_time
    print(f"\n✓ Loading completed in {elapsed:.1f} seconds")
    
    # Step 3: Create retention rates
    print("\n" + "="*80)
    print("STEP 3: Setting retention rates...")
    print("-"*80 + "\n")
    
    retention_rates = loader.create_retention_rates(
        paper_rate=paper_retention,
        patent_rate=patent_retention,
        clinical_trial_rate=clinical_trial_retention
    )
    
    # Step 4: Run credit transfer
    print("\n" + "="*80)
    print("STEP 4: Computing credit transfer...")
    print("-"*80 + "\n")
    
    start_time = time.time()
    
    credit_calc = GeneralCreditTransfer(
        adjacency=adjacency,
        retention_rates=retention_rates,
        use_integer_ids=True,
        enable_convergence_check=True
    )
    
    kudos, total_credit = credit_calc.compute()
    elapsed = time.time() - start_time
    
    print(f"\n✓ Credit computation completed in {elapsed/60:.1f} minutes")
    print(f"  Convergence: {'Yes' if credit_calc.converged else 'No'}")
    print(f"  Iterations: {credit_calc.iterations}")
    
    # Step 5: Calculate h-indices
    print("\n" + "="*80)
    print("STEP 5: Computing author h-indices...")
    print("-"*80 + "\n")
    
    start_time = time.time()
    
    h_indices_kudos, direct_citations = calculate_h_index_from_kudos(
        kudos, node_to_authors, author_names
    )
    
    h_indices_total = calculate_h_index_from_kudos(
        total_credit, node_to_authors, author_names
    )[0]
    
    elapsed = time.time() - start_time
    print(f"\n✓ H-index computation completed in {elapsed:.1f} seconds")
    
    # Step 6: Save results
    print("\n" + "="*80)
    print("STEP 6: Saving results...")
    print("-"*80 + "\n")
    
    results_dir = os.path.join(output_dir, 'results')
    os.makedirs(results_dir, exist_ok=True)
    
    # Save credit scores
    np.savez_compressed(
        os.path.join(results_dir, f'{prefix}_credits.npz'),
        kudos=kudos,
        total_credit=total_credit
    )
    print(f"  ✓ Saved credit scores")
    
    # Save h-indices
    import json
    
    h_indices_file = os.path.join(results_dir, f'{prefix}_h_indices.json')
    with open(h_indices_file, 'w') as f:
        json.dump({
            'h_indices_kudos': {str(k): int(v) for k, v in h_indices_kudos.items()},
            'h_indices_total': {str(k): int(v) for k, v in h_indices_total.items()},
            'direct_citations': {str(k): int(v) for k, v in direct_citations.items()}
        }, f, indent=2)
    print(f"  ✓ Saved h-indices")
    
    # Save top authors
    print("\n  Top 20 authors by h-index (kudos):")
    sorted_authors = sorted(h_indices_kudos.items(), key=lambda x: x[1], reverse=True)[:20]
    for rank, (author_id, h_idx) in enumerate(sorted_authors, 1):
        author_name = author_names.get(author_id, f"Author_{author_id}")
        direct_cites = direct_citations.get(author_id, 0)
        print(f"    {rank:2d}. {author_name[:40]:40s} h={h_idx:3d} (direct citations: {direct_cites})")
    
    print("\n" + "="*80)
    print("EXPERIMENT COMPLETE")
    print("="*80)
    print(f"\n  Results saved to: {results_dir}/")
    
    return {
        'kudos': kudos,
        'total_credit': total_credit,
        'h_indices_kudos': h_indices_kudos,
        'h_indices_total': h_indices_total,
        'direct_citations': direct_citations
    }


if __name__ == "__main__":
    # Configuration
    db_config = {
        'host': 'localhost',
        'database': 'citations_db',
        'user': 'your_username',
        'password': 'your_password',
        'port': 5432
    }
    
    output_dir = 'data/large_scale_experiment'
    
    # Run experiment
    results = run_large_scale_experiment(
        db_config=db_config,
        output_dir=output_dir,
        paper_retention=0.5,
        patent_retention=0.5,
        clinical_trial_retention=0.5,
        extract_data=True  # Set to False to skip SQL extraction
    )
    
    print("\n✓ All done!")
```

---

## Performance Optimization

### Memory Optimization Tips

1. **Use appropriate data types:**
   ```python
   # Instead of default int64
   node_types = np.array(types, dtype=np.uint8)  # Saves 87.5% memory
   
   # Instead of float64
   retention_rates = np.array(rates, dtype=np.float32)  # Saves 50% memory
   ```

2. **Sparse matrix format selection:**
   ```python
   # CSR for row operations (most common)
   adjacency_csr = sp.csr_matrix(...)
   
   # CSC for column operations
   adjacency_csc = adjacency_csr.tocsc()
   
   # COO for construction only
   adjacency_coo = sp.coo_matrix(...)
   adjacency_csr = adjacency_coo.tocsr()
   ```

3. **Batch processing for SQL queries:**
   ```python
   batch_size = 100000  # Process 100K rows at a time
   cursor.execute(query)
   while True:
       rows = cursor.fetchmany(batch_size)
       if not rows:
           break
       # Process batch
   ```

### Computation Optimization

1. **Use sparse matrix operations:**
   ```python
   # Efficient: uses sparse operations
   result = adjacency @ vector
   
   # Inefficient: converts to dense
   result = adjacency.toarray() @ vector  # DON'T DO THIS!
   ```

2. **Enable convergence checking:**
   ```python
   credit_calc = GeneralCreditTransfer(
       adjacency=adjacency,
       retention_rates=retention_rates,
       enable_convergence_check=True,
       convergence_threshold=1e-6,
       max_iterations=100
   )
   ```

3. **Parallel processing (for multiple experiments):**
   ```python
   from multiprocessing import Pool
   
   def run_experiment(retention_params):
       # Run single experiment
       return results
   
   # Run multiple retention strategies in parallel
   with Pool(4) as pool:
       all_results = pool.map(run_experiment, retention_params_list)
   ```

### Disk I/O Optimization

1. **Compressed formats:**
   ```python
   # Save compressed (slower write, smaller file)
   sp.save_npz('adjacency.npz', matrix, compressed=True)
   np.savez_compressed('data.npz', **arrays)
   
   # Save uncompressed (faster, larger file)
   np.save('array.npy', array)
   ```

2. **Memory mapping for very large files:**
   ```python
   # Memory-map array (doesn't load into RAM)
   large_array = np.load('huge_array.npy', mmap_mode='r')
   ```

---

## Troubleshooting

### Out of Memory Errors

**Problem:** `MemoryError` when loading adjacency matrix

**Solutions:**
1. Check available RAM:
   ```python
   import psutil
   print(f"Available RAM: {psutil.virtual_memory().available / 1e9:.1f} GB")
   ```

2. Use memory mapping:
   ```python
   # Don't load full matrix into memory
   adjacency = sp.load_npz('adjacency.npz')
   # Process in chunks
   ```

3. Process in batches:
   ```python
   # Split graph into subgraphs
   n_nodes = metadata['n_nodes']
   chunk_size = 1000000
   for i in range(0, n_nodes, chunk_size):
       subgraph = adjacency[i:i+chunk_size, :]
       # Process subgraph
   ```

### Slow SQL Queries

**Problem:** Extraction takes too long

**Solutions:**
1. Add database indexes:
   ```sql
   CREATE INDEX idx_citations_source ON citations(source_id, source_type);
   CREATE INDEX idx_authorships_node ON authorships(node_id, node_type);
   ```

2. Increase batch size:
   ```python
   batch_size = 500000  # Larger batches = fewer round trips
   ```

3. Use database connection pooling:
   ```python
   from psycopg2 import pool
   connection_pool = pool.SimpleConnectionPool(1, 20, **db_config)
   ```

### Convergence Issues

**Problem:** Credit transfer doesn't converge

**Solutions:**
1. Check for cycles in the graph:
   ```python
   # DAG shouldn't have cycles
   import networkx as nx
   G = nx.DiGraph(adjacency)
   cycles = list(nx.simple_cycles(G))
   print(f"Found {len(cycles)} cycles")
   ```

2. Increase max iterations:
   ```python
   credit_calc = GeneralCreditTransfer(
       ...,
       max_iterations=200  # Increase from default
   )
   ```

3. Adjust convergence threshold:
   ```python
   convergence_threshold=1e-5  # Less strict (faster)
   ```

---

## Quick Reference

### Essential Commands

```bash
# 1. Install dependencies
pip install numpy scipy pandas psycopg2-binary

# 2. Extract from SQL database
python extract_from_sql.py

# 3. Load and process
python run_large_scale_experiment.py

# 4. View results
ls -lh data/large_scale_experiment/results/
```

### File Formats Summary

| File | Format | Size (10M nodes) | Purpose |
|------|--------|-----------------|---------|
| `*_adjacency.npz` | Sparse CSR | ~1.2 GB | Graph structure |
| `*_node_types.npy` | uint8 array | 10 MB | Node type codes |
| `*_node_ids.npy` | int64 array | 80 MB | External IDs |
| `*_authors.npz` | Compressed | ~200 MB | Author mappings |
| `*_author_names.json` | JSON | ~50 MB | Human-readable names |
| `*_metadata.json` | JSON | <1 MB | Statistics |

### Memory Requirements

| Graph Size | Nodes | Edges | RAM Needed | Disk Space |
|-----------|-------|-------|-----------|-----------|
| Small | 100K | 1M | 1 GB | 100 MB |
| Medium | 1M | 10M | 4 GB | 500 MB |
| Large | 10M | 100M | 16 GB | 1.5 GB |
| Very Large | 50M | 1B | 64 GB | 13 GB |

---

**Date:** January 27, 2026  
**Version:** 1.0  
**Compatible with:** Nature Scientific Data (2025) multi-type citation graphs
