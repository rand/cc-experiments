---
name: modal-gpu-workloads
description: Running ML/AI inference on Modal
---



# Modal GPU Workloads

**Use this skill when:**
- Running ML/AI inference on Modal
- Training models on GPU
- Selecting appropriate GPU types
- Optimizing GPU utilization and costs
- Working with PyTorch, TensorFlow, or JAX

## GPU Selection

### Available GPU Types

Choose GPU based on workload:

```python
import modal

app = modal.App("gpu-app")

# T4 - Budget-friendly, good for inference
@app.function(gpu="t4")
def t4_inference(text: str):
    # 16GB VRAM, ~$0.50/hour
    return run_small_model(text)

# L4 - Good balance for most workloads
@app.function(gpu="l4")
def l4_inference(text: str):
    # 24GB VRAM, ~$1.00/hour
    return run_medium_model(text)

# L40S - RECOMMENDED for most ML workloads
# Best cost/performance ratio
@app.function(gpu="l40s")
def l40s_inference(text: str):
    # 48GB VRAM, great price/performance
    return run_large_model(text)

# A100 - High-end for large models/training
@app.function(gpu="a100")
def a100_training():
    # 40GB or 80GB VRAM, ~$4-8/hour
    return train_large_model()

# H100 - Cutting edge for very large workloads
@app.function(gpu="h100")
def h100_training():
    # 80GB VRAM, ~$8-12/hour
    return train_huge_model()

# Multiple GPUs
@app.function(gpu="a100:4")  # 4x A100
def multi_gpu_training():
    return distributed_training()
```

### GPU Recommendations

**For inference:**
- Small models (<7B params): T4 or L4
- Medium models (7-13B params): L40S
- Large models (13-70B params): L40S or A100
- Very large models (>70B params): A100 or H100

**For training:**
- Fine-tuning small models: L4 or L40S
- Fine-tuning medium models: L40S or A100
- Training from scratch: A100 or H100
- Distributed training: Multiple A100 or H100

## PyTorch on GPU

### Basic Inference

Set up PyTorch with GPU:

```python
image = (
    modal.Image.debian_slim()
    .uv_pip_install(
        "torch==2.1.0",
        "transformers==4.35.0"
    )
)

@app.cls(gpu="l40s", image=image)
class TextGenerator:
    @modal.enter()
    def load_model(self):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        model_name = "meta-llama/Llama-2-7b-hf"

        print(f"Loading model {model_name}...")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16,
            device_map="auto"
        )
        print("Model loaded")

    @modal.method()
    def generate(self, prompt: str, max_length: int = 100) -> str:
        import torch

        inputs = self.tokenizer(prompt, return_tensors="pt").to("cuda")

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_length=max_length,
                temperature=0.7,
                do_sample=True
            )

        return self.tokenizer.decode(outputs[0], skip_special_tokens=True)

@app.local_entrypoint()
def main():
    generator = TextGenerator()
    result = generator.generate.remote("Once upon a time")
    print(result)
```

### Batch Inference

Process multiple inputs efficiently:

```python
@app.cls(gpu="l40s", image=image)
class BatchInference:
    @modal.enter()
    def load_model(self):
        import torch
        from transformers import pipeline

        self.classifier = pipeline(
            "sentiment-analysis",
            model="distilbert-base-uncased-finetuned-sst-2-english",
            device=0  # GPU 0
        )

    @modal.method()
    def predict_batch(self, texts: list[str]) -> list[dict]:
        # Process in batches for efficiency
        batch_size = 32
        results = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_results = self.classifier(batch)
            results.extend(batch_results)

        return results

@app.local_entrypoint()
def main():
    texts = ["I love this!" for _ in range(1000)]

    classifier = BatchInference()
    results = classifier.predict_batch.remote(texts)
    print(f"Processed {len(results)} texts")
```

## Model Optimization

### Quantization

Reduce memory usage with quantization:

```python
image = (
    modal.Image.debian_slim()
    .uv_pip_install(
        "torch==2.1.0",
        "transformers==4.35.0",
        "bitsandbytes==0.41.0",
        "accelerate==0.24.0"
    )
)

@app.cls(gpu="l40s", image=image)
class QuantizedModel:
    @modal.enter()
    def load_model(self):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

        # 4-bit quantization config
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4"
        )

        self.tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-2-7b-hf")
        self.model = AutoModelForCausalLM.from_pretrained(
            "meta-llama/Llama-2-7b-hf",
            quantization_config=quantization_config,
            device_map="auto"
        )

    @modal.method()
    def generate(self, prompt: str) -> str:
        inputs = self.tokenizer(prompt, return_tensors="pt").to("cuda")
        outputs = self.model.generate(**inputs, max_length=100)
        return self.tokenizer.decode(outputs[0])
```

### Flash Attention

Use Flash Attention for faster inference:

```python
image = (
    modal.Image.debian_slim()
    .uv_pip_install(
        "torch==2.1.0",
        "transformers==4.35.0",
        "flash-attn==2.3.3"
    )
)

@app.cls(gpu="l40s", image=image)
class FastModel:
    @modal.enter()
    def load_model(self):
        import torch
        from transformers import AutoModelForCausalLM

        self.model = AutoModelForCausalLM.from_pretrained(
            "meta-llama/Llama-2-7b-hf",
            torch_dtype=torch.float16,
            device_map="auto",
            attn_implementation="flash_attention_2"
        )
```

## Training on GPU

### Fine-Tuning

Fine-tune models on GPU:

```python
image = (
    modal.Image.debian_slim()
    .uv_pip_install(
        "torch==2.1.0",
        "transformers==4.35.0",
        "datasets==2.14.0",
        "accelerate==0.24.0"
    )
)

@app.function(
    gpu="a100",
    timeout=3600,  # 1 hour
    image=image
)
def fine_tune_model(dataset_name: str, output_path: str):
    import torch
    from transformers import (
        AutoModelForSequenceClassification,
        AutoTokenizer,
        Trainer,
        TrainingArguments
    )
    from datasets import load_dataset

    # Load model and tokenizer
    model = AutoModelForSequenceClassification.from_pretrained(
        "distilbert-base-uncased",
        num_labels=2
    ).to("cuda")

    tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased")

    # Load and prepare dataset
    dataset = load_dataset(dataset_name)

    def tokenize(examples):
        return tokenizer(
            examples["text"],
            padding="max_length",
            truncation=True
        )

    tokenized_dataset = dataset.map(tokenize, batched=True)

    # Training configuration
    training_args = TrainingArguments(
        output_dir=output_path,
        num_train_epochs=3,
        per_device_train_batch_size=16,
        per_device_eval_batch_size=16,
        warmup_steps=500,
        weight_decay=0.01,
        logging_dir="./logs",
        fp16=True,  # Mixed precision training
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset["train"],
        eval_dataset=tokenized_dataset["test"]
    )

    # Train
    trainer.train()

    # Save model
    trainer.save_model(output_path)

    return {"status": "complete", "output": output_path}
```

### Distributed Training

Train across multiple GPUs:

```python
@app.function(
    gpu="a100:4",  # 4 GPUs
    timeout=7200,
    image=image
)
def distributed_training():
    import torch
    import torch.distributed as dist
    from transformers import Trainer, TrainingArguments

    # Training args for distributed training
    training_args = TrainingArguments(
        output_dir="./output",
        num_train_epochs=3,
        per_device_train_batch_size=8,
        gradient_accumulation_steps=4,
        fp16=True,
        deepspeed="ds_config.json",  # DeepSpeed config
        local_rank=-1  # Auto-set by launcher
    )

    # Trainer handles distribution automatically
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset
    )

    trainer.train()
```

## GPU Memory Management

### Monitoring Memory

Track GPU memory usage:

```python
@app.function(gpu="l40s")
def monitor_memory():
    import torch

    print(f"Allocated: {torch.cuda.memory_allocated() / 1e9:.2f} GB")
    print(f"Reserved: {torch.cuda.memory_reserved() / 1e9:.2f} GB")
    print(f"Max allocated: {torch.cuda.max_memory_allocated() / 1e9:.2f} GB")

    # Clear cache
    torch.cuda.empty_cache()

    return "Memory checked"
```

### Gradient Checkpointing

Reduce memory for training:

```python
@app.function(gpu="l40s", image=image)
def train_with_checkpointing():
    from transformers import AutoModelForCausalLM

    model = AutoModelForCausalLM.from_pretrained("gpt2")

    # Enable gradient checkpointing
    model.gradient_checkpointing_enable()

    # Train with reduced memory
    # (slower but fits larger models)
```

## Cost Optimization

### Auto-Shutdown

Set timeouts to avoid unnecessary costs:

```python
# Timeout after 5 minutes of inactivity
@app.function(gpu="l40s", timeout=300)
def inference_with_timeout(text: str):
    return generate(text)

# Container idle timeout
@app.function(
    gpu="l40s",
    container_idle_timeout=60  # Shutdown after 60s idle
)
def auto_shutdown_inference(text: str):
    return generate(text)
```

### Warm Pool

Keep containers warm for low latency:

```python
# Keep 1 container warm for instant response
@app.function(
    gpu="l40s",
    keep_warm=1
)
def low_latency_inference(text: str):
    return generate(text)
```

## Testing GPU Code Locally

### CPU Fallback for Development

Test without GPU:

```python
@app.function(gpu="l40s" if modal.is_remote() else None)
def flexible_inference(text: str):
    import torch

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")

    model = load_model().to(device)
    return model(text)
```

## Anti-Patterns to Avoid

**DON'T load models on every invocation:**
```python
# ❌ BAD - Loads model each time (very slow)
@app.function(gpu="l40s")
def bad_inference(text: str):
    model = load_model()  # Slow!
    return model(text)

# ✅ GOOD - Load once per container
@app.cls(gpu="l40s")
class GoodInference:
    @modal.enter()
    def load_model(self):
        self.model = load_model()

    @modal.method()
    def predict(self, text: str):
        return self.model(text)
```

**DON'T use expensive GPUs for simple tasks:**
```python
# ❌ BAD - H100 for tiny model
@app.function(gpu="h100")
def overkill(text: str):
    return simple_model(text)  # Wastes $10/hour

# ✅ GOOD - Match GPU to workload
@app.function(gpu="t4")
def appropriate(text: str):
    return simple_model(text)  # Costs $0.50/hour
```

**DON'T forget to set timeouts:**
```python
# ❌ BAD - Could run forever
@app.function(gpu="a100")
def no_timeout():
    while True:
        process()

# ✅ GOOD - Bounded execution
@app.function(gpu="a100", timeout=3600)
def with_timeout():
    process_for_limited_time()
```

## Related Skills

- **modal-functions-basics.md** - Basic Modal function patterns
- **modal-image-building.md** - Installing ML dependencies
- **modal-volumes-secrets.md** - Storing models and data
- **modal-web-endpoints.md** - Serving models via HTTP
