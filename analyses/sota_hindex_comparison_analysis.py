#!/usr/bin/env python3
"""
Compare SOTA h-index variants (Katz/PageRank) against standard h-index baseline.

The baseline is the retention=1 dataset:
- data/pubmed/pkg24s4_1_author_hindices.txt

SOTA datasets:
- data/sota_hindex/katz_hindex_500k.txt
- data/sota_hindex/pagerank_hindex_500k.txt

Outputs are written to a dedicated analysis folder by default:
- analyses/sota_hindex_comparison/plots
- analyses/sota_hindex_comparison/tables
- analyses/sota_hindex_comparison/analysis_report.txt

Usage:
    python3 analyses/sota_hindex_comparison_analysis.py \
        [--baseline-data-dir DATA_DIR] \
        [--sota-data-dir DATA_DIR] \
        [--output-dir OUTPUT_DIR]
"""

import os
import sys
import shutil
import argparse
from datetime import datetime
from typing import cast

import numpy as np
import pandas as pd
from scipy import stats

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns


BASELINE_KEY = 'baseline'
METHOD_FILES = {
    'katz': 'katz_hindex_500k.txt',
    'pagerank': 'pagerank_hindex_500k.txt',
}
BASELINE_FILE = 'pkg24s4_1_author_hindices.txt'
METHODS = list(METHOD_FILES.keys())

CUTOFFS = [10, 100, 1000, 10_000]
CUTOFF_LABELS = {c: f'Top-{c:,}' for c in CUTOFFS}
COL_NAMES = ['author_id', 'h_index', 'total_kudos', 'num_publications', 'author_name']

sns.set_theme(style='whitegrid', font_scale=1.1)
PALETTE = sns.color_palette('colorblind', n_colors=6)


def _method_tag(method: str) -> str:
    return f'baseline_to_{method}'


def _method_display(method: str) -> str:
    return f'baseline -> {method}'


def _save_fig(fig, plots_dir: str, stem: str):
    fig.savefig(os.path.join(plots_dir, stem + '.pdf'), bbox_inches='tight', dpi=150)
    fig.savefig(os.path.join(plots_dir, stem + '.png'), bbox_inches='tight', dpi=150)
    plt.close(fig)


def _save_table(df: pd.DataFrame, tables_dir: str, stem: str,
                txt_header: str = '', index: bool = True):
    csv_path = os.path.join(tables_dir, stem + '.csv')
    txt_path = os.path.join(tables_dir, stem + '.txt')
    df.to_csv(csv_path, index=index)
    with open(txt_path, 'w') as f:
        if txt_header:
            f.write(txt_header + '\n')
            f.write('=' * len(txt_header) + '\n\n')
        f.write(df.to_string(index=index))
        f.write('\n')


def _load_hindex_file(path: str, label: str) -> pd.DataFrame:
    if not os.path.isfile(path):
        raise FileNotFoundError(f'Missing required file for {label}: {path}')
    print(f'  Loading {label}: {os.path.basename(path)} ...', end=' ', flush=True)
    df = pd.read_csv(
        path,
        comment='#',
        sep=r'\s+',
        names=COL_NAMES,
        dtype={
            'author_id': np.int64,
            'h_index': np.int32,
            'total_kudos': np.float64,
            'num_publications': np.int32,
            'author_name': str,
        },
    )
    df.drop(columns=['author_name'], inplace=True)
    df.sort_values('h_index', ascending=False, kind='mergesort', inplace=True)
    df.reset_index(drop=True, inplace=True)
    df['rank'] = df.index + 1
    df.set_index('author_id', inplace=True)
    print(f'{len(df):,} authors loaded.')
    return df


def load_data(baseline_data_dir: str, sota_data_dir: str) -> dict[str, pd.DataFrame]:
    data = {
        BASELINE_KEY: _load_hindex_file(os.path.join(baseline_data_dir, BASELINE_FILE), 'baseline')
    }
    for method, fname in METHOD_FILES.items():
        data[method] = _load_hindex_file(os.path.join(sota_data_dir, fname), method)
    return data


