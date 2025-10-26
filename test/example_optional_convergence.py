"""
Example demonstrating optional convergence checking.

This shows when and how to skip convergence checks for performance.
"""

import numpy as np
from graph.GraphUtils import Graph
from credit.generalFormulation import GeneralCreditTransfer
import time


def example_with_convergence_check():
    """Standard mode: Check convergence before solving"""
    print("=" * 70)
    print("Example 1: WITH Convergence Check (Default, Safer)")
    print("=" * 70)

    # Create a simple DAG
    g = Graph(is_directed=True)
    g.add_edge('a', 'b')
    g.add_edge('b', 'c')
    g.add_edge('a', 'c')

    gct = GeneralCreditTransfer(graph=g)
    gct.set_uniform_retention(0.3)

    start = time.time()
    total_credit, kudos, diagnostics = gct.compute_credit_distribution(check_convergence=True)
    elapsed = time.time() - start

    print(f"\nTime taken: {elapsed*1000:.2f} ms")
    print("\nDiagnostics:")
    for key, value in diagnostics.items():
        print(f"  {key}: {value}")

    print("\nResults:")
    results = gct.get_results_dict(total_credit, kudos)
    for node, values in results.items():
        print(f"  {node}: Credit={values['total_credit']:.4f}, Kudos={values['kudos']:.4f}")

    print("\n✓ Convergence verified - results are guaranteed correct")


def example_without_convergence_check():
    """Performance mode: Skip convergence check (use for known DAGs or large graphs)"""
    print("\n" + "=" * 70)
    print("Example 2: WITHOUT Convergence Check (Faster, Use with Caution)")
    print("=" * 70)

    # Same graph as above
    g = Graph(is_directed=True)
    g.add_edge('a', 'b')
    g.add_edge('b', 'c')
    g.add_edge('a', 'c')

    gct = GeneralCreditTransfer(graph=g)
    gct.set_uniform_retention(0.3)

    start = time.time()
    # Skip convergence check for performance
    total_credit, kudos, diagnostics = gct.compute_credit_distribution(check_convergence=False)
    elapsed = time.time() - start

    print(f"\nTime taken: {elapsed*1000:.2f} ms")
    print("\nDiagnostics:")
    for key, value in diagnostics.items():
        print(f"  {key}: {value}")

    print("\nResults:")
    results = gct.get_results_dict(total_credit, kudos)
    for node, values in results.items():
        print(f"  {node}: Credit={values['total_credit']:.4f}, Kudos={values['kudos']:.4f}")

    print("\n✓ Convergence check skipped - faster but assumes graph is well-formed")


def example_performance_comparison():
    """Compare performance for a larger graph"""
    print("\n" + "=" * 70)
    print("Example 3: Performance Comparison (Larger Graph)")
    print("=" * 70)

    # Create a larger DAG
    n = 100
    node_labels = [f'n{i}' for i in range(n)]

    # Create a chain with some cross-edges
    g = Graph(is_directed=True)
    for i in range(n-1):
        g.add_edge(node_labels[i], node_labels[i+1])
        if i % 5 == 0 and i + 5 < n:
            g.add_edge(node_labels[i], node_labels[i+5])

    gct = GeneralCreditTransfer(graph=g)
    gct.set_uniform_retention(0.2)

    # WITH convergence check
    print(f"\nGraph size: {n} nodes, {len(g.edges())} edges")

    start = time.time()
    total_credit1, kudos1, diag1 = gct.compute_credit_distribution(check_convergence=True)
    time_with = time.time() - start

    print(f"\nWITH convergence check:    {time_with*1000:.2f} ms")
    print(f"  Spectral radius: {diag1['spectral_radius']:.6f}")
    print(f"  Determinant: {diag1['determinant']:.6e}")

    # WITHOUT convergence check
    start = time.time()
    total_credit2, kudos2, diag2 = gct.compute_credit_distribution(check_convergence=False)
    time_without = time.time() - start

    print(f"\nWITHOUT convergence check: {time_without*1000:.2f} ms")
    print(f"  Convergence check skipped: {diag2.get('convergence_check_skipped', False)}")

    # Verify results are identical
    results_match = np.allclose(total_credit1, total_credit2) and np.allclose(kudos1, kudos2)

    speedup = time_with / time_without if time_without > 0 else float('inf')
    print(f"\nSpeedup: {speedup:.2f}x faster")
    print(f"Results match: {results_match}")
    print(f"\n✓ For large graphs, skipping convergence check can save significant time")


def example_when_to_skip():
    """Guidelines for when to skip convergence check"""
    print("\n" + "=" * 70)
    print("Guidelines: When to Skip Convergence Check")
    print("=" * 70)

    print("""
SKIP convergence check (check_convergence=False) when:
  ✓ Graph is a known DAG (Directed Acyclic Graph)
  ✓ Graph structure is guaranteed to converge (e.g., from validated data)
  ✓ Working with very large graphs (>10,000 nodes) where eigenvalue computation is slow
  ✓ Running multiple iterations with the same graph structure
  ✓ Performance is critical and you've validated convergence separately

ALWAYS CHECK convergence (check_convergence=True) when:
  ✗ First-time analysis of a new graph
  ✗ Graph may contain cycles
  ✗ Graph structure is user-generated or untrusted
  ✗ Debugging unexpected results
  ✗ Small to medium graphs (<10,000 nodes) where check is fast
  ✗ You need convergence diagnostics (spectral radius, determinant)

RISK of skipping:
  - If graph has problematic cycles, results may be incorrect or infinite
  - No warning will be given - you must trust your graph structure
  - Silent failures can propagate to downstream analysis

BEST PRACTICE:
  1. Always check convergence on first run
  2. If converges, can skip check on subsequent runs with same structure
  3. For production systems, implement structure validation upstream
  4. For very large graphs, consider sparse eigenvalue solvers
    """)


if __name__ == "__main__":
    example_with_convergence_check()
    example_without_convergence_check()
    example_performance_comparison()
    example_when_to_skip()

    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    print("""
Use check_convergence=True (default):  Safe, validates graph structure
Use check_convergence=False:           Fast, assumes graph is well-formed

For your papers/datasets use case:
  - If building from validated database: can skip after first validation
  - If user-generated citations: always check
  - For million-node graphs: consider skipping for performance
    """)

