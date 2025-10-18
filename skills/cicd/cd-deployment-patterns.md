---
name: cicd-cd-deployment-patterns
description: Implementing zero-downtime deployment strategies
---



# CD Deployment Patterns

**Scope**: Blue-green deployments, canary releases, rolling updates, rollback strategies, and environment promotion patterns

**Lines**: 395

**Last Updated**: 2025-10-18

**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Use this skill when:
- Implementing zero-downtime deployment strategies
- Setting up blue-green or canary deployments
- Configuring rolling updates for Kubernetes/container orchestration
- Designing rollback mechanisms
- Managing environment promotion (dev → staging → prod)
- Implementing feature flags for gradual rollouts
- Setting up deployment approvals and gates
- Automating database migrations with deployments

Don't use this skill for:
- Basic workflow configuration (see `github-actions-workflows.md`)
- Testing strategies (see `ci-testing-strategy.md`)
- Pipeline optimization (see `ci-optimization.md`)

---

## Core Concepts

### Deployment Strategies

1. **Blue-Green**: Two identical environments, switch traffic atomically
2. **Canary**: Gradual rollout to subset of users
3. **Rolling**: Sequential update of instances
4. **Recreate**: Stop old, start new (downtime acceptable)
5. **Shadow**: Run new version alongside old without serving traffic

### Risk vs Speed Trade-offs

```
Strategy      | Speed | Safety | Complexity | Rollback Speed
──────────────|──────|───────|───────────|───────────────
Recreate      | ★★★★ | ★     | ★          | ★★
Rolling       | ★★★  | ★★    | ★★         | ★★
Blue-Green    | ★★★★ | ★★★★  | ★★★        | ★★★★★
Canary        | ★★   | ★★★★★ | ★★★★       | ★★★★
```

---

## Patterns

### Blue-Green Deployment

```yaml
name: Blue-Green Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production

    steps:
      - uses: actions/checkout@v4

      # Build new version
      - name: Build Docker image
        run: |
          docker build -t myapp:${{ github.sha }} .
          docker tag myapp:${{ github.sha }} myapp:green

      # Deploy to green environment
      - name: Deploy to green
        run: |
          # Deploy to inactive environment
          kubectl apply -f k8s/deployment-green.yaml
          kubectl set image deployment/myapp-green myapp=myapp:${{ github.sha }}
          kubectl rollout status deployment/myapp-green

      # Run smoke tests on green
      - name: Smoke test green environment
        run: |
          ./scripts/smoke-test.sh https://green.myapp.com

      # Switch traffic to green
      - name: Switch traffic
        run: |
          # Update service to point to green
          kubectl patch service myapp -p '{"spec":{"selector":{"version":"green"}}}'

      # Monitor for issues
      - name: Monitor new deployment
        run: |
          sleep 300  # Monitor for 5 minutes
          ./scripts/check-metrics.sh

      # Rollback if needed
      - name: Rollback on failure
        if: failure()
        run: |
          kubectl patch service myapp -p '{"spec":{"selector":{"version":"blue"}}}'
          kubectl delete deployment myapp-green

      # Make green the new blue
      - name: Promote green to blue
        if: success()
        run: |
          kubectl delete deployment myapp-blue
          kubectl apply -f k8s/deployment-blue.yaml
          kubectl set image deployment/myapp-blue myapp=myapp:${{ github.sha }}
```

### Canary Deployment

