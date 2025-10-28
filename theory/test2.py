# Example calculation of transitive credit using the closed-form from notes.pdf
# Nodes: 1,2,3,4
# Edges (with transfer fractions):
# 1 -> 2 : 0.5   (node 1 sends 0.5 of its credit to node 2)
# 2 -> 3 : 0.6
# 3 -> 1 : 0.3,  3 -> 4 : 0.4  (node 3 sends total 0.7)
# 4 has no outgoing transfers (sink)
#
# Transfer matrix A (rows = source, cols = destination):
# A[i,j] = fraction of node i's credit transferred to node j
#
# Input vector v is the indegree vector (each incoming citation contributes 1 unit)
# We compute:
#   c = (I - A^T)^{-1} v   (total credit at each node)
#   r = A @ 1              (total fraction each node redistributes)
#   k = (I - diag(r)) @ c  (kudos retained by each node)
#
# We'll present the numeric results and a small table.
import numpy as np

# Build A
A = np.array([[ 0, (1/3),   (1/3),   (1/3)   ],
              [ (1/3), 0,   (1/3),   (1/3)   ],
              [ (1/3), (1/3),   (1/3),   0    ],
              [ (1/3), (1/3),   (1/3),   0   ]])

             


# input v (indegree of each node, from the edge list)
v = np.array([1, 0, 0, 0])

I = np.eye(4)

# Closed-form
M = I - A.T
c = np.linalg.solve(M, v)   # (I - A^T)^{-1} v
r = A.dot(np.ones(4))       # total fraction redistributed by each node (row sums)
k= np.diag(1 - r) @ c      # kudos retained
