---
name: dspy-debugging
description: Debugging patterns for DSPy programs including trace analysis, prompt inspection, profiling, and visualization
---

# DSPy Debugging

**Scope**: Program inspection, trace analysis, prompt debugging, performance profiling, error diagnosis, logging
**Lines**: ~500
**Last Updated**: 2025-10-30

## When to Use This Skill

Activate this skill when:
- DSPy program produces unexpected outputs
- Investigating performance bottlenecks
- Understanding prompt optimization results
- Analyzing LM API failures
- Debugging module composition issues
- Inspecting intermediate results in pipelines
- Profiling token usage and costs
- Visualizing program execution flow

## Core Concepts

### Debugging Challenges

**Black box behavior**:
- LM outputs are non-deterministic
- Prompts are auto-generated
- Optimization changes prompts
- Hard to isolate issues

**Complex composition**:
- Multiple modules chained
- Intermediate results hidden
- Error propagation across modules
- Unclear failure points

**Performance issues**:
- Slow LM calls
- Inefficient prompts
- Token waste
- Rate limits

### Debugging Strategy

**Levels of inspection**:
1. **Output level**: Check final results
2. **Module level**: Inspect individual modules
3. **Prompt level**: View generated prompts
4. **Trace level**: Analyze full execution trace
5. **LM level**: Debug API calls

**Debugging workflow**:
1. **Reproduce**: Make issue consistent
2. **Isolate**: Identify failing component
3. **Inspect**: Examine prompts and traces
4. **Fix**: Modify and test
5. **Verify**: Confirm fix works

### DSPy Inspection Tools

**Built-in tools**:
- `dspy.inspect_history()` - View recent LM calls
- `dspy.settings.trace` - Enable execution tracing
- Module attributes - Access predictions and history
- Signature inspection - View input/output specs

**Custom tools**:
- Logging wrappers
- Trace analyzers
- Prompt visualizers
- Performance profilers

---

## Patterns

### Pattern 1: Basic Output Inspection

```python
import dspy

# Configure LM
lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
dspy.configure(lm=lm)

# Create module
qa = dspy.ChainOfThought("question -> answer")

# Execute and inspect result
result = qa(question="What is DSPy?")

print("=== Result Inspection ===")
print(f"Answer: {result.answer}")
print(f"Reasoning: {result.reasoning}")

# Inspect all fields
print("\n=== All Fields ===")
for field in result._fields:
    print(f"{field}: {getattr(result, field)}")

# Check if result is valid
print("\n=== Validation ===")
print(f"Has answer: {hasattr(result, 'answer')}")
print(f"Answer is non-empty: {bool(result.answer.strip())}")
print(f"Has reasoning: {hasattr(result, 'reasoning')}")

# Inspect metadata if available
if hasattr(result, "_trace"):
    print("\n=== Trace Metadata ===")
    print(f"Trace: {result._trace}")
```

**When to use**:
- Initial debugging
- Sanity checking outputs
- Verifying field presence
- Quick inspection

### Pattern 2: Prompt Inspection

```python
import dspy

class InspectableLM:
    """LM wrapper that logs prompts and responses."""

    def __init__(self, lm):
        self.lm = lm
        self.history = []

    def __call__(self, prompt, **kwargs):
        """Execute LM call and log details."""
        print("\n" + "="*80)
        print("PROMPT:")
        print("="*80)
        print(prompt)
        print("="*80)

        response = self.lm(prompt, **kwargs)

        print("\nRESPONSE:")
        print("="*80)
        print(response)
        print("="*80)

        # Save to history
        self.history.append({
            "prompt": prompt,
            "response": response,
            "kwargs": kwargs,
        })

        return response

    def __getattr__(self, name):
        """Delegate other attributes to underlying LM."""
        return getattr(self.lm, name)

# Usage
base_lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
inspectable_lm = InspectableLM(base_lm)
dspy.configure(lm=inspectable_lm)

# Now all LM calls will be logged
qa = dspy.ChainOfThought("question -> answer")
result = qa(question="What is 2+2?")

# Access prompt history
print("\n=== Prompt History ===")
for i, entry in enumerate(inspectable_lm.history):
    print(f"\nCall {i+1}:")
    print(f"Prompt length: {len(entry['prompt'])} chars")
    print(f"Response length: {len(str(entry['response']))} chars")
```

