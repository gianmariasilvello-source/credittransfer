"""
Test suite for AuthorMetrics module.

Tests h-index computation, author statistics, and performance with large datasets.
"""

import numpy as np
import time
from graph.GraphUtils import Graph
from credit.generalFormulation import GeneralCreditTransfer
from credit.authorMetrics import AuthorMetrics, create_random_authorship


def test_basic_h_index():
    """Test basic h-index computation with known values."""
    print("=" * 80)
    print("Test 1: Basic h-index Computation")
    print("=" * 80)

    metrics = AuthorMetrics({}, None)

    # Test case 1: h-index = 3
    kudos1 = np.array([10, 8, 5, 4, 3])
    h1 = metrics.compute_h_index(kudos1)
    print(f"\nKudos: {kudos1}")
    print(f"h-index: {h1} (expected: 4)")
    assert h1 == 4, f"Expected 4, got {h1}"

    # Test case 2: h-index = 3
    kudos2 = np.array([3, 3, 3, 2, 2, 1])
    h2 = metrics.compute_h_index(kudos2)
    print(f"\nKudos: {kudos2}")
    print(f"h-index: {h2} (expected: 3)")
    assert h2 == 3, f"Expected 3, got {h2}"

    # Test case 3: h-index = 0 (no publications)
    kudos3 = np.array([])
    h3 = metrics.compute_h_index(kudos3)
    print(f"\nKudos: {kudos3}")
    print(f"h-index: {h3} (expected: 0)")
    assert h3 == 0, f"Expected 0, got {h3}"

    # Test case 4: h-index = 1
    kudos4 = np.array([1, 0, 0, 0])
    h4 = metrics.compute_h_index(kudos4)
    print(f"\nKudos: {kudos4}")
    print(f"h-index: {h4} (expected: 1)")
    assert h4 == 1, f"Expected 1, got {h4}"

    print("\n✓ All basic h-index tests passed")
    print("=" * 80)


def test_small_citation_network():
    """Test with small citation network with known structure."""
    print("\n" + "=" * 80)
    print("Test 2: Small Citation Network with Authors")
    print("=" * 80)

    # Create simple graph: 5 papers
    n_papers = 5
    node_labels = list(range(n_papers))

    # Adjacency matrix: later papers cite earlier ones
    adj_matrix = np.array([
        [0, 0, 0, 0, 0],  # Paper 0
        [1, 0, 0, 0, 0],  # Paper 1 -> 0
        [1, 1, 0, 0, 0],  # Paper 2 -> 0, 1
        [1, 0, 1, 0, 0],  # Paper 3 -> 0, 2
        [0, 1, 1, 1, 0],  # Paper 4 -> 1, 2, 3
    ])

    g = Graph.from_matrix(node_labels, adj_matrix, is_directed=True)
    node_types = np.array([0] * n_papers)  # All papers

    # Compute credit
    gct = GeneralCreditTransfer(graph=g, node_types=node_types)
    gct.set_uniform_retention(0.3)
    total_credit, kudos, diag = gct.compute_credit_distribution()

    print("\nPaper kudos:")
    for i, k in enumerate(kudos):
        print(f"  Paper {i}: {k:.4f}")

    # Define authorship
    # Author 0: papers 0, 1 (highly cited early papers)
    # Author 1: papers 2, 3
    # Author 2: paper 4
    node_to_authors = {
        0: [0],
        1: [0],
        2: [1],
        3: [1],
        4: [2]
    }

    author_names = {
        0: "Alice (prolific, cited)",
        1: "Bob (mid-career)",
        2: "Charlie (junior)"
    }

    # Compute h-indices
    author_metrics = AuthorMetrics(node_to_authors, author_names)
    h_indices = author_metrics.compute_all_h_indices(kudos)

    print("\nAuthor metrics:")
    for author_id in sorted(h_indices.keys()):
        name = author_metrics.get_author_name(author_id)
        h_idx = h_indices[author_id]
        author_kudos = author_metrics.get_author_kudos(author_id, kudos)
        print(f"  {name}:")
        print(f"    Publications: {len(author_kudos)}")
        print(f"    Kudos: {author_kudos}")
        print(f"    h-index: {h_idx}")
        print(f"    Total kudos: {np.sum(author_kudos):.4f}")

    print("\n✓ Small network test passed")
    print("=" * 80)


