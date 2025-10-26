---
name: product-prd-user-stories-acceptance
description: Writing effective user stories, epics, acceptance criteria, and story mapping for product requirements
---

# PRD User Stories & Acceptance Criteria

**Scope**: Techniques for writing epics, user stories, acceptance criteria, story mapping, and edge case coverage
**Lines**: ~300
**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Breaking down features into user stories for development
- Writing acceptance criteria that engineering can test against
- Creating epics to organize large features or initiatives
- Story mapping user journeys to identify gaps
- Estimating story complexity with engineering teams
- Defining edge cases and error scenarios
- Ensuring user stories meet INVEST criteria (Independent, Negotiable, Valuable, Estimable, Small, Testable)
- Translating PRD requirements into actionable development tasks

## Core Concepts

### Concept 1: Epic, Story, Task Hierarchy

**Epic**: Large feature or initiative spanning multiple sprints
- Example: "User Authentication System"
- Typically 3-10 user stories
- Represents major capability or workflow

**User Story**: Single piece of functionality from user perspective
- Example: "As a new user, I want to sign up with email so I can create an account"
- Completable in one sprint (typically 1-5 days)
- Follows "As a [user], I want [capability], so that [benefit]" format

**Task**: Technical implementation step (engineering breaks stories into tasks)
- Example: "Create signup API endpoint", "Design signup form UI"
- Completable in hours to 1 day
- Implementation detail, not user-facing

### Concept 2: INVEST Criteria for User Stories

**Independent**: Story can be developed without dependencies on other stories
**Negotiable**: Details can be discussed and refined during development
**Valuable**: Delivers clear value to user or business
**Estimable**: Engineering can estimate effort required
**Small**: Fits within one sprint (typically <5 days)
**Testable**: Has clear pass/fail acceptance criteria

### Concept 3: Acceptance Criteria Formats

**GIVEN-WHEN-THEN** (Behavior-Driven Development):
- GIVEN [context/precondition]
- WHEN [action occurs]
- THEN [expected outcome]

**Checklist Format**:
- [ ] Requirement 1 met
- [ ] Requirement 2 met
- [ ] Edge case handled

**Scenario-Based**:
- Scenario 1: [Description] → [Expected result]
- Scenario 2: [Description] → [Expected result]

---

## Patterns

### Pattern 1: Epic Template

**When to use**:
- Organizing large features spanning multiple stories
- Planning multi-sprint initiatives

```markdown
# Epic: User Authentication System

## Epic Goal
Enable users to securely create accounts, log in, and manage their credentials.

## User Segments
- New users (signing up for first time)
- Returning users (logging in)
- Users who forgot password

## Success Metrics
- 90% of signups complete within 2 minutes
- <1% failed login rate due to technical issues
- Password reset flow completion rate >80%

## User Stories (7 total)
1. ✅ Sign up with email and password
2. ✅ Verify email address
3. 🔄 Log in with email and password
4. ⏳ Reset forgotten password
5. ⏳ Enable two-factor authentication
6. ⏳ Update password from settings
7. ⏳ Log out and clear session

## Out of Scope
- Social login (Google, GitHub) - defer to Q2
- Biometric authentication - future consideration
- Single Sign-On (SSO) - enterprise feature, separate epic

## Dependencies
- Email service provider integration (SendGrid)
- Security review for password hashing approach
```

### Pattern 2: User Story Template (Standard)

**Use case**: Writing clear, testable user stories

```markdown
## User Story: Sign Up with Email

**As a** new user
**I want** to create an account using my email and password
**So that** I can access personalized features and save my data

### Acceptance Criteria

**GIVEN** I am on the signup page
**WHEN** I enter a valid email, password (8+ chars, 1 number, 1 symbol), and confirm password
**THEN** the system creates my account and sends a verification email

**GIVEN** I am on the signup page
**WHEN** I enter an email that's already registered
**THEN** I see an error message "Email already in use. Try logging in."

**GIVEN** I am on the signup page
**WHEN** I enter a password that doesn't meet requirements
**THEN** I see real-time validation feedback (e.g., "Password must include a number")

**GIVEN** I successfully signed up
**WHEN** I check my email inbox
**THEN** I receive a verification email within 1 minute with a working verification link

### Edge Cases
- Email with special characters (e.g., user+tag@example.com) - should work
- Very long email (>100 chars) - should validate and accept up to 254 chars
- Network failure during signup - should show error, allow retry
- Duplicate submission (double-click signup button) - should prevent duplicate accounts

### Out of Scope (This Story)
- Password strength meter (separate story)
- Social login options (deferred)
- CAPTCHA for bot prevention (if spam becomes issue)

### Estimation
- Story Points: 3
- Confidence: High
```

