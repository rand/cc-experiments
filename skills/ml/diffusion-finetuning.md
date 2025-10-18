---
name: ml-diffusion-finetuning
description: Fine-tuning diffusion models for custom styles or subjects
---



# Diffusion Fine-Tuning

**Scope**: Fine-tuning diffusion models with DreamBooth, LoRA, textual inversion, dataset preparation
**Lines**: ~360
**Last Updated**: 2025-10-18

## When to Use This Skill

Activate this skill when:
- Fine-tuning diffusion models for custom styles or subjects
- Training DreamBooth models for specific people, objects, or concepts
- Implementing LoRA (Low-Rank Adaptation) for efficient fine-tuning
- Using textual inversion to add new concepts without model modification
- Preparing datasets for diffusion model training
- Debugging overfitting or underfitting in fine-tuned models
- Merging multiple LoRAs or checkpoints
- Optimizing training hyperparameters for quality and speed

## Core Concepts

### Fine-Tuning Approaches

**Full Fine-Tuning**:
- Train entire model (billions of parameters)
- Requires massive compute (A100/H100 for days)
- Best quality but extremely expensive
- Risk of catastrophic forgetting

**DreamBooth**:
- Fine-tune subset of model on 3-20 images
- Preserves general knowledge with regularization
- Moderate compute (A100 for 30-60 minutes)
- Best for specific subjects (people, pets, objects)

**LoRA (Low-Rank Adaptation)**:
- Train small adapter matrices (rank 4-128)
- Only 0.5-5% of model parameters
- Fast training (10-30 minutes on A100)
- Easy to share and merge (10-100MB files)

**Textual Inversion**:
- Learn new token embedding (1-8 vectors)
- Model weights frozen, only embedding trained
- Very fast (5-15 minutes on A100)
- Limited flexibility but lightweight

### DreamBooth Theory

**Core Idea**: Fine-tune model to associate trigger word with specific subject

**Training Process**:
1. Collect 3-20 images of subject
2. Choose unique trigger word (e.g., "sks person", "xyz dog")
3. Fine-tune model with caption: "[trigger] [class]"
4. Use regularization images to prevent overfitting

**Regularization**: Generate ~100-200 images of class (e.g., "person", "dog") to maintain general knowledge

**Key Parameters**:
- Learning rate: 1e-6 to 5e-6 (lower = safer)
- Training steps: 500-2000 (depends on dataset size)
- Regularization weight: 0.5-1.0

### LoRA for Diffusion

**Architecture**: Add low-rank matrices to attention layers

```
W_modified = W_pretrained + α * (A × B)
where A is rxd, B is dxr (r << d)
```

**Rank Selection**:
- Rank 4-8: Simple styles, fast training, small files
- Rank 16-32: Complex styles, balanced
- Rank 64-128: Maximum flexibility, slower training

**Benefits over Full Fine-Tuning**:
- 100x faster training
- 1000x smaller files (10-100MB vs 2-7GB)
- No catastrophic forgetting
- Easy to merge multiple LoRAs
- Can be applied/removed at inference

### Dataset Preparation

**Image Requirements**:
- **Quantity**: 3-5 (minimum), 10-20 (ideal), 50+ (style training)
- **Quality**: High resolution, clear subject, good lighting
- **Diversity**: Different angles, poses, lighting, backgrounds
- **Consistency**: Same subject, avoid multiple people/objects

**Captioning**:
- DreamBooth: "[trigger] [class]" (e.g., "sks person")
- LoRA: Descriptive captions (helps generalization)
- Textual Inversion: Fixed template with trigger word

**Data Augmentation**: Not recommended (model handles variation)

---

## Patterns

### DreamBooth Training (diffusers)

```python
from diffusers import StableDiffusionPipeline, DreamBoothTrainer
from diffusers.utils import make_image_grid
import torch

# 1. Prepare dataset
# - instance_images/: Your 10-20 images
# - class_images/: 100-200 regularization images (generate with SD)

# 2. Generate regularization images (one-time)
pipe = StableDiffusionPipeline.from_pretrained(
    "runwayml/stable-diffusion-v1-5",
    torch_dtype=torch.float16,
).to("cuda")

class_prompt = "a photo of a person"  # Match your subject class
for i in range(200):
    image = pipe(class_prompt, num_inference_steps=50).images[0]
    image.save(f"class_images/{i:04d}.png")

# 3. Train DreamBooth
from accelerate import Accelerator
from diffusers import DDPMScheduler

accelerator = Accelerator(mixed_precision="fp16")

# Training config
config = {
    "pretrained_model": "runwayml/stable-diffusion-v1-5",
    "instance_data_dir": "./instance_images",
    "class_data_dir": "./class_images",
    "instance_prompt": "a photo of sks person",  # Your trigger
    "class_prompt": "a photo of a person",       # Class for regularization
    "learning_rate": 5e-6,
    "max_train_steps": 800,
    "train_batch_size": 1,
    "gradient_accumulation_steps": 1,
    "prior_preservation": True,
    "prior_preservation_weight": 1.0,
    "output_dir": "./dreambooth_output",
}

# Note: Full training script requires ~200 lines
# Use diffusers training script: examples/dreambooth/train_dreambooth.py
```

