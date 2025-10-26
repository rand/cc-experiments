---
name: ml-llm-as-judge
description: Comprehensive guide to LLM-as-judge evaluation patterns including Prometheus 2 models, G-Eval framework, pairwise/pointwise/reference-guided methods, bias mitigation, and uncertainty quantification
---

# LLM-as-Judge Evaluation

Last Updated: 2025-10-26

## When to Use This Skill

Use LLM-as-judge evaluation when:
- **Subjective quality metrics**: Evaluating helpfulness, coherence, creativity, tone
- **Open-ended generation**: Assessing essay writing, creative content, dialogue quality
- **No ground truth**: Tasks where reference answers don't exist or are insufficient
- **Human preference alignment**: Approximating human judgments at scale
- **Rapid iteration**: Quick feedback on prompt or model changes without human annotation
- **Multi-dimensional evaluation**: Assessing multiple quality aspects simultaneously
- **Pairwise comparison**: A/B testing between model outputs or prompt variations
- **Cost-effective scaling**: Replacing expensive human evaluation for certain tasks

**Anti-pattern**: Using LLM-as-judge for tasks with **objective ground truth** (use exact match, BLEU, etc. instead). Never rely solely on LLM judges without validation against human judgments.

## Core Concepts

### Evaluation Paradigms

**1. Pointwise Evaluation**
- Judge evaluates single output independently
- Assigns absolute score (e.g., 1-5 rating)
- Simple but prone to inconsistent scale usage

**2. Pairwise Evaluation**
- Judge compares two outputs (A vs B)
- Determines which is better or if tied
- More reliable than pointwise (relative comparison easier than absolute)
- Can suffer from position bias

**3. Reference-Guided Evaluation**
- Judge has access to reference answer
- Evaluates output quality against reference
- Useful for factual accuracy, task completion

### LLM Judge Models (2024-2025)

**Prometheus 2 (Fine-tuned Evaluators)**
- **Models**: prometheus-7b-v2.0, prometheus-8x7b-v2.0
- **Specialty**: Fine-tuned specifically for evaluation tasks
- **Strengths**: Consistent scoring, explicit rubrics, reduced bias
- **Variants**: BGB (Best-of-n Greedy + Backtracking) for improved accuracy
- **Open source**: Full control and transparency

**G-Eval (GPT-based)**
- **Framework**: Uses GPT-4 for evaluation with chain-of-thought
- **Strengths**: High correlation with human judgments, flexible criteria
- **Weaknesses**: More expensive, potential GPT-4 biases

**GPT-4 / Claude 3 Opus (General-purpose)**
- **Use case**: Quick prototyping, high-quality evaluations
- **Strengths**: Strong reasoning, nuanced judgments
- **Weaknesses**: Expensive, API-dependent, potential biases

**Llama-3-70B-Instruct / Mixtral-8x7B**
- **Use case**: Cost-effective, self-hosted evaluation
- **Strengths**: Good performance for many tasks, lower cost
- **Weaknesses**: Lower quality than specialized models

### Bias Mitigation Strategies

**Position Bias**: Judge favors first/second position in pairwise comparisons
- **Solution**: Swap positions and average scores

**Verbosity Bias**: Judge favors longer responses
- **Solution**: Include length-agnostic criteria, normalize by length

**Self-Enhancement Bias**: Judge favors outputs from same model family
- **Solution**: Use different model for judging than generation

**Scale Inconsistency**: Judge uses rating scale inconsistently
- **Solution**: Use pairwise comparisons or calibration sets

### Uncertainty Quantification

**Self-Consistency**: Sample multiple judgments and measure agreement
**Confidence Scoring**: Ask judge to provide confidence level
**Multi-Judge Ensemble**: Use multiple judges and measure consensus

## Implementation Patterns

### Pattern 1: Prometheus 2 Pointwise Evaluation

**When to use**: Fine-tuned evaluator with explicit rubrics

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

