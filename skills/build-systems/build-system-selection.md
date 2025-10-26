---
name: build-systems-build-system-selection
description: Decision matrix for choosing between Make, CMake, Gradle, Maven, Bazel, and other build systems based on project requirements, language, and scale.
---
# Build System Selection

**Last Updated**: 2025-10-26

## When to Use This Skill

Use this skill when:
- Starting a new project and choosing build system
- Migrating from one build system to another
- Evaluating build system trade-offs for team/project
- Deciding between language-native vs polyglot build tools
- Assessing monorepo vs polyrepo build strategies

**Prerequisites**: Understanding of project requirements, language ecosystem, team size

## Decision Framework

### Quick Decision Tree

```
What language(s)?
├─ Pure C/C++
│  ├─ Simple project → Make
│  ├─ Cross-platform → CMake
│  └─ Monorepo/Google-scale → Bazel
├─ Pure Java/Kotlin
│  ├─ Convention over configuration → Maven
│  ├─ Flexibility/performance → Gradle
│  └─ Monorepo → Bazel
├─ Pure Rust → Cargo (no alternatives)
├─ Pure Go → go build (no alternatives)
├─ Pure Python → uv, pip-tools, Poetry
├─ Pure JavaScript/TypeScript → npm, pnpm, Bun
├─ Polyglot (multiple languages)
│  ├─ <50k files → Language-specific tools + orchestration
│  └─ >50k files → Bazel or Pants
└─ Monorepo (many projects)
   ├─ Pure JVM → Gradle multi-project
   └─ Mixed languages → Bazel
```

## Build System Comparison Matrix

### Feature Matrix

| Feature | Make | CMake | Maven | Gradle | Bazel | Cargo | Go |
|---------|------|-------|-------|--------|-------|-------|------|
| **Languages** | Any | C/C++ | JVM | JVM+ | Any | Rust | Go |
| **Learning Curve** | Medium | Steep | Low | Medium | Steep | Low | Low |
| **Performance** | Good | Good | Slow | Fast | Fastest | Fast | Fast |
| **Incremental** | Good | Good | Good | Excellent | Excellent | Excellent | Excellent |
| **Caching** | Basic | Basic | Local | Local+Remote | Remote | Local | Local |
| **Cross-platform** | Manual | Excellent | Excellent | Excellent | Excellent | Excellent | Excellent |
| **IDE Support** | Basic | Excellent | Excellent | Excellent | Good | Excellent | Excellent |
| **Dependency Mgmt** | Manual | Manual | Excellent | Excellent | Excellent | Excellent | Excellent |
| **Monorepo** | Poor | Medium | Good | Good | Excellent | N/A | N/A |
| **Ecosystem** | Mature | Mature | Mature | Growing | Growing | Growing | Mature |

### Performance Benchmarks (2024 Data)

**Clean Build** (medium project, ~10k files):
- Make: ~60s
- CMake+Ninja: ~50s
- Maven: ~120s
- Gradle: ~90s (cold), ~30s (warm daemon)
- Bazel: ~100s (hermetic overhead)
- Cargo: ~40s
- Go: ~20s

**Incremental Build** (1% file change):
- Make: ~5s
- CMake+Ninja: ~4s
- Maven: ~30s
- Gradle: ~3s
- Bazel: ~2s
- Cargo: ~2s
- Go: ~1s

**Note**: Bazel with remote cache: ~0.5s (cache hit)

## Language-Specific Recommendations

### C/C++ Projects

```
Project Type → Recommendation
─────────────────────────────────────
Simple CLI tool → Make
Cross-platform lib → CMake
Large monorepo → Bazel
Game engine → CMake + custom scripts
Embedded → CMake with toolchains
```

**Make**:
- ✅ Ubiquitous, minimal dependencies
- ✅ Fast for small projects
- ❌ Poor cross-platform support
- ❌ Manual dependency tracking

**CMake**:
- ✅ Excellent cross-platform
- ✅ Rich ecosystem (find_package)
- ✅ IDE integration (Visual Studio, Xcode)
- ❌ Steep learning curve
- ❌ Verbose configuration

**Bazel**:
- ✅ Hermetic builds
- ✅ Remote caching
- ✅ Polyglot support
- ❌ Steep learning curve
- ❌ Setup overhead for small projects

