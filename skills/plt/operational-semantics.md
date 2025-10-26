---
name: operational-semantics
description: Operational semantics including small-step, big-step, evaluation strategies, and reduction systems
---

# Operational Semantics

**Scope**: Small-step semantics, big-step semantics, evaluation strategies, reduction systems, contextual semantics
**Lines**: ~420
**Last Updated**: 2025-10-25

## When to Use This Skill

Activate this skill when:
- Defining formal semantics for programming languages
- Proving properties of evaluation (determinism, confluence)
- Understanding call-by-value vs call-by-name evaluation
- Implementing interpreters with formal foundations
- Reasoning about program equivalence
- Designing abstract machines

## Core Concepts

### Small-Step Semantics

**Transition relation**: e → e' (expression e steps to e')

```python
from dataclasses import dataclass
from typing import Union, Optional

# Language syntax
@dataclass
class IntLit:
    value: int

@dataclass
class BoolLit:
    value: bool

@dataclass
class Var:
    name: str

@dataclass
class Add:
    left: 'Expr'
    right: 'Expr'

@dataclass
class If:
    cond: 'Expr'
    then_branch: 'Expr'
    else_branch: 'Expr'

@dataclass
class Abs:
    """λx. e"""
    param: str
    body: 'Expr'

@dataclass
class App:
    func: 'Expr'
    arg: 'Expr'

Expr = Union[IntLit, BoolLit, Var, Add, If, Abs, App]

def is_value(expr: Expr) -> bool:
    """Check if expression is a value (cannot step further)"""
    return isinstance(expr, (IntLit, BoolLit, Abs))

def substitute(expr: Expr, var: str, replacement: Expr) -> Expr:
    """Capture-avoiding substitution: expr[var := replacement]"""
    match expr:
        case Var(name):
            return replacement if name == var else expr
        case Add(l, r):
            return Add(substitute(l, var, replacement), substitute(r, var, replacement))
        case If(c, t, e):
            return If(substitute(c, var, replacement), 
                     substitute(t, var, replacement),
                     substitute(e, var, replacement))
        case Abs(param, body):
            if param == var:
                return expr  # Variable shadowed
            return Abs(param, substitute(body, var, replacement))
        case App(f, a):
            return App(substitute(f, var, replacement), substitute(a, var, replacement))
        case _:
            return expr

def small_step(expr: Expr) -> Optional[Expr]:
    """
    Small-step reduction: e → e'
    Returns None if no step possible (stuck or value)
    """
    match expr:
        # Values don't step
        case _ if is_value(expr):
            return None
        
        # Arithmetic
        case Add(IntLit(m), IntLit(n)):
            return IntLit(m + n)
        case Add(e1, e2) if not is_value(e1):
            e1_stepped = small_step(e1)
            return Add(e1_stepped, e2) if e1_stepped else None
        case Add(e1, e2) if is_value(e1) and not is_value(e2):
            e2_stepped = small_step(e2)
            return Add(e1, e2_stepped) if e2_stepped else None
        
        # Conditionals
        case If(BoolLit(True), then_branch, _):
            return then_branch
        case If(BoolLit(False), _, else_branch):
            return else_branch
        case If(cond, t, e) if not is_value(cond):
            cond_stepped = small_step(cond)
            return If(cond_stepped, t, e) if cond_stepped else None
        
        # Application (call-by-value)
        case App(Abs(param, body), arg) if is_value(arg):
            # β-reduction
            return substitute(body, param, arg)
        case App(func, arg) if not is_value(func):
            # Evaluate function first
            func_stepped = small_step(func)
            return App(func_stepped, arg) if func_stepped else None
        case App(func, arg) if is_value(func) and not is_value(arg):
            # Then evaluate argument
            arg_stepped = small_step(arg)
            return App(func, arg_stepped) if arg_stepped else None
        
        case _:
            return None  # Stuck

def evaluate(expr: Expr, max_steps: int = 1000) -> Expr:
    """
    Multi-step evaluation: e →* v
    Reduce to normal form
    """
    for _ in range(max_steps):
        stepped = small_step(expr)
        if stepped is None:
            break
        expr = stepped
    return expr

# Example: (λx. x + 1) 5 →* 6
term = App(Abs('x', Add(Var('x'), IntLit(1))), IntLit(5))
print(f"Initial: {term}")

step1 = small_step(term)
print(f"Step 1: {step1}")  # x + 1 [x := 5] = 5 + 1

step2 = small_step(step1) if step1 else None
print(f"Step 2: {step2}")  # 6

result = evaluate(term)
print(f"Result: {result}")  # IntLit(6)
```

