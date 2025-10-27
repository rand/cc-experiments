# Full Specification: Level 3 Resources Implementation

**Phase**: 2 - Decomposition and Test Plan
**Date**: 2025-10-27

## Component Decomposition

### Component 1: Manual Resources Creator
**Purpose**: Hand-craft Resources for 15 high-value skills

**Sub-components**:
1.1. Skill Analyzer
   - Read skill content
   - Identify code examples
   - Extract external references
   - Classify complexity

1.2. Resources Structure Creator
   - Create `resources/` directory
   - Generate `REFERENCE.md`
   - Create `scripts/` directory
   - Create `examples/` structure

1.3. Script Generator (Manual)
   - Write validation scripts
   - Write test scripts
   - Write utility scripts
   - Add CLI interfaces

1.4. Documentation Writer
   - Write `scripts/README.md`
   - Update main SKILL.md with Resources section
   - Add usage examples

**Dependencies**: None (can run in parallel per skill)

**Typed Holes**:
```python
# Interface: SkillResourcesCreator
class SkillResourcesCreator:
    def analyze_skill(self, skill_path: Path) -> SkillAnalysis: ...
    def create_structure(self, skill_path: Path) -> ResourcesStructure: ...
    def generate_reference(self, analysis: SkillAnalysis) -> str: ...
    def generate_scripts(self, analysis: SkillAnalysis) -> List[Script]: ...
    def update_skill_md(self, skill_path: Path, resources: ResourcesStructure): ...
```

---

### Component 2: Generator Infrastructure
**Purpose**: Automate Resources creation for bulk work

**Sub-components**:
2.1. Reference Generator
   - Extract detailed content from skills
   - Format as REFERENCE.md
   - Include external references
   - Add tool comparisons

2.2. Validation Script Generator
   - Analyze configuration snippets
   - Generate validators
   - Add error handling
   - Create CLI interface

2.3. Test Script Generator
   - Identify testable components
   - Generate integration tests
   - Add Docker support
   - Create test runners

2.4. Example Extractor
   - Find code examples
   - Extract to standalone files
   - Add dependencies (requirements.txt, package.json)
   - Create README per example

2.5. Documentation Generator
   - Generate scripts/README.md
   - Update main SKILL.md
   - Add usage examples

**Dependencies**:
- Requires patterns from Component 1 (manual skills)
- Needs at least 8-10 manual skills complete before building generators

**Typed Holes**:
```python
# Interface: ResourcesGenerator
class ResourcesGenerator:
    def generate_reference(self, skill: Skill) -> str: ...
    def generate_validation_script(self, skill: Skill) -> Script: ...
    def generate_test_script(self, skill: Skill) -> Script: ...
    def extract_examples(self, skill: Skill) -> List[Example]: ...
    def generate_documentation(self, skill: Skill, resources: Resources) -> str: ...

# Interface: PatternLibrary
class PatternLibrary:
    def learn_from_manual_skill(self, skill_path: Path): ...
    def get_script_template(self, script_type: str) -> Template: ...
    def get_reference_template(self) -> Template: ...
```

---

### Component 3: Bulk Executor
**Purpose**: Apply generators to 108 remaining skills

**Sub-components**:
3.1. Batch Processor
   - Load skill list
   - Run generators in parallel
   - Handle errors gracefully
   - Generate reports

3.2. Quality Checker
   - Spot-check 20% of generated Resources
   - Validate structure
   - Check script syntax
   - Verify documentation completeness

3.3. Regenerator
   - Identify failed generations
   - Fix generator issues
   - Re-run on failed skills

**Dependencies**:
- Requires Component 2 (generators) complete
- Can parallelize across skill categories

**Typed Holes**:
```python
# Interface: BulkExecutor
class BulkExecutor:
    def load_skill_list(self, priority: str = "HIGH") -> List[Path]: ...
    def execute_parallel(self, skills: List[Path], generators: ResourcesGenerator): ...
    def collect_results(self) -> ExecutionReport: ...
    def identify_failures(self, report: ExecutionReport) -> List[Path]: ...
```

---

### Component 4: Validation Infrastructure
**Purpose**: Ensure quality and correctness of all Resources

**Sub-components**:
4.1. Script Validator
   - Execute all scripts in sandboxed environment
   - Verify exit codes
   - Check error handling
   - Validate JSON output format

4.2. Reference Validator
   - Check URLs are live (requests library)
   - Verify external references exist
   - Validate markdown formatting
   - Check for broken links

4.3. Example Validator
   - Extract examples
   - Create virtual environments
   - Run examples
   - Verify output

4.4. Integration Tester
   - Spin up Docker containers (postgres, redis, etc.)
   - Run integration tests
   - Verify examples work against real systems
   - Clean up containers

**Dependencies**:
- Runs after Resources are created (Components 1 or 3)
- Can parallelize per skill

**Typed Holes**:
```python
# Interface: Validator
class Validator:
    def validate_scripts(self, resources_path: Path) -> ValidationResult: ...
    def validate_references(self, reference_md: Path) -> ValidationResult: ...
    def validate_examples(self, examples_path: Path) -> ValidationResult: ...
    def run_integration_tests(self, skill_path: Path) -> ValidationResult: ...

# Interface: ValidationResult
@dataclass
class ValidationResult:
    passed: bool
    failures: List[str]
    warnings: List[str]
    execution_time: float
```

---

### Component 5: CI/CD Integration
**Purpose**: Automate quality checks in GitHub Actions

**Sub-components**:
5.1. CI Configuration
   - Create `.github/workflows/skills-quality.yml`
   - Add script validation
   - Add reference checking
   - Add example testing

