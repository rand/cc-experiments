# Model Versioning for Compiled DSPy Models

A comprehensive example demonstrating semantic versioning, model registry, promotion workflows, and rollback capabilities for compiled DSPy models in production.

## Overview

This example showcases:
- **Semantic versioning** for model releases using semver
- **Model registry** with multiple versions per model
- **Promotion workflow** (development → staging → production)
- **Model comparison** and performance tracking
- **Rollback capabilities** for production issues
- **Metadata tracking** for auditability and compliance

## Versioning Strategy

### Semantic Versioning Rules

Following semver 2.0.0 for model versions:

- **MAJOR** (1.0.0): Breaking changes in input/output format, API changes
- **MINOR** (0.1.0): New features, improved accuracy, backward-compatible changes
- **PATCH** (0.0.1): Bug fixes, minor optimizations, no behavior changes

### Version Lifecycle

```
Development → Staging → Production → Deprecated
     ↓           ↓          ↓
  Testing    Validation  Monitoring
```

## Architecture

### Core Components

1. **ModelRegistry**: Central registry managing all model versions
2. **ModelVersion**: Version metadata with semver and status
3. **ModelStatus**: Lifecycle stages (Development, Staging, Production, Deprecated)
4. **ModelMetadata**: Comprehensive tracking information

### Directory Structure

```
models/
├── qa-model/
│   ├── 1.0.0/
│   │   ├── model.pkl
│   │   └── metadata.json
│   ├── 1.1.0/
│   │   ├── model.pkl
│   │   └── metadata.json
│   └── 2.0.0/
│       ├── model.pkl
│       └── metadata.json
└── summarization-model/
    └── 1.0.0/
        ├── model.pkl
        └── metadata.json
```

## Usage

### Basic Workflow

```bash
# Run the complete versioning example
cargo run

# Build for release
cargo build --release
```

### Example Output

The example demonstrates:
1. Creating multiple model versions (1.0.0, 1.1.0, 2.0.0)
2. Promoting models through lifecycle stages
3. Comparing versions by performance metrics
4. Rolling back from problematic production version
5. Displaying version history

## Versioning Best Practices

### When to Bump MAJOR

- Input schema changes (new required fields)
- Output format changes (structure modifications)
- Removed or renamed parameters
- Incompatible behavior changes

Example:
```rust
// v1.0.0: Returns simple string
pub fn predict(question: &str) -> String;

// v2.0.0: Returns structured response (BREAKING)
pub fn predict(question: &str) -> PredictionResponse;
```

### When to Bump MINOR

- New optional parameters
- Improved accuracy/performance
- Additional output fields (backward-compatible)
- New optional features

Example:
```rust
// v1.0.0: Basic QA
pub fn predict(question: &str) -> String;

// v1.1.0: Added confidence score (backward-compatible)
pub fn predict(question: &str) -> (String, f64);
```

### When to Bump PATCH

- Bug fixes
- Performance optimizations
- Internal refactoring
- Documentation updates

## Promotion Workflow

### Development Phase

- Initial training and optimization
- Unit testing and validation
- Performance benchmarking
- Code review

### Staging Phase

- Integration testing
- Load testing
- A/B testing preparation
- Stakeholder review

### Production Phase

- Gradual rollout (canary deployment)
- Monitoring and alerting
- Performance tracking
- Incident response readiness

### Deprecation

- Version marked as deprecated
- Grace period for migration
- Clear communication
- Eventually archived

## Comparison Criteria

Models are compared on:
- **Validation score**: Primary accuracy metric
- **Training examples**: Dataset size
- **Optimizer**: Optimization method used
- **Base model**: Underlying LLM
- **Hyperparameters**: Configuration differences

## Rollback Strategy

### When to Rollback

- Performance degradation (>5% accuracy drop)
- Increased latency (>2x p99 latency)
- Error rate spike (>1% errors)
- Resource exhaustion
- Security vulnerability

### Rollback Process

1. Identify problematic version
2. Locate last known good version
3. Promote previous production version
4. Mark problematic version as deprecated
5. Post-mortem and root cause analysis

## Metadata Tracking

Each model version tracks:

```json
{
  "model_id": "qa-model",
  "version": "1.1.0",
  "created_at": "2025-01-15T10:30:00Z",
  "optimizer": "MIPROv2",
  "base_model": "gpt-3.5-turbo",
  "num_training_examples": 1500,
  "validation_score": 0.89,
  "hyperparameters": {
    "num_candidates": 10,
    "temperature": 0.7
  }
}
```

## Integration with CI/CD

### Automated Version Validation

```yaml
# .github/workflows/model-release.yml
name: Model Release
on:
  push:
    tags:
      - 'v*'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Validate version
        run: cargo run --bin validate-version
      - name: Run tests
        run: cargo test
      - name: Promote to staging
        run: cargo run --bin promote-staging
```

## Monitoring and Observability

Track key metrics:
- **Version distribution**: % traffic per version
- **Performance metrics**: Latency, throughput, accuracy
- **Error rates**: By version and error type
- **Resource usage**: Memory, CPU, GPU utilization

## Security Considerations

- **Model signing**: Cryptographic signatures for authenticity
- **Access control**: Version-level permissions
- **Audit trail**: All promotion/rollback events logged
- **Vulnerability scanning**: Automated security checks

## Advanced Features

### Automatic Rollback

Implement automatic rollback triggers:
```rust
if error_rate > threshold {
    registry.rollback_to_previous_production(model_id)?;
    alert_team("Automatic rollback triggered");
}
```

### Canary Deployments

Gradual rollout with traffic splitting:
```rust
// Route 10% traffic to new version
registry.set_traffic_split(model_id, "2.0.0", 0.10)?;

// Monitor metrics...

// Increase to 50% if healthy
registry.set_traffic_split(model_id, "2.0.0", 0.50)?;
```

### A/B Testing

Compare versions with controlled experiments:
```rust
let experiment = registry.create_experiment(
    model_id,
    "1.1.0",  // Control
    "2.0.0",  // Treatment
    0.5,      // 50/50 split
)?;

// Collect metrics and decide winner
```

## Dependencies

- `pyo3`: Python interop for DSPy integration
- `semver`: Semantic versioning support
- `serde`/`serde_json`: Serialization for metadata
- `chrono`: Timestamp tracking
- `anyhow`: Error handling
- `tokio`: Async runtime

## File Structure

```
model-versioning/
├── Cargo.toml          # Project configuration
├── README.md           # This file
└── src/
    ├── lib.rs          # Core versioning logic (600-700 lines)
    └── main.rs         # Example workflows (400-500 lines)
```

## Line Count

- `lib.rs`: ~650 lines (registry, versioning, promotion)
- `main.rs`: ~450 lines (workflows, examples, demos)
- Total: ~1100 lines of Rust code

## References

- [Semantic Versioning 2.0.0](https://semver.org/)
- [DSPy Documentation](https://dspy-docs.vercel.app/)
- [Model Versioning Best Practices](https://ml-ops.org/content/mlops-principles)

## License

MIT
