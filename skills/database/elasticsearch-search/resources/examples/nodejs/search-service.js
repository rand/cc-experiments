#!/usr/bin/env node
/**
 * Elasticsearch Search Service (Node.js)
 *
 * Demonstrates search patterns using @elastic/elasticsearch client.
 *
 * Installation:
 *   npm install @elastic/elasticsearch
 *
 * Usage:
 *   node search-service.js
 */

const { Client } = require('@elastic/elasticsearch');

// Create Elasticsearch client
const client = new Client({
  node: 'http://localhost:9200',
  // auth: { username: 'elastic', password: 'password' }
});

/**
 * Search Service Class
 */
class SearchService {
  constructor(client, index) {
    this.client = client;
    this.index = index;
  }

  /**
   * Full-text search across multiple fields
   */
  async searchProducts(query, filters = {}) {
    const body = {
      query: {
        bool: {
          must: [
            {
              multi_match: {
                query,
                fields: ['name^3', 'description^2', 'tags'],
                fuzziness: 'AUTO'
              }
            }
          ],
          filter: []
        }
      },
      size: 20,
      sort: [
        { _score: 'desc' },
        { rating: 'desc' }
      ]
    };

    // Add filters
    if (filters.category) {
      body.query.bool.filter.push({
        term: { 'category.keyword': filters.category }
      });
    }

    if (filters.minPrice || filters.maxPrice) {
      const range = {};
      if (filters.minPrice) range.gte = filters.minPrice;
      if (filters.maxPrice) range.lte = filters.maxPrice;
      body.query.bool.filter.push({ range: { price: range } });
    }

    if (filters.inStock) {
      body.query.bool.filter.push({ term: { in_stock: true } });
    }

    const result = await this.client.search({
      index: this.index,
      body
    });

    return this.formatResults(result);
  }

  /**
   * Autocomplete suggestions
   */
  async autocomplete(prefix, category = null) {
    const suggest = {
      product_suggest: {
        prefix,
        completion: {
          field: 'suggest',
          size: 10,
          skip_duplicates: true,
          fuzzy: { fuzziness: 'AUTO' }
        }
      }
    };

    // Add category context if specified
    if (category) {
      suggest.product_suggest.completion.contexts = {
        category: [category]
      };
    }

    const result = await this.client.search({
      index: this.index,
      body: { suggest }
    });

    return result.body.suggest.product_suggest[0].options.map(opt => ({
      text: opt.text,
      score: opt._score
    }));
  }

  /**
   * Faceted search with aggregations
   */
  async facetedSearch(query, facets = ['category', 'brand', 'price']) {
    const body = {
      query: {
        multi_match: {
          query,
          fields: ['name^2', 'description']
        }
      },
      size: 20,
      aggs: {}
    };

    // Add requested facets
    if (facets.includes('category')) {
      body.aggs.categories = {
        terms: { field: 'category.keyword', size: 10 }
      };
    }

    if (facets.includes('brand')) {
      body.aggs.brands = {
        terms: { field: 'brand.keyword', size: 20 }
      };
    }

    if (facets.includes('price')) {
      body.aggs.price_ranges = {
        range: {
          field: 'price',
          ranges: [
            { key: 'Under $50', to: 50 },
            { key: '$50 - $200', from: 50, to: 200 },
            { key: '$200 - $500', from: 200, to: 500 },
            { key: 'Over $500', from: 500 }
          ]
        }
      };
    }

    const result = await this.client.search({
      index: this.index,
      body
    });

    return {
      results: this.formatResults(result),
      facets: this.formatAggregations(result.body.aggregations)
    };
  }

