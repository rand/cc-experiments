---
name: ml-huggingface-autotrain
description: Need quick fine-tuning without writing training code
---



# HuggingFace AutoTrain

**Scope**: No-code/low-code LLM fine-tuning with AutoTrain, CLI, web UI, deployment
**Lines**: ~330
**Last Updated**: 2025-10-25

## When to Use This Skill

Activate this skill when:
- Need quick fine-tuning without writing training code
- Working with non-technical team members
- Prototyping models rapidly before custom implementation
- Standardizing fine-tuning workflows across team
- Training multiple models with different hyperparameters
- Limited ML engineering resources available

## Core Concepts

### AutoTrain Overview

**What is AutoTrain**:
- Hugging Face's automated training platform
- Web UI and CLI for model fine-tuning
- Supports LLMs, vision, tabular, and more
- Automatic hyperparameter optimization
- Built-in experiment tracking

**Key Features**:
- Zero-code web interface option
- One-command CLI training
- Automatic data validation
- Multi-task support (text classification, NER, LLM, etc.)
- Direct Hub integration for models and datasets

**Supported Tasks**:
- LLM fine-tuning (instruction tuning, chat)
- Text classification (binary, multi-class, multi-label)
- Named Entity Recognition (NER)
- Question Answering
- Summarization
- Translation
- Image classification
- Tabular (classification, regression)

### Pricing and Compute

**Free Tier**:
- Community GPU access (limited availability)
- CPU training for small datasets
- Public model hosting on Hub

**Paid Spaces**:
- Dedicated GPU instances (A10G, A100)
- Priority queue access
- Private training runs
- ~$0.60-$4/hour depending on GPU

**Enterprise**:
- Custom compute configurations
- SSO and compliance features
- Volume discounts

### Workflow

**Standard Flow**:
1. Prepare dataset (CSV, JSON, or Hub dataset)
2. Upload to Hugging Face Hub or local file
3. Configure task and hyperparameters
4. Launch training (web UI or CLI)
5. Monitor progress and metrics
6. Download or deploy model

---

## Patterns

### CLI Installation

```bash
# Install AutoTrain
pip install autotrain-advanced

# Verify installation
autotrain --version

# Login to Hugging Face
huggingface-cli login
# Paste your token from https://huggingface.co/settings/tokens
```

### LLM Fine-Tuning (CLI)

```bash
# Basic LLM fine-tuning
autotrain llm \
  --train \
  --model meta-llama/Llama-3.2-3B \
  --data-path /path/to/dataset \
  --text-column text \
  --lr 2e-4 \
  --batch-size 2 \
  --epochs 3 \
  --trainer sft \
  --peft \
  --quantization int4 \
  --project-name llama-3-finetuned \
  --push-to-hub \
  --username your-username

# Advanced options
autotrain llm \
  --train \
  --model mistralai/Mistral-7B-v0.3 \
  --data-path dataset.csv \
  --text-column text \
  --lr 2e-4 \
  --batch-size 4 \
  --epochs 3 \
  --block-size 1024 \
  --warmup-ratio 0.1 \
  --lora-r 16 \
  --lora-alpha 32 \
  --lora-dropout 0.05 \
  --weight-decay 0.01 \
  --gradient-accumulation 4 \
  --mixed-precision fp16 \
  --project-name mistral-custom \
  --log wandb
```

### Dataset Formats

**Text/LLM Format** (CSV):
```csv
text
"Below is an instruction...\n\n### Instruction:\nWhat is Python?\n\n### Response:\nPython is a programming language."
"Below is an instruction...\n\n### Instruction:\nExplain AI\n\n### Response:\nAI stands for Artificial Intelligence."
```

**Text/LLM Format** (JSON):
```json
[
  {
    "text": "Below is an instruction...\n\n### Instruction:\nWhat is Python?\n\n### Response:\nPython is a programming language."
  },
  {
    "text": "Below is an instruction...\n\n### Instruction:\nExplain AI\n\n### Response:\nAI stands for Artificial Intelligence."
  }
]
```

