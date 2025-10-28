# Feature Flags Reference Guide

Comprehensive reference for feature flag management, implementation, and best practices.

**Version**: 1.0
**Last Updated**: 2025-10-27

## Table of Contents

1. [Introduction](#1-introduction)
2. [Feature Flag Types](#2-feature-flag-types)
3. [Flag Management Platforms](#3-flag-management-platforms)
4. [Progressive Delivery Patterns](#4-progressive-delivery-patterns)
5. [Targeting and Segmentation](#5-targeting-and-segmentation)
6. [Rollout Strategies](#6-rollout-strategies)
7. [A/B Testing and Experimentation](#7-ab-testing-and-experimentation)
8. [Flag Lifecycle Management](#8-flag-lifecycle-management)
9. [Technical Debt Prevention](#9-technical-debt-prevention)
10. [Client-Side vs Server-Side](#10-client-side-vs-server-side)
11. [Performance Considerations](#11-performance-considerations)
12. [Security and Compliance](#12-security-and-compliance)
13. [Testing Strategies](#13-testing-strategies)
14. [Monitoring and Observability](#14-monitoring-and-observability)
15. [Architecture Patterns](#15-architecture-patterns)
16. [Integration Patterns](#16-integration-patterns)
17. [Troubleshooting](#17-troubleshooting)
18. [Best Practices](#18-best-practices)
19. [Anti-Patterns](#19-anti-patterns)
20. [Reference Implementation](#20-reference-implementation)

---

## 1. Introduction

### What are Feature Flags?

Feature flags (also called feature toggles, feature switches, or feature gates) are a software development technique that allows teams to enable, disable, or modify application behavior without deploying new code.

### Why Use Feature Flags?

**Benefits**:
- **Risk Reduction**: Deploy code without exposing features
- **Gradual Rollouts**: Release to small user segments first
- **A/B Testing**: Experiment with multiple variations
- **Kill Switches**: Quickly disable problematic features
- **Trunk-Based Development**: Keep code in main branch
- **Faster Iteration**: Decouple deployment from release

**Use Cases**:
- Progressive feature rollouts
- Canary deployments
- Blue-green deployments
- A/B and multivariate testing
- Emergency kill switches
- Permission-based access
- Infrastructure migration
- Performance tuning
- Beta programs
- Scheduled releases

### Core Concepts

**Flag**: Boolean or multivariate configuration that controls behavior

**Evaluation**: Process of determining flag value for a user/context

**Variation**: One of multiple possible flag values

**Targeting**: Rules that determine which users see which variation

**Rollout**: Gradual exposure of users to a feature

**Context**: User/request information used for targeting

---

## 2. Feature Flag Types

### 2.1 Release Toggles

**Purpose**: Control deployment of new features

**Characteristics**:
- Short-lived (should be removed after full rollout)
- Binary (on/off)
- Progressive rollout support
- High business visibility

**When to Use**:
- New feature launches
- Breaking changes
- UI redesigns
- Infrastructure changes

**Example**:
```python
if feature_flags.is_enabled('new-dashboard'):
    return new_dashboard_view()
else:
    return legacy_dashboard_view()
```

**Lifecycle**:
1. Create flag (default: off)
2. Deploy code with flag checks
3. Test in staging
4. Gradually rollout in production
5. Monitor metrics
6. Remove flag after 100% rollout

**Best Practices**:
- Set expiration date on creation
- Track rollout metrics
- Plan removal from day one
- Document rollout schedule
- Have rollback plan

### 2.2 Experiment Toggles

**Purpose**: A/B testing and multivariate experiments

**Characteristics**:
- Multiple variations
- Statistical analysis required
- Metrics tracking integrated
- User bucketing consistent
- Medium-term duration

**When to Use**:
- A/B tests
- Multivariate tests
- UX optimization
- Performance tuning
- Conversion optimization

**Example**:
```python
variant = feature_flags.get_variation('checkout-flow', user)
if variant == 'single-page':
    return single_page_checkout()
elif variant == 'multi-step':
    return multi_step_checkout()
else:  # control
    return current_checkout()
```

**Requirements**:
- Sample size calculation
- Statistical significance testing
- Consistent user bucketing
- Metrics instrumentation
- Analysis tools

**Best Practices**:
- Define success metrics upfront
- Calculate required sample size
- Run until statistical significance
- Document hypothesis and results
- Clean up after conclusion

### 2.3 Ops Toggles

**Purpose**: Operational control and system behavior tuning

**Characteristics**:
- Long-lived
- Frequently changed
- Technical/operational focus
- Low business visibility
- Configuration-oriented

**When to Use**:
- Circuit breakers
- Rate limiting
- Cache configuration
- Database connection pools
- Logging levels
- Feature degradation

**Example**:
```python
config = feature_flags.get_variation('api-rate-limits', user)
rate_limiter.configure(
    requests_per_minute=config['rpm'],
    burst_limit=config['burst']
)
```

**Best Practices**:
- Version configurations
- Monitor after changes
- Document operational impact
- Use gradual rollouts
- Have safe defaults

### 2.4 Permission Toggles

**Purpose**: Control access based on user attributes

**Characteristics**:
- Long-lived
- User-attribute based
- Fine-grained access control
- Integration with auth systems
- Stable over time

**When to Use**:
- Premium features
- Beta programs
- Internal tools
- Tiered access
- Geographic restrictions

**Example**:
```python
if feature_flags.is_enabled('premium-features', user):
    # User has premium plan
    return premium_feature_set()
else:
    return standard_feature_set()
```

**Best Practices**:
- Integrate with IAM
- Clear permission model
- Audit access patterns
- Document entitlements
- Sync with billing

### 2.5 Kill Switches

**Purpose**: Emergency disable of problematic features

**Characteristics**:
- Critical business function
- Instant effect required
- Default to safe state
- Override all other logic
- Well-tested in drills

**When to Use**:
- Performance issues
- Data corruption risk
- Security vulnerabilities
- Third-party outages
- Cascading failures

**Example**:
```python
if not feature_flags.is_enabled('ml-recommendations'):
    # Kill switch active - use fallback
    return static_recommendations()
else:
    return ml_recommendations()
```

**Best Practices**:
- Test regularly
- Clear ownership
- Documented procedures
- Automated monitoring
- Incident response integration
- Post-incident cleanup

---

## 3. Flag Management Platforms

### 3.1 LaunchDarkly

**Overview**: Enterprise feature management platform

**Key Features**:
- Real-time flag updates
- Advanced targeting rules
- A/B testing built-in
- SDKs for 20+ languages
- Audit logs and compliance
- Flag dependencies
- Workflow automation

**Pricing**: Starts at $8.33/seat/month

**Best For**: Enterprise teams, complex targeting needs

**SDK Example**:
```python
import ldclient
from ldclient.config import Config

# Initialize
ldclient.set_config(Config(sdk_key="your-sdk-key"))
client = ldclient.get()

# Evaluate flag
user = {
    "key": "user-123",
    "email": "user@example.com",
    "custom": {"plan": "premium"}
}

enabled = client.variation("new-feature", user, False)
```

**Pros**:
- Mature platform
- Excellent documentation
- Strong enterprise features
- Responsive support
- Active development

**Cons**:
- Expensive for small teams
- Complex for simple needs
- Vendor lock-in risk

**Integration**:
- CI/CD: GitHub Actions, Jenkins, CircleCI
- APM: Datadog, New Relic, Honeycomb
- Analytics: Segment, Amplitude
- Issue Tracking: Jira, Linear

### 3.2 Split

**Overview**: Feature flagging and experimentation platform

**Key Features**:
- Impact analysis
- Real-time monitoring
- Advanced segmentation
- Built-in analytics
- Data export
- IDE integrations

**Pricing**: Starts at $33/developer/month

**Best For**: Product teams, data-driven orgs

**SDK Example**:
```javascript
const SplitFactory = require('@splitsoftware/splitio').SplitFactory;

const factory = SplitFactory({
  core: {
    authorizationKey: 'your-api-key'
  }
});

const client = factory.client();

client.on(client.Event.SDK_READY, () => {
  const treatment = client.getTreatment('user-123', 'new-feature');
  if (treatment === 'on') {
    // Feature enabled
  }
});
```

**Pros**:
- Strong analytics
- Impact tracking
- Good experimentation tools
- Clean UI

**Cons**:
- Higher pricing
- Learning curve
- Less flexible targeting than LaunchDarkly

### 3.3 Unleash

**Overview**: Open-source feature toggle system

**Key Features**:
- Self-hosted or cloud
- Multiple strategies (gradual rollout, user segments)
- Client-side and server-side SDKs
- Admin UI
- Metrics and events
- Open source (Apache 2.0)

**Pricing**: Free (self-hosted), Pro starts at $80/month

**Best For**: Teams wanting control, budget-conscious, self-hosted needs

**SDK Example**:
```python
from UnleashClient import UnleashClient

client = UnleashClient(
    url="http://unleash.example.com",
    app_name="my-app",
    custom_headers={'Authorization': 'my-api-token'}
)

client.initialize_client()

enabled = client.is_enabled("new-feature", {
    'userId': 'user-123'
})
```

**Pros**:
- Open source
- Self-hosted option
- Lower cost
- Good community
- Privacy control

**Cons**:
- Less mature than commercial options
- Self-hosting operational burden
- Fewer integrations

### 3.4 ConfigCat

**Overview**: Simple, affordable feature flag service

**Key Features**:
- Simple UI
- Targeting rules
- Config inheritance
- Change history
- Webhooks
- SDK for 15+ languages

**Pricing**: Free tier, Pro starts at $49/month

**Best For**: Small teams, simple use cases, budget-conscious

**SDK Example**:
```javascript
const configcat = require('configcat-node');

const client = configcat.createClient('your-sdk-key');

client.getValueAsync('new-feature', false, {
  identifier: 'user-123',
  custom: { plan: 'premium' }
}).then((value) => {
  if (value) {
    // Feature enabled
  }
});
```

**Pros**:
- Simple to use
- Affordable
- Good documentation
- Fast

**Cons**:
- Fewer features than enterprise platforms
- Limited analytics
- Smaller ecosystem

### 3.5 Custom/Roll Your Own

**When to Consider**:
- Unique requirements
- Cost sensitivity
- Privacy/security needs
- Simple use cases
- Learning/experimentation

**Minimum Viable Implementation**:
```python
# Simple file-based flags
import json
from typing import Any, Dict

class FeatureFlags:
    def __init__(self, config_file: str):
        with open(config_file) as f:
            self.flags = json.load(f)

    def is_enabled(self, flag_key: str, user_id: str, default: bool = False) -> bool:
        flag = self.flags.get(flag_key, {})
        if not flag.get('enabled', False):
            return False

        # Check user allowlist
        if user_id in flag.get('users', []):
            return True

        # Check percentage rollout
        percentage = flag.get('percentage', 0)
        bucket = hash(f"{flag_key}:{user_id}") % 100
        return bucket < percentage
```

**Pros**:
- Full control
- No vendor lock-in
- No ongoing costs
- Privacy control
- Customizable

**Cons**:
- Development/maintenance burden
- Missing features (analytics, UI, etc.)
- No support
- Reinventing the wheel

**Recommendation**: Use managed platform unless you have specific needs or constraints

---

## 4. Progressive Delivery Patterns

### 4.1 Canary Deployment

**Definition**: Deploy to small subset of users/servers first, then gradually expand

**When to Use**:
- High-risk changes
- Performance-sensitive features
- Infrastructure changes
- Database migrations

**Implementation**:
```python
# Server-side canary
if server_hostname in canary_hosts:
    use_new_implementation()
else:
    use_current_implementation()

# User-based canary
if user_id in canary_users:
    use_new_implementation()
else:
    use_current_implementation()
```

**Rollout Schedule**:
```
Day 0: Internal users (10 users)
Day 1: Canary users (100 users)
Day 3: 1% of traffic
Day 5: 5% of traffic
Day 7: 25% of traffic
Day 10: 50% of traffic
Day 14: 100% of traffic
```

**Monitoring Checklist**:
- [ ] Error rate within threshold
- [ ] Latency p95/p99 stable
- [ ] Resource utilization normal
- [ ] No customer complaints
- [ ] Metrics match control group

**Rollback Triggers**:
- Error rate > 2x baseline
- Latency p95 > 1.5x baseline
- Customer complaints
- Resource exhaustion
- Data integrity issues

### 4.2 Blue-Green Deployment

**Definition**: Maintain two identical production environments, switch traffic between them

**When to Use**:
- Zero-downtime deployments
- Easy rollback required
- Database migrations
- Full system changes

**Implementation**:
```python
# Load balancer level
if feature_flags.is_enabled('use-green-environment'):
    route_to_green_environment()
else:
    route_to_blue_environment()
```

**Process**:
1. Deploy to green (inactive) environment
2. Test green environment
3. Gradually shift traffic to green
4. Monitor metrics
5. Shift remaining traffic
6. Keep blue as rollback option
7. Deploy next version to blue

**Advantages**:
- Instant rollback
- Testing in production-like environment
- No partial state

**Disadvantages**:
- Requires 2x infrastructure
- Database changes complex
- State synchronization issues

### 4.3 Ring Deployment

**Definition**: Progressive rollout across concentric user rings

**Rings**:
- **Ring 0**: Internal users, developers (100%)
- **Ring 1**: Early adopters, beta users (50-100%)
- **Ring 2**: Premium/power users (25-50%)
- **Ring 3**: All users (0-100%)

**Implementation**:
```python
def get_user_ring(user):
    if user.is_internal:
        return 0
    elif user.beta_opted_in:
        return 1
    elif user.plan in ['premium', 'enterprise']:
        return 2
    else:
        return 3

ring = get_user_ring(current_user)
if ring <= feature_config['current_ring']:
    use_new_feature()
```

**Ring Advancement Criteria**:
- No critical bugs in current ring
- Error rate < threshold
- Metrics look good
- 48 hours of stability
- Stakeholder approval

**Timeline Example**:
```
Week 1: Ring 0 (100%)
Week 2: Ring 1 (100%)
Week 3: Ring 2 (50%)
Week 4: Ring 2 (100%)
Week 5: Ring 3 (25%)
Week 6: Ring 3 (50%)
Week 7: Ring 3 (100%)
```

### 4.4 Percentage Rollout

**Definition**: Gradually increase percentage of users seeing feature

**When to Use**:
- Standard feature releases
- Low to medium risk changes
- A/B tests
- Load testing in production

**Implementation (Consistent Hashing)**:
```python
def is_enabled_for_user(flag_key: str, user_id: str, percentage: float) -> bool:
    """
    Consistent bucketing - same user always gets same result
    """
    hash_value = int(hashlib.md5(f"{flag_key}:{user_id}".encode()).hexdigest(), 16)
    bucket = (hash_value % 10000) / 100.0  # 0-100
    return bucket < percentage
```

**Recommended Schedule**:
```
1% → monitor 24h
5% → monitor 24h
10% → monitor 48h
25% → monitor 48h
50% → monitor 48h
100% → monitor 72h
```

**Acceleration Criteria**:
- Zero incidents
- Metrics better than baseline
- Positive user feedback
- No performance degradation

**Deceleration/Halt Criteria**:
- Any critical bugs
- Error rate increase
- Performance degradation
- Negative user feedback

### 4.5 Dark Launch

**Definition**: Deploy feature to production but don't expose to users

**When to Use**:
- Load testing
- Performance validation
- Shadow traffic testing
- Pre-warming caches

**Implementation**:
```python
# Execute both code paths, only return old path
old_result = legacy_implementation()

if feature_flags.is_enabled('dark-launch-new-impl'):
    # Execute but don't use result
    try:
        new_result = new_implementation()
        # Log comparison
        compare_results(old_result, new_result)
    except Exception as e:
        log_error(e)

return old_result
```

**Use Cases**:
- Shadow testing
- Performance baselining
- Data collection
- Algorithm comparison

---

## 5. Targeting and Segmentation

### 5.1 User-Based Targeting

**User Attributes**:
```json
{
  "user_id": "user-123",
  "email": "user@example.com",
  "name": "John Doe",
  "plan": "premium",
  "country": "US",
  "signup_date": "2024-01-15",
  "lifetime_value": 1250.50,
  "attributes": {
    "company": "Acme Corp",
    "role": "admin",
    "team_size": 50
  }
}
```

**Targeting Rules**:

**Exact Match**:
```json
{
  "attribute": "user_id",
  "operator": "equals",
  "values": ["user-123", "user-456"]
}
```

**List Membership**:
```json
{
  "attribute": "plan",
  "operator": "in",
  "values": ["premium", "enterprise"]
}
```

**Numeric Comparison**:
```json
{
  "attribute": "lifetime_value",
  "operator": "greater_than",
  "values": [1000]
}
```

**String Patterns**:
```json
{
  "attribute": "email",
  "operator": "ends_with",
  "values": ["@company.com"]
}
```

**Date Ranges**:
```json
{
  "attribute": "signup_date",
  "operator": "after",
  "values": ["2024-01-01"]
}
```

### 5.2 Segment-Based Targeting

**Segment Definition**:
```json
{
  "key": "power-users",
  "name": "Power Users",
  "conditions": [
    {
      "attribute": "sessions_per_month",
      "operator": "greater_than",
      "values": [50]
    },
    {
      "attribute": "feature_adoption_rate",
      "operator": "greater_than",
      "values": [0.7]
    }
  ]
}
```

**Using Segments**:
```python
if user in segments['power-users']:
    enable_advanced_features()
```

**Common Segments**:
- **Beta Users**: Opted into early access
- **Power Users**: High engagement
- **At-Risk Users**: Declining usage
- **New Users**: Recently signed up
- **VIP Customers**: High value
- **Internal Users**: Company employees

### 5.3 Context-Based Targeting

**Request Context**:
```json
{
  "request_id": "req-abc123",
  "ip_address": "203.0.113.42",
  "user_agent": "Mozilla/5.0...",
  "device_type": "mobile",
  "platform": "ios",
  "app_version": "2.1.0",
  "locale": "en-US",
  "timezone": "America/Los_Angeles"
}
```

**Targeting Rules**:

**Geographic**:
```json
{
  "attribute": "country",
  "operator": "in",
  "values": ["US", "CA", "GB"]
}
```

**Device Type**:
```json
{
  "attribute": "device_type",
  "operator": "equals",
  "values": ["mobile"]
}
```

**App Version**:
```json
{
  "attribute": "app_version",
  "operator": "semver_greater",
  "values": ["2.0.0"]
}
```

### 5.4 Time-Based Targeting

**Implementation**:
```python
def is_enabled_for_time(flag_key: str, schedule: dict) -> bool:
    now = datetime.now()
    current_time = now.time()
    current_day = now.strftime('%A').lower()

    # Check day of week
    if current_day not in schedule.get('days', []):
        return False

    # Check time range
    start_time = schedule.get('start_time')
    end_time = schedule.get('end_time')

    if start_time and current_time < start_time:
        return False
    if end_time and current_time > end_time:
        return False

    return True
```

**Use Cases**:
- Scheduled releases
- Weekend-only features
- Business hours limitations
- Maintenance windows
- Time-zone specific rollouts

### 5.5 Composite Targeting

**All Conditions (AND)**:
```json
{
  "all_of": [
    {"attribute": "plan", "operator": "equals", "values": ["premium"]},
    {"attribute": "country", "operator": "equals", "values": ["US"]},
    {"attribute": "device_type", "operator": "equals", "values": ["mobile"]}
  ]
}
```

**Any Condition (OR)**:
```json
{
  "any_of": [
    {"attribute": "plan", "operator": "in", "values": ["premium", "enterprise"]},
    {"attribute": "beta_opted_in", "operator": "equals", "values": [true]}
  ]
}
```

**None Of (NOT)**:
```json
{
  "none_of": [
    {"attribute": "email", "operator": "ends_with", "values": ["@competitor.com"]},
    {"attribute": "blocked", "operator": "equals", "values": [true]}
  ]
}
```

**Complex Rule**:
```json
{
  "all_of": [
    {
      "any_of": [
        {"attribute": "plan", "operator": "in", "values": ["premium", "enterprise"]},
        {"attribute": "lifetime_value", "operator": "greater_than", "values": [5000]}
      ]
    },
    {
      "none_of": [
        {"attribute": "churn_risk", "operator": "greater_than", "values": [0.7]},
        {"attribute": "support_tickets", "operator": "greater_than", "values": [10]}
      ]
    }
  ]
}
```

---

## 6. Rollout Strategies

### 6.1 Linear Rollout

**Pattern**: Increase percentage at constant rate

**Schedule**:
```
Day 0:  0%
Day 1:  10%
Day 2:  20%
Day 3:  30%
Day 4:  40%
Day 5:  50%
Day 6:  60%
Day 7:  70%
Day 8:  80%
Day 9:  90%
Day 10: 100%
```

**Pros**:
- Predictable
- Easy to understand
- Simple automation

**Cons**:
- May be too aggressive
- Doesn't account for risk

**Best For**: Low-risk features, internal tools

### 6.2 Exponential Rollout

**Pattern**: Double exposure each phase

**Schedule**:
```
Phase 1: 1%   (100 users)
Phase 2: 2%   (200 users)
Phase 3: 4%   (400 users)
Phase 4: 8%   (800 users)
Phase 5: 16%  (1.6K users)
Phase 6: 32%  (3.2K users)
Phase 7: 64%  (6.4K users)
Phase 8: 100% (10K users)
```

**Pros**:
- Conservative start
- Fast completion
- Good risk/speed balance

**Cons**:
- Large jumps at end
- May be too fast

**Best For**: Medium-risk features, standard releases

### 6.3 Logarithmic Rollout

**Pattern**: Large jumps early, small at end

**Schedule**:
```
Phase 1: 50%
Phase 2: 75%
Phase 3: 87.5%
Phase 4: 93.75%
Phase 5: 96.875%
Phase 6: 98.4375%
Phase 7: 100%
```

**Pros**:
- Quick to majority
- Cautious at end
- Good for stable features

**Cons**:
- Aggressive start
- May expose too many users early

**Best For**: Well-tested features, confident releases

### 6.4 Custom Staged Rollout

**Pattern**: Manual control at each stage

**Example**:
```
Week 1: Internal (50 users)
Week 2: Beta users (500 users)
Week 3: 1% (1K users)
Week 4: 5% (5K users)
Week 5: 10% (10K users)
Week 6: 25% (25K users)
Week 7: 50% (50K users)
Week 8: 100% (100K users)
```

**Pros**:
- Maximum control
- Can adjust based on feedback
- Risk-appropriate pacing

**Cons**:
- Manual work
- Slow
- Requires discipline

**Best For**: High-risk features, major changes

### 6.5 Automated Rollout

**Pattern**: System automatically advances based on metrics

**Implementation**:
```python
class AutoRollout:
    def __init__(self, flag_key, schedule, metrics):
        self.flag_key = flag_key
        self.schedule = schedule
        self.metrics = metrics

    def advance_if_safe(self):
        current = self.get_current_percentage()
        next_percentage = self.get_next_percentage()

        if self.is_safe_to_advance():
            self.set_percentage(next_percentage)
            log.info(f"Advanced {self.flag_key} to {next_percentage}%")
        else:
            log.warning(f"Holding {self.flag_key} at {current}%")

    def is_safe_to_advance(self):
        # Check metrics
        error_rate = self.metrics.get_error_rate(self.flag_key)
        latency_p95 = self.metrics.get_latency_p95(self.flag_key)

        # Safety checks
        if error_rate > self.threshold['error_rate']:
            return False
        if latency_p95 > self.threshold['latency']:
            return False

        # Check stability period
        if not self.stable_for_hours(24):
            return False

        return True
```

**Pros**:
- Hands-off
- Fast when safe
- Data-driven

**Cons**:
- Requires robust monitoring
- Complex to implement
- May miss edge cases

**Best For**: Mature organizations, high-volume services

---

## 7. A/B Testing and Experimentation

### 7.1 Experiment Design

**Hypothesis Template**:
```
We believe that [change] will cause [impact] for [audience].
We will know this is true when we see [metric] change by [amount].
```

**Example**:
```
We believe that changing the checkout button from blue to red
will increase conversion rate for mobile users.
We will know this is true when we see conversion rate increase by 5%.
```

**Components**:
1. **Hypothesis**: What you're testing
2. **Variations**: Control + treatments
3. **Audience**: Who sees the test
4. **Metrics**: What you measure
5. **Sample Size**: How many users
6. **Duration**: How long to run
7. **Success Criteria**: What constitutes a win

### 7.2 Sample Size Calculation

**Formula**:
```
n = 2 * (Z_α/2 + Z_β)² * σ² / δ²

Where:
n = required sample size per variation
Z_α/2 = z-score for significance level (1.96 for 95%)
Z_β = z-score for power (0.84 for 80%)
σ = standard deviation
δ = minimum detectable effect
```

**Python Implementation**:
```python
from scipy.stats import norm
import math

def calculate_sample_size(
    baseline_rate: float,
    minimum_detectable_effect: float,
    significance_level: float = 0.05,
    power: float = 0.80
) -> int:
    """
    Calculate required sample size for A/B test

    Args:
        baseline_rate: Current conversion rate (e.g., 0.10 for 10%)
        minimum_detectable_effect: Minimum effect to detect (e.g., 0.05 for 5% lift)
        significance_level: Alpha (typically 0.05)
        power: 1 - Beta (typically 0.80)

    Returns:
        Required sample size per variation
    """
    # Z-scores
    z_alpha = norm.ppf(1 - significance_level / 2)
    z_beta = norm.ppf(power)

    # Standard deviation
    p1 = baseline_rate
    p2 = baseline_rate * (1 + minimum_detectable_effect)
    pooled_std = math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))

    # Sample size
    n = 2 * ((z_alpha + z_beta) * pooled_std / (p2 - p1)) ** 2

    return math.ceil(n)

# Example
n = calculate_sample_size(
    baseline_rate=0.10,
    minimum_detectable_effect=0.10,  # 10% relative lift
    significance_level=0.05,
    power=0.80
)
print(f"Required sample size: {n:,} per variation")
# Output: Required sample size: 3,842 per variation
```

### 7.3 Statistical Significance

**Two-Sample Z-Test**:
```python
from scipy.stats import norm
import math

def calculate_significance(
    control_conversions: int,
    control_users: int,
    treatment_conversions: int,
    treatment_users: int
) -> dict:
    """
    Calculate statistical significance of A/B test

    Returns:
        dict with p-value, z-score, confidence intervals
    """
    # Conversion rates
    p_control = control_conversions / control_users
    p_treatment = treatment_conversions / treatment_users

    # Pooled proportion
    p_pool = (control_conversions + treatment_conversions) / \
             (control_users + treatment_users)

    # Standard error
    se = math.sqrt(p_pool * (1 - p_pool) * \
                   (1/control_users + 1/treatment_users))

    # Z-score
    z_score = (p_treatment - p_control) / se

    # P-value (two-tailed)
    p_value = 2 * (1 - norm.cdf(abs(z_score)))

    # Confidence intervals (95%)
    margin = 1.96 * se
    ci_lower = (p_treatment - p_control) - margin
    ci_upper = (p_treatment - p_control) + margin

    # Relative lift
    lift = (p_treatment - p_control) / p_control

    return {
        'control_rate': p_control,
        'treatment_rate': p_treatment,
        'absolute_difference': p_treatment - p_control,
        'relative_lift': lift,
        'z_score': z_score,
        'p_value': p_value,
        'significant_at_95': p_value < 0.05,
        'confidence_interval': (ci_lower, ci_upper)
    }

# Example
result = calculate_significance(
    control_conversions=380,
    control_users=4000,
    treatment_conversions=440,
    treatment_users=4000
)

print(f"Control: {result['control_rate']:.2%}")
print(f"Treatment: {result['treatment_rate']:.2%}")
print(f"Lift: {result['relative_lift']:.2%}")
print(f"P-value: {result['p_value']:.4f}")
print(f"Significant: {result['significant_at_95']}")
```

### 7.4 Multivariate Testing

**Setup**:
```json
{
  "experiment_key": "checkout-optimization",
  "variations": [
    {
      "key": "control",
      "button_color": "blue",
      "button_text": "Checkout",
      "layout": "vertical"
    },
    {
      "key": "variant-a",
      "button_color": "red",
      "button_text": "Checkout",
      "layout": "vertical"
    },
    {
      "key": "variant-b",
      "button_color": "blue",
      "button_text": "Buy Now",
      "layout": "vertical"
    },
    {
      "key": "variant-c",
      "button_color": "red",
      "button_text": "Buy Now",
      "layout": "horizontal"
    }
  ],
  "allocation": {
    "control": 25,
    "variant-a": 25,
    "variant-b": 25,
    "variant-c": 25
  }
}
```

**Sample Size Adjustment**:
```python
# With more variations, need larger sample size
# Apply Bonferroni correction

def multivariate_sample_size(
    baseline_sample_size: int,
    num_variations: int
) -> int:
    """
    Adjust sample size for multiple comparisons

    Args:
        baseline_sample_size: Sample size for 2-variation test
        num_variations: Total number of variations (including control)

    Returns:
        Adjusted sample size
    """
    # Conservative: multiply by number of comparisons
    comparisons = num_variations - 1
    return baseline_sample_size * comparisons

# Example: 4 variations needs 3x sample size
adjusted = multivariate_sample_size(4000, 4)
print(f"Adjusted sample size: {adjusted:,}")
# Output: 12,000
```

### 7.5 Sequential Testing

**Early Stopping**:
```python
def can_stop_early(
    control_conversions: int,
    control_users: int,
    treatment_conversions: int,
    treatment_users: int,
    alpha: float = 0.05,
    min_sample_size: int = 1000
) -> dict:
    """
    Check if experiment can be stopped early

    Uses sequential testing boundaries to control false positive rate

    Returns:
        dict with decision and rationale
    """
    # Don't stop before minimum sample size
    if control_users < min_sample_size or treatment_users < min_sample_size:
        return {
            'can_stop': False,
            'reason': 'Minimum sample size not reached'
        }

    # Calculate current result
    result = calculate_significance(
        control_conversions, control_users,
        treatment_conversions, treatment_users
    )

    # Stricter threshold for early stopping (to control Type I error)
    early_stop_alpha = alpha / 2

    if result['p_value'] < early_stop_alpha:
        return {
            'can_stop': True,
            'reason': 'Significant result with early stopping correction',
            'winner': 'treatment' if result['treatment_rate'] > result['control_rate'] else 'control'
        }

    # Check for futility (unlikely to reach significance)
    # If p-value > 0.5, very unlikely to become significant
    if result['p_value'] > 0.5 and control_users > min_sample_size * 2:
        return {
            'can_stop': True,
            'reason': 'Futility - unlikely to reach significance',
            'winner': None
        }

    return {
        'can_stop': False,
        'reason': 'Continue collecting data'
    }
```

---

## 8. Flag Lifecycle Management

### 8.1 Flag States

**Lifecycle States**:

1. **Draft**: Defined but not deployed
2. **Active**: Deployed, in use
3. **Deprecated**: Marked for removal
4. **Archived**: Removed from code, kept in config
5. **Deleted**: Completely removed

**State Transitions**:
```
Draft → Active → Deprecated → Archived → Deleted
  ↓                    ↑
  └────────────────────┘ (cancel)
```

### 8.2 Flag Metadata

**Required Fields**:
```json
{
  "key": "new-checkout-flow",
  "name": "New Checkout Flow",
  "description": "Simplified single-page checkout",
  "type": "release",
  "created_at": "2025-01-15T10:00:00Z",
  "created_by": "user-123",
  "owner": "checkout-team",
  "maintainers": ["user-123", "user-456"],
  "tags": ["checkout", "conversion", "frontend"],
  "temporary": true,
  "expiration_date": "2025-03-15",
  "jira_ticket": "PROJ-1234"
}
```

**Optional Fields**:
```json
{
  "documentation_url": "https://wiki.example.com/new-checkout",
  "rollout_plan_url": "https://docs.example.com/rollout-plan",
  "estimated_removal_date": "2025-04-01",
  "dependencies": ["feature-x", "feature-y"],
  "blocks": ["feature-z"],
  "risk_level": "medium",
  "blast_radius": "high"
}
```

### 8.3 Flag Naming Conventions

**Recommended Format**:
```
<category>-<feature>-<variant>

Examples:
- release-new-dashboard
- experiment-button-color
- ops-cache-ttl
- permission-premium-features
- killswitch-ml-recommendations
```

**Best Practices**:
- Lowercase with hyphens
- Descriptive and specific
- Include category/type
- Avoid generic names
- Keep under 50 characters
- No special characters except hyphen

**Anti-Patterns**:
```
❌ flag1, flag2, flag3  (non-descriptive)
❌ temp_flag  (unclear purpose)
❌ newFeature  (inconsistent casing)
❌ enable_the_new_super_cool_dashboard_redesign  (too long)
```

### 8.4 Flag Documentation

**Template**:
```markdown
# Feature Flag: new-checkout-flow

## Overview
Single-page checkout to improve conversion rate

## Details
- **Type**: Release toggle
- **Owner**: Checkout Team
- **Created**: 2025-01-15
- **Target Removal**: 2025-04-01

## Variations
- `control`: Current multi-step checkout
- `treatment`: New single-page checkout

## Rollout Plan
1. Week 1: Internal users (100%)
2. Week 2: Beta users (100%)
3. Week 3: 10% of all users
4. Week 4: 50% of all users
5. Week 5: 100% of all users

## Success Metrics
- Primary: Conversion rate (target: +5%)
- Secondary: Time to complete (target: -20%)

## Rollback Plan
1. Set flag to 0%
2. Monitor for 1 hour
3. Deploy hotfix if needed

## Code Locations
- `app/checkout/views.py:125`
- `app/checkout/templates/checkout.html:45`
- `tests/checkout/test_views.py:78`

## Dependencies
- Requires `payment-api-v2` flag enabled
- Blocks `express-checkout` flag

## Cleanup Checklist
- [ ] Remove flag checks from code
- [ ] Update tests
- [ ] Remove configuration
- [ ] Update documentation
- [ ] Notify stakeholders
```

### 8.5 Flag Retention Policy

**Retention Schedule**:

**Release Toggles**:
- Remove 30 days after 100% rollout
- Archive in config for 90 days
- Delete after 1 year

**Experiment Toggles**:
- Remove 14 days after conclusion
- Archive results indefinitely
- Delete flag config after 6 months

**Ops Toggles**:
- Keep indefinitely while in use
- Review annually
- Remove if unused for 6 months

**Permission Toggles**:
- Keep as long as permission exists
- Review quarterly
- Migrate to proper IAM when stable

**Kill Switches**:
- Keep indefinitely
- Test quarterly
- Document last test date

**Enforcement**:
```python
# Automated flag lifecycle management

def check_flag_retention():
    """Check flags against retention policy"""
    flags = get_all_flags()
    issues = []

    for flag in flags:
        age_days = (datetime.now() - flag['created_at']).days

        if flag['type'] == 'release' and age_days > 120:
            if flag['rollout_percentage'] == 100:
                issues.append({
                    'flag': flag['key'],
                    'issue': 'Release flag at 100% for 120+ days',
                    'action': 'Remove'
                })

        if flag['type'] == 'experiment' and flag.get('concluded'):
            days_since_conclusion = \
                (datetime.now() - flag['concluded_at']).days
            if days_since_conclusion > 14:
                issues.append({
                    'flag': flag['key'],
                    'issue': 'Experiment concluded 14+ days ago',
                    'action': 'Remove'
                })

    return issues
```

---

## 9. Technical Debt Prevention

### 9.1 Flag Debt Indicators

**Warning Signs**:
- Flag age > 180 days
- No usage in 90 days
- Single variation used >99% of time
- Owner left company
- No documentation
- Multiple dependent flags
- Complex conditional logic
- Forgotten in codebase

**Detection**:
```python
def detect_flag_debt(flag: Dict) -> List[str]:
    """Detect technical debt indicators"""
    issues = []

    # Check age
    age_days = (datetime.now() - flag['created_at']).days
    if age_days > 180:
        issues.append(f"Flag is {age_days} days old")

    # Check usage
    metrics = get_usage_metrics(flag['key'])
    if metrics['days_since_last_evaluation'] > 90:
        issues.append("Not evaluated in 90+ days")

    # Check variation distribution
    if metrics['variation_distribution']:
        max_pct = max(metrics['variation_distribution'].values())
        if max_pct > 99:
            issues.append("Single variation used >99% of time")

    # Check owner
    owner = flag.get('owner')
    if not owner or not user_exists(owner):
        issues.append("No valid owner")

    # Check documentation
    if not flag.get('documentation_url'):
        issues.append("No documentation")

    # Check dependencies
    if len(flag.get('dependencies', [])) > 3:
        issues.append(f"{len(flag['dependencies'])} dependencies")

    return issues
```

### 9.2 Automated Cleanup

**Cleanup Bot**:
```python
class FlagCleanupBot:
    """Automated flag cleanup system"""

    def __init__(self, flag_manager, notification_service):
        self.flag_manager = flag_manager
        self.notifications = notification_service

    def run_daily_checks(self):
        """Run daily cleanup checks"""
        flags = self.flag_manager.get_all_flags()

        for flag in flags:
            # Check if flag can be cleaned up
            if self.should_remove(flag):
                self.schedule_removal(flag)
            elif self.should_warn(flag):
                self.send_warning(flag)

    def should_remove(self, flag: Dict) -> bool:
        """Check if flag should be removed"""
        # Release flags at 100% for 30+ days
        if flag['type'] == 'release':
            if flag['rollout_percentage'] == 100:
                days_at_100 = self.days_at_percentage(flag, 100)
                return days_at_100 > 30

        # Experiment flags 14+ days after conclusion
        if flag['type'] == 'experiment':
            if flag.get('concluded'):
                days_since = (datetime.now() - flag['concluded_at']).days
                return days_since > 14

        # Flags not evaluated in 90+ days
        metrics = get_usage_metrics(flag['key'])
        if metrics['days_since_last_evaluation'] > 90:
            return True

        return False

    def should_warn(self, flag: Dict) -> bool:
        """Check if owner should be warned"""
        age_days = (datetime.now() - flag['created_at']).days

        # Warn at 90, 120, 150 days
        if age_days in [90, 120, 150]:
            return True

        return False

    def schedule_removal(self, flag: Dict):
        """Schedule flag for removal"""
        # Create removal ticket
        ticket = self.create_removal_ticket(flag)

        # Notify owner
        self.notifications.send(
            to=flag['owner'],
            subject=f"Flag {flag['key']} scheduled for removal",
            body=f"Flag meets removal criteria. Ticket: {ticket}"
        )

        # Mark flag as deprecated
        self.flag_manager.update_flag(
            flag['key'],
            deprecated=True,
            deprecation_reason="Automated cleanup"
        )

    def send_warning(self, flag: Dict):
        """Send warning to owner"""
        age_days = (datetime.now() - flag['created_at']).days
        self.notifications.send(
            to=flag['owner'],
            subject=f"Flag {flag['key']} is {age_days} days old",
            body=f"Please review if this flag can be removed."
        )
```

### 9.3 Flag Metrics Dashboard

**Key Metrics**:
```python
def calculate_flag_health_metrics() -> Dict:
    """Calculate organizational flag health metrics"""
    flags = get_all_flags()

    metrics = {
        'total_flags': len(flags),
        'flags_by_type': {},
        'flags_by_age': {
            '<30_days': 0,
            '30-90_days': 0,
            '90-180_days': 0,
            '>180_days': 0
        },
        'stale_flags': 0,
        'deprecated_flags': 0,
        'flags_without_owner': 0,
        'flags_without_docs': 0,
        'average_age_days': 0,
        'oldest_flag_days': 0
    }

    ages = []
    for flag in flags:
        # Type distribution
        flag_type = flag['type']
        metrics['flags_by_type'][flag_type] = \
            metrics['flags_by_type'].get(flag_type, 0) + 1

        # Age distribution
        age_days = (datetime.now() - flag['created_at']).days
        ages.append(age_days)

        if age_days < 30:
            metrics['flags_by_age']['<30_days'] += 1
        elif age_days < 90:
            metrics['flags_by_age']['30-90_days'] += 1
        elif age_days < 180:
            metrics['flags_by_age']['90-180_days'] += 1
        else:
            metrics['flags_by_age']['>180_days'] += 1

        # Stale flags
        usage = get_usage_metrics(flag['key'])
        if usage['days_since_last_evaluation'] > 90:
            metrics['stale_flags'] += 1

        # Deprecated flags
        if flag.get('deprecated'):
            metrics['deprecated_flags'] += 1

        # Missing owner
        if not flag.get('owner'):
            metrics['flags_without_owner'] += 1

        # Missing docs
        if not flag.get('documentation_url'):
            metrics['flags_without_docs'] += 1

    metrics['average_age_days'] = sum(ages) / len(ages) if ages else 0
    metrics['oldest_flag_days'] = max(ages) if ages else 0

    return metrics
```

---

*[Continued in next section due to length...]*

## 10. Client-Side vs Server-Side

### 10.1 Server-Side Evaluation

**Definition**: Flags evaluated on server before responding to client

**Architecture**:
```
Client Request → Server → Flag SDK → Evaluation → Response
```

**Advantages**:
- **Security**: Flag logic hidden from users
- **Performance**: No client overhead
- **Consistency**: Single source of truth
- **Control**: Instant updates
- **Privacy**: User data stays on server

**Disadvantages**:
- **Latency**: Adds server processing time
- **Server Load**: Evaluation on every request
- **Cost**: More server resources needed

**Use Cases**:
- Backend feature toggles
- Security-sensitive flags
- Database queries
- API rate limiting
- Payment processing

**Implementation**:
```python
from flask import Flask, request, jsonify

app = Flask(__name__)
flag_client = LaunchDarklyClient(sdk_key="...")

@app.route('/api/checkout')
def checkout():
    user = get_current_user()

    # Server-side evaluation
    use_new_flow = flag_client.is_enabled(
        'new-checkout-flow',
        user,
        default=False
    )

    if use_new_flow:
        return process_new_checkout()
    else:
        return process_legacy_checkout()
```

### 10.2 Client-Side Evaluation

**Definition**: Flags evaluated in browser/mobile app

**Architecture**:
```
Client → Flag SDK (Local) → Evaluation → Render
```

**Advantages**:
- **Performance**: No server round-trip
- **Offline**: Works without connectivity
- **Cost**: Reduces server load
- **UX**: Instant response

**Disadvantages**:
- **Security**: Flag logic visible
- **Stale Data**: May not have latest values
- **Size**: SDK adds to bundle
- **Complexity**: More client logic

**Use Cases**:
- UI variations
- Frontend experiments
- Visual changes
- Performance optimizations
- Mobile features

**Implementation**:
```javascript
import { LDClient } from 'launchdarkly-js-client-sdk';

const client = LDClient.initialize('client-side-id', {
  key: 'user-123',
  email: 'user@example.com'
});

client.on('ready', () => {
  // Client-side evaluation
  const showNewUI = client.variation('new-ui', false);

  if (showNewUI) {
    renderNewUI();
  } else {
    renderLegacyUI();
  }
});
```

### 10.3 Hybrid Approach

**Best of Both Worlds**:

**Server-Side For**:
- Business logic
- Payment processing
- Data access
- Security checks
- Rate limiting

**Client-Side For**:
- UI rendering
- Animations
- Layout changes
- Theme switching
- Progressive enhancement

**Implementation**:
```javascript
// 1. Server renders initial state
<script>
  window.FLAGS = {
    newUI: true,
    darkMode: false
  };
</script>

// 2. Client hydrates and takes over
const client = FlagClient.initialize();

// Use server flags immediately
if (window.FLAGS.newUI) {
  renderNewUI();
}

// Update with client-side SDK
client.on('ready', () => {
  const flags = client.allFlags();
  updateFlags(flags);
});
```

### 10.4 Edge Evaluation

**Definition**: Evaluate flags at CDN edge

**Architecture**:
```
Client → CDN/Edge → Flag Evaluation → Origin (if needed)
```

**Advantages**:
- **Low Latency**: Evaluated close to user
- **Scale**: Edge handles load
- **Performance**: Cached at edge
- **Global**: Works worldwide

**Implementation (Cloudflare Workers)**:
```javascript
addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

async function handleRequest(request) {
  const userId = request.headers.get('X-User-ID');

  // Evaluate flag at edge
  const useNewAPI = evaluateFlag('new-api', userId);

  const apiUrl = useNewAPI ?
    'https://api-v2.example.com' :
    'https://api-v1.example.com';

  return fetch(apiUrl, request);
}

function evaluateFlag(flagKey, userId) {
  // Simple percentage-based evaluation
  const hash = simpleHash(`${flagKey}:${userId}`);
  const bucket = hash % 100;
  return bucket < 25; // 25% rollout
}
```

---

## 11. Performance Considerations

### 11.1 Caching Strategies

**In-Memory Cache**:
```python
from functools import lru_cache
import time

class CachedFlagClient:
    def __init__(self, client, ttl_seconds=60):
        self.client = client
        self.ttl = ttl_seconds
        self.cache = {}

    def is_enabled(self, flag_key, user):
        cache_key = f"{flag_key}:{user['id']}"

        # Check cache
        if cache_key in self.cache:
            value, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.ttl:
                return value

        # Evaluate and cache
        value = self.client.is_enabled(flag_key, user)
        self.cache[cache_key] = (value, time.time())

        return value
```

**Redis Cache**:
```python
import redis
import json

class RedisCachedFlagClient:
    def __init__(self, client, redis_client, ttl_seconds=60):
        self.client = client
        self.redis = redis_client
        self.ttl = ttl_seconds

    def is_enabled(self, flag_key, user):
        cache_key = f"flag:{flag_key}:{user['id']}"

        # Check Redis
        cached = self.redis.get(cache_key)
        if cached:
            return json.loads(cached)

        # Evaluate and cache
        value = self.client.is_enabled(flag_key, user)
        self.redis.setex(cache_key, self.ttl, json.dumps(value))

        return value
```

**CDN Caching**:
```javascript
// Cache flag values at CDN edge
async function getCachedFlags(userId) {
  const cacheKey = `flags:${userId}`;
  const cached = await EDGE_CACHE.get(cacheKey);

  if (cached) {
    return JSON.parse(cached);
  }

  // Fetch from origin
  const flags = await fetchFlags(userId);

  // Cache for 60 seconds
  await EDGE_CACHE.put(cacheKey, JSON.stringify(flags), {
    expirationTtl: 60
  });

  return flags;
}
```

### 11.2 Batch Evaluation

**Problem**: Evaluating flags one-by-one is expensive

**Solution**: Evaluate multiple flags in single call

```python
def get_all_flags_for_user(user):
    """
    Evaluate all flags for user in single operation

    More efficient than individual calls
    """
    return flag_client.all_flags(user)

# Usage
flags = get_all_flags_for_user(current_user)

if flags['new-ui']:
    render_new_ui()

if flags['beta-features']:
    enable_beta_features()
```

### 11.3 Async Evaluation

**Non-Blocking Evaluation**:
```python
import asyncio

async def evaluate_flags_async(flag_keys, user):
    """Evaluate multiple flags concurrently"""
    tasks = [
        flag_client.is_enabled_async(key, user)
        for key in flag_keys
    ]

    results = await asyncio.gather(*tasks)

    return dict(zip(flag_keys, results))

# Usage
flags = await evaluate_flags_async(
    ['feature-a', 'feature-b', 'feature-c'],
    current_user
)
```

### 11.4 Streaming Updates

**WebSocket/SSE for Real-Time Updates**:
```javascript
// Client subscribes to flag changes
const flagStream = new EventSource('/flags/stream');

flagStream.addEventListener('flag-update', (event) => {
  const { flagKey, newValue } = JSON.parse(event.data);

  // Update local cache
  flagCache.set(flagKey, newValue);

  // Trigger re-render if needed
  if (flagKey === 'ui-theme') {
    updateTheme(newValue);
  }
});
```

**Server Implementation**:
```python
from flask import Flask, Response
import json
import time

@app.route('/flags/stream')
def flag_stream():
    def generate():
        while True:
            # Check for flag updates
            updates = get_flag_updates()

            for update in updates:
                yield f"data: {json.dumps(update)}\n\n"

            time.sleep(1)  # Poll every second

    return Response(generate(), mimetype='text/event-stream')
```

### 11.5 Lazy Loading

**Load Flags on Demand**:
```python
class LazyFlagClient:
    """Load flags only when needed"""

    def __init__(self, client):
        self.client = client
        self.loaded_flags = set()

    def is_enabled(self, flag_key, user):
        # Load flag configuration if not already loaded
        if flag_key not in self.loaded_flags:
            self.client.load_flag(flag_key)
            self.loaded_flags.add(flag_key)

        return self.client.is_enabled(flag_key, user)
```

### 11.6 Performance Benchmarks

**Target Latencies**:
- **Server-Side Evaluation**: < 10ms
- **Client-Side Evaluation**: < 1ms
- **Cache Hit**: < 1ms
- **Cache Miss + Evaluation**: < 50ms
- **Flag Update Propagation**: < 5s

**Measurement**:
```python
import time

def benchmark_flag_evaluation(iterations=10000):
    """Benchmark flag evaluation performance"""
    start = time.time()

    for i in range(iterations):
        user = {'id': f'user-{i}'}
        flag_client.is_enabled('test-flag', user)

    duration = time.time() - start
    avg_ms = (duration / iterations) * 1000

    print(f"Evaluated {iterations} flags in {duration:.2f}s")
    print(f"Average: {avg_ms:.3f}ms per evaluation")

    return avg_ms
```

---

*[To be continued with remaining sections...]*

Due to length constraints, I'll create the first part of REFERENCE.md now and continue in subsequent writes. Let me create a marker indicating this is part 1 and will continue.

## 12. Security and Compliance

### 12.1 Security Considerations

**Flag Value Security**:
- Never expose sensitive data in flag values
- Use indirection (IDs, not secrets)
- Encrypt sensitive configurations
- Audit access to flag management

**Access Control**:
```yaml
# Example RBAC for flags
roles:
  - name: flag-admin
    permissions:
      - create-flags
      - update-flags
      - delete-flags
      - view-flags

  - name: flag-operator
    permissions:
      - update-rollout-percentage
      - toggle-flags
      - view-flags

  - name: flag-viewer
    permissions:
      - view-flags
```

**API Key Security**:
```python
# Never hardcode API keys
import os

SDK_KEY = os.getenv('LAUNCHDARKLY_SDK_KEY')
if not SDK_KEY:
    raise ValueError("SDK_KEY not configured")

# Use different keys per environment
KEYS = {
    'development': os.getenv('LD_DEV_KEY'),
    'staging': os.getenv('LD_STAGING_KEY'),
    'production': os.getenv('LD_PROD_KEY')
}
```

### 12.2 Compliance Requirements

**Audit Logging**:
```python
def log_flag_change(flag_key, old_value, new_value, user_id):
    """Log all flag changes for audit trail"""
    audit_log.write({
        'timestamp': datetime.now().isoformat(),
        'flag_key': flag_key,
        'old_value': old_value,
        'new_value': new_value,
        'changed_by': user_id,
        'ip_address': get_client_ip(),
        'user_agent': get_user_agent()
    })
```

**Data Residency**:
- Use region-specific flag providers
- Keep user data in appropriate regions
- Comply with GDPR, CCPA, etc.

**PII Handling**:
- Don't log PII in flag evaluations
- Hash user IDs when possible
- Implement data retention policies

### 12.3 Security Best Practices

1. **Least Privilege**: Minimal flag access per role
2. **Separation of Duties**: Require approvals for changes
3. **Regular Audits**: Review flag access quarterly
4. **Secret Rotation**: Rotate API keys regularly
5. **Secure Transmission**: HTTPS for all flag APIs
6. **Input Validation**: Validate flag values
7. **Rate Limiting**: Prevent abuse
8. **Monitoring**: Alert on suspicious activity

---

## 13. Testing Strategies

### 13.1 Unit Testing

**Testing with Mocked Flags**:
```python
import pytest
from unittest.mock import Mock

def test_new_feature_enabled():
    """Test behavior when feature is enabled"""
    flag_client = Mock()
    flag_client.is_enabled.return_value = True

    result = process_with_feature(flag_client, 'new-feature')

    assert result == expected_new_behavior
    flag_client.is_enabled.assert_called_once_with('new-feature')

def test_new_feature_disabled():
    """Test behavior when feature is disabled"""
    flag_client = Mock()
    flag_client.is_enabled.return_value = False

    result = process_with_feature(flag_client, 'new-feature')

    assert result == expected_legacy_behavior
```

**Testing All Variations**:
```python
@pytest.mark.parametrize('flag_value,expected', [
    (True, 'new_behavior'),
    (False, 'legacy_behavior')
])
def test_feature_variations(flag_value, expected):
    """Test all flag variations"""
    flag_client = Mock()
    flag_client.is_enabled.return_value = flag_value

    result = process_with_feature(flag_client, 'feature')

    assert result == expected
```

### 13.2 Integration Testing

**Testing with Real Flag Provider**:
```python
def test_flag_integration():
    """Test integration with flag provider"""
    client = LaunchDarklyClient(sdk_key=TEST_SDK_KEY)

    # Create test flag
    test_flag = create_test_flag('test-integration-flag')

    try:
        # Test enabled state
        test_flag.set_enabled(True)
        assert client.is_enabled('test-integration-flag', test_user)

        # Test disabled state
        test_flag.set_enabled(False)
        assert not client.is_enabled('test-integration-flag', test_user)

    finally:
        # Cleanup
        delete_test_flag('test-integration-flag')
```

### 13.3 End-to-End Testing

**Testing Full User Flow**:
```python
def test_checkout_flow_with_feature():
    """E2E test of checkout with new feature"""
    # Setup test user with flag enabled
    user = create_test_user()
    enable_flag_for_user('new-checkout', user.id)

    # Simulate user journey
    browser = Browser()
    browser.login(user)
    browser.add_to_cart(test_product)
    browser.go_to_checkout()

    # Verify new checkout flow is shown
    assert browser.page_contains('Single-Page Checkout')
    assert not browser.page_contains('Step 1 of 3')

    # Complete checkout
    browser.fill_payment_details()
    browser.click('Complete Purchase')

    # Verify success
    assert browser.page_contains('Order Confirmed')
```

### 13.4 Load Testing

**Testing Flag Performance**:
```python
from locust import HttpUser, task, between

class FlagLoadTest(HttpUser):
    wait_time = between(0.1, 0.5)

    @task
    def check_feature_flag(self):
        """Load test flag evaluation endpoint"""
        self.client.get('/api/features/new-checkout', headers={
            'X-User-ID': f'user-{self.user_id}'
        })

    def on_start(self):
        """Initialize user"""
        self.user_id = generate_random_user_id()
```

**Run Load Test**:
```bash
locust -f flag_load_test.py --host=https://api.example.com
```

### 13.5 Shadow Testing

**Compare New vs Old Implementation**:
```python
def shadow_test_implementation():
    """Run both implementations and compare"""
    # Get both results
    old_result = legacy_implementation()
    new_result = new_implementation()

    # Compare results
    if old_result != new_result:
        log_mismatch({
            'old': old_result,
            'new': new_result,
            'context': get_request_context()
        })

    # Always return old result (safe)
    return old_result
```

---

## 14. Monitoring and Observability

### 14.1 Key Metrics

**Flag Evaluation Metrics**:
- Total evaluations per second
- Evaluation latency (p50, p95, p99)
- Cache hit rate
- Error rate
- Variation distribution

**Flag Health Metrics**:
- Number of active flags
- Flag age distribution
- Stale flags count
- Flags without owners
- Deprecated flags

**Business Metrics**:
- Feature adoption rate
- User engagement by variation
- Conversion rate by variation
- Revenue impact

### 14.2 Logging

**Structured Logging**:
```python
import logging
import json

logger = logging.getLogger(__name__)

def log_flag_evaluation(flag_key, user_id, result, duration_ms):
    """Log flag evaluation with structured data"""
    logger.info('flag_evaluation', extra={
        'flag_key': flag_key,
        'user_id': hash_user_id(user_id),  # Hash for privacy
        'result': result,
        'duration_ms': duration_ms,
        'timestamp': datetime.now().isoformat()
    })
```

**Log Aggregation**:
```json
{
  "timestamp": "2025-10-27T10:15:30Z",
  "level": "INFO",
  "event": "flag_evaluation",
  "flag_key": "new-checkout",
  "user_id_hash": "a1b2c3d4",
  "result": true,
  "duration_ms": 2.3,
  "cache_hit": true
}
```

### 14.3 Alerting

**Alert Rules**:
```yaml
alerts:
  - name: HighFlagEvaluationLatency
    condition: p95(flag_evaluation_duration_ms) > 100
    for: 5m
    severity: warning
    message: "Flag evaluation latency is high"

  - name: HighFlagErrorRate
    condition: rate(flag_evaluation_errors) > 0.01
    for: 2m
    severity: critical
    message: "High rate of flag evaluation errors"

  - name: FlagCacheMissRate
    condition: cache_miss_rate > 0.5
    for: 10m
    severity: warning
    message: "High cache miss rate for flags"

  - name: StaleFlags
    condition: stale_flags_count > 10
    for: 24h
    severity: info
    message: "Multiple stale flags need cleanup"
```

### 14.4 Dashboards

**Grafana Dashboard Panels**:

1. **Flag Evaluations Rate**
```promql
rate(feature_flags_evaluations_total[5m])
```

2. **Evaluation Latency**
```promql
histogram_quantile(0.95,
  rate(feature_flags_evaluation_duration_seconds_bucket[5m])
)
```

3. **Top Evaluated Flags**
```promql
topk(10, sum by (flag_key) (
  rate(feature_flags_evaluations_total[5m])
))
```

4. **Variation Distribution**
```promql
sum by (flag_key, variation) (
  rate(feature_flags_evaluations_total[5m])
)
```

5. **Cache Performance**
```promql
rate(feature_flags_cache_hits_total[5m])
/
(rate(feature_flags_cache_hits_total[5m]) +
 rate(feature_flags_cache_misses_total[5m]))
```

### 14.5 Distributed Tracing

**OpenTelemetry Integration**:
```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

def evaluate_flag_with_tracing(flag_key, user):
    """Evaluate flag with distributed tracing"""
    with tracer.start_as_current_span("evaluate_flag") as span:
        span.set_attribute("flag.key", flag_key)
        span.set_attribute("user.id", hash_user_id(user['id']))

        result = flag_client.is_enabled(flag_key, user)

        span.set_attribute("flag.result", result)
        span.set_attribute("flag.cached", was_cached())

        return result
```

---

## 15. Architecture Patterns

### 15.1 Centralized Flag Service

**Architecture**:
```
┌──────────┐      ┌──────────────────┐      ┌────────────┐
│  App 1   │─────▶│                  │─────▶│            │
├──────────┤      │  Flag Service    │      │ Flag Store │
│  App 2   │─────▶│  (API Gateway)   │─────▶│ (Database) │
├──────────┤      │                  │      │            │
│  App 3   │─────▶│                  │      │            │
└──────────┘      └──────────────────┘      └────────────┘
```

**Advantages**:
- Single source of truth
- Consistent behavior
- Easy to manage
- Centralized auditing

**Disadvantages**:
- Single point of failure
- Latency for all requests
- Scaling challenges

**Implementation**:
```python
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/v1/flags/<flag_key>')
def get_flag(flag_key):
    """Centralized flag evaluation endpoint"""
    user_id = request.headers.get('X-User-ID')
    user = get_user_context(user_id)

    result = flag_manager.is_enabled(flag_key, user)

    return jsonify({
        'flag_key': flag_key,
        'enabled': result,
        'evaluated_at': datetime.now().isoformat()
    })
```

### 15.2 Sidecar Pattern

**Architecture**:
```
┌─────────────────────┐
│   Application Pod   │
│  ┌──────────────┐   │
│  │     App      │   │
│  └──────┬───────┘   │
│         │ localhost │
│  ┌──────▼───────┐   │
│  │ Flag Sidecar │   │
│  └──────┬───────┘   │
└─────────┼───────────┘
          │
    ┌─────▼─────┐
    │ Flag API  │
    └───────────┘
```

**Advantages**:
- Low latency (localhost)
- Fault isolation
- Independent scaling
- Language agnostic

**Kubernetes Sidecar**:
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-with-flags
spec:
  containers:
  - name: app
    image: myapp:latest
    env:
    - name: FLAG_SERVICE_URL
      value: "http://localhost:8000"

  - name: flag-sidecar
    image: flag-proxy:latest
    ports:
    - containerPort: 8000
    env:
    - name: FLAG_API_KEY
      valueFrom:
        secretKeyRef:
          name: flag-secrets
          key: api-key
```

### 15.3 Event-Driven Pattern

**Architecture**:
```
┌────────────┐      ┌──────────────┐      ┌───────────┐
│ Flag Admin │─────▶│ Event Stream │─────▶│  Service  │
│   Update   │      │  (Kafka)     │      │  Updates  │
└────────────┘      └──────────────┘      └───────────┘
                           │
                    ┌──────▼──────┐
                    │ All Services│
                    │   Subscribe │
                    └─────────────┘
```

**Advantages**:
- Real-time updates
- Decoupled services
- Scalable
- Event replay possible

**Kafka Implementation**:
```python
from kafka import KafkaConsumer
import json

consumer = KafkaConsumer(
    'flag-updates',
    bootstrap_servers=['kafka:9092'],
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)

for message in consumer:
    event = message.value

    if event['type'] == 'flag_updated':
        flag_key = event['flag_key']
        new_value = event['new_value']

        # Update local cache
        flag_cache.set(flag_key, new_value)

        logger.info(f"Updated flag {flag_key} to {new_value}")
```

### 15.4 Gateway Pattern

**Architecture**:
```
                   ┌──────────────┐
Client ───────────▶│   API GW     │
                   │ (Flag Logic) │
                   └──────┬───────┘
                          │
              ┌───────────┼───────────┐
              │           │           │
         ┌────▼───┐  ┌───▼────┐ ┌───▼────┐
         │Service1│  │Service2│ │Service3│
         └────────┘  └────────┘ └────────┘
```

**API Gateway with Flags**:
```javascript
// Kong/Nginx/Envoy plugin
function evaluateFlag(flagKey, user) {
  const enabled = flagService.isEnabled(flagKey, user);

  if (!enabled) {
    // Reject request or route to different backend
    return {
      statusCode: 403,
      body: 'Feature not available'
    };
  }

  // Continue to backend
  return proxy(request);
}
```

---

## 16. Integration Patterns

### 16.1 CI/CD Integration

**GitHub Actions**:
```yaml
name: Deploy with Flag Check

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Check flag status
        run: |
          FLAG_STATUS=$(curl -H "Authorization: Bearer ${{ secrets.LD_API_KEY }}" \
            https://app.launchdarkly.com/api/v2/flags/default/my-flag)

          if [ "$(echo $FLAG_STATUS | jq -r '.environments.production.on')" == "true" ]; then
            echo "Flag is enabled, proceeding with deployment"
          else
            echo "Flag is disabled, skipping deployment"
            exit 1
          fi

      - name: Deploy
        run: ./deploy.sh
```

**Automated Flag Creation**:
```yaml
- name: Create feature flag
  run: |
    curl -X POST https://app.launchdarkly.com/api/v2/flags/default \
      -H "Authorization: Bearer ${{ secrets.LD_API_KEY }}" \
      -H "Content-Type: application/json" \
      -d '{
        "key": "feature-${{ github.sha }}",
        "name": "Feature from ${{ github.ref }}",
        "tags": ["automated", "ci"]
      }'
```

### 16.2 Analytics Integration

**Segment Integration**:
```python
import analytics

def track_flag_exposure(user_id, flag_key, variation):
    """Track flag exposure in analytics"""
    analytics.track(
        user_id=user_id,
        event='Feature Flag Evaluated',
        properties={
            'flag_key': flag_key,
            'variation': variation,
            'timestamp': datetime.now().isoformat()
        }
    )

# Usage
variation = flag_client.get_variation('new-feature', user)
track_flag_exposure(user['id'], 'new-feature', variation)
```

**Amplitude Integration**:
```javascript
const amplitude = require('amplitude-js');

function trackFlagEvaluation(userId, flagKey, variation) {
  amplitude.getInstance().logEvent('Flag Evaluated', {
    flag_key: flagKey,
    variation: variation,
    user_id: userId
  });
}
```

### 16.3 APM Integration

**Datadog Integration**:
```python
from datadog import statsd

def track_flag_metrics(flag_key, duration_ms, result):
    """Send flag metrics to Datadog"""
    statsd.histogram(
        'flag.evaluation.duration',
        duration_ms,
        tags=[f'flag:{flag_key}', f'result:{result}']
    )

    statsd.increment(
        'flag.evaluation.count',
        tags=[f'flag:{flag_key}', f'result:{result}']
    )
```

**New Relic Integration**:
```python
import newrelic.agent

@newrelic.agent.background_task()
def evaluate_flag_with_tracking(flag_key, user):
    """Evaluate flag with New Relic tracking"""
    with newrelic.agent.FunctionTrace(
        name=f'FlagEvaluation/{flag_key}'
    ):
        result = flag_client.is_enabled(flag_key, user)

        newrelic.agent.add_custom_parameter('flag_key', flag_key)
        newrelic.agent.add_custom_parameter('flag_result', result)

        return result
```

---

## 17. Troubleshooting

### 17.1 Common Issues

**Issue: Flags not updating**

**Symptoms**:
- Users seeing old behavior
- Flag changes not taking effect
- Inconsistent behavior across instances

**Diagnosis**:
```bash
# Check flag value in provider
curl -H "Authorization: Bearer $API_KEY" \
  https://app.launchdarkly.com/api/v2/flags/default/my-flag

# Check local cache
redis-cli GET "flag:my-flag:user-123"

# Check SDK version
python -c "import ldclient; print(ldclient.version())"
```

**Solutions**:
1. Clear cache
2. Verify SDK connection
3. Check network/firewall
4. Update SDK version
5. Verify API credentials

**Issue: High latency**

**Symptoms**:
- Slow page loads
- API timeouts
- Poor user experience

**Diagnosis**:
```python
# Add timing to flag evaluations
import time

start = time.time()
result = flag_client.is_enabled('my-flag', user)
duration = (time.time() - start) * 1000

if duration > 100:
    logger.warning(f"Slow flag evaluation: {duration}ms")
```

**Solutions**:
1. Enable caching
2. Use client-side evaluation
3. Batch flag evaluations
4. Reduce targeting complexity
5. Move to edge evaluation

**Issue: Inconsistent results**

**Symptoms**:
- Same user seeing different variations
- A/B test results unreliable
- User complaints

**Diagnosis**:
```python
# Check bucketing consistency
user_id = "user-123"
results = []

for i in range(100):
    result = flag_client.is_enabled('my-flag', user_id)
    results.append(result)

# Should always be same result
assert len(set(results)) == 1, "Inconsistent bucketing!"
```

**Solutions**:
1. Verify consistent hashing
2. Check user ID stability
3. Review targeting rules
4. Clear inconsistent cache
5. Fix clock skew issues

### 17.2 Debug Mode

**Enable Debug Logging**:
```python
import logging

# Enable debug logging for flag SDK
logging.getLogger('ldclient').setLevel(logging.DEBUG)

# Evaluate flag with debug output
result = flag_client.is_enabled('my-flag', user)
# Output will show evaluation details
```

**Debug Inspector**:
```python
class DebugFlagClient:
    """Wrapper that logs all flag evaluations"""

    def __init__(self, client):
        self.client = client

    def is_enabled(self, flag_key, user):
        logger.debug(f"Evaluating {flag_key} for user {user['id']}")

        result = self.client.is_enabled(flag_key, user)

        logger.debug(f"Result: {result}")
        logger.debug(f"User attributes: {user}")

        return result
```

### 17.3 Health Checks

**Flag Service Health**:
```python
from flask import Flask, jsonify

@app.route('/health')
def health_check():
    """Health check endpoint"""
    checks = {
        'flag_sdk': check_flag_sdk(),
        'cache': check_cache(),
        'database': check_database()
    }

    healthy = all(checks.values())

    return jsonify({
        'status': 'healthy' if healthy else 'unhealthy',
        'checks': checks
    }), 200 if healthy else 503

def check_flag_sdk():
    """Verify flag SDK is working"""
    try:
        # Try evaluating a test flag
        result = flag_client.is_enabled('health-check', {
            'id': 'health-check-user'
        })
        return True
    except Exception as e:
        logger.error(f"Flag SDK check failed: {e}")
        return False
```

---

## 18. Best Practices

### 18.1 Naming and Organization

✅ **DO**:
- Use descriptive names
- Include type prefix
- Use consistent casing
- Keep names short but clear
- Document purpose

❌ **DON'T**:
- Use generic names (flag1, temp)
- Mix naming conventions
- Create overly long names
- Use abbreviations

### 18.2 Lifecycle Management

✅ **DO**:
- Set expiration dates
- Track flag age
- Remove after rollout
- Document retirement plans
- Regular cleanup

❌ **DON'T**:
- Leave flags indefinitely
- Skip removal planning
- Ignore old flags
- Forget to cleanup

### 18.3 Testing

✅ **DO**:
- Test all variations
- Mock flags in tests
- Test flag removal
- Include E2E tests
- Test rollback scenarios

❌ **DON'T**:
- Only test one variation
- Rely on production flags in tests
- Skip variation testing
- Forget edge cases

### 18.4 Monitoring

✅ **DO**:
- Monitor evaluation metrics
- Track flag health
- Alert on anomalies
- Dashboard key metrics
- Log important events

❌ **DON'T**:
- Ignore metrics
- Skip monitoring
- Over-alert
- Log sensitive data

### 18.5 Security

✅ **DO**:
- Rotate API keys
- Use RBAC
- Audit flag changes
- Encrypt sensitive data
- Follow least privilege

❌ **DON'T**:
- Hardcode credentials
- Grant excessive access
- Skip auditing
- Expose flag logic publicly

---

## 19. Anti-Patterns

### 19.1 Flag Sprawl

**Problem**: Too many flags, impossible to manage

**Symptoms**:
- 100+ active flags
- No one knows what flags do
- Fear of removing any flag
- Performance issues

**Solution**:
- Aggressive cleanup
- Retention policies
- Automated alerts
- Regular reviews

### 19.2 Nested Flags

**Problem**: Flags that depend on other flags

**Example**:
```python
# BAD: Complex nested logic
if flag_a:
    if flag_b:
        if flag_c:
            new_feature()
```

**Solution**:
- Combine into single flag
- Use multivariate flags
- Simplify logic

### 19.3 Flag Abuse

**Problem**: Using flags for configuration

**Example**:
```python
# BAD: Using flags as config
api_timeout = flag_client.get_variation('api-timeout', user)
cache_ttl = flag_client.get_variation('cache-ttl', user)
```

**Solution**:
- Use proper configuration system
- Reserve flags for feature control
- Separate concerns

### 19.4 Missing Default Values

**Problem**: No safe fallback when flag fails

**Example**:
```python
# BAD: No default
enabled = flag_client.is_enabled('feature')  # What if it fails?
```

**Solution**:
```python
# GOOD: Always provide default
enabled = flag_client.is_enabled('feature', user, default=False)
```

### 19.5 Tight Coupling

**Problem**: Flags embedded throughout codebase

**Solution**:
- Centralize flag checks
- Use dependency injection
- Abstract flag logic
- Clean architecture

---

## 20. Reference Implementation

### 20.1 Complete Example

**Feature Flag Service**:
```python
"""
Complete Feature Flag Service Implementation

Includes: caching, metrics, testing, monitoring
"""

from typing import Dict, Any, Optional
import hashlib
import time
from dataclasses import dataclass
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)


@dataclass
class User:
    """User context for flag evaluation"""
    id: str
    email: Optional[str] = None
    plan: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None


class FlagService:
    """
    Production-ready feature flag service

    Features:
    - Multiple evaluation strategies
    - Caching
    - Metrics
    - Error handling
    - Consistent bucketing
    """

    def __init__(self, cache_ttl: int = 60):
        self.cache_ttl = cache_ttl
        self.flags = {}
        self.metrics = {
            'evaluations': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'errors': 0
        }

    def register_flag(
        self,
        key: str,
        name: str,
        enabled: bool = True,
        rollout_percentage: float = 0,
        targeting_rules: Optional[list] = None
    ):
        """Register a feature flag"""
        self.flags[key] = {
            'key': key,
            'name': name,
            'enabled': enabled,
            'rollout_percentage': rollout_percentage,
            'targeting_rules': targeting_rules or []
        }
        logger.info(f"Registered flag: {key}")

    def is_enabled(
        self,
        flag_key: str,
        user: User,
        default: bool = False
    ) -> bool:
        """
        Evaluate if flag is enabled for user

        Returns default value on error
        """
        self.metrics['evaluations'] += 1

        try:
            # Check cache
            cache_key = f"{flag_key}:{user.id}"
            cached = self._get_cache(cache_key)
            if cached is not None:
                self.metrics['cache_hits'] += 1
                return cached

            self.metrics['cache_misses'] += 1

            # Get flag
            flag = self.flags.get(flag_key)
            if not flag:
                logger.warning(f"Flag not found: {flag_key}")
                return default

            # Check if flag is enabled
            if not flag['enabled']:
                self._set_cache(cache_key, False)
                return False

            # Apply targeting rules
            for rule in flag['targeting_rules']:
                if self._matches_rule(user, rule):
                    result = rule['variation'] == 'enabled'
                    self._set_cache(cache_key, result)
                    return result

            # Apply percentage rollout
            if flag['rollout_percentage'] > 0:
                in_rollout = self._is_in_rollout(
                    flag_key,
                    user.id,
                    flag['rollout_percentage']
                )
                self._set_cache(cache_key, in_rollout)
                return in_rollout

            # Default to disabled
            self._set_cache(cache_key, False)
            return False

        except Exception as e:
            self.metrics['errors'] += 1
            logger.error(f"Error evaluating flag {flag_key}: {e}")
            return default

    def _matches_rule(self, user: User, rule: Dict) -> bool:
        """Check if user matches targeting rule"""
        attribute = rule['attribute']
        operator = rule['operator']
        values = rule['values']

        user_value = getattr(user, attribute, None)
        if user_value is None:
            user_value = user.attributes.get(attribute) if user.attributes else None

        if user_value is None:
            return False

        if operator == 'equals':
            return user_value in values
        elif operator == 'not_equals':
            return user_value not in values
        elif operator == 'greater_than':
            return user_value > values[0]
        elif operator == 'less_than':
            return user_value < values[0]

        return False

    def _is_in_rollout(
        self,
        flag_key: str,
        user_id: str,
        percentage: float
    ) -> bool:
        """Consistent bucketing for percentage rollout"""
        hash_input = f"{flag_key}:{user_id}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        bucket = (hash_value % 10000) / 100.0
        return bucket < percentage

    @lru_cache(maxsize=1000)
    def _get_cache(self, key: str) -> Optional[bool]:
        """Get from cache (simplified)"""
        # In production, use Redis
        return None

    def _set_cache(self, key: str, value: bool):
        """Set cache (simplified)"""
        # In production, use Redis with TTL
        pass

    def get_metrics(self) -> Dict[str, int]:
        """Get service metrics"""
        return self.metrics.copy()


# Usage Example
if __name__ == '__main__':
    # Initialize service
    service = FlagService()

    # Register flags
    service.register_flag(
        key='new-dashboard',
        name='New Dashboard',
        enabled=True,
        rollout_percentage=25.0
    )

    service.register_flag(
        key='premium-features',
        name='Premium Features',
        enabled=True,
        targeting_rules=[{
            'attribute': 'plan',
            'operator': 'equals',
            'values': ['premium', 'enterprise'],
            'variation': 'enabled'
        }]
    )

    # Test evaluations
    free_user = User(id='user-1', plan='free')
    premium_user = User(id='user-2', plan='premium')

    print(f"Free user - new dashboard: {service.is_enabled('new-dashboard', free_user)}")
    print(f"Free user - premium features: {service.is_enabled('premium-features', free_user)}")
    print(f"Premium user - premium features: {service.is_enabled('premium-features', premium_user)}")

    # Print metrics
    print(f"\nMetrics: {service.get_metrics()}")
```

---

## Appendix A: Glossary

**A/B Test**: Experiment comparing two variations

**Allocation**: Distribution of users across variations

**Bucketing**: Assignment of users to variations

**Canary Deployment**: Gradual rollout starting with small group

**Client-Side Evaluation**: Flag evaluation in browser/mobile app

**Context**: User/request data used for targeting

**Experiment**: Test with multiple variations and metrics

**Evaluation**: Process of determining flag value

**Feature Flag**: Configuration controlling feature availability

**Kill Switch**: Emergency disable mechanism

**Ops Toggle**: Operational configuration flag

**Permission Toggle**: Access control flag

**Progressive Delivery**: Gradual rollout strategies

**Release Toggle**: Feature deployment control

**Rollout**: Gradual exposure of feature to users

**Segment**: Group of users with common attributes

**Server-Side Evaluation**: Flag evaluation on server

**Targeting**: Rules determining who sees what

**Variation**: Possible value of a flag

---

## Appendix B: Tools and Resources

**Flag Management Platforms**:
- LaunchDarkly: https://launchdarkly.com
- Split: https://www.split.io
- Unleash: https://www.getunleash.io
- ConfigCat: https://configcat.com
- Flagsmith: https://flagsmith.com

**SDKs and Libraries**:
- LaunchDarkly SDKs: https://docs.launchdarkly.com/sdk
- Unleash SDKs: https://docs.getunleash.io/sdks
- OpenFeature: https://openfeature.dev

**Books**:
- "Feature Toggles" by Pete Hodgson
- "Continuous Delivery" by Jez Humble

**Articles**:
- Martin Fowler: Feature Toggles
- Pete Hodgson: Feature Toggle Best Practices

---

## Appendix C: Quick Reference

**Common Commands**:
```bash
# Create flag
./manage_feature_flags.py create --key my-flag --name "My Flag"

# Update rollout
./manage_feature_flags.py update --key my-flag --rollout 50

# List flags
./manage_feature_flags.py list --environment production

# Analyze usage
./analyze_flag_usage.py track --flag my-flag --days 30

# Test variations
./test_flag_variations.py test --flag my-flag --all-variations
```

**Environment Variables**:
```bash
export LAUNCHDARKLY_SDK_KEY="sdk-key-..."
export UNLEASH_API_URL="https://unleash.example.com"
export UNLEASH_API_TOKEN="token-..."
```

**Quick Checks**:
```bash
# Check flag status
curl -H "Authorization: Bearer $API_KEY" \
  https://app.launchdarkly.com/api/v2/flags/default/my-flag

# Monitor metrics
curl http://localhost:8000/metrics | grep feature_flags

# View logs
tail -f /var/log/feature-flags.log | grep "flag_evaluation"
```

---

**Document Version**: 1.0
**Last Updated**: 2025-10-27
**Authors**: Feature Flags Team
**License**: Internal Use Only

---

*End of Feature Flags Reference Guide*
