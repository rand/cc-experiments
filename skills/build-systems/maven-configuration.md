---
name: build-systems-maven-configuration
description: Maven POM structure, dependency management, plugin configuration, lifecycle phases, multi-module projects, profiles, and repository management for Java projects.
---
# Maven Configuration

**Last Updated**: 2025-10-26

## When to Use This Skill

Use this skill when:
- Building Java projects with convention-over-configuration approach
- Working with legacy enterprise Java codebases
- Needing strong dependency management and central repository
- Creating libraries for Maven Central publication
- Requiring standardized project structure
- Integrating with enterprise tools (Jenkins, Nexus, Artifactory)

**Alternatives**: Gradle (flexibility), Bazel (monorepos), Ant (legacy)

**Prerequisites**: JDK 8+ installed, Maven 3.9+ (3.9.6 latest as of 2024)

## Core Concepts

### Project Object Model (POM)

```xml
<!-- pom.xml - Minimum viable POM -->
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
                             http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <!-- Coordinates -->
    <groupId>com.example</groupId>
    <artifactId>myapp</artifactId>
    <version>1.0.0-SNAPSHOT</version>
    <packaging>jar</packaging>

    <!-- Metadata -->
    <name>My Application</name>
    <description>Sample Maven project</description>

    <!-- Properties -->
    <properties>
        <maven.compiler.source>17</maven.compiler.source>
        <maven.compiler.target>17</maven.compiler.target>
        <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
    </properties>

    <!-- Dependencies -->
    <dependencies>
        <dependency>
            <groupId>org.junit.jupiter</groupId>
            <artifactId>junit-jupiter</artifactId>
            <version>5.10.0</version>
            <scope>test</scope>
        </dependency>
    </dependencies>
</project>
```

### Standard Directory Structure

```
project/
├── pom.xml
├── src/
│   ├── main/
│   │   ├── java/              # Java source files
│   │   ├── resources/         # Application resources
│   │   └── webapp/            # Web application files (WAR)
│   └── test/
│       ├── java/              # Test source files
│       └── resources/         # Test resources
└── target/                    # Build output (gitignored)
    ├── classes/
    ├── test-classes/
    └── myapp-1.0.0.jar
```

## Dependency Management

### Dependency Declaration

```xml
<dependencies>
    <!-- Compile + Runtime dependency -->
    <dependency>
        <groupId>org.slf4j</groupId>
        <artifactId>slf4j-api</artifactId>
        <version>2.0.9</version>
    </dependency>

    <!-- Runtime only -->
    <dependency>
        <groupId>org.postgresql</groupId>
        <artifactId>postgresql</artifactId>
        <version>42.6.0</version>
        <scope>runtime</scope>
    </dependency>

    <!-- Test only -->
    <dependency>
        <groupId>org.junit.jupiter</groupId>
        <artifactId>junit-jupiter</artifactId>
        <version>5.10.0</version>
        <scope>test</scope>
    </dependency>

    <!-- Provided (e.g., servlet API from container) -->
    <dependency>
        <groupId>jakarta.servlet</groupId>
        <artifactId>jakarta.servlet-api</artifactId>
        <version>6.0.0</version>
        <scope>provided</scope>
    </dependency>
</dependencies>
```

### Dependency Scopes

```xml
<!-- Scopes determine classpath availability:
     compile:  Default, all classpaths
     provided: Compile + test, not runtime (container provides)
     runtime:  Runtime + test, not compile
     test:     Test only
     system:   Similar to provided, but manual path (avoid)
     import:   Only for <dependencyManagement>, imports BOM
-->
```

### Dependency Management (BOM)

```xml
<!-- Parent or root POM -->
<dependencyManagement>
    <dependencies>
        <!-- Import Spring Boot BOM -->
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-dependencies</artifactId>
            <version>3.2.0</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>

        <!-- Or manage versions directly -->
        <dependency>
            <groupId>com.google.guava</groupId>
            <artifactId>guava</artifactId>
            <version>32.1.3-jre</version>
        </dependency>
    </dependencies>
</dependencyManagement>

<!-- Child modules can omit version -->
<dependencies>
    <dependency>
        <groupId>com.google.guava</groupId>
        <artifactId>guava</artifactId>
        <!-- Version inherited from dependencyManagement -->
    </dependency>
</dependencies>
```

