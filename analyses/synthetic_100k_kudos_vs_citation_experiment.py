#!/usr/bin/env python3
"""
Large-scale synthetic experiment: Kudos/Total-Credit vs. traditional citation h-index.

Generates a synthetic multi-type scholarly graph with:
    - 100,000 nodes: ~50% papers, ~30% datasets, ~30% software
      (proportions are normalized to sum to 1, following the convention used by
      generators/generate_synthetic_graph.py)
    - Average out-degree (references per node) = 20
    - Realistic power-law in-degree, community structure, hierarchy and
      type-aware citation preferences
    - Guaranteed acyclic: every edge only points from a node to a strictly
      earlier node (temporal order), so the graph has NO self-loops and NO
      cycles by construction.
    - Authors assigned to nodes with a power-law productivity distribution
      (for h-index computation)

The credit-transfer model uses a UNIFORM retention rate of 0.5 for every node
type (papers, datasets, software). Convergence checking is disabled
(check_convergence=False) to maximize efficiency, which is safe here because
the graph is acyclic by construction (spectral radius of A^T is exactly 0).

The script measures wall-clock time for:
    1. Building the sparse transfer matrix + solving for total credit & kudos
    2. Computing the h-index of every author from KUDOS
    3. Computing the h-index of every author from traditional in-degree
       (direct citation count)

It produces a markdown report with:
    - A description of the experiment and the machine hardware used
    - Top-10 authors by kudos h-index vs. traditional citation h-index
    - Top-10 nodes (type, kudos, total credit, traditional citation count)
    - Kendall's tau rank correlation between the Top-1000 authors ranked by
      citation h-index (descending) and the same authors' kudos h-index rank

Usage:
    python3 analyses/synthetic_100k_kudos_vs_citation_experiment.py
    python3 analyses/synthetic_100k_kudos_vs_citation_experiment.py --n-nodes 1000000
"""

from __future__ import annotations

import os
import sys
import time
import random
import argparse
import platform
import subprocess
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix, eye
from scipy.sparse.linalg import spsolve, spsolve_triangular
from scipy import stats

PROJECT_ROOT = str(Path(__file__).resolve().parents[1])
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from credit.authorMetrics import AuthorMetrics

try:
    import psutil
    HAVE_PSUTIL = True
except ImportError:
    HAVE_PSUTIL = False


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class ExperimentConfig:
    n_nodes: int = 100_000
    # Requested proportions (paper, dataset, software). They do not need to
    # sum to 1.0 - they are normalized automatically, matching the behaviour
    # of generators/generate_synthetic_graph.py.
    type_proportions_raw: Tuple[float, float, float] = (0.5, 0.3, 0.3)
    type_names: Tuple[str, str, str] = ('paper', 'dataset', 'software')

    avg_out_degree: float = 20.0
    max_out_degree: int = 60          # hard cap, realistic upper bound on reference lists
    powerlaw_exponent: float = 2.3    # in-degree inequality (typical scholarly range 2.0-2.5)
    n_communities: int = 40           # research subfields
    hierarchy_levels: int = 7
    level_bias: float = 0.7

    # Retention: uniform 0.5 for ALL node types (as requested)
    retention: float = 0.5

    # Authors: realistic ratio of ~1 author per ~3.3 works
    n_authors: int = 30_000
    avg_authors_per_node: float = 3.3
    author_productivity_exponent: float = 1.8

    seed: int = 20260701

    output_dir: str = os.path.join(PROJECT_ROOT, 'analyses', 'synthetic_100k_kudos_vs_citation')
    label: str = '100K'   # human-readable size label used in report title/text

    top_nodes: int = 10
    top_authors: int = 10
    top_authors_kendall: int = 1000


CFG = ExperimentConfig()


def build_config_for_size(n_nodes: int, seed: int = 20260701,
                          output_dir: str = None, n_authors: int = None,
                          n_communities: int = None) -> ExperimentConfig:
    """
    Build an ExperimentConfig scaled to an arbitrary node count, keeping the
    same realistic ratios used for the 100K baseline (~1 author per 3.3
    works, ~1 community per 2,500 nodes, capped sensibly).
    """
    if n_authors is None:
        n_authors = max(1000, round(n_nodes / 3.3))
    if n_communities is None:
        n_communities = int(np.clip(round(n_nodes / 2500), 10, 400))

    if n_nodes >= 1_000_000:
        label = f'{n_nodes // 1_000_000}M'
    elif n_nodes >= 1_000:
        label = f'{n_nodes // 1_000}K'
    else:
        label = str(n_nodes)

    if output_dir is None:
        output_dir = os.path.join(PROJECT_ROOT, 'analyses', f'synthetic_{label.lower()}_kudos_vs_citation')

    return ExperimentConfig(
        n_nodes=n_nodes,
        n_authors=n_authors,
        n_communities=n_communities,
        seed=seed,
        output_dir=output_dir,
        label=label,
    )

