# Quick Reference: Large-Scale Data from Nature Scientific Data Paper

**Processing multi-type citation graphs (papers, patents, clinical trials) from SQL databases**

---

## 📊 Understanding the Data Structures

This section explains **what** each data structure represents, **how** it's built, and **why** it's designed this way. Understanding these concepts will help you build your own implementations.

---

### 1. Node Types: Classification System

**Purpose:** Identify which type each node belongs to in a multi-type graph.

**Representation:** A simple array where each element corresponds to a node, and the value indicates its type.

```
Node Type Codes:
  0 = Paper (journal article, conference paper, preprint)
  1 = Patent (issued patents, patent applications)
  2 = Clinical Trial (registered clinical studies)
```

**Example with 7 nodes:**
```
Node IDs:        [   0,     1,     2,     3,     4,     5,     6   ]
Node Types:      [   0,     0,     1,     0,     2,     1,     0   ]
Interpretation:  Paper, Paper, Patent, Paper, Trial, Patent, Paper
```

**Why uint8?** Each type code fits in 0-255, so we only need 1 byte per node instead of 8 bytes (int64). For 10 million nodes, this saves 70 MB of memory!

**How to Build:**
1. Create an empty list or array
2. For each node in your database:
   - If it's from the `publications` table → append 0
   - If it's from the `patents` table → append 1
   - If it's from the `clinical_trials` table → append 2
3. Convert to numpy array with `dtype=uint8`

---

### 2. Adjacency Matrix: The Graph Structure

**Purpose:** Represent which nodes cite/reference which other nodes (the edges of the graph).

**Conceptual Representation:** A 2D matrix where:
- **Rows** represent the **source** nodes (who is citing)
- **Columns** represent the **target** nodes (who is being cited)
- **Value of 1** means "there is an edge from row to column"
- **Value of 0** means "no edge"

**Small Example (6 nodes):**

```
Citation relationships in words:
  - Paper 0 cites Paper 1
  - Paper 0 cites Patent 2
  - Paper 3 cites Paper 0
  - Paper 3 cites Paper 1
  - Patent 2 cites Paper 1
  - Clinical Trial 4 cites Paper 0

Dense matrix representation:
        Target Node
        0   1   2   3   4   5
    0 [ 0   1   1   0   0   0 ]  ← Node 0 cites nodes 1 and 2
S   1 [ 0   0   0   0   0   0 ]  ← Node 1 cites nothing
o   2 [ 0   1   0   0   0   0 ]  ← Node 2 cites node 1
u   3 [ 1   1   0   0   0   0 ]  ← Node 3 cites nodes 0 and 1
r   4 [ 1   0   0   0   0   0 ]  ← Node 4 cites node 0
c   5 [ 0   0   0   0   0   0 ]  ← Node 5 cites nothing
e
```

**Reading the Matrix:**
- `matrix[3][0] = 1` means: Node 3 → Node 0 (3 cites 0)
- `matrix[0][1] = 1` means: Node 0 → Node 1 (0 cites 1)
- `matrix[1][3] = 0` means: No edge from Node 1 to Node 3

**The Sparsity Problem:**

For 10 million nodes, a dense matrix would need:
```
10,000,000 × 10,000,000 = 100 trillion entries
100,000,000,000,000 bytes = 100 TB of memory! ❌
```

But in reality, a paper might cite only 20-30 other papers:
```
10,000,000 nodes × 25 citations each = 250 million edges
Only 250,000,000 entries actually have value 1
That's 0.00025% of the matrix! (99.99975% are zeros)
```

**Sparse Matrix Solution:**

Instead of storing all zeros, only store the non-zero entries:

```
Edge List Format (before creating sparse matrix):
  source_nodes = [0, 0, 2, 3, 3, 4]
  target_nodes = [1, 2, 1, 0, 1, 0]
  
This represents:
  0 → 1
  0 → 2
  2 → 1
  3 → 0
  3 → 1
  4 → 0
```

**CSR (Compressed Sparse Row) Format:**

The most efficient format for our use case. It stores three arrays:

1. **data**: The non-zero values (all 1s for unweighted graphs)
2. **indices**: Column index for each non-zero value
3. **indptr**: Where each row starts in the indices array

**Example CSR for our 6-node graph:**

```
data     = [1, 1, 1, 1, 1, 1]           # All edges have weight 1
indices  = [1, 2, 1, 0, 1, 0]           # Column positions
indptr   = [0, 2, 2, 3, 5, 6, 6]        # Row boundaries

Interpretation:
  Row 0: indices[0:2] = [1, 2]    → edges to nodes 1, 2
  Row 1: indices[2:2] = []        → no edges
  Row 2: indices[2:3] = [1]       → edge to node 1
  Row 3: indices[3:5] = [0, 1]    → edges to nodes 0, 1
  Row 4: indices[5:6] = [0]       → edge to node 0
  Row 5: indices[6:6] = []        → no edges
```

**Memory Comparison:**
```
Dense:  6 × 6 = 36 entries × 4 bytes = 144 bytes
Sparse: 6 edges × (4+4+1) bytes = 54 bytes
Savings: 62%

For 10M nodes with 250M edges:
Dense:  100 TB ❌
Sparse: ~3 GB ✅ (33,000x smaller!)
```

**How to Build:**
1. Extract all citation relationships from database
2. Create two lists: `sources` and `targets`
3. For each citation (A cites B):
   - Append A's index to `sources`
   - Append B's index to `targets`
4. Create sparse matrix: `csr_matrix((data, (sources, targets)), shape=(n_nodes, n_nodes))`

---

### 3. Retention Rates: Credit Transfer Configuration

**Purpose:** Control how much credit each node keeps vs. transfers to its citations.

**Representation:** An array with one value per node, ranging from 0.0 to 1.0.

