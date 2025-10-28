---
name: build-systems-cmake-patterns
description: Modern CMake target-based approach, find_package, FetchContent, generator expressions, cross-platform configuration, and installation rules for C/C++ projects.
---
# CMake Patterns

**Last Updated**: 2025-10-26

## When to Use This Skill

Use this skill when:
- Building cross-platform C/C++ projects
- Managing complex dependency graphs
- Integrating third-party libraries with find_package
- Generating IDE project files (Visual Studio, Xcode, etc.)
- Creating installable libraries with export/import support
- Migrating from Makefiles or other build systems

**Alternatives**: Make (simplicity), Bazel (monorepos), Meson (speed)

**Prerequisites**: C/C++ compiler toolchains, CMake 3.20+ (4.0.2 latest as of 2024)

## Core Concepts

### Modern CMake Philosophy

```cmake
# Modern CMake (3.20+) is TARGET-BASED
# Targets have properties (compile flags, includes, links)
# Properties propagate through INTERFACE/PUBLIC/PRIVATE

# WRONG (Old-style, CMake 2.x)
include_directories(${PROJECT_SOURCE_DIR}/include)
add_definitions(-DUSE_FEATURE)
link_libraries(pthread)

# CORRECT (Modern CMake 3.x)
add_library(mylib src/lib.cpp)
target_include_directories(mylib PUBLIC include)
target_compile_definitions(mylib PRIVATE USE_FEATURE)
target_link_libraries(mylib PRIVATE pthread)
```

### Minimum CMakeLists.txt

```cmake
cmake_minimum_required(VERSION 3.20)
project(MyProject VERSION 1.0.0 LANGUAGES CXX)

# Set C++ standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Create executable
add_executable(myapp src/main.cpp)

# Add library
add_library(mylib src/lib.cpp)
target_include_directories(mylib PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)

# Link executable to library
target_link_libraries(myapp PRIVATE mylib)
```

### Project Structure

```
project/
├── CMakeLists.txt          # Root CMake file
├── cmake/
│   ├── Config.cmake.in     # Package config template
│   └── FindMyDep.cmake     # Custom Find module
├── src/
│   ├── CMakeLists.txt      # Source CMake
│   └── main.cpp
├── include/
│   └── myproject/
│       └── mylib.h
├── tests/
│   ├── CMakeLists.txt      # Test CMake
│   └── test_main.cpp
└── build/                  # Out-of-source build (gitignored)
```

## Target-Based Configuration

### Target Types

```cmake
# EXECUTABLE
add_executable(myapp main.cpp utils.cpp)

# STATIC LIBRARY (.a or .lib)
add_library(mylib STATIC lib.cpp)

# SHARED LIBRARY (.so, .dylib, or .dll)
add_library(mylib SHARED lib.cpp)

# INTERFACE LIBRARY (header-only)
add_library(mylib INTERFACE)
target_include_directories(mylib INTERFACE include)

# OBJECT LIBRARY (compile once, link many)
add_library(common OBJECT common.cpp)
target_link_libraries(app1 PRIVATE common)
target_link_libraries(app2 PRIVATE common)
```

### Visibility: PUBLIC, PRIVATE, INTERFACE

```cmake
add_library(mylib src/lib.cpp)

# PRIVATE: Only used by this target
target_compile_definitions(mylib PRIVATE INTERNAL_DEBUG)

# INTERFACE: Not used by this target, but propagated to consumers
target_include_directories(mylib INTERFACE include)

# PUBLIC: Used by this target AND propagated to consumers
target_include_directories(mylib PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
)

# Example propagation
add_executable(myapp main.cpp)
target_link_libraries(myapp PRIVATE mylib)
# myapp automatically gets mylib's PUBLIC and INTERFACE properties
```

### Generator Expressions

