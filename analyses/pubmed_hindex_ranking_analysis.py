#!/usr/bin/env python3
"""
PubMed H-Index Ranking Analysis across Retention Rates

Every analysis is performed **per retention-rate variation** (1→0.75,
1→0.5, 1→0.25) and data from different variations are NEVER mixed in
the same plot or table row.

Cutoff levels: Top-10, Top-100, Top-1000, Top-10000 (no full list).

Outputs
-------
- analyses/plots/        PDF + PNG plots
- analyses/tables/       TXT (formatted) + CSV tables
- analyses/analysis_report.txt   summary report

Usage
-----
    python3 analyses/pubmed_hindex_ranking_analysis.py \
        [--data-dir DATA_DIR] [--output-dir OUTPUT_DIR]
"""

import os
import sys
import shutil
import argparse
from datetime import datetime

import numpy as np
import pandas as pd
from scipy import stats

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

RETENTION_FILES = {
    1.00: 'pkg24s4_1_author_hindices.txt',
    0.75: 'pkg24s4_0_75_author_hindices.txt',
    0.50: 'pkg24s4_0_5_author_hindices.txt',
    0.25: 'pkg24s4_0.25_author_hindices.txt',
}

RETENTION_RATES = sorted(RETENTION_FILES.keys(), reverse=True)  # [1.0, 0.75, 0.5, 0.25]
BASELINE_RATE = 1.0
OTHER_RATES = [r for r in RETENTION_RATES if r != BASELINE_RATE]  # [0.75, 0.5, 0.25]

CUTOFFS = [10, 100, 1000, 10_000]
CUTOFF_LABELS = {c: f'Top-{c:,}' for c in CUTOFFS}

COL_NAMES = ['author_id', 'h_index', 'total_kudos', 'num_publications', 'author_name']

sns.set_theme(style='whitegrid', font_scale=1.1)
PALETTE = sns.color_palette('colorblind', n_colors=6)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rl(rate: float) -> str:
    """Short column-safe label: 100, 075, 050, 025."""
    return f'{int(rate * 100):03d}'


def _rd(rate: float) -> str:
    """Human-readable label: r=0.25."""
    return f'r={rate:.2f}'


def _var_tag(rate: float) -> str:
    """File-name safe variation tag: 1_to_075."""
    return f'1_to_{_rl(rate)}'


def _var_display(rate: float) -> str:
    """Readable variation label: r=1.0 → r=0.25."""
    return f'r=1.0 \u2192 r={rate:.2f}'


def _save_fig(fig, plots_dir: str, stem: str):
    fig.savefig(os.path.join(plots_dir, stem + '.pdf'), bbox_inches='tight', dpi=150)
    fig.savefig(os.path.join(plots_dir, stem + '.png'), bbox_inches='tight', dpi=150)
    plt.close(fig)


def _save_table(df: pd.DataFrame, tables_dir: str, stem: str,
                txt_header: str = '', index: bool = True):
    """Save a DataFrame as both .csv and .txt (pretty-printed)."""
    csv_path = os.path.join(tables_dir, stem + '.csv')
    txt_path = os.path.join(tables_dir, stem + '.txt')
    df.to_csv(csv_path, index=index)
    with open(txt_path, 'w') as f:
        if txt_header:
            f.write(txt_header + '\n')
            f.write('=' * len(txt_header) + '\n\n')
        f.write(df.to_string(index=index))
        f.write('\n')

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_data(data_dir: str) -> dict[float, pd.DataFrame]:
    data = {}
    for rate, fname in RETENTION_FILES.items():
        path = os.path.join(data_dir, fname)
        if not os.path.isfile(path):
            print(f"  WARNING: File not found: {path}")
            continue
        print(f"  Loading {fname}  (retention={rate}) ...", end=' ', flush=True)
        df = pd.read_csv(
            path, comment='#', sep=r'\s+', names=COL_NAMES,
            dtype={'author_id': np.int64, 'h_index': np.int32,
                   'total_kudos': np.float64, 'num_publications': np.int32,
                   'author_name': str},
        )
        df.drop(columns=['author_name'], inplace=True)
        df.sort_values('h_index', ascending=False, kind='mergesort', inplace=True)
        df.reset_index(drop=True, inplace=True)
        df['rank'] = df.index + 1
        df.set_index('author_id', inplace=True)
        data[rate] = df
        print(f"{len(df):,} authors loaded.")
    return data


