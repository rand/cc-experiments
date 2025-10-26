---
name: ml-llm-evaluation-frameworks
description: Production-grade LLM evaluation using Arize Phoenix (OpenTelemetry tracing, self-hosted evals), Braintrust (86x faster search), LangSmith, and Langfuse with cost tracking and observability integration
---

# LLM Evaluation Frameworks

Last Updated: 2025-10-26

## When to Use This Skill

Use LLM evaluation frameworks when:
- **Production monitoring**: Tracking LLM performance in deployed applications
- **Continuous evaluation**: Running automated evals on every model or prompt change
- **Cost optimization**: Monitoring token usage and inference costs across projects
- **Tracing and debugging**: Understanding LLM behavior through distributed tracing
- **A/B testing**: Comparing prompt variations or model versions
- **Dataset management**: Organizing test cases and golden datasets
- **Team collaboration**: Sharing evaluation results and datasets across teams
- **Compliance**: Auditing LLM outputs for safety, bias, or regulatory requirements

**Anti-pattern**: Using only offline benchmarks without production evaluation. Always monitor real-world performance.

## Core Concepts

### Framework Comparison (2024-2025)

| Feature | Arize Phoenix | Braintrust | LangSmith | Langfuse |
|---------|---------------|------------|-----------|----------|
| **Self-Hosted** | ✅ Yes | ❌ Cloud only | ❌ Cloud only | ✅ Yes |
| **Open Source** | ✅ Full | ⚠️ Partial | ❌ No | ✅ Full |
| **Tracing Protocol** | OpenTelemetry | Proprietary | Proprietary | OpenInference |
| **Framework Support** | All (agnostic) | All | LangChain focus | All |
| **Search Speed** | Fast | 86x faster | Standard | Fast |
| **Built-in Evals** | ✅ Extensive | ✅ Yes | ✅ Yes | ⚠️ Limited |
| **Cost Tracking** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **Pricing** | Free (OSS) | Paid tiers | Paid tiers | Free tier + paid |

### Arize Phoenix: Deep Dive

**Why Phoenix?**
- **Framework-agnostic**: Works with any LLM framework (LangChain, LlamaIndex, DSPy, raw OpenAI)
- **OpenTelemetry standard**: Industry-standard tracing protocol
- **Self-hostable**: Full control over data privacy and infrastructure
- **Production-ready evals**: Built-in library of evaluation metrics
- **Real-time monitoring**: Live dashboards for production systems

**Architecture**:
```
Your Application
    ↓
OpenTelemetry Instrumentation
    ↓
Phoenix Collector (OTLP endpoint)
    ↓
Phoenix UI (React dashboard)
```

**Key Components**:
1. **Tracing**: OpenTelemetry-based distributed tracing for LLM calls
2. **Evaluations**: Pre-built and custom eval functions
3. **Datasets**: Test case management and versioning
4. **Experiments**: Compare models, prompts, or configurations
5. **Embeddings**: Visualize and cluster embeddings for debugging

### Braintrust

**Strengths**:
- **Search performance**: 86x faster search compared to competitors (2024 benchmark)
- **API-first design**: Programmatic access to all features
- **Prompt playground**: Interactive prompt engineering with version control
- **Scoring functions**: Flexible evaluation metric system

**Best for**: Teams prioritizing search performance and API-driven workflows

### LangSmith

**Strengths**:
- **LangChain integration**: Native support for LangChain applications
- **Human feedback**: Built-in annotation and feedback collection
- **Dataset sharing**: Public datasets and community benchmarks

**Best for**: LangChain-heavy applications with human-in-the-loop workflows

### Langfuse

**Strengths**:
- **Open source + cloud**: Self-host or use managed service
- **Cost analytics**: Detailed token usage and cost breakdowns
- **Prompt management**: Version control for prompts with A/B testing

**Best for**: Cost-conscious teams wanting open-source flexibility

## Implementation Patterns

### Pattern 1: Arize Phoenix Setup and Tracing

**When to use**: Starting with Phoenix for framework-agnostic evaluation

```bash
# Installation
pip install arize-phoenix openinference-instrumentation-openai

# Start Phoenix server (local)
python -m phoenix.server.main serve

# Or use Docker
docker run -p 6006:6006 arizephoenix/phoenix:latest
```

**Basic OpenAI tracing**:

```python
from phoenix.otel import register
from openinference.instrumentation.openai import OpenAIInstrumentor
from openai import OpenAI

# Configure Phoenix endpoint
tracer_provider = register(
    project_name="my-llm-app",
    endpoint="http://localhost:6006/v1/traces",
)

# Auto-instrument OpenAI
OpenAIInstrumentor().instrument(tracer_provider=tracer_provider)

# Use OpenAI normally - traces sent automatically
client = OpenAI()
response = client.chat.completions.create(
    model="gpt-4-turbo-preview",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the capital of France?"},
    ],
)

print(response.choices[0].message.content)
# Phoenix UI now shows this trace at http://localhost:6006
```

**LangChain tracing**:

```python
from phoenix.otel import register
from openinference.instrumentation.langchain import LangChainInstrumentor
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser

# Setup Phoenix
tracer_provider = register(project_name="langchain-app")

# Auto-instrument LangChain
LangChainInstrumentor().instrument(tracer_provider=tracer_provider)

# Build LangChain pipeline
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant."),
    ("user", "{input}"),
])

llm = ChatOpenAI(model="gpt-4-turbo-preview")
chain = prompt | llm | StrOutputParser()

# Run - automatically traced
result = chain.invoke({"input": "What is the capital of France?"})
print(result)
```

**LlamaIndex tracing**:

```python
from phoenix.otel import register
from openinference.instrumentation.llama_index import LlamaIndexInstrumentor
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader

# Setup Phoenix
tracer_provider = register(project_name="llamaindex-app")

# Auto-instrument LlamaIndex
LlamaIndexInstrumentor().instrument(tracer_provider=tracer_provider)

# Build RAG system
documents = SimpleDirectoryReader("data").load_data()
index = VectorStoreIndex.from_documents(documents)

# Query - automatically traced
query_engine = index.as_query_engine()
response = query_engine.query("What is the main topic?")
print(response)
```

### Pattern 2: Phoenix Evaluations

**When to use**: Running automated evaluations on traces

```python
import phoenix as px
from phoenix.evals import (
    HallucinationEvaluator,
    RelevanceEvaluator,
    ToxicityEvaluator,
    OpenAIModel,
)

# Launch Phoenix and get session
session = px.launch_app()

# Get traces from Phoenix
traces_df = px.Client().get_trace_dataset()

# Configure evaluator model
eval_model = OpenAIModel(model="gpt-4-turbo-preview")

# Run hallucination evaluation
hallucination_eval = HallucinationEvaluator(eval_model)
hallucination_results = hallucination_eval.evaluate(
    dataframe=traces_df,
    query_column="input",
    response_column="output",
    reference_column="retrieved_context",
)

# Run relevance evaluation
relevance_eval = RelevanceEvaluator(eval_model)
relevance_results = relevance_eval.evaluate(
    dataframe=traces_df,
    query_column="input",
    document_column="retrieved_context",
)

# Run toxicity evaluation
toxicity_eval = ToxicityEvaluator(eval_model)
toxicity_results = toxicity_eval.evaluate(
    dataframe=traces_df,
    text_column="output",
)

# Combine results
traces_df["hallucination_score"] = hallucination_results["label"]
traces_df["relevance_score"] = relevance_results["label"]
traces_df["toxicity_score"] = toxicity_results["label"]

# Upload results back to Phoenix
px.Client().log_evaluations(traces_df)

# View in Phoenix UI
print(f"View results at {session.url}")
```

**Custom Phoenix evaluators**:

```python
from phoenix.evals import LLMEvaluator, OpenAIModel
from phoenix.evals.models import EvalCriteria

# Define custom evaluation criteria
code_quality_template = """
You are evaluating code quality. Rate the following code on:
1. Correctness
2. Efficiency
3. Readability

Code:
{code}

Provide a score from 1-5 where:
1 = Poor
3 = Acceptable
5 = Excellent
"""

# Create custom evaluator
code_quality_eval = LLMEvaluator(
    model=OpenAIModel(model="gpt-4-turbo-preview"),
    template=code_quality_template,
    rails=["1", "2", "3", "4", "5"],  # Valid outputs
)

# Run evaluation
code_df = traces_df[traces_df["task_type"] == "code_generation"]
code_quality_results = code_quality_eval.evaluate(
    dataframe=code_df,
    code_column="output",
)

# Analyze results
print(f"Average code quality: {code_quality_results['score'].mean():.2f}")
print(f"Low quality outputs: {(code_quality_results['score'] <= 2).sum()}")
```

