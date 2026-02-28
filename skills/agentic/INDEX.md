---
name: agentic-index
description: Index of Agentic Workflow Skills
---

# Agentic Workflow Skills

Comprehensive skills for building autonomous AI agents, managing context, and orchestrating multi-step tool-use workflows.

## Category Overview

**Total Skills**: 3
**Focus**: Task decomposition, tool use patterns, context/memory management for LLM agents
**Use Cases**: AI agent development, autonomous workflows, tool-calling systems, multi-step reasoning pipelines

## Skills in This Category

### agentic-task-decomposition.md
**Description**: Breaking complex tasks into executable agent steps
**Lines**: ~280
**Use When**:
- Decomposing complex goals into subtasks for an LLM agent
- Deciding whether to decompose further or execute directly
- Building dependency graphs between agent steps
- Handling ambiguous or underspecified user requests
- Designing parallel vs sequential execution plans
- Implementing failure recovery and re-planning strategies

**Key Concepts**: Goal decomposition, task graphs, atomic tasks, iterative refinement, re-planning, parallel execution

---

### agentic-tool-use.md
**Description**: Effective LLM tool calling patterns and multi-tool workflows
**Lines**: ~300
**Use When**:
- Implementing function calling / tool use in LLM agents
- Designing tool schemas and structured outputs
- Composing multi-tool workflows (parallel and sequential)
- Handling tool call errors, retries, and fallbacks
- Selecting the right tool for a given subtask
- Avoiding common tool-use anti-patterns

**Key Concepts**: Function calling, structured output, parallel tool use, error handling, tool selection heuristics, multi-tool composition

---

### agentic-memory.md
**Description**: Context window management, working memory, and long-term persistence
**Lines**: ~260
**Use When**:
- Managing context window limits in long-running agents
- Implementing working memory (scratchpads, state tracking)
- Designing long-term memory (file-based, database, embeddings)
- Deciding when to summarize, truncate, or persist context
- Building multi-turn conversation architectures
- Preventing context overflow and stale memory issues

**Key Concepts**: Context window management, summarization, sliding window, scratchpad patterns, file-based memory, embedding retrieval

---

## Common Workflows

### Building an Autonomous Agent
**Goal**: Design a complete agent loop from task intake to completion

**Sequence**:
1. `agentic-task-decomposition.md` - Parse goals, build task graph
2. `agentic-tool-use.md` - Implement tool-calling execution layer
3. `agentic-memory.md` - Add context management for long tasks

**Example**: Code generation agent that reads specs, writes code, runs tests, iterates

---

### Adding Tool Use to an Existing Agent
**Goal**: Integrate structured tool calling into an LLM pipeline

**Sequence**:
1. `agentic-tool-use.md` - Design tool schemas, calling patterns
2. `agentic-task-decomposition.md` - Break multi-tool tasks into steps
3. `agentic-memory.md` - Track tool results across turns

**Example**: Customer support agent gaining access to databases and APIs

---

### Long-Running Agent Sessions
**Goal**: Handle tasks that exceed a single context window

**Sequence**:
1. `agentic-memory.md` - Implement context management strategy
2. `agentic-task-decomposition.md` - Chunk work into context-bounded steps
3. `agentic-tool-use.md` - Use file I/O tools for persistence

**Example**: Multi-hour coding session with iterative refinement

---

### Task Planning and Execution
**Goal**: Plan, execute, and recover from failures

**Sequence**:
1. `agentic-task-decomposition.md` - Decompose and plan
2. `agentic-tool-use.md` - Execute plan with tools
3. `agentic-task-decomposition.md` - Re-plan on failure

**Example**: Migration agent that plans schema changes, executes them, verifies results

---

## Skill Combinations

### With API Skills (`discover-api`)
- Agent-driven API testing and exploration
- Automated API client generation
- Multi-endpoint orchestration workflows

**Common combos**:
- `agentic-tool-use.md` + `api/rest-api-design.md`
- `agentic-task-decomposition.md` + `api/api-error-handling.md`

---

### With Testing Skills (`discover-testing`)
- Autonomous test generation agents
- Test-driven agent development
- Automated test execution and reporting

**Common combos**:
- `agentic-task-decomposition.md` + `testing/test-strategy.md`
- `agentic-tool-use.md` + `testing/integration-testing.md`

---

### With Database Skills (`discover-database`)
- Database-backed agent memory
- Autonomous data migration agents
- Query generation and optimization agents

**Common combos**:
- `agentic-memory.md` + `database/postgres-schema-design.md`
- `agentic-tool-use.md` + `database/sql-query-patterns.md`

---

### With Infrastructure Skills (`discover-infra`, `discover-infra`)
- Agent deployment and scaling
- Infrastructure-as-code generation agents
- Automated deployment pipelines

**Common combos**:
- `agentic-task-decomposition.md` + `infrastructure/infrastructure-security.md`
- `agentic-memory.md` + `infrastructure/cost-optimization.md`

---

## Quick Selection Guide

**Start with task decomposition when**:
- You have a complex goal that needs breaking down
- Tasks have dependencies or ordering constraints
- You need to handle ambiguous requirements
- Building a planning layer for an agent

**Start with tool use when**:
- Implementing the execution layer of an agent
- Adding new tools or capabilities
- Debugging tool call failures
- Optimizing multi-tool workflows

**Start with memory when**:
- Agent sessions are hitting context limits
- Need to persist state across turns or sessions
- Building multi-turn conversational agents
- Implementing retrieval-augmented generation

---

## Loading Skills

All skills are available in the `skills/agentic/` directory:

Read agentic-task-decomposition.md
Read agentic-tool-use.md
Read agentic-memory.md


**Pro tip**: Start with task decomposition to plan, then tool use to execute, then memory to scale beyond a single context window.

---

**Related Categories**:
- `discover-api` - API design for agent-accessible services
- `discover-testing` - Testing agent behaviors
- `discover-database` - Persistent storage for agent memory
- `discover-infra` - Deploying and scaling agent systems
- `discover-infra` - Serverless agent execution environments
