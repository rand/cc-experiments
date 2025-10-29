# Capacity Planning Examples

This directory contains production-ready examples for capacity planning tasks.

## Directory Structure

```
examples/
├── forecasting/          # Forecasting models and examples
│   └── prophet_forecast.py
├── dashboards/           # Grafana dashboards (JSON)
├── auto-scaling/         # Auto-scaling configurations
│   └── kubernetes_hpa.yaml
├── load-testing/         # Load testing scenarios
│   └── locust_loadtest.py
├── cost-optimization/    # Cost analysis tools
│   └── analyze_costs.py
├── database/             # Database capacity planning
├── traffic-prediction/   # Traffic analysis examples
└── README.md            # This file
```

## Examples Overview

### 1. Forecasting (`forecasting/`)

**prophet_forecast.py**: Complete Prophet-based forecasting example
- Loads historical capacity data
- Trains Prophet model with seasonality detection
- Generates 90-day forecasts with confidence intervals
- Visualizes results and trend components
- Provides capacity recommendations

```bash
python forecasting/prophet_forecast.py --input data.csv --forecast-days 90 --visualize
```

### 2. Auto-Scaling (`auto-scaling/`)

**kubernetes_hpa.yaml**: Production-ready Kubernetes HPA configuration
- CPU and memory-based scaling
- Custom metrics (RPS, latency)
- External metrics (queue depth)
- Advanced scaling behavior policies
- Scale-up/scale-down strategies

```bash
kubectl apply -f auto-scaling/kubernetes_hpa.yaml
```

### 3. Load Testing (`load-testing/`)

**locust_loadtest.py**: Comprehensive Locust load test
- Multiple user types (browsing, shopping, API clients)
- Realistic session patterns and think time
- Custom metrics tracking
- Staged load progression
- Capacity recommendations based on results

```bash
# Run with Web UI
locust -f load-testing/locust_loadtest.py --host https://api.example.com

# Headless mode
locust -f load-testing/locust_loadtest.py --headless \
  --users 1000 --spawn-rate 10 --run-time 30m \
  --host https://api.example.com
```

### 4. Cost Optimization (`cost-optimization/`)

**analyze_costs.py**: Cloud cost analysis tool
- Right-sizing recommendations
- Reserved capacity opportunities
- Spot instance candidates
- Storage tiering suggestions

```bash
python cost-optimization/analyze_costs.py --provider aws --region us-east-1 --optimize
```

## Usage Patterns

### Basic Capacity Planning Workflow

1. **Collect Historical Data**
   ```bash
   # Export metrics from Prometheus or load from CSV
   ../scripts/analyze_resource_usage.py --prometheus http://localhost:9090 --days 60
   ```

2. **Analyze Current Usage**
   ```bash
   ../scripts/analyze_resource_usage.py --input metrics.csv \
     --detect-anomalies --cost-analysis
   ```

3. **Generate Forecast**
   ```bash
   python forecasting/prophet_forecast.py --input metrics.csv \
     --forecast-days 90 --visualize --export forecast.csv
   ```

4. **Load Test**
   ```bash
   locust -f load-testing/locust_loadtest.py --headless \
     --users 1000 --run-time 30m --host https://staging.example.com
   ```

5. **Configure Auto-Scaling**
   ```bash
   # Edit and apply HPA configuration
   kubectl apply -f auto-scaling/kubernetes_hpa.yaml
   ```

6. **Test Scaling**
   ```bash
   ../scripts/test_scaling.py --k8s-deployment api \
     --namespace production --test-hpa --duration 30 --report report.html
   ```

7. **Optimize Costs**
   ```bash
   python cost-optimization/analyze_costs.py --optimize
   ```

### Advanced Scenarios

#### Multi-Resource Forecasting
```bash
# Forecast multiple metrics simultaneously
../scripts/forecast_capacity.py --input metrics.csv \
  --methods linear prophet arima --ensemble --json
```

#### Comprehensive Analysis
```bash
# Full analysis with all features
../scripts/analyze_resource_usage.py \
  --prometheus http://localhost:9090 \
  --days 30 \
  --detect-anomalies \
  --anomaly-method isolation_forest \
  --cost-analysis \
  --recommend-rightsizing \
  --visualize \
  --output full_analysis.json
```

## Data Formats

### CSV Format for Forecasting
```csv
timestamp,value
2024-01-01,45.2
2024-01-02,47.1
2024-01-03,46.8
```

### CSV Format for Resource Analysis
```csv
timestamp,resource,value
2024-01-01 00:00:00,cpu,45.2
2024-01-01 00:00:00,memory,62.5
2024-01-01 00:00:00,disk,78.3
```

## Integration with Existing Tools

### Prometheus
All scripts support Prometheus integration:
```bash
--prometheus http://localhost:9090 --query 'metric_name'
```

### Grafana
Import dashboard JSON files from `dashboards/` directory.

### Kubernetes
Apply manifests from `auto-scaling/` directory:
```bash
kubectl apply -f auto-scaling/
```

## Best Practices

1. **Regular Analysis**: Run capacity analysis monthly
2. **Load Testing**: Test quarterly or before major releases
3. **Forecast Horizon**: Use 60-90 day forecasts
4. **Confidence Intervals**: Always review upper bounds
5. **Cost Review**: Analyze costs monthly
6. **Auto-Scaling**: Test HPA configuration in staging first
7. **Documentation**: Document capacity decisions

## Troubleshooting

### Prophet Import Error
```bash
pip install prophet
```

### Locust Not Found
```bash
pip install locust
```

### k6 Not Installed
Download from: https://k6.io/docs/getting-started/installation/

### Kubernetes Access
```bash
kubectl config current-context
kubectl get pods -n production
```

## Contributing

When adding new examples:
1. Include comprehensive comments
2. Add example usage in docstring
3. Update this README
4. Test examples work end-to-end
5. Include sample data if applicable

## Related Skills

- `../REFERENCE.md`: Comprehensive capacity planning reference
- `../scripts/`: Production-ready capacity planning scripts
- `monitoring-alerts.md`: Alerting on capacity thresholds
- `performance-optimization.md`: Performance tuning

---

**Last Updated**: 2025-10-29
