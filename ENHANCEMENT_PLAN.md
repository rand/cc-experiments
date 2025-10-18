# Skills Enhancement Plan

Based on Codex's suggestions, this document outlines the roadmap for improving the skills library.

## Status Summary

- ✅ **Enhancement 1**: YAML frontmatter added to all 132 skills
- ✅ **Enhancement 2**: Future dates fixed (84 skills updated to 2025-10-18)
- 🔄 **Enhancement 3**: Oversized skills identified (89 skills >500 lines)
- ⏳ **Enhancement 4**: Companion assets planned
- ⏳ **Enhancement 5**: Smoke tests designed

---

## Enhancement 3: Split Oversized Skills

### Priority 1: Largest Skills (>800 lines)

#### orm-patterns.md (941 lines) → 3 sub-skills
- `orm-patterns-core.md` - ORM basics, models, queries (~250 lines)
- `orm-n-plus-one.md` - N+1 prevention, eager loading strategies (~350 lines)
- `orm-transactions.md` - Transactions, concurrency, locking patterns (~300 lines)

#### duckdb-analytics.md (890 lines) → 3 sub-skills
- `duckdb-basics.md` - Setup, querying, data types, SQL features (~250 lines)
- `duckdb-file-formats.md` - Parquet, CSV, JSON integration (~300 lines)
- `duckdb-performance.md` - Window functions, optimization, aggregations (~300 lines)

#### docker-compose-development.md (844 lines) → 2 sub-skills
- `docker-compose-basics.md` - Services, networks, volumes, basics (~400 lines)
- `docker-compose-advanced.md` - Dependencies, healthchecks, secrets, multi-stage (~400 lines)

#### rest-api-design.md (838 lines) → 3 sub-skills
- `rest-api-resources.md` - Resource modeling, URLs, naming conventions (~250 lines)
- `rest-api-methods.md` - HTTP methods (GET, POST, PUT, PATCH, DELETE) (~300 lines)
- `rest-api-status-codes.md` - Status codes, error handling, idempotency (~250 lines)

### Priority 2: Medium-Large Skills (700-800 lines)

#### smt-theory-applications.md (813 lines) → 2 sub-skills
- `smt-program-verification.md` - Program verification, symbolic execution
- `smt-constraint-solving.md` - Scheduling, optimization problems

#### infrastructure-security.md (799 lines) → 2 sub-skills
- `infrastructure-iam-security.md` - IAM roles, policies, least privilege
- `infrastructure-encryption-secrets.md` - Encryption, secrets management, KMS

#### kubernetes-basics.md (784 lines) → 2 sub-skills
- `kubernetes-core-concepts.md` - Pods, Deployments, Services, ConfigMaps
- `kubernetes-networking-storage.md` - Ingress, PersistentVolumes, StatefulSets

#### api-authentication.md (788 lines) → 2 sub-skills
- `api-jwt-authentication.md` - JWT implementation, refresh tokens
- `api-oauth-authentication.md` - OAuth 2.0 flows, social login

### Priority 3: Candidate Skills (600-700 lines)

Review and potentially split:
- react-form-handling.md (778)
- ci-security.md (774)
- aws-serverless.md (773)
- api-rate-limiting.md (767)
- nextjs-app-router.md (760)
- database-selection.md (758)
- container-security.md (754)

### Splitting Guidelines

1. **Preserve cross-references**: Update related skills links
2. **Maintain coherence**: Each sub-skill should be independently useful
3. **Add navigation**: Each sub-skill should reference siblings
4. **Keep examples**: Distribute code examples appropriately

---

## Enhancement 4: Companion Assets

### Asset Types

#### 1. Starter Templates
Process-heavy skills benefit from ready-to-use templates:

**Modal.com Skills**:
- `assets/modal-starter/` - Minimal Modal app with GPU, web endpoints
- `assets/modal-llm-starter/` - LLM inference template with caching
- `assets/modal-training-starter/` - Training pipeline with checkpoints

