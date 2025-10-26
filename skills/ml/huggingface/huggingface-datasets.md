---
name: ml-huggingface-datasets
description: Loading, processing, and managing datasets with HuggingFace datasets library
---

# HuggingFace Datasets

**Scope**: Loading datasets, preprocessing, custom datasets, streaming, caching, data collators
**Lines**: ~325
**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Loading datasets from HuggingFace Hub
- Processing large datasets that don't fit in memory
- Creating custom datasets from CSV, JSON, or other formats
- Applying transformations to dataset columns
- Filtering and selecting dataset subsets
- Preparing data for model training
- Managing dataset caching and storage
- Using data collators for dynamic batching

## Core Concepts

### Dataset Structure

**DatasetDict**: Container for multiple splits
```python
from datasets import load_dataset

dataset = load_dataset("imdb")
# DatasetDict({
#     train: Dataset({features: ['text', 'label'], num_rows: 25000})
#     test: Dataset({features: ['text', 'label'], num_rows: 25000})
# })
```

**Dataset**: Single split with rows and columns
```python
train_dataset = dataset["train"]
# Dataset({
#     features: ['text', 'label'],
#     num_rows: 25000
# })
```

**Features**: Column types and metadata
- `Value`: Single value (int, float, string)
- `ClassLabel`: Categorical labels
- `Sequence`: List of values
- `Image`: Image data
- `Audio`: Audio data

### Loading Datasets

**From Hub**:
```python
from datasets import load_dataset

# Load entire dataset
dataset = load_dataset("squad")

# Load specific split
train_data = load_dataset("squad", split="train")

# Load specific configuration
dataset = load_dataset("glue", "mrpc")

# Streaming mode (for large datasets)
dataset = load_dataset("c4", "en", streaming=True)
```

**From Local Files**:
```python
# CSV
dataset = load_dataset("csv", data_files="data.csv")

# JSON
dataset = load_dataset("json", data_files="data.json")

# Multiple files
dataset = load_dataset("json", data_files={
    "train": "train.json",
    "test": "test.json"
})

# Parquet
dataset = load_dataset("parquet", data_files="data.parquet")
```

### Dataset Processing

**Map**: Apply function to each example
```python
def tokenize(example):
    return tokenizer(example["text"], truncation=True, padding="max_length")

dataset = dataset.map(tokenize, batched=True)
```

**Filter**: Keep examples matching condition
```python
# Filter by condition
dataset = dataset.filter(lambda x: len(x["text"]) > 100)

# Filter with index
dataset = dataset.filter(lambda x, i: i % 2 == 0, with_indices=True)
```

**Select**: Choose specific examples
```python
# Select by index
small_dataset = dataset.select(range(1000))

# Select random sample
sample = dataset.shuffle(seed=42).select(range(100))
```

---

## Patterns

### Loading Common Datasets

```python
from datasets import load_dataset

# Text classification
imdb = load_dataset("imdb")
sst2 = load_dataset("glue", "sst2")

# Question answering
squad = load_dataset("squad")
squad_v2 = load_dataset("squad_v2")

# Summarization
cnn_dailymail = load_dataset("cnn_dailymail", "3.0.0")

# Translation
wmt = load_dataset("wmt14", "de-en")

# Named Entity Recognition
conll = load_dataset("conll2003")

# Image classification
cifar10 = load_dataset("cifar10")
mnist = load_dataset("mnist")
```

### Processing with Map

```python
from datasets import load_dataset
from transformers import AutoTokenizer

dataset = load_dataset("imdb")
tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")

# Simple mapping
def tokenize_function(examples):
    return tokenizer(examples["text"], truncation=True, padding="max_length")

tokenized_dataset = dataset.map(tokenize_function, batched=True)

# Map with multiple columns
def preprocess(examples):
    # Tokenize text
    tokenized = tokenizer(examples["text"], truncation=True)
    # Add custom field
    tokenized["length"] = [len(text.split()) for text in examples["text"]]
    return tokenized

processed = dataset.map(preprocess, batched=True)

# Remove original columns
processed = dataset.map(
    tokenize_function,
    batched=True,
    remove_columns=dataset["train"].column_names
)

# Parallel processing
processed = dataset.map(
    tokenize_function,
    batched=True,
    num_proc=4  # Use 4 processes
)
```

