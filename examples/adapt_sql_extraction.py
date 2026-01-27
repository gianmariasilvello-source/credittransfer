"""
Example: Adapt SQL extraction for your specific database schema

This example shows how to customize extract_from_sql.py for different
database schemas, particularly for the Nature Scientific Data paper format.
"""

# ============================================================================
# EXAMPLE 1: Custom SQL Queries for Your Schema
# ============================================================================

# If your publications table has different column names:
def extract_publications_custom(self, batch_size=100000):
    """Extract publications with custom schema."""
    print("\n[1/3] Extracting publications...")
    
    # Customize this query for your schema
    query = """
        SELECT 
            pub_id as id,           -- Your ID column name
            pub_type as type        -- Your type column name
        FROM research_papers        -- Your table name
        WHERE year >= 2000          -- Optional: filter by year
        ORDER BY pub_id
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


# ============================================================================
# EXAMPLE 2: Different Relationship Semantics
# ============================================================================

def extract_citations_custom(self, batch_size=100000):
    """
    Extract citations with custom relationship semantics.
    
    Adapt this based on how relationships are stored in your database.
    """
    print("\n" + "="*80)
    print("EXTRACTING CITATIONS")
    print("="*80 + "\n")
    
    # Example: Your database might have separate tables for each type
    
    # 1. Paper-to-paper citations
    query_paper_paper = """
        SELECT citing_paper_id, cited_paper_id
        FROM paper_citations
    """
    self.cursor.execute(query_paper_paper)
    count = 0
    while True:
        rows = self.cursor.fetchmany(batch_size)
        if not rows:
            break
        for citing_id, cited_id in rows:
            idx_source = self.external_to_index.get((citing_id, 'paper'))
            idx_target = self.external_to_index.get((cited_id, 'paper'))
            if idx_source is not None and idx_target is not None:
                self.edge_sources.append(idx_source)
                self.edge_targets.append(idx_target)
                count += 1
    print(f"  Paper-to-paper citations: {count:,}")
    
    # 2. Paper-to-patent citations
    query_paper_patent = """
        SELECT paper_id, patent_id
        FROM paper_patent_citations
    """
    self.cursor.execute(query_paper_patent)
    count = 0
    while True:
        rows = self.cursor.fetchmany(batch_size)
        if not rows:
            break
        for paper_id, patent_id in rows:
            idx_source = self.external_to_index.get((paper_id, 'paper'))
            idx_target = self.external_to_index.get((patent_id, 'patent'))
            if idx_source is not None and idx_target is not None:
                self.edge_sources.append(idx_source)
                self.edge_targets.append(idx_target)
                count += 1
    print(f"  Paper-to-patent citations: {count:,}")
    
    # 3. Paper-to-clinical trial citations
    query_paper_trial = """
        SELECT paper_id, trial_id
        FROM paper_trial_citations
    """
    self.cursor.execute(query_paper_trial)
    count = 0
    while True:
        rows = self.cursor.fetchmany(batch_size)
        if not rows:
            break
        for paper_id, trial_id in rows:
            idx_source = self.external_to_index.get((paper_id, 'paper'))
            idx_target = self.external_to_index.get((trial_id, 'clinical_trial'))
            if idx_source is not None and idx_target is not None:
                self.edge_sources.append(idx_source)
                self.edge_targets.append(idx_target)
                count += 1
    print(f"  Paper-to-clinical trial citations: {count:,}")


# ============================================================================
# EXAMPLE 3: Loading from CSV Files (Alternative to SQL)
# ============================================================================

import pandas as pd
import numpy as np
from collections import defaultdict

def load_from_csv_files(data_dir: str, output_dir: str):
    """
    Alternative: Load data from CSV files instead of SQL database.
    
    Use this if your data is in CSV format from the Nature paper.
    """
    
    print("="*80)
    print("LOADING FROM CSV FILES")
    print("="*80 + "\n")
    
    # Load papers
    print("[1/5] Loading papers...")
    papers_df = pd.read_csv(f'{data_dir}/papers.csv')
    print(f"  ✓ Loaded {len(papers_df):,} papers")
    
    # Load patents
    print("[2/5] Loading patents...")
    patents_df = pd.read_csv(f'{data_dir}/patents.csv')
    print(f"  ✓ Loaded {len(patents_df):,} patents")
    
    # Load clinical trials
    print("[3/5] Loading clinical trials...")
    trials_df = pd.read_csv(f'{data_dir}/clinical_trials.csv')
    print(f"  ✓ Loaded {len(trials_df):,} clinical trials")
    
    # Load citations
    print("[4/5] Loading citations...")
    citations_df = pd.read_csv(f'{data_dir}/citations.csv')
    print(f"  ✓ Loaded {len(citations_df):,} citations")
    
    # Load authors
    print("[5/5] Loading authors...")
    authors_df = pd.read_csv(f'{data_dir}/authors.csv')
    authorships_df = pd.read_csv(f'{data_dir}/authorships.csv')
    print(f"  ✓ Loaded {len(authors_df):,} authors")
    print(f"  ✓ Loaded {len(authorships_df):,} authorships")
    
    # Create mappings
    external_to_index = {}
    node_types = []
    node_external_ids = []
    index_counter = 0
    
    # Map papers
    for paper_id in papers_df['id']:
        external_to_index[(paper_id, 'paper')] = index_counter
        node_types.append(0)
        node_external_ids.append(paper_id)
        index_counter += 1
    
    # Map patents
    for patent_id in patents_df['id']:
        external_to_index[(patent_id, 'patent')] = index_counter
        node_types.append(1)
        node_external_ids.append(patent_id)
        index_counter += 1
    
    # Map clinical trials
    for trial_id in trials_df['id']:
        external_to_index[(trial_id, 'clinical_trial')] = index_counter
        node_types.append(2)
        node_external_ids.append(trial_id)
        index_counter += 1
    
    print(f"\n✓ Total nodes: {index_counter:,}")
    
    # Build edge list
    edge_sources = []
    edge_targets = []
    
    for _, row in citations_df.iterrows():
        source_key = (row['source_id'], row['source_type'])
        target_key = (row['target_id'], row['target_type'])
        
        if source_key in external_to_index and target_key in external_to_index:
            idx_source = external_to_index[source_key]
            idx_target = external_to_index[target_key]
            edge_sources.append(idx_source)
            edge_targets.append(idx_target)
    
    print(f"✓ Total edges: {len(edge_sources):,}")
    
    # Build author mappings
    node_to_authors = defaultdict(list)
    author_id_map = {}
    author_names = {}
    
    for _, row in authorships_df.iterrows():
        node_key = (row['node_id'], row['node_type'])
        if node_key in external_to_index:
            node_idx = external_to_index[node_key]
            author_id = row['author_id']
            
            if author_id not in author_id_map:
                internal_id = len(author_id_map)
                author_id_map[author_id] = internal_id
                # Get author name from authors_df
                author_row = authors_df[authors_df['id'] == author_id]
                if not author_row.empty:
                    author_names[internal_id] = author_row.iloc[0]['name']
            
            node_to_authors[node_idx].append(author_id_map[author_id])
    
    print(f"✓ Total authors: {len(author_id_map):,}")
    print(f"✓ Author mappings: {sum(len(v) for v in node_to_authors.values()):,}")
    
    # Convert to numpy arrays and serialize (same as SQL version)
    import scipy.sparse as sp
    import os
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Create sparse adjacency matrix
    n_nodes = index_counter
    n_edges = len(edge_sources)
    adjacency = sp.csr_matrix(
        (np.ones(n_edges, dtype=np.float32), (edge_sources, edge_targets)),
        shape=(n_nodes, n_nodes),
        dtype=np.float32
    )
    
    # Save files
    sp.save_npz(f'{output_dir}/nature_data_adjacency.npz', adjacency, compressed=True)
    np.save(f'{output_dir}/nature_data_node_types.npy', np.array(node_types, dtype=np.uint8))
    np.save(f'{output_dir}/nature_data_node_ids.npy', np.array(node_external_ids, dtype=np.int64))
    
    # Save author mappings
    author_node_indices = []
    author_ids_list = []
    author_counts = []
    for node_idx in sorted(node_to_authors.keys()):
        authors = node_to_authors[node_idx]
        author_node_indices.append(node_idx)
        author_counts.append(len(authors))
        author_ids_list.extend(authors)
    
    np.savez_compressed(
        f'{output_dir}/nature_data_authors.npz',
        node_indices=np.array(author_node_indices, dtype=np.int32),
        author_counts=np.array(author_counts, dtype=np.int32),
        author_ids=np.array(author_ids_list, dtype=np.int32)
    )
    
    # Save author names
    import json
    with open(f'{output_dir}/nature_data_author_names.json', 'w') as f:
        json.dump({str(k): v for k, v in author_names.items()}, f)
    
    # Save metadata
    metadata = {
        'n_nodes': n_nodes,
        'n_edges': n_edges,
        'n_papers': int(np.sum(np.array(node_types) == 0)),
        'n_patents': int(np.sum(np.array(node_types) == 1)),
        'n_clinical_trials': int(np.sum(np.array(node_types) == 2)),
        'n_authors': len(author_id_map),
        'prefix': 'nature_data'
    }
    
    with open(f'{output_dir}/nature_data_metadata.json', 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print("\n" + "="*80)
    print("CSV LOADING COMPLETE")
    print("="*80)
    print(f"\n✓ Files saved to: {output_dir}/")
    
    return metadata


# ============================================================================
# EXAMPLE 4: Using the Custom Loader
# ============================================================================

if __name__ == "__main__":
    
    # Option 1: Load from SQL (if you have PostgreSQL database)
    print("OPTION 1: SQL DATABASE\n")
    print("Uncomment and configure database connection:")
    print("""
    from extract_from_sql import extract_from_database
    
    db_config = {
        'host': 'your_host',
        'database': 'your_database',
        'user': 'your_username',
        'password': 'your_password',
        'port': 5432
    }
    
    metadata = extract_from_database(
        db_config=db_config,
        output_dir='data/large_scale_experiment',
        prefix='nature_data'
    )
    """)
    
    print("\n" + "="*80 + "\n")
    
    # Option 2: Load from CSV files
    print("OPTION 2: CSV FILES\n")
    print("Example usage:")
    print("""
    metadata = load_from_csv_files(
        data_dir='source_data/nature_paper',
        output_dir='data/large_scale_experiment'
    )
    """)
    
    print("\n" + "="*80 + "\n")
    
    # Option 3: Use existing serialized files
    print("OPTION 3: USE EXISTING SERIALIZED FILES\n")
    print("""
    from load_large_scale_data import LargeScaleDataLoader
    from credit.generalFormulation import GeneralCreditTransfer
    from credit.authorMetrics import calculate_h_index_from_kudos
    
    # Load data
    loader = LargeScaleDataLoader('data/large_scale_experiment', 'nature_data')
    adjacency, node_types, node_ids, node_to_authors, author_names, metadata = loader.load_all()
    
    # Set retention rates
    retention_rates = loader.create_retention_rates(
        paper_rate=0.5,
        patent_rate=0.5,
        clinical_trial_rate=0.5
    )
    
    # Compute credit transfer
    ct = GeneralCreditTransfer(
        adjacency=adjacency,
        retention_rates=retention_rates,
        use_integer_ids=True
    )
    kudos, total_credit = ct.compute()
    
    # Calculate h-indices
    h_indices_kudos, direct_citations = calculate_h_index_from_kudos(
        kudos, node_to_authors, author_names
    )
    
    # Print top authors
    sorted_authors = sorted(h_indices_kudos.items(), key=lambda x: x[1], reverse=True)[:20]
    for rank, (author_id, h_idx) in enumerate(sorted_authors, 1):
        name = author_names.get(author_id, f"Author_{author_id}")
        cites = direct_citations.get(author_id, 0)
        print(f"{rank:2d}. {name:40s} h={h_idx:3d} (citations: {cites})")
    """)
    
    print("\n" + "="*80)
    print("Choose the option that fits your data format!")
    print("="*80)