class PrometheusEvaluator:
    """Prometheus 2 evaluator for pointwise assessment."""

    def __init__(self, model_name="prometheus-eval/prometheus-7b-v2.0"):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.bfloat16,
            device_map="auto",
        )

    def evaluate(
        self,
        instruction: str,
        response: str,
        reference_answer: str = None,
        rubric: str = None,
    ) -> dict:
        """
        Evaluate response using Prometheus format.

        Args:
            instruction: The task instruction
            response: The response to evaluate
            reference_answer: Optional reference answer
            rubric: Evaluation rubric (5-point scale by default)

        Returns:
            Dict with score and feedback
        """
        # Default rubric
        if rubric is None:
            rubric = """
1: The response is completely incorrect or irrelevant.
2: The response has major errors or misses key points.
3: The response is acceptable but has some mistakes or lacks detail.
4: The response is good with minor issues.
5: The response is excellent, accurate, and comprehensive.
"""

        # Prometheus prompt format
        if reference_answer:
            prompt = f"""###Task Description:
An instruction (might include an Input inside it), a response to evaluate, and a score rubric representing a evaluation criteria are given.

1. Write a detailed feedback that assess the quality of the response strictly based on the given score rubric, not evaluating in general.
2. After writing a feedback, write a score that is an integer between 1 and 5. You should refer to the score rubric.
3. The output format should look as follows: \"Feedback: (write a feedback for criteria) [RESULT] (an integer number between 1 and 5)\"

###The instruction to evaluate:
{instruction}

###Response to evaluate:
{response}

###Reference Answer (Score 5):
{reference_answer}

###Score Rubrics:
{rubric}

###Feedback:"""
        else:
            prompt = f"""###Task Description:
An instruction (might include an Input inside it), a response to evaluate, and a score rubric representing a evaluation criteria are given.

1. Write a detailed feedback that assess the quality of the response strictly based on the given score rubric, not evaluating in general.
2. After writing a feedback, write a score that is an integer between 1 and 5. You should refer to the score rubric.
3. The output format should look as follows: \"Feedback: (write a feedback for criteria) [RESULT] (an integer number between 1 and 5)\"

###The instruction to evaluate:
{instruction}

###Response to evaluate:
{response}

###Score Rubrics:
{rubric}

###Feedback:"""

        # Generate evaluation
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=512,
                temperature=0.0,
                do_sample=False,
            )

        evaluation = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

        # Extract score and feedback
        feedback = evaluation.split("###Feedback:")[-1].strip()

        # Parse score
        import re
        score_match = re.search(r'\[RESULT\]\s*(\d+)', feedback)
        score = int(score_match.group(1)) if score_match else None

        return {
            "score": score,
            "feedback": feedback.split("[RESULT]")[0].strip() if score else feedback,
            "raw_output": evaluation,
        }

# Usage
evaluator = PrometheusEvaluator()

result = evaluator.evaluate(
    instruction="Explain photosynthesis in simple terms.",
    response="Photosynthesis is the process where plants use sunlight to make food from water and carbon dioxide.",
    reference_answer="Photosynthesis is the process by which plants convert light energy into chemical energy. Plants use sunlight, water, and carbon dioxide to produce glucose (sugar) and oxygen.",
)

print(f"Score: {result['score']}/5")
print(f"Feedback: {result['feedback']}")
```

### Pattern 2: G-Eval Framework

**When to use**: GPT-4 based evaluation with chain-of-thought

```python
from openai import OpenAI
import json

