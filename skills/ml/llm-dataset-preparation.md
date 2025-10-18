---
name: ml-llm-dataset-preparation
description: Preparing training data for LLM fine-tuning
---



# LLM Dataset Preparation

**Scope**: Dataset formatting, quality control, instruction tuning, chat templates, validation
**Lines**: ~360
**Last Updated**: 2025-10-18

## When to Use This Skill

Activate this skill when:
- Preparing training data for LLM fine-tuning
- Converting datasets to instruction or chat format
- Ensuring dataset quality before training
- Creating custom training datasets from raw data
- Debugging training issues related to data format
- Splitting datasets for training and validation

## Core Concepts

### Dataset Quality Principles

**Quality over Quantity**:
- 100 high-quality examples > 10,000 low-quality examples
- Clean, well-formatted data prevents training issues
- Diverse examples improve generalization
- Representative samples prevent bias

**Key Quality Metrics**:
- Correctness: Outputs are factually accurate
- Consistency: Similar inputs have similar outputs
- Completeness: Outputs fully address inputs
- Diversity: Wide range of topics and styles
- Length: Appropriate response length for task

### Common Dataset Formats

**Instruction Format** (Alpaca):
- Structured instruction-response pairs
- Optional context/input field
- Best for task-oriented fine-tuning

**Chat Format** (ShareGPT/ChatML):
- Multi-turn conversations
- System, user, assistant roles
- Best for conversational models

**Completion Format**:
- Simple text completion
- Single text field
- Best for domain adaptation

### Train/Validation Splits

**Standard Splits**:
- 80/20 train/validation (small datasets <1k)
- 90/10 train/validation (medium datasets 1k-10k)
- 95/5 train/validation (large datasets >10k)

**Stratified Splitting**:
- Maintain label distribution
- Balance topic diversity
- Ensure edge cases in validation

---

## Patterns

### Alpaca Instruction Format

```python
# Single example structure
alpaca_example = {
    "instruction": "What is the capital of France?",
    "input": "",  # Optional context
    "output": "The capital of France is Paris."
}

# With context/input
alpaca_with_context = {
    "instruction": "Summarize the following text.",
    "input": "Paris is the capital and most populous city of France...",
    "output": "Paris is France's capital and largest city."
}

# Format as training text
alpaca_prompt = """Below is an instruction that describes a task. Write a response that appropriately completes the request.

### Instruction:
{instruction}

### Response:
{output}"""

# With input field
alpaca_prompt_with_input = """Below is an instruction that describes a task, paired with an input that provides further context. Write a response that appropriately completes the request.

### Instruction:
{instruction}

### Input:
{input}

### Response:
{output}"""

def format_alpaca(example):
    """Convert Alpaca dict to training text."""
    if example.get("input", "").strip():
        return alpaca_prompt_with_input.format(**example)
    else:
        return alpaca_prompt.format(**example)

# Usage
training_text = format_alpaca(alpaca_example)
```

### ShareGPT Chat Format

```python
# Multi-turn conversation structure
sharegpt_example = {
    "conversations": [
        {"from": "system", "value": "You are a helpful assistant."},
        {"from": "human", "value": "What is Python?"},
        {"from": "gpt", "value": "Python is a high-level programming language known for its simplicity and versatility."},
        {"from": "human", "value": "What are its main uses?"},
        {"from": "gpt", "value": "Python is commonly used for web development, data science, machine learning, automation, and scientific computing."}
    ]
}

# Convert to training format
def format_sharegpt(example, tokenizer):
    """Convert ShareGPT to training text with proper formatting."""
    conversation = example["conversations"]

    # Build conversation string
    text = ""
    for turn in conversation:
        role = turn["from"]
        content = turn["value"]

        if role == "system":
            text += f"<|im_start|>system\n{content}<|im_end|>\n"
        elif role == "human":
            text += f"<|im_start|>user\n{content}<|im_end|>\n"
        elif role == "gpt":
            text += f"<|im_start|>assistant\n{content}<|im_end|>\n"

    text += tokenizer.eos_token
    return text
```

### ChatML Format (OpenAI-style)

```python
# Modern chat format
chatml_example = {
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the capital of France?"},
        {"role": "assistant", "content": "The capital of France is Paris."}
    ]
}

# Format for training
def format_chatml(messages, tokenizer):
    """Convert ChatML messages to training text."""
    formatted = ""

    for message in messages:
        role = message["role"]
        content = message["content"]
        formatted += f"<|im_start|>{role}\n{content}<|im_end|>\n"

    formatted += tokenizer.eos_token
    return formatted

# Validate message structure
def validate_chatml(example):
    """Ensure ChatML format is valid."""
    messages = example.get("messages", [])

    if not messages:
        return False

    # Check required fields
    for msg in messages:
        if "role" not in msg or "content" not in msg:
            return False
        if msg["role"] not in ["system", "user", "assistant"]:
            return False

    return True
```