def build_pair(data: dict[float, pd.DataFrame], rate: float,
               columns: list[str] | None = None) -> pd.DataFrame:
    """Inner-join baseline (r=1.0) with ONE other rate.  No mixing."""
    if columns is None:
        columns = ['h_index', 'rank']
    base = data[BASELINE_RATE][columns].copy()
    base.rename(columns={c: f'{c}_base' for c in columns}, inplace=True)
    other = data[rate][columns].copy()
    other.rename(columns={c: f'{c}_other' for c in columns}, inplace=True)
    return base.join(other, how='inner')


def build_merged_all(data: dict[float, pd.DataFrame],
                     columns: list[str] | None = None) -> pd.DataFrame:
    """Inner-join all four rates (used only for trajectory plots)."""
    if columns is None:
        columns = ['h_index', 'rank']
    merged = None
    for rate in RETENTION_RATES:
        df = data[rate][columns].copy()
        df.rename(columns={c: f'{c}_{_rl(rate)}' for c in columns}, inplace=True)
        merged = df if merged is None else merged.join(df, how='inner')
    return merged

# ===================================================================
# 1. RANK CORRELATIONS  -  per variation, per cutoff
# ===================================================================

def compute_rank_correlations(data: dict[float, pd.DataFrame],
                              tables_dir: str) -> pd.DataFrame:
    print("\n" + "=" * 80)
    print("1. RANK CORRELATION ANALYSIS")
    print("=" * 80)

    rows = []
    for rate in OTHER_RATES:
        pair = build_pair(data, rate)
        for cutoff in CUTOFFS:
            label = CUTOFF_LABELS[cutoff]
            mask = (pair['rank_base'] <= cutoff) | (pair['rank_other'] <= cutoff)
            sub = pair.loc[mask]
            n = len(sub)
            if n < 3:
                rows.append(dict(variation=_var_display(rate), cutoff=label,
                                 target_rate=rate, n=n,
                                 spearman=np.nan, kendall=np.nan,
                                 weighted_kendall=np.nan))
                continue
            sp, _ = stats.spearmanr(sub['rank_base'], sub['rank_other'])
            if n <= 50_000:
                kt, _ = stats.kendalltau(sub['rank_base'], sub['rank_other'])
                wk, _ = stats.weightedtau(sub['rank_base'], sub['rank_other'])
            else:
                kt, wk = np.nan, np.nan
            rows.append(dict(variation=_var_display(rate), cutoff=label,
                             target_rate=rate, n=n,
                             spearman=sp, kendall=kt, weighted_kendall=wk))

    results = pd.DataFrame(rows)

    # --- print & save per variation ---
    for rate in OTHER_RATES:
        sub = results[results['target_rate'] == rate].copy()
        sub_out = sub[['cutoff', 'n', 'spearman', 'kendall', 'weighted_kendall']].copy()
        sub_out.columns = ['Cutoff', 'N', 'Spearman', 'Kendall', 'W-Kendall']
        title = f'Rank correlations: {_var_display(rate)}'
        print(f"\n--- {title} ---")
        print(sub_out.to_string(index=False))
        _save_table(sub_out, tables_dir,
                    f'correlations_{_var_tag(rate)}',
                    txt_header=title, index=False)

    # also save the combined table
    out_all = results[['variation', 'cutoff', 'n', 'spearman', 'kendall',
                       'weighted_kendall']].copy()
    out_all.columns = ['Variation', 'Cutoff', 'N', 'Spearman', 'Kendall', 'W-Kendall']
    _save_table(out_all, tables_dir, 'correlations_all',
                txt_header='Rank correlations - all variations', index=False)

    return results

# ===================================================================
# 2. H-INDEX CHANGE ANALYSIS  -  per variation, per cutoff
# ===================================================================

