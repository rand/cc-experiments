---
name: dspy-agents
description: Building intelligent agents with DSPy using ReAct, tools, memory, and advanced agent patterns
---

# DSPy Agents

**Scope**: ReAct agents, tool creation, memory systems, agent loops, multi-step reasoning
**Lines**: ~480
**Last Updated**: 2025-10-30

## When to Use This Skill

Activate this skill when:
- Building autonomous agents that can use tools and take actions
- Implementing multi-step reasoning workflows
- Creating agents that interact with external systems (APIs, databases, search)
- Designing agentic RAG systems with dynamic retrieval
- Building customer service bots or research assistants
- Implementing agents with memory and state management

## Core Concepts

### What are Agents?

**Definition**: Autonomous systems that observe, reason, act, and learn iteratively

**Purpose**:
- **Autonomy**: Agents make decisions and take actions independently
- **Tool use**: Access external information and capabilities
- **Multi-step reasoning**: Break down complex tasks into steps
- **Adaptability**: Learn from observations and adjust behavior

**Key insight**: Agents are modules that loop through Thought → Action → Observation cycles

### ReAct Pattern

**Re**asoning + **Act**ing framework:
1. **Thought**: Agent reasons about what to do next
2. **Action**: Agent selects and executes a tool
3. **Observation**: Agent sees result of action
4. **Repeat**: Continue until task is complete

**When to use ReAct**:
- Tasks requiring external information
- Multi-step problem solving
- Dynamic decision making
- Tool orchestration

### Tools in DSPy

**Tool**: Python function that an agent can call

**Characteristics**:
- Clear function signature
- Docstring describing purpose
- Returns string or structured data
- Side-effect free (when possible)

---

## Patterns

### Pattern 1: Basic ReAct Agent

```python
import dspy

# Configure LM
lm = dspy.LM("openai/gpt-4o-mini")
dspy.configure(lm=lm)

# Define tools
def search_web(query: str) -> str:
    """Search the web for information."""
    # Implement actual search (e.g., Google, Bing)
    return f"Search results for: {query}"

def calculate(expression: str) -> str:
    """Evaluate mathematical expressions."""
    try:
        result = eval(expression)  # Use safely in production!
        return str(result)
    except Exception as e:
        return f"Error: {e}"

# Define agent signature
class AgentSignature(dspy.Signature):
    """Answer questions using available tools."""
    question = dspy.InputField()
    answer = dspy.OutputField()

# Create ReAct agent
agent = dspy.ReAct(
    AgentSignature,
    tools=[search_web, calculate],
    max_iters=5,  # Maximum thought-action cycles
)

# Use agent
result = agent(question="What is 15% of the population of Tokyo?")
print(result.answer)
```

**How it works**:
1. Agent reads question
2. Thinks about what information is needed
3. Decides to use `search_web("Tokyo population")`
4. Observes result: "14 million"
5. Thinks about calculation needed
6. Decides to use `calculate("0.15 * 14000000")`
7. Observes result: "2100000"
8. Generates final answer: "2.1 million"

### Pattern 2: Agent with Custom Tool Registry

```python
import dspy
from typing import Callable, Dict

class ToolRegistry:
    """Manage tools available to agent."""

    def __init__(self):
        self.tools: Dict[str, Callable] = {}

    def register(self, name: str = None):
        """Decorator to register tool."""
        def decorator(func):
            tool_name = name or func.__name__
            self.tools[tool_name] = func
            return func
        return decorator

    def get_tools(self):
        """Get list of registered tools."""
        return list(self.tools.values())

# Create registry
registry = ToolRegistry()

# Register tools
@registry.register()
def search_docs(query: str) -> str:
    """Search internal documentation."""
    # Implement doc search
    return f"Documentation results for: {query}"

@registry.register()
def query_database(sql: str) -> str:
    """Query database for information."""
    # Implement safe SQL execution
    return f"Query results for: {sql}"

@registry.register()
def send_email(to: str, subject: str, body: str) -> str:
    """Send email to user."""
    # Implement email sending
    return f"Email sent to {to}"

# Create agent with registered tools
agent = dspy.ReAct(
    "task -> result",
    tools=registry.get_tools(),
    max_iters=10,
)

# Use agent
result = agent(task="Find the latest sales data and email it to john@example.com")
print(result.result)
```

