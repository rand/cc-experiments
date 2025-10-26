---
name: ml-llm-benchmarks-evaluation
description: Comprehensive guide to evaluating LLMs using standard benchmarks including MMLU, HellaSwag, BBH, HumanEval, TruthfulQA, and GSM8K, with practical implementation using LightEval and lm-evaluation-harness
---

# LLM Benchmarks Evaluation

Last Updated: 2025-10-26

## When to Use This Skill

Use LLM benchmark evaluation when:
- **Comparing model capabilities**: Measuring performance across different LLMs or model versions
- **Tracking training progress**: Monitoring improvements during fine-tuning or continued pre-training
- **Validating model releases**: Ensuring models meet minimum quality thresholds before deployment
- **Research validation**: Reproducing published results or establishing baselines
- **Domain transfer**: Assessing model performance on new tasks or domains
- **Resource optimization**: Determining if a smaller/faster model meets accuracy requirements
- **Detecting contamination**: Identifying potential training data leakage in benchmarks

**Anti-pattern**: Using benchmarks as the **only** evaluation metric. Always complement with domain-specific tests, human evaluation, and production metrics.

## Core Concepts

### Standard Benchmark Categories

**1. Knowledge & Reasoning**
- **MMLU** (Massive Multitask Language Understanding): 57 subjects across STEM, humanities, social sciences
- **BBH** (BIG-Bench Hard): 23 challenging tasks from BIG-Bench that require multi-step reasoning
- **TruthfulQA**: 817 questions testing model truthfulness and resistance to falsehoods

**2. Code Generation**
- **HumanEval**: 164 Python programming problems with test cases
- **MBPP** (Mostly Basic Python Problems): 974 entry-level programming tasks
- **CodeContests**: Competitive programming problems requiring algorithmic reasoning

**3. Math Reasoning**
- **GSM8K**: 8,500 grade school math word problems
- **MATH**: 12,500 challenging competition mathematics problems
- **MathQA**: Math word problems with multiple-choice answers

**4. Common Sense & NLU**
- **HellaSwag**: Commonsense inference about physical situations
- **PIQA** (Physical Interaction QA): Physical commonsense reasoning
- **WinoGrande**: Winograd schema challenge for pronoun resolution
- **ARC** (AI2 Reasoning Challenge): Science questions for grade school students

**5. Safety & Alignment**
- **ToxiGen**: Detecting implicit toxicity and hate speech
- **BBQ** (Bias Benchmark for QA): Measuring social biases
- **BOLD**: Measuring biases in open-ended language generation

### Evaluation Frameworks

**lm-evaluation-harness** (EleutherAI):
- Unified framework for 200+ tasks
- Standardized prompting and scoring
- Reproducible evaluation pipeline
- Supports HuggingFace models, OpenAI API, Anthropic, etc.

**LightEval** (HuggingFace):
- Lightweight, fast evaluation framework
- Easy integration with HuggingFace Hub
- Custom task creation
- Efficient multi-GPU evaluation

### Key Metrics

**Accuracy**: Percentage of correct answers (most common)
**Exact Match (EM)**: Exact string match for generation tasks
**Pass@k**: Percentage of problems solved with k samples (code generation)
**F1 Score**: Harmonic mean of precision and recall (span-based tasks)
**BLEU/ROUGE**: N-gram overlap for generation (less common in modern evals)
**Normalized Accuracy**: Accounting for random guessing baseline

## Implementation Patterns

### Pattern 1: lm-evaluation-harness Setup

**When to use**: Industry-standard benchmark evaluation with reproducibility

```bash
# Installation
pip install lm-eval

# Basic evaluation (HuggingFace model)
lm_eval --model hf \
    --model_args pretrained=meta-llama/Llama-2-7b-hf \
    --tasks mmlu,hellaswag,truthfulqa_mc2 \
    --device cuda:0 \
    --batch_size 8

# Multiple tasks with custom settings
lm_eval --model hf \
    --model_args pretrained=mistralai/Mistral-7B-v0.1,dtype=bfloat16 \
    --tasks mmlu,arc_challenge,hellaswag,gsm8k,humaneval \
    --num_fewshot 5 \
    --device cuda:0 \
    --batch_size auto \
    --output_path results/mistral-7b-eval.json

# OpenAI API models
lm_eval --model openai-completions \
    --model_args model=gpt-4-turbo-preview \
    --tasks mmlu,truthfulqa_mc2 \
    --output_path results/gpt4-eval.json

# Anthropic Claude
lm_eval --model anthropic \
    --model_args model=claude-3-opus-20240229 \
    --tasks mmlu,truthfulqa_mc2
```

