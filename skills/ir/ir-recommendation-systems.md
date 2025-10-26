---
name: ir-recommendation-systems
description: Collaborative filtering, content-based filtering, hybrid recommenders, matrix factorization, and cold start solutions
---

# Information Retrieval: Recommendation Systems

**Scope**: Collaborative filtering (user/item-based, matrix factorization), content-based filtering, hybrid approaches, neural collaborative filtering, and cold start handling
**Lines**: ~380
**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Building product, content, or user recommendations
- Implementing collaborative filtering (user-user or item-item)
- Using matrix factorization techniques (SVD, ALS)
- Combining content features with behavioral data (hybrid)
- Solving cold start problems for new users or items
- Evaluating recommendation quality offline and online
- Personalizing content feeds or search results
- Increasing user engagement through relevant suggestions

## Core Concepts

### Concept 1: Collaborative Filtering

**User-Based**: Recommend items liked by similar users
**Item-Based**: Recommend items similar to what user liked
**Matrix Factorization**: Decompose user-item matrix into latent factors

```python
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# User-Item matrix (rows=users, cols=items, values=ratings)
ratings = np.array([
    [5, 3, 0, 1],  # User 0
    [4, 0, 0, 1],  # User 1
    [1, 1, 0, 5],  # User 2
    [1, 0, 0, 4],  # User 3
    [0, 1, 5, 4],  # User 4
])

# User-based collaborative filtering
def user_based_cf(ratings, user_id, k=2):
    """Recommend based on similar users"""
    # Compute user similarities
    user_sim = cosine_similarity(ratings)

    # Find k most similar users (exclude self)
    similar_users = np.argsort(user_sim[user_id])[::-1][1:k+1]

    # Predict ratings for unrated items
    user_ratings = ratings[user_id]
    predictions = np.zeros(ratings.shape[1])

    for item_id in range(ratings.shape[1]):
        if user_ratings[item_id] == 0:  # Unrated item
            # Weighted average of similar users' ratings
            numerator = 0
            denominator = 0
            for sim_user in similar_users:
                if ratings[sim_user, item_id] > 0:
                    numerator += user_sim[user_id, sim_user] * ratings[sim_user, item_id]
                    denominator += user_sim[user_id, sim_user]

            if denominator > 0:
                predictions[item_id] = numerator / denominator

    return predictions

# Item-based collaborative filtering
def item_based_cf(ratings, user_id, k=2):
    """Recommend based on similar items"""
    # Compute item similarities
    item_sim = cosine_similarity(ratings.T)

    user_ratings = ratings[user_id]
    predictions = np.zeros(ratings.shape[1])

    for item_id in range(ratings.shape[1]):
        if user_ratings[item_id] == 0:  # Unrated item
            # Find k most similar items user has rated
            similar_items = np.argsort(item_sim[item_id])[::-1]

            numerator = 0
            denominator = 0
            for sim_item in similar_items:
                if user_ratings[sim_item] > 0:
                    numerator += item_sim[item_id, sim_item] * user_ratings[sim_item]
                    denominator += item_sim[item_id, sim_item]

            if denominator > 0:
                predictions[item_id] = numerator / denominator

    return predictions

# Test
user_id = 0
user_preds = user_based_cf(ratings, user_id, k=2)
item_preds = item_based_cf(ratings, user_id, k=2)

print(f"User-based predictions: {user_preds}")
print(f"Item-based predictions: {item_preds}")
```

### Concept 2: Matrix Factorization

**Decomposition**: `R ≈ U × V^T`
- `R`: user-item ratings (m × n)
- `U`: user factors (m × k)
- `V`: item factors (n × k)
- `k`: latent dimensions (typically 10-200)

**Algorithms**:
- SVD (Singular Value Decomposition)
- ALS (Alternating Least Squares)
- SGD (Stochastic Gradient Descent)

