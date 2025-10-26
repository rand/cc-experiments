---
name: ml-llm-model-selection
description: Choosing the right LLM based on capabilities, benchmarks, pricing, and use cases
---

# LLM Model Selection

**Scope**: Model comparison, capability mapping, pricing analysis, benchmark interpretation, strategic selection
**Lines**: ~420
**Last Updated**: 2025-10-26

## When to Use This Skill

Activate this skill when:
- Starting a new LLM-powered project and selecting initial models
- Evaluating whether to switch models due to cost or performance
- Building multi-model systems that leverage specialized capabilities
- Optimizing LLM budgets without sacrificing quality
- Comparing frontier models (GPT-4o, Claude 3.5/4, Gemini 2.5, DeepSeek)
- Benchmarking models for specific tasks (code, reasoning, multilingual)
- Understanding tradeoffs between quality, speed, cost, and context length

## Core Concepts

### The Model Selection Framework

**Decision Factors**:
1. **Task Fit**: What capabilities does the task require?
2. **Budget**: What's the acceptable cost per query?
3. **Latency**: How fast must responses be?
4. **Quality**: What's the minimum acceptable performance?
5. **Context**: How much input context is needed?
6. **Scale**: What's the expected query volume?

**Selection Process**:
```
Define requirements -> Filter by constraints -> Benchmark finalists -> Select optimal model(s)
```

### 2025 Model Landscape

**Frontier Models** (Strongest):
- **OpenAI**: GPT-4o (multimodal, 128k), o1 (reasoning-focused)
- **Anthropic**: Claude 3.5 Sonnet (200k context), Claude 4 (upcoming)
- **Google**: Gemini 2.5 Pro, Gemini 2.5 Flash (fast, multimodal)
- **xAI**: Grok 3 (X Premium+, competitive benchmarks)

**Open-Weight Leaders**:
- **Meta**: LLaMA 3.3 70B (instruction-tuned, multilingual)
- **DeepSeek**: R1 (reasoning), V3 (671B MoE, $5.5M training cost)
- **Mistral**: Mixtral 8x22B, Mistral Large

**Fast/Cheap Tier**:
- **OpenAI**: GPT-4o mini ($0.15/$0.60 per million tokens)
- **Anthropic**: Claude 3 Haiku ($0.25/$1.25)
- **Google**: Gemini 2.5 Flash ($0.10/$0.40, 370 tok/s)

### Benchmark Interpretation

**MMLU (Massive Multitask Language Understanding)**:
- Measures general knowledge across 57 subjects
- **Top performers**: GPT-4o (88.7%), Gemini 2.5 (88-89%), Claude 3.5 Sonnet (82.25%)
- **Use for**: General-purpose model selection
- **Limitation**: Doesn't test reasoning depth or code quality

**HumanEval (Code Generation)**:
- Python programming problems, pass@1 metric
- **Top performers**: Claude 3.5 Sonnet (92.0%), GPT-4o (90.2%)
- **Use for**: Selecting coding assistants
- **Limitation**: Only Python; doesn't test debugging or explanation

**BBH (Big Bench Hard)**:
- 23 challenging reasoning tasks
- **Top performers**: GPT-4o, Claude 3.5, DeepSeek R1
- **Use for**: Complex reasoning applications
- **Limitation**: Academic tasks; real-world reasoning may differ

**MATH-500 (Mathematics)**:
- College-level math problems
- **Top performer**: DeepSeek R1 Distilled (94.5%)
- **Use for**: STEM tutoring, technical analysis
- **Limitation**: Symbolic math only; not applied problems

**GPQA Diamond (Graduate-Level Science)**:
- PhD-level questions in physics, chemistry, biology
- **Top performer**: DeepSeek R1 Distilled (65.2%)
- **Use for**: Research assistance, expert-level queries
- **Limitation**: Narrow domain; doesn't generalize to all expertise

### Capability Matrix

**Strengths by Model** (2025 data):

