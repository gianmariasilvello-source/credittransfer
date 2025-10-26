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
                    # Maintain reverse adjacency for directed graphs to speed indegree/in_neighbors
                    self._reverse_adjacency = {} if is_directed else None

                def add_node(self, node):
                    """
                    Adds a node to the graph.

                    Args:
                        node: The node to add.
                    """
                    if node not in self.adjacency:
                        self.adjacency[node] = set()
                    if self.is_directed:
                        if node not in self._reverse_adjacent_nodes():
                            self._reverse_adjacency[node] = set()

                def _reverse_adjacent_nodes(self):
                    # Helper to avoid attribute checks in hot paths
                    return self._reverse_adjacency if self._reverse_adjacency is not None else {}

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
                    else:
                        # maintain reverse adjacency for directed graphs
                        self._reverse_adjacency[node2].add(node1)

                def get_neighbors(self, node):
                    """
                    Returns the neighbors of a given node.

                    Args:
                        node: The node whose neighbors to return.

                    Returns:
                        A set of neighboring nodes.
                    """
                    return self.adjacency.get(node, set())

                def in_neighbors(self, node):
                    """Return nodes with edges into `node` (for directed graphs).
                    For undirected graphs, this equals get_neighbors(node).
                    """
                    if self.is_directed:
                        return self._reverse_adjacent_nodes().get(node, set())
                    return self.get_neighbors(node)

                def indegree(self, node):
                    """Return the in-degree of `node`. For undirected graphs, returns degree."""
                    return len(self.in_neighbors(node))

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

                @staticmethod
                def from_edgelist(filepath, is_directed=True, comment_char='#', delimiter=None):
                    """
                    Load a graph from an edgelist file.

                    File format: one edge per line as "source target"
                    Lines starting with comment_char are ignored.

                    Args:
                        filepath: Path to the edgelist file
                        is_directed: If True, creates a directed graph (default: True)
                        comment_char: Character indicating comment lines (default: '#')
                        delimiter: Delimiter between source and target (default: whitespace)

                    Returns:
                        A Graph object

                    Example file format:
                        # Citation network edgelist
                        # source target
                        0 1
                        0 2
                        1 3
                        2 3

                    Example usage:
                        graph = Graph.from_edgelist('data/synthetic_edges.txt')
                    """
                    graph = Graph(is_directed=is_directed)

                    with open(filepath, 'r') as f:
                        for line_num, line in enumerate(f, 1):
                            line = line.strip()

                            # Skip empty lines and comments
                            if not line or line.startswith(comment_char):
                                continue

                            # Parse edge
                            try:
                                if delimiter:
                                    parts = line.split(delimiter)
                                else:
                                    parts = line.split()

                                if len(parts) < 2:
                                    print(f"Warning: Skipping malformed line {line_num}: {line}")
                                    continue

                                source = parts[0]
                                target = parts[1]

                                # Try to convert to int if possible (for integer node IDs)
                                try:
                                    source = int(source)
                                    target = int(target)
                                except ValueError:
                                    pass  # Keep as strings

                                graph.add_edge(source, target)

                            except Exception as e:
                                print(f"Warning: Error parsing line {line_num}: {line} - {e}")
                                continue

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