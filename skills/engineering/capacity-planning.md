---
name: engineering-capacity-planning
description: Comprehensive capacity planning including forecasting, resource modeling, load testing, scaling strategies, cost optimization, and disaster recovery planning for production systems
---

# Capacity Planning

**Scope**: Forecasting methods, resource modeling (CPU/memory/disk/network), load testing, scaling strategies (vertical/horizontal/auto-scaling), cost optimization, cloud resource planning, database capacity planning, traffic analysis, disaster recovery capacity

**Lines**: ~850

**Last Updated**: 2025-10-27

**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Planning capacity for new services or features
- Forecasting future resource needs
- Conducting load testing and stress testing
- Designing auto-scaling policies
- Optimizing cloud costs
- Planning database capacity and scaling
- Analyzing traffic patterns and growth
- Sizing disaster recovery infrastructure
- Preparing for seasonal traffic spikes
- Evaluating scaling architecture decisions

Don't use this skill for:
- Real-time monitoring (see `monitoring-alerts.md`)
- Incident response (see `incident-response.md`)
- Performance optimization (see `performance-optimization.md`)
- Cost tracking (see `cloud-cost-management.md`)

---

## Core Concepts

### Concept 1: Capacity Planning Fundamentals

**Definition**: Proactive planning to ensure systems have sufficient resources to meet current and future demand

**Key Principles**:
```
Measure → Forecast → Plan → Provision → Monitor
   ↓         ↓        ↓        ↓          ↓
Current   Future   Resource  Deploy    Validate
 Usage    Demand   Sizing    Changes   Results
```

**Planning Horizons**:
```
Immediate (Days-Weeks):
├─ Handle current load spikes
├─ Address urgent capacity constraints
└─ Emergency scaling

Short-term (1-3 Months):
├─ Known launches or campaigns
├─ Seasonal patterns
└─ Planned migrations

Long-term (6-12+ Months):
├─ Business growth projections
├─ Architecture changes
└─ Strategic planning
```

**Resource Types**:
- **Compute**: CPU cores, vCPUs, processing power
- **Memory**: RAM for application workloads
- **Storage**: Disk space, IOPS, throughput
- **Network**: Bandwidth, connections, latency
- **Application**: Connection pools, worker threads, queues

---

### Concept 2: Forecasting Methods

**Definition**: Predict future resource usage based on historical data and growth patterns

**Linear Forecasting**:
```python
# Simple linear regression
# Usage = baseline + growth_rate * time
# Best for: Steady, predictable growth

future_usage = current_usage + (growth_rate * time_periods)

# Example: 100 GB today, growing 10 GB/month
# In 6 months: 100 + (10 * 6) = 160 GB
```

**Exponential Forecasting**:
```python
# Exponential growth
# Usage = baseline * (1 + growth_rate) ^ time
# Best for: Viral growth, compound growth

future_usage = current_usage * ((1 + growth_rate) ** time_periods)

# Example: 1000 users, growing 20%/month
# In 6 months: 1000 * (1.2^6) = 2,986 users
```

**Seasonal Forecasting (Prophet)**:
```python
# Facebook Prophet for seasonal patterns
# Best for: Weekly/monthly patterns, holidays

from prophet import Prophet

df = pd.DataFrame({
    'ds': dates,      # Date column
    'y': usage        # Usage metric
})

model = Prophet(
    yearly_seasonality=True,
    weekly_seasonality=True,
    daily_seasonality=False
)
model.fit(df)

# Forecast 90 days
future = model.make_future_dataframe(periods=90)
forecast = model.predict(future)
```

**Time-Series Analysis (ARIMA)**:
```python
# ARIMA for complex patterns
# Best for: Multiple trends, autocorrelation

from statsmodels.tsa.arima.model import ARIMA

model = ARIMA(usage_data, order=(p, d, q))
fitted = model.fit()

# Forecast next 30 days
forecast = fitted.forecast(steps=30)
```

**Machine Learning (LSTM)**:
```python
# Neural networks for complex patterns
# Best for: Non-linear relationships, multiple features

from tensorflow.keras import Sequential
from tensorflow.keras.layers import LSTM, Dense

model = Sequential([
    LSTM(50, return_sequences=True, input_shape=(lookback, features)),
    LSTM(50),
    Dense(1)
])

model.compile(optimizer='adam', loss='mse')
model.fit(X_train, y_train, epochs=50)
```

