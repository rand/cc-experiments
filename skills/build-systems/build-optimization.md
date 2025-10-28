---
name: build-systems-build-optimization
description: Incremental builds, dependency tracking, build caching (ccache, sccache, Bazel), parallel builds, build time profiling, and CI/CD optimization strategies.
---
# Build Optimization

**Last Updated**: 2025-10-26

## When to Use This Skill

Use this skill when:
- Build times are slowing down development velocity
- CI/CD pipelines are taking too long
- Incremental builds are slower than expected
- Team is wasting time waiting for builds
- Large codebase (>10k files) requires optimization
- Remote teams need shared build cache

**Prerequisites**: Understanding of build systems (Make, CMake, Gradle, Bazel), profiling tools

## Core Concepts

### Build Performance Hierarchy

```
Impact (High → Low):
1. Incremental builds (only rebuild changed files)
2. Parallel builds (use all CPU cores)
3. Build caching (local + remote)
4. Precompiled headers (C/C++)
5. Link-time optimization (balance speed vs size)
6. Dependency reduction (fewer deps = faster)
7. Compiler optimization flags (balance speed vs debuggability)
```

### Build Time Breakdown

```
Typical C++ build (100k LOC):
├── Preprocessing:    10% (includes, macros)
├── Parsing:          15% (syntax tree)
├── Template inst:    20% (C++ templates)
├── Optimization:     25% (code generation)
├── Linking:          20% (combine objects)
└── Other:            10% (I/O, overhead)

Python/Java build:
├── Dependency res:   30% (Maven/Gradle)
├── Compilation:      40% (javac, etc.)
├── Testing:          20% (unit tests)
└── Packaging:        10% (JAR/wheel)
```

## Incremental Builds

### Dependency Tracking

#### Make Dependency Generation

```makefile
# Makefile - Automatic dependency tracking
CC := gcc
CFLAGS := -Wall -O2
DEPFLAGS = -MMD -MP

SOURCES := $(wildcard *.c)
OBJECTS := $(SOURCES:.c=.o)
DEPS := $(OBJECTS:.o=.d)

program: $(OBJECTS)
	$(CC) $^ -o $@

# Compile with dependency generation
%.o: %.c
	$(CC) $(CFLAGS) $(DEPFLAGS) -c $< -o $@

# Include generated dependencies
-include $(DEPS)

clean:
	rm -f $(OBJECTS) $(DEPS) program
```

#### CMake Dependency Tracking

```cmake
# CMakeLists.txt - Built-in dependency tracking
add_executable(myapp
    main.cpp
    utils.cpp
    config.cpp
)

# CMake automatically tracks:
# - Source file changes
# - Header file changes (via compiler dependency generation)
# - CMakeLists.txt changes

# Enable faster dependency scanning (CMake 3.16+)
set(CMAKE_DEPENDS_USE_COMPILER TRUE)
```

#### Gradle Incremental Compilation

```kotlin
// build.gradle.kts - Up-to-date checks
tasks.compileJava {
    // Gradle automatically tracks:
    inputs.files(sourceSets.main.get().allSource)
    outputs.dir(sourceSets.main.get().java.classesDirectory)

    // Enable incremental compilation (default in Gradle 7+)
    options.isIncremental = true
}

// Custom task with inputs/outputs
tasks.register<Copy>("processResources") {
    from("src/resources")
    into("$buildDir/resources")

    // Declare inputs/outputs for incremental builds
    inputs.dir("src/resources")
    outputs.dir("$buildDir/resources")
}
```

### Build Avoidance

```bash
# Make - Only rebuild if changed
make                  # Builds only if sources newer than target

# CMake - Detects changes automatically
cmake --build build   # Rebuilds only changed files

# Gradle - Task up-to-date checking
./gradlew build       # Skips up-to-date tasks

# Bazel - Fine-grained caching
bazel build //app     # Rebuilds only affected actions
```

## Parallel Builds

### Make Parallel Builds

```bash
# Use -j flag for parallel jobs
make -j              # Use all CPU cores
make -j8             # Use 8 parallel jobs
make -j$(nproc)      # Use number of CPU cores

# Load average limit
make -j8 -l4         # Max 8 jobs, load average < 4.0
```

```makefile
# Makefile - Optimize for parallelism
# Avoid recursive make (breaks parallelism)

# WRONG: Recursive make
subdirs:
	$(MAKE) -C src
	$(MAKE) -C tests

# CORRECT: Include sub-makefiles
include src/Makefile
include tests/Makefile
```

