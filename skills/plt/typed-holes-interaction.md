---
name: typed-holes-interaction
description: IDE integration with typed holes - goal-directed programming, hole refinement, case splitting, proof search, tactics, elaborator reflection (Agda, Idris, Lean models)
---

# Typed Holes: IDE Interaction

**Scope**: IDE integration, goal-directed development, hole commands, tactics, elaborator reflection, proof search
**Lines**: ~380
**Last Updated**: 2025-10-25

## When to Use This Skill

Activate this skill when:
- Implementing IDE features for typed holes
- Building interactive development environments
- Working with proof assistants (Agda, Idris, Lean)
- Designing goal-directed programming workflows
- Implementing auto-completion with type information
- Adding tactics and proof automation

## Core Concepts

### Hole as Interaction Point

**Key idea**: Holes are not just placeholders - they're interactive development tools

```python
from dataclasses import dataclass
from typing import List, Optional, Dict

@dataclass
class InteractiveHole:
    """Hole with IDE integration"""
    name: str
    expected_type: 'Type'
    context: Dict[str, 'Type']  # Variables in scope
    position: tuple  # (line, column) in source

    # IDE features
    def show_goal(self) -> str:
        """Display what this hole needs to produce"""
        return f"Goal: {self.expected_type}"

    def show_context(self) -> List[str]:
        """Display available variables"""
        return [f"{var} : {typ}" for var, typ in self.context.items()]

    def suggest_completions(self) -> List[str]:
        """Type-driven code suggestions"""
        suggestions = []

        # Suggest variables of compatible type
        for var, typ in self.context.items():
            if consistent(typ, self.expected_type):
                suggestions.append(var)

        # Suggest constructors for expected type
        if isinstance(self.expected_type, DataType):
            suggestions.extend(self.expected_type.constructors)

        return suggestions

# Example: Agda-style interaction
def agda_hole_interaction():
    """
    In Agda:

    f : ℕ → ℕ
    f x = {! !}

    C-c C-l (load): Shows hole with index
    f x = { }0

    C-c C-, (goal): Show goal and context
      Goal: ℕ
      ————————————————
      x : ℕ

    C-c C-r (refine): Try to refine hole
    C-c C-a (auto): Search for solution
    """
    pass

print("Holes are interaction points for development")
```

### Goal-Directed Programming Workflow

**Workflow**: Types guide development through holes

```python
class GoalDirectedDevelopment:
    """Goal-directed programming using holes"""

    @staticmethod
    def workflow_example():
        """
        Example: Implement map for lists

        Step 1: Write type signature
          map : (A → B) → List A → List B

        Step 2: Write skeleton with holes
          map f xs = ?goal

        Step 3: Inspect goal
          ?goal : List B
          Context: f : A → B, xs : List A

        Step 4: Case split on xs
          map f [] = ?nil-case
          map f (x :: xs') = ?cons-case

        Step 5: Fill each hole
          ?nil-case : List B
          Context: f : A → B
          → Solution: []

          ?cons-case : List B
          Context: f : A → B, x : A, xs' : List A
          → Solution: f x :: map f xs'

        Step 6: Complete!
          map f [] = []
          map f (x :: xs') = f x :: map f xs'
        """
        pass

    @staticmethod
    def type_driven_steps():
        """
        At each hole:
        1. Inspect goal type
        2. Check available variables
        3. Determine possible actions:
           - Use variable (if type matches)
           - Apply constructor
           - Case split on variable
           - Refine hole structure
        """
        pass

print("Goal-directed: types → holes → refinement → solution")
```

### Hole Commands (IDE Protocol)

**Language Server Protocol** extensions for holes