```
Retention Rate = proportion of credit kept
Transfer Rate  = 1 - retention_rate (proportion transferred)

Examples:
  retention_rate = 1.0 → keep 100%, transfer 0%   (no transitivity)
  retention_rate = 0.5 → keep 50%,  transfer 50%
  retention_rate = 0.0 → keep 0%,   transfer 100% (maximum transitivity)
```

**Example with 7 nodes:**

```
Node Index:      [  0,   1,   2,   3,   4,   5,   6  ]
Node Types:      [  0,   0,   1,   0,   2,   1,   0  ]  (Paper, Paper, Patent, ...)
Retention:       [0.5, 0.5, 0.7, 0.5, 0.3, 0.7, 0.5]

Interpretation:
  - Papers (nodes 0,1,3,6): Keep 50%, transfer 50% to citations
  - Patents (nodes 2,5):    Keep 70%, transfer 30% to citations  
  - Trials (node 4):        Keep 30%, transfer 70% to citations
```

**Visual Example - Credit Flow:**

```
Initial state: Each node starts with 1.0 kudos (direct citations)

Node 0 (Paper, retention=0.5):
  ┌─────────────┐
  │ Kudos: 1.0  │
  │ Keeps: 0.5  │  (stays in node 0)
  │ Transfers:  │
  │   0.25 → 1  │  (50% split between 2 citations)
  │   0.25 → 2  │
  └─────────────┘

Node 3 (Paper, retention=0.5):
  ┌─────────────┐
  │ Kudos: 1.0  │
  │ Keeps: 0.5  │
  │ Transfers:  │
  │   0.25 → 0  │  (Node 0 receives this!)
  │   0.25 → 1  │
  └─────────────┘

After 1 iteration, Node 0's total credit:
  0.5 (kept) + 0.25 (from node 3) = 0.75
```

**How to Build:**
1. Start with the node types array
2. Create an empty array of the same size (float32)
3. Set retention rates based on type:
   ```
   For each node i:
     if node_types[i] == 0:  retention[i] = paper_rate
     if node_types[i] == 1:  retention[i] = patent_rate
     if node_types[i] == 2:  retention[i] = clinical_trial_rate
   ```

---

### 4. Author Mappings: Attributing Work to People

**Purpose:** Track which authors contributed to which papers/patents/trials for h-index calculation.

**Representation:** A dictionary mapping node indices to lists of author IDs.

**Conceptual Structure:**

```
node_to_authors = {
    node_index: [author_id_1, author_id_2, ...],
    ...
}

author_names = {
    author_id: "Author Full Name",
    ...
}
```

**Example with 6 nodes and 5 authors:**

```
Nodes:
  0: "Deep Learning for Image Recognition" (Paper)
  1: "Neural Network Hardware" (Patent)
  2: "ImageNet Dataset" (Paper)
  3: "Cancer Treatment Trial" (Clinical Trial)
  4: "Transfer Learning Survey" (Paper)
  5: "Computer Vision System" (Patent)

Authors:
  0: "Smith, Jane"
  1: "Johnson, Robert"
  2: "Lee, Maria"
  3: "Zhang, Wei"
  4: "Garcia, Carlos"

Author Mappings:
  node_to_authors = {
      0: [0, 1],        # Paper 0 by Smith and Johnson
      1: [1, 2],        # Patent 1 by Johnson and Lee
      2: [0, 2, 3],     # Paper 2 by Smith, Lee, and Zhang
      3: [3, 4],        # Trial 3 by Zhang and Garcia
      4: [0],           # Paper 4 by Smith only
      5: [2, 4],        # Patent 5 by Lee and Garcia
  }

  author_names = {
      0: "Smith, Jane",
      1: "Johnson, Robert",
      2: "Lee, Maria",
      3: "Zhang, Wei",
      4: "Garcia, Carlos"
  }
```

**Why This Structure?**

One author may have multiple works:
```
"Smith, Jane" (ID=0) appears in nodes: [0, 2, 4]
  → 3 publications

"Johnson, Robert" (ID=1) appears in nodes: [0, 1]
  → 2 works (1 paper, 1 patent)
```

To calculate h-index for Smith:
1. Find all nodes: [0, 2, 4]
2. Get kudos for each: [0.75, 1.2, 0.5]
3. Sort descending: [1.2, 0.75, 0.5]
4. Find h: largest h where h papers have ≥h citations each
   - Paper 1: 1.2 ≥ 1? ✓
   - Paper 2: 0.75 ≥ 2? ✗
   - h-index = 1

**How to Build:**
1. Create empty dictionary
2. Query authorship table from database
3. For each (node_id, author_id) pair:
   ```
   Get or create node's internal index
   Get or create author's internal ID
   Add author_id to the list for that node:
     if node_index not in mapping:
         mapping[node_index] = []
     mapping[node_index].append(author_internal_id)
   ```

---

### 5. Node ID Mappings: External vs Internal

**Purpose:** Bridge between database IDs (arbitrary, non-contiguous) and matrix indices (0, 1, 2, ..., n-1).

**Why Needed?**

Database IDs might look like:
```
Paper IDs:  [101, 523, 1047, 2003, ...]
Patent IDs: [5001, 5002, 5005, ...]
```

But matrix indices must be contiguous:
```
Matrix indices: [0, 1, 2, 3, 4, 5, ...]
```

**Mapping Structure:**

```
external_to_index = {
    (database_id, node_type): matrix_index,
    ...
}

Example:
  external_to_index = {
      (101, 'paper'):   0,
      (523, 'paper'):   1,
      (1047, 'paper'):  2,
      (5001, 'patent'): 3,
      (2003, 'paper'):  4,
      (5002, 'patent'): 5,
  }
```

**Reverse mapping (for looking up results):**

