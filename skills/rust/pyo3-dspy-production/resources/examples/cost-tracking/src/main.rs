use anyhow::Result;
use chrono::Duration;
use cost_tracking::{AlertLevel, BudgetAlert, CostBudget, CostTracker};
use std::sync::{Arc, Mutex};

/// Simulated API call with token counts
struct ApiCall {
    user_id: String,
    endpoint: String,
    model: String,
    input_tokens: usize,
    output_tokens: usize,
}

impl ApiCall {
    fn new(
        user_id: &str,
        endpoint: &str,
        model: &str,
        input_tokens: usize,
        output_tokens: usize,
    ) -> Self {
        Self {
            user_id: user_id.to_string(),
            endpoint: endpoint.to_string(),
            model: model.to_string(),
            input_tokens,
            output_tokens,
        }
    }
}

/// Simulate a batch of API calls
fn simulate_api_calls() -> Vec<ApiCall> {
    vec![
        // User 1: Heavy GPT-4 usage
        ApiCall::new("alice@example.com", "api/chat", "gpt-4-turbo", 2000, 800),
        ApiCall::new("alice@example.com", "api/chat", "gpt-4-turbo", 1500, 1200),
        ApiCall::new("alice@example.com", "api/completion", "gpt-4-turbo", 1800, 900),
        ApiCall::new("alice@example.com", "api/chat", "gpt-4", 3000, 1500),

        // User 2: Mixed model usage
        ApiCall::new("bob@example.com", "api/chat", "gpt-3.5-turbo", 500, 200),
        ApiCall::new("bob@example.com", "api/chat", "claude-3-sonnet", 4000, 800),
        ApiCall::new("bob@example.com", "api/completion", "gpt-3.5-turbo", 600, 150),
        ApiCall::new("bob@example.com", "api/chat", "claude-3-haiku", 800, 100),

        // User 3: Premium model heavy user
        ApiCall::new("charlie@example.com", "api/chat", "claude-3-opus", 8000, 3000),
        ApiCall::new("charlie@example.com", "api/chat", "claude-3-opus", 12000, 4000),
        ApiCall::new("charlie@example.com", "api/completion", "gpt-4", 5000, 2500),

        // User 4: Efficient usage
        ApiCall::new("dana@example.com", "api/chat", "claude-3-haiku", 400, 150),
        ApiCall::new("dana@example.com", "api/chat", "gpt-3.5-turbo", 500, 200),
        ApiCall::new("dana@example.com", "api/completion", "llama-3-8b", 600, 300),

        // User 5: Long context usage
        ApiCall::new("eve@example.com", "api/chat", "gemini-1.5-pro", 20000, 2000),
        ApiCall::new("eve@example.com", "api/chat", "claude-3-sonnet", 15000, 3000),
        ApiCall::new("eve@example.com", "api/completion", "gemini-1.5-flash", 10000, 800),

        // More varied usage patterns
        ApiCall::new("alice@example.com", "api/embedding", "gpt-3.5-turbo", 1000, 0),
        ApiCall::new("bob@example.com", "api/chat", "llama-3-70b", 2000, 1000),
        ApiCall::new("charlie@example.com", "api/chat", "gpt-4-turbo", 1200, 400),
        ApiCall::new("dana@example.com", "api/completion", "claude-3-haiku", 500, 200),
    ]
}

/// Demo 1: Basic cost tracking
fn demo_basic_tracking(tracker: &mut CostTracker) -> Result<()> {
    println!("═══════════════════════════════════════════════════════");
    println!("Demo 1: Basic Cost Tracking");
    println!("═══════════════════════════════════════════════════════\n");

    let calls = vec![
        ApiCall::new("demo_user", "api/chat", "gpt-4-turbo", 1000, 500),
        ApiCall::new("demo_user", "api/chat", "gpt-3.5-turbo", 1000, 500),
        ApiCall::new("demo_user", "api/chat", "claude-3-haiku", 1000, 500),
    ];

    for call in calls {
        let cost = tracker.track_prediction(
            &call.user_id,
            &call.endpoint,
            &call.model,
            call.input_tokens,
            call.output_tokens,
        )?;

        println!("Model: {}", call.model);
        println!("  Input tokens: {}", call.input_tokens);
        println!("  Output tokens: {}", call.output_tokens);
        println!("  Cost: ${:.4}\n", cost);
    }

    Ok(())
}

