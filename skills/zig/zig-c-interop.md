---
name: zig-c-interop
description: Calling C libraries from Zig
---



# Zig C Interoperability

**Use this skill when:**
- Calling C libraries from Zig
- Linking C code
- Working with C headers
- Interfacing with system libraries
- Building hybrid C/Zig projects

## Linking C Libraries

### In build.zig

```zig
const std = @import("std");

pub fn build(b: *std.Build) void {
    const exe = b.addExecutable(.{
        .name = "app",
        .root_source_file = .{ .path = "src/main.zig" },
        .target = target,
        .optimize = optimize,
    });

    // Link libc
    exe.linkLibC();

    // Link system library
    exe.linkSystemLibrary("sqlite3");

    // Add C source files
    exe.addCSourceFile(.{
        .file = .{ .path = "src/helper.c" },
        .flags = &.{"-std=c11"},
    });

    // Add include path
    exe.addIncludePath(.{ .path = "include" });

    b.installArtifact(exe);
}
```

## Calling C Functions

```zig
const c = @cImport({
    @cInclude("stdio.h");
    @cInclude("sqlite3.h");
});

pub fn main() !void {
    // Call C function
    _ = c.printf("Hello from C!\n");

    // Use C types
    var db: ?*c.sqlite3 = null;
    const rc = c.sqlite3_open(":memory:", &db);

    if (rc != c.SQLITE_OK) {
        return error.DatabaseError;
    }
    defer _ = c.sqlite3_close(db);
}
```

## C Types in Zig

```zig
// C integer types
c_int       // int
c_uint      // unsigned int
c_long      // long
c_ulong     // unsigned long

// Pointers
[*c]u8      // C pointer (nullable, can be null)
[*]u8       // Zig many-item pointer (not nullable)

// Strings
const c_str: [*:0]const u8 = "C string";  // Null-terminated
```

## Exporting Zig to C

```zig
// Export function for C
export fn add(a: c_int, b: c_int) c_int {
    return a + b;
}

// Use from C:
// extern int add(int a, int b);
```

## Related Skills

- **zig-build-system.md** - Build configuration
- **zig-memory-management.md** - Managing C memory
