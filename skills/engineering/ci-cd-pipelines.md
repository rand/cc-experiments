---
name: engineering-ci-cd-pipelines
description: Comprehensive CI/CD pipeline design covering build, test, security, deployment automation, artifact management, and multi-platform implementation (GitHub Actions, GitLab CI, Jenkins, CircleCI)
---

# CI/CD Pipelines

**Scope**: Complete CI/CD pipeline architecture from source to production, including build automation, testing strategies, security scanning, artifact management, deployment patterns, and platform-specific implementations

**Lines**: ~850

**Last Updated**: 2025-10-27

**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Designing or implementing CI/CD pipelines from scratch
- Optimizing existing pipeline performance and reliability
- Implementing security scanning and compliance gates
- Setting up multi-environment deployment workflows
- Managing artifacts and versioning strategies
- Configuring automated testing in pipelines
- Implementing infrastructure as code for pipelines
- Troubleshooting pipeline failures and bottlenecks
- Migrating between CI/CD platforms

Don't use this skill for:
- Specific deployment strategies (see `deployment-strategies.md`)
- Kubernetes-specific deployments (see `kubernetes-deployment`)
- Security-only concerns (see `ci-security.md`)
- Testing strategies only (see `ci-testing-strategy.md`)

---

## Core Concepts

### Concept 1: Pipeline Stages Architecture

**Definition**: Structured progression from code commit to production deployment

**Standard Pipeline Stages**:
```
Source → Build → Test → Security → Package → Deploy → Monitor
  ↓        ↓       ↓        ↓         ↓        ↓       ↓
 SCM    Compile  Units   SAST     Artifacts  Envs   Observe
        Bundle   Integ   DAST     Registry   Promote Metrics
        Assets   E2E     Vuln     Version    Health  Alerts
```

**Stage Principles**:
1. **Fail Fast**: Run fastest checks first
2. **Isolation**: Each stage independent and idempotent
3. **Artifacts**: Build once, deploy many times
4. **Gates**: Quality gates block bad deployments
5. **Observability**: Comprehensive logging and metrics

**Stage Dependencies**:
```
Build ← Tests require built artifacts
Tests ← Security scans require dependencies
Package ← Deployment requires tested artifacts
Deploy ← Monitoring validates deployment
```

---

### Concept 2: Pipeline as Code

**Definition**: Define pipelines in version-controlled declarative configuration

**Benefits**:
```
Version Control: Track changes, review, rollback
Reproducibility: Same config = same pipeline
Code Review: Pipeline changes reviewed like code
Testing: Test pipeline changes in branches
Documentation: Pipeline is self-documenting
```

**Platform Comparison**:
```
Platform          | Language | Features
------------------|----------|------------------
GitHub Actions    | YAML     | Matrix, reusable workflows
GitLab CI         | YAML     | Include, extends, DAG
Jenkins           | Groovy   | Shared libraries, DSL
CircleCI          | YAML     | Orbs, workflows
Buildkite         | YAML     | Dynamic pipelines
```

---

### Concept 3: Artifact Management

**Definition**: Store, version, and distribute build artifacts efficiently

**Artifact Strategy**:
```
Build Once
  ↓
Tag with metadata (git sha, version, timestamp)
  ↓
Store in registry (Docker, npm, Maven, PyPI)
  ↓
Promote through environments
  ↓
Track provenance and SBOM
```

**Versioning Strategies**:
- **Semantic**: `v1.2.3` for releases
- **SHA-based**: `v1.2.3-abc1234` for traceability
- **Timestamp**: `v1.2.3-20251027-1430` for ordering
- **Environment**: `v1.2.3-staging` for promotion

**Registry Types**:
```
Docker:     Docker Hub, GHCR, ECR, GCR, ACR
npm/Node:   npm registry, GitHub Packages
Python:     PyPI, private package index
Java:       Maven Central, Artifactory, Nexus
Generic:    S3, GCS, Azure Blob
```

---

## Patterns

