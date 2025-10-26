---
name: ir-query-understanding
description: Query expansion, spell correction, semantic search, query classification, entity recognition, and autocomplete
---

# Information Retrieval: Query Understanding

**Scope**: Query preprocessing including expansion, spell correction, semantic understanding, classification, entity recognition, and suggestions
**Lines**: ~300
**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Improving search recall through query expansion
- Handling misspelled queries with spell correction
- Understanding query intent (informational, navigational, transactional)
- Extracting entities from queries (people, places, products)
- Implementing autocomplete and query suggestions
- Bridging vocabulary gap between users and documents
- Supporting multilingual search queries
- Personalizing query interpretation based on user context

## Core Concepts

### Concept 1: Query Expansion

**Techniques**:

**Synonym Expansion**: Add related terms
- "laptop" → "laptop", "notebook", "computer"

**Pseudo-Relevance Feedback**: Use top results to expand
- Search → Get top 5 → Extract terms → Re-search

**Word Embeddings**: Add semantically similar terms
- Use word2vec, GloVe, or transformer embeddings

```python
from gensim.models import Word2Vec
import numpy as np

# Load pre-trained word embeddings
# For demo, train small model (use pre-trained in production)
sentences = [
    ["machine", "learning", "algorithms"],
    ["deep", "learning", "neural", "networks"],
    ["supervised", "learning", "classification"],
]
model = Word2Vec(sentences, vector_size=100, window=5, min_count=1)

def expand_query_embeddings(query, model, top_k=3):
    """Expand query with semantically similar terms"""
    terms = query.lower().split()
    expanded = set(terms)

    for term in terms:
        if term in model.wv:
            # Get similar words
            similar = model.wv.most_similar(term, topn=top_k)
            for word, score in similar:
                if score > 0.7:  # Threshold for similarity
                    expanded.add(word)

    return " ".join(expanded)

# Pseudo-relevance feedback
def pseudo_relevance_feedback(query, search_fn, top_k=5, expansion_terms=3):
    """Expand query using top search results"""
    # Initial search
    results = search_fn(query, limit=top_k)

    # Extract terms from top results
    from collections import Counter
    term_counts = Counter()

    for doc in results:
        # Simple tokenization (use proper NLP in production)
        terms = doc['content'].lower().split()
        term_counts.update(terms)

    # Add most common terms not in original query
    query_terms = set(query.lower().split())
    expansion = []

    for term, count in term_counts.most_common():
        if term not in query_terms and len(expansion) < expansion_terms:
            expansion.append(term)

    expanded_query = query + " " + " ".join(expansion)
    return expanded_query

# Example
original_query = "machine learning"
expanded = expand_query_embeddings(original_query, model, top_k=2)
print(f"Expanded query: {expanded}")
```

### Concept 2: Spell Correction

**Approaches**:

**Edit Distance**: Levenshtein distance to find close matches
**Context-Aware**: Use language model to pick best correction
**Search-Based**: Correct based on index terms

```python
import re
from collections import Counter

def edit_distance(s1, s2):
    """Compute Levenshtein distance"""
    if len(s1) < len(s2):
        return edit_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]

class SpellChecker:
    def __init__(self, corpus):
        """Build dictionary from corpus"""
        self.word_counts = Counter()
        for doc in corpus:
            words = re.findall(r'\w+', doc.lower())
            self.word_counts.update(words)

    def correction(self, word):
        """Find best correction for word"""
        if word in self.word_counts:
            return word

        # Generate candidates within edit distance 1-2
        candidates = self._candidates(word)

        # Return most frequent candidate
        return max(candidates, key=lambda w: self.word_counts.get(w, 0))

    def _candidates(self, word):
        """Generate candidate corrections"""
        # Known words at edit distance 0, 1, 2
        return (
            self._known([word]) or
            self._known(self._edits1(word)) or
            self._known(self._edits2(word)) or
            [word]
        )

    def _known(self, words):
        """Filter to known words"""
        return set(w for w in words if w in self.word_counts)

    def _edits1(self, word):
        """All edits 1 edit away"""
        letters = 'abcdefghijklmnopqrstuvwxyz'
        splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
        deletes = [L + R[1:] for L, R in splits if R]
        transposes = [L + R[1] + R[0] + R[2:] for L, R in splits if len(R) > 1]
        replaces = [L + c + R[1:] for L, R in splits if R for c in letters]
        inserts = [L + c + R for L, R in splits for c in letters]
        return set(deletes + transposes + replaces + inserts)

    def _edits2(self, word):
        """All edits 2 edits away"""
        return set(e2 for e1 in self._edits1(word) for e2 in self._edits1(e1))

# Example
corpus = ["machine learning algorithms", "deep learning networks", "supervised learning"]
speller = SpellChecker(corpus)

misspelled = "machne lerning"
corrected = " ".join([speller.correction(word) for word in misspelled.split()])
print(f"Corrected: {corrected}")  # "machine learning"
```

