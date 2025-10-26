---
name: ir-search-fundamentals
description: Core information retrieval concepts including TF-IDF, BM25, inverted indexes, and Elasticsearch
---

# Information Retrieval: Search Fundamentals

**Scope**: Core IR concepts covering TF-IDF, BM25, inverted indexes, Elasticsearch/OpenSearch, and text preprocessing
**Lines**: ~340
**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Building search functionality for documents, products, or content
- Implementing full-text search with relevance ranking
- Configuring Elasticsearch or OpenSearch clusters
- Optimizing search performance and relevance
- Understanding ranking algorithms (TF-IDF, BM25)
- Designing inverted indexes for efficient retrieval
- Processing text queries and documents
- Tuning search parameters for domain-specific needs

## Core Concepts

### Concept 1: TF-IDF (Term Frequency - Inverse Document Frequency)

**Formula**: `TF-IDF(t, d) = TF(t, d) × IDF(t)`

Where:
- `TF(t, d)` = frequency of term t in document d
- `IDF(t) = log(N / df(t))` where N = total documents, df(t) = documents containing t

**Key Points**:
- Higher weight for terms frequent in document but rare in corpus
- Filters out common words naturally (high df → low IDF)
- Classic baseline for text retrieval and ranking

```python
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np

# Build TF-IDF matrix
documents = [
    "machine learning algorithms for classification",
    "deep learning neural networks",
    "classification algorithms in machine learning"
]

vectorizer = TfidfVectorizer()
tfidf_matrix = vectorizer.fit_transform(documents)

# Get feature names and scores
feature_names = vectorizer.get_feature_names_out()
doc_0_scores = tfidf_matrix[0].toarray()[0]

# Show top terms for first document
top_indices = np.argsort(doc_0_scores)[-5:][::-1]
for idx in top_indices:
    print(f"{feature_names[idx]}: {doc_0_scores[idx]:.3f}")
```

### Concept 2: BM25 (Best Match 25)

**Formula**: `BM25(q, d) = Σ IDF(qi) × (f(qi, d) × (k1 + 1)) / (f(qi, d) + k1 × (1 - b + b × |d| / avgdl))`

Where:
- `k1` = term frequency saturation (typical: 1.2-2.0)
- `b` = length normalization (typical: 0.75)
- `|d|` = document length, `avgdl` = average document length

**Key Points**:
- State-of-the-art lexical ranking (better than TF-IDF)
- Length normalization prevents bias toward long documents
- Diminishing returns for high term frequency
- Default in Elasticsearch 5.0+

```python
from elasticsearch import Elasticsearch

# BM25 is default in Elasticsearch
es = Elasticsearch(['http://localhost:9200'])

# Index with BM25 similarity (default)
index_settings = {
    "settings": {
        "number_of_shards": 1,
        "index": {
            "similarity": {
                "default": {
                    "type": "BM25",
                    "k1": 1.2,  # Term frequency saturation
                    "b": 0.75    # Length normalization
                }
            }
        }
    },
    "mappings": {
        "properties": {
            "title": {"type": "text"},
            "content": {"type": "text"}
        }
    }
}

es.indices.create(index="articles", body=index_settings)

# Search with BM25 ranking
query = {
    "query": {
        "match": {
            "content": "machine learning algorithms"
        }
    }
}

results = es.search(index="articles", body=query)
```

### Concept 3: Inverted Indexes

**Structure**: Maps terms to document IDs containing those terms

```
Term        → Postings List (doc_id, frequency, positions)
"machine"   → [(1, 2, [5, 23]), (3, 1, [15])]
"learning"  → [(1, 3, [6, 24, 45]), (2, 1, [8]), (3, 2, [16, 34])]
```

**Key Points**:
- Enables fast lookup: O(k) where k = documents with term
- Stores term positions for phrase queries
- Compressed for disk efficiency
- Updated incrementally or rebuilt periodically

