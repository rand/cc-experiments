---
name: build-systems-gradle-jvm-builds
description: Gradle Kotlin DSL and Groovy DSL, dependency management, version catalogs, build lifecycle, task configuration, multi-project builds, and performance optimization for Java/Kotlin projects.
---
# Gradle JVM Builds

**Last Updated**: 2025-10-26

## When to Use This Skill

Use this skill when:
- Building Java, Kotlin, Scala, or Groovy projects
- Managing multi-module JVM applications
- Creating Android applications (Gradle is default)
- Needing flexible, programmable build logic
- Requiring dependency version management across modules
- Migrating from Maven or Ant

**Alternatives**: Maven (convention over configuration), Bazel (monorepos), sbt (Scala)

**Prerequisites**: JDK 11+ installed, Gradle 8.0+ (8.10 latest as of 2024)

## Core Concepts

### Gradle Wrapper (Recommended)

```bash
# Initialize project with wrapper
gradle init --type java-application --dsl kotlin

# Use wrapper (ensures consistent Gradle version)
./gradlew build        # Unix/macOS
gradlew.bat build      # Windows

# Upgrade wrapper
./gradlew wrapper --gradle-version 8.10
```

### Kotlin DSL vs Groovy DSL

**Kotlin DSL (build.gradle.kts)** - Recommended for new projects:
```kotlin
// Type-safe, IDE support, refactoring
plugins {
    kotlin("jvm") version "1.9.24"
    application
}

repositories {
    mavenCentral()
}

dependencies {
    implementation("com.google.guava:guava:32.1.3-jre")
    testImplementation(kotlin("test"))
}

application {
    mainClass.set("com.example.AppKt")
}

tasks.test {
    useJUnitPlatform()
}
```

**Groovy DSL (build.gradle)** - Legacy, but still common:
```groovy
plugins {
    id 'org.jetbrains.kotlin.jvm' version '1.9.24'
    id 'application'
}

repositories {
    mavenCentral()
}

dependencies {
    implementation 'com.google.guava:guava:32.1.3-jre'
    testImplementation 'org.jetbrains.kotlin:kotlin-test'
}

application {
    mainClass = 'com.example.AppKt'
}

test {
    useJUnitPlatform()
}
```

### Project Structure

```
project/
├── gradle/
│   └── wrapper/
│       ├── gradle-wrapper.jar
│       └── gradle-wrapper.properties
├── gradlew              # Unix wrapper script
├── gradlew.bat          # Windows wrapper script
├── settings.gradle.kts  # Project settings
├── build.gradle.kts     # Root build file
├── gradle.properties    # Build properties
└── src/
    ├── main/
    │   ├── java/
    │   ├── kotlin/
    │   └── resources/
    └── test/
        ├── java/
        ├── kotlin/
        └── resources/
```

## Dependency Management

### Dependency Configurations

```kotlin
// build.gradle.kts
dependencies {
    // Compile and runtime
    implementation("org.slf4j:slf4j-api:2.0.9")

    // Compile only (not in runtime classpath)
    compileOnly("org.projectlombok:lombok:1.18.30")

    // Runtime only
    runtimeOnly("org.postgresql:postgresql:42.6.0")

    // API (exposed to consumers, use sparingly)
    api("com.google.guava:guava:32.1.3-jre")

    // Test dependencies
    testImplementation("org.junit.jupiter:junit-jupiter:5.10.0")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")

    // Annotation processing
    annotationProcessor("org.projectlombok:lombok:1.18.30")
    kapt("com.google.dagger:dagger-compiler:2.48")
}
```

### Version Catalogs (Gradle 7.0+)

```toml
# gradle/libs.versions.toml
[versions]
kotlin = "1.9.24"
junit = "5.10.0"
guava = "32.1.3-jre"

[libraries]
kotlin-stdlib = { module = "org.jetbrains.kotlin:kotlin-stdlib", version.ref = "kotlin" }
guava = { module = "com.google.guava:guava", version.ref = "guava" }
junit-jupiter = { module = "org.junit.jupiter:junit-jupiter", version.ref = "junit" }

[plugins]
kotlin-jvm = { id = "org.jetbrains.kotlin.jvm", version.ref = "kotlin" }
```

