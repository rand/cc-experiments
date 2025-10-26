---
name: ml-huggingface-hub
description: Managing models, datasets, and Spaces on HuggingFace Hub
---

# HuggingFace Hub

**Scope**: Model repositories, dataset management, Hub API, Spaces hosting, authentication
**Lines**: ~310
**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Uploading or downloading models from HuggingFace Hub
- Managing dataset repositories and metadata
- Searching for pre-trained models or datasets
- Creating and hosting demo applications on Spaces
- Configuring authentication and access tokens
- Writing model cards and documentation
- Sharing work with the ML community
- Versioning models and tracking experiments

## Core Concepts

### Hub Architecture

**Repository Types**:
- **Model repositories**: Store model weights, configs, tokenizers
- **Dataset repositories**: Host datasets with metadata and README
- **Space repositories**: Deploy Gradio/Streamlit apps

**Repository Structure**:
```
username/repo-name
├── README.md              # Model card or dataset description
├── config.json            # Model configuration
├── pytorch_model.bin      # Model weights
├── tokenizer.json         # Tokenizer files
├── .gitattributes         # Git LFS configuration
└── model_card.md          # Optional detailed documentation
```

**Git LFS Integration**:
- Large files (>10MB) automatically tracked with Git LFS
- Efficient storage and bandwidth usage
- Version control for binary files

### Authentication

**Access Tokens**:
- Read tokens: Download private repos, access gated models
- Write tokens: Upload models, create repos, push changes
- Token scopes: read, write, manage repos

**Token Management**:
```python
from huggingface_hub import login, logout

# Login with token (prompts for input)
login()

# Login programmatically
login(token="hf_...")

# Logout
logout()
```

**Environment Variables**:
```bash
export HF_TOKEN="hf_..."
export HUGGINGFACE_TOKEN="hf_..."  # Alternative
```

### Model Cards

**Purpose**:
- Document model capabilities and limitations
- Specify intended use cases
- Describe training data and methodology
- Address ethical considerations
- Provide usage examples

**Key Sections**:
- Model description
- Intended uses and limitations
- Training data and procedure
- Evaluation results
- Bias and ethical considerations
- How to use (code examples)
- Citation information

---

## Patterns

### Installation and Setup

```bash
# Install hub library
pip install huggingface_hub

# Login from CLI
huggingface-cli login
# Paste token from https://huggingface.co/settings/tokens

# Verify login
huggingface-cli whoami
```

### Uploading Models

```python
from huggingface_hub import HfApi, create_repo
from transformers import AutoModel, AutoTokenizer

# Initialize API
api = HfApi()

# Create repository
repo_id = "username/model-name"
create_repo(repo_id, repo_type="model", exist_ok=True)

# Upload model and tokenizer
model = AutoModel.from_pretrained("bert-base-uncased")
tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")

model.push_to_hub(repo_id)
tokenizer.push_to_hub(repo_id)

# Alternative: upload specific files
api.upload_file(
    path_or_fileobj="model.safetensors",
    path_in_repo="model.safetensors",
    repo_id=repo_id,
    repo_type="model",
)
```

### Downloading Models

```python
from huggingface_hub import hf_hub_download, snapshot_download

# Download single file
model_path = hf_hub_download(
    repo_id="bert-base-uncased",
    filename="pytorch_model.bin",
    cache_dir="./cache"
)

# Download entire repository
repo_path = snapshot_download(
    repo_id="bert-base-uncased",
    cache_dir="./cache"
)

# Download specific revision (branch/tag/commit)
snapshot_download(
    repo_id="bert-base-uncased",
    revision="main",
    cache_dir="./cache"
)
```

### Searching Models and Datasets

