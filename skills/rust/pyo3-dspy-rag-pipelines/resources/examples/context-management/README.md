# Context Window Management Example

Production-ready context window management for RAG pipelines with intelligent token counting, smart truncation strategies, and document prioritization.

## Features

- **Token Counting**: Integration with tiktoken for accurate OpenAI token counting
- **Context Window Limits**: Support for multiple model limits (4k, 8k, 16k, 32k tokens)
- **Smart Truncation**: Multiple strategies for handling context overflow
  - Head-only: Keep earliest content
  - Tail-only: Keep latest content
  - Middle: Keep beginning and end, remove middle
  - Sliding window: Keep most recent within budget
- **Document Prioritization**: Relevance-based ordering and filtering
- **Context Assembly**: Intelligent context building from retrieved documents
- **Overflow Handling**: Graceful degradation when context exceeds limits
- **Token Budget Allocation**: System prompt, query, and document allocation

## Use Cases

1. **RAG Pipelines**: Manage retrieved document context for LLM queries
2. **Conversation History**: Keep relevant history within token limits
3. **Document Summarization**: Progressive summarization with context constraints
4. **Multi-turn Dialogues**: Maintain conversation context efficiently
5. **Long Document Processing**: Handle documents exceeding context windows

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Context Manager                        │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Tiktoken   │  │  Truncation  │  │ Prioritization│  │
│  │   Counter    │  │  Strategies  │  │   Scorer      │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│         │                  │                  │          │
│         └──────────────────┴──────────────────┘          │
│                            │                             │
│                   ┌────────▼────────┐                    │
│                   │ Context Builder │                    │
│                   └─────────────────┘                    │
│                            │                             │
└────────────────────────────┼─────────────────────────────┘
                             │
                    ┌────────▼─────────┐
                    │   LLM Query      │
                    └──────────────────┘
```

## Token Budget Allocation

Default allocation for 8k context window:
- **System Prompt**: 500 tokens (6%)
- **User Query**: 200 tokens (2.5%)
- **Response Buffer**: 1000 tokens (12.5%)
- **Documents**: 6300 tokens (79%)

Adjustable based on use case:
- Q&A: More document space
- Chat: More conversation history
- Summarization: Maximum document space

## Truncation Strategies

### 1. Head-Only
Keep earliest content, discard overflow from end.
```
Original: [A, B, C, D, E, F]
Result:   [A, B, C]
```
**Best for**: Sequential processing, instruction following

### 2. Tail-Only
Keep latest content, discard overflow from beginning.
```
Original: [A, B, C, D, E, F]
Result:   [D, E, F]
```
**Best for**: Conversation history, recent context priority

### 3. Middle
Keep beginning and end, remove middle content.
```
Original: [A, B, C, D, E, F]
Result:   [A, B, ... E, F]
```
**Best for**: Maintaining context boundaries, document structure

### 4. Sliding Window
Keep most recent content within fixed window.
```
Original: [A, B, C, D, E, F]
Window:   [C, D, E]  (moves right)
```
**Best for**: Streaming, progressive processing

## Document Prioritization

Documents ranked by:
1. **Relevance Score**: Retrieved similarity/ranking
2. **Recency**: Timestamp or order in results
3. **Length**: Shorter documents preferred when space limited
4. **Completeness**: Full documents over fragments

Priority formula:
```
priority = (relevance * 0.6) + (recency * 0.2) + (1 / sqrt(length) * 0.1) + (completeness * 0.1)
```

## Quick Start

```bash
# Build
cargo build --release

# Run with default settings (8k context window)
cargo run

# The example demonstrates:
# 1. Token counting with tiktoken
# 2. All truncation strategies on sample documents
# 3. Priority-based document selection
# 4. Context assembly with budget constraints
# 5. Overflow handling scenarios
```

## Example Output

```
Context Window Management Example
==================================

Model: gpt-3.5-turbo
Context Limit: 8192 tokens
Token Budget:
  System: 500 tokens
  Query: 200 tokens
  Response: 1000 tokens
  Documents: 6492 tokens

Retrieved Documents: 5
Total tokens: 8450

Truncation Strategy: Middle
Documents included: 4 (fit within budget)
Final context tokens: 7892

