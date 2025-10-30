---
name: dspy-integrations
description: Framework integrations for DSPy including LangChain, LlamaIndex, MLflow, FastAPI, Gradio, and database systems
---

# DSPy Integrations

**Scope**: LangChain, LlamaIndex, MLflow, FastAPI, Gradio, Streamlit, databases, MCP/A2A protocols
**Lines**: ~500
**Last Updated**: 2025-10-30

## When to Use This Skill

Activate this skill when:
- Integrating DSPy with LangChain or LlamaIndex
- Adding DSPy programs to existing applications
- Building web APIs with FastAPI or Flask
- Creating UIs with Gradio or Streamlit
- Tracking experiments with MLflow or W&B
- Deploying on Databricks or cloud platforms
- Connecting DSPy to databases
- Implementing MCP (Model Context Protocol) or A2A patterns

## Core Concepts

### Integration Patterns

**Embedding DSPy**:
- DSPy as component in larger system
- Wrap DSPy modules for external APIs
- Adapt inputs/outputs for compatibility
- Maintain DSPy optimization capabilities

**Wrapping External Tools**:
- Use external tools within DSPy
- Create DSPy-compatible interfaces
- Preserve type safety and signatures
- Enable optimization across boundaries

**Bidirectional Integration**:
- DSPy calls external, external calls DSPy
- Shared state management
- Consistent error handling
- Unified logging and monitoring

### Common Integration Challenges

**API Mismatches**:
- Different input/output formats
- Incompatible type systems
- Async vs sync interfaces
- Error handling differences

**State Management**:
- Stateless DSPy vs stateful frameworks
- Session management
- Context preservation
- Optimization artifacts

**Performance**:
- Overhead from adapters
- Serialization costs
- Network latency
- Resource contention

---

## Patterns

### Pattern 1: LangChain Integration

```python
import dspy
from langchain.llms.base import LLM
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from typing import Optional, List, Any

class DSPyLangChainLLM(LLM):
    """Wrap DSPy LM as LangChain LLM."""

    dspy_lm: Any
    module: dspy.Module

    def __init__(self, dspy_lm, signature: str = "input -> output"):
        super().__init__()
        self.dspy_lm = dspy_lm
        dspy.configure(lm=dspy_lm)
        self.module = dspy.Predict(signature)

    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        """Execute DSPy module on prompt."""
        result = self.module(input=prompt)
        return result.output

    @property
    def _llm_type(self) -> str:
        return "dspy"

class LangChainDSPyBridge:
    """Use LangChain tools within DSPy."""

    def __init__(self, langchain_chain: LLMChain):
        self.chain = langchain_chain

    def __call__(self, **kwargs) -> str:
        """Execute LangChain chain."""
        return self.chain.run(**kwargs)

# Example 1: Use DSPy in LangChain
dspy_lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
dspy_langchain_llm = DSPyLangChainLLM(dspy_lm, signature="question -> answer")

# Use in LangChain chain
template = "Question: {question}\nAnswer:"
prompt = PromptTemplate(template=template, input_variables=["question"])
langchain_chain = LLMChain(llm=dspy_langchain_llm, prompt=prompt)

result = langchain_chain.run(question="What is DSPy?")
print(result)

# Example 2: Use LangChain tools in DSPy
from langchain.tools import Tool

def search_tool(query: str) -> str:
    """Simulated search tool."""
    return f"Search results for: {query}"

lc_tool = Tool(
    name="Search",
    func=search_tool,
    description="Search for information",
)

class DSPyWithLangChainTools(dspy.Module):
    """DSPy module using LangChain tools."""

    def __init__(self, tools: List[Tool]):
        super().__init__()
        self.tools = {tool.name: tool.func for tool in tools}
        self.planner = dspy.ChainOfThought("question -> tool_name: str, tool_input: str")
        self.synthesizer = dspy.Predict("question, search_result -> answer")

    def forward(self, question):
        # Plan which tool to use
        plan = self.planner(question=question)

        # Execute tool
        if plan.tool_name in self.tools:
            tool_result = self.tools[plan.tool_name](plan.tool_input)
        else:
            tool_result = "Tool not found"

        # Synthesize answer
        result = self.synthesizer(
            question=question,
            search_result=tool_result,
        )

        return result

# Use LangChain tools in DSPy
lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
dspy.configure(lm=lm)

dspy_module = DSPyWithLangChainTools(tools=[lc_tool])
result = dspy_module(question="What is the weather in Paris?")
print(result.answer)
```

