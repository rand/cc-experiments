# Certificate Management - Comprehensive Reference

**Version**: 1.0
**Last Updated**: 2025-10-27
**Scope**: X.509 certificates, certificate lifecycle, CA hierarchies, ACME protocol, cert-manager, certificate monitoring, mTLS, revocation

---

## Table of Contents

1. [Fundamentals](#fundamentals)
2. [X.509 Certificates](#x509-certificates)
3. [Certificate Lifecycle](#certificate-lifecycle)
4. [Certificate Authority Hierarchies](#certificate-authority-hierarchies)
5. [ACME Protocol](#acme-protocol)
6. [Let's Encrypt](#lets-encrypt)
7. [Certificate Automation](#certificate-automation)
8. [Kubernetes cert-manager](#kubernetes-cert-manager)
9. [Mutual TLS (mTLS)](#mutual-tls-mtls)
10. [Certificate Revocation](#certificate-revocation)
11. [Certificate Transparency](#certificate-transparency)
12. [Certificate Pinning](#certificate-pinning)
13. [Monitoring and Alerting](#monitoring-and-alerting)
14. [Best Practices](#best-practices)
15. [Common Issues](#common-issues)
16. [Security Considerations](#security-considerations)
17. [Compliance](#compliance)
18. [Tools and Utilities](#tools-and-utilities)

---

## Fundamentals

### What is a Digital Certificate?

A **digital certificate** binds a public key to an identity (person, organization, or device) and is signed by a trusted Certificate Authority (CA).

**Core Purpose**:
- **Authentication**: Prove identity (e.g., "I am example.com")
- **Encryption**: Establish secure communication (TLS/SSL)
- **Integrity**: Verify data hasn't been tampered with

**Trust Model**:
```
Root CA (self-signed, highly trusted)
  ↓
Intermediate CA (signed by Root CA)
  ↓
End-Entity Certificate (signed by Intermediate CA)
  ↓
Your Website/API (uses certificate)
```

### Certificate Components

```
Certificate = {
  Version: 3 (X.509v3)
  Serial Number: Unique identifier
  Signature Algorithm: SHA256-RSA
  Issuer: CA that signed this cert
  Validity: {
    Not Before: 2025-01-01
    Not After: 2025-12-31
  }
  Subject: Entity this cert represents (CN=example.com)
  Public Key: RSA 2048-bit or ECDSA P-256
  Extensions: {
    Subject Alternative Names (SANs)
    Key Usage
    Extended Key Usage
    Certificate Policies
    Authority Key Identifier
    Subject Key Identifier
  }
  Signature: CA's signature over all above data
}
```

### Trust Chain Verification

When a client connects to a server:
1. Server sends its certificate + intermediate certificates
2. Client verifies certificate chain:
   - Each certificate signed by next in chain
   - Chain ends at trusted root CA
   - All certificates valid (not expired)
   - Certificate not revoked (OCSP/CRL check)
   - Subject/SAN matches hostname

**Example Chain**:
```
example.com (end-entity cert)
  ↓ signed by
Let's Encrypt R3 (intermediate CA)
  ↓ signed by
ISRG Root X1 (root CA, in browser trust store)
```

---

## X.509 Certificates

### X.509 Standard

**X.509** is the ITU-T standard for public key certificates (RFC 5280).

**Versions**:
- **v1**: Basic certificate (rarely used)
- **v2**: Added unique identifiers
- **v3**: Added extensions (current standard)

### Certificate Formats

**PEM (Privacy Enhanced Mail)**:
```
-----BEGIN CERTIFICATE-----
MIIDXTCCAkWgAwIBAgIJAKJ5...(Base64 encoded)...
-----END CERTIFICATE-----
```
- Text format, Base64-encoded DER
- Used by: Apache, Nginx, OpenSSL
- Extensions: `.pem`, `.crt`, `.cer`

**DER (Distinguished Encoding Rules)**:
- Binary format
- Used by: Java, Windows
- Extensions: `.der`, `.cer`

**PKCS#12 / PFX**:
```
Contains:
- Certificate
- Private key
- Intermediate certificates
Protected by password
```
- Binary format, password-protected bundle
- Used by: Windows, Java keystores
- Extensions: `.p12`, `.pfx`

**Conversions**:
```bash
# PEM to DER
openssl x509 -in cert.pem -outform DER -out cert.der

# DER to PEM
openssl x509 -in cert.der -inform DER -outform PEM -out cert.pem

# PEM to PKCS#12
openssl pkcs12 -export -in cert.pem -inkey key.pem -out cert.p12

# PKCS#12 to PEM
openssl pkcs12 -in cert.p12 -out cert.pem -nodes
```

### Subject and Subject Alternative Names (SANs)

**Subject** (legacy, single name):
```
CN=example.com
O=Example Corp
L=San Francisco
ST=California
C=US
```

**Subject Alternative Names** (modern, multiple names):
```
DNS:example.com
DNS:www.example.com
DNS:*.example.com         # Wildcard
IP:192.0.2.1
email:admin@example.com
URI:https://example.com
```

**Best Practice**: Use SANs for all names. Modern browsers ignore CN and require SAN.

### Certificate Extensions

**Key Usage**:
```
- Digital Signature
- Key Encipherment
- Data Encipherment
- Key Agreement
- Certificate Signing
- CRL Signing
```

**Extended Key Usage**:
```
- TLS Web Server Authentication (1.3.6.1.5.5.7.3.1)
- TLS Web Client Authentication (1.3.6.1.5.5.7.3.2)
- Code Signing (1.3.6.1.5.5.7.3.3)
- Email Protection (1.3.6.1.5.5.7.3.4)
- Time Stamping (1.3.6.1.5.5.7.3.8)
```

**Authority Information Access (AIA)**:
```
- OCSP: http://ocsp.letsencrypt.org
- CA Issuers: http://cert.letsencrypt.org/letsencryptauthorityx3.der
```

**CRL Distribution Points**:
```
URI: http://crl.example.com/crl.pem
```

### Viewing Certificates

**OpenSSL**:
```bash
# View certificate details
openssl x509 -in cert.pem -text -noout

# View specific fields
openssl x509 -in cert.pem -noout -subject
openssl x509 -in cert.pem -noout -issuer
openssl x509 -in cert.pem -noout -dates
openssl x509 -in cert.pem -noout -serial

# View SANs
openssl x509 -in cert.pem -noout -ext subjectAltName

# View from remote server
echo | openssl s_client -connect example.com:443 2>/dev/null | \
    openssl x509 -text -noout
```

**Other Tools**:
```bash
# View with certutil (NSS)
certutil -L -d sql:$HOME/.pki/nssdb -n "example.com"

# View PKCS#12
openssl pkcs12 -in cert.p12 -info -noout
```

---

## Certificate Lifecycle

### 1. Key Generation

**RSA** (traditional):
```bash
# Generate 2048-bit RSA key (minimum)
openssl genrsa -out key.pem 2048

# Generate 3072-bit RSA key (recommended)
openssl genrsa -out key.pem 3072

# Generate 4096-bit RSA key (high security)
openssl genrsa -out key.pem 4096

# Generate encrypted key
openssl genrsa -aes256 -out key.pem 3072
```

**ECDSA** (modern, smaller keys):
```bash
# Generate P-256 key (equivalent to RSA-3072)
openssl ecparam -genkey -name prime256v1 -out key.pem

# Generate P-384 key (equivalent to RSA-7680)
openssl ecparam -genkey -name secp384r1 -out key.pem

# Generate P-521 key
openssl ecparam -genkey -name secp521r1 -out key.pem
```

**Key Size Recommendations**:
```
RSA:
- Minimum: 2048 bits (deprecated soon)
- Recommended: 3072 bits
- High security: 4096 bits

ECDSA:
- Recommended: P-256 (256 bits)
- High security: P-384 (384 bits)
```

### 2. Certificate Signing Request (CSR)

**Generate CSR**:
```bash
# From existing key
openssl req -new -key key.pem -out csr.pem \
    -subj "/C=US/ST=California/L=SF/O=Example/CN=example.com"

# Generate key + CSR in one step
openssl req -new -newkey rsa:3072 -nodes -keyout key.pem -out csr.pem

# With SANs (using config file)
openssl req -new -key key.pem -out csr.pem -config san.conf
```

**SAN Configuration** (`san.conf`):
```ini
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req

[req_distinguished_name]
CN = example.com

[v3_req]
subjectAltName = @alt_names

[alt_names]
DNS.1 = example.com
DNS.2 = www.example.com
DNS.3 = *.api.example.com
IP.1 = 192.0.2.1
```

**View CSR**:
```bash
openssl req -in csr.pem -text -noout
```

### 3. Certificate Issuance

**Self-Signed Certificate** (development only):
```bash
# Generate self-signed cert (1 year)
openssl req -x509 -new -nodes -key key.pem -days 365 -out cert.pem

# With SANs
openssl req -x509 -new -nodes -key key.pem -days 365 \
    -out cert.pem -extensions v3_req -config san.conf
```

**CA-Signed Certificate**:
```bash
# Submit CSR to CA (Let's Encrypt, DigiCert, etc.)
# CA validates domain ownership
# CA signs CSR and returns certificate
```

### 4. Deployment

**Nginx**:
```nginx
server {
    listen 443 ssl http2;
    server_name example.com;

    ssl_certificate /etc/ssl/certs/fullchain.pem;  # cert + intermediate
    ssl_certificate_key /etc/ssl/private/key.pem;
    ssl_trusted_certificate /etc/ssl/certs/chain.pem;  # for OCSP stapling
}
```

**Apache**:
```apache
<VirtualHost *:443>
    SSLEngine on
    SSLCertificateFile /etc/ssl/certs/cert.pem
    SSLCertificateKeyFile /etc/ssl/private/key.pem
    SSLCertificateChainFile /etc/ssl/certs/chain.pem
</VirtualHost>
```

**HAProxy**:
```
bind :443 ssl crt /etc/ssl/certs/example.com.pem
# example.com.pem contains: cert + key + intermediates
```

### 5. Monitoring

**Track Expiration**:
```bash
# Days until expiry
openssl x509 -in cert.pem -noout -enddate | \
    awk -F= '{print $2}' | xargs -I {} date -d {} +%s | \
    awk -v now=$(date +%s) '{print int(($1-now)/86400)}'

# Check remote certificate
echo | openssl s_client -connect example.com:443 2>/dev/null | \
    openssl x509 -noout -dates
```

**Alerts**:
- Alert at 30 days before expiry
- Critical alert at 14 days
- Emergency alert at 7 days

### 6. Renewal

**Before Expiry**:
- Renew 30+ days before expiration
- Let's Encrypt: 90-day lifetime, renew at 60 days
- Commercial CAs: 1-year lifetime, renew at ~30 days

**Renewal Process**:
```bash
# Automated (certbot)
certbot renew --quiet

# Manual
# 1. Generate new CSR (can reuse key or generate new)
# 2. Submit to CA
# 3. Deploy new certificate
# 4. Reload server
```

### 7. Rotation

**Zero-Downtime Rotation**:
```bash
# 1. Obtain new certificate
certbot certonly --webroot -w /var/www/html -d example.com

# 2. Backup old certificate
cp /etc/ssl/certs/example.com.crt /backup/

# 3. Deploy new certificate
cp /etc/letsencrypt/live/example.com/fullchain.pem /etc/ssl/certs/

# 4. Test configuration
nginx -t

# 5. Reload (no downtime)
systemctl reload nginx

# 6. Verify
curl -vI https://example.com 2>&1 | grep "expire date"
```

### 8. Revocation (if compromised)

**When to Revoke**:
- Private key compromised
- Certificate issued with incorrect information
- Certificate no longer needed
- Key material suspected to be weak

**Revocation Process**:
```bash
# Let's Encrypt
certbot revoke --cert-name example.com

# Manual (if you have cert + key)
certbot revoke --cert-path /path/to/cert.pem

# Specify reason
certbot revoke --cert-path /path/to/cert.pem --reason keyCompromise
```

---

## Certificate Authority Hierarchies

### CA Hierarchy Structure

```
Root CA (offline, highly secured)
  ├─ Intermediate CA 1 (online, issues certs)
  │   ├─ End-Entity Cert 1
  │   └─ End-Entity Cert 2
  └─ Intermediate CA 2
      ├─ End-Entity Cert 3
      └─ End-Entity Cert 4
```

**Why Intermediates?**
- Protect root CA (keep offline)
- Limit blast radius if intermediate compromised
- Different intermediates for different purposes
- Easier to revoke intermediate than root

### Public CAs

**Let's Encrypt**:
- Free, automated
- 90-day certificate lifetime
- Domain Validation (DV) only
- Rate limits apply

**DigiCert**:
- Commercial CA
- DV, OV (Organization Validation), EV (Extended Validation)
- 1-year maximum lifetime
- Premium support

**Sectigo (formerly Comodo)**:
- Commercial CA
- DV, OV, EV certificates
- Code signing, email certificates

**GlobalSign**:
- Commercial CA
- Enterprise PKI solutions
- IoT certificates

### Private CAs

**Use Cases**:
- Internal services (mTLS between microservices)
- Development/testing environments
- IoT device authentication
- VPN certificates

**Options**:
1. **OpenSSL** (manual)
2. **CFSSL** (Cloudflare's PKI toolkit)
3. **HashiCorp Vault** (automated PKI)
4. **AWS Certificate Manager Private CA**
5. **Smallstep** (step-ca)

### Building a Private CA with OpenSSL

**Root CA**:
```bash
# Generate root CA key (keep offline!)
openssl genrsa -aes256 -out root-ca.key 4096

# Generate root CA certificate (10 years)
openssl req -x509 -new -nodes -key root-ca.key -sha256 -days 3650 \
    -out root-ca.crt -subj "/CN=My Root CA"
```

**Intermediate CA**:
```bash
# Generate intermediate CA key
openssl genrsa -aes256 -out intermediate-ca.key 3072

# Generate intermediate CA CSR
openssl req -new -key intermediate-ca.key -out intermediate-ca.csr \
    -subj "/CN=My Intermediate CA"

# Sign intermediate CA with root CA
openssl x509 -req -in intermediate-ca.csr -CA root-ca.crt \
    -CAkey root-ca.key -CAcreateserial -out intermediate-ca.crt \
    -days 1825 -sha256 -extfile intermediate-extensions.conf
```

**Intermediate Extensions** (`intermediate-extensions.conf`):
```ini
basicConstraints = critical, CA:TRUE, pathlen:0
keyUsage = critical, digitalSignature, cRLSign, keyCertSign
```

**Issue End-Entity Certificate**:
```bash
# Generate server key + CSR
openssl req -new -newkey rsa:2048 -nodes -keyout server.key \
    -out server.csr -subj "/CN=example.com"

# Sign with intermediate CA
openssl x509 -req -in server.csr -CA intermediate-ca.crt \
    -CAkey intermediate-ca.key -CAcreateserial -out server.crt \
    -days 365 -sha256 -extfile server-extensions.conf
```

**Server Extensions** (`server-extensions.conf`):
```ini
basicConstraints = CA:FALSE
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = example.com
DNS.2 = www.example.com
```

**Create Certificate Chain**:
```bash
# Combine server cert + intermediate
cat server.crt intermediate-ca.crt > fullchain.pem
```

---

## ACME Protocol

### Overview

**ACME (Automatic Certificate Management Environment)** is a protocol for automating certificate issuance and renewal (RFC 8555).

**Key Features**:
- Fully automated (no human intervention)
- Domain validation challenges
- Automatic renewal
- Standardized protocol

**ACME Flow**:
```
1. Account Registration
   Client → ACME Server: Register account

2. Order Creation
   Client → ACME Server: Request certificate for domain(s)

3. Authorization Challenges
   ACME Server → Client: Provide challenge(s)
   Client: Complete challenge (HTTP-01, DNS-01, TLS-ALPN-01)
   ACME Server: Verify challenge

4. Certificate Issuance
   Client → ACME Server: Submit CSR
   ACME Server → Client: Return signed certificate

5. Renewal (before expiry)
   Repeat steps 2-4
```

### Challenge Types

**HTTP-01 Challenge**:
```
1. ACME server provides token
2. Client creates file: .well-known/acme-challenge/{token}
3. ACME server fetches: http://example.com/.well-known/acme-challenge/{token}
4. File contains key authorization
5. Validation passes if content matches
```

**Pros**:
- Easy to automate
- Works with standard web servers
- No DNS API required

**Cons**:
- Requires port 80 open
- No wildcard certificates
- Must be publicly accessible

**DNS-01 Challenge**:
```
1. ACME server provides token
2. Client creates TXT record: _acme-challenge.example.com
3. ACME server queries DNS for TXT record
4. Validation passes if record matches
```

**Pros**:
- Supports wildcard certificates
- No need for port 80
- Works for internal servers

**Cons**:
- Requires DNS API access
- DNS propagation delay
- More complex to automate

**TLS-ALPN-01 Challenge**:
```
1. ACME server provides token
2. Client configures TLS server with special certificate
3. ACME server connects on port 443 with ALPN protocol
4. Validation passes if special certificate present
```

**Pros**:
- Works on port 443 (no port 80 needed)
- Fast validation

**Cons**:
- Requires TLS server modification
- Not widely supported

### ACME Clients

**Certbot** (EFF):
- Official ACME client
- Python-based
- Plugins for Apache, Nginx
- Most popular

**acme.sh**:
- Shell script (minimal dependencies)
- Supports many DNS providers
- Lightweight, fast

**Caddy**:
- Web server with built-in ACME
- Automatic HTTPS
- No configuration needed

**cert-manager**:
- Kubernetes native
- Automatic certificate management in K8s
- Supports multiple issuers

**Traefik**:
- Reverse proxy with built-in ACME
- Automatic certificate provisioning
- Docker/K8s integration

---

## Let's Encrypt

### Overview

**Let's Encrypt** is a free, automated, open Certificate Authority using ACME protocol.

**Key Facts**:
- **Lifetime**: 90 days (encourages automation)
- **Rate Limits**: 50 certs/domain/week, 5 duplicates/week
- **Validation**: DV (Domain Validation) only
- **Wildcard Support**: Yes (via DNS-01 challenge)
- **Cost**: Free
- **Launch**: 2016

### Rate Limits

**Certificates per Registered Domain**: 50/week
```
example.com, www.example.com, api.example.com count as same domain
Can issue 50 certificates for example.com per week
```

**Duplicate Certificates**: 5/week
```
Same set of names (ignoring order)
example.com + www.example.com is duplicate of previous cert with same names
```

**New Orders**: 300/account/3 hours
```
Creating new orders (not completed certificates)
```

**Failed Validations**: 5/account/hostname/hour
```
Failed ACME challenges
```

**Mitigation**:
- Use staging environment for testing
- Batch certificate requests
- Use wildcard certificates when appropriate

### Staging Environment

**Staging ACME URL**:
```
https://acme-staging-v02.api.letsencrypt.org/directory
```

**Usage**:
```bash
# Certbot staging
certbot --staging -d example.com

# acme.sh staging
acme.sh --issue --staging -d example.com -w /var/www/html

# Always test with staging first to avoid rate limits!
```

### Trust Chain

**Current Chain** (2024+):
```
ISRG Root X1 (RSA)
  └─ Let's Encrypt R3 (RSA intermediate)
      └─ Your Certificate

ISRG Root X2 (ECDSA)
  └─ Let's Encrypt E1 (ECDSA intermediate)
      └─ Your Certificate
```

**Compatibility**:
- ISRG Root X1: Trusted by all modern browsers/OS
- Old Android (<7.1): May need alternate chain

---

## Certificate Automation

### Certbot

**Installation**:
```bash
# Ubuntu/Debian
sudo apt install certbot python3-certbot-nginx

# RHEL/CentOS
sudo yum install certbot python3-certbot-nginx

# macOS
brew install certbot

# Docker
docker run -it --rm -v /etc/letsencrypt:/etc/letsencrypt certbot/certbot
```

**Basic Usage**:
```bash
# Obtain certificate (webroot)
certbot certonly --webroot -w /var/www/html -d example.com -d www.example.com

# Obtain + install (Nginx)
certbot --nginx -d example.com -d www.example.com

# Wildcard certificate (DNS challenge)
certbot certonly --manual --preferred-challenges dns -d '*.example.com' -d example.com

# List certificates
certbot certificates

# Renew all certificates
certbot renew

# Test renewal
certbot renew --dry-run

# Revoke certificate
certbot revoke --cert-name example.com
```

**Automation**:
```bash
# Cron job (runs twice daily)
0 0,12 * * * certbot renew --quiet --post-hook "systemctl reload nginx"

# Systemd timer (preferred)
sudo systemctl enable certbot-renew.timer
sudo systemctl start certbot-renew.timer
```

**Hooks**:
```bash
# Pre-hook (before renewal)
certbot renew --pre-hook "systemctl stop nginx"

# Post-hook (after successful renewal)
certbot renew --post-hook "systemctl reload nginx"

# Deploy-hook (after certificate deployed)
certbot renew --deploy-hook "systemctl reload nginx && /scripts/notify.sh"
```

### acme.sh

**Installation**:
```bash
⚠️ **SECURITY**: Piping curl to shell is dangerous. For production:
```bash
# Download script first
curl -O https://get.acme.sh
# Verify checksum
sha256sum get.acme.sh
# Review content
less get.acme.sh
# Then execute
bash get.acme.sh
source ~/.bashrc
```
For development/learning only:
```bash
curl https://get.acme.sh | sh
source ~/.bashrc
```

**Basic Usage**:
```bash
# HTTP validation (standalone)
acme.sh --issue --standalone -d example.com -d www.example.com

# HTTP validation (webroot)
acme.sh --issue -d example.com -w /var/www/html

# DNS validation (Cloudflare)
export CF_Token="your-cloudflare-api-token"  # Placeholder - replace with actual API token from Cloudflare dashboard
acme.sh --issue --dns dns_cf -d example.com -d '*.example.com'

# DNS validation (AWS Route53)
export AWS_ACCESS_KEY_ID="your-key-id"
export AWS_SECRET_ACCESS_KEY="your-secret"
acme.sh --issue --dns dns_aws -d example.com

# Install certificate
acme.sh --install-cert -d example.com \
    --key-file /etc/ssl/private/example.com.key \
    --fullchain-file /etc/ssl/certs/example.com.crt \
    --reloadcmd "systemctl reload nginx"

# Upgrade ACME version
acme.sh --upgrade --auto-upgrade

# Force renewal
acme.sh --renew -d example.com --force
```

**Auto-Renewal**:
```bash
# Installed as cron job automatically
# Runs daily, renews certs < 60 days from expiry
# View cron:
crontab -l | grep acme.sh
```

**DNS Providers**:
```bash
# acme.sh supports 100+ DNS providers
# Cloudflare, AWS Route53, Google Cloud DNS, Azure DNS, etc.

# List all supported providers
acme.sh --list-dns-providers

# Example: Cloudflare
export CF_Token="your-token"
acme.sh --issue --dns dns_cf -d example.com

# Example: GoDaddy
export GD_Key="your-key"
export GD_Secret="your-secret"
acme.sh --issue --dns dns_gd -d example.com
```

---

## Kubernetes cert-manager

### Overview

**cert-manager** is a Kubernetes add-on that automates certificate management.

**Features**:
- Automatic certificate issuance and renewal
- Support for multiple CAs (Let's Encrypt, Vault, Venafi, self-signed)
- Native Kubernetes integration
- Certificate CR (Custom Resource)

### Installation

**Using kubectl**:
```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
```

**Using Helm**:
```bash
helm repo add jetstack https://charts.jetstack.io
helm repo update

helm install cert-manager jetstack/cert-manager \
    --namespace cert-manager \
    --create-namespace \
    --version v1.13.0 \
    --set installCRDs=true
```

**Verify Installation**:
```bash
kubectl get pods -n cert-manager

# Should see:
# cert-manager-xxxxx
# cert-manager-cainjector-xxxxx
# cert-manager-webhook-xxxxx
```

### Issuers

**ClusterIssuer** (cluster-wide):
```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@example.com
    privateKeySecretRef:
      name: letsencrypt-prod-account-key
    solvers:
    - http01:
        ingress:
          class: nginx
```

**DNS-01 Solver** (for wildcards):
```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-dns
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@example.com
    privateKeySecretRef:
      name: letsencrypt-dns-account-key
    solvers:
    - dns01:
        cloudflare:
          email: admin@example.com
          apiTokenSecretRef:
            name: cloudflare-api-token
            key: api-token
```

**Staging Issuer**:
```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-staging
spec:
  acme:
    server: https://acme-staging-v02.api.letsencrypt.org/directory
    email: admin@example.com
    privateKeySecretRef:
      name: letsencrypt-staging-account-key
    solvers:
    - http01:
        ingress:
          class: nginx
```

**Private CA Issuer**:
```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: private-ca
spec:
  ca:
    secretName: ca-key-pair
```

### Certificate Resources

**Manual Certificate**:
```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: example-com-tls
  namespace: default
spec:
  secretName: example-com-tls
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
  - example.com
  - www.example.com
  privateKey:
    algorithm: RSA
    size: 2048
```

**Wildcard Certificate**:
```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: wildcard-example-com
  namespace: default
spec:
  secretName: wildcard-example-com-tls
  issuerRef:
    name: letsencrypt-dns
    kind: ClusterIssuer
  dnsNames:
  - '*.example.com'
  - example.com
```

**Ingress Annotation** (automatic):
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: example-ingress
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - example.com
    - www.example.com
    secretName: example-com-tls
  rules:
  - host: example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: example-service
            port:
              number: 80
```

### Certificate Lifecycle

**Check Status**:
```bash
# View certificates
kubectl get certificates -A

# Describe certificate
kubectl describe certificate example-com-tls

# View certificate secret
kubectl get secret example-com-tls -o yaml

# Check certificate expiry
kubectl get certificate example-com-tls -o jsonpath='{.status.notAfter}'
```

**Force Renewal**:
```bash
# Delete secret to trigger renewal
kubectl delete secret example-com-tls

# Or annotate certificate
kubectl annotate certificate example-com-tls \
    cert-manager.io/issue-temporary-certificate="true" --overwrite
```

**Troubleshooting**:
```bash
# View cert-manager logs
kubectl logs -n cert-manager deploy/cert-manager

# View certificate events
kubectl describe certificate example-com-tls

# View challenge status (ACME)
kubectl get challenges
kubectl describe challenge example-com-tls-xxxxx

# View order status
kubectl get orders
kubectl describe order example-com-tls-xxxxx
```

---

## Mutual TLS (mTLS)

### Overview

**Mutual TLS** is when both client and server authenticate each other using certificates.

**Standard TLS**:
```
Client → Server: Verify server certificate
```

**mTLS**:
```
Client → Server: Verify server certificate
Client ← Server: Request client certificate
Client → Server: Send client certificate
Server: Verify client certificate
```

**Use Cases**:
- Microservice authentication (service-to-service)
- API authentication (instead of API keys)
- Zero-trust networks
- IoT device authentication

### Server Configuration

**Nginx**:
```nginx
server {
    listen 443 ssl;
    server_name api.example.com;

    # Server certificate
    ssl_certificate /etc/ssl/certs/server.crt;
    ssl_certificate_key /etc/ssl/private/server.key;

    # Client certificate verification
    ssl_client_certificate /etc/ssl/certs/ca.crt;
    ssl_verify_client on;
    ssl_verify_depth 2;

    location / {
        # Client certificate info available
        proxy_set_header X-Client-Cert-DN $ssl_client_s_dn;
        proxy_set_header X-Client-Cert-Serial $ssl_client_serial;
        proxy_pass http://backend;
    }
}
```

**Optional Client Cert** (fallback to other auth):
```nginx
ssl_verify_client optional;

location / {
    if ($ssl_client_verify != SUCCESS) {
        # No valid client cert, require other auth
        return 401;
    }
}
```

**Apache**:
```apache
<VirtualHost *:443>
    SSLEngine on
    SSLCertificateFile /etc/ssl/certs/server.crt
    SSLCertificateKeyFile /etc/ssl/private/server.key

    # Client certificate verification
    SSLCACertificateFile /etc/ssl/certs/ca.crt
    SSLVerifyClient require
    SSLVerifyDepth 2

    <Location />
        # Client cert info in environment variables
        # SSL_CLIENT_S_DN, SSL_CLIENT_SERIAL, etc.
    </Location>
</VirtualHost>
```

### Client Configuration

**curl**:
```bash
curl --cert client.crt --key client.key --cacert ca.crt https://api.example.com
```

**Python**:
```python
import requests

response = requests.get(
    'https://api.example.com',
    cert=('client.crt', 'client.key'),
    verify='ca.crt'
)
```

**Go**:
```go
package main

import (
    "crypto/tls"
    "crypto/x509"
    "io/ioutil"
    "net/http"
)

func main() {
    // Load client cert
    cert, err := tls.LoadX509KeyPair("client.crt", "client.key")
    if err != nil {
        panic(err)
    }

    // Load CA cert
    caCert, err := ioutil.ReadFile("ca.crt")
    if err != nil {
        panic(err)
    }
    caCertPool := x509.NewCertPool()
    caCertPool.AppendCertsFromPEM(caCert)

    tlsConfig := &tls.Config{
        Certificates: []tls.Certificate{cert},
        RootCAs:      caCertPool,
    }

    client := &http.Client{
        Transport: &http.Transport{
            TLSClientConfig: tlsConfig,
        },
    }

    resp, err := client.Get("https://api.example.com")
    if err != nil {
        panic(err)
    }
    defer resp.Body.Close()
}
```

### Kubernetes mTLS (Service Mesh)

**Istio**:
```yaml
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: default
spec:
  mtls:
    mode: STRICT  # Require mTLS for all traffic
```

**Linkerd**:
```bash
# Install Linkerd with mTLS enabled by default
linkerd install | kubectl apply -f -

# Inject mTLS sidecar
kubectl get deploy -o yaml | linkerd inject - | kubectl apply -f -
```

---

## Certificate Revocation

### Why Revoke Certificates?

- Private key compromised
- Certificate issued with incorrect information
- Certificate no longer needed
- CA compromise
- Affiliation change

### Certificate Revocation List (CRL)

**CRL** is a list of revoked certificate serial numbers published by CA.

**CRL Structure**:
```
CRL = {
  Issuer: CA that issued this CRL
  This Update: 2025-01-01
  Next Update: 2025-01-02
  Revoked Certificates: [
    {Serial: 123456, Revocation Date: 2025-01-01, Reason: keyCompromise},
    {Serial: 789012, Revocation Date: 2025-01-01, Reason: superseded}
  ]
  Signature: CA signature
}
```

**Download CRL**:
```bash
# Extract CRL URL from certificate
openssl x509 -in cert.pem -noout -ext crlDistributionPoints

# Download CRL
wget http://crl.example.com/crl.pem

# View CRL
openssl crl -in crl.pem -text -noout
```

**Check if Certificate Revoked**:
```bash
# Verify certificate against CRL
openssl verify -crl_check -CRLfile crl.pem -CAfile ca.crt cert.pem
```

**Limitations**:
- CRL can be large (millions of serial numbers)
- Must download entire CRL
- Stale data (CRL updated periodically)
- Privacy issue (reveals which sites you visit)

### Online Certificate Status Protocol (OCSP)

**OCSP** provides real-time certificate status checking.

**OCSP Request**:
```
Client → OCSP Responder: Is certificate serial 123456 valid?
OCSP Responder → Client: Good | Revoked | Unknown
```

**Check OCSP**:
```bash
# Extract OCSP URL from certificate
openssl x509 -in cert.pem -noout -ocsp_uri

# Check OCSP status
openssl ocsp -issuer ca.crt -cert cert.pem \
    -url http://ocsp.letsencrypt.org -resp_text
```

**OCSP Response**:
```
OCSP Response Status: successful (0x0)
Response Type: Basic OCSP Response
Certificate ID:
  Hash Algorithm: sha1
  Issuer Name Hash: ...
  Issuer Key Hash: ...
  Serial Number: 123456
Cert Status: good
This Update: Jan  1 00:00:00 2025 GMT
Next Update: Jan  8 00:00:00 2025 GMT
```

**OCSP Stapling**:
```
Server periodically fetches OCSP response
Server "staples" OCSP response to TLS handshake
Client receives certificate + OCSP response together
No need for client to contact OCSP responder
```

**Enable OCSP Stapling** (Nginx):
```nginx
ssl_stapling on;
ssl_stapling_verify on;
ssl_trusted_certificate /etc/ssl/certs/chain.pem;
```

**Verify OCSP Stapling**:
```bash
echo | openssl s_client -connect example.com:443 -status 2>&1 | grep "OCSP"
```

### OCSP Must-Staple

**Must-Staple** extension forces server to provide OCSP response.

**Benefits**:
- Prevents OCSP soft-fail attacks
- Guarantees fresh revocation status

**Risks**:
- If OCSP responder down, site becomes unavailable
- Not widely used

**Request Must-Staple Certificate**:
```bash
# CSR with must-staple extension
openssl req -new -key key.pem -out csr.pem \
    -reqexts SAN -config <(cat /etc/ssl/openssl.cnf \
    <(printf "[SAN]\nsubjectAltName=DNS:example.com\n1.3.6.1.5.5.7.1.24=DER:30:03:02:01:05"))
```

---

## Certificate Transparency

### Overview

**Certificate Transparency (CT)** is a public log of all issued certificates.

**Goals**:
- Detect mis-issued certificates
- Detect malicious CAs
- Monitor certificate issuance for your domains

**How It Works**:
```
1. CA issues certificate
2. CA submits certificate to CT logs
3. CT log returns Signed Certificate Timestamp (SCT)
4. CA includes SCT in certificate or TLS handshake
5. Browser verifies SCT
```

**SCT Delivery Methods**:
- Embedded in certificate (X.509 extension)
- TLS extension (during handshake)
- OCSP stapling

### CT Logs

**Major CT Logs**:
- Google: logs.google.com
- Cloudflare: cloudflare.com/ssl/cert-transparency
- DigiCert: digicert.com/ct

**View CT Logs**:
```bash
# crt.sh (web search)
https://crt.sh/?q=example.com

# certstream (real-time monitoring)
pip install certstream
python -m certstream
```

### Monitoring with CT Logs

**Monitor for Unauthorized Certificates**:
```python
import certstream
import json

def callback(message, context):
    if message['message_type'] == "certificate_update":
        domains = message['data']['leaf_cert']['all_domains']
        if any('example.com' in d for d in domains):
            print(f"Certificate issued for: {domains}")

certstream.listen_for_events(callback)
```

**crt.sh API**:
```bash
# Search for certificates
curl -s "https://crt.sh/?q=example.com&output=json" | jq

# Monitor for new certificates
curl -s "https://crt.sh/?q=example.com&output=json" | \
    jq -r '.[].common_name' | sort -u
```

**Benefits**:
- Detect unauthorized certificate issuance
- Discover subdomains
- Audit certificate practices
- Incident response

---

## Certificate Pinning

### Overview

**Certificate Pinning** is hardcoding expected certificate (or public key) in client application.

**Purpose**:
- Prevent man-in-the-middle attacks
- Prevent rogue CA from issuing valid certificate
- Additional security layer

**Types**:
1. **Certificate Pinning**: Pin entire certificate
2. **Public Key Pinning**: Pin public key only (survives cert renewal)
3. **CA Pinning**: Pin CA certificate

### Implementation

**Pin Certificate** (iOS):
```swift
let url = URL(string: "https://api.example.com")!
let pinnedCertData = Data(contentsOf: Bundle.main.url(forResource: "cert", withExtension: "der")!)

let session = URLSession(configuration: .default, delegate: self, delegateQueue: nil)

func urlSession(_ session: URLSession, didReceive challenge: URLAuthenticationChallenge,
                completionHandler: @escaping (URLSession.AuthChallengeDisposition, URLCredential?) -> Void) {
    guard let serverTrust = challenge.protectionSpace.serverTrust,
          let certificate = SecTrustGetCertificateAtIndex(serverTrust, 0) else {
        completionHandler(.cancelAuthenticationChallenge, nil)
        return
    }

    let serverCertData = SecCertificateCopyData(certificate) as Data
    if serverCertData == pinnedCertData {
        completionHandler(.useCredential, URLCredential(trust: serverTrust))
    } else {
        completionHandler(.cancelAuthenticationChallenge, nil)
    }
}
```

**Pin Public Key** (Android):
```java
// Compute SHA-256 hash of public key
String publicKeyHash = "sha256/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=";

CertificatePinner certificatePinner = new CertificatePinner.Builder()
    .add("api.example.com", publicKeyHash)
    .build();

OkHttpClient client = new OkHttpClient.Builder()
    .certificatePinner(certificatePinner)
    .build();
```

**HTTP Public Key Pinning (HPKP)** (deprecated):
```
Public-Key-Pins:
  pin-sha256="base64==";
  pin-sha256="backup-base64==";
  max-age=5184000;
  includeSubDomains
```

**HPKP Issues**:
- Bricking risk (pin wrong key → site inaccessible)
- Difficult to recover
- Deprecated in browsers

### Best Practices

**Do**:
- Pin backup keys (for rotation)
- Use public key pinning (not cert pinning)
- Test thoroughly before deploying
- Have revocation mechanism

**Don't**:
- Pin only one key (no rotation path)
- Use HPKP (deprecated)
- Pin without testing

**Extract Public Key Hash** (for pinning):
```bash
# Extract public key
openssl x509 -in cert.pem -pubkey -noout > pubkey.pem

# Compute SHA-256 hash
openssl pkey -pubin -in pubkey.pem -outform DER | \
    openssl dgst -sha256 -binary | \
    base64
```

---

## Monitoring and Alerting

### What to Monitor

**Certificate Expiry**:
- Days until expiration
- Alert at 30, 14, 7, 1 days

**Certificate Validity**:
- Valid chain
- Not revoked (OCSP/CRL)
- Matches expected subject/SANs

**Certificate Deployment**:
- Certificate deployed on all servers
- Consistent across load balancers

**Certificate Health**:
- Key size (minimum 2048-bit RSA)
- Signature algorithm (SHA-256+)
- No weak ciphers

### Monitoring Tools

**Prometheus + ssl_exporter**:
```yaml
# Prometheus scrape config
scrape_configs:
  - job_name: 'ssl'
    metrics_path: /probe
    static_configs:
      - targets:
        - example.com:443
        - api.example.com:443
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: ssl-exporter:9219
```

**Alert Rules**:
```yaml
groups:
- name: certificates
  rules:
  - alert: CertificateExpiringSoon
    expr: ssl_cert_not_after - time() < 86400 * 30
    for: 1h
    labels:
      severity: warning
    annotations:
      summary: "Certificate expiring in < 30 days"
      description: "Certificate for {{ $labels.instance }} expires in {{ $value | humanizeDuration }}"

  - alert: CertificateExpiringSoonCritical
    expr: ssl_cert_not_after - time() < 86400 * 7
    for: 1h
    labels:
      severity: critical
    annotations:
      summary: "Certificate expiring in < 7 days"
      description: "Certificate for {{ $labels.instance }} expires in {{ $value | humanizeDuration }}"

  - alert: CertificateInvalid
    expr: ssl_cert_verify_error == 1
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "Certificate validation failed"
      description: "Certificate for {{ $labels.instance }} failed validation"
```

**Blackbox Exporter**:
```yaml
modules:
  https_2xx:
    prober: http
    http:
      valid_status_codes: [200]
      fail_if_ssl: false
      fail_if_not_ssl: true
      tls_config:
        insecure_skip_verify: false
```

**Nagios/Icinga**:
```bash
# check_ssl_cert plugin
check_ssl_cert -H example.com -w 30 -c 7
```

**Custom Script** (simple):
```bash
#!/bin/bash
DAYS_WARNING=30
DAYS_CRITICAL=7

DOMAIN="example.com"
EXPIRY_DATE=$(echo | openssl s_client -connect $DOMAIN:443 2>/dev/null | \
    openssl x509 -noout -enddate | cut -d= -f2)

EXPIRY_EPOCH=$(date -d "$EXPIRY_DATE" +%s)
NOW_EPOCH=$(date +%s)
DAYS_REMAINING=$(( ($EXPIRY_EPOCH - $NOW_EPOCH) / 86400 ))

if [ $DAYS_REMAINING -lt $DAYS_CRITICAL ]; then
    echo "CRITICAL: Certificate expires in $DAYS_REMAINING days"
    exit 2
elif [ $DAYS_REMAINING -lt $DAYS_WARNING ]; then
    echo "WARNING: Certificate expires in $DAYS_REMAINING days"
    exit 1
else
    echo "OK: Certificate expires in $DAYS_REMAINING days"
    exit 0
fi
```

### Certificate Inventory

**Track All Certificates**:
```
Domain          | Expiry      | Issuer          | SANs
----------------|-------------|-----------------|------------------
example.com     | 2025-03-01  | Let's Encrypt   | example.com, www
api.example.com | 2025-02-15  | Let's Encrypt   | api.example.com
*.internal      | 2025-06-01  | Private CA      | *.internal
```

**Automated Discovery**:
```bash
# Scan all domains
for domain in $(cat domains.txt); do
    echo "Checking $domain..."
    echo | openssl s_client -connect $domain:443 2>/dev/null | \
        openssl x509 -noout -subject -dates -issuer
done
```

---

## Best Practices

### 1. Certificate Lifetime

**Recommended**:
- Let's Encrypt: 90 days (renew at 60 days)
- Commercial: 1 year maximum
- Internal: 1 year or less

**Why Short Lifetimes?**
- Limit damage if compromised
- Encourage automation
- Easier to deprecate weak crypto

### 2. Key Management

**Best Practices**:
- Generate keys on secure system
- Protect private keys (chmod 600)
- Never commit keys to version control
- Use Hardware Security Module (HSM) for CA keys
- Rotate keys periodically

**Key Storage**:
```bash
# Correct permissions
chmod 600 /etc/ssl/private/key.pem
chown root:root /etc/ssl/private/key.pem

# Encrypt key at rest
openssl genrsa -aes256 -out key.pem 3072
```

### 3. Automation

**Automate Everything**:
- Certificate issuance
- Certificate renewal
- Certificate deployment
- Monitoring and alerting

**Why?**
- Human error causes most outages
- Consistent process
- No forgotten renewals
- Scalable

### 4. Monitoring

**Monitor Proactively**:
- Track expiration (30+ days before)
- Alert on validation failures
- Monitor CT logs for unauthorized certs
- Track certificate inventory

### 5. Testing

**Test Renewal Process**:
```bash
# Dry run renewal
certbot renew --dry-run

# Test in staging first
certbot --staging -d example.com

# Verify deployment
curl -vI https://example.com 2>&1 | grep "expire date"
```

### 6. Backup and Recovery

**Backup**:
- Private keys (encrypted)
- Certificates
- CA certificates
- Configuration files

**Recovery Plan**:
- Document renewal process
- Keep backup certificates ready
- Test recovery procedure

### 7. Certificate Revocation

**Revoke When**:
- Private key compromised
- Certificate mis-issued
- No longer needed

**How to Revoke**:
```bash
# Let's Encrypt
certbot revoke --cert-path /path/to/cert.pem --reason keyCompromise

# Report to CA
# Update CRL/OCSP
# Deploy new certificate
```

---

## Common Issues

### Issue 1: Certificate Expired

**Symptoms**:
- Browser shows "Your connection is not private"
- ERR_CERT_DATE_INVALID

**Cause**:
- Forgot to renew
- Renewal automation failed
- Wrong certificate deployed

**Fix**:
```bash
# Check expiration
openssl x509 -in cert.pem -noout -enddate

# Renew immediately
certbot renew --force-renewal --cert-name example.com

# Deploy new certificate
systemctl reload nginx
```

**Prevention**:
- Automated renewal
- Monitoring and alerting
- Renew 30+ days before expiry

### Issue 2: Certificate Chain Incomplete

**Symptoms**:
- Some clients can't connect
- SSL Labs shows "Chain issues"
- Mobile devices fail

**Cause**:
- Missing intermediate certificate
- Wrong certificate order

**Fix**:
```bash
# Check chain
openssl s_client -connect example.com:443 -showcerts

# Rebuild chain (correct order)
cat cert.pem intermediate.pem > fullchain.pem

# Deploy
cp fullchain.pem /etc/ssl/certs/
systemctl reload nginx
```

### Issue 3: Private Key Mismatch

**Symptoms**:
- Server fails to start
- SSL handshake errors

**Cause**:
- Certificate and key don't match
- Wrong key deployed

**Fix**:
```bash
# Verify certificate and key match
CERT_MODULUS=$(openssl x509 -noout -modulus -in cert.pem | openssl md5)
KEY_MODULUS=$(openssl rsa -noout -modulus -in key.pem | openssl md5)

if [ "$CERT_MODULUS" == "$KEY_MODULUS" ]; then
    echo "Match"
else
    echo "Mismatch!"
fi
```

### Issue 4: SAN Missing

**Symptoms**:
- Browser shows certificate error
- "Certificate name mismatch"

**Cause**:
- Certificate missing required SAN
- Accessing site with unlisted name

**Fix**:
```bash
# Check SANs
openssl x509 -in cert.pem -noout -ext subjectAltName

# Reissue with all required SANs
certbot certonly --cert-name example.com \
    -d example.com -d www.example.com -d api.example.com
```

### Issue 5: Rate Limit Hit

**Symptoms**:
- "too many certificates already issued" error
- Let's Encrypt rejects request

**Cause**:
- Exceeded 50 certs/domain/week
- Exceeded 5 duplicates/week

**Fix**:
```bash
# Wait for rate limit to reset (1 week)
# OR use wildcard certificate
certbot certonly --dns-cloudflare \
    -d '*.example.com' -d example.com

# OR use different domains
```

**Prevention**:
- Test with staging
- Use wildcard certs
- Batch requests

---

## Security Considerations

### 1. Private Key Protection

**Critical**:
- Private key compromise = total security failure
- Protect with file permissions (chmod 600)
- Never log private keys
- Never transmit unencrypted
- Use HSM for high-value keys

**Key Generation**:
```bash
# Generate on secure system (not shared/public)
openssl genrsa -out key.pem 3072

# Set restrictive permissions immediately
chmod 600 key.pem
chown root:root key.pem
```

### 2. Certificate Validation

**Always Validate**:
- Certificate not expired
- Certificate chain complete
- Certificate not revoked
- Hostname matches SAN
- Signature valid

**Client-Side**:
```python
import requests

# Good: Validate certificate
response = requests.get('https://example.com', verify=True)

# Bad: Disable validation (NEVER in production)
response = requests.get('https://example.com', verify=False)
```

### 3. Weak Cryptography

**Avoid**:
- RSA < 2048 bits
- SHA-1 signatures
- MD5 signatures
- Self-signed certs in production (unless private CA)

**Use**:
- RSA 3072+ or ECDSA P-256+
- SHA-256+ signatures
- CA-signed certificates

### 4. Certificate Transparency

**Monitor CT Logs**:
- Detect unauthorized issuance
- Audit certificate practices
- Incident response

### 5. Revocation

**Have Plan**:
- How to revoke quickly
- How to deploy new certificate
- Communication plan

---

## Compliance

### PCI-DSS

**Requirements**:
- Use strong cryptography (TLS 1.2+)
- Manage certificates securely
- Expire certificates annually (or less)
- Disable weak ciphers

**Certificate Requirements**:
- SHA-256+ signatures
- RSA 2048+ or ECDSA P-256+
- Valid chain to trusted CA

### HIPAA

**Requirements**:
- Protect ePHI in transit (TLS)
- Encryption of data at rest
- Access controls
- Audit logging

**Certificate Best Practices**:
- Strong encryption (TLS 1.2+)
- Certificate expiration monitoring
- Revocation capability
- Audit certificate access

### SOC 2

**Requirements**:
- Security controls
- Availability
- Confidentiality

**Certificate Controls**:
- Automated renewal
- Monitoring and alerting
- Documented procedures
- Access controls

### GDPR

**Requirements**:
- Protect personal data
- Encryption in transit
- Security by design

**Certificate Practices**:
- TLS for all personal data transmission
- Certificate validation
- Timely renewal

---

## Tools and Utilities

### OpenSSL

**Swiss Army Knife** of cryptography:
```bash
# Generate key
openssl genrsa -out key.pem 2048

# Generate CSR
openssl req -new -key key.pem -out csr.pem

# View certificate
openssl x509 -in cert.pem -text -noout

# Verify chain
openssl verify -CAfile ca.crt cert.pem

# Check remote certificate
openssl s_client -connect example.com:443
```

### Certbot

**Let's Encrypt automation**:
```bash
# Obtain certificate
certbot certonly --webroot -w /var/www/html -d example.com

# Renew
certbot renew

# List certificates
certbot certificates
```

### acme.sh

**Lightweight ACME client**:
```bash
# Issue certificate
acme.sh --issue -d example.com -w /var/www/html

# Install
acme.sh --install-cert -d example.com \
    --key-file /etc/ssl/private/key.pem \
    --fullchain-file /etc/ssl/certs/cert.pem
```

### step CLI

**Smallstep certificate tools**:
```bash
# View certificate
step certificate inspect cert.pem

# Verify certificate
step certificate verify cert.pem --roots ca.crt

# Create certificate
step certificate create example.com cert.pem key.pem \
    --profile leaf --ca ca.crt --ca-key ca.key
```

### cfssl

**Cloudflare PKI toolkit**:
```bash
# Generate CA
cfssl gencert -initca ca-csr.json | cfssljson -bare ca

# Sign certificate
cfssl sign -ca ca.pem -ca-key ca-key.pem csr.pem | cfssljson -bare cert
```

### cert-manager

**Kubernetes native**:
```bash
# Install
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Create issuer
kubectl apply -f issuer.yaml

# Check certificates
kubectl get certificates -A
```

### SSL Labs

**Online testing**:
```
https://www.ssllabs.com/ssltest/
```

**Grades**:
- A+: Perfect configuration
- A: Good configuration
- B: Acceptable with warnings
- C-F: Serious issues

### Nmap

**Certificate scanning**:
```bash
# Scan for SSL/TLS
nmap --script ssl-cert,ssl-enum-ciphers -p 443 example.com

# Check certificate expiration
nmap --script ssl-cert --script-args ssl-cert.expiration 30 example.com
```

### testssl.sh

**Comprehensive TLS testing**:
```bash
# Download
git clone https://github.com/drwetter/testssl.sh.git

# Run
./testssl.sh example.com

# JSON output
./testssl.sh --json example.com
```

---

## Summary

**Certificate Management** is critical for secure communication. Key takeaways:

1. **Automate Everything**: Use ACME/Let's Encrypt, cert-manager, certbot
2. **Monitor Proactively**: Track expiration, validate chains, alert early
3. **Protect Private Keys**: Restrictive permissions, never log/commit
4. **Use Short Lifetimes**: 90 days (Let's Encrypt) or 1 year maximum
5. **Validate Always**: Complete chain, not revoked, hostname matches
6. **Plan for Revocation**: Know how to revoke and deploy new cert quickly
7. **Monitor CT Logs**: Detect unauthorized issuance
8. **Test Renewals**: Dry-run, staging environment, verify deployment

**Certificate lifecycle**: Generate → Issue → Deploy → Monitor → Renew → Rotate → (Revoke if needed)

**Automation prevents outages**. Manual processes fail. Automate issuance, renewal, deployment, and monitoring.

---

**References**:
- RFC 5280: X.509 Public Key Infrastructure
- RFC 8555: ACME Protocol
- RFC 6960: OCSP
- RFC 6962: Certificate Transparency
- Let's Encrypt: https://letsencrypt.org/
- cert-manager: https://cert-manager.io/
- SSL Labs: https://www.ssllabs.com/

---

**End of Reference**
