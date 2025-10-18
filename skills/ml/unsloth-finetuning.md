---
name: ml-unsloth-finetuning
description: Fine-tuning LLMs (Llama, Mistral, Qwen) efficiently
---



# Unsloth Fine-Tuning

**Scope**: Fast LLM fine-tuning with Unsloth, memory optimization, multi-GPU, Flash Attention
**Lines**: ~350
**Last Updated**: 2025-10-18

## When to Use This Skill

Activate this skill when:
- Fine-tuning LLMs (Llama, Mistral, Qwen) efficiently
- Working in memory-constrained GPU environments
- Needing 2-5x faster training than standard methods
- Optimizing training costs with reduced memory usage
- Requiring rapid iteration on fine-tuning experiments
- Training with consumer GPUs (24GB VRAM or less)

## Core Concepts

### Unsloth Architecture

**Speed Optimizations**:
- Flash Attention 2 integration for 2x faster attention
- Custom CUDA kernels for backward pass optimization
- Optimized RoPE (Rotary Position Embeddings) computation
- Fused layernorm and cross-entropy operations
- 4-bit quantization with minimal accuracy loss

**Memory Efficiency**:
- Reduces VRAM usage by 30-60% vs standard training
- Enables larger batch sizes on same hardware
- Supports gradient checkpointing out of the box
- Efficient mixed precision (bfloat16) handling

**Compatibility**:
- Works with PEFT/LoRA for parameter-efficient training
- Supports Hugging Face Transformers ecosystem
- Compatible with Modal.com GPU workloads
- Drop-in replacement for standard fine-tuning

### Supported Models

**Llama Family**:
- Llama 3.2 (1B, 3B), Llama 3.1 (8B, 70B, 405B)
- Llama 3 (8B, 70B), Llama 2 (7B, 13B, 70B)

**Mistral Family**:
- Mistral 7B v0.3, Mixtral 8x7B, 8x22B
- Mistral Small, Mistral NeMo

**Other Models**:
- Qwen 2.5 (0.5B - 72B), Qwen 2 (0.5B - 72B)
- Gemma 2 (2B, 9B, 27B), Phi-3.5 (mini)
- TinyLlama, OpenELM variants

### Quantization Strategies

**4-bit QLoRA** (Recommended):
- Uses NF4 (Normal Float 4) quantization
- Maintains 99%+ of full precision performance
- Reduces memory by 4x vs FP16
- Allows fine-tuning 70B models on 48GB GPU

**16-bit Training**:
- Full bfloat16 precision for maximum quality
- Requires 2-4x more VRAM
- Recommended for models <13B with sufficient VRAM

---

## Patterns

### Basic Llama 3 Fine-Tuning

```python
from unsloth import FastLanguageModel
import torch

# Load model with 4-bit quantization
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="unsloth/llama-3-8b-bnb-4bit",
    max_seq_length=2048,
    dtype=None,  # Auto-detect (bfloat16 for Ampere+)
    load_in_4bit=True,
)

# Configure LoRA
model = FastLanguageModel.get_peft_model(
    model,
    r=16,  # LoRA rank
    target_modules=[
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj"
    ],
    lora_alpha=16,
    lora_dropout=0,  # Optimized for 0 dropout
    bias="none",
    use_gradient_checkpointing="unsloth",  # Unsloth's optimized checkpointing
    random_state=3407,
)
```

### Dataset Preparation

```python
from datasets import load_dataset

# Load dataset (Alpaca format)
dataset = load_dataset("yahma/alpaca-cleaned", split="train")

# Format for instruction tuning
alpaca_prompt = """Below is an instruction that describes a task. Write a response that appropriately completes the request.

### Instruction:
{}

### Response:
{}"""

def format_prompts(examples):
    instructions = examples["instruction"]
    outputs = examples["output"]
    texts = []

    for instruction, output in zip(instructions, outputs):
        text = alpaca_prompt.format(instruction, output) + tokenizer.eos_token
        texts.append(text)

    return {"text": texts}

# Apply formatting
dataset = dataset.map(format_prompts, batched=True)
```

### Training with SFTTrainer

```python
from trl import SFTTrainer
from transformers import TrainingArguments

trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    dataset_text_field="text",
    max_seq_length=2048,
    dataset_num_proc=2,
    packing=False,  # Can make training 5x faster for short sequences
    args=TrainingArguments(
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,  # Effective batch size = 8
        warmup_steps=5,
        max_steps=60,  # Or num_train_epochs=1
        learning_rate=2e-4,
        fp16=not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_bf16_supported(),
        logging_steps=1,
        optim="adamw_8bit",  # Reduced memory optimizer
        weight_decay=0.01,
        lr_scheduler_type="linear",
        seed=3407,
        output_dir="outputs",
    ),
)

# Train
trainer_stats = trainer.train()
```

