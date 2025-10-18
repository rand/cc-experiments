---
name: math-linear-algebra-computation
description: Solving systems of linear equations (Ax = b)
---



# Linear Algebra Computation

## Metadata
- **Skill ID**: linear-algebra-computation
- **Category**: Mathematics/Computation
- **Complexity**: Advanced
- **Last Updated**: 2025-10-18

## Overview
Computational linear algebra using NumPy and SciPy for matrix operations, decompositions, solving linear systems, and dimensionality reduction. Essential for scientific computing, machine learning, and numerical analysis.

## When to Use This Skill
- Solving systems of linear equations (Ax = b)
- Matrix decompositions (SVD, QR, Cholesky, eigendecomposition)
- Dimensionality reduction (PCA, matrix approximations)
- Least squares problems and linear regression
- Computing matrix norms, condition numbers, ranks
- Large-scale sparse matrix operations
- Numerical linear algebra in scientific computing

## When NOT to Use This Skill
- Symbolic mathematics (use SymPy instead)
- Small matrices where performance doesn't matter
- When automatic differentiation is needed (use JAX/PyTorch)
- Graph algorithms (use NetworkX)
- Pure theoretical proofs (not computational)

## Prerequisites
- Python basics
- Understanding of linear algebra concepts
- NumPy array operations
- Basic numerical analysis awareness

## Core Concepts

### 1. Matrix Operations Fundamentals

**Efficient Matrix Multiplication**
```python
import numpy as np

# Basic matrix multiplication
A = np.random.rand(1000, 500)
B = np.random.rand(500, 300)

# Standard: A @ B or np.dot(A, B)
C = A @ B  # Preferred Python 3.5+

# Matrix-vector: use @ for clarity
x = np.random.rand(500)
y = A @ x

# Batch matrix multiplication
batch_A = np.random.rand(10, 100, 50)
batch_B = np.random.rand(10, 50, 30)
batch_C = np.einsum('ijk,ikl->ijl', batch_A, batch_B)
# Or: batch_C = batch_A @ batch_B (broadcasting)

# Outer product
u = np.random.rand(100)
v = np.random.rand(200)
outer = np.outer(u, v)  # 100x200 matrix

# Inner product (dot product)
inner = np.inner(u, u)  # Scalar
```

**Matrix Norms and Properties**
```python
from numpy.linalg import norm

A = np.random.rand(100, 100)

# Frobenius norm (default)
fro_norm = norm(A)  # sqrt(sum of squared elements)

# 2-norm (spectral norm, largest singular value)
spectral_norm = norm(A, ord=2)

# Nuclear norm (sum of singular values)
nuclear_norm = norm(A, ord='nuc')

# Infinity norm (max row sum)
inf_norm = norm(A, ord=np.inf)

# 1-norm (max column sum)
one_norm = norm(A, ord=1)

# Condition number (sensitivity to perturbations)
cond = np.linalg.cond(A)  # ||A|| * ||A^-1||
# High condition number = ill-conditioned matrix
```

### 2. Solving Linear Systems

**Direct Methods (Ax = b)**
```python
from scipy.linalg import solve, lu_factor, lu_solve, cho_factor, cho_solve

# General system: prefer solve() over inv()
A = np.random.rand(100, 100)
b = np.random.rand(100)

# NEVER do this (slow and numerically unstable):
# x = np.linalg.inv(A) @ b  # BAD!

# ALWAYS do this instead:
x = np.linalg.solve(A, b)  # GOOD!

# Multiple right-hand sides
B = np.random.rand(100, 5)
X = np.linalg.solve(A, B)

# LU decomposition for repeated solves
lu, piv = lu_factor(A)
x1 = lu_solve((lu, piv), b)
x2 = lu_solve((lu, piv), b + 0.1)  # Reuse factorization

# Symmetric positive definite: use Cholesky
A_spd = A @ A.T + np.eye(100)  # Force SPD
c, low = cho_factor(A_spd)
x_cho = cho_solve((c, low), b)

# Check solution quality
residual = norm(A @ x - b) / norm(b)
print(f"Relative residual: {residual:.2e}")
```