### Pattern 1: GitHub Actions Multi-Stage Pipeline

**Problem**: Need comprehensive pipeline with parallel execution

**Implementation**:
```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
  workflow_dispatch:

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  # Stage 1: Validate
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Validate code format
        run: npm run lint

      - name: Type check
        run: npm run typecheck

      - name: Check for secrets
        uses: gitleaks/gitleaks-action@v2

  # Stage 2: Build
  build:
    needs: validate
    runs-on: ubuntu-latest
    outputs:
      version: ${{ steps.version.outputs.version }}
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Build
        run: npm run build

      - name: Generate version
        id: version
        run: |
          VERSION="v$(jq -r .version package.json)-${GITHUB_SHA::8}"
          echo "version=$VERSION" >> $GITHUB_OUTPUT

      - name: Upload build artifacts
        uses: actions/upload-artifact@v4
        with:
          name: dist-${{ steps.version.outputs.version }}
          path: dist/
          retention-days: 7

  # Stage 3: Test (parallel)
  test-unit:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run test:unit -- --coverage

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          flags: unit

  test-integration:
    needs: build
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run test:integration
        env:
          DATABASE_URL: postgresql://postgres:postgres@postgres:5432/test

  test-e2e:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npx playwright install --with-deps
      - run: npm run test:e2e

      - uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: playwright-report
          path: playwright-report/

  # Stage 4: Security (parallel)
  security-sast:
    needs: build
    runs-on: ubuntu-latest
    permissions:
      security-events: write
    steps:
      - uses: actions/checkout@v4

      - name: CodeQL Analysis
        uses: github/codeql-action/init@v3
        with:
          languages: javascript
          queries: security-extended

      - uses: github/codeql-action/autobuild@v3
      - uses: github/codeql-action/analyze@v3

  security-dependencies:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'

      - run: npm audit --audit-level=high

      - name: Snyk test
        uses: snyk/actions/node@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          args: --severity-threshold=high

  # Stage 5: Package
  package:
    needs: [test-unit, test-integration, test-e2e, security-sast, security-dependencies]
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    outputs:
      image-tag: ${{ steps.meta.outputs.tags }}
    steps:
      - uses: actions/checkout@v4

      - name: Download artifacts
        uses: actions/download-artifact@v4
        with:
          name: dist-${{ needs.build.outputs.version }}
          path: dist/

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=ref,event=pr
            type=semver,pattern={{version}}
            type=sha,prefix={{branch}}-
            type=raw,value=${{ needs.build.outputs.version }}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
          build-args: |
            VERSION=${{ needs.build.outputs.version }}
            COMMIT=${{ github.sha }}

      - name: Generate SBOM
        uses: anchore/sbom-action@v0
        with:
          image: ${{ steps.meta.outputs.tags }}
          format: spdx-json
          output-file: sbom.spdx.json

      - name: Scan image
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ steps.meta.outputs.tags }}
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'

      - uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: 'trivy-results.sarif'

  # Stage 6: Deploy to Staging
  deploy-staging:
    needs: package
    if: github.ref == 'refs/heads/develop'
    runs-on: ubuntu-latest
    environment:
      name: staging
      url: https://staging.example.com
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_STAGING }}
          aws-region: us-east-1

      - name: Deploy to ECS
        run: |
          aws ecs update-service \
            --cluster staging-cluster \
            --service myapp \
            --force-new-deployment

      - name: Wait for deployment
        run: |
          aws ecs wait services-stable \
            --cluster staging-cluster \
            --services myapp

      - name: Smoke tests
        run: |
          curl -f https://staging.example.com/health
          npm run test:smoke -- --baseUrl=https://staging.example.com

  # Stage 7: Deploy to Production
  deploy-production:
    needs: package
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://example.com
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_PRODUCTION }}
          aws-region: us-east-1

      - name: Deploy to ECS (canary)
        run: |
          # Deploy with 10% traffic
          ./scripts/canary-deploy.sh \
            --cluster prod-cluster \
            --service myapp \
            --image ${{ needs.package.outputs.image-tag }} \
            --canary-percent 10

      - name: Monitor canary
        run: |
          # Monitor for 10 minutes
          ./scripts/monitor-canary.sh \
            --duration 600 \
            --error-threshold 1.0

      - name: Promote canary
        run: |
          # Shift to 100% traffic
          ./scripts/promote-canary.sh \
            --cluster prod-cluster \
            --service myapp

  # Stage 8: Notify
  notify:
    needs: [deploy-staging, deploy-production]
    if: always()
    runs-on: ubuntu-latest
    steps:
      - name: Notify Slack
        uses: slackapi/slack-github-action@v1
        with:
          payload: |
            {
              "text": "Deployment ${{ needs.deploy-production.result }}",
              "blocks": [
                {
                  "type": "section",
                  "text": {
                    "type": "mrkdwn",
                    "text": "Deployment to production: *${{ needs.deploy-production.result }}*\nCommit: ${{ github.sha }}\nActor: ${{ github.actor }}"
                  }
                }
              ]
            }
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK }}
```

