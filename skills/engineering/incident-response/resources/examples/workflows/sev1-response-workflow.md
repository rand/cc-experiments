# SEV-1 Incident Response Workflow

This document provides a complete walkthrough of responding to a SEV-1 (critical) incident from detection to postmortem.

## Scenario

**Incident**: High error rate (35%) in payment processing API
**Detection**: Automated monitoring alert at 14:25 UTC
**Impact**: 50% of payment transactions failing, affecting thousands of users

---

## Phase 1: Detection and Declaration (14:25 - 14:35 UTC)

### 14:25 - Alert Fires

**PagerDuty Alert**:
```
CRITICAL: High Error Rate in Payment API
Error rate: 35% (threshold: 5%)
Dashboard: https://grafana.example.com/d/payments
Runbook: https://runbooks.example.com/payments/high-error-rate
```

**On-call engineer (Alice) receives page**

### 14:27 - Initial Assessment

Alice acknowledges alert and checks dashboard:
```bash
# Quick checks
curl https://api.example.com/health
# Returns: {"status": "degraded", "payment_api": "unhealthy"}

# Check recent deployments
kubectl rollout history deployment/payment-service | tail -5
# Shows: deployment v2.3.1 at 14:15 UTC (10 minutes ago)

# Check error logs
kubectl logs -l app=payment-service --since=15m | grep ERROR | head -20
# Shows: database connection errors
```

**Assessment**:
- Error rate 35% and climbing
- Started ~14:20 UTC (5 min after deployment)
- Database connection errors in logs
- Likely related to deployment v2.3.1

### 14:30 - Declare SEV-1

Alice determines this is SEV-1:
- [x] >50% of users affected (payments are critical)
- [x] Revenue impact (thousands of failed transactions)
- [x] SLA breach imminent (99.9% monthly availability)

**Actions**:
```bash
# 1. Create incident in tracking system
./create_incident.py create \
  --title "High error rate in payment API" \
  --severity SEV-1 \
  --impact "50% of payment transactions failing" \
  --service payment-api \
  --detected-by monitoring

# Output: Created incident: INC-20251027-ABC123

# 2. Create PagerDuty incident
python pagerduty-integration.py create \
  --incident-id INC-20251027-ABC123 \
  --service-id PXXXXXX \
  --title "SEV-1: Payment API High Error Rate"

# 3. Create Slack war room
python slack-incident-bot.py create-war-room \
  --incident-id INC-20251027-ABC123 \
  --title "High error rate in payment API" \
  --severity SEV-1 \
  --ic-user-id U123ABC  # Alice

# Output: Created war room: #incident-20251027-abc123
```

### 14:32 - Initial War Room Message

**Alice posts in #incident-20251027-abc123**:
```
@here SEV-1 Incident Declared

INC-20251027-ABC123: High error rate in payment API

IMPACT:
- 35% error rate in payment transactions
- Affecting 50% of users attempting payments
- Started: ~14:20 UTC (correlates with deployment v2.3.1)

CURRENT STATUS: Investigating

TEAM:
- IC: @alice
- On-call: @alice (same person, need backup)

FIRST ACTIONS:
- Assessing rollback vs. fix
- Need database team to check connection pool
- Communications: notify support team NOW

Next update in 15 minutes.
```

### 14:33 - Page Additional Team

```bash
# Page database specialist
pagerduty incident create \
  --service database-service \
  --title "DB connection errors - Payment incident" \
  --urgency high

# Page engineering manager for IC support
pagerduty incident create \
  --escalation-policy eng-management \
  --title "SEV-1 needs IC support"

# Invite to war room
python slack-incident-bot.py invite \
  --channel incident-20251027-abc123 \
  --users U234BCD,U345CDE  # Bob (DB), Charlie (Mgr)
```

### 14:35 - Initial Customer Notification