  /**
   * Search with custom scoring
   */
  async searchWithBoost(query, boostFactors = {}) {
    const body = {
      query: {
        function_score: {
          query: {
            multi_match: {
              query,
              fields: ['name^2', 'description']
            }
          },
          functions: []
        }
      },
      size: 20
    };

    // Boost premium products
    if (boostFactors.premiumBoost) {
      body.query.function_score.functions.push({
        filter: { term: { is_premium: true } },
        weight: boostFactors.premiumBoost
      });
    }

    // Boost by rating
    if (boostFactors.ratingBoost) {
      body.query.function_score.functions.push({
        field_value_factor: {
          field: 'rating',
          factor: boostFactors.ratingBoost,
          modifier: 'sqrt',
          missing: 1
        }
      });
    }

    // Recency boost
    if (boostFactors.recencyBoost) {
      body.query.function_score.functions.push({
        gauss: {
          created_at: {
            origin: 'now',
            scale: '30d',
            decay: 0.5
          }
        }
      });
    }

    body.query.function_score.score_mode = 'sum';
    body.query.function_score.boost_mode = 'multiply';

    const result = await this.client.search({
      index: this.index,
      body
    });

    return this.formatResults(result);
  }

  /**
   * Pagination with search_after
   */
  async paginatedSearch(query, pageSize = 20, searchAfter = null) {
    const body = {
      query: {
        multi_match: {
          query,
          fields: ['name', 'description']
        }
      },
      size: pageSize,
      sort: [
        { created_at: 'desc' },
        { _id: 'desc' }
      ]
    };

    if (searchAfter) {
      body.search_after = searchAfter;
    }

    const result = await this.client.search({
      index: this.index,
      body
    });

    const hits = result.body.hits.hits;
    const nextSearchAfter = hits.length > 0
      ? hits[hits.length - 1].sort
      : null;

    return {
      results: this.formatResults(result),
      nextSearchAfter,
      hasMore: hits.length === pageSize
    };
  }

  /**
   * Format search results
   */
  formatResults(result) {
    return result.body.hits.hits.map(hit => ({
      id: hit._id,
      score: hit._score,
      ...hit._source
    }));
  }

  /**
   * Format aggregations
   */
  formatAggregations(aggs) {
    if (!aggs) return {};

    const formatted = {};

    for (const [key, value] of Object.entries(aggs)) {
      if (value.buckets) {
        formatted[key] = value.buckets.map(bucket => ({
          key: bucket.key,
          count: bucket.doc_count
        }));
      }
    }

    return formatted;
  }
}

/**
 * Run examples
 */
async function main() {
  try {
    // Check connection
    const ping = await client.ping();
    console.log('✓ Connected to Elasticsearch');

    const service = new SearchService(client, 'products');

    // Example 1: Simple search
    console.log('\n1. Simple search:');
    const results1 = await service.searchProducts('laptop', {
      minPrice: 500,
      inStock: true
    });
    console.log(`Found ${results1.length} results`);
    results1.slice(0, 3).forEach(r => {
      console.log(`  [${r.score.toFixed(2)}] ${r.name} - $${r.price}`);
    });

    // Example 2: Autocomplete
    console.log('\n2. Autocomplete:');
    const suggestions = await service.autocomplete('lap');
    console.log(`Found ${suggestions.length} suggestions`);
    suggestions.slice(0, 5).forEach(s => {
      console.log(`  ${s.text}`);
    });

    // Example 3: Faceted search
    console.log('\n3. Faceted search:');
    const faceted = await service.facetedSearch('gaming');
    console.log(`Found ${faceted.results.length} results`);
    console.log('Facets:', JSON.stringify(faceted.facets, null, 2));

    // Example 4: Custom scoring
    console.log('\n4. Search with custom scoring:');
    const boosted = await service.searchWithBoost('laptop', {
      premiumBoost: 2,
      ratingBoost: 1.5,
      recencyBoost: true
    });
    console.log(`Found ${boosted.length} results`);
    boosted.slice(0, 3).forEach(r => {
      console.log(`  [${r.score.toFixed(2)}] ${r.name}`);
    });

    // Example 5: Pagination
    console.log('\n5. Paginated search:');
    const page1 = await service.paginatedSearch('product', 10);
    console.log(`Page 1: ${page1.results.length} results, hasMore: ${page1.hasMore}`);

    if (page1.hasMore) {
      const page2 = await service.paginatedSearch('product', 10, page1.nextSearchAfter);
      console.log(`Page 2: ${page2.results.length} results`);
    }

    console.log('\n✓ All examples completed!');

  } catch (error) {
    console.error('✗ Error:', error.message);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = SearchService;
