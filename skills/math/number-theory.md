---
name: number-theory
description: Number theory including primes, modular arithmetic, Diophantine equations, and cryptographic applications
---

# Number Theory

**Scope**: Primes, divisibility, modular arithmetic, Diophantine equations, quadratic residues, cryptography
**Lines**: ~400
**Last Updated**: 2025-10-25

## When to Use This Skill

Activate this skill when:
- Working with prime numbers and factorization
- Implementing modular arithmetic for cryptography
- Solving Diophantine equations
- Understanding RSA, Diffie-Hellman, elliptic curve crypto
- Analyzing divisibility and congruences
- Computing number-theoretic functions (φ, τ, σ)

## Core Concepts

### Divisibility and Primes

**Division algorithm**: For a, b ∈ ℤ with b > 0, ∃! q, r: a = bq + r with 0 ≤ r < b

**GCD and LCM**:

```python
import math
from typing import Tuple

def gcd(a: int, b: int) -> int:
    """Euclidean algorithm for GCD"""
    while b:
        a, b = b, a % b
    return abs(a)

def extended_gcd(a: int, b: int) -> Tuple[int, int, int]:
    """
    Extended Euclidean algorithm
    Returns (gcd, x, y) where gcd = ax + by
    """
    if b == 0:
        return abs(a), 1 if a >= 0 else -1, 0
    
    gcd_val, x1, y1 = extended_gcd(b, a % b)
    x = y1
    y = x1 - (a // b) * y1
    
    return gcd_val, x, y

def lcm(a: int, b: int) -> int:
    """LCM via gcd: lcm(a,b) = |ab|/gcd(a,b)"""
    return abs(a * b) // gcd(a, b)

# Example
a, b = 48, 18
g = gcd(a, b)
print(f"gcd({a}, {b}) = {g}")  # 6

g, x, y = extended_gcd(a, b)
print(f"{g} = {a}·{x} + {b}·{y}")  # 6 = 48·(-1) + 18·3
print(f"Verify: {a*x + b*y}")  # 6
```

**Prime testing**:

```python
def is_prime(n: int) -> bool:
    """Trial division primality test"""
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    
    # Check odd divisors up to √n
    for i in range(3, int(n**0.5) + 1, 2):
        if n % i == 0:
            return False
    return True

def miller_rabin(n: int, k: int = 5) -> bool:
    """
    Miller-Rabin primality test (probabilistic)
    k: number of rounds (higher = more accurate)
    Error probability: 4^(-k)
    """
    if n < 2:
        return False
    if n == 2 or n == 3:
        return True
    if n % 2 == 0:
        return False
    
    # Write n-1 = 2^r · d
    r, d = 0, n - 1
    while d % 2 == 0:
        r += 1
        d //= 2
    
    # Miller-Rabin test
    import random
    for _ in range(k):
        a = random.randint(2, n - 2)
        x = pow(a, d, n)  # a^d mod n
        
        if x == 1 or x == n - 1:
            continue
        
        for _ in range(r - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False  # Composite
    
    return True  # Probably prime

# Example
print(f"Is 97 prime? {is_prime(97)}")  # True
print(f"Is 1009 prime (Miller-Rabin)? {miller_rabin(1009)}")  # True
```

**Sieve of Eratosthenes**:

```python
def sieve_of_eratosthenes(limit: int) -> list[int]:
    """Generate all primes up to limit"""
    if limit < 2:
        return []
    
    is_prime = [True] * (limit + 1)
    is_prime[0] = is_prime[1] = False
    
    for i in range(2, int(limit**0.5) + 1):
        if is_prime[i]:
            # Mark multiples as composite
            for j in range(i*i, limit + 1, i):
                is_prime[j] = False
    
    return [i for i in range(limit + 1) if is_prime[i]]

# Example
primes = sieve_of_eratosthenes(100)
print(f"Primes up to 100: {primes[:10]}...")  # [2, 3, 5, 7, 11, 13, ...]
```

### Modular Arithmetic

**Congruences**: a ≡ b (mod n) iff n | (a - b)