```python
from huggingface_hub import HfApi

api = HfApi()

# Search models
models = api.list_models(
    filter="text-classification",
    sort="downloads",
    direction=-1,
    limit=10
)

for model in models:
    print(f"{model.modelId}: {model.downloads} downloads")

# Search by task
models = api.list_models(task="text-generation", limit=5)

# Search by author
models = api.list_models(author="meta-llama")

# Search datasets
datasets = api.list_datasets(
    filter="translation",
    sort="downloads",
    limit=10
)

for dataset in datasets:
    print(f"{dataset.id}: {dataset.downloads} downloads")
```

### Creating and Managing Datasets

```python
from huggingface_hub import HfApi, create_repo
from datasets import Dataset

# Create dataset repository
repo_id = "username/dataset-name"
create_repo(repo_id, repo_type="dataset", exist_ok=True)

# Create dataset
data = {
    "text": ["Example 1", "Example 2", "Example 3"],
    "label": [0, 1, 0]
}
dataset = Dataset.from_dict(data)

# Push to Hub
dataset.push_to_hub(repo_id)

# Upload additional files (README, etc.)
api = HfApi()
api.upload_file(
    path_or_fileobj="README.md",
    path_in_repo="README.md",
    repo_id=repo_id,
    repo_type="dataset"
)
```

### Working with Spaces

```python
from huggingface_hub import create_repo, upload_file

# Create Space repository
space_id = "username/space-name"
create_repo(
    space_id,
    repo_type="space",
    space_sdk="gradio",  # or "streamlit"
    exist_ok=True
)

# Upload app file
upload_file(
    path_or_fileobj="app.py",
    path_in_repo="app.py",
    repo_id=space_id,
    repo_type="space"
)

# Upload requirements
upload_file(
    path_or_fileobj="requirements.txt",
    path_in_repo="requirements.txt",
    repo_id=space_id,
    repo_type="space"
)
```

### Model Versioning

```python
from huggingface_hub import HfApi

api = HfApi()

# Create a new branch
api.create_branch(
    repo_id="username/model-name",
    branch="experiment-1",
    repo_type="model"
)

# Upload to specific branch
api.upload_file(
    path_or_fileobj="model.safetensors",
    path_in_repo="model.safetensors",
    repo_id="username/model-name",
    revision="experiment-1",
    repo_type="model"
)

# Create tag
api.create_tag(
    repo_id="username/model-name",
    tag="v1.0",
    repo_type="model"
)
```

### Writing Model Cards

```markdown
---
language: en
license: mit
tags:
- text-classification
- sentiment-analysis
datasets:
- imdb
metrics:
- accuracy
- f1
model-index:
- name: sentiment-classifier
  results:
  - task:
      type: text-classification
    dataset:
      name: IMDB
      type: imdb
    metrics:
    - type: accuracy
      value: 0.92
---

# Model Card for Sentiment Classifier

## Model Description

This model is a fine-tuned BERT model for sentiment analysis on movie reviews.

## Intended Uses

- Classify movie reviews as positive or negative
- Sentiment analysis on English text
- Educational purposes and research

## Limitations

- Trained only on movie reviews, may not generalize to other domains
- English language only
- May struggle with sarcasm or nuanced sentiment

## Training Data

Trained on IMDB dataset containing 50,000 movie reviews.

## Training Procedure

- Base model: bert-base-uncased
- Fine-tuning: 3 epochs with learning rate 2e-5
- Batch size: 16
- Optimizer: AdamW

## Evaluation Results

- Accuracy: 92%
- F1 Score: 0.91

## How to Use

```python
from transformers import pipeline

