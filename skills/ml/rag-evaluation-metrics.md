---
name: ml-rag-evaluation-metrics
description: Comprehensive guide to RAG evaluation using RAGAS (Faithfulness, Answer Relevancy, Context Precision/Recall), LLM-as-judge patterns, synthetic datasets, and integration with Arize Phoenix and Langfuse
---

# RAG Evaluation Metrics

Last Updated: 2025-10-26

## When to Use This Skill

Use RAG evaluation metrics when:
- **Building RAG systems**: Evaluating retrieval-augmented generation pipelines
- **Optimizing retrieval**: Tuning chunk size, embedding models, or retrieval strategies
- **Measuring generation quality**: Assessing answer faithfulness and relevance
- **A/B testing**: Comparing different RAG configurations or models
- **Production monitoring**: Tracking RAG performance in deployed applications
- **Synthetic data evaluation**: Testing with generated question-answer pairs
- **End-to-end RAG**: Evaluating both retrieval and generation components
- **Context window optimization**: Determining optimal number of retrieved chunks

**Anti-pattern**: Evaluating RAG systems with only generation metrics. Always assess **both** retrieval quality and answer quality.

## Core Concepts

### RAGAS Framework (2024-2025)

**RAGAS** (Retrieval Augmented Generation Assessment) provides specialized metrics for RAG evaluation:

**Generation Metrics**:
1. **Faithfulness**: Whether the answer is grounded in retrieved context (hallucination detection)
2. **Answer Relevancy**: How relevant the answer is to the query

**Retrieval Metrics**:
3. **Context Precision**: Proportion of relevant chunks in retrieved context
4. **Context Recall**: Whether all necessary information is retrieved

**End-to-End Metrics**:
5. **Answer Correctness**: Similarity between generated answer and ground truth
6. **Answer Semantic Similarity**: Semantic alignment with expected answer

### RAG Evaluation Dimensions

```
Query → Retrieval → Generation → Answer
  ↓         ↓           ↓          ↓
Eval:   Context     Faithfulness  Relevancy
        Precision   (no halluc.)  (on-topic)
        Recall
```

### LLM-as-Judge for RAG

RAG evaluation heavily uses LLM-as-judge patterns:
- **Faithfulness**: Judge checks if answer claims are supported by context
- **Relevancy**: Judge assesses if answer addresses the query
- **Context Ranking**: Judge evaluates which chunks are most relevant

### Synthetic Dataset Generation

**Problem**: Real-world RAG datasets with ground truth are scarce

**Solution**: Generate synthetic question-answer pairs from documents
- Extract key information from chunks
- Generate questions that require that information
- Create ground truth answers
- Evaluate RAG system on synthetic dataset

## Implementation Patterns

### Pattern 1: RAGAS Basic Evaluation

**When to use**: Standard RAG evaluation with all metrics

```python
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
    answer_correctness,
)
from datasets import Dataset

# Prepare evaluation dataset
eval_data = {
    "question": [
        "What is the capital of France?",
        "Who wrote Romeo and Juliet?",
    ],
    "contexts": [
        # Retrieved contexts (list of chunks)
        [
            "Paris is the capital and largest city of France.",
            "France is a country in Western Europe.",
        ],
        [
            "William Shakespeare wrote Romeo and Juliet in the 1590s.",
            "Romeo and Juliet is a tragedy about two young lovers.",
        ],
    ],
    "answer": [
        # Generated answers
        "The capital of France is Paris.",
        "Romeo and Juliet was written by William Shakespeare.",
    ],
    "ground_truth": [
        # Reference answers (optional, for answer_correctness)
        "Paris",
        "William Shakespeare",
    ],
}

# Create dataset
dataset = Dataset.from_dict(eval_data)

# Run evaluation
results = evaluate(
    dataset,
    metrics=[
        faithfulness,
        answer_relevancy,
        context_precision,
        context_recall,
        answer_correctness,
    ],
)

# View results
print(results)
print(f"Faithfulness: {results['faithfulness']:.4f}")
print(f"Answer Relevancy: {results['answer_relevancy']:.4f}")
print(f"Context Precision: {results['context_precision']:.4f}")
print(f"Context Recall: {results['context_recall']:.4f}")
print(f"Answer Correctness: {results['answer_correctness']:.4f}")

# Export results
results_df = results.to_pandas()
results_df.to_csv("ragas_results.csv", index=False)
```

