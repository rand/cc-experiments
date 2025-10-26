---
name: graph-rag
description: Graph-based retrieval-augmented generation with entity extraction, community detection, and multihop reasoning
---

# Graph RAG

**Scope**: Entity graphs, Microsoft GraphRAG, community detection, multihop reasoning, Neo4j integration
**Lines**: ~480
**Last Updated**: 2025-10-26

## When to Use This Skill

Activate this skill when:
- Queries require multihop reasoning across connected entities
- Need to answer "what are the themes" or "summarize across topics" (global queries)
- Working with large document collections (>1M tokens, 100+ documents)
- Standard vector RAG misses entity relationships and connections
- Building knowledge graphs from unstructured text
- Queries involve entity relationships (e.g., "How are X and Y related?")
- Implementing Microsoft GraphRAG (2024) or similar graph-based RAG
- Exploring SAM-RAG, ArchRAG, LightRAG variants (2024-2025)
- Using Neo4j, ArangoDB, or other graph databases for retrieval
- Need explainable reasoning paths (graph traversal evidence)
- Evaluating graph RAG quality with LLM-as-judge

## Core Concepts

### What is Graph RAG?

**Graph RAG**: Build knowledge graph from documents → Query graph for retrieval
1. **Extract**: Entities and relationships from text
2. **Build**: Knowledge graph (nodes = entities, edges = relationships)
3. **Detect**: Communities (clusters of related entities)
4. **Summarize**: Community summaries (hierarchical)
5. **Query**: Local (entity-specific) or global (theme-based)

**Difference from vector RAG**:
- Vector RAG: Similarity in embedding space
- Graph RAG: Structural relationships in graph

**When graph wins**:
- Multihop questions: "How did X influence Y through Z?"
- Global questions: "What are the main themes in this dataset?"
- Entity-centric: "Tell me about all events involving X"

### Microsoft GraphRAG (2024)

**Paper**: "From Local to Global: A Graph RAG Approach to Query-Focused Summarization" (Microsoft, 2024)

**Key innovations**:
1. **Entity extraction**: LLM extracts entities + relationships
2. **Community detection**: Leiden algorithm clusters entities
3. **Hierarchical summarization**: Communities summarized at multiple levels
4. **Query types**:
   - Local: Entity-specific (standard RAG-like)
   - Global: Dataset-wide themes (unique to GraphRAG)

**Results** (Microsoft 2024 benchmarks):
- 72.5% comprehensiveness vs 10-20% for naive RAG (global queries)
- Handles 1M+ token datasets effectively
- Trade-off: 5-10x cost for graph building

### Community Detection (Leiden Algorithm)

**Leiden algorithm**: Find densely connected clusters in graph
- Improves on Louvain method (2019)
- Hierarchical: Multi-level communities
- Used by Microsoft GraphRAG

**Example**:
```
Entities: {Alice, Bob, Carol, Dave, Eve}
Edges: Alice-Bob, Bob-Carol (community 1)
        Dave-Eve (community 2)
Communities: {Alice, Bob, Carol}, {Dave, Eve}
```

**Why useful**: Summarize communities instead of individual entities

### Local vs Global Queries

**Local queries** (entity-specific):
- "What is Alice's role?"
- "How are Alice and Bob related?"
- Strategy: Find entity → Traverse graph → Retrieve context

**Global queries** (theme-based):
- "What are the main themes in this dataset?"
- "Summarize the key events"
- Strategy: Use community summaries → Aggregate insights

### Recent Variants (2024-2025)

**SAM-RAG** (Self-Augmented Memory):
- Adds memory layer to graph
- Stores conversation context in graph
- Use: Conversational RAG with history

**ArchRAG** (Architectural RAG):
- Optimizes graph structure for retrieval
- Prunes irrelevant edges
- Use: Large-scale efficiency

**LightRAG** (Lightweight):
- Simpler entity extraction (no full LLM)
- Faster graph building
- Use: Resource-constrained environments

### PIKE-RAG Findings (2024)

**PIKE-RAG study**: "When Does Graph RAG Underperform?"
- Graph RAG excels: Multihop, global queries
- Graph RAG struggles: Simple lookups, single-document queries
- Key insight: Graph overhead not worth it for all query types