def analyze_hindex_changes(data: dict[float, pd.DataFrame],
                           tables_dir: str) -> dict:
    print("\n" + "=" * 80)
    print("2. H-INDEX CHANGE ANALYSIS")
    print("=" * 80)

    all_change_dfs = {}    # key = (rate, cutoff)
    all_gainers = {}       # key = rate
    all_losers = {}        # key = rate

    for rate in OTHER_RATES:
        pair = build_pair(data, rate,
                          columns=['h_index', 'rank', 'total_kudos',
                                   'num_publications'])
        pair['delta_h'] = pair['h_index_other'] - pair['h_index_base']
        pair['delta_rank'] = pair['rank_base'] - pair['rank_other']

        for cutoff in CUTOFFS:
            label = CUTOFF_LABELS[cutoff]
            top = pair[pair['rank_base'] <= cutoff].sort_values('rank_base')

            out = pd.DataFrame({
                'rank_baseline': top['rank_base'].astype(int),
                'author_id': top.index,
                f'h_index_r1.00': top['h_index_base'].astype(int),
                f'h_index_r{rate:.2f}': top['h_index_other'].astype(int),
                'delta_h': top['delta_h'].astype(int),
                'delta_rank': top['delta_rank'].astype(int),
                'num_publications': top['num_publications_base'].astype(int),
            })
            out = out.reset_index(drop=True)

            title = f'H-index change {_var_display(rate)} - {label}'
            print(f"\n--- {title} ({len(out):,} authors) ---")
            print(out.head(min(20, len(out))).to_string(index=False))
            if len(out) > 20:
                print(f"  ... ({len(out) - 20:,} more rows)")
            _save_table(out, tables_dir,
                        f'hindex_change_{_var_tag(rate)}_{cutoff}',
                        txt_header=title, index=False)
            all_change_dfs[(rate, cutoff)] = out

        # --- gainers / losers for this variation ---
        gainers = pair.nlargest(30, 'delta_h')
        losers = pair.nsmallest(30, 'delta_h')

        for tag, subset, direction in [('gainers', gainers, 'INCREASE'),
                                        ('losers', losers, 'DECREASE')]:
            out = pd.DataFrame({
                'author_id': subset.index,
                f'h_index_r1.00': subset['h_index_base'].astype(int),
                f'h_index_r{rate:.2f}': subset['h_index_other'].astype(int),
                'delta_h': subset['delta_h'].astype(int),
                'rank_baseline': subset['rank_base'].astype(int),
                f'rank_r{rate:.2f}': subset['rank_other'].astype(int),
                'delta_rank': subset['delta_rank'].astype(int),
                'num_publications': subset['num_publications_base'].astype(int),
            }).reset_index(drop=True)

            title = f'Top 30 {direction} - {_var_display(rate)}'
            print(f"\n--- {title} ---")
            print(out.to_string(index=False))
            _save_table(out, tables_dir,
                        f'{tag}_{_var_tag(rate)}',
                        txt_header=title, index=False)

        all_gainers[rate] = gainers
        all_losers[rate] = losers

    return dict(change_dfs=all_change_dfs,
                gainers=all_gainers, losers=all_losers)

# ===================================================================
# 3. TRANSITIVITY BENEFICIARIES  -  per variation
# ===================================================================

