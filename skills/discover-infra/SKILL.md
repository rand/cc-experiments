---
name: discover-infra
description: Automatically discover cloud, infrastructure, deployment, and container skills when working with AWS, GCP, Azure, Docker, Kubernetes, Terraform, Netlify, Heroku, serverless, or IaC
license: MIT
metadata:
  author: rand
  version: "4.0"
compatibility:
  claude-code: ">=1.0.0"
---

# Infrastructure & Cloud Skills Discovery

## When This Skill Activates
- Cloud platforms (AWS, GCP, Azure)
- Serverless functions (Lambda, Cloud Functions, Modal)
- Infrastructure as Code (Terraform, IaC)
- Docker, containers, Kubernetes
- Container security, networking, registries
- Cloudflare Workers, edge computing
- Deployment platforms (Netlify, Heroku)
- Cost optimization, infrastructure security
- CI/CD deployment strategies, rollbacks

## Available Skills (30 total)

### Cloud (13 skills)
1. **aws-lambda-functions** - Lambda development, triggers, optimization
2. **aws-api-gateway** - REST/HTTP/WebSocket APIs, authorization
3. **aws-databases** - RDS, DynamoDB, ElastiCache, Aurora
4. **aws-iam-security** - IAM, Cognito, Secrets Manager, KMS
5. **aws-storage** - S3, EBS, EFS, Glacier, lifecycle policies
6. **aws-ec2-compute** - EC2, Auto Scaling, Load Balancing
7. **aws-networking** - VPC, security groups, Route53, CloudFront
8. **gcp-serverless** - Cloud Functions, Cloud Run, App Engine
9. **gcp-compute** - Compute Engine, GKE, autoscaling
10. **gcp-databases** - Cloud SQL, Firestore, Bigtable, Spanner
11. **gcp-storage** - Cloud Storage, Persistent Disk, Filestore
12. **gcp-iam-security** - IAM, service accounts, Secret Manager
13. **gcp-networking** - VPC, firewall, Cloud DNS, Cloud CDN

### Infrastructure (6 skills)
1. **terraform-patterns** - Modules, state, workspaces, best practices
2. **kubernetes-basics** - Pods, deployments, services, configuration
3. **cloudflare-workers** - Edge functions, KV storage, Durable Objects
4. **infrastructure-security** - Network security, secrets, hardening
5. **cost-optimization** - Cloud cost reduction strategies
6. **aws-serverless** - Serverless architecture patterns

### Deployment (6 skills)
1. **heroku-deployment** - Deployment, dynos, buildpacks
2. **heroku-addons** - Databases, caching, monitoring addons
3. **heroku-troubleshooting** - Common issues and debugging
4. **netlify-deployment** - Build, deploy, previews, CDN
5. **netlify-functions** - Serverless functions on Netlify
6. **netlify-optimization** - Performance, caching, edge

### Containers (5 skills)
1. **dockerfile-optimization** - Multi-stage builds, layer caching
2. **docker-compose-development** - Multi-service local development
3. **container-networking** - Bridge, overlay, service discovery
4. **container-security** - Image scanning, runtime security
5. **container-registry-management** - Registry setup, policies

## Load Full Category Details
Read ../cloud/INDEX.md
Read ../infrastructure/INDEX.md
Read ../deployment/INDEX.md
Read ../containers/INDEX.md

## Progressive Loading
- **Level 1**: This gateway loads automatically (~80 lines)
- **Level 2**: Load category INDEX.md for full skill listings
- **Level 3**: Load specific skills as needed
