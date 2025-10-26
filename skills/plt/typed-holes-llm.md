---
name: typed-holes-llm
description: LLM integration with typed holes (OOPSLA 2024) - static context for code synthesis, type-driven prompting, validation, ranking, combining language servers with LLMs
---

# Typed Holes + LLMs: AI-Assisted Programming

**Scope**: OOPSLA 2024 "Statically Contextualizing LLMs", type-driven synthesis, validation, ranking, practical integration
**Lines**: ~450
**Last Updated**: 2025-10-25

## When to Use This Skill

Activate this skill when:
- Building AI-assisted programming tools (Copilot-like features)
- Integrating LLMs with typed languages
- Implementing type-aware code completion
- Designing AI pair programming systems
- Validating and ranking LLM-generated code
- Combining static analysis with neural code generation

## Core Concepts

### The Problem: LLMs Without Types

**Challenge**: LLMs generate code without understanding types

```python
from dataclasses import dataclass
from typing import List, Optional

# Traditional LLM code completion
class NaiveLLMCompletion:
    """
    Problem with naive LLM completion:

    User types:
      def process_data(x: int) ->

    LLM generates:
      return str(x)  # OK

    But also generates plausible-looking WRONG code:
      return x.split(",")  # Type error! int has no split
      return [x]  # Type error! Expected str, got List[int]
    """

    def complete(self, prefix: str) -> str:
        """
        LLM samples from learned distribution

        No type checking!
        No context about what's in scope!
        No knowledge of expected return type!
        """
        # Call LLM API
        completion = llm_api(prefix)
        return completion  # Might not even parse!

print("Problem: LLMs don't understand types or context")
```

### Solution: Statically Contextualizing LLMs (OOPSLA 2024)

**Key idea**: Use typed holes to provide static context to LLMs

```python
@dataclass
class TypedHoleContext:
    """
    Rich context from typed hole

    From OOPSLA 2024: "Statically Contextualizing Large Language Models
    with Typed Holes"
    """
    hole_id: str
    expected_type: 'Type'
    in_scope_vars: dict  # var → type
    imports: List[str]
    surrounding_code: str
    type_definitions: dict  # Available types

    def to_llm_prompt(self) -> str:
        """
        Convert typed hole context to LLM prompt

        This is the KEY insight: Type information → Better prompts
        """
        prompt = f"""Complete this code:

Expected type: {self.expected_type}

Available variables:
{self.format_vars()}

Imports:
{chr(10).join(self.imports)}

Context:
{self.surrounding_code}

Complete the hole at <<<HOLE>>> with code that has type {self.expected_type}.
Only use variables from the available list.
"""
        return prompt

    def format_vars(self) -> str:
        """Format in-scope variables for prompt"""
        return "\n".join([f"  {var} : {typ}"
                         for var, typ in self.in_scope_vars.items()])

# Example usage
def example_static_context():
    """
    Code:
      def factorial(n: int) -> int:
          if n == 0:
              return 1
          else:
              return <<<HOLE>>>

    Context extracted:
      Expected type: int
      In scope: n : int, factorial : int → int
      Imports: (none)

    LLM prompt:
      "Complete hole with type int.
       Available: n : int, factorial : int → int"

    LLM generates:
      n * factorial(n - 1)  ✓ Correct type!
    """
    pass

print("Solution: Static context from types guides LLM")
```

### Architecture: Language Server + LLM

**Integration pattern**: Combine LSP with LLM API

