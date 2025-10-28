#!/usr/bin/env python3
"""
Elasticsearch Python Client Examples

Demonstrates common search patterns using the official elasticsearch-py client.

Installation:
    pip install elasticsearch

Usage:
    python elasticsearch-client.py
"""

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from datetime import datetime
import json


def create_client():
    """Create Elasticsearch client"""
    # Basic connection
    es = Elasticsearch(
        ["http://localhost:9200"],
        basic_auth=("elastic", "password"),  # If security enabled
        verify_certs=False  # For development only
    )

    # Check connection
    if es.ping():
        print("✓ Connected to Elasticsearch")
    else:
        raise Exception("Cannot connect to Elasticsearch")

    return es


def create_index(es):
    """Create index with mappings"""
    mapping = {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 1
        },
        "mappings": {
            "properties": {
                "title": {
                    "type": "text",
                    "fields": {"keyword": {"type": "keyword"}}
                },
                "description": {"type": "text"},
                "price": {"type": "float"},
                "category": {"type": "keyword"},
                "tags": {"type": "keyword"},
                "created_at": {"type": "date"},
                "rating": {"type": "float"}
            }
        }
    }

    index_name = "products"

    # Delete if exists (for demo)
    if es.indices.exists(index=index_name):
        es.indices.delete(index=index_name)

    # Create index
    es.indices.create(index=index_name, body=mapping)
    print(f"✓ Created index: {index_name}")


def index_documents(es):
    """Index sample documents"""
    products = [
        {
            "_index": "products",
            "_id": "1",
            "_source": {
                "title": "Gaming Laptop",
                "description": "High performance gaming laptop with RTX graphics",
                "price": 1499.99,
                "category": "electronics",
                "tags": ["laptop", "gaming", "computer"],
                "created_at": "2025-10-27T10:00:00",
                "rating": 4.5
            }
        },
        {
            "_index": "products",
            "_id": "2",
            "_source": {
                "title": "Wireless Mouse",
                "description": "Ergonomic wireless mouse with precision tracking",
                "price": 29.99,
                "category": "accessories",
                "tags": ["mouse", "wireless", "computer"],
                "created_at": "2025-10-26T10:00:00",
                "rating": 4.2
            }
        },
        {
            "_index": "products",
            "_id": "3",
            "_source": {
                "title": "Mechanical Keyboard",
                "description": "RGB mechanical keyboard with blue switches",
                "price": 129.99,
                "category": "accessories",
                "tags": ["keyboard", "mechanical", "gaming"],
                "created_at": "2025-10-25T10:00:00",
                "rating": 4.8
            }
        }
    ]

    # Bulk index
    success, failed = bulk(es, products)
    print(f"✓ Indexed {success} documents")

    # Refresh index to make documents searchable immediately
    es.indices.refresh(index="products")