**Benefits**:
- Centralized tool management
- Easy to add/remove tools
- Tool discovery and documentation
- Dependency injection

### Pattern 3: Agent with Memory

```python
import dspy

class MemoryAgent(dspy.Module):
    """Agent with conversation memory."""

    def __init__(self, tools, max_memory=5):
        super().__init__()
        self.tools = tools
        self.max_memory = max_memory
        self.memory = []  # Store recent interactions

        self.agent = dspy.ReAct(
            "context, question -> answer",
            tools=tools,
            max_iters=5,
        )

    def forward(self, question):
        # Build context from memory
        context_parts = []
        for mem in self.memory[-self.max_memory:]:
            context_parts.append(f"Q: {mem['question']}\nA: {mem['answer']}")

        context = "\n\n".join(context_parts) if context_parts else "No previous context."

        # Run agent with context
        result = self.agent(context=context, question=question)

        # Store in memory
        self.memory.append({
            'question': question,
            'answer': result.answer,
        })

        return result

    def clear_memory(self):
        """Clear conversation memory."""
        self.memory = []

# Define tools
def get_user_info(user_id: str) -> str:
    """Get user information from database."""
    return f"User {user_id}: John Doe, Premium account"

def get_order_status(order_id: str) -> str:
    """Check order status."""
    return f"Order {order_id}: Shipped, arriving tomorrow"

# Create memory agent
agent = MemoryAgent(tools=[get_user_info, get_order_status], max_memory=3)

# Multi-turn conversation
print(agent(question="What's the status of user 12345?").answer)
print(agent(question="Do they have any pending orders?").answer)
print(agent(question="When will their order arrive?").answer)
# Agent remembers previous context!
```

**When to use**:
- Conversational agents
- Customer service bots
- Research assistants
- Any multi-turn interaction

### Pattern 4: Agentic RAG

```python
import dspy

class AgenticRAG(dspy.Module):
    """RAG system where agent decides when to retrieve."""

    def __init__(self):
        super().__init__()

        # Agent decides if/what to retrieve
        self.planner = dspy.ChainOfThought(
            "question -> needs_retrieval: bool, search_queries: list[str]"
        )

        # Retrieval tool
        self.retrieve = dspy.Retrieve(k=5)

        # Answer generation
        self.generate = dspy.ChainOfThought("question, context -> answer")

    def forward(self, question):
        # Plan retrieval strategy
        plan = self.planner(question=question)

        # Parse needs_retrieval
        needs_retrieval = str(plan.needs_retrieval).lower() in ['true', 'yes', '1']

        if needs_retrieval and hasattr(plan, 'search_queries'):
            # Parse queries (may be comma-separated string)
            if isinstance(plan.search_queries, str):
                queries = [q.strip() for q in plan.search_queries.split(',')]
            else:
                queries = plan.search_queries

            # Retrieve for each query
            all_passages = []
            for query in queries[:3]:  # Limit to 3 queries
                passages = self.retrieve(query).passages
                all_passages.extend(passages)

            # Deduplicate passages
            unique_passages = list(dict.fromkeys(all_passages))
            context = "\n\n".join(unique_passages[:5])
        else:
            # No retrieval needed
            context = "No additional context required."

        # Generate answer
        return self.generate(question=question, context=context)

# Use agentic RAG
lm = dspy.LM("openai/gpt-4o-mini")
dspy.configure(lm=lm)

rag = AgenticRAG()
result = rag(question="What is the capital of France?")
# Agent realizes no retrieval needed for this simple question
print(result.answer)

result = rag(question="What are the latest features in DSPy 2025?")
# Agent decides to retrieve current information
print(result.answer)
```

**Benefits**:
- Retrieves only when necessary
- Generates dynamic search queries
- More efficient than always retrieving
- Better for mixed query types

### Pattern 5: Tool-Building Agent