def build_pair(data: dict[str, pd.DataFrame], method: str,
               columns: list[str] | None = None) -> pd.DataFrame:
    if columns is None:
        columns = ['h_index', 'rank']
    base = data[BASELINE_KEY][columns].copy()
    base.rename(columns={c: f'{c}_base' for c in columns}, inplace=True)
    other = data[method][columns].copy()
    other.rename(columns={c: f'{c}_other' for c in columns}, inplace=True)
    return base.join(other, how='inner')


def compute_rank_correlations(data: dict[str, pd.DataFrame],
                              tables_dir: str) -> pd.DataFrame:
    print('\n' + '=' * 80)
    print('1. RANK CORRELATION ANALYSIS')
    print('=' * 80)

    rows = []
    for method in METHODS:
        pair = build_pair(data, method)
        for cutoff in CUTOFFS:
            label = CUTOFF_LABELS[cutoff]
            mask = (pair['rank_base'] <= cutoff) | (pair['rank_other'] <= cutoff)
            sub = pair.loc[mask]
            n = len(sub)
            if n < 3:
                rows.append(dict(
                    variation=_method_display(method), method=method, cutoff=label,
                    n=n, spearman=np.nan, kendall=np.nan, weighted_kendall=np.nan,
                ))
                continue
            sp, _ = stats.spearmanr(sub['rank_base'], sub['rank_other'])
            if n <= 50_000:
                kt, _ = stats.kendalltau(sub['rank_base'], sub['rank_other'])
                wk, _ = stats.weightedtau(sub['rank_base'], sub['rank_other'])
            else:
                kt, wk = np.nan, np.nan
            rows.append(dict(
                variation=_method_display(method), method=method, cutoff=label,
                n=n, spearman=sp, kendall=kt, weighted_kendall=wk,
            ))

    results = pd.DataFrame(rows)

    for method in METHODS:
        sub = results[results['method'] == method].copy()
        sub_out = sub[['cutoff', 'n', 'spearman', 'kendall', 'weighted_kendall']].copy()
        sub_out.columns = ['Cutoff', 'N', 'Spearman', 'Kendall', 'W-Kendall']
        title = f'Rank correlations: {_method_display(method)}'
        print(f'\n--- {title} ---')
        print(sub_out.to_string(index=False))
        _save_table(sub_out, tables_dir, f'correlations_{_method_tag(method)}', txt_header=title, index=False)

    out_all = results[['variation', 'cutoff', 'n', 'spearman', 'kendall', 'weighted_kendall']].copy()
    out_all.columns = ['Variation', 'Cutoff', 'N', 'Spearman', 'Kendall', 'W-Kendall']
    _save_table(out_all, tables_dir, 'correlations_all', txt_header='Rank correlations - all methods', index=False)
    return results


