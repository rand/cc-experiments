# Basic ReAct Agent Example

Complete demonstration of ReAct (Reasoning + Acting) agent implementation using DSPy from Rust via PyO3.

## Overview

This example shows how to:
- Configure a ReAct agent with DSPy
- Register and use simple tools (search, calculator)
- Execute agent reasoning loops
- Extract complete execution traces with thoughts, actions, and observations
- Handle errors gracefully with production-quality patterns

## What is ReAct?

ReAct is an agentic pattern that combines **Reasoning** and **Acting**:

```
Question → [Reason → Act → Observe] (loop) → Answer
```

The agent:
1. **Reasons**: Thinks about what to do next
2. **Acts**: Chooses and executes a tool
3. **Observes**: Processes the tool's output
4. Repeats until it can answer the question

## Prerequisites

### System Requirements
- Rust 1.70+
- Python 3.8+
- OpenAI API key (for language model)

### Python Dependencies
```bash
pip install dspy-ai openai
```

### Environment Setup
```bash
export OPENAI_API_KEY="sk-..."
```

## Project Structure

```
basic-react/
├── Cargo.toml          # Project dependencies
├── README.md           # This file
└── src/
    └── main.rs         # ReAct agent implementation
```

## Building and Running

```bash
# Build the project
cargo build

# Run the example
cargo run

# Run with trace output
RUST_LOG=debug cargo run

# Run tests
cargo test
```

## Code Architecture

### Core Components

**1. Helper Macros**
```rust
kwargs!(py, "key" => value)  // Create Python kwargs dict
py_str!(py, "string")        // Create Python string
```

**2. LM Configuration**
```rust
configure_dspy_lm() -> Result<()>
```
Configures DSPy with OpenAI language model.

**3. Agent Execution**
```rust
let agent = ReActAgent::new(config)?;
let result = agent.forward_with_trace(question)?;
```

**4. Trace Extraction**
```rust
pub struct ReActResult {
    pub answer: String,
    pub trajectory: Vec<AgentStep>,
    pub total_iterations: usize,
    pub success: bool,
}

pub struct AgentStep {
    pub step_number: usize,
    pub thought: String,
    pub action: String,
    pub observation: String,
}
```

### Tool System

The example includes two simulated tools:

**Search Tool**: Simulates web search results
```rust
search("Paris France") -> "Paris is the capital of France..."
```

**Calculator Tool**: Evaluates mathematical expressions
```rust
calculator("2 + 2") -> "4"
```

In production, these would call real APIs (Google Serper, Wolfram Alpha, etc.).

## Example Usage

### Example 1: Simple Question
```rust
let agent = ReActAgent::new(config)?;
let result = agent.forward_with_trace("What is 15 * 23?")?;

println!("Answer: {}", result.answer);
println!("Steps taken: {}", result.total_iterations);
```

### Example 2: With Trace Analysis
```rust
let result = agent.forward_with_trace(question)?;

for step in &result.trajectory {
    println!("Step {}: {}", step.step_number, step.thought);
    println!("  Action: {}", step.action);
    println!("  Result: {}", step.observation);
}
```

### Example 3: Multiple Queries
```rust
let questions = vec![
    "What is the capital of France?",
    "Calculate 42 * 37",
    "Search for information about Rust programming",
];

for question in questions {
    let result = agent.forward_with_trace(question)?;
    println!("Q: {}", question);
    println!("A: {}", result.answer);
}
```

## Output Example

```
=== Example 1: Simple Calculation ===
Question: What is 25 * 17?

Agent Trace:
Step 1:
  Thought: I need to calculate 25 * 17
  Action: calculator("25 * 17")
  Observation: 425

Answer: 425

Total iterations: 1
Success: true

=== Example 2: Multi-step Reasoning ===
Question: What is the capital of France and what is its population?

Agent Trace:
Step 1:
  Thought: I need to search for information about Paris
  Action: search("Paris France capital")
  Observation: Paris is the capital and largest city of France...

Step 2:
  Thought: I found that Paris is the capital. Now I need population info.
  Action: search("Paris population")
  Observation: The population of Paris is approximately 2.1 million...

Answer: The capital of France is Paris, with a population of approximately 2.1 million people.

Total iterations: 2
Success: true
```

