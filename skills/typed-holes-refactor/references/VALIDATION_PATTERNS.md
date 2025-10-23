---
name: validation-patterns
description: Reference guide for test patterns to validate hole resolutions including characterization tests, property tests, and integration tests. Use as reference when validating refactoring steps.
---

# Validation Patterns

Test patterns for validating hole resolutions.

## Characterization Tests

Capture current behavior as safety net.

### Pattern: API Contract Preservation

```python
# tests/characterization/test_api_contracts.py
import pytest
import json
from pathlib import Path

class TestAPIContracts:
    @pytest.fixture(scope="session")
    def baseline_dir(self):
        return Path("tests/characterization/baselines")
    
    def test_all_public_apis(self, baseline_dir):
        """Every public API preserves exact behavior"""
        apis = discover_public_apis()
        
        for api in apis:
            test_cases = load_test_cases(api)
            
            for case in test_cases:
                # Load baseline result
                baseline_file = baseline_dir / f"{api}_{case.id}.json"
                if baseline_file.exists():
                    baseline = json.loads(baseline_file.read_text())
                else:
                    # First run - save baseline
                    result = execute_api(api, case)
                    baseline_file.write_text(json.dumps(result, indent=2))
                    baseline = result
                
                # Compare current result to baseline
                current = execute_api(api, case)
                assert current == baseline, (
                    f"API {api} behavior changed for {case.id}\n"
                    f"Expected: {baseline}\n"
                    f"Got: {current}"
                )
```

### Pattern: Performance Baseline

```python
# tests/characterization/test_performance.py
import pytest
import time
import statistics

class TestPerformanceBaselines:
    ITERATIONS = 100
    TOLERANCE = 1.2  # Allow 20% slowdown
    
    @pytest.fixture(scope="session")
    def baselines(self):
        path = Path("tests/characterization/perf_baselines.json")
        if path.exists():
            return json.loads(path.read_text())
        return {}
    
    def measure_operation(self, operation, *args):
        """Measure operation timing over multiple iterations"""
        times = []
        for _ in range(self.ITERATIONS):
            start = time.perf_counter()
            operation(*args)
            end = time.perf_counter()
            times.append(end - start)
        
        return {
            "p50": statistics.median(times),
            "p99": statistics.quantiles(times, n=100)[-1],
            "mean": statistics.mean(times),
            "stdev": statistics.stdev(times)
        }
    
    def test_critical_operations(self, baselines):
        """Ensure critical operations don't regress"""
        operations = [
            ("parse_prompt", parse_prompt, sample_prompt),
            ("generate_ir", generate_ir, sample_input),
            ("execute_code", execute_code, sample_code),
        ]
        
        for name, operation, test_data in operations:
            current = self.measure_operation(operation, test_data)
            
            if name in baselines:
                baseline = baselines[name]
                # Check p99 latency doesn't exceed tolerance
                assert current["p99"] <= baseline["p99"] * self.TOLERANCE, (
                    f"{name} performance regression\n"
                    f"Baseline p99: {baseline['p99']:.4f}s\n"
                    f"Current p99: {current['p99']:.4f}s\n"
                    f"Increase: {(current['p99'] / baseline['p99']):.2%}"
                )
            else:
                # First run - save baseline
                baselines[name] = current
```

## Resolution Validation Tests

Verify hole resolution meets criteria.

### Pattern: Architecture Validation

```python
# tests/refactor/test_r1_architecture.py
import ast
import importlib
from pathlib import Path

class TestArchitectureResolution:
    """Validate R1: target_architecture is resolved correctly"""
    
    def test_layers_defined(self):
        """All layers exist with expected modules"""
        layers = load_architecture_spec()["layers"]
        
        for layer_name, expected_modules in layers.items():
            layer_path = Path(f"src/{layer_name}")
            assert layer_path.exists(), f"Layer {layer_name} not found"
            
            actual_modules = {
                f.stem for f in layer_path.glob("*.py")
                if f.stem != "__init__"
            }
            
            assert actual_modules == set(expected_modules), (
                f"Layer {layer_name} modules mismatch\n"
                f"Expected: {expected_modules}\n"
                f"Actual: {actual_modules}"
            )
    
    def test_no_layer_violations(self):
        """Verify no imports violate layer rules"""
        arch = load_architecture_spec()
        violations = []
        
        for layer, rules in arch["rules"].items():
            allowed = set(rules["can_import"])
            forbidden = set(rules["cannot_import"])
            
            for module_file in Path(f"src/{layer}").glob("**/*.py"):
                tree = ast.parse(module_file.read_text())
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imported_layer = alias.name.split(".")[0]
                            if imported_layer in forbidden:
                                violations.append({
                                    "file": str(module_file),
                                    "layer": layer,
                                    "illegal_import": imported_layer
                                })
        
        assert len(violations) == 0, (
            f"Found {len(violations)} layer violations:\n" +
            "\n".join(str(v) for v in violations)
        )
    
    def test_dependency_graph_acyclic(self):
        """Ensure no circular dependencies"""
        graph = build_dependency_graph()
        cycles = detect_cycles(graph)
        
        assert len(cycles) == 0, (
            f"Found circular dependencies:\n" +
            "\n".join(" -> ".join(cycle) for cycle in cycles)
        )
```