**Python API usage**:

```python
from lm_eval import evaluator, tasks
from lm_eval.models.huggingface import HFLM

# Initialize model
model = HFLM(pretrained="meta-llama/Llama-2-7b-hf", device="cuda:0")

# Run evaluation
results = evaluator.simple_evaluate(
    model=model,
    tasks=["mmlu", "hellaswag", "truthfulqa_mc2", "gsm8k"],
    num_fewshot=5,
    batch_size=8,
    device="cuda:0",
)

# Access results
print(f"MMLU Accuracy: {results['results']['mmlu']['acc']:.4f}")
print(f"HellaSwag Accuracy: {results['results']['hellaswag']['acc_norm']:.4f}")
print(f"TruthfulQA MC2: {results['results']['truthfulqa_mc2']['acc']:.4f}")
print(f"GSM8K: {results['results']['gsm8k']['exact_match']:.4f}")

# Save results
import json
with open("eval_results.json", "w") as f:
    json.dump(results, f, indent=2)
```

### Pattern 2: LightEval Framework

**When to use**: Fast evaluation with HuggingFace integration

```python
from lighteval.tasks.lighteval_task import LightevalTaskConfig
from lighteval.models.model_loader import load_model
from lighteval.main_lighteval import main_evaluate

# Define evaluation config
tasks = [
    "mmlu:all",
    "hellaswag",
    "arc:challenge",
    "truthfulqa:mc2",
    "gsm8k",
]

# Load model
model_config = {
    "model_name": "meta-llama/Llama-2-7b-hf",
    "dtype": "bfloat16",
    "device_map": "auto",
}

# Run evaluation
results = main_evaluate(
    model_config=model_config,
    tasks=tasks,
    batch_size=8,
    num_fewshot=5,
    output_dir="lighteval_results",
    save_details=True,
)

# Results structure
for task_name, task_results in results.items():
    print(f"{task_name}: {task_results['acc']:.4f}")
```

### Pattern 3: Custom Task Creation

**When to use**: Evaluating on domain-specific or custom benchmarks

```python
# lm-evaluation-harness custom task
from lm_eval.api.task import Task
from lm_eval.api.instance import Instance

class CustomMedicalQA(Task):
    VERSION = 0
    DATASET_PATH = "custom/medical_qa"
    DATASET_NAME = None

    def has_training_docs(self):
        return True

    def has_validation_docs(self):
        return True

    def has_test_docs(self):
        return True

    def training_docs(self):
        return self.dataset["train"]

    def validation_docs(self):
        return self.dataset["validation"]

    def test_docs(self):
        return self.dataset["test"]

    def doc_to_text(self, doc):
        # Format prompt
        return f"Question: {doc['question']}\nAnswer:"

    def doc_to_target(self, doc):
        # Correct answer
        return doc["answer"]

    def construct_requests(self, doc, ctx):
        # Create evaluation request
        ll, is_greedy = self.get_request_type()
        return Instance(
            request_type=ll,
            doc=doc,
            arguments=(ctx, {"until": ["\n"]}),
            idx=0,
        )

    def process_results(self, doc, results):
        # Score the result
        gold = self.doc_to_target(doc)
        pred = results[0].strip()

        return {
            "acc": int(pred.lower() == gold.lower()),
            "exact_match": int(pred == gold),
        }

    def aggregation(self):
        return {
            "acc": mean,
            "exact_match": mean,
        }

    def higher_is_better(self):
        return {
            "acc": True,
            "exact_match": True,
        }

# Register and use
from lm_eval.tasks import TaskManager
task_manager = TaskManager()
task_manager.register_task("custom_medical_qa", CustomMedicalQA)

# Evaluate
results = evaluator.simple_evaluate(
    model=model,
    tasks=["custom_medical_qa"],
    num_fewshot=3,
)
```

### Pattern 4: HumanEval Code Generation

**When to use**: Evaluating code generation capabilities

```python
from human_eval.data import write_jsonl, read_problems
from human_eval.evaluation import evaluate_functional_correctness

# Generate completions
def generate_one_completion(prompt, model, tokenizer):
    """Generate a single completion for a code prompt."""
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

    outputs = model.generate(
        **inputs,
        max_new_tokens=512,
        temperature=0.2,
        top_p=0.95,
        do_sample=True,
        stop_sequences=["```", "\nclass", "\ndef", "\nif __name__"],
    )

    completion = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return completion[len(prompt):]

