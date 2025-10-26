from credit.creditUtils import display_results
from credit.generalFormulation import GeneralCreditTransfer
from graph.GraphUtils import Graph


def example_dag():

    """Example: Simple DAG with 3 nodes."""
    print("=" * 70)
    print("EXAMPLE 1: Simple DAG (a -> b -> c)")
    print("=" * 70)

    # Create graph
    g = Graph(is_directed=True)
    g.add_edge('a', 'b')
    g.add_edge('b', 'c')

    # set the retention rate for the nodes
    retention_rate = 0.8
    weights = {
        ('1', '2'): 1.0,
        ('2', '3'): 1.0
    }

    # Compute credit
    ct = GeneralCreditTransfer(g)
    # set the same retention rate for all nodes
    #ct.set_uniform_retention(retention_rate)
    ct.set_retention_rates(weights)
    total_credit, kudos, diagnostics = ct.compute_credit_distribution()

    # Display results
    display_results(ct, total_credit, kudos, diagnostics)


def example_cyclic_aperiodic():
    """Example: Cycle with self-loop (aperiodic)."""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Cyclic graph with self-loop (aperiodic)")
    print("=" * 70)

    # set the retention rate for the nodes if the uniform distribution is used
    retention_rate = 0.5

    # Create 3-cycle with self-loop at node a
    g = Graph(is_directed=True)
    g.add_edge('a', 'd')  # self-loop
    g.add_edge('a', 'b')
    g.add_edge('b', 'c')
    g.add_edge('c', 'a')

    # Print graph structure
    print("\nGraph structure:")
    print("  " + ", ".join(f"{u} -> {v}" for u, v in g.edges()))

    ct = GeneralCreditTransfer(g)
    ct.set_uniform_retention(0.5)
    total_credit, kudos, diagnostics = ct.compute_credit_distribution()


    display_results(ct, total_credit, kudos, diagnostics)




def example_periodic_failure():
    """Example: Periodic 5-node graph that fails."""
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Periodic 5-node graph (FAILS - ρ = 1)")
    print("=" * 70)

    g = Graph(is_directed=True)
    g.add_edge(1, 2)
    g.add_edge(2, 3)
    g.add_edge(2, 4)
    g.add_edge(3, 5)
    g.add_edge(4, 5)
    g.add_edge(5, 1)

    weights = {
        (1, 2): 1.0,
        (2, 3): 0.5,
        (2, 4): 0.5,
        (3, 5): 1.0,
        (4, 5): 1.0,
        (5, 1): 1.0
    }

    ct = GeneralCreditTransfer(g, weights)


    try:
        total_credit, kudos, diagnostics = ct.compute_credit_distribution()

        display_results(ct, total_credit, kudos, diagnostics)
        print("Unexpectedly converged!")
    except ValueError as e:
        print(f"\nExpected failure:\n{e}")


def example_peter():
    """Example: Periodic 5-node graph that fails."""
    print("\n" + "=" * 70)
    print("EXAMPLE 4: 4-node with loop, almost zero retention")
    print("=" * 70)

    g = Graph(is_directed=True)
    g.add_edge(1, 2)
    g.add_edge(2, 3)
    g.add_edge(3, 4)
    g.add_edge(4, 2)

    weights = {
        (1, 2): 0.0,
        (2, 3): 0.0,
        (3, 4): 0.1,
        (4, 2): 0.0,
    }

    ct = GeneralCreditTransfer(g, weights)


    try:
        total_credit, kudos, diagnostics = ct.compute_credit_distribution()

        display_results(ct, total_credit, kudos, diagnostics)
    except ValueError as e:
        print(f"\nExpected failure:\n{e}")