**Interpreting scores** (0.0 to 1.0 scale):
- **Faithfulness < 0.7**: High hallucination risk, review generation prompts
- **Answer Relevancy < 0.7**: Answers not addressing questions, review system prompt
- **Context Precision < 0.5**: Too many irrelevant chunks, improve retrieval
- **Context Recall < 0.7**: Missing information, retrieve more chunks or improve embeddings

### Pattern 2: Custom RAGAS Metrics

**When to use**: Domain-specific RAG evaluation needs

```python
from ragas.metrics.base import Metric
from ragas.metrics._faithfulness import FaithfulnesswithHHEM
from langchain_openai import ChatOpenAI

# Custom metric: Code Correctness for code RAG
class CodeCorrectness(Metric):
    """Evaluate whether code answer is correct and executable."""

    def __init__(self, llm=None):
        self.llm = llm or ChatOpenAI(model="gpt-4-turbo-preview")

    def score(self, row):
        """
        Score code correctness.

        Args:
            row: Dict with 'question', 'answer', 'contexts', 'ground_truth'

        Returns:
            Score from 0.0 to 1.0
        """
        question = row["question"]
        code_answer = row["answer"]
        context = "\n".join(row["contexts"])

        prompt = f"""Evaluate the correctness of the following code answer.

Question: {question}

Context: {context}

Code Answer:
{code_answer}

Rate the code on:
1. Syntactic correctness (no errors)
2. Logical correctness (solves the problem)
3. Best practices (follows conventions)

Provide a score from 0.0 to 1.0, where:
- 0.0 = Completely incorrect or won't run
- 0.5 = Partially correct but has issues
- 1.0 = Perfect solution

Return ONLY a number between 0.0 and 1.0.
"""

        response = self.llm.invoke(prompt)
        score_text = response.content.strip()

        try:
            score = float(score_text)
            return max(0.0, min(1.0, score))  # Clamp to [0, 1]
        except ValueError:
            # Fallback if LLM doesn't return a number
            return 0.5

# Custom metric: Medical Accuracy
class MedicalAccuracy(Metric):
    """Evaluate medical accuracy with safety checks."""

    def __init__(self, llm=None):
        self.llm = llm or ChatOpenAI(model="gpt-4-turbo-preview")

    def score(self, row):
        """Score medical accuracy and safety."""
        question = row["question"]
        answer = row["answer"]
        context = "\n".join(row["contexts"])

        prompt = f"""You are a medical expert evaluator. Assess the following medical answer.

Question: {question}

Retrieved Medical Context:
{context}

Answer:
{answer}

Evaluate on:
1. Medical accuracy (based on context)
2. Safety (no harmful advice)
3. Appropriate disclaimers (mentions consulting doctor if needed)

Score from 0.0 to 1.0:
- 0.0 = Medically incorrect or dangerous
- 0.5 = Partially correct but incomplete or lacks safety disclaimers
- 1.0 = Medically accurate, safe, and appropriately cautious

Return ONLY a number between 0.0 and 1.0.
"""

        response = self.llm.invoke(prompt)

        try:
            score = float(response.content.strip())
            return max(0.0, min(1.0, score))
        except ValueError:
            return 0.5

# Use custom metrics
from ragas import evaluate

custom_results = evaluate(
    dataset,
    metrics=[
        faithfulness,
        answer_relevancy,
        CodeCorrectness(),  # Custom metric
    ],
)

print(f"Code Correctness: {custom_results['code_correctness']:.4f}")
```

### Pattern 3: Synthetic Dataset Generation

**When to use**: Creating test datasets from documents