**Command-line training** (recommended):
```bash
accelerate launch train_dreambooth.py \
  --pretrained_model_name_or_path="runwayml/stable-diffusion-v1-5" \
  --instance_data_dir="./instance_images" \
  --class_data_dir="./class_images" \
  --output_dir="./dreambooth_output" \
  --instance_prompt="a photo of sks person" \
  --class_prompt="a photo of a person" \
  --resolution=512 \
  --train_batch_size=1 \
  --gradient_accumulation_steps=1 \
  --learning_rate=5e-6 \
  --lr_scheduler="constant" \
  --lr_warmup_steps=0 \
  --max_train_steps=800 \
  --prior_preservation \
  --prior_loss_weight=1.0
```

### LoRA Training (diffusers + PEFT)

```python
import modal
from pathlib import Path

# Modal deployment for LoRA training
app = modal.App("lora-training")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "diffusers==0.30.0",
        "transformers==4.44.0",
        "accelerate==0.33.0",
        "peft==0.11.0",
        "bitsandbytes==0.43.0",
        "torch==2.1.0",
        "torchvision==0.16.0",
        "xformers==0.0.27",
    )
)

@app.function(
    gpu="A100",  # 40GB VRAM recommended
    image=image,
    timeout=3600,  # 1 hour
    volumes={"/data": modal.Volume.from_name("lora-data")},
)
def train_lora(
    instance_images_dir: str,
    instance_prompt: str,
    output_name: str,
    steps: int = 1000,
    rank: int = 16,
    learning_rate: float = 1e-4,
):
    """Train LoRA for Stable Diffusion"""
    from diffusers import StableDiffusionPipeline
    from peft import LoraConfig, get_peft_model
    import torch
    from torch.utils.data import Dataset, DataLoader
    from PIL import Image
    import os

    # Load base model
    pipe = StableDiffusionPipeline.from_pretrained(
        "runwayml/stable-diffusion-v1-5",
        torch_dtype=torch.float16,
    ).to("cuda")

    # Configure LoRA
    lora_config = LoraConfig(
        r=rank,                    # Rank (4-128)
        lora_alpha=rank,           # Scaling factor
        target_modules=[           # Which layers to adapt
            "to_q", "to_k", "to_v", "to_out.0"
        ],
        lora_dropout=0.0,
        bias="none",
    )

    # Apply LoRA to UNet
    pipe.unet = get_peft_model(pipe.unet, lora_config)
    pipe.unet.print_trainable_parameters()

    # Dataset
    class DreamBoothDataset(Dataset):
        def __init__(self, images_dir, prompt):
            self.images = [
                os.path.join(images_dir, f)
                for f in os.listdir(images_dir)
                if f.endswith(('.png', '.jpg', '.jpeg'))
            ]
            self.prompt = prompt

        def __len__(self):
            return len(self.images)

        def __getitem__(self, idx):
            image = Image.open(self.images[idx]).convert("RGB")
            image = image.resize((512, 512))
            return {"image": image, "prompt": self.prompt}

    dataset = DreamBoothDataset(instance_images_dir, instance_prompt)
    dataloader = DataLoader(dataset, batch_size=1, shuffle=True)

    # Optimizer
    optimizer = torch.optim.AdamW(
        pipe.unet.parameters(),
        lr=learning_rate,
        betas=(0.9, 0.999),
        weight_decay=1e-2,
    )

    # Training loop
    pipe.unet.train()
    for step in range(steps):
        batch = next(iter(dataloader))

        # Forward pass
        latents = pipe.vae.encode(batch["image"]).latent_dist.sample()
        latents = latents * pipe.vae.config.scaling_factor

        # Add noise
        noise = torch.randn_like(latents)
        timesteps = torch.randint(0, pipe.scheduler.config.num_train_timesteps, (1,))

        noisy_latents = pipe.scheduler.add_noise(latents, noise, timesteps)

        # Predict noise
        encoder_hidden_states = pipe.encode_prompt(batch["prompt"])
        noise_pred = pipe.unet(noisy_latents, timesteps, encoder_hidden_states).sample

        # Loss
        loss = torch.nn.functional.mse_loss(noise_pred, noise)

        # Backward
        loss.backward()
        optimizer.step()
        optimizer.zero_grad()

        if step % 100 == 0:
            print(f"Step {step}/{steps}, Loss: {loss.item():.4f}")

    # Save LoRA weights
    output_path = f"/data/{output_name}"
    pipe.unet.save_pretrained(output_path)
    print(f"LoRA saved to {output_path}")

    return output_path
```

