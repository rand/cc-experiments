#!/usr/bin/env python3
"""
DSPy Integration with Qdrant Vector Database

Demonstrates:
- Custom Qdrant retriever for DSPy
- RAG pipeline with Qdrant backend
- Embedding generation and storage
- Filtered retrieval with metadata
"""

import dspy
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import json

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        Distance,
        VectorParams,
        PointStruct,
        Filter,
        FieldCondition,
        MatchValue,
    )
except ImportError:
    print("Please install: pip install qdrant-client")
    exit(1)

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("Please install: pip install sentence-transformers")
    exit(1)


@dataclass
class Document:
    """Document with text and metadata"""

    id: str
    text: str
    metadata: Dict[str, Any]


class QdrantRM(dspy.Retrieve):
    """
    Custom Qdrant Retriever Module for DSPy

    Integrates Qdrant vector database as a retrieval module
    for DSPy pipelines with embedding generation.
    """

    def __init__(
        self,
        url: str = "http://localhost:6333",
        collection_name: str = "documents",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        api_key: Optional[str] = None,
        k: int = 3,
    ):
        """
        Initialize Qdrant retriever

        Args:
            url: Qdrant server URL
            collection_name: Collection to search
            embedding_model: SentenceTransformer model name
            api_key: Optional API key for Qdrant Cloud
            k: Number of results to retrieve
        """
        super().__init__(k=k)

        self.client = QdrantClient(url=url, api_key=api_key)
        self.collection_name = collection_name
        self.k = k

        # Initialize embedding model
        print(f"Loading embedding model: {embedding_model}")
        self.embedder = SentenceTransformer(embedding_model)
        self.vector_size = self.embedder.get_sentence_embedding_dimension()

        # Ensure collection exists
        self._ensure_collection()

    def _ensure_collection(self):
        """Create collection if it doesn't exist"""
        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)

            if not exists:
                print(f"Creating collection: {self.collection_name}")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size, distance=Distance.COSINE
                    ),
                )
        except Exception as e:
            print(f"Error ensuring collection: {e}")

    def forward(
        self, query_or_queries: str | List[str], k: Optional[int] = None
    ) -> dspy.Prediction:
        """
        Retrieve relevant passages for query

        Args:
            query_or_queries: Single query or list of queries
            k: Optional override for number of results

        Returns:
            dspy.Prediction with passages field
        """
        queries = (
            [query_or_queries]
            if isinstance(query_or_queries, str)
            else query_or_queries
        )
        limit = k or self.k

        all_passages = []

        for query in queries:
            # Generate query embedding
            query_vector = self.embedder.encode(query).tolist()

            # Search Qdrant
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit,
                with_payload=True,
            )

            # Extract passages
            passages = [
                {
                    "text": result.payload.get("text", ""),
                    "score": result.score,
                    "id": str(result.id),
                    "metadata": result.payload,
                }
                for result in results
            ]

            all_passages.extend(passages)

        return dspy.Prediction(passages=all_passages)

    def index_documents(self, documents: List[Document]) -> None:
        """
        Index documents into Qdrant

        Args:
            documents: List of Document objects to index
        """
        print(f"Indexing {len(documents)} documents...")

        # Generate embeddings
        texts = [doc.text for doc in documents]
        embeddings = self.embedder.encode(texts, show_progress_bar=True)

        # Prepare points
        points = []
        for doc, embedding in zip(documents, embeddings):
            payload = {"text": doc.text, **doc.metadata}
            points.append(
                PointStruct(id=doc.id, vector=embedding.tolist(), payload=payload)
            )

        # Upsert to Qdrant
        self.client.upsert(collection_name=self.collection_name, points=points)
        print(f"Indexed {len(points)} documents successfully")

    def search_with_filter(
        self, query: str, filters: Dict[str, Any], k: Optional[int] = None
    ) -> List[Dict]:
        """
        Search with metadata filters

        Args:
            query: Search query
            filters: Dictionary of field->value filters
            k: Number of results

        Returns:
            List of result dictionaries
        """
        limit = k or self.k

        # Generate query embedding
        query_vector = self.embedder.encode(query).tolist()

        # Build filter conditions
        conditions = [
            FieldCondition(key=key, match=MatchValue(value=value))
            for key, value in filters.items()
        ]

        filter_obj = Filter(must=conditions) if conditions else None

        # Search
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=filter_obj,
            limit=limit,
            with_payload=True,
        )

        return [
            {
                "text": result.payload.get("text", ""),
                "score": result.score,
                "id": str(result.id),
                "metadata": result.payload,
            }
            for result in results
        ]


