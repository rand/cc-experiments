# Feature Flag Retirement Workflow

Production-ready workflow for safely retiring feature flags with checklists, timelines, and automation.

## Overview

Feature flag retirement is critical to prevent technical debt. This workflow ensures safe, systematic flag removal.

## Retirement Phases

### Phase 1: Identification (Week 1)

**Objective**: Identify flags ready for retirement

**Checklist**:
- [ ] Flag has been at 100% rollout for 30+ days
- [ ] No active experiments using this flag
- [ ] No customer-facing issues reported
- [ ] Flag variation is consistently used (>99%)
- [ ] Business stakeholders approve removal
- [ ] Technical team reviews impact

**Analysis**:
```bash
# Check flag usage
./analyze_flag_usage.py track --flag feature-x --days 90

# Check stale flags
./analyze_flag_usage.py stale --threshold 90 --flags-file flags.json

# Get retirement recommendations
./analyze_flag_usage.py recommend-retire \
    --confidence 0.8 \
    --flags-file flags.json
```

**Criteria for Retirement**:
1. **Age**: Flag is 90+ days old
2. **Stability**: No changes in 30+ days
3. **Consistency**: Single variation used >99% of time
4. **Impact**: Low risk to business operations
5. **Dependencies**: No other flags depend on it

**Output**: List of candidate flags with confidence scores

### Phase 2: Planning (Week 2)

**Objective**: Create detailed retirement plan

**Tasks**:

1. **Code Analysis**
   ```bash
   # Find all code references
   grep -r "feature-x" --include="*.py" --include="*.js" .

   # Or use the analysis tool
   ./analyze_flag_usage.py debt --flag feature-x --flags-file flags.json
   ```

2. **Dependency Mapping**
   - Identify services using the flag
   - Check for SDK integrations
   - Review analytics/monitoring dependencies
   - Document configuration files

3. **Impact Assessment**
   | Area | Impact Level | Notes |
   |------|-------------|-------|
   | Frontend | Low | Only in 2 components |
   | Backend | Medium | Used in 5 services |
   | Mobile | None | Not used |
   | Analytics | High | Multiple dashboards |
   | Tests | Medium | 15 tests reference flag |

4. **Rollback Plan**
   - Document how to re-enable if needed
   - Identify monitoring metrics
   - Define rollback triggers

**Output**: Retirement plan document

### Phase 3: Communication (Week 2-3)

**Objective**: Notify stakeholders and prepare teams

**Communication Plan**:

1. **Announcement** (Week 2, Monday)
   ```
   Subject: Feature Flag Retirement: feature-x

   We plan to retire the 'feature-x' feature flag in 2 weeks.

   Timeline:
   - Week 3: Code cleanup begins
   - Week 4: Flag removed from codebase
   - Week 5: Monitoring period

   Impact:
   - [List affected areas]

   Action Required:
   - Review your services for dependencies
   - Update documentation
   - Notify your team

   Questions? Contact: [Team]
   ```

2. **Team Notifications**
   - Engineering teams
   - Product managers
   - QA/Testing teams
   - DevOps/SRE
   - Support team

3. **Documentation Updates**
   - Update feature flag registry
   - Mark flag as "deprecated" in code
   - Add warnings to SDK calls

**Checklist**:
- [ ] Sent announcement email
- [ ] Posted in Slack/Teams channels
- [ ] Updated Jira/Linear tickets
- [ ] Marked flag as deprecated in LaunchDarkly/Unleash
- [ ] Updated README and docs

### Phase 4: Deprecation (Week 3)

**Objective**: Mark flag as deprecated and prepare for removal

**Steps**:

1. **Add Deprecation Warnings**
   ```python
   # Python example
   import warnings

   def check_feature_x():
       warnings.warn(
           "feature-x flag is deprecated and will be removed in v2.0",
           DeprecationWarning,
           stacklevel=2
       )
       return feature_flags.is_enabled('feature-x')
   ```

   ```javascript
   // JavaScript example
   function checkFeatureX() {
       console.warn('feature-x flag is deprecated and will be removed in v2.0');
       return featureFlags.isEnabled('feature-x');
   }
   ```