**Chat Format** (JSON):
```json
[
  {
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "What is Python?"},
      {"role": "assistant", "content": "Python is a programming language."}
    ]
  },
  {
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "Explain AI"},
      {"role": "assistant", "content": "AI stands for Artificial Intelligence."}
    ]
  }
]
```

**Classification Format** (CSV):
```csv
text,label
"This product is amazing!",positive
"Terrible experience",negative
"It's okay",neutral
```

### Text Classification

```bash
autotrain text-classification \
  --train \
  --model distilbert-base-uncased \
  --data-path data.csv \
  --text-column text \
  --target-column label \
  --lr 2e-5 \
  --batch-size 16 \
  --epochs 5 \
  --project-name sentiment-classifier \
  --push-to-hub \
  --username your-username
```

### Using Hub Datasets

```bash
# Use dataset from Hugging Face Hub
autotrain llm \
  --train \
  --model meta-llama/Llama-3.2-3B \
  --data-path username/dataset-name \
  --text-column text \
  --lr 2e-4 \
  --batch-size 2 \
  --epochs 3 \
  --project-name llama-finetuned

# Specify dataset split
autotrain llm \
  --train \
  --model meta-llama/Llama-3.2-3B \
  --data-path username/dataset-name \
  --train-split train \
  --valid-split validation \
  --text-column text \
  --lr 2e-4 \
  --epochs 3
```

### Modal.com Deployment

```python
import modal

app = modal.App("autotrain-finetune")

image = (
    modal.Image.debian_slim()
    .pip_install("autotrain-advanced", "huggingface_hub")
)

volume = modal.Volume.from_name("autotrain-volume", create_if_missing=True)

@app.function(
    gpu="l40s",
    image=image,
    volumes={"/data": volume},
    secrets=[modal.Secret.from_name("huggingface-secret")],
    timeout=7200
)
def run_autotrain(
    model_name: str,
    dataset_path: str,
    project_name: str,
    push_to_hub: bool = True
):
    import subprocess
    import os

    # Build autotrain command
    cmd = [
        "autotrain", "llm",
        "--train",
        "--model", model_name,
        "--data-path", dataset_path,
        "--text-column", "text",
        "--lr", "2e-4",
        "--batch-size", "2",
        "--epochs", "3",
        "--trainer", "sft",
        "--peft",
        "--quantization", "int4",
        "--project-name", project_name,
        "--log", "tensorboard"
    ]

    if push_to_hub:
        cmd.extend([
            "--push-to-hub",
            "--username", os.environ["HF_USERNAME"]
        ])

    # Run training
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise Exception(f"Training failed: {result.stderr}")

    return {
        "status": "complete",
        "project": project_name,
        "output": result.stdout
    }

@app.local_entrypoint()
def main(model: str = "meta-llama/Llama-3.2-3B"):
    result = run_autotrain.remote(
        model_name=model,
        dataset_path="/data/training.jsonl",
        project_name="llama-finetuned"
    )
    print(result)
```

### Python API Usage

```python
from autotrain.trainers.clm.params import LLMTrainingParams
from autotrain.trainers.clm import train as llm_train

# Configure training parameters
params = LLMTrainingParams(
    model="meta-llama/Llama-3.2-3B",
    data_path="/path/to/data",
    text_column="text",
    lr=2e-4,
    batch_size=2,
    epochs=3,
    block_size=1024,
    warmup_ratio=0.1,
    lora_r=16,
    lora_alpha=32,
    lora_dropout=0.05,
    trainer="sft",
    use_peft=True,
    quantization="int4",
    project_name="llama-finetuned",
    log="tensorboard",
    push_to_hub=True,
    username="your-username",
)

# Run training
llm_train(params)
```

### Hyperparameter Tuning

```bash
# Try multiple learning rates
for lr in 1e-4 2e-4 5e-4; do
  autotrain llm \
    --train \
    --model meta-llama/Llama-3.2-3B \
    --data-path data.jsonl \
    --text-column text \
    --lr $lr \
    --batch-size 2 \
    --epochs 3 \
    --project-name "llama-lr-${lr}"
done

# Grid search with different LoRA ranks
for rank in 8 16 32; do
  autotrain llm \
    --train \
    --model mistralai/Mistral-7B-v0.3 \
    --data-path data.jsonl \
    --text-column text \
    --lr 2e-4 \
    --lora-r $rank \
    --lora-alpha $((rank * 2)) \
    --project-name "mistral-r${rank}"
done
```