# Evaluate on HumanEval
problems = read_problems()
samples = []

for task_id, problem in problems.items():
    prompt = problem["prompt"]

    # Generate multiple samples (pass@k)
    for _ in range(10):  # Generate 10 samples for pass@10
        completion = generate_one_completion(prompt, model, tokenizer)

        samples.append({
            "task_id": task_id,
            "completion": completion,
        })

# Write samples
write_jsonl("samples.jsonl", samples)

# Evaluate correctness
results = evaluate_functional_correctness(
    sample_file="samples.jsonl",
    k=[1, 10, 100],  # pass@1, pass@10, pass@100
    n_workers=4,
    timeout=3.0,
)

print(f"Pass@1: {results['pass@1']:.4f}")
print(f"Pass@10: {results['pass@10']:.4f}")
```

### Pattern 5: GSM8K Math Evaluation

**When to use**: Evaluating mathematical reasoning with chain-of-thought

```python
from datasets import load_dataset

# Load GSM8K
dataset = load_dataset("gsm8k", "main")

def extract_answer(text):
    """Extract numerical answer from GSM8K format."""
    # GSM8K answers are in format "#### 42"
    if "####" in text:
        return text.split("####")[1].strip()

    # Extract last number if no ####
    import re
    numbers = re.findall(r"-?\d+\.?\d*", text)
    return numbers[-1] if numbers else ""

def evaluate_gsm8k(model, tokenizer, num_samples=100):
    """Evaluate model on GSM8K with chain-of-thought prompting."""

    # Chain-of-thought prompt
    few_shot_examples = """
Q: There are 15 trees in the grove. Grove workers will plant trees in the grove today. After they are done, there will be 21 trees. How many trees did the grove workers plant today?
A: There are 15 trees originally. Then there were 21 trees after some more were planted. So there must have been 21 - 15 = 6. #### 6

Q: If there are 3 cars in the parking lot and 2 more cars arrive, how many cars are in the parking lot?
A: There are originally 3 cars. 2 more cars arrive. 3 + 2 = 5. #### 5
"""

    correct = 0
    total = 0

    for example in dataset["test"].select(range(num_samples)):
        question = example["question"]
        gold_answer = extract_answer(example["answer"])

        # Create prompt with few-shot examples
        prompt = f"{few_shot_examples}\nQ: {question}\nA:"

        # Generate
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        outputs = model.generate(
            **inputs,
            max_new_tokens=512,
            temperature=0.0,  # Greedy for math
            do_sample=False,
        )

        completion = tokenizer.decode(outputs[0], skip_special_tokens=True)
        pred_answer = extract_answer(completion)

        # Check correctness
        if pred_answer == gold_answer:
            correct += 1
        total += 1

        # Debug output
        if total <= 5:
            print(f"Question: {question}")
            print(f"Gold: {gold_answer}, Pred: {pred_answer}")
            print(f"Completion: {completion}\n")

    accuracy = correct / total
    print(f"GSM8K Accuracy: {accuracy:.4f} ({correct}/{total})")
    return accuracy
```

## Code Examples

### Example 1: Comprehensive Benchmark Suite

```python
from lm_eval import evaluator
from lm_eval.models.huggingface import HFLM
import json
from datetime import datetime

