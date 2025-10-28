---
name: engineering-incident-response
description: Comprehensive incident response practices including lifecycle management, severity classification, war rooms, runbooks, blameless postmortems, and SRE metrics (MTTR, MTTD, MTTA, MTBF)
---

# Incident Response

**Scope**: Complete incident lifecycle from detection through postmortem, including IC role, communication protocols, escalation policies, metrics-driven improvement, and blameless culture development

**Lines**: ~700

**Last Updated**: 2025-10-27

**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Responding to service outages or degradations
- Managing production incidents (SEV-1 through SEV-4)
- Setting up incident response processes
- Defining severity classification criteria
- Creating runbooks and playbooks
- Conducting postmortem meetings
- Implementing on-call rotations
- Measuring incident response effectiveness (MTTR, MTTD, MTTA)
- Building blameless culture

Don't use this skill for:
- Proactive monitoring setup (see `monitoring-observability.md`)
- Deployment strategies (see `deployment-strategies.md`)
- Security incident response (see `security-incident-response`)
- Disaster recovery planning (see `disaster-recovery`)

---

## Core Concepts

### Concept 1: Incident Lifecycle

**Definition**: Structured progression from detection through resolution and learning

**Lifecycle Stages**:
```
Detection → Response → Mitigation → Resolution → Postmortem
    ↓         ↓           ↓            ↓            ↓
  Alert   Assemble   Implement    Verify      Document
           Team       Fix          Normal      Lessons
```

**Key Principles**:
1. **Customer First**: Restore service before finding root cause
2. **Clear Communication**: Keep stakeholders informed
3. **Document Everything**: Timeline, decisions, actions
4. **Learn and Improve**: Every incident is learning opportunity
5. **Blameless**: Focus on systems, not individuals

**Stage Objectives**:
- **Detection**: Minimize MTTD (Mean Time To Detect)
- **Response**: Fast acknowledgment and team assembly
- **Mitigation**: Reduce customer impact quickly
- **Resolution**: Restore full service functionality
- **Postmortem**: Extract lessons, prevent recurrence

---

### Concept 2: Severity Classification

**Definition**: Categorize incidents by impact to determine response urgency

**Severity Levels**:
```
SEV-1 (Critical):
├─ Complete outage or severe degradation
├─ >50% users affected
├─ Business-critical functions unavailable
└─ Response: Immediate, 24/7, all hands

SEV-2 (High):
├─ Significant degradation
├─ 10-50% users affected
├─ Major features impaired
└─ Response: Urgent, specialized team

SEV-3 (Medium):
├─ Minor degradation
├─ 1-10% users affected
├─ Workarounds available
└─ Response: Standard on-call

SEV-4 (Low):
├─ Minimal/no user impact
├─ Internal tools affected
├─ Cosmetic issues
└─ Response: Business hours
```

**Classification Matrix**:
| Users Affected | Revenue Impact | SLA Risk | Severity |
|----------------|----------------|----------|----------|
| >50%           | >$10K/hr      | Yes      | SEV-1    |
| 10-50%         | $1-10K/hr     | Maybe    | SEV-2    |
| 1-10%          | <$1K/hr       | No       | SEV-3    |
| <1%            | None          | No       | SEV-4    |

**Escalation/De-escalation**:
- Escalate when impact worse than assessed
- De-escalate when mitigation reduces impact
- Re-assess severity every 30 minutes

---

### Concept 3: Incident Commander (IC) Role

**Definition**: Single person responsible for coordinating incident response

**IC Responsibilities**:
```
Coordinate: Direct technical responders
Decide: Final call on mitigation strategies
Communicate: Ensure stakeholders informed
Document: Maintain timeline
Drive: Keep team focused on restoration
Declare: Determine when resolved
```

**IC is NOT**:
- The person fixing the technical issue
- The person writing all updates
- Responsible for root cause (during incident)
- Working on multiple tasks simultaneously

**IC Decision Framework**:
```
Rollback? → Recent deployment + High confidence issue? → YES
          → Unsure or no deployment? → Investigate 15 min → Still bad? → ROLLBACK

Escalate? → Need expertise not on-call? → Page specialist
          → Need management decision? → Page manager
          → Need vendor help? → Open critical ticket

Resolve? → All criteria met + 15+ min stable? → YES
         → Any criteria failed? → Continue monitoring
```

---

## Patterns

### Pattern 1: War Room Coordination

**Problem**: Need structured communication during chaotic incidents

**War Room Structure**:
```
Channel: #incident-YYYYMMDD-description
├─ IC: Coordinates, makes decisions
├─ Tech Lead: Hands on keyboard, implements
├─ Comms Lead: External updates
├─ Scribe: Documents timeline
└─ SMEs: Domain experts as needed

Communication Format:
[HH:MM] [@person] [TYPE] Description

Types:
- ACTION: Something done
- DECISION: Choice made
- OBSERVATION: Data/status
- QUESTION: Need info
- ANSWER: Response
```

