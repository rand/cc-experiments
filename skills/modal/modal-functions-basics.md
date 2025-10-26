---
name: modal-functions-basics
description: Building serverless functions on Modal.com
---



# Modal Functions Basics

**Use this skill when:**
- Building serverless functions on Modal.com
- Defining Modal app structure and decorators
- Understanding function lifecycle and execution
- Working with Modal's Python SDK
- Creating basic serverless endpoints

## App Structure

### Basic App Definition

Define Modal apps with decorators:

```python
import modal

# Create app instance
app = modal.App("my-app")

# Define simple function
@app.function()
def hello(name: str) -> str:
    return f"Hello, {name}!"

# Local invocation
@app.local_entrypoint()
def main():
    result = hello.remote("World")
    print(result)
```

### Function Decorators

Use `@app.function()` for serverless functions:

```python
@app.function()
def simple_function():
    """Basic function with no special configuration"""
    return "Hello from Modal!"

# With timeout
@app.function(timeout=300)  # 5 minutes
def long_running_task():
    import time
    time.sleep(200)
    return "Done!"

# With memory configuration
@app.function(memory=2048)  # 2GB RAM
def memory_intensive():
    large_array = [0] * 10_000_000
    return sum(large_array)

# With CPU configuration
@app.function(cpu=4)
def parallel_processing():
    import multiprocessing
    pool = multiprocessing.Pool(4)
    # Parallel work
    return "Processed"
```

## Image Configuration

### Base Images

Configure runtime environment:

```python
# Debian slim base
image = modal.Image.debian_slim()

# Ubuntu base
image = modal.Image.ubuntu()

# Specific Python version
image = modal.Image.debian_slim(python_version="3.11")

# Use image in function
@app.function(image=image)
def my_function():
    return "Using custom image"
```

### Installing Packages

Install Python packages with uv (recommended):

```python
# Single package
image = modal.Image.debian_slim().uv_pip_install("requests")

# Multiple packages
image = modal.Image.debian_slim().uv_pip_install(
    "numpy",
    "pandas",
    "scikit-learn"
)

# With specific versions
image = modal.Image.debian_slim().uv_pip_install(
    "torch==2.1.0",
    "transformers==4.35.0"
)

# From requirements.txt
image = modal.Image.debian_slim().uv_pip_install_from_requirements(
    "requirements.txt"
)

@app.function(image=image)
def ml_inference(text: str):
    import torch
    from transformers import pipeline
    # ML code
    return result
```

### System Dependencies

Install system packages:

```python
# Install system packages
image = (
    modal.Image.debian_slim()
    .apt_install("ffmpeg", "libsm6", "libxext6")
    .uv_pip_install("opencv-python")
)

@app.function(image=image)
def process_video(video_path: str):
    import cv2
    # Video processing
    return "Processed"
```

### Custom Commands

Run custom setup commands:

```python
image = (
    modal.Image.debian_slim()
    .uv_pip_install("torch")
    .run_commands(
        "mkdir -p /models",
        "wget https://example.com/model.bin -O /models/model.bin"
    )
)

@app.function(image=image)
def use_model():
    model_path = "/models/model.bin"
    # Use preloaded model
    return result
```

## Function Invocation Patterns

### Remote Invocation

Call functions from Python code:

```python
@app.function()
def process_item(item_id: int) -> dict:
    # Processing logic
    return {"id": item_id, "status": "processed"}

@app.local_entrypoint()
def main():
    # Synchronous call (waits for result)
    result = process_item.remote(42)
    print(result)

    # Multiple calls
    results = []
    for i in range(10):
        result = process_item.remote(i)
        results.append(result)
```

### Parallel Execution

Run functions concurrently:

```python
@app.function()
def process_item(item: dict) -> dict:
    import time
    time.sleep(2)  # Simulate work
    return {"id": item["id"], "processed": True}

@app.local_entrypoint()
def main():
    items = [{"id": i} for i in range(100)]

    # Sequential - takes 200 seconds
    results = [process_item.remote(item) for item in items]

    # Parallel - much faster
    results = list(process_item.map(items))
    print(f"Processed {len(results)} items")
```

### Spawning Functions

Use `.spawn()` for fire-and-forget:

```python
@app.function()
def send_notification(user_id: int, message: str):
    # Send notification (don't need to wait)
    import requests
    requests.post(
        "https://notifications.example.com/send",
        json={"user_id": user_id, "message": message}
    )

@app.function()
def process_order(order_id: int):
    # Process order
    order = get_order(order_id)
    process(order)

    # Spawn notification (don't wait)
    send_notification.spawn(order.user_id, "Order processed!")

    return {"status": "complete"}
```

## Local Entrypoints

### CLI Interface

Create command-line interfaces:

```python
@app.local_entrypoint()
def main(name: str = "World"):
    """
    Simple greeting CLI

    Usage:
        modal run app.py --name Alice
    """
    result = hello.remote(name)
    print(result)

# Multiple entrypoints
@app.local_entrypoint()
def process():
    """Process all pending items"""
    items = get_pending_items()
    results = list(process_item.map(items))
    print(f"Processed {len(results)} items")

@app.local_entrypoint()
def status():
    """Check system status"""
    stats = get_stats.remote()
    print(f"Status: {stats}")
```

## Container Lifecycle

### Container Reuse

Understand warm vs cold starts:

```python
# Global state persists across invocations in same container
model = None

@app.function()
def predict(text: str):
    global model

    # Load model once per container
    if model is None:
        print("Loading model (cold start)")
        from transformers import pipeline
        model = pipeline("sentiment-analysis")

    # Reuse loaded model (warm start)
    return model(text)
```

### Function Context

Use `@enter` and `@exit` for lifecycle hooks:

