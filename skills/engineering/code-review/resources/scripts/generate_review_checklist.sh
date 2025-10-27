#!/usr/bin/env bash
#
# Generate custom review checklists based on PR type and language.
#
# Usage:
#   ./generate_review_checklist.sh --type feature --lang python
#   ./generate_review_checklist.sh --type bugfix --lang typescript
#   ./generate_review_checklist.sh --type security --lang rust
#   ./generate_review_checklist.sh --help

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
PR_TYPE="feature"
LANGUAGE="python"
OUTPUT_FORMAT="markdown"
OUTPUT_FILE=""

# Usage information
usage() {
    cat << EOF
Generate custom code review checklists

Usage: $0 [OPTIONS]

Options:
    -t, --type TYPE         PR type: feature, bugfix, security, refactor, docs (default: feature)
    -l, --lang LANG         Language: python, javascript, typescript, rust, go (default: python)
    -f, --format FORMAT     Output format: markdown, json (default: markdown)
    -o, --output FILE       Output file (default: stdout)
    -h, --help              Show this help message

Examples:
    $0 --type feature --lang python
    $0 --type security --lang typescript --output security-checklist.md
    $0 --type bugfix --lang rust --format json

Environment Variables:
    PR_NUMBER              If set, includes PR number in checklist
    PR_TITLE               If set, includes PR title in checklist
EOF
    exit 0
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--type)
            PR_TYPE="$2"
            shift 2
            ;;
        -l|--lang)
            LANGUAGE="$2"
            shift 2
            ;;
        -f|--format)
            OUTPUT_FORMAT="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo -e "${RED}Error: Unknown option $1${NC}" >&2
            usage
            ;;
    esac
done

# Validate inputs
if [[ ! "$PR_TYPE" =~ ^(feature|bugfix|security|refactor|docs)$ ]]; then
    echo -e "${RED}Error: Invalid PR type '$PR_TYPE'${NC}" >&2
    exit 1
fi

if [[ ! "$LANGUAGE" =~ ^(python|javascript|typescript|rust|go)$ ]]; then
    echo -e "${RED}Error: Invalid language '$LANGUAGE'${NC}" >&2
    exit 1
fi

if [[ ! "$OUTPUT_FORMAT" =~ ^(markdown|json)$ ]]; then
    echo -e "${RED}Error: Invalid format '$OUTPUT_FORMAT'${NC}" >&2
    exit 1
fi

# Generate checklist based on type and language
generate_checklist() {
    local type="$1"
    local lang="$2"
    local format="$3"

    if [[ "$format" == "markdown" ]]; then
        generate_markdown_checklist "$type" "$lang"
    else
        generate_json_checklist "$type" "$lang"
    fi
}

# Generate markdown checklist
generate_markdown_checklist() {
    local type="$1"
    local lang="$2"

    cat << EOF
# Code Review Checklist

**Type:** $type
**Language:** $lang
**Date:** $(date -u +"%Y-%m-%d %H:%M:%S UTC")
EOF

    if [[ -n "${PR_NUMBER:-}" ]]; then
        echo "**PR:** #$PR_NUMBER"
    fi

    if [[ -n "${PR_TITLE:-}" ]]; then
        echo "**Title:** $PR_TITLE"
    fi

    cat << 'EOF'

---

## General Review

### Design
- [ ] Change improves overall code health
- [ ] Appropriate level of abstraction
- [ ] Follows existing patterns and architecture
- [ ] No unnecessary complexity
- [ ] Future-proof and extensible

### Functionality
- [ ] Code does what author intended
- [ ] Edge cases handled appropriately
- [ ] Error handling is correct
- [ ] Resource management is proper (files, connections, memory)
- [ ] No obvious bugs or logic errors

### Naming & Clarity
- [ ] Variables, functions, classes have descriptive names
- [ ] Code is self-documenting
- [ ] Complex logic has explanatory comments
- [ ] No misleading names or abbreviations

### Tests
- [ ] New functionality has tests
- [ ] Tests are correct and meaningful
- [ ] Tests cover edge cases
- [ ] All tests pass
- [ ] Test names clearly describe what they test

### Documentation
- [ ] Public APIs have documentation
- [ ] README updated if needed
- [ ] Breaking changes documented
- [ ] Migration guide provided if needed

EOF

    # Type-specific checks
    case "$type" in
        feature)
            cat << 'EOF'
## Feature-Specific Checks

