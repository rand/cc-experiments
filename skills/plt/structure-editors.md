---
name: structure-editors
description: Structure editor design patterns - projectional editing, syntax-directed editing, edit actions, cursor management, rendering, text workflow integration
---

# Structure Editors: Design Patterns

**Scope**: Projectional editing, edit actions, zipper cursors, rendering, text integration, educational tools
**Lines**: ~400
**Last Updated**: 2025-10-25

## When to Use This Skill

Activate this skill when:
- Designing structure editors (projectional editors)
- Building syntax-directed development tools
- Creating educational programming environments
- Implementing domain-specific language editors
- Understanding alternatives to text-based editing
- Integrating structure editing with traditional workflows

## Core Concepts

### Projectional Editing vs Text Editing

**Key difference**: Edit AST directly vs edit text and parse

```python
from dataclasses import dataclass
from typing import Union, List, Optional

# Text editor approach
class TextEditor:
    """
    Traditional text editing:

    1. User types characters
    2. Editor stores as string
    3. Parser parses on demand (or continuously)
    4. Show syntax errors

    Problems:
    - Intermediate states invalid ("if tr")
    - Parser errors cryptic
    - Lost productivity (syntax errors block progress)
    """
    text: str
    cursor_position: int

    def insert_char(self, ch: str):
        """Insert character at cursor"""
        self.text = (self.text[:self.cursor_position] +
                    ch +
                    self.text[self.cursor_position:])
        self.cursor_position += 1

    def parse(self) -> Optional['AST']:
        """Try to parse - may fail!"""
        try:
            return parse(self.text)
        except SyntaxError:
            return None  # Invalid!

# Structure editor approach
class StructureEditor:
    """
    Projectional editing:

    1. User performs edit actions
    2. Editor stores as AST
    3. Project AST to display
    4. Always valid!

    Benefits:
    - Always syntactically correct
    - Can't introduce syntax errors
    - Type-directed editing (know what's valid)
    """
    ast: 'Expr'
    cursor: 'ZContext'  # Zipper

    def construct_if(self):
        """
        Construct if-expression

        Before: ⦇⦈ (hole)
        After:  if ⦇⦈ then ⦇⦈ else ⦇⦈

        Always valid AST!
        """
        self.ast = IfExpr(
            EmptyHole(),
            EmptyHole(),
            EmptyHole()
        )

    def project(self) -> str:
        """Project AST to text for display"""
        return pretty_print(self.ast)

print("Structure editing: AST → Display (always valid)")
```

### Edit Actions and Edit Contexts

**Edit actions**: Operations on AST that preserve well-formedness

```python
from enum import Enum

class EditAction(Enum):
    # Movement
    MOVE_PARENT = "parent"
    MOVE_CHILD_1 = "child1"
    MOVE_CHILD_2 = "child2"

    # Construction
    CONSTRUCT_NUM = "num"
    CONSTRUCT_VAR = "var"
    CONSTRUCT_LAM = "lam"
    CONSTRUCT_AP = "ap"
    CONSTRUCT_IF = "if"
    CONSTRUCT_PLUS = "plus"

    # Deletion
    DELETE = "del"

    # Refinement
    FINISH = "finish"  # Remove hole wrapper

class EditContext:
    """
    Context for edit actions

    Determines which actions are valid at cursor
    """

    @staticmethod
    def available_actions(cursor_expr: 'Expr', expected_type: 'Type') -> List[EditAction]:
        """
        Which actions are valid at current position?

        Depends on:
        - What's under cursor
        - Expected type
        - Surrounding context
        """
        actions = []

        # Always can move (if not at root)
        actions.append(EditAction.MOVE_PARENT)

        # If empty hole: can construct anything
        if isinstance(cursor_expr, EmptyHole):
            actions.extend([
                EditAction.CONSTRUCT_NUM,
                EditAction.CONSTRUCT_VAR,
                EditAction.CONSTRUCT_LAM,
                EditAction.CONSTRUCT_IF,
            ])

        # If has children: can move down
        if isinstance(cursor_expr, (Lam, Ap, If, Plus)):
            actions.append(EditAction.MOVE_CHILD_1)
            if isinstance(cursor_expr, (Ap, If, Plus)):
                actions.append(EditAction.MOVE_CHILD_2)

        # Can always delete (replace with hole)
        actions.append(EditAction.DELETE)

        return actions

print("Edit actions: Only valid operations available")
```

### Cursor Management with Zippers

**Zipper**: Navigate AST efficiently

