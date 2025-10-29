# Production Debugging Checklist

Comprehensive checklist for safe and effective production debugging.

## Pre-Debug Checklist

### Environment Verification
- [ ] Confirmed issue exists in production
- [ ] Checked if reproducible in staging/test
- [ ] Verified correct production environment (not dev/staging)
- [ ] Noted current traffic levels and load
- [ ] Identified time window of issue occurrence

### Safety Assessment
- [ ] Selected replica/secondary instance (not primary)
- [ ] Confirmed instance can be taken out of rotation if needed
- [ ] Assessed customer impact of debug operations
- [ ] Set timeout limits for all debug operations (max 60 seconds)
- [ ] Configured resource limits (CPU < 80%, Memory < 85%)
- [ ] Prepared rollback plan if issue worsens

### Team Communication
- [ ] Notified team in war room/incident channel
- [ ] Incident Commander aware and approved (if SEV-1/SEV-2)
- [ ] On-call engineer standing by
- [ ] Documented planned debug activities
- [ ] Set up real-time communication channel

### Data Collection (Non-Invasive)
- [ ] Exported relevant logs for offline analysis
- [ ] Captured baseline metrics from monitoring dashboards
- [ ] Saved example failing requests/traces
- [ ] Identified correlated services/dependencies
- [ ] Checked for recent deployments/config changes

---

## During Debugging

### Continuous Monitoring
- [ ] Monitor customer-facing metrics during debug
- [ ] Watch error rates and latency percentiles
- [ ] Check resource utilization of debug target
- [ ] Monitor impact of debug tools themselves
- [ ] Set alerts for degradation

### Documentation
- [ ] Document all commands executed
- [ ] Record timestamps of actions
- [ ] Capture tool outputs and observations
- [ ] Note any unexpected behaviors
- [ ] Track hypotheses tested

### Safety Checks (Every 5 Minutes)
- [ ] Customer metrics still acceptable
- [ ] No increase in error rates
- [ ] System resources within limits
- [ ] Debug tools not causing issues
- [ ] Team communication maintained

---

## Debugging Approaches (In Order of Safety)

### 1. Log Analysis (Safest)
- [ ] Review application logs in time window
- [ ] Check for error patterns
- [ ] Correlate across services
- [ ] Look for warnings before failures
- [ ] Analyze log volume trends

### 2. Metrics Analysis
- [ ] Check error rate metrics
- [ ] Analyze latency percentiles (p50, p95, p99)
- [ ] Review resource utilization (CPU, memory, disk, network)
- [ ] Compare with baseline/historical data
- [ ] Look for anomalies or spikes

### 3. Distributed Tracing
- [ ] Query failing traces by time window
- [ ] Identify slow spans (latency bottlenecks)
- [ ] Check for error spans
- [ ] Map service dependencies
- [ ] Analyze critical path

### 4. Database Debugging
- [ ] Check slow query logs
- [ ] Review active connections and locks
- [ ] Analyze query execution plans
- [ ] Monitor connection pool usage
- [ ] Check for deadlocks

### 5. Network Debugging
- [ ] Capture packet samples (not full traffic)
- [ ] Check for retransmissions
- [ ] Analyze connection states (TIME_WAIT, CLOSE_WAIT)
- [ ] Test connectivity between services
- [ ] Review DNS resolution

### 6. Memory Debugging (Medium Risk)
- [ ] Profile memory usage trend (non-invasive sampling)
- [ ] Take heap snapshot if needed (10-30 seconds max)
- [ ] Compare snapshots if multiple available
- [ ] Check for leak patterns
- [ ] Review GC metrics if applicable

### 7. Live Profiling (Higher Risk)
- [ ] Use sampling profilers only (py-spy, pprof)
- [ ] Set strict time limit (30-60 seconds max)
- [ ] Monitor impact on latency
- [ ] Use low sampling rate (50-100 Hz)
- [ ] Stop immediately if issues detected

---

## Post-Debug Checklist

### Cleanup
- [ ] Stopped all debug tools and processes
- [ ] Disabled any trace collection if enabled
- [ ] Removed debug endpoints if added
- [ ] Restored instance to normal rotation
- [ ] Cleaned up temporary files and captures
- [ ] Verified system returned to baseline

### Documentation
- [ ] Documented root cause (if found)
- [ ] Captured evidence and supporting data
- [ ] Created timeline of investigation
- [ ] Noted what worked and what didn't
- [ ] Saved debug artifacts for reference

### Follow-Up
- [ ] Created postmortem or incident report
- [ ] Shared findings with team
- [ ] Created tickets for permanent fixes
- [ ] Updated runbooks with learnings
- [ ] Scheduled postmortem meeting if warranted

### Verification
- [ ] Confirmed issue resolved or mitigated
- [ ] Verified no new issues introduced
- [ ] Checked customer-facing metrics returned to normal
- [ ] Monitored for issue recurrence (24 hours)

---

## Emergency Abort Criteria

Stop debugging immediately if:

- [ ] Error rate increases significantly
- [ ] Latency degrades noticeably
- [ ] Customer complaints spike
- [ ] System becomes unstable
- [ ] Resource limits exceeded (CPU > 90%, Memory > 90%)
- [ ] Debug tools causing cascading failures
- [ ] Unable to roll back changes

**Emergency Actions:**
1. STOP all debug operations immediately
2. Kill debug tools/processes
3. Remove instance from rotation if needed
4. NOTIFY incident commander and team
5. ASSESS if debug contributed to instability
6. REVERT any changes made
7. DOCUMENT what was attempted
8. REGROUP to plan safer approach

---

## Tool Safety Reference

### Safe for Production (Low Risk)
- Log analysis (offline)
- Metrics collection and dashboards
- Distributed trace analysis (sampled)
- Read-only database queries
- Network packet capture (filtered, time-limited)

### Use with Caution (Medium Risk)
- Sampling profilers (py-spy, pprof) with time limits
- Heap snapshots (quick, < 30 seconds)
- System call tracing (strace) on single replica
- Core dump analysis (after process crash)
- Ephemeral debug containers (Kubernetes)

### Avoid or Extreme Caution (High Risk)
- Debugger attachment (pauses execution)
- Full traffic tracing (high overhead)
- Heap dumps on large processes (long pause)
- Code hot-patching (unpredictable)
- Blocking debug operations

---

## Common Issues Quick Reference

### High Error Rate
1. Check recent deployments → Rollback if recent
2. Check external dependencies → Enable circuit breaker
3. Check database → Review slow queries, connection pool
4. Check rate limiting → Adjust if false positives

### High Latency
1. Check distributed traces → Find slow spans
2. Check database queries → Optimize slow queries
3. Check external APIs → Set timeouts, enable caching
4. Check resource utilization → Scale if needed

### Memory Issues
1. Check memory growth trend → Look for leaks
2. Check heap size → May need increase
3. Check GC metrics → Tune if excessive
4. Check for large allocations → Stream instead

### Connection Issues
1. Check connection pool → May be exhausted
2. Check network connectivity → Test between services
3. Check DNS resolution → Verify records
4. Check TLS certificates → May be expired

---

## Remember

1. **Safety First**: Never compromise customer experience
2. **Minimal Impact**: Use least invasive method that works
3. **Time Limits**: Always set timeouts on operations
4. **Team Aware**: Keep everyone informed
5. **Document Everything**: For yourself and others
6. **Learn and Share**: Update runbooks with findings

**When in doubt, stop and ask for help.**