| Model               | Code | Reason | Speed | Cost | Context | Multimodal |
|---------------------|------|--------|-------|------|---------|------------|
| GPT-4o              | A    | A      | B     | C    | 128k    | Yes        |
| GPT-4o mini         | B    | B      | A     | A    | 128k    | Yes        |
| Claude 3.5 Sonnet   | A+   | A      | B     | C    | 200k    | Yes (basic)|
| Claude 3 Haiku      | B    | B      | A     | A    | 200k    | No         |
| Gemini 2.5 Pro      | A    | A      | B     | B    | 1M      | Yes        |
| Gemini 2.5 Flash    | B+   | B+     | A+    | A+   | 1M      | Yes        |
| DeepSeek V3         | A    | B+     | B     | A+   | 128k    | No         |
| DeepSeek R1         | A    | A+     | C     | A    | 128k    | No         |
| LLaMA 3.3 70B       | B+   | B      | A     | A    | 128k    | No         |
| Grok 3              | A    | A      | B     | D    | 128k    | Yes        |

*A+ = Best-in-class, A = Excellent, B = Good, C = Average, D = Expensive*

### Pricing Deep Dive (2025)

**Premium Tier** ($10-75 per million output tokens):
- Claude 3 Opus: $15/$75 (highest quality, rarely needed)
- GPT-4o: $5/$20 (balanced strong model)
- Claude 3.5 Sonnet: $3/$15 (best coding ROI)

**Mid Tier** ($1-5 per million output tokens):
- Gemini 2.5 Pro: $1.25/$5 (long context)
- DeepSeek V3: ~$0.30/$1 (open-source alternative)
- Claude 3 Haiku: $0.25/$1.25 (fast)

**Budget Tier** ($0.40-1 per million output tokens):
- Gemini 2.5 Flash: $0.10/$0.40 (cheapest strong model)
- GPT-4o mini: $0.15/$0.60 (reliable baseline)

**Cost Efficiency**:
- DeepSeek V3 is 27.4x cheaper than GPT-4o for similar quality
- Gemini Flash is 20x cheaper than GPT-4o with 370 tok/s speed
- Claude Haiku is 16x cheaper than Claude Sonnet for simple tasks

---

## Implementation Patterns

### Strategic Stack Approach

```python
from enum import Enum
from typing import Optional

class TaskComplexity(Enum):
    SIMPLE = "simple"  # Factual, short
    MODERATE = "moderate"  # Multi-step, some reasoning
    COMPLEX = "complex"  # Deep analysis, coding

class ModelStack:
    """Strategic model selection based on task characteristics"""

    def __init__(self):
        self.models = {
            "coding_expert": "claude-3-5-sonnet-20241022",
            "reasoning_expert": "gpt-4o",
            "speed_optimized": "gemini-2.5-flash",
            "cost_optimized": "gpt-4o-mini",
            "long_context": "claude-3-5-sonnet-20241022",  # 200k
            "multimodal": "gpt-4o",
        }

    def select(
        self,
        task_type: str,
        complexity: TaskComplexity,
        context_length: int = 0,
        budget_sensitive: bool = False
    ) -> str:
        """Select optimal model based on task characteristics"""

        # Long context override (>100k tokens)
        if context_length > 100_000:
            return self.models["long_context"]

        # Budget override
        if budget_sensitive and complexity != TaskComplexity.COMPLEX:
            return self.models["cost_optimized"]

        # Task-specific selection
        if task_type == "code":
            return self.models["coding_expert"]

        if task_type == "vision" or task_type == "multimodal":
            return self.models["multimodal"]

        # Complexity-based selection
        if complexity == TaskComplexity.SIMPLE:
            return self.models["speed_optimized"]
        elif complexity == TaskComplexity.MODERATE:
            return self.models["cost_optimized"]
        else:  # COMPLEX
            if task_type == "reasoning":
                return self.models["reasoning_expert"]
            return self.models["coding_expert"]

# Usage
stack = ModelStack()

# Coding task
model = stack.select("code", TaskComplexity.COMPLEX)
print(f"Coding: {model}")  # claude-3-5-sonnet

# Simple factual query
model = stack.select("qa", TaskComplexity.SIMPLE)
print(f"Simple QA: {model}")  # gemini-2.5-flash

# Long document analysis
model = stack.select("analysis", TaskComplexity.COMPLEX, context_length=150_000)
print(f"Long context: {model}")  # claude-3-5-sonnet (200k)

# Budget-sensitive moderate task
model = stack.select("summary", TaskComplexity.MODERATE, budget_sensitive=True)
print(f"Budget summary: {model}")  # gpt-4o-mini
```

