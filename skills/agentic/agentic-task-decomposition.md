---
name: agentic-task-decomposition
description: Breaking complex tasks into executable agent steps with dependency management, failure recovery, and re-planning
---

# Agentic Task Decomposition

**Scope**: Goal decomposition, task graphs, atomic tasks, parallel execution, re-planning
**Lines**: ~280
**Last Updated**: 2026-02-02

## When to Use This Skill

Activate this skill when:
- Decomposing complex goals into subtasks for an LLM agent
- Deciding whether to decompose further or execute directly
- Building dependency graphs between agent steps
- Handling ambiguous or underspecified user requests
- Designing parallel vs sequential execution plans
- Implementing failure recovery and re-planning strategies
- Sizing tasks for LLM execution (context-bounded, verifiable)

## Core Concepts

### Decompose vs Execute Directly

Not every task needs decomposition. Use this decision framework:

```
Can I complete this in one tool call or one coherent response?
  YES -> Execute directly
  NO  -> Does it have independent sub-parts?
           YES -> Decompose and identify parallelism
           NO  -> Break into sequential steps
```

**Execute directly when**:
- Single file edit, single command, single query
- Task fits within working memory without state tracking
- No branching logic or conditional paths

**Decompose when**:
- Multiple files, tools, or systems involved
- Steps depend on results of prior steps
- Task requires verification between stages
- Failure in one part shouldn't abort everything

---

### Decomposition Strategies

#### Goal-to-Subgoal Decomposition

Start with the end state and work backward:

```python
# Goal: "Add user authentication to the API"
# Decompose by asking "what must be true for this to be done?"

task_graph = {
    "goal": "Add user authentication",
    "subgoals": [
        {
            "id": "auth-model",
            "task": "Create User model with password hashing",
            "depends_on": [],
            "verify": "User model exists with hash_password method"
        },
        {
            "id": "auth-routes",
            "task": "Create login/register endpoints",
            "depends_on": ["auth-model"],
            "verify": "POST /login and POST /register return tokens"
        },
        {
            "id": "auth-middleware",
            "task": "Create JWT middleware",
            "depends_on": ["auth-model"],
            "verify": "Protected routes reject unauthenticated requests"
        },
        {
            "id": "auth-tests",
            "task": "Write integration tests",
            "depends_on": ["auth-routes", "auth-middleware"],
            "verify": "All tests pass"
        }
    ]
}
```

#### Dependency Graph Approach

Model tasks as a directed acyclic graph (DAG):

```
auth-model ──┬── auth-routes ──┬── auth-tests
             └── auth-middleware ┘
```

**Rules**:
- No cycles (if A depends on B, B cannot depend on A)
- Tasks with no dependencies are immediately executable
- Tasks sharing no dependencies can run in parallel

#### Iterative Refinement

Start coarse, refine as you learn:

```
Round 1: "Build authentication" (too big)
Round 2: "Create model", "Create routes", "Create middleware", "Write tests"
Round 3: "Create model" -> "Define schema", "Add password hashing", "Add validation"
```

**Stop refining when** each task is:
- **Atomic**: Completable in one focused step
- **Verifiable**: Has a clear success condition
- **Context-bounded**: Fits in working memory with room for tool results

---

### Task Sizing for LLM Execution

A well-sized task for an LLM agent:

| Property | Good | Too Big | Too Small |
|----------|------|---------|-----------|
| **Scope** | Edit one function | Refactor entire module | Rename one variable |
| **Verification** | Run specific test | "Does it work?" | N/A |
| **Context** | Needs 2-3 file reads | Needs 20+ files loaded | Needs nothing |
| **Duration** | 1-5 tool calls | 50+ tool calls | 0 tool calls |

**Heuristic**: If a task requires more than 10 tool calls, it should probably be decomposed further. If it requires zero tool calls, it might be premature decomposition.

---

### Handling Ambiguity

When the user request is underspecified:

```python
def handle_ambiguity(task):
    # Strategy 1: Make assumptions explicit
    assumptions = identify_assumptions(task)
    if assumptions:
        # Ask for confirmation before proceeding
        return clarify(assumptions)

    # Strategy 2: Choose the most common interpretation
    # Document the choice so user can redirect
    interpretation = most_likely_interpretation(task)
    log(f"Interpreting '{task}' as: {interpretation}")

    # Strategy 3: Start with the unambiguous parts
    clear_subtasks = [t for t in decompose(task) if not t.ambiguous]
    return execute(clear_subtasks)  # Do what's clear, ask about the rest
```