### Monitoring and Logs

```bash
# View TensorBoard logs
tensorboard --logdir outputs/llama-finetuned

# Stream logs during training
tail -f outputs/llama-finetuned/training.log

# Check Weights & Biases (if enabled)
# Training metrics automatically logged to wandb.ai
```

---

## Quick Reference

### Common Commands

```bash
# List available tasks
autotrain --help

# LLM fine-tuning
autotrain llm --train --model MODEL --data-path DATA

# Text classification
autotrain text-classification --train --model MODEL --data-path DATA

# Token classification (NER)
autotrain token-classification --train --model MODEL --data-path DATA

# Check training status
ls -lah outputs/

# Test trained model
autotrain llm --infer --model outputs/llama-finetuned --text "Hello, how are you?"
```

### Key Parameters

```
Parameter              | Default    | Description
-----------------------|------------|----------------------------------
--model                | Required   | Base model from Hub
--data-path            | Required   | Path to dataset (local or Hub)
--text-column          | "text"     | Column name for text data
--lr                   | 5e-5       | Learning rate
--batch-size           | 8          | Training batch size per device
--epochs               | 3          | Number of training epochs
--block-size           | 1024       | Max sequence length
--warmup-ratio         | 0.1        | Warmup ratio of total steps
--lora-r               | 16         | LoRA rank
--lora-alpha           | 32         | LoRA alpha
--quantization         | None       | "int4", "int8", or None
--project-name         | Required   | Output directory name
--push-to-hub          | False      | Push to Hugging Face Hub
--log                  | None       | "tensorboard" or "wandb"
```

### Dataset Validation Checklist

```
✅ Dataset has required columns (text, label, etc.)
✅ No missing values in required columns
✅ Text is properly formatted (no binary data)
✅ Labels are valid (for classification)
✅ Dataset is not empty
✅ Train/validation split if provided
✅ File encoding is UTF-8
✅ JSON is valid (if using JSON format)
```

---

## Anti-Patterns

❌ **Not validating dataset format**: Training fails halfway through
✅ Validate dataset format before starting training:
```bash
# Check CSV
head data.csv
wc -l data.csv

# Validate JSON
python -m json.tool data.json > /dev/null && echo "Valid JSON"
```

❌ **Using web UI for production workflows**: Not reproducible
✅ Use CLI or Python API for production, version control configs

❌ **Ignoring validation metrics**: Overfitting not detected
✅ Always provide validation split:
```bash
autotrain llm \
  --train \
  --model MODEL \
  --data-path data \
  --train-split train \
  --valid-split validation  # Important!
```

❌ **Default hyperparameters for all tasks**: Suboptimal results
✅ Tune learning rate, batch size, and LoRA rank per task

❌ **Not monitoring training**: Miss errors or early stopping
✅ Enable logging and monitor:
```bash
autotrain llm --train --log tensorboard ...
# In another terminal:
tensorboard --logdir outputs/
```

❌ **Forgetting to save/push model**: Lose trained weights
✅ Always use `--push-to-hub` or save outputs/
```bash
autotrain llm --train --push-to-hub --username USER ...
```

❌ **Wrong quantization for GPU**: OOM or slow training
✅ Match quantization to GPU VRAM:
- 48GB+: No quantization or int8
- 24GB: int4 for 7B+ models
- <24GB: int4 required for 7B+ models

❌ **Single experiment without comparison**: Can't assess quality
✅ Run multiple experiments with different hyperparameters

---

## Related Skills

- `ml/unsloth-finetuning.md` - Faster alternative with custom code
- `ml/llm-dataset-preparation.md` - Preparing high-quality datasets
- `ml/lora-peft-techniques.md` - Understanding LoRA parameters
- `modal/modal-gpu-workloads.md` - GPU selection and deployment
- `ml/huggingface/huggingface-hub.md` - Managing models and datasets on Hub
- `ml/huggingface/huggingface-transformers.md` - Loading and using models
- `ml/huggingface/huggingface-datasets.md` - Working with datasets

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
