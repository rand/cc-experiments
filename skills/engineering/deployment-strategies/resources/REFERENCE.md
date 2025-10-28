# Deployment Strategies - Comprehensive Reference

## Table of Contents
1. [Deployment Strategy Overview](#deployment-strategy-overview)
2. [Blue-Green Deployment](#blue-green-deployment)
3. [Canary Deployment](#canary-deployment)
4. [Rolling Deployment](#rolling-deployment)
5. [Recreate Deployment](#recreate-deployment)
6. [Progressive Delivery](#progressive-delivery)
7. [Feature Flags](#feature-flags)
8. [Rollback Procedures](#rollback-procedures)
9. [Zero-Downtime Deployments](#zero-downtime-deployments)
10. [Database Migrations](#database-migrations)
11. [Kubernetes Deployment Strategies](#kubernetes-deployment-strategies)
12. [Cloud Provider Strategies](#cloud-provider-strategies)
13. [Traffic Management](#traffic-management)
14. [Monitoring and Observability](#monitoring-and-observability)
15. [Testing Strategies](#testing-strategies)

---

## Deployment Strategy Overview

### What is a Deployment Strategy?

A deployment strategy is a method for updating running instances of your application. The choice of strategy affects:
- **Downtime**: How much, if any
- **Risk**: Blast radius of failures
- **Speed**: Time to full deployment
- **Cost**: Resource overhead
- **Complexity**: Operational burden

### Strategy Comparison Matrix

| Strategy | Downtime | Risk | Speed | Cost | Complexity | Rollback Speed |
|----------|----------|------|-------|------|------------|----------------|
| Recreate | High | High | Fast | Low | Low | Slow |
| Rolling | None | Medium | Medium | Low | Medium | Medium |
| Blue-Green | None | Low | Fast | High | Medium | Instant |
| Canary | None | Very Low | Slow | Medium | High | Fast |
| A/B Testing | None | Very Low | Slow | High | High | Fast |

### Decision Tree

```
Need zero downtime?
├─ NO → Recreate (simplest, cheapest)
└─ YES → Need instant rollback?
    ├─ YES → Blue-Green (higher cost)
    └─ NO → Need gradual validation?
        ├─ YES → Canary (complex, safest)
        └─ NO → Rolling (balanced)
```

### Key Metrics to Monitor

**Deployment Health**:
- Error rate (5xx responses)
- Response time (p50, p95, p99)
- Request success rate
- CPU/Memory utilization
- Database connection pool
- Queue depth

**Business Metrics**:
- Conversion rate
- User engagement
- Revenue impact
- Customer complaints

---

## Blue-Green Deployment

### Concept

Maintain two identical production environments (Blue and Green). At any time, only one serves live traffic. Deploy to the idle environment, test it, then switch traffic over.

```
┌─────────────┐
│   Router    │
└──────┬──────┘
       │
       ├──────────┐
       │          │
   ┌───▼──┐   ┌──▼───┐
   │ Blue │   │Green │
   │ v1.0 │   │ v1.1 │  ← Deploy here
   └──────┘   └──────┘

After switch:

┌─────────────┐
│   Router    │
└──────┬──────┘
       │
       ├──────────┐
       │          │
   ┌──▼───┐   ┌──▼───┐
   │ Blue │   │Green │  ← Live traffic
   │ v1.0 │   │ v1.1 │
   └──────┘   └──────┘
```

### Benefits

**Advantages**:
- Instant rollback (switch router back)
- Full testing before cutover
- Zero downtime
- Easy to understand and implement

**Disadvantages**:
- Requires 2x infrastructure
- Database migration challenges
- Stateful applications need careful handling
- Cost overhead

### Implementation Patterns

#### Pattern 1: Load Balancer Switch

**AWS ALB Target Groups**:
```bash
# Deploy to green environment
aws ecs update-service \
  --cluster production \
  --service app-green \
  --force-new-deployment

# Wait for health checks
aws elbv2 wait target-in-service \
  --target-group-arn $GREEN_TG_ARN

# Switch traffic to green
aws elbv2 modify-listener \
  --listener-arn $LISTENER_ARN \
  --default-actions Type=forward,TargetGroupArn=$GREEN_TG_ARN

# Keep blue running for rollback
sleep 600  # 10 minutes

# Scale down blue
aws ecs update-service \
  --cluster production \
  --service app-blue \
  --desired-count 0
```

#### Pattern 2: DNS Switch

**Route53 Weighted Routing**:
```python
import boto3

route53 = boto3.client('route53')

# Switch to green
route53.change_resource_record_sets(
    HostedZoneId='Z123456',
    ChangeBatch={
        'Changes': [
            {
                'Action': 'UPSERT',
                'ResourceRecordSet': {
                    'Name': 'app.example.com',
                    'Type': 'A',
                    'SetIdentifier': 'green',
                    'Weight': 100,
                    'AliasTarget': {
                        'HostedZoneId': 'Z789012',
                        'DNSName': 'green-lb.us-east-1.elb.amazonaws.com',
                        'EvaluateTargetHealth': True
                    }
                }
            },
            {
                'Action': 'UPSERT',
                'ResourceRecordSet': {
                    'Name': 'app.example.com',
                    'Type': 'A',
                    'SetIdentifier': 'blue',
                    'Weight': 0,  # No traffic
                    'AliasTarget': {
                        'HostedZoneId': 'Z345678',
                        'DNSName': 'blue-lb.us-east-1.elb.amazonaws.com',
                        'EvaluateTargetHealth': True
                    }
                }
            }
        ]
    }
)
```

#### Pattern 3: Kubernetes Blue-Green

**Service Selector Switch**:
```yaml
# blue-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-blue
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
      - name: app
        image: myapp:1.0.0
        ports:
        - containerPort: 8080
---
# green-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-green
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
      version: green
  template:
    metadata:
      labels:
        app: myapp
        version: green
    spec:
      containers:
      - name: app
        image: myapp:1.1.0
        ports:
        - containerPort: 8080
---
# service.yaml (initially pointing to blue)
apiVersion: v1
kind: Service
metadata:
  name: app-service
spec:
  selector:
    app: myapp
    version: blue  # Change to 'green' to switch
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8080
  type: LoadBalancer
```

**Switch Script**:
```bash
#!/bin/bash
# switch-to-green.sh

set -euo pipefail

NAMESPACE=${NAMESPACE:-default}
SERVICE=app-service
NEW_VERSION=green
OLD_VERSION=blue

echo "Deploying green version..."
kubectl apply -f green-deployment.yaml -n $NAMESPACE

echo "Waiting for green pods to be ready..."
kubectl wait --for=condition=available \
  --timeout=300s \
  deployment/app-green -n $NAMESPACE

echo "Running smoke tests against green..."
GREEN_IP=$(kubectl get svc app-service-green -n $NAMESPACE \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
curl -f http://$GREEN_IP/health || {
  echo "Green health check failed!"
  exit 1
}

echo "Switching service to green..."
kubectl patch service $SERVICE -n $NAMESPACE \
  -p '{"spec":{"selector":{"version":"'$NEW_VERSION'"}}}'

echo "Monitoring for 5 minutes..."
sleep 300

# Check error rates
ERROR_RATE=$(kubectl logs -l version=green -n $NAMESPACE --tail=1000 \
  | grep -c "ERROR" || echo 0)

if [ $ERROR_RATE -gt 10 ]; then
  echo "High error rate detected! Rolling back..."
  kubectl patch service $SERVICE -n $NAMESPACE \
    -p '{"spec":{"selector":{"version":"'$OLD_VERSION'"}}}'
  exit 1
fi

echo "Deployment successful! Scaling down blue..."
kubectl scale deployment app-blue --replicas=0 -n $NAMESPACE
```

### Database Considerations

**Challenge**: Both environments may share the same database. How to handle schema changes?

**Strategy 1: Backward Compatible Migrations**

```sql
-- Phase 1: Add new column (nullable)
ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT NULL;

-- Deploy green with code that uses new column

-- Phase 2: Backfill data
UPDATE users SET email_verified = TRUE WHERE email_confirmed_at IS NOT NULL;

-- Phase 3: Make non-nullable (after blue is retired)
ALTER TABLE users ALTER COLUMN email_verified SET NOT NULL;
```

**Strategy 2: Expand-Contract Pattern**

```
1. EXPAND: Add new schema alongside old
   ├─ Deploy green with dual writes (old + new)
   └─ Backfill new schema from old

2. SWITCH: Change reads from old to new
   └─ Green reads from new schema

3. CONTRACT: Remove old schema
   └─ After blue is retired
```

**Example**:
```python
# Phase 1: Dual writes
def create_user(name, email):
    # Write to both old and new tables
    user_id = db.execute(
        "INSERT INTO users (name) VALUES (%s) RETURNING id",
        (name,)
    )
    db.execute(
        "INSERT INTO user_emails (user_id, email) VALUES (%s, %s)",
        (user_id, email)
    )
    return user_id

# Phase 2: Read from new schema
def get_user_email(user_id):
    return db.query(
        "SELECT email FROM user_emails WHERE user_id = %s",
        (user_id,)
    )
```

### Health Check Requirements

**Critical**: Green must be fully validated before switching.

```python
import requests
import time

def validate_green_environment(green_url, blue_metrics):
    """Comprehensive validation before switch"""

    # 1. Basic health check
    response = requests.get(f"{green_url}/health")
    assert response.status_code == 200

    # 2. Dependency health
    health_data = response.json()
    assert health_data['database'] == 'healthy'
    assert health_data['cache'] == 'healthy'
    assert health_data['message_queue'] == 'healthy'

    # 3. Smoke tests
    test_user = create_test_user(green_url)
    assert test_user['id'] is not None

    # 4. Performance comparison
    green_response_time = measure_response_time(green_url)
    blue_response_time = blue_metrics['avg_response_time']

    # Green shouldn't be >20% slower
    assert green_response_time < blue_response_time * 1.2

    # 5. Load test
    run_load_test(green_url, duration=60, rps=100)

    # 6. Check for errors
    errors = check_logs_for_errors(green_url)
    assert len(errors) == 0

    return True
```

---

## Canary Deployment

### Concept

Gradually roll out changes to a small subset of users before deploying to everyone. Monitor metrics closely and expand or rollback based on health.

```
┌─────────────────────────────────────────┐
│             Load Balancer               │
└────┬──────────────────────────┬─────────┘
     │ 95%                      │ 5%
     │                          │
┌────▼─────┐              ┌────▼─────┐
│  Stable  │              │  Canary  │
│  v1.0    │              │  v1.1    │
│ (19 pods)│              │ (1 pod)  │
└──────────┘              └──────────┘

Progression:
5% → Monitor → 25% → Monitor → 50% → Monitor → 100%
     ↓ Issues?         ↓ Issues?        ↓ Issues?
     Rollback          Rollback         Rollback
```

### Benefits

**Advantages**:
- Minimal blast radius
- Real production validation
- Gradual confidence building
- Data-driven decisions

**Disadvantages**:
- Complex traffic routing
- Longer deployment time
- Requires advanced monitoring
- Stateful applications are tricky

### Implementation Patterns

#### Pattern 1: Flagger (Kubernetes)

**Flagger Canary Resource**:
```yaml
apiVersion: flagger.app/v1beta1
kind: Canary
metadata:
  name: myapp
  namespace: production
spec:
  # Deployment reference
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: myapp

  # Service mesh provider
  provider: istio

  # Progressive traffic shift
  progressDeadlineSeconds: 600

  service:
    port: 80
    targetPort: 8080

  # Canary analysis
  analysis:
    # Schedule
    interval: 1m
    threshold: 5
    maxWeight: 50
    stepWeight: 10

    # Metrics
    metrics:
    - name: request-success-rate
      thresholdRange:
        min: 99
      interval: 1m

    - name: request-duration
      thresholdRange:
        max: 500
      interval: 1m

    # Prometheus queries
    - name: error-rate
      templateRef:
        name: error-rate
        namespace: flagger-system
      thresholdRange:
        max: 1
      interval: 1m

    # Webhooks for custom validation
    webhooks:
    - name: load-test
      url: http://flagger-loadtester/
      timeout: 5s
      metadata:
        type: cmd
        cmd: "hey -z 1m -q 10 -c 2 http://myapp-canary/"
```

**MetricTemplate for Custom Metrics**:
```yaml
apiVersion: flagger.app/v1beta1
kind: MetricTemplate
metadata:
  name: error-rate
  namespace: flagger-system
spec:
  provider:
    type: prometheus
    address: http://prometheus:9090
  query: |
    sum(
      rate(
        http_requests_total{
          status=~"5..",
          deployment="{{ target }}"
        }[{{ interval }}]
      )
    )
    /
    sum(
      rate(
        http_requests_total{
          deployment="{{ target }}"
        }[{{ interval }}]
      )
    )
    * 100
```

#### Pattern 2: AWS App Mesh Canary

```yaml
# VirtualService with weighted routing
apiVersion: appmesh.k8s.aws/v1beta2
kind: VirtualService
metadata:
  name: myapp
  namespace: production
spec:
  provider:
    virtualRouter:
      virtualRouterRef:
        name: myapp-router
---
apiVersion: appmesh.k8s.aws/v1beta2
kind: VirtualRouter
metadata:
  name: myapp-router
  namespace: production
spec:
  listeners:
  - portMapping:
      port: 80
      protocol: http
  routes:
  - name: main-route
    httpRoute:
      match:
        prefix: /
      action:
        weightedTargets:
        - virtualNodeRef:
            name: myapp-stable
          weight: 95
        - virtualNodeRef:
            name: myapp-canary
          weight: 5
```

**Automated Canary Controller**:
```python
import boto3
import time
from dataclasses import dataclass

@dataclass
class CanaryConfig:
    stable_version: str
    canary_version: str
    initial_weight: int = 5
    step_weight: int = 15
    max_weight: int = 100
    interval_seconds: int = 300
    error_threshold: float = 1.0  # 1% error rate
    latency_threshold_ms: int = 500

class CanaryController:
    def __init__(self, config: CanaryConfig):
        self.config = config
        self.appmesh = boto3.client('appmesh')
        self.cloudwatch = boto3.client('cloudwatch')
        self.current_weight = 0

    def execute_canary(self):
        """Execute progressive canary deployment"""

        weights = range(
            self.config.initial_weight,
            self.config.max_weight + 1,
            self.config.step_weight
        )

        for weight in weights:
            print(f"Shifting {weight}% traffic to canary...")

            # Update traffic weights
            self.update_weights(weight)
            self.current_weight = weight

            # Wait for metrics
            print(f"Waiting {self.config.interval_seconds}s for metrics...")
            time.sleep(self.config.interval_seconds)

            # Validate health
            if not self.validate_canary_health():
                print(f"Health check failed at {weight}%! Rolling back...")
                self.rollback()
                return False

            print(f"{weight}% deployment successful")

        print("Canary deployment complete!")
        return True

    def update_weights(self, canary_weight: int):
        """Update App Mesh virtual router weights"""
        stable_weight = 100 - canary_weight

        self.appmesh.update_route(
            meshName='production-mesh',
            virtualRouterName='myapp-router',
            routeName='main-route',
            spec={
                'httpRoute': {
                    'match': {'prefix': '/'},
                    'action': {
                        'weightedTargets': [
                            {
                                'virtualNode': 'myapp-stable',
                                'weight': stable_weight
                            },
                            {
                                'virtualNode': 'myapp-canary',
                                'weight': canary_weight
                            }
                        ]
                    }
                }
            }
        )

    def validate_canary_health(self) -> bool:
        """Check canary metrics against thresholds"""

        # Check error rate
        error_rate = self.get_error_rate('myapp-canary')
        if error_rate > self.config.error_threshold:
            print(f"Error rate too high: {error_rate}%")
            return False

        # Check latency
        p99_latency = self.get_p99_latency('myapp-canary')
        if p99_latency > self.config.latency_threshold_ms:
            print(f"P99 latency too high: {p99_latency}ms")
            return False

        # Compare to stable
        stable_error_rate = self.get_error_rate('myapp-stable')
        if error_rate > stable_error_rate * 1.5:
            print(f"Canary error rate significantly worse than stable")
            return False

        return True

    def get_error_rate(self, service: str) -> float:
        """Get error rate from CloudWatch"""
        response = self.cloudwatch.get_metric_statistics(
            Namespace='AWS/AppMesh',
            MetricName='HTTPCode_Target_5XX_Count',
            Dimensions=[
                {'Name': 'VirtualNode', 'Value': service},
            ],
            StartTime=time.time() - 300,
            EndTime=time.time(),
            Period=300,
            Statistics=['Sum']
        )

        errors = response['Datapoints'][0]['Sum'] if response['Datapoints'] else 0

        # Get total requests
        response = self.cloudwatch.get_metric_statistics(
            Namespace='AWS/AppMesh',
            MetricName='RequestCount',
            Dimensions=[
                {'Name': 'VirtualNode', 'Value': service},
            ],
            StartTime=time.time() - 300,
            EndTime=time.time(),
            Period=300,
            Statistics=['Sum']
        )

        total = response['Datapoints'][0]['Sum'] if response['Datapoints'] else 1

        return (errors / total) * 100

    def get_p99_latency(self, service: str) -> float:
        """Get P99 latency from CloudWatch"""
        response = self.cloudwatch.get_metric_statistics(
            Namespace='AWS/AppMesh',
            MetricName='TargetResponseTime',
            Dimensions=[
                {'Name': 'VirtualNode', 'Value': service},
            ],
            StartTime=time.time() - 300,
            EndTime=time.time(),
            Period=300,
            Statistics=['Maximum'],
            ExtendedStatistics=['p99']
        )

        if response['Datapoints']:
            return response['Datapoints'][0].get('p99', 0)
        return 0

    def rollback(self):
        """Rollback to stable version"""
        self.update_weights(0)
        print("Rolled back to stable version")

# Usage
if __name__ == '__main__':
    config = CanaryConfig(
        stable_version='1.0.0',
        canary_version='1.1.0',
        initial_weight=5,
        step_weight=15,
        interval_seconds=300
    )

    controller = CanaryController(config)
    success = controller.execute_canary()

    if not success:
        exit(1)
```

#### Pattern 3: Header-Based Canary

Route specific users (internal employees, beta testers) to canary based on headers.

**Istio VirtualService**:
```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: myapp
spec:
  hosts:
  - myapp.example.com
  http:
  # Route beta testers to canary
  - match:
    - headers:
        x-user-group:
          exact: beta-testers
    route:
    - destination:
        host: myapp
        subset: canary

  # Route internal employees to canary
  - match:
    - headers:
        x-user-email:
          regex: ".*@example.com"
    route:
    - destination:
        host: myapp
        subset: canary

  # Default: weighted routing
  - route:
    - destination:
        host: myapp
        subset: stable
      weight: 95
    - destination:
        host: myapp
        subset: canary
      weight: 5
```

---

## Rolling Deployment

### Concept

Update instances one at a time or in small batches. New version gradually replaces old version without downtime.

```
Initial: [v1] [v1] [v1] [v1] [v1]

Step 1:  [v2] [v1] [v1] [v1] [v1]  ← Update pod 1
Step 2:  [v2] [v2] [v1] [v1] [v1]  ← Update pod 2
Step 3:  [v2] [v2] [v2] [v1] [v1]  ← Update pod 3
Step 4:  [v2] [v2] [v2] [v2] [v1]  ← Update pod 4
Step 5:  [v2] [v2] [v2] [v2] [v2]  ← Update pod 5

Final:   [v2] [v2] [v2] [v2] [v2]
```

### Benefits

**Advantages**:
- No extra infrastructure needed
- Zero downtime
- Gradual rollout
- Built into most platforms

**Disadvantages**:
- Mixed versions during deployment
- Slower rollback
- No instant switch
- Requires backward compatibility

### Implementation Patterns

#### Pattern 1: Kubernetes RollingUpdate

**Deployment with RollingUpdate Strategy**:
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
      maxSurge: 2         # Max 2 extra pods during update
      maxUnavailable: 1   # Max 1 pod can be unavailable

  selector:
    matchLabels:
      app: myapp

  template:
    metadata:
      labels:
        app: myapp
        version: "1.1.0"
    spec:
      containers:
      - name: app
        image: myapp:1.1.0
        ports:
        - containerPort: 8080

        # Liveness probe
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
          failureThreshold: 3

        # Readiness probe (critical for rolling updates)
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 5
          failureThreshold: 2

        # Resource limits
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 512Mi
```

**How It Works**:
1. Kubernetes creates 1 new pod (within maxSurge limit)
2. Waits for readiness probe to pass
3. Marks 1 old pod as terminating
4. Waits for old pod to finish graceful shutdown
5. Repeats until all pods are new version

**Controlling Rollout Speed**:
```bash
# Slow rollout (1 pod at a time)
maxSurge: 1
maxUnavailable: 0

# Fast rollout (replace 50% at once)
maxSurge: 50%
maxUnavailable: 0

# Balanced (2 extra, 1 down)
maxSurge: 2
maxUnavailable: 1
```

#### Pattern 2: AWS ECS Rolling Update

**ECS Service with Rolling Update**:
```json
{
  "serviceName": "myapp",
  "cluster": "production",
  "taskDefinition": "myapp:5",
  "desiredCount": 10,
  "deploymentConfiguration": {
    "deploymentCircuitBreaker": {
      "enable": true,
      "rollback": true
    },
    "maximumPercent": 200,
    "minimumHealthyPercent": 100
  },
  "healthCheckGracePeriodSeconds": 60,
  "loadBalancers": [
    {
      "targetGroupArn": "arn:aws:elasticloadbalancing:...",
      "containerName": "myapp",
      "containerPort": 8080
    }
  ]
}
```

**Deployment Circuit Breaker**:
Automatically rolls back if:
- Tasks fail to start
- Health checks fail
- Too many tasks stop unexpectedly

```bash
# Deploy new task definition
aws ecs update-service \
  --cluster production \
  --service myapp \
  --task-definition myapp:6 \
  --force-new-deployment

# Monitor rollout
aws ecs wait services-stable \
  --cluster production \
  --services myapp
```

#### Pattern 3: Application-Level Rolling Update

For non-container deployments (VMs, bare metal).

**Ansible Rolling Update**:
```yaml
# rolling-update.yml
- name: Rolling update
  hosts: app_servers
  serial: "25%"  # Update 25% of hosts at a time

  tasks:
  - name: Remove from load balancer
    uri:
      url: "http://lb.example.com/api/pool/remove"
      method: POST
      body_format: json
      body:
        server: "{{ inventory_hostname }}"

  - name: Wait for connections to drain
    wait_for:
      timeout: 30

  - name: Stop application
    systemd:
      name: myapp
      state: stopped

  - name: Update application
    copy:
      src: /builds/myapp-v1.1.0
      dest: /opt/myapp/current
      owner: app
      group: app
      mode: '0755'

  - name: Run database migrations
    command: /opt/myapp/current/migrate
    run_once: true
    delegate_to: "{{ groups['app_servers'][0] }}"

  - name: Start application
    systemd:
      name: myapp
      state: started
      enabled: yes

  - name: Wait for health check
    uri:
      url: "http://{{ inventory_hostname }}:8080/health"
      status_code: 200
    register: result
    until: result.status == 200
    retries: 12
    delay: 5

  - name: Add back to load balancer
    uri:
      url: "http://lb.example.com/api/pool/add"
      method: POST
      body_format: json
      body:
        server: "{{ inventory_hostname }}"

  - name: Pause between batches
    pause:
      seconds: 30
```

### Graceful Shutdown

Critical for rolling updates to avoid dropping connections.

**Application Code**:
```python
import signal
import sys
import time
from http.server import HTTPServer

class GracefulHTTPServer(HTTPServer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_shutting_down = False

        # Register signal handlers
        signal.signal(signal.SIGTERM, self.handle_shutdown)
        signal.signal(signal.SIGINT, self.handle_shutdown)

    def handle_shutdown(self, signum, frame):
        """Handle shutdown signal"""
        print(f"Received signal {signum}, starting graceful shutdown...")
        self.is_shutting_down = True

        # Stop accepting new connections
        self.server_close()

        # Wait for existing requests to complete
        print("Waiting for existing requests to complete...")
        time.sleep(10)  # Grace period

        # Exit
        print("Shutdown complete")
        sys.exit(0)

# Kubernetes sends SIGTERM, waits terminationGracePeriodSeconds (default 30s),
# then sends SIGKILL
```

**Kubernetes Pod Lifecycle**:
```yaml
spec:
  terminationGracePeriodSeconds: 60  # Time to gracefully shutdown
  containers:
  - name: app
    lifecycle:
      preStop:
        exec:
          # Called before SIGTERM
          command: ["/bin/sh", "-c", "sleep 5"]  # Allow time for readiness probe updates to propagate
```

---

## Recreate Deployment

### Concept

Simplest strategy: shut down all old instances, then start new instances. Results in downtime.

```
Step 1: [v1] [v1] [v1] [v1] [v1]  ← Running v1

Step 2: [ ] [ ] [ ] [ ] [ ]        ← Shutdown all

Step 3: [v2] [v2] [v2] [v2] [v2]  ← Start v2
```

### When to Use

**Good for**:
- Development/staging environments
- Non-critical applications
- Major version upgrades that can't run side-by-side
- Database schema changes requiring downtime
- Cost-sensitive deployments

**Avoid for**:
- Production systems
- Customer-facing applications
- SLA requirements

### Implementation

**Kubernetes Recreate Strategy**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  replicas: 5
  strategy:
    type: Recreate  # Terminates all pods before creating new ones

  selector:
    matchLabels:
      app: myapp

  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: app
        image: myapp:2.0.0
```

**Maintenance Window Deployment**:
```bash
#!/bin/bash
# deploy-with-maintenance.sh

set -euo pipefail

# Display maintenance page
kubectl apply -f maintenance-page.yaml

# Scale down application
kubectl scale deployment myapp --replicas=0

# Wait for pods to terminate
kubectl wait --for=delete pod -l app=myapp --timeout=60s

# Run database migrations
kubectl apply -f db-migration-job.yaml
kubectl wait --for=condition=complete job/db-migration --timeout=600s

# Deploy new version
kubectl set image deployment/myapp app=myapp:2.0.0

# Scale up
kubectl scale deployment myapp --replicas=5

# Wait for new pods
kubectl wait --for=condition=ready pod -l app=myapp --timeout=300s

# Remove maintenance page
kubectl delete -f maintenance-page.yaml

echo "Deployment complete!"
```

---

## Progressive Delivery

### Concept

Combining deployment strategies with feature flags, experimentation, and observability for controlled, data-driven rollouts.

### Progressive Delivery Pipeline

```
Code → Build → Deploy (canary) → Observe → Decide
                 ↓                  ↓         ↓
           Feature flag ON     Metrics OK?   Expand
                                    ↓         or
                               Metrics bad?   Rollback
```

### Feature Flags + Canary

Decouple deployment from release:
- **Deploy**: Get code to production
- **Release**: Enable features for users

**LaunchDarkly + Kubernetes Example**:
```python
import ldclient
from ldclient.config import Config

# Initialize LaunchDarkly
ldclient.set_config(Config("sdk-key"))
ld_client = ldclient.get()

def get_pricing_page(user_id):
    user = {
        "key": user_id,
        "custom": {
            "deployment_version": os.getenv("APP_VERSION"),
            "canary_group": os.getenv("CANARY_GROUP", "stable")
        }
    }

    # Check feature flag
    show_new_pricing = ld_client.variation("new-pricing-page", user, False)

    if show_new_pricing:
        return render_template("pricing_v2.html")
    else:
        return render_template("pricing_v1.html")
```

**Targeting Rules**:
```json
{
  "flagKey": "new-pricing-page",
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

### Experimentation (A/B Testing)

Run controlled experiments during rollout.

**Optimizely + Metrics Example**:
```python
from optimizely import optimizely
from datadog import statsd

# Initialize Optimizely
optimizely_client = optimizely.Optimizely(datafile=datafile)

def checkout_page(user_id):
    # Assign user to variation
    variation = optimizely_client.activate(
        'checkout_redesign',
        user_id,
        attributes={'platform': 'web'}
    )

    # Track conversion
    def track_purchase(order_value):
        optimizely_client.track(
            'purchase',
            user_id,
            attributes={'revenue': order_value}
        )

        # Also track in monitoring
        statsd.increment(
            'checkout.purchase',
            tags=[f'variation:{variation}']
        )
        statsd.histogram(
            'checkout.revenue',
            order_value,
            tags=[f'variation:{variation}']
        )

    if variation == 'new_checkout':
        return render_template("checkout_v2.html", track_fn=track_purchase)
    else:
        return render_template("checkout_v1.html", track_fn=track_purchase)
```

---

## Feature Flags

### Types of Feature Flags

1. **Release Flags**: Control feature rollout
2. **Ops Flags**: Kill switches for emergencies
3. **Experiment Flags**: A/B testing
4. **Permission Flags**: Entitlements

### Implementation Patterns

#### Pattern 1: Simple Boolean Flag

```python
# config.py
FEATURE_FLAGS = {
    'new_search': os.getenv('FEATURE_NEW_SEARCH', 'false').lower() == 'true',
    'ml_recommendations': os.getenv('FEATURE_ML_RECS', 'false').lower() == 'true',
}

def is_enabled(flag_name):
    return FEATURE_FLAGS.get(flag_name, False)

# usage
if is_enabled('new_search'):
    return new_search_algorithm(query)
else:
    return old_search_algorithm(query)
```

#### Pattern 2: Percentage Rollout

```python
import hashlib

def is_enabled_for_user(flag_name, user_id, rollout_percentage):
    """
    Deterministic assignment based on user_id hash.
    Same user always gets same assignment.
    """
    hash_input = f"{flag_name}:{user_id}"
    hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
    bucket = hash_value % 100
    return bucket < rollout_percentage

# Rollout to 10% of users
if is_enabled_for_user('new_checkout', user.id, rollout_percentage=10):
    return new_checkout_flow()
```

#### Pattern 3: Targeting Rules

```python
from dataclasses import dataclass
from typing import List, Callable

@dataclass
class Rule:
    name: str
    condition: Callable
    enabled: bool

class FeatureFlag:
    def __init__(self, name, default=False):
        self.name = name
        self.default = default
        self.rules: List[Rule] = []

    def add_rule(self, name, condition, enabled):
        self.rules.append(Rule(name, condition, enabled))
        return self

    def is_enabled(self, context):
        # Check rules in order
        for rule in self.rules:
            if rule.condition(context):
                return rule.enabled

        # Default
        return self.default

# Usage
new_dashboard_flag = FeatureFlag('new_dashboard', default=False)
new_dashboard_flag.add_rule(
    'internal_users',
    lambda ctx: ctx.user.email.endswith('@example.com'),
    enabled=True
).add_rule(
    'beta_testers',
    lambda ctx: ctx.user.groups.contains('beta'),
    enabled=True
).add_rule(
    'gradual_rollout',
    lambda ctx: is_enabled_for_user('new_dashboard', ctx.user.id, 25),
    enabled=True
)

# Check flag
context = {'user': current_user}
if new_dashboard_flag.is_enabled(context):
    return render_template('dashboard_v2.html')
```

### Kill Switches

Emergency off switches for critical issues.

```python
# Redis-backed kill switch
import redis

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def is_feature_killed(feature_name):
    """Check if feature is killed"""
    return redis_client.get(f"kill_switch:{feature_name}") == b"true"

def kill_feature(feature_name, reason):
    """Kill a feature (can be called via admin API)"""
    redis_client.set(f"kill_switch:{feature_name}", "true")
    redis_client.set(f"kill_switch:{feature_name}:reason", reason)
    redis_client.set(f"kill_switch:{feature_name}:killed_at", datetime.now().isoformat())

    # Alert team
    send_alert(f"Feature {feature_name} killed: {reason}")

# Usage
if not is_feature_killed('ml_recommendations'):
    recommendations = get_ml_recommendations(user)
else:
    # Fallback
    recommendations = get_simple_recommendations(user)
```

### Feature Flag Lifecycle

```
1. CREATE flag (default OFF)
   ↓
2. ENABLE for internal users
   ↓
3. ENABLE for beta testers
   ↓
4. GRADUAL rollout (1% → 5% → 25% → 50% → 100%)
   ↓
5. REMOVE flag from code
   ↓
6. DELETE flag config
```

**Technical Debt Management**:
```python
# Add expiry metadata
@dataclass
class FeatureFlagMetadata:
    name: str
    created_at: datetime
    created_by: str
    description: str
    intended_lifecycle: str  # "temporary", "permanent", "ops"
    removal_ticket: Optional[str] = None

# Alert on old temporary flags
def audit_feature_flags():
    old_flags = [
        flag for flag in get_all_flags()
        if flag.intended_lifecycle == "temporary"
        and (datetime.now() - flag.created_at).days > 90
        and not flag.removal_ticket
    ]

    if old_flags:
        create_tech_debt_ticket(
            f"Remove {len(old_flags)} old feature flags",
            flags=old_flags
        )
```

---

## Rollback Procedures

### Rollback Decision Criteria

**Automatic Rollback Triggers**:
- Error rate > threshold (e.g., 1%)
- Response time > threshold (e.g., p99 > 1s)
- Health check failures
- Crash loops
- Resource exhaustion

**Manual Rollback Indicators**:
- Customer complaints spike
- Revenue drop
- Critical bug reports
- Security issues

### Rollback Strategies by Deployment Type

| Deployment | Rollback Speed | Rollback Method |
|------------|----------------|-----------------|
| Blue-Green | Instant | Switch router back |
| Canary | Fast | Set weight to 0% |
| Rolling | Medium | Revert deployment |
| Recreate | Slow | Deploy previous version |

### Implementation Patterns

#### Pattern 1: Automated Rollback (Kubernetes)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  replicas: 10
  revisionHistoryLimit: 10  # Keep last 10 revisions

  progressDeadlineSeconds: 600  # Rollback if not ready in 10min

  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
      maxSurge: 1
```

**Manual Rollback**:
```bash
# View deployment history
kubectl rollout history deployment/myapp

# Rollback to previous version
kubectl rollout undo deployment/myapp

# Rollback to specific revision
kubectl rollout undo deployment/myapp --to-revision=3

# Pause rollout (if issues detected mid-deployment)
kubectl rollout pause deployment/myapp

# Resume after investigation
kubectl rollout resume deployment/myapp
```

**Automated Rollback Script**:
```bash
#!/bin/bash
# auto-rollback.sh

set -euo pipefail

DEPLOYMENT=$1
NAMESPACE=${2:-default}
ERROR_THRESHOLD=5  # Max 5% error rate
CHECK_DURATION=300  # 5 minutes

echo "Monitoring deployment: $DEPLOYMENT"

for i in {1..10}; do
  sleep 30

  # Get error rate from Prometheus
  ERROR_RATE=$(curl -s "http://prometheus:9090/api/v1/query" \
    --data-urlencode "query=sum(rate(http_requests_total{status=~\"5..\",deployment=\"$DEPLOYMENT\"}[5m]))/sum(rate(http_requests_total{deployment=\"$DEPLOYMENT\"}[5m]))*100" \
    | jq -r '.data.result[0].value[1]' || echo "0")

  echo "Current error rate: $ERROR_RATE%"

  # Check threshold
  if (( $(echo "$ERROR_RATE > $ERROR_THRESHOLD" | bc -l) )); then
    echo "ERROR: Error rate $ERROR_RATE% exceeds threshold $ERROR_THRESHOLD%"
    echo "Rolling back deployment..."

    kubectl rollout undo deployment/$DEPLOYMENT -n $NAMESPACE

    # Send alert
    curl -X POST https://hooks.slack.com/services/xxx \
      -H 'Content-Type: application/json' \
      -d "{\"text\":\"🚨 Auto-rollback triggered for $DEPLOYMENT due to high error rate: $ERROR_RATE%\"}"

    exit 1
  fi
done

echo "Deployment stable ✅"
```

#### Pattern 2: Database Rollback

**Challenge**: Can't rollback database easily. Must plan ahead.

**Backward Compatible Migrations**:
```sql
-- WRONG: Can't rollback easily
ALTER TABLE users DROP COLUMN legacy_field;

-- RIGHT: Keep old field, mark deprecated
ALTER TABLE users ADD COLUMN legacy_field_deprecated BOOLEAN DEFAULT TRUE;
-- Remove in future migration after code rollback period passes
```

**Migration Rollback Script**:
```python
# migrations/003_add_email_verification.py

def upgrade():
    """Forward migration"""
    op.add_column('users',
        sa.Column('email_verified', sa.Boolean(), nullable=True)
    )
    op.add_column('users',
        sa.Column('email_verified_at', sa.DateTime(), nullable=True)
    )

def downgrade():
    """Rollback migration"""
    op.drop_column('users', 'email_verified_at')
    op.drop_column('users', 'email_verified')

# Apply migration
alembic upgrade head

# Rollback if needed
alembic downgrade -1  # Go back 1 version
```

**Data Migration Rollback**:
```python
# For data migrations, keep audit trail

def migrate_user_preferences():
    """Migrate preferences from JSON to normalized table"""

    # 1. Copy data to new table
    db.execute("""
        INSERT INTO user_preferences (user_id, key, value)
        SELECT
            id,
            jsonb_object_keys(preferences),
            preferences->>jsonb_object_keys(preferences)
        FROM users
        WHERE preferences IS NOT NULL
    """)

    # 2. Keep old column (don't drop until rollback period passes)
    # 3. Dual write during transition
    # 4. After rollback period, drop old column

# Rollback: truncate new table, rely on old column still being there
# Example of safe rollback strategy - clearing temp data while preserving original
def rollback_user_preferences():
    db.execute("TRUNCATE user_preferences")
    # Old column still has data
```

---

## Zero-Downtime Deployments

### Requirements

1. **Load Balancer Health Checks**: Only send traffic to healthy instances
2. **Graceful Shutdown**: Finish processing requests before stopping
3. **Readiness Probes**: Don't accept traffic until ready
4. **Connection Draining**: Wait for connections to close
5. **Backward Compatibility**: Old and new versions can coexist

### Health Check Best Practices

**Deep Health Check**:
```python
from flask import Flask, jsonify
import redis
import psycopg2

app = Flask(__name__)

@app.route('/health')
def health():
    """Liveness probe - is app alive?"""
    return jsonify({"status": "ok"}), 200

@app.route('/ready')
def ready():
    """Readiness probe - is app ready for traffic?"""
    health_status = {
        "database": "unknown",
        "cache": "unknown",
        "disk": "unknown"
    }

    all_healthy = True

    # Check database
    try:
        conn = psycopg2.connect("dbname=myapp")
        conn.close()
        health_status["database"] = "healthy"
    except Exception as e:
        health_status["database"] = "unhealthy"
        all_healthy = False

    # Check cache
    try:
        r = redis.Redis(host='redis')
        r.ping()
        health_status["cache"] = "healthy"
    except Exception as e:
        health_status["cache"] = "unhealthy"
        all_healthy = False

    # Check disk space
    import shutil
    stat = shutil.disk_usage("/")
    free_percent = (stat.free / stat.total) * 100
    if free_percent < 10:
        health_status["disk"] = "unhealthy"
        all_healthy = False
    else:
        health_status["disk"] = "healthy"

    status_code = 200 if all_healthy else 503
    return jsonify(health_status), status_code
```

### Connection Draining

**ALB Connection Draining**:
```bash
# Configure deregistration delay (time to drain connections)
aws elbv2 modify-target-group-attributes \
  --target-group-arn $TG_ARN \
  --attributes Key=deregistration_delay.timeout_seconds,Value=300
```

**NGINX Connection Draining**:
```nginx
# nginx.conf
upstream app {
    server app1.example.com:8080;
    server app2.example.com:8080;

    # Gracefully remove servers
    keepalive 32;
}

server {
    listen 80;

    location / {
        proxy_pass http://app;
        proxy_http_version 1.1;

        # Allow long-running requests to complete
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }
}
```

**Graceful Shutdown Pattern**:
```go
package main

import (
    "context"
    "net/http"
    "os"
    "os/signal"
    "syscall"
    "time"
)

func main() {
    srv := &http.Server{Addr: ":8080"}

    // Start server
    go func() {
        if err := srv.ListenAndServe(); err != http.ErrServerClosed {
            log.Fatalf("Server failed: %v", err)
        }
    }()

    // Wait for interrupt signal
    stop := make(chan os.Signal, 1)
    signal.Notify(stop, os.Interrupt, syscall.SIGTERM)
    <-stop

    // Graceful shutdown with timeout
    ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
    defer cancel()

    log.Println("Shutting down gracefully...")
    if err := srv.Shutdown(ctx); err != nil {
        log.Fatalf("Server forced to shutdown: %v", err)
    }

    log.Println("Server stopped")
}
```

---

## Database Migrations

### Migration Strategies

#### Strategy 1: Expand-Migrate-Contract

**Phase 1: Expand** (deploy new schema alongside old)
```sql
-- Add new column (nullable)
ALTER TABLE orders ADD COLUMN status_v2 VARCHAR(50);

-- Deploy application v1.1 that writes to BOTH columns
```

**Phase 2: Migrate** (copy data)
```sql
-- Backfill new column
UPDATE orders
SET status_v2 = CASE
    WHEN status = 0 THEN 'pending'
    WHEN status = 1 THEN 'processing'
    WHEN status = 2 THEN 'completed'
    WHEN status = 3 THEN 'cancelled'
END
WHERE status_v2 IS NULL;
```

**Phase 3: Contract** (remove old schema)
```sql
-- Deploy application v1.2 that only uses new column

-- Drop old column
ALTER TABLE orders DROP COLUMN status;

-- Rename new column
ALTER TABLE orders RENAME COLUMN status_v2 TO status;
```

#### Strategy 2: Shadow Tables

For major schema changes:

```sql
-- Create new table with desired schema
CREATE TABLE orders_v2 (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    status VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Copy data
INSERT INTO orders_v2 (id, user_id, status, created_at)
SELECT id, user_id,
    CASE
        WHEN status = 0 THEN 'pending'
        WHEN status = 1 THEN 'processing'
        WHEN status = 2 THEN 'completed'
        WHEN status = 3 THEN 'cancelled'
    END,
    created_at
FROM orders;

-- Application does dual writes during transition

-- Swap tables (during maintenance window if needed)
BEGIN;
ALTER TABLE orders RENAME TO orders_old;
ALTER TABLE orders_v2 RENAME TO orders;
COMMIT;
```

#### Strategy 3: Database Views

Provide backward compatibility via views:

```sql
-- New normalized schema
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(255) NOT NULL
);

CREATE TABLE user_profiles (
    user_id BIGINT PRIMARY KEY REFERENCES users(id),
    email VARCHAR(255) NOT NULL,
    full_name VARCHAR(255)
);

-- Backward-compatible view for old code
CREATE VIEW users_legacy AS
SELECT
    u.id,
    u.username,
    p.email,
    p.full_name
FROM users u
LEFT JOIN user_profiles p ON u.id = p.user_id;

-- Old code continues to query users_legacy
-- New code queries users + user_profiles directly
```

### Online Schema Change Tools

**GitHub's gh-ost**:
```bash
# Non-blocking table migration
gh-ost \
  --user=root \
  --password=secret \
  --host=mysql.example.com \
  --database=myapp \
  --table=orders \
  --alter="ADD COLUMN priority INT NOT NULL DEFAULT 0" \
  --exact-rowcount \
  --concurrent-rowcount \
  --default-retries=120 \
  --chunk-size=1000 \
  --max-load=Threads_running=25 \
  --critical-load=Threads_running=1000 \
  --execute
```

**How it works**:
1. Creates ghost table with new schema
2. Copies data in chunks
3. Captures ongoing changes via binary log
4. Swaps tables atomically

**Percona pt-online-schema-change**:
```bash
pt-online-schema-change \
  --alter="ADD COLUMN email_verified BOOLEAN DEFAULT FALSE" \
  --execute \
  D=myapp,t=users \
  --chunk-size=1000 \
  --max-load="Threads_running=50" \
  --critical-load="Threads_running=100"
```

---

## Kubernetes Deployment Strategies

### Native Strategies Summary

```yaml
# 1. RollingUpdate (default)
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1
    maxUnavailable: 1

# 2. Recreate
strategy:
  type: Recreate
```

### Advanced Strategies with Service Mesh

#### Istio Traffic Shifting

**Gradual Canary**:
```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: myapp
spec:
  hosts:
  - myapp
  http:
  - match:
    - headers:
        end-user:
          exact: "debug"
    route:
    - destination:
        host: myapp
        subset: v2
  - route:
    - destination:
        host: myapp
        subset: v1
      weight: 90
    - destination:
        host: myapp
        subset: v2
      weight: 10
---
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: myapp
spec:
  host: myapp
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
```

#### Argo Rollouts

**Canary with Analysis**:
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: myapp
spec:
  replicas: 10
  strategy:
    canary:
      steps:
      - setWeight: 10
      - pause: {duration: 10m}
      - setWeight: 20
      - pause: {duration: 10m}
      - setWeight: 40
      - pause: {duration: 10m}
      - setWeight: 60
      - pause: {duration: 10m}
      - setWeight: 80
      - pause: {duration: 10m}

      analysis:
        templates:
        - templateName: success-rate
        startingStep: 2

        args:
        - name: service-name
          value: myapp

  revisionHistoryLimit: 5
  selector:
    matchLabels:
      app: myapp

  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: myapp
        image: myapp:v2
        ports:
        - containerPort: 8080
---
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: success-rate
spec:
  args:
  - name: service-name

  metrics:
  - name: success-rate
    initialDelay: 60s
    interval: 5m
    successCondition: result[0] >= 0.95
    provider:
      prometheus:
        address: http://prometheus:9090
        query: |
          sum(rate(
            http_requests_total{
              service="{{ args.service-name }}",
              status!~"5.."
            }[5m]
          ))
          /
          sum(rate(
            http_requests_total{
              service="{{ args.service-name }}"
            }[5m]
          ))
```

**Blue-Green with Preview**:
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: myapp
spec:
  replicas: 3
  strategy:
    blueGreen:
      activeService: myapp-active
      previewService: myapp-preview
      autoPromotionEnabled: false

      prePromotionAnalysis:
        templates:
        - templateName: smoke-tests

      postPromotionAnalysis:
        templates:
        - templateName: success-rate

  selector:
    matchLabels:
      app: myapp

  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: myapp
        image: myapp:v2
---
apiVersion: v1
kind: Service
metadata:
  name: myapp-active
spec:
  selector:
    app: myapp
  ports:
  - port: 80
    targetPort: 8080
---
apiVersion: v1
kind: Service
metadata:
  name: myapp-preview
spec:
  selector:
    app: myapp
  ports:
  - port: 80
    targetPort: 8080
```

**Manual Promotion**:
```bash
# Promote to active
kubectl argo rollouts promote myapp

# Abort rollout
kubectl argo rollouts abort myapp

# Retry rollout
kubectl argo rollouts retry myapp
```

---

## Cloud Provider Strategies

### AWS Deployment Options

#### ECS Blue-Green with CodeDeploy

**CodeDeploy AppSpec**:
```yaml
version: 0.0
Resources:
  - TargetService:
      Type: AWS::ECS::Service
      Properties:
        TaskDefinition: "arn:aws:ecs:us-east-1:123456789012:task-definition/myapp:5"
        LoadBalancerInfo:
          ContainerName: "myapp"
          ContainerPort: 8080
        PlatformVersion: "LATEST"

Hooks:
  - BeforeInstall: "LambdaFunctionToValidateBeforeInstall"
  - AfterInstall: "LambdaFunctionToValidateAfterInstall"
  - AfterAllowTestTraffic: "LambdaFunctionToValidateAfterTestTrafficStarts"
  - BeforeAllowTraffic: "LambdaFunctionToValidateBeforeAllowingProductionTraffic"
  - AfterAllowTraffic: "LambdaFunctionToValidateAfterAllowingProductionTraffic"
```

**Deployment Configuration**:
```json
{
  "deploymentConfigName": "CodeDeployDefault.ECSCanary10Percent5Minutes",
  "computePlatform": "ECS",
  "trafficRoutingConfig": {
    "type": "TimeBasedCanary",
    "timeBasedCanary": {
      "canaryPercentage": 10,
      "canaryInterval": 5
    }
  }
}
```

**Options**:
- `ECSCanary10Percent5Minutes`: 10% for 5 min, then 100%
- `ECSLinear10PercentEvery3Minutes`: Linear progression
- `ECSAllAtOnce`: Immediate switch

#### Lambda Deployment

**Canary Deployment**:
```yaml
# SAM template
Resources:
  MyFunction:
    Type: AWS::Serverless::Function
    Properties:
      Handler: index.handler
      Runtime: python3.9
      AutoPublishAlias: live

      DeploymentPreference:
        Type: Canary10Percent10Minutes
        Alarms:
          - !Ref MyFunctionErrorsAlarm
        Hooks:
          PreTraffic: !Ref PreTrafficHook
          PostTraffic: !Ref PostTrafficHook

  MyFunctionErrorsAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmDescription: Lambda errors
      MetricName: Errors
      Namespace: AWS/Lambda
      Statistic: Sum
      Period: 60
      EvaluationPeriods: 2
      Threshold: 0
      ComparisonOperator: GreaterThanThreshold
```

### GCP Deployment Options

#### Cloud Run Blue-Green

```bash
# Deploy new revision (no traffic)
gcloud run deploy myapp \
  --image gcr.io/my-project/myapp:v2 \
  --no-traffic \
  --region us-central1

# Test new revision
REVISION_URL=$(gcloud run services describe myapp \
  --region us-central1 \
  --format='value(status.traffic[0].url)')

curl $REVISION_URL/health

# Shift 10% traffic
gcloud run services update-traffic myapp \
  --region us-central1 \
  --to-revisions LATEST=10

# Monitor metrics...

# Shift all traffic
gcloud run services update-traffic myapp \
  --region us-central1 \
  --to-latest
```

#### GKE with Anthos Service Mesh

Similar to Istio traffic management (Anthos uses Istio under the hood).

### Azure Deployment Options

#### App Service Deployment Slots

```bash
# Create deployment slot
az webapp deployment slot create \
  --name myapp \
  --resource-group mygroup \
  --slot staging

# Deploy to staging slot
az webapp deployment source config-zip \
  --resource-group mygroup \
  --name myapp \
  --slot staging \
  --src app.zip

# Test staging
curl https://myapp-staging.azurewebsites.net/health

# Swap slots (blue-green switch)
az webapp deployment slot swap \
  --resource-group mygroup \
  --name myapp \
  --slot staging \
  --target-slot production
```

**Traffic Routing (Canary)**:
```bash
# Route 10% to staging
az webapp traffic-routing set \
  --resource-group mygroup \
  --name myapp \
  --distribution staging=10

# Remove routing
az webapp traffic-routing clear \
  --resource-group mygroup \
  --name myapp
```

---

## Traffic Management

### Load Balancer Configuration

#### Weighted Round Robin

**HAProxy**:
```
backend myapp
    balance roundrobin

    server app-v1-1 10.0.1.10:8080 check weight 9
    server app-v1-2 10.0.1.11:8080 check weight 9
    server app-v2-1 10.0.2.10:8080 check weight 1
```

#### Least Connections

**NGINX**:
```nginx
upstream myapp {
    least_conn;

    server app1.example.com:8080;
    server app2.example.com:8080;
    server app3.example.com:8080;
}
```

### Session Affinity (Sticky Sessions)

**Problem**: User gets routed to different versions mid-session.

**Solution**: Pin user to same backend.

**NGINX Sticky Sessions**:
```nginx
upstream myapp {
    ip_hash;  # Route based on client IP

    server app1.example.com:8080;
    server app2.example.com:8080;
}

# Or cookie-based
upstream myapp {
    server app1.example.com:8080;
    server app2.example.com:8080;

    sticky cookie srv_id expires=1h domain=.example.com path=/;
}
```

**Kubernetes Service**:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: myapp
spec:
  selector:
    app: myapp
  sessionAffinity: ClientIP
  sessionAffinityConfig:
    clientIP:
      timeoutSeconds: 10800  # 3 hours
  ports:
  - port: 80
    targetPort: 8080
```

### Circuit Breaking

Prevent cascading failures during deployment.

**Istio Circuit Breaker**:
```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: myapp
spec:
  host: myapp
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 50
        http2MaxRequests: 100
        maxRequestsPerConnection: 2

    outlierDetection:
      consecutiveErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
      minHealthPercent: 40
```

---

## Monitoring and Observability

### Key Metrics During Deployment

**RED Metrics**:
- **Rate**: Requests per second
- **Errors**: Error rate
- **Duration**: Response time

**USE Metrics**:
- **Utilization**: CPU, memory usage
- **Saturation**: Queue depth
- **Errors**: Error count

### Prometheus Queries for Deployment Monitoring

```promql
# Error rate comparison (canary vs stable)
sum(rate(http_requests_total{status=~"5..",version="canary"}[5m]))
/
sum(rate(http_requests_total{version="canary"}[5m]))

# Latency comparison
histogram_quantile(0.99,
  sum(rate(http_request_duration_seconds_bucket{version="canary"}[5m])) by (le)
)

# Request rate
sum(rate(http_requests_total{version="canary"}[5m]))

# Saturation (queue depth)
avg(queue_depth{service="myapp",version="canary"})
```

### Deployment Dashboard

**Grafana Dashboard JSON**:
```json
{
  "panels": [
    {
      "title": "Request Rate by Version",
      "targets": [
        {
          "expr": "sum(rate(http_requests_total[5m])) by (version)"
        }
      ]
    },
    {
      "title": "Error Rate by Version",
      "targets": [
        {
          "expr": "sum(rate(http_requests_total{status=~\"5..\"}[5m])) by (version) / sum(rate(http_requests_total[5m])) by (version) * 100"
        }
      ]
    },
    {
      "title": "P99 Latency by Version",
      "targets": [
        {
          "expr": "histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (version, le))"
        }
      ]
    }
  ]
}
```

### Alerting During Deployment

**AlertManager Rules**:
```yaml
groups:
- name: deployment
  rules:
  - alert: HighErrorRateDuringDeployment
    expr: |
      sum(rate(http_requests_total{status=~"5..",version="canary"}[5m]))
      /
      sum(rate(http_requests_total{version="canary"}[5m]))
      > 0.01
    for: 2m
    labels:
      severity: critical
    annotations:
      summary: "High error rate in canary deployment"
      description: "Canary version has {{ $value }}% error rate"

  - alert: HighLatencyDuringDeployment
    expr: |
      histogram_quantile(0.99,
        sum(rate(http_request_duration_seconds_bucket{version="canary"}[5m])) by (le)
      ) > 1.0
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High latency in canary deployment"
      description: "Canary P99 latency is {{ $value }}s"
```

---

## Testing Strategies

### Pre-Deployment Testing

1. **Unit Tests**: Test individual components
2. **Integration Tests**: Test component interactions
3. **E2E Tests**: Test full user flows
4. **Load Tests**: Validate performance
5. **Chaos Tests**: Test resilience

### Smoke Testing

Quick validation after deployment.

```python
import requests
import sys

def smoke_test(base_url):
    """Run smoke tests against deployed environment"""

    tests = [
        # Health check
        {
            'name': 'Health Check',
            'url': f'{base_url}/health',
            'expected_status': 200,
            'expected_body': {'status': 'ok'}
        },
        # Critical API endpoint
        {
            'name': 'List Products',
            'url': f'{base_url}/api/products',
            'expected_status': 200,
            'validate': lambda r: len(r.json()['products']) > 0
        },
        # Authentication
        {
            'name': 'Login',
            'url': f'{base_url}/api/login',
            'method': 'POST',
            'json': {'username': 'test', 'password': 'test'},
            'expected_status': 200,
            'validate': lambda r: 'token' in r.json()
        }
    ]

    failed = []

    for test in tests:
        try:
            method = test.get('method', 'GET')
            if method == 'GET':
                response = requests.get(test['url'], timeout=10)
            else:
                response = requests.post(
                    test['url'],
                    json=test.get('json'),
                    timeout=10
                )

            # Check status
            if response.status_code != test['expected_status']:
                failed.append(f"{test['name']}: Expected {test['expected_status']}, got {response.status_code}")
                continue

            # Custom validation
            if 'validate' in test:
                if not test['validate'](response):
                    failed.append(f"{test['name']}: Validation failed")
                    continue

            # Expected body
            if 'expected_body' in test:
                if response.json() != test['expected_body']:
                    failed.append(f"{test['name']}: Body mismatch")
                    continue

            print(f"✓ {test['name']}")

        except Exception as e:
            failed.append(f"{test['name']}: {str(e)}")

    if failed:
        print("\nFailed tests:")
        for failure in failed:
            print(f"✗ {failure}")
        return False

    print("\nAll smoke tests passed ✓")
    return True

if __name__ == '__main__':
    if not smoke_test('https://myapp.example.com'):
        sys.exit(1)
```

### Canary Testing with Real Traffic

**Synthetic Monitoring**:
```python
# Datadog Synthetics example
from datadog_api_client import ApiClient, Configuration
from datadog_api_client.v1.api.synthetics_api import SyntheticsApi

config = Configuration()
api_client = ApiClient(config)
api = SyntheticsApi(api_client)

# Create API test
test = api.create_synthetics_api_test(
    body={
        "name": "Canary Health Check",
        "type": "api",
        "subtype": "http",
        "request": {
            "method": "GET",
            "url": "https://myapp-canary.example.com/health",
            "headers": {
                "X-Canary-Test": "true"
            }
        },
        "assertions": [
            {"type": "statusCode", "operator": "is", "target": 200},
            {"type": "responseTime", "operator": "lessThan", "target": 1000},
            {"type": "body", "operator": "contains", "target": "ok"}
        ],
        "locations": ["aws:us-east-1", "aws:us-west-2"],
        "options": {
            "tick_every": 60,
            "min_failure_duration": 0,
            "min_location_failed": 1
        },
        "message": "Canary health check failed @pagerduty",
        "tags": ["env:canary", "team:backend"]
    }
)
```

---

## Summary

### Deployment Strategy Decision Matrix

| Scenario | Recommended Strategy | Why |
|----------|---------------------|-----|
| Mission-critical app, instant rollback needed | Blue-Green | Instant switch back |
| High-risk changes, gradual validation | Canary | Minimal blast radius |
| Standard updates, limited resources | Rolling | No extra infra |
| Dev/staging, cost-sensitive | Recreate | Simplest, cheapest |
| Experimentation needed | A/B + Canary | Data-driven decisions |
| Database schema changes | Expand-Contract | Maintains compatibility |

### Best Practices Checklist

- [ ] Health checks configured (liveness + readiness)
- [ ] Graceful shutdown implemented
- [ ] Connection draining configured
- [ ] Backward-compatible migrations
- [ ] Monitoring and alerting in place
- [ ] Rollback procedure documented and tested
- [ ] Load testing performed
- [ ] Smoke tests automated
- [ ] Feature flags for risky changes
- [ ] Database rollback plan
- [ ] Runbook for deployments
- [ ] Post-deployment validation

### Common Pitfalls to Avoid

1. **No health checks**: Sending traffic to unhealthy instances
2. **Abrupt shutdown**: Dropping active connections
3. **Incompatible schema changes**: Breaking old version
4. **No rollback plan**: Stuck with broken deployment
5. **Insufficient monitoring**: Can't detect issues
6. **Testing in production only**: No pre-deployment validation
7. **Manual deployments**: Error-prone, not repeatable
8. **Single deployment strategy**: Use right tool for the job
9. **Ignoring database**: Schema changes are hard to rollback
10. **No feature flags**: Can't disable problematic features

---

**END OF REFERENCE**