### Exclusions and Overrides

```xml
<dependency>
    <groupId>com.example</groupId>
    <artifactId>mylib</artifactId>
    <version>1.0.0</version>

    <!-- Exclude transitive dependency -->
    <exclusions>
        <exclusion>
            <groupId>org.slf4j</groupId>
            <artifactId>slf4j-log4j12</artifactId>
        </exclusion>
    </exclusions>
</dependency>

<!-- Override transitive version -->
<dependency>
    <groupId>com.google.guava</groupId>
    <artifactId>guava</artifactId>
    <version>32.1.3-jre</version>
</dependency>
```

## Build Lifecycle

### Standard Lifecycles

Maven has 3 built-in lifecycles:
1. **default** - Build and deploy
2. **clean** - Clean build artifacts
3. **site** - Generate project documentation

### Default Lifecycle Phases

```
validate → compile → test → package → verify → install → deploy
```

```bash
# Execute phases (runs all previous phases)
mvn validate        # Validate project structure
mvn compile         # Compile source code
mvn test            # Run unit tests
mvn package         # Create JAR/WAR
mvn verify          # Run integration tests
mvn install         # Install to local repository (~/.m2)
mvn deploy          # Deploy to remote repository

# Clean lifecycle
mvn clean           # Delete target/ directory

# Combined
mvn clean install   # Clean then install
mvn clean verify    # Clean then verify (common in CI)
```

### Phase-Plugin-Goal Binding

```xml
<!-- Plugins bind goals to lifecycle phases -->
<build>
    <plugins>
        <!-- Compiler plugin (binds to compile phase) -->
        <plugin>
            <groupId>org.apache.maven.plugins</groupId>
            <artifactId>maven-compiler-plugin</artifactId>
            <version>3.11.0</version>
            <configuration>
                <source>17</source>
                <target>17</target>
            </configuration>
        </plugin>

        <!-- Surefire plugin (binds to test phase) -->
        <plugin>
            <groupId>org.apache.maven.plugins</groupId>
            <artifactId>maven-surefire-plugin</artifactId>
            <version>3.2.2</version>
        </plugin>
    </plugins>
</build>

<!-- Execute specific plugin goal -->
<!-- mvn compiler:compile -->
<!-- mvn surefire:test -->
```

## Plugin Configuration

### Essential Plugins

```xml
<build>
    <plugins>
        <!-- Compiler Plugin -->
        <plugin>
            <groupId>org.apache.maven.plugins</groupId>
            <artifactId>maven-compiler-plugin</artifactId>
            <version>3.11.0</version>
            <configuration>
                <release>17</release>
                <compilerArgs>
                    <arg>-parameters</arg>
                </compilerArgs>
            </configuration>
        </plugin>

        <!-- Surefire (Unit Tests) -->
        <plugin>
            <groupId>org.apache.maven.plugins</groupId>
            <artifactId>maven-surefire-plugin</artifactId>
            <version>3.2.2</version>
            <configuration>
                <includes>
                    <include>**/*Test.java</include>
                </includes>
            </configuration>
        </plugin>

        <!-- Failsafe (Integration Tests) -->
        <plugin>
            <groupId>org.apache.maven.plugins</groupId>
            <artifactId>maven-failsafe-plugin</artifactId>
            <version>3.2.2</version>
            <executions>
                <execution>
                    <goals>
                        <goal>integration-test</goal>
                        <goal>verify</goal>
                    </goals>
                </execution>
            </executions>
        </plugin>

        <!-- JAR Plugin -->
        <plugin>
            <groupId>org.apache.maven.plugins</groupId>
            <artifactId>maven-jar-plugin</artifactId>
            <version>3.3.0</version>
            <configuration>
                <archive>
                    <manifest>
                        <mainClass>com.example.Main</mainClass>
                    </manifest>
                </archive>
            </configuration>
        </plugin>

        <!-- Assembly (Fat JAR) -->
        <plugin>
            <groupId>org.apache.maven.plugins</groupId>
            <artifactId>maven-assembly-plugin</artifactId>
            <version>3.6.0</version>
            <configuration>
                <descriptorRefs>
                    <descriptorRef>jar-with-dependencies</descriptorRef>
                </descriptorRefs>
                <archive>
                    <manifest>
                        <mainClass>com.example.Main</mainClass>
                    </manifest>
                </archive>
            </configuration>
            <executions>
                <execution>
                    <phase>package</phase>
                    <goals>
                        <goal>single</goal>
                    </goals>
                </execution>
            </executions>
        </plugin>

        <!-- Shade (Fat JAR with relocation) -->
        <plugin>
            <groupId>org.apache.maven.plugins</groupId>
            <artifactId>maven-shade-plugin</artifactId>
            <version>3.5.1</version>
            <executions>
                <execution>
                    <phase>package</phase>
                    <goals>
                        <goal>shade</goal>
                    </goals>
                    <configuration>
                        <transformers>
                            <transformer implementation="org.apache.maven.plugins.shade.resource.ManifestResourceTransformer">
                                <mainClass>com.example.Main</mainClass>
                            </transformer>
                        </transformers>
                    </configuration>
                </execution>
            </executions>
        </plugin>
    </plugins>
</build>
```

