---
name: debugging-container-debugging
description: Debugging applications inside containers using docker exec, kubectl debug, ephemeral containers, and distroless debugging techniques
---

# Container Debugging

**Scope**: Docker debugging, Kubernetes ephemeral containers, kubectl debug, debug vs production images, distroless debugging, sidecar patterns

**Lines**: 410

**Last Updated**: 2025-10-26

---

## When to Use This Skill

Use this skill when:
- Debugging applications running in Docker containers
- Troubleshooting Kubernetes pods without debug tools
- Investigating networking issues in containerized environments
- Analyzing resource constraints (CPU, memory limits)
- Debugging distroless or minimal container images
- Inspecting container filesystem and processes
- Troubleshooting container startup failures
- Debugging multi-container pods (sidecars, init containers)

**Don't use** for:
- Local development debugging (use IDE debuggers)
- Applications running directly on host (use standard debugging)
- Simple logging issues (check container logs first)

---

## Core Concepts

### Container Debugging Challenges

**Why containers are harder to debug**:
1. **Immutable infrastructure**: Can't install debug tools at runtime
2. **Minimal images**: Production images lack shells, utilities
3. **Ephemeral nature**: Containers restart, losing state
4. **Network isolation**: Different networking namespace
5. **Resource limits**: CPU/memory constraints affect behavior

### Debug Image vs Production Image

```dockerfile
# Production image: Minimal, secure
FROM gcr.io/distroless/python3-debian11
COPY app.py /app/
CMD ["/app/app.py"]
# No shell, no package manager, no debug tools!

# Debug image: Full tooling
FROM python:3.11-slim
RUN apt-get update && apt-get install -y \
    curl vim strace tcpdump netcat
COPY app.py /app/
CMD ["/app/app.py"]
```

### Container Debugging Techniques

```
Layer 1: Non-invasive (read-only inspection)
├─ docker logs / kubectl logs
├─ docker inspect / kubectl describe
└─ docker stats / kubectl top

Layer 2: Shell access
├─ docker exec -it <container> /bin/sh
├─ kubectl exec -it <pod> -- /bin/sh
└─ nsenter (host-level container access)

Layer 3: Ephemeral debugging
├─ kubectl debug (ephemeral container)
├─ Debug sidecar containers
└─ docker run with shared volumes

Layer 4: Advanced diagnostics
├─ strace (syscall tracing)
├─ tcpdump (network analysis)
└─ gdb (attach to running process)
```

---

## Patterns

### Pattern 1: Docker Container Debugging

```bash
# 1. Check container status
docker ps -a  # Show all containers (including stopped)
docker inspect <container_id>  # Full container metadata

# 2. View logs
docker logs <container_id>
docker logs -f <container_id>  # Follow logs
docker logs --tail 100 <container_id>  # Last 100 lines
docker logs --since 10m <container_id>  # Last 10 minutes

# 3. Execute commands inside container
docker exec -it <container_id> /bin/sh
docker exec -it <container_id> /bin/bash  # If bash available

# 4. Inspect filesystem
docker exec <container_id> ls -la /app
docker exec <container_id> cat /app/config.yaml

# 5. Check resource usage
docker stats <container_id>  # Real-time stats
docker top <container_id>    # Running processes

# 6. Copy files from container
docker cp <container_id>:/app/logs/error.log ./error.log

# 7. Attach to running container (see stdout)
docker attach <container_id>

# 8. Run debug tools (if not in image)
# Mount debug tools from host
docker run -it --pid=container:<container_id> \
  --net=container:<container_id> \
  --cap-add sys_admin \
  nicolaka/netshoot
```

### Pattern 2: Kubernetes Pod Debugging

```bash
# 1. Check pod status
kubectl get pods -n <namespace>
kubectl describe pod <pod_name> -n <namespace>

# 2. View logs
kubectl logs <pod_name> -n <namespace>
kubectl logs <pod_name> -c <container_name> -n <namespace>  # Multi-container pod
kubectl logs -f <pod_name> -n <namespace>  # Follow logs
kubectl logs --previous <pod_name>  # Previous container (after crash)

# 3. Execute commands in pod
kubectl exec -it <pod_name> -n <namespace> -- /bin/sh
kubectl exec -it <pod_name> -c <container_name> -- /bin/sh  # Specific container

# 4. Port forwarding (access pod from localhost)
kubectl port-forward <pod_name> 8080:80 -n <namespace>

# 5. Check resource usage
kubectl top pod <pod_name> -n <namespace>
kubectl top pods -n <namespace> --sort-by=memory

# 6. Copy files from pod
kubectl cp <namespace>/<pod_name>:/app/config.yaml ./config.yaml
kubectl cp <namespace>/<pod_name>:/app/logs ./logs -c <container_name>

# 7. View events
kubectl get events -n <namespace> --sort-by='.lastTimestamp'
kubectl describe pod <pod_name> -n <namespace> | grep -A 10 Events
```

### Pattern 3: Ephemeral Debug Containers (Kubernetes 1.23+)

