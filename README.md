# Credit Transfer Project

Transitive credit distribution for citation networks with multi-type nodes and author h-index calculation.

## Quick Start

```python
from graph.GraphUtils import Graph
from credit.generalFormulation import GeneralCreditTransfer

# Create graph
graph = Graph(is_directed=True)
graph.add_edge(0, 1)
graph.add_edge(0, 2)

# Compute credit (20% retention)
ct = GeneralCreditTransfer(graph)
ct.set_uniform_retention(0.2)
total_credit, kudos, _ = ct.compute_credit_distribution()
```

## Features

- **Transitive credit** distribution without global damping
- **Multi-type nodes** (papers, datasets, software) with different retention rates
- **Author h-index** calculation from kudos
- **Sparse matrices** for large graphs (100K+ nodes)
- **Integer indexing** for 10-50x performance boost
- **Property file** configuration

## Installation

```bash
git clone https://github.com/yourusername/CreditTransferProject.git
cd CreditTransferProject
pip install -r requirements.txt
```

## Usage

### Basic Example

```python
import numpy as np
from graph.GraphUtils import Graph
from credit.generalFormulation import GeneralCreditTransfer
from credit.authorMetrics import AuthorMetrics

# Create citation graph
graph = Graph(is_directed=True)
graph.add_edge(0, 1)  # Paper 0 cites Paper 1
graph.add_edge(0, 2)  # Paper 0 cites Dataset 2

# Node types: 0=paper, 1=dataset
node_types = np.array([0, 0, 1])

# Compute credit with type-specific retention
ct = GeneralCreditTransfer(graph, node_types=node_types)
ct.set_retention_by_type(np.array([0.2, 0.9]))  # Papers 20%, Datasets 90%
total_credit, kudos, _ = ct.compute_credit_distribution()

# Calculate author h-indices
node_to_authors = {0: [1, 2], 1: [1], 2: [2, 3]}
author_names = {1: "Smith, J.", 2: "Jones, M.", 3: "Lee, S."}
metrics = AuthorMetrics(node_to_authors, author_names)
h_indices = metrics.compute_all_h_indices(kudos)
```

### Using Property Files

```bash
python3 creditRunner.py config/multi_type.properties
```

## MES Experiment

The Marine Ecosystem Studies (MES) dataset provides a real-world test case.

### Data Preparation

```bash
python3 experiments/prepare_mes_data.py
```

Parses source JSONL files from `source_graph_data/curated_MES/` and creates:
- `data/mes_experiment/mes_adjacency.txt` (~174 MB)
- `data/mes_experiment/mes_node_types.txt`
- `data/mes_experiment/mes_authors.txt`
- `data/mes_experiment/mes_author_names.txt`
- `data/mes_experiment/mes_metadata.json`

### Run Experiment

```bash
python3 experiments/run_mes_experiment.py
```

Results saved to `output/mes_experiment/`:
- `mes_credit_results.txt` - Per-node credit and kudos
- `mes_author_hindices.txt` - H-indices for all authors
- `mes_experiment_summary.json` - Summary with top 100 authors

### Configuration

Edit `config/mes_experiment.properties`:

```ini
[parameters]
num_types = 3
type_0_retention = 0.2   # Papers
type_1_retention = 0.9   # Datasets
type_2_retention = 0.7   # Software
```

## Mathematical Foundation

**Credit equation:**
```
c = (I - A^T)^{-1} v
```

**Kudos equation:**
```
k = [I - diag(A·1)] c
```

Where:
- `c` = total credit vector
- `k` = kudos (retained credit)
- `A` = transfer matrix
- `v` = external credit (indegree)

## API Reference

### GeneralCreditTransfer

```python
ct = GeneralCreditTransfer(graph, node_types=None, use_integer_indices=None)
ct.set_uniform_retention(rate)
ct.set_retention_by_type(rates_array)
total_credit, kudos, diagnostics = ct.compute_credit_distribution(
    check_convergence=True,
    use_sparse_eigensolver=True
)
```

### AuthorMetrics

