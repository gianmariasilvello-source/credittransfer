# Synthetic Citation Graph Generator

Generate realistic citation networks with configurable properties for testing and analysis.

## Features

The generator creates citation networks with all the key properties observed in real citation networks:

### 1. **DAG Structure (Directed Acyclic Graph)**
- Papers can only cite papers published before them
- Enforces temporal ordering
- No citation cycles

### 2. **Power-Law In-Degree Distribution**
- Few highly-cited "landmark" papers
- Many papers with few citations
- Matches real-world citation patterns
- Configurable exponent (typically 2.0-3.0)

### 3. **Exponential Out-Degree Distribution**
- Variable number of references per paper
- Most papers cite a moderate number of references
- Some papers are comprehensive reviews with many citations

### 4. **Community Structure**
- Simulates research subfields
- Higher citation probability within communities
- Lower citation probability across communities
- Configurable number of communities

### 5. **Transitivity (Triangle Formation)**
- If A cites B and B cites C, higher probability that A cites C
- Creates realistic citation chains
- Configurable probability

### 6. **Hierarchical Structure**
- Papers at different hierarchical levels
- Foundational papers at higher levels
- Papers preferentially cite "upward" in hierarchy

### 7. **Multi-Type Nodes**
- Support for papers, datasets, software, etc.
- Different citation patterns per type
- Configurable proportions

## Quick Start

```bash
# Generate small test graph (100 nodes)
python3 generators/generate_synthetic_graph.py config/synthetic_small.properties

# Generate medium graph (1,000 nodes)
python3 generators/generate_synthetic_graph.py config/synthetic_citation.properties

# Generate large graph (10,000 nodes)
python3 generators/generate_synthetic_graph.py config/synthetic_large.properties

# Complete workflow (generate + analyze)
python3 run_synthetic_workflow.py
```

## Configuration

### Basic Parameters

```ini
[graph]
n_nodes = 1000  # Total number of nodes

[types]
num_types = 3
type_0_name = paper
type_0_proportion = 0.70
type_1_name = dataset
type_1_proportion = 0.25
type_2_name = software
type_2_proportion = 0.05
```

### Density Control

```ini
[density]
avg_out_degree = 15.0  # Average references per paper
density_variation = 0.2  # Variation in density
```

### In-Degree Distribution (Power-Law)

```ini
[indegree]
powerlaw_exponent = 2.5
# Lower values (1.5-2.0) = more inequality (few super-cited papers)
# Higher values (2.5-3.5) = more equal distribution
```

### Out-Degree Distribution (Exponential)

```ini
[outdegree]
exp_lambda = 0.3
# Controls variation in number of references
```

### Community Structure

```ini
[communities]
n_communities = 10  # Number of research subfields
within_community_prob = 0.6  # Probability of citing within community
between_community_prob = 0.4  # Probability of citing across communities
```

### Network Structure

```ini
[structure]
transitivity_prob = 0.3  # Probability of forming triangles
hierarchy_levels = 5  # Number of hierarchical levels
level_bias = 0.7  # Strength of upward citation bias
```

### Type-Specific Citation Patterns

```ini
[citation_preferences]
# Papers cite: mostly papers, some datasets, rarely software
type_0_cites = 0:1.0, 1:0.3, 2:0.1

# Datasets cite: mostly datasets, some papers
type_1_cites = 0:0.2, 1:1.0, 2:0.1

# Software cites: balanced
type_2_cites = 0:0.5, 1:0.5, 2:0.3
```

## Output Files

The generator creates files compatible with the credit transfer framework:

- `{prefix}_adjacency.txt` - Adjacency matrix (space-separated)
- `{prefix}_node_types.txt` - Node type assignments
- `{prefix}_node_labels.txt` - Node ID mappings
- `{prefix}_metadata.json` - Generation statistics

## Example Workflow

```bash
# 1. Generate graph
python3 generators/generate_synthetic_graph.py config/synthetic_citation.properties

# 2. Run credit transfer
python3 creditRunner.py config/run_synthetic.properties

# Or use the combined workflow
python3 run_synthetic_workflow.py
```

## Presets

### Small (100 nodes)
```bash
python3 generators/generate_synthetic_graph.py config/synthetic_small.properties
```
- Fast generation
- Good for testing
- 2 node types (papers, datasets)

### Medium (1,000 nodes)
```bash
python3 generators/generate_synthetic_graph.py config/synthetic_citation.properties
```
- Realistic scale
- 3 node types (papers, datasets, software)
- Good for experiments

### Large (10,000 nodes)
```bash
python3 generators/generate_synthetic_graph.py config/synthetic_large.properties
```
- Large-scale testing
- 25 communities
- More complex structure

## Validation

Run tests to verify the generator:

```bash
python3 test/test_synthetic_generator.py
```

Checks:
- DAG property (no back edges)
- Degree distributions
- Community structure
- Serialization

## Customization

Create your own configuration by copying and editing a preset:

```bash
cp config/synthetic_citation.properties config/my_graph.properties
# Edit my_graph.properties
python3 generators/generate_synthetic_graph.py config/my_graph.properties
```

## Generation Mechanisms

The generator uses multiple mechanisms simultaneously:

1. **Preferential Attachment (30%)** - Power-law in-degree
2. **Community-Based (25%)** - Within/across community citations
3. **Transitive (20%)** - Triangle formation
4. **Type Preference (15%)** - Type-specific patterns
5. **Hierarchical (10%)** - Upward citation bias

These percentages create realistic citation patterns that match observed networks.

## Use Cases

- **Testing credit transfer algorithms** on known structures
- **Benchmarking performance** on different graph sizes
- **Comparing retention strategies** across graph types
- **Understanding algorithm behavior** with controlled properties
- **Generating training data** for ML models
- **Simulating research networks** for analysis

## Tips

- Start with `synthetic_small.properties` for quick tests
- Adjust `powerlaw_exponent` to control citation inequality
- Increase `transitivity_prob` for tighter citation networks
- Use higher `within_community_prob` for more isolated subfields
- Set `seed` for reproducible graphs

---

**Date:** October 26, 2025

