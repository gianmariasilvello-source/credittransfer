"""
Author Metrics Module - Efficient h-index computation for authors.

This module provides efficient computation of author-level metrics (h-index)
from paper/dataset kudos values. Uses integer author IDs for optimal performance.

Author: Credit Transfer Project
Date: October 2025
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Union
from collections import defaultdict


class AuthorMetrics:
    """
    Efficiently compute h-index and other metrics for authors based on kudos.

    Uses integer author IDs for optimal performance with large author sets.
    Supports optional mapping to human-readable author names.
    """

    def __init__(self,
                 node_to_authors: Dict[int, Union[List[int], np.ndarray]],
                 author_names: Optional[Dict[int, str]] = None):
        """
        Initialize author metrics calculator.

        Args:
            node_to_authors: Maps node ID (paper/dataset) -> list of author IDs
                           Uses INTEGER author IDs for efficiency.
                           E.g., {0: [5, 12, 8], 1: [5, 9], 2: [5, 12]}
            author_names: Optional mapping from author_id -> author name
                         E.g., {5: "Smith, J.", 12: "Zhang, L."}
                         If None, author IDs are used for display.

        Example:
            # Paper 0 authored by authors 5, 12, 8
            # Paper 1 authored by authors 5, 9
            node_to_authors = {
                0: [5, 12, 8],
                1: [5, 9],
                2: [5, 12]
            }

            # Optional: human-readable names
            author_names = {
                5: "Smith, J.",
                12: "Zhang, L.",
                8: "Johnson, K.",
                9: "Lee, S."
            }

            metrics = AuthorMetrics(node_to_authors, author_names)
        """
        self.node_to_authors = node_to_authors
        self.author_names = author_names if author_names is not None else {}

        # Extract all unique author IDs and sort for consistent ordering
        all_authors = set()
        for authors in node_to_authors.values():
            if isinstance(authors, np.ndarray):
                all_authors.update(authors.tolist())
            else:
                all_authors.update(authors)

        self.author_ids = sorted(all_authors)
        self.n_authors = len(self.author_ids)

        # Build reverse index: author_id -> list of node IDs (papers/datasets)
        # This is the key data structure for efficient lookup
        self.author_to_nodes = defaultdict(list)
        for node_id, authors in node_to_authors.items():
            if isinstance(authors, np.ndarray):
                authors = authors.tolist()
            for author_id in authors:
                self.author_to_nodes[author_id].append(node_id)

        # Convert to numpy arrays for faster indexing
        for author_id in self.author_ids:
            self.author_to_nodes[author_id] = np.array(self.author_to_nodes[author_id], dtype=np.int32)

    def get_author_name(self, author_id: int) -> str:
        """
        Get display name for an author.

        Args:
            author_id: Integer author ID

        Returns:
            Author name if available, otherwise "Author {id}"
        """
        return self.author_names.get(author_id, f"Author {author_id}")

    def get_author_kudos(self, author_id: int, kudos: np.ndarray) -> np.ndarray:
        """
        Get all kudos values for a specific author's publications.

        Args:
            author_id: Integer author ID
            kudos: Kudos vector from credit distribution

        Returns:
            Numpy array of kudos values for this author's works
        """
        node_ids = self.author_to_nodes.get(author_id, np.array([], dtype=np.int32))
        if len(node_ids) == 0:
            return np.array([])

        # Vectorized indexing - very fast
        return kudos[node_ids]

    def compute_h_index(self, kudos_values: np.ndarray) -> int:
        """
        Compute h-index from an array of kudos values.

        h-index definition: The largest number h such that h publications
        have at least h kudos each.

        Args:
            kudos_values: Array of kudos for an author's publications

        Returns:
            h-index value (integer)

        Algorithm:
            1. Sort kudos in descending order
            2. Find max h where kudos[h-1] >= h

        Time complexity: O(n log n) where n = number of publications
        """
        if len(kudos_values) == 0:
            return 0

        # Sort kudos in descending order
        sorted_kudos = np.sort(kudos_values)[::-1]

        # Find h-index: max h where sorted_kudos[h-1] >= h
        h = 0
        for i, kudos_val in enumerate(sorted_kudos, start=1):
            if kudos_val >= i:
                h = i
            else:
                break

        return h

    def compute_all_h_indices(self, kudos: np.ndarray) -> Dict[int, int]:
        """
        Compute h-index for all authors efficiently.

        Args:
            kudos: Kudos vector from credit distribution (length = n_nodes)

        Returns:
            Dictionary mapping author_id -> h_index

        Time complexity: O(A × P × log P) where:
            A = number of authors
            P = average publications per author
        """
        h_indices = {}

        for author_id in self.author_ids:
            kudos_vals = self.get_author_kudos(author_id, kudos)
            h_indices[author_id] = self.compute_h_index(kudos_vals)

        return h_indices

    def compute_h_index_from_total_credit(self, total_credit: np.ndarray) -> Dict[int, int]:
        """
        Compute h-index for all authors using TOTAL CREDIT instead of kudos.

        This measures an author's influence including all transitive credit,
        not just retained credit (kudos).

        Args:
            total_credit: Total credit vector from credit distribution

        Returns:
            Dictionary mapping author_id -> h_index_from_total_credit
        """
        h_indices = {}

        for author_id in self.author_ids:
            # Get total credit for this author's works (instead of kudos)
            node_ids = self.author_to_nodes.get(author_id, np.array([], dtype=np.int32))
            if len(node_ids) == 0:
                h_indices[author_id] = 0
            else:
                credit_vals = total_credit[node_ids]
                h_indices[author_id] = self.compute_h_index(credit_vals)

        return h_indices

    def get_author_direct_citations(self, author_id: int, graph) -> int:
        """
        Count total direct citations (in-degree) for all of an author's works.

        Args:
            author_id: Integer author ID
            graph: Graph object

        Returns:
            Total number of direct citations across all author's publications
        """
        node_ids = self.author_to_nodes.get(author_id, np.array([], dtype=np.int32))
        if len(node_ids) == 0:
            return 0

        # Fast path: precompute indegree per node in one pass
        indegree = defaultdict(int)
        adjacency = getattr(graph, 'adjacency', {})
        for src, nbrs in adjacency.items():
            for tgt in nbrs:
                indegree[tgt] += 1

        total_citations = 0
        for node_id in node_ids:
            total_citations += indegree.get(node_id, 0)

        return total_citations

    def compute_all_direct_citations(self, graph) -> Dict[int, int]:
        """
        Compute total direct citations for all authors.

        Args:
            graph: Graph object

        Returns:
            Dictionary mapping author_id -> total_direct_citations
        """
        # Precompute indegree for all nodes in a single pass over edges
        indegree = defaultdict(int)
        adjacency = getattr(graph, 'adjacency', {})
        for src, nbrs in adjacency.items():
            for tgt in nbrs:
                indegree[tgt] += 1

        citations = {}
        for author_id in self.author_ids:
            node_ids = self.author_to_nodes.get(author_id, np.array([], dtype=np.int32))
            total = 0
            for node_id in node_ids:
                total += indegree.get(node_id, 0)
            citations[author_id] = total

        return citations

    def compute_author_statistics(self, kudos: np.ndarray) -> Dict[int, Dict[str, float]]:
        """
        Compute comprehensive statistics for each author.

        Args:
            kudos: Kudos vector from credit distribution

        Returns:
            Dictionary mapping author_id -> statistics dict with:
                - h_index: h-index value
                - total_kudos: Sum of all kudos
                - avg_kudos: Average kudos per publication
                - max_kudos: Maximum kudos for any publication
                - n_publications: Number of publications
        """
        stats = {}

        for author_id in self.author_ids:
            kudos_vals = self.get_author_kudos(author_id, kudos)

            if len(kudos_vals) == 0:
                stats[author_id] = {
                    'h_index': 0,
                    'total_kudos': 0.0,
                    'avg_kudos': 0.0,
                    'max_kudos': 0.0,
                    'n_publications': 0
                }
            else:
                stats[author_id] = {
                    'h_index': self.compute_h_index(kudos_vals),
                    'total_kudos': float(np.sum(kudos_vals)),
                    'avg_kudos': float(np.mean(kudos_vals)),
                    'max_kudos': float(np.max(kudos_vals)),
                    'n_publications': len(kudos_vals)
                }

        return stats

    def get_top_authors_by_h_index(self,
                                   kudos: np.ndarray,
                                   top_k: int = 10) -> List[Tuple[int, int, str]]:
        """
        Get top k authors ranked by h-index.

        Args:
            kudos: Kudos vector from credit distribution
            top_k: Number of top authors to return

        Returns:
            List of (author_id, h_index, author_name) tuples,
            sorted by h_index descending
        """
        h_indices = self.compute_all_h_indices(kudos)

        # Sort by h-index descending, then by author_id for ties
        sorted_authors = sorted(
            h_indices.items(),
            key=lambda x: (x[1], x[0]),
            reverse=True
        )

        # Add author names
        result = [
            (author_id, h_idx, self.get_author_name(author_id))
            for author_id, h_idx in sorted_authors[:top_k]
        ]

        return result

    def get_top_authors_by_total_kudos(self,
                                      kudos: np.ndarray,
                                      top_k: int = 10) -> List[Tuple[int, float, str]]:
        """
        Get top k authors ranked by total kudos.

        Args:
            kudos: Kudos vector from credit distribution
            top_k: Number of top authors to return

        Returns:
            List of (author_id, total_kudos, author_name) tuples,
            sorted by total_kudos descending
        """
        author_kudos = {}

        for author_id in self.author_ids:
            kudos_vals = self.get_author_kudos(author_id, kudos)
            author_kudos[author_id] = float(np.sum(kudos_vals))

        # Sort by total kudos descending
        sorted_authors = sorted(
            author_kudos.items(),
            key=lambda x: x[1],
            reverse=True
        )

        # Add author names
        result = [
            (author_id, total_kudos, self.get_author_name(author_id))
            for author_id, total_kudos in sorted_authors[:top_k]
        ]

        return result

    def display_author_report(self,
                            kudos: np.ndarray,
                            total_credit: Optional[np.ndarray] = None,
                            graph = None,
                            top_k: int = 10,
                            show_details: bool = True):
        """
        Print a formatted report of author metrics.

        Args:
            kudos: Kudos vector from credit distribution
            total_credit: Optional total credit vector for h-index from total credit
            graph: Optional graph for computing direct citations
            top_k: Number of top authors to display
            show_details: If True, show detailed statistics
        """
        print(f"\n{'='*80}")
        print(f"AUTHOR METRICS REPORT")
        print(f"{'='*80}")
        print(f"Total authors: {self.n_authors}")
        print(f"Total publications: {len(self.node_to_authors)}")

        # Compute all metrics
        h_indices_kudos = self.compute_all_h_indices(kudos)
        h_indices_credit = None
        direct_citations = None

        if total_credit is not None:
            h_indices_credit = self.compute_h_index_from_total_credit(total_credit)

        if graph is not None:
            direct_citations = self.compute_all_direct_citations(graph)

        # Top authors by h-index (from kudos)
        print(f"\n{'='*80}")
        print(f"Top {top_k} Authors by h-index (from KUDOS)")
        print(f"{'='*80}")

        header = f"{'Rank':<6} {'Author ID':<12} {'h-kudos':<10} {'Pubs':<8} {'Total Kudos':<15}"
        if h_indices_credit:
            header += f" {'h-credit':<10}"
        if direct_citations:
            header += f" {'Citations':<12}"
        header += " Name"
        print(header)
        print(f"{'-'*80}")

        # Sort by h-index from kudos
        sorted_authors = sorted(
            h_indices_kudos.items(),
            key=lambda x: (x[1], x[0]),
            reverse=True
        )[:top_k]

        for rank, (author_id, h_idx_kudos) in enumerate(sorted_authors, 1):
            kudos_vals = self.get_author_kudos(author_id, kudos)
            n_pubs = len(kudos_vals)
            total_kudos = np.sum(kudos_vals)
            name = self.get_author_name(author_id)

            line = f"{rank:<6} {author_id:<12} {h_idx_kudos:<10} {n_pubs:<8} {total_kudos:<15.2f}"

            if h_indices_credit:
                h_idx_credit = h_indices_credit[author_id]
                line += f" {h_idx_credit:<10}"

            if direct_citations:
                cites = direct_citations[author_id]
                line += f" {cites:<12}"

            line += f" {name}"
            print(line)

        # Top authors by h-index from total credit (if available)
        if h_indices_credit:
            print(f"\n{'='*80}")
            print(f"Top {top_k} Authors by h-index (from TOTAL CREDIT)")
            print(f"{'='*80}")

            header = f"{'Rank':<6} {'Author ID':<12} {'h-credit':<10} {'h-kudos':<10} {'Pubs':<8} {'Total Credit':<15}"
            if direct_citations:
                header += f" {'Citations':<12}"
            header += " Name"
            print(header)
            print(f"{'-'*80}")

            # Sort by h-index from total credit
            sorted_by_credit = sorted(
                h_indices_credit.items(),
                key=lambda x: (x[1], x[0]),
                reverse=True
            )[:top_k]

            for rank, (author_id, h_idx_credit) in enumerate(sorted_by_credit, 1):
                node_ids = self.author_to_nodes.get(author_id, np.array([], dtype=np.int32))
                n_pubs = len(node_ids)
                total_cred = np.sum(total_credit[node_ids]) if n_pubs > 0 else 0
                h_idx_kudos = h_indices_kudos[author_id]
                name = self.get_author_name(author_id)

                line = f"{rank:<6} {author_id:<12} {h_idx_credit:<10} {h_idx_kudos:<10} {n_pubs:<8} {total_cred:<15.2f}"

                if direct_citations:
                    cites = direct_citations[author_id]
                    line += f" {cites:<12}"

                line += f" {name}"
                print(line)

        if show_details:
            # Top authors by total kudos
            print(f"\n{'='*80}")
            print(f"Top {top_k} Authors by Total Kudos")
            print(f"{'='*80}")

            header = f"{'Rank':<6} {'Author ID':<12} {'Total Kudos':<15} {'Pubs':<8} {'Avg Kudos':<12}"
            if direct_citations:
                header += f" {'Citations':<12}"
            header += " Name"
            print(header)
            print(f"{'-'*80}")

            top_by_kudos = self.get_top_authors_by_total_kudos(kudos, top_k)
            for rank, (author_id, total_kudos_val, name) in enumerate(top_by_kudos, 1):
                kudos_vals = self.get_author_kudos(author_id, kudos)
                n_pubs = len(kudos_vals)
                avg_kudos = total_kudos_val / n_pubs if n_pubs > 0 else 0

                line = f"{rank:<6} {author_id:<12} {total_kudos_val:<15.2f} {n_pubs:<8} {avg_kudos:<12.2f}"

                if direct_citations:
                    cites = direct_citations[author_id]
                    line += f" {cites:<12}"

                line += f" {name}"
                print(line)


def create_random_authorship(n_nodes: int,
                             n_authors: int,
                             min_authors: int = 1,
                             max_authors: int = 5,
                             seed: Optional[int] = None) -> Dict[int, List[int]]:
    """
    Generate random authorship for testing purposes.

    Args:
        n_nodes: Number of papers/datasets
        n_authors: Total number of authors
        min_authors: Minimum authors per paper
        max_authors: Maximum authors per paper
        seed: Random seed for reproducibility

    Returns:
        Dictionary mapping node_id -> list of author_ids
    """
    if seed is not None:
        np.random.seed(seed)

    node_to_authors = {}

    for node_id in range(n_nodes):
        n_authors_for_node = np.random.randint(min_authors, max_authors + 1)
        authors = np.random.choice(n_authors, size=n_authors_for_node, replace=False)
        node_to_authors[node_id] = list(authors)

    return node_to_authors
