---
name: cloud-kubernetes-deployment
category: cloud
description: Deploy and manage applications on Kubernetes with production best practices
tags: [kubernetes, k8s, deployment, cloud, containers, orchestration]
version: 1.0.0
---

# Kubernetes Deployment

Deploy and manage containerized applications on Kubernetes with production best practices for high availability, security, and scalability.

## Overview

This skill covers Kubernetes deployment strategies, including:

- **Pod and Deployment Management**: Creating and managing workloads
- **Service Discovery**: Exposing and accessing applications
- **Rolling Updates**: Zero-downtime deployments and rollbacks
- **Resource Management**: CPU, memory, and storage configuration
- **Health Checks**: Liveness, readiness, and startup probes
- **Configuration**: ConfigMaps, Secrets, and environment management
- **Networking**: Services, Ingress, and NetworkPolicies
- **Security**: RBAC, Pod Security Standards, security contexts
- **Autoscaling**: HPA, VPA, and cluster autoscaling
- **GitOps**: ArgoCD and Flux workflows
- **Helm**: Package management and templating

## When to Use

- Deploying containerized applications to Kubernetes
- Managing application lifecycle in Kubernetes
- Implementing CI/CD for Kubernetes deployments
- Setting up production-ready Kubernetes workloads
- Troubleshooting Kubernetes deployments
- Migrating applications to Kubernetes

## Prerequisites

- Docker and containerization basics
- YAML syntax
- Basic networking concepts
- Command-line proficiency
- Access to a Kubernetes cluster (or local testing with kind/minikube)

## Key Concepts

### Kubernetes Resources

**Workloads:**
- **Pod**: Smallest deployable unit (one or more containers)
- **Deployment**: Manages ReplicaSets for stateless apps
- **StatefulSet**: Manages stateful workloads with stable identities
- **DaemonSet**: Runs pods on all (or selected) nodes
- **Job/CronJob**: Batch processing and scheduled tasks

**Services:**
- **ClusterIP**: Internal cluster communication
- **NodePort**: Expose on node IPs
- **LoadBalancer**: Cloud provider load balancer
- **Ingress**: HTTP/HTTPS routing

**Configuration:**
- **ConfigMap**: Non-sensitive configuration data
- **Secret**: Sensitive data (base64 encoded)
- **PersistentVolume/PVC**: Storage management

**Security:**
- **ServiceAccount**: Pod identity
- **Role/ClusterRole**: RBAC permissions
- **NetworkPolicy**: Pod network isolation
- **PodSecurityPolicy/Standards**: Pod security controls

### Deployment Strategies

**Rolling Update (Default):**
- Gradual replacement of old pods with new ones
- Zero downtime
- Configurable with maxSurge and maxUnavailable

**Recreate:**
- Delete all old pods before creating new ones
- Causes downtime
- Useful when incompatible versions can't coexist

**Canary:**
- Deploy new version to small subset
- Monitor metrics before full rollout
- Manual traffic splitting

**Blue-Green:**
- Deploy new version alongside old
- Switch traffic all at once
- Easy rollback

## Basic Usage

### Create Deployment

```bash
# From command line
kubectl create deployment web --image=nginx:1.25 --replicas=3

# From YAML
kubectl apply -f deployment.yaml
```

**deployment.yaml:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
      - name: nginx
        image: nginx:1.25
        ports:
        - containerPort: 80
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 200m
            memory: 256Mi
```

### Expose with Service

```bash
# Create service
kubectl expose deployment web --port=80 --type=LoadBalancer

# From YAML
kubectl apply -f service.yaml
```

**service.yaml:**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: web
spec:
  selector:
    app: web
  ports:
  - port: 80
    targetPort: 80
  type: LoadBalancer
```

### Update Deployment

```bash
# Update image
kubectl set image deployment/web nginx=nginx:1.26

# Edit deployment
kubectl edit deployment/web

# Apply changes from file
kubectl apply -f deployment.yaml

# Monitor rollout
kubectl rollout status deployment/web
```

### Rollback Deployment

```bash
# View history
kubectl rollout history deployment/web

# Rollback to previous version
kubectl rollout undo deployment/web

# Rollback to specific revision
kubectl rollout undo deployment/web --to-revision=2
```

## Advanced Patterns