### Filtering and Selecting

```python
from datasets import load_dataset

dataset = load_dataset("imdb", split="train")

# Filter by length
long_reviews = dataset.filter(lambda x: len(x["text"]) > 500)

# Filter by label
positive_only = dataset.filter(lambda x: x["label"] == 1)

# Complex filtering
def is_quality_review(example):
    return len(example["text"]) > 100 and example["text"].count(".") > 3

quality_reviews = dataset.filter(is_quality_review)

# Select first 1000 examples
subset = dataset.select(range(1000))

# Select random sample
sample = dataset.shuffle(seed=42).select(range(100))

# Train/test split
split_dataset = dataset.train_test_split(test_size=0.2, seed=42)
train_data = split_dataset["train"]
test_data = split_dataset["test"]
```

### Creating Custom Datasets

```python
from datasets import Dataset, DatasetDict

# From dictionary
data = {
    "text": ["Example 1", "Example 2", "Example 3"],
    "label": [0, 1, 0]
}
dataset = Dataset.from_dict(data)

# From pandas DataFrame
import pandas as pd

df = pd.DataFrame({
    "text": ["Example 1", "Example 2"],
    "label": [0, 1]
})
dataset = Dataset.from_pandas(df)

# From generator (for large data)
def data_generator():
    for i in range(1000):
        yield {"text": f"Example {i}", "label": i % 2}

dataset = Dataset.from_generator(data_generator)

# Create DatasetDict with multiple splits
dataset_dict = DatasetDict({
    "train": Dataset.from_dict(train_data),
    "test": Dataset.from_dict(test_data)
})

# From CSV
dataset = Dataset.from_csv("data.csv")

# From JSON lines
dataset = Dataset.from_json("data.jsonl")
```

### Streaming Large Datasets

```python
from datasets import load_dataset

# Load in streaming mode
dataset = load_dataset("c4", "en", streaming=True)

# Iterate through examples
for example in dataset["train"]:
    print(example["text"])
    break  # Process first example

# Take first N examples
from itertools import islice

first_1000 = list(islice(dataset["train"], 1000))

# Filter streaming dataset
filtered = dataset["train"].filter(lambda x: len(x["text"]) > 100)

# Map streaming dataset
tokenized = dataset["train"].map(lambda x: tokenizer(x["text"]))

# Shuffle streaming dataset
shuffled = dataset["train"].shuffle(seed=42, buffer_size=10000)
```

### Dataset Features and Schema

```python
from datasets import Dataset, Features, Value, ClassLabel, Sequence

# Define custom features
features = Features({
    "text": Value("string"),
    "label": ClassLabel(names=["negative", "positive"]),
    "tokens": Sequence(Value("string")),
    "score": Value("float32")
})

# Create dataset with features
data = {
    "text": ["Good movie", "Bad movie"],
    "label": [1, 0],
    "tokens": [["good", "movie"], ["bad", "movie"]],
    "score": [0.9, 0.1]
}
dataset = Dataset.from_dict(data, features=features)

# Access features
print(dataset.features)
# {'text': Value(dtype='string'),
#  'label': ClassLabel(names=['negative', 'positive']),
#  'tokens': Sequence(Value(dtype='string')),
#  'score': Value(dtype='float32')}

# Convert labels to integers
label_int = dataset["label"][0]  # 1

# Convert integers to label names
label_name = dataset.features["label"].int2str(1)  # "positive"
```

### Caching and Storage

