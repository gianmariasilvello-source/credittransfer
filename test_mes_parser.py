"""
Test script for revised MESProcessor with id-based author mapping.
"""

import sys
sys.path.insert(0, '/Users/gianmariasilvello/PycharmProjects/CreditTransferProject')

from dataprocessing.MESProcessor import MESDataParser

print("Testing revised MESProcessor with id-based author mapping...")
print("=" * 80)

# Initialize parser with curated MES data
parser = MESDataParser(
    publications_file='source_graph_data/curated_MES/publications.jsonl',
    datasets_file='source_graph_data/curated_MES/datasets.jsonl',
    software_file='source_graph_data/curated_MES/software.jsonl',
    authors_file='source_graph_data/curated_MES/authors.jsonl',
    relations_file='source_graph_data/curated_MES/relations.jsonl'
)

print("\nParsing all data files...")
try:
    graph, node_types, node_to_authors, author_names = parser.parse_all()

    # Print summary
    parser.print_summary()

    # Show sample author mappings
    print("\n" + "=" * 80)
    print("SAMPLE AUTHOR MAPPINGS")
    print("=" * 80)

    sample_count = 0
    for node_id, author_ids in list(node_to_authors.items())[:10]:
        node_info = parser.nodes.get(node_id, {})
        node_type = node_info.get('type', 'unknown')
        title = node_info.get('title', 'N/A')[:50]

        print(f"\nNode {node_id} ({node_type}): {title}")
        print(f"  Authors ({len(author_ids)}):")
        for author_id in author_ids[:5]:  # Show first 5 authors
            author_name = author_names.get(author_id, 'Unknown')
            print(f"    - {author_id}: {author_name}")
        if len(author_ids) > 5:
            print(f"    ... and {len(author_ids) - 5} more")

        sample_count += 1
        if sample_count >= 5:
            break

    # Show some author details
    print("\n" + "=" * 80)
    print("SAMPLE AUTHOR DETAILS")
    print("=" * 80)

    for author_id, name in list(author_names.items())[:20]:
        print(f"  {author_id}: {name}")

    print("\n" + "=" * 80)
    print("PARSING SUCCESSFUL!")
    print("=" * 80)

except Exception as e:
    print(f"\nERROR: {str(e)}")
    import traceback
    traceback.print_exc()