```python
from collections import defaultdict

class InvertedIndex:
    def __init__(self):
        self.index = defaultdict(list)

    def add_document(self, doc_id, text):
        """Add document to index with term positions"""
        terms = text.lower().split()
        for position, term in enumerate(terms):
            # Store (doc_id, position)
            self.index[term].append((doc_id, position))

    def search(self, query_term):
        """Return documents containing query term"""
        postings = self.index[query_term.lower()]
        doc_ids = set(doc_id for doc_id, _ in postings)
        return doc_ids

    def phrase_search(self, phrase):
        """Find documents with exact phrase"""
        terms = phrase.lower().split()
        if not terms:
            return set()

        # Get postings for first term
        candidates = {}
        for doc_id, pos in self.index[terms[0]]:
            if doc_id not in candidates:
                candidates[doc_id] = []
            candidates[doc_id].append(pos)

        # Check subsequent terms at consecutive positions
        for i, term in enumerate(terms[1:], 1):
            new_candidates = {}
            for doc_id, start_pos in self.index[term]:
                if doc_id in candidates:
                    for candidate_pos in candidates[doc_id]:
                        if start_pos == candidate_pos + i:
                            if doc_id not in new_candidates:
                                new_candidates[doc_id] = []
                            new_candidates[doc_id].append(candidate_pos)
            candidates = new_candidates

        return set(candidates.keys())

# Example usage
index = InvertedIndex()
index.add_document(1, "machine learning is powerful")
index.add_document(2, "deep learning neural networks")
index.add_document(3, "machine learning algorithms")

print(index.search("learning"))  # {1, 2, 3}
print(index.phrase_search("machine learning"))  # {1, 3}
```

### Concept 4: Text Preprocessing

**Pipeline**: Raw text → Tokens → Normalized tokens → Indexed terms

**Key Steps**:
- Tokenization: split on whitespace, punctuation
- Lowercasing: normalize case
- Stop word removal: filter common words ("the", "is", "a")
- Stemming/Lemmatization: reduce to root form

```python
from elasticsearch import Elasticsearch

# Define analyzer with preprocessing
analyzer_config = {
    "settings": {
        "analysis": {
            "analyzer": {
                "custom_english": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": [
                        "lowercase",
                        "english_stop",
                        "english_stemmer"
                    ]
                }
            },
            "filter": {
                "english_stop": {
                    "type": "stop",
                    "stopwords": "_english_"
                },
                "english_stemmer": {
                    "type": "stemmer",
                    "language": "english"
                }
            }
        }
    },
    "mappings": {
        "properties": {
            "content": {
                "type": "text",
                "analyzer": "custom_english"
            }
        }
    }
}

# Test analyzer
es = Elasticsearch(['http://localhost:9200'])
result = es.indices.analyze(
    body={
        "analyzer": "custom_english",
        "text": "The machines are learning quickly"
    }
)
# Tokens: ["machin", "learn", "quick"]
```

---

## Patterns

### Pattern 1: Multi-Field Search with Boosting

**When to use**:
- Search across multiple fields (title, description, tags)
- Prioritize certain fields over others

```python
# ❌ Bad: Search single field, missing relevant results
query = {
    "query": {
        "match": {
            "content": "elasticsearch tutorial"
        }
    }
}

# ✅ Good: Search multiple fields with boosting
query = {
    "query": {
        "multi_match": {
            "query": "elasticsearch tutorial",
            "fields": [
                "title^3",      # 3x weight for title matches
                "description^2", # 2x weight for description
                "content",      # 1x weight for content
                "tags^2"        # 2x weight for tags
            ],
            "type": "best_fields"
        }
    }
}

results = es.search(index="articles", body=query)
```

**Benefits**:
- Increases recall by searching more fields
- Maintains precision via field boosting
- Surfaces most relevant results based on where matches occur

### Pattern 2: Boolean Queries with Filtering

**Use case**: Combine multiple constraints (must match, should match, must not match)

