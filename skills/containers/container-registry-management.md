---
name: containers-container-registry-management
description: Choosing a container registry (ECR/GCR/Harbor/Docker Hub)
---



# Container Registry Management

**Scope**: Registry options (ECR/GCR/Harbor), image tagging, promotion workflows
**Lines**: ~280
**Last Updated**: 2025-10-18

## When to Use This Skill

Activate this skill when:
- Choosing a container registry (ECR/GCR/Harbor/Docker Hub)
- Implementing image tagging strategies
- Setting up image promotion workflows (dev → staging → prod)
- Managing registry authentication and permissions
- Optimizing image storage and costs
- Implementing vulnerability scanning pipelines
- Configuring image retention policies
- Troubleshooting registry push/pull issues

## Core Concepts

### What is a Container Registry?

**Container registry**: Storage and distribution system for container images.

**Key properties**:
- **Centralized storage**: Single source of truth for images
- **Access control**: Authentication and authorization
- **Versioning**: Multiple versions via tags
- **Distribution**: Efficient image distribution
- **Scanning**: Vulnerability detection
- **Metadata**: Image labels, manifests, digests

**Registry workflow**:
```
Build → Tag → Push → Registry → Pull → Deploy
```

---

## Registry Options

### Docker Hub (Public/Default)

**Characteristics**:
- **Public**: Free for public images
- **Private**: Limited free private repos (paid plans)
- **Default**: Used if no registry specified
- **Global**: High availability, CDN

**Usage**:
```bash
# Login
docker login

# Tag
docker tag myapp:latest username/myapp:v1.0.0

# Push
docker push username/myapp:v1.0.0

# Pull
docker pull username/myapp:v1.0.0
```

**Pros**: Easy, well-integrated, global CDN
**Cons**: Rate limits (100 pulls/6h unauthenticated), costs for private repos

### AWS Elastic Container Registry (ECR)

**Characteristics**:
- **Private**: Private by default
- **AWS-integrated**: Works with ECS, EKS, Lambda
- **Scanning**: Built-in vulnerability scanning
- **Regional**: Per-region registries

**Setup**:
```bash
# Login (get token from AWS)
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  123456789012.dkr.ecr.us-east-1.amazonaws.com

# Create repository
aws ecr create-repository --repository-name myapp

# Tag
docker tag myapp:latest \
  123456789012.dkr.ecr.us-east-1.amazonaws.com/myapp:v1.0.0

# Push
docker push \
  123456789012.dkr.ecr.us-east-1.amazonaws.com/myapp:v1.0.0
```

**Pros**: AWS integration, security scanning, fine-grained IAM
**Cons**: AWS-only, regional (latency), costs per storage/transfer

### Google Container Registry (GCR) / Artifact Registry

**Characteristics**:
- **Private**: Private by default
- **GCP-integrated**: Works with GKE, Cloud Run
- **Global**: Multi-region support
- **Scanning**: Built-in vulnerability scanning

**Setup**:
```bash
# Login (using gcloud)
gcloud auth configure-docker

# Tag
docker tag myapp:latest gcr.io/my-project/myapp:v1.0.0

# Push
docker push gcr.io/my-project/myapp:v1.0.0

# Pull
docker pull gcr.io/my-project/myapp:v1.0.0
```

**Artifact Registry** (newer, recommended):
```bash
# Login
gcloud auth configure-docker us-docker.pkg.dev

# Push
docker push us-docker.pkg.dev/my-project/my-repo/myapp:v1.0.0
```

**Pros**: GCP integration, global, good performance
**Cons**: GCP-only, costs per storage/transfer

### Azure Container Registry (ACR)

**Characteristics**:
- **Private**: Private by default
- **Azure-integrated**: Works with AKS, App Service
- **Geo-replication**: Multi-region replication
- **Scanning**: Defender for Cloud integration

**Setup**:
```bash
# Login
az acr login --name myregistry

# Tag
docker tag myapp:latest myregistry.azurecr.io/myapp:v1.0.0

# Push
docker push myregistry.azurecr.io/myapp:v1.0.0
```

**Pros**: Azure integration, geo-replication, security scanning
**Cons**: Azure-only, costs per tier

### GitHub Container Registry (GHCR)

**Characteristics**:
- **GitHub-integrated**: Tied to GitHub repos
- **Public/private**: Support for both
- **Free**: Generous free tier
- **CI/CD**: Easy GitHub Actions integration