**Recommendation**: Hybrid approach (vector for simple, graph for complex)

---

## Implementation Patterns

### Pattern 1: Microsoft GraphRAG with DSPy

```python
import dspy
import networkx as nx
from typing import List, Dict
import community as community_louvain  # python-louvain for Leiden

class EntityExtractor(dspy.Module):
    """Extract entities and relationships from text."""

    def __init__(self):
        super().__init__()
        self.extract = dspy.ChainOfThought(
            "text -> entities: list[str], relationships: list[tuple[str, str, str]]"
        )

    def forward(self, text: str):
        result = self.extract(text=text)
        return result


class GraphRAGBuilder:
    """Build knowledge graph from documents."""

    def __init__(self):
        self.graph = nx.Graph()
        self.extractor = EntityExtractor()

    def add_documents(self, documents: List[str]):
        """Extract entities and build graph."""
        for doc in documents:
            extraction = self.extractor(text=doc)

            # Add entities as nodes
            for entity in extraction.entities:
                if not self.graph.has_node(entity):
                    self.graph.add_node(entity, documents=[])
                self.graph.nodes[entity]['documents'].append(doc)

            # Add relationships as edges
            for source, relation, target in extraction.relationships:
                if source in extraction.entities and target in extraction.entities:
                    self.graph.add_edge(source, target, relation=relation)

    def detect_communities(self):
        """Detect communities using Leiden algorithm."""
        # Using Louvain as approximation (python-louvain library)
        communities = community_louvain.best_partition(self.graph)

        # Assign community IDs to nodes
        for node, comm_id in communities.items():
            self.graph.nodes[node]['community'] = comm_id

        return communities

    def get_community_subgraph(self, community_id: int):
        """Extract subgraph for a community."""
        nodes = [n for n, d in self.graph.nodes(data=True) if d.get('community') == community_id]
        return self.graph.subgraph(nodes)


class CommunitySummarizer(dspy.Module):
    """Summarize a community of entities."""

    def __init__(self):
        super().__init__()
        self.summarize = dspy.ChainOfThought(
            "entities, relationships, documents -> summary"
        )

    def forward(self, subgraph, documents):
        entities = list(subgraph.nodes())
        relationships = [
            f"{u} -{subgraph.edges[u, v]['relation']}-> {v}"
            for u, v in subgraph.edges()
        ]

        summary = self.summarize(
            entities=entities,
            relationships=relationships,
            documents=documents
        )

        return summary


class GraphRAG(dspy.Module):
    """Graph RAG with local and global query support."""

    def __init__(self, graph_builder: GraphRAGBuilder):
        super().__init__()
        self.builder = graph_builder
        self.summarizer = CommunitySummarizer()

        # For local queries
        self.local_gen = dspy.ChainOfThought("context, question -> answer")

        # For global queries
        self.global_gen = dspy.ChainOfThought("summaries, question -> answer")

    def forward(self, question: str, query_type="local"):
        if query_type == "local":
            return self._local_query(question)
        else:
            return self._global_query(question)

    def _local_query(self, question: str):
        """Entity-specific query (like standard RAG)."""
        # Extract entities from question
        entity_extraction = EntityExtractor()(text=question)
        query_entities = entity_extraction.entities

        # Find relevant nodes in graph
        context_docs = []
        for entity in query_entities:
            if self.builder.graph.has_node(entity):
                docs = self.builder.graph.nodes[entity].get('documents', [])
                context_docs.extend(docs)

        # Generate answer from context
        context = "\n\n".join(set(context_docs))
        return self.local_gen(context=context, question=question)

    def _global_query(self, question: str):
        """Global query using community summaries."""
        # Detect communities
        communities = self.builder.detect_communities()

        # Summarize each community
        summaries = []
        for comm_id in set(communities.values()):
            subgraph = self.builder.get_community_subgraph(comm_id)

            # Collect documents for community
            docs = []
            for node in subgraph.nodes():
                docs.extend(self.builder.graph.nodes[node].get('documents', []))

            summary = self.summarizer(subgraph=subgraph, documents=docs)
            summaries.append(summary.summary)

        # Generate answer from summaries
        summaries_text = "\n\n".join(summaries)
        return self.global_gen(summaries=summaries_text, question=question)


# Usage
lm = dspy.LM("openai/gpt-4o-mini")
dspy.configure(lm=lm)

# Build graph
documents = [
    "Alice works with Bob on the AI project.",
    "Bob collaborates with Carol on machine learning.",
    "Dave and Eve are working on the robotics team.",
]

builder = GraphRAGBuilder()
builder.add_documents(documents)

# Query graph
rag = GraphRAG(builder)

# Local query
result_local = rag(question="What is Bob working on?", query_type="local")
print("Local:", result_local.answer)

# Global query
result_global = rag(question="What are the main projects?", query_type="global")
print("Global:", result_global.answer)
```