- [ ] Feature matches requirements/spec
- [ ] User experience is intuitive
- [ ] Feature is discoverable
- [ ] Performance is acceptable
- [ ] Feature flags implemented if needed
- [ ] Backwards compatible or migration provided
- [ ] Analytics/logging added for feature usage
- [ ] Feature can be rolled back if issues arise

EOF
            ;;
        bugfix)
            cat << 'EOF'
## Bugfix-Specific Checks

- [ ] Root cause identified and documented
- [ ] Fix addresses root cause, not just symptom
- [ ] Test added that reproduces the bug
- [ ] Test fails without the fix, passes with it
- [ ] Similar bugs checked elsewhere in codebase
- [ ] Regression prevented (won't break again)
- [ ] Fix doesn't introduce new bugs
- [ ] Related issues/tickets referenced

EOF
            ;;
        security)
            cat << 'EOF'
## Security-Specific Checks

### Authentication & Authorization
- [ ] All endpoints require authentication
- [ ] Authorization checks on every privileged operation
- [ ] No IDOR vulnerabilities (user can only access own data)
- [ ] Session management is secure

### Input Validation
- [ ] All user input validated (type, length, format)
- [ ] SQL queries use parameterization
- [ ] File uploads restricted (type, size, content)
- [ ] URLs validated before redirects
- [ ] No injection vulnerabilities (SQL, XSS, command, etc.)

### Data Protection
- [ ] Sensitive data encrypted at rest and in transit
- [ ] No secrets hardcoded (use environment variables)
- [ ] PII handled according to privacy requirements
- [ ] Logs don't contain sensitive information

### Dependencies
- [ ] All dependencies up-to-date
- [ ] No known vulnerabilities in dependencies
- [ ] Dependency versions pinned

EOF
            ;;
        refactor)
            cat << 'EOF'
## Refactor-Specific Checks

- [ ] Refactoring has clear goal/benefit
- [ ] Functionality preserved (no behavior changes)
- [ ] All existing tests pass
- [ ] No new bugs introduced
- [ ] Code is simpler after refactoring
- [ ] Performance not degraded
- [ ] Backwards compatible or migration provided
- [ ] Commit history is clear (can be reviewed incrementally)

EOF
            ;;
        docs)
            cat << 'EOF'
## Documentation-Specific Checks

- [ ] Information is accurate and up-to-date
- [ ] Examples work correctly
- [ ] Code samples follow best practices
- [ ] Links are valid
- [ ] Grammar and spelling correct
- [ ] Formatting is consistent
- [ ] Target audience appropriate
- [ ] Search keywords included

EOF
            ;;
    esac

    # Language-specific checks
    case "$lang" in
        python)
            cat << 'EOF'
## Python-Specific Checks

### Code Quality
- [ ] Follows PEP 8 style guide
- [ ] Type hints used for public APIs
- [ ] Docstrings for modules, classes, functions
- [ ] No unused imports
- [ ] List/dict comprehensions used appropriately

### Best Practices
- [ ] Context managers for resource management (`with` statements)
- [ ] Exceptions used properly (not bare `except:`)
- [ ] No mutable default arguments
- [ ] F-strings used for formatting (Python 3.6+)
- [ ] Generators used for large sequences

### Testing
- [ ] pytest used for tests
- [ ] Fixtures used appropriately
- [ ] Mocks/patches used correctly
- [ ] Test coverage >70%

### Dependencies
- [ ] Requirements.txt or pyproject.toml updated
- [ ] Virtual environment used
- [ ] Python version specified

### Linting
- [ ] `ruff check` passes
- [ ] `mypy` passes (if using type hints)
- [ ] `bandit` security check passes

EOF
            ;;
        javascript|typescript)
            cat << 'EOF'
## JavaScript/TypeScript-Specific Checks

### Code Quality
- [ ] ESLint rules pass
- [ ] Prettier formatting applied
- [ ] No console.log statements
- [ ] No commented-out code
- [ ] Destructuring used appropriately

### Best Practices
- [ ] Const/let used (no var)
- [ ] Arrow functions used appropriately
- [ ] Async/await over callbacks
- [ ] Error handling for promises
- [ ] No unused variables

### TypeScript Specific
- [ ] No `any` types (use unknown or proper types)
- [ ] Interfaces defined for data structures
- [ ] Strict mode enabled
- [ ] Type guards used where needed
- [ ] Generic types used appropriately

### Testing
- [ ] Jest tests written
- [ ] Tests don't rely on timing
- [ ] Mocks used appropriately
- [ ] Test coverage >70%

