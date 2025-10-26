---
name: build-systems-cross-platform-builds
description: Platform detection, conditional compilation, preprocessor macros, CMake cross-compilation, Zig cross-compilation, toolchain configuration, and multi-platform testing strategies.
---
# Cross-Platform Builds

**Last Updated**: 2025-10-26

## When to Use This Skill

Use this skill when:
- Building software for Windows, macOS, and Linux
- Cross-compiling for different architectures (x86, ARM, etc.)
- Handling platform-specific APIs and behaviors
- Creating portable libraries or applications
- Targeting embedded systems or mobile platforms
- Managing platform-specific dependencies

**Prerequisites**: Understanding of target platforms, C/C++ or Rust, build systems (CMake, Cargo, etc.)

## Core Concepts

### Platform Taxonomy

```
Operating Systems:
├── Windows (Win32/Win64)
├── macOS (Darwin)
├── Linux (various distros)
├── BSD (FreeBSD, OpenBSD, NetBSD)
├── Mobile (iOS, Android)
└── Embedded (FreeRTOS, bare-metal)

Architectures:
├── x86 (32-bit, i386, i686)
├── x86_64 (64-bit, amd64)
├── ARM (32-bit, armv7, armv8)
├── ARM64 (AArch64, Apple Silicon)
├── RISC-V
└── WebAssembly (wasm32, wasm64)

Compilers:
├── GCC (Linux, cross-platform)
├── Clang/LLVM (macOS, cross-platform)
├── MSVC (Windows)
└── MinGW/Cygwin (Windows POSIX)
```

## Platform Detection

### Compiler Predefined Macros

```c
// C/C++ preprocessor macros for platform detection

// Operating System
#ifdef _WIN32
    // Windows (32-bit or 64-bit)
    #ifdef _WIN64
        // Windows 64-bit
    #endif
#elif __APPLE__
    #include <TargetConditionals.h>
    #if TARGET_OS_MAC
        // macOS
    #elif TARGET_OS_IPHONE
        // iOS
    #endif
#elif __linux__
    // Linux
#elif __FreeBSD__
    // FreeBSD
#elif __unix__
    // Generic Unix
#endif

// Architecture
#ifdef _M_X64 || __x86_64__ || __amd64__
    // x86_64 (64-bit)
#elif _M_IX86 || __i386__
    // x86 (32-bit)
#elif __aarch64__ || _M_ARM64
    // ARM64
#elif __arm__ || _M_ARM
    // ARM 32-bit
#endif

// Compiler
#ifdef _MSC_VER
    // Microsoft Visual C++
#elif __GNUC__
    // GCC or compatible
#elif __clang__
    // Clang
#endif
```

### CMake Platform Detection

```cmake
# Operating system
if(WIN32)
    message(STATUS "Building for Windows")
elseif(APPLE)
    message(STATUS "Building for macOS")
elseif(UNIX)
    message(STATUS "Building for Unix/Linux")
endif()

# Architecture
if(CMAKE_SIZEOF_VOID_P EQUAL 8)
    message(STATUS "64-bit build")
else()
    message(STATUS "32-bit build")
endif()

# Compiler
if(MSVC)
    message(STATUS "Using MSVC")
elseif(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
    message(STATUS "Using GCC")
elseif(CMAKE_CXX_COMPILER_ID STREQUAL "Clang")
    message(STATUS "Using Clang")
endif()
```

### Rust Platform Detection

```rust
// Rust conditional compilation
#[cfg(target_os = "windows")]
fn platform_specific() {
    println!("Windows");
}

#[cfg(target_os = "macos")]
fn platform_specific() {
    println!("macOS");
}

#[cfg(target_os = "linux")]
fn platform_specific() {
    println!("Linux");
}

#[cfg(target_arch = "x86_64")]
fn arch_specific() {
    println!("x86_64");
}

#[cfg(target_arch = "aarch64")]
fn arch_specific() {
    println!("ARM64");
}
```

## Conditional Compilation

### C/C++ Preprocessor

```c
// header.h - Cross-platform exports
#ifdef _WIN32
    #ifdef BUILD_DLL
        #define API_EXPORT __declspec(dllexport)
    #else
        #define API_EXPORT __declspec(dllimport)
    #endif
#else
    #define API_EXPORT __attribute__((visibility("default")))
#endif

// Usage
API_EXPORT void my_function();
```