**Modular inverse**:

```python
def mod_inverse(a: int, n: int) -> int:
    """
    Compute a^(-1) mod n (multiplicative inverse)
    Exists iff gcd(a, n) = 1
    """
    gcd_val, x, _ = extended_gcd(a, n)
    
    if gcd_val != 1:
        raise ValueError(f"No inverse: gcd({a}, {n}) = {gcd_val} ≠ 1")
    
    return x % n

def chinese_remainder_theorem(moduli: list[int], remainders: list[int]) -> int:
    """
    Solve system: x ≡ a_i (mod n_i)
    Requires moduli pairwise coprime
    """
    if len(moduli) != len(remainders):
        raise ValueError("Moduli and remainders must have same length")
    
    # Check coprimality
    for i in range(len(moduli)):
        for j in range(i + 1, len(moduli)):
            if gcd(moduli[i], moduli[j]) != 1:
                raise ValueError(f"Moduli not coprime: gcd({moduli[i]}, {moduli[j]}) ≠ 1")
    
    # Compute solution
    N = 1
    for n in moduli:
        N *= n
    
    x = 0
    for n_i, a_i in zip(moduli, remainders):
        N_i = N // n_i
        M_i = mod_inverse(N_i, n_i)
        x += a_i * N_i * M_i
    
    return x % N

# Example
moduli = [3, 5, 7]
remainders = [2, 3, 2]
solution = chinese_remainder_theorem(moduli, remainders)
print(f"Solution to CRT system: x ≡ {solution} (mod {3*5*7})")  # x = 23

# Verify
for n, a in zip(moduli, remainders):
    print(f"{solution} ≡ {solution % n} (mod {n}), expected {a}")
```

**Euler's totient function**:

```python
def euler_phi(n: int) -> int:
    """
    φ(n) = |{k : 1 ≤ k ≤ n, gcd(k,n) = 1}|
    Number of integers coprime to n
    """
    result = n
    p = 2
    
    # Factor n and apply φ(p^k) = p^(k-1)(p-1)
    while p * p <= n:
        if n % p == 0:
            # Remove factor p
            while n % p == 0:
                n //= p
            # Multiply by (1 - 1/p)
            result -= result // p
        p += 1
    
    if n > 1:
        # n is prime
        result -= result // n
    
    return result

# Examples
print(f"φ(9) = {euler_phi(9)}")  # 6 (1,2,4,5,7,8 coprime to 9)
print(f"φ(12) = {euler_phi(12)}")  # 4 (1,5,7,11)

# Euler's theorem: a^φ(n) ≡ 1 (mod n) if gcd(a,n)=1
n = 10
a = 3
assert pow(a, euler_phi(n), n) == 1
print(f"{a}^φ({n}) ≡ {pow(a, euler_phi(n), n)} (mod {n})")
```

### Quadratic Residues

**Legendre symbol**: (a/p) = 1 if a is quadratic residue mod p, -1 otherwise

```python
def legendre_symbol(a: int, p: int) -> int:
    """
    Compute (a/p) using Euler's criterion:
    (a/p) ≡ a^((p-1)/2) (mod p)
    """
    if not is_prime(p) or p == 2:
        raise ValueError("p must be odd prime")
    
    a = a % p
    if a == 0:
        return 0
    
    result = pow(a, (p - 1) // 2, p)
    return -1 if result == p - 1 else result

def tonelli_shanks(n: int, p: int) -> int:
    """
    Find r such that r² ≡ n (mod p)
    Tonelli-Shanks algorithm for modular square root
    """
    if legendre_symbol(n, p) != 1:
        raise ValueError(f"{n} is not a quadratic residue mod {p}")
    
    # Factor p-1 = Q · 2^S
    Q, S = p - 1, 0
    while Q % 2 == 0:
        Q //= 2
        S += 1
    
    # Find quadratic non-residue
    z = 2
    while legendre_symbol(z, p) != -1:
        z += 1
    
    # Initialize
    M = S
    c = pow(z, Q, p)
    t = pow(n, Q, p)
    R = pow(n, (Q + 1) // 2, p)
    
    while True:
        if t == 0:
            return 0
        if t == 1:
            return R
        
        # Find least i: t^(2^i) = 1
        i = 1
        temp = (t * t) % p
        while temp != 1:
            temp = (temp * temp) % p
            i += 1
        
        # Update
        b = pow(c, 1 << (M - i - 1), p)
        M = i
        c = (b * b) % p
        t = (t * c) % p
        R = (R * b) % p

# Example: Solve x² ≡ 10 (mod 13)
p = 13
n = 10
print(f"Legendre({n}/{p}) = {legendre_symbol(n, p)}")  # 1 (is quadratic residue)
sqrt_mod = tonelli_shanks(n, p)
print(f"√{n} ≡ {sqrt_mod} (mod {p})")  # 6
print(f"Verify: {sqrt_mod}² ≡ {(sqrt_mod**2) % p} (mod {p})")  # 10
```

