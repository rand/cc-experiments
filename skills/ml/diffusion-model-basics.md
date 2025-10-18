---
name: ml-diffusion-model-basics
description: Understanding diffusion model theory and mechanics (forward/reverse process)
---



# Diffusion Model Basics

**Scope**: Diffusion model fundamentals, architectures, inference pipelines, and model selection
**Lines**: ~340
**Last Updated**: 2025-10-18

## When to Use This Skill

Activate this skill when:
- Understanding diffusion model theory and mechanics (forward/reverse process)
- Implementing image generation with diffusion models
- Selecting appropriate diffusion models for specific use cases
- Configuring sampling parameters (schedulers, guidance, steps)
- Debugging diffusion model inference issues
- Comparing diffusion architectures (DDPM, DDIM, Stable Diffusion, SDXL)
- Optimizing inference quality vs speed tradeoffs

## Core Concepts

### Forward and Reverse Diffusion Process

**Forward Process (Noise Addition)**:
- Gradually adds Gaussian noise to data over T timesteps
- q(x_t | x_{t-1}) = N(x_t; √(1-β_t) x_{t-1}, β_t I)
- β_t is variance schedule (increases from β_1 to β_T)
- After T steps, x_T ≈ N(0, I) (pure noise)

**Reverse Process (Denoising)**:
- Learns to reverse noise addition: p_θ(x_{t-1} | x_t)
- Neural network predicts noise ε_θ(x_t, t) at each timestep
- Iteratively removes noise to generate samples
- Conditioned on text embeddings for text-to-image

**Key Insight**: Training predicts noise, inference removes it step-by-step

### Noise Scheduling

**Purpose**: Controls noise addition/removal over time

**Common Schedulers**:
- **DDPM** (Denoising Diffusion Probabilistic Models): Original, slow but high quality
- **DDIM** (Denoising Diffusion Implicit Models): Deterministic, 10-50x faster
- **PNDM** (Pseudo Numerical Methods): Better numerical stability
- **DPM-Solver**: Adaptive step size, excellent speed/quality
- **Euler/Euler Ancestral**: Simple, good for artistic styles
- **UniPC**: Fast, high quality, good default choice

**Scheduler Selection**:
- Quality priority → DDPM, DPM-Solver++
- Speed priority → DDIM, DPM-Solver, UniPC
- Artistic/creative → Euler Ancestral
- Deterministic → DDIM, DPM-Solver

### UNet Architecture

**Core Component**: Modified UNet backbone for noise prediction

**Architecture**:
- **Encoder**: Downsampling with ResNet blocks + attention
- **Bottleneck**: Dense attention layers (most compute)
- **Decoder**: Upsampling with skip connections
- **Time Embedding**: Sinusoidal positional encoding for timestep t
- **Cross-Attention**: Inject text conditioning (CLIP embeddings)

**Attention Mechanisms**:
- Self-attention: Within image features
- Cross-attention: Text-to-image conditioning
- Spatial attention: Preserve spatial structure

### Latent Diffusion Models (Stable Diffusion)

**Key Innovation**: Operate in compressed latent space, not pixel space

**Components**:
- **VAE Encoder**: Compress images to latent space (8x8x reduction)
- **UNet**: Diffusion in latent space (64x64 instead of 512x512)
- **VAE Decoder**: Reconstruct images from latents
- **Text Encoder**: CLIP (SD 1.x/2.x) or T5/CLIP (SDXL, SD3)

**Benefits**:
- 8-10x faster than pixel-space diffusion
- Lower VRAM requirements
- Maintains image quality
- Enables higher resolutions

---

## Patterns

### Basic Text-to-Image Generation (Stable Diffusion 1.5)

```python
from diffusers import StableDiffusionPipeline
import torch

# Load pipeline
pipe = StableDiffusionPipeline.from_pretrained(
    "runwayml/stable-diffusion-v1-5",
    torch_dtype=torch.float16,
    safety_checker=None,  # Optional: disable for speed
)
pipe = pipe.to("cuda")

# Generate image
prompt = "A serene mountain landscape at sunset, highly detailed, 4k"
negative_prompt = "blurry, low quality, distorted, ugly"

image = pipe(
    prompt=prompt,
    negative_prompt=negative_prompt,
    num_inference_steps=50,  # More steps = better quality
    guidance_scale=7.5,      # How strongly to follow prompt
    height=512,
    width=512,
    generator=torch.Generator("cuda").manual_seed(42),  # Reproducibility
).images[0]

image.save("output.png")
```

**When to use**:
- General purpose text-to-image generation
- 512x512 images (native resolution)
- Quick prototyping and iteration

### SDXL for Higher Quality