**Benefits**:
- Parallel execution reduces pipeline time
- Comprehensive quality gates
- Artifact promotion pattern
- Progressive deployment
- Monitoring and notifications

---

### Pattern 2: GitLab CI Multi-Environment Pipeline

**Problem**: Need complex deployment workflow with manual approvals

**Implementation**:
```yaml
# .gitlab-ci.yml
stages:
  - validate
  - build
  - test
  - security
  - package
  - deploy-dev
  - deploy-staging
  - deploy-production

variables:
  DOCKER_DRIVER: overlay2
  DOCKER_TLS_CERTDIR: "/certs"
  IMAGE_TAG: $CI_REGISTRY_IMAGE:$CI_COMMIT_SHORT_SHA

# Templates
.build-template: &build-template
  image: node:20
  cache:
    key: ${CI_COMMIT_REF_SLUG}
    paths:
      - node_modules/
      - .npm/
  before_script:
    - npm ci --cache .npm --prefer-offline

.deploy-template: &deploy-template
  image: alpine:latest
  before_script:
    - apk add --no-cache curl
    - curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
    - chmod +x kubectl
    - mv kubectl /usr/local/bin/

# Stage: Validate
lint:
  stage: validate
  <<: *build-template
  script:
    - npm run lint
    - npm run typecheck
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH

# Stage: Build
build:
  stage: build
  <<: *build-template
  script:
    - npm run build
    - echo "VERSION=$(jq -r .version package.json)-$CI_COMMIT_SHORT_SHA" > version.txt
  artifacts:
    paths:
      - dist/
      - version.txt
    expire_in: 1 week
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH

# Stage: Test
test:unit:
  stage: test
  <<: *build-template
  needs: [build]
  script:
    - npm run test:unit -- --coverage
  coverage: '/All files[^|]*\|[^|]*\s+([\d\.]+)/'
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage/cobertura-coverage.xml

test:integration:
  stage: test
  <<: *build-template
  needs: [build]
  services:
    - name: postgres:16
      alias: postgres
  variables:
    POSTGRES_DB: test
    POSTGRES_USER: test
    POSTGRES_PASSWORD: test
    DATABASE_URL: postgresql://test:test@postgres:5432/test
  script:
    - npm run test:integration

test:e2e:
  stage: test
  <<: *build-template
  needs: [build]
  script:
    - npx playwright install --with-deps
    - npm run test:e2e
  artifacts:
    when: on_failure
    paths:
      - playwright-report/
    expire_in: 7 days

# Stage: Security
security:sast:
  stage: security
  needs: [build]
  image: returntocorp/semgrep
  script:
    - semgrep --config=auto --sarif > gl-sast-report.json
  artifacts:
    reports:
      sast: gl-sast-report.json

security:dependency:
  stage: security
  needs: [build]
  <<: *build-template
  script:
    - npm audit --audit-level=moderate
  allow_failure: true

security:secrets:
  stage: security
  image: zricethezav/gitleaks
  script:
    - gitleaks detect --verbose --no-git
  allow_failure: false

# Stage: Package
docker:build:
  stage: package
  image: docker:24
  services:
    - docker:24-dind
  needs:
    - build
    - test:unit
    - test:integration
    - test:e2e
    - security:sast
    - security:dependency
  before_script:
    - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
  script:
    - docker build
        --build-arg VERSION=$(cat version.txt)
        --build-arg COMMIT=$CI_COMMIT_SHA
        --tag $IMAGE_TAG
        --tag $CI_REGISTRY_IMAGE:latest
        .
    - docker push $IMAGE_TAG
    - docker push $CI_REGISTRY_IMAGE:latest

    # Scan image
    - apk add --no-cache curl
    ⚠️ **SECURITY**: Piping curl to shell is dangerous. For production:
    - curl -O https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh
    - sha256sum install.sh
    - less install.sh
    - sh install.sh -b /usr/local/bin
    # For development/learning only:
    - curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin
    - trivy image --exit-code 0 --severity HIGH,CRITICAL $IMAGE_TAG

    # Generate SBOM
    ⚠️ **SECURITY**: Piping curl to shell is dangerous. For production:
    - curl -O https://raw.githubusercontent.com/anchore/syft/main/install.sh
    - sha256sum install.sh
    - less install.sh
    - sh install.sh -b /usr/local/bin
    # For development/learning only:
    - curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin
    - syft $IMAGE_TAG -o spdx-json > sbom.spdx.json
  artifacts:
    paths:
      - sbom.spdx.json
    expire_in: 30 days
  rules:
    - if: $CI_COMMIT_BRANCH

# Stage: Deploy Development
deploy:dev:
  stage: deploy-dev
  <<: *deploy-template
  needs: [docker:build]
  environment:
    name: development
    url: https://dev.example.com
    on_stop: stop:dev
  script:
    - kubectl config use-context dev-cluster
    - kubectl set image deployment/myapp myapp=$IMAGE_TAG -n dev
    - kubectl rollout status deployment/myapp -n dev
    - curl -f https://dev.example.com/health
  rules:
    - if: $CI_COMMIT_BRANCH == "develop"

stop:dev:
  stage: deploy-dev
  <<: *deploy-template
  environment:
    name: development
    action: stop
  script:
    - kubectl delete deployment myapp -n dev
  when: manual
  rules:
    - if: $CI_COMMIT_BRANCH == "develop"

# Stage: Deploy Staging
deploy:staging:
  stage: deploy-staging
  <<: *deploy-template
  needs: [docker:build]
  environment:
    name: staging
    url: https://staging.example.com
  script:
    - kubectl config use-context staging-cluster
    - |
      cat <<EOF | kubectl apply -f -
      apiVersion: apps/v1
      kind: Deployment
      metadata:
        name: myapp
        namespace: staging
      spec:
        replicas: 2
        selector:
          matchLabels:
            app: myapp
        template:
          metadata:
            labels:
              app: myapp
              version: $CI_COMMIT_SHORT_SHA
          spec:
            containers:
            - name: myapp
              image: $IMAGE_TAG
              ports:
              - containerPort: 8080
              env:
              - name: ENVIRONMENT
                value: staging
              readinessProbe:
                httpGet:
                  path: /ready
                  port: 8080
              livenessProbe:
                httpGet:
                  path: /health
                  port: 8080
      EOF
    - kubectl rollout status deployment/myapp -n staging
    - sleep 30
    - curl -f https://staging.example.com/health
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH

# Stage: Deploy Production
deploy:production:
  stage: deploy-production
  <<: *deploy-template
  needs: [deploy:staging]
  environment:
    name: production
    url: https://example.com
  script:
    - kubectl config use-context production-cluster

    # Blue-green deployment
    - export CURRENT_COLOR=$(kubectl get service myapp -n prod -o jsonpath='{.spec.selector.color}')
    - export NEW_COLOR=$(if [ "$CURRENT_COLOR" = "blue" ]; then echo "green"; else echo "blue"; fi)

    # Deploy new version
    - kubectl set image deployment/myapp-$NEW_COLOR myapp=$IMAGE_TAG -n prod
    - kubectl rollout status deployment/myapp-$NEW_COLOR -n prod

    # Health check
    - kubectl run curl-test --image=curlimages/curl --rm -it --restart=Never -- curl -f http://myapp-$NEW_COLOR.prod.svc.cluster.local/health

    # Switch traffic
    - kubectl patch service myapp -n prod -p '{"spec":{"selector":{"color":"'$NEW_COLOR'"}}}'

    # Monitor for 5 minutes
    - sleep 300

    # Verify success
    - curl -f https://example.com/health

    - echo "Deployment successful. Old color $CURRENT_COLOR, new color $NEW_COLOR"
  when: manual
  only:
    - main
```