```python
from ragas.testset.generator import TestsetGenerator
from ragas.testset.evolutions import simple, reasoning, multi_context
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Load documents
loader = DirectoryLoader("./docs", glob="**/*.txt", loader_cls=TextLoader)
documents = loader.load()

# Split into chunks
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
)
chunks = text_splitter.split_documents(documents)

# Setup generator
generator = TestsetGenerator.from_langchain(
    generator_llm=ChatOpenAI(model="gpt-4-turbo-preview"),
    critic_llm=ChatOpenAI(model="gpt-4-turbo-preview"),
    embeddings=OpenAIEmbeddings(),
)

# Generate test dataset
testset = generator.generate_with_langchain_docs(
    documents=chunks,
    test_size=50,  # Generate 50 question-answer pairs
    distributions={
        simple: 0.5,         # 50% simple questions
        reasoning: 0.25,     # 25% reasoning questions
        multi_context: 0.25, # 25% questions requiring multiple chunks
    },
)

# Convert to evaluation format
testset_df = testset.to_pandas()

print(f"Generated {len(testset_df)} test cases")
print(testset_df.head())

# Save for later use
testset_df.to_csv("synthetic_testset.csv", index=False)

# Use for evaluation
from datasets import Dataset

eval_dataset = Dataset.from_pandas(testset_df)

# Now evaluate your RAG system on synthetic data
def run_rag(question):
    """Your RAG system."""
    # Retrieve contexts
    contexts = retriever.get_relevant_documents(question)

    # Generate answer
    answer = generator.generate(question, contexts)

    return {
        "question": question,
        "contexts": [c.page_content for c in contexts],
        "answer": answer,
    }

# Generate answers for synthetic questions
eval_results = []

for example in testset_df.itertuples():
    rag_output = run_rag(example.question)
    rag_output["ground_truth"] = example.ground_truth

    eval_results.append(rag_output)

# Evaluate
eval_dataset = Dataset.from_list(eval_results)
results = evaluate(
    eval_dataset,
    metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
)

print(results)
```

### Pattern 4: Arize Phoenix Integration

**When to use**: Production RAG monitoring with tracing

```python
import phoenix as px
from phoenix.trace.langchain import LangChainInstrumentor
from phoenix.evals import (
    HallucinationEvaluator,
    RelevanceEvaluator,
    OpenAIModel,
)
from langchain_openai import ChatOpenAI
from langchain.chains import RetrievalQA
from langchain_community.vectorstores import Chroma

# Start Phoenix
session = px.launch_app()

# Instrument LangChain
LangChainInstrumentor().instrument()

# Build RAG system (automatically traced)
vectorstore = Chroma.from_documents(documents, OpenAIEmbeddings())
retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

qa_chain = RetrievalQA.from_chain_type(
    llm=ChatOpenAI(model="gpt-4-turbo-preview"),
    chain_type="stuff",
    retriever=retriever,
    return_source_documents=True,
)

# Run queries (automatically traced)
questions = [
    "What is the capital of France?",
    "Who wrote Romeo and Juliet?",
    # ... more questions
]

for question in questions:
    result = qa_chain({"query": question})
    print(f"Q: {question}")
    print(f"A: {result['result']}\n")

# Get traces from Phoenix
traces_df = px.Client().get_trace_dataset()

# Run Phoenix evaluations
eval_model = OpenAIModel(model="gpt-4-turbo-preview")

# Hallucination evaluation (Faithfulness)
hallucination_eval = HallucinationEvaluator(eval_model)
hallucination_results = hallucination_eval.evaluate(
    dataframe=traces_df,
    query_column="input",
    response_column="output",
    reference_column="retrieved_context",
)

# Relevance evaluation (Answer Relevancy)
relevance_eval = RelevanceEvaluator(eval_model)
relevance_results = relevance_eval.evaluate(
    dataframe=traces_df,
    query_column="input",
    document_column="retrieved_context",
)

# Add scores to traces
traces_df["hallucination_score"] = hallucination_results["label"]
traces_df["relevance_score"] = relevance_results["label"]

# Calculate metrics
hallucination_rate = (hallucination_results["label"] == "hallucinated").sum() / len(traces_df)
relevance_rate = (relevance_results["label"] == "relevant").sum() / len(traces_df)

print(f"Hallucination rate: {hallucination_rate:.2%}")
print(f"Relevance rate: {relevance_rate:.2%}")

# Upload results back to Phoenix
px.Client().log_evaluations(traces_df)

print(f"View results at {session.url}")
```

