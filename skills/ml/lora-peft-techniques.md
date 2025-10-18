---
name: ml-lora-peft-techniques
description: Fine-tuning large models with limited GPU memory
---



# LoRA and PEFT Techniques

**Scope**: LoRA, QLoRA, adapter tuning, rank selection, merging, multi-adapter inference
**Lines**: ~340
**Last Updated**: 2025-10-18

## When to Use This Skill

Activate this skill when:
- Fine-tuning large models with limited GPU memory
- Training multiple task-specific adapters from same base model
- Reducing training time and storage costs
- Merging multiple LoRA adapters for multi-task models
- Optimizing fine-tuning hyperparameters (rank, alpha)
- Deploying memory-efficient models in production

## Core Concepts

### Parameter-Efficient Fine-Tuning (PEFT)

**What is PEFT**:
- Train only a small subset of model parameters
- Freeze base model weights
- Add small trainable "adapter" layers
- Achieves 99%+ of full fine-tuning quality
- Uses 10-100x less memory and storage

**PEFT Methods**:
- **LoRA**: Low-Rank Adaptation (most popular)
- **QLoRA**: Quantized LoRA (4-bit base model)
- **Prefix Tuning**: Learn task-specific prompts
- **Adapter Layers**: Small bottleneck layers
- **IA3**: Learned rescaling vectors

### LoRA (Low-Rank Adaptation)

**How LoRA Works**:
- Freezes original model weights W
- Adds trainable low-rank matrices A and B
- Updates: ΔW = B × A (where B is m×r, A is r×n)
- Final output: W + ΔW = W + BA
- Only trains A and B (<<< original parameters)

**Key Hyperparameters**:
- **Rank (r)**: Dimensionality of low-rank matrices (4-128)
- **Alpha**: Scaling factor for LoRA updates (usually = r)
- **Dropout**: Regularization (0-0.1, often 0 for LoRA)
- **Target Modules**: Which layers to apply LoRA to

**Memory Savings**:
- 7B model: ~28GB → ~6GB (4-bit QLoRA)
- 13B model: ~52GB → ~10GB (4-bit QLoRA)
- 70B model: ~280GB → ~48GB (4-bit QLoRA)

### QLoRA (Quantized LoRA)

**QLoRA Components**:
- 4-bit NormalFloat (NF4) quantization of base model
- Double quantization for constants
- Paged optimizers for memory efficiency
- LoRA adapters trained in bfloat16

**Benefits**:
- Train 70B models on single 48GB GPU
- Minimal quality loss vs full precision
- Faster training than 16-bit LoRA

---

## Patterns

### Basic LoRA Configuration

```python
from peft import LoraConfig, get_peft_model
from transformers import AutoModelForCausalLM

# Load base model
model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-3-8b",
    device_map="auto",
    torch_dtype="auto"
)

# Configure LoRA
lora_config = LoraConfig(
    r=16,  # Rank
    lora_alpha=16,  # Alpha (scaling)
    target_modules=[
        "q_proj",  # Query projection
        "k_proj",  # Key projection
        "v_proj",  # Value projection
        "o_proj",  # Output projection
    ],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM"
)

# Apply LoRA
model = get_peft_model(model, lora_config)

# Print trainable parameters
model.print_trainable_parameters()
# Output: trainable params: 4,194,304 || all params: 8,030,261,248 || trainable%: 0.05%
```

### QLoRA with 4-bit Quantization

```python
from transformers import AutoModelForCausalLM, BitsAndBytesConfig
from peft import LoraConfig, prepare_model_for_kbit_training, get_peft_model
import torch

# 4-bit quantization config
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",  # NormalFloat4
    bnb_4bit_compute_dtype=torch.bfloat16,  # Compute in bf16
    bnb_4bit_use_double_quant=True,  # Double quantization
)

# Load quantized model
model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-3-8b",
    quantization_config=bnb_config,
    device_map="auto",
)

# Prepare for k-bit training
model = prepare_model_for_kbit_training(model)

# Apply LoRA
lora_config = LoraConfig(
    r=64,  # Higher rank for 4-bit to compensate
    lora_alpha=128,
    target_modules=[
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj"  # MLP layers
    ],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM"
)

model = get_peft_model(model, lora_config)
```

### Target Module Selection

