---
name: modal-modal-common-errors
description: Encountering Modal deployment or runtime errors
---



# Modal Common Errors

**Scope**: Common Modal.com errors, debugging strategies, and proven solutions
**Lines**: ~340
**Last Updated**: 2025-10-18

## When to Use This Skill

Activate this skill when:
- Encountering Modal deployment or runtime errors
- Debugging failed Modal function executions
- Resolving image build failures
- Fixing import and dependency errors
- Troubleshooting timeout and memory issues
- Solving GPU allocation problems
- Debugging network and connection errors

## Core Concepts

### Error Categories

**Build-time errors**: Occur during image building
- Package installation failures
- Dependency conflicts
- Invalid Dockerfile syntax
- Missing system dependencies
- Network timeouts during build

**Runtime errors**: Occur during function execution
- Import errors (module not found)
- Timeout errors (function exceeded limit)
- Memory errors (OOM)
- GPU allocation failures
- Permission errors

**Deployment errors**: Occur during app deployment
- Invalid app configuration
- Authentication failures
- Resource quota exceeded
- Invalid decorator usage

### Debugging Strategy

**Step 1: Identify error phase**
- Build time → Check image configuration
- Runtime → Check function code and dependencies
- Deployment → Check app structure and auth

**Step 2: Read error messages carefully**
- Modal provides detailed stack traces
- Look for root cause (not just last line)
- Check for common patterns

**Step 3: Use debugging tools**
- `modal shell` for interactive debugging
- `modal logs` for historical debugging
- Local testing with `modal run --dev`

---

## Patterns

### Image Build Errors

#### Error: "ModuleNotFoundError" at runtime

```
ERROR: ModuleNotFoundError: No module named 'requests'
```

**Cause**: Package not installed in Modal image

**Solution**:
```python
# ❌ Bad: Package not in image
@app.function()
def fetch_data():
    import requests  # Will fail!
    return requests.get("https://api.example.com").json()

# ✅ Good: Install package in image
image = modal.Image.debian_slim().uv_pip_install("requests")

@app.function(image=image)
def fetch_data():
    import requests
    return requests.get("https://api.example.com").json()
```

#### Error: "Package installation failed"

```
ERROR: Could not find a version that satisfies the requirement numpy==2.0.0
```

**Cause**: Invalid version or package name

**Solution**:
```python
# ❌ Bad: Wrong version or typo
image = modal.Image.debian_slim().uv_pip_install(
    "numpy==2.0.0",  # Version doesn't exist
    "pandass"        # Typo
)

# ✅ Good: Verify versions and names
image = modal.Image.debian_slim().uv_pip_install(
    "numpy==1.26.0",  # Valid version
    "pandas==2.1.0"   # Correct spelling
)
```

**Debugging tip**: Test packages locally first with `uv pip install`

#### Error: "System dependency missing"

```
ERROR: ImportError: libGL.so.1: cannot open shared object file
```

**Cause**: Missing system library (common with OpenCV, etc.)

**Solution**:
```python
# ❌ Bad: Only Python package
image = modal.Image.debian_slim().uv_pip_install("opencv-python")

# ✅ Good: Install system dependencies first
image = (
    modal.Image.debian_slim()
    .apt_install("libgl1-mesa-glx", "libglib2.0-0")
    .uv_pip_install("opencv-python")
)
```

### Runtime Errors

#### Error: "TimeoutError"

```
ERROR: Function exceeded timeout of 60 seconds
```

**Cause**: Function ran longer than timeout limit (default 60s)

**Solution**:
```python
# ❌ Bad: Default timeout too short
@app.function()
def train_model():
    # Takes 5 minutes
    model.fit(X_train, y_train)
    return model

# ✅ Good: Set appropriate timeout
@app.function(timeout=600)  # 10 minutes
def train_model():
    model.fit(X_train, y_train)
    return model
```

**Timeout limits**:
- Default: 60 seconds
- Maximum: 86400 seconds (24 hours)
- Best practice: Set 20% higher than expected runtime

#### Error: "OutOfMemoryError"

