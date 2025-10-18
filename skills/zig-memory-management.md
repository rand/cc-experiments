---
name: zig-memory-management
description: Managing memory in Zig
---



# Zig Memory Management

**Use this skill when:**
- Managing memory in Zig
- Using allocators correctly
- Implementing defer/errdefer
- Avoiding memory leaks
- Understanding Zig's explicit allocation

## Allocators

### Using Allocators

```zig
const std = @import("std");

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    // Allocate memory
    const bytes = try allocator.alloc(u8, 100);
    defer allocator.free(bytes);

    // Use bytes
}
```

### Common Allocators

```zig
// General Purpose Allocator (recommended for most cases)
var gpa = std.heap.GeneralPurposeAllocator(.{}){};
const allocator = gpa.allocator();

// Arena Allocator (free all at once)
var arena = std.heap.ArenaAllocator.init(std.heap.page_allocator);
defer arena.deinit();
const allocator = arena.allocator();

// Fixed Buffer Allocator (stack-based)
var buffer: [1024]u8 = undefined;
var fba = std.heap.FixedBufferAllocator.init(&buffer);
const allocator = fba.allocator();

// Page Allocator (direct mmap)
const allocator = std.heap.page_allocator;
```

## defer and errdefer

### Resource Cleanup

```zig
fn processFile(path: []const u8) !void {
    const file = try std.fs.cwd().openFile(path, .{});
    defer file.close();  // Always runs

    const content = try file.readToEndAlloc(allocator, 1024 * 1024);
    defer allocator.free(content);  // Always runs

    // Process content
}

fn riskyOperation() !void {
    const resource = try allocate();
    errdefer deallocate(resource);  // Only runs on error

    try doSomethingThatMightFail();

    // If we get here, caller owns resource
    return resource;
}
```

## Memory Safety Patterns

```zig
// ✅ GOOD - Explicit ownership
fn createBuffer(allocator: std.mem.Allocator) ![]u8 {
    return try allocator.alloc(u8, 100);
}

// Caller owns and must free
const buf = try createBuffer(allocator);
defer allocator.free(buf);

// ❌ BAD - Unclear ownership
fn badFunction() []u8 {
    var buf: [100]u8 = undefined;  // Stack memory!
    return buf[0..];  // Dangling pointer!
}
```

## ArrayList

```zig
var list = std.ArrayList(i32).init(allocator);
defer list.deinit();

try list.append(42);
try list.append(43);

for (list.items) |item| {
    std.debug.print("{}\n", .{item});
}
```

## Related Skills

- **zig-testing.md** - Testing allocators
- **zig-build-system.md** - Build configuration
- **zig-c-interop.md** - Managing C memory