```python
import dspy

class ToolBuilder(dspy.Module):
    """Agent that can create new tools dynamically."""

    def __init__(self):
        super().__init__()

        # Generate Python function code
        self.code_gen = dspy.ChainOfThought(
            "tool_description -> function_code: str, function_name: str"
        )

    def create_tool(self, description):
        """Generate a new tool function."""
        result = self.code_gen(tool_description=description)

        # Parse generated code
        function_code = result.function_code
        function_name = result.function_name

        # Execute code to define function (DANGER: only for trusted LLMs!)
        namespace = {}
        try:
            exec(function_code, namespace)
            return namespace.get(function_name)
        except Exception as e:
            print(f"Error creating tool: {e}")
            return None

class MetaAgent(dspy.Module):
    """Agent that can create tools as needed."""

    def __init__(self):
        super().__init__()
        self.tool_builder = ToolBuilder()
        self.available_tools = []

        # Main agent loop
        self.agent = dspy.ReAct(
            "task, available_tools_description -> result",
            tools=[],  # Start with no tools
            max_iters=10,
        )

    def forward(self, task):
        # Describe available tools
        tool_desc = ", ".join([
            f.__name__ + ": " + (f.__doc__ or "No description")
            for f in self.available_tools
        ]) if self.available_tools else "No tools available yet."

        # Try to complete task
        try:
            return self.agent(
                task=task,
                available_tools_description=tool_desc
            )
        except Exception as e:
            # If agent needs a tool it doesn't have, create it
            print(f"Agent needs new capability: {e}")

            # Generate new tool (simplified - production needs better error handling)
            new_tool = self.tool_builder.create_tool(
                f"Tool to help with: {task}"
            )

            if new_tool:
                self.available_tools.append(new_tool)
                self.agent.tools.append(new_tool)

                # Retry task
                return self.agent(
                    task=task,
                    available_tools_description=tool_desc
                )

# Use meta-agent (CAUTION: Educational example, not production-safe)
# meta_agent = MetaAgent()
# result = meta_agent(task="Convert 100 USD to EUR")
```

**Caution**: Code generation and execution is dangerous. Only use with:
- Trusted LLMs
- Sandboxed execution environments
- Strict validation
- Security review

### Pattern 6: Error-Handling Agent

```python
import dspy

class RobustAgent(dspy.Module):
    """Agent with error handling and retry logic."""

    def __init__(self, tools, max_retries=3):
        super().__init__()
        self.max_retries = max_retries

        # Wrap tools with error handling
        self.safe_tools = [self._wrap_tool(t) for t in tools]

        self.agent = dspy.ReAct(
            "question -> answer",
            tools=self.safe_tools,
            max_iters=10,
        )

    def _wrap_tool(self, tool):
        """Wrap tool with error handling."""
        def safe_tool(*args, **kwargs):
            try:
                result = tool(*args, **kwargs)
                return f"Success: {result}"
            except Exception as e:
                return f"Error: Tool '{tool.__name__}' failed with: {str(e)}"

        # Preserve metadata
        safe_tool.__name__ = tool.__name__
        safe_tool.__doc__ = tool.__doc__
        return safe_tool

    def forward(self, question):
        for attempt in range(self.max_retries):
            try:
                result = self.agent(question=question)

                # Validate result
                if result.answer and len(result.answer.strip()) > 0:
                    return result

                print(f"Attempt {attempt + 1}: Empty answer, retrying...")

            except Exception as e:
                if attempt == self.max_retries - 1:
                    # Last attempt failed
                    return dspy.Prediction(
                        answer=f"Failed to answer after {self.max_retries} attempts. Last error: {e}"
                    )

                print(f"Attempt {attempt + 1} failed: {e}, retrying...")

        return dspy.Prediction(answer="Failed to generate answer.")

# Define flaky tools
def unreliable_api(query: str) -> str:
    """Simulate unreliable API."""
    import random
    if random.random() < 0.3:
        raise Exception("API timeout")
    return f"API result for: {query}"

# Create robust agent
agent = RobustAgent(tools=[unreliable_api], max_retries=3)
result = agent(question="Query the API for data")
print(result.answer)
```

**When to use**:
- Production agents with external dependencies
- Unreliable tools (network, APIs)
- Critical applications requiring reliability

### Pattern 7: Streaming Agent