```python
# ✅ Structured boolean query with filters
query = {
    "query": {
        "bool": {
            "must": [
                {"match": {"content": "machine learning"}}
            ],
            "should": [
                {"match": {"tags": "python"}},
                {"match": {"tags": "tutorial"}}
            ],
            "filter": [
                {"range": {"publish_date": {"gte": "2023-01-01"}}},
                {"term": {"status": "published"}}
            ],
            "must_not": [
                {"term": {"category": "deprecated"}}
            ],
            "minimum_should_match": 1
        }
    }
}

results = es.search(index="articles", body=query)
```

**Benefits**:
- Filter clauses don't affect scoring (faster)
- Flexible combination of requirements
- Clean separation of relevance vs constraints

### Pattern 3: Phrase Queries for Exact Matching

**When to use**: Require exact phrase or proximity

```python
# Match exact phrase
phrase_query = {
    "query": {
        "match_phrase": {
            "content": "machine learning"
        }
    }
}

# Match terms within N positions (slop)
proximity_query = {
    "query": {
        "match_phrase": {
            "content": {
                "query": "machine learning",
                "slop": 2  # Allow up to 2 words between terms
            }
        }
    }
}

# "machine learning" matches
# "machine and deep learning" matches (slop=2)
# "machine algorithms and learning" does not match
```

### Pattern 4: Aggregations for Faceted Search

**Use case**: Show category counts, price ranges, filters

```python
# ✅ Combine search with aggregations
query = {
    "query": {
        "match": {"content": "laptop"}
    },
    "aggs": {
        "by_brand": {
            "terms": {
                "field": "brand.keyword",
                "size": 10
            }
        },
        "price_ranges": {
            "range": {
                "field": "price",
                "ranges": [
                    {"to": 500},
                    {"from": 500, "to": 1000},
                    {"from": 1000, "to": 2000},
                    {"from": 2000}
                ]
            }
        },
        "avg_rating": {
            "avg": {"field": "rating"}
        }
    }
}

results = es.search(index="products", body=query)
facets = results['aggregations']
```

### Pattern 5: Highlighting Matched Terms

**Use case**: Show users where query matches in results

```python
query = {
    "query": {
        "multi_match": {
            "query": "machine learning",
            "fields": ["title", "content"]
        }
    },
    "highlight": {
        "fields": {
            "title": {"number_of_fragments": 0},
            "content": {
                "fragment_size": 150,
                "number_of_fragments": 3,
                "pre_tags": ["<mark>"],
                "post_tags": ["</mark>"]
            }
        }
    }
}

results = es.search(index="articles", body=query)
for hit in results['hits']['hits']:
    highlights = hit.get('highlight', {})
    print(highlights.get('content', []))
```

### Pattern 6: Tuning BM25 Parameters

**When to use**: Default BM25 doesn't match domain characteristics

```python
# Short documents (tweets, titles): reduce k1
short_doc_similarity = {
    "type": "BM25",
    "k1": 0.8,  # Lower saturation (default 1.2)
    "b": 0.5    # Less length normalization
}

# Long documents (articles, books): increase k1
long_doc_similarity = {
    "type": "BM25",
    "k1": 2.0,  # Higher saturation
    "b": 0.9    # More length normalization
}

# Apply per-field
mapping = {
    "properties": {
        "title": {
            "type": "text",
            "similarity": "short_doc_sim"
        },
        "content": {
            "type": "text",
            "similarity": "long_doc_sim"
        }
    }
}
```

---

## Quick Reference

### Elasticsearch Query Types

```
Query Type        | Use Case                    | Example
------------------|-----------------------------|---------
match             | Full-text search            | {"match": {"field": "query"}}
multi_match       | Search multiple fields      | {"multi_match": {"query": "...", "fields": [...]}}
match_phrase      | Exact phrase                | {"match_phrase": {"field": "exact phrase"}}
term              | Exact value (no analysis)   | {"term": {"status": "published"}}
range             | Numeric/date ranges         | {"range": {"price": {"gte": 10, "lte": 100}}}
bool              | Combine queries             | {"bool": {"must": [...], "filter": [...]}}
```