### Pattern 5: End-to-End RAG Pipeline Evaluation

**When to use**: Comprehensive evaluation across RAG components

```python
from typing import List, Dict, Tuple
import numpy as np
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)
from datasets import Dataset

class RAGEvaluationPipeline:
    """Comprehensive RAG evaluation pipeline."""

    def __init__(self, rag_system, test_dataset: List[Dict]):
        """
        Args:
            rag_system: Your RAG system with query(question) -> (answer, contexts)
            test_dataset: List of {question, ground_truth} dicts
        """
        self.rag_system = rag_system
        self.test_dataset = test_dataset

    def run_rag_on_dataset(self) -> List[Dict]:
        """Run RAG system on all test questions."""
        results = []

        for example in self.test_dataset:
            question = example["question"]

            # Run RAG
            answer, contexts = self.rag_system.query(question)

            results.append({
                "question": question,
                "answer": answer,
                "contexts": [c.page_content for c in contexts],
                "ground_truth": example["ground_truth"],
            })

        return results

    def evaluate_retrieval(self, results: List[Dict]) -> Dict:
        """Evaluate retrieval quality."""
        # Context Precision: proportion of retrieved chunks that are relevant
        # Context Recall: whether all needed info is retrieved

        dataset = Dataset.from_list(results)

        retrieval_metrics = evaluate(
            dataset,
            metrics=[context_precision, context_recall],
        )

        return {
            "context_precision": retrieval_metrics["context_precision"],
            "context_recall": retrieval_metrics["context_recall"],
        }

    def evaluate_generation(self, results: List[Dict]) -> Dict:
        """Evaluate generation quality."""
        # Faithfulness: answer grounded in context
        # Answer Relevancy: answer addresses question

        dataset = Dataset.from_list(results)

        generation_metrics = evaluate(
            dataset,
            metrics=[faithfulness, answer_relevancy],
        )

        return {
            "faithfulness": generation_metrics["faithfulness"],
            "answer_relevancy": generation_metrics["answer_relevancy"],
        }

    def evaluate_end_to_end(self, results: List[Dict]) -> Dict:
        """Full RAG evaluation."""
        dataset = Dataset.from_list(results)

        all_metrics = evaluate(
            dataset,
            metrics=[
                faithfulness,
                answer_relevancy,
                context_precision,
                context_recall,
            ],
        )

        return {
            "faithfulness": all_metrics["faithfulness"],
            "answer_relevancy": all_metrics["answer_relevancy"],
            "context_precision": all_metrics["context_precision"],
            "context_recall": all_metrics["context_recall"],
        }

    def analyze_failures(self, results: List[Dict], threshold: float = 0.7):
        """Identify and analyze failure cases."""
        # Run detailed evaluation per example
        failures = {
            "low_faithfulness": [],
            "low_relevancy": [],
            "low_context_precision": [],
            "low_context_recall": [],
        }

        dataset = Dataset.from_list(results)

        # Get per-example scores
        detailed_results = evaluate(
            dataset,
            metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        )

        df = detailed_results.to_pandas()

        # Identify failures
        for idx, row in df.iterrows():
            example = results[idx]

            if row["faithfulness"] < threshold:
                failures["low_faithfulness"].append({
                    "question": example["question"],
                    "answer": example["answer"],
                    "contexts": example["contexts"],
                    "score": row["faithfulness"],
                })

            if row["answer_relevancy"] < threshold:
                failures["low_relevancy"].append({
                    "question": example["question"],
                    "answer": example["answer"],
                    "score": row["answer_relevancy"],
                })

            if row["context_precision"] < 0.5:  # Lower threshold
                failures["low_context_precision"].append({
                    "question": example["question"],
                    "contexts": example["contexts"],
                    "score": row["context_precision"],
                })

            if row["context_recall"] < threshold:
                failures["low_context_recall"].append({
                    "question": example["question"],
                    "contexts": example["contexts"],
                    "ground_truth": example["ground_truth"],
                    "score": row["context_recall"],
                })

        return failures

    def run_full_evaluation(self) -> Dict:
        """Run complete evaluation pipeline."""
        print("Running RAG system on test dataset...")
        results = self.run_rag_on_dataset()

        print("Evaluating retrieval...")
        retrieval_metrics = self.evaluate_retrieval(results)

        print("Evaluating generation...")
        generation_metrics = self.evaluate_generation(results)

        print("Evaluating end-to-end...")
        e2e_metrics = self.evaluate_end_to_end(results)

        print("Analyzing failures...")
        failures = self.analyze_failures(results)

        # Compile report
        report = {
            "overall_metrics": e2e_metrics,
            "retrieval_metrics": retrieval_metrics,
            "generation_metrics": generation_metrics,
            "failure_analysis": {
                "num_low_faithfulness": len(failures["low_faithfulness"]),
                "num_low_relevancy": len(failures["low_relevancy"]),
                "num_low_context_precision": len(failures["low_context_precision"]),
                "num_low_context_recall": len(failures["low_context_recall"]),
            },
            "sample_failures": {
                k: v[:3] for k, v in failures.items()  # Top 3 per category
            },
        }

        return report

# Usage
class MyRAGSystem:
    """Your RAG system."""

    def query(self, question: str) -> Tuple[str, List]:
        """Return (answer, contexts)."""
        # Your RAG implementation
        pass

test_dataset = [
    {"question": "What is photosynthesis?", "ground_truth": "Photosynthesis is..."},
    # ... more examples
]

pipeline = RAGEvaluationPipeline(
    rag_system=MyRAGSystem(),
    test_dataset=test_dataset,
)

report = pipeline.run_full_evaluation()

print("\n=== RAG Evaluation Report ===")
print(f"Faithfulness: {report['overall_metrics']['faithfulness']:.4f}")
print(f"Answer Relevancy: {report['overall_metrics']['answer_relevancy']:.4f}")
print(f"Context Precision: {report['overall_metrics']['context_precision']:.4f}")
print(f"Context Recall: {report['overall_metrics']['context_recall']:.4f}")

print(f"\nFailure counts:")
for metric, count in report["failure_analysis"].items():
    print(f"  {metric}: {count}")
```

