"""
MES Experiment - Prepare Data

This script parses the MES (Marine Ecosystem Studies) dataset and serializes it
to files for credit transfer experiments.
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from dataprocessing.MESProcessor import MESDataParser


def prepare_mes_data():
    """Parse MES data and serialize to files."""

    print("\n" + "="*80)
    print("MES DATA PREPARATION")
    print("="*80 + "\n")

    # Define file paths
    data_dir = os.path.join(project_root, 'source_graph_data', 'curated_MES')
    output_dir = os.path.join(project_root, 'data', 'mes_experiment')

    # Initialize parser
    print("Initializing MES data parser...")
    parser = MESDataParser(
        publications_file=os.path.join(data_dir, 'publications.jsonl'),
        datasets_file=os.path.join(data_dir, 'datasets.jsonl'),
        software_file=os.path.join(data_dir, 'software.jsonl'),
        authors_file=os.path.join(data_dir, 'authors.jsonl'),
        relations_file=os.path.join(data_dir, 'relations.jsonl')
    )

    # Parse all data
    print("Parsing MES dataset...")
    graph, node_types, node_to_authors, author_names = parser.parse_all()

    # Print summary
    parser.print_summary()

    # Serialize to files
    metadata = parser.serialize_to_files(output_dir, prefix='mes')

    print("\nData preparation complete!")
    print(f"Serialized files are in: {output_dir}/")
    print("\nNext step: Run the experiment with run_mes_experiment.py")

    return metadata


if __name__ == "__main__":
    try:
        metadata = prepare_mes_data()
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

