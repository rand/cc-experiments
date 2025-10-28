# Deployment Strategies - Production Examples

This directory contains production-ready examples for various deployment strategies.

## Directory Structure

```
examples/
├── blue-green/          # Blue-green deployment examples
├── canary/              # Canary deployment examples
├── rolling/             # Rolling update examples
├── database-migration/  # Database migration patterns
├── github-actions/      # CI/CD workflow examples
└── docker/              # Docker-based deployment examples
```

## Examples Overview

### Blue-Green Deployments

**kubernetes-blue-green.yaml**
- Complete Kubernetes blue-green setup
- Two identical deployments (blue and stable)
- Service-based traffic switching
- Health checks and readiness probes
- Pod Disruption Budget for high availability
- Horizontal Pod Autoscaler configuration

**Usage**:
```bash
# Deploy blue environment
kubectl apply -f blue-green/kubernetes-blue-green.yaml

# Test green environment
kubectl port-forward svc/myapp-green-preview 8080:80

# Switch to green
kubectl patch service myapp -p '{"spec":{"selector":{"version":"green"}}}'

# Rollback to blue
kubectl patch service myapp -p '{"spec":{"selector":{"version":"blue"}}}'
```

---

### Canary Deployments

**flagger-canary.yaml**
- Flagger progressive canary deployment
- Istio service mesh integration
- Prometheus metrics-based validation
- Automatic rollback on failure
- Custom MetricTemplates
- Load testing webhooks

**Prerequisites**:
- Kubernetes cluster
- Istio installed
- Flagger installed
- Prometheus metrics

**Usage**:
```bash
# Install prerequisites
istioctl install --set profile=demo
kubectl apply -f https://raw.githubusercontent.com/fluxcd/flagger/main/artifacts/flagger/crd.yaml
kubectl apply -f https://raw.githubusercontent.com/fluxcd/flagger/main/artifacts/flagger/flagger.yaml

# Deploy canary configuration
kubectl apply -f canary/flagger-canary.yaml

# Trigger canary by updating image
kubectl set image deployment/myapp myapp=myapp:v2.0.0

# Monitor canary progress
kubectl get canary -w
```

---

### Rolling Updates

**kubernetes-rolling-update.yaml**
- Production-ready Deployment configuration
- Optimized rolling update strategy
- Comprehensive health checks (liveness, readiness, startup)
- Resource limits and requests
- Graceful shutdown with preStop hooks
- Security context configuration
- Pod anti-affinity for HA
- ConfigMap and Secret integration

**Usage**:
```bash
# Deploy application
kubectl apply -f rolling/kubernetes-rolling-update.yaml

# Update image (triggers rolling update)
kubectl set image deployment/myapp myapp=myapp:v2.0.0

# Monitor rollout
kubectl rollout status deployment/myapp

# View rollout history
kubectl rollout history deployment/myapp

# Rollback to previous version
kubectl rollout undo deployment/myapp

# Rollback to specific revision
kubectl rollout undo deployment/myapp --to-revision=2
```

---

### Database Migrations

**expand-contract-migration.sql**
- Complete expand-contract pattern
- Zero-downtime schema changes
- Backward compatibility strategies
- Batch backfill operations
- Rollback procedures
- Shadow table pattern
- View-based compatibility layers
- Online schema change tools integration

**Usage**:
```bash
# Phase 1: EXPAND (run before deploying v1.1)
psql -f database-migration/expand-contract-migration.sql -v phase=expand

# Deploy application v1.1 (dual writes to old and new columns)

# Phase 2: MIGRATE (background data migration)
psql -f database-migration/expand-contract-migration.sql -v phase=migrate

# Deploy application v1.2 (reads from new column)

# Phase 3: CONTRACT (cleanup after rollback window)
psql -f database-migration/expand-contract-migration.sql -v phase=contract
```

**Important Notes**:
- Wait appropriate time between phases (e.g., 1-2 weeks for rollback window)
- Monitor application health after each phase
- Test rollback procedures before production
- Use transactions where possible

---

### GitHub Actions Workflows

**canary-deployment-workflow.yml**
- Automated canary deployment pipeline
- Docker image build and security scanning
- Progressive traffic shifting
- Prometheus metrics validation
- Automatic rollback on failure
- Slack notifications
- Multi-stage deployment (10% → 25% → 50% → 75% → 100%)

**Setup**:
1. Add to `.github/workflows/canary-deploy.yml`
2. Configure secrets:
   - `KUBE_CONFIG`: Kubernetes cluster config
   - `SLACK_WEBHOOK_URL`: Slack notifications
