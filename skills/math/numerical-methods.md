---
name: math-numerical-methods
description: Solving ordinary differential equations (ODEs)
---



# Numerical Methods

## Metadata
- **Skill ID**: numerical-methods
- **Category**: Mathematics/Numerical Analysis
- **Complexity**: Advanced
- **Last Updated**: 2025-10-18

## Overview
Numerical analysis methods for solving differential equations, integration, root finding, interpolation, and numerical differentiation using SciPy and NumPy. Core techniques for scientific computing and engineering simulations.

## When to Use This Skill
- Solving ordinary differential equations (ODEs)
- Solving partial differential equations (PDEs)
- Numerical integration (quadrature)
- Root finding and equation solving
- Function interpolation and approximation
- Numerical differentiation
- Initial value and boundary value problems

## When NOT to Use This Skill
- Symbolic mathematics (use SymPy)
- When analytical solution is available
- Discrete/combinatorial problems
- Statistical inference (use probability-statistics.md)
- Pure optimization (use optimization-algorithms.md)

## Prerequisites
- Calculus (derivatives, integrals, differential equations)
- Linear algebra basics
- NumPy array operations
- Understanding of numerical stability

## Core Concepts

### 1. Solving Ordinary Differential Equations (ODEs)

**Initial Value Problems (IVP)**
```python
import numpy as np
from scipy.integrate import solve_ivp, odeint
import matplotlib.pyplot as plt

# Example: Exponential decay dy/dt = -k*y, y(0) = y0
def exponential_decay(t, y, k=0.5):
    """
    ODE function in form dy/dt = f(t, y)
    For solve_ivp: signature is f(t, y, *args)
    """
    return -k * y

# Initial condition
y0 = [1.0]
t_span = (0, 10)
t_eval = np.linspace(0, 10, 100)

# Solve using RK45 (default, adaptive Runge-Kutta)
solution = solve_ivp(
    exponential_decay,
    t_span,
    y0,
    t_eval=t_eval,
    method='RK45',  # Explicit Runge-Kutta (4,5)
    dense_output=True  # For continuous solution
)

print(f"Success: {solution.success}")
print(f"Message: {solution.message}")

# Analytical solution for comparison
y_exact = y0[0] * np.exp(-0.5 * t_eval)
error = np.abs(solution.y[0] - y_exact).max()
print(f"Max error: {error:.2e}")

# System of ODEs: Lotka-Volterra (predator-prey)
def lotka_volterra(t, z, alpha=1.0, beta=0.1, delta=0.075, gamma=1.5):
    """
    Predator-prey model:
    dx/dt = alpha*x - beta*x*y    (prey)
    dy/dt = delta*x*y - gamma*y   (predator)
    """
    x, y = z
    return [
        alpha * x - beta * x * y,
        delta * x * y - gamma * y
    ]

z0 = [10, 5]  # Initial populations
solution_lv = solve_ivp(
    lotka_volterra,
    (0, 50),
    z0,
    t_eval=np.linspace(0, 50, 1000),
    method='RK45'
)
```

**Available ODE Solvers**
```python
# Explicit methods (non-stiff):
# - 'RK45': Explicit Runge-Kutta (4,5) - default, good general purpose
# - 'RK23': Explicit Runge-Kutta (2,3) - faster, less accurate
# - 'DOP853': Explicit Runge-Kutta (8,5,3) - high accuracy

# Implicit methods (stiff equations):
# - 'Radau': Implicit Runge-Kutta (5th order)
# - 'BDF': Backward Differentiation Formula
# - 'LSODA': Automatic stiffness detection and switching

# Example: Stiff equation (van der Pol oscillator)
def van_der_pol(t, y, mu=1000):
    """Stiff for large mu"""
    return [y[1], mu * (1 - y[0]**2) * y[1] - y[0]]

# Use stiff solver
solution_stiff = solve_ivp(
    van_der_pol,
    (0, 3000),
    [2.0, 0.0],
    method='Radau',  # Implicit method for stiff problems
    rtol=1e-6,
    atol=1e-9
)
```