```cmake
# Conditional compilation based on build type
target_compile_options(mylib PRIVATE
    $<$<CONFIG:Debug>:-g -O0>
    $<$<CONFIG:Release>:-O3>
)

# Platform-specific flags
target_compile_definitions(mylib PRIVATE
    $<$<PLATFORM_ID:Windows>:WINDOWS_BUILD>
    $<$<PLATFORM_ID:Linux>:LINUX_BUILD>
    $<$<PLATFORM_ID:Darwin>:MACOS_BUILD>
)

# Compiler-specific flags
target_compile_options(mylib PRIVATE
    $<$<CXX_COMPILER_ID:GNU>:-Wall -Wextra>
    $<$<CXX_COMPILER_ID:MSVC>:/W4>
    $<$<CXX_COMPILER_ID:Clang>:-Weverything>
)

# Build vs Install include paths
target_include_directories(mylib PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)
```

## Dependency Management

### find_package

```cmake
# Find installed packages
find_package(Threads REQUIRED)
find_package(Boost 1.70 REQUIRED COMPONENTS system filesystem)
find_package(OpenCV 4.5 REQUIRED)

# Link found packages
target_link_libraries(myapp PRIVATE
    Threads::Threads
    Boost::system
    Boost::filesystem
    opencv_core
    opencv_imgproc
)

# Optional package
find_package(ZLIB)
if(ZLIB_FOUND)
    target_link_libraries(mylib PRIVATE ZLIB::ZLIB)
    target_compile_definitions(mylib PRIVATE HAVE_ZLIB)
endif()
```

### FetchContent (CMake 3.11+)

```cmake
include(FetchContent)

# Fetch from Git
FetchContent_Declare(
    json
    GIT_REPOSITORY https://github.com/nlohmann/json.git
    GIT_TAG v3.11.2
)

FetchContent_Declare(
    googletest
    GIT_REPOSITORY https://github.com/google/googletest.git
    GIT_TAG v1.14.0
)

# Make available
FetchContent_MakeAvailable(json googletest)

# Use fetched library
target_link_libraries(myapp PRIVATE nlohmann_json::nlohmann_json)
target_link_libraries(tests PRIVATE gtest_main)
```

### Custom Find Modules

```cmake
# cmake/FindMyDep.cmake
find_path(MYDEP_INCLUDE_DIR mydep.h
    PATHS /usr/include /usr/local/include
)

find_library(MYDEP_LIBRARY
    NAMES mydep
    PATHS /usr/lib /usr/local/lib
)

include(FindPackageHandleStandardArgs)
find_package_handle_standard_args(MyDep
    REQUIRED_VARS MYDEP_LIBRARY MYDEP_INCLUDE_DIR
)

if(MYDEP_FOUND AND NOT TARGET MyDep::MyDep)
    add_library(MyDep::MyDep UNKNOWN IMPORTED)
    set_target_properties(MyDep::MyDep PROPERTIES
        IMPORTED_LOCATION "${MYDEP_LIBRARY}"
        INTERFACE_INCLUDE_DIRECTORIES "${MYDEP_INCLUDE_DIR}"
    )
endif()

# Use in CMakeLists.txt
list(APPEND CMAKE_MODULE_PATH "${CMAKE_SOURCE_DIR}/cmake")
find_package(MyDep REQUIRED)
target_link_libraries(myapp PRIVATE MyDep::MyDep)
```

## Cross-Platform Configuration

### Platform Detection

```cmake
if(WIN32)
    # Windows-specific
    target_compile_definitions(myapp PRIVATE PLATFORM_WINDOWS)
    target_link_libraries(myapp PRIVATE ws2_32)
elseif(APPLE)
    # macOS-specific
    target_compile_definitions(myapp PRIVATE PLATFORM_MACOS)
    target_link_libraries(myapp PRIVATE "-framework CoreFoundation")
elseif(UNIX)
    # Linux/BSD-specific
    target_compile_definitions(myapp PRIVATE PLATFORM_LINUX)
    target_link_libraries(myapp PRIVATE pthread dl)
endif()
```

