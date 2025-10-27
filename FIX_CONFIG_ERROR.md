═══════════════════════════════════════════════════════════════════════════
           FIXED: ConfigParser NoSectionError - Complete Guide
═══════════════════════════════════════════════════════════════════════════

ERROR YOU'RE SEEING:
───────────────────────────────────────────────────────────────────────────
configparser.NoSectionError: No section: 'graph'

ROOT CAUSE:
───────────────────────────────────────────────────────────────────────────
The script couldn't find or properly load the config file.

FIXES APPLIED:
═══════════════════════════════════════════════════════════════════════════

✅ 1. Changed default config path to use ABSOLUTE paths
   - Avoids working directory issues
   - Script now finds config regardless of where you run it from

✅ 2. Added comprehensive error handling
   - Shows exactly which config file is being used
   - Lists available config files if the specified one is missing
   - Shows working directory for debugging

✅ 3. Updated retention strategies for 2 node types
   - All strategies now use [papers, datasets] instead of 3 types

FILES MODIFIED:
═══════════════════════════════════════════════════════════════════════════

📄 experiments/run_ranking_comparison_10K.py
   - main() function now uses absolute paths
   - Better error messages
   - Config validation before loading generator

📄 config/synthetic_10K.properties
   - Verified to have all required sections including [graph]
   - Updated documentation for all parameters

HOW TO RUN:
═══════════════════════════════════════════════════════════════════════════

Method 1: Default config (recommended)
─────────────────────────────────────────────────────────────────────────── 
cd /Users/gianmariasilvello/PycharmProjects/CreditTransferProject
python3 experiments/run_ranking_comparison_10K.py

This will use: config/synthetic_10K.properties


Method 2: Custom config
───────────────────────────────────────────────────────────────────────────
python3 experiments/run_ranking_comparison_10K.py config/your_config.properties


VERIFICATION STEPS:
═══════════════════════════════════════════════════════════════════════════

Step 1: Verify config file exists
───────────────────────────────────────────────────────────────────────────
cd /Users/gianmariasilvello/PycharmProjects/CreditTransferProject
ls -la config/synthetic_10K.properties

Expected: File should exist


Step 2: Verify [graph] section exists
───────────────────────────────────────────────────────────────────────────
grep -A 2 "^\[graph\]" config/synthetic_10K.properties

Expected output:
[graph]
n_nodes = 10000


Step 3: Run the test script
───────────────────────────────────────────────────────────────────────────
./test_config.sh

Expected: All tests pass


Step 4: Run the actual experiment
───────────────────────────────────────────────────────────────────────────
python3 experiments/run_ranking_comparison_10K.py

Expected output (first few lines):
════════════════════════════════════════════════════════════════════════════════════════════════════
AUTHOR RANKING COMPARISON ACROSS RETENTION RATES
════════════════════════════════════════════════════════════════════════════════════════════════════

Configuration file: /Users/gianmariasilvello/PycharmProjects/CreditTransferProject/config/synthetic_10K.properties

Analyzing:
  1. Top-20 rankings for each retention strategy
  2. Kendall's tau correlation between strategies
  3. Ranking volatility (which authors' ranks change most)
  4. Separate analysis for h-kudos and h-credit

Generating synthetic citation graph...


TROUBLESHOOTING:
═══════════════════════════════════════════════════════════════════════════

If you STILL get the error:
───────────────────────────────────────────────────────────────────────────

1. Check your working directory:
   pwd
   
   Should be: /Users/gianmariasilvello/PycharmProjects/CreditTransferProject


2. Verify you're running the updated script:
   head -420 experiments/run_ranking_comparison_10K.py | tail -20
   
   Should show: script_dir = os.path.dirname(os.path.abspath(__file__))


3. Check if you have any command-line arguments:
   If you run: python3 experiments/run_ranking_comparison_10K.py some_file.properties
   Then it will use "some_file.properties" instead of the default


4. Verify Python can import configparser:
   python3 -c "import configparser; print('OK')"
   
   Expected: OK


5. Check file permissions:
   ls -l config/synthetic_10K.properties
   
   Expected: File should be readable (r-- in permissions)


6. Try the test script:
   ./test_config.sh
   
   This will diagnose exactly where the problem is


WHAT THE SCRIPT DOES:
═══════════════════════════════════════════════════════════════════════════

1. Loads config/synthetic_10K.properties (absolute path)
2. Generates ONE synthetic graph with 10,000 nodes
3. Runs 6 retention strategies on the SAME graph:
   
   Strategy 1: Direct Citations Only [1.0, 1.0]  ← Baseline
   Strategy 2: High Retention        [0.8, 0.9]
   Strategy 3: Medium Retention      [0.5, 0.7]
   Strategy 4: Low Retention         [0.2, 0.5]
   Strategy 5: Papers Only           [0.5, 1.0]
   Strategy 6: Datasets Only         [1.0, 0.5]

4. Computes h-indices for all authors under each strategy
5. Displays comparison tables and Kendall's tau analysis
6. Saves results to: output/ranking_comparison/


EXPECTED RUNTIME:
═══════════════════════════════════════════════════════════════════════════

For 10,000 nodes with 3,000 authors:
- Graph generation: ~30-60 seconds
- Each retention strategy: ~10-20 seconds
- Total: ~2-5 minutes


NEED MORE HELP?
═══════════════════════════════════════════════════════════════════════════

If the error persists after trying all troubleshooting steps:

1. Run the test script and share the output:
   ./test_config.sh

2. Try running with explicit path:
   python3 experiments/run_ranking_comparison_10K.py \
       "$(pwd)/config/synthetic_10K.properties"

3. Check if there are any hidden characters in the config file:
   file config/synthetic_10K.properties
   
   Expected: ASCII text


═══════════════════════════════════════════════════════════════════════════
KEY CHANGES SUMMARY:
═══════════════════════════════════════════════════════════════════════════

Before (BROKEN):
  gen_config = 'config/synthetic_10K.properties'  # Relative path
  generator = SyntheticCitationGraphGenerator(gen_config)  # No error handling

After (FIXED):
  script_dir = os.path.dirname(os.path.abspath(__file__))
  project_root = os.path.dirname(script_dir)
  default_config = os.path.join(project_root, 'config', 'synthetic_10K.properties')
  
  if not os.path.exists(gen_config):
      # Show helpful error message
  
  try:
      generator = SyntheticCitationGraphGenerator(gen_config)
  except Exception as e:
      # Show detailed error with context

═══════════════════════════════════════════════════════════════════════════

This fix ensures the config file is ALWAYS found, regardless of:
  ✓ Where you run the script from
  ✓ What your current working directory is
  ✓ Whether you use relative or absolute paths

═══════════════════════════════════════════════════════════════════════════