3. Configure environment variables in workflow file

**Usage**:
```bash
# Automatic trigger on push to main
git push origin main

# Manual trigger with custom parameters
gh workflow run canary-deploy.yml \
  -f canary_percentage=10 \
  -f environment=production
```

---

### Docker Compose

**docker-compose-blue-green.yml**
- Blue-green deployment with Docker Compose
- NGINX load balancer for traffic switching
- Shared database and cache
- Prometheus and Grafana monitoring
- Health checks for all services
- Volume management

**Usage**:
```bash
# Start blue environment
docker-compose up -d blue nginx

# Deploy green environment
docker-compose --profile green up -d green

# Switch to green
./switch-to-green.sh

# Rollback to blue
./switch-to-blue.sh

# Cleanup
docker-compose down -v
```

---

## Testing Examples

All examples include health checks and can be tested using:

```bash
# Test health endpoint
curl http://localhost/health

# Test readiness endpoint
curl http://localhost/ready

# Load test
hey -z 60s -q 10 -c 2 http://localhost/

# Monitor metrics
curl http://localhost/metrics
```

## Deployment Validation

Use the provided scripts to validate configurations:

```bash
# Validate Kubernetes manifests
../scripts/validate_deployment.py --file kubernetes-blue-green.yaml

# Test deployment downtime
../scripts/test_deployment.sh --url http://localhost --duration 300

# Execute automated canary
../scripts/execute_canary.py --platform kubernetes --service myapp --version v2.0
```

## Best Practices

1. **Always use health checks**: Both liveness and readiness probes
2. **Test rollback procedures**: Before production deployment
3. **Monitor metrics**: Error rates, latency, business metrics
4. **Gradual rollout**: Start with small percentage (5-10%)
5. **Maintain backward compatibility**: Especially for database changes
6. **Document procedures**: Runbooks for each deployment type
7. **Automate validation**: CI/CD integration for all checks
8. **Set rollback thresholds**: Automatic rollback criteria

## Troubleshooting

### Blue-Green Issues

**Problem**: Green environment not receiving traffic after switch
```bash
# Check service selector
kubectl get svc myapp -o yaml | grep selector

# Check pod labels
kubectl get pods --show-labels

# Verify endpoints
kubectl get endpoints myapp
```

**Problem**: Downtime during switch
```bash
# Check readiness probes
kubectl describe deployment myapp-green

# Verify connection draining
kubectl describe svc myapp
```

### Canary Issues

**Problem**: Canary stuck at low percentage
```bash
# Check Flagger status
kubectl describe canary myapp

# View Flagger logs
kubectl logs -n flagger-system deployment/flagger

# Check metrics
kubectl get metrictemplates
```

**Problem**: Automatic rollback triggered
```bash
# View canary events
kubectl describe canary myapp

# Check Prometheus metrics
curl "http://prometheus:9090/api/v1/query?query=http_requests_total"
```

### Rolling Update Issues

**Problem**: Deployment stuck in progress
```bash
# Check rollout status
kubectl rollout status deployment/myapp

# View deployment events
kubectl describe deployment myapp

# Check pod status
kubectl get pods -l app=myapp
```

**Problem**: Pods not ready
```bash
# Check readiness probe
kubectl describe pod <pod-name>

# View pod logs
kubectl logs <pod-name>

# Debug container
kubectl exec -it <pod-name> -- /bin/sh
```

### Database Migration Issues

**Problem**: Backfill taking too long
```sql
-- Check progress
SELECT COUNT(*) FROM orders WHERE status_name IS NULL;

-- Adjust batch size
-- Reduce chunk size in migration script
```

**Problem**: Data inconsistency
```sql
-- Verify data integrity
SELECT
  status,
  status_name,
  COUNT(*)
FROM orders
GROUP BY status, status_name
HAVING status != CASE status_name
  WHEN 'pending' THEN 0
  WHEN 'processing' THEN 1
  ...
END;
```

## Additional Resources

- [Main REFERENCE.md](../REFERENCE.md) - Comprehensive deployment strategies guide
- [Kubernetes Documentation](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)
- [Flagger Documentation](https://docs.flagger.app/)
- [Istio Traffic Management](https://istio.io/latest/docs/tasks/traffic-management/)
- [Database Migrations Best Practices](https://www.postgresql.org/docs/current/ddl-alter.html)

## Contributing

When adding new examples:
1. Include comprehensive comments
2. Add health checks
3. Document prerequisites
4. Provide usage instructions
5. Include rollback procedures
6. Test in realistic environment

## License

These examples are provided as-is for educational and production use.
