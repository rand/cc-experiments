---
name: ml-llm-model-routing
description: Intelligent LLM routing with RouteLLM, semantic routing, and cost optimization
---

# LLM Model Routing

**Scope**: Cost-effective LLM routing, RouteLLM framework, semantic routing, rule-based strategies, observability
**Lines**: ~450
**Last Updated**: 2025-10-26

## When to Use This Skill

Activate this skill when:
- Reducing LLM costs while maintaining quality (up to 85% reduction)
- Building applications with mixed complexity queries
- Implementing multi-model architectures for different use cases
- Optimizing response latency and quality tradeoffs
- Routing based on query intent, complexity, or domain
- Instrumenting routing decisions with observability tools
- Deploying production LLM systems with cost constraints

## Core Concepts

### The Routing Problem

**Challenge**: Strong models (GPT-4o, Claude 3.5 Sonnet) are expensive but not always necessary. Weak models (GPT-4o mini, Gemini Flash) are cheap but limited.

**Solution**: Route queries dynamically to appropriate models based on complexity, intent, or requirements.

**Benefits**:
- 85%+ cost reduction on benchmarks (MT Bench)
- 45% cost reduction on MMLU
- 35% cost reduction on GSM8K
- Maintained quality equivalent to always using strong models
- Improved average latency for simple queries

### Routing Strategies

**1. Learning-Based Routing (RouteLLM)**:
- Trained on preference data (human/GPT-4 judgments)
- Predicts which model pair will satisfy quality thresholds
- Generalizes across different strong/weak model pairs

**2. Semantic Routing**:
- Uses embeddings to match queries to specialized models
- Routes based on semantic similarity to reference prompts
- Enables domain-specific model assignment

**3. Rule-Based Routing**:
- Deterministic rules based on query metadata
- Simple heuristics (length, keywords, patterns)
- Fastest routing decision time

**4. Hybrid Routing**:
- Combines multiple strategies for robustness
- Fallback chains for reliability
- Context-aware routing logic

### RouteLLM Framework

**Architecture**:
Published at ICLR 2025, RouteLLM is an open-source framework from UC Berkeley and Anyscale for cost-effective LLM routing based on preference data.

**Key Components**:
- **Router Models**: Trained classifiers that predict model selection
- **Preference Data**: Training data from Chatbot Arena, human feedback
- **Model Pairs**: Strong model (GPT-4) + weak model (Mixtral, GPT-3.5)
- **Threshold Tuning**: Adjustable quality/cost tradeoff

**Router Types**:

1. **sw_ranking** (Elo-based):
   - Weighted Elo calculation for routing decisions
   - Fast, interpretable, no training required
   - Good baseline performance

2. **bert** (BERT classifier):
   - BERT encoder trained on preference data
   - Balances speed and accuracy
   - Recommended for production use

3. **causal_llm** (LLM classifier):
   - Fine-tuned LLM as router (e.g., Llama)
   - Highest accuracy but slower
   - Best for quality-critical applications

4. **matrix_factorization**:
   - Low-rank factorization of preference matrix
   - Memory efficient
   - Suitable for large-scale deployments

**Performance**:
- Matches commercial routers (Martian, Not Diamond)
- 40%+ cheaper than commercial alternatives
- Generalizes to new model pairs without retraining

### Semantic Routing Architecture

**Components**:
- **Encoder**: Embedding model (BERT, Sentence Transformers, OpenAI)
- **Route Definitions**: Named routes with example prompts
- **Similarity Matching**: Cosine similarity to route examples
- **Threshold**: Minimum similarity for route assignment

**Modern Implementations (2025)**:

1. **vLLM Semantic Router**:
   - Rust-based, high-concurrency routing
   - ModernBERT classifier for intent detection
   - Zero-copy inference with Hugging Face Candle
   - Mixture-of-Models (MoM) architecture

2. **Red Hat Semantic Processor**:
   - Envoy ExtProc integration
   - Hybrid Rust + Golang implementation
   - Semantic cache with response reuse
   - ~90% accuracy without LLM inference

3. **Aurelio Labs Semantic Router**:
   - Multi-modal support (text, images)
   - Easy encoder integration (Cohere, OpenAI, HuggingFace)
   - Layer-based decision making

