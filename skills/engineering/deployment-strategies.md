---
name: engineering-deployment-strategies
description: Production deployment strategies including blue-green, canary, rolling updates, zero-downtime deployments, and database migrations
---

# Deployment Strategies

**Scope**: Comprehensive deployment patterns, progressive delivery, feature flags, rollback procedures, and database migration strategies across Kubernetes, cloud platforms, and containerized environments

**Lines**: ~650

**Last Updated**: 2025-10-27

**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Designing deployment pipelines for production systems
- Implementing zero-downtime deployments
- Setting up progressive delivery (canary, blue-green)
- Planning database schema migrations
- Configuring rollback procedures
- Implementing feature flags for gradual rollouts
- Designing traffic shifting strategies
- Setting up deployment validation and health checks

Don't use this skill for:
- Basic CI/CD pipeline setup (see `continuous-integration.md`)
- Container orchestration basics (see `kubernetes-deployment`)
- Infrastructure provisioning (see `terraform-best-practices`)

---

## Core Concepts

### Concept 1: Deployment Strategy Selection

**Definition**: Choose deployment approach based on risk tolerance, downtime requirements, and infrastructure capabilities

**Decision Matrix**:
```
Requirement          | Recommended Strategy
---------------------|--------------------
Zero downtime        | Blue-Green, Canary, Rolling
Instant rollback     | Blue-Green
Gradual validation   | Canary
Limited resources    | Rolling, Recreate
Complex migrations   | Blue-Green + Feature Flags
High risk changes    | Canary + A/B Testing
```

**Key Principles**:
1. Understand blast radius of failures
2. Plan for rollback scenarios
3. Validate before full deployment
4. Monitor metrics during rollout
5. Maintain backward compatibility

**Benefits**:
- Reduced deployment risk
- Faster time to production
- Improved reliability
- Better user experience

---

### Concept 2: Progressive Delivery

**Definition**: Gradually release changes with continuous validation and control

**Components**:
```
Code → Deploy → Feature Flag → Observe → Decide
         ↓           ↓            ↓         ↓
    Containers   Control      Metrics   Expand/
                 Exposure               Rollback
```

**Traffic Management Patterns**:
- **Percentage-based**: Route X% of traffic to new version
- **User-based**: Route specific users/groups to canary
- **Geography-based**: Route by region for localized testing
- **Header-based**: Route based on request headers (internal testing)

**Validation Strategy**:
1. Deploy to canary environment
2. Route small traffic percentage
3. Monitor error rates, latency, business metrics
4. Gradually increase traffic
5. Promote or rollback based on metrics

---

### Concept 3: Database Migration Strategies

**Definition**: Evolve database schema without breaking application deployments

**Expand-Contract Pattern**:
```
Phase 1: EXPAND
  ├─ Add new schema alongside old
  ├─ Deploy app with dual writes
  └─ Both versions work

Phase 2: MIGRATE
  ├─ Backfill new schema
  └─ Verify data integrity

Phase 3: CONTRACT
  ├─ Deploy app using only new schema
  ├─ Remove old schema
  └─ Cleanup
```

**Backward Compatibility Rules**:
- Add columns as nullable first
- Never drop columns during deployment
- Use views for compatibility layers
- Dual write during transitions
- Batch backfill operations

**Rollback Considerations**:
- Keep old schema during rollback window
- Test rollback procedures
- Document migration dependencies
- Use transactions where possible

---

## Patterns

### Pattern 1: Blue-Green Deployment

**Problem**: Need instant rollback capability with zero downtime

**Kubernetes Implementation**:
```yaml
# Two identical deployments
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp-blue
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
      version: blue
  template:
    metadata:
      labels:
        app: myapp
        version: blue
    spec:
      containers:
      - name: myapp
        image: myapp:v1.0.0
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
---
# Service switches between blue and green
apiVersion: v1
kind: Service
metadata:
  name: myapp
spec:
  selector:
    app: myapp
    version: blue  # Change to 'green' to switch
  ports:
  - port: 80
    targetPort: 8080
```

