---
name: dspy-setup
description: Installation, configuration, and language model setup for DSPy framework including Modal and HuggingFace
---

# DSPy Setup

**Scope**: Installation, LM configuration, environment setup, Modal/HuggingFace integration
**Lines**: ~420
**Last Updated**: 2025-10-25

## When to Use This Skill

Activate this skill when:
- Starting a new DSPy project from scratch
- Configuring language models for DSPy programs
- Setting up Modal-hosted models for DSPy
- Integrating HuggingFace models (Inference API or self-hosted)
- Troubleshooting DSPy installation issues
- Switching between different LM providers (OpenAI, Anthropic, Modal, HF)
- Understanding DSPy's core architecture and initialization

## Core Concepts

### DSPy Programming Model

**Philosophy**: Programming, not prompting
- Write **declarative Python code** instead of brittle prompt strings
- Define task structure with **signatures** (input/output specs)
- Compose reusable **modules** (Predict, ChainOfThought, ReAct)
- Let DSPy **optimize** prompts and weights automatically

**Key insight**: DSPy separates "what" (signatures) from "how" (modules) from "optimization" (teleprompters)

### Installation and Dependencies

**Core package**:
```bash
# Latest stable release
pip install dspy-ai

# Or with uv (recommended)
uv add dspy-ai

# Development/latest version
pip install git+https://github.com/stanfordnlp/dspy.git
```

**Optional dependencies**:
```bash
# For specific LM providers
uv add openai anthropic cohere litellm

# For HuggingFace
uv add huggingface-hub transformers

# For Modal integration
uv add modal

# For RAG and vector search
uv add chromadb weaviate-client qdrant-client

# For evaluation and metrics
uv add datasets evaluate
```

### Language Model Configuration

**LM object**: Central to DSPy workflow
- **Configure once**, use everywhere
- Supports multiple providers (OpenAI, Anthropic, Modal, HuggingFace, local)
- Handles API keys, rate limits, caching

**Three configuration patterns**:
1. **Global default**: `dspy.configure(lm=lm)` - all modules use this LM
2. **Module-specific**: `predictor = dspy.Predict(signature, lm=custom_lm)`
3. **Context manager**: Temporarily override LM for specific operations

---

## Patterns

### Pattern 1: Basic Setup (OpenAI)

```python
import dspy

# Configure OpenAI LM
lm = dspy.LM(
    model="openai/gpt-4o-mini",
    api_key="your-api-key-here",  # or set OPENAI_API_KEY env var
    max_tokens=1000,
    temperature=0.0,
)

# Set as global default
dspy.configure(lm=lm)

# Test configuration
response = lm("Hello, DSPy!")
print(response)  # Should return LM response
```

**When to use**:
- Quick prototyping with OpenAI models
- Production apps with GPT-4 or GPT-3.5
- Cost-effective development with gpt-4o-mini

### Pattern 2: Anthropic Claude Setup

```python
import dspy
import os

# Configure Claude
lm = dspy.LM(
    model="anthropic/claude-3-5-sonnet-20241022",
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    max_tokens=4096,
    temperature=0.0,
)

dspy.configure(lm=lm)

# Claude-specific features
lm_with_caching = dspy.LM(
    model="anthropic/claude-3-5-sonnet-20241022",
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    max_tokens=4096,
    # Claude supports prompt caching for long contexts
    cache_prompt=True,
)
```

**When to use**:
- Long context windows (200K tokens)
- Advanced reasoning tasks
- Cost optimization with prompt caching

### Pattern 3: Modal-Hosted Models

