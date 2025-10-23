---
name: code-patterns
description: Reference guide for detecting AI slop patterns in code including generic variable names, obvious comments, and unnecessary abstractions. Use as reference when reviewing code quality.
---

# Code Slop Patterns

This reference documents common "AI slop" patterns in code that indicate low-quality, AI-generated content that should be cleaned up.

## Table of Contents
- Naming Antipatterns
- Comment Antipatterns
- Structure Antipatterns
- Implementation Antipatterns
- Documentation Antipatterns

## Naming Antipatterns

### Overly Generic Names
**Bad:** `data`, `result`, `temp`, `value`, `item`, `thing`, `obj`, `info`

These names appear frequently in AI-generated code and provide no semantic meaning.

**Better:** Name things after what they represent:
- `userData` → `currentUser`, `userProfile`, `activeSession`
- `result` → `parsedDocument`, `sortedItems`, `validationError`
- `temp` → `formattedDate`, `normalizedInput`, `previousValue`

### Unnecessarily Verbose Names
**Bad:** `getUserDataFromDatabaseByUserIdAndReturnResult()`, `calculateTotalSumOfAllItemPricesInCart()`

**Better:** `getUser(userId)`, `calculateCartTotal()`

The function signature and context provide enough information.

### Generic Placeholder Patterns
Watch for repeated use of:
- `foo`, `bar`, `baz` in production code
- `test1`, `test2`, `test3` as function names
- `MyClass`, `MyFunction`, `MyVariable` prefixes
- `Helper`, `Manager`, `Handler` suffixes without specificity

## Comment Antipatterns

### Obvious Comments
Comments that restate what the code clearly does:

```python
# Bad
# Create a user
user = User()

# Increment the counter
counter += 1

# Return the result
return result

# Loop through the items
for item in items:
    process(item)
```

**Rule:** If the code is self-documenting, delete the comment.

### Generic TODO Comments
```python
# Bad
# TODO: Implement this function
# TODO: Add error handling
# TODO: Optimize this code
# TODO: Refactor this

# Better
# TODO(user): Handle case where API returns 429 rate limit
# TODO(user): Profile this loop - suspected O(n²) bottleneck with n>10000
```

Include WHO should do it, WHAT specifically, and WHY if not obvious.

### Over-Explained Simple Logic
```python
# Bad
# Check if the user is authenticated by examining the session token
# and verifying it matches our stored tokens in the database
if session.token in valid_tokens:
    # If authenticated, proceed with the request
    process_request()
```

**Better:** Just write clear code, or if truly complex, explain the business rule, not the syntax.

### Comment Blocks That Announce Sections
```python
# Bad
########################################
# INITIALIZATION
########################################

########################################
# MAIN PROCESSING LOGIC
########################################
```

**Better:** Use functions or classes to organize code. Comments shouldn't be needed to show structure.

## Structure Antipatterns

### Unnecessary Abstraction Layers
```python
# Bad - AI-generated overengineering
class UserManagerFactory:
    def create_user_manager(self):
        return UserManager()

class UserManager:
    def get_user_repository(self):
        return UserRepository()

class UserRepository:
    def get_user(self, user_id):
        return db.query(User).filter(User.id == user_id).first()

# Better
def get_user(user_id):
    return db.query(User).filter(User.id == user_id).first()
```

**Rule:** Don't add abstraction layers until you need them. YAGNI.

### Over-Use of Design Patterns
Not everything needs to be:
- Factory Pattern
- Singleton Pattern
- Observer Pattern
- Strategy Pattern
- Adapter Pattern

Use patterns when they solve real problems, not because you learned about them.

### Generic Error Handling
```python
# Bad
try:
    result = dangerous_operation()
except Exception as e:
    print(f"An error occurred: {e}")
    pass  # Continue anyway
```

**Better:** Catch specific exceptions and handle them appropriately.

### Empty Catch Blocks
```python
# Bad
try:
    risky_operation()
except:
    pass
```

This is nearly always wrong. If you truly need to ignore an exception, explain why in a comment.

## Implementation Antipatterns

### Unnecessarily Complex Implementations
```python
# Bad - AI overthinking simple tasks
def is_even(n):
    """Check if a number is even using mathematical properties."""
    return (n / 2) == (n // 2)

# Better
def is_even(n):
    return n % 2 == 0
```

### Premature Optimization
```python
# Bad - optimizing before profiling
# Using bit manipulation for "performance"
def multiply_by_two(n):
    return n << 1

# Better - clear and correct
def multiply_by_two(n):
    return n * 2
```