**ODE Events (Finding Crossings)**
```python
def projectile(t, y, g=9.81):
    """Projectile motion: y = [x, vx, z, vz]"""
    return [y[1], 0, y[3], -g]

def hit_ground(t, y):
    """Event: projectile hits ground (z=0)"""
    return y[2]  # z-coordinate

hit_ground.terminal = True  # Stop integration when event occurs
hit_ground.direction = -1   # Only detect decreasing (falling)

y0 = [0, 10, 0, 10]  # x, vx, z, vz
solution = solve_ivp(
    projectile,
    (0, 10),
    y0,
    events=hit_ground,
    dense_output=True
)

if solution.t_events[0].size > 0:
    t_impact = solution.t_events[0][0]
    print(f"Projectile hits ground at t={t_impact:.4f}s")
```

**Alternative: odeint (Legacy Interface)**
```python
# odeint uses different signature: f(y, t, *args)
def exponential_decay_odeint(y, t, k=0.5):
    return -k * y

t = np.linspace(0, 10, 100)
y = odeint(exponential_decay_odeint, y0, t)
```

### 2. Numerical Integration (Quadrature)

**Single Integrals**
```python
from scipy.integrate import quad, fixed_quad, simpson, trapezoid

# Example: Integrate f(x) = x^2 from 0 to 1
def f(x):
    return x**2

# Adaptive quadrature (most accurate)
result, error = quad(f, 0, 1)
print(f"Integral: {result:.10f}, Error estimate: {error:.2e}")
# Exact: 1/3 = 0.333333...

# With parameters
def gaussian(x, mu, sigma):
    return np.exp(-0.5 * ((x - mu) / sigma)**2) / (sigma * np.sqrt(2 * np.pi))

integral, _ = quad(gaussian, -np.inf, np.inf, args=(0, 1))
print(f"Gaussian integral: {integral:.10f}")  # Should be 1.0

# Vector-valued integrands
def vector_f(x):
    return [x**2, x**3, np.sin(x)]

result, _ = quad(vector_f, 0, np.pi, full_output=False, vec_func=True)

# Fixed-order Gaussian quadrature (faster, less accurate)
result_fixed, _ = fixed_quad(f, 0, 1, n=5)  # 5-point Gauss-Legendre

# Composite rules (for tabulated data)
x = np.linspace(0, 1, 101)
y = x**2
integral_trap = trapezoid(y, x)  # Trapezoidal rule
integral_simp = simpson(y, x)    # Simpson's rule (more accurate)
```

**Multiple Integrals**
```python
from scipy.integrate import dblquad, tplquad, nquad

# Double integral: ∫∫ x*y dx dy over [0,1] x [0,1]
def integrand_2d(y, x):
    return x * y

result, error = dblquad(integrand_2d, 0, 1, 0, 1)
print(f"Double integral: {result:.6f}")  # Exact: 0.25

# Variable limits: ∫∫ f(x,y) dy dx where y from 0 to x
def integrand(y, x):
    return x * y

result, _ = dblquad(integrand, 0, 1, lambda x: 0, lambda x: x)
print(f"Result: {result:.6f}")  # 1/6

# Triple integral: volume of sphere
def sphere_integrand(phi, theta, r):
    return r**2 * np.sin(theta)

R = 1.0
result, _ = tplquad(
    sphere_integrand,
    0, R,              # r from 0 to R
    lambda r: 0, lambda r: np.pi,     # theta from 0 to pi
    lambda r, theta: 0, lambda r, theta: 2*np.pi  # phi from 0 to 2pi
)
print(f"Sphere volume: {result:.6f}")  # 4/3 * pi * R^3

# n-dimensional integrals
def nd_integrand(x):
    """Integral over n-dimensional unit cube"""
    return np.prod(x)  # x[0] * x[1] * ... * x[n-1]

ranges = [(0, 1)] * 4  # 4D integral
result, _ = nquad(nd_integrand, ranges)
```

