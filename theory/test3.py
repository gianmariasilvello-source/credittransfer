
# Build A
A = np.array([[0,   1],
              [0.9, 0]])
v = np.array([1,0])

I = np.eye(A.shape[0])

M = I - A.T
c= np.linalg.solve(M,v)   # (I - A^T)^{-1} v
r = A.dot(np.ones(A.shape[0])) # total fraction redistributed by each node (row sums)
k = np.diag(1 - r) @ c      # kudos retained

print(c)