### Pattern 3: Phoenix Datasets and Experiments

**When to use**: Systematic evaluation across model versions or prompts

```python
import phoenix as px
from phoenix.experiments import run_experiment
from openai import OpenAI

# Create dataset
dataset = px.Client().create_dataset(
    dataset_name="customer-support-qa",
    description="Customer support question answering",
)

# Add examples
examples = [
    {
        "input": "How do I reset my password?",
        "expected_output": "Visit the account settings page and click 'Reset Password'.",
    },
    {
        "input": "What's your refund policy?",
        "expected_output": "We offer 30-day money-back guarantee on all products.",
    },
    # ... more examples
]

for example in examples:
    dataset.add_example(**example)

# Define task function
def qa_task(input_text: str, model: str = "gpt-4-turbo-preview") -> str:
    """Generate answer using specified model."""
    client = OpenAI()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a customer support assistant."},
            {"role": "user", "content": input_text},
        ],
    )
    return response.choices[0].message.content

# Run experiment with GPT-4
experiment_gpt4 = run_experiment(
    dataset=dataset,
    task=lambda example: qa_task(example["input"], model="gpt-4-turbo-preview"),
    experiment_name="gpt4-customer-support",
)

# Run experiment with GPT-3.5
experiment_gpt35 = run_experiment(
    dataset=dataset,
    task=lambda example: qa_task(example["input"], model="gpt-3.5-turbo"),
    experiment_name="gpt35-customer-support",
)

# Compare results
from phoenix.evals import RelevanceEvaluator

eval_model = OpenAIModel(model="gpt-4-turbo-preview")
relevance_eval = RelevanceEvaluator(eval_model)

# Evaluate both experiments
gpt4_scores = relevance_eval.evaluate(experiment_gpt4.results)
gpt35_scores = relevance_eval.evaluate(experiment_gpt35.results)

print(f"GPT-4 avg relevance: {gpt4_scores['score'].mean():.2f}")
print(f"GPT-3.5 avg relevance: {gpt35_scores['score'].mean():.2f}")

# View detailed comparison in Phoenix UI
```

### Pattern 4: Braintrust Integration

**When to use**: Leveraging fast search and prompt playground

```python
import braintrust
from braintrust import init_logger

# Initialize Braintrust
project = braintrust.init(
    project="customer-support-qa",
    api_key="your-api-key",
)

# Log experiment
experiment = project.experiment(
    name="gpt4-vs-gpt35",
    dataset="customer-support-v1",
)

# Define evaluation function
def evaluate_response(input_text, expected, actual):
    """Custom scoring function."""
    # Exact match
    exact_match = 1.0 if actual.strip() == expected.strip() else 0.0

    # Use Braintrust's built-in scorers
    from braintrust.scorer import Factuality

    factuality = Factuality()
    fact_score = factuality(output=actual, expected=expected)

    return {
        "exact_match": exact_match,
        "factuality": fact_score,
    }

# Run evaluation
for example in dataset:
    # Generate response
    response = qa_task(example["input"])

    # Log to Braintrust
    experiment.log(
        input=example["input"],
        output=response,
        expected=example["expected_output"],
        scores=evaluate_response(
            example["input"],
            example["expected_output"],
            response,
        ),
        metadata={
            "model": "gpt-4-turbo-preview",
            "timestamp": datetime.now().isoformat(),
        },
    )

# Get experiment summary
summary = experiment.summarize()
print(f"Average factuality: {summary['factuality']:.2f}")
print(f"Exact match rate: {summary['exact_match']:.2f}")

# Fast search (Braintrust's 86x advantage)
search_results = project.search(
    query="password reset",
    limit=10,
    filter={"scores.factuality": {"$gte": 0.8}},
)

for result in search_results:
    print(f"Input: {result['input']}")
    print(f"Output: {result['output']}")
    print(f"Factuality: {result['scores']['factuality']}")
```

### Pattern 5: Cost Tracking Across Frameworks

**When to use**: Monitoring and optimizing LLM costs