**When to use**:
- Need both local (entity) and global (theme) queries
- Have 100+ documents to build knowledge graph
- Can afford LLM costs for entity extraction

### Pattern 2: Neo4j Graph RAG Integration

```python
import dspy
from neo4j import GraphDatabase

class Neo4jGraphRAG:
    """Graph RAG using Neo4j database."""

    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.extractor = EntityExtractor()

    def add_documents(self, documents: List[str]):
        """Extract entities and store in Neo4j."""
        with self.driver.session() as session:
            for doc in documents:
                extraction = self.extractor(text=doc)

                # Create entity nodes
                for entity in extraction.entities:
                    session.run(
                        "MERGE (e:Entity {name: $name}) "
                        "ON CREATE SET e.documents = [$doc] "
                        "ON MATCH SET e.documents = e.documents + $doc",
                        name=entity, doc=doc
                    )

                # Create relationship edges
                for source, relation, target in extraction.relationships:
                    session.run(
                        "MATCH (s:Entity {name: $source}), (t:Entity {name: $target}) "
                        "MERGE (s)-[r:RELATED {type: $relation}]->(t)",
                        source=source, target=target, relation=relation
                    )

    def query_entity_neighborhood(self, entity: str, hops=2):
        """Retrieve entity neighborhood (multihop)."""
        with self.driver.session() as session:
            result = session.run(
                f"""
                MATCH path = (e:Entity {{name: $entity}})-[*1..{hops}]-(connected)
                RETURN connected.name AS entity, connected.documents AS documents
                """,
                entity=entity
            )

            docs = []
            for record in result:
                docs.extend(record["documents"])

            return list(set(docs))

    def query_global_communities(self):
        """Get community summaries using Neo4j community detection."""
        with self.driver.session() as session:
            # Run Louvain community detection
            session.run(
                "CALL gds.louvain.write('myGraph', {writeProperty: 'community'})"
            )

            # Get communities
            result = session.run(
                "MATCH (e:Entity) "
                "RETURN e.community AS community, collect(e.name) AS entities"
            )

            communities = {}
            for record in result:
                communities[record["community"]] = record["entities"]

            return communities

    def close(self):
        self.driver.close()


class Neo4jRAG(dspy.Module):
    """RAG with Neo4j graph backend."""

    def __init__(self, neo4j_rag: Neo4jGraphRAG):
        super().__init__()
        self.neo4j = neo4j_rag
        self.generate = dspy.ChainOfThought("context, question -> answer")

    def forward(self, question: str, entity: str = None, hops=2):
        if entity:
            # Local query: entity neighborhood
            docs = self.neo4j.query_entity_neighborhood(entity, hops=hops)
            context = "\n\n".join(docs)
        else:
            # Global query: all documents
            # (Simplified; in practice, use community summaries)
            context = "Global context from Neo4j"

        return self.generate(context=context, question=question)
```

**When to use**:
- Need production-scale graph database (millions of entities)
- Want persistent graph storage
- Need advanced graph algorithms (Neo4j GDS library)
- Building multi-user RAG applications

### Pattern 3: Multihop Reasoning with Graph Traversal