```python
import dspy
import modal

# Deploy model on Modal with GPU
app = modal.App("dspy-llm")

@app.function(
    image=modal.Image.debian_slim().pip_install("vllm", "transformers"),
    gpu="L40S",  # Cost-effective GPU
    timeout=600,
)
@modal.web_endpoint(method="POST")
def inference(request: dict):
    """Modal endpoint for model inference"""
    from vllm import LLM, SamplingParams

    # Load model once (cached across requests)
    llm = LLM(model="meta-llama/Meta-Llama-3.1-8B-Instruct")

    prompt = request.get("prompt")
    params = SamplingParams(
        temperature=request.get("temperature", 0.0),
        max_tokens=request.get("max_tokens", 1000),
    )

    output = llm.generate(prompt, params)
    return {"response": output[0].outputs[0].text}

# Use Modal endpoint in DSPy
# After deploying: modal deploy dspy_modal.py

import requests

class ModalLM:
    """Custom LM wrapper for Modal endpoints"""
    def __init__(self, endpoint_url, max_tokens=1000, temperature=0.0):
        self.endpoint_url = endpoint_url
        self.max_tokens = max_tokens
        self.temperature = temperature

    def __call__(self, prompt, **kwargs):
        response = requests.post(
            self.endpoint_url,
            json={
                "prompt": prompt,
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                "temperature": kwargs.get("temperature", self.temperature),
            }
        )
        return response.json()["response"]

# Configure DSPy with Modal endpoint
modal_lm = ModalLM(
    endpoint_url="https://your-app--inference.modal.run",
    max_tokens=1000,
)

# Note: For full DSPy integration, wrap in dspy.LM-compatible class
```

**When to use**:
- GPU-accelerated inference without infrastructure management
- Cost-effective deployment (pay only for usage)
- Custom fine-tuned models
- High-throughput batch processing

**Benefits**:
- Serverless GPU inference (L40S, H100, A100)
- Automatic scaling
- Cold start optimization with Modal's caching

### Pattern 4: HuggingFace Inference API

```python
import dspy
import os

# Use HuggingFace Inference API
lm = dspy.LM(
    model="huggingface/meta-llama/Meta-Llama-3.1-8B-Instruct",
    api_key=os.getenv("HUGGINGFACE_API_KEY"),
    api_base="https://api-inference.huggingface.co/models",
    max_tokens=1000,
)

dspy.configure(lm=lm)

# Alternative: Use specific HuggingFace endpoint
lm = dspy.LM(
    model="huggingface/mistralai/Mistral-7B-Instruct-v0.2",
    api_key=os.getenv("HUGGINGFACE_API_KEY"),
    max_tokens=1000,
)
```

**When to use**:
- Quick access to HuggingFace hosted models
- Testing different open-source models
- Prototyping without infrastructure setup

### Pattern 5: Self-Hosted HuggingFace (vLLM/TGI)

```python
import dspy

# Connect to self-hosted vLLM or Text Generation Inference server
# Assumes you have vLLM running: vllm serve meta-llama/Meta-Llama-3.1-8B-Instruct

lm = dspy.LM(
    model="openai/meta-llama/Meta-Llama-3.1-8B-Instruct",  # vLLM uses OpenAI-compatible API
    api_base="http://localhost:8000/v1",  # vLLM default endpoint
    api_key="EMPTY",  # vLLM doesn't require auth by default
    max_tokens=2000,
)

dspy.configure(lm=lm)

# For Text Generation Inference (TGI)
lm_tgi = dspy.LM(
    model="tgi/meta-llama/Meta-Llama-3.1-8B-Instruct",
    api_base="http://localhost:8080",  # TGI default port
    max_tokens=2000,
)
```

**When to use**:
- Running models on your own infrastructure
- Maximum control over model configuration
- High-throughput production deployments

### Pattern 6: Modal + HuggingFace Integration

