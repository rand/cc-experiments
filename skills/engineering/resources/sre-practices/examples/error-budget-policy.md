# Error Budget Policy

**Service**: Payment API
**Owner**: Payments Team
**Last Updated**: 2025-10-27
**Version**: 2.0

## Overview

This document defines how we use error budgets to balance reliability and feature velocity. The error budget is the allowed amount of unreliability, calculated from our SLO targets.

## Error Budget Calculation

### Current SLOs

| Metric | Target | Error Budget |
|--------|--------|--------------|
| Availability | 99.95% | 0.05% = 21.6 minutes/month |
| Latency (p95) | < 300ms | 5% requests may exceed |
| Latency (p99) | < 1s | 1% requests may exceed |

### Time-Based Budget

```
Total time in 30 days: 43,200 minutes
Error budget: 0.05% = 21.6 minutes
Budget per week: ~5.4 minutes
Budget per day: ~0.72 minutes (43 seconds)
```

## Budget Consumption Zones

### Zone 1: Healthy (< 25% consumed)

**Status**: 🟢 Green

**Characteristics**:
- Less than 5.4 minutes of downtime consumed
- System operating well within SLO
- Plenty of budget for innovation

**Actions**:
- **Development**: Normal velocity, full feature work
- **Releases**: Continuous deployment enabled
- **Changes**: No restrictions, experiment freely
- **Monitoring**: Standard dashboards and alerts

**Meeting Cadence**: Monthly SLO review

**Approval Required**: No

---

### Zone 2: Concerning (25-50% consumed)

**Status**: 🟡 Yellow

**Characteristics**:
- 5.4 - 10.8 minutes consumed
- Elevated risk of SLO miss
- Need to be more careful with changes

**Actions**:
- **Development**: Add reliability tasks to sprint backlog
- **Releases**: Staged rollouts with extended monitoring
- **Changes**: Risk assessment required for risky changes
- **Monitoring**: Increase alert sensitivity, daily checks

**Restrictions**:
- Defer non-critical features
- No breaking changes without careful review
- Extended canary periods (50% → 100% over 2 hours)

**Meeting Cadence**: Bi-weekly SLO review

**Approval Required**: No, but Tech Lead should be informed

**Communication**: Notify team in #payments-sre Slack channel

---

### Zone 3: Critical (50-75% consumed)

**Status**: 🟠 Orange

**Characteristics**:
- 10.8 - 16.2 minutes consumed
- High risk of missing SLO
- Urgent reliability focus needed

**Actions**:
- **Development**: 50% sprint capacity on reliability improvements
- **Releases**: Manual approval required for all deployments
- **Changes**: Feature freeze on non-critical changes
- **Monitoring**: Daily SLO review meetings, extended on-call

**Restrictions**:
- **Feature freeze**: Only critical features and bug fixes
- **All changes require approval** from Tech Lead AND Engineering Manager
- **Mandatory postmortems** for all incidents
- **Extended canary**: 5% → 25% → 50% → 100% over 6 hours minimum

**Required Actions**:
1. Identify top sources of error budget consumption
2. Create action items to reduce toil and improve reliability
3. Review recent changes for potential rollback
4. Assess if recent features should be rolled back or fixed

**Meeting Cadence**: Daily standup focused on SLO

**Approval Required**: Yes (Tech Lead + Engineering Manager)

**Communication**:
- Slack: #payments-sre, #engineering-all
- Email: payments-team@company.com
- Escalation: VP Engineering notified

---

### Zone 4: Exhausted (> 75% consumed)

**Status**: 🔴 Red

**Characteristics**:
- More than 16.2 minutes consumed
- SLO at risk of breach
- Emergency response mode

**Actions**:
- **Development**: 100% focus on reliability, zero feature work
- **Releases**: Complete feature freeze, emergency fixes only
- **Changes**: Incident response mode
- **Monitoring**: War room, twice-daily executive updates