**When to use**:
- Existing LangChain infrastructure
- Need LangChain's tool ecosystem
- Gradual migration to/from DSPy
- Hybrid architectures

**Benefits**:
- Access LangChain's tools
- Incremental adoption
- Maintain existing code
- Best of both worlds

### Pattern 2: LlamaIndex Integration

```python
import dspy
from llama_index.core import VectorStoreIndex, Document, Settings
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.retrievers import VectorIndexRetriever
from typing import List

class DSPyLlamaIndexRAG(dspy.Module):
    """DSPy RAG using LlamaIndex retriever."""

    def __init__(self, llama_index: VectorStoreIndex, top_k: int = 3):
        super().__init__()
        self.retriever = VectorIndexRetriever(
            index=llama_index,
            similarity_top_k=top_k,
        )
        self.generator = dspy.ChainOfThought("context, question -> answer")

    def forward(self, question):
        # Retrieve using LlamaIndex
        nodes = self.retriever.retrieve(question)

        # Extract text from nodes
        context = "\n\n".join([node.text for node in nodes])

        # Generate answer using DSPy
        result = self.generator(context=context, question=question)

        return result

class LlamaIndexDSPyBridge:
    """Use DSPy as LLM in LlamaIndex."""

    def __init__(self, dspy_module: dspy.Module):
        self.dspy_module = dspy_module

    def complete(self, prompt: str) -> str:
        """LlamaIndex LLM interface."""
        result = self.dspy_module(input=prompt)
        return result.output

    def stream_complete(self, prompt: str):
        """Streaming interface (simplified)."""
        return self.complete(prompt)

# Example 1: Use LlamaIndex retriever in DSPy
lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
dspy.configure(lm=lm)

# Create LlamaIndex
documents = [
    Document(text="DSPy is a framework for programming language models."),
    Document(text="DSPy uses signatures to define tasks."),
    Document(text="DSPy optimizers improve prompts automatically."),
]

index = VectorStoreIndex.from_documents(documents)

# Use in DSPy
rag = DSPyLlamaIndexRAG(llama_index=index, top_k=2)
result = rag(question="What is DSPy?")
print(result.answer)

# Example 2: Use DSPy in LlamaIndex
dspy_module = dspy.Predict("input -> output")
llama_llm = LlamaIndexDSPyBridge(dspy_module)

# Configure LlamaIndex with DSPy LLM
Settings.llm = llama_llm

# Now LlamaIndex uses DSPy internally
query_engine = index.as_query_engine()
response = query_engine.query("What is DSPy?")
print(response)
```

**When to use**:
- Advanced retrieval strategies
- Complex document processing
- Multi-modal RAG
- Existing LlamaIndex pipelines

**Benefits**:
- Powerful retrieval
- Document management
- Index optimization
- Rich ecosystem

### Pattern 3: FastAPI Web Service

```python
import dspy
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import uvicorn

app = FastAPI(title="DSPy API")

# Initialize DSPy
lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
dspy.configure(lm=lm)

# Create DSPy modules
qa_module = dspy.ChainOfThought("question -> answer")
classifier = dspy.Predict("text -> category, confidence: float")

# Pydantic models for API
class QuestionRequest(BaseModel):
    question: str
    max_tokens: Optional[int] = 500

class QuestionResponse(BaseModel):
    answer: str
    reasoning: Optional[str] = None

class ClassificationRequest(BaseModel):
    text: str

class ClassificationResponse(BaseModel):
    category: str
    confidence: float

# API endpoints
@app.post("/qa", response_model=QuestionResponse)
async def question_answering(request: QuestionRequest):
    """Question answering endpoint."""
    try:
        result = qa_module(question=request.question)
        return QuestionResponse(
            answer=result.answer,
            reasoning=getattr(result, "reasoning", None),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/classify", response_model=ClassificationResponse)
async def classify_text(request: ClassificationRequest):
    """Text classification endpoint."""
    try:
        result = classifier(text=request.text)
        return ClassificationResponse(
            category=result.category,
            confidence=result.confidence,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

# Run server: uvicorn main:app --reload
# API docs: http://localhost:8000/docs

# Client example
import requests

# Question answering
response = requests.post(
    "http://localhost:8000/qa",
    json={"question": "What is DSPy?"},
)
print(response.json())

# Classification
response = requests.post(
    "http://localhost:8000/classify",
    json={"text": "This is amazing!"},
)
print(response.json())
```