class BenchmarkRunner:
    """Run comprehensive LLM benchmark suite."""

    def __init__(self, model_name, output_dir="benchmark_results"):
        self.model_name = model_name
        self.output_dir = output_dir
        self.model = None

    def load_model(self):
        """Load model for evaluation."""
        self.model = HFLM(
            pretrained=self.model_name,
            device="cuda:0",
            dtype="bfloat16",
        )

    def run_knowledge_benchmarks(self):
        """Run knowledge and reasoning benchmarks."""
        tasks = [
            "mmlu",
            "truthfulqa_mc2",
            "arc_challenge",
            "hellaswag",
            "winogrande",
        ]

        results = evaluator.simple_evaluate(
            model=self.model,
            tasks=tasks,
            num_fewshot=5,
            batch_size=8,
        )

        return results

    def run_code_benchmarks(self):
        """Run code generation benchmarks."""
        tasks = [
            "humaneval",
            "mbpp",
        ]

        results = evaluator.simple_evaluate(
            model=self.model,
            tasks=tasks,
            num_fewshot=0,  # Zero-shot for code
            batch_size=1,
        )

        return results

    def run_math_benchmarks(self):
        """Run math reasoning benchmarks."""
        tasks = [
            "gsm8k",
            "math_algebra",
        ]

        results = evaluator.simple_evaluate(
            model=self.model,
            tasks=tasks,
            num_fewshot=8,  # More examples for math
            batch_size=4,
        )

        return results

    def generate_report(self, all_results):
        """Generate comprehensive evaluation report."""
        report = {
            "model": self.model_name,
            "timestamp": datetime.now().isoformat(),
            "results": {},
            "summary": {},
        }

        # Extract key metrics
        for task_name, task_results in all_results["results"].items():
            report["results"][task_name] = task_results

            # Primary metric per task
            if "acc" in task_results:
                report["summary"][task_name] = task_results["acc"]
            elif "exact_match" in task_results:
                report["summary"][task_name] = task_results["exact_match"]
            elif "pass@1" in task_results:
                report["summary"][task_name] = task_results["pass@1"]

        # Calculate category averages
        knowledge_tasks = ["mmlu", "truthfulqa_mc2", "arc_challenge", "hellaswag"]
        knowledge_avg = sum(
            report["summary"][t] for t in knowledge_tasks if t in report["summary"]
        ) / len([t for t in knowledge_tasks if t in report["summary"]])

        report["category_averages"] = {
            "knowledge_reasoning": knowledge_avg,
        }

        # Save report
        output_path = f"{self.output_dir}/{self.model_name.replace('/', '_')}_report.json"
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)

        return report

    def run_full_suite(self):
        """Run complete benchmark suite."""
        print(f"Starting evaluation for {self.model_name}")

        self.load_model()

        print("Running knowledge benchmarks...")
        knowledge_results = self.run_knowledge_benchmarks()

        print("Running code benchmarks...")
        code_results = self.run_code_benchmarks()

        print("Running math benchmarks...")
        math_results = self.run_math_benchmarks()

        # Combine results
        all_results = {
            "results": {
                **knowledge_results["results"],
                **code_results["results"],
                **math_results["results"],
            }
        }

        report = self.generate_report(all_results)

        print("\n=== Evaluation Summary ===")
        for task, score in report["summary"].items():
            print(f"{task}: {score:.4f}")

        return report

# Usage
runner = BenchmarkRunner("mistralai/Mistral-7B-v0.1")
report = runner.run_full_suite()
```

### Example 2: Contamination Detection

```python
from lm_eval.api.metrics import perplexity
from transformers import AutoModelForCausalLM, AutoTokenizer
import numpy as np

class ContaminationDetector:
    """Detect potential benchmark contamination in training data."""

    def __init__(self, model_name):
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            device_map="auto",
        )
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)

    def calculate_perplexity(self, texts):
        """Calculate perplexity for list of texts."""
        perplexities = []

        for text in texts:
            inputs = self.tokenizer(text, return_tensors="pt").to(self.model.device)

            with torch.no_grad():
                outputs = self.model(**inputs, labels=inputs["input_ids"])
                loss = outputs.loss
                perplexity = torch.exp(loss).item()

            perplexities.append(perplexity)

        return perplexities

    def detect_contamination(self, benchmark_samples, baseline_samples):
        """
        Detect contamination by comparing perplexity on benchmark vs baseline.

        Suspiciously low perplexity on benchmark suggests potential memorization.
        """
        benchmark_ppl = self.calculate_perplexity(benchmark_samples)
        baseline_ppl = self.calculate_perplexity(baseline_samples)

        benchmark_mean = np.mean(benchmark_ppl)
        baseline_mean = np.mean(baseline_ppl)

        # Calculate ratio
        ratio = baseline_mean / benchmark_mean

        # Flag if benchmark perplexity is suspiciously lower
        contamination_flag = ratio > 1.5  # Threshold based on empirical studies

        report = {
            "benchmark_perplexity": {
                "mean": benchmark_mean,
                "std": np.std(benchmark_ppl),
                "min": np.min(benchmark_ppl),
                "max": np.max(benchmark_ppl),
            },
            "baseline_perplexity": {
                "mean": baseline_mean,
                "std": np.std(baseline_ppl),
            },
            "ratio": ratio,
            "contamination_suspected": contamination_flag,
        }

        return report