**Rule:** Clear code first, then optimize based on profiling data.

### Copy-Paste Code Blocks
Watch for:
- Similar functions with slight variations
- Repeated conditional logic
- Duplicated error handling

**Better:** Extract common logic into shared functions.

### Magic Numbers Without Explanation
```python
# Bad
if len(input) > 255:
    raise ValueError()

# Better
MAX_INPUT_LENGTH = 255  # Database column limit
if len(input) > MAX_INPUT_LENGTH:
    raise ValueError(f"Input exceeds maximum length of {MAX_INPUT_LENGTH}")
```

## Documentation Antipatterns

### Generic Docstrings
```python
# Bad
def process_data(data):
    """Process the data.
    
    Args:
        data: The data to process
        
    Returns:
        The processed data
    """
    pass
```

This adds zero information. Either document properly or don't document at all.

### README Boilerplate
Watch for:
- "This project aims to..."
- "Welcome to our amazing project!"
- Generic installation instructions that don't match the actual project
- Placeholder sections never filled in
- Excessive emoji and "inspirational" quotes

### Over-Documented Internal APIs
Not everything needs exhaustive documentation:

```python
# Bad - Internal helper function
def _format_date(date_obj):
    """Format a date object into a string.
    
    This function takes a date object and formats it according to
    ISO 8601 standards. It is used internally by the DateProcessor
    class to ensure consistent date formatting across the application.
    
    Args:
        date_obj (datetime): A datetime object representing the date
                            to be formatted. Must be a valid datetime
                            instance with timezone information.
    
    Returns:
        str: A string representation of the date in ISO 8601 format.
             The format includes year, month, day, hour, minute, and
             second components with timezone offset.
    
    Raises:
        ValueError: If date_obj is None or not a datetime instance.
        TypeError: If date_obj is of an incompatible type.
    
    Example:
        >>> dt = datetime.now()
        >>> _format_date(dt)
        '2024-01-15T14:30:00+00:00'
    
    Note:
        This is an internal function and should not be called directly
        by external code. Use the public DateProcessor.format() method
        instead.
    
    See Also:
        - DateProcessor.format()
        - parse_date()
        - validate_date()
    """
    return date_obj.isoformat()

# Better for internal helper
def _format_date(date_obj):
    """Return ISO 8601 formatted string."""
    return date_obj.isoformat()
```

## Language-Specific Slop

### Python
- Unnecessary use of `lambda` when a function would be clearer
- List comprehensions when a simple loop would be more readable
- Overuse of `*args, **kwargs` without clear need
- Generic exception catching: `except Exception:`

### JavaScript/TypeScript
- Unnecessary use of arrow functions everywhere
- Over-chaining array methods for simple operations
- Generic `any` types in TypeScript
- Excessive use of ternary operators for complex logic

### Java
- Excessive getter/setter boilerplate for simple data holders
- Unnecessary use of interfaces with single implementations
- Generic `Object` types instead of generics
- Over-reliance on inheritance vs composition

## Detection Signals

### High-Confidence Slop Indicators
1. Variable named `result` that holds different types
2. Functions with generic verbs: `handleData`, `processInfo`, `manageItems`
3. Comments that explain syntax rather than intent
4. Every function has a docstring, even trivial ones
5. Consistent over-engineering across codebase

### Medium-Confidence Indicators
1. Very long function/variable names that include the full context
2. Excessive defensive programming (checking for impossible conditions)
3. Empty or minimal implementations with "TODO" comments
4. Uniform structure across all functions (same patterns everywhere)

## Cleanup Strategies

### Immediate Actions
1. Delete obvious comments
2. Rename generic variables in their immediate scope
3. Remove empty catch blocks or add proper handling
4. Delete unused imports and functions

### Refactoring
1. Extract repeated code into functions
2. Simplify complex conditionals
3. Remove unnecessary abstraction layers
4. Replace generic names with domain-specific names

### Testing-Required Changes
1. Removing error handling (ensure safe to remove)
2. Simplifying algorithms (verify behavior matches)
3. Removing "defensive" null checks (ensure they're truly unnecessary)

## Context Matters

Sometimes patterns that look like slop are actually appropriate:

- **Generic names in small scopes:** `i`, `x`, `acc` in a 3-line function is fine
- **Verbose names in public APIs:** Better too clear than too cryptic
- **Defensive programming:** In public-facing APIs or critical systems
- **Detailed docstrings:** For public libraries and complex algorithms
- **Design patterns:** In large codebases where they genuinely help

The key is distinguishing between **intentional engineering decisions** and **mindless pattern repetition**.