classifier = pipeline("sentiment-analysis", model="username/sentiment-classifier")
result = classifier("This movie was amazing!")
print(result)
```

## Ethical Considerations

This model may reflect biases present in movie review data.

## Citation

If you use this model, please cite:
```
@misc{sentiment-classifier,
  author = {Your Name},
  title = {Sentiment Classifier},
  year = {2025},
  publisher = {HuggingFace},
  url = {https://huggingface.co/username/sentiment-classifier}
}
```
```

---

## Quick Reference

### Common Commands

```bash
# Login
huggingface-cli login

# Check login status
huggingface-cli whoami

# Upload model
huggingface-cli upload username/model-name ./model_dir

# Download model
huggingface-cli download username/model-name

# Create repo
huggingface-cli repo create username/repo-name --type model

# Delete repo
huggingface-cli delete-cache
```

### Hub API Methods

```
Method                  | Use Case                    | Example
------------------------|-----------------------------|---------
create_repo()           | Create new repository       | create_repo("user/repo")
upload_file()           | Upload single file          | upload_file("model.bin", repo_id="user/repo")
snapshot_download()     | Download entire repo        | snapshot_download("user/repo")
hf_hub_download()       | Download single file        | hf_hub_download("user/repo", "config.json")
list_models()           | Search models               | list_models(filter="text-gen")
list_datasets()         | Search datasets             | list_datasets(author="user")
create_branch()         | Version model               | create_branch("user/repo", "v2")
create_tag()            | Tag release                 | create_tag("user/repo", "v1.0")
```

### Key Guidelines

```
✅ DO: Write comprehensive model cards with limitations
✅ DO: Use semantic versioning for model releases
✅ DO: Test model uploads with small files first
✅ DO: Use private repos for sensitive or in-progress work
✅ DO: Include usage examples in model cards
✅ DO: Document training data and methodology

❌ DON'T: Upload models without documentation
❌ DON'T: Share write tokens publicly
❌ DON'T: Upload sensitive data to public repos
❌ DON'T: Skip ethical considerations in model cards
```

---

## Anti-Patterns

### Critical Violations

```python
# ❌ NEVER: Hardcode tokens in code
model.push_to_hub("user/repo", token="hf_xxxx")

# ✅ CORRECT: Use environment variables or login
login()
model.push_to_hub("user/repo")
```

❌ **Hardcoded tokens**: Security risk, tokens can be leaked
✅ **Correct approach**: Use `huggingface-cli login` or environment variables

### Common Mistakes

```python
# ❌ Don't: Upload without model card
create_repo("user/model")
model.push_to_hub("user/model")  # No documentation

# ✅ Correct: Create model card first
create_repo("user/model")
with open("README.md", "w") as f:
    f.write("# Model Card\n\n...")
api.upload_file("README.md", repo_id="user/model")
model.push_to_hub("user/model")
```

❌ **Missing model cards**: Users can't understand model purpose or limitations
✅ **Better**: Always include comprehensive documentation

```python
# ❌ Don't: Ignore versioning
model.push_to_hub("user/model")  # Overwrites previous version

# ✅ Correct: Use branches or tags
api.create_branch("user/model", branch="v1.1")
model.push_to_hub("user/model", revision="v1.1")
```

❌ **No versioning**: Can't track model changes or roll back
✅ **Better**: Use branches for experiments, tags for releases

```python
# ❌ Don't: Upload entire directories without .gitignore
api.upload_folder("./checkpoints", repo_id="user/model")
# Uploads unnecessary files, cache, etc.

# ✅ Correct: Use .gitignore or upload selectively
api.upload_file("model.safetensors", repo_id="user/model")
api.upload_file("config.json", repo_id="user/model")
```

❌ **Uploading unnecessary files**: Wastes storage and bandwidth
✅ **Better**: Upload only required model files

---

## Related Skills

- `ml/huggingface/huggingface-transformers.md` - Loading and using models from Hub
- `ml/huggingface/huggingface-datasets.md` - Working with Hub datasets
- `ml/huggingface/huggingface-spaces.md` - Deploying apps on Spaces
- `ml/huggingface/huggingface-autotrain.md` - Training models to upload to Hub
- `ml/unsloth-finetuning.md` - Fine-tuning models for Hub upload
- `ml/llm-dataset-preparation.md` - Preparing datasets for Hub

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