**Benefits**:
- See exact prompts DSPy generates
- Understand prompt structure
- Identify prompt issues
- Debug optimization effects

**When to use**:
- Understanding prompt construction
- Debugging unexpected outputs
- Analyzing optimization changes
- Learning DSPy prompt patterns

### Pattern 3: Execution Tracing

```python
import dspy
from datetime import datetime
import json

class TracingModule(dspy.Module):
    """Wrapper that traces module execution."""

    def __init__(self, module: dspy.Module, module_name: str):
        super().__init__()
        self.module = module
        self.module_name = module_name
        self.traces = []

    def forward(self, **kwargs):
        """Execute with tracing."""
        trace_entry = {
            "module": self.module_name,
            "timestamp": datetime.utcnow().isoformat(),
            "inputs": kwargs,
        }

        try:
            start_time = datetime.now()
            result = self.module(**kwargs)
            duration = (datetime.now() - start_time).total_seconds()

            trace_entry["outputs"] = {
                field: getattr(result, field)
                for field in result._fields
            }
            trace_entry["duration_seconds"] = duration
            trace_entry["status"] = "success"

        except Exception as e:
            trace_entry["error"] = str(e)
            trace_entry["status"] = "error"
            raise e

        finally:
            self.traces.append(trace_entry)
            self._print_trace(trace_entry)

        return result

    def _print_trace(self, trace_entry):
        """Pretty print trace entry."""
        print(f"\n{'='*80}")
        print(f"Module: {trace_entry['module']}")
        print(f"Status: {trace_entry['status']}")
        print(f"Duration: {trace_entry.get('duration_seconds', 0):.3f}s")
        print(f"Inputs: {trace_entry['inputs']}")
        if "outputs" in trace_entry:
            print(f"Outputs: {trace_entry['outputs']}")
        if "error" in trace_entry:
            print(f"Error: {trace_entry['error']}")
        print("="*80)

    def save_traces(self, filepath: str):
        """Save traces to file."""
        with open(filepath, "w") as f:
            json.dump(self.traces, f, indent=2)

# Usage
lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
dspy.configure(lm=lm)

# Wrap modules for tracing
qa_module = dspy.ChainOfThought("question -> answer")
traced_qa = TracingModule(qa_module, "qa_module")

# Execute with tracing
result = traced_qa(question="What is DSPy?")

# Save traces for analysis
traced_qa.save_traces("execution_traces.json")

# Analyze traces
print("\n=== Trace Analysis ===")
total_duration = sum(t.get("duration_seconds", 0) for t in traced_qa.traces)
print(f"Total execution time: {total_duration:.3f}s")
print(f"Number of calls: {len(traced_qa.traces)}")
print(f"Average call time: {total_duration / len(traced_qa.traces):.3f}s")
```

**Trace information**:
- Module names
- Input/output values
- Execution timestamps
- Duration per module
- Error details
- Call order

### Pattern 4: Pipeline Debugging

```python
import dspy

class DebugPipeline(dspy.Module):
    """Pipeline with intermediate checkpoints."""

    def __init__(self):
        super().__init__()
        self.step1 = dspy.Predict("question -> sub_questions: list[str]")
        self.step2 = dspy.ChainOfThought("question -> answer")
        self.step3 = dspy.Predict("answers: list[str] -> final_answer: str")

        # Checkpoint storage
        self.checkpoints = {}

    def _checkpoint(self, name: str, value):
        """Save checkpoint for debugging."""
        self.checkpoints[name] = value
        print(f"\n[CHECKPOINT: {name}]")
        print(f"Value: {value}")
        return value

    def forward(self, question):
        """Execute pipeline with checkpoints."""
        # Step 1: Decompose question
        decomp = self.step1(question=question)
        self._checkpoint("decomposition", decomp.sub_questions)

        # Step 2: Answer sub-questions
        sub_answers = []
        for i, sub_q in enumerate(decomp.sub_questions):
            ans = self.step2(question=sub_q)
            sub_answers.append(ans.answer)
            self._checkpoint(f"sub_answer_{i}", ans.answer)

        # Step 3: Synthesize final answer
        final = self.step3(answers=sub_answers)
        self._checkpoint("final_answer", final.final_answer)

        return dspy.Prediction(
            sub_questions=decomp.sub_questions,
            sub_answers=sub_answers,
            answer=final.final_answer,
        )

    def print_checkpoints(self):
        """Print all checkpoints."""
        print("\n=== Pipeline Checkpoints ===")
        for name, value in self.checkpoints.items():
            print(f"{name}: {value}")

# Usage
lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
dspy.configure(lm=lm)

pipeline = DebugPipeline()
result = pipeline(question="Compare Python and JavaScript")

# Inspect checkpoints
pipeline.print_checkpoints()

# Check specific checkpoint
if "decomposition" in pipeline.checkpoints:
    print(f"\nDecomposition produced {len(pipeline.checkpoints['decomposition'])} sub-questions")
```

