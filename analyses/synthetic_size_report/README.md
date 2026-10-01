# Synthetic Size Report Artifacts
This folder contains outputs from synthetic graph size experiments.
## Main report
- `SYNTHETIC_SIZE_EXPERIMENT_REPORT.md`
## Generated tables
- `tables/synthetic_graph_size_summary.csv`
- `tables/synthetic_graph_type_distribution.csv`
## Generated plots
- `plots/nodes_edges_by_size.png` / `.pdf`
- `plots/degree_transitivity_by_size.png` / `.pdf`
- `plots/type_composition_by_size.png` / `.pdf`
## How to regenerate
From project root:
```bash
python3 analyses/synthetic_graph_size_experiments.py
```
