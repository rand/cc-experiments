---
name: skill-prompt-discovery
description: User makes a request involving specific technologies or frameworks
---



# Prompt Skill Discovery

**Scope**: Analyzing user prompts/context to identify which existing skills should be activated
**Lines**: ~390
**Last Updated**: 2025-10-18

## When to Use This Skill

Activate this skill when:
- User makes a request involving specific technologies or frameworks
- Context mentions specialized tools, languages, or platforms
- Task requires domain expertise beyond general programming
- Multi-step workflow requires skill composition
- Proactive skill activation during conversation is needed
- Determining which skills to read from _INDEX.md

## Core Concepts

### Intent Analysis

**What is the user trying to accomplish?**
- Extract the primary goal (build, debug, optimize, deploy, learn)
- Identify the outcome they want (working app, fixed bug, faster system)
- Separate explicit requests from implied needs
- Consider context from conversation history

**Types of intent:**
- **Building**: Creating new systems, features, or components
- **Debugging**: Fixing errors, investigating issues, troubleshooting
- **Optimizing**: Improving performance, reducing costs, enhancing quality
- **Deploying**: Shipping to production, CI/CD setup, infrastructure
- **Learning**: Understanding concepts, exploring options, research

### Tech Signal Extraction

**Keywords → Technologies mapping:**
- Look for framework names: "Next.js" → `nextjs-*.md`
- Look for languages: "Zig", "Swift", "Go" → language-specific skills
- Look for platforms: "Modal", "Heroku", "Netlify" → platform skills
- Look for domains: "database", "API", "TUI" → domain skills
- Look for tools: "Docker", "Terraform", "Kubernetes" → tool skills

**Implicit signals:**
- "iOS app" → SwiftUI/Swift skills even if not explicitly mentioned
- "TUI" or "terminal dashboard" → Bubble Tea or Ratatui
- "ML model" → Modal GPU + ML skills
- "REST API" → API design + auth + database skills
- "CI/CD" → GitHub Actions + testing + deployment skills

### Workflow Pattern Matching

**Request → Skill chain:**
- Single-step tasks → 1-2 skills
- Multi-component systems → 3-6 skills in workflow
- Full-stack applications → 6+ skills across layers
- Infrastructure projects → IaC + security + observability chain

**Common patterns:**
```
"Build X" → Architecture skill + Implementation skills + Testing
"Deploy Y" → Containerization + CI/CD + Infrastructure
"Debug Z" → Troubleshooting skill + Domain skills
"Optimize A" → Performance skill + Profiling + Monitoring
```

### Context-Aware Activation