### Spring Boot Plugin

```xml
<parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>3.2.0</version>
</parent>

<build>
    <plugins>
        <plugin>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-maven-plugin</artifactId>
        </plugin>
    </plugins>
</build>

<!-- Build: mvn spring-boot:run -->
<!-- Package: mvn package (creates executable JAR) -->
```

## Multi-Module Projects

### Project Structure

```
multi-module/
├── pom.xml              # Parent POM
├── core/
│   └── pom.xml
├── api/
│   └── pom.xml
└── app/
    └── pom.xml
```

### Parent POM

```xml
<!-- multi-module/pom.xml -->
<project>
    <modelVersion>4.0.0</modelVersion>

    <groupId>com.example</groupId>
    <artifactId>multi-module-parent</artifactId>
    <version>1.0.0-SNAPSHOT</version>
    <packaging>pom</packaging>

    <!-- Declare modules -->
    <modules>
        <module>core</module>
        <module>api</module>
        <module>app</module>
    </modules>

    <!-- Common properties -->
    <properties>
        <maven.compiler.source>17</maven.compiler.source>
        <maven.compiler.target>17</maven.compiler.target>
        <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
        <junit.version>5.10.0</junit.version>
    </properties>

    <!-- Dependency management (versions) -->
    <dependencyManagement>
        <dependencies>
            <dependency>
                <groupId>org.junit.jupiter</groupId>
                <artifactId>junit-jupiter</artifactId>
                <version>${junit.version}</version>
                <scope>test</scope>
            </dependency>
        </dependencies>
    </dependencyManagement>

    <!-- Common dependencies for all modules -->
    <dependencies>
        <dependency>
            <groupId>org.junit.jupiter</groupId>
            <artifactId>junit-jupiter</artifactId>
            <scope>test</scope>
        </dependency>
    </dependencies>
</project>
```

### Child Module POM

```xml
<!-- multi-module/app/pom.xml -->
<project>
    <modelVersion>4.0.0</modelVersion>

    <!-- Parent reference -->
    <parent>
        <groupId>com.example</groupId>
        <artifactId>multi-module-parent</artifactId>
        <version>1.0.0-SNAPSHOT</version>
    </parent>

    <artifactId>app</artifactId>

    <!-- Module dependencies -->
    <dependencies>
        <dependency>
            <groupId>com.example</groupId>
            <artifactId>core</artifactId>
            <version>${project.version}</version>
        </dependency>

        <dependency>
            <groupId>com.example</groupId>
            <artifactId>api</artifactId>
            <version>${project.version}</version>
        </dependency>
    </dependencies>
</project>
```

### Building Multi-Module Projects

```bash
# Build all modules from root
mvn clean install

# Build specific module
mvn clean install -pl app

# Build module and dependencies
mvn clean install -pl app -am

# Build without dependencies
mvn clean install -pl app -DskipTests

# Build in parallel
mvn clean install -T 4  # 4 threads
```

## Profiles

### Profile Definition

