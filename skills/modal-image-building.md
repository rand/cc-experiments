---
name: modal-image-building
description: Configuring Modal runtime environments
---



# Modal Image Building

**Use this skill when:**
- Configuring Modal runtime environments
- Installing dependencies for Modal functions
- Optimizing image build times
- Working with custom system packages
- Building reproducible deployments

## Image Basics

### Base Images

Choose appropriate base image:

```python
import modal

# Debian Slim (recommended for most cases)
image = modal.Image.debian_slim()

# Debian Slim with specific Python version
image = modal.Image.debian_slim(python_version="3.11")

# Ubuntu (when Debian packages unavailable)
image = modal.Image.ubuntu()
```

## Python Package Installation

### uv_pip_install (Recommended)

Use `uv_pip_install` for fast, reliable installs:

```python
# Single package
image = modal.Image.debian_slim().uv_pip_install("requests")

# Multiple packages
image = modal.Image.debian_slim().uv_pip_install(
    "numpy",
    "pandas",
    "scikit-learn"
)

# With versions
image = modal.Image.debian_slim().uv_pip_install(
    "torch==2.1.0",
    "transformers==4.35.0",
    "accelerate==0.24.0"
)

# From requirements.txt
image = modal.Image.debian_slim().uv_pip_install_from_requirements(
    "requirements.txt"
)
```

### Why uv_pip_install

Benefits over `pip_install`:
- 10-100x faster dependency resolution
- Better reproducibility
- More reliable conflict resolution
- Lockfile support

```python
# ❌ SLOWER - Traditional pip
image = modal.Image.debian_slim().pip_install(
    "torch",
    "transformers"
)  # Can take minutes

# ✅ FASTER - uv
image = modal.Image.debian_slim().uv_pip_install(
    "torch",
    "transformers"
)  # Takes seconds
```

## System Dependencies

### apt_install

Install system packages:

```python
# Single package
image = modal.Image.debian_slim().apt_install("ffmpeg")

# Multiple packages
image = modal.Image.debian_slim().apt_install(
    "ffmpeg",
    "libsm6",
    "libxext6",
    "libxrender-dev",
    "libgomp1"
)

# Common combinations
# For OpenCV
opencv_image = (
    modal.Image.debian_slim()
    .apt_install("libsm6", "libxext6", "libxrender-dev")
    .uv_pip_install("opencv-python")
)

# For audio processing
audio_image = (
    modal.Image.debian_slim()
    .apt_install("ffmpeg", "libsndfile1")
    .uv_pip_install("librosa", "soundfile")
)
```

## Custom Commands

### run_commands

Execute arbitrary shell commands:

```python
# Download and setup model
image = (
    modal.Image.debian_slim()
    .uv_pip_install("torch")
    .run_commands(
        "mkdir -p /models",
        "wget https://example.com/model.bin -O /models/model.bin"
    )
)

# Build from source
image = (
    modal.Image.debian_slim()
    .apt_install("build-essential", "cmake")
    .run_commands(
        "git clone https://github.com/example/lib.git",
        "cd lib && mkdir build && cd build",
        "cmake .. && make && make install"
    )
)

# Environment setup
image = (
    modal.Image.debian_slim()
    .run_commands(
        "export PATH=/custom/bin:$PATH",
        "echo 'export PATH=/custom/bin:$PATH' >> /root/.bashrc"
    )
)
```

## Layering and Caching

### Build Layers Efficiently

Order operations for optimal caching:

```python
# ✅ GOOD - System deps first (change rarely)
image = (
    modal.Image.debian_slim()
    .apt_install("ffmpeg", "libsm6")  # Cached
    .uv_pip_install("opencv-python")   # Cached if deps unchanged
    .copy_local_file("config.yaml", "/app/config.yaml")  # Changes often
)

# ❌ BAD - Frequently changing layers first
image = (
    modal.Image.debian_slim()
    .copy_local_file("config.yaml", "/app/config.yaml")  # Invalidates cache!
    .apt_install("ffmpeg")  # Has to rebuild every time
    .uv_pip_install("opencv-python")
)
```

### Separate Concerns

Split rarely-changing from frequently-changing:

```python
# Base image (changes rarely)
base_image = (
    modal.Image.debian_slim()
    .apt_install("ffmpeg", "libsm6")
    .uv_pip_install(
        "torch==2.1.0",
        "transformers==4.35.0"
    )
)

# App image (changes frequently)
app_image = (
    base_image
    .copy_local_dir("./src", "/app/src")
    .copy_local_file("config.yaml", "/app/config.yaml")
)

@app.function(image=app_image)
def my_function():
    pass
```

## Environment Variables

### Set Build-Time Variables

Configure environment during build:

```python
image = (
    modal.Image.debian_slim()
    .env({"HF_HOME": "/models/cache"})
    .uv_pip_install("transformers")
)

# Multiple variables
image = (
    modal.Image.debian_slim()
    .env({
        "TRANSFORMERS_CACHE": "/models/transformers",
        "HF_HOME": "/models/huggingface",
        "TORCH_HOME": "/models/torch"
    })
)
```

