# Example 6: Valgrind Memory Leak Detection

This example demonstrates memory leak detection and analysis using Valgrind Memcheck and Massif for C/C++ applications.

## Prerequisites

```bash
# Ubuntu/Debian
sudo apt-get install valgrind

# CentOS/RHEL
sudo yum install valgrind

# macOS (limited support)
# Valgrind support on macOS is incomplete, use alternative tools:
# - leaks (built-in)
# - Instruments (Xcode)
```

## Sample C Application with Leaks

```c
// memory_leaks.c
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

// Leak 1: Memory allocated but never freed
char* create_string(const char* text) {
    char* result = malloc(strlen(text) + 1);
    strcpy(result, text);
    return result;  // Caller forgets to free
}

// Leak 2: Lost pointer to allocated memory
void lost_pointer() {
    char* data = malloc(100);
    strcpy(data, "temporary");
    data = NULL;  // Lost reference, cannot free
}

// Leak 3: Incorrect deallocation in array
void array_leak() {
    char** strings = malloc(10 * sizeof(char*));

    for (int i = 0; i < 10; i++) {
        strings[i] = malloc(50);
        sprintf(strings[i], "String %d", i);
    }

    // Only free outer array, not individual strings
    free(strings);  // Inner allocations leaked
}

// Correct pattern (for comparison)
void no_leak() {
    char* temp = malloc(100);
    strcpy(temp, "temporary data");
    // Use temp
    free(temp);  // Properly freed
}

// Buffer overflow
void buffer_overflow() {
    char* buffer = malloc(10);
    strcpy(buffer, "This string is too long!");  // Overflow!
    free(buffer);
}

// Use after free
void use_after_free() {
    char* data = malloc(50);
    strcpy(data, "hello");
    free(data);
    printf("%s\n", data);  // Use after free!
}

// Double free
void double_free() {
    char* data = malloc(50);
    free(data);
    free(data);  // Double free!
}

int main() {
    printf("Running memory leak examples...\n");

    // Leaks
    char* str = create_string("test");  // Leaked
    lost_pointer();
    array_leak();

    // Correct usage
    no_leak();

    // Errors (uncomment to test)
    // buffer_overflow();
    // use_after_free();
    // double_free();

    printf("Completed\n");
    return 0;
}
```

```bash
# Compile with debug symbols (no optimization for clear stack traces)
gcc -g -O0 -o memory_leaks memory_leaks.c
```

## Memcheck: Memory Error Detection

### Basic Leak Check

```bash
# Full leak check
valgrind --leak-check=full ./memory_leaks

# Show reachable blocks
valgrind --leak-check=full --show-leak-kinds=all ./memory_leaks

# Track origins of uninitialized values
valgrind --leak-check=full --track-origins=yes ./memory_leaks
```

### Example Output

```
==12345== Memcheck, a memory error detector
==12345== Copyright (C) 2002-2017, and GNU GPL'd, by Julian Seward et al.
==12345== Using Valgrind-3.15.0 and LibVEX; rerun with -h for copyright info
==12345== Command: ./memory_leaks
==12345==
Running memory leak examples...
Completed
==12345==
==12345== HEAP SUMMARY:
==12345==     in use at exit: 555 bytes in 12 blocks
==12345==   total heap usage: 15 allocs, 3 frees, 1,155 bytes allocated
==12345==
==12345== 5 bytes in 1 blocks are definitely lost in loss record 1 of 3
==12345==    at 0x4C2FB0F: malloc (in /usr/lib/valgrind/vgpreload_memcheck-amd64-linux.so)
==12345==    by 0x108678: create_string (memory_leaks.c:8)
==12345==    by 0x1087BC: main (memory_leaks.c:54)
==12345==
==12345== 100 bytes in 1 blocks are definitely lost in loss record 2 of 3
==12345==    at 0x4C2FB0F: malloc (in /usr/lib/valgrind/vgpreload_memcheck-amd64-linux.so)
==12345==    by 0x1086A4: lost_pointer (memory_leaks.c:15)
==12345==    by 0x1087C4: main (memory_leaks.c:55)
==12345==
==12345== 450 bytes in 10 blocks are definitely lost in loss record 3 of 3
==12345==    at 0x4C2FB0F: malloc (in /usr/lib/valgrind/vgpreload_memcheck-amd64-linux.so)
==12345==    by 0x1086D8: array_leak (memory_leaks.c:22)
==12345==    by 0x1087CC: main (memory_leaks.c:56)
==12345==
==12345== LEAK SUMMARY:
==12345==    definitely lost: 555 bytes in 12 blocks
==12345==    indirectly lost: 0 bytes in 0 blocks
==12345==      possibly lost: 0 bytes in 0 blocks
==12345==    still reachable: 0 bytes in 0 blocks
==12345==         suppressed: 0 bytes in 0 blocks
==12345==
==12345== For lists of detected and suppressed errors, rerun with: -s
==12345== ERROR SUMMARY: 3 errors from 3 contexts (suppressed: 0 from 0)
```

