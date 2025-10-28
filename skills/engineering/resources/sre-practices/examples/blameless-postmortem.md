# Incident Postmortem: API High Error Rate

**Date**: 2025-10-27
**Incident Commander**: Alice Smith (@alice)
**Severity**: Sev2
**Duration**: 45 minutes (14:23 - 15:08 UTC)
**Impact**: ~15,000 users experienced errors (10% of active users)
**Error Budget Impact**: 15% of monthly budget consumed

## Executive Summary

The Payment API experienced elevated error rates (5-10%) for 45 minutes due to database connection pool exhaustion. A recent deployment introduced an N+1 query pattern that, combined with a 3x traffic spike from a marketing campaign, saturated database connections. Service was restored by rolling back the deployment. No data was lost or corrupted.

**Root Cause**: N+1 query pattern introduced in v2.3.4, triggered by unexpected traffic spike.

**Key Learnings**:
- Load testing under realistic traffic is critical
- Marketing campaigns must be coordinated with engineering
- Database query patterns need better visibility

## Timeline

All times in UTC.

**14:20** - Deployment v2.3.4 completed successfully
- Auto-deployment via CI/CD
- Initial health checks passed
- No alerts triggered

**14:23** - First alert fired: Error rate > 1%
- Prometheus alert: `ErrorRateHigh`
- PagerDuty page sent to on-call (@alice)
- Error rate climbing: 1% → 3% → 5%

**14:25** - On-call engineer @alice acknowledged alert
- Checked Grafana dashboard
- Observed error pattern: Database timeouts
- Began investigation

**14:27** - Traffic analysis revealed 3x normal load
- Marketing campaign launched (not communicated)
- Traffic: 1000 req/s → 3000 req/s
- Still within system capacity normally

**14:30** - Identified database connection pool saturation
- Connection pool: 100% utilization
- New requests timing out waiting for connections
- Query duration increased: 50ms → 500ms

**14:33** - Database pool exhausted
- All 50 connections in use
- Queue depth: 200+ waiting requests
- Timeout errors cascading

**14:35** - Incident commander assigned (@alice)
- War room opened: #incident-2025-10-27
- Roles assigned:
  - IC: @alice
  - Ops: @bob
  - Comms: @charlie
- Decision: Investigate recent deployment

**14:37** - Root cause identified: N+1 query in v2.3.4
- Code review of recent deployment
- Found inefficient query in `/api/products` endpoint
- Query pattern: 1 query + N queries (N = items)
- Under high load: 100 items × 3000 req/s = 300,000 queries/s

**14:40** - Decision: Rollback to v2.3.3
- Rollback safer than debugging in production
- Previous version known-good
- @bob initiated rollback via CI/CD

**14:42** - Rollback initiated
- Kubernetes rolling update started
- 25% → 50% → 75% → 100% over 5 minutes
- Monitoring error rates closely

**14:45** - Rollback complete (v2.3.3 deployed)
- All pods running previous version
- Error rate declining: 5% → 3% → 1%

**14:50** - Error rate returned to baseline
- Error rate: < 0.1% (normal)
- Database connections: 30/50 in use (normal)
- Query latency: 50ms (normal)

**14:55** - Monitoring for stability
- Extended observation period
- No new alerts
- Database pool stable

**15:00** - Customer communication sent
- Status page updated: "Incident resolved"
- Email to affected users
- Summary of impact and resolution

**15:08** - Incident declared resolved
- All metrics normal for 15 minutes
- Closed war room
- Scheduled postmortem meeting

## Root Cause Analysis

### Five Whys

**Problem**: API returned 500 errors

1. **Why?** Database connection timeouts
2. **Why?** Connection pool exhausted
3. **Why?** Too many concurrent database queries
4. **Why?** N+1 query pattern + high traffic
5. **Why?** Code change not tested under load

**Root Cause**: Lack of load testing in CI/CD pipeline allowed inefficient query pattern to reach production.

### Technical Details

**Code Change** (v2.3.4):

```python
# BAD: N+1 query pattern
def get_products(category_id):
    products = db.query("SELECT * FROM products WHERE category_id = ?", category_id)
    for product in products:
        # N queries (one per product)
        product.reviews = db.query("SELECT * FROM reviews WHERE product_id = ?", product.id)
    return products
```

**Should have been**:

