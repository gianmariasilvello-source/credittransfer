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
A = np.zeros((4,4))
A[0,1] = 0.5   # 1->2
A[1,2] = 0.6   # 2->3
A[2,0] = 0.3   # 3->1
A[2,3] = 0.4   # 3->4
# node 4 has no outgoing transfers (row 3 is zeros)

# input v (indegree of each node, from the edge list)
v = np.array([1.0, 1.0, 1.0, 1.0])

I = np.eye(4)

# Check spectral radius of A^T
eigvals = np.linalg.eigvals(A.T)
spectral_radius = max(abs(eigvals))

# Closed-form
M = I - A.T
c = np.linalg.solve(M, v)   # (I - A^T)^{-1} v
r = A.dot(np.ones(4))       # total fraction redistributed by each node (row sums)
K = np.diag(1 - r) @ c      # kudos retained
