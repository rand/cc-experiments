"""
Reranking module for Production RAG system

This module is called from Rust via PyO3 to rerank retrieved documents
using cross-encoder models for improved relevance.
"""

from typing import List, Tuple, Optional
from sentence_transformers import CrossEncoder
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Reranker:
    """
    Document reranker using cross-encoder models.

    Cross-encoders jointly encode the query and document,
    providing better relevance scores than bi-encoders at
    the cost of higher computational requirements.
    """

    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        device: Optional[str] = None,
    ):
        """
        Initialize the reranker.

        Args:
            model_name: HuggingFace cross-encoder model identifier
            device: Device to use ('cuda', 'cpu', or None for auto)
        """
        logger.info(f"Loading reranking model: {model_name}")
        self.model = CrossEncoder(model_name, device=device)
        self.model_name = model_name
        logger.info("Reranking model loaded successfully")

    def rerank(self, query: str, documents: List[str]) -> List[float]:
        """
        Rerank documents based on relevance to query.

        Args:
            query: Search query
            documents: List of document texts to rerank

        Returns:
            Relevance scores (higher is better)
        """
        if not documents:
            return []

        # Create query-document pairs
        pairs = [[query, doc] for doc in documents]

        # Predict relevance scores
        scores = self.model.predict(pairs, show_progress_bar=False)

        return scores.tolist()

    def rerank_with_indices(
        self, query: str, documents: List[str]
    ) -> List[Tuple[int, float]]:
        """
        Rerank documents and return sorted indices with scores.

        Args:
            query: Search query
            documents: List of document texts to rerank

        Returns:
            List of (index, score) tuples sorted by score (descending)
        """
        scores = self.rerank(query, documents)
        indexed_scores = list(enumerate(scores))
        indexed_scores.sort(key=lambda x: x[1], reverse=True)
        return indexed_scores

    def top_k(
        self, query: str, documents: List[str], k: int = 5
    ) -> List[Tuple[int, str, float]]:
        """
        Get top-k most relevant documents.

        Args:
            query: Search query
            documents: List of document texts to rerank
            k: Number of top results to return

        Returns:
            List of (index, document, score) tuples
        """
        indexed_scores = self.rerank_with_indices(query, documents)
        top_results = indexed_scores[:k]

        return [(idx, documents[idx], score) for idx, score in top_results]


# Global reranker instance (cached)
_reranker_instance: Optional[Reranker] = None


def get_reranker(
    model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
) -> Reranker:
    """
    Get or create reranker instance.

    This function caches the reranker to avoid reloading the model
    on every call from Rust.

    Args:
        model_name: HuggingFace model identifier

    Returns:
        Reranker instance
    """
    global _reranker_instance

    if _reranker_instance is None or _reranker_instance.model_name != model_name:
        _reranker_instance = Reranker(model_name=model_name)

    return _reranker_instance


# Convenience functions for direct use from Rust
def rerank_documents(
    query: str,
    documents: List[str],
    model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
) -> List[float]:
    """
    Convenience function to rerank documents.

    Args:
        query: Search query
        documents: List of document texts
        model_name: Model to use

    Returns:
        Relevance scores
    """
    reranker = get_reranker(model_name)
    return reranker.rerank(query, documents)


def get_top_k(
    query: str,
    documents: List[str],
    k: int = 5,
    model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
) -> List[Tuple[int, str, float]]:
    """
    Convenience function to get top-k documents.

    Args:
        query: Search query
        documents: List of document texts
        k: Number of results
        model_name: Model to use

    Returns:
        List of (index, document, score) tuples
    """
    reranker = get_reranker(model_name)
    return reranker.top_k(query, documents, k)


if __name__ == "__main__":
    # Test the reranker
    reranker = get_reranker()

    query = "How does Rust ensure memory safety?"
    documents = [
        "Rust uses an ownership system to manage memory automatically.",
        "Python is a dynamically typed programming language.",
        "Memory safety in Rust is enforced at compile time through the borrow checker.",
        "JavaScript runs in web browsers and on Node.js servers.",
        "The ownership model prevents data races and null pointer dereferences.",
    ]

    print(f"Query: {query}\n")

    # Rerank all documents
    scores = reranker.rerank(query, documents)
    print("Reranking scores:")
    for i, (doc, score) in enumerate(zip(documents, scores)):
        print(f"{i+1}. [{score:.3f}] {doc}")

    # Get top-3
    print("\nTop-3 documents:")
    top_results = reranker.top_k(query, documents, k=3)
    for idx, doc, score in top_results:
        print(f"[{score:.3f}] {doc}")