```python
# GOOD: Single query with JOIN
def get_products(category_id):
    return db.query("""
        SELECT p.*, r.*
        FROM products p
        LEFT JOIN reviews r ON p.id = r.product_id
        WHERE p.category_id = ?
    """, category_id)
```

**Impact Under Load**:

- Normal traffic (1000 req/s): 100 products × 1000 = 100,000 queries/s ✓ Manageable
- Spike traffic (3000 req/s): 100 products × 3000 = 300,000 queries/s ✗ Overwhelmed pool

## Contributing Factors

1. **No load testing in CI/CD**
   - Changes deployed without performance validation
   - N+1 pattern not caught by code review
   - No automated query analysis

2. **Marketing campaign not coordinated**
   - Engineering not aware of 3x traffic spike
   - No capacity planning for campaign
   - Campaign launched without heads-up

3. **Insufficient query monitoring**
   - No per-query performance tracking
   - Database metrics aggregated (missed individual slow queries)
   - No alerting on query patterns

4. **Manual deployment rollback**
   - Rollback took 10 minutes (manual process)
   - No automatic rollback on error spike
   - Delay extended incident duration

5. **Missing connection pool alerts**
   - No alert for connection pool utilization > 80%
   - Would have warned before exhaustion
   - Earlier detection possible

## Impact Assessment

### User Impact

- **Affected users**: ~15,000 (10% of active users during incident)
- **Error rate**: 5-10% (baseline < 0.1%)
- **Failed transactions**: ~150 payment attempts
- **Estimated revenue impact**: $3,000 (average $20/transaction)

### System Impact

- **Duration**: 45 minutes
- **Peak error rate**: 10%
- **Database connections**: 100% utilization for 20 minutes
- **Latency increase**: 50ms → 500ms (p95)

### SLO Impact

- **Monthly error budget**: 21.6 minutes (99.95% availability)
- **Budget consumed**: 3.24 minutes (15% of monthly budget)
- **Status**: Moved from "Healthy" to "Concerning" zone
- **Remaining budget**: 18.36 minutes

### Customer Sentiment

- **Support tickets**: 23 tickets filed during incident
- **Twitter mentions**: 12 complaints
- **NPS impact**: Monitoring for changes (data in 7 days)

## Resolution

### Immediate Fix

Rolled back to v2.3.4, which restored service within 10 minutes of decision.

### Permanent Fix

Fixed N+1 query in v2.3.5:
- Rewrote query with proper JOIN
- Load tested under 5x expected traffic
- Verified query performance < 100ms
- Deployed successfully with no issues

## Action Items

### Prevention (Stop it from happening)

| Priority | Action | Owner | Due Date | Ticket |
|----------|--------|-------|----------|--------|
| P0 | Add load testing to CI/CD pipeline | @bob | 2025-11-10 | ENG-1234 |
| P0 | Implement query performance monitoring | @charlie | 2025-11-15 | ENG-1235 |
| P1 | Add database connection pool alerts | @alice | 2025-11-08 | ENG-1236 |
| P1 | Establish marketing-engineering coordination | @diana | 2025-11-20 | ENG-1237 |
| P2 | Add query linter to catch N+1 patterns | @bob | 2025-11-25 | ENG-1238 |

### Detection (Find it faster)

| Priority | Action | Owner | Due Date | Ticket |
|----------|--------|-------|----------|--------|
| P0 | Add query execution time to traces | @charlie | 2025-11-12 | ENG-1239 |
| P1 | Reduce alert evaluation window (5m → 1m) | @alice | 2025-11-05 | ENG-1240 |
| P1 | Add per-endpoint query count metrics | @bob | 2025-11-18 | ENG-1241 |

### Response (Fix it faster)

| Priority | Action | Owner | Due Date | Ticket |
|----------|--------|-------|----------|--------|
| P0 | Implement auto-rollback on error threshold | @bob | 2025-11-18 | ENG-1242 |
| P1 | Document connection pool troubleshooting | @alice | 2025-11-08 | ENG-1243 |
| P2 | Create runbook for database saturation | @charlie | 2025-11-15 | ENG-1244 |

### Process Improvements

| Priority | Action | Owner | Due Date | Ticket |
|----------|--------|-------|----------|--------|
| P1 | Require load testing sign-off for deploys | @manager | 2025-11-12 | ENG-1245 |
| P1 | Create marketing-engineering notification process | @product | 2025-11-10 | ENG-1246 |
| P2 | Add capacity planning review (quarterly) | @sre | 2025-12-01 | ENG-1247 |