class GEvalEvaluator:
    """G-Eval framework using GPT-4 with chain-of-thought."""

    def __init__(self, model="gpt-4-turbo-preview"):
        self.client = OpenAI()
        self.model = model

    def evaluate(
        self,
        task_description: str,
        criteria: str,
        response: str,
        context: str = None,
        min_score: int = 1,
        max_score: int = 5,
    ) -> dict:
        """
        Evaluate response using G-Eval with chain-of-thought.

        Args:
            task_description: What the task is
            criteria: What to evaluate (coherence, fluency, etc.)
            response: The response to evaluate
            context: Optional context (e.g., prompt, reference)
            min_score: Minimum score
            max_score: Maximum score

        Returns:
            Dict with score, reasoning, and confidence
        """
        # G-Eval prompt with chain-of-thought
        prompt = f"""You will be given a task description and evaluation criteria. Your job is to evaluate the given response based on the criteria.

Task Description:
{task_description}

Evaluation Criteria:
{criteria}

{f"Context: {context}" if context else ""}

Response to Evaluate:
{response}

Please evaluate step-by-step:
1. First, identify the key aspects of the evaluation criteria
2. Analyze how well the response meets each aspect
3. Provide a final score from {min_score} to {max_score}

Your response MUST be valid JSON in this format:
{{
  "reasoning": "Detailed step-by-step analysis",
  "score": <integer from {min_score} to {max_score}>,
  "confidence": <float from 0.0 to 1.0>
}}
"""

        # Call GPT-4 with JSON mode
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert evaluator. Provide thoughtful, unbiased assessments.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
        )

        result = json.loads(response.choices[0].message.content)

        return result

    def evaluate_with_uncertainty(
        self,
        task_description: str,
        criteria: str,
        response: str,
        num_samples: int = 5,
    ) -> dict:
        """
        Evaluate with uncertainty quantification via self-consistency.

        Args:
            task_description: Task description
            criteria: Evaluation criteria
            response: Response to evaluate
            num_samples: Number of evaluations to sample

        Returns:
            Dict with mean score, std, and all samples
        """
        scores = []
        reasonings = []

        for _ in range(num_samples):
            result = self.evaluate(task_description, criteria, response)
            scores.append(result["score"])
            reasonings.append(result["reasoning"])

        import numpy as np

        return {
            "mean_score": np.mean(scores),
            "std_score": np.std(scores),
            "min_score": np.min(scores),
            "max_score": np.max(scores),
            "all_scores": scores,
            "sample_reasonings": reasonings,
            "confidence": 1.0 - (np.std(scores) / np.mean(scores)) if np.mean(scores) > 0 else 0.0,
        }

# Usage
evaluator = GEvalEvaluator()

# Single evaluation
result = evaluator.evaluate(
    task_description="Summarize a scientific article for general audience",
    criteria="Evaluate based on: 1) Accuracy of scientific content, 2) Clarity for non-experts, 3) Conciseness",
    response="Researchers found that exercise increases brain health by promoting neurogenesis. Regular physical activity can improve memory and reduce dementia risk.",
    context="Original article discusses BDNF protein and hippocampal neurogenesis in exercise studies.",
)

print(f"Score: {result['score']}/5")
print(f"Reasoning: {result['reasoning']}")

# Evaluation with uncertainty
uncertain_result = evaluator.evaluate_with_uncertainty(
    task_description="Summarize a scientific article for general audience",
    criteria="Evaluate based on accuracy, clarity, and conciseness",
    response="Researchers found that exercise increases brain health...",
    num_samples=5,
)

print(f"Mean score: {uncertain_result['mean_score']:.2f} ± {uncertain_result['std_score']:.2f}")
print(f"Confidence: {uncertain_result['confidence']:.2f}")
```

### Pattern 3: Pairwise Comparison with Bias Mitigation

**When to use**: A/B testing with position bias correction

```python
from openai import OpenAI
import json