```
node_ids = [101, 523, 1047, 5001, 2003, 5002]
           ↓    ↓    ↓     ↓     ↓     ↓
indices  = [0,   1,   2,    3,    4,    5]
```

**Usage Example:**

```
Database says: "Paper 523 cites Patent 5001"

1. Look up indices:
   Paper 523  → index 1
   Patent 5001 → index 3

2. Add edge to adjacency matrix:
   adjacency[1, 3] = 1

3. After computation, if we want to know the credit of Paper 523:
   credit_scores[1] = 1.25
   
4. To report: "Paper 523 has credit score 1.25"
```

**How to Build:**
1. Initialize counter = 0
2. Process all nodes from all tables:
   ```
   For each paper in publications:
       external_to_index[(paper.id, 'paper')] = counter
       node_ids.append(paper.id)
       node_types.append(0)
       counter += 1
   
   For each patent in patents:
       external_to_index[(patent.id, 'patent')] = counter
       node_ids.append(patent.id)
       node_types.append(1)
       counter += 1
   
   (same for clinical trials...)
   ```

---

## 📊 Complete Data Model Summary

### Quick Reference Table

| Data Structure | Type | Size (10M nodes) | Purpose |
|----------------|------|------------------|---------|
| **Adjacency Matrix** | Sparse CSR | ~3 GB | Graph edges (who cites whom) |
| **Node Types** | uint8 array | 10 MB | Classification (paper/patent/trial) |
| **Retention Rates** | float32 array | 40 MB | Credit transfer configuration |
| **Node IDs** | int64 array | 80 MB | Database ID ↔ matrix index |
| **Author Mappings** | Dict | ~200 MB | Node → authors association |
| **Author Names** | Dict | ~50 MB | Author ID → human name |

---

## 🚀 Quick Start (3 Steps)

### Step 1: Configure Database Connection

Edit `config/sql_extraction.properties`:
```ini
[database]
host = your_host
database = citations_db
user = your_username
password = your_password

[extraction]
output_dir = data/large_scale_experiment
prefix = nature_data
```

### Step 2: Extract from SQL

```bash
python3 extract_from_sql.py
```

**What it does:**
- Extracts papers, patents, clinical trials
- Builds adjacency matrix (edges)
- Maps authors to nodes
- Serializes to disk in compressed format

**Output files:**
```
data/large_scale_experiment/
├── nature_data_adjacency.npz      # Sparse matrix (compressed)
├── nature_data_node_types.npy     # uint8 array
├── nature_data_node_ids.npy       # int64 array
├── nature_data_authors.npz        # Compressed author mappings
├── nature_data_author_names.json  # Human-readable names
└── nature_data_metadata.json      # Graph statistics
```

### Step 3: Run Credit Transfer

```python
from load_large_scale_data import LargeScaleDataLoader
from credit.generalFormulation import GeneralCreditTransfer
from credit.authorMetrics import calculate_h_index_from_kudos

# Load data
loader = LargeScaleDataLoader('data/large_scale_experiment', 'nature_data')
adjacency, node_types, node_ids, node_to_authors, author_names, metadata = loader.load_all()

# Set retention rates
retention_rates = loader.create_retention_rates(
    paper_rate=0.5,
    patent_rate=0.5, 
    clinical_trial_rate=0.5
)

# Compute credit transfer
ct = GeneralCreditTransfer(
    adjacency=adjacency,
    retention_rates=retention_rates,
    use_integer_ids=True,
    enable_convergence_check=True
)
kudos, total_credit = ct.compute()

# Calculate h-indices
h_indices_kudos, direct_citations = calculate_h_index_from_kudos(
    kudos, node_to_authors, author_names
)
```

---

## 🧮 Understanding Credit Transfer Algorithm

This section explains the mathematical process of credit distribution step-by-step.

---

### The Core Concept

**Goal:** Distribute credit transitively through citation chains while respecting retention rates.

**Starting Point:** Every node begins with **kudos = 1.0** (representing one direct citation or initial credit).

**Process:** Credit flows from citing papers to cited papers, respecting retention rates.

---

### Step-by-Step Example

**Setup:** 5 nodes with the following citation structure:

```
Citation Graph:
    ┌─────┐
    │  4  │ (Paper, retention=0.5)
    └──┬──┘
       │
    ┌──▼──┐
    │  3  │ (Paper, retention=0.5)
    └──┬──┘
       │
    ┌──▼──┐     ┌─────┐
    │  0  │◄────│  1  │ (Paper, retention=0.5)
    └──┬──┘     └─────┘
       │
       │  ┌─────┐
       └─►│  2  │ (Patent, retention=0.7)
          └─────┘

Edges (who cites whom):
  4 → 3    (4 cites 3)
  3 → 0    (3 cites 0)
  1 → 0    (1 cites 0)
  0 → 2    (0 cites 2)
```

**Adjacency Matrix:**

```
        0   1   2   3   4
    0 [ 0   0   1   0   0 ]  ← Node 0 cites node 2
    1 [ 1   0   0   0   0 ]  ← Node 1 cites node 0
    2 [ 0   0   0   0   0 ]  ← Node 2 cites nothing (sink)
    3 [ 1   0   0   0   0 ]  ← Node 3 cites node 0
    4 [ 0   0   0   1   0 ]  ← Node 4 cites node 3
```

**Retention Rates:**

```
Node:      [  0,   1,   2,   3,   4 ]
Type:      [  0,   0,   1,   0,   0 ]  (P, P, Patent, P, P)
Retention: [0.5, 0.5, 0.7, 0.5, 0.5]
```

---

### Iteration-by-Iteration Credit Flow

**Initial State (Iteration 0):**