**Communications Lead (auto-assigned or manually)**:
```markdown
Subject: [SEV-1] Payment Processing Issue

We are currently experiencing elevated error rates in payment processing.

IMPACT:
- Some payment transactions may fail
- Users may see error messages during checkout
- Started at: 14:20 UTC

STATUS:
- Issue identified and team actively investigating
- Working on mitigation

NEXT UPDATE:
- Will provide update in 30 minutes
- Status page: https://status.example.com

We apologize for the inconvenience.
```

---

## Phase 2: Mitigation (14:35 - 14:50 UTC)

### 14:36 - Team Assembled

**War room participants**:
- Alice (IC)
- Bob (Database Team, Tech Lead)
- Charlie (Engineering Manager)
- Diana (Communications)
- Eve (Scribe)

**Charlie (Mgr) posts**:
```
[14:36] @charlie Taking formal IC role. @alice moving to tech lead.

Roles:
- IC: @charlie
- Tech Lead: @alice
- Database SME: @bob
- Communications: @diana
- Scribe: @eve

@alice, what's your recommendation? Rollback or investigate?
```

### 14:37 - Rollback Decision

**Timeline in war room**:
```
[14:37] @alice [OBSERVATION] Deployment v2.3.1 correlates exactly with error spike
[14:38] @alice [OBSERVATION] Logs show "connection pool exhausted" errors
[14:38] @bob [OBSERVATION] DB connection count at 95/100 (near max)
[14:39] @bob [OBSERVATION] Queries look normal, but higher volume than usual
[14:40] @charlie [DECISION] Rollback deployment v2.3.1 to v2.3.0
[14:40] @alice [ACTION] Starting rollback now
```

**Rollback execution**:
```bash
# 1. Rollback deployment
kubectl rollout undo deployment/payment-service

# 2. Verify rollback
kubectl rollout status deployment/payment-service
# Output: successfully rolled out

# 3. Monitor metrics
watch -n 5 'curl -s https://api.example.com/metrics | grep payment_error_rate'
```

### 14:42 - Rollback Complete

```
[14:42] @alice [ACTION] Rollback complete, v2.3.0 now running
[14:43] @alice [OBSERVATION] Error rate still at 30%
[14:43] @charlie [DECISION] Rollback didn't help immediately, monitor for 5 minutes
```

### 14:45 - Mitigation Working

```
[14:45] @alice [OBSERVATION] Error rate declining: 22%
[14:46] @bob [OBSERVATION] DB connection count dropping: 75/100
[14:47] @alice [OBSERVATION] Error rate at 10%
[14:48] @alice [OBSERVATION] Error rate at 3%
```

### 14:48 - Additional Mitigation

```
[14:48] @bob [RECOMMENDATION] Increase connection pool to prevent recurrence
[14:49] @charlie [DECISION] Proceed with pool increase
[14:49] @bob [ACTION] Increasing pool from 20 to 50
```

```bash
# Increase connection pool
kubectl set env deployment/payment-service DB_POOL_SIZE=50

# Verify
kubectl get deployment payment-service -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="DB_POOL_SIZE")].value}'
# Output: 50
```

### 14:50 - Error Rate Normalized

```
[14:50] @alice [OBSERVATION] Error rate back to baseline: 0.5%
[14:50] @charlie [DECISION] Monitoring for 15 minutes before declaring resolved
```

### 14:50 - Update Customers

```markdown
Subject: [SEV-1] Update #1 - Payment Processing Issue

UPDATE #1 - 14:50 UTC

CURRENT STATUS: Mitigated

ACTIONS TAKEN:
- 14:40 UTC: Rolled back recent deployment
- 14:49 UTC: Increased database connection pool capacity
- Error rate decreased from 35% to 0.5% (baseline)

CURRENT EFFORTS:
- Monitoring for stability before declaring resolved
- Investigating root cause

NEXT UPDATE: 15:20 UTC (or when resolved)
```

---

## Phase 3: Monitoring and Resolution (14:50 - 15:15 UTC)

### 14:50 - 15:05: Monitoring Period