### CMake Parallel Builds

```bash
# Parallel build with CMake
cmake --build build -j8          # 8 parallel jobs
cmake --build build --parallel   # Use all cores

# Ninja (faster than Make)
cmake -G Ninja ..
ninja -j8
```

```cmake
# CMakeLists.txt - Optimize for parallelism
# Use OBJECT libraries to avoid rebuilding common code
add_library(common OBJECT common.cpp utils.cpp)

add_executable(app1 app1.cpp)
target_link_libraries(app1 PRIVATE common)

add_executable(app2 app2.cpp)
target_link_libraries(app2 PRIVATE common)

# common.cpp compiled once, linked into both executables
```

### Gradle Parallel Builds

```bash
# Enable parallel execution
./gradlew build --parallel

# Configure max workers
./gradlew build --max-workers=8
```

```properties
# gradle.properties - Enable by default
org.gradle.parallel=true
org.gradle.workers.max=8
```

### Bazel Parallel Builds

```bash
# Bazel parallelizes automatically
bazel build //...

# Control parallelism
bazel build //... --jobs=8
bazel build //... --local_ram_resources=4096  # MB
bazel build //... --local_cpu_resources=8
```

## Build Caching

### ccache (C/C++)

```bash
# Install ccache
sudo apt install ccache         # Linux
brew install ccache             # macOS

# Configure
ccache --max-size=10G
ccache --set-config=compression=true

# Use with Make
export CC="ccache gcc"
export CXX="ccache g++"
make

# Use with CMake
cmake -DCMAKE_C_COMPILER_LAUNCHER=ccache \
      -DCMAKE_CXX_COMPILER_LAUNCHER=ccache ..

# Stats
ccache -s
ccache --show-stats

# Clean cache
ccache --clear
```

```cmake
# CMakeLists.txt - Automatic ccache detection
find_program(CCACHE_PROGRAM ccache)
if(CCACHE_PROGRAM)
    set(CMAKE_C_COMPILER_LAUNCHER "${CCACHE_PROGRAM}")
    set(CMAKE_CXX_COMPILER_LAUNCHER "${CCACHE_PROGRAM}")
    message(STATUS "Using ccache: ${CCACHE_PROGRAM}")
endif()
```

### sccache (Multi-Language)

```bash
# Install sccache (Rust-based, supports C++, Rust, Python)
cargo install sccache

# Configure
export SCCACHE_DIR=~/.cache/sccache
export SCCACHE_CACHE_SIZE="10G"

# Use with CMake
export CMAKE_C_COMPILER_LAUNCHER=sccache
export CMAKE_CXX_COMPILER_LAUNCHER=sccache

# Use with Cargo
export RUSTC_WRAPPER=sccache

# Remote cache (S3, Redis, etc.)
export SCCACHE_BUCKET=my-build-cache
export SCCACHE_REGION=us-west-2

# Stats
sccache --show-stats
```

### Gradle Build Cache

```bash
# Enable build cache
./gradlew build --build-cache
```

```properties
# gradle.properties - Enable by default
org.gradle.caching=true
```

```kotlin
// build.gradle.kts - Remote build cache
buildCache {
    local {
        isEnabled = true
        directory = file("$rootDir/.gradle/build-cache")
    }

    remote<HttpBuildCache> {
        url = uri("https://cache.example.com")
        isPush = System.getenv("CI") == "true"  // Only push from CI
        credentials {
            username = System.getenv("CACHE_USER")
            password = System.getenv("CACHE_PASS")
        }
    }
}
```

### Bazel Remote Cache

```bash
# Local disk cache
bazel build //... --disk_cache=~/.cache/bazel
```

```bash
# .bazelrc - Remote cache configuration
build --remote_cache=https://cache.example.com
build --remote_upload_local_results=true

# Google Cloud Storage
build --remote_cache=https://storage.googleapis.com/my-bazel-cache
build --google_default_credentials

# Authentication
build --remote_header=Authorization=Bearer TOKEN
```

### Remote Build Execution

```bash
# Bazel remote execution (BuildBarn, BuildBuddy, etc.)
bazel build //... \
    --remote_executor=grpcs://remotebuildexecution.googleapis.com \
    --remote_instance_name=projects/my-project/instances/default

# BuildBuddy (open source)
bazel build //... --remote_cache=grpcs://remote.buildbuddy.io \
    --remote_header=x-buildbuddy-api-key=YOUR_KEY
```

