# Stateful Agent Example

A comprehensive example demonstrating persistent agent memory, conversation history tracking, and context augmentation in Rust using PyO3 and DSPy.

## Overview

This example implements a stateful ReAct agent that maintains conversation history, stores facts, and uses context from previous interactions to provide more informed responses. The agent demonstrates:

- **Persistent Memory**: Conversation history and facts stored in memory
- **Context Augmentation**: Previous interactions inform current responses
- **State Serialization**: Save and load agent state to/from JSON
- **Memory Pruning**: Strategies to manage memory size and relevance
- **Multi-turn Conversations**: Natural dialogue with context awareness

## Key Concepts

### AgentMemory

The `AgentMemory` struct maintains:
- **Conversation History**: Q&A pairs with timestamps and reasoning steps
- **Fact Storage**: Key-value pairs for learned information
- **Context Building**: Retrieves recent relevant context
- **Persistence**: JSON serialization/deserialization

### StatefulReActAgent

The agent combines:
- Tool registry for available actions
- Memory for conversation context
- DSPy ReAct for reasoning
- Context-augmented question answering

## Project Structure

```
stateful-agent/
├── Cargo.toml           # Dependencies and configuration
├── README.md            # This file
└── src/
    ├── lib.rs          # AgentMemory and core library (400-500 lines)
    └── main.rs         # StatefulReActAgent demo (200-300 lines)
```

## Installation

### Prerequisites

1. **Rust toolchain** (1.70+):
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

2. **Python** (3.8+) with DSPy:
```bash
pip install dspy-ai
```

3. **OpenAI API key** (or other LM provider):
```bash
export OPENAI_API_KEY='your-key-here'
```

### Build

```bash
# Build library
cargo build --release

# Build standalone binary
cargo build --release --bin stateful-agent

# Run the demo
cargo run --bin stateful-agent
```

## Usage

### As a Library

```rust
use stateful_agent::{AgentMemory, ConversationTurn};
use chrono::Utc;

// Create new memory
let mut memory = AgentMemory::new();

// Add conversation turns
memory.add_turn(
    "What is the capital of France?".to_string(),
    "Paris".to_string(),
    3
);

// Store facts
memory.add_fact("user_name".to_string(), "Alice".to_string());
memory.add_fact("favorite_color".to_string(), "blue".to_string());

// Get context for next interaction
let context = memory.get_context(5); // Last 5 turns
println!("Context: {}", context);

// Save to disk
memory.save("agent_memory.json")?;

// Load from disk
let loaded = AgentMemory::load("agent_memory.json")?;
```

### Running the Demo

The demo showcases:
1. **Multi-turn conversation** with memory retention
2. **Fact extraction** and storage
3. **Context augmentation** in subsequent questions
4. **Memory persistence** across sessions
5. **Memory pruning** strategies

```bash
cargo run --bin stateful-agent
```

Example session:
```
=== Stateful Agent Demo ===

Turn 1: What is the capital of France?
Answer: Paris is the capital of France.

Turn 2: What is the population?
Answer: Based on our previous discussion about Paris, the population of Paris is approximately 2.2 million in the city proper, and about 12 million in the metropolitan area.

Memory saved to: agent_memory.json

=== Memory Statistics ===
Conversation turns: 2
Facts stored: 3
Memory size: 245 bytes
Created: 2025-10-30 13:15:42 UTC
Last updated: 2025-10-30 13:15:45 UTC
```

## Memory Management

### Context Window Strategies

```rust
// Get last N turns
let context = memory.get_context(5);

// Get turns within time window
let recent = memory.get_recent_turns(Duration::from_secs(3600)); // Last hour

// Get relevant turns by keyword
let relevant = memory.search_history("Paris");
```

### Memory Pruning

```rust
// Prune old conversations (keep last N)
memory.prune_history(100);

// Prune by age (remove older than duration)
memory.prune_by_age(Duration::from_days(7));

// Prune by relevance score
memory.prune_irrelevant(0.3); // Remove turns with score < 0.3
```