## Code Examples

### Example 1: Comparing RAG Configurations

```python
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision
from datasets import Dataset
import pandas as pd

class RAGComparison:
    """Compare different RAG configurations."""

    def __init__(self, test_questions: List[str], ground_truths: List[str]):
        self.test_questions = test_questions
        self.ground_truths = ground_truths

    def evaluate_configuration(
        self,
        config_name: str,
        rag_system,
    ) -> pd.DataFrame:
        """Evaluate single RAG configuration."""
        results = []

        for question, ground_truth in zip(self.test_questions, self.ground_truths):
            answer, contexts = rag_system.query(question)

            results.append({
                "question": question,
                "answer": answer,
                "contexts": [c.page_content for c in contexts],
                "ground_truth": ground_truth,
            })

        dataset = Dataset.from_list(results)

        metrics = evaluate(
            dataset,
            metrics=[faithfulness, answer_relevancy, context_precision],
        )

        return pd.DataFrame({
            "config": config_name,
            "faithfulness": [metrics["faithfulness"]],
            "answer_relevancy": [metrics["answer_relevancy"]],
            "context_precision": [metrics["context_precision"]],
        })

    def compare_configurations(
        self,
        configurations: Dict[str, object],
    ) -> pd.DataFrame:
        """
        Compare multiple RAG configurations.

        Args:
            configurations: {config_name: rag_system} dict

        Returns:
            Comparison dataframe
        """
        results = []

        for config_name, rag_system in configurations.items():
            print(f"Evaluating: {config_name}")

            config_results = self.evaluate_configuration(config_name, rag_system)
            results.append(config_results)

        comparison_df = pd.concat(results, ignore_index=True)

        # Add ranking
        comparison_df["avg_score"] = comparison_df[
            ["faithfulness", "answer_relevancy", "context_precision"]
        ].mean(axis=1)

        comparison_df = comparison_df.sort_values("avg_score", ascending=False)

        return comparison_df

# Usage
test_questions = [
    "What is machine learning?",
    "How does a neural network work?",
    # ... more
]

ground_truths = [
    "Machine learning is...",
    "Neural networks are...",
    # ... more
]

comparator = RAGComparison(test_questions, ground_truths)

# Different RAG configurations to compare
configurations = {
    "base_rag": BaseRAGSystem(),
    "hybrid_search": HybridSearchRAG(),  # BM25 + vector
    "rerank": RerankRAG(),               # With reranker
    "large_chunks": LargeChunkRAG(),     # 1500 tokens
    "small_chunks": SmallChunkRAG(),     # 500 tokens
}

comparison = comparator.compare_configurations(configurations)

print("\n=== RAG Configuration Comparison ===")
print(comparison.to_string(index=False))

# Save results
comparison.to_csv("rag_comparison.csv", index=False)
```