/// Demo 2: Budget enforcement
fn demo_budget_enforcement() -> Result<()> {
    println!("\n═══════════════════════════════════════════════════════");
    println!("Demo 2: Budget Enforcement");
    println!("═══════════════════════════════════════════════════════\n");

    // Create tracker with strict budget
    let budget = CostBudget::builder()
        .daily_limit(5.0)
        .per_user_daily_limit(2.0)
        .alert_threshold(0.70)
        .build();

    let mut tracker = CostTracker::with_budget("pricing.json", budget)?;

    // Set up alert handler
    let alert_count = Arc::new(Mutex::new(0));
    let alert_count_clone = alert_count.clone();

    tracker.on_alert(move |alert: &BudgetAlert| {
        let mut count = alert_count_clone.lock().unwrap();
        *count += 1;

        let level_str = match alert.level {
            AlertLevel::Warning => "⚠️  WARNING",
            AlertLevel::Critical => "🔴 CRITICAL",
            AlertLevel::Exceeded => "🚫 EXCEEDED",
        };

        println!("{}: {}", level_str, alert.message);
        println!("  Current: ${:.2} / Limit: ${:.2} ({:.1}% utilized)\n",
            alert.current_cost, alert.limit, alert.utilization);
    });

    // Simulate expensive requests
    println!("Making expensive API calls...\n");

    let expensive_calls = vec![
        ApiCall::new("budget_user", "api/chat", "gpt-4", 5000, 2000),
        ApiCall::new("budget_user", "api/chat", "gpt-4", 5000, 2000),
        ApiCall::new("budget_user", "api/chat", "claude-3-opus", 8000, 3000),
    ];

    for (i, call) in expensive_calls.iter().enumerate() {
        println!("Request {}: {}", i + 1, call.model);

        match tracker.check_budget(&call.user_id) {
            Ok(_) => {
                match tracker.track_prediction(
                    &call.user_id,
                    &call.endpoint,
                    &call.model,
                    call.input_tokens,
                    call.output_tokens,
                ) {
                    Ok(cost) => println!("  ✓ Completed: ${:.4}\n", cost),
                    Err(e) => println!("  ✗ Failed: {}\n", e),
                }
            }
            Err(e) => {
                println!("  ✗ Budget check failed: {}\n", e);
            }
        }
    }

    let alert_total = alert_count.lock().unwrap();
    println!("Total alerts triggered: {}", *alert_total);

    Ok(())
}

/// Demo 3: Cost aggregation and reporting
fn demo_cost_reporting(tracker: &mut CostTracker) -> Result<()> {
    println!("\n═══════════════════════════════════════════════════════");
    println!("Demo 3: Cost Aggregation and Reporting");
    println!("═══════════════════════════════════════════════════════\n");

    // Process all simulated calls
    let calls = simulate_api_calls();

    println!("Processing {} API calls...\n", calls.len());

    for call in calls {
        tracker.track_prediction(
            &call.user_id,
            &call.endpoint,
            &call.model,
            call.input_tokens,
            call.output_tokens,
        )?;
    }

    // Aggregate by model
    println!("Cost by Model:");
    println!("─────────────────────────────────────────────────────");
    let by_model = tracker.aggregate_by_model(Duration::days(1));
    let mut model_costs: Vec<_> = by_model.iter().collect();
    model_costs.sort_by(|a, b| b.1.partial_cmp(a.1).unwrap());

    for (model, cost) in model_costs {
        println!("{:20} ${:>8.4}", model, cost);
    }

    // Aggregate by user
    println!("\n\nCost by User:");
    println!("─────────────────────────────────────────────────────");
    let by_user = tracker.aggregate_by_user(Duration::days(1));
    let mut user_costs: Vec<_> = by_user.iter().collect();
    user_costs.sort_by(|a, b| b.1.partial_cmp(a.1).unwrap());

    for (user, cost) in user_costs {
        println!("{:30} ${:>8.4}", user, cost);
    }

    // Aggregate by endpoint
    println!("\n\nCost by Endpoint:");
    println!("─────────────────────────────────────────────────────");
    let by_endpoint = tracker.aggregate_by_endpoint(Duration::days(1));
    let mut endpoint_costs: Vec<_> = by_endpoint.iter().collect();
    endpoint_costs.sort_by(|a, b| b.1.partial_cmp(a.1).unwrap());

    for (endpoint, cost) in endpoint_costs {
        println!("{:20} ${:>8.4}", endpoint, cost);
    }

    Ok(())
}

