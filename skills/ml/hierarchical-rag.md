---
name: hierarchical-rag
description: Multi-level retrieval with recursive summarization and parent-child document structures for improved context selection
---

# Hierarchical RAG

**Scope**: Multi-level document structures, recursive summarization, parent-child chunks, top-down/bottom-up retrieval
**Lines**: ~420
**Last Updated**: 2025-10-26

## When to Use This Skill

Activate this skill when:
- Documents have natural hierarchies (books → chapters → sections → paragraphs)
- Need both high-level summaries and detailed content
- Standard flat chunking loses document structure context
- Queries vary in abstraction level ("summarize the book" vs "explain section 3.2")
- Working with long-form content (technical docs, research papers, books)
- Want to preserve document structure for better context
- Need to zoom in/out between summary and detail levels
- Using LlamaIndex or LangChain hierarchical document loaders
- Evaluating retrieval quality with RAGAS hierarchical metrics

## Core Concepts

### Hierarchical Document Structure

**Levels** (example: technical documentation):
```
Level 0 (Root): Entire document
Level 1 (Chapter): "Chapter 3: Architecture"
Level 2 (Section): "3.2 Database Design"
Level 3 (Subsection): "3.2.1 Schema Optimization"
Level 4 (Paragraph): Individual paragraphs
```

**Why hierarchy matters**:
- Context: Section title provides context for paragraphs
- Navigation: Can drill down from high-level to specific
- Flexibility: Answer high-level or detailed queries

### Flat vs Hierarchical Chunking

**Flat chunking** (standard RAG):
```
Document → [Chunk 1, Chunk 2, Chunk 3, ...]
```
- Each chunk independent
- Loses document structure
- Same chunk size for all content

**Hierarchical chunking**:
```
Document (summary)
  ├─ Chapter 1 (summary)
  │   ├─ Section 1.1 (summary)
  │   │   ├─ Paragraph 1
  │   │   └─ Paragraph 2
  │   └─ Section 1.2 (summary)
  └─ Chapter 2 (summary)
```
- Parent-child relationships preserved
- Each level has summaries
- Can navigate up/down hierarchy

### Recursive Summarization

**Process**: Bottom-up summary generation
```
1. Leaf nodes: Original text (paragraphs)
2. Level 3: Summarize paragraphs → subsection summary
3. Level 2: Summarize subsections → section summary
4. Level 1: Summarize sections → chapter summary
5. Level 0: Summarize chapters → document summary
```

**Benefits**:
- Multi-resolution: Query at any abstraction level
- Context propagation: Parent summaries provide context
- Efficient: Can answer high-level queries without reading all details

### Retrieval Strategies

**Top-down** (coarse-to-fine):
```
1. Retrieve at high level (e.g., chapter summaries)
2. If relevant, drill down to sections
3. Continue until reaching paragraph level
```
- Use: Exploratory queries, broad questions

**Bottom-up** (fine-to-coarse):
```
1. Retrieve at paragraph level (detailed)
2. Include parent contexts (section, chapter)
3. Return combined context
```
- Use: Specific queries, factual lookups

**Hybrid** (both directions):
```
1. Retrieve at paragraph level
2. Include parent summaries (section, chapter)
3. Include sibling paragraphs (same section)
4. Return enriched context
```
- Use: General-purpose (recommended)

### Parent-Child Chunks

**Parent**: Higher-level summary or context
**Child**: Detailed content within parent

**Example**:
```
Parent: "Section 3.2: Database Design (Summary: This section covers..."
Children: [
  "Paragraph 1: PostgreSQL was chosen because...",
  "Paragraph 2: The schema includes five main tables..."
]
```

**Retrieval pattern**:
1. Embed and retrieve child chunks
2. When child matches, include parent context
3. LLM sees both detail and surrounding context

---

## Implementation Patterns

### Pattern 1: Recursive Summarization with DSPy

