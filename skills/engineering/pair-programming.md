---
name: engineering-pair-programming
description: Pair programming techniques, driver-navigator roles, mob programming, remote pairing tools and best practices
---

# Pair Programming & Mob Programming

**Scope**: Comprehensive guide to pair programming, mob programming, remote pairing, and collaborative coding practices
**Lines**: ~280
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Onboarding new team members
- Solving complex problems
- Sharing knowledge across team
- Establishing coding standards
- Reviewing critical code live
- Learning new technologies
- Breaking through development blockers
- Building team cohesion

## Core Concepts

### Concept 1: Driver-Navigator Pattern

**Driver**: Person typing/coding
- Focus on tactical implementation
- Write code, run tests
- Think about syntax and details

**Navigator**: Person guiding
- Focus on strategic direction
- Think about design and architecture
- Catch errors and suggest improvements

**Switch Roles**: Every 15-25 minutes

```
┌─────────────────────────────────────┐
│ Navigator: "Let's extract this      │
│ validation logic into a function"   │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ Driver: *types function extraction* │
│ "Like this?"                        │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ Navigator: "Yes, but let's make it  │
│ return early on invalid input"      │
└─────────────────────────────────────┘
```

---

### Concept 2: Pairing Styles

**Ping-Pong Pairing** (with TDD):
```
1. Person A: Write failing test
2. Person B: Make test pass
3. Person B: Refactor
4. Person B: Write next failing test
5. Person A: Make test pass
6. Repeat...
```

**Strong-Style Pairing**:
> "For an idea to go from your head to the computer, it must go through someone else's hands"