**Checkpoint strategy**:
- After each major step
- Before error-prone operations
- At data transformations
- Before expensive LM calls

**When to use**:
- Multi-step pipelines
- Complex workflows
- Identifying failure points
- Understanding data flow

### Pattern 5: Performance Profiling

```python
import dspy
import time
from dataclasses import dataclass
from typing import List

@dataclass
class ProfileEntry:
    """Profiling data for a module call."""
    module_name: str
    duration_seconds: float
    prompt_tokens: int
    completion_tokens: int
    estimated_cost_usd: float

class ProfilingLM:
    """LM wrapper that tracks performance metrics."""

    def __init__(self, lm, model_name: str = "gpt-4o-mini"):
        self.lm = lm
        self.model_name = model_name
        self.profiles: List[ProfileEntry] = []

        # Token costs (per million tokens)
        self.token_costs = {
            "gpt-4o-mini": {"prompt": 0.15, "completion": 0.60},
            "gpt-4o": {"prompt": 2.50, "completion": 10.00},
            "gpt-4": {"prompt": 30.00, "completion": 60.00},
        }

    def __call__(self, prompt, **kwargs):
        """Execute with profiling."""
        start = time.time()
        response = self.lm(prompt, **kwargs)
        duration = time.time() - start

        # Estimate tokens (rough approximation)
        prompt_tokens = len(prompt.split()) * 1.3  # ~1.3 tokens per word
        completion_tokens = len(str(response).split()) * 1.3

        # Calculate cost
        costs = self.token_costs.get(self.model_name, {"prompt": 0, "completion": 0})
        estimated_cost = (
            (prompt_tokens * costs["prompt"] / 1_000_000) +
            (completion_tokens * costs["completion"] / 1_000_000)
        )

        # Record profile
        self.profiles.append(ProfileEntry(
            module_name=self.model_name,
            duration_seconds=duration,
            prompt_tokens=int(prompt_tokens),
            completion_tokens=int(completion_tokens),
            estimated_cost_usd=estimated_cost,
        ))

        return response

    def get_profile_summary(self):
        """Get profiling summary."""
        if not self.profiles:
            return "No profiling data"

        total_duration = sum(p.duration_seconds for p in self.profiles)
        total_prompt_tokens = sum(p.prompt_tokens for p in self.profiles)
        total_completion_tokens = sum(p.completion_tokens for p in self.profiles)
        total_cost = sum(p.estimated_cost_usd for p in self.profiles)

        return f"""
=== Profiling Summary ===
Total calls: {len(self.profiles)}
Total duration: {total_duration:.2f}s
Average duration: {total_duration / len(self.profiles):.2f}s
Total prompt tokens: {total_prompt_tokens:,}
Total completion tokens: {total_completion_tokens:,}
Total tokens: {total_prompt_tokens + total_completion_tokens:,}
Estimated total cost: ${total_cost:.4f}
Average cost per call: ${total_cost / len(self.profiles):.4f}
"""

    def __getattr__(self, name):
        return getattr(self.lm, name)

# Usage
base_lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
profiling_lm = ProfilingLM(base_lm, model_name="gpt-4o-mini")
dspy.configure(lm=profiling_lm)

# Execute some operations
qa = dspy.ChainOfThought("question -> answer")

for question in ["What is 2+2?", "Why is sky blue?", "Explain quantum computing"]:
    result = qa(question=question)

# View profiling results
print(profiling_lm.get_profile_summary())

# Identify expensive calls
print("\n=== Most Expensive Calls ===")
sorted_profiles = sorted(profiling_lm.profiles, key=lambda p: p.estimated_cost_usd, reverse=True)
for i, profile in enumerate(sorted_profiles[:3], 1):
    print(f"{i}. Duration: {profile.duration_seconds:.2f}s, Cost: ${profile.estimated_cost_usd:.4f}")
```