### Production-Ready Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
  labels:
    app: api
    version: v1
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
        version: v1
    spec:
      serviceAccountName: api
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 2000

      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values:
                  - api
              topologyKey: kubernetes.io/hostname

      containers:
      - name: api
        image: myapp/api:v1.0.0
        ports:
        - name: http
          containerPort: 8080

        env:
        - name: DB_HOST
          valueFrom:
            configMapKeyRef:
              name: api-config
              key: db.host
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: api-secrets
              key: db.password

        resources:
          requests:
            cpu: 500m
            memory: 512Mi
          limits:
            cpu: 2
            memory: 2Gi

        startupProbe:
          httpGet:
            path: /healthz/startup
            port: http
          periodSeconds: 10
          failureThreshold: 30

        livenessProbe:
          httpGet:
            path: /healthz/live
            port: http
          periodSeconds: 10
          failureThreshold: 3

        readinessProbe:
          httpGet:
            path: /healthz/ready
            port: http
          periodSeconds: 5
          failureThreshold: 3

        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          runAsNonRoot: true
          capabilities:
            drop:
            - ALL

        volumeMounts:
        - name: tmp
          mountPath: /tmp

      volumes:
      - name: tmp
        emptyDir: {}
```

### Horizontal Pod Autoscaler

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### ConfigMap and Secret

```yaml
# ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: api-config
data:
  db.host: "postgres.default.svc.cluster.local"
  db.port: "5432"
  app.yaml: |
    server:
      port: 8080
      timeout: 30s
---
# Secret
# ❌ BAD: Hardcoded credentials - example only, never do this in production
# In production, use sealed-secrets, external-secrets-operator, or your cloud provider's secret management
apiVersion: v1
kind: Secret
metadata:
  name: api-secrets
type: Opaque
stringData:
  db.password: "changeme123"  # Example only - use secret management in production
  api.key: "secret-api-key"  # Example only - use secret management in production
```

## Common Commands

```bash
# Get resources
kubectl get deployments
kubectl get pods
kubectl get services
kubectl get all

# Describe resource
kubectl describe deployment web
kubectl describe pod web-abc123

# View logs
kubectl logs deployment/web
kubectl logs -f pod/web-abc123  # Follow logs
kubectl logs pod/web-abc123 --previous  # Previous container

# Execute commands in pod
kubectl exec -it pod/web-abc123 -- /bin/sh

# Port forwarding
kubectl port-forward deployment/web 8080:80

# Scale deployment
kubectl scale deployment/web --replicas=5

# Delete resources
kubectl delete deployment web
kubectl delete -f deployment.yaml
```

## Troubleshooting

### Pod Not Starting

```bash
# Check pod status
kubectl get pods
kubectl describe pod <pod-name>

# Common issues:
# - ImagePullBackOff: Check image name and registry credentials
# - CrashLoopBackOff: Check logs for application errors
# - Pending: Check resource availability and node constraints

# View events
kubectl get events --sort-by='.lastTimestamp'

# Check logs
kubectl logs <pod-name>
```

### Service Not Accessible

```bash
# Check service and endpoints
kubectl get service web
kubectl get endpoints web

# Test DNS
kubectl run -it --rm debug --image=busybox --restart=Never -- nslookup web

# Test connectivity
kubectl run -it --rm debug --image=curlimages/curl --restart=Never -- curl http://web
```

### Deployment Not Rolling Out

```bash
# Check rollout status
kubectl rollout status deployment/web

# View deployment events
kubectl describe deployment web

# Check replica sets
kubectl get rs -l app=web