```python
from scipy.sparse.linalg import svds

def matrix_factorization_svd(ratings, k=2):
    """SVD-based matrix factorization"""
    # Handle missing values: replace 0s with row mean
    ratings_mean = np.mean(ratings, axis=1, keepdims=True)
    ratings_filled = ratings.copy()
    ratings_filled[ratings == 0] = np.repeat(ratings_mean, ratings.shape[1], axis=1)[ratings == 0]

    # SVD
    U, sigma, Vt = svds(ratings_filled, k=k)

    # Reconstruct ratings
    sigma = np.diag(sigma)
    predicted_ratings = np.dot(np.dot(U, sigma), Vt)

    return predicted_ratings, U, Vt.T

# Predict
predicted_ratings, user_factors, item_factors = matrix_factorization_svd(ratings, k=2)

# Recommend for user 0
user_id = 0
user_predictions = predicted_ratings[user_id]
unrated_items = np.where(ratings[user_id] == 0)[0]
recommended_items = sorted(unrated_items, key=lambda x: user_predictions[x], reverse=True)

print(f"Top recommendations for user {user_id}: {recommended_items[:3]}")
```

### Concept 3: Content-Based Filtering

**Idea**: Recommend items similar to what user liked based on item features

**Features**:
- Text: TF-IDF, embeddings
- Categories: one-hot encoding
- Attributes: price, brand, color
- Media: image embeddings, audio features

```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Item descriptions
items = [
    "smartphone with 5G camera",
    "laptop with SSD storage",
    "wireless headphones bluetooth",
    "tablet with stylus pen",
    "smartwatch fitness tracker"
]

# Extract TF-IDF features
vectorizer = TfidfVectorizer()
item_features = vectorizer.fit_transform(items)

# User profile: aggregate features of items user liked
user_liked_items = [0, 2]  # Liked smartphone and headphones
user_profile = item_features[user_liked_items].mean(axis=0)

# Compute similarity to all items
similarities = cosine_similarity(user_profile, item_features)[0]

# Recommend items user hasn't interacted with
recommended_indices = np.argsort(similarities)[::-1]
recommended_items = [i for i in recommended_indices if i not in user_liked_items]

print(f"Content-based recommendations: {recommended_items[:3]}")
for idx in recommended_items[:3]:
    print(f"  {items[idx]} (score: {similarities[idx]:.3f})")
```

### Concept 4: Hybrid Recommenders

**Approaches**:

**Weighted**: Combine CF and content-based scores
```
score = α × CF_score + (1-α) × content_score
```

**Switching**: Choose method based on context
- New users → content-based
- Established users → collaborative

**Feature Augmentation**: Add content features to CF model

**Cascade**: Use one method to filter, another to rank

```python
def hybrid_recommender(user_id, ratings, item_features, alpha=0.5):
    """Weighted hybrid of CF and content-based"""
    # Collaborative filtering score
    cf_scores = item_based_cf(ratings, user_id)

    # Content-based score
    user_liked_items = np.where(ratings[user_id] > 0)[0]
    user_profile = item_features[user_liked_items].mean(axis=0)
    content_scores = cosine_similarity(user_profile, item_features)[0]

    # Normalize scores to 0-1
    cf_norm = (cf_scores - cf_scores.min()) / (cf_scores.max() - cf_scores.min() + 1e-9)
    content_norm = (content_scores - content_scores.min()) / (content_scores.max() - content_scores.min() + 1e-9)

    # Weighted combination
    hybrid_scores = alpha * cf_norm + (1 - alpha) * content_norm

    # Recommend unrated items
    unrated_items = np.where(ratings[user_id] == 0)[0]
    recommended_items = sorted(unrated_items, key=lambda x: hybrid_scores[x], reverse=True)

    return recommended_items, hybrid_scores

# Test
recommended, scores = hybrid_recommender(0, ratings, item_features, alpha=0.6)
print(f"Hybrid recommendations: {recommended[:3]}")
```

---

## Patterns

### Pattern 1: Implicit Feedback (Clicks, Views, Purchases)

**When to use**: No explicit ratings, only behavioral signals