### Dataset Creation from Scratch

```python
from datasets import Dataset
import json

# Create dataset from list of examples
examples = [
    {
        "instruction": "Explain what machine learning is.",
        "output": "Machine learning is a subset of AI that enables systems to learn from data."
    },
    {
        "instruction": "What is Python used for?",
        "output": "Python is used for web development, data science, automation, and more."
    },
    # ... more examples
]

# Convert to Hugging Face Dataset
dataset = Dataset.from_dict({
    "instruction": [ex["instruction"] for ex in examples],
    "output": [ex["output"] for ex in examples]
})

# Save to disk
dataset.save_to_disk("./my_dataset")

# Save as JSON
with open("dataset.json", "w") as f:
    json.dump(examples, f, indent=2)

# Save as JSONL (one example per line)
with open("dataset.jsonl", "w") as f:
    for ex in examples:
        f.write(json.dumps(ex) + "\n")
```

### Data Cleaning Pipeline

```python
from datasets import load_dataset
import re

def clean_text(text):
    """Clean and normalize text."""
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)

    # Remove special characters (keep basic punctuation)
    text = re.sub(r'[^\w\s.,!?-]', '', text)

    # Trim whitespace
    text = text.strip()

    return text

def filter_quality(example, min_length=10, max_length=2048):
    """Filter out low-quality examples."""
    instruction = example.get("instruction", "")
    output = example.get("output", "")

    # Check minimum length
    if len(output) < min_length:
        return False

    # Check maximum length (prevent truncation)
    if len(output) > max_length:
        return False

    # Check for empty or placeholder text
    if not instruction.strip() or not output.strip():
        return False

    # Check for common placeholder patterns
    placeholders = ["lorem ipsum", "placeholder", "TODO", "xxx"]
    if any(p in output.lower() for p in placeholders):
        return False

    return True

# Apply cleaning pipeline
dataset = load_dataset("json", data_files="raw_data.json")
dataset = dataset.map(lambda x: {
    "instruction": clean_text(x["instruction"]),
    "output": clean_text(x["output"])
})
dataset = dataset.filter(filter_quality)

print(f"Cleaned dataset: {len(dataset)} examples")
```

### Train/Validation Split

```python
from datasets import load_dataset, DatasetDict

# Load dataset
dataset = load_dataset("json", data_files="data.jsonl", split="train")

# Simple split
dataset_dict = dataset.train_test_split(test_size=0.1, seed=42)

# Create DatasetDict with named splits
final_dataset = DatasetDict({
    "train": dataset_dict["train"],
    "validation": dataset_dict["test"]
})

# Save splits
final_dataset.save_to_disk("./dataset_with_splits")

# Or save to Hub
final_dataset.push_to_hub("username/dataset-name")

# Stratified split (for classification)
from sklearn.model_selection import train_test_split

# Get labels
labels = [ex["label"] for ex in dataset]

# Stratified split maintains label distribution
train_idx, val_idx = train_test_split(
    range(len(dataset)),
    test_size=0.1,
    stratify=labels,
    random_state=42
)

train_dataset = dataset.select(train_idx)
val_dataset = dataset.select(val_idx)
```

### Dataset Deduplication

```python
from datasets import load_dataset

def deduplicate_dataset(dataset, key="text"):
    """Remove duplicate examples."""
    seen = set()
    unique_indices = []

    for i, example in enumerate(dataset):
        text = example[key]

        # Use hash for memory efficiency
        text_hash = hash(text)

        if text_hash not in seen:
            seen.add(text_hash)
            unique_indices.append(i)

    print(f"Removed {len(dataset) - len(unique_indices)} duplicates")
    return dataset.select(unique_indices)

# Usage
dataset = load_dataset("json", data_files="data.json")
dataset = deduplicate_dataset(dataset["train"], key="output")
```

### Converting Web Data to Training Format

```python
import requests
from bs4 import BeautifulSoup

def scrape_to_qa(url):
    """Convert FAQ page to Q&A dataset."""
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    qa_pairs = []

    # Example: Find question-answer pairs
    for qa in soup.find_all('div', class_='faq-item'):
        question = qa.find('h3', class_='question').get_text().strip()
        answer = qa.find('p', class_='answer').get_text().strip()

        qa_pairs.append({
            "instruction": question,
            "output": answer
        })

    return qa_pairs

# Convert to Alpaca format
faqs = scrape_to_qa("https://example.com/faq")
dataset = Dataset.from_dict({
    "instruction": [qa["instruction"] for qa in faqs],
    "output": [qa["output"] for qa in faqs]
})
```

### Data Augmentation