## Lessons Learned

### What Went Well ✓

1. **Quick detection (3 minutes)**
   - Alert fired within 3 minutes of problem
   - On-call acknowledged immediately
   - Monitoring provided good visibility

2. **Clear incident command**
   - IC assigned quickly
   - Roles clear (IC, Ops, Comms)
   - War room effective for coordination

3. **Decisive rollback decision**
   - Didn't waste time debugging in production
   - Rollback decision made quickly (15 minutes)
   - Previous version known-good

4. **No data loss**
   - Timeouts didn't cause data corruption
   - Database integrity maintained
   - No financial discrepancies

5. **Good customer communication**
   - Status page updated promptly
   - Clear, honest messaging
   - Follow-up email sent

### What Went Poorly ✗

1. **No load testing caught the issue**
   - N+1 query not identified before production
   - Code review missed performance issue
   - No automated performance checks

2. **Manual rollback took 10 minutes**
   - Could have been faster with automation
   - Extended incident duration
   - Automation would have reduced impact

3. **Marketing campaign not communicated**
   - 3x traffic spike unexpected
   - No capacity planning opportunity
   - Could have scaled proactively

4. **Missing database performance monitoring**
   - Query patterns not visible
   - No per-endpoint query metrics
   - Slow query detection delayed

5. **No connection pool alerts**
   - Pool exhaustion was sudden
   - Would have benefited from early warning
   - Alert would enable proactive response

### Where We Got Lucky 🍀

1. **Incident during business hours**
   - Team available for quick response
   - If at 2am, could have been much longer

2. **Simple rollback path available**
   - No database migrations in v2.3.4
   - Rollback was straightforward
   - If migration, would need more complex recovery

3. **Database connections recovered quickly**
   - No need to restart database
   - Connections freed automatically
   - Could have required manual intervention

4. **No cascading failures**
   - Dependent services handled timeouts gracefully
   - Circuit breakers worked as designed
   - Could have taken down auth-service

5. **User perception**
   - Most users experienced intermittent errors
   - Not complete outage
   - Perception less severe than reality

## Metrics and Data

### Error Budget

- **Pre-incident budget**: 21.6 minutes (100%)
- **Budget consumed**: 3.24 minutes (15%)
- **Remaining budget**: 18.36 minutes (85%)
- **Status change**: Healthy → Concerning

### Performance Impact

| Metric | Baseline | During Incident | Peak |
|--------|----------|-----------------|------|
| Error rate | < 0.1% | 5-10% | 10% |
| Latency (p95) | 50ms | 200-500ms | 500ms |
| Latency (p99) | 200ms | 1000ms+ | 2000ms |
| DB connections | 30/50 | 50/50 | 50/50 (exhausted) |
| Query time | 50ms | 300ms | 600ms |

### Business Impact

- **Failed transactions**: 150
- **Revenue impact**: $3,000 estimated
- **Support tickets**: 23
- **Refunds issued**: 5 ($100 total)

## Supporting Information

### References

- **Incident Slack thread**: [#incidents-2025-10-27](https://slack.com/archives/incidents-2025-10-27)
- **Grafana dashboard**: [Incident Dashboard](https://grafana.company.com/d/incident-20251027)
- **Code change (v2.3.4)**: [PR #1234](https://github.com/company/api/pull/1234)
- **Rollback (v2.3.3)**: [Deployment Log](https://ci.company.com/deployments/54321)
- **Prometheus alerts**: [Alert History](https://prometheus.company.com/alerts)

### Attendees

- Alice Smith (Incident Commander, SRE)
- Bob Johnson (Operations Lead, Backend)
- Charlie Brown (Communications, Product)
- Diana Martinez (Engineering Manager)
- Eve Wilson (Database Admin)

### Follow-up

- **Postmortem meeting**: 2025-10-28 at 2pm
- **Action item review**: 2025-11-11 (bi-weekly)
- **Retrospective**: 2025-11-25 (assess improvements)

---

**Approval**:
- Incident Commander: Alice Smith (2025-10-27)
- Engineering Manager: Diana Martinez (2025-10-28)
- VP Engineering: Frank Thompson (2025-10-28)

**Document Version**: 1.0
**Status**: Final