**Setup**:
```bash
# Login (using GitHub token)
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Tag
docker tag myapp:latest ghcr.io/username/myapp:v1.0.0

# Push
docker push ghcr.io/username/myapp:v1.0.0
```

**GitHub Actions**:
```yaml
- name: Login to GHCR
  uses: docker/login-action@v2
  with:
    registry: ghcr.io
    username: ${{ github.actor }}
    password: ${{ secrets.GITHUB_TOKEN }}

- name: Build and push
  uses: docker/build-push-action@v4
  with:
    push: true
    tags: ghcr.io/${{ github.repository }}:latest
```

**Pros**: Free, GitHub integration, easy CI/CD
**Cons**: GitHub-specific, less enterprise features

### Harbor (Self-Hosted)

**Characteristics**:
- **Self-hosted**: Full control
- **Open-source**: CNCF project
- **Enterprise features**: RBAC, replication, scanning
- **Multi-registry**: Proxy to Docker Hub, GCR, etc.

**Setup** (Docker Compose):
```yaml
version: '3.8'

services:
  registry:
    image: goharbor/harbor-registryctl:v2.9.0
    volumes:
      - registry_data:/storage

  core:
    image: goharbor/harbor-core:v2.9.0
    depends_on:
      - registry

volumes:
  registry_data:
```

**Pros**: Self-hosted, full control, no vendor lock-in
**Cons**: Operational overhead, requires infrastructure

### Comparison Matrix

| Registry | Cost | Private | Scanning | Multi-Cloud | Best For |
|----------|------|---------|----------|-------------|----------|
| **Docker Hub** | Free/Paid | Limited | No | Yes | Public images, quick start |
| **ECR** | Pay-per-use | Yes | Yes | No (AWS) | AWS workloads |
| **GCR/AR** | Pay-per-use | Yes | Yes | No (GCP) | GCP workloads |
| **ACR** | Tiered | Yes | Yes | No (Azure) | Azure workloads |
| **GHCR** | Free (generous) | Yes | No | Yes | GitHub projects |
| **Harbor** | Infrastructure | Yes | Yes | Yes | Self-hosted, multi-cloud |

---

## Image Tagging Strategies

### Semantic Versioning (Recommended)

**Format**: `MAJOR.MINOR.PATCH` (e.g., `1.2.3`)

```bash
# Tag with semantic version
docker tag myapp:latest myregistry/myapp:1.2.3

# Also tag mutable aliases
docker tag myapp:latest myregistry/myapp:1.2     # Minor series
docker tag myapp:latest myregistry/myapp:1       # Major series
docker tag myapp:latest myregistry/myapp:latest  # Latest

# Push all tags
docker push myregistry/myapp:1.2.3
docker push myregistry/myapp:1.2
docker push myregistry/myapp:1
docker push myregistry/myapp:latest
```

**Deployment**:
```yaml
# Production: Pin exact version
image: myregistry/myapp:1.2.3

# Staging: Minor series (auto-patch updates)
image: myregistry/myapp:1.2

# Dev: Latest (always newest)
image: myregistry/myapp:latest
```

### Git-Based Tagging

**Commit SHA** (immutable, traceable):
```bash
# Tag with git commit SHA
GIT_SHA=$(git rev-parse --short HEAD)
docker tag myapp:latest myregistry/myapp:$GIT_SHA
docker push myregistry/myapp:$GIT_SHA
```

**Branch name**:
```bash
# Tag with branch
BRANCH=$(git rev-parse --abbrev-ref HEAD)
docker tag myapp:latest myregistry/myapp:$BRANCH
docker push myregistry/myapp:$BRANCH
```

**Combined** (version + SHA):
```bash
VERSION=1.2.3
GIT_SHA=$(git rev-parse --short HEAD)
docker tag myapp:latest myregistry/myapp:${VERSION}-${GIT_SHA}
docker push myregistry/myapp:${VERSION}-${GIT_SHA}
# Example: myregistry/myapp:1.2.3-abc123
```

### Environment-Based Tagging

```bash
# Tag by environment
docker tag myapp:latest myregistry/myapp:dev
docker tag myapp:latest myregistry/myapp:staging
docker tag myapp:latest myregistry/myapp:prod
```