```python
import dspy
from typing import Iterator

class StreamingAgent(dspy.Module):
    """Agent that streams responses in real-time."""

    def __init__(self, tools):
        super().__init__()
        self.tools = tools

        # For streaming, we need custom implementation
        self.think = dspy.ChainOfThought("context, question -> thought")
        self.act = dspy.Predict("thought, tools -> tool_name, tool_args")
        self.answer = dspy.ChainOfThought("context, observations -> answer")

    def forward_stream(self, question) -> Iterator[str]:
        """Execute agent with streaming output."""
        context = f"Question: {question}\n\n"
        observations = []

        yield f"[AGENT START] Processing: {question}\n\n"

        for iteration in range(5):  # Max iterations
            # Think
            yield f"[THOUGHT {iteration+1}] "
            thought_result = self.think(context=context, question=question)
            yield f"{thought_result.thought}\n\n"

            # Decide action
            action_result = self.act(
                thought=thought_result.thought,
                tools=", ".join(t.__name__ for t in self.tools)
            )

            tool_name = action_result.tool_name.strip()

            # Check if agent wants to answer
            if tool_name.lower() in ['answer', 'done', 'finish']:
                yield "[DECISION] Ready to answer\n\n"
                break

            # Execute tool
            yield f"[ACTION {iteration+1}] Using {tool_name}\n"

            tool = next((t for t in self.tools if t.__name__ == tool_name), None)
            if tool:
                try:
                    # Parse tool_args (simplified)
                    result = tool(action_result.tool_args)
                    observation = f"{tool_name}: {result}"
                    yield f"[OBSERVATION {iteration+1}] {observation}\n\n"

                    observations.append(observation)
                    context += f"\nObservation: {observation}"
                except Exception as e:
                    error_msg = f"Error executing {tool_name}: {e}"
                    yield f"[ERROR] {error_msg}\n\n"
                    observations.append(error_msg)
            else:
                yield f"[ERROR] Tool '{tool_name}' not found\n\n"

        # Generate final answer
        yield "[ANSWER] "
        all_observations = "\n".join(observations)
        answer_result = self.answer(context=context, observations=all_observations)
        yield f"{answer_result.answer}\n"

        yield "[AGENT COMPLETE]\n"

# Define tools
def search(query: str) -> str:
    """Search for information."""
    return f"Search results: Information about {query}"

# Create streaming agent
agent = StreamingAgent(tools=[search])

# Stream agent execution
for chunk in agent.forward_stream("What is DSPy?"):
    print(chunk, end='', flush=True)
```

**Benefits**:
- Real-time feedback to users
- Better UX for long-running agents
- Visibility into agent reasoning
- Early error detection

### Pattern 8: Agent with State Machine

```python
import dspy
from enum import Enum

class AgentState(Enum):
    INIT = "initializing"
    PLANNING = "planning"
    EXECUTING = "executing"
    REVIEWING = "reviewing"
    COMPLETE = "complete"
    ERROR = "error"

class StatefulAgent(dspy.Module):
    """Agent with explicit state machine."""

    def __init__(self, tools):
        super().__init__()
        self.tools = tools
        self.state = AgentState.INIT

        # State-specific modules
        self.planner = dspy.ChainOfThought("task -> plan: list[str]")
        self.executor = dspy.ReAct(
            "step, tools_available -> result",
            tools=tools,
            max_iters=3
        )
        self.reviewer = dspy.ChainOfThought(
            "task, results -> is_complete: bool, next_action"
        )

    def forward(self, task):
        self.state = AgentState.PLANNING
        results = []

        # Planning phase
        plan_result = self.planner(task=task)

        # Parse plan
        if isinstance(plan_result.plan, str):
            steps = [s.strip() for s in plan_result.plan.split(',')]
        else:
            steps = plan_result.plan

        # Execution phase
        self.state = AgentState.EXECUTING

        for i, step in enumerate(steps[:5]):  # Limit steps
            tools_desc = ", ".join(t.__name__ for t in self.tools)
            step_result = self.executor(step=step, tools_available=tools_desc)
            results.append(f"Step {i+1}: {step_result.result}")

        # Review phase
        self.state = AgentState.REVIEWING
        all_results = "\n".join(results)
        review = self.reviewer(task=task, results=all_results)

        # Check completion
        is_complete = str(review.is_complete).lower() in ['true', 'yes', '1']

        if is_complete:
            self.state = AgentState.COMPLETE
            return dspy.Prediction(
                answer=all_results,
                state=self.state.value,
                steps_completed=len(steps)
            )
        else:
            # Would retry or handle incomplete state
            self.state = AgentState.ERROR
            return dspy.Prediction(
                answer=f"Task incomplete. Next: {review.next_action}",
                state=self.state.value,
                steps_completed=len(steps)
            )

# Define tools
def web_search(query: str) -> str:
    """Search the web."""
    return f"Web results for: {query}"

def calculator(expr: str) -> str:
    """Calculate expression."""
    try:
        return str(eval(expr))
    except Exception as e:
        return f"Error: {e}"

# Create stateful agent
agent = StatefulAgent(tools=[web_search, calculator])
result = agent(task="Find the population of Tokyo and calculate 10% of it")

print(f"State: {result.state}")
print(f"Answer: {result.answer}")
print(f"Steps: {result.steps_completed}")
```