## Copying Local Files

### copy_local_file and copy_local_dir

Include local files in image:

```python
# Single file
image = (
    modal.Image.debian_slim()
    .copy_local_file("config.yaml", "/app/config.yaml")
)

# Directory
image = (
    modal.Image.debian_slim()
    .copy_local_dir("./src", "/app/src")
    .copy_local_dir("./data", "/app/data")
)

# With .gitignore-like filtering
image = (
    modal.Image.debian_slim()
    .copy_local_dir(
        "./src",
        "/app/src",
        ignore=["*.pyc", "__pycache__", "*.log"]
    )
)
```

## Dockerfile Integration

### From Dockerfile

Use existing Dockerfiles:

```python
# From Dockerfile in repo
image = modal.Image.from_dockerfile("Dockerfile")

# From Dockerfile with context
image = modal.Image.from_dockerfile(
    "docker/Dockerfile",
    context_mount=modal.Mount.from_local_dir(".", remote_path="/context")
)

# From Dockerfile with build args
image = modal.Image.from_dockerfile(
    "Dockerfile",
    build_args={"PYTHON_VERSION": "3.11"}
)
```

## Complete Examples

### ML Image

Comprehensive ML environment:

```python
ml_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install(
        "git",
        "wget",
        "libsm6",
        "libxext6"
    )
    .uv_pip_install(
        "torch==2.1.0",
        "torchvision==0.16.0",
        "transformers==4.35.0",
        "accelerate==0.24.0",
        "bitsandbytes==0.41.0",
        "datasets==2.14.0",
        "evaluate==0.4.1",
        "tensorboard==2.15.0"
    )
    .env({
        "HF_HOME": "/cache/huggingface",
        "TORCH_HOME": "/cache/torch"
    })
)
```

### Data Processing Image

ETL/data science environment:

```python
data_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("postgresql-client", "libpq-dev")
    .uv_pip_install(
        "pandas==2.1.0",
        "numpy==1.24.0",
        "sqlalchemy==2.0.0",
        "psycopg2-binary==2.9.9",
        "pyarrow==13.0.0",
        "duckdb==0.9.0"
    )
)
```

### Web Scraping Image

Browser automation environment:

```python
scraping_image = (
    modal.Image.debian_slim()
    .apt_install(
        "chromium",
        "chromium-driver"
    )
    .uv_pip_install(
        "selenium==4.15.0",
        "beautifulsoup4==4.12.0",
        "requests==2.31.0",
        "lxml==4.9.0"
    )
)
```

## Debugging Images

### Interactive Debugging

Test image builds:

```python
@app.function(image=my_image)
def debug_image():
    import subprocess
    import sys

    # Check Python version
    print(f"Python: {sys.version}")

    # Check installed packages
    result = subprocess.run(
        ["pip", "list"],
        capture_output=True,
        text=True
    )
    print(result.stdout)

    # Check system packages
    result = subprocess.run(
        ["dpkg", "-l"],
        capture_output=True,
        text=True
    )
    print(result.stdout[:1000])  # First 1000 chars

    return "Debug complete"
```

## Anti-Patterns to Avoid

**DON'T use pip_install when uv_pip_install works:**
```python
# ❌ SLOW
image = modal.Image.debian_slim().pip_install("torch", "transformers")

# ✅ FAST
image = modal.Image.debian_slim().uv_pip_install("torch", "transformers")
```

**DON'T copy unnecessary files:**
```python
# ❌ BAD - Copies everything including .git, node_modules
image = modal.Image.debian_slim().copy_local_dir(".", "/app")

# ✅ GOOD - Only copy what's needed
image = (
    modal.Image.debian_slim()
    .copy_local_dir(
        "./src",
        "/app/src",
        ignore=["*.pyc", "__pycache__", ".git", "node_modules"]
    )
)
```

**DON'T install packages without versions in production:**
```python
# ❌ BAD - Non-reproducible
image = modal.Image.debian_slim().uv_pip_install("torch", "transformers")

# ✅ GOOD - Pinned versions
image = modal.Image.debian_slim().uv_pip_install(
    "torch==2.1.0",
    "transformers==4.35.0"
)
```

**DON'T put changing layers early:**
```python
# ❌ BAD - Invalidates cache on every code change
image = (
    modal.Image.debian_slim()
    .copy_local_dir("./src", "/app")  # Changes often!
    .uv_pip_install("torch")          # Has to rebuild
)

# ✅ GOOD - Stable layers first
image = (
    modal.Image.debian_slim()
    .uv_pip_install("torch")          # Cached
    .copy_local_dir("./src", "/app")  # Only this rebuilds
)
```

## Related Skills

- **modal-functions-basics.md** - Using images in functions
- **modal-gpu-workloads.md** - ML/GPU-specific images
- **modal-volumes-secrets.md** - Baking data vs volumes