```kotlin
// build.gradle.kts - Use catalog
dependencies {
    implementation(libs.kotlin.stdlib)
    implementation(libs.guava)
    testImplementation(libs.junit.jupiter)
}

plugins {
    alias(libs.plugins.kotlin.jvm)
}
```

### Dependency Resolution

```kotlin
// Force specific version
configurations.all {
    resolutionStrategy {
        force("com.google.guava:guava:32.1.3-jre")
    }
}

// Exclude transitive dependency
dependencies {
    implementation("com.example:lib:1.0") {
        exclude(group = "org.slf4j", module = "slf4j-log4j12")
    }
}

// Replace dependency
configurations.all {
    resolutionStrategy.dependencySubstitution {
        substitute(module("org.slf4j:slf4j-simple"))
            .using(module("org.slf4j:slf4j-nop:2.0.9"))
    }
}

// View dependency tree
// ./gradlew dependencies --configuration compileClasspath
```

## Build Lifecycle and Tasks

### Standard Lifecycle

```
Initialization → Configuration → Execution
     ↓                ↓              ↓
settings.gradle  build.gradle   Task execution
```

### Task Configuration

```kotlin
// Define custom task
tasks.register("hello") {
    doLast {
        println("Hello, Gradle!")
    }
}

// Configure existing task
tasks.named<Test>("test") {
    useJUnitPlatform()
    maxHeapSize = "1G"
    testLogging {
        events("passed", "skipped", "failed")
    }
}

// Task with inputs/outputs (incremental builds)
tasks.register<Copy>("processTemplates") {
    from("src/templates")
    into("$buildDir/generated")
    expand(project.properties)

    inputs.dir("src/templates")
    outputs.dir("$buildDir/generated")
}

// Task dependencies
tasks.named("build") {
    dependsOn("processTemplates")
}
```

### Custom Task Types

```kotlin
// Define task class
abstract class GenerateVersionTask : DefaultTask() {
    @get:Input
    abstract val version: Property<String>

    @get:OutputFile
    abstract val outputFile: RegularFileProperty

    @TaskAction
    fun generate() {
        outputFile.get().asFile.writeText("version=${version.get()}")
    }
}

// Register task
tasks.register<GenerateVersionTask>("generateVersion") {
    version.set(project.version.toString())
    outputFile.set(layout.buildDirectory.file("version.properties"))
}
```

### Task Execution

```bash
# Run specific task
./gradlew build                # Build project
./gradlew clean                # Clean build directory
./gradlew test                 # Run tests
./gradlew assemble             # Build without tests

# Task selection
./gradlew :app:build           # Build specific subproject
./gradlew build -x test        # Exclude test task

# Parallel execution
./gradlew build --parallel     # Parallel subproject builds

# Information
./gradlew tasks                # List available tasks
./gradlew dependencies         # Show dependency tree
./gradlew properties           # Show project properties
```

## Multi-Project Builds

### Project Structure

```
multi-project/
├── settings.gradle.kts
├── build.gradle.kts       # Root build file
├── app/
│   └── build.gradle.kts
├── core/
│   └── build.gradle.kts
└── utils/
    └── build.gradle.kts
```

### Settings Configuration

```kotlin
// settings.gradle.kts
rootProject.name = "multi-project"

include("app", "core", "utils")

// Optional: change project directory
project(":app").projectDir = file("application")
```

### Root Build File

```kotlin
// build.gradle.kts (root)
plugins {
    kotlin("jvm") version "1.9.24" apply false
}

allprojects {
    group = "com.example"
    version = "1.0.0"

    repositories {
        mavenCentral()
    }
}

subprojects {
    apply(plugin = "org.jetbrains.kotlin.jvm")

    dependencies {
        // Common dependencies for all subprojects
        testImplementation("org.junit.jupiter:junit-jupiter:5.10.0")
    }

    tasks.withType<Test> {
        useJUnitPlatform()
    }
}
```

### Subproject Dependencies

```kotlin
// app/build.gradle.kts
plugins {
    application
}

dependencies {
    implementation(project(":core"))
    implementation(project(":utils"))

    implementation("com.google.guava:guava:32.1.3-jre")
}

application {
    mainClass.set("com.example.app.MainKt")
}
```

### Composite Builds

```kotlin
// settings.gradle.kts
includeBuild("../shared-library")

// Now can depend on included build
dependencies {
    implementation("com.example:shared-library:1.0")
}
```