### Compiler Configuration

```cmake
# Set compiler
set(CMAKE_C_COMPILER gcc)
set(CMAKE_CXX_COMPILER g++)

# Or use environment: CC=clang CXX=clang++ cmake ..

# Compiler-specific options
if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
    target_compile_options(mylib PRIVATE -Wall -Wextra -Wpedantic)
elseif(CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
    target_compile_options(mylib PRIVATE /W4 /WX)
elseif(CMAKE_CXX_COMPILER_ID STREQUAL "Clang")
    target_compile_options(mylib PRIVATE -Wall -Wextra -Wno-unused-parameter)
endif()
```

### Build Types

```cmake
# Set default build type
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

# Available: Debug, Release, RelWithDebInfo, MinSizeRel

# Custom build type
set(CMAKE_CXX_FLAGS_PROFILING "-g -O2 -pg" CACHE STRING "Profiling flags")
set(CMAKE_BUILD_TYPE Profiling)

# Per-config properties
set_target_properties(mylib PROPERTIES
    DEBUG_POSTFIX "_d"
    RELEASE_POSTFIX ""
)
```

### Cross-Compilation

```cmake
# Toolchain file: toolchain-arm.cmake
set(CMAKE_SYSTEM_NAME Linux)
set(CMAKE_SYSTEM_PROCESSOR arm)

set(CMAKE_C_COMPILER arm-linux-gnueabihf-gcc)
set(CMAKE_CXX_COMPILER arm-linux-gnueabihf-g++)

set(CMAKE_FIND_ROOT_PATH /usr/arm-linux-gnueabihf)
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)

# Use: cmake -DCMAKE_TOOLCHAIN_FILE=toolchain-arm.cmake ..
```

## Installation and Packaging

### Install Rules

```cmake
# Install executable
install(TARGETS myapp
    RUNTIME DESTINATION bin
)

# Install library
install(TARGETS mylib
    EXPORT MyLibTargets
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
    RUNTIME DESTINATION bin
    INCLUDES DESTINATION include
)

# Install headers
install(DIRECTORY include/
    DESTINATION include
    FILES_MATCHING PATTERN "*.h"
)

# Install CMake config files
install(EXPORT MyLibTargets
    FILE MyLibTargets.cmake
    NAMESPACE MyLib::
    DESTINATION lib/cmake/MyLib
)

# Install custom files
install(FILES LICENSE README.md
    DESTINATION share/doc/mylib
)
```

### Package Config

```cmake
# cmake/MyLibConfig.cmake.in
@PACKAGE_INIT@

include("${CMAKE_CURRENT_LIST_DIR}/MyLibTargets.cmake")

check_required_components(MyLib)

# CMakeLists.txt
include(CMakePackageConfigHelpers)

configure_package_config_file(
    cmake/MyLibConfig.cmake.in
    "${CMAKE_CURRENT_BINARY_DIR}/MyLibConfig.cmake"
    INSTALL_DESTINATION lib/cmake/MyLib
)

write_basic_package_version_file(
    "${CMAKE_CURRENT_BINARY_DIR}/MyLibConfigVersion.cmake"
    VERSION ${PROJECT_VERSION}
    COMPATIBILITY SameMajorVersion
)

install(FILES
    "${CMAKE_CURRENT_BINARY_DIR}/MyLibConfig.cmake"
    "${CMAKE_CURRENT_BINARY_DIR}/MyLibConfigVersion.cmake"
    DESTINATION lib/cmake/MyLib
)
```

### CPack Integration

```cmake
# Package generation
set(CPACK_GENERATOR "TGZ;DEB;RPM")
set(CPACK_PACKAGE_NAME "myproject")
set(CPACK_PACKAGE_VERSION "${PROJECT_VERSION}")
set(CPACK_PACKAGE_CONTACT "author@example.com")
set(CPACK_DEBIAN_PACKAGE_DEPENDS "libboost-all-dev")

include(CPack)

# Build package: cmake --build build --target package
```

