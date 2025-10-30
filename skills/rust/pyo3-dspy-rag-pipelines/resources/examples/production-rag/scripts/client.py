#!/usr/bin/env python3
"""
Python client example for Production RAG API
Demonstrates how to interact with the RAG system from Python
"""

import json
import time
from typing import List, Dict, Any, Optional
import requests


class RAGClient:
    """Client for interacting with Production RAG API"""

    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    def health_check(self) -> Dict[str, Any]:
        """Check system health"""
        response = self.session.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()

    def index_documents(
        self,
        documents: List[Dict[str, Any]],
        chunk_size: int = 512,
        overlap: int = 50,
    ) -> Dict[str, Any]:
        """Index documents into the RAG system"""
        payload = {
            "documents": documents,
            "chunk_size": chunk_size,
            "overlap": overlap,
        }
        response = self.session.post(
            f"{self.base_url}/index",
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    def query(
        self,
        query: str,
        top_k: int = 5,
        rerank: bool = True,
        temperature: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Query the RAG system"""
        payload = {
            "query": query,
            "top_k": top_k,
            "rerank": rerank,
        }
        if temperature is not None:
            payload["temperature"] = temperature

        response = self.session.post(
            f"{self.base_url}/query",
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    def get_metrics(self) -> str:
        """Get Prometheus metrics"""
        response = self.session.get(f"{self.base_url}/metrics")
        response.raise_for_status()
        return response.text


def main():
    """Example usage"""
    print("Production RAG Client Example")
    print("=" * 50)

    # Initialize client
    client = RAGClient()

    # Check health
    print("\n1. Health Check")
    health = client.health_check()
    print(f"   Status: {health['status']}")
    print(f"   Components: {json.dumps(health['components'], indent=2)}")

    # Index sample documents
    print("\n2. Indexing Documents")
    documents = [
        {
            "id": "rust-memory",
            "text": """
            Rust's memory safety is achieved through its ownership system. Each value
            in Rust has a single owner, and when the owner goes out of scope, the value
            is automatically dropped. This prevents memory leaks and use-after-free bugs
            without requiring a garbage collector.
            """,
            "metadata": {"category": "memory-safety", "difficulty": "intermediate"},
        },
        {
            "id": "rust-concurrency",
            "text": """
            Rust's type system and ownership model ensure thread safety at compile time.
            The compiler prevents data races by ensuring that mutable data is not shared
            across threads unless protected by synchronization primitives like Mutex or
            RwLock. This makes concurrent programming safer and easier.
            """,
            "metadata": {"category": "concurrency", "difficulty": "advanced"},
        },
        {
            "id": "rust-performance",
            "text": """
            Rust provides zero-cost abstractions, meaning you can use high-level features
            without runtime overhead. The compiler optimizes code aggressively, often
            producing binaries as fast as or faster than equivalent C or C++ code. This
            makes Rust ideal for systems programming where performance is critical.
            """,
            "metadata": {"category": "performance", "difficulty": "beginner"},
        },
        {
            "id": "rust-ecosystem",
            "text": """
            The Rust ecosystem includes Cargo (package manager), crates.io (package
            registry), and rustfmt/clippy (formatting and linting tools). This rich
            tooling makes Rust development productive and enjoyable. The community is
            welcoming and helpful to newcomers.
            """,
            "metadata": {"category": "ecosystem", "difficulty": "beginner"},
        },
    ]

    result = client.index_documents(documents)
    print(f"   Indexed: {result['indexed']} chunks")
    print(f"   Duration: {result['duration_ms']}ms")

    # Wait for indexing to complete
    print("\n   Waiting for indexing to complete...")
    time.sleep(3)

    # Query examples
    queries = [
        ("How does Rust prevent memory leaks?", 3, True),
        ("What makes Rust good for concurrent programming?", 2, True),
        ("Tell me about Rust's performance characteristics", 3, False),
        ("What tools are available in the Rust ecosystem?", 2, True),
    ]

    print("\n3. Query Examples")
    for i, (query_text, top_k, rerank) in enumerate(queries, 1):
        print(f"\n   Query {i}: {query_text}")
        print(f"   Settings: top_k={top_k}, rerank={rerank}")

        response = client.query(
            query=query_text,
            top_k=top_k,
            rerank=rerank,
            temperature=0.7,
        )

        print(f"   Latency: {response['latency_ms']}ms")
        print(f"   Answer: {response['answer'][:200]}...")
        print(f"   Sources: {len(response['sources'])}")

        # Show top source
        if response["sources"]:
            top_source = response["sources"][0]
            print(f"   Top Source Score: {top_source['score']:.3f}")
            print(f"   Top Source: {top_source['text'][:100]}...")

    # Show metrics
    print("\n4. Metrics Sample")
    metrics = client.get_metrics()
    for line in metrics.split("\n"):
        if line.startswith("rag_") and not line.startswith("#"):
            print(f"   {line}")
            if metrics.split("\n").index(line) > 10:
                break

    print("\n" + "=" * 50)
    print("Example completed successfully!")


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to RAG API. Is the server running?")
        print("Start it with: cargo run --release")
    except Exception as e:
        print(f"Error: {e}")
        raise
