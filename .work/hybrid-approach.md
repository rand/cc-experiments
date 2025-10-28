# Hybrid Approach: Pattern-Accelerated Skill Resources

**Date**: 2025-10-27
**Status**: ACTIVE
**Context**: After completing 24 manual skills (Waves 1-5), we're implementing a hybrid approach that maintains high quality while accelerating through pattern reuse.

---

## 1. Foundation: 24 Completed Skills

### Pattern Consistency Achieved (100%)
```
24 skills across 14 categories:
- REFERENCE.md: 1,400-4,500 lines each
- Scripts: 3 per skill (executable, --help, --json)
- Examples: 4-17 per skill (production-ready, multi-language)
- Skill updates: "## Level 3: Resources" section
```

### Categories Covered
- Security (3): tls-configuration, security-headers, api-authentication
- Database (2): postgres-query-optimization, postgres-migrations
- API (2): rest-api-design, graphql-schema-design
- Testing (3): integration-testing, test-driven-development, code-review
- Frontend (4): react-state-management, nextjs-seo, web-accessibility, websocket-implementation
- Infrastructure (4): terraform-best-practices, kubernetes-deployment, aws-lambda-deployment, dockerfile-optimization
- Realtime (2): consensus-raft, crdt-fundamentals
- Networking (1): http2-multiplexing
- Observability (2): distributed-tracing, metrics-instrumentation
- Data (1): redis-data-structures

---

## 2. Hybrid Methodology

### Core Principle
**Use 24 skills as templates while maintaining manual quality control**

### Three Acceleration Techniques

#### A. Category Templates
When creating Resources for a skill in a covered category, use existing skills as structural templates:

**Example: New API Skill**
- **Template**: rest-api-design + graphql-schema-design
- **REFERENCE.md sections**: Adapt from template structure
- **Scripts**: Reuse script types (validate, generate, benchmark)
- **Examples**: Follow language mix pattern (Python, TypeScript, Go)
- **Acceleration**: 40-50% faster than pure manual

#### B. Script Archetypes
Identify reusable script patterns across the 24 skills:

**Script Type 1: Validation/Analysis**
- Examples: check_accessibility.py, analyze_traces.py, analyze_schema.py
- Pattern: CLI with --json, error detection, recommendations
- Template: CLI boilerplate, JSON output, error handling

**Script Type 2: Generation/Optimization**
- Examples: generate_migration.py, optimize_image.sh, generate_sitemap.py
- Pattern: Input processing, generation logic, output validation
- Template: Input validation, generation framework, testing

**Script Type 3: Testing/Benchmarking**
- Examples: test_headers.sh, benchmark_queries.sh, test_keyboard_nav.js
- Pattern: Test execution, result collection, reporting
- Template: Test runner, metrics collection, JSON reports

**Acceleration**: Start with archetype, customize for skill domain

#### C. REFERENCE.md Sections
Common sections across all 24 skills:

**Universal Sections**:
1. Fundamentals / Overview
2. Core Concepts / Architecture
3. Best Practices
4. Common Patterns
5. Tools & Implementations
6. Anti-Patterns / Pitfalls
7. Performance Considerations
8. References & Further Reading

**Acceleration**: Use section structure as outline, fill with skill-specific content

---

## 3. Quality Gates (Maintain 100%)

### Pre-Launch Validation
- [ ] Skill category understood
- [ ] Closest template skills identified (2-3)
- [ ] Domain-specific requirements documented
- [ ] Script types appropriate for skill

### During Creation
- [ ] REFERENCE.md sections follow template structure
- [ ] Scripts executable with --help and --json
- [ ] Examples production-ready and multi-language
- [ ] Pattern consistency with 24 completed skills

### Post-Creation Validation
- [ ] All files created (REFERENCE.md, 3 scripts, 4+ examples)
- [ ] Scripts executable (chmod 755)
- [ ] Documentation complete
- [ ] No TODO/mock/stub comments
- [ ] Skill file updated with Level 3 section

### Manual Review Checkpoints
- [ ] REFERENCE.md technical accuracy
- [ ] Script functionality and CLI interface
- [ ] Example code quality and variety
- [ ] Overall pattern consistency

---

## 4. Wave 6 Execution Plan

### Skill Selection Strategy
**Prioritize**:
1. **High-value categories not yet covered**: AI/ML, Mobile, Data pipelines
2. **Categories with 1 skill**: Expand coverage (networking, data)
3. **Common workflows**: CI/CD, monitoring, caching