```
ERROR: Container killed due to OOM (Out of Memory)
```

**Cause**: Function exceeded memory limit

**Solution**:
```python
# ❌ Bad: Default memory (1GB) insufficient
@app.function()
def process_large_file():
    df = pd.read_csv("huge_file.csv")  # 5GB file
    return df.shape

# ✅ Good: Increase memory limit
@app.function(memory=8192)  # 8GB RAM
def process_large_file():
    df = pd.read_csv("huge_file.csv")
    return df.shape

# ✅ Better: Stream data instead
@app.function(memory=2048)
def process_large_file_streaming():
    chunks = pd.read_csv("huge_file.csv", chunksize=10000)
    total_rows = sum(len(chunk) for chunk in chunks)
    return total_rows
```

#### Error: "GPUOutOfMemoryError"

```
ERROR: CUDA out of memory. Tried to allocate 2.00 GiB
```

**Cause**: Model or batch size too large for GPU memory

**Solution**:
```python
# ❌ Bad: Batch size too large
@app.function(gpu="A10G")  # 24GB VRAM
def train():
    batch_size = 128  # Too large
    train_loader = DataLoader(dataset, batch_size=batch_size)
    # OOM error

# ✅ Good: Reduce batch size
@app.function(gpu="A10G")
def train():
    batch_size = 32  # Fits in memory
    train_loader = DataLoader(dataset, batch_size=batch_size)

# ✅ Better: Use gradient accumulation
@app.function(gpu="A10G")
def train():
    batch_size = 16
    accumulation_steps = 4  # Effective batch size = 64
    train_loader = DataLoader(dataset, batch_size=batch_size)
```

### Import and Dependency Errors

#### Error: "Relative import error"

```
ERROR: ImportError: attempted relative import with no known parent package
```

**Cause**: Relative imports don't work in Modal's execution model

**Solution**:
```python
# ❌ Bad: Relative imports
from .utils import helper_function
from ..models import Model

# ✅ Good: Absolute imports or inline code
# Option 1: Include code in same file
@app.function()
def helper_function():
    return "helper"

@app.function()
def main():
    result = helper_function.remote()

# Option 2: Use Modal's mount feature
from modal import Mount

@app.function(
    mounts=[Mount.from_local_dir("./src", remote_path="/root/src")]
)
def main():
    import sys
    sys.path.append("/root/src")
    from utils import helper_function
```

#### Error: "NameError: name 'X' is not defined"

```
ERROR: NameError: name 'MY_CONSTANT' is not defined
```

**Cause**: Global variables not available in Modal functions

**Solution**:
```python
# ❌ Bad: Global variable
MY_CONSTANT = 42

@app.function()
def use_constant():
    return MY_CONSTANT  # Not available!

# ✅ Good: Pass as parameter or use class
@app.function()
def use_constant(constant: int = 42):
    return constant

# ✅ Better: Use app.cls for state
@app.cls()
class MyService:
    def __init__(self):
        self.constant = 42

    @modal.method()
    def use_constant(self):
        return self.constant
```

### Network and Connection Errors

#### Error: "ConnectionError: Failed to connect"

```
ERROR: requests.exceptions.ConnectionError: Failed to establish connection
```

**Cause**: Network issues, firewall, or service unavailable

**Solution**:
```python
# ❌ Bad: No retry logic
@app.function()
def fetch_data():
    response = requests.get("https://api.example.com/data")
    return response.json()

# ✅ Good: Add retries and timeout
from tenacity import retry, stop_after_attempt, wait_exponential

@app.function(timeout=300)
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
def fetch_data():
    response = requests.get(
        "https://api.example.com/data",
        timeout=30
    )
    response.raise_for_status()
    return response.json()
```

#### Error: "Modal authentication failed"

```
ERROR: modal.exception.AuthError: Invalid token
```

**Cause**: Missing or expired Modal token

**Solution**:
```bash
# Re-authenticate with Modal
modal token set --token-id <YOUR_TOKEN_ID> --token-secret <YOUR_SECRET>

# Or use interactive auth
modal setup
```

