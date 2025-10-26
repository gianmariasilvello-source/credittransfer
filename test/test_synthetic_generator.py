"""
Test Synthetic Citation Graph Generator

Verifies that the generator creates valid citation networks with expected properties.
"""

import sys
import os
import numpy as np

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from generators.generate_synthetic_graph import SyntheticCitationGraphGenerator


def test_small_graph():
    """Test generation of small graph."""
    print("\n" + "="*80)
    print("TEST: Small Synthetic Graph Generation")
    print("="*80)

    config_file = os.path.join(project_root, 'config', 'synthetic_small.properties')

    generator = SyntheticCitationGraphGenerator(config_file)
    graph, node_types, metadata = generator.generate()

    # Verify basic properties
    assert len(graph.nodes()) == 100, "Should have 100 nodes"
    assert len(graph.edges()) > 0, "Should have edges"

    # Verify DAG property (no back edges)
    edges = graph.edges()
    for source, target in edges:
        assert source > target, f"Back edge detected: {source} -> {target} (should be DAG)"

    # Verify node types
    assert len(node_types) == 100, "Should have type for each node"
    assert np.all(node_types >= 0) and np.all(node_types < 2), "Types should be 0 or 1"

    # Verify metadata
    assert metadata['n_nodes'] == 100
    assert metadata['n_edges'] > 0
    assert 0 <= metadata['transitivity'] <= 1

    print(f"✓ Generated {metadata['n_nodes']} nodes, {metadata['n_edges']} edges")
    print(f"✓ DAG property verified (all edges go from later to earlier nodes)")
    print(f"✓ Avg in-degree: {metadata['avg_in_degree']:.2f}")
    print(f"✓ Avg out-degree: {metadata['avg_out_degree']:.2f}")
    print(f"✓ Transitivity: {metadata['transitivity']:.3f}")
    print(f"✓ Type distribution: {metadata['type_distribution']}")

    print("\n✓ Small graph test PASSED")


def test_degree_distributions():
    """Test that degree distributions match expectations."""
    print("\n" + "="*80)
    print("TEST: Degree Distributions")
    print("="*80)

    config_file = os.path.join(project_root, 'config', 'synthetic_small.properties')

    generator = SyntheticCitationGraphGenerator(config_file)
    graph, node_types, metadata = generator.generate()

    # Compute degree distributions
    in_degrees = np.zeros(100)
    out_degrees = np.zeros(100)

    for source, target in graph.edges():
        out_degrees[source] += 1
        in_degrees[target] += 1

    # Check out-degree follows exponential-ish pattern (most nodes have similar out-degree)
    avg_out = np.mean(out_degrees)
    print(f"✓ Average out-degree: {avg_out:.2f}")

    # Check in-degree has variation (power-law means high variance)
    std_in = np.std(in_degrees)
    print(f"✓ In-degree std dev: {std_in:.2f} (high variance expected)")

    # Check max in-degree is significantly higher than average (power-law property)
    max_in = np.max(in_degrees)
    avg_in = np.mean(in_degrees)
    print(f"✓ Max in-degree: {max_in} (avg: {avg_in:.2f})")

    assert max_in > 2 * avg_in, "Power-law: max should be >> average"

    print("\n✓ Degree distribution test PASSED")


def test_community_structure():
    """Test that community structure is present."""
    print("\n" + "="*80)
    print("TEST: Community Structure")
    print("="*80)

    config_file = os.path.join(project_root, 'config', 'synthetic_small.properties')

    generator = SyntheticCitationGraphGenerator(config_file)

    # Access internal community assignments
    graph, node_types, metadata = generator.generate()

    # Check that community mechanism was used
    assert metadata['edges_by_mechanism']['community'] > 0, "Should have community-based edges"

    print(f"✓ Community edges: {metadata['edges_by_mechanism']['community']}")
    print(f"✓ Preferential edges: {metadata['edges_by_mechanism']['preferential']}")
    print(f"✓ Transitive edges: {metadata['edges_by_mechanism']['transitive']}")

    print("\n✓ Community structure test PASSED")


def test_serialization():
    """Test that graphs can be saved and loaded."""
    print("\n" + "="*80)
    print("TEST: Serialization")
    print("="*80)

    config_file = os.path.join(project_root, 'config', 'synthetic_small.properties')

    generator = SyntheticCitationGraphGenerator(config_file)
    graph, node_types, metadata = generator.generate()

    # Save to files
    generator.save_to_files(graph, node_types, metadata)

    # Verify files exist
    output_dir = generator.config['output_dir']
    prefix = generator.config['output_prefix']

    files = [
        f'{prefix}_adjacency.txt',
        f'{prefix}_node_types.txt',
        f'{prefix}_node_labels.txt',
        f'{prefix}_metadata.json'
    ]

    for filename in files:
        filepath = os.path.join(output_dir, filename)
        assert os.path.exists(filepath), f"File should exist: {filepath}"
        print(f"✓ File created: {filename}")

    print("\n✓ Serialization test PASSED")


def run_all_tests():
    """Run all tests."""
    print("\n" + "="*80)
    print("SYNTHETIC GRAPH GENERATOR - TEST SUITE")
    print("="*80)

    try:
        test_small_graph()
        test_degree_distributions()
        test_community_structure()
        test_serialization()

        print("\n" + "="*80)
        print("ALL TESTS PASSED ✓")
        print("="*80 + "\n")

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    run_all_tests()