```python
class LanguageServerLLMBridge:
    """
    Bridge between language server and LLM

    Language Server provides:
    - Type information
    - Scope information
    - Available symbols
    - Diagnostics

    LLM provides:
    - Code generation
    - Pattern matching
    - Idiomatic completions
    """

    def __init__(self, lsp_client, llm_client):
        self.lsp = lsp_client
        self.llm = llm_client

    async def complete_hole(self, document_uri: str, position: tuple) -> List[str]:
        """
        Complete typed hole using LSP + LLM

        Workflow:
        1. LSP: Get type at position
        2. LSP: Get scope (available vars)
        3. Build prompt from static context
        4. LLM: Generate candidates
        5. LSP: Type-check each candidate
        6. Return only valid candidates, ranked by type fit
        """
        # Step 1-2: Get static context from LSP
        type_info = await self.lsp.get_type_at_position(document_uri, position)
        scope = await self.lsp.get_scope(document_uri, position)

        context = TypedHoleContext(
            hole_id="h1",
            expected_type=type_info.expected_type,
            in_scope_vars=scope,
            imports=self.get_imports(document_uri),
            surrounding_code=self.get_context_window(document_uri, position),
            type_definitions={}
        )

        # Step 3: Build prompt
        prompt = context.to_llm_prompt()

        # Step 4: Generate candidates
        candidates = await self.llm.generate(prompt, n=10, temperature=0.7)

        # Step 5-6: Validate and rank
        valid_candidates = []
        for candidate in candidates:
            if await self.validate_candidate(document_uri, position, candidate):
                type_score = await self.type_match_score(candidate, type_info.expected_type)
                valid_candidates.append((candidate, type_score))

        # Sort by type match score
        valid_candidates.sort(key=lambda x: x[1], reverse=True)

        return [c for c, _ in valid_candidates]

    async def validate_candidate(self, uri: str, pos: tuple, code: str) -> bool:
        """
        Validate candidate using LSP

        1. Insert code at position
        2. Get diagnostics
        3. Check for type errors
        4. Return valid/invalid
        """
        # Insert candidate into document
        test_doc = self.insert_at_position(uri, pos, code)

        # Get diagnostics
        diagnostics = await self.lsp.get_diagnostics(test_doc)

        # Check for errors at or near insertion point
        has_errors = any(d.severity == "error" for d in diagnostics
                        if overlaps(d.range, pos))

        return not has_errors

    async def type_match_score(self, code: str, expected: 'Type') -> float:
        """
        Score how well code matches expected type

        Exact match: 1.0
        Consistent (gradual): 0.8
        Subtype: 0.9
        Supertype: 0.5
        Inconsistent: 0.0
        """
        actual = await self.lsp.infer_type(code)

        if actual == expected:
            return 1.0
        elif self.is_subtype(actual, expected):
            return 0.9
        elif self.is_consistent(actual, expected):
            return 0.8
        elif self.is_supertype(actual, expected):
            return 0.5
        else:
            return 0.0

print("Architecture: LSP provides context, LLM generates, LSP validates")
```

### Type-Driven Prompt Engineering

**Craft prompts using type information**

```python
class TypeDrivenPromptBuilder:
    """
    Build LLM prompts from type information

    Strategy: More type info → Better prompts → Better completions
    """

    def build_prompt(self, hole: TypedHoleContext) -> str:
        """
        Build comprehensive prompt

        Include:
        1. Expected type (most important!)
        2. Available variables and their types
        3. Type definitions (if complex types)
        4. Examples (if available)
        5. Constraints (if any)
        """
        sections = []

        # Section 1: Goal
        sections.append(f"Goal: Write code with type {hole.expected_type}")

        # Section 2: Available variables
        if hole.in_scope_vars:
            sections.append(self.format_scope(hole.in_scope_vars))

        # Section 3: Type definitions
        if hole.expected_type.is_complex():
            sections.append(self.format_type_defs(hole.expected_type))

        # Section 4: Examples
        examples = self.find_similar_examples(hole.expected_type)
        if examples:
            sections.append(self.format_examples(examples))

        # Section 5: Constraints
        sections.append("Constraints: Only use variables in scope. Code must type-check.")

        return "\n\n".join(sections)

    def format_scope(self, scope: dict) -> str:
        """
        Format in-scope variables

        Group by type for clarity
        """
        by_type = {}
        for var, typ in scope.items():
            by_type.setdefault(str(typ), []).append(var)

        lines = ["Available variables:"]
        for typ, vars in by_type.items():
            lines.append(f"  {typ}: {', '.join(vars)}")

        return "\n".join(lines)

    def format_type_defs(self, typ: 'Type') -> str:
        """
        Show type definitions for complex types

        Example:
          User : Record
            { name : String
            , age : Int
            , email : String
            }
        """
        if isinstance(typ, RecordType):
            fields = "\n".join([f"    {name} : {field_type}"
                              for name, field_type in typ.fields.items()])
            return f"{typ.name} : Record\n{{\n{fields}\n}}"
        # ... other complex types

    def find_similar_examples(self, expected_type: 'Type') -> List[str]:
        """
        Find existing code with same type

        Search codebase for:
        - Functions returning expected_type
        - Expressions of expected_type

        Show as examples to LLM
        """
        # Search codebase index
        examples = search_by_type(expected_type, limit=3)
        return examples

print("Type-driven prompts: Richer context → Better completions")
```