def analyze_hindex_changes(data: dict[str, pd.DataFrame],
                           tables_dir: str) -> dict:
    print('\n' + '=' * 80)
    print('2. H-INDEX CHANGE ANALYSIS')
    print('=' * 80)

    all_change_dfs = {}
    all_gainers = {}
    all_losers = {}

    for method in METHODS:
        pair = build_pair(data, method, columns=['h_index', 'rank', 'total_kudos', 'num_publications'])
        pair['delta_h'] = pair['h_index_other'] - pair['h_index_base']
        pair['delta_rank'] = pair['rank_base'] - pair['rank_other']

        for cutoff in CUTOFFS:
            label = CUTOFF_LABELS[cutoff]
            top = pair[pair['rank_base'] <= cutoff].sort_values('rank_base')

            out = pd.DataFrame({
                'rank_baseline': top['rank_base'].astype(int),
                'author_id': top.index,
                'h_index_baseline': top['h_index_base'].astype(int),
                f'h_index_{method}': top['h_index_other'].astype(int),
                'delta_h': top['delta_h'].astype(int),
                'delta_rank': top['delta_rank'].astype(int),
                'num_publications': top['num_publications_base'].astype(int),
            }).reset_index(drop=True)

            title = f'H-index change {_method_display(method)} - {label}'
            print(f'\n--- {title} ({len(out):,} authors) ---')
            print(out.head(min(20, len(out))).to_string(index=False))
            if len(out) > 20:
                print(f'  ... ({len(out) - 20:,} more rows)')
            _save_table(out, tables_dir, f'hindex_change_{_method_tag(method)}_{cutoff}', txt_header=title, index=False)
            all_change_dfs[(method, cutoff)] = out

        gainers = pair.nlargest(30, 'delta_h')
        losers = pair.nsmallest(30, 'delta_h')

        for tag, subset, direction in [('gainers', gainers, 'INCREASE'), ('losers', losers, 'DECREASE')]:
            out = pd.DataFrame({
                'author_id': subset.index,
                'h_index_baseline': subset['h_index_base'].astype(int),
                f'h_index_{method}': subset['h_index_other'].astype(int),
                'delta_h': subset['delta_h'].astype(int),
                'rank_baseline': subset['rank_base'].astype(int),
                f'rank_{method}': subset['rank_other'].astype(int),
                'delta_rank': subset['delta_rank'].astype(int),
                'num_publications': subset['num_publications_base'].astype(int),
            }).reset_index(drop=True)

            title = f'Top 30 {direction} - {_method_display(method)}'
            print(f'\n--- {title} ---')
            print(out.to_string(index=False))
            _save_table(out, tables_dir, f'{tag}_{_method_tag(method)}', txt_header=title, index=False)

        all_gainers[method] = gainers
        all_losers[method] = losers

    return {'change_dfs': all_change_dfs, 'gainers': all_gainers, 'losers': all_losers}


def analyze_transitivity_beneficiaries(data: dict[str, pd.DataFrame],
                                       tables_dir: str) -> dict[str, pd.DataFrame]:
    print('\n' + '=' * 80)
    print('3. BENEFICIARIES ANALYSIS (SOTA VS BASELINE)')
    print('=' * 80)

    beneficiary_dfs = {}

    for method in METHODS:
        pair = build_pair(data, method, columns=['h_index', 'rank', 'total_kudos', 'num_publications'])
        pair['abs_benefit'] = pair['h_index_other'] - pair['h_index_base']
        pair['rel_benefit'] = np.where(
            pair['h_index_base'] > 0,
            pair['abs_benefit'] / pair['h_index_base'],
            np.where(pair['h_index_other'] > 0, np.inf, 0.0),
        )
        pair['kudos_ratio'] = np.where(
            pair['total_kudos_base'] > 0,
            pair['total_kudos_other'] / pair['total_kudos_base'],
            0.0,
        )

        top_abs = pair.nlargest(50, 'abs_benefit')
        out_abs = pd.DataFrame({
            'rank': range(1, len(top_abs) + 1),
            'author_id': top_abs.index,
            'h_baseline': top_abs['h_index_base'].astype(int),
            f'h_{method}': top_abs['h_index_other'].astype(int),
            'delta_h': top_abs['abs_benefit'].astype(int),
            'rel_pct': (top_abs['rel_benefit'] * 100).round(1),
            'num_publications': top_abs['num_publications_base'].astype(int),
            'kudos_ratio': top_abs['kudos_ratio'].round(2),
        }).reset_index(drop=True)

        title_abs = f'Top 50 beneficiaries (absolute) - {_method_display(method)}'
        print(f'\n--- {title_abs} ---')
        print(out_abs.to_string(index=False))
        _save_table(out_abs, tables_dir, f'beneficiaries_abs_{_method_tag(method)}', txt_header=title_abs, index=False)

        filtered = pair[pair['h_index_base'] >= 10]
        top_rel = filtered.nlargest(50, 'rel_benefit')
        out_rel = pd.DataFrame({
            'rank': range(1, len(top_rel) + 1),
            'author_id': top_rel.index,
            'h_baseline': top_rel['h_index_base'].astype(int),
            f'h_{method}': top_rel['h_index_other'].astype(int),
            'delta_h': top_rel['abs_benefit'].astype(int),
            'rel_pct': (top_rel['rel_benefit'] * 100).round(1),
            'num_publications': top_rel['num_publications_base'].astype(int),
            'kudos_ratio': top_rel['kudos_ratio'].round(2),
        }).reset_index(drop=True)

        title_rel = f'Top 50 beneficiaries (relative, h>=10) - {_method_display(method)}'
        print(f'\n--- {title_rel} ---')
        print(out_rel.to_string(index=False))
        _save_table(out_rel, tables_dir, f'beneficiaries_rel_{_method_tag(method)}', txt_header=title_rel, index=False)

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
            summary_rows.append(('Mean h_baseline of gainers', round(g['h_index_base'].mean(), 1)))
            summary_rows.append(('Mean pubs of gainers', round(g['num_publications_base'].mean(), 1)))
        if n_loss > 0:
            lo = pair[pair['abs_benefit'] < 0]
            summary_rows.append(('Mean h_baseline of losers', round(lo['h_index_base'].mean(), 1)))
            summary_rows.append(('Mean pubs of losers', round(lo['num_publications_base'].mean(), 1)))

        sum_df = pd.DataFrame(summary_rows, columns=['Metric', 'Value'])
        title_sum = f'Benefit summary - {_method_display(method)}'
        print(f'\n--- {title_sum} ---')
        print(sum_df.to_string(index=False))
        _save_table(sum_df, tables_dir, f'benefit_summary_{_method_tag(method)}', txt_header=title_sum, index=False)

        beneficiary_dfs[method] = pair

    return beneficiary_dfs


