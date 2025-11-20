import numpy as np
A = np.array([[ 0, 1, 0, 0   ],
              [ 0, 0, 1, 0   ],
              [ 0, 0, 0, 0.9 ],
              [ 0, 1, 0, 0   ]])
             


v = np.array([1, 0, 0, 0])

I = np.eye(4)

# Closed-form
M = I - A.T
c = np.linalg.solve(M, v)   # (I - A^T)^{-1} v
r = A.dot(np.ones(4))       # total fraction redistributed by each node (row sums)
k = np.diag(1 - r) @ c      # kudos retained
