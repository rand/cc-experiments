---
name: ml-huggingface-transformers
description: Loading models, pipelines, inference, and tokenization with transformers library
---

# HuggingFace Transformers

**Scope**: Loading models, pipelines, inference, tokenizers, quantization, custom configurations
**Lines**: ~365
**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Loading pre-trained models for inference or fine-tuning
- Using high-level pipelines for common NLP tasks
- Implementing custom inference logic with models
- Working with tokenizers for text preprocessing
- Quantizing models for reduced memory usage
- Configuring model architectures and parameters
- Batching predictions for efficiency
- Accelerating inference with GPU

## Core Concepts

### Auto Classes

**Purpose**: Automatically detect and load correct model/tokenizer classes

**Main Classes**:
- `AutoModel`: Base model without task-specific head
- `AutoModelForSequenceClassification`: Text classification
- `AutoModelForCausalLM`: Text generation (GPT-style)
- `AutoModelForSeq2SeqLM`: Sequence-to-sequence (T5, BART)
- `AutoTokenizer`: Tokenizer for any model

```python
from transformers import AutoModel, AutoTokenizer

# Automatically loads correct classes
model = AutoModel.from_pretrained("bert-base-uncased")
tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
```

### Pipelines

**High-Level API**: One-line inference for common tasks

**Available Tasks**:
- `text-generation`: Generate text continuations
- `text-classification`: Classify text sentiment/topics
- `question-answering`: Answer questions from context
- `fill-mask`: Fill in masked tokens
- `summarization`: Summarize long text
- `translation`: Translate between languages
- `zero-shot-classification`: Classify without training
- `feature-extraction`: Get embeddings

```python
from transformers import pipeline

# Create pipeline
classifier = pipeline("text-classification", model="distilbert-base-uncased-finetuned-sst-2-english")

# Single prediction
result = classifier("I love this product!")
# [{'label': 'POSITIVE', 'score': 0.9998}]

# Batch predictions
results = classifier(["Great!", "Terrible!", "It's okay"])
```

### Tokenization

**Process**: Convert text to model inputs

**Key Operations**:
- Encoding: Text → token IDs
- Decoding: Token IDs → text
- Special tokens: [CLS], [SEP], [PAD], [MASK]
- Padding and truncation: Handle variable lengths

```python
from transformers import AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")

# Encode text
inputs = tokenizer("Hello, world!", return_tensors="pt")
# {'input_ids': tensor([[101, 7592, 1010, 2088, 999, 102]]),
#  'attention_mask': tensor([[1, 1, 1, 1, 1, 1]])}

# Decode back to text
text = tokenizer.decode(inputs["input_ids"][0])
# "[CLS] hello, world! [SEP]"
```

### Model Inference

**Forward Pass**: Get model predictions

```python
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

model = AutoModelForSequenceClassification.from_pretrained("distilbert-base-uncased-finetuned-sst-2-english")
tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased-finetuned-sst-2-english")

# Tokenize input
inputs = tokenizer("I love this!", return_tensors="pt")

# Get predictions
with torch.no_grad():
    outputs = model(**inputs)

# Extract logits and probabilities
logits = outputs.logits
probs = torch.softmax(logits, dim=-1)
predicted_class = torch.argmax(probs, dim=-1).item()
```

---

## Patterns

### Basic Model Loading

```python
from transformers import AutoModel, AutoTokenizer

# Load model and tokenizer
model_name = "bert-base-uncased"
model = AutoModel.from_pretrained(model_name)
tokenizer = AutoTokenizer.from_pretrained(model_name)

# Load to GPU
model = model.to("cuda")

# Load with specific dtype
model = AutoModel.from_pretrained(model_name, torch_dtype=torch.float16)

# Load from local path
model = AutoModel.from_pretrained("/path/to/local/model")
```

### Using Pipelines

```python
from transformers import pipeline

# Text generation
generator = pipeline("text-generation", model="gpt2")
output = generator("Once upon a time", max_length=50, num_return_sequences=2)

# Question answering
qa = pipeline("question-answering", model="distilbert-base-cased-distilled-squad")
result = qa(
    question="What is Python?",
    context="Python is a high-level programming language known for its simplicity."
)
# {'answer': 'a high-level programming language', 'score': 0.98, 'start': 10, 'end': 43}

# Summarization
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
summary = summarizer(
    "Long article text here...",
    max_length=130,
    min_length=30,
    do_sample=False
)

# Zero-shot classification
classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
result = classifier(
    "This is a story about sports",
    candidate_labels=["sports", "politics", "technology"]
)
```

### Custom Inference