**Advantages**:
- Sub-millisecond routing decisions
- No LLM call required for routing
- Handles multi-domain applications
- Supports caching and reuse

---

## Implementation Patterns

### RouteLLM: Basic Setup

```python
from routellm.controller import Controller

# Initialize router with model pair
router = Controller(
    routers=["bert"],  # or ["sw_ranking", "causal_llm", "mf"]
    strong_model="gpt-4-1106-preview",
    weak_model="mixtral-8x7b-instruct-v0.1",
    api_base="http://localhost:8000/v1",  # Optional: custom endpoint
)

# Route a query
query = "Explain quantum entanglement"
response = router.route(
    model="router-bert-0.5",  # router-{type}-{threshold}
    messages=[{"role": "user", "content": query}]
)

print(f"Routed to: {response.model}")
print(f"Response: {response.choices[0].message.content}")
```

### RouteLLM: Threshold Tuning

```python
# Threshold controls quality/cost tradeoff
# Higher threshold = more weak model usage = lower cost
# Lower threshold = more strong model usage = higher quality

thresholds = [0.3, 0.5, 0.7, 0.9]

for threshold in thresholds:
    router_name = f"router-bert-{threshold}"
    response = router.route(
        model=router_name,
        messages=[{"role": "user", "content": "Simple math: 2+2"}]
    )
    print(f"Threshold {threshold}: {response.model}")

# Results:
# 0.3 -> gpt-4 (conservative, high quality)
# 0.5 -> mixtral (balanced)
# 0.7 -> mixtral (aggressive cost savings)
# 0.9 -> mixtral (maximum savings)
```

### RouteLLM: Evaluation Mode

```python
import pandas as pd
from routellm.routers import ROUTER_CLS

# Load router for evaluation
router_cls = ROUTER_CLS["bert"]
router = router_cls(
    strong_model_name="gpt-4-1106-preview",
    weak_model_name="mixtral-8x7b-instruct-v0.1"
)

# Evaluate on dataset
test_queries = [
    "What is 2+2?",
    "Explain the implications of quantum computing on cryptography",
    "Name the capital of France",
    "Analyze the socioeconomic factors in the French Revolution"
]

decisions = []
for query in test_queries:
    # Get routing decision (0-1 score)
    score = router.route(query)
    selected = "strong" if score < 0.5 else "weak"
    decisions.append({
        "query": query[:50],
        "score": score,
        "model": selected
    })

df = pd.DataFrame(decisions)
print(df)

# Calculate cost savings
weak_ratio = (df["model"] == "weak").mean()
print(f"Weak model usage: {weak_ratio:.1%}")
print(f"Estimated savings: {weak_ratio * 0.95:.1%}")  # 95% cheaper
```

### Semantic Routing with Aurelio

```python
from semantic_router import Route, RouteLayer
from semantic_router.encoders import OpenAIEncoder

# Define routes with examples
code_route = Route(
    name="code",
    utterances=[
        "How do I write a function in Python?",
        "Debug this code snippet",
        "Explain this algorithm",
        "Write a sorting function"
    ]
)

general_route = Route(
    name="general",
    utterances=[
        "What is the weather today?",
        "Tell me a joke",
        "What's the capital of France?",
        "Who won the World Series?"
    ]
)

reasoning_route = Route(
    name="reasoning",
    utterances=[
        "Solve this complex math problem",
        "Analyze the implications of this policy",
        "Compare and contrast these approaches",
        "Provide a detailed ethical analysis"
    ]
)

# Initialize encoder and layer
encoder = OpenAIEncoder()
route_layer = RouteLayer(
    encoder=encoder,
    routes=[code_route, general_route, reasoning_route]
)

# Route queries
queries = [
    "How do I reverse a string in JavaScript?",
    "What's 2+2?",
    "Explain the philosophical implications of AI consciousness"
]

for query in queries:
    route = route_layer(query)
    print(f"Query: {query[:50]}")
    print(f"Route: {route.name if route else 'fallback'}\n")

# Map routes to models
model_map = {
    "code": "claude-3.5-sonnet",  # Best at coding
    "general": "gpt-4o-mini",  # Fast and cheap
    "reasoning": "gpt-4o",  # Strong reasoning
    None: "gpt-4o-mini"  # Default fallback
}

def route_and_call(query: str):
    route = route_layer(query)
    model = model_map.get(route.name if route else None)
    print(f"Routing to: {model}")
    # Call selected model...
```