**Least Squares Problems**
```python
from numpy.linalg import lstsq
from scipy.linalg import qr

# Overdetermined system (more equations than unknowns)
A = np.random.rand(200, 100)  # 200 equations, 100 unknowns
b = np.random.rand(200)

# Solve min ||Ax - b||^2
x, residuals, rank, s = lstsq(A, b, rcond=None)

# Underdetermined system (infinite solutions, find minimum norm)
A_under = np.random.rand(50, 100)  # 50 equations, 100 unknowns
b_under = np.random.rand(50)
x_min_norm = lstsq(A_under, b_under, rcond=None)[0]

# Weighted least squares
W = np.diag(np.random.rand(200))  # Weight matrix
A_weighted = W @ A
b_weighted = W @ b
x_weighted = lstsq(A_weighted, b_weighted, rcond=None)[0]

# QR-based least squares (more stable for ill-conditioned A)
Q, R = qr(A, mode='economic')
x_qr = solve(R, Q.T @ b)
```

### 3. Matrix Decompositions

**Singular Value Decomposition (SVD)**
```python
from numpy.linalg import svd
from scipy.sparse.linalg import svds

# Full SVD: A = U @ S @ V^T
A = np.random.rand(100, 50)
U, s, Vt = svd(A, full_matrices=False)

# U: 100x50 (left singular vectors)
# s: 50 (singular values, sorted descending)
# Vt: 50x50 (right singular vectors transposed)

# Reconstruct original matrix
S = np.diag(s)
A_reconstructed = U @ S @ Vt
assert np.allclose(A, A_reconstructed)

# Low-rank approximation (truncated SVD)
k = 10  # Keep top 10 components
A_approx = U[:, :k] @ np.diag(s[:k]) @ Vt[:k, :]

# Approximation error
error = norm(A - A_approx, 'fro') / norm(A, 'fro')
print(f"Relative error with k={k}: {error:.4f}")

# Sparse SVD (for large matrices, top k singular values only)
A_large = np.random.rand(1000, 500)
k = 20
U_k, s_k, Vt_k = svds(A_large, k=k)
# Note: svds returns singular values in ASCENDING order
# Reverse them for consistency
idx = np.argsort(s_k)[::-1]
s_k = s_k[idx]
U_k = U_k[:, idx]
Vt_k = Vt_k[idx, :]

# Matrix pseudoinverse via SVD
tolerance = 1e-10
s_inv = np.array([1/si if si > tolerance else 0 for si in s])
A_pinv = Vt.T @ np.diag(s_inv) @ U.T
```

**Eigenvalue Decomposition**
```python
from numpy.linalg import eig, eigh
from scipy.linalg import eig as scipy_eig

# General matrix (possibly complex eigenvalues)
A = np.random.rand(100, 100)
eigenvalues, eigenvectors = eig(A)

# A @ v = λ * v
# eigenvectors[:, i] corresponds to eigenvalues[i]

# Symmetric/Hermitian matrices (real eigenvalues, orthogonal eigenvectors)
A_sym = (A + A.T) / 2
eigenvalues_sym, eigenvectors_sym = eigh(A_sym)
# eigenvalues are sorted in ascending order

# Verify decomposition
Lambda = np.diag(eigenvalues_sym)
assert np.allclose(A_sym, eigenvectors_sym @ Lambda @ eigenvectors_sym.T)

# Generalized eigenvalue problem: A @ v = λ * B @ v
B = np.random.rand(100, 100)
B_spd = B @ B.T + np.eye(100)
eigenvalues_gen, eigenvectors_gen = scipy_eig(A_sym, B_spd)

# Power iteration for dominant eigenvalue
def power_iteration(A, num_iterations=100):
    v = np.random.rand(A.shape[1])
    for _ in range(num_iterations):
        v = A @ v
        v = v / norm(v)
    eigenvalue = (v @ A @ v) / (v @ v)
    return eigenvalue, v

lambda_max, v_max = power_iteration(A_sym)
```

