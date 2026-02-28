---
name: mcp-tool-design
description: Designing effective MCP tools with proper naming, schemas, error handling, annotations, and progressive disclosure patterns
---

# MCP Tool Design

**Scope**: Tool naming, input schemas, error handling, annotations, idempotency, progressive disclosure
**Lines**: ~280
**Last Updated**: 2025-11-01

## When to Use This Skill

Activate this skill when:
- Designing MCP tool interfaces and naming conventions
- Defining parameter schemas for MCP tools
- Implementing error handling with isError flag
- Adding tool annotations (readOnlyHint, destructiveHint)
- Making tools safe and idempotent
- Applying progressive disclosure patterns
- Reviewing MCP tools for anti-patterns

## Core Concepts

### Tool Naming Conventions

Tools are identified by name and described in natural language for the LLM. Names and descriptions are critical because the model uses them to decide when and how to call a tool.

**Naming rules**:
- Use `verb_noun` format: `search_files`, `create_issue`, `get_user`
- Be specific: `search_codebase` not `search`
- Use consistent prefixes for related tools: `db_query`, `db_insert`, `db_schema`
- Avoid abbreviations the model might not understand
- Keep under 64 characters

**Description rules**:
- First sentence: what the tool does (used for tool selection)
- Additional sentences: constraints, caveats, when NOT to use it
- Mention return value format if non-obvious
- Include examples of valid input if the schema is complex

```typescript
server.tool(
  "search_codebase",
  "Search for files and code matching a pattern in the project. " +
  "Returns file paths and matching line content. " +
  "Use glob patterns for file names, regex for content search.",
  { /* schema */ },
  handler
);
```

---

### Input Schema Design

MCP tools use JSON Schema for input validation. The schema is sent to the model, which generates conforming input.

#### Required vs Optional Parameters

```typescript
server.tool(
  "query_database",
  "Execute a read-only SQL query against the database",
  {
    query: z.string().describe("SQL SELECT query to execute"),
    database: z.string().optional().describe("Database name. Defaults to 'main'"),
    limit: z.number().optional().default(100).describe("Max rows to return (default: 100)"),
  },
  handler
);
```

**Guidelines**:
- Required params: the minimum needed to do useful work
- Optional params: sensible defaults, documented in description
- Use `.describe()` on every parameter -- the model reads these
- Prefer strings over enums unless the set is small and fixed
- For complex inputs, use nested objects sparingly (models handle flat schemas better)

#### Schema Patterns

**Enum for constrained choices**:
```typescript
format: z.enum(["json", "csv", "text"]).describe("Output format"),
```

**Array inputs**:
```typescript
tags: z.array(z.string()).describe("Filter by tags"),
```

**Object inputs** (use sparingly):
```typescript
filters: z.object({
  status: z.string().optional(),
  assignee: z.string().optional(),
}).describe("Optional filters to narrow results"),
```

---

### Error Handling

MCP tools can signal errors in two ways:

#### 1. Tool-Level Errors (isError flag)
For errors the model should see and potentially recover from:

```typescript
server.tool("read_file", "Read file contents", { path: z.string() },
  async ({ path }) => {
    try {
      const content = await fs.readFile(path, "utf-8");
      return { content: [{ type: "text", text: content }] };
    } catch (err) {
      return {
        isError: true,
        content: [{
          type: "text",
          text: `Error reading ${path}: ${err.message}`,
        }],
      };
    }
  }
);
```

```python
@server.tool()
async def read_file(path: str) -> str:
    """Read file contents."""
    try:
        return Path(path).read_text()
    except FileNotFoundError:
        raise McpError(f"File not found: {path}")
    except PermissionError:
        raise McpError(f"Permission denied: {path}")
```

**Use isError when**:
- File not found, permission denied
- Invalid user-provided input
- Resource temporarily unavailable
- The model might retry or try a different approach

#### 2. Protocol-Level Errors (JSON-RPC errors)
For programming errors and protocol violations. These indicate bugs, not user errors.

- Invalid method name
- Malformed request
- Internal server crash

**Never use protocol errors for expected failure modes** (file not found, empty results, etc.).

#### Structured Error Responses

Provide actionable information:
```typescript
return {
  isError: true,
  content: [{
    type: "text",
    text: JSON.stringify({
      error: "QUERY_SYNTAX_ERROR",
      message: "Invalid SQL syntax near 'FORM'",
      suggestion: "Did you mean 'FROM'?",
      line: 1,
      column: 15,
    }),
  }],
};
```

---

### Tool Annotations

Annotations provide metadata about tool behavior without affecting execution. Clients use them for UI hints, safety checks, and permission prompts.