```python
# Implicit feedback: 1 = interacted, 0 = not interacted
implicit_ratings = np.array([
    [1, 1, 0, 0],  # User 0 clicked items 0, 1
    [1, 0, 0, 1],  # User 1 clicked items 0, 3
    [0, 1, 0, 1],
    [0, 0, 1, 1],
])

from implicit.als import AlternatingLeastSquares

# Convert to sparse matrix (required by implicit library)
from scipy.sparse import csr_matrix
sparse_ratings = csr_matrix(implicit_ratings)

# Train ALS model
model = AlternatingLeastSquares(factors=10, iterations=20, regularization=0.01)
model.fit(sparse_ratings)

# Recommend for user
user_id = 0
recommendations = model.recommend(user_id, sparse_ratings[user_id], N=3)

print(f"Recommendations: {recommendations}")
```

### Pattern 2: Cold Start - Content Bootstrapping

**Use case**: New items or users with no interaction history

```python
def cold_start_item(new_item_features, item_features, ratings, top_k=5):
    """Recommend new item to users based on content similarity"""
    # Find most similar existing items
    similarities = cosine_similarity([new_item_features], item_features)[0]
    similar_items = np.argsort(similarities)[::-1][:top_k]

    # Recommend to users who liked similar items
    recommended_users = []
    for user_id in range(ratings.shape[0]):
        user_ratings = ratings[user_id]
        # Check if user liked similar items
        if any(user_ratings[item_id] > 0 for item_id in similar_items):
            recommended_users.append(user_id)

    return recommended_users

def cold_start_user(user_preferences, item_features, top_k=5):
    """Recommend items to new user based on stated preferences"""
    # User provides initial preferences (e.g., survey, onboarding)
    # preferences: text description or selected categories

    # Convert preferences to feature vector
    user_vector = vectorizer.transform([user_preferences])

    # Find similar items
    similarities = cosine_similarity(user_vector, item_features)[0]
    recommended_items = np.argsort(similarities)[::-1][:top_k]

    return recommended_items

# Example
new_user_prefs = "wireless headphones with noise cancellation"
recommendations = cold_start_user(new_user_prefs, item_features, top_k=3)
```

### Pattern 3: Diversity and Serendipity

**When to use**: Avoid filter bubbles, increase discovery

```python
def diversified_recommendations(user_id, candidate_items, item_features, scores, diversity_weight=0.3):
    """MMR-style diversification"""
    selected = []
    remaining = list(candidate_items)

    while len(selected) < 10 and remaining:
        best_item = None
        best_score = -float('inf')

        for item in remaining:
            # Relevance score
            relevance = scores[item]

            # Diversity penalty: similarity to selected items
            if selected:
                similarities = cosine_similarity(
                    item_features[item].reshape(1, -1),
                    item_features[selected]
                )[0]
                diversity_penalty = max(similarities)
            else:
                diversity_penalty = 0

            # MMR score
            mmr = relevance - diversity_weight * diversity_penalty

            if mmr > best_score:
                best_score = mmr
                best_item = item

        selected.append(best_item)
        remaining.remove(best_item)

    return selected
```

### Pattern 4: Session-Based Recommendations

**Use case**: Recommend based on current session (e.g., shopping cart)

```python
def session_based_recommendations(session_items, item_similarity_matrix, top_k=5):
    """Recommend items based on current session"""
    # Aggregate item similarities for session
    session_scores = np.zeros(item_similarity_matrix.shape[0])

    for item_id in session_items:
        # Add similarity scores from this item
        session_scores += item_similarity_matrix[item_id]

    # Remove already selected items
    session_scores[session_items] = -np.inf

    # Top-k recommendations
    recommended_items = np.argsort(session_scores)[::-1][:top_k]
    return recommended_items

# Example: User has items [0, 2] in cart
cart_items = [0, 2]
session_recs = session_based_recommendations(cart_items, item_sim, top_k=3)
```

### Pattern 5: Temporal Dynamics (Recency Weighting)

**When to use**: User preferences change over time

