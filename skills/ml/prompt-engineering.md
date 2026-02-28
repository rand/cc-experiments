---
name: ml-prompt-engineering
description: Prompt engineering patterns for developers including system prompts, few-shot learning, chain-of-thought, structured output, and tool use prompts
---


# Prompt Engineering

**Scope**: System prompts, few-shot, chain-of-thought, structured output, tool use, evaluation
**Lines**: ~300
**Last Updated**: 2026-02-02

## When to Use This Skill

Activate this skill when:
- Designing system prompts for LLM-powered features
- Implementing few-shot learning for classification or extraction
- Building chain-of-thought reasoning pipelines
- Enforcing structured output (JSON, XML, typed responses)
- Designing tool use / function calling prompts
- Debugging poor LLM outputs or inconsistent behavior
- Evaluating and iterating on prompt quality

## Core Concepts

### System Prompt Design

A system prompt defines the LLM's role, constraints, and output format. Structure it in layers:

```
1. Role and identity
2. Core instructions and constraints
3. Output format specification
4. Examples (optional, but powerful)
5. Edge case handling
```

**Example -- code review assistant**:
```
You are a senior software engineer performing code reviews.

Instructions:
- Focus on bugs, security issues, and performance problems
- Ignore style issues (formatters handle those)
- Rate severity: critical, warning, or suggestion
- If the code is correct and clean, say so briefly

Output format:
For each finding, output:
- File and line number
- Severity (critical/warning/suggestion)
- Description of the issue
- Suggested fix

If no issues are found, respond with: "No issues found."
```

**Rules for system prompts**:
- Be specific about what the model should and should NOT do
- Define output format explicitly -- do not leave it to the model's discretion
- Put the most important instructions first and last (primacy and recency effects)
- Avoid contradictory instructions; test for conflicts
- Keep it under 1500 tokens unless you have demonstrated that longer prompts improve output

---

### Few-Shot Patterns

Few-shot prompting provides examples that demonstrate the desired input-output mapping.

#### Selecting Examples

- **Cover the output space**: Include at least one example per category or output type
- **Include edge cases**: Show how to handle ambiguous or tricky inputs
- **Use realistic data**: Synthetic examples that are too clean teach the wrong patterns
- **3-5 examples is usually sufficient**: More is not always better; it consumes context window

#### Formatting

Consistent delimiters make examples unambiguous:

```
Classify the sentiment of each review.

Review: "The battery lasts forever and the screen is gorgeous."
Sentiment: positive

Review: "It works, I guess. Nothing special."
Sentiment: neutral

Review: "Broke after two days. Customer service was unhelpful."
Sentiment: negative

Review: "{{USER_INPUT}}"
Sentiment:
```

#### Negative Examples

Show what NOT to do when the model tends toward a specific failure mode:

```
Extract the company name from the text. If no company is mentioned, return "NONE".

Text: "I work at Anthropic on language models."
Company: Anthropic

Text: "The weather is nice today."
Company: NONE

Text: "{{USER_INPUT}}"
Company:
```

Without the negative example, models may hallucinate a company name when none exists.

---

### Chain-of-Thought (CoT)

Chain-of-thought prompting asks the model to show its reasoning before giving a final answer. This improves accuracy on tasks requiring logic, math, or multi-step reasoning.

#### Explicit CoT

```
Solve the following problem step by step, then give the final answer.

Problem: A store has 45 apples. They sell 12 in the morning and receive
a shipment of 30 in the afternoon. A customer then buys 8. How many
apples does the store have?

Step-by-step reasoning:
1. Start with 45 apples
2. Sell 12: 45 - 12 = 33
3. Receive 30: 33 + 30 = 63
4. Customer buys 8: 63 - 8 = 55

Final answer: 55
```

#### Scratchpad Pattern

For complex tasks, give the model a dedicated reasoning space:

```xml
<task>Determine if this code has a security vulnerability.</task>

<code>
def login(username, password):
    query = f"SELECT * FROM users WHERE name='{username}' AND pass='{password}'"
    return db.execute(query)
</code>

Think through this step by step in <scratchpad> tags, then provide
your assessment in <answer> tags.
```

The scratchpad can be parsed out and discarded from user-facing output while preserving reasoning quality.

#### When CoT Helps vs Hurts
- **Helps**: Math, logic, code analysis, multi-step reasoning, ambiguous classification
- **Hurts**: Simple lookups, creative writing, tasks where speed matters more than accuracy
- **Cost**: Increases token usage (and latency). Use only when accuracy gains justify the cost.

---

### Structured Output

#### JSON Mode

Most LLM APIs support JSON mode. Combine it with a schema in the prompt:

```
Extract the following fields from the customer message.
Respond with valid JSON matching this schema:

{
  "intent": "refund" | "question" | "complaint" | "praise",
  "product": string | null,
  "urgency": "low" | "medium" | "high",
  "summary": string (under 50 words)
}
```

**Tips**:
- Always provide the schema in the prompt even when using JSON mode
- Use `null` explicitly for optional fields
- Constrain string fields with enums or length limits
- Validate the output programmatically; never trust the model to always conform

#### XML Tags for Structure

When you need structured sections but not strict JSON:

```xml
Analyze the following code and respond using these tags:

<bugs>List any bugs found, one per line</bugs>
<security>List security concerns</security>
<suggestions>List improvement suggestions</suggestions>

If a section has no findings, include the tags with "None" inside.
```

XML tags are useful for:
- Separating reasoning from answers (scratchpad pattern)
- Multi-part outputs that mix prose and data
- Easy regex-based extraction in post-processing

#### Schema Enforcement with Tool Use

The most reliable structured output uses function calling / tool use, where the API enforces the output schema:

```python
tools = [{
    "name": "classify_ticket",
    "description": "Classify a support ticket",
    "input_schema": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "enum": ["billing", "technical", "account", "other"]
            },
            "priority": {
                "type": "integer",
                "minimum": 1,
                "maximum": 5
            },
            "summary": {
                "type": "string",
                "maxLength": 200
            }
        },
        "required": ["category", "priority", "summary"]
    }
}]
```

This approach gives you type safety the schema guarantees. Use it whenever structured output reliability matters.

---

### Tool Use Prompts

#### Designing Tool Descriptions

Tool descriptions are prompts. Write them as carefully as system prompts.

```python
# BAD
{"name": "search", "description": "Search for stuff"}

# GOOD
{
    "name": "search_knowledge_base",
    "description": "Search the internal knowledge base for articles matching a query. Returns the top 5 results ranked by relevance. Use this when the user asks a question that requires factual information about our products or policies. Do NOT use this for general conversation.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural language search query. Be specific. Example: 'refund policy for digital products'"
            },
            "max_results": {
                "type": "integer",
                "description": "Number of results to return (1-10). Default: 5",
                "default": 5
            }
        },
        "required": ["query"]
    }
}
```

**Rules for tool descriptions**:
- Explain **when** to use the tool, not just what it does
- Explain **when NOT** to use it to prevent misuse
- Describe parameter semantics with examples
- Document what the tool returns

#### Parallel Tool Use

When the model can call multiple tools simultaneously:

```
You have access to the following tools. When multiple pieces of
information are needed independently, call the relevant tools
in parallel rather than sequentially.

For example, if a user asks "What's the weather in NYC and
the stock price of AAPL?", call both weather and stock tools
simultaneously.
```

#### Error Recovery

Tell the model how to handle tool failures:

```
If a tool call returns an error:
1. Do NOT retry the same call with the same parameters
2. If the error suggests a parameter issue, try correcting the parameters
3. If the tool is unavailable, inform the user and suggest alternatives
4. Never fabricate data that a tool should have provided
```

---

