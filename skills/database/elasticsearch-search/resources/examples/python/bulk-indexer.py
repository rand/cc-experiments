#!/usr/bin/env python3
"""
Elasticsearch Bulk Indexer

Efficiently bulk index documents with error handling, progress tracking,
and retry logic.

Installation:
    pip install elasticsearch

Usage:
    python bulk-indexer.py --input data.json --index products
    python bulk-indexer.py --input data.jsonl --index products --batch-size 5000
"""

import argparse
import json
import sys
from typing import Iterator, Dict, Any, List
from dataclasses import dataclass
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk, parallel_bulk, streaming_bulk
import time


@dataclass
class IndexStats:
    """Indexing statistics"""
    total: int = 0
    successful: int = 0
    failed: int = 0
    start_time: float = 0
    end_time: float = 0

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time

    @property
    def docs_per_second(self) -> float:
        return self.successful / self.duration if self.duration > 0 else 0


class BulkIndexer:
    """Bulk indexing with error handling and progress tracking"""

    def __init__(self, es: Elasticsearch, index: str, batch_size: int = 1000):
        self.es = es
        self.index = index
        self.batch_size = batch_size
        self.stats = IndexStats()

    def load_documents(self, file_path: str) -> Iterator[Dict[str, Any]]:
        """Load documents from JSON or JSONL file"""
        with open(file_path, 'r') as f:
            # Try JSON array first
            try:
                data = json.load(f)
                if isinstance(data, list):
                    for doc in data:
                        yield doc
                else:
                    yield data
                return
            except json.JSONDecodeError:
                pass

            # Try JSONL format
            f.seek(0)
            for line in f:
                line = line.strip()
                if line:
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError as e:
                        print(f"Warning: Skipping invalid JSON line: {e}", file=sys.stderr)

    def generate_actions(self, documents: Iterator[Dict[str, Any]]) -> Iterator[Dict[str, Any]]:
        """Generate bulk index actions"""
        for doc in documents:
            # Extract _id if present
            doc_id = doc.pop('_id', None)

            action = {
                '_index': self.index,
                '_source': doc
            }

            if doc_id:
                action['_id'] = doc_id

            yield action

    def bulk_index_simple(self, documents: Iterator[Dict[str, Any]]) -> IndexStats:
        """Simple bulk indexing (single-threaded)"""
        self.stats = IndexStats(start_time=time.time())

        actions = list(self.generate_actions(documents))
        self.stats.total = len(actions)

        print(f"Indexing {self.stats.total} documents...")

        try:
            # Bulk index with error handling
            success, failed = bulk(
                self.es,
                actions,
                chunk_size=self.batch_size,
                raise_on_error=False,
                raise_on_exception=False,
                max_retries=3,
                initial_backoff=2
            )

            self.stats.successful = success
            self.stats.failed = len(failed) if isinstance(failed, list) else failed

        except Exception as e:
            print(f"Error during bulk indexing: {e}", file=sys.stderr)

        self.stats.end_time = time.time()
        return self.stats

    def bulk_index_streaming(self, documents: Iterator[Dict[str, Any]]) -> IndexStats:
        """Streaming bulk indexing (memory efficient)"""
        self.stats = IndexStats(start_time=time.time())

        print("Starting streaming bulk index...")

        actions = self.generate_actions(documents)

        for ok, result in streaming_bulk(
            self.es,
            actions,
            chunk_size=self.batch_size,
            raise_on_error=False,
            raise_on_exception=False,
            max_retries=3,
            initial_backoff=2
        ):
            self.stats.total += 1

            if ok:
                self.stats.successful += 1
            else:
                self.stats.failed += 1
                action, info = result.popitem()
                print(f"Failed to index: {info}", file=sys.stderr)

            # Progress indicator
            if self.stats.total % 1000 == 0:
                print(f"Indexed {self.stats.total} documents...", end='\r')

        print()  # New line after progress
        self.stats.end_time = time.time()
        return self.stats

    def bulk_index_parallel(self, documents: Iterator[Dict[str, Any]], threads: int = 4) -> IndexStats:
        """Parallel bulk indexing (faster for large datasets)"""
        self.stats = IndexStats(start_time=time.time())

        print(f"Starting parallel bulk index with {threads} threads...")

        actions = self.generate_actions(documents)

        for success, info in parallel_bulk(
            self.es,
            actions,
            chunk_size=self.batch_size,
            thread_count=threads,
            raise_on_error=False,
            raise_on_exception=False,
            max_chunk_bytes=10 * 1024 * 1024  # 10MB
        ):
            self.stats.total += 1

            if success:
                self.stats.successful += 1
            else:
                self.stats.failed += 1
                print(f"Failed to index: {info}", file=sys.stderr)

            # Progress indicator
            if self.stats.total % 1000 == 0:
                print(f"Indexed {self.stats.total} documents...", end='\r')

        print()  # New line after progress
        self.stats.end_time = time.time()
        return self.stats

    def print_stats(self, stats: IndexStats):
        """Print indexing statistics"""
        print("\n" + "="*80)
        print("INDEXING STATISTICS")
        print("="*80)
        print(f"Total Documents: {stats.total}")
        print(f"Successfully Indexed: {stats.successful}")
        print(f"Failed: {stats.failed}")
        print(f"Success Rate: {stats.successful/stats.total*100:.2f}%")
        print(f"Duration: {stats.duration:.2f}s")
        print(f"Throughput: {stats.docs_per_second:.2f} docs/sec")
        print("="*80)


