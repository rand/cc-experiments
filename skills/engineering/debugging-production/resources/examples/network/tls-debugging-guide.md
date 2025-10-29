# TLS/SSL Debugging Guide

Comprehensive guide for debugging TLS/SSL issues in production.

## Quick Diagnostics

### 1. Test TLS Connection
```bash
# Basic connection test
openssl s_client -connect api.example.com:443

# With SNI (Server Name Indication)
openssl s_client -connect api.example.com:443 -servername api.example.com

# Show certificate chain
openssl s_client -connect api.example.com:443 -showcerts
```

### 2. Check Certificate Expiration
```bash
# Quick check
echo | openssl s_client -connect api.example.com:443 2>/dev/null | \
  openssl x509 -noout -dates

# Detailed info
echo | openssl s_client -connect api.example.com:443 2>/dev/null | \
  openssl x509 -noout -text
```

### 3. Test Specific TLS Version
```bash
# TLS 1.2
openssl s_client -connect api.example.com:443 -tls1_2

# TLS 1.3
openssl s_client -connect api.example.com:443 -tls1_3

# SSL 3.0 (should fail for security)
openssl s_client -connect api.example.com:443 -ssl3
```

---

## Common TLS Issues

### Issue 1: Certificate Verification Failed

**Symptoms:**
```
verify error:num=20:unable to get local issuer certificate
verify error:num=21:unable to verify the first certificate
```

**Diagnosis:**
```bash
# Check certificate chain
openssl s_client -connect api.example.com:443 -showcerts

# Verify with CA bundle
openssl s_client -connect api.example.com:443 \
  -CAfile /etc/ssl/certs/ca-certificates.crt
```

**Common Causes:**
- Incomplete certificate chain
- Self-signed certificate
- CA certificate not trusted
- Wrong intermediate certificate

**Fix:**
```bash
# Include intermediate certificate in server config
cat server.crt intermediate.crt > fullchain.crt

# Or trust the CA (development only)
sudo cp custom-ca.crt /usr/local/share/ca-certificates/
sudo update-ca-certificates
```

### Issue 2: Certificate Name Mismatch

**Symptoms:**
```
verify error:num=62:Hostname mismatch
certificate verify failed: subject alternative name does not match
```

**Diagnosis:**
```bash
# Check certificate SANs
echo | openssl s_client -connect api.example.com:443 2>/dev/null | \
  openssl x509 -noout -text | grep -A 1 "Subject Alternative Name"

# Check certificate CN
echo | openssl s_client -connect api.example.com:443 2>/dev/null | \
  openssl x509 -noout -subject
```

**Common Causes:**
- Connecting to IP instead of hostname
- Certificate issued for different domain
- Missing Subject Alternative Name (SAN)
- Wildcard mismatch

**Fix:**
- Use correct hostname in connection
- Reissue certificate with correct SANs
- Use wildcard certificate if applicable

### Issue 3: TLS Handshake Timeout

**Symptoms:**
```
Connection timeout
TLS handshake timeout
connect: Operation timed out
```

**Diagnosis:**
```bash
# Test with timeout
timeout 5 openssl s_client -connect api.example.com:443

# Check port accessibility
nc -zv api.example.com 443

# Trace connection
curl -v --trace-time https://api.example.com 2>&1 | grep -i "ssl\|tls"
```

**Common Causes:**
- Firewall blocking port 443
- Network issues
- Server not responding
- MTU/fragmentation issues

**Fix:**
```bash
# Check firewall rules
iptables -L -n | grep 443

# Test from different network
curl -v https://api.example.com

# Check MTU
ip link show | grep mtu
```

### Issue 4: Cipher Suite Mismatch

**Symptoms:**
```
no ciphers available
no suitable shared cipher
sslv3 alert handshake failure
```

**Diagnosis:**
```bash
# Show supported ciphers
nmap --script ssl-enum-ciphers -p 443 api.example.com

# Test specific cipher
openssl s_client -connect api.example.com:443 \
  -cipher 'ECDHE-RSA-AES128-GCM-SHA256'

# Show negotiated cipher
openssl s_client -connect api.example.com:443 | grep "Cipher"
```

**Common Causes:**
- Client requires cipher not supported by server
- Server configured with too restrictive ciphers
- Old TLS version not supported
- Missing cipher suite support in OpenSSL

**Fix:**
```nginx
# Nginx: Enable broader cipher support
ssl_ciphers HIGH:!aNULL:!MD5;
ssl_prefer_server_ciphers on;
```

### Issue 5: Certificate Expired

**Symptoms:**
```
certificate has expired
certificate is not yet valid
```

**Diagnosis:**
```bash
# Check expiration
echo | openssl s_client -connect api.example.com:443 2>/dev/null | \
  openssl x509 -noout -dates

# Calculate days until expiration
echo | openssl s_client -connect api.example.com:443 2>/dev/null | \
  openssl x509 -noout -checkend 0
```

