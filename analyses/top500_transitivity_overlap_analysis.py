#!/usr/bin/env python3
"""Top-500 baseline-focused overlap analysis across transitivity retention rates."""

import os
import argparse
from typing import cast

import pandas as pd

COL_NAMES = ['author_id', 'h_index', 'total_kudos', 'num_publications', 'author_name']
RETENTION_FILES = {
    1.00: 'pkg24s4_1_author_hindices.txt',
    0.75: 'pkg24s4_0_75_author_hindices.txt',
    0.50: 'pkg24s4_0_5_author_hindices.txt',
    0.25: 'pkg24s4_0.25_author_hindices.txt',
}
BASE_RATE = 1.0
OTHER_RATES = [0.75, 0.50, 0.25]


def load_hindex(path: str) -> pd.DataFrame:
    df = pd.read_csv(
        path,
        comment='#',
        sep=r'\s+',
        names=COL_NAMES,
        dtype={
            'author_id': 'int64',
            'h_index': 'int32',
            'total_kudos': 'float64',
            'num_publications': 'int32',
            'author_name': 'string',
        },
    )
    df = df.drop(columns=['author_name'])
    df = df.sort_values('h_index', ascending=False, kind='mergesort').reset_index(drop=True)
    df['rank'] = df.index + 1
    return df.set_index('author_id')


def analyze_top500(project_root: str, data_dir: str, output_dir: str):
    data = {}
    for rate, fname in RETENTION_FILES.items():
        path = os.path.join(data_dir, fname)
        data[rate] = load_hindex(path)

    tables_dir = os.path.join(output_dir, 'tables')
    os.makedirs(tables_dir, exist_ok=True)

    baseline = data[BASE_RATE]
    baseline_top500_ids = set(baseline.index[baseline['rank'] <= 500])
    summary_rows = []

    for rate in OTHER_RATES:
        other = data[rate]
        other_top500_ids = set(other.index[other['rank'] <= 500])
        overlap_ids = baseline_top500_ids & other_top500_ids

        pair = baseline[['h_index', 'rank', 'num_publications']].rename(
            columns={'h_index': 'h_base', 'rank': 'rank_base', 'num_publications': 'pubs_base'}
        ).join(
            other[['h_index', 'rank']].rename(columns={'h_index': 'h_other', 'rank': 'rank_other'}),
            how='inner',
        )

        top = pair[pair['rank_base'] <= 500].copy()
        top['delta_h'] = top['h_other'] - top['h_base']
        top['delta_rank'] = top['rank_base'] - top['rank_other']

        rate_tag = f'{int(rate * 100):03d}'
        detail = top.sort_values('rank_base').reset_index().rename(columns={'index': 'author_id'})
        detail.to_csv(os.path.join(tables_dir, f'top500_baseline_detail_r{rate_tag}.csv'), index=False)

        overlap_detail = detail[detail['author_id'].isin(overlap_ids)].copy()
        overlap_detail.to_csv(os.path.join(tables_dir, f'top500_overlap_detail_r{rate_tag}.csv'), index=False)

        summary_rows.append({
            'target_rate': rate,
            'baseline_top500_count': 500,
            'baseline_top500_present_in_target': int(top.shape[0]),
            'target_top500_count': 500,
            'overlap_top500_count': int(len(overlap_ids)),
            'overlap_pct_of_baseline_top500': 100.0 * len(overlap_ids) / 500.0,
            'mean_delta_h_baseline_top500': float(top['delta_h'].mean()),
            'median_delta_h_baseline_top500': float(top['delta_h'].median()),
            'min_delta_h_baseline_top500': int(top['delta_h'].min()),
            'max_delta_h_baseline_top500': int(top['delta_h'].max()),
            'mean_delta_rank_baseline_top500': float(top['delta_rank'].mean()),
            'median_delta_rank_baseline_top500': float(top['delta_rank'].median()),
            'authors_moved_up_rank': int((top['delta_rank'] > 0).sum()),
            'authors_moved_down_rank': int((top['delta_rank'] < 0).sum()),
            'authors_same_rank': int((top['delta_rank'] == 0).sum()),
            'authors_gained_h': int((top['delta_h'] > 0).sum()),
            'authors_lost_h': int((top['delta_h'] < 0).sum()),
            'authors_same_h': int((top['delta_h'] == 0).sum()),
        })

    summary = pd.DataFrame(summary_rows)
    summary_csv = os.path.join(tables_dir, 'top500_baseline_summary_transitivity.csv')
    summary.to_csv(summary_csv, index=False)

    report_path = os.path.join(output_dir, 'top500_baseline_transitivity_analysis.txt')
    with open(report_path, 'w') as f:
        f.write('Top-500 Baseline-Centric Transitivity Comparison\n')
        f.write('===============================================\n\n')
        f.write('Definition:\n')
        f.write('- Baseline set: authors ranked <=500 at retention=1.00\n')
        f.write('- Overlap count: |Top500_r1.00 ∩ Top500_rX|\n\n')
        for row in summary_rows:
            f.write(f"Target rate: r={row['target_rate']:.2f}\n")
            f.write(f"  Overlap Top-500 count: {row['overlap_top500_count']} / 500 ({row['overlap_pct_of_baseline_top500']:.2f}%)\n")
            f.write(f"  Baseline Top-500 present in target file: {row['baseline_top500_present_in_target']}\n")
            f.write(f"  Mean delta_h (target - baseline): {row['mean_delta_h_baseline_top500']:.3f}\n")
            f.write(f"  Median delta_h: {row['median_delta_h_baseline_top500']:.3f}\n")
            f.write(f"  delta_h range: [{row['min_delta_h_baseline_top500']}, {row['max_delta_h_baseline_top500']}]\n")
            f.write(f"  Authors gained/lost/same h: {row['authors_gained_h']}/{row['authors_lost_h']}/{row['authors_same_h']}\n")
            f.write(f"  Mean delta_rank (positive means moved up): {row['mean_delta_rank_baseline_top500']:.3f}\n")
            f.write(f"  Median delta_rank: {row['median_delta_rank_baseline_top500']:.3f}\n")
            f.write(f"  Authors moved up/down/same rank: {row['authors_moved_up_rank']}/{row['authors_moved_down_rank']}/{row['authors_same_rank']}\n\n")

    print(summary.to_string(index=False))
    print(f'Wrote: {summary_csv}')
    print(f'Wrote: {report_path}')


def main():
    parser = argparse.ArgumentParser(description='Top-500 transitivity overlap analysis')
    parser.add_argument('--data-dir', default='data/pubmed')
    parser.add_argument('--output-dir', default='analyses/transitivity_top500_overlap')
    args = parser.parse_args()

    data_dir_arg = cast(str, args.data_dir)
    output_dir_arg = cast(str, args.output_dir)

    project_root = cast(str, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data_dir = cast(str, os.path.join(project_root, data_dir_arg) if not os.path.isabs(data_dir_arg) else data_dir_arg)
    output_dir = cast(str, os.path.join(project_root, output_dir_arg) if not os.path.isabs(output_dir_arg) else output_dir_arg)
    os.makedirs(output_dir, exist_ok=True)

    analyze_top500(project_root, data_dir, output_dir)


if __name__ == '__main__':
    main()

