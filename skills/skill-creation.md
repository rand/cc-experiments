---
name: skill-creation
description: Creating new atomic skills for the skills system
---



# Skill Creation

**Scope**: Creating atomic skills, structure, integration with CLAUDE.md, discovery patterns
**Lines**: ~400
**Last Updated**: 2025-10-18

## When to Use This Skill

Activate this skill when:
- Creating new atomic skills for the skills system
- Refactoring monolithic skills into atomic components
- Documenting specialized knowledge for reuse
- Integrating new skills into CLAUDE.md efficiently
- Establishing skill discovery patterns
- Ensuring skills remain composable and maintainable

## Core Concepts

### Atomic Skill Principles

**Atomicity**: One skill, one focus
- Single domain (e.g., "Postgres query optimization" not "All database skills")
- Clear scope boundary
- Self-contained knowledge
- Can be read and applied in isolation

**Composability**: Skills combine for workflows
- Reference related skills
- Support skill chaining (Skill A → Skill B → Skill C)
- Work together for complex tasks
- No circular dependencies

**Discoverability**: Pattern-based finding
- Filename matches domain (`postgres-*.md`, `api-*.md`)
- Category directories (`cicd/`, `infrastructure/`)
- Keywords in "When to Use This Skill"
- Referenced in _INDEX.md

**Efficiency**: Optimal size and structure
- **Target**: 250-400 lines
- **Maximum**: 500 lines (split if larger)
- **Minimum**: 150 lines (merge if smaller)
- Scannable sections with clear headers

### Integration Philosophy

**CLAUDE.md stays lean**:
- Don't list every skill individually
- Use category summaries with counts
- Provide Quick Category Reference for pattern matching
- Target: Keep CLAUDE.md under 800 lines

**_INDEX.md is comprehensive**:
- Complete skill catalog with tables
- Discovery patterns (by tech, task, domain)
- Skill combination examples (workflows)
- Quick reference for common tasks

---

## Skill Structure Template

### Required Sections

Every atomic skill must include:

```markdown
# [Skill Name]

**Scope**: One-line description of what this skill covers
**Lines**: ~[estimated line count]
**Last Updated**: YYYY-MM-DD

## When to Use This Skill

Activate this skill when:
- [Specific trigger 1]
- [Specific trigger 2]
- [Specific trigger 3]
- [Specific trigger 4]
- [Specific trigger 5]

## Core Concepts

### [Concept 1]

**[Sub-concept]**:
- Key point 1
- Key point 2
- Key point 3

### [Concept 2]

[Explanation with code examples where applicable]

---

## Patterns

### [Pattern 1 Name]

```[language]
// Code example
// With explanatory comments
```

**When to use**:
- Condition 1
- Condition 2

### [Pattern 2 Name]

```[language]
// Another example
```

**Benefits**:
- Benefit 1
- Benefit 2

---

## Quick Reference

### [Reference Table or Command List]

```
Command/Pattern    | Use Case           | Example
-------------------|--------------------|---------
[item]             | [when to use]      | [example]
```

### [Key Guidelines]

```
✅ DO: [Good practice]
✅ DO: [Good practice]
❌ DON'T: [Anti-pattern]
❌ DON'T: [Anti-pattern]
```

---

## Anti-Patterns

❌ **[Anti-pattern 1]**: [Why it's bad]
✅ [Correct approach]

❌ **[Anti-pattern 2]**: [Why it's bad]
✅ [Correct approach]

---

## Related Skills

- `related-skill-1.md` - [How it relates]
- `related-skill-2.md` - [How it relates]
- `related-skill-3.md` - [How it relates]

---

**Last Updated**: YYYY-MM-DD
**Format Version**: 1.0 (Atomic)
```

### Section Guidelines

**"When to Use This Skill"**:
- 5-8 specific activation triggers
- Action-oriented ("Implementing X", "Debugging Y")
- Helps with skill discovery
- Should match _INDEX.md "Use When" column

**"Core Concepts"**:
- Foundational knowledge
- Mental models and frameworks
- 2-4 major concepts
- Each concept 3-5 sub-points

**"Patterns"**:
- Practical code examples
- Real-world scenarios
- Copy-paste ready snippets
- Commented for clarity

**"Quick Reference"**:
- Cheat sheet format
- Tables, lists, command references
- Scannable at a glance
- Emergency lookup section