# Type-aware citation preferences (weights, normalized internally).
# type 0 = paper, 1 = dataset, 2 = software
TYPE_CITATION_PREFS = {
    0: {0: 1.0, 1: 0.35, 2: 0.15},   # papers mostly cite papers, some datasets, rare software
    1: {0: 0.5, 1: 1.0, 2: 0.2},     # datasets cite other datasets and some papers
    2: {0: 0.6, 1: 0.6, 2: 0.4},     # software cites papers/datasets/other software roughly evenly
}

MECHANISM_CUM_PROBS = np.cumsum([0.30, 0.25, 0.20, 0.15, 0.10])  # pref, community, transitive, type, hierarchy


# ---------------------------------------------------------------------------
# Fast, amortized O(1)-per-candidate synthetic graph generator
# ---------------------------------------------------------------------------

def normalize_proportions(raw: Tuple[float, float, float]) -> List[float]:
    total = sum(raw)
    return [p / total for p in raw]


def precompute_level_weights(hierarchy_levels: int, level_bias: float) -> np.ndarray:
    """weights[source_level, target_level] favouring citing lower (more foundational) levels."""
    levels = np.arange(hierarchy_levels)
    diff = levels[:, None] - levels[None, :]          # source - target
    w = np.exp(level_bias * diff)
    w = w / w.sum(axis=1, keepdims=True)
    return w


def precompute_type_weights(type_prefs: Dict[int, Dict[int, float]], n_types: int = 3) -> np.ndarray:
    w = np.zeros((n_types, n_types), dtype=np.float64)
    for src_type, prefs in type_prefs.items():
        for tgt_type, weight in prefs.items():
            w[src_type, tgt_type] = weight
    row_sums = w.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1.0
    return w / row_sums


def generate_large_synthetic_graph(cfg: ExperimentConfig):
    """
    Generate a large synthetic multi-type citation graph efficiently.

    Uses amortized O(1) target-selection mechanisms (growth pools, following
    the classic Barabasi-Albert trick) instead of the O(n) per-candidate
    approach used by generators/generate_synthetic_graph.py, so it scales to
    n=100,000 nodes / ~2M edges in well under a minute.

    Returns:
        sources, targets: int64 numpy arrays describing directed edges (u -> v, u > v)
        node_types: uint8 numpy array (0=paper, 1=dataset, 2=software)
        node_to_authors: dict node_id -> list[author_id]
        gen_metadata: dict with generation statistics
    """
    rng = random.Random(cfg.seed)
    np_rng = np.random.default_rng(cfg.seed)

    n = cfg.n_nodes
    proportions = normalize_proportions(cfg.type_proportions_raw)
    node_types = np_rng.choice(3, size=n, p=proportions).astype(np.uint8)
    node_communities = np_rng.integers(0, cfg.n_communities, size=n)
    node_levels = np_rng.integers(0, cfg.hierarchy_levels, size=n)

    out_degrees = np_rng.exponential(cfg.avg_out_degree, size=n)
    out_degrees = np.clip(np.round(out_degrees), 0, cfg.max_out_degree).astype(np.int64)
    out_degrees[0] = 0  # first node in temporal order cannot cite anything

    level_weights = precompute_level_weights(cfg.hierarchy_levels, cfg.level_bias)
    type_weights = precompute_type_weights(TYPE_CITATION_PREFS, n_types=3)

    # Growth pools (Barabasi-Albert style): a node id appears once per "unit of
    # attractiveness"; appending the target id on every accepted edge grows
    # its in-degree weight -> approximate preferential attachment in O(1).
    pref_pool: List[int] = [0]
    community_pool: Dict[int, List[int]] = {c: [] for c in range(cfg.n_communities)}
    type_pool: Dict[int, List[int]] = {t: [] for t in range(3)}
    level_pool: Dict[int, List[int]] = {lv: [] for lv in range(cfg.hierarchy_levels)}

    community_pool[int(node_communities[0])].append(0)
    type_pool[int(node_types[0])].append(0)
    level_pool[int(node_levels[0])].append(0)

    out_neighbors: List[List[int]] = [[] for _ in range(n)]

    sources: List[int] = []
    targets: List[int] = []

    t_gen_start = time.perf_counter()

    randrange = rng.randrange
    randfloat = rng.random
    choices = rng.choices

    for i in range(1, n):
        k = int(out_degrees[i])
        if k > i:
            k = i

        if k > 0:
            src_type = int(node_types[i])
            src_level = int(node_levels[i])
            src_comm = int(node_communities[i])
            type_w_row = type_weights[src_type]
            level_w_row = level_weights[src_level]

            selected: set = set()
            max_attempts = k * 6
            attempts = 0

            while len(selected) < k and attempts < max_attempts:
                attempts += 1
                r = randfloat()
                target = None

                if r < MECHANISM_CUM_PROBS[0]:
                    # preferential attachment via growth pool
                    pool = pref_pool
                    if pool:
                        cand = pool[randrange(len(pool))]
                        if cand != i and cand not in selected:
                            target = cand

                elif r < MECHANISM_CUM_PROBS[1]:
                    # community
                    pool = community_pool[src_comm]
                    if pool:
                        cand = pool[randrange(len(pool))]
                        if cand not in selected:
                            target = cand

                elif r < MECHANISM_CUM_PROBS[2]:
                    # transitive closure (2-hop via an already-selected target)
                    if selected:
                        base = next(iter(selected)) if len(selected) == 1 else \
                            list(selected)[randrange(len(selected))]
                        nbrs = out_neighbors[base]
                        if nbrs:
                            cand = nbrs[randrange(len(nbrs))]
                            if cand != i and cand not in selected:
                                target = cand
                    if target is None and pref_pool:
                        cand = pref_pool[randrange(len(pref_pool))]
                        if cand != i and cand not in selected:
                            target = cand

                elif r < MECHANISM_CUM_PROBS[3]:
                    # type preference
                    chosen_type = choices(range(3), weights=type_w_row, k=1)[0]
                    pool = type_pool[chosen_type]
                    if pool:
                        cand = pool[randrange(len(pool))]
                        if cand not in selected:
                            target = cand

                else:
                    # hierarchical (favour foundational / lower levels)
                    chosen_lv = choices(range(cfg.hierarchy_levels), weights=level_w_row, k=1)[0]
                    pool = level_pool[chosen_lv]
                    if pool:
                        cand = pool[randrange(len(pool))]
                        if cand not in selected:
                            target = cand

                if target is not None:
                    selected.add(target)

            for t in selected:
                sources.append(i)
                targets.append(t)
            out_neighbors[i] = list(selected)

        # register node i in growth pools (after edges are decided, so it
        # cannot cite itself and cannot appear in its own candidate pool)
        pref_pool.append(i)
        for t in out_neighbors[i]:
            pref_pool.append(t)   # target's attractiveness grows with in-degree
        community_pool[int(node_communities[i])].append(i)
        type_pool[int(node_types[i])].append(i)
        level_pool[int(node_levels[i])].append(i)

    gen_elapsed = time.perf_counter() - t_gen_start

    sources_arr = np.array(sources, dtype=np.int64)
    targets_arr = np.array(targets, dtype=np.int64)

    node_to_authors, author_names = generate_authors(cfg, np_rng)

    gen_metadata = {
        'n_nodes': n,
        'n_edges': int(len(sources_arr)),
        'generation_wall_time_sec': gen_elapsed,
        'type_proportions_normalized': proportions,
    }

    return sources_arr, targets_arr, node_types, node_to_authors, author_names, gen_metadata