**CI/CD**:
```yaml
# GitHub Actions
- name: Tag and push
  run: |
    docker tag myapp:latest myregistry/myapp:${{ github.sha }}
    docker tag myapp:latest myregistry/myapp:${{ github.ref_name }}
    docker push --all-tags myregistry/myapp
```

### Anti-Patterns (Avoid)

❌ **Using only :latest**
```bash
docker push myregistry/myapp:latest
# Problem: No version history, hard to rollback
```

❌ **Dates as tags**
```bash
docker tag myapp:latest myregistry/myapp:2025-10-18
# Problem: No semantic meaning, hard to compare
```

❌ **Overwriting tags**
```bash
docker tag myapp:latest myregistry/myapp:1.2.3
docker push myregistry/myapp:1.2.3
# Later: rebuild and push same tag
# Problem: Tag now points to different image!
```

✅ **Best practice**: Use immutable tags (SHA, version) + mutable aliases (:latest, :stable)

---

## Image Promotion Workflows

### Pattern 1: Environment Promotion

**Workflow**: Dev → Staging → Production

```bash
# Step 1: Build and tag
docker build -t myregistry/myapp:${VERSION}-${SHA} .

# Step 2: Push to registry
docker push myregistry/myapp:${VERSION}-${SHA}

# Step 3: Deploy to dev
docker tag myregistry/myapp:${VERSION}-${SHA} myregistry/myapp:dev
docker push myregistry/myapp:dev

# Step 4: Promote to staging (after tests pass)
docker pull myregistry/myapp:${VERSION}-${SHA}
docker tag myregistry/myapp:${VERSION}-${SHA} myregistry/myapp:staging
docker push myregistry/myapp:staging

# Step 5: Promote to prod (after staging validation)
docker pull myregistry/myapp:${VERSION}-${SHA}
docker tag myregistry/myapp:${VERSION}-${SHA} myregistry/myapp:prod
docker push myregistry/myapp:prod
```

**Key**: Immutable base tag (`${VERSION}-${SHA}`), mutable environment tags.

### Pattern 2: Registry-Based Promotion

**Multiple registries** (dev/staging/prod):
```bash
# Dev registry
docker tag myapp:latest dev-registry/myapp:1.2.3
docker push dev-registry/myapp:1.2.3

# Promote to staging registry
docker pull dev-registry/myapp:1.2.3
docker tag dev-registry/myapp:1.2.3 staging-registry/myapp:1.2.3
docker push staging-registry/myapp:1.2.3

# Promote to prod registry
docker pull staging-registry/myapp:1.2.3
docker tag staging-registry/myapp:1.2.3 prod-registry/myapp:1.2.3
docker push prod-registry/myapp:1.2.3
```

### Pattern 3: Repository-Based Promotion

**Single registry, different repos**:
```bash
# Push to dev repo
docker push myregistry/dev/myapp:1.2.3

# Promote to staging repo
docker pull myregistry/dev/myapp:1.2.3
docker tag myregistry/dev/myapp:1.2.3 myregistry/staging/myapp:1.2.3
docker push myregistry/staging/myapp:1.2.3

# Promote to prod repo
docker pull myregistry/staging/myapp:1.2.3
docker tag myregistry/staging/myapp:1.2.3 myregistry/prod/myapp:1.2.3
docker push myregistry/prod/myapp:1.2.3
```

### CI/CD Automation (GitHub Actions)

```yaml
name: Build and Promote

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Login to Registry
        uses: docker/login-action@v2
        with:
          registry: myregistry.io
          username: ${{ secrets.REGISTRY_USER }}
          password: ${{ secrets.REGISTRY_PASSWORD }}

      - name: Build and push
        uses: docker/build-push-action@v4
        with:
          push: true
          tags: |
            myregistry.io/myapp:${{ github.sha }}
            myregistry.io/myapp:dev

  promote-staging:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Promote to staging
        run: |
          docker pull myregistry.io/myapp:${{ github.sha }}
          docker tag myregistry.io/myapp:${{ github.sha }} myregistry.io/myapp:staging
          docker push myregistry.io/myapp:staging

  promote-prod:
    needs: promote-staging
    runs-on: ubuntu-latest
    environment: production   # Requires approval
    steps:
      - name: Promote to prod
        run: |
          docker pull myregistry.io/myapp:${{ github.sha }}
          docker tag myregistry.io/myapp:${{ github.sha }} myregistry.io/myapp:prod
          docker push myregistry.io/myapp:prod
```