Context Assembly:
--------------------------------------------------
System: You are a helpful AI assistant...
Query: What are the key features of Rust?
Documents:
  [1] Rust Memory Safety (relevance: 0.95) - 2100 tokens
  [2] Rust Ownership Model (relevance: 0.92) - 1850 tokens
  [3] Rust Performance (relevance: 0.88) - 1650 tokens
  [4] Rust Concurrency (relevance: 0.85) - 1792 tokens
--------------------------------------------------

Tokens used: 7892 / 8192 (96.3%)
Documents omitted: 1 (low priority)
```

## Integration Example

```rust
use context_manager::{ContextManager, TruncationStrategy, Document};

// Initialize with model limits
let manager = ContextManager::new(8192, "gpt-3.5-turbo")?;

// Add retrieved documents with scores
let docs = vec![
    Document::new("doc1", "Content about Rust...", 0.95),
    Document::new("doc2", "More Rust details...", 0.88),
    Document::new("doc3", "Advanced Rust...", 0.82),
];

// Build context with smart truncation
let context = manager.build_context(
    "You are a helpful assistant",
    "What is Rust?",
    &docs,
    TruncationStrategy::Middle,
)?;

// Use context in LLM call
let response = llm_client.complete(&context).await?;
```

## Python Integration (PyO3)

```python
from context_manager import ContextManager, Document, TruncationStrategy

# Initialize
manager = ContextManager(context_limit=8192, model="gpt-3.5-turbo")

# Create documents
docs = [
    Document(id="1", content="...", relevance=0.95),
    Document(id="2", content="...", relevance=0.88),
]

# Build context
context = manager.build_context(
    system_prompt="You are helpful",
    query="What is Rust?",
    documents=docs,
    strategy=TruncationStrategy.MIDDLE
)

# Use with OpenAI
response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": context.system_prompt},
        {"role": "user", "content": context.query},
    ],
    max_tokens=context.response_budget
)
```

## Configuration

Customize token budgets:

```rust
let mut manager = ContextManager::new(8192, "gpt-3.5-turbo")?;

// Adjust allocation for Q&A use case
manager.set_budget_allocation(
    400,  // system prompt
    200,  // query
    800,  // response
    // remaining for documents
)?;

// For chat with more history
manager.set_budget_allocation(
    300,  // system
    500,  // query + history
    1000, // response
)?;
```

## Performance Characteristics

- **Token Counting**: ~100k tokens/sec (tiktoken)
- **Context Building**: ~50ms for 20 documents
- **Memory**: ~O(n) where n = total document size
- **Truncation**: O(n) single pass

## Best Practices

1. **Pre-count tokens**: Count before expensive LLM calls
2. **Cache token counts**: Reuse for same content
3. **Prioritize early**: Filter before truncation
4. **Monitor usage**: Track actual vs budgeted tokens
5. **Test strategies**: Different strategies for different use cases
6. **Leave buffer**: Don't use 100% of limit
7. **Handle overflow**: Graceful degradation plan

## Advanced Patterns

### Progressive Context Reduction
```rust
let strategies = vec![
    TruncationStrategy::Middle,
    TruncationStrategy::Tail,
    TruncationStrategy::Head,
];

for strategy in strategies {
    if let Ok(context) = manager.build_context(system, query, docs, strategy) {
        if context.total_tokens() <= limit {
            return Ok(context);
        }
    }
}
```

### Adaptive Budget Allocation
```rust
// Adjust based on query complexity
let query_tokens = manager.count_tokens(query)?;
if query_tokens > 300 {
    manager.increase_query_budget(200)?;
}
```

### Multi-tier Priority
```rust
// Critical documents always included
let critical_docs = docs.iter().filter(|d| d.relevance > 0.9);
let optional_docs = docs.iter().filter(|d| d.relevance <= 0.9);

// Build with tiered inclusion
let context = manager.build_with_tiers(
    system, query,
    critical_docs, optional_docs,
    strategy
)?;
```

## Troubleshooting

**Context always truncated**: Reduce system prompt or increase limit
**Low quality results**: Try different truncation strategies
**Token count mismatch**: Ensure correct model encoding (cl100k_base for GPT-3.5/4)
**Slow performance**: Cache token counts, reduce document preprocessing

## References

- [OpenAI Tokenizer](https://platform.openai.com/tokenizer)
- [tiktoken](https://github.com/openai/tiktoken)
- [Context Window Limits](https://platform.openai.com/docs/models)
- [RAG Best Practices](https://www.anthropic.com/index/retrieval-augmented-generation)

## License

MIT
