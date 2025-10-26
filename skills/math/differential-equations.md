---
name: differential-equations
description: Differential equations including ODEs, PDEs, analytical methods, numerical solutions
---

# Differential Equations

**Scope**: ODEs, PDEs, analytical and numerical methods, stability analysis
**Lines**: ~400
**Last Updated**: 2025-10-25

## When to Use This Skill

Activate this skill when:
- Solving ordinary differential equations (ODEs) analytically or numerically
- Working with partial differential equations (heat, wave, Laplace)
- Modeling dynamical systems and physical phenomena
- Analyzing stability of equilibrium points
- Implementing numerical integrators (Euler, Runge-Kutta)
- Solving boundary value problems

## Core Concepts

### First-Order ODEs

**Standard form**: dy/dx = f(x, y)

**Methods**:
- Separable: dy/dx = g(x)h(y)
- Linear: dy/dx + P(x)y = Q(x)
- Exact: M(x,y)dx + N(x,y)dy = 0

```python
import numpy as np
from scipy.integrate import solve_ivp
import matplotlib.pyplot as plt

# Example: dy/dx = -2xy, y(0) = 1
# Analytical solution: y = exp(-x²)

def exponential_decay(x, y):
    return -2 * x * y[0]

# Solve numerically
sol = solve_ivp(exponential_decay, [0, 3], [1], dense_output=True)
x_vals = np.linspace(0, 3, 100)
y_vals = sol.sol(x_vals)[0]

# Compare with analytical
y_exact = np.exp(-x_vals**2)
error = np.max(np.abs(y_vals - y_exact))
print(f"Max error: {error:.2e}")
```

### Second-Order ODEs

**Linear constant coefficients**: y'' + ay' + by = 0

**Characteristic equation**: r² + ar + b = 0
- Distinct real roots: y = c₁e^(r₁x) + c₂e^(r₂x)
- Repeated root: y = (c₁ + c₂x)e^(rx)
- Complex roots r = α ± iβ: y = e^(αx)(c₁cos(βx) + c₂sin(βx))

```python
def harmonic_oscillator(t, y):
    """
    d²x/dt² + 2ζω₀(dx/dt) + ω₀²x = 0
    Damped harmonic oscillator
    State: [x, dx/dt]
    """
    omega_0 = 2.0  # Natural frequency
    zeta = 0.1     # Damping ratio

    x, v = y
    dxdt = v
    dvdt = -2*zeta*omega_0*v - omega_0**2*x

    return [dxdt, dvdt]

# Initial conditions: x(0)=1, v(0)=0
sol = solve_ivp(harmonic_oscillator, [0, 10], [1, 0], dense_output=True)
t = np.linspace(0, 10, 200)
x = sol.sol(t)[0]
```

### Partial Differential Equations

**Heat equation**: ∂u/∂t = α∇²u
**Wave equation**: ∂²u/∂t² = c²∇²u
**Laplace equation**: ∇²u = 0

```python
from scipy.sparse import diags
from scipy.sparse.linalg import spsolve

def solve_heat_equation_1d(L, T, nx, nt, alpha=1.0):
    """
    Solve ∂u/∂t = α∂²u/∂x² on [0,L] × [0,T]
    Using finite differences
    """
    dx = L / (nx - 1)
    dt = T / (nt - 1)

    # Stability: dt ≤ dx²/(2α)
    r = alpha * dt / dx**2
    if r > 0.5:
        print(f"Warning: r={r:.3f} > 0.5, may be unstable")

    # Initialize
    u = np.zeros((nt, nx))
    u[0, :] = np.sin(np.pi * np.linspace(0, L, nx) / L)  # Initial condition

    # Time stepping (explicit method)
    for n in range(nt - 1):
        for i in range(1, nx - 1):
            u[n+1, i] = u[n, i] + r * (u[n, i+1] - 2*u[n, i] + u[n, i-1])
        # Boundary conditions: u = 0 at x=0, x=L
        u[n+1, 0] = 0
        u[n+1, -1] = 0

    return u

# Solve
u = solve_heat_equation_1d(L=1.0, T=0.5, nx=50, nt=100, alpha=0.01)
```

### Numerical Methods

**Euler method**: y_{n+1} = y_n + h·f(x_n, y_n)

