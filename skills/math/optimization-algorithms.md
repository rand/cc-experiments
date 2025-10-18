---
name: math-optimization-algorithms
description: Machine learning model training (gradient descent, Adam, SGD)
---



# Optimization Algorithms

## Metadata
- **Skill ID**: optimization-algorithms
- **Category**: Mathematics/Optimization
- **Complexity**: Advanced
- **Last Updated**: 2025-10-18

## Overview
Numerical optimization algorithms for unconstrained and constrained problems using SciPy and custom implementations. Covers gradient descent variants, Newton methods, convex optimization, and operations research applications.

## When to Use This Skill
- Machine learning model training (gradient descent, Adam, SGD)
- Parameter tuning and hyperparameter optimization
- Resource allocation and operations research
- Curve fitting and nonlinear regression
- Constrained optimization (linear/quadratic programming)
- Portfolio optimization and economics
- Engineering design optimization

## When NOT to Use This Skill
- Symbolic optimization (use SymPy)
- Discrete/combinatorial optimization (use OR-Tools, Gurobi)
- Multi-objective optimization without scalarization
- Global optimization of highly non-convex functions (use evolutionary algorithms)
- When analytical solution exists

## Prerequisites
- Linear algebra basics
- Calculus (derivatives, gradients)
- NumPy array operations
- Understanding of convexity concepts

## Core Concepts

### 1. Unconstrained Optimization Basics

**Gradient Descent Framework**
```python
import numpy as np
from numpy.linalg import norm

def gradient_descent(f, grad_f, x0, lr=0.01, max_iter=1000, tol=1e-6):
    """
    Minimize f(x) using gradient descent.

    Args:
        f: Objective function
        grad_f: Gradient of f
        x0: Initial point
        lr: Learning rate
        max_iter: Maximum iterations
        tol: Convergence tolerance
    """
    x = x0.copy()
    history = {'x': [x.copy()], 'f': [f(x)]}

    for i in range(max_iter):
        grad = grad_f(x)
        x_new = x - lr * grad

        # Check convergence
        if norm(x_new - x) < tol:
            print(f"Converged in {i+1} iterations")
            break

        x = x_new
        history['x'].append(x.copy())
        history['f'].append(f(x))

    return x, history

# Example: Minimize f(x) = x^T A x - b^T x (quadratic)
n = 10
A = np.random.rand(n, n)
A = A @ A.T + np.eye(n)  # Make positive definite
b = np.random.rand(n)

def f(x):
    return 0.5 * x @ A @ x - b @ x

def grad_f(x):
    return A @ x - b

x0 = np.random.rand(n)
x_opt, history = gradient_descent(f, grad_f, x0, lr=0.01)

# Analytical solution: A x = b
x_exact = np.linalg.solve(A, b)
print(f"Error: {norm(x_opt - x_exact):.2e}")
```

**Momentum and Acceleration**
```python
def momentum_gd(f, grad_f, x0, lr=0.01, momentum=0.9, max_iter=1000, tol=1e-6):
    """Gradient descent with momentum (Polyak, 1964)"""
    x = x0.copy()
    v = np.zeros_like(x)  # Velocity

    for i in range(max_iter):
        grad = grad_f(x)
        v = momentum * v - lr * grad
        x_new = x + v

        if norm(x_new - x) < tol:
            break

        x = x_new

    return x

def nesterov_gd(f, grad_f, x0, lr=0.01, momentum=0.9, max_iter=1000, tol=1e-6):
    """Nesterov accelerated gradient (NAG)"""
    x = x0.copy()
    v = np.zeros_like(x)

    for i in range(max_iter):
        # Look ahead
        x_ahead = x + momentum * v
        grad = grad_f(x_ahead)

        v = momentum * v - lr * grad
        x_new = x + v

        if norm(x_new - x) < tol:
            break

        x = x_new

    return x
```

### 2. Adaptive Learning Rate Methods