def search_examples(es):
    """Demonstrate various search patterns"""

    print("\n" + "="*80)
    print("SEARCH EXAMPLES")
    print("="*80)

    # 1. Simple match query
    print("\n1. Simple match query:")
    result = es.search(
        index="products",
        body={
            "query": {
                "match": {"description": "gaming"}
            }
        }
    )
    print_results(result)

    # 2. Multi-field search
    print("\n2. Multi-field search:")
    result = es.search(
        index="products",
        body={
            "query": {
                "multi_match": {
                    "query": "gaming",
                    "fields": ["title^2", "description", "tags"]
                }
            }
        }
    )
    print_results(result)

    # 3. Bool query with filters
    print("\n3. Bool query with filters:")
    result = es.search(
        index="products",
        body={
            "query": {
                "bool": {
                    "must": [
                        {"match": {"description": "gaming"}}
                    ],
                    "filter": [
                        {"range": {"price": {"gte": 100}}},
                        {"term": {"category": "electronics"}}
                    ]
                }
            }
        }
    )
    print_results(result)

    # 4. Aggregations
    print("\n4. Aggregations (category breakdown):")
    result = es.search(
        index="products",
        body={
            "size": 0,
            "aggs": {
                "categories": {
                    "terms": {"field": "category"},
                    "aggs": {
                        "avg_price": {"avg": {"field": "price"}},
                        "avg_rating": {"avg": {"field": "rating"}}
                    }
                }
            }
        }
    )
    print_aggregations(result)

    # 5. Range query
    print("\n5. Range query (price between $20 and $150):")
    result = es.search(
        index="products",
        body={
            "query": {
                "range": {
                    "price": {"gte": 20, "lte": 150}
                }
            }
        }
    )
    print_results(result)

    # 6. Sorted search
    print("\n6. Sorted by price (descending):")
    result = es.search(
        index="products",
        body={
            "query": {"match_all": {}},
            "sort": [{"price": "desc"}]
        }
    )
    print_results(result)

    # 7. Search with highlighting
    print("\n7. Search with highlighting:")
    result = es.search(
        index="products",
        body={
            "query": {"match": {"description": "gaming"}},
            "highlight": {
                "fields": {
                    "description": {}
                }
            }
        }
    )
    print_highlighted_results(result)


def update_document(es):
    """Update document"""
    print("\n" + "="*80)
    print("UPDATE DOCUMENT")
    print("="*80)

    # Update by ID
    es.update(
        index="products",
        id="1",
        body={
            "doc": {
                "price": 1399.99,
                "rating": 4.7
            }
        }
    )
    print("✓ Updated document 1")

    # Update by query
    es.update_by_query(
        index="products",
        body={
            "script": {
                "source": "ctx._source.price = ctx._source.price * 0.9",
                "lang": "painless"
            },
            "query": {
                "term": {"category": "accessories"}
            }
        }
    )
    print("✓ Applied 10% discount to all accessories")


def delete_operations(es):
    """Delete operations"""
    print("\n" + "="*80)
    print("DELETE OPERATIONS")
    print("="*80)

    # Delete by ID
    es.delete(index="products", id="2")
    print("✓ Deleted document 2")

    # Delete by query
    es.delete_by_query(
        index="products",
        body={
            "query": {
                "range": {"price": {"lt": 50}}
            }
        }
    )
    print("✓ Deleted products with price < $50")


def print_results(result):
    """Print search results"""
    hits = result["hits"]["hits"]
    total = result["hits"]["total"]["value"]
    took = result["took"]

    print(f"Found {total} results in {took}ms")
    for hit in hits:
        source = hit["_source"]
        score = hit["_score"]
        print(f"  [{score:.2f}] {source['title']} - ${source['price']}")


def print_aggregations(result):
    """Print aggregation results"""
    if "aggregations" not in result:
        return

    categories = result["aggregations"]["categories"]["buckets"]
    print(f"Found {len(categories)} categories:")
    for bucket in categories:
        category = bucket["key"]
        count = bucket["doc_count"]
        avg_price = bucket["avg_price"]["value"]
        avg_rating = bucket["avg_rating"]["value"]
        print(f"  {category}: {count} products, avg price: ${avg_price:.2f}, avg rating: {avg_rating:.2f}")


def print_highlighted_results(result):
    """Print results with highlighting"""
    hits = result["hits"]["hits"]
    for hit in hits:
        source = hit["_source"]
        print(f"  {source['title']}")
        if "highlight" in hit:
            for field, highlights in hit["highlight"].items():
                print(f"    {field}: {highlights[0]}")


def main():
    """Run all examples"""
    try:
        # Connect
        es = create_client()

        # Create index
        create_index(es)

        # Index documents
        index_documents(es)

        # Search examples
        search_examples(es)

        # Update operations
        update_document(es)

        # Refresh to see updates
        es.indices.refresh(index="products")

        # Delete operations
        delete_operations(es)

        print("\n✓ All examples completed successfully!")

    except Exception as e:
        print(f"✗ Error: {e}")


if __name__ == "__main__":
    main()