```python
# Attention-only (memory efficient)
target_modules = ["q_proj", "v_proj"]

# All attention (good balance)
target_modules = ["q_proj", "k_proj", "v_proj", "o_proj"]

# Attention + MLP (best quality)
target_modules = [
    "q_proj", "k_proj", "v_proj", "o_proj",
    "gate_proj", "up_proj", "down_proj"
]

# Auto-detect all linear layers
import re

def find_all_linear_names(model):
    """Find all linear layer names in model."""
    cls = torch.nn.Linear
    lora_module_names = set()

    for name, module in model.named_modules():
        if isinstance(module, cls):
            names = name.split('.')
            lora_module_names.add(names[-1])

    # Remove output layer
    if "lm_head" in lora_module_names:
        lora_module_names.remove("lm_head")

    return list(lora_module_names)

target_modules = find_all_linear_names(model)
```

### Rank Selection Strategy

```python
# Small models (<3B) or simple tasks
lora_config = LoraConfig(r=8, lora_alpha=16)

# Medium models (7-13B) general tasks
lora_config = LoraConfig(r=16, lora_alpha=32)

# Large models (30-70B) or complex tasks
lora_config = LoraConfig(r=64, lora_alpha=128)

# Quality vs efficiency tradeoff
ranks = [8, 16, 32, 64]
for r in ranks:
    print(f"Rank {r}:")
    print(f"  Trainable params: ~{r * 2 * 4096 * 32 / 1e6:.1f}M")
    print(f"  Storage: ~{r * 2 * 4096 * 32 * 2 / 1e6:.1f}MB")
```

### Saving and Loading LoRA Adapters

```python
from peft import PeftModel

# Save LoRA adapter only (~100MB for r=16)
model.save_pretrained("./lora-adapters")

# Load LoRA adapter
from transformers import AutoModelForCausalLM

base_model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-3-8b",
    device_map="auto"
)

model = PeftModel.from_pretrained(
    base_model,
    "./lora-adapters"
)

# Merge adapter into base model (for deployment)
merged_model = model.merge_and_unload()
merged_model.save_pretrained("./merged-model")

# Push to Hub (adapter only)
model.push_to_hub("username/lora-adapter")

# Push merged model
merged_model.push_to_hub("username/merged-model")
```

### Multi-Adapter Inference

```python
from peft import PeftModel

# Load base model once
base_model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-3-8b",
    device_map="auto"
)

# Load first adapter
model = PeftModel.from_pretrained(
    base_model,
    "adapters/task1",
    adapter_name="task1"
)

# Add second adapter
model.load_adapter("adapters/task2", adapter_name="task2")

# Add third adapter
model.load_adapter("adapters/task3", adapter_name="task3")

# Switch between adapters
model.set_adapter("task1")
output1 = model.generate(**inputs)

model.set_adapter("task2")
output2 = model.generate(**inputs)

# Disable all adapters (use base model)
model.disable_adapters()
output_base = model.generate(**inputs)
```

### Merging Multiple Adapters

```python
from peft import PeftModel

# Load base and first adapter
model = PeftModel.from_pretrained(
    base_model,
    "adapters/task1",
    adapter_name="task1"
)

# Load additional adapters
model.load_adapter("adapters/task2", adapter_name="task2")
model.load_adapter("adapters/task3", adapter_name="task3")

# Merge adapters with weights
model.add_weighted_adapter(
    adapters=["task1", "task2", "task3"],
    weights=[0.5, 0.3, 0.2],
    adapter_name="merged",
    combination_type="linear"  # or "cat" for concatenation
)

# Save merged adapter
model.save_pretrained("./merged-adapter")
```

### Training with PEFT

```python
from transformers import Trainer, TrainingArguments
from peft import get_peft_model, LoraConfig

# Configure LoRA
lora_config = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=["q_proj", "v_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM"
)

# Apply to model
model = get_peft_model(model, lora_config)

# Training arguments
training_args = TrainingArguments(
    output_dir="./lora-output",
    per_device_train_batch_size=4,
    gradient_accumulation_steps=4,
    learning_rate=2e-4,  # Higher LR for LoRA
    num_train_epochs=3,
    logging_steps=10,
    save_strategy="epoch",
    fp16=True,
)

# Train
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
)

trainer.train()

# Save LoRA adapter
model.save_pretrained("./lora-final")
```

### Modal.com Deployment

