# SEV-1 Incident Template

This template provides a structured approach for managing critical (SEV-1) incidents.

## Initial Response (0-5 minutes)

### Incident Commander Actions

```markdown
## Incident Declaration

- [ ] Acknowledge alert
- [ ] Create incident ticket: [JIRA/Linear link]
- [ ] Declare SEV-1 in #incidents channel
- [ ] Create war room: #incident-YYYYMMDD-description
- [ ] Page required personnel via PagerDuty
- [ ] Announce IC role in war room

**War Room Message Template**:
```
@here SEV-1 Incident Declared

Title: [Brief description]
Impact: [What's broken for users]
Started: [HH:MM UTC]

I'm taking IC. Current responders:
- IC: @your-name
- On-call: @engineer-name

First priority: Assess and mitigate customer impact.
Status update in 15 minutes.
```
```

### Technical Lead Actions

```markdown
- [ ] Join war room
- [ ] Quick assessment:
  - What's broken?
  - How many users affected?
  - Since when?
  - What changed recently?
- [ ] Report findings to IC
- [ ] Begin hands-on investigation
```

### Communications Lead Actions

```markdown
- [ ] Join war room
- [ ] Update status page to "Investigating"
- [ ] Send initial customer notification
- [ ] Alert support team via #support-escalations
- [ ] Prepare for updates every 30 minutes
```

## Assessment Phase (5-15 minutes)

### Questions to Answer

```markdown
## Incident Assessment

1. **What is broken?**
   - Service: [name]
   - Feature: [specific functionality]
   - Scope: [partial/complete outage]

2. **User Impact**
   - Users affected: [number/%]
   - Severity of impact: [cannot use X / slow performance / errors]
   - Geographic scope: [global / region-specific]

3. **Timeline**
   - Issue started: [HH:MM UTC]
   - First detected: [HH:MM UTC]
   - Detection method: [monitoring / customer report / internal]

4. **Recent Changes**
   - Deployments in last 2 hours: [yes/no - versions]
   - Config changes: [yes/no - what changed]
   - Infrastructure changes: [yes/no - what changed]
   - Traffic patterns: [normal / spike / unusual]

5. **Current Metrics**
   - Error rate: [X%]
   - P95 latency: [Xms]
   - Throughput: [X req/s]
   - Resource utilization: [CPU/Memory/Disk]
```

### Severity Confirmation

```markdown
Confirm SEV-1 classification:
- [ ] >50% of users affected OR
- [ ] Complete outage of critical feature OR
- [ ] Revenue impact >$10K/hour OR
- [ ] Data breach/security incident OR
- [ ] SLA breach imminent

If criteria not met, consider de-escalating to SEV-2.
```

## Mitigation Phase (15-60 minutes)

### Mitigation Decision Tree

```
Recent deployment (< 2 hours)?
├─ YES → High confidence in deployment quality?
│        ├─ NO → ROLLBACK (fastest path)
│        └─ YES → Can fix in < 15 minutes?
│                 ├─ YES → Implement fix, monitor closely
│                 └─ NO → ROLLBACK
│
└─ NO → Resource exhaustion?
        ├─ YES → Scale up immediately
        │        Check for memory leaks / connection leaks
        │
        └─ NO → Dependency failure?
                ├─ YES → Enable graceful degradation
                │        Failover to backup
                │        Route around failed dependency
                │
                └─ NO → Deep investigation required
                        Consider enabling maintenance mode
                        while investigating
```

### Mitigation Actions

```markdown
## Common Mitigation Actions

### Rollback Deployment
```bash
# Kubernetes
kubectl rollout undo deployment/[service-name]
kubectl rollout status deployment/[service-name]

# Verify error rate decreased
# Wait 5 minutes for metrics to stabilize
```

### Scale Resources
```bash
# Increase replicas
kubectl scale deployment/[service-name] --replicas=20

# Increase resource limits
kubectl set resources deployment/[service-name] \
  --limits=memory=8Gi,cpu=4000m

# Monitor metrics for improvement
```

### Disable Feature Flag
```bash
# Using feature flag API
curl -X POST "$FEATURE_FLAG_API/disable" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"flag":"new_feature","reason":"SEV-1 incident"}'