```python
import dspy
from typing import List, Dict

class RecursiveSummarizer(dspy.Module):
    """Build hierarchical summaries bottom-up."""

    def __init__(self):
        super().__init__()
        self.summarize = dspy.ChainOfThought("text -> summary")

    def forward(self, text: str):
        return self.summarize(text=text)


class HierarchicalDocumentBuilder:
    """Build hierarchical document structure with summaries."""

    def __init__(self):
        self.summarizer = RecursiveSummarizer()
        self.hierarchy = {}

    def build_hierarchy(self, document: str, levels: List[str]) -> Dict:
        """
        Build hierarchy from document.

        Args:
            document: Full document text
            levels: Level definitions (e.g., ["chapter", "section", "paragraph"])
        """
        # Parse document into hierarchy (simplified)
        # In practice, use proper document parser
        parsed = self._parse_document(document, levels)

        # Build summaries bottom-up
        self._build_summaries(parsed)

        return parsed

    def _parse_document(self, document: str, levels: List[str]) -> Dict:
        """Parse document into hierarchical structure."""
        # Simplified: Split by headers/sections
        # Real implementation: Use markdown parser, PDF parser, etc.

        hierarchy = {
            "level": "document",
            "text": document,
            "summary": None,
            "children": []
        }

        # Example: Split into chapters (level 1)
        chapters = document.split("\n# ")  # Markdown H1

        for chapter_text in chapters[1:]:  # Skip first split
            chapter_node = {
                "level": "chapter",
                "text": chapter_text,
                "summary": None,
                "children": []
            }

            # Split into sections (level 2)
            sections = chapter_text.split("\n## ")  # Markdown H2

            for section_text in sections[1:]:
                section_node = {
                    "level": "section",
                    "text": section_text,
                    "summary": None,
                    "children": []
                }

                # Split into paragraphs (level 3)
                paragraphs = section_text.split("\n\n")

                for para in paragraphs:
                    para_node = {
                        "level": "paragraph",
                        "text": para,
                        "summary": para,  # Paragraphs are leaf nodes
                        "children": []
                    }
                    section_node["children"].append(para_node)

                chapter_node["children"].append(section_node)

            hierarchy["children"].append(chapter_node)

        return hierarchy

    def _build_summaries(self, node: Dict):
        """Recursively build summaries bottom-up."""
        # Base case: leaf nodes (paragraphs)
        if not node["children"]:
            return

        # Recursive case: summarize children first
        for child in node["children"]:
            self._build_summaries(child)

        # Summarize this level from children
        if node["children"]:
            child_summaries = [child["summary"] for child in node["children"]]
            combined = "\n\n".join(child_summaries)

            summary_result = self.summarizer(text=combined)
            node["summary"] = summary_result.summary


# Usage
lm = dspy.LM("openai/gpt-4o-mini")
dspy.configure(lm=lm)

document = """
# Chapter 1: Introduction
## Section 1.1: Background
This is paragraph 1 of section 1.1.

This is paragraph 2 of section 1.1.

## Section 1.2: Motivation
This is paragraph 1 of section 1.2.

# Chapter 2: Methods
## Section 2.1: Approach
This is paragraph 1 of section 2.1.
"""

builder = HierarchicalDocumentBuilder()
hierarchy = builder.build_hierarchy(document, levels=["chapter", "section", "paragraph"])

print("Document summary:", hierarchy["summary"])
print("Chapter 1 summary:", hierarchy["children"][0]["summary"])
```

**When to use**:
- Building multi-level summaries for navigation
- Need to answer queries at different abstraction levels
- Want to preserve document structure

### Pattern 2: Parent-Child Chunk Retrieval with DSPy