class RAGPipeline(dspy.Module):
    """
    Retrieval Augmented Generation pipeline using Qdrant
    """

    def __init__(self, num_passages: int = 3):
        super().__init__()
        self.retrieve = dspy.Retrieve(k=num_passages)
        self.generate_answer = dspy.ChainOfThought("context, question -> answer")

    def forward(self, question: str) -> dspy.Prediction:
        """
        Generate answer using retrieved context

        Args:
            question: User question

        Returns:
            Prediction with answer and context
        """
        # Retrieve relevant passages
        context_result = self.retrieve(question)
        passages = context_result.passages

        # Format context
        context = "\n\n".join(
            [
                f"[{i+1}] {p['text']}"
                if isinstance(p, dict)
                else f"[{i+1}] {p}"
                for i, p in enumerate(passages)
            ]
        )

        # Generate answer
        answer = self.generate_answer(context=context, question=question)

        return dspy.Prediction(
            answer=answer.answer, context=passages, reasoning=getattr(answer, "reasoning", None)
        )


def example_basic_retrieval():
    """Example: Basic retrieval with Qdrant"""
    print("\n=== Basic Retrieval Example ===\n")

    # Initialize retriever
    rm = QdrantRM(
        url="http://localhost:6333",
        collection_name="demo_docs",
        k=3,
    )

    # Sample documents
    documents = [
        Document(
            id="doc1",
            text="Qdrant is a vector similarity search engine and vector database.",
            metadata={"category": "database", "source": "docs"},
        ),
        Document(
            id="doc2",
            text="Vector databases are optimized for similarity search using embeddings.",
            metadata={"category": "database", "source": "article"},
        ),
        Document(
            id="doc3",
            text="Machine learning models generate dense vector representations.",
            metadata={"category": "ml", "source": "tutorial"},
        ),
        Document(
            id="doc4",
            text="DSPy is a framework for programming with language models.",
            metadata={"category": "ml", "source": "docs"},
        ),
        Document(
            id="doc5",
            text="Retrieval augmented generation combines search with LLMs.",
            metadata={"category": "rag", "source": "research"},
        ),
    ]

    # Index documents
    rm.index_documents(documents)

    # Test retrieval
    query = "What is a vector database?"
    results = rm(query)

    print(f"Query: {query}\n")
    print("Results:")
    for i, passage in enumerate(results.passages, 1):
        print(f"\n{i}. Score: {passage['score']:.4f}")
        print(f"   Text: {passage['text']}")
        print(f"   Category: {passage['metadata'].get('category')}")


def example_filtered_search():
    """Example: Filtered search with metadata"""
    print("\n=== Filtered Search Example ===\n")

    rm = QdrantRM(url="http://localhost:6333", collection_name="demo_docs")

    # Search with category filter
    query = "Tell me about databases"
    results = rm.search_with_filter(
        query=query, filters={"category": "database"}, k=5
    )

    print(f"Query: {query}")
    print(f"Filter: category=database\n")
    print("Results:")
    for i, result in enumerate(results, 1):
        print(f"\n{i}. Score: {result['score']:.4f}")
        print(f"   Text: {result['text']}")
        print(f"   Source: {result['metadata'].get('source')}")


def example_rag_pipeline():
    """Example: Full RAG pipeline with DSPy"""
    print("\n=== RAG Pipeline Example ===\n")

    # Note: This requires OpenAI API key
    try:
        # Configure DSPy with Qdrant retriever
        lm = dspy.OpenAI(model="gpt-3.5-turbo")
        rm = QdrantRM(url="http://localhost:6333", collection_name="demo_docs", k=3)

        dspy.settings.configure(lm=lm, rm=rm)

        # Create RAG pipeline
        rag = RAGPipeline(num_passages=3)

        # Ask question
        question = "How do vector databases work with embeddings?"
        result = rag(question)

        print(f"Question: {question}\n")
        print(f"Answer: {result.answer}\n")

        if result.reasoning:
            print(f"Reasoning: {result.reasoning}\n")

        print("Retrieved Context:")
        for i, passage in enumerate(result.context, 1):
            text = passage["text"] if isinstance(passage, dict) else passage
            print(f"{i}. {text}")

    except Exception as e:
        print(f"RAG pipeline requires OpenAI API key: {e}")
        print("Set OPENAI_API_KEY environment variable to run this example")


def example_collection_stats():
    """Example: Get collection statistics"""
    print("\n=== Collection Statistics ===\n")

    client = QdrantClient(url="http://localhost:6333")
    collection_name = "demo_docs"

    try:
        # Get collection info
        info = client.get_collection(collection_name=collection_name)

        print(f"Collection: {collection_name}")
        print(f"  Status: {info.status}")
        print(f"  Points: {info.points_count}")
        print(f"  Vectors: {info.vectors_count}")
        print(f"  Vector Size: {info.config.params.vectors.size}")
        print(f"  Distance: {info.config.params.vectors.distance}")
    except Exception as e:
        print(f"Error getting collection info: {e}")


def main():
    """Run all examples"""
    print("=" * 60)
    print("Qdrant + DSPy Integration Examples")
    print("=" * 60)

    try:
        # Run examples
        example_basic_retrieval()
        example_filtered_search()
        example_collection_stats()
        example_rag_pipeline()

    except Exception as e:
        print(f"\nError running examples: {e}")
        print("\nMake sure Qdrant is running:")
        print("  docker-compose up -d")


if __name__ == "__main__":
    main()