def create_test_data(count: int = 1000) -> List[Dict[str, Any]]:
    """Create test documents"""
    import random
    from datetime import datetime, timedelta

    categories = ['electronics', 'books', 'clothing', 'home', 'sports']
    brands = ['Apple', 'Samsung', 'Sony', 'Dell', 'HP', 'Generic']

    documents = []
    for i in range(count):
        doc = {
            '_id': f'prod_{i:06d}',
            'name': f'Product {i}',
            'description': f'Description for product {i}',
            'category': random.choice(categories),
            'brand': random.choice(brands),
            'price': round(random.uniform(10, 2000), 2),
            'rating': round(random.uniform(1, 5), 1),
            'in_stock': random.choice([True, False]),
            'stock': random.randint(0, 100),
            'tags': random.sample(['new', 'sale', 'featured', 'bestseller'], k=random.randint(0, 3)),
            'created_at': (datetime.now() - timedelta(days=random.randint(0, 365))).isoformat()
        }
        documents.append(doc)

    return documents


def main():
    parser = argparse.ArgumentParser(
        description="Bulk index documents into Elasticsearch",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--input',
        help='Input file (JSON or JSONL format)'
    )
    parser.add_argument(
        '--index',
        required=True,
        help='Elasticsearch index name'
    )
    parser.add_argument(
        '--endpoint',
        default='http://localhost:9200',
        help='Elasticsearch endpoint (default: http://localhost:9200)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=1000,
        help='Batch size for bulk operations (default: 1000)'
    )
    parser.add_argument(
        '--method',
        choices=['simple', 'streaming', 'parallel'],
        default='streaming',
        help='Indexing method (default: streaming)'
    )
    parser.add_argument(
        '--threads',
        type=int,
        default=4,
        help='Number of threads for parallel indexing (default: 4)'
    )
    parser.add_argument(
        '--disable-refresh',
        action='store_true',
        help='Disable refresh during indexing for better performance'
    )
    parser.add_argument(
        '--generate-test-data',
        type=int,
        metavar='COUNT',
        help='Generate test data instead of reading from file'
    )

    args = parser.parse_args()

    try:
        # Connect to Elasticsearch
        es = Elasticsearch([args.endpoint])

        if not es.ping():
            print("Error: Cannot connect to Elasticsearch", file=sys.stderr)
            sys.exit(1)

        print(f"✓ Connected to Elasticsearch at {args.endpoint}")

        # Disable refresh for better indexing performance
        if args.disable_refresh:
            print("Disabling refresh interval...")
            es.indices.put_settings(
                index=args.index,
                body={"index": {"refresh_interval": "-1"}}
            )

        # Create indexer
        indexer = BulkIndexer(es, args.index, args.batch_size)

        # Load documents
        if args.generate_test_data:
            print(f"Generating {args.generate_test_data} test documents...")
            documents = iter(create_test_data(args.generate_test_data))
        elif args.input:
            print(f"Loading documents from {args.input}...")
            documents = indexer.load_documents(args.input)
        else:
            parser.error("Either --input or --generate-test-data must be specified")

        # Index documents
        if args.method == 'simple':
            stats = indexer.bulk_index_simple(documents)
        elif args.method == 'streaming':
            stats = indexer.bulk_index_streaming(documents)
        elif args.method == 'parallel':
            stats = indexer.bulk_index_parallel(documents, args.threads)

        # Re-enable refresh
        if args.disable_refresh:
            print("Re-enabling refresh...")
            es.indices.put_settings(
                index=args.index,
                body={"index": {"refresh_interval": "30s"}}
            )
            es.indices.refresh(index=args.index)

        # Print statistics
        indexer.print_stats(stats)

        # Exit with error if any failures
        sys.exit(1 if stats.failed > 0 else 0)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
