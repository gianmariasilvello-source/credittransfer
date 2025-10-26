"""
Transitive Credit Distribution - Formulation I: General Transfer Model
Without Global Damping

This module implements credit distribution on directed graphs using arbitrary
transfer matrices without a global damping factor. It requires the graph to
be a DAG or, if cyclic, to have contractive cycles and be aperiodic for
guaranteed convergence.

Mathematical Formulation:
    c = A^T c + v      (total credit equation)
    k = c - (A·1) ⊙ c  (kudos equation, ⊙ = element-wise product)

Closed form:
    c = (I - A^T)^{-1} v
    k = [I - diag(A·1)] c

Author: Generated for credit distribution research
Date: October 2025
"""

import numpy as np
from scipy.sparse import csr_matrix, eye
from scipy.sparse.linalg import spsolve, eigs
from typing import Dict, Tuple, Optional, List
from graph.GraphUtils import Graph

class GeneralCreditTransfer:
    """
    Implements general credit transfer without global damping.

    This class computes transitive credit distribution using an arbitrary
    transfer matrix A, where A[i,j] represents the fraction of credit that
    node i transfers to node j.

    Attributes:
        graph (Graph): The directed graph structure
        transfer_matrix (csr_matrix): Sparse transfer matrix A
        nodes_list (list): Ordered list of node labels
        node_to_idx (dict): Mapping from node labels to matrix indices
        node_types (np.ndarray): Optional array of node type codes (0, 1, ...)
        _row_sums_cache (np.ndarray): Cached row sums for efficiency
    """

    def __init__(self, graph: Graph, node_types: Optional[np.ndarray] = None,
                 transfer_weights: Optional[Dict[Tuple, float]] = None,
                 use_integer_indices: bool = None):
        """
        Initialize the credit transfer model.

        Args:
            graph: A Graph object (must be directed)
            node_types: Optional array of node type codes (e.g., 0=paper, 1=dataset)
                       indexed to align with nodes_list
            transfer_weights: Dictionary mapping (source, target) -> weight.
                            If None, all edges get equal weight from each node.
            use_integer_indices: If True, assumes nodes are integers and uses direct indexing.
                               If False, uses dictionary mapping for arbitrary node labels.
                               If None (default), auto-detects based on node types.

        Raises:
            ValueError: If graph is not directed

        Note:
            Integer indexing mode is faster for large graphs with integer node IDs,
            as it avoids dictionary lookups. Best for graphs with nodes labeled 0, 1, 2, ...
        """
        if not graph.is_directed:
            raise ValueError("Graph must be directed for credit transfer")

        self.graph = graph
        self.nodes_list = list(graph.nodes())
        self.n = len(self.nodes_list)

        # Determine indexing strategy
        if use_integer_indices is None:
            # Auto-detect: use integer indexing if all nodes are integers
            use_integer_indices = all(isinstance(node, (int, np.integer)) for node in self.nodes_list)

        self.use_integer_indices = use_integer_indices

        if self.use_integer_indices:
            # Verify nodes are consecutive integers starting from 0
            if not self._validate_integer_nodes():
                raise ValueError(
                    "use_integer_indices=True requires nodes to be consecutive integers "
                    "starting from 0. Use use_integer_indices=False for arbitrary labels."
                )
            # Direct indexing - no dictionary needed
            self.node_to_idx = None
        else:
            # Dictionary mapping for arbitrary node labels
            self.node_to_idx = {node: i for i, node in enumerate(self.nodes_list)}

        # Store node types array for vectorized operations
        self.node_types = node_types

        # Cache for row sums to avoid recomputation
        self._row_sums_cache = None

        # Build transfer matrix (now sparse)
        self.transfer_matrix = self._build_transfer_matrix(transfer_weights)

    def _validate_integer_nodes(self) -> bool:
        """
        Validate that nodes are consecutive integers from 0 to n-1.

        Returns:
            True if nodes are valid for integer indexing, False otherwise.
        """
        try:
            # Check all nodes are integers
            int_nodes = [int(node) for node in self.nodes_list]
            # Check they form the set {0, 1, 2, ..., n-1}
            return set(int_nodes) == set(range(self.n))
        except (ValueError, TypeError):
            return False

    def _get_node_index(self, node) -> int:
        """
        Get the index of a node, using direct or dictionary lookup based on mode.

        Args:
            node: The node label

        Returns:
            Integer index of the node
        """
        if self.use_integer_indices:
            return int(node)
        else:
            return self.node_to_idx[node]

    def _build_transfer_matrix(self, transfer_weights: Optional[Dict[Tuple, float]]) -> csr_matrix:
        """
        Construct the sparse transfer matrix A from the graph and edge weights.

        Args:
            transfer_weights: Edge weights (source, target) -> fraction

        Returns:
            Sparse transfer matrix A of shape (n, n) in CSR format
        """
        row_indices = []
        col_indices = []
        data = []

        for source in self.nodes_list:
            neighbors = self.graph.get_neighbors(source)
            if not neighbors:
                continue

            src_idx = self._get_node_index(source)

            if transfer_weights is None:
                # Equal split among neighbors
                weight_per_neighbor = 1.0 / len(neighbors)
                for target in neighbors:
                    tgt_idx = self._get_node_index(target)
                    row_indices.append(src_idx)
                    col_indices.append(tgt_idx)
                    data.append(weight_per_neighbor)
            else:
                # Use provided weights
                for target in neighbors:
                    tgt_idx = self._get_node_index(target)
                    edge = (source, target)
                    weight = transfer_weights.get(edge, 0.0)
                    if weight != 0.0:  # Only store non-zero weights
                        row_indices.append(src_idx)
                        col_indices.append(tgt_idx)
                        data.append(weight)

        return csr_matrix((data, (row_indices, col_indices)), shape=(self.n, self.n))

    def compute_indegree_vector(self) -> np.ndarray:
        """
        Compute the indegree vector (number of incoming edges per node).

        This is the standard external credit injection vector v = A^T · 1,
        where each incoming edge contributes +1 credit.

        Returns:
            Indegree vector v of shape (n,)
        """
        indegree = np.zeros(self.n)

        for source in self.nodes_list:
            for target in self.graph.get_neighbors(source):
                tgt_idx = self._get_node_index(target)
                indegree[tgt_idx] += 1

        return indegree

    def check_convergence(self, use_sparse_solver: bool = True) -> Tuple[bool, float, float]:
        """
        Check whether the credit system will converge.

        Args:
            use_sparse_solver: If True, use sparse eigenvalue solver (faster for large graphs).
                              If False, use dense solver (more accurate for small graphs).

        Returns:
            Tuple of (converges, spectral_radius, determinant):
                - converges: True if det(I - A^T) != 0
                - spectral_radius: ρ(A^T)
                - determinant: det(I - A^T)

        Note:
            For large graphs (>1000 nodes), sparse solver is recommended.
            For small graphs (<100 nodes), dense solver may be more accurate.
        """
        A_T = self.transfer_matrix.T.tocsr()

        # Calculate spectral radius (largest eigenvalue magnitude)
        if use_sparse_solver and self.n > 100:
            # Use sparse eigenvalue solver for large matrices
            try:
                # Compute only the k largest magnitude eigenvalues
                # k must be < n, typically we only need a few
                k = min(6, self.n - 2)  # Compute top 6 eigenvalues or n-2, whichever is smaller

                if k < 1:
                    # Matrix too small for sparse solver, fall back to dense
                    use_sparse_solver = False
                else:
                    eigenvalues, _ = eigs(A_T, k=k, which='LM')  # LM = Largest Magnitude
                    spectral_radius = np.max(np.abs(eigenvalues))
            except Exception as e:
                # If sparse solver fails (e.g., convergence issues), fall back to dense
                print(f"Warning: Sparse eigenvalue solver failed ({e}), falling back to dense solver")
                use_sparse_solver = False

        if not use_sparse_solver or self.n <= 100:
            # Use dense eigenvalue computation for small matrices or if sparse failed
            A_T_dense = A_T.toarray()
            eigenvalues = np.linalg.eigvals(A_T_dense)
            spectral_radius = np.max(np.abs(eigenvalues))

        # Calculate the determinant of (I - A^T)
        # For large sparse matrices, determinant computation is expensive
        # We can skip it if spectral_radius < 1 (sufficient condition for convergence)
        if self.n > 1000 and spectral_radius < 0.99:
            # For large matrices with clear convergence, approximate determinant as non-zero
            determinant = 1.0 - spectral_radius  # Approximation
            converges = True
        else:
            # For smaller matrices or borderline cases, compute exact determinant
            I = np.eye(self.n)
            A_T_dense = A_T.toarray()
            B = I - A_T_dense
            determinant = np.linalg.det(B)
            converges = np.abs(determinant) > 1e-10

        return converges, spectral_radius, determinant

    def compute_credit_distribution(self,
                                    external_credit: Optional[np.ndarray] = None,
                                    check_convergence: bool = True,
                                    use_sparse_eigensolver: bool = True
                                    ) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """
        Compute the total credit and kudos for each node.

        Solves the system:
            c = (I - A^T)^{-1} v
            k = [I - diag(A·1)] c

        Args:
            external_credit: External credit vector v. If None, uses indegree.
            check_convergence: If True, verify convergence before solving (default: True).
                              Set to False to skip for known DAGs or large graphs.
            use_sparse_eigensolver: If True, use sparse eigenvalue solver for convergence check.
                                   Only used if check_convergence=True.

        Returns:
            Tuple of (total_credit, kudos, diagnostics):
                - total_credit: Vector c of total accumulated credit
                - kudos: Vector k of retained credit
                - diagnostics: Dictionary with convergence info

        Raises:
            ValueError: If check_convergence=True and system does not converge

        Note:
            Skipping convergence check can improve performance for large graphs,
            but may produce incorrect results if the graph has problematic cycles.
            Only skip if you're certain the graph structure guarantees convergence.
        """
        diagnostics = {}

        # Optionally check convergence
        if check_convergence:
            converges, spectral_radius, determinant = self.check_convergence(use_sparse_solver=use_sparse_eigensolver)

            diagnostics['spectral_radius'] = spectral_radius
            diagnostics['determinant'] = determinant
            diagnostics['converges'] = converges
            diagnostics['used_sparse_eigensolver'] = use_sparse_eigensolver and self.n > 100

            if not converges:
                raise ValueError(
                    f"Credit system does not converge:\n"
                    f"  Spectral radius ρ(A^T) = {spectral_radius:.6f}\n"
                    f"  det(I - A^T) = {determinant:.10e}\n"
                    f"Ensure graph is DAG or cycles are contractive and aperiodic."
                )
        else:
            diagnostics['spectral_radius'] = None
            diagnostics['determinant'] = None
            diagnostics['converges'] = None
            diagnostics['convergence_check_skipped'] = True

        # Set external credit vector
        if external_credit is None:
            v = self.compute_indegree_vector()
        else:
            v = external_credit

        # Solve for total credit: c = (I - A^T)^{-1} v
        # Use sparse matrices and solver for efficiency
        I = eye(self.n, format='csr')
        A_T = self.transfer_matrix.T.tocsr()
        B = I - A_T

        # Use sparse solver instead of dense
        total_credit = spsolve(B, v)

        # Ensure result is 1D array
        if hasattr(total_credit, 'A1'):
            total_credit = total_credit.A1

        # Compute kudos: k = c - (A·1) ⊙ c
        # Use cached row sums if available
        if self._row_sums_cache is None:
            self._row_sums_cache = np.array(self.transfer_matrix.sum(axis=1)).flatten()

        row_sums = self._row_sums_cache
        kudos = total_credit * (1 - row_sums)

        # Conservation check
        total_kudos = np.sum(kudos)
        total_external = np.sum(v)
        diagnostics['total_kudos'] = total_kudos
        diagnostics['total_external_credit'] = total_external
        diagnostics['conservation_error'] = np.abs(total_kudos - total_external)

        return total_credit, kudos, diagnostics

    def get_results_dict(self, total_credit: np.ndarray, kudos: np.ndarray) -> Dict:
        """
        Package results as a dictionary keyed by node labels.

        Args:
            total_credit: Total credit vector
            kudos: Kudos vector

        Returns:
            Dictionary mapping node -> {'total_credit': c, 'kudos': k}
        """
        results = {}

        if self.use_integer_indices:
            # Direct indexing mode - nodes are their own indices
            for node in self.nodes_list:
                idx = int(node)
                results[node] = {
                    'total_credit': total_credit[idx],
                    'kudos': kudos[idx]
                }
        else:
            # Dictionary mode
            for node, idx in self.node_to_idx.items():
                results[node] = {
                    'total_credit': total_credit[idx],
                    'kudos': kudos[idx]
                }

        return results

    def compute_edge_transfers(self, total_credit: np.ndarray) -> Dict[Tuple, float]:
        """
        Compute the credit transferred along each edge.

        For edge (i, j), transfer = A[i,j] × c[i]

        Args:
            total_credit: Total credit vector c

        Returns:
            Dictionary mapping (source, target) -> credit_transferred
        """
        edge_transfers = {}

        for source in self.nodes_list:
            src_idx = self._get_node_index(source)
            for target in self.graph.get_neighbors(source):
                tgt_idx = self._get_node_index(target)
                transfer = self.transfer_matrix[src_idx, tgt_idx] * total_credit[src_idx]
                edge_transfers[(source, target)] = transfer

        return edge_transfers


    def set_retention_rates(self, retention_rates: Dict) -> None:
        """
        Set how much credit each node retains as kudos and update the transfer matrix.

        Args:
            retention_rates: Dict mapping node -> fraction to retain (0.0 .. 1.0)

        Notes:
            - Nodes not present in `retention_rates` default to 0.0 retention.
            - Nodes with no outgoing neighbors are ignored (they retain everything).
        """
        # validate type
        if not isinstance(retention_rates, dict):
            raise TypeError("retention_rates must be a dict mapping node -> float")

        transfer_weights: Dict[Tuple, float] = {}

        for source in self.nodes_list:
            neighbors = list(self.graph.get_neighbors(source))
            if not neighbors:
                # no outgoing edges -> nothing to distribute
                continue

            retention = retention_rates.get(source, 0.0)
            if not isinstance(retention, (int, float)):
                raise TypeError(f"retention rate for node {source!r} must be a number")
            retention = float(retention)
            if not (0.0 <= retention <= 1.0):
                raise ValueError(f"retention rate for node {source!r} must be between 0.0 and 1.0")

            to_transfer = 1.0 - retention
            weight_per_neighbor = to_transfer / len(neighbors)

            for target in neighbors:
                transfer_weights[(source, target)] = weight_per_neighbor

        # rebuild transfer matrix from computed edge weights
        self.transfer_matrix = self._build_transfer_matrix(transfer_weights)

        # Invalidate cached row sums since matrix changed
        self._row_sums_cache = None


    def set_uniform_retention(self, rate: float) -> None:
        """
        Assign the same retention rate to all nodes and update the transfer matrix.

        Args:
            rate: Fraction to retain for every node (0.0 <= rate <= 1.0)
        """
        if not isinstance(rate, (int, float)):
            raise TypeError("rate must be a number")
        rate = float(rate)
        if rate < 0.0 or rate > 1.0:
            raise ValueError("rate must be between 0.0 and 1.0")

        if not hasattr(self, "nodes_list") or self.nodes_list is None:
            raise RuntimeError("Instance has no nodes_list; ensure graph initialized")

        retention_rates = {node: rate for node in self.nodes_list}
        # delegate to instance method
        self.set_retention_rates(retention_rates)


    def set_retention_by_type(self, type_retention_rates: np.ndarray) -> None:
        """
        Set retention rates based on node types using vectorized operations.

        This is an efficient method for large graphs where nodes are categorized
        into types (e.g., 0=paper, 1=dataset) and each type has a different
        retention rate.

        Args:
            type_retention_rates: Array where index corresponds to node type code
                                 and value is the retention rate for that type.
                                 E.g., np.array([0.2, 0.9]) means type 0 retains 20%,
                                 type 1 retains 90%.

        Raises:
            RuntimeError: If node_types was not provided during initialization

        Example:
            # Papers (type 0) retain 20%, Datasets (type 1) retain 90%
            gct.set_retention_by_type(np.array([0.2, 0.9]))
        """
        if self.node_types is None:
            raise RuntimeError(
                "node_types not provided during initialization. "
                "Pass node_types array to __init__ to use this method."
            )

        if not isinstance(type_retention_rates, np.ndarray):
            type_retention_rates = np.array(type_retention_rates, dtype=np.float64)
        else:
            # Ensure it's float type to handle both int and float inputs
            type_retention_rates = type_retention_rates.astype(np.float64)

        # Vectorized indexing: get retention rate for each node based on its type
        retention_rates_array = type_retention_rates[self.node_types]

        # Build retention_rates_dict using the node order (enumeration) so that
        # the per-node retention aligns with retention_rates_array regardless of
        # whether nodes are integer-labeled or arbitrary labels.
        retention_rates_dict = {
            node: float(retention_rates_array[idx])
            for idx, node in enumerate(self.nodes_list)
        }

        self.set_retention_rates(retention_rates_dict)