**Metrics tracked**:
- Latency per call
- Token usage
- Cost per call
- Total cost
- Call frequency

**Optimization opportunities**:
- High-cost calls → optimize prompts
- Slow calls → investigate bottlenecks
- Many calls → cache or batch

### Pattern 6: Error Diagnosis

```python
import dspy
from typing import Optional
import traceback

class DiagnosticModule(dspy.Module):
    """Module with comprehensive error diagnostics."""

    def __init__(self, signature: str):
        super().__init__()
        self.predictor = dspy.ChainOfThought(signature)
        self.error_history = []

    def forward(self, **kwargs):
        """Execute with error diagnostics."""
        try:
            return self.predictor(**kwargs)

        except Exception as e:
            # Capture detailed error information
            error_info = {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "inputs": kwargs,
                "traceback": traceback.format_exc(),
            }

            # Add to history
            self.error_history.append(error_info)

            # Print detailed diagnostics
            self._print_diagnostics(error_info)

            # Re-raise
            raise e

    def _print_diagnostics(self, error_info):
        """Print error diagnostics."""
        print("\n" + "="*80)
        print("ERROR DIAGNOSTICS")
        print("="*80)
        print(f"Error Type: {error_info['error_type']}")
        print(f"Message: {error_info['error_message']}")
        print("\nInputs:")
        for key, value in error_info['inputs'].items():
            print(f"  {key}: {value}")
        print("\nTraceback:")
        print(error_info['traceback'])
        print("="*80)

        # Suggest fixes based on error type
        self._suggest_fixes(error_info)

    def _suggest_fixes(self, error_info):
        """Suggest potential fixes based on error."""
        error_type = error_info['error_type']

        suggestions = {
            "KeyError": [
                "Check if all required signature fields are present",
                "Verify input field names match signature",
                "Check for typos in field names",
            ],
            "ValueError": [
                "Verify input types match signature expectations",
                "Check for empty or malformed inputs",
                "Validate input data format",
            ],
            "TimeoutError": [
                "Increase timeout setting",
                "Check network connectivity",
                "Verify API endpoint is responsive",
            ],
            "RateLimitError": [
                "Reduce request rate",
                "Add exponential backoff",
                "Check API quota",
            ],
        }

        if error_type in suggestions:
            print("\nSuggested fixes:")
            for i, suggestion in enumerate(suggestions[error_type], 1):
                print(f"{i}. {suggestion}")

# Usage
lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
dspy.configure(lm=lm)

diagnostic_module = DiagnosticModule("question -> answer")

# Test with various inputs
try:
    result = diagnostic_module(question="What is DSPy?")
    print("Success!")
except Exception:
    print("Error handled with diagnostics")

# Test with problematic input
try:
    result = diagnostic_module(wrong_field="This will fail")
except Exception:
    print("Error diagnosed")

# Review error history
print(f"\nTotal errors: {len(diagnostic_module.error_history)}")
```

**Diagnostic information**:
- Error type and message
- Input values that caused error
- Full stack trace
- Suggested fixes
- Error patterns

### Pattern 7: Interactive Debugging

