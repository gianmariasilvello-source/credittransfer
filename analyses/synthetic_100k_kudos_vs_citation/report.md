# Synthetic 100K-Node Credit Transfer Experiment

*Generated: 2026-10-01T13:38:26.649991*

## 1. Experiment Description

This experiment evaluates the efficiency and ranking behaviour of the transitive credit-transfer model ("kudos" and "total credit") compared to traditional direct citation counts, on a large synthetic multi-type scholarly citation graph.

A synthetic directed acyclic citation graph with **100,000 nodes** was generated with three node types: **papers**, **datasets**, and **software**. The nodes were requested in proportions 50% / 30% / 30% (paper/dataset/software); since these do not sum to 100%, they were normalized (as in the project convention) to **45.45% papers, 27.27% datasets, 27.27% software**.

The graph has an average out-degree (references per node) of **18.98** (target: 20.0), for a total of **1,898,323 edges**. Citation targets are chosen with a mixture of realistic mechanisms: power-law preferential attachment (in-degree exponent ~2.3), community/subfield structure (40 communities), transitive closure (citation triangles), type-aware citation preferences (e.g. papers preferentially cite papers), and a 7-level citation hierarchy favouring foundational works. Every edge is constructed so that the source node index is strictly greater than the target node index (temporal ordering) -- **this guarantees the graph is a DAG by construction, with no self-loops and no cycles**.

**30,000 synthetic authors** were assigned to nodes using a power-law productivity model (preferential attachment over author IDs), giving realistic "star researcher" behaviour, at an average of ~3.3 authors per work.

The credit-transfer model used a **uniform retention rate of 0.5 for all node types** (papers, datasets, software each keep 50% of incoming credit as kudos and redistribute the remaining 50% to the works they cite). Convergence checking was **disabled** (`check_convergence=False`) to maximize efficiency; this is safe because the acyclic-by-construction graph guarantees `A^T` is nilpotent (spectral radius = 0), so the system `c = (I - A^T)^-1 v` is always well-posed.

## 2. Machine / Hardware

| Property | Value |
|---|---|
| OS | macOS-26.6.2-arm64-arm-64bit |
| CPU | Apple M2 |
| CPU cores (logical / physical) | 8 / 8 |
| Total RAM | 24.0 GB |
| Python | 3.12.6 |
| NumPy / SciPy / Pandas | 2.3.4 / 1.16.2 / 3.0.0 |

## 3. Graph Statistics

| Metric | Value |
|---|---|
| Nodes | 100,000 |
| Edges | 1,898,323 |
| Paper nodes | 45,542 (45.5%) |
| Dataset nodes | 27,082 (27.1%) |
| Software nodes | 27,376 (27.4%) |
| Authors | 30,000 |
| Retention rate (all types) | 0.5 |
| Graph generation wall time | 1.86 s |

## 4. Wall-Clock Timing Comparison

Timings were measured with `time.perf_counter()` around the isolated computation only (matrix construction / sparse solve for credit; per-author h-index aggregation for the h-index measurements).

| Computation | Wall time (s) |
|---|---|
| Build sparse transfer matrix + solve for kudos & total credit | 0.0787 |
| h-index for all authors, from **KUDOS** | 0.1817 |
| h-index for all authors, from **traditional citations** (in-degree) | 0.1672 |

The citation-based h-index computation took **0.920x** the time of the kudos-based computation (both use the identical per-author aggregation code path from `AuthorMetrics`; any difference reflects value distribution / sorting cost, not algorithmic complexity, since both are O(A x P log P)). The per-author h-index aggregation dominates; the credit-distribution sparse linear solve takes only 0.0787 s, and the h-index step reuses its output without re-deriving kudos or citations.

Conservation check: total kudos = 1898323.00, total external credit (sum of in-degrees) = 1898323.00, error = 6.98e-10.

## 5. Top-10 Synthetic Authors -- h-index Comparison

### 5.1 Ranked by KUDOS h-index

| Rank | Author | h-index (kudos) | Total Kudos | Publications |
| --- | --- | --- | --- | --- |
| 1 | Author_29916 | 24 | 2153.09 | 126 |
| 2 | Author_04808 | 21 | 1486.51 | 102 |
| 3 | Author_12371 | 20 | 4173.64 | 129 |
| 4 | Author_25383 | 20 | 1252.57 | 92 |
| 5 | Author_24980 | 19 | 1597.96 | 66 |
| 6 | Author_03031 | 18 | 1726.12 | 88 |
| 7 | Author_00349 | 18 | 1532.87 | 58 |
| 8 | Author_03855 | 18 | 1512.98 | 108 |
| 9 | Author_04451 | 18 | 1122.29 | 67 |
| 10 | Author_20586 | 17 | 4335.15 | 92 |

