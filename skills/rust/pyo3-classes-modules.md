---
name: pyo3-classes-modules
description: PyO3 classes, methods, and module organization for Python extensions
category: rust
tags: [pyo3, rust, python, classes, modules, plugins, oop]
prerequisites:
  - pyo3-fundamentals
  - Understanding of Python classes and OOP
  - Rust traits and implementations
level: intermediate
resources:
  - REFERENCE.md (3,500-4,000 lines)
  - 3 scripts (800+ lines each)
  - 9-10 production examples
---

# PyO3 Classes and Modules

## Overview

Master creating Python classes in Rust with PyO3, including methods, properties, class hierarchies, inheritance, Python protocols, module organization, plugin architectures, and hot-reload patterns. This skill enables building sophisticated object-oriented APIs that feel native to Python users while leveraging Rust's performance and safety.

## What You'll Learn

### Core Concepts
- **#[pyclass]**: Creating Python classes in Rust
- **#[pymethods]**: Implementing methods, properties, class methods, static methods
- **Class Hierarchies**: Inheritance patterns and hybrid class hierarchies
- **Python Protocols**: Implementing __str__, __repr__, __iter__, __len__, etc.
- **Module Organization**: Structuring large PyO3 projects with multiple modules
- **Plugin Architecture**: Dynamic plugin loading and hot-reload patterns [ADVANCED]

### Advanced Topics [ADVANCED]
- **Hot-Reload Patterns**: Reloading Rust code without restarting Python
- **Hybrid Class Hierarchies**: Python base classes with Rust subclasses (and vice versa)
- **Custom Descriptors**: Implementing Python descriptor protocol in Rust
- **Metaclasses**: Advanced metaclass patterns for Rust classes
- **Multiple Inheritance**: Handling Python's MRO with Rust classes
- **Plugin SDK Design**: Creating extensible plugin systems

## When to Use

**Ideal for**:
- Building class-based APIs (similar to Python libraries)
- Creating plugin systems and extensible frameworks
- Implementing stateful operations with encapsulation
- Providing object-oriented interfaces to Rust libraries
- Building complex data structures with methods

**Not ideal for**:
- Simple functional APIs (use standalone functions instead)
- Stateless operations (functions are simpler)
- When inheritance hierarchies become too complex

## Key Resources

### REFERENCE.md
Comprehensive guide covering:
- #[pyclass] fundamentals and configuration
- Methods: instance, class, static, properties
- Special methods: __init__, __str__, __repr__, operators
- Inheritance and class hierarchies
- Python protocols: iterator, sequence, mapping, context manager
- Module organization and packaging
- Plugin architecture patterns
- Hot-reload implementation strategies
- Performance considerations for class-based APIs

### Scripts

**1. class_inspector.py** (800+ lines)
- Inspects PyO3 classes and methods
- Validates protocol implementations
- Checks method signatures and type hints
- Generates class documentation
- Tests inheritance hierarchies
- CLI: --inspect, --validate, --generate-docs

**2. plugin_manager.py** (800+ lines)
- Plugin discovery and loading system
- Hot-reload capability
- Plugin lifecycle management
- Dependency resolution
- Sandbox execution
- CLI: --load, --reload, --list, --validate

**3. module_organizer.py** (800+ lines)
- Analyzes module structure
- Suggests reorganization strategies
- Generates module templates
- Validates import patterns
- Checks circular dependencies
- CLI: --analyze, --template, --validate

### Examples

**1. basic_class/** - Simple PyO3 class
- Minimal #[pyclass] example
- Instance methods and properties
- __init__ constructor
- Python usage examples

**2. advanced_class/** - Full-featured class
- Class methods and static methods
- Properties with getters/setters
- Special methods (__str__, __repr__, __eq__)
- Comprehensive test suite

**3. inheritance/** - Class hierarchy patterns
- Base class in Rust, subclass in Python
- Base class in Python, subclass in Rust
- Multiple levels of inheritance
- Method resolution order (MRO)

**4. protocols/** - Python protocol implementations
- Iterator protocol (__iter__, __next__)
- Sequence protocol (__len__, __getitem__)
- Context manager (__enter__, __exit__)
- Comparison operators
- Arithmetic operators

**5. plugin_system/** - Complete plugin architecture
- Plugin discovery mechanism
- Plugin loading and initialization
- Hot-reload implementation
- Plugin API/SDK
- Example plugins

**6. state_machine/** - Stateful class example
- Complex internal state
- State transitions
- Event handling
- Persistence

**7. data_class/** - Data-oriented class
- Field validation
- Serialization/deserialization
- Builder pattern
- Immutability patterns

**8. hybrid_hierarchy/** - Mixed Python/Rust classes [ADVANCED]
- Python base with Rust implementation
- Rust base with Python extension
- Multiple inheritance scenarios
- MRO handling

**9. module_structure/** - Large project organization
- Multi-module Rust project
- Submodule organization
- Re-exports and public API
- Documentation structure

**10. hot_reload/** - Hot-reload implementation [ADVANCED]
- File watching for changes
- Safe reload mechanism
- State preservation
- Reload callbacks

## Quality Standards

All resources meet Wave 10-11 quality standards:
- ✅ 0 CRITICAL/HIGH security findings
- ✅ 100% type hints (Python)
- ✅ Comprehensive error handling
- ✅ Production-ready code
- ✅ Full CLI support (--help, --json, --verbose, --dry-run)
- ✅ Extensive documentation
- ✅ Real-world examples

## Loading Resources

```bash
# Load comprehensive reference
cat skills/rust/pyo3-classes-modules/resources/REFERENCE.md

# Inspect a PyO3 class
python skills/rust/pyo3-classes-modules/resources/scripts/class_inspector.py --inspect MyClass

# Manage plugins
python skills/rust/pyo3-classes-modules/resources/scripts/plugin_manager.py --load plugins/ --reload

# Analyze module structure
python skills/rust/pyo3-classes-modules/resources/scripts/module_organizer.py --analyze src/
```

## Related Skills

- **pyo3-fundamentals**: Prerequisites (type conversion, error handling)
- **pyo3-type-conversion-advanced**: Complex type handling for classes
- **pyo3-testing-quality-ci**: Testing strategies for classes
- **pyo3-cli-embedding-plugins**: Advanced plugin patterns

## References

- [PyO3 Class Guide](https://pyo3.rs/latest/class.html)
- [Python Data Model](https://docs.python.org/3/reference/datamodel.html)
- [Python Descriptor Protocol](https://docs.python.org/3/howto/descriptor.html)
- [Plugin Architecture Patterns](https://www.oreilly.com/library/view/software-architecture-patterns/9781491971437/)

---

**Status**: Ready for implementation
**Estimated Size**: 7,200-8,400 lines total
**Time to Complete**: 6-7 days