---

## Authentication and Permissions

### Docker Hub

```bash
# Login
docker login
# Enter: username, password

# Logout
docker logout
```

### ECR (IAM-based)

```bash
# Get login password
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  123456789012.dkr.ecr.us-east-1.amazonaws.com
```

**IAM Policy** (push/pull):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:PutImage"
      ],
      "Resource": "*"
    }
  ]
}
```

### GCR (gcloud-based)

```bash
# Configure Docker to use gcloud credentials
gcloud auth configure-docker

# Or manually
gcloud auth print-access-token | \
  docker login -u oauth2accesstoken --password-stdin \
  https://gcr.io
```

### GitHub Container Registry

```bash
# Create personal access token (read:packages, write:packages)
echo $GITHUB_TOKEN | \
  docker login ghcr.io -u USERNAME --password-stdin
```

### Harbor (User/Password)

```bash
docker login myregistry.example.com
# Enter: username, password
```

---

## Image Retention Policies

### Docker Hub

**Manually delete**:
```bash
# Via UI or API
curl -X DELETE \
  -H "Authorization: Bearer $TOKEN" \
  https://hub.docker.com/v2/repositories/username/myapp/tags/old-tag/
```

### ECR Lifecycle Policies

```json
{
  "rules": [
    {
      "rulePriority": 1,
      "description": "Keep last 10 images",
      "selection": {
        "tagStatus": "any",
        "countType": "imageCountMoreThan",
        "countNumber": 10
      },
      "action": {
        "type": "expire"
      }
    },
    {
      "rulePriority": 2,
      "description": "Delete untagged after 7 days",
      "selection": {
        "tagStatus": "untagged",
        "countType": "sinceImagePushed",
        "countUnit": "days",
        "countNumber": 7
      },
      "action": {
        "type": "expire"
      }
    }
  ]
}
```

**Apply**:
```bash
aws ecr put-lifecycle-policy \
  --repository-name myapp \
  --lifecycle-policy-text file://policy.json
```

### GCR/Artifact Registry

```bash
# Delete images older than 30 days
gcloud artifacts docker images delete \
  us-docker.pkg.dev/my-project/my-repo/myapp:old-tag \
  --delete-tags
```

### Harbor Retention Rules

**Via UI**: Project → Policy → Retention Rules
- Keep last N images
- Keep images from last N days
- Regex-based tag matching

---

## Troubleshooting

### Issue 1: Authentication Failed

**Symptom**: `unauthorized: authentication required`

**Solution**: Re-login
```bash
# Check current login
cat ~/.docker/config.json

# Re-login
docker login myregistry.io
```

### Issue 2: Image Not Found

**Symptom**: `Error response from daemon: manifest for myapp:v1.0.0 not found`

**Solution**: Check tag exists
```bash
# List tags (Docker Hub)
curl https://hub.docker.com/v2/repositories/username/myapp/tags

# List tags (ECR)
aws ecr describe-images --repository-name myapp
```

### Issue 3: Slow Push/Pull

**Symptom**: Push/pull takes very long

**Solutions**:
1. **Use closer region** (if multi-region registry)
2. **Optimize image size** (multi-stage builds)
3. **Check network bandwidth**
4. **Use registry cache/proxy**

---

## Quick Reference

### Common Commands

```bash
# Login
docker login myregistry.io

# Tag
docker tag myapp:latest myregistry.io/myapp:v1.0.0

# Push
docker push myregistry.io/myapp:v1.0.0

# Pull
docker pull myregistry.io/myapp:v1.0.0

# Remove local image
docker rmi myregistry.io/myapp:v1.0.0

# Push all tags
docker push --all-tags myregistry.io/myapp
```

### Tagging Best Practices

```bash
# Immutable: Version + SHA
docker tag myapp:latest myregistry/myapp:1.2.3-abc123

# Mutable: Environment
docker tag myapp:latest myregistry/myapp:dev
docker tag myapp:latest myregistry/myapp:staging
docker tag myapp:latest myregistry/myapp:prod

# Mutable: Latest
docker tag myapp:latest myregistry/myapp:latest
```

---

## Related Skills

- `dockerfile-optimization.md` - Building efficient images
- `container-security.md` - Scanning images for vulnerabilities
- `ci-cd-pipelines.md` - Automating builds and promotions
- `kubernetes-deployments.md` - Deploying images to K8s

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
