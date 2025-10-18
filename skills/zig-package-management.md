---
name: zig-package-management
description: Adding dependencies to Zig projects
---



# Zig Package Management

**Use this skill when:**
- Adding dependencies to Zig projects
- Managing build.zig.zon
- Working with Zig package manager
- Vendoring dependencies
- Creating reusable packages

## build.zig.zon

```zig
.{
    .name = "my-project",
    .version = "0.1.0",
    .dependencies = .{
        .@"some-package" = .{
            .url = "https://github.com/user/package/archive/main.tar.gz",
            .hash = "1220abcdef...",
        },
    },
    .paths = .{
        "build.zig",
        "build.zig.zon",
        "src",
    },
}
```

## Adding Dependencies

```bash
# Zig will prompt for hash on first build
zig build

# Or fetch manually
zig fetch --save https://github.com/user/package/archive/main.tar.gz
```

## Using Dependencies in build.zig

```zig
pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    const exe = b.addExecutable(.{
        .name = "my-app",
        .root_source_file = .{ .path = "src/main.zig" },
        .target = target,
        .optimize = optimize,
    });

    // Add dependency
    const pkg = b.dependency("some-package", .{
        .target = target,
        .optimize = optimize,
    });

    exe.root_module.addImport("pkg", pkg.module("pkg"));

    b.installArtifact(exe);
}
```

## Using Imported Packages

```zig
const std = @import("std");
const pkg = @import("pkg");

pub fn main() !void {
    pkg.doSomething();
}
```

## Related Skills

- **zig-build-system.md** - Build configuration
- **zig-project-setup.md** - Project structure