```bash
# Create ephemeral debug container with all tools
kubectl debug <pod_name> -n <namespace> \
  -it --image=nicolaka/netshoot \
  --target=<container_name>

# Debug with specific debug image
kubectl debug <pod_name> -n <namespace> \
  -it --image=busybox:1.35 \
  --target=app-container

# Debug by copying pod and replacing image
kubectl debug <pod_name> -n <namespace> \
  -it --copy-to=debug-pod \
  --container=app \
  --image=python:3.11-slim

# Debug distroless container
kubectl debug <pod_name> -n <namespace> \
  -it --image=busybox:1.35 \
  --target=distroless-app \
  --share-processes

# Example: Debug container with full tooling
kubectl debug my-app-pod -n production \
  -it --image=ubuntu:22.04 \
  --target=app -- /bin/bash

# Inside debug container:
# - Shared PID namespace: can see target process
# - Shared network namespace: same network stack
# - Shared filesystem: can inspect volumes
```

**Debug container example** (Python app in distroless):
```yaml
# Original pod (distroless, no shell)
apiVersion: v1
kind: Pod
metadata:
  name: my-app
spec:
  containers:
  - name: app
    image: gcr.io/distroless/python3
    command: ["/app/main.py"]

# Debug with ephemeral container
# kubectl debug my-app -it --image=python:3.11-slim --target=app
# Now you can:
# - ps aux (see processes)
# - ls -la /proc/<pid>/fd (open file descriptors)
# - cat /proc/<pid>/environ (environment variables)
# - strace -p <pid> (trace syscalls)
```

### Pattern 4: nsenter (Host-Level Container Access)

```bash
# Get container PID
docker inspect --format '{{.State.Pid}}' <container_id>
# Or:
docker inspect <container_id> | jq '.[0].State.Pid'

# Enter container namespaces from host
PID=$(docker inspect --format '{{.State.Pid}}' <container_id>)

# Enter all namespaces
nsenter -t $PID -m -u -i -n -p /bin/sh

# Enter specific namespaces
nsenter -t $PID -n ip addr  # Network namespace
nsenter -t $PID -m ls /app  # Mount namespace
nsenter -t $PID -p ps aux   # PID namespace

# Use nsenter with Kubernetes (requires node access)
# 1. Get node where pod is running
kubectl get pod <pod_name> -o wide

# 2. SSH to node
ssh <node_name>

# 3. Find container ID
crictl ps | grep <pod_name>

# 4. Get container PID
PID=$(crictl inspect <container_id> | jq '.info.pid')

# 5. Enter container
nsenter -t $PID -m -u -i -n -p /bin/sh
```

### Pattern 5: Debug Sidecar Pattern

```yaml
# Deployment with debug sidecar
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  replicas: 1
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      shareProcessNamespace: true  # Share PID namespace
      containers:
      # Main application (distroless)
      - name: app
        image: gcr.io/distroless/python3
        command: ["/app/main.py"]
        volumeMounts:
        - name: app-data
          mountPath: /app/data

      # Debug sidecar (full tooling)
      - name: debug
        image: nicolaka/netshoot
        command: ["/bin/sleep", "infinity"]
        volumeMounts:
        - name: app-data
          mountPath: /app/data
        securityContext:
          capabilities:
            add: ["SYS_PTRACE"]  # Allow attaching to processes

      volumes:
      - name: app-data
        emptyDir: {}

# Access debug sidecar
# kubectl exec -it <pod_name> -c debug -- /bin/bash

# From debug sidecar, you can:
# - ps aux (see main app process)
# - strace -p <pid> (trace main app)
# - tcpdump -i any (capture network traffic)
# - ls /app/data (inspect shared volumes)
```

### Pattern 6: Distroless Container Debugging

```bash
# Option 1: Ephemeral container (Kubernetes 1.23+)
kubectl debug <pod_name> \
  -it --image=busybox:1.35 \
  --target=distroless-app \
  --share-processes

# Option 2: Debug image with same app
# Build debug variant of Dockerfile
FROM python:3.11-slim AS debug
RUN apt-get update && apt-get install -y \
    curl vim strace tcpdump netcat procps
COPY app/ /app/
CMD ["/app/main.py"]

FROM gcr.io/distroless/python3 AS production
COPY app/ /app/
CMD ["/app/main.py"]

# Deploy debug image temporarily
kubectl set image deployment/my-app app=my-app:debug

# Rollback to production after debugging
kubectl rollout undo deployment/my-app

# Option 3: Copy files from running container
kubectl cp <pod_name>:/app/config.yaml ./config.yaml
kubectl exec <pod_name> -- cat /app/logs/error.log > error.log

# Option 4: Use docker multi-stage with debug target
docker build --target debug -t my-app:debug .
docker run -it my-app:debug /bin/bash
```

### Pattern 7: Network Debugging in Containers