```python
import random

def augment_instruction(instruction):
    """Create variations of instructions."""
    templates = [
        "{}",
        "Can you {}?",
        "Please {}",
        "I need help with: {}",
        "Explain: {}"
    ]

    # Lowercase first word for some templates
    inst_lower = instruction[0].lower() + instruction[1:]

    return random.choice(templates).format(inst_lower)

def augment_dataset(dataset, augmentation_factor=2):
    """Augment dataset by creating variations."""
    augmented = []

    for example in dataset:
        # Keep original
        augmented.append(example)

        # Create variations
        for _ in range(augmentation_factor - 1):
            augmented.append({
                "instruction": augment_instruction(example["instruction"]),
                "output": example["output"]
            })

    return Dataset.from_dict({
        "instruction": [ex["instruction"] for ex in augmented],
        "output": [ex["output"] for ex in augmented]
    })
```

### Validation and Quality Checks

```python
def validate_dataset(dataset):
    """Comprehensive dataset validation."""
    issues = []

    for i, example in enumerate(dataset):
        # Check required fields
        if "text" not in example and "instruction" not in example:
            issues.append(f"Example {i}: Missing text field")

        # Check for empty content
        text = example.get("text") or example.get("instruction", "")
        if not text.strip():
            issues.append(f"Example {i}: Empty text")

        # Check length
        if len(text) < 10:
            issues.append(f"Example {i}: Text too short ({len(text)} chars)")

        # Check encoding
        try:
            text.encode('utf-8')
        except UnicodeEncodeError:
            issues.append(f"Example {i}: Invalid encoding")

    if issues:
        print(f"Found {len(issues)} issues:")
        for issue in issues[:10]:  # Show first 10
            print(f"  - {issue}")
    else:
        print("Dataset validation passed!")

    return len(issues) == 0

# Usage
is_valid = validate_dataset(dataset)
```

---

## Quick Reference

### Dataset Format Summary

```
Format        | Use Case              | Structure
--------------|-----------------------|----------------------------
Alpaca        | Instruction tuning    | instruction, input, output
ShareGPT      | Multi-turn chat       | conversations (from, value)
ChatML        | OpenAI-style chat     | messages (role, content)
Completion    | Domain adaptation     | text
Classification| Text classification   | text, label
```

### Minimum Dataset Sizes

```
Task                    | Minimum Examples | Recommended
------------------------|------------------|-------------
Simple classification   | 100              | 1,000+
Instruction tuning      | 500              | 5,000+
Chat fine-tuning        | 1,000            | 10,000+
Domain adaptation       | 10,000           | 100,000+
```

### Quality Checklist

```
✅ No duplicate examples
✅ No empty or null values
✅ Consistent formatting across examples
✅ Appropriate length (not too short or long)
✅ Valid UTF-8 encoding
✅ Train/validation split created
✅ No placeholder or dummy text
✅ Factually accurate outputs
✅ Diverse topics and styles
✅ Representative of target use case
```

### Common Cleaning Steps

```python
# 1. Remove duplicates
dataset = deduplicate_dataset(dataset)

# 2. Filter by length
dataset = dataset.filter(lambda x: 10 < len(x["text"]) < 2048)

# 3. Clean text
dataset = dataset.map(lambda x: {"text": clean_text(x["text"])})

# 4. Remove placeholders
dataset = dataset.filter(lambda x: "TODO" not in x["text"])

# 5. Split train/val
dataset = dataset.train_test_split(test_size=0.1)
```

---

## Anti-Patterns

❌ **No validation split**: Can't detect overfitting
✅ Always create validation split:
```python
dataset = dataset.train_test_split(test_size=0.1)
```

❌ **Inconsistent formatting**: Training fails or poor results
✅ Validate format consistency before training:
```python
validate_dataset(dataset)
```

❌ **Including duplicates**: Model memorizes instead of learning
✅ Deduplicate before training

❌ **Wrong prompt format for model**: Model doesn't follow instructions
✅ Use model's native format (check model card):
```python
# Check model card for correct format!
# Llama 3: <|begin_of_text|>...<|end_of_text|>
# ChatML: <|im_start|>...<|im_end|>
```

❌ **Too much data cleaning**: Lose important patterns
✅ Clean only obvious errors, preserve natural language variation

❌ **Ignoring dataset statistics**: Miss data issues
✅ Analyze before training:
```python
print(f"Examples: {len(dataset)}")
print(f"Avg length: {sum(len(x['text']) for x in dataset) / len(dataset)}")
print(f"Max length: {max(len(x['text']) for x in dataset)}")
```

❌ **No quality control**: GIGO (garbage in, garbage out)
✅ Manually review random samples before training

❌ **Using raw web scraping without cleaning**: Noise and errors
✅ Always clean and validate scraped data

---

## Related Skills

- `unsloth-finetuning.md` - Fast fine-tuning with prepared datasets
- `huggingface-autotrain.md` - Automated training with datasets
- `lora-peft-techniques.md` - Efficient fine-tuning methods
- `data-validation.md` - Advanced validation techniques
- `text-preprocessing.md` - Text cleaning and normalization
- `huggingface-hub.md` - Uploading and managing datasets

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
