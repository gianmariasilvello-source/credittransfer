"""
Synthetic Citation Graph Generator

Generates realistic citation networks with typical citation network properties:
- Directed Acyclic Graph (DAG) structure
- Power-law in-degree distribution (few highly-cited papers)
- Exponential out-degree distribution
- Community structure (research subfields)
- Hierarchical structure
- Transitivity (citation triangles)
- Multi-type nodes (papers, datasets, software)

Author: Credit Transfer Project
Date: October 2025
"""

import numpy as np
import json
from typing import Dict, List, Tuple, Optional, Set
from collections import defaultdict
from graph.GraphUtils import Graph
import configparser


class SyntheticCitationGraphGenerator:
    """
    Generate synthetic citation networks with realistic properties.

    Key features:
    - DAG structure (respects temporal order)
    - Power-law in-degree distribution
    - Exponential out-degree distribution
    - Community structure with preferential attachment within communities
    - Transitivity (triangles)
    - Multiple node types with different citation patterns
    """

    def __init__(self, config_file: str):
        """
        Initialize generator from configuration file.

        Args:
            config_file: Path to .properties configuration file
        """
        self.config = self._load_config(config_file)
        self._validate_config()

        # Set random seed for reproducibility
        if self.config['seed'] is not None:
            np.random.seed(self.config['seed'])

    def _load_config(self, config_file: str) -> Dict:
        """Load configuration from properties file."""
        parser = configparser.ConfigParser()
        parser.read(config_file)

        config = {
            # Graph size
            'n_nodes': parser.getint('graph', 'n_nodes'),

            # Node type distribution
            'num_types': parser.getint('types', 'num_types'),
            'type_names': {},
            'type_proportions': [],

            # Density and connectivity
            'avg_out_degree': parser.getfloat('density', 'avg_out_degree'),
            'density_variation': parser.getfloat('density', 'density_variation', fallback=0.2),

            # Power-law in-degree parameters
            'powerlaw_exponent': parser.getfloat('indegree', 'powerlaw_exponent', fallback=2.5),

            # Exponential out-degree parameters
            'exp_out_lambda': parser.getfloat('outdegree', 'exp_lambda', fallback=0.3),

            # Community structure
            'n_communities': parser.getint('communities', 'n_communities'),
            'within_community_prob': parser.getfloat('communities', 'within_community_prob'),
            'between_community_prob': parser.getfloat('communities', 'between_community_prob'),

            # Transitivity (triangle formation)
            'transitivity_prob': parser.getfloat('structure', 'transitivity_prob'),

            # Hierarchical structure
            'hierarchy_levels': parser.getint('structure', 'hierarchy_levels', fallback=5),
            'level_bias': parser.getfloat('structure', 'level_bias', fallback=0.7),

            # Type-specific citation patterns
            'type_citation_preferences': {},

            # Authors
            'n_authors': parser.getint('authors', 'n_authors', fallback=0),
            'avg_authors_per_node': parser.getfloat('authors', 'avg_authors_per_node', fallback=3.0),
            'author_productivity_exponent': parser.getfloat('authors', 'productivity_exponent', fallback=2.0),

            # Output
            'output_dir': parser.get('output', 'output_dir'),
            'output_prefix': parser.get('output', 'output_prefix', fallback='synthetic'),
            'save_dense_adjacency': parser.getboolean('output', 'save_dense_adjacency', fallback=True),

            # Random seed
            'seed': parser.getint('general', 'seed', fallback=None) if parser.has_option('general', 'seed') else None
        }

        # Load type information
        for i in range(config['num_types']):
            type_name = parser.get('types', f'type_{i}_name')
            type_proportion = parser.getfloat('types', f'type_{i}_proportion')
            config['type_names'][i] = type_name
            config['type_proportions'].append(type_proportion)

            # Load citation preferences if specified
            if parser.has_option('citation_preferences', f'type_{i}_cites'):
                prefs = parser.get('citation_preferences', f'type_{i}_cites')
                # Parse comma-separated list of (type:weight) pairs
                pref_dict = {}
                for item in prefs.split(','):
                    if ':' in item:
                        target_type, weight = item.strip().split(':')
                        pref_dict[int(target_type)] = float(weight)
                config['type_citation_preferences'][i] = pref_dict

        # Normalize type proportions
        total = sum(config['type_proportions'])
        config['type_proportions'] = [p / total for p in config['type_proportions']]

        return config

    def _validate_config(self):
        """Validate configuration parameters."""
        if self.config['n_nodes'] < 1:
            raise ValueError("n_nodes must be >= 1")

        if self.config['n_communities'] > self.config['n_nodes']:
            raise ValueError("n_communities cannot exceed n_nodes")

        if not (0 <= self.config['within_community_prob'] <= 1):
            raise ValueError("within_community_prob must be in [0, 1]")

        if not (0 <= self.config['transitivity_prob'] <= 1):
            raise ValueError("transitivity_prob must be in [0, 1]")

    def generate(self) -> Tuple[Graph, np.ndarray, Dict, Dict]:
        """
        Generate synthetic citation graph with authors.

        Returns:
            Tuple of (graph, node_types, node_to_authors, metadata):
                - graph: Graph object with citation edges
                - node_types: Array of node type codes
                - node_to_authors: Dict mapping node_id -> list of author_ids
                - metadata: Dictionary with generation statistics
        """
        print(f"\nGenerating synthetic citation graph...")
        print(f"  Nodes: {self.config['n_nodes']}")
        print(f"  Communities: {self.config['n_communities']}")
        print(f"  Types: {self.config['num_types']}")
        if self.config['n_authors'] > 0:
            print(f"  Authors: {self.config['n_authors']}")

        # Step 1: Assign node types
        node_types = self._assign_node_types()

        # Step 2: Assign nodes to communities
        node_communities = self._assign_communities()

        # Step 3: Assign temporal order (for DAG property)
        temporal_order = np.arange(self.config['n_nodes'])

        # Step 4: Assign hierarchical levels
        node_levels = self._assign_hierarchy_levels()

        # Step 5: Generate edges with all constraints
        graph, edges_by_mechanism = self._generate_edges(
            node_types, node_communities, temporal_order, node_levels
        )

        # Step 6: Generate authors
        node_to_authors, author_names = self._generate_authors()

        # Step 7: Compute metadata
        metadata = self._compute_metadata(graph, node_types, node_communities, edges_by_mechanism, node_to_authors)

        print(f"\nGeneration complete:")
        print(f"  Total edges: {len(graph.edges())}")
        print(f"  Avg in-degree: {metadata['avg_in_degree']:.2f}")
        print(f"  Avg out-degree: {metadata['avg_out_degree']:.2f}")
        print(f"  Transitivity: {metadata['transitivity']:.3f}")
        if self.config['n_authors'] > 0:
            print(f"  Total authors: {len(author_names)}")
            print(f"  Avg authors per node: {metadata.get('avg_authors_per_node', 0):.2f}")

        return graph, node_types, node_to_authors, metadata

    def _assign_node_types(self) -> np.ndarray:
        """Assign type to each node based on proportions."""
        node_types = np.random.choice(
            self.config['num_types'],
            size=self.config['n_nodes'],
            p=self.config['type_proportions']
        )
        return node_types

    def _assign_communities(self) -> np.ndarray:
        """Assign each node to a community."""
        # Distribute nodes evenly across communities
        node_communities = np.random.randint(
            0, self.config['n_communities'],
            size=self.config['n_nodes']
        )
        return node_communities

    def _assign_hierarchy_levels(self) -> np.ndarray:
        """Assign hierarchical level to each node."""
        levels = np.random.randint(
            0, self.config['hierarchy_levels'],
            size=self.config['n_nodes']
        )
        return levels

    def _generate_authors(self) -> Tuple[Dict[int, List[int]], Dict[int, str]]:
        """
        Generate authors with realistic productivity patterns.

        Uses power-law distribution for author productivity:
        - Few highly productive authors (many papers)
        - Many authors with few papers

        Returns:
            Tuple of (node_to_authors, author_names):
                - node_to_authors: Dict mapping node_id -> list of author_ids
                - author_names: Dict mapping author_id -> author name
        """
        n_authors = self.config['n_authors']

        if n_authors == 0:
            return {}, {}

        # Generate author names
        author_names = {
            i: f"Author_{i:04d}"
            for i in range(n_authors)
        }

        # Generate authorship using power-law productivity distribution
        # Some authors are highly productive, most have few papers

        # Sample number of authors per node from Poisson-like distribution
        avg_authors = self.config['avg_authors_per_node']
        node_to_authors = {}

        # Track author productivity for power-law distribution
        author_paper_counts = np.zeros(n_authors)

        for node_id in range(self.config['n_nodes']):
            # Number of authors for this node (1 to 10, centered around avg)
            n_authors_for_node = int(np.random.gamma(
                shape=avg_authors,
                scale=1.0
            ))
            n_authors_for_node = max(1, min(10, n_authors_for_node))

            # Select authors using preferential attachment (productive authors more likely)
            # This creates power-law productivity distribution
            if np.sum(author_paper_counts) == 0:
                # First paper - random selection
                selected_authors = np.random.choice(
                    n_authors,
                    size=n_authors_for_node,
                    replace=False
                )
            else:
                # Preferential attachment: productive authors more likely
                # Add 1 to avoid zero probabilities
                probs = (author_paper_counts + 1) ** (-self.config['author_productivity_exponent'])
                probs /= probs.sum()

                selected_authors = np.random.choice(
                    n_authors,
                    size=n_authors_for_node,
                    replace=False,
                    p=probs
                )

            node_to_authors[node_id] = list(selected_authors)

            # Update productivity counts
            for author_id in selected_authors:
                author_paper_counts[author_id] += 1

        return node_to_authors, author_names

    def _generate_edges(self,
                       node_types: np.ndarray,
                       node_communities: np.ndarray,
                       temporal_order: np.ndarray,
                       node_levels: np.ndarray) -> Tuple[Graph, Dict]:
        """
        Generate edges with realistic citation patterns.

        Combines multiple mechanisms:
        1. Preferential attachment (power-law in-degree)
        2. Community structure
        3. Transitivity
        4. Type-specific preferences
        5. Hierarchical bias
        """
        graph = Graph(is_directed=True)

        # Add all nodes
        for i in range(self.config['n_nodes']):
            graph.add_node(i)

        # Track edges by generation mechanism
        edges_by_mechanism = {
            'preferential': 0,
            'community': 0,
            'transitive': 0,
            'type_preference': 0,
            'hierarchical': 0
        }

        # Track in-degrees for preferential attachment
        in_degrees = np.zeros(self.config['n_nodes'])

        # Generate out-degrees from exponential distribution
        out_degrees = self._sample_out_degrees()

        # For each node, generate its citations
        for source in range(self.config['n_nodes']):
            n_citations = out_degrees[source]

            if n_citations == 0:
                continue

            # Get valid targets (only earlier nodes - DAG property)
            valid_targets = list(range(source))  # Can only cite earlier papers

            if not valid_targets:
                continue

            # Generate citations using mixed strategy
            targets = self._select_citation_targets(
                source, n_citations, valid_targets,
                node_types, node_communities, node_levels,
                in_degrees, graph, edges_by_mechanism
            )

            # Add edges
            for target in targets:
                if not graph.get_neighbors(source) or target not in graph.get_neighbors(source):
                    graph.add_edge(source, target)
                    in_degrees[target] += 1

        return graph, edges_by_mechanism

    def _sample_out_degrees(self) -> np.ndarray:
        """Sample out-degrees from exponential distribution."""
        # Exponential distribution with mean = avg_out_degree
        scale = self.config['avg_out_degree']
        out_degrees = np.random.exponential(scale, size=self.config['n_nodes'])

        # Round to integers
        out_degrees = np.round(out_degrees).astype(int)

        # Clip to reasonable range
        out_degrees = np.clip(out_degrees, 0, min(50, self.config['n_nodes'] // 10))

        return out_degrees

    def _select_citation_targets(self,
                                source: int,
                                n_citations: int,
                                valid_targets: List[int],
                                node_types: np.ndarray,
                                node_communities: np.ndarray,
                                node_levels: np.ndarray,
                                in_degrees: np.ndarray,
                                graph: Graph,
                                edges_by_mechanism: Dict) -> Set[int]:
        """
        Select citation targets using multiple mechanisms.
        """
        selected = set()
        n_valid = len(valid_targets)

        # Limit citations to available targets
        n_citations = min(n_citations, n_valid)

        source_type = node_types[source]
        source_community = node_communities[source]
        source_level = node_levels[source]

        while len(selected) < n_citations and len(selected) < n_valid:
            # Choose mechanism probabilistically
            mechanism = np.random.choice(
                ['preferential', 'community', 'transitive', 'type', 'hierarchical'],
                p=[0.3, 0.25, 0.2, 0.15, 0.1]
            )

            target = None

            if mechanism == 'preferential':
                # Preferential attachment (power-law in-degree)
                target = self._select_preferential(valid_targets, in_degrees, selected)
                if target is not None:
                    edges_by_mechanism['preferential'] += 1

            elif mechanism == 'community':
                # Community-based selection
                target = self._select_community(
                    valid_targets, node_communities, source_community, selected
                )
                if target is not None:
                    edges_by_mechanism['community'] += 1

            elif mechanism == 'transitive':
                # Transitive closure (triangles)
                target = self._select_transitive(source, valid_targets, graph, selected)
                if target is not None:
                    edges_by_mechanism['transitive'] += 1

            elif mechanism == 'type':
                # Type preference
                target = self._select_by_type(
                    valid_targets, node_types, source_type, selected
                )
                if target is not None:
                    edges_by_mechanism['type_preference'] += 1

            elif mechanism == 'hierarchical':
                # Hierarchical bias (cite higher levels)
                target = self._select_hierarchical(
                    valid_targets, node_levels, source_level, selected
                )
                if target is not None:
                    edges_by_mechanism['hierarchical'] += 1

            if target is not None:
                selected.add(target)

        return selected

    def _select_preferential(self,
                            valid_targets: List[int],
                            in_degrees: np.ndarray,
                            selected: Set[int]) -> Optional[int]:
        """Select target using preferential attachment (power-law)."""
        available = [t for t in valid_targets if t not in selected]
        if not available:
            return None

        # Add 1 to avoid zero probabilities; higher in-degree => higher probability
        degrees = in_degrees[available] + 1.0

        # Apply power-law preference with positive exponent (alpha > 0)
        alpha = max(0.0, float(self.config['powerlaw_exponent']))
        # Normalize degrees^alpha
        weights = degrees ** alpha
        total = weights.sum()
        if total <= 0:
            # Fallback to uniform if something goes wrong
            return np.random.choice(available)
        probs = weights / total

        target = np.random.choice(available, p=probs)
        return target

    def _select_community(self,
                         valid_targets: List[int],
                         node_communities: np.ndarray,
                         source_community: int,
                         selected: Set[int]) -> Optional[int]:
        """Select target preferring same community."""
        available = [t for t in valid_targets if t not in selected]
        if not available:
            return None

        same_community = [t for t in available if node_communities[t] == source_community]

        if same_community and np.random.rand() < self.config['within_community_prob']:
            return np.random.choice(same_community)
        else:
            return np.random.choice(available)

    def _select_transitive(self,
                          source: int,
                          valid_targets: List[int],
                          graph: Graph,
                          selected: Set[int]) -> Optional[int]:
        """Select target to form triangles (transitivity)."""
        available = [t for t in valid_targets if t not in selected]
        if not available:
            return None

        # Find nodes that source's neighbors cite (2-hop neighbors)
        neighbors = graph.get_neighbors(source)
        two_hop = set()
        for neighbor in neighbors:
            two_hop.update(graph.get_neighbors(neighbor))

        # Candidates for triangle formation
        triangle_candidates = [t for t in available if t in two_hop]

        if triangle_candidates and np.random.rand() < self.config['transitivity_prob']:
            return np.random.choice(triangle_candidates)
        else:
            return np.random.choice(available) if available else None

    def _select_by_type(self,
                       valid_targets: List[int],
                       node_types: np.ndarray,
                       source_type: int,
                       selected: Set[int]) -> Optional[int]:
        """Select target based on type preferences."""
        available = [t for t in valid_targets if t not in selected]
        if not available:
            return None

        # Check if source type has preferences
        if source_type in self.config['type_citation_preferences']:
            prefs = self.config['type_citation_preferences'][source_type]

            # Compute weights for available targets
            weights = np.array([
                prefs.get(node_types[t], 1.0) for t in available
            ])
            weights /= weights.sum()

            return np.random.choice(available, p=weights)
        else:
            return np.random.choice(available)

    def _select_hierarchical(self,
                           valid_targets: List[int],
                           node_levels: np.ndarray,
                           source_level: int,
                           selected: Set[int]) -> Optional[int]:
        """Select target with hierarchical bias (cite higher levels)."""
        available = [t for t in valid_targets if t not in selected]
        if not available:
            return None

        # Bias towards higher levels (lower level numbers)
        level_diff = source_level - node_levels[available]

        # Compute weights: higher weight for higher levels
        weights = np.exp(self.config['level_bias'] * level_diff)
        weights /= weights.sum()

        return np.random.choice(available, p=weights)

    def _compute_metadata(self,
                         graph: Graph,
                         node_types: np.ndarray,
                         node_communities: np.ndarray,
                         edges_by_mechanism: Dict,
                         node_to_authors: Dict = None) -> Dict:
        """Compute statistics about the generated graph."""
        n = self.config['n_nodes']
        edges = graph.edges()
        n_edges = len(edges)

        # Degree distributions
        in_degrees = np.zeros(n)
        out_degrees = np.zeros(n)

        for source, target in edges:
            out_degrees[source] += 1
            in_degrees[target] += 1

        # Transitivity (clustering coefficient)
        transitivity = self._compute_transitivity(graph)

        # Type distribution
        type_counts = {}
        for i in range(self.config['num_types']):
            count = np.sum(node_types == i)
            type_counts[self.config['type_names'][i]] = int(count)

        metadata = {
            'n_nodes': n,
            'n_edges': n_edges,
            'avg_in_degree': float(np.mean(in_degrees)),
            'avg_out_degree': float(np.mean(out_degrees)),
            'max_in_degree': int(np.max(in_degrees)),
            'max_out_degree': int(np.max(out_degrees)),
            'transitivity': float(transitivity),
            'type_distribution': type_counts,
            'edges_by_mechanism': edges_by_mechanism,
            'config': {
                'n_communities': self.config['n_communities'],
                'powerlaw_exponent': self.config['powerlaw_exponent'],
                'transitivity_prob': self.config['transitivity_prob'],
                'within_community_prob': self.config['within_community_prob']
            }
        }

        # Add author statistics if authors were generated
        if node_to_authors and len(node_to_authors) > 0:
            n_authors = self.config['n_authors']
            nodes_with_authors = len([n for n, a in node_to_authors.items() if len(a) > 0])
            total_authorships = sum(len(a) for a in node_to_authors.values())
            avg_authors_per_node = total_authorships / max(1, nodes_with_authors)

            # Author productivity distribution
            author_paper_counts = np.zeros(n_authors)
            for authors in node_to_authors.values():
                for author_id in authors:
                    author_paper_counts[author_id] += 1

            metadata['n_authors'] = n_authors
            metadata['nodes_with_authors'] = nodes_with_authors
            metadata['avg_authors_per_node'] = float(avg_authors_per_node)
            metadata['max_papers_per_author'] = int(np.max(author_paper_counts))
            metadata['avg_papers_per_author'] = float(np.mean(author_paper_counts[author_paper_counts > 0]))

        return metadata

    def _compute_transitivity(self, graph: Graph) -> float:
        """Compute global transitivity (clustering coefficient)."""
        triangles = 0
        triples = 0

        nodes = graph.nodes()

        for node in nodes:
            neighbors = list(graph.get_neighbors(node))
            k = len(neighbors)

            if k < 2:
                continue

            # Count triangles
            for i in range(k):
                for j in range(i + 1, k):
                    if neighbors[j] in graph.get_neighbors(neighbors[i]):
                        triangles += 1

            # Count triples
            triples += k * (k - 1) // 2

        return triangles / triples if triples > 0 else 0.0

    def save_to_files(self,
                     graph: Graph,
                     node_types: np.ndarray,
                     node_to_authors: Dict,
                     metadata: Dict):
        """
        Save generated graph to files compatible with credit transfer framework.
        """
        import os

        output_dir = self.config['output_dir']
        prefix = self.config['output_prefix']

        os.makedirs(output_dir, exist_ok=True)

        print(f"\nSaving graph to {output_dir}/")

        # New: Edgelist (preferred for large graphs)
        edges_file = os.path.join(output_dir, f'{prefix}_edges.txt')
        with open(edges_file, 'w') as f:
            f.write("# Edgelist: one 'source target' per line\n")
            f.write("# Directed edges: source -> target\n")
            for src, tgt in graph.edges():
                f.write(f"{src} {tgt}\n")
        print(f"  Saved: {edges_file}")

        # Dense adjacency matrix (optional, controlled by config)
        if self.config.get('save_dense_adjacency', True):
            nodes, matrix = graph.to_matrix()
            adj_file = os.path.join(output_dir, f'{prefix}_adjacency.txt')
            with open(adj_file, 'w') as f:
                f.write("# Synthetic Citation Graph - Adjacency Matrix\n")
                f.write(f"# Nodes: {self.config['n_nodes']}\n")
                f.write(f"# Edges: {len(graph.edges())}\n")
                f.write("#\n")
                for row in matrix:
                    f.write(' '.join(map(str, row)) + '\n')
            print(f"  Saved: {adj_file}")
        else:
            print("  Skipped: dense adjacency matrix (save_dense_adjacency=false)")

        # 2. Node types
        types_file = os.path.join(output_dir, f'{prefix}_node_types.txt')
        with open(types_file, 'w') as f:
            f.write("# Node Types\n")
            f.write("# Format: node_id node_type\n")
            f.write("#\n")
            for i, node_type in enumerate(node_types):
                f.write(f"{i} {node_type}\n")

        print(f"  Saved: {types_file}")

        # 3. Node labels
        labels_file = os.path.join(output_dir, f'{prefix}_node_labels.txt')
        with open(labels_file, 'w') as f:
            f.write("# Node Labels\n")
            f.write("# Format: internal_id\n")
            f.write("#\n")
            for i in range(self.config['n_nodes']):
                f.write(f"{i}\n")

        print(f"  Saved: {labels_file}")

        # 4. Authors (if generated)
        if node_to_authors and len(node_to_authors) > 0:
            authors_file = os.path.join(output_dir, f'{prefix}_authors.txt')
            with open(authors_file, 'w') as f:
                f.write("# Node to Authors Mapping\n")
                f.write("# Format: node_id author_id1 author_id2 ...\n")
                f.write("#\n")
                for node_id in sorted(node_to_authors.keys()):
                    if len(node_to_authors[node_id]) > 0:
                        author_ids = ' '.join(map(str, node_to_authors[node_id]))
                        f.write(f"{node_id} {author_ids}\n")

            print(f"  Saved: {authors_file}")

            # 5. Author names
            if 'n_authors' in metadata and metadata['n_authors'] > 0:
                author_names_file = os.path.join(output_dir, f'{prefix}_author_names.txt')
                with open(author_names_file, 'w') as f:
                    f.write("# Author Names\n")
                    f.write("# Format: author_id author_name\n")
                    f.write("#\n")
                    for author_id in range(metadata['n_authors']):
                        f.write(f"{author_id} Author_{author_id:04d}\n")

                print(f"  Saved: {author_names_file}")

        # 6. Metadata
        metadata_file = os.path.join(output_dir, f'{prefix}_metadata.json')
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)

        print(f"  Saved: {metadata_file}")

        print(f"\nGeneration complete! Files saved to {output_dir}/")


def main():
    """Main entry point for synthetic graph generation."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python generate_synthetic_graph.py <config_file>")
        print("\nExample: python generate_synthetic_graph.py config/synthetic_citation.properties")
        sys.exit(1)

    config_file = sys.argv[1]

    # Generate graph
    generator = SyntheticCitationGraphGenerator(config_file)
    graph, node_types, node_to_authors, metadata = generator.generate()

    # Save to files
    generator.save_to_files(graph, node_types, node_to_authors, metadata)

    print("\n" + "="*80)
    print("SYNTHETIC GRAPH GENERATION COMPLETE")
    print("="*80)
    print(f"\nTo run credit transfer on this graph:")
    print(f"  python3 creditRunner.py config/run_synthetic.properties")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