class PairwiseJudge:
    """Pairwise comparison with position bias mitigation."""

    def __init__(self, model="gpt-4-turbo-preview"):
        self.client = OpenAI()
        self.model = model

    def compare(
        self,
        instruction: str,
        response_a: str,
        response_b: str,
        criteria: str = "overall quality",
    ) -> dict:
        """
        Compare two responses with bias mitigation.

        Args:
            instruction: The task instruction
            response_a: First response
            response_b: Second response
            criteria: What to compare on

        Returns:
            Dict with winner and reasoning
        """
        # First comparison (A first, B second)
        result_ab = self._single_comparison(
            instruction, response_a, response_b, criteria, "A", "B"
        )

        # Second comparison (B first, A second) to mitigate position bias
        result_ba = self._single_comparison(
            instruction, response_b, response_a, criteria, "B", "A"
        )

        # Aggregate results
        if result_ab["winner"] == result_ba["winner"]:
            # Consistent winner
            winner = result_ab["winner"]
            confidence = "high"
        elif result_ab["winner"] == "tie" or result_ba["winner"] == "tie":
            # One or both say tie
            winner = "tie"
            confidence = "medium"
        else:
            # Disagreement - position bias detected
            winner = "tie"
            confidence = "low"

        return {
            "winner": winner,
            "confidence": confidence,
            "reasoning_ab": result_ab["reasoning"],
            "reasoning_ba": result_ba["reasoning"],
            "position_bias_detected": result_ab["winner"] != result_ba["winner"] and "tie" not in [result_ab["winner"], result_ba["winner"]],
        }

    def _single_comparison(
        self,
        instruction: str,
        response_first: str,
        response_second: str,
        criteria: str,
        first_label: str,
        second_label: str,
    ) -> dict:
        """Single pairwise comparison."""
        prompt = f"""Compare the following two responses to the given instruction based on {criteria}.

Instruction:
{instruction}

Response {first_label}:
{response_first}

Response {second_label}:
{response_second}

Which response is better? Provide your answer as JSON:
{{
  "winner": "{first_label}" or "{second_label}" or "tie",
  "reasoning": "Detailed explanation of why"
}}
"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an objective evaluator. Provide fair, unbiased comparisons.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
        )

        result = json.loads(response.choices[0].message.content)
        return result

# Usage
judge = PairwiseJudge()

result = judge.compare(
    instruction="Write a haiku about spring",
    response_a="Cherry blossoms bloom\nGentle breeze carries petals\nSpring has come again",
    response_b="Flowers are blooming\nIt is springtime outside now\nNature is pretty",
    criteria="poetic quality and imagery",
)

print(f"Winner: {result['winner']}")
print(f"Confidence: {result['confidence']}")
print(f"Position bias detected: {result['position_bias_detected']}")
print(f"Reasoning (A-B): {result['reasoning_ab']}")
```

### Pattern 4: Multi-Dimensional Evaluation

**When to use**: Assessing multiple quality aspects simultaneously

```python
from typing import List, Dict
from openai import OpenAI
import json

class MultiDimensionalJudge:
    """Evaluate response across multiple dimensions."""

    def __init__(self, model="gpt-4-turbo-preview"):
        self.client = OpenAI()
        self.model = model

    def evaluate(
        self,
        instruction: str,
        response: str,
        dimensions: List[Dict[str, str]],
    ) -> dict:
        """
        Evaluate response across multiple dimensions.

        Args:
            instruction: Task instruction
            response: Response to evaluate
            dimensions: List of {name, description, min_score, max_score} dicts

        Returns:
            Dict with scores per dimension and overall
        """
        # Build dimension descriptions
        dimension_descriptions = []
        for dim in dimensions:
            dimension_descriptions.append(
                f"- {dim['name']}: {dim['description']} (scale: {dim.get('min_score', 1)}-{dim.get('max_score', 5)})"
            )

        prompt = f"""Evaluate the following response across multiple dimensions.

Instruction:
{instruction}

Response:
{response}

Evaluation Dimensions:
{chr(10).join(dimension_descriptions)}

For each dimension:
1. Provide a score within the specified range
2. Explain your reasoning

