# Example 1: Python cProfile with SnakeViz Visualization

This example demonstrates CPU profiling of Python applications using the built-in cProfile module with SnakeViz for interactive visualization.

## Prerequisites

```bash
pip install snakeviz
```

## Sample Application

```python
# fibonacci_app.py
def fibonacci_recursive(n):
    """Inefficient recursive Fibonacci."""
    if n <= 1:
        return n
    return fibonacci_recursive(n - 1) + fibonacci_recursive(n - 2)

def fibonacci_iterative(n):
    """Efficient iterative Fibonacci."""
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b

def process_data(data):
    """Simulate data processing."""
    results = []
    for item in data:
        # Expensive computation
        results.append(fibonacci_recursive(item % 25))
    return results

def main():
    data = list(range(1000))

    # Inefficient version
    results1 = process_data(data)

    # More efficient version
    results2 = [fibonacci_iterative(x % 25) for x in data]

    print(f"Processed {len(results1)} items")

if __name__ == "__main__":
    main()
```

## Profiling with cProfile

### Method 1: Command-line profiling

```bash
# Profile and save to file
python -m cProfile -o profile.stats fibonacci_app.py

# View with pstats
python -m pstats profile.stats
# In pstats shell:
# > sort cumulative
# > stats 20
# > quit

# Or one-liner
python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative').print_stats(20)"
```

### Method 2: Programmatic profiling

```python
# fibonacci_profiled.py
import cProfile
import pstats
from fibonacci_app import main

# Profile the main function
profiler = cProfile.Profile()
profiler.enable()

main()

profiler.disable()

# Print statistics
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)

# Save for later analysis
stats.dump_stats('profile.stats')
```

## Visualization with SnakeViz

```bash
# Launch interactive visualization
snakeviz profile.stats

# Opens browser with:
# - Icicle chart (hierarchical view)
# - Sunburst chart (radial view)
# - Function table (sortable statistics)
```

## Interpreting Results

### Expected Output (pstats)

```
   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
        1    0.000    0.000    2.345    2.345 fibonacci_app.py:1(<module>)
        1    0.012    0.012    2.345    2.345 fibonacci_app.py:25(main)
        1    0.089    0.089    2.234    2.234 fibonacci_app.py:13(process_data)
   150050    2.145    0.000    2.145    0.000 fibonacci_app.py:1(fibonacci_recursive)
        1    0.000    0.000    0.098    0.098 <listcomp>:1(<listcomp>)
     1000    0.098    0.000    0.098    0.000 fibonacci_app.py:7(fibonacci_iterative)
```

### Key Insights

1. **fibonacci_recursive**: 150,050 calls, 2.145s total
   - Exponential time complexity
   - Hot function consuming 91% of runtime

2. **process_data**: Wrapper function, 89ms overhead
   - List building overhead

3. **fibonacci_iterative**: 1,000 calls, 98ms total
   - 22x faster than recursive version
   - Linear time complexity

### Optimization Opportunities

1. **Replace recursive Fibonacci** with iterative version
   - Speedup: ~22x
   - Impact: 91% of runtime

2. **Memoization** for recursive version (if needed)
   ```python
   from functools import lru_cache

   @lru_cache(maxsize=None)
   def fibonacci_recursive(n):
       if n <= 1:
           return n
       return fibonacci_recursive(n - 1) + fibonacci_recursive(n - 2)
   ```

3. **List comprehension** instead of loop
   - Already done in efficient version
   - Slight performance improvement

## SnakeViz Navigation

### Icicle Chart
- **Width**: Time spent in function
- **Color**: Different functions
- **Click**: Zoom into function's callees
- **Hover**: See detailed statistics

### Sunburst Chart
- **Radial segments**: Call hierarchy
- **Angle**: Proportion of time
- **Center**: Root function
- **Click**: Navigate hierarchy

### Function Table
- Sort by: tottime, cumtime, ncalls
- Filter by: function name
- Export: CSV for further analysis

## Best Practices

1. **Profile representative workload**: Use realistic data size
2. **Run multiple times**: Account for variance (average results)
3. **Focus on cumtime**: Total time including callees
4. **Identify hotspots**: Functions >5% of runtime
5. **Verify optimizations**: Profile before and after

## CI Integration

```yaml
# .github/workflows/profile.yml
name: Profile Performance

on: [pull_request]

jobs:
  profile:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install snakeviz

      - name: Profile application
        run: |
          python -m cProfile -o profile.stats fibonacci_app.py
          python -m pstats profile.stats <<EOF
          sort cumulative
          stats 10
          quit
          EOF

      - name: Upload profile
        uses: actions/upload-artifact@v3
        with:
          name: profile-stats
          path: profile.stats
```

## Troubleshooting

### Issue: High overhead from profiling
**Solution**: Use sampling profiler (py-spy) instead
```bash
py-spy record -o profile.svg --format flamegraph -- python fibonacci_app.py
```

### Issue: Cannot profile C extensions
**Solution**: C extensions show as built-in, use line_profiler for Python code
```python
from line_profiler import LineProfiler

lp = LineProfiler()
lp.add_function(process_data)
lp.run('main()')
lp.print_stats()
```

### Issue: Profile file too large
**Solution**: Filter functions or reduce workload
```python
# Only profile specific functions
profiler.enable()
process_data(data)  # Only profile this
profiler.disable()
```

## Summary

- **cProfile**: Built-in, deterministic profiling
- **SnakeViz**: Interactive visualization
- **Use Cases**: Development, identifying hotspots
- **Overhead**: 5-20% (acceptable for development)
- **Alternative**: py-spy for production (lower overhead)
