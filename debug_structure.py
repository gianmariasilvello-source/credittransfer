"""Quick debug script to see structure of HasAuthor relations"""
import json

print("Checking structure of HasAuthor relations...")

with open('source_graph_data/curated_MES/relations.jsonl', 'r') as f:
    count = 0
    for line in f:
        if count >= 3:  # Only show first 3
            break
        obj = json.loads(line)
        if obj.get('semantics') == 'HasAuthor':
            print(f"\nHasAuthor relation #{count + 1}:")
            print(f"  source: {obj.get('source')}")
            print(f"  target: {obj.get('target')}")
            count += 1

print("\n" + "="*80)
print("Checking structure of authors file...")

with open('source_graph_data/curated_MES/authors.jsonl', 'r') as f:
    for i, line in enumerate(f):
        if i >= 5:  # Show first 5
            break
        obj = json.loads(line)
        print(f"\nAuthors entry #{i + 1}:")
        print(f"  Keys: {list(obj.keys())}")
        if 'id' in obj:
            print(f"  id: {obj.get('id')}")
            print(f"  fullname: {obj.get('fullname')}")
        else:
            print(f"  NO 'id' FIELD FOUND")
            print(f"  Sample: {json.dumps(obj, indent=2)[:300]}")