```python
import numpy as np
from datetime import datetime, timedelta

def time_weighted_user_profile(user_interactions, item_features, decay_days=30):
    """Build user profile with recency weighting"""
    user_profile = np.zeros(item_features.shape[1])
    total_weight = 0

    for interaction in user_interactions:
        item_id = interaction['item_id']
        timestamp = interaction['timestamp']
        rating = interaction.get('rating', 1)

        # Time decay: exponential decay based on age
        days_ago = (datetime.now() - timestamp).days
        weight = np.exp(-days_ago / decay_days) * rating

        user_profile += weight * item_features[item_id]
        total_weight += weight

    if total_weight > 0:
        user_profile /= total_weight

    return user_profile

# Example
interactions = [
    {'item_id': 0, 'timestamp': datetime.now() - timedelta(days=5), 'rating': 5},
    {'item_id': 2, 'timestamp': datetime.now() - timedelta(days=30), 'rating': 4},
]

user_profile = time_weighted_user_profile(interactions, item_features)
```

### Pattern 6: Contextual Recommendations

**Use case**: Consider context (time, location, device, weather)

```python
def contextual_recommendations(user_id, context, ratings, context_features):
    """Adjust recommendations based on context"""
    # Base recommendations
    base_scores = item_based_cf(ratings, user_id)

    # Context adjustments
    context_boosts = np.ones(len(base_scores))

    # Time-based: morning vs evening
    if context['time_of_day'] == 'morning':
        context_boosts[context_features['category'] == 'news'] *= 1.5
    elif context['time_of_day'] == 'evening':
        context_boosts[context_features['category'] == 'entertainment'] *= 1.5

    # Location-based
    if context['location'] == 'home':
        context_boosts[context_features['category'] == 'home_goods'] *= 1.3

    # Device-based
    if context['device'] == 'mobile':
        context_boosts[context_features['mobile_friendly'] == 1] *= 1.2

    # Apply boosts
    adjusted_scores = base_scores * context_boosts

    return np.argsort(adjusted_scores)[::-1]
```

### Pattern 7: Evaluation - Offline Metrics

**When to use**: Validate recommender before deployment

```python
def evaluate_recommender(test_data, predict_fn, k=10):
    """Evaluate with Precision@k, Recall@k, nDCG@k"""
    precisions = []
    recalls = []
    ndcgs = []

    for user_id, ground_truth_items in test_data:
        # Get recommendations
        recommendations = predict_fn(user_id, k=k)

        # Precision@k
        relevant_in_top_k = len(set(recommendations) & set(ground_truth_items))
        precision = relevant_in_top_k / k
        precisions.append(precision)

        # Recall@k
        recall = relevant_in_top_k / len(ground_truth_items) if ground_truth_items else 0
        recalls.append(recall)

        # nDCG@k (binary relevance)
        dcg = sum([1 / np.log2(i + 2) for i, item in enumerate(recommendations) if item in ground_truth_items])
        idcg = sum([1 / np.log2(i + 2) for i in range(min(k, len(ground_truth_items)))])
        ndcg = dcg / idcg if idcg > 0 else 0
        ndcgs.append(ndcg)

    return {
        'precision@k': np.mean(precisions),
        'recall@k': np.mean(recalls),
        'ndcg@k': np.mean(ndcgs)
    }

# Example
test_data = [
    (0, [2, 3]),  # User 0 interacted with items 2, 3 in test set
    (1, [1, 3]),
]

metrics = evaluate_recommender(test_data, lambda u, k: item_based_cf(ratings, u)[:k], k=5)
print(metrics)
```

---

## Quick Reference

### Recommendation Approaches

```
Approach            | Pros                           | Cons
--------------------|--------------------------------|---------------------
User-based CF       | Serendipity, novel items       | Scalability, sparsity
Item-based CF       | Scalable, stable               | Less diversity
Matrix Factorization| Scalable, handles sparsity     | Cold start
Content-based       | No cold start for items        | Overspecialization
Hybrid              | Best of both worlds            | Complexity
```

### Evaluation Metrics