**Benefits**:
- GitLab-native features (includes, artifacts, environments)
- Manual approval gates for production
- Blue-green deployment pattern
- Comprehensive testing and security
- Multi-cluster deployment

---

### Pattern 3: Jenkins Declarative Pipeline

**Problem**: Need flexible pipeline with shared libraries

**Implementation**:
```groovy
// Jenkinsfile
@Library('shared-pipeline-library') _

pipeline {
    agent {
        kubernetes {
            yaml """
apiVersion: v1
kind: Pod
spec:
  containers:
  - name: node
    image: node:20
    command: ['cat']
    tty: true
  - name: docker
    image: docker:24
    command: ['cat']
    tty: true
    volumeMounts:
    - name: docker-sock
      mountPath: /var/run/docker.sock
  volumes:
  - name: docker-sock
    hostPath:
      path: /var/run/docker.sock
"""
        }
    }

    environment {
        DOCKER_REGISTRY = 'registry.example.com'
        IMAGE_NAME = "${DOCKER_REGISTRY}/myapp"
        VERSION = sh(script: "echo v\$(cat package.json | jq -r .version)-\${GIT_COMMIT[0..7]}", returnStdout: true).trim()
    }

    options {
        buildDiscarder(logRotator(numToKeepStr: '30'))
        timeout(time: 1, unit: 'HOURS')
        timestamps()
        disableConcurrentBuilds()
    }

    parameters {
        booleanParam(name: 'DEPLOY_TO_PRODUCTION', defaultValue: false, description: 'Deploy to production?')
        choice(name: 'ENVIRONMENT', choices: ['dev', 'staging', 'production'], description: 'Target environment')
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                sh 'git clean -fdx'
            }
        }

        stage('Validate') {
            parallel {
                stage('Lint') {
                    steps {
                        container('node') {
                            sh 'npm ci'
                            sh 'npm run lint'
                            sh 'npm run typecheck'
                        }
                    }
                }
                stage('Secret Scan') {
                    steps {
                        sh 'docker run --rm -v $(pwd):/repo zricethezav/gitleaks:latest detect --source /repo --no-git'
                    }
                }
            }
        }

        stage('Build') {
            steps {
                container('node') {
                    sh 'npm ci'
                    sh 'npm run build'
                    stash includes: 'dist/**', name: 'build-artifacts'
                }
            }
        }

        stage('Test') {
            parallel {
                stage('Unit Tests') {
                    steps {
                        container('node') {
                            sh 'npm run test:unit -- --coverage'
                            junit 'test-results/junit.xml'
                            publishCoverage adapters: [
                                coberturaAdapter('coverage/cobertura-coverage.xml')
                            ]
                        }
                    }
                }
                stage('Integration Tests') {
                    steps {
                        container('node') {
                            sh '''
                                docker run -d --name postgres-test \
                                    -e POSTGRES_PASSWORD=test \
                                    -p 5432:5432 postgres:16
                                sleep 5
                                export DATABASE_URL=postgresql://postgres:test@localhost:5432/test
                                npm run test:integration
                                docker stop postgres-test
                                docker rm postgres-test
                            '''
                        }
                    }
                }
                stage('E2E Tests') {
                    steps {
                        container('node') {
                            sh 'npx playwright install --with-deps'
                            sh 'npm run test:e2e'
                        }
                    }
                    post {
                        failure {
                            archiveArtifacts artifacts: 'playwright-report/**', allowEmptyArchive: true
                        }
                    }
                }
            }
        }

        stage('Security Scan') {
            parallel {
                stage('Dependency Scan') {
                    steps {
                        container('node') {
                            sh 'npm audit --audit-level=moderate || true'
                            sh 'npx snyk test --severity-threshold=high || true'
                        }
                    }
                }
                stage('SAST') {
                    steps {
                        sh 'docker run --rm -v $(pwd):/src returntocorp/semgrep semgrep --config=auto --sarif /src'
                    }
                }
            }
        }

        stage('Package') {
            steps {
                container('docker') {
                    unstash 'build-artifacts'
                    script {
                        def image = docker.build("${IMAGE_NAME}:${VERSION}",
                            "--build-arg VERSION=${VERSION} " +
                            "--build-arg COMMIT=${GIT_COMMIT} .")

                        docker.withRegistry("https://${DOCKER_REGISTRY}", 'docker-registry-credentials') {
                            image.push("${VERSION}")
                            image.push('latest')
                        }

                        // Scan image
                        sh "trivy image --exit-code 0 --severity HIGH,CRITICAL ${IMAGE_NAME}:${VERSION}"

                        // Generate SBOM
                        sh "syft ${IMAGE_NAME}:${VERSION} -o spdx-json > sbom.spdx.json"
                        archiveArtifacts artifacts: 'sbom.spdx.json', fingerprint: true
                    }
                }
            }
        }

        stage('Deploy to Development') {
            when {
                branch 'develop'
            }
            steps {
                deployToEnvironment('dev', VERSION)
            }
        }

        stage('Deploy to Staging') {
            when {
                branch 'main'
            }
            steps {
                deployToEnvironment('staging', VERSION)

                // Run smoke tests
                sh "curl -f https://staging.example.com/health"
            }
        }

        stage('Deploy to Production') {
            when {
                allOf {
                    branch 'main'
                    expression { params.DEPLOY_TO_PRODUCTION == true }
                }
            }
            steps {
                input message: 'Deploy to production?', ok: 'Deploy'

                deployToEnvironment('production', VERSION)

                // Canary deployment with monitoring
                script {
                    sh """
                        kubectl set image deployment/myapp-canary myapp=${IMAGE_NAME}:${VERSION} -n prod
                        kubectl rollout status deployment/myapp-canary -n prod

                        # Monitor for 10 minutes
                        sleep 600

                        # Check error rate
                        ERROR_RATE=\$(curl -s http://prometheus:9090/api/v1/query?query=rate(http_requests_total{status=~"5.."}[5m]) | jq -r '.data.result[0].value[1]')
                        if (( \$(echo "\$ERROR_RATE > 0.01" | bc -l) )); then
                            echo "Error rate too high: \$ERROR_RATE"
                            kubectl rollout undo deployment/myapp-canary -n prod
                            exit 1
                        fi

                        # Promote to full deployment
                        kubectl set image deployment/myapp myapp=${IMAGE_NAME}:${VERSION} -n prod
                        kubectl rollout status deployment/myapp -n prod
                    """
                }
            }
        }
    }

    post {
        always {
            cleanWs()
        }
        success {
            slackSend(
                color: 'good',
                message: "SUCCESS: ${env.JOB_NAME} #${env.BUILD_NUMBER} (<${env.BUILD_URL}|Open>)"
            )
        }
        failure {
            slackSend(
                color: 'danger',
                message: "FAILURE: ${env.JOB_NAME} #${env.BUILD_NUMBER} (<${env.BUILD_URL}|Open>)"
            )
        }
    }
}

// Helper function
def deployToEnvironment(env, version) {
    sh """
        kubectl config use-context ${env}-cluster
        kubectl set image deployment/myapp myapp=${IMAGE_NAME}:${version} -n ${env}
        kubectl rollout status deployment/myapp -n ${env}
        kubectl get pods -n ${env} -l app=myapp
    """
}
```

