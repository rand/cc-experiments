use anyhow::{anyhow, Context, Result};
use chrono::{DateTime, Duration, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::Path;

/// Model pricing information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelPricing {
    /// Cost per 1000 input tokens in USD
    pub input_cost_per_1k: f64,
    /// Cost per 1000 output tokens in USD
    pub output_cost_per_1k: f64,
    /// Maximum context window size
    pub context_window: usize,
}

impl ModelPricing {
    pub fn new(input_cost: f64, output_cost: f64, context_window: usize) -> Self {
        Self {
            input_cost_per_1k: input_cost,
            output_cost_per_1k: output_cost,
            context_window,
        }
    }

    /// Calculate cost for given token counts
    pub fn calculate_cost(&self, input_tokens: usize, output_tokens: usize) -> f64 {
        let input_cost = (input_tokens as f64 / 1000.0) * self.input_cost_per_1k;
        let output_cost = (output_tokens as f64 / 1000.0) * self.output_cost_per_1k;
        input_cost + output_cost
    }

    /// Check if token count exceeds context window
    pub fn exceeds_context(&self, tokens: usize) -> bool {
        tokens > self.context_window
    }

    /// Calculate cost per token (weighted average)
    pub fn cost_per_token(&self) -> f64 {
        // Assume 70% input, 30% output for average
        (self.input_cost_per_1k * 0.7 + self.output_cost_per_1k * 0.3) / 1000.0
    }
}

/// Budget configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CostBudget {
    /// Daily limit in USD
    pub daily_limit_usd: f64,
    /// Monthly limit in USD
    pub monthly_limit_usd: f64,
    /// Per-user daily limit in USD
    pub per_user_daily_limit_usd: f64,
    /// Alert threshold as percentage (0.0-1.0)
    pub alert_threshold_percent: f64,
}

impl CostBudget {
    pub fn builder() -> CostBudgetBuilder {
        CostBudgetBuilder::default()
    }

    /// Check if daily limit is exceeded
    pub fn is_daily_exceeded(&self, current_cost: f64) -> bool {
        current_cost >= self.daily_limit_usd
    }

    /// Check if monthly limit is exceeded
    pub fn is_monthly_exceeded(&self, current_cost: f64) -> bool {
        current_cost >= self.monthly_limit_usd
    }

    /// Check if user daily limit is exceeded
    pub fn is_user_daily_exceeded(&self, current_cost: f64) -> bool {
        current_cost >= self.per_user_daily_limit_usd
    }

    /// Check if alert threshold is reached
    pub fn should_alert(&self, current_cost: f64, limit: f64) -> bool {
        current_cost >= (limit * self.alert_threshold_percent)
    }

    /// Get remaining budget
    pub fn remaining_daily(&self, current_cost: f64) -> f64 {
        (self.daily_limit_usd - current_cost).max(0.0)
    }

    pub fn remaining_monthly(&self, current_cost: f64) -> f64 {
        (self.monthly_limit_usd - current_cost).max(0.0)
    }

    /// Get budget utilization percentage
    pub fn utilization_daily(&self, current_cost: f64) -> f64 {
        (current_cost / self.daily_limit_usd * 100.0).min(100.0)
    }

    pub fn utilization_monthly(&self, current_cost: f64) -> f64 {
        (current_cost / self.monthly_limit_usd * 100.0).min(100.0)
    }
}

/// Builder for CostBudget
#[derive(Default)]
pub struct CostBudgetBuilder {
    daily_limit: Option<f64>,
    monthly_limit: Option<f64>,
    per_user_daily_limit: Option<f64>,
    alert_threshold: Option<f64>,
}

impl CostBudgetBuilder {
    pub fn daily_limit(mut self, limit: f64) -> Self {
        self.daily_limit = Some(limit);
        self
    }

    pub fn monthly_limit(mut self, limit: f64) -> Self {
        self.monthly_limit = Some(limit);
        self
    }