2. **Update Flag Metadata**
   ```bash
   # Using management tool
   ./manage_feature_flags.py update \
       --key feature-x \
       --environment production \
       --description "DEPRECATED: Will be removed 2025-02-01"
   ```

3. **Add Tests for Removal**
   ```python
   # Test that flag can be safely removed
   def test_feature_x_removal():
       # Verify default behavior
       result = get_feature_behavior(flag_enabled=False)
       assert result == expected_default_behavior

       # Verify flag enabled behavior (should be same)
       result = get_feature_behavior(flag_enabled=True)
       assert result == expected_default_behavior
   ```

**Checklist**:
- [ ] Deprecation warnings added
- [ ] Flag marked as deprecated in provider
- [ ] Tests verify removal safety
- [ ] Monitoring alerts updated
- [ ] Documentation reflects deprecation

### Phase 5: Code Cleanup (Week 4)

**Objective**: Remove flag references from code

**Process**:

1. **Create Feature Branch**
   ```bash
   git checkout -b remove-feature-x-flag
   ```

2. **Remove Flag Checks**
   ```python
   # Before
   if feature_flags.is_enabled('feature-x'):
       new_implementation()
   else:
       legacy_implementation()

   # After (keep winning variation)
   new_implementation()
   ```

3. **Remove Unused Code**
   - Delete legacy code paths
   - Remove conditional logic
   - Clean up imports
   - Update comments

4. **Update Tests**
   ```python
   # Before
   @parametrize('flag_enabled', [True, False])
   def test_feature_x(flag_enabled):
       # Test both paths
       pass

   # After
   def test_feature_x():
       # Test single path
       pass
   ```

5. **Update Documentation**
   - Remove flag from feature flag registry
   - Update architecture docs
   - Clean up onboarding guides

**Automated Cleanup Tool**:
```bash
# Find and replace
find . -type f -name "*.py" -exec sed -i '' \
    '/feature-x/d' {} +

# Verify changes
git diff --stat
```

**Checklist**:
- [ ] All flag checks removed
- [ ] Legacy code paths deleted
- [ ] Tests updated
- [ ] Documentation updated
- [ ] Code reviewed
- [ ] All tests passing

### Phase 6: Flag Removal (Week 4-5)

**Objective**: Remove flag from provider and configuration

**Steps**:

1. **Disable Flag**
   ```bash
   ./manage_feature_flags.py toggle \
       --key feature-x \
       --environment production \
       --enabled false
   ```

2. **Monitor for 48 Hours**
   - Check error rates
   - Review user complaints
   - Monitor performance metrics
   - Verify rollback readiness

3. **Archive Flag** (After monitoring period)
   ```bash
   ./manage_feature_flags.py archive \
       --key feature-x \
       --environment production
   ```

4. **Remove from Code** (After archive)
   ```bash
   git add .
   git commit -m "Remove feature-x flag after successful rollout"
   git push origin remove-feature-x-flag
   ```

5. **Deploy Changes**
   - Deploy to staging
   - Run integration tests
   - Deploy to production
   - Monitor rollout

**Monitoring Checklist**:
- [ ] Error rates stable
- [ ] Performance metrics unchanged
- [ ] No customer complaints
- [ ] Rollback plan tested
- [ ] On-call team notified

### Phase 7: Verification (Week 5-6)

**Objective**: Verify complete removal and cleanup

**Verification Steps**:

1. **Code Search**
   ```bash
   # Ensure no references remain
   grep -r "feature-x" . --include="*.py" --include="*.js"

   # Should return no results
   ```

2. **Provider Verification**
   ```bash
   # Verify flag is archived
   ./manage_feature_flags.py list \
       --environment production \
       --archived true | grep feature-x
   ```

3. **Monitoring Review**
   - 7 days of metrics post-removal
   - No anomalies detected
   - Performance stable