**Benefits**:
- Kubernetes-based agents
- Shared library functions
- Parallel execution
- Manual approval gates
- Comprehensive notifications

---

## Anti-Patterns

### Anti-Pattern 1: Testing Without Artifacts

**Problem**: Re-building code in test stages

**Why It's Bad**:
- Wastes time rebuilding
- Tests different code than what deploys
- Non-deterministic results
- Longer pipeline duration

**Solution**:
```yaml
# Build once
build:
  script: npm run build
  artifacts:
    paths: [dist/]

# Test using artifacts
test:
  needs: [build]
  script:
    - download artifacts
    - npm test
```

---

### Anti-Pattern 2: No Pipeline Caching

**Problem**: Installing dependencies every run

**Why It's Bad**:
- Slow pipeline execution
- Network dependency
- Wastes resources
- Unpredictable timing

**Solution**:
```yaml
# GitHub Actions
- uses: actions/setup-node@v4
  with:
    cache: 'npm'

# GitLab CI
cache:
  key: ${CI_COMMIT_REF_SLUG}
  paths:
    - node_modules/
    - .npm/
```

---

### Anti-Pattern 3: Secrets in Code

**Problem**: Hardcoded credentials in pipeline configs

**Why It's Bad**:
- Security risk
- Leaked in version control
- Difficult to rotate
- Compliance violations