**Adam Optimizer**
```python
def adam(f, grad_f, x0, lr=0.001, beta1=0.9, beta2=0.999,
         eps=1e-8, max_iter=1000, tol=1e-6):
    """
    Adam: Adaptive Moment Estimation (Kingma & Ba, 2015)
    Most popular optimizer for deep learning.
    """
    x = x0.copy()
    m = np.zeros_like(x)  # First moment (mean)
    v = np.zeros_like(x)  # Second moment (variance)

    for t in range(1, max_iter + 1):
        grad = grad_f(x)

        # Update biased first moment estimate
        m = beta1 * m + (1 - beta1) * grad

        # Update biased second moment estimate
        v = beta2 * v + (1 - beta2) * (grad ** 2)

        # Bias correction
        m_hat = m / (1 - beta1 ** t)
        v_hat = v / (1 - beta2 ** t)

        # Update parameters
        x_new = x - lr * m_hat / (np.sqrt(v_hat) + eps)

        if norm(x_new - x) < tol:
            break

        x = x_new

    return x

def rmsprop(f, grad_f, x0, lr=0.01, decay=0.9, eps=1e-8,
            max_iter=1000, tol=1e-6):
    """RMSprop: Root Mean Square Propagation (Hinton)"""
    x = x0.copy()
    cache = np.zeros_like(x)

    for i in range(max_iter):
        grad = grad_f(x)

        # Accumulate squared gradient
        cache = decay * cache + (1 - decay) * (grad ** 2)

        # Update with normalized gradient
        x_new = x - lr * grad / (np.sqrt(cache) + eps)

        if norm(x_new - x) < tol:
            break

        x = x_new

    return x

def adagrad(f, grad_f, x0, lr=0.01, eps=1e-8, max_iter=1000, tol=1e-6):
    """AdaGrad: Adaptive Gradient (Duchi et al., 2011)"""
    x = x0.copy()
    cache = np.zeros_like(x)

    for i in range(max_iter):
        grad = grad_f(x)

        # Accumulate all squared gradients
        cache += grad ** 2

        # Adaptive learning rate per parameter
        x_new = x - lr * grad / (np.sqrt(cache) + eps)

        if norm(x_new - x) < tol:
            break

        x = x_new

    return x
```

### 3. Newton and Quasi-Newton Methods

**Newton's Method**
```python
def newton_method(f, grad_f, hess_f, x0, max_iter=100, tol=1e-6):
    """
    Newton's method: uses second-order information (Hessian).
    Quadratic convergence near minimum.
    """
    x = x0.copy()

    for i in range(max_iter):
        grad = grad_f(x)
        hess = hess_f(x)

        # Solve H * delta = -grad
        delta = np.linalg.solve(hess, -grad)
        x_new = x + delta

        if norm(delta) < tol:
            print(f"Converged in {i+1} iterations")
            break

        x = x_new

    return x

# Example: Rosenbrock function
def rosenbrock(x):
    return 100 * (x[1] - x[0]**2)**2 + (1 - x[0])**2

def rosenbrock_grad(x):
    return np.array([
        -400 * x[0] * (x[1] - x[0]**2) - 2 * (1 - x[0]),
        200 * (x[1] - x[0]**2)
    ])

def rosenbrock_hess(x):
    return np.array([
        [1200 * x[0]**2 - 400 * x[1] + 2, -400 * x[0]],
        [-400 * x[0], 200]
    ])

x0 = np.array([0.0, 0.0])
x_opt = newton_method(rosenbrock, rosenbrock_grad, rosenbrock_hess, x0)
print(f"Optimum: {x_opt}, f(x*) = {rosenbrock(x_opt):.2e}")
```

**BFGS (Quasi-Newton)**
```python
def bfgs(f, grad_f, x0, max_iter=100, tol=1e-6):
    """
    BFGS: Broyden-Fletcher-Goldfarb-Shanno algorithm.
    Approximates Hessian inverse using gradient information only.
    """
    x = x0.copy()
    n = len(x)
    H = np.eye(n)  # Initial Hessian inverse approximation

    grad = grad_f(x)

    for i in range(max_iter):
        # Search direction
        p = -H @ grad

        # Line search (simplified backtracking)
        alpha = 1.0
        while f(x + alpha * p) > f(x) + 1e-4 * alpha * grad @ p:
            alpha *= 0.5
            if alpha < 1e-10:
                break

        # Update
        x_new = x + alpha * p
        grad_new = grad_f(x_new)

        # Check convergence
        if norm(grad_new) < tol:
            print(f"Converged in {i+1} iterations")
            break

        # BFGS update of Hessian inverse
        s = x_new - x
        y = grad_new - grad

        rho = 1.0 / (y @ s)
        if rho > 0:  # Ensure positive definiteness
            I = np.eye(n)
            H = (I - rho * np.outer(s, y)) @ H @ (I - rho * np.outer(y, s)) + rho * np.outer(s, s)

        x = x_new
        grad = grad_new

    return x

# Compare with SciPy implementation
from scipy.optimize import minimize

result = minimize(rosenbrock, x0, method='BFGS', jac=rosenbrock_grad)
print(f"SciPy BFGS: {result.x}, f(x*) = {result.fun:.2e}")
```

