"""
Analyze HasAuthor Relations - Check correspondence between relations and authors files.
"""

import json
from collections import defaultdict
from typing import Dict, Set, Tuple


def analyze_hasauthor_correspondence(
    authors_file: str,
    relations_file: str
) -> Dict[str, any]:
    """
    Analyze HasAuthor relations and check correspondence with authors file.

    Args:
        authors_file: Path to authors.json
        relations_file: Path to relations.json

    Returns:
        Dictionary with analysis results
    """
    print(f"Loading authors from: {authors_file}")
    # Load files (support both .json and .jsonl formats)
    with open(authors_file, 'r') as f:
        if authors_file.endswith('.jsonl'):
            authors_data = [json.loads(line) for line in f if line.strip()]
        else:
            authors_data = json.load(f)
    print(f"  Loaded {len(authors_data)} entries from authors file")

    print(f"Loading relations from: {relations_file}")
    with open(relations_file, 'r') as f:
        if relations_file.endswith('.jsonl'):
            relations_data = [json.loads(line) for line in f if line.strip()]
        else:
            relations_data = json.load(f)
    print(f"  Loaded {len(relations_data)} entries from relations file")

    # Extract HasAuthor relations from relations file
    hasauthor_relations = [
        rel for rel in relations_data
        if rel.get('semantics') == 'HasAuthor'
    ]
    print(f"  Found {len(hasauthor_relations)} HasAuthor relations")

    # Parse authors from authors file
    # The authors file contains individual author records with pid and fullname
    authors_from_file = set()
    author_pid_to_name = {}
    author_fullname_index = {}

    for entry in authors_data:
        # Extract author identification
        pids = entry.get('id', [])
        fullname = entry.get('fullname', '')

        # Handle pid as list or string
        if isinstance(pids, list):
            for pid in pids:
                if pid:
                    pid = str(pid)
                    authors_from_file.add(pid)
                    author_pid_to_name[pid] = fullname
        elif pids:
            pid = str(pids)
            authors_from_file.add(pid)
            author_pid_to_name[pid] = fullname

        # Also index by fullname for matching
        if fullname:
            author_fullname_index[fullname] = pids if isinstance(pids, list) else [pids]


    # Parse authors from HasAuthor relations
    # Relations use 'source' (node) and 'target' (author ID)
    authors_from_relations = set()
    nodes_in_relations = set()
    relation_author_details = defaultdict(list)
    nodes_in_authors_file = set()  # Not used with this data structure

    for rel in hasauthor_relations:
        # Extract node (source) and author (target)
        node_id = rel.get('source', '')
        author_id = rel.get('target', '')

        if node_id:
            node_id = str(node_id)
            nodes_in_relations.add(node_id)

        if author_id:
            author_id = str(author_id)
            authors_from_relations.add(author_id)

            # Get author name from the authors file if available
            author_name = author_pid_to_name.get(author_id, 'Unknown')

            relation_author_details[author_id].append({
                'node': node_id,
                'author_id': author_id,
                'fullname': author_name
            })

    # Compute statistics
    authors_only_in_file = authors_from_file - authors_from_relations
    authors_only_in_relations = authors_from_relations - authors_from_file
    authors_in_both = authors_from_file & authors_from_relations

    # Note: In this dataset, authors.jsonl is a list of all authors,
    # not a mapping of nodes to authors. The node information comes from relations.
    nodes_in_both = set()  # Not applicable
    nodes_only_in_file = set()  # Not applicable

    # Check for authors identified by different formats
    # Author IDs starting with 'a' followed by digits vs other formats
    authors_by_simple_id = sum(
        1 for key in authors_from_relations if key.startswith('a') and key[1:].isdigit()
    )
    authors_by_complex_id = len(authors_from_relations) - authors_by_simple_id

    return {
        'total_hasauthor_relations': len(hasauthor_relations),
        'authors_file_count': len(authors_from_file),
        'relations_hasauthor_count': len(authors_from_relations),
        'authors_in_both': len(authors_in_both),
        'authors_only_in_file': len(authors_only_in_file),
        'authors_only_in_relations': len(authors_only_in_relations),
        'nodes_in_relations': len(nodes_in_relations),
        'authors_by_simple_id': authors_by_simple_id,
        'authors_by_complex_id': authors_by_complex_id,
        'sample_authors_only_in_file': list(authors_only_in_file)[:10],
        'sample_authors_only_in_relations': list(authors_only_in_relations)[:10],
        'sample_nodes_in_relations': list(nodes_in_relations)[:10],
        'author_pid_to_name': author_pid_to_name,
        'relation_author_details': dict(relation_author_details)
    }


