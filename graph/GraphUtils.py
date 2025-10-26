class Graph:
                """
                A simple graph implementation using an adjacency list.
                Supports both directed and undirected graphs.
                """

                def __init__(self, is_directed=False):
                    """
                    Initializes an empty graph.

                    Args:
                        is_directed: If True, the graph is directed.
                    """
                    self.adjacency = {}
                    self.is_directed = is_directed

                def add_node(self, node):
                    """
                    Adds a node to the graph.

                    Args:
                        node: The node to add.
                    """
                    if node not in self.adjacency:
                        self.adjacency[node] = set()

                def add_edge(self, node1, node2):
                    """
                    Adds an edge between node1 and node2.

                    Args:
                        node1: The source node.
                        node2: The target node.
                    """
                    self.add_node(node1)
                    self.add_node(node2)
                    self.adjacency[node1].add(node2)
                    if not self.is_directed:
                        self.adjacency[node2].add(node1)

                def get_neighbors(self, node):
                    """
                    Returns the neighbors of a given node.

                    Args:
                        node: The node whose neighbors to return.

                    Returns:
                        A set of neighboring nodes.
                    """
                    return self.adjacency.get(node, set())

                def nodes(self):
                    """
                    Returns a list of all nodes in the graph.

                    Returns:
                        A list of nodes.
                    """
                    return list(self.adjacency.keys())

                def edges(self):
                    """
                    Returns a list of all unique edges in the graph as tuples.

                    Returns:
                        A list of tuples, each representing an edge (node1, node2).
                    """
                    edge_list = []
                    seen = set()
                    for node, neighbors in self.adjacency.items():
                        for neighbor in neighbors:
                            edge = (node, neighbor)
                            if self.is_directed or (tuple(sorted(edge)) not in seen):
                                edge_list.append(edge)
                                if not self.is_directed:
                                    seen.add(tuple(sorted(edge)))
                    return edge_list

                @staticmethod
                def from_matrix(nodes, matrix, is_directed=False):
                    """
                    Creates a Graph from a list of nodes and an adjacency matrix.

                    Args:
                        nodes: List of node labels.
                        matrix: 2D list representing the adjacency matrix.
                        is_directed: If True, creates a directed graph.

                    Returns:
                        A Graph object.
                    """
                    graph = Graph(is_directed=is_directed)
                    for i, node in enumerate(nodes):
                        graph.add_node(node)
                    for i in range(len(nodes)):
                        for j in range(len(nodes)):
                            if matrix[i][j]:
                                graph.add_edge(nodes[i], nodes[j])
                    return graph

                def to_matrix(self):
                    """
                    Return a tuple (nodes, matrix) where `nodes` is a list of node labels
                    and `matrix` is a size x size adjacency matrix with 1 for an edge
                    from nodes[i] -> nodes[j], 0 otherwise.
                    """
                    nodes = list(self.nodes())
                    idx = {n: i for i, n in enumerate(nodes)}
                    size = len(nodes)
                    matrix = [[0] * size for _ in range(size)]

                    adjacency = getattr(self, "adjacency", {})
                    for u, neighbors in adjacency.items():
                        if u not in idx:
                            continue
                        i = idx[u]
                        for v in neighbors:
                            j = idx.get(v)
                            if j is None:
                                continue
                            matrix[i][j] = 1

                    return nodes, matrix