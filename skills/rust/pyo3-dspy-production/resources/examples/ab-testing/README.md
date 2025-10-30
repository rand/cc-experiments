# A/B Testing for DSPy Models

A comprehensive A/B testing infrastructure for comparing DSPy model variants in production, with traffic splitting, metrics collection, and statistical analysis.

## Overview

This example demonstrates how to:

1. **Configure multi-variant experiments** with traffic splitting
2. **Route traffic** based on configurable strategies
3. **Collect metrics** for latency, quality, and user feedback
4. **Analyze results** with statistical significance testing
5. **Generate promotion decisions** based on confidence intervals

## Features

### Traffic Splitting Strategies

- **Weighted random**: Probabilistic routing based on variant weights
- **Sticky sessions**: Consistent routing per user
- **Gradual rollout**: Progressive traffic shifting
- **Geographic routing**: Region-based variant assignment

### Metrics Collection

- **Latency metrics**: p50, p95, p99 percentiles
- **Quality metrics**: Task-specific success rates
- **User feedback**: Explicit ratings and implicit signals
- **Cost metrics**: Token usage and API costs

### Statistical Analysis

- **T-tests**: Compare continuous metrics (latency)
- **Chi-square tests**: Compare categorical metrics (success rate)
- **Confidence intervals**: Estimate effect sizes
- **Sample size calculation**: Determine experiment duration
- **Power analysis**: Assess statistical power

### Promotion Decisions

- **Automatic criteria**: Statistical significance + minimum sample size
- **Safety checks**: No performance regressions
- **Confidence thresholds**: Configurable p-values
- **Rollback triggers**: Automatic reversion on failures

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    ABTestRunner                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Traffic Router                                     │ │
│  │  - Weighted random selection                       │ │
│  │  - Sticky session management                       │ │
│  │  - Gradual rollout control                         │ │
│  └────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Model Variants                                     │ │
│  │  - Control (baseline)                              │ │
│  │  - Treatment A (variant 1)                         │ │
│  │  - Treatment B (variant 2)                         │ │
│  └────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Metrics Collector                                  │ │
│  │  - Per-request latency                             │ │
│  │  - Quality scores                                  │ │
│  │  - User feedback                                   │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│              Statistical Analyzer                        │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Hypothesis Testing                                 │ │
│  │  - T-tests for continuous metrics                  │ │
│  │  - Chi-square for categorical metrics              │ │
│  │  - Effect size calculation                         │ │
│  └────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Confidence Intervals                               │ │
│  │  - Bootstrap resampling                            │ │
│  │  - Percentile method                               │ │
│  │  - Normal approximation                            │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│              Experiment Report                           │
│  - Variant performance comparison                        │
│  - Statistical significance                              │
│  - Promotion recommendation                              │
│  - Rollback triggers                                     │
└─────────────────────────────────────────────────────────┘
```

## Usage

### Basic A/B Test

```rust
use ab_testing::*;

// Configure experiment
let config = ABTestConfig {
    name: "model-v2-test".to_string(),
    variants: vec![
        ModelVariant {
            name: "control".to_string(),
            model_path: "models/v1".to_string(),
            weight: 0.5,
        },
        ModelVariant {
            name: "treatment".to_string(),
            model_path: "models/v2".to_string(),
            weight: 0.5,
        },
    ],
    traffic_strategy: TrafficStrategy::WeightedRandom,
    min_sample_size: 1000,
    confidence_level: 0.95,
    duration_hours: 24,
};

// Run experiment
let mut runner = ABTestRunner::new(config)?;
runner.start().await?;

// Process requests
for request in requests {
    let variant = runner.route_traffic(&request.user_id);
    let response = runner.predict(&variant, &request).await?;
    runner.record_metrics(&variant, &response);
}