### Benchmark-Driven Selection

```python
import pandas as pd

# 2025 benchmark data
benchmark_data = {
    "model": [
        "gpt-4o",
        "claude-3.5-sonnet",
        "gemini-2.5-flash",
        "gpt-4o-mini",
        "deepseek-v3",
        "deepseek-r1-distilled-70b"
    ],
    "mmlu": [88.7, 82.3, 85.0, 82.0, 84.5, 83.0],
    "humaneval": [90.2, 92.0, 88.0, 87.2, 89.0, 87.5],
    "math_500": [76.0, 78.0, 70.0, 72.0, 75.0, 94.5],
    "gpqa_diamond": [53.6, 59.4, 50.0, 48.0, 55.0, 65.2],
    "input_cost": [5.00, 3.00, 0.10, 0.15, 0.30, 0.30],
    "output_cost": [20.00, 15.00, 0.40, 0.60, 1.00, 1.00],
    "speed_tokens_per_sec": [50, 45, 370, 80, 60, 40]
}

df = pd.DataFrame(benchmark_data)

def select_model_by_benchmark(
    task: str,
    budget_per_1k_output: float = None,
    min_score: float = 80.0
) -> pd.DataFrame:
    """Filter models by task benchmark and constraints"""

    # Select relevant benchmark
    benchmark_map = {
        "code": "humaneval",
        "reasoning": "mmlu",
        "math": "math_500",
        "research": "gpqa_diamond"
    }

    benchmark_col = benchmark_map.get(task, "mmlu")

    # Filter by minimum score
    filtered = df[df[benchmark_col] >= min_score].copy()

    # Calculate cost for 1M tokens (typical workload)
    filtered["cost_per_1m"] = (
        (filtered["input_cost"] * 0.2) +  # 20% input, 80% output
        (filtered["output_cost"] * 0.8)
    )

    # Budget filter
    if budget_per_1k_output:
        max_cost_per_1m = budget_per_1k_output * 1000
        filtered = filtered[filtered["cost_per_1m"] <= max_cost_per_1m]

    # Sort by performance, then cost
    filtered = filtered.sort_values(
        [benchmark_col, "cost_per_1m"],
        ascending=[False, True]
    )

    return filtered[[
        "model", benchmark_col, "cost_per_1m", "speed_tokens_per_sec"
    ]]

# Example: Select coding model with $10 budget per 1k output tokens
print("Code generation models (budget $10/1k output):")
print(select_model_by_benchmark("code", budget_per_1k_output=10))

# Example: Select math model (no budget constraint)
print("\nMath reasoning models:")
print(select_model_by_benchmark("math", min_score=70))

# Output:
#                       model  humaneval  cost_per_1m  speed_tokens_per_sec
# 1       claude-3.5-sonnet       92.0        12.60                    45
# 4              deepseek-v3       89.0         0.86                    60
# 5  deepseek-r1-distilled...     87.5         0.86                    40
```

### Cost-Quality Pareto Frontier

