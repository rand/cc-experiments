# LM API Cost Tracking and Budgeting

A comprehensive cost tracking system for Language Model API usage with budget enforcement and cost optimization recommendations.

## Features

- **Per-Model Pricing**: Accurate cost tracking with up-to-date pricing tables
- **Multi-Dimensional Aggregation**: Track costs by user, endpoint, model, time period
- **Budget Enforcement**: Daily/monthly limits with configurable alerts
- **Cost Reports**: Detailed analytics and optimization recommendations
- **Real-Time Tracking**: Track costs per prediction with token counting

## Architecture

```
┌─────────────────┐
│  Application    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐
│  CostTracker    │─────▶│  Pricing DB  │
└────────┬────────┘      └──────────────┘
         │
         ├──▶ track_prediction()
         ├──▶ check_budget()
         ├──▶ aggregate_costs()
         └──▶ generate_report()

┌─────────────────────────────────────┐
│  Cost Dimensions                    │
├─────────────────────────────────────┤
│  • User ID                          │
│  • Model Name                       │
│  • Endpoint                         │
│  • Time Period (hour/day/month)     │
│  • Request Type                     │
└─────────────────────────────────────┘
```

## Usage

### Basic Cost Tracking

```rust
use cost_tracking::{CostTracker, ModelPricing, CostBudget};

// Initialize tracker with pricing data
let mut tracker = CostTracker::new("pricing.json")?;

// Track a prediction
let cost = tracker.track_prediction(
    "user_123",
    "api/chat",
    "gpt-4-turbo",
    1500,  // input tokens
    500,   // output tokens
)?;

println!("Prediction cost: ${:.4}", cost);
```

### Budget Enforcement

```rust
// Check budget before making API call
match tracker.check_budget("user_123") {
    Ok(_) => {
        // Proceed with API call
        let result = make_api_call();
        tracker.track_prediction(...)?;
    }
    Err(e) => {
        // Budget exceeded, handle gracefully
        eprintln!("Budget exceeded: {}", e);
    }
}
```

### Cost Reporting

```rust
// Generate cost report
let report = tracker.generate_report(
    Some("user_123"),  // Optional user filter
    None,              // All models
    chrono::Duration::days(7)  // Last 7 days
)?;

println!("{}", report.summary());
println!("\nRecommendations:");
for rec in report.recommendations() {
    println!("  • {}", rec);
}
```

### Cost Aggregation

```rust
// Aggregate by model
let by_model = tracker.aggregate_by_model(chrono::Duration::days(30));
for (model, cost) in by_model {
    println!("{}: ${:.2}", model, cost);
}

// Aggregate by user
let by_user = tracker.aggregate_by_user(chrono::Duration::days(1));
for (user, cost) in by_user {
    println!("{}: ${:.2}", user, cost);
}
```

## Cost Optimization Guide

### 1. Model Selection

Choose the right model for the task:

- **Simple tasks**: Use cheaper models (GPT-3.5, Llama-3-8B, Claude Haiku)
- **Complex reasoning**: Use premium models sparingly (GPT-4, Claude Opus)
- **Long context**: Consider models with larger windows (Claude, Gemini)

### 2. Token Optimization

Reduce token usage:

```rust
// Bad: Verbose prompts
let prompt = "I would like you to please analyze this text...";

// Good: Concise prompts
let prompt = "Analyze: {text}";
```

### 3. Caching Strategies

- Cache frequent predictions
- Reuse system prompts
- Batch similar requests

### 4. Budget Allocation

Set appropriate limits:

```rust
let budget = CostBudget::builder()
    .daily_limit(50.0)
    .monthly_limit(1000.0)
    .per_user_daily_limit(5.0)
    .alert_threshold(0.80)  // Alert at 80%
    .build();
```

### 5. Monitoring

Track cost trends:

- Daily cost patterns
- Per-user consumption
- Model usage distribution
- Endpoint efficiency

## Pricing Data

The system tracks costs for major LM providers:

