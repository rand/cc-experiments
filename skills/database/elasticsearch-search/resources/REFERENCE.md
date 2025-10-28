# Elasticsearch Search - Comprehensive Reference

**Scope**: Deep dive into Elasticsearch architecture, Query DSL, mappings, analyzers, aggregations, and optimization patterns
**Lines**: ~3,500
**Last Updated**: 2025-10-27

## Table of Contents

1. [Elasticsearch Architecture](#elasticsearch-architecture)
2. [Core Concepts](#core-concepts)
3. [Inverted Index Internals](#inverted-index-internals)
4. [Mapping Types and Analyzers](#mapping-types-and-analyzers)
5. [Query DSL Deep Dive](#query-dsl-deep-dive)
6. [Full-Text Search](#full-text-search)
7. [Aggregations](#aggregations)
8. [Search Performance Optimization](#search-performance-optimization)
9. [Indexing Strategies](#indexing-strategies)
10. [Shard Management](#shard-management)
11. [Common Search Patterns](#common-search-patterns)
12. [Anti-Patterns and Fixes](#anti-patterns-and-fixes)
13. [Production Best Practices](#production-best-practices)

---

## Elasticsearch Architecture

### Cluster Structure

```
Cluster (elasticsearch-prod)
├── Node 1 (Master-eligible, Data)
│   ├── Index: products
│   │   ├── Shard 0 (Primary)
│   │   └── Shard 2 (Replica)
│   └── Index: orders
│       └── Shard 1 (Primary)
├── Node 2 (Master-eligible, Data)
│   ├── Index: products
│   │   ├── Shard 1 (Primary)
│   │   └── Shard 0 (Replica)
│   └── Index: orders
│       └── Shard 0 (Replica)
└── Node 3 (Master, Coordinating)
    └── Routes requests
```

### Node Types

**Master Node**:
- Cluster management
- Index creation/deletion
- Shard allocation
- Not recommended for heavy query load

**Data Node**:
- Stores documents
- Executes queries
- Performs aggregations
- Most resource-intensive

**Coordinating Node**:
- Routes requests
- Merge results from data nodes
- No data storage

**Ingest Node**:
- Pre-processes documents before indexing
- Runs ingest pipelines
- Transform/enrich data

### Document Storage Flow

```
1. Client → Coordinating Node
2. Coordinating Node → Primary Shard (based on document _id hash)
3. Primary Shard → Replica Shards (replication)
4. All Shards → Acknowledge
5. Coordinating Node → Client (success)
```

### Search Query Flow

```
1. Client → Coordinating Node
2. Coordinating Node → All Shards (broadcast)
3. Each Shard → Execute query, return document IDs + scores
4. Coordinating Node → Merge/sort results (global top N)
5. Coordinating Node → Fetch full documents from shards
6. Coordinating Node → Client (results)
```

**Phases**:
- **Query Phase**: Find matching documents, score them
- **Fetch Phase**: Retrieve full document content

---

## Core Concepts

### Index

**Logical namespace** for documents. Similar to a database table.

```json
PUT /products
{
  "settings": {
    "number_of_shards": 3,
    "number_of_replicas": 2
  },
  "mappings": {
    "properties": {
      "name": {"type": "text"},
      "price": {"type": "float"},
      "category": {"type": "keyword"}
    }
  }
}
```

### Document

**JSON object** stored in an index.

```json
POST /products/_doc
{
  "name": "Laptop",
  "price": 999.99,
  "category": "Electronics",
  "description": "High-performance laptop with 16GB RAM",
  "tags": ["computer", "portable"],
  "created_at": "2025-10-27T12:00:00Z"
}
```

### Shard

**Physical unit of storage**. An index is split into shards.

- **Primary Shard**: Original shard
- **Replica Shard**: Copy of primary (for availability + read throughput)

**Shard count**:
- Cannot change after index creation (must reindex)
- Choose based on data size and query patterns

### Mapping

**Schema definition** for documents. Defines field types and analyzers.

```json
{
  "mappings": {
    "properties": {
      "title": {
        "type": "text",
        "analyzer": "english",
        "fields": {
          "keyword": {
            "type": "keyword"
          }
        }
      },
      "price": {"type": "scaled_float", "scaling_factor": 100},
      "created_at": {"type": "date"},
      "location": {"type": "geo_point"},
      "tags": {"type": "keyword"}
    }
  }
}
```

### Analyzer

**Text processing pipeline**: tokenization → filtering → normalization.

```
Input: "The QUICK Brown Fox Jumped"
     ↓ Tokenizer
Tokens: ["The", "QUICK", "Brown", "Fox", "Jumped"]
     ↓ Lowercase Filter
Tokens: ["the", "quick", "brown", "fox", "jumped"]
     ↓ Stop Words Filter
Tokens: ["quick", "brown", "fox", "jumped"]
     ↓ Stemmer
Tokens: ["quick", "brown", "fox", "jump"]
```

---

## Inverted Index Internals

### What is an Inverted Index?

Maps **terms → document IDs**.

**Example Documents**:
```
Doc 1: "Elasticsearch is fast"
Doc 2: "Elasticsearch is scalable"
Doc 3: "Fast and scalable search"
```

**Inverted Index**:
```
Term           | Document IDs | Frequency | Positions
---------------|--------------|-----------|----------
elasticsearch  | [1, 2]       | [1, 1]    | [[0], [0]]
fast           | [1, 3]       | [1, 1]    | [[2], [0]]
scalable       | [2, 3]       | [1, 1]    | [[2], [2]]
search         | [3]          | [1]       | [[3]]
```

### Index Segments

Elasticsearch uses **Lucene segments**:

```
Index
├── Segment 1 (immutable)
│   ├── Documents 1-1000
│   ├── Inverted Index
│   └── Field Data
├── Segment 2 (immutable)
│   ├── Documents 1001-2000
│   └── ...
└── In-Memory Buffer (current writes)
```

**Segment Lifecycle**:
1. Documents written to in-memory buffer
2. Buffer flushed to disk → new segment created
3. Segments merged periodically (reduce overhead)
4. Old segments deleted after merge

**Refresh Interval**:
- Default: 1 second
- Makes new documents searchable
- Trade-off: Frequent refresh = more segments = slower search

```json
PUT /my-index/_settings
{
  "index": {
    "refresh_interval": "30s"
  }
}
```

### Term Vectors

**Store term positions and offsets** for highlighting and analysis.

```json
PUT /articles
{
  "mappings": {
    "properties": {
      "content": {
        "type": "text",
        "term_vector": "with_positions_offsets_payloads"
      }
    }
  }
}
```

Options:
- `no`: No term vectors (default)
- `yes`: Term + frequency
- `with_positions`: Include term positions
- `with_offsets`: Include character offsets
- `with_positions_offsets`: Both
- `with_positions_offsets_payloads`: Everything

---

## Mapping Types and Analyzers

### Field Types

#### Text vs Keyword

**Text**: Full-text searchable, analyzed

```json
{
  "name": {
    "type": "text",
    "analyzer": "standard"
  }
}
```

Use for:
- Full-text search
- Partial matching
- Analyzed/stemmed queries

**Keyword**: Exact matching, not analyzed

```json
{
  "status": {
    "type": "keyword"
  }
}
```

Use for:
- Exact matching
- Aggregations
- Sorting
- Filtering

**Multi-field Pattern** (best of both):

```json
{
  "title": {
    "type": "text",
    "fields": {
      "keyword": {
        "type": "keyword"
      },
      "english": {
        "type": "text",
        "analyzer": "english"
      }
    }
  }
}
```

Query:
- Full-text: `title: "search query"`
- Exact: `title.keyword: "Exact Title"`
- Language-specific: `title.english: "searching"`

#### Numeric Types

```json
{
  "price": {"type": "float"},
  "quantity": {"type": "integer"},
  "big_number": {"type": "long"},
  "percentage": {"type": "scaled_float", "scaling_factor": 100}
}
```

**scaled_float**: Stores as long, scales by factor. Memory-efficient for prices.

#### Date Types

```json
{
  "created_at": {
    "type": "date",
    "format": "strict_date_optional_time||epoch_millis"
  }
}
```

Supports:
- ISO 8601: `2025-10-27T12:00:00Z`
- Epoch millis: `1730030400000`
- Custom formats: `yyyy-MM-dd HH:mm:ss`

#### Boolean

```json
{
  "is_active": {"type": "boolean"}
}
```

Values: `true`, `false`, `"true"`, `"false"`, `"yes"`, `"no"`, `"on"`, `"off"`

#### Object and Nested

**Object**: Flattened

```json
{
  "user": {
    "type": "object",
    "properties": {
      "name": {"type": "text"},
      "email": {"type": "keyword"}
    }
  }
}
```

Stored as: `user.name`, `user.email`

**Nested**: Maintains object relationships

```json
{
  "comments": {
    "type": "nested",
    "properties": {
      "author": {"type": "keyword"},
      "text": {"type": "text"}
    }
  }
}
```

**Why nested?**

```json
Document: {
  "comments": [
    {"author": "Alice", "text": "Great!"},
    {"author": "Bob", "text": "Terrible!"}
  ]
}

# Object query (WRONG - matches document):
"author": "Alice" AND "text": "Terrible"

# Nested query (CORRECT - no match):
"nested": {"path": "comments", "query": {"bool": {"must": [
  {"term": {"comments.author": "Alice"}},
  {"match": {"comments.text": "Terrible"}}
]}}}
```

#### Geo Types

**Geo Point**:

```json
{
  "location": {"type": "geo_point"}
}

// Document
{
  "location": {"lat": 40.7128, "lon": -74.0060}
}
```

**Geo Shape**:

```json
{
  "area": {"type": "geo_shape"}
}

// Document
{
  "area": {
    "type": "polygon",
    "coordinates": [[[lon1, lat1], [lon2, lat2], ...]]
  }
}
```

### Analyzers

#### Built-in Analyzers

**Standard** (default):
- Tokenizer: Standard tokenizer (Unicode text segmentation)
- Filters: Lowercase

```
Input: "The Quick BROWN Fox"
Output: ["the", "quick", "brown", "fox"]
```

**Simple**:
- Tokenizer: Non-letter characters
- Filters: Lowercase

```
Input: "The Quick-Brown Fox's"
Output: ["the", "quick", "brown", "fox", "s"]
```

**Whitespace**:
- Tokenizer: Whitespace
- Filters: None

```
Input: "The Quick BROWN"
Output: ["The", "Quick", "BROWN"]
```

**Keyword**:
- No tokenization (entire string as token)

```
Input: "New York City"
Output: ["New York City"]
```

**Language Analyzers** (e.g., `english`):
- Tokenizer: Standard
- Filters: Lowercase, stop words, stemmer

```
Input: "running quickly"
Output: ["run", "quick"]  // Stemmed
```

#### Custom Analyzers

```json
PUT /my-index
{
  "settings": {
    "analysis": {
      "analyzer": {
        "my_custom_analyzer": {
          "type": "custom",
          "tokenizer": "standard",
          "filter": ["lowercase", "asciifolding", "my_stop", "my_synonym"]
        }
      },
      "filter": {
        "my_stop": {
          "type": "stop",
          "stopwords": ["the", "is", "at"]
        },
        "my_synonym": {
          "type": "synonym",
          "synonyms": ["quick,fast", "laptop,computer"]
        }
      }
    }
  }
}
```

#### Analyzer Testing

```json
POST /_analyze
{
  "analyzer": "standard",
  "text": "The Quick Brown Fox Jumped"
}

// Response:
{
  "tokens": [
    {"token": "the", "start_offset": 0, "end_offset": 3},
    {"token": "quick", "start_offset": 4, "end_offset": 9},
    {"token": "brown", "start_offset": 10, "end_offset": 15},
    {"token": "fox", "start_offset": 16, "end_offset": 19},
    {"token": "jumped", "start_offset": 20, "end_offset": 26}
  ]
}
```

---

## Query DSL Deep Dive

### Query Context vs Filter Context

**Query Context**: Relevance scoring (how well does document match?)

```json
{
  "query": {
    "match": {
      "title": "elasticsearch"
    }
  }
}
```

Returns `_score` (relevance).

**Filter Context**: Boolean yes/no (does document match?)

```json
{
  "query": {
    "bool": {
      "filter": [
        {"term": {"status": "published"}},
        {"range": {"price": {"gte": 10}}}
      ]
    }
  }
}
```

No scoring, cacheable, faster.

### Full-Text Queries

#### Match Query

**Standard full-text search**. Analyzes input, finds matching documents.

```json
GET /products/_search
{
  "query": {
    "match": {
      "description": {
        "query": "fast laptop",
        "operator": "and"
      }
    }
  }
}
```

Options:
- `operator`: `or` (default) or `and`
- `minimum_should_match`: `"75%"` (at least 75% terms must match)
- `fuzziness`: `"AUTO"` (typo tolerance)
- `analyzer`: Override default analyzer

#### Match Phrase Query

**Exact phrase matching** (terms in order).

```json
{
  "query": {
    "match_phrase": {
      "description": {
        "query": "high performance laptop",
        "slop": 1
      }
    }
  }
}
```

`slop`: How far apart terms can be.
- `slop: 0`: Exact phrase
- `slop: 1`: One word gap allowed

Example:
- Query: "quick fox" (slop: 1)
- Matches: "quick brown fox" (1 word between)

#### Multi-Match Query

**Search across multiple fields**.

```json
{
  "query": {
    "multi_match": {
      "query": "laptop",
      "fields": ["title^3", "description", "tags"],
      "type": "best_fields"
    }
  }
}
```

Options:
- `fields`: Field list with boosts (`^3` = 3x weight)
- `type`:
  - `best_fields`: Use highest scoring field (default)
  - `most_fields`: Combine scores from all fields
  - `cross_fields`: Treat fields as one big field
  - `phrase`: Match phrase across fields
  - `phrase_prefix`: Phrase prefix across fields

#### Match Bool Prefix Query

**Prefix search** on last term.

```json
{
  "query": {
    "match_bool_prefix": {
      "title": "quick bro"
    }
  }
}
```

Matches: "quick brown", "quick bronze", etc.

Use for: Autocomplete

### Term-Level Queries

#### Term Query

**Exact term matching** (no analysis).

```json
{
  "query": {
    "term": {
      "status": "published"
    }
  }
}
```

Use on: `keyword`, `numeric`, `date`, `boolean` fields.

**Warning**: Don't use on `text` fields (analyzed differently).

```json
// WRONG (on text field)
{"term": {"title": "Quick"}}  // Won't match (indexed as "quick")

// RIGHT (on text field)
{"match": {"title": "Quick"}}  // Will match (analyzed to "quick")

// RIGHT (on keyword field)
{"term": {"title.keyword": "Quick Brown Fox"}}  // Exact match
```

#### Terms Query

**Match any of multiple terms**.

```json
{
  "query": {
    "terms": {
      "status": ["published", "draft", "pending"]
    }
  }
}
```

#### Range Query

**Range matching**.

```json
{
  "query": {
    "range": {
      "price": {
        "gte": 10,
        "lte": 100
      }
    }
  }
}
```

Operators:
- `gt`: Greater than
- `gte`: Greater than or equal
- `lt`: Less than
- `lte`: Less than or equal

**Date ranges**:

```json
{
  "range": {
    "created_at": {
      "gte": "2025-01-01",
      "lt": "2025-12-31",
      "format": "yyyy-MM-dd"
    }
  }
}
```

**Date math**:

```json
{
  "range": {
    "created_at": {
      "gte": "now-7d/d",
      "lte": "now/d"
    }
  }
}
```

- `now`: Current time
- `-7d`: Minus 7 days
- `/d`: Round to day

#### Exists Query

**Check field existence**.

```json
{
  "query": {
    "exists": {
      "field": "email"
    }
  }
}
```

#### Prefix Query

**Prefix matching**.

```json
{
  "query": {
    "prefix": {
      "username": "john"
    }
  }
}
```

Matches: "john", "johnny", "johnson"

**Warning**: Expensive on large datasets (scans all terms).

#### Wildcard Query

**Pattern matching**.

```json
{
  "query": {
    "wildcard": {
      "username": "joh*son"
    }
  }
}
```

- `*`: Any characters
- `?`: Single character

**Warning**: Very expensive, avoid leading wildcards (`*son`).

#### Fuzzy Query

**Typo tolerance**.

```json
{
  "query": {
    "fuzzy": {
      "username": {
        "value": "jhon",
        "fuzziness": "AUTO"
      }
    }
  }
}
```

`fuzziness`:
- `AUTO`: 0-2 edits based on term length
- `0`, `1`, `2`: Fixed edit distance

Matches: "john" (1 edit: h ↔ o)

### Compound Queries

#### Bool Query

**Combine multiple queries**.

```json
{
  "query": {
    "bool": {
      "must": [
        {"match": {"title": "elasticsearch"}}
      ],
      "filter": [
        {"term": {"status": "published"}},
        {"range": {"price": {"gte": 10}}}
      ],
      "should": [
        {"match": {"description": "fast"}},
        {"match": {"description": "scalable"}}
      ],
      "must_not": [
        {"term": {"category": "deprecated"}}
      ],
      "minimum_should_match": 1
    }
  }
}
```

Clauses:
- `must`: Must match (affects score)
- `filter`: Must match (no score, cached)
- `should`: Should match (boosts score)
- `must_not`: Must not match (filter, cached)

**Performance tip**: Use `filter` for exact matches, `must` for relevance.

#### Boosting Query

**Decrease score for certain matches**.

```json
{
  "query": {
    "boosting": {
      "positive": {
        "match": {"title": "laptop"}
      },
      "negative": {
        "match": {"description": "refurbished"}
      },
      "negative_boost": 0.5
    }
  }
}
```

Reduces score by 50% for refurbished laptops.

#### Constant Score Query

**Fixed score** (no relevance calculation).

```json
{
  "query": {
    "constant_score": {
      "filter": {
        "term": {"status": "published"}
      },
      "boost": 1.0
    }
  }
}
```

All matches get same score (faster).

### Nested Query

**Query nested objects**.

```json
{
  "query": {
    "nested": {
      "path": "comments",
      "query": {
        "bool": {
          "must": [
            {"match": {"comments.author": "Alice"}},
            {"match": {"comments.text": "Great"}}
          ]
        }
      },
      "score_mode": "avg"
    }
  }
}
```

`score_mode`:
- `avg`: Average score of matches
- `max`: Maximum score
- `sum`: Sum of scores
- `none`: No scoring (filter mode)

---

## Full-Text Search

### Relevance Scoring

**TF-IDF** (Term Frequency-Inverse Document Frequency):

```
score = TF × IDF × field_norm

TF (Term Frequency):
  - How often term appears in document
  - More occurrences = higher score

IDF (Inverse Document Frequency):
  - How rare term is across all documents
  - Rare terms = higher score

field_norm:
  - Shorter fields = higher score
```

**BM25** (default since ES 5.0):

Improved TF-IDF with diminishing returns for term frequency.

```
score = IDF × (TF × (k1 + 1)) / (TF + k1 × (1 - b + b × (field_length / avg_field_length)))
```

Parameters:
- `k1`: Term frequency saturation (default: 1.2)
- `b`: Field length normalization (default: 0.75)

### Boosting

**Field-level boost**:

```json
{
  "query": {
    "multi_match": {
      "query": "laptop",
      "fields": ["title^3", "description^1.5", "tags"]
    }
  }
}
```

`title` matches get 3x score, `description` 1.5x.

**Query-level boost**:

```json
{
  "query": {
    "bool": {
      "should": [
        {"match": {"title": {"query": "laptop", "boost": 3}}},
        {"match": {"description": "laptop"}}
      ]
    }
  }
}
```

**Function Score Query** (complex boosting):

```json
{
  "query": {
    "function_score": {
      "query": {"match": {"title": "laptop"}},
      "functions": [
        {
          "filter": {"match": {"category": "premium"}},
          "weight": 2
        },
        {
          "field_value_factor": {
            "field": "popularity",
            "factor": 1.2,
            "modifier": "log1p"
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
      "boost_mode": "multiply",
      "score_mode": "sum"
    }
  }
}
```

Functions:
- `weight`: Fixed boost
- `field_value_factor`: Boost by field value
- `gauss`: Decay function (time-based, distance-based)
- `random_score`: Randomize results

### Highlighting

**Highlight matching terms**.

```json
{
  "query": {"match": {"content": "elasticsearch"}},
  "highlight": {
    "fields": {
      "content": {
        "fragment_size": 150,
        "number_of_fragments": 3,
        "pre_tags": ["<mark>"],
        "post_tags": ["</mark>"]
      }
    }
  }
}
```

Response:

```json
{
  "hits": [{
    "_source": {"content": "...full text..."},
    "highlight": {
      "content": [
        "...text with <mark>elasticsearch</mark> highlighted...",
        "...another fragment with <mark>elasticsearch</mark>..."
      ]
    }
  }]
}
```

### Suggesters

#### Term Suggester (typo correction)

```json
{
  "suggest": {
    "my-suggestion": {
      "text": "elasticsarch",
      "term": {
        "field": "content"
      }
    }
  }
}
```

Suggests: "elasticsearch"

#### Phrase Suggester (phrase correction)

```json
{
  "suggest": {
    "my-suggestion": {
      "text": "elastc serch",
      "phrase": {
        "field": "content"
      }
    }
  }
}
```

Suggests: "elastic search"

#### Completion Suggester (autocomplete)

**Mapping**:

```json
{
  "mappings": {
    "properties": {
      "suggest": {
        "type": "completion"
      }
    }
  }
}
```

**Index**:

```json
{
  "suggest": {
    "input": ["elasticsearch", "elastic search", "es"],
    "weight": 10
  }
}
```

**Query**:

```json
{
  "suggest": {
    "my-suggest": {
      "prefix": "elas",
      "completion": {
        "field": "suggest"
      }
    }
  }
}
```

---

## Aggregations

### Bucket Aggregations

**Group documents into buckets**.

#### Terms Aggregation

**Group by field value**.

```json
{
  "aggs": {
    "categories": {
      "terms": {
        "field": "category.keyword",
        "size": 10
      }
    }
  }
}
```

Response:

```json
{
  "aggregations": {
    "categories": {
      "buckets": [
        {"key": "Electronics", "doc_count": 1234},
        {"key": "Books", "doc_count": 987},
        ...
      ]
    }
  }
}
```

#### Range Aggregation

**Group by ranges**.

```json
{
  "aggs": {
    "price_ranges": {
      "range": {
        "field": "price",
        "ranges": [
          {"to": 50},
          {"from": 50, "to": 100},
          {"from": 100, "to": 500},
          {"from": 500}
        ]
      }
    }
  }
}
```

#### Date Histogram Aggregation

**Group by time intervals**.

```json
{
  "aggs": {
    "sales_over_time": {
      "date_histogram": {
        "field": "created_at",
        "calendar_interval": "month"
      }
    }
  }
}
```

Intervals:
- `calendar_interval`: `minute`, `hour`, `day`, `week`, `month`, `quarter`, `year`
- `fixed_interval`: `30s`, `1h`, `7d`

#### Histogram Aggregation

**Group by numeric intervals**.

```json
{
  "aggs": {
    "price_distribution": {
      "histogram": {
        "field": "price",
        "interval": 50
      }
    }
  }
}
```

Buckets: 0-50, 50-100, 100-150, ...

#### Filters Aggregation

**Multiple named filters**.

```json
{
  "aggs": {
    "status_breakdown": {
      "filters": {
        "filters": {
          "active": {"term": {"status": "active"}},
          "inactive": {"term": {"status": "inactive"}},
          "pending": {"term": {"status": "pending"}}
        }
      }
    }
  }
}
```

### Metric Aggregations

**Calculate metrics**.

#### Basic Metrics

```json
{
  "aggs": {
    "avg_price": {"avg": {"field": "price"}},
    "min_price": {"min": {"field": "price"}},
    "max_price": {"max": {"field": "price"}},
    "sum_revenue": {"sum": {"field": "revenue"}},
    "doc_count": {"value_count": {"field": "price"}}
  }
}
```

#### Stats Aggregation

**All basic stats at once**.

```json
{
  "aggs": {
    "price_stats": {
      "stats": {"field": "price"}
    }
  }
}
```

Returns: `count`, `min`, `max`, `avg`, `sum`

#### Extended Stats

**Includes variance, std_deviation**.

```json
{
  "aggs": {
    "price_extended_stats": {
      "extended_stats": {"field": "price"}
    }
  }
}
```

#### Percentiles

**Distribution percentiles**.

```json
{
  "aggs": {
    "load_time_percentiles": {
      "percentiles": {
        "field": "load_time",
        "percents": [50, 95, 99]
      }
    }
  }
}
```

Response: `{"50.0": 123, "95.0": 456, "99.0": 789}`

#### Cardinality

**Approximate unique count**.

```json
{
  "aggs": {
    "unique_users": {
      "cardinality": {"field": "user_id"}
    }
  }
}
```

Uses HyperLogLog (approximate, memory-efficient).

### Nested Aggregations

**Aggregations within aggregations**.

```json
{
  "aggs": {
    "categories": {
      "terms": {"field": "category.keyword"},
      "aggs": {
        "avg_price": {"avg": {"field": "price"}},
        "price_ranges": {
          "range": {
            "field": "price",
            "ranges": [
              {"to": 50},
              {"from": 50, "to": 100},
              {"from": 100}
            ]
          },
          "aggs": {
            "total_revenue": {"sum": {"field": "revenue"}}
          }
        }
      }
    }
  }
}
```

Result structure:
```
categories (buckets)
├── Electronics
│   ├── avg_price: 250
│   └── price_ranges (buckets)
│       ├── 0-50: total_revenue: 5000
│       ├── 50-100: total_revenue: 8000
│       └── 100+: total_revenue: 20000
└── Books
    └── ...
```

### Pipeline Aggregations

**Aggregate on aggregation results**.

#### Bucket Script

**Calculate from bucket metrics**.

```json
{
  "aggs": {
    "sales_per_month": {
      "date_histogram": {
        "field": "date",
        "calendar_interval": "month"
      },
      "aggs": {
        "total_sales": {"sum": {"field": "amount"}},
        "transaction_count": {"value_count": {"field": "amount"}},
        "avg_transaction": {
          "bucket_script": {
            "buckets_path": {
              "sales": "total_sales",
              "count": "transaction_count"
            },
            "script": "params.sales / params.count"
          }
        }
      }
    }
  }
}
```

#### Moving Average

**Time-series smoothing**.

```json
{
  "aggs": {
    "sales_per_day": {
      "date_histogram": {
        "field": "date",
        "calendar_interval": "day"
      },
      "aggs": {
        "daily_sales": {"sum": {"field": "amount"}},
        "sales_moving_avg": {
          "moving_avg": {
            "buckets_path": "daily_sales",
            "window": 7,
            "model": "simple"
          }
        }
      }
    }
  }
}
```

#### Derivative

**Rate of change**.

```json
{
  "aggs": {
    "sales_per_month": {
      "date_histogram": {
        "field": "date",
        "calendar_interval": "month"
      },
      "aggs": {
        "total_sales": {"sum": {"field": "amount"}},
        "sales_derivative": {
          "derivative": {
            "buckets_path": "total_sales"
          }
        }
      }
    }
  }
}
```

---

## Search Performance Optimization

### Query Optimization

#### Use Filter Context

**Filters are cached and faster**.

```json
// Slow (query context)
{
  "query": {
    "bool": {
      "must": [
        {"match": {"title": "laptop"}},
        {"term": {"status": "published"}},
        {"range": {"price": {"gte": 100}}}
      ]
    }
  }
}

// Fast (filter context for exact matches)
{
  "query": {
    "bool": {
      "must": [
        {"match": {"title": "laptop"}}
      ],
      "filter": [
        {"term": {"status": "published"}},
        {"range": {"price": {"gte": 100}}}
      ]
    }
  }
}
```

#### Avoid Deep Pagination

**Deep pagination is expensive**.

```json
// Expensive (page 1000)
GET /products/_search?from=10000&size=10

// Better: Use search_after
GET /products/_search
{
  "size": 10,
  "sort": [{"_id": "asc"}],
  "search_after": ["last_document_id"]
}
```

**Why?**
- `from + size`: Coordinator must collect and sort (from + size) documents from each shard
- Page 1000 with size 10 = 10,010 documents per shard sorted and discarded

**search_after**:
- Stateless cursor
- No deep pagination overhead
- Must provide sort values

#### Use Index Sorting

**Pre-sort index for common queries**.

```json
PUT /products
{
  "settings": {
    "index": {
      "sort.field": ["category.keyword", "price"],
      "sort.order": ["asc", "desc"]
    }
  }
}
```

Benefits:
- Faster sorting on these fields
- Early termination for top N queries

#### Disable _source for Large Documents

**If you only need specific fields**.

```json
GET /logs/_search
{
  "query": {"match_all": {}},
  "_source": false,
  "stored_fields": ["@timestamp", "level", "message"]
}
```

Or use docvalue_fields:

```json
{
  "query": {"match_all": {}},
  "_source": false,
  "docvalue_fields": ["@timestamp", "level", "message"]
}
```

#### Limit Result Fields

**Only retrieve needed fields**.

```json
GET /products/_search
{
  "query": {"match": {"title": "laptop"}},
  "_source": ["title", "price", "category"]
}
```

### Indexing Optimization

#### Bulk Indexing

**Batch documents for efficiency**.

```json
POST /_bulk
{"index": {"_index": "products", "_id": "1"}}
{"title": "Laptop", "price": 999}
{"index": {"_index": "products", "_id": "2"}}
{"title": "Mouse", "price": 29}
{"update": {"_index": "products", "_id": "3"}}
{"doc": {"price": 799}}
{"delete": {"_index": "products", "_id": "4"}}
```

Best practices:
- Batch size: 1000-5000 documents or 5-15MB
- Use client libraries (handle retries, backoff)
- Disable refresh during bulk load

#### Disable Refresh During Bulk Load

```json
PUT /products/_settings
{
  "index": {
    "refresh_interval": "-1"
  }
}

// ... bulk index ...

POST /products/_refresh

PUT /products/_settings
{
  "index": {
    "refresh_interval": "30s"
  }
}
```

#### Increase Refresh Interval

**For high write throughput**.

```json
PUT /products/_settings
{
  "index": {
    "refresh_interval": "30s"
  }
}
```

Default: `1s` (real-time search)
Higher values: Better indexing performance, slower search visibility

#### Replica Shards During Indexing

**Disable replicas during initial bulk load**.

```json
PUT /products/_settings
{
  "index": {
    "number_of_replicas": 0
  }
}

// ... bulk index ...

PUT /products/_settings
{
  "index": {
    "number_of_replicas": 1
  }
}
```

#### Use Auto-Generated IDs

**Faster than custom IDs**.

```json
// Faster (auto-generated ID)
POST /products/_doc
{"title": "Laptop"}

// Slower (custom ID - requires version check)
PUT /products/_doc/custom-id-123
{"title": "Laptop"}
```

---

## Indexing Strategies

### Index Aliases

**Logical names for indices**.

```json
POST /_aliases
{
  "actions": [
    {"add": {"index": "products-v1", "alias": "products"}},
    {"add": {"index": "products-v2", "alias": "products-latest"}}
  ]
}
```

Use cases:
- Zero-downtime reindexing
- Blue-green deployments
- Multiple indices for single alias (search across all)

**Atomic Alias Swap**:

```json
POST /_aliases
{
  "actions": [
    {"remove": {"index": "products-v1", "alias": "products"}},
    {"add": {"index": "products-v2", "alias": "products"}}
  ]
}
```

### Reindexing

**Copy documents to new index**.

```json
POST /_reindex
{
  "source": {
    "index": "products-old"
  },
  "dest": {
    "index": "products-new"
  }
}
```

**With query filter**:

```json
POST /_reindex
{
  "source": {
    "index": "products",
    "query": {
      "range": {
        "created_at": {"gte": "2025-01-01"}
      }
    }
  },
  "dest": {
    "index": "products-2025"
  }
}
```

**Remote reindex**:

```json
POST /_reindex
{
  "source": {
    "remote": {
      "host": "https://other-cluster:9200",
      "username": "user",
      "password": "pass"
    },
    "index": "products"
  },
  "dest": {
    "index": "products"
  }
}
```

### Index Templates

**Auto-apply settings to new indices**.

```json
PUT /_index_template/logs_template
{
  "index_patterns": ["logs-*"],
  "template": {
    "settings": {
      "number_of_shards": 3,
      "number_of_replicas": 1,
      "refresh_interval": "10s"
    },
    "mappings": {
      "properties": {
        "@timestamp": {"type": "date"},
        "message": {"type": "text"},
        "level": {"type": "keyword"}
      }
    }
  }
}
```

New indices matching `logs-*` automatically get these settings.

### Index Lifecycle Management (ILM)

**Automate index lifecycle**.

```json
PUT /_ilm/policy/logs_policy
{
  "policy": {
    "phases": {
      "hot": {
        "actions": {
          "rollover": {
            "max_size": "50GB",
            "max_age": "7d"
          }
        }
      },
      "warm": {
        "min_age": "7d",
        "actions": {
          "shrink": {"number_of_shards": 1},
          "forcemerge": {"max_num_segments": 1}
        }
      },
      "cold": {
        "min_age": "30d",
        "actions": {
          "freeze": {}
        }
      },
      "delete": {
        "min_age": "90d",
        "actions": {
          "delete": {}
        }
      }
    }
  }
}
```

Phases:
- **Hot**: Active indexing and queries (fast hardware)
- **Warm**: No writes, infrequent queries (cheaper hardware)
- **Cold**: Rarely queried (archive storage)
- **Delete**: Remove index

### Rollover

**Create new index when criteria met**.

```json
POST /logs-000001/_rollover
{
  "conditions": {
    "max_age": "7d",
    "max_docs": 1000000,
    "max_size": "50gb"
  }
}
```

Creates `logs-000002` if any condition met.

---

## Shard Management

### Choosing Shard Count

**Guidelines**:

```
Shard size: 10-50 GB (optimal)
Max shard size: 50 GB (recommended limit)
Shards per node: 20-25 per GB heap

Example:
- 500 GB index
- Target: 25 GB per shard
- Shards: 500 / 25 = 20 shards
```

**Over-sharding problems**:
- More overhead (each shard = Lucene index)
- Slower queries (more shard coordination)
- More heap memory usage

**Under-sharding problems**:
- Large shards (slow recovery, rebalancing)
- Cannot distribute across nodes
- Hot spots (uneven load)

### Shard Allocation Awareness

**Distribute shards across zones**.

```yaml
# elasticsearch.yml
cluster.routing.allocation.awareness.attributes: zone
node.attr.zone: zone-a
```

Elasticsearch ensures replicas in different zones.

### Shard Allocation Filtering

**Control shard placement**.

```json
PUT /products/_settings
{
  "index.routing.allocation.include._tier": "data_hot",
  "index.routing.allocation.exclude._name": "node-3"
}
```

### Split Index

**Increase shard count** (new index created).

```json
POST /products/_split/products-split
{
  "settings": {
    "index.number_of_shards": 6
  }
}
```

Requirements:
- Source index must be read-only
- Target shard count must be multiple of source

### Shrink Index

**Reduce shard count** (new index created).

```json
POST /products/_shrink/products-shrink
{
  "settings": {
    "index.number_of_shards": 1
  }
}
```

Requirements:
- Source index must be read-only
- All shards must be on single node
- Target shard count must divide source count

---

## Common Search Patterns

### Autocomplete

**Completion Suggester** (fastest):

```json
// Mapping
{
  "mappings": {
    "properties": {
      "suggest": {
        "type": "completion"
      }
    }
  }
}

// Index
{"suggest": ["Elasticsearch Guide", "Elasticsearch Tutorial"]}

// Query
{
  "suggest": {
    "product-suggest": {
      "prefix": "elas",
      "completion": {
        "field": "suggest",
        "size": 5
      }
    }
  }
}
```

**Match Bool Prefix** (more flexible):

```json
{
  "query": {
    "match_bool_prefix": {
      "title": {
        "query": "elas tut"
      }
    }
  }
}
```

**Edge N-Grams** (most flexible):

```json
// Mapping
{
  "settings": {
    "analysis": {
      "analyzer": {
        "autocomplete": {
          "tokenizer": "autocomplete_tokenizer",
          "filter": ["lowercase"]
        }
      },
      "tokenizer": {
        "autocomplete_tokenizer": {
          "type": "edge_ngram",
          "min_gram": 2,
          "max_gram": 10,
          "token_chars": ["letter", "digit"]
        }
      }
    }
  },
  "mappings": {
    "properties": {
      "title": {
        "type": "text",
        "analyzer": "autocomplete",
        "search_analyzer": "standard"
      }
    }
  }
}

// Query
{"match": {"title": "elas"}}
```

### Fuzzy Search

**Typo tolerance**.

```json
{
  "query": {
    "match": {
      "title": {
        "query": "elasticsarch",
        "fuzziness": "AUTO"
      }
    }
  }
}
```

Matches: "elasticsearch"

### Faceted Search

**Category + facets (aggregations)**.

```json
{
  "query": {
    "bool": {
      "filter": [
        {"term": {"category": "electronics"}},
        {"range": {"price": {"gte": 100, "lte": 500}}}
      ]
    }
  },
  "aggs": {
    "categories": {
      "terms": {"field": "category.keyword"}
    },
    "price_ranges": {
      "range": {
        "field": "price",
        "ranges": [
          {"to": 100},
          {"from": 100, "to": 500},
          {"from": 500}
        ]
      }
    },
    "brands": {
      "terms": {"field": "brand.keyword"}
    }
  }
}
```

### Geo Search

**Geo distance**:

```json
{
  "query": {
    "bool": {
      "filter": {
        "geo_distance": {
          "distance": "10km",
          "location": {
            "lat": 40.7128,
            "lon": -74.0060
          }
        }
      }
    }
  }
}
```

**Geo bounding box**:

```json
{
  "query": {
    "bool": {
      "filter": {
        "geo_bounding_box": {
          "location": {
            "top_left": {"lat": 40.8, "lon": -74.1},
            "bottom_right": {"lat": 40.6, "lon": -73.9}
          }
        }
      }
    }
  }
}
```

**Geo shape**:

```json
{
  "query": {
    "bool": {
      "filter": {
        "geo_shape": {
          "area": {
            "shape": {
              "type": "polygon",
              "coordinates": [[[lon1, lat1], [lon2, lat2], ...]]
            },
            "relation": "within"
          }
        }
      }
    }
  }
}
```

### Multi-Language Search

**Per-language analyzers**.

```json
{
  "mappings": {
    "properties": {
      "title": {
        "type": "text",
        "fields": {
          "english": {
            "type": "text",
            "analyzer": "english"
          },
          "spanish": {
            "type": "text",
            "analyzer": "spanish"
          },
          "french": {
            "type": "text",
            "analyzer": "french"
          }
        }
      }
    }
  }
}

// Query based on user language
{
  "query": {
    "match": {
      "title.spanish": "búsqueda"
    }
  }
}
```

---

## Anti-Patterns and Fixes

### Anti-Pattern 1: Using Wildcards at Start

```json
// SLOW
{
  "query": {
    "wildcard": {
      "username": "*smith"
    }
  }
}

// BETTER: Reverse field + prefix
// Index with reversed username: "htims"
{
  "query": {
    "prefix": {
      "username_reversed": "htims"
    }
  }
}
```

### Anti-Pattern 2: Deep Pagination

```json
// SLOW (page 1000)
GET /products/_search?from=10000&size=10

// BETTER: search_after
{
  "size": 10,
  "sort": [{"_id": "asc"}],
  "search_after": ["last_id"]
}
```

### Anti-Pattern 3: Mapping Explosion

```json
// BAD: Dynamic mapping with high cardinality
{
  "user_12345_name": "Alice",
  "user_67890_name": "Bob"
}
// Creates thousands of fields

// GOOD: Nested or flattened
{
  "users": [
    {"id": "12345", "name": "Alice"},
    {"id": "67890", "name": "Bob"}
  ]
}
```

### Anti-Pattern 4: Expensive Aggregations

```json
// SLOW: High cardinality terms agg
{
  "aggs": {
    "all_users": {
      "terms": {"field": "user_id", "size": 100000}
    }
  }
}

// BETTER: Composite aggregation (paginated)
{
  "aggs": {
    "users_page": {
      "composite": {
        "size": 1000,
        "sources": [
          {"user_id": {"terms": {"field": "user_id"}}}
        ]
      }
    }
  }
}
```

### Anti-Pattern 5: Not Using Filters

```json
// SLOW: Everything in must (scoring)
{
  "query": {
    "bool": {
      "must": [
        {"term": {"status": "published"}},
        {"range": {"price": {"gte": 10}}}
      ]
    }
  }
}

// FAST: Use filters (cached, no scoring)
{
  "query": {
    "bool": {
      "filter": [
        {"term": {"status": "published"}},
        {"range": {"price": {"gte": 10}}}
      ]
    }
  }
}
```

### Anti-Pattern 6: Over-Sharding

```json
// BAD: 500 shards for 50 GB index
{
  "settings": {
    "number_of_shards": 500
  }
}

// GOOD: 2-3 shards for 50 GB
{
  "settings": {
    "number_of_shards": 2
  }
}
```

### Anti-Pattern 7: Querying Analyzed Fields with Term

```json
// WRONG: term query on text field
{
  "query": {
    "term": {
      "title": "Quick Brown Fox"
    }
  }
}
// Won't match (indexed as "quick", "brown", "fox")

// RIGHT: Use match or keyword field
{
  "query": {
    "match": {"title": "Quick Brown Fox"}
  }
}
// OR
{
  "query": {
    "term": {"title.keyword": "Quick Brown Fox"}
  }
}
```

---

## Production Best Practices

### Monitoring

**Key metrics**:

```bash
# Cluster health
GET /_cluster/health

# Node stats
GET /_nodes/stats

# Index stats
GET /products/_stats

# Hot threads (performance issues)
GET /_nodes/hot_threads
```

**Watch for**:
- Cluster status: `red` (data loss), `yellow` (unassigned replicas)
- JVM heap: >75% sustained = problem
- Query latency: p95, p99 percentiles
- Indexing rate: docs/sec
- Search rate: queries/sec
- Rejected threads: Sign of overload

### Capacity Planning

**Heap sizing**:
- Max 32 GB (compressed pointers limit)
- 50% of RAM (rest for OS file cache)
- Typical: 16-32 GB per node

**Disk**:
- Use SSDs for hot data
- Plan for 15-20% overhead (merges, snapshots)
- Monitor disk usage: Keep below 85%

**Shards per node**:
- Rule of thumb: 20 shards per GB heap
- 64 GB heap = ~1,200 shards max

### Security

**Enable security**:

```yaml
# elasticsearch.yml
xpack.security.enabled: true
xpack.security.transport.ssl.enabled: true
xpack.security.http.ssl.enabled: true
```

**Role-based access**:

```json
POST /_security/role/readonly
{
  "indices": [
    {
      "names": ["products"],
      "privileges": ["read"]
    }
  ]
}
```

### Backups

**Snapshot repository**:

```json
PUT /_snapshot/my_backup
{
  "type": "fs",
  "settings": {
    "location": "/mnt/backups/elasticsearch"
  }
}
```

**Create snapshot**:

```json
PUT /_snapshot/my_backup/snapshot_1
{
  "indices": "products,orders",
  "include_global_state": false
}
```

**Restore**:

```json
POST /_snapshot/my_backup/snapshot_1/_restore
{
  "indices": "products"
}
```

### Circuit Breakers

**Prevent OOM errors**.

```yaml
# elasticsearch.yml
indices.breaker.total.limit: 70%
indices.breaker.fielddata.limit: 40%
indices.breaker.request.limit: 40%
```

### Rate Limiting

**Search throttling** (prevent abuse):

```json
PUT /products/_settings
{
  "index": {
    "search.slowlog.threshold.query.warn": "10s",
    "search.slowlog.threshold.query.info": "5s"
  }
}
```

**Use application-level rate limiting** (e.g., API gateway).

---

## Quick Reference

### Mapping Types

```
Type          | Use Case
--------------|------------------------------------------
text          | Full-text search (analyzed)
keyword       | Exact match, aggregations, sorting
integer/long  | Whole numbers
float/double  | Decimals
scaled_float  | Fixed decimals (e.g., prices)
date          | Dates/timestamps
boolean       | true/false
object        | JSON object (flattened)
nested        | Array of objects (maintains relationships)
geo_point     | Lat/lon coordinates
geo_shape     | Geographic shapes
ip            | IPv4/IPv6 addresses
completion    | Autocomplete suggestions
```

### Query Types

```
Query            | Context | Use Case
-----------------|---------|---------------------------
match            | Query   | Full-text search
term             | Filter  | Exact match (keyword, number, date)
range            | Filter  | Numeric/date ranges
bool             | Both    | Combine queries (must, filter, should, must_not)
prefix           | Filter  | Prefix matching
wildcard         | Filter  | Pattern matching (expensive)
fuzzy            | Query   | Typo tolerance
match_phrase     | Query   | Exact phrase
multi_match      | Query   | Search multiple fields
nested           | Both    | Query nested objects
geo_distance     | Filter  | Geo proximity
exists           | Filter  | Field existence
```

### Aggregation Types

```
Type              | Purpose
------------------|---------------------------
terms             | Group by field value
range             | Group by ranges
date_histogram    | Group by time intervals
histogram         | Group by numeric intervals
filters           | Named filter groups
avg/min/max/sum   | Basic metrics
stats             | All basic stats
percentiles       | Distribution percentiles
cardinality       | Unique count (approx)
bucket_script     | Calculate from metrics
moving_avg        | Time-series smoothing
```

### Performance Checklist

```
Query Performance:
[ ] Use filter context for exact matches
[ ] Avoid deep pagination (use search_after)
[ ] Limit result size and fields
[ ] Use index sorting for common queries
[ ] Prefer keyword fields for aggregations
[ ] Avoid leading wildcards
[ ] Use query caching (filter context)
[ ] Tune refresh_interval for write-heavy workloads

Indexing Performance:
[ ] Use bulk API (1000-5000 docs per batch)
[ ] Disable refresh during bulk load
[ ] Reduce replica count during initial load
[ ] Use auto-generated IDs
[ ] Increase refresh_interval
[ ] Disable unnecessary features (_source, doc_values)

Shard Management:
[ ] Target 10-50 GB per shard
[ ] Avoid over-sharding (20-25 shards per GB heap)
[ ] Use ILM for time-series data
[ ] Enable shard allocation awareness
[ ] Monitor shard distribution
```

---

**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)
