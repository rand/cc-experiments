---
name: engineering-continuous-integration
description: CI/CD pipeline design, automated testing, deployment strategies, and continuous delivery best practices
---

# Continuous Integration & Delivery

**Scope**: Comprehensive guide to CI/CD pipelines, automated testing, deployment strategies, and delivery practices
**Lines**: ~350
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Setting up CI/CD for a project
- Automating build and test processes
- Implementing deployment pipelines
- Establishing quality gates
- Reducing manual deployment work
- Improving deployment confidence
- Shortening feedback loops
- Scaling engineering team

## Core Concepts

### Concept 1: Continuous Integration (CI)

**Definition**: Automatically build and test code on every commit

**Key Principles**:
1. Commit code frequently (multiple times per day)
2. Every commit triggers automated build
3. Automated tests run on every build
4. Fix broken builds immediately
5. Keep build fast (< 10 minutes)

**Benefits**:
- Catch bugs early
- Reduce integration problems
- Deploy faster
- Increase confidence

---

### Concept 2: Continuous Delivery (CD)

**Definition**: Every change can be deployed to production automatically

```
Continuous Integration
  ↓
Continuous Delivery (can deploy any time)
  ↓
Continuous Deployment (auto-deploy to production)
```

**Deployment Strategies**:
- **Blue-Green**: Two environments, switch traffic
- **Canary**: Gradual rollout to subset of users
- **Rolling**: Update instances one at a time
- **Feature Flags**: Deploy code, enable features later

---

### Concept 3: Pipeline Stages

**Typical CI/CD Pipeline**:
```
Commit → Build → Test → Deploy → Monitor
   ↓       ↓       ↓       ↓        ↓
 Code   Compile  Unit   Staging  Metrics
        Package  Lint   Prod     Alerts
                 E2E
```

---

## Patterns

### Pattern 1: GitHub Actions Pipeline

**Basic CI Pipeline**:
```yaml
# .github/workflows/ci.yml
name: CI Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Lint with flake8
        run: |
          flake8 src/ --max-complexity=10

      - name: Type check with mypy
        run: |
          mypy src/

      - name: Run tests
        run: |
          pytest tests/ --cov=src --cov-fail-under=80

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

### Pattern 2: Multi-Stage Pipeline

**Comprehensive Pipeline**:
```yaml
# .github/workflows/pipeline.yml
name: Full Pipeline

on:
  push:
    branches: [main]

jobs:
  # Stage 1: Build
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build Docker image
        run: docker build -t myapp:${{ github.sha }} .
      - name: Push to registry
        run: docker push myapp:${{ github.sha }}

  # Stage 2: Test
  test:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Unit tests
        run: npm test
      - name: Integration tests
        run: npm run test:integration
      - name: E2E tests
        run: npm run test:e2e

  # Stage 3: Security scan
  security:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Snyk scan
        uses: snyk/actions/node@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}

  # Stage 4: Deploy to staging
  deploy-staging:
    needs: [test, security]
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - name: Deploy to staging
        run: |
          kubectl set image deployment/myapp \
            myapp=myapp:${{ github.sha }} \
            -n staging

  # Stage 5: Deploy to production (manual approval)
  deploy-production:
    needs: deploy-staging
    runs-on: ubuntu-latest
    environment: production
    steps:
      - name: Deploy to production
        run: |
          kubectl set image deployment/myapp \
            myapp=myapp:${{ github.sha }} \
            -n production
```

---

### Pattern 3: Quality Gates

**Fail Build on Quality Issues**:
```yaml
- name: Check code coverage
  run: |
    pytest --cov=src --cov-fail-under=80
    # Fails if coverage < 80%

- name: Check code complexity
  run: |
    radon cc src/ -a -nb --total-average-threshold=B
    # Fails if complexity > B grade

- name: Check for vulnerabilities
  run: |
    safety check
    # Fails if known vulnerabilities found