## Build Optimization

### Build Cache

```kotlin
// gradle.properties
org.gradle.caching=true

// build.gradle.kts
tasks.withType<Test> {
    outputs.cacheIf { true }
}
```

```bash
# Local cache (default: ~/.gradle/caches)
./gradlew build --build-cache

# Remote cache (for teams/CI)
# buildCache {
#     remote<HttpBuildCache> {
#         url = uri("https://cache.example.com")
#     }
# }
```

### Configuration Cache (Gradle 8.0+)

```bash
# Enable configuration cache
./gradlew build --configuration-cache

# gradle.properties
org.gradle.configuration-cache=true
```

### Parallel Execution

```properties
# gradle.properties
org.gradle.parallel=true
org.gradle.workers.max=4
org.gradle.caching=true
```

### JVM Options

```properties
# gradle.properties
org.gradle.jvmargs=-Xmx2g -XX:MaxMetaspaceSize=512m -XX:+HeapDumpOnOutOfMemoryError
org.gradle.daemon=true
```

### Performance Profiling

```bash
# Generate performance report
./gradlew build --profile

# Report at: build/reports/profile/profile-*.html

# Scan for insights (requires Gradle account)
./gradlew build --scan
```

## Plugins

### Applying Plugins

```kotlin
// Core plugins (no version)
plugins {
    java
    application
}

// Community plugins (from Gradle Plugin Portal)
plugins {
    id("org.springframework.boot") version "3.2.0"
    id("io.spring.dependency-management") version "1.1.4"
}

// Apply to subprojects only
plugins {
    kotlin("jvm") version "1.9.24" apply false
}
```

### Common Plugins

```kotlin
// Java projects
plugins {
    java
    `java-library`      // For libraries (exposes API)
    application         // For executables
}

// Kotlin projects
plugins {
    kotlin("jvm") version "1.9.24"
    kotlin("plugin.spring") version "1.9.24"
}

// Spring Boot
plugins {
    id("org.springframework.boot") version "3.2.0"
}

// Shadow (fat JAR)
plugins {
    id("com.github.johnrengelman.shadow") version "8.1.1"
}
```

### Plugin Configuration

```kotlin
// Configure Java plugin
java {
    toolchain {
        languageVersion.set(JavaLanguageVersion.of(17))
    }
    withSourcesJar()
    withJavadocJar()
}

// Configure application plugin
application {
    mainClass.set("com.example.MainKt")
    applicationDefaultJvmArgs = listOf("-Xmx512m")
}

// Configure Shadow plugin
tasks.shadowJar {
    archiveBaseName.set("myapp")
    archiveClassifier.set("")
    archiveVersion.set("1.0.0")
}
```

## Testing

### JUnit 5 Configuration

```kotlin
dependencies {
    testImplementation("org.junit.jupiter:junit-jupiter:5.10.0")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")
}

tasks.test {
    useJUnitPlatform()

    // Test selection
    filter {
        includeTestsMatching("*Test")
        excludeTestsMatching("*IntegrationTest")
    }

    // Logging
    testLogging {
        events("passed", "skipped", "failed")
        showStandardStreams = false
    }

    // Parallelization
    maxParallelForks = Runtime.getRuntime().availableProcessors()

    // Reports
    reports {
        html.required.set(true)
        junitXml.required.set(true)
    }
}
```

### Integration Tests

```kotlin
// Create separate source set
sourceSets {
    create("integrationTest") {
        compileClasspath += sourceSets.main.get().output
        runtimeClasspath += sourceSets.main.get().output
    }
}

configurations["integrationTestImplementation"].extendsFrom(configurations.testImplementation.get())

tasks.register<Test>("integrationTest") {
    testClassesDirs = sourceSets["integrationTest"].output.classesDirs
    classpath = sourceSets["integrationTest"].runtimeClasspath
    useJUnitPlatform()
}
```

## Anti-Patterns

### ❌ Not Using Wrapper

```bash
# WRONG: Direct gradle command (version varies by machine)
gradle build

# CORRECT: Use wrapper (consistent version)
./gradlew build
```

### ❌ Configuration at Execution Time