```python
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

# Load model and tokenizer
model = AutoModelForCausalLM.from_pretrained("gpt2")
tokenizer = AutoTokenizer.from_pretrained("gpt2")

# Prepare input
prompt = "The future of AI is"
inputs = tokenizer(prompt, return_tensors="pt")

# Generate text
with torch.no_grad():
    outputs = model.generate(
        inputs["input_ids"],
        max_length=50,
        num_beams=5,
        temperature=0.7,
        top_k=50,
        top_p=0.95,
        do_sample=True,
        pad_token_id=tokenizer.eos_token_id
    )

# Decode output
generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
print(generated_text)
```

### Batch Processing

```python
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import torch

model = AutoModelForSequenceClassification.from_pretrained("distilbert-base-uncased-finetuned-sst-2-english")
tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased-finetuned-sst-2-english")

# Batch of texts
texts = [
    "I love this product!",
    "This is terrible.",
    "It's okay, I guess."
]

# Tokenize with padding
inputs = tokenizer(texts, padding=True, truncation=True, return_tensors="pt")

# Batch inference
with torch.no_grad():
    outputs = model(**inputs)
    probs = torch.softmax(outputs.logits, dim=-1)

# Process results
for i, text in enumerate(texts):
    positive_prob = probs[i][1].item()
    print(f"{text}: {positive_prob:.2%} positive")
```

### Model Quantization

```python
from transformers import AutoModelForCausalLM, BitsAndBytesConfig

# 4-bit quantization config
quantization_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4"
)

# Load quantized model
model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-2-7b-hf",
    quantization_config=quantization_config,
    device_map="auto"
)

# 8-bit quantization (simpler)
model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-2-7b-hf",
    load_in_8bit=True,
    device_map="auto"
)
```

### Working with Tokenizers

```python
from transformers import AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")

# Basic encoding
tokens = tokenizer.encode("Hello, world!")
# [101, 7592, 1010, 2088, 999, 102]

# Encoding with special tokens control
tokens = tokenizer.encode("Hello, world!", add_special_tokens=False)
# [7592, 1010, 2088, 999]

# Batch encoding with padding
texts = ["Short text", "This is a longer text example"]
encoded = tokenizer(
    texts,
    padding=True,
    truncation=True,
    max_length=512,
    return_tensors="pt"
)

# Get attention mask
attention_mask = encoded["attention_mask"]

# Decode with special tokens
text = tokenizer.decode(tokens, skip_special_tokens=False)
# "[CLS] hello, world! [SEP]"

# Decode without special tokens
text = tokenizer.decode(tokens, skip_special_tokens=True)
# "hello, world!"

# Token to string mapping
token_str = tokenizer.convert_ids_to_tokens([7592, 1010, 2088])
# ['hello', ',', 'world']
```

### GPU Acceleration

```python
import torch
from transformers import AutoModel, AutoTokenizer

# Check GPU availability
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Load model to GPU
model = AutoModel.from_pretrained("bert-base-uncased").to(device)
tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")

# Process on GPU
text = "Example text"
inputs = tokenizer(text, return_tensors="pt").to(device)

with torch.no_grad():
    outputs = model(**inputs)

# Move outputs back to CPU if needed
embeddings = outputs.last_hidden_state.cpu()

# Multi-GPU with device_map
from transformers import AutoModelForCausalLM

model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-2-7b-hf",
    device_map="auto",  # Automatically distribute across GPUs
    torch_dtype=torch.float16
)
```

### Custom Model Configuration

```python
from transformers import AutoConfig, AutoModel

# Load default config
config = AutoConfig.from_pretrained("bert-base-uncased")

# Modify config
config.num_hidden_layers = 6  # Reduce layers
config.hidden_size = 512      # Reduce hidden size
config.num_attention_heads = 8

# Create model from custom config
model = AutoModel.from_config(config)

# Or modify during loading
model = AutoModel.from_pretrained(
    "bert-base-uncased",
    num_hidden_layers=6,
    hidden_size=512
)

# Save custom config
config.save_pretrained("./my-custom-bert")
```

### Streaming Generation

```python
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer
from threading import Thread

model = AutoModelForCausalLM.from_pretrained("gpt2")
tokenizer = AutoTokenizer.from_pretrained("gpt2")

prompt = "The future of AI"
inputs = tokenizer(prompt, return_tensors="pt")

# Create streamer
streamer = TextIteratorStreamer(tokenizer, skip_special_tokens=True)

# Generate in background thread
generation_kwargs = dict(
    inputs["input_ids"],
    streamer=streamer,
    max_length=100
)
thread = Thread(target=model.generate, kwargs=generation_kwargs)
thread.start()

# Stream output
print(prompt, end="")
for new_text in streamer:
    print(new_text, end="", flush=True)
thread.join()
```

---

## Quick Reference

### Common Model Classes

