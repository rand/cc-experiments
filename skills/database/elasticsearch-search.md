---
name: database-elasticsearch-search
description: Full-text search and relevance optimization with Elasticsearch
---

# Elasticsearch Search

**Scope**: Full-text search, Query DSL, aggregations, relevance tuning, performance optimization
**Lines**: ~450
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Building full-text search functionality
- Implementing autocomplete or typeahead
- Designing faceted search with filters
- Optimizing search relevance and scoring
- Creating analytics dashboards with aggregations
- Debugging slow Elasticsearch queries
- Planning index mappings and analyzers
- Implementing search-as-you-type features
- Building recommendation systems
- Analyzing search patterns and user behavior

## Core Concepts

### Inverted Index

Elasticsearch uses **inverted indexes** for fast full-text search.

**How it works**:
```
Documents:
  Doc 1: "Elasticsearch is fast"
  Doc 2: "Elasticsearch is scalable"

Inverted Index:
  Term           → Document IDs
  elasticsearch  → [1, 2]
  fast           → [1]
  scalable       → [2]
```

**Search Process**:
1. Query analyzed → terms extracted
2. Look up terms in inverted index → get document IDs
3. Score and rank documents by relevance
4. Return top results

### Mapping and Analyzers

**Mapping** defines field types and how they're indexed.

**Text vs Keyword**:
```json
{
  "mappings": {
    "properties": {
      "title": {
        "type": "text",
        "fields": {
          "keyword": {"type": "keyword"}
        }
      }
    }
  }
}
```

- `text`: Full-text search, analyzed, tokenized
- `keyword`: Exact matching, aggregations, sorting

**Analyzer** processes text during indexing and searching:
```
Input: "The QUICK Brown Fox"
  ↓ Standard Tokenizer
["The", "QUICK", "Brown", "Fox"]
  ↓ Lowercase Filter
["the", "quick", "brown", "fox"]
  ↓ Stop Words Filter
["quick", "brown", "fox"]
```

### Query Types

**Match Query** (full-text):
```json
{
  "query": {
    "match": {
      "description": {
        "query": "gaming laptop",
        "operator": "and"
      }
    }
  }
}
```

**Term Query** (exact match):
```json
{
  "query": {
    "term": {
      "status.keyword": "published"
    }
  }
}
```

**Bool Query** (combine queries):
```json
{
  "query": {
    "bool": {
      "must": [{"match": {"title": "laptop"}}],
      "filter": [
        {"term": {"category": "electronics"}},
        {"range": {"price": {"gte": 500}}}
      ],
      "should": [{"term": {"brand": "Apple"}}],
      "must_not": [{"term": {"status": "discontinued"}}]
    }
  }
}
```

- `must`: Must match, affects score
- `filter`: Must match, no scoring (cached, faster)
- `should`: Optional, boosts score
- `must_not`: Must not match (filter)

---

## Patterns

### Pattern 1: Multi-Field Search with Boosting

**When to use**:
- Search across multiple fields (title, description, tags)
- Prioritize matches in certain fields (title > description)

```json
{
  "query": {
    "multi_match": {
      "query": "gaming laptop",
      "fields": ["title^3", "description^1.5", "tags"],
      "type": "best_fields",
      "fuzziness": "AUTO"
    }
  }
}
```

**Benefits**:
- Searches multiple fields in one query
- Field boosting (`^3`) increases relevance for title matches
- `fuzziness` handles typos
- `best_fields` uses highest-scoring field

### Pattern 2: Filtered Search (Performance)

**Use case**: Exact filters + full-text search

```json
// ❌ Bad: Everything in must (slower, scoring overhead)
{
  "query": {
    "bool": {
      "must": [
        {"match": {"description": "laptop"}},
        {"term": {"status": "published"}},
        {"range": {"price": {"gte": 500}}}
      ]
    }
  }
}

// ✅ Good: Use filter for exact matches (faster, cached)
{
  "query": {
    "bool": {
      "must": [{"match": {"description": "laptop"}}],
      "filter": [
        {"term": {"status": "published"}},
        {"range": {"price": {"gte": 500}}}
      ]
    }
  }
}
```

