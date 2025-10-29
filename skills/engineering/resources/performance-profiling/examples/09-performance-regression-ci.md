# Example 9: Performance Regression Detection in CI/CD

This example demonstrates automated performance regression detection integrated into CI/CD pipelines.

## Overview

**Goals**:
- Detect performance regressions before merge
- Block PRs with significant slowdowns
- Track performance trends over time
- Provide actionable feedback to developers

**Components**:
1. Benchmark suite
2. Performance baseline storage
3. Automated comparison
4. Visualization and reporting
5. CI/CD integration

## Benchmark Suite

### Python (pytest-benchmark)

```python
# test_performance.py
import pytest
import time

def fibonacci_recursive(n):
    if n <= 1:
        return n
    return fibonacci_recursive(n - 1) + fibonacci_recursive(n - 2)

def fibonacci_iterative(n):
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a

class TestPerformance:
    def test_fibonacci_recursive(self, benchmark):
        """Benchmark recursive Fibonacci."""
        result = benchmark(fibonacci_recursive, 20)
        assert result == 6765

    def test_fibonacci_iterative(self, benchmark):
        """Benchmark iterative Fibonacci."""
        result = benchmark(fibonacci_iterative, 1000)
        assert result > 0

    def test_data_processing(self, benchmark):
        """Benchmark data processing pipeline."""
        def process_data():
            data = list(range(10000))
            return sum(x ** 2 for x in data)

        result = benchmark(process_data)
        assert result > 0
```

```bash
# Install dependencies
pip install pytest pytest-benchmark

# Run benchmarks
pytest test_performance.py --benchmark-only --benchmark-json=results.json

# Compare with baseline
pytest-benchmark compare 0001 0002 --group-by=name
```

### Go (testing package)

```go
// fibonacci_test.go
package main

import (
    "testing"
)

func BenchmarkFibonacciRecursive(b *testing.B) {
    for i := 0; i < b.N; i++ {
        fibonacciRecursive(20)
    }
}

func BenchmarkFibonacciIterative(b *testing.B) {
    for i := 0; i < b.N; i++ {
        fibonacciIterative(1000)
    }
}

func BenchmarkDataProcessing(b *testing.B) {
    for i := 0; i < b.N; i++ {
        sum := 0
        for j := 0; j < 10000; j++ {
            sum += j * j
        }
        _ = sum
    }
}
```

```bash
# Run benchmarks
go test -bench=. -benchmem -benchtime=10s -count=5 | tee benchmark.txt

# Compare with baseline
benchstat baseline.txt current.txt
```

### Rust (criterion)

```rust
// benches/benchmark.rs
use criterion::{black_box, criterion_group, criterion_main, Criterion};

fn fibonacci_recursive(n: u64) -> u64 {
    match n {
        0 => 0,
        1 => 1,
        _ => fibonacci_recursive(n - 1) + fibonacci_recursive(n - 2),
    }
}

fn criterion_benchmark(c: &mut Criterion) {
    c.bench_function("fibonacci 20", |b| {
        b.iter(|| fibonacci_recursive(black_box(20)))
    });

    c.bench_function("data processing", |b| {
        b.iter(|| {
            let sum: u64 = (0..10000).map(|x| x * x).sum();
            black_box(sum)
        })
    });
}

criterion_group!(benches, criterion_benchmark);
criterion_main!(benches);
```

```bash
# Run benchmarks
cargo bench

# Results in target/criterion/
```

## GitHub Actions Integration

### Complete Workflow