```python
@dataclass
class Zipper:
    """
    Zipper: Focus on one node, remember path back

    Components:
    - Focus: Current subtree under cursor
    - Context: Path back to root (one-hole contexts)
    """
    focus: 'Expr'
    context: 'Context'

    def go_up(self) -> Optional['Zipper']:
        """Move cursor to parent"""
        match self.context:
            case Top():
                return None  # Already at root
            case Parent(parent_type, siblings, parent_context):
                # Plug hole in parent
                new_focus = reconstruct(parent_type, self.focus, siblings)
                return Zipper(new_focus, parent_context)

    def go_down(self, child_index: int) -> Optional['Zipper']:
        """Move cursor to nth child"""
        match self.focus:
            case Lam(param, body):
                if child_index == 0:
                    new_context = LamContext(param, self.context)
                    return Zipper(body, new_context)
            case Ap(func, arg):
                if child_index == 0:
                    return Zipper(func, ApFuncContext(arg, self.context))
                elif child_index == 1:
                    return Zipper(arg, ApArgContext(func, self.context))
            # ... other cases

        return None  # Invalid child index

    def replace(self, new_focus: 'Expr') -> 'Zipper':
        """Replace focused node"""
        return Zipper(new_focus, self.context)

# Example: Navigation
def example_navigation():
    """
    Expression: (λx. x + 1) 5

    Zipper positions:
    1. Focus: (λx. x + 1) 5, Context: Top
    2. Focus: λx. x + 1, Context: ApFunc(5, Top)
    3. Focus: x + 1, Context: Lam("x", ApFunc(5, Top))
    4. Focus: x, Context: PlusLeft(1, Lam("x", ApFunc(5, Top)))
    """
    pass

print("Zipper: Efficient navigation with O(1) up/down")
```

### Rendering and Layout

**Project AST to display**: Pretty-printing with cursor indication

```python
class Renderer:
    """
    Render AST as text with cursor

    Considerations:
    - Indentation
    - Parentheses (minimal)
    - Highlighting (syntax, types, cursor)
    - Multi-line layout
    """

    def render(self, zipper: Zipper) -> str:
        """
        Render with cursor indicated

        Example:
          if ▸true then 1 else 2
               ^^^ cursor here
        """
        # Reconstruct full expression
        full_expr = self.reconstruct_root(zipper)

        # Pretty print with cursor marker
        return self.pretty_print_with_cursor(full_expr, zipper.focus)

    def pretty_print_with_cursor(self, expr: 'Expr', cursor_focus: 'Expr') -> str:
        """
        Pretty print, mark cursor position

        Uses boxes/layout algorithm
        """
        match expr:
            case Num(n):
                marker = "▸" if expr == cursor_focus else ""
                return f"{marker}{n}"

            case Lam(param, body):
                body_str = self.pretty_print_with_cursor(body, cursor_focus)
                marker = "▸" if expr == cursor_focus else ""
                return f"{marker}λ{param}. {body_str}"

            case Ap(func, arg):
                func_str = self.pretty_print_with_cursor(func, cursor_focus)
                arg_str = self.pretty_print_with_cursor(arg, cursor_focus)
                marker = "▸" if expr == cursor_focus else ""
                return f"{marker}({func_str} {arg_str})"

            # ... other cases

    def layout_boxes(self, expr: 'Expr') -> 'Box':
        """
        Box layout algorithm (Haskell-style)

        Determine:
        - Horizontal vs vertical layout
        - Indentation
        - Line breaking
        """
        pass

print("Rendering: AST → pretty text with cursor")
```

### Selection and Multi-Cursor

**Selection**: Mark range in AST

```python
@dataclass
class Selection:
    """
    Selection in structure editor

    Two approaches:
    1. Path-based: (start_path, end_path)
    2. Subtree-based: Select whole subtree
    """
    root: 'Expr'
    selected_paths: List[List[int]]  # Multiple cursors!

    def delete_selection(self) -> 'Expr':
        """
        Delete selected nodes

        Replace each with hole
        """
        result = self.root
        for path in self.selected_paths:
            result = replace_at_path(result, path, EmptyHole())
        return result

    def extract_selection(self) -> 'Expr':
        """
        Extract selection to variable

        Before: e₁ + (e₂ + e₃)  [select e₂ + e₃]
        After:  let x = e₂ + e₃ in e₁ + x
        """
        pass

# Multi-cursor editing
class MultiCursor:
    """
    Multiple cursors in structure editor

    Example: Rename all occurrences
    - Select variable x
    - Add cursor at each occurrence
    - Type new name
    - All occurrences updated simultaneously
    """
    cursors: List[Zipper]

    def apply_action(self, action: EditAction):
        """Apply action to all cursors"""
        self.cursors = [self.apply_single(c, action) for c in self.cursors]

print("Selection: Subtree-based, supports multi-cursor")
```

### Integration with Text Workflows

**Hybrid approach**: Structure editor with text escape hatch

```python
class HybridEditor:
    """
    Combine structure editing with text editing

    Modes:
    1. Structure mode (default): Edit AST
    2. Text mode: Edit as text, re-parse on commit

    Users can drop to text for familiar workflow
    """

    def __init__(self):
        self.mode = "structure"
        self.ast = EmptyHole()
        self.text_buffer = None

    def enter_text_mode(self):
        """
        Switch to text mode

        - Serialize AST to text
        - Let user edit text freely
        - Parse on exit
        """
        self.mode = "text"
        self.text_buffer = serialize_to_text(self.ast)
        # User now edits text_buffer

    def exit_text_mode(self):
        """
        Return to structure mode

        - Parse text buffer
        - If success: Update AST
        - If error: Show errors, stay in text mode
        """
        try:
            new_ast = parse(self.text_buffer)
            self.ast = new_ast
            self.mode = "structure"
            self.text_buffer = None
        except SyntaxError as e:
            # Show error, let user fix
            show_error(e)

    def copy_as_text(self) -> str:
        """
        Copy AST as text (for external tools)

        Enables interop with text-based tools:
        - Version control (git)
        - Code review tools
        - grep, sed, etc.
        """
        return serialize_to_text(self.ast)

print("Hybrid: Structure editing + text mode escape hatch")
```