```yaml
name: Canary Deploy

on:
  push:
    branches: [main]

jobs:
  deploy-canary:
    runs-on: ubuntu-latest
    environment: production

    steps:
      - uses: actions/checkout@v4

      - name: Deploy canary (10%)
        run: |
          # Deploy canary with 10% traffic
          kubectl apply -f k8s/canary-deployment.yaml
          kubectl set image deployment/myapp-canary myapp=myapp:${{ github.sha }}

          # Configure traffic split
          kubectl apply -f - <<EOF
          apiVersion: networking.istio.io/v1beta1
          kind: VirtualService
          metadata:
            name: myapp
          spec:
            hosts:
            - myapp.com
            http:
            - match:
              - headers:
                  canary:
                    exact: "true"
              route:
              - destination:
                  host: myapp-canary
            - route:
              - destination:
                  host: myapp-stable
                weight: 90
              - destination:
                  host: myapp-canary
                weight: 10
          EOF

      - name: Monitor canary metrics
        run: |
          ./scripts/monitor-canary.sh --duration=600 --threshold=5

      - name: Gradually increase traffic
        if: success()
        run: |
          # 25%
          ./scripts/adjust-traffic.sh --canary=25 --stable=75
          sleep 300

          # 50%
          ./scripts/adjust-traffic.sh --canary=50 --stable=50
          sleep 300

          # 100%
          ./scripts/adjust-traffic.sh --canary=100 --stable=0

      - name: Promote canary to stable
        if: success()
        run: |
          kubectl set image deployment/myapp-stable myapp=myapp:${{ github.sha }}
          kubectl delete deployment myapp-canary

      - name: Rollback canary
        if: failure()
        run: |
          kubectl delete deployment myapp-canary
          ./scripts/alert-slack.sh "Canary rollback triggered"
```

### Rolling Deployment (Kubernetes)

```yaml
name: Rolling Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production

    steps:
      - uses: actions/checkout@v4

      - name: Update Kubernetes deployment
        run: |
          kubectl set image deployment/myapp \
            myapp=myapp:${{ github.sha }} \
            --record

          # Configure rolling update strategy
          kubectl patch deployment myapp -p '{
            "spec": {
              "strategy": {
                "type": "RollingUpdate",
                "rollingUpdate": {
                  "maxSurge": 1,
                  "maxUnavailable": 0
                }
              }
            }
          }'

      - name: Wait for rollout
        run: |
          kubectl rollout status deployment/myapp --timeout=600s

      - name: Verify deployment
        run: |
          # Check pod health
          kubectl get pods -l app=myapp

          # Run health checks
          ./scripts/health-check.sh

      - name: Rollback on failure
        if: failure()
        run: |
          kubectl rollout undo deployment/myapp
          kubectl rollout status deployment/myapp
```

### Environment Promotion Pipeline

```yaml
name: Environment Promotion

on:
  push:
    branches: [main]

jobs:
  deploy-dev:
    runs-on: ubuntu-latest
    environment: development

    steps:
      - uses: actions/checkout@v4
      - name: Deploy to dev
        run: ./scripts/deploy.sh dev

      - name: Run smoke tests
        run: ./scripts/smoke-test.sh https://dev.myapp.com

  deploy-staging:
    needs: deploy-dev
    runs-on: ubuntu-latest
    environment: staging

    steps:
      - uses: actions/checkout@v4
      - name: Deploy to staging
        run: ./scripts/deploy.sh staging

      - name: Run integration tests
        run: npm run test:integration

      - name: Run E2E tests
        run: npm run test:e2e

  deploy-prod:
    needs: deploy-staging
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://myapp.com

    steps:
      - uses: actions/checkout@v4

      # Manual approval via environment protection rules
      - name: Deploy to production
        run: ./scripts/deploy.sh production

      - name: Verify deployment
        run: ./scripts/verify-prod.sh

      - name: Notify team
        if: always()
        run: |
          ./scripts/notify-slack.sh \
            "Production deployment: ${{ job.status }}" \
            "Version: ${{ github.sha }}"
```

### Database Migration with Deployment

```yaml
name: Deploy with Migrations

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production

    steps:
      - uses: actions/checkout@v4

      # Backup database before migration
      - name: Backup database
        run: |
          ./scripts/backup-db.sh production
          echo "BACKUP_ID=$(date +%s)" >> $GITHUB_ENV

      # Run forward migrations
      - name: Run migrations
        run: |
          # Test migrations on copy first
          ./scripts/test-migration.sh

          # Apply to production
          npm run migrate:up
        env:
          DATABASE_URL: ${{ secrets.PROD_DATABASE_URL }}

      # Deploy application
      - name: Deploy application
        run: |
          kubectl set image deployment/myapp myapp=myapp:${{ github.sha }}
          kubectl rollout status deployment/myapp

      # Verify deployment
      - name: Verify deployment
        run: ./scripts/health-check.sh

      # Rollback on failure
      - name: Rollback deployment and database
        if: failure()
        run: |
          # Rollback application
          kubectl rollout undo deployment/myapp

          # Rollback database
          npm run migrate:down
          ./scripts/restore-db.sh production ${{ env.BACKUP_ID }}
```

