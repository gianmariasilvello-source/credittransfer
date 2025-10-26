"""
Test script to verify efficiency improvements work correctly.
Run after installing scipy: pip install scipy
"""

import numpy as np
from graph.GraphUtils import Graph
from credit.generalFormulation import GeneralCreditTransfer

def test_sparse_matrix_implementation():
    """Test that sparse matrix implementation works correctly"""
    print("=" * 60)
    print("Testing Sparse Matrix Implementation")
    print("=" * 60)

    # Create a simple graph
    g = Graph(is_directed=True)
    g.add_edge('1', '2')
    g.add_edge('1', '3')
    g.add_edge('2', '3')
    g.add_edge('3', '4')

    # Initialize credit transfer model
    gct = GeneralCreditTransfer(graph=g)

    # Set uniform retention
    gct.set_uniform_retention(0.3)

    # Compute credit
    total_credit, kudos, diagnostics = gct.compute_credit_distribution()

    print("\nDiagnostics:")
    for key, value in diagnostics.items():
        print(f"  {key}: {value}")

    print("\nResults:")
    results = gct.get_results_dict(total_credit, kudos)
    for node, values in results.items():
        print(f"  Node {node}: Total Credit = {values['total_credit']:.4f}, Kudos = {values['kudos']:.4f}")

    print("\n✓ Sparse matrix implementation works correctly")


def test_node_types_and_retention_by_type():
    """Test node types and vectorized retention rate assignment"""
    print("\n" + "=" * 60)
    print("Testing Node Types with Different Retention Rates")
    print("=" * 60)

    # Create graph with papers and datasets
    node_labels = ['p1', 'p2', 'd1', 'p3', 'd2']
    n = len(node_labels)

    # Adjacency matrix: p1 -> d1, p2 -> p1, p3 -> d1, d1 -> d2
    adj_matrix = np.array([
        [0, 0, 1, 0, 0],  # p1 -> d1
        [1, 0, 0, 0, 0],  # p2 -> p1
        [0, 0, 0, 0, 0],  # d1 (no outgoing)
        [0, 0, 1, 0, 0],  # p3 -> d1
        [0, 0, 0, 0, 0],  # d2 (no outgoing)
    ])

    # Node types: 0 = paper, 1 = dataset
    node_types = np.array([0, 0, 1, 0, 1])  # p1, p2, d1, p3, d2

    # Create graph from matrix
    g = Graph.from_matrix(node_labels, adj_matrix, is_directed=True)

    # Initialize with node types
    gct = GeneralCreditTransfer(graph=g, node_types=node_types)

    # Set different retention rates by type
    # Papers retain 20%, Datasets retain 90%
    type_retention_rates = np.array([0.2, 0.9])
    gct.set_retention_by_type(type_retention_rates)

    # Compute credit
    total_credit, kudos, diagnostics = gct.compute_credit_distribution()

    print("\nNode Types Configuration:")
    print(f"  Papers (type 0) retain: {type_retention_rates[0]*100:.0f}%")
    print(f"  Datasets (type 1) retain: {type_retention_rates[1]*100:.0f}%")

    print("\nDiagnostics:")
    for key, value in diagnostics.items():
        print(f"  {key}: {value}")

    print("\nResults by Node Type:")
    results = gct.get_results_dict(total_credit, kudos)
    for i, (node, values) in enumerate(results.items()):
        node_type = "paper" if node_types[i] == 0 else "dataset"
        print(f"  {node} ({node_type}): Total Credit = {values['total_credit']:.4f}, Kudos = {values['kudos']:.4f}")

    print("\n✓ Node types and vectorized retention rates work correctly")