---

### Concept 3: Resource Modeling

**Definition**: Model resource consumption based on workload characteristics

**CPU Modeling**:
```
CPU_needed = (requests_per_second * cpu_per_request) / cores_per_instance

Example:
- 1000 req/sec
- 10ms CPU per request
- 4 vCPU per instance

CPU_usage = (1000 * 0.010) / 4 = 2.5 cores (62.5% utilization)

Add headroom: 2.5 / 0.7 = 3.6 cores → Need 1 instance
```

**Memory Modeling**:
```
Memory_needed = base_memory + (connections * memory_per_connection)

Example:
- Base: 500 MB
- 1000 concurrent connections
- 2 MB per connection

Memory = 500 + (1000 * 2) = 2500 MB = 2.5 GB

Add headroom: 2.5 / 0.8 = 3.1 GB → Need 4 GB instance
```

**Storage Modeling**:
```
Storage_growth = current_size + (daily_growth * days) + retention

Example:
- Current: 1 TB
- Growth: 10 GB/day
- Forecast: 180 days
- Retention: 90 days

Storage = 1000 + (10 * 180) + (10 * 90) = 2800 GB = 2.8 TB

Add safety margin (20%): 2.8 * 1.2 = 3.4 TB
```

**Network Modeling**:
```
Bandwidth = (requests_per_second * avg_response_size) / (1024 * 1024)

Example:
- 5000 req/sec
- 50 KB avg response

Bandwidth = (5000 * 50) / 1024 = 244 MB/sec ≈ 2 Gbps

Peak traffic (3x): 6 Gbps required
```

---

## Patterns

### Pattern 1: Headroom and Safety Margins

**Problem**: Systems fail when running at 100% capacity

**Headroom Strategy**:
```
Resource Type    | Target Utilization | Safety Margin
-----------------|-------------------|---------------
CPU              | 70%               | 30%
Memory           | 80%               | 20%
Disk Space       | 80%               | 20%
IOPS             | 75%               | 25%
Network          | 60%               | 40%
Connection Pools | 75%               | 25%
```

**Why Headroom Matters**:
```
Without Headroom (100% target):
├─ No room for traffic spikes
├─ Deployment requires downtime
├─ Single failure cascades
└─ Performance degradation

With Headroom (70% target):
├─ Handles 43% traffic increase
├─ Rolling deployments safe
├─ Failure tolerance
└─ Consistent performance
```

**Calculating Headroom**:
```python
def calculate_headroom(current_usage, capacity, target_util=0.7):
    """Calculate remaining headroom."""
    current_util = current_usage / capacity
    remaining = (target_util - current_util) * capacity
    return {
        'current_utilization': current_util,
        'remaining_headroom': remaining,
        'time_to_capacity': estimate_time_to_capacity(current_usage, remaining)
    }
```

---

### Pattern 2: Load Testing Strategy

**Problem**: Need to validate capacity under realistic load

**Load Testing Pyramid**:
```
                  ┌─────────────────┐
                  │  Chaos Testing  │  (Rare, extreme scenarios)
                  └─────────────────┘
                ┌───────────────────────┐
                │   Stress Testing      │  (Beyond limits)
                └───────────────────────┘
            ┌───────────────────────────────┐
            │     Load Testing              │  (Expected peak)
            └───────────────────────────────┘
        ┌───────────────────────────────────────┐
        │      Baseline Testing                 │  (Normal load)
        └───────────────────────────────────────┘
```

**Load Test Types**:
```yaml
Baseline Test:
  duration: 10 minutes
  load: Normal traffic (e.g., 100 req/sec)
  goal: Establish performance baseline
  metrics: P50, P95, P99 latency, error rate

Load Test:
  duration: 30 minutes
  load: Expected peak (e.g., 500 req/sec)
  goal: Verify capacity for known peaks
  metrics: Latency, throughput, resource usage

Stress Test:
  duration: 15 minutes
  load: Beyond peak (e.g., 1000 req/sec)
  goal: Find breaking point
  metrics: When does it fail? How does it fail?

Soak Test:
  duration: 4-24 hours
  load: Sustained normal-high load
  goal: Find memory leaks, resource exhaustion
  metrics: Memory growth, connection leaks

Spike Test:
  duration: 2 minutes
  load: Sudden 10x increase
  goal: Validate auto-scaling response
  metrics: Scale-up time, recovery time
```