**When to use**:
- Building APIs for DSPy programs
- Microservices architecture
- Web integration
- Production deployments

**Benefits**:
- REST API standard
- Auto-generated docs
- Type validation
- Async support

### Pattern 4: Gradio UI

```python
import dspy
import gradio as gr

# Initialize DSPy
lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
dspy.configure(lm=lm)

# Create modules
qa_module = dspy.ChainOfThought("question -> answer")
summarizer = dspy.Predict("text -> summary")

# Gradio interface functions
def answer_question(question: str) -> tuple[str, str]:
    """Answer question and return answer + reasoning."""
    try:
        result = qa_module(question=question)
        return result.answer, getattr(result, "reasoning", "")
    except Exception as e:
        return f"Error: {e}", ""

def summarize_text(text: str, max_length: int) -> str:
    """Summarize text."""
    try:
        result = summarizer(text=text)
        return result.summary
    except Exception as e:
        return f"Error: {e}"

# Create Gradio interface
with gr.Blocks(title="DSPy Demo") as demo:
    gr.Markdown("# DSPy Question Answering & Summarization")

    with gr.Tab("Question Answering"):
        with gr.Row():
            with gr.Column():
                question_input = gr.Textbox(
                    label="Question",
                    placeholder="Ask a question...",
                    lines=3,
                )
                qa_button = gr.Button("Answer")

            with gr.Column():
                answer_output = gr.Textbox(label="Answer", lines=5)
                reasoning_output = gr.Textbox(label="Reasoning", lines=5)

        qa_button.click(
            fn=answer_question,
            inputs=[question_input],
            outputs=[answer_output, reasoning_output],
        )

    with gr.Tab("Summarization"):
        with gr.Row():
            with gr.Column():
                text_input = gr.Textbox(
                    label="Text to Summarize",
                    placeholder="Enter text...",
                    lines=10,
                )
                max_length = gr.Slider(
                    minimum=50,
                    maximum=500,
                    value=150,
                    label="Max Summary Length",
                )
                sum_button = gr.Button("Summarize")

            with gr.Column():
                summary_output = gr.Textbox(label="Summary", lines=10)

        sum_button.click(
            fn=summarize_text,
            inputs=[text_input, max_length],
            outputs=[summary_output],
        )

    with gr.Tab("Examples"):
        gr.Examples(
            examples=[
                ["What is machine learning?"],
                ["Explain quantum computing."],
                ["What is the capital of France?"],
            ],
            inputs=[question_input],
        )

# Launch
demo.launch(share=False)
```

**When to use**:
- Quick demos and prototypes
- Internal tools
- User testing
- Showcasing capabilities

**Benefits**:
- Rapid UI development
- Built-in components
- Easy sharing
- No frontend code

### Pattern 5: MLflow Tracking