def create_plots(data: dict[str, pd.DataFrame],
                 corr_results: pd.DataFrame,
                 change_results: dict,
                 beneficiary_dfs: dict,
                 plots_dir: str):
    print('\n' + '=' * 80)
    print('4. GENERATING PLOTS')
    print('=' * 80)

    _plot_correlation_bars(corr_results, plots_dir)
    _plot_hindex_trajectories(data, change_results, plots_dir)
    _plot_scatter_per_method(data, plots_dir)
    _plot_benefit_distribution_per_method(beneficiary_dfs, plots_dir)
    _plot_top_beneficiaries_bar_per_method(beneficiary_dfs, plots_dir)
    _plot_rank_displacement_per_method(data, plots_dir)

    print(f'\n  All plots saved to: {plots_dir}/')


def _plot_correlation_bars(corr_results: pd.DataFrame, plots_dir: str):
    print('  Plotting correlation bar charts...')
    for method in METHODS:
        sub = corr_results[corr_results['method'] == method].copy()
        cutoff_labels = [CUTOFF_LABELS[c] for c in CUTOFFS]
        metrics = ['spearman', 'kendall', 'weighted_kendall']
        metric_names = ['Spearman', 'Kendall', 'W-Kendall']

        fig, ax = plt.subplots(figsize=(9, 5))
        x = np.arange(len(CUTOFFS))
        width = 0.25
        for i, (m, mn) in enumerate(zip(metrics, metric_names)):
            vals = []
            for c in CUTOFFS:
                row = sub[sub['cutoff'] == CUTOFF_LABELS[c]]
                vals.append(row[m].values[0] if len(row) else np.nan)
            bars = ax.bar(x + i * width, vals, width, label=mn, color=PALETTE[i], alpha=0.85)
            for bar, v in zip(bars, vals):
                if not np.isnan(v):
                    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                            f'{v:.3f}', ha='center', va='bottom', fontsize=7)

        ax.set_xticks(x + width)
        ax.set_xticklabels(cutoff_labels)
        ax.set_ylabel('Correlation')
        ax.set_title(f'Rank Correlation vs Baseline - {method}')
        ax.set_ylim(-0.6, 1.15)
        ax.axhline(0, color='grey', linewidth=0.5, linestyle='--')
        ax.legend(fontsize=9)
        plt.tight_layout()
        _save_fig(fig, plots_dir, f'correlations_{_method_tag(method)}')


