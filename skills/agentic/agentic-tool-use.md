---
name: agentic-tool-use
description: Effective LLM tool calling patterns, parallel execution, error handling, and multi-tool workflow composition
---

# Agentic Tool Use

**Scope**: Function calling, structured output, parallel tool use, error handling, tool selection
**Lines**: ~300
**Last Updated**: 2026-02-02

## When to Use This Skill

Activate this skill when:
- Implementing function calling / tool use in LLM agents
- Designing tool schemas and structured outputs
- Composing multi-tool workflows (parallel and sequential)
- Handling tool call errors, retries, and fallbacks
- Selecting the right tool for a given subtask
- Optimizing tool call efficiency (reducing round trips)
- Debugging unexpected tool call behavior

## Core Concepts

### Tool Calling Fundamentals

An LLM tool call follows this cycle:

```
User message
  -> LLM reasons about what to do
  -> LLM emits tool_use block(s)
  -> System executes tool(s)
  -> Tool results returned to LLM
  -> LLM reasons about results
  -> LLM responds or makes more tool calls
```

**Key principle**: The LLM decides *which* tools to call and *what arguments* to pass. The system executes them. The LLM interprets results.

### Tool Schema Design

Well-designed tool schemas reduce errors and improve selection:

```json
{
  "name": "search_codebase",
  "description": "Search for patterns in source files. Use for finding function definitions, imports, usage patterns. Returns matching lines with file paths and line numbers.",
  "input_schema": {
    "type": "object",
    "properties": {
      "pattern": {
        "type": "string",
        "description": "Regex pattern to search for (e.g., 'def process_', 'import.*json')"
      },
      "file_glob": {
        "type": "string",
        "description": "Optional glob to filter files (e.g., '*.py', 'src/**/*.ts')"
      },
      "max_results": {
        "type": "integer",
        "description": "Maximum results to return. Default 20.",
        "default": 20
      }
    },
    "required": ["pattern"]
  }
}
```

**Schema design rules**:
- **Description tells when to use it**, not just what it does
- **Parameter descriptions include examples** of valid values
- **Required vs optional** clearly separated
- **Defaults documented** so the LLM knows what happens if omitted
- **Constrained types** (enums, bounds) prevent invalid calls

---

### Parallel Tool Use

Call multiple tools simultaneously when their inputs are independent:

```
# GOOD: Independent reads - call in parallel
Tool calls: [
  {"tool": "read_file", "args": {"path": "src/auth.py"}},
  {"tool": "read_file", "args": {"path": "src/models.py"}},
  {"tool": "read_file", "args": {"path": "tests/test_auth.py"}}
]

# BAD: Second call depends on first result - must be sequential
Tool calls: [
  {"tool": "search_code", "args": {"pattern": "class User"}},
  {"tool": "read_file", "args": {"path": "???"}}  # Don't know path yet
]
```

**Parallel when**:
- Multiple file reads with known paths
- Independent searches across different patterns
- Fetching unrelated data sources
- Running independent validation checks

**Sequential when**:
- Need result of tool A to determine tool B's arguments
- Write operations that must happen in order
- Verification after modification

**Efficiency**: Parallel calls complete in one round trip. Three sequential calls take three round trips. Prefer parallel when possible.

---

### Error Handling and Retry Strategies

```python
# Tiered error handling for tool calls
def handle_tool_error(error, tool_call, attempt):
    # Tier 1: Transient errors - retry immediately
    if error.type in ["timeout", "rate_limit", "connection_error"]:
        if attempt < 3:
            return retry(tool_call, backoff=2 ** attempt)

    # Tier 2: Input errors - fix and retry
    if error.type == "invalid_input":
        # Common fixes:
        # - File not found -> search for correct path
        # - Invalid regex -> simplify pattern
        # - Permission denied -> try alternative approach
        fixed_call = fix_input(tool_call, error.message)
        return retry(fixed_call)

    # Tier 3: Tool not available - use alternative
    if error.type == "tool_not_found":
        alternative = find_alternative_tool(tool_call)
        if alternative:
            return execute(alternative)

    # Tier 4: Persistent failure - report and continue
    return ToolResult(
        success=False,
        error=error.message,
        suggestion="Try alternative approach"
    )
```

**Common error patterns and fixes**:

| Error | Likely Cause | Fix |
|-------|-------------|-----|
| File not found | Wrong path | Search for file first |
| Timeout | Tool too slow | Reduce scope, add limits |
| Invalid JSON | Malformed arguments | Validate before calling |
| Permission denied | Sandboxed operation | Use allowed alternative |
| Empty result | Too narrow search | Broaden pattern, try synonyms |
| Too many results | Too broad search | Add filters, narrow scope |

---

### Tool Selection Heuristics

When multiple tools could accomplish a task, select based on:

```
1. Specificity: Prefer specialized tools over general ones
   - "Find function definition" -> code search (not generic grep)
   - "Check test status" -> test runner (not file read)

2. Efficiency: Prefer fewer round trips
   - Need 3 files? Parallel read (not sequential)
   - Need file + search? Can they parallel? Do it.

3. Reliability: Prefer tools with structured output
   - JSON output > free text output
   - Typed results > untyped results

4. Scope: Match tool scope to task scope
   - Single file edit -> edit tool
   - Multi-file rename -> batch tool or script
   - Whole project search -> glob/grep (not reading every file)
```

**Decision tree for common tasks**:

```
Need information?
  About file contents -> Read file
  About file existence/location -> Glob/find
  About content patterns -> Grep/search
  About external state -> API call / command

Need to change something?
  Single precise edit -> Edit tool (with exact match)
  New file -> Write tool
  Multiple related edits -> Script or sequential edits
  System state -> Shell command

Need to verify?
  Code compiles -> Build command
  Tests pass -> Test runner
  Behavior correct -> Script + assertions
```

---

### Composing Multi-Tool Workflows

Complex tasks require orchestrating multiple tools. Structure workflows as phases:

```python
# Phase-based multi-tool workflow
workflow = {
    "discover": {
        "description": "Understand the current state",
        "tools": ["glob", "grep", "read_file"],
        "parallel": True,
        "output": "file_map, relevant_code"
    },
    "plan": {
        "description": "Determine changes needed",
        "tools": [],  # LLM reasoning only, no tools
        "input": "discover.output",
        "output": "change_plan"
    },
    "execute": {
        "description": "Make the changes",
        "tools": ["edit_file", "write_file"],
        "parallel": False,  # Edits may conflict
        "input": "plan.output",
        "output": "modified_files"
    },
    "verify": {
        "description": "Confirm changes are correct",
        "tools": ["run_tests", "read_file"],
        "parallel": True,
        "input": "execute.output",
        "output": "test_results"
    }
}
```

**Workflow patterns**:

1. **Read-Modify-Verify**: Read state -> Make changes -> Verify result
2. **Search-Analyze-Act**: Find relevant code -> Understand it -> Transform it
3. **Plan-Execute-Check**: Determine steps -> Do them -> Validate outcome
4. **Iterate-Until-Done**: Try approach -> Check result -> Adjust -> Repeat

---

### Structured Output

When a tool returns structured data, use it structurally:

```python
# GOOD: Use structured tool results directly
search_result = tool("grep", pattern="def authenticate", glob="*.py")
for match in search_result.matches:
    file_content = tool("read_file", path=match.file)
    # Work with specific file

# BAD: Ignore structure, re-parse from text
result_text = tool("grep", pattern="def authenticate")
# Manually parsing "file.py:42: def authenticate(..." from text
```

**Structured output guidelines**:
- Parse tool results into structured data immediately
- Use typed fields rather than parsing free text
- Validate results match expected schema before using
- Handle missing/null fields gracefully

---

## Anti-Patterns

### Tool Abuse
**Problem**: Using tools when direct reasoning suffices.
**Example**: Calling a calculator tool for `2 + 2`. Reading a file just to count its lines when you already have it in context.
**Fix**: Only call tools when you need information or effects you don't already have.

### Unnecessary Sequential Calls
**Problem**: Making tool calls one at a time when they could be parallel.
**Example**: Reading 5 files sequentially when none depend on each other.
**Fix**: Identify independent calls and batch them.

### Missing Validation
**Problem**: Using tool results without checking success/failure.
**Example**: Assuming a file write succeeded without verifying. Using search results without checking if any matched.
**Fix**: Always check tool result status before proceeding.

### Over-Tooling
**Problem**: Using a tool for every micro-step instead of composing a script.
**Example**: 50 individual `edit_file` calls instead of one well-crafted script.
**Fix**: When making many similar changes, write a script and execute it.

### Ignoring Tool Descriptions
**Problem**: Choosing tools by name alone without reading descriptions.
**Example**: Using `write_file` when `edit_file` is more appropriate (and safer).
**Fix**: Match task requirements to tool descriptions, not just names.

---

## Checklist

- [ ] Are independent tool calls batched in parallel?
- [ ] Does each tool call have validated, well-formed arguments?
- [ ] Is there error handling for each tool call?
- [ ] Am I using the most specific tool available?
- [ ] Am I checking tool results before using them?
- [ ] Could I accomplish this with fewer tool calls?
- [ ] Am I avoiding tools when reasoning alone suffices?
- [ ] Are write operations followed by verification?

---

## Related Skills

- `agentic-task-decomposition.md` - Planning which tools to call and when
- `agentic-memory.md` - Managing tool results across conversation turns
