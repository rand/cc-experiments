---
name: lambda-calculus
description: Lambda calculus including untyped, simply typed, Church encodings, and reduction strategies
---

# Lambda Calculus

**Scope**: Untyped λ-calculus, simply typed λ-calculus, Church encodings, β-reduction, combinators
**Lines**: ~420
**Last Updated**: 2025-10-25

## When to Use This Skill

Activate this skill when:
- Understanding foundations of functional programming
- Studying computation theory and Church-Turing thesis
- Implementing interpreters for functional languages
- Working with higher-order functions and closures
- Formalizing programming language semantics
- Exploring type theory foundations

## Core Concepts

### Syntax and Terms

**λ-terms**:
- Variables: x, y, z, ...
- Abstraction: λx. M (function with parameter x, body M)
- Application: M N (apply M to N)

```python
from dataclasses import dataclass
from typing import Union

# Abstract syntax tree for λ-terms
@dataclass
class Var:
    name: str
    
    def __repr__(self):
        return self.name

@dataclass
class Abs:
    """Abstraction: λx. body"""
    param: str
    body: 'Term'
    
    def __repr__(self):
        return f"(λ{self.param}. {self.body})"

@dataclass
class App:
    """Application: func arg"""
    func: 'Term'
    arg: 'Term'
    
    def __repr__(self):
        return f"({self.func} {self.arg})"

Term = Union[Var, Abs, App]

# Example terms
identity = Abs('x', Var('x'))  # λx. x
const = Abs('x', Abs('y', Var('x')))  # λx. λy. x
apply_twice = Abs('f', Abs('x', App(Var('f'), App(Var('f'), Var('x')))))  # λf. λx. f (f x)

print(f"Identity: {identity}")
print(f"Const: {const}")
print(f"Apply twice: {apply_twice}")
```

### Free and Bound Variables

**Free variables**: FV(M) = variables not bound by λ
**Bound variables**: Variables under a λ-abstraction

```python
def free_vars(term: Term) -> set:
    """Compute set of free variables"""
    match term:
        case Var(name):
            return {name}
        case Abs(param, body):
            return free_vars(body) - {param}
        case App(func, arg):
            return free_vars(func) | free_vars(arg)

# Examples
print(f"FV(λx. x) = {free_vars(identity)}")  # ∅
print(f"FV(λx. y) = {free_vars(Abs('x', Var('y')))}")  # {y}
print(f"FV((λx. x) y) = {free_vars(App(identity, Var('y')))}")  # {y}
```

### Substitution and α-conversion

**Substitution**: M[x := N] replaces free occurrences of x in M with N
**α-conversion**: Rename bound variables (λx. M) →_α (λy. M[x := y])

```python
def substitute(term: Term, var: str, replacement: Term) -> Term:
    """
    term[var := replacement]
    Capture-avoiding substitution
    """
    match term:
        case Var(name):
            return replacement if name == var else term
        
        case Abs(param, body):
            if param == var:
                # Variable shadowed, don't substitute
                return term
            elif param in free_vars(replacement):
                # Capture would occur, need α-conversion
                fresh = fresh_var(param, free_vars(term) | free_vars(replacement))
                renamed_body = substitute(body, param, Var(fresh))
                return Abs(fresh, substitute(renamed_body, var, replacement))
            else:
                return Abs(param, substitute(body, var, replacement))
        
        case App(func, arg):
            return App(substitute(func, var, replacement), substitute(arg, var, replacement))

_counter = 0
def fresh_var(base: str, avoid: set) -> str:
    """Generate fresh variable name"""
    global _counter
    while True:
        name = f"{base}{_counter}" if _counter > 0 else base
        _counter += 1
        if name not in avoid:
            return name

# Example: (λx. λy. x)[x := y] with capture avoidance
term = Abs('x', Abs('y', Var('x')))
result = substitute(term, 'x', Var('y'))
print(f"{term}[x := y] = {result}")
```

### β-reduction

**β-reduction**: (λx. M) N →_β M[x := N]

**Reduction strategies**:
- Normal order: leftmost-outermost redex first
- Applicative order: leftmost-innermost redex first (call-by-value)
- Call-by-name: like normal order but no reduction under λ