### 5.2 Ranked by traditional CITATION h-index

| Rank | Author | h-index (citations) | Total Citations | Publications |
| --- | --- | --- | --- | --- |
| 1 | Author_29916 | 28 | 2679 | 126 |
| 2 | Author_12371 | 25 | 3733 | 129 |
| 3 | Author_04808 | 25 | 1859 | 102 |
| 4 | Author_25383 | 24 | 1715 | 92 |
| 5 | Author_24980 | 23 | 1878 | 66 |
| 6 | Author_20586 | 22 | 3369 | 92 |
| 7 | Author_17369 | 22 | 2079 | 107 |
| 8 | Author_15630 | 22 | 1628 | 98 |
| 9 | Author_04451 | 22 | 1407 | 67 |
| 10 | Author_10599 | 22 | 1172 | 73 |

## 6. Top-10 Nodes by Kudos

| Node ID | Type | Kudos | Total Credit | Traditional Citations |
| --- | --- | --- | --- | --- |
| 0 | paper | 103791.377 | 103791.377 | 10405 |
| 1 | software | 42861.672 | 85723.344 | 9257 |
| 2 | dataset | 26303.427 | 52606.854 | 6803 |
| 4 | dataset | 16895.708 | 33791.416 | 5730 |
| 3 | paper | 16021.594 | 32043.188 | 5164 |
| 6 | software | 14656.394 | 29312.787 | 5027 |
| 5 | paper | 14000.558 | 28001.115 | 5039 |
| 9 | dataset | 11536.78 | 23073.56 | 4525 |
| 18 | paper | 9749.877 | 19499.754 | 3966 |
| 8 | software | 9377.333 | 18754.666 | 3614 |

## 7. Kendall's Tau: Top-1000 Authors (Citation h-index) vs. Kudos Ranking

The top-1000 authors were selected and ordered by descending **traditional citation h-index**. Each author's corresponding rank (and h-index) under the **kudos-based** ranking (computed over all authors) was then looked up, and Kendall's tau rank correlation coefficient was computed between the two rankings.

| Correlation | Kendall tau | p-value |
|---|---|---|
| Citation rank vs. Kudos rank (Top-1000) | 0.6418 | 7.457e-203 |
| Citation h-index vs. Kudos h-index values (Top-1000) | 0.6740 | 1.396e-160 |

A Kendall tau of **0.6418** indicates a **moderate** rank agreement between the traditional citation-count-based ranking and the transitive kudos-based ranking among the top-1000 most-cited authors. The full top-1000 comparison table is saved to `tables/top1000_citation_vs_kudos_ranking.csv`; the first 20 rows are shown below.

| Citation Rank | Author ID | Author | h-index (citation) | h-index (kudos) | Kudos Rank |
| --- | --- | --- | --- | --- | --- |
| 1 | 29916 | Author_29916 | 28 | 24 | 1 |
| 2 | 12371 | Author_12371 | 25 | 20 | 3 |
| 3 | 4808 | Author_04808 | 25 | 21 | 2 |
| 4 | 25383 | Author_25383 | 24 | 20 | 4 |
| 5 | 24980 | Author_24980 | 23 | 19 | 5 |
| 6 | 20586 | Author_20586 | 22 | 17 | 10 |
| 7 | 17369 | Author_17369 | 22 | 17 | 14 |
| 8 | 15630 | Author_15630 | 22 | 17 | 16 |
| 9 | 4451 | Author_04451 | 22 | 18 | 9 |
| 10 | 10599 | Author_10599 | 22 | 17 | 20 |
| 11 | 20711 | Author_20711 | 21 | 16 | 22 |
| 12 | 15471 | Author_15471 | 21 | 16 | 25 |
| 13 | 9181 | Author_09181 | 21 | 17 | 11 |
| 14 | 3031 | Author_03031 | 21 | 18 | 6 |
| 15 | 3855 | Author_03855 | 21 | 18 | 8 |
| 16 | 29781 | Author_29781 | 21 | 17 | 12 |
| 17 | 22092 | Author_22092 | 21 | 16 | 32 |
| 18 | 12325 | Author_12325 | 21 | 16 | 31 |
| 19 | 17905 | Author_17905 | 21 | 15 | 67 |
| 20 | 1088 | Author_01088 | 21 | 16 | 38 |

## 8. Reproducibility

- Random seed: `20260701`
- Graph size: `--n-nodes 100000` (authors=30000, communities=40)
- Script: `analyses/synthetic_100k_kudos_vs_citation_experiment.py`
- Run with: `python3 analyses/synthetic_100k_kudos_vs_citation_experiment.py --n-nodes 100000 --n-authors 30000 --n-communities 40 --seed 20260701`