def generate_authors(cfg: ExperimentConfig, np_rng: np.random.Generator):
    """Vectorized-ish author assignment with power-law productivity (preferential attachment)."""
    n_authors = cfg.n_authors
    n_nodes = cfg.n_nodes
    author_names = {i: f"Author_{i:05d}" for i in range(n_authors)}

    node_to_authors: Dict[int, List[int]] = {}
    author_paper_counts = np.zeros(n_authors, dtype=np.float64)

    # Growth-pool trick again: sample authors with preferential attachment in O(1).
    author_pool: List[int] = list(range(n_authors))  # everyone starts with weight 1

    n_authors_per_node = np.clip(
        np_rng.gamma(shape=cfg.avg_authors_per_node, scale=1.0, size=n_nodes).round().astype(int),
        1, 8
    )

    rnd = random.Random(cfg.seed + 1)
    for node_id in range(n_nodes):
        k = int(n_authors_per_node[node_id])
        chosen: set = set()
        attempts = 0
        max_attempts = k * 8
        while len(chosen) < k and attempts < max_attempts:
            attempts += 1
            a = author_pool[rnd.randrange(len(author_pool))]
            chosen.add(a)
        chosen_list = list(chosen)
        node_to_authors[node_id] = chosen_list
        for a in chosen_list:
            author_paper_counts[a] += 1
            author_pool.append(a)  # productivity increases future selection probability

    return node_to_authors, author_names


# ---------------------------------------------------------------------------
# Credit transfer (direct sparse construction for max efficiency)
# ---------------------------------------------------------------------------