### Dependencies
- [ ] package.json updated
- [ ] package-lock.json committed
- [ ] No security vulnerabilities (`npm audit`)

EOF
            ;;
        rust)
            cat << 'EOF'
## Rust-Specific Checks

### Code Quality
- [ ] `cargo fmt` applied
- [ ] `cargo clippy` warnings addressed
- [ ] No compiler warnings
- [ ] Documentation comments for public APIs
- [ ] Examples in doc comments work

### Best Practices
- [ ] Error handling uses Result/Option
- [ ] Ownership and borrowing correct
- [ ] Lifetimes specified where needed
- [ ] No unsafe code (or justified with comments)
- [ ] Zero-cost abstractions used appropriately

### Testing
- [ ] Unit tests in same file as code
- [ ] Integration tests in tests/ directory
- [ ] Doc tests for examples
- [ ] Tests use appropriate assertions

### Performance
- [ ] Allocations minimized
- [ ] Cloning avoided where possible
- [ ] Iterators preferred over loops
- [ ] Release build tested

### Dependencies
- [ ] Cargo.toml updated
- [ ] Cargo.lock committed
- [ ] Dependency versions appropriate
- [ ] Features used to minimize dependencies

EOF
            ;;
        go)
            cat << 'EOF'
## Go-Specific Checks

### Code Quality
- [ ] `gofmt` applied
- [ ] `go vet` passes
- [ ] `golangci-lint` passes
- [ ] Comments for exported functions/types
- [ ] Package documentation exists

### Best Practices
- [ ] Error handling explicit (no `_` without reason)
- [ ] Interfaces small and focused
- [ ] Goroutines have clear lifecycle
- [ ] Channels used safely (no deadlocks)
- [ ] Context used for cancellation

### Testing
- [ ] Table-driven tests used
- [ ] Test names descriptive
- [ ] Test coverage >70%
- [ ] Benchmarks for performance-critical code

### Concurrency
- [ ] Race detector passes (`go test -race`)
- [ ] No data races
- [ ] Mutexes used correctly
- [ ] WaitGroups used for goroutine sync

### Dependencies
- [ ] go.mod updated
- [ ] go.sum committed
- [ ] Minimal dependencies
- [ ] Replace directives justified

EOF
            ;;
    esac

    cat << 'EOF'
## Performance

- [ ] No N+1 queries
- [ ] Appropriate database indexes
- [ ] Caching used where beneficial
- [ ] Large datasets paginated or streamed
- [ ] Algorithms are efficient (not O(n²) when O(n log n) possible)

## Security

- [ ] Input validation on all user data
- [ ] Output escaped/sanitized
- [ ] Authentication/authorization checked
- [ ] No secrets in code or logs
- [ ] Dependencies have no known vulnerabilities

## Maintainability

- [ ] Code follows team style guide
- [ ] No code duplication
- [ ] Functions are small and focused (<50 lines)
- [ ] Complexity is justified
- [ ] Future developers will understand this

---

## Overall Assessment

**Status:** ⚪ Not Started / 🟡 In Review / 🟢 Approved / 🔴 Changes Requested

**Summary:**
<!-- Overall assessment of the PR -->

**Positive Aspects:**
<!-- What was done well -->

**Areas for Improvement:**
<!-- What could be better -->

**Action Items:**
<!-- Specific changes needed before approval -->

**Reviewer:** <!-- Your name -->
**Date:** <!-- Review date -->

EOF
}

