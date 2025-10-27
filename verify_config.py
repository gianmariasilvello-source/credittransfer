#!/usr/bin/env python3
"""
Quick verification that run_ranking_comparison_10K.py can load its config.
Run this to diagnose config loading issues.
"""

import os
import sys

print("═" * 80)
print("CONFIG LOADING VERIFICATION")
print("═" * 80)

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

print(f"\n1. Project root: {project_root}")

# Check config file
config_file = os.path.join(project_root, 'config', 'synthetic_10K.properties')
print(f"2. Config file: {config_file}")
print(f"   Exists? {os.path.exists(config_file)}")

if not os.path.exists(config_file):
    print("\n❌ ERROR: Config file not found!")
    sys.exit(1)

# Try to parse it
print("\n3. Parsing config file...")
import configparser

parser = configparser.ConfigParser()
files_read = parser.read(config_file)

if not files_read:
    print("   ❌ ERROR: Failed to read config file")
    sys.exit(1)

print(f"   ✓ Successfully read config file")
print(f"   Sections found: {parser.sections()}")

# Check for [graph] section
if 'graph' not in parser.sections():
    print("\n❌ ERROR: [graph] section not found!")
    print(f"   Available sections: {parser.sections()}")
    sys.exit(1)

print(f"\n4. [graph] section:")
print(f"   ✓ Found [graph] section")
try:
    n_nodes = parser.getint('graph', 'n_nodes')
    print(f"   ✓ n_nodes = {n_nodes}")
except Exception as e:
    print(f"   ❌ ERROR reading n_nodes: {e}")
    sys.exit(1)

# Try to load the generator
print("\n5. Loading SyntheticCitationGraphGenerator...")
try:
    from generators.generate_synthetic_graph import SyntheticCitationGraphGenerator
    print("   ✓ Import successful")
except Exception as e:
    print(f"   ❌ ERROR importing: {e}")
    sys.exit(1)

# Try to instantiate it
print("\n6. Instantiating generator with config...")
try:
    generator = SyntheticCitationGraphGenerator(config_file)
    print("   ✓ Generator created successfully")
    print(f"   Config loaded:")
    print(f"     - n_nodes: {generator.config['n_nodes']}")
    print(f"     - num_types: {generator.config['num_types']}")
    print(f"     - type_names: {generator.config['type_names']}")
    print(f"     - n_authors: {generator.config['n_authors']}")
except Exception as e:
    print(f"   ❌ ERROR creating generator: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# All good!
print("\n" + "═" * 80)
print("✅ ALL CHECKS PASSED")
print("═" * 80)
print("\nThe config file is valid and the generator can load it successfully.")
print("\nYou can now run:")
print("  python3 experiments/run_ranking_comparison_10K.py")
print("═" * 80)