```python
import modal
import dspy

# Deploy HuggingFace model on Modal with optimized serving
app = modal.App("dspy-hf-modal")

@app.function(
    image=modal.Image.debian_slim()
        .pip_install("vllm", "transformers", "torch"),
    gpu="L40S",
    timeout=600,
    # Use Modal volumes for model caching
    volumes={"/models": modal.Volume.from_name("hf-models")},
)
@modal.asgi_app()
def serve():
    """Serve HuggingFace model via vLLM on Modal"""
    from vllm import AsyncLLMEngine, AsyncEngineArgs, SamplingParams
    from vllm.entrypoints.openai.api_server import build_app

    # Configure vLLM engine
    engine_args = AsyncEngineArgs(
        model="meta-llama/Meta-Llama-3.1-8B-Instruct",
        download_dir="/models",  # Use Modal volume
        tensor_parallel_size=1,
    )

    # Build OpenAI-compatible API
    return build_app(engine_args)

# After deployment, use in DSPy
lm = dspy.LM(
    model="openai/meta-llama/Meta-Llama-3.1-8B-Instruct",
    api_base="https://your-app--serve.modal.run/v1",
    api_key="EMPTY",
    max_tokens=2000,
)

dspy.configure(lm=lm)
```

**When to use**:
- Best of both worlds: HuggingFace models + Modal's serverless GPUs
- Production deployments with autoscaling
- Cost optimization (only pay when using)

**Benefits**:
- No infrastructure management
- Automatic GPU scaling
- Model caching with Modal volumes
- OpenAI-compatible API

### Pattern 7: Local Models (Ollama)

```python
import dspy

# Run local model via Ollama
# First: ollama pull llama3.2
lm = dspy.LM(
    model="ollama/llama3.2",
    api_base="http://localhost:11434",  # Ollama default port
    max_tokens=2000,
)

dspy.configure(lm=lm)

# No API key needed for local models
# Great for development and privacy-sensitive applications
```

**When to use**:
- Offline development
- Privacy requirements (data stays local)
- Cost-free experimentation
- Custom fine-tuned models

### Pattern 8: Multi-Model Setup

```python
import dspy

# Different models for different purposes
fast_lm = dspy.LM("openai/gpt-4o-mini", max_tokens=500)
smart_lm = dspy.LM("openai/gpt-4o", max_tokens=2000)
modal_lm = dspy.LM(
    "openai/meta-llama/Meta-Llama-3.1-8B-Instruct",
    api_base="https://your-app.modal.run/v1",
    api_key="EMPTY",
)

# Set default for most operations
dspy.configure(lm=fast_lm)

# Use smart model for complex reasoning
class ComplexReasoner(dspy.Module):
    def __init__(self):
        super().__init__()
        # Override with smarter model
        self.predictor = dspy.ChainOfThought("question -> answer", lm=smart_lm)

    def forward(self, question):
        return self.predictor(question=question)

# Use Modal model for high-volume, cost-sensitive tasks
high_volume_predictor = dspy.Predict("text -> category", lm=modal_lm)
```

**Benefits**:
- Cost optimization (use expensive models only when needed)
- Performance optimization (fast models for simple tasks)
- Flexibility (switch models without code changes)

---

## Advanced Patterns

### Pattern 9: Multi-Region Deployment with Failover

```python
import dspy
import os
from typing import List, Optional

class MultiRegionLM:
    """LM with automatic failover across regions/providers."""

    def __init__(self, endpoints: List[dict], max_retries=2):
        """
        Args:
            endpoints: List of {provider, model, api_key, api_base}
            max_retries: Retries per endpoint before failover
        """
        self.endpoints = endpoints
        self.max_retries = max_retries
        self.current_idx = 0

    def __call__(self, prompt, **kwargs):
        """Try each endpoint until success."""
        last_error = None

        for endpoint_idx in range(len(self.endpoints)):
            endpoint = self.endpoints[self.current_idx]

            for retry in range(self.max_retries):
                try:
                    lm = dspy.LM(
                        model=endpoint["model"],
                        api_key=endpoint.get("api_key"),
                        api_base=endpoint.get("api_base"),
                        **kwargs
                    )
                    return lm(prompt)

                except Exception as e:
                    last_error = e
                    print(f"Endpoint {self.current_idx} attempt {retry+1} failed: {e}")

            # Move to next endpoint
            self.current_idx = (self.current_idx + 1) % len(self.endpoints)

        raise Exception(f"All endpoints failed. Last error: {last_error}")

# Configure multi-region setup
endpoints = [
    {
        "provider": "openai",
        "model": "openai/gpt-4o-mini",
        "api_key": os.getenv("OPENAI_API_KEY"),
    },
    {
        "provider": "anthropic",
        "model": "anthropic/claude-3-5-sonnet-20241022",
        "api_key": os.getenv("ANTHROPIC_API_KEY"),
    },
    {
        "provider": "modal",
        "model": "openai/meta-llama/Meta-Llama-3.1-8B-Instruct",
        "api_base": "https://your-app.modal.run/v1",
        "api_key": "EMPTY",
    },
]

multi_region_lm = MultiRegionLM(endpoints)
```