```python
import dspy
import networkx as nx

class MultihopGraphRAG(dspy.Module):
    """Graph RAG with explicit multihop reasoning."""

    def __init__(self, graph: nx.Graph, max_hops=3):
        super().__init__()
        self.graph = graph
        self.max_hops = max_hops

        # Extract next hop query
        self.next_hop = dspy.ChainOfThought(
            "question, current_context -> needs_more_info: bool, next_entity"
        )

        # Final answer generation
        self.generate = dspy.ChainOfThought("context, question -> answer, reasoning_path")

    def forward(self, question: str, start_entity: str):
        visited = set()
        all_context = []
        reasoning_path = [start_entity]

        current_entity = start_entity

        for hop in range(self.max_hops):
            # Get context for current entity
            if self.graph.has_node(current_entity):
                docs = self.graph.nodes[current_entity].get('documents', [])
                all_context.extend(docs)
                visited.add(current_entity)

            # Check if we need more info
            context_so_far = "\n".join(all_context)
            hop_result = self.next_hop(question=question, current_context=context_so_far)

            if not hop_result.needs_more_info:
                break

            # Find next entity to explore
            next_entity = hop_result.next_entity

            # Verify entity exists and is connected
            if self.graph.has_node(next_entity) and next_entity not in visited:
                # Check if reachable from current entity
                if nx.has_path(self.graph, current_entity, next_entity):
                    reasoning_path.append(next_entity)
                    current_entity = next_entity
                else:
                    break  # Not reachable
            else:
                break

        # Generate final answer
        final_context = "\n\n".join(all_context)
        result = self.generate(context=final_context, question=question)

        result.reasoning_path = " → ".join(reasoning_path)
        result.num_hops = len(reasoning_path) - 1

        return result


# Example usage
G = nx.Graph()
G.add_node("Alice", documents=["Alice is a researcher in AI."])
G.add_node("Bob", documents=["Bob works on NLP with Alice."])
G.add_node("Carol", documents=["Carol collaborates with Bob on transformers."])
G.add_edge("Alice", "Bob", relation="collaborates")
G.add_edge("Bob", "Carol", relation="works_with")

rag = MultihopGraphRAG(G, max_hops=3)
result = rag(question="How is Alice connected to transformer research?", start_entity="Alice")

print("Answer:", result.answer)
print("Path:", result.reasoning_path)  # Alice → Bob → Carol
print("Hops:", result.num_hops)
```

**When to use**:
- Queries explicitly require multihop reasoning
- Need to show reasoning paths to users (explainability)
- Working with knowledge graphs where relationships matter

### Pattern 4: LLM-as-Judge for Graph RAG Quality

```python
import dspy

class GraphRAGJudge(dspy.Module):
    """Evaluate Graph RAG answer quality using LLM."""

    def __init__(self):
        super().__init__()
        self.judge = dspy.ChainOfThought(
            "question, answer, reasoning_path, ground_truth -> "
            "correctness: float, completeness: float, path_quality: float, feedback"
        )

    def forward(self, question, answer, reasoning_path, ground_truth):
        result = self.judge(
            question=question,
            answer=answer,
            reasoning_path=reasoning_path,
            ground_truth=ground_truth
        )

        return result


def evaluate_graph_rag(graph_rag, test_set):
    """Evaluate Graph RAG system."""
    judge = GraphRAGJudge()

    results = []
    for example in test_set:
        # Generate answer
        prediction = graph_rag(
            question=example.question,
            start_entity=example.start_entity
        )

        # Judge quality
        judgment = judge(
            question=example.question,
            answer=prediction.answer,
            reasoning_path=prediction.reasoning_path,
            ground_truth=example.ground_truth
        )

        results.append({
            "question": example.question,
            "answer": prediction.answer,
            "path": prediction.reasoning_path,
            "correctness": float(judgment.correctness),
            "completeness": float(judgment.completeness),
            "path_quality": float(judgment.path_quality),
            "feedback": judgment.feedback
        })

    # Aggregate metrics
    avg_correctness = sum(r["correctness"] for r in results) / len(results)
    avg_completeness = sum(r["completeness"] for r in results) / len(results)
    avg_path_quality = sum(r["path_quality"] for r in results) / len(results)

    print(f"Correctness: {avg_correctness:.2f}")
    print(f"Completeness: {avg_completeness:.2f}")
    print(f"Path Quality: {avg_path_quality:.2f}")

    return results
```