```
Class                               | Task
------------------------------------|----------------------------------
AutoModel                           | Base model (embeddings)
AutoModelForSequenceClassification  | Text classification
AutoModelForCausalLM                | Text generation (GPT)
AutoModelForMaskedLM                | Masked language modeling (BERT)
AutoModelForSeq2SeqLM               | Sequence-to-sequence (T5, BART)
AutoModelForQuestionAnswering       | Question answering
AutoModelForTokenClassification     | Named entity recognition
```

### Pipeline Tasks

```
Pipeline                  | Example Model              | Use Case
--------------------------|----------------------------|---------------------------
text-generation           | gpt2, llama                | Generate text
text-classification       | distilbert-sst2            | Sentiment, topics
question-answering        | distilbert-squad           | Answer questions
fill-mask                 | bert-base-uncased          | Fill [MASK] tokens
summarization             | facebook/bart-large-cnn    | Summarize text
translation               | Helsinki-NLP/opus-mt       | Translate languages
zero-shot-classification  | facebook/bart-large-mnli   | Classify without training
feature-extraction        | sentence-transformers      | Get embeddings
```

### Key Parameters

```
Parameter           | Default | Description
--------------------|---------|----------------------------------------
max_length          | varies  | Maximum sequence length
num_beams           | 1       | Beam search width (1 = greedy)
temperature         | 1.0     | Sampling temperature (lower = focused)
top_k               | 50      | Top-k sampling
top_p               | 1.0     | Nucleus sampling threshold
do_sample           | False   | Use sampling vs greedy decoding
pad_token_id        | None    | Token ID for padding
eos_token_id        | None    | Token ID for end-of-sequence
```

### Key Guidelines

```
✅ DO: Use pipelines for simple tasks
✅ DO: Batch inputs for efficiency
✅ DO: Move models to GPU when available
✅ DO: Use torch.no_grad() during inference
✅ DO: Quantize large models to save memory
✅ DO: Handle padding and truncation properly

❌ DON'T: Load models in loops (cache outside)
❌ DON'T: Forget to set pad_token_id for generation
❌ DON'T: Process one item at a time (use batches)
❌ DON'T: Keep models in float32 unnecessarily
```

---

## Anti-Patterns

### Critical Violations

```python
# ❌ NEVER: Load model in loop
for text in texts:
    model = AutoModel.from_pretrained("bert-base-uncased")  # Extremely slow!
    result = model(text)

# ✅ CORRECT: Load once, reuse
model = AutoModel.from_pretrained("bert-base-uncased")
for text in texts:
    result = model(text)
```

❌ **Loading models repeatedly**: Wastes time and memory
✅ **Correct approach**: Load once, reuse for all predictions

### Common Mistakes

```python
# ❌ Don't: Ignore device placement
model = AutoModel.from_pretrained("bert-base-uncased")
inputs = tokenizer(text, return_tensors="pt").to("cuda")
outputs = model(**inputs)  # Error: model on CPU, inputs on GPU

# ✅ Correct: Match devices
model = AutoModel.from_pretrained("bert-base-uncased").to("cuda")
inputs = tokenizer(text, return_tensors="pt").to("cuda")
outputs = model(**inputs)
```

❌ **Device mismatch**: Runtime errors
✅ **Better**: Ensure model and inputs on same device

```python
# ❌ Don't: Forget no_grad during inference
outputs = model(**inputs)  # Builds computation graph unnecessarily

# ✅ Correct: Use no_grad
with torch.no_grad():
    outputs = model(**inputs)
```

❌ **Missing no_grad**: Wastes memory tracking gradients
✅ **Better**: Always use `torch.no_grad()` for inference

```python
# ❌ Don't: Process items one by one
results = []
for text in texts:
    inputs = tokenizer(text, return_tensors="pt")
    output = model(**inputs)
    results.append(output)

# ✅ Correct: Batch processing
inputs = tokenizer(texts, padding=True, truncation=True, return_tensors="pt")
outputs = model(**inputs)
```

❌ **No batching**: Slow inference, underutilized GPU
✅ **Better**: Batch inputs for 10-100x speedup

```python
# ❌ Don't: Forget pad_token_id for generation
outputs = model.generate(inputs)
# Warning: Setting `pad_token_id` to `eos_token_id`

# ✅ Correct: Set explicitly
outputs = model.generate(
    inputs,
    pad_token_id=tokenizer.eos_token_id
)
```

❌ **Missing pad_token_id**: Warnings and potential issues
✅ **Better**: Always set for generation tasks

---

## Related Skills

- `ml/huggingface/huggingface-hub.md` - Downloading models from Hub
- `ml/huggingface/huggingface-datasets.md` - Loading datasets for training
- `ml/huggingface/huggingface-autotrain.md` - Fine-tuning models
- `ml/unsloth-finetuning.md` - Fast fine-tuning with Unsloth
- `ml/lora-peft-techniques.md` - Parameter-efficient fine-tuning
- `modal/modal-gpu-workloads.md` - GPU deployment for inference

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