**Benefits**:
- Filters are cached by Elasticsearch
- No scoring overhead for exact matches
- 2-5x faster for filtered queries

### Pattern 3: Autocomplete with Completion Suggester

**Use case**: Fast typeahead suggestions

**Mapping**:
```json
{
  "mappings": {
    "properties": {
      "suggest": {
        "type": "completion",
        "contexts": [
          {"name": "category", "type": "category"}
        ]
      }
    }
  }
}
```

**Index**:
```json
{
  "name": "Gaming Laptop",
  "suggest": {
    "input": ["gaming laptop", "laptop gaming", "gaming"],
    "weight": 10,
    "contexts": {"category": "electronics"}
  }
}
```

**Query**:
```json
{
  "suggest": {
    "product_suggest": {
      "prefix": "gam",
      "completion": {
        "field": "suggest",
        "size": 10,
        "contexts": {"category": "electronics"},
        "fuzzy": {"fuzziness": "AUTO"}
      }
    }
  }
}
```

**Benefits**:
- Extremely fast (optimized data structure)
- Context-aware filtering
- Fuzzy matching for typos
- Sub-millisecond response time

### Pattern 4: Faceted Search

**Use case**: E-commerce filters (category, price, brand)

```json
{
  "query": {
    "match": {"title": "laptop"}
  },
  "aggs": {
    "categories": {
      "terms": {"field": "category.keyword", "size": 10}
    },
    "price_ranges": {
      "range": {
        "field": "price",
        "ranges": [
          {"to": 500},
          {"from": 500, "to": 1500},
          {"from": 1500}
        ]
      }
    },
    "brands": {
      "terms": {"field": "brand.keyword", "size": 20}
    }
  }
}
```

**Benefits**:
- Single query returns results + facets
- Users can refine search with filters
- Shows distribution across categories/prices

### Pattern 5: Pagination with search_after

**Use case**: Deep pagination (page 100+)

```json
// ❌ Bad: from/size for deep pagination (expensive)
GET /products/_search?from=10000&size=10

// ✅ Good: search_after (efficient, stateless)
{
  "query": {"match_all": {}},
  "size": 10,
  "sort": [
    {"created_at": "desc"},
    {"_id": "desc"}
  ],
  "search_after": ["2025-10-27T00:00:00Z", "prod_123"]
}
```

**Why search_after?**
- No deep pagination overhead
- Constant memory usage
- Scales to any page depth

**Trade-off**: Can't jump to arbitrary pages (sequential only)

### Pattern 6: Custom Scoring with function_score

**Use case**: Boost results by multiple factors

```json
{
  "query": {
    "function_score": {
      "query": {"match": {"title": "laptop"}},
      "functions": [
        {
          "filter": {"term": {"is_premium": true}},
          "weight": 2
        },
        {
          "field_value_factor": {
            "field": "rating",
            "factor": 1.5,
            "modifier": "sqrt"
          }
        },
        {
          "gauss": {
            "created_at": {
              "origin": "now",
              "scale": "30d",
              "decay": 0.5
            }
          }
        }
      ],
      "score_mode": "sum",
      "boost_mode": "multiply"
    }
  }
}
```

**Factors**:
- Premium products: 2x boost
- Rating: Square root boosting
- Recency: Decay over 30 days

### Pattern 7: Aggregations with Nested Buckets

**Use case**: Multi-level analytics

```json
{
  "size": 0,
  "aggs": {
    "categories": {
      "terms": {"field": "category.keyword"},
      "aggs": {
        "brands": {
          "terms": {"field": "brand.keyword"},
          "aggs": {
            "avg_price": {"avg": {"field": "price"}},
            "avg_rating": {"avg": {"field": "rating"}}
          }
        }
      }
    }
  }
}
```