```python
import modal

app = modal.App("lora-finetune")

image = (
    modal.Image.debian_slim()
    .pip_install(
        "torch",
        "transformers",
        "peft",
        "bitsandbytes",
        "accelerate"
    )
)

@app.function(
    gpu="l40s",
    image=image,
    timeout=3600
)
def train_lora(base_model: str, dataset_path: str, output_path: str):
    from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer
    from peft import LoraConfig, get_peft_model
    from datasets import load_dataset
    import torch

    # Load model
    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        device_map="auto",
        torch_dtype=torch.bfloat16
    )

    tokenizer = AutoTokenizer.from_pretrained(base_model)

    # Configure LoRA
    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM"
    )

    model = get_peft_model(model, lora_config)

    # Load dataset
    dataset = load_dataset("json", data_files=dataset_path)

    # Train
    training_args = TrainingArguments(
        output_dir=output_path,
        per_device_train_batch_size=4,
        num_train_epochs=3,
        learning_rate=2e-4,
        logging_steps=10,
        save_strategy="epoch",
        bf16=True,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset["train"],
    )

    trainer.train()

    # Save adapter
    model.save_pretrained(output_path)
    tokenizer.save_pretrained(output_path)

    return {"status": "complete", "path": output_path}
```

---

## Quick Reference

### LoRA Rank Guidelines

```
Rank (r) | Trainable Params | Storage  | Use Case
---------|------------------|----------|---------------------------
4-8      | ~1-2M            | ~10MB    | Simple tasks, proof-of-concept
16       | ~4M              | ~50MB    | General fine-tuning
32       | ~8M              | ~100MB   | Complex tasks
64       | ~16M             | ~200MB   | Very complex, QLoRA compensation
128+     | ~32M+            | ~400MB+  | Experimental, diminishing returns
```

### Target Module Recommendations

```
Configuration           | Modules                          | Quality | Memory
------------------------|----------------------------------|---------|--------
Minimal                 | q_proj, v_proj                   | Good    | Low
Recommended             | q_proj, k_proj, v_proj, o_proj   | Better  | Medium
Full Attention + MLP    | All attention + gate/up/down     | Best    | High
```

### Alpha Selection

```python
# Common patterns
lora_alpha = r          # 1:1 ratio (standard)
lora_alpha = r * 2      # 2:1 ratio (stronger updates)
lora_alpha = 32         # Fixed at 32 (some practitioners prefer)

# Alpha / r ratio controls update magnitude
# Higher ratio = stronger LoRA influence
```

### PEFT Methods Comparison

```
Method      | Memory  | Quality | Speed | Use Case
------------|---------|---------|-------|----------------------------
LoRA        | Low     | High    | Fast  | General fine-tuning
QLoRA       | Very Low| High    | Fast  | Large models, limited VRAM
Prefix      | Low     | Medium  | Fast  | Prompt engineering
Adapter     | Medium  | High    | Medium| Task-specific modules
Full FT     | High    | Highest | Slow  | Maximum quality, unlimited compute
```

---

## Anti-Patterns

❌ **Rank too low**: Poor adaptation to task
✅ Start with r=16, increase if quality insufficient

❌ **Rank too high**: Overfitting, wasted compute
✅ Rarely need r>64 even for complex tasks

❌ **Wrong alpha/r ratio**: Unstable training
```python
# ❌ Bad: Alpha much larger than rank
lora_config = LoraConfig(r=8, lora_alpha=128)

# ✅ Good: Alpha = r or 2*r
lora_config = LoraConfig(r=16, lora_alpha=32)
```

❌ **Training all layers**: Negates memory benefits
✅ Target only attention or attention+MLP

❌ **Not using gradient checkpointing**: OOM on large models
```python
# ✅ Enable gradient checkpointing
model.gradient_checkpointing_enable()
```

❌ **Merging without testing adapters separately**: Can't debug
✅ Test individual adapters before merging

❌ **Using LoRA for small models with plenty VRAM**: Unnecessary
✅ Use full fine-tuning for models <3B if VRAM allows

❌ **Not saving adapter separately**: Lose flexibility
✅ Save adapter before merging for reusability

❌ **Ignoring base model precision**: Quality/memory mismatch
```python
# ❌ Bad: 4-bit model but fp32 LoRA
# ✅ Good: Match compute dtype
bnb_config = BitsAndBytesConfig(
    bnb_4bit_compute_dtype=torch.bfloat16
)
```

---

## Related Skills

- `unsloth-finetuning.md` - Fast LoRA training with Unsloth
- `modal-gpu-workloads.md` - GPU selection for PEFT training
- `llm-dataset-preparation.md` - Preparing data for fine-tuning
- `huggingface-autotrain.md` - Automated LoRA training
- `model-merging.md` - Advanced adapter merging techniques
- `quantization-techniques.md` - Model quantization deep dive

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
