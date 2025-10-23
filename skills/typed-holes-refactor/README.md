# Typed Holes Refactor - Claude Code Skill

A comprehensive skill for systematically refactoring codebases using the Design by Typed Holes methodology - iterative, test-driven refactoring with formal hole resolution, constraint propagation, and continuous validation.

## What This Skill Does

This skill helps you refactor codebases by:

1. **Discovering architectural unknowns** ("holes") in your codebase
2. **Resolving holes systematically** using test-driven development
3. **Propagating constraints** through dependency graphs
4. **Validating continuously** to prevent regressions
5. **Generating comprehensive reports** comparing old vs new

## Key Features

- ✅ **Test-Driven**: Write validation tests BEFORE refactoring
- ✅ **Safe**: Works in branches, preserves main and .beads/
- ✅ **Systematic**: Formal hole resolution with dependency tracking
- ✅ **Validated**: Continuous validation against characterization tests
- ✅ **Comprehensive**: Complete tooling for discovery, validation, and reporting

## Installation

### Option 1: Claude Desktop/Web (Recommended)

1. Download `typed-holes-refactor.skill`
2. In Claude, go to Settings → Skills
3. Click "Add Skill" and upload the .skill file
4. The skill is now available for use!

### Option 2: Manual Installation (Claude Code)

```bash
# Copy skill to your skills directory
mkdir -p ~/.claude/skills
unzip typed-holes-refactor.skill -d ~/.claude/skills/
```

## Quick Start

### Step 1: Install the Skill

Follow installation instructions above.

### Step 2: Start Claude Code in Your Project

```bash
cd your-project
claude-code
```

### Step 3: Use the Initial Prompt

Copy and paste this into Claude Code:

```
I want to refactor this codebase using the typed-holes-refactor skill. Here's the context:

Repository: [describe your repo]
Goal: [what you want to achieve]
Constraints: [any specific constraints]

Please:
1. Read the typed-holes-refactor skill
2. Create a safe refactor branch
3. Run discover_holes.py to analyze the codebase
4. Create baseline characterization tests
5. Help me resolve holes one by one using test-driven development

Let's start with the discovery phase.
```

### Step 4: Follow the Process

The skill will guide you through:

1. **Discovery**: Analyze codebase and identify holes
2. **Characterization**: Write tests capturing current behavior
3. **Resolution**: Resolve holes one by one with TDD
4. **Validation**: Continuous validation at each step
5. **Reporting**: Generate comprehensive delta report

## Workflow Overview

```
┌─────────────────────────────────────────────────────────┐
│ 1. DISCOVERY                                             │
│    git checkout -b refactor/typed-holes-v1              │
│    python scripts/discover_holes.py                      │
│    → Creates REFACTOR_IR.md with hole catalog           │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 2. CHARACTERIZATION                                      │
│    Create tests/characterization/test_*.py              │
│    → Captures exact current behavior                     │
│    → Safety net for refactoring                          │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 3. ITERATIVE RESOLUTION (repeat for each hole)          │
│    a. python scripts/next_hole.py                        │
│       → Shows ready holes                                │
│    b. Write tests/refactor/test_h{N}_*.py (fails first) │
│    c. Implement resolution                               │
│    d. python scripts/validate_resolution.py H{N}         │
│    e. python scripts/propagate.py H{N}                   │
│    f. git commit -m "Resolve H{N}: ..."                  │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 4. FINAL REPORT                                          │
│    python scripts/generate_report.py > REFACTOR_REPORT.md│
│    → Comprehensive delta analysis                        │
│    → Ready for merge                                     │
└─────────────────────────────────────────────────────────┘
```

## Scripts Included

The skill includes these automation scripts:

- **`discover_holes.py`** - Analyze codebase and generate REFACTOR_IR.md
- **`next_hole.py`** - Show next resolvable holes based on dependencies
- **`validate_resolution.py`** - Check if hole resolution satisfies constraints
- **`propagate.py`** - Update dependent holes after resolution
- **`generate_report.py`** - Create comprehensive delta report

All scripts include `--help` for detailed usage.

## Reference Documentation

The skill includes comprehensive references:

- **`HOLE_TYPES.md`** - Complete taxonomy of refactoring holes
- **`CONSTRAINT_RULES.md`** - Constraint propagation patterns
- **`VALIDATION_PATTERNS.md`** - Test patterns for validation

Claude will read these as needed during the refactoring process.

## Example Usage

See `USAGE_PROMPT.md` for:
- Complete example prompts
- Troubleshooting guides
- Advanced usage patterns
- Best practices

## When to Use This Skill

Perfect for:
- 🏗️ **Architecture refactoring** - Reorganizing code structure
- 🔄 **Code consolidation** - Merging duplicate implementations
- 🧹 **Technical debt reduction** - Systematic cleanup
- 📈 **Complexity reduction** - Simplifying convoluted code
- ✅ **Quality improvement** - Improving test coverage and code quality

Not ideal for:
- Small, localized changes (overkill)
- Exploratory refactoring (too structured)
- Breaking changes without compatibility needs (use simpler approach)

## Key Principles

1. **Test-Driven Everything** - Write tests before refactoring
2. **Hole-Driven Progress** - Resolve unknowns systematically
3. **Continuous Validation** - Never break characterization tests
4. **Safe by Construction** - Work in branches, preserve history
5. **Formal Completeness** - All holes resolved = refactoring complete

## Compatibility

- **Works with**: Python, JavaScript, TypeScript, Go, Rust, and other languages
- **Requires**: Git repository with branch support
- **Optional**: pytest (for Python), radon (for complexity analysis)

## Support

If you encounter issues:

1. Check `USAGE_PROMPT.md` for troubleshooting prompts
2. Review the reference documentation in the skill
3. Ask Claude Code for help - it has access to all skill documentation

## Meta-Consistency

This skill practices what it preaches: it uses the typed holes methodology to refactor codebases, and can even use itself to improve itself! 🤯

## License

See LICENSE.txt in the skill package.

---

**Ready to refactor systematically? Install the skill and start with the prompts in USAGE_PROMPT.md!**