**"Anti-Patterns"**:
- Common mistakes
- What NOT to do
- Why it's wrong + correct alternative
- Learn from common errors

**"Related Skills"**:
- 3-6 related atomic skills
- How they connect (workflow, dependency, alternative)
- Enables skill composition

---

## Creating a New Skill

### Step 1: Scope Definition

**Ask these questions**:
1. What's the **single focus** of this skill?
2. Can I describe it in **one line**?
3. Is it **too broad**? (Split into multiple skills)
4. Is it **too narrow**? (Merge with related skill)
5. What are **5 triggers** for activating this skill?

**Example scoping**:
- ❌ "Database development" → Too broad
- ❌ "PostgreSQL EXPLAIN ANALYZE" → Too narrow
- ✅ "Postgres query optimization" → Just right (indexes, EXPLAIN, query rewriting)

### Step 2: Research and Outline

**Gather information**:
- Official documentation
- Best practices articles
- Common patterns from experience
- Anti-patterns and gotchas

**Create outline**:
```markdown
# [Skill Name]

## Core Concepts (2-4 concepts)
- Concept 1: [Mental model]
- Concept 2: [Key principle]

## Patterns (4-8 patterns)
- Pattern 1: [Common use case]
- Pattern 2: [Alternative approach]

## Quick Reference
- Commands/APIs
- Decision matrix

## Anti-Patterns (3-5)
- Common mistake 1
- Common mistake 2

## Related Skills (3-6)
- Skill A (workflow predecessor)
- Skill B (alternative)
- Skill C (next step)
```

### Step 3: Write Content