**When to use**:
- Production systems requiring 99.9%+ uptime
- Multi-cloud strategies
- Cost optimization through provider arbitrage
- Geographic latency reduction

### Pattern 10: Cost-Optimized Model Router

```python
import dspy
from typing import Callable

class CostOptimizedRouter:
    """Route requests to cost-appropriate models."""

    def __init__(self, fast_lm: dspy.LM, smart_lm: dspy.LM,
                 complexity_fn: Callable[[str], float]):
        """
        Args:
            fast_lm: Cheap, fast model (e.g., gpt-4o-mini)
            smart_lm: Expensive, capable model (e.g., gpt-4o)
            complexity_fn: Function returning 0-1 complexity score
        """
        self.fast_lm = fast_lm
        self.smart_lm = smart_lm
        self.complexity_fn = complexity_fn
        self.complexity_threshold = 0.6

    def __call__(self, prompt, **kwargs):
        """Route based on prompt complexity."""
        complexity = self.complexity_fn(prompt)

        if complexity < self.complexity_threshold:
            # Use fast model for simple prompts
            return self.fast_lm(prompt, **kwargs)
        else:
            # Use smart model for complex prompts
            return self.smart_lm(prompt, **kwargs)

# Complexity heuristic
def estimate_complexity(prompt: str) -> float:
    """Estimate prompt complexity (0-1 scale)."""
    score = 0.0

    # Length factor
    word_count = len(prompt.split())
    score += min(word_count / 1000, 0.3)

    # Complexity keywords
    complex_keywords = ["analyze", "compare", "evaluate", "synthesize", "reasoning"]
    keyword_count = sum(1 for kw in complex_keywords if kw in prompt.lower())
    score += min(keyword_count * 0.15, 0.4)

    # Multi-step indicators
    if any(ind in prompt.lower() for ind in ["step by step", "first", "then", "finally"]):
        score += 0.3

    return min(score, 1.0)

# Configure router
fast = dspy.LM("openai/gpt-4o-mini", max_tokens=500)
smart = dspy.LM("openai/gpt-4o", max_tokens=2000)

router = CostOptimizedRouter(fast, smart, estimate_complexity)
dspy.configure(lm=router)
```

**Benefits**:
- Reduce costs by 60-80% on average workloads
- Maintain quality on complex tasks
- Automatic routing based on prompt analysis

### Pattern 11: Modal + caching for Batch Processing

```python
import modal
import dspy

app = modal.App("dspy-batch-processor")

# Persistent cache volume
cache_volume = modal.Volume.from_name("llm-cache", create_if_missing=True)

@app.function(
    image=modal.Image.debian_slim().pip_install("vllm", "transformers", "diskcache"),
    gpu="L40S",
    volumes={"/cache": cache_volume},
    timeout=1800,
)
def batch_inference(prompts: list[str], model: str = "meta-llama/Meta-Llama-3.1-8B-Instruct"):
    """Process prompts in batch with caching."""
    from vllm import LLM, SamplingParams
    from diskcache import Cache

    # Initialize cache
    cache = Cache("/cache/responses")

    # Load model once
    llm = LLM(model=model, download_dir="/cache/models")

    results = []
    uncached_prompts = []
    uncached_indices = []

    # Check cache first
    for i, prompt in enumerate(prompts):
        cached = cache.get(prompt)
        if cached:
            results.append(cached)
        else:
            uncached_prompts.append(prompt)
            uncached_indices.append(i)
            results.append(None)  # Placeholder

    # Batch process uncached prompts
    if uncached_prompts:
        params = SamplingParams(temperature=0.0, max_tokens=1000)
        outputs = llm.generate(uncached_prompts, params)

        # Store in cache and results
        for idx, output in zip(uncached_indices, outputs):
            response = output.outputs[0].text
            cache.set(prompts[idx], response)
            results[idx] = response

    return results

# Use in DSPy
@app.local_entrypoint()
def main():
    prompts = ["What is DSPy?"] * 100  # Example batch
    results = batch_inference.remote(prompts)
    print(f"Processed {len(results)} prompts")
```

