---
name: ml-huggingface-spaces
description: Deploying Gradio and Streamlit apps on HuggingFace Spaces
---

# HuggingFace Spaces

**Scope**: Gradio apps, Streamlit apps, Space configuration, hardware selection, secrets management
**Lines**: ~285
**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Deploying interactive ML demos and applications
- Sharing models with non-technical users
- Creating public or private app interfaces
- Hosting Gradio or Streamlit applications
- Configuring GPU-accelerated inference
- Managing API keys and secrets securely
- Embedding apps in websites or documentation
- Setting up custom domains for apps

## Core Concepts

### Space Types

**Gradio Spaces**: Python library for ML interfaces
- Quick setup with minimal code
- Pre-built components (sliders, text boxes, images)
- Automatic input/output handling
- Built-in examples and flagging
- Real-time inference

**Streamlit Spaces**: Python framework for data apps
- More flexible layouts
- Custom widgets and components
- Session state management
- Data visualization support
- Multi-page apps

**Static Spaces**: HTML/CSS/JS only
- No server-side computation
- Client-side inference with ONNX.js or TensorFlow.js
- Fast loading, no compute costs

### Space Configuration

**README.md Metadata**: Configure Space settings
```yaml
---
title: My Demo App
emoji: 🚀
colorFrom: blue
colorTo: purple
sdk: gradio  # or streamlit, static
sdk_version: 4.0.0
app_file: app.py
pinned: false
license: mit
---
```

**Hardware Options**:
- CPU Basic (free): 2 vCPU, 16GB RAM
- CPU Upgrade ($0.03/hr): 8 vCPU, 32GB RAM
- T4 GPU ($0.60/hr): 16GB VRAM
- A10G GPU ($3.15/hr): 24GB VRAM
- A100 GPU ($4.13/hr): 40GB VRAM

### Secrets Management

**Environment Variables**: Store API keys securely
- Accessible in app code via `os.environ`
- Not visible in public repos
- Configure in Space settings UI
- Support for HuggingFace tokens, OpenAI keys, etc.

---

## Patterns

### Basic Gradio App

```python
import gradio as gr
from transformers import pipeline

# Load model
classifier = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")

# Define function
def classify_text(text):
    result = classifier(text)[0]
    return f"{result['label']}: {result['score']:.2%}"

# Create interface
demo = gr.Interface(
    fn=classify_text,
    inputs=gr.Textbox(lines=2, placeholder="Enter text here..."),
    outputs=gr.Textbox(label="Sentiment"),
    title="Sentiment Analysis",
    description="Analyze sentiment of text using DistilBERT",
    examples=[
        ["I love this product!"],
        ["This is terrible."],
        ["It's okay, I guess."]
    ]
)

# Launch app
if __name__ == "__main__":
    demo.launch()
```

### Advanced Gradio with Multiple Inputs

```python
import gradio as gr
from transformers import pipeline

generator = pipeline("text-generation", model="gpt2")

def generate_text(prompt, max_length, temperature, top_p):
    result = generator(
        prompt,
        max_length=max_length,
        temperature=temperature,
        top_p=top_p,
        num_return_sequences=1
    )
    return result[0]["generated_text"]

demo = gr.Interface(
    fn=generate_text,
    inputs=[
        gr.Textbox(lines=3, label="Prompt"),
        gr.Slider(10, 200, value=50, step=10, label="Max Length"),
        gr.Slider(0.1, 2.0, value=0.7, step=0.1, label="Temperature"),
        gr.Slider(0.1, 1.0, value=0.95, step=0.05, label="Top P")
    ],
    outputs=gr.Textbox(lines=5, label="Generated Text"),
    title="GPT-2 Text Generator",
    examples=[
        ["Once upon a time", 100, 0.8, 0.95],
        ["The future of AI", 150, 0.7, 0.9]
    ]
)

demo.launch()
```

### Gradio with Image Input/Output

```python
import gradio as gr
from PIL import Image
from transformers import pipeline

# Image classification
classifier = pipeline("image-classification", model="google/vit-base-patch16-224")

def classify_image(image):
    results = classifier(image)
    # Format results as dictionary for label component
    return {result["label"]: result["score"] for result in results[:5]}

demo = gr.Interface(
    fn=classify_image,
    inputs=gr.Image(type="pil", label="Upload Image"),
    outputs=gr.Label(num_top_classes=5, label="Predictions"),
    title="Image Classification",
    description="Classify images using Vision Transformer",
    examples=["cat.jpg", "dog.jpg"]
)

demo.launch()
```

### Basic Streamlit App