### Pattern: Consolidation Validation

```python
# tests/refactor/test_r4_consolidation.py
import pytest

class TestConsolidationResolution:
    """Validate R4: consolidation_targets resolved correctly"""
    
    @pytest.fixture
    def old_functions(self):
        """Old functions being consolidated"""
        return [parse_v1, parse_v2, parse_v3]
    
    @pytest.fixture
    def test_cases(self):
        """Comprehensive test cases covering all variants"""
        return load_test_cases("parsing")
    
    def test_unified_function_equivalence(self, old_functions, test_cases):
        """New unified function produces same results as old functions"""
        for old_func in old_functions:
            # Get test cases specific to this variant
            variant_cases = [
                case for case in test_cases
                if case.variant == old_func.__name__
            ]
            
            for case in variant_cases:
                old_result = old_func(case.input)
                new_result = unified_parse(case.input, mode=old_func.__name__)
                
                assert old_result == new_result, (
                    f"Consolidated function differs from {old_func.__name__}\n"
                    f"Input: {case.input}\n"
                    f"Expected: {old_result}\n"
                    f"Got: {new_result}"
                )
    
    def test_no_remaining_duplicates(self):
        """Verify duplicate code eliminated"""
        from radon.complexity import cc_visit
        
        duplicates = find_code_clones(
            path="src/",
            min_lines=6,
            similarity_threshold=0.8
        )
        
        assert len(duplicates) == 0, (
            f"Found {len(duplicates)} duplicate code blocks:\n" +
            "\n".join(f"{d.file1}:{d.line1} <-> {d.file2}:{d.line2}"
                     for d in duplicates)
        )
    
    def test_complexity_reduced(self):
        """Verify cyclomatic complexity improved"""
        old_complexity = sum(
            cc_visit(open(f).read())[0].complexity
            for f in ["parse_v1.py", "parse_v2.py", "parse_v3.py"]
        )
        
        new_complexity = cc_visit(
            open("parser.py").read()
        )[0].complexity
        
        assert new_complexity < old_complexity, (
            f"Complexity not reduced\n"
            f"Old: {old_complexity}\n"
            f"New: {new_complexity}"
        )
```

### Pattern: Performance Validation

```python
# tests/refactor/test_r5_performance.py
import pytest
import time

class TestPerformanceImprovement:
    """Validate performance holes resolved correctly"""
    
    ITERATIONS = 100
    
    def measure_throughput(self, operation, test_data):
        """Measure operations per second"""
        start = time.perf_counter()
        for _ in range(self.ITERATIONS):
            operation(test_data)
        end = time.perf_counter()
        
        return self.ITERATIONS / (end - start)
    
    def test_throughput_improved(self):
        """Refactored code has better throughput"""
        test_data = load_sample_data()
        
        # Get baseline from characterization tests
        baseline = load_baseline("throughput")
        
        # Measure new throughput
        current = self.measure_throughput(refactored_operation, test_data)
        
        improvement = (current - baseline) / baseline
        
        assert improvement > 0, (
            f"Throughput regressed by {-improvement:.2%}\n"
            f"Baseline: {baseline:.2f} ops/sec\n"
            f"Current: {current:.2f} ops/sec"
        )
        
        print(f"Throughput improved by {improvement:.2%}")
```

## Integration Tests

End-to-end validation.

### Pattern: Workflow Equivalence