### Interpreting Leak Types

1. **Definitely lost**: Memory leaked, no pointers to it
   - **Fix**: Find allocation site and add free()

2. **Indirectly lost**: Memory leaked via lost parent structure
   - **Fix**: Fix parent leak, children will be freed

3. **Possibly lost**: Pointers exist but point to middle of block
   - **Investigate**: May be legitimate or leak

4. **Still reachable**: Allocated but not freed, pointer exists
   - **Usually OK**: Global or static allocations
   - **Fix if needed**: Add cleanup code

## Advanced Memcheck Features

### Detect Invalid Reads/Writes

```c
// invalid_access.c
#include <stdlib.h>
#include <string.h>

int main() {
    char* buffer = malloc(10);

    // Invalid write (buffer overflow)
    buffer[10] = 'x';  // Index 10 is out of bounds

    // Invalid read
    char c = buffer[15];

    free(buffer);

    // Invalid free
    free(buffer + 5);  // Freeing non-heap pointer

    return 0;
}
```

```bash
valgrind --leak-check=full ./invalid_access
```

**Output shows**:
- Invalid write of size 1
- Invalid read of size 1
- Invalid free() / delete / delete[]

### Uninitialized Value Detection

```c
// uninitialized.c
#include <stdio.h>

int main() {
    int x;  // Uninitialized
    int y = x + 5;  // Use of uninitialized value
    printf("y = %d\n", y);
    return 0;
}
```

```bash
valgrind --track-origins=yes ./uninitialized
```

**Output**:
```
==12345== Conditional jump or move depends on uninitialised value(s)
==12345==    at 0x4E8B6A0: printf (printf.c:35)
==12345==    by 0x108654: main (uninitialized.c:6)
==12345==  Uninitialised value was created by a stack allocation
==12345==    at 0x108640: main (uninitialized.c:3)
```

## Massif: Heap Profiling

### Profile Heap Usage Over Time

```bash
# Run with Massif
valgrind --tool=massif --massif-out-file=massif.out ./memory_leaks

# View report
ms_print massif.out
```

### Example Massif Output

```
    KB
19.63^                                                                       #
     |                                                                       #
     |                                                                       #
     |                                                                       #
     |                                                                       #
     |                                                                       #
     |                                                                       @
     |                                                                      @@
     |                                                                     @@@
     |                                                                    @@@@
   0 +----------------------------------------------------------------------->Ki
     0                                                                   100.0

Number of snapshots: 50
 Detailed snapshots: [9, 19, 29, 39, 49]

--------------------------------------------------------------------------------
  n        time(i)         total(B)   useful-heap(B) extra-heap(B)    stacks(B)
--------------------------------------------------------------------------------
  0              0                0                0             0            0
  9      1,234,567        1,000,000          950,000        50,000            0
 19      2,345,678        1,500,000        1,450,000        50,000            0
 29      3,456,789        2,000,000        1,950,000        50,000            0
```

### Detailed Snapshot Analysis

```bash
# More frequent snapshots
valgrind --tool=massif --detailed-freq=1 --massif-out-file=massif.out ./memory_leaks

# Analyze specific snapshot
ms_print massif.out | less
```

**Snapshot details**:
```
92.31% (1,844,000B) (heap allocation functions) malloc/new/new[]
├─ 50.00% (1,000,000B) in 1 blocks
│  └─ 0x108678: create_string (memory_leaks.c:8)
│     └─ 0x1087BC: main (memory_leaks.c:54)
│
└─ 42.31% (844,000B) in 844 blocks
   └─ 0x1086D8: array_leak (memory_leaks.c:22)
      └─ 0x1087CC: main (memory_leaks.c:56)
```

### Massif Visualizer (GUI)

```bash
# Install
sudo apt-get install massif-visualizer

# Visualize
massif-visualizer massif.out
```

**Features**:
- Timeline graph of memory usage
- Allocation tree view
- Filter by allocation site
- Export to PNG/SVG

## Suppression Files

### Generate Suppressions for Known Issues

