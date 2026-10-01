# Synthetic 1M-Node Credit Transfer Experiment

*Generated: 2026-07-01T16:42:58.173187*

## 1. Experiment Description

This experiment evaluates the efficiency and ranking behaviour of the transitive credit-transfer model ("kudos" and "total credit") compared to traditional direct citation counts, on a large synthetic multi-type scholarly citation graph.

A synthetic directed acyclic citation graph with **1,000,000 nodes** was generated with three node types: **papers**, **datasets**, and **software**. The nodes were requested in proportions 50% / 30% / 30% (paper/dataset/software); since these do not sum to 100%, they were normalized (as in the project convention) to **45.45% papers, 27.27% datasets, 27.27% software**.

The graph has an average out-degree (references per node) of **19.00** (target: 20.0), for a total of **19,000,677 edges**. Citation targets are chosen with a mixture of realistic mechanisms: power-law preferential attachment (in-degree exponent ~2.3), community/subfield structure (400 communities), transitive closure (citation triangles), type-aware citation preferences (e.g. papers preferentially cite papers), and a 7-level citation hierarchy favouring foundational works. Every edge is constructed so that the source node index is strictly greater than the target node index (temporal ordering) -- **this guarantees the graph is a DAG by construction, with no self-loops and no cycles**.

**303,030 synthetic authors** were assigned to nodes using a power-law productivity model (preferential attachment over author IDs), giving realistic "star researcher" behaviour, at an average of ~3.3 authors per work.

The credit-transfer model used a **uniform retention rate of 0.5 for all node types** (papers, datasets, software each keep 50% of incoming credit as kudos and redistribute the remaining 50% to the works they cite). Convergence checking was **disabled** (`check_convergence=False`) to maximize efficiency; this is safe because the acyclic-by-construction graph guarantees `A^T` is nilpotent (spectral radius = 0), so the system `c = (I - A^T)^-1 v` is always well-posed.

## 2. Machine / Hardware

| Property | Value |
|---|---|
| OS | macOS-26.5.1-arm64-arm-64bit |
| CPU | Apple M2 |
| CPU cores (logical / physical) | 8 / 8 |
| Total RAM | 24.0 GB |
| Python | 3.12.6 |
| NumPy / SciPy / Pandas | 2.3.4 / 1.16.2 / 3.0.0 |

## 3. Graph Statistics

| Metric | Value |
|---|---|
| Nodes | 1,000,000 |
| Edges | 19,000,677 |
| Paper nodes | 455,089 (45.5%) |
| Dataset nodes | 272,524 (27.3%) |
| Software nodes | 272,387 (27.2%) |
| Authors | 303,030 |
| Retention rate (all types) | 0.5 |
| Graph generation wall time | 33.22 s |

## 4. Wall-Clock Timing Comparison

Timings were measured with `time.perf_counter()` around the isolated computation only (matrix construction / sparse solve for credit; per-author h-index aggregation for the h-index measurements).

| Computation | Wall time (s) |
|---|---|
| Build sparse transfer matrix + solve for kudos & total credit | 1.4825 |
| h-index for all authors, from **KUDOS** | 4.1261 |
| h-index for all authors, from **traditional citations** (in-degree) | 4.1245 |

The citation-based h-index computation took **1.000x** the time of the kudos-based computation (both use the identical per-author aggregation code path from `AuthorMetrics`; any difference reflects value distribution / sorting cost, not algorithmic complexity, since both are O(A x P log P)). The dominant cost by far is the credit-distribution sparse linear solve (1.4825 s), which the h-index step reuses without re-deriving kudos or citations.

Conservation check: total kudos = 19000677.00, total external credit (sum of in-degrees) = 19000677.00, error = 7.45e-09.

## 5. Top-10 Synthetic Authors -- h-index Comparison

### 5.1 Ranked by KUDOS h-index

| Rank | Author | h-index (kudos) | Total Kudos | Publications |
| --- | --- | --- | --- | --- |
| 1 | Author_85509 | 21 | 6828.78 | 91 |
| 2 | Author_293169 | 21 | 2119.4 | 98 |
| 3 | Author_50269 | 21 | 1508.68 | 104 |
| 4 | Author_31200 | 21 | 1384.64 | 89 |
| 5 | Author_113401 | 20 | 1863.94 | 128 |
| 6 | Author_61048 | 20 | 1732.72 | 109 |
| 7 | Author_244116 | 20 | 1700.31 | 85 |
| 8 | Author_118204 | 20 | 1655.67 | 89 |
| 9 | Author_177644 | 20 | 1580.92 | 134 |
| 10 | Author_206310 | 20 | 1543.51 | 116 |