```python
from datasets import load_dataset, disable_caching, enable_caching

# Default: caching enabled (~/.cache/huggingface/datasets/)

# Disable caching
disable_caching()
dataset = load_dataset("imdb")

# Re-enable caching
enable_caching()

# Custom cache directory
dataset = load_dataset("imdb", cache_dir="/custom/cache/path")

# Save dataset to disk
dataset.save_to_disk("./my_dataset")

# Load from disk
from datasets import load_from_disk
dataset = load_from_disk("./my_dataset")

# Clear cache for specific dataset
dataset.cleanup_cache_files()
```

### Data Collators

```python
from transformers import DataCollatorWithPadding, DataCollatorForLanguageModeling
from datasets import load_dataset
from transformers import AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
dataset = load_dataset("imdb", split="train[:1000]")

# Tokenize dataset
def tokenize(examples):
    return tokenizer(examples["text"], truncation=True)

tokenized = dataset.map(tokenize, batched=True, remove_columns=dataset.column_names)

# Dynamic padding collator
data_collator = DataCollatorWithPadding(tokenizer=tokenizer)

# Use with DataLoader
from torch.utils.data import DataLoader

dataloader = DataLoader(
    tokenized,
    batch_size=8,
    collate_fn=data_collator
)

# Masked language modeling collator
mlm_collator = DataCollatorForLanguageModeling(
    tokenizer=tokenizer,
    mlm=True,
    mlm_probability=0.15
)
```

### Combining and Interleaving Datasets

```python
from datasets import load_dataset, concatenate_datasets, interleave_datasets

# Load multiple datasets
dataset1 = load_dataset("imdb", split="train")
dataset2 = load_dataset("yelp_polarity", split="train")

# Concatenate (stack vertically)
combined = concatenate_datasets([dataset1, dataset2])

# Interleave (alternate examples)
interleaved = interleave_datasets([dataset1, dataset2])

# Interleave with custom probabilities
interleaved = interleave_datasets(
    [dataset1, dataset2],
    probabilities=[0.7, 0.3],  # 70% from dataset1, 30% from dataset2
    seed=42
)

# Interleave with stopping strategy
interleaved = interleave_datasets(
    [dataset1, dataset2],
    stopping_strategy="all_exhausted"  # or "first_exhausted"
)
```

---

## Quick Reference

### Loading Methods

```
Method                  | Source                    | Example
------------------------|---------------------------|----------------------------------
load_dataset(name)      | HuggingFace Hub           | load_dataset("imdb")
load_dataset(csv)       | CSV file                  | load_dataset("csv", data_files="data.csv")
load_dataset(json)      | JSON/JSONL file           | load_dataset("json", data_files="data.jsonl")
Dataset.from_dict()     | Python dictionary         | Dataset.from_dict({"text": [...], "label": [...]})
Dataset.from_pandas()   | Pandas DataFrame          | Dataset.from_pandas(df)
Dataset.from_generator()| Python generator          | Dataset.from_generator(gen_fn)
load_from_disk()        | Saved dataset on disk     | load_from_disk("./dataset")
```

### Processing Methods

```
Method                  | Purpose                   | Example
------------------------|---------------------------|----------------------------------
map()                   | Apply function to all     | dataset.map(tokenize, batched=True)
filter()                | Keep matching examples    | dataset.filter(lambda x: x["label"] == 1)
select()                | Choose by index           | dataset.select(range(100))
shuffle()               | Randomize order           | dataset.shuffle(seed=42)
train_test_split()      | Split into train/test     | dataset.train_test_split(test_size=0.2)
rename_column()         | Rename column             | dataset.rename_column("text", "sentence")
remove_columns()        | Drop columns              | dataset.remove_columns(["col1", "col2"])
flatten()               | Unnest nested columns     | dataset.flatten()
```

### Key Parameters