4. **Documentation Audit**
   - Flag removed from all docs
   - Blog posts updated
   - Training materials current

**Final Checklist**:
- [ ] No code references found
- [ ] Flag archived in provider
- [ ] 7 days of stable metrics
- [ ] Documentation updated
- [ ] Team notified of completion
- [ ] Postmortem written (if issues)

## Timeline Summary

| Week | Phase | Key Activities |
|------|-------|----------------|
| 1 | Identification | Analyze usage, get approvals |
| 2 | Planning | Map dependencies, create plan |
| 2-3 | Communication | Notify stakeholders |
| 3 | Deprecation | Mark deprecated, add warnings |
| 4 | Code Cleanup | Remove flag checks |
| 4-5 | Flag Removal | Archive flag, deploy changes |
| 5-6 | Verification | Confirm complete removal |

## Automation Scripts

### 1. Flag Retirement Candidate Finder
```bash
#!/bin/bash
# find_retirement_candidates.sh

./analyze_flag_usage.py recommend-retire \
    --confidence 0.8 \
    --flags-file flags.json \
    --json > candidates.json

# Generate report
./analyze_flag_usage.py report \
    --results candidates.json \
    --format html \
    --output retirement_candidates.html
```

### 2. Code Reference Scanner
```bash
#!/bin/bash
# scan_flag_references.sh

FLAG_KEY=$1

echo "Scanning for references to: $FLAG_KEY"

# Find in code
echo "=== Code References ==="
rg "$FLAG_KEY" --type py --type js --type go

# Find in configs
echo "=== Config References ==="
find . -name "*.yaml" -o -name "*.json" | xargs grep "$FLAG_KEY"

# Find in tests
echo "=== Test References ==="
rg "$FLAG_KEY" --glob "*test*"
```

### 3. Safe Removal Verifier
```bash
#!/bin/bash
# verify_safe_removal.sh

FLAG_KEY=$1

echo "Verifying safe removal of: $FLAG_KEY"

# Check usage stats
./analyze_flag_usage.py track --flag "$FLAG_KEY" --days 90

# Check for dependencies
./analyze_flag_usage.py debt --flag "$FLAG_KEY"

# Run tests
pytest tests/ -v

echo "Verification complete"
```

## Rollback Procedures

### Emergency Rollback

If issues detected after flag removal:

1. **Immediate Response** (0-15 minutes)
   ```bash
   # Revert deployment
   kubectl rollout undo deployment/app

   # Or revert via CD tool
   argocd app rollback app-production
   ```

2. **Re-enable Flag** (15-30 minutes)
   ```bash
   # Re-create flag if deleted
   ./manage_feature_flags.py create \
       --key feature-x \
       --name "Feature X (Restored)" \
       --type release \
       --variations '{"on": true, "off": false}' \
       --default off \
       --enabled
   ```

3. **Communication** (30-60 minutes)
   - Notify stakeholders
   - Update incident tracker
   - Schedule postmortem

## Best Practices

1. **Never Rush**: Take full 6 weeks if needed
2. **Monitor Continuously**: Watch metrics at each phase
3. **Communicate Early**: Notify teams early and often
4. **Document Everything**: Keep detailed records
5. **Test Thoroughly**: Verify each step
6. **Plan Rollback**: Always have escape plan
7. **Learn from Issues**: Write postmortems

## Common Pitfalls

- **Removing too quickly**: Skipping monitoring periods
- **Missing dependencies**: Not checking all services
- **Poor communication**: Surprising teams with changes
- **No rollback plan**: Unable to revert if issues
- **Incomplete removal**: Leaving dead code/configs

## Success Metrics

- Time to retirement: < 6 weeks
- Zero production incidents
- No customer impact
- Complete code removal
- Team satisfaction: High

## Tools Reference

- `manage_feature_flags.py`: Flag CRUD operations
- `analyze_flag_usage.py`: Usage analytics
- `test_flag_variations.py`: Validation testing

## Conclusion

Follow this workflow to safely retire feature flags without disruption. Take time, communicate well, and monitor carefully.