### Example 2: Continuous RAG Monitoring

```python
import phoenix as px
from phoenix.trace.langchain import LangChainInstrumentor
from phoenix.evals import HallucinationEvaluator, OpenAIModel
from datetime import datetime, timedelta
import pandas as pd

class RAGMonitor:
    """Continuous monitoring for production RAG systems."""

    def __init__(self, phoenix_endpoint: str = "http://localhost:6006"):
        self.px_client = px.Client(endpoint=phoenix_endpoint)
        self.eval_model = OpenAIModel(model="gpt-4-turbo-preview")
        self.hallucination_eval = HallucinationEvaluator(self.eval_model)

    def get_recent_traces(self, hours: int = 24) -> pd.DataFrame:
        """Get RAG traces from last N hours."""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)

        traces = self.px_client.get_trace_dataset(
            start_time=start_time,
            end_time=end_time,
        )

        return traces

    def evaluate_recent_performance(self, hours: int = 24) -> Dict:
        """Evaluate RAG performance from recent traces."""
        traces = self.get_recent_traces(hours)

        if len(traces) == 0:
            return {"error": "No traces found"}

        # Run hallucination evaluation
        hallucination_results = self.hallucination_eval.evaluate(
            dataframe=traces,
            query_column="input",
            response_column="output",
            reference_column="retrieved_context",
        )

        # Calculate metrics
        hallucination_rate = (
            (hallucination_results["label"] == "hallucinated").sum() / len(traces)
        )

        # Identify problematic queries
        traces["hallucination"] = hallucination_results["label"]
        hallucinated_queries = traces[traces["hallucination"] == "hallucinated"]

        return {
            "period_hours": hours,
            "total_queries": len(traces),
            "hallucination_rate": hallucination_rate,
            "num_hallucinations": len(hallucinated_queries),
            "sample_hallucinations": hallucinated_queries.head(5).to_dict("records"),
        }

    def alert_on_degradation(
        self,
        threshold_hallucination: float = 0.1,
        hours: int = 1,
    ) -> bool:
        """Alert if performance degrades beyond threshold."""
        metrics = self.evaluate_recent_performance(hours)

        if metrics.get("hallucination_rate", 0) > threshold_hallucination:
            print(f"ALERT: Hallucination rate {metrics['hallucination_rate']:.2%} exceeds threshold {threshold_hallucination:.2%}")
            print(f"Sample hallucinations:")
            for sample in metrics["sample_hallucinations"]:
                print(f"  Query: {sample['input']}")
                print(f"  Answer: {sample['output']}\n")

            return True

        return False

# Usage (run periodically)
monitor = RAGMonitor()

# Check every hour
metrics = monitor.evaluate_recent_performance(hours=1)
print(f"Last hour performance:")
print(f"  Total queries: {metrics['total_queries']}")
print(f"  Hallucination rate: {metrics['hallucination_rate']:.2%}")

# Alert if degraded
monitor.alert_on_degradation(threshold_hallucination=0.1)
```