def analyze_transitivity_beneficiaries(data: dict[float, pd.DataFrame],
                                       tables_dir: str) -> dict:
    print("\n" + "=" * 80)
    print("3. TRANSITIVITY BENEFICIARIES ANALYSIS")
    print("=" * 80)

    beneficiary_dfs = {}

    for rate in OTHER_RATES:
        pair = build_pair(data, rate,
                          columns=['h_index', 'rank', 'total_kudos',
                                   'num_publications'])
        pair['abs_benefit'] = pair['h_index_other'] - pair['h_index_base']
        pair['rel_benefit'] = np.where(
            pair['h_index_base'] > 0,
            pair['abs_benefit'] / pair['h_index_base'],
            np.where(pair['h_index_other'] > 0, np.inf, 0.0))
        pair['kudos_ratio'] = np.where(
            pair['total_kudos_base'] > 0,
            pair['total_kudos_other'] / pair['total_kudos_base'], 0.0)

        # --- Top 50 absolute ---
        top_abs = pair.nlargest(50, 'abs_benefit')
        out_abs = pd.DataFrame({
            'rank': range(1, len(top_abs) + 1),
            'author_id': top_abs.index,
            'h_baseline': top_abs['h_index_base'].astype(int),
            f'h_r{rate:.2f}': top_abs['h_index_other'].astype(int),
            'delta_h': top_abs['abs_benefit'].astype(int),
            'rel_pct': (top_abs['rel_benefit'] * 100).round(1),
            'num_publications': top_abs['num_publications_base'].astype(int),
            'kudos_ratio': top_abs['kudos_ratio'].round(2),
        }).reset_index(drop=True)

        title_abs = f'Top 50 transitivity beneficiaries (absolute) - {_var_display(rate)}'
        print(f"\n--- {title_abs} ---")
        print(out_abs.to_string(index=False))
        _save_table(out_abs, tables_dir,
                    f'beneficiaries_abs_{_var_tag(rate)}',
                    txt_header=title_abs, index=False)

        # --- Top 50 relative (h_baseline >= 10) ---
        filtered = pair[pair['h_index_base'] >= 10]
        top_rel = filtered.nlargest(50, 'rel_benefit')
        out_rel = pd.DataFrame({
            'rank': range(1, len(top_rel) + 1),
            'author_id': top_rel.index,
            'h_baseline': top_rel['h_index_base'].astype(int),
            f'h_r{rate:.2f}': top_rel['h_index_other'].astype(int),
            'delta_h': top_rel['abs_benefit'].astype(int),
            'rel_pct': (top_rel['rel_benefit'] * 100).round(1),
            'num_publications': top_rel['num_publications_base'].astype(int),
            'kudos_ratio': top_rel['kudos_ratio'].round(2),
        }).reset_index(drop=True)

        title_rel = (f'Top 50 transitivity beneficiaries (relative, h>=10) '
                     f'- {_var_display(rate)}')
        print(f"\n--- {title_rel} ---")
        print(out_rel.to_string(index=False))
        _save_table(out_rel, tables_dir,
                    f'beneficiaries_rel_{_var_tag(rate)}',
                    txt_header=title_rel, index=False)

        # --- Summary ---
        n_gain = (pair['abs_benefit'] > 0).sum()
        n_loss = (pair['abs_benefit'] < 0).sum()
        n_same = (pair['abs_benefit'] == 0).sum()
        summary_rows = [
            ('Total authors', len(pair)),
            ('Authors with h-index gain', n_gain),
            ('Authors with h-index loss', n_loss),
            ('Authors unchanged', n_same),
            ('Mean delta-h', round(pair['abs_benefit'].mean(), 3)),
            ('Median delta-h', int(pair['abs_benefit'].median())),
            ('Max gain', int(pair['abs_benefit'].max())),
            ('Max loss', int(pair['abs_benefit'].min())),
        ]
        if n_gain > 0:
            g = pair[pair['abs_benefit'] > 0]
            summary_rows.append(('Mean h_baseline of gainers',
                                 round(g['h_index_base'].mean(), 1)))
            summary_rows.append(('Mean pubs of gainers',
                                 round(g['num_publications_base'].mean(), 1)))
        if n_loss > 0:
            lo = pair[pair['abs_benefit'] < 0]
            summary_rows.append(('Mean h_baseline of losers',
                                 round(lo['h_index_base'].mean(), 1)))
            summary_rows.append(('Mean pubs of losers',
                                 round(lo['num_publications_base'].mean(), 1)))

        sum_df = pd.DataFrame(summary_rows, columns=['Metric', 'Value'])
        title_sum = f'Transitivity benefit summary - {_var_display(rate)}'
        print(f"\n--- {title_sum} ---")
        print(sum_df.to_string(index=False))
        _save_table(sum_df, tables_dir,
                    f'benefit_summary_{_var_tag(rate)}',
                    txt_header=title_sum, index=False)

        beneficiary_dfs[rate] = pair

    return beneficiary_dfs

# ===================================================================
# 4. PLOTS  -  every plot is per variation, never mixing
# ===================================================================

def create_plots(data: dict[float, pd.DataFrame],
                 corr_results: pd.DataFrame,
                 change_results: dict,
                 beneficiary_dfs: dict,
                 plots_dir: str):
    print("\n" + "=" * 80)
    print("4. GENERATING PLOTS")
    print("=" * 80)

    _plot_correlation_bars(corr_results, plots_dir)
    _plot_hindex_trajectories(data, change_results, plots_dir)
    _plot_scatter_per_variation(data, plots_dir)
    _plot_benefit_distribution_per_variation(beneficiary_dfs, plots_dir)
    _plot_top_beneficiaries_bar_per_variation(beneficiary_dfs, plots_dir)
    _plot_rank_displacement_per_variation(data, plots_dir)

    print(f"\n  All plots saved to: {plots_dir}/")


