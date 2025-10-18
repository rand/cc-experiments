---
name: ml-stable-diffusion-deployment
description: Deploying Stable Diffusion models to production environments
---



# Stable Diffusion Deployment

**Scope**: Deploying Stable Diffusion to production, optimization techniques, scalable inference APIs
**Lines**: ~350
**Last Updated**: 2025-10-18

## When to Use This Skill

Activate this skill when:
- Deploying Stable Diffusion models to production environments
- Building scalable image generation APIs and services
- Optimizing diffusion model inference for speed and cost
- Setting up batch processing pipelines for image generation
- Implementing caching and warm-start strategies
- Selecting appropriate GPU infrastructure for diffusion workloads
- Debugging performance issues in diffusion deployments
- Managing concurrent requests and queue systems

## Core Concepts

### VRAM Management

**Memory Requirements**:
- **SD 1.5 (fp16)**: ~4GB VRAM for single inference
- **SDXL (fp16)**: ~8-12GB VRAM for single inference
- **SD 3.0 (fp16)**: ~10-14GB VRAM for single inference
- **Batch processing**: Multiply by batch size + overhead

**Optimization Techniques**:
- **Model precision**: fp16 vs fp32 (2x memory savings)
- **CPU offloading**: Trade memory for speed
- **Sequential offloading**: Extreme memory savings (very slow)
- **Attention slicing**: Reduce memory for attention layers
- **VAE tiling**: Process large images in tiles

### Model Loading and Caching

**Cold Start Problem**: Loading model from disk is slow (5-30 seconds)

**Solutions**:
- **Keep model in VRAM**: Never unload between requests
- **Model caching**: Load once, reuse for all requests
- **Warm containers**: Pre-load models before first request
- **Multiple workers**: Dedicated GPU per worker

**Best Practice**: Load model at container startup, not per request

### Inference Optimization

**Speed Optimization Hierarchy**:
1. **xformers/flash-attention**: 30-50% speedup, free
2. **torch.compile()**: 20-30% speedup, PyTorch 2.0+
3. **Better scheduler**: 2-5x speedup (fewer steps)
4. **Reduced resolution**: 4x speedup (512 vs 1024)
5. **Lower precision**: 2x speedup (fp16 vs fp32)

**Quality vs Speed Tradeoffs**:
- Fewer steps: Faster but lower quality
- Lower guidance: Faster but less prompt adherence
- Smaller model: Faster but reduced capabilities
- Lower resolution: Faster but less detail

### API Design Patterns

**Synchronous API**: Simple but blocks on long inference
```python
@app.post("/generate")
def generate(prompt: str):
    image = pipe(prompt)  # Blocks for 3-10 seconds
    return image
```

**Asynchronous API**: Better for concurrent requests
```python
@app.post("/generate")
async def generate(prompt: str):
    image = await async_pipe(prompt)
    return image
```

**Queue-based API**: Best for production
```python
@app.post("/generate")
def generate(prompt: str):
    job_id = queue.enqueue(prompt)
    return {"job_id": job_id, "status": "pending"}

@app.get("/status/{job_id}")
def status(job_id: str):
    return queue.get_status(job_id)
```

---

## Patterns

### Basic Modal.com Deployment