```c
// Platform-specific includes
#ifdef _WIN32
    #include <windows.h>
    #include <winsock2.h>
#else
    #include <unistd.h>
    #include <sys/socket.h>
    #include <netinet/in.h>
#endif

// Platform-specific implementations
void sleep_ms(int ms) {
#ifdef _WIN32
    Sleep(ms);
#else
    usleep(ms * 1000);
#endif
}
```

### CMake Conditional Configuration

```cmake
# Platform-specific sources
if(WIN32)
    set(PLATFORM_SOURCES src/platform_win.cpp)
elseif(APPLE)
    set(PLATFORM_SOURCES src/platform_mac.cpp)
else()
    set(PLATFORM_SOURCES src/platform_linux.cpp)
endif()

add_library(mylib src/common.cpp ${PLATFORM_SOURCES})

# Platform-specific compile flags
if(WIN32)
    target_compile_definitions(mylib PRIVATE UNICODE _UNICODE)
    target_link_libraries(mylib PRIVATE ws2_32)
elseif(APPLE)
    target_link_libraries(mylib PRIVATE "-framework CoreFoundation")
else()
    target_link_libraries(mylib PRIVATE pthread dl)
endif()
```

### Cargo Platform-Specific Dependencies

```toml
# Cargo.toml
[dependencies]
# Common dependencies
serde = "1.0"

# Platform-specific dependencies
[target.'cfg(windows)'.dependencies]
winapi = { version = "0.3", features = ["winuser", "winsock2"] }

[target.'cfg(unix)'.dependencies]
libc = "0.2"

[target.'cfg(target_os = "macos")'.dependencies]
core-foundation = "0.9"
```

## CMake Cross-Compilation

### Toolchain Files

```cmake
# toolchain-arm-linux.cmake
set(CMAKE_SYSTEM_NAME Linux)
set(CMAKE_SYSTEM_PROCESSOR arm)

# Cross-compiler paths
set(CMAKE_C_COMPILER arm-linux-gnueabihf-gcc)
set(CMAKE_CXX_COMPILER arm-linux-gnueabihf-g++)

# Sysroot (target system root)
set(CMAKE_SYSROOT /usr/arm-linux-gnueabihf)
set(CMAKE_FIND_ROOT_PATH /usr/arm-linux-gnueabihf)

# Search paths
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)

# Compiler flags
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -march=armv7-a -mfpu=neon")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -march=armv7-a -mfpu=neon")
```

```bash
# Use toolchain file
cmake -DCMAKE_TOOLCHAIN_FILE=toolchain-arm-linux.cmake ..
cmake --build .
```

### Windows Toolchain on Linux (MinGW)

```cmake
# toolchain-mingw-w64.cmake
set(CMAKE_SYSTEM_NAME Windows)
set(CMAKE_SYSTEM_PROCESSOR x86_64)

set(CMAKE_C_COMPILER x86_64-w64-mingw32-gcc)
set(CMAKE_CXX_COMPILER x86_64-w64-mingw32-g++)
set(CMAKE_RC_COMPILER x86_64-w64-mingw32-windres)

set(CMAKE_FIND_ROOT_PATH /usr/x86_64-w64-mingw32)
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)

# Link statically to avoid DLL dependencies
set(CMAKE_EXE_LINKER_FLAGS "-static-libgcc -static-libstdc++")
```

```bash
# Build Windows executable on Linux
cmake -DCMAKE_TOOLCHAIN_FILE=toolchain-mingw-w64.cmake ..
cmake --build .
# Output: myapp.exe (Windows executable)
```

## Zig Cross-Compilation

### Zig as Cross-Compiler

```bash
# Zig provides cross-compilation out of the box (no toolchain setup)

# List targets
zig targets

# Cross-compile C/C++ for Windows on Linux
zig cc main.c -target x86_64-windows-gnu -o main.exe

# Cross-compile for ARM64 Linux
zig cc main.c -target aarch64-linux-gnu -o main

# Cross-compile for macOS (requires SDK)
zig cc main.c -target x86_64-macos -o main

# With CMake
CC="zig cc -target x86_64-windows-gnu" cmake ..
```