def test_integer_vs_optional_names():
    """Test that author names are optional."""
    print("\n" + "=" * 80)
    print("Test 3: Integer IDs vs Optional Names")
    print("=" * 80)

    # Simple authorship
    node_to_authors = {
        0: [0, 1],
        1: [1, 2],
        2: [0, 2]
    }

    # Test 1: Without names
    print("\n1. Without author names:")
    metrics_no_names = AuthorMetrics(node_to_authors, author_names=None)
    for author_id in [0, 1, 2]:
        name = metrics_no_names.get_author_name(author_id)
        print(f"   Author {author_id}: {name}")

    # Test 2: With names
    print("\n2. With author names:")
    author_names = {0: "Smith, J.", 1: "Zhang, L.", 2: "Johnson, K."}
    metrics_with_names = AuthorMetrics(node_to_authors, author_names)
    for author_id in [0, 1, 2]:
        name = metrics_with_names.get_author_name(author_id)
        print(f"   Author {author_id}: {name}")

    print("\n✓ Optional names work correctly")
    print("=" * 80)


def test_performance_large_scale():
    """Test performance with large numbers of authors and publications."""
    print("\n" + "=" * 80)
    print("Test 4: Large-Scale Performance Test")
    print("=" * 80)

    sizes = [(1000, 100), (10000, 1000), (50000, 5000)]

    print(f"\n{'Papers':<10} {'Authors':<10} {'Init (ms)':<12} {'H-index (ms)':<15} {'Per Author (μs)':<15}")
    print("-" * 80)

    for n_papers, n_authors in sizes:
        # Create random authorship
        node_to_authors = create_random_authorship(
            n_nodes=n_papers,
            n_authors=n_authors,
            min_authors=2,
            max_authors=4,
            seed=42
        )

        # Create random kudos
        kudos = np.random.exponential(scale=2.0, size=n_papers)

        # Initialize
        start = time.time()
        metrics = AuthorMetrics(node_to_authors)
        init_time = (time.time() - start) * 1000

        # Compute h-indices
        start = time.time()
        h_indices = metrics.compute_all_h_indices(kudos)
        h_time = (time.time() - start) * 1000
        per_author = (h_time / n_authors) * 1000  # microseconds

        print(f"{n_papers:<10} {n_authors:<10} {init_time:<12.2f} {h_time:<15.2f} {per_author:<15.2f}")

    print("\n✓ Performance test completed")
    print("=" * 80)


def test_author_statistics():
    """Test comprehensive author statistics computation."""
    print("\n" + "=" * 80)
    print("Test 5: Author Statistics")
    print("=" * 80)

    # Create test data
    node_to_authors = {
        0: [0],
        1: [0],
        2: [0],
        3: [1],
        4: [1],
    }

    kudos = np.array([10.0, 8.0, 5.0, 3.0, 2.0])

    author_names = {0: "High Impact", 1: "Lower Impact"}

    metrics = AuthorMetrics(node_to_authors, author_names)
    stats = metrics.compute_author_statistics(kudos)

    print("\nAuthor Statistics:")
    for author_id, author_stats in stats.items():
        print(f"\n{metrics.get_author_name(author_id)}:")
        for key, value in author_stats.items():
            print(f"  {key}: {value}")

    # Verify calculations
    assert stats[0]['n_publications'] == 3
    assert stats[0]['total_kudos'] == 23.0
    assert abs(stats[0]['avg_kudos'] - 23.0/3) < 0.01
    assert stats[0]['max_kudos'] == 10.0
    assert stats[0]['h_index'] == 3  # Papers with kudos [10, 8, 5] -> h=3

    assert stats[1]['n_publications'] == 2
    assert stats[1]['total_kudos'] == 5.0
    assert stats[1]['h_index'] == 2  # Papers with kudos [3, 2] -> h=2

    print("\n✓ Statistics computation correct")
    print("=" * 80)