def _plot_hindex_trajectories(data: dict[str, pd.DataFrame],
                              change_results: dict,
                              plots_dir: str):
    print('  Plotting h-index trajectories...')
    for method in METHODS:
        pair = build_pair(data, method, columns=['h_index', 'rank'])

        for top_n, gname in [(10, 'Top-10'), (20, 'Top-20')]:
            top = pair[pair['rank_base'] <= top_n].sort_values('rank_base')
            fig, ax = plt.subplots(figsize=(7, 5))
            for aid, row in top.iterrows():
                ax.plot([0, 1], [int(row['h_index_base']), int(row['h_index_other'])],
                        marker='o', markersize=5, alpha=0.7, label=f'{aid}')
            ax.set_xlabel('Method')
            ax.set_ylabel('H-Index')
            ax.set_title(f'H-Index: {gname} Authors - {_method_display(method)}')
            ax.set_xticks([0, 1])
            ax.set_xticklabels(['baseline', method])
            if top_n <= 15:
                ax.legend(fontsize=6, ncol=2, loc='best')
            ax.grid(True, alpha=0.3)
            plt.tight_layout()
            _save_fig(fig, plots_dir, f'trajectories_{gname.lower().replace("-", "")}_{_method_tag(method)}')

        gainers = change_results['gainers'][method]
        losers = change_results['losers'][method]
        for tag, subset, label in [('gainers', gainers.head(15), 'Top 15 Gainers'),
                                   ('losers', losers.head(15), 'Top 15 Losers')]:
            fig, ax = plt.subplots(figsize=(8, 5.5))
            for aid, row in subset.iterrows():
                ax.plot([0, 1], [int(row['h_index_base']), int(row['h_index_other'])],
                        marker='o', markersize=5, alpha=0.7,
                        label=f'{aid} (h={int(row["h_index_base"])})')
            ax.set_xlabel('Method')
            ax.set_ylabel('H-Index')
            ax.set_title(f'{label} - {_method_display(method)}')
            ax.set_xticks([0, 1])
            ax.set_xticklabels(['baseline', method])
            ax.legend(fontsize=6, ncol=2, loc='best')
            ax.grid(True, alpha=0.3)
            plt.tight_layout()
            _save_fig(fig, plots_dir, f'trajectories_{tag}_{_method_tag(method)}')


def _plot_scatter_per_method(data: dict[str, pd.DataFrame], plots_dir: str):
    print('  Plotting scatter comparisons...')
    for method in METHODS:
        pair = build_pair(data, method, columns=['h_index', 'rank'])

        plot_df = pair if len(pair) <= 50_000 else pair.sample(50_000, random_state=42)
        fig, ax = plt.subplots(figsize=(6.5, 6))
        ax.scatter(plot_df['h_index_base'], plot_df['h_index_other'], alpha=0.08, s=3,
                   color=PALETTE[0], rasterized=True)
        mx = float(max(plot_df['h_index_base'].max(), plot_df['h_index_other'].max()))
        ax.plot([0, mx], [0, mx], 'k--', alpha=0.5, linewidth=1, label='y = x')
        ax.set_xlabel('H-Index baseline')
        ax.set_ylabel(f'H-Index {method}')
        ax.set_title(f'H-Index Scatter - {_method_display(method)}')
        ax.legend(fontsize=9)
        ax.set_aspect('equal', adjustable='datalim')
        plt.tight_layout()
        _save_fig(fig, plots_dir, f'scatter_{_method_tag(method)}')

        top1k = pair[pair['rank_base'] <= 1000]
        fig, ax = plt.subplots(figsize=(6.5, 6))
        ax.scatter(top1k['h_index_base'], top1k['h_index_other'], alpha=0.35, s=10, color=PALETTE[1])
        mx = float(max(top1k['h_index_base'].max(), top1k['h_index_other'].max()))
        ax.plot([0, mx], [0, mx], 'k--', alpha=0.5, linewidth=1, label='y = x')
        ax.set_xlabel('H-Index baseline')
        ax.set_ylabel(f'H-Index {method}')
        ax.set_title(f'H-Index Scatter Top-1000 - {_method_display(method)}')
        ax.legend(fontsize=9)
        plt.tight_layout()
        _save_fig(fig, plots_dir, f'scatter_top1000_{_method_tag(method)}')