# Usage
detector = ContaminationDetector("meta-llama/Llama-2-7b-hf")

# Sample from MMLU test set
mmlu_samples = [
    "Question: What is the capital of France?\nA. London\nB. Paris\nC. Berlin\nD. Madrid\nAnswer: B",
    # ... more MMLU examples
]

# Baseline: Similar format but different questions
baseline_samples = [
    "Question: What color is the sky?\nA. Red\nB. Blue\nC. Green\nD. Yellow\nAnswer: B",
    # ... more baseline examples
]

contamination_report = detector.detect_contamination(mmlu_samples, baseline_samples)
print(contamination_report)
```

## Anti-Patterns

### Anti-Pattern 1: Benchmark Overfitting
**Wrong**: Optimizing exclusively for benchmark performance
```python
# BAD: Training specifically to improve MMLU score
train_on_mmlu_like_data()  # Creates overfit model
```

**Right**: Use benchmarks as one signal among many
```python
# GOOD: Balanced evaluation strategy
benchmark_scores = evaluate_benchmarks(model)
domain_scores = evaluate_domain_tasks(model)
human_eval_scores = get_human_ratings(model)

overall_score = weighted_average([benchmark_scores, domain_scores, human_eval_scores])
```

### Anti-Pattern 2: Ignoring Benchmark Limitations
**Wrong**: Treating benchmark scores as absolute truth
```python
# BAD: Assuming higher MMLU = better model for all use cases
if model_a_mmlu > model_b_mmlu:
    deploy(model_a)  # May not be better for your specific task
```

**Right**: Validate on target domain
```python
# GOOD: Test on actual use case
benchmark_scores = evaluate_benchmarks([model_a, model_b])
domain_scores = evaluate_on_real_data([model_a, model_b])

# Choose based on domain performance
best_model = max([model_a, model_b], key=lambda m: domain_scores[m])
```

### Anti-Pattern 3: Inconsistent Evaluation Settings
**Wrong**: Comparing results with different configurations
```python
# BAD: Inconsistent few-shot settings
model_a_results = evaluate(model_a, num_fewshot=5)
model_b_results = evaluate(model_b, num_fewshot=0)  # Not comparable!
```

**Right**: Standardize evaluation protocol
```python
# GOOD: Consistent settings
EVAL_CONFIG = {
    "num_fewshot": 5,
    "batch_size": 8,
    "temperature": 0.0,
    "tasks": ["mmlu", "hellaswag", "truthfulqa_mc2"],
}

model_a_results = evaluate(model_a, **EVAL_CONFIG)
model_b_results = evaluate(model_b, **EVAL_CONFIG)
```

## Related Skills

- `llm-evaluation-frameworks.md`: Arize Phoenix, Braintrust, LangSmith for production evaluation
- `llm-as-judge.md`: Using LLMs to evaluate LLM outputs with Prometheus and G-Eval
- `rag-evaluation-metrics.md`: RAGAS metrics for RAG system evaluation
- `custom-llm-evaluation.md`: Domain-specific and custom evaluation metrics
- `dspy-evaluation.md`: DSPy metric functions and evaluation patterns

## Summary

LLM benchmark evaluation provides standardized, reproducible metrics for model capabilities:

**Key Takeaways**:
1. **Standard benchmarks**: MMLU (knowledge), HumanEval (code), GSM8K (math), HellaSwag (common sense)
2. **Frameworks**: lm-evaluation-harness (200+ tasks), LightEval (HuggingFace integration)
3. **Metrics**: Accuracy, pass@k, exact match, F1 depending on task type
4. **Contamination risk**: Always check for training data leakage using perplexity analysis
5. **Limitations**: Benchmarks are proxies, not guarantees of real-world performance

**Best Practices**:
- Use consistent evaluation settings for fair comparisons
- Combine multiple benchmarks covering different capabilities
- Always validate on domain-specific tasks before deployment
- Monitor for contamination using perplexity or membership inference
- Report full evaluation details (num_fewshot, temperature, etc.) for reproducibility

**When to combine with other skills**:
- Use `llm-evaluation-frameworks.md` for production monitoring and tracing
- Use `llm-as-judge.md` when benchmark metrics don't capture quality (e.g., creative writing)
- Use `rag-evaluation-metrics.md` for retrieval-augmented generation systems
- Use `custom-llm-evaluation.md` for domain-specific or safety evaluations
