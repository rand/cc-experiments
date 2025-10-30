# Agent Toolkit

Reusable library of tools and patterns for building DSPy agents.

## Tools Included

1. **SearchTool** - Web/knowledge base search
2. **CalculatorTool** - Mathematical operations
3. **PythonTool** - Execute Python code
4. **SQLTool** - Query databases
5. **APITool** - Make HTTP requests
6. **FileTool** - Read/write files

## Quick Start

```python
from agent_toolkit import ReActAgent, SearchTool, CalculatorTool

agent = ReActAgent(
    tools=[SearchTool(), CalculatorTool()],
    max_steps=5
)

result = agent(goal="What is the square root of 144?")
print(result.answer)
```

## Custom Tools

```python
from agent_toolkit import Tool

class WeatherTool(Tool):
    name = "weather"
    description = "Get weather for a city"

    def execute(self, city: str) -> str:
        # Your implementation
        return f"Weather in {city}: Sunny"

# Use it
agent = ReActAgent(tools=[WeatherTool()])
```

## Files

- `toolkit.py` - Main toolkit implementation
- `tools/` - Individual tool implementations
- `examples/` - Usage examples
- `tests/` - Test suite

## Features

- Plug-and-play tool system
- Automatic tool discovery
- Error handling and retries
- Tool composition
- Memory management