**When to use**:
- Large-scale batch processing (>1000 prompts)
- Repeated prompts across runs
- Cost-sensitive workloads
- Offline evaluation pipelines

---

## Production Considerations

### Deployment Architecture

**Single Model (Simple)**:
```
Client → DSPy App → OpenAI API
```
- Use for: MVPs, low-traffic apps (<100 req/day)
- Cost: Pay-per-token to API provider
- Latency: 200-2000ms depending on provider

**Modal-Hosted (Scalable)**:
```
Client → DSPy App → Modal Endpoint → vLLM → Model
```
- Use for: Production apps, custom models, cost optimization
- Cost: $0.50-2.00/hour GPU time (only when active)
- Latency: 50-500ms (lower than API with L40S/H100)

**Hybrid (Optimal)**:
```
Client → DSPy App → Router → [Modal (batch), OpenAI (realtime), Anthropic (complex)]
```
- Use for: Large-scale production
- Cost: 40-70% reduction vs API-only
- Latency: 50-2000ms depending on route

### Scaling Guidelines

**Request Volume**:
- <100/day: Direct API calls (OpenAI, Anthropic)
- 100-10K/day: Modal with 1-2 GPUs
- 10K-100K/day: Modal with autoscaling (2-10 GPUs)
- >100K/day: Multi-region Modal + API failover

**Model Size**:
- 7B parameters: L40S GPU (48GB VRAM) - $0.50/hr
- 13B parameters: L40S or A100 (40GB) - $1.00/hr
- 70B parameters: 2x A100 (80GB) or H100 - $4.00/hr

### Monitoring and Observability

```python
import dspy
import time
import logging
from contextlib import contextmanager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MonitoredLM:
    """LM wrapper with monitoring."""

    def __init__(self, lm: dspy.LM, metrics_callback=None):
        self.lm = lm
        self.metrics_callback = metrics_callback
        self.call_count = 0
        self.total_latency = 0.0
        self.error_count = 0

    def __call__(self, prompt, **kwargs):
        self.call_count += 1
        start_time = time.time()

        try:
            result = self.lm(prompt, **kwargs)
            latency = time.time() - start_time
            self.total_latency += latency

            # Log metrics
            logger.info(f"LM call #{self.call_count}: {latency:.2f}s")

            if self.metrics_callback:
                self.metrics_callback({
                    "call_count": self.call_count,
                    "latency": latency,
                    "success": True,
                    "prompt_length": len(prompt),
                    "timestamp": start_time,
                })

            return result

        except Exception as e:
            self.error_count += 1
            logger.error(f"LM call failed: {e}")

            if self.metrics_callback:
                self.metrics_callback({
                    "call_count": self.call_count,
                    "error": str(e),
                    "success": False,
                    "timestamp": start_time,
                })

            raise

    def stats(self):
        """Return aggregated statistics."""
        avg_latency = self.total_latency / self.call_count if self.call_count > 0 else 0
        error_rate = self.error_count / self.call_count if self.call_count > 0 else 0

        return {
            "total_calls": self.call_count,
            "avg_latency_ms": avg_latency * 1000,
            "error_count": self.error_count,
            "error_rate": error_rate,
        }

# Usage
lm = dspy.LM("openai/gpt-4o-mini")
monitored_lm = MonitoredLM(lm)
dspy.configure(lm=monitored_lm)

# After processing
print(monitored_lm.stats())
```