```python
from diffusers import StableDiffusionXLPipeline
import torch

# SDXL has better text understanding and higher resolution
pipe = StableDiffusionXLPipeline.from_pretrained(
    "stabilityai/stable-diffusion-xl-base-1.0",
    torch_dtype=torch.float16,
    variant="fp16",
    use_safetensors=True,
)
pipe = pipe.to("cuda")

# Enable CPU offloading for lower VRAM (slower but uses ~6GB vs 12GB)
# pipe.enable_model_cpu_offload()

prompt = "Astronaut riding a horse on Mars, photorealistic, 8k uhd"
negative_prompt = "cartoon, painting, illustration"

image = pipe(
    prompt=prompt,
    negative_prompt=negative_prompt,
    num_inference_steps=40,  # SDXL converges faster
    guidance_scale=7.0,      # Lower than SD 1.5
    height=1024,             # Native resolution
    width=1024,
).images[0]

image.save("sdxl_output.png")
```

**Benefits**:
- Better text comprehension (multiple text encoders)
- Higher native resolution (1024x1024)
- Improved image quality and details
- Better anatomy and composition

### Scheduler Comparison

```python
from diffusers import (
    StableDiffusionPipeline,
    DDIMScheduler,
    DPMSolverMultistepScheduler,
    EulerAncestralDiscreteScheduler,
    UniPCMultistepScheduler,
)
import torch

pipe = StableDiffusionPipeline.from_pretrained(
    "runwayml/stable-diffusion-v1-5",
    torch_dtype=torch.float16,
)
pipe = pipe.to("cuda")

prompt = "A magical forest with glowing mushrooms"

# Fast and deterministic (recommended default)
pipe.scheduler = UniPCMultistepScheduler.from_config(pipe.scheduler.config)
image_unipc = pipe(prompt, num_inference_steps=20).images[0]

# High quality, slower
pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
image_dpm = pipe(prompt, num_inference_steps=25).images[0]

# Artistic/creative (non-deterministic)
pipe.scheduler = EulerAncestralDiscreteScheduler.from_config(pipe.scheduler.config)
image_euler = pipe(prompt, num_inference_steps=30).images[0]

# Original DDIM (fast, deterministic)
pipe.scheduler = DDIMScheduler.from_config(pipe.scheduler.config)
image_ddim = pipe(prompt, num_inference_steps=50).images[0]
```

**When to use each**:
- UniPC: Default choice (fast + high quality)
- DPM-Solver: Maximum quality, moderate speed
- Euler Ancestral: Creative/artistic styles
- DDIM: When you need exact determinism

### Guidance Scale Tuning

```python
import torch
from diffusers import StableDiffusionPipeline

pipe = StableDiffusionPipeline.from_pretrained(
    "runwayml/stable-diffusion-v1-5",
    torch_dtype=torch.float16,
).to("cuda")

prompt = "A red apple on a wooden table"

# Generate with different guidance scales
guidance_scales = [1.0, 3.0, 7.5, 12.0, 20.0]
images = []

for scale in guidance_scales:
    image = pipe(
        prompt=prompt,
        guidance_scale=scale,
        num_inference_steps=30,
        generator=torch.Generator("cuda").manual_seed(42),
    ).images[0]
    images.append(image)
    image.save(f"guidance_{scale}.png")

# Guidance scale effects:
# 1.0-3.0: More creative, less prompt adherence, diverse
# 7.0-9.0: Balanced (recommended range)
# 10.0-15.0: Strong prompt adherence, less variation
# 15.0+: Over-saturated, artifacts, "burnt" look
```

**Guidance Scale Guidelines**:
- 1.0-3.0: Exploratory, artistic freedom
- 7.0-8.0: General purpose (SD 1.5)
- 5.0-7.0: General purpose (SDXL)
- 10.0+: When prompt is very specific

### Batch Generation

```python
from diffusers import StableDiffusionPipeline
import torch

pipe = StableDiffusionPipeline.from_pretrained(
    "runwayml/stable-diffusion-v1-5",
    torch_dtype=torch.float16,
).to("cuda")

prompt = "A futuristic cityscape at night"

# Generate multiple images in one call (efficient)
images = pipe(
    prompt=prompt,
    num_images_per_prompt=4,  # Batch size (watch VRAM)
    num_inference_steps=30,
    guidance_scale=7.5,
).images

# Save all images
for i, img in enumerate(images):
    img.save(f"batch_{i}.png")
```

**VRAM considerations**:
- SD 1.5: ~2GB per image at 512x512
- SDXL: ~4-5GB per image at 1024x1024
- Reduce batch size if OOM

### Image-to-Image Generation

```python
from diffusers import StableDiffusionImg2ImgPipeline
from PIL import Image
import torch

# Load img2img pipeline
pipe = StableDiffusionImg2ImgPipeline.from_pretrained(
    "runwayml/stable-diffusion-v1-5",
    torch_dtype=torch.float16,
).to("cuda")

# Load input image
init_image = Image.open("input.png").convert("RGB")
init_image = init_image.resize((512, 512))

prompt = "A watercolor painting of the same scene"

# Generate variation
image = pipe(
    prompt=prompt,
    image=init_image,
    strength=0.75,  # 0.0 = no change, 1.0 = full generation
    num_inference_steps=50,
    guidance_scale=7.5,
).images[0]

image.save("img2img_output.png")
```