### Multi-GPU Training

```python
# Use with torchrun or Modal multi-GPU
import modal

app = modal.App("unsloth-multi-gpu")

image = (
    modal.Image.debian_slim()
    .pip_install("unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git")
    .pip_install("xformers", "trl", "peft", "accelerate")
)

@app.function(
    gpu="a100:2",  # 2x A100
    image=image,
    timeout=7200
)
def multi_gpu_training():
    from unsloth import FastLanguageModel
    from accelerate import Accelerator

    accelerator = Accelerator()

    # Model automatically distributed across GPUs
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name="unsloth/llama-3-70b-bnb-4bit",
        max_seq_length=4096,
        dtype=None,
        load_in_4bit=True,
        device_map="auto"  # Auto-distribute across GPUs
    )

    model = FastLanguageModel.get_peft_model(
        model,
        r=32,  # Higher rank for 70B model
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        lora_alpha=32,
    )

    # Train with accelerate
    # (SFTTrainer handles multi-GPU automatically)
```

### Saving and Loading

```python
# Save LoRA adapter only (small, ~100MB)
model.save_pretrained("lora_model")
tokenizer.save_pretrained("lora_model")

# Save merged model (full weights)
model.save_pretrained_merged(
    "merged_model",
    tokenizer,
    save_method="merged_16bit"  # or "lora", "merged_4bit"
)

# Push to Hugging Face Hub
model.push_to_hub_merged(
    "username/model-name",
    tokenizer,
    save_method="merged_16bit",
    token="hf_..."
)

# Load for inference
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="lora_model",
    max_seq_length=2048,
    dtype=None,
    load_in_4bit=True,
)
FastLanguageModel.for_inference(model)  # Enable fast inference mode
```

### Inference After Training

```python
# Enable fast inference (disables dropout, etc.)
FastLanguageModel.for_inference(model)

# Generate
inputs = tokenizer(
    [alpaca_prompt.format(
        "What is the capital of France?",
        ""  # Leave output empty for generation
    )],
    return_tensors="pt"
).to("cuda")

outputs = model.generate(
    **inputs,
    max_new_tokens=128,
    use_cache=True,
    temperature=1.5,
    min_p=0.1
)

print(tokenizer.batch_decode(outputs))
```

### Modal.com Deployment

```python
import modal

app = modal.App("unsloth-finetune")

image = (
    modal.Image.debian_slim()
    .pip_install(
        "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git",
        "xformers",
        "trl",
        "peft"
    )
)

volume = modal.Volume.from_name("model-volume", create_if_missing=True)

@app.function(
    gpu="l40s",  # Recommended: great price/performance
    image=image,
    volumes={"/models": volume},
    timeout=3600
)
def finetune_llama(
    dataset_name: str,
    output_path: str = "/models/finetuned"
):
    from unsloth import FastLanguageModel
    from trl import SFTTrainer
    from transformers import TrainingArguments
    from datasets import load_dataset

    # Load model
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name="unsloth/llama-3-8b-bnb-4bit",
        max_seq_length=2048,
        dtype=None,
        load_in_4bit=True,
    )

    # Apply LoRA
    model = FastLanguageModel.get_peft_model(
        model,
        r=16,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        lora_alpha=16,
    )

    # Load dataset
    dataset = load_dataset(dataset_name, split="train")

    # Train
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        dataset_text_field="text",
        max_seq_length=2048,
        args=TrainingArguments(
            per_device_train_batch_size=2,
            gradient_accumulation_steps=4,
            warmup_steps=5,
            max_steps=100,
            learning_rate=2e-4,
            fp16=not torch.cuda.is_bf16_supported(),
            bf16=torch.cuda.is_bf16_supported(),
            logging_steps=1,
            optim="adamw_8bit",
            output_dir="/tmp/output",
        ),
    )

    trainer.train()

    # Save to volume
    model.save_pretrained(output_path)
    tokenizer.save_pretrained(output_path)
    volume.commit()

    return {"status": "complete", "path": output_path}

@app.local_entrypoint()
def main():
    result = finetune_llama.remote("yahma/alpaca-cleaned")
    print(result)
```

### Chat Template Fine-Tuning