### Rule-Based Routing

```python
import re
from typing import Literal

ModelType = Literal["strong", "weak", "specialized"]

class RuleBasedRouter:
    def __init__(
        self,
        strong_model: str = "gpt-4o",
        weak_model: str = "gpt-4o-mini",
        code_model: str = "claude-3.5-sonnet"
    ):
        self.strong = strong_model
        self.weak = weak_model
        self.code = code_model

    def route(self, query: str, context: dict = None) -> str:
        """Route based on heuristics"""
        query_lower = query.lower()

        # Rule 1: Code-related queries -> specialized model
        code_keywords = ["code", "function", "debug", "implement", "algorithm"]
        if any(kw in query_lower for kw in code_keywords):
            return self.code

        # Rule 2: Simple factual queries -> weak model
        simple_patterns = [
            r"^what is \w+\?$",
            r"^who is \w+\?$",
            r"^when did \w+",
            r"^\d+[\+\-\*/]\d+",  # Simple math
        ]
        if any(re.match(p, query_lower) for p in simple_patterns):
            return self.weak

        # Rule 3: Long, complex queries -> strong model
        if len(query) > 500:
            return self.strong

        # Rule 4: Reasoning keywords -> strong model
        reasoning_keywords = [
            "analyze", "implications", "compare", "evaluate",
            "critique", "synthesize", "ethical", "philosophical"
        ]
        if any(kw in query_lower for kw in reasoning_keywords):
            return self.strong

        # Rule 5: Context indicates multi-turn conversation -> strong model
        if context and context.get("turn_count", 0) > 3:
            return self.strong

        # Default: weak model
        return self.weak

# Usage
router = RuleBasedRouter()

queries = [
    "Write a binary search function",  # -> code model
    "What is the capital of France?",  # -> weak
    "2+2",  # -> weak
    "Analyze the ethical implications of AI in healthcare"  # -> strong
]

for q in queries:
    model = router.route(q)
    print(f"{q[:50]:50} -> {model}")
```

### Hybrid Routing with Fallback

```python
from typing import Optional
import openai

class HybridRouter:
    def __init__(self):
        self.semantic_router = route_layer  # From earlier example
        self.rule_router = RuleBasedRouter()

    def route(
        self,
        query: str,
        use_semantic: bool = True,
        use_rules: bool = True
    ) -> str:
        """Hybrid routing with fallback chain"""

        # Try semantic routing first (most accurate)
        if use_semantic:
            route = self.semantic_router(query)
            if route and route.name:
                return model_map.get(route.name)

        # Fallback to rule-based routing
        if use_rules:
            return self.rule_router.route(query)

        # Final fallback
        return "gpt-4o-mini"

    def route_with_retry(self, query: str, max_retries: int = 2):
        """Route with fallback on errors"""
        models = [
            self.route(query),  # Primary
            "gpt-4o",  # Fallback 1
            "claude-3.5-sonnet"  # Fallback 2
        ]

        for i, model in enumerate(models[:max_retries + 1]):
            try:
                response = openai.ChatCompletion.create(
                    model=model,
                    messages=[{"role": "user", "content": query}],
                    timeout=30
                )
                return {
                    "model": model,
                    "response": response.choices[0].message.content,
                    "attempt": i + 1
                }
            except Exception as e:
                print(f"Model {model} failed: {e}")
                if i == len(models) - 1:
                    raise
                continue

# Usage
hybrid = HybridRouter()
result = hybrid.route_with_retry(
    "Explain quantum entanglement to a 10-year-old"
)
print(f"Used model: {result['model']} (attempt {result['attempt']})")
```

### Arize Phoenix Observability