## Testing with CTest

### Basic Testing

```cmake
# Enable testing
enable_testing()

# Add test executable
add_executable(test_mylib test_mylib.cpp)
target_link_libraries(test_mylib PRIVATE mylib gtest_main)

# Register tests
add_test(NAME test_mylib COMMAND test_mylib)

# Set test properties
set_tests_properties(test_mylib PROPERTIES
    TIMEOUT 30
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
)

# Run: cmake --build build --target test
# Or: ctest --test-dir build
```

### GoogleTest Integration

```cmake
include(GoogleTest)

add_executable(tests test_main.cpp test_utils.cpp)
target_link_libraries(tests PRIVATE mylib gtest_main)

# Auto-discover tests
gtest_discover_tests(tests)

# Or manual
add_test(NAME UtilsTest COMMAND tests --gtest_filter=UtilsTest.*)
```

## Advanced Techniques

### Option and Cache Variables

```cmake
# User-configurable options
option(BUILD_SHARED_LIBS "Build shared libraries" ON)
option(ENABLE_TESTS "Build tests" OFF)
option(USE_OPENMP "Enable OpenMP support" OFF)

# Cache variables
set(MAX_THREADS 4 CACHE STRING "Maximum thread count")
set(INSTALL_PREFIX "/opt/myapp" CACHE PATH "Install prefix")

# Conditional compilation
if(ENABLE_TESTS)
    enable_testing()
    add_subdirectory(tests)
endif()

if(USE_OPENMP)
    find_package(OpenMP REQUIRED)
    target_link_libraries(mylib PUBLIC OpenMP::OpenMP_CXX)
endif()

# Configure from command line:
# cmake -DENABLE_TESTS=ON -DMAX_THREADS=8 ..
```

### configure_file

```cmake
# config.h.in
#define PROJECT_VERSION "@PROJECT_VERSION@"
#define MAX_THREADS @MAX_THREADS@
#cmakedefine USE_OPENMP

# CMakeLists.txt
configure_file(
    "${CMAKE_SOURCE_DIR}/config.h.in"
    "${CMAKE_BINARY_DIR}/config.h"
)
target_include_directories(mylib PRIVATE ${CMAKE_BINARY_DIR})
```

### Custom Commands

```cmake
# Generate file at build time
add_custom_command(
    OUTPUT generated.cpp
    COMMAND python ${CMAKE_SOURCE_DIR}/generate.py > generated.cpp
    DEPENDS generate.py
    COMMENT "Generating source file"
)

add_executable(myapp main.cpp generated.cpp)

# Custom target
add_custom_target(docs
    COMMAND doxygen ${CMAKE_SOURCE_DIR}/Doxyfile
    WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
    COMMENT "Generating documentation"
)
```

### Precompiled Headers (CMake 3.16+)

```cmake
target_precompile_headers(mylib PRIVATE
    <vector>
    <string>
    <iostream>
    "common.h"
)

# Reuse PCH across targets
target_precompile_headers(myapp REUSE_FROM mylib)
```

## Anti-Patterns

### ❌ Global Commands (Old CMake)

```cmake
# WRONG: Affects all targets
include_directories(${PROJECT_SOURCE_DIR}/include)
link_libraries(pthread)
add_definitions(-DUSE_FEATURE)

# CORRECT: Target-specific
target_include_directories(mylib PUBLIC include)
target_link_libraries(mylib PRIVATE pthread)
target_compile_definitions(mylib PRIVATE USE_FEATURE)
```

### ❌ In-Source Builds

```cmake
# WRONG: Pollutes source directory
cd project && cmake .

# CORRECT: Out-of-source build
mkdir build && cd build && cmake ..
```

### ❌ Hardcoded Paths