**L-BFGS (Limited-Memory BFGS)**
```python
from scipy.optimize import minimize

# L-BFGS: More efficient for high-dimensional problems
# Only stores a few vectors instead of full Hessian approximation

def high_dim_function(x):
    # Example: L2 regularized logistic regression
    # Assume X, y are data matrices/vectors
    pass

result = minimize(
    rosenbrock,
    x0,
    method='L-BFGS-B',  # Bounded L-BFGS
    jac=rosenbrock_grad,
    bounds=[(-2, 2), (-2, 2)]  # Box constraints
)
```

### 4. Constrained Optimization

**Linear Programming**
```python
from scipy.optimize import linprog

# Minimize c^T x subject to:
# A_ub @ x <= b_ub (inequality constraints)
# A_eq @ x == b_eq (equality constraints)
# bounds on x

# Example: Diet problem
# Minimize cost: 2*x1 + 3*x2 (x1=bread, x2=milk)
c = np.array([2, 3])

# Constraints: at least 10 units protein, 8 units vitamins
# x1 + 2*x2 >= 10 => -x1 - 2*x2 <= -10
# 2*x1 + x2 >= 8  => -2*x1 - x2 <= -8
A_ub = np.array([[-1, -2], [-2, -1]])
b_ub = np.array([-10, -8])

# Non-negativity
bounds = [(0, None), (0, None)]

result = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method='highs')
print(f"Optimal solution: {result.x}")
print(f"Minimum cost: {result.fun:.2f}")
```

**Quadratic Programming**
```python
from scipy.optimize import minimize

# Minimize 0.5 x^T H x + f^T x subject to constraints

# Example: Portfolio optimization
# Minimize variance: 0.5 x^T Sigma x
# Subject to: sum(x) = 1 (fully invested)
#             mu^T x >= target_return (return constraint)
#             x >= 0 (long only)

n_assets = 5
np.random.seed(42)

# Covariance matrix (risk)
Sigma = np.random.rand(n_assets, n_assets)
Sigma = Sigma @ Sigma.T  # Ensure positive semi-definite

# Expected returns
mu = np.random.rand(n_assets) * 0.1 + 0.05
target_return = 0.08

def portfolio_variance(x):
    return 0.5 * x @ Sigma @ x

def portfolio_variance_grad(x):
    return Sigma @ x

# Constraints
constraints = [
    {'type': 'eq', 'fun': lambda x: np.sum(x) - 1},  # Fully invested
    {'type': 'ineq', 'fun': lambda x: mu @ x - target_return}  # Return target
]

# Bounds: long only
bounds = [(0, 1) for _ in range(n_assets)]

x0 = np.ones(n_assets) / n_assets  # Equal weight initial guess

result = minimize(
    portfolio_variance,
    x0,
    method='SLSQP',  # Sequential Least Squares Programming
    jac=portfolio_variance_grad,
    bounds=bounds,
    constraints=constraints
)

print(f"Optimal portfolio: {result.x}")
print(f"Expected return: {mu @ result.x:.4f}")
print(f"Portfolio variance: {result.fun:.6f}")
```

**Non-Linear Constrained Optimization**
```python
from scipy.optimize import minimize, NonlinearConstraint

# Example: Minimize Rosenbrock with circle constraint
# min f(x) s.t. x[0]^2 + x[1]^2 <= 1

def constraint_fun(x):
    return 1 - (x[0]**2 + x[1]**2)  # >= 0

def constraint_jac(x):
    return np.array([-2*x[0], -2*x[1]])

# Method 1: Dictionary constraint
constraint = {'type': 'ineq', 'fun': constraint_fun, 'jac': constraint_jac}

result = minimize(
    rosenbrock,
    x0,
    method='SLSQP',
    jac=rosenbrock_grad,
    constraints=constraint
)

# Method 2: NonlinearConstraint (more general)
nlc = NonlinearConstraint(
    lambda x: x[0]**2 + x[1]**2,  # Constraint function
    -np.inf,  # Lower bound
    1,  # Upper bound
    jac=lambda x: np.array([2*x[0], 2*x[1]])
)

result2 = minimize(
    rosenbrock,
    x0,
    method='trust-constr',  # Interior point method
    jac=rosenbrock_grad,
    hess=rosenbrock_hess,
    constraints=nlc
)
```

