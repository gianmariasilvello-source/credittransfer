#!/usr/bin/env python3
"""
EXAMPLE: Custom Retention Strategies

This example shows how to customize the retention strategies
for synthetic graph ranking comparison experiments.

Copy this file and modify the 'strategies' list to test your own
retention rate combinations.

Usage:
    python3 experiments/example_custom_strategies.py config/synthetic_small.properties
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# IMPORTANT: This is a simplified example
# For full functionality, use: run_ranking_comparison.py
# This example just shows how to customize the strategies list

def main():
    """Show how to customize strategies and run the actual experiment."""
    import numpy as np

    print("="*100)
    print("CUSTOM RETENTION STRATEGIES - EXAMPLE TEMPLATE")
    print("="*100)

    print("\nThis file shows HOW to customize retention strategies.")
    print("The actual implementation is in: run_ranking_comparison.py")

    print("\n" + "="*100)
    print("EXAMPLE: Custom Strategies Definition")
    print("="*100)

    # ===================================================================
    # THIS IS HOW YOU DEFINE CUSTOM STRATEGIES
    # Copy this pattern to run_ranking_comparison.py (line ~550)
    # ===================================================================

    strategies = [
        # ALWAYS include the baseline (no transitivity)
        {
            'name': 'Direct Citations (1.0, 1.0, 1.0)',
            'rates': np.array([1.0, 1.0, 1.0])  # [papers, datasets, software]
        },

        # Example 1: Very conservative (minimal credit transfer)
        {
            'name': 'Conservative (0.9, 0.95, 0.95)',
            'rates': np.array([0.9, 0.95, 0.95])
        },

        # Example 2: Moderate - papers transfer more
        {
            'name': 'Papers Transfer (0.5, 0.8, 0.8)',
            'rates': np.array([0.5, 0.8, 0.8])
        },

        # Example 3: Aggressive - high credit transfer
        {
            'name': 'Aggressive (0.2, 0.4, 0.4)',
            'rates': np.array([0.2, 0.4, 0.4])
        },

        # Example 4: Only papers transfer (datasets/software keep all)
        {
            'name': 'Papers Only Transfer (0.3, 1.0, 1.0)',
            'rates': np.array([0.3, 1.0, 1.0])
        },

        # Example 5: Custom - your own combination
        # EDIT THESE VALUES to test your own strategy!
        {
            'name': 'My Custom Strategy (0.6, 0.7, 0.5)',
            'rates': np.array([0.6, 0.7, 0.5])  # <-- CHANGE THESE!
        },
    ]

    print(f"\nExample strategies defined: {len(strategies)}")
    for i, s in enumerate(strategies, 1):
        rates = s['rates']
        print(f"  {i}. {s['name']}")
        print(f"     Retention rates: Papers={rates[0]}, Datasets={rates[1]}, Software={rates[2]}")

    print("\n" + "="*100)
    print("TO USE THESE CUSTOM STRATEGIES:")
    print("="*100)

    print("\nMETHOD 1 (RECOMMENDED): Edit run_ranking_comparison.py")
    print("-" * 60)
    print("1. Open: experiments/run_ranking_comparison.py")
    print("2. Find the 'strategies' list (around line 550)")
    print("3. Copy the strategy definitions from above")
    print("4. Paste them into run_ranking_comparison.py")
    print("5. Run: python3 experiments/run_ranking_comparison.py config/synthetic_small.properties")

    print("\nMETHOD 2 (ALTERNATIVE): Create your own script")
    print("-" * 60)
    print("1. Copy: cp experiments/run_ranking_comparison.py experiments/my_custom.py")
    print("2. Edit: experiments/my_custom.py (line ~550)")
    print("3. Run: python3 experiments/my_custom.py config/synthetic_small.properties")

    print("\n" + "="*100)
    print("QUICK GUIDE: Retention Rate Values")
    print("="*100)
    print("\nFormat: np.array([papers, datasets, software])")
    print("\nValue meanings:")
    print("  1.0 = Keep 100%, transfer 0%   (no transitivity)")
    print("  0.8 = Keep 80%, transfer 20%")
    print("  0.5 = Keep 50%, transfer 50%")
    print("  0.2 = Keep 20%, transfer 80%")
    print("  0.0 = Keep 0%, transfer 100%   (maximum transitivity)")

    print("\n" + "="*100)
    print("WOULD YOU LIKE TO RUN THE ACTUAL EXPERIMENT NOW?")
    print("="*100)

    response = input("\nRun run_ranking_comparison.py with default strategies? [y/N]: ").strip().lower()

    if response == 'y':
        import subprocess

        config_file = 'config/synthetic_small.properties'
        if len(sys.argv) > 1:
            config_file = sys.argv[1]

        # Get the correct path to run_ranking_comparison.py
        script_dir = os.path.dirname(os.path.abspath(__file__))
        comparison_script = os.path.join(script_dir, 'run_ranking_comparison.py')

        # Make config path absolute too
        if not os.path.isabs(config_file):
            config_file = os.path.join(project_root, config_file)

        print(f"\nRunning: python3 {comparison_script} {config_file}")
        print("="*100 + "\n")

        # Run the actual experiment
        subprocess.run([
            sys.executable,
            comparison_script,
            config_file
        ])
    else:
        print("\nTo run with custom strategies:")
        print("  1. Edit experiments/run_ranking_comparison.py (line ~550)")
        print("  2. Modify the strategies list with your custom values")
        print("  3. Run: python3 experiments/run_ranking_comparison.py config/synthetic_small.properties")

    print("\n" + "="*100)
    print("For complete documentation, see: SYNTHETIC_GRAPHS_GUIDE.md")
    print("="*100 + "\n")


if __name__ == "__main__":
    main()