```python
@dataclass
class HoleCommand:
    """IDE command for hole manipulation"""
    command_type: str
    hole_id: str
    parameters: dict

# Common hole commands
class HoleCommands:
    """Standard IDE hole commands"""

    @staticmethod
    def show_goal(hole: InteractiveHole) -> str:
        """
        Display goal and context

        Output:
          Goal: String
          ————————————————
          x : Int
          y : Bool
        """
        goal = f"Goal: {hole.expected_type}"
        divider = "—" * 20
        context_lines = [f"{var} : {typ}" for var, typ in hole.context.items()]
        return f"{goal}\n{divider}\n" + "\n".join(context_lines)

    @staticmethod
    def refine(hole: InteractiveHole, constructor: str) -> 'Expr':
        """
        Refine hole with constructor

        Example:
          ?h : Bool
          refine True → True
          refine if → if ?cond then ?then else ?else
        """
        match constructor:
            case "if":
                return IfExpr(
                    Hole("cond", TBool(), hole.context),
                    Hole("then", hole.expected_type, hole.context),
                    Hole("else", hole.expected_type, hole.context)
                )
            case _:
                # Apply constructor, create holes for arguments
                return construct_with_holes(constructor, hole.expected_type)

    @staticmethod
    def case_split(hole: InteractiveHole, var: str) -> List[tuple['Pattern', InteractiveHole]]:
        """
        Case split on variable

        Example:
          ?h : Bool
          Context: x : Maybe Int

          case_split on x:
          →  case x of
               Nothing → ?nothing-case : Bool
               Just y  → ?just-case : Bool  (with y : Int)
        """
        var_type = hole.context[var]
        constructors = get_constructors(var_type)

        branches = []
        for ctor in constructors:
            # Create pattern
            pattern = make_pattern(ctor)
            # Create hole for this branch
            new_context = extend_context(hole.context, pattern)
            branch_hole = InteractiveHole(
                name=f"{hole.name}-{ctor.name}",
                expected_type=hole.expected_type,
                context=new_context,
                position=hole.position
            )
            branches.append((pattern, branch_hole))

        return branches

    @staticmethod
    def auto_solve(hole: InteractiveHole, max_depth: int = 3) -> Optional['Expr']:
        """
        Automated proof search / term synthesis

        Try to fill hole automatically using:
        - Variables in context
        - Constructor combinations
        - Recursive calls (if applicable)

        Uses bounded search (max_depth)
        """
        return proof_search(hole.expected_type, hole.context, max_depth)

print("IDE commands: show goal, refine, case split, auto-solve")
```

### Proof Search and Auto-Filling

**Automated hole filling** via search

```python
class ProofSearch:
    """Automatic term synthesis for holes"""

    def __init__(self, max_depth: int = 3):
        self.max_depth = max_depth
        self.cache = {}  # Memoization

    def search(self, goal: 'Type', context: dict, depth: int = 0) -> Optional['Expr']:
        """
        Search for term of given type

        Strategy:
        1. Check context variables (depth 0)
        2. Try constructors (depth 1)
        3. Try function application (depth 2+)
        4. Recursive search on sub-goals
        """
        if depth > self.max_depth:
            return None

        # Check cache
        cache_key = (goal, tuple(context.items()), depth)
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Try context variables
        for var, var_type in context.items():
            if var_type == goal:
                return Var(var)

        # Try constructors
        if isinstance(goal, DataType):
            for ctor in goal.constructors:
                term = self.try_constructor(ctor, goal, context, depth)
                if term:
                    self.cache[cache_key] = term
                    return term

        # Try function application
        for var, var_type in context.items():
            if isinstance(var_type, TArrow) and var_type.result == goal:
                # Try to construct argument
                arg = self.search(var_type.param, context, depth + 1)
                if arg:
                    term = App(Var(var), arg)
                    self.cache[cache_key] = term
                    return term

        return None

    def try_constructor(self, ctor: 'Constructor', goal: 'Type', context: dict, depth: int):
        """
        Try to apply constructor

        For constructor: C : T₁ → ... → Tₙ → G
        Search for terms of types T₁, ..., Tₙ
        """
        arg_types = ctor.argument_types()
        args = []

        for arg_type in arg_types:
            arg = self.search(arg_type, context, depth + 1)
            if arg is None:
                return None  # Can't find this argument
            args.append(arg)

        # Success! Build constructor application
        return ConstructorApp(ctor, args)

# Example: Auto-solving in Agda
def agda_auto_example():
    """
    In Agda:

    sym : {A : Set} {x y : A} → x ≡ y → y ≡ x
    sym p = {! !}

    C-c C-a (auto):
    → Tries: refl? No, wrong type.
    → Tries: case split on p
    → Tries: pattern match p = refl
    → Success: sym refl = refl
    """
    pass

print("Proof search: automated hole filling within depth bound")
```