```python
# ChatML format
chat_template = """<|im_start|>system
{system}<|im_end|>
<|im_start|>user
{user}<|im_end|>
<|im_start|>assistant
{assistant}<|im_end|>"""

def format_chat(examples):
    texts = []
    for system, user, assistant in zip(
        examples["system"],
        examples["user"],
        examples["assistant"]
    ):
        text = chat_template.format(
            system=system,
            user=user,
            assistant=assistant
        ) + tokenizer.eos_token
        texts.append(text)
    return {"text": texts}

dataset = dataset.map(format_chat, batched=True)
```

---

## Quick Reference

### GPU Requirements by Model Size

```
Model Size    | 4-bit VRAM | 16-bit VRAM | Recommended GPU
--------------|------------|-------------|------------------
1-3B          | 6-8 GB     | 12-16 GB    | T4, L4
7-8B          | 12-16 GB   | 24-32 GB    | L40S
13B           | 16-20 GB   | 32-40 GB    | L40S, A100
70B           | 40-48 GB   | 140+ GB     | A100 80GB, H100
```

### Unsloth Installation

```bash
# Standard installation
pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
pip install xformers trl peft accelerate

# For CUDA 11.8
pip install "unsloth[cu118-ampere-new] @ git+https://github.com/unslothai/unsloth.git"

# For CUDA 12.1+
pip install "unsloth[cu121-ampere-new] @ git+https://github.com/unslothai/unsloth.git"
```

### Key Hyperparameters

```python
# LoRA Configuration
r = 16                    # Rank: 8-64 (higher = more params, better quality)
lora_alpha = 16           # Usually same as r
lora_dropout = 0          # Unsloth optimized for 0
target_modules = [        # All attention + MLP for best results
    "q_proj", "k_proj", "v_proj", "o_proj",
    "gate_proj", "up_proj", "down_proj"
]

# Training Configuration
batch_size = 2            # Per device (increase for larger GPUs)
gradient_accumulation = 4 # Effective batch = batch_size * accumulation
learning_rate = 2e-4      # Standard for LoRA
warmup_steps = 5          # 5-10% of total steps
max_seq_length = 2048     # Model's max (512-4096)
```

### Common Commands

```python
# Enable inference mode
FastLanguageModel.for_inference(model)

# Save adapter only
model.save_pretrained("path")

# Save merged 16-bit
model.save_pretrained_merged("path", tokenizer, save_method="merged_16bit")

# Save merged 4-bit (smallest)
model.save_pretrained_merged("path", tokenizer, save_method="merged_4bit")

# Push to Hub
model.push_to_hub_merged("user/model", tokenizer, save_method="merged_16bit")
```

---

## Anti-Patterns

❌ **Using standard Transformers for fine-tuning**: Slower and uses more memory
✅ Use Unsloth for 2-5x speedup with same results

❌ **Loading full precision models**: Wastes VRAM on consumer GPUs
✅ Always use `load_in_4bit=True` for models >7B

❌ **Wrong dtype for GPU architecture**:
```python
# ❌ Bad: Forces FP16 on Ampere+ GPUs
args = TrainingArguments(fp16=True, bf16=False)

# ✅ Good: Auto-detect best dtype
args = TrainingArguments(
    fp16=not torch.cuda.is_bf16_supported(),
    bf16=torch.cuda.is_bf16_supported()
)
```

❌ **Tiny batch sizes without gradient accumulation**: Unstable training
✅ Use `gradient_accumulation_steps` to increase effective batch size

❌ **Too many LoRA target modules**: Wastes memory for marginal gains
✅ Start with attention layers only: `["q_proj", "k_proj", "v_proj", "o_proj"]`

❌ **Ignoring sequence length**: OOM errors or wasted compute
✅ Set `max_seq_length` to actual data length (analyze dataset first)

❌ **Not using gradient checkpointing**: Runs out of VRAM
✅ Always use `use_gradient_checkpointing="unsloth"` for large models

❌ **Saving full model every epoch**: Wastes disk space
✅ Save LoRA adapter only (~100MB) or push merged model once at end

❌ **Using standard AdamW**: Higher memory usage
✅ Use `optim="adamw_8bit"` for 2x memory reduction

---

## Related Skills

- `lora-peft-techniques.md` - LoRA configuration, rank selection, merging
- `llm-dataset-preparation.md` - Dataset formatting, quality, validation
- `modal-gpu-workloads.md` - GPU selection, cost optimization, deployment
- `huggingface-autotrain.md` - Alternative no-code fine-tuning approach
- `llm-inference-optimization.md` - Post-training inference optimization
- `model-evaluation.md` - Evaluating fine-tuned model quality

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
