---
name: cryptography-ssl-legacy
description: Legacy SSL/TLS protocols (SSL 2.0/3.0, TLS 1.0/1.1), vulnerabilities, deprecation, and migration strategies
---

# Legacy SSL/TLS Protocols

**Scope**: SSL 2.0/3.0, TLS 1.0/1.1, vulnerabilities, migration to modern TLS
**Lines**: ~310
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Understanding SSL/TLS history
- Migrating from legacy protocols
- Supporting legacy clients
- Addressing security vulnerabilities
- Meeting compliance requirements (PCI DSS, HIPAA)
- Debugging compatibility issues
- Planning protocol deprecation
- Conducting security audits

## Protocol Timeline

```
1995: SSL 2.0 (deprecated 2011)
1996: SSL 3.0 (deprecated 2015)
1999: TLS 1.0 (deprecated 2020)
2006: TLS 1.1 (deprecated 2020)
2008: TLS 1.2 (current, widely supported)
2018: TLS 1.3 (current, modern)
```

---

## SSL 2.0

### Overview

**Released**: 1995
**Deprecated**: 2011 (RFC 6176)
**Status**: MUST NOT be used

### Major Vulnerabilities

```
1. No protection for handshake
2. Weak MAC construction
3. Same key for encryption and MAC
4. Downgrade attacks possible
5. No certificate chain verification
```

### Detection

```bash
# Test if SSL 2.0 is enabled (should fail)
openssl s_client -connect example.com:443 -ssl2
```

**Expected output** (secure):
```
error:1407F0E5:SSL routines:SSL2_WRITE:ssl handshake failure
```

---

## SSL 3.0

### Overview

**Released**: 1996
**Deprecated**: 2015 (RFC 7568)
**Status**: MUST NOT be used

### POODLE Attack

**Vulnerability**: Padding Oracle On Downgraded Legacy Encryption

**Impact**: CBC mode ciphers can be exploited to decrypt data

**Exploit**:
```
1. Force downgrade to SSL 3.0
2. Use CBC cipher
3. Inject chosen plaintext
4. Decrypt 1 byte per 256 requests
5. Recover session cookies
```

**Mitigation**: Disable SSL 3.0 entirely

```nginx
# Nginx
ssl_protocols TLSv1.2 TLSv1.3;

# Apache
SSLProtocol -all +TLSv1.2 +TLSv1.3
```

---

## TLS 1.0

### Overview

**Released**: 1999 (RFC 2246)
**Deprecated**: 2020
**Status**: Should not be used

### Known Vulnerabilities

**BEAST** (2011):
- Browser Exploit Against SSL/TLS
- CBC cipher vulnerability
- Mitigated by using TLS 1.1+ or RC4

**CRIME** (2012):
- Compression Ratio Info-leak Made Easy
- Exploits TLS compression
- Mitigation: Disable compression

**Example vulnerable configuration**:
```nginx
# ❌ Bad: Includes TLS 1.0
ssl_protocols TLSv1 TLSv1.1 TLSv1.2;
ssl_ciphers ALL:!aNULL:!eNULL;
```

### Browser Support End Dates

```
Chrome: Disabled January 2020
Firefox: Disabled March 2020
Safari: Disabled March 2020
Edge: Disabled January 2020
```

---

## TLS 1.1

### Overview

**Released**: 2006 (RFC 4346)
**Deprecated**: 2020
**Status**: Should not be used

### Improvements over TLS 1.0

```
+ Explicit IV for CBC (BEAST mitigation)
+ Protection against CBC attacks
+ Better PRNG requirements
```

### Why Still Deprecated?

```
- No modern cipher suites (no AEAD)
- No perfect forward secrecy requirement
- No modern features (SNI optional)
- Superseded by TLS 1.2/1.3
```

---

## Migration Strategies

### Phase 1: Assessment

**Identify current usage**:
```bash
# Check server configuration
openssl s_client -connect example.com:443 -tls1
openssl s_client -connect example.com:443 -tls1_1

# Analyze logs for client versions
awk '{print $9}' access.log | sort | uniq -c
```

**Python script to analyze TLS versions**:
```python
import ssl
import socket
from collections import Counter

def check_tls_version(host, port=443):
    versions = []
    for version in [ssl.TLSVersion.TLSv1, ssl.TLSVersion.TLSv1_1,
                    ssl.TLSVersion.TLSv1_2, ssl.TLSVersion.TLSv1_3]:
        try:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.minimum_version = version
            context.maximum_version = version
            with socket.create_connection((host, port)) as sock:
                with context.wrap_socket(sock, server_hostname=host) as ssock:
                    versions.append(ssock.version())
        except:
            pass
    return versions

# Check what server supports
supported = check_tls_version('example.com')
print(f"Supported versions: {supported}")
```

### Phase 2: Communication

**Announce deprecation timeline**:
```
T-180 days: Announce deprecation plan
T-90 days:  Remind users, provide migration guide
T-30 days:  Final warning
T-0:        Disable legacy protocols
T+30 days:  Monitor for issues
```

**Migration notice template**:
```
Subject: Action Required: TLS 1.0/1.1 Deprecation

We are upgrading our security by disabling TLS 1.0 and 1.1 on [DATE].

Required Action:
- Update clients to support TLS 1.2 or 1.3
- Test your integration before [DATE]

How to Check:
$ openssl s_client -connect api.example.com:443 -tls1_2

Support: security@example.com
```