### Feature Flag Deployment

```yaml
name: Feature Flag Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production

    steps:
      - uses: actions/checkout@v4

      # Deploy with feature disabled
      - name: Deploy with feature flag off
        run: |
          kubectl set image deployment/myapp myapp=myapp:${{ github.sha }}
          kubectl rollout status deployment/myapp

      # Enable feature for internal users (0%)
      - name: Enable for internal
        run: |
          curl -X PATCH https://api.launchdarkly.com/api/v2/flags/default/new-feature \
            -H "Authorization: ${{ secrets.LAUNCHDARKLY_TOKEN }}" \
            -d '{"instructions": [{"kind": "updateTargets", "values": {"targets": ["internal"]}}]}'

      # Gradual rollout
      - name: Gradual rollout
        run: |
          # 5%
          ./scripts/update-flag.sh new-feature --percentage=5
          sleep 600

          # 25%
          ./scripts/update-flag.sh new-feature --percentage=25
          sleep 600

          # 50%
          ./scripts/update-flag.sh new-feature --percentage=50
          sleep 600

          # 100%
          ./scripts/update-flag.sh new-feature --percentage=100

      - name: Monitor metrics
        run: |
          ./scripts/check-error-rate.sh --flag=new-feature --threshold=1.0

      - name: Rollback feature
        if: failure()
        run: |
          ./scripts/update-flag.sh new-feature --percentage=0
```

### Multi-Region Deployment

```yaml
name: Multi-Region Deploy

on:
  push:
    branches: [main]

jobs:
  deploy-primary:
    runs-on: ubuntu-latest
    environment: production-us-east

    steps:
      - uses: actions/checkout@v4

      - name: Deploy to us-east-1
        run: |
          aws eks update-kubeconfig --region us-east-1 --name prod-cluster
          kubectl set image deployment/myapp myapp=myapp:${{ github.sha }}
          kubectl rollout status deployment/myapp

      - name: Verify primary region
        run: ./scripts/health-check.sh us-east-1

  deploy-secondary:
    needs: deploy-primary
    runs-on: ubuntu-latest
    strategy:
      matrix:
        region: [us-west-2, eu-west-1, ap-southeast-1]

    steps:
      - uses: actions/checkout@v4

      - name: Deploy to ${{ matrix.region }}
        run: |
          aws eks update-kubeconfig --region ${{ matrix.region }} --name prod-cluster
          kubectl set image deployment/myapp myapp=myapp:${{ github.sha }}
          kubectl rollout status deployment/myapp

      - name: Verify region
        run: ./scripts/health-check.sh ${{ matrix.region }}

      - name: Update global load balancer
        run: |
          aws route53 change-resource-record-sets \
            --hosted-zone-id ${{ secrets.HOSTED_ZONE_ID }} \
            --change-batch file://dns-update-${{ matrix.region }}.json
```

### Deployment with Health Checks

```yaml
name: Deploy with Health Checks

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production

    steps:
      - uses: actions/checkout@v4

      - name: Deploy application
        run: |
          kubectl set image deployment/myapp myapp=myapp:${{ github.sha }}

      - name: Wait for pods to be ready
        run: |
          kubectl rollout status deployment/myapp --timeout=600s

      - name: Health check - HTTP endpoints
        run: |
          for i in {1..30}; do
            if curl -f https://myapp.com/health; then
              echo "Health check passed"
              break
            fi
            echo "Attempt $i failed, retrying..."
            sleep 10
          done

      - name: Health check - Database connectivity
        run: |
          kubectl exec deployment/myapp -- npm run db:ping

      - name: Health check - Dependencies
        run: |
          ./scripts/check-dependencies.sh \
            --redis \
            --postgres \
            --s3

      - name: Monitor error rates
        run: |
          ./scripts/monitor-errors.sh --duration=300 --threshold=0.5

      - name: Automated rollback
        if: failure()
        run: |
          echo "Health checks failed, rolling back"
          kubectl rollout undo deployment/myapp
          kubectl rollout status deployment/myapp

          # Notify team
          ./scripts/notify-slack.sh \
            "Deployment rolled back due to health check failure" \
            "SHA: ${{ github.sha }}"
```