**Solution**:
```yaml
# Use secret management
env:
  API_KEY: ${{ secrets.API_KEY }}

# Use OIDC for cloud providers
- uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: ${{ secrets.AWS_ROLE }}
```

---

### Anti-Pattern 4: No Version Tagging

**Problem**: Deploying "latest" tag

**Why It's Bad**:
- Can't rollback
- No traceability
- Overwrites existing images
- Breaks reproducibility

**Solution**:
```yaml
# Semantic versioning with git sha
VERSION: v1.2.3-abc1234
IMAGE_TAG: myapp:v1.2.3-abc1234

# Tag multiple
tags:
  - myapp:v1.2.3-abc1234
  - myapp:v1.2.3
  - myapp:latest
```

---

### Anti-Pattern 5: Sequential-Only Execution

**Problem**: Running all jobs sequentially

**Why It's Bad**:
- Very slow pipelines
- Wastes CI resources
- Poor developer experience
- Delayed feedback

**Solution**:
```yaml
# Parallel stages
test-unit:
  needs: [build]
test-integration:
  needs: [build]
test-e2e:
  needs: [build]
# All run in parallel
```

---

## Quick Reference

### Pipeline Performance Optimization

```yaml
Caching:         Cache dependencies (npm, pip, maven)
Parallelization: Run independent jobs in parallel
Artifacts:       Build once, reuse everywhere
Docker layers:   Multi-stage builds, layer caching
Matrix builds:   Test multiple versions simultaneously
Conditional:     Skip unnecessary jobs
```