**QR Decomposition**
```python
from numpy.linalg import qr

# A = Q @ R (Q orthogonal, R upper triangular)
A = np.random.rand(100, 50)

# Full QR (Q is 100x100)
Q_full, R_full = qr(A, mode='complete')

# Economic QR (Q is 100x50, preferred)
Q, R = qr(A, mode='reduced')

# Verify orthogonality
assert np.allclose(Q.T @ Q, np.eye(50))
assert np.allclose(A, Q @ R)

# Applications:
# 1. Least squares (already shown)
# 2. Gram-Schmidt orthogonalization
def gram_schmidt(A):
    Q, R = qr(A)
    return Q

# 3. QR algorithm for eigenvalues
def qr_eigenvalue_algorithm(A, iterations=100):
    A_k = A.copy()
    for _ in range(iterations):
        Q, R = qr(A_k)
        A_k = R @ Q
    # Diagonal of A_k approximates eigenvalues
    return np.diag(A_k)
```

**Cholesky Decomposition**
```python
from numpy.linalg import cholesky
from scipy.linalg import cholesky as scipy_cholesky

# A = L @ L^T (A must be symmetric positive definite)
A_spd = np.random.rand(100, 50)
A_spd = A_spd @ A_spd.T + np.eye(100)  # Force SPD

# Lower triangular
L = cholesky(A_spd)
assert np.allclose(A_spd, L @ L.T)

# Upper triangular (SciPy)
U = scipy_cholesky(A_spd, lower=False)
assert np.allclose(A_spd, U.T @ U)

# Solving Ax = b with Cholesky
# A = L @ L^T => L @ (L^T @ x) = b
# Solve L @ y = b, then L^T @ x = y
from scipy.linalg import solve_triangular

b = np.random.rand(100)
y = solve_triangular(L, b, lower=True)
x = solve_triangular(L.T, y, lower=False)
assert np.allclose(A_spd @ x, b)

# Updating Cholesky factorization (rank-1 update)
def cholesky_rank1_update(L, u):
    """Update L when A' = A + u @ u^T"""
    from scipy.linalg.lapack import dchud
    L_updated, info = dchud(L.T, u)
    return L_updated.T
```

### 4. Dimensionality Reduction

**Principal Component Analysis (PCA)**
```python
from sklearn.decomposition import PCA

# Data matrix: n samples x p features
X = np.random.rand(1000, 100)

# Center the data
X_centered = X - X.mean(axis=0)

# Method 1: SVD-based PCA (preferred for stability)
U, s, Vt = svd(X_centered, full_matrices=False)

# Principal components (eigenvectors of covariance)
components = Vt  # p x p

# Explained variance
explained_variance = (s ** 2) / (X.shape[0] - 1)
explained_variance_ratio = explained_variance / explained_variance.sum()

# Project data onto top k components
k = 10
X_reduced = U[:, :k] @ np.diag(s[:k])

# Reconstruct approximation
X_reconstructed = X_reduced @ Vt[:k, :] + X.mean(axis=0)

# Method 2: Eigendecomposition of covariance matrix
cov_matrix = np.cov(X_centered.T)  # p x p
eigenvalues, eigenvectors = eigh(cov_matrix)

# Sort in descending order
idx = np.argsort(eigenvalues)[::-1]
eigenvalues = eigenvalues[idx]
eigenvectors = eigenvectors[:, idx]

# Same principal components (up to sign)
assert np.allclose(np.abs(components[0]), np.abs(eigenvectors[:, 0]))

# Scikit-learn PCA (recommended for production)
pca = PCA(n_components=10)
X_pca = pca.fit_transform(X)
print(f"Explained variance ratio: {pca.explained_variance_ratio_.sum():.4f}")
```

**Randomized SVD (Fast Approximation)**
```python
from sklearn.utils.extmath import randomized_svd

# For very large matrices, randomized SVD is much faster
A_large = np.random.rand(10000, 5000)
k = 50

# Randomized SVD
U_rand, s_rand, Vt_rand = randomized_svd(A_large, n_components=k, random_state=42)

# Compare with truncated SVD
from scipy.sparse.linalg import svds
U_exact, s_exact, Vt_exact = svds(A_large, k=k)

# Randomized is approximate but much faster
# Error typically < 1% for k << min(m, n)
```

