---
name: modal-modal-performance-debugging
description: Modal functions running slower than expected
---



# Modal Performance Debugging

**Scope**: Modal.com performance profiling, optimization, and cost reduction
**Lines**: ~350
**Last Updated**: 2025-10-18

## When to Use This Skill

Activate this skill when:
- Modal functions running slower than expected
- Experiencing high cloud costs on Modal
- GPU utilization is low despite allocation
- Cold start times are excessive
- Container initialization is slow
- Functions timeout due to performance issues
- Need to profile and optimize Modal workloads

## Core Concepts

### Performance Bottlenecks

**Cold starts**: Time to initialize new container
- Image download and extraction
- Package imports
- Model loading
- Checkpoint restoration

**Warm starts**: Time to reuse existing container
- Function execution only
- Significantly faster than cold starts
- Depends on container reuse strategy

**Execution time**: Actual function runtime
- Business logic performance
- GPU/CPU utilization
- Network I/O
- Disk I/O

**Resource efficiency**: Utilization vs allocation
- GPU memory usage vs allocated
- CPU usage vs allocated cores
- Memory usage vs allocated RAM
- Cost = allocation time, not usage time

### Performance Metrics

**Key metrics to track**:
- Cold start time (container init)
- Warm start time (function only)
- Execution time (business logic)
- GPU utilization (%)
- Memory peak usage (MB)
- Cost per invocation ($)

**How to measure**:
```python
import time
import modal

@app.function()
def measure_performance():
    start = time.time()

    # Your code here
    result = expensive_operation()

    duration = time.time() - start
    print(f"Execution time: {duration:.2f}s")
    return result
```

### Cost Optimization

**Cost factors**:
- Container runtime (billed per second)
- GPU type and quantity
- Memory allocation
- CPU allocation
- Cold start overhead

**Cost formula**:
```
Total Cost = (Container Runtime) × (Resource Rate)
Container Runtime = Cold Start + Execution Time
```

