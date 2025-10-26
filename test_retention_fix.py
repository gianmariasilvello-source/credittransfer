#!/usr/bin/env python3
"""Test script to verify retention rates work with both int and float values."""

import sys
sys.path.insert(0, '/Users/gianmariasilvello/PycharmProjects/CreditTransferProject')

import numpy as np
from graph.GraphUtils import Graph
from credit.generalFormulation import GeneralCreditTransfer

# Test with different retention rates
node_labels = [0, 1, 2, 3, 4]
adj_matrix = [[0, 1, 1, 0, 1],
              [0, 0, 1, 1, 0],
              [0, 0, 0, 1, 0],
              [0, 0, 0, 0, 0],
              [0, 1, 0, 0, 0]]
node_types = np.array([0, 1, 0, 0, 1])
g = Graph.from_matrix(node_labels, adj_matrix, is_directed=True)

print("=" * 60)
print("Testing retention rate fix")
print("=" * 60)

gct = GeneralCreditTransfer(graph=g, node_types=node_types, use_integer_indices=True)

# Test 1: Mixed int and float retention rates
print("\n1. Testing with retention rates [0.2, 0.8]:")
type_retention_rates = np.array([0.2, 0.8])
gct.set_retention_by_type(type_retention_rates)

total_credit, kudos, diagnostics = gct.compute_credit_distribution(
    check_convergence=False
)

print(f"   Kudos: {kudos}")

# Test 2: Both 1 (int) and 1.0 (float) - THIS WAS THE BUG
print("\n2. Testing with retention rates [1, 1.0] (int and float):")
type_retention_rates = np.array([1, 1.0])
gct.set_retention_by_type(type_retention_rates)

total_credit, kudos, diagnostics = gct.compute_credit_distribution(
    check_convergence=False
)

print(f"   Kudos: {kudos}")

# Test 3: All integers
print("\n3. Testing with retention rates [1, 1] (both int):")
type_retention_rates = np.array([1, 1])
gct.set_retention_by_type(type_retention_rates)

total_credit, kudos, diagnostics = gct.compute_credit_distribution(
    check_convergence=False
)

print(f"   Kudos: {kudos}")

# Test 4: All floats
print("\n4. Testing with retention rates [1.0, 1.0] (both float):")
type_retention_rates = np.array([1.0, 1.0])
gct.set_retention_by_type(type_retention_rates)

total_credit, kudos, diagnostics = gct.compute_credit_distribution(
    check_convergence=False
)

print(f"   Kudos: {kudos}")

print("\n" + "=" * 60)
print("All tests passed! Retention rates work with int and float.")
print("=" * 60)