### Big-Step Semantics

**Evaluation relation**: e ⇓ v (expression e evaluates to value v)

```python
def big_step(expr: Expr, env: dict = None) -> Expr:
    """
    Big-step evaluation: e ⇓ v
    Directly evaluate to value (no intermediate steps)
    """
    env = env or {}
    
    match expr:
        # Values evaluate to themselves
        case _ if is_value(expr):
            return expr
        
        # Variables
        case Var(name):
            if name not in env:
                raise NameError(f"Unbound variable: {name}")
            return env[name]
        
        # Arithmetic
        case Add(e1, e2):
            v1 = big_step(e1, env)
            v2 = big_step(e2, env)
            if isinstance(v1, IntLit) and isinstance(v2, IntLit):
                return IntLit(v1.value + v2.value)
            raise TypeError("Addition requires integers")
        
        # Conditionals
        case If(cond, then_branch, else_branch):
            cond_val = big_step(cond, env)
            if isinstance(cond_val, BoolLit):
                if cond_val.value:
                    return big_step(then_branch, env)
                else:
                    return big_step(else_branch, env)
            raise TypeError("Condition must be boolean")
        
        # Application
        case App(func, arg):
            func_val = big_step(func, env)
            if isinstance(func_val, Abs):
                arg_val = big_step(arg, env)
                # Evaluate body with extended environment
                new_env = env | {func_val.param: arg_val}
                return big_step(func_val.body, new_env)
            raise TypeError("Application requires function")
        
        case _:
            raise ValueError(f"Cannot evaluate: {expr}")

# Example: if true then 1 + 2 else 3 + 4 ⇓ 3
term = If(BoolLit(True), Add(IntLit(1), IntLit(2)), Add(IntLit(3), IntLit(4)))
result = big_step(term)
print(f"{term} ⇓ {result}")  # IntLit(3)
```

### Evaluation Strategies

**Call-by-value (CBV)**: Evaluate arguments before function application

```python
def cbv_step(expr: Expr) -> Optional[Expr]:
    """Call-by-value reduction"""
    match expr:
        case App(Abs(param, body), arg) if is_value(arg):
            # Argument is value, reduce
            return substitute(body, param, arg)
        case App(func, arg) if not is_value(func):
            # Reduce function first
            func_stepped = cbv_step(func)
            return App(func_stepped, arg) if func_stepped else None
        case App(func, arg) if is_value(func):
            # Function is value, reduce argument
            arg_stepped = cbv_step(arg)
            return App(func, arg_stepped) if arg_stepped else None
        case _:
            return None

# Example: (λx. λy. x) ((λz. z) 1) 2
# CBV: Reduce (λz. z) 1 first, then apply
```

**Call-by-name (CBN)**: Substitute arguments without evaluating

```python
def cbn_step(expr: Expr) -> Optional[Expr]:
    """Call-by-name reduction"""
    match expr:
        case App(Abs(param, body), arg):
            # Substitute immediately, don't evaluate arg
            return substitute(body, param, arg)
        case App(func, arg):
            # Reduce function only
            func_stepped = cbn_step(func)
            return App(func_stepped, arg) if func_stepped else None
        case _:
            return None

# Example: (λx. 1) ((λy. y y) (λy. y y))
# CBN: Return 1 without evaluating Ω = (λy. y y) (λy. y y)
# CBV: Loop forever evaluating Ω
```

**Call-by-need (lazy evaluation)**: CBN with memoization

```python
class Thunk:
    """Delayed computation with memoization"""
    def __init__(self, expr: Expr, env: dict):
        self.expr = expr
        self.env = env
        self.value = None
    
    def force(self):
        """Evaluate thunk (memoized)"""
        if self.value is None:
            self.value = lazy_eval(self.expr, self.env)
        return self.value

def lazy_eval(expr: Expr, env: dict = None) -> Expr:
    """Call-by-need evaluation"""
    env = env or {}
    
    match expr:
        case Var(name):
            if name not in env:
                raise NameError(f"Unbound variable: {name}")
            # Force thunk if necessary
            val = env[name]
            return val.force() if isinstance(val, Thunk) else val
        
        case App(func, arg):
            func_val = lazy_eval(func, env)
            if isinstance(func_val, Abs):
                # Create thunk for argument
                thunk = Thunk(arg, env)
                new_env = env | {func_val.param: thunk}
                return lazy_eval(func_val.body, new_env)
        
        case _ if is_value(expr):
            return expr
        
        case _:
            raise ValueError(f"Cannot evaluate: {expr}")

# Lazy evaluation allows working with infinite data structures
```