**Example: CMake for Cross-Platform C++ Library**
```cmake
cmake_minimum_required(VERSION 3.20)
project(MyLib VERSION 1.0.0)

add_library(mylib src/lib.cpp)
target_include_directories(mylib PUBLIC include)

# Works on Windows, macOS, Linux
install(TARGETS mylib DESTINATION lib)
```

### JVM Projects (Java, Kotlin, Scala)

```
Project Type → Recommendation
─────────────────────────────────────
Spring Boot app → Maven or Gradle
Android app → Gradle (only option)
Microservices → Maven (standardization)
Multi-module lib → Gradle (performance)
Large monorepo → Bazel
```

**Maven**:
- ✅ Convention over configuration
- ✅ Mature, stable, well-documented
- ✅ Excellent IDE support
- ✅ Central repository ecosystem
- ❌ Slower than Gradle
- ❌ XML verbosity
- ❌ Limited flexibility

**Gradle**:
- ✅ Faster than Maven (2-3x with cache)
- ✅ Flexible (Kotlin DSL)
- ✅ Better multi-module support
- ✅ Android default
- ❌ Steeper learning curve
- ❌ More complex than Maven
- ❌ Configuration can be inconsistent

**Bazel**:
- ✅ Best for large monorepos
- ✅ Remote caching
- ✅ Polyglot (Java + C++ + Python)
- ❌ Steep learning curve
- ❌ Less JVM-specific tooling than Maven/Gradle

**Example: Maven for Spring Boot**
```xml
<parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>3.2.0</version>
</parent>

<!-- Convention: no plugin config needed -->
<build>
    <plugins>
        <plugin>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-maven-plugin</artifactId>
        </plugin>
    </plugins>
</build>
```

**Example: Gradle for Multi-Module**
```kotlin
// settings.gradle.kts
include("core", "api", "app")

// Fast incremental builds, parallel execution
// ./gradlew build --parallel
```

### Rust Projects

```
Cargo is the ONLY choice
- Integrated with rustc
- Excellent dependency management (crates.io)
- Fast incremental builds
- No alternative needed
```

```toml
# Cargo.toml
[package]
name = "myapp"
version = "0.1.0"

[dependencies]
serde = "1.0"
tokio = { version = "1.35", features = ["full"] }
```

### Go Projects

```
go build is the standard
- Built into Go toolchain
- Zero configuration for simple projects
- Fast compilation
- Minimal alternatives (Bazel for large monorepos)
```

```go
// go.mod
module github.com/user/project

go 1.21

require (
    github.com/gorilla/mux v1.8.1
)
```

### Python Projects

```
Project Type → Recommendation
─────────────────────────────────────
Modern app/lib → uv (fastest, 2024)
Legacy project → pip + requirements.txt
Library → Poetry or uv
Monorepo → Bazel or Pants
```

**uv** (Recommended, 2024):
- ✅ 10-100x faster than pip
- ✅ Rust-based (rye successor)
- ✅ Modern resolver
- ✅ Lock files

**Poetry**:
- ✅ Good dependency management
- ✅ Mature ecosystem
- ❌ Slower than uv
- ❌ Lock file conflicts

**pip-tools**:
- ✅ Simple, minimal
- ✅ Reproducible builds
- ❌ Manual workflow

### JavaScript/TypeScript Projects

```
Package Manager → Recommendation
─────────────────────────────────────
New project → pnpm or Bun (fast)
Legacy → npm
Monorepo → pnpm workspaces or Turborepo
```

**pnpm**:
- ✅ Faster than npm (3x)
- ✅ Efficient disk usage
- ✅ Workspace support

**Bun**:
- ✅ Fastest (Zig-based)
- ✅ Drop-in npm replacement
- ❌ Less mature ecosystem

**npm**:
- ✅ Default, ubiquitous
- ✅ Stable
- ❌ Slower than alternatives

## Monorepo vs Polyrepo

### Monorepo Build Systems

```
Scale → Recommendation
─────────────────────────────────────
Small (<10 projects) → Language-native + Makefiles
Medium (10-50 projects) → Gradle/Maven multi-module
Large (50-200 projects) → Bazel or Pants
Google-scale (>200 projects) → Bazel
```

**Bazel**:
- ✅ Built for monorepos
- ✅ Hermetic, reproducible
- ✅ Remote caching/execution
- ✅ Polyglot
- ❌ Steep learning curve
- ❌ Requires migration effort