---

## Quick Reference

### Deployment Strategy Selection

```yaml
Use Case                          → Strategy
─────────────────────────────────────────────────
Zero downtime required           → Blue-Green or Rolling
High-risk changes                → Canary
Limited resources                → Rolling
Fast rollback critical           → Blue-Green
Gradual validation needed        → Canary
Simple app, downtime OK          → Recreate
A/B testing                      → Feature Flags + Canary
```

### Kubernetes Rolling Update Config

```yaml
spec:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1        # Extra pods during rollout
      maxUnavailable: 0  # Minimum availability
  minReadySeconds: 30    # Wait before marking ready
  progressDeadlineSeconds: 600  # Timeout
```

### Rollback Commands

```bash
# Kubernetes
kubectl rollout undo deployment/myapp
kubectl rollout undo deployment/myapp --to-revision=2

# Docker
docker service update --rollback myapp

# AWS ECS
aws ecs update-service --cluster prod --service myapp --force-new-deployment

# Vercel
vercel rollback
```

---

## Anti-Patterns

### ❌ No Automated Rollback

```yaml
# WRONG: Manual intervention required
- name: Deploy
  run: ./deploy.sh
# [If it fails, ops team manually fixes]
```

```yaml
# CORRECT: Automated rollback
- name: Deploy
  run: ./deploy.sh

- name: Health check
  run: ./health-check.sh

- name: Rollback on failure
  if: failure()
  run: ./rollback.sh
```

### ❌ Deploying Without Health Checks

```yaml
# WRONG: Assume deployment succeeded
- run: kubectl apply -f deployment.yaml
```

```yaml
# CORRECT: Verify deployment health
- run: kubectl apply -f deployment.yaml
- run: kubectl rollout status deployment/myapp
- run: ./smoke-test.sh
```

### ❌ No Database Backup Before Migration

```yaml
# WRONG: Risky migration
- run: npm run migrate:up
- run: ./deploy.sh
```

```yaml
# CORRECT: Backup first
- run: ./backup-db.sh
- run: npm run migrate:up
- run: ./deploy.sh
- if: failure()
  run: ./restore-db.sh
```

### ❌ Deploying to All Regions Simultaneously

```yaml
# WRONG: All regions at once
jobs:
  deploy:
    strategy:
      matrix:
        region: [us, eu, asia]
    steps: [deploy]
```

```yaml
# CORRECT: Staged rollout
jobs:
  deploy-primary:
    steps: [deploy to us-east-1]
  deploy-secondary:
    needs: deploy-primary
    strategy:
      matrix:
        region: [us-west-2, eu-west-1]
```

### ❌ No Monitoring Period After Deployment

```yaml
# WRONG: Deploy and forget
- run: ./deploy.sh
```

```yaml
# CORRECT: Monitor post-deployment
- run: ./deploy.sh
- run: sleep 300  # 5 minute soak period
- run: ./check-metrics.sh
```

### ❌ Skipping Canary for High-Risk Changes

```yaml
# WRONG: Direct to production
on:
  push:
    branches: [main]
jobs:
  deploy-prod:
    steps: [deploy 100%]
```

```yaml
# CORRECT: Canary for risky changes
jobs:
  deploy-canary:
    if: contains(github.event.head_commit.message, '[high-risk]')
    steps: [deploy 10%, monitor, gradual rollout]
```

---

## Related Skills

- `github-actions-workflows.md` - Workflow configuration basics
- `ci-testing-strategy.md` - Pre-deployment testing
- `ci-optimization.md` - Deployment speed optimization
- `ci-security.md` - Secure deployment practices

---

**Last Updated**: 2025-10-18

**Format Version**: 1.0 (Atomic)