### Concept 3: Query Classification

**Intent Types**:

- **Informational**: Seeking knowledge ("what is machine learning")
- **Navigational**: Finding specific site/page ("github login")
- **Transactional**: Ready to act ("buy macbook pro")

```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

# Training data: (query, intent)
training_data = [
    ("what is machine learning", "informational"),
    ("how does neural network work", "informational"),
    ("github login", "navigational"),
    ("facebook home page", "navigational"),
    ("buy macbook pro", "transactional"),
    ("book flight to paris", "transactional"),
    ("machine learning tutorial", "informational"),
    ("amazon prime", "navigational"),
    ("order pizza online", "transactional"),
]

queries, intents = zip(*training_data)

# Train classifier
vectorizer = TfidfVectorizer()
X = vectorizer.fit_transform(queries)

classifier = LogisticRegression()
classifier.fit(X, intents)

def classify_query(query, vectorizer, classifier):
    """Classify query intent"""
    X_query = vectorizer.transform([query])
    intent = classifier.predict(X_query)[0]
    probabilities = classifier.predict_proba(X_query)[0]

    return {
        'intent': intent,
        'confidence': max(probabilities)
    }

# Example
test_query = "how to learn python"
result = classify_query(test_query, vectorizer, classifier)
print(f"Intent: {result['intent']} (confidence: {result['confidence']:.2f})")
```

### Concept 4: Entity Recognition

**Extract**: People, places, products, dates, prices from queries

```python
import re

class QueryEntityExtractor:
    def __init__(self):
        # Patterns for common entities
        self.patterns = {
            'price': r'\$?\d+(?:\.\d{2})?',
            'date': r'\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4}',
            'email': r'[\w\.-]+@[\w\.-]+\.\w+',
            'phone': r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
        }

        # Product catalog (in production, load from database)
        self.products = {'macbook', 'iphone', 'ipad', 'airpods'}
        self.brands = {'apple', 'google', 'microsoft', 'amazon'}

    def extract(self, query):
        """Extract entities from query"""
        entities = {}

        # Regex-based extraction
        for entity_type, pattern in self.patterns.items():
            matches = re.findall(pattern, query, re.IGNORECASE)
            if matches:
                entities[entity_type] = matches

        # Dictionary-based extraction
        query_lower = query.lower()
        words = set(query_lower.split())

        entities['products'] = [p for p in self.products if p in query_lower]
        entities['brands'] = [b for b in self.brands if b in words]

        return entities

# Example
extractor = QueryEntityExtractor()
query = "buy macbook pro under $2000"
entities = extractor.extract(query)
print(f"Entities: {entities}")
# {'price': ['2000'], 'products': ['macbook'], 'brands': ['apple']}
```

---

## Patterns

### Pattern 1: Autocomplete with Prefix Matching

**When to use**: Real-time query suggestions as user types

```python
class TrieNode:
    def __init__(self):
        self.children = {}
        self.is_end = False
        self.frequency = 0

class Autocomplete:
    def __init__(self):
        self.root = TrieNode()

    def insert(self, query, frequency=1):
        """Insert query into trie"""
        node = self.root
        for char in query.lower():
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]

        node.is_end = True
        node.frequency += frequency

    def search(self, prefix, max_results=5):
        """Get top suggestions for prefix"""
        # Navigate to prefix
        node = self.root
        for char in prefix.lower():
            if char not in node.children:
                return []
            node = node.children[char]

        # Collect all completions
        results = []
        self._collect_completions(node, prefix, results)

        # Sort by frequency and return top-k
        results.sort(key=lambda x: x[1], reverse=True)
        return [query for query, freq in results[:max_results]]

    def _collect_completions(self, node, current, results):
        """Recursively collect all completions"""
        if node.is_end:
            results.append((current, node.frequency))

        for char, child in node.children.items():
            self._collect_completions(child, current + char, results)

# Build autocomplete from query logs
ac = Autocomplete()
query_log = [
    ("machine learning", 100),
    ("machine learning tutorial", 50),
    ("machine learning algorithms", 30),
    ("machine vision", 20),
]

for query, freq in query_log:
    ac.insert(query, freq)

# Suggest
suggestions = ac.search("machine l", max_results=3)
print(f"Suggestions: {suggestions}")
```