```python
import streamlit as st
from transformers import pipeline

st.title("Sentiment Analysis App")
st.write("Analyze the sentiment of your text")

# Load model (cached)
@st.cache_resource
def load_model():
    return pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")

classifier = load_model()

# Input
text = st.text_area("Enter text:", height=100)

# Predict button
if st.button("Analyze"):
    if text:
        with st.spinner("Analyzing..."):
            result = classifier(text)[0]

            # Display result
            st.success("Analysis Complete!")
            col1, col2 = st.columns(2)
            col1.metric("Label", result["label"])
            col2.metric("Confidence", f"{result['score']:.2%}")
    else:
        st.warning("Please enter some text")

# Examples
st.subheader("Examples")
if st.button("Try Example: Positive"):
    st.write("I love this product!")
if st.button("Try Example: Negative"):
    st.write("This is terrible.")
```

### Streamlit with Session State

```python
import streamlit as st
from transformers import pipeline

st.title("Chat with GPT-2")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Load model
@st.cache_resource
def load_model():
    return pipeline("text-generation", model="gpt2")

generator = load_model()

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Chat input
if prompt := st.chat_input("Your message"):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.write(prompt)

    # Generate response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = generator(prompt, max_length=100, num_return_sequences=1)[0]["generated_text"]
            st.write(response)

    # Add assistant message
    st.session_state.messages.append({"role": "assistant", "content": response})
```

### Space Configuration with README

```markdown
---
title: Sentiment Analysis Demo
emoji: 😊
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: 4.0.0
app_file: app.py
pinned: false
license: mit
tags:
- sentiment-analysis
- nlp
- transformers
models:
- distilbert-base-uncased-finetuned-sst-2-english
---

# Sentiment Analysis Demo

This Space demonstrates sentiment analysis using DistilBERT.

## Features
- Real-time sentiment classification
- Confidence scores
- Example inputs

## Usage
Enter any text and click "Submit" to analyze sentiment.

## Model
Uses `distilbert-base-uncased-finetuned-sst-2-english` from HuggingFace.
```

### Using Secrets

```python
import os
import gradio as gr
from openai import OpenAI

# Access secret (set in Space settings)
api_key = os.environ.get("OPENAI_API_KEY")

if not api_key:
    raise ValueError("OPENAI_API_KEY not found in secrets")

client = OpenAI(api_key=api_key)

def generate_with_gpt(prompt):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

demo = gr.Interface(
    fn=generate_with_gpt,
    inputs=gr.Textbox(lines=3, label="Prompt"),
    outputs=gr.Textbox(lines=5, label="Response"),
    title="GPT-3.5 Generator"
)

demo.launch()
```

### GPU-Accelerated Inference

```python
import gradio as gr
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

# Check GPU availability
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")

# Load model to GPU
model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-2-7b-chat-hf",
    torch_dtype=torch.float16,
    device_map="auto"
)
tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-2-7b-chat-hf")

def generate(prompt, max_length=100):
    inputs = tokenizer(prompt, return_tensors="pt").to(device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_length=max_length,
            temperature=0.7,
            top_p=0.95,
            do_sample=True
        )

    return tokenizer.decode(outputs[0], skip_special_tokens=True)

demo = gr.Interface(
    fn=generate,
    inputs=[
        gr.Textbox(lines=3, label="Prompt"),
        gr.Slider(50, 500, value=100, label="Max Length")
    ],
    outputs=gr.Textbox(lines=10, label="Generated Text"),
    title="Llama 2 Chat (GPU-Accelerated)"
)

demo.launch()
```

### Custom Domain and Embedding

```python
import gradio as gr

demo = gr.Interface(
    fn=lambda x: x,
    inputs=gr.Textbox(),
    outputs=gr.Textbox(),
    title="My App"
)

# Launch with custom settings
demo.launch(
    share=False,  # Don't create temporary share link
    show_api=True,  # Show API documentation
    show_error=True  # Show errors in UI
)
```

**Embed in HTML**:
```html
<!-- Embed Space in website -->
<iframe
  src="https://username-space-name.hf.space"
  frameborder="0"
  width="850"
  height="450"
></iframe>

<!-- Embed with Gradio JS -->
<script type="module" src="https://gradio.s3-us-west-2.amazonaws.com/3.50.0/gradio.js"></script>

<gradio-app src="https://username-space-name.hf.space"></gradio-app>
```

---

## Quick Reference

### Gradio Components