**Restrictions**:
- **Complete feature freeze**: No new features, period
- **Emergency fixes only**: Must be approved by VP Engineering or CTO
- **Rigorous testing**: All changes tested in staging with load testing
- **Extended rollout**: Manual, gradual rollout with constant monitoring

**Required Actions**:
1. **Executive escalation**: Notify VP Engineering, CTO immediately
2. **Root cause analysis**: Identify all sources of budget consumption
3. **Remediation plan**: Create detailed plan to restore reliability
4. **Daily reports**: Written updates to executives twice daily
5. **Postmortem**: Comprehensive review of what led to exhaustion

**Meeting Cadence**: Twice daily war room

**Approval Required**: Yes (VP Engineering OR CTO)

**Communication**:
- Slack: #incidents, #engineering-all, #executive
- Email: engineering-all@company.com, executives@company.com
- Status page: Public notification if customer-impacting

---

## Error Budget Attribution

We track what consumes our error budget to identify improvement opportunities.

### Attribution Categories

1. **Infrastructure failures** (cloud provider, network, hardware)
2. **Deployment-related** (bad releases, config changes)
3. **Dependency failures** (upstream services, databases)
4. **Traffic spikes** (unexpected load, DDoS)
5. **Application bugs** (code defects)
6. **Human error** (manual operations, misconfigurations)
7. **Scheduled maintenance** (planned downtime)

### Monthly Attribution Report

```
Error Budget Consumption (October 2025)
Total consumed: 12.5 minutes (57.8%)

Attribution:
1. Deployment-related: 6.2 minutes (48.7%)
   - Bad release (v2.5.1): 5 minutes
   - Config rollout issue: 1.2 minutes

2. Dependency failures: 4.5 minutes (36%)
   - Database failover: 3 minutes
   - Auth service outage: 1.5 minutes

3. Infrastructure: 1.8 minutes (14.4%)
   - AWS us-east-1 network issue: 1.8 minutes

Action Items:
- Improve pre-deployment testing (owner: Alice)
- Implement automatic rollback on error spike (owner: Bob)
- Add caching layer for auth service (owner: Charlie)
```

## Burn Rate Alerting

We use multi-window, multi-burn-rate alerts based on Google SRE best practices.

### Alert Thresholds

| Window | Burn Rate | Impact | Alert | Action |
|--------|-----------|--------|-------|--------|
| 1 hour | 14.4x | 5% budget in 1 hour | Page | Immediate response |
| 6 hours | 6x | 5% budget in 6 hours | Page | Urgent response |
| 24 hours | 3x | 5% budget in 24 hours | Ticket | Schedule investigation |

### Example Burn Rates

**Normal operation**: 1x burn rate
- Consuming budget at expected rate
- On track to use 100% by end of window

**Fast burn**: 14.4x burn rate
- Consuming budget 14.4x faster than normal
- Will exhaust 5% of budget in 1 hour
- **Action**: Page on-call immediately, start incident response

**Slow burn**: 3x burn rate
- Consuming budget 3x faster than normal
- Will exhaust budget in 10 days instead of 30
- **Action**: Create ticket, investigate during business hours

## Budget Reset Policy

### Rolling Window

We use a 30-day rolling window, which means:
- Budget is continuously calculated
- Old incidents "age out" after 30 days
- No sudden resets (avoids cliff-edge behavior)

**Implications**:
- Past incidents impact budget for 30 days
- Recent reliability improvements take time to reflect
- More stable, predictable budget consumption

### No Gaming

**We do not reset budgets early**. This would undermine the purpose of error budgets. If the budget is exhausted:
1. We focus on reliability improvements
2. We defer feature work until budget recovers
3. We learn from what caused the exhaustion

## Stakeholder Communication

### Internal Communication

**Zone 1-2**: Standard Slack notifications
**Zone 3**: Daily email updates to engineering
**Zone 4**: Twice-daily updates to executives

### External Communication

**Customer notification required when**:
- SLA breach (< 99.9% availability)
- Major incidents lasting > 15 minutes
- Data integrity issues

**Status page updates**:
- All Sev1 incidents
- Sev2 incidents lasting > 30 minutes
- Scheduled maintenance