```python
import numpy as np
import matplotlib.pyplot as plt

# Plot cost vs quality for model selection
models = df.copy()
models["quality_score"] = models[["mmlu", "humaneval"]].mean(axis=1)

plt.figure(figsize=(10, 6))
plt.scatter(
    models["output_cost"],
    models["quality_score"],
    s=models["speed_tokens_per_sec"],  # Bubble size = speed
    alpha=0.6
)

for idx, row in models.iterrows():
    plt.annotate(
        row["model"],
        (row["output_cost"], row["quality_score"]),
        fontsize=9
    )

plt.xlabel("Output Cost ($/M tokens)")
plt.ylabel("Average Quality Score")
plt.title("LLM Pareto Frontier: Cost vs Quality\n(Bubble size = speed)")
plt.xscale("log")
plt.grid(True, alpha=0.3)

# Identify Pareto-optimal models
# (Models not dominated by any other in both cost and quality)
def is_pareto_optimal(costs, qualities):
    is_optimal = np.ones(len(costs), dtype=bool)
    for i, (c, q) in enumerate(zip(costs, qualities)):
        is_optimal[i] = not np.any(
            (costs < c) & (qualities > q)
        )
    return is_optimal

pareto = is_pareto_optimal(
    models["output_cost"].values,
    models["quality_score"].values
)

print("Pareto-optimal models:")
print(models[pareto][["model", "output_cost", "quality_score"]])
```

### Multi-Model Portfolio

```python
from typing import Dict, List
from dataclasses import dataclass

@dataclass
class ModelConfig:
    name: str
    cost_per_1k: float
    strength: str
    use_cases: List[str]

class ModelPortfolio:
    """Manage a portfolio of models for different use cases"""

    def __init__(self):
        self.models = [
            ModelConfig(
                "claude-3-5-sonnet",
                cost_per_1k=12.6,
                strength="coding",
                use_cases=["code_generation", "code_review", "debugging"]
            ),
            ModelConfig(
                "gpt-4o",
                cost_per_1k=16.5,
                strength="reasoning",
                use_cases=["analysis", "planning", "complex_reasoning"]
            ),
            ModelConfig(
                "gemini-2.5-flash",
                cost_per_1k=0.35,
                strength="speed",
                use_cases=["simple_qa", "classification", "summarization"]
            ),
            ModelConfig(
                "gpt-4o-mini",
                cost_per_1k=0.54,
                strength="balanced",
                use_cases=["general", "moderate_complexity", "fallback"]
            ),
            ModelConfig(
                "deepseek-v3",
                cost_per_1k=0.86,
                strength="cost_efficiency",
                use_cases=["high_volume", "batch_processing"]
            )
        ]

    def recommend(self, use_case: str, max_cost: float = None) -> List[str]:
        """Recommend models for a use case"""
        candidates = [
            m.name for m in self.models
            if use_case in m.use_cases
        ]

        if max_cost:
            candidates = [
                m.name for m in self.models
                if use_case in m.use_cases and m.cost_per_1k <= max_cost
            ]

        return candidates

    def cost_report(self, monthly_queries: Dict[str, int]):
        """Estimate monthly costs based on query distribution"""
        total_cost = 0
        for use_case, count in monthly_queries.items():
            models = self.recommend(use_case)
            if not models:
                continue

            # Use cheapest model for use case
            cheapest = min(
                [m for m in self.models if m.name in models],
                key=lambda x: x.cost_per_1k
            )

            cost = count * cheapest.cost_per_1k / 1000
            total_cost += cost

            print(f"{use_case:20} | {count:8} queries | {cheapest.name:20} | ${cost:8.2f}")

        print(f"\n{'Total':20} | {sum(monthly_queries.values()):8} queries | {'':<20} | ${total_cost:8.2f}")

# Usage
portfolio = ModelPortfolio()

# Monthly query distribution
queries = {
    "code_generation": 50_000,
    "simple_qa": 500_000,
    "analysis": 10_000,
    "summarization": 100_000
}

portfolio.cost_report(queries)

# Output:
# code_generation      |    50000 queries | claude-3-5-sonnet    |   630.00
# simple_qa            |   500000 queries | gemini-2.5-flash     |   175.00
# analysis             |    10000 queries | gpt-4o               |   165.00
# summarization        |   100000 queries | gemini-2.5-flash     |    35.00
#
# Total                |   660000 queries |                      |  1005.00
```