```python
import phoenix as px
from openai import OpenAI
from datetime import datetime, timedelta

# Setup Phoenix with cost tracking
tracer_provider = px.otel.register(
    project_name="cost-tracking",
    endpoint="http://localhost:6006/v1/traces",
)

# Track costs in spans
from opentelemetry import trace

def track_llm_call(model: str, input_tokens: int, output_tokens: int):
    """Add cost metadata to current span."""
    # Pricing as of 2025 (per 1M tokens)
    PRICING = {
        "gpt-4-turbo-preview": {"input": 10.00, "output": 30.00},
        "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
        "claude-3-opus": {"input": 15.00, "output": 75.00},
        "claude-3-sonnet": {"input": 3.00, "output": 15.00},
    }

    pricing = PRICING.get(model, {"input": 0, "output": 0})

    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    total_cost = input_cost + output_cost

    # Add to current span
    span = trace.get_current_span()
    span.set_attribute("llm.token_count.prompt", input_tokens)
    span.set_attribute("llm.token_count.completion", output_tokens)
    span.set_attribute("llm.cost.input", input_cost)
    span.set_attribute("llm.cost.output", output_cost)
    span.set_attribute("llm.cost.total", total_cost)

    return total_cost

# Use with OpenAI
client = OpenAI()

def generate_with_cost_tracking(prompt: str, model: str = "gpt-4-turbo-preview"):
    """Generate response and track costs."""
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )

    # Extract token counts
    usage = response.usage
    cost = track_llm_call(model, usage.prompt_tokens, usage.completion_tokens)

    print(f"Cost: ${cost:.4f}")

    return response.choices[0].message.content

# Generate cost reports from Phoenix
px_client = px.Client()

# Get traces from last 24 hours
end_time = datetime.now()
start_time = end_time - timedelta(days=1)

traces = px_client.get_trace_dataset(
    start_time=start_time,
    end_time=end_time,
)

# Calculate total costs
total_cost = traces["llm.cost.total"].sum()
cost_by_model = traces.groupby("llm.model_name")["llm.cost.total"].sum()

print(f"Total cost (24h): ${total_cost:.2f}")
print("\nCost by model:")
for model, cost in cost_by_model.items():
    print(f"  {model}: ${cost:.2f}")

# Identify expensive queries
expensive_queries = traces.nlargest(10, "llm.cost.total")
print("\nMost expensive queries:")
for _, row in expensive_queries.iterrows():
    print(f"  Cost: ${row['llm.cost.total']:.4f} | Input: {row['input'][:50]}...")
```

## Code Examples

### Example 1: Multi-Framework Evaluation Pipeline

