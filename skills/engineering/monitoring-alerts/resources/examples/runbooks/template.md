# Alert: [AlertName]

> **Status**: [Draft | Active | Archived]
> **Last Updated**: YYYY-MM-DD
> **Owner**: [Team/Person]
> **Severity**: [Critical | Warning | Info]

---

## Overview

Brief description of what this alert means and why it exists.

**What is being measured**: Describe the metric or condition

**Why it matters**: Explain the business or technical impact

---

## Symptoms

What the oncall engineer will observe:
- System behavior
- User-facing symptoms
- Related metrics

---

## Impact

### User Impact
- [ ] Service unavailable
- [ ] Performance degraded
- [ ] Feature disabled
- [ ] No user impact

### Business Impact
- Revenue impact: [None | Low | Medium | High]
- Customer impact: [Number of affected users]
- SLA impact: [Yes/No]

---

## Severity

**Current Severity**: [Critical | Warning | Info]

### Escalation Criteria

Escalate to **Critical** if:
- Condition persists > [duration]
- Metric exceeds [threshold]
- User impact confirmed

Escalate to **Manager** if:
- No progress after [duration]
- Customer escalation received
- Multiple related incidents

---

## Diagnosis

### 1. Verify the Alert

Check if alert is accurate:

```bash
# Query Prometheus to verify metric
curl 'http://prometheus:9090/api/v1/query?query=[METRIC_NAME]'

# Check Grafana dashboard
# URL: [Dashboard URL]
```

**Expected**: [What should you see?]
**Actual**: [What are you seeing?]

### 2. Check Related Systems

```bash
# Check service health
kubectl get pods -n [namespace]
kubectl logs -f [pod-name] --tail=100

# Check dependencies
curl -I https://[dependency]/health
```

### 3. Review Recent Changes

```bash
# Check recent deployments
kubectl rollout history deployment/[name]

# Check git commits
git log --since="1 hour ago" --oneline

# Check recent alerts
# Alertmanager URL: [URL]
```

### 4. Identify Root Cause

Common causes:
1. **[Cause 1]**: How to identify, how to confirm
2. **[Cause 2]**: How to identify, how to confirm
3. **[Cause 3]**: How to identify, how to confirm

---

## Remediation

### Immediate Actions (< 5 minutes)

**Objective**: Stop the bleeding, restore service

1. **Action 1**:
   ```bash
   # Command with explanation
   kubectl scale deployment/[name] --replicas=[N]
   ```
   **Expected outcome**: [What should happen]
   **Verification**: [How to verify it worked]

2. **Action 2**:
   ```bash
   # Command
   ```

3. **If above don't work**: Escalate to [team/person]

### Short-term Fix (< 1 hour)

**Objective**: Stable workaround while investigating root cause

1. **Action 1**:
   - Step-by-step instructions
   - Expected outcomes
   - Rollback procedure if needed

2. **Action 2**:
   - Instructions

### Long-term Fix

**Objective**: Permanent resolution

1. Create ticket: [Ticket system link template]
2. Investigate root cause
3. Implement permanent fix
4. Update monitoring/alerts if needed

---

## Rollback

If remediation makes things worse:

```bash
# Rollback deployment
kubectl rollout undo deployment/[name]

# Restore from backup
./restore_backup.sh [backup-id]

# Disable feature flag
curl -X POST https://[feature-flags]/disable/[flag]
```

---

## Communication

### Who to Notify

| Stakeholder | When | How |
|-------------|------|-----|
| Team Lead | Immediately | Slack #[channel] |
| Manager | If not resolved in 30min | Phone/Slack |
| Customers | If impact confirmed | Status page |
| Exec Team | If revenue impact | Email + Slack |

### Communication Templates

**Initial notification** (within 5 minutes):
```
[INCIDENT] [Service] - [Brief description]

Impact: [User-facing impact]
Started: [Time]
Status: Investigating
Next update: [Time]

Incident lead: [Name]
Slack channel: #incident-[ID]
```

**Status update** (every 30 minutes):
```
[UPDATE] [Service] - [Brief description]

Actions taken:
- [Action 1]
- [Action 2]

Current status: [Status]
Next update: [Time]
```

**Resolution**:
```
[RESOLVED] [Service] - [Brief description]

Resolution: [What fixed it]
Root cause: [Brief description]
Duration: [Total time]
Postmortem: [Link] (to be completed within 48h)
```

---

## Prevention

### Monitoring Improvements
- [ ] Add monitoring for [metric]
- [ ] Adjust alert threshold to [value]
- [ ] Create dashboard for [view]

### Process Improvements
- [ ] Add deployment check for [condition]
- [ ] Update documentation
- [ ] Add automated test

### Code/Infrastructure Changes
- [ ] Increase resource limits
- [ ] Implement circuit breaker
- [ ] Add caching layer

---

## Validation

### Post-Remediation Checks

Verify service is healthy:

```bash
# Check 1: Service responding
curl https://[service]/health

# Check 2: Metrics recovered
# [Dashboard URL]

# Check 3: Error rate normal
# [Query URL]

# Check 4: Latency acceptable
# [Dashboard URL]
```

All checks passing? ✓ Incident resolved

---

## Related Information

### Dashboards
- [Dashboard name]: [URL]
- [Dashboard name]: [URL]

### Related Alerts
- `[AlertName]`: [Brief description]
- `[AlertName]`: [Brief description]

### Documentation
- Architecture docs: [URL]
- API docs: [URL]
- Infrastructure docs: [URL]

### Previous Incidents
- [INC-123]: [Date] - [Brief description]
- [INC-456]: [Date] - [Brief description]

### Team Contacts
- Oncall: Check PagerDuty schedule
- Team Slack: #[channel]
- Team email: [email]

---

## Appendix

### Useful Commands

```bash
# View logs
kubectl logs -f [pod] --namespace=[ns] --tail=100

# Check resource usage
kubectl top pods -n [namespace]

# Describe pod
kubectl describe pod [pod] -n [namespace]

# Execute command in pod
kubectl exec -it [pod] -n [namespace] -- bash

# Port forward for debugging
kubectl port-forward [pod] 8080:8080 -n [namespace]
```

### Metrics Queries

```promql
# Request rate
sum(rate(http_requests_total[5m])) by (service)

# Error rate
sum(rate(http_requests_total{status=~"5.."}[5m])) by (service)
/
sum(rate(http_requests_total[5m])) by (service)

# Latency p95
histogram_quantile(0.95,
  sum(rate(http_request_duration_seconds_bucket[5m])) by (le, service)
)
```

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| YYYY-MM-DD | [Name] | Initial version |
| YYYY-MM-DD | [Name] | Updated remediation steps |

---

## Feedback

Found an issue with this runbook? Incident didn't match the runbook?

- Create issue: [Link to issue tracker]
- Slack: #[channel]
- Update directly: [Link to this file in git]
