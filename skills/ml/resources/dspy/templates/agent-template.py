"""
DSPy Agent Template

Template for building ReAct-style agents with tool use, memory, and
error recovery.
"""

import dspy
from typing import List, Dict, Any, Optional, Callable
import json


# ============================================================================
# TOOL DEFINITIONS
# ============================================================================

class Tool:
    """Base class for agent tools.

    Example:
        ```python
        class CalculatorTool(Tool):
            name = "calculator"
            description = "Performs arithmetic operations"

            def execute(self, operation: str) -> str:
                return str(eval(operation))
        ```
    """

    name: str = "tool"
    description: str = "A tool"
    parameters: Dict[str, Any] = {}

    def execute(self, **kwargs) -> str:
        """Execute tool with given parameters.

        Args:
            **kwargs: Tool-specific parameters

        Returns:
            Tool execution result as string

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Tool must implement execute()")

    def to_dict(self) -> Dict[str, Any]:
        """Convert tool to dictionary for prompting."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }


# ============================================================================
# EXAMPLE TOOLS
# ============================================================================

class SearchTool(Tool):
    """Tool for searching a knowledge base."""

    name = "search"
    description = "Search for information in the knowledge base"
    parameters = {
        "query": {"type": "string", "description": "Search query"}
    }

    def __init__(self, retriever: Optional[dspy.Retrieve] = None):
        """Initialize with optional retriever.

        Args:
            retriever: DSPy retriever module
        """
        self.retriever = retriever or dspy.Retrieve(k=3)

    def execute(self, query: str) -> str:
        """Execute search.

        Args:
            query: Search query

        Returns:
            Search results as formatted string
        """
        prediction = self.retriever(query)
        passages = prediction.passages

        results = []
        for i, passage in enumerate(passages, 1):
            results.append(f"{i}. {passage[:200]}...")

        return "\n".join(results)


class CalculatorTool(Tool):
    """Tool for mathematical calculations."""

    name = "calculator"
    description = "Perform arithmetic calculations"
    parameters = {
        "expression": {"type": "string", "description": "Math expression to evaluate"}
    }

    def execute(self, expression: str) -> str:
        """Execute calculation.

        Args:
            expression: Math expression (e.g., "2 + 2")

        Returns:
            Calculation result
        """
        try:
            # Safe eval for basic arithmetic
            result = eval(expression, {"__builtins__": {}}, {})
            return str(result)
        except Exception as e:
            return f"Error: {str(e)}"


class PythonTool(Tool):
    """Tool for executing Python code."""

    name = "python"
    description = "Execute Python code"
    parameters = {
        "code": {"type": "string", "description": "Python code to execute"}
    }

    def execute(self, code: str) -> str:
        """Execute Python code.

        Args:
            code: Python code string

        Returns:
            Execution output or error
        """
        try:
            # Capture output
            from io import StringIO
            import sys

            old_stdout = sys.stdout
            sys.stdout = StringIO()

            exec(code)

            output = sys.stdout.getvalue()
            sys.stdout = old_stdout

            return output or "Code executed successfully"
        except Exception as e:
            return f"Error: {str(e)}"


# ============================================================================
# AGENT SIGNATURES
# ============================================================================

class ThinkSignature(dspy.Signature):
    """Signature for agent thinking step."""

    goal: str = dspy.InputField(desc="The goal to achieve")
    context: str = dspy.InputField(desc="Current context and observations")
    available_tools: str = dspy.InputField(desc="Available tools")

    thought: str = dspy.OutputField(desc="Your reasoning about what to do next")
    action: str = dspy.OutputField(desc="Tool to use (or 'finish' if done)")
    action_input: str = dspy.OutputField(desc="Input for the tool")


class AnswerSignature(dspy.Signature):
    """Signature for final answer generation."""

    goal: str = dspy.InputField(desc="The original goal")
    trajectory: str = dspy.InputField(desc="All thoughts and observations")

    answer: str = dspy.OutputField(desc="Final answer to the goal")
    confidence: str = dspy.OutputField(desc="Confidence level (high/medium/low)")


# ============================================================================
# REACT AGENT
# ============================================================================

