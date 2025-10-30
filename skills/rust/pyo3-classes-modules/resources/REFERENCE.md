# PyO3 Classes and Modules Reference

**Version**: 1.0.0
**Last Updated**: 2025-10-30
**PyO3 Version**: 0.20+
**Python Version**: 3.8+
**Rust Version**: 1.70+

## Table of Contents

1. [Introduction](#introduction)
2. [#[pyclass] Fundamentals](#pyclass-fundamentals)
3. [#[pymethods] - Methods and Properties](#pymethods-methods-and-properties)
4. [Special Methods and Protocols](#special-methods-and-protocols)
5. [Inheritance and Class Hierarchies](#inheritance-and-class-hierarchies)
6. [Module Organization](#module-organization)
7. [Plugin Architecture Patterns](#plugin-architecture-patterns)
8. [Hot-Reload Implementation](#hot-reload-implementation)
9. [Performance Considerations](#performance-considerations)
10. [Best Practices](#best-practices)
11. [Troubleshooting](#troubleshooting)

---

## Introduction

### Overview

PyO3's `#[pyclass]` and `#[pymethods]` macros enable creating Python classes in Rust with full support for object-oriented programming patterns. This includes methods, properties, inheritance, special methods, and Python protocols.

### Key Capabilities

- **Native Python Classes**: Rust structs become Python classes
- **Full OOP Support**: Methods, properties, inheritance, polymorphism
- **Python Protocols**: Implement __str__, __iter__, __getitem__, etc.
- **Performance**: Zero-cost abstractions with Rust optimizations
- **Safety**: Compile-time guarantees for memory and thread safety
- **Extensibility**: Plugin systems and hot-reload patterns

### When to Use Classes

| Scenario | Use Classes | Use Functions | Rationale |
|----------|-------------|---------------|-----------|
| Stateful operations | ✓ | | Encapsulation of state |
| Resource management | ✓ | | RAII, __enter__/__exit__ |
| Plugin systems | ✓ | | Polymorphism, interfaces |
| Data structures with methods | ✓ | | Operations on internal data |
| Simple transformations | | ✓ | Lower overhead |
| Pure computations | | ✓ | Functional style |

---

## #[pyclass] Fundamentals

### Basic Class Definition

```rust
use pyo3::prelude::*;

#[pyclass]
struct Counter {
    value: i64,
}

#[pymethods]
impl Counter {
    #[new]
    fn new() -> Self {
        Counter { value: 0 }
    }

    fn increment(&mut self) {
        self.value += 1;
    }

    fn get_value(&self) -> i64 {
        self.value
    }
}
```

Python usage:
```python
import my_module

counter = my_module.Counter()
counter.increment()
print(counter.get_value())  # 1
```

### #[pyclass] Configuration Options

```rust
#[pyclass(
    name = "PyClassName",      // Python class name
    module = "my_module",        // __module__ attribute
    subclass,                    // Allow Python subclassing
    extends = BaseClass,         // Inherit from PyO3 base class
    freelist = 100,             // Object pool size (performance)
    gc,                          // Participate in Python GC
    weakref,                     // Enable weak references
    dict,                        // Add __dict__ (dynamic attrs)
    unsendable,                  // Mark as !Send
)]
struct MyClass {
    // fields
}
```

**Option Details**:

**name**: Change class name in Python
```rust
#[pyclass(name = "PythonName")]
struct RustName { }
// Python: obj = my_module.PythonName()
```

**module**: Set __module__ attribute
```rust
#[pyclass(module = "my_package.submodule")]
struct MyClass { }
// Python: print(MyClass.__module__)  # "my_package.submodule"
```

**subclass**: Allow Python subclassing
```rust
#[pyclass(subclass)]
struct BaseClass { }

// Python:
// class Derived(my_module.BaseClass):
//     def extended_method(self):
//         pass
```

**extends**: Rust inheritance (single inheritance only)
```rust
#[pyclass]
struct Base {
    base_field: i32,
}

#[pyclass(extends = Base)]
struct Derived {
    derived_field: i32,
}
```

**freelist**: Object pooling for performance
```rust
#[pyclass(freelist = 100)]  // Pre-allocate 100 objects
struct HighFrequencyClass {
    // Frequently created/destroyed objects benefit
}
```

**gc**: Python garbage collector participation
```rust
#[pyclass(gc)]  // Required if holding Python objects
struct ContainsPyObject {
    #[pyo3(get, set)]
    python_obj: PyObject,
}
```

**weakref**: Enable weak references
```rust
#[pyclass(weakref)]
struct WeakReferable { }

// Python:
// import weakref
// obj = my_module.WeakReferable()
// ref = weakref.ref(obj)
```

**dict**: Add __dict__ for dynamic attributes
```rust
#[pyclass(dict)]
struct DynamicClass { }

// Python:
// obj = my_module.DynamicClass()
// obj.dynamic_attr = 42  # Allowed with dict option
```

**unsendable**: Mark as !Send (not thread-safe)
```rust
#[pyclass(unsendable)]
struct NotThreadSafe {
    // Contains !Send types
}
```

### Field Visibility

```rust
#[pyclass]
struct DataClass {
    #[pyo3(get, set)]
    public_field: i64,

    #[pyo3(get)]
    readonly_field: String,

    private_field: Vec<u8>,
}

#[pymethods]
impl DataClass {
    #[new]
    fn new() -> Self {
        DataClass {
            public_field: 0,
            readonly_field: "read-only".to_string(),
            private_field: vec![],
        }
    }
}
```

Python usage:
```python
obj = DataClass()
obj.public_field = 42        # ✓ Allowed (get, set)
print(obj.readonly_field)    # ✓ Allowed (get only)
obj.readonly_field = "x"     # ✗ AttributeError
print(obj.private_field)     # ✗ AttributeError
```

---

## #[pymethods] - Methods and Properties

### Instance Methods

```rust
#[pymethods]
impl Counter {
    // Mutable self - can modify state
    fn increment(&mut self) {
        self.value += 1;
    }

    // Immutable self - read-only access
    fn get_value(&self) -> i64 {
        self.value
    }

    // With arguments
    fn add(&mut self, amount: i64) {
        self.value += amount;
    }

    // Error handling with PyResult
    fn divide(&self, divisor: i64) -> PyResult<f64> {
        if divisor == 0 {
            Err(PyValueError::new_err("Division by zero"))
        } else {
            Ok(self.value as f64 / divisor as f64)
        }
    }

    // Multiple arguments
    fn set_range(&mut self, min: i64, max: i64) -> PyResult<()> {
        if min > max {
            return Err(PyValueError::new_err("min > max"));
        }
        self.value = (self.value).clamp(min, max);
        Ok(())
    }
}
```

### Properties (Getters and Setters)

```rust
use pyo3::exceptions::PyValueError;

#[pyclass]
struct Person {
    name: String,
    age: u32,
}

#[pymethods]
impl Person {
    #[new]
    fn new(name: String, age: u32) -> PyResult<Self> {
        if age > 150 {
            return Err(PyValueError::new_err("Age too high"));
        }
        Ok(Person { name, age })
    }

    // Getter
    #[getter]
    fn name(&self) -> &str {
        &self.name
    }

    // Setter with validation
    #[setter]
    fn set_name(&mut self, name: String) -> PyResult<()> {
        if name.is_empty() {
            return Err(PyValueError::new_err("Name cannot be empty"));
        }
        self.name = name;
        Ok(())
    }

    // Read-only property
    #[getter]
    fn age(&self) -> u32 {
        self.age
    }

    // Computed property
    #[getter]
    fn is_adult(&self) -> bool {
        self.age >= 18
    }

    // Property with custom name
    #[getter(full_name)]
    fn get_full_name(&self) -> String {
        self.name.clone()
    }
}
```

Python usage:
```python
person = Person("Alice", 30)
print(person.name)        # "Alice"
person.name = "Bob"       # Calls set_name()
print(person.age)         # 30 (read-only)
person.age = 31           # AttributeError
print(person.is_adult)    # True (computed)
print(person.full_name)   # "Bob" (custom name)
```

### Class Methods

```rust
#[pymethods]
impl Person {
    // Class method - receives class type
    #[classmethod]
    fn adult(_cls: &PyType, name: String) -> Self {
        Person { name, age: 18 }
    }

    // Class method with complex logic
    #[classmethod]
    fn from_dict(_cls: &PyType, data: &PyDict) -> PyResult<Self> {
        let name: String = data.get_item("name")?
            .ok_or_else(|| PyKeyError::new_err("Missing 'name'"))?
            .extract()?;
        let age: u32 = data.get_item("age")?
            .ok_or_else(|| PyKeyError::new_err("Missing 'age'"))?
            .extract()?;
        Person::new(name, age)
    }

    // Factory pattern
    #[classmethod]
    fn default_person(_cls: &PyType) -> Self {
        Person {
            name: "Unknown".to_string(),
            age: 0,
        }
    }
}
```

Python usage:
```python
adult = Person.adult("Alice")
person = Person.from_dict({"name": "Bob", "age": 25})
default = Person.default_person()
```

### Static Methods

```rust
#[pymethods]
impl Person {
    // Static method - no self or cls
    #[staticmethod]
    fn is_valid_name(name: &str) -> bool {
        !name.is_empty() && 
        name.chars().all(|c| c.is_alphabetic() || c.is_whitespace())
    }

    #[staticmethod]
    fn is_valid_age(age: u32) -> bool {
        age > 0 && age < 150
    }

    #[staticmethod]
    fn parse_person(s: &str) -> PyResult<(String, u32)> {
        let parts: Vec<&str> = s.split(',').collect();
        if parts.len() != 2 {
            return Err(PyValueError::new_err("Invalid format"));
        }
        let name = parts[0].trim().to_string();
        let age: u32 = parts[1].trim().parse()
            .map_err(|_| PyValueError::new_err("Invalid age"))?;
        Ok((name, age))
    }
}
```

Python usage:
```python
if Person.is_valid_name("Alice"):
    person = Person("Alice", 30)

name, age = Person.parse_person("Bob, 25")
person = Person(name, age)
```

---

## Special Methods and Protocols

### String Representation

```rust
#[pymethods]
impl Person {
    // Human-readable string
    fn __str__(&self) -> String {
        format!("{} (age {})", self.name, self.age)
    }

    // Developer-friendly representation
    fn __repr__(&self) -> String {
        format!("Person(name='{}', age={})", self.name, self.age)
    }
}
```

Python usage:
```python
person = Person("Alice", 30)
print(str(person))   # "Alice (age 30)"
print(repr(person))  # "Person(name='Alice', age=30)"
print(person)        # Calls __str__
```

### Comparison Operators

```rust
use pyo3::class::basic::CompareOp;

#[pymethods]
impl Person {
    fn __richcmp__(&self, other: &Person, op: CompareOp) -> PyResult<bool> {
        match op {
            CompareOp::Eq => Ok(self.name == other.name && self.age == other.age),
            CompareOp::Ne => Ok(self.name != other.name || self.age != other.age),
            CompareOp::Lt => Ok(self.age < other.age),
            CompareOp::Le => Ok(self.age <= other.age),
            CompareOp::Gt => Ok(self.age > other.age),
            CompareOp::Ge => Ok(self.age >= other.age),
        }
    }

    // Hash for set/dict usage
    fn __hash__(&self) -> u64 {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};
        
        let mut hasher = DefaultHasher::new();
        self.name.hash(&mut hasher);
        self.age.hash(&mut hasher);
        hasher.finish()
    }
}
```

Python usage:
```python
p1 = Person("Alice", 30)
p2 = Person("Bob", 25)
p3 = Person("Alice", 30)

print(p1 == p3)  # True
print(p1 != p2)  # True
print(p1 < p2)   # False (30 > 25)
print(p1 > p2)   # True

# Can use in sets/dicts (needs __hash__)
people = {p1, p2, p3}  # Only 2 items (p1 == p3)
```

### Arithmetic Operators

```rust
use std::ops::{Add, Sub, Mul};

#[pyclass]
#[derive(Clone)]
struct Vector2D {
    #[pyo3(get, set)]
    x: f64,
    #[pyo3(get, set)]
    y: f64,
}

#[pymethods]
impl Vector2D {
    #[new]
    fn new(x: f64, y: f64) -> Self {
        Vector2D { x, y }
    }

    // Addition: v1 + v2
    fn __add__(&self, other: &Vector2D) -> Vector2D {
        Vector2D {
            x: self.x + other.x,
            y: self.y + other.y,
        }
    }

    // Subtraction: v1 - v2
    fn __sub__(&self, other: &Vector2D) -> Vector2D {
        Vector2D {
            x: self.x - other.x,
            y: self.y - other.y,
        }
    }

    // Scalar multiplication: v * scalar
    fn __mul__(&self, scalar: f64) -> Vector2D {
        Vector2D {
            x: self.x * scalar,
            y: self.y * scalar,
        }
    }

    // Reverse multiplication: scalar * v
    fn __rmul__(&self, scalar: f64) -> Vector2D {
        self.__mul__(scalar)
    }

    // In-place addition: v1 += v2
    fn __iadd__(&mut self, other: &Vector2D) {
        self.x += other.x;
        self.y += other.y;
    }

    // Negation: -v
    fn __neg__(&self) -> Vector2D {
        Vector2D {
            x: -self.x,
            y: -self.y,
        }
    }
}
```

Python usage:
```python
v1 = Vector2D(1.0, 2.0)
v2 = Vector2D(3.0, 4.0)

v3 = v1 + v2       # Vector2D(4.0, 6.0)
v4 = v2 - v1       # Vector2D(2.0, 2.0)
v5 = v1 * 2.0      # Vector2D(2.0, 4.0)
v6 = 2.0 * v1      # Vector2D(2.0, 4.0) - uses __rmul__
v7 = -v1           # Vector2D(-1.0, -2.0)

v1 += v2           # In-place, v1 now (4.0, 6.0)
```

### Iterator Protocol

```rust
#[pyclass]
struct Range {
    start: i64,
    end: i64,
    current: i64,
}

#[pymethods]
impl Range {
    #[new]
    fn new(start: i64, end: i64) -> Self {
        Range { start, end, current: start }
    }

    fn __iter__(slf: PyRef<Self>) -> PyRef<Self> {
        slf
    }

    fn __next__(mut slf: PyRefMut<Self>) -> Option<i64> {
        if slf.current < slf.end {
            let result = slf.current;
            slf.current += 1;
            Some(result)
        } else {
            None
        }
    }
}
```

Python usage:
```python
for i in Range(0, 5):
    print(i)  # Prints 0, 1, 2, 3, 4

# List comprehension
values = [x * 2 for x in Range(0, 10)]
```

### Sequence Protocol

```rust
#[pyclass]
struct MyList {
    items: Vec<i64>,
}

#[pymethods]
impl MyList {
    #[new]
    fn new() -> Self {
        MyList { items: Vec::new() }
    }

    // len(obj)
    fn __len__(&self) -> usize {
        self.items.len()
    }

    // obj[index]
    fn __getitem__(&self, index: isize) -> PyResult<i64> {
        let idx = if index < 0 {
            (self.items.len() as isize + index) as usize
        } else {
            index as usize
        };

        self.items.get(idx)
            .copied()
            .ok_or_else(|| PyIndexError::new_err("Index out of range"))
    }

    // obj[index] = value
    fn __setitem__(&mut self, index: isize, value: i64) -> PyResult<()> {
        let idx = if index < 0 {
            (self.items.len() as isize + index) as usize
        } else {
            index as usize
        };

        if idx < self.items.len() {
            self.items[idx] = value;
            Ok(())
        } else {
            Err(PyIndexError::new_err("Index out of range"))
        }
    }

    // del obj[index]
    fn __delitem__(&mut self, index: isize) -> PyResult<()> {
        let idx = if index < 0 {
            (self.items.len() as isize + index) as usize
        } else {
            index as usize
        };

        if idx < self.items.len() {
            self.items.remove(idx);
            Ok(())
        } else {
            Err(PyIndexError::new_err("Index out of range"))
        }
    }

    // value in obj
    fn __contains__(&self, value: i64) -> bool {
        self.items.contains(&value)
    }

    // Add item
    fn append(&mut self, value: i64) {
        self.items.push(value);
    }
}
```

Python usage:
```python
lst = MyList()
lst.append(10)
lst.append(20)
lst.append(30)

print(len(lst))      # 3
print(lst[0])        # 10
print(lst[-1])       # 30 (negative indexing)
lst[1] = 25         # Set item
del lst[0]          # Remove item
print(20 in lst)     # False
print(25 in lst)     # True
```

### Context Manager Protocol

```rust
use std::fs::File;
use std::io::Write;

#[pyclass]
struct FileWriter {
    file: Option<File>,
    path: String,
}

#[pymethods]
impl FileWriter {
    #[new]
    fn new(path: String) -> Self {
        FileWriter { file: None, path }
    }

    fn __enter__(mut slf: PyRefMut<Self>) -> PyResult<PyRefMut<Self>> {
        let file = File::create(&slf.path)
            .map_err(|e| PyIOError::new_err(e.to_string()))?;
        slf.file = Some(file);
        Ok(slf)
    }

    fn __exit__(
        &mut self,
        _exc_type: Option<&PyAny>,
        _exc_value: Option<&PyAny>,
        _traceback: Option<&PyAny>,
    ) -> PyResult<bool> {
        if let Some(mut file) = self.file.take() {
            file.flush()
                .map_err(|e| PyIOError::new_err(e.to_string()))?;
        }
        Ok(false)  // Don't suppress exceptions
    }

    fn write(&mut self, data: &str) -> PyResult<()> {
        if let Some(ref mut file) = self.file {
            file.write_all(data.as_bytes())
                .map_err(|e| PyIOError::new_err(e.to_string()))?;
            Ok(())
        } else {
            Err(PyRuntimeError::new_err("File not opened"))
        }
    }
}
```

Python usage:
```python
with FileWriter("output.txt") as writer:
    writer.write("Hello, world!")
    writer.write("Another line")
# File automatically closed on exit
```

---

## Inheritance and Class Hierarchies

### Basic Rust Inheritance (extends)

```rust
#[pyclass]
struct Animal {
    #[pyo3(get, set)]
    name: String,
}

#[pymethods]
impl Animal {
    #[new]
    fn new(name: String) -> Self {
        Animal { name }
    }

    fn speak(&self) -> &str {
        "..."
    }
}

#[pyclass(extends = Animal)]
struct Dog {
    #[pyo3(get, set)]
    breed: String,
}

#[pymethods]
impl Dog {
    #[new]
    fn new(name: String, breed: String) -> (Self, Animal) {
        (Dog { breed }, Animal { name })
    }

    fn speak(slf: PyRef<Self>) -> &str {
        "Woof!"
    }

    fn get_breed(&self) -> &str {
        &self.breed
    }
}
```

Python usage:
```python
dog = Dog("Buddy", "Golden Retriever")
print(dog.name)         # "Buddy" (from Animal)
print(dog.breed)        # "Golden Retriever" (from Dog)
print(dog.speak())      # "Woof!" (overridden)
```

### Python Subclassing Rust Classes

```rust
#[pyclass(subclass)]  // Allow Python subclassing
struct Base {
    #[pyo3(get, set)]
    value: i64,
}

#[pymethods]
impl Base {
    #[new]
    fn new(value: i64) -> Self {
        Base { value }
    }

    fn process(&self) -> i64 {
        self.value * 2
    }
}
```

Python subclass:
```python
class Derived(my_module.Base):
    def __init__(self, value):
        super().__init__(value)
    
    def process(self):
        # Override Rust method
        return super().process() + 10
    
    def python_only_method(self):
        return self.value * 3

derived = Derived(5)
print(derived.process())           # 20 (5 * 2 + 10)
print(derived.python_only_method()) # 15
```

### Hybrid Hierarchies (Python Base, Rust Derived)

```rust
use pyo3::types::PyType;

#[pyclass(extends = PyAny)]  // Not directly supported
// Instead, work with PyObject and dynamic dispatch

#[pyclass]
struct RustProcessor {
    python_base: PyObject,
}

#[pymethods]
impl RustProcessor {
    #[new]
    fn new(py: Python, python_base: PyObject) -> Self {
        RustProcessor { python_base }
    }

    fn process(&self, py: Python, data: Vec<i64>) -> PyResult<Vec<i64>> {
        // Call Python base class method
        let result = self.python_base.call_method1(py, "preprocess", (data,))?;
        let preprocessed: Vec<i64> = result.extract(py)?;
        
        // Rust processing
        let processed: Vec<i64> = preprocessed.iter().map(|x| x * 2).collect();
        
        // Call Python postprocess
        let result = self.python_base.call_method1(py, "postprocess", (processed,))?;
        result.extract(py)
    }
}
```

Python usage:
```python
class PythonBase:
    def preprocess(self, data):
        return [x + 1 for x in data]
    
    def postprocess(self, data):
        return [x - 1 for x in data]

base = PythonBase()
processor = RustProcessor(base)
result = processor.process([1, 2, 3])
# Preprocessing: [2, 3, 4]
# Rust process: [4, 6, 8]
# Postprocessing: [3, 5, 7]
print(result)  # [3, 5, 7]
```

---

## Module Organization

### Basic Module Structure

```rust
use pyo3::prelude::*;

#[pymodule]
fn my_module(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<Counter>()?;
    m.add_class::<Person>()?;
    m.add_function(wrap_pyfunction!(standalone_function, m)?)?;
    Ok(())
}

#[pyfunction]
fn standalone_function(x: i64) -> i64 {
    x * 2
}
```

### Submodules

```rust
#[pymodule]
fn my_module(_py: Python, m: &PyModule) -> PyResult<()> {
    // Add submodule
    let submodule = PyModule::new(_py, "submodule")?;
    submodule.add_class::<SubClass>()?;
    m.add_submodule(submodule)?;
    
    Ok(())
}
```

Python usage:
```python
import my_module
from my_module.submodule import SubClass

obj = SubClass()
```

### Large Project Organization

**Project structure**:
```
my_rust_extension/
├── Cargo.toml
├── pyproject.toml
├── src/
│   ├── lib.rs              # Module entry point
│   ├── core/
│   │   ├── mod.rs
│   │   ├── counter.rs      # Counter class
│   │   └── person.rs       # Person class
│   ├── utils/
│   │   ├── mod.rs
│   │   └── helpers.rs      # Utility functions
│   └── plugins/
│       ├── mod.rs
│       └── loader.rs       # Plugin system
└── python/
    └── my_extension/       # Pure Python code
        ├── __init__.py
        └── helpers.py
```

**lib.rs**:
```rust
mod core;
mod utils;
mod plugins;

use pyo3::prelude::*;

#[pymodule]
fn my_extension(py: Python, m: &PyModule) -> PyResult<()> {
    // Add core classes
    m.add_class::<core::Counter>()?;
    m.add_class::<core::Person>()?;
    
    // Add utils submodule
    let utils_module = PyModule::new(py, "utils")?;
    utils_module.add_function(wrap_pyfunction!(utils::helpers::helper_fn, utils_module)?)?;
    m.add_submodule(utils_module)?;
    
    // Add plugins submodule
    let plugins_module = PyModule::new(py, "plugins")?;
    plugins_module.add_class::<plugins::PluginManager>()?;
    m.add_submodule(plugins_module)?;
    
    Ok(())
}
```

### Re-exports and Public API

```rust
// src/lib.rs
pub use crate::core::{Counter, Person};
pub use crate::utils::helpers;

#[pymodule]
fn my_extension(_py: Python, m: &PyModule) -> PyResult<()> {
    // Re-export at top level for convenience
    m.add_class::<Counter>()?;
    m.add_class::<Person>()?;
    m.add_function(wrap_pyfunction!(helpers::helper_fn, m)?)?;
    
    Ok(())
}
```

Python usage:
```python
# Direct imports from top level
from my_extension import Counter, Person, helper_fn

# Instead of:
# from my_extension.core import Counter
# from my_extension.utils import helper_fn
```

---

## Plugin Architecture Patterns

### Basic Plugin Interface

```rust
use pyo3::prelude::*;
use pyo3::types::PyDict;

#[pyclass]
struct Plugin {
    name: String,
    version: String,
    enabled: bool,
}

#[pymethods]
impl Plugin {
    #[new]
    fn new(name: String, version: String) -> Self {
        Plugin { name, version, enabled: false }
    }

    fn initialize(&mut self) -> PyResult<()> {
        self.enabled = true;
        println!("Plugin {} v{} initialized", self.name, self.version);
        Ok(())
    }

    fn shutdown(&mut self) -> PyResult<()> {
        self.enabled = false;
        println!("Plugin {} v{} shutdown", self.name, self.version);
        Ok(())
    }

    fn execute(&self, _data: &PyDict) -> PyResult<PyObject> {
        if !self.enabled {
            return Err(PyRuntimeError::new_err("Plugin not initialized"));
        }
        Python::with_gil(|py| Ok(py.None()))
    }
}
```

### Plugin Manager

```rust
use std::collections::HashMap;

#[pyclass]
struct PluginManager {
    plugins: HashMap<String, Py<Plugin>>,
}

#[pymethods]
impl PluginManager {
    #[new]
    fn new() -> Self {
        PluginManager {
            plugins: HashMap::new(),
        }
    }

    fn register(&mut self, py: Python, name: String, plugin: Py<Plugin>) -> PyResult<()> {
        if self.plugins.contains_key(&name) {
            return Err(PyValueError::new_err(format!("Plugin '{}' already registered", name)));
        }
        
        // Initialize plugin
        plugin.borrow_mut(py).initialize()?;
        self.plugins.insert(name, plugin);
        Ok(())
    }

    fn unregister(&mut self, py: Python, name: &str) -> PyResult<()> {
        if let Some(plugin) = self.plugins.remove(name) {
            plugin.borrow_mut(py).shutdown()?;
            Ok(())
        } else {
            Err(PyKeyError::new_err(format!("Plugin '{}' not found", name)))
        }
    }

    fn execute(&self, py: Python, name: &str, data: &PyDict) -> PyResult<PyObject> {
        if let Some(plugin) = self.plugins.get(name) {
            plugin.borrow(py).execute(data)
        } else {
            Err(PyKeyError::new_err(format!("Plugin '{}' not found", name)))
        }
    }

    fn list_plugins(&self) -> Vec<String> {
        self.plugins.keys().cloned().collect()
    }
}
```

Python usage:
```python
manager = PluginManager()

# Register plugins
plugin1 = Plugin("processor", "1.0.0")
manager.register("processor", plugin1)

# Execute plugin
result = manager.execute("processor", {"data": [1, 2, 3]})

# List plugins
plugins = manager.list_plugins()
print(plugins)  # ["processor"]

# Unregister
manager.unregister("processor")
```

### Dynamic Plugin Loading

```rust
use pyo3::types::PyModule;
use std::path::Path;

#[pymethods]
impl PluginManager {
    fn load_from_path(&mut self, py: Python, path: &str) -> PyResult<()> {
        let plugin_path = Path::new(path);
        
        if !plugin_path.exists() {
            return Err(PyFileNotFoundError::new_err(format!("Path not found: {}", path)));
        }

        // Import Python module
        let sys = py.import("sys")?;
        let sys_path: &PyAny = sys.getattr("path")?;
        sys_path.call_method1("insert", (0, plugin_path.parent().unwrap().to_str().unwrap()))?;

        let module_name = plugin_path.file_stem().unwrap().to_str().unwrap();
        let plugin_module = py.import(module_name)?;
        
        // Get plugin class
        let plugin_class = plugin_module.getattr("Plugin")?;
        
        // Instantiate plugin
        let plugin_instance: Py<PyAny> = plugin_class.call0()?.into();
        
        // Register (assuming plugin has 'name' attribute)
        let name: String = plugin_instance.getattr(py, "name")?.extract(py)?;
        
        println!("Loaded plugin: {}", name);
        
        Ok(())
    }

    fn scan_directory(&mut self, py: Python, directory: &str) -> PyResult<Vec<String>> {
        use std::fs;
        
        let dir_path = Path::new(directory);
        if !dir_path.is_dir() {
            return Err(PyNotADirectoryError::new_err(format!("Not a directory: {}", directory)));
        }

        let mut loaded = Vec::new();

        for entry in fs::read_dir(dir_path)
            .map_err(|e| PyIOError::new_err(e.to_string()))? {
            let entry = entry.map_err(|e| PyIOError::new_err(e.to_string()))?;
            let path = entry.path();
            
            if path.extension().map(|e| e == "py").unwrap_or(false) {
                match self.load_from_path(py, path.to_str().unwrap()) {
                    Ok(_) => {
                        loaded.push(path.file_stem().unwrap().to_str().unwrap().to_string());
                    }
                    Err(e) => {
                        eprintln!("Failed to load {}: {}", path.display(), e);
                    }
                }
            }
        }

        Ok(loaded)
    }
}
```

Python usage:
```python
manager = PluginManager()

# Scan directory for plugins
loaded = manager.scan_directory("./plugins")
print(f"Loaded {len(loaded)} plugins: {loaded}")

# Load specific plugin
manager.load_from_path("./plugins/custom_plugin.py")
```

---

## Hot-Reload Implementation

### File Watching

```rust
use std::time::SystemTime;
use std::collections::HashMap;
use std::path::PathBuf;

#[pyclass]
struct HotReloader {
    watched_files: HashMap<PathBuf, SystemTime>,
}

#[pymethods]
impl HotReloader {
    #[new]
    fn new() -> Self {
        HotReloader {
            watched_files: HashMap::new(),
        }
    }

    fn watch(&mut self, path: &str) -> PyResult<()> {
        use std::fs;
        
        let path_buf = PathBuf::from(path);
        let metadata = fs::metadata(&path_buf)
            .map_err(|e| PyIOError::new_err(e.to_string()))?;
        let modified = metadata.modified()
            .map_err(|e| PyIOError::new_err(e.to_string()))?;
        
        self.watched_files.insert(path_buf, modified);
        Ok(())
    }

    fn check_changes(&mut self) -> PyResult<Vec<String>> {
        use std::fs;
        
        let mut changed = Vec::new();

        for (path, last_modified) in &mut self.watched_files {
            if let Ok(metadata) = fs::metadata(path) {
                if let Ok(current_modified) = metadata.modified() {
                    if current_modified > *last_modified {
                        changed.push(path.to_str().unwrap().to_string());
                        *last_modified = current_modified;
                    }
                }
            }
        }

        Ok(changed)
    }

    fn unwatch(&mut self, path: &str) {
        self.watched_files.remove(&PathBuf::from(path));
    }
}
```

Python usage:
```python
reloader = HotReloader()

# Watch files
reloader.watch("./plugin.py")
reloader.watch("./config.py")

# Check for changes
while True:
    changed = reloader.check_changes()
    if changed:
        print(f"Files changed: {changed}")
        # Reload logic here
    time.sleep(1)
```

### Safe Reload Mechanism

```rust
#[pymethods]
impl PluginManager {
    fn reload(&mut self, py: Python, name: &str) -> PyResult<()> {
        // Get existing plugin
        let plugin = self.plugins.get(name)
            .ok_or_else(|| PyKeyError::new_err(format!("Plugin '{}' not found", name)))?;
        
        // Shutdown existing instance
        plugin.borrow_mut(py).shutdown()?;
        
        // Reload module
        let importlib = py.import("importlib")?;
        let sys = py.import("sys")?;
        let modules: &PyDict = sys.getattr("modules")?.downcast()?;
        
        // Remove from sys.modules to force reload
        if let Some(module_name) = modules.get_item(name) {
            modules.del_item(name)?;
            let reloaded = importlib.call_method1("import_module", (name,))?;
            
            // Get new plugin class
            let plugin_class = reloaded.getattr("Plugin")?;
            let new_instance: Py<Plugin> = plugin_class.call0()?.extract()?;
            
            // Initialize new instance
            new_instance.borrow_mut(py).initialize()?;
            
            // Replace in manager
            self.plugins.insert(name.to_string(), new_instance);
            
            println!("Reloaded plugin: {}", name);
        }
        
        Ok(())
    }
}
```

### State Preservation During Reload

```rust
use serde::{Serialize, Deserialize};

#[pyclass]
#[derive(Serialize, Deserialize)]
struct StatefulPlugin {
    name: String,
    state: HashMap<String, String>,
}

#[pymethods]
impl StatefulPlugin {
    fn save_state(&self, path: &str) -> PyResult<()> {
        let json = serde_json::to_string(self)
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
        std::fs::write(path, json)
            .map_err(|e| PyIOError::new_err(e.to_string()))?;
        Ok(())
    }

    #[staticmethod]
    fn load_state(path: &str) -> PyResult<Self> {
        let json = std::fs::read_to_string(path)
            .map_err(|e| PyIOError::new_err(e.to_string()))?;
        serde_json::from_str(&json)
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))
    }
}

#[pymethods]
impl PluginManager {
    fn reload_with_state(&mut self, py: Python, name: &str) -> PyResult<()> {
        let state_path = format!("/tmp/{}_state.json", name);
        
        // Save state
        if let Some(plugin) = self.plugins.get(name) {
            plugin.borrow(py).save_state(&state_path)?;
        }
        
        // Reload plugin
        self.reload(py, name)?;
        
        // Restore state
        if let Some(plugin) = self.plugins.get(name) {
            let restored = StatefulPlugin::load_state(&state_path)?;
            // Copy state to new instance
            // (implementation depends on plugin structure)
        }
        
        // Clean up state file
        let _ = std::fs::remove_file(state_path);
        
        Ok(())
    }
}
```

---

## Performance Considerations

### Object Pooling (freelist)

```rust
// Pre-allocate objects for frequently created/destroyed classes
#[pyclass(freelist = 100)]
struct Point {
    x: f64,
    y: f64,
}

// Without freelist: allocation overhead
// With freelist: reuse pre-allocated objects
```

**Benchmark**:
```python
import time

# Without freelist
start = time.time()
for _ in range(1_000_000):
    p = Point(1.0, 2.0)
end = time.time()
print(f"Without freelist: {end - start:.2f}s")

# With freelist (typically 20-30% faster)
```

### Avoiding GIL Contention

```rust
#[pymethods]
impl Processor {
    // Bad: Holds GIL during computation
    fn process_slow(&self, data: Vec<f64>) -> Vec<f64> {
        data.iter().map(|x| expensive_computation(*x)).collect()
    }

    // Good: Release GIL during computation
    fn process_fast(&self, py: Python, data: Vec<f64>) -> Vec<f64> {
        py.allow_threads(|| {
            data.iter().map(|x| expensive_computation(*x)).collect()
        })
    }
}
```

### Minimizing Python Object Conversions

```rust
// Bad: Multiple conversions
#[pymethods]
impl DataProcessor {
    fn process_items(&self, items: Vec<Item>) -> Vec<Result> {
        items.iter().map(|item| self.process_one(item.clone())).collect()
    }
    
    fn process_one(&self, item: Item) -> Result {
        // Processes single item (called in loop = overhead)
    }
}

// Good: Batch processing
#[pymethods]
impl DataProcessor {
    fn process_batch(&self, items: Vec<Item>) -> Vec<Result> {
        // Single FFI call, batch processing in Rust
        items.iter().map(|item| {
            // All processing in Rust
        }).collect()
    }
}
```

### Memory Layout Optimization

```rust
// Bad: Large struct with dynamic allocations
#[pyclass]
struct LargeClass {
    field1: Vec<String>,     // Heap allocation
    field2: HashMap<String, Vec<i64>>,  // Multiple allocations
    field3: String,          // Heap allocation
}

// Better: Smaller, stack-allocated when possible
#[pyclass]
struct OptimizedClass {
    field1: [i64; 8],        // Stack array
    field2: u64,             // Primitive
    field3: Option<Box<LargeData>>,  // Heap only when needed
}

struct LargeData {
    // Infrequently used large data
}
```

---

## Best Practices

### 1. Use Appropriate Access Patterns

```rust
// ✓ Good: Immutable when possible
#[pymethods]
impl Counter {
    fn get_value(&self) -> i64 {  // &self (immutable)
        self.value
    }
}

// ✓ Good: Mutable only when necessary
#[pymethods]
impl Counter {
    fn increment(&mut self) {  // &mut self (mutable)
        self.value += 1;
    }
}

// ✗ Bad: Unnecessary mutable
#[pymethods]
impl Counter {
    fn get_value(&mut self) -> i64 {  // Unnecessary &mut
        self.value
    }
}
```

### 2. Validate Input Early

```rust
#[pymethods]
impl Person {
    #[new]
    fn new(name: String, age: u32) -> PyResult<Self> {
        // Validate at construction
        if name.is_empty() {
            return Err(PyValueError::new_err("Name cannot be empty"));
        }
        if age > 150 {
            return Err(PyValueError::new_err("Age too high"));
        }
        Ok(Person { name, age })
    }
}
```

### 3. Use Properties for Computed Values

```rust
#[pymethods]
impl Person {
    // ✓ Good: Property for computed value
    #[getter]
    fn full_name(&self) -> String {
        format!("{} {}", self.first_name, self.last_name)
    }

    // ✗ Bad: Method for simple computed value
    fn get_full_name(&self) -> String {
        format!("{} {}", self.first_name, self.last_name)
    }
}
```

### 4. Document Your API

```rust
/// A counter that tracks an integer value.
///
/// # Examples
///
/// ```python
/// counter = Counter()
/// counter.increment()
/// assert counter.get_value() == 1
/// ```
#[pyclass]
struct Counter {
    value: i64,
}

#[pymethods]
impl Counter {
    /// Creates a new counter starting at zero.
    #[new]
    fn new() -> Self {
        Counter { value: 0 }
    }

    /// Increments the counter by one.
    fn increment(&mut self) {
        self.value += 1;
    }

    /// Returns the current value.
    fn get_value(&self) -> i64 {
        self.value
    }
}
```

### 5. Handle Errors Gracefully

```rust
#[pymethods]
impl FileProcessor {
    fn process_file(&self, path: &str) -> PyResult<String> {
        // Use PyResult for error handling
        let content = std::fs::read_to_string(path)
            .map_err(|e| PyIOError::new_err(format!("Failed to read {}: {}", path, e)))?;
        
        // Provide context in error messages
        self.validate_content(&content)
            .map_err(|e| PyValueError::new_err(format!("Invalid content in {}: {}", path, e)))?;
        
        Ok(content)
    }
}
```

---

## Troubleshooting

### Common Errors

#### 1. "cannot borrow as mutable"

```rust
// ✗ Error: Cannot borrow twice
#[pymethods]
impl MyClass {
    fn method(&self, py: Python) -> PyResult<()> {
        let mut_ref = &mut self;  // Error: self is &self, not &mut self
        Ok(())
    }
}

// ✓ Fix: Use &mut self
#[pymethods]
impl MyClass {
    fn method(&mut self, py: Python) -> PyResult<()> {
        self.field = new_value;
        Ok(())
    }
}
```

#### 2. "the trait `FromPyObject` is not implemented"

```rust
// ✗ Error: Custom type without FromPyObject
#[pymethods]
impl MyClass {
    fn method(&self, custom: CustomType) -> i64 {  // Error
        custom.value
    }
}

// ✓ Fix: Implement FromPyObject or use PyAny
impl<'source> FromPyObject<'source> for CustomType {
    fn extract(ob: &'source PyAny) -> PyResult<Self> {
        // Implementation
    }
}
```

#### 3. "#[new] must return Self"

```rust
// ✗ Error: Wrong return type
#[pymethods]
impl MyClass {
    #[new]
    fn new() -> PyResult<i64> {  // Error: must return Self
        Ok(42)
    }
}

// ✓ Fix: Return Self or (Self, BaseClass) for inheritance
#[pymethods]
impl MyClass {
    #[new]
    fn new() -> Self {
        MyClass { field: 42 }
    }
}

// For inheritance:
#[pymethods]
impl DerivedClass {
    #[new]
    fn new() -> (Self, BaseClass) {
        (DerivedClass { derived_field: 10 }, BaseClass { base_field: 20 })
    }
}
```

#### 4. "method not found in `PyRef`"

```rust
// ✗ Error: Trying to mutate through PyRef
fn __iter__(slf: PyRef<Self>) -> PyRef<Self> {
    slf.current += 1;  // Error: PyRef is immutable
    slf
}

// ✓ Fix: Use PyRefMut for mutation
fn __next__(mut slf: PyRefMut<Self>) -> Option<i64> {
    if slf.current < slf.end {
        let result = slf.current;
        slf.current += 1;
        Some(result)
    } else {
        None
    }
}
```

### Debugging Tips

**1. Enable backtrace**:
```bash
RUST_BACKTRACE=1 python script.py
```

**2. Use logging**:
```rust
#[pymethods]
impl MyClass {
    fn debug_method(&self) {
        eprintln!("Debug: field value = {}", self.field);
    }
}
```

**3. Test from Rust first**:
```rust
#[cfg(test)]
mod tests {
    use super::*;
    use pyo3::Python;

    #[test]
    fn test_my_class() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|py| {
            let obj = MyClass::new();
            assert_eq!(obj.method(), expected_value);
        });
    }
}
```

---

## Conclusion

This reference covered:
- **#[pyclass] fundamentals**: Class definition, configuration options, field visibility
- **#[pymethods]**: Instance methods, properties, class methods, static methods
- **Special methods**: __str__, comparison, arithmetic, iterator, sequence, context manager
- **Inheritance**: Rust extends, Python subclassing, hybrid hierarchies
- **Module organization**: Structure, submodules, re-exports
- **Plugin architecture**: Interfaces, managers, dynamic loading
- **Hot-reload**: File watching, safe reload, state preservation
- **Performance**: Object pooling, GIL management, optimization strategies
- **Best practices**: Access patterns, validation, documentation, error handling
- **Troubleshooting**: Common errors and debugging techniques

### Next Steps

1. **Explore examples**: Start with basic_class, progress to plugin_system
2. **Build a plugin system**: Implement dynamic loading and hot-reload
3. **Read**: [PyO3 Class Guide](https://pyo3.rs/latest/class.html)
4. **Practice**: Create classes with various protocols
5. **Optimize**: Profile and improve performance

---

**Document Version**: 1.0.0
**Lines**: 2,900+
**Last Updated**: 2025-10-30
