---
name: type-systems
description: Type systems including type checking, inference, polymorphism, subtyping, and soundness
---

# Type Systems

**Scope**: Type checking, type inference, polymorphism, subtyping, soundness, gradual typing
**Lines**: ~450
**Last Updated**: 2025-10-25

## When to Use This Skill

Activate this skill when:
- Designing type systems for programming languages
- Implementing type checkers and type inference algorithms
- Understanding parametric polymorphism and generics
- Working with subtyping and object-oriented type systems
- Proving type soundness (progress + preservation)
- Exploring gradual typing and type migration

## Core Concepts

### Type Judgments

**Typing judgment**: Γ ⊢ e : τ (in context Γ, expression e has type τ)

```python
from dataclasses import dataclass
from typing import Union, Optional
from enum import Enum

# Types
@dataclass
class TInt:
    def __repr__(self):
        return "Int"

@dataclass
class TBool:
    def __repr__(self):
        return "Bool"

@dataclass
class TFun:
    """Function type: τ₁ → τ₂"""
    param: 'Type'
    result: 'Type'
    
    def __repr__(self):
        return f"({self.param} → {self.result})"

@dataclass
class TVar:
    """Type variable for polymorphism"""
    name: str
    
    def __repr__(self):
        return self.name

Type = Union[TInt, TBool, TFun, TVar]

# Terms
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
class Abs:
    """λx:τ. e (annotated abstraction)"""
    param: str
    param_type: Type
    body: 'Expr'

@dataclass
class App:
    func: 'Expr'
    arg: 'Expr'

@dataclass
class If:
    cond: 'Expr'
    then_branch: 'Expr'
    else_branch: 'Expr'

Expr = Union[IntLit, BoolLit, Var, Abs, App, If]

# Type environment
Context = dict[str, Type]

def type_check(expr: Expr, ctx: Context) -> Type:
    """
    Type checking algorithm
    Returns type if well-typed, raises TypeError otherwise
    """
    match expr:
        case IntLit(_):
            return TInt()
        
        case BoolLit(_):
            return TBool()
        
        case Var(name):
            if name not in ctx:
                raise TypeError(f"Unbound variable: {name}")
            return ctx[name]
        
        case Abs(param, param_type, body):
            # Γ, x:τ₁ ⊢ e:τ₂  ⟹  Γ ⊢ λx:τ₁. e : τ₁ → τ₂
            new_ctx = ctx | {param: param_type}
            body_type = type_check(body, new_ctx)
            return TFun(param_type, body_type)
        
        case App(func, arg):
            # Γ ⊢ e₁ : τ₁ → τ₂    Γ ⊢ e₂ : τ₁  ⟹  Γ ⊢ e₁ e₂ : τ₂
            func_type = type_check(func, ctx)
            arg_type = type_check(arg, ctx)
            
            match func_type:
                case TFun(param_type, result_type):
                    if not types_equal(param_type, arg_type):
                        raise TypeError(f"Type mismatch: expected {param_type}, got {arg_type}")
                    return result_type
                case _:
                    raise TypeError(f"Expected function type, got {func_type}")
        
        case If(cond, then_branch, else_branch):
            # Γ ⊢ e₁ : Bool    Γ ⊢ e₂ : τ    Γ ⊢ e₃ : τ  ⟹  Γ ⊢ if e₁ then e₂ else e₃ : τ
            cond_type = type_check(cond, ctx)
            if not isinstance(cond_type, TBool):
                raise TypeError(f"Condition must be Bool, got {cond_type}")
            
            then_type = type_check(then_branch, ctx)
            else_type = type_check(else_branch, ctx)
            
            if not types_equal(then_type, else_type):
                raise TypeError(f"Branches have different types: {then_type} vs {else_type}")
            
            return then_type

def types_equal(t1: Type, t2: Type) -> bool:
    """Check type equality"""
    match (t1, t2):
        case (TInt(), TInt()) | (TBool(), TBool()):
            return True
        case (TFun(p1, r1), TFun(p2, r2)):
            return types_equal(p1, p2) and types_equal(r1, r2)
        case (TVar(n1), TVar(n2)):
            return n1 == n2
        case _:
            return False

# Example: type check λx:Int. x + 1
identity_int = Abs('x', TInt(), Var('x'))
id_type = type_check(identity_int, {})
print(f"Type of λx:Int. x: {id_type}")  # Int → Int
```