class ReActAgent(dspy.Module):
    """ReAct-style agent with tool use.

    Implements the ReAct (Reasoning + Acting) pattern for agents that can
    use tools to accomplish goals.

    Args:
        tools: List of available tools
        max_steps: Maximum reasoning steps
        verbose: Whether to print intermediate steps

    Example:
        ```python
        agent = ReActAgent(
            tools=[SearchTool(), CalculatorTool()],
            max_steps=5
        )

        result = agent(goal="What is the square root of 144?")
        print(result.answer)
        ```

    Attributes:
        tools: Dictionary of available tools
        think: Predictor for reasoning steps
        answer: Predictor for final answer
    """

    def __init__(
        self,
        tools: List[Tool],
        max_steps: int = 10,
        verbose: bool = False
    ):
        """Initialize ReAct agent.

        Args:
            tools: List of Tool instances
            max_steps: Maximum reasoning iterations
            verbose: Print intermediate steps
        """
        super().__init__()

        # Register tools
        self.tools: Dict[str, Tool] = {tool.name: tool for tool in tools}
        self.max_steps = max_steps
        self.verbose = verbose

        # Initialize predictors
        self.think = dspy.ChainOfThought(ThinkSignature)
        self.answer = dspy.ChainOfThought(AnswerSignature)

    def forward(self, goal: str) -> dspy.Prediction:
        """Execute agent to accomplish goal.

        Args:
            goal: The goal/question for the agent

        Returns:
            Prediction with answer and trajectory

        Example:
            ```python
            result = agent(goal="Find the capital of France")
            print(result.answer)
            print(result.trajectory)  # Full reasoning trace
            ```
        """
        trajectory = []
        context = "Starting task."

        for step in range(self.max_steps):
            # Think about next action
            thought_pred = self.think(
                goal=goal,
                context=context,
                available_tools=self._format_tools()
            )

            thought = thought_pred.thought
            action = thought_pred.action.strip().lower()
            action_input = thought_pred.action_input

            trajectory.append({
                "step": step + 1,
                "thought": thought,
                "action": action,
                "action_input": action_input
            })

            if self.verbose:
                print(f"\n--- Step {step + 1} ---")
                print(f"Thought: {thought}")
                print(f"Action: {action}")
                print(f"Input: {action_input}")

            # Check if done
            if action == "finish":
                break

            # Execute tool
            observation = self._execute_tool(action, action_input)
            trajectory[-1]["observation"] = observation

            if self.verbose:
                print(f"Observation: {observation}")

            # Update context
            context = f"Action: {action}({action_input})\nObservation: {observation}"

        # Generate final answer
        trajectory_str = self._format_trajectory(trajectory)
        answer_pred = self.answer(goal=goal, trajectory=trajectory_str)

        # Validate answer
        dspy.Assert(
            len(answer_pred.answer) > 0,
            "Answer cannot be empty"
        )

        dspy.Suggest(
            answer_pred.confidence in ["high", "medium", "low"],
            "Confidence should be high/medium/low",
            target_module=self.answer
        )

        # Return with full trajectory
        return dspy.Prediction(
            answer=answer_pred.answer,
            confidence=answer_pred.confidence,
            trajectory=trajectory,
            num_steps=len(trajectory)
        )

    def _format_tools(self) -> str:
        """Format available tools for prompt."""
        lines = []
        for tool in self.tools.values():
            lines.append(f"- {tool.name}: {tool.description}")
        return "\n".join(lines)

    def _format_trajectory(self, trajectory: List[Dict]) -> str:
        """Format trajectory for final answer generation."""
        lines = []
        for entry in trajectory:
            lines.append(f"Step {entry['step']}:")
            lines.append(f"  Thought: {entry['thought']}")
            lines.append(f"  Action: {entry['action']}({entry['action_input']})")
            if "observation" in entry:
                lines.append(f"  Observation: {entry['observation']}")
        return "\n".join(lines)

    def _execute_tool(self, tool_name: str, tool_input: str) -> str:
        """Execute a tool and return observation.

        Args:
            tool_name: Name of tool to execute
            tool_input: Input for tool

        Returns:
            Tool execution result
        """
        if tool_name not in self.tools:
            return f"Error: Tool '{tool_name}' not found. Available: {list(self.tools.keys())}"

        try:
            tool = self.tools[tool_name]
            result = tool.execute(**self._parse_tool_input(tool_input))
            return result
        except Exception as e:
            return f"Error executing {tool_name}: {str(e)}"

    def _parse_tool_input(self, tool_input: str) -> Dict[str, Any]:
        """Parse tool input string into kwargs.

        Args:
            tool_input: Raw input string

        Returns:
            Dictionary of parsed arguments
        """
        # Try JSON parsing first
        try:
            return json.loads(tool_input)
        except:
            pass

        # Fall back to simple string
        return {"query": tool_input} if tool_input else {}


# ============================================================================
# MEMORY-ENHANCED AGENT
# ============================================================================

