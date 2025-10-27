---
name: engineering-functional-programming
description: Functional programming principles, immutability, pure functions, higher-order functions, and FP patterns
---

# Functional Programming Principles

**Scope**: Comprehensive guide to FP principles, immutability, pure functions, composition, and practical FP patterns
**Lines**: ~350
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Building data transformation pipelines
- Implementing concurrent/parallel systems
- Reducing bugs through immutability
- Creating highly testable code
- Working with React, Redux, or functional frameworks
- Processing streams or collections
- Implementing functional-first languages (Haskell, Elixir, F#)
- Applying FP principles in multi-paradigm languages

## Core Concepts

### Concept 1: Pure Functions

**Definition**: Same inputs → Same outputs, no side effects

```python
# Pure function
def add(a: int, b: int) -> int:
    return a + b

# Always returns same result for same inputs
assert add(2, 3) == 5
assert add(2, 3) == 5  # Deterministic!

# Impure function (side effects)
total = 0
def add_impure(a: int) -> int:
    global total
    total += a  # Side effect: modifies external state
    return total

# Returns different results!
assert add_impure(5) == 5
assert add_impure(5) == 10  # Not deterministic!
```

**Benefits**:
- Easy to test (no mocks needed)
- Easy to reason about
- Safe to parallelize
- Cacheable (memoization)

---

### Concept 2: Immutability

**Definition**: Data never changes after creation

```typescript
// Mutable (bad)
const user = { name: "John", age: 30 };
user.age = 31;  // Mutation!

// Immutable (good)
const user = { name: "John", age: 30 };
const olderUser = { ...user, age: 31 };  // New object
// user still has age 30
```

**Why It Matters**:
```python
# Mutable bug
def add_item(cart: List[str], item: str) -> List[str]:
    cart.append(item)  # Mutates input!
    return cart

my_cart = ["apple"]
new_cart = add_item(my_cart, "banana")
print(my_cart)  # ["apple", "banana"] - SURPRISE!

# Immutable fix
def add_item(cart: List[str], item: str) -> List[str]:
    return cart + [item]  # New list

my_cart = ["apple"]
new_cart = add_item(my_cart, "banana")
print(my_cart)  # ["apple"] - unchanged!
```

---

### Concept 3: Higher-Order Functions

**Definition**: Functions that take functions as arguments or return functions

```javascript
// map: transform each element
const numbers = [1, 2, 3, 4];
const doubled = numbers.map(n => n * 2);
// [2, 4, 6, 8]

// filter: select elements
const evens = numbers.filter(n => n % 2 === 0);
// [2, 4]

// reduce: combine elements
const sum = numbers.reduce((acc, n) => acc + n, 0);
// 10
```

**Function Composition**:
```python
def compose(f, g):
    return lambda x: f(g(x))

def add_one(x):
    return x + 1

def double(x):
    return x * 2

# Compose functions
add_one_then_double = compose(double, add_one)
result = add_one_then_double(5)  # (5 + 1) * 2 = 12
```

---

## Patterns

### Pattern 1: Map, Filter, Reduce

**Imperative Style** (mutating):
```python
# Imperative
numbers = [1, 2, 3, 4, 5]
result = []
for n in numbers:
    if n % 2 == 0:
        result.append(n * 2)
print(result)  # [4, 8]
```

**Functional Style** (immutable):
```python
# Functional
numbers = [1, 2, 3, 4, 5]
result = list(
    map(lambda n: n * 2,
        filter(lambda n: n % 2 == 0, numbers))
)
print(result)  # [4, 8]

# Even better: List comprehension
result = [n * 2 for n in numbers if n % 2 == 0]
```

---

### Pattern 2: Currying & Partial Application

**Currying**: Transform f(a, b, c) → f(a)(b)(c)

```javascript
// Not curried
function add(a, b, c) {
  return a + b + c;
}
add(1, 2, 3);  // 6

// Curried
function addCurried(a) {
  return function(b) {
    return function(c) {
      return a + b + c;
    };
  };
}
addCurried(1)(2)(3);  // 6

// Partially apply
const add1 = addCurried(1);
const add1and2 = add1(2);
const result = add1and2(3);  // 6
```

**Practical Use**:
```typescript
// Reusable validators
const hasMinLength = (min: number) => (str: string) => str.length >= min;
const hasMaxLength = (max: number) => (str: string) => str.length <= max;

const isValidUsername = hasMinLength(3);
const isValidPassword = hasMinLength(8);
const isValidTweet = hasMaxLength(280);

console.log(isValidUsername("ab"));  // false
console.log(isValidPassword("secret123"));  // true
console.log(isValidTweet("Hello world!"));  // true
```

---

### Pattern 3: Immutable Data Updates

**Nested Object Updates**:
```typescript
// Bad: Mutation
const user = {
  name: "John",
  address: {
    city: "Boston",
    zip: "02101"
  }
};
user.address.city = "Cambridge";  // Mutation!

// Good: Immutable
const updatedUser = {
  ...user,
  address: {
    ...user.address,
    city: "Cambridge"
  }
};
```

**Using Libraries** (Immer):
```typescript
import produce from "immer";

const updatedUser = produce(user, draft => {
  draft.address.city = "Cambridge";
  // Looks like mutation, but returns new object!
});
```

---

### Pattern 4: Function Composition

**Manual Composition**:
```python
def add_one(x):
    return x + 1

def double(x):
    return x * 2

def square(x):
    return x ** 2

# Nested calls (hard to read)
result = square(double(add_one(5)))  # ((5 + 1) * 2)^2 = 144

# Compose helper
def compose(*fns):
    def composed(x):
        for fn in reversed(fns):
            x = fn(x)
        return x
    return composed

# Readable pipeline
pipeline = compose(square, double, add_one)
result = pipeline(5)  # 144
```

**Pipe Operator** (JavaScript):
```javascript
// Without pipe
const result = square(double(addOne(5)));

// With pipe (future JS syntax)
const result = 5
  |> addOne
  |> double
  |> square;
```

---

### Pattern 5: Monads (Error Handling)

**Optional/Maybe Monad**:
```python
from typing import Optional, TypeVar, Callable

T = TypeVar('T')
U = TypeVar('U')

class Maybe:
    def __init__(self, value: Optional[T]):
        self._value = value

    def map(self, fn: Callable[[T], U]) -> 'Maybe[U]':
        if self._value is None:
            return Maybe(None)
        return Maybe(fn(self._value))

    def flat_map(self, fn: Callable[[T], 'Maybe[U]']) -> 'Maybe[U]':
        if self._value is None:
            return Maybe(None)
        return fn(self._value)

    def get_or_else(self, default: T) -> T:
        return self._value if self._value is not None else default

# Usage: Chain operations safely
def find_user(id: str) -> Maybe[User]:
    user = database.get(id)
    return Maybe(user)

def get_email(user: User) -> Maybe[str]:
    return Maybe(user.email)

# Safe chaining (no null checks!)
email = (find_user("123")
         .flat_map(get_email)
         .get_or_else("no-email@example.com"))
```

**Result Monad** (Rust-style):
```typescript
class Result<T, E> {
  constructor(
    private value?: T,
    private error?: E
  ) {}

  static ok<T>(value: T): Result<T, never> {
    return new Result(value, undefined);
  }

  static err<E>(error: E): Result<never, E> {
    return new Result(undefined, error);
  }

  map<U>(fn: (value: T) => U): Result<U, E> {
    if (this.error !== undefined) {
      return Result.err(this.error);
    }
    return Result.ok(fn(this.value!));
  }

  unwrapOr(defaultValue: T): T {
    return this.value !== undefined ? this.value : defaultValue;
  }
}

// Usage
function divide(a: number, b: number): Result<number, string> {
  if (b === 0) {
    return Result.err("Division by zero");
  }
  return Result.ok(a / b);
}

const result = divide(10, 2).map(x => x * 2);
console.log(result.unwrapOr(0));  // 10
```

---

### Pattern 6: Functors & Applicatives

**Functor**: Container with `map`

```go
// Functor: List
func Map[T, U any](xs []T, f func(T) U) []U {
    result := make([]U, len(xs))
    for i, x := range xs {
        result[i] = f(x)
    }
    return result
}

numbers := []int{1, 2, 3}
doubled := Map(numbers, func(n int) int { return n * 2 })
// [2, 4, 6]
```

---

### Pattern 7: Recursion Over Loops

**Imperative Loop**:
```python
def sum_list(numbers):
    total = 0
    for n in numbers:
        total += n
    return total
```

**Functional Recursion**:
```python
def sum_list(numbers):
    if not numbers:
        return 0
    return numbers[0] + sum_list(numbers[1:])

# Tail-recursive (optimizable)
def sum_list_tail(numbers, acc=0):
    if not numbers:
        return acc
    return sum_list_tail(numbers[1:], acc + numbers[0])
```

---

### Pattern 8: Lazy Evaluation

**Python Generators** (lazy):
```python
# Eager (loads all into memory)
def squares_eager(n):
    return [x**2 for x in range(n)]

squares = squares_eager(1000000)  # Memory intensive!

# Lazy (generates on demand)
def squares_lazy(n):
    for x in range(n):
        yield x**2

squares = squares_lazy(1000000)  # No memory used yet!
for sq in squares:  # Generated as needed
    print(sq)
```

**Functional Streams**:
```javascript
// Infinite stream
function* naturals() {
  let n = 0;
  while (true) {
    yield n++;
  }
}

function* map(stream, fn) {
  for (const value of stream) {
    yield fn(value);
  }
}

function* take(stream, n) {
  let count = 0;
  for (const value of stream) {
    if (count++ >= n) break;
    yield value;
  }
}

// Lazy evaluation
const numbers = naturals();
const doubled = map(numbers, n => n * 2);
const first5 = take(doubled, 5);

console.log([...first5]);  // [0, 2, 4, 6, 8]
```

---

## Best Practices

### Functional Programming Guidelines

**Do's**:
- Prefer pure functions
- Use immutable data structures
- Compose small functions
- Avoid shared mutable state
- Use recursion for iteration
- Leverage higher-order functions
- Make illegal states unrepresentable

**Don'ts**:
- Mutate function arguments
- Use global variables
- Perform I/O in pure functions
- Write deeply nested code
- Ignore performance implications
- Force FP in inappropriate contexts

---

## Anti-Patterns

### Common FP Mistakes

```
❌ Forcing FP Everywhere
→ Use imperative code when clearer (loops for performance)

❌ Over-Abstraction
→ Don't curry every function - only when useful

❌ Ignoring Performance
→ Immutability has costs - profile and optimize

❌ Deep Nesting
→ Use pipeline/composition for readability

❌ Recreating Arrays Repeatedly
→ Use transducers or optimize with libraries

❌ No Side Effects Ever
→ I/O is necessary - isolate side effects

❌ Monads for Everything
→ Use when beneficial, not dogmatically
```

---

## Language-Specific Examples

### Python (functools, itertools)
```python
from functools import reduce
from itertools import chain, groupby

# Reduce
sum = reduce(lambda acc, x: acc + x, [1, 2, 3, 4], 0)

# Chain iterables
combined = chain([1, 2], [3, 4], [5, 6])

# Group by
data = [("A", 1), ("B", 2), ("A", 3)]
grouped = {k: list(g) for k, g in groupby(sorted(data), key=lambda x: x[0])}
```

### JavaScript/TypeScript (Lodash/FP)
```typescript
import { compose, map, filter } from "lodash/fp";

const process = compose(
  map((x: number) => x * 2),
  filter((x: number) => x > 5)
);

const result = process([1, 3, 5, 7, 9]);
// [14, 18]
```

### Rust (Iterators)
```rust
let result: Vec<i32> = vec![1, 2, 3, 4, 5]
    .iter()
    .filter(|&x| x % 2 == 0)
    .map(|&x| x * 2)
    .collect();
// [4, 8]
```

---

## Related Skills

- **engineering-test-driven-development**: Pure functions are easy to test
- **engineering-refactoring-patterns**: Refactoring to functional style
- **engineering-code-quality**: FP improves code quality
- **engineering-design-patterns**: FP alternatives to OOP patterns

---

## References

- [Functional Programming in JavaScript by Luis Atencio](https://www.manning.com/books/functional-programming-in-javascript)
- [Professor Frisby's Mostly Adequate Guide](https://mostly-adequate.gitbook.io/mostly-adequate-guide/)
- [Functional Programming Principles by Martin Odersky](https://www.coursera.org/learn/scala-functional-programming)
- [Ramda Documentation](https://ramdajs.com/)
