# DSPy Optimization Checklist

Comprehensive checklist for optimizing DSPy programs with teleprompters.

## Pre-Optimization

### Data Preparation
- [ ] Training dataset collected (min 50 examples)
- [ ] Validation dataset collected (separate from training)
- [ ] Test dataset collected (never used for optimization)
- [ ] Data quality reviewed (no duplicates, errors)
- [ ] Data distribution balanced (no class imbalance)
- [ ] Examples have all required fields
- [ ] Input fields marked with `.with_inputs()`

### Baseline Evaluation
- [ ] Baseline model defined (unoptimized)
- [ ] Evaluation metric defined clearly
- [ ] Baseline score measured on test set
- [ ] Performance targets set (e.g., >80% accuracy)
- [ ] Current bottlenecks identified

### Environment Setup
- [ ] LM configured and tested
- [ ] API keys secured in environment variables
- [ ] Cost budget defined ($10, $100, etc.)
- [ ] Timeout configured for optimization job
- [ ] Version control snapshot created

## Optimization Strategy

### Optimizer Selection
- [ ] **BootstrapFewShot**: For quick iteration (<1 hour)
- [ ] **MIPROv2**: For production quality (2-8 hours)
- [ ] **COPRO**: For multi-module pipelines
- [ ] **GEPA**: For multi-agent systems
- [ ] **BootstrapFinetune**: For maximum accuracy (if >1000 examples)

### Hyperparameters
- [ ] `max_bootstrapped_demos` set (2-6 recommended)
- [ ] `max_labeled_demos` set (0-3 recommended)
- [ ] `num_candidates` set for MIPROv2 (5-20)
- [ ] `metric_threshold` set (0.7-0.9 recommended)
- [ ] `auto` level chosen (light/medium/heavy)

### Cost Estimation
- [ ] Estimated LM calls calculated (examples × candidates × rounds)
- [ ] Estimated tokens calculated (~300 tokens/call avg)
- [ ] Estimated cost calculated (tokens × cost_per_1k)
- [ ] Budget approved
- [ ] Monitoring set up for actual costs

## During Optimization

### Monitoring
- [ ] Progress logs reviewed periodically
- [ ] Intermediate scores tracked
- [ ] Candidate prompts inspected
- [ ] Examples passing/failing tracked
- [ ] Resource usage monitored (CPU, memory)

### Quality Checks
- [ ] Bootstrapped examples reviewed for quality
- [ ] Generated prompts make sense
- [ ] No overfitting to training data
- [ ] Validation scores improving
- [ ] No error spikes in logs

### Intermediate Saves
- [ ] Checkpoints saved every N iterations
- [ ] Partial results saved
- [ ] Best candidate tracked separately
- [ ] Logs backed up
- [ ] Time estimates updated

## Post-Optimization

### Validation
- [ ] Final model compiled successfully
- [ ] Validation score improved vs baseline
- [ ] Test score improved vs baseline (final check)
- [ ] Improvement statistically significant
- [ ] No degradation on edge cases

### Quality Assurance
- [ ] Generated prompts reviewed manually
- [ ] Sample predictions inspected
- [ ] Error analysis performed on failures
- [ ] Bias evaluation conducted
- [ ] Prompt length acceptable (<5000 tokens)

### Versioning
- [ ] Optimized model saved with version (v1, v2, etc.)
- [ ] Git commit created with optimization results
- [ ] Metadata saved (scores, hyperparameters, date)
- [ ] Training data snapshot saved
- [ ] Optimizer config saved for reproducibility

## Deployment Preparation

### Model Export
- [ ] Compiled model saved to file (`.json`, `.pkl`)
- [ ] Model loadable without re-optimization
- [ ] Model size acceptable (<100MB)
- [ ] Loading time acceptable (<5s)
- [ ] Dependencies documented

### A/B Testing Setup
- [ ] Baseline model ready for comparison
- [ ] Optimized model ready for comparison
- [ ] Traffic split configured (90/10 or 70/30)
- [ ] Metrics tracked for both variants
- [ ] Rollback plan defined

### Documentation
- [ ] Optimization results documented
  - Baseline score
  - Final score
  - Improvement percentage
  - Hyperparameters used
  - Training set size
  - Optimization time
  - Total cost
- [ ] Failure modes documented
- [ ] Known limitations noted
- [ ] Deployment instructions written

## Deployment

### Staging Validation
- [ ] Deployed to staging environment
- [ ] Smoke tests passed
- [ ] Integration tests passed
- [ ] Performance tests passed
- [ ] Security scan passed

### Production Rollout
- [ ] Feature flag configured for gradual rollout
- [ ] Monitoring dashboards updated
- [ ] Alerts configured (latency, errors)
- [ ] On-call team notified
- [ ] Rollback procedure tested

### Monitoring (First 24 Hours)
- [ ] Request rate monitored
- [ ] Latency monitored (vs baseline)
- [ ] Error rate monitored
- [ ] Success rate monitored
- [ ] User feedback collected

## Post-Deployment

### Performance Analysis
- [ ] A/B test results analyzed
- [ ] Statistical significance confirmed
- [ ] Cost per request calculated
- [ ] User satisfaction measured
- [ ] Business metrics impacted positively

### Iteration Planning
- [ ] Failure cases identified
- [ ] Additional training data needed identified
- [ ] Next optimization iteration planned
- [ ] Schedule for re-optimization set (quarterly?)
- [ ] Continuous evaluation pipeline set up

### Knowledge Sharing
- [ ] Results presented to team
- [ ] Learnings documented
- [ ] Best practices updated
- [ ] Optimization playbook updated
- [ ] Retrospective conducted

---

## Common Pitfalls to Avoid

❌ **Optimizing on test set**: Use separate train/val/test splits
❌ **Too few examples**: Need 50+ for BootstrapFewShot, 500+ for MIPROv2
❌ **Vague metrics**: Define clear, measurable success criteria
❌ **Optimizing in production**: Always pre-compile offline
❌ **No baseline**: Can't measure improvement without baseline
❌ **Ignoring costs**: Set budgets and monitor spending
❌ **Skipping validation**: Always validate on held-out data
❌ **No version control**: Track all models and configs in git
❌ **Single optimization run**: Try multiple hyperparameter combinations
❌ **Deploying without A/B test**: Always test before full rollout

---

## Optimization Timeline

**Quick Iteration** (2-4 hours):
- BootstrapFewShot with 50 examples
- 2-4 demos, light optimization
- Good for development and prototyping

**Production Quality** (1-2 days):
- MIPROv2 with 500+ examples
- 10-20 candidates, medium optimization
- Multiple hyperparameter trials
- Comprehensive evaluation

**Maximum Performance** (3-7 days):
- MIPROv2 heavy + BootstrapFinetune
- 1000+ examples
- Grid search over hyperparameters
- Extensive evaluation and validation

---

**Version**: 1.0
**Last Updated**: 2025-10-30