**Metrics**:
- **Correctness**: Is the answer factually correct?
- **Completeness**: Does it cover all aspects of the question?
- **Path quality**: Is the reasoning path logical and efficient?

---

## Quick Reference

### Query Type Selection
```
Simple lookup → Vector RAG (cheaper, faster)
Multihop reasoning → Graph RAG (better quality)
Global themes → Graph RAG (community summaries)
Entity relationships → Graph RAG (graph traversal)
```

### Graph Building Steps
```
1. Extract entities + relationships (LLM)
2. Build graph (NetworkX or Neo4j)
3. Detect communities (Leiden/Louvain)
4. Summarize communities (hierarchical)
5. Query (local or global)
```

### Cost Tradeoff (Microsoft 2024)
```
Graph building: 5-10x cost of vector RAG
Query cost: Similar to vector RAG
Break-even: ~50+ complex queries on same dataset
```

### Platform Selection
```
NetworkX: Prototyping, <10K entities
Neo4j: Production, >100K entities, persistent storage
ArangoDB: Multi-model (graph + document)
```

---

## Anti-Patterns

❌ **Using graph RAG for simple lookups**:
```python
# Bad - graph overhead not worth it
rag = GraphRAG(builder)
result = rag("What is Alice's email?", query_type="local")
# Vector RAG would be faster and cheaper
```
✅ Use vector RAG for simple queries:
```python
# Good - reserve graph for complex queries
if is_complex_query(question):
    result = graph_rag(question)
else:
    result = vector_rag(question)
```

❌ **Building graph for small datasets**:
```python
# Bad - 5 documents, graph is overkill
documents = ["doc1", "doc2", "doc3", "doc4", "doc5"]
builder.add_documents(documents)  # Expensive entity extraction
```
✅ Use graph for large datasets (>100 docs):
```python
# Good - graph valuable for 1000+ documents
if len(documents) > 100:
    use_graph_rag()
else:
    use_vector_rag()
```

❌ **Ignoring community detection cost**:
```python
# Bad - running Leiden on every query
def query(question):
    communities = detect_communities()  # Expensive!
    return answer
```
✅ Pre-compute communities:
```python
# Good - detect communities once during build
builder.add_documents(docs)
builder.detect_communities()  # Once
# ... later
rag.query(question)  # Uses pre-computed communities
```

❌ **No evaluation of reasoning paths**:
```python
# Bad - trust graph traversal blindly
result = multihop_rag(question, start_entity)
return result.answer  # Is the path correct?
```
✅ Evaluate path quality:
```python
# Good - validate reasoning paths
result = multihop_rag(question, start_entity)
judgment = judge.evaluate(result.reasoning_path, ground_truth)
if judgment.path_quality > 0.7:
    return result.answer
```

---

## Related Skills

- `dspy-rag.md` - Basic vector RAG patterns
- `hybrid-search-rag.md` - Combining vector and BM25 retrieval
- `rag-reranking-techniques.md` - Multi-stage retrieval
- `hierarchical-rag.md` - Multi-level document structures
- `database/neo4j-basics.md` - Graph database fundamentals

---

## Summary

Graph RAG excels at complex queries requiring multihop reasoning and global insights:
- **Architecture**: Entity extraction → Graph building → Community detection → Query (local/global)
- **Microsoft GraphRAG (2024)**: 72.5% comprehensiveness vs 10-20% for naive RAG (global queries)
- **Advantages**: Multihop reasoning, relationship discovery, global theme extraction, handles 1M+ token datasets
- **Limitations**: 5-10x build cost, overkill for simple lookups (PIKE-RAG findings)
- **Recent variants**: SAM-RAG (memory), ArchRAG (efficiency), LightRAG (lightweight)
- **Platforms**: NetworkX (prototyping), Neo4j (production), ArangoDB (multi-model)
- **Evaluation**: LLM-as-judge for correctness, completeness, path quality
- **Best practice**: Use graph for multihop/global queries, vector for simple lookups (hybrid approach)

Graph RAG is not a replacement for vector RAG—it's a complementary approach for specific query types.

---

**Last Updated**: 2025-10-26
**Format Version**: 1.0 (Atomic)