### Pattern 3: Acceptance Criteria - Checklist Format

**Use case**: Simple features with clear requirements

```markdown
## User Story: Export Data as CSV

**As a** data analyst
**I want** to export my dashboard data as a CSV file
**So that** I can analyze it in Excel or other tools

### Acceptance Criteria
- [ ] "Export CSV" button is visible on dashboard
- [ ] Clicking button downloads a CSV file with correct filename (e.g., "dashboard-data-2025-10-25.csv")
- [ ] CSV includes all visible data rows (respects current filters)
- [ ] CSV columns match dashboard column headers
- [ ] Date fields are formatted as YYYY-MM-DD
- [ ] Numbers include proper decimal separators (based on user locale)
- [ ] Export completes in <5 seconds for up to 10,000 rows
- [ ] User sees loading indicator during export
- [ ] Error message shown if export fails (e.g., network issue)

### Test Cases
1. Happy path: 100 rows, all filters off → CSV downloads correctly
2. Large dataset: 10,000 rows → completes in <5 seconds
3. Filtered data: Date filter applied → CSV only includes filtered rows
4. Empty data: No rows to export → Show "No data to export" message
5. Network failure: API error → Show error message, allow retry
```

### Pattern 4: Scenario-Based Acceptance Criteria

**Use case**: Complex workflows with multiple paths

```markdown
## User Story: Password Reset Flow

**As a** user who forgot my password
**I want** to reset it via email link
**So that** I can regain access to my account

### Acceptance Criteria

**Scenario 1: Successful Password Reset**
- User navigates to "Forgot Password" page
- User enters registered email address
- System sends reset email within 1 minute
- User clicks reset link in email (valid for 24 hours)
- User enters new password (meets requirements)
- System updates password and logs user in
- Old password no longer works

**Scenario 2: Unregistered Email**
- User enters email not in system
- System shows generic message: "If email exists, reset link sent" (security)
- No email is actually sent
- Prevents email enumeration attacks

**Scenario 3: Expired Reset Link**
- User receives reset email
- User clicks link after 24 hours
- System shows "Reset link expired. Request a new one."
- User can request new reset link

**Scenario 4: Reused Reset Link**
- User requests reset link
- User successfully resets password
- User tries to use same link again
- System shows "Reset link already used. Request a new one."

**Scenario 5: Password Requirements Not Met**
- User clicks reset link
- User enters password without number/symbol
- System shows real-time validation errors
- User cannot submit until requirements met
```

### Pattern 5: Story Mapping for User Journeys

**Use case**: Organizing stories by user workflow to identify gaps

```markdown
## Story Map: User Onboarding Journey

### Backbone (Major Activities)
1. Discover Product
2. Sign Up
3. Complete Profile
4. First Use
5. Become Active User

### User Stories (organized by activity)

**1. Discover Product**
- View marketing homepage
- Watch product demo video
- Read case studies

**2. Sign Up** ⭐ MVP PRIORITY
- Create account with email
- Verify email address
- Accept terms of service

**3. Complete Profile**
- Add profile photo
- Set display name
- Configure preferences

**4. First Use** ⭐ MVP PRIORITY
- See onboarding tutorial
- Complete first task (e.g., create project)
- Invite team member (optional)

**5. Become Active User**
- Use product 3 days in a row (habit formation)
- Complete 10 tasks (engagement milestone)
- Upgrade to paid plan (conversion)

### MVP Slice (Walking Skeleton)
- Create account with email ✅
- Verify email address ✅
- See onboarding tutorial ✅
- Complete first task ✅

### Post-MVP Additions
- Profile customization
- Team invitations
- Advanced tutorials
```