5.2. Pre-commit Hooks
   - Validate YAML frontmatter
   - Check Resources structure
   - Lint scripts
   - Verify documentation

**Dependencies**:
- Requires validation infrastructure (Component 4)
- Independent of other components

**Typed Holes**:
```python
# Interface: CIValidator
class CIValidator:
    def validate_skill_structure(self, skill_path: Path) -> bool: ...
    def run_pre_commit_checks(self, changed_files: List[Path]) -> bool: ...
```

---

## Dependency Graph

```
Component 1 (Manual Skills)
    ↓ (patterns learned)
Component 2 (Generators) ──┐
    ↓                       │
Component 3 (Bulk)         │
    ↓                       │
    └───────────────────────┘
              ↓
    Component 4 (Validation)
              ↓
    Component 5 (CI/CD)
```

**Parallelization Opportunities**:
- Component 1: All 15 manual skills are independent
- Component 2: Sub-components are independent (can build generators in parallel)
- Component 3: Skills can be processed in parallel by category
- Component 4: Validation can run per skill in parallel

---

## Critical Path Analysis

**Critical Path**: Component 1 → Component 2 → Component 3 → Component 4

**Bottlenecks**:
1. Generator development (Component 2) blocks bulk execution
2. Need 8-10 manual skills before starting generators
3. Validation is gated on Resources creation

**Optimization**:
- Start Component 4 (validation infra) in parallel with Component 1
- Begin Component 5 (CI/CD) in parallel with Component 2
- Parallelize Component 1 across multiple agents (5-8 agents, 2-3 skills each)

---

## Integration Points (Typed Holes)

### Hole 1: SkillResourcesCreator ↔ PatternLibrary
**Contract**: Manual creator feeds patterns to library
```python
def complete_manual_skill(skill_path: Path) -> Patterns:
    creator = SkillResourcesCreator()
    resources = creator.create_resources(skill_path)
    return PatternLibrary.extract_patterns(resources)
```

### Hole 2: PatternLibrary ↔ ResourcesGenerator
**Contract**: Pattern library provides templates to generators
```python
def generate_resources(skill_path: Path, patterns: PatternLibrary) -> Resources:
    generator = ResourcesGenerator(patterns)
    return generator.generate_all(skill_path)
```

### Hole 3: ResourcesGenerator ↔ BulkExecutor
**Contract**: Executor applies generators to skills
```python
def bulk_generate(skills: List[Path], generator: ResourcesGenerator) -> Report:
    executor = BulkExecutor()
    return executor.execute_parallel(skills, generator)
```

### Hole 4: Resources ↔ Validator
**Contract**: Validator checks Resources quality
```python
def validate_resources(resources_path: Path) -> ValidationResult:
    validator = Validator()
    return validator.validate_all(resources_path)
```

---

## Constraints and Invariants

**Constraints**:
1. Each skill must have exactly one `resources/` directory
2. Scripts must be executable (`chmod +x`)
3. REFERENCE.md must be valid markdown
4. All scripts must have `#!/usr/bin/env python3` or `#!/bin/bash`
5. Scripts must accept `--help` flag
6. Scripts must output JSON when `--json` flag present

**Invariants**:
1. Resources directory presence: `skill_path/resources/` exists
2. Documentation completeness: `scripts/README.md` exists if scripts exist
3. Script executability: All `.py` and `.sh` files are executable
4. Reference existence: `REFERENCE.md` exists
5. Main skill updated: SKILL.md contains Level 3 Resources section

---

## Edge Cases

1. **Skill has no code examples**: Generate REFERENCE.md only, no scripts
2. **Skill references external APIs**: Include API testing scripts
3. **Skill has Docker examples**: Include docker-compose.yml in examples/
4. **Skill has multiple languages**: Create separate example directories per language
5. **Generator fails**: Log error, continue with other skills, collect failures for retry
6. **Script validation fails**: Mark skill for manual review, don't block other skills
7. **External reference is dead**: Replace with alternative or remove, document in validation report

---

## Test Plan

### Test Types

**Unit Tests** (for generators):
- Test reference extraction
- Test script generation
- Test template rendering
- Test pattern matching

**Integration Tests** (for complete flow):
- Test manual skill creation end-to-end
- Test generator on sample skills
- Test bulk execution on 5 test skills
- Test validation on generated Resources

**E2E Tests** (for complete system):
- Create Resources for 3 test skills
- Run all validators
- Verify CI/CD integration
- Test regeneration after fixes

**Property Tests** (invariants):
- All skills with Resources have valid structure
- All scripts are executable
- All REFERENCE.md files are valid markdown
- All external references return 200 OK

### Coverage Targets

- **Critical path** (manual creation, generators, bulk execution): 90%+
- **Business logic** (pattern extraction, script generation): 80%+
- **Validation layer**: 80%+
- **Overall**: 75%+

### Test Data

**Sample Skills for Testing**:
- `test-skills/simple/` - Minimal skill with 1 example
- `test-skills/complex/` - Skill with 10+ examples, multiple languages
- `test-skills/no-code/` - Skill with only documentation
- `test-skills/external-deps/` - Skill referencing external APIs

---

## Checkpoints

1. **After 5 manual skills**: Review patterns, begin generator design
2. **After 10 manual skills**: Complete generator prototypes, test on 3 skills
3. **After 15 manual skills**: Finalize generators, begin bulk execution
4. **After bulk generation**: Run validation on 20% sample
5. **After validation**: Fix issues, regenerate failed skills
6. **Final checkpoint**: All 123 skills validated, CI passing

---

**Phase 2 Complete**: ✅
**Next Phase**: Full Spec → Plan (Execution Plan with Parallelization)
