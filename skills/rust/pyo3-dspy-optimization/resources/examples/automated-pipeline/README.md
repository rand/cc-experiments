# Automated Pipeline Example

This example demonstrates a complete end-to-end automated DSPy optimization pipeline with scheduling, quality gates, automatic deployment, and monitoring capabilities.

## Architecture

The pipeline consists of four stages that execute sequentially:

```
┌─────────────┐    ┌──────────┐    ┌────────────┐    ┌────────────┐
│  Data Prep  │ -> │ Training │ -> │ Validation │ -> │ Deployment │
└─────────────┘    └──────────┘    └────────────┘    └────────────┘
      │                  │                │                  │
      v                  v                v                  v
  Validate           Optimize         Check            Deploy to
  datasets           with DSPy      quality gates      production
```

### Pipeline Stages

1. **Data Prep**: Load and validate training/validation datasets
2. **Training**: Run DSPy optimization (MIPROv2, BootstrapFewShot, etc.)
3. **Validation**: Evaluate model performance and collect metrics
4. **Deployment**: Deploy to production if quality gates pass

### Quality Gates

Quality gates are checks that must pass before deployment:

- **Accuracy Threshold**: Minimum model accuracy
- **F1 Score Threshold**: Minimum F1 score
- **Evaluation Coverage**: Minimum number of examples evaluated

If any required gate fails, the pipeline stops and optionally rolls back.

### Features

- **Scheduled Execution**: Run pipelines on a cron schedule
- **Quality Gates**: Automated validation with configurable thresholds
- **Automatic Deployment**: Deploy successful models to production
- **Rollback Support**: Revert to previous model on failure
- **Notifications**: Webhook, Slack, and email alerts
- **State Persistence**: Track pipeline history and status
- **Artifact Management**: Store models and metrics for each run

## Usage

### Installation

```bash
cd automated-pipeline
cargo build --release
```

### Initialize Configuration

Create a default configuration file:

```bash
cargo run -- init
```

This creates `pipeline.yaml` with default settings. Edit this file to customize:

```yaml
name: "production_optimization"
optimizer: "MIPROv2"
train_data: "data/train.json"
val_data: "data/val.json"

quality_gates:
  - name: "accuracy_threshold"
    metric: "accuracy"
    min_value: 0.75
    required: true

deploy_dir: "models/production"
auto_deploy: true
enable_rollback: true
```

### Validate Configuration

Check that your configuration is valid:

```bash
cargo run -- validate
```

This verifies:
- Data files exist
- Directories are accessible
- Quality gates are properly configured
- Notification settings are valid

### Run Pipeline Once

Execute the pipeline manually:

```bash
cargo run -- run
```

Output:
```
=== Pipeline Execution Summary ===
Run ID: run_1698765432
Status: SUCCESS
Started: 2023-10-31 10:30:00 UTC
Duration: 145s

Stage Results:
  DataPrep: ✓ (2.1s)
    Metrics:
      train_examples: 500
      val_examples: 100
  Training: ✓ (120.5s)
    Metrics:
      trials: 100
  Validation: ✓ (20.2s)
    Metrics:
      accuracy: 0.8500
      f1_score: 0.8200
  Deployment: ✓ (2.2s)

Deployed Model: models/production/model_1698765577.pkl
```

### Schedule Automatic Runs

Start the scheduler to run pipelines automatically:

```bash
# Run daily at midnight
cargo run -- schedule "0 0 * * *"

# Run every 6 hours
cargo run -- schedule "0 */6 * * *"

# Run twice daily at 9 AM and 9 PM
cargo run -- schedule "0 9,21 * * *"

# Run on weekdays at 8 AM
cargo run -- schedule "0 8 * * 1-5"
```

The scheduler runs in the foreground. Press Ctrl+C to stop.

### Check Pipeline Status

View current pipeline state:

```bash
cargo run -- status
```