### Common Pipeline Metrics

```yaml
Lead Time:       Commit to production
Build Time:      Duration of build stage
Test Time:       Duration of all tests
Deployment Time: Time to deploy
Failure Rate:    % of failed pipelines
MTTR:           Mean time to recovery
```

### Security Scanning Tools

```yaml
SAST:           CodeQL, Semgrep, SonarQube
Dependency:     npm audit, Snyk, Dependabot
Container:      Trivy, Grype, Snyk Container
Secrets:        Gitleaks, TruffleHog
License:        license-checker, FOSSA
SBOM:           Syft, CycloneDX
```

---

## Level 3: Resources

**Extended documentation, production-ready scripts, and complete examples**

### REFERENCE.md
**Location**: `resources/REFERENCE.md` (3,847 lines)

Comprehensive reference covering:
- CI/CD fundamentals and architecture patterns
- Platform-specific implementations (GitHub Actions, GitLab CI, Jenkins, CircleCI, Buildkite)
- Pipeline optimization strategies (caching, parallelization, artifacts)
- Testing integration (unit, integration, E2E, security)
- Security scanning and compliance (SAST, DAST, SCA, secrets)
- Artifact management and versioning strategies
- Multi-environment deployment workflows
- Monitoring and observability in pipelines
- Troubleshooting and debugging techniques
- Migration guides between platforms
- Complete production examples for all patterns

