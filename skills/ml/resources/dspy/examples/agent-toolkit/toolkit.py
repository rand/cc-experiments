"""Agent Toolkit - Reusable tools and patterns for DSPy agents."""

import dspy
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod


# ============================================================================
# BASE TOOL
# ============================================================================

class Tool(ABC):
    """Base class for agent tools."""

    name: str = "tool"
    description: str = "A tool"
    parameters: Dict[str, Any] = {}

    @abstractmethod
    def execute(self, **kwargs) -> str:
        """Execute tool."""
        pass

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }


# ============================================================================
# BUILT-IN TOOLS
# ============================================================================

class SearchTool(Tool):
    """Search knowledge base."""

    name = "search"
    description = "Search for information"
    parameters = {"query": {"type": "string"}}

    def __init__(self, k: int = 3):
        self.retriever = dspy.Retrieve(k=k)

    def execute(self, query: str) -> str:
        results = self.retriever(query).passages
        return "\n".join(f"{i+1}. {p[:200]}..." for i, p in enumerate(results))


class CalculatorTool(Tool):
    """Perform calculations."""

    name = "calculator"
    description = "Perform arithmetic"
    parameters = {"expression": {"type": "string"}}

    def execute(self, expression: str) -> str:
        try:
            result = eval(expression, {"__builtins__": {}}, {})
            return str(result)
        except Exception as e:
            return f"Error: {e}"


class PythonTool(Tool):
    """Execute Python code."""

    name = "python"
    description = "Execute Python code"
    parameters = {"code": {"type": "string"}}

    def execute(self, code: str) -> str:
        try:
            from io import StringIO
            import sys

            old_stdout = sys.stdout
            sys.stdout = StringIO()

            exec(code)

            output = sys.stdout.getvalue()
            sys.stdout = old_stdout

            return output or "Success"
        except Exception as e:
            return f"Error: {e}"


# ============================================================================
# REACT AGENT
# ============================================================================

class ReActAgent(dspy.Module):
    """ReAct agent with tool use."""

    def __init__(self, tools: List[Tool], max_steps: int = 10):
        super().__init__()
        self.tools = {tool.name: tool for tool in tools}
        self.max_steps = max_steps
        self.think = dspy.ChainOfThought("goal, context, tools -> thought, action, action_input")
        self.answer = dspy.ChainOfThought("goal, trajectory -> answer, confidence")

    def forward(self, goal: str) -> dspy.Prediction:
        trajectory = []
        context = "Starting."

        for step in range(self.max_steps):
            # Think
            thought = self.think(
                goal=goal,
                context=context,
                tools=self._format_tools()
            )

            action = thought.action.strip().lower()
            action_input = thought.action_input

            if action == "finish":
                break

            # Execute tool
            observation = self._execute_tool(action, action_input)
            trajectory.append({
                "thought": thought.thought,
                "action": action,
                "observation": observation
            })

            context = f"Action: {action}\nObservation: {observation}"

        # Generate answer
        answer = self.answer(
            goal=goal,
            trajectory=str(trajectory)
        )

        return dspy.Prediction(
            answer=answer.answer,
            confidence=answer.confidence,
            trajectory=trajectory
        )

    def _format_tools(self) -> str:
        return "\n".join(f"- {t.name}: {t.description}" for t in self.tools.values())

    def _execute_tool(self, tool_name: str, tool_input: str) -> str:
        if tool_name not in self.tools:
            return f"Error: Tool '{tool_name}' not found"

        try:
            return self.tools[tool_name].execute(query=tool_input)
        except Exception as e:
            return f"Error: {e}"


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    # Configure
    lm = dspy.OpenAI(model="gpt-3.5-turbo")
    dspy.settings.configure(lm=lm)

    # Create agent
    agent = ReActAgent(
        tools=[SearchTool(), CalculatorTool()],
        max_steps=5
    )

    # Test
    result = agent(goal="What is the square root of 144?")
    print(f"Answer: {result.answer}")
    print(f"Confidence: {result.confidence}")