### Validation and Ranking Pipeline

**Filter and rank LLM outputs by type correctness**

```python
class CandidateValidator:
    """
    Validate LLM-generated candidates

    Multi-stage pipeline:
    1. Parse check: Valid syntax?
    2. Type check: Correct type?
    3. Scope check: Only uses available vars?
    4. Style check: Idiomatic?
    5. Rank by quality
    """

    def __init__(self, lsp_client):
        self.lsp = lsp_client

    async def validate_pipeline(self, candidates: List[str],
                               context: TypedHoleContext) -> List[tuple[str, float]]:
        """
        Multi-stage validation pipeline

        Returns: List[(code, score)] sorted by score
        """
        results = []

        for candidate in candidates:
            score = await self.score_candidate(candidate, context)
            if score > 0:  # Only valid candidates
                results.append((candidate, score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results

    async def score_candidate(self, code: str, context: TypedHoleContext) -> float:
        """
        Score candidate (0.0 - 1.0)

        Scoring criteria:
        - Parse: Must parse (filter out)
        - Type exact match: +1.0
        - Type consistent: +0.8
        - Only uses in-scope vars: +0.2
        - Idiomatic style: +0.1
        - Follows naming conventions: +0.05
        """
        total_score = 0.0

        # Stage 1: Parse check
        if not self.parses(code):
            return 0.0  # Invalid

        # Stage 2: Type check
        inferred_type = await self.lsp.infer_type(code)
        type_score = self.type_compatibility(inferred_type, context.expected_type)
        if type_score == 0:
            return 0.0  # Type error
        total_score += type_score

        # Stage 3: Scope check
        used_vars = self.extract_variables(code)
        if not all(v in context.in_scope_vars for v in used_vars):
            return 0.0  # Uses undefined var

        total_score += 0.2  # Bonus for correct scope

        # Stage 4: Style check
        style_score = await self.check_style(code)
        total_score += style_score * 0.1

        # Stage 5: Naming conventions
        naming_score = self.check_naming(code)
        total_score += naming_score * 0.05

        return min(total_score, 1.0)  # Cap at 1.0

    def type_compatibility(self, actual: 'Type', expected: 'Type') -> float:
        """
        How compatible are these types?

        1.0: Exact match
        0.9: Subtype
        0.8: Consistent (gradual typing)
        0.5: Supertype (overly general)
        0.0: Incompatible
        """
        if actual == expected:
            return 1.0
        elif is_subtype(actual, expected):
            return 0.9
        elif is_consistent(actual, expected):
            return 0.8
        elif is_supertype(actual, expected):
            return 0.5
        else:
            return 0.0

    async def check_style(self, code: str) -> float:
        """
        Check code style

        Use linter/formatter to check:
        - Line length
        - Formatting
        - Idioms
        """
        lint_results = await self.lsp.lint(code)
        # Fewer warnings → Higher score
        return max(0, 1.0 - len(lint_results) * 0.1)

print("Validation: Multi-stage filter → Only show type-correct code")
```

### Interactive Refinement Loop

**User + LLM collaboration via holes**

