"""
Embedding module for Production RAG system

This module is called from Rust via PyO3 to generate text embeddings
using sentence-transformers models.
"""

from typing import List, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Embedder:
    """
    Text embedder using sentence-transformers.

    Provides efficient embedding generation with model caching
    and batch processing support.
    """

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        normalize: bool = True,
        device: Optional[str] = None,
    ):
        """
        Initialize the embedder.

        Args:
            model_name: HuggingFace model identifier
            normalize: Whether to normalize embeddings to unit length
            device: Device to use ('cuda', 'cpu', or None for auto)
        """
        logger.info(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name, device=device)
        self.normalize = normalize
        self.model_name = model_name
        logger.info(f"Model loaded successfully. Dimension: {self.get_dimension()}")

    def embed(self, text: str) -> List[float]:
        """
        Embed a single text.

        Args:
            text: Input text to embed

        Returns:
            Embedding as list of floats
        """
        embedding = self.model.encode(
            [text],
            normalize_embeddings=self.normalize,
            show_progress_bar=False,
        )[0]
        return embedding.tolist()

    def embed_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Embed multiple texts in batches.

        Args:
            texts: List of input texts
            batch_size: Batch size for processing

        Returns:
            List of embeddings
        """
        if not texts:
            return []

        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=self.normalize,
            show_progress_bar=False,
        )
        return embeddings.tolist()

    def get_dimension(self) -> int:
        """Get embedding dimension."""
        return self.model.get_sentence_embedding_dimension()

    def get_max_length(self) -> int:
        """Get maximum sequence length."""
        return self.model.max_seq_length


# Global embedder instance (cached)
_embedder_instance: Optional[Embedder] = None


def get_embedder(
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    normalize: bool = True,
) -> Embedder:
    """
    Get or create embedder instance.

    This function caches the embedder to avoid reloading the model
    on every call from Rust.

    Args:
        model_name: HuggingFace model identifier
        normalize: Whether to normalize embeddings

    Returns:
        Embedder instance
    """
    global _embedder_instance

    if _embedder_instance is None or _embedder_instance.model_name != model_name:
        _embedder_instance = Embedder(model_name=model_name, normalize=normalize)

    return _embedder_instance


# Convenience functions for direct use from Rust
def embed_text(text: str, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> List[float]:
    """
    Convenience function to embed a single text.

    Args:
        text: Input text
        model_name: Model to use

    Returns:
        Embedding vector
    """
    embedder = get_embedder(model_name)
    return embedder.embed(text)


def embed_batch(
    texts: List[str],
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    batch_size: int = 32,
) -> List[List[float]]:
    """
    Convenience function to embed multiple texts.

    Args:
        texts: List of input texts
        model_name: Model to use
        batch_size: Batch size

    Returns:
        List of embedding vectors
    """
    embedder = get_embedder(model_name)
    return embedder.embed_batch(texts, batch_size)


if __name__ == "__main__":
    # Test the embedder
    embedder = get_embedder()

    # Single embedding
    text = "Rust is a systems programming language."
    embedding = embedder.embed(text)
    print(f"Text: {text}")
    print(f"Embedding dimension: {len(embedding)}")
    print(f"First 5 values: {embedding[:5]}")

    # Batch embedding
    texts = [
        "Rust ensures memory safety.",
        "Python is great for ML.",
        "PyO3 bridges Rust and Python.",
    ]
    embeddings = embedder.embed_batch(texts)
    print(f"\nBatch embeddings: {len(embeddings)} texts")
    print(f"Dimensions: {[len(e) for e in embeddings]}")