### 5. Special Optimization Problems

**Least Squares (Levenberg-Marquardt)**
```python
from scipy.optimize import least_squares

# Nonlinear least squares: min sum_i r_i(x)^2
# where r(x) is residual vector

# Example: Curve fitting to exponential decay
t = np.linspace(0, 5, 50)
y_true = 3 * np.exp(-0.5 * t) + 0.1 * np.random.randn(50)

def residuals(params, t, y):
    a, b = params
    return y - a * np.exp(-b * t)

def jacobian(params, t, y):
    a, b = params
    J = np.zeros((len(t), 2))
    J[:, 0] = -np.exp(-b * t)
    J[:, 1] = a * t * np.exp(-b * t)
    return J

params0 = [1.0, 0.1]
result = least_squares(
    residuals,
    params0,
    args=(t, y_true),
    jac=jacobian,
    method='lm'  # Levenberg-Marquardt
)

print(f"Fitted parameters: a={result.x[0]:.4f}, b={result.x[1]:.4f}")
```

**Convex Optimization (CVXPY)**
```python
import cvxpy as cp

# Example: L1-regularized regression (Lasso)
# min ||Ax - b||_2^2 + lambda ||x||_1

n, m = 100, 50
np.random.seed(0)
A = np.random.randn(n, m)
x_true = np.random.randn(m)
x_true[m//2:] = 0  # Sparse
b = A @ x_true + 0.1 * np.random.randn(n)

x = cp.Variable(m)
lambda_reg = 0.1

objective = cp.Minimize(
    cp.sum_squares(A @ x - b) + lambda_reg * cp.norm1(x)
)

problem = cp.Problem(objective)
problem.solve()

print(f"Optimal value: {problem.value:.4f}")
print(f"Non-zeros in solution: {np.sum(np.abs(x.value) > 1e-3)}")
```

## Patterns and Best Practices

### Pattern 1: Algorithm Selection
```python
def select_optimizer(problem_type, dim, has_gradient, has_hessian, constrained):
    """
    Guide for selecting optimization algorithm.
    """
    if constrained:
        if problem_type == 'linear':
            return 'linprog (simplex or interior-point)'
        elif problem_type == 'quadratic':
            return 'minimize with SLSQP or trust-constr'
        elif problem_type == 'convex':
            return 'CVXPY or trust-constr'
        else:
            return 'SLSQP or trust-constr with constraints'
    else:
        if dim < 10:
            if has_hessian:
                return 'Newton method'
            elif has_gradient:
                return 'BFGS'
            else:
                return 'Nelder-Mead'
        elif dim < 1000:
            if has_gradient:
                return 'L-BFGS-B'
            else:
                return 'Powell or CG'
        else:  # High dimensional
            if has_gradient:
                return 'Adam or L-BFGS-B'
            else:
                return 'L-BFGS-B (numerical gradients)'
```

### Pattern 2: Hyperparameter Tuning
```python
from scipy.optimize import differential_evolution

# Global optimization for hyperparameter search
def objective(params):
    lr, momentum = params
    # Train model with these hyperparameters
    # Return validation loss
    return validation_loss

bounds = [(1e-4, 1e-1), (0.5, 0.99)]  # [lr, momentum]

result = differential_evolution(
    objective,
    bounds,
    maxiter=100,
    seed=42,
    workers=-1  # Parallel evaluation
)

best_lr, best_momentum = result.x
```

### Pattern 3: Multi-Start Optimization
```python
def multi_start_optimization(f, grad_f, bounds, n_starts=10):
    """
    Run optimization from multiple random starting points.
    Helps escape local minima.
    """
    best_x = None
    best_f = np.inf

    for i in range(n_starts):
        # Random starting point
        x0 = np.random.uniform(bounds[:, 0], bounds[:, 1])

        result = minimize(f, x0, method='L-BFGS-B', jac=grad_f, bounds=bounds)

        if result.fun < best_f:
            best_f = result.fun
            best_x = result.x

    return best_x, best_f
```

### Pattern 4: Convergence Monitoring
```python
class OptimizationLogger:
    def __init__(self):
        self.history = {'x': [], 'f': [], 'grad_norm': []}

    def __call__(self, xk):
        """Callback for scipy.optimize.minimize"""
        self.history['x'].append(xk.copy())
        self.history['f'].append(f(xk))
        self.history['grad_norm'].append(norm(grad_f(xk)))

logger = OptimizationLogger()
result = minimize(f, x0, method='BFGS', jac=grad_f, callback=logger)

# Plot convergence
import matplotlib.pyplot as plt
plt.semilogy(logger.history['grad_norm'])
plt.xlabel('Iteration')
plt.ylabel('Gradient Norm')
plt.title('Convergence History')
```