## Precompiled Headers (C/C++)

### CMake Precompiled Headers

```cmake
# CMakeLists.txt - Precompiled headers (CMake 3.16+)
add_library(mylib src/lib.cpp)

# Add precompiled headers
target_precompile_headers(mylib PRIVATE
    <vector>
    <string>
    <iostream>
    <algorithm>
    "common.h"
    "utils.h"
)

# Reuse across targets
add_executable(myapp main.cpp)
target_precompile_headers(myapp REUSE_FROM mylib)
```

**Impact**: 20-40% faster builds for header-heavy C++ projects

### Manual Precompiled Headers

```bash
# GCC/Clang - Generate PCH
g++ -x c++-header common.h -o common.h.gch

# Use PCH
g++ main.cpp -include common.h -o main
```

## Link-Time Optimization (LTO)

### CMake LTO Configuration

```cmake
# CMakeLists.txt - Enable LTO
set(CMAKE_INTERPROCEDURAL_OPTIMIZATION TRUE)

# Or per-target
add_executable(myapp main.cpp)
set_target_properties(myapp PROPERTIES
    INTERPROCEDURAL_OPTIMIZATION TRUE
)

# Or per-configuration
set(CMAKE_INTERPROCEDURAL_OPTIMIZATION_RELEASE TRUE)
```

**Trade-off**: 10-20% smaller binaries, 2-3x slower link time

### Selective LTO

```cmake
# Enable LTO only for Release builds
if(CMAKE_BUILD_TYPE STREQUAL "Release")
    set(CMAKE_INTERPROCEDURAL_OPTIMIZATION TRUE)
endif()
```

## Build Time Profiling

### CMake Build Time Analysis

```bash
# Verbose build output
cmake --build build --verbose

# Time individual commands
cmake --build build -- VERBOSE=1 2>&1 | ts -i '%.s'

# Ninja build time trace
cmake -G Ninja ..
ninja -d stats       # Build statistics
ninja -d explain     # Explain why targets rebuild
```

### Gradle Build Profiling

```bash
# Generate build profile
./gradlew build --profile

# Output: build/reports/profile/profile-<timestamp>.html

# Build scan (detailed insights)
./gradlew build --scan
```

### Bazel Build Profiling

```bash
# Generate profile
bazel build //... --profile=profile.json

# Analyze profile
bazel analyze-profile profile.json

# JSON output for custom analysis
bazel analyze-profile profile.json --dump=json > analysis.json
```

```python
# analyze_bazel_profile.py
import json

with open('profile.json') as f:
    profile = json.load(f)

# Find slow actions
actions = [(event['dur'], event['name'])
           for event in profile['traceEvents']
           if event.get('ph') == 'X']

slowest = sorted(actions, reverse=True)[:10]
for duration, name in slowest:
    print(f"{duration/1000:.2f}ms - {name}")
```

### Clang Build Time Tracing

```bash
# Clang -ftime-trace (Clang 9+)
clang++ -ftime-trace main.cpp -o main

# Generates main.json (Chrome trace format)
# View in chrome://tracing
```

## CI/CD Optimization

### GitHub Actions Build Optimization

```yaml
# .github/workflows/optimized.yml
name: Optimized Build

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      # Cache dependencies
      - name: Cache Gradle
        uses: actions/cache@v4
        with:
          path: |
            ~/.gradle/caches
            ~/.gradle/wrapper
          key: ${{ runner.os }}-gradle-${{ hashFiles('**/*.gradle*') }}

      # ccache for C/C++
      - name: Setup ccache
        uses: hendrikmuhs/ccache-action@v1
        with:
          key: ${{ runner.os }}-ccache

      # Parallel build
      - name: Build
        run: |
          cmake -DCMAKE_C_COMPILER_LAUNCHER=ccache \
                -DCMAKE_CXX_COMPILER_LAUNCHER=ccache ..
          cmake --build . --parallel

      # Upload build artifacts (for dependent jobs)
      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: build-artifacts
          path: build/
```

### Docker Build Optimization

```dockerfile
# Dockerfile - Multi-stage builds with caching
FROM rust:1.75 AS builder

# Cache dependencies separately (changes less often)
WORKDIR /app
COPY Cargo.toml Cargo.lock ./
RUN mkdir src && echo "fn main() {}" > src/main.rs && \
    cargo build --release && \
    rm -rf src  # Safe: cleaning temporary build directory

# Build actual code (changes more often)
COPY src ./src
RUN touch src/main.rs && cargo build --release

# Final image (minimal)
FROM debian:bookworm-slim
COPY --from=builder /app/target/release/myapp /usr/local/bin/
CMD ["myapp"]
```

