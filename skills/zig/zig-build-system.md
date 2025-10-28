---
name: zig-build-system
description: Configuring build.zig
---



# Zig Build System

**Use this skill when:**
- Configuring build.zig
- Adding dependencies
- Cross-compiling projects
- Creating build steps
- Managing build options

## Basic build.zig

```zig
const std = @import("std");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    const exe = b.addExecutable(.{
        .name = "my-app",
        .root_source_file = .{ .path = "src/main.zig" },
        .target = target,
        .optimize = optimize,
    });

    b.installArtifact(exe);

    const run_cmd = b.addRunArtifact(exe);
    run_cmd.step.dependOn(b.getInstallStep());

    const run_step = b.step("run", "Run the app");
    run_step.dependOn(&run_cmd.step);
}
```

## Build Commands

```bash
# Build project
zig build

# Run project
zig build run

# Build and run tests
zig build test

# Clean build artifacts - safe to run
rm -rf zig-out zig-cache

# Build for release
zig build -Doptimize=ReleaseFast
```

## Cross-Compilation

```zig
// In build.zig - specify target
const target = b.resolveTargetQuery(.{
    .cpu_arch = .x86_64,
    .os_tag = .linux,
});

const exe = b.addExecutable(.{
    .name = "my-app",
    .root_source_file = .{ .path = "src/main.zig" },
    .target = target,
    .optimize = optimize,
});
```

```bash
# Cross-compile for different targets
zig build -Dtarget=x86_64-linux
zig build -Dtarget=aarch64-macos
zig build -Dtarget=x86_64-windows
```

## Related Skills

- **zig-project-setup.md** - Project initialization
- **zig-testing.md** - Test configuration
- **zig-package-management.md** - External dependencies