```python
import dspy
from typing import Optional

class InteractiveDebugger(dspy.Module):
    """Interactive debugger for DSPy modules."""

    def __init__(self, module: dspy.Module, breakpoints: list = None):
        super().__init__()
        self.module = module
        self.breakpoints = breakpoints or []
        self.step_mode = False
        self.variables = {}

    def forward(self, **kwargs):
        """Execute with interactive debugging."""
        self.variables["inputs"] = kwargs

        # Pre-execution breakpoint
        if "pre" in self.breakpoints:
            self._breakpoint("pre", kwargs)

        # Execute module
        result = self.module(**kwargs)

        self.variables["outputs"] = {
            field: getattr(result, field)
            for field in result._fields
        }

        # Post-execution breakpoint
        if "post" in self.breakpoints:
            self._breakpoint("post", self.variables["outputs"])

        return result

    def _breakpoint(self, name: str, context: dict):
        """Interactive breakpoint."""
        print(f"\n{'='*80}")
        print(f"BREAKPOINT: {name}")
        print("="*80)
        print("Context:")
        for key, value in context.items():
            print(f"  {key}: {value}")
        print("\nCommands: (c)ontinue, (i)nspect, (v)ariables, (s)tep, (q)uit")

        while True:
            command = input(f"{name}> ").strip().lower()

            if command == "c":
                break
            elif command == "i":
                print("\nDetailed Inspection:")
                print(context)
            elif command == "v":
                print("\nAll Variables:")
                print(self.variables)
            elif command == "s":
                self.step_mode = True
                break
            elif command == "q":
                raise KeyboardInterrupt("User quit debugging")
            else:
                print("Unknown command")

# Usage (interactive)
lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
dspy.configure(lm=lm)

qa = dspy.ChainOfThought("question -> answer")
debugger = InteractiveDebugger(qa, breakpoints=["pre", "post"])

# Will stop at breakpoints for interactive inspection
# result = debugger(question="What is DSPy?")
```

**Interactive commands**:
- Continue (c): Resume execution
- Inspect (i): View detailed context
- Variables (v): View all variables
- Step (s): Enable step mode
- Quit (q): Exit debugging

**When to use**:
- Complex debugging scenarios
- Understanding execution flow
- Inspecting intermediate values
- Learning DSPy behavior

### Pattern 8: Visualization Tools

```python
import dspy
from typing import List, Dict
import json

class ExecutionVisualizer:
    """Visualize DSPy program execution."""

    def __init__(self):
        self.nodes: List[Dict] = []
        self.edges: List[Dict] = []

    def add_node(self, node_id: str, label: str, node_type: str):
        """Add node to graph."""
        self.nodes.append({
            "id": node_id,
            "label": label,
            "type": node_type,
        })

    def add_edge(self, from_id: str, to_id: str, label: str = ""):
        """Add edge to graph."""
        self.edges.append({
            "from": from_id,
            "to": to_id,
            "label": label,
        })

    def to_mermaid(self) -> str:
        """Generate Mermaid diagram."""
        lines = ["graph TD"]

        # Add nodes
        for node in self.nodes:
            node_id = node["id"]
            label = node["label"]
            node_type = node["type"]

            # Style based on type
            if node_type == "input":
                lines.append(f'  {node_id}["{label}"]')
            elif node_type == "module":
                lines.append(f'  {node_id}["{label}"]')
            elif node_type == "output":
                lines.append(f'  {node_id}("{label}")')

        # Add edges
        for edge in self.edges:
            from_id = edge["from"]
            to_id = edge["to"]
            label = edge.get("label", "")
            lines.append(f'  {from_id} -->|{label}| {to_id}')

        return "\n".join(lines)

    def save_mermaid(self, filepath: str):
        """Save Mermaid diagram to file."""
        with open(filepath, "w") as f:
            f.write(self.to_mermaid())

class VisualizablePipeline(dspy.Module):
    """Pipeline that generates execution visualization."""

    def __init__(self):
        super().__init__()
        self.step1 = dspy.Predict("question -> sub_questions: list[str]")
        self.step2 = dspy.ChainOfThought("question -> answer")
        self.step3 = dspy.Predict("answers: list[str] -> final_answer: str")

        self.visualizer = ExecutionVisualizer()

    def forward(self, question):
        """Execute and generate visualization."""
        # Add input node
        self.visualizer.add_node("input", f"Q: {question[:30]}...", "input")

        # Step 1
        self.visualizer.add_node("step1", "Decompose", "module")
        self.visualizer.add_edge("input", "step1")
        decomp = self.step1(question=question)

        # Step 2 (for each sub-question)
        sub_answers = []
        for i, sub_q in enumerate(decomp.sub_questions):
            node_id = f"step2_{i}"
            self.visualizer.add_node(node_id, f"Answer {i+1}", "module")
            self.visualizer.add_edge("step1", node_id, sub_q[:20])
            ans = self.step2(question=sub_q)
            sub_answers.append(ans.answer)

        # Step 3
        self.visualizer.add_node("step3", "Synthesize", "module")
        for i in range(len(sub_answers)):
            self.visualizer.add_edge(f"step2_{i}", "step3")
        final = self.step3(answers=sub_answers)

        # Output node
        self.visualizer.add_node("output", f"A: {final.final_answer[:30]}...", "output")
        self.visualizer.add_edge("step3", "output")

        return dspy.Prediction(answer=final.final_answer)

# Usage
lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
dspy.configure(lm=lm)

pipeline = VisualizablePipeline()
result = pipeline(question="Compare Python and JavaScript")

# Save visualization
pipeline.visualizer.save_mermaid("execution_graph.mmd")

# Print Mermaid diagram
print(pipeline.visualizer.to_mermaid())
```