```bash
# Generate suppression entries
valgrind --leak-check=full --gen-suppressions=all ./memory_leaks 2>&1 | \
    grep -A 5 "insert_a_suppression" > suppressions.supp
```

### Use Suppression File

```bash
valgrind --leak-check=full --suppressions=suppressions.supp ./memory_leaks
```

### Example Suppression Entry

```
{
   ignore_glibc_leak
   Memcheck:Leak
   match-leak-kinds: reachable
   fun:malloc
   fun:_dl_init
   obj:/lib/x86_64-linux-gnu/ld-2.27.so
}
```

## CI/CD Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/memcheck.yml
name: Memory Check

on: [push, pull_request]

jobs:
  memcheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install Valgrind
        run: sudo apt-get install -y valgrind

      - name: Build
        run: gcc -g -O0 -o memory_leaks memory_leaks.c

      - name: Run Memcheck
        run: |
          valgrind --leak-check=full --errors-for-leak-kinds=definite \
            --error-exitcode=1 ./memory_leaks

      - name: Upload Valgrind Report
        if: failure()
        uses: actions/upload-artifact@v3
        with:
          name: valgrind-report
          path: valgrind.log
```

### Pre-Commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

echo "Running memory leak check..."

# Build test binary
make test_binary

# Run Valgrind
valgrind --leak-check=full --error-exitcode=1 --quiet ./test_binary

if [ $? -ne 0 ]; then
    echo "Memory leaks detected! Fix before committing."
    exit 1
fi

echo "Memory check passed."
```

## C++ Specific Considerations

### C++ Memory Management

```cpp
// memory_leaks.cpp
#include <string>
#include <vector>

class DataHolder {
public:
    DataHolder() {
        data = new int[100];  // Manual allocation
    }
    ~DataHolder() {
        // Missing: delete[] data; causes leak
    }
private:
    int* data;
};

void cpp_leaks() {
    // Leak 1: Missing delete
    DataHolder* holder = new DataHolder();  // Never deleted

    // Leak 2: Exception safety
    std::string* str = new std::string("test");
    // If exception thrown here, str is leaked
    throw std::runtime_error("Error!");
    delete str;  // Never reached

    // Correct: Use RAII
    std::vector<int> vec(100);  // Automatically managed
    std::string text = "test";  // Automatically managed
}
```

### Valgrind with C++

```bash
# Compile C++
g++ -g -O0 -o memory_leaks_cpp memory_leaks.cpp

# Run with C++ demangling
valgrind --leak-check=full --demangle=yes ./memory_leaks_cpp
```

## Alternatives to Valgrind

### AddressSanitizer (ASan)

```bash
# Compile with ASan (much faster than Valgrind)
gcc -g -O1 -fsanitize=address -fno-omit-frame-pointer -o memory_leaks memory_leaks.c

# Run (no Valgrind needed)
./memory_leaks

# ASan detects:
# - Use-after-free
# - Heap buffer overflow
# - Stack buffer overflow
# - Use after return
# - Memory leaks (with ASAN_OPTIONS=detect_leaks=1)
```

**Comparison**:
- **Valgrind**: More comprehensive, higher overhead (10-100x)
- **ASan**: Faster (2x overhead), requires recompilation

## Best Practices

1. **Compile with debug symbols**: `-g` flag essential
2. **Disable optimizations**: `-O0` for clearer stack traces
3. **Run regularly**: Integrate into CI/CD
4. **Fix "definitely lost" first**: Highest priority
5. **Use suppressions sparingly**: Only for known false positives
6. **Profile representative workload**: Test realistic scenarios

## Troubleshooting

### Issue: Valgrind too slow

```bash
# Use ASan instead for development
gcc -fsanitize=address -g -o app app.c
./app

# Or reduce Valgrind checks
valgrind --leak-check=no --tool=none ./app  # Fastest
```

### Issue: Too many false positives

```bash
# Use suppressions
valgrind --leak-check=full --gen-suppressions=all ./app 2>&1 | \
    tee suppressions.txt

# Edit suppressions.txt, then:
valgrind --suppressions=suppressions.txt ./app
```

### Issue: Missing symbols

```bash
# Ensure debug symbols installed
sudo apt-get install libc6-dbg libstdc++6-dbg

# Build with -g
gcc -g -o app app.c
```

## Summary

- **Valgrind Memcheck**: Comprehensive memory error detection
- **Massif**: Heap profiling and allocation tracking
- **Overhead**: 10-100x slowdown (development only)
- **Use Cases**: Memory leak detection, buffer overflow detection
- **Production Alternative**: AddressSanitizer (ASan)
- **Best Practice**: Run in CI/CD on every commit