## Review and Adjustment

### Quarterly SLO Review

**Participants**: SRE, Engineering, Product, Customer Success

**Agenda**:
1. Review past quarter achievement
2. Analyze error budget consumption patterns
3. Assess if SLO targets are appropriate
4. Update error budget policy if needed
5. Identify top reliability improvements

**Questions to ask**:
- Did we meet our SLO?
- If yes, should we tighten it (too much budget left)?
- If no, should we loosen it or improve reliability?
- Is the error budget policy working?
- Are teams responding appropriately to budget consumption?

### Policy Adjustments

**When to adjust thresholds**:
- Team consistently exhausts budget: Loosen SLO or improve reliability
- Team never uses budget: Tighten SLO to enable more velocity
- Policy feels arbitrary: Adjust zones based on actual impact

**Process**:
1. Propose changes in quarterly review
2. Get consensus from engineering and product
3. Document changes and rationale
4. Update this policy
5. Communicate to all stakeholders

## Examples and Case Studies

### Example 1: Healthy Budget Usage

**Scenario**: Early in month, 10% budget consumed
- Status: Zone 1 (Healthy)
- Action: Continue normal operations
- Velocity: Full speed ahead

### Example 2: Bad Deployment

**Scenario**: Bad deployment consumes 30% budget in 2 hours
- Status: Zone 2 (Concerning)
- Action:
  1. Rollback deployment immediately
  2. Mandatory postmortem
  3. Implement better pre-deployment testing
  4. Switch to Zone 2 restrictions
  5. Monitor budget closely

### Example 3: Approaching Exhaustion

**Scenario**: 70% budget consumed with 10 days left in window
- Status: Zone 3 (Critical)
- Action:
  1. Feature freeze on non-critical work
  2. Daily standup focused on reliability
  3. Identify and fix top sources of errors
  4. Consider rolling back recent risky features
  5. Notify VP Engineering
  6. Create remediation plan

### Example 4: Budget Exhausted

**Scenario**: 85% budget consumed with 15 days left
- Status: Zone 4 (Exhausted)
- Action:
  1. Complete feature freeze
  2. Executive war room
  3. Comprehensive root cause analysis
  4. Detailed remediation plan
  5. Twice-daily executive updates
  6. Focus 100% on reliability until budget recovers

## Appendix: Budget Calculation Formulas

### Time-Based SLO

```
Error Budget (minutes) = Total Time × (1 - SLO Target)

Example (99.95% over 30 days):
Error Budget = 30 days × 24 hours × 60 minutes × (1 - 0.9995)
             = 43,200 minutes × 0.0005
             = 21.6 minutes
```

### Request-Based SLO

```
Error Budget (requests) = Total Requests × (1 - SLO Target)

Example (99.9% success rate, 10M requests):
Error Budget = 10,000,000 × (1 - 0.999)
             = 10,000 failed requests allowed
```

### Burn Rate

```
Burn Rate = (Budget Consumed / Time Elapsed) / (1 / Window Duration)

Example (15% budget consumed in 3 days of 30-day window):
Expected Consumption = 3 / 30 = 10%
Actual Consumption = 15%
Burn Rate = 15% / 10% = 1.5x
```

### Prediction

```
Hours Until Exhaustion = (Remaining Budget) / (Current Burn Rate)

Example (40% budget consumed in 120 hours):
Burn Rate = 0.4 / 120 = 0.00333 per hour
Remaining = 0.6
Hours Until Exhaustion = 0.6 / 0.00333 = 180 hours (7.5 days)
```

---

**Document Control**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 2.0 | 2025-10-27 | SRE Team | Updated thresholds, added burn rate alerting |
| 1.1 | 2025-08-15 | SRE Team | Added attribution tracking |
| 1.0 | 2025-01-10 | SRE Team | Initial policy |

**Approval**:
- Tech Lead: Alice Smith (2025-10-27)
- Engineering Manager: Bob Jones (2025-10-27)
- VP Engineering: Charlie Brown (2025-10-27)