## Anti-Patterns

### Anti-Pattern 1: Only Evaluating Generation
**Wrong**: Ignoring retrieval quality
```python
# BAD: Only measure answer quality
results = evaluate(dataset, metrics=[answer_relevancy])
# Misses retrieval failures!
```

**Right**: Evaluate both retrieval and generation
```python
# GOOD: Measure both components
results = evaluate(
    dataset,
    metrics=[
        context_precision,  # Retrieval
        context_recall,     # Retrieval
        faithfulness,       # Generation
        answer_relevancy,   # Generation
    ],
)
```

### Anti-Pattern 2: No Synthetic Data
**Wrong**: Waiting for labeled data
```python
# BAD: Can't evaluate without manual labels
# Wait months for human annotations...
```

**Right**: Generate synthetic datasets
```python
# GOOD: Generate test data from documents
testset = generator.generate_with_langchain_docs(
    documents=chunks,
    test_size=100,
)
# Evaluate immediately!
```

### Anti-Pattern 3: Ignoring Context Window
**Wrong**: Always retrieving fixed number of chunks
```python
# BAD: Always retrieve 10 chunks
retriever = vectorstore.as_retriever(k=10)
# May exceed context window or waste tokens
```

**Right**: Optimize based on context precision/recall
```python
# GOOD: Experiment with different k values
for k in [3, 5, 7, 10]:
    retriever = vectorstore.as_retriever(k=k)
    # Evaluate context precision vs recall
    # Find optimal k that balances both
```

## Related Skills

- `llm-benchmarks-evaluation.md`: Standard benchmarks for LLM capabilities
- `llm-evaluation-frameworks.md`: Arize Phoenix, Braintrust for production monitoring
- `llm-as-judge.md`: LLM-as-judge patterns used in RAGAS metrics
- `custom-llm-evaluation.md`: Domain-specific RAG evaluation metrics
- `dspy-evaluation.md`: DSPy evaluation for RAG optimization

## Summary

RAG evaluation requires specialized metrics for both retrieval and generation:

**Key Takeaways**:
1. **RAGAS metrics**: Faithfulness (hallucination), Answer Relevancy, Context Precision/Recall
2. **LLM-as-judge**: Core technique for evaluating semantic quality in RAG
3. **Synthetic datasets**: Generate test data from documents when labels unavailable
4. **Production monitoring**: Integrate with Phoenix/Langfuse for continuous evaluation
5. **Component-level**: Always evaluate retrieval AND generation separately

**RAGAS Metrics Summary**:
- **Faithfulness**: Answer grounded in retrieved context (no hallucination)
- **Answer Relevancy**: Answer addresses the query
- **Context Precision**: Retrieved chunks are relevant (low noise)
- **Context Recall**: All needed information is retrieved (no gaps)

**Best Practices**:
- Use synthetic data generation for rapid testing
- Monitor both retrieval and generation quality
- Optimize chunk size and retrieval count based on metrics
- Set up continuous monitoring for production RAG systems
- Combine RAGAS with domain-specific metrics for comprehensive evaluation

**When to combine with other skills**:
- Use `llm-as-judge.md` for custom RAG quality criteria
- Use `llm-evaluation-frameworks.md` for Phoenix/Langfuse integration
- Use `custom-llm-evaluation.md` for domain-specific RAG metrics
- Use `dspy-evaluation.md` when using DSPy for RAG optimization
