---
name: typed-holes-examples
description: Complete worked examples of typed holes refactoring including simple file reorganization and complex API consolidation scenarios with full test suites and constraint validation.
---

# Typed Holes Refactoring Examples

Complete worked examples demonstrating the methodology in action.

## Table of Contents

1. [Simple Example: File Reorganization](#simple-example-file-reorganization)
2. [Detailed Example: API Parser Consolidation](#detailed-example-api-parser-consolidation)

---

## Simple Example: File Reorganization

**Scenario**: Reorganize a flat codebase into proper module structure.

**Current State**: All code in `src/` with no clear organization (15 files).

### Phase 0: Discovery

```bash
git checkout -b refactor/typed-holes-v1
python scripts/discover_holes.py
```

**Generated REFACTOR_IR.md (simplified)**:

```markdown
## Hole Catalog

#### H0_architecture

**Question**: What is the current module organization?

**Dependencies**: None

**Status**: pending

**Resolution**: TBD

#### R1_target_architecture

**Question**: How should modules be organized?

**Dependencies**: H0_architecture

**Status**: pending

**Resolution**: TBD

#### R4_file_moves

**Question**: Which files move to which modules?

**Dependencies**: R1_target_architecture

**Status**: pending

**Resolution**: TBD
```

### Phase 1: Resolve H0 (Current State)

**Analysis**:
```python
# tests/characterization/test_current_imports.py
def test_all_imports_work():
    """Capture current import structure"""
    from src import parser, validator, config
    from src import api_client, data_processor
    # All imports succeed
    assert True
```

**Resolution**:
- 15 files in flat structure
- 3 categories: core logic (6), API clients (4), utilities (5)

**Mark H0 resolved** in IR, commit.

### Phase 2: Resolve R1 (Target Architecture)

**Decision**:
```python
# Proposed structure
src/
  core/        # Business logic
  clients/     # API clients
  utils/       # Utilities
```

**Validation**:
```python
# tests/refactor/test_r1_architecture.py
def test_no_circular_dependencies():
    """Ensure clean dependency flow"""
    # utils can't import from core or clients
    # core can't import from clients
    assert validate_architecture_rules()
```

**Mark R1 resolved**, commit.

### Phase 3: Resolve R4 (File Moves)

**Implementation**:
```bash
mkdir -p src/core src/clients src/utils
git mv src/parser.py src/core/
git mv src/validator.py src/core/
# ... move remaining files
```

**Tests**:
```python
# tests/refactor/test_r4_moves.py
def test_imports_still_work():
    """All old import paths still work via __init__.py"""
    from src import parser  # Re-exported
    from src.core import parser  # New location
    assert True

def test_no_broken_imports():
    """Run all modules to detect import errors"""
    import_all_modules()  # Would fail if imports broken
```

**Result**: All files moved, tests pass, commit.

### Phase 4: Generate Report

```bash
python scripts/generate_report.py > REFACTOR_REPORT.md
```

**Metrics**:
- Holes resolved: 3/3
- Files reorganized: 15
- All tests passing: ✓
- Time: 2 hours

**Simple example complete!**

---

## Detailed Example: API Parser Consolidation

**Scenario**: Three similar API parsers (`parse_v1.py`, `parse_v2.py`, `parse_v3.py`) with 80% duplicate code. Consolidate into single unified parser.

### Phase 0: Discovery & Setup

```bash
git checkout -b refactor/typed-holes-parser-consolidation
python scripts/discover_holes.py
```

**Initial Analysis**:
- 3 parser files: 450, 520, 380 LOC
- Duplication: ~75%
- Differences: v1 (XML), v2 (JSON), v3 (JSON + validation)

### Generated REFACTOR_IR.md

```markdown
# Refactor Intermediate Representation

## Executive Summary

**Goal**: Consolidate 3 API parsers into single unified implementation

**Total Holes**: 8
**Pending**: 8
**Resolved**: 0

## Hole Catalog

### Current State Holes

#### H0_parser_differences

**Question**: What are the exact differences between the 3 parsers?

**Dependencies**: None

**Status**: pending

**Resolution**: TBD

**Validation**: TBD

---

#### H0_test_coverage

**Question**: What is current test coverage for parsers?

**Dependencies**: None

**Status**: pending

**Resolution**: TBD

---

### Architecture Holes

#### R1_unified_interface

**Question**: What should the unified parser interface be?

**Dependencies**: H0_parser_differences

**Status**: pending

**Resolution**: TBD

---

#### R2_format_handling

**Question**: How to handle multiple formats (XML, JSON)?

**Dependencies**: R1_unified_interface

**Status**: pending

**Resolution**: TBD

---

### Implementation Holes

#### R4_consolidate_parsing

**Question**: How to merge core parsing logic?

**Dependencies**: R2_format_handling

**Status**: pending

**Resolution**: TBD

---

#### R5_validation_strategy

**Question**: How to unify validation across formats?

**Dependencies**: R4_consolidate_parsing

**Status**: pending

**Resolution**: TBD

---

### Quality Holes

#### R7_test_strategy

**Question**: How to ensure equivalence after consolidation?

**Dependencies**: H0_test_coverage

**Status**: pending

**Resolution**: TBD

---

#### R8_migration_path

**Question**: How to migrate existing code to use new parser?

**Dependencies**: R4_consolidate_parsing, R5_validation_strategy

**Status**: pending

**Resolution**: TBD

---

## Constraints

### Must Preserve
- [x] C1: All current parsing behavior
- [ ] C2: Backward compatible API
- [ ] C3: Performance (no regression)

### Must Improve
- [ ] C5: Reduce duplication by >60%
- [ ] C6: Increase test coverage to >85%
- [ ] C7: Reduce total LOC by >30%

### Must Maintain
- [ ] C9: Type safety (mypy clean)
- [ ] C10: All error handling
```

### Sync with Beads

```bash
python scripts/holes_to_beads.py
```

Creates 8 bead issues with dependencies:
```
bd-1: H0_parser_differences (ready)
bd-2: H0_test_coverage (ready)
bd-3: R1_unified_interface (blocked by bd-1)
bd-4: R2_format_handling (blocked by bd-3)
...
```

### Phase 1: Resolve H0 Holes (Current State)

#### H0_parser_differences

**Investigation**:

```python
# scripts/analyze_parsers.py
import ast

def compare_parsers():
    v1_funcs = extract_functions("parse_v1.py")
    v2_funcs = extract_functions("parse_v2.py")
    v3_funcs = extract_functions("parse_v3.py")

    common = set(v1_funcs) & set(v2_funcs) & set(v3_funcs)
    # ['parse_header', 'parse_body', 'handle_error']

    unique_v1 = ['parse_xml', 'xml_to_dict']
    unique_v2 = ['parse_json']
    unique_v3 = ['validate_schema', 'check_required']

    return {
        "common": common,
        "unique": {"v1": unique_v1, "v2": unique_v2, "v3": unique_v3}
    }
```

**Resolution**:
```markdown
**Differences**:
- Format handling: v1=XML, v2/v3=JSON
- Validation: Only v3 has schema validation
- Core logic: 75% identical (header, body, error handling)

**Commonalities**:
- Same API contract: `parse(data) -> ParsedResult`
- Same error handling strategy
- Same result structure
```

**Update REFACTOR_IR.md**: Mark H0_parser_differences as resolved.

```bash
bd update bd-1 --status done --reason "Analysis complete"
git add REFACTOR_IR.md
git commit -m "Resolve H0_parser_differences: Document parser variations"
```

#### H0_test_coverage

**Analysis**:

```python
# Run coverage
pytest tests/ --cov=src/parsers --cov-report=term

# Results:
# parse_v1.py: 45%
# parse_v2.py: 62%
# parse_v3.py: 71%
```

**Resolution**: Current coverage: 59% average, gaps in error handling.

**Write Characterization Tests**:

```python
# tests/characterization/test_parser_v1_baseline.py
import json

def test_v1_valid_xml():
    """Capture v1 behavior on valid XML"""
    xml = '<data><item>test</item></data>'
    result = parse_v1(xml)
    save_baseline("v1_valid", result)
    assert result.success

def test_v1_invalid_xml():
    """Capture v1 error handling"""
    xml = '<data><unclosed>'
    result = parse_v1(xml)
    save_baseline("v1_invalid", result)
    assert not result.success
    assert "parse error" in result.error.lower()

# Similar for v2, v3...
```

**Mark H0_test_coverage resolved**, commit.

### Phase 2: Architecture Holes

#### R1_unified_interface

**Design**:

```python
# src/parsers/unified.py
from typing import Protocol, Union
from dataclasses import dataclass

@dataclass
class ParseResult:
    success: bool
    data: dict
    error: Optional[str] = None
    format: str = ""

class Parser(Protocol):
    """Unified parser interface"""
    def parse(self, raw_data: Union[str, bytes]) -> ParseResult:
        ...

    def validate(self, data: dict) -> bool:
        ...
```

**Validation Test**:

```python
# tests/refactor/test_r1_interface.py
def test_unified_interface_defined():
    """Interface is well-formed"""
    from src.parsers.unified import Parser, ParseResult
    assert hasattr(Parser, 'parse')
    assert hasattr(Parser, 'validate')

def test_result_structure():
    """ParseResult has required fields"""
    result = ParseResult(success=True, data={})
    assert hasattr(result, 'success')
    assert hasattr(result, 'data')
```

**Resolution**:
```markdown
Unified interface: Parser protocol with parse() and validate()
Common result: ParseResult dataclass
Type-safe: mypy compliant
```

**Update IR**, mark R1 resolved, propagate constraints to R2, commit.

```bash
bd update bd-3 --status done
python scripts/propagate.py R1
```

#### R2_format_handling

**Design**:

```python
# src/parsers/unified.py
from enum import Enum

class Format(Enum):
    XML = "xml"
    JSON = "json"

class UnifiedParser:
    def __init__(self, format: Format):
        self.format = format
        self._parser = self._get_parser(format)

    def _get_parser(self, format: Format):
        if format == Format.XML:
            return XMLParser()
        elif format == Format.JSON:
            return JSONParser()

    def parse(self, raw_data: Union[str, bytes]) -> ParseResult:
        """Delegate to format-specific parser"""
        return self._parser.parse(raw_data)
```

**Tests**:

```python
# tests/refactor/test_r2_formats.py
def test_xml_format_supported():
    parser = UnifiedParser(Format.XML)
    result = parser.parse('<data><item>test</item></data>')
    assert result.success

def test_json_format_supported():
    parser = UnifiedParser(Format.JSON)
    result = parser.parse('{"item": "test"}')
    assert result.success

def test_format_auto_detection():
    """Can detect format automatically"""
    parser = UnifiedParser(Format.AUTO)
    xml_result = parser.parse('<data/>')
    json_result = parser.parse('{}')
    assert xml_result.format == "xml"
    assert json_result.format == "json"
```

**Mark R2 resolved**, propagate to R4, commit.

### Phase 3: Implementation Holes

#### R4_consolidate_parsing

**Implementation**:

```python
# src/parsers/unified.py
class UnifiedParser:
    def parse(self, raw_data: Union[str, bytes]) -> ParseResult:
        """Unified parsing logic"""
        try:
            # Step 1: Parse format-specific data
            parsed = self._parser.parse_raw(raw_data)

            # Step 2: Normalize to common structure
            normalized = self._normalize(parsed)

            # Step 3: Extract common fields
            header = self._parse_header(normalized)
            body = self._parse_body(normalized)

            return ParseResult(
                success=True,
                data={"header": header, "body": body},
                format=self.format.value
            )
        except Exception as e:
            return self._handle_error(e)

    def _normalize(self, parsed):
        """Convert XML/JSON to common dict structure"""
        # Consolidates logic from v1.py:xml_to_dict and v2.py:flatten_json
        if self.format == Format.XML:
            return xml_to_dict(parsed)
        return parsed

    def _parse_header(self, data: dict):
        """Extract header (was duplicated in all 3 parsers)"""
        return {
            "timestamp": data.get("ts", data.get("timestamp")),
            "version": data.get("v", data.get("version", "1.0")),
        }

    def _parse_body(self, data: dict):
        """Extract body (was duplicated in all 3 parsers)"""
        return data.get("payload", data.get("body", {}))

    def _handle_error(self, error: Exception) -> ParseResult:
        """Unified error handling (was duplicated in all 3)"""
        return ParseResult(
            success=False,
            data={},
            error=f"Parse error: {str(error)}",
            format=self.format.value
        )
```

**Equivalence Tests**:

```python
# tests/refactor/test_r4_equivalence.py
import pytest

@pytest.mark.parametrize("xml_input,expected", [
    ('<data><item>test</item></data>', {"item": "test"}),
    ('<data></data>', {}),
])
def test_xml_parsing_equivalent_to_v1(xml_input, expected):
    """New parser produces same results as v1 for XML"""
    old_result = parse_v1(xml_input)
    new_result = UnifiedParser(Format.XML).parse(xml_input)

    assert new_result.success == old_result.success
    assert new_result.data == old_result.data

@pytest.mark.parametrize("json_input,expected", [
    ('{"item": "test"}', {"item": "test"}),
    ('{}', {}),
])
def test_json_parsing_equivalent_to_v2(json_input, expected):
    """New parser produces same results as v2 for JSON"""
    old_result = parse_v2(json_input)
    new_result = UnifiedParser(Format.JSON).parse(json_input)

    assert new_result.success == old_result.success
    assert new_result.data == old_result.data
```

**Run characterization tests**:

```bash
pytest tests/characterization/ -v
# All baseline tests pass - behavior preserved ✓
```

**Mark R4 resolved**, commit.

#### R5_validation_strategy

**Implementation**:

```python
# src/parsers/unified.py
from jsonschema import validate, ValidationError

class UnifiedParser:
    def __init__(self, format: Format, schema: Optional[dict] = None):
        self.format = format
        self.schema = schema
        self._parser = self._get_parser(format)

    def validate(self, data: dict) -> bool:
        """Unified validation (from v3)"""
        if not self.schema:
            return True  # No schema = always valid

        try:
            validate(instance=data, schema=self.schema)
            return True
        except ValidationError:
            return False

    def parse(self, raw_data, validate_result=True) -> ParseResult:
        result = self._parse_internal(raw_data)

        if result.success and validate_result:
            if not self.validate(result.data):
                result.success = False
                result.error = "Validation failed"

        return result
```

**Tests**:

```python
# tests/refactor/test_r5_validation.py
def test_validation_with_schema():
    """Validation works like v3"""
    schema = {
        "type": "object",
        "properties": {"item": {"type": "string"}},
        "required": ["item"]
    }

    parser = UnifiedParser(Format.JSON, schema=schema)

    valid = parser.parse('{"item": "test"}')
    assert valid.success

    invalid = parser.parse('{"other": "test"}')
    assert not invalid.success
    assert "validation" in invalid.error.lower()

def test_validation_optional():
    """Can parse without validation"""
    parser = UnifiedParser(Format.JSON)  # No schema
    result = parser.parse('{"anything": "goes"}')
    assert result.success
```

**Mark R5 resolved**, commit.

### Phase 4: Quality & Migration

#### R7_test_strategy

**Strategy**:
```markdown
1. Characterization tests: Capture all v1/v2/v3 behavior (DONE)
2. Equivalence tests: New parser = old parsers for all cases
3. Unit tests: Each method tested independently
4. Integration tests: Full workflows
5. Property tests: Random inputs don't crash
```

**Additional tests**:

```python
# tests/refactor/test_r7_comprehensive.py
from hypothesis import given, strategies as st

@given(st.text())
def test_parser_never_crashes(random_input):
    """Parser handles any input gracefully"""
    parser = UnifiedParser(Format.JSON)
    result = parser.parse(random_input)
    # Should return result (success or error), never crash
    assert isinstance(result, ParseResult)

def test_integration_full_workflow():
    """End-to-end workflow"""
    parser = UnifiedParser(Format.JSON, schema=get_api_schema())

    # Fetch from API
    raw_data = fetch_api_data()

    # Parse
    result = parser.parse(raw_data)
    assert result.success

    # Use parsed data
    process_data(result.data)
```

**Coverage**:
```bash
pytest tests/ --cov=src/parsers --cov-report=html
# unified.py: 91% coverage ✓
```

**Mark R7 resolved**, commit.

#### R8_migration_path

**Migration**:

```python
# src/parsers/__init__.py
"""
Backward compatibility wrappers
"""
from .unified import UnifiedParser, Format, ParseResult

def parse_v1(xml_data: str) -> ParseResult:
    """Deprecated: Use UnifiedParser(Format.XML) instead"""
    import warnings
    warnings.warn("parse_v1 is deprecated", DeprecationWarning)
    return UnifiedParser(Format.XML).parse(xml_data)

def parse_v2(json_data: str) -> ParseResult:
    """Deprecated: Use UnifiedParser(Format.JSON) instead"""
    import warnings
    warnings.warn("parse_v2 is deprecated", DeprecationWarning)
    return UnifiedParser(Format.JSON).parse(json_data)

# Export for backward compatibility
__all__ = ['UnifiedParser', 'Format', 'ParseResult', 'parse_v1', 'parse_v2']
```

**Migration Guide**:

```markdown
# MIGRATION.md

## Migrating from old parsers to UnifiedParser

### Before:
```python
from src.parsers import parse_v1, parse_v2

result = parse_v2(json_data)
```

### After:
```python
from src.parsers import UnifiedParser, Format

parser = UnifiedParser(Format.JSON)
result = parser.parse(json_data)
```

### Timeline:
- Week 1: Deploy with backward compatibility
- Week 2-4: Migrate all call sites
- Week 5: Remove old functions
```

**Mark R8 resolved**, commit.

### Phase 5: Final Validation

```bash
python scripts/check_completeness.py
```

**Output**:
```
============================================================
  TYPED HOLES REFACTORING - PROGRESS DASHBOARD
============================================================

📊 Overall Progress: 8/8 holes (100.0%)
[██████████████████████████████████████████████████] 100.0%

🎯 Current Phase: Phase 5: Complete (ready for deployment)

📋 Next Steps:
  • Generate final report: python scripts/generate_report.py
  • Review all constraints satisfied
  • Prepare PR for review
```

### Generate Final Report

```bash
python scripts/generate_report.py > REFACTOR_REPORT.md
```

**REFACTOR_REPORT.md**:

```markdown
# Refactor Report: API Parser Consolidation

## Executive Summary

Successfully consolidated 3 duplicate API parsers into single unified implementation.

**Duration**: 3 days
**Holes Resolved**: 8/8 (100%)
**All Gates Passed**: ✓

## Hole Resolution Summary

| Hole ID | Description | Status | Validation |
|---------|-------------|--------|------------|
| H0_parser_differences | Analyzed parser variations | ✓ | Manual analysis |
| H0_test_coverage | Measured coverage | ✓ | pytest --cov |
| R1_unified_interface | Designed Protocol interface | ✓ | Type checker |
| R2_format_handling | Multi-format support | ✓ | Format tests |
| R4_consolidate_parsing | Merged core logic | ✓ | Equivalence tests |
| R5_validation_strategy | Unified validation | ✓ | Schema tests |
| R7_test_strategy | Comprehensive testing | ✓ | 91% coverage |
| R8_migration_path | Backward compatibility | ✓ | Migration guide |

## Metrics Delta

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Total LOC | 1,350 | 420 | -69% ✓ |
| Duplication | 75% | 5% | -70% ✓ |
| Test Coverage | 59% | 91% | +32% ✓ |
| Complexity (avg) | 12.4 | 6.2 | -50% ✓ |
| Files | 3 | 1 | -67% ✓ |

## Behavioral Analysis

**Intentional Changes**:
- None - all behavior preserved

**Equivalence Validation**:
- 147 characterization tests: ✓ All pass
- 68 equivalence tests: ✓ All pass
- Property tests (1000 random inputs): ✓ All handled

## Constraint Validation

### Must Preserve
- [x] C1: All current parsing behavior - VERIFIED
- [x] C2: Backward compatible API - VERIFIED
- [x] C3: Performance (no regression) - VERIFIED (3% faster)

### Must Improve
- [x] C5: Reduce duplication by >60% - ACHIEVED (70%)
- [x] C6: Increase test coverage to >85% - ACHIEVED (91%)
- [x] C7: Reduce total LOC by >30% - ACHIEVED (69%)

### Must Maintain
- [x] C9: Type safety (mypy clean) - VERIFIED
- [x] C10: All error handling - VERIFIED

**All constraints satisfied!**

## Migration Guide

See MIGRATION.md for step-by-step migration from old parsers.

## Risk Assessment

**Risk Level**: LOW

**Mitigation**:
- Backward compatibility maintained
- Comprehensive test coverage
- Gradual migration strategy
- Can revert instantly if issues found

## Recommendation

✅ **APPROVED FOR MERGE**

All validation gates passed, constraints satisfied, comprehensive testing complete.
```

### Create Pull Request

```bash
git push -u origin refactor/typed-holes-parser-consolidation
gh pr create \
  --title "Consolidate API parsers using typed holes methodology" \
  --body "$(cat REFACTOR_REPORT.md)"
```

**Detailed example complete!**

---

## Summary: Key Takeaways

### Simple Example (File Reorganization)
- **Time**: 2 hours
- **Holes**: 3
- **Value**: Clear organization, 0 regressions

### Complex Example (Parser Consolidation)
- **Time**: 3 days
- **Holes**: 8
- **Value**: -69% LOC, -70% duplication, +32% coverage, 0 regressions

### Universal Patterns

1. **Always start with characterization tests** - Safety net before changes
2. **Resolve current state holes first** - Understand before changing
3. **Architecture holes before implementation** - Design then build
4. **Test each hole resolution independently** - Incremental validation
5. **Track progress with beads** - Never lose state across sessions
6. **Generate final report** - Document decisions and outcomes

### When to Use This Methodology

**Use for**:
- Refactoring >5 files
- Consolidating duplicate code
- Architectural changes
- Any refactor with >3 distinct steps

**Skip for**:
- Single file changes
- Simple renames
- Adding new features (not refactoring)
- Time pressure situations

---

**Questions?** See [SKILL.md](../SKILL.md) for full methodology or [TROUBLESHOOTING.md](../SKILL.md#troubleshooting) for common issues.