**Example War Room Flow**:
```
[14:30] @ic [DECISION] Declaring SEV-1, creating war room
[14:32] @tech-lead [OBSERVATION] Error rate 35%, started 14:20
[14:35] @tech-lead [OBSERVATION] Correlates with deployment v2.3.1
[14:37] @ic [DECISION] Rollback deployment
[14:40] @tech-lead [ACTION] Rollback complete
[14:45] @tech-lead [OBSERVATION] Error rate declining to 8%
[14:50] @ic [DECISION] Monitoring 15 min before resolving
```

**Benefits**:
- Clear roles prevent confusion
- Structured updates create timeline
- Decision documentation for postmortem
- Stakeholders get visibility

---

### Pattern 2: Blameless Postmortem

**Problem**: Need to learn from incidents without creating fear

**Blameless Principles**:
```
Focus on:
✓ Systems and processes
✓ "The monitoring didn't..."
✓ "The process allowed..."
✓ Why system permitted issue

Avoid:
✗ Individual blame
✗ "Alice deployed bad code"
✗ "Bob didn't notice"
✗ Who made mistake
```

**Postmortem Structure**:
```markdown
# Postmortem: [Title]

## Executive Summary
3-sentence summary: what happened, impact, resolution

## Impact
- User impact metrics
- Business impact
- Technical metrics

## Timeline
| Time | Event |
|------|-------|
| ...  | ...   |

## Root Cause Analysis (Five Whys)
1. Why did X fail? → Answer
2. Why did that happen? → Answer
3. Why did that happen? → Answer
4. Why did that happen? → Answer
5. Why did that happen? → Answer

## What Went Well
- Positives to reinforce

## What Went Poorly
- Areas for improvement (blameless!)

## Action Items
| Action | Owner | Deadline | Category |
|--------|-------|----------|----------|
| ...    | ...   | ...      | Prevent  |

## Lessons Learned
Key takeaways for organization
```

**Action Item Categories**:
- **Prevent**: Stop recurrence
- **Detect**: Find faster
- **Respond**: Mitigate faster
- **Process**: Improve workflow

---

### Pattern 3: Metrics-Driven Improvement

**Problem**: Need objective measures of incident response effectiveness

**The Four Golden Metrics**:
```
MTTR (Mean Time To Repair):
├─ Time from incident start to resolution
├─ Target: <1 hour SEV-1, <4 hours SEV-2
└─ Improve: Better runbooks, automation, rollback

MTTD (Mean Time To Detect):
├─ Time from issue start to detection
├─ Target: <5 minutes
└─ Improve: Synthetic monitoring, better alerts

MTTA (Mean Time To Acknowledge):
├─ Time from alert to acknowledgment
├─ Target: <5 min SEV-1, <15 min SEV-2
└─ Improve: Clear on-call, alert quality

MTBF (Mean Time Between Failures):
├─ Time between incidents
├─ Target: Increasing over time
└─ Improve: Action item completion, testing
```

**Measurement Example**:
```python
# Calculate MTTR
incidents = load_resolved_incidents()
durations = [
    (inc.resolved_at - inc.started_at).total_seconds() / 60
    for inc in incidents
]
mttr_minutes = mean(durations)

# By severity
sev1_mttr = mean([d for inc, d in zip(incidents, durations)
                   if inc.severity == 'SEV-1'])
```

**SLO and Error Budget**:
```yaml
service: api
slo:
  availability: 99.9%  # Max 43.8 min downtime/month
  error_rate: 0.1%

error_budget:
  monthly_downtime: 43.8 minutes
  used_this_month: 135 minutes  # 308% - EXHAUSTED

actions_when_exhausted:
  - Freeze non-critical deployments
  - Focus on reliability
  - Postmortem all incidents
  - Mandatory chaos engineering
```

---

## Checklist

### Incident Response Checklist

