---
name: api-api-design-rules
description: 30+ opinionated API design rules for REST endpoints, error handling, pagination, versioning, and security. Actionable best practices.
---

# API Design Rules

Opinionated, high-density rules for designing HTTP/REST APIs. These are prescriptive — follow them unless you have a specific, articulated reason not to. Not a tutorial; assumes working API knowledge.

---

## Resources

**1. Use nouns, not verbs.**
Resources are things. Use `/users`, `/orders`, `/invoices`. Never `/getUsers`, `/createOrder`.

```
# Bad
POST /createUser
GET  /getUserById?id=123

# Good
POST /users
GET  /users/123
```

**2. Use plural nouns for collections.**
`/users` not `/user`. A collection endpoint and a single-resource endpoint should share the same base path.

**3. Nest resources max 2 levels deep.**
`/users/123/orders` is fine. `/users/123/orders/456/items/789/variants` is not. Promote deeply nested resources to top-level with filters.

```
# Bad
GET /users/123/orders/456/items/789

# Good
GET /order-items/789
GET /order-items?order_id=456
```

**4. Use consistent naming — snake_case for JSON fields.**
Pick one convention and enforce it. `created_at`, not `createdAt` mixed with `updated-at`. Snake_case is most interoperable.

**5. Use specific resource names over generic ones.**
`/search-results` not `/data`. `/payment-methods` not `/items`. Names should be self-documenting.

**6. Represent actions on resources as sub-resources or state changes.**
For non-CRUD operations, use a sub-resource or update the resource state.

```
# Bad
POST /orders/123/cancel

# Better (if cancel is a state transition)
PATCH /orders/123  { "status": "cancelled" }

# Also acceptable (if cancel has side effects beyond state)
POST /orders/123/cancellation
```

---

## HTTP

**7. Use the correct HTTP method.**
`GET` reads (safe, idempotent). `POST` creates (not idempotent). `PUT` replaces (idempotent). `PATCH` partially updates (idempotent). `DELETE` removes (idempotent).

**8. Return the correct status code.**
Don't return `200` for everything. Key codes:
- `201` Created (with `Location` header)
- `204` No Content (successful DELETE)
- `400` Bad Request (validation failure)
- `401` Unauthorized (no/bad credentials)
- `403` Forbidden (authenticated but not authorized)
- `404` Not Found
- `409` Conflict (duplicate, state conflict)
- `422` Unprocessable Entity (semantically invalid)
- `429` Too Many Requests

**9. Use idempotency keys for non-idempotent operations.**
Accept an `Idempotency-Key` header on `POST` endpoints. Store and check it server-side. Retry-safe APIs prevent duplicate charges, orders, and messages.

```
POST /payments
Idempotency-Key: abc-123-def
```

**10. Support `Accept` and `Content-Type` headers.**
Always return `Content-Type: application/json`. If you support multiple formats, respect `Accept`. Return `406` if you can't satisfy it.

**11. Use `HEAD` for existence checks and metadata.**
`HEAD /users/123` returns headers only. Use it for checking if a resource exists without fetching the body.

---

## Pagination

**12. Always paginate list endpoints.**
Never return unbounded collections. Even if you have 10 items today, you'll have 10,000 tomorrow.

**13. Prefer cursor-based pagination over offset.**
Offset pagination breaks when data changes between pages. Cursor pagination is stable and performant.

```json
{
  "data": [...],
  "pagination": {
    "next_cursor": "eyJpZCI6MTAwfQ==",
    "has_more": true
  }
}
```

**14. Use a consistent response envelope.**
Every list endpoint returns the same shape. Clients shouldn't guess.

```json
{
  "data": [],
  "pagination": { "next_cursor": null, "has_more": false }
}
```

**15. Make total count optional and explicit.**
`GET /users?include_total=true`. Counting is expensive on large tables. Don't compute it by default. Return it in a `total_count` field when requested.

---

## Errors

**16. Use RFC 7807 Problem Details format.**
Machine-readable, standardized, extensible.