### 5. Sparse Matrices

**Sparse Matrix Operations**
```python
from scipy.sparse import csr_matrix, csc_matrix, lil_matrix
from scipy.sparse.linalg import spsolve, gmres, cg

# Create sparse matrix (row-based for fast row operations)
row = np.array([0, 0, 1, 2, 2, 2])
col = np.array([0, 2, 2, 0, 1, 2])
data = np.array([1, 2, 3, 4, 5, 6])
A_sparse = csr_matrix((data, (row, col)), shape=(3, 3))

# Dense equivalent
A_dense = A_sparse.toarray()

# Matrix-vector multiplication
x = np.array([1, 2, 3])
y = A_sparse @ x  # Fast for sparse matrices

# Solving sparse linear systems
n = 1000
# Create sparse positive definite matrix
from scipy.sparse import diags
A_sparse_spd = diags([1, -2, 1], [-1, 0, 1], shape=(n, n)).tocsr()
A_sparse_spd = A_sparse_spd @ A_sparse_spd.T + diags([10], [0], shape=(n, n))

b = np.random.rand(n)

# Direct solver (LU-based)
x_direct = spsolve(A_sparse_spd, b)

# Iterative solvers (better for very large systems)
# Conjugate gradient (for SPD matrices)
x_cg, info = cg(A_sparse_spd, b, tol=1e-8)

# GMRES (for general matrices)
x_gmres, info = gmres(A_sparse_spd, b, tol=1e-8)

# Check convergence
if info == 0:
    print("Converged successfully")
elif info > 0:
    print(f"Did not converge after {info} iterations")
```

## Patterns and Best Practices

### Pattern 1: Never Invert Matrices
```python
# WRONG: Explicitly computing inverse
A = np.random.rand(100, 100)
b = np.random.rand(100)
x = np.linalg.inv(A) @ b  # Slow and unstable!

# RIGHT: Use solve
x = np.linalg.solve(A, b)  # Fast and stable!

# WRONG: Computing (A^T A)^-1 A^T b (normal equations)
A = np.random.rand(200, 100)
b = np.random.rand(200)
x = np.linalg.inv(A.T @ A) @ A.T @ b  # Numerically unstable!

# RIGHT: Use lstsq
x = np.linalg.lstsq(A, b, rcond=None)[0]  # Stable QR-based!
```

### Pattern 2: Check Conditioning
```python
def solve_with_conditioning_check(A, b, threshold=1e12):
    cond = np.linalg.cond(A)
    if cond > threshold:
        print(f"Warning: Matrix is ill-conditioned (cond={cond:.2e})")
        print("Consider regularization or preconditioning")

    x = np.linalg.solve(A, b)

    # Verify solution
    residual = norm(A @ x - b) / norm(b)
    if residual > 1e-6:
        print(f"Warning: Large residual {residual:.2e}")

    return x
```

### Pattern 3: Memory-Efficient Matrix Operations
```python
# Avoid creating intermediate large matrices
n = 10000

# WRONG: Creates intermediate n x n matrix
A = np.random.rand(n, n)
B = np.random.rand(n, n)
result = (A @ B) @ A.T  # Two n x n intermediates!

# BETTER: Use einsum or explicit ordering
result = A @ (B @ A.T)  # Only one intermediate

# BEST: For complex expressions, use einsum
# result = np.einsum('ij,jk,ki->i', A, B, A)  # No intermediates!
```

### Pattern 4: Numerical Stability
```python
# Computing variance: two-pass algorithm
X = np.random.rand(1000, 100)

# WRONG: Naive variance (numerically unstable)
mean = X.mean(axis=0)
variance_naive = ((X - mean) ** 2).mean(axis=0)

# RIGHT: Use built-in (Welford's algorithm)
variance_stable = np.var(X, axis=0)

# For covariance: use np.cov, not manual computation
cov_stable = np.cov(X.T)
```

## Quick Reference

