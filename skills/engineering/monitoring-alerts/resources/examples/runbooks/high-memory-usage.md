# Alert: HighMemoryUsage

> **Status**: Active
> **Last Updated**: 2025-10-27
> **Owner**: Platform Team
> **Severity**: Critical

---

## Overview

This alert fires when memory usage exceeds 90% for more than 5 minutes on any node.

**What is being measured**: `node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes`

**Why it matters**: High memory usage can lead to:
- OOM (Out of Memory) killer terminating processes
- System instability and crashes
- Service degradation or unavailability
- Swap thrashing (severe performance impact)

---

## Symptoms

What you'll observe:
- Memory usage > 90% in monitoring
- Pods being evicted (Kubernetes)
- Swap usage increasing
- System slowness
- Application crashes or restarts
- "Out of memory" errors in logs

---

## Impact

### User Impact
- [x] Performance degraded (slow responses)
- [ ] Service unavailable (if OOM occurs)
- [ ] Feature disabled
- [ ] No user impact

### Business Impact
- Revenue impact: Medium (degraded performance)
- Customer impact: Varies by service affected
- SLA impact: Yes (if availability drops below threshold)

---

## Severity

**Current Severity**: Critical (if > 95%), Warning (if > 90%)

### Escalation Criteria

Escalate to **Critical** if:
- Memory usage > 95%
- OOM events detected
- Multiple pods evicted
- Service impact confirmed

Escalate to **Manager** if:
- No improvement after 30 minutes
- Cluster-wide memory pressure
- Customer complaints received

---

## Diagnosis

### 1. Verify the Alert

```bash
# SSH to affected node
ssh [node-ip]

# Check current memory usage
free -h

# Example output:
#               total        used        free      shared  buff/cache   available
# Mem:           15Gi        14Gi       100Mi        50Mi       900Mi       800Mi
# Swap:         2.0Gi       1.5Gi       500Mi

# Check memory usage percentage
echo "scale=2; $(grep MemAvailable /proc/meminfo | awk '{print $2}') / $(grep MemTotal /proc/meminfo | awk '{print $2}') * 100" | bc

# View top memory consumers
top -o %MEM

# Or use htop (better visualization)
htop
```

**Expected**: Memory available > 10% (> 1.5GB on 16GB node)
**Actual**: Memory available < 10%

### 2. Identify Memory Consumers

```bash
# Top 10 processes by memory (Linux)
ps aux --sort=-%mem | head -11

# Detailed per-process memory breakdown
ps aux | awk '{print $6/1024 " MB\t" $11}' | sort -n

# Container memory usage (Docker)
docker stats --no-stream --format "table {{.Container}}\t{{.MemUsage}}"

# Kubernetes pod memory usage
kubectl top pods --all-namespaces --sort-by=memory

# Check for memory leaks in specific process
pmap -x [PID] | tail -1
```

### 3. Check for Memory Leaks

```bash
# Monitor process memory over time
watch -n 5 'ps aux | grep [process-name]'

# Check for zombie processes
ps aux | grep defunct

# View kernel memory slab usage
sudo slabtop

# Check page cache usage
cat /proc/meminfo | grep -E '(Cached|Buffers|Slab)'

# OOM killer logs
dmesg | grep -i "out of memory"
sudo journalctl -xe | grep -i oom
```

### 4. Review Recent Changes

```bash
# Recent deployments (Kubernetes)
kubectl rollout history deployment/[name]

# Recent pod restarts
kubectl get pods --all-namespaces --field-selector=status.phase=Running --sort-by=.status.startTime

# Check resource limits
kubectl describe pod [pod-name] | grep -A 5 "Limits"

# Git commits (if applicable)
git log --since="6 hours ago" --oneline
```

### Common Causes

1. **Memory leak**: Application not releasing memory
   - Confirm: Memory usage steadily increasing over time
   - Check: Application logs for errors, heap dumps