### Diophantine Equations

**Linear Diophantine**: ax + by = c

```python
def linear_diophantine(a: int, b: int, c: int) -> Tuple[int, int]:
    """
    Solve ax + by = c
    Solution exists iff gcd(a, b) | c
    Returns one particular solution (x0, y0)
    General solution: x = x0 + (b/d)t, y = y0 - (a/d)t
    """
    g = gcd(a, b)
    
    if c % g != 0:
        raise ValueError(f"No solution: gcd({a},{b})={g} does not divide {c}")
    
    # Solve ax' + by' = g
    _, x0, y0 = extended_gcd(a, b)
    
    # Scale to ax + by = c
    x = x0 * (c // g)
    y = y0 * (c // g)
    
    return x, y

# Example: 12x + 18y = 6
x, y = linear_diophantine(12, 18, 6)
print(f"Solution to 12x + 18y = 6: x={x}, y={y}")
print(f"Verify: 12·{x} + 18·{y} = {12*x + 18*y}")
```

**Pell's equation**: x² - Dy² = 1

```python
def solve_pell(D: int, limit: int = 100) -> Tuple[int, int]:
    """
    Find smallest solution to x² - Dy² = 1
    Using continued fraction of √D
    """
    if int(D**0.5)**2 == D:
        raise ValueError("D must not be a perfect square")
    
    # Continued fraction expansion of √D
    m, d, a0 = 0, 1, int(D**0.5)
    
    # Convergents
    p_prev, p = 0, 1
    q_prev, q = 1, 0
    
    a = a0
    for _ in range(limit):
        p, p_prev = a * p + p_prev, p
        q, q_prev = a * q + q_prev, q
        
        # Check if (p, q) is solution
        if p*p - D*q*q == 1:
            return p, q
        
        # Next continued fraction term
        m = d * a - m
        d = (D - m*m) // d
        a = (a0 + m) // d
    
    raise ValueError("No solution found within limit")

# Example: x² - 2y² = 1
x, y = solve_pell(2)
print(f"Smallest solution to x² - 2y² = 1: ({x}, {y})")  # (3, 2)
print(f"Verify: {x}² - 2·{y}² = {x*x - 2*y*y}")  # 1
```

### Cryptographic Applications

**RSA encryption**:

```python
def generate_rsa_keys(p: int, q: int, e: int = 65537):
    """
    Generate RSA key pair
    p, q: distinct primes
    e: public exponent (commonly 65537)
    """
    if not (is_prime(p) and is_prime(q)):
        raise ValueError("p and q must be prime")
    
    n = p * q
    phi_n = (p - 1) * (q - 1)
    
    if gcd(e, phi_n) != 1:
        raise ValueError(f"e={e} not coprime to φ(n)={phi_n}")
    
    d = mod_inverse(e, phi_n)
    
    return {
        'public_key': (n, e),
        'private_key': (n, d),
        'p': p,
        'q': q,
        'phi_n': phi_n
    }

def rsa_encrypt(message: int, public_key: Tuple[int, int]) -> int:
    """Encrypt: c = m^e mod n"""
    n, e = public_key
    return pow(message, e, n)

def rsa_decrypt(ciphertext: int, private_key: Tuple[int, int]) -> int:
    """Decrypt: m = c^d mod n"""
    n, d = private_key
    return pow(ciphertext, d, n)

# Example
p, q = 61, 53
keys = generate_rsa_keys(p, q)
print(f"Public key: (n={keys['public_key'][0]}, e={keys['public_key'][1]})")
print(f"Private key: (n={keys['private_key'][0]}, d={keys['private_key'][1]})")

message = 123
ciphertext = rsa_encrypt(message, keys['public_key'])
decrypted = rsa_decrypt(ciphertext, keys['private_key'])

print(f"Original message: {message}")
print(f"Encrypted: {ciphertext}")
print(f"Decrypted: {decrypted}")
assert message == decrypted
```

---

## Patterns

### Pattern 1: Prime Factorization

```python
def prime_factorization(n: int) -> dict:
    """Return prime factorization as {prime: exponent}"""
    factors = {}
    d = 2
    
    while d * d <= n:
        while n % d == 0:
            factors[d] = factors.get(d, 0) + 1
            n //= d
        d += 1
    
    if n > 1:
        factors[n] = factors.get(n, 0) + 1
    
    return factors

# Example
n = 360
factors = prime_factorization(n)
print(f"{n} = {' · '.join(f'{p}^{e}' if e > 1 else str(p) for p, e in factors.items())}")
# 360 = 2^3 · 3^2 · 5
```

### Pattern 2: Fermat's Little Theorem

**Theorem**: If p is prime and gcd(a, p) = 1, then a^(p-1) ≡ 1 (mod p)

```python
def fermat_primality_test(n: int, k: int = 5) -> bool:
    """
    Probabilistic primality test using Fermat's Little Theorem
    k: number of rounds
    """
    if n < 2:
        return False
    if n == 2 or n == 3:
        return True
    
    import random
    for _ in range(k):
        a = random.randint(2, n - 2)
        if pow(a, n - 1, n) != 1:
            return False  # Definitely composite
    
    return True  # Probably prime (may fail for Carmichael numbers)
```

---

## Quick Reference

### Number-Theoretic Functions

| Function | Definition | Example |
|----------|-----------|---------|
| φ(n) | Euler's totient | φ(12) = 4 |
| τ(n) | Number of divisors | τ(12) = 6 |
| σ(n) | Sum of divisors | σ(12) = 28 |
| ω(n) | Number of distinct prime factors | ω(12) = 2 |
| Ω(n) | Number of prime factors (with multiplicity) | Ω(12) = 4 |

### Important Theorems

```
Fermat's Little Theorem: p prime, gcd(a,p)=1 ⟹ a^(p-1) ≡ 1 (mod p)
Euler's Theorem: gcd(a,n)=1 ⟹ a^φ(n) ≡ 1 (mod n)
Wilson's Theorem: p prime ⟺ (p-1)! ≡ -1 (mod p)
Chinese Remainder Theorem: System of congruences has unique solution mod N
```

---

## Anti-Patterns

❌ **Using trial division for large primes**: O(√n) too slow
✅ Use Miller-Rabin or other probabilistic tests

❌ **Assuming Fermat test is conclusive**: Carmichael numbers pass but aren't prime
✅ Use Miller-Rabin which handles Carmichael numbers

❌ **Computing a^b mod n naively**: Overflow for large numbers
✅ Use built-in `pow(a, b, n)` with modular exponentiation

❌ **Forgetting coprimality requirement**: CRT needs pairwise coprime moduli
✅ Verify gcd(n_i, n_j) = 1 before applying CRT

---

## Related Skills

- `abstract-algebra.md` - Rings ℤ/nℤ, fields, Galois theory
- `set-theory.md` - Cardinality of ℕ, ℤ, ℚ
- `formal/z3-solver-basics.md` - Solving number-theoretic constraints
- `cryptography.md` - RSA, Diffie-Hellman, elliptic curves (if exists)

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
