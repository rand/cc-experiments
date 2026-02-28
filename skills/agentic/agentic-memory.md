---
name: agentic-memory
description: Context window management, working memory patterns, and long-term persistence for LLM agents
---

# Agentic Memory

**Scope**: Context window management, working memory, long-term memory, summarization, state tracking
**Lines**: ~260
**Last Updated**: 2026-02-02

## When to Use This Skill

Activate this skill when:
- Managing context window limits in long-running agents
- Implementing working memory (scratchpads, state tracking, todo lists)
- Designing long-term memory (file-based, database-backed, embedding-based)
- Deciding when to summarize, truncate, or persist context
- Building multi-turn conversation architectures
- Preventing context overflow and stale memory issues

## Core Concepts

### Context Window Management

Every LLM has a finite context window. Effective agents manage it deliberately:

```
Context Window Budget:
  [System prompt]        ~2K tokens (fixed)
  [Skill/instructions]   ~3K tokens (loaded on demand)
  [Conversation history]  Variable (managed)
  [Working memory]       ~1-2K tokens (scratchpad)
  [Tool results]          Variable (most volatile)
  [Generation headroom]  ~4K tokens (reserved for output)
```

**Management strategies**:

#### Summarization
Replace verbose history with compressed summaries:

```python
# Before summarization (4000 tokens):
# Turn 1: Read 3 files, analyzed imports...
# Turn 2: Found bug in auth.py line 42...
# Turn 3: Attempted fix, tests failed because...
# Turn 4: Read test file, found assertion expects...

# After summarization (200 tokens):
# Summary: Found bug in auth.py:42 where token validation
# skips expiry check. Fix attempt failed because test_auth.py:88
# expects specific error message format. Need to update both
# the validation logic and the error message.
```

**When to summarize**:
- Context exceeds 60% capacity
- Old turns contain large tool results no longer needed
- Conversation shifts to a new subtask

**What to preserve in summaries**:
- Decisions made and their rationale
- Key findings (file paths, line numbers, error messages)
- Current plan and progress
- Unresolved questions

**What to drop**:
- Raw tool output already processed
- Exploration dead ends (unless they inform current approach)
- Verbose intermediate reasoning

#### Truncation
Drop oldest context when not valuable:

```python
def truncate_context(messages, max_tokens):
    # Always keep: system prompt, current task, recent turns
    protected = messages[:1] + messages[-3:]  # System + last 3

    # Score remaining by relevance
    scorable = messages[1:-3]
    scored = [(relevance_score(m), m) for m in scorable]
    scored.sort(reverse=True)

    # Keep highest-scored messages that fit
    budget = max_tokens - token_count(protected)
    kept = []
    for score, msg in scored:
        if token_count(msg) <= budget:
            kept.append(msg)
            budget -= token_count(msg)

    return messages[:1] + sorted(kept, key=lambda m: m.index) + messages[-3:]
```

#### Sliding Window
Keep only the N most recent turns:

```python
def sliding_window(messages, window_size=10):
    system = messages[:1]
    summary = create_summary(messages[1:-window_size])
    recent = messages[-window_size:]
    return system + [summary] + recent
```

---

### Working Memory Patterns

Working memory is structured state the agent maintains during a task.

#### Scratchpad Pattern
Maintain a running scratchpad of key information:

```markdown
## Agent Scratchpad

### Current Task
Implement user authentication for the REST API

### Key Files
- src/auth.py - Main auth module (needs JWT validation fix)
- src/models/user.py - User model with password hashing
- tests/test_auth.py - Auth tests (3 failing)

### Plan
1. [DONE] Read existing auth code
2. [DONE] Identify the bug (missing expiry check)
3. [IN PROGRESS] Fix token validation
4. [ ] Update error messages
5. [ ] Run tests

### Decisions
- Using PyJWT library (already in requirements)
- Token expiry: 1 hour (matches existing config)

### Blockers
- None currently
```

**Implementation**: Store as a message, update each turn, or persist to a file.

#### State Tracking Pattern
Track structured state for stateful workflows:

```python
agent_state = {
    "phase": "implement",       # orient | plan | implement | verify
    "files_modified": [
        "src/auth.py",
        "src/models/user.py"
    ],
    "tests_status": {
        "total": 12,
        "passing": 9,
        "failing": 3,
        "failing_tests": [
            "test_token_expiry",
            "test_invalid_token",
            "test_refresh_flow"
        ]
    },
    "remaining_tasks": [
        "Fix token expiry validation",
        "Update error message format"
    ],
    "decisions": [
        {"what": "Use PyJWT", "why": "Already in dependencies"}
    ]
}
```

#### Todo List Pattern
Simple but effective for tracking multi-step work:

```markdown
## TODO
- [x] Read auth module
- [x] Find the bug
- [ ] Fix validation logic in auth.py:42
- [ ] Update error messages to match test expectations
- [ ] Run test suite
- [ ] Commit changes
```

**When to use which**:
- **Scratchpad**: Exploratory tasks, debugging, investigation
- **State tracking**: Stateful workflows, multi-phase processes
- **Todo list**: Sequential task execution, checklists

---

### Long-Term Memory

For state that must persist beyond a single context window or session.

#### File-Based Memory

```python
# Write findings to a file for later retrieval
def persist_findings(filepath, findings):
    """Store structured findings as markdown."""
    content = f"""# Investigation Findings
## Date: {datetime.now().isoformat()}
## Task: {findings['task']}

### Key Discoveries
{chr(10).join(f'- {d}' for d in findings['discoveries'])}

### Decisions Made
{chr(10).join(f'- {d["what"]}: {d["why"]}' for d in findings['decisions'])}

### Files Modified
{chr(10).join(f'- {f}' for f in findings['files'])}

### Open Questions
{chr(10).join(f'- {q}' for q in findings['questions'])}
"""
    write_file(filepath, content)

# Retrieve in a later session
def load_findings(filepath):
    return read_file(filepath)
```

