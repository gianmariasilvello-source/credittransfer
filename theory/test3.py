
# Build A
A = np.array([[ 1, 0,   0, ],
              [ 0,  1  ,   -2 ],
              [ 0,  -0.5  ,   1]])


I = np.eye(A.shape[0])

AA = np.linalg.inv(A)

print(AA)