class MemoryAgent(ReActAgent):
    """Agent with episodic memory.

    Extends ReActAgent with memory of past interactions.

    Example:
        ```python
        agent = MemoryAgent(
            tools=[SearchTool()],
            max_memory=5
        )

        result1 = agent(goal="What is Python?")
        result2 = agent(goal="What did I just ask?")  # Remembers
        ```
    """

    def __init__(self, *args, max_memory: int = 10, **kwargs):
        """Initialize memory agent.

        Args:
            max_memory: Maximum past interactions to remember
            *args, **kwargs: Passed to ReActAgent
        """
        super().__init__(*args, **kwargs)
        self.memory: List[Dict[str, str]] = []
        self.max_memory = max_memory

    def forward(self, goal: str) -> dspy.Prediction:
        """Execute with memory context."""
        # Add memory to goal context
        if self.memory:
            memory_context = self._format_memory()
            goal = f"Memory:\n{memory_context}\n\nCurrent goal: {goal}"

        # Execute
        result = super().forward(goal=goal)

        # Save to memory
        self._add_to_memory(goal, result.answer)

        return result

    def _format_memory(self) -> str:
        """Format memory for context."""
        lines = []
        for i, entry in enumerate(self.memory[-self.max_memory:], 1):
            lines.append(f"{i}. Q: {entry['goal']}")
            lines.append(f"   A: {entry['answer']}")
        return "\n".join(lines)

    def _add_to_memory(self, goal: str, answer: str):
        """Add interaction to memory."""
        self.memory.append({"goal": goal, "answer": answer})

        # Trim to max size
        if len(self.memory) > self.max_memory:
            self.memory = self.memory[-self.max_memory:]

    def clear_memory(self):
        """Clear all memory."""
        self.memory = []


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

def example_basic_agent():
    """Example: Basic ReAct agent."""
    import dspy

    # Configure LM
    lm = dspy.OpenAI(model="gpt-3.5-turbo")
    dspy.settings.configure(lm=lm)

    # Create agent with tools
    agent = ReActAgent(
        tools=[
            CalculatorTool(),
            SearchTool()
        ],
        max_steps=5,
        verbose=True
    )

    # Run agent
    result = agent(goal="What is the square root of 144?")

    print(f"\nFinal Answer: {result.answer}")
    print(f"Confidence: {result.confidence}")
    print(f"Steps taken: {result.num_steps}")


def example_memory_agent():
    """Example: Agent with memory."""
    import dspy

    lm = dspy.OpenAI(model="gpt-3.5-turbo")
    dspy.settings.configure(lm=lm)

    agent = MemoryAgent(
        tools=[SearchTool()],
        max_memory=5,
        verbose=False
    )

    # First query
    result1 = agent(goal="What is Python?")
    print(f"Q1: {result1.answer}\n")

    # Follow-up (uses memory)
    result2 = agent(goal="What are its main uses?")
    print(f"Q2: {result2.answer}\n")

    # Check memory
    print(f"Memory size: {len(agent.memory)}")


def example_custom_tool():
    """Example: Creating custom tools."""
    import dspy

    class WeatherTool(Tool):
        """Custom weather tool."""
        name = "weather"
        description = "Get current weather for a city"
        parameters = {"city": {"type": "string"}}

        def execute(self, city: str) -> str:
            # Simulate weather API
            return f"Weather in {city}: Sunny, 72°F"

    lm = dspy.OpenAI(model="gpt-3.5-turbo")
    dspy.settings.configure(lm=lm)

    agent = ReActAgent(
        tools=[WeatherTool()],
        max_steps=3
    )

    result = agent(goal="What's the weather in San Francisco?")
    print(result.answer)


def example_agent_optimization():
    """Example: Optimizing agents."""
    import dspy
    from dspy.teleprompt import BootstrapFewShot

    # Create agent
    agent = ReActAgent(tools=[CalculatorTool()], max_steps=5)

    # Create training data
    trainset = [
        dspy.Example(
            goal="What is 5 + 7?",
            answer="12"
        ).with_inputs("goal"),
        dspy.Example(
            goal="What is 10 * 3?",
            answer="30"
        ).with_inputs("goal"),
    ]

    # Define metric
    def accuracy(example, prediction, trace=None):
        return float(example.answer in prediction.answer)

    # Optimize
    optimizer = BootstrapFewShot(metric=accuracy, max_bootstrapped_demos=2)
    optimized_agent = optimizer.compile(agent, trainset=trainset)

    # Use optimized agent
    result = optimized_agent(goal="What is 8 + 9?")
    print(result.answer)


if __name__ == "__main__":
    # Uncomment to run examples
    # example_basic_agent()
    # example_memory_agent()
    # example_custom_tool()
    # example_agent_optimization()
    pass