    pub fn per_user_daily_limit(mut self, limit: f64) -> Self {
        self.per_user_daily_limit = Some(limit);
        self
    }

    pub fn alert_threshold(mut self, threshold: f64) -> Self {
        self.alert_threshold = Some(threshold);
        self
    }

    pub fn build(self) -> CostBudget {
        CostBudget {
            daily_limit_usd: self.daily_limit.unwrap_or(100.0),
            monthly_limit_usd: self.monthly_limit.unwrap_or(2000.0),
            per_user_daily_limit_usd: self.per_user_daily_limit.unwrap_or(10.0),
            alert_threshold_percent: self.alert_threshold.unwrap_or(0.80),
        }
    }
}

/// Alert level for budget notifications
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum AlertLevel {
    Warning,
    Critical,
    Exceeded,
}

/// Budget alert
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BudgetAlert {
    pub level: AlertLevel,
    pub message: String,
    pub current_cost: f64,
    pub limit: f64,
    pub utilization: f64,
    pub timestamp: DateTime<Utc>,
}

impl BudgetAlert {
    pub fn new(
        level: AlertLevel,
        message: String,
        current_cost: f64,
        limit: f64,
    ) -> Self {
        let utilization = (current_cost / limit * 100.0).min(100.0);
        Self {
            level,
            message,
            current_cost,
            limit,
            utilization,
            timestamp: Utc::now(),
        }
    }
}

/// Individual cost record
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CostRecord {
    pub user_id: String,
    pub endpoint: String,
    pub model: String,
    pub input_tokens: usize,
    pub output_tokens: usize,
    pub cost_usd: f64,
    pub timestamp: DateTime<Utc>,
}

impl CostRecord {
    pub fn new(
        user_id: String,
        endpoint: String,
        model: String,
        input_tokens: usize,
        output_tokens: usize,
        cost_usd: f64,
    ) -> Self {
        Self {
            user_id,
            endpoint,
            model,
            input_tokens,
            output_tokens,
            cost_usd,
            timestamp: Utc::now(),
        }
    }

    pub fn total_tokens(&self) -> usize {
        self.input_tokens + self.output_tokens
    }
}

/// Aggregated cost statistics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CostStats {
    pub total_cost: f64,
    pub total_requests: usize,
    pub total_input_tokens: usize,
    pub total_output_tokens: usize,
    pub average_cost_per_request: f64,
    pub average_tokens_per_request: f64,
}

impl CostStats {
    pub fn new() -> Self {
        Self {
            total_cost: 0.0,
            total_requests: 0,
            total_input_tokens: 0,
            total_output_tokens: 0,
            average_cost_per_request: 0.0,
            average_tokens_per_request: 0.0,
        }
    }

    pub fn add_record(&mut self, record: &CostRecord) {
        self.total_cost += record.cost_usd;
        self.total_requests += 1;
        self.total_input_tokens += record.input_tokens;
        self.total_output_tokens += record.output_tokens;

        if self.total_requests > 0 {
            self.average_cost_per_request = self.total_cost / self.total_requests as f64;
            self.average_tokens_per_request =
                (self.total_input_tokens + self.total_output_tokens) as f64
                / self.total_requests as f64;
        }
    }
}

/// Cost report
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CostReport {
    pub period_start: DateTime<Utc>,
    pub period_end: DateTime<Utc>,
    pub overall_stats: CostStats,
    pub by_model: HashMap<String, CostStats>,
    pub by_user: HashMap<String, CostStats>,
    pub by_endpoint: HashMap<String, CostStats>,
    pub top_users: Vec<(String, f64)>,
    pub top_models: Vec<(String, f64)>,
    pub recommendations: Vec<String>,
}

impl CostReport {
    pub fn new(period_start: DateTime<Utc>, period_end: DateTime<Utc>) -> Self {
        Self {
            period_start,
            period_end,
            overall_stats: CostStats::new(),
            by_model: HashMap::new(),
            by_user: HashMap::new(),
            by_endpoint: HashMap::new(),
            top_users: Vec::new(),
            top_models: Vec::new(),
            recommendations: Vec::new(),
        }
    }

