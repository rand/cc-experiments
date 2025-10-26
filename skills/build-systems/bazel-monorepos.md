---
name: build-systems-bazel-monorepos
description: Bazel BUILD files, WORKSPACE/MODULE.bazel, hermetic builds, remote caching, build rules, Starlark custom rules, and monorepo best practices for polyglot projects.
---
# Bazel Monorepos

**Last Updated**: 2025-10-26

## When to Use This Skill

Use this skill when:
- Managing large-scale polyglot monorepos (multiple languages)
- Requiring hermetic, reproducible builds
- Needing fast incremental builds with remote caching
- Building projects with complex dependency graphs
- Targeting multiple platforms from single codebase
- Working at Google-scale (Bazel powers Google's internal build)

**Alternatives**: Gradle (JVM), CMake (C/C++), Cargo (Rust), language-specific tools

**Prerequisites**: Bazel 7.0+ installed (7.4.1 latest as of 2024), Bazelisk (version manager)

## Core Concepts

### Bazel Philosophy

```
Hermetic:     All dependencies explicit, no network during build
Incremental:  Only rebuild what changed (fine-grained)
Parallel:     Maximize parallelization across cores
Cacheable:    Remote cache for team-wide sharing
Polyglot:     Unified build for Java, C++, Python, Go, etc.
```

### Bazelisk (Recommended)

```bash
# Install Bazelisk (manages Bazel versions)
# macOS
brew install bazelisk

# Linux
wget https://github.com/bazelbuild/bazelisk/releases/latest/download/bazelisk-linux-amd64
chmod +x bazelisk-linux-amd64
sudo mv bazelisk-linux-amd64 /usr/local/bin/bazel

# Bazelisk reads .bazelversion for project-specific version
echo "7.4.1" > .bazelversion

# Use bazel command (Bazelisk transparently handles version)
bazel version
```

### Project Structure

```
monorepo/
├── WORKSPACE.bazel         # Workspace config (legacy)
├── MODULE.bazel            # Module config (Bazel 6.0+, bzlmod)
├── .bazelversion           # Bazel version (for Bazelisk)
├── .bazelrc                # Build configuration
├── java/
│   ├── BUILD.bazel         # Build rules for Java code
│   └── com/example/
│       └── Main.java
├── cpp/
│   ├── BUILD.bazel
│   └── lib.cc
├── python/
│   ├── BUILD.bazel
│   └── app.py
└── proto/
    ├── BUILD.bazel
    └── service.proto
```

## WORKSPACE and MODULE Files

### WORKSPACE.bazel (Legacy)

```python
# WORKSPACE.bazel - Legacy dependency management
workspace(name = "my_project")

# HTTP archive (external dependency)
load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

http_archive(
    name = "rules_java",
    urls = ["https://github.com/bazelbuild/rules_java/archive/refs/tags/6.0.0.tar.gz"],
    sha256 = "...",
)

http_archive(
    name = "rules_python",
    urls = ["https://github.com/bazelbuild/rules_python/releases/download/0.27.0/rules_python-0.27.0.tar.gz"],
    sha256 = "...",
)

# Load rules
load("@rules_java//java:repositories.bzl", "rules_java_dependencies", "rules_java_toolchains")
rules_java_dependencies()
rules_java_toolchains()

load("@rules_python//python:repositories.bzl", "py_repositories")
py_repositories()
```

### MODULE.bazel (Bzlmod, Bazel 6.0+)

```python
# MODULE.bazel - Modern dependency management
module(
    name = "my_project",
    version = "1.0.0",
)

# Bazel Central Registry dependencies
bazel_dep(name = "rules_java", version = "6.0.0")
bazel_dep(name = "rules_python", version = "0.27.0")
bazel_dep(name = "rules_cc", version = "0.0.9")
bazel_dep(name = "protobuf", version = "24.4")

# Maven dependencies (Java)
maven = use_extension("@rules_jvm_external//:extensions.bzl", "maven")
maven.install(
    artifacts = [
        "com.google.guava:guava:32.1.3-jre",
        "org.junit.jupiter:junit-jupiter:5.10.0",
    ],
    repositories = [
        "https://repo.maven.apache.org/maven2",
    ],
)
use_repo(maven, "maven")

# Python dependencies
pip = use_extension("@rules_python//python:extensions.bzl", "pip")
pip.parse(
    hub_name = "pip",
    python_version = "3.11",
    requirements_lock = "//:requirements_lock.txt",
)
use_repo(pip, "pip")
```

## BUILD Files

### Java Build Rules

```python
# java/BUILD.bazel
load("@rules_java//java:defs.bzl", "java_binary", "java_library", "java_test")

# Library
java_library(
    name = "utils",
    srcs = glob(["com/example/utils/*.java"]),
    deps = [
        "@maven//:com_google_guava_guava",
    ],
    visibility = ["//visibility:public"],
)

# Binary (executable)
java_binary(
    name = "app",
    srcs = ["com/example/Main.java"],
    main_class = "com.example.Main",
    deps = [
        ":utils",
        "//proto:service_java_proto",
    ],
)

# Test
java_test(
    name = "utils_test",
    srcs = glob(["com/example/utils/*Test.java"]),
    test_class = "com.example.utils.UtilsTest",
    deps = [
        ":utils",
        "@maven//:org_junit_jupiter_junit_jupiter",
    ],
)
```

### C++ Build Rules

```python
# cpp/BUILD.bazel
load("@rules_cc//cc:defs.bzl", "cc_binary", "cc_library", "cc_test")

# Library
cc_library(
    name = "mylib",
    srcs = ["lib.cc"],
    hdrs = ["lib.h"],
    deps = [
        "@com_google_absl//absl/strings",
    ],
    visibility = ["//visibility:public"],
)

# Binary
cc_binary(
    name = "app",
    srcs = ["main.cc"],
    deps = [":mylib"],
)

# Test
cc_test(
    name = "mylib_test",
    srcs = ["lib_test.cc"],
    deps = [
        ":mylib",
        "@com_google_googletest//:gtest_main",
    ],
)
```

### Python Build Rules

```python
# python/BUILD.bazel
load("@rules_python//python:defs.bzl", "py_binary", "py_library", "py_test")

# Library
py_library(
    name = "utils",
    srcs = ["utils.py"],
    deps = [
        "@pip//numpy",
    ],
    visibility = ["//visibility:public"],
)

# Binary
py_binary(
    name = "app",
    srcs = ["app.py"],
    main = "app.py",
    deps = [
        ":utils",
        "//proto:service_py_proto",
    ],
)

# Test
py_test(
    name = "utils_test",
    srcs = ["utils_test.py"],
    deps = [
        ":utils",
        "@pip//pytest",
    ],
)
```

### Protobuf Build Rules

```python
# proto/BUILD.bazel
load("@rules_proto//proto:defs.bzl", "proto_library")
load("@rules_java//java:defs.bzl", "java_proto_library")
load("@rules_python//python:proto.bzl", "py_proto_library")

# Proto definition
proto_library(
    name = "service_proto",
    srcs = ["service.proto"],
    visibility = ["//visibility:public"],
)

# Java proto
java_proto_library(
    name = "service_java_proto",
    deps = [":service_proto"],
    visibility = ["//visibility:public"],
)

# Python proto
py_proto_library(
    name = "service_py_proto",
    deps = [":service_proto"],
    visibility = ["//visibility:public"],
)
```

## Build Configuration

### .bazelrc

```bash
# .bazelrc - Build configuration
# Common flags
build --enable_platform_specific_config
build --incompatible_strict_action_env
build --verbose_failures

# Performance
build --jobs=8
build --local_ram_resources=HOST_RAM*.5
build --remote_cache=https://cache.example.com

# Output
build --show_timestamps
build --color=yes

# Java
build --java_runtime_version=remotejdk_11
build --tool_java_runtime_version=remotejdk_11

# C++
build:linux --cxxopt=-std=c++17
build:macos --cxxopt=-std=c++17

# Test
test --test_output=errors
test --test_summary=detailed

# Platform-specific (auto-selected)
build:linux --copt=-DLINUX
build:macos --copt=-DMACOS
build:windows --copt=/DWINDOWS
```

## Remote Caching

### Local Cache

```bash
# Enable disk cache (default ~/.cache/bazel)
build --disk_cache=~/.cache/bazel
```

### Remote Cache (HTTP)

```bash
# .bazelrc
build --remote_cache=https://cache.example.com
build --remote_upload_local_results=true

# Or use Google Cloud Storage
build --remote_cache=https://storage.googleapis.com/my-bazel-cache
build --google_default_credentials
```

### Remote Execution (Advanced)

```bash
# Remote build execution (RBE)
build --remote_executor=grpcs://remotebuildexecution.googleapis.com
build --remote_instance_name=projects/my-project/instances/default_instance
build --google_default_credentials
```

## Custom Rules (Starlark)

### Simple Custom Rule

```python
# rules/custom.bzl
def _my_rule_impl(ctx):
    """Implementation function for my_rule."""
    # Access attributes
    input_file = ctx.file.src
    output_file = ctx.actions.declare_file(ctx.label.name + ".out")

    # Run action
    ctx.actions.run_shell(
        inputs = [input_file],
        outputs = [output_file],
        command = "cat {} > {}".format(input_file.path, output_file.path),
    )

    # Return provider
    return [DefaultInfo(files = depset([output_file]))]

# Define rule
my_rule = rule(
    implementation = _my_rule_impl,
    attrs = {
        "src": attr.label(allow_single_file = True, mandatory = True),
    },
)
```

```python
# BUILD.bazel - Use custom rule
load("//rules:custom.bzl", "my_rule")

my_rule(
    name = "processed",
    src = "input.txt",
)
```

### Advanced Custom Rule

```python
# rules/code_gen.bzl
def _code_gen_impl(ctx):
    """Generate code from template."""
    template = ctx.file.template
    output = ctx.actions.declare_file(ctx.attr.output_name)

    # Run Python script
    ctx.actions.run(
        executable = ctx.executable._generator,
        arguments = [
            "--template", template.path,
            "--output", output.path,
            "--config", ctx.attr.config,
        ],
        inputs = [template],
        outputs = [output],
        mnemonic = "CodeGen",
        progress_message = "Generating code from {}".format(template.short_path),
    )

    return [DefaultInfo(files = depset([output]))]

code_gen = rule(
    implementation = _code_gen_impl,
    attrs = {
        "template": attr.label(allow_single_file = [".tpl"], mandatory = True),
        "output_name": attr.string(mandatory = True),
        "config": attr.string(default = "default"),
        "_generator": attr.label(
            default = Label("//tools:generator"),
            executable = True,
            cfg = "exec",
        ),
    },
)
```

## Monorepo Best Practices

### Visibility Control

```python
# Restrict visibility
java_library(
    name = "internal_utils",
    srcs = ["Utils.java"],
    visibility = ["//java:__subpackages__"],  # Only java/ subtree
)

# Public visibility
java_library(
    name = "public_api",
    srcs = ["Api.java"],
    visibility = ["//visibility:public"],  # Entire workspace
)

# Package group
package_group(
    name = "backend_team",
    packages = [
        "//backend/...",
        "//common/...",
    ],
)

java_library(
    name = "backend_lib",
    srcs = ["BackendLib.java"],
    visibility = [":backend_team"],
)
```

### Glob Patterns

```python
# Glob source files
java_library(
    name = "lib",
    srcs = glob(["src/**/*.java"]),
    resources = glob(["resources/**/*"]),
)

# Exclude patterns
java_library(
    name = "lib",
    srcs = glob(
        ["**/*.java"],
        exclude = ["**/*Test.java", "**/testdata/**"],
    ),
)
```

### Macros for Reusability

```python
# macros/java.bzl
def java_module(name, srcs, deps = [], **kwargs):
    """Standard Java module with library and test."""
    native.java_library(
        name = name,
        srcs = srcs,
        deps = deps,
        **kwargs
    )

    native.java_test(
        name = name + "_test",
        srcs = native.glob([name + "/**/*Test.java"]),
        deps = [
            ":" + name,
            "@maven//:org_junit_jupiter_junit_jupiter",
        ] + deps,
        **kwargs
    )
```

```python
# BUILD.bazel
load("//macros:java.bzl", "java_module")

java_module(
    name = "utils",
    srcs = glob(["utils/**/*.java"]),
    deps = ["@maven//:com_google_guava_guava"],
)
```

## Performance Optimization

### Query Dependencies

```bash
# Show dependency graph
bazel query --output=graph //java/... > graph.dot

# Find dependencies
bazel query "deps(//java:app)"

# Reverse dependencies (what depends on X)
bazel query "rdeps(//..., //java:utils)"

# Find test targets
bazel query "tests(//java/...)"
```

### Build Analysis

```bash
# Profile build
bazel build //java:app --profile=profile.json

# View profile
bazel analyze-profile profile.json

# Show action timing
bazel build //java:app --experimental_show_artifacts --experimental_profile_cpu_usage
```

### Incremental Builds

```bash
# Bazel automatically detects changes
# Only rebuilds affected targets

# Force rebuild
bazel clean
bazel build //...

# Or specific target
bazel clean --expunge  # Nuclear option (clears all caches)
```

## Anti-Patterns

### ❌ Not Using Hermetic Builds

```python
# WRONG: External system dependency
genrule(
    name = "bad",
    outs = ["output.txt"],
    cmd = "curl https://example.com/data > $@",  # Network access!
)

# CORRECT: Explicit dependency
http_file(
    name = "data",
    urls = ["https://example.com/data"],
    sha256 = "...",
)

genrule(
    name = "good",
    srcs = ["@data//file"],
    outs = ["output.txt"],
    cmd = "cp $< $@",
)
```

### ❌ Overly Broad Globs

```python
# WRONG: Too broad, includes unintended files
srcs = glob(["**/*.java"])

# CORRECT: Specific patterns
srcs = glob(
    ["src/**/*.java"],
    exclude = [
        "**/*Test.java",
        "**/testdata/**",
        "**/generated/**",
    ],
)
```

### ❌ Not Pinning Versions

```python
# WRONG: Unpinned version (non-reproducible)
http_archive(
    name = "rules_java",
    urls = ["https://github.com/bazelbuild/rules_java/archive/refs/heads/main.zip"],
)

# CORRECT: Pinned version with SHA
http_archive(
    name = "rules_java",
    urls = ["https://github.com/bazelbuild/rules_java/archive/refs/tags/6.0.0.tar.gz"],
    sha256 = "469b7f3b580b4fcf8112f4d6eb3e3d8239ef05f68a33e2c3c4f23d3a4e286994",
)
```

## Quick Reference

### Essential Bazel Commands

```bash
# Build
bazel build //java:app                # Build target
bazel build //java/...                # Build all in java/
bazel build //...                     # Build entire workspace

# Test
bazel test //java:app_test            # Run single test
bazel test //java/...                 # Run all tests in java/
bazel test //... --test_output=all    # Verbose test output

# Run
bazel run //java:app                  # Build and run binary

# Clean
bazel clean                           # Clean build outputs
bazel clean --expunge                 # Nuclear clean (all caches)

# Query
bazel query //java/...                # List targets
bazel query "deps(//java:app)"        # Show dependencies
bazel query "rdeps(//..., //java:lib)" # Reverse dependencies

# Info
bazel info                            # Show workspace info
bazel version                         # Bazel version
```

### Target Labels

```
//package:target              # Absolute label
//package                     # Short form (target = package name)
:target                       # Relative to current package
//...                         # All targets in workspace
//package/...                 # All targets under package/
@repo//package:target         # External repository
```

## Bazel vs Gradle Performance (2024 Data)

**Build Performance** (Google internal data, 2024):
- **Cold build**: Bazel ~15% slower (hermetic sandboxing overhead)
- **Incremental build**: Bazel 3-5x faster (fine-grained caching)
- **Multi-language**: Bazel scales better (unified graph)
- **Remote cache**: Bazel superior (built-in, action-level granularity)

**When Bazel Excels**:
- Large monorepos (>100k files)
- Polyglot projects (Java + C++ + Python)
- Multiple teams sharing cache
- Strict reproducibility requirements

**When Gradle Excels**:
- Pure JVM projects
- Smaller codebases (<50k files)
- Flexible build logic needed
- Android development (Gradle is default)

## Python Integration Example

```python
# tools/generator.py - Custom code generator
import argparse

def generate(template_path, output_path, config):
    with open(template_path) as f:
        template = f.read()

    # Process template (simplified)
    code = template.replace("{{CONFIG}}", config)

    with open(output_path, 'w') as f:
        f.write(code)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--config", default="default")
    args = parser.parse_args()

    generate(args.template, args.output, args.config)
```

```python
# tools/BUILD.bazel
py_binary(
    name = "generator",
    srcs = ["generator.py"],
    visibility = ["//visibility:public"],
)
```

## Related Skills

- `build-system-selection.md` - Choosing between build systems
- `gradle-jvm-builds.md` - Alternative for JVM projects
- `cmake-patterns.md` - Alternative for C/C++ projects
- `build-optimization.md` - Caching and performance
- `cicd/ci-optimization.md` - Bazel in CI pipelines

## Summary

Bazel is Google's open-source build system designed for massive monorepos with hermetic, reproducible builds:

**Key Takeaways**:
1. **Hermetic builds** - All dependencies explicit, no network during build
2. **Fine-grained caching** - Action-level caching for fast incremental builds
3. **Remote cache/execution** - Share build artifacts across team/CI
4. **Polyglot support** - Unified build for Java, C++, Python, Go, etc.
5. **Bzlmod** - Modern dependency management (Bazel 6.0+)
6. **Starlark rules** - Extend Bazel with custom build logic
7. **Visibility control** - Enforce module boundaries
8. **Incremental by default** - Only rebuild what changed

**When to Choose Bazel**:
- Large monorepos (Google, Uber, LinkedIn scale)
- Multiple languages in single codebase
- Strict reproducibility requirements
- Need for remote caching/execution

**When to Choose Alternatives**:
- Small projects (setup overhead not justified)
- Pure JVM (Gradle simpler)
- Pure C/C++ (CMake more familiar)
- Rapid prototyping (Bazel has learning curve)

Bazel excels at scale but requires investment in learning and setup. For projects expecting to grow to Google-scale complexity, the investment pays off.