**Switch Procedure**:
```bash
# 1. Deploy green environment
kubectl apply -f deployment-green.yaml

# 2. Wait for green to be ready
kubectl wait --for=condition=available deployment/myapp-green

# 3. Test green environment
curl http://myapp-green-preview/health

# 4. Switch traffic to green
kubectl patch service myapp -p '{"spec":{"selector":{"version":"green"}}}'

# 5. Monitor for issues (keep blue running)
sleep 600

# 6. Scale down blue (after validation)
kubectl scale deployment myapp-blue --replicas=0
```

**Benefits**: Instant rollback, full testing before switch
**Trade-offs**: Requires 2x infrastructure, database complexity

---

### Pattern 2: Canary Deployment with Flagger

**Problem**: Need gradual validation with automatic rollback

**Flagger Canary Resource**:
```yaml
apiVersion: flagger.app/v1beta1
kind: Canary
metadata:
  name: myapp
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: myapp
  provider: istio
  analysis:
    interval: 1m
    threshold: 5
    maxWeight: 50
    stepWeight: 10
    metrics:
    - name: request-success-rate
      thresholdRange:
        min: 99
      interval: 1m
    - name: request-duration
      thresholdRange:
        max: 500
      interval: 1m
```

**Progressive Rollout**:
```
5% → Monitor → 15% → Monitor → 25% → Monitor → 50% → Complete
     ↓              ↓              ↓              ↓
   Healthy?      Healthy?       Healthy?       Healthy?
     ↓              ↓              ↓              ↓
   Continue      Continue       Continue       Promote
     or             or             or             or
   Rollback      Rollback       Rollback       Rollback
```

**Benefits**: Minimal blast radius, data-driven decisions
**Trade-offs**: Slower deployment, complex traffic management

---

### Pattern 3: Rolling Update with Health Checks

**Problem**: Need zero downtime with limited resources

**Kubernetes Configuration**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  replicas: 10
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1  # Max 1 pod down at a time
      maxSurge: 2        # Allow 2 extra pods during update
  template:
    spec:
      terminationGracePeriodSeconds: 60
      containers:
      - name: myapp
        image: myapp:v2.0.0
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          failureThreshold: 2
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          failureThreshold: 3
        lifecycle:
          preStop:
            exec:
              command: ["/bin/sh", "-c", "sleep 15"]
```

**Update Process**:
1. Create 1 new pod (within maxSurge)
2. Wait for readiness probe to pass
3. Terminate 1 old pod
4. Wait for graceful shutdown
5. Repeat until all pods updated

**Benefits**: No extra infrastructure, gradual rollout
**Trade-offs**: Slower than blue-green, mixed versions during deployment

---

### Pattern 4: Database Expand-Contract Migration

**Problem**: Need to change database schema without breaking deployments

**Implementation**:
```sql
-- PHASE 1: EXPAND (v1.1 app deployment)
ALTER TABLE orders ADD COLUMN status_name VARCHAR(50) NULL;

CREATE TRIGGER sync_status
BEFORE INSERT OR UPDATE ON orders
FOR EACH ROW
EXECUTE FUNCTION sync_order_status();

-- PHASE 2: MIGRATE (background job)
UPDATE orders
SET status_name = CASE status
  WHEN 0 THEN 'pending'
  WHEN 1 THEN 'processing'
  WHEN 2 THEN 'completed'
END
WHERE status_name IS NULL;

-- PHASE 3: CONTRACT (v1.2 app deployment)
ALTER TABLE orders ALTER COLUMN status_name SET NOT NULL;
ALTER TABLE orders DROP COLUMN status;
```

**Application Evolution**:
```
v1.0: Reads/writes old column
v1.1: Reads old, writes both (dual write)
v1.2: Reads/writes new column only
v1.3: Old column removed
```

**Benefits**: Zero downtime, rollback-safe
**Trade-offs**: Multi-phase deployment, temporary overhead

---

### Pattern 5: Feature Flag Controlled Rollout

**Problem**: Decouple deployment from release

**Implementation**:
```python
from launchdarkly import LDClient