# Verify flag disabled
curl "$FEATURE_FLAG_API/flags" | jq '.flags.new_feature'
```

### Enable Graceful Degradation
```python
# Application-level fallback
try:
    result = external_service.call(timeout=5)
except (TimeoutError, ConnectionError):
    # Serve from cache or return degraded response
    result = cache.get(key, default=SAFE_FALLBACK)
    metrics.increment('degraded_mode_active')
```

### Route Traffic
```bash
# Route traffic away from failing region
aws route53 change-resource-record-sets \
  --hosted-zone-id $ZONE_ID \
  --change-batch file://failover-config.json

# Or disable bad region in load balancer
kubectl annotate ingress main \
  nginx.ingress.kubernetes.io/canary-weight=0
```
```

## Communication Updates

### Update Schedule

```markdown
SEV-1 Update Cadence:
- Initial: Within 10 minutes of declaration
- Progress: Every 30 minutes
- Resolution: Immediately when resolved
- Postmortem: Within 48 hours
```

### Update Template (30-minute intervals)

```markdown
Subject: [SEV-1] Update #[N] - [Service Name] - [Status]

UPDATE #[N] - [HH:MM UTC]

CURRENT STATUS: [Investigating / Identified / Mitigating / Monitoring]

IMPACT:
- [Current user impact]
- Users affected: [Updated count if known]
- Error rate: [Current %]

ACTIONS TAKEN:
- [HH:MM] [Action 1]
- [HH:MM] [Action 2]

CURRENT EFFORTS:
- [What we're working on now]

EXPECTED TIMELINE:
- [Best estimate OR "investigating"]

NEXT UPDATE: [30 minutes from now]

[IC Name] - Incident Commander
```

## Resolution Phase

### Resolution Criteria

```markdown
Service can be declared RESOLVED when ALL criteria met:

Technical Metrics:
- [ ] Error rate back to baseline (<0.5%)
- [ ] Latency within SLO (p95 < [X]ms)
- [ ] Throughput recovered to normal levels
- [ ] All health checks passing
- [ ] No active alerts

Customer Impact:
- [ ] User-facing functionality verified working
- [ ] Support ticket volume back to normal
- [ ] No customer reports in last 30 minutes

System Stability:
- [ ] No recurring issues for 30+ minutes
- [ ] Monitoring confirms stable state
- [ ] Related systems healthy
- [ ] Dependencies verified operational

Do NOT resolve if:
- Metrics still elevated
- Mitigation is temporary (will fail again)
- Root cause unknown and likely to recur
- Still receiving customer complaints
```

### Resolution Actions

```markdown
When declaring RESOLVED:

1. [ ] IC announces resolution in war room
2. [ ] Update status page to "Resolved"
3. [ ] Send final customer notification
4. [ ] Update incident ticket to Resolved
5. [ ] Thank team members publicly
6. [ ] Schedule postmortem (within 24-48 hours)
7. [ ] Document any follow-up work needed
8. [ ] Close war room (keep pinned messages)
9. [ ] Update on-call handoff notes
10. [ ] Notify leadership of resolution
```

### Resolution Notification

```markdown
Subject: [RESOLVED] [Service Name] - Incident Resolved

The incident affecting [Service Name] has been RESOLVED.

SUMMARY:
- Started: [HH:MM UTC]
- Resolved: [HH:MM UTC]
- Duration: [X hours, Y minutes]
- Impact: [Brief description]

RESOLUTION:
- [Brief description of what fixed it]
- Service is now operating normally
- Monitoring for continued stability

ROOT CAUSE:
- Preliminary: [Brief description]
- Full postmortem will be published within 48 hours

NO ACTION REQUIRED from users.

We apologize for any inconvenience this may have caused.

[IC Name] - Incident Commander
```

## Post-Incident (24-72 hours)

### Immediate Follow-up

