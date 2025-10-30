#!/usr/bin/env python3
"""
Embedding Cache with LRU and Redis Backend

Provides cost-effective embedding caching with:
- In-memory LRU cache for hot embeddings
- Redis backend for persistent storage
- Cache key normalization for better hit rates
- Batch operations with cache lookup
- Statistics tracking (hit rate, cost savings)
- CLI interface for common operations

Usage:
    python embedding_cache.py cache --text "query" --embedding-file emb.json
    python embedding_cache.py get --text "query"
    python embedding_cache.py warm --texts texts.txt
    python embedding_cache.py stats
    python embedding_cache.py clear --pattern "prefix:*"
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("Warning: redis package not available. Install with: pip install redis", file=sys.stderr)

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    print("Warning: numpy not available. Install with: pip install numpy", file=sys.stderr)


@dataclass
class CacheStats:
    """Statistics for cache performance tracking."""
    hits: int = 0
    misses: int = 0
    total_requests: int = 0
    total_cost_saved: float = 0.0
    total_embeddings_cached: int = 0
    cache_size_bytes: int = 0

    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        if self.total_requests == 0:
            return 0.0
        return self.hits / self.total_requests

    def to_dict(self) -> dict:
        """Convert stats to dictionary."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "total_requests": self.total_requests,
            "hit_rate": self.hit_rate(),
            "total_cost_saved": self.total_cost_saved,
            "total_embeddings_cached": self.total_embeddings_cached,
            "cache_size_mb": self.cache_size_bytes / (1024 * 1024),
        }


@dataclass
class EmbeddingConfig:
    """Configuration for embedding providers."""
    provider: str = "openai"  # openai, huggingface
    model: str = "text-embedding-3-small"
    dimension: int = 1536
    cost_per_token: float = 0.00002  # OpenAI ada-002 pricing

    @classmethod
    def openai_small(cls) -> "EmbeddingConfig":
        """OpenAI text-embedding-3-small configuration."""
        return cls(
            provider="openai",
            model="text-embedding-3-small",
            dimension=1536,
            cost_per_token=0.00002,
        )

    @classmethod
    def openai_large(cls) -> "EmbeddingConfig":
        """OpenAI text-embedding-3-large configuration."""
        return cls(
            provider="openai",
            model="text-embedding-3-large",
            dimension=3072,
            cost_per_token=0.00013,
        )

    @classmethod
    def huggingface(cls, model: str = "sentence-transformers/all-MiniLM-L6-v2") -> "EmbeddingConfig":
        """HuggingFace model configuration."""
        return cls(
            provider="huggingface",
            model=model,
            dimension=384,
            cost_per_token=0.0,  # Free for local inference
        )


class LRUCache:
    """Simple LRU cache implementation using OrderedDict."""

    def __init__(self, capacity: int = 1000):
        """Initialize LRU cache with given capacity."""
        self.capacity = capacity
        self.cache: OrderedDict = OrderedDict()

    def get(self, key: str) -> Optional[List[float]]:
        """Get value from cache, return None if not found."""
        if key not in self.cache:
            return None
        # Move to end (most recently used)
        self.cache.move_to_end(key)
        return self.cache[key]

    def put(self, key: str, value: List[float]) -> None:
        """Put value in cache, evict LRU if at capacity."""
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)  # Remove oldest

    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()

    def size(self) -> int:
        """Return number of cached items."""
        return len(self.cache)