Output:
```
=== Pipeline Status ===
Name: production_optimization
Optimizer: MIPROv2

Status: Idle

Statistics:
  Total Runs: 42
  Successful: 38
  Failed: 4
  Success Rate: 90.5%

Last Success: 2023-10-31 10:32:25 UTC
Last Failure: 2023-10-28 15:20:10 UTC

Deployed Model: models/production/model_1698765577.pkl

Quality Gates:
  accuracy_threshold (accuracy)
    Min: 0.75
    Required: true
  f1_threshold (f1_score)
    Min: 0.70
    Required: true
```

### View Pipeline History

Show recent pipeline runs:

```bash
# Show last 10 runs (default)
cargo run -- history

# Show last 5 runs
cargo run -- history 5
```

## Configuration Reference

### Pipeline Settings

```yaml
# Pipeline identification
name: "my_pipeline"

# DSPy optimizer
optimizer: "MIPROv2"  # or "BootstrapFewShot"

# Data paths
train_data: "data/train.json"
val_data: "data/val.json"

# Optimization parameters
max_trials: 100
```

### Quality Gates

```yaml
quality_gates:
  - name: "gate_name"
    metric: "metric_name"
    min_value: 0.7  # Optional minimum
    max_value: 1.0  # Optional maximum
    required: true  # Fail pipeline if gate fails
```

Available metrics from validation stage:
- `accuracy`: Model accuracy
- `f1_score`: F1 score
- `examples_evaluated`: Number of examples evaluated

### Deployment Settings

```yaml
# Where to deploy successful models
deploy_dir: "models/production"

# Where to store artifacts
artifact_dir: "artifacts"

# Automatically deploy on success
auto_deploy: true

# Rollback on failure
enable_rollback: true
```

### Notifications

```yaml
notifications:
  # Generic webhook (POST JSON)
  webhook_url: "https://example.com/webhook"

  # Slack webhook
  slack_webhook: "https://hooks.slack.com/services/..."

  # Email addresses
  email_addresses:
    - "team@example.com"

  # When to notify
  notify_on_success: true
  notify_on_failure: true
```

Webhook payload format:
```json
{
  "pipeline": "production_optimization",
  "status": "SUCCESS",
  "run_id": "run_1698765432",
  "duration_secs": 145,
  "success": true
}
```

## Architecture Details

### State Management

Pipeline state is persisted to `.pipeline_state.json`:

```json
{
  "current_stage": null,
  "current_run_id": null,
  "last_success": "2023-10-31T10:32:25Z",
  "last_failure": null,
  "total_runs": 42,
  "successful_runs": 38,
  "failed_runs": 4,
  "deployed_model": "models/production/model_1698765577.pkl"
}
```

### Artifact Storage

Each pipeline run creates artifacts in `artifacts/run_<timestamp>/`:

```
artifacts/
└── run_1698765432/
    ├── data_prep/
    ├── training/
    │   └── model.pkl
    ├── validation/
    └── deployment/
        └── model_1698765577.pkl
```

### Deployment Strategy

1. Model is optimized and saved to `artifacts/run_*/training/model.pkl`
2. Validation stage evaluates the model
3. Quality gates are checked
4. If all gates pass:
   - Model is copied to `deploy_dir/model_<timestamp>.pkl`
   - Symlink `deploy_dir/latest.pkl` points to new model
5. If deployment fails:
   - Previous model remains in production
   - Optional rollback to previous successful model

### Error Handling

The pipeline handles failures gracefully:

1. **Stage Failure**: Pipeline stops, notifications sent, no deployment
2. **Quality Gate Failure**: Treated as validation failure
3. **Deployment Failure**: Rollback to previous model if enabled
4. **Notification Failure**: Logged but doesn't fail pipeline

## Production Deployment

### Running as a Service

Create a systemd service file `/etc/systemd/system/pipeline.service`:

```ini
[Unit]
Description=Automated DSPy Pipeline
After=network.target

[Service]
Type=simple
User=pipeline
WorkingDirectory=/opt/pipeline
ExecStart=/opt/pipeline/target/release/automated-pipeline schedule "0 0 * * *"
Restart=always
Environment=RUST_LOG=info

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable pipeline
sudo systemctl start pipeline
sudo systemctl status pipeline
```

