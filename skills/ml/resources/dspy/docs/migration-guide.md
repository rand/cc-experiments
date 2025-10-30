# DSPy Migration Guide

Guide for upgrading DSPy applications across versions and migrating from other frameworks.

## Table of Contents
- [Upgrading DSPy Versions](#upgrading-dspy-versions)
- [Breaking Changes by Version](#breaking-changes-by-version)
- [Migrating from Other Frameworks](#migrating-from-other-frameworks)
- [Migration Strategies](#migration-strategies)
- [Compatibility Matrix](#compatibility-matrix)

---

## Upgrading DSPy Versions

### Pre-Migration Checklist

**Before upgrading**:
- [ ] Review changelog for breaking changes
- [ ] Create git branch for migration
- [ ] Back up compiled models (`.json`, `.pkl` files)
- [ ] Document current performance metrics (baseline)
- [ ] Run full test suite on current version
- [ ] Check dependency compatibility (LM providers, databases)
- [ ] Estimate re-optimization time and cost
- [ ] Schedule downtime if needed

### Migration Process

**Step 1: Environment Setup**
```bash
# Create isolated environment
python -m venv venv-dspy-new
source venv-dspy-new/bin/activate

# Install new version
pip install dspy-ai==<new-version>

# Install dependencies
pip install -r requirements.txt
```

**Step 2: Code Compatibility Check**
```python
# Run import check
import dspy
print(f"DSPy version: {dspy.__version__}")

# Check for deprecated APIs
import warnings
warnings.filterwarnings('default', category=DeprecationWarning)

# Test basic functionality
lm = dspy.OpenAI(model="gpt-3.5-turbo")
dspy.settings.configure(lm=lm)
```

**Step 3: Update Codebase**
```bash
# Run automated migration tools (if available)
dspy-migrate --from 2.0 --to 2.5 --path src/

# Review and fix deprecation warnings
pytest -W default::DeprecationWarning

# Update signatures, modules, optimizers
# (See version-specific sections below)
```

**Step 4: Test Migration**
```bash
# Run unit tests
pytest tests/unit/ -v

# Run integration tests
pytest tests/integration/ -v

# Evaluate on test set
python scripts/evaluate.py --dataset test.jsonl
```

**Step 5: Re-optimize (if needed)**
```python
# Check if compiled models still work
program = dspy.load("models/qa_v2.json")
result = program(question="Test question")

# If performance degrades, re-optimize
from dspy.teleprompt import MIPROv2

optimizer = MIPROv2(metric=accuracy, num_candidates=10)
optimized = optimizer.compile(program, trainset=train)
```

**Step 6: Validate Performance**
```bash
# Compare metrics: old vs new
python scripts/compare_metrics.py \
  --baseline metrics_old.json \
  --current metrics_new.json

# Check latency and throughput
python scripts/benchmark.py --runs 100
```

**Step 7: Deploy**
```bash
# Deploy to staging
./deploy_staging.sh

# Run smoke tests
pytest tests/smoke/ --env staging

# Deploy to production with canary
./deploy_production.sh --strategy canary --percent 10

# Monitor for 24 hours, then full rollout
```

---

## Breaking Changes by Version

### DSPy 2.5 → 3.0

**Signatures**:
```python
# OLD (2.5)
class QA(dspy.Signature):
    question = dspy.InputField()
    answer = dspy.OutputField()

# NEW (3.0) - Explicit class-based fields
class QA(dspy.Signature):
    """Answer questions."""
    question: str = dspy.InputField()
    answer: str = dspy.OutputField()
```

**Optimizers**:
```python
# OLD (2.5)
optimizer = dspy.BootstrapFewShot(metric=accuracy)
optimized = optimizer.compile(program, trainset=train)

# NEW (3.0) - Renamed to Teleprompter
from dspy.teleprompt import BootstrapFewShot

teleprompter = BootstrapFewShot(metric=accuracy)
optimized = teleprompter.compile(program, trainset=train)
```

**Configuration**:
```python
# OLD (2.5)
dspy.settings.configure(lm=lm, rm=rm)

# NEW (3.0) - Context manager
with dspy.context(lm=lm, rm=rm):
    result = program(input)
```

**Assertions**:
```python
# OLD (2.5)
dspy.Assert(len(answer) > 10, "Answer too short")

# NEW (3.0) - Returns Assertion object
from dspy.primitives import Assertion

assertion = Assertion(
    constraint=lambda x: len(x.answer) > 10,
    msg="Answer too short",
    backtrack=True
)
```

**Migration Script**:
```python
# migrate_2_5_to_3_0.py
import re
from pathlib import Path

def migrate_signatures(code: str) -> str:
    """Add type hints to signatures."""
    pattern = r'(\w+)\s*=\s*dspy\.(Input|Output)Field\(\)'
    replacement = r'\1: str = dspy.\2Field()'
    return re.sub(pattern, replacement, code)

def migrate_optimizers(code: str) -> str:
    """Rename optimizer imports."""
    code = code.replace(
        'dspy.BootstrapFewShot',
        'dspy.teleprompt.BootstrapFewShot'
    )
    code = code.replace(
        'dspy.MIPROv2',
        'dspy.teleprompt.MIPROv2'
    )
    return code

def migrate_file(path: Path):
    """Migrate a single file."""
    code = path.read_text()
    code = migrate_signatures(code)
    code = migrate_optimizers(code)
    path.write_text(code)
    print(f"Migrated: {path}")

if __name__ == "__main__":
    for path in Path("src/").rglob("*.py"):
        migrate_file(path)
```

### DSPy 2.0 → 2.5

**Modules**:
```python
# OLD (2.0)
class QA(dspy.Module):
    def __init__(self):
        self.generate = dspy.Predict("question -> answer")

# NEW (2.5) - Signature classes preferred
class QA(dspy.Module):
    def __init__(self):
        self.generate = dspy.Predict(QASignature)
```

**Retrieval**:
```python
# OLD (2.0)
rm = dspy.Retrieve(k=5)
passages = rm(query)

# NEW (2.5) - Returns dspy.Prediction
rm = dspy.Retrieve(k=5)
prediction = rm(query)
passages = prediction.passages  # Access via attribute
```

**Evaluation**:
```python
# OLD (2.0)
evaluate = dspy.Evaluate(devset=dev, metric=accuracy)
score = evaluate(program)

# NEW (2.5) - Display progress and details
from dspy.evaluate import Evaluate

evaluate = Evaluate(
    devset=dev,
    metric=accuracy,
    display_progress=True,
    display_table=True
)
score = evaluate(program)
```

### DSPy 1.x → 2.0

**Major Rewrite**: DSPy 2.0 was a complete rewrite. Migration requires full refactor.

**Key Changes**:
- Introduction of Signature classes (vs string-based)
- Module-based architecture (vs functional)
- Teleprompter optimization framework
- LM and RM abstraction improvements
- Assertions and validation framework

**Migration Strategy**: Rewrite applications from scratch using DSPy 2.0 patterns. Treat as greenfield project.

---

## Migrating from Other Frameworks

### From LangChain

**LangChain Concepts → DSPy Equivalents**:

| LangChain | DSPy Equivalent |
|-----------|-----------------|
| `PromptTemplate` | `dspy.Signature` |
| `LLMChain` | `dspy.Predict` |
| `SequentialChain` | `dspy.Module` with multiple `forward` calls |
| `RetrievalQA` | `dspy.ChainOfThought` + `dspy.Retrieve` |
| `ConversationBufferMemory` | Custom state in `dspy.Module` |
| `Agent` | `dspy.ReAct` |
| `Tool` | Python function with signature |

**Example Migration**:

```python
# LangChain
from langchain import LLMChain, PromptTemplate

prompt = PromptTemplate(
    input_variables=["question"],
    template="Answer the question: {question}"
)
chain = LLMChain(llm=llm, prompt=prompt)
result = chain.run(question="What is AI?")

# DSPy
class QA(dspy.Signature):
    """Answer questions."""
    question: str = dspy.InputField()
    answer: str = dspy.OutputField()

class QAModule(dspy.Module):
    def __init__(self):
        self.generate = dspy.ChainOfThought(QA)

    def forward(self, question):
        return self.generate(question=question)

qa = QAModule()
result = qa(question="What is AI?")
```

**Benefits of DSPy**:
- Optimizable prompts (no manual prompt engineering)
- Type-safe signatures
- Automatic prompt evolution
- Built-in evaluation framework
- Cleaner module composition

### From LlamaIndex

**LlamaIndex Concepts → DSPy Equivalents**:

| LlamaIndex | DSPy Equivalent |
|------------|-----------------|
| `VectorStoreIndex` | `dspy.Retrieve` with vector RM |
| `QueryEngine` | `dspy.Module` with retrieval |
| `ResponseSynthesizer` | `dspy.ChainOfThought` |
| `ChatEngine` | `dspy.Module` with conversation state |
| `Agent` | `dspy.ReAct` |

**Example Migration**:

```python
# LlamaIndex
from llama_index import VectorStoreIndex, SimpleDirectoryReader

documents = SimpleDirectoryReader("data").load_data()
index = VectorStoreIndex.from_documents(documents)
query_engine = index.as_query_engine()
response = query_engine.query("What is the revenue?")

# DSPy
import dspy
from dspy.retrieve.chromadb_rm import ChromadbRM

# Setup retrieval
rm = ChromadbRM(collection_name="documents", k=5)
dspy.settings.configure(rm=rm)

class RAG(dspy.Module):
    def __init__(self):
        self.retrieve = dspy.Retrieve(k=5)
        self.generate = dspy.ChainOfThought("context, question -> answer")

    def forward(self, question):
        context = self.retrieve(question).passages
        return self.generate(context=context, question=question)

rag = RAG()
response = rag(question="What is the revenue?")
```

**Benefits of DSPy**:
- Optimizable retrieval (k, query rewriting)
- End-to-end optimization of RAG pipeline
- Cleaner abstraction
- Better for production (compiled programs)

### From Haystack

**Haystack Concepts → DSPy Equivalents**:

| Haystack | DSPy Equivalent |
|----------|-----------------|
| `Pipeline` | `dspy.Module` |
| `Retriever` | `dspy.Retrieve` |
| `Reader` | `dspy.ChainOfThought` |
| `PromptNode` | `dspy.Predict` |
| `Agent` | `dspy.ReAct` |

**Example Migration**:

```python
# Haystack
from haystack import Pipeline
from haystack.nodes import BM25Retriever, FARMReader

pipeline = Pipeline()
pipeline.add_node(BM25Retriever(document_store), name="Retriever", inputs=["Query"])
pipeline.add_node(FARMReader(model_name="model"), name="Reader", inputs=["Retriever"])

result = pipeline.run(query="What is AI?")

# DSPy
import dspy

class QA(dspy.Module):
    def __init__(self):
        self.retrieve = dspy.Retrieve(k=5)
        self.answer = dspy.ChainOfThought("context, question -> answer")

    def forward(self, question):
        context = self.retrieve(question).passages
        return self.answer(context=context, question=question)

qa = QA()
result = qa(question="What is AI?")
```

---

## Migration Strategies

### Incremental Migration

**Strategy**: Migrate one component at a time, run both systems in parallel.

**Steps**:
1. **Identify boundaries**: Find clean separation points (e.g., retrieval vs generation)
2. **Create adapters**: Build compatibility layer between old and new
3. **Migrate incrementally**: Replace one component per sprint
4. **Validate continuously**: Compare outputs at each step
5. **Decommission old system**: Once all components migrated

**Example Adapter**:
```python
# Adapter for gradual LangChain → DSPy migration
class DSPyAdapter:
    """Wrap DSPy module to look like LangChain chain."""

    def __init__(self, dspy_module):
        self.module = dspy_module

    def run(self, **kwargs):
        """LangChain-style interface."""
        result = self.module(**kwargs)
        return result.answer if hasattr(result, 'answer') else str(result)

    def __call__(self, inputs):
        """LangChain chain interface."""
        return self.run(**inputs)

# Use in existing LangChain pipeline
dspy_qa = QAModule()
adapter = DSPyAdapter(dspy_qa)

# Works with LangChain code
from langchain import SequentialChain
chain = SequentialChain(chains=[existing_chain, adapter])
```

### Big Bang Migration

**Strategy**: Rewrite entire system at once.

**When to use**:
- Small codebase (<1000 LOC)
- Clean slate opportunity
- Major version upgrade with breaking changes
- Tight deadline, can't afford gradual migration

**Steps**:
1. **Freeze old system**: No new features, only bug fixes
2. **Rewrite in DSPy**: Build from scratch using best practices
3. **Shadow run**: Run both systems in parallel, compare outputs
4. **Validate**: Extensive testing on production data
5. **Cutover**: Switch traffic to new system
6. **Monitor**: Watch for regressions

### Strangler Fig Pattern

**Strategy**: Gradually replace old system by routing traffic to new system.

**Steps**:
1. **Create routing layer**: Proxy that routes requests
2. **Migrate one endpoint**: Implement in DSPy
3. **Route subset of traffic**: 10% → 50% → 100%
4. **Validate**: Compare outputs, monitor metrics
5. **Repeat**: Migrate next endpoint
6. **Remove old system**: Once all traffic routed

**Example Router**:
```python
# Traffic router for gradual migration
class MigrationRouter:
    def __init__(self, old_system, new_system, rollout_percent=10):
        self.old = old_system
        self.new = new_system
        self.rollout = rollout_percent

    def route(self, request):
        """Route based on rollout percentage."""
        import random

        if random.randint(1, 100) <= self.rollout:
            # Route to new DSPy system
            try:
                return self.new(request), "new"
            except Exception as e:
                logger.error(f"New system failed: {e}")
                return self.old(request), "old_fallback"
        else:
            # Route to old system
            return self.old(request), "old"

# Usage
old_qa = LangChainQA()
new_qa = DSPyQA()
router = MigrationRouter(old_qa, new_qa, rollout_percent=10)

result, system = router.route(request)
log_metrics(system=system, latency=..., accuracy=...)
```

---

## Compatibility Matrix

### DSPy Version Compatibility

| DSPy Version | Python | LM Providers | Vector DBs | Status |
|--------------|--------|--------------|------------|--------|
| 3.0+ | 3.9+ | OpenAI, Anthropic, Cohere, Together, Anyscale, Ollama, vLLM | Chroma, Weaviate, Pinecone, Qdrant, Milvus | Current |
| 2.5 | 3.8+ | OpenAI, Anthropic, Cohere, Together | Chroma, Weaviate, Pinecone | Supported |
| 2.0 | 3.8+ | OpenAI, Cohere | Chroma, Weaviate | EOL 2025-06 |
| 1.x | 3.7+ | OpenAI | ColBERTv2 | EOL 2024-12 |

### LM Provider Compatibility

| Provider | DSPy 2.5 | DSPy 3.0 | Notes |
|----------|----------|----------|-------|
| OpenAI | ✅ | ✅ | Full support |
| Anthropic Claude | ✅ | ✅ | Full support |
| Cohere | ✅ | ✅ | Full support |
| Together AI | ✅ | ✅ | Full support |
| Anyscale | ⚠️ | ✅ | Limited in 2.5 |
| Ollama | ❌ | ✅ | Only 3.0+ |
| vLLM | ❌ | ✅ | Only 3.0+ |
| Azure OpenAI | ✅ | ✅ | Configure endpoint |

### Vector Database Compatibility

| Vector DB | DSPy 2.5 | DSPy 3.0 | Notes |
|-----------|----------|----------|-------|
| ChromaDB | ✅ | ✅ | Full support |
| Weaviate | ✅ | ✅ | Full support |
| Pinecone | ✅ | ✅ | Full support |
| Qdrant | ⚠️ | ✅ | Limited in 2.5 |
| Milvus | ❌ | ✅ | Only 3.0+ |
| FAISS | ✅ | ✅ | Local only |
| Elasticsearch | ❌ | ✅ | Only 3.0+ |

---

## Common Migration Issues

### Issue 1: Compiled Models Not Loading

**Problem**: Old compiled models fail to load in new DSPy version.

**Cause**: Serialization format changed.

**Solution**:
```python
# Re-compile models
from dspy.teleprompt import BootstrapFewShot

# Load old model's training data
with open("training_data.json") as f:
    trainset = [dspy.Example(**ex).with_inputs('question') for ex in json.load(f)]

# Re-optimize with new version
optimizer = BootstrapFewShot(metric=accuracy)
optimized = optimizer.compile(program, trainset=trainset)

# Save new version
optimized.save("model_v3.json")
```

### Issue 2: Performance Regression

**Problem**: New version slower or less accurate.

**Cause**: Optimizer improvements, different defaults.

**Solution**:
```python
# Tune hyperparameters
from dspy.teleprompt import MIPROv2

optimizer = MIPROv2(
    metric=accuracy,
    num_candidates=20,  # Increase from default 10
    init_temperature=1.0,
    verbose=True
)

optimized = optimizer.compile(
    program,
    trainset=train,
    max_bootstrapped_demos=4,  # Increase context
    max_labeled_demos=2
)

# A/B test: old vs new
evaluate_both(old_model, optimized, test_set)
```

### Issue 3: Deprecated API Usage

**Problem**: Warnings about deprecated APIs.

**Cause**: APIs evolve, old patterns discouraged.

**Solution**:
```bash
# Find all deprecation warnings
pytest -W default::DeprecationWarning 2>&1 | grep -i deprecated

# Run automated fixer (if available)
dspy-fix-deprecations --path src/

# Manually update based on migration guide
```

### Issue 4: Incompatible Dependencies

**Problem**: DSPy requires conflicting dependency versions.

**Cause**: Transitive dependency conflicts.

**Solution**:
```bash
# Check dependency tree
pip-tree

# Isolate DSPy environment
python -m venv venv-dspy-only
source venv-dspy-only/bin/activate
pip install dspy-ai

# Use dependency groups (pyproject.toml)
[project.optional-dependencies]
dspy = ["dspy-ai==3.0", "openai==1.0"]
legacy = ["langchain==0.1", "llama-index==0.9"]

# Install selectively
pip install -e ".[dspy]"
```

---

## Migration Testing Checklist

**Before declaring migration complete**:
- [ ] All unit tests passing (>80% coverage)
- [ ] All integration tests passing
- [ ] Evaluation metrics match or exceed baseline
- [ ] Latency within acceptable range (p95 < 2s)
- [ ] Cost per request acceptable
- [ ] No deprecation warnings
- [ ] Documentation updated
- [ ] Team trained on new patterns
- [ ] Monitoring dashboards updated
- [ ] Rollback procedure tested
- [ ] Production traffic validated (shadow run)
- [ ] Post-migration retrospective scheduled

---

**Version**: 1.0
**Last Updated**: 2025-10-30