# --- 4a. Correlation bar charts (one per variation) ---

def _plot_correlation_bars(corr_results: pd.DataFrame, plots_dir: str):
    print("  Plotting correlation bar charts...")
    for rate in OTHER_RATES:
        sub = corr_results[corr_results['target_rate'] == rate].copy()
        cutoff_labels = [CUTOFF_LABELS[c] for c in CUTOFFS]
        metrics = ['spearman', 'kendall', 'weighted_kendall']
        metric_names = ['Spearman \u03c1', 'Kendall \u03c4', 'W-Kendall \u03c4']

        fig, ax = plt.subplots(figsize=(9, 5))
        x = np.arange(len(CUTOFFS))
        width = 0.25
        for i, (m, mn) in enumerate(zip(metrics, metric_names)):
            vals = []
            for c in CUTOFFS:
                row = sub[sub['cutoff'] == CUTOFF_LABELS[c]]
                v = row[m].values[0] if len(row) else np.nan
                vals.append(v)
            bars = ax.bar(x + i * width, vals, width, label=mn,
                          color=PALETTE[i], alpha=0.85)
            for bar, v in zip(bars, vals):
                if not np.isnan(v):
                    ax.text(bar.get_x() + bar.get_width() / 2,
                            bar.get_height() + 0.01,
                            f'{v:.3f}', ha='center', va='bottom', fontsize=7)

        ax.set_xticks(x + width)
        ax.set_xticklabels(cutoff_labels)
        ax.set_ylabel('Correlation')
        ax.set_title(f'Rank Correlation vs Baseline \u2013 {_var_display(rate)}')
        ax.set_ylim(-0.6, 1.15)
        ax.axhline(0, color='grey', linewidth=0.5, linestyle='--')
        ax.legend(fontsize=9)
        plt.tight_layout()
        _save_fig(fig, plots_dir, f'correlations_{_var_tag(rate)}')


# --- 4b. H-index trajectories (one per variation) ---

def _plot_hindex_trajectories(data: dict[float, pd.DataFrame],
                              change_results: dict, plots_dir: str):
    print("  Plotting h-index trajectories...")

    # Per-variation trajectory for top-10 and top-20
    for rate in OTHER_RATES:
        pair = build_pair(data, rate, columns=['h_index', 'rank'])
        for top_n, gname in [(10, 'Top-10'), (20, 'Top-20')]:
            top = pair[pair['rank_base'] <= top_n].sort_values('rank_base')
            fig, ax = plt.subplots(figsize=(7, 5))
            for aid, row in top.iterrows():
                h_base = int(row['h_index_base'])
                h_other = int(row['h_index_other'])
                ax.plot([1.0, rate], [h_base, h_other], marker='o',
                        markersize=5, alpha=0.7, label=f'{aid}')
            ax.set_xlabel('Retention Rate')
            ax.set_ylabel('H-Index')
            ax.set_title(f'H-Index: {gname} Authors \u2013 {_var_display(rate)}')
            ax.set_xticks([1.0, rate])
            ax.set_xticklabels(['1.00', f'{rate:.2f}'])
            if top_n <= 15:
                ax.legend(fontsize=6, ncol=2, loc='best')
            ax.grid(True, alpha=0.3)
            plt.tight_layout()
            _save_fig(fig, plots_dir,
                      f'trajectories_{gname.lower().replace("-", "")}_{_var_tag(rate)}')

    # Per-variation trajectories for gainers / losers
    for rate in OTHER_RATES:
        gainers = change_results['gainers'][rate]
        losers = change_results['losers'][rate]
        for tag, subset, label in [('gainers', gainers.head(15), 'Top 15 Gainers'),
                                   ('losers', losers.head(15), 'Top 15 Losers')]:
            fig, ax = plt.subplots(figsize=(8, 5.5))
            for aid, row in subset.iterrows():
                h_base = int(row['h_index_base'])
                h_other = int(row['h_index_other'])
                ax.plot([1.0, rate], [h_base, h_other], marker='o',
                        markersize=5, alpha=0.7,
                        label=f'{aid} (h={h_base})')
            ax.set_xlabel('Retention Rate')
            ax.set_ylabel('H-Index')
            ax.set_title(f'{label} \u2013 {_var_display(rate)}')
            ax.set_xticks([1.0, rate])
            ax.set_xticklabels(['1.00', f'{rate:.2f}'])
            ax.legend(fontsize=6, ncol=2, loc='best')
            ax.grid(True, alpha=0.3)
            plt.tight_layout()
            _save_fig(fig, plots_dir,
                      f'trajectories_{tag}_{_var_tag(rate)}')


