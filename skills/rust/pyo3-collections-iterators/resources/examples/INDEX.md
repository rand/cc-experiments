# PyO3 Collections & Iterators - Examples Index

Quick reference guide to all 10 examples.

## Quick Navigation

| # | Name | Difficulty | Lines | Topic |
|---|------|------------|-------|-------|
| 01 | [basic_iterator](#01-basic-iterator) | Beginner | 130 | Iterator protocol |
| 02 | [collection_conversion](#02-collection-conversion) | Beginner | 158 | Type conversion |
| 03 | [sequence_protocol](#03-sequence-protocol) | Beginner | 194 | Sequences |
| 04 | [lazy_iterator](#04-lazy-iterator) | Intermediate | 197 | Lazy evaluation |
| 05 | [bidirectional_iter](#05-bidirectional-iterator) | Intermediate | 157 | Bidirectional |
| 06 | [custom_collection](#06-custom-collection) | Intermediate | 205 | Custom types |
| 07 | [iterator_combinators](#07-iterator-combinators) | Intermediate | 229 | Combinators |
| 08 | [streaming_data](#08-streaming-data) | Advanced | 169 | Streaming |
| 09 | [parallel_iterator](#09-parallel-iterator) | Advanced | 172 | Parallelism |
| 10 | [production_pipeline](#10-production-pipeline) | Advanced | 270 | Pipeline |

## Example Details

### 01. Basic Iterator
**Path**: `01_basic_iterator/`
**Difficulty**: Beginner
**What**: Iterator protocol fundamentals
**Key Concepts**: `__iter__`, `__next__`, state management
**Use Cases**: Number generation, stateful iteration

**Build**: `cd 01_basic_iterator && maturin develop`

---

### 02. Collection Conversion
**Path**: `02_collection_conversion/`
**Difficulty**: Beginner
**What**: Type conversion between Rust and Python
**Key Concepts**: Vec↔List, HashMap↔Dict, HashSet↔Set
**Use Cases**: Data transformation, API responses

**Build**: `cd 02_collection_conversion && maturin develop`

---

### 03. Sequence Protocol
**Path**: `03_sequence_protocol/`
**Difficulty**: Beginner
**What**: Python sequence protocol implementation
**Key Concepts**: `__len__`, `__getitem__`, `__setitem__`, slicing
**Use Cases**: Custom collections, data structures

**Build**: `cd 03_sequence_protocol && maturin develop`

---

### 04. Lazy Iterator
**Path**: `04_lazy_iterator/`
**Difficulty**: Intermediate
**What**: Lazy evaluation and deferred computation
**Key Concepts**: Fibonacci, filtering, chaining, transforms
**Use Cases**: Large datasets, infinite sequences

**Build**: `cd 04_lazy_iterator && maturin develop`

---

### 05. Bidirectional Iterator
**Path**: `05_bidirectional_iter/`
**Difficulty**: Intermediate
**What**: Forward and reverse iteration
**Key Concepts**: VecDeque, peekable, windows
**Use Cases**: Parsers, sliding windows, undo/redo

**Build**: `cd 05_bidirectional_iter && maturin develop`

---

### 06. Custom Collection
**Path**: `06_custom_collection/`
**Difficulty**: Intermediate
**What**: Domain-specific collection types
**Key Concepts**: Hybrid collection, priority queue, circular buffer
**Use Cases**: Caches, task queues, ring buffers

**Build**: `cd 06_custom_collection && maturin develop`

---

### 07. Iterator Combinators
**Path**: `07_iterator_combinators/`
**Difficulty**: Intermediate
**What**: Functional programming patterns
**Key Concepts**: Map, filter, chain, zip, take, skip
**Use Cases**: ETL pipelines, data transformation

**Build**: `cd 07_iterator_combinators && maturin develop`

---

### 08. Streaming Data
**Path**: `08_streaming_data/`
**Difficulty**: Advanced
**What**: Memory-efficient large data processing
**Key Concepts**: File streaming, chunking, CSV, buffering
**Use Cases**: Log analysis, batch processing

**Build**: `cd 08_streaming_data && maturin develop`

---

### 09. Parallel Iterator
**Path**: `09_parallel_iterator/`
**Difficulty**: Advanced
**What**: Multi-threaded data processing with Rayon
**Key Concepts**: Parallel map/filter/reduce, sorting, batching
**Use Cases**: High-performance computing, bulk operations
**Dependencies**: rayon = "1.8"

**Build**: `cd 09_parallel_iterator && maturin develop`

---

### 10. Production Pipeline
**Path**: `10_production_pipeline/`
**Difficulty**: Advanced
**What**: Complete end-to-end data pipeline
**Key Concepts**: Filters, transforms, stats, time series, anomaly detection
**Use Cases**: Analytics systems, data pipelines, monitoring
**Dependencies**: rayon = "1.8"

**Build**: `cd 10_production_pipeline && maturin develop`

---

## Learning Paths

### Path 1: Complete Beginner (10-12 hours)
```
01 → 02 → 03 → 04 → 07 → 08 → 10
Foundation  Patterns   Production
```

### Path 2: Intermediate Developer (6-8 hours)
```
Review: 01-03 → Focus: 04, 06, 07 → Advanced: 08-10
```

### Path 3: Advanced Developer (4-5 hours)
```
Skim: 01-07 → Deep Dive: 08, 09, 10
```

## Topic Index

### Iterator Basics
- 01: Basic iterator protocol
- 04: Lazy iterators
- 05: Bidirectional iterators

### Collections
- 02: Standard collections (list, dict, set)
- 03: Sequence protocol
- 06: Custom collection types

### Functional Patterns
- 04: Lazy evaluation
- 07: Combinators (map, filter, etc.)

### Performance
- 08: Streaming large data
- 09: Parallel processing
- 10: Production pipelines

## Quick Commands

**Verify all examples**:
```bash
./verify_structure.sh
```

**Build all examples**:
```bash
for dir in */; do
  (cd "$dir" && maturin develop)
done
```

**Test all examples**:
```bash
for dir in */; do
  (cd "$dir" && python test_example.py)
done
```

**Count lines**:
```bash
find . -name 'lib.rs' -exec wc -l {} + | tail -1
```

## File Structure

Each example contains:
```
XX_example_name/
├── src/
│   └── lib.rs          # Rust implementation
├── Cargo.toml          # Rust dependencies
├── pyproject.toml      # Python packaging
├── test_example.py     # Python tests
└── README.md           # Documentation
```

## Dependencies

**Required**:
- Rust 1.70+
- Python 3.8+
- PyO3 0.20+
- maturin 1.0+

**Optional** (for examples 09, 10):
- rayon 1.8+

## Statistics

- **Total Examples**: 10
- **Total Files**: 51
- **Total Lines**: 4,456
  - Rust: 2,081
  - Tests: 909
  - Docs: 1,466
- **Average Example Size**: ~200 lines Rust
- **Test Coverage**: ~40% test-to-code ratio

## Additional Resources

- [Main README](README.md) - Detailed overview
- [SUMMARY.txt](SUMMARY.txt) - Complete project summary
- [verify_structure.sh](verify_structure.sh) - Verification script

---

**Status**: ✓ Complete
**Last Updated**: 2025-10-30
**Verification**: All examples tested and verified