```xml
<profiles>
    <!-- Development profile -->
    <profile>
        <id>dev</id>
        <activation>
            <activeByDefault>true</activeByDefault>
        </activation>
        <properties>
            <env>development</env>
            <db.url>jdbc:h2:mem:testdb</db.url>
        </properties>
    </profile>

    <!-- Production profile -->
    <profile>
        <id>prod</id>
        <properties>
            <env>production</env>
            <db.url>jdbc:postgresql://prod-db:5432/app</db.url>
        </properties>
        <build>
            <plugins>
                <plugin>
                    <groupId>org.apache.maven.plugins</groupId>
                    <artifactId>maven-compiler-plugin</artifactId>
                    <configuration>
                        <debug>false</debug>
                        <optimize>true</optimize>
                    </configuration>
                </plugin>
            </plugins>
        </build>
    </profile>

    <!-- Platform-specific -->
    <profile>
        <id>windows</id>
        <activation>
            <os>
                <family>windows</family>
            </os>
        </activation>
        <properties>
            <script.extension>.bat</script.extension>
        </properties>
    </profile>
</profiles>

<!-- Activate profile: mvn clean install -Pprod -->
<!-- Multiple profiles: mvn clean install -Pdev,docker -->
```

## Repository Management

### Repository Configuration

```xml
<repositories>
    <!-- Maven Central (default, can omit) -->
    <repository>
        <id>central</id>
        <url>https://repo.maven.apache.org/maven2</url>
    </repository>

    <!-- Custom repository -->
    <repository>
        <id>company-repo</id>
        <url>https://repo.company.com/maven</url>
        <releases>
            <enabled>true</enabled>
        </releases>
        <snapshots>
            <enabled>false</enabled>
        </snapshots>
    </repository>
</repositories>

<!-- Plugin repositories -->
<pluginRepositories>
    <pluginRepository>
        <id>spring-plugins</id>
        <url>https://repo.spring.io/plugins-release</url>
    </pluginRepository>
</pluginRepositories>
```

### Settings.xml (Global Configuration)

```xml
<!-- ~/.m2/settings.xml -->
<settings>
    <!-- Local repository location -->
    <localRepository>${user.home}/.m2/repository</localRepository>

    <!-- Mirrors -->
    <mirrors>
        <mirror>
            <id>company-mirror</id>
            <url>https://nexus.company.com/repository/maven-public</url>
            <mirrorOf>central</mirrorOf>
        </mirror>
    </mirrors>

    <!-- Servers (authentication) -->
    <servers>
        <server>
            <id>company-repo</id>
            <username>deploy-user</username>
            <password>{encrypted-password}</password>
        </server>
    </servers>

    <!-- Active profiles -->
    <activeProfiles>
        <activeProfile>company</activeProfile>
    </activeProfiles>
</settings>
```

## Anti-Patterns

### ❌ Not Using dependencyManagement

```xml
<!-- WRONG: Duplicate versions across modules -->
<!-- module1/pom.xml -->
<dependency>
    <groupId>com.google.guava</groupId>
    <artifactId>guava</artifactId>
    <version>32.1.3-jre</version>
</dependency>

<!-- module2/pom.xml -->
<dependency>
    <groupId>com.google.guava</groupId>
    <artifactId>guava</artifactId>
    <version>31.0-jre</version> <!-- Different version! -->
</dependency>

<!-- CORRECT: Centralize in parent POM -->
<!-- parent/pom.xml -->
<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>com.google.guava</groupId>
            <artifactId>guava</artifactId>
            <version>32.1.3-jre</version>
        </dependency>
    </dependencies>
</dependencyManagement>
```

### ❌ Hardcoded Versions

```xml
<!-- WRONG -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-web</artifactId>
    <version>3.2.0</version>
</dependency>

<!-- CORRECT: Use properties -->
<properties>
    <spring-boot.version>3.2.0</spring-boot.version>
</properties>

<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-web</artifactId>
    <version>${spring-boot.version}</version>
</dependency>
```

### ❌ Not Specifying Plugin Versions

```xml
<!-- WRONG: Unversioned plugin (non-reproducible builds) -->
<plugin>
    <groupId>org.apache.maven.plugins</groupId>
    <artifactId>maven-compiler-plugin</artifactId>
</plugin>

<!-- CORRECT: Pin versions -->
<plugin>
    <groupId>org.apache.maven.plugins</groupId>
    <artifactId>maven-compiler-plugin</artifactId>
    <version>3.11.0</version>
</plugin>
```