**Special Integrals**
```python
from scipy.special import erf
from scipy.integrate import cumulative_trapezoid

# Cumulative integral (indefinite integral at points)
x = np.linspace(0, 2*np.pi, 100)
y = np.sin(x)
cumulative = cumulative_trapezoid(y, x, initial=0)
# cumulative[i] ≈ ∫_0^x[i] sin(t) dt = 1 - cos(x[i])

# Monte Carlo integration (high dimensions)
def monte_carlo_integrate(f, bounds, n_samples=100000):
    """
    Estimate integral of f over hypercube defined by bounds.
    bounds: [(a1,b1), (a2,b2), ..., (an,bn)]
    """
    dim = len(bounds)
    samples = np.random.uniform(
        [b[0] for b in bounds],
        [b[1] for b in bounds],
        size=(n_samples, dim)
    )

    values = np.array([f(s) for s in samples])
    volume = np.prod([b[1] - b[0] for b in bounds])

    return volume * values.mean(), volume * values.std() / np.sqrt(n_samples)

# Example: 10D integral of sum(x_i^2)
def high_dim_f(x):
    return np.sum(x**2)

result, error = monte_carlo_integrate(high_dim_f, [(0, 1)] * 10, n_samples=1000000)
print(f"10D integral: {result:.4f} ± {error:.4f}")
```

### 3. Root Finding

**Scalar Root Finding**
```python
from scipy.optimize import root_scalar, brentq, newton

# Example: Find x where f(x) = x^3 - 2x - 5 = 0
def f(x):
    return x**3 - 2*x - 5

def df(x):
    return 3*x**2 - 2

# Brent's method (bracketing, no derivative needed)
result = root_scalar(f, bracket=[0, 3], method='brentq')
print(f"Root: {result.root:.10f}, Iterations: {result.iterations}")

# Newton-Raphson (needs derivative, faster convergence)
result_newton = root_scalar(f, x0=2, fprime=df, method='newton')
print(f"Root (Newton): {result_newton.root:.10f}")

# Secant method (approximates derivative)
result_secant = root_scalar(f, x0=2, x1=3, method='secant')

# Direct functions for common methods
root_brent = brentq(f, 0, 3)  # Same as brentq method
root_newton = newton(f, 2, fprime=df)  # Newton's method
```

**Multi-Dimensional Root Finding**
```python
from scipy.optimize import root, fsolve

# System of nonlinear equations
def equations(z):
    x, y = z
    return [
        x**2 + y**2 - 4,   # Circle: x^2 + y^2 = 4
        x - y - 1          # Line: x - y = 1
    ]

def jacobian(z):
    x, y = z
    return [
        [2*x, 2*y],
        [1, -1]
    ]

# Newton-like methods
result = root(equations, [1, 1], jac=jacobian, method='hybr')
print(f"Solution: {result.x}")
print(f"Residual: {equations(result.x)}")

# Alternative: fsolve (older interface)
solution = fsolve(equations, [1, 1])

# Verify solutions
x, y = solution
assert np.isclose(x**2 + y**2, 4)
assert np.isclose(x - y, 1)
```

### 4. Interpolation

**1D Interpolation**
```python
from scipy.interpolate import interp1d, CubicSpline, PchipInterpolator

# Data points
x = np.array([0, 1, 2, 3, 4, 5])
y = np.array([0, 1, 4, 9, 16, 25])  # y = x^2

# Linear interpolation
f_linear = interp1d(x, y, kind='linear')

# Cubic spline (smooth)
f_cubic = interp1d(x, y, kind='cubic')

# Natural cubic spline (better extrapolation)
cs = CubicSpline(x, y)

# PCHIP (preserves monotonicity, no overshooting)
pchip = PchipInterpolator(x, y)

# Evaluate
x_new = np.linspace(0, 5, 100)
y_linear = f_linear(x_new)
y_cubic = f_cubic(x_new)
y_cs = cs(x_new)
y_pchip = pchip(x_new)

# Extrapolation
f_extrap = interp1d(x, y, kind='cubic', fill_value='extrapolate')
y_extrap = f_extrap(6.0)  # Extrapolate beyond data range
```

**Multi-Dimensional Interpolation**
```python
from scipy.interpolate import RegularGridInterpolator, griddata

# 2D interpolation on regular grid
x = np.linspace(0, 5, 6)
y = np.linspace(0, 5, 6)
X, Y = np.meshgrid(x, y, indexing='ij')
Z = X**2 + Y**2

# Regular grid interpolator
interp_2d = RegularGridInterpolator((x, y), Z)

# Evaluate at new points
points = np.array([[1.5, 2.5], [3.2, 4.1]])
values = interp_2d(points)

# Irregular (scattered) data interpolation
np.random.seed(0)
points_irreg = np.random.rand(100, 2) * 5
values_irreg = points_irreg[:, 0]**2 + points_irreg[:, 1]**2

# Create regular grid
xi = np.linspace(0, 5, 50)
yi = np.linspace(0, 5, 50)
XI, YI = np.meshgrid(xi, yi)

# Interpolate
ZI = griddata(points_irreg, values_irreg, (XI, YI), method='cubic')
```