```
[14:52] @alice [OBSERVATION] All metrics stable for 2 minutes
[14:55] @alice [OBSERVATION] No new errors in logs
[14:58] @bob [OBSERVATION] DB connection pool at healthy 15/50 utilization
[15:00] @alice [OBSERVATION] Payment success rate back to 99.5% (normal)
[15:02] @alice [OBSERVATION] No customer complaints in last 10 minutes
[15:05] @alice [OBSERVATION] 15 minutes stable, all criteria met
```

### 15:05 - Pre-Resolution Checklist

**Charlie (IC) verifies resolution criteria**:
```
Resolution Criteria:
✓ Error rate back to baseline (<0.5%)
✓ Latency within SLO (p95 < 500ms)
✓ Throughput recovered to normal
✓ All health checks passing
✓ No active alerts
✓ User-facing functionality verified
✓ Support ticket volume normal
✓ No customer reports for 15+ minutes
✓ System stable for 15+ minutes
✓ Related systems healthy
✓ Dependencies verified operational

ALL CRITERIA MET
```

### 15:07 - Declare Resolved

```
[15:07] @charlie [DECISION] Declaring incident RESOLVED
[15:07] @charlie [NOTIFICATION] Incident INC-20251027-ABC123 is RESOLVED
[15:07] @charlie [ACTION] @diana send resolution notification
[15:08] @charlie [ACTION] @eve schedule postmortem for tomorrow 10:00 UTC
```

**Update systems**:
```bash
# Update incident status
./create_incident.py update INC-20251027-ABC123 \
  --status resolved \
  --event "Incident resolved" \
  --author charlie

# Resolve PagerDuty incident
python pagerduty-integration.py resolve \
  --incident-id PXXXXXX \
  --resolution "Rolled back deployment and increased connection pool"

# Update Slack
python slack-incident-bot.py post-resolution \
  --channel incident-20251027-abc123 \
  --incident-id INC-20251027-ABC123 \
  --duration "45 minutes" \
  --resolution "Rolled back deployment v2.3.1 and increased DB connection pool to 50"
```

### 15:10 - Final Customer Notification

```markdown
Subject: [RESOLVED] Payment Processing Issue Resolved

The incident affecting payment processing has been RESOLVED.

SUMMARY:
- Started: 14:20 UTC
- Resolved: 15:07 UTC
- Duration: 47 minutes
- Impact: Elevated error rates in payment transactions

RESOLUTION:
- Rolled back deployment v2.3.1
- Increased database connection pool capacity
- Service is now operating normally
- Monitoring for continued stability

ROOT CAUSE:
- Preliminary: Deployment introduced query changes that exhausted DB connection pool
- Full postmortem will be published within 48 hours

NO ACTION REQUIRED from users. All pending payments will be automatically retried.

We apologize for any inconvenience this may have caused.
```

### 15:12 - Thank Team

```
[15:12] @charlie Thank you team for excellent response:
- @alice: Quick diagnosis and rollback
- @bob: Fast DB analysis and mitigation
- @diana: Clear customer communications
- @eve: Great timeline documentation

MTTR: 47 minutes from detection to resolution

Postmortem: Tomorrow 10:00 UTC in this channel
This war room will stay open for documentation.
```

---

## Phase 4: Post-Incident (Next 48 hours)

### Hour 1: Immediate Follow-up

**Actions**:
```bash
# Compile timeline
python slack-incident-bot.py export-timeline \
  --channel incident-20251027-abc123 \
  --output timeline.json

# Gather metrics
curl "https://grafana.example.com/api/dashboards/uid/payments" > metrics.json

# Take screenshots of key graphs
# (manual or automated)

# Begin postmortem draft
./generate_postmortem.py \
  --incident-id INC-20251027-ABC123 \
  --authors alice,bob,charlie \
  --template deployment \
  --output postmortems/INC-20251027-ABC123.md
```

### Hour 24: Postmortem Draft

**Draft sections completed**:
- Executive summary
- Timeline (from war room logs)
- Impact assessment
- Root cause analysis (Five Whys)
- What went well / poorly
- Initial action items

**Key findings**:
1. **Immediate cause**: Deployment v2.3.1 introduced N+1 query pattern
2. **Contributing factors**: Connection pool too small, no load testing
3. **Latent conditions**: No automated pool sizing, no query performance monitoring