# --- 4c. Scatter: baseline h-index vs other (one plot per variation) ---

def _plot_scatter_per_variation(data: dict[float, pd.DataFrame],
                                plots_dir: str):
    print("  Plotting scatter comparisons (per variation)...")
    for rate in OTHER_RATES:
        pair = build_pair(data, rate, columns=['h_index', 'rank'])

        # Full scatter (sampled)
        plot_df = pair if len(pair) <= 50_000 else pair.sample(50_000, random_state=42)
        fig, ax = plt.subplots(figsize=(6.5, 6))
        ax.scatter(plot_df['h_index_base'], plot_df['h_index_other'],
                   alpha=0.08, s=3, color=PALETTE[0], rasterized=True)
        mx = max(plot_df['h_index_base'].max(), plot_df['h_index_other'].max())
        ax.plot([0, mx], [0, mx], 'k--', alpha=0.5, linewidth=1, label='y = x')
        ax.set_xlabel('H-Index at r=1.00 (baseline)')
        ax.set_ylabel(f'H-Index at r={rate:.2f}')
        ax.set_title(f'H-Index Scatter \u2013 {_var_display(rate)}')
        ax.legend(fontsize=9)
        ax.set_aspect('equal', adjustable='datalim')
        plt.tight_layout()
        _save_fig(fig, plots_dir, f'scatter_{_var_tag(rate)}')

        # Top-1000 zoom
        top1k = pair[pair['rank_base'] <= 1000]
        fig, ax = plt.subplots(figsize=(6.5, 6))
        ax.scatter(top1k['h_index_base'], top1k['h_index_other'],
                   alpha=0.35, s=10, color=PALETTE[1])
        mx = max(top1k['h_index_base'].max(), top1k['h_index_other'].max())
        ax.plot([0, mx], [0, mx], 'k--', alpha=0.5, linewidth=1, label='y = x')
        ax.set_xlabel('H-Index at r=1.00')
        ax.set_ylabel(f'H-Index at r={rate:.2f}')
        ax.set_title(f'H-Index Scatter Top-1000 \u2013 {_var_display(rate)}')
        ax.legend(fontsize=9)
        plt.tight_layout()
        _save_fig(fig, plots_dir, f'scatter_top1000_{_var_tag(rate)}')


# --- 4d. Benefit distribution (one per variation) ---

def _plot_benefit_distribution_per_variation(beneficiary_dfs: dict,
                                             plots_dir: str):
    print("  Plotting benefit distribution (per variation)...")
    for rate in OTHER_RATES:
        pair = beneficiary_dfs[rate]
        benefit = pair['abs_benefit']

        fig, axes = plt.subplots(1, 3, figsize=(18, 5))

        # Histogram (log scale)
        ax = axes[0]
        bmin, bmax = benefit.min(), benefit.max()
        bins = np.arange(bmin - 0.5, bmax + 1.5, 1)
        if len(bins) > 200:
            bins = np.linspace(bmin - 0.5, bmax + 0.5, 200)
        ax.hist(benefit.values, bins=bins, color=PALETTE[0], alpha=0.7,
                edgecolor='white', linewidth=0.3)
        ax.axvline(0, color='red', linestyle='--', alpha=0.7)
        ax.set_yscale('log')
        ax.set_xlabel(f'H-Index Change ({_var_display(rate)})')
        ax.set_ylabel('Number of Authors')
        ax.set_title(f'Distribution of \u0394h \u2013 {_var_display(rate)}')

        # Non-zero histogram
        ax = axes[1]
        nz = benefit[benefit != 0]
        if len(nz) > 0:
            bins2 = np.arange(nz.min() - 0.5, nz.max() + 1.5, 1)
            if len(bins2) > 150:
                bins2 = np.linspace(nz.min() - 0.5, nz.max() + 0.5, 150)
            ax.hist(nz.values, bins=bins2, color=PALETTE[1], alpha=0.7,
                    edgecolor='white', linewidth=0.3)
        ax.axvline(0, color='red', linestyle='--', alpha=0.7)
        ax.set_xlabel(f'H-Index Change (non-zero) \u2013 {_var_display(rate)}')
        ax.set_ylabel('Number of Authors')
        ax.set_title(f'Non-Zero \u0394h \u2013 {_var_display(rate)}')

        # Pie
        ax = axes[2]
        n_gain = (benefit > 0).sum()
        n_loss = (benefit < 0).sum()
        n_same = (benefit == 0).sum()
        ax.pie([n_gain, n_loss, n_same],
               labels=[f'Gain ({n_gain:,})', f'Loss ({n_loss:,})',
                       f'No change ({n_same:,})'],
               colors=[PALETTE[2], PALETTE[3], PALETTE[4]],
               autopct='%1.1f%%', startangle=90,
               textprops={'fontsize': 9})
        ax.set_title(f'Authors by \u0394h Category \u2013 {_var_display(rate)}')

        plt.tight_layout()
        _save_fig(fig, plots_dir, f'benefit_distribution_{_var_tag(rate)}')