```python
import dspy
from typing import List, Dict, Tuple

class ParentChildRetriever:
    """Retrieve child chunks with parent context."""

    def __init__(self, hierarchy: Dict):
        self.hierarchy = hierarchy
        self.chunks = []
        self.parent_map = {}

        # Flatten hierarchy into chunks with parent pointers
        self._flatten_hierarchy(hierarchy, parent=None)

    def _flatten_hierarchy(self, node: Dict, parent: Dict):
        """Flatten hierarchy into retrievable chunks."""
        # Add this node as chunk (except root)
        if node["level"] != "document":
            chunk_id = len(self.chunks)
            self.chunks.append({
                "id": chunk_id,
                "level": node["level"],
                "text": node["text"],
                "summary": node["summary"]
            })

            # Map to parent
            if parent:
                self.parent_map[chunk_id] = parent

        # Recurse to children
        for child in node["children"]:
            self._flatten_hierarchy(child, parent=node)

    def retrieve(self, query: str, k=5) -> List[Dict]:
        """Retrieve chunks with parent context."""
        # Simplified: Use embedding similarity (in practice, use vector DB)
        # For demo, just return top chunks

        retrieved_chunks = []

        for chunk in self.chunks[:k]:  # Simplified selection
            # Get parent context
            parent_context = None
            if chunk["id"] in self.parent_map:
                parent = self.parent_map[chunk["id"]]
                parent_context = parent["summary"]

            retrieved_chunks.append({
                "text": chunk["text"],
                "summary": chunk["summary"],
                "level": chunk["level"],
                "parent_context": parent_context
            })

        return retrieved_chunks


class HierarchicalRAG(dspy.Module):
    """RAG with hierarchical retrieval."""

    def __init__(self, retriever: ParentChildRetriever):
        super().__init__()
        self.retriever = retriever
        self.generate = dspy.ChainOfThought("context, question -> answer")

    def forward(self, question: str):
        # Retrieve chunks with parent context
        retrieved = self.retriever.retrieve(question, k=5)

        # Format context with hierarchy
        context_parts = []
        for chunk in retrieved:
            if chunk["parent_context"]:
                context_parts.append(f"[Parent: {chunk['parent_context']}]\n{chunk['text']}")
            else:
                context_parts.append(chunk["text"])

        context = "\n\n---\n\n".join(context_parts)

        return self.generate(context=context, question=question)


# Usage
retriever = ParentChildRetriever(hierarchy)
rag = HierarchicalRAG(retriever)

result = rag(question="What is section 1.1 about?")
print(result.answer)
```

**When to use**:
- Want to preserve parent context in retrieval
- Chunks benefit from surrounding section/chapter info
- Standard flat retrieval loses important context

### Pattern 3: Top-Down Hierarchical Retrieval

```python
import dspy

class TopDownRetriever(dspy.Module):
    """Top-down coarse-to-fine retrieval."""

    def __init__(self, hierarchy: Dict, max_depth=3):
        super().__init__()
        self.hierarchy = hierarchy
        self.max_depth = max_depth

        # LLM to decide if we need to drill down
        self.should_drill = dspy.ChainOfThought(
            "question, summary -> is_relevant: bool, drill_down: bool"
        )

    def forward(self, question: str, current_depth=0):
        """Recursively drill down if relevant."""
        if current_depth >= self.max_depth:
            return []

        relevant_nodes = []

        # Check each node at current level
        for node in self._get_nodes_at_depth(self.hierarchy, current_depth):
            # Check if node is relevant
            decision = self.should_drill(
                question=question,
                summary=node["summary"]
            )

            if decision.is_relevant:
                relevant_nodes.append(node)

                # Drill down to children if needed
                if decision.drill_down and node["children"]:
                    child_results = self._drill_down(question, node, current_depth + 1)
                    relevant_nodes.extend(child_results)

        return relevant_nodes

    def _get_nodes_at_depth(self, node: Dict, target_depth: int, current_depth=0):
        """Get all nodes at target depth."""
        if current_depth == target_depth:
            return [node]

        nodes = []
        for child in node["children"]:
            nodes.extend(self._get_nodes_at_depth(child, target_depth, current_depth + 1))

        return nodes

    def _drill_down(self, question: str, node: Dict, depth: int):
        """Drill down into node's children."""
        relevant = []

        for child in node["children"]:
            decision = self.should_drill(question=question, summary=child["summary"])

            if decision.is_relevant:
                relevant.append(child)

                if decision.drill_down and child["children"]:
                    relevant.extend(self._drill_down(question, child, depth + 1))

        return relevant


class TopDownRAG(dspy.Module):
    """RAG with top-down hierarchical retrieval."""

    def __init__(self, hierarchy: Dict):
        super().__init__()
        self.retriever = TopDownRetriever(hierarchy, max_depth=3)
        self.generate = dspy.ChainOfThought("context, question -> answer")

    def forward(self, question: str):
        # Top-down retrieval
        relevant_nodes = self.retriever(question=question)

        # Extract text from nodes
        context_parts = [node["text"] for node in relevant_nodes]
        context = "\n\n".join(context_parts)

        return self.generate(context=context, question=question)
```