## Quick Reference

### SciPy Optimize Methods
```python
# Unconstrained:
# - 'BFGS': General-purpose, needs gradient
# - 'L-BFGS-B': High-dimensional, supports bounds
# - 'Newton-CG': Needs Hessian or Hessian-vector product
# - 'trust-ncg': Trust region, needs Hessian
# - 'Nelder-Mead': Derivative-free, slow but robust

# Constrained:
# - 'SLSQP': Sequential Least Squares, general constraints
# - 'trust-constr': Interior point, very general
# - 'COBYLA': Derivative-free, only inequality constraints

# Global:
# - differential_evolution: Genetic algorithm
# - dual_annealing: Simulated annealing
# - shgo: Simplicial homology
# - basinhopping: Random perturbations + local search
```

### Learning Rate Selection
```python
# Rule of thumb for gradient descent:
# lr = 1 / L where L is Lipschitz constant of gradient
# For quadratic f(x) = 0.5 x^T A x: L = largest eigenvalue of A

def estimate_lipschitz_lr(grad_f, x0, n_samples=10):
    """Estimate safe learning rate"""
    grads = []
    for _ in range(n_samples):
        x = x0 + 0.1 * np.random.randn(len(x0))
        grads.append(grad_f(x))

    # Estimate Lipschitz constant
    L = max([norm(g) for g in grads]) / 0.1
    return 1.0 / L if L > 0 else 0.01
```

## Anti-Patterns

### Anti-Pattern 1: Wrong Learning Rate
```python
# WRONG: Fixed learning rate without tuning
x_opt = gradient_descent(f, grad_f, x0, lr=0.01)  # May diverge or be too slow

# RIGHT: Use line search or adaptive method
result = minimize(f, x0, method='BFGS', jac=grad_f)
# Or use Adam for non-convex problems
```

### Anti-Pattern 2: Ignoring Constraints
```python
# WRONG: Projecting after unconstrained optimization
x_opt = minimize(f, x0, method='BFGS').x
x_opt = np.clip(x_opt, 0, 1)  # Approximate projection

# RIGHT: Use constrained optimizer
result = minimize(f, x0, method='L-BFGS-B', bounds=[(0, 1)] * len(x0))
```

### Anti-Pattern 3: Poor Initialization
```python
# WRONG: Starting from zero or random
x0 = np.zeros(n)  # May be saddle point

# RIGHT: Use domain knowledge or multiple starts
x0 = compute_reasonable_initial_guess()
# Or use multi-start strategy
```

### Anti-Pattern 4: Not Checking Convergence
```python
# WRONG: Assuming optimization succeeded
result = minimize(f, x0, method='BFGS')
x_opt = result.x  # May not have converged!

# RIGHT: Check result status
if not result.success:
    print(f"Optimization failed: {result.message}")
    print(f"Gradient norm: {norm(grad_f(result.x))}")
```

## Troubleshooting

### Issue: Slow Convergence
```python
# Check gradient computation
from scipy.optimize import check_grad
err = check_grad(f, grad_f, x0)
if err > 1e-5:
    print("Gradient implementation may be incorrect!")

# Try different method
result = minimize(f, x0, method='L-BFGS-B', jac=grad_f)
```

### Issue: Divergence
```python
# Reduce learning rate or add line search
# Check if problem is convex
# Verify gradient correctness
# Add regularization
```

### Issue: Getting Stuck in Local Minimum
```python
# Use global optimization
from scipy.optimize import basinhopping

minimizer_kwargs = {"method": "BFGS", "jac": grad_f}
result = basinhopping(f, x0, minimizer_kwargs=minimizer_kwargs, niter=100)
```

## Related Skills
- `linear-algebra-computation.md` - Matrix operations for optimization
- `numerical-methods.md` - Numerical differentiation, integration
- `probability-statistics.md` - Stochastic optimization, Bayesian optimization

## Learning Resources
- SciPy Optimize: https://docs.scipy.org/doc/scipy/reference/optimize.html
- CVXPY: https://www.cvxpy.org/
- Numerical Optimization (Nocedal & Wright)
- Convex Optimization (Boyd & Vandenberghe)