- Navigator has idea
- Driver implements (doesn't think independently)
- Forces clear communication
- Great for teaching

**Unstructured Pairing**:
- Fluid role switching
- Both contribute equally
- Works well for experienced pairs

---

### Concept 3: Mob Programming

**Definition**: Entire team works on same code at same time

**Setup**:
- One driver, multiple navigators
- Rotate driver every 10-15 minutes
- Large screen visible to all
- Timer for rotations

**Benefits**:
- Maximum knowledge sharing
- Real-time code review
- No handoffs or context switching
- Team alignment

---

## Patterns

### Pattern 1: Effective Pairing Session

**Before Session**:
```markdown
1. Define goal (30 seconds)
   "We're implementing user authentication"

2. Agree on approach (2 minutes)
   "Let's use JWT tokens and bcrypt for passwords"

3. Set time box (1-2 hours)
   "Let's pair until lunch"

4. Choose roles
   "I'll drive first, you navigate"
```

**During Session**:
- Switch roles every 15-25 min
- Take breaks together
- Communicate constantly
- Think out loud

**After Session**:
- Commit and push code
- Reflect on what worked
- Document learnings

---

### Pattern 2: Communication Patterns

**Good Communication**:
```
Navigator: "Let's add error handling for the null case"
Driver: "Good catch. Like this?" *types*
Navigator: "Yes, but we should also log the error"
Driver: "Makes sense" *adds logging*
```

**Bad Communication**:
```
Navigator: "That's wrong"
Driver: "Why?"
Navigator: "Just change it"
Driver: "To what?"
Navigator: *grabs keyboard* "Like this!" ← Anti-pattern!
```

**Best Practices**:
- Be specific: "Let's extract lines 45-50 into a function"
- Ask questions: "What if the user is null?"
- Acknowledge: "Good idea, let's try that"
- Never grab keyboard without permission

---

### Pattern 3: Remote Pairing Setup

**Tools**:
```
Screen Sharing:
- VS Code Live Share (best for coding)
- Tuple (low latency, great for pairing)
- Zoom/Google Meet (screen share + audio)

Code Collaboration:
- VS Code Live Share: Real-time editing
- JetBrains Code With Me: IntelliJ pairing
- tmux: Terminal multiplexing

Communication:
- Discord: Low latency voice
- Slack huddle: Quick screen share
- Tuple: Built-in voice chat
```

**VS Code Live Share Example**:
```bash
# Host starts session
# Share link with pair

# Guest joins
# Both can edit, run terminal, debug

# Benefits:
# - No lag (local editing)
# - Each person uses own setup
# - Shared terminal and debugger
```

---

### Pattern 4: Pairing with Skill Gaps

**Expert + Novice**:
```
Strong-Style Pairing:
- Novice drives (hands on keyboard)
- Expert navigates (teaches)
- Forces expert to explain clearly
- Novice learns by doing

Example:
Expert: "Let's create a new function called validate_email"
Novice: *types function signature*
Expert: "Good, now add a parameter for the email string"
Novice: *adds parameter*
Expert: "What should we check first?"
Novice: "If it contains an @ symbol?"
Expert: "Exactly! Go ahead and write that"
```

**Two Experts**:
```
Unstructured Pairing:
- Fluid role switching
- Both contribute ideas equally
- Quick knowledge exchange
- Focus on hard problems
```

---

### Pattern 5: Mob Programming Session

**Roles**:
- **Driver**: Types code (hands, not brain)
- **Navigator**: Guides driver (thinks strategically)
- **Mob**: Suggests ideas to navigator

**Rotation**:
```
Every 10 minutes:
Driver → Mob (rest)
Navigator → Driver (implement)
Mob member → Navigator (think)
```

**Example Session**:
```
10:00 - Alice drives, Bob navigates, team suggests
10:10 - Bob drives, Carol navigates, team suggests
10:20 - Carol drives, Dave navigates, team suggests
10:30 - Dave drives, Alice navigates, team suggests
10:40 - Break (5 min)
```

---

## Best Practices

### Pairing Etiquette

**Do's**:
- Be present (no phone, no email)
- Communicate constantly
- Think out loud
- Take breaks together
- Switch roles regularly
- Be patient and respectful
- Ask "why" not "what"

**Don'ts**:
- Don't grab keyboard
- Don't work in silence
- Don't dominate session
- Don't check phone/email
- Don't skip breaks
- Don't criticize personally
- Don't pair for 8 hours straight

---

### When to Pair

**Good Times to Pair**:
- Critical features (auth, payments)
- Complex algorithms
- Unfamiliar codebases
- Onboarding new engineers
- Breaking through blockers
- Establishing patterns

**Bad Times to Pair**:
- Trivial tasks (simple bug fixes)
- Routine work (updating docs)
- Deep research (exploring options)
- Individual learning time
- When tired or unfocused

---

### Optimal Pairing Duration

```
Session Length: 1-2 hours
Break: 5-10 minutes
Daily Pairing: 4-6 hours max

Schedule Example:
09:00-10:30: Pair session 1
10:30-10:40: Break
10:40-12:00: Pair session 2
12:00-13:00: Lunch (separate)
13:00-14:30: Pair session 3
14:30-16:00: Solo work

Don't pair 100% of time - solo work is valuable!
```

---

## Anti-Patterns

### Common Pairing Mistakes

```
❌ Watch-the-Master
→ One person codes, other watches silently
✅ Active navigation and communication

❌ Keyboard Hogging
→ Driver refuses to switch
✅ Time-box rotations (15-25 min)

❌ Back-seat Driving
→ Navigator dictates every keystroke
✅ Navigate strategically, not tactically

❌ Pairing 8 Hours Straight
→ Exhausting and ineffective
✅ 4-6 hours max, with breaks

❌ Pairing on Everything
→ Waste time on trivial tasks
✅ Pair on complex, critical work

❌ Silent Pairing
→ No communication, no collaboration
✅ Think out loud, discuss constantly

❌ Unequal Participation
→ One person dominates
✅ Equal time as driver/navigator
```

---

## Remote Pairing Tips

### Making Remote Pairing Effective

**Technical Setup**:
```bash
# High-quality audio crucial
- Use headphones (reduce echo)
- Use quality mic (not laptop mic)
- Test audio before session

# Screen sharing
- Share entire screen (not just window)
- Increase font size (18-20pt)
- Use high-contrast theme
- Hide distracting notifications

# Collaboration tools
- VS Code Live Share: Shared editing
- Shared terminal: Both can type
- Shared debugger: Both can step through
```

**Communication**:
```
# Over-communicate (no body language)
"I'm thinking..." (when silent)
"Let me drive next" (before grabbing control)
"Can you try...?" (instead of just doing it)

# Use video when possible
- See facial expressions
- Read body language
- Build rapport
```

---

## Measuring Success

### Pairing Effectiveness Metrics

**Qualitative**:
- Knowledge shared between team members
- Fewer bugs in production
- Faster onboarding
- Improved code quality
- Team cohesion

**Quantitative**:
- Defect rate (should decrease)
- Code review time (should decrease)
- Time to production (may increase initially)
- Bus factor (should increase)

**Team Surveys**:
```markdown
Weekly Pairing Retrospective:
1. What worked well?
2. What could improve?
3. Did you learn something new?
4. Was pairing time well spent?
5. Would you pair on this task again?
```

---

## Code Example: Pairing Session

**Ping-Pong TDD Session**:
```python
# Person A: Write failing test
def test_calculate_discount_for_vip():
    customer = Customer(type="VIP")
    discount = calculate_discount(customer, purchase_amount=100)
    assert discount == 20  # 20% discount for VIP

# Test fails (function doesn't exist)

# Person B: Make test pass (minimal implementation)
def calculate_discount(customer, purchase_amount):
    if customer.type == "VIP":
        return purchase_amount * 0.20
    return 0

# Test passes!

# Person B: Refactor
def calculate_discount(customer, purchase_amount):
    VIP_DISCOUNT_RATE = 0.20
    if customer.is_vip():  # Better abstraction
        return purchase_amount * VIP_DISCOUNT_RATE
    return 0

# Person B: Write next failing test
def test_calculate_discount_for_regular():
    customer = Customer(type="REGULAR")
    discount = calculate_discount(customer, purchase_amount=100)
    assert discount == 10  # 10% discount for regular

# Test fails (returns 0)

# Person A: Make test pass
def calculate_discount(customer, purchase_amount):
    VIP_DISCOUNT_RATE = 0.20
    REGULAR_DISCOUNT_RATE = 0.10

    if customer.is_vip():
        return purchase_amount * VIP_DISCOUNT_RATE
    return purchase_amount * REGULAR_DISCOUNT_RATE

# Tests pass! Continue...
```

---

## Related Skills

- **engineering-code-review**: Pair programming is live code review
- **engineering-test-driven-development**: Ping-pong pairing with TDD
- **engineering-refactoring-patterns**: Pair on refactoring
- **engineering-domain-driven-design**: Pair to model domain

---

## References

- [Pair Programming Illuminated by Laurie Williams](https://www.amazon.com/Pair-Programming-Illuminated-Laurie-Williams/dp/0201745763)
- [Mob Programming by Woody Zuill](https://www.agilealliance.org/resources/experience-reports/mob-programming-agile2014/)
- [Strong-Style Pairing](https://llewellynfalco.blogspot.com/2014/06/llewellyns-strong-style-pairing.html)
- [Remote Pairing by Joe Moore](https://martinfowler.com/articles/remote-or-co-located.html)