```bash
# Debugging DNS
kubectl exec -it <pod_name> -- nslookup kubernetes.default
kubectl exec -it <pod_name> -- cat /etc/resolv.conf

# If no nslookup, use debug container
kubectl debug <pod_name> -it --image=nicolaka/netshoot
# Inside debug container:
dig kubernetes.default.svc.cluster.local
nslookup google.com

# Test connectivity
kubectl exec -it <pod_name> -- wget -O- http://service-name:8080/health
kubectl exec -it <pod_name> -- nc -zv service-name 8080

# Capture network traffic (requires privileged)
kubectl exec -it <pod_name> -- tcpdump -i any -w /tmp/capture.pcap
kubectl cp <pod_name>:/tmp/capture.pcap ./capture.pcap

# Analyze in Wireshark
wireshark capture.pcap

# Check network policies
kubectl get networkpolicies -n <namespace>
kubectl describe networkpolicy <policy_name>

# Test pod-to-pod connectivity
# Terminal 1: Start server
kubectl run test-server --image=nginx --port=80

# Terminal 2: Test from client
kubectl run test-client -it --rm --image=busybox -- wget -O- test-server
```

---

## Quick Reference

### Essential Debug Images

| Image | Use Case | Size | Tools |
|-------|----------|------|-------|
| **nicolaka/netshoot** | Network debugging | ~400MB | curl, tcpdump, nslookup, iperf, netcat |
| **busybox:1.35** | Minimal debugging | ~5MB | sh, wget, nc (basic utils) |
| **ubuntu:22.04** | Full debugging | ~80MB | apt, full shell, build tools |
| **alpine:3.18** | Lightweight + package manager | ~7MB | apk, sh, basic utils |

### Docker Debug Commands

```bash
# Logs
docker logs <container> [-f] [--tail N] [--since TIME]

# Stats
docker stats [<container>]
docker top <container>

# Filesystem
docker exec <container> ls /app
docker cp <container>:/path/to/file ./file

# Shell
docker exec -it <container> /bin/sh
docker run -it --entrypoint /bin/sh <image>

# Network
docker inspect <container> | jq '.[0].NetworkSettings'
docker network inspect <network>

# Processes
docker exec <container> ps aux
nsenter -t <pid> -p ps aux
```

### Kubernetes Debug Commands

```bash
# Logs
kubectl logs <pod> [-c <container>] [-f] [--previous]

# Stats
kubectl top pod <pod>
kubectl top nodes

# Filesystem
kubectl exec <pod> -- ls /app
kubectl cp <pod>:/path/to/file ./file

# Shell
kubectl exec -it <pod> -- /bin/sh
kubectl debug <pod> -it --image=busybox

# Network
kubectl port-forward <pod> 8080:80
kubectl get svc,endpoints

# Events
kubectl get events --sort-by='.lastTimestamp'
kubectl describe pod <pod>
```

### strace Cheat Sheet

```bash
# Trace syscalls of running process
strace -p <pid>

# Trace specific syscalls
strace -e trace=open,read,write -p <pid>

# Trace with timestamps
strace -tt -p <pid>

# Count syscalls
strace -c -p <pid>

# Trace new process from start
strace -f python app.py

# Save to file
strace -o /tmp/trace.log -p <pid>
```

---

## Anti-Patterns

### ❌ Installing Debug Tools in Production Images

```dockerfile
# WRONG: Bloated production image
FROM python:3.11-slim
RUN apt-get update && apt-get install -y \
    vim curl tcpdump strace gdb  # Increases attack surface!
COPY app.py /app/
CMD ["python", "/app/app.py"]

# CORRECT: Multi-stage with debug target
FROM python:3.11-slim AS base
COPY app.py /app/

FROM base AS debug
RUN apt-get update && apt-get install -y vim curl strace

FROM base AS production
CMD ["python", "/app/app.py"]
```

### ❌ Running Containers as Root

```yaml
# WRONG: Root user in container
containers:
- name: app
  image: my-app:latest
  # Runs as root by default!

# CORRECT: Non-root user
containers:
- name: app
  image: my-app:latest
  securityContext:
    runAsUser: 1000
    runAsNonRoot: true
    allowPrivilegeEscalation: false
```

### ❌ Debugging with Modified Code

```bash
# WRONG: Edit code in running container
kubectl exec -it <pod> -- vi /app/main.py  # Changes lost on restart!

# CORRECT: Rebuild image with changes
docker build -t my-app:debug .
kubectl set image deployment/my-app app=my-app:debug
```

### ❌ Forgetting Resource Limits

```yaml
# WRONG: No resource limits (can OOM)
containers:
- name: app
  image: my-app:latest

# CORRECT: Define limits
containers:
- name: app
  image: my-app:latest
  resources:
    requests:
      memory: "128Mi"
      cpu: "100m"
    limits:
      memory: "256Mi"
      cpu: "500m"
```

---

## Related Skills

- **containers/dockerfile-optimization.md** - Multi-stage builds for debug images
- **debugging/network-debugging.md** - tcpdump, DNS, connectivity testing
- **infrastructure/kubernetes-basics.md** - Pod lifecycle, namespaces
- **observability/structured-logging.md** - Container logging best practices

---

**Last Updated**: 2025-10-26
**Format Version**: 1.0 (Atomic)