**Visualization types**:
- Execution flow graphs
- Module dependency graphs
- Data flow diagrams
- Performance heatmaps
- Token usage charts

**Tools**:
- Mermaid for flowcharts
- Graphviz for complex graphs
- Plotly for interactive charts
- Matplotlib for static plots

---

## Quick Reference

### Quick Debugging Commands

```python
# Inspect result fields
print(result._fields)

# View all attributes
print(vars(result))

# Check for specific field
hasattr(result, "answer")

# View LM history (if available)
# dspy.inspect_history()

# Enable detailed logging
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Common Issues and Solutions

| Issue | Likely Cause | Solution |
|-------|-------------|----------|
| Empty output | LM failed to parse | Inspect prompt, simplify signature |
| KeyError | Missing field | Check signature field names |
| Timeout | LM too slow | Reduce max_tokens, use faster model |
| Unexpected output | Wrong prompt | Use InspectableLM to view prompt |
| High cost | Too many tokens | Profile and optimize prompts |
| Non-deterministic | temperature > 0 | Set temperature=0.0 |

### Debugging Checklist

```
Before debugging:
✅ Reproduce the issue consistently
✅ Set temperature=0 for deterministic behavior
✅ Simplify to minimal failing example
✅ Check recent code changes

During debugging:
✅ Inspect output structure
✅ View generated prompts
✅ Check intermediate results
✅ Profile performance
✅ Review error traces

After fixing:
✅ Add regression test
✅ Document the issue
✅ Update error handling
✅ Monitor in production
```

### Useful Libraries

```bash
# Install debugging tools
pip install ipdb  # Interactive debugger
pip install snoop  # Print debugging
pip install icecream  # Debug printing
pip install py-spy  # Performance profiler
pip install memray  # Memory profiler
```

---

## Anti-Patterns

❌ **No logging or tracing**: Flying blind
```python
# Bad - no visibility
result = module(question=question)
```
✅ Add tracing or logging:
```python
# Good
traced_module = TracingModule(module, "my_module")
result = traced_module(question=question)
```

❌ **Not inspecting prompts**: Missing obvious issues
```python
# Bad - don't know what prompts look like
```
✅ Use InspectableLM:
```python
# Good
inspectable_lm = InspectableLM(lm)
dspy.configure(lm=inspectable_lm)
```

❌ **Ignoring performance**: Unexpected costs
```python
# Bad - no idea about cost or speed
```
✅ Profile performance:
```python
# Good
profiling_lm = ProfilingLM(lm)
dspy.configure(lm=profiling_lm)
# ... check profiling_lm.get_profile_summary()
```

❌ **No error context**: Can't reproduce issues
```python
# Bad
try:
    result = module(question=question)
except Exception:
    pass  # What happened?
```
✅ Capture context:
```python
# Good
try:
    result = module(question=question)
except Exception as e:
    print(f"Error with question: {question}")
    print(f"Error: {e}")
    print(f"Traceback: {traceback.format_exc()}")
    raise
```

---

## Related Skills

- `dspy-testing.md` - Testing strategies for debugging
- `dspy-production.md` - Production debugging and monitoring
- `dspy-evaluation.md` - Evaluating program quality
- `python-debugging.md` - General Python debugging
- `performance-profiling.md` - Performance optimization

---

**Last Updated**: 2025-10-30
**Format Version**: 1.0 (Atomic)