**When to use**:
- Exploratory queries (broad questions)
- Want to avoid reading all details if high-level summary suffices
- Efficient retrieval for large documents

### Pattern 4: LlamaIndex Hierarchical Document Loader

```python
import dspy
from llama_index.core import Document, VectorStoreIndex
from llama_index.core.node_parser import HierarchicalNodeParser

class LlamaIndexHierarchicalRAG:
    """Hierarchical RAG using LlamaIndex."""

    def __init__(self, documents: List[str]):
        # Parse documents hierarchically
        parser = HierarchicalNodeParser.from_defaults(
            chunk_sizes=[2048, 512, 128]  # Level sizes: chapter, section, paragraph
        )

        # Create LlamaIndex documents
        docs = [Document(text=doc) for doc in documents]

        # Parse into hierarchical nodes
        nodes = parser.get_nodes_from_documents(docs)

        # Build index
        self.index = VectorStoreIndex(nodes)

    def query(self, question: str, similarity_top_k=5):
        """Query with hierarchical retrieval."""
        query_engine = self.index.as_query_engine(
            similarity_top_k=similarity_top_k,
            response_mode="tree_summarize"  # Use hierarchy for response
        )

        response = query_engine.query(question)
        return response


# Usage
documents = [
    "Large document 1 with chapters and sections...",
    "Large document 2 with chapters and sections...",
]

rag = LlamaIndexHierarchicalRAG(documents)
response = rag.query("What are the main themes?")
print(response)
```

**When to use**:
- Using LlamaIndex ecosystem
- Want built-in hierarchical parsing
- Need tree summarization for responses

### Pattern 5: RAGAS Hierarchical Evaluation

```python
import dspy
from ragas import evaluate
from ragas.metrics import context_precision, context_recall, faithfulness

class HierarchicalRAGEvaluator:
    """Evaluate hierarchical RAG quality."""

    def __init__(self, rag_system):
        self.rag = rag_system

    def evaluate(self, test_set):
        """Evaluate using RAGAS metrics."""
        predictions = []

        for example in test_set:
            result = self.rag(question=example.question)

            predictions.append({
                "question": example.question,
                "answer": result.answer,
                "contexts": result.retrieved_contexts,  # Hierarchical contexts
                "ground_truth": example.ground_truth
            })

        # Evaluate with RAGAS
        ragas_results = evaluate(
            dataset=predictions,
            metrics=[
                context_precision,  # Precision of retrieved contexts
                context_recall,     # Recall of relevant contexts
                faithfulness        # Answer faithfulness to context
            ]
        )

        print("RAGAS Results:")
        print(f"Context Precision: {ragas_results['context_precision']:.3f}")
        print(f"Context Recall: {ragas_results['context_recall']:.3f}")
        print(f"Faithfulness: {ragas_results['faithfulness']:.3f}")

        return ragas_results
```

**Metrics**:
- **Context precision**: Are retrieved chunks relevant?
- **Context recall**: Did we retrieve all relevant chunks?
- **Faithfulness**: Is answer grounded in retrieved context?