```python
import dspy
import mlflow
from typing import List

class MLflowTrackedProgram(dspy.Module):
    """DSPy program with MLflow tracking."""

    def __init__(self, signature: str, experiment_name: str = "dspy"):
        super().__init__()
        self.predictor = dspy.ChainOfThought(signature)
        self.experiment_name = experiment_name

        # Set up MLflow
        mlflow.set_experiment(experiment_name)

    def forward(self, **kwargs):
        """Execute with MLflow tracking."""
        with mlflow.start_run():
            # Log parameters
            mlflow.log_params({
                "signature": str(self.predictor.signature),
                **kwargs,
            })

            # Execute prediction
            try:
                result = self.predictor(**kwargs)

                # Log outputs
                mlflow.log_dict(
                    {field: getattr(result, field) for field in result._fields},
                    "outputs.json",
                )

                # Log metrics (if available)
                if hasattr(result, "confidence"):
                    mlflow.log_metric("confidence", result.confidence)

                return result

            except Exception as e:
                mlflow.log_param("error", str(e))
                raise e

def optimize_with_mlflow(
    program: dspy.Module,
    trainset: List[dspy.Example],
    experiment_name: str = "dspy_optimization",
):
    """Optimize DSPy program with MLflow tracking."""
    mlflow.set_experiment(experiment_name)

    with mlflow.start_run(run_name="optimization"):
        # Log training data info
        mlflow.log_param("trainset_size", len(trainset))

        # Optimize
        metric = lambda ex, pred: float(ex.answer in pred.answer)
        optimizer = dspy.BootstrapFewShot(metric=metric)

        optimized = optimizer.compile(program, trainset=trainset)

        # Evaluate and log metrics
        scores = []
        for example in trainset:
            pred = optimized(**example.inputs())
            score = metric(example, pred)
            scores.append(score)

        accuracy = sum(scores) / len(scores)
        mlflow.log_metric("accuracy", accuracy)

        # Log model
        mlflow.pyfunc.log_model(
            artifact_path="model",
            python_model=optimized,
        )

        print(f"Logged to MLflow: accuracy={accuracy:.2%}")

    return optimized

# Usage
lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
dspy.configure(lm=lm)

# Track individual predictions
tracked_qa = MLflowTrackedProgram(
    "question -> answer",
    experiment_name="qa_system",
)
result = tracked_qa(question="What is DSPy?")

# Track optimization
trainset = [
    dspy.Example(question="What is 2+2?", answer="4").with_inputs("question"),
    dspy.Example(question="What is 3+3?", answer="6").with_inputs("question"),
]

program = dspy.ChainOfThought("question -> answer")
optimized = optimize_with_mlflow(program, trainset)

# View in MLflow UI: mlflow ui
```

**When to use**:
- Experiment tracking
- Model versioning
- Team collaboration
- Production monitoring

**Benefits**:
- Track experiments
- Compare runs
- Version models
- Share results

### Pattern 6: Database Integration

```python
import dspy
import sqlite3
from typing import List, Dict, Any

class DatabaseRAG(dspy.Module):
    """RAG system using database for retrieval."""

    def __init__(self, db_path: str):
        super().__init__()
        self.db_path = db_path
        self.generator = dspy.ChainOfThought("context, question -> answer")

        # Initialize database
        self._init_db()

    def _init_db(self):
        """Initialize database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY,
                text TEXT NOT NULL,
                metadata TEXT
            )
        """)

        conn.commit()
        conn.close()

    def add_documents(self, documents: List[Dict[str, Any]]):
        """Add documents to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for doc in documents:
            cursor.execute(
                "INSERT INTO documents (text, metadata) VALUES (?, ?)",
                (doc["text"], str(doc.get("metadata", {}))),
            )

        conn.commit()
        conn.close()

    def retrieve(self, query: str, top_k: int = 3) -> List[str]:
        """Retrieve relevant documents (simple keyword match)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Simple keyword search
        keywords = query.lower().split()
        conditions = " OR ".join([f"LOWER(text) LIKE ?" for _ in keywords])
        params = [f"%{kw}%" for kw in keywords]

        cursor.execute(
            f"SELECT text FROM documents WHERE {conditions} LIMIT ?",
            params + [top_k],
        )

        results = [row[0] for row in cursor.fetchall()]
        conn.close()

        return results

    def forward(self, question):
        """Answer question using database retrieval."""
        # Retrieve relevant documents
        documents = self.retrieve(question, top_k=3)

        if not documents:
            return dspy.Prediction(answer="No relevant information found.")

        # Generate answer
        context = "\n\n".join(documents)
        result = self.generator(context=context, question=question)

        return result

# Usage
lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
dspy.configure(lm=lm)

# Create database RAG
db_rag = DatabaseRAG(db_path="knowledge.db")

# Add documents
db_rag.add_documents([
    {"text": "DSPy is a framework for programming language models."},
    {"text": "DSPy uses signatures to define input/output behavior."},
    {"text": "DSPy optimizers automatically improve prompts."},
])

# Query
result = db_rag(question="What is DSPy?")
print(result.answer)

# Advanced: Use with other databases
class PostgresRAG(dspy.Module):
    """RAG using PostgreSQL with pgvector."""

    def __init__(self, connection_string: str):
        super().__init__()
        self.conn_string = connection_string
        self.generator = dspy.ChainOfThought("context, question -> answer")

    def retrieve(self, query: str, top_k: int = 3) -> List[str]:
        """Retrieve using vector similarity."""
        import psycopg2

        conn = psycopg2.connect(self.conn_string)
        cursor = conn.cursor()

        # Use pgvector for semantic search
        cursor.execute("""
            SELECT text FROM documents
            ORDER BY embedding <-> %s
            LIMIT %s
        """, (query, top_k))

        results = [row[0] for row in cursor.fetchall()]
        conn.close()

        return results

    def forward(self, question):
        documents = self.retrieve(question)
        context = "\n\n".join(documents)
        return self.generator(context=context, question=question)
```