```
Parameter       | Default    | Description
----------------|------------|----------------------------------------
batched         | False      | Process examples in batches (faster)
num_proc        | None       | Number of parallel processes
remove_columns  | None       | Columns to remove after mapping
batch_size      | 1000       | Batch size for batched=True
cache_file_name | None       | Custom cache file path
load_from_cache | True       | Use cached results if available
```

### Key Guidelines

```
✅ DO: Use batched=True for faster processing
✅ DO: Stream large datasets that don't fit in memory
✅ DO: Remove unnecessary columns to save memory
✅ DO: Use num_proc for CPU-intensive preprocessing
✅ DO: Define features for custom datasets
✅ DO: Use data collators for dynamic padding

❌ DON'T: Load entire dataset if you only need a subset
❌ DON'T: Forget to set seed for reproducible shuffling
❌ DON'T: Keep original columns if not needed
❌ DON'T: Process without batching (much slower)
```

---

## Anti-Patterns

### Critical Violations

```python
# ❌ NEVER: Process without batching for large datasets
dataset = dataset.map(tokenize)  # Processes one example at a time

# ✅ CORRECT: Use batched processing
dataset = dataset.map(tokenize, batched=True)  # 10-100x faster
```

❌ **No batching**: Extremely slow for large datasets
✅ **Correct approach**: Always use `batched=True` for transformations

### Common Mistakes

```python
# ❌ Don't: Keep unnecessary columns
tokenized = dataset.map(tokenize, batched=True)
# Still has original "text" column, wastes memory

# ✅ Correct: Remove columns not needed for training
tokenized = dataset.map(
    tokenize,
    batched=True,
    remove_columns=dataset.column_names
)
```

❌ **Keeping unused columns**: Wastes memory
✅ **Better**: Remove columns after processing

```python
# ❌ Don't: Load entire dataset when you need subset
dataset = load_dataset("c4", "en")  # Hundreds of GB!
small_dataset = dataset["train"].select(range(1000))

# ✅ Correct: Use streaming or split parameter
dataset = load_dataset("c4", "en", split="train[:1000]", streaming=True)
```

❌ **Loading full dataset unnecessarily**: Memory waste
✅ **Better**: Use `split` parameter or streaming

```python
# ❌ Don't: Forget to set seed for shuffling
shuffled = dataset.shuffle()
# Different order each run, not reproducible

# ✅ Correct: Set seed
shuffled = dataset.shuffle(seed=42)
```

❌ **No shuffle seed**: Results not reproducible
✅ **Better**: Always set seed for reproducibility

```python
# ❌ Don't: Process serially when you can parallelize
processed = dataset.map(expensive_function, batched=True)
# Uses single process

# ✅ Correct: Use multiple processes
processed = dataset.map(
    expensive_function,
    batched=True,
    num_proc=4  # 4x faster on 4 cores
)
```

❌ **No parallelization**: Slow preprocessing
✅ **Better**: Use `num_proc` for CPU-heavy tasks

```python
# ❌ Don't: Create dataset without features for custom data
dataset = Dataset.from_dict({
    "text": ["Example"],
    "label": ["positive"]  # Should be integer/ClassLabel
})

# ✅ Correct: Define features
features = Features({
    "text": Value("string"),
    "label": ClassLabel(names=["negative", "positive"])
})
dataset = Dataset.from_dict(
    {"text": ["Example"], "label": [1]},
    features=features
)
```

❌ **Missing features**: Type inconsistencies
✅ **Better**: Define features explicitly for custom datasets

---

## Related Skills

- `ml/huggingface/huggingface-hub.md` - Uploading datasets to Hub
- `ml/huggingface/huggingface-transformers.md` - Using datasets with models
- `ml/huggingface/huggingface-autotrain.md` - Training with datasets
- `ml/llm-dataset-preparation.md` - Preparing high-quality training data
- `database/postgres-optimization.md` - Storing processed datasets
- `data/etl-patterns.md` - ETL workflows for datasets

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