### Educational Use Cases

**Structure editors for learning**: Reduce cognitive load

```python
class EducationalEditor:
    """
    Structure editor for teaching programming

    Benefits:
    - No syntax errors distract from learning
    - Type-guided construction teaches types
    - Example-driven development workflow
    - Visual execution (step through)
    """

    def beginner_mode(self):
        """
        Beginner mode features:

        1. Limited action palette
           - Only show simple actions initially
           - Unlock more as learner progresses

        2. Inline help
           - "This hole expects a number"
           - "You can fill this with: 1, 2, x+1, ..."

        3. Example-driven
           - Show example inputs/outputs
           - Let learner fill holes to match examples

        4. Instant feedback
           - Type errors shown immediately
           - Evaluation results live
        """
        pass

    def visual_execution(self, program: 'Expr'):
        """
        Visual step-through execution

        - Highlight current redex
        - Show evaluation steps
        - Inspect values at each step

        Helps learners understand evaluation
        """
        pass

print("Educational: Structure editors reduce syntax burden")
```

---

## Patterns

### Pattern 1: Progressive Disclosure

```python
def progressive_disclosure():
    """
    Show only relevant actions at each point

    Beginner:
    - construct num
    - construct var
    - construct +

    Intermediate:
    - + construct if
    - + construct lambda

    Advanced:
    - + construct let
    - + construct match
    - + construct type

    Gradually unlock complexity
    """
    print("Progressive: Start simple, add complexity as needed")
```

### Pattern 2: Template-Based Construction

```python
def template_construction(template_name: str) -> 'Expr':
    """
    Common patterns as templates

    Templates:
    - "if-then-else" → if ⦇⦈ then ⦇⦈ else ⦇⦈
    - "let-in" → let x = ⦇⦈ in ⦇⦈
    - "fold" → fold ⦇⦈ ⦇⦈ ⦇⦈

    Reduces repetitive construction
    """
    templates = {
        "if": IfExpr(EmptyHole(), EmptyHole(), EmptyHole()),
        "let": LetExpr("x", EmptyHole(), EmptyHole()),
    }
    return templates.get(template_name, EmptyHole())

print("Templates: Common patterns as single action")
```

### Pattern 3: Type-Directed Palette

```python
def type_directed_palette(expected_type: 'Type', context: dict) -> List[str]:
    """
    Show only actions that produce expected type

    Expected: Bool
    Show:
    - true, false (literals)
    - x == y (if x, y : comparable)
    - not ⦇⦈ (constructor)
    - ⦇⦈ && ⦇⦈ (operator)

    Hide:
    - + (produces Num, not Bool)
    - lambda (produces function)
    """
    palette = []

    if expected_type == TBool():
        palette.extend(["true", "false", "not", "&&", "||"])

    if expected_type == TNum():
        palette.extend(["0", "1", "+", "*", "-"])

    # Variables of matching type
    for var, typ in context.items():
        if consistent(typ, expected_type):
            palette.append(var)

    return palette

print("Type-directed: Only show valid constructions")
```

---

## Quick Reference

### Edit Action Categories

| Category | Actions | Purpose |
|----------|---------|---------|
| Movement | parent, child(n) | Navigate AST |
| Construction | num, var, lam, ap, if, + | Build structure |
| Deletion | del | Remove (→ hole) |
| Refinement | finish, refine | Transform holes |

### Zipper Operations

```
go_up() : Move to parent (O(1))
go_down(n) : Move to nth child (O(1))
replace(e) : Replace focus (O(1))
reconstruct() : Build root (O(depth))
```

### Rendering Strategies

```
Inline: Single line (a + b)
Block: Multi-line with indentation
  if cond
  then branch1
  else branch2
Hybrid: Smart line breaking
```

---

## Anti-Patterns

❌ **Forcing structure-only**: Users need text mode sometimes
✅ Provide text mode escape hatch

❌ **Ignoring copy/paste**: Users expect familiar operations
✅ Support clipboard operations (serialize/parse)

❌ **Poor keyboard navigation**: Mouse-only is slow
✅ Keyboard shortcuts for all actions

❌ **No visual feedback**: User doesn't know what's valid
✅ Show available actions, highlight cursor

---

## Related Skills

- `hazelnut-calculus.md` - Formal edit action semantics
- `typed-holes-foundations.md` - Holes in structure editors
- `live-programming-holes.md` - Live programming with structure editors
- `typed-holes-interaction.md` - IDE integration patterns

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