def _plot_benefit_distribution_per_method(beneficiary_dfs: dict, plots_dir: str):
    print('  Plotting benefit distribution...')
    for method in METHODS:
        pair = beneficiary_dfs[method]
        benefit = pair['abs_benefit']

        fig, axes = plt.subplots(1, 3, figsize=(18, 5))

        ax = axes[0]
        bmin, bmax = benefit.min(), benefit.max()
        bins = np.arange(bmin - 0.5, bmax + 1.5, 1)
        if len(bins) > 200:
            bins = np.linspace(bmin - 0.5, bmax + 0.5, 200)
        ax.hist(benefit.values, bins=bins, color=PALETTE[0], alpha=0.7, edgecolor='white', linewidth=0.3)
        ax.axvline(0, color='red', linestyle='--', alpha=0.7)
        ax.set_yscale('log')
        ax.set_xlabel(f'H-Index Change ({_method_display(method)})')
        ax.set_ylabel('Number of Authors')
        ax.set_title(f'Distribution of delta-h - {_method_display(method)}')

        ax = axes[1]
        nz = benefit[benefit != 0]
        if len(nz) > 0:
            bins2 = np.arange(nz.min() - 0.5, nz.max() + 1.5, 1)
            if len(bins2) > 150:
                bins2 = np.linspace(nz.min() - 0.5, nz.max() + 0.5, 150)
            ax.hist(nz.values, bins=bins2, color=PALETTE[1], alpha=0.7, edgecolor='white', linewidth=0.3)
        ax.axvline(0, color='red', linestyle='--', alpha=0.7)
        ax.set_xlabel(f'H-Index Change (non-zero) - {_method_display(method)}')
        ax.set_ylabel('Number of Authors')
        ax.set_title(f'Non-Zero delta-h - {_method_display(method)}')

        ax = axes[2]
        n_gain = (benefit > 0).sum()
        n_loss = (benefit < 0).sum()
        n_same = (benefit == 0).sum()
        ax.pie([n_gain, n_loss, n_same],
               labels=[f'Gain ({n_gain:,})', f'Loss ({n_loss:,})', f'No change ({n_same:,})'],
               colors=[PALETTE[2], PALETTE[3], PALETTE[4]],
               autopct='%1.1f%%', startangle=90, textprops={'fontsize': 9})
        ax.set_title(f'Authors by delta-h category - {_method_display(method)}')

        plt.tight_layout()
        _save_fig(fig, plots_dir, f'benefit_distribution_{_method_tag(method)}')


def _plot_top_beneficiaries_bar_per_method(beneficiary_dfs: dict, plots_dir: str):
    print('  Plotting top beneficiaries bar charts...')
    for method in METHODS:
        pair = beneficiary_dfs[method]
        top = pair.nlargest(25, 'abs_benefit').copy()
        top['author_label'] = top.index.astype(str)

        fig, ax = plt.subplots(figsize=(10, 8))
        y = np.arange(len(top))
        ax.barh(y, top['h_index_base'].values, height=0.4, color=PALETTE[0], alpha=0.8, label='h @ baseline')
        ax.barh(y + 0.4, top['h_index_other'].values, height=0.4, color=PALETTE[2], alpha=0.8, label=f'h @ {method}')
        ax.set_yticks(y + 0.2)
        ax.set_yticklabels(top['author_label'].values, fontsize=8)
        ax.set_xlabel('H-Index')
        ax.set_title(f'Top 25 Beneficiaries - {_method_display(method)}')
        ax.legend(fontsize=10, loc='lower right')
        for i, (_, row) in enumerate(top.iterrows()):
            gain = int(row['abs_benefit'])
            sign = '+' if gain >= 0 else ''
            ax.text(row['h_index_other'] + 1, i + 0.2, f'{sign}{gain}', va='center', fontsize=7, color='green')
        ax.invert_yaxis()
        plt.tight_layout()
        _save_fig(fig, plots_dir, f'top_beneficiaries_{_method_tag(method)}')