### Cost Management

**Budget Tracking**:
```python
class BudgetLM:
    """LM with budget enforcement."""

    def __init__(self, lm: dspy.LM, max_budget_usd: float,
                 cost_per_1k_tokens: float):
        self.lm = lm
        self.max_budget = max_budget_usd
        self.cost_per_1k = cost_per_1k_tokens
        self.total_cost = 0.0
        self.total_tokens = 0

    def __call__(self, prompt, **kwargs):
        # Estimate cost before call
        estimated_tokens = len(prompt.split()) * 1.3  # Rough estimate
        estimated_cost = (estimated_tokens / 1000) * self.cost_per_1k

        if self.total_cost + estimated_cost > self.max_budget:
            raise Exception(
                f"Budget exceeded: ${self.total_cost:.2f} / ${self.max_budget:.2f}"
            )

        result = self.lm(prompt, **kwargs)

        # Update actual cost (if available from response metadata)
        self.total_tokens += estimated_tokens
        self.total_cost += estimated_cost

        return result

    def budget_status(self):
        return {
            "spent": self.total_cost,
            "remaining": self.max_budget - self.total_cost,
            "percentage": (self.total_cost / self.max_budget) * 100,
        }

# Usage: limit to $10 budget
lm = dspy.LM("openai/gpt-4o-mini")
budget_lm = BudgetLM(lm, max_budget_usd=10.0, cost_per_1k_tokens=0.15)
dspy.configure(lm=budget_lm)
```

### Error Recovery and Resilience

**Circuit Breaker Pattern**:
```python
import time

class CircuitBreakerLM:
    """LM with circuit breaker for resilience."""

    def __init__(self, lm: dspy.LM, failure_threshold=5,
                 recovery_timeout=60):
        self.lm = lm
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.circuit_open = False

    def __call__(self, prompt, **kwargs):
        # Check if circuit is open
        if self.circuit_open:
            if time.time() - self.last_failure_time < self.recovery_timeout:
                raise Exception("Circuit breaker open - service unavailable")
            else:
                # Try recovery
                self.circuit_open = False
                self.failure_count = 0

        try:
            result = self.lm(prompt, **kwargs)
            # Reset on success
            self.failure_count = 0
            return result

        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                self.circuit_open = True
                logger.error("Circuit breaker opened")

            raise

# Usage
lm = dspy.LM("openai/gpt-4o-mini")
resilient_lm = CircuitBreakerLM(lm, failure_threshold=5, recovery_timeout=60)
dspy.configure(lm=resilient_lm)
```

---

## Quick Reference

### Installation Commands

```bash
# Standard installation
pip install dspy-ai

# With uv (recommended)
uv add dspy-ai

# With Modal and HuggingFace support
uv add dspy-ai modal huggingface-hub transformers

# Optional dependencies
uv add openai anthropic cohere litellm chromadb weaviate-client
```

### LM Configuration Patterns

| Provider | Model String | API Base | Use Case |
|----------|--------------|----------|----------|
| OpenAI | `openai/gpt-4o-mini` | Default | Fast, cost-effective |
| OpenAI | `openai/gpt-4o` | Default | Advanced reasoning |
| Anthropic | `anthropic/claude-3-5-sonnet-20241022` | Default | Long context, caching |
| Modal | `openai/model-name` | Custom endpoint | Serverless GPU |
| HuggingFace | `huggingface/model-name` | HF Inference API | Hosted open models |
| vLLM | `openai/model-name` | `http://localhost:8000/v1` | Self-hosted |
| Ollama | `ollama/llama3.2` | `http://localhost:11434` | Local, privacy |

### Modal Deployment Quick Start

```bash
# Install Modal
uv add modal

# Set up Modal account
modal setup

# Deploy model endpoint
modal deploy dspy_modal.py

# Get endpoint URL
modal app list
```