**Gradle Multi-Project**:
- ✅ Good JVM monorepo support
- ✅ Familiar to Java/Kotlin teams
- ✅ Gradle wrapper ensures consistency
- ❌ Less efficient than Bazel at scale
- ❌ JVM-centric

**Pants** (Alternative to Bazel):
- ✅ Python-first
- ✅ Simpler than Bazel
- ✅ Remote caching
- ❌ Smaller community than Bazel

### Polyrepo Build Systems

```
Use language-native tools:
- C/C++: CMake or Make
- Java: Maven or Gradle
- Rust: Cargo
- Go: go build
- Python: uv
- JS/TS: pnpm

Orchestrate with CI (GitHub Actions, GitLab CI)
```

## Migration Strategies

### Make → CMake

**Rationale**: Cross-platform support, better dependency management

```bash
# Before (Makefile)
gcc -o myapp main.c utils.c -I./include

# After (CMakeLists.txt)
add_executable(myapp main.c utils.c)
target_include_directories(myapp PRIVATE include)
```

**Migration Steps**:
1. Create CMakeLists.txt with equivalent targets
2. Test on primary platform
3. Verify cross-platform builds
4. Migrate toolchain flags to target properties
5. Remove Makefile

### Maven → Gradle

**Rationale**: Performance, multi-module flexibility

**Migration Tool**:
```bash
# Gradle provides migration tool
gradle init  # Converts existing Maven project
```

**Manual Migration**:
1. Convert pom.xml to build.gradle.kts
2. Update dependency declarations
3. Migrate plugins
4. Test build lifecycle equivalence
5. Verify CI pipeline compatibility

### Gradle/Maven → Bazel

**Rationale**: Monorepo scale, hermetic builds

**Migration Steps**:
1. Start with leaf modules (no dependencies)
2. Create BUILD files incrementally
3. Use rules_jvm_external for Maven dependencies
4. Migrate tests
5. Hybrid build during transition (Bazel + Gradle)
6. Full cutover after validation

**Tools**:
- `rules_jvm_external` for Maven deps
- `migration-tooling` (Bazel repo)

## Decision Checklist

### Before Choosing Build System

```
[ ] What languages? (Pure vs polyglot)
[ ] Project size? (<1k, 1-10k, 10-100k, >100k files)
[ ] Team size? (1-5, 5-20, 20-100, >100)
[ ] Monorepo or polyrepo?
[ ] Cross-platform requirements?
[ ] Performance critical? (CI time budget?)
[ ] Remote caching needed?
[ ] Existing expertise on team?
[ ] Migration cost vs benefit?
[ ] IDE support requirements?
[ ] Open source or proprietary?
```

### Red Flags

```
❌ Using Make for cross-platform C++ library
   → Use CMake

❌ Using Bazel for 5-person team, single language
   → Use language-native tool

❌ Using Maven for Android
   → Use Gradle (only option)

❌ Using custom scripts for polyglot monorepo
   → Use Bazel

❌ Using npm for large monorepo (>50 packages)
   → Use pnpm workspaces or Bazel
```

## Build System Evolution Path

### Small Project → Medium → Large

```
Phase 1: Small (1-5 developers, <1k files)
→ Language-native tools (Cargo, go build, npm)
→ Simple Makefiles for C/C++

Phase 2: Medium (5-20 developers, 1-10k files)
→ CMake for C/C++
→ Gradle or Maven for JVM
→ Monorepo with multi-module builds

Phase 3: Large (20-100 developers, 10-100k files)
→ Bazel for polyglot monorepo
→ Remote caching for CI acceleration
→ Hermetic builds for reproducibility

Phase 4: Google-scale (>100 developers, >100k files)
→ Bazel with remote execution
→ Build infrastructure team
→ Custom rules and optimizations
```

## Anti-Patterns

### ❌ Premature Bazel Adoption

```
WRONG: 3-person team, 500 files, pure Java
  → Use Bazel (overkill, months of setup)

CORRECT: 3-person team, 500 files, pure Java
  → Use Maven (days of setup, team expertise)
```

### ❌ Language Mismatch

```
WRONG: Pure Rust project
  → Use CMake (fighting ecosystem)

CORRECT: Pure Rust project
  → Use Cargo (designed for Rust)
```

