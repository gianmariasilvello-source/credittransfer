"""
Data Parser for Research Dataset with Multiple Node Types and Relationships

Parses publications, datasets, software, authors, and various relationship types
into a format compatible with GeneralCreditTransfer.
"""

import json
import numpy as np
from typing import Dict, List, Tuple, Set, Optional
from collections import defaultdict
from graph.GraphUtils import Graph


class MESDataParser:
    """
    Parse the curated MES research dataset with papers, datasets, software, and complex relationships.

    Handles multiple semantic relationship types and author associations.
    """

    # Node type codes
    TYPE_PAPER = 0
    TYPE_DATASET = 1
    TYPE_SOFTWARE = 2

    # Relationship semantics that create edges FROM object TO subject
    OBJECT_TO_SUBJECT = {
        'IsReferencedBy',  # paper A IsReferencedBy paper B -> B references A -> edge B->A
        'IsSupplementedBy',  # dataset A IsSupplementedBy paper B -> B supplements A -> edge B->A
        'isPartOf',  # dataset A isPartOf paper B -> A is part of B -> edge B->A
        'isCitedBy'  # dataset A isCitedBy paper B -> B cites A -> edge B->A
    }

    # Relationship semantics that create edges FROM subject TO object
    SUBJECT_TO_OBJECT = {
        'references',  # paper A references paper B -> edge A->B
        'cites',  # paper A cites dataset B -> edge A->B
        'documents',  # paper A documents dataset B -> edge A->B
        'IsSupplementTo'  # paper A IsSupplementTo dataset B -> edge A->B
    }

    def __init__(self,
                 publications_file: str,
                 datasets_file: str,
                 software_file: Optional[str] = None,
                 authors_file: Optional[str] = None,
                 relations_file: Optional[str] = None):
        """
        Initialize parser with data file paths.

        Args:
            publications_file: JSON file with paper nodes
            datasets_file: JSON file with dataset nodes
            software_file: Optional JSON file with software nodes
            authors_file: Optional JSON file with author mappings
            relations_file: Optional JSON file with relationships
        """
        self.publications_file = publications_file
        self.datasets_file = datasets_file
        self.software_file = software_file
        self.authors_file = authors_file
        self.relations_file = relations_file

        # Parsed data
        self.nodes = {}  # node_id -> {type, pid, fullname, title, etc.}
        self.node_types = {}  # node_id -> type_code
        self.authors = defaultdict(list)  # node_id -> [author_ids]
        self.author_names = {}  # author_id -> name
        self.edges = set()  # (source, target) tuples

        # ID mappings
        self.node_id_counter = 0
        self.author_id_counter = 0
        self.external_to_internal_node = {}  # external_id -> internal_id
        self.external_to_internal_author = {}  # external_author_id -> internal_id

    def _get_or_create_node_id(self, external_id: str, node_type: int) -> int:
        """Get or create internal node ID for external ID."""
        if external_id not in self.external_to_internal_node:
            internal_id = self.node_id_counter
            self.external_to_internal_node[external_id] = internal_id
            self.node_types[internal_id] = node_type
            self.node_id_counter += 1
            return internal_id
        return self.external_to_internal_node[external_id]

    def _get_or_create_author_id(self, external_author_id: str, author_name: str) -> int:
        """Get or create internal author ID."""
        if external_author_id not in self.external_to_internal_author:
            internal_id = self.author_id_counter
            self.external_to_internal_author[external_author_id] = internal_id
            self.author_names[internal_id] = author_name
            self.author_id_counter += 1
            return internal_id
        return self.external_to_internal_author[external_author_id]

    def parse_all(self) -> Tuple[Graph, np.ndarray, Dict[int, List[int]], Dict[int, str]]:
        """
        Parse all data files and build graph structure.

        Returns:
            Tuple of (graph, node_types_array, node_to_authors, author_names):
                - graph: Graph object with citation edges
                - node_types_array: numpy array of node type codes
                - node_to_authors: dict mapping node_id -> [author_ids]
                - author_names: dict mapping author_id -> name
        """
        # Parse nodes
        self._parse_publications()
        self._parse_datasets()
        if self.software_file:
            self._parse_software()

        # Parse authors FIRST to load author ID to name mappings
        # This must happen before parsing relations so HasAuthor processing can use real names
        if self.authors_file:
            self._parse_authors()

        # Parse relationships (including HasAuthor)
        if self.relations_file:
            self._parse_relations()

        # Build graph
        graph = Graph(is_directed=True)
        for node_id in range(self.node_id_counter):
            graph.add_node(node_id)

        for source, target in self.edges:
            graph.add_edge(source, target)

        # Build node types array
        node_types_array = np.array([
            self.node_types[i] for i in range(self.node_id_counter)
        ], dtype=np.int32)

        return graph, node_types_array, dict(self.authors), self.author_names

    def _parse_publications(self):
        """Parse publications/papers file."""
        with open(self.publications_file, 'r') as f:
            if self.publications_file.endswith('.jsonl'):
                data = [json.loads(line) for line in f if line.strip()]
            else:
                data = json.load(f)

        for item in data:
            external_id = item.get('pid') or item.get('id')
            if not external_id:
                continue

            internal_id = self._get_or_create_node_id(external_id, self.TYPE_PAPER)
            self.nodes[internal_id] = {
                'type': 'paper',
                'external_id': external_id,
                'title': item.get('title', ''),
                'fullname': item.get('fullname', ''),
                'raw': item
            }

    def _parse_datasets(self):
        """Parse datasets file."""
        with open(self.datasets_file, 'r') as f:
            if self.datasets_file.endswith('.jsonl'):
                data = [json.loads(line) for line in f if line.strip()]
            else:
                data = json.load(f)

        for item in data:
            external_id = item.get('pid') or item.get('id')
            if not external_id:
                continue

            internal_id = self._get_or_create_node_id(external_id, self.TYPE_DATASET)
            self.nodes[internal_id] = {
                'type': 'dataset',
                'external_id': external_id,
                'title': item.get('title', ''),
                'fullname': item.get('fullname', ''),
                'raw': item
            }

    def _parse_software(self):
        """Parse software file."""
        with open(self.software_file, 'r') as f:
            if self.software_file.endswith('.jsonl'):
                data = [json.loads(line) for line in f if line.strip()]
            else:
                data = json.load(f)

        for item in data:
            external_id = item.get('pid') or item.get('id')
            if not external_id:
                continue

            internal_id = self._get_or_create_node_id(external_id, self.TYPE_SOFTWARE)
            self.nodes[internal_id] = {
                'type': 'software',
                'external_id': external_id,
                'title': item.get('title', ''),
                'fullname': item.get('fullname', ''),
                'raw': item
            }

    def _parse_relations(self):
        """
        Parse relationships file and create edges.

        Handles two types of relations:
        1. Citation/reference relations → create graph edges
        2. HasAuthor relations → build node-to-authors mapping

        Relations use either:
        - Old format: subject/object fields (nested objects with pid/id)
        - New format: source/target fields (direct string IDs)
        """
        if not self.relations_file:
            return

        # Load relations.jsonl as JSONL format (one JSON object per line)
        with open(self.relations_file, 'r') as f:
            if self.relations_file.endswith('.jsonl'):
                relations_data = [json.loads(line) for line in f if line.strip()]
            else:
                relations_data = json.load(f)

        for rel in relations_data:
            semantic = rel.get('semantics')
            if not semantic:
                continue

            # Handle HasAuthor relations separately (build node-to-authors mapping)
            if semantic == 'HasAuthor':
                self._process_hasauthor_relation(rel)
                continue

            # Handle citation/reference relations (build graph edges)
            # Extract IDs - support both old format (subject/object) and new format (source/target)
            if 'source' in rel and 'target' in rel:
                # New format: direct string IDs
                subject_id = rel.get('source')
                object_id = rel.get('target')
            else:
                # Old format: nested objects
                subject_id = rel.get('subject', {}).get('pid') or rel.get('subject', {}).get('id')
                object_id = rel.get('object', {}).get('pid') or rel.get('object', {}).get('id')

            if not subject_id or not object_id:
                continue

            # Check if nodes exist
            if subject_id not in self.external_to_internal_node:
                continue
            if object_id not in self.external_to_internal_node:
                continue

            subj_internal = self.external_to_internal_node[subject_id]
            obj_internal = self.external_to_internal_node[object_id]

            # Determine edge direction based on semantics
            if semantic in self.OBJECT_TO_SUBJECT:
                # Edge from object to subject
                self.edges.add((obj_internal, subj_internal))
            elif semantic in self.SUBJECT_TO_OBJECT:
                # Edge from subject to object
                self.edges.add((subj_internal, obj_internal))
            elif semantic == 'IsDocumentedBy':
                # Special case: reverse direction
                self.edges.add((obj_internal, subj_internal))

    def _process_hasauthor_relation(self, rel: Dict):
        """
        Process a single HasAuthor relation to build node-to-authors mapping.

        HasAuthor relation format:
        {
            "source": "node_id",      # publication/dataset/software ID
            "target": "author_id",    # author ID (matches id field in authors.jsonl)
            "semantics": "HasAuthor",
            "rank": "1"               # optional author ordering
        }
        """
        # Extract node ID and author ID
        node_id = rel.get('source')
        author_id = rel.get('target')

        if not node_id or not author_id:
            return

        # Check if node exists in our graph
        if node_id not in self.external_to_internal_node:
            return

        internal_node_id = self.external_to_internal_node[node_id]

        # Convert author_id to string and get/create internal author ID
        author_id_str = str(author_id)

        # Get internal author ID (will use existing if already created from authors file)
        # If author wasn't in authors.jsonl, create with "Unknown" name
        internal_author_id = self._get_or_create_author_id(author_id_str, "Unknown")

        # Add to node-to-authors mapping
        self.authors[internal_node_id].append(internal_author_id)

    def _parse_authors(self):
        """
        Parse authors file to build author ID to name mapping.

        The authors.jsonl file contains author records with:
        - id: unique author identifier (used in HasAuthor relations)
        - fullname: author's full name
        - name, surname: author name components
        - pid: list of external identifiers (ORCID, Microsoft Academic, etc.)

        Note: Actual node-to-author mappings are extracted from HasAuthor relations
        in relations.jsonl, not from this file.
        """
        if not self.authors_file:
            return

        # Load authors.jsonl as JSONL format (one JSON object per line)
        with open(self.authors_file, 'r') as f:
            if self.authors_file.endswith('.jsonl'):
                authors_data = [json.loads(line) for line in f if line.strip()]
            else:
                authors_data = json.load(f)

        # Build mapping from author id to author information
        for entry in authors_data:
            author_id = entry.get('id')
            if not author_id:
                # If no id field, this might be old format - skip or warn
                continue

            # Get author name (prefer fullname, fallback to constructed name)
            fullname = entry.get('fullname', '')
            if not fullname:
                name = entry.get('name', '')
                surname = entry.get('surname', '')
                fullname = f"{surname}, {name}" if surname and name else (surname or name)

            # Convert author_id to string for consistency
            author_id_str = str(author_id)

            # Create internal author ID and store mapping
            internal_author_id = self._get_or_create_author_id(author_id_str, fullname)

            # Store external PIDs if available for potential future use
            # (though we primarily use the id field for mapping)
            pids = entry.get('pid', [])
            if pids and not isinstance(pids, list):
                pids = [pids]

    def print_summary(self):
        """Print summary statistics of parsed data."""
        n_papers = sum(1 for t in self.node_types.values() if t == self.TYPE_PAPER)
        n_datasets = sum(1 for t in self.node_types.values() if t == self.TYPE_DATASET)
        n_software = sum(1 for t in self.node_types.values() if t == self.TYPE_SOFTWARE)

        print(f"\n{'=' * 80}")
        print(f"PARSED RESEARCH DATA SUMMARY")
        print(f"{'=' * 80}")
        print(f"Total nodes: {self.node_id_counter}")
        print(f"  Papers: {n_papers}")
        print(f"  Datasets: {n_datasets}")
        print(f"  Software: {n_software}")
        print(f"Total edges: {len(self.edges)}")
        print(f"Total authors: {self.author_id_counter}")
        print(f"Nodes with authors: {len(self.authors)}")

    def serialize_to_files(self, output_dir: str, prefix: str = 'mes') -> dict:
        """
        Serialize parsed MES data to text files for credit transfer experiments.

        Args:
            output_dir: Directory to save files
            prefix: Prefix for output filenames

        Returns:
            Dictionary with metadata about the serialized data
        """
        import os
        import json

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        print(f"\nSerializing data to {output_dir}/")

        # 1. Save adjacency matrix
        adjacency_file = os.path.join(output_dir, f'{prefix}_adjacency.txt')
        with open(adjacency_file, 'w') as f:
            f.write("# MES Citation Graph - Adjacency Matrix\n")
            f.write(f"# Nodes: {self.node_id_counter}\n")
            f.write(f"# Edges: {len(self.edges)}\n")
            f.write("#\n")

            # Build adjacency matrix
            matrix = [[0] * self.node_id_counter for _ in range(self.node_id_counter)]
            for src, tgt in self.edges:
                matrix[src][tgt] = 1

            # Write matrix
            for row in matrix:
                f.write(' '.join(map(str, row)) + '\n')

        print(f"  Saved adjacency matrix: {adjacency_file} ({os.path.getsize(adjacency_file) / (1024 * 1024):.2f} MB)")

        # 2. Save node types
        node_types_file = os.path.join(output_dir, f'{prefix}_node_types.txt')
        with open(node_types_file, 'w') as f:
            f.write("# Node Types (0=paper, 1=dataset, 2=software)\n")
            f.write("# Format: node_id node_type\n")
            f.write("#\n")

            for node_id in range(self.node_id_counter):
                node_type = self.node_types[node_id]
                f.write(f"{node_id} {node_type}\n")

        print(f"  Saved node types: {node_types_file}")

        # 3. Save node labels (internal ID to external ID mapping)
        node_labels_file = os.path.join(output_dir, f'{prefix}_node_labels.txt')
        with open(node_labels_file, 'w') as f:
            f.write("# Node ID Mapping\n")
            f.write("# Format: internal_id\n")
            f.write("#\n")

            for node_id in range(self.node_id_counter):
                f.write(f"{node_id}\n")

        print(f"  Saved node labels: {node_labels_file}")

        # 4. Save authorship data
        authors_file = os.path.join(output_dir, f'{prefix}_authors.txt')
        with open(authors_file, 'w') as f:
            f.write("# Node to Authors Mapping\n")
            f.write("# Format: node_id author_id1 author_id2 ...\n")
            f.write("#\n")

            for node_id in sorted(self.authors.keys()):
                author_ids = ' '.join(map(str, self.authors[node_id]))
                f.write(f"{node_id} {author_ids}\n")

        print(f"  Saved authorship data: {authors_file}")

        # 5. Save author names
        author_names_file = os.path.join(output_dir, f'{prefix}_author_names.txt')
        with open(author_names_file, 'w') as f:
            f.write("# Author Names\n")
            f.write("# Format: author_id author_name\n")
            f.write("#\n")

            for author_id in sorted(self.author_names.keys()):
                author_name = self.author_names[author_id]
                f.write(f"{author_id} {author_name}\n")

        print(f"  Saved author names: {author_names_file}")

        # 6. Save metadata
        n_papers = sum(1 for t in self.node_types.values() if t == self.TYPE_PAPER)
        n_datasets = sum(1 for t in self.node_types.values() if t == self.TYPE_DATASET)
        n_software = sum(1 for t in self.node_types.values() if t == self.TYPE_SOFTWARE)

        metadata = {
            'dataset': 'MES (Marine Ecosystem Studies)',
            'total_nodes': self.node_id_counter,
            'total_edges': len(self.edges),
            'total_authors': self.author_id_counter,
            'node_counts': {
                'papers': n_papers,
                'datasets': n_datasets,
                'software': n_software
            },
            'files': {
                'adjacency': os.path.basename(adjacency_file),
                'node_types': os.path.basename(node_types_file),
                'node_labels': os.path.basename(node_labels_file),
                'authors': os.path.basename(authors_file),
                'author_names': os.path.basename(author_names_file)
            }
        }

        metadata_file = os.path.join(output_dir, f'{prefix}_metadata.json')
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)

        print(f"  Saved metadata: {metadata_file}")
        print(f"\nSerialization complete!")

        return metadata

