# Synthetic Citation Graphs - Complete Guide

**Complete reference for generating realistic citation networks and running controlled ranking comparison experiments.**

## Table of Contents
1. [Quick Start (5 Minutes)](#quick-start-5-minutes)
2. [Graph Generation Parameters](#graph-generation-parameters)
3. [How to Customize Retention Strategies](#how-to-customize-retention-strategies)
4. [Retention Strategies Explained](#retention-strategies)
5. [Ranking Comparison Experiments](#ranking-comparison-experiments)
6. [Output Interpretation](#output-interpretation)
7. [Advanced Examples](#advanced-examples)
8. [Loading Graphs from Edgelist Files](#loading-graphs-from-edgelist-files)
9. [Presets](#presets)
10. [Best Practices](#best-practices)
11. [Troubleshooting](#troubleshooting)
12. [Quick Reference Card](#quick-reference-card)

---

### 1. Generate a Small Test Graph
```bash
python3 generators/generate_synthetic_graph.py config/synthetic_small.properties
```

### 2. Run Ranking Comparison with Baseline
```bash
python3 experiments/run_ranking_comparison.py config/synthetic_small.properties
```

This compares 6 retention strategies including the **Direct Citations baseline (no transitivity)**.

### 3. View Results
```bash
# See top-20 rankings side-by-side
# See Kendall's tau correlation matrix
# Results saved to: output/ranking_comparison/ranking_comparison_*.json
```

---

## Table of Contents
1. [Graph Generation Parameters](#graph-generation-parameters)
2. [Retention Strategies](#retention-strategies)
3. [Ranking Comparison Experiments](#ranking-comparison-experiments)
4. [Output Interpretation](#output-interpretation)
5. [Advanced Examples](#advanced-examples)

---

## Graph Generation Parameters

### Configuration File Structure

Edit `config/synthetic_citation.properties`:

```ini
[general]
seed = 42                        # Random seed for reproducibility

[graph]
n_nodes = 1000                   # Total number of nodes

[types]
num_types = 3                    # Number of node types
type_0_name = paper              # Type 0 name
type_0_proportion = 0.70         # Type 0 proportion (70%)
type_1_name = dataset
type_1_proportion = 0.25
type_2_name = software
type_2_proportion = 0.05

[density]
avg_out_degree = 15.0            # Average references per paper
density_variation = 0.2          # Variation in density (0.0-1.0)

[indegree]
powerlaw_exponent = 2.5          # Power-law exponent for citations
                                 # Lower (1.5-2.0) = more inequality
                                 # Higher (2.5-3.5) = more equal

[outdegree]
exp_lambda = 0.3                 # Exponential distribution parameter

[communities]
n_communities = 10               # Number of research subfields
within_community_prob = 0.6      # Prob of citing within community
between_community_prob = 0.4     # Prob of citing across communities

[structure]
transitivity_prob = 0.3          # Triangle formation probability
hierarchy_levels = 5             # Number of hierarchical levels
level_bias = 0.7                 # Upward citation bias strength

[citation_preferences]
# Type-specific citation patterns (type:weight pairs)
type_0_cites = 0:1.0, 1:0.3, 2:0.1
type_1_cites = 0:0.2, 1:1.0, 2:0.1
type_2_cites = 0:0.5, 1:0.5, 2:0.3

[authors]
n_authors = 300                  # Number of unique authors
avg_authors_per_node = 3.0       # Average authors per publication
productivity_exponent = 2.0      # Power-law for author productivity
                                 # Lower = few highly productive authors

[output]
output_dir = data/synthetic
output_prefix = synthetic_citation
```

### Parameter Details

#### Graph Size (`[graph]`)
- **`n_nodes`**: Total nodes in the graph
  - Small: 100 (fast testing)
  - Medium: 1,000 (realistic experiments)
  - Large: 10,000+ (large-scale testing)

#### Node Types (`[types]`)
- **`num_types`**: Number of different node types
  - Typical: 2-3 (papers, datasets, software)
- **`type_X_proportion`**: Fraction of nodes of each type
  - Must sum to 1.0
  - Example: 70% papers, 25% datasets, 5% software

#### Density (`[density]`)
- **`avg_out_degree`**: Average citations per paper
  - Typical range: 10-25
  - Higher = denser graph
- **`density_variation`**: How much density varies
  - 0.0 = uniform (all nodes cite same amount)
  - 1.0 = high variation

#### In-Degree Distribution (`[indegree]`)
- **`powerlaw_exponent`**: Controls citation inequality
  - **1.5-2.0**: High inequality (few superstar papers)
  - **2.5-3.0**: Moderate inequality (typical)
  - **3.0+**: Low inequality (more equal distribution)

#### Communities (`[communities]`)
- **`n_communities`**: Number of research subfields
  - Typical: 5-25
- **`within_community_prob`**: Probability of citing within same field
  - Higher (0.7-0.9) = isolated fields
  - Lower (0.3-0.5) = connected fields

#### Network Structure (`[structure]`)
- **`transitivity_prob`**: Triangle formation probability
  - If A→B and B→C, probability that A→C
  - Higher = more citation chains
  - Typical: 0.2-0.4
- **`hierarchy_levels`**: Stratification levels
  - Papers at higher levels are more foundational
- **`level_bias`**: Strength of upward citation preference
  - Higher = stronger bias toward foundational work

#### Authors (`[authors]`)
- **`n_authors`**: Total unique authors
  - Rule of thumb: 0.3-0.5 × n_nodes
- **`avg_authors_per_node`**: Co-authors per publication
  - Typical: 2-4
- **`productivity_exponent`**: Author productivity inequality
  - Lower (1.5) = few highly productive authors
  - Higher (2.5) = more equal productivity

---

## How to Customize Retention Strategies

### Quick Answer

**Edit:** `experiments/run_ranking_comparison.py`  
**Line:** ~550  
**Change:** The `strategies` list

### Step-by-Step Instructions

#### 1. Open the File
```bash
nano experiments/run_ranking_comparison.py
# Or use your preferred editor
```

#### 2. Find the Strategies Section (Line ~550)

Look for this code:
```python
strategies = [
    {
        'name': 'Direct Citations Only (1.0, 1.0, 1.0)',
        'rates': np.array([1.0, 1.0, 1.0])
    },
    {
        'name': 'High Retention (0.8, 0.9, 0.9)',
        'rates': np.array([0.8, 0.9, 0.9])
    },
    # ... more strategies
]
```

#### 3. Customize the Retention Rates

**Format:** `np.array([papers, datasets, software])`

**Example - Add your custom strategy:**
```python
strategies = [
    # Always keep the baseline!
    {
        'name': 'Direct Citations Only (1.0, 1.0, 1.0)',
        'rates': np.array([1.0, 1.0, 1.0])
    },
    # Your custom strategies
    {
        'name': 'Conservative (0.9, 0.95, 0.95)',
        'rates': np.array([0.9, 0.95, 0.95])
    },
    {
        'name': 'My Custom Strategy (0.6, 0.7, 0.5)',
        'rates': np.array([0.6, 0.7, 0.5])  # <-- Change these numbers!
    },
]
```

#### 4. Save and Run
```bash
python3 experiments/run_ranking_comparison.py config/synthetic_small.properties
```

### Understanding Retention Values

Each strategy has **3 values**: `[type_0, type_1, type_2]`
- **type_0** = papers (typically)
- **type_1** = datasets (typically)  
- **type_2** = software (typically)

**What the values mean:**

| Value | Keep | Transfer | Effect |
|-------|------|----------|--------|
| 1.0 | 100% | 0% | No transitivity (baseline) |
| 0.8 | 80% | 20% | Minimal transitivity |
| 0.5 | 50% | 50% | Moderate transitivity |
| 0.2 | 20% | 80% | High transitivity |
| 0.0 | 0% | 100% | Maximum transitivity |

**Examples:**
```python
np.array([1.0, 1.0, 1.0])  # Baseline - no credit transfer
np.array([0.5, 1.0, 1.0])  # Only papers transfer credit
np.array([0.2, 0.5, 0.7])  # Different rate for each type
np.array([0.5, 0.5, 0.5])  # All types transfer equally
np.array([0.0, 0.0, 0.0])  # Maximum credit flow
```

### Common Strategy Patterns

#### Test Incremental Retention (Papers Only)
```python
strategies = [
    {'name': 'Baseline (1.0, 1.0, 1.0)', 'rates': np.array([1.0, 1.0, 1.0])},
    {'name': 'Papers 90% (0.9, 1.0, 1.0)', 'rates': np.array([0.9, 1.0, 1.0])},
    {'name': 'Papers 70% (0.7, 1.0, 1.0)', 'rates': np.array([0.7, 1.0, 1.0])},
    {'name': 'Papers 50% (0.5, 1.0, 1.0)', 'rates': np.array([0.5, 1.0, 1.0])},
    {'name': 'Papers 30% (0.3, 1.0, 1.0)', 'rates': np.array([0.3, 1.0, 1.0])},
]
```
**Purpose:** See how paper retention affects rankings while keeping datasets/software constant.

#### Test Equal Retention Across Types
```python
strategies = [
    {'name': 'No Transfer (1.0, 1.0, 1.0)', 'rates': np.array([1.0, 1.0, 1.0])},
    {'name': 'Low Transfer (0.8, 0.8, 0.8)', 'rates': np.array([0.8, 0.8, 0.8])},
    {'name': 'Medium Transfer (0.5, 0.5, 0.5)', 'rates': np.array([0.5, 0.5, 0.5])},
    {'name': 'High Transfer (0.2, 0.2, 0.2)', 'rates': np.array([0.2, 0.2, 0.2])},
]
```
**Purpose:** Test transitivity effects when all types behave the same way.

#### Test Type-Specific Strategies
```python
strategies = [
    {'name': 'Baseline (1.0, 1.0, 1.0)', 'rates': np.array([1.0, 1.0, 1.0])},
    {'name': 'Papers Favored (0.9, 0.5, 0.5)', 'rates': np.array([0.9, 0.5, 0.5])},
    {'name': 'Datasets Favored (0.5, 0.9, 0.5)', 'rates': np.array([0.5, 0.9, 0.5])},
    {'name': 'Software Favored (0.5, 0.5, 0.9)', 'rates': np.array([0.5, 0.5, 0.9])},
]
```
**Purpose:** Compare which type benefits most from high retention.

### Alternative: Create Your Own Script

If you want to keep the original file unchanged:

```bash
# Copy the script
cp experiments/run_ranking_comparison.py experiments/my_custom_experiment.py

# Edit your copy
nano experiments/my_custom_experiment.py
# Go to line ~550 and modify strategies

# Run your custom version
python3 experiments/my_custom_experiment.py config/synthetic_small.properties
```

### Best Practices

✅ **ALWAYS include baseline** `np.array([1.0, 1.0, 1.0])` as first strategy  
✅ **Use descriptive names** that include the retention values  
✅ **Test 4-6 strategies** per experiment (not too many)  
✅ **Include extremes** for comparison (e.g., very high and very low retention)  
✅ **Document your choices** in strategy names and comments  
✅ **Set random seed** in config for reproducibility  

### Troubleshooting

**Q: Too many strategies make output unreadable**  
A: Keep it to 4-6 strategies. Run multiple experiments if needed.

**Q: Results look too similar across strategies**  
A: Increase the range - try [1.0, 0.5, 0.0] instead of [1.0, 0.9, 0.8]

**Q: Want to test many incremental values**  
A: Use a loop to generate strategies programmatically:
```python
strategies = [{'name': 'Baseline (1.0, 1.0, 1.0)', 'rates': np.array([1.0, 1.0, 1.0])}]
for retention in [0.8, 0.6, 0.4, 0.2]:
    strategies.append({
        'name': f'Papers {int(retention*100)}% ({retention}, 1.0, 1.0)',
        'rates': np.array([retention, 1.0, 1.0])
    })
```

---

## Retention Strategies

### Six Default Strategies

Every experiment compares these 6 strategies by default:

#### 1. ⭐ Direct Citations Only (1.0, 1.0, 1.0) - BASELINE
```ini
All types: 100% retention
```
- **No credit transfer** - pure baseline
- **No transitivity effects**
- Rankings = direct citations only
- h-kudos = h-credit = in-degree
- **Always include this as reference!**

#### 2. High Retention (0.8, 0.9, 0.9)
```ini
Papers: 80%, Datasets: 90%, Software: 90%
```
- Minimal credit transfer
- Close to Direct Citations baseline
- Small transitivity effects

#### 3. Medium Retention (0.5, 0.7, 0.7)
```ini
Papers: 50%, Datasets: 70%, Software: 70%
```
- Balanced approach
- Moderate transitive effects
- Good middle ground

#### 4. Low Retention (0.2, 0.5, 0.5)
```ini
Papers: 20%, Datasets: 50%, Software: 50%
```
- High credit transfer
- Strong transitive amplification
- Emphasizes citation chains

#### 5. Papers Only Retain (0.5, 1.0, 1.0)
```ini
Papers: 50%, Datasets: 100%, Software: 100%
```
- Tests paper-specific transfer
- Datasets/software keep all credit

#### 6. Datasets Only Retain (0.0, 0.9, 0.0)
```ini
Papers: 0%, Datasets: 90%, Software: 0%
```
- Extreme strategy
- Only datasets retain credit
- Maximum transitivity for papers

---

## Ranking Comparison Experiments

### Setup: Controlled Environment

The experiment uses the **same graph structure** for all retention strategies, ensuring fair comparison.

### Running the Experiment

```bash
# Basic usage
python3 experiments/run_ranking_comparison.py config/synthetic_small.properties

# Medium graph (recommended)
python3 experiments/run_ranking_comparison.py config/synthetic_citation.properties

# Large graph
python3 experiments/run_ranking_comparison.py config/synthetic_large.properties
```

### What It Does

1. **Generates one synthetic graph** with authors
2. **Runs 6 experiments** on the same graph with different retention rates
3. **Computes rankings** from both h-kudos and h-credit
4. **Calculates Kendall's tau** to measure ranking similarity
5. **Identifies volatile authors** whose ranks change most
6. **Saves results** to JSON for further analysis

### Output Sections

#### A. Side-by-Side Top-20 Rankings

Shows top 20 authors for each strategy in parallel:

```
TOP-20 RANKINGS COMPARISON - H-INDEX FROM KUDOS
================================================================
Rank | Direct Citations   | High Retention    | Low Retention
-----|-------------------|-------------------|------------------
1    | Author_0046 (h=4) | Author_0046 (h=4) | Author_0049 (h=3)
2    | Author_0024 (h=4) | Author_0024 (h=4) | Author_0009 (h=3)
3    | Author_0010 (h=4) | Author_0010 (h=4) | Author_0047 (h=2)
...
```

**What to look for:**
- Same authors across strategies? → Stable rankings
- Different authors? → Retention rates matter
- Compare with Direct Citations baseline

#### B. Kendall's Tau Correlation Matrix

Measures ranking similarity (values from -1.0 to 1.0):

```
KENDALL'S TAU CORRELATION MATRIX - H-INDEX FROM KUDOS
==================================================================
                      Direct   High     Medium   Low      Papers   Datasets
Direct Citations      1.000    0.952    0.831    0.598    0.876    0.387
High Retention        0.952    1.000    0.876    0.654    0.892    0.432
Medium Retention      0.831    0.876    1.000    0.789    0.945    0.521
Low Retention         0.598    0.654    0.789    1.000    0.768    0.678
Papers Only           0.876    0.892    0.945    0.768    1.000    0.501
Datasets Only         0.387    0.432    0.521    0.678    0.501    1.000
```

**Interpretation:**
- **τ > 0.9**: Very stable (retention choice barely matters)
- **τ = 0.7-0.9**: Stable (small ranking changes)
- **τ = 0.5-0.7**: Moderately stable (noticeable changes)
- **τ < 0.5**: Unstable (significant ranking differences)

**Key Insight:** Direct Citations shows τ=0.952 with High Retention → minimal transitivity effect!

#### C. Ranking Volatility Analysis

**Most Volatile** (rankings change dramatically):
```
Author           Mean Rank    Std Dev    Range      Min→Max
Author_0035      12.4         8.52       22         2→24
Author_0024      5.8          6.31       15         1→16
```

**Most Stable** (rankings stay consistent):
```
Author           Mean Rank    Std Dev    Range      Ranks Across Strategies
Author_0046      1.2          0.42       1          [1, 1, 2, 1, 1]
Author_0010      3.0          0.71       2          [3, 3, 3, 4, 3]
```

#### D. Summary Statistics

```
Average Kendall's Tau:
  H-index from kudos:        τ = 0.743 (MODERATELY STABLE)
  H-index from total credit: τ = 0.812 (VERY STABLE)

Interpretation:
  • Total credit rankings more stable than kudos rankings
  • Transitive effects smooth out variations
  • Direct Citations baseline highly correlated with high retention
```

---

## Output Interpretation

### Understanding the Results

When you run a ranking comparison experiment, you get four main types of output:

#### 1. Side-by-Side Top-20 Rankings

Shows top 20 authors for each strategy in parallel:

```
TOP-20 RANKINGS COMPARISON - H-INDEX FROM KUDOS
================================================================
Rank | Direct Citations   | High Retention    | Low Retention
-----|-------------------|-------------------|------------------
1    | Author_0046 (h=4) | Author_0046 (h=4) | Author_0049 (h=3)
2    | Author_0024 (h=4) | Author_0024 (h=4) | Author_0009 (h=3)
3    | Author_0010 (h=4) | Author_0010 (h=4) | Author_0047 (h=2)
...
```

**What to look for:**
- **Same authors across strategies?** → Rankings are stable
- **Different authors?** → Retention rates significantly affect rankings
- **Always compare with Direct Citations baseline** → Shows transitivity impact

#### 2. Kendall's Tau Correlation Matrix

Measures ranking similarity between all strategy pairs (values from -1.0 to 1.0):

```
KENDALL'S TAU CORRELATION MATRIX - H-INDEX FROM KUDOS
==================================================================
                      Direct   High     Medium   Low      Papers   Datasets
Direct Citations      1.000    0.952    0.831    0.598    0.876    0.387
High Retention        0.952    1.000    0.876    0.654    0.892    0.432
Medium Retention      0.831    0.876    1.000    0.789    0.945    0.521
Low Retention         0.598    0.654    0.789    1.000    0.768    0.678
Papers Only           0.876    0.892    0.945    0.768    1.000    0.501
Datasets Only         0.387    0.432    0.521    0.678    0.501    1.000
```

**Kendall's Tau Interpretation:**

| τ Value | Interpretation | Meaning |
|---------|----------------|---------|
| 0.9 - 1.0 | Very Stable | Retention choice barely affects rankings |
| 0.7 - 0.9 | Stable | Small ranking changes |
| 0.5 - 0.7 | Moderately Stable | Noticeable but not dramatic changes |
| 0.3 - 0.5 | Unstable | Significant ranking differences |
| 0.0 - 0.3 | Very Unstable | Rankings are very different |
| < 0.0 | Reversed | Rankings are negatively correlated |

**Key Patterns to Notice:**
- **Direct Citations vs High Retention:** Usually τ > 0.90 (very similar - minimal transitivity)
- **Direct Citations vs Medium Retention:** Usually τ ≈ 0.75-0.85 (moderately similar)
- **Direct Citations vs Low Retention:** Usually τ ≈ 0.50-0.65 (different - strong transitivity)
- **Direct Citations vs Extreme Strategies:** Usually τ < 0.50 (very different)

**What This Tells You:**
- High τ between strategies → Retention rate choice doesn't matter much
- Low τ between strategies → Retention rate choice significantly affects who gets recognized
- τ decreasing with lower retention → Transitivity effects increase

#### 3. Ranking Volatility Analysis

**Most Volatile Authors** (rankings change dramatically):
```
Author           Mean Rank    Std Dev    Range      Min→Max
Author_0035      12.4         8.52       22         2→24
Author_0024      5.8          6.31       15         1→16
```

**Most Stable Authors** (rankings stay consistent):
```
Author           Mean Rank    Std Dev    Range      Ranks Across Strategies
Author_0046      1.2          0.42       1          [1, 1, 2, 1, 1]
Author_0010      3.0          0.71       2          [3, 3, 3, 4, 3]
```

**Interpretation:**
- **High volatility (large std dev):** Author's rank is sensitive to retention rates
  - Benefits disproportionately from transitive credit
  - Network position matters more than direct citations
- **Low volatility (small std dev):** Author's rank is stable
  - Direct impact dominates
  - Core high-impact contributor regardless of strategy

#### 4. Summary Statistics

```
Average Kendall's Tau:
  H-index from kudos:        τ = 0.743 (MODERATELY STABLE)
  H-index from total credit: τ = 0.812 (VERY STABLE)

Interpretation:
  • Total credit rankings more stable than kudos rankings
  • Transitive effects smooth out variations in total credit
  • Kudos rankings more sensitive to retention rate changes
```

### Comparing H-Kudos vs H-Credit

**H-index from Kudos:**
- Based on **retained credit** only
- Measures **direct retained impact**
- More sensitive to retention rate changes
- Reflects what the author "keeps"

**H-index from Total Credit:**
- Based on **total credit** (retained + transitive)
- Measures **full influence** including network effects
- More stable across retention strategies
- Reflects author's total impact in the network

**When h-credit >> h-kudos:**
- Author benefits significantly from transitive credit
- Well-positioned in citation network
- Influence extends beyond direct citations
- Citation chains amplify their impact

**When h-kudos ≈ h-credit:**
- Author's impact is primarily direct
- Less dependent on citation chains
- Impact similar across all strategies
- Strong direct contributions

### Analyzing Results Against Baseline

**Always compare against Direct Citations (1.0, 1.0, 1.0):**

1. **High correlation (τ > 0.9) with baseline**
   - Transitivity adds little value
   - Rankings essentially determined by direct citations
   - Complex credit transfer may not be worth it

2. **Moderate correlation (τ = 0.6-0.8) with baseline**
   - Transitivity has noticeable but not dramatic effect
   - Some authors benefit from network position
   - May want to consider both metrics

3. **Low correlation (τ < 0.6) with baseline**
   - Transitivity significantly changes rankings
   - Network position very important
   - Different authors recognized with/without transitivity
   - Need to carefully choose retention strategy

### Decision Guide Based on Results

**If you see high Kendall's tau (>0.85) across all strategies:**
→ Retention rates don't matter much
→ Can choose based on other criteria (fairness, incentives, simplicity)
→ Consider using Direct Citations baseline for simplicity

**If you see low Kendall's tau (<0.6) across strategies:**
→ Retention rates critically affect rankings
→ Need careful consideration of which strategy is "fair"
→ May want to report multiple metrics
→ Document your retention rate choice thoroughly

**If h-credit rankings are much more stable than h-kudos:**
→ Total credit provides more robust metric
→ Less sensitive to parameter choices
→ May be better for practical use

**If many authors show high volatility:**
→ Network position is very important in this graph
→ Consider both direct and transitive metrics
→ Acknowledge that rankings are strategy-dependent

---

#### 1. Compare Against Baseline

**Always start with Direct Citations Only:**
- This is your ground truth
- No transitivity effects
- Pure direct citation counts

**Then compare other strategies:**
- High correlation (τ > 0.9) with baseline → transitivity adds little
- Low correlation (τ < 0.6) with baseline → transitivity significantly changes rankings

#### 2. Kendall's Tau Patterns

**What high τ means:**
- Rankings are similar
- Retention rate choice doesn't matter much
- Can choose based on other criteria (fairness, incentives)

**What low τ means:**
- Rankings are different
- Retention rate choice affects who gets recognized
- Need to carefully consider implications

#### 3. Volatility Analysis

**Volatile authors:**
- Rank changes dramatically across strategies
- Benefit disproportionately from transitive credit
- Network position matters more than direct citations

**Stable authors:**
- Rank stays consistent
- Direct impact dominates
- Core high-impact contributors

#### 4. H-Kudos vs H-Credit

**When h-credit >> h-kudos:**
- Author benefits from transitive credit
- Well-positioned in citation network
- Influence extends beyond direct citations

**When h-kudos ≈ h-credit:**
- Author's impact is primarily direct
- Less dependent on citation chains
- Impact similar across strategies

---

## Advanced Examples

### Example 1: Custom Retention Strategies

**Scenario:** Test fine-grained retention rates

```bash
# 1. Copy the experiment script
cp experiments/run_ranking_comparison.py experiments/custom_retention_test.py

# 2. Edit the strategies (around line 550)
```

```python
strategies = [
    # Always include baseline
    {'name': 'Baseline (1.0, 1.0, 1.0)', 
     'rates': np.array([1.0, 1.0, 1.0])},
    
    # Test incremental retention for papers
    {'name': 'Papers 90% (0.9, 1.0, 1.0)', 
     'rates': np.array([0.9, 1.0, 1.0])},
    {'name': 'Papers 70% (0.7, 1.0, 1.0)', 
     'rates': np.array([0.7, 1.0, 1.0])},
    {'name': 'Papers 50% (0.5, 1.0, 1.0)', 
     'rates': np.array([0.5, 1.0, 1.0])},
    {'name': 'Papers 30% (0.3, 1.0, 1.0)', 
     'rates': np.array([0.3, 1.0, 1.0])},
    {'name': 'Papers 10% (0.1, 1.0, 1.0)', 
     'rates': np.array([0.1, 1.0, 1.0])},
]
```

```bash
# 3. Run the custom experiment
python3 experiments/custom_retention_test.py config/synthetic_small.properties

# 4. Analyze: How does Kendall's tau change as paper retention decreases?
```

### Example 2: Testing Different Transitivity Levels

**Goal:** Measure how transitivity affects rankings

```bash
# Create 3 configs with different transitivity
# config/synthetic_low_trans.properties
[structure]
transitivity_prob = 0.1

# config/synthetic_med_trans.properties
[structure]
transitivity_prob = 0.3

# config/synthetic_high_trans.properties
[structure]
transitivity_prob = 0.6

# Run comparisons
python3 experiments/run_ranking_comparison.py config/synthetic_low_trans.properties
python3 experiments/run_ranking_comparison.py config/synthetic_med_trans.properties
python3 experiments/run_ranking_comparison.py config/synthetic_high_trans.properties

# Compare Kendall's tau between Direct Citations and Low Retention
# Higher transitivity → lower τ (more ranking change)
```

### Example 2: Community Structure Impact

**Goal:** Test how isolated communities affect rankings

```bash
# Isolated communities
[communities]
n_communities = 20
within_community_prob = 0.9
between_community_prob = 0.1

# Connected communities
[communities]
n_communities = 5
within_community_prob = 0.5
between_community_prob = 0.5

# Compare: Isolated communities → more stable rankings within fields
```

### Example 3: Author Productivity Analysis

**Goal:** Test impact of author productivity distribution

```bash
# Few superstar authors
[authors]
productivity_exponent = 1.5

# More equal productivity
[authors]
productivity_exponent = 2.5

# Compare h-index distributions
```

### Example 4: Controlled Transitivity Experiment

**Setup for publication:**

```bash
# 1. Generate graph with known properties
python3 generators/generate_synthetic_graph.py config/synthetic_citation.properties

# 2. Run ranking comparison (includes Direct Citations baseline)
python3 experiments/run_ranking_comparison.py config/synthetic_citation.properties

# 3. Analyze results
cat output/ranking_comparison/ranking_comparison_*.json

# 4. Report key metrics:
#    - Kendall's tau between Direct Citations and other strategies
#    - Number of authors changing rank by >10 positions
#    - Correlation between h-kudos and h-credit
```

---

## Presets

### Small Graph (Testing)
```ini
n_nodes = 100
n_authors = 50
n_communities = 5
avg_out_degree = 10.0
```
**Use for:** Quick tests, debugging

### Medium Graph (Experiments)
```ini
n_nodes = 1000
n_authors = 300
n_communities = 10
avg_out_degree = 15.0
```
**Use for:** Main experiments, analysis

### Large Graph (Scalability)
```ini
n_nodes = 10000
n_authors = 3000
n_communities = 25
avg_out_degree = 20.0
```
**Use for:** Performance testing, large-scale analysis

---

## Best Practices

### 1. Always Include Direct Citations Baseline
```python
strategies = [
    {'name': 'Direct Citations Only (1.0, 1.0, 1.0)', 'rates': np.array([1.0, 1.0, 1.0])},
    # ... other strategies
]
```

### 2. Set Random Seed for Reproducibility
```ini
[general]
seed = 42
```

### 3. Validate Graph Properties
```python
# Check metadata after generation
with open('data/synthetic/synthetic_citation_metadata.json') as f:
    metadata = json.load(f)
    print(f"Transitivity: {metadata['transitivity']:.3f}")
    print(f"Avg in-degree: {metadata['avg_in_degree']:.2f}")
```

### 4. Compare Multiple Metrics
- H-index from kudos (direct retained impact)
- H-index from total credit (including transitive)
- Direct citation counts
- Kendall's tau correlation

### 5. Document Your Configuration
Save a copy of your config file with results:
```bash
cp config/synthetic_citation.properties output/experiment_config_20251026.properties
```

---

## Loading Graphs from Edgelist Files

### Why Use Edgelist Format?

For large graphs (>10,000 nodes), edgelist files are:
- **Much smaller**: O(E) vs O(N²) for dense adjacency matrices
- **Faster to load**: No matrix parsing overhead
- **Memory efficient**: Only store actual edges
- **Git-friendly**: Stay under GitHub's 100MB file limit

### Edgelist File Format

Simple text format with one edge per line:

```
# Citation network edgelist
# source target
0 1
0 2
1 3
2 3
5 10
```

### Loading a Graph from Edgelist

**Python API:**

```python
from graph.GraphUtils import Graph

# Load a directed graph (default for citations)
graph = Graph.from_edgelist('data/synthetic_small/small_citation_edges.txt')

# Load an undirected graph
graph = Graph.from_edgelist('data/my_network_edges.txt', is_directed=False)

# Custom delimiter (e.g., comma-separated)
graph = Graph.from_edgelist('data/edges.csv', delimiter=',')

# Custom comment character
graph = Graph.from_edgelist('data/edges.txt', comment_char='%')
```

**Complete Example:**

```python
from graph.GraphUtils import Graph
from credit.generalFormulation import GeneralCreditTransfer
from credit.authorMetrics import AuthorMetrics
import numpy as np

# Load graph from edgelist
graph = Graph.from_edgelist('data/synthetic_small/small_citation_edges.txt')

# Load node types (same as before)
node_types = []
with open('data/synthetic_small/small_citation_node_types.txt', 'r') as f:
    for line in f:
        if line.startswith('#'):
            continue
        parts = line.strip().split()
        if len(parts) == 2:
            node_types.append(int(parts[1]))
node_types = np.array(node_types)

# Load authors (same as before)
node_to_authors = {}
with open('data/synthetic_small/small_citation_authors.txt', 'r') as f:
    for line in f:
        if line.startswith('#'):
            continue
        parts = line.strip().split()
        if len(parts) >= 2:
            node_id = int(parts[0])
            author_ids = [int(x) for x in parts[1:]]
            node_to_authors[node_id] = author_ids

# Run credit transfer
gct = GeneralCreditTransfer(graph, node_types=node_types, use_integer_indices=True)
gct.set_retention_by_type(np.array([0.5, 0.7, 0.7]))  # Your retention rates

total_credit, kudos, diagnostics = gct.compute_credit_distribution(
    check_convergence=False,
    use_sparse_eigensolver=True
)

# Compute author metrics
author_names = {i: f"Author_{i:04d}" for i in range(max(max(authors) for authors in node_to_authors.values()) + 1)}
metrics = AuthorMetrics(node_to_authors, author_names)
h_indices = metrics.compute_all_h_indices(kudos)

print(f"Loaded graph: {len(graph.nodes())} nodes, {len(graph.edges())} edges")
print(f"Top author: {max(h_indices.items(), key=lambda x: x[1])}")
```

### Complete Working Example

A full working example is available in `examples/load_edgelist_example.py`:

```bash
# Generate a test graph first
python3 generators/generate_synthetic_graph.py config/synthetic_small.properties

# Run the edgelist loading example
python3 examples/load_edgelist_example.py
```

This demonstrates:
- Loading graph from edgelist
- Loading node types and authors
- Running credit transfer analysis
- Computing author h-indices
- All from edgelist files (no dense adjacency matrix needed)

### Generating Edgelist Files

When generating synthetic graphs, you can skip the dense adjacency file to save time and space:

**In your config file:**
```ini
[output]
output_dir = data/synthetic_large
output_prefix = large_citation
save_dense_adjacency = false    # Skip dense matrix, only save edgelist
```

**What gets saved:**
- ✅ `large_citation_edges.txt` - Edgelist (always saved)
- ❌ `large_citation_adjacency.txt` - Dense matrix (skipped)
- ✅ `large_citation_node_types.txt` - Node types
- ✅ `large_citation_authors.txt` - Author mappings
- ✅ `large_citation_metadata.json` - Graph statistics

### Converting Between Formats

**From adjacency matrix to edgelist:**

```python
from graph.GraphUtils import Graph

# Load from adjacency matrix
nodes, matrix = load_adjacency_matrix('data/old_graph_adjacency.txt')
graph = Graph.from_matrix(nodes, matrix, is_directed=True)

# Save as edgelist
with open('data/graph_edges.txt', 'w') as f:
    f.write("# Converted from adjacency matrix\n")
    f.write("# source target\n")
    for src, tgt in graph.edges():
        f.write(f"{src} {tgt}\n")
```

**From edgelist to adjacency matrix:**

```python
from graph.GraphUtils import Graph

# Load from edgelist
graph = Graph.from_edgelist('data/graph_edges.txt')

# Convert to matrix
nodes, matrix = graph.to_matrix()

# Save matrix
with open('data/graph_adjacency.txt', 'w') as f:
    f.write("# Adjacency matrix\n")
    for row in matrix:
        f.write(' '.join(map(str, row)) + '\n')
```

### Performance Comparison

**For a graph with 100,000 nodes and 1,000,000 edges:**

| Format | File Size | Load Time | Memory |
|--------|-----------|-----------|--------|
| Dense Adjacency | ~10 GB | 120 sec | 40 GB |
| Edgelist | 20 MB | 2 sec | 80 MB |

**Recommendation:**
- **Small graphs (<1,000 nodes)**: Either format works
- **Medium graphs (1,000-10,000 nodes)**: Prefer edgelist
- **Large graphs (>10,000 nodes)**: Use edgelist only

---

## Troubleshooting

### Graph is too dense/sparse
Adjust `avg_out_degree`:
- Too sparse: Increase from 15 to 20-25
- Too dense: Decrease from 15 to 10-12

### Not enough transitivity
Increase `transitivity_prob`:
- From 0.3 to 0.5-0.6

### Rankings too similar across strategies
Lower `powerlaw_exponent`:
- From 2.5 to 1.8-2.0 (creates more inequality)

### Community structure not visible
Increase community separation:
- `within_community_prob` from 0.6 to 0.8
- `between_community_prob` from 0.4 to 0.2

---

## Quick Reference Card

### Customizing Retention Strategies

**File to edit:** `experiments/run_ranking_comparison.py` (line ~550)

**Template:**
```python
strategies = [
    {'name': 'Strategy Name (X, Y, Z)', 'rates': np.array([X, Y, Z])},
]
```

**Where:**
- `X` = papers retention (0.0-1.0)
- `Y` = datasets retention (0.0-1.0)
- `Z` = software retention (0.0-1.0)

**Common patterns:**
```python
# Baseline (always include!)
{'name': 'Baseline (1.0, 1.0, 1.0)', 'rates': np.array([1.0, 1.0, 1.0])}

# Papers only transfer
{'name': 'Papers Transfer (0.5, 1.0, 1.0)', 'rates': np.array([0.5, 1.0, 1.0])}

# Equal retention
{'name': 'Equal 50% (0.5, 0.5, 0.5)', 'rates': np.array([0.5, 0.5, 0.5])}

# Datasets favored
{'name': 'Datasets High (0.2, 0.9, 0.2)', 'rates': np.array([0.2, 0.9, 0.2])}

# Maximum transitivity
{'name': 'Max Transitivity (0.0, 0.0, 0.0)', 'rates': np.array([0.0, 0.0, 0.0])}
```

**Then run:**
```bash
python3 experiments/run_ranking_comparison.py config/synthetic_small.properties
```

---

## Summary

### Minimal Working Example

```bash
# 1. Generate graph (5 seconds)
python3 generators/generate_synthetic_graph.py config/synthetic_small.properties

# 2. Compare rankings (30 seconds)
python3 experiments/run_ranking_comparison.py config/synthetic_small.properties

# 3. Check results
ls -lh output/ranking_comparison/
```

### Key Takeaways

✅ **Always include Direct Citations baseline** (1.0, 1.0, 1.0)  
✅ **Use Kendall's tau** to measure ranking stability  
✅ **Compare h-kudos and h-credit** to understand transitivity  
✅ **Analyze volatility** to identify sensitive authors  
✅ **Set random seed** for reproducibility  

---

**Date:** October 26, 2025  
**Version:** 1.0  
**Status:** Complete and tested

