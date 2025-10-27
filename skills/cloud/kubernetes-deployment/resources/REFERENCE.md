# Kubernetes Deployment - Comprehensive Reference

## Table of Contents

1. [Kubernetes Fundamentals](#kubernetes-fundamentals)
2. [Pod Architecture](#pod-architecture)
3. [Deployments](#deployments)
4. [Services](#services)
5. [Rolling Updates and Rollbacks](#rolling-updates-and-rollbacks)
6. [Resource Management](#resource-management)
7. [Health Checks](#health-checks)
8. [Configuration Management](#configuration-management)
9. [Persistent Storage](#persistent-storage)
10. [Networking](#networking)
11. [Security](#security)
12. [Autoscaling](#autoscaling)
13. [GitOps Patterns](#gitops-patterns)
14. [Helm Package Management](#helm-package-management)
15. [Production Best Practices](#production-best-practices)
16. [Troubleshooting](#troubleshooting)
17. [Common Pitfalls](#common-pitfalls)

---

## Kubernetes Fundamentals

### Architecture Overview

Kubernetes is a container orchestration platform that manages containerized applications across a cluster of machines.

**Control Plane Components:**

```
┌─────────────────────────────────────────────────────────┐
│                    Control Plane                        │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   API       │  │   Scheduler  │  │  Controller  │  │
│  │   Server    │  │              │  │   Manager    │  │
│  └─────────────┘  └──────────────┘  └──────────────┘  │
│         │                                               │
│  ┌─────────────┐                                       │
│  │    etcd     │  (Distributed key-value store)        │
│  └─────────────┘                                       │
└─────────────────────────────────────────────────────────┘
         │
         │ (API calls)
         ▼
┌─────────────────────────────────────────────────────────┐
│                    Worker Nodes                         │
│  ┌───────────────────────────────────────────────────┐ │
│  │  Node 1                                           │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐       │ │
│  │  │  kubelet │  │  kube-   │  │ Container│       │ │
│  │  │          │  │  proxy   │  │ Runtime  │       │ │
│  │  └──────────┘  └──────────┘  └──────────┘       │ │
│  │       │                            │              │ │
│  │       └────────┬───────────────────┘              │ │
│  │                │                                   │ │
│  │         ┌──────▼─────┐  ┌──────────┐             │ │
│  │         │   Pod 1    │  │  Pod 2   │             │ │
│  │         │ Container  │  │Container │             │ │
│  │         └────────────┘  └──────────┘             │ │
│  └───────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

**API Server:**
- Central management entity
- All operations go through the API server
- RESTful interface over HTTP/HTTPS
- Authentication, authorization, and admission control
- Persists cluster state to etcd

**etcd:**
- Distributed, consistent key-value store
- Stores all cluster configuration and state
- Source of truth for cluster
- Supports watch operations for real-time updates
- Typically runs 3-5 replicas for HA

**Scheduler:**
- Watches for newly created Pods with no assigned node
- Selects optimal node based on:
  - Resource requirements and availability
  - Hardware/software/policy constraints
  - Affinity and anti-affinity specifications
  - Data locality
  - Deadlines

**Controller Manager:**
- Runs controller processes:
  - Node Controller: Notices and responds to node failures
  - Replication Controller: Maintains correct number of pods
  - Endpoints Controller: Populates Endpoints object
  - Service Account & Token Controllers: Create default accounts and API access tokens

**Cloud Controller Manager:**
- Embeds cloud-specific control logic
- Node Controller: Check cloud provider to determine if node has been deleted
- Route Controller: Set up routes in underlying cloud infrastructure
- Service Controller: Create, update, delete cloud provider load balancers

### Worker Node Components

**kubelet:**
- Primary node agent
- Registers node with API server
- Watches for PodSpecs from API server
- Ensures containers described in PodSpecs are running and healthy
- Reports node and pod status back to API server
- Executes container liveness and readiness probes

**kube-proxy:**
- Network proxy running on each node
- Maintains network rules for pod communication
- Implements Kubernetes Service abstraction
- Modes:
  - iptables (default): Uses iptables rules for traffic forwarding
  - IPVS: Uses Linux IPVS for better performance at scale
  - userspace: Older, legacy mode

**Container Runtime:**
- Software responsible for running containers
- Kubernetes supports multiple runtimes via CRI (Container Runtime Interface)
- Common runtimes:
  - containerd (recommended)
  - CRI-O
  - Docker Engine (via cri-dockerd shim)

### Kubernetes Objects

Every Kubernetes object has:

**Spec:**
- Desired state you provide
- What you want the object to be

**Status:**
- Current state of the object
- Provided and updated by Kubernetes

**Metadata:**
- Name: String identifier unique within namespace
- UID: Unique across time and space
- Namespace: Logical cluster partition
- Labels: Key-value pairs for organization
- Annotations: Non-identifying metadata

**Basic Object Structure:**

```yaml
apiVersion: apps/v1      # API version
kind: Deployment         # Object type
metadata:                # Object metadata
  name: my-app
  namespace: default
  labels:
    app: my-app
    version: v1
  annotations:
    description: "My application deployment"
spec:                    # Desired state
  replicas: 3
  selector:
    matchLabels:
      app: my-app
  template:
    # Pod template spec
status:                  # Current state (managed by Kubernetes)
  availableReplicas: 3
  readyReplicas: 3
```

### Namespaces

Namespaces provide scope for names and resource isolation.

**Default Namespaces:**

```bash
# Default namespaces
default              # Default namespace for objects with no namespace
kube-system          # Kubernetes system components
kube-public          # Publicly accessible data (even without authentication)
kube-node-lease      # Lease objects for node heartbeats
```

**Creating Namespaces:**

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: development
  labels:
    environment: dev
```

```bash
# Create namespace
kubectl create namespace development

# Set default namespace for context
kubectl config set-context --current --namespace=development

# List all namespaces
kubectl get namespaces

# Describe namespace
kubectl describe namespace development
```

**Resource Quotas:**

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: dev-quota
  namespace: development
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 20Gi
    limits.cpu: "20"
    limits.memory: 40Gi
    pods: "50"
    services: "10"
    persistentvolumeclaims: "10"
```

**Limit Ranges:**

```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: dev-limits
  namespace: development
spec:
  limits:
  - max:
      cpu: "2"
      memory: 4Gi
    min:
      cpu: 100m
      memory: 128Mi
    default:
      cpu: 500m
      memory: 512Mi
    defaultRequest:
      cpu: 200m
      memory: 256Mi
    type: Container
  - max:
      cpu: "4"
      memory: 8Gi
    min:
      cpu: 200m
      memory: 256Mi
    type: Pod
```

---

## Pod Architecture

### Pod Fundamentals

A Pod is the smallest deployable unit in Kubernetes:

- One or more containers that share:
  - Network namespace (IP address, ports)
  - IPC namespace
  - UTS namespace (hostname)
  - Storage volumes
- Scheduled together on the same node
- Atomic unit of scheduling

**Pod Lifecycle:**

```
┌─────────────┐
│   Pending   │ ← Pod accepted, waiting for scheduling/images
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Running   │ ← At least one container running
└──────┬──────┘
       │
       ├──────────┐
       ▼          ▼
┌──────────┐  ┌──────────┐
│Succeeded │  │  Failed  │ ← All containers terminated
└──────────┘  └──────────┘
       │          │
       ▼          ▼
┌──────────────────┐
│     Unknown      │ ← State cannot be determined
└──────────────────┘
```

**Pod Phases:**

- **Pending**: Pod accepted but not running yet
  - Waiting for scheduling
  - Pulling images
  - Starting containers

- **Running**: Pod bound to node, all containers created
  - At least one container running
  - Or container starting/restarting

- **Succeeded**: All containers terminated successfully
  - Will not restart
  - Typical for Jobs

- **Failed**: All containers terminated, at least one failed
  - Exited with non-zero status
  - Or terminated by system

- **Unknown**: Pod state cannot be obtained
  - Typically communication error with node

### Container States

Each container in a Pod has its own state:

**Waiting:**
```yaml
state:
  waiting:
    reason: ContainerCreating
    message: "Pulling image"
```

**Running:**
```yaml
state:
  running:
    startedAt: "2025-01-15T10:30:00Z"
```

**Terminated:**
```yaml
state:
  terminated:
    exitCode: 0
    reason: Completed
    startedAt: "2025-01-15T10:30:00Z"
    finishedAt: "2025-01-15T10:35:00Z"
```

### Pod Template

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: my-app-pod
  labels:
    app: my-app
    tier: frontend
spec:
  # Restart policy for all containers in pod
  restartPolicy: Always  # Always, OnFailure, Never

  # Service account for pod
  serviceAccountName: my-app-sa

  # Security context for pod (applies to all containers)
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    fsGroup: 2000
    seccompProfile:
      type: RuntimeDefault

  # DNS configuration
  dnsPolicy: ClusterFirst
  dnsConfig:
    nameservers:
      - 8.8.8.8
    searches:
      - my-app.svc.cluster.local
    options:
      - name: ndots
        value: "2"

  # Node selection
  nodeSelector:
    disktype: ssd

  # Affinity rules
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: kubernetes.io/zone
            operator: In
            values:
            - us-west-2a
            - us-west-2b
    podAntiAffinity:
      preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        podAffinityTerm:
          labelSelector:
            matchExpressions:
            - key: app
              operator: In
              values:
              - my-app
          topologyKey: kubernetes.io/hostname

  # Tolerations for taints
  tolerations:
  - key: "node.kubernetes.io/not-ready"
    operator: "Exists"
    effect: "NoExecute"
    tolerationSeconds: 300

  # Init containers run before app containers
  initContainers:
  - name: init-db
    image: busybox:1.35
    command: ['sh', '-c', 'until nslookup db-service; do echo waiting for db; sleep 2; done']

  # Application containers
  containers:
  - name: app
    image: my-app:v1.0.0
    imagePullPolicy: IfNotPresent  # Always, Never, IfNotPresent

    # Command and args override ENTRYPOINT and CMD
    command: ["/app/server"]
    args: ["--config", "/etc/config/app.yaml"]

    # Working directory
    workingDir: /app

    # Ports exposed by container
    ports:
    - name: http
      containerPort: 8080
      protocol: TCP
    - name: metrics
      containerPort: 9090
      protocol: TCP

    # Environment variables
    env:
    - name: ENV
      value: "production"
    - name: DB_HOST
      valueFrom:
        configMapKeyRef:
          name: app-config
          key: db.host
    - name: DB_PASSWORD
      valueFrom:
        secretKeyRef:
          name: app-secrets
          key: db.password
    - name: POD_NAME
      valueFrom:
        fieldRef:
          fieldPath: metadata.name
    - name: POD_IP
      valueFrom:
        fieldRef:
          fieldPath: status.podIP

    # Environment from ConfigMap/Secret
    envFrom:
    - configMapRef:
        name: app-config
    - secretRef:
        name: app-secrets

    # Resource requests and limits
    resources:
      requests:
        cpu: 100m
        memory: 128Mi
      limits:
        cpu: 500m
        memory: 512Mi

    # Volume mounts
    volumeMounts:
    - name: config
      mountPath: /etc/config
      readOnly: true
    - name: data
      mountPath: /var/lib/app
    - name: tmp
      mountPath: /tmp

    # Liveness probe
    livenessProbe:
      httpGet:
        path: /healthz
        port: http
        httpHeaders:
        - name: X-Custom-Header
          value: Awesome
      initialDelaySeconds: 30
      periodSeconds: 10
      timeoutSeconds: 5
      successThreshold: 1
      failureThreshold: 3

    # Readiness probe
    readinessProbe:
      httpGet:
        path: /ready
        port: http
      initialDelaySeconds: 5
      periodSeconds: 5
      timeoutSeconds: 3
      successThreshold: 1
      failureThreshold: 3

    # Startup probe
    startupProbe:
      httpGet:
        path: /startup
        port: http
      initialDelaySeconds: 0
      periodSeconds: 10
      timeoutSeconds: 3
      successThreshold: 1
      failureThreshold: 30

    # Lifecycle hooks
    lifecycle:
      postStart:
        exec:
          command: ["/bin/sh", "-c", "echo 'Container started' > /tmp/startup.log"]
      preStop:
        exec:
          command: ["/bin/sh", "-c", "sleep 15"]

    # Security context for container
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      runAsNonRoot: true
      runAsUser: 1000
      capabilities:
        drop:
        - ALL
        add:
        - NET_BIND_SERVICE

  # Volumes used by containers
  volumes:
  - name: config
    configMap:
      name: app-config
  - name: data
    persistentVolumeClaim:
      claimName: app-data
  - name: tmp
    emptyDir: {}

  # Image pull secrets
  imagePullSecrets:
  - name: registry-credentials

  # Hostname configuration
  hostname: my-app
  subdomain: apps

  # Host network mode
  hostNetwork: false
  hostPID: false
  hostIPC: false

  # Priority and preemption
  priorityClassName: high-priority

  # Topology spread constraints
  topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: kubernetes.io/zone
    whenUnsatisfiable: DoNotSchedule
    labelSelector:
      matchLabels:
        app: my-app
```

### Multi-Container Patterns

**Sidecar Pattern:**

```yaml
# Log aggregator sidecar
apiVersion: v1
kind: Pod
metadata:
  name: app-with-logging
spec:
  containers:
  - name: app
    image: my-app:v1
    volumeMounts:
    - name: logs
      mountPath: /var/log/app
  - name: log-aggregator
    image: fluentd:v1
    volumeMounts:
    - name: logs
      mountPath: /var/log/app
      readOnly: true
  volumes:
  - name: logs
    emptyDir: {}
```

**Ambassador Pattern:**

```yaml
# Proxy/ambassador for external service
apiVersion: v1
kind: Pod
metadata:
  name: app-with-proxy
spec:
  containers:
  - name: app
    image: my-app:v1
    env:
    - name: DATABASE_HOST
      value: localhost  # Connect to ambassador
    - name: DATABASE_PORT
      value: "5432"
  - name: db-proxy
    image: cloud-sql-proxy:v1
    command: ["/cloud_sql_proxy"]
    args:
    - "-instances=project:region:instance=tcp:5432"
```

**Adapter Pattern:**

```yaml
# Metrics adapter
apiVersion: v1
kind: Pod
metadata:
  name: app-with-adapter
spec:
  containers:
  - name: app
    image: my-app:v1
    # Exposes custom metrics format
  - name: metrics-adapter
    image: prometheus-adapter:v1
    # Converts to Prometheus format
    ports:
    - name: metrics
      containerPort: 9090
```

### Init Containers

Init containers run before app containers and must complete successfully:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: myapp-pod
spec:
  initContainers:
  # Wait for service to be available
  - name: wait-for-db
    image: busybox:1.35
    command: ['sh', '-c']
    args:
    - |
      until nslookup db-service.$(cat /var/run/secrets/kubernetes.io/serviceaccount/namespace).svc.cluster.local; do
        echo "Waiting for db-service"
        sleep 2
      done

  # Initialize database schema
  - name: init-schema
    image: postgres:14
    env:
    - name: PGHOST
      value: db-service
    - name: PGUSER
      valueFrom:
        secretKeyRef:
          name: db-creds
          key: username
    - name: PGPASSWORD
      valueFrom:
        secretKeyRef:
          name: db-creds
          key: password
    command: ['sh', '-c']
    args:
    - |
      psql -c "CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, name VARCHAR(100));"

  # Download configuration
  - name: fetch-config
    image: curlimages/curl:7.85.0
    command: ['sh', '-c']
    args:
    - |
      curl -o /config/app.yaml https://config-server/api/config
    volumeMounts:
    - name: config
      mountPath: /config

  containers:
  - name: app
    image: my-app:v1
    volumeMounts:
    - name: config
      mountPath: /etc/app

  volumes:
  - name: config
    emptyDir: {}
```

### Ephemeral Containers

For debugging running pods (requires feature gate):

```bash
# Add ephemeral debug container to running pod
kubectl debug -it pod-name --image=busybox:1.35 --target=container-name

# Debug with a copy of the pod
kubectl debug pod-name -it --copy-to=debug-pod --container=debug -- sh

# Debug node by running pod on node
kubectl debug node/node-name -it --image=ubuntu
```

---

## Deployments

### Deployment Fundamentals

Deployments manage ReplicaSets and provide declarative updates for Pods.

**Hierarchy:**

```
Deployment
  └── ReplicaSet (current)
        └── Pod 1
        └── Pod 2
        └── Pod 3
  └── ReplicaSet (old - for rollback)
```

**Basic Deployment:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
  labels:
    app: nginx
  annotations:
    kubernetes.io/change-cause: "Initial deployment"
spec:
  # Number of desired pods
  replicas: 3

  # How deployment should proceed
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1        # Max pods above desired count
      maxUnavailable: 1  # Max pods unavailable during update

  # Minimum time for pod to be considered ready
  minReadySeconds: 5

  # History limit for rollback
  revisionHistoryLimit: 10

  # Seconds to wait before considering deployment failed
  progressDeadlineSeconds: 600

  # Paused deployments won't reconcile
  paused: false

  # Selector to find pods to manage
  selector:
    matchLabels:
      app: nginx

  # Template for pods
  template:
    metadata:
      labels:
        app: nginx
        version: v1
    spec:
      containers:
      - name: nginx
        image: nginx:1.25
        ports:
        - name: http
          containerPort: 80
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 200m
            memory: 256Mi
        livenessProbe:
          httpGet:
            path: /
            port: http
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /
            port: http
          initialDelaySeconds: 5
          periodSeconds: 5
```

### Deployment Strategies

**RollingUpdate (Default):**

```yaml
spec:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 25%        # Can be percentage or absolute number
      maxUnavailable: 25%  # Can be percentage or absolute number
```

Process:
1. Create new ReplicaSet with 0 replicas
2. Scale up new ReplicaSet gradually
3. Scale down old ReplicaSet gradually
4. Maintain maxSurge and maxUnavailable constraints

**Recreate Strategy:**

```yaml
spec:
  strategy:
    type: Recreate
```

Process:
1. Scale down old ReplicaSet to 0
2. Wait for all old pods to terminate
3. Create new ReplicaSet and scale up
4. Results in downtime but ensures no version mixing

### Update Patterns

**Kubectl Apply:**

```bash
# Update deployment from file
kubectl apply -f deployment.yaml

# Update image
kubectl set image deployment/nginx-deployment nginx=nginx:1.26

# Edit deployment interactively
kubectl edit deployment/nginx-deployment

# Scale deployment
kubectl scale deployment/nginx-deployment --replicas=5

# Autoscale deployment
kubectl autoscale deployment/nginx-deployment --min=3 --max=10 --cpu-percent=80

# Pause deployment (stop reconciliation)
kubectl rollout pause deployment/nginx-deployment

# Resume deployment
kubectl rollout resume deployment/nginx-deployment
```

**Patch Updates:**

```bash
# Strategic merge patch
kubectl patch deployment nginx-deployment -p '{"spec":{"replicas":5}}'

# JSON patch
kubectl patch deployment nginx-deployment --type='json' -p='[{"op": "replace", "path": "/spec/replicas", "value":5}]'

# Merge patch
kubectl patch deployment nginx-deployment --type=merge -p '{"spec":{"template":{"spec":{"containers":[{"name":"nginx","image":"nginx:1.26"}]}}}}'
```

### Monitoring Deployments

```bash
# Watch deployment status
kubectl rollout status deployment/nginx-deployment

# View deployment history
kubectl rollout history deployment/nginx-deployment

# View specific revision
kubectl rollout history deployment/nginx-deployment --revision=2

# Get deployment details
kubectl describe deployment nginx-deployment

# Watch pods being updated
kubectl get pods -l app=nginx -w

# Get ReplicaSets
kubectl get rs -l app=nginx

# View events
kubectl get events --field-selector involvedObject.name=nginx-deployment
```

**Deployment Conditions:**

```yaml
status:
  conditions:
  - type: Available
    status: "True"
    reason: MinimumReplicasAvailable
    message: Deployment has minimum availability
  - type: Progressing
    status: "True"
    reason: NewReplicaSetAvailable
    message: ReplicaSet "nginx-deployment-5d59d67564" has successfully progressed
  observedGeneration: 2
  replicas: 3
  updatedReplicas: 3
  readyReplicas: 3
  availableReplicas: 3
```

### Advanced Selector Patterns

```yaml
spec:
  selector:
    # Match all labels
    matchLabels:
      app: nginx
      tier: frontend

    # Match expressions (more flexible)
    matchExpressions:
    - key: environment
      operator: In
      values:
      - production
      - staging
    - key: feature
      operator: NotIn
      values:
      - experimental
    - key: app
      operator: Exists
    - key: deprecated
      operator: DoesNotExist
```

Operators:
- `In`: Label value in set
- `NotIn`: Label value not in set
- `Exists`: Label key exists (value ignored)
- `DoesNotExist`: Label key doesn't exist
- `Gt`: Greater than (integer values)
- `Lt`: Less than (integer values)

### StatefulSets vs Deployments

Use StatefulSets when you need:

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: mysql
spec:
  serviceName: mysql  # Headless service for network identity
  replicas: 3
  selector:
    matchLabels:
      app: mysql
  template:
    metadata:
      labels:
        app: mysql
    spec:
      containers:
      - name: mysql
        image: mysql:8.0
        ports:
        - name: mysql
          containerPort: 3306
        volumeMounts:
        - name: data
          mountPath: /var/lib/mysql
  # Persistent storage for each pod
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: ["ReadWriteOnce"]
      storageClassName: fast-ssd
      resources:
        requests:
          storage: 10Gi
```

**StatefulSet Features:**
- Stable network identities: `mysql-0`, `mysql-1`, `mysql-2`
- Stable storage: Each pod gets its own PVC
- Ordered deployment and scaling
- Ordered rolling updates
- Ordered deletion

**When to Use:**
- Databases (MySQL, PostgreSQL, MongoDB)
- Distributed systems (Kafka, ZooKeeper, Elasticsearch)
- Applications requiring stable network identity
- Applications requiring stable persistent storage

### DaemonSets

Ensure a pod runs on every (or selected) node:

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluentd
spec:
  selector:
    matchLabels:
      app: fluentd
  template:
    metadata:
      labels:
        app: fluentd
    spec:
      # Tolerate node taints
      tolerations:
      - key: node-role.kubernetes.io/control-plane
        effect: NoSchedule

      containers:
      - name: fluentd
        image: fluentd:v1.16
        resources:
          limits:
            memory: 200Mi
          requests:
            cpu: 100m
            memory: 200Mi
        volumeMounts:
        - name: varlog
          mountPath: /var/log
        - name: varlibdockercontainers
          mountPath: /var/lib/docker/containers
          readOnly: true

      terminationGracePeriodSeconds: 30

      volumes:
      - name: varlog
        hostPath:
          path: /var/log
      - name: varlibdockercontainers
        hostPath:
          path: /var/lib/docker/containers
```

**DaemonSet Use Cases:**
- Log collection (Fluentd, Filebeat)
- Monitoring agents (Prometheus Node Exporter, Datadog)
- Storage daemons (Ceph, GlusterFS)
- Network plugins (Calico, Flannel)

---

## Services

### Service Types

**ClusterIP (Default):**

```yaml
apiVersion: v1
kind: Service
metadata:
  name: backend
spec:
  type: ClusterIP
  selector:
    app: backend
  ports:
  - name: http
    port: 80        # Port exposed by service
    targetPort: 8080  # Port on container
    protocol: TCP
  sessionAffinity: ClientIP  # Sticky sessions
  sessionAffinityConfig:
    clientIP:
      timeoutSeconds: 10800
```

Internal cluster IP only. Use for:
- Internal microservices communication
- Backend services not exposed externally

**NodePort:**

```yaml
apiVersion: v1
kind: Service
metadata:
  name: frontend
spec:
  type: NodePort
  selector:
    app: frontend
  ports:
  - name: http
    port: 80
    targetPort: 8080
    nodePort: 30080  # Port on node (30000-32767)
    protocol: TCP
```

Exposes service on each node's IP at static port. Use for:
- Development/testing
- Quick external access without load balancer
- Legacy systems expecting node IP:port

**LoadBalancer:**

```yaml
apiVersion: v1
kind: Service
metadata:
  name: web
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: nlb
    service.beta.kubernetes.io/aws-load-balancer-backend-protocol: http
spec:
  type: LoadBalancer
  selector:
    app: web
  ports:
  - name: http
    port: 80
    targetPort: 8080
  loadBalancerSourceRanges:
  - 192.168.1.0/24
  - 10.0.0.0/8
```

Provisions cloud provider load balancer. Use for:
- Production external access
- Layer 4 load balancing
- Automatic cloud integration

**ExternalName:**

```yaml
apiVersion: v1
kind: Service
metadata:
  name: database
spec:
  type: ExternalName
  externalName: db.example.com
```

Creates CNAME DNS record. Use for:
- External service references
- Migration from external to internal services
- Service aliases

### Headless Services

```yaml
apiVersion: v1
kind: Service
metadata:
  name: mysql
spec:
  clusterIP: None  # Headless
  selector:
    app: mysql
  ports:
  - name: mysql
    port: 3306
```

No cluster IP allocated. DNS returns pod IPs directly. Use for:
- StatefulSets (stable network identities)
- Custom load balancing
- Direct pod-to-pod communication
- Service discovery

### Service Discovery

**DNS:**

```bash
# Service DNS format
<service-name>.<namespace>.svc.cluster.local

# Examples
backend.default.svc.cluster.local
mysql.database.svc.cluster.local

# Headless service returns all pod IPs
mysql-0.mysql.default.svc.cluster.local
mysql-1.mysql.default.svc.cluster.local
```

**Environment Variables:**

```bash
# Kubernetes injects service info as env vars
BACKEND_SERVICE_HOST=10.0.0.1
BACKEND_SERVICE_PORT=80
BACKEND_PORT=tcp://10.0.0.1:80
BACKEND_PORT_80_TCP=tcp://10.0.0.1:80
BACKEND_PORT_80_TCP_PROTO=tcp
BACKEND_PORT_80_TCP_PORT=80
BACKEND_PORT_80_TCP_ADDR=10.0.0.1
```

### Endpoints

Services select pods and create Endpoints:

```yaml
apiVersion: v1
kind: Endpoints
metadata:
  name: backend
subsets:
- addresses:
  - ip: 10.244.1.5
    nodeName: node-1
    targetRef:
      kind: Pod
      name: backend-abc123
      namespace: default
  - ip: 10.244.2.7
    nodeName: node-2
    targetRef:
      kind: Pod
      name: backend-def456
      namespace: default
  ports:
  - name: http
    port: 8080
    protocol: TCP
```

**Manual Endpoints (for external services):**

```yaml
apiVersion: v1
kind: Service
metadata:
  name: external-db
spec:
  ports:
  - port: 3306
---
apiVersion: v1
kind: Endpoints
metadata:
  name: external-db
subsets:
- addresses:
  - ip: 192.168.1.100
  ports:
  - port: 3306
```

### Service Mesh Integration

**Istio Service:**

```yaml
apiVersion: v1
kind: Service
metadata:
  name: productpage
  labels:
    app: productpage
spec:
  ports:
  - port: 9080
    name: http
  selector:
    app: productpage
---
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: productpage
spec:
  hosts:
  - productpage
  http:
  - match:
    - headers:
        end-user:
          exact: jason
    route:
    - destination:
        host: productpage
        subset: v2
  - route:
    - destination:
        host: productpage
        subset: v1
```

**Linkerd Service:**

```yaml
apiVersion: v1
kind: Service
metadata:
  name: webapp
  annotations:
    config.linkerd.io/proxy-cpu-request: 100m
    config.linkerd.io/proxy-memory-request: 50Mi
spec:
  ports:
  - port: 80
    targetPort: 8080
  selector:
    app: webapp
```

---

## Rolling Updates and Rollbacks

### Update Process

**Update Triggers:**

```bash
# Image update
kubectl set image deployment/nginx nginx=nginx:1.26 --record

# Resource update
kubectl set resources deployment/nginx -c=nginx --limits=cpu=500m,memory=512Mi

# Environment variable update
kubectl set env deployment/nginx ENV=production

# From file
kubectl apply -f deployment.yaml
```

**Update Flow:**

```
Old ReplicaSet: 3 pods ████████████
New ReplicaSet: 0 pods

maxSurge: 1, maxUnavailable: 1

Step 1: Create 1 new pod
Old: 3 pods ████████████
New: 1 pod  ████

Step 2: Terminate 1 old pod
Old: 2 pods ████████
New: 1 pod  ████

Step 3: Create 1 new pod
Old: 2 pods ████████
New: 2 pods ████████

Step 4: Terminate 1 old pod
Old: 1 pod  ████
New: 2 pods ████████

Step 5: Create 1 new pod
Old: 1 pod  ████
New: 3 pods ████████████

Step 6: Terminate last old pod
Old: 0 pods
New: 3 pods ████████████ ✓ Complete
```

### Rollback

**Undo Deployment:**

```bash
# Rollback to previous revision
kubectl rollout undo deployment/nginx

# Rollback to specific revision
kubectl rollout undo deployment/nginx --to-revision=2

# Check rollout status
kubectl rollout status deployment/nginx

# View rollout history
kubectl rollout history deployment/nginx

# View specific revision details
kubectl rollout history deployment/nginx --revision=3
```

**Revision History:**

```bash
$ kubectl rollout history deployment/nginx
deployment.apps/nginx
REVISION  CHANGE-CAUSE
1         kubectl apply --filename=deployment.yaml
2         kubectl set image deployment/nginx nginx=nginx:1.25
3         kubectl set image deployment/nginx nginx=nginx:1.26

$ kubectl rollout history deployment/nginx --revision=2
deployment.apps/nginx with revision #2
Pod Template:
  Labels:       app=nginx
                pod-template-hash=5d59d67564
  Annotations:  kubernetes.io/change-cause: kubectl set image deployment/nginx nginx=nginx:1.25
  Containers:
   nginx:
    Image:      nginx:1.25
    Port:       80/TCP
```

### Progressive Delivery

**Canary Deployment:**

```yaml
# Stable version
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-stable
spec:
  replicas: 9
  selector:
    matchLabels:
      app: myapp
      version: stable
  template:
    metadata:
      labels:
        app: myapp
        version: stable
    spec:
      containers:
      - name: app
        image: myapp:v1.0
---
# Canary version (10% traffic)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-canary
spec:
  replicas: 1
  selector:
    matchLabels:
      app: myapp
      version: canary
  template:
    metadata:
      labels:
        app: myapp
        version: canary
    spec:
      containers:
      - name: app
        image: myapp:v2.0
---
# Service targets both versions
apiVersion: v1
kind: Service
metadata:
  name: myapp
spec:
  selector:
    app: myapp  # Matches both stable and canary
  ports:
  - port: 80
```

**Blue-Green Deployment:**

```yaml
# Blue (current) deployment
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
        image: myapp:v1.0
---
# Green (new) deployment
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
        image: myapp:v2.0
---
# Service initially points to blue
apiVersion: v1
kind: Service
metadata:
  name: myapp
spec:
  selector:
    app: myapp
    version: blue  # Switch to green after validation
  ports:
  - port: 80
```

Switch traffic:
```bash
# After validating green
kubectl patch service myapp -p '{"spec":{"selector":{"version":"green"}}}'

# Rollback if needed
kubectl patch service myapp -p '{"spec":{"selector":{"version":"blue"}}}'
```

### Automated Rollback

**Progressive Delivery with Flagger:**

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
  service:
    port: 80
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
    webhooks:
    - name: load-test
      url: http://flagger-loadtester/
      timeout: 5s
      metadata:
        cmd: "hey -z 1m -q 10 -c 2 http://myapp/"
```

Flagger automates:
1. Deploy canary version
2. Gradually shift traffic (10%, 20%, ..., 50%)
3. Measure metrics at each step
4. Promote if metrics good, rollback if bad
5. Cleanup old version

---

## Resource Management

### Resource Requests and Limits

**Requests:**
- Guaranteed resources
- Used for scheduling decisions
- Pod won't schedule if node can't satisfy requests

**Limits:**
- Maximum resources pod can use
- CPU: Throttled if exceeded
- Memory: OOMKilled if exceeded

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: resource-demo
spec:
  containers:
  - name: app
    image: my-app
    resources:
      requests:
        cpu: 500m      # 0.5 CPU cores
        memory: 512Mi  # 512 MiB
        ephemeral-storage: 2Gi
      limits:
        cpu: 1000m     # 1 CPU core
        memory: 1Gi    # 1 GiB
        ephemeral-storage: 4Gi
```

**CPU Units:**
- `1` = 1 CPU core (1 AWS vCPU, 1 GCP Core, 1 Azure vCore)
- `1000m` = 1000 millicores = 1 core
- `100m` = 0.1 core
- Can request fractional cores

**Memory Units:**
- `128974848` = 128 MB (bytes)
- `129e6` = 129 MB (scientific notation)
- `129M` = 129 megabytes
- `123Mi` = 123 mebibytes (1 Mi = 1024 Ki)
- `1Gi` = 1 gibibyte

### Quality of Service (QoS)

Kubernetes assigns QoS class based on requests/limits:

**Guaranteed (highest priority):**

```yaml
# All containers have equal requests and limits for CPU and memory
resources:
  requests:
    cpu: 500m
    memory: 512Mi
  limits:
    cpu: 500m
    memory: 512Mi
```

- Never throttled or evicted unless exceeding limits
- Use for critical workloads

**Burstable:**

```yaml
# At least one container has request < limit or missing limit
resources:
  requests:
    cpu: 250m
    memory: 256Mi
  limits:
    cpu: 1000m
    memory: 1Gi
```

- Throttled when resources contended
- Evicted if node runs out of resources
- Use for most workloads

**BestEffort (lowest priority):**

```yaml
# No requests or limits specified
resources: {}
```

- First to be throttled/evicted
- Use for batch jobs, non-critical workloads

### Resource Quotas

Limit aggregate resource consumption per namespace:

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: compute-resources
  namespace: development
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 20Gi
    requests.nvidia.com/gpu: "4"
    limits.cpu: "20"
    limits.memory: 40Gi
    limits.nvidia.com/gpu: "4"
```

**Object Count Quotas:**

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: object-counts
spec:
  hard:
    pods: "50"
    services: "10"
    services.loadbalancers: "2"
    services.nodeports: "5"
    persistentvolumeclaims: "10"
    requests.storage: 100Gi
    configmaps: "20"
    secrets: "20"
```

**Storage Class Quotas:**

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: storage-quotas
spec:
  hard:
    # SSD storage
    fast-ssd.storageclass.storage.k8s.io/requests.storage: 50Gi
    fast-ssd.storageclass.storage.k8s.io/persistentvolumeclaims: "5"
    # HDD storage
    slow-hdd.storageclass.storage.k8s.io/requests.storage: 500Gi
    slow-hdd.storageclass.storage.k8s.io/persistentvolumeclaims: "20"
```

### Limit Ranges

Set default requests/limits and constraints per namespace:

```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: cpu-mem-limit-range
  namespace: development
spec:
  limits:
  # Container limits
  - type: Container
    default:  # Default limits
      cpu: 500m
      memory: 512Mi
    defaultRequest:  # Default requests
      cpu: 200m
      memory: 256Mi
    max:  # Maximum allowed
      cpu: 2
      memory: 2Gi
    min:  # Minimum required
      cpu: 50m
      memory: 64Mi
    maxLimitRequestRatio:  # Max limit/request ratio
      cpu: 4
      memory: 4

  # Pod limits (sum of all containers)
  - type: Pod
    max:
      cpu: 4
      memory: 4Gi
    min:
      cpu: 100m
      memory: 128Mi

  # PVC limits
  - type: PersistentVolumeClaim
    max:
      storage: 50Gi
    min:
      storage: 1Gi
```

### Priority and Preemption

**Priority Classes:**

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority
value: 1000000
globalDefault: false
description: "Mission-critical workloads"
preemptionPolicy: PreemptLowerPriority  # or Never
---
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: medium-priority
value: 100000
globalDefault: false
description: "Production workloads"
---
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: low-priority
value: 10000
globalDefault: true
description: "Development and batch workloads"
```

**Using Priority:**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: critical-app
spec:
  priorityClassName: high-priority
  containers:
  - name: app
    image: critical-app:v1
```

**Preemption Process:**
1. Scheduler tries to schedule high-priority pod
2. If no resources available, looks for lower-priority pods to evict
3. Evicts lower-priority pods
4. Schedules high-priority pod
5. Evicted pods rescheduled when resources available

### Vertical Pod Autoscaling

Automatically adjust requests/limits:

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: my-app-vpa
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  updatePolicy:
    updateMode: "Auto"  # Off, Initial, Recreate, Auto
  resourcePolicy:
    containerPolicies:
    - containerName: app
      minAllowed:
        cpu: 100m
        memory: 128Mi
      maxAllowed:
        cpu: 2
        memory: 2Gi
      controlledResources: ["cpu", "memory"]
```

**Update Modes:**
- **Off**: Only recommendations, no updates
- **Initial**: Set resources on pod creation only
- **Recreate**: Update by recreating pods
- **Auto**: Update in-place (if supported) or recreate

---

## Health Checks

### Probe Types

**Liveness Probe:**
- Indicates if container is running
- Failed probe triggers container restart
- Use for deadlock detection

**Readiness Probe:**
- Indicates if container ready to serve traffic
- Failed probe removes pod from service endpoints
- Use for slow startup, dependencies

**Startup Probe:**
- Indicates if application started
- Disables liveness/readiness until passes
- Use for slow-starting applications

### Probe Mechanisms

**HTTP GET:**

```yaml
livenessProbe:
  httpGet:
    path: /healthz
    port: 8080
    httpHeaders:
    - name: X-Custom-Header
      value: Health-Check
    scheme: HTTP  # HTTP or HTTPS
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  successThreshold: 1
  failureThreshold: 3
```

**TCP Socket:**

```yaml
livenessProbe:
  tcpSocket:
    port: 8080
  initialDelaySeconds: 15
  periodSeconds: 20
```

**Exec Command:**

```yaml
livenessProbe:
  exec:
    command:
    - cat
    - /tmp/healthy
  initialDelaySeconds: 5
  periodSeconds: 5
```

**gRPC:**

```yaml
livenessProbe:
  grpc:
    port: 9090
    service: my.app.v1.Health  # Optional
  initialDelaySeconds: 10
  periodSeconds: 10
```

### Probe Configuration

```yaml
livenessProbe:
  httpGet:
    path: /healthz
    port: 8080

  # Seconds after container starts before probe
  initialDelaySeconds: 30

  # How often to perform probe
  periodSeconds: 10

  # Seconds after which probe times out
  timeoutSeconds: 5

  # Minimum consecutive successes for probe to be considered successful
  successThreshold: 1

  # Minimum consecutive failures for probe to be considered failed
  failureThreshold: 3

  # Optional: minimum time to consider pod "ready"
  # after container becomes ready
  minReadySeconds: 5
```

### Complete Health Check Example

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
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
      - name: app
        image: web-app:v1
        ports:
        - name: http
          containerPort: 8080

        # Startup probe: Allow 5 minutes for slow startup
        startupProbe:
          httpGet:
            path: /startup
            port: http
          initialDelaySeconds: 0
          periodSeconds: 10
          timeoutSeconds: 3
          successThreshold: 1
          failureThreshold: 30  # 30 * 10s = 5 minutes

        # Liveness probe: Detect deadlocks
        livenessProbe:
          httpGet:
            path: /healthz
            port: http
          initialDelaySeconds: 0  # Startup probe handles initial delay
          periodSeconds: 10
          timeoutSeconds: 5
          successThreshold: 1
          failureThreshold: 3  # Restart after 30s of failures

        # Readiness probe: Remove from service when not ready
        readinessProbe:
          httpGet:
            path: /ready
            port: http
          initialDelaySeconds: 0
          periodSeconds: 5
          timeoutSeconds: 3
          successThreshold: 1
          failureThreshold: 3  # Remove after 15s of failures

        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 512Mi
```

### Health Check Endpoints

**Example Implementation (Go):**

```go
package main

import (
    "net/http"
    "sync/atomic"
    "time"
)

var (
    isStarted = int32(0)
    isHealthy = int32(1)
    isReady   = int32(1)
)

func startupHandler(w http.ResponseWriter, r *http.Request) {
    if atomic.LoadInt32(&isStarted) == 1 {
        w.WriteHeader(http.StatusOK)
        w.Write([]byte("Started"))
    } else {
        w.WriteHeader(http.StatusServiceUnavailable)
        w.Write([]byte("Not started"))
    }
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
    if atomic.LoadInt32(&isHealthy) == 1 {
        w.WriteHeader(http.StatusOK)
        w.Write([]byte("Healthy"))
    } else {
        w.WriteHeader(http.StatusServiceUnavailable)
        w.Write([]byte("Unhealthy"))
    }
}

func readyHandler(w http.ResponseWriter, r *http.Request) {
    if atomic.LoadInt32(&isReady) == 1 {
        w.WriteHeader(http.StatusOK)
        w.Write([]byte("Ready"))
    } else {
        w.WriteHeader(http.StatusServiceUnavailable)
        w.Write([]byte("Not ready"))
    }
}

func main() {
    // Simulate startup
    go func() {
        time.Sleep(10 * time.Second)
        atomic.StoreInt32(&isStarted, 1)
    }()

    http.HandleFunc("/startup", startupHandler)
    http.HandleFunc("/healthz", healthHandler)
    http.HandleFunc("/ready", readyHandler)

    http.ListenAndServe(":8080", nil)
}
```

### Best Practices

1. **Always use readiness probes** for production
2. **Separate startup from liveness** for slow-starting apps
3. **Keep probe handlers lightweight** (< 1s response time)
4. **Don't check dependencies in liveness** (only internal health)
5. **Check dependencies in readiness** (database, cache, etc.)
6. **Use appropriate failure thresholds** (3 failures = ~30s for 10s period)
7. **Tune for your application** (startup time, request duration)
8. **Monitor probe failures** (indicates application issues)

---

## Configuration Management

### ConfigMaps

Store non-sensitive configuration data:

**Create ConfigMap:**

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: default
data:
  # Simple key-value
  ENV: production
  LOG_LEVEL: info

  # Multi-line value
  app.yaml: |
    server:
      port: 8080
      host: 0.0.0.0
    database:
      host: db.example.com
      port: 5432
      name: myapp

  # JSON configuration
  features.json: |
    {
      "feature_a": true,
      "feature_b": false,
      "beta_features": ["feature_c", "feature_d"]
    }
binaryData:
  # Binary data (base64 encoded)
  logo.png: iVBORw0KGgoAAAANSUhEUgAAA...
```

**From Files:**

```bash
# From file
kubectl create configmap app-config --from-file=config.yaml

# From directory
kubectl create configmap app-config --from-file=configs/

# From literal values
kubectl create configmap app-config \
  --from-literal=ENV=production \
  --from-literal=LOG_LEVEL=info

# From env file
kubectl create configmap app-config --from-env-file=.env
```

**Using ConfigMaps:**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app
spec:
  containers:
  - name: app
    image: myapp:v1

    # Environment variables from ConfigMap
    env:
    - name: ENV
      valueFrom:
        configMapKeyRef:
          name: app-config
          key: ENV
    - name: LOG_LEVEL
      valueFrom:
        configMapKeyRef:
          name: app-config
          key: LOG_LEVEL

    # All keys as environment variables
    envFrom:
    - configMapRef:
        name: app-config

    # Mount as volume
    volumeMounts:
    - name: config
      mountPath: /etc/config
      readOnly: true

    # Mount specific keys
    - name: app-yaml
      mountPath: /etc/app/app.yaml
      subPath: app.yaml
      readOnly: true

  volumes:
  - name: config
    configMap:
      name: app-config
  - name: app-yaml
    configMap:
      name: app-config
      items:
      - key: app.yaml
        path: app.yaml
```

### Secrets

Store sensitive data (base64 encoded at rest):

**Create Secret:**

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
type: Opaque
data:
  # Base64 encoded values
  username: YWRtaW4=
  password: cGFzc3dvcmQxMjM=
stringData:
  # Plain text (automatically encoded)
  api-key: my-secret-api-key-12345
```

**Secret Types:**

```yaml
# Generic/Opaque (default)
type: Opaque

# Docker registry credentials
type: kubernetes.io/dockerconfigjson
data:
  .dockerconfigjson: eyJhdXRocyI6eyJodHRwczovL...

# TLS certificate
type: kubernetes.io/tls
data:
  tls.crt: LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS...
  tls.key: LS0tLS1CRUdJTiBSU0EgUFJJVkFURSBLRVktLS...

# Service account token
type: kubernetes.io/service-account-token

# Basic authentication
type: kubernetes.io/basic-auth
stringData:
  username: admin
  password: password123

# SSH authentication
type: kubernetes.io/ssh-auth
data:
  ssh-privatekey: LS0tLS1CRUdJTiBPUEVOU1NIIFBSSVZBVEUgS0VZLUwtL...
```

**From CLI:**

```bash
# Generic secret
kubectl create secret generic app-secrets \
  --from-literal=username=admin \
  --from-literal=password=password123

# From files
kubectl create secret generic app-secrets \
  --from-file=ssh-privatekey=~/.ssh/id_rsa \
  --from-file=ssh-publickey=~/.ssh/id_rsa.pub

# Docker registry
kubectl create secret docker-registry regcred \
  --docker-server=docker.io \
  --docker-username=myuser \
  --docker-password=mypassword \
  --docker-email=myemail@example.com

# TLS secret
kubectl create secret tls tls-secret \
  --cert=path/to/cert.crt \
  --key=path/to/cert.key
```

**Using Secrets:**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app
spec:
  containers:
  - name: app
    image: myapp:v1

    # Environment variables from Secret
    env:
    - name: DB_USERNAME
      valueFrom:
        secretKeyRef:
          name: app-secrets
          key: username
    - name: DB_PASSWORD
      valueFrom:
        secretKeyRef:
          name: app-secrets
          key: password

    # All keys as environment variables
    envFrom:
    - secretRef:
        name: app-secrets

    # Mount as volume
    volumeMounts:
    - name: secrets
      mountPath: /etc/secrets
      readOnly: true

    # TLS certificate
    - name: tls
      mountPath: /etc/tls
      readOnly: true

  volumes:
  - name: secrets
    secret:
      secretName: app-secrets
      defaultMode: 0400  # Read-only for owner
  - name: tls
    secret:
      secretName: tls-secret
      items:
      - key: tls.crt
        path: cert.crt
      - key: tls.key
        path: cert.key

  # Docker registry secret
  imagePullSecrets:
  - name: regcred
```

### External Secrets

**External Secrets Operator:**

```yaml
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: aws-secretsmanager
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-west-2
      auth:
        secretRef:
          accessKeyIDSecretRef:
            name: aws-credentials
            key: access-key
          secretAccessKeySecretRef:
            name: aws-credentials
            key: secret-key
---
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: app-secrets
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secretsmanager
    kind: SecretStore
  target:
    name: app-secrets
    creationPolicy: Owner
  data:
  - secretKey: password
    remoteRef:
      key: prod/myapp/db-password
  - secretKey: api-key
    remoteRef:
      key: prod/myapp/api-key
```

**Sealed Secrets:**

```bash
# Install sealed-secrets controller
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/controller.yaml

# Install kubeseal CLI
brew install kubeseal

# Create sealed secret
kubectl create secret generic mysecret --from-literal=password=mypassword --dry-run=client -o yaml | \
  kubeseal -o yaml > sealed-secret.yaml

# Apply sealed secret (safe to commit)
kubectl apply -f sealed-secret.yaml

# Controller decrypts to regular secret
kubectl get secret mysecret
```

### Immutable ConfigMaps and Secrets

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config-v1
immutable: true
data:
  ENV: production
```

Benefits:
- Protects against accidental updates
- Improves cluster performance (no watches needed)
- Requires creating new ConfigMap/Secret for updates

---

## Persistent Storage

### Storage Classes

Define storage types with different properties:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd
  annotations:
    storageclass.kubernetes.io/is-default-class: "true"
provisioner: kubernetes.io/aws-ebs  # Cloud provider specific
parameters:
  type: gp3
  iopsPerGB: "50"
  throughput: "125"
  encrypted: "true"
  kmsKeyId: arn:aws:kms:us-west-2:123456789012:key/12345678-1234-1234-1234-123456789012
volumeBindingMode: WaitForFirstConsumer  # or Immediate
allowVolumeExpansion: true
reclaimPolicy: Delete  # Delete or Retain
mountOptions:
  - debug
  - noatime
```

**Common Provisioners:**

```yaml
# AWS EBS
provisioner: kubernetes.io/aws-ebs
parameters:
  type: gp3  # gp2, gp3, io1, io2, st1, sc1

# GCE Persistent Disk
provisioner: kubernetes.io/gce-pd
parameters:
  type: pd-standard  # pd-standard, pd-ssd, pd-balanced

# Azure Disk
provisioner: kubernetes.io/azure-disk
parameters:
  storageaccounttype: Premium_LRS  # Standard_LRS, Premium_LRS, StandardSSD_LRS, UltraSSD_LRS

# Ceph RBD
provisioner: kubernetes.io/rbd
parameters:
  monitors: 10.16.153.105:6789,10.16.153.106:6789
  adminId: kube
  adminSecretName: ceph-secret
  pool: kube
  userId: kube

# NFS
provisioner: example.com/nfs
parameters:
  server: nfs-server.example.com
  path: /exports
  readOnly: "false"

# Local storage
provisioner: kubernetes.io/no-provisioner
volumeBindingMode: WaitForFirstConsumer
```

### Persistent Volumes (PV)

Administrator-provisioned storage:

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: pv-nfs
spec:
  capacity:
    storage: 100Gi
  accessModes:
  - ReadWriteMany
  persistentVolumeReclaimPolicy: Retain  # Retain, Delete, Recycle
  storageClassName: nfs
  mountOptions:
  - hard
  - nfsvers=4.1
  nfs:
    path: /exports/data
    server: nfs-server.example.com
---
apiVersion: v1
kind: PersistentVolume
metadata:
  name: pv-local
spec:
  capacity:
    storage: 500Gi
  accessModes:
  - ReadWriteOnce
  persistentVolumeReclaimPolicy: Retain
  storageClassName: local-storage
  local:
    path: /mnt/disks/ssd1
  nodeAffinity:
    required:
      nodeSelectorTerms:
      - matchExpressions:
        - key: kubernetes.io/hostname
          operator: In
          values:
          - node-1
```

### Persistent Volume Claims (PVC)

User request for storage:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: app-data
spec:
  accessModes:
  - ReadWriteOnce  # RWO, ROX, RWX, RWOP
  resources:
    requests:
      storage: 10Gi
  storageClassName: fast-ssd

  # Optional: bind to specific PV
  volumeName: pv-0001

  # Optional: label selector
  selector:
    matchLabels:
      environment: production
    matchExpressions:
    - key: tier
      operator: In
      values:
      - frontend

  # Volume mode
  volumeMode: Filesystem  # or Block

  # Data source (clone/snapshot)
  dataSource:
    kind: VolumeSnapshot
    apiGroup: snapshot.storage.k8s.io
    name: snapshot-20230115
```

**Access Modes:**
- **ReadWriteOnce (RWO)**: Single node read-write
- **ReadOnlyMany (ROX)**: Multiple nodes read-only
- **ReadWriteMany (RWX)**: Multiple nodes read-write
- **ReadWriteOncePod (RWOP)**: Single pod read-write (1.27+)

**Using PVCs:**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app
spec:
  containers:
  - name: app
    image: myapp:v1
    volumeMounts:
    - name: data
      mountPath: /var/lib/app
  volumes:
  - name: data
    persistentVolumeClaim:
      claimName: app-data
```

### Volume Snapshots

```yaml
# VolumeSnapshotClass
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotClass
metadata:
  name: csi-aws-vsc
driver: ebs.csi.aws.com
deletionPolicy: Delete  # Delete or Retain
parameters:
  tagSpecification_1: "Name=Created by|Value=K8s CSI"
---
# VolumeSnapshot
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: app-data-snapshot
spec:
  volumeSnapshotClassName: csi-aws-vsc
  source:
    persistentVolumeClaimName: app-data
---
# Restore from snapshot
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: app-data-restored
spec:
  accessModes:
  - ReadWriteOnce
  storageClassName: fast-ssd
  resources:
    requests:
      storage: 10Gi
  dataSource:
    kind: VolumeSnapshot
    apiGroup: snapshot.storage.k8s.io
    name: app-data-snapshot
```

### Volume Expansion

```yaml
# StorageClass with expansion enabled
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: expandable
provisioner: kubernetes.io/aws-ebs
allowVolumeExpansion: true  # Enable expansion
---
# Expand PVC
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: app-data
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 20Gi  # Increased from 10Gi
  storageClassName: expandable
```

```bash
# Expand volume
kubectl patch pvc app-data -p '{"spec":{"resources":{"requests":{"storage":"20Gi"}}}}'

# Check expansion status
kubectl get pvc app-data -w
```

### StatefulSet with Storage

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: mysql
spec:
  serviceName: mysql
  replicas: 3
  selector:
    matchLabels:
      app: mysql
  template:
    metadata:
      labels:
        app: mysql
    spec:
      containers:
      - name: mysql
        image: mysql:8.0
        volumeMounts:
        - name: data
          mountPath: /var/lib/mysql
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: ["ReadWriteOnce"]
      storageClassName: fast-ssd
      resources:
        requests:
          storage: 10Gi
```

Creates PVCs automatically:
- `data-mysql-0` for pod `mysql-0`
- `data-mysql-1` for pod `mysql-1`
- `data-mysql-2` for pod `mysql-2`

---

## Networking

### Service Networking

**ClusterIP Implementation:**

```
Client Pod (10.244.1.5)
  ↓ DNS lookup: backend.default.svc.cluster.local
  ↓ Returns: 10.96.0.10 (Service ClusterIP)
  ↓ Connect to 10.96.0.10:80
  ↓ kube-proxy intercepts (iptables/IPVS rules)
  ↓ Load balances to endpoints
  ├→ Pod 1 (10.244.2.3:8080)
  ├→ Pod 2 (10.244.3.7:8080)
  └→ Pod 3 (10.244.1.9:8080)
```

**iptables Mode:**

```bash
# Example iptables rules created by kube-proxy
-A KUBE-SERVICES -d 10.96.0.10/32 -p tcp -m tcp --dport 80 -j KUBE-SVC-BACKEND
-A KUBE-SVC-BACKEND -m statistic --mode random --probability 0.33 -j KUBE-SEP-POD1
-A KUBE-SVC-BACKEND -m statistic --mode random --probability 0.50 -j KUBE-SEP-POD2
-A KUBE-SVC-BACKEND -j KUBE-SEP-POD3
-A KUBE-SEP-POD1 -p tcp -m tcp -j DNAT --to-destination 10.244.2.3:8080
-A KUBE-SEP-POD2 -p tcp -m tcp -j DNAT --to-destination 10.244.3.7:8080
-A KUBE-SEP-POD3 -p tcp -m tcp -j DNAT --to-destination 10.244.1.9:8080
```

### Ingress

HTTP/HTTPS routing to services:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app-ingress
  annotations:
    # Ingress class (if not using ingressClassName)
    kubernetes.io/ingress.class: nginx

    # SSL redirect
    nginx.ingress.kubernetes.io/ssl-redirect: "true"

    # Rate limiting
    nginx.ingress.kubernetes.io/limit-rps: "100"

    # CORS
    nginx.ingress.kubernetes.io/enable-cors: "true"
    nginx.ingress.kubernetes.io/cors-allow-origin: "https://example.com"

    # Authentication
    nginx.ingress.kubernetes.io/auth-type: basic
    nginx.ingress.kubernetes.io/auth-secret: basic-auth
    nginx.ingress.kubernetes.io/auth-realm: "Authentication Required"

    # Rewrite
    nginx.ingress.kubernetes.io/rewrite-target: /$2

    # Custom headers
    nginx.ingress.kubernetes.io/configuration-snippet: |
      more_set_headers "X-Frame-Options: DENY";
      more_set_headers "X-Content-Type-Options: nosniff";
spec:
  ingressClassName: nginx

  # TLS configuration
  tls:
  - hosts:
    - app.example.com
    - www.app.example.com
    secretName: tls-secret

  # Default backend
  defaultBackend:
    service:
      name: default-backend
      port:
        number: 80

  # Routing rules
  rules:
  - host: app.example.com
    http:
      paths:
      # Path prefix matching
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: api-service
            port:
              number: 80

      # Exact path matching
      - path: /health
        pathType: Exact
        backend:
          service:
            name: health-service
            port:
              name: http

      # Default path
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend-service
            port:
              number: 80

  # Multiple hosts
  - host: admin.app.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: admin-service
            port:
              number: 80
```

**Path Types:**
- **Prefix**: Matches URL path prefix (e.g., `/api` matches `/api/v1/users`)
- **Exact**: Matches exact URL path
- **ImplementationSpecific**: Depends on ingress controller

**Ingress Controllers:**

```bash
# NGINX Ingress Controller
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm install ingress-nginx ingress-nginx/ingress-nginx

# Traefik
helm repo add traefik https://helm.traefik.io/traefik
helm install traefik traefik/traefik

# HAProxy
helm repo add haproxytech https://haproxytech.github.io/helm-charts
helm install haproxy haproxytech/kubernetes-ingress

# AWS ALB Ingress Controller
helm repo add eks https://aws.github.io/eks-charts
helm install aws-load-balancer-controller eks/aws-load-balancer-controller
```

### Network Policies

Control traffic between pods:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-network-policy
spec:
  # Apply to pods with these labels
  podSelector:
    matchLabels:
      app: api

  # Policy types
  policyTypes:
  - Ingress
  - Egress

  # Ingress rules (incoming traffic)
  ingress:
  # Allow from frontend pods
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080

  # Allow from specific namespace
  - from:
    - namespaceSelector:
        matchLabels:
          environment: production
    ports:
    - protocol: TCP
      port: 8080

  # Allow from IP range
  - from:
    - ipBlock:
        cidr: 192.168.1.0/24
        except:
        - 192.168.1.5/32
    ports:
    - protocol: TCP
      port: 8080

  # Egress rules (outgoing traffic)
  egress:
  # Allow to database pods
  - to:
    - podSelector:
        matchLabels:
          app: database
    ports:
    - protocol: TCP
      port: 5432

  # Allow to external IPs
  - to:
    - ipBlock:
        cidr: 0.0.0.0/0
        except:
        - 169.254.169.254/32  # Block metadata service
    ports:
    - protocol: TCP
      port: 443

  # Allow DNS
  - to:
    - namespaceSelector:
        matchLabels:
          name: kube-system
    - podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
```

**Default Deny All:**

```yaml
# Deny all ingress
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
spec:
  podSelector: {}
  policyTypes:
  - Ingress
---
# Deny all egress
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-egress
spec:
  podSelector: {}
  policyTypes:
  - Egress
```

**Allow All:**

```yaml
# Allow all ingress
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-all-ingress
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  ingress:
  - {}
---
# Allow all egress
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-all-egress
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress:
  - {}
```

### DNS

**DNS Records:**

```bash
# Service: <service>.<namespace>.svc.cluster.local
backend.default.svc.cluster.local

# Headless service pod: <pod-name>.<service>.<namespace>.svc.cluster.local
mysql-0.mysql.default.svc.cluster.local

# Pod: <pod-ip-dashed>.<namespace>.pod.cluster.local
10-244-1-5.default.pod.cluster.local
```

**Custom DNS:**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: custom-dns
spec:
  dnsPolicy: None  # Default, ClusterFirst, ClusterFirstWithHostNet, None
  dnsConfig:
    nameservers:
    - 8.8.8.8
    - 8.8.4.4
    searches:
    - default.svc.cluster.local
    - svc.cluster.local
    - cluster.local
    - example.com
    options:
    - name: ndots
      value: "2"
    - name: edns0
  containers:
  - name: app
    image: myapp:v1
```

**CoreDNS Configuration:**

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: coredns
  namespace: kube-system
data:
  Corefile: |
    .:53 {
        errors
        health {
            lameduck 5s
        }
        ready
        kubernetes cluster.local in-addr.arpa ip6.arpa {
            pods insecure
            fallthrough in-addr.arpa ip6.arpa
            ttl 30
        }
        prometheus :9153
        forward . /etc/resolv.conf {
            max_concurrent 1000
        }
        cache 30
        loop
        reload
        loadbalance
    }

    example.com:53 {
        errors
        cache 30
        forward . 8.8.8.8 8.8.4.4
    }
```

---

## Security

### RBAC (Role-Based Access Control)

**Roles and ClusterRoles:**

```yaml
# Role: namespace-scoped
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pod-reader
  namespace: default
rules:
- apiGroups: [""]  # Core API group
  resources: ["pods"]
  verbs: ["get", "list", "watch"]
- apiGroups: [""]
  resources: ["pods/log"]
  verbs: ["get"]
---
# ClusterRole: cluster-wide
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: secret-reader
rules:
- apiGroups: [""]
  resources: ["secrets"]
  verbs: ["get", "list"]
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
```

**RoleBindings and ClusterRoleBindings:**

```yaml
# RoleBinding: Grant role in namespace
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: read-pods
  namespace: default
subjects:
- kind: User
  name: jane
  apiGroup: rbac.authorization.k8s.io
- kind: ServiceAccount
  name: my-app
  namespace: default
- kind: Group
  name: developers
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
---
# ClusterRoleBinding: Grant cluster role
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: read-secrets-global
subjects:
- kind: Group
  name: admins
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: ClusterRole
  name: secret-reader
  apiGroup: rbac.authorization.k8s.io
```

**Common Verbs:**
- `get`: Read specific resource
- `list`: List resources
- `watch`: Watch resources for changes
- `create`: Create new resources
- `update`: Update existing resources
- `patch`: Patch resources
- `delete`: Delete resources
- `deletecollection`: Delete collection of resources

**Service Accounts:**

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-app
  namespace: default
automountServiceAccountToken: true
imagePullSecrets:
- name: registry-creds
secrets:
- name: my-app-token
---
# Use in pod
apiVersion: v1
kind: Pod
metadata:
  name: my-app
spec:
  serviceAccountName: my-app
  containers:
  - name: app
    image: myapp:v1
```

### Pod Security Standards

**Pod Security Admission:**

```yaml
# Namespace labels for Pod Security Standards
apiVersion: v1
kind: Namespace
metadata:
  name: production
  labels:
    # Enforce level (blocks violations)
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.28

    # Audit level (logs violations)
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.28

    # Warn level (returns warnings)
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.28
```

**Security Levels:**

**Privileged:** Unrestricted (no restrictions)

**Baseline:** Minimally restrictive
- No host namespaces
- No privileged containers
- No hostPath volumes (except specific types)
- No host ports
- Limited capabilities

**Restricted:** Heavily restricted (production recommended)
- All Baseline requirements
- Must run as non-root
- No privilege escalation
- Drop ALL capabilities
- Read-only root filesystem
- Seccomp profile required

### Security Context

**Pod-level:**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: security-context-demo
spec:
  securityContext:
    # Run as non-root user
    runAsNonRoot: true
    runAsUser: 1000
    runAsGroup: 3000
    fsGroup: 2000
    fsGroupChangePolicy: "OnRootMismatch"

    # Seccomp profile
    seccompProfile:
      type: RuntimeDefault

    # SELinux options
    seLinuxOptions:
      level: "s0:c123,c456"

    # Supplemental groups
    supplementalGroups: [4000, 5000]

    # Sysctls
    sysctls:
    - name: net.ipv4.ip_local_port_range
      value: "32768 60999"

  containers:
  - name: app
    image: myapp:v1
    securityContext:
      # Override pod-level settings
      runAsUser: 2000

      # Capabilities
      capabilities:
        drop:
        - ALL
        add:
        - NET_BIND_SERVICE

      # Prevent privilege escalation
      allowPrivilegeEscalation: false

      # Read-only root filesystem
      readOnlyRootFilesystem: true

      # Privileged mode
      privileged: false

      # Proc mount
      procMount: Default
```

### Pod Security Policies (Deprecated)

Replaced by Pod Security Admission, but still used in older clusters:

```yaml
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: restricted
spec:
  privileged: false
  allowPrivilegeEscalation: false
  requiredDropCapabilities:
  - ALL
  volumes:
  - 'configMap'
  - 'emptyDir'
  - 'projected'
  - 'secret'
  - 'downwardAPI'
  - 'persistentVolumeClaim'
  hostNetwork: false
  hostIPC: false
  hostPID: false
  runAsUser:
    rule: 'MustRunAsNonRoot'
  seLinux:
    rule: 'RunAsAny'
  supplementalGroups:
    rule: 'RunAsAny'
  fsGroup:
    rule: 'RunAsAny'
  readOnlyRootFilesystem: true
```

### Network Security

**Encrypt Traffic with Istio:**

```yaml
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: production
spec:
  mtls:
    mode: STRICT  # PERMISSIVE, STRICT, DISABLE
---
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: allow-frontend
  namespace: production
spec:
  selector:
    matchLabels:
      app: api
  action: ALLOW
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/production/sa/frontend"]
    to:
    - operation:
        methods: ["GET", "POST"]
        paths: ["/api/v1/*"]
```

---

## Autoscaling

### Horizontal Pod Autoscaler (HPA)

Scale pods based on metrics:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: app-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  minReplicas: 2
  maxReplicas: 10

  # Metrics for scaling decisions
  metrics:
  # CPU utilization
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70

  # Memory utilization
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80

  # Custom metrics
  - type: Pods
    pods:
      metric:
        name: http_requests_per_second
      target:
        type: AverageValue
        averageValue: "1000"

  # External metrics
  - type: External
    external:
      metric:
        name: queue_depth
        selector:
          matchLabels:
            queue: jobs
      target:
        type: AverageValue
        averageValue: "30"

  # Scaling behavior
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
      - type: Pods
        value: 2
        periodSeconds: 60
      selectPolicy: Max
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
      - type: Pods
        value: 1
        periodSeconds: 60
      selectPolicy: Min
```

**Scaling Algorithm:**

```
desiredReplicas = ceil[currentReplicas * (currentMetricValue / targetMetricValue)]
```

### Vertical Pod Autoscaler (VPA)

Automatically adjust resource requests/limits:

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: app-vpa
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app

  # Update policy
  updatePolicy:
    updateMode: "Auto"  # Off, Initial, Recreate, Auto
    minReplicas: 2

  # Resource policy
  resourcePolicy:
    containerPolicies:
    - containerName: app
      minAllowed:
        cpu: 100m
        memory: 128Mi
      maxAllowed:
        cpu: 2
        memory: 2Gi
      controlledResources:
      - cpu
      - memory
      controlledValues: RequestsAndLimits  # RequestsOnly, RequestsAndLimits
      mode: Auto  # Off, Auto
```

**Recommendation Structure:**

```yaml
status:
  recommendation:
    containerRecommendations:
    - containerName: app
      lowerBound:
        cpu: 200m
        memory: 256Mi
      target:
        cpu: 500m
        memory: 512Mi
      uncappedTarget:
        cpu: 800m
        memory: 1Gi
      upperBound:
        cpu: 1
        memory: 2Gi
```

### Cluster Autoscaler

Scale cluster nodes based on demand:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cluster-autoscaler
  namespace: kube-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: cluster-autoscaler
  template:
    metadata:
      labels:
        app: cluster-autoscaler
    spec:
      serviceAccountName: cluster-autoscaler
      containers:
      - name: cluster-autoscaler
        image: k8s.gcr.io/autoscaling/cluster-autoscaler:v1.28.0
        command:
        - ./cluster-autoscaler
        - --cloud-provider=aws
        - --namespace=kube-system
        - --node-group-auto-discovery=asg:tag=k8s.io/cluster-autoscaler/enabled,k8s.io/cluster-autoscaler/my-cluster
        - --balance-similar-node-groups
        - --skip-nodes-with-system-pods=false
        - --scale-down-enabled=true
        - --scale-down-delay-after-add=10m
        - --scale-down-unneeded-time=10m
        - --scale-down-utilization-threshold=0.5
        resources:
          limits:
            cpu: 100m
            memory: 600Mi
          requests:
            cpu: 100m
            memory: 600Mi
```

**Node Pool Configuration (GKE):**

```bash
gcloud container clusters create my-cluster \
  --enable-autoscaling \
  --min-nodes=1 \
  --max-nodes=10 \
  --node-pool=default-pool
```

**Scale-down Conditions:**
1. Node utilization below threshold
2. All pods can be rescheduled elsewhere
3. No scale-down annotation preventing it
4. Minimum unneeded time elapsed

### KEDA (Kubernetes Event-Driven Autoscaling)

Scale based on external event sources:

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: app-scaledobject
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  minReplicaCount: 1
  maxReplicaCount: 100
  pollingInterval: 30
  cooldownPeriod: 300

  triggers:
  # RabbitMQ queue
  - type: rabbitmq
    metadata:
      host: amqp://rabbitmq.default.svc.cluster.local:5672
      queueName: jobs
      queueLength: "20"

  # Kafka topic
  - type: kafka
    metadata:
      bootstrapServers: kafka.default.svc.cluster.local:9092
      consumerGroup: my-consumer-group
      topic: events
      lagThreshold: "50"

  # Prometheus
  - type: prometheus
    metadata:
      serverAddress: http://prometheus.monitoring.svc.cluster.local:9090
      metricName: http_requests_total
      query: sum(rate(http_requests_total{job="my-app"}[1m]))
      threshold: "1000"

  # AWS SQS
  - type: aws-sqs-queue
    metadata:
      queueURL: https://sqs.us-west-2.amazonaws.com/123456789012/my-queue
      queueLength: "30"
      awsRegion: us-west-2
    authenticationRef:
      name: aws-credentials
```

---

## GitOps Patterns

### ArgoCD

**Installation:**

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Access UI
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Get admin password
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
```

**Application:**

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-app
  namespace: argocd
spec:
  project: default

  # Source
  source:
    repoURL: https://github.com/myorg/myapp
    targetRevision: HEAD
    path: k8s/production

    # Helm
    helm:
      releaseName: my-app
      values: |
        replicaCount: 3
        image:
          tag: v1.2.3
      valueFiles:
      - values-production.yaml

    # Kustomize
    kustomize:
      namePrefix: prod-
      images:
      - myapp:v1.2.3

  # Destination
  destination:
    server: https://kubernetes.default.svc
    namespace: production

  # Sync policy
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
      allowEmpty: false
    syncOptions:
    - CreateNamespace=true
    - PrunePropagationPolicy=foreground
    - PruneLast=true
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m

  # Health check
  ignoreDifferences:
  - group: apps
    kind: Deployment
    jsonPointers:
    - /spec/replicas
```

**AppProject:**

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: production
  namespace: argocd
spec:
  description: Production applications

  # Allowed source repositories
  sourceRepos:
  - https://github.com/myorg/*
  - https://charts.helm.sh/stable

  # Allowed destinations
  destinations:
  - namespace: production
    server: https://kubernetes.default.svc
  - namespace: monitoring
    server: https://kubernetes.default.svc

  # Allowed resource types
  clusterResourceWhitelist:
  - group: '*'
    kind: '*'

  namespaceResourceBlacklist:
  - group: ''
    kind: ResourceQuota
  - group: ''
    kind: LimitRange

  # Allowed RBAC subjects
  roles:
  - name: deployer
    description: Can sync applications
    policies:
    - p, proj:production:deployer, applications, sync, production/*, allow
    groups:
    - deployers
```

### Flux

**Installation:**

```bash
# Install Flux CLI
brew install fluxcd/tap/flux

# Bootstrap Flux
flux bootstrap github \
  --owner=myorg \
  --repository=fleet-infra \
  --branch=main \
  --path=clusters/production \
  --personal
```

**GitRepository:**

```yaml
apiVersion: source.toolkit.fluxcd.io/v1
kind: GitRepository
metadata:
  name: my-app
  namespace: flux-system
spec:
  interval: 1m
  url: https://github.com/myorg/myapp
  ref:
    branch: main
  secretRef:
    name: git-credentials
```

**Kustomization:**

```yaml
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: my-app
  namespace: flux-system
spec:
  interval: 5m
  path: ./k8s/production
  prune: true
  sourceRef:
    kind: GitRepository
    name: my-app
  healthChecks:
  - apiVersion: apps/v1
    kind: Deployment
    name: my-app
    namespace: production
  timeout: 2m
  wait: true
```

**HelmRelease:**

```yaml
apiVersion: helm.toolkit.fluxcd.io/v2beta1
kind: HelmRelease
metadata:
  name: my-app
  namespace: flux-system
spec:
  interval: 5m
  chart:
    spec:
      chart: my-app
      version: 1.2.3
      sourceRef:
        kind: HelmRepository
        name: my-charts
  values:
    replicaCount: 3
    image:
      tag: v1.2.3
  install:
    remediation:
      retries: 3
  upgrade:
    remediation:
      retries: 3
```

---

## Helm Package Management

### Helm Chart Structure

```
my-app/
├── Chart.yaml          # Chart metadata
├── values.yaml         # Default values
├── values-dev.yaml     # Environment-specific values
├── values-prod.yaml
├── charts/             # Chart dependencies
├── templates/          # Kubernetes manifests
│   ├── NOTES.txt       # Post-install notes
│   ├── _helpers.tpl    # Template helpers
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   ├── configmap.yaml
│   ├── secret.yaml
│   ├── hpa.yaml
│   └── tests/
│       └── test-connection.yaml
└── .helmignore         # Ignore patterns
```

**Chart.yaml:**

```yaml
apiVersion: v2
name: my-app
description: My application Helm chart
type: application
version: 1.2.3
appVersion: "v1.2.3"
keywords:
  - web
  - api
home: https://example.com
sources:
  - https://github.com/myorg/myapp
maintainers:
  - name: John Doe
    email: john@example.com
dependencies:
  - name: postgresql
    version: 12.0.0
    repository: https://charts.bitnami.com/bitnami
    condition: postgresql.enabled
  - name: redis
    version: 17.0.0
    repository: https://charts.bitnami.com/bitnami
    condition: redis.enabled
```

**values.yaml:**

```yaml
# Default values for my-app

replicaCount: 3

image:
  repository: myapp
  pullPolicy: IfNotPresent
  tag: ""  # Defaults to Chart.appVersion

imagePullSecrets: []
nameOverride: ""
fullnameOverride: ""

serviceAccount:
  create: true
  annotations: {}
  name: ""

podAnnotations: {}

podSecurityContext:
  runAsNonRoot: true
  runAsUser: 1000
  fsGroup: 2000

securityContext:
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities:
    drop:
    - ALL

service:
  type: ClusterIP
  port: 80

ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: app.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: app-tls
      hosts:
        - app.example.com

resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 100m
    memory: 128Mi

autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 80
  targetMemoryUtilizationPercentage: 80

nodeSelector: {}

tolerations: []

affinity: {}

postgresql:
  enabled: true
  auth:
    username: myapp
    password: changeme
    database: myapp
  primary:
    persistence:
      size: 10Gi

redis:
  enabled: true
  auth:
    enabled: true
    password: changeme
  master:
    persistence:
      size: 8Gi
```

**templates/deployment.yaml:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "my-app.fullname" . }}
  labels:
    {{- include "my-app.labels" . | nindent 4 }}
spec:
  {{- if not .Values.autoscaling.enabled }}
  replicas: {{ .Values.replicaCount }}
  {{- end }}
  selector:
    matchLabels:
      {{- include "my-app.selectorLabels" . | nindent 6 }}
  template:
    metadata:
      annotations:
        checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}
        {{- with .Values.podAnnotations }}
        {{- toYaml . | nindent 8 }}
        {{- end }}
      labels:
        {{- include "my-app.selectorLabels" . | nindent 8 }}
    spec:
      {{- with .Values.imagePullSecrets }}
      imagePullSecrets:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      serviceAccountName: {{ include "my-app.serviceAccountName" . }}
      securityContext:
        {{- toYaml .Values.podSecurityContext | nindent 8 }}
      containers:
      - name: {{ .Chart.Name }}
        securityContext:
          {{- toYaml .Values.securityContext | nindent 12 }}
        image: "{{ .Values.image.repository }}:{{ .Values.image.tag | default .Chart.AppVersion }}"
        imagePullPolicy: {{ .Values.image.pullPolicy }}
        ports:
        - name: http
          containerPort: 8080
          protocol: TCP
        livenessProbe:
          httpGet:
            path: /healthz
            port: http
        readinessProbe:
          httpGet:
            path: /ready
            port: http
        resources:
          {{- toYaml .Values.resources | nindent 12 }}
        env:
        - name: DATABASE_URL
          value: "postgresql://{{ .Values.postgresql.auth.username }}:{{ .Values.postgresql.auth.password }}@{{ include "my-app.fullname" . }}-postgresql:5432/{{ .Values.postgresql.auth.database }}"
      {{- with .Values.nodeSelector }}
      nodeSelector:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      {{- with .Values.affinity }}
      affinity:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      {{- with .Values.tolerations }}
      tolerations:
        {{- toYaml . | nindent 8 }}
      {{- end }}
```

**templates/_helpers.tpl:**

```yaml
{{/*
Expand the name of the chart.
*/}}
{{- define "my-app.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "my-app.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "my-app.labels" -}}
helm.sh/chart: {{ include "my-app.chart" . }}
{{ include "my-app.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "my-app.selectorLabels" -}}
app.kubernetes.io/name: {{ include "my-app.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "my-app.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "my-app.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}
```

### Helm Commands

```bash
# Create new chart
helm create my-app

# Validate chart
helm lint my-app/

# Template chart (dry-run)
helm template my-app my-app/ --values my-app/values-prod.yaml

# Install chart
helm install my-app my-app/ --namespace production --create-namespace

# Install with values override
helm install my-app my-app/ \
  --set replicaCount=5 \
  --set image.tag=v1.2.3 \
  --values my-app/values-prod.yaml

# Upgrade release
helm upgrade my-app my-app/ --namespace production

# Rollback release
helm rollback my-app 1

# Uninstall release
helm uninstall my-app --namespace production

# List releases
helm list --all-namespaces

# Get release values
helm get values my-app

# Get release manifest
helm get manifest my-app

# Show chart dependencies
helm dependency list my-app/

# Update dependencies
helm dependency update my-app/

# Package chart
helm package my-app/

# Push to registry
helm push my-app-1.2.3.tgz oci://registry.example.com/charts
```

---

## Production Best Practices

### Resource Configuration

1. **Always set resource requests and limits**
2. **Use appropriate QoS class** (Guaranteed for critical, Burstable for most)
3. **Size correctly** (profile actual usage, add 20% buffer)
4. **Consider autoscaling** (HPA for traffic-driven, VPA for resource optimization)

### Health Checks

1. **Always use readiness probes** in production
2. **Use startup probes** for slow-starting applications
3. **Tune probe parameters** based on application behavior
4. **Separate liveness from readiness** logic
5. **Monitor probe failures** as application health indicators

### High Availability

1. **Run multiple replicas** (minimum 3 for critical services)
2. **Use pod anti-affinity** to spread across nodes/zones
3. **Set PodDisruptionBudgets** to prevent simultaneous eviction
4. **Use topologySpreadConstraints** for even distribution
5. **Configure appropriate replica counts** for traffic patterns

### Security

1. **Run as non-root** user
2. **Use read-only root filesystem**
3. **Drop ALL capabilities** unless specifically needed
4. **Disable privilege escalation**
5. **Use NetworkPolicies** to restrict traffic
6. **Enable RBAC** and principle of least privilege
7. **Scan images** for vulnerabilities
8. **Rotate secrets** regularly
9. **Use Pod Security Standards** (Restricted level)

### Configuration Management

1. **Externalize configuration** (ConfigMaps, Secrets)
2. **Use immutable ConfigMaps/Secrets** in production
3. **Version configuration** with application
4. **Separate environment-specific** values
5. **Never commit secrets** to Git

### Monitoring and Observability

1. **Expose metrics** (Prometheus format)
2. **Implement structured logging**
3. **Add distributed tracing** (OpenTelemetry)
4. **Monitor resource usage**
5. **Set up alerts** for critical issues
6. **Use dashboards** for visibility

### Deployment Strategy

1. **Use rolling updates** with appropriate parameters
2. **Test in staging** environment first
3. **Implement progressive delivery** (canary, blue-green)
4. **Have rollback plan**
5. **Monitor during rollout**
6. **Use deployment tools** (ArgoCD, Flux)

### Backup and Disaster Recovery

1. **Backup persistent data** regularly
2. **Test restore procedures**
3. **Document recovery steps**
4. **Use multiple availability zones**
5. **Have cross-region replication** for critical data

### Cost Optimization

1. **Right-size resources** (use VPA recommendations)
2. **Use node autoscaling**
3. **Implement pod preemption** for batch workloads
4. **Use spot instances** for fault-tolerant workloads
5. **Monitor and eliminate waste**

---

## Troubleshooting

### Common Issues

**Pods Not Starting:**

```bash
# Check pod status
kubectl get pods
kubectl describe pod <pod-name>

# Common issues:
# - ImagePullBackOff: Check image name, registry credentials
# - CrashLoopBackOff: Check logs, readiness probe
# - Pending: Check resources, node capacity, taints/tolerations

# Check events
kubectl get events --sort-by='.lastTimestamp'

# Check logs
kubectl logs <pod-name>
kubectl logs <pod-name> --previous  # Previous container instance

# Check resource constraints
kubectl top nodes
kubectl top pods

# Debug with ephemeral container
kubectl debug <pod-name> -it --image=busybox --target=<container-name>
```

**Service Not Accessible:**

```bash
# Check service
kubectl get svc <service-name>
kubectl describe svc <service-name>

# Check endpoints
kubectl get endpoints <service-name>

# Test DNS resolution
kubectl run -it --rm debug --image=busybox --restart=Never -- nslookup <service-name>

# Test connectivity
kubectl run -it --rm debug --image=curlimages/curl --restart=Never -- curl http://<service-name>

# Check network policies
kubectl get networkpolicies
kubectl describe networkpolicy <policy-name>
```

**Deployment Not Rolling Out:**

```bash
# Check deployment status
kubectl rollout status deployment/<deployment-name>

# Check deployment events
kubectl describe deployment <deployment-name>

# Check replica sets
kubectl get rs -l app=<app-name>

# Check for failed pods
kubectl get pods -l app=<app-name> --field-selector=status.phase!=Running

# Pause/resume deployment
kubectl rollout pause deployment/<deployment-name>
kubectl rollout resume deployment/<deployment-name>
```

### Debug Commands

```bash
# Get cluster info
kubectl cluster-info
kubectl version

# Get node details
kubectl get nodes
kubectl describe node <node-name>
kubectl top nodes

# Get all resources
kubectl get all --all-namespaces

# Get resource usage
kubectl top pods --all-namespaces
kubectl top nodes

# Port forward to pod
kubectl port-forward <pod-name> 8080:80

# Execute command in pod
kubectl exec -it <pod-name> -- /bin/sh

# Copy files to/from pod
kubectl cp <local-path> <pod-name>:<pod-path>
kubectl cp <pod-name>:<pod-path> <local-path>

# View API resources
kubectl api-resources
kubectl api-versions

# Explain resource
kubectl explain pod.spec.containers

# Get raw YAML
kubectl get pod <pod-name> -o yaml

# Diff changes
kubectl diff -f deployment.yaml
```

---

## Common Pitfalls

### Anti-Patterns

1. **Running as root**
   - Security risk
   - Use runAsNonRoot and runAsUser

2. **No resource limits**
   - Noisy neighbor problem
   - Always set limits

3. **No health checks**
   - Service routes to unhealthy pods
   - Always use readiness probes

4. **Hardcoded configuration**
   - Can't change without rebuild
   - Use ConfigMaps and Secrets

5. **Single replica in production**
   - No high availability
   - Use multiple replicas with anti-affinity

6. **Missing PodDisruptionBudget**
   - All pods can be evicted simultaneously
   - Set appropriate minAvailable

7. **No monitoring/logging**
   - Can't diagnose issues
   - Implement observability from start

8. **Latest image tag**
   - Non-reproducible deployments
   - Use specific version tags

9. **No resource requests**
   - Poor scheduling decisions
   - Always set requests

10. **Storing state in containers**
    - Data loss on restart
    - Use PersistentVolumes

11. **No network policies**
    - Unrestricted pod communication
    - Implement least-privilege networking

12. **Deploying to main branch directly**
    - No testing before production
    - Use GitOps with proper branching

### Performance Issues

1. **Insufficient resources**
   - Solution: Increase limits, use HPA

2. **Slow readiness probe**
   - Solution: Optimize probe endpoint, increase timeout

3. **Too many small pods**
   - Solution: Right-size pods, use node affinity

4. **Network latency**
   - Solution: Use headless services, optimize service mesh

5. **Disk I/O bottleneck**
   - Solution: Use faster storage class, optimize queries

### Security Issues

1. **Privileged containers**
   - Solution: Drop privileges, use specific capabilities

2. **Secrets in environment variables**
   - Solution: Mount secrets as volumes

3. **No network segmentation**
   - Solution: Implement NetworkPolicies

4. **Running latest images**
   - Solution: Pin versions, scan for vulnerabilities

5. **Overly permissive RBAC**
   - Solution: Apply principle of least privilege

---

This reference covers the fundamental concepts and patterns for Kubernetes deployment. For production use, always test configurations in non-production environments first, implement proper monitoring, and follow security best practices.