ld_client = LDClient("sdk-key")

def get_pricing_page(user_id):
    user = {
        "key": user_id,
        "custom": {
            "deployment_version": os.getenv("APP_VERSION"),
            "canary_group": os.getenv("CANARY_GROUP")
        }
    }

    # Feature flag controls which version user sees
    use_new_pricing = ld_client.variation("new-pricing", user, False)

    if use_new_pricing:
        return render_template("pricing_v2.html")
    else:
        return render_template("pricing_v1.html")
```

**Targeting Rules**:
```json
{
  "flagKey": "new-pricing",
  "targeting": [
    {
      "variation": 1,
      "values": ["canary"],
      "attribute": "canary_group"
    },
    {
      "variation": 1,
      "percentage": {
        "variations": [
          {"variation": 0, "weight": 95000},
          {"variation": 1, "weight": 5000}
        ]
      }
    }
  ]
}
```

**Benefits**: Deploy code safely, control feature exposure, instant rollback
**Trade-offs**: Code complexity, flag management overhead

---

## Anti-Patterns

### Anti-Pattern 1: No Rollback Plan

**Problem**: Deploying without tested rollback procedures

**Why It's Bad**:
- Panic during incidents
- Extended downtime
- Data loss risks
- Manual recovery errors

**Solution**:
```bash
# Document and test rollback
# Blue-Green: Switch back
kubectl patch service myapp -p '{"spec":{"selector":{"version":"blue"}}}'

# Rolling: Rollback deployment
kubectl rollout undo deployment/myapp

# Database: Keep old schema during rollback window
# Feature Flags: Kill switch
```

---

### Anti-Pattern 2: Testing in Production Only

**Problem**: No pre-deployment validation

**Why It's Bad**:
- Discover issues after user impact
- No safety net
- Higher risk

**Solution**:
```yaml
# Smoke tests before full rollout
- name: Test green environment
  run: |
    GREEN_URL=$(get_green_url)
    curl -f $GREEN_URL/health
    curl -f $GREEN_URL/api/test
    ./load-test.sh $GREEN_URL
```

---

### Anti-Pattern 3: Incompatible Schema Changes

**Problem**: Breaking old application version with schema changes

**Why It's Bad**:
- Forces all-or-nothing deployment
- Can't rollback
- Downtime required

**Solution**: Use expand-contract pattern, maintain backward compatibility

---

### Anti-Pattern 4: No Health Checks

**Problem**: Routing traffic to unhealthy instances

**Why It's Bad**:
- User-facing errors
- Failed deployments go undetected
- No automatic recovery

**Solution**:
```yaml
readinessProbe:
  httpGet:
    path: /ready
    port: 8080
  failureThreshold: 2
livenessProbe:
  httpGet:
    path: /health
    port: 8080
  failureThreshold: 3
```

---

### Anti-Pattern 5: Manual Deployment Steps

**Problem**: Undocumented manual interventions

**Why It's Bad**:
- Not reproducible
- Error-prone
- Knowledge silos
- Can't automate

**Solution**: Automate everything, document runbooks, use GitOps

---

## Quick Reference

### Deployment Strategy Comparison

| Strategy | Downtime | Rollback | Cost | Complexity |
|----------|----------|----------|------|------------|
| Recreate | High | Slow | Low | Low |
| Rolling | None | Medium | Low | Medium |
| Blue-Green | None | Instant | High (2x) | Medium |
| Canary | None | Fast | Medium | High |

### Health Check Best Practices

```yaml
# Liveness: Is app alive?
livenessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 30
  periodSeconds: 10
  failureThreshold: 3