```typescript
server.tool(
  "delete_file",
  "Permanently delete a file from the filesystem",
  { path: z.string().describe("File path to delete") },
  async ({ path }) => { /* ... */ },
  {
    annotations: {
      readOnlyHint: false,      // This tool modifies state
      destructiveHint: true,    // This tool destroys data
      idempotentHint: true,     // Deleting twice = same result
      openWorldHint: false,     // Only affects local filesystem
    },
  }
);
```

| Annotation | Default | Meaning |
|-----------|---------|---------|
| `readOnlyHint` | `false` | Tool only reads, never modifies state |
| `destructiveHint` | `false` | Tool may irreversibly destroy data |
| `idempotentHint` | `false` | Calling multiple times = same effect as once |
| `openWorldHint` | `true` | Tool interacts with external world (network, APIs) |

**Best practices**:
- Set `readOnlyHint: true` on all read-only tools (search, list, get)
- Set `destructiveHint: true` on delete, overwrite, drop operations
- Set `idempotentHint: true` when safe to retry (PUT semantics)
- Annotations are hints, not enforcement -- server must still validate

---

### Idempotency and Safety

**Safe tools** (no side effects): search, read, list, get, count
- Always set `readOnlyHint: true`
- Can be called any number of times without consequence

**Idempotent tools** (same result on repeat): create-or-update, delete, set
- Set `idempotentHint: true`
- Calling with same args twice produces same state
- Model can safely retry on timeout

**Non-idempotent tools** (different result on repeat): append, increment, send
- Default hints are fine
- Document in description that repeated calls have cumulative effects
- Consider adding deduplication (idempotency keys)

---

### Progressive Disclosure

Design tool sets that let the model explore incrementally:

```
1. list_items     → Overview of what's available
2. get_item       → Details about a specific item
3. update_item    → Make changes to a specific item
```

**Pattern: list -> detail -> execute**

```typescript
// Level 1: Discover what's available
server.tool("list_tables", "List all database tables", {}, handler);

// Level 2: Get details about a specific thing
server.tool("describe_table", "Get schema for a table",
  { table: z.string() }, handler);

// Level 3: Operate on it
server.tool("query_table", "Run a query against a table",
  { table: z.string(), query: z.string() }, handler);
```

This pattern:
- Reduces errors (model learns the domain before acting)
- Limits blast radius (model explores before modifying)
- Improves tool selection (model has context for choosing the right tool)

---

## Anti-Patterns

### God Tools
**Problem**: One tool that does everything via mode/action parameters.
```typescript
// BAD: god tool
server.tool("database", "Do database things",
  { action: z.enum(["query", "insert", "delete", "schema"]), ... });
```
**Fix**: Separate tools with focused responsibilities.

### Missing Descriptions
**Problem**: No description or parameter descriptions. Model guesses usage.
```typescript
// BAD
server.tool("proc", "", { x: z.string() }, handler);
```
**Fix**: Always provide clear descriptions for tools and every parameter.

### No Input Validation
**Problem**: Trusting model-generated input blindly.
**Fix**: Validate beyond schema -- check file paths, SQL injection, bounds.

### Returning Raw Errors
**Problem**: Stack traces and internal errors exposed to the model.
**Fix**: Catch errors, return structured messages with `isError: true`.

### Too Many Tools
**Problem**: 50+ tools overwhelm the model's context and selection ability.
**Fix**: Group related operations. Use progressive disclosure. Consider multiple focused servers.

### No Empty-Result Handling
**Problem**: Returning nothing or undefined when search finds zero results.
**Fix**: Always return a clear message: "No results found for query X".

---

## Checklist

- [ ] Tool names follow `verb_noun` convention
- [ ] Every tool has a clear, multi-sentence description
- [ ] Every parameter has a `.describe()` annotation
- [ ] Required vs optional params are correct
- [ ] Error cases return `isError: true` with actionable messages
- [ ] Annotations set correctly (readOnlyHint, destructiveHint)
- [ ] Read-only tools marked as such
- [ ] Destructive tools flagged appropriately
- [ ] Progressive disclosure pattern applied where applicable
- [ ] Total tool count is manageable (< 20 per server recommended)
- [ ] Input validated beyond schema (path traversal, injection, bounds)
- [ ] Empty results return clear messages

## Related Skills

- `mcp-server-fundamentals.md` - Server setup and primitives
- `mcp-testing.md` - Testing tool implementations
- `../api/rest-api-design.md` - REST resource modeling (parallel patterns)
- `../api/api-error-handling.md` - Error response design