```kotlin
// WRONG: Configuration in doLast (runs at execution)
tasks.register("bad") {
    doLast {
        project.dependencies.add("implementation", "com.example:lib:1.0")
    }
}

// CORRECT: Configuration at configuration time
dependencies {
    implementation("com.example:lib:1.0")
}
```

### ❌ Using Legacy Configurations

```kotlin
// WRONG: Deprecated configurations
dependencies {
    compile("com.example:lib:1.0")     // Removed in Gradle 7
    testCompile("junit:junit:4.13.2")
}

// CORRECT: Modern configurations
dependencies {
    implementation("com.example:lib:1.0")
    testImplementation("junit:junit:4.13.2")
}
```

### ❌ Hardcoded Versions

```kotlin
// WRONG: Scattered versions
dependencies {
    implementation("org.springframework.boot:spring-boot-starter-web:3.2.0")
    implementation("org.springframework.boot:spring-boot-starter-data-jpa:3.2.0")
}

// CORRECT: Version catalogs or properties
val springBootVersion = "3.2.0"
dependencies {
    implementation("org.springframework.boot:spring-boot-starter-web:$springBootVersion")
    implementation("org.springframework.boot:spring-boot-starter-data-jpa:$springBootVersion")
}
```

## Quick Reference

### Essential Gradle Commands

```bash
# Build lifecycle
./gradlew clean                # Clean build directory
./gradlew build                # Compile, test, assemble
./gradlew assemble             # Build without tests
./gradlew test                 # Run tests only

# Information
./gradlew tasks                # List available tasks
./gradlew dependencies         # Show dependency tree
./gradlew projects             # List subprojects
./gradlew properties           # Show project properties

# Performance
./gradlew build --parallel     # Parallel execution
./gradlew build --build-cache  # Enable build cache
./gradlew build --profile      # Generate performance report
./gradlew build --scan         # Upload build scan

# Debugging
./gradlew build --info         # Info logging
./gradlew build --debug        # Debug logging
./gradlew build --stacktrace   # Show stack traces
```

### Common Properties (gradle.properties)

```properties
# Build performance
org.gradle.parallel=true
org.gradle.caching=true
org.gradle.configuration-cache=true
org.gradle.workers.max=4

# JVM settings
org.gradle.jvmargs=-Xmx2g -XX:MaxMetaspaceSize=512m

# Daemon
org.gradle.daemon=true

# Project properties
version=1.0.0
group=com.example
```

## Python Integration Example

```python
# generate_buildscript.py - Generate Gradle dependencies
import json

with open('dependencies.json') as f:
    deps = json.load(f)

for dep in deps:
    config = dep.get('configuration', 'implementation')
    print(f'{config}("{dep["group"]}:{dep["name"]}:{dep["version"]}")')
```

```kotlin
// build.gradle.kts - Use generated dependencies
val generatedDeps = providers.exec {
    commandLine("python", "generate_buildscript.py")
}.standardOutput.asText.get()

// Note: This is illustrative; in practice, use version catalogs
```

## Related Skills

- `maven-configuration.md` - Alternative JVM build system
- `build-system-selection.md` - Choosing between Gradle, Maven, Bazel
- `bazel-monorepos.md` - Alternative for large-scale projects
- `build-optimization.md` - Build caching strategies
- `cicd/github-actions-workflows.md` - Gradle in CI pipelines

## Summary

Gradle is the dominant build system for JVM projects, offering flexibility and performance:

**Key Takeaways**:
1. **Use Gradle Wrapper** - Ensures consistent builds across environments
2. **Kotlin DSL** - Prefer for new projects (type safety, IDE support)
3. **Version catalogs** - Centralize dependency versions (Gradle 7.0+)
4. **Configuration cache** - Major performance boost (Gradle 8.0+)
5. **Build cache** - Enable local/remote caching for incremental builds
6. **Parallel execution** - Use `--parallel` for multi-module projects
7. **Dependency configurations** - Understand implementation vs api vs compileOnly
8. **Task dependencies** - Leverage incremental build with inputs/outputs

**2024 Benchmark Data**: Gradle 8.x with configuration cache and parallel execution is 2-3x faster than Maven for multi-module builds, and competitive with Bazel for JVM-only projects (Bazel excels at polyglot monorepos).

Gradle's flexibility makes it ideal for complex JVM projects, Android development, and polyglot builds requiring custom logic.