def print_correspondence_report(results: Dict):
    """Print formatted report of correspondence analysis."""
    print(f"\n{'='*80}")
    print("HASAUTHOR CORRESPONDENCE ANALYSIS")
    print(f"{'='*80}")

    print(f"\n{'Total HasAuthor Relations:':<40} {results['total_hasauthor_relations']:>10}")
    print(f"{'Unique nodes in relations:':<40} {results['nodes_in_relations']:>10}")

    print(f"\n{'AUTHOR CORRESPONDENCE':^80}")
    print(f"{'-'*80}")
    print(f"{'Authors in authors.jsonl:':<40} {results['authors_file_count']:>10}")
    print(f"{'Authors in HasAuthor relations:':<40} {results['relations_hasauthor_count']:>10}")
    print(f"{'Authors in BOTH:':<40} {results['authors_in_both']:>10}")
    print(f"{'Authors ONLY in file:':<40} {results['authors_only_in_file']:>10}")
    print(f"{'Authors ONLY in relations:':<40} {results['authors_only_in_relations']:>10}")

    print(f"\n{'AUTHOR IDENTIFICATION METHOD':^80}")
    print(f"{'-'*80}")
    print(f"{'Authors with simple ID (aXXXXX):':<40} {results['authors_by_simple_id']:>10}")
    print(f"{'Authors with complex/unknown ID:':<40} {results['authors_by_complex_id']:>10}")

    # Calculate correspondence percentages
    if results['authors_file_count'] > 0:
        pct_authors_in_both = (results['authors_in_both'] / results['authors_file_count']) * 100
        print(f"\n{'Authors overlap (file->relations):':<40} {pct_authors_in_both:>9.1f}%")

    if results['relations_hasauthor_count'] > 0:
        pct_relations_covered = (results['authors_in_both'] / results['relations_hasauthor_count']) * 100
        print(f"{'Authors overlap (relations->file):':<40} {pct_relations_covered:>9.1f}%")

    # Show samples
    if results['sample_authors_only_in_file']:
        print(f"\n{'Sample authors ONLY in file (first 10):'}")
        for author in results['sample_authors_only_in_file']:
            name = results['author_pid_to_name'].get(author, 'N/A')
            print(f"  {author[:50]:<50} | {name[:50]}")

    if results['sample_authors_only_in_relations']:
        print(f"\n{'Sample authors ONLY in relations (first 10):'}")
        for author in results['sample_authors_only_in_relations']:
            details = results['relation_author_details'].get(author, [{}])[0]
            fullname = details.get('fullname', 'Unknown')
            print(f"  {author[:50]:<50} | {fullname[:50]}")

    if results.get('sample_nodes_in_relations'):
        print(f"\n{'Sample nodes with authors (first 10):'}")
        for node in results['sample_nodes_in_relations']:
            print(f"  {node[:70]}")

    print(f"\n{'='*80}")


# Usage example
if __name__ == '__main__':
    import sys

    if len(sys.argv) < 3:
        print("Usage: python analyze_hasauthor.py <authors.json> <relations.json>")
        sys.exit(1)

    authors_file = sys.argv[1]
    relations_file = sys.argv[2]

    results = analyze_hasauthor_correspondence(authors_file, relations_file)
    print_correspondence_report(results)

    # Save detailed results to JSON
    output_file = "hasauthor_analysis.json"
    with open(output_file, 'w') as f:
        # Remove large dict for cleaner output
        results_to_save = {k: v for k, v in results.items()
                          if k not in ['author_pid_to_name', 'relation_author_details']}
        json.dump(results_to_save, f, indent=2)

    print(f"\nDetailed analysis saved to: {output_file}")