```markdown
Within 24 hours of resolution:
- [ ] Compile timeline from war room logs
- [ ] Gather metrics, graphs, screenshots
- [ ] Schedule postmortem meeting (1 hour)
  - Invite: IC, tech lead, responders, stakeholders
  - Facilitator: Someone NOT on incident response
- [ ] Begin drafting postmortem document
```

### Postmortem Meeting

```markdown
Agenda (60 minutes):

1. [5 min] Facilitator reads executive summary
2. [10 min] Walk through timeline
3. [10 min] Discuss what went well
4. [15 min] Discuss what went poorly (blameless!)
5. [15 min] Brainstorm action items
6. [5 min] Assign owners and deadlines

Rules:
- Blameless: Focus on systems, not people
- Specific: "The monitoring" not "we"
- Actionable: Every issue needs action item
- Time-boxed: Park deep dives for later
```

### Action Item Tracking

```markdown
All action items must have:
- [ ] Clear description of work
- [ ] Owner assigned
- [ ] Deadline set (1-4 weeks)
- [ ] Priority (P0/P1/P2)
- [ ] Tracked in project management tool

Categories:
- Prevent: Actions to prevent recurrence
- Detect: Actions to detect faster
- Respond: Actions to respond faster
- Process: Process improvements

Follow-up:
- [ ] 1 week: Check-in on progress
- [ ] 1 month: Review completion rate
- [ ] Quarterly: Review effectiveness
```

## War Room Best Practices

### Communication Format

```markdown
Use structured updates in war room:

[HH:MM] [@person] [Action/Decision/Observation]

Examples:
[14:23] @alice [ACTION] Rolled back deployment v2.5.3
[14:25] @bob [OBSERVATION] Error rate decreased to 2%
[14:27] @ic [DECISION] Monitoring for 10 min before resolving
[14:30] @comms [NOTIFICATION] Customer update sent
[14:35] @tech-lead [QUESTION] Do we know which requests are failing?
[14:37] @alice [ANSWER] Seeing failures on /api/v1/orders endpoint
```

### Roles Clarity

```markdown
Incident Commander (IC):
- Makes all decisions
- Coordinates responders
- Manages communication cadence
- Declares resolution
- NOT hands on keyboard

Technical Lead:
- Hands on keyboard
- Implements fixes
- Technical investigation
- Reports findings to IC

Communications Lead:
- Writes all external updates
- Sends to customers, leadership, support
- Manages status page
- NOT involved in technical decisions

Scribe:
- Documents timeline
- Records decisions
- Tracks action items
- NOT involved in investigation
```

## Metrics to Track

```markdown
For every SEV-1, record:

Detection:
- MTTD (Mean Time To Detect): Alert time - Issue start
- Detection method: Monitoring / Customer / Manual

Response:
- MTTA (Mean Time To Acknowledge): Ack time - Alert time
- Time to IC assigned: IC assigned - Alert time
- Time to first update: First comms - Alert time

Resolution:
- MTTR (Mean Time To Repair): Resolved - Alert time
- Time to mitigation: First relief - Alert time
- Customer impact duration: Restored - Impact start

Impact:
- Users affected (count or %)
- Failed requests / transactions
- Revenue impact ($)
- Support tickets generated
```

## Checklist Summary

```markdown
## SEV-1 Quick Checklist

Initial (0-5 min):
- [ ] Declare SEV-1
- [ ] Create war room
- [ ] Page team
- [ ] Assess impact
- [ ] Initial customer notification

Mitigation (5-60 min):
- [ ] Identify recent changes
- [ ] Implement mitigation
- [ ] Verify impact reduced
- [ ] Updates every 30 min

Resolution:
- [ ] Verify all criteria met
- [ ] Monitor for 30+ min
- [ ] Final customer notification
- [ ] Schedule postmortem

Post-Incident:
- [ ] Postmortem draft (24 hr)
- [ ] Postmortem meeting (48 hr)
- [ ] Action items assigned (72 hr)
- [ ] Publish postmortem (1 week)
```