/// Demo 4: Comprehensive reports with recommendations
fn demo_comprehensive_report(tracker: &CostTracker) -> Result<()> {
    println!("\n\n═══════════════════════════════════════════════════════");
    println!("Demo 4: Comprehensive Cost Report");
    println!("═══════════════════════════════════════════════════════\n");

    // Generate full report
    let report = tracker.generate_report(None, None, Duration::days(1))?;

    // Display summary
    println!("{}", report.summary());

    // Display recommendations
    println!("\n\nOptimization Recommendations:");
    println!("─────────────────────────────────────────────────────");
    for (i, rec) in report.recommendations().iter().enumerate() {
        println!("{}. {}", i + 1, rec);
    }

    // Budget status
    println!("\n\nBudget Status:");
    println!("─────────────────────────────────────────────────────");
    let daily_cost = tracker.get_daily_cost(None);
    let monthly_cost = tracker.get_monthly_cost(None);
    let budget = tracker.get_budget();

    println!("Daily:");
    println!("  Spent: ${:.2}", daily_cost);
    println!("  Limit: ${:.2}", budget.daily_limit_usd);
    println!("  Remaining: ${:.2}", budget.remaining_daily(daily_cost));
    println!("  Utilization: {:.1}%", budget.utilization_daily(daily_cost));

    println!("\nMonthly:");
    println!("  Spent: ${:.2}", monthly_cost);
    println!("  Limit: ${:.2}", budget.monthly_limit_usd);
    println!("  Remaining: ${:.2}", budget.remaining_monthly(monthly_cost));
    println!("  Utilization: {:.1}%", budget.utilization_monthly(monthly_cost));

    // Forecast
    let forecast = tracker.forecast_monthly_cost()?;
    println!("\nProjected Monthly Cost: ${:.2}", forecast);
    if forecast > budget.monthly_limit_usd {
        println!("⚠️  WARNING: Forecast exceeds monthly budget by ${:.2}",
            forecast - budget.monthly_limit_usd);
    }

    Ok(())
}

/// Demo 5: User-specific analysis
fn demo_user_analysis(tracker: &CostTracker) -> Result<()> {
    println!("\n\n═══════════════════════════════════════════════════════");
    println!("Demo 5: User-Specific Cost Analysis");
    println!("═══════════════════════════════════════════════════════\n");

    let users = vec![
        "alice@example.com",
        "bob@example.com",
        "charlie@example.com",
        "dana@example.com",
        "eve@example.com",
    ];

    for user in users {
        println!("User: {}", user);
        println!("─────────────────────────────────────────────────────");

        let report = tracker.generate_report(
            Some(user),
            None,
            Duration::days(1),
        )?;

        println!("  Total Cost: ${:.4}", report.overall_stats.total_cost);
        println!("  Requests: {}", report.overall_stats.total_requests);
        println!("  Avg Cost/Request: ${:.4}", report.overall_stats.average_cost_per_request);
        println!("  Total Tokens: {}",
            report.overall_stats.total_input_tokens + report.overall_stats.total_output_tokens);

        // Most used model
        if let Some((model, _)) = report.top_models.first() {
            println!("  Primary Model: {}", model);
        }

        // Budget check
        let user_daily_cost = tracker.get_daily_cost(Some(user));
        let budget = tracker.get_budget();
        let util = (user_daily_cost / budget.per_user_daily_limit_usd) * 100.0;

        println!("  Daily Budget: ${:.2} / ${:.2} ({:.1}%)",
            user_daily_cost, budget.per_user_daily_limit_usd, util);

        if util > 80.0 {
            println!("  ⚠️  High budget utilization");
        }

        println!();
    }

    Ok(())
}

