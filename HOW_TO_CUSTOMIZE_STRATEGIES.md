# How to Customize Retention Strategies

## Quick Answer

Edit **`experiments/run_ranking_comparison.py`** at **line ~550** and change the `strategies` list.

## Step-by-Step Instructions

### 1. Open the File
```bash
# Open in your editor
nano experiments/run_ranking_comparison.py
# Or
vim experiments/run_ranking_comparison.py
# Or use your IDE
```

### 2. Find the Strategies Section (around line 550)

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

### 3. Modify the Retention Rates

Change the numbers in `np.array([X, Y, Z])`:
- **X** = papers retention rate (0.0 to 1.0)
- **Y** = datasets retention rate (0.0 to 1.0)
- **Z** = software retention rate (0.0 to 1.0)

**Example - Add your custom strategy:**
```python
strategies = [
    # Always keep the baseline!
    {
        'name': 'Direct Citations Only (1.0, 1.0, 1.0)',
        'rates': np.array([1.0, 1.0, 1.0])
    },
    # Your custom strategy
    {
        'name': 'My Custom Strategy (0.6, 0.7, 0.5)',
        'rates': np.array([0.6, 0.7, 0.5])  # Change these numbers!
    },
]
```

### 4. Save and Run
```bash
python3 experiments/run_ranking_comparison.py config/synthetic_small.properties
```

## Understanding Retention Values

| Value | Meaning | Transitivity |
|-------|---------|-------------|
| 1.0 | Keep 100%, transfer 0% | None (baseline) |
| 0.8 | Keep 80%, transfer 20% | Low |
| 0.5 | Keep 50%, transfer 50% | Medium |
| 0.2 | Keep 20%, transfer 80% | High |
| 0.0 | Keep 0%, transfer 100% | Maximum |

## Common Strategy Patterns

### Test Incremental Changes
```python
strategies = [
    {'name': 'Baseline (1.0, 1.0, 1.0)', 'rates': np.array([1.0, 1.0, 1.0])},
    {'name': '80% (0.8, 1.0, 1.0)', 'rates': np.array([0.8, 1.0, 1.0])},
    {'name': '60% (0.6, 1.0, 1.0)', 'rates': np.array([0.6, 1.0, 1.0])},
    {'name': '40% (0.4, 1.0, 1.0)', 'rates': np.array([0.4, 1.0, 1.0])},
    {'name': '20% (0.2, 1.0, 1.0)', 'rates': np.array([0.2, 1.0, 1.0])},
]
```

### Test Equal Retention
```python
strategies = [
    {'name': 'No Transfer (1.0, 1.0, 1.0)', 'rates': np.array([1.0, 1.0, 1.0])},
    {'name': 'Low Transfer (0.8, 0.8, 0.8)', 'rates': np.array([0.8, 0.8, 0.8])},
    {'name': 'Med Transfer (0.5, 0.5, 0.5)', 'rates': np.array([0.5, 0.5, 0.5])},
    {'name': 'High Transfer (0.2, 0.2, 0.2)', 'rates': np.array([0.2, 0.2, 0.2])},
]
```

### Test Type-Specific Strategies
```python
strategies = [
    {'name': 'Baseline (1.0, 1.0, 1.0)', 'rates': np.array([1.0, 1.0, 1.0])},
    {'name': 'Papers Favored (0.9, 0.5, 0.5)', 'rates': np.array([0.9, 0.5, 0.5])},
    {'name': 'Datasets Favored (0.5, 0.9, 0.5)', 'rates': np.array([0.5, 0.9, 0.5])},
    {'name': 'Software Favored (0.5, 0.5, 0.9)', 'rates': np.array([0.5, 0.5, 0.9])},
]
```

## Best Practices

✅ **ALWAYS** include baseline: `np.array([1.0, 1.0, 1.0])`  
✅ Use descriptive names that show the retention values  
✅ Test 4-6 strategies per experiment (not too many)  
✅ Include at least one extreme strategy for comparison  
✅ Set random seed in config for reproducibility  

## Complete Example

**File:** `experiments/run_ranking_comparison.py` (line ~550)

**Before:**
```python
strategies = [
    {'name': 'Direct Citations Only (1.0, 1.0, 1.0)', 'rates': np.array([1.0, 1.0, 1.0])},
    {'name': 'High Retention (0.8, 0.9, 0.9)', 'rates': np.array([0.8, 0.9, 0.9])},
    {'name': 'Medium Retention (0.5, 0.7, 0.7)', 'rates': np.array([0.5, 0.7, 0.7])},
    # etc...
]
```

**After (with your custom strategies):**
```python
strategies = [
    # Baseline - always include!
    {'name': 'No Transitivity (1.0, 1.0, 1.0)', 'rates': np.array([1.0, 1.0, 1.0])},
    
    # Your custom strategies
    {'name': 'Conservative (0.9, 0.95, 0.95)', 'rates': np.array([0.9, 0.95, 0.95])},
    {'name': 'Moderate (0.5, 0.7, 0.7)', 'rates': np.array([0.5, 0.7, 0.7])},
    {'name': 'Aggressive (0.2, 0.4, 0.4)', 'rates': np.array([0.2, 0.4, 0.4])},
    {'name': 'Papers Only (0.3, 1.0, 1.0)', 'rates': np.array([0.3, 1.0, 1.0])},
]
```

**Run:**
```bash
python3 experiments/run_ranking_comparison.py config/synthetic_small.properties
```

## Alternative: Create Your Own Script

If you want to keep the original intact:

```bash
# 1. Copy the script
cp experiments/run_ranking_comparison.py experiments/my_custom_experiment.py

# 2. Edit your copy (line ~550)
nano experiments/my_custom_experiment.py

# 3. Run your custom version
python3 experiments/my_custom_experiment.py config/synthetic_small.properties
```

## Troubleshooting

**Error: "No section: 'graph'"**
- Make sure you're using a valid config file (e.g., `config/synthetic_small.properties`)

**Too many/few strategies**
- 4-6 strategies is optimal for comparison
- More than 8 makes the output hard to read

**Results look strange**
- Always include baseline (1.0, 1.0, 1.0) for reference
- Check that values are between 0.0 and 1.0

---

**For more details, see:** [SYNTHETIC_GRAPHS_GUIDE.md](SYNTHETIC_GRAPHS_GUIDE.md)