```bash
# Use BuildKit for better caching
DOCKER_BUILDKIT=1 docker build -t myapp .

# Remote cache
docker buildx build \
    --cache-from type=registry,ref=myregistry/cache \
    --cache-to type=registry,ref=myregistry/cache,mode=max \
    -t myapp .
```

### Bazel Remote Cache in CI

```yaml
# .github/workflows/bazel-ci.yml
- name: Build with Bazel
  run: |
    bazel build //... \
      --remote_cache=https://storage.googleapis.com/${{ secrets.GCS_BUCKET }} \
      --google_default_credentials \
      --jobs=8
```

## Dependency Optimization

### Reduce Header Dependencies (C/C++)

```cpp
// WRONG: Include entire header in .h file
// mylib.h
#include <vector>
#include <string>
#include <map>

class MyLib {
    std::vector<std::string> data;
    std::map<int, std::string> lookup;
};

// CORRECT: Forward declarations in .h, includes in .cpp
// mylib.h
#include <iosfwd>  // Forward declarations for std streams

class MyLib {
    class Impl;  // Pimpl idiom
    Impl* pimpl;
};

// mylib.cpp
#include "mylib.h"
#include <vector>
#include <string>
#include <map>

// Full implementation with includes
```

**Impact**: 30-50% faster incremental builds (fewer recompilations)

### Gradle Dependency Analysis

```bash
# Find unused dependencies
./gradlew dependencies --configuration compileClasspath

# Dependency insight
./gradlew dependencyInsight --dependency guava

# Build scan shows dependency resolution time
./gradlew build --scan
```

## Compiler Optimization Flags

### Development vs Production Builds

```cmake
# CMakeLists.txt - Build type flags
set(CMAKE_CXX_FLAGS_DEBUG "-g -O0")           # Fast compile, slow runtime
set(CMAKE_CXX_FLAGS_RELEASE "-O3 -DNDEBUG")   # Slow compile, fast runtime
set(CMAKE_CXX_FLAGS_RELWITHDEBINFO "-O2 -g")  # Balanced
```

```makefile
# Makefile - Conditional optimization
DEBUG ?= 0

ifeq ($(DEBUG), 1)
    CFLAGS = -g -O0              # Fast build
else
    CFLAGS = -O2 -DNDEBUG        # Optimized
endif
```

### Distributed Compilation

#### distcc (C/C++)

```bash
# Setup distcc
sudo apt install distcc

# Configure
export DISTCC_HOSTS="localhost/8 remote1/4 remote2/4"
export CC="distcc gcc"
export CXX="distcc g++"

# Build
make -j16  # More jobs than local cores
```

#### icecc (icecream)

```bash
# Install icecc
sudo apt install icecc

# Use with CMake
export CC="icecc gcc"
export CXX="icecc g++"

cmake -DCMAKE_C_COMPILER_LAUNCHER=icecc \
      -DCMAKE_CXX_COMPILER_LAUNCHER=icecc ..
```

## Anti-Patterns

### ❌ Not Using Build Cache

```bash
# WRONG: Clean build every time in CI
./gradlew clean build  # Wastes 90% of build time

# CORRECT: Incremental build with cache
./gradlew build --build-cache
```

### ❌ Sequential Builds

```bash
# WRONG: Single-threaded build
make

# CORRECT: Parallel build
make -j$(nproc)
```

### ❌ Overly Aggressive Optimization in Development

```cmake
# WRONG: Always use -O3 (slow compilation)
set(CMAKE_CXX_FLAGS "-O3")

# CORRECT: Use -O0 or -O1 for development
if(CMAKE_BUILD_TYPE STREQUAL "Debug")
    set(CMAKE_CXX_FLAGS "-O0 -g")
endif()
```

### ❌ Not Profiling Builds

```bash
# WRONG: Blindly add optimizations without measuring
# "I think this will help"

# CORRECT: Profile first, optimize second
bazel build //... --profile=profile.json
bazel analyze-profile profile.json
# Identify actual bottlenecks, then optimize
```

## Quick Reference

### Build Optimization Checklist