**Simpler approach using diffusers training script**:
```bash
accelerate launch train_dreambooth_lora.py \
  --pretrained_model_name_or_path="runwayml/stable-diffusion-v1-5" \
  --instance_data_dir="./instance_images" \
  --output_dir="./lora_output" \
  --instance_prompt="a photo of sks person" \
  --resolution=512 \
  --train_batch_size=1 \
  --gradient_accumulation_steps=1 \
  --learning_rate=1e-4 \
  --lr_scheduler="constant" \
  --lr_warmup_steps=0 \
  --max_train_steps=1000 \
  --use_lora \
  --lora_rank=16
```

### Using Trained LoRA

```python
from diffusers import StableDiffusionPipeline
import torch

# Load base model
pipe = StableDiffusionPipeline.from_pretrained(
    "runwayml/stable-diffusion-v1-5",
    torch_dtype=torch.float16,
).to("cuda")

# Load LoRA weights
pipe.unet.load_attn_procs("./lora_output")

# Generate with LoRA
prompt = "a photo of sks person as an astronaut"
image = pipe(
    prompt=prompt,
    num_inference_steps=30,
    guidance_scale=7.5,
).images[0]

image.save("lora_output.png")
```

### Merging Multiple LoRAs

```python
from diffusers import StableDiffusionPipeline
from safetensors.torch import load_file
import torch

pipe = StableDiffusionPipeline.from_pretrained(
    "runwayml/stable-diffusion-v1-5",
    torch_dtype=torch.float16,
).to("cuda")

# Load multiple LoRAs with different weights
lora_weights = [
    ("./lora_style_1", 0.7),   # 70% influence
    ("./lora_style_2", 0.5),   # 50% influence
    ("./lora_subject", 1.0),   # 100% influence
]

# Apply LoRAs
for lora_path, weight in lora_weights:
    pipe.load_lora_weights(lora_path, adapter_name=lora_path)
    pipe.set_adapters([lora_path], adapter_weights=[weight])

# Generate with merged LoRAs
prompt = "sks person in xyz style"
image = pipe(prompt).images[0]
```

### Textual Inversion

```python
# Textual inversion training (simplified)
from diffusers import StableDiffusionPipeline
import torch

pipe = StableDiffusionPipeline.from_pretrained(
    "runwayml/stable-diffusion-v1-5",
    torch_dtype=torch.float16,
).to("cuda")

# Initialize new token embedding
placeholder_token = "<my-concept>"
num_vectors = 1  # Can use 2-8 for complex concepts

# Add token to tokenizer
pipe.tokenizer.add_tokens([placeholder_token])
pipe.text_encoder.resize_token_embeddings(len(pipe.tokenizer))

# Initialize embedding (copy from similar word)
token_id = pipe.tokenizer.convert_tokens_to_ids(placeholder_token)
similar_token_id = pipe.tokenizer.convert_tokens_to_ids("person")

with torch.no_grad():
    pipe.text_encoder.get_input_embeddings().weight[token_id] = \
        pipe.text_encoder.get_input_embeddings().weight[similar_token_id].clone()

# Training: Only optimize new embedding, freeze rest
# (Full training code ~150 lines, use diffusers script)
```

**Command-line training**:
```bash
accelerate launch textual_inversion.py \
  --pretrained_model_name_or_path="runwayml/stable-diffusion-v1-5" \
  --train_data_dir="./instance_images" \
  --learnable_property="object" \
  --placeholder_token="<my-concept>" \
  --initializer_token="person" \
  --resolution=512 \
  --train_batch_size=1 \
  --learning_rate=5e-4 \
  --max_train_steps=3000 \
  --output_dir="./textual_inversion_output"
```

### Dataset Preparation Script