### GPU Errors

#### Error: "GPU not available"

```
ERROR: RuntimeError: CUDA is not available
```

**Cause**: GPU not properly configured in decorator

**Solution**:
```python
# ❌ Bad: GPU not specified
@app.function()
def train_model():
    device = torch.device("cuda")  # Fails!
    model.to(device)

# ✅ Good: Specify GPU
@app.function(gpu="A10G")
def train_model():
    device = torch.device("cuda")
    model.to(device)
```

#### Error: "Requested GPU unavailable"

```
ERROR: No capacity available for gpu=H100
```

**Cause**: Requested GPU type not available in region

**Solution**:
```python
# ❌ Bad: Single GPU type
@app.function(gpu="H100")  # Might not be available
def train():
    pass

# ✅ Good: Use fallback GPUs
@app.function(gpu="L40S")  # More availability
def train():
    pass

# ✅ Better: Use gpu.Any for flexibility
@app.function(gpu=modal.gpu.Any())
def train():
    pass
```

---

## Quick Reference

### Common Error Messages and Solutions

```
Error Pattern                          | Solution
---------------------------------------|------------------------------------------
ModuleNotFoundError                    | Add package to image.uv_pip_install()
TimeoutError                           | Increase timeout parameter
OutOfMemoryError                       | Increase memory parameter or optimize
CUDA out of memory                     | Reduce batch size or use larger GPU
ImportError: libXX.so                  | Add system dependency with apt_install()
NameError: name 'X' not defined        | Move global to function or use class
ConnectionError                        | Add retry logic and timeouts
AuthError: Invalid token               | Run modal setup or modal token set
GPU not available                      | Add gpu parameter to @app.function()
No capacity for GPU                    | Use different GPU type or Any()
```

### Debugging Commands

```bash
# View real-time logs
modal logs my-app

# Interactive shell in container
modal shell my-app::my_function

# Test locally with dev mode
modal run --dev my_app.py

# Check app status
modal app list

# View function history
modal app logs my-app --function my_function

# Debug image build
modal image build my-app::image --force-rebuild
```

### Error Prevention Checklist

```
✅ DO: Test packages locally before adding to image
✅ DO: Set appropriate timeouts for long-running functions
✅ DO: Monitor memory usage and set limits accordingly
✅ DO: Use retry logic for network calls
✅ DO: Install system dependencies before Python packages
✅ DO: Use modal shell for interactive debugging

❌ DON'T: Ignore build warnings
❌ DON'T: Use default timeout for slow operations
❌ DON'T: Assume global variables work in functions
❌ DON'T: Skip error handling in production code
❌ DON'T: Use relative imports
❌ DON'T: Deploy without testing with --dev first
```

---

## Anti-Patterns

❌ **Ignoring logs**: Not checking `modal logs` when errors occur
✅ Use `modal logs my-app` to see detailed error traces

❌ **Not using modal shell**: Debugging blind without interactive access
✅ Use `modal shell my-app::function` to debug interactively

❌ **Skipping --dev mode**: Deploying without local testing
✅ Always test with `modal run --dev` before deploying

❌ **Generic error handling**: Catching all exceptions without logging
✅ Log specific errors with context for debugging

❌ **Not pinning versions**: Using unpinned package versions
✅ Pin all package versions: `uv_pip_install("pandas==2.1.0")`

❌ **Large Docker images**: Installing unnecessary packages
✅ Only install required packages, use debian_slim base

❌ **No timeout strategy**: Using default timeouts everywhere
✅ Set appropriate timeouts per function based on expected runtime

❌ **Ignoring GPU metrics**: Not monitoring GPU utilization
✅ Log GPU memory usage and utilization during runs

---

## Related Skills

- `modal-performance-debugging.md` - Performance profiling and optimization
- `modal-functions-basics.md` - Basic Modal function setup and configuration
- `modal-gpu-workloads.md` - GPU configuration and best practices
- `modal-image-building.md` - Image building strategies and optimization
- `modal-web-endpoints.md` - Debugging web endpoint specific issues

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