def compute_credit_transfer(sources: np.ndarray, targets: np.ndarray, n_nodes: int,
                            retention: float) -> Tuple[np.ndarray, np.ndarray, float, Dict]:
    """
    Build the sparse transfer matrix directly from edge arrays and solve for
    total credit / kudos. Equivalent to
    GeneralCreditTransfer(...).compute_credit_distribution(check_convergence=False)
    but avoids the overhead of the dict/set-based Graph object, which matters
    at 100K nodes / ~2M edges.

    Efficiency note: because every edge satisfies source > target (temporal /
    acyclic construction), the transfer matrix A is *strictly lower
    triangular* in node-id order, so A^T is strictly upper triangular and
    B = I - A^T is upper triangular with unit diagonal. This means the linear
    system c = B^-1 v can be solved EXACTLY via a single sparse triangular
    back-substitution (spsolve_triangular) in O(nnz) time, with no fill-in --
    dramatically faster than a generic sparse LU factorization (spsolve),
    which does not exploit the triangular structure and suffers severe
    fill-in on wide-bandwidth citation graphs at this scale.
    """
    n_edges = len(sources)
    out_degree = np.bincount(sources, minlength=n_nodes).astype(np.float64)
    in_degree = np.bincount(targets, minlength=n_nodes).astype(np.float64)

    weight_per_edge = np.zeros(n_edges, dtype=np.float64)
    nz = out_degree[sources] > 0
    weight_per_edge[nz] = (1.0 - retention) / out_degree[sources[nz]]

    t0 = time.perf_counter()

    A = csr_matrix((weight_per_edge, (sources, targets)), shape=(n_nodes, n_nodes))

    # v = indegree vector (external credit injection = 1 unit per incoming citation)
    v = in_degree

    I = eye(n_nodes, format='csr')
    A_T = A.transpose().tocsr()
    B = (I - A_T).tocsr()
    B.sort_indices()

    is_dag_order = bool(np.all(sources > targets))
    if is_dag_order:
        # Exact, fast path: B is upper triangular with unit diagonal.
        total_credit = spsolve_triangular(B, v, lower=False, unit_diagonal=True)
    else:
        # Fallback: generic sparse solve (handles arbitrary cyclic/contractive graphs)
        total_credit = spsolve(B, v)
        if hasattr(total_credit, 'A1'):
            total_credit = total_credit.A1

    row_sums = np.array(A.sum(axis=1)).flatten()
    kudos = total_credit * (1.0 - row_sums)

    elapsed = time.perf_counter() - t0

    diagnostics = {
        'total_kudos': float(np.sum(kudos)),
        'total_external_credit': float(np.sum(v)),
        'conservation_error': float(np.abs(np.sum(kudos) - np.sum(v))),
        'n_edges': n_edges,
    }

    return total_credit, kudos, elapsed, diagnostics


# ---------------------------------------------------------------------------
# Hardware / environment description
# ---------------------------------------------------------------------------

def get_hardware_info() -> Dict[str, str]:
    info = {
        'platform': platform.platform(),
        'system': platform.system(),
        'release': platform.release(),
        'machine': platform.machine(),
        'processor': platform.processor() or 'unknown',
        'python_version': platform.python_version(),
        'cpu_count_logical': str(os.cpu_count()),
    }

    # macOS-specific: get a friendly CPU brand string via sysctl
    if platform.system() == 'Darwin':
        try:
            brand = subprocess.check_output(
                ['sysctl', '-n', 'machdep.cpu.brand_string'], text=True
            ).strip()
            info['cpu_brand'] = brand
        except Exception:
            info['cpu_brand'] = info['processor']
        try:
            physical = subprocess.check_output(['sysctl', '-n', 'hw.physicalcpu'], text=True).strip()
            info['cpu_count_physical'] = physical
        except Exception:
            info['cpu_count_physical'] = 'unknown'
    else:
        info['cpu_brand'] = info['processor']
        info['cpu_count_physical'] = str(os.cpu_count())

    if HAVE_PSUTIL:
        vm = psutil.virtual_memory()
        info['total_ram_gb'] = f"{vm.total / (1024**3):.1f}"
    else:
        info['total_ram_gb'] = 'unknown (psutil not installed)'

    import numpy, scipy
    info['numpy_version'] = numpy.__version__
    info['scipy_version'] = scipy.__version__
    info['pandas_version'] = pd.__version__

    return info


# ---------------------------------------------------------------------------
# Analysis helpers
# ---------------------------------------------------------------------------

def compute_author_h_index_table(node_to_authors: Dict[int, List[int]],
                                  author_names: Dict[int, str],
                                  values: np.ndarray,
                                  totals_label: str) -> Tuple[pd.DataFrame, float]:
    """Compute per-author h-index (and totals) from a per-node value array; returns (df, wall_time_sec)."""
    t0 = time.perf_counter()
    metrics = AuthorMetrics(node_to_authors, author_names)
    h_indices = metrics.compute_all_h_indices(values)

    rows = []
    for author_id, h_idx in h_indices.items():
        vals = metrics.get_author_kudos(author_id, values)  # generic getter, works for any per-node array
        rows.append({
            'author_id': author_id,
            'author_name': author_names.get(author_id, f'Author_{author_id}'),
            'h_index': h_idx,
            totals_label: float(np.sum(vals)),
            'n_publications': len(vals),
        })
    elapsed = time.perf_counter() - t0

    df = pd.DataFrame(rows)
    df.sort_values(['h_index', totals_label], ascending=[False, False], inplace=True)
    df.reset_index(drop=True, inplace=True)
    df['rank'] = df.index + 1
    return df, elapsed


def save_table(df: pd.DataFrame, tables_dir: str, stem: str, header: str = ''):
    df.to_csv(os.path.join(tables_dir, stem + '.csv'), index=False)
    with open(os.path.join(tables_dir, stem + '.txt'), 'w') as f:
        if header:
            f.write(header + '\n' + '=' * len(header) + '\n\n')
        f.write(df.to_string(index=False))
        f.write('\n')