```python
def is_redex(term: Term) -> bool:
    """Check if term is a β-redex: (λx. M) N"""
    match term:
        case App(Abs(_, _), _):
            return True
        case _:
            return False

def beta_reduce_once(term: Term) -> Term:
    """Perform one β-reduction step (normal order)"""
    match term:
        case App(Abs(param, body), arg):
            # β-redex: reduce it
            return substitute(body, param, arg)
        
        case App(func, arg):
            # Try reducing function first
            if not isinstance(func, Var):
                return App(beta_reduce_once(func), arg)
            else:
                # Then try reducing argument
                return App(func, beta_reduce_once(arg))
        
        case Abs(param, body):
            # Reduce under abstraction (normal order does this)
            return Abs(param, beta_reduce_once(body))
        
        case _:
            return term

def normalize(term: Term, max_steps: int = 100) -> Term:
    """Reduce to normal form (if exists)"""
    for _ in range(max_steps):
        try:
            new_term = beta_reduce_once(term)
            if new_term == term:
                break
            term = new_term
        except:
            break
    return term

# Example: (λx. x) (λy. y) →_β λy. y
term = App(identity, identity)
result = normalize(term)
print(f"{term} →* {result}")

# Example: (λf. λx. f (f x)) (λy. y) z →_β z
term = App(App(apply_twice, identity), Var('z'))
result = normalize(term)
print(f"{term} →* {result}")
```

### Church Encodings

**Church numerals**: Encode natural numbers as functions

```python
def church_numeral(n: int) -> Term:
    """
    n̅ = λf. λx. f^n x
    0 = λf. λx. x
    1 = λf. λx. f x
    2 = λf. λx. f (f x)
    """
    body = Var('x')
    for _ in range(n):
        body = App(Var('f'), body)
    return Abs('f', Abs('x', body))

# Successor: succ = λn. λf. λx. f (n f x)
succ = Abs('n', Abs('f', Abs('x', 
    App(Var('f'), App(App(Var('n'), Var('f')), Var('x')))
)))

# Addition: add = λm. λn. λf. λx. m f (n f x)
add = Abs('m', Abs('n', Abs('f', Abs('x',
    App(App(Var('m'), Var('f')), App(App(Var('n'), Var('f')), Var('x')))
))))

# Multiplication: mul = λm. λn. λf. m (n f)
mul = Abs('m', Abs('n', Abs('f', 
    App(Var('m'), App(Var('n'), Var('f')))
)))

# Example: 2 + 3
two = church_numeral(2)
three = church_numeral(3)
five = normalize(App(App(add, two), three))
print(f"2̅ + 3̅ = {five}")
```

**Church booleans**:

```python
# true = λt. λf. t
# false = λt. λf. f
true = Abs('t', Abs('f', Var('t')))
false = Abs('t', Abs('f', Var('f')))

# if = λb. λt. λf. b t f (identity in λ-calculus!)
if_then_else = Abs('b', Abs('t', Abs('f', App(App(Var('b'), Var('t')), Var('f')))))

# and = λp. λq. p q p
and_op = Abs('p', Abs('q', App(App(Var('p'), Var('q')), Var('p'))))

# or = λp. λq. p p q
or_op = Abs('p', Abs('q', App(App(Var('p'), Var('p')), Var('q'))))

# not = λp. λa. λb. p b a
not_op = Abs('p', Abs('a', Abs('b', App(App(Var('p'), Var('b')), Var('a')))))

# Example: not true →_β false
result = normalize(App(not_op, true))
print(f"not true →* {result}")
```

### Combinators

**S, K, I combinators** (SKI combinator calculus):

```python
# I = λx. x (identity)
I = Abs('x', Var('x'))

# K = λx. λy. x (constant)
K = Abs('x', Abs('y', Var('x')))

# S = λx. λy. λz. x z (y z)
S = Abs('x', Abs('y', Abs('z', 
    App(App(Var('x'), Var('z')), App(Var('y'), Var('z')))
)))

# Theorem: SKK = I
SKK = App(App(S, K), K)
result = normalize(SKK)
print(f"S K K →* {result}")  # Should reduce to identity

# Y combinator (fixed-point): Y = λf. (λx. f (x x)) (λx. f (x x))
Y = Abs('f', 
    App(
        Abs('x', App(Var('f'), App(Var('x'), Var('x')))),
        Abs('x', App(Var('f'), App(Var('x'), Var('x'))))
    )
)

# Property: Y f →_β f (Y f)
# Used for recursion in λ-calculus
```

### Simply Typed λ-calculus

**Types**: τ ::= α | τ → τ