### Pattern 6: Story Estimation with T-Shirt Sizing

**Use case**: Quick estimation during backlog grooming

```markdown
## Story Sizing Reference

**XS (1 point)**: ~1-2 hours
- Add a label to a form field
- Change button color
- Update copy on a page

**S (2 points)**: ~half day
- Add a new form field with validation
- Create a simple filter
- Add sorting to a table

**M (3 points)**: ~1 day
- Build a new form with 5-10 fields
- Implement search with filters
- Add CSV export

**L (5 points)**: ~2-3 days
- Create new dashboard page
- Implement authentication flow
- Build API integration with third-party service

**XL (8 points)**: ~1 week
- Design and implement new database schema
- Build real-time notification system
- Create complex data visualization

**TOO BIG (13+ points)**: Break down into smaller stories
- "Build entire user management system" → Split into epics/stories
```

### Pattern 7: Edge Cases and Error Scenarios Checklist

**Use case**: Ensuring comprehensive acceptance criteria

```markdown
## Edge Cases Checklist for User Stories

### Input Validation
- [ ] Empty input (required fields)
- [ ] Extremely long input (>1000 chars)
- [ ] Special characters (unicode, emojis, SQL injection attempts)
- [ ] Input with only whitespace
- [ ] Invalid format (e.g., malformed email)

### State Transitions
- [ ] Action performed twice (idempotency)
- [ ] Action performed by two users simultaneously (concurrency)
- [ ] User navigates away mid-process
- [ ] User hits back button
- [ ] Session expires during action

### Network and Performance
- [ ] Network failure mid-request
- [ ] Slow network (<1 Mbps)
- [ ] Request timeout
- [ ] Large payload (>10 MB)
- [ ] API rate limit hit

### Permissions and Access
- [ ] Unauthenticated user attempts action
- [ ] User without proper permissions
- [ ] User accessing another user's data
- [ ] Expired authentication token

### Browser and Device
- [ ] Mobile vs desktop
- [ ] Different browsers (Chrome, Safari, Firefox)
- [ ] Old browser versions (IE11 if required)
- [ ] Screen readers (accessibility)
- [ ] Slow device (older hardware)

### Data States
- [ ] Empty state (no data to display)
- [ ] Single item
- [ ] Thousands of items (pagination needed?)
- [ ] Deleted or archived items
- [ ] Corrupted data
```

### Pattern 8: User Story with Non-Functional Requirements

**Use case**: Including performance, security, accessibility requirements in stories

```markdown
## User Story: Real-Time Dashboard Updates

**As a** operations manager
**I want** dashboard metrics to update in real-time
**So that** I can monitor system health without refreshing

### Functional Acceptance Criteria
- Dashboard connects to WebSocket on page load
- Metrics update within 2 seconds of backend event
- Visual indicator shows connection status (green = connected)
- If connection lost, auto-reconnects within 5 seconds
- User can manually refresh if needed

### Non-Functional Requirements

**Performance (NFR)**:
- [ ] Updates render without blocking UI thread
- [ ] Supports 1,000+ concurrent connections per server
- [ ] Memory usage stays <50MB per client session
- [ ] CPU usage <10% on client during updates

**Security (NFR)**:
- [ ] WebSocket uses WSS (encrypted)
- [ ] Authentication token validated on connection
- [ ] Connection closes after 30 min of inactivity
- [ ] Rate limiting: max 100 messages/sec per client

**Accessibility (NFR)**:
- [ ] Screen reader announces new data updates
- [ ] Updates don't interrupt keyboard navigation
- [ ] Visual updates paired with ARIA live regions
- [ ] Color changes have sufficient contrast (WCAG AA)

**Reliability (NFR)**:
- [ ] Graceful degradation if WebSocket unavailable (poll instead)
- [ ] Exponential backoff for reconnection attempts
- [ ] Circuit breaker after 5 failed reconnections
- [ ] Error tracking/logging for connection failures
```