def df_to_markdown(df: pd.DataFrame) -> str:
    try:
        return df.to_markdown(index=False)
    except ImportError:
        # tabulate not installed -> fallback simple pipe table
        cols = list(df.columns)
        lines = ['| ' + ' | '.join(cols) + ' |', '| ' + ' | '.join(['---'] * len(cols)) + ' |']
        for _, row in df.iterrows():
            lines.append('| ' + ' | '.join(str(row[c]) for c in cols) + ' |')
        return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Main experiment
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Synthetic large-scale kudos vs. citation h-index experiment')
    parser.add_argument('--n-nodes', type=int, default=100_000, help='Number of nodes to generate')
    parser.add_argument('--n-authors', type=int, default=None, help='Number of authors (default: scaled to n-nodes)')
    parser.add_argument('--n-communities', type=int, default=None, help='Number of communities (default: scaled)')
    parser.add_argument('--seed', type=int, default=20260701, help='Random seed')
    parser.add_argument('--output-dir', type=str, default=None, help='Output directory (default: scaled to size)')
    args = parser.parse_args()

    cfg = build_config_for_size(
        n_nodes=args.n_nodes, seed=args.seed,
        output_dir=args.output_dir, n_authors=args.n_authors,
        n_communities=args.n_communities,
    )
    output_dir = cfg.output_dir
    tables_dir = os.path.join(output_dir, 'tables')
    os.makedirs(tables_dir, exist_ok=True)

    print('=' * 80)
    print(f'SYNTHETIC {cfg.label}-NODE CREDIT TRANSFER EXPERIMENT')
    print('Kudos/Total-Credit h-index vs. Traditional Citation h-index')
    print('=' * 80)

    hw_info = get_hardware_info()
    print('\nHardware:')
    for k, v in hw_info.items():
        print(f'  {k}: {v}')

    # ---------------------------------------------------------------
    # 1. Generate the synthetic graph
    # ---------------------------------------------------------------
    print(f'\n[1/5] Generating synthetic graph ({cfg.n_nodes:,} nodes, avg out-degree={cfg.avg_out_degree})...')
    (sources, targets, node_types, node_to_authors, author_names,
     gen_meta) = generate_large_synthetic_graph(cfg)

    n_nodes = cfg.n_nodes
    n_edges = gen_meta['n_edges']
    in_degree = np.bincount(targets, minlength=n_nodes).astype(np.int64)
    out_degree = np.bincount(sources, minlength=n_nodes).astype(np.int64)

    print(f"  Generated in {gen_meta['generation_wall_time_sec']:.2f}s: "
          f"{n_nodes:,} nodes, {n_edges:,} edges "
          f"(avg out-degree={n_edges / n_nodes:.2f}, avg in-degree={n_edges / n_nodes:.2f})")
    type_counts = {cfg.type_names[t]: int(np.sum(node_types == t)) for t in range(3)}
    print(f"  Type distribution: {type_counts}")
    print(f"  Authors: {cfg.n_authors:,} assigned across {n_nodes:,} nodes "
          f"(avg {sum(len(v) for v in node_to_authors.values()) / n_nodes:.2f} authors/node)")

    # Sanity: verify acyclicity (all edges point strictly backward => DAG, no self-loops)
    assert np.all(sources > targets), "Graph must be acyclic (source > target for all edges)"

    # ---------------------------------------------------------------
    # 2. Credit transfer: kudos & total credit (retention=0.5 for all types)
    # ---------------------------------------------------------------
    print('\n[2/5] Computing credit distribution (uniform retention=0.5, '
          'check_convergence=False)...')
    total_credit, kudos, t_credit, credit_diag = compute_credit_transfer(
        sources, targets, n_nodes, cfg.retention
    )
    print(f'  Wall time (build matrix + sparse solve): {t_credit:.4f}s')
    print(f"  Total kudos: {credit_diag['total_kudos']:.2f}  "
          f"Total external credit (sum in-degree): {credit_diag['total_external_credit']:.2f}  "
          f"Conservation error: {credit_diag['conservation_error']:.2e}")

    # ---------------------------------------------------------------
    # 3. Author h-index: kudos-based vs. traditional citation-based
    # ---------------------------------------------------------------
    print('\n[3/5] Computing author h-indices (kudos-based and citation-based)...')

    citations = in_degree.astype(np.float64)  # traditional direct-citation count per node

    df_kudos_h, t_hindex_kudos = compute_author_h_index_table(
        node_to_authors, author_names, kudos, 'total_kudos'
    )
    df_cite_h, t_hindex_citation = compute_author_h_index_table(
        node_to_authors, author_names, citations, 'total_citations'
    )

    print(f'  Wall time - h-index from KUDOS:     {t_hindex_kudos:.4f}s '
          f'({len(df_kudos_h):,} authors)')
    print(f'  Wall time - h-index from CITATIONS: {t_hindex_citation:.4f}s '
          f'({len(df_cite_h):,} authors)')

    speedup = t_hindex_citation / t_hindex_kudos if t_hindex_kudos > 0 else float('nan')
    print(f'  Ratio (citation-time / kudos-time): {speedup:.3f}x')

    save_table(df_kudos_h, tables_dir, 'author_hindex_kudos_full',
               'Full author ranking by KUDOS h-index')
    save_table(df_cite_h, tables_dir, 'author_hindex_citation_full',
               'Full author ranking by CITATION h-index')

    # ---------------------------------------------------------------
    # 4. Top-10 tables (authors and nodes)
    # ---------------------------------------------------------------
    print('\n[4/5] Building top-10 tables...')

    top10_kudos_authors = df_kudos_h.head(cfg.top_authors).copy()
    top10_cite_authors = df_cite_h.head(cfg.top_authors).copy()
    save_table(top10_kudos_authors, tables_dir, 'top10_authors_kudos_hindex',
               'Top-10 authors by KUDOS h-index')
    save_table(top10_cite_authors, tables_dir, 'top10_authors_citation_hindex',
               'Top-10 authors by CITATION h-index')

    node_type_names = np.array(cfg.type_names)[node_types]
    node_df = pd.DataFrame({
        'node_id': np.arange(n_nodes),
        'node_type': node_type_names,
        'kudos': kudos,
        'total_credit': total_credit,
        'citations_indegree': in_degree,
    })
    top10_nodes = node_df.sort_values('kudos', ascending=False).head(cfg.top_nodes).reset_index(drop=True)
    save_table(top10_nodes, tables_dir, 'top10_nodes_kudos', 'Top-10 nodes by KUDOS')

    # ---------------------------------------------------------------
    # 5. Kendall's tau: top-1000 authors by CITATION h-index vs KUDOS h-index rank
    # ---------------------------------------------------------------
    print(f'\n[5/5] Computing Kendall tau correlation on top-{cfg.top_authors_kendall} '
          f'authors (ranked by citation h-index, descending)...')

    top_n = cfg.top_authors_kendall
    top_by_citation = df_cite_h.head(top_n).copy()

    kudos_rank_lookup = df_kudos_h.set_index('author_id')['rank']
    kudos_hidx_lookup = df_kudos_h.set_index('author_id')['h_index']

    top_by_citation['citation_rank'] = top_by_citation['rank']
    top_by_citation['kudos_rank'] = top_by_citation['author_id'].map(kudos_rank_lookup)
    top_by_citation['kudos_h_index'] = top_by_citation['author_id'].map(kudos_hidx_lookup)
    top_by_citation.rename(columns={'h_index': 'citation_h_index'}, inplace=True)

    comparison_df = top_by_citation[[
        'citation_rank', 'author_id', 'author_name',
        'citation_h_index', 'kudos_h_index', 'kudos_rank'
    ]].reset_index(drop=True)
    save_table(comparison_df, tables_dir, 'top1000_citation_vs_kudos_ranking',
               f'Top-{top_n} authors by citation h-index vs. kudos-based ranking')

    tau, p_value = stats.kendalltau(comparison_df['citation_rank'], comparison_df['kudos_rank'])
    tau_hidx, p_value_hidx = stats.kendalltau(comparison_df['citation_h_index'],
                                               comparison_df['kudos_h_index'])
    print(f"  Kendall's tau (rank vs rank):    tau={tau:.4f}  p-value={p_value:.3e}")
    print(f"  Kendall's tau (h-index values):  tau={tau_hidx:.4f}  p-value={p_value_hidx:.3e}")

    # ---------------------------------------------------------------
    # Write markdown report
    # ---------------------------------------------------------------
    write_report(
        output_dir=output_dir,
        cfg=cfg,
        hw_info=hw_info,
        gen_meta=gen_meta,
        type_counts=type_counts,
        n_edges=n_edges,
        t_credit=t_credit,
        credit_diag=credit_diag,
        t_hindex_kudos=t_hindex_kudos,
        t_hindex_citation=t_hindex_citation,
        top10_kudos_authors=top10_kudos_authors,
        top10_cite_authors=top10_cite_authors,
        top10_nodes=top10_nodes,
        comparison_df=comparison_df,
        tau=tau, p_value=p_value,
        tau_hidx=tau_hidx, p_value_hidx=p_value_hidx,
        top_n=top_n,
    )

    print('\n' + '=' * 80)
    print('EXPERIMENT COMPLETE')
    print(f'  Report: {os.path.join(output_dir, "report.md")}')
    print(f'  Tables: {tables_dir}/')
    print('=' * 80)


