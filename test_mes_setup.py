#!/usr/bin/env python3
"""
Test script to verify MES experiment setup is working correctly.
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

print("="*80)
print("MES EXPERIMENT SETUP VERIFICATION")
print("="*80)

# Test 1: Check source files exist
print("\n1. Checking source JSONL files...")
data_dir = os.path.join(project_root, 'source_graph_data', 'curated_MES')
required_files = ['authors.jsonl', 'datasets.jsonl', 'publications.jsonl',
                 'relations.jsonl', 'software.jsonl']

all_exist = True
for filename in required_files:
    filepath = os.path.join(data_dir, filename)
    exists = os.path.exists(filepath)
    status = "✓" if exists else "✗"
    print(f"  {status} {filename}")
    if not exists:
        all_exist = False

if not all_exist:
    print("\n✗ ERROR: Some source files are missing!")
    sys.exit(1)

# Test 2: Check if MESProcessor can be imported
print("\n2. Testing MESProcessor import...")
try:
    from dataprocessing.MESProcessor import MESDataParser
    print("  ✓ MESDataParser imported successfully")
except Exception as e:
    print(f"  ✗ Failed to import: {e}")
    sys.exit(1)

# Test 3: Check experiment scripts exist
print("\n3. Checking experiment scripts...")
exp_dir = os.path.join(project_root, 'experiments')
exp_scripts = ['prepare_mes_data.py', 'run_mes_experiment.py']

for script in exp_scripts:
    filepath = os.path.join(exp_dir, script)
    exists = os.path.exists(filepath)
    status = "✓" if exists else "✗"
    print(f"  {status} {script}")

# Test 4: Check config files exist
print("\n4. Checking configuration files...")
config_dir = os.path.join(project_root, 'config')
config_files = ['mes_experiment.properties',
                'mes_experiment_high_dataset.properties',
                'mes_experiment_paper_alltransit.properties']

for config in config_files:
    filepath = os.path.join(config_dir, config)
    exists = os.path.exists(filepath)
    status = "✓" if exists else "✗"
    print(f"  {status} {config}")

# Test 5: Check if data directory can be created
print("\n5. Testing data directory creation...")
mes_data_dir = os.path.join(project_root, 'data', 'mes_experiment')
try:
    os.makedirs(mes_data_dir, exist_ok=True)
    if os.path.exists(mes_data_dir):
        print(f"  ✓ Directory exists: {mes_data_dir}")
    else:
        print(f"  ✗ Failed to create directory")
except Exception as e:
    print(f"  ✗ Error: {e}")

# Test 6: Try parsing a small sample
print("\n6. Testing MES parser (sample)...")
try:
    import json

    # Load just a few records to test parsing
    with open(os.path.join(data_dir, 'publications.jsonl'), 'r') as f:
        pub_sample = json.loads(f.readline())

    with open(os.path.join(data_dir, 'authors.jsonl'), 'r') as f:
        auth_sample = json.loads(f.readline())

    print(f"  ✓ Sample publication ID: {pub_sample.get('id', 'N/A')}")
    print(f"  ✓ Sample author ID: {auth_sample.get('id', 'N/A')}")

except Exception as e:
    print(f"  ✗ Error reading samples: {e}")

print("\n" + "="*80)
print("VERIFICATION COMPLETE")
print("="*80)
print("\nNext steps:")
print("  1. Run: python3 experiments/prepare_mes_data.py")
print("  2. Run: python3 experiments/run_mes_experiment.py")
print("="*80 + "\n")