**iOS Skills**:
- `assets/swiftui-starter/` - MVVM app template with navigation
- `assets/swiftdata-starter/` - SwiftData app with sync
- `assets/ios-networking-starter/` - NetworkService actor pattern

**Zig Skills**:
- `assets/zig-project-template/` - Standard Zig project layout
- `assets/zig-cli-template/` - CLI app with subcommands
- `assets/zig-lib-template/` - Library with tests and docs

#### 2. Reference Scripts
Automation for common workflows:

**Database Skills**:
- `scripts/postgres-schema-generator.py` - Generate schema from models
- `scripts/migration-validator.py` - Check migration safety
- `scripts/n-plus-one-detector.py` - Analyze queries for N+1

**CI/CD Skills**:
- `scripts/workflow-generator.sh` - Generate GitHub Actions workflow
- `scripts/security-scan-setup.sh` - Configure security scanning
- `scripts/cache-analyzer.py` - Analyze cache hit rates

#### 3. Seed Projects
Full working examples:

**Infrastructure**:
- `examples/terraform-aws-starter/` - Multi-env AWS setup
- `examples/kubernetes-app/` - Complete k8s application
- `examples/docker-compose-stack/` - Full local dev environment

**Web**:
- `examples/nextjs-full-stack/` - Next.js + tRPC + Prisma
- `examples/fastapi-async/` - FastAPI with async patterns
- `examples/react-native-app/` - Cross-platform mobile app

### Asset Directory Structure

```
skills/
├── api/
│   ├── rest-api-design.md
│   └── assets/
│       ├── openapi-template.yaml
│       └── postman-collection.json
├── modal/
│   ├── modal-functions-basics.md
│   └── assets/
│       ├── modal-starter/
│       │   ├── app.py
│       │   ├── requirements.txt
│       │   └── README.md
│       └── modal-llm-starter/
│           ├── inference.py
│           ├── deployment.md
│           └── test_local.py
└── swiftui-architecture.md
    └── assets/
        └── MVVMStarter/
            ├── Package.swift
            ├── Sources/
            └── README.md
```

---

## Enhancement 5: Smoke Tests Strategy

### Test Categories

#### 1. Syntax Validation
Ensure code snippets are syntactically correct:

```python
# tests/validate_code_blocks.py
def test_python_syntax():
    """Extract and validate Python code blocks"""
    for skill in python_skills:
        code_blocks = extract_code_blocks(skill, language='python')
        for block in code_blocks:
            compile(block, '<string>', 'exec')

def test_swift_syntax():
    """Validate Swift code blocks"""
    # Use swiftc or swift-syntax
    pass

def test_zig_syntax():
    """Validate Zig code blocks"""
    # Use zig ast-check
    pass
```

#### 2. Dependency Verification
Check that imports/dependencies are real:

```python
# tests/verify_dependencies.py
def test_modal_imports():
    """Verify Modal.com code uses valid imports"""
    modal_skills = glob("skills/modal-*.md")
    for skill in modal_skills:
        imports = extract_imports(skill, language='python')
        for imp in imports:
            assert imp in ['modal', 'fastapi', 'pydantic']
```

#### 3. Tool Chain Validation
Verify instructions work with current tools:

```yaml
# .github/workflows/smoke-tests.yml
name: Skill Smoke Tests

on: [push, pull_request]

jobs:
  modal-skills:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Test Modal code blocks
        run: |
          pip install modal
          python tests/validate_modal_skills.py

  swift-skills:
    runs-on: macos-14
    steps:
      - uses: actions/checkout@v4
      - name: Test Swift code blocks
        run: |
          swift --version
          python tests/validate_swift_skills.py

  zig-skills:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: goto-bus-stop/setup-zig@v2
        with:
          version: 0.13.0
      - name: Test Zig code blocks
        run: |
          zig version
          python tests/validate_zig_skills.py
```