# Readiness: Can app serve traffic?
readinessProbe:
  httpGet:
    path: /ready
    port: 8080
  initialDelaySeconds: 10
  periodSeconds: 5
  failureThreshold: 2
```

### Graceful Shutdown

```python
import signal
import sys

def handle_shutdown(signum, frame):
    print("Shutting down gracefully...")
    # Stop accepting new requests
    server.close()
    # Wait for existing requests
    time.sleep(10)
    sys.exit(0)

signal.signal(signal.SIGTERM, handle_shutdown)
```

### Database Migration Checklist

- [ ] Schema changes are backward compatible
- [ ] Dual write implemented during transition
- [ ] Backfill plan for existing data
- [ ] Rollback procedure documented
- [ ] Migration tested in staging
- [ ] Monitoring for data consistency

---

## Level 3: Resources

**Extended documentation, production-ready examples, and automation tools**

### REFERENCE.md
**Location**: `resources/REFERENCE.md` (4,033 lines)

Comprehensive reference covering:
- Deployment strategy deep-dive (blue-green, canary, rolling, recreate)
- Progressive delivery patterns and feature flags
- Rollback procedures and automation
- Zero-downtime deployment techniques
- Database migration strategies (expand-contract, shadow tables)
- Kubernetes deployment patterns with Istio/Flagger
- Cloud provider deployment strategies (AWS, GCP, Azure)
- Traffic management and load balancing
- Monitoring and observability during deployments
- Testing strategies and validation
- Complete code examples for all patterns

### Scripts

**validate_deployment.py** (600+ lines)
Validates deployment configuration files across multiple platforms:
```bash
# Validate Kubernetes manifests
./validate_deployment.py --file deployment.yaml

# Check entire directory
./validate_deployment.py --directory k8s/ --type kubernetes

# JSON output for CI/CD
./validate_deployment.py --file deployment.yaml --json
```

**execute_canary.py** (550+ lines)
Executes automated canary deployments with progressive traffic shifting:
```bash
# Kubernetes canary deployment
./execute_canary.py --platform kubernetes --service myapp --version v2.0

# AWS ALB canary
./execute_canary.py --platform aws-alb --service myapp --version v2.0

# Custom configuration
./execute_canary.py --config canary-config.yaml --json
```

**test_deployment.sh** (400+ lines)
Tests deployment processes and measures downtime:
```bash
# Monitor deployment and measure downtime
./test_deployment.sh --url https://myapp.com --duration 300

# Test specific strategy
./test_deployment.sh --url https://myapp.com --strategy blue-green --json
```

### Production Examples

**Blue-Green Deployments**:
- `examples/blue-green/kubernetes-blue-green.yaml`: Complete K8s blue-green setup with health checks, PDB, and HPA
- `examples/docker/docker-compose-blue-green.yml`: Docker Compose blue-green with NGINX load balancer

**Canary Deployments**:
- `examples/canary/flagger-canary.yaml`: Flagger + Istio progressive canary with Prometheus metrics
- `examples/github-actions/canary-deployment-workflow.yml`: GitHub Actions automated canary pipeline

**Rolling Updates**:
- `examples/rolling/kubernetes-rolling-update.yaml`: Production-ready rolling update with proper health checks and resource limits

**Database Migrations**:
- `examples/database-migration/expand-contract-migration.sql`: Complete expand-contract pattern with PostgreSQL

All examples include:
- Production-ready configurations
- Comprehensive comments
- Health check implementations
- Rollback procedures
- Monitoring integration
- Security best practices

---

## Related Skills

- `continuous-integration.md` - CI pipeline design
- `test-driven-development.md` - Testing strategies
- `technical-debt.md` - Managing deployment complexity
- `cloud-kubernetes-deployment` - Kubernetes specifics
- `terraform-best-practices` - Infrastructure provisioning

---

**Last Updated**: 2025-10-27
**Maintainer**: Skills Team
**Validation**: CI-validated, production-tested patterns
