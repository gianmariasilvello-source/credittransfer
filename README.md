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
- 100,000 nodes / 1.9M edges (acyclic): ~0.1s credit solve
- 1,000,000 nodes / 19M edges (acyclic): ~1s credit solve

See [Experiments and Analyses](#experiments-and-analyses) for the full large-scale timings.

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
│   ├── author_dedup.py           # MES author deduplication
│   ├── simple_jev.py             # Minimal Simple Jev client
│   └── MES_SEMANTICS_REFERENCE.md
├── analyses/                     # Experiment scripts, reports, plots, tables
│   └── FINDINGS_REPORT.md
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
- `IsPartOf`, `HasPart` - Hierarchical relationships
- `documents`, `IsDocumentedBy` - Documentation relationships

Semantics are matched case-insensitively (the curated data uses DataCite capitalization
such as `Cites`/`IsPartOf`; older exports used lower camel case). Relations whose curation
`status` is `Removed` are skipped by default; pass `excluded_statuses=set()` to
`MESDataParser` to keep them. Dropped and unrecognized relations are counted in the
parser summary.

See `dataprocessing/MES_SEMANTICS_REFERENCE.md` for complete details.

### Author Deduplication

The MES authors file has one record per author *mention source*, so one person can appear
under several ids (`Brewin, Robert J. W.`, `Brewin, RJW`, `R Brewin`), which splits their
credit. `dataprocessing/author_dedup.py` merges them:

1. **Blocking**: pairs with the same normalized surname and compatible given names
2. **Hard rules**: same ORCID → merge; different ORCIDs → keep apart
3. **Judgment**: remaining pairs are scored by TypeSafe or Simple Jev (same person / curator review / different people)
4. **Clustering**: union-find over merged pairs → `author_id -> canonical author_id`

```bash
python -m dataprocessing.author_dedup --candidates-only   # blocking + rules only, no API calls
python -m dataprocessing.author_dedup --eval 100          # score ORCID-labeled pairs (needs TYPESAFE_API_KEY)
python -m dataprocessing.author_dedup                     # judge all pairs, write merges
python -m dataprocessing.author_dedup --backend simple-jev --eval 100
```

Candidate pairs are written to `data/author_dedup/candidates.jsonl`. Judgments are cached
per backend model, so both backends can be compared on the same pairs.

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

## Experiments and Analyses

Scripts in `analyses/` reproduce the experiments below. Run them from the project root;
each writes its plots (PDF + PNG), tables (CSV + TXT) and a text/Markdown report to the
output folder listed. Retention `r = 1` means no transitive transfer (direct citations
only) and is the baseline throughout.

| Experiment | Script | Output |
|---|---|---|
| PubMed h-index vs retention rate | `pubmed_hindex_ranking_analysis.py` | `analyses/plots/`, `analyses/tables/`, `analyses/analysis_report.txt` |
| Top-500 overlap across retention rates | `top500_transitivity_overlap_analysis.py` | `analyses/transitivity_top500_overlap/` |
| SOTA baselines (Katz, PageRank) vs h-index | `sota_hindex_comparison_analysis.py` | `analyses/sota_hindex_comparison/` |
| Top-500 overlap with SOTA baselines | `top500_sota_baseline_analysis.py` | `analyses/sota_hindex_comparison/` |
| Synthetic kudos vs citation h-index (100K, 1M nodes) | `synthetic_100k_kudos_vs_citation_experiment.py` | `analyses/synthetic_{100k,1m}_kudos_vs_citation/` |
| Synthetic graph size (100, 1K, 10K nodes) | `synthetic_graph_size_experiments.py` | `analyses/synthetic_size_report/` |
| Impact of loops/cycles on convergence | `loop_impact_large_synthetic_analysis.py` | `analyses/loop_impact_report/` |

The written-up findings for the PubMed experiment are in
**[analyses/FINDINGS_REPORT.md](analyses/FINDINGS_REPORT.md)**.

### PubMed: transitive credit vs retention rate

Inputs: precomputed author h-indices in `data/pubmed/` at `r = 1, 0.75, 0.5, 0.25`.
Every comparison is against `r = 1`; variations are never mixed.

```bash
python3 analyses/pubmed_hindex_ranking_analysis.py
python3 analyses/top500_transitivity_overlap_analysis.py
```

| Variation | Gainers | Losers | Max gain | Top-500 overlap |
|---|--:|--:|--:|--:|
| r = 1 → 0.75 | 11.1% | 75.3% | +29 | 90.0% |
| r = 1 → 0.50 | 10.5% | 84.8% | +62 | 76.6% |
| r = 1 → 0.25 | 7.1% | 91.2% | +96 | 58.8% |

Most authors lose h-index as retention drops, while a small minority, whose papers are
cited by highly cited work, gains substantially.

### State-of-the-art baselines: Katz and PageRank

Inputs: `data/pubmed/pkg24s4_1_author_hindices.txt` (baseline) and
`data/sota_hindex/{katz,pagerank}_hindex_500k.txt`.

```bash
python3 analyses/sota_hindex_comparison_analysis.py
python3 analyses/top500_sota_baseline_analysis.py
```

Both baselines reorder the ranking far more than transitive credit does: the baseline
top-500 overlaps 49.2% with Katz and 31.6% with PageRank (vs 58.8–90.0% above), and
Top-10 Spearman correlation is −0.06 (Katz) and −0.61 (PageRank).

### Synthetic: kudos vs citation h-index at scale

Generates an acyclic multi-type graph (papers, datasets, software; ~19 references per
node), assigns authors with power-law productivity, computes kudos with uniform
retention 0.5, and compares author h-indices from kudos vs raw citation counts.

```bash
python3 analyses/synthetic_100k_kudos_vs_citation_experiment.py \
    --n-nodes 100000 --n-authors 30000 --n-communities 40 --seed 20260701
python3 analyses/synthetic_100k_kudos_vs_citation_experiment.py \
    --n-nodes 1000000 --n-authors 303030 --n-communities 400 --seed 20260701
```

| Nodes | Edges | Credit solve | Kendall τ (top-1000, citation vs kudos) |
|--:|--:|--:|--:|
| 100K | 1.9M | 0.08 s | 0.64 |
| 1M | 19.0M | 0.93 s | 0.52 |

Use the exact arguments above to reproduce the committed results: without
`--n-authors`, the author count is scaled from the node count and the rankings change.
Timings are from an Apple M2 (24 GB).

### Synthetic graph size and loop impact

```bash
python3 analyses/synthetic_graph_size_experiments.py
python3 analyses/loop_impact_large_synthetic_analysis.py
```

- **Graph size** regenerates the small, 1K and 10K synthetic graphs from
  `config/synthetic_*.properties` and compares density, degree, transitivity and type mix.
  Note that it overwrites the graph files in `data/synthetic*/` (deterministic for a fixed seed).
- **Loop impact** adds self-loops or reversed edges to the 10K graph and measures the
  spectral radius ρ of the citation transfer matrix (before retention is applied). The
  acyclic baseline has ρ = 0; 1–5% reversed edges give ρ ≈ 0.99–1.00; 1% self-loops give
  ρ = 1, so the report flags self-loops as the highest-risk perturbation for convergence.
  See `analyses/loop_impact_report/LOOP_TREATMENT_IMPACT_LARGE_SYNTHETIC.md`.

## Testing

```bash
python3 -m pytest test/
python3 test/test_fully_optimized.py
python3 test/test_author_metrics.py
```

The test suite runs in about 30 seconds. Install `pytest` first if your environment does not have it.

## License

[Specify your license]

## Citation

```bibtex
@software{credit_transfer_2025,
authors = {Peter Buneman, Matteo Lissandrini, Gianmaria Silvello}
  title={Credit Transfer: Transitive Credit Distribution for Citation Networks},
  year={2025}
}
```

---

**Date:** October 1, 2026