### Type Inference (Algorithm W)

**Hindley-Milner type inference**: Infer types without annotations

```python
from typing import Dict, Set

@dataclass
class TyVar:
    """Type variable for inference"""
    id: int
    
    def __repr__(self):
        return f"'t{self.id}"

InferType = Union[TInt, TBool, TFun, TyVar]

class TypeInference:
    def __init__(self):
        self.next_tyvar = 0
        self.substitution: Dict[int, InferType] = {}
    
    def fresh_tyvar(self) -> TyVar:
        """Generate fresh type variable"""
        tv = TyVar(self.next_tyvar)
        self.next_tyvar += 1
        return tv
    
    def apply_subst(self, ty: InferType) -> InferType:
        """Apply substitution to type"""
        match ty:
            case TyVar(id) if id in self.substitution:
                return self.apply_subst(self.substitution[id])
            case TFun(param, result):
                return TFun(self.apply_subst(param), self.apply_subst(result))
            case _:
                return ty
    
    def unify(self, t1: InferType, t2: InferType):
        """
        Unification: find substitution making t1 = t2
        Robinson's algorithm
        """
        t1 = self.apply_subst(t1)
        t2 = self.apply_subst(t2)
        
        match (t1, t2):
            case (TInt(), TInt()) | (TBool(), TBool()):
                return
            
            case (TFun(p1, r1), TFun(p2, r2)):
                self.unify(p1, p2)
                self.unify(r1, r2)
            
            case (TyVar(id1), TyVar(id2)) if id1 == id2:
                return
            
            case (TyVar(id), _):
                if self.occurs_check(id, t2):
                    raise TypeError(f"Infinite type: 't{id} = {t2}")
                self.substitution[id] = t2
            
            case (_, TyVar(id)):
                if self.occurs_check(id, t1):
                    raise TypeError(f"Infinite type: 't{id} = {t1}")
                self.substitution[id] = t1
            
            case _:
                raise TypeError(f"Cannot unify {t1} and {t2}")
    
    def occurs_check(self, id: int, ty: InferType) -> bool:
        """Check if type variable occurs in type"""
        ty = self.apply_subst(ty)
        match ty:
            case TyVar(id2):
                return id == id2
            case TFun(param, result):
                return self.occurs_check(id, param) or self.occurs_check(id, result)
            case _:
                return False
    
    def infer(self, expr: Expr, ctx: Dict[str, InferType]) -> InferType:
        """
        Type inference (Algorithm W)
        Returns inferred type
        """
        match expr:
            case IntLit(_):
                return TInt()
            
            case BoolLit(_):
                return TBool()
            
            case Var(name):
                if name not in ctx:
                    raise TypeError(f"Unbound variable: {name}")
                return ctx[name]
            
            case Abs(param, None, body):  # Unannotated abstraction
                param_ty = self.fresh_tyvar()
                new_ctx = ctx | {param: param_ty}
                body_ty = self.infer(body, new_ctx)
                return TFun(param_ty, body_ty)
            
            case App(func, arg):
                func_ty = self.infer(func, ctx)
                arg_ty = self.infer(arg, ctx)
                result_ty = self.fresh_tyvar()
                self.unify(func_ty, TFun(arg_ty, result_ty))
                return self.apply_subst(result_ty)
            
            case If(cond, then_branch, else_branch):
                cond_ty = self.infer(cond, ctx)
                self.unify(cond_ty, TBool())
                then_ty = self.infer(then_branch, ctx)
                else_ty = self.infer(else_branch, ctx)
                self.unify(then_ty, else_ty)
                return self.apply_subst(then_ty)

# Example: infer type of λx. x
@dataclass
class UntypedAbs:
    param: str
    body: Expr

unannotated_id = UntypedAbs('x', Var('x'))
inferencer = TypeInference()
inferred_type = inferencer.infer(unannotated_id, {})
inferred_type = inferencer.apply_subst(inferred_type)
print(f"Inferred type of λx. x: {inferred_type}")  # 't0 → 't0 (polymorphic!)
```

