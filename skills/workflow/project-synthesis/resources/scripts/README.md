# Project Synthesis Scripts

Bundled scripts for project synthesis operations. These handle deterministic operations that would otherwise require repeated implementation.

## Usage

All scripts should be run from project root:

```bash
python skills/workflow/project-synthesis/resources/scripts/extract_concepts.py
```

## Scripts

### extract_concepts.py

**Purpose**: Extract key concepts from all project files

**Scans**:
- Markdown headers (## and ###)
- Code structures (classes, functions, types)
- Beads issue descriptions
- Bold terms in markdown (important concepts)

**Supported Languages**:
- Python (.py)
- TypeScript/JavaScript (.ts, .js)
- Go (.go)
- Rust (.rs)
- Zig (.zig)

**Output**: `$SYNTHESIS_DIR/concepts.json`

**Format**:
```json
{
  "header": [
    {"value": "Authentication System", "count": 3, "sources": ["plan.md", "spec.md"]}
  ],
  "class": [
    {"value": "UserAuth", "count": 2, "sources": ["auth.py", "test_auth.py"]}
  ],
  "function": [
    {"value": "validate_token", "count": 4, "sources": ["auth.py", "utils.py"]}
  ]
}
```

**What it captures**:
- Section headers from docs
- Class/function/type names from code
- Important terms (bold text in markdown)
- Beads issue terminology
- Occurrence counts and source files

**Environment**:
- Reads `$SYNTHESIS_DIR` environment variable (defaults to `.claude/synthesis/current`)
- Creates output directory if it doesn't exist
- Skips `node_modules`, `.git`, `dist` directories

**Example**:
```bash
# Set synthesis directory
export SYNTHESIS_DIR=.claude/synthesis/$(date +%Y%m%d_%H%M%S)

# Run extraction
python skills/workflow/project-synthesis/resources/scripts/extract_concepts.py

# View results
cat $SYNTHESIS_DIR/concepts.json | jq '.header | .[:5]'
```

### Future Scripts

The following scripts are referenced in the main skill but not yet implemented:

- **analyze_dependencies.py** - Build comprehensive dependency graph
- **update_references.py** - Fix references to moved/archived files
- **validate_references.py** - Check for broken links in markdown files

These will be added as the skill matures and real-world usage patterns emerge.

## Requirements

- Python 3.8+
- No external dependencies (stdlib only)
- Run from project root directory

## Best Practices

When creating new scripts for this skill:

1. **Make them deterministic** - Same input = same output
2. **Handle errors gracefully** - Don't crash on missing files
3. **Use meaningful output** - JSON for data, clear messages for logs
4. **Document in this README** - Explain purpose and usage
5. **Test them** - Actually run before committing
6. **Keep dependencies minimal** - Prefer stdlib over external packages

---

**Last Updated**: 2025-10-27