### Memory Size Management

```rust
// Check memory size
let size = memory.estimate_size();
if size > 10_000_000 { // 10 MB
    memory.compact(); // Summarize old history
}

// Serialize with compression
memory.save_compressed("memory.json.gz")?;
```

## Advanced Features

### Custom Context Building

```rust
impl AgentMemory {
    pub fn get_context_with_relevance(
        &self,
        query: &str,
        max_turns: usize
    ) -> String {
        // Score each turn by relevance to query
        // Return top-k most relevant
    }
}
```

### Fact Extraction

```rust
// Extract facts from conversation
let facts = memory.extract_facts_from_turn(turn_id);
for (key, value) in facts {
    memory.add_fact(key, value);
}
```

### Multi-Agent Memory Sharing

```rust
// Merge memories from multiple agents
let combined = AgentMemory::merge(vec![memory1, memory2, memory3]);

// Share specific facts
memory1.share_facts_with(&mut memory2, vec!["user_name", "preferences"]);
```

## Performance Considerations

### Memory Footprint

- **Small**: < 100 turns, < 50 facts: ~50 KB
- **Medium**: 100-1000 turns, 50-500 facts: ~500 KB
- **Large**: 1000+ turns, 500+ facts: 5+ MB

### Serialization Performance

- **JSON**: ~1 ms for 100 turns
- **Compressed**: ~5 ms for 100 turns (50% size reduction)
- **Binary**: ~0.5 ms for 100 turns (smallest size)

### Context Retrieval

- **Last N turns**: O(n) - fast for small N
- **Time-based**: O(n) - linear scan
- **Keyword search**: O(n*m) - can be slow for large histories
- **Indexed**: O(log n) - use for large histories

## Testing

```bash
# Run all tests
cargo test

# Run with output
cargo test -- --nocapture

# Run specific test
cargo test test_memory_persistence
```

## Integration with DSPy

### Setting up DSPy Agent

```python
import dspy

# Configure LM
lm = dspy.OpenAI(model='gpt-4')
dspy.settings.configure(lm=lm)

# Define agent signature
class ReActAgent(dspy.Module):
    def __init__(self):
        super().__init__()
        self.react = dspy.ReAct("question -> answer")

    def forward(self, question):
        return self.react(question=question)
```

### Using from Rust

```rust
use pyo3::prelude::*;
use stateful_agent::StatefulReActAgent;

Python::with_gil(|py| {
    let agent = StatefulReActAgent::new(py)?;

    // First question
    let answer1 = agent.execute_with_memory(
        py,
        "What is machine learning?"
    )?;

    // Follow-up with context
    let answer2 = agent.execute_with_memory(
        py,
        "What are its applications?"
    )?;

    // Memory automatically includes previous Q&A
});
```

## Troubleshooting

### Common Issues

1. **Memory not persisting**:
   - Check file permissions for `agent_memory.json`
   - Ensure `save()` is called before program exit

2. **Context not being used**:
   - Verify `get_context()` returns non-empty string
   - Check `max_turns` parameter is > 0

3. **Performance degradation**:
   - Implement memory pruning
   - Use compressed serialization
   - Consider indexed search for large histories

### Debug Logging

```rust
env_logger::init();

// Set environment variable
// RUST_LOG=stateful_agent=debug cargo run
```

## Real-World Applications

### Customer Support Bot
- Remembers customer information across sessions
- Provides personalized responses based on history
- Tracks issue resolution progress

### Research Assistant
- Maintains context of research topic
- Remembers key findings and sources
- Builds knowledge graph over time

### Personal Assistant
- Learns user preferences and habits
- Provides context-aware recommendations
- Manages long-term goals and tasks

## References

- [PyO3 Documentation](https://pyo3.rs)
- [DSPy Documentation](https://github.com/stanfordnlp/dspy)
- [ReAct Paper](https://arxiv.org/abs/2210.03629)
- [Agent Memory Patterns](https://arxiv.org/abs/2304.03442)

## License

This example is part of the PyO3-DSPy Agents skill documentation.