### Docker Deployment

Create `Dockerfile`:

```dockerfile
FROM rust:1.70 as builder
WORKDIR /app
COPY . .
RUN cargo build --release

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y python3 python3-pip
RUN pip3 install dspy-ai
COPY --from=builder /app/target/release/automated-pipeline /usr/local/bin/
COPY pipeline.yaml /app/
WORKDIR /app
CMD ["automated-pipeline", "schedule", "0 0 * * *"]
```

Build and run:

```bash
docker build -t dspy-pipeline .
docker run -d --name pipeline \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/models:/app/models \
  -v $(pwd)/artifacts:/app/artifacts \
  dspy-pipeline
```

### Monitoring

Monitor pipeline execution:

```bash
# View logs
RUST_LOG=info cargo run -- schedule "0 0 * * *"

# Check status periodically
watch -n 60 'cargo run -- status'

# Track history
cargo run -- history 10
```

Set up health checks:

```bash
# Check if pipeline is running
ps aux | grep automated-pipeline

# Check last success timestamp
cargo run -- status | grep "Last Success"

# Alert if no successful runs in 24 hours
```

## Examples

### Production Pipeline with High Standards

```yaml
name: "production"
optimizer: "MIPROv2"
max_trials: 200

quality_gates:
  - name: "high_accuracy"
    metric: "accuracy"
    min_value: 0.90
    required: true
  - name: "high_f1"
    metric: "f1_score"
    min_value: 0.85
    required: true

auto_deploy: true
enable_rollback: true
```

### Experimental Pipeline

```yaml
name: "experimental"
optimizer: "BootstrapFewShot"
max_trials: 50

quality_gates:
  - name: "basic_accuracy"
    metric: "accuracy"
    min_value: 0.60
    required: false

auto_deploy: false
enable_rollback: false
```

### Scheduled Retraining

Run weekly retraining with notification:

```bash
cargo run -- schedule "0 2 * * 0"  # 2 AM every Sunday
```

Configure aggressive quality gates to ensure only improvements deploy:

```yaml
quality_gates:
  - name: "improvement_required"
    metric: "accuracy"
    min_value: 0.92  # Higher than current production model
    required: true
```

## Troubleshooting

### Pipeline Fails at Data Prep

**Symptom**: DataPrep stage fails with file not found error

**Solution**: Verify data paths in `pipeline.yaml` and run validation:

```bash
cargo run -- validate
```

### Quality Gates Always Fail

**Symptom**: Validation succeeds but quality gates fail

**Solution**: Check gate thresholds are reasonable:

```bash
cargo run -- run  # See actual metric values
# Adjust min_value in pipeline.yaml based on results
```

### Deployment Fails

**Symptom**: Deployment stage fails with permission error

**Solution**: Ensure deploy directory is writable:

```bash
mkdir -p models/production
chmod 755 models/production
```

### Scheduler Stops Unexpectedly

**Symptom**: Scheduled runs stop after first execution

**Solution**: Check for errors in logs:

```bash
RUST_LOG=debug cargo run -- schedule "0 0 * * *"
```

### Rollback Not Working

**Symptom**: Rollback enabled but doesn't restore previous model

**Solution**: Verify previous model exists in state:

```bash
cargo run -- status  # Check "Deployed Model" field
ls -l models/production/
```

## Best Practices

1. **Start Conservative**: Begin with loose quality gates and tighten based on results
2. **Monitor Closely**: Watch first few scheduled runs to catch issues
3. **Test Locally**: Run pipeline manually before scheduling
4. **Version Models**: Timestamped models allow easy comparison
5. **Keep Artifacts**: Retain artifacts for debugging and analysis
6. **Set Up Alerts**: Configure notifications for both success and failure
7. **Plan Rollback**: Test rollback procedure before relying on it
8. **Document Thresholds**: Explain why each quality gate threshold was chosen
9. **Review History**: Regularly check pipeline history for trends
10. **Update Dependencies**: Keep DSPy and pipeline dependencies current

## License

This example is part of the PyO3-DSPy optimization skill resources.
