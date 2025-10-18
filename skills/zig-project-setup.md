---
name: zig-project-setup
description: Initializing new Zig projects
---



# Zig Project Setup

**Use this skill when:**
- Initializing new Zig projects
- Organizing Zig codebases
- Setting up project structure
- Configuring build.zig
- Working with Zig 0.13.x+

## Project Initialization

```bash
# Create executable project
zig init-exe
# Creates: src/main.zig, build.zig, build.zig.zon

# Create library project
zig init-lib
# Creates: src/root.zig, build.zig, build.zig.zon
```

## Project Structure

```
my-project/
├── build.zig          # Build configuration
├── build.zig.zon      # Dependencies
├── src/
│   ├── main.zig       # Entry point (exe)
│   └── lib.zig        # Library root
├── tests/
│   └── test.zig       # Tests
└── README.md
```

## Basic main.zig

```zig
const std = @import("std");

pub fn main() !void {
    const stdout = std.io.getStdOut().writer();
    try stdout.print("Hello, {s}!\n", .{"World"});
}
```

## Related Skills

- **zig-build-system.md** - Configure build.zig
- **zig-testing.md** - Test organization
- **zig-package-management.md** - Manage dependencies