```
[ ] Enable incremental builds (dependency tracking)
[ ] Use parallel builds (-j flag)
[ ] Enable build cache (ccache, sccache, Gradle, Bazel)
[ ] Use precompiled headers (C/C++)
[ ] Reduce header dependencies (forward declarations)
[ ] Profile build times (identify bottlenecks)
[ ] Use faster build generator (Ninja vs Make)
[ ] Enable remote caching (team/CI)
[ ] Optimize CI (cache dependencies, parallel jobs)
[ ] Use LTO only for release builds
[ ] Consider distributed compilation (large teams)
```

### Expected Speedups

| Optimization | Speedup (Incremental) | Speedup (Clean) |
|--------------|----------------------|-----------------|
| Parallel builds (8 cores) | 2-4x | 4-6x |
| ccache/sccache | 10-50x | 5-10x |
| Precompiled headers | 1.2-1.4x | 1.2-1.4x |
| Ninja vs Make | 1.1-1.3x | 1.1-1.3x |
| Remote cache (Bazel) | 10-100x | 5-20x |
| Dependency reduction | 1.5-3x | 1.1-1.2x |

### Build Tool Performance (2024)

**C/C++ Build Systems** (100k LOC project):
- Make (single-thread): 120s
- Make (-j8): 30s
- CMake + Ninja (-j8): 25s
- CMake + Ninja + ccache: 5s (incremental)
- Bazel + remote cache: 2s (incremental, cache hit)

**JVM Build Systems** (50k LOC project):
- Maven: 90s
- Gradle: 60s (cold)
- Gradle (daemon + cache): 10s (incremental)
- Bazel + remote cache: 5s (incremental)

## Python Integration Example

```python
# build_profiler.py - Analyze build performance
import json
import sys
from collections import defaultdict

def analyze_build_profile(profile_path):
    """Analyze Bazel build profile JSON."""
    with open(profile_path) as f:
        profile = json.load(f)

    # Aggregate by action type
    by_type = defaultdict(lambda: {'count': 0, 'total_ms': 0})

    for event in profile['traceEvents']:
        if event.get('ph') == 'X':  # Duration event
            name = event.get('name', 'unknown')
            duration_ms = event.get('dur', 0) / 1000

            # Extract action type (e.g., "CppCompile")
            action_type = name.split()[0] if ' ' in name else name

            by_type[action_type]['count'] += 1
            by_type[action_type]['total_ms'] += duration_ms

    # Sort by total time
    sorted_types = sorted(by_type.items(),
                          key=lambda x: x[1]['total_ms'],
                          reverse=True)

    print("Build Performance Summary")
    print("=" * 60)
    for action_type, stats in sorted_types[:10]:
        avg_ms = stats['total_ms'] / stats['count']
        print(f"{action_type:20s} | {stats['count']:5d} actions | "
              f"{stats['total_ms']:8.1f}ms total | {avg_ms:6.1f}ms avg")

if __name__ == '__main__':
    analyze_build_profile(sys.argv[1])

# Usage: python build_profiler.py profile.json
```

## Related Skills

- `make-fundamentals.md` - Make parallelization and optimization
- `cmake-patterns.md` - CMake precompiled headers and caching
- `gradle-jvm-builds.md` - Gradle build cache and optimization
- `bazel-monorepos.md` - Bazel remote caching and execution
- `cicd/ci-optimization.md` - CI/CD build optimization strategies

## Summary

Build optimization is critical for developer productivity and CI/CD efficiency:

**Key Takeaways**:
1. **Incremental builds** - Only rebuild what changed (biggest impact)
2. **Parallel builds** - Use all CPU cores with `-j` flag
3. **Build caching** - Local (ccache) and remote (Bazel, Gradle)
4. **Precompiled headers** - 20-40% faster C++ builds
5. **Profile first** - Measure before optimizing
6. **Dependency reduction** - Fewer includes = faster incremental builds
7. **CI optimization** - Cache dependencies, use build cache, parallelize
8. **Development speed** - Use `-O0` or `-O1` for faster iteration

**2024 Best Practices**:
- **C/C++**: CMake + Ninja + ccache/sccache + PCH
- **Java**: Gradle with build cache + parallel execution
- **Rust**: Cargo with sccache
- **Monorepo**: Bazel with remote cache/execution

**Impact**: Proper build optimization can reduce build times from hours to minutes, dramatically improving developer velocity and CI/CD efficiency.

**ROI**: For a 10-person team waiting 10 minutes/day for builds, optimization to 1 minute saves ~750 hours/year.