Return your evaluation as JSON:
{{
  "dimensions": [
    {{
      "name": "dimension_name",
      "score": <score>,
      "reasoning": "explanation"
    }},
    ...
  ],
  "overall_score": <average score>,
  "summary": "overall assessment"
}}
"""

        response_eval = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert evaluator. Assess each dimension independently.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
        )

        result = json.loads(response_eval.choices[0].message.content)

        # Calculate weighted overall score if weights provided
        if any("weight" in dim for dim in dimensions):
            weighted_score = sum(
                dim_result["score"] * next((d["weight"] for d in dimensions if d["name"] == dim_result["name"]), 1.0)
                for dim_result in result["dimensions"]
            ) / sum(dim.get("weight", 1.0) for dim in dimensions)

            result["weighted_overall_score"] = weighted_score

        return result

# Usage
judge = MultiDimensionalJudge()

result = judge.evaluate(
    instruction="Explain quantum entanglement to a high school student",
    response="Quantum entanglement is when two particles are connected in a weird way. If you measure one particle, it instantly affects the other, even if they're far apart. Einstein called it 'spooky action at a distance.' It's like having two magic coins that always land on opposite sides.",
    dimensions=[
        {
            "name": "accuracy",
            "description": "Scientific accuracy of the explanation",
            "min_score": 1,
            "max_score": 5,
            "weight": 2.0,  # Most important
        },
        {
            "name": "clarity",
            "description": "How clear and understandable the explanation is",
            "min_score": 1,
            "max_score": 5,
            "weight": 1.5,
        },
        {
            "name": "engagement",
            "description": "How engaging and interesting the explanation is",
            "min_score": 1,
            "max_score": 5,
            "weight": 1.0,
        },
        {
            "name": "appropriate_level",
            "description": "Whether the explanation is appropriate for high school students",
            "min_score": 1,
            "max_score": 5,
            "weight": 1.5,
        },
    ],
)

print("Dimension scores:")
for dim in result["dimensions"]:
    print(f"  {dim['name']}: {dim['score']}/5 - {dim['reasoning']}")

print(f"\nOverall score: {result['overall_score']:.2f}")
print(f"Weighted score: {result.get('weighted_overall_score', 'N/A'):.2f}")
print(f"Summary: {result['summary']}")
```

### Pattern 5: Expert-in-the-Loop Validation

**When to use**: Validating LLM judge against human experts

```python
import pandas as pd
from sklearn.metrics import cohen_kappa_score
from typing import List, Dict
import json

class JudgeValidator:
    """Validate LLM judge against human annotations."""

    def __init__(self, llm_judge):
        """
        Args:
            llm_judge: Any judge class with evaluate() method
        """
        self.llm_judge = llm_judge

    def validate_against_humans(
        self,
        test_cases: List[Dict],
        human_annotations: List[int],
    ) -> dict:
        """
        Validate LLM judge against human expert annotations.

        Args:
            test_cases: List of {instruction, response} dicts
            human_annotations: List of human scores (same order as test_cases)

        Returns:
            Validation metrics
        """
        llm_scores = []

        for case in test_cases:
            result = self.llm_judge.evaluate(
                instruction=case["instruction"],
                response=case["response"],
            )
            llm_scores.append(result["score"])

        # Calculate agreement metrics
        from scipy.stats import pearsonr, spearmanr

        # Pearson correlation (linear relationship)
        pearson_corr, pearson_p = pearsonr(llm_scores, human_annotations)

        # Spearman correlation (rank-order relationship)
        spearman_corr, spearman_p = spearmanr(llm_scores, human_annotations)

        # Cohen's Kappa (categorical agreement)
        kappa = cohen_kappa_score(human_annotations, llm_scores)

        # Mean Absolute Error
        mae = sum(abs(h - l) for h, l in zip(human_annotations, llm_scores)) / len(human_annotations)

        # Identify disagreements
        disagreements = [
            {
                "case": test_cases[i],
                "human_score": human_annotations[i],
                "llm_score": llm_scores[i],
                "difference": abs(human_annotations[i] - llm_scores[i]),
            }
            for i in range(len(test_cases))
            if abs(human_annotations[i] - llm_scores[i]) >= 2  # Significant disagreement
        ]

        return {
            "pearson_correlation": pearson_corr,
            "spearman_correlation": spearman_corr,
            "cohens_kappa": kappa,
            "mean_absolute_error": mae,
            "num_significant_disagreements": len(disagreements),
            "disagreement_rate": len(disagreements) / len(test_cases),
            "sample_disagreements": disagreements[:5],  # Top 5 for review
        }

    def calibrate_judge(
        self,
        calibration_set: List[Dict],
        human_scores: List[int],
        target_correlation: float = 0.8,
    ) -> str:
        """
        Generate calibration recommendations based on validation.

        Args:
            calibration_set: Test cases for calibration
            human_scores: Human expert scores
            target_correlation: Desired correlation threshold

        Returns:
            Calibration recommendations
        """
        validation = self.validate_against_humans(calibration_set, human_scores)

        recommendations = []

        if validation["pearson_correlation"] < target_correlation:
            recommendations.append(
                f"Low correlation ({validation['pearson_correlation']:.2f}). Consider:\n"
                "  - Using a more capable judge model (e.g., GPT-4 instead of GPT-3.5)\n"
                "  - Refining evaluation criteria/rubrics\n"
                "  - Adding more examples to the prompt"
            )

        if validation["mean_absolute_error"] > 1.0:
            recommendations.append(
                f"High MAE ({validation['mean_absolute_error']:.2f}). The judge is often off by >1 point.\n"
                "  - Review sample disagreements\n"
                "  - Clarify scoring rubric\n"
                "  - Use reference-guided evaluation if possible"
            )

        if validation["disagreement_rate"] > 0.2:
            recommendations.append(
                f"High disagreement rate ({validation['disagreement_rate']:.1%}).\n"
                "  - Review cases where judge disagrees significantly\n"
                "  - Add calibration examples to prompt\n"
                "  - Consider ensemble of multiple judges"
            )

        if not recommendations:
            recommendations.append(
                "Judge performance is acceptable. Continue monitoring on production data."
            )

        return "\n\n".join(recommendations)

# Usage
from geval_evaluator import GEvalEvaluator  # From Pattern 2

judge = GEvalEvaluator()
validator = JudgeValidator(judge)

# Test cases with human expert scores
test_cases = [
    {
        "instruction": "Explain photosynthesis",
        "response": "Photosynthesis is how plants make food using sunlight...",
    },
    # ... more cases
]

human_scores = [4, 5, 3, 2, 4, 5, 3, 4]  # From expert annotations

# Validate
validation_results = validator.validate_against_humans(test_cases, human_scores)

print(f"Pearson correlation: {validation_results['pearson_correlation']:.3f}")
print(f"Spearman correlation: {validation_results['spearman_correlation']:.3f}")
print(f"Cohen's Kappa: {validation_results['cohens_kappa']:.3f}")
print(f"MAE: {validation_results['mean_absolute_error']:.2f}")

# Get calibration recommendations
recommendations = validator.calibrate_judge(test_cases, human_scores)
print(f"\nRecommendations:\n{recommendations}")
```

## Code Examples

### Example 1: Production LLM-as-Judge Pipeline

```python
from typing import List, Dict, Optional
from dataclasses import dataclass
import json
from datetime import datetime

@dataclass
class JudgmentResult:
    """Result from LLM judge."""
    score: float
    reasoning: str
    confidence: float
    judge_model: str
    timestamp: str
    metadata: Dict = None

class ProductionJudgePipeline:
    """Production-ready LLM-as-judge pipeline with logging and monitoring."""

    def __init__(
        self,
        judge_model: str = "gpt-4-turbo-preview",
        enable_uncertainty: bool = True,
        enable_bias_mitigation: bool = True,
        log_path: str = "judge_logs.jsonl",
    ):
        self.judge = GEvalEvaluator(model=judge_model)
        self.pairwise_judge = PairwiseJudge(model=judge_model)
        self.enable_uncertainty = enable_uncertainty
        self.enable_bias_mitigation = enable_bias_mitigation
        self.log_path = log_path

    def judge_single(
        self,
        task_description: str,
        criteria: str,
        response: str,
        context: Optional[str] = None,
    ) -> JudgmentResult:
        """Judge single response with optional uncertainty quantification."""

        if self.enable_uncertainty:
            result = self.judge.evaluate_with_uncertainty(
                task_description=task_description,
                criteria=criteria,
                response=response,
                num_samples=3,
            )

            judgment = JudgmentResult(
                score=result["mean_score"],
                reasoning=result["sample_reasonings"][0],  # First reasoning
                confidence=result["confidence"],
                judge_model=self.judge.model,
                timestamp=datetime.now().isoformat(),
                metadata={
                    "std_score": result["std_score"],
                    "all_scores": result["all_scores"],
                },
            )
        else:
            result = self.judge.evaluate(
                task_description=task_description,
                criteria=criteria,
                response=response,
                context=context,
            )

            judgment = JudgmentResult(
                score=result["score"],
                reasoning=result["reasoning"],
                confidence=result.get("confidence", 1.0),
                judge_model=self.judge.model,
                timestamp=datetime.now().isoformat(),
            )

        # Log judgment
        self._log_judgment(judgment, task_description, response)

        return judgment

    def judge_pairwise(
        self,
        instruction: str,
        response_a: str,
        response_b: str,
        criteria: str = "overall quality",
    ) -> Dict:
        """Judge pairwise comparison with bias mitigation."""

        result = self.pairwise_judge.compare(
            instruction=instruction,
            response_a=response_a,
            response_b=response_b,
            criteria=criteria,
        )

        # Log comparison
        self._log_comparison(result, instruction, response_a, response_b)

        return result

    def batch_evaluate(
        self,
        examples: List[Dict],
        task_description: str,
        criteria: str,
    ) -> List[JudgmentResult]:
        """Evaluate batch of examples."""

        results = []

        for i, example in enumerate(examples):
            judgment = self.judge_single(
                task_description=task_description,
                criteria=criteria,
                response=example["response"],
                context=example.get("context"),
            )

            results.append(judgment)

            # Progress
            if (i + 1) % 10 == 0:
                print(f"Evaluated {i + 1}/{len(examples)} examples")

        # Calculate statistics
        scores = [r.score for r in results]
        avg_score = sum(scores) / len(scores)
        avg_confidence = sum(r.confidence for r in results) / len(results)

        print(f"\nBatch statistics:")
        print(f"  Average score: {avg_score:.2f}")
        print(f"  Average confidence: {avg_confidence:.2f}")
        print(f"  Score range: {min(scores):.2f} - {max(scores):.2f}")

        return results

    def _log_judgment(self, judgment: JudgmentResult, task: str, response: str):
        """Log judgment to file."""
        log_entry = {
            "type": "single_judgment",
            "task": task,
            "response": response,
            "score": judgment.score,
            "confidence": judgment.confidence,
            "judge_model": judgment.judge_model,
            "timestamp": judgment.timestamp,
        }

        with open(self.log_path, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

    def _log_comparison(self, result: Dict, instruction: str, response_a: str, response_b: str):
        """Log pairwise comparison."""
        log_entry = {
            "type": "pairwise_comparison",
            "instruction": instruction,
            "response_a": response_a,
            "response_b": response_b,
            "winner": result["winner"],
            "confidence": result["confidence"],
            "position_bias_detected": result["position_bias_detected"],
            "timestamp": datetime.now().isoformat(),
        }

        with open(self.log_path, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

# Usage
pipeline = ProductionJudgePipeline(
    judge_model="gpt-4-turbo-preview",
    enable_uncertainty=True,
    enable_bias_mitigation=True,
)

# Single judgment
judgment = pipeline.judge_single(
    task_description="Summarize scientific article",
    criteria="Accuracy, clarity, and conciseness",
    response="Researchers found exercise promotes brain health...",
)

print(f"Score: {judgment.score:.2f} (confidence: {judgment.confidence:.2f})")

# Batch evaluation
examples = [
    {"response": "Response 1..."},
    {"response": "Response 2..."},
    # ... more
]

batch_results = pipeline.batch_evaluate(
    examples=examples,
    task_description="Question answering",
    criteria="Correctness and completeness",
)
```

## Anti-Patterns

### Anti-Pattern 1: Using LLM Judge for Objective Tasks
**Wrong**: Using judge for tasks with clear right/wrong answers
```python
# BAD: LLM judge for exact match tasks
judgment = judge.evaluate(
    task="What is 2+2?",
    response="4",
)  # Expensive and unnecessary
```

**Right**: Use deterministic metrics
```python
# GOOD: Exact match for objective tasks
def evaluate_math(response, expected):
    return {"score": 1.0 if response.strip() == expected.strip() else 0.0}
```

### Anti-Pattern 2: Ignoring Position Bias
**Wrong**: Single pairwise comparison
```python
# BAD: Position bias not addressed
winner = judge.compare(response_a, response_b)  # May favor first position
```

**Right**: Swap positions and aggregate
```python
# GOOD: Mitigate position bias
result_ab = judge.compare(response_a, response_b)
result_ba = judge.compare(response_b, response_a)

if result_ab["winner"] == result_ba["winner"]:
    winner = result_ab["winner"]  # Consistent
else:
    winner = "tie"  # Disagreement = bias detected
```

### Anti-Pattern 3: Not Validating Against Humans
**Wrong**: Blind trust in LLM judge
```python
# BAD: No validation
scores = [judge.evaluate(case) for case in test_cases]
# Are these scores reliable? Unknown!
```

**Right**: Validate on calibration set
```python
# GOOD: Validate against human experts
validator = JudgeValidator(judge)
validation = validator.validate_against_humans(test_cases, human_scores)

if validation["pearson_correlation"] < 0.7:
    print("WARNING: Low correlation with humans. Review calibration.")
```

## Related Skills

- `llm-benchmarks-evaluation.md`: Standard benchmarks for objective capability testing
- `llm-evaluation-frameworks.md`: Arize Phoenix, Braintrust for production evaluation
- `rag-evaluation-metrics.md`: RAGAS metrics combining LLM-as-judge with retrieval evaluation
- `custom-llm-evaluation.md`: Domain-specific evaluation metrics and continuous evaluation
- `dspy-evaluation.md`: DSPy metric functions and prompt optimization

## Summary

LLM-as-judge provides scalable, flexible evaluation for subjective quality metrics:

**Key Takeaways**:
1. **Specialized models**: Prometheus 2 (fine-tuned), G-Eval (GPT-4 CoT), general-purpose (Claude/GPT-4)
2. **Paradigms**: Pointwise (absolute), pairwise (comparative), reference-guided (factual)
3. **Bias mitigation**: Position swapping, verbosity normalization, multi-judge ensemble
4. **Uncertainty**: Self-consistency sampling, confidence scoring, agreement metrics
5. **Validation**: Always validate against human experts on calibration set

**Best Practices**:
- Use pairwise comparison when possible (more reliable than pointwise)
- Always mitigate position bias by swapping positions
- Quantify uncertainty with multi-sample evaluation
- Validate judge against human annotations before production use
- Use specialized models (Prometheus) for consistent, transparent evaluation
- Reserve LLM judges for subjective tasks (use deterministic metrics for objective tasks)

**When to combine with other skills**:
- Use `llm-benchmarks-evaluation.md` for objective capability testing (MMLU, HumanEval)
- Use `llm-evaluation-frameworks.md` to integrate judges with Phoenix/Braintrust pipelines
- Use `rag-evaluation-metrics.md` for RAG-specific metrics with LLM-as-judge components
- Use `custom-llm-evaluation.md` for domain-specific rubrics and safety evaluation