# Generate JSON checklist
generate_json_checklist() {
    local type="$1"
    local lang="$2"

    cat << EOF
{
  "metadata": {
    "type": "$type",
    "language": "$lang",
    "generated_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "pr_number": "${PR_NUMBER:-}",
    "pr_title": "${PR_TITLE:-}"
  },
  "checklist": {
    "general": [
      {"id": "design-1", "text": "Change improves overall code health", "checked": false},
      {"id": "design-2", "text": "Appropriate level of abstraction", "checked": false},
      {"id": "design-3", "text": "Follows existing patterns and architecture", "checked": false},
      {"id": "functionality-1", "text": "Code does what author intended", "checked": false},
      {"id": "functionality-2", "text": "Edge cases handled appropriately", "checked": false},
      {"id": "tests-1", "text": "New functionality has tests", "checked": false},
      {"id": "tests-2", "text": "All tests pass", "checked": false}
    ],
EOF

    case "$type" in
        feature)
            cat << 'EOF'
    "feature_specific": [
      {"id": "feature-1", "text": "Feature matches requirements/spec", "checked": false},
      {"id": "feature-2", "text": "User experience is intuitive", "checked": false},
      {"id": "feature-3", "text": "Performance is acceptable", "checked": false},
      {"id": "feature-4", "text": "Backwards compatible or migration provided", "checked": false}
    ],
EOF
            ;;
        bugfix)
            cat << 'EOF'
    "bugfix_specific": [
      {"id": "bugfix-1", "text": "Root cause identified and documented", "checked": false},
      {"id": "bugfix-2", "text": "Fix addresses root cause, not just symptom", "checked": false},
      {"id": "bugfix-3", "text": "Test added that reproduces the bug", "checked": false},
      {"id": "bugfix-4", "text": "Fix doesn't introduce new bugs", "checked": false}
    ],
EOF
            ;;
        security)
            cat << 'EOF'
    "security_specific": [
      {"id": "security-1", "text": "All endpoints require authentication", "checked": false},
      {"id": "security-2", "text": "All user input validated", "checked": false},
      {"id": "security-3", "text": "No secrets hardcoded", "checked": false},
      {"id": "security-4", "text": "No known vulnerabilities in dependencies", "checked": false}
    ],
EOF
            ;;
        refactor)
            cat << 'EOF'
    "refactor_specific": [
      {"id": "refactor-1", "text": "Refactoring has clear goal/benefit", "checked": false},
      {"id": "refactor-2", "text": "Functionality preserved", "checked": false},
      {"id": "refactor-3", "text": "All existing tests pass", "checked": false},
      {"id": "refactor-4", "text": "Code is simpler after refactoring", "checked": false}
    ],
EOF
            ;;
        docs)
            cat << 'EOF'
    "docs_specific": [
      {"id": "docs-1", "text": "Information is accurate and up-to-date", "checked": false},
      {"id": "docs-2", "text": "Examples work correctly", "checked": false},
      {"id": "docs-3", "text": "Links are valid", "checked": false},
      {"id": "docs-4", "text": "Grammar and spelling correct", "checked": false}
    ],
EOF
            ;;
    esac

    case "$lang" in
        python)
            cat << 'EOF'
    "language_specific": [
      {"id": "python-1", "text": "Follows PEP 8 style guide", "checked": false},
      {"id": "python-2", "text": "Type hints used for public APIs", "checked": false},
      {"id": "python-3", "text": "ruff check passes", "checked": false},
      {"id": "python-4", "text": "mypy passes", "checked": false}
    ]
EOF
            ;;
        javascript|typescript)
            cat << 'EOF'
    "language_specific": [
      {"id": "js-1", "text": "ESLint rules pass", "checked": false},
      {"id": "js-2", "text": "Prettier formatting applied", "checked": false},
      {"id": "js-3", "text": "No console.log statements", "checked": false},
      {"id": "js-4", "text": "npm audit passes", "checked": false}
    ]
EOF
            ;;
        rust)
            cat << 'EOF'
    "language_specific": [
      {"id": "rust-1", "text": "cargo fmt applied", "checked": false},
      {"id": "rust-2", "text": "cargo clippy passes", "checked": false},
      {"id": "rust-3", "text": "No compiler warnings", "checked": false},
      {"id": "rust-4", "text": "Error handling uses Result/Option", "checked": false}
    ]
EOF
            ;;
        go)
            cat << 'EOF'
    "language_specific": [
      {"id": "go-1", "text": "gofmt applied", "checked": false},
      {"id": "go-2", "text": "go vet passes", "checked": false},
      {"id": "go-3", "text": "golangci-lint passes", "checked": false},
      {"id": "go-4", "text": "Race detector passes", "checked": false}
    ]
EOF
            ;;
    esac

    cat << 'EOF'
  },
  "assessment": {
    "status": "not_started",
    "summary": "",
    "positive_aspects": [],
    "areas_for_improvement": [],
    "action_items": [],
    "reviewer": "",
    "review_date": ""
  }
}
EOF
}

# Main execution
main() {
    local output
    output=$(generate_checklist "$PR_TYPE" "$LANGUAGE" "$OUTPUT_FORMAT")

    if [[ -n "$OUTPUT_FILE" ]]; then
        echo "$output" > "$OUTPUT_FILE"
        echo -e "${GREEN}Checklist generated: $OUTPUT_FILE${NC}" >&2
    else
        echo "$output"
    fi
}

main
