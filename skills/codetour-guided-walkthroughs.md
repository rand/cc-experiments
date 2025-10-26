---
name: codetour-guided-walkthroughs
description: Creating and following CodeTour walkthroughs for codebase understanding
---

# CodeTour Guided Walkthroughs

**Scope**: Creating interactive code tours and following existing tours for codebase understanding
**Lines**: ~380
**Last Updated**: 2025-10-26
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Onboarding to an unfamiliar codebase
- Creating documentation for complex features or architecture
- Following existing CodeTour walkthroughs for context
- Documenting multi-file workflows or data flows
- Creating guided bug reproduction paths
- Explaining refactoring changes to team members
- Building interactive tutorials for framework usage
- Capturing architectural decisions with code examples

## Core Concepts

### Tour Structure

**Tour File Format**:
- Extension: `.tour` (JSON format)
- Location: `.tours/`, `.vscode/tours/`, `.github/tours/`, or project root
- Schema: Defined by microsoft/codetour specification

**Required Properties**:
```json
{
  "title": "Tour name",
  "steps": [
    {
      "description": "Step explanation (required)"
    }
  ]
}
```

**Optional Properties**:
- `description`: Overall tour description
- `ref`: Git branch/commit/tag reference
- `isPrimary`: Boolean for primary tour flag
- `nextTour`: Title of follow-up tour for chaining

### Step Types

**File-Based Steps**: Navigate to specific code locations
```json
{
  "file": "src/server.ts",
  "line": 42,
  "description": "# Main Server Entry\n\nThis is where the HTTP server starts..."
}
```

**Directory Steps**: Show overall structure
```json
{
  "directory": "src/api/",
  "description": "API handlers are organized by resource type"
}
```

**Content Steps**: Provide context without code
```json
{
  "description": "# Welcome to the API\n\nThis tour covers authentication flow"
}
```

**Pattern-Based Steps**: Match code dynamically
```json
{
  "file": "src/auth.ts",
  "pattern": "export class AuthService",
  "description": "The AuthService handles all authentication logic"
}
```

### Selection Ranges

**Highlight Code Blocks**:
```json
{
  "file": "src/database.ts",
  "selection": {
    "start": {"line": 10, "character": 0},
    "end": {"line": 20, "character": 0}
  },
  "description": "Connection pool configuration"
}
```

---

## Patterns

### Pattern 1: Create Basic Onboarding Tour

```python
import json
from pathlib import Path

def create_onboarding_tour(output_path: str = ".tours/getting-started.tour"):
    """Create a basic onboarding tour for new developers."""

    tour = {
        "title": "Getting Started with the Codebase",
        "description": "A walkthrough of key files and architecture",
        "steps": [
            {
                "description": "# Welcome!\n\nThis tour will guide you through the main components of our application."
            },
            {
                "file": "README.md",
                "line": 1,
                "description": "Start by reading the README for setup instructions"
            },
            {
                "directory": "src/",
                "description": "All source code lives in the `src/` directory"
            },
            {
                "file": "src/main.py",
                "pattern": "def main\\(\\):",
                "description": "# Application Entry Point\n\nThe main() function initializes and starts the application"
            }
        ]
    }

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(tour, f, indent=2)

    return output_path
```

### Pattern 2: Architecture Deep-Dive Tour

```python
def create_architecture_tour(component: str, files: list[dict]):
    """Create a tour explaining a specific architectural component."""

    tour = {
        "title": f"{component} Architecture",
        "description": f"Deep dive into {component} design and implementation",
        "steps": [
            {
                "description": f"# {component} Overview\n\nThis component handles..."
            }
        ]
    }

    # Add file-based steps
    for file_info in files:
        tour["steps"].append({
            "file": file_info["path"],
            "line": file_info.get("line"),
            "selection": file_info.get("selection"),
            "description": file_info["explanation"]
        })

    return tour
```

### Pattern 3: Follow Existing Tour Programmatically

