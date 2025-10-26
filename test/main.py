import tkinter as tk
import sys

import numpy as np

from credit.authorMetrics import AuthorMetrics
from credit.creditUtils import display_results
from credit.generalFormulation import GeneralCreditTransfer
from graph.GraphGUI import GraphGUI
from graph.GraphUtils import Graph
from test.graphTemplates import example_dag, example_cyclic_aperiodic, example_periodic_failure, example_peter


def main():
    nodes = ['A', 'B', 'C']
    matrix = [
        [0, 1, 0],
        [0, 0, 1],
        [0, 1, 0]
    ]
    g = Graph.from_matrix(nodes, matrix, is_directed=True)
    print("Nodes:", g.nodes())
    print("Edges:", g.edges())


def run_mode(mode: str = "gui"):
    if mode == "gui":
        root = tk.Tk()
        gui = GraphGUI(root)
        root.mainloop()
    elif mode == "examples":
        example_dag()
        example_cyclic_aperiodic()
        example_periodic_failure()
        example_peter()
    elif mode == "custom":
        #use gui to create a graph from adjacency matrix
        # then cut and paste the node list and the matrix into this function to test

        g = Graph(is_directed=True)
        g.add_edge(1, 2)
        g.add_edge(2, 3)
        g.add_edge(3, 4)
        g.add_edge(4, 2)

        # these are the transfer weights for each edge
        weights = {
            (1, 2): 1,
            (2, 3): 1,
            (3, 4): 0.9,
            (4, 2): 1,
        }

        ct = GeneralCreditTransfer(g, weights)
        v = np.array([1, 0, 0, 0])
        total_credit, kudos, diagnostics = ct.compute_credit_distribution(v)
        display_results(ct, total_credit, kudos, diagnostics)
    elif mode == "matrix":
        # Example of creating a graph from an adjacency matrix
        nodes = [1, 2, 3, 4]
        matrix = [
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1],
            [0, 1, 0, 0]
        ]
        g = Graph.from_matrix(nodes, matrix, is_directed=True)

        # Example weights for the edges
        weights = {
            (1, 2): 1,
            (2, 3): 1,
            (3, 4): 0.9,
            (4, 2): 1,
        }

        ct = GeneralCreditTransfer(g, weights)
        v = np.array([1, 0, 0, 0])
        total_credit, kudos, diagnostics = ct.compute_credit_distribution(v, check_convergence=True,
        use_sparse_eigensolver=True)
        display_results(ct, total_credit, kudos, diagnostics)
    elif mode == "optimized":
        node_labels = [0, 1, 2, 3, 4]
        adj_matrix =  [[0, 1, 1, 0, 1],
                      [0, 0, 1, 1, 0],
                      [0, 0, 0, 1, 0],
                      [0, 0, 0, 0, 0],
                       [0, 1, 0, 0, 0]]
        # 0=paper, 1=dataset
        node_types = np.array([0, 1, 0, 0, 1])
        g = Graph.from_matrix(node_labels, adj_matrix, is_directed=True)
        print(f"Graph: {len(g.nodes())} nodes, {len(g.edges())} edges")

        # ============================================================================
        # Initialize with ALL optimizations
        # ============================================================================

        gct = GeneralCreditTransfer(
            graph=g,
            node_types=node_types,  # For vectorized retention rates
            use_integer_indices=True
        )

        print(f"Using integer indexing: {gct.use_integer_indices}")
        print(f"Sparse matrix: {gct.transfer_matrix.format} format")
        print(f"Memory usage: ~{gct.transfer_matrix.data.nbytes / 1024 / 1024:.1f} MB")

        # Papers retain 100%, Datasets retain 80%
        type_retention_rates = np.array([1, 0.8])
        gct.set_retention_by_type(type_retention_rates)

        total_credit, kudos, diagnostics = gct.compute_credit_distribution(
            check_convergence=True,  # Verify convergence
            use_sparse_eigensolver=True  # Use sparse eigenvalue solver
        )

        print(f"Kudos:  {kudos}")
        print(f"Total credit:  {total_credit}")

        node_to_authors = {
            0: [0, 1],
            1: [0, 1],
            2: [1],
            3: [1],
            4: [2]
        }

        author_names = {
            0: "Alice (cited)",
            1: "Bob (senior)",
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


    elif mode == "file":
        # Run from configuration file
        if len(sys.argv) < 3:
            print("Usage: python main.py file <config_file>")
            print("Example: python main.py file ../config/example.properties")
            sys.exit(1)

        config_file = sys.argv[2]
        if not os.path.exists(config_file):
            print(f"Error: Configuration file not found: {config_file}")
            sys.exit(1)

        from credit.creditRunner import run_from_config
        run_from_config(config_file)
    else:
        print(f"Unknown mode: {mode}. Available modes:")
        print("  gui      - Interactive graph GUI")
        print("  examples - Run example graphs")
        print("  custom   - Run custom example with weights")
        print("  matrix   - Run matrix-based example")
        print("  optimized - Run optimized example with all features")
        print("  file <config> - Run from configuration file")

if __name__ == "__main__":
    import os
    mode = sys.argv[1] if len(sys.argv) > 1 else "optimized"
    run_mode(mode)