def _plot_rank_displacement_per_method(data: dict[str, pd.DataFrame], plots_dir: str):
    print('  Plotting rank displacement...')
    for method in METHODS:
        pair = build_pair(data, method, columns=['h_index', 'rank'])
        pair['rank_change'] = pair['rank_base'] - pair['rank_other']

        fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

        ax = axes[0]
        top5k = pair[pair['rank_base'] <= 5000]
        sc = ax.scatter(top5k['h_index_base'], top5k['rank_change'], alpha=0.3, s=5,
                        c=top5k['rank_change'], cmap='RdYlGn', rasterized=True)
        ax.axhline(0, color='black', linewidth=0.8, alpha=0.5)
        ax.set_xlabel('H-Index baseline')
        ax.set_ylabel('Rank Change (positive = moved up)')
        ax.set_title(f'Rank Displacement (Top-5000)\n{_method_display(method)}')
        plt.colorbar(sc, ax=ax, label='Rank Change', shrink=0.8)

        ax = axes[1]
        top1k = pair[pair['rank_base'] <= 1000]
        rc = top1k['rank_change'].values
        bins = np.linspace(rc.min(), rc.max(), 80)
        ax.hist(rc, bins=bins, color=PALETTE[1], alpha=0.7, edgecolor='white')
        ax.axvline(0, color='red', linestyle='--', alpha=0.7)
        ax.set_xlabel(f'Rank Change ({_method_display(method)})')
        ax.set_ylabel('Number of Authors')
        ax.set_title(f'Rank Displacement Distribution (Top-1000)\n{_method_display(method)}')

        plt.tight_layout()
        _save_fig(fig, plots_dir, f'rank_displacement_{_method_tag(method)}')


def write_summary_report(corr_results: pd.DataFrame,
                         beneficiary_dfs: dict,
                         output_dir: str):
    path = os.path.join(output_dir, 'analysis_report.txt')
    print(f'\n  Writing summary report to {path}')

    with open(path, 'w') as f:
        f.write('=' * 80 + '\n')
        f.write('SOTA (Katz/PageRank) vs Baseline H-Index - Summary Report\n')
        f.write(f'Generated: {datetime.now().isoformat()}\n')
        f.write('=' * 80 + '\n\n')

        f.write('CONFIGURATION\n' + '-' * 40 + '\n')
        f.write(f'  Baseline file: {BASELINE_FILE}\n')
        f.write(f'  Methods:       {METHODS}\n')
        f.write(f'  Cutoffs:       {CUTOFFS}\n\n')

        for method in METHODS:
            pair = beneficiary_dfs[method]
            ben = pair['abs_benefit']
            f.write(f'METHOD {_method_display(method)}\n' + '-' * 40 + '\n')
            f.write(f'  Authors in common:       {len(pair):>10,}\n')
            f.write(f'  Authors gaining h-index: {(ben > 0).sum():>10,} ({(ben > 0).mean()*100:.1f}%)\n')
            f.write(f'  Authors losing h-index:  {(ben < 0).sum():>10,} ({(ben < 0).mean()*100:.1f}%)\n')
            f.write(f'  Authors unchanged:       {(ben == 0).sum():>10,} ({(ben == 0).mean()*100:.1f}%)\n')
            f.write(f'  Mean dh:  {ben.mean():>+.3f}\n')
            f.write(f'  Max gain: {ben.max():>+d}    Max loss: {ben.min():>+d}\n')

            sub = corr_results[corr_results['method'] == method]
            for _, row in sub.iterrows():
                sp = f"{row['spearman']:.4f}" if not np.isnan(row['spearman']) else 'N/A'
                kt = f"{row['kendall']:.4f}" if not np.isnan(row['kendall']) else 'N/A'
                f.write(f"  {row['cutoff']:<10}  Spearman={sp}  Kendall={kt}\n")
            f.write('\n')

    print(f'  Report written to {path}')