```
Component           | Type        | Use Case
--------------------|-------------|---------------------------
Textbox             | Input       | Text input/output
Slider              | Input       | Numeric range selection
Image               | Input       | Image upload
Audio               | Input       | Audio upload
Video               | Input       | Video upload
File                | Input       | File upload
Label               | Output      | Classification results
JSON                | Output      | Structured data
HTML                | Output      | Custom HTML
Plot                | Output      | Matplotlib/Plotly plots
```

### Streamlit Components

```
Component           | Function              | Use Case
--------------------|-----------------------|---------------------------
text_input()        | st.text_input()       | Single line text
text_area()         | st.text_area()        | Multi-line text
slider()            | st.slider()           | Numeric slider
selectbox()         | st.selectbox()        | Dropdown selection
file_uploader()     | st.file_uploader()    | File upload
image()             | st.image()            | Display image
dataframe()         | st.dataframe()        | Display table
chart()             | st.line_chart()       | Line chart
metric()            | st.metric()           | Key metric display
```

### Hardware Tiers

```
Tier          | vCPU | RAM   | GPU VRAM | Cost/Hour | Use Case
--------------|------|-------|----------|-----------|---------------------------
CPU Basic     | 2    | 16GB  | -        | Free      | Light inference
CPU Upgrade   | 8    | 32GB  | -        | $0.03     | CPU-intensive tasks
T4 Small      | 4    | 15GB  | 16GB     | $0.60     | Small models (<7B)
A10G Large    | 12   | 46GB  | 24GB     | $3.15     | Medium models (7-13B)
A100 Large    | 12   | 142GB | 40GB     | $4.13     | Large models (13B+)
```

### Key Guidelines

```
✅ DO: Cache model loading with @st.cache_resource (Streamlit)
✅ DO: Provide example inputs for easier testing
✅ DO: Use secrets for API keys and tokens
✅ DO: Test locally before deploying
✅ DO: Set appropriate hardware tier for model size
✅ DO: Add loading states and error handling

❌ DON'T: Hardcode API keys in code
❌ DON'T: Load models on every function call
❌ DON'T: Use GPU for CPU-compatible models
❌ DON'T: Forget to add title and description
```

---

## Anti-Patterns

### Critical Violations

```python
# ❌ NEVER: Hardcode secrets
api_key = "sk-xxxxxxxxxxxx"  # SECURITY RISK!

# ✅ CORRECT: Use environment variables
api_key = os.environ.get("OPENAI_API_KEY")
```

❌ **Hardcoded secrets**: Security breach, exposed in public repos
✅ **Correct approach**: Use Space secrets in settings

### Common Mistakes

```python
# ❌ Don't: Load model on every call (Streamlit)
def predict(text):
    model = pipeline("sentiment-analysis")  # Reloads every time!
    return model(text)

# ✅ Correct: Cache model loading
@st.cache_resource
def load_model():
    return pipeline("sentiment-analysis")

model = load_model()

def predict(text):
    return model(text)
```

❌ **No model caching**: Slow, wastes resources
✅ **Better**: Cache with `@st.cache_resource` or load globally

```python
# ❌ Don't: Use GPU for small models
# Running CPU-compatible model on A100 ($4/hr)
model = pipeline("sentiment-analysis", model="distilbert-base-uncased")

# ✅ Correct: Use CPU for small models
# Save costs, same performance
model = pipeline("sentiment-analysis", model="distilbert-base-uncased", device="cpu")
```

❌ **Wrong hardware tier**: Wasted cost
✅ **Better**: Match hardware to model requirements

```python
# ❌ Don't: No error handling
def predict(text):
    return model(text)  # Crashes on invalid input

# ✅ Correct: Handle errors gracefully
def predict(text):
    try:
        if not text or len(text.strip()) == 0:
            return "Please enter some text"
        return model(text)
    except Exception as e:
        return f"Error: {str(e)}"
```

❌ **No error handling**: Poor user experience
✅ **Better**: Validate inputs and catch exceptions

```python
# ❌ Don't: Missing examples
demo = gr.Interface(fn=predict, inputs=..., outputs=...)

# ✅ Correct: Provide examples
demo = gr.Interface(
    fn=predict,
    inputs=...,
    outputs=...,
    examples=[
        ["Example input 1"],
        ["Example input 2"]
    ]
)
```

❌ **No examples**: Users don't know what to try
✅ **Better**: Always provide 2-5 example inputs

---

## Related Skills

- `ml/huggingface/huggingface-hub.md` - Managing Space repositories
- `ml/huggingface/huggingface-transformers.md` - Loading models for Spaces
- `frontend/elegant-design.md` - Improving UI/UX of custom interfaces
- `modal/modal-web-endpoints.md` - Alternative deployment platform
- `infrastructure/cloudflare-workers.md` - Edge deployment alternative

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
