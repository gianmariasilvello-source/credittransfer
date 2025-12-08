import numpy as np


# Build A
A = np.array([[0,   1],
              [0.9, 0]])
I = np.eye(A.shape[0])

NOW = 100  #Start of time = 0
# Build v
v = np.array([[.0,.0] for i in range (0, NOW)]+[[0,1]])
k = np.array([[.0,.0] for i in range (0, NOW)]+[[0,0]])


c = np.zeros([NOW+1, A.shape[0]])
#Build c(ost) arrays indexed by time
c[NOW] = v[NOW]
for t in range(NOW-1, -1, -1):
    c[t] = A.T@c[t+1] +v[t]

r = A.dot(np.ones(A.shape[0]))
for t in range(NOW, -1, -1):
    k[t] = np.diag(1-r)@c[t]

for t in range(NOW, -1, -1):
    print(t, "&", c[t][0], "&", c[t][1], "&",  k[t][0], "&", k[t][1])

print("%%%%")
print (k.sum(axis=0))
print (c.sum(axis=0))
