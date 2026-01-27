# Quick Reference: Large-Scale Data from Nature Scientific Data Paper

**Processing multi-type citation graphs (papers, patents, clinical trials) from SQL databases**

---

## 📊 Data Model

### Node Types
```python
TYPE_PAPER = 0
TYPE_PATENT = 1
TYPE_CLINICAL_TRIAL = 2
```

### Key Data Structures
1. **Adjacency Matrix**: `scipy.sparse.csr_matrix` (compressed sparse row)
2. **Node Types**: `np.ndarray` with `dtype=uint8` 
3. **Retention Rates**: `np.ndarray` with `dtype=float32`
4. **Author Mappings**: `Dict[int, List[int]]` (node_index → author_ids)

---

## 🚀 Quick Start (3 Steps)

### Step 1: Configure Database Connection

Edit `config/sql_extraction.properties`:
```ini
[database]
host = your_host
database = citations_db
user = your_username
password = your_password

[extraction]
output_dir = data/large_scale_experiment
prefix = nature_data
```

### Step 2: Extract from SQL

```bash
python3 extract_from_sql.py
```

**What it does:**
- Extracts papers, patents, clinical trials
- Builds adjacency matrix (edges)
- Maps authors to nodes
- Serializes to disk in compressed format

**Output files:**
```
data/large_scale_experiment/
├── nature_data_adjacency.npz      # Sparse matrix (compressed)
├── nature_data_node_types.npy     # uint8 array
├── nature_data_node_ids.npy       # int64 array
├── nature_data_authors.npz        # Compressed author mappings
├── nature_data_author_names.json  # Human-readable names
└── nature_data_metadata.json      # Graph statistics
```

### Step 3: Run Credit Transfer

```python
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
    use_integer_ids=True,
    enable_convergence_check=True
)
kudos, total_credit = ct.compute()

# Calculate h-indices
h_indices_kudos, direct_citations = calculate_h_index_from_kudos(
    kudos, node_to_authors, author_names
)
```

---

## 📦 File Formats

### Adjacency Matrix (`.npz`)
- **Format**: Compressed sparse CSR
- **Size**: ~12 bytes per edge
- **Load**: `sp.load_npz('file.npz')`

### Node Types (`.npy`)
- **Format**: uint8 array
- **Size**: 1 byte per node
- **Load**: `np.load('file.npy')`

### Authors (`.npz`)
- **Format**: Compressed arrays (node_indices, author_counts, author_ids)
- **Size**: ~4 bytes per author assignment
- **Load**: `np.load('file.npz')`

---

## 💾 Memory Requirements

| Nodes | Edges | RAM | Disk Space |
|-------|-------|-----|-----------|
| 1M | 10M | 4 GB | 500 MB |
| 10M | 100M | 16 GB | 1.5 GB |
| 50M | 1B | 64 GB | 13 GB |

**Optimization tips:**
- Use `dtype=uint8` for node types (87.5% smaller than int64)
- Use `dtype=float32` for retention rates (50% smaller than float64)
- Always use sparse matrices (never convert to dense!)

---

## 🔧 SQL Schema Requirements

### Minimal Required Tables

```sql
-- Papers
publications (id BIGINT, title TEXT, ...)

-- Patents
patents (id BIGINT, patent_number TEXT, ...)

-- Clinical Trials
clinical_trials (id BIGINT, nct_id TEXT, ...)

-- Citations/Relations
citations (
    source_id BIGINT,
    target_id BIGINT,
    source_type VARCHAR,
    target_type VARCHAR,
    relationship VARCHAR
)

-- Authors
authors (id BIGINT, name TEXT)

-- Authorship
authorships (
    node_id BIGINT,
    node_type VARCHAR,
    author_id BIGINT
)
```

### Required Indexes

```sql
CREATE INDEX idx_citations_source ON citations(source_id, source_type);
CREATE INDEX idx_citations_target ON citations(target_id, target_type);
CREATE INDEX idx_authorships_node ON authorships(node_id, node_type);
CREATE INDEX idx_authorships_author ON authorships(author_id);
```

---

## ⚡ Performance Tips

### Extraction
1. **Batch size**: 100K-500K rows per fetch
2. **Use indexes**: See SQL schema above
3. **Connection pooling**: For parallel extraction

### Processing
1. **Sparse operations**: Always use `@` operator (don't convert to dense!)
2. **Integer IDs**: Set `use_integer_ids=True` (10-50x faster)
3. **Convergence check**: Enable to stop early

### Memory
1. **Memory mapping**: For very large arrays
2. **Batch processing**: Split graph into chunks if needed
3. **Compression**: Use `.npz` format with compression

---

## 🎯 Retention Rate Examples

### Scenario 1: Papers transfer more credit
```python
retention_rates = loader.create_retention_rates(
    paper_rate=0.3,          # 70% transfer
    patent_rate=0.8,         # 20% transfer
    clinical_trial_rate=0.8  # 20% transfer
)
```

### Scenario 2: Equal transfer
```python
retention_rates = loader.create_retention_rates(
    paper_rate=0.5,
    patent_rate=0.5,
    clinical_trial_rate=0.5
)
```

### Scenario 3: No transitivity (baseline)
```python
retention_rates = loader.create_retention_rates(
    paper_rate=1.0,
    patent_rate=1.0,
    clinical_trial_rate=1.0
)
```

---

## 📖 Relationship Semantics

**From source to target:**
- `cites` - Paper A cites Paper B → edge A→B
- `references` - Paper A references Patent B → edge A→B
- `documents` - Paper A documents Clinical Trial B → edge A→B

**From target to source:**
- `isCitedBy` - Paper A isCitedBy Paper B → edge B→A
- `isReferencedBy` - Paper A isReferencedBy Patent B → edge B→A

---

## ❓ Troubleshooting

### Out of Memory
```python
# Check available RAM
import psutil
print(f"RAM: {psutil.virtual_memory().available / 1e9:.1f} GB")

# Use memory mapping for large arrays
large_array = np.load('huge.npy', mmap_mode='r')
```

### Slow SQL Queries
- Add database indexes (see schema above)
- Increase batch_size in config
- Use connection pooling

### Convergence Issues
- Check for cycles: `nx.simple_cycles(G)`
- Increase max_iterations
- Adjust convergence_threshold

---

## 📚 Full Documentation

- **Complete Guide**: [LARGE_SCALE_DATA_GUIDE.md](LARGE_SCALE_DATA_GUIDE.md)
- **Synthetic Graphs**: [SYNTHETIC_GRAPHS_GUIDE.md](SYNTHETIC_GRAPHS_GUIDE.md)
- **Main README**: [README.md](README.md)

---

**Date:** January 27, 2026  
**Version:** 1.0  
**Paper**: Nature Scientific Data (2025) - https://www.nature.com/articles/s41597-025-05343-8
