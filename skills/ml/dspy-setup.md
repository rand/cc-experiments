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

- `dspy-signatures.md` - Next step: Define input/output signatures
- `dspy-modules.md` - Building composable prediction modules
- `dspy-optimizers.md` - Optimizing prompts with teleprompters
- `modal-functions-basics.md` - Modal deployment fundamentals
- `modal-gpu-workloads.md` - GPU selection and optimization for Modal
- `modal-web-endpoints.md` - Creating Modal web endpoints for inference
- `llm-dataset-preparation.md` - Preparing training data for optimization

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