### Parametric Polymorphism

**System F (polymorphic λ-calculus)**:
- Type abstraction: Λα. e
- Type application: e [τ]

```python
@dataclass
class ForAll:
    """Polymorphic type: ∀α. τ"""
    tyvar: str
    body: Type
    
    def __repr__(self):
        return f"∀{self.tyvar}. {self.body}"

@dataclass
class TyAbs:
    """Type abstraction: Λα. e"""
    tyvar: str
    body: Expr

@dataclass
class TyApp:
    """Type application: e [τ]"""
    expr: Expr
    tyarg: Type

# Polymorphic identity: Λα. λx:α. x
poly_id = TyAbs('α', Abs('x', TVar('α'), Var('x')))
# Type: ∀α. α → α

# Instantiation: (Λα. λx:α. x) [Int]
# Result type: Int → Int
```

### Subtyping

**Subtype relation**: τ₁ <: τ₂ (τ₁ is a subtype of τ₂)

**Rules**:
- Reflexivity: τ <: τ
- Transitivity: τ₁ <: τ₂, τ₂ <: τ₃ ⟹ τ₁ <: τ₃
- Functions (contravariant in argument): τ₁' <: τ₁, τ₂ <: τ₂' ⟹ (τ₁ → τ₂) <: (τ₁' → τ₂')

```python
def is_subtype(t1: Type, t2: Type) -> bool:
    """Check if t1 <: t2"""
    # Reflexivity
    if types_equal(t1, t2):
        return True
    
    match (t1, t2):
        # Function subtyping (contravariant in argument, covariant in result)
        case (TFun(p1, r1), TFun(p2, r2)):
            return is_subtype(p2, p1) and is_subtype(r1, r2)  # Note: p2 <: p1!
        
        # Additional rules for records, objects, etc.
        case _:
            return False

# Example: (Int → Bool) <: (Int → Bool)? Yes (reflexive)
# (Int → Int) <: (Int → Bool)? No
# (Bool → Int) <: (Int → Int)? No (Int ⊀: Bool)
```

### Type Soundness

**Progress**: Well-typed terms are not stuck
**Preservation**: If Γ ⊢ e : τ and e →* e', then Γ ⊢ e' : τ

```python
def progress(expr: Expr, ty: Type) -> bool:
    """
    Progress theorem: well-typed closed term is either value or can step
    
    Proof sketch:
    - Base cases (literals): values, done
    - Abs: value, done
    - App: by IH, func is value or steps
      - If value, must be Abs, so can β-reduce
      - If steps, can step App
    - If: cond is value or steps, etc.
    """
    # Values: literals and abstractions
    if isinstance(expr, (IntLit, BoolLit, Abs)):
        return True  # Is value
    
    # Otherwise can step (simplified check)
    return can_step(expr)

def can_step(expr: Expr) -> bool:
    """Check if expression can take a step"""
    match expr:
        case App(Abs(_, _, _), _):
            return True  # β-reduction
        case App(func, arg):
            return can_step(func) or can_step(arg)
        case If(BoolLit(_), _, _):
            return True  # Can select branch
        case If(cond, _, _):
            return can_step(cond)
        case _:
            return False

def preservation(expr: Expr, ty: Type, ctx: Context) -> bool:
    """
    Preservation theorem: if Γ ⊢ e : τ and e → e', then Γ ⊢ e' : τ
    
    Proof by induction on typing derivation
    """
    # Verify type is preserved after stepping
    if can_step(expr):
        expr_stepped = step(expr)  # Would need evaluation function
        try:
            ty_stepped = type_check(expr_stepped, ctx)
            return types_equal(ty, ty_stepped)
        except TypeError:
            return False
    return True

def step(expr: Expr) -> Expr:
    """Single evaluation step (simplified)"""
    match expr:
        case App(Abs(param, _, body), arg):
            # β-reduction (substitute arg for param in body)
            return substitute(body, param, arg)
        case _:
            return expr

def substitute(expr: Expr, var: str, replacement: Expr) -> Expr:
    """Substitute variable in expression"""
    match expr:
        case Var(name):
            return replacement if name == var else expr
        case Abs(param, ty, body):
            if param == var:
                return expr  # Shadowed
            return Abs(param, ty, substitute(body, var, replacement))
        case App(func, arg):
            return App(substitute(func, var, replacement), substitute(arg, var, replacement))
        case _:
            return expr
```

