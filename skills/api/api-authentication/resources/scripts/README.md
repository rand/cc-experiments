# API Authentication Scripts

This directory contains executable scripts for JWT validation, OAuth 2.0 flow testing, and password hashing benchmarks.

## Scripts Overview

### test_jwt.py
Comprehensive JWT security testing tool for validation, expiration checks, signing verification, and vulnerability detection.

**Features**:
- Validate JWT tokens with full security checks
- Generate JWT tokens with proper claims
- Inspect token structure (header, payload, signature)
- Run security attack tests (none algorithm, algorithm confusion, weak secrets)
- Check for common vulnerabilities and best practice violations

**Usage**:
```bash
# Validate a JWT token
python test_jwt.py --token "eyJhbGc..." --validate --secret "your-secret" --algorithm HS256

# Generate a new JWT token
python test_jwt.py --generate --algorithm HS256 --secret "my-secret" \
                   --payload '{"sub":"user123","role":"admin"}' --expires-in 3600

# Inspect token structure
python test_jwt.py --token "eyJhbGc..." --inspect

# Run security tests
python test_jwt.py --token "eyJhbGc..." --attack-test --secret "your-secret" --json
```

**Security Tests**:
- None algorithm vulnerability
- Algorithm confusion attack (RS256 vs HS256)
- Weak secret detection
- Expiration bypass attempts
- Signature stripping
- Sensitive data in payload
- Token lifetime validation

---

### test_oauth_flow.py
OAuth 2.0 flow validator for testing authorization endpoints, token endpoints, and security compliance with RFC 6749.

**Features**:
- Test authorization endpoints (Authorization Code Flow)
- Test token endpoints (Client Credentials, Refresh Token flows)
- Validate PKCE implementation
- Check state parameter handling
- Test redirect URI validation
- Verify HTTPS enforcement
- Content-Type validation

**Usage**:
```bash
# Test authorization endpoint
python test_oauth_flow.py --auth-url https://auth.example.com/authorize \
                          --client-id CLIENT_ID \
                          --redirect-uri https://app.example.com/callback

# Test token endpoint
python test_oauth_flow.py --token-url https://auth.example.com/token \
                          --client-id CLIENT_ID \
                          --client-secret SECRET \
                          --test-token-endpoint

# Full OAuth 2.0 test
python test_oauth_flow.py --auth-url https://auth.example.com/authorize \
                          --token-url https://auth.example.com/token \
                          --client-id CLIENT_ID \
                          --client-secret SECRET \
                          --redirect-uri https://app.example.com/callback \
                          --full-test --json
```

**Tests**:
- Authorization endpoint connectivity
- PKCE support detection
- State parameter handling (CSRF protection)
- Redirect URI validation (prevents authorization code interception)
- Response type validation
- Client credentials authentication
- Invalid credentials handling
- HTTPS enforcement
- Content-Type header validation

---

### benchmark_hashing.py
Password hashing algorithm benchmark comparing bcrypt, Argon2id, and scrypt for performance and security characteristics.

**Features**:
- Benchmark bcrypt with configurable rounds
- Benchmark Argon2id with time/memory/parallelism tuning
- Benchmark scrypt with N/r/p parameters
- Auto-tune Argon2 for target hashing time
- Compare all algorithms side-by-side
- Statistical analysis (mean, median, stdev)
- Memory usage comparison

**Usage**:
```bash
# Benchmark all algorithms
python benchmark_hashing.py --algorithm all --iterations 50

# Tune Argon2 for 350ms target (recommended: 250-500ms)
python benchmark_hashing.py --algorithm argon2 --tune --target-ms 350

# Compare with custom parameters
python benchmark_hashing.py --compare \
                            --bcrypt-rounds 12 \
                            --argon2-time 3 \
                            --argon2-memory 65536 \
                            --iterations 100

# Benchmark specific algorithm
python benchmark_hashing.py --algorithm bcrypt --bcrypt-rounds 14 --iterations 20
```

**Parameters**:
- **bcrypt**: `--bcrypt-rounds` (default: 12, range: 10-14)
- **Argon2**: `--argon2-time` (default: 3), `--argon2-memory` (default: 65536 KB)
- **scrypt**: `--scrypt-n` (default: 16384), `--scrypt-r` (default: 8), `--scrypt-p` (default: 1)

**Output**:
```
Algorithm       Hash Time       Verify Time     Memory
--------------------------------------------------------------------------------
bcrypt          235.42ms        234.89ms        ~4KB
argon2id        287.15ms        286.73ms        65536KB
scrypt          412.34ms        411.92ms        16384KB
================================================================================

Recommendation: bcrypt
Reason: Closest to optimal 250-500ms range (target: 350ms)
```

---

## Prerequisites

### Python Dependencies

```bash
# JWT testing
pip install pyjwt cryptography

# OAuth 2.0 testing
pip install requests

# Password hashing benchmarks
pip install bcrypt argon2-cffi

# All dependencies
pip install pyjwt cryptography requests bcrypt argon2-cffi
```

### Using uv (recommended)
```bash
uv pip install pyjwt cryptography requests bcrypt argon2-cffi
```

---

## Examples