**Locust Load Test Example**:
```python
from locust import HttpUser, task, between

class APIUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def get_items(self):
        self.client.get("/api/items")

    @task(1)
    def create_item(self):
        self.client.post("/api/items", json={
            "name": "test",
            "value": 42
        })

# Run: locust -f loadtest.py --users 1000 --spawn-rate 10
```

---

### Pattern 3: Auto-Scaling Strategy

**Problem**: Manual scaling is slow and error-prone

**Horizontal Pod Autoscaler (Kubernetes)**:
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api
  minReplicas: 3
  maxReplicas: 20
  metrics:
    # CPU-based scaling
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70

    # Memory-based scaling
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80

    # Custom metric (RPS)
    - type: Pods
      pods:
        metric:
          name: requests_per_second
        target:
          type: AverageValue
          averageValue: "100"

  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300  # Wait 5 min before scale down
      policies:
      - type: Percent
        value: 50                       # Remove max 50% of pods
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0     # Scale up immediately
      policies:
      - type: Percent
        value: 100                      # Double pods if needed
        periodSeconds: 30
      - type: Pods
        value: 5                        # Add max 5 pods
        periodSeconds: 30
```

**AWS Auto Scaling**:
```json
{
  "ServiceNamespace": "ecs",
  "ScalableDimension": "ecs:service:DesiredCount",
  "PolicyType": "TargetTrackingScaling",
  "TargetTrackingScalingPolicyConfiguration": {
    "TargetValue": 70.0,
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "ECSServiceAverageCPUUtilization"
    },
    "ScaleOutCooldown": 60,
    "ScaleInCooldown": 300
  }
}
```

**Scaling Triggers**:
```
Metric Type       | Scale Up Threshold | Scale Down Threshold
------------------|--------------------|-----------------------
CPU               | >70% for 2 min    | <30% for 10 min
Memory            | >80% for 2 min    | <40% for 10 min
Request Rate      | >80% capacity     | <40% capacity
Response Time     | P95 > 500ms       | P95 < 200ms
Queue Depth       | >100 messages     | <10 messages
Error Rate        | >1%               | <0.1%
```

---

### Pattern 4: Cost Optimization

**Problem**: Over-provisioning wastes money, under-provisioning hurts users

**Cost Optimization Strategies**:
```
1. Right-sizing:
   ├─ Analyze actual usage vs provisioned
   ├─ Downsize over-provisioned resources
   └─ Use smaller instance types where possible

2. Reserved/Committed Capacity:
   ├─ 1-year commitment: ~30% discount
   ├─ 3-year commitment: ~50% discount
   └─ Use for baseline capacity

3. Spot/Preemptible Instances:
   ├─ 70-90% discount
   ├─ Use for batch workloads
   └─ Fault-tolerant services

4. Auto-scaling:
   ├─ Scale down during off-peak
   ├─ Match capacity to demand
   └─ Avoid idle resources

5. Storage Tiering:
   ├─ Hot data: SSD
   ├─ Warm data: HDD
   └─ Cold data: Archive (S3 Glacier)
```

**Cost Analysis**:
```python
def analyze_cost_optimization(resources):
    """Identify cost optimization opportunities."""

    opportunities = []

    for resource in resources:
        utilization = resource.avg_utilization
        cost = resource.monthly_cost

        # Under-utilized (< 30% for 30 days)
        if utilization < 0.30:
            savings = cost * 0.5  # Estimate 50% savings
            opportunities.append({
                'resource': resource.name,
                'action': 'Downsize or terminate',
                'current_util': utilization,
                'potential_savings': savings
            })

        # No reservation (stable workload)
        if not resource.is_reserved and resource.age_days > 90:
            savings = cost * 0.35  # 35% with 1-year RI
            opportunities.append({
                'resource': resource.name,
                'action': 'Purchase reserved capacity',
                'potential_savings': savings
            })

    return opportunities