```python
import modal
from pathlib import Path

# Define image with diffusers and optimizations
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "diffusers==0.30.0",
        "transformers==4.44.0",
        "accelerate==0.33.0",
        "safetensors==0.4.4",
        "xformers==0.0.27",  # Memory efficient attention
    )
)

app = modal.App("stable-diffusion")

# Download model at build time
with image.imports():
    from diffusers import StableDiffusionPipeline
    import torch

@app.cls(
    gpu="L40S",  # 48GB VRAM, cost-effective for SDXL
    image=image,
    timeout=600,  # 10 minute timeout
)
class StableDiffusionModel:
    @modal.build()
    def download_model(self):
        """Download model during image build"""
        from diffusers import StableDiffusionPipeline

        StableDiffusionPipeline.from_pretrained(
            "runwayml/stable-diffusion-v1-5",
            torch_dtype=torch.float16,
        )

    @modal.enter()
    def load_model(self):
        """Load model once when container starts"""
        from diffusers import StableDiffusionPipeline
        import torch

        self.pipe = StableDiffusionPipeline.from_pretrained(
            "runwayml/stable-diffusion-v1-5",
            torch_dtype=torch.float16,
        ).to("cuda")

        # Enable memory efficient attention
        self.pipe.enable_xformers_memory_efficient_attention()

    @modal.method()
    def generate(
        self,
        prompt: str,
        negative_prompt: str = "blurry, low quality",
        num_inference_steps: int = 30,
        guidance_scale: float = 7.5,
    ):
        """Generate single image"""
        import torch

        image = self.pipe(
            prompt=prompt,
            negative_prompt=negative_prompt,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
        ).images[0]

        # Return as bytes
        from io import BytesIO
        buf = BytesIO()
        image.save(buf, format="PNG")
        return buf.getvalue()

@app.local_entrypoint()
def main():
    model = StableDiffusionModel()
    image_bytes = model.generate.remote("A serene mountain landscape")

    # Save locally
    with open("output.png", "wb") as f:
        f.write(image_bytes)
```

**Key Points**:
- Model downloaded during build (faster cold starts)
- Model loaded once at container startup
- GPU stays warm between requests
- xformers enabled for memory efficiency

### SDXL Deployment with Optimization

```python
import modal

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "diffusers==0.30.0",
        "transformers==4.44.0",
        "accelerate==0.33.0",
        "safetensors==0.4.4",
        "xformers==0.0.27",
        "torch==2.1.0",
    )
)

app = modal.App("sdxl-optimized")

@app.cls(
    gpu="A100",  # 40GB VRAM needed for SDXL with optimizations
    image=image,
    timeout=900,
    container_idle_timeout=300,  # Keep warm for 5 min
)
class SDXLModel:
    @modal.build()
    def download_models(self):
        from diffusers import StableDiffusionXLPipeline
        import torch

        # Download base model
        StableDiffusionXLPipeline.from_pretrained(
            "stabilityai/stable-diffusion-xl-base-1.0",
            torch_dtype=torch.float16,
            variant="fp16",
            use_safetensors=True,
        )

    @modal.enter()
    def load_model(self):
        from diffusers import StableDiffusionXLPipeline, UniPCMultistepScheduler
        import torch

        # Load pipeline
        self.pipe = StableDiffusionXLPipeline.from_pretrained(
            "stabilityai/stable-diffusion-xl-base-1.0",
            torch_dtype=torch.float16,
            variant="fp16",
            use_safetensors=True,
        ).to("cuda")

        # Optimizations
        self.pipe.enable_xformers_memory_efficient_attention()

        # Fast scheduler (20-25 steps instead of 50)
        self.pipe.scheduler = UniPCMultistepScheduler.from_config(
            self.pipe.scheduler.config
        )

        # Compile UNet for speedup (PyTorch 2.0+)
        # Adds ~60s warmup, saves 20-30% per inference
        import torch._dynamo
        torch._dynamo.config.suppress_errors = True
        self.pipe.unet = torch.compile(
            self.pipe.unet,
            mode="reduce-overhead",
            fullgraph=True,
        )

        # Warmup compilation
        print("Warming up model...")
        self.pipe(
            "warmup",
            num_inference_steps=1,
            guidance_scale=5.0,
        )
        print("Model ready!")

    @modal.method()
    def generate(
        self,
        prompt: str,
        negative_prompt: str = "blurry, low quality, distorted",
        num_inference_steps: int = 25,  # Reduced with UniPC
        guidance_scale: float = 6.0,    # Lower for SDXL
        width: int = 1024,
        height: int = 1024,
        seed: int | None = None,
    ):
        import torch
        from io import BytesIO

        generator = None
        if seed is not None:
            generator = torch.Generator("cuda").manual_seed(seed)

        image = self.pipe(
            prompt=prompt,
            negative_prompt=negative_prompt,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            width=width,
            height=height,
            generator=generator,
        ).images[0]

        buf = BytesIO()
        image.save(buf, format="PNG")
        return buf.getvalue()
```