```python
from PIL import Image
import os
from pathlib import Path

def prepare_dreambooth_dataset(
    input_dir: str,
    output_dir: str,
    target_size: int = 512,
    min_images: int = 5,
):
    """Prepare and validate DreamBooth dataset"""

    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # Supported formats
    image_extensions = {'.jpg', '.jpeg', '.png', '.webp'}

    # Collect images
    images = [
        f for f in input_path.iterdir()
        if f.suffix.lower() in image_extensions
    ]

    if len(images) < min_images:
        raise ValueError(f"Need at least {min_images} images, found {len(images)}")

    print(f"Processing {len(images)} images...")

    # Process each image
    for i, img_path in enumerate(images):
        img = Image.open(img_path).convert("RGB")

        # Resize to square, maintaining aspect ratio
        width, height = img.size
        min_dim = min(width, height)

        # Center crop to square
        left = (width - min_dim) // 2
        top = (height - min_dim) // 2
        img = img.crop((left, top, left + min_dim, top + min_dim))

        # Resize to target size
        img = img.resize((target_size, target_size), Image.LANCZOS)

        # Save
        output_file = output_path / f"{i:04d}.png"
        img.save(output_file, "PNG")
        print(f"Processed: {output_file}")

    print(f"Dataset ready: {len(images)} images in {output_path}")

    # Create caption file
    caption_file = output_path / "captions.txt"
    with open(caption_file, "w") as f:
        f.write("# Edit this file to add captions\n")
        f.write("# Format: image_name.png: caption\n\n")
        for i in range(len(images)):
            f.write(f"{i:04d}.png: a photo of sks person\n")

    print(f"Caption template created: {caption_file}")

# Usage
prepare_dreambooth_dataset(
    input_dir="./raw_images",
    output_dir="./instance_images",
    target_size=512,
)
```

---

## Quick Reference

### Method Comparison

```
Method            | Train Time | File Size | Quality | Flexibility | Best For
------------------|------------|-----------|---------|-------------|------------------
Full Fine-Tune    | Days       | 2-7GB     | Best    | Highest     | Max quality, budget unlimited
DreamBooth        | 30-60 min  | 2-7GB     | High    | High        | Specific subjects, traditional
LoRA              | 10-30 min  | 10-100MB  | High    | High        | Modern default, shareable
Textual Inversion | 5-15 min   | <1MB      | Medium  | Low         | Simple concepts, lightweight
```

### Hyperparameter Guidelines

```
Parameter                  | DreamBooth | LoRA     | Textual Inv
---------------------------|------------|----------|-------------
Learning Rate              | 5e-6       | 1e-4     | 5e-4
Training Steps             | 800-2000   | 1000     | 3000
Batch Size                 | 1          | 1-2      | 1
Gradient Accumulation      | 1-4        | 1-2      | 1
LoRA Rank                  | N/A        | 16-32    | N/A
Number of Images           | 10-20      | 10-50    | 5-15
Regularization Weight      | 1.0        | Optional | N/A
```

### Training Checklist

```
✅ Dataset: 5-20 images, high quality, diverse angles
✅ Images: Resized to 512x512, square crop, PNG format
✅ Captions: Consistent format with trigger word
✅ Regularization: 100-200 class images (DreamBooth)
✅ GPU: A100 recommended (T4 works but slower)
✅ Learning Rate: Start conservative (lower is safer)
✅ Checkpoints: Save every 100-200 steps
✅ Validation: Test generation every 200 steps
✅ Monitoring: Track loss, watch for overfitting
```

### Overfitting Signs

```
❌ Training loss near zero but validation loss high
❌ Generated images identical to training images
❌ Can only generate exact training poses/angles
❌ Poor generalization to new prompts
❌ Artifacts or distortions in novel scenes

✅ Solution: Reduce steps, lower learning rate, add regularization, increase dataset diversity
```

---

## Anti-Patterns

❌ **Too few training images**: Using 1-3 images
✅ Use 5-10 minimum, 10-20 ideal for DreamBooth/LoRA

❌ **Overfitting with too many steps**: Training until loss = 0
✅ Monitor validation, stop at 800-1500 steps (DreamBooth), 1000 (LoRA)

❌ **No regularization (DreamBooth)**: Model forgets general knowledge
✅ Always use prior preservation with 100-200 class images

❌ **Generic trigger words**: Using "person", "dog" (conflicts with model)
✅ Use unique identifiers: "sks person", "xyz dog"

❌ **Wrong LoRA rank**: Using rank 128 for simple styles
✅ Start with rank 16, increase only if needed

❌ **High learning rate**: Using 1e-3 or higher
✅ Use 5e-6 (DreamBooth), 1e-4 (LoRA), 5e-4 (textual inversion)

❌ **Low quality dataset**: Blurry, inconsistent, multiple subjects
✅ High resolution, clear subject, consistent lighting, single subject

❌ **No validation during training**: Training blind
✅ Generate test images every 200 steps to monitor progress

❌ **Training on CPU or small GPU**: T4 with SDXL
✅ Use A100 for SDXL, L40S/A100 for SD 1.5

---

## Related Skills

- `diffusion-model-basics.md` - Core diffusion concepts and architecture
- `stable-diffusion-deployment.md` - Deploying fine-tuned models to production
- `lora-peft-techniques.md` - General LoRA/PEFT concepts
- `modal-gpu-workloads.md` - GPU training infrastructure
- `modal-functions-basics.md` - Modal deployment patterns

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
