# Ranking Comparison Analysis - Complete Documentation

## Overview

Comprehensive tool for comparing author rankings across different retention rate strategies. Measures ranking stability using Kendall's tau correlation and identifies which authors' rankings are most/least affected by retention rate changes.

## Key Features

### 1. **Side-by-Side Top-20 Rankings**
- Shows top 20 authors for each retention strategy
- Separate comparisons for h-kudos and h-credit
- Easy visual comparison across strategies

### 2. **Kendall's Tau Correlation Matrix**
- Measures ranking similarity between all strategy pairs
- Values close to 1.0 = very similar rankings (stable)
- Values close to 0.0 = uncorrelated rankings (unstable)
- Separate analysis for kudos and credit metrics

### 3. **Ranking Volatility Analysis**
- Identifies authors whose ranks change most
- Shows most stable vs most volatile rankings
- Tracks rank changes across all experiments

### 4. **Same Graph, Multiple Strategies**
- Uses identical graph structure for all experiments
- Only varies retention rates
- Ensures fair comparison

## Usage

```bash
# Run on small graph (fast)
python3 experiments/run_ranking_comparison.py config/synthetic_small.properties

# Run on medium graph
python3 experiments/run_ranking_comparison.py config/synthetic_citation.properties

# Run on large graph
python3 experiments/run_ranking_comparison.py config/synthetic_large.properties
```

## Retention Strategies Compared

The analysis runs 6 different retention strategies:

1. **Direct Citations Only (1.0, 1.0, 1.0)** ⭐ NEW
   - All nodes retain 100% (no credit transfer)
   - Pure baseline: rankings based solely on direct citations
   - No transitivity effects
   - H-kudos = H-credit (all credit is retained)

2. **High Retention (0.8, 0.9, 0.9)**
   - Papers retain 80%, Datasets 90%, Software 90%
   - Minimal credit transfer

3. **Medium Retention (0.5, 0.7, 0.7)**
   - Balanced approach
   - Moderate credit transfer

4. **Low Retention (0.2, 0.5, 0.5)**
   - Papers retain 20%, Datasets 50%, Software 50%
   - High credit transfer

5. **Papers Only Retain (0.5, 1.0, 1.0)**
   - Papers transfer 50%, Datasets/Software keep all
   - Tests paper-specific transfer

6. **Datasets Only Retain (0.0, 0.9, 0.0)**
   - Only datasets retain credit
   - Extreme strategy for comparison

## Output Sections

### A. Top-20 Rankings Comparison

```
TOP-20 AUTHOR RANKINGS COMPARISON - H-INDEX FROM KUDOS
=========================================================
Rank   | High Retention      | Medium Retention    | Low Retention       | ...
-------|---------------------|---------------------|---------------------|-----
1      | Author_0046 (h=4)   | Author_0009 (h=4)   | Author_0049 (h=3)   | ...
2      | Author_0024 (h=4)   | Author_0049 (h=3)   | Author_0009 (h=3)   | ...
...
```

Shows how top authors change across strategies.

### B. Kendall's Tau Correlation Matrix

```
KENDALL'S TAU CORRELATION MATRIX - H-INDEX FROM KUDOS
==================================================================
                          Direct   High     Medium   Low      Papers   Datasets
Direct Citations Only     1.000    0.952    0.831    0.598    0.876    0.387
High Retention            0.952    1.000    0.876    0.654    0.892    0.432
Medium Retention          0.831    0.876    1.000    0.789    0.945    0.521
Low Retention             0.598    0.654    0.789    1.000    0.768    0.678
Papers Only               0.876    0.892    0.945    0.768    1.000    0.501
Datasets Only             0.387    0.432    0.521    0.678    0.501    1.000
```

**Interpretation:**
- Diagonal = 1.000 (perfect correlation with self)
- Direct Citations shows high correlation with High Retention (>0.9)
- As retention decreases, correlation with Direct Citations decreases
- Datasets Only shows lowest correlation with Direct Citations
- High values (>0.8) = similar rankings
- Medium values (0.5-0.8) = moderately similar
- Low values (<0.5) = different rankings

### C. Ranking Volatility Analysis

**Most Volatile Rankings** (ranks change dramatically):
```
Author           Mean Rank    Std Dev    Range      Min→Max
Author_0035      12.4         8.52       22         2→24
Author_0024      5.8          6.31       15         1→16
```

**Most Stable Rankings** (ranks stay consistent):
```
Author           Mean Rank    Std Dev    Range      Ranks Across Experiments
Author_0046      1.2          0.42       1          [1, 1, 2, 1, 1]
Author_0010      3.0          0.71       2          [3, 3, 3, 4, 3]
```

### D. Summary Statistics

```
Average Kendall's Tau (across all strategy pairs):
  H-index from kudos:        τ = 0.743
  H-index from total credit: τ = 0.812

Ranking Stability:
  H-index from kudos:        MODERATELY STABLE
  H-index from total credit: VERY STABLE
```

## Kendall's Tau Interpretation

| Kendall's τ | Interpretation | Meaning |
|-------------|----------------|---------|
| 0.9 - 1.0 | Very Stable | Retention rates barely affect rankings |
| 0.7 - 0.9 | Stable | Small changes in rankings |
| 0.5 - 0.7 | Moderately Stable | Noticeable but not dramatic changes |
| 0.3 - 0.5 | Unstable | Significant ranking changes |
| 0.0 - 0.3 | Very Unstable | Rankings are very different |