**Conversation history matters:**
- Previous skills activated inform current needs
- Build on existing context (don't re-read same skills)
- Track what the user is working on across turns
- Recognize continuation vs new topic

**Project context signals:**
- Existing files mentioned → Infer tech stack
- Error messages shown → Identify troubleshooting skills
- Commands run → Understand current workflow phase
- Git repo structure → Detect project type

---

## Patterns

### Pattern 1: Technology Keyword Extraction

```python
# Conceptual pattern (not actual code)
def extract_tech_signals(prompt: str) -> list[str]:
    """Extract technology keywords from user prompt"""

    tech_keywords = {
        # Frameworks
        "next.js": ["nextjs-*.md", "react-*.md"],
        "swiftui": ["swiftui-*.md", "swift-*.md", "ios-*.md"],
        "bubble tea": ["bubbletea-*.md", "tui-*.md"],
        "ratatui": ["ratatui-*.md", "tui-*.md"],

        # Languages
        "zig": ["zig-*.md"],
        "swift": ["swift-*.md", "swiftui-*.md", "ios-*.md"],
        "go": ["bubbletea-*.md"] if "tui" in prompt else [],
        "rust": ["ratatui-*.md"] if "tui" in prompt else [],

        # Platforms
        "modal": ["modal-*.md"],
        "heroku": ["heroku-*.md"],
        "netlify": ["netlify-*.md"],
        "aws": ["aws-*.md", "infrastructure/*.md"],

        # Domains
        "database": ["postgres-*.md", "database-*.md"],
        "api": ["api-*.md", "rest-*.md", "graphql-*.md"],
        "testing": ["test-*.md", "unit-*.md", "integration-*.md"],
        "docker": ["docker-*.md", "container-*.md"],
    }

    return [skill for keyword, skills in tech_keywords.items()
            if keyword in prompt.lower() for skill in skills]
```

**When to use:**
- User explicitly mentions technologies
- Prompt contains framework/tool names
- Clear technical domain identified

**Example:**
- Prompt: "Help me build a Next.js app with Postgres"
- Signals: `nextjs-*.md`, `react-*.md`, `postgres-*.md`, `database-*.md`

### Pattern 2: Intent-Based Skill Selection

```
Intent mapping:
├─ "build" / "create" / "start"
│  └─ Architecture + Setup + Testing skills
│
├─ "debug" / "fix" / "error"
│  └─ Troubleshooting + Domain skills
│
├─ "deploy" / "production" / "ship"
│  └─ CI/CD + Infrastructure + Observability
│
├─ "optimize" / "improve" / "speed up"
│  └─ Performance + Profiling + Monitoring
│
└─ "learn" / "understand" / "explain"
   └─ Conceptual skills + Architecture patterns
```

**Example workflows:**

```markdown
# Build intent
"Build a REST API" →
  1. rest-api-design.md (architecture)
  2. api-authentication.md (implementation)
  3. postgres-schema-design.md (data layer)
  4. unit-testing-patterns.md (quality)

# Debug intent
"Debug slow Postgres queries" →
  1. postgres-query-optimization.md (direct solution)
  2. database-connection-pooling.md (if pooling issue)
  3. orm-patterns.md (if ORM N+1 problem)

# Deploy intent
"Deploy to production" →
  1. dockerfile-optimization.md (containerization)
  2. github-actions-workflows.md (CI/CD)
  3. infrastructure-security.md (hardening)
  4. structured-logging.md (observability)
```

### Pattern 3: Multi-Domain Detection

```
Example: "Build ML API on Modal with Postgres"

Domains detected:
1. ML inference → modal-gpu-workloads.md
2. API layer → modal-web-endpoints.md, api-*.md
3. Database → postgres-schema-design.md
4. Cloud platform → modal-functions-basics.md

Skill chain:
  modal-functions-basics.md (foundation)
  → modal-gpu-workloads.md (ML workloads)
  → modal-web-endpoints.md (API endpoints)
  → postgres-schema-design.md (data persistence)
  → api-authentication.md (security)
```

**When to use:**
- Prompt mentions multiple technologies
- Complex system with multiple layers
- Full-stack or end-to-end projects

### Pattern 4: _INDEX.md Quick Reference First

```markdown
# Decision tree for skill discovery

User prompt received
  ↓
Is it a common task? (check _INDEX.md Quick Reference Table)
  ├─ YES: Read listed skills directly
  └─ NO: Continue analysis
      ↓
Identify technology/domain keywords
  ↓
Search _INDEX.md by pattern:
  - By Technology section
  - By Task Type section
  - By Problem Domain section
  ↓
Find category, read relevant skills
  ↓
Check "Common workflows" in category
  ↓
Activate skill chain
```

**Example using _INDEX.md:**

```
Prompt: "Setup Heroku deployment"

Quick Reference lookup:
  | Deploy to Heroku | heroku-deployment.md, heroku-addons.md | 1→2 |

Result: Read heroku-deployment.md, then heroku-addons.md
```

### Pattern 5: Workflow Composition

```
Complex workflow detection:

"Build production-ready iOS app" →
  Layer 1 (Foundation):
    - swiftui-architecture.md
    - swift-concurrency.md

  Layer 2 (Features):
    - ios-networking.md
    - swiftdata-persistence.md
    - swiftui-navigation.md

  Layer 3 (Quality):
    - ios-testing.md
    - web-accessibility.md (if applicable)

Read order: Layer 1 → Layer 2 → Layer 3
```

**Heuristics for composition:**
- 0-2 components → Read 1-3 skills
- 3-5 components → Read 4-7 skills
- 6+ components or "production-ready" → Read 8+ skills across layers

### Pattern 6: Context Continuation

```python
# Track conversation state
class ConversationContext:
    active_skills: set[str] = set()
    tech_stack: set[str] = set()
    current_phase: str = "unknown"  # setup, implementation, debugging, deployment

def should_activate_skill(skill: str, context: ConversationContext) -> bool:
    """Determine if skill should be activated given conversation context"""

    # Don't re-read recently active skills (unless debugging)
    if skill in context.active_skills and context.current_phase != "debugging":
        return False

    # Activate complementary skills based on phase
    if context.current_phase == "deployment":
        return skill in ["ci-*.md", "infrastructure-*.md", "observability-*.md"]

    # Activate based on established tech stack
    if "modal" in context.tech_stack:
        return skill.startswith("modal-")

    return True
```

**Example:**
```
Turn 1: "Start Zig project"
  → Activate: zig-project-setup.md, zig-build-system.md

Turn 2: "Add tests"
  → Activate: zig-testing.md
  → Skip: zig-project-setup.md (already covered)

Turn 3: "Link to C library"
  → Activate: zig-c-interop.md
  → Context: Still working on Zig project
```

---

## Quick Reference

### Technology → Skills Map

```
Technology          | Skill Patterns                              | Count
--------------------|---------------------------------------------|------
Next.js             | nextjs-*.md, react-*.md, frontend-*.md      | 8
SwiftUI/iOS         | swiftui-*.md, swift-*.md, ios-*.md          | 6
Modal.com           | modal-*.md                                  | 8
Zig                 | zig-*.md                                    | 6
Go TUI              | bubbletea-*.md, tui-*.md                    | 3
Rust TUI            | ratatui-*.md, tui-*.md                      | 3
PostgreSQL          | postgres-*.md, database-*.md                | 8
REST API            | rest-api-*.md, api-*.md                     | 7
GraphQL             | graphql-*.md, api-*.md                      | 5
Docker              | docker-*.md, container-*.md                 | 5
Kubernetes          | kubernetes-*.md, infrastructure-*.md        | 6
Heroku              | heroku-*.md                                 | 3
Netlify             | netlify-*.md                                | 3
LLM Fine-tuning     | unsloth-*.md, llm-*.md, lora-*.md          | 4
Diffusion Models    | diffusion-*.md, stable-diffusion-*.md       | 3
React Native        | react-native-*.md, mobile-*.md              | 4
Lean 4              | lean-*.md                                   | 4
Z3 Solver           | z3-*.md, sat-*.md, smt-*.md                | 3
Beads               | beads-*.md                                  | 4
```

### Intent → Skill Priority

```
BUILD new system:
  Priority 1: Architecture/setup skills (swiftui-architecture.md, zig-project-setup.md)
  Priority 2: Implementation skills (domain-specific)
  Priority 3: Testing/quality skills (test-*.md)

DEBUG existing system:
  Priority 1: Troubleshooting skills (*-troubleshooting.md, *-debugging.md)
  Priority 2: Domain skills (postgres-query-optimization.md)
  Priority 3: Observability skills (structured-logging.md)

DEPLOY to production:
  Priority 1: CI/CD skills (github-actions-*.md, cd-*.md)
  Priority 2: Infrastructure skills (terraform-*.md, kubernetes-*.md)
  Priority 3: Observability skills (metrics-*.md, alerting-*.md)

OPTIMIZE performance:
  Priority 1: Performance-specific skills (*-performance-*.md, *-optimization-*.md)
  Priority 2: Profiling/monitoring skills (metrics-*.md)
  Priority 3: Architecture review skills (react-component-patterns.md)

LEARN technology:
  Priority 1: Basics/fundamentals (*-basics.md, *-architecture.md)
  Priority 2: Patterns/best practices (*-patterns.md, tui-best-practices.md)
  Priority 3: Advanced/specialized (*-advanced-*.md)
```

### Decision Matrix

```
Prompt Complexity | Skills to Read | Strategy
------------------|----------------|----------
Simple (1 tech)   | 1-2 skills     | Direct lookup in _INDEX.md Quick Reference
Medium (2-3 tech) | 3-5 skills     | Check "By Technology" section, compose workflow
Complex (4+ tech) | 6-10 skills    | Check "Skill Combination Examples", use workflow chains
Unclear           | 0 skills       | ASK for clarification before reading skills
```

### Common Patterns Quick Lookup

```
✅ DO: Check _INDEX.md Quick Reference Table first
✅ DO: Search by technology pattern (modal-*.md, zig-*.md)
✅ DO: Use "By Task Type" section for common tasks
✅ DO: Reference "Skill Combination Examples" for complex workflows
✅ DO: Compose multiple skills for multi-domain requests

❌ DON'T: Read skills before understanding user intent
❌ DON'T: Read all skills in a category (select relevant ones)
❌ DON'T: Re-read skills already active in conversation
❌ DON'T: Activate skills for technologies not actually used
❌ DON'T: Over-activate (10+ skills) for simple tasks
```

---

## Anti-Patterns

❌ **Reading skills before analyzing intent**: Waste time reading irrelevant skills
✅ Extract intent first, then determine which skills apply

❌ **Activating skills for unrelated technologies**: User says "iOS app", you activate Android skills
✅ Match technology signals precisely (iOS → SwiftUI, not Android)

❌ **Over-activating skills**: Simple "add button to SwiftUI view" → Read all 6 iOS skills
✅ Read only swiftui-architecture.md for component patterns

❌ **Under-activating skills**: "Production Next.js app" → Only read nextjs-app-router.md
✅ Activate frontend performance, SEO, testing, deployment skills too

❌ **Ignoring conversation context**: Re-reading same skill every turn
✅ Track active skills, only re-read if phase changes or debugging

❌ **Not using _INDEX.md**: Searching files manually instead of using Quick Reference
✅ Check _INDEX.md Quick Reference Table for common tasks first

❌ **Missing implicit signals**: "TUI app" → Don't recognize Bubble Tea or Ratatui needed
✅ Map domain keywords to specific implementations (TUI → Bubble Tea/Ratatui)

❌ **Flat skill activation**: Read all skills without considering dependencies
✅ Follow skill workflows (foundation → implementation → quality)

---

## Related Skills

- `skill-prompt-planning.md` - Planning responses and task breakdown after skill activation
- `skill-repo-discovery.md` - Discovering codebase structure to inform skill needs
- `skill-creation.md` - Creating new skills when gaps are discovered
- `beads-workflow.md` - Managing multi-step workflows that require skill composition
- `beads-context-strategies.md` - Preserving skill activation context across sessions

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