```python
from dataclasses import dataclass
from typing import Union as TUnion

@dataclass
class TVar:
    """Type variable"""
    name: str
    
    def __repr__(self):
        return self.name

@dataclass
class TArrow:
    """Function type: τ₁ → τ₂"""
    input: 'Type'
    output: 'Type'
    
    def __repr__(self):
        return f"({self.input} → {self.output})"

Type = TUnion[TVar, TArrow]

# Typing context: Γ = {x₁: τ₁, ..., xₙ: τₙ}
Context = dict[str, Type]

def type_check(term: Term, context: Context) -> Type:
    """
    Type checking for simply typed λ-calculus
    Γ ⊢ M : τ
    """
    match term:
        case Var(name):
            if name not in context:
                raise TypeError(f"Unbound variable: {name}")
            return context[name]
        
        case Abs(param, body):
            # Need type annotation in practice
            # For now, assume param has type α
            param_type = TVar('α')
            new_context = context | {param: param_type}
            body_type = type_check(body, new_context)
            return TArrow(param_type, body_type)
        
        case App(func, arg):
            func_type = type_check(func, context)
            arg_type = type_check(arg, context)
            
            match func_type:
                case TArrow(input_type, output_type):
                    if input_type != arg_type:
                        raise TypeError(f"Type mismatch: expected {input_type}, got {arg_type}")
                    return output_type
                case _:
                    raise TypeError(f"Expected function type, got {func_type}")

# Example: type check identity function
try:
    id_type = type_check(identity, {})
    print(f"Type of λx. x: {id_type}")  # α → α
except TypeError as e:
    print(f"Type error: {e}")
```

---

## Patterns

### Pattern 1: Recursion via Fixed Points

```python
# Factorial using Y combinator
# fact = Y (λf. λn. if (n = 0) 1 (n * f (n-1)))

# In practice, use recursive definitions with Y:
def factorial_lambda():
    """
    Factorial: F = λf. λn. if (n = 0) 1 (n · f (pred n))
    fact = Y F
    """
    # Simplified representation
    return "Y (λf. λn. if (isZero n) 1 (mul n (f (pred n))))"
```

### Pattern 2: Encoding Data Structures

```python
# Pairs: pair = λx. λy. λf. f x y
pair = Abs('x', Abs('y', Abs('f', App(App(Var('f'), Var('x')), Var('y')))))

# fst = λp. p (λx. λy. x)
fst = Abs('p', App(Var('p'), K))

# snd = λp. p (λx. λy. y)
snd = Abs('p', App(Var('p'), Abs('x', Abs('y', Var('y')))))

# Lists (Church encoding):
# nil = λc. λn. n
# cons = λh. λt. λc. λn. c h (t c n)
nil = Abs('c', Abs('n', Var('n')))
cons = Abs('h', Abs('t', Abs('c', Abs('n', 
    App(App(Var('c'), Var('h')), App(App(Var('t'), Var('c')), Var('n')))
))))
```

---

## Quick Reference

### Reduction Rules

```
β-reduction: (λx. M) N →_β M[x := N]
α-conversion: λx. M →_α λy. M[x := y] (y fresh)
η-conversion: λx. M x →_η M (if x ∉ FV(M))
```

### Church Encodings

| Concept | Encoding |
|---------|----------|
| 0 | λf. λx. x |
| succ | λn. λf. λx. f (n f x) |
| true | λt. λf. t |
| false | λt. λf. f |
| pair | λx. λy. λf. f x y |
| nil | λc. λn. n |

### Combinators

```
I = λx. x
K = λx. λy. x
S = λx. λy. λz. x z (y z)
Y = λf. (λx. f (x x)) (λx. f (x x))
```

---

## Anti-Patterns

❌ **Forgetting capture avoidance**: (λx. λy. x)[x := y] ≠ λy. y (capture!)
✅ Use α-conversion: (λx. λy₀. x)[x := y] = λy₀. y

❌ **Assuming all terms terminate**: Ω = (λx. x x) (λx. x x) loops forever
✅ Simply typed λ-calculus has strong normalization

❌ **Confusing β-equivalence with syntactic equality**: (λx. x) ≠ (λy. y) syntactically but =_β
✅ Use α-conversion or compare normal forms

---

## Related Skills

- `type-systems.md` - Type checking, inference, polymorphism
- `dependent-types.md` - Dependent function types, Π-types
- `curry-howard.md` - Propositions as types correspondence
- `operational-semantics.md` - Formal semantics for λ-calculus
- `formal/lean-proof-basics.md` - Formalizing λ-calculus in Lean

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