```cmake
# WRONG
target_include_directories(mylib PUBLIC /usr/local/include)

# CORRECT
find_package(MyDep REQUIRED)
target_link_libraries(mylib PUBLIC MyDep::MyDep)
```

### ❌ Not Using Modern CMake Features

```cmake
# WRONG: CMake 2.x style
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -O2")

# CORRECT: CMake 3.x style
target_compile_options(mylib PRIVATE -Wall)
target_compile_options(mylib PRIVATE $<$<CONFIG:Release>:-O2>)
```

## Quick Reference

### Essential CMake Commands

```bash
# Configure
cmake -S . -B build                    # Source in ., build in build/
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake -B build -DENABLE_TESTS=ON

# Build
cmake --build build                    # Build all targets
cmake --build build --target myapp     # Build specific target
cmake --build build -j 8               # Parallel build

# Install
cmake --install build --prefix /opt    # Install to prefix

# Test
ctest --test-dir build                 # Run all tests
ctest --test-dir build -R UtilsTest    # Run matching tests

# Clean
cmake --build build --target clean     # Clean build artifacts
rm -rf build                           # Full clean - cleans build artifacts only
```

### CMake Variables Reference

```cmake
CMAKE_SOURCE_DIR           # Top-level source directory
CMAKE_BINARY_DIR           # Top-level build directory
CMAKE_CURRENT_SOURCE_DIR   # Current CMakeLists.txt directory
CMAKE_CURRENT_BINARY_DIR   # Current build directory
PROJECT_SOURCE_DIR         # project() source directory
PROJECT_VERSION            # Version from project()

CMAKE_CXX_COMPILER         # C++ compiler path
CMAKE_BUILD_TYPE           # Debug/Release/RelWithDebInfo/MinSizeRel
CMAKE_INSTALL_PREFIX       # Install prefix (default /usr/local)
```

## Python Integration Example

```python
# generate_config.py - Generate CMake config from JSON
import json
import sys

with open('config.json') as f:
    config = json.load(f)

cmake_code = f"""
set(APP_VERSION "{config['version']}")
set(APP_NAME "{config['name']}")
set(FEATURES "{';'.join(config['features'])}")
"""

print(cmake_code)
```

```cmake
# CMakeLists.txt - Use generated config
execute_process(
    COMMAND python ${CMAKE_SOURCE_DIR}/generate_config.py
    OUTPUT_VARIABLE GENERATED_CONFIG
)

# Include generated config
file(WRITE ${CMAKE_BINARY_DIR}/generated.cmake "${GENERATED_CONFIG}")
include(${CMAKE_BINARY_DIR}/generated.cmake)

message(STATUS "App: ${APP_NAME} v${APP_VERSION}")
```

## Related Skills

- `make-fundamentals.md` - Traditional Makefile-based builds
- `build-system-selection.md` - Choosing between build systems
- `cross-platform-builds.md` - Multi-platform strategies
- `build-optimization.md` - Build caching and parallelization
- `bazel-monorepos.md` - Alternative for large-scale projects
- `cicd/ci-optimization.md` - CMake in CI pipelines

## Summary

CMake is the de facto standard for cross-platform C/C++ projects, with modern features enabling clean, maintainable builds:

**Key Takeaways**:
1. **Target-based** - Use `target_*` commands, not global `include_directories`
2. **Visibility matters** - Understand PUBLIC, PRIVATE, INTERFACE propagation
3. **Generator expressions** - Use `$<>` for conditional configuration
4. **find_package** - Prefer finding installed packages over manual paths
5. **FetchContent** - Fetch dependencies at configure time (CMake 3.11+)
6. **Out-of-source builds** - Always build in separate directory
7. **Export/install** - Create proper package config for library consumers
8. **Cross-platform** - Leverage platform detection and toolchain files

CMake 4.0.2 (2024) continues the modern CMake philosophy with improved performance and better diagnostics. While steeper learning curve than Make, CMake excels at managing complex dependencies and generating native build files for any platform.