## Error Handling

The example demonstrates production-quality error handling:

```rust
// Invalid input
match agent.forward_with_trace("") {
    Ok(_) => println!("Success"),
    Err(e) => eprintln!("Error: {}", e),  // "Input cannot be empty"
}

// LM configuration errors
match configure_dspy_lm() {
    Ok(_) => println!("Configured"),
    Err(e) => eprintln!("Config failed: {}", e),  // Missing API key
}

// Tool execution errors
match tool_registry.execute("invalid_tool", input) {
    Ok(result) => println!("Result: {}", result),
    Err(e) => eprintln!("Tool error: {}", e),  // Tool not found
}
```

## Configuration Options

```rust
pub struct ReActConfig {
    pub signature: String,        // Default: "question -> answer"
    pub max_iterations: usize,    // Default: 5
    pub temperature: f32,         // Default: 0.7
}
```

Customize the agent behavior:
```rust
let config = ReActConfig {
    signature: "context, question -> detailed_answer".to_string(),
    max_iterations: 10,
    temperature: 0.5,
};
```

## Integration with Production Systems

To use this pattern in production:

1. **Replace simulated tools with real implementations**:
   ```rust
   // Use Google Serper API for search
   let search_tool = create_search_tool(api_key);

   // Use Wolfram Alpha for calculations
   let calc_tool = create_calculator_tool(api_key);
   ```

2. **Add tool registry**:
   ```rust
   let mut registry = ToolRegistry::new();
   registry.register("search", metadata, search_tool);
   registry.register("calculator", metadata, calc_tool);
   ```

3. **Implement observability**:
   ```rust
   // Log each step
   for step in &result.trajectory {
       tracing::info!("Agent step: {}", step.thought);
   }

   // Monitor performance
   let duration = start.elapsed();
   metrics.record_agent_execution(duration, result.success);
   ```

4. **Add retry logic**:
   ```rust
   let result = retry_with_backoff(|| {
       agent.forward_with_trace(question)
   }, max_retries)?;
   ```

## Testing

Run the included tests:
```bash
cargo test
```

Test coverage includes:
- Python initialization
- DSPy import verification
- Agent configuration
- Tool execution
- Trace extraction
- Error handling

## Common Issues

### Issue: "dspy module not found"
**Solution**: Install DSPy: `pip install dspy-ai`

### Issue: "OpenAI API key not set"
**Solution**: Export your API key: `export OPENAI_API_KEY="sk-..."`

### Issue: "Python 3.x not found"
**Solution**: Ensure Python 3.8+ is installed and in PATH

### Issue: Agent returns empty answer
**Solution**: Check max_iterations - agent may need more steps. Increase from 5 to 10.

## Performance Considerations

- **Cold start**: First execution includes Python interpreter initialization (~100ms)
- **Warm execution**: Subsequent calls are much faster (~50ms + LM latency)
- **Memory**: Each agent instance holds a Python object reference
- **Concurrency**: Use `Python::with_gil` for thread-safe execution

## Next Steps

After mastering this example, explore:

1. **Advanced Tool Registry** - See the `tool-registry` example
2. **Multi-Agent Systems** - See the `parallel-agents` example
3. **State Management** - See the `stateful-agent` example
4. **Production Deployment** - See the `production-agent` example

## References

- [DSPy Documentation](https://dspy-docs.vercel.app/)
- [PyO3 Guide](https://pyo3.rs/)
- [ReAct Paper](https://arxiv.org/abs/2210.03629)
- [DSPy GitHub](https://github.com/stanfordnlp/dspy)

## License

MIT License - See project root for details.