# --- 4e. Top beneficiaries bar (one per variation) ---

def _plot_top_beneficiaries_bar_per_variation(beneficiary_dfs: dict,
                                              plots_dir: str):
    print("  Plotting top beneficiaries bar (per variation)...")
    for rate in OTHER_RATES:
        pair = beneficiary_dfs[rate]
        top = pair.nlargest(25, 'abs_benefit').copy()
        top['author_label'] = top.index.astype(str)

        fig, ax = plt.subplots(figsize=(10, 8))
        y = np.arange(len(top))
        ax.barh(y, top['h_index_base'].values, height=0.4,
                color=PALETTE[0], alpha=0.8, label='h @ r=1.00')
        ax.barh(y + 0.4, top['h_index_other'].values, height=0.4,
                color=PALETTE[2], alpha=0.8, label=f'h @ r={rate:.2f}')
        ax.set_yticks(y + 0.2)
        ax.set_yticklabels(top['author_label'].values, fontsize=8)
        ax.set_xlabel('H-Index')
        ax.set_title(f'Top 25 Beneficiaries \u2013 {_var_display(rate)}')
        ax.legend(fontsize=10, loc='lower right')
        for i, (_, row) in enumerate(top.iterrows()):
            g = int(row['abs_benefit'])
            ax.text(row['h_index_other'] + 1, i + 0.2,
                    f'+{g}', va='center', fontsize=7, color='green')
        ax.invert_yaxis()
        plt.tight_layout()
        _save_fig(fig, plots_dir, f'top_beneficiaries_{_var_tag(rate)}')


# --- 4f. Rank displacement (one per variation) ---

def _plot_rank_displacement_per_variation(data: dict[float, pd.DataFrame],
                                          plots_dir: str):
    print("  Plotting rank displacement (per variation)...")
    for rate in OTHER_RATES:
        pair = build_pair(data, rate, columns=['h_index', 'rank'])
        pair['rank_change'] = pair['rank_base'] - pair['rank_other']

        fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

        # Left: scatter top-5000
        ax = axes[0]
        top5k = pair[pair['rank_base'] <= 5000]
        sc = ax.scatter(top5k['h_index_base'], top5k['rank_change'],
                        alpha=0.3, s=5, c=top5k['rank_change'],
                        cmap='RdYlGn', rasterized=True)
        ax.axhline(0, color='black', linewidth=0.8, alpha=0.5)
        ax.set_xlabel('H-Index at r=1.0')
        ax.set_ylabel('Rank Change (positive = moved up)')
        ax.set_title(f'Rank Displacement (Top-5000)\n{_var_display(rate)}')
        plt.colorbar(sc, ax=ax, label='Rank Change', shrink=0.8)

        # Right: histogram top-1000
        ax = axes[1]
        top1k = pair[pair['rank_base'] <= 1000]
        rc = top1k['rank_change'].values
        bins = np.linspace(rc.min(), rc.max(), 80)
        ax.hist(rc, bins=bins, color=PALETTE[1], alpha=0.7, edgecolor='white')
        ax.axvline(0, color='red', linestyle='--', alpha=0.7)
        ax.set_xlabel(f'Rank Change ({_var_display(rate)})')
        ax.set_ylabel('Number of Authors')
        ax.set_title(f'Rank Displacement Distribution (Top-1000)\n{_var_display(rate)}')

        plt.tight_layout()
        _save_fig(fig, plots_dir, f'rank_displacement_{_var_tag(rate)}')