/// Demo 6: Model comparison
fn demo_model_comparison(tracker: &CostTracker) -> Result<()> {
    println!("\n═══════════════════════════════════════════════════════");
    println!("Demo 6: Model Cost Comparison");
    println!("═══════════════════════════════════════════════════════\n");

    let models = vec![
        "gpt-4-turbo",
        "gpt-4",
        "gpt-3.5-turbo",
        "claude-3-opus",
        "claude-3-sonnet",
        "claude-3-haiku",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
    ];

    println!("Cost comparison for 10,000 tokens (7,000 input, 3,000 output):\n");
    println!("{:20} {:>12} {:>12} {:>12}", "Model", "Input", "Output", "Total");
    println!("─────────────────────────────────────────────────────────────");

    for model in models {
        if let Some(pricing) = tracker.get_pricing(model) {
            let input_cost = pricing.calculate_cost(7000, 0);
            let output_cost = pricing.calculate_cost(0, 3000);
            let total_cost = pricing.calculate_cost(7000, 3000);

            println!("{:20} ${:>11.4} ${:>11.4} ${:>11.4}",
                model, input_cost, output_cost, total_cost);
        }
    }

    // Cost efficiency ranking
    println!("\n\nCost Efficiency Ranking (lowest to highest):");
    println!("─────────────────────────────────────────────────────");

    let mut efficiency: Vec<_> = tracker.aggregate_by_model(Duration::days(1))
        .into_iter()
        .collect();
    efficiency.sort_by(|a, b| a.1.partial_cmp(&b.1).unwrap());

    for (i, (model, cost)) in efficiency.iter().enumerate() {
        println!("{}. {:25} ${:.4}", i + 1, model, cost);
    }

    Ok(())
}

/// Demo 7: Export functionality
fn demo_export(tracker: &CostTracker) -> Result<()> {
    println!("\n\n═══════════════════════════════════════════════════════");
    println!("Demo 7: Data Export");
    println!("═══════════════════════════════════════════════════════\n");

    // Export to JSON
    let export_path = "/tmp/cost_tracking_export.json";
    tracker.export_json(export_path, Duration::days(1))?;
    println!("✓ Exported cost data to: {}", export_path);

    // Show sample records
    let records = tracker.get_records(Duration::days(1));
    println!("\nSample records (showing first 3):");
    println!("─────────────────────────────────────────────────────");

    for record in records.iter().take(3) {
        println!("User: {}", record.user_id);
        println!("  Model: {}", record.model);
        println!("  Endpoint: {}", record.endpoint);
        println!("  Tokens: {} in, {} out", record.input_tokens, record.output_tokens);
        println!("  Cost: ${:.4}", record.cost_usd);
        println!("  Time: {}\n", record.timestamp.format("%Y-%m-%d %H:%M:%S"));
    }

    println!("Total records: {}", records.len());

    Ok(())
}

fn main() -> Result<()> {
    println!("\n");
    println!("╔═══════════════════════════════════════════════════════╗");
    println!("║  LM API Cost Tracking and Budgeting Demo             ║");
    println!("╚═══════════════════════════════════════════════════════╝");

    // Create main tracker
    let mut tracker = CostTracker::new("pricing.json")?;

    // Run demos
    demo_basic_tracking(&mut tracker)?;
    demo_budget_enforcement()?;
    demo_cost_reporting(&mut tracker)?;
    demo_comprehensive_report(&tracker)?;
    demo_user_analysis(&tracker)?;
    demo_model_comparison(&tracker)?;
    demo_export(&tracker)?;

    // Final summary
    println!("\n\n═══════════════════════════════════════════════════════");
    println!("Demo Complete - Final Summary");
    println!("═══════════════════════════════════════════════════════\n");

    let daily_cost = tracker.get_daily_cost(None);
    let records = tracker.get_records(Duration::days(1));

    println!("Total API calls tracked: {}", records.len());
    println!("Total cost: ${:.2}", daily_cost);
    println!("Average cost per call: ${:.4}", daily_cost / records.len() as f64);

    println!("\n✓ All demos completed successfully!");
    println!("\nNext steps:");
    println!("  • Review the exported data in /tmp/cost_tracking_export.json");
    println!("  • Customize pricing.json with your actual pricing");
    println!("  • Integrate CostTracker into your application");
    println!("  • Set up budget alerts for your team");
    println!("  • Monitor and optimize based on recommendations\n");

    Ok(())
}