```
Node  | Kudos | Total Credit | Explanation
------|-------|--------------|----------------------------------
  0   |  1.0  |     1.0      | Starts with 1.0
  1   |  1.0  |     1.0      | Starts with 1.0
  2   |  1.0  |     1.0      | Starts with 1.0
  3   |  1.0  |     1.0      | Starts with 1.0
  4   |  1.0  |     1.0      | Starts with 1.0
```

---

**Iteration 1:**

Each node keeps its retention rate and transfers the rest to its citations.

```
Node 0:
  - Keeps: 1.0 × 0.5 = 0.5
  - Transfers: 1.0 × (1 - 0.5) = 0.5
  - Cites 1 node (node 2), so transfers 0.5 to node 2

Node 1:
  - Keeps: 1.0 × 0.5 = 0.5
  - Transfers: 0.5
  - Cites 1 node (node 0), so transfers 0.5 to node 0

Node 2:
  - Keeps: 1.0 × 0.7 = 0.7
  - Transfers: 0.3
  - Cites 0 nodes, so transfers nothing

Node 3:
  - Keeps: 1.0 × 0.5 = 0.5
  - Transfers: 0.5
  - Cites 1 node (node 0), so transfers 0.5 to node 0

Node 4:
  - Keeps: 1.0 × 0.5 = 0.5
  - Transfers: 0.5
  - Cites 1 node (node 3), so transfers 0.5 to node 3

Credit Flow Visualization:
       0.5        0.5
    1 ──────► 0 ──────► 2
              ▲
       0.5    │
    3 ────────┘
    ▲
    │ 0.5
    4

After Iteration 1:
Node  | Kudos | Received  | New Total | Calculation
------|-------|-----------|-----------|---------------------------
  0   |  1.0  | 0.5+0.5   |   2.0     | 1.0 + (from 1) + (from 3)
  1   |  1.0  |   0.0     |   1.0     | No incoming credit
  2   |  1.0  |   0.5     |   1.5     | 1.0 + (from 0)
  3   |  1.0  |   0.5     |   1.5     | 1.0 + (from 4)
  4   |  1.0  |   0.0     |   1.0     | No incoming credit
```

---

**Iteration 2:**

Now node 0 has 2.0 credit, node 3 has 1.5, etc. They transfer again.

```
Node 0 (credit=2.0):
  - Keeps: 2.0 × 0.5 = 1.0
  - Transfers: 2.0 × 0.5 = 1.0 to node 2

Node 1 (credit=1.0):
  - Keeps: 0.5
  - Transfers: 0.5 to node 0

Node 2 (credit=1.5):
  - Keeps: 1.5 × 0.7 = 1.05
  - Transfers: 0.45 (but cites nothing, so this "leaks")

Node 3 (credit=1.5):
  - Keeps: 0.75
  - Transfers: 0.75 to node 0

Node 4 (credit=1.0):
  - Keeps: 0.5
  - Transfers: 0.5 to node 3

After Iteration 2:
Node  | Previous | Received    | New Total | Notes
------|----------|-------------|-----------|----------------------
  0   |   2.0    | 0.5+0.75    |   3.25    | Accumulating credit
  1   |   1.0    |   0.0       |   1.0     | No change
  2   |   1.5    |   1.0       |   2.5     | Receiving from 0
  3   |   1.5    |   0.5       |   2.0     | Receiving from 4
  4   |   1.0    |   0.0       |   1.0     | No change
```

---

**Convergence:**

The process continues until credit values stabilize (change < threshold).

```
Final Credit (after convergence):
Node  | Kudos | Total Credit | Interpretation
------|-------|--------------|----------------------------------------
  0   |  1.0  |    ~4.2      | High credit (cited by 1 and 3)
  1   |  1.0  |    ~1.0      | Only direct credit (no incoming)
  2   |  1.0  |    ~3.5      | Good credit (cited by 0, who has high credit)
  3   |  1.0  |    ~2.8      | Medium credit (cited by 4)
  4   |  1.0  |    ~1.0      | Only direct credit (leaf node)
```

**Key Insight:** Node 0 has higher credit than node 2, even though both are cited once directly, because node 0 is cited by nodes with higher credit (transitivity effect!).

---

### Matrix Formulation

The iterative process can be expressed mathematically:

```
Variables:
  C_t     = total credit vector at iteration t
  K       = kudos vector (always 1.0 for each node)
  R       = retention rates (diagonal matrix)
  A^T     = transposed adjacency matrix
  D_out   = out-degree diagonal matrix (how many citations each node makes)

Formula:
  C_{t+1} = K + (I - R) × A^T × D_out^{-1} × C_t

Where:
  K                   = Starting credit (kudos)
  (I - R)             = Transfer rates
  A^T × D_out^{-1}    = Normalized adjacency (distributes evenly)
  C_t                 = Current credit being transferred

Convergence:
  Stop when ||C_{t+1} - C_t|| < threshold
```

**What each component does:**

1. **K (kudos):** Ensures every node keeps its initial 1.0 credit
2. **(I - R):** Scales credit by transfer rate (1 - retention)
3. **A^T:** Directs credit flow (transpose because credit flows backward along edges)
4. **D_out^{-1}:** Divides transferred credit equally among citations
5. **C_t:** The credit being redistributed in this iteration

---

### Example: Two Nodes, One Edge

Simplest case to understand the math:

```
Setup:
  Node 0 cites Node 1
  Both have retention = 0.5

Adjacency Matrix:
    [0  1]
    [0  0]

Iteration 1:
  Node 0: Keeps 0.5, transfers 0.5 to node 1
  Node 1: Keeps 0.5, transfers 0.5 (nowhere to go)
  
  Result: C_1 = [1.0, 1.5]

Iteration 2:
  Node 0: Keeps 0.5 of its 1.0, transfers 0.5 to node 1
  Node 1: Keeps 0.75 of its 1.5, transfers 0.75 (nowhere to go)
  
  Result: C_2 = [1.0, 1.75]

Convergence:
  Node 0: 1.0 (only kudos, all transfer goes to 1)
  Node 1: 2.0 (kudos + all credit from 0)
```