### Temperature and Sampling Guidance

| Temperature | Use Case |
|-------------|----------|
| 0.0 | Deterministic tasks: classification, extraction, code generation |
| 0.3-0.5 | Balanced: summarization, Q&A, moderate creativity |
| 0.7-1.0 | Creative tasks: writing, brainstorming, dialogue |
| >1.0 | Rarely useful. Outputs become incoherent. |

**Rules**:
- Use temperature 0 for anything that needs consistency across runs
- If you need variety, increase temperature but add constraints in the prompt
- `top_p` is an alternative to temperature; do not use both aggressively
- For production systems, always set temperature explicitly; never rely on defaults

---

### Evaluation and Iteration

#### Systematic Prompt Evaluation

1. **Build an eval set**: 20-50 representative inputs with expected outputs
2. **Define metrics**: Accuracy, format compliance, hallucination rate, latency
3. **Baseline**: Measure the current prompt against the eval set
4. **Iterate**: Change one thing at a time. Measure after each change.
5. **Regression test**: Every prompt change runs against the full eval set

#### Common Failure Modes and Fixes

| Failure | Likely Cause | Fix |
|---------|-------------|-----|
| Ignores instructions | Instruction buried in middle of prompt | Move to start or end |
| Hallucinated facts | No grounding data provided | Add retrieval, constrain to provided context |
| Wrong output format | Format spec is vague | Add explicit examples, use JSON/tool mode |
| Inconsistent behavior | Temperature too high | Lower temperature, add more examples |
| Too verbose | No length constraint | Add "respond in under N words/sentences" |
| Refuses valid requests | Overly broad safety framing | Narrow the restriction, add explicit permissions |

#### Before/After Example

**Before** (vague):
```
Summarize this article.
```

**After** (specific):
```
Summarize the following article in exactly 3 bullet points.
Each bullet should be one sentence, under 25 words.
Focus on the key findings, not background information.
Do not include opinions or speculation.

Article:
{{ARTICLE_TEXT}}
```

The "after" version produces consistent, predictable output because every axis of variation is constrained.

---

## Anti-patterns

- **Vague instructions**: "Be helpful" or "Do a good job" adds nothing. Be specific about what good looks like.
- **Conflicting constraints**: "Be concise" + "Include all details" forces the model to guess which you actually want.
- **Over-prompting**: 5000-token system prompts with redundant instructions. If the model already does it well, do not instruct it.
- **Prompt injection vulnerability**: User input that can override system instructions. Always separate system instructions from user input structurally.
- **Assuming determinism**: Even at temperature 0, outputs can vary across API versions. Build for variation.
- **Testing on one example**: A prompt that works for your test case may fail on the next ten. Always use an eval set.
- **Prompt cargo-culting**: Copying prompts from blog posts without understanding why they work. Every prompt should be tailored to your specific model, task, and data.

---

## Checklists

### System Prompt Review
- [ ] Role is clearly defined
- [ ] Instructions are specific and non-contradictory
- [ ] Output format is explicitly specified with examples
- [ ] Edge cases and error handling are addressed
- [ ] Prompt is tested against an eval set of 20+ examples
- [ ] User input is structurally separated from instructions
- [ ] Token count is reasonable for the task

### Tool Use Design
- [ ] Each tool has a clear description with usage guidance
- [ ] Parameters have descriptions and examples
- [ ] Error handling behavior is specified
- [ ] Parallel vs sequential tool use is addressed
- [ ] Output schema is enforced via API, not just prompt

---

## Related Skills

- `llm-model-selection.md` -- Choosing the right model for the task
- `llm-evaluation-frameworks.md` -- Systematic evaluation approaches
- `dspy-signatures.md` -- Programmatic prompt optimization with DSPy
- `llm-as-judge.md` -- Using LLMs to evaluate LLM outputs
- `rag-evaluation-metrics.md` -- Evaluating retrieval-augmented generation
