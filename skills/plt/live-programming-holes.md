---
name: live-programming-holes
description: Live programming with typed holes - Hazel environment, continuous feedback, live evaluation with indeterminate results, incremental bidirectional typing (OOPSLA 2025), collaborative editing (Grove)
---

# Live Programming with Typed Holes

**Scope**: Hazel environment, live evaluation, incremental typing (OOPSLA 2025), collaborative editing (Grove POPL 2025)
**Lines**: ~420
**Last Updated**: 2025-10-25

## When to Use This Skill

Activate this skill when:
- Building live programming environments
- Implementing continuous feedback systems
- Creating educational programming tools
- Designing exploratory programming interfaces
- Implementing real-time collaboration for code
- Understanding incremental type checking algorithms

## Core Concepts

### Live Programming Principles

**Live programming**: Immediate, continuous feedback while editing

```python
from dataclasses import dataclass
from typing import Union, Optional, List

class LiveEnvironment:
    """
    Live programming environment characteristics:

    1. Edit freely: All intermediate states valid
    2. See immediately: Continuous evaluation
    3. Inspect anywhere: Click to see types, values
    4. No compile step: No edit-compile-run cycle
    """

    def __init__(self):
        self.program = EmptyHole()  # Start with hole
        self.evaluation_result = None
        self.type_info = {}

    def on_edit(self, new_program: 'Expr'):
        """
        On every edit:
        1. Re-type check (incremental)
        2. Re-evaluate (if possible)
        3. Update display
        """
        # Incremental type checking
        self.type_info = self.incremental_typecheck(new_program)

        # Live evaluation
        try:
            self.evaluation_result = self.evaluate(new_program)
        except:
            self.evaluation_result = IndeterminateResult()

        # Update UI immediately
        self.update_display()

    def update_display(self):
        """
        Show:
        - Syntax highlighting
        - Type annotations (hover)
        - Evaluation result
        - Hole goals
        """
        pass

print("Live programming: edit → type → eval → display (continuously)")
```

### Hazel Architecture

**Hazel**: Web-based live functional programming environment

```python
@dataclass
class HazelState:
    """
    Hazel system state

    Core components:
    - Editor: Structure editor (Hazelnut)
    - Type checker: Bidirectional with holes
    - Evaluator: Small-step with indeterminate results
    - UI: React-based web interface
    """
    # Current program (ZExp with cursor)
    program: 'ZExp'

    # Type information
    type_map: dict  # Expression → Type

    # Evaluation state
    eval_state: 'EvalState'

    # UI state
    cursor_position: tuple
    selected_hole: Optional[str]

@dataclass
class EvalState:
    """
    Evaluation state for live environment

    Multiple evaluation modes:
    - Step-by-step: Single reduction steps
    - To value: Reduce to normal form
    - Lazy: Evaluate on demand
    """
    current_expr: 'Expr'
    step_count: int
    is_indeterminate: bool  # Contains holes

# Hazel workflow
def hazel_workflow():
    """
    User interaction in Hazel:

    1. Edit structure (keyboard/mouse)
       → Hazelnut edit actions

    2. Type check continuously
       → Bidirectional type synthesis

    3. Evaluate on demand
       → Click "evaluate" or automatic

    4. Inspect results
       → Hover for types
       → Click holes to see goals
       → Step through evaluation

    Always valid, always typeable, always inspectable!
    """
    pass

print("Hazel: Fully integrated live environment")
```

### Live Evaluation with Indeterminate Results

**Key insight**: Can evaluate programs with holes to indeterminate results

