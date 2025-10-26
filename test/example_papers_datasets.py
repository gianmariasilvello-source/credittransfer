"""
Example: Using GeneralCreditTransfer with Papers and Datasets

This example demonstrates how to use the efficiency improvements for
a graph with two node types (papers and datasets) with different
retention rates.
"""

import numpy as np
from graph.GraphUtils import Graph
from credit.generalFormulation import GeneralCreditTransfer


def main():
    print("=" * 70)
    print("Credit Transfer Example: Papers and Datasets")
    print("=" * 70)

    # Step 1: Define your graph structure
    # ====================================
    # We have 6 nodes: 4 papers (p1-p4) and 2 datasets (d1-d2)
    node_labels = ['p1', 'p2', 'p3', 'p4', 'd1', 'd2']
    n = len(node_labels)

    # Define the adjacency matrix (who cites whom)
    # Rows = source, Columns = target
    # Citation network:
    #   - p1 cites d1
    #   - p2 cites p1 and d1
    #   - p3 cites p2 and d2
    #   - p4 cites p3 and d2
    #   - d1 and d2 don't cite anyone

    adj_matrix = np.array([
        #  p1  p2  p3  p4  d1  d2
        [  0,  0,  0,  0,  1,  0],  # p1
        [  1,  0,  0,  0,  1,  0],  # p2
        [  0,  1,  0,  0,  0,  1],  # p3
        [  0,  0,  1,  0,  0,  1],  # p4
        [  0,  0,  0,  0,  0,  0],  # d1 (dataset - no outgoing)
        [  0,  0,  0,  0,  0,  0],  # d2 (dataset - no outgoing)
    ])

    # Step 2: Define node types
    # =========================
    # Use integer codes: 0 = paper, 1 = dataset
    # This array is parallel to node_labels
    node_types = np.array([
        0,  # p1 is a paper
        0,  # p2 is a paper
        0,  # p3 is a paper
        0,  # p4 is a paper
        1,  # d1 is a dataset
        1,  # d2 is a dataset
    ])

    print("\nGraph Structure:")
    print(f"  Nodes: {node_labels}")
    print(f"  Node Types: {['paper' if t == 0 else 'dataset' for t in node_types]}")
    print(f"  Adjacency Matrix shape: {adj_matrix.shape}")
    print(f"  Total edges: {np.sum(adj_matrix)}")

    # Step 3: Create the graph
    # ========================
    g = Graph.from_matrix(node_labels, adj_matrix, is_directed=True)

    # Step 4: Initialize the credit transfer model
    # ============================================
    # Pass node_types to enable vectorized retention rate assignment
    gct = GeneralCreditTransfer(graph=g, node_types=node_types)

    # Step 5: Set different retention rates for papers vs datasets
    # ============================================================
    # Papers retain 20% (transfer 80% to their references)
    # Datasets retain 90% (transfer 10% to their references, but they have none)

    paper_retention = 0.2
    dataset_retention = 0.9

    # Create retention rates array indexed by node type
    type_retention_rates = np.array([
        paper_retention,   # type 0 (papers)
        dataset_retention  # type 1 (datasets)
    ])

    # Apply retention rates efficiently using vectorized method
    gct.set_retention_by_type(type_retention_rates)

    print(f"\nRetention Rates Configuration:")
    print(f"  Papers (type 0): {paper_retention * 100:.0f}% retention")
    print(f"  Datasets (type 1): {dataset_retention * 100:.0f}% retention")

    # Step 6: Compute credit distribution
    # ===================================
    # For large graphs, you can skip convergence check for better performance:
    # total_credit, kudos, diagnostics = gct.compute_credit_distribution(check_convergence=False)
    #
    # By default, convergence is checked (recommended for first-time analysis):
    total_credit, kudos, diagnostics = gct.compute_credit_distribution(check_convergence=True)

    # Step 7: Display results
    # =======================
    print("\n" + "-" * 70)
    print("Convergence Diagnostics:")
    print("-" * 70)
    print(f"  Converges: {diagnostics['converges']}")
    print(f"  Spectral radius: {diagnostics['spectral_radius']:.6f}")
    print(f"  Determinant of (I - A^T): {diagnostics['determinant']:.6f}")
    print(f"  Total external credit: {diagnostics['total_external_credit']:.2f}")
    print(f"  Total kudos: {diagnostics['total_kudos']:.2f}")
    print(f"  Conservation error: {diagnostics['conservation_error']:.2e}")

    print("\n" + "-" * 70)
    print("Credit Distribution Results:")
    print("-" * 70)
    print(f"{'Node':<8} {'Type':<10} {'Total Credit':<15} {'Kudos':<15} {'Retention':<12}")
    print("-" * 70)

    results = gct.get_results_dict(total_credit, kudos)
    for i, (node, values) in enumerate(results.items()):
        node_type = "Paper" if node_types[i] == 0 else "Dataset"
        retention_pct = type_retention_rates[node_types[i]] * 100
        print(f"{node:<8} {node_type:<10} {values['total_credit']:<15.4f} "
              f"{values['kudos']:<15.4f} {retention_pct:<12.0f}%")

    # Step 8: Analyze the results
    # ===========================
    print("\n" + "-" * 70)
    print("Analysis:")
    print("-" * 70)

    # Compare credit received by papers vs datasets
    paper_indices = [i for i in range(n) if node_types[i] == 0]
    dataset_indices = [i for i in range(n) if node_types[i] == 1]

    total_paper_credit = sum(total_credit[i] for i in paper_indices)
    total_dataset_credit = sum(total_credit[i] for i in dataset_indices)

    total_paper_kudos = sum(kudos[i] for i in paper_indices)
    total_dataset_kudos = sum(kudos[i] for i in dataset_indices)

    print(f"\nPapers (4 nodes):")
    print(f"  Total Credit: {total_paper_credit:.2f}")
    print(f"  Total Kudos: {total_paper_kudos:.2f}")
    print(f"  Average Credit per Paper: {total_paper_credit/len(paper_indices):.2f}")

    print(f"\nDatasets (2 nodes):")
    print(f"  Total Credit: {total_dataset_credit:.2f}")
    print(f"  Total Kudos: {total_dataset_kudos:.2f}")
    print(f"  Average Credit per Dataset: {total_dataset_credit/len(dataset_indices):.2f}")

    print("\n" + "=" * 70)
    print("Interpretation:")
    print("=" * 70)
    print("""
Datasets (d1, d2) receive the most credit because:
1. They are cited by papers (receive external credit)
2. They retain 90% of their credit as kudos (high retention rate)
3. They don't cite anyone else (no credit outflow)

Papers receive less kudos because:
1. They only retain 20% of their credit
2. They transfer 80% to their references (other papers or datasets)
3. The credit flows through the citation network

This models a scenario where datasets are foundational resources that
accumulate credit, while papers act as credit distributors.
    """)

    print("=" * 70)


if __name__ == "__main__":
    main()

