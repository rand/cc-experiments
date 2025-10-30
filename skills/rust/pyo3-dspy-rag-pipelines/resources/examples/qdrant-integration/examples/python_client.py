#!/usr/bin/env python3
"""
Pure Python Qdrant Client Example

Demonstrates direct usage of Qdrant Python client without DSPy,
useful for understanding the underlying operations.
"""

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any
import time


class QdrantManager:
    """Production-ready Qdrant client wrapper"""

    def __init__(
        self,
        url: str = "http://localhost:6333",
        api_key: str = None,
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    ):
        """Initialize Qdrant client and embedding model"""
        self.client = QdrantClient(url=url, api_key=api_key)
        self.embedder = SentenceTransformer(embedding_model)
        self.vector_size = self.embedder.get_sentence_embedding_dimension()
        print(f"Initialized with vector size: {self.vector_size}")

    def health_check(self) -> bool:
        """Check if Qdrant is healthy"""
        try:
            health = self.client.get_collections()
            print("Qdrant health check: OK")
            return True
        except Exception as e:
            print(f"Qdrant health check failed: {e}")
            return False

    def create_collection(
        self, collection_name: str, distance: Distance = Distance.COSINE
    ) -> bool:
        """Create a new collection"""
        try:
            # Check if exists
            collections = self.client.get_collections().collections
            if any(c.name == collection_name for c in collections):
                print(f"Collection '{collection_name}' already exists")
                return True

            # Create collection
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=self.vector_size, distance=distance),
            )
            print(f"Created collection '{collection_name}'")
            return True
        except Exception as e:
            print(f"Error creating collection: {e}")
            return False

    def delete_collection(self, collection_name: str) -> bool:
        """Delete a collection"""
        try:
            self.client.delete_collection(collection_name=collection_name)
            print(f"Deleted collection '{collection_name}'")
            return True
        except Exception as e:
            print(f"Error deleting collection: {e}")
            return False

    def index_documents(
        self, collection_name: str, documents: List[Dict[str, Any]]
    ) -> bool:
        """
        Index documents with automatic embedding generation

        Args:
            collection_name: Target collection
            documents: List of dicts with 'id', 'text', and optional metadata
        """
        try:
            # Extract texts for embedding
            texts = [doc["text"] for doc in documents]

            # Generate embeddings
            print(f"Generating embeddings for {len(texts)} documents...")
            embeddings = self.embedder.encode(texts, show_progress_bar=True)

            # Prepare points
            points = []
            for doc, embedding in zip(documents, embeddings):
                payload = {k: v for k, v in doc.items() if k != "vector"}
                points.append(
                    PointStruct(
                        id=doc.get("id", hash(doc["text"])),
                        vector=embedding.tolist(),
                        payload=payload,
                    )
                )

            # Upsert to Qdrant
            self.client.upsert(collection_name=collection_name, points=points)
            print(f"Indexed {len(points)} documents")
            return True
        except Exception as e:
            print(f"Error indexing documents: {e}")
            return False

    def search(
        self,
        collection_name: str,
        query: str,
        limit: int = 5,
        filter_dict: Dict[str, Any] = None,
        score_threshold: float = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents

        Args:
            collection_name: Collection to search
            query: Search query text
            limit: Maximum results
            filter_dict: Optional metadata filters
            score_threshold: Minimum similarity score

        Returns:
            List of results with id, score, and payload
        """
        try:
            # Generate query embedding
            query_vector = self.embedder.encode(query).tolist()

            # Build filter if provided
            query_filter = None
            if filter_dict:
                conditions = [
                    FieldCondition(key=key, match=MatchValue(value=value))
                    for key, value in filter_dict.items()
                ]
                query_filter = Filter(must=conditions)

            # Search
            results = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                query_filter=query_filter,
                limit=limit,
                score_threshold=score_threshold,
                with_payload=True,
            )

            # Format results
            formatted = [
                {
                    "id": str(result.id),
                    "score": result.score,
                    "payload": result.payload,
                }
                for result in results
            ]

            return formatted
        except Exception as e:
            print(f"Error searching: {e}")
            return []

    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """Get collection statistics"""
        try:
            info = self.client.get_collection(collection_name=collection_name)
            return {
                "name": collection_name,
                "status": info.status,
                "points_count": info.points_count,
                "vectors_count": info.vectors_count,
                "vector_size": info.config.params.vectors.size,
                "distance": info.config.params.vectors.distance,
            }
        except Exception as e:
            print(f"Error getting collection info: {e}")
            return {}


def example_basic_operations():
    """Example: Basic Qdrant operations"""
    print("\n=== Basic Operations ===\n")

    # Initialize
    manager = QdrantManager()

    # Health check
    if not manager.health_check():
        print("Qdrant is not available!")
        return

    collection_name = "python_demo"

    # Create collection
    manager.create_collection(collection_name)

    # Sample documents
    documents = [
        {
            "id": "1",
            "text": "Qdrant is a vector similarity search engine.",
            "category": "database",
            "year": 2021,
        },
        {
            "id": "2",
            "text": "Vector databases store high-dimensional embeddings.",
            "category": "database",
            "year": 2022,
        },
        {
            "id": "3",
            "text": "Machine learning models create vector representations.",
            "category": "ml",
            "year": 2020,
        },
        {
            "id": "4",
            "text": "Semantic search uses embeddings for relevance.",
            "category": "search",
            "year": 2021,
        },
        {
            "id": "5",
            "text": "RAG systems combine retrieval with generation.",
            "category": "rag",
            "year": 2023,
        },
    ]

    # Index documents
    manager.index_documents(collection_name, documents)

    # Get collection info
    print("\nCollection Info:")
    info = manager.get_collection_info(collection_name)
    for key, value in info.items():
        print(f"  {key}: {value}")


def example_search():
    """Example: Various search patterns"""
    print("\n=== Search Examples ===\n")

    manager = QdrantManager()
    collection_name = "python_demo"

    # Basic search
    print("1. Basic Search:")
    results = manager.search(collection_name, "What is a vector database?", limit=3)

    for i, result in enumerate(results, 1):
        print(f"\n   Result {i}:")
        print(f"   Score: {result['score']:.4f}")
        print(f"   Text: {result['payload']['text']}")

    # Filtered search
    print("\n2. Filtered Search (category=database):")
    results = manager.search(
        collection_name, "database systems", limit=5, filter_dict={"category": "database"}
    )

    for i, result in enumerate(results, 1):
        print(f"\n   Result {i}:")
        print(f"   Score: {result['score']:.4f}")
        print(f"   Text: {result['payload']['text']}")
        print(f"   Year: {result['payload']['year']}")

    # Search with score threshold
    print("\n3. Search with Score Threshold (>= 0.8):")
    results = manager.search(
        collection_name,
        "vector similarity search",
        limit=10,
        score_threshold=0.8,
    )

    print(f"   Found {len(results)} results with score >= 0.8")
    for result in results:
        print(f"   - {result['payload']['text']} (score: {result['score']:.4f})")


def example_batch_operations():
    """Example: Batch indexing performance"""
    print("\n=== Batch Operations ===\n")

    manager = QdrantManager()
    collection_name = "batch_demo"

    # Create collection
    manager.create_collection(collection_name)

    # Generate synthetic documents
    num_docs = 100
    documents = [
        {
            "id": str(i),
            "text": f"Document {i} about topic {i % 10}",
            "topic": i % 10,
            "batch": i // 10,
        }
        for i in range(num_docs)
    ]

    # Measure indexing time
    start = time.time()
    manager.index_documents(collection_name, documents)
    duration = time.time() - start

    print(f"\nIndexed {num_docs} documents in {duration:.2f} seconds")
    print(f"Rate: {num_docs / duration:.1f} docs/second")

    # Verify
    info = manager.get_collection_info(collection_name)
    print(f"Collection contains {info['points_count']} points")

    # Cleanup
    manager.delete_collection(collection_name)


def example_metadata_filters():
    """Example: Advanced metadata filtering"""
    print("\n=== Metadata Filtering ===\n")

    manager = QdrantManager()
    collection_name = "python_demo"

    # Multiple filter conditions
    print("1. Filter by category=database:")
    results = manager.search(
        collection_name, "technology", limit=5, filter_dict={"category": "database"}
    )

    for result in results:
        print(
            f"   - {result['payload']['text']} "
            f"(category: {result['payload']['category']})"
        )

    print("\n2. Filter by year=2021:")
    results = manager.search(
        collection_name, "search technology", limit=5, filter_dict={"year": 2021}
    )

    for result in results:
        print(
            f"   - {result['payload']['text']} " f"(year: {result['payload']['year']})"
        )


def main():
    """Run all examples"""
    print("=" * 60)
    print("Qdrant Python Client Examples")
    print("=" * 60)

    try:
        example_basic_operations()
        example_search()
        example_metadata_filters()
        example_batch_operations()

        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\nError: {e}")
        print("\nMake sure Qdrant is running:")
        print("  docker-compose up -d")


if __name__ == "__main__":
    main()