**Databases supported**:
- SQLite (embedded)
- PostgreSQL (pgvector)
- MongoDB (document store)
- Redis (caching)
- Elasticsearch (search)

### Pattern 7: Streamlit App

```python
import dspy
import streamlit as st

# Page config
st.set_page_config(
    page_title="DSPy Demo",
    page_icon="🤖",
    layout="wide",
)

# Initialize DSPy (cached)
@st.cache_resource
def load_dspy():
    lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
    dspy.configure(lm=lm)
    return {
        "qa": dspy.ChainOfThought("question -> answer"),
        "summarizer": dspy.Predict("text -> summary"),
    }

modules = load_dspy()

# Sidebar
with st.sidebar:
    st.title("DSPy Modules")
    module_choice = st.selectbox(
        "Choose module",
        ["Question Answering", "Summarization"],
    )

# Main content
st.title("🤖 DSPy Demo")

if module_choice == "Question Answering":
    st.header("Question Answering")

    question = st.text_area("Enter your question:", height=100)

    if st.button("Answer"):
        if question:
            with st.spinner("Thinking..."):
                result = modules["qa"](question=question)

            st.success("Answer:")
            st.write(result.answer)

            if hasattr(result, "reasoning"):
                with st.expander("View Reasoning"):
                    st.write(result.reasoning)
        else:
            st.warning("Please enter a question")

elif module_choice == "Summarization":
    st.header("Text Summarization")

    text = st.text_area("Enter text to summarize:", height=200)

    max_length = st.slider("Max summary length", 50, 500, 150)

    if st.button("Summarize"):
        if text:
            with st.spinner("Summarizing..."):
                result = modules["summarizer"](text=text)

            st.success("Summary:")
            st.write(result.summary)
        else:
            st.warning("Please enter text")

# Run: streamlit run app.py
```

**When to use**:
- Data science applications
- Internal dashboards
- Quick prototypes
- Interactive demos

### Pattern 8: MCP/A2A Protocol Integration