// Analyze results
let report = runner.analyze()?;
if report.should_promote() {
    println!("Promoting variant: {}", report.winner);
}
```

### Multi-Variant Test

```rust
let config = ABTestConfig {
    name: "multi-model-test".to_string(),
    variants: vec![
        ModelVariant {
            name: "control".to_string(),
            model_path: "models/baseline".to_string(),
            weight: 0.4,
        },
        ModelVariant {
            name: "variant-a".to_string(),
            model_path: "models/optimized".to_string(),
            weight: 0.3,
        },
        ModelVariant {
            name: "variant-b".to_string(),
            model_path: "models/experimental".to_string(),
            weight: 0.3,
        },
    ],
    traffic_strategy: TrafficStrategy::StickySession,
    min_sample_size: 5000,
    confidence_level: 0.99,
    duration_hours: 72,
};
```

### Gradual Rollout

```rust
let config = ABTestConfig {
    name: "gradual-rollout".to_string(),
    variants: vec![
        ModelVariant {
            name: "control".to_string(),
            model_path: "models/stable".to_string(),
            weight: 0.9, // Start with 90% control
        },
        ModelVariant {
            name: "canary".to_string(),
            model_path: "models/new".to_string(),
            weight: 0.1, // 10% canary traffic
        },
    ],
    traffic_strategy: TrafficStrategy::GradualRollout {
        initial_treatment_weight: 0.1,
        target_treatment_weight: 0.5,
        step_size: 0.1,
        step_duration_hours: 6,
    },
    min_sample_size: 500,
    confidence_level: 0.95,
    duration_hours: 48,
};
```

## Metrics

### Latency Metrics

- **p50**: Median latency
- **p95**: 95th percentile latency
- **p99**: 99th percentile latency
- **mean**: Average latency

### Quality Metrics

- **Success rate**: Percentage of successful predictions
- **Error rate**: Percentage of failed predictions
- **User satisfaction**: Average user rating (1-5)
- **Task completion**: Percentage of completed tasks

### Cost Metrics

- **Token usage**: Total tokens consumed
- **API calls**: Total API requests
- **Cost per request**: Average cost per prediction

## Statistical Analysis

### T-Test for Latency

```
H0: μ_control = μ_treatment
H1: μ_control ≠ μ_treatment

t = (x̄_control - x̄_treatment) / SE
p-value = P(|T| > |t|)
```

### Chi-Square for Success Rate

```
H0: p_control = p_treatment
H1: p_control ≠ p_treatment

χ² = Σ (O - E)² / E
p-value = P(χ² > χ²_observed)
```

### Effect Size

```
Cohen's d = (μ_treatment - μ_control) / σ_pooled

Small: d = 0.2
Medium: d = 0.5
Large: d = 0.8
```

## Promotion Criteria

A variant is promoted if:

1. **Statistical significance**: p-value < α (default: 0.05)
2. **Minimum sample size**: n > n_min (default: 1000)
3. **No regressions**: No metric worse than control by > 5%
4. **Effect size**: Cohen's d > 0.2 (small effect)
5. **Confidence interval**: Lower bound > 0 (improvement guaranteed)

## Safety Mechanisms

### Automatic Rollback

The system automatically rolls back to control if:

- **Error rate spike**: > 10% increase in errors
- **Latency regression**: > 20% increase in p99 latency
- **User satisfaction drop**: > 0.5 decrease in ratings
- **Statistical anomaly**: Z-score > 3 for any metric

### Circuit Breaker

```rust
let circuit_breaker = CircuitBreaker {
    error_threshold: 0.5,  // 50% errors
    window_size: 100,       // Last 100 requests
    timeout_seconds: 60,    // Circuit open for 60s
};
```

### Rate Limiting

```rust
let rate_limiter = RateLimiter {
    requests_per_second: 1000,
    burst_size: 100,
};
```

## Configuration

### experiment_config.json

```json
{
  "name": "model-comparison",
  "variants": [
    {
      "name": "control",
      "model_path": "models/production/v1",
      "weight": 0.5
    },
    {
      "name": "treatment",
      "model_path": "models/production/v2",
      "weight": 0.5
    }
  ],
  "traffic_strategy": "weighted_random",
  "min_sample_size": 1000,
  "confidence_level": 0.95,
  "duration_hours": 24,
  "metrics": {
    "latency": {
      "enabled": true,
      "percentiles": [50, 95, 99]
    },
    "quality": {
      "enabled": true,
      "threshold": 0.8
    },
    "cost": {
      "enabled": true,
      "max_cost_per_request": 0.01
    }
  },
  "promotion": {
    "auto_promote": false,
    "required_confidence": 0.95,
    "min_improvement": 0.05,
    "max_regression": 0.02
  },
  "safety": {
    "rollback_on_errors": true,
    "error_threshold": 0.1,
    "latency_threshold_multiplier": 1.2
  }
}
```

## Running the Example

```bash
# Build
cargo build --release