---

## Quick Reference

### Retrieval Strategy Selection
```
Broad question → Top-down (coarse-to-fine)
Specific question → Bottom-up (fine-to-coarse)
General purpose → Hybrid (parent-child)
```

### Hierarchy Levels (Typical)
```
Level 0: Document (1-10K tokens)
Level 1: Chapter (1K-3K tokens)
Level 2: Section (300-1K tokens)
Level 3: Subsection (100-300 tokens)
Level 4: Paragraph (50-150 tokens)
```

### Summary Generation
```
Leaf nodes: Original text
Internal nodes: Summarize children (recursive)
Root: Overall document summary
```

### Platform Support
```
LlamaIndex: HierarchicalNodeParser (built-in)
LangChain: RecursiveCharacterTextSplitter (custom)
DSPy: Custom hierarchy builders (this skill)
```

---

## Anti-Patterns

❌ **Losing parent context during retrieval**:
```python
# Bad - retrieve paragraphs without parent context
chunks = retrieve(query, k=5)  # Just paragraphs
context = "\n".join(chunks)  # No section/chapter info
```
✅ Include parent context:
```python
# Good - retrieve with parent summaries
chunks = retrieve_with_parents(query, k=5)
context = format_hierarchical_context(chunks)  # Includes parent info
```

❌ **Flat chunking for hierarchical documents**:
```python
# Bad - split book into equal 512-token chunks
chunks = split_text(book, chunk_size=512)  # Loses structure
```
✅ Preserve hierarchy:
```python
# Good - parse hierarchy first
hierarchy = parse_hierarchical(book)  # Chapters → sections → paragraphs
chunks = hierarchical_chunks(hierarchy)
```

❌ **Not summarizing intermediate levels**:
```python
# Bad - only store leaf paragraphs
for paragraph in document:
    store(paragraph)  # No chapter/section summaries
```
✅ Build summaries at all levels:
```python
# Good - recursive summarization
hierarchy = build_hierarchy(document)
add_summaries_recursive(hierarchy)  # All levels have summaries
```

❌ **Same chunk size for all levels**:
```python
# Bad - 512 tokens for everything
chunks = [
    {"level": "chapter", "size": 512},  # Too small!
    {"level": "paragraph", "size": 512}  # Too large!
]
```
✅ Level-appropriate sizes:
```python
# Good - larger chunks for higher levels
chunks = [
    {"level": "chapter", "size": 2048},
    {"level": "section", "size": 512},
    {"level": "paragraph", "size": 128}
]
```

---

## Related Skills

- `dspy-rag.md` - Basic RAG patterns and flat retrieval
- `hybrid-search-rag.md` - Combining vector and BM25 retrieval
- `rag-reranking-techniques.md` - Multi-stage retrieval
- `graph-rag.md` - Graph-based retrieval for relationships
- `database/postgres-schema-design.md` - Storing hierarchical data

---

## Summary

Hierarchical RAG preserves document structure for better context and flexible retrieval:
- **Architecture**: Parse hierarchy → Recursive summarization → Multi-level retrieval
- **Parent-child chunks**: Retrieve detailed content with surrounding context
- **Retrieval strategies**: Top-down (coarse-to-fine), bottom-up (fine-to-coarse), hybrid
- **Typical levels**: Document → Chapter → Section → Subsection → Paragraph
- **Platforms**: LlamaIndex HierarchicalNodeParser, LangChain recursive splitters, custom DSPy
- **Evaluation**: RAGAS metrics (context precision, recall, faithfulness)
- **Best practice**: Use hierarchy for structured documents (books, docs, papers), flat chunking for unstructured text
- **Key advantage**: Answer queries at any abstraction level ("summarize book" or "explain section 3.2")

Hierarchical RAG is most valuable for long-form, structured documents where context and navigation matter.

---

**Last Updated**: 2025-10-26
**Format Version**: 1.0 (Atomic)