**Optimization strategy**:
1. Reduce cold starts (keep containers warm)
2. Minimize execution time (optimize code)
3. Right-size resources (don't over-allocate)
4. Use cheaper GPUs when possible

---

## Patterns

### Profiling Modal Functions

#### Basic execution profiling

```python
import time
import modal

app = modal.App("profiling-demo")

@app.function()
def profile_execution():
    """Profile different stages of execution"""
    stages = {}

    # Stage 1: Data loading
    start = time.time()
    data = load_data()
    stages["data_loading"] = time.time() - start

    # Stage 2: Processing
    start = time.time()
    result = process_data(data)
    stages["processing"] = time.time() - start

    # Stage 3: Output
    start = time.time()
    save_result(result)
    stages["saving"] = time.time() - start

    # Print profiling results
    total = sum(stages.values())
    print(f"\nPerformance Profile:")
    for stage, duration in stages.items():
        pct = (duration / total) * 100
        print(f"  {stage}: {duration:.2f}s ({pct:.1f}%)")
    print(f"  Total: {total:.2f}s")

    return result
```

#### GPU utilization profiling

```python
import modal

# Add nvidia-smi to image
image = modal.Image.debian_slim().apt_install("nvidia-utils")

@app.function(gpu="A10G", image=image)
def profile_gpu():
    """Monitor GPU utilization during execution"""
    import subprocess
    import time

    def get_gpu_stats():
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used",
             "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True
        )
        util, mem = result.stdout.strip().split(", ")
        return int(util), int(mem)

    # Sample GPU stats during execution
    stats = []
    start = time.time()

    # Run workload
    for i in range(100):
        # Your GPU work here
        compute_intensive_task()

        if i % 10 == 0:
            util, mem = get_gpu_stats()
            stats.append((time.time() - start, util, mem))

    # Analyze GPU utilization
    avg_util = sum(s[1] for s in stats) / len(stats)
    avg_mem = sum(s[2] for s in stats) / len(stats)

    print(f"\nGPU Performance:")
    print(f"  Average utilization: {avg_util:.1f}%")
    print(f"  Average memory used: {avg_mem} MB")
    print(f"  Peak memory: {max(s[2] for s in stats)} MB")

    if avg_util < 50:
        print("⚠️  WARNING: Low GPU utilization. Consider CPU-only.")

    return stats
```

### Cold Start Optimization

#### Minimize image size

```python
# ❌ Bad: Large image with unnecessary packages
image = modal.Image.debian_slim().uv_pip_install(
    "transformers[torch]",  # Includes all dependencies
    "tensorflow",           # Not needed
    "scipy",                # Not needed
    "matplotlib"            # Not needed
)

# ✅ Good: Minimal image
image = modal.Image.debian_slim().uv_pip_install(
    "torch",
    "transformers"  # Only what's needed
)

# ✅ Better: Layer commonly used packages
base_image = modal.Image.debian_slim().uv_pip_install(
    "torch",
    "transformers"
)

# Cache this as base, add specific deps per function
specialized_image = base_image.uv_pip_install("sentencepiece")
```

#### Lazy imports for faster cold starts

```python
# ❌ Bad: Import heavy libraries at module level
import torch
import transformers
import numpy as np

@app.function()
def inference(text: str):
    model = transformers.AutoModel.from_pretrained("model")
    # Cold start includes import time

# ✅ Good: Lazy imports inside function
@app.function()
def inference(text: str):
    import torch  # Only imported when function runs
    import transformers

    model = transformers.AutoModel.from_pretrained("model")
    # Faster cold start

# ✅ Better: Use container lifecycle for expensive ops
@app.cls()
class InferenceService:
    @modal.enter()
    def load_model(self):
        """Runs once per container, not per invocation"""
        import torch
        import transformers

        self.model = transformers.AutoModel.from_pretrained("model")
        print("Model loaded (once per container)")

    @modal.method()
    def inference(self, text: str):
        # Model already loaded, super fast warm starts
        return self.model(text)
```

#### Checkpoint optimization

```python
import modal

# ❌ Bad: Download model every cold start
@app.function(gpu="A10G")
def slow_inference():
    from transformers import AutoModel

    # Downloads ~2GB every cold start
    model = AutoModel.from_pretrained("large-model")
    return model

# ✅ Good: Use Volume to cache model
volume = modal.Volume.from_name("model-cache", create_if_missing=True)

@app.function(
    gpu="A10G",
    volumes={"/cache": volume}
)
def fast_inference():
    from transformers import AutoModel
    import os

    cache_dir = "/cache/models"
    os.makedirs(cache_dir, exist_ok=True)

    # Downloads once, then cached
    model = AutoModel.from_pretrained(
        "large-model",
        cache_dir=cache_dir
    )
    return model

# ✅ Better: Pre-download during image build
def download_model():
    from transformers import AutoModel
    AutoModel.from_pretrained(
        "large-model",
        cache_dir="/model"
    )

image = (
    modal.Image.debian_slim()
    .uv_pip_install("transformers", "torch")
    .run_function(download_model)  # Download during build
)

@app.function(gpu="A10G", image=image)
def fastest_inference():
    from transformers import AutoModel

    # Model already in image, instant load
    model = AutoModel.from_pretrained("large-model", cache_dir="/model")
    return model
```

### Container Reuse Optimization

#### Keep containers warm

```python
# ❌ Bad: Containers die after each call
@app.function(timeout=60)
def process():
    # Container dies after 60s timeout
    expensive_setup()
    do_work()

# ✅ Good: Use keep_warm to maintain pool
@app.function(
    keep_warm=1,  # Keep 1 container always ready
    timeout=300
)
def process():
    expensive_setup()  # Only runs on cold start
    do_work()

# ✅ Better: Use cls with lifecycle management
@app.cls(keep_warm=2)  # Keep 2 containers warm
class Processor:
    @modal.enter()
    def setup(self):
        """Runs once per container"""
        self.expensive_resource = load_large_model()
        print("Setup complete (once per container)")

    @modal.method()
    def process(self, data):
        """Reuses warm container and setup"""
        return self.expensive_resource.process(data)
```

#### Concurrency tuning

```python
# ❌ Bad: One call per container (inefficient)
@app.function()
def handle_request(data):
    return process(data)

# ✅ Good: Allow concurrent calls on same container
@app.function(
    concurrency_limit=10,  # 10 calls per container
    keep_warm=2            # 2 containers = 20 concurrent
)
def handle_request(data):
    return process(data)

# ⚠️ Caution: Only for thread-safe workloads
# Not suitable for GPU workloads (GPU is exclusive)
```

### GPU Performance Optimization

#### Right-size GPU allocation

```python
# ❌ Bad: Over-allocated GPU
@app.function(gpu="H100")  # 80GB VRAM, expensive
def small_model_inference():
    # Only uses 4GB VRAM, wastes 76GB
    model = load_small_model()
    return model.predict()

# ✅ Good: Match GPU to workload
@app.function(gpu="T4")  # 16GB VRAM, much cheaper
def small_model_inference():
    # Uses 4GB, T4 is sufficient
    model = load_small_model()
    return model.predict()

# ✅ Better: Profile first, then choose GPU
@app.function(gpu="A10G")  # Test with mid-tier
def profile_gpu_needs():
    import torch

    model = load_model()

    # Check memory usage
    allocated = torch.cuda.memory_allocated() / 1e9
    reserved = torch.cuda.memory_reserved() / 1e9

    print(f"GPU Memory - Allocated: {allocated:.2f}GB, Reserved: {reserved:.2f}GB")

    # Based on results:
    # < 8GB: Use T4
    # 8-24GB: Use L40S or A10G
    # > 24GB: Use A100 or H100

    return model.predict()
```

#### Batch processing for throughput

```python
# ❌ Bad: Process one item at a time
@app.function(gpu="A10G")
def process_items(items: list):
    results = []
    for item in items:
        result = model.predict(item)  # Underutilizes GPU
        results.append(result)
    return results

# ✅ Good: Batch processing
@app.function(gpu="A10G")
def process_items(items: list):
    import torch

    # Process in batches to saturate GPU
    batch_size = 32
    results = []

    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]

        # GPU works on 32 items simultaneously
        batch_results = model.predict(torch.tensor(batch))
        results.extend(batch_results)

    return results

# ✅ Better: Dynamic batching
@app.function(gpu="A10G")
def process_items(items: list):
    import torch

    # Adjust batch size based on available memory
    gpu_mem_gb = torch.cuda.get_device_properties(0).total_memory / 1e9

    if gpu_mem_gb >= 40:
        batch_size = 128
    elif gpu_mem_gb >= 20:
        batch_size = 64
    else:
        batch_size = 32

    print(f"Using batch size: {batch_size}")

    results = []
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        results.extend(model.predict(torch.tensor(batch)))

    return results
```

### Memory Optimization

#### Monitor and right-size memory

```python
import modal
import tracemalloc

@app.function(memory=2048)  # Start with 2GB
def profile_memory():
    """Profile memory usage to right-size allocation"""
    tracemalloc.start()

    # Your workload
    data = load_and_process_data()

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print(f"\nMemory Usage:")
    print(f"  Current: {current / 1e6:.2f} MB")
    print(f"  Peak: {peak / 1e6:.2f} MB")
    print(f"  Allocated: 2048 MB")
    print(f"  Utilization: {(peak / 1e6) / 2048 * 100:.1f}%")

    # Optimal allocation: peak × 1.2 (20% headroom)
    optimal = int(peak / 1e6 * 1.2)
    print(f"  Recommended: {optimal} MB")

    return data
```

#### Stream large data

```python
# ❌ Bad: Load entire dataset into memory
@app.function(memory=16384)  # Need 16GB for 10GB file
def process_large_file():
    import pandas as pd

    # Loads entire 10GB file into memory
    df = pd.read_csv("huge_data.csv")
    return df.describe()

# ✅ Good: Stream data in chunks
@app.function(memory=2048)  # Only need 2GB
def process_large_file():
    import pandas as pd

    # Process 100K rows at a time
    chunks = pd.read_csv("huge_data.csv", chunksize=100_000)

    stats = []
    for chunk in chunks:
        stats.append(chunk.describe())

    # Combine statistics
    return pd.concat(stats).mean()
```

---

## Quick Reference

### Performance Profiling Commands

```python
# Execution timing
import time
start = time.time()
result = function()
print(f"Duration: {time.time() - start:.2f}s")

# Memory profiling
import tracemalloc
tracemalloc.start()
result = function()
current, peak = tracemalloc.get_traced_memory()
print(f"Peak memory: {peak / 1e6:.2f} MB")

# GPU stats
import subprocess
subprocess.run(["nvidia-smi"])
```

### Optimization Checklist

```
Cold Start Optimization:
✅ Minimize image size (only required packages)
✅ Use lazy imports where possible
✅ Cache models in Volumes or image
✅ Pre-download assets during image build

Container Reuse:
✅ Use keep_warm for frequently called functions
✅ Use @app.cls() with @modal.enter() for setup
✅ Set appropriate concurrency_limit

GPU Optimization:
✅ Profile GPU memory usage first
✅ Choose cheapest GPU that fits workload
✅ Use batch processing to saturate GPU
✅ Monitor utilization (aim for >80%)

Memory Optimization:
✅ Profile peak memory usage
✅ Right-size allocation (peak × 1.2)
✅ Stream large datasets instead of loading
✅ Clean up large objects when done

Cost Optimization:
✅ Reduce cold starts (keep_warm)
✅ Minimize execution time (optimize code)
✅ Right-size all resources (GPU, memory, CPU)
✅ Use cheaper GPUs when possible (T4 vs H100)
```

### Performance Metrics

```
Metric                 | Good         | Investigate
-----------------------|--------------|------------------
Cold start time        | < 10s        | > 30s
Warm start time        | < 1s         | > 5s
GPU utilization        | > 80%        | < 50%
Memory utilization     | 60-90%       | < 40% or > 95%
Cost per invocation    | -            | Track trends
```

---

## Anti-Patterns

❌ **Ignoring cold starts**: Accepting slow initialization
✅ Use keep_warm, cache models, optimize image size

❌ **Poor checkpoint strategy**: Downloading models every cold start
✅ Use Volumes or bake models into image

❌ **Over-sized images**: Including unnecessary dependencies
✅ Only install required packages, use debian_slim

❌ **Wrong GPU choice**: Using H100 for small models
✅ Profile first, choose cheapest GPU that fits

❌ **Single-item processing**: Underutilizing GPU with small batches
✅ Use batch processing to saturate GPU

❌ **No profiling**: Guessing at resource requirements
✅ Profile memory, GPU, and execution time

❌ **Ignoring warm containers**: Every call does expensive setup
✅ Use @app.cls() with @modal.enter() for one-time setup

❌ **Loading entire datasets**: Running out of memory
✅ Stream data in chunks when possible

---

## Related Skills

- `modal-common-errors.md` - Debugging common Modal errors
- `modal-optimization.md` - Advanced optimization techniques
- `modal-gpu-workloads.md` - GPU configuration and best practices
- `modal-functions-basics.md` - Basic Modal function configuration
- `modal-image-building.md` - Image optimization strategies

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