- name: Check for code duplication
  run: |
    jscpd src/ --threshold 5
    # Fails if > 5% duplication

- name: Check for linting errors
  run: |
    eslint src/ --max-warnings=0
    # Fails on any warnings
```

---

### Pattern 4: Blue-Green Deployment

```yaml
# Blue-Green deployment strategy
- name: Deploy to green environment
  run: |
    # Deploy new version to "green" environment
    kubectl apply -f k8s/green/ -n production

- name: Run smoke tests on green
  run: |
    curl https://green.myapp.com/health
    npm run test:smoke -- --url=https://green.myapp.com

- name: Switch traffic to green
  run: |
    # Switch load balancer to green
    kubectl patch service myapp \
      -p '{"spec":{"selector":{"version":"green"}}}' \
      -n production

- name: Monitor green for 10 minutes
  run: |
    # Monitor error rates, latency
    sleep 600

- name: Destroy blue environment
  run: |
    kubectl delete -f k8s/blue/ -n production
```

---

### Pattern 5: Canary Deployment

```yaml
# Gradual rollout to production
- name: Deploy canary (5% traffic)
  run: |
    kubectl set image deployment/myapp-canary \
      myapp=myapp:${{ github.sha }}
    kubectl scale deployment/myapp-canary --replicas=1

- name: Monitor canary for 15 minutes
  run: |
    # Check error rates, latency
    if [ $ERROR_RATE -gt $THRESHOLD ]; then
      echo "Canary failed, rolling back"
      exit 1
    fi

- name: Increase to 25% traffic
  run: |
    kubectl scale deployment/myapp-canary --replicas=5

- name: Monitor for 15 minutes
  run: |
    # Check metrics again
    sleep 900

- name: Full rollout (100% traffic)
  run: |
    kubectl set image deployment/myapp \
      myapp=myapp:${{ github.sha }}
    kubectl delete deployment/myapp-canary
```

---

### Pattern 6: Feature Flags

**Deploy code without enabling features**:
```python
# Deploy with feature disabled
from feature_flags import is_enabled

@app.route("/api/users")
def get_users():
    if is_enabled("new_user_endpoint"):
        return new_get_users()  # New implementation
    else:
        return old_get_users()  # Old implementation

# Configuration
# feature_flags.yaml
features:
  new_user_endpoint:
    enabled: false  # Deploy code, don't enable yet
    rollout_percentage: 0

# Gradual rollout
# 1. Deploy code with flag disabled
# 2. Enable for 5% of users
# 3. Monitor metrics
# 4. Increase to 25%, 50%, 100%
# 5. Remove flag after full rollout
```

---

### Pattern 7: Automated Rollback

```yaml
- name: Deploy new version
  id: deploy
  run: |
    kubectl set image deployment/myapp myapp:${{ github.sha }}
    kubectl rollout status deployment/myapp

- name: Monitor deployment
  id: monitor
  run: |
    # Check error rates for 5 minutes
    ERROR_RATE=$(check_error_rate)
    if [ $ERROR_RATE -gt 5 ]; then
      echo "Error rate too high: $ERROR_RATE%"
      exit 1
    fi

- name: Rollback on failure
  if: failure()
  run: |
    echo "Deployment failed, rolling back"
    kubectl rollout undo deployment/myapp
    # Send alert to team
    curl -X POST $SLACK_WEBHOOK \
      -d '{"text":"Deployment rolled back due to high error rate"}'
```

---

## Best Practices

### CI/CD Guidelines

**Do's**:
- Keep builds fast (< 10 min)
- Run tests on every commit
- Fail fast (quick feedback)
- Automate everything
- Use quality gates
- Monitor deployments
- Have rollback plan
- Test deployment process

**Don'ts**:
- Don't commit to broken build
- Don't skip tests to save time
- Don't deploy manually
- Don't ignore failing tests
- Don't deploy on Friday (unless CD)
- Don't skip staging environment
- Don't deploy without monitoring

---

### Build Optimization

**Slow Build** (15 minutes):
```yaml
- name: Install dependencies
  run: npm install  # Downloads every time