---

### Special Cases

**Case 1: Retention = 1.0 (No Transitivity)**
```
All nodes keep all credit
Total Credit = Kudos = 1.0 for everyone
Result: Only direct citations count (baseline)
```

**Case 2: Retention = 0.0 (Maximum Transitivity)**
```
All credit flows to citations
Leaf nodes accumulate everything
Papers that cite nothing get very high credit
```

**Case 3: Sink Nodes (cite nothing)**
```
These nodes accumulate credit from others
Act as "credit attractors"
Should have retention = 1.0 to prevent credit "leaking"
```

**Case 4: Citation Chains**
```
A → B → C → D

With retention = 0.5:
  D gets 1.0 (kudos only)
  C gets 1.0 + 0.5 (from D)
  B gets 1.0 + 0.75 (from C)
  A gets 1.0 + 0.875 (from B)

Credit propagates backward through the chain!
```

---

## 🔨 Building Data Structures from Scratch

This section provides a conceptual algorithm for building each data structure from SQL database queries.

---

### Algorithm 1: Building Node Types and ID Mappings

**Input:** Three SQL tables: `publications`, `patents`, `clinical_trials`

**Output:** 
- `node_types` array
- `node_ids` array  
- `external_to_index` dictionary

**Algorithm:**

```
STEP 1: Initialize
  - counter = 0
  - node_types = empty list
  - node_ids = empty list
  - external_to_index = empty dictionary

STEP 2: Process Publications
  Query: SELECT id FROM publications
  
  For each row:
    node_ids.append(row.id)
    node_types.append(0)                          # 0 = paper
    external_to_index[(row.id, 'paper')] = counter
    counter = counter + 1

STEP 3: Process Patents
  Query: SELECT id FROM patents
  
  For each row:
    node_ids.append(row.id)
    node_types.append(1)                          # 1 = patent
    external_to_index[(row.id, 'patent')] = counter
    counter = counter + 1

STEP 4: Process Clinical Trials
  Query: SELECT id FROM clinical_trials
  
  For each row:
    node_ids.append(row.id)
    node_types.append(2)                          # 2 = clinical_trial
    external_to_index[(row.id, 'clinical_trial')] = counter
    counter = counter + 1

STEP 5: Convert to arrays
  node_types_array = convert node_types to numpy array with dtype=uint8
  node_ids_array = convert node_ids to numpy array with dtype=int64

RESULT:
  Total nodes = counter
  node_types_array has length = counter
  node_ids_array has length = counter
  external_to_index has counter entries
```

**Example Execution:**

```
Database content:
  publications: [101, 205, 308]
  patents: [5001, 5002]
  clinical_trials: [9001]

Iteration 1 (Paper 101):
  counter = 0
  node_ids = [101]
  node_types = [0]
  external_to_index = {(101, 'paper'): 0}

Iteration 2 (Paper 205):
  counter = 1
  node_ids = [101, 205]
  node_types = [0, 0]
  external_to_index = {(101, 'paper'): 0, (205, 'paper'): 1}

Iteration 3 (Paper 308):
  counter = 2
  node_ids = [101, 205, 308]
  node_types = [0, 0, 0]
  external_to_index = {(101, 'paper'): 0, (205, 'paper'): 1, (308, 'paper'): 2}

Iteration 4 (Patent 5001):
  counter = 3
  node_ids = [101, 205, 308, 5001]
  node_types = [0, 0, 0, 1]
  external_to_index = {..., (5001, 'patent'): 3}

Iteration 5 (Patent 5002):
  counter = 4
  node_ids = [101, 205, 308, 5001, 5002]
  node_types = [0, 0, 0, 1, 1]
  external_to_index = {..., (5002, 'patent'): 4}

Iteration 6 (Clinical Trial 9001):
  counter = 5
  node_ids = [101, 205, 308, 5001, 5002, 9001]
  node_types = [0, 0, 0, 1, 1, 2]
  external_to_index = {..., (9001, 'clinical_trial'): 5}

Final:
  Total nodes: 6
  node_types: [0, 0, 0, 1, 1, 2]
  node_ids: [101, 205, 308, 5001, 5002, 9001]
```

---

### Algorithm 2: Building Adjacency Matrix

**Input:** 
- SQL table: `citations(source_id, target_id, source_type, target_type, relationship)`
- `external_to_index` dictionary from Algorithm 1
- Total number of nodes

**Output:** Sparse adjacency matrix (CSR format)

**Algorithm:**

```
STEP 1: Initialize
  - edge_sources = empty list
  - edge_targets = empty list
  - n_nodes = total number of nodes

STEP 2: Extract Citations
  Query: SELECT source_id, target_id, source_type, target_type, relationship
         FROM citations
  
  For each row:
    # Map external IDs to internal indices
    source_key = (row.source_id, row.source_type)
    target_key = (row.target_id, row.target_type)
    
    # Check if both nodes exist
    if source_key in external_to_index AND target_key in external_to_index:
      idx_source = external_to_index[source_key]
      idx_target = external_to_index[target_key]
      
      # Determine edge direction based on relationship semantics
      if row.relationship in ['cites', 'references', 'documents']:
        # Source → Target
        edge_sources.append(idx_source)
        edge_targets.append(idx_target)
      
      elif row.relationship in ['isCitedBy', 'isReferencedBy']:
        # Target → Source (reverse direction!)
        edge_sources.append(idx_target)
        edge_targets.append(idx_source)
      
      else:
        # Default: Source → Target
        edge_sources.append(idx_source)
        edge_targets.append(idx_target)

STEP 3: Create Sparse Matrix
  n_edges = length of edge_sources
  edge_data = array of n_edges ones (all weights = 1.0)
  
  Create CSR sparse matrix:
    adjacency = csr_matrix(
      (edge_data, (edge_sources, edge_targets)),
      shape=(n_nodes, n_nodes),
      dtype=float32
    )

RESULT:
  Sparse matrix of size n_nodes × n_nodes
  Contains n_edges non-zero entries
```