---

## Quick Reference

### User Story Checklist (INVEST)

```
Criteria | Question to Ask
---------|----------------
Independent | Can this be developed without waiting for other stories?
Negotiable | Are implementation details flexible?
Valuable | Does this deliver user/business value?
Estimable | Can engineering estimate this?
Small | Can this be completed in 1 sprint?
Testable | Are there clear pass/fail criteria?
```

### Acceptance Criteria Format Guide

```
Format | Best For | Example
-------|----------|--------
GIVEN-WHEN-THEN | Behavior-driven, multiple scenarios | Login flow, form validation
Checklist | Simple features, clear requirements | Export CSV, UI changes
Scenario-Based | Complex workflows, branching paths | Password reset, multi-step forms
```

### Story Estimation Quick Guide

```
Size | Effort | Examples
-----|--------|----------
XS (1) | 1-2 hours | Copy changes, style tweaks
S (2) | Half day | New form field, simple filter
M (3) | 1 day | Full form, search feature
L (5) | 2-3 days | Dashboard page, auth flow
XL (8) | 1 week | Complex integration, new schema
```

### Key Guidelines

```
✅ DO: Write from user perspective (not implementation details)
✅ DO: Include edge cases and error scenarios
✅ DO: Make acceptance criteria testable (clear pass/fail)
✅ DO: Keep stories small (completable in one sprint)
✅ DO: Involve engineering in story refinement

❌ DON'T: Write stories as tasks ("Create API endpoint")
❌ DON'T: Prescribe implementation ("Use React hooks")
❌ DON'T: Make stories too large (break epics into stories)
❌ DON'T: Skip non-functional requirements (performance, security)
❌ DON'T: Write vague acceptance criteria ("should work well")
```

---

## Anti-Patterns

### Critical Violations

❌ **Task Disguised as User Story**: Writing implementation tasks instead of user value
```markdown
# ❌ NEVER:
**As a** developer
**I want** to create a REST API endpoint for user data
**So that** the frontend can call it

# ✅ CORRECT:
**As a** dashboard user
**I want** to see my profile information displayed
**So that** I can verify my account details are correct

[Engineering will decide if this needs new API endpoint]
```

❌ **Vague Acceptance Criteria**: "Should be fast" instead of measurable requirements
```markdown
# ❌ Don't:
- Dashboard should load fast
- Form should be easy to use

# ✅ Correct:
- Dashboard loads in <2 seconds on 3G network
- Form has real-time validation with clear error messages
- Form is keyboard-navigable (all fields reachable via Tab)
```

### Common Mistakes

❌ **Epic-Sized Story**: Story too large to complete in one sprint
```markdown
# ❌ Don't:
"As a user, I want a complete user management system"

# ✅ Correct: Break into stories
- Story 1: Create user account with email
- Story 2: Edit user profile
- Story 3: Deactivate user account
- Story 4: List all users (admin)
```

❌ **Missing Edge Cases**: Only happy path in acceptance criteria
```markdown
# ❌ Don't:
GIVEN I enter valid credentials
WHEN I click login
THEN I am logged in

# ✅ Correct: Include error scenarios
- Valid credentials → Login succeeds
- Invalid password → Error message shown
- Account locked (3 failed attempts) → Locked message shown
- Network failure → Error message, retry button
```

❌ **Technical Implementation in User Story**: Dictating how to build it
```markdown
# ❌ Don't:
"As a user, I want the app to use Redis caching so page loads are faster"

# ✅ Correct:
"As a user, I want dashboard to load in <2 seconds so I can quickly check metrics"
[Engineering decides: Redis, in-memory cache, or other solution]
```

---

## Related Skills

- `prd-structure-templates.md` - Document user stories within PRD structure
- `prd-requirements-gathering.md` - Use before this skill to discover what stories are needed
- `prd-technical-specifications.md` - Bridge user stories to technical implementation
- `test-e2e-patterns.md` - Convert acceptance criteria into automated tests
- `engineering/rfc-technical-design.md` - Engineering translates stories into technical designs

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
