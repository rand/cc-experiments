# Example 03: Simple Classes

This example demonstrates creating Python classes in Rust using PyO3's `#[pyclass]` and `#[pymethods]` macros.

## What You'll Learn

- Creating Python classes with `#[pyclass]`
- Defining methods with `#[pymethods]`
- Constructors with `#[new]`
- Mutable vs immutable methods (`&mut self` vs `&self`)
- Exposing fields with `#[pyo3(get, set)]`
- Static methods with `#[staticmethod]`
- Special methods (`__repr__`, `__str__`)
- Input validation and error handling

## Building

```bash
maturin develop
```

## Running Tests

```bash
pytest test_example.py -v
```

## Usage Examples

```python
import simple_class as sc

# Counter
counter = sc.Counter(10)
counter.increment()
print(counter.value)  # 11

# Point
p1 = sc.Point(3.0, 4.0)
p2 = sc.Point.origin()
print(p1.distance_from(p2))  # 5.0

# Person
person = sc.Person("Alice", 30)
print(person.greet())  # "Hello, I'm Alice and I'm 30 years old."
person.birthday()
print(person.age)  # 31

# BankAccount
acc1 = sc.BankAccount("ACC001", 1000.0)
acc2 = sc.BankAccount("ACC002", 500.0)
acc1.transfer(acc2, 200.0)
print(acc1.get_balance())  # 800.0
print(acc2.get_balance())  # 700.0

# Rectangle
rect = sc.Rectangle(4.0, 5.0)
print(rect.area())  # 20.0
rect.scale(2.0)
print(rect.width)  # 8.0

square = sc.Rectangle.square(5.0)
print(square.is_square())  # True
```

## Key Concepts

### Defining a PyClass

```rust
#[pyclass]
struct Counter {
    #[pyo3(get, set)]  // Make field accessible from Python
    value: i64,
}
```

### Constructor

```rust
#[pymethods]
impl Counter {
    #[new]
    fn new(initial: Option<i64>) -> Self {
        Counter {
            value: initial.unwrap_or(0),
        }
    }
}
```

### Methods

**Immutable methods** (read-only access):
```rust
fn get_value(&self) -> i64 {
    self.value
}
```

**Mutable methods** (can modify state):
```rust
fn increment(&mut self) {
    self.value += 1;
}
```

### Static Methods

```rust
#[staticmethod]
fn origin() -> Self {
    Point { x: 0.0, y: 0.0 }
```

### Special Methods

```rust
fn __repr__(&self) -> String {
    format!("Counter(value={})", self.value)
}

fn __str__(&self) -> String {
    format!("Counter: {}", self.value)
}
```

### Field Access Control

- `#[pyo3(get)]` - Read-only from Python
- `#[pyo3(set)]` - Write-only from Python
- `#[pyo3(get, set)]` - Read-write from Python
- No annotation - Private to Rust

### Error Handling

Methods can return `PyResult<T>` to handle errors:

```rust
#[new]
fn new(name: String, age: u32) -> PyResult<Self> {
    if name.is_empty() {
        return Err(PyValueError::new_err("Name cannot be empty"));
    }
    Ok(Person { name, age })
}
```

## Class Examples

### Counter
Simple mutable state with increment/decrement operations.

### Point
2D point with distance calculations and movement operations.

### Person
Demonstrates read-only fields (`name`) and validation.

### BankAccount
Complex business logic with balance management and transfers.

### Rectangle
Geometric calculations with validation and static constructors.

## Best Practices

1. **Validate in constructor**: Check invariants in `#[new]`
2. **Use appropriate mutability**: `&self` for queries, `&mut self` for commands
3. **Return PyResult**: Use `PyResult<T>` for operations that can fail
4. **Implement __repr__**: Helpful for debugging
5. **Use descriptive error messages**: Help users understand what went wrong

## Performance Notes

- PyO3 classes are stored on the heap
- Method calls have minimal overhead compared to pure Python
- Field access through `#[pyo3(get, set)]` is very fast
- Mutable methods require exclusive access (Python GIL handles this)

## Next Steps

- **04_type_validation**: Custom type validators and converters
- **05_complex_types**: Working with Option, Result, and nested types
- **06_class_inheritance**: Subclassing and trait-based polymorphism
- **07_property_methods**: Properties with custom getters/setters