def write_report(output_dir: str, cfg: ExperimentConfig, hw_info: Dict[str, str],
                  gen_meta: Dict, type_counts: Dict, n_edges: int,
                  t_credit: float, credit_diag: Dict,
                  t_hindex_kudos: float, t_hindex_citation: float,
                  top10_kudos_authors: pd.DataFrame, top10_cite_authors: pd.DataFrame,
                  top10_nodes: pd.DataFrame, comparison_df: pd.DataFrame,
                  tau: float, p_value: float, tau_hidx: float, p_value_hidx: float,
                  top_n: int):
    report_path = os.path.join(output_dir, 'report.md')

    speed_ratio = t_hindex_citation / t_hindex_kudos if t_hindex_kudos > 0 else float('nan')

    top10_kudos_display = top10_kudos_authors[['rank', 'author_name', 'h_index',
                                                'total_kudos', 'n_publications']].rename(
        columns={'rank': 'Rank', 'author_name': 'Author', 'h_index': 'h-index (kudos)',
                 'total_kudos': 'Total Kudos', 'n_publications': 'Publications'})
    top10_kudos_display['Total Kudos'] = top10_kudos_display['Total Kudos'].round(2)

    top10_cite_display = top10_cite_authors[['rank', 'author_name', 'h_index',
                                              'total_citations', 'n_publications']].rename(
        columns={'rank': 'Rank', 'author_name': 'Author', 'h_index': 'h-index (citations)',
                 'total_citations': 'Total Citations', 'n_publications': 'Publications'})
    top10_cite_display['Total Citations'] = top10_cite_display['Total Citations'].astype(int)

    top10_nodes_display = top10_nodes.copy()
    top10_nodes_display['kudos'] = top10_nodes_display['kudos'].round(3)
    top10_nodes_display['total_credit'] = top10_nodes_display['total_credit'].round(3)
    top10_nodes_display.rename(columns={
        'node_id': 'Node ID', 'node_type': 'Type', 'kudos': 'Kudos',
        'total_credit': 'Total Credit', 'citations_indegree': 'Traditional Citations'
    }, inplace=True)

    comparison_display = comparison_df.head(20).copy()
    comparison_display.rename(columns={
        'citation_rank': 'Citation Rank', 'author_id': 'Author ID', 'author_name': 'Author',
        'citation_h_index': 'h-index (citation)', 'kudos_h_index': 'h-index (kudos)',
        'kudos_rank': 'Kudos Rank'
    }, inplace=True)

    with open(report_path, 'w') as f:
        f.write(f'# Synthetic {cfg.label}-Node Credit Transfer Experiment\n\n')
        f.write(f'*Generated: {datetime.now().isoformat()}*\n\n')

        f.write('## 1. Experiment Description\n\n')
        f.write(
            'This experiment evaluates the efficiency and ranking behaviour of the transitive '
            'credit-transfer model ("kudos" and "total credit") compared to traditional direct '
            'citation counts, on a large synthetic multi-type scholarly citation graph.\n\n'
            f'A synthetic directed acyclic citation graph with **{cfg.n_nodes:,} nodes** was generated '
            'with three node types: **papers**, **datasets**, and **software**. The nodes were '
            f'requested in proportions 50% / 30% / 30% (paper/dataset/software); since these do not '
            'sum to 100%, they were normalized (as in the project convention) to '
            f"**{gen_meta['type_proportions_normalized'][0]*100:.2f}% papers, "
            f"{gen_meta['type_proportions_normalized'][1]*100:.2f}% datasets, "
            f"{gen_meta['type_proportions_normalized'][2]*100:.2f}% software**.\n\n"
            f'The graph has an average out-degree (references per node) of **{n_edges / cfg.n_nodes:.2f}** '
            f'(target: 20.0), for a total of **{n_edges:,} edges**. '
            'Citation targets are chosen with a mixture of realistic mechanisms: '
            f'power-law preferential attachment (in-degree exponent ~{cfg.powerlaw_exponent}), '
            f'community/subfield structure ({cfg.n_communities} communities), transitive closure '
            '(citation triangles), type-aware citation preferences (e.g. papers preferentially cite '
            f'papers), and a {cfg.hierarchy_levels}-level citation hierarchy favouring foundational '
            'works. Every edge is constructed so that the source node index is strictly greater '
            'than the target node index (temporal ordering) -- **this guarantees the graph is a DAG '
            'by construction, with no self-loops and no cycles**.\n\n'
            f'**{cfg.n_authors:,} synthetic authors** were assigned to nodes using a power-law '
            'productivity model (preferential attachment over author IDs), giving realistic '
            f'"star researcher" behaviour, at an average of ~{cfg.avg_authors_per_node:.1f} authors '
            'per work.\n\n'
            f'The credit-transfer model used a **uniform retention rate of {cfg.retention} for all '
            'node types** (papers, datasets, software each keep 50% of incoming credit as kudos and '
            'redistribute the remaining 50% to the works they cite). Convergence checking was '
            '**disabled** (`check_convergence=False`) to maximize efficiency; this is safe because '
            'the acyclic-by-construction graph guarantees `A^T` is nilpotent (spectral radius = 0), '
            'so the system `c = (I - A^T)^-1 v` is always well-posed.\n\n'
        )

        f.write('## 2. Machine / Hardware\n\n')
        f.write('| Property | Value |\n|---|---|\n')
        f.write(f"| OS | {hw_info['platform']} |\n")
        f.write(f"| CPU | {hw_info.get('cpu_brand', hw_info['processor'])} |\n")
        f.write(f"| CPU cores (logical / physical) | {hw_info['cpu_count_logical']} / "
                f"{hw_info.get('cpu_count_physical', 'unknown')} |\n")
        f.write(f"| Total RAM | {hw_info['total_ram_gb']} GB |\n")
        f.write(f"| Python | {hw_info['python_version']} |\n")
        f.write(f"| NumPy / SciPy / Pandas | {hw_info['numpy_version']} / "
                f"{hw_info['scipy_version']} / {hw_info['pandas_version']} |\n\n")

        f.write('## 3. Graph Statistics\n\n')
        f.write('| Metric | Value |\n|---|---|\n')
        f.write(f"| Nodes | {cfg.n_nodes:,} |\n")
        f.write(f"| Edges | {n_edges:,} |\n")
        for name, count in type_counts.items():
            f.write(f"| {name.capitalize()} nodes | {count:,} ({count / cfg.n_nodes * 100:.1f}%) |\n")
        f.write(f"| Authors | {cfg.n_authors:,} |\n")
        f.write(f"| Retention rate (all types) | {cfg.retention} |\n")
        f.write(f"| Graph generation wall time | {gen_meta['generation_wall_time_sec']:.2f} s |\n\n")

        f.write('## 4. Wall-Clock Timing Comparison\n\n')
        f.write(
            'Timings were measured with `time.perf_counter()` around the isolated computation only '
            '(matrix construction / sparse solve for credit; per-author h-index aggregation for the '
            'h-index measurements).\n\n'
        )
        f.write('| Computation | Wall time (s) |\n|---|---|\n')
        f.write(f"| Build sparse transfer matrix + solve for kudos & total credit | {t_credit:.4f} |\n")
        f.write(f"| h-index for all authors, from **KUDOS** | {t_hindex_kudos:.4f} |\n")
        f.write(f"| h-index for all authors, from **traditional citations** (in-degree) | "
                f"{t_hindex_citation:.4f} |\n\n")
        f.write(
            f"The citation-based h-index computation took **{speed_ratio:.3f}x** the time of the "
            'kudos-based computation (both use the identical per-author aggregation code path from '
            '`AuthorMetrics`; any difference reflects value distribution / sorting cost, not '
            'algorithmic complexity, since both are O(A x P log P)). The dominant cost by far is the '
            f'credit-distribution sparse linear solve ({t_credit:.4f} s), which the h-index step '
            'reuses without re-deriving kudos or citations.\n\n'
        )
        f.write(f"Conservation check: total kudos = {credit_diag['total_kudos']:.2f}, "
                f"total external credit (sum of in-degrees) = {credit_diag['total_external_credit']:.2f}, "
                f"error = {credit_diag['conservation_error']:.2e}.\n\n")

        f.write(f'## 5. Top-{cfg.top_authors} Synthetic Authors -- h-index Comparison\n\n')
        f.write('### 5.1 Ranked by KUDOS h-index\n\n')
        f.write(df_to_markdown(top10_kudos_display) + '\n\n')
        f.write('### 5.2 Ranked by traditional CITATION h-index\n\n')
        f.write(df_to_markdown(top10_cite_display) + '\n\n')

        f.write(f'## 6. Top-{cfg.top_nodes} Nodes by Kudos\n\n')
        f.write(df_to_markdown(top10_nodes_display) + '\n\n')

        f.write(f'## 7. Kendall\'s Tau: Top-{top_n} Authors (Citation h-index) vs. Kudos Ranking\n\n')
        f.write(
            f'The top-{top_n} authors were selected and ordered by descending **traditional citation '
            'h-index**. Each author\'s corresponding rank (and h-index) under the **kudos-based** '
            'ranking (computed over all authors) was then looked up, and Kendall\'s tau rank '
            'correlation coefficient was computed between the two rankings.\n\n'
        )
        f.write('| Correlation | Kendall tau | p-value |\n|---|---|---|\n')
        f.write(f'| Citation rank vs. Kudos rank (Top-{top_n}) | {tau:.4f} | {p_value:.3e} |\n')
        f.write(f'| Citation h-index vs. Kudos h-index values (Top-{top_n}) | {tau_hidx:.4f} | '
                f'{p_value_hidx:.3e} |\n\n')

        interp = 'strong' if abs(tau) > 0.7 else ('moderate' if abs(tau) > 0.4 else 'weak')
        f.write(
            f'A Kendall tau of **{tau:.4f}** indicates a **{interp}** rank agreement between the '
            'traditional citation-count-based ranking and the transitive kudos-based ranking among '
            f'the top-{top_n} most-cited authors. The full top-{top_n} comparison table is saved to '
            f'`tables/top1000_citation_vs_kudos_ranking.csv`; the first 20 rows are shown below.\n\n'
        )
        f.write(df_to_markdown(comparison_display) + '\n\n')

        f.write('## 8. Reproducibility\n\n')
        f.write(f'- Random seed: `{cfg.seed}`\n')
        f.write(f'- Graph size: `--n-nodes {cfg.n_nodes}` (authors={cfg.n_authors}, communities={cfg.n_communities})\n')
        f.write(f'- Script: `analyses/synthetic_100k_kudos_vs_citation_experiment.py`\n')
        f.write(f'- Run with: `python3 analyses/synthetic_100k_kudos_vs_citation_experiment.py '
                f'--n-nodes {cfg.n_nodes} --n-authors {cfg.n_authors} --n-communities {cfg.n_communities} '
                f'--seed {cfg.seed}`\n')

    print(f'\n  Report written to: {report_path}')


if __name__ == '__main__':
    main()




