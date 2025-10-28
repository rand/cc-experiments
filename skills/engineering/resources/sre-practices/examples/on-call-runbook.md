# On-Call Runbook: Payment API

Quick reference for on-call engineers supporting the Payment API.

## Service Overview
- **Service**: payment-api
- **Team**: Payments (@payments-team)
- **Slack**: #payments-sre
- **PagerDuty**: https://company.pagerduty.com/services/payment-api
- **Dashboard**: https://grafana.company.com/d/payment-api

## Emergency Contacts
- Primary on-call: Check PagerDuty schedule
- Secondary backup: Check PagerDuty escalation
- Manager: @diana (Slack, +1-555-0100)
- Tech Lead: @alice (Slack, +1-555-0101)
- Executive escalation: VP Eng @frank (+1-555-0200)

## Common Alerts

### High Error Rate (> 1%)
**Severity**: Critical | **Page**: Yes

**Symptoms**: Users experiencing 500 errors, failed transactions

**Quick Checks**:
1. Dashboard: https://grafana.company.com/d/payment-api
2. Recent deployments: `kubectl rollout history deployment/payment-api`
3. Dependency health: Check auth-service, database
4. Traffic spike: Compare current vs normal load

**Common Causes & Fixes**:
- **Recent deployment**: Rollback via `kubectl rollout undo deployment/payment-api`
- **Database issue**: Check connections, consider failover
- **Dependency down**: Enable circuit breaker, use fallback
- **Traffic spike**: Scale horizontally: `kubectl scale deployment/payment-api --replicas=10`

**Escalation**: If not resolved in 30min, escalate to @tech-lead

### High Latency (p95 > 500ms)
**Severity**: Warning | **Page**: Yes

**Quick Checks**:
1. Traces: https://jaeger.company.com/search?service=payment-api
2. Identify slow endpoints
3. Check database query performance
4. Review external API latency

**Common Causes**:
- Slow database queries: Check query plans, add indexes
- External API slow: Check circuit breaker, enable timeout
- Resource constrained: Check CPU/memory, scale if needed

### Database Connection Pool Exhausted
**Severity**: Critical | **Page**: Yes

**Quick Checks**:
1. Connection pool metrics: Check Grafana
2. Long-running queries: `SELECT * FROM pg_stat_activity WHERE state = 'active'`
3. Connection leaks: Check application logs

**Immediate Actions**:
1. Increase pool size (temp): Update config, redeploy
2. Kill long queries: Use `pg_terminate_backend(pid)`
3. Restart app (last resort): `kubectl rollout restart deployment/payment-api`

## Runbook Links
- High Error Rate: https://wiki.company.com/runbooks/high-error-rate
- Database Issues: https://wiki.company.com/runbooks/database
- Deployment Rollback: https://wiki.company.com/runbooks/rollback
- Scaling Guide: https://wiki.company.com/runbooks/scaling