**Writing guidelines**:
- Use **active voice** ("Configure X" not "X is configured")
- **Code examples** for every pattern
- **Clear comments** in code
- **Real-world context** ("When building REST APIs...")
- **Concrete over abstract** (show don't tell)

**Code example format**:
```typescript
// ❌ Bad: No error handling
async function fetchUser(id: string) {
  const response = await fetch(`/api/users/${id}`);
  return response.json();
}

// ✅ Good: Proper error handling
async function fetchUser(id: string) {
  const response = await fetch(`/api/users/${id}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch user: ${response.status}`);
  }

  return response.json();
}
```

**Balance depth vs brevity**:
- Go deep on **one topic**
- Keep related topics as **references to other skills**
- Aim for **250-400 lines**
- If over 500 lines → split into 2 skills

### Step 4: Test Readability

**Read through and check**:
- [ ] Can I scan this in 2 minutes?
- [ ] Are code examples copy-paste ready?
- [ ] Is Quick Reference section useful?
- [ ] Do headers clearly segment content?
- [ ] Are anti-patterns concrete?
- [ ] Do related skills make sense?

**Readability test**:
- Remove yourself from the skill for 1 day
- Come back and try to use it cold
- Can you find what you need quickly?

### Step 5: Integration with System

**Add to _INDEX.md**:

1. **Add skill to category table**:
```markdown
| `new-skill.md` | Brief description of use case | ~300 |
```

2. **Update category workflow section**:
```markdown
**Common workflows:**
- New workflow: `new-skill.md` → `existing-skill.md`
```

3. **Add to discovery patterns**:
```markdown
**New Category**: Search `new-*.md`, `category-*.md`
```

4. **Create skill combination example** (if workflow-worthy):
```markdown
### New Workflow Name
1. `skill-1.md` - Purpose
2. `new-skill.md` - Purpose
3. `skill-3.md` - Purpose
```

5. **Add to Quick Reference Table**:
```markdown
| New task | new-skill.md, related-skill.md | 1→2 |
```

6. **Update total counts**:
```markdown
**Total Skills**: [new count]

### By Category Breakdown
- [Category]: [new count] skills
```

**Update CLAUDE.md** (Section 9 only):

1. **Update category summary** (if new category):
```markdown
**Advanced Categories** ([new count] skills):
- **New Category** ([count]): Skill 1, Skill 2, Skill 3
```

2. **Update Quick Category Reference**:
```markdown
New Category:   new-*.md ([count]) | category-*.md ([count])
```

3. **Update discovery patterns** (if new pattern):
```markdown
ls skills/new-*.md
ls skills/category/*.md
```

4. **Update total in header**:
```markdown
### Skills Catalog ([new total] Total)
```

**DO NOT**:
- ❌ List individual skills in CLAUDE.md (use summaries)
- ❌ Add more than 10 lines to CLAUDE.md per skill
- ❌ Duplicate content between CLAUDE.md and _INDEX.md
- ❌ Exceed 800 lines in CLAUDE.md

### Step 6: File Organization

**Naming convention**:
- Lowercase with hyphens: `postgres-query-optimization.md`
- Technology prefix: `postgres-*.md`, `react-*.md`
- Pattern: `[tech]-[focus].md`

**Directory structure**:
```
skills/
  api/                    # Category directories for cohesion
    rest-api-design.md
    graphql-schema-design.md
  cicd/
    github-actions-workflows.md
    ci-testing-strategy.md
  database/               # Or flat with prefix
    postgres-query-optimization.md
  postgres-*.md           # Or prefixed files at root
  react-*.md
  skill-creation.md       # Meta skills at root
  _INDEX.md               # Always at root
```

**Category vs flat**:
- Use **category directories** for 4+ related skills
- Use **prefix pattern** for 2-3 related skills
- Keep **meta/workflow skills** at root (beads-*, skill-creation)

---

## Integration Checklist

Before considering a skill "complete":

**Skill file itself**:
- [ ] Title matches filename
- [ ] Scope is one clear line
- [ ] Line count is accurate (~actual count)
- [ ] "When to Use This Skill" has 5+ triggers
- [ ] Core Concepts section (2-4 concepts)
- [ ] Patterns section with code examples (4-8 patterns)
- [ ] Quick Reference section (tables/commands)
- [ ] Anti-Patterns section (3-5 patterns)
- [ ] Related Skills section (3-6 skills)
- [ ] Last Updated date is current
- [ ] Format Version is specified
- [ ] Total lines: 250-400 (max 500)

**_INDEX.md updates**:
- [ ] Added to category table with description
- [ ] Updated category workflow section
- [ ] Added to discovery patterns (if new pattern)
- [ ] Created skill combination example (if applicable)
- [ ] Added to Quick Reference Table (if common task)
- [ ] Updated total skills count
- [ ] Updated category breakdown counts

**CLAUDE.md updates** (Section 9 only):
- [ ] Updated category summary with new count
- [ ] Updated Quick Category Reference (if needed)
- [ ] Updated discovery patterns (if new pattern)
- [ ] Updated total skills count in header
- [ ] Verified CLAUDE.md still under 800 lines
- [ ] No individual skill descriptions added (summaries only)

**Testing**:
- [ ] Skill is discoverable via pattern search
- [ ] Skill is scannable (can read in 2-3 minutes)
- [ ] Code examples are copy-paste ready
- [ ] Related skills references are accurate
- [ ] Skill fits into documented workflows

---

## Best Practices

### Writing Style

**Be concise**:
```markdown
❌ "When you are working on implementing authentication and authorization
    for your API endpoints, you should consider using this skill."

✅ "Implementing API authentication and authorization"
```

**Be specific**:
```markdown
❌ "This helps with databases"
✅ "Optimizing slow Postgres queries with EXPLAIN plans and indexes"
```

**Use examples**:
```markdown
❌ "Configure your settings appropriately"
✅
```typescript
// Configure connection pool
const pool = new Pool({
  max: 20,              // Maximum connections
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000,
});
```
```

### Code Examples

**Format consistently**:
- Language identifier in code fence
- Comments explaining key lines
- Real-world variable names (not foo/bar)
- Show both bad ❌ and good ✅ patterns
- Keep examples under 30 lines

**Bad example**:
```javascript
// No context, unclear purpose
function process(x) {
  return x.map(y => y * 2);
}
```

**Good example**:
```typescript
// Transform user data for API response
interface User {
  id: string;
  email: string;
  password: string; // Never send to client
}

function sanitizeUser(user: User) {
  const { password, ...safeUser } = user;
  return safeUser; // Only id and email
}
```

### Organization

**Front-load important info**:
1. "When to Use This Skill" - Helps discovery
2. "Core Concepts" - Mental models first
3. "Patterns" - Practical examples
4. "Quick Reference" - Emergency lookup
5. "Anti-Patterns" - Learn from mistakes
6. "Related Skills" - Next steps

**Use visual hierarchy**:
- `#` for skill title
- `##` for major sections
- `###` for sub-sections
- `**Bold**` for emphasis
- `` `code` `` for commands/filenames
- Horizontal rules `---` between major sections

### Maintenance

**Keep skills current**:
- Update "Last Updated" date when changing content
- Review annually for outdated patterns
- Add new patterns as they emerge
- Archive deprecated patterns to Anti-Patterns

**Version control**:
- Commit skills to git
- Use descriptive commit messages
- Tag major skill system versions
- Track CLAUDE.md changes separately

---

## Common Patterns

### Pattern 1: Create Category Skill Set

**Scenario**: Adding 5 skills for new technology (Kubernetes)

**Steps**:
1. Create directory: `mkdir skills/kubernetes/`
2. Create 5 skills with consistent naming:
   - `kubernetes-basics.md`
   - `kubernetes-deployments.md`
   - `kubernetes-services.md`
   - `kubernetes-security.md`
   - `kubernetes-troubleshooting.md`
3. Add category to _INDEX.md with table
4. Update CLAUDE.md Section 9 with category summary
5. Add discovery pattern: `ls skills/kubernetes/*.md`

### Pattern 2: Split Monolithic Skill

**Scenario**: Existing skill too large (800 lines)

**Steps**:
1. Identify 2-3 distinct sub-topics
2. Create separate skills for each
3. Extract content to new files
4. Update Related Skills to cross-reference
5. Archive old monolithic skill to `_archive/`
6. Update _INDEX.md and CLAUDE.md

**Example**:
- Before: `database-complete.md` (800 lines)
- After: `postgres-query-optimization.md`, `postgres-migrations.md`, `postgres-schema-design.md`

### Pattern 3: Add Skill to Existing Category

**Scenario**: One new skill for existing category

**Steps**:
1. Create skill file in category directory or with prefix
2. Add row to _INDEX.md category table
3. Update category workflow section if needed
4. Increment count in CLAUDE.md category summary
5. Update total counts in both files

---

## Anti-Patterns

❌ **Monolithic skills**: 1000+ line skills covering entire domains
✅ Split into 3-5 atomic skills (250-400 lines each)

❌ **Listing all skills in CLAUDE.md**: Bloats the main config
✅ Use category summaries and Quick Category Reference

❌ **No discovery patterns**: Skills hard to find
✅ Consistent naming, category directories, _INDEX.md search patterns

❌ **Copy-paste from docs**: Raw documentation dumps
✅ Curated patterns, real-world examples, opinionated best practices

❌ **Missing code examples**: Abstract explanations only
✅ Every pattern has code example with comments

❌ **No Related Skills**: Skills exist in isolation
✅ Link 3-6 related skills for composability

❌ **Inconsistent structure**: Each skill different format
✅ Follow template structure (When/Core/Patterns/Quick/Anti/Related)

❌ **Stale content**: Skills never updated
✅ Review and update annually, track "Last Updated" date

---

## Quick Reference

### New Skill Checklist

```
1. Define scope (one-line description, 5 triggers)
2. Research content (docs, best practices)
3. Create outline (Core/Patterns/Quick/Anti/Related)
4. Write content (250-400 lines, code examples)
5. Test readability (scan in 2 minutes)
6. Add to _INDEX.md (table, workflows, patterns)
7. Update CLAUDE.md Section 9 (summary, counts)
8. Verify CLAUDE.md still < 800 lines
9. Commit to git
```

### File Structure Quick Copy

```markdown
# Skill Name

**Scope**: One-line description
**Lines**: ~300
**Last Updated**: 2025-10-18

## When to Use This Skill

- Trigger 1
- Trigger 2

## Core Concepts

### Concept 1

## Patterns

### Pattern 1

## Quick Reference

## Anti-Patterns

## Related Skills

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
```

### CLAUDE.md Impact Budget

```
Adding 1 skill to existing category:
  _INDEX.md: +1 line (table row)
  CLAUDE.md: +0 lines (increment count in summary)

Adding new category (5 skills):
  _INDEX.md: +40 lines (section with table)
  CLAUDE.md: +2 lines (category summary + quick ref)

Current budget:
  CLAUDE.md: 678/800 lines (122 lines remaining)
  Can add ~60 skills before hitting limit (at current efficiency)
```

---

## Related Skills

- `beads-workflow.md` - Managing skill creation as tracked work
- `beads-context-strategies.md` - Managing context during large skill creation
- `frontend/nextjs-seo.md` - Example of well-structured atomic skill
- `testing/performance-testing.md` - Example of comprehensive patterns section
- `database/postgres-query-optimization.md` - Example of code-heavy skill

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