```yaml
# .github/workflows/performance.yml
name: Performance Regression Check

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  benchmark:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write  # To comment on PRs

    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0  # Fetch all history for comparison

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install pytest pytest-benchmark
          pip install -r requirements.txt

      - name: Download baseline benchmark
        id: download-baseline
        continue-on-error: true
        uses: actions/download-artifact@v3
        with:
          name: benchmark-baseline
          path: baseline/

      - name: Run benchmarks
        run: |
          pytest test_performance.py \
            --benchmark-only \
            --benchmark-json=current.json \
            --benchmark-min-rounds=10

      - name: Compare with baseline
        id: compare
        if: steps.download-baseline.outcome == 'success'
        run: |
          python scripts/compare_benchmarks.py \
            baseline/benchmark.json \
            current.json \
            --threshold=0.05 \
            --output=comparison.json

      - name: Post PR comment
        if: github.event_name == 'pull_request' && steps.compare.outcome == 'success'
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const comparison = JSON.parse(fs.readFileSync('comparison.json', 'utf8'));

            let body = '## Performance Benchmark Results\n\n';

            if (comparison.regressions.length > 0) {
              body += '### ⚠️ Regressions Detected\n\n';
              body += '| Benchmark | Baseline | Current | Change |\n';
              body += '|-----------|----------|---------|--------|\n';
              for (const reg of comparison.regressions) {
                body += `| ${reg.name} | ${reg.baseline}ms | ${reg.current}ms | ${reg.change}% |\n`;
              }
              body += '\n';
            }

            if (comparison.improvements.length > 0) {
              body += '### ✅ Improvements\n\n';
              body += '| Benchmark | Baseline | Current | Change |\n';
              body += '|-----------|----------|---------|--------|\n';
              for (const imp of comparison.improvements) {
                body += `| ${imp.name} | ${imp.baseline}ms | ${imp.current}ms | ${imp.change}% |\n`;
              }
            }

            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: body
            });

      - name: Fail on regression
        if: steps.compare.outcome == 'success'
        run: |
          python -c "
          import json
          with open('comparison.json') as f:
              data = json.load(f)
          if data['regressions']:
              print(f\"❌ {len(data['regressions'])} performance regression(s) detected\")
              exit(1)
          print('✅ No performance regressions')
          "

      - name: Upload current benchmark
        if: github.event_name == 'push' && github.ref == 'refs/heads/main'
        uses: actions/upload-artifact@v3
        with:
          name: benchmark-baseline
          path: current.json
```

### Comparison Script

```python
#!/usr/bin/env python3
# scripts/compare_benchmarks.py

import argparse
import json
import sys
from typing import Dict, List, Tuple


def load_benchmark(file_path: str) -> Dict:
    """Load pytest-benchmark JSON results."""
    with open(file_path) as f:
        return json.load(f)


def compare_benchmarks(
    baseline: Dict,
    current: Dict,
    threshold: float = 0.05
) -> Tuple[List[Dict], List[Dict]]:
    """
    Compare two benchmark results.

    Args:
        baseline: Baseline benchmark data
        current: Current benchmark data
        threshold: Regression threshold (0.05 = 5%)

    Returns:
        Tuple of (regressions, improvements)
    """
    regressions = []
    improvements = []

    baseline_by_name = {
        bench['name']: bench for bench in baseline['benchmarks']
    }

    for bench in current['benchmarks']:
        name = bench['name']

        if name not in baseline_by_name:
            continue

        baseline_bench = baseline_by_name[name]

        # Compare mean time
        baseline_mean = baseline_bench['stats']['mean']
        current_mean = bench['stats']['mean']

        change_percent = ((current_mean - baseline_mean) / baseline_mean) * 100

        if change_percent > (threshold * 100):
            regressions.append({
                'name': name,
                'baseline': round(baseline_mean * 1000, 3),  # Convert to ms
                'current': round(current_mean * 1000, 3),
                'change': round(change_percent, 2)
            })
        elif change_percent < -(threshold * 100):
            improvements.append({
                'name': name,
                'baseline': round(baseline_mean * 1000, 3),
                'current': round(current_mean * 1000, 3),
                'change': round(change_percent, 2)
            })

    return regressions, improvements


def main():
    parser = argparse.ArgumentParser(
        description='Compare benchmark results'
    )
    parser.add_argument('baseline', help='Baseline benchmark file')
    parser.add_argument('current', help='Current benchmark file')
    parser.add_argument(
        '--threshold',
        type=float,
        default=0.05,
        help='Regression threshold (default: 0.05 = 5%%)'
    )
    parser.add_argument(
        '--output',
        help='Output JSON file'
    )

    args = parser.parse_args()

    baseline = load_benchmark(args.baseline)
    current = load_benchmark(args.current)

    regressions, improvements = compare_benchmarks(
        baseline, current, args.threshold
    )

    result = {
        'regressions': regressions,
        'improvements': improvements
    }

    if args.output:
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2)

    # Print summary
    print(f"Regressions: {len(regressions)}")
    print(f"Improvements: {len(improvements)}")

    if regressions:
        print("\n⚠️ Performance Regressions:")
        for reg in regressions:
            print(f"  {reg['name']}: {reg['baseline']}ms → {reg['current']}ms ({reg['change']:+.2f}%)")

    if improvements:
        print("\n✅ Performance Improvements:")
        for imp in improvements:
            print(f"  {imp['name']}: {imp['baseline']}ms → {imp['current']}ms ({imp['change']:+.2f}%)")

    return 0 if not regressions else 1


if __name__ == '__main__':
    sys.exit(main())
```

## GitLab CI Integration