**Optimizations applied**:
- xformers: 30-40% memory reduction
- UniPC scheduler: 2x faster (25 steps vs 50)
- torch.compile: 20-30% inference speedup
- fp16: 50% memory reduction
- Container idle timeout: Avoid cold starts

### FastAPI Web Endpoint

```python
import modal
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from fastapi.responses import Response

web_app = FastAPI()
app = modal.App("sd-api")

# [Same image and model class as above]

class GenerationRequest(BaseModel):
    prompt: str = Field(..., description="Text prompt for generation")
    negative_prompt: str = Field(
        default="blurry, low quality",
        description="Negative prompt"
    )
    num_inference_steps: int = Field(default=30, ge=10, le=100)
    guidance_scale: float = Field(default=7.5, ge=1.0, le=20.0)
    width: int = Field(default=512, ge=256, le=1024)
    height: int = Field(default=512, ge=256, le=1024)
    seed: int | None = Field(default=None, description="Random seed")

@web_app.post("/generate")
async def generate_image(request: GenerationRequest):
    """Generate image from text prompt"""
    try:
        # Call Modal function
        model = StableDiffusionModel()
        image_bytes = model.generate.remote(
            prompt=request.prompt,
            negative_prompt=request.negative_prompt,
            num_inference_steps=request.num_inference_steps,
            guidance_scale=request.guidance_scale,
            width=request.width,
            height=request.height,
            seed=request.seed,
        )

        return Response(content=image_bytes, media_type="image/png")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@web_app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.function(image=image)
@modal.asgi_app()
def fastapi_app():
    return web_app
```

**Usage**:
```bash
# Deploy
modal deploy stable_diffusion.py

# Test
curl -X POST https://your-app.modal.run/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "A magical forest", "seed": 42}' \
  --output image.png
```

### Batch Processing Pipeline

```python
import modal

app = modal.App("sd-batch")

@app.cls(gpu="L40S", image=image)
class BatchGenerator:
    @modal.enter()
    def load_model(self):
        from diffusers import StableDiffusionPipeline
        import torch

        self.pipe = StableDiffusionPipeline.from_pretrained(
            "runwayml/stable-diffusion-v1-5",
            torch_dtype=torch.float16,
        ).to("cuda")

        self.pipe.enable_xformers_memory_efficient_attention()

    @modal.method()
    def generate_batch(
        self,
        prompts: list[str],
        batch_size: int = 4,  # Process 4 at a time
    ):
        """Generate multiple images efficiently"""
        import torch
        from io import BytesIO

        all_images = []

        # Process in batches to manage VRAM
        for i in range(0, len(prompts), batch_size):
            batch_prompts = prompts[i:i + batch_size]

            # Generate batch
            images = self.pipe(
                prompt=batch_prompts,
                num_inference_steps=30,
                guidance_scale=7.5,
            ).images

            # Convert to bytes
            for image in images:
                buf = BytesIO()
                image.save(buf, format="PNG")
                all_images.append(buf.getvalue())

        return all_images

@app.local_entrypoint()
def main():
    prompts = [
        "A red apple",
        "A blue car",
        "A green forest",
        "A yellow sunset",
        "A purple mountain",
    ]

    generator = BatchGenerator()
    images = generator.generate_batch.remote(prompts, batch_size=2)

    # Save all images
    for i, img_bytes in enumerate(images):
        with open(f"batch_{i}.png", "wb") as f:
            f.write(img_bytes)
```

**Benefits**:
- Amortize model loading across many images
- Efficient VRAM usage with batching
- Parallel processing on single GPU

### Memory-Constrained Deployment (CPU Offloading)