```python
metrics = AuthorMetrics(node_to_authors, author_names)
h_indices = metrics.compute_all_h_indices(kudos)
metrics.display_author_report(kudos, top_k=20)
```

### Graph

```python
graph = Graph(is_directed=True)
graph.add_node(node)
graph.add_edge(source, target)
graph = Graph.from_matrix(nodes, matrix, is_directed=True)
```

## Performance

- **Integer indexing**: 10-50x faster for large graphs
- **Sparse matrices**: Handles 100K+ nodes efficiently
- **Vectorized operations**: NumPy for author metrics

**Benchmarks:**
- 1,000 nodes: ~0.1s
- 10,000 nodes: ~1.2s
- 100,000 nodes: ~45s

## File Structure

```
CreditTransferProject/
├── credit/
│   ├── generalFormulation.py    # Core algorithm
│   ├── authorMetrics.py          # H-index computation
│   └── creditUtils.py
├── graph/
│   └── GraphUtils.py             # Graph structure
├── dataprocessing/
│   ├── MESProcessor.py           # MES data parser
│   └── MES_SEMANTICS_REFERENCE.md
├── experiments/
│   ├── prepare_mes_data.py
│   └── run_mes_experiment.py
├── config/
│   ├── multi_type.properties
│   └── mes_experiment.properties
├── test/
├── creditRunner.py
└── README.md
```

## MES Dataset Structure

**Source files** (`source_graph_data/curated_MES/`):
- `authors.jsonl` - Author metadata with fullnames
- `publications.jsonl` - Research papers
- `datasets.jsonl` - Research datasets
- `software.jsonl` - Software tools
- `relations.jsonl` - All relationships (citations, authorship)

**Relationship semantics:**
- `references`, `cites` - Citation relationships
- `HasAuthor` - Node to author mappings
- `IsSupplementTo`, `IsSupplementedBy` - Supplementary relationships
- `isPartOf` - Hierarchical relationships

See `dataprocessing/MES_SEMANTICS_REFERENCE.md` for complete details.

## Synthetic Graph Generation

Generate realistic citation networks with configurable properties for controlled experiments.

### Quick Start
```bash
# Generate and compare rankings (includes Direct Citations baseline)
python3 experiments/run_ranking_comparison.py config/synthetic_small.properties
```

### Features
- **DAG structure** - Papers cite only earlier papers
- **Power-law in-degree** - Few highly-cited papers
- **Community structure** - Research subfields
- **Transitivity** - Triangle formation
- **Authors with h-index** - Power-law productivity
- **6 retention strategies** - Including Direct Citations baseline (no transitivity)

### Complete Guide
See **[SYNTHETIC_GRAPHS_GUIDE.md](SYNTHETIC_GRAPHS_GUIDE.md)** for:
- Complete parameter explanations
- Retention strategy details
- Ranking comparison setup
- Output interpretation
- Advanced examples

## Large-Scale Data Processing

Process multi-type citation graphs from SQL databases (50GB+) with efficient serialization.

### Quick Start
```bash
# 1. Extract from SQL database
python3 extract_from_sql.py

# 2. Load and run credit transfer
python3 load_large_scale_data.py
```

### Features
- **SQL database extraction** - PostgreSQL batch processing
- **Multi-type graphs** - Papers, patents, clinical trials
- **Memory-efficient** - Sparse matrices with compressed serialization
- **Author h-indices** - Large-scale author metrics
- **50M+ nodes** - Scales to billions of edges

### Complete Guide
See **[LARGE_SCALE_DATA_GUIDE.md](LARGE_SCALE_DATA_GUIDE.md)** for:
- SQL database schema
- Extraction workflow
- Serialization formats
- Performance optimization
- Memory requirements
- Troubleshooting

## Testing

```bash
python3 -m pytest test/
python3 test/test_fully_optimized.py
python3 test/test_author_metrics.py
```

## License

[Specify your license]

## Citation

```bibtex
@software{credit_transfer_2025,
  title={Credit Transfer: Transitive Credit Distribution for Citation Networks},
  year={2025}
}
```

---

**Date:** October 26, 2025