    pub fn summary(&self) -> String {
        let duration = self.period_end - self.period_start;
        format!(
            "Cost Report ({} days)\n\
             ====================\n\
             Total Cost: ${:.2}\n\
             Total Requests: {}\n\
             Total Tokens: {} (input: {}, output: {})\n\
             Avg Cost/Request: ${:.4}\n\
             Avg Tokens/Request: {:.0}\n\
             \n\
             Top 5 Models:\n{}\n\
             \n\
             Top 5 Users:\n{}",
            duration.num_days(),
            self.overall_stats.total_cost,
            self.overall_stats.total_requests,
            self.overall_stats.total_input_tokens + self.overall_stats.total_output_tokens,
            self.overall_stats.total_input_tokens,
            self.overall_stats.total_output_tokens,
            self.overall_stats.average_cost_per_request,
            self.overall_stats.average_tokens_per_request,
            self.format_top_list(&self.top_models, 5),
            self.format_top_list(&self.top_users, 5),
        )
    }

    fn format_top_list(&self, list: &[(String, f64)], limit: usize) -> String {
        list.iter()
            .take(limit)
            .enumerate()
            .map(|(i, (name, cost))| format!("  {}. {}: ${:.2}", i + 1, name, cost))
            .collect::<Vec<_>>()
            .join("\n")
    }

    pub fn recommendations(&self) -> &[String] {
        &self.recommendations
    }
}

/// Pricing database loaded from JSON
#[derive(Debug, Clone, Serialize, Deserialize)]
struct PricingDatabase {
    models: HashMap<String, ModelPricing>,
    default_budget: CostBudget,
}

/// Main cost tracker
pub struct CostTracker {
    pricing: HashMap<String, ModelPricing>,
    budget: CostBudget,
    records: Vec<CostRecord>,
    alert_handlers: Vec<Box<dyn Fn(&BudgetAlert) + Send + Sync>>,
}

impl CostTracker {
    /// Create a new cost tracker from pricing file
    pub fn new<P: AsRef<Path>>(pricing_path: P) -> Result<Self> {
        let content = fs::read_to_string(pricing_path.as_ref())
            .context("Failed to read pricing file")?;

        let db: PricingDatabase = serde_json::from_str(&content)
            .context("Failed to parse pricing file")?;

        Ok(Self {
            pricing: db.models,
            budget: db.default_budget,
            records: Vec::new(),
            alert_handlers: Vec::new(),
        })
    }

    /// Create with custom budget
    pub fn with_budget<P: AsRef<Path>>(pricing_path: P, budget: CostBudget) -> Result<Self> {
        let mut tracker = Self::new(pricing_path)?;
        tracker.budget = budget;
        Ok(tracker)
    }

    /// Add custom model pricing
    pub fn add_model_pricing(&mut self, model: String, pricing: ModelPricing) -> Result<()> {
        if self.pricing.contains_key(&model) {
            return Err(anyhow!("Model '{}' already exists", model));
        }
        self.pricing.insert(model, pricing);
        Ok(())
    }

    /// Update existing model pricing
    pub fn update_model_pricing(&mut self, model: &str, pricing: ModelPricing) -> Result<()> {
        if !self.pricing.contains_key(model) {
            return Err(anyhow!("Model '{}' not found", model));
        }
        self.pricing.insert(model.to_string(), pricing);
        Ok(())
    }

    /// Get model pricing
    pub fn get_pricing(&self, model: &str) -> Option<&ModelPricing> {
        self.pricing.get(model)
    }

    /// Register alert handler
    pub fn on_alert<F>(&mut self, handler: F)
    where
        F: Fn(&BudgetAlert) + Send + Sync + 'static,
    {
        self.alert_handlers.push(Box::new(handler));
    }