### Function Selection Guide
```python
# Solving Ax = b:
# - General: np.linalg.solve(A, b)
# - SPD: scipy.linalg.cho_solve(cho_factor(A), b)
# - Sparse: scipy.sparse.linalg.spsolve(A, b)
# - Overdetermined: np.linalg.lstsq(A, b)

# Matrix decomposition:
# - SVD: np.linalg.svd(A) or scipy.sparse.linalg.svds(A, k)
# - Eigenvalues: np.linalg.eigh(A) for symmetric
# - QR: np.linalg.qr(A)
# - Cholesky: np.linalg.cholesky(A) for SPD

# Matrix properties:
# - Norm: np.linalg.norm(A, ord=...)
# - Condition: np.linalg.cond(A)
# - Rank: np.linalg.matrix_rank(A)
# - Determinant: np.linalg.det(A)
```

### Performance Tips
1. Use `@` instead of `np.dot()` for clarity and speed
2. Prefer `solve()` over `inv()` (10x faster, more accurate)
3. Use `eigh()` for symmetric matrices (2x faster than `eig()`)
4. Set `full_matrices=False` in SVD for efficiency
5. Use sparse matrices when >90% zeros
6. Vectorize operations, avoid Python loops
7. Use `einsum()` for complex tensor operations

## Anti-Patterns

### Anti-Pattern 1: Matrix Inversion
```python
# NEVER do this
x = np.linalg.inv(A) @ b

# ALWAYS do this
x = np.linalg.solve(A, b)
```

### Anti-Pattern 2: Ignoring Conditioning
```python
# WRONG: Blindly solving without checking
x = np.linalg.solve(A, b)

# RIGHT: Check condition number first
cond = np.linalg.cond(A)
if cond > 1e12:
    # Add regularization
    A_reg = A + 1e-6 * np.eye(A.shape[0])
    x = np.linalg.solve(A_reg, b)
```

### Anti-Pattern 3: Inefficient Operations
```python
# WRONG: Loop over rows/columns
result = np.zeros(n)
for i in range(n):
    result[i] = A[i, :] @ x

# RIGHT: Vectorize
result = A @ x
```

### Anti-Pattern 4: Premature Densification
```python
# WRONG: Converting sparse to dense unnecessarily
A_sparse = csr_matrix(...)
A_dense = A_sparse.toarray()  # Memory explosion!
x = np.linalg.solve(A_dense, b)

# RIGHT: Use sparse solvers
x = spsolve(A_sparse, b)
```

## Troubleshooting

### Issue: Singular Matrix Error
```python
# Cause: Matrix is not invertible (det = 0 or near 0)
# Solution 1: Check rank
rank = np.linalg.matrix_rank(A)
if rank < A.shape[0]:
    print("Matrix is rank-deficient")

# Solution 2: Add regularization
A_reg = A + lambda_reg * np.eye(A.shape[0])

# Solution 3: Use pseudoinverse
x = np.linalg.pinv(A) @ b
```

### Issue: Slow Performance
```python
# Check if matrix is sparse
sparsity = 1 - np.count_nonzero(A) / A.size
if sparsity > 0.9:
    print("Use sparse matrix format!")
    A_sparse = csr_matrix(A)
```

### Issue: Numerical Instability
```python
# Check condition number
cond = np.linalg.cond(A)
if cond > 1 / np.finfo(float).eps:
    print("Matrix is numerically singular!")
    # Use more stable algorithm or regularization
```

## Related Skills
- `optimization-algorithms.md` - Uses linear algebra for gradients, Hessians
- `numerical-methods.md` - Linear algebra for ODEs, PDEs
- `probability-statistics.md` - Covariance matrices, multivariate distributions
- `data-validation.md` - Matrix data quality checks

## Learning Resources
- NumPy Linear Algebra: https://numpy.org/doc/stable/reference/routines.linalg.html
- SciPy Linear Algebra: https://docs.scipy.org/doc/scipy/reference/linalg.html
- Matrix Computations (Golub & Van Loan)
- Numerical Linear Algebra (Trefethen & Bau)