# Run with default config
cargo run --release

# Run with custom config
cargo run --release -- --config custom_experiment.json

# Run with specific duration
cargo run --release -- --duration-hours 48

# Run in dry-run mode (no actual traffic routing)
cargo run --release -- --dry-run
```

## Output

The example produces:

1. **Real-time metrics**: Console output during experiment
2. **Experiment report**: JSON file with detailed results
3. **Promotion recommendation**: Decision and reasoning
4. **Visualizations**: Metrics charts (requires gnuplot)

Example report:

```json
{
  "experiment_name": "model-v2-test",
  "duration_hours": 24,
  "total_requests": 10000,
  "variants": {
    "control": {
      "requests": 5000,
      "latency_p50": 45.2,
      "latency_p95": 120.5,
      "latency_p99": 180.3,
      "success_rate": 0.95,
      "user_satisfaction": 4.2
    },
    "treatment": {
      "requests": 5000,
      "latency_p50": 38.1,
      "latency_p95": 98.2,
      "latency_p99": 145.6,
      "success_rate": 0.97,
      "user_satisfaction": 4.5
    }
  },
  "statistical_analysis": {
    "latency_t_test": {
      "t_statistic": -3.45,
      "p_value": 0.0006,
      "significant": true
    },
    "success_rate_chi_square": {
      "chi_square": 8.23,
      "p_value": 0.004,
      "significant": true
    },
    "effect_size": {
      "cohens_d": 0.42,
      "interpretation": "medium"
    }
  },
  "promotion_decision": {
    "should_promote": true,
    "winner": "treatment",
    "confidence": 0.99,
    "reasoning": "Treatment shows statistically significant improvement in latency (p=0.0006) and success rate (p=0.004) with medium effect size (d=0.42). All safety checks passed."
  }
}
```

## Best Practices

1. **Sample Size**: Ensure sufficient samples for statistical power
2. **Duration**: Run experiments for at least one business cycle
3. **Metrics**: Track multiple metrics, not just one
4. **Safety**: Always include rollback mechanisms
5. **Documentation**: Document experiment hypothesis and expected outcomes
6. **Monitoring**: Watch for unexpected behavior during rollout
7. **Iteration**: Use learnings to refine future experiments

## Advanced Topics

### Bayesian A/B Testing

For early stopping and continuous monitoring:

```rust
let bayesian_analyzer = BayesianAnalyzer {
    prior_alpha: 1.0,
    prior_beta: 1.0,
    credible_interval: 0.95,
};
```

### Multi-Armed Bandits

For adaptive traffic allocation:

```rust
let bandit = ThompsonSampling {
    variants: vec!["control", "treatment_a", "treatment_b"],
    exploration_rate: 0.1,
};
```

### Segmented Analysis

Analyze results by user segments:

```rust
let segments = vec![
    Segment::new("power_users", |u| u.requests_per_day > 100),
    Segment::new("new_users", |u| u.account_age_days < 30),
    Segment::new("enterprise", |u| u.plan == "enterprise"),
];
```

## References

- [A/B Testing Statistics](https://www.evanmiller.org/ab-testing/)
- [Controlled Experiments at Scale](https://ai.stanford.edu/~ronnyk/2009controlledExperimentsOnTheWebSurvey.pdf)
- [Statistical Power and Sample Size](https://www.stat.ubc.ca/~rollin/stats/ssize/)