### Wave 6 Candidates (5 skills)
1. **ci-cd-github-actions** (engineering/ci-cd)
   - Template: terraform-best-practices, kubernetes-deployment
   - Scripts: validate workflow, optimize pipeline, test actions

2. **prometheus-monitoring** (observability/prometheus-monitoring)
   - Template: metrics-instrumentation, distributed-tracing
   - Scripts: validate config, analyze metrics, test alerts

3. **api-rate-limiting** (api/api-rate-limiting)
   - Template: rest-api-design, api-authentication
   - Scripts: test rate limits, analyze patterns, benchmark throughput

4. **nginx-configuration** (networking/nginx-configuration)
   - Template: http2-multiplexing, tls-configuration
   - Scripts: validate config, optimize settings, test performance

5. **elasticsearch-search** (database/elasticsearch-search)
   - Template: postgres-query-optimization, redis-data-structures
   - Scripts: analyze queries, optimize indexes, benchmark search

### Parallel Execution Strategy
- **5 agents** (Agent-H1 through Agent-H5)
- **Each agent receives**:
  - Skill specification
  - 2-3 template skills for reference
  - Script archetype guidelines
  - REFERENCE.md section structure
  - Quality gate checklist

### Expected Velocity
- **Time**: 40-50% faster than pure manual (Waves 1-5)
- **Quality**: Maintain 100% pattern consistency
- **Output**: ~25,000-35,000 lines per wave

---

## 5. Hybrid Agent Prompt Template

```markdown
## Task: Create Level 3 Resources for {skill_name}

### Template Skills (Use as Reference)
1. {template_skill_1} - {reason}
2. {template_skill_2} - {reason}

### Required Outputs
1. **REFERENCE.md** (1,500-4,000 lines)
   - Use section structure from templates
   - Technical depth and code examples
   - References to RFCs, specs, official docs

2. **3 Scripts** (400-600 lines each)
   - Script 1: {type} (see archetype)
   - Script 2: {type} (see archetype)
   - Script 3: {type} (see archetype)
   - All: executable, --help, --json, CLI

3. **4-10 Examples** (production-ready)
   - Follow language mix from templates
   - Complete, runnable code
   - Well-commented with error handling

4. **Skill File Update**
   - Add "## Level 3: Resources" section
   - Document REFERENCE.md, scripts, examples
   - Include quick start examples

### Script Archetypes
{relevant_archetypes}

### Quality Gates
{quality_checklist}

### Output Format
Report skills/category/skill-name/resources/ directory with:
- REFERENCE.md created (line count)
- 3 scripts created (names, line counts)
- Examples created (count, languages)
- Skill file updated (confirm)

Keep report CONCISE (under 2000 lines).
```

---

## 6. Success Metrics

### Quantitative
- **Velocity**: 40-50% faster than pure manual
- **Quality**: 100% pattern consistency maintained
- **Coverage**: All scripts executable, all examples runnable
- **Documentation**: Complete REFERENCE.md with examples

### Qualitative
- **Technical Accuracy**: Grounded in official docs, RFCs, best practices
- **Production Ready**: Scripts and examples immediately usable
- **Comprehensive**: REFERENCE.md covers fundamentals through advanced
- **Consistent**: Follows established pattern from 24 skills

---

## 7. Rollout Plan

### Wave 6 (This Wave)
- 5 skills using hybrid approach
- Full manual review of all outputs
- Refine hybrid methodology based on results

### Wave 7+
- Scale to 6-7 skills per wave (if quality maintained)
- Introduce additional accelerations (e.g., script templates)
- Continue manual review checkpoints

### Long-term
- Target: 60-80 skills with Resources (from original 123 HIGH priority)
- Timeline: 8-12 weeks at 5-7 skills/wave
- Quality: Maintain 100% pattern consistency

---

## 8. Risk Mitigation

### Risk: Quality Degradation
**Mitigation**: Manual review checkpoints, quality gates, pattern validation

### Risk: Template Over-reliance
**Mitigation**: Domain-specific customization required, multiple templates per skill

### Risk: Script Functionality
**Mitigation**: All scripts must be executable and tested

### Risk: Context Efficiency Loss
**Mitigation**: Maintain Level 3 pattern (bash execution, not context loading)

---

## Next Action

**Launch Wave 6**: 5 skills with hybrid approach, parallel agents, full quality gates.