**Initial Response (0-5 min)**:
- [ ] Acknowledge alert
- [ ] Assess severity and impact
- [ ] Create incident ticket
- [ ] Notify stakeholders
- [ ] Assign Incident Commander
- [ ] Create war room (#incident-YYYYMMDD-description)
- [ ] Begin timeline documentation

**Mitigation (5-60 min)**:
- [ ] Identify recent changes (deployments, configs)
- [ ] Determine mitigation strategy (rollback/scale/fix)
- [ ] Implement mitigation
- [ ] Verify impact reduced
- [ ] Provide updates every 15-30 minutes
- [ ] Document all actions and decisions

**Resolution**:
- [ ] Error rates back to baseline
- [ ] Latency within SLOs
- [ ] No active customer reports
- [ ] System stable 15+ minutes
- [ ] All health checks passing
- [ ] Dependencies verified
- [ ] Send final customer notification
- [ ] Schedule postmortem (24-48 hours)

**Postmortem (24-72 hours)**:
- [ ] Compile timeline from war room
- [ ] Gather metrics and graphs
- [ ] Draft postmortem document
- [ ] Conduct postmortem meeting (blameless)
- [ ] Define action items with owners
- [ ] Publish postmortem internally
- [ ] Follow up on action items

---

## Anti-Patterns

**Process Anti-Patterns**:
```
❌ No clear IC → Multiple people making conflicting decisions
❌ Skip severity classification → Wrong response urgency
❌ Investigate before mitigating → Customers suffer longer
❌ No communication updates → Stakeholders anxious, duplicate work
❌ Resolve too early → Issue recurs immediately
❌ Skip postmortem → No learning, same issue repeats
```

**Communication Anti-Patterns**:
```
❌ Blame individuals → Fear, information hiding
❌ Vague updates → Stakeholders don't understand status
❌ Irregular updates → Anxiety and escalations
❌ Over-technical → Non-engineers confused
❌ No final notification → Unclear if resolved
```

**Metrics Anti-Patterns**:
```
❌ Only measure MTTR → Ignore detection and acknowledgment
❌ Don't track by severity → Can't prioritize improvements
❌ No trend analysis → Miss systemic issues
❌ Ignore action item completion → Same incidents repeat
❌ Celebrate "hero" fixes → Discourage prevention
```

---

## Recovery

**When Incident Gets Worse**:
```
1. STOP current mitigation if making things worse
2. ROLLBACK to last known good state
3. RE-ASSESS severity (may need to escalate)
4. PAGE additional help (specialists, manager)
5. COMMUNICATE change in status
6. CONSIDER maintenance mode to stop damage
```

**When IC Needs to Hand Off**:
```
1. Brief new IC on:
   - Current status and impact
   - What's been tried
   - Current strategy
   - Key people and roles
   - Pending decisions

2. New IC announces role in war room
3. Old IC stays available for questions
4. Document handoff in timeline
```

**When Postmortem Becomes Blame**:
```
1. Facilitator intervenes immediately
2. Reframe: "What allowed this?" not "Who did this?"
3. Focus on systems: monitoring, processes, tools
4. If continues, pause meeting
5. Reset expectations: blameless or don't continue
```

---

## Level 3: Resources

**Extended Documentation**: [REFERENCE.md](resources/REFERENCE.md) (3,200+ lines)
- Complete incident lifecycle with detailed procedures
- Comprehensive severity classification framework
- Incident Commander playbook with decision trees
- Communication protocols and templates
- Detection and alerting strategies
- War room setup and coordination
- Runbook and playbook structures
- Blameless postmortem methodology
- Metrics and measurement (MTTR, MTTD, MTTA, MTBF)
- On-call management best practices
- Escalation policies and decision matrices
- Tool integrations (PagerDuty, Slack, Statuspage)
- SRE practices (chaos engineering, error budgets)

**Scripts**: Production-ready tools in `resources/scripts/`
- `create_incident.py` (600 lines): Create and track incidents with structured templates, severity classification, war room setup, and timeline management
- `analyze_mttr.py` (550 lines): Comprehensive MTTR/MTTD/MTTA analysis, incident patterns, trends, recommendations, and service comparisons
- `generate_postmortem.py` (500 lines): Generate blameless postmortem documents from incidents with templates for common scenarios (deployment, resource exhaustion, dependency failures)

**Examples**: Production-ready examples in `resources/examples/`
- **templates/**:
  - `sev1-incident-template.md`: Complete SEV-1 response template with checklists, communication formats, decision trees, and role definitions
  - `escalation-policy.yaml`: Comprehensive escalation policies for services, severity levels, time-based rules, and vendor contacts
- **runbooks/**:
  - `database-connection-pool-exhausted.md`: Production runbook with symptoms, diagnosis steps, mitigation strategies, and prevention actions
- **integrations/**:
  - `pagerduty-integration.py`: Full PagerDuty API integration for incident creation, updates, escalation, on-call schedules, and Events API v2
  - `slack-incident-bot.py`: Slack bot for war room creation, status updates, role assignment, timeline tracking, and resolution notifications
- **workflows/**:
  - `sev1-response-workflow.md`: Complete SEV-1 walkthrough from detection through postmortem with real timeline, metrics, and lessons learned

All scripts include:
- `--help` for comprehensive usage documentation
- `--json` output for programmatic integration
- Executable permissions and proper shebang lines
- Type hints and docstrings
- Error handling and validation
- Example usage in main block

**Usage**:
```bash
# Create incident with tracking
./create_incident.py create --title "High API error rate" \
  --severity SEV-1 --impact "50% of users affected" --service api

# Analyze incident metrics
./analyze_mttr.py --period 30 --verbose --compare-services

# Generate postmortem from incident
./generate_postmortem.py --incident-id INC-123 \
  --authors alice,bob --template deployment --output postmortem.md

# PagerDuty integration
python pagerduty-integration.py --create --service-id PXXXXXX

# Slack war room
python slack-incident-bot.py create-war-room \
  --incident-id INC-123 --title "API errors" --severity SEV-1
```

---

## Related Skills

- `monitoring-observability.md`: Alerting and detection
- `deployment-strategies.md`: Rollback procedures
- `on-call-management.md`: Rotation and compensation
- `sre-practices.md`: SLOs, error budgets, chaos engineering
- `technical-writing.md`: Documentation and runbooks
- `communication-stakeholder.md`: Update templates
