#!/bin/bash
# Test script for run_ranking_comparison_10K.py
# This verifies the config file can be found and loaded

echo "═══════════════════════════════════════════════════════════════════════════"
echo "  Testing run_ranking_comparison_10K.py Config Loading"
echo "═══════════════════════════════════════════════════════════════════════════"
echo ""

# Get to project root
cd "$(dirname "$0")/.."

echo "1. Checking config file exists..."
if [ -f "config/synthetic_10K.properties" ]; then
    echo "   ✓ config/synthetic_10K.properties found"
else
    echo "   ❌ config/synthetic_10K.properties NOT FOUND"
    exit 1
fi

echo ""
echo "2. Checking [graph] section in config..."
if grep -q "^\[graph\]" config/synthetic_10K.properties; then
    echo "   ✓ [graph] section found"
    echo "   Content:"
    grep -A 2 "^\[graph\]" config/synthetic_10K.properties | sed 's/^/     /'
else
    echo "   ❌ [graph] section NOT FOUND"
    exit 1
fi

echo ""
echo "3. Testing config parsing with Python..."
python3 << 'PYTHON'
import os
import sys
import configparser

config_file = 'config/synthetic_10K.properties'

if not os.path.exists(config_file):
    print(f"   ❌ File not found: {config_file}")
    sys.exit(1)

parser = configparser.ConfigParser()
files_read = parser.read(config_file)

if not files_read:
    print(f"   ❌ Failed to read config file")
    sys.exit(1)

print(f"   ✓ Config file parsed successfully")
print(f"   Sections: {parser.sections()}")

if 'graph' not in parser.sections():
    print(f"   ❌ [graph] section not found in parsed config")
    sys.exit(1)

n_nodes = parser.getint('graph', 'n_nodes')
print(f"   ✓ [graph] section accessible")
print(f"   n_nodes = {n_nodes}")
PYTHON

if [ $? -eq 0 ]; then
    echo ""
    echo "═══════════════════════════════════════════════════════════════════════════"
    echo "  ✓ ALL TESTS PASSED"
    echo "═══════════════════════════════════════════════════════════════════════════"
    echo ""
    echo "The config file is valid. You can now run:"
    echo "  python3 experiments/run_ranking_comparison_10K.py"
    echo ""
else
    echo ""
    echo "═══════════════════════════════════════════════════════════════════════════"
    echo "  ❌ TESTS FAILED"
    echo "═══════════════════════════════════════════════════════════════════════════"
    exit 1
fi