```python
class InteractiveRefinement:
    """
    Interactive refinement with LLM

    Workflow:
    1. User creates hole
    2. LLM suggests completions
    3. User picks one or refines hole further
    4. Repeat until satisfied
    """

    def __init__(self, llm_bridge: LanguageServerLLMBridge):
        self.llm = llm_bridge
        self.refinement_history = []

    async def suggest_for_hole(self, hole: TypedHoleContext) -> List[str]:
        """
        Suggest completions for hole

        Returns top N candidates
        """
        candidates = await self.llm.complete_hole(hole.document_uri, hole.position)
        return candidates[:5]  # Top 5

    async def refine_hole(self, hole: TypedHoleContext, user_refinement: str):
        """
        User refines hole (makes more specific)

        Example:
          Original hole: ?result : List[int]
          User refines: map ?f ?xs

        Now we have two holes:
          ?f : int → int
          ?xs : List[int]

        LLM generates for each sub-hole
        """
        # Parse user refinement
        refined = parse_with_holes(user_refinement)

        # Extract new holes
        new_holes = extract_holes(refined, hole.expected_type)

        # Generate candidates for each new hole
        suggestions = {}
        for new_hole in new_holes:
            suggestions[new_hole.hole_id] = await self.suggest_for_hole(new_hole)

        return suggestions

    def record_choice(self, hole_id: str, chosen_code: str):
        """
        Record user's choice

        Use for:
        - Learning user preferences
        - Improving future suggestions
        - Building local context
        """
        self.refinement_history.append({
            'hole': hole_id,
            'choice': chosen_code,
            'timestamp': time.time()
        })

    async def learn_from_history(self):
        """
        Learn from user's past choices

        Fine-tune LLM or adjust ranking based on:
        - Types user prefers
        - Coding style
        - Idiom preferences
        """
        # Analyze patterns in choices
        patterns = self.analyze_patterns(self.refinement_history)

        # Adjust ranking weights
        self.update_ranking_weights(patterns)

print("Interactive: User guides, LLM suggests, iterate until satisfied")
```

### Context Building Strategies

**What context to include in prompts?**

```python
class ContextBuilder:
    """
    Build rich context for LLM prompts

    Balance:
    - More context → Better suggestions
    - Too much context → Token limits, noise
    """

    def build_context(self, hole: TypedHoleContext, max_tokens: int = 2000) -> str:
        """
        Build context within token budget

        Priority (highest first):
        1. Expected type (essential)
        2. In-scope variables (essential)
        3. Surrounding code (high)
        4. Type definitions (medium)
        5. Similar examples (medium)
        6. Imports (low)
        7. Module docs (low)
        """
        context_parts = []
        tokens_used = 0

        # Priority 1: Expected type
        type_str = f"Expected type: {hole.expected_type}"
        context_parts.append(type_str)
        tokens_used += estimate_tokens(type_str)

        # Priority 2: In-scope variables
        scope_str = self.format_scope(hole.in_scope_vars)
        if tokens_used + estimate_tokens(scope_str) < max_tokens:
            context_parts.append(scope_str)
            tokens_used += estimate_tokens(scope_str)

        # Priority 3: Surrounding code
        surrounding = self.get_surrounding_code(hole, context_lines=5)
        if tokens_used + estimate_tokens(surrounding) < max_tokens:
            context_parts.append(f"Surrounding code:\n{surrounding}")
            tokens_used += estimate_tokens(surrounding)

        # Priority 4: Type definitions
        if tokens_used < max_tokens * 0.7:  # Only if room
            type_defs = self.get_relevant_type_defs(hole.expected_type)
            if tokens_used + estimate_tokens(type_defs) < max_tokens:
                context_parts.append(type_defs)
                tokens_used += estimate_tokens(type_defs)

        # Priority 5: Examples
        if tokens_used < max_tokens * 0.8:
            examples = self.find_similar_examples(hole.expected_type, limit=2)
            for ex in examples:
                if tokens_used + estimate_tokens(ex) < max_tokens:
                    context_parts.append(f"Example:\n{ex}")
                    tokens_used += estimate_tokens(ex)

        return "\n\n".join(context_parts)

    def get_surrounding_code(self, hole: TypedHoleContext, context_lines: int) -> str:
        """
        Get N lines before and after hole

        Include enough to understand context,
        but not so much to overwhelm LLM
        """
        pass

    def get_relevant_type_defs(self, typ: 'Type') -> str:
        """
        Get type definitions relevant to expected type

        If expected type is User:
        - Include User definition
        - Include types User references

        Build dependency closure (limited depth)
        """
        pass

print("Context building: Prioritize essential info, fit in token budget")
```

---

## Patterns

### Pattern 1: Type-First Completion