### Hour 26: Postmortem Meeting

**Agenda** (1 hour):
```
10:00-10:05: Read executive summary
10:05-10:15: Walk through timeline
10:15-10:25: What went well
10:25-10:40: What went poorly (blameless!)
10:40-10:55: Action items
10:55-11:00: Assign owners and deadlines
```

**Action Items Defined**:

**Prevent Recurrence**:
- [ ] Add connection pool monitoring alerts (Bob, Nov 3)
- [ ] Implement query performance monitoring (Alice, Nov 10)
- [ ] Add automated load testing to CI/CD (Charlie, Nov 17)
- [ ] Review all N+1 query patterns in codebase (Dev team, Nov 20)

**Improve Detection**:
- [ ] Add synthetic payment transaction monitor (Alice, Nov 5)
- [ ] Lower error rate alert threshold to 2% (Bob, Nov 1)

**Improve Response**:
- [ ] Create runbook for connection pool issues (Bob, Nov 1)
- [ ] Document rollback decision criteria (Charlie, Nov 3)

**Improve Processes**:
- [ ] Require load test results for DB-heavy changes (Manager, Nov 10)
- [ ] Add DB query review to code review checklist (Team, Nov 5)

### Hour 48: Publish Postmortem

**Published to**:
- Internal wiki
- Engineering blog (sanitized)
- Shared in #engineering

**Follow-up scheduled**:
- 1 week: Check-in on action items
- 1 month: Review completion rate
- Quarterly: Review effectiveness

---

## Metrics Captured

### Response Metrics
- **MTTD** (Mean Time To Detect): 5 minutes (14:20 issue start → 14:25 alert)
- **MTTA** (Mean Time To Acknowledge): 2 minutes (14:25 alert → 14:27 ack)
- **MTTR** (Mean Time To Repair): 47 minutes (14:20 start → 15:07 resolved)
- **Time to IC**: 10 minutes (14:25 alert → 14:35 formal IC)
- **Time to Mitigation**: 20 minutes (14:25 alert → 14:45 error rate declining)

### Impact Metrics
- **Duration**: 47 minutes
- **Failed Requests**: ~15,000 payment API calls
- **Users Affected**: ~5,000 unique users
- **Revenue Impact**: ~$25,000 in failed transactions
- **Support Tickets**: 234 tickets

### Response Quality
- **Communication Cadence**: Initial (10min), Update (20min), Resolution (47min)
- **Team Response**: 5 people engaged within 15 minutes
- **Rollback Speed**: 5 minutes to complete
- **Resolution Criteria**: All 11 criteria verified

---

## Lessons Learned

### What Went Well
1. ✅ **Fast detection**: Monitoring alerted within 5 minutes
2. ✅ **Quick rollback**: Recognized deployment correlation and acted fast
3. ✅ **Clear communication**: Regular updates kept stakeholders informed
4. ✅ **Team coordination**: War room structure kept everyone aligned
5. ✅ **Good documentation**: Timeline made postmortem easy to write

### What Went Poorly
1. ❌ **Deployment caused issue**: Should have caught in testing
2. ❌ **No load testing**: Last load test was 3 months old
3. ❌ **Missing alerts**: No alert for connection pool utilization
4. ❌ **Code review gap**: N+1 pattern not caught in review
5. ❌ **Manual pool sizing**: Should be automated based on traffic

### Key Takeaways
1. **Load testing must be automated** and run on every deploy
2. **Connection pool needs monitoring** with alerts before exhaustion
3. **Code review needs performance checklist** for database queries
4. **Rollback is the safe default** when deployment correlates with issues
5. **War room structure works** - clear roles, regular updates, good documentation

---

## Template Sections for Future Incidents

This workflow can be adapted for other SEV-1 incidents by:
1. Replacing payment API scenario with actual service
2. Adjusting mitigation steps based on root cause
3. Keeping same structure: Detection → Mitigation → Resolution → Postmortem
4. Using same communication templates
5. Following same metrics collection