### Phase 3: Gradual Rollout

**Progressive enforcement**:
```nginx
# Week 1-2: Log warnings
map $ssl_protocol $is_legacy {
    "TLSv1"   "1";
    "TLSv1.1" "1";
    default   "0";
}

server {
    if ($is_legacy = "1") {
        add_header X-TLS-Deprecated "true" always;
    }
}

# Week 3-4: Specific endpoints only
location /api/v2 {
    if ($is_legacy = "1") {
        return 426 "Upgrade Required: TLS 1.2+ needed";
    }
}

# Week 5+: Full enforcement
ssl_protocols TLSv1.2 TLSv1.3;
```

### Phase 4: Monitoring

**Track migration progress**:
```bash
# Count requests by TLS version
awk '{print $ssl_protocol}' access.log | sort | uniq -c

# Alert on legacy usage
if grep -q "TLSv1.0\|TLSv1.1" access.log; then
    echo "ALERT: Legacy TLS detected"
fi
```

---

## Legacy Client Support

### Compatibility Matrix

| Client | TLS 1.2 | TLS 1.3 |
|--------|---------|---------|
| Chrome 30+ | ✅ | Chrome 70+ |
| Firefox 27+ | ✅ | Firefox 63+ |
| Safari 7+ | ✅ | Safari 12.1+ |
| IE 11 | ✅ | ❌ |
| Python 2.7.9+ | ✅ | Python 3.7+ |
| Java 8+ | ✅ | Java 11+ |
| .NET 4.5+ | ✅ | .NET Core 3.0+ |

### Handling Legacy Clients

**Option 1: Separate endpoint**:
```nginx
# Modern endpoint
server {
    listen 443 ssl;
    server_name api.example.com;
    ssl_protocols TLSv1.2 TLSv1.3;
}

# Legacy endpoint (isolated)
server {
    listen 8443 ssl;
    server_name legacy.example.com;
    ssl_protocols TLSv1 TLSv1.1 TLSv1.2;

    # Additional monitoring/restrictions
    limit_req zone=legacy burst=5;
}
```

**Option 2: User agent detection**:
```nginx
map $http_user_agent $allow_legacy {
    "~*MSIE [6-9]" "1";
    "~*Windows NT 5" "1";
    default "0";
}

server {
    ssl_protocols TLSv1 TLSv1.1 TLSv1.2;

    if ($allow_legacy != "1") {
        ssl_protocols TLSv1.2 TLSv1.3;
    }
}
```

---

## Compliance Requirements

### PCI DSS

```
Requirement 4.1 (as of June 2018):
- TLS 1.0 must be disabled
- TLS 1.1 can be used until June 2024
- TLS 1.2+ recommended
```

### NIST Guidelines

```
NIST SP 800-52 Rev. 2:
- TLS 1.2 minimum
- TLS 1.3 recommended
- SSL 2.0/3.0, TLS 1.0/1.1 prohibited
```

### HIPAA

```
Not specific about TLS version, but requires:
- Current security standards
- Protection against known vulnerabilities
→ Effectively requires TLS 1.2+
```

---

## Vulnerability Summary

| Protocol | Critical Vulnerabilities |
|----------|-------------------------|
| SSL 2.0 | Multiple fundamental flaws |
| SSL 3.0 | POODLE |
| TLS 1.0 | BEAST, CRIME |
| TLS 1.1 | No AEAD support |
| TLS 1.2 | ROBOT (RSA only) |
| TLS 1.3 | None known (as of 2025) |

---

## Testing Legacy Protocol Support

### Detect Enabled Protocols

```bash
#!/bin/bash
HOST=$1
PORT=${2:-443}

for version in ssl2 ssl3 tls1 tls1_1 tls1_2 tls1_3; do
    echo -n "Testing $version: "
    if openssl s_client -connect $HOST:$PORT -$version </dev/null 2>/dev/null | grep -q "Protocol"; then
        echo "✅ Enabled"
    else
        echo "❌ Disabled"
    fi
done
```

### Automated Scanning

```bash
# Using testssl.sh
./testssl.sh --protocols example.com

# Using nmap
nmap --script ssl-enum-ciphers -p 443 example.com

# Using sslscan
sslscan example.com:443
```

---

## Best Practices

### 1. Minimum TLS Version

```nginx
# ✅ Good: TLS 1.2 minimum
ssl_protocols TLSv1.2 TLSv1.3;

# ⚠️ Acceptable: TLS 1.2 only (legacy support)
ssl_protocols TLSv1.2;

# ❌ Bad: Legacy protocols enabled
ssl_protocols TLSv1 TLSv1.1 TLSv1.2;
```

### 2. Regular Audits

```bash
# Monthly check for legacy protocol usage
0 0 1 * * /usr/local/bin/check-tls-versions.sh | mail -s "TLS Audit" security@example.com
```

### 3. Document Exceptions

```yaml
# legacy-clients.yaml
allowed_legacy_clients:
  - ip: 192.168.1.100
    reason: "Legacy medical device - upgrade planned Q3 2025"
    approved_by: "security-team"
    expires: "2025-09-30"
```

---

## Related Skills

- `cryptography-tls-configuration` - Modern TLS setup
- `cryptography-crypto-best-practices` - Security practices
- `protocols-protocol-debugging` - TLS troubleshooting
- `security-vulnerability-assessment` - Security auditing

---

**Last Updated**: 2025-10-27