#### 4. Example Output Capture
Store expected outputs for reproducibility:

```
tests/
├── snapshots/
│   ├── modal-functions-basics/
│   │   ├── hello-world-output.txt
│   │   └── gpu-inference-output.txt
│   ├── swiftui-architecture/
│   │   └── viewmodel-test-output.txt
│   └── zig-project-setup/
│       └── init-output.txt
```

### Test Implementation Plan

#### Phase 1: Static Analysis (Week 1)
- ✅ Extract code blocks by language
- ✅ Validate Python syntax
- ✅ Validate JavaScript/TypeScript syntax
- ⏳ Validate Swift syntax (requires macOS runner)
- ⏳ Validate Zig syntax (requires zig compiler)

#### Phase 2: Import Validation (Week 2)
- ⏳ Check Python imports exist
- ⏳ Check JavaScript/TypeScript packages exist
- ⏳ Check Swift package dependencies
- ⏳ Check Zig dependencies

#### Phase 3: Execution Tests (Week 3)
- ⏳ Run Modal.com examples in sandbox
- ⏳ Compile Swift examples
- ⏳ Build Zig examples
- ⏳ Test database migration scripts

#### Phase 4: Snapshot Testing (Week 4)
- ⏳ Capture outputs for deterministic examples
- ⏳ Create regression tests for examples
- ⏳ Add CI workflow for snapshot validation

---

## CI Workflow: Date Validation

```yaml
# .github/workflows/validate-dates.yml
name: Validate Dates

on:
  pull_request:
    paths:
      - 'skills/**/*.md'

jobs:
  check-dates:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Check for future dates
        run: |
          python3 << 'EOF'
          import re
          import sys
          from pathlib import Path
          from datetime import datetime

          today = datetime.now().date()
          errors = []

          skills_dir = Path("skills")
          for skill_file in skills_dir.rglob("*.md"):
              if "_archive" in str(skill_file):
                  continue

              content = skill_file.read_text()
              matches = re.findall(r'\*\*Last Updated\*\*:\s*(\d{4}-\d{2}-\d{2})', content)

              for match in matches:
                  date = datetime.strptime(match, "%Y-%m-%d").date()
                  if date > today:
                      errors.append(f"{skill_file}: Future date {match}")

          if errors:
              print("❌ Found future dates:")
              for error in errors:
                  print(f"  {error}")
              sys.exit(1)
          else:
              print("✅ All dates are valid")
          EOF
```

---

## Timeline

### Immediate (This Week)
- ✅ Add YAML frontmatter
- ✅ Fix future dates
- ⏳ Create CI date validation workflow
- ⏳ Analyze oversized skills

### Short-term (Next 2 Weeks)
- ⏳ Split top 5 oversized skills (orm-patterns, duckdb-analytics, docker-compose, rest-api, smt-theory)
- ⏳ Create Modal starter templates
- ⏳ Create SwiftUI starter templates
- ⏳ Implement basic smoke tests (syntax validation)

### Medium-term (Next Month)
- ⏳ Split remaining Priority 1 & 2 oversized skills
- ⏳ Add companion assets for all Modal skills
- ⏳ Add companion assets for all iOS skills
- ⏳ Implement dependency verification tests
- ⏳ Create Zig starter templates

### Long-term (Next Quarter)
- ⏳ Complete all skill splits
- ⏳ Full smoke test coverage
- ⏳ Snapshot testing for deterministic examples
- ⏳ Auto-update toolchain version checks
- ⏳ Documentation site with searchable skills

---

## Success Metrics

- **Skill Size**: 90% of skills under 500 lines
- **Test Coverage**: 80% of code blocks validated
- **Companion Assets**: 100% of Modal, iOS, Zig skills have templates
- **Date Accuracy**: 0 future-dated "Last Updated" fields
- **CI Health**: All smoke tests passing on main branch

---

**Last Updated**: 2025-10-18