# ===================================================================
# 5. SUMMARY REPORT
# ===================================================================

def write_summary_report(corr_results: pd.DataFrame,
                         beneficiary_dfs: dict,
                         output_dir: str):
    path = os.path.join(output_dir, 'analysis_report.txt')
    print(f"\n  Writing summary report to {path}")

    with open(path, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("PubMed Author H-Index Ranking Analysis - Summary Report\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write("=" * 80 + "\n\n")

        f.write("CONFIGURATION\n" + "-" * 40 + "\n")
        f.write(f"  Baseline rate:  {BASELINE_RATE}\n")
        f.write(f"  Variations:     {[f'1->{r}' for r in OTHER_RATES]}\n")
        f.write(f"  Cutoffs:        {CUTOFFS}\n\n")

        for rate in OTHER_RATES:
            pair = beneficiary_dfs[rate]
            ben = pair['abs_benefit']
            n = len(pair)
            f.write(f"VARIATION {_var_display(rate)}\n" + "-" * 40 + "\n")
            f.write(f"  Authors in common:       {n:>10,}\n")
            f.write(f"  Authors gaining h-index: {(ben > 0).sum():>10,} "
                    f"({(ben > 0).mean()*100:.1f}%)\n")
            f.write(f"  Authors losing h-index:  {(ben < 0).sum():>10,} "
                    f"({(ben < 0).mean()*100:.1f}%)\n")
            f.write(f"  Authors unchanged:       {(ben == 0).sum():>10,} "
                    f"({(ben == 0).mean()*100:.1f}%)\n")
            f.write(f"  Mean dh:  {ben.mean():>+.3f}\n")
            f.write(f"  Max gain: {ben.max():>+d}    Max loss: {ben.min():>+d}\n")

            # Correlations for this variation
            sub = corr_results[corr_results['target_rate'] == rate]
            for _, row in sub.iterrows():
                sp = f"{row['spearman']:.4f}" if not np.isnan(row['spearman']) else 'N/A'
                kt = f"{row['kendall']:.4f}" if not np.isnan(row['kendall']) else 'N/A'
                f.write(f"  {row['cutoff']:<10}  Spearman={sp}  Kendall={kt}\n")
            f.write("\n")

    print(f"  Report written to {path}")

# ===================================================================
# MAIN
# ===================================================================

def main():
    parser = argparse.ArgumentParser(
        description='PubMed H-Index Ranking Analysis')
    parser.add_argument('--data-dir', default='data/pubmed')
    parser.add_argument('--output-dir', default='analyses')
    args = parser.parse_args()

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = (os.path.join(project_root, args.data_dir)
                if not os.path.isabs(args.data_dir) else args.data_dir)
    output_dir = (os.path.join(project_root, args.output_dir)
                  if not os.path.isabs(args.output_dir) else args.output_dir)

    plots_dir = os.path.join(output_dir, 'plots')
    tables_dir = os.path.join(output_dir, 'tables')

    # Clean old outputs
    for d in [plots_dir, tables_dir]:
        if os.path.isdir(d):
            shutil.rmtree(d)
        os.makedirs(d, exist_ok=True)

    print("=" * 80)
    print("PubMed Author H-Index Ranking Analysis")
    print(f"  Data directory:   {data_dir}")
    print(f"  Output directory: {output_dir}")
    print(f"  Plots:            {plots_dir}")
    print(f"  Tables:           {tables_dir}")
    print(f"  Timestamp:        {datetime.now().isoformat()}")
    print("=" * 80)

    print("\nLoading data...")
    data = load_data(data_dir)
    if len(data) < 2:
        print("ERROR: Need at least 2 files. Exiting.")
        sys.exit(1)

    # 1. Correlations
    corr_results = compute_rank_correlations(data, tables_dir)

    # 2. H-index changes
    change_results = analyze_hindex_changes(data, tables_dir)

    # 3. Transitivity beneficiaries
    beneficiary_dfs = analyze_transitivity_beneficiaries(data, tables_dir)

    # 4. Plots
    create_plots(data, corr_results, change_results, beneficiary_dfs, plots_dir)

    # 5. Report
    write_summary_report(corr_results, beneficiary_dfs, output_dir)

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)


if __name__ == '__main__':
    main()