**Benefits**:
- Explicit state transitions
- Better debugging and monitoring
- Clear execution phases
- Resumable workflows

---

## Quick Reference

### Basic ReAct Agent Setup

```python
import dspy

# Define tools
def tool1(arg: str) -> str:
    """Tool description."""
    return result

def tool2(arg: str) -> str:
    """Tool description."""
    return result

# Create agent
agent = dspy.ReAct(
    "question -> answer",
    tools=[tool1, tool2],
    max_iters=5,
)

# Use agent
result = agent(question="Your question")
```

### Tool Requirements

```python
# Good tool signature
def my_tool(query: str) -> str:
    """
    Clear description of what the tool does.

    Args:
        query: Description of the parameter

    Returns:
        Description of the return value
    """
    # Implementation
    return result
```

### Agent Best Practices

```
✅ DO: Write clear tool docstrings
✅ DO: Handle tool errors gracefully
✅ DO: Limit max_iters to prevent infinite loops
✅ DO: Provide context/memory when needed
✅ DO: Validate tool outputs
✅ DO: Log agent reasoning for debugging

❌ DON'T: Create tools with side effects (when avoidable)
❌ DON'T: Use unsafe code execution
❌ DON'T: Ignore error handling
❌ DON'T: Create too many similar tools (confuses agent)
❌ DON'T: Forget to test tools independently
```

### Common Tool Patterns

```python
# Information retrieval
def search_docs(query: str) -> str:
    """Search documentation."""
    pass

# Computation
def calculate(expression: str) -> str:
    """Evaluate math expression."""
    pass

# Data access
def query_db(query: str) -> str:
    """Query database."""
    pass

# External API
def call_api(endpoint: str, params: dict) -> str:
    """Call external API."""
    pass

# File operations
def read_file(path: str) -> str:
    """Read file contents."""
    pass
```

---

## Anti-Patterns

❌ **Too many tools**: Agent gets confused
```python
# Bad - 50 tools
agent = dspy.ReAct(sig, tools=list_of_50_tools)
```
✅ Curate essential tools:
```python
# Good - 5-10 focused tools
agent = dspy.ReAct(sig, tools=[search, calc, db, api])
```

❌ **Vague tool descriptions**: Agent misuses tools
```python
# Bad
def tool(x):
    """Does stuff."""
    pass
```
✅ Clear, specific descriptions:
```python
# Good
def search_products(query: str) -> str:
    """Search product database by name or SKU. Returns JSON list of matching products."""
    pass
```

❌ **No error handling**: Agent crashes
```python
# Bad
def api_call(url):
    return requests.get(url).json()  # May fail!
```
✅ Handle errors:
```python
# Good
def api_call(url: str) -> str:
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return f"Error: {e}"
```

❌ **Unbounded loops**: Agent runs forever
```python
# Bad
agent = dspy.ReAct(sig, tools=tools, max_iters=1000)
```
✅ Reasonable limits:
```python
# Good
agent = dspy.ReAct(sig, tools=tools, max_iters=5)
```

---

## Related Skills

- `dspy-modules.md` - Understanding ReAct module basics
- `dspy-multi-agent.md` - Multi-agent systems and orchestration
- `dspy-production.md` - Deploying agents to production
- `dspy-testing.md` - Testing agent behavior
- `dspy-debugging.md` - Debugging agent reasoning
- `dspy-rag.md` - Agentic RAG patterns
- `dspy-optimizers.md` - Optimizing agent prompts

---

**Last Updated**: 2025-10-30
**Format Version**: 1.0 (Atomic)