**Priority order**:
1. Execute unambiguous parts immediately
2. State assumptions explicitly before acting on ambiguous parts
3. Ask for clarification only when ambiguity blocks all progress

---

### Parallel vs Sequential Execution

```python
# Identify parallelism from the dependency graph
def execution_plan(tasks):
    remaining = set(tasks)
    plan = []

    while remaining:
        # Find tasks whose dependencies are all completed
        ready = {t for t in remaining
                 if all(d not in remaining for d in t.depends_on)}

        if not ready:
            raise CyclicDependencyError()

        # All ready tasks can execute in parallel
        plan.append({"parallel": list(ready)})
        remaining -= ready

    return plan

# Result:
# [
#   {"parallel": ["auth-model"]},              # Wave 1
#   {"parallel": ["auth-routes", "auth-middleware"]},  # Wave 2
#   {"parallel": ["auth-tests"]}               # Wave 3
# ]
```

**When to parallelize**:
- Independent file reads/searches (always parallel)
- Independent tool calls with no shared state
- Tests for different components

**When to keep sequential**:
- Write depends on read result
- Later step uses output of earlier step
- Order matters for correctness (migrations, deployments)

---

### Failure Recovery and Re-Planning

```python
def execute_with_recovery(plan):
    completed = []
    for wave in plan:
        results = execute_parallel(wave["parallel"])

        for task, result in results:
            if result.failed:
                # Strategy 1: Retry with more context
                if result.error_type == "insufficient_context":
                    retry = enrich_context(task)
                    result = execute(retry)

                # Strategy 2: Decompose the failing task further
                if result.error_type == "too_complex":
                    subtasks = decompose_further(task)
                    result = execute_with_recovery(subtasks)

                # Strategy 3: Re-plan from current state
                if result.error_type == "assumption_violated":
                    new_plan = replan(
                        original_goal=plan.goal,
                        completed=completed,
                        new_information=result.error
                    )
                    return execute_with_recovery(new_plan)

                # Strategy 4: Skip and continue
                if task.optional:
                    log(f"Skipping optional task: {task}")
                    continue

                # Strategy 5: Abort with clear status
                raise AgentError(
                    completed=completed,
                    failed=task,
                    remaining=remaining_tasks(plan, completed)
                )

            completed.append(task)

    return completed
```

**Recovery priority**:
1. Retry with more context (cheapest)
2. Decompose further (task was too big)
3. Re-plan (assumptions were wrong)
4. Skip if optional
5. Abort with clear status report

---

## Anti-Patterns

### Over-Decomposition
**Problem**: Breaking simple tasks into dozens of micro-steps.
**Symptom**: More time planning than executing. Tasks like "open file", "read line 5", "change word".
**Fix**: If a task takes fewer tool calls to execute than to plan, just do it.

### Under-Decomposition
**Problem**: Attempting complex multi-file changes in one shot.
**Symptom**: Losing track of state, incomplete changes, forgetting steps.
**Fix**: If you catch yourself re-reading the same context, the task needs decomposition.

### Rigid Plans
**Problem**: Following the original plan even when early results change the situation.
**Symptom**: Completing tasks that are no longer relevant, ignoring new information.
**Fix**: Check assumptions after each step. Re-plan when the situation changes.

### Dependency Blindness
**Problem**: Executing tasks in parallel when they actually share state.
**Symptom**: Race conditions, conflicting edits, inconsistent state.
**Fix**: Explicitly list what each task reads and writes. Overlap means sequential.

---

## Checklist

- [ ] Can I execute this directly without decomposition?
- [ ] Are all subtasks atomic, verifiable, and context-bounded?
- [ ] Is the dependency graph a DAG (no cycles)?
- [ ] Have I identified parallel execution opportunities?
- [ ] Does each task have a clear success condition?
- [ ] Is there a recovery strategy for likely failure modes?
- [ ] Have I made ambiguous assumptions explicit?

---

## Related Skills

- `agentic-tool-use.md` - Executing decomposed tasks with tools
- `agentic-memory.md` - Managing context across task steps