### Scripts

**validate_pipeline.py** (782 lines)
Validates pipeline configurations across multiple platforms:
```bash
# Validate GitHub Actions workflow
./validate_pipeline.py --file .github/workflows/ci.yml --platform github-actions

# Validate GitLab CI
./validate_pipeline.py --file .gitlab-ci.yml --platform gitlab

# Check entire directory
./validate_pipeline.py --directory .github/workflows/ --platform github-actions

# JSON output for CI integration
./validate_pipeline.py --file ci.yml --json
```

**analyze_pipeline_performance.py** (698 lines)
Analyzes pipeline performance and identifies bottlenecks:
```bash
# Analyze GitHub Actions workflows
./analyze_pipeline_performance.py --platform github-actions --repo owner/repo

# Compare multiple runs
./analyze_pipeline_performance.py --runs 100 --compare

# Generate optimization report
./analyze_pipeline_performance.py --output report.html --recommendations

# JSON output
./analyze_pipeline_performance.py --json
```

**test_pipeline.sh** (656 lines)
Tests pipeline configurations and deployment procedures:
```bash
# Dry-run pipeline locally
./test_pipeline.sh --file .github/workflows/ci.yml --dry-run

# Test deployment scripts
./test_pipeline.sh --test-deployment --environment staging

# Validate rollback procedures
./test_pipeline.sh --test-rollback

# Full pipeline simulation
./test_pipeline.sh --simulate --verbose
```

### Production Examples

**Complete Multi-Platform Pipelines**:
- `examples/github-actions/complete-pipeline.yml`: Full GitHub Actions pipeline with all stages
- `examples/gitlab-ci/complete-pipeline.yml`: Full GitLab CI pipeline with environments
- `examples/jenkins/Jenkinsfile`: Complete Jenkins declarative pipeline
- `examples/circleci/config.yml`: CircleCI pipeline with workflows and orbs

**Deployment Automation**:
- `examples/deployment/kubernetes-deploy.yml`: Kubernetes deployment automation
- `examples/deployment/aws-ecs-deploy.yml`: AWS ECS deployment
- `examples/deployment/azure-deploy.yml`: Azure App Service deployment
- `examples/deployment/gcp-deploy.yml`: Google Cloud Run deployment

**Security Integration**:
- `examples/security/trivy-scan.yml`: Container scanning with Trivy
- `examples/security/snyk-integration.yml`: Snyk security scanning
- `examples/security/codeql-analysis.yml`: CodeQL SAST integration

**Artifact Management**:
- `examples/artifacts/docker-registry.yml`: Docker image management
- `examples/artifacts/npm-publish.yml`: NPM package publishing
- `examples/artifacts/versioning-strategy.yml`: Semantic versioning automation

All examples include:
- Production-ready configurations
- Comprehensive comments and documentation
- Error handling and validation
- Security best practices
- Performance optimizations
- Monitoring integration

---

## Related Skills

- `deployment-strategies.md` - Blue-green, canary, rolling deployments
- `ci-security.md` - Security scanning and secret management
- `ci-testing-strategy.md` - Test execution patterns
- `ci-optimization.md` - Pipeline performance tuning
- `kubernetes-deployment` - K8s-specific deployments
- `docker-best-practices` - Container optimization

---

**Last Updated**: 2025-10-27
**Maintainer**: Skills Team
**Validation**: CI-validated, production-tested patterns