### Zig Build System Cross-Compilation

```zig
// build.zig
const std = @import("std");

pub fn build(b: *std.Build) void {
    // Target can be overridden: zig build -Dtarget=x86_64-windows
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    const exe = b.addExecutable(.{
        .name = "myapp",
        .root_source_file = .{ .path = "src/main.zig" },
        .target = target,
        .optimize = optimize,
    });

    b.installArtifact(exe);
}
```

```bash
# Cross-compile with Zig
zig build -Dtarget=x86_64-windows     # Windows
zig build -Dtarget=aarch64-linux      # ARM64 Linux
zig build -Dtarget=x86_64-macos       # macOS
zig build -Dtarget=wasm32-freestanding # WebAssembly
```

## Cargo Cross-Compilation

### Cross Tool

```bash
# Install cross (wrapper around Cargo)
cargo install cross

# Cross-compile for different targets
cross build --target x86_64-pc-windows-gnu
cross build --target aarch64-unknown-linux-gnu
cross build --target armv7-unknown-linux-gnueabihf

# List targets
rustc --print target-list
```

### Manual Cross-Compilation

```bash
# Add target
rustup target add x86_64-pc-windows-gnu
rustup target add aarch64-unknown-linux-gnu

# Build for target
cargo build --target x86_64-pc-windows-gnu
cargo build --target aarch64-unknown-linux-gnu
```

### Cargo Config for Cross-Compilation

```toml
# .cargo/config.toml
[target.x86_64-pc-windows-gnu]
linker = "x86_64-w64-mingw32-gcc"

[target.aarch64-unknown-linux-gnu]
linker = "aarch64-linux-gnu-gcc"
```

## Platform-Specific Code Patterns

### File Paths

```c
// C - Platform-specific path separators
#ifdef _WIN32
    #define PATH_SEPARATOR '\\'
    #define PATH_SEPARATOR_STR "\\"
#else
    #define PATH_SEPARATOR '/'
    #define PATH_SEPARATOR_STR "/"
#endif

// Build path
char path[256];
snprintf(path, sizeof(path), "data%s%s", PATH_SEPARATOR_STR, "config.txt");
```

```rust
// Rust - Use std::path (automatically handles platform differences)
use std::path::{Path, PathBuf};

let path = Path::new("data").join("config.txt");
// Windows: data\config.txt
// Unix: data/config.txt
```

### Sockets

```c
// C - Cross-platform socket initialization
#ifdef _WIN32
    WSADATA wsa_data;
    WSAStartup(MAKEWORD(2, 2), &wsa_data);
    SOCKET sock = socket(AF_INET, SOCK_STREAM, 0);
    // Use sock...
    closesocket(sock);
    WSACleanup();
#else
    int sock = socket(AF_INET, SOCK_STREAM, 0);
    // Use sock...
    close(sock);
#endif
```

### Dynamic Libraries

```c
// C - Cross-platform dynamic library loading
#ifdef _WIN32
    HMODULE handle = LoadLibraryA("mylib.dll");
    void* symbol = GetProcAddress(handle, "my_function");
    FreeLibrary(handle);
#else
    void* handle = dlopen("libmylib.so", RTLD_LAZY);
    void* symbol = dlsym(handle, "my_function");
    dlclose(handle);
#endif
```

```rust
// Rust - Use libloading crate (cross-platform)
use libloading::{Library, Symbol};

let lib = Library::new("mylib.so")?;
let func: Symbol<fn() -> i32> = lib.get(b"my_function")?;
let result = func();
```

## Platform-Specific Optimizations

### Compiler Flags

```cmake
# CMake - Platform-specific optimizations
if(WIN32)
    target_compile_options(mylib PRIVATE /O2 /GL)
    target_link_options(mylib PRIVATE /LTCG)
elseif(CMAKE_CXX_COMPILER_ID STREQUAL "GNU" OR CMAKE_CXX_COMPILER_ID STREQUAL "Clang")
    target_compile_options(mylib PRIVATE -O3 -march=native -flto)
    target_link_options(mylib PRIVATE -flto)
endif()
```

### SIMD Intrinsics