- name: Run all tests
  run: npm test     # Runs everything
```

**Fast Build** (5 minutes):
```yaml
- name: Cache dependencies
  uses: actions/cache@v3
  with:
    path: ~/.npm
    key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}

- name: Install dependencies
  run: npm ci  # Faster than npm install

- name: Run unit tests (fast)
  run: npm run test:unit

- name: Run integration tests (parallel)
  run: npm run test:integration -- --parallel

# E2E tests run only on main branch
- name: Run E2E tests
  if: github.ref == 'refs/heads/main'
  run: npm run test:e2e
```

---

## Anti-Patterns

### Common CI/CD Mistakes

```
❌ Manual Deployment Steps
→ "SSH into server and run deploy.sh"
✅ Fully automated deployment

❌ No Tests in CI
→ "We'll test it manually"
✅ Automated tests on every commit

❌ Long-Running Builds
→ 30+ minute builds
✅ Optimize to < 10 minutes

❌ Ignoring Broken Builds
→ "I'll fix it later"
✅ Fix immediately or revert

❌ Deploying Without Monitoring
→ "Hope it works!"
✅ Monitor metrics and auto-rollback

❌ No Staging Environment
→ Test in production
✅ Deploy to staging first

❌ Big Bang Deployments
→ Deploy everything at once
✅ Incremental rollouts (canary)
```

---

## Platform Examples

### GitHub Actions
```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: npm test
```

### GitLab CI
```yaml
# .gitlab-ci.yml
stages:
  - test
  - deploy

test:
  stage: test
  script:
    - npm test

deploy:
  stage: deploy
  script:
    - kubectl apply -f k8s/
  only:
    - main
```

### CircleCI
```yaml
# .circleci/config.yml
version: 2.1
jobs:
  test:
    docker:
      - image: node:18
    steps:
      - checkout
      - run: npm test

workflows:
  test-deploy:
    jobs:
      - test
```

### Jenkins
```groovy
pipeline {
    agent any
    stages {
        stage('Test') {
            steps {
                sh 'npm test'
            }
        }
        stage('Deploy') {
            steps {
                sh 'kubectl apply -f k8s/'
            }
        }
    }
}
```

---

## Monitoring & Observability

**Key Metrics**:
```
Deployment Frequency: How often we deploy
Lead Time: Time from commit to production
Change Failure Rate: % of deployments that fail
Mean Time to Recovery: Time to fix production issues

DORA Metrics Targets:
- Elite: Multiple deploys/day, < 1 hour lead time
- High: Weekly to daily deploys, < 1 day lead time
- Medium: Monthly to weekly, 1 week lead time
- Low: < Monthly, > 6 months lead time
```

**Health Checks**:
```python
@app.route("/health")
def health():
    return {
        "status": "healthy",
        "version": os.getenv("VERSION"),
        "database": check_database(),
        "cache": check_cache(),
    }

@app.route("/ready")
def readiness():
    # Check if app is ready to serve traffic
    if not is_database_ready():
        return {"status": "not ready"}, 503
    return {"status": "ready"}
```

---

## Related Skills

- **engineering-test-driven-development**: TDD enables fast CI
- **engineering-code-review**: Automated checks in CI
- **engineering-code-quality**: Quality gates in pipeline
- **engineering-technical-debt**: CI prevents debt accumulation

---

## References

- [Continuous Delivery by Jez Humble](https://www.amazon.com/Continuous-Delivery-Deployment-Automation-Addison-Wesley/dp/0321601912)
- [The Phoenix Project by Gene Kim](https://www.amazon.com/Phoenix-Project-DevOps-Helping-Business/dp/0988262592)
- [Accelerate by Nicole Forsgren](https://www.amazon.com/Accelerate-Software-Performing-Technology-Organizations/dp/1942788339)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