### Pattern 2: Contextual Query Rewriting

**Use case**: Rewrite query based on user context or conversation

```python
def contextual_query_rewrite(query, user_context, conversation_history):
    """Rewrite query with context"""
    rewritten = query

    # Resolve pronouns using conversation history
    if any(pronoun in query.lower() for pronoun in ['it', 'this', 'that', 'he', 'she']):
        if conversation_history:
            last_entity = extract_main_entity(conversation_history[-1])
            rewritten = rewritten.replace('it', last_entity)
            rewritten = rewritten.replace('this', last_entity)

    # Add implicit location
    if user_context.get('location') and 'near' not in query.lower():
        if any(term in query.lower() for term in ['restaurant', 'hotel', 'store']):
            rewritten += f" near {user_context['location']}"

    # Add temporal context
    if user_context.get('time_period'):
        if any(term in query.lower() for term in ['news', 'events', 'weather']):
            rewritten += f" {user_context['time_period']}"

    return rewritten

# Example
context = {'location': 'San Francisco', 'time_period': 'today'}
history = ["machine learning conferences"]

query = "when is it happening"
rewritten = contextual_query_rewrite(query, context, history)
print(f"Rewritten: {rewritten}")
# "when is machine learning conferences happening"
```

### Pattern 3: Multi-Language Query Understanding

**When to use**: Support queries in multiple languages

```python
from langdetect import detect

def multilingual_query_processing(query):
    """Detect language and process accordingly"""
    try:
        lang = detect(query)
    except:
        lang = 'en'

    # Language-specific processing
    if lang == 'en':
        # English stopwords
        stopwords = {'the', 'a', 'an', 'is', 'are'}
    elif lang == 'es':
        # Spanish stopwords
        stopwords = {'el', 'la', 'los', 'las', 'es', 'son'}
    elif lang == 'zh-cn':
        # Chinese - different tokenization
        # Use jieba or similar
        stopwords = set()
    else:
        stopwords = set()

    # Process with language-specific rules
    terms = query.lower().split()
    filtered_terms = [t for t in terms if t not in stopwords]

    return {
        'language': lang,
        'processed_query': ' '.join(filtered_terms),
        'original_query': query
    }

# Example
query_en = "what is machine learning"
query_es = "qué es aprendizaje automático"

result_en = multilingual_query_processing(query_en)
result_es = multilingual_query_processing(query_es)
```

### Pattern 4: Query Segmentation

**Use case**: Break complex queries into components

```python
import re

def segment_query(query):
    """Segment query into structured components"""
    segments = {
        'what': None,    # What user is looking for
        'where': None,   # Location constraint
        'when': None,    # Time constraint
        'how': None,     # Method/manner
        'attributes': [] # Additional attributes
    }

    query_lower = query.lower()

    # Extract location
    location_pattern = r'(?:in|at|near)\s+([a-z\s]+?)(?:\s|$)'
    location_match = re.search(location_pattern, query_lower)
    if location_match:
        segments['where'] = location_match.group(1).strip()

    # Extract time
    time_keywords = ['today', 'tomorrow', 'this week', 'next month']
    for keyword in time_keywords:
        if keyword in query_lower:
            segments['when'] = keyword
            break

    # Extract main intent
    if query_lower.startswith('how'):
        segments['how'] = query
    else:
        # Remove location and time, rest is "what"
        what = query_lower
        if segments['where']:
            what = what.replace(f"in {segments['where']}", "")
            what = what.replace(f"near {segments['where']}", "")
        if segments['when']:
            what = what.replace(segments['when'], "")
        segments['what'] = what.strip()

    return segments

# Example
query = "italian restaurants in San Francisco open today"
segments = segment_query(query)
print(f"Segments: {segments}")
```

### Pattern 5: Query Relaxation

**When to use**: No results for strict query, relax constraints