```c
// C - Platform-specific SIMD
#include <stdint.h>

void add_vectors(float* a, float* b, float* c, size_t n) {
#if defined(__SSE__) && (defined(__x86_64__) || defined(_M_X64))
    // x86_64 SSE
    #include <xmmintrin.h>
    for (size_t i = 0; i < n; i += 4) {
        __m128 va = _mm_load_ps(&a[i]);
        __m128 vb = _mm_load_ps(&b[i]);
        __m128 vc = _mm_add_ps(va, vb);
        _mm_store_ps(&c[i], vc);
    }
#elif defined(__ARM_NEON)
    // ARM NEON
    #include <arm_neon.h>
    for (size_t i = 0; i < n; i += 4) {
        float32x4_t va = vld1q_f32(&a[i]);
        float32x4_t vb = vld1q_f32(&b[i]);
        float32x4_t vc = vaddq_f32(va, vb);
        vst1q_f32(&c[i], vc);
    }
#else
    // Fallback scalar code
    for (size_t i = 0; i < n; i++) {
        c[i] = a[i] + b[i];
    }
#endif
}
```

## Testing Multi-Platform Builds

### CI/CD Matrix Testing

```yaml
# .github/workflows/cross-platform.yml
name: Cross-Platform Build

on: [push, pull_request]

jobs:
  build:
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        arch: [x86_64]
        include:
          - os: ubuntu-latest
            arch: aarch64

    runs-on: ${{ matrix.os }}

    steps:
      - uses: actions/checkout@v4

      - name: Build
        run: |
          mkdir build
          cd build
          cmake ..
          cmake --build .

      - name: Test
        run: |
          cd build
          ctest --output-on-failure
```

### Docker for Cross-Platform Testing

```dockerfile
# Dockerfile.cross - Multi-platform build
FROM --platform=$BUILDPLATFORM debian:bookworm AS builder

ARG TARGETPLATFORM
ARG BUILDPLATFORM

RUN apt-get update && apt-get install -y \
    gcc-aarch64-linux-gnu \
    gcc-x86-64-linux-gnu \
    cmake

COPY . /src
WORKDIR /src/build

RUN if [ "$TARGETPLATFORM" = "linux/arm64" ]; then \
        cmake -DCMAKE_TOOLCHAIN_FILE=../toolchain-arm64.cmake .. ; \
    else \
        cmake .. ; \
    fi && \
    cmake --build .

# Build for multiple platforms
# docker buildx build --platform linux/amd64,linux/arm64 -t myapp:latest .
```

## Anti-Patterns

### ❌ Hardcoded Platform Assumptions

```c
// WRONG: Assumes Unix-like system
void read_config() {
    FILE* f = fopen("/etc/myapp/config.txt", "r");  // Fails on Windows
}

// CORRECT: Use platform-appropriate paths
#ifdef _WIN32
    const char* config_path = "C:\\ProgramData\\MyApp\\config.txt";
#else
    const char* config_path = "/etc/myapp/config.txt";
#endif
```

### ❌ Not Testing on Target Platforms

```bash
# WRONG: Only test on developer machine (macOS)
# Ship to production (Linux) without testing

# CORRECT: Use CI matrix to test all platforms
# See CI/CD matrix example above
```

### ❌ Mixing Platform-Specific APIs

```c
// WRONG: Mix Windows and POSIX APIs
#include <windows.h>
#include <pthread.h>  // Won't compile on Windows

// CORRECT: Use conditional compilation
#ifdef _WIN32
    #include <windows.h>
#else
    #include <pthread.h>
#endif
```

### ❌ Ignoring Endianness

```c
// WRONG: Assume little-endian (x86)
uint32_t value = *(uint32_t*)buffer;

// CORRECT: Handle endianness explicitly
#include <stdint.h>

uint32_t read_le32(const uint8_t* buf) {
    return (uint32_t)buf[0]
         | ((uint32_t)buf[1] << 8)
         | ((uint32_t)buf[2] << 16)
         | ((uint32_t)buf[3] << 24);
}
```

## Quick Reference

### Platform Detection Macros