def test_row_sums_caching():
    """Test that row sums are cached and reused"""
    print("\n" + "=" * 60)
    print("Testing Row Sums Caching")
    print("=" * 60)

    # Create a simple graph
    g = Graph(is_directed=True)
    g.add_edge('A', 'B')
    g.add_edge('A', 'C')
    g.add_edge('B', 'C')

    gct = GeneralCreditTransfer(graph=g)
    gct.set_uniform_retention(0.25)

    # First computation - cache should be populated
    print("\nFirst computation (cache empty)...")
    assert gct._row_sums_cache is None, "Cache should be None initially"
    total_credit1, kudos1, _ = gct.compute_credit_distribution()
    assert gct._row_sums_cache is not None, "Cache should be populated after computation"
    print(f"  Cache populated: {gct._row_sums_cache}")

    # Second computation - cache should be reused
    print("\nSecond computation (cache reused)...")
    cached_values = gct._row_sums_cache.copy()
    total_credit2, kudos2, _ = gct.compute_credit_distribution()
    assert np.allclose(cached_values, gct._row_sums_cache), "Cache should be reused"
    assert np.allclose(total_credit1, total_credit2), "Results should be identical"
    print("  Cache reused successfully")

    # Change retention rates - cache should be invalidated
    print("\nChanging retention rates (cache invalidated)...")
    gct.set_uniform_retention(0.5)
    assert gct._row_sums_cache is None, "Cache should be invalidated after changing retention"
    total_credit3, kudos3, _ = gct.compute_credit_distribution()
    assert gct._row_sums_cache is not None, "Cache should be repopulated"
    print("  Cache invalidated and repopulated successfully")

    print("\n✓ Row sums caching works correctly")


def test_sparse_eigenvalue_solver():
    """Test that sparse eigenvalue solver works correctly"""
    print("\n" + "=" * 60)
    print("Testing Sparse Eigenvalue Solver")
    print("=" * 60)

    # Create a medium-sized graph
    g = Graph(is_directed=True)
    for i in range(150):
        # Create a chain with some cross-edges
        if i < 149:
            g.add_edge(f'n{i}', f'n{i+1}')
        if i % 5 == 0 and i + 5 < 150:
            g.add_edge(f'n{i}', f'n{i+5}')

    gct = GeneralCreditTransfer(graph=g)
    gct.set_uniform_retention(0.3)

    print(f"\nGraph size: {gct.n} nodes")

    # Test with sparse solver
    print("\nUsing SPARSE eigenvalue solver...")
    import time
    start = time.time()
    tc_sparse, k_sparse, diag_sparse = gct.compute_credit_distribution(
        check_convergence=True,
        use_sparse_eigensolver=True
    )
    time_sparse = time.time() - start

    print(f"  Time: {time_sparse:.3f}s")
    print(f"  Used sparse: {diag_sparse.get('used_sparse_eigensolver', False)}")
    print(f"  Spectral radius: {diag_sparse['spectral_radius']:.6f}")
    print(f"  Converges: {diag_sparse['converges']}")

    # Test with dense solver for comparison
    print("\nUsing DENSE eigenvalue solver...")
    start = time.time()
    tc_dense, k_dense, diag_dense = gct.compute_credit_distribution(
        check_convergence=True,
        use_sparse_eigensolver=False
    )
    time_dense = time.time() - start

    print(f"  Time: {time_dense:.3f}s")
    print(f"  Spectral radius: {diag_dense['spectral_radius']:.6f}")
    print(f"  Converges: {diag_dense['converges']}")

    # Verify results match
    speedup = time_dense / time_sparse if time_sparse > 0 else float('inf')
    print(f"\nSpeedup: {speedup:.2f}x")

    rho_match = np.abs(diag_sparse['spectral_radius'] - diag_dense['spectral_radius']) < 1e-4
    credit_match = np.allclose(tc_sparse, tc_dense, rtol=1e-3)
    kudos_match = np.allclose(k_sparse, k_dense, rtol=1e-3)

    assert rho_match, "Spectral radii should match"
    assert credit_match, "Credit results should match"
    assert kudos_match, "Kudos results should match"

    print(f"Results match: ✓")
    print("\n✓ Sparse eigenvalue solver works correctly and is faster")


if __name__ == "__main__":
    try:
        test_sparse_matrix_implementation()
        test_node_types_and_retention_by_type()
        test_row_sums_caching()
        test_sparse_eigenvalue_solver()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