### Tactics and Elaborator Reflection

**Tactics**: Meta-programs that construct terms

```python
# Idris/Lean style tactics
@dataclass
class Tactic:
    """Tactic: function from goal to term (or new goals)"""
    name: str
    implementation: 'Callable'

class TacticEngine:
    """Execute tactics to fill holes"""

    def __init__(self):
        self.tactics = {}

    def register_tactic(self, name: str, impl):
        """Register new tactic"""
        self.tactics[name] = Tactic(name, impl)

    def apply_tactic(self, tactic_name: str, hole: InteractiveHole) -> 'TacticResult':
        """
        Apply tactic to hole

        Returns:
        - Success(expr): Hole filled with expr
        - NewGoals([hole1, ...]): Hole refined into sub-holes
        - Failure(msg): Tactic failed
        """
        tactic = self.tactics[tactic_name]
        return tactic.implementation(hole)

# Built-in tactics
def tactic_intro(hole: InteractiveHole) -> 'TacticResult':
    """
    intro: Introduce lambda or forall

    Goal: A → B
    intro → λx. ?goal' where ?goal' : B (x : A)
    """
    if isinstance(hole.expected_type, TArrow):
        param_name = fresh_var()
        new_context = hole.context | {param_name: hole.expected_type.param}
        new_hole = InteractiveHole(
            name=f"{hole.name}-body",
            expected_type=hole.expected_type.result,
            context=new_context,
            position=hole.position
        )
        return NewGoals([new_hole])
    else:
        return Failure("intro requires arrow type")

def tactic_exact(hole: InteractiveHole, term: 'Expr') -> 'TacticResult':
    """
    exact: Provide exact term

    Check term has correct type, fill hole
    """
    if typecheck(term, hole.context) == hole.expected_type:
        return Success(term)
    else:
        return Failure(f"Term has wrong type")

def tactic_apply(hole: InteractiveHole, func: str) -> 'TacticResult':
    """
    apply: Apply function from context

    Goal: G
    Context: f : A → B → G

    apply f → New goals: ?arg1 : A, ?arg2 : B
    """
    func_type = hole.context.get(func)
    if not func_type:
        return Failure(f"Unknown function: {func}")

    # Extract argument types
    args, result = decompose_arrow(func_type)

    if result != hole.expected_type:
        return Failure(f"Result type mismatch")

    # Create holes for arguments
    new_holes = [
        InteractiveHole(f"{hole.name}-arg{i}", arg_type, hole.context, hole.position)
        for i, arg_type in enumerate(args)
    ]

    return NewGoals(new_holes)

# Elaborator reflection (Lean/Idris)
def elaborator_reflection_example():
    """
    In Lean 4:

    theorem my_theorem : P → Q := by
      intro p        -- Tactic: introduce hypothesis
      apply h p      -- Tactic: apply function h
      exact e        -- Tactic: provide exact term e

    Elaborator reflection: Tactics are functions in meta-level language
    Access to:
    - Goal state (holes)
    - Context
    - Type information
    - Can construct terms programmatically
    """
    pass

print("Tactics: meta-programs that construct proof terms")
```

### Hole Refinement Strategies

**Interactive refinement**: Transform holes step-by-step