```

---

## Checklist

### Capacity Planning Checklist

**Data Collection**:
- [ ] Collect 30+ days of historical metrics
- [ ] Identify all resource types (CPU, memory, disk, network)
- [ ] Document current capacity and utilization
- [ ] Identify peak usage patterns
- [ ] Collect business growth projections
- [ ] Document seasonal patterns
- [ ] Identify upcoming launches or campaigns

**Forecasting**:
- [ ] Choose forecasting method (linear, exponential, seasonal)
- [ ] Generate forecasts with confidence intervals
- [ ] Account for known future events
- [ ] Include business growth projections
- [ ] Model multiple scenarios (conservative, expected, aggressive)
- [ ] Review forecasts with stakeholders

**Capacity Planning**:
- [ ] Calculate required resources with headroom
- [ ] Identify scaling bottlenecks
- [ ] Plan scaling approach (vertical vs horizontal)
- [ ] Design auto-scaling policies
- [ ] Document capacity constraints
- [ ] Create procurement timeline
- [ ] Estimate costs for capacity changes

**Testing**:
- [ ] Conduct baseline load tests
- [ ] Run load tests at expected peak
- [ ] Perform stress testing to find limits
- [ ] Test auto-scaling behavior
- [ ] Validate disaster recovery capacity
- [ ] Document test results and limits

**Implementation**:
- [ ] Provision additional capacity
- [ ] Configure auto-scaling
- [ ] Update monitoring and alerts
- [ ] Document capacity decisions
- [ ] Train team on new capacity
- [ ] Plan rollback if issues arise

**Monitoring**:
- [ ] Monitor utilization trends
- [ ] Track forecast accuracy
- [ ] Alert on capacity thresholds
- [ ] Review capacity monthly
- [ ] Update forecasts quarterly
- [ ] Conduct load tests quarterly

---

## Anti-Patterns

**Planning Anti-Patterns**:
```
❌ No historical data → Guessing instead of forecasting
❌ Short history (< 30 days) → Missing patterns
❌ Ignore seasonality → Under-capacity during peaks
❌ No headroom → Systems at 100%, no room for spikes
❌ Only plan for average → Fail during peak load
❌ Plan for 1 year out → Inaccurate, wasted effort
```

**Testing Anti-Patterns**:
```
❌ Test in production → Risk customer impact
❌ No load testing → Discover limits during incidents
❌ Test with synthetic data → Doesn't match real usage
❌ Single load test → Miss edge cases
❌ No stress testing → Don't know breaking point
❌ Ignore test failures → Launch without confidence
```

**Scaling Anti-Patterns**:
```
❌ Manual scaling only → Slow response to load changes
❌ Aggressive scale-down → Flapping, instability
❌ No scale-up delay → Over-react to spikes
❌ Scale on CPU only → Miss memory constraints
❌ No max replicas → Runaway scaling, cost explosion
❌ No monitoring → Don't know if scaling works
```

**Cost Anti-Patterns**:
```
❌ Over-provision "to be safe" → Wasted money
❌ No reservation strategy → Pay full price
❌ Ignore right-sizing → Pay for unused resources
❌ No cost monitoring → Surprise bills
❌ No auto-scaling → Pay for idle resources
❌ No storage lifecycle → Pay for old data
```

---

## Recovery

**When Forecasts Are Wrong**:
```
1. MEASURE actual vs predicted variance
2. IDENTIFY root cause (unexpected growth, bad model, missing data)
3. ADJUST forecast model or parameters
4. UPDATE capacity plan with new forecast
5. COMMUNICATE changes to stakeholders
6. DOCUMENT lessons learned
```

**When Load Tests Reveal Issues**:
```
1. DOCUMENT the issue and load level
2. DETERMINE impact (hard limit or degradation?)
3. IDENTIFY bottleneck (CPU, memory, database, network)
4. CALCULATE capacity needed to pass
5. IMPLEMENT fixes (optimize or add capacity)
6. RE-TEST to validate
7. UPDATE capacity plan
```

**When Scaling Fails**:
```
1. REVERT to manual scaling if safe
2. DIAGNOSE root cause (metrics, limits, quotas)
3. TEST fixes in non-production
4. DEPLOY fix with monitoring
5. VALIDATE auto-scaling behavior
6. DOCUMENT failure and resolution
```

---

## Level 3: Resources

**Extended Documentation**: [REFERENCE.md](resources/REFERENCE.md) (2,800+ lines)
- Comprehensive capacity planning methodologies
- Detailed forecasting techniques (linear, exponential, Prophet, ARIMA, LSTM)
- Resource modeling formulas and examples
- Load testing strategies and tools (Locust, k6, JMeter, Gatling)
- Scaling strategies (vertical, horizontal, auto-scaling)
- Cost optimization techniques across cloud providers
- Database capacity planning (RDBMS, NoSQL, caching)
- Network capacity planning
- Disaster recovery capacity planning
- Compliance and headroom requirements
- Traffic analysis and prediction methods
- Cloud resource planning (AWS, GCP, Azure)

**Scripts**: Production-ready tools in `resources/scripts/`
- `forecast_capacity.py` (850 lines): Time-series forecasting with multiple algorithms (linear regression, exponential smoothing, Prophet, ARIMA), seasonality detection, confidence intervals, multi-resource modeling, visualization
- `analyze_resource_usage.py` (780 lines): Historical usage analysis, trend detection, anomaly detection, peak usage patterns, cost analysis, utilization reports, right-sizing recommendations
- `test_scaling.py` (720 lines): Load testing orchestration, measure scaling efficiency, test auto-scaling triggers, validate resource limits, cost-performance analysis, generate reports

**Examples**: Production-ready examples in `resources/examples/`
- **forecasting/**:
  - `prophet_forecast.py`: Complete Prophet-based forecasting model with seasonality
  - `multi_metric_forecast.py`: Forecast multiple resources simultaneously
- **dashboards/**:
  - `capacity_dashboard.json`: Grafana dashboard for capacity monitoring
  - `forecast_dashboard.json`: Visualization of capacity forecasts
- **auto-scaling/**:
  - `kubernetes_hpa.yaml`: Comprehensive HPA configuration
  - `kubernetes_vpa.yaml`: Vertical Pod Autoscaler configuration
  - `aws_autoscaling.json`: AWS Auto Scaling policies
  - `gcp_autoscaling.yaml`: GCP autoscaling configuration
- **load-testing/**:
  - `locust_loadtest.py`: Production Locust load test scenario
  - `k6_script.js`: k6 load testing script with scenarios
- **cost-optimization/**:
  - `analyze_costs.py`: Cloud cost analysis and optimization
  - `rightsizing_recommendations.py`: Instance right-sizing tool
- **database/**:
  - `database_capacity_model.py`: Database capacity modeling
- **examples/**:
  - `traffic_prediction.py`: Traffic pattern analysis and prediction
  - `capacity_report.py`: Generate comprehensive capacity reports

All scripts include:
- `--help` for comprehensive usage documentation
- `--json` output for programmatic integration
- Executable permissions and proper shebang lines
- Type hints and docstrings
- Error handling and validation
- Example usage in main block

**Usage**:
```bash
# Forecast capacity for next 90 days
./forecast_capacity.py --metric cpu_usage --period 90 \
  --method prophet --output forecast.json --visualize

# Analyze resource usage patterns
./analyze_resource_usage.py --days 30 --resources cpu,memory,disk \
  --detect-anomalies --json

# Test scaling behavior
./test_scaling.py --target api-service --duration 30 \
  --max-rps 1000 --test-autoscaling --report scaling_report.html

# Generate capacity forecast
python examples/forecasting/prophet_forecast.py \
  --input metrics.csv --forecast-days 60

# Analyze costs
python examples/cost-optimization/analyze_costs.py \
  --provider aws --region us-east-1 --optimize
```

---

## Related Skills

- `monitoring-alerts.md`: Real-time capacity monitoring
- `performance-optimization.md`: Optimize resource usage
- `cloud-cost-management.md`: Track and optimize costs
- `database-scaling.md`: Database-specific capacity planning
- `sre-practices.md`: SLOs and error budgets for capacity
- `deployment-strategies.md`: Safe capacity changes
- `incident-response.md`: Respond to capacity incidents

---

**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)
**Level 3 Resources**: Available