    /// Track a prediction and return its cost
    pub fn track_prediction(
        &mut self,
        user_id: &str,
        endpoint: &str,
        model: &str,
        input_tokens: usize,
        output_tokens: usize,
    ) -> Result<f64> {
        let pricing = self.pricing.get(model)
            .ok_or_else(|| anyhow!("Model '{}' not found in pricing database", model))?;

        // Check context window
        let total_tokens = input_tokens + output_tokens;
        if pricing.exceeds_context(total_tokens) {
            return Err(anyhow!(
                "Token count {} exceeds context window {} for model '{}'",
                total_tokens,
                pricing.context_window,
                model
            ));
        }

        // Calculate cost
        let cost = pricing.calculate_cost(input_tokens, output_tokens);

        // Record
        let record = CostRecord::new(
            user_id.to_string(),
            endpoint.to_string(),
            model.to_string(),
            input_tokens,
            output_tokens,
            cost,
        );

        self.records.push(record);

        Ok(cost)
    }

    /// Check if budget allows the request
    pub fn check_budget(&self, user_id: &str) -> Result<()> {
        let daily_cost = self.get_daily_cost(None);
        let monthly_cost = self.get_monthly_cost(None);
        let user_daily_cost = self.get_daily_cost(Some(user_id));

        // Check daily limit
        if self.budget.is_daily_exceeded(daily_cost) {
            return Err(anyhow!(
                "Daily budget limit exceeded: ${:.2} / ${:.2}",
                daily_cost,
                self.budget.daily_limit_usd
            ));
        }

        // Check monthly limit
        if self.budget.is_monthly_exceeded(monthly_cost) {
            return Err(anyhow!(
                "Monthly budget limit exceeded: ${:.2} / ${:.2}",
                monthly_cost,
                self.budget.monthly_limit_usd
            ));
        }

        // Check user daily limit
        if self.budget.is_user_daily_exceeded(user_daily_cost) {
            return Err(anyhow!(
                "User daily budget limit exceeded: ${:.2} / ${:.2}",
                user_daily_cost,
                self.budget.per_user_daily_limit_usd
            ));
        }

        // Check alert thresholds
        if self.budget.should_alert(daily_cost, self.budget.daily_limit_usd) {
            self.trigger_alert(BudgetAlert::new(
                AlertLevel::Warning,
                format!("Daily budget at {:.0}%", self.budget.utilization_daily(daily_cost)),
                daily_cost,
                self.budget.daily_limit_usd,
            ));
        }

        if self.budget.should_alert(monthly_cost, self.budget.monthly_limit_usd) {
            self.trigger_alert(BudgetAlert::new(
                AlertLevel::Warning,
                format!("Monthly budget at {:.0}%", self.budget.utilization_monthly(monthly_cost)),
                monthly_cost,
                self.budget.monthly_limit_usd,
            ));
        }

        Ok(())
    }

    fn trigger_alert(&self, alert: BudgetAlert) {
        for handler in &self.alert_handlers {
            handler(&alert);
        }
    }

    /// Get total cost for a time period
    fn get_cost_for_period(&self, duration: Duration, user_id: Option<&str>) -> f64 {
        let cutoff = Utc::now() - duration;
        self.records
            .iter()
            .filter(|r| r.timestamp >= cutoff)
            .filter(|r| user_id.map_or(true, |u| r.user_id == u))
            .map(|r| r.cost_usd)
            .sum()
    }

    /// Get daily cost
    pub fn get_daily_cost(&self, user_id: Option<&str>) -> f64 {
        self.get_cost_for_period(Duration::days(1), user_id)
    }

    /// Get monthly cost
    pub fn get_monthly_cost(&self, user_id: Option<&str>) -> f64 {
        self.get_cost_for_period(Duration::days(30), user_id)
    }

    /// Aggregate costs by model
    pub fn aggregate_by_model(&self, duration: Duration) -> HashMap<String, f64> {
        let cutoff = Utc::now() - duration;
        let mut aggregation = HashMap::new();

        for record in self.records.iter().filter(|r| r.timestamp >= cutoff) {
            *aggregation.entry(record.model.clone()).or_insert(0.0) += record.cost_usd;
        }

        aggregation
    }