```python
@app.cls(
    gpu="T4",  # Only 16GB VRAM
    image=image,
)
class MemoryEfficientSDXL:
    @modal.enter()
    def load_model(self):
        from diffusers import StableDiffusionXLPipeline
        import torch

        self.pipe = StableDiffusionXLPipeline.from_pretrained(
            "stabilityai/stable-diffusion-xl-base-1.0",
            torch_dtype=torch.float16,
            variant="fp16",
        )

        # Enable CPU offloading (slow but works on 16GB)
        self.pipe.enable_model_cpu_offload()

        # Enable VAE tiling for large images
        self.pipe.enable_vae_tiling()

        # Enable attention slicing
        self.pipe.enable_attention_slicing(slice_size=1)

    @modal.method()
    def generate(self, prompt: str):
        """Generate with minimal VRAM"""
        image = self.pipe(
            prompt=prompt,
            num_inference_steps=25,
            guidance_scale=6.0,
        ).images[0]

        from io import BytesIO
        buf = BytesIO()
        image.save(buf, format="PNG")
        return buf.getvalue()
```

**Tradeoffs**:
- ✅ Works on smaller GPUs (T4, 16GB)
- ❌ 2-4x slower than full GPU
- Use when: GPU budget limited, speed not critical

---

## Quick Reference

### GPU Selection for Modal.com

```
Model    | Min VRAM | Recommended GPU | Cost/Hour* | Speed
---------|----------|-----------------|------------|-------
SD 1.5   | 4GB      | L40S            | $1.60      | Fast
SDXL     | 8GB      | L40S            | $1.60      | Medium
SDXL Opt | 12GB     | A100 (40GB)     | $3.00      | Fast
SD 3.0   | 12GB     | A100 (40GB)     | $3.00      | Medium

*Approximate Modal.com pricing
```

### Optimization Techniques

```
Technique                    | Memory Savings | Speed Improvement | Quality Impact
-----------------------------|----------------|-------------------|---------------
fp16 precision               | 50%            | 2x                | Minimal
xformers attention           | 30-40%         | 1.3x              | None
torch.compile()              | 0%             | 1.2-1.3x          | None
Better scheduler (UniPC)     | 0%             | 2-3x              | Minimal
CPU offloading               | 60-70%         | 0.3-0.5x (slower) | None
Attention slicing            | 20-30%         | 0.9x              | None
VAE tiling                   | 15-25%         | 0.95x             | None
Reduced steps (50→25)        | 0%             | 2x                | Small
```

### Deployment Checklist

```
✅ Model downloaded at build time (not runtime)
✅ Model loaded in @modal.enter() (not per request)
✅ xformers enabled for memory efficiency
✅ Appropriate scheduler selected (UniPC/DPM-Solver)
✅ torch.compile() applied (if using PyTorch 2.0+)
✅ GPU selected based on VRAM needs
✅ Container idle timeout set (avoid cold starts)
✅ Error handling and logging implemented
✅ Health check endpoint available
✅ Monitoring for inference time and errors
```

---

## Anti-Patterns

❌ **Loading model on every request**: Cold start every time (5-30 seconds)
✅ Load once in @modal.enter(), reuse across requests

❌ **Not enabling xformers**: Wasting 30-40% memory
✅ Always enable: `pipe.enable_xformers_memory_efficient_attention()`

❌ **Using DDPM scheduler**: 50-100 steps required
✅ Use UniPC, DPM-Solver (20-30 steps sufficient)

❌ **Running without torch.compile()**: Missing free 20-30% speedup
✅ Compile UNet with PyTorch 2.0+ for production

❌ **Wrong GPU selection**: Overpaying or OOM errors
✅ L40S for SD 1.5/SDXL with optimizations, A100 for max performance

❌ **Not setting container_idle_timeout**: Constant cold starts
✅ Set to 300-600 seconds to keep container warm

❌ **Ignoring memory leaks**: VRAM gradually fills
✅ Clear cache between requests: `torch.cuda.empty_cache()`

❌ **Synchronous API blocking worker**: Poor concurrency
✅ Use async or queue-based API for production

❌ **No warmup after torch.compile()**: First request very slow
✅ Run dummy inference after compilation

---

## Related Skills

- `diffusion-model-basics.md` - Core diffusion concepts and inference
- `diffusion-finetuning.md` - Fine-tuning models for custom use cases
- `modal-gpu-workloads.md` - GPU selection and configuration
- `modal-web-endpoints.md` - FastAPI endpoint patterns
- `modal-functions-basics.md` - Modal fundamentals and decorators
- `lora-peft-techniques.md` - LoRA for efficient fine-tuning

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