```python
import dspy
from typing import Dict, Any, List
import json

class MCPDSPyAdapter:
    """Adapter for Model Context Protocol."""

    def __init__(self, dspy_module: dspy.Module):
        self.module = dspy_module

    def handle_request(self, mcp_request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP request format."""
        # Extract MCP fields
        context = mcp_request.get("context", {})
        prompt = mcp_request.get("prompt", "")
        parameters = mcp_request.get("parameters", {})

        # Map to DSPy inputs
        dspy_inputs = {
            "question": prompt,
            **parameters,
        }

        # Execute DSPy module
        try:
            result = self.module(**dspy_inputs)

            # Convert to MCP response format
            mcp_response = {
                "status": "success",
                "output": {
                    field: getattr(result, field)
                    for field in result._fields
                },
                "metadata": {
                    "module": self.module.__class__.__name__,
                },
            }

            return mcp_response

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

class A2AProtocolAdapter:
    """Adapter for Agent-to-Agent protocol."""

    def __init__(self, dspy_module: dspy.Module, agent_id: str):
        self.module = dspy_module
        self.agent_id = agent_id

    def send_message(self, to_agent: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """Send A2A message."""
        # Execute DSPy module
        result = self.module(**message.get("payload", {}))

        # Format as A2A message
        return {
            "from": self.agent_id,
            "to": to_agent,
            "message_type": "response",
            "payload": {
                field: getattr(result, field)
                for field in result._fields
            },
            "timestamp": "2025-10-30T00:00:00Z",
        }

    def receive_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Receive and process A2A message."""
        if message.get("message_type") == "request":
            payload = message.get("payload", {})
            response = self.module(**payload)

            return {
                "from": self.agent_id,
                "to": message["from"],
                "message_type": "response",
                "payload": {
                    field: getattr(response, field)
                    for field in response._fields
                },
            }

        return {"status": "unknown_message_type"}

# Usage
lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
dspy.configure(lm=lm)

qa_module = dspy.ChainOfThought("question -> answer")

# MCP adapter
mcp_adapter = MCPDSPyAdapter(qa_module)

mcp_request = {
    "context": {"domain": "general"},
    "prompt": "What is DSPy?",
    "parameters": {},
}

mcp_response = mcp_adapter.handle_request(mcp_request)
print(json.dumps(mcp_response, indent=2))

# A2A adapter
a2a_adapter = A2AProtocolAdapter(qa_module, agent_id="dspy_agent_1")

a2a_request = {
    "from": "coordinator",
    "to": "dspy_agent_1",
    "message_type": "request",
    "payload": {"question": "What is DSPy?"},
}

a2a_response = a2a_adapter.receive_message(a2a_request)
print(json.dumps(a2a_response, indent=2))
```

**When to use**:
- Multi-agent systems
- Protocol standardization
- Interoperability
- Distributed architectures

---

## Quick Reference

### Integration Checklist

```
Before integrating:
✅ Understand both API interfaces
✅ Identify data format mismatches
✅ Plan error handling strategy
✅ Consider performance overhead

During integration:
✅ Create adapter layer
✅ Handle type conversions
✅ Maintain error context
✅ Add logging/monitoring

After integration:
✅ Test edge cases
✅ Document integration
✅ Monitor performance
✅ Version adapter code
```

### Common Integration Patterns

| Framework | Pattern | Use Case |
|-----------|---------|----------|
| LangChain | Wrapper LLM | Use DSPy in LangChain chains |
| LlamaIndex | Custom retriever | Advanced RAG with DSPy |
| FastAPI | REST endpoints | Web API for DSPy |
| Gradio | UI wrapper | Quick demos |
| MLflow | Tracking decorator | Experiment tracking |
| Streamlit | Cached module | Interactive dashboards |

### Installation Commands

```bash
# LangChain
uv add langchain langchain-community

# LlamaIndex
uv add llama-index

# Web frameworks
uv add fastapi uvicorn gradio streamlit

# Experiment tracking
uv add mlflow wandb

# Databases
uv add sqlalchemy psycopg2 pymongo redis
```

---

## Anti-Patterns

❌ **Tight coupling**: Hard to maintain
```python
# Bad - direct dependencies everywhere
def my_function():
    langchain_result = langchain_chain.run()
    dspy_result = dspy_module(langchain_result)
    return dspy_result
```
✅ Use adapter pattern:
```python
# Good
adapter = LangChainDSPyBridge(langchain_chain)
result = adapter(input=data)
```

❌ **No error mapping**: Confusing errors
```python
# Bad
try:
    result = external_tool(data)
except Exception as e:
    raise e  # Unclear which system failed
```
✅ Map errors properly:
```python
# Good
try:
    result = external_tool(data)
except ExternalError as e:
    raise IntegrationError(f"External tool failed: {e}")
```

❌ **Performance ignorance**: Slow integrations
```python
# Bad
for item in large_list:
    result = dspy_module(item)  # No batching
```
✅ Batch when possible:
```python
# Good
results = dspy_module.batch(items=large_list)
```

---

## Related Skills

- `dspy-production.md` - Production deployment
- `fastapi-advanced.md` - FastAPI patterns
- `mlflow-tracking.md` - Experiment tracking
- `langchain-agents.md` - LangChain integration
- `llamaindex-rag.md` - LlamaIndex patterns

---

**Last Updated**: 2025-10-30
**Format Version**: 1.0 (Atomic)