```python
# tests/integration/test_workflows.py
import pytest

class TestWorkflowEquivalence:
    """Ensure end-to-end workflows produce identical results"""
    
    @pytest.fixture
    def scenarios(self):
        """Real-world scenarios with expected outputs"""
        return load_scenarios("tests/integration/scenarios/")
    
    def test_complete_workflows(self, scenarios):
        """Run full workflows on old and new code"""
        for scenario in scenarios:
            # Run on old code (from main branch)
            old_result = run_workflow_old(scenario.input)
            
            # Run on new code (refactored branch)
            new_result = run_workflow_new(scenario.input)
            
            # Results should be identical
            assert old_result == new_result, (
                f"Workflow {scenario.name} produced different results\n"
                f"Input: {scenario.input}\n"
                f"Old: {old_result}\n"
                f"New: {new_result}"
            )
            
            # Performance should not regress
            old_time = scenario.baseline_time
            new_time = measure_workflow_time(scenario.input)
            
            assert new_time <= old_time * 1.2, (
                f"Workflow {scenario.name} performance regressed\n"
                f"Old: {old_time:.2f}s\n"
                f"New: {new_time:.2f}s"
            )
```

## Property-Based Tests

Validate properties that should always hold.

### Pattern: Invariant Checking

```python
# tests/refactor/test_invariants.py
from hypothesis import given, strategies as st

class TestInvariants:
    """Test properties that must always hold"""
    
    @given(st.text(min_size=1, max_size=1000))
    def test_parse_serialize_roundtrip(self, text):
        """Parse then serialize should return to original"""
        parsed = parse(text)
        serialized = serialize(parsed)
        reparsed = parse(serialized)
        
        assert parsed == reparsed
    
    @given(st.lists(st.integers(), min_size=0, max_size=100))
    def test_sort_idempotent(self, data):
        """Sorting twice gives same result as sorting once"""
        sorted_once = custom_sort(data)
        sorted_twice = custom_sort(sorted_once)
        
        assert sorted_once == sorted_twice
    
    @given(st.dictionaries(st.text(), st.integers()))
    def test_cache_consistency(self, data):
        """Cache should return same value as uncached"""
        for key, value in data.items():
            # Uncached computation
            uncached_result = expensive_operation(key, value)
            
            # Cached computation
            cached_result = cached_expensive_operation(key, value)
            
            assert uncached_result == cached_result
```

## Migration Tests

Validate safe transition.

### Pattern: Feature Flag Testing

```python
# tests/migration/test_feature_flags.py
import pytest

class TestFeatureFlags:
    """Validate feature flag rollout mechanism"""
    
    def test_flag_off_uses_old_code(self):
        """When flag disabled, should use old implementation"""
        set_feature_flag("use_refactored_code", False)
        
        result = call_api("/endpoint", test_data)
        
        # Should match old behavior exactly
        assert result == old_baseline_result
        assert get_active_implementation() == "old"
    
    def test_flag_on_uses_new_code(self):
        """When flag enabled, should use new implementation"""
        set_feature_flag("use_refactored_code", True)
        
        result = call_api("/endpoint", test_data)
        
        # Should match new behavior
        assert result == new_expected_result
        assert get_active_implementation() == "new"
    
    def test_toggle_flag_mid_flight(self):
        """Can toggle flag without restart"""
        set_feature_flag("use_refactored_code", False)
        result1 = call_api("/endpoint", test_data)
        
        set_feature_flag("use_refactored_code", True)
        result2 = call_api("/endpoint", test_data)
        
        # Both should work, possibly with different results
        assert result1 is not None
        assert result2 is not None
    
    def test_percentage_rollout(self):
        """Percentage rollout distributes correctly"""
        set_feature_flag_percentage("use_refactored_code", 50)
        
        results = {"old": 0, "new": 0}
        for user_id in range(1000):
            impl = get_implementation_for_user(user_id)
            results[impl] += 1
        
        # Should be approximately 50/50
        ratio = results["new"] / 1000
        assert 0.45 <= ratio <= 0.55, f"Rollout ratio: {ratio}"
```

## Summary

Validation patterns ensure:

1. **Characterization tests** preserve existing behavior
2. **Resolution tests** verify holes are correctly resolved
3. **Integration tests** validate end-to-end workflows
4. **Property tests** check invariants hold
5. **Migration tests** ensure safe transitions

Use these patterns throughout the refactoring process to maintain confidence and catch regressions early.