### Configuration Checklist

```
✅ DO: Store API keys in environment variables
✅ DO: Set reasonable max_tokens limits
✅ DO: Use temperature=0.0 for deterministic outputs
✅ DO: Configure global LM with dspy.configure()
✅ DO: Test LM configuration before building modules
✅ DO: Use Modal volumes for model caching
✅ DO: Use L40S GPU for cost-effective Modal deployments

❌ DON'T: Hard-code API keys in source code
❌ DON'T: Use very high temperatures (>0.7) for structured tasks
❌ DON'T: Forget to set max_tokens (can cause unexpected costs)
❌ DON'T: Skip error handling for API calls
❌ DON'T: Leave Modal dev apps running (use modal app stop)
```

---

## Anti-Patterns

❌ **Hard-coded API keys**: Security risk, not shareable
```python
# Bad
lm = dspy.LM("openai/gpt-4o-mini", api_key="sk-1234567890")
```
✅ Use environment variables:
```python
# Good
import os
lm = dspy.LM("openai/gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))
```

❌ **No max_tokens limit**: Unexpected costs, slow responses
```python
# Bad
lm = dspy.LM("openai/gpt-4o")  # No limit
```
✅ Set reasonable limits:
```python
# Good
lm = dspy.LM("openai/gpt-4o", max_tokens=2000)
```

❌ **Forgetting dspy.configure()**: Modules won't know which LM to use
```python
# Bad
lm = dspy.LM("openai/gpt-4o-mini")
predictor = dspy.Predict("text -> label")  # No LM configured!
```
✅ Configure globally or per-module:
```python
# Good
lm = dspy.LM("openai/gpt-4o-mini")
dspy.configure(lm=lm)
predictor = dspy.Predict("text -> label")  # Uses configured LM
```

❌ **Not using Modal volumes for model caching**: Slow cold starts
```python
# Bad - Downloads model on every cold start
@app.function(image=image, gpu="L40S")
def serve():
    llm = LLM(model="meta-llama/Meta-Llama-3.1-70B")  # Re-downloads every time
```
✅ Use Modal volumes:
```python
# Good - Cache model in volume
@app.function(
    image=image,
    gpu="L40S",
    volumes={"/models": modal.Volume.from_name("hf-models")},
)
def serve():
    llm = LLM(model="meta-llama/Meta-Llama-3.1-70B", download_dir="/models")
```

---

## Related Skills

### Core DSPy Skills
- `dspy-signatures.md` - Next step: Define input/output signatures
- `dspy-modules.md` - Building composable prediction modules
- `dspy-optimizers.md` - Optimizing prompts with teleprompters
- `dspy-evaluation.md` - Evaluating program performance
- `dspy-rag.md` - Building RAG systems
- `dspy-assertions.md` - Adding validation and constraints

### Advanced DSPy Skills
- `dspy-agents.md` - Building autonomous agents with tool use
- `dspy-prompt-engineering.md` - Advanced prompting techniques
- `dspy-finetuning.md` - Fine-tuning models with DSPy
- `dspy-streaming.md` - Implementing streaming responses
- `dspy-structured-outputs.md` - Generating structured data
- `dspy-caching.md` - Implementing caching strategies
- `dspy-testing.md` - Testing DSPy programs
- `dspy-deployment.md` - Production deployment patterns

### Infrastructure Skills
- `modal-functions-basics.md` - Modal deployment fundamentals
- `modal-gpu-workloads.md` - GPU selection and optimization for Modal
- `modal-web-endpoints.md` - Creating Modal web endpoints for inference
- `llm-dataset-preparation.md` - Preparing training data for optimization

### Resources
- `resources/dspy/level1-quickstart.md` - Getting started guide
- `resources/dspy/level2-architecture.md` - DSPy architecture deep dive
- `resources/dspy/level3-production.md` - Production deployment guide

---

**Last Updated**: 2025-10-30
**Format Version**: 1.0 (Atomic)