**Example Execution:**

```
Database content:
  citations:
    (101, 205, 'paper', 'paper', 'cites')      → Paper 101 cites Paper 205
    (101, 5001, 'paper', 'patent', 'cites')    → Paper 101 cites Patent 5001
    (205, 308, 'paper', 'paper', 'cites')      → Paper 205 cites Paper 308
    (308, 101, 'paper', 'paper', 'isCitedBy')  → Paper 101 isCitedBy Paper 308

Recall node mappings:
  (101, 'paper')   → index 0
  (205, 'paper')   → index 1
  (308, 'paper')   → index 2
  (5001, 'patent') → index 3

Iteration 1: (101, 205, 'cites')
  source_key = (101, 'paper') → idx 0
  target_key = (205, 'paper') → idx 1
  'cites' → direction is source to target
  edge_sources = [0]
  edge_targets = [1]

Iteration 2: (101, 5001, 'cites')
  source_key = (101, 'paper') → idx 0
  target_key = (5001, 'patent') → idx 3
  edge_sources = [0, 0]
  edge_targets = [1, 3]

Iteration 3: (205, 308, 'cites')
  source_key = (205, 'paper') → idx 1
  target_key = (308, 'paper') → idx 2
  edge_sources = [0, 0, 1]
  edge_targets = [1, 3, 2]

Iteration 4: (308, 101, 'isCitedBy')
  source_key = (308, 'paper') → idx 2
  target_key = (101, 'paper') → idx 0
  'isCitedBy' → REVERSE direction! Target to Source
  edge_sources = [0, 0, 1, 0]  ← Added target (0)
  edge_targets = [1, 3, 2, 2]  ← Added source (2)

Final edge lists:
  edge_sources = [0, 0, 1, 0]
  edge_targets = [1, 3, 2, 2]
  
Resulting adjacency matrix:
        0   1   2   3   4   5
    0 [ 0   1   1   1   0   0 ]  ← Node 0 cites 1, 2, 3
    1 [ 0   0   1   0   0   0 ]  ← Node 1 cites 2
    2 [ 0   0   0   0   0   0 ]  ← Node 2 cites nothing
    3 [ 0   0   0   0   0   0 ]
    4 [ 0   0   0   0   0   0 ]
    5 [ 0   0   0   0   0   0 ]
```

**Important Note on Edge Direction:**

```
Citation semantics in natural language are tricky!

"Paper A cites Paper B"
  → A is the citing paper (source)
  → B is the cited paper (target)
  → Edge direction: A → B

"Paper A is cited by Paper B"
  → A is the cited paper (receives citation)
  → B is the citing paper (gives citation)
  → Edge direction: B → A (reversed!)

Always verify the relationship semantics in your database!
```

---

### Algorithm 3: Building Retention Rates

**Input:** 
- `node_types` array
- Retention rate parameters (paper_rate, patent_rate, trial_rate)

**Output:** `retention_rates` array

**Algorithm:**

```
STEP 1: Initialize
  n_nodes = length of node_types
  retention_rates = array of size n_nodes (float32)

STEP 2: Assign Rates Based on Type
  For i from 0 to n_nodes-1:
    node_type = node_types[i]
    
    if node_type == 0:  # Paper
      retention_rates[i] = paper_rate
    
    elif node_type == 1:  # Patent
      retention_rates[i] = patent_rate
    
    elif node_type == 2:  # Clinical Trial
      retention_rates[i] = trial_rate

RESULT:
  retention_rates array of length n_nodes
  Each element is between 0.0 and 1.0
```

**Example Execution:**

```
Input:
  node_types = [0, 0, 0, 1, 1, 2]
  paper_rate = 0.5
  patent_rate = 0.7
  trial_rate = 0.3

Processing:
  i=0: node_types[0] = 0 (paper)  → retention_rates[0] = 0.5
  i=1: node_types[1] = 0 (paper)  → retention_rates[1] = 0.5
  i=2: node_types[2] = 0 (paper)  → retention_rates[2] = 0.5
  i=3: node_types[3] = 1 (patent) → retention_rates[3] = 0.7
  i=4: node_types[4] = 1 (patent) → retention_rates[4] = 0.7
  i=5: node_types[5] = 2 (trial)  → retention_rates[5] = 0.3

Result:
  retention_rates = [0.5, 0.5, 0.5, 0.7, 0.7, 0.3]
```

---

### Algorithm 4: Building Author Mappings

**Input:**
- SQL table: `authors(id, name)`
- SQL table: `authorships(node_id, node_type, author_id)`
- `external_to_index` dictionary

**Output:**
- `node_to_authors` dictionary
- `author_names` dictionary

**Algorithm:**