```python
import json
from pathlib import Path
from typing import Iterator

def read_tour(tour_path: str) -> dict:
    """Load a tour file from disk."""
    with open(tour_path) as f:
        return json.load(f)

def iterate_tour_steps(tour: dict) -> Iterator[tuple[int, dict]]:
    """Iterate through tour steps with indices."""
    for idx, step in enumerate(tour["steps"], 1):
        yield idx, step

def follow_tour(tour_path: str):
    """Follow a tour and extract insights."""
    tour = read_tour(tour_path)

    print(f"Tour: {tour['title']}")
    if desc := tour.get('description'):
        print(f"Description: {desc}\n")

    for step_num, step in iterate_tour_steps(tour):
        print(f"Step {step_num}:")

        if file_path := step.get('file'):
            line = step.get('line', 1)
            print(f"  File: {file_path}:{line}")

        if directory := step.get('directory'):
            print(f"  Directory: {directory}")

        print(f"  Description: {step['description'][:100]}...\n")
```

### Pattern 4: Feature Workflow Tour

```python
def create_feature_tour(feature_name: str, workflow_steps: list[str]):
    """Create a tour showing how a feature works end-to-end."""

    tour = {
        "title": f"{feature_name} - Complete Workflow",
        "description": f"Follow data flow through {feature_name}",
        "steps": [
            {
                "description": f"# {feature_name} Flow\n\nTrace how data moves through the system"
            }
        ]
    }

    # Add workflow steps
    step_descriptions = {
        "api": "API endpoint receives request",
        "validation": "Request validation and schema checking",
        "service": "Business logic processing",
        "database": "Data persistence",
        "response": "Response formatting and return"
    }

    for step_type in workflow_steps:
        tour["steps"].append({
            "file": f"src/{step_type}.py",
            "description": f"## {step_type.title()}\n\n{step_descriptions[step_type]}"
        })

    return tour
```

### Pattern 5: Bug Investigation Tour

```python
def create_bug_tour(bug_id: str, reproduction_steps: list[dict]):
    """Document bug reproduction path for investigation."""

    tour = {
        "title": f"Bug #{bug_id} - Investigation Guide",
        "description": "Steps to reproduce and understand the issue",
        "ref": f"bug-{bug_id}",  # Link to bug fix branch
        "steps": []
    }

    for idx, step in enumerate(reproduction_steps, 1):
        tour["steps"].append({
            "file": step["file"],
            "line": step.get("line"),
            "description": f"## Step {idx}: {step['action']}\n\n{step['explanation']}"
        })

    # Add final step for the fix
    tour["steps"].append({
        "description": "# The Fix\n\nSee the next tour for the solution..."
        "nextTour": f"Bug #{bug_id} - Solution"
    })

    return tour
```

### Pattern 6: Multi-File Refactoring Tour

```python
def create_refactoring_tour(refactor_name: str, before_after: list[tuple]):
    """Document a refactoring with before/after comparisons."""

    tour = {
        "title": f"Refactoring: {refactor_name}",
        "description": "Understanding the changes and motivations",
        "steps": [
            {
                "description": f"# Refactoring: {refactor_name}\n\n## Goals\n- Improve readability\n- Reduce complexity\n- Enhance maintainability"
            }
        ]
    }

    for file_path, old_pattern, new_pattern, reason in before_after:
        tour["steps"].extend([
            {
                "file": file_path,
                "pattern": old_pattern,
                "description": f"## Before\n\nOld approach: {reason['problem']}"
            },
            {
                "file": file_path,
                "pattern": new_pattern,
                "description": f"## After\n\nNew approach: {reason['solution']}"
            }
        ])

    return tour
```

### Pattern 7: Find All Tours in Repository

```python
from pathlib import Path
from typing import List

def discover_tours(repo_path: str = ".") -> List[Path]:
    """Find all CodeTour files in a repository."""

    search_paths = [
        ".tours/**/*.tour",
        ".vscode/tours/**/*.tour",
        ".github/tours/**/*.tour",
        "*.tour",
        ".vscode/*.tour"
    ]

    tours = []
    repo = Path(repo_path)

    for pattern in search_paths:
        tours.extend(repo.glob(pattern))

    return sorted(set(tours))

def list_available_tours(repo_path: str = "."):
    """List all available tours with metadata."""

    tours = discover_tours(repo_path)

    for tour_path in tours:
        tour = read_tour(tour_path)
        primary = " [PRIMARY]" if tour.get("isPrimary") else ""
        print(f"- {tour['title']}{primary}")
        print(f"  Path: {tour_path}")
        print(f"  Steps: {len(tour['steps'])}")
        if desc := tour.get('description'):
            print(f"  Description: {desc[:60]}...")
        print()
```

### Pattern 8: Validate Tour Structure

