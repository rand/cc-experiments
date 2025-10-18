---
name: infrastructure-kubernetes-basics
description: Deploying containerized applications at scale
---


# Kubernetes Basics

**Scope**: Container orchestration with Kubernetes - Pods, Deployments, Services, ConfigMaps, Secrets, Ingress
**Lines**: 378
**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

**Activate when**:
- Deploying containerized applications at scale
- Managing microservices architectures
- Automating container orchestration and scaling
- Implementing rolling updates and rollbacks
- Managing application configuration and secrets
- Setting up load balancing and service discovery

**Prerequisites**:
- Docker installed and basic Docker knowledge
- kubectl CLI installed (`brew install kubectl` or from kubernetes.io)
- Access to Kubernetes cluster (Minikube, EKS, GKE, AKS)
- Basic understanding of YAML syntax
- Container registry account (Docker Hub, ECR, GCR)

**Common scenarios**:
- Deploying web applications and APIs
- Running batch jobs and cron tasks
- Implementing blue-green deployments
- Auto-scaling based on load
- Managing multi-environment deployments
- Service mesh implementation

---

## Core Concepts

### 1. Pods

```yaml
# pod.yaml - Smallest deployable unit
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
  labels:
    app: nginx
    environment: production
spec:
  containers:
  - name: nginx
    image: nginx:1.25
    ports:
    - containerPort: 80
      name: http
    resources:
      requests:
        memory: "64Mi"
        cpu: "250m"
      limits:
        memory: "128Mi"
        cpu: "500m"
    env:
    - name: ENVIRONMENT
      value: "production"
    livenessProbe:
      httpGet:
        path: /health
        port: 80
      initialDelaySeconds: 30
      periodSeconds: 10
    readinessProbe:
      httpGet:
        path: /ready
        port: 80
      initialDelaySeconds: 5
      periodSeconds: 5
  restartPolicy: Always
```

### 2. Deployments

```yaml
# deployment.yaml - Manages ReplicaSets and rolling updates
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  labels:
    app: web-app
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1        # Max pods above desired count
      maxUnavailable: 0  # Max pods unavailable during update
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
        version: v1.0.0
    spec:
      containers:
      - name: web-app
        image: myregistry/web-app:1.0.0
        ports:
        - containerPort: 8080
          name: http
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url
        - name: APP_CONFIG
          valueFrom:
            configMapKeyRef:
              name: app-config
              key: config.json
        resources:
          requests:
            memory: "256Mi"
            cpu: "500m"
          limits:
            memory: "512Mi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 5
```

### 3. Services

```yaml
# service-clusterip.yaml - Internal service
apiVersion: v1
kind: Service
metadata:
  name: web-app-service
spec:
  type: ClusterIP  # Only accessible within cluster
  selector:
    app: web-app
  ports:
  - port: 80
    targetPort: 8080
    protocol: TCP
    name: http

---
# service-loadbalancer.yaml - External load balancer
apiVersion: v1
kind: Service
metadata:
  name: web-app-lb
spec:
  type: LoadBalancer  # Cloud provider load balancer
  selector:
    app: web-app
  ports:
  - port: 80
    targetPort: 8080
    protocol: TCP

---
# service-nodeport.yaml - Exposes on node IP
apiVersion: v1
kind: Service
metadata:
  name: web-app-nodeport
spec:
  type: NodePort  # Accessible on node IP:NodePort
  selector:
    app: web-app
  ports:
  - port: 80
    targetPort: 8080
    nodePort: 30080  # 30000-32767 range
```

### 4. ConfigMaps

```yaml
# configmap.yaml - Configuration data
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  # Key-value pairs
  log_level: "info"
  max_connections: "100"

  # File-like keys
  config.json: |
    {
      "apiUrl": "https://api.example.com",
      "timeout": 30,
      "retries": 3
    }

  nginx.conf: |
    server {
      listen 80;
      server_name _;

      location / {
        proxy_pass http://backend:8080;
        proxy_set_header Host $host;
      }
    }

---
# Use ConfigMap in Pod
apiVersion: v1
kind: Pod
metadata:
  name: app-pod
spec:
  containers:
  - name: app
    image: myapp:1.0
    # Environment variables from ConfigMap
    envFrom:
    - configMapRef:
        name: app-config
    # Individual env vars
    env:
    - name: LOG_LEVEL
      valueFrom:
        configMapKeyRef:
          name: app-config
          key: log_level
    # Mount as volume
    volumeMounts:
    - name: config-volume
      mountPath: /etc/config
  volumes:
  - name: config-volume
    configMap:
      name: app-config
      items:
      - key: nginx.conf
        path: nginx.conf
```