```c
// OS Detection
_WIN32          // Windows (32 or 64-bit)
_WIN64          // Windows 64-bit
__APPLE__       // macOS, iOS
__linux__       // Linux
__unix__        // Unix-like
__FreeBSD__     // FreeBSD

// Architecture
__x86_64__      // x86_64 (GCC/Clang)
_M_X64          // x86_64 (MSVC)
__i386__        // x86 (GCC/Clang)
_M_IX86         // x86 (MSVC)
__aarch64__     // ARM64 (GCC/Clang)
_M_ARM64        // ARM64 (MSVC)
__arm__         // ARM32
__wasm32__      // WebAssembly

// Compiler
_MSC_VER        // MSVC
__GNUC__        // GCC
__clang__       // Clang
```

### CMake Cross-Compilation

```bash
# ARM Linux
cmake -DCMAKE_TOOLCHAIN_FILE=toolchain-arm.cmake ..

# Windows on Linux (MinGW)
cmake -DCMAKE_TOOLCHAIN_FILE=toolchain-mingw.cmake ..

# Android
cmake -DCMAKE_TOOLCHAIN_FILE=$ANDROID_NDK/build/cmake/android.toolchain.cmake \
      -DANDROID_ABI=arm64-v8a ..
```

### Zig Cross-Compilation Targets

```bash
# Common targets
x86_64-linux-gnu          # Linux x86_64
aarch64-linux-gnu         # Linux ARM64
x86_64-windows-gnu        # Windows x86_64
x86_64-macos              # macOS x86_64
aarch64-macos             # macOS ARM64 (Apple Silicon)
wasm32-freestanding       # WebAssembly
```

## Python Integration Example

```python
# detect_platform.py - Platform detection and configuration
import platform
import sys

def detect_platform():
    """Detect platform and generate build configuration."""
    os_type = platform.system()  # 'Windows', 'Darwin', 'Linux'
    machine = platform.machine()  # 'x86_64', 'arm64', 'AMD64', etc.

    config = {
        'os': os_type.lower(),
        'arch': machine.lower(),
        'compiler': 'msvc' if os_type == 'Windows' else 'gcc',
        'shared_ext': {
            'Windows': '.dll',
            'Darwin': '.dylib',
            'Linux': '.so',
        }.get(os_type, '.so'),
    }

    return config

if __name__ == '__main__':
    config = detect_platform()
    print(f"OS: {config['os']}")
    print(f"Architecture: {config['arch']}")
    print(f"Compiler: {config['compiler']}")
    print(f"Shared library extension: {config['shared_ext']}")

# Generate CMake config
# cmake -DPLATFORM_OS={config['os']} -DPLATFORM_ARCH={config['arch']} ..
```

## Related Skills

- `cmake-patterns.md` - CMake configuration for cross-platform builds
- `build-system-selection.md` - Choosing build systems
- `zig-build-system.md` - Zig cross-compilation features
- `zig-cross-compilation.md` - Advanced Zig cross-compilation
- `build-optimization.md` - Build performance
- `cicd/ci-optimization.md` - CI/CD for multi-platform testing

## Summary

Cross-platform development requires careful attention to platform differences and systematic testing:

**Key Takeaways**:
1. **Platform detection** - Use preprocessor macros or build system detection
2. **Conditional compilation** - Isolate platform-specific code with `#ifdef`
3. **Toolchain files** - Use CMake toolchain files for cross-compilation
4. **Zig advantage** - Zig provides zero-setup cross-compilation
5. **Test all platforms** - Use CI matrix testing for validation
6. **Abstract platform APIs** - Create platform-agnostic interfaces
7. **Handle edge cases** - Endianness, path separators, line endings
8. **Cross-compilation** - Build for target platforms from development machine

**Best Practices**:
- Prefer cross-platform libraries (Rust std, C++ std::filesystem)
- Use platform detection in build system, not just source code
- Test on actual target platforms, not just cross-compiled binaries
- Document platform-specific requirements and limitations

**2024 Tooling**:
- **Zig**: Zero-setup cross-compilation (best DX)
- **CMake**: Mature cross-platform builds (most ecosystem support)
- **Cargo + cross**: Easy Rust cross-compilation
- **Docker buildx**: Multi-platform container builds

Cross-platform development is essential for modern software, and tools like Zig are making it increasingly accessible.