```python
@dataclass
class DeterminateValue:
    """Concrete value"""
    value: any

@dataclass
class IndeterminateValue:
    """Value containing holes - we don't know what it is yet"""
    hole_id: str
    expected_type: 'Type'
    context: dict

Result = Union[DeterminateValue, IndeterminateValue]

class LiveEvaluator:
    """Evaluate programs with holes"""

    def evaluate_live(self, expr: 'Expr') -> Result:
        """
        Evaluate with holes

        Examples:
        - 2 + 3 → 5 (determinate)
        - 2 + ?h → ⊥h (indeterminate)
        - if true then 5 else ?h → 5 (determinate! Hole not evaluated)
        - if ?h then 1 else 2 → ⊥h (indeterminate, need hole value)
        """
        match expr:
            case Hole(name, typ, ctx):
                # Hole evaluates to indeterminate
                return IndeterminateValue(name, typ, ctx)

            case Num(n):
                return DeterminateValue(n)

            case Plus(e1, e2):
                v1 = self.evaluate_live(e1)
                v2 = self.evaluate_live(e2)

                # If either indeterminate, result is indeterminate
                if isinstance(v1, IndeterminateValue):
                    return v1
                if isinstance(v2, IndeterminateValue):
                    return v2

                # Both determinate: compute
                return DeterminateValue(v1.value + v2.value)

            case If(cond, then_branch, else_branch):
                cond_val = self.evaluate_live(cond)

                if isinstance(cond_val, IndeterminateValue):
                    # Can't decide which branch
                    return cond_val

                # Determinate condition: choose branch
                if cond_val.value:
                    return self.evaluate_live(then_branch)
                else:
                    return self.evaluate_live(else_branch)

    def display_result(self, result: Result) -> str:
        """
        Display evaluation result to user

        Determinate: Show value
        Indeterminate: Show which hole blocked evaluation
        """
        match result:
            case DeterminateValue(v):
                return f"Result: {v}"
            case IndeterminateValue(hole_id, typ, _):
                return f"⊥{hole_id} : {typ} (indeterminate - depends on hole)"

print("Live evaluation: Results may be indeterminate but still meaningful")
```

### Incremental Bidirectional Typing (OOPSLA 2025)

**Incremental typing**: Re-type only what changed (Distinguished Paper!)

```python
class IncrementalTypeChecker:
    """
    Incremental bidirectional type checking

    Based on OOPSLA 2025 work:
    "Incremental Bidirectional Typing via Order Maintenance"

    Key idea: Borrow techniques from incremental browser layout
    """

    def __init__(self):
        self.type_cache = {}  # Expression → Type
        self.dependency_graph = {}  # What depends on what
        self.dirty_set = set()  # What needs re-checking

    def edit(self, old_expr: 'Expr', new_expr: 'Expr', path: List[int]):
        """
        Handle edit at path

        Instead of re-typing entire program:
        1. Mark changed node as dirty
        2. Propagate dirtiness up dependencies
        3. Re-type only dirty nodes
        """
        # Mark affected nodes
        self.mark_dirty(path)

        # Incremental re-typing
        return self.retype_dirty()

    def mark_dirty(self, path: List[int]):
        """
        Mark node and dependents as dirty

        If e changed at path p:
        - Mark e as dirty
        - Mark parent of e as dirty (dependent)
        - Propagate to all ancestors
        """
        for node in self.ancestors(path):
            self.dirty_set.add(node)

            # Mark anything that depends on this node
            for dependent in self.dependency_graph.get(node, []):
                self.dirty_set.add(dependent)

    def retype_dirty(self):
        """
        Re-type only dirty nodes

        Process in dependency order:
        1. Leaves first (no dependencies)
        2. Then parents (depend on leaves)
        3. Bottom-up to root
        """
        # Topological sort of dirty nodes
        ordered = self.topo_sort(self.dirty_set)

        for node in ordered:
            # Re-type this node
            new_type = self.typecheck_node(node)
            self.type_cache[node] = new_type

        self.dirty_set.clear()

    def typecheck_node(self, node: 'Expr') -> 'Type':
        """
        Type single node

        Can use cached types for clean children!
        Only re-type dirty subtrees
        """
        match node:
            case App(f, arg):
                # Lookup types (cached if clean, recomputed if dirty)
                f_type = self.get_type(f)
                arg_type = self.get_type(arg)

                # Type application
                if isinstance(f_type, TArrow):
                    check_consistent(arg_type, f_type.param)
                    return f_type.result
                else:
                    return THole()
            # ... other cases

    def get_type(self, expr: 'Expr') -> 'Type':
        """
        Get type: from cache if clean, recompute if dirty
        """
        if expr in self.dirty_set:
            return self.typecheck_node(expr)
        else:
            return self.type_cache.get(expr, THole())

print("Incremental typing: Only re-type what changed")
```