### 5. Secrets

```yaml
# secret.yaml - Sensitive data (base64 encoded)
apiVersion: v1
kind: Secret
metadata:
  name: db-credentials
type: Opaque
data:
  username: YWRtaW4=  # echo -n 'admin' | base64
  password: cGFzc3dvcmQxMjM=  # echo -n 'password123' | base64
  url: cG9zdGdyZXM6Ly9hZG1pbjpwYXNzd29yZDEyM0BkYi5leGFtcGxlLmNvbTo1NDMyL215ZGI=

---
# Use Secret in Pod
apiVersion: v1
kind: Pod
metadata:
  name: db-client
spec:
  containers:
  - name: client
    image: postgres:15
    env:
    - name: DB_USERNAME
      valueFrom:
        secretKeyRef:
          name: db-credentials
          key: username
    - name: DB_PASSWORD
      valueFrom:
        secretKeyRef:
          name: db-credentials
          key: password
    # Mount as files
    volumeMounts:
    - name: db-secret
      mountPath: /etc/secrets
      readOnly: true
  volumes:
  - name: db-secret
    secret:
      secretName: db-credentials
```

### 6. Ingress

```yaml
# ingress.yaml - HTTP/HTTPS routing
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - app.example.com
    secretName: app-tls-cert
  rules:
  - host: app.example.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: api-service
            port:
              number: 80
      - path: /
        pathType: Prefix
        backend:
          service:
            name: web-service
            port:
              number: 80
```

---

## Patterns

### Multi-Container Pods

```yaml
# Sidecar pattern - logging container
apiVersion: v1
kind: Pod
metadata:
  name: web-app-with-logging
spec:
  containers:
  # Main application container
  - name: web-app
    image: myapp:1.0
    ports:
    - containerPort: 8080
    volumeMounts:
    - name: shared-logs
      mountPath: /var/log/app

  # Sidecar logging container
  - name: log-shipper
    image: fluent/fluent-bit:2.0
    volumeMounts:
    - name: shared-logs
      mountPath: /var/log/app
    - name: fluent-bit-config
      mountPath: /fluent-bit/etc/

  volumes:
  - name: shared-logs
    emptyDir: {}
  - name: fluent-bit-config
    configMap:
      name: fluent-bit-config
```

### CronJobs

```yaml
# cronjob.yaml - Scheduled jobs
apiVersion: batch/v1
kind: CronJob
metadata:
  name: daily-backup
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM UTC
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 1
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: backup-tool:1.0
            env:
            - name: BACKUP_TARGET
              value: "s3://backups/daily"
            - name: AWS_ACCESS_KEY_ID
              valueFrom:
                secretKeyRef:
                  name: aws-credentials
                  key: access_key_id
            - name: AWS_SECRET_ACCESS_KEY
              valueFrom:
                secretKeyRef:
                  name: aws-credentials
                  key: secret_access_key
          restartPolicy: OnFailure
```

### Horizontal Pod Autoscaler

```yaml
# hpa.yaml - Auto-scaling based on metrics
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web-app-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web-app
  minReplicas: 2
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
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
```

### StatefulSets

```yaml
# statefulset.yaml - For stateful applications
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
spec:
  serviceName: postgres-headless
  replicas: 3
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15
        ports:
        - containerPort: 5432
          name: postgres
        env:
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgres-secret
              key: password
        volumeMounts:
        - name: postgres-data
          mountPath: /var/lib/postgresql/data
  volumeClaimTemplates:
  - metadata:
      name: postgres-data
    spec:
      accessModes: ["ReadWriteOnce"]
      storageClassName: "fast-ssd"
      resources:
        requests:
          storage: 10Gi
```

### NetworkPolicies

```yaml
# networkpolicy.yaml - Network segmentation
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-network-policy
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: web
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: database
    ports:
    - protocol: TCP
      port: 5432
  - to:  # Allow DNS
    - namespaceSelector: {}
    ports:
    - protocol: UDP
      port: 53
```

---

## Quick Reference

### kubectl Commands