```
STEP 1: Initialize
  - author_counter = 0
  - author_id_map = empty dictionary  # external_id → internal_id
  - author_names = empty dictionary   # internal_id → name
  - node_to_authors = empty dictionary  # node_index → [author_ids]

STEP 2: Load Author Names
  Query: SELECT id, name FROM authors
  
  For each row:
    internal_id = author_counter
    author_id_map[row.id] = internal_id
    author_names[internal_id] = row.name
    author_counter = author_counter + 1

STEP 3: Load Authorships
  Query: SELECT node_id, node_type, author_id FROM authorships
  
  For each row:
    # Map node to internal index
    node_key = (row.node_id, row.node_type)
    
    if node_key in external_to_index:
      node_index = external_to_index[node_key]
      
      # Map author to internal ID
      if row.author_id in author_id_map:
        author_internal_id = author_id_map[row.author_id]
      else:
        # Author not in authors table, create without name
        author_internal_id = author_counter
        author_id_map[row.author_id] = author_internal_id
        author_counter = author_counter + 1
      
      # Add to mapping
      if node_index not in node_to_authors:
        node_to_authors[node_index] = empty list
      
      node_to_authors[node_index].append(author_internal_id)

RESULT:
  node_to_authors: maps node indices to lists of author IDs
  author_names: maps author IDs to names
  Total authors: author_counter
```

**Example Execution:**

```
Database content:
  authors:
    (1001, "Smith, Jane")
    (1002, "Johnson, Robert")
    (1003, "Lee, Maria")
  
  authorships:
    (101, 'paper', 1001)    → Paper 101 by Smith
    (101, 'paper', 1002)    → Paper 101 by Johnson
    (205, 'paper', 1001)    → Paper 205 by Smith
    (308, 'paper', 1003)    → Paper 308 by Lee
    (5001, 'patent', 1002)  → Patent 5001 by Johnson
    (5001, 'patent', 1003)  → Patent 5001 by Lee

Recall node mappings:
  (101, 'paper')   → index 0
  (205, 'paper')   → index 1
  (308, 'paper')   → index 2
  (5001, 'patent') → index 3

STEP 2: Load authors
  author_id_map = {1001: 0, 1002: 1, 1003: 2}
  author_names = {0: "Smith, Jane", 1: "Johnson, Robert", 2: "Lee, Maria"}
  author_counter = 3

STEP 3: Load authorships
  Row 1: (101, 'paper', 1001)
    node_index = 0
    author_internal_id = 0
    node_to_authors = {0: [0]}

  Row 2: (101, 'paper', 1002)
    node_index = 0
    author_internal_id = 1
    node_to_authors = {0: [0, 1]}

  Row 3: (205, 'paper', 1001)
    node_index = 1
    author_internal_id = 0
    node_to_authors = {0: [0, 1], 1: [0]}

  Row 4: (308, 'paper', 1003)
    node_index = 2
    author_internal_id = 2
    node_to_authors = {0: [0, 1], 1: [0], 2: [2]}

  Row 5: (5001, 'patent', 1002)
    node_index = 3
    author_internal_id = 1
    node_to_authors = {0: [0, 1], 1: [0], 2: [2], 3: [1]}

  Row 6: (5001, 'patent', 1003)
    node_index = 3
    author_internal_id = 2
    node_to_authors = {0: [0, 1], 1: [0], 2: [2], 3: [1, 2]}

Final result:
  node_to_authors = {
    0: [0, 1],   # Paper 101: Smith, Johnson
    1: [0],      # Paper 205: Smith
    2: [2],      # Paper 308: Lee
    3: [1, 2]    # Patent 5001: Johnson, Lee
  }
  
  author_names = {
    0: "Smith, Jane",
    1: "Johnson, Robert",
    2: "Lee, Maria"
  }
```

---

### Algorithm 5: Computing H-Index

**Input:**
- Credit scores (kudos or total_credit) array
- `node_to_authors` dictionary
- `author_names` dictionary

**Output:** H-index for each author

**Algorithm:**

```
STEP 1: Aggregate Credit per Author
  author_credits = empty dictionary  # author_id → list of credit scores
  
  For each node_index in node_to_authors:
    credit_score = credits[node_index]
    author_list = node_to_authors[node_index]
    
    For each author_id in author_list:
      if author_id not in author_credits:
        author_credits[author_id] = empty list
      
      author_credits[author_id].append(credit_score)

STEP 2: Calculate H-Index for Each Author
  h_indices = empty dictionary  # author_id → h_index
  
  For each author_id in author_credits:
    credits_list = author_credits[author_id]
    
    # Sort in descending order
    sorted_credits = sort credits_list in descending order
    
    # Find h-index
    h = 0
    For i from 0 to length(sorted_credits)-1:
      if sorted_credits[i] >= (i + 1):
        h = i + 1
      else:
        break
    
    h_indices[author_id] = h

RESULT:
  h_indices: maps author_id to h-index value
```

**Example Execution:**

```
Input:
  credits = [2.5, 1.8, 3.2, 1.0]  # Nodes 0, 1, 2, 3
  
  node_to_authors = {
    0: [0, 1],   # Credit 2.5 for Smith and Johnson
    1: [0],      # Credit 1.8 for Smith
    2: [2],      # Credit 3.2 for Lee
    3: [1, 2]    # Credit 1.0 for Johnson and Lee
  }

STEP 1: Aggregate credits
  Node 0 (credit=2.5) has authors [0, 1]:
    author_credits = {0: [2.5], 1: [2.5]}
  
  Node 1 (credit=1.8) has authors [0]:
    author_credits = {0: [2.5, 1.8], 1: [2.5]}
  
  Node 2 (credit=3.2) has authors [2]:
    author_credits = {0: [2.5, 1.8], 1: [2.5], 2: [3.2]}
  
  Node 3 (credit=1.0) has authors [1, 2]:
    author_credits = {0: [2.5, 1.8], 1: [2.5, 1.0], 2: [3.2, 1.0]}

STEP 2: Calculate h-indices
  Author 0 (Smith):
    credits = [2.5, 1.8]
    sorted = [2.5, 1.8]
    Check: 2.5 >= 1? Yes → h=1
    Check: 1.8 >= 2? No → stop
    h-index = 1

  Author 1 (Johnson):
    credits = [2.5, 1.0]
    sorted = [2.5, 1.0]
    Check: 2.5 >= 1? Yes → h=1
    Check: 1.0 >= 2? No → stop
    h-index = 1

  Author 2 (Lee):
    credits = [3.2, 1.0]
    sorted = [3.2, 1.0]
    Check: 3.2 >= 1? Yes → h=1
    Check: 1.0 >= 2? No → stop
    h-index = 1

Result:
  h_indices = {0: 1, 1: 1, 2: 1}

Example with more papers:
  Author with credits [10, 8, 5, 4, 3]
  sorted = [10, 8, 5, 4, 3]
  Check: 10 >= 1? Yes → h=1
  Check: 8 >= 2? Yes → h=2
  Check: 5 >= 3? Yes → h=3
  Check: 4 >= 4? Yes → h=4
  Check: 3 >= 5? No → stop
  h-index = 4
  
  Interpretation: This author has 4 papers with at least 4 citations each
```

