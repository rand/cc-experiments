#!/bin/bash
# Test script for Production RAG API

set -e

BASE_URL="${BASE_URL:-http://localhost:8080}"

echo "Testing Production RAG API at $BASE_URL"
echo "=========================================="

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Health Check
echo -e "\n${YELLOW}Test 1: Health Check${NC}"
curl -s "$BASE_URL/health" | jq '.' || echo -e "${RED}FAILED${NC}"

# Test 2: Index Documents
echo -e "\n${YELLOW}Test 2: Index Documents${NC}"
curl -s -X POST "$BASE_URL/index" \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [
      {
        "id": "rust-1",
        "text": "Rust is a systems programming language that runs blazingly fast, prevents segfaults, and guarantees thread safety. It achieves memory safety without garbage collection through its ownership system.",
        "metadata": {"category": "language", "source": "docs"}
      },
      {
        "id": "rust-2",
        "text": "The ownership system in Rust ensures that each value has a single owner. When the owner goes out of scope, the value is dropped. This prevents memory leaks and data races.",
        "metadata": {"category": "ownership", "source": "docs"}
      },
      {
        "id": "rust-3",
        "text": "Rust provides zero-cost abstractions, meaning you can write high-level code without sacrificing performance. The compiler optimizes code to be as fast as hand-written low-level code.",
        "metadata": {"category": "performance", "source": "docs"}
      }
    ],
    "chunk_size": 512,
    "overlap": 50
  }' | jq '.' && echo -e "${GREEN}SUCCESS${NC}" || echo -e "${RED}FAILED${NC}"

# Give time for indexing
echo -e "\n${YELLOW}Waiting 3 seconds for indexing...${NC}"
sleep 3

# Test 3: Query without reranking
echo -e "\n${YELLOW}Test 3: Query without Reranking${NC}"
curl -s -X POST "$BASE_URL/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How does Rust ensure memory safety?",
    "top_k": 3,
    "rerank": false
  }' | jq '{answer: .answer, sources: .sources | length, latency_ms: .latency_ms}' \
  && echo -e "${GREEN}SUCCESS${NC}" || echo -e "${RED}FAILED${NC}"

# Test 4: Query with reranking
echo -e "\n${YELLOW}Test 4: Query with Reranking${NC}"
curl -s -X POST "$BASE_URL/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the ownership system in Rust?",
    "top_k": 2,
    "rerank": true,
    "temperature": 0.5
  }' | jq '{answer: .answer, sources: .sources | length, latency_ms: .latency_ms}' \
  && echo -e "${GREEN}SUCCESS${NC}" || echo -e "${RED}FAILED${NC}"

# Test 5: Metrics
echo -e "\n${YELLOW}Test 5: Metrics Endpoint${NC}"
curl -s "$BASE_URL/metrics" | grep -E "rag_queries_total|rag_cache" \
  && echo -e "${GREEN}SUCCESS${NC}" || echo -e "${RED}FAILED${NC}"

# Test 6: Cache Hit
echo -e "\n${YELLOW}Test 6: Cache Hit Test${NC}"
echo "Query 1:"
curl -s -X POST "$BASE_URL/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are zero-cost abstractions?",
    "top_k": 2,
    "rerank": false
  }' | jq '.latency_ms'

echo "Query 2 (should be faster due to cache):"
curl -s -X POST "$BASE_URL/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are zero-cost abstractions?",
    "top_k": 2,
    "rerank": false
  }' | jq '.latency_ms' && echo -e "${GREEN}SUCCESS${NC}" || echo -e "${RED}FAILED${NC}"

echo -e "\n=========================================="
echo -e "${GREEN}All tests completed!${NC}"