```python
from typing import List, Dict, Any
import phoenix as px
from phoenix.evals import HallucinationEvaluator, OpenAIModel
from langfuse import Langfuse
from openai import OpenAI
import json

class UnifiedEvaluationPipeline:
    """Evaluation pipeline supporting multiple frameworks."""

    def __init__(
        self,
        phoenix_endpoint: str = "http://localhost:6006",
        langfuse_public_key: str = None,
        langfuse_secret_key: str = None,
    ):
        # Setup Phoenix
        self.px_client = px.Client(endpoint=phoenix_endpoint)

        # Setup Langfuse (optional)
        self.langfuse = None
        if langfuse_public_key and langfuse_secret_key:
            self.langfuse = Langfuse(
                public_key=langfuse_public_key,
                secret_key=langfuse_secret_key,
            )

        # Setup OpenAI
        self.openai_client = OpenAI()

        # Setup evaluators
        self.eval_model = OpenAIModel(model="gpt-4-turbo-preview")
        self.hallucination_eval = HallucinationEvaluator(self.eval_model)

    def evaluate_dataset(
        self,
        dataset: List[Dict[str, Any]],
        model: str = "gpt-4-turbo-preview",
        system_prompt: str = "You are a helpful assistant.",
    ) -> Dict[str, Any]:
        """
        Evaluate dataset across all configured frameworks.

        Args:
            dataset: List of {input, expected_output, context} dicts
            model: OpenAI model name
            system_prompt: System prompt for generation

        Returns:
            Evaluation results with framework-specific metrics
        """
        results = {
            "model": model,
            "total_examples": len(dataset),
            "phoenix_results": [],
            "langfuse_results": [],
            "summary": {},
        }

        for idx, example in enumerate(dataset):
            # Generate response
            response = self.openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": example["input"]},
                ],
            )

            output = response.choices[0].message.content
            usage = response.usage

            # Log to Phoenix
            phoenix_result = self._log_to_phoenix(
                input_text=example["input"],
                output=output,
                expected=example.get("expected_output"),
                context=example.get("context"),
                usage=usage,
                model=model,
            )
            results["phoenix_results"].append(phoenix_result)

            # Log to Langfuse (if configured)
            if self.langfuse:
                langfuse_result = self._log_to_langfuse(
                    input_text=example["input"],
                    output=output,
                    expected=example.get("expected_output"),
                    usage=usage,
                    model=model,
                )
                results["langfuse_results"].append(langfuse_result)

            # Progress
            if (idx + 1) % 10 == 0:
                print(f"Processed {idx + 1}/{len(dataset)} examples")

        # Calculate summary metrics
        results["summary"] = self._calculate_summary(results)

        return results

    def _log_to_phoenix(self, input_text, output, expected, context, usage, model):
        """Log result to Phoenix and run evaluations."""
        # Create trace manually (if not using auto-instrumentation)
        trace_data = {
            "input": input_text,
            "output": output,
            "expected": expected,
            "context": context,
            "model": model,
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
        }

        # Run hallucination eval if context provided
        hallucination_score = None
        if context:
            eval_result = self.hallucination_eval.evaluate_single(
                query=input_text,
                response=output,
                reference=context,
            )
            hallucination_score = eval_result["label"]

        trace_data["hallucination_score"] = hallucination_score

        return trace_data

    def _log_to_langfuse(self, input_text, output, expected, usage, model):
        """Log result to Langfuse."""
        generation = self.langfuse.generation(
            name="qa-generation",
            model=model,
            input=input_text,
            output=output,
            metadata={"expected": expected},
            usage={
                "input": usage.prompt_tokens,
                "output": usage.completion_tokens,
                "total": usage.total_tokens,
            },
        )

        return {
            "trace_id": generation.trace_id,
            "generation_id": generation.id,
        }

    def _calculate_summary(self, results):
        """Calculate aggregate metrics."""
        phoenix_results = results["phoenix_results"]

        # Hallucination rate
        hallucination_scores = [
            r["hallucination_score"]
            for r in phoenix_results
            if r["hallucination_score"] is not None
        ]
        hallucination_rate = (
            sum(1 for s in hallucination_scores if s == "hallucinated")
            / len(hallucination_scores)
            if hallucination_scores
            else 0
        )

        # Token statistics
        total_prompt_tokens = sum(r["prompt_tokens"] for r in phoenix_results)
        total_completion_tokens = sum(r["completion_tokens"] for r in phoenix_results)

        return {
            "hallucination_rate": hallucination_rate,
            "total_prompt_tokens": total_prompt_tokens,
            "total_completion_tokens": total_completion_tokens,
            "avg_prompt_tokens": total_prompt_tokens / len(phoenix_results),
            "avg_completion_tokens": total_completion_tokens / len(phoenix_results),
        }

    def export_results(self, results, output_path: str):
        """Export results to JSON."""
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)

        print(f"Results exported to {output_path}")

# Usage
pipeline = UnifiedEvaluationPipeline(
    phoenix_endpoint="http://localhost:6006",
    langfuse_public_key="pk-xxx",
    langfuse_secret_key="sk-xxx",
)

dataset = [
    {
        "input": "What is the capital of France?",
        "expected_output": "Paris",
        "context": "France is a country in Europe. Its capital city is Paris.",
    },
    # ... more examples
]

results = pipeline.evaluate_dataset(
    dataset=dataset,
    model="gpt-4-turbo-preview",
    system_prompt="You are a geography expert.",
)

print(f"Hallucination rate: {results['summary']['hallucination_rate']:.2%}")
print(f"Avg tokens per query: {results['summary']['avg_prompt_tokens']:.0f}")

pipeline.export_results(results, "evaluation_results.json")
```

### Example 2: Phoenix Self-Hosted Production Setup

```python
# docker-compose.yml for production Phoenix deployment
"""
version: '3.8'

services:
  phoenix:
    image: arizephoenix/phoenix:latest
    ports:
      - "6006:6006"
    environment:
      - PHOENIX_SQL_DATABASE_URL=postgresql://user:pass@postgres:5432/phoenix
      - PHOENIX_WORKING_DIR=/data
    volumes:
      - phoenix-data:/data
    depends_on:
      - postgres
    restart: unless-stopped

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=phoenix
    volumes:
      - postgres-data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  phoenix-data:
  postgres-data:
"""

# Application code with production Phoenix
from phoenix.otel import register
from openinference.instrumentation.openai import OpenAIInstrumentor
import os

# Configure production Phoenix endpoint
PHOENIX_ENDPOINT = os.getenv("PHOENIX_ENDPOINT", "http://phoenix:6006/v1/traces")

tracer_provider = register(
    project_name="production-app",
    endpoint=PHOENIX_ENDPOINT,
)

# Auto-instrument
OpenAIInstrumentor().instrument(tracer_provider=tracer_provider)

# Your application code runs as normal
# All traces automatically sent to self-hosted Phoenix
```