**Result Structure**:
```
Electronics
├── Apple: avg_price: $1200, avg_rating: 4.5
├── Dell: avg_price: $800, avg_rating: 4.2
Books
├── Penguin: avg_price: $15, avg_rating: 4.7
```

### Pattern 8: Highlighting Matches

**Use case**: Show matching text snippets

```json
{
  "query": {"match": {"description": "gaming"}},
  "highlight": {
    "fields": {
      "description": {
        "fragment_size": 150,
        "number_of_fragments": 3
      }
    },
    "pre_tags": ["<mark>"],
    "post_tags": ["</mark>"]
  }
}
```

**Result**:
```json
{
  "highlight": {
    "description": [
      "High performance <mark>gaming</mark> laptop...",
      "Ideal for <mark>gaming</mark> and content creation..."
    ]
  }
}
```

---

## Quick Reference

### Query Types

```
Type              | Use Case                    | Analyzed
------------------|-----------------------------|---------
match             | Full-text search            | Yes
term              | Exact match                 | No
range             | Numeric/date ranges         | No
bool              | Combine queries             | N/A
multi_match       | Multi-field search          | Yes
prefix            | Prefix matching             | No
wildcard          | Pattern matching            | No
fuzzy             | Typo tolerance              | Yes
match_phrase      | Exact phrase                | Yes
```

### Aggregation Types

```
Type              | Purpose
------------------|----------------------------------
terms             | Group by field value
range             | Group by ranges
date_histogram    | Group by time intervals
avg/min/max/sum   | Calculate metrics
cardinality       | Unique count (approximate)
percentiles       | Distribution percentiles
top_hits          | Top documents per bucket
```

### Mapping Types

```
Type              | Use Case
------------------|----------------------------------
text              | Full-text search
keyword           | Exact match, aggregations
integer/long      | Whole numbers
float/double      | Decimals
date              | Dates/timestamps
boolean           | true/false
nested            | Array of objects
geo_point         | Lat/lon coordinates
completion        | Autocomplete
```

---

## Common Pitfalls

❌ **Using term query on text fields**
```json
{"term": {"title": "Quick"}}  // Won't match (analyzed as "quick")
```
✅ Use `match` or query `title.keyword`

❌ **Deep pagination with from/size**
```json
GET /products/_search?from=10000&size=10  // Expensive
```
✅ Use `search_after` for deep pagination

❌ **Large terms aggregations**
```json
{"aggs": {"all_users": {"terms": {"size": 100000}}}}
```
✅ Use composite aggregation or limit size

❌ **Not using filters for exact matches**
```json
{"bool": {"must": [{"term": {"status": "active"}}]}}
```
✅ Move to `filter` for caching and performance

❌ **Leading wildcards**
```json
{"wildcard": {"name": "*smith"}}  // Extremely slow
```
✅ Use reverse field + prefix or full-text search

❌ **Over-sharding**
```json
{"settings": {"number_of_shards": 100}}  // For 10GB index
```
✅ Target 10-50 GB per shard (2-3 shards for 10GB)

---

## Level 3: Resources

This skill includes Level 3 Resources (executable tools, reference materials, examples):

### Comprehensive Reference

**`resources/REFERENCE.md`** (3,500+ lines)

Deep dive covering:
- Elasticsearch architecture (nodes, shards, segments, inverted index internals)
- Complete Query DSL reference with examples (match, term, bool, nested, function_score)
- Mapping types and analyzers (text, keyword, custom analyzers, token filters)
- Full-text search patterns (relevance scoring, TF-IDF, BM25, boosting)
- Aggregations (bucket, metric, pipeline aggregations with nested examples)
- Performance optimization (query optimization, indexing strategies, shard sizing)
- Index management (aliases, reindexing, ILM, rollover)
- Common search patterns (autocomplete, fuzzy search, faceted search, geo search)
- Anti-patterns and fixes (deep pagination, mapping explosion, expensive queries)
- Production best practices (monitoring, capacity planning, security, backups)

### Executable Scripts

**`resources/scripts/analyze_queries.py`**