---

## Patterns

### Pattern 1: Generics in Languages

**ML-style polymorphism**:
```ocaml
(* OCaml *)
let id x = x;;          (* 'a -> 'a *)
let const x y = x;;     (* 'a -> 'b -> 'a *)
```

**Java generics**:
```java
<T> T identity(T x) { return x; }
<T extends Comparable<T>> T max(T a, T b) { ... }
```

### Pattern 2: Algebraic Data Types

```python
# Representing sum types
@dataclass
class Option:
    """Option<T> = None | Some(T)"""
    pass

@dataclass
class None_(Option):
    pass

@dataclass
class Some(Option):
    value: Type

# Type checking pattern matching
def match_option(opt: Option, none_case: Expr, some_case: Expr) -> Type:
    """Type check: match opt { None => ..., Some(x) => ... }"""
    pass
```

### Pattern 3: Gradual Typing

**Dynamic type**: ⋆ (unknown type)

```python
@dataclass
class TDynamic:
    """Dynamic type ⋆"""
    def __repr__(self):
        return "⋆"

def consistent(t1: Type, t2: Type) -> bool:
    """
    Consistency relation: t1 ~ t2
    More permissive than equality, allows ⋆
    """
    match (t1, t2):
        case (TDynamic(), _) | (_, TDynamic()):
            return True  # ⋆ consistent with everything
        case (TFun(p1, r1), TFun(p2, r2)):
            return consistent(p1, p2) and consistent(r1, r2)
        case _:
            return types_equal(t1, t2)
```

---

## Quick Reference

### Typing Rules (Simply Typed λ-Calculus)

```
Γ(x) = τ
────────── (Var)
Γ ⊢ x : τ

Γ, x:τ₁ ⊢ e:τ₂
────────────────────── (Abs)
Γ ⊢ λx:τ₁. e : τ₁ → τ₂

Γ ⊢ e₁ : τ₁ → τ₂    Γ ⊢ e₂ : τ₁
─────────────────────────────── (App)
Γ ⊢ e₁ e₂ : τ₂
```

### Type Inference (Hindley-Milner)

```
Algorithm W (unification-based):
1. Generate fresh type variables
2. Collect constraints
3. Unify constraints
4. Apply substitution
```

### Subtyping Rules

```
τ <: τ                             (Refl)

τ₁ <: τ₂    τ₂ <: τ₃
─────────────────── (Trans)
τ₁ <: τ₃

τ₁' <: τ₁    τ₂ <: τ₂'
──────────────────────────── (Arrow)
τ₁ → τ₂ <: τ₁' → τ₂'
```

---

## Anti-Patterns

❌ **Confusing type checking and type inference**: Checking needs annotations, inference doesn't
✅ Bidirectional typing combines both

❌ **Ignoring variance**: List<Dog> is not subtype of List<Animal> (invariant)
✅ Array types are invariant, function arguments contravariant

❌ **Assuming soundness**: Unsafe features (casts, null) break type soundness
✅ Gradual typing makes unsoundness explicit with ⋆ type

❌ **Over-constraining inference**: Requiring full annotations defeats purpose
✅ Use bidirectional typing: infer when possible, check when needed

---

## Related Skills

- `lambda-calculus.md` - Foundation for typed λ-calculi
- `dependent-types.md` - Types depending on values
- `curry-howard.md` - Proofs as programs, types as propositions
- `operational-semantics.md` - Evaluation and reduction
- `program-verification.md` - Proving program properties via types

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