```bash
# Cluster info
kubectl cluster-info
kubectl get nodes
kubectl top nodes

# Pods
kubectl get pods
kubectl get pods -o wide
kubectl describe pod <pod-name>
kubectl logs <pod-name>
kubectl logs <pod-name> -f  # Follow logs
kubectl logs <pod-name> -c <container-name>  # Multi-container
kubectl exec -it <pod-name> -- /bin/bash

# Deployments
kubectl get deployments
kubectl describe deployment <deployment-name>
kubectl rollout status deployment/<deployment-name>
kubectl rollout history deployment/<deployment-name>
kubectl rollout undo deployment/<deployment-name>
kubectl scale deployment/<deployment-name> --replicas=5

# Services
kubectl get services
kubectl describe service <service-name>
kubectl get endpoints

# ConfigMaps and Secrets
kubectl create configmap app-config --from-file=config.json
kubectl create secret generic db-creds --from-literal=password=secret123
kubectl get configmaps
kubectl get secrets
kubectl describe configmap <name>

# Apply manifests
kubectl apply -f deployment.yaml
kubectl apply -f ./manifests/  # Directory
kubectl delete -f deployment.yaml

# Port forwarding
kubectl port-forward pod/<pod-name> 8080:80
kubectl port-forward service/<service-name> 8080:80

# Labels and selectors
kubectl get pods --selector=app=web
kubectl label pods <pod-name> environment=production
kubectl get pods --show-labels

# Contexts and namespaces
kubectl config get-contexts
kubectl config use-context <context-name>
kubectl get namespaces
kubectl create namespace dev
kubectl config set-context --current --namespace=dev

# Debug
kubectl debug <pod-name> -it --image=busybox
kubectl get events
kubectl get all -n <namespace>
```

### Resource Requests and Limits

```yaml
resources:
  requests:
    memory: "256Mi"  # Guaranteed
    cpu: "500m"      # 0.5 CPU cores
  limits:
    memory: "512Mi"  # Maximum
    cpu: "1000m"     # 1 CPU core

# CPU units:
# 1 CPU = 1000m (millicores)
# 100m = 0.1 CPU
# 500m = 0.5 CPU

# Memory units:
# 128Mi = 128 Mebibytes
# 1Gi = 1 Gibibyte
```

---

## Anti-Patterns

### Critical Violations

```yaml
# ❌ NEVER: Run as root without necessity
spec:
  containers:
  - name: app
    image: myapp:1.0
    # No securityContext - runs as root

# ✅ CORRECT: Run as non-root user
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    fsGroup: 1000
  containers:
  - name: app
    image: myapp:1.0
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
```

```yaml
# ❌ NEVER: Use 'latest' tag in production
spec:
  containers:
  - name: app
    image: myapp:latest  # Unpredictable

# ✅ CORRECT: Use specific version tags
spec:
  containers:
  - name: app
    image: myapp:1.2.3  # Reproducible
    imagePullPolicy: IfNotPresent
```

```yaml
# ❌ NEVER: Ignore resource limits
spec:
  containers:
  - name: app
    image: myapp:1.0
    # No resources defined - can consume unlimited

# ✅ CORRECT: Always define resources
spec:
  containers:
  - name: app
    image: myapp:1.0
    resources:
      requests:
        memory: "256Mi"
        cpu: "250m"
      limits:
        memory: "512Mi"
        cpu: "500m"
```

### Common Mistakes

```yaml
# ❌ Don't expose secrets in environment variables unnecessarily
env:
- name: DB_PASSWORD
  value: "hardcoded-password"  # Visible in pod spec

# ✅ CORRECT: Use secrets and mount as files when possible
volumeMounts:
- name: db-secret
  mountPath: /etc/secrets
  readOnly: true
volumes:
- name: db-secret
  secret:
    secretName: db-credentials
```

```yaml
# ❌ Don't skip health checks
spec:
  containers:
  - name: app
    image: myapp:1.0
    # No liveness or readiness probes

# ✅ CORRECT: Always implement health checks
spec:
  containers:
  - name: app
    image: myapp:1.0
    livenessProbe:
      httpGet:
        path: /healthz
        port: 8080
      initialDelaySeconds: 30
      periodSeconds: 10
    readinessProbe:
      httpGet:
        path: /ready
        port: 8080
      initialDelaySeconds: 5
      periodSeconds: 5
```

```bash
# ❌ Don't apply without reviewing
kubectl apply -f manifest.yaml  # No validation

# ✅ CORRECT: Validate and review first
kubectl apply -f manifest.yaml --dry-run=client -o yaml
kubectl diff -f manifest.yaml
kubectl apply -f manifest.yaml
```

---

## Related Skills

**Infrastructure**:
- `terraform-patterns.md` - Infrastructure as Code for Kubernetes resources
- `infrastructure-security.md` - RBAC, network policies, security contexts
- `cost-optimization.md` - Resource sizing, cluster autoscaling

**Development**:
- `aws-serverless.md` - Alternative to container orchestration
- `cloudflare-workers.md` - Edge computing alternative

**Standards from CLAUDE.md**:
- Always define resource requests and limits
- Use specific image tags (not 'latest')
- Implement liveness and readiness probes
- Run containers as non-root users
- Use namespaces for multi-tenancy
- Apply network policies for security

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