### 5. Numerical Differentiation

**Finite Differences**
```python
from scipy.misc import derivative

# Forward difference: f'(x) ≈ (f(x+h) - f(x)) / h
def forward_diff(f, x, h=1e-5):
    return (f(x + h) - f(x)) / h

# Central difference: f'(x) ≈ (f(x+h) - f(x-h)) / (2h)
def central_diff(f, x, h=1e-5):
    return (f(x + h) - f(x - h)) / (2 * h)

# SciPy's derivative (adaptive)
def f(x):
    return np.sin(x)

x = np.pi / 4
df_numerical = derivative(f, x, dx=1e-5)
df_exact = np.cos(x)
print(f"Numerical: {df_numerical:.10f}")
print(f"Exact: {df_exact:.10f}")
print(f"Error: {abs(df_numerical - df_exact):.2e}")

# Higher-order derivatives
d2f = derivative(f, x, dx=1e-5, n=2)  # Second derivative
d2f_exact = -np.sin(x)

# Gradient (multi-dimensional)
from scipy.optimize import approx_fprime

def g(x):
    return x[0]**2 + x[1]**2 + x[2]**2

x0 = np.array([1.0, 2.0, 3.0])
grad_numerical = approx_fprime(x0, g, epsilon=1e-8)
grad_exact = 2 * x0
print(f"Gradient error: {np.linalg.norm(grad_numerical - grad_exact):.2e}")
```

**Numerical Jacobian and Hessian**
```python
from scipy.optimize import approx_fprime

def vector_function(x):
    """f: R^n -> R^m"""
    return np.array([
        x[0]**2 + x[1],
        x[0] * x[1],
        x[1]**2
    ])

def jacobian_finite_diff(f, x, epsilon=1e-8):
    """Compute Jacobian using finite differences"""
    n = len(x)
    f0 = f(x)
    m = len(f0)
    J = np.zeros((m, n))

    for i in range(n):
        x_plus = x.copy()
        x_plus[i] += epsilon
        J[:, i] = (f(x_plus) - f0) / epsilon

    return J

x = np.array([1.0, 2.0])
J = jacobian_finite_diff(vector_function, x)

# Hessian (second derivatives)
from scipy.optimize import approx_fprime

def hessian_finite_diff(f, x, epsilon=1e-5):
    """Compute Hessian using finite differences"""
    n = len(x)
    H = np.zeros((n, n))

    f0 = f(x)
    grad = approx_fprime(x, f, epsilon)

    for i in range(n):
        x_plus = x.copy()
        x_plus[i] += epsilon
        grad_plus = approx_fprime(x_plus, f, epsilon)
        H[:, i] = (grad_plus - grad) / epsilon

    # Symmetrize
    H = (H + H.T) / 2
    return H
```

### 6. Boundary Value Problems (BVP)

**Solving BVPs with solve_bvp**
```python
from scipy.integrate import solve_bvp

# Example: y'' = -y, y(0) = 0, y(pi) = 0
# Convert to first-order system: y1 = y, y2 = y'
# y1' = y2, y2' = -y1

def bvp_ode(x, y):
    """System: [y1', y2'] as function of x and [y1, y2]"""
    return np.vstack([y[1], -y[0]])

def boundary_conditions(ya, yb):
    """Residuals at boundaries: should be zero"""
    return np.array([ya[0], yb[0]])  # y(0) = 0, y(pi) = 0

# Initial mesh
x = np.linspace(0, np.pi, 5)
y_guess = np.zeros((2, x.size))
y_guess[0] = np.sin(x)  # Initial guess for y
y_guess[1] = np.cos(x)  # Initial guess for y'

solution = solve_bvp(bvp_ode, boundary_conditions, x, y_guess)

# Evaluate on fine mesh
x_plot = np.linspace(0, np.pi, 100)
y_plot = solution.sol(x_plot)[0]

# Exact solution: y = C * sin(x)
```