```python
@app.cls()
class ModelInference:
    @modal.enter()
    def load_model(self):
        """Called once when container starts"""
        print("Loading model...")
        from transformers import pipeline
        self.model = pipeline("sentiment-analysis")
        print("Model loaded")

    @modal.method()
    def predict(self, text: str):
        """Called for each request"""
        return self.model(text)

    @modal.exit()
    def cleanup(self):
        """Called when container shuts down"""
        print("Cleaning up...")
        self.model = None

# Usage
@app.local_entrypoint()
def main():
    inference = ModelInference()
    results = inference.predict.map([
        "I love this!",
        "This is terrible",
        "Not sure how I feel"
    ])
    print(results)
```

## Passing Data

### Input Types

Accept various input types:

```python
from typing import List, Dict, Any

@app.function()
def process_primitives(
    count: int,
    ratio: float,
    enabled: bool,
    name: str
) -> dict:
    return {
        "count": count,
        "ratio": ratio,
        "enabled": enabled,
        "name": name
    }

@app.function()
def process_collections(
    items: List[str],
    config: Dict[str, Any]
) -> dict:
    return {
        "item_count": len(items),
        "config_keys": list(config.keys())
    }

from dataclasses import dataclass

@dataclass
class Task:
    id: int
    title: str
    priority: int

@app.function()
def process_dataclass(task: Task) -> dict:
    return {
        "id": task.id,
        "title": task.title,
        "priority": task.priority
    }
```

### Return Values

Return serializable data:

```python
@app.function()
def return_dict() -> dict:
    return {"status": "success", "count": 42}

@app.function()
def return_list() -> list:
    return [1, 2, 3, 4, 5]

@app.function()
def return_dataclass() -> Task:
    return Task(id=1, title="Example", priority=5)

# For large data, use volumes or object storage
@app.function()
def process_large_data():
    # Don't return large objects directly
    # Instead, write to volume or upload to S3
    volume.write_file("output.json", json.dumps(large_data))
    return {"location": "output.json"}
```

## Error Handling

### Retries

Configure automatic retries:

```python
@app.function(retries=3)
def flaky_api_call():
    """Retries up to 3 times on failure"""
    import requests
    response = requests.get("https://api.example.com/data")
    response.raise_for_status()
    return response.json()

# Custom retry logic
@app.function()
def robust_processing(item_id: int):
    import time
    max_attempts = 3

    for attempt in range(max_attempts):
        try:
            return process_with_external_api(item_id)
        except Exception as e:
            if attempt == max_attempts - 1:
                raise
            print(f"Attempt {attempt + 1} failed: {e}")
            time.sleep(2 ** attempt)  # Exponential backoff
```

### Exception Handling

Handle errors gracefully:

```python
@app.function()
def safe_processing(data: dict):
    try:
        result = risky_operation(data)
        return {"status": "success", "result": result}
    except ValueError as e:
        return {"status": "error", "error": str(e)}
    except Exception as e:
        # Log error for debugging
        print(f"Unexpected error: {e}")
        return {"status": "error", "error": "Internal error"}

@app.local_entrypoint()
def main():
    result = safe_processing.remote({"key": "value"})
    if result["status"] == "error":
        print(f"Processing failed: {result['error']}")
    else:
        print(f"Success: {result['result']}")
```

## Logging and Debugging

### Print Statements

Use print for logging (appears in Modal dashboard):

```python
@app.function()
def logged_function(item_id: int):
    print(f"Processing item {item_id}")

    result = process(item_id)
    print(f"Item {item_id} result: {result}")

    return result
```

### Structured Logging

Use Python logging module:

```python
import logging

@app.function()
def structured_logging():
    logger = logging.getLogger(__name__)

    logger.info("Starting processing")
    logger.warning("This is a warning")
    logger.error("This is an error")

    return "Done"
```

## Testing Functions Locally

### Local Testing

Test before deploying:

```python
# test_app.py
from app import process_item

def test_process_item():
    result = process_item.local(42)
    assert result["id"] == 42
    assert result["status"] == "processed"

if __name__ == "__main__":
    test_process_item()
    print("Tests passed!")
```

## Anti-Patterns to Avoid

**DON'T use global mutable state without understanding container lifecycle:**
```python
# ❌ BAD - Assumes single invocation
counter = 0

@app.function()
def bad_counter():
    global counter
    counter += 1
    return counter  # Unpredictable across containers

# ✅ GOOD - Use parameters or persistent storage
@app.function()
def good_counter(current_count: int):
    return current_count + 1
```

**DON'T return large objects directly:**
```python
# ❌ BAD - Slow and may hit size limits
@app.function()
def bad_large_data():
    huge_list = [i for i in range(10_000_000)]
    return huge_list

# ✅ GOOD - Use volumes or object storage
@app.function()
def good_large_data(volume: modal.Volume):
    huge_list = [i for i in range(10_000_000)]
    volume.write_file("data.json", json.dumps(huge_list))
    return {"location": "data.json", "size": len(huge_list)}
```

**DON'T use blocking sleep in hot loops:**
```python
# ❌ BAD - Wastes container time
@app.function()
def bad_polling():
    while True:
        time.sleep(60)
        check_status()

# ✅ GOOD - Use scheduled functions
@app.function(schedule=modal.Period(minutes=1))
def good_polling():
    check_status()
```

## Related Skills

- **modal-gpu-workloads.md** - GPU configuration for ML workloads
- **modal-web-endpoints.md** - Creating HTTP endpoints
- **modal-scheduling.md** - Scheduled and periodic functions
- **modal-volumes-secrets.md** - Persistent storage and secrets
- **modal-image-building.md** - Advanced image configuration