### Key Guidelines

```
✅ DO: Use filters for non-scoring constraints (faster)
✅ DO: Boost important fields in multi_match queries
✅ DO: Analyze your data distribution before tuning BM25
✅ DO: Use match for full-text, term for exact values
✅ DO: Add stop word removal for common language text
✅ DO: Test queries with explain API to understand scoring

❌ DON'T: Use wildcards at start of term (slow: *xyz)
❌ DON'T: Return all fields if you only need a few
❌ DON'T: Use scripting in hot path (expensive)
❌ DON'T: Index without defining mappings (type guessing fails)
```

---

## Anti-Patterns

### Critical Violations

```python
# ❌ NEVER: Leading wildcard queries (full index scan)
bad_query = {
    "query": {
        "wildcard": {
            "content": "*ing"  # Scans entire index
        }
    }
}

# ✅ CORRECT: Use n-grams or suffix analysis
index_settings = {
    "settings": {
        "analysis": {
            "analyzer": {
                "suffix_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "reverse", "edge_ngram_filter", "reverse"]
                }
            },
            "filter": {
                "edge_ngram_filter": {
                    "type": "edge_ngram",
                    "min_gram": 2,
                    "max_gram": 10
                }
            }
        }
    }
}
```

❌ **Leading wildcards**: Full index scans kill performance
✅ **Correct approach**: Use n-gram analysis for substring search

### Common Mistakes

```python
# ❌ Don't: Fetch all results without pagination
bad_search = es.search(index="articles", body={"query": {"match_all": {}}})

# ✅ Correct: Use from/size or search_after for pagination
good_search = es.search(
    index="articles",
    body={"query": {"match_all": {}}},
    from_=0,
    size=20
)

# ✅ Better: Use scroll API for large result sets
results = es.search(
    index="articles",
    scroll='2m',
    size=1000,
    body={"query": {"match_all": {}}}
)
```

❌ **Unbounded queries**: Memory exhaustion, slow responses
✅ **Better**: Always paginate or use scroll API

```python
# ❌ Don't: Use analyzed fields for exact matching
bad_filter = {
    "query": {
        "match": {
            "category": "Machine Learning"  # Analyzed, might match partial
        }
    }
}

# ✅ Correct: Use keyword fields for exact values
good_filter = {
    "query": {
        "term": {
            "category.keyword": "Machine Learning"  # Exact match
        }
    }
}
```

❌ **Wrong field type**: Match vs term confusion leads to unexpected results
✅ **Better**: Use keyword fields (.keyword) for exact matching

```python
# ❌ Don't: Score-heavy queries in filters
bad_query = {
    "query": {
        "bool": {
            "must": [
                {"match": {"status": "published"}},  # Should be filter
                {"match": {"author": "John Doe"}}    # Should be filter
            ]
        }
    }
}

# ✅ Correct: Non-scoring constraints in filter context
good_query = {
    "query": {
        "bool": {
            "must": [
                {"match": {"content": "machine learning"}}
            ],
            "filter": [
                {"term": {"status": "published"}},
                {"term": {"author.keyword": "John Doe"}}
            ]
        }
    }
}
```

❌ **Scoring in filters**: Wastes CPU on scoring, slower queries
✅ **Better**: Use filter context for exact constraints

---

## Related Skills

- `ir-vector-search.md` - Semantic search using embeddings (complements lexical search)
- `ir-ranking-reranking.md` - Improve result quality with learning to rank and cross-encoders
- `ir-query-understanding.md` - Query expansion, spell correction, intent detection before retrieval
- `ir-recommendation-systems.md` - Content-based filtering uses similar IR techniques
- `ml/dspy-rag.md` - Retrieval-Augmented Generation combines search with LLMs

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