```yaml
# .gitlab-ci.yml
stages:
  - test
  - benchmark
  - report

benchmark:
  stage: benchmark
  image: python:3.11
  script:
    - pip install pytest pytest-benchmark
    - pytest test_performance.py --benchmark-only --benchmark-json=current.json
  artifacts:
    paths:
      - current.json
    reports:
      performance: current.json

compare:
  stage: report
  image: python:3.11
  script:
    - |
      if [ -f baseline.json ]; then
        python scripts/compare_benchmarks.py baseline.json current.json --threshold=0.05
      else
        echo "No baseline found, skipping comparison"
      fi
  artifacts:
    paths:
      - comparison.json
  allow_failure: false
```

## Performance Tracking Dashboard

### Store Historical Data

```python
# scripts/store_benchmark.py
import json
import os
from datetime import datetime
from pathlib import Path

def store_benchmark(benchmark_file: str, output_dir: str):
    """Store benchmark with timestamp."""
    with open(benchmark_file) as f:
        data = json.load(f)

    timestamp = datetime.now().isoformat()
    commit = os.environ.get('GITHUB_SHA', 'unknown')
    branch = os.environ.get('GITHUB_REF_NAME', 'unknown')

    output = {
        'timestamp': timestamp,
        'commit': commit,
        'branch': branch,
        'benchmarks': data['benchmarks']
    }

    output_path = Path(output_dir) / f"benchmark_{commit[:8]}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"Stored benchmark: {output_path}")
```

### Visualize Trends

```python
# scripts/visualize_trends.py
import json
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime

def visualize_trends(benchmark_dir: str, output_file: str):
    """Generate performance trend graphs."""
    benchmarks = []

    for file in sorted(Path(benchmark_dir).glob("benchmark_*.json")):
        with open(file) as f:
            benchmarks.append(json.load(f))

    # Group by benchmark name
    trends = {}
    for bench_set in benchmarks:
        timestamp = datetime.fromisoformat(bench_set['timestamp'])

        for bench in bench_set['benchmarks']:
            name = bench['name']
            mean = bench['stats']['mean'] * 1000  # Convert to ms

            if name not in trends:
                trends[name] = {'timestamps': [], 'values': []}

            trends[name]['timestamps'].append(timestamp)
            trends[name]['values'].append(mean)

    # Plot
    fig, axes = plt.subplots(len(trends), 1, figsize=(12, 4 * len(trends)))

    if len(trends) == 1:
        axes = [axes]

    for ax, (name, data) in zip(axes, trends.items()):
        ax.plot(data['timestamps'], data['values'], marker='o')
        ax.set_title(name)
        ax.set_xlabel('Date')
        ax.set_ylabel('Time (ms)')
        ax.grid(True)

    plt.tight_layout()
    plt.savefig(output_file)
    print(f"Saved trend graph: {output_file}")
```

## Best Practices

### 1. Stable Benchmark Environment

```yaml
# Use consistent hardware
runs-on: ubuntu-latest  # ✓ Consistent
# runs-on: self-hosted  # ❌ May vary

# Pin dependencies
python-version: '3.11.5'  # ✓ Specific
# python-version: '3.x'   # ❌ May change

# Minimize noise
- name: Disable CPU frequency scaling
  run: |
    echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
```

### 2. Multiple Iterations

```python
# ✓ Multiple runs for statistical significance
pytest test_performance.py --benchmark-min-rounds=10

# ❌ Single run (unreliable)
pytest test_performance.py --benchmark-min-rounds=1
```

### 3. Reasonable Thresholds

```
Threshold too strict (1%):   False positives, noise
✓ Recommended (5%):          Balance between sensitivity and noise
Threshold too loose (20%):   Miss real regressions
```

### 4. Warm-up Runs

```python
def test_with_warmup(benchmark):
    """Benchmark with warm-up to reduce JIT noise."""
    benchmark.pedantic(
        target_function,
        rounds=10,
        warmup_rounds=5  # Discard first 5 runs
    )
```

## Troubleshooting

### Issue: Flaky benchmarks

```python
# Increase min rounds
pytest --benchmark-min-rounds=20

# Check variance
pytest --benchmark-only --benchmark-compare-fail=mean:5%
```

### Issue: Missing baseline

```bash
# First run on main branch creates baseline
git checkout main
pytest --benchmark-only --benchmark-autosave
```

### Issue: PR comment not posted

```yaml
# Ensure permissions
permissions:
  pull-requests: write  # Required for commenting
```

## Summary

- **Automated Detection**: Catch regressions before merge
- **CI/CD Integration**: GitHub Actions, GitLab CI, Jenkins
- **Threshold**: 5% typical, adjust for noise tolerance
- **Blocking**: Fail CI on significant regressions
- **Tracking**: Store historical data for trend analysis
- **Reporting**: Post results as PR comments
- **Best Practices**: Stable environment, multiple iterations, warm-up