```python
class HoleRefinement:
    """Strategies for refining holes"""

    @staticmethod
    def by_cases(hole: InteractiveHole, var: str):
        """
        Refine by case analysis

        Before:
          ?h : Bool
          Context: x : Maybe Int

        After (case split on x):
          case x of
            Nothing → ?h-nothing : Bool
            Just y  → ?h-just : Bool  (y : Int in context)
        """
        pass

    @staticmethod
    def by_induction(hole: InteractiveHole, var: str):
        """
        Refine by induction on variable

        Before:
          ?h : List Int → Int
          Context: xs : List Int

        After (induction on xs):
          ?h [] = ?base : Int
          ?h (x :: xs') = ?step : Int
            where IH : List Int → Int (inductive hypothesis)
        """
        pass

    @staticmethod
    def by_computation(hole: InteractiveHole):
        """
        Refine by normalizing expected type

        Goal: 2 + 2
        Normalize → Goal: 4
        Suggest: 4
        """
        normalized = normalize(hole.expected_type)
        return InteractiveHole(
            hole.name,
            normalized,
            hole.context,
            hole.position
        )

    @staticmethod
    def by_unification(hole: InteractiveHole, template: 'Expr'):
        """
        Refine using template with fresh holes

        Template: f ?x ?y
        Goal: Int

        Unify: f ?x ?y : Int
        → ?x : ?, ?y : ?  (infer types)
        """
        pass

print("Refinement strategies: cases, induction, computation, unification")
```

---

## Patterns

### Pattern 1: Incremental Development

```python
def incremental_development_workflow():
    """
    1. Write top-level type
    2. Create hole for implementation
    3. Inspect hole goal
    4. Refine hole (case split, construct, etc.)
    5. Repeat for new holes
    6. Eventually: all holes filled!

    Advantage: Always have well-typed intermediate states
    """
    print("Incremental: type → hole → refine → repeat")
```

### Pattern 2: Type-Driven Test Generation

```python
def test_generation_from_holes(hole: InteractiveHole):
    """
    Use hole type to generate tests

    Hole: ?h : Int → Int

    Generate tests:
    - ?h 0 = ?result0 : Int
    - ?h 1 = ?result1 : Int
    - ?h (-1) = ?result-1 : Int

    Fill results interactively, then synthesize implementation
    """
    test_inputs = generate_test_inputs(hole.expected_type.param)

    tests = []
    for input_val in test_inputs:
        result_hole = InteractiveHole(
            f"result-{input_val}",
            hole.expected_type.result,
            {},
            hole.position
        )
        tests.append((input_val, result_hole))

    return tests

print("Test generation: use types to create test cases")
```

### Pattern 3: Collaborative Proof Development

```python
def collaborative_proof_with_holes():
    """
    Multiple developers working on proof

    Developer A: Writes theorem statement, creates hole
    Developer B: Refines hole into cases
    Developer C: Fills first case
    Developer D: Fills second case

    Holes enable decomposition of proof work
    """
    print("Collaboration: holes split proof into independent pieces")
```

---

## Quick Reference

### IDE Commands

| Command | Shortcut (Agda) | Purpose |
|---------|-----------------|---------|
| show goal | C-c C-, | Display goal and context |
| refine | C-c C-r | Refine hole with constructor |
| case split | C-c C-c | Split on variable |
| auto | C-c C-a | Automated search |
| give | C-c C-SPC | Fill hole with term |

### Common Tactics

| Tactic | Purpose | Example |
|--------|---------|---------|
| intro | Introduce binder | λx. ?goal |
| exact | Provide exact term | exact: x |
| apply | Apply function | apply: f → new goals |
| cases | Case analysis | cases x → branches |
| induction | Inductive proof | induction xs → base + step |
| refl | Reflexivity | prove: x = x |

### Refinement Strategies

```
By cases: Split on sum/bool type
By induction: Split on inductive type
By computation: Normalize and simplify
By unification: Match pattern template
```

---

## Anti-Patterns

❌ **Ignoring hole context**: Can't provide good suggestions
✅ Show available variables and their types

❌ **Unbounded proof search**: Hangs IDE
✅ Use depth limit, timeout, resource limits

❌ **Poor error messages**: "Tactic failed"
✅ Explain why tactic failed, suggest alternatives

❌ **No undo**: Can't backtrack from bad refinement
✅ Support undo/redo for hole operations

---

## Related Skills

- `typed-holes-foundations.md` - Basic holes concepts
- `hazelnut-calculus.md` - Edit actions for holes
- `typed-holes-semantics.md` - Advanced type theory
- `dependent-types.md` - Holes in Lean/Agda/Idris
- `program-verification.md` - Tactics for proofs
- `typed-holes-llm.md` - AI-assisted hole filling

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