### Complete JWT Security Audit
```bash
#!/bin/bash

TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."  # Test token for security audit only
SECRET="your-secret-key"  # Placeholder - use actual secret for validation

# 1. Inspect token structure
echo "=== Token Inspection ==="
python test_jwt.py --token "$TOKEN" --inspect

# 2. Validate token
echo -e "\n=== Token Validation ==="
python test_jwt.py --token "$TOKEN" --validate --secret "$SECRET" --algorithm HS256

# 3. Run security tests
echo -e "\n=== Security Tests ==="
python test_jwt.py --token "$TOKEN" --attack-test --secret "$SECRET" --json > jwt_security_report.json

echo "Report saved to jwt_security_report.json"
```

### Full OAuth 2.0 Compliance Check
```bash
#!/bin/bash

AUTH_URL="https://auth.example.com/authorize"
TOKEN_URL="https://auth.example.com/token"
CLIENT_ID="your_client_id"
CLIENT_SECRET="your_client_secret"
REDIRECT_URI="https://app.example.com/callback"

# Full OAuth 2.0 security test
python test_oauth_flow.py \
    --auth-url "$AUTH_URL" \
    --token-url "$TOKEN_URL" \
    --client-id "$CLIENT_ID" \
    --client-secret "$CLIENT_SECRET" \
    --redirect-uri "$REDIRECT_URI" \
    --full-test \
    --json > oauth_compliance_report.json

echo "Compliance report saved to oauth_compliance_report.json"
```

### Password Hashing Parameter Selection
```bash
#!/bin/bash

# 1. Benchmark all algorithms with default parameters
echo "=== Default Parameters Benchmark ==="
python benchmark_hashing.py --algorithm all --iterations 50

# 2. Tune Argon2 for optimal performance (250-500ms)
echo -e "\n=== Tuning Argon2 ==="
python benchmark_hashing.py --algorithm argon2 --tune --target-ms 350

# 3. Compare optimized parameters
echo -e "\n=== Final Comparison ==="
python benchmark_hashing.py --compare \
    --bcrypt-rounds 12 \
    --argon2-time 3 \
    --argon2-memory 65536 \
    --iterations 100 \
    --json > hashing_benchmark.json

echo "Benchmark saved to hashing_benchmark.json"
```

### CI/CD Integration
```bash
#!/bin/bash
# Run JWT security checks in CI pipeline

set -e

TOKEN="${JWT_TOKEN}"
SECRET="${JWT_SECRET}"

# Run security tests
python test_jwt.py --token "$TOKEN" --attack-test --secret "$SECRET" --json > jwt_results.json

# Check for critical vulnerabilities
if grep -q '"severity": "CRITICAL"' jwt_results.json; then
    echo "CRITICAL vulnerabilities found in JWT implementation"
    exit 1
fi

echo "JWT security checks passed"
```

---

## Output Formats

All scripts support JSON output for easy integration with CI/CD pipelines and security dashboards:

```bash
# JSON output
python test_jwt.py --token "$TOKEN" --validate --secret "$SECRET" --json
python test_oauth_flow.py --full-test --json
python benchmark_hashing.py --compare --json
```

**JSON structure**:
```json
{
  "timestamp": "2025-10-27T12:34:56.789Z",
  "tests": [
    {
      "test": "token_validation",
      "result": {
        "valid": true,
        "claims": {...},
        "issues": []
      }
    }
  ],
  "vulnerabilities": []
}
```

---

## Security Best Practices

### JWT
- Use RS256 for microservices (public key validation)
- Use HS256 for monoliths with secure key storage
- Set expiration time (15-60 minutes)
- Validate signature, issuer, audience, and expiration
- Never store sensitive data in payload
- Use strong secrets (256+ bits for HMAC)

### OAuth 2.0
- Use PKCE for all public clients (mobile, SPAs)
- Validate redirect URIs (exact match)
- Use state parameter for CSRF protection
- Short-lived access tokens (5-15 minutes)
- Long-lived refresh tokens (days to months)
- Implement refresh token rotation

### Password Hashing
- **Target**: 250-500ms hashing time
- **Recommended**: Argon2id (winner of Password Hashing Competition)
- **Alternative**: bcrypt (rounds=12-14)
- **Avoid**: MD5, SHA-1, SHA-256, plain SHA-512

---

## Troubleshooting

### JWT Validation Fails
```bash
# Check token structure
python test_jwt.py --token "$TOKEN" --inspect

# Verify algorithm
python test_jwt.py --token "$TOKEN" --validate --secret "$SECRET" --algorithm RS256

# Check for expiration
python test_jwt.py --token "$TOKEN" --inspect | grep exp
```

### OAuth 2.0 Connection Issues
```bash
# Test with verbose output
python test_oauth_flow.py --auth-url "$URL" --test-auth-endpoint --verbose

# Check HTTPS
curl -I "$AUTH_URL"

# Verify redirect URI is registered
python test_oauth_flow.py --auth-url "$URL" --client-id "$ID" --redirect-uri "$URI" --verbose
```

### Hashing Too Slow
```bash
# Lower parameters
python benchmark_hashing.py --algorithm argon2 --argon2-time 2 --argon2-memory 32768

# Or tune automatically
python benchmark_hashing.py --algorithm argon2 --tune --target-ms 250
```

---

## Safety Note

**IMPORTANT**:
- Only test OAuth endpoints you own or have explicit authorization to test
- Do not use production secrets in testing
- These tools are for security validation, not exploitation
- Unauthorized security testing is illegal and unethical

---

## Related Resources

- `../REFERENCE.md` - Detailed JWT/OAuth specifications
- `../examples/` - Implementation examples
- Main skill: `../../api-authentication.md`

---

**Last Updated**: 2025-10-27
**Version**: 1.0