**Strength parameter**:
- 0.0-0.3: Minor adjustments, style transfer
- 0.4-0.6: Moderate changes, keep composition
- 0.7-0.9: Major changes, loose reference
- 0.9-1.0: Almost like text-to-image

### Inpainting

```python
from diffusers import StableDiffusionInpaintPipeline
from PIL import Image
import torch

pipe = StableDiffusionInpaintPipeline.from_pretrained(
    "runwayml/stable-diffusion-inpainting",
    torch_dtype=torch.float16,
).to("cuda")

# Load image and mask (white = inpaint area)
image = Image.open("input.png").convert("RGB").resize((512, 512))
mask = Image.open("mask.png").convert("RGB").resize((512, 512))

prompt = "A red sports car"

result = pipe(
    prompt=prompt,
    image=image,
    mask_image=mask,
    num_inference_steps=50,
    guidance_scale=7.5,
).images[0]

result.save("inpainted.png")
```

**Use cases**:
- Object removal/replacement
- Background changes
- Detail refinement
- Creative editing

---

## Quick Reference

### Model Comparison

```
Model          | Resolution | VRAM   | Speed | Quality | Best For
---------------|------------|--------|-------|---------|------------------
SD 1.5         | 512x512    | 4GB    | Fast  | Good    | General, fast iteration
SD 2.1         | 768x768    | 6GB    | Mid   | Better  | Higher res, improved quality
SDXL 1.0       | 1024x1024  | 8-12GB | Slow  | Best    | Production, high quality
SD 3.0         | 1024x1024  | 10GB+  | Mid   | Best    | Latest, best text understanding
```

### Inference Parameters

```
Parameter             | Range      | Default | Effect
----------------------|------------|---------|--------------------------------
num_inference_steps   | 20-100     | 50      | Quality vs speed (diminishing returns >50)
guidance_scale        | 1.0-20.0   | 7.5     | Prompt adherence (7-9 optimal)
height/width          | 512-1024   | 512     | Output resolution (multiple of 64)
num_images_per_prompt | 1-8        | 1       | Batch generation (VRAM limited)
strength (img2img)    | 0.0-1.0    | 0.8     | How much to change input
```

### Scheduler Selection

```
✅ DO: Use UniPC or DPM-Solver for best quality/speed balance
✅ DO: Use Euler Ancestral for artistic/creative outputs
✅ DO: Reduce steps with better schedulers (20-30 vs 50)
✅ DO: Match scheduler to use case (deterministic vs creative)

❌ DON'T: Use DDPM unless you need exact original algorithm
❌ DON'T: Use 100+ steps (waste of compute, minimal gain)
❌ DON'T: Ignore scheduler choice (huge impact on results)
```

### Prompt Engineering

```
✅ DO: Be specific and descriptive
✅ DO: Use quality tags ("highly detailed", "4k", "professional")
✅ DO: Use negative prompts to avoid common issues
✅ DO: Mention style/medium if important ("oil painting", "photograph")

❌ DON'T: Be vague or ambiguous
❌ DON'T: Forget negative prompts (prevents common artifacts)
❌ DON'T: Over-complicate (model has limits on prompt length)
```

---

## Anti-Patterns

❌ **Using default scheduler without consideration**: DDPM is slow, better options exist
✅ Use UniPC, DPM-Solver, or Euler Ancestral based on use case

❌ **Ignoring guidance scale**: Using default 7.5 for everything
✅ Tune guidance scale (7-9 for SD 1.5, 5-7 for SDXL)

❌ **Too many inference steps**: Using 100+ steps for marginal gains
✅ Use 20-30 steps with good scheduler, 40-50 max for quality

❌ **Wrong resolution**: Generating 1024x1024 with SD 1.5
✅ Use native resolution (512 for SD 1.5, 1024 for SDXL)

❌ **No negative prompts**: Forgetting to specify what to avoid
✅ Always use negative prompts ("blurry, low quality, distorted")

❌ **Not setting seed for debugging**: Non-reproducible results
✅ Use fixed seed during development/debugging

❌ **Loading full precision models**: Using float32 on GPU
✅ Use float16/bfloat16 for 2x speed and 50% VRAM reduction

❌ **Ignoring safety checker overhead**: Keeping it on when not needed
✅ Disable safety checker for faster inference (if appropriate)

---

## Related Skills

- `stable-diffusion-deployment.md` - Production deployment, API setup, optimization
- `diffusion-finetuning.md` - Fine-tuning with DreamBooth, LoRA, textual inversion
- `modal-gpu-workloads.md` - GPU selection and configuration for diffusion models
- `modal-web-endpoints.md` - Creating API endpoints for diffusion inference
- `lora-peft-techniques.md` - LoRA for parameter-efficient fine-tuning

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