# Pause and resume
kubectl rollout pause deployment/web
kubectl rollout resume deployment/web
```

## Best Practices

### Resource Management
- Always set resource requests and limits
- Use appropriate QoS class (Guaranteed for critical workloads)
- Monitor actual usage and adjust accordingly

### Health Checks
- Always define readiness probes
- Use startup probes for slow-starting applications
- Keep probe endpoints lightweight

### Security
- Run as non-root user
- Use read-only root filesystem
- Drop all capabilities unless needed
- Implement NetworkPolicies
- Use RBAC with least privilege
- Scan images for vulnerabilities

### High Availability
- Run multiple replicas (minimum 3 for critical services)
- Use pod anti-affinity to spread across nodes/zones
- Define PodDisruptionBudgets
- Use topology spread constraints

### Configuration
- Externalize configuration with ConfigMaps/Secrets
- Use immutable ConfigMaps/Secrets in production
- Never commit secrets to Git
- Version configuration with application

### Deployment
- Use specific image tags (never :latest)
- Implement gradual rollouts (canary/blue-green)
- Monitor during rollout
- Have rollback plan
- Test in staging first

## Related Skills

- `containers-docker`: Container fundamentals
- `cloud-aws-eks`: AWS Kubernetes service
- `cloud-gcp-gke`: Google Kubernetes Engine
- `observability-prometheus`: Metrics collection
- `cicd-github-actions`: CI/CD automation
- `infrastructure-terraform`: Infrastructure as Code

## Level 3: Resources

Comprehensive resources for Kubernetes deployment are available in the `resources/` directory:

### Reference Material

**`resources/REFERENCE.md`** (1,800+ lines)
Complete reference covering:
- Kubernetes architecture and fundamentals
- Pod lifecycle and multi-container patterns
- Deployment strategies and rollout management
- Service networking and discovery
- Resource management and QoS
- Health checks configuration
- ConfigMaps and Secrets management
- Persistent storage (PVs, PVCs, StorageClasses)
- Networking (Services, Ingress, NetworkPolicies)
- Security (RBAC, Pod Security Standards, security contexts)
- Autoscaling (HPA, VPA, Cluster Autoscaler)
- GitOps patterns (ArgoCD, Flux)
- Helm charts and package management
- Production best practices
- Troubleshooting guide
- Common pitfalls and anti-patterns

### Executable Scripts

**`resources/scripts/validate_manifests.py`**
Validate Kubernetes YAML manifests for correctness and best practices:
- YAML syntax validation
- Kubernetes API schema compliance
- Security best practices checks
- Resource configuration validation
- Common misconfiguration detection
- kubectl dry-run validation
- JSON and colored output options

```bash
# Validate single file
./validate_manifests.py deployment.yaml

# Validate directory
./validate_manifests.py --strict manifests/

# JSON output
./validate_manifests.py --json deployment.yaml
```

**`resources/scripts/analyze_deployment.py`**
Analyze deployments for issues and optimization opportunities:
- Configuration issue detection
- Security vulnerability scanning
- Resource optimization recommendations
- High availability concerns
- Production readiness assessment
- Live cluster analysis support

```bash
# Analyze file
./analyze_deployment.py deployment.yaml

# Analyze live cluster
./analyze_deployment.py --cluster --namespace production

# JSON output
./analyze_deployment.py --json --cluster
```

**`resources/scripts/test_deployment.sh`**
Test deployments in local Kubernetes cluster:
- Creates test cluster (kind/minikube)
- Deploys manifests
- Validates rollout
- Runs health checks
- Executes smoke tests
- Automatic cleanup

```bash
# Test with kind
./test_deployment.sh deployment.yaml

# Test with minikube
./test_deployment.sh --provider minikube manifests/

# Keep cluster for debugging
./test_deployment.sh --no-cleanup deployment.yaml
```

### Examples

**`resources/examples/manifests/basic-deployment/`**
Simple deployment example:
- Basic Deployment with nginx
- ClusterIP Service
- Minimal configuration for learning

**`resources/examples/manifests/production-deployment/`**
Production-ready deployment:
- Full Deployment with all best practices
- LoadBalancer Service with annotations
- ConfigMap and Secret management
- HorizontalPodAutoscaler
- PodDisruptionBudget
- Security contexts and RBAC
- Multi-container patterns
- Health checks and lifecycle hooks

**`resources/examples/helm/sample-chart/`**
Complete Helm chart structure:
- Chart.yaml with metadata and dependencies
- values.yaml with sensible defaults
- Templates for all resources
- Helper templates (_helpers.tpl)
- Configurable security and resources

**`resources/examples/kustomize/`**
Kustomize overlays for environments:
- `base/`: Base manifests
- `overlays/dev/`: Development environment customizations
- `overlays/prod/`: Production environment customizations
- Demonstrates patching and configuration management

**`resources/examples/cicd/github-actions-deploy.yml`**
Complete GitHub Actions workflow:
- Build and push Docker images
- Validate manifests
- Deploy to staging (on PR)
- Deploy to production (on main)
- Rollback on failure
- Smoke tests

## Learning Path

1. **Start**: Basic deployment and service creation
2. **Intermediate**: Add health checks, resource limits, ConfigMaps
3. **Advanced**: Implement autoscaling, GitOps, production patterns
4. **Expert**: Multi-cluster, service mesh, advanced networking

## See Also

- [Official Kubernetes Documentation](https://kubernetes.io/docs/)
- [Kubernetes Patterns](https://k8spatterns.io/)
- [Production Best Practices](https://kubernetes.io/docs/setup/best-practices/)