2. **Increased load**: More traffic than capacity
   - Confirm: Request rate increased, more pods running
   - Check: Request metrics, pod count

3. **Large data processing**: Batch job or analytics
   - Confirm: Scheduled job running, large dataset being processed
   - Check: Cron jobs, data pipeline status

4. **Page cache**: Linux caching disk I/O
   - Confirm: "Cached" high in `/proc/meminfo`, "Available" still reasonable
   - Action: Usually safe, kernel will free if needed

5. **Resource limit mismatch**: Pod limits too high
   - Confirm: Sum of pod limits > node capacity
   - Check: `kubectl describe node [node]`

---

## Remediation

### Immediate Actions (< 5 minutes)

**Objective**: Prevent OOM, keep system stable

1. **Clear page cache** (temporary relief):
   ```bash
   # This is safe - kernel will rebuild cache as needed
   sync && echo 3 > /proc/sys/vm/drop_caches
   ```
   **Expected outcome**: Memory usage drops 10-20%
   **Verification**: Run `free -h` again

2. **Identify and restart leaking service** (if known):
   ```bash
   # Kubernetes
   kubectl rollout restart deployment/[name]

   # Systemd service
   sudo systemctl restart [service]

   # Docker container
   docker restart [container-id]
   ```
   **Expected outcome**: Memory released, service recovers
   **Verification**: Check memory usage of new pods/processes

3. **Scale horizontally** (if auto-scaling available):
   ```bash
   # Kubernetes - add more replicas
   kubectl scale deployment [name] --replicas=[N+2]

   # Cloud - add instances
   aws autoscaling set-desired-capacity --auto-scaling-group-name [name] --desired-capacity [N+1]
   ```
   **Expected outcome**: Load distributed, per-instance memory reduced
   **Verification**: `kubectl top pods` shows lower memory per pod

4. **Evict low-priority workloads** (emergency only):
   ```bash
   # Kubernetes - delete non-critical pods
   kubectl delete pod [pod-name] -n [namespace]

   # Stop batch jobs
   kubectl delete job [job-name]
   ```

**If above don't work**: Escalate to platform team lead immediately

### Short-term Fix (< 1 hour)

**Objective**: Stable state while investigating root cause

1. **Adjust resource limits** (if over-committed):
   ```yaml
   # Edit deployment
   kubectl edit deployment [name]

   # Set appropriate limits
   resources:
     requests:
       memory: "256Mi"
     limits:
       memory: "512Mi"
   ```

2. **Enable swap** (temporary, not recommended long-term):
   ```bash
   # Check current swap
   swapon -s

   # Create swap file (if none exists)
   sudo fallocate -l 4G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   ```
   **Note**: This buys time but doesn't fix the problem

3. **Tune application memory settings**:
   ```bash
   # Java applications - reduce heap size
   export JAVA_OPTS="-Xmx2g -Xms512m"

   # Node.js - set max old space
   export NODE_OPTIONS="--max-old-space-size=2048"

   # Python - limit worker memory
   export WORKER_MEMORY_LIMIT=512M
   ```

4. **Implement pod disruption budget** (prevent cascading failures):
   ```yaml
   apiVersion: policy/v1
   kind: PodDisruptionBudget
   metadata:
     name: [app]-pdb
   spec:
     minAvailable: 2
     selector:
       matchLabels:
         app: [app]
   ```

### Long-term Fix

1. **Increase node resources**:
   - Vertical scaling: Upgrade to larger instances
   - Horizontal scaling: Add more nodes
   - Auto-scaling: Configure memory-based scaling

2. **Optimize application memory**:
   - Profile and fix memory leaks
   - Optimize data structures
   - Implement caching strategies
   - Add memory limits and monitoring

3. **Improve resource management**:
   - Set accurate resource requests/limits
   - Use pod priority classes
   - Enable vertical pod autoscaler
   - Implement memory quotas per namespace

---

## Rollback

If remediation makes things worse:

```bash
# Rollback deployment
kubectl rollout undo deployment/[name]

# Restore previous auto-scaling settings
kubectl apply -f autoscaling-backup.yaml

# Disable swap (if enabled as temp fix)
sudo swapoff /swapfile
sudo rm /swapfile
```

---

## Communication

### Who to Notify

| Stakeholder | When | How |
|-------------|------|-----|
| Platform Team | Immediately | Slack #platform-oncall |
| Engineering Manager | If not resolved in 30min | Slack + Phone |
| Application Owners | If specific app identified | Slack team channel |
| Customers | If service degraded > 15min | Status page |

### Communication Templates

**Initial notification**:
```
[INCIDENT] High Memory Usage on [node/cluster]

Impact: [service] may experience slow responses
Started: [time]
Status: Investigating memory consumption
Next update: [+15min]

Incident lead: [oncall engineer]
Slack: #incident-[ID]
```

---

## Prevention

### Monitoring Improvements
- [x] Alert on memory > 90% (existing)
- [ ] Alert on OOM events
- [ ] Monitor memory growth rate
- [ ] Dashboard for memory breakdown

### Process Improvements
- [ ] Memory load testing before deployment
- [ ] Automatic heap dumps on high memory
- [ ] Regular memory profiling of applications

### Code/Infrastructure Changes
- [ ] Implement memory limits on all pods
- [ ] Add memory leak detection
- [ ] Configure horizontal pod autoscaling
- [ ] Optimize memory-intensive operations

---

## Validation

### Post-Remediation Checks

```bash
# 1. Memory usage normal
free -h | grep Mem
# Available should be > 20%

# 2. No OOM events in last 10 minutes
dmesg | grep -i oom | tail -5

# 3. All pods running
kubectl get pods --all-namespaces | grep -v Running

# 4. Application metrics normal
# Check dashboard: [URL]

# 5. No pending pod evictions
kubectl get events --all-namespaces | grep Evicted
```

All checks passing? ✓ Incident resolved

---

## Related Information

### Dashboards
- Node Resources: https://grafana.example.com/d/node-resources
- Pod Memory: https://grafana.example.com/d/pod-memory
- OOM Events: https://grafana.example.com/d/oom-events

### Related Alerts
- `OOMKiller`: OOM events occurred
- `HighSwapUsage`: Swapping indicates memory pressure
- `PodEvicted`: Pods evicted due to resource pressure

### Documentation
- Memory Troubleshooting: https://docs.example.com/memory
- Resource Limits Guide: https://docs.example.com/resources
- Kubernetes Best Practices: https://docs.example.com/k8s

### Previous Incidents
- INC-234: 2025-08-15 - Java heap leak in API service
- INC-567: 2025-09-22 - Redis cache grew unbounded
- INC-890: 2025-10-10 - Pod limits too high, node over-committed

---

## Appendix

### Memory Metrics Explained

```
MemTotal     : Total physical RAM
MemFree      : Unused RAM
MemAvailable : RAM available for starting new applications (includes reclaimable cache)
Buffers      : Temporary storage for block devices
Cached       : Page cache from files
Slab         : Kernel data structures
SwapTotal    : Total swap space
SwapFree     : Unused swap space
```

**Key metric**: `MemAvailable` (not `MemFree`)

### Kubernetes Memory Metrics

```bash
# Pod memory requests vs limits
kubectl describe node [node] | grep -A 5 "Allocated resources"

# Memory pressure eviction thresholds
kubectl get nodes -o json | jq '.items[].status.allocatable.memory'

# Top memory-consuming namespaces
kubectl top pods -A | awk '{print $1, $4}' | sort -k2 -rh | head -20
```

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-10-27 | Platform Team | Initial version |
| 2025-10-27 | SRE | Added Kubernetes-specific steps |

---

## Feedback

Found this runbook helpful? Found an issue?

- GitHub: https://github.com/example/runbooks/issues
- Slack: #platform-runbooks
- Email: platform-team@example.com