## Anti-Patterns

### Anti-Pattern 1: Framework Lock-In
**Wrong**: Building everything for one framework
```python
# BAD: Tightly coupled to LangSmith
from langsmith import Client

def evaluate_model():
    client = Client()  # Only works with LangSmith
    # ... LangSmith-specific code
```

**Right**: Use OpenTelemetry for portability
```python
# GOOD: Framework-agnostic tracing
from phoenix.otel import register
from opentelemetry import trace

tracer_provider = register(project_name="my-app")
tracer = trace.get_tracer(__name__)

# Works with Phoenix, or any OTLP-compatible backend
with tracer.start_as_current_span("llm-call") as span:
    span.set_attribute("llm.model", "gpt-4")
    # ... your code
```

### Anti-Pattern 2: Not Tracking Costs
**Wrong**: Ignoring cost implications
```python
# BAD: No cost tracking
for prompt in large_dataset:
    expensive_model(prompt)  # Could cost $$$
```

**Right**: Monitor costs in real-time
```python
# GOOD: Track and alert on costs
cost_tracker = CostTracker(budget_limit=100.00)

for prompt in large_dataset:
    if cost_tracker.remaining_budget < 10.00:
        # Switch to cheaper model or stop
        model = "gpt-3.5-turbo"

    response = model(prompt)
    cost_tracker.log_cost(response.usage)
```

### Anti-Pattern 3: Manual Instrumentation Everywhere
**Wrong**: Manually logging every LLM call
```python
# BAD: Manual tracing
def call_llm(prompt):
    start = time.time()
    response = openai.chat.completions.create(...)
    duration = time.time() - start

    log_to_framework({
        "prompt": prompt,
        "response": response,
        "duration": duration,
    })  # Tedious and error-prone
```

**Right**: Use auto-instrumentation
```python
# GOOD: Auto-instrumentation
from openinference.instrumentation.openai import OpenAIInstrumentor

OpenAIInstrumentor().instrument()

# All OpenAI calls automatically traced
response = openai.chat.completions.create(...)
# No manual logging needed!
```

## Related Skills

- `llm-benchmarks-evaluation.md`: Standard benchmarks (MMLU, HumanEval) for offline evaluation
- `llm-as-judge.md`: Using LLMs to evaluate LLM outputs with Prometheus and G-Eval
- `rag-evaluation-metrics.md`: RAGAS metrics for RAG systems with framework integration
- `custom-llm-evaluation.md`: Domain-specific evaluation metrics and continuous evaluation
- `dspy-evaluation.md`: DSPy-specific evaluation patterns and metric functions

## Summary

LLM evaluation frameworks provide production-grade monitoring and evaluation:

**Key Takeaways**:
1. **Arize Phoenix**: Best for self-hosted, framework-agnostic tracing with OpenTelemetry
2. **Braintrust**: Best for fast search (86x) and API-driven workflows
3. **LangSmith**: Best for LangChain applications with human feedback
4. **Langfuse**: Best for open-source + cost tracking

**Phoenix Deep Dive**:
- Auto-instrumentation for OpenAI, LangChain, LlamaIndex, DSPy
- Built-in evaluators: Hallucination, Relevance, Toxicity, Q&A correctness
- Dataset and experiment management for systematic evaluation
- Self-hostable with PostgreSQL backend for production
- Real-time dashboards and embedding visualization

**Best Practices**:
- Use OpenTelemetry for portability across frameworks
- Track costs per model, user, or project
- Auto-instrument instead of manual logging
- Run continuous evals on production traffic
- Self-host for data privacy and control (Phoenix, Langfuse)

**When to combine with other skills**:
- Use `llm-benchmarks-evaluation.md` for offline capability testing
- Use `llm-as-judge.md` when automated metrics don't capture quality
- Use `rag-evaluation-metrics.md` for RAG-specific metrics (RAGAS)
- Use `custom-llm-evaluation.md` for domain-specific or safety evaluations