### ❌ Build System Fragmentation

```
WRONG: Monorepo with 10 different build systems
  → Each team uses own tool
  → Integration nightmare

CORRECT: Monorepo with unified build
  → Bazel or Gradle multi-project
  → Consistent builds across teams
```

### ❌ Not Using Build Cache

```
WRONG: CI rebuilds everything every time
  → 30-minute builds

CORRECT: Enable build cache (Gradle, Bazel)
  → 5-minute incremental builds
```

## Quick Reference

### Build System Selection Table

| Project Profile | Recommended Build System | Runner-Up |
|----------------|-------------------------|-----------|
| C++ cross-platform lib | CMake | Bazel |
| Java microservices | Maven | Gradle |
| Kotlin Android app | Gradle | N/A |
| Rust CLI tool | Cargo | N/A |
| Go web service | go build | N/A |
| Python app | uv | Poetry |
| TypeScript React app | pnpm | Bun |
| Polyglot monorepo | Bazel | Pants |
| 100+ module Java monorepo | Bazel | Gradle |
| Legacy C project | Make | CMake |

### Build System Strengths Summary

**Make**: Ubiquitous, minimal, fast for small C/C++ projects
**CMake**: Cross-platform C/C++, excellent IDE support
**Maven**: Standardized JVM builds, convention over configuration
**Gradle**: Flexible JVM builds, fast incremental, Android
**Bazel**: Large monorepos, hermetic, polyglot, remote cache
**Cargo**: Rust builds, integrated ecosystem
**go build**: Go builds, zero config
**uv**: Python deps, fast, modern
**pnpm**: JavaScript monorepos, efficient

## Python Integration Example

```python
# build_selector.py - Choose build system based on project analysis
import os
import json

def analyze_project():
    """Analyze project to recommend build system."""
    languages = set()

    # Detect languages
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.java'):
                languages.add('java')
            elif file.endswith('.cpp') or file.endswith('.h'):
                languages.add('cpp')
            elif file.endswith('.py'):
                languages.add('python')
            elif file.endswith('.rs'):
                languages.add('rust')

    # Count files
    file_count = sum(len(files) for _, _, files in os.walk('.'))

    # Recommend
    if len(languages) == 1:
        lang = list(languages)[0]
        if lang == 'rust':
            return 'Cargo'
        elif lang == 'python':
            return 'uv'
        elif lang == 'java':
            return 'Maven' if file_count < 10000 else 'Gradle'
        elif lang == 'cpp':
            return 'CMake'
    elif len(languages) > 1:
        return 'Bazel' if file_count > 10000 else 'Language-native + orchestration'

    return 'Unknown'

if __name__ == '__main__':
    print(f"Recommended build system: {analyze_project()}")
```

## Related Skills

- `make-fundamentals.md` - Make syntax and patterns
- `cmake-patterns.md` - CMake configuration
- `gradle-jvm-builds.md` - Gradle for JVM
- `maven-configuration.md` - Maven for Java
- `bazel-monorepos.md` - Bazel for monorepos
- `build-optimization.md` - Build performance
- `cross-platform-builds.md` - Multi-platform strategies

## Summary

Choosing the right build system is critical for long-term project success:

**Key Takeaways**:
1. **Language-native first** - Use Cargo (Rust), go build (Go), uv (Python) when possible
2. **Scale matters** - Small projects: simple tools; Large monorepos: Bazel
3. **Team expertise** - Leverage existing knowledge (Maven → Gradle easier than Maven → Bazel)
4. **Migration cost** - Factor in conversion effort vs benefit
5. **Performance** - Gradle > Maven for JVM; Bazel > all for monorepos with cache
6. **Cross-platform** - CMake best for C/C++; Bazel best for polyglot
7. **Ecosystem** - Maven has largest JVM library ecosystem
8. **Future-proofing** - Choose tools that scale with project growth

**2024 Trends**:
- **uv** displacing pip/Poetry for Python (10-100x faster)
- **Bun** gaining traction for JavaScript (faster than npm/pnpm)
- **Bazel** adoption increasing for large companies (Uber, LinkedIn, Stripe)
- **Gradle** remains dominant for Android, growing for server-side JVM

**Bottom Line**: Start simple, migrate when complexity justifies it. Don't use Bazel for a 3-person team, but don't use Make for a 300-person monorepo.