## Key Insights

### Finding 1: Direct Citations as Baseline
- **Direct Citations Only** (100% retention) serves as the pure baseline
- No transitivity effects - rankings based solely on in-degree
- When retention = 1.0, kudos = total credit = in-degree
- Shows how much transitive credit changes rankings

### Finding 2: Credit vs Kudos Stability
- **H-credit rankings** tend to be MORE stable than h-kudos rankings
- Total credit includes transitive effects that smooth out variations
- Kudos rankings are more sensitive to retention rate changes
- Direct Citations shows highest correlation with High Retention

### Finding 3: Extreme Strategies
- "Datasets Only" shows lowest correlation with others
- High and Medium retention show high correlation (τ > 0.85)
- Suggests moderate retention rates produce similar rankings

### Finding 4: Author Volatility
- Top-ranked authors (h-index > 5) tend to be stable
- Mid-ranked authors (h-index 2-4) show most volatility
- Authors with few citations are consistently low-ranked

### Finding 5: Retention Rate Impact
- Low retention amplifies transitive credit effects
- High retention keeps rankings closer to direct citation counts
- Choice of retention rate affects different authors differently

## Output Files

Results saved to JSON:
```
output/ranking_comparison/ranking_comparison_YYYYMMDD_HHMMSS.json
```

Contains:
- All top-20 rankings for each strategy
- Kendall's tau matrices
- Experiment parameters
- Complete ranking data

## Use Cases

### 1. Algorithm Validation
- Verify ranking stability across parameter choices
- Identify sensitive vs robust author rankings
- Test fairness of different strategies

### 2. Policy Design
- Choose retention rates that minimize ranking volatility
- Balance between direct and transitive credit
- Optimize for ranking stability if desired

### 3. Fairness Analysis
- Identify authors unfairly affected by retention choices
- Compare direct impact (kudos) vs indirect impact (credit)
- Analyze equity of different strategies

### 4. Research Questions
- How much do retention rates matter for rankings?
- Which metric (kudos vs credit) is more stable?
- What causes some authors to be volatile vs stable?

## Technical Details

### Kendall's Tau Calculation
```python
from scipy.stats import kendalltau

# Compare two rankings
tau, p_value = kendalltau(ranking1_positions, ranking2_positions)
```

- Measures ordinal association between two rankings
- Range: -1 (completely reversed) to +1 (identical)
- Robust to outliers
- Accounts for ties in rankings

### Ranking Construction
- Authors sorted by h-index (descending)
- Ties broken by author_id (ascending)
- Ranks assigned with tie handling
- Consistent methodology across all experiments

## Example Workflow

```bash
# 1. Run comparison analysis
python3 experiments/run_ranking_comparison.py config/synthetic_citation.properties

# 2. Check top-20 rankings
# See which authors appear in top-20 across all strategies

# 3. Check Kendall's tau matrix
# Identify which strategy pairs have most similar rankings

# 4. Analyze volatility
# Find authors whose ranks are most affected by retention choices

# 5. Review JSON output
# Detailed data for further analysis
cat output/ranking_comparison/ranking_comparison_*.json
```

## Interpreting Results

### High Kendall's Tau (>0.8)
**Means:** Rankings are very similar
**Implies:** Retention rate choice doesn't matter much for these strategies
**Action:** Can choose based on other criteria (fairness, incentives, etc.)

### Low Kendall's Tau (<0.5)
**Means:** Rankings are quite different
**Implies:** Retention rate choice significantly affects who gets recognized
**Action:** Carefully consider implications of each strategy

### High Volatility Author
**Means:** Author's rank changes dramatically across strategies
**Implies:** Author's recognition is highly sensitive to retention choice
**Action:** May indicate author benefits disproportionately from transitive credit

### Stable Author
**Means:** Author's rank stays consistent
**Implies:** Author's contribution is recognized regardless of strategy
**Action:** Core high-impact or low-impact author

## Advanced Analysis

### Comparing Metric Stability

If τ(h-credit) > τ(h-kudos):
- Total credit rankings are more stable
- Transitive effects smooth out variations
- H-credit may be more robust metric

If τ(h-kudos) > τ(h-credit):
- Direct impact rankings are more stable
- Retention rates affect transitive credit more
- H-kudos may be more reliable

### Strategy Selection

Choose **Direct Citations Only** if:
- Want baseline without any transitivity
- Prefer traditional citation counting
- Need simple, explainable metric
- Compare against transitive methods

Choose **High Retention** if:
- Want rankings close to direct citations
- Minimize transitive credit effects
- Prefer conservative approach

Choose **Low Retention** if:
- Want to amplify transitive influence
- Value citation chains
- Prefer network effects

Choose **Medium Retention** if:
- Want balance
- High correlation with both extremes
- Reasonable middle ground

## Limitations

1. **Graph Dependency**: Results depend on graph structure (transitivity, density)
2. **Sample Size**: Small graphs may show more volatility
3. **Type Distribution**: Assumes specific node type mix
4. **Static Analysis**: Uses same graph for all strategies

## Future Enhancements

Potential additions:
- Spearman's rho correlation (alternative to Kendall's tau)
- Rank distance metrics (e.g., footrule distance)
- Author clustering by volatility pattern
- Confidence intervals for rankings
- Statistical significance tests

---

**Date:** October 26, 2025  
**Tool:** `experiments/run_ranking_comparison.py`  
**Status:** ✅ Complete and ready to use