    /// Aggregate costs by user
    pub fn aggregate_by_user(&self, duration: Duration) -> HashMap<String, f64> {
        let cutoff = Utc::now() - duration;
        let mut aggregation = HashMap::new();

        for record in self.records.iter().filter(|r| r.timestamp >= cutoff) {
            *aggregation.entry(record.user_id.clone()).or_insert(0.0) += record.cost_usd;
        }

        aggregation
    }

    /// Aggregate costs by endpoint
    pub fn aggregate_by_endpoint(&self, duration: Duration) -> HashMap<String, f64> {
        let cutoff = Utc::now() - duration;
        let mut aggregation = HashMap::new();

        for record in self.records.iter().filter(|r| r.timestamp >= cutoff) {
            *aggregation.entry(record.endpoint.clone()).or_insert(0.0) += record.cost_usd;
        }

        aggregation
    }

    /// Generate comprehensive cost report
    pub fn generate_report(
        &self,
        user_id: Option<&str>,
        model: Option<&str>,
        duration: Duration,
    ) -> Result<CostReport> {
        let cutoff = Utc::now() - duration;
        let period_start = cutoff;
        let period_end = Utc::now();

        let mut report = CostReport::new(period_start, period_end);

        // Filter records
        let filtered_records: Vec<_> = self.records
            .iter()
            .filter(|r| r.timestamp >= cutoff)
            .filter(|r| user_id.map_or(true, |u| r.user_id == u))
            .filter(|r| model.map_or(true, |m| r.model == m))
            .collect();

        // Overall stats
        for record in &filtered_records {
            report.overall_stats.add_record(record);
        }

        // By model
        for record in &filtered_records {
            report.by_model
                .entry(record.model.clone())
                .or_insert_with(CostStats::new)
                .add_record(record);
        }

        // By user
        for record in &filtered_records {
            report.by_user
                .entry(record.user_id.clone())
                .or_insert_with(CostStats::new)
                .add_record(record);
        }

        // By endpoint
        for record in &filtered_records {
            report.by_endpoint
                .entry(record.endpoint.clone())
                .or_insert_with(CostStats::new)
                .add_record(record);
        }

        // Top users
        let mut user_costs: Vec<_> = report.by_user
            .iter()
            .map(|(k, v)| (k.clone(), v.total_cost))
            .collect();
        user_costs.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());
        report.top_users = user_costs;

