# Prometheus Metrics Stack - Docker Compose

Complete Prometheus monitoring stack with Grafana dashboards and sample applications.

## Quick Start

```bash
# Start the stack
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the stack
docker-compose down

# Stop and remove volumes (reset all data)
docker-compose down -v
```

## Services

### Prometheus
- **URL**: http://localhost:9090
- **Purpose**: Metrics collection and storage
- **Config**: `prometheus/prometheus.yml`

### Grafana
- **URL**: http://localhost:3000
- **Credentials**: admin / admin
- **Purpose**: Visualization and dashboards
- **Dashboards**: Pre-loaded HTTP metrics dashboard

### AlertManager
- **URL**: http://localhost:9093
- **Purpose**: Alert routing and notifications
- **Config**: `alertmanager/alertmanager.yml`

### Node Exporter
- **URL**: http://localhost:9100/metrics
- **Purpose**: System-level metrics (CPU, memory, disk, network)

### Sample Application
- **URL**: http://localhost:8080
- **Metrics**: http://localhost:8080/metrics
- **Purpose**: Instrumented Flask app with Prometheus metrics

### Blackbox Exporter
- **URL**: http://localhost:9115
- **Purpose**: HTTP/TCP probing for availability checks

## Usage

### 1. Access Prometheus

Navigate to http://localhost:9090 and run queries:

```promql
# Request rate
rate(http_requests_total[5m])

# Error rate
sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))

# Latency p95
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

### 2. Access Grafana

1. Navigate to http://localhost:3000
2. Login with admin/admin
3. Go to Dashboards → Browse
4. Open "HTTP Metrics Dashboard"

### 3. Generate Traffic

Send requests to the sample application:

```bash
# Get users
curl http://localhost:8080/api/users

# Login
curl -X POST http://localhost:8080/api/login

# Create order
curl -X POST http://localhost:8080/api/orders

# Generate load
for i in {1..100}; do
  curl -s http://localhost:8080/api/users > /dev/null
  sleep 0.1
done
```

### 4. View Metrics

```bash
# Application metrics
curl http://localhost:8080/metrics

# Node metrics
curl http://localhost:9100/metrics
```

### 5. Trigger Alerts

```bash
# Generate errors
for i in {1..100}; do
  curl -s http://localhost:8080/api/error
done

# Check alerts in Prometheus
open http://localhost:9090/alerts

# Check AlertManager
open http://localhost:9093
```

## Configuration Files

### prometheus/prometheus.yml
Main Prometheus configuration with scrape targets and rules.

### prometheus/rules.yml
Recording rules for pre-computing metrics.

### prometheus/alerts.yml
Alerting rules for monitoring conditions.

### alertmanager/alertmanager.yml
Alert routing and notification configuration.

### grafana/provisioning/
Grafana datasources and dashboard provisioning.

## Customization

### Add New Scrape Target

Edit `prometheus/prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'my-app'
    static_configs:
      - targets: ['my-app:8080']
```

Then reload configuration:

```bash
docker-compose exec prometheus kill -HUP 1
# or
curl -X POST http://localhost:9090/-/reload
```

### Add AlertManager Routes

Edit `alertmanager/alertmanager.yml`:

```yaml
route:
  receiver: 'slack'
  routes:
    - match:
        severity: critical
      receiver: 'pagerduty'

receivers:
  - name: 'slack'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/XXX'
        channel: '#alerts'
```

### Import Grafana Dashboards

1. Go to http://localhost:3000
2. Click "+" → "Import"
3. Enter dashboard ID (e.g., 1860 for Node Exporter Full)
4. Select "Prometheus" as datasource

## Persistence

Data is persisted in named volumes:
- `prometheus-data`: Metrics data (15 days retention)
- `grafana-data`: Dashboards and settings
- `alertmanager-data`: Alert state

To backup data:

```bash
docker run --rm -v prometheus-data:/data -v $(pwd):/backup alpine tar czf /backup/prometheus-backup.tar.gz /data
```

## Troubleshooting

### Prometheus not scraping targets

```bash
# Check target status
curl http://localhost:9090/api/v1/targets

# View Prometheus logs
docker-compose logs prometheus
```

### Grafana dashboard shows no data

1. Check datasource: Configuration → Data Sources → Prometheus
2. Verify queries in Explore tab
3. Check time range (upper right)

### Alerts not firing

1. Check alert rules: http://localhost:9090/alerts
2. Verify AlertManager config: http://localhost:9093
3. Check AlertManager logs: `docker-compose logs alertmanager`

## Production Considerations

For production deployments:

1. **Security**: Enable authentication and TLS
2. **High Availability**: Run multiple Prometheus instances
3. **Long-term Storage**: Configure remote write (Thanos, Cortex, M3)
4. **Resource Limits**: Set CPU/memory limits
5. **Backup**: Regular snapshots of TSDB
6. **Monitoring**: Monitor Prometheus itself

Example resource limits:

```yaml
services:
  prometheus:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

## Further Reading

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [AlertManager Documentation](https://prometheus.io/docs/alerting/latest/alertmanager/)
- [PromQL Cheat Sheet](https://promlabs.com/promql-cheat-sheet/)