### Live Pattern Matching

**Live pattern editing**: See match coverage in real-time

```python
class LivePatternChecker:
    """
    Live pattern match analysis

    Shows:
    - Which patterns are redundant
    - Which cases are missing
    - Example values that reach each branch
    """

    def analyze_match(self, match_expr: Match) -> 'MatchAnalysis':
        """
        Analyze pattern match live

        Example:
          match x : Bool with
          | true → 1
          | _    → 2

        Analysis:
        - Pattern 1 (true): Covers {true}
        - Pattern 2 (_): Covers {false} (not redundant!)
        - Complete: Yes
        """
        scrutinee_type = self.get_type(match_expr.scrutinee)
        all_values = enumerate_values(scrutinee_type)

        coverage = []
        for i, (pattern, _) in enumerate(match_expr.branches):
            covered = match_values(pattern, all_values)
            coverage.append((i, covered))

            # Remove covered values
            all_values = all_values - covered

        return MatchAnalysis(
            coverage=coverage,
            uncovered=all_values,
            redundant=self.find_redundant(coverage)
        )

    def display_coverage(self, analysis: 'MatchAnalysis'):
        """
        Display coverage visually in IDE

        - Green: Pattern covers new cases
        - Yellow: Pattern is redundant
        - Red: Missing cases (uncovered)
        """
        pass

print("Live pattern analysis: See coverage and completeness instantly")
```

### Grove: Collaborative Editing (POPL 2025)

**Grove**: Commutative edit actions for real-time collaboration

```python
class GroveCollaboration:
    """
    Grove: Bidirectionally Typed Structure Editor Calculus (POPL 2025)

    Key innovation: Commutative edit actions

    Traditional conflict:
      User A: Edit at position 10
      User B: Insert at position 5
      → Position 10 is now 15! Conflict!

    Grove approach:
      Edits reference paths in tree, not positions
      Most edits naturally commute
    """

    def __init__(self):
        self.local_operations = []
        self.remote_operations = []
        self.program_state = EmptyHole()

    def apply_edit(self, edit: 'GroveEdit', source: str):
        """
        Apply edit (local or remote)

        Grove guarantees:
        1. Edits at different paths commute
        2. Edits at same path have defined merge
        3. Type safety preserved in all merges
        """
        if source == "local":
            self.local_operations.append(edit)
        else:
            self.remote_operations.append(edit)

        # Apply edit
        self.program_state = self.transform_and_apply(edit, self.program_state)

    def transform_and_apply(self, edit: 'GroveEdit', state: 'Expr') -> 'Expr':
        """
        Operational transformation for Grove

        If concurrent edits:
        - Transform edit to account for other edits
        - Apply transformed edit
        - Result: Convergent state (same for all users)
        """
        # Transform edit based on concurrent operations
        transformed = self.transform(edit, self.get_concurrent_edits(edit))

        # Apply transformed edit
        return self.apply(transformed, state)

    def transform(self, edit: 'GroveEdit', concurrent: List['GroveEdit']) -> 'GroveEdit':
        """
        Transform edit to commute with concurrent edits

        Example:
          Edit A: Insert at path [0, 1]
          Edit B: Insert at path [0]

        Transform B relative to A:
          B' still at [0] (independent paths)

        Transform A relative to B:
          A' now at [0, 1, 1] (B changed structure)
        """
        pass

print("Grove: Conflict-free collaborative structure editing")
```