### ❌ Mixing Dependencies and DependencyManagement

```xml
<!-- WRONG: Version in both places -->
<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>com.google.guava</groupId>
            <artifactId>guava</artifactId>
            <version>32.1.3-jre</version>
        </dependency>
    </dependencies>
</dependencyManagement>

<dependencies>
    <dependency>
        <groupId>com.google.guava</groupId>
        <artifactId>guava</artifactId>
        <version>31.0-jre</version> <!-- Override defeats purpose -->
    </dependency>
</dependencies>

<!-- CORRECT: Version only in dependencyManagement -->
<dependencies>
    <dependency>
        <groupId>com.google.guava</groupId>
        <artifactId>guava</artifactId>
        <!-- Inherits version from dependencyManagement -->
    </dependency>
</dependencies>
```

## Quick Reference

### Essential Maven Commands

```bash
# Lifecycle
mvn clean                      # Clean target/
mvn compile                    # Compile sources
mvn test                       # Run unit tests
mvn package                    # Create JAR/WAR
mvn verify                     # Run integration tests
mvn install                    # Install to local repo
mvn deploy                     # Deploy to remote repo

# Combined
mvn clean install              # Most common workflow
mvn clean verify               # CI workflow
mvn clean package -DskipTests  # Fast build

# Multi-module
mvn install -pl app            # Build specific module
mvn install -pl app -am        # Build with dependencies
mvn install -T 4               # Parallel build (4 threads)

# Profiles
mvn install -Pprod             # Activate profile

# Information
mvn dependency:tree            # Show dependency tree
mvn dependency:analyze         # Analyze dependencies
mvn help:effective-pom         # Show effective POM
mvn versions:display-dependency-updates  # Check updates
```

### POM Coordinates

```xml
<groupId>com.example</groupId>        <!-- Organization/group -->
<artifactId>myapp</artifactId>        <!-- Project name -->
<version>1.0.0-SNAPSHOT</version>     <!-- Version -->
<packaging>jar</packaging>            <!-- jar, war, pom, etc. -->
```

## Python Integration Example

```python
# generate_dependencies.py - Generate Maven dependencies from JSON
import json
import xml.etree.ElementTree as ET

with open('dependencies.json') as f:
    deps = json.load(f)

dependencies = ET.Element('dependencies')

for dep in deps:
    dependency = ET.SubElement(dependencies, 'dependency')
    ET.SubElement(dependency, 'groupId').text = dep['group']
    ET.SubElement(dependency, 'artifactId').text = dep['name']
    ET.SubElement(dependency, 'version').text = dep['version']
    if 'scope' in dep:
        ET.SubElement(dependency, 'scope').text = dep['scope']

print(ET.tostring(dependencies, encoding='unicode'))
```

## Related Skills

- `gradle-jvm-builds.md` - Modern alternative to Maven
- `build-system-selection.md` - Choosing between Maven, Gradle, Bazel
- `build-optimization.md` - Build caching and performance
- `cicd/github-actions-workflows.md` - Maven in CI pipelines

## Summary

Maven is the original convention-over-configuration build system for Java, still dominant in enterprise environments:

**Key Takeaways**:
1. **Standard structure** - Convention over configuration reduces boilerplate
2. **POM hierarchy** - Parent POMs share configuration across modules
3. **dependencyManagement** - Centralize versions without forcing inclusion
4. **Lifecycle phases** - Understand validate → compile → test → package → install → deploy
5. **Plugin ecosystem** - Rich plugin library for common tasks
6. **Repository management** - Central repositories simplify dependency resolution
7. **Profiles** - Environment-specific configuration
8. **Multi-module** - Manage complex projects with module aggregation

**Maven vs Gradle** (2024 data):
- **Maven**: Simpler, more standardized, better for traditional Java projects
- **Gradle**: Faster (2-3x with cache), more flexible, better for Android/Kotlin

Maven excels at standardization and reproducibility, making it ideal for enterprise Java projects requiring strict conventions and tooling integration.