### Contextual Semantics

**Evaluation contexts**: E ::= [] | E e | v E | ...

```python
@dataclass
class Hole:
    """Evaluation context hole []"""
    pass

@dataclass
class CtxApp1:
    """E e (context in function position)"""
    context: 'Context'
    arg: Expr

@dataclass
class CtxApp2:
    """v E (context in argument position, function is value)"""
    func: Expr
    context: 'Context'

Context = Union[Hole, CtxApp1, CtxApp2]

def plug(ctx: Context, expr: Expr) -> Expr:
    """Fill hole in context with expression: E[e]"""
    match ctx:
        case Hole():
            return expr
        case CtxApp1(inner_ctx, arg):
            return App(plug(inner_ctx, expr), arg)
        case CtxApp2(func, inner_ctx):
            return App(func, plug(inner_ctx, expr))

def decompose(expr: Expr) -> Optional[tuple[Context, Expr]]:
    """
    Decompose expression into context and redex: e = E[r]
    Returns (E, r) where r is redex
    """
    match expr:
        case App(Abs(param, body), arg) if is_value(arg):
            # Found redex
            return (Hole(), expr)
        case App(func, arg):
            if not is_value(func):
                # Decompose function
                ctx, redex = decompose(func)
                return (CtxApp1(ctx, arg), redex)
            elif not is_value(arg):
                # Decompose argument
                ctx, redex = decompose(arg)
                return (CtxApp2(func, ctx), redex)
        case _:
            return None

# Context-based stepping
def contextual_step(expr: Expr) -> Optional[Expr]:
    """e = E[r] → E[r'] where r → r'"""
    decomp = decompose(expr)
    if decomp is None:
        return None
    
    ctx, redex = decomp
    redex_stepped = small_step(redex)
    if redex_stepped is None:
        return None
    
    return plug(ctx, redex_stepped)
```

---

## Patterns

### Pattern 1: Determinism

```python
def is_deterministic(expr: Expr) -> bool:
    """
    Check if semantics is deterministic:
    If e → e₁ and e → e₂, then e₁ = e₂
    """
    # For our CBV semantics, this always holds
    # Prove by induction on step relation
    return True
```

### Pattern 2: Confluence

```python
def is_confluent(expr: Expr) -> bool:
    """
    Church-Rosser property:
    If e →* e₁ and e →* e₂, then ∃e₃: e₁ →* e₃ and e₂ →* e₃
    """
    # For pure λ-calculus, this holds
    # For CBV, determinism implies confluence
    return True
```

---

## Quick Reference

### Small-Step vs Big-Step

| Aspect | Small-Step | Big-Step |
|--------|-----------|----------|
| Notation | e → e' | e ⇓ v |
| Granularity | One step at a time | Direct to value |
| Non-termination | e → e' → ... (infinite) | No rule applies |
| Intermediate steps | Explicit | Hidden |

### Evaluation Strategies

| Strategy | Rule | Example |
|----------|------|---------|
| Call-by-value | (λx. e) v → e[x := v] | Strict languages (ML, Scheme) |
| Call-by-name | (λx. e) e' → e[x := e'] | Algol, early languages |
| Call-by-need | CBN + memoization | Haskell (lazy) |

---

## Anti-Patterns

❌ **Confusing small-step and big-step**: Different tools for different purposes
✅ Small-step for reasoning about steps, big-step for final results

❌ **Assuming all languages are deterministic**: Non-deterministic concurrency exists
✅ Explicitly model non-determinism when needed

❌ **Ignoring evaluation order**: CBV and CBN have different termination behavior
✅ Choose evaluation strategy based on language design goals

---

## Related Skills

- `lambda-calculus.md` - β-reduction and normalization
- `type-systems.md` - Type soundness (progress + preservation)
- `curry-howard.md` - Proof normalization as program evaluation
- `program-verification.md` - Proving properties of evaluation

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