```python
def validate_tour(tour: dict) -> list[str]:
    """Validate tour structure and return errors."""

    errors = []

    # Required fields
    if "title" not in tour:
        errors.append("Missing required field: title")

    if "steps" not in tour:
        errors.append("Missing required field: steps")
    elif not isinstance(tour["steps"], list):
        errors.append("Field 'steps' must be an array")
    else:
        # Validate each step
        for idx, step in enumerate(tour["steps"], 1):
            if "description" not in step:
                errors.append(f"Step {idx}: Missing required field 'description'")

            # Check for conflicting fields
            if "file" in step and "directory" in step:
                errors.append(f"Step {idx}: Cannot have both 'file' and 'directory'")

            # Validate selection structure
            if sel := step.get("selection"):
                if "start" not in sel or "end" not in sel:
                    errors.append(f"Step {idx}: Selection must have 'start' and 'end'")

    return errors
```

---

## Quick Reference

### Tour File Locations

```
Priority Order          | Path
------------------------|-------------------------
Workspace tours         | .tours/*.tour
VS Code tours           | .vscode/tours/*.tour
GitHub tours            | .github/tours/*.tour
Root tours              | *.tour, .vscode/*.tour
```

### Tour Object Schema

```json
{
  "title": "string (required)",
  "description": "string (optional)",
  "ref": "git reference (optional)",
  "isPrimary": "boolean (optional)",
  "steps": ["array (required)"],
  "nextTour": "string (optional)"
}
```

### Step Object Schema

```json
{
  "description": "string (required)",
  "file": "string (optional)",
  "directory": "string (optional)",
  "line": "number (optional)",
  "pattern": "regex string (optional)",
  "selection": {
    "start": {"line": 0, "character": 0},
    "end": {"line": 10, "character": 0}
  },
  "title": "string (optional)"
}
```

### Key Guidelines

```
✅ DO: Use markdown in descriptions for rich formatting
✅ DO: Prefer pattern matching over hardcoded line numbers
✅ DO: Keep tours focused (8-12 steps ideal)
✅ DO: Chain related tours with nextTour
✅ DO: Test tours by following them manually
✅ DO: Update tours when code changes significantly

❌ DON'T: Create tours with 20+ steps (split into multiple)
❌ DON'T: Use absolute file paths (use workspace-relative)
❌ DON'T: Hardcode line numbers for frequently-changing code
❌ DON'T: Leave tours without clear descriptions
❌ DON'T: Mix unrelated topics in one tour
```

---

## Anti-Patterns

### Critical Violations

❌ **Hardcoded line numbers for volatile code**:
```json
{
  "file": "src/api.ts",
  "line": 147,  // This line number will change frequently
  "description": "Authentication middleware"
}
```

✅ **Use pattern matching**:
```json
{
  "file": "src/api.ts",
  "pattern": "export const authMiddleware",
  "description": "Authentication middleware"
}
```

❌ **Tours that are too long**: 25-step tour covering entire codebase
✅ **Split into focused tours**: "Authentication Tour", "Database Tour", "API Tour"

❌ **Missing context in descriptions**:
```json
{
  "file": "src/utils.ts",
  "line": 50,
  "description": "Helper function"  // Too vague
}
```

✅ **Rich, helpful descriptions**:
```json
{
  "file": "src/utils.ts",
  "pattern": "export function parseConfig",
  "description": "# Configuration Parser\n\nParses YAML config files and validates against schema. Returns typed config object or throws ValidationError."
}
```

### Common Mistakes

❌ **Absolute file paths**: `"file": "/Users/alice/project/src/main.py"`
✅ **Workspace-relative paths**: `"file": "src/main.py"`

❌ **Stale tours**: Tours never updated as code evolves
✅ **Maintained tours**: Review and update quarterly or after major refactors

❌ **No tour discovery**: Tours hidden in random locations
✅ **Standard locations**: Use `.tours/` directory, mark primary tour with `isPrimary: true`

---

## Related Skills

- `skill-repo-discovery.md` - Discovering codebase structure and patterns
- `skill-repo-planning.md` - Planning repository exploration strategies
- `skill-creation.md` - Creating documentation and knowledge artifacts
- `beads-workflow.md` - Tracking documentation work with Beads

---

**Last Updated**: 2025-10-26
**Format Version**: 1.0 (Atomic)