| Model | Input ($/1K tokens) | Output ($/1K tokens) |
|-------|---------------------|----------------------|
| GPT-4 Turbo | $0.01 | $0.03 |
| GPT-4 | $0.03 | $0.06 |
| GPT-3.5 Turbo | $0.0005 | $0.0015 |
| Claude 3 Opus | $0.015 | $0.075 |
| Claude 3 Sonnet | $0.003 | $0.015 |
| Claude 3 Haiku | $0.00025 | $0.00125 |
| Gemini 1.5 Pro | $0.0035 | $0.0105 |
| Gemini 1.5 Flash | $0.00035 | $0.00105 |

Update `pricing.json` to reflect current pricing.

## Budget Alerts

The system provides three alert levels:

1. **Warning (80%)**: Approaching budget limit
2. **Critical (95%)**: Near budget exhaustion
3. **Exceeded (100%)**: Budget limit reached

Configure alert handlers:

```rust
tracker.on_alert(|alert| {
    match alert.level {
        AlertLevel::Warning => log::warn!("{}", alert.message),
        AlertLevel::Critical => log::error!("{}", alert.message),
        AlertLevel::Exceeded => {
            log::error!("{}", alert.message);
            // Notify administrators
            send_notification(&alert);
        }
    }
});
```

## Cost Dimensions

Track costs across multiple dimensions:

### By User
```rust
let user_costs = tracker.aggregate_by_user(Duration::days(1));
```

### By Model
```rust
let model_costs = tracker.aggregate_by_model(Duration::days(1));
```

### By Endpoint
```rust
let endpoint_costs = tracker.aggregate_by_endpoint(Duration::days(1));
```

### By Time Period
```rust
let hourly = tracker.aggregate_by_hour(Duration::days(1));
let daily = tracker.aggregate_by_day(Duration::days(30));
```

## Advanced Features

### Custom Pricing

Add custom model pricing:

```rust
tracker.add_model_pricing(
    "custom-model",
    ModelPricing {
        input_cost_per_1k: 0.002,
        output_cost_per_1k: 0.006,
        context_window: 32000,
    }
)?;
```

### Cost Forecasting

Predict future costs based on historical data:

```rust
let forecast = tracker.forecast_monthly_cost()?;
println!("Projected monthly cost: ${:.2}", forecast);
```

### Export Reports

Export cost data for analysis:

```rust
// JSON export
tracker.export_json("costs.json", Duration::days(30))?;

// CSV export
tracker.export_csv("costs.csv", Duration::days(30))?;
```

## Running the Demo

```bash
# Build the project
cargo build --release

# Run the demo
cargo run --bin cost-tracking-demo

# Run with custom pricing
cargo run --bin cost-tracking-demo -- --pricing custom-pricing.json
```

## Integration Example

```rust
use cost_tracking::{CostTracker, CostBudget};
use anyhow::Result;

struct ApiClient {
    tracker: CostTracker,
}

impl ApiClient {
    pub fn new(pricing_path: &str) -> Result<Self> {
        Ok(Self {
            tracker: CostTracker::new(pricing_path)?,
        })
    }

    pub async fn chat_completion(
        &mut self,
        user_id: &str,
        model: &str,
        prompt: &str,
    ) -> Result<String> {
        // Check budget before call
        self.tracker.check_budget(user_id)?;

        // Make API call
        let (response, input_tokens, output_tokens) =
            self.call_api(model, prompt).await?;

        // Track cost
        self.tracker.track_prediction(
            user_id,
            "api/chat",
            model,
            input_tokens,
            output_tokens,
        )?;

        Ok(response)
    }

    pub fn get_usage_report(&self, user_id: &str) -> Result<String> {
        let report = self.tracker.generate_report(
            Some(user_id),
            None,
            chrono::Duration::days(30),
        )?;
        Ok(report.summary())
    }
}
```

## Performance Considerations

- **In-Memory Tracking**: Fast lookups, O(1) cost tracking
- **Batch Aggregation**: Efficient multi-dimensional analysis
- **Lazy Loading**: Load pricing data on demand
- **Async Support**: Non-blocking cost tracking with Tokio

## Testing

```bash
# Run tests
cargo test

# Run with coverage
cargo tarpaulin --out Html
```

## License

See parent project license.
