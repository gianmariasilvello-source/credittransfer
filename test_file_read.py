import json
import sys

print("Testing file reading...")

authors_file = 'source_graph_data/curated_MES/authors.jsonl'
relations_file = 'source_graph_data/curated_MES/relations.jsonl'

try:
    with open(authors_file, 'r') as f:
        lines = [line.strip() for line in f if line.strip()]
        print(f"Authors file: {len(lines)} lines")
        if lines:
            first = json.loads(lines[0])
            print(f"First entry keys: {list(first.keys())}")
            print(f"First entry sample: {str(first)[:200]}")
except Exception as e:
    print(f"Error reading authors: {e}")

try:
    with open(relations_file, 'r') as f:
        lines = [line.strip() for line in f if line.strip()]
        print(f"\nRelations file: {len(lines)} lines")

        # Count HasAuthor relations
        hasauthor_count = 0
        for line in lines[:100]:  # Check first 100
            try:
                obj = json.loads(line)
                if obj.get('semantics') == 'HasAuthor':
                    hasauthor_count += 1
                    if hasauthor_count == 1:
                        print(f"First HasAuthor: {str(obj)[:300]}")
            except:
                pass
        print(f"HasAuthor relations in first 100: {hasauthor_count}")
except Exception as e:
    print(f"Error reading relations: {e}")