**Best for**: Investigation notes, architecture decisions, project context

#### Database-Backed Memory

```python
# Store structured memories with metadata
def store_memory(db, memory):
    db.execute("""
        INSERT INTO agent_memory (key, value, category, created_at, ttl)
        VALUES (?, ?, ?, ?, ?)
    """, (
        memory["key"],
        json.dumps(memory["value"]),
        memory["category"],  # "finding", "decision", "error"
        datetime.now(),
        memory.get("ttl")   # Optional expiry
    ))

# Query by category or recency
def recall(db, category=None, limit=10):
    query = "SELECT * FROM agent_memory"
    if category:
        query += f" WHERE category = '{category}'"
    query += f" ORDER BY created_at DESC LIMIT {limit}"
    return db.execute(query).fetchall()
```

**Best for**: Structured data, queryable history, multi-agent coordination

#### Embedding-Based Memory (RAG)

```python
# Store with embeddings for semantic retrieval
def store_with_embedding(memory_store, text, metadata):
    embedding = embed(text)  # Generate vector embedding
    memory_store.upsert(
        id=metadata["id"],
        embedding=embedding,
        text=text,
        metadata=metadata
    )

# Retrieve by semantic similarity
def semantic_recall(memory_store, query, top_k=5):
    query_embedding = embed(query)
    results = memory_store.search(query_embedding, top_k=top_k)
    return [r.text for r in results if r.score > 0.7]
```

**Best for**: Large knowledge bases, finding relevant past experiences, FAQ-style recall

---

### Memory Architecture for Multi-Turn Agents

```
                    +------------------+
                    |  Context Window  |
                    |  (Working Set)   |
                    +--------+---------+
                             |
              +--------------+--------------+
              |              |              |
     +--------v---+  +------v------+  +----v--------+
     | Scratchpad |  | Recent Turns|  | Tool Results|
     | (Updated   |  | (Sliding    |  | (Ephemeral, |
     |  each turn)|  |  window)    |  |  summarized)|
     +--------+---+  +------+------+  +----+--------+
              |              |              |
              +--------------+--------------+
                             |
                    +--------v---------+
                    |  Summarization   |
                    |  Layer           |
                    +--------+---------+
                             |
              +--------------+--------------+
              |              |              |
     +--------v---+  +------v------+  +----v--------+
     | File Store |  |  Database   |  |  Embeddings |
     | (.md notes)|  | (Structured)|  | (Semantic)  |
     +------------+  +-------------+  +-------------+
            Long-Term Memory Layer
```

**Flow**:
1. Each turn, update scratchpad with new information
2. Tool results enter context, get processed, key facts extracted
3. When context grows, summarize older turns
4. Important findings persist to long-term storage
5. On new sessions, load relevant long-term memory into context

---

### When to Persist vs Discard

| Information | Persist | Discard |
|-------------|---------|---------|
| Architecture decisions | Always | Never |
| Bug root causes | Always | Never |
| File paths and locations | Session-scoped | After session |
| Raw tool output | Never | After processing |
| Intermediate reasoning | Rarely | Usually |
| Error messages | If unresolved | After fix |
| Test results | Latest only | Superseded results |
| User preferences | Always | Never |

**Rule of thumb**: If you would need to re-discover this information, persist it. If you can re-derive it cheaply, discard it.

---

## Anti-Patterns

### Context Overflow
**Problem**: Loading everything into context without managing capacity.
**Symptom**: Agent responses degrade, start hallucinating, lose track of the task.
**Fix**: Monitor context usage. Summarize proactively at 60% capacity. Drop raw tool results after extracting key facts.

### Stale Memory
**Problem**: Acting on information that is no longer accurate.
**Symptom**: Editing files based on outdated reads. Assuming test status from 10 turns ago.
**Fix**: Re-read files before editing. Re-run tests before reporting status. Timestamp all cached information.

### Over-Summarization
**Problem**: Summarizing too aggressively, losing critical details.
**Symptom**: "I fixed the auth bug" but can't recall which file, which line, or what the fix was.
**Fix**: Summaries must preserve: file paths, line numbers, specific values, decision rationale. Summarize verbosity, not facts.

### Memory Without Retrieval
**Problem**: Persisting memories but never loading them.
**Symptom**: Repeating past investigations. Making decisions already made.
**Fix**: At session start, load relevant memories. Before investigating, check if findings already exist.

### Scratchpad Rot
**Problem**: Scratchpad becomes outdated or inconsistent with actual state.
**Symptom**: Scratchpad says "3 tests failing" but actually 1 was fixed.
**Fix**: Update scratchpad after every significant action. Periodically verify scratchpad against reality.

---

## Checklist

- [ ] Is context usage being monitored and managed?
- [ ] Are summaries preserving critical details (paths, numbers, decisions)?
- [ ] Is working memory (scratchpad/state) being updated each turn?
- [ ] Are long-lived findings persisted to files or database?
- [ ] Am I re-reading files before editing (not relying on stale reads)?
- [ ] Is there a retrieval strategy for previously persisted memories?
- [ ] Are raw tool results being discarded after processing?

---

## Related Skills

- `agentic-task-decomposition.md` - Context-bounded task sizing
- `agentic-tool-use.md` - Managing tool results in context