**Runge-Kutta 4th order (RK4)**:
```python
def rk4_step(f, x, y, h):
    """Single RK4 step"""
    k1 = f(x, y)
    k2 = f(x + h/2, y + h*k1/2)
    k3 = f(x + h/2, y + h*k2/2)
    k4 = f(x + h, y + h*k3)

    return y + h * (k1 + 2*k2 + 2*k3 + k4) / 6

def rk4_solve(f, x0, y0, x_end, h):
    """RK4 integration"""
    xs = [x0]
    ys = [y0]

    x, y = x0, y0
    while x < x_end:
        y = rk4_step(f, x, y, h)
        x += h
        xs.append(x)
        ys.append(y)

    return np.array(xs), np.array(ys)
```

### Phase Plane Analysis

**Autonomous system**: dx/dt = f(x, y), dy/dt = g(x, y)

**Equilibrium points**: f(x*, y*) = 0, g(x*, y*) = 0

**Stability**: Linearize via Jacobian

```python
def phase_plane_example():
    """Lotka-Volterra predator-prey model"""
    def lotka_volterra(t, z):
        x, y = z  # x=prey, y=predator
        alpha, beta, delta, gamma = 1.0, 0.1, 0.075, 1.5

        dxdt = alpha*x - beta*x*y
        dydt = delta*x*y - gamma*y

        return [dxdt, dydt]

    # Find equilibrium
    # x* = gamma/delta, y* = alpha/beta

    # Jacobian at equilibrium
    def jacobian_at_equilibrium():
        alpha, beta, delta, gamma = 1.0, 0.1, 0.075, 1.5
        x_star = gamma / delta
        y_star = alpha / beta

        J = np.array([
            [0, -beta*x_star],
            [delta*y_star, 0]
        ])

        eigenvalues = np.linalg.eigvals(J)
        return eigenvalues  # Pure imaginary → center (neutrally stable)

    return lotka_volterra, jacobian_at_equilibrium()
```

---

## Patterns

### Pattern 1: Separation of Variables

For PDEs of form ∂u/∂t = L[u] where L is spatial operator:
Assume u(x,t) = X(x)T(t)

```python
# Heat equation: u(x,t) = Σ c_n·sin(nπx/L)·exp(-n²π²αt/L²)
```

### Pattern 2: Method of Characteristics

For first-order PDEs: a(x,y)u_x + b(x,y)u_y = c(x,y,u)

Characteristic curves: dx/a = dy/b = du/c

### Pattern 3: Finite Element Method

For BVPs: weak formulation → Galerkin method

```python
from scipy.sparse import lil_matrix
from scipy.sparse.linalg import spsolve

def fem_1d_poisson(n_elements, f):
    """-u'' = f on [0,1], u(0)=u(1)=0"""
    n = n_elements + 1
    h = 1.0 / n_elements

    # Stiffness matrix
    K = lil_matrix((n, n))
    F = np.zeros(n)

    for i in range(1, n-1):
        K[i, i] = 2/h
        K[i, i-1] = -1/h
        K[i, i+1] = -1/h
        F[i] = f(i*h) * h

    # Apply boundary conditions (already u[0]=u[-1]=0)
    K = K.tocsr()
    u = spsolve(K[1:-1, 1:-1], F[1:-1])

    return np.concatenate([[0], u, [0]])
```

---

## Quick Reference

### ODE Types and Solutions

| Type | Form | Method |
|------|------|--------|
| Separable | dy/dx = g(x)h(y) | Integrate both sides |
| Linear 1st order | y' + P(x)y = Q(x) | Integrating factor |
| Bernoulli | y' + P(x)y = Q(x)y^n | Substitution v = y^(1-n) |
| Homogeneous 2nd | y'' + ay' + by = 0 | Characteristic equation |
| Variation of parameters | y'' + ay' + by = f(x) | Particular solution |

### PDE Classification

| Type | Form | Example |
|------|------|---------|
| Parabolic | B² - AC = 0 | Heat equation |
| Hyperbolic | B² - AC > 0 | Wave equation |
| Elliptic | B² - AC < 0 | Laplace equation |

---

## Anti-Patterns

❌ **Ignoring stability**: Using Euler method with large step size
✅ Check CFL condition for explicit methods

❌ **Not checking existence/uniqueness**: Assuming solution exists
✅ Verify Lipschitz condition for existence theorems

❌ **Using analytical methods only**: Many DEs have no closed form
✅ Combine analytical insights with numerical methods

---

## Related Skills

- `numerical-methods.md` - Numerical integration, root finding
- `linear-algebra-computation.md` - Matrix methods for systems
- `optimization-algorithms.md` - Optimal control problems
- `topology-point-set.md` - Function spaces, Banach spaces

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