def validate_results(data: dict[str, pd.DataFrame],
                     corr_results: pd.DataFrame,
                     change_results: dict,
                     beneficiary_dfs: dict,
                     tables_dir: str):
    print('\n' + '=' * 80)
    print('5. VALIDATION (DOUBLE CHECK)')
    print('=' * 80)

    checks = []
    for method in METHODS:
        pair = build_pair(data, method, columns=['h_index', 'rank'])
        checks.append((f'{method}: common authors > 0', len(pair) > 0))

        ben = beneficiary_dfs[method]
        checks.append((f'{method}: delta consistency', np.array_equal(
            (ben['h_index_other'] - ben['h_index_base']).values,
            ben['abs_benefit'].values,
        )))

        top10_csv = os.path.join(tables_dir, f'hindex_change_{_method_tag(method)}_10.csv')
        top10 = pd.read_csv(top10_csv)
        checks.append((f'{method}: top-10 table has 10 rows', len(top10) == 10))

        corr_sub = corr_results[corr_results['method'] == method]
        checks.append((f'{method}: 4 cutoff correlation rows', len(corr_sub) == len(CUTOFFS)))

        for _, row in corr_sub.iterrows():
            cutoff_num = int(str(row['cutoff']).replace('Top-', '').replace(',', ''))
            mask = (pair['rank_base'] <= cutoff_num) | (pair['rank_other'] <= cutoff_num)
            checks.append((
                f"{method}: N matches for {row['cutoff']}",
                int(row['n']) == int(mask.sum()),
            ))

    failed = [name for name, ok in checks if not ok]
    if failed:
        print('Validation failures detected:')
        for name in failed:
            print(f'  - {name}')
        raise RuntimeError(f'Validation failed ({len(failed)} checks).')

    print(f'All validation checks passed ({len(checks)} checks).')


def main():
    parser = argparse.ArgumentParser(description='SOTA H-Index vs Baseline Analysis')
    parser.add_argument('--baseline-data-dir', default='data/pubmed')
    parser.add_argument('--sota-data-dir', default='data/sota_hindex')
    parser.add_argument('--output-dir', default='analyses/sota_hindex_comparison')
    args = parser.parse_args()

    baseline_data_dir_arg = cast(str, args.baseline_data_dir)
    sota_data_dir_arg = cast(str, args.sota_data_dir)
    output_dir_arg = cast(str, args.output_dir)

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    baseline_data_dir = (os.path.join(project_root, baseline_data_dir_arg)
                         if not os.path.isabs(baseline_data_dir_arg) else baseline_data_dir_arg)
    sota_data_dir = (os.path.join(project_root, sota_data_dir_arg)
                     if not os.path.isabs(sota_data_dir_arg) else sota_data_dir_arg)
    output_dir = (os.path.join(project_root, output_dir_arg)
                  if not os.path.isabs(output_dir_arg) else output_dir_arg)

    plots_dir = os.path.join(output_dir, 'plots')
    tables_dir = os.path.join(output_dir, 'tables')

    for d in [plots_dir, tables_dir]:
        if os.path.isdir(d):
            shutil.rmtree(d)
        os.makedirs(d, exist_ok=True)

    print('=' * 80)
    print('SOTA (Katz/PageRank) vs Baseline H-Index Analysis')
    print(f'  Baseline data dir: {baseline_data_dir}')
    print(f'  SOTA data dir:     {sota_data_dir}')
    print(f'  Output directory:  {output_dir}')
    print(f'  Plots:             {plots_dir}')
    print(f'  Tables:            {tables_dir}')
    print(f'  Timestamp:         {datetime.now().isoformat()}')
    print('=' * 80)

    print('\nLoading data...')
    data = load_data(baseline_data_dir, sota_data_dir)

    corr_results = compute_rank_correlations(data, tables_dir)
    change_results = analyze_hindex_changes(data, tables_dir)
    beneficiary_dfs = analyze_transitivity_beneficiaries(data, tables_dir)
    create_plots(data, corr_results, change_results, beneficiary_dfs, plots_dir)
    write_summary_report(corr_results, beneficiary_dfs, output_dir)
    validate_results(data, corr_results, change_results, beneficiary_dfs, tables_dir)

    print('\n' + '=' * 80)
    print('ANALYSIS COMPLETE')
    print('=' * 80)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'ERROR: {exc}')
        sys.exit(1)