```python
async def type_first_completion_workflow(lsp, llm, position):
    """
    1. User types partial expression
    2. LSP infers expected type from context
    3. Use expected type to guide LLM
    4. Generate only candidates of correct type

    Example:
      def f(x: int) -> str:
          return <<<cursor>>>

    LSP: Expected type is str
    LLM prompt: "Generate expression of type str, using x : int"
    LLM candidates:
      - str(x) ✓
      - str(x * 2) ✓
      - f"{x}" ✓
      NOT:
      - x (wrong type)
      - x + 1 (wrong type)
    """
    expected_type = await lsp.infer_expected_type(position)
    candidates = await llm.generate_typed(expected_type)
    return candidates
```

### Pattern 2: Iterative Refinement with Feedback

```python
async def iterative_refinement(user, llm, hole):
    """
    1. LLM suggests initial completions
    2. User picks one or refines further
    3. If refinement: LLM suggests for refined hole
    4. Repeat until complete

    Example:
      Hole: ?h : List[int]

      Round 1:
        LLM suggests: [1, 2, 3], [], list(range(10))
        User: "map over something"

      Round 2:
        User types: map ?f ?xs
        Now holes: ?f : int → int, ?xs : List[int]
        LLM suggests for ?f: lambda x: x+1, lambda x: x*2
        LLM suggests for ?xs: [1,2,3], range(10)

      User picks: map (lambda x: x*2) (range(10))
    """
    pass
```

### Pattern 3: Example-Driven Synthesis

```python
async def example_driven_synthesis(examples, llm):
    """
    User provides examples, LLM synthesizes code

    Examples:
      f(0) = 0
      f(1) = 1
      f(5) = 120

    Prompt to LLM:
      "Write function f : int → int
       such that:
         f(0) = 0
         f(1) = 1
         f(5) = 120"

    LLM synthesizes: factorial function

    Then validate against examples!
    """
    prompt = build_example_prompt(examples)
    candidates = await llm.generate(prompt)

    # Validate against examples
    valid = [c for c in candidates
             if all(eval_candidate(c, inp) == out
                   for inp, out in examples)]
    return valid
```

---

## Quick Reference

### Integration Architecture

```
┌─────────────┐
│ Editor/IDE  │
└──────┬──────┘
       │
┌──────▼─────────┐         ┌──────────────┐
│ Language       │◄───────►│ LLM API      │
│ Server (LSP)   │         │ (OpenAI,etc) │
└───────┬────────┘         └──────────────┘
        │
    Type info,
    Validation
```

### Prompt Template

```
Goal: Write code with type {expected_type}

Available variables:
  {var1} : {type1}
  {var2} : {type2}

Constraints:
- Only use variables in scope
- Code must type-check
- Return type must be {expected_type}

Complete: {hole_context}
```

### Validation Pipeline

```
LLM Output → Parse → Type Check → Scope Check → Style Check → Rank
           ↓        ↓             ↓              ↓             ↓
         Invalid  Invalid      Invalid        Valid         Top-N
         (reject) (reject)     (reject)     (low rank)    (present)
```

---

## Anti-Patterns

❌ **Using LLM without type info**: Generates type-incorrect code
✅ Always include expected type in prompt

❌ **Accepting LLM output unchecked**: Dangerous!
✅ Validate every candidate before showing to user

❌ **Showing all LLM outputs**: Overwhelming, low quality
✅ Filter and rank, show only top valid candidates

❌ **Static prompts**: Same prompt for all contexts
✅ Build context-specific prompts using type info

❌ **Ignoring user feedback**: Miss learning opportunities
✅ Record choices, learn preferences, improve over time

---

## Related Skills

- `typed-holes-foundations.md` - Theoretical foundations
- `typed-holes-interaction.md` - IDE integration patterns
- `type-systems.md` - Type inference and checking
- `program-verification.md` - Verifying generated code
- `typed-holes-semantics.md` - Gradual typing and consistency

---

## Further Reading

- **OOPSLA 2024**: "Statically Contextualizing Large Language Models with Typed Holes"
- **Hazel Project**: hazel.org - Live programming with holes
- **Copilot Research**: GitHub's work on neural code completion
- **Tabnine**: Type-aware autocompletion

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