Analyzes Elasticsearch Query DSL queries for performance issues:
```bash
# Analyze query file
./analyze_queries.py --query-file queries.json

# Analyze single query
./analyze_queries.py --query '{"query": {"match": {"field": "value"}}}'

# JSON output
./analyze_queries.py --query-file queries.json --json

# With Elasticsearch endpoint
./analyze_queries.py --query-file queries.json --endpoint http://localhost:9200
```

Features:
- Detects expensive operations (leading wildcards, deep pagination, large aggregations)
- Identifies anti-patterns (term on text fields, missing filters, scoring overhead)
- Suggests optimizations (use filters, reduce page size, optimize aggregations)
- Scores queries (0-100) and assesses complexity (low, medium, high)
- JSON output for CI/CD integration

**`resources/scripts/optimize_indexes.py`**

Analyzes indices and provides optimization recommendations:
```bash
# Analyze single index
./optimize_indexes.py --index products --endpoint http://localhost:9200

# Analyze all indices
./optimize_indexes.py --all-indices

# JSON output
./optimize_indexes.py --index products --json
```

Features:
- Shard sizing analysis (recommends optimal shard count for data size)
- Mapping optimization (detects mapping explosion, missing multi-fields)
- Settings recommendations (refresh_interval, replicas, codecs)
- Index health score (0-100)
- Actionable implementation steps

**`resources/scripts/benchmark_search.py`**

Benchmarks query performance with statistical analysis:
```bash
# Benchmark query file
./benchmark_search.py --query-file queries.json --index products

# Custom iterations and concurrency
./benchmark_search.py --query-file queries.json --iterations 500 --concurrent-requests 10

# JSON output
./benchmark_search.py --query-file queries.json --json
```

Features:
- Measures latency (min, max, mean, median, p95, p99, stddev)
- Calculates throughput (queries/sec)
- Concurrent execution support
- Warmup iterations
- Performance assessment (excellent, good, acceptable, poor)

### Examples

**Mappings**:
- `examples/mappings/product-index.json` - Complete product index with custom analyzers, multi-fields, nested objects, completion suggester

**Queries**:
- `examples/queries/full-text-search.json` - 10+ full-text search patterns (match, multi_match, bool, fuzzy, boosting, nested, highlighting, pagination)
- `examples/queries/aggregations.json` - 12+ aggregation examples (terms, range, date_histogram, nested, pipeline, bucket_script)
- `examples/queries/autocomplete.json` - 10+ autocomplete patterns (completion suggester, match_bool_prefix, edge n-grams, phrase suggester)

**Python**:
- `examples/python/elasticsearch-client.py` - Comprehensive client examples (CRUD, search, aggregations, updates, highlighting)
- `examples/python/bulk-indexer.py` - Production-ready bulk indexer (streaming, parallel, error handling, progress tracking)

**Node.js**:
- `examples/nodejs/search-service.js` - Search service class (full-text search, autocomplete, faceted search, custom scoring, pagination)

**Docker**:
- `examples/docker/docker-compose.yml` - Single-node and multi-node Elasticsearch + Kibana setup

### Quick Start

```bash
# Start Elasticsearch + Kibana
cd resources/examples/docker && docker-compose up -d

# Analyze query performance
./resources/scripts/analyze_queries.py --query-file my-queries.json

# Get index optimization recommendations
./resources/scripts/optimize_indexes.py --index products

# Benchmark queries
./resources/scripts/benchmark_search.py --query-file queries.json --index products

# Run Python examples
cd resources/examples/python
pip install elasticsearch
python elasticsearch-client.py

# Bulk index test data
python bulk-indexer.py --generate-test-data 10000 --index products
```

---

## Related Skills

- `postgres-query-optimization.md` - Query optimization concepts applicable to Elasticsearch
- `redis-data-structures.md` - Caching Elasticsearch results
- `api-rate-limiting.md` - Rate limiting search APIs
- `database-selection.md` - When to use Elasticsearch vs other databases

---

**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)