## Patterns and Best Practices

### Pattern 1: Error Estimation
```python
def richardson_extrapolation(f, x, h, order=2):
    """
    Improve finite difference accuracy using Richardson extrapolation.
    """
    D1 = (f(x + h) - f(x - h)) / (2 * h)
    D2 = (f(x + h/2) - f(x - h/2)) / h

    # Richardson extrapolation
    D_improved = (2**order * D2 - D1) / (2**order - 1)
    return D_improved
```

### Pattern 2: Adaptive Step Size
```python
def adaptive_integration(f, a, b, tol=1e-6):
    """
    Adaptive Simpson's rule: subdivide where error is large.
    """
    def simpson_rule(f, a, b):
        h = (b - a) / 2
        return h/3 * (f(a) + 4*f(a+h) + f(b))

    def adaptive_simpson(a, b, tol, whole):
        c = (a + b) / 2
        left = simpson_rule(f, a, c)
        right = simpson_rule(f, c, b)

        if abs(left + right - whole) < 15 * tol:
            return left + right
        else:
            return (adaptive_simpson(a, c, tol/2, left) +
                    adaptive_simpson(c, b, tol/2, right))

    whole = simpson_rule(f, a, b)
    return adaptive_simpson(a, b, tol, whole)
```

### Pattern 3: Stability Analysis
```python
def check_stiffness(f, t_span, y0, threshold=100):
    """
    Estimate stiffness ratio of ODE system.
    """
    from scipy.linalg import eigvals

    # Jacobian at initial point
    def jacobian_fd(t, y):
        n = len(y)
        J = np.zeros((n, n))
        eps = 1e-8
        f0 = f(t, y)
        for i in range(n):
            y_plus = y.copy()
            y_plus[i] += eps
            J[:, i] = (f(t, y_plus) - f0) / eps
        return J

    J = jacobian_fd(t_span[0], y0)
    eigs = eigvals(J)

    stiffness_ratio = abs(max(eigs.real) / min(eigs.real))

    if stiffness_ratio > threshold:
        print(f"System is stiff (ratio: {stiffness_ratio:.2e})")
        print("Use implicit solver: 'Radau' or 'BDF'")
    else:
        print("System is non-stiff")
        print("Use explicit solver: 'RK45' or 'DOP853'")

    return stiffness_ratio
```

## Quick Reference

### ODE Solver Selection
```python
# Non-stiff: RK45 (default), DOP853 (high accuracy)
# Stiff: Radau, BDF
# Auto-switching: LSODA
# rtol, atol: relative and absolute tolerances (default: 1e-3, 1e-6)
```

### Integration Method Selection
```python
# Smooth functions: quad (adaptive)
# Tabulated data: simpson (accurate), trapezoid (simple)
# High dimensions: Monte Carlo
# Infinite limits: quad with ±np.inf
```

## Anti-Patterns

### Anti-Pattern 1: Too Large Step Size
```python
# WRONG: Using fixed large step in finite differences
h = 0.1
df = (f(x + h) - f(x)) / h  # Large error!

# RIGHT: Use small h or adaptive methods
from scipy.misc import derivative
df = derivative(f, x, dx=1e-5)
```

### Anti-Pattern 2: Ignoring Stiffness
```python
# WRONG: Using explicit method for stiff ODE
solution = solve_ivp(stiff_ode, t_span, y0, method='RK45')  # Will be slow!

# RIGHT: Use implicit method
solution = solve_ivp(stiff_ode, t_span, y0, method='Radau')
```

### Anti-Pattern 3: Poor Interpolation Choice
```python
# WRONG: Cubic spline for non-smooth data
f = interp1d(x, y, kind='cubic')  # May oscillate!

# RIGHT: Use PCHIP for monotonic data
from scipy.interpolate import PchipInterpolator
f = PchipInterpolator(x, y)  # No overshooting
```

## Related Skills
- `linear-algebra-computation.md` - Linear solvers for numerical methods
- `optimization-algorithms.md` - Optimization for parameter fitting
- `probability-statistics.md` - Statistical analysis of numerical results

## Learning Resources
- SciPy Documentation: https://docs.scipy.org/doc/scipy/reference/
- Numerical Recipes (Press et al.)
- Numerical Methods for Engineers (Chapra & Canale)
