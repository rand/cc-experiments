---
name: discover-systems-theory
description: Automatically discover eBPF, compiler, programming language theory, information retrieval, and formal verification skills when working with kernel tracing, parsers, type systems, Z3, Lean, or theorem proving
license: MIT
metadata:
  author: rand
  version: "4.0"
compatibility:
  claude-code: ">=1.0.0"
---

# Systems Theory & Language Design Skills Discovery

## When This Skill Activates
- eBPF, kernel tracing, XDP, kprobes, BPF
- Compilers, parsers, interpreters, AST, bytecode
- Type systems, type theory, programming language design
- LLVM, IR, SSA, code generation, optimization passes
- Information retrieval, search, ranking, vector search
- Formal verification, theorem proving, model checking
- SAT, SMT, Z3, Lean, constraint solving

## Available Skills (32 total)

### eBPF (4 skills)
1. **ebpf-fundamentals** - eBPF programs, verifier, maps
2. **ebpf-networking** - XDP, TC, socket filtering
3. **ebpf-security-monitoring** - LSM hooks, syscall tracing
4. **ebpf-tracing-observability** - kprobes, tracepoints, profiling

### Information Retrieval (5 skills)
1. **ir-search-fundamentals** - Indexing, tokenization, TF-IDF, BM25
2. **ir-query-understanding** - Query parsing, expansion, intent
3. **ir-ranking-reranking** - Learning to rank, cross-encoders
4. **ir-vector-search** - Embeddings, ANN, HNSW, FAISS
5. **ir-recommendation-systems** - Collaborative/content-based filtering

### Programming Language Theory (13 skills)
1. **type-systems** - Type theory, inference, polymorphism
2. **lambda-calculus** - Lambda calculus, reduction, Church encodings
3. **curry-howard** - Propositions as types, proofs as programs
4. **dependent-types** - Dependent types, refinement types
5. **operational-semantics** - Small-step, big-step semantics
6. **program-verification** - Hoare logic, invariants, correctness
7. **structure-editors** - Structural editing, projectional editors
8. **hazelnut-calculus** - Hazelnut typed holes calculus
9. **live-programming-holes** - Live programming with typed holes
10. **typed-holes-foundations** - Typed holes theory and foundations
11. **typed-holes-interaction** - Interactive typed hole filling
12. **typed-holes-llm** - LLM-powered typed hole completion
13. **typed-holes-semantics** - Typed holes formal semantics

### Formal Methods (10 skills)
1. **z3-solver-basics** - Z3 SMT solver, constraints, assertions
2. **sat-solving-strategies** - SAT solving, DPLL, CDCL
3. **smt-theory-applications** - SMT theories, bitvectors, arrays
4. **lean-proof-basics** - Lean 4 basics, tactics, terms
5. **lean-tactics** - Advanced Lean tactics and automation
6. **lean-theorem-proving** - Theorem proving patterns in Lean
7. **lean-mathlib4** - Mathlib4 library usage
8. **csp-modeling** - Constraint satisfaction problems
9. **constraint-propagation** - Arc consistency, propagation
10. **backtracking-search** - Backtracking, branch and bound

## Load Full Category Details
Read ../ebpf/INDEX.md
Read ../ir/INDEX.md
Read ../plt/INDEX.md
Read ../formal/INDEX.md

## Progressive Loading
- **Level 1**: This gateway loads automatically (~70 lines)
- **Level 2**: Load category INDEX.md for full skill listings
- **Level 3**: Load specific skills as needed
