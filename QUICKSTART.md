# Quick Start Guide

## 1. Simple Graph (1 minute)

```python
from graph.GraphUtils import Graph
from credit.generalFormulation import GeneralCreditTransfer

graph = Graph(is_directed=True)
graph.add_edge("A", "B")
graph.add_edge("A", "C")

ct = GeneralCreditTransfer(graph)
ct.set_uniform_retention(0.2)
total_credit, kudos, _ = ct.compute_credit_distribution()

results = ct.get_results_dict(total_credit, kudos)
for node, vals in results.items():
    print(f"{node}: kudos={vals['kudos']:.4f}")
```

## 2. Multi-Type Graph (2 minutes)

```python
import numpy as np

# Papers (0), Datasets (1)
graph = Graph(is_directed=True)
graph.add_edge(0, 1)
graph.add_edge(2, 1)
node_types = np.array([0, 1, 0])

ct = GeneralCreditTransfer(graph, node_types=node_types)
ct.set_retention_by_type(np.array([0.2, 0.9]))  # Papers 20%, Datasets 90%
total_credit, kudos, _ = ct.compute_credit_distribution()
```

## 3. With Authors (3 minutes)

```python
from credit.authorMetrics import AuthorMetrics

# Define authorship
node_to_authors = {0: [1, 2], 1: [2, 3], 2: [1]}
author_names = {1: "Smith, J.", 2: "Jones, M.", 3: "Lee, S."}

# Compute h-indices
metrics = AuthorMetrics(node_to_authors, author_names)
h_indices = metrics.compute_all_h_indices(kudos)
metrics.display_author_report(kudos, top_k=10)
```

## 4. Property Files (30 seconds)

```bash
python3 creditRunner.py config/multi_type.properties
```

## 5. MES Experiment (5 minutes)

```bash
# Prepare data (once)
python3 experiments/prepare_mes_data.py

# Run experiment
python3 experiments/run_mes_experiment.py

# View results
head -50 output/mes_experiment/mes_author_hindices.txt
```

## 6. Synthetic Graphs (2 minutes)

```bash
# Generate graph and compare rankings (includes Direct Citations baseline)
python3 experiments/run_ranking_comparison.py config/synthetic_small.properties

# View side-by-side top-20 rankings
# See Kendall's tau correlation matrix  
# Analyze ranking volatility
```

**What you get:**
- Top-20 rankings for 6 retention strategies (including baseline)
- Kendall's tau correlation matrix
- Ranking volatility analysis
- h-index from both kudos and total credit

**Complete guide:** See [SYNTHETIC_GRAPHS_GUIDE.md](SYNTHETIC_GRAPHS_GUIDE.md)
- All parameter explanations
- Controlled experiment setup
- Output interpretation
- Advanced examples

## Common Tasks

**Set retention rates by node type:**
```python
ct.set_retention_by_type(np.array([0.2, 0.9, 0.7]))  # Papers, Datasets, Software
```

**Skip convergence check (faster):**
```python
total_credit, kudos, _ = ct.compute_credit_distribution(check_convergence=False)
```

**Use integer indexing (10x faster):**
```python
ct = GeneralCreditTransfer(graph, use_integer_indices=True)
```

## Next Steps

See README.md for full documentation.