```python
import phoenix as px
from phoenix.trace import using_project
from opentelemetry import trace

# Start Phoenix
px.launch_app()

# Instrument routing
tracer = trace.get_tracer(__name__)

@using_project("llm-routing")
def route_and_call(query: str):
    with tracer.start_as_current_span("routing_decision") as span:
        # Route
        router = HybridRouter()
        selected_model = router.route(query)

        # Log routing decision
        span.set_attribute("query", query)
        span.set_attribute("selected_model", selected_model)
        span.set_attribute("routing_strategy", "hybrid")

        # Call model
        with tracer.start_as_current_span("llm_call") as call_span:
            call_span.set_attribute("model", selected_model)

            response = openai.ChatCompletion.create(
                model=selected_model,
                messages=[{"role": "user", "content": query}]
            )

            # Log metrics
            call_span.set_attribute("tokens_used", response.usage.total_tokens)
            call_span.set_attribute("cost_usd", calculate_cost(response, selected_model))

        return response

# View routing patterns in Phoenix UI
# Navigate to http://localhost:6006
```

---

## Quick Reference

### Model Strengths by Category (2025)

```
Category      | Best Models              | Use Case
--------------|--------------------------|----------------------------------
Reasoning     | GPT-4o, Claude 3.5/4    | Complex analysis, multi-step logic
Coding        | Claude 3.5 Sonnet       | Code generation, debugging
Speed         | Gemini 2.5 Flash        | 370 tok/s, real-time applications
Cost          | GPT-4o mini, Gemini Flash| Simple queries, high volume
Multimodal    | GPT-4o, Gemini 2.5      | Vision + text tasks
Long Context  | Claude 3.5 (200k)       | Document analysis, large codebases
```

### Cost Comparison (per million tokens)

```
Model                    | Input    | Output   | Use Case
-------------------------|----------|----------|------------------
GPT-4o                   | $5.00    | $20.00   | General strong
GPT-4o mini              | $0.15    | $0.60    | General weak
Claude 3.5 Sonnet        | $3.00    | $15.00   | Coding strong
Claude 3 Haiku           | $0.25    | $1.25    | Fast weak
Gemini 2.5 Flash         | $0.10    | $0.40    | Cheapest strong
DeepSeek V3              | $0.30    | $1.00    | Open-source alt
```

### Routing Decision Tree

```
Query characteristics -> Recommended strategy
────────────────────────────────────────────────
High volume, mixed complexity -> RouteLLM
Domain-specific (code, legal)  -> Semantic routing
Latency critical              -> Rule-based
Quality critical              -> Always strong model
Budget constrained            -> RouteLLM threshold 0.7+
Multi-turn conversations      -> Session-aware routing
```

---

## Anti-Patterns

❌ **Always using the strongest model**: Wastes 10-50x cost on simple queries
✅ Route based on complexity; use weak models for 60-80% of queries

❌ **No observability on routing decisions**: Can't optimize or debug
✅ Use Arize Phoenix to trace routing logic and model performance

❌ **Static routing rules that don't adapt**: Performance degrades over time
✅ Continuously evaluate routing accuracy; retrain or adjust thresholds

❌ **Ignoring latency in routing overhead**: Routing adds 100ms+ delay
✅ Use cached semantic embeddings; pre-compute route assignments

❌ **Single point of failure in routing**: Entire system fails if router breaks
✅ Implement fallback chains; default to mid-tier model on router errors

❌ **Not tracking cost savings**: Can't justify routing complexity
✅ Log model selection, token usage, and calculate cost deltas

❌ **Over-engineering for simple use cases**: Rule-based is fine for 2-3 models
✅ Start simple; add RouteLLM/semantic routing when scaling to 5+ models

❌ **Training routers on outdated model pairs**: New models shift capabilities
✅ Regularly re-evaluate with current model benchmarks (GPT-4o, Claude 3.5)

---

## Related Skills

- `llm-model-selection.md` - Choosing models for specific capabilities
- `multi-model-orchestration.md` - Coordinating multiple models in pipelines
- `modal-web-endpoints.md` - Deploying routing logic as FastAPI endpoints
- `api-rate-limiting.md` - Rate limiting across multiple model providers
- `observability-distributed-tracing.md` - Tracing multi-model systems
- `api-error-handling.md` - Handling provider failures and fallbacks

---

**Last Updated**: 2025-10-26
**Format Version**: 1.0 (Atomic)