        // Top models
        let mut model_costs: Vec<_> = report.by_model
            .iter()
            .map(|(k, v)| (k.clone(), v.total_cost))
            .collect();
        model_costs.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());
        report.top_models = model_costs;

        // Generate recommendations
        report.recommendations = self.generate_recommendations(&report);

        Ok(report)
    }

    fn generate_recommendations(&self, report: &CostReport) -> Vec<String> {
        let mut recommendations = Vec::new();

        // Check for expensive models
        if let Some((expensive_model, cost)) = report.top_models.first() {
            if *cost > report.overall_stats.total_cost * 0.5 {
                if expensive_model.contains("gpt-4") && !expensive_model.contains("turbo") {
                    recommendations.push(format!(
                        "Consider switching from {} to GPT-4 Turbo for a 67% cost reduction",
                        expensive_model
                    ));
                } else if expensive_model.contains("claude-3-opus") {
                    recommendations.push(
                        "Consider using Claude 3 Sonnet for less complex tasks (80% cost reduction)".to_string()
                    );
                }
            }
        }

        // Check token efficiency
        if report.overall_stats.average_tokens_per_request > 5000.0 {
            recommendations.push(
                "High average token usage detected. Consider prompt optimization or response caching".to_string()
            );
        }

        // Check user distribution
        if let Some((top_user, cost)) = report.top_users.first() {
            if *cost > report.overall_stats.total_cost * 0.7 {
                recommendations.push(format!(
                    "User '{}' accounts for {:.0}% of costs. Consider implementing user-specific quotas",
                    top_user,
                    (*cost / report.overall_stats.total_cost) * 100.0
                ));
            }
        }

        // Budget utilization
        let daily_util = self.budget.utilization_daily(self.get_daily_cost(None));
        if daily_util > 90.0 {
            recommendations.push(
                "Daily budget utilization above 90%. Consider increasing limits or optimizing usage".to_string()
            );
        }

        // Low-cost alternatives
        let has_expensive_models = report.by_model.keys()
            .any(|m| m.contains("gpt-4") || m.contains("opus"));
        let has_cheap_models = report.by_model.keys()
            .any(|m| m.contains("3.5") || m.contains("haiku") || m.contains("llama"));

        if has_expensive_models && !has_cheap_models {
            recommendations.push(
                "All requests use premium models. Consider cheaper alternatives for simple tasks".to_string()
            );
        }

        recommendations
    }

    /// Forecast monthly cost based on current trend
    pub fn forecast_monthly_cost(&self) -> Result<f64> {
        let last_7_days_cost = self.get_cost_for_period(Duration::days(7), None);
        let daily_average = last_7_days_cost / 7.0;
        let forecast = daily_average * 30.0;
        Ok(forecast)
    }

    /// Export cost data to JSON
    pub fn export_json<P: AsRef<Path>>(&self, path: P, duration: Duration) -> Result<()> {
        let cutoff = Utc::now() - duration;
        let filtered_records: Vec<_> = self.records
            .iter()
            .filter(|r| r.timestamp >= cutoff)
            .cloned()
            .collect();

        let json = serde_json::to_string_pretty(&filtered_records)
            .context("Failed to serialize records")?;

        fs::write(path, json).context("Failed to write JSON file")?;
        Ok(())
    }

    /// Get all records within duration
    pub fn get_records(&self, duration: Duration) -> Vec<&CostRecord> {
        let cutoff = Utc::now() - duration;
        self.records
            .iter()
            .filter(|r| r.timestamp >= cutoff)
            .collect()
    }

    /// Clear old records
    pub fn clear_old_records(&mut self, keep_duration: Duration) {
        let cutoff = Utc::now() - keep_duration;
        self.records.retain(|r| r.timestamp >= cutoff);
    }

    /// Get current budget
    pub fn get_budget(&self) -> &CostBudget {
        &self.budget
    }

    /// Update budget
    pub fn set_budget(&mut self, budget: CostBudget) {
        self.budget = budget;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_model_pricing_calculation() {
        let pricing = ModelPricing::new(0.01, 0.03, 128000);
        let cost = pricing.calculate_cost(1000, 500);
        assert!((cost - 0.025).abs() < 0.001);
    }

    #[test]
    fn test_budget_limits() {
        let budget = CostBudget::builder()
            .daily_limit(100.0)
            .monthly_limit(2000.0)
            .build();

        assert!(!budget.is_daily_exceeded(50.0));
        assert!(budget.is_daily_exceeded(100.0));
        assert!(budget.is_daily_exceeded(150.0));
    }

    #[test]
    fn test_budget_alerts() {
        let budget = CostBudget::builder()
            .daily_limit(100.0)
            .alert_threshold(0.80)
            .build();

        assert!(!budget.should_alert(70.0, 100.0));
        assert!(budget.should_alert(80.0, 100.0));
        assert!(budget.should_alert(90.0, 100.0));
    }

    #[test]
    fn test_cost_stats() {
        let mut stats = CostStats::new();

        let record = CostRecord::new(
            "user1".to_string(),
            "api/chat".to_string(),
            "gpt-4".to_string(),
            1000,
            500,
            0.045,
        );

        stats.add_record(&record);

        assert_eq!(stats.total_requests, 1);
        assert!((stats.total_cost - 0.045).abs() < 0.001);
        assert_eq!(stats.total_input_tokens, 1000);
        assert_eq!(stats.total_output_tokens, 500);
    }
}