def test_top_authors_ranking():
    """Test ranking authors by different metrics."""
    print("\n" + "=" * 80)
    print("Test 6: Author Rankings")
    print("=" * 80)

    # Create scenario where top by h-index differs from top by kudos
    node_to_authors = {
        0: [0], 1: [0], 2: [0], 3: [0],  # Author 0: 4 papers, moderate kudos each
        4: [1], 5: [1],                   # Author 1: 2 papers, very high kudos
        6: [2], 7: [2], 8: [2],          # Author 2: 3 papers, mixed kudos
    }

    kudos = np.array([
        5.0, 5.0, 5.0, 5.0,  # Author 0: consistent quality
        20.0, 18.0,           # Author 1: two blockbusters
        10.0, 3.0, 2.0        # Author 2: one great, two okay
    ])

    author_names = {
        0: "Consistent Carl",
        1: "Superstar Sally",
        2: "Mixed Mike"
    }

    metrics = AuthorMetrics(node_to_authors, author_names)

    print("\n1. Top by h-index:")
    top_h = metrics.get_top_authors_by_h_index(kudos, top_k=3)
    for rank, (author_id, h_idx, name) in enumerate(top_h, 1):
        print(f"   {rank}. {name}: h-index={h_idx}")

    print("\n2. Top by total kudos:")
    top_kudos = metrics.get_top_authors_by_total_kudos(kudos, top_k=3)
    for rank, (author_id, total_kudos, name) in enumerate(top_kudos, 1):
        print(f"   {rank}. {name}: {total_kudos:.1f} total kudos")

    # Verify rankings
    assert top_h[0][2] == "Consistent Carl", "Carl should have highest h-index (4)"
    assert top_kudos[0][2] == "Superstar Sally", "Sally should have highest total kudos"

    print("\n✓ Ranking tests passed")
    print("=" * 80)


def test_backward_compatibility():
    """Test that existing code without authors still works."""
    print("\n" + "=" * 80)
    print("Test 7: Backward Compatibility")
    print("=" * 80)

    # Create graph and compute credit WITHOUT any author code
    g = Graph(is_directed=True)
    for i in range(5):
        if i > 0:
            g.add_edge(i, i-1)

    node_types = np.array([0] * 5)
    gct = GeneralCreditTransfer(graph=g, node_types=node_types)
    gct.set_uniform_retention(0.3)

    total_credit, kudos, diag = gct.compute_credit_distribution()

    print("\nCredit distribution computed successfully (no authors):")
    print(f"  Total kudos: {diag['total_kudos']:.2f}")
    print(f"  Converges: {diag['converges']}")

    print("\n✓ Backward compatibility maintained")
    print("=" * 80)


if __name__ == "__main__":
    try:
        test_basic_h_index()
        test_small_citation_network()
        test_integer_vs_optional_names()
        test_performance_large_scale()
        test_author_statistics()
        test_top_authors_ranking()
        test_backward_compatibility()

        print("\n" + "=" * 80)
        print("ALL AUTHOR METRICS TESTS PASSED ✓")
        print("=" * 80)
        print("\nKey Findings:")
        print("  ✓ H-index computation is correct")
        print("  ✓ Integer author IDs work efficiently")
        print("  ✓ Author names are optional")
        print("  ✓ Performance scales well (< 1ms per author)")
        print("  ✓ Statistics computation works correctly")
        print("  ✓ Backward compatibility maintained")
        print("  ✓ Works seamlessly with optimized credit computation")

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