---

## 📦 File Formats

### Adjacency Matrix (`.npz`)
- **Format**: Compressed sparse CSR
- **Size**: ~12 bytes per edge
- **Load**: `sp.load_npz('file.npz')`

### Node Types (`.npy`)
- **Format**: uint8 array
- **Size**: 1 byte per node
- **Load**: `np.load('file.npy')`

### Authors (`.npz`)
- **Format**: Compressed arrays (node_indices, author_counts, author_ids)
- **Size**: ~4 bytes per author assignment
- **Load**: `np.load('file.npz')`

---

## 💾 Memory Requirements

| Nodes | Edges | RAM | Disk Space |
|-------|-------|-----|-----------|
| 1M | 10M | 4 GB | 500 MB |
| 10M | 100M | 16 GB | 1.5 GB |
| 50M | 1B | 64 GB | 13 GB |

**Optimization tips:**
- Use `dtype=uint8` for node types (87.5% smaller than int64)
- Use `dtype=float32` for retention rates (50% smaller than float64)
- Always use sparse matrices (never convert to dense!)

---

## 🔧 SQL Schema Requirements

### Minimal Required Tables

```sql
-- Papers
publications (id BIGINT, title TEXT, ...)

-- Patents
patents (id BIGINT, patent_number TEXT, ...)

-- Clinical Trials
clinical_trials (id BIGINT, nct_id TEXT, ...)

-- Citations/Relations
citations (
    source_id BIGINT,
    target_id BIGINT,
    source_type VARCHAR,
    target_type VARCHAR,
    relationship VARCHAR
)

-- Authors
authors (id BIGINT, name TEXT)

-- Authorship
authorships (
    node_id BIGINT,
    node_type VARCHAR,
    author_id BIGINT
)
```

### Required Indexes

```sql
CREATE INDEX idx_citations_source ON citations(source_id, source_type);
CREATE INDEX idx_citations_target ON citations(target_id, target_type);
CREATE INDEX idx_authorships_node ON authorships(node_id, node_type);
CREATE INDEX idx_authorships_author ON authorships(author_id);
```

---

## ⚡ Performance Tips

### Extraction
1. **Batch size**: 100K-500K rows per fetch
2. **Use indexes**: See SQL schema above
3. **Connection pooling**: For parallel extraction

### Processing
1. **Sparse operations**: Always use `@` operator (don't convert to dense!)
2. **Integer IDs**: Set `use_integer_ids=True` (10-50x faster)
3. **Convergence check**: Enable to stop early

### Memory
1. **Memory mapping**: For very large arrays
2. **Batch processing**: Split graph into chunks if needed
3. **Compression**: Use `.npz` format with compression

---

## 🎯 Retention Rate Examples

### Scenario 1: Papers transfer more credit
```python
retention_rates = loader.create_retention_rates(
    paper_rate=0.3,          # 70% transfer
    patent_rate=0.8,         # 20% transfer
    clinical_trial_rate=0.8  # 20% transfer
)
```

### Scenario 2: Equal transfer
```python
retention_rates = loader.create_retention_rates(
    paper_rate=0.5,
    patent_rate=0.5,
    clinical_trial_rate=0.5
)
```

### Scenario 3: No transitivity (baseline)
```python
retention_rates = loader.create_retention_rates(
    paper_rate=1.0,
    patent_rate=1.0,
    clinical_trial_rate=1.0
)
```

---

## 📖 Relationship Semantics

**From source to target:**
- `cites` - Paper A cites Paper B → edge A→B
- `references` - Paper A references Patent B → edge A→B
- `documents` - Paper A documents Clinical Trial B → edge A→B

**From target to source:**
- `isCitedBy` - Paper A isCitedBy Paper B → edge B→A
- `isReferencedBy` - Paper A isReferencedBy Patent B → edge B→A

---

## ❓ Troubleshooting

### Out of Memory
```python
# Check available RAM
import psutil
print(f"RAM: {psutil.virtual_memory().available / 1e9:.1f} GB")

# Use memory mapping for large arrays
large_array = np.load('huge.npy', mmap_mode='r')
```

### Slow SQL Queries
- Add database indexes (see schema above)
- Increase batch_size in config
- Use connection pooling

### Convergence Issues
- Check for cycles: `nx.simple_cycles(G)`
- Increase max_iterations
- Adjust convergence_threshold

---

## 📚 Full Documentation

- **Complete Guide**: [LARGE_SCALE_DATA_GUIDE.md](LARGE_SCALE_DATA_GUIDE.md)
- **Synthetic Graphs**: [SYNTHETIC_GRAPHS_GUIDE.md](SYNTHETIC_GRAPHS_GUIDE.md)
- **Main README**: [README.md](README.md)

---

**Date:** January 27, 2026  
**Version:** 1.0  
**Paper**: Nature Scientific Data (2025) - https://www.nature.com/articles/s41597-025-05343-8