```
Metric        | Formula                      | Interpretation
--------------|------------------------------|----------------
Precision@k   | relevant_in_top_k / k        | Accuracy of top-k
Recall@k      | relevant_in_top_k / total    | Coverage of relevant
nDCG@k        | DCG / IDCG (position aware)  | Ranking quality
Hit Rate      | users_with_hit / total_users | At least one relevant
Coverage      | recommended_items / all_items| Catalog coverage
```

### Key Guidelines

```
✅ DO: Use item-based CF for large user bases (more scalable)
✅ DO: Combine collaborative and content-based (hybrid)
✅ DO: Handle cold start with content features or popularity
✅ DO: Diversify recommendations to avoid filter bubbles
✅ DO: Weight recent interactions more heavily
✅ DO: A/B test recommendations with engagement metrics

❌ DON'T: Use user-based CF for millions of users (doesn't scale)
❌ DON'T: Ignore implicit feedback (clicks, views, time spent)
❌ DON'T: Recommend only popular items (hurts diversity)
❌ DON'T: Deploy without offline evaluation first
❌ DON'T: Forget to filter already consumed items
```

---

## Anti-Patterns

### Critical Violations

```python
# ❌ NEVER: Recommend items user already consumed
def bad_recommender(user_id, scores):
    return np.argsort(scores)[::-1][:10]
    # Might include items user already rated/bought

# ✅ CORRECT: Filter consumed items
def good_recommender(user_id, scores, user_history):
    # Exclude already consumed
    scores_filtered = scores.copy()
    scores_filtered[user_history] = -np.inf

    recommendations = np.argsort(scores_filtered)[::-1][:10]
    return recommendations
```

❌ **Recommending consumed items**: Terrible user experience
✅ **Correct approach**: Always filter user's history

### Common Mistakes

```python
# ❌ Don't: Ignore popularity bias
# Popular items dominate, long tail gets no exposure
recommendations = top_rated_items[:10]

# ✅ Correct: Balance popularity with personalization
def debiased_recommendations(user_scores, item_popularity, alpha=0.7):
    """Combine personalization with popularity"""
    # Normalize
    user_scores_norm = user_scores / user_scores.max()
    popularity_norm = item_popularity / item_popularity.max()

    # Inverse popularity weighting
    scores = user_scores_norm / (popularity_norm ** alpha + 1e-9)
    return np.argsort(scores)[::-1]
```

❌ **Popularity bias**: Long tail items never recommended
✅ **Better**: Inverse popularity weighting or diversity constraints

```python
# ❌ Don't: Use only explicit ratings
# Most users don't rate, lose 95%+ of signals
ratings_matrix = explicit_ratings_only

# ✅ Correct: Use implicit feedback
implicit_signals = {
    'click': 1,
    'add_to_cart': 2,
    'purchase': 5,
    'review': 3
}

# Build ratings from all interactions
for interaction in user_interactions:
    rating = implicit_signals.get(interaction['type'], 0)
    ratings_matrix[user_id, item_id] += rating
```

❌ **Explicit ratings only**: Massive data sparsity
✅ **Better**: Use implicit feedback (clicks, views, purchases)

```python
# ❌ Don't: Train on all data, no holdout
model.fit(all_interactions)
# Can't evaluate quality, might overfit

# ✅ Correct: Temporal split for evaluation
# Train on history, test on recent interactions
train_cutoff = datetime.now() - timedelta(days=7)

train_data = [x for x in interactions if x['timestamp'] < train_cutoff]
test_data = [x for x in interactions if x['timestamp'] >= train_cutoff]

model.fit(train_data)
metrics = evaluate(model, test_data)
```

❌ **No evaluation**: Can't measure quality or improvements
✅ **Better**: Temporal split, evaluate on future interactions

---

## Related Skills

- `ir-search-fundamentals.md` - Content-based filtering uses IR techniques (TF-IDF, embeddings)
- `ir-vector-search.md` - Semantic similarity for content-based recommendations
- `ir-ranking-reranking.md` - Ranking metrics and learning to rank for recommendations
- `ml/dspy-rag.md` - Retrieval patterns similar to recommendation retrieval
- `database-postgres.md` - Store user-item interactions efficiently

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