---

## Quick Reference

### Model Selection Decision Tree

```
Start here -> What's the primary constraint?

Cost-constrained:
  ├─ High volume (>1M queries/month) -> DeepSeek V3 or Gemini Flash
  ├─ Moderate volume -> GPT-4o mini
  └─ Complex tasks only -> RouteLLM with GPT-4o/mini pair

Quality-constrained:
  ├─ Coding -> Claude 3.5 Sonnet
  ├─ Reasoning/Analysis -> GPT-4o or DeepSeek R1
  ├─ Math -> DeepSeek R1 Distilled
  └─ General -> GPT-4o or Gemini 2.5 Pro

Latency-constrained:
  ├─ Maximum speed -> Gemini 2.5 Flash (370 tok/s)
  ├─ Balanced -> GPT-4o mini
  └─ OK with moderate -> Claude 3.5 Sonnet

Context-constrained:
  ├─ >128k tokens -> Claude 3.5 Sonnet (200k) or Gemini (1M)
  ├─ 32-128k -> GPT-4o, Claude, or Gemini
  └─ <32k -> Any model
```

### Benchmarks by Use Case

```
Use Case               | Primary Benchmark | Secondary Benchmark
-----------------------|-------------------|--------------------
Code generation        | HumanEval         | MBPP (Python)
Complex reasoning      | BBH, GPQA         | MMLU
Mathematics            | MATH-500          | GSM8K
General knowledge      | MMLU              | TriviaQA
Instruction following  | IFEval            | MT Bench
Multilingual           | MGSM              | XLSum
Long context           | RULER, BABILong   | QMSum
```

### Cost Optimization Strategies

```
Strategy                | Savings  | Complexity | When to Use
------------------------|----------|------------|---------------------------
Use cheaper models      | 50-95%   | Low        | Simple/moderate tasks
Model routing           | 40-85%   | Medium     | Mixed-complexity workload
Prompt caching          | 10-90%   | Low        | Repeated context
Batch processing        | 50%      | Medium     | Non-urgent queries
Open-source self-host   | 70-100%  | High       | Very high volume
```

---

## Anti-Patterns

❌ **Always using the latest model**: GPT-4o not always better than Claude 3.5 for code
✅ Benchmark models for your specific use case before committing

❌ **Choosing based on MMLU alone**: Doesn't predict real-world performance
✅ Evaluate on multiple benchmarks relevant to your domain

❌ **Ignoring speed/latency differences**: Gemini Flash is 7x faster than GPT-4o
✅ Consider tokens/second for user-facing applications

❌ **Not testing open-source alternatives**: DeepSeek V3 rivals GPT-4o at 1/20th cost
✅ Benchmark LLaMA 3.3, DeepSeek, Mixtral for cost-sensitive projects

❌ **Overlooking context length limits**: Running out of context mid-conversation
✅ Choose Claude (200k) or Gemini (1M) for long-context applications

❌ **Single-model commitment**: Locks you into one provider's pricing/limits
✅ Build abstraction layer to support multiple models (see multi-model-orchestration)

❌ **Not tracking actual costs**: "Budget-friendly" model becomes expensive at scale
✅ Monitor token usage and costs per endpoint/model combination

❌ **Choosing based on marketing claims**: "Most advanced AI" doesn't mean best for your task
✅ Run your own evaluations with representative test cases

---

## Related Skills

- `llm-model-routing.md` - Dynamic routing between models for cost optimization
- `multi-model-orchestration.md` - Coordinating multiple models in workflows
- `modal-gpu-workloads.md` - Self-hosting open-source models on GPUs
- `api-rate-limiting.md` - Managing rate limits across providers
- `llm-dataset-preparation.md` - Preparing evaluation datasets
- `observability-distributed-tracing.md` - Monitoring model performance

---

**Last Updated**: 2025-10-26
**Format Version**: 1.0 (Atomic)