### Performance Optimizations

**Making live programming fast** enough for interactive use

```python
class PerformanceOptimizations:
    """
    Optimizations for live programming

    Challenges:
    - Type check on every keystroke (can't be slow!)
    - Evaluate continuously (can't block UI)
    - Large programs (thousands of lines)
    """

    @staticmethod
    def incremental_everything():
        """
        1. Incremental parsing (structure editor: free!)
        2. Incremental type checking (OOPSLA 2025)
        3. Incremental evaluation (cache results)
        4. Incremental rendering (React reconciliation)
        """
        pass

    @staticmethod
    def lazy_evaluation():
        """
        Don't evaluate everything immediately

        - Evaluate visible parts
        - Evaluate on demand (click to expand)
        - Cache evaluation results
        - Invalidate cache on edit
        """
        pass

    @staticmethod
    def web_workers():
        """
        Use Web Workers for heavy computation

        Main thread: UI, editor
        Worker thread: Type checking, evaluation

        Communication:
        - Main → Worker: Edit operations
        - Worker → Main: Type info, results
        """
        pass

    @staticmethod
    def memoization():
        """
        Memoize expensive operations

        - Type synthesis
        - Constraint solving
        - Pattern match analysis
        - Evaluation results
        """
        pass

print("Performance: Incremental + lazy + parallel + memoized")
```

---

## Patterns

### Pattern 1: Example-Driven Development

```python
def example_driven_pattern():
    """
    Live programming enables example-driven workflow

    1. Write examples first
       factorial 0 = 1
       factorial 3 = 6

    2. See examples fail (holes)
       factorial n = ?impl

    3. Implement to make examples pass
       factorial 0 = 1
       factorial n = n * factorial (n - 1)

    4. Examples now pass live!

    Immediate feedback guides implementation
    """
    print("Examples first, then implement to match")
```

### Pattern 2: Visual Debugging

```python
def visual_debugging():
    """
    Live evaluation enables visual debugging

    - Click expression: See value
    - Step through evaluation: See each step
    - Inspect hole: See why indeterminate
    - Trace execution: See call graph

    No printf debugging needed!
    """
    pass
```

### Pattern 3: Exploratory Programming

```python
def exploratory_pattern():
    """
    Live environment for exploration

    1. Import library
    2. Create hole: ?explore
    3. See available functions (autocomplete)
    4. Try function: f ?arg
    5. See type error or result immediately
    6. Iterate rapidly

    Learning by experimentation
    """
    pass
```

---

## Quick Reference

### Hazel Environment

| Component | Technology | Purpose |
|-----------|------------|---------|
| Editor | ReasonML + React | Structure editor UI |
| Type checker | Bidirectional | Continuous typing |
| Evaluator | Small-step | Live evaluation |
| Backend | OCaml | Core semantics |

### Incremental Typing

```
Edit → Mark dirty → Propagate → Re-type only dirty → Cache

Performance: O(size of edit) not O(size of program)
```

### Grove Collaboration

```
Edit → Transform → Apply → Converge

Property: Commutative edits → No conflicts
```

### Evaluation Results

```
Determinate: Concrete value
Indeterminate: Contains holes (⊥h)
Error: Type error (⦇e⦈ type mismatch)
```

---

## Anti-Patterns

❌ **Re-typing entire program on edit**: Too slow
✅ Incremental type checking

❌ **Blocking UI during evaluation**: Unresponsive
✅ Use web workers, async evaluation

❌ **No feedback on indeterminate**: Confusing
✅ Show which hole blocked evaluation

❌ **Conflicting concurrent edits**: Data loss
✅ Use operational transformation (Grove)

---

## Related Skills

- `hazelnut-calculus.md` - Structure editor foundation
- `typed-holes-foundations.md` - Basic holes theory
- `typed-holes-interaction.md` - IDE features for holes
- `structure-editors.md` - Editor design patterns
- `operational-semantics.md` - Evaluation semantics

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