```python
def relaxed_search(query, search_fn, min_results=3):
    """Progressive query relaxation if no results"""
    # Try exact query first
    results = search_fn(query)

    if len(results) >= min_results:
        return results, "exact"

    # Relaxation strategies
    strategies = [
        ('remove_quotes', lambda q: q.replace('"', '')),
        ('remove_stopwords', lambda q: remove_stopwords(q)),
        ('expand_synonyms', lambda q: expand_with_synonyms(q)),
        ('stem_terms', lambda q: stem_query(q)),
    ]

    for strategy_name, strategy_fn in strategies:
        relaxed_query = strategy_fn(query)
        results = search_fn(relaxed_query)

        if len(results) >= min_results:
            return results, strategy_name

    # Ultimate fallback: search individual terms (OR query)
    terms = query.split()
    results = search_fn(" OR ".join(terms))

    return results, "individual_terms"

def remove_stopwords(query):
    stopwords = {'the', 'a', 'an', 'is', 'are', 'in', 'on', 'at'}
    return ' '.join([w for w in query.split() if w.lower() not in stopwords])
```

---

## Quick Reference

### Query Expansion Techniques

```
Technique                | Use Case                   | Pros              | Cons
-------------------------|----------------------------|-------------------|-------------
Synonyms                 | Vocabulary mismatch        | Simple, fast      | Limited coverage
Pseudo-relevance feedback| High-quality corpus        | Domain-adaptive   | Query drift
Word embeddings          | Semantic similarity        | Broader coverage  | May add noise
User click data          | Large query logs           | User-validated    | Needs logs
```

### Intent Classification

```
Intent Type      | Indicators                       | Search Strategy
-----------------|----------------------------------|------------------
Informational    | what, how, why, definition       | Return documents, snippets
Navigational     | brand name, login, homepage      | Return direct link
Transactional    | buy, order, download, book       | Return products, CTAs
```

### Key Guidelines

```
✅ DO: Spell-check queries before search
✅ DO: Expand queries to bridge vocabulary gap
✅ DO: Classify intent to customize results
✅ DO: Extract entities for structured search
✅ DO: Suggest queries as user types (autocomplete)
✅ DO: Handle multilingual queries

❌ DON'T: Over-expand queries (query drift)
❌ DON'T: Ignore user's original terms
❌ DON'T: Auto-correct without showing original
❌ DON'T: Suggest irrelevant queries
❌ DON'T: Apply same processing to all languages
```

---

## Anti-Patterns

### Critical Violations

```python
# ❌ NEVER: Auto-correct without showing original query
def bad_search(query):
    corrected = spell_correct(query)
    return search(corrected)
    # User doesn't know query was changed

# ✅ CORRECT: Show correction, let user confirm
def good_search(query):
    corrected = spell_correct(query)
    if corrected != query:
        # Return both original and corrected results
        return {
            'original_results': search(query),
            'did_you_mean': corrected,
            'corrected_results': search(corrected)
        }
    return {'results': search(query)}
```

❌ **Silent auto-correction**: User confusion, wrong results
✅ **Correct approach**: Show "Did you mean?" with original results

### Common Mistakes

```python
# ❌ Don't: Expand query too aggressively
expanded = original_query + " " + " ".join(all_synonyms)
# Query drift: "python programming" → "python programming snake coding development"

# ✅ Correct: Selective expansion with scoring
def selective_expansion(query, synonyms, threshold=0.8):
    expanded = query
    for term in query.split():
        if term in synonyms:
            # Add only high-confidence synonyms
            for syn, score in synonyms[term]:
                if score > threshold:
                    expanded += f" {syn}"
    return expanded
```

❌ **Over-expansion**: Query drift, irrelevant results
✅ **Better**: Use confidence thresholds, limit expansion

```python
# ❌ Don't: Ignore query structure
query = "machine learning NOT deep learning"
processed = " ".join(query.split())  # Loses NOT operator

# ✅ Correct: Preserve operators
def parse_query(query):
    # Preserve boolean operators, quotes, etc.
    tokens = []
    operators = {'AND', 'OR', 'NOT'}

    for token in query.split():
        if token.upper() in operators:
            tokens.append(token.upper())
        else:
            tokens.append(token)

    return tokens
```

❌ **Destroying query structure**: Loses user intent
✅ **Better**: Respect operators, quotes, special syntax

---

## Related Skills

- `ir-search-fundamentals.md` - Use expanded queries with BM25/Elasticsearch
- `ir-vector-search.md` - Semantic query understanding with embeddings
- `ir-ranking-reranking.md` - Rank results after query understanding
- `ir-recommendation-systems.md` - Query-based recommendations
- `frontend-forms-validation.md` - Client-side query validation

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