**Fix:**
- Renew certificate before expiration
- Set up monitoring for expiration (30 days warning)
- Use automated renewal (Let's Encrypt)

---

## Capturing TLS Traffic

### Method 1: Using SSLKEYLOGFILE

```bash
# Set environment variable before starting application
export SSLKEYLOGFILE=/tmp/sslkeys.log

# Start application (works with Firefox, Chrome, curl, etc.)
curl https://api.example.com

# Capture traffic
tcpdump -i any -s 65535 -w /tmp/tls.pcap 'port 443'

# Open in Wireshark:
# Edit -> Preferences -> Protocols -> TLS
# -> (Pre)-Master-Secret log filename: /tmp/sslkeys.log
```

### Method 2: Using mitmproxy

```bash
# Install
pip install mitmproxy

# Run as transparent proxy
mitmproxy --mode transparent --listen-host 0.0.0.0 --listen-port 8080

# Or reverse proxy
mitmproxy --mode reverse:https://backend-api:443 --listen-port 8080

# Configure client to use proxy
export https_proxy=http://localhost:8080

# Trust mitmproxy CA certificate
cat ~/.mitmproxy/mitmproxy-ca-cert.pem >> /etc/ssl/certs/ca-certificates.crt
```

---

## Certificate Management

### Generate Self-Signed Certificate (Development)

```bash
# Generate private key and certificate
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem \
  -days 365 -nodes \
  -subj "/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
```

### Verify Certificate Chain

```bash
# Verify certificate against CA
openssl verify -CAfile ca.crt server.crt

# Build and verify chain
openssl verify -CAfile root.crt -untrusted intermediate.crt server.crt
```

### Convert Certificate Formats

```bash
# PEM to DER
openssl x509 -in cert.pem -outform der -out cert.der

# PEM to PKCS12
openssl pkcs12 -export -in cert.pem -inkey key.pem -out cert.p12

# PKCS12 to PEM
openssl pkcs12 -in cert.p12 -out cert.pem -nodes
```

---

## Testing Tools

### curl

```bash
# Basic HTTPS request
curl https://api.example.com

# Show TLS info
curl -v https://api.example.com 2>&1 | grep -i "ssl\|tls"

# Use specific TLS version
curl --tlsv1.2 https://api.example.com

# Ignore certificate verification (testing only!)
curl -k https://api.example.com

# Use client certificate
curl --cert client.pem --key client-key.pem https://api.example.com
```

### nmap

```bash
# Enumerate supported ciphers
nmap --script ssl-enum-ciphers -p 443 api.example.com

# Check for vulnerabilities
nmap --script ssl-* -p 443 api.example.com

# Check certificate
nmap --script ssl-cert -p 443 api.example.com
```

### testssl.sh

```bash
# Install
git clone https://github.com/drwetter/testssl.sh.git

# Run comprehensive test
./testssl.sh api.example.com:443

# Test specific category
./testssl.sh --protocols api.example.com:443
./testssl.sh --ciphers api.example.com:443
```

---

## Monitoring Certificate Expiration

### Script

```bash
#!/bin/bash
# check-cert-expiry.sh

HOST="$1"
PORT="${2:-443}"
WARN_DAYS=30

if [[ -z "$HOST" ]]; then
    echo "Usage: $0 <host> [port]"
    exit 1
fi

# Get expiration date
EXPIRY=$(echo | openssl s_client -connect "$HOST:$PORT" -servername "$HOST" 2>/dev/null | \
  openssl x509 -noout -enddate | cut -d= -f2)

# Convert to epoch
EXPIRY_EPOCH=$(date -d "$EXPIRY" +%s)
NOW_EPOCH=$(date +%s)

# Calculate days
DAYS_UNTIL_EXPIRY=$(( (EXPIRY_EPOCH - NOW_EPOCH) / 86400 ))

echo "Certificate expires: $EXPIRY"
echo "Days until expiration: $DAYS_UNTIL_EXPIRY"

if [[ $DAYS_UNTIL_EXPIRY -lt 0 ]]; then
    echo "ERROR: Certificate has expired!"
    exit 2
elif [[ $DAYS_UNTIL_EXPIRY -lt $WARN_DAYS ]]; then
    echo "WARNING: Certificate expires in $DAYS_UNTIL_EXPIRY days"
    exit 1
else
    echo "OK: Certificate valid for $DAYS_UNTIL_EXPIRY days"
    exit 0
fi
```

---

## Best Practices

1. **Certificate Management**
   - Use automated renewal (Let's Encrypt, cert-manager)
   - Monitor expiration dates (30-day warning)
   - Keep private keys secure
   - Use strong key sizes (4096-bit RSA or 256-bit ECC)

2. **TLS Configuration**
   - Disable old protocols (SSL 3.0, TLS 1.0, TLS 1.1)
   - Use modern cipher suites
   - Enable Perfect Forward Secrecy
   - Prefer server cipher order

3. **Security**
   - Regular security audits (testssl.sh, SSL Labs)
   - Monitor for vulnerabilities (Heartbleed, etc.)
   - Use HSTS headers
   - Implement certificate pinning for mobile apps

4. **Troubleshooting**
   - Always check logs first
   - Use verbose mode in clients
   - Test from multiple locations
   - Verify with online tools (SSL Labs)
