---
name: zig-testing
description: Writing unit tests in Zig
---



# Zig Testing

**Use this skill when:**
- Writing unit tests in Zig
- Organizing test code
- Testing allocators and memory
- Running test suites
- Debugging failed tests

## Basic Tests

```zig
const std = @import("std");
const testing = std.testing;

fn add(a: i32, b: i32) i32 {
    return a + b;
}

test "addition" {
    try testing.expect(add(2, 2) == 4);
    try testing.expectEqual(@as(i32, 4), add(2, 2));
}

test "string comparison" {
    try testing.expectEqualStrings("hello", "hello");
}
```

## Test Organization

```zig
// src/math.zig
pub fn multiply(a: i32, b: i32) i32 {
    return a * b;
}

test "multiply" {
    try testing.expectEqual(@as(i32, 6), multiply(2, 3));
}

// tests/test.zig
const math = @import("math");

test "math functions" {
    try testing.expect(math.multiply(2, 3) == 6);
}
```

## Running Tests

```bash
# Run all tests
zig build test

# Run specific test file
zig test src/main.zig

# Run with optimization
zig build test -Doptimize=ReleaseFast
```

## Testing Allocators

```zig
test "allocator test" {
    var arena = std.heap.ArenaAllocator.init(testing.allocator);
    defer arena.deinit();
    const allocator = arena.allocator();

    const list = try allocator.alloc(i32, 10);
    // Use list
    // Arena frees automatically
}
```

## Related Skills

- **zig-memory-management.md** - Testing memory safety
- **zig-build-system.md** - Test configuration