```json
{
  "type": "https://api.example.com/errors/insufficient-funds",
  "title": "Insufficient Funds",
  "status": 422,
  "detail": "Account balance is $10.00, but $25.00 is required.",
  "instance": "/payments/abc-123"
}
```

**17. Include a machine-readable error code.**
`"type"` or a `"code"` field that clients can switch on. Never make clients parse `"detail"` strings to determine error type.

**18. Never leak internal details in errors.**
No stack traces, SQL queries, file paths, or internal service names in production error responses. Log them server-side.

**19. Return structured validation errors.**
For 400/422 responses, return per-field errors so clients can display them inline.

```json
{
  "type": "https://api.example.com/errors/validation",
  "title": "Validation Error",
  "status": 422,
  "errors": [
    { "field": "email", "message": "Must be a valid email address" },
    { "field": "age", "message": "Must be at least 18" }
  ]
}
```

**20. Use `Retry-After` header for 429 and 503 responses.**
Tell clients when to retry. Without it, clients guess and thundering-herd your service.

---

## Security

**21. Rate limit every public endpoint.**
Apply rate limits per IP, per API key, or per user. Return `429` with `Retry-After`. No exceptions for "low traffic" endpoints.

**22. Require authentication on every endpoint.**
Explicitly mark the rare public endpoints as public. Default is authenticated. Never "forget" auth on a new endpoint.

**23. Configure CORS explicitly.**
Never `Access-Control-Allow-Origin: *` on authenticated endpoints. Allowlist specific origins. Set `Access-Control-Allow-Credentials` only when needed.

**24. Never put secrets in URLs.**
API keys, tokens, passwords — never in query strings. They end up in logs, browser history, and referrer headers. Use headers.

```
# Bad
GET /users?api_key=sk_live_abc123

# Good
GET /users
Authorization: Bearer sk_live_abc123
```

**25. Validate and sanitize all input.**
Don't trust Content-Length, query params, path params, or headers. Validate types, ranges, and formats. Reject unknown fields in strict mode.

---

## Versioning

**26. Version in the URL path.**
`/v1/users`, `/v2/users`. Header-based versioning is harder to test, debug, and cache. URL versioning is visible and simple.

**27. Send deprecation headers on old versions.**
Use `Deprecation: true` and `Sunset: Sat, 01 Jan 2025 00:00:00 GMT` headers. Give clients automated signals.

**28. Announce sunset dates at least 6 months ahead.**
Breaking changes need lead time. Document the migration path. Monitor usage of deprecated versions and notify active consumers.

---

## General

**29. Use ISO 8601 for all dates and times.**
Always `2024-01-15T09:30:00Z`. Never Unix timestamps in API responses (use them internally if you want). Always include timezone — prefer UTC.

**30. Use ETags for caching.**
Return `ETag` on GET responses. Support `If-None-Match` for conditional requests. Return `304 Not Modified` when content hasn't changed.

**31. Support `fields` parameter for partial responses.**
Let clients request only the fields they need: `GET /users/123?fields=id,name,email`. Reduces payload and processing.

**32. Use HATEOAS links for discoverability where it adds value.**
For complex workflows (checkout, onboarding), include `_links` with next actions. Don't add links to every endpoint mechanically.

```json
{
  "id": "order-123",
  "status": "pending",
  "_links": {
    "pay": { "href": "/orders/order-123/payment", "method": "POST" },
    "cancel": { "href": "/orders/order-123", "method": "DELETE" }
  }
}
```

**33. Make bulk operations explicit.**
Don't overload single-resource endpoints for bulk. Use `POST /users/bulk` or `POST /bulk` with an operations array. Set sensible batch size limits.

**34. Return the created/updated resource in mutation responses.**
`POST` returns `201` with the full resource. `PATCH` returns `200` with the updated resource. Saves clients a follow-up GET.

**35. Document every endpoint with request/response examples.**
OpenAPI spec is the minimum. Include realistic example payloads, not lorem ipsum. Document error responses too.