### 5.2 Ranked by traditional CITATION h-index

| Rank | Author | h-index (citations) | Total Citations | Publications |
| --- | --- | --- | --- | --- |
| 1 | Author_85509 | 25 | 4784 | 91 |
| 2 | Author_293169 | 25 | 2367 | 98 |
| 3 | Author_244116 | 25 | 2098 | 85 |
| 4 | Author_31200 | 25 | 1848 | 89 |
| 5 | Author_76991 | 24 | 2580 | 82 |
| 6 | Author_61048 | 24 | 2104 | 109 |
| 7 | Author_64777 | 24 | 2096 | 100 |
| 8 | Author_263049 | 24 | 2066 | 112 |
| 9 | Author_41665 | 24 | 2055 | 103 |
| 10 | Author_37322 | 24 | 1913 | 81 |

## 6. Top-10 Nodes by Kudos

| Node ID | Type | Kudos | Total Credit | Traditional Citations |
| --- | --- | --- | --- | --- |
| 0 | paper | 913423.037 | 913423.037 | 85131 |
| 1 | software | 221558.629 | 443117.257 | 51713 |
| 3 | paper | 150564.59 | 301129.18 | 40828 |
| 2 | dataset | 143762.118 | 287524.236 | 37926 |
| 4 | dataset | 116375.929 | 232751.857 | 32775 |
| 6 | software | 113843.733 | 227687.466 | 32560 |
| 5 | paper | 97458.012 | 194916.023 | 29329 |
| 14 | paper | 90236.509 | 180473.017 | 27805 |
| 12 | software | 82176.622 | 164353.245 | 26459 |
| 9 | dataset | 79173.809 | 158347.618 | 25699 |

## 7. Kendall's Tau: Top-1000 Authors (Citation h-index) vs. Kudos Ranking

The top-1000 authors were selected and ordered by descending **traditional citation h-index**. Each author's corresponding rank (and h-index) under the **kudos-based** ranking (computed over all authors) was then looked up, and Kendall's tau rank correlation coefficient was computed between the two rankings.

| Correlation | Kendall tau | p-value |
|---|---|---|
| Citation rank vs. Kudos rank (Top-1000) | 0.5172 | 1.796e-132 |
| Citation h-index vs. Kudos h-index values (Top-1000) | 0.5709 | 3.208e-110 |

A Kendall tau of **0.5172** indicates a **moderate** rank agreement between the traditional citation-count-based ranking and the transitive kudos-based ranking among the top-1000 most-cited authors. The full top-1000 comparison table is saved to `tables/top1000_citation_vs_kudos_ranking.csv`; the first 20 rows are shown below.

| Citation Rank | Author ID | Author | h-index (citation) | h-index (kudos) | Kudos Rank |
| --- | --- | --- | --- | --- | --- |
| 1 | 85509 | Author_85509 | 25 | 21 | 1 |
| 2 | 293169 | Author_293169 | 25 | 21 | 2 |
| 3 | 244116 | Author_244116 | 25 | 20 | 7 |
| 4 | 31200 | Author_31200 | 25 | 21 | 4 |
| 5 | 76991 | Author_76991 | 24 | 19 | 13 |
| 6 | 61048 | Author_61048 | 24 | 20 | 6 |
| 7 | 64777 | Author_64777 | 24 | 19 | 15 |
| 8 | 263049 | Author_263049 | 24 | 19 | 16 |
| 9 | 41665 | Author_41665 | 24 | 19 | 17 |
| 10 | 37322 | Author_37322 | 24 | 17 | 93 |
| 11 | 261776 | Author_261776 | 24 | 19 | 24 |
| 12 | 33654 | Author_33654 | 24 | 18 | 45 |
| 13 | 268036 | Author_268036 | 24 | 19 | 25 |
| 14 | 137895 | Author_137895 | 24 | 20 | 11 |
| 15 | 234778 | Author_234778 | 23 | 17 | 72 |
| 16 | 94197 | Author_94197 | 23 | 18 | 30 |
| 17 | 277493 | Author_277493 | 23 | 19 | 12 |
| 18 | 138929 | Author_138929 | 23 | 19 | 14 |
| 19 | 113401 | Author_113401 | 23 | 20 | 5 |
| 20 | 177644 | Author_177644 | 23 | 20 | 9 |

## 8. Reproducibility

- Random seed: `20260701`
- Graph size: `--n-nodes 1000000` (authors=303030, communities=400)
- Script: `analyses/synthetic_100k_kudos_vs_citation_experiment.py`
- Run with: `python3 analyses/synthetic_100k_kudos_vs_citation_experiment.py --n-nodes 1000000 --n-authors 303030 --n-communities 400 --seed 20260701`