class EmbeddingCache:
    """
    Two-tier embedding cache with LRU memory cache and Redis backend.

    Features:
    - Fast LRU in-memory cache for hot embeddings
    - Persistent Redis storage for cold embeddings
    - Text normalization for better hit rates
    - Batch operations with automatic cache lookup
    - Statistics tracking for hit rate and cost savings
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        lru_capacity: int = 1000,
        config: Optional[EmbeddingConfig] = None,
        namespace: str = "emb",
    ):
        """
        Initialize embedding cache.

        Args:
            redis_url: Redis connection URL (default: redis://localhost:6379/0)
            lru_capacity: Number of embeddings to keep in LRU cache
            config: Embedding configuration for cost tracking
            namespace: Redis key namespace prefix
        """
        self.lru = LRUCache(capacity=lru_capacity)
        self.config = config or EmbeddingConfig.openai_small()
        self.namespace = namespace
        self.stats = CacheStats()

        # Initialize Redis if available
        self.redis_client = None
        if REDIS_AVAILABLE:
            redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=False)
                self.redis_client.ping()
            except (redis.ConnectionError, redis.TimeoutError) as e:
                print(f"Warning: Could not connect to Redis: {e}", file=sys.stderr)
                self.redis_client = None

    def normalize_text(self, text: str) -> str:
        """
        Normalize text for better cache hit rates.

        - Strip whitespace
        - Lowercase
        - Collapse multiple spaces
        - Remove special characters (optional)
        """
        text = text.strip().lower()
        text = re.sub(r'\s+', ' ', text)
        return text

    def generate_cache_key(self, text: str) -> str:
        """
        Generate cache key from text.

        Uses SHA256 hash of normalized text with model prefix.
        """
        normalized = self.normalize_text(text)
        text_hash = hashlib.sha256(normalized.encode()).hexdigest()
        return f"{self.namespace}:{self.config.model}:{text_hash}"

    def get(self, text: str) -> Optional[List[float]]:
        """
        Get embedding from cache (LRU -> Redis).

        Returns None if not found in either cache tier.
        """
        self.stats.total_requests += 1
        cache_key = self.generate_cache_key(text)

        # Try LRU cache first
        embedding = self.lru.get(cache_key)
        if embedding is not None:
            self.stats.hits += 1
            return embedding

        # Try Redis backend
        if self.redis_client:
            try:
                data = self.redis_client.get(cache_key)
                if data:
                    embedding = json.loads(data)
                    # Promote to LRU cache
                    self.lru.put(cache_key, embedding)
                    self.stats.hits += 1
                    return embedding
            except (redis.RedisError, json.JSONDecodeError) as e:
                print(f"Error reading from Redis: {e}", file=sys.stderr)

        self.stats.misses += 1
        return None

    def put(self, text: str, embedding: List[float]) -> None:
        """
        Put embedding in cache (both LRU and Redis).

        Args:
            text: Original text
            embedding: Embedding vector
        """
        cache_key = self.generate_cache_key(text)

        # Store in LRU
        self.lru.put(cache_key, embedding)

        # Store in Redis
        if self.redis_client:
            try:
                data = json.dumps(embedding)
                self.redis_client.set(cache_key, data)
                self.stats.cache_size_bytes += len(data)
            except (redis.RedisError, json.JSONEncodeError) as e:
                print(f"Error writing to Redis: {e}", file=sys.stderr)

        self.stats.total_embeddings_cached += 1

        # Update cost savings (estimated)
        tokens = len(text.split())  # Rough approximation
        self.stats.total_cost_saved += tokens * self.config.cost_per_token

    def batch_get(self, texts: List[str]) -> Tuple[List[Optional[List[float]]], List[int]]:
        """
        Batch get embeddings from cache.

        Returns:
            embeddings: List of embeddings (None for cache misses)
            miss_indices: Indices of texts that were cache misses
        """
        embeddings = []
        miss_indices = []

        for i, text in enumerate(texts):
            embedding = self.get(text)
            embeddings.append(embedding)
            if embedding is None:
                miss_indices.append(i)

        return embeddings, miss_indices

    def batch_put(self, texts: List[str], embeddings: List[List[float]]) -> None:
        """
        Batch put embeddings in cache.

        Args:
            texts: List of texts
            embeddings: List of corresponding embeddings
        """
        if len(texts) != len(embeddings):
            raise ValueError("texts and embeddings must have same length")

        for text, embedding in zip(texts, embeddings):
            self.put(text, embedding)

    def clear(self, pattern: Optional[str] = None) -> int:
        """
        Clear cache entries.

        Args:
            pattern: Optional Redis key pattern (e.g., "prefix:*")

        Returns:
            Number of keys cleared
        """
        cleared = 0

        # Clear LRU
        if pattern is None:
            self.lru.clear()
            cleared += self.lru.size()

        # Clear Redis
        if self.redis_client:
            try:
                if pattern:
                    # Use SCAN for pattern matching
                    cursor = 0
                    while True:
                        cursor, keys = self.redis_client.scan(
                            cursor, match=f"{self.namespace}:{pattern}", count=100
                        )
                        if keys:
                            self.redis_client.delete(*keys)
                            cleared += len(keys)
                        if cursor == 0:
                            break
                else:
                    # Clear all keys with namespace
                    keys = list(self.redis_client.scan_iter(match=f"{self.namespace}:*"))
                    if keys:
                        self.redis_client.delete(*keys)
                        cleared += len(keys)
            except redis.RedisError as e:
                print(f"Error clearing Redis: {e}", file=sys.stderr)

        return cleared

    def get_stats(self) -> CacheStats:
        """Get current cache statistics."""
        return self.stats

    def warm_cache(self, texts: List[str], embeddings: List[List[float]]) -> None:
        """
        Pre-warm cache with embeddings.

        Useful for loading frequently-used embeddings at startup.
        """
        self.batch_put(texts, embeddings)


def load_texts_from_file(file_path: str) -> List[str]:
    """Load texts from file (one per line)."""
    texts = []
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                texts.append(line)
    return texts


def load_embedding_from_file(file_path: str) -> List[float]:
    """Load embedding vector from JSON file."""
    with open(file_path, 'r') as f:
        data = json.load(f)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and "embedding" in data:
            return data["embedding"]
        else:
            raise ValueError(f"Invalid embedding format in {file_path}")


def main():
    """CLI interface for embedding cache."""
    parser = argparse.ArgumentParser(
        description="Embedding cache with LRU and Redis backend"
    )
    parser.add_argument(
        "--redis-url",
        default=None,
        help="Redis connection URL (default: redis://localhost:6379/0)"
    )
    parser.add_argument(
        "--lru-capacity",
        type=int,
        default=1000,
        help="LRU cache capacity (default: 1000)"
    )
    parser.add_argument(
        "--model",
        default="text-embedding-3-small",
        help="Embedding model name (default: text-embedding-3-small)"
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # cache command
    cache_parser = subparsers.add_parser("cache", help="Cache an embedding")
    cache_parser.add_argument("--text", required=True, help="Text to cache")
    cache_parser.add_argument("--embedding-file", required=True, help="JSON file with embedding")

    # get command
    get_parser = subparsers.add_parser("get", help="Get embedding from cache")
    get_parser.add_argument("--text", required=True, help="Text to lookup")

    # warm command
    warm_parser = subparsers.add_parser("warm", help="Warm cache with texts")
    warm_parser.add_argument("--texts", required=True, help="File with texts (one per line)")
    warm_parser.add_argument("--embeddings", required=True, help="JSON file with embeddings array")

    # stats command
    subparsers.add_parser("stats", help="Show cache statistics")

    # clear command
    clear_parser = subparsers.add_parser("clear", help="Clear cache entries")
    clear_parser.add_argument("--pattern", help="Redis key pattern to clear (e.g., 'prefix:*')")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Initialize cache
    config = EmbeddingConfig(model=args.model)
    cache = EmbeddingCache(
        redis_url=args.redis_url,
        lru_capacity=args.lru_capacity,
        config=config,
    )

    # Execute command
    if args.command == "cache":
        embedding = load_embedding_from_file(args.embedding_file)
        cache.put(args.text, embedding)
        print(f"Cached embedding for text: {args.text[:50]}...")
        print(f"Cache key: {cache.generate_cache_key(args.text)}")

    elif args.command == "get":
        embedding = cache.get(args.text)
        if embedding:
            print(f"Found embedding (dimension: {len(embedding)})")
            print(json.dumps({"text": args.text, "embedding": embedding[:5]}))  # Show first 5 dims
        else:
            print(f"No embedding found for: {args.text}")
            return 1

    elif args.command == "warm":
        texts = load_texts_from_file(args.texts)
        with open(args.embeddings, 'r') as f:
            embeddings = json.load(f)

        if len(texts) != len(embeddings):
            print(f"Error: texts ({len(texts)}) and embeddings ({len(embeddings)}) count mismatch")
            return 1

        cache.warm_cache(texts, embeddings)
        print(f"Warmed cache with {len(texts)} embeddings")

    elif args.command == "stats":
        stats = cache.get_stats()
        print(json.dumps(stats.to_dict(), indent=2))

    elif args.command == "clear":
        cleared = cache.clear(args.pattern)
        print(f"Cleared {cleared} cache entries")

    return 0


if __name__ == "__main__":
    sys.exit(main())
