---
name: cryptography-certificate-management
description: Certificate lifecycle management including rotation, renewal, monitoring, automation with Let's Encrypt and ACME
---

# Certificate Management

**Scope**: Certificate rotation, renewal, monitoring, Let's Encrypt, ACME protocol, automation
**Lines**: ~350
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Managing certificate expiration
- Automating certificate renewal
- Implementing Let's Encrypt
- Monitoring certificate health
- Rotating certificates
- Setting up ACME clients
- Handling certificate revocation
- Planning certificate infrastructure

## Certificate Lifecycle

```
1. Generation → Create private key and CSR
2. Issuance  → CA signs certificate
3. Deployment → Install on servers
4. Monitoring → Track expiration
5. Renewal   → Get new certificate before expiry
6. Rotation  → Replace old with new
7. Revocation → Invalidate if compromised (optional)
```

---

## Let's Encrypt & ACME

### Overview

**Let's Encrypt**:
- Free, automated certificate authority
- 90-day certificate lifetime
- ACME protocol for automation
- Rate limits apply

**ACME Protocol**:
```
1. Account creation
2. Domain validation (HTTP-01, DNS-01, TLS-ALPN-01)
3. Certificate request
4. Certificate issuance
5. Certificate renewal
```

### Certbot

**Installation**:
```bash
# Ubuntu/Debian
sudo apt install certbot python3-certbot-nginx

# macOS
brew install certbot
```

**HTTP-01 Challenge** (webroot):
```bash
# Obtain certificate
sudo certbot certonly --webroot \
    -w /var/www/html \
    -d example.com \
    -d www.example.com

# Certificates stored in:
# /etc/letsencrypt/live/example.com/fullchain.pem
# /etc/letsencrypt/live/example.com/privkey.pem
```

**Nginx plugin** (automatic):
```bash
# Obtain and install certificate
sudo certbot --nginx -d example.com -d www.example.com

# Certbot automatically:
# - Validates domain
# - Obtains certificate
# - Updates nginx config
# - Reloads nginx
```

**DNS-01 Challenge** (wildcards):
```bash
# For wildcard certificates
sudo certbot certonly --manual \
    --preferred-challenges dns \
    -d '*.example.com' \
    -d example.com

# Add TXT record to DNS:
# _acme-challenge.example.com → [provided value]
```

**Auto-renewal**:
```bash
# Test renewal
sudo certbot renew --dry-run

# Setup cron (or systemd timer)
0 0,12 * * * certbot renew --quiet --post-hook "systemctl reload nginx"
```

### acme.sh

**Alternative ACME client**:
```bash
# Install
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
```
For development/learning only:
```bash
curl https://get.acme.sh | sh

# Issue certificate (HTTP validation)
acme.sh --issue -d example.com -w /var/www/html

# Issue wildcard (DNS validation with Cloudflare)
export CF_Token="your-cloudflare-api-token"  # Placeholder - replace with actual API token from Cloudflare dashboard
acme.sh --issue --dns dns_cf -d example.com -d '*.example.com'

# Install certificate
acme.sh --install-cert -d example.com \
    --key-file /etc/ssl/private/example.com.key \
    --fullchain-file /etc/ssl/certs/example.com.crt \
    --reloadcmd "systemctl reload nginx"

# Auto-renewal (automatic after install)
acme.sh --cron
```

---

## Automation Patterns

### Pattern 1: Systemd Timer for Renewal

**Service file** (`/etc/systemd/system/certbot-renew.service`):
```ini
[Unit]
Description=Certbot Renewal

[Service]
Type=oneshot
ExecStart=/usr/bin/certbot renew --quiet --deploy-hook "systemctl reload nginx"
```

**Timer file** (`/etc/systemd/system/certbot-renew.timer`):
```ini
[Unit]
Description=Certbot Renewal Timer

[Timer]
OnCalendar=daily
RandomizedDelaySec=1h
Persistent=true

[Install]
WantedBy=timers.target
```

**Enable**:
```bash
sudo systemctl enable --now certbot-renew.timer
sudo systemctl list-timers certbot-renew.timer
```

### Pattern 2: Kubernetes cert-manager

**Install cert-manager**:
```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
```

**ClusterIssuer** (Let's Encrypt):
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
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
```

**Certificate resource**:
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
```

**Ingress annotation** (automatic):
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: example
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - example.com
    secretName: example-com-tls
  rules:
  - host: example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: example
            port:
              number: 80
```

### Pattern 3: Custom Automation Script

**Python renewal script**:
```python
#!/usr/bin/env python3
import subprocess
import ssl
import socket
from datetime import datetime, timedelta
import smtplib
from email.message import EmailMessage

def check_certificate_expiry(hostname, port=443):
    """Check days until certificate expires"""
    context = ssl.create_default_context()
    with socket.create_connection((hostname, port)) as sock:
        with context.wrap_socket(sock, server_hostname=hostname) as ssock:
            cert = ssock.getpeercert()
            not_after = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
            days_remaining = (not_after - datetime.now()).days
            return days_remaining

def renew_certificate(domain):
    """Renew certificate using certbot"""
    result = subprocess.run(
        ['certbot', 'renew', '--cert-name', domain, '--quiet'],
        capture_output=True,
        text=True
    )
    return result.returncode == 0

def send_alert(subject, body):
    """Send email alert"""
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = 'certbot@example.com'
    msg['To'] = 'admin@example.com'
    msg.set_content(body)

    with smtplib.SMTP('localhost') as s:
        s.send_message(msg)

def main():
    domains = ['example.com', 'api.example.com']

    for domain in domains:
        try:
            days = check_certificate_expiry(domain)
            print(f"{domain}: {days} days until expiry")

            # Renew if < 30 days remaining
            if days < 30:
                print(f"Renewing {domain}...")
                if renew_certificate(domain):
                    send_alert(
                        f"Certificate renewed: {domain}",
                        f"Successfully renewed certificate for {domain}"
                    )
                else:
                    send_alert(
                        f"Certificate renewal FAILED: {domain}",
                        f"Failed to renew certificate for {domain}"
                    )

            # Alert if < 14 days and renewal failed
            elif days < 14:
                send_alert(
                    f"Certificate expiring soon: {domain}",
                    f"Certificate for {domain} expires in {days} days"
                )

        except Exception as e:
            send_alert(
                f"Certificate check failed: {domain}",
                f"Error checking {domain}: {str(e)}"
            )

if __name__ == '__main__':
    main()
```

---

## Monitoring

### Check Expiration

**OpenSSL**:
```bash
# Check expiration date
echo | openssl s_client -connect example.com:443 2>/dev/null | \
    openssl x509 -noout -dates

# Days until expiry
echo | openssl s_client -connect example.com:443 2>/dev/null | \
    openssl x509 -noout -enddate | \
    awk -F= '{print $2}' | xargs -I {} date -d {} +%s | \
    awk -v now=$(date +%s) '{print int(($1-now)/86400)}'
```

**Prometheus Exporter**:
```yaml
# ssl_exporter
apiVersion: v1
kind: Service
metadata:
  name: ssl-exporter
spec:
  ports:
  - port: 9219
  selector:
    app: ssl-exporter
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ssl-exporter
spec:
  template:
    spec:
      containers:
      - name: ssl-exporter
        image: ribbybibby/ssl-exporter:latest
        args:
        - --config.file=/config/ssl-exporter.yaml
```

**Prometheus alert**:
```yaml
groups:
- name: certificates
  rules:
  - alert: CertificateExpiringSoon
    expr: ssl_cert_not_after - time() < 86400 * 30
    labels:
      severity: warning
    annotations:
      summary: "Certificate expiring in < 30 days"
      description: "Certificate for {{ $labels.instance }} expires in {{ $value | humanizeDuration }}"
```

### Monitoring Services

**SSL Labs API**:
```python
import requests
import time

def check_ssl_labs(domain):
    """Check SSL configuration with SSL Labs"""
    api_url = "https://api.ssllabs.com/api/v3/analyze"

    # Start scan
    requests.get(api_url, params={'host': domain, 'startNew': 'on'})

    # Poll for results
    while True:
        resp = requests.get(api_url, params={'host': domain}).json()
        if resp['status'] == 'READY':
            grade = resp['endpoints'][0]['grade']
            return grade
        time.sleep(30)

grade = check_ssl_labs('example.com')
print(f"SSL Labs grade: {grade}")
```

---

## Certificate Rotation

### Zero-Downtime Rotation

**Strategy**:
```
1. Obtain new certificate
2. Deploy new certificate alongside old
3. Update configuration to use new
4. Reload/restart services
5. Verify new certificate active
6. Remove old certificate
```

**Nginx example**:
```bash
# 1. Obtain new certificate
certbot certonly --webroot -w /var/www/html -d example.com

# 2. Test configuration
nginx -t

# 3. Reload nginx (no downtime)
systemctl reload nginx

# 4. Verify
echo | openssl s_client -connect example.com:443 2>/dev/null | \
    openssl x509 -noout -dates
```

### Multi-Server Rotation

**Ansible playbook**:
```yaml
---
- name: Rotate certificates
  hosts: webservers
  tasks:
    - name: Copy new certificate
      copy:
        src: "{{ item }}"
        dest: "/etc/ssl/certs/"
        mode: 0644
      loop:
        - example.com.crt
        - example.com-chain.crt

    - name: Copy private key
      copy:
        src: example.com.key
        dest: /etc/ssl/private/
        mode: 0600

    - name: Reload nginx
      systemd:
        name: nginx
        state: reloaded

    - name: Verify certificate
      shell: |
        echo | openssl s_client -connect localhost:443 2>/dev/null | \
        openssl x509 -noout -dates
      register: cert_check
      changed_when: false

    - name: Display certificate info
      debug:
        var: cert_check.stdout
```

---

## Best Practices

### 1. Renewal Window

```bash
# ✅ Good: Renew 30 days before expiry
if [ $days_remaining -lt 30 ]; then
    renew_certificate
fi

# ❌ Bad: Wait until last minute
if [ $days_remaining -lt 3 ]; then
    renew_certificate
fi
```

### 2. Monitoring

```bash
# ✅ Good: Multiple monitoring approaches
- Prometheus metrics
- Periodic checks
- Alert 30 days before expiry

# ❌ Bad: No monitoring
# (certificate expires, site goes down)
```

### 3. Backup Certificates

```bash
# ✅ Good: Backup before rotation
cp /etc/ssl/certs/example.com.crt /backup/
certbot renew

# ❌ Bad: No backup
certbot renew
# (if renewal fails, no fallback)
```

---

## Troubleshooting

### Issue 1: Rate Limits

**Let's Encrypt limits**:
```
- 50 certificates per domain per week
- 5 duplicate certificates per week
- 300 new orders per account per 3 hours
```

**Solution**: Use staging environment for testing
```bash
certbot --staging -d example.com
```

### Issue 2: Renewal Failure

**Check renewal status**:
```bash
certbot certificates
```

**Common issues**:
- Webroot path wrong
- DNS not propagated (DNS-01)
- Firewall blocking (HTTP-01)
- Rate limit exceeded

**Debug**:
```bash
certbot renew --dry-run --debug
```

---

## Related Skills

- `cryptography-pki-fundamentals` - Certificate basics
- `cryptography-tls-configuration` - TLS setup
- `infrastructure-automation` - Deployment automation
- `observability-metrics-monitoring` - Monitoring setup

---

## Level 3: Resources

**Location**: `/Users/rand/src/cc-polymath/skills/cryptography/certificate-management/resources/`

This skill includes comprehensive Level 3 resources for production certificate management implementations:

### REFERENCE.md (~3,100 lines)

Comprehensive technical reference covering:
- **Fundamentals**: Digital certificates, X.509 standard, trust chains, PKI concepts
- **Certificate Components**: Subject, SANs, extensions, key usage, certificate formats (PEM, DER, PKCS#12)
- **Certificate Lifecycle**: Generation, CSR creation, issuance, deployment, monitoring, renewal, rotation, revocation
- **CA Hierarchies**: Root/intermediate CAs, public vs private CAs, trust models
- **ACME Protocol**: Challenge types (HTTP-01, DNS-01, TLS-ALPN-01), ACME flow, client implementations
- **Let's Encrypt**: Rate limits, staging environment, trust chain, wildcard certificates
- **Certificate Automation**: Certbot usage, acme.sh, renewal hooks, systemd timers
- **Kubernetes cert-manager**: Installation, issuers, certificate resources, ingress annotations
- **Mutual TLS (mTLS)**: Server/client configuration, service mesh integration, zero-trust patterns
- **Certificate Revocation**: CRL, OCSP, OCSP stapling, must-staple extension
- **Certificate Transparency**: CT logs, monitoring, unauthorized certificate detection
- **Certificate Pinning**: Public key pinning, HPKP (deprecated), mobile implementations
- **Monitoring**: Prometheus exporters, expiration tracking, alerting strategies
- **Best Practices**: Lifetime management, key protection, automation, testing, backup/recovery
- **Common Issues**: Troubleshooting expired certs, chain issues, key mismatches, SAN errors
- **Security**: Private key protection, validation requirements, weak cryptography avoidance
- **Compliance**: PCI-DSS, HIPAA, SOC2, GDPR certificate requirements
- **Tools**: OpenSSL, certbot, acme.sh, step CLI, cfssl, cert-manager, SSL Labs, testssl.sh

### Scripts (3 production-ready tools)

**validate_certificates.py** (580+ lines) - Comprehensive certificate validation
- Validates certificates from remote hosts or local files
- Checks expiration dates with configurable thresholds
- Detects weak algorithms (MD5, SHA-1, weak RSA keys)
- Validates certificate chains and hostname matching
- SAN validation including wildcard matching
- OCSP/CRL revocation checking support
- Compliance validation (PCI-DSS, HIPAA, SOC2)
- Batch validation from hosts file
- JSON output for CI/CD integration
- Detailed reporting with severity levels
- Usage: `./validate_certificates.py --host example.com --compliance PCI-DSS --json`

**renew_certificates.py** (450+ lines) - Automated ACME certificate renewal
- ACME protocol automation (Let's Encrypt, ZeroSSL)
- HTTP-01 and DNS-01 challenge support
- Automatic renewal based on expiration thresholds
- Pre/post/deploy hook support
- Automatic backup before renewal
- Rollback on renewal failure
- Batch renewal of all expiring certificates
- Dry-run mode for testing
- Staging environment support
- Custom ACME provider support
- DNS provider integration (Cloudflare, Route53, etc.)
- Usage: `./renew_certificates.py --domain example.com --dns-provider cloudflare --json`

**monitor_cert_expiry.sh** (550+ lines) - Certificate expiration monitoring
- Monitors certificates from remote hosts or local files
- Configurable warning/critical thresholds
- Multiple output formats (text, JSON, Prometheus, CSV)
- Batch monitoring from hosts file
- Directory scanning for certificate files
- Email/webhook/Slack alerting
- Certificate inventory export
- OCSP revocation status checking
- Prometheus metrics format for monitoring integration
- Color-coded terminal output
- Exit codes for CI/CD integration
- Usage: `./monitor_cert_expiry.sh --hosts-file hosts.txt --format prometheus --alert-email admin@example.com`

### Examples (6 production-ready implementations)

**python/acme_automation.py** - ACME protocol automation from scratch
- Account registration and key management
- Certificate ordering with ACME protocol
- HTTP-01 challenge implementation
- DNS-01 challenge for wildcard certificates
- CSR generation with multiple SANs
- Complete ACME workflow demonstration
- Staging environment support
- Production-ready patterns

**python/mtls_server_client.py** - Mutual TLS implementation
- mTLS server with client certificate verification
- mTLS client with certificate authentication
- Certificate generation helper
- TLS version and cipher suite configuration
- Client certificate extraction and validation
- Zero-trust authentication pattern
- Service-to-service authentication example

**python/prometheus_cert_exporter.py** - Prometheus metrics exporter
- Exports certificate expiration metrics
- Multi-host monitoring support
- Prometheus-compatible metrics format
- Certificate metadata collection
- Expiration time tracking
- Validity status monitoring
- Error counting and duration tracking
- Health check endpoint
- Production-ready monitoring integration

**kubernetes/cert-manager-setup.yaml** - Comprehensive cert-manager configuration
- ClusterIssuers for Let's Encrypt (production and staging)
- DNS-01 solvers (Cloudflare, Route53)
- Certificate resources with SANs
- Wildcard certificate examples
- Ingress annotation automation
- Namespace-scoped issuers
- Private CA issuer configuration
- mTLS client certificates
- Certificate lifecycle management
- Renewal configuration
- Troubleshooting helpers

**bash/certbot-automation.sh** - Complete certbot automation suite
- HTTP-01 webroot validation
- Nginx plugin integration
- Wildcard certificates (manual and automated DNS)
- DNS provider integration (Cloudflare, Route53)
- Systemd timer setup for auto-renewal
- Pre/post/deploy hooks
- Certificate revocation
- Force renewal
- Staging environment testing
- Custom CSR usage
- Certificate monitoring
- Nginx installation automation
- 18+ production examples

**config/nginx-ssl-best-practices.conf** - Production Nginx SSL configuration
- Modern TLS 1.2/1.3 configuration
- Strong cipher suite selection
- OCSP stapling setup
- HSTS and security headers
- Let's Encrypt integration
- HTTP to HTTPS redirect
- Wildcard certificate support
- mTLS configuration
- Multiple domain examples
- SSL Labs A+ rating configuration
- Certificate renewal integration
- PHP-FPM and reverse proxy examples

### Quick Start

```bash
# Validate remote certificate
cd /Users/rand/src/cc-polymath/skills/cryptography/certificate-management/resources/scripts
./validate_certificates.py --host example.com --check-revocation

# Renew certificate automatically
./renew_certificates.py --domain example.com --webroot /var/www/html --post-hook "systemctl reload nginx"

# Monitor certificate expiration
./monitor_cert_expiry.sh --hosts-file hosts.txt --threshold-warning 30 --json

# Export Prometheus metrics
./monitor_cert_expiry.sh --hosts-file hosts.txt --format prometheus > /var/lib/prometheus/cert_metrics.prom

# Run Python examples
cd ../examples/python
pip install cryptography acme josepy prometheus_client
python acme_automation.py http01
python mtls_server_client.py setup && python mtls_server_client.py server
python prometheus_cert_exporter.py --hosts example.com:443

# View comprehensive reference
cd ../
less REFERENCE.md
```

### Integration Notes

**CI/CD Integration**:
```yaml
# .github/workflows/certificate-check.yml
- name: Validate Certificates
  run: |
    ./scripts/validate_certificates.py \
      --batch-file production-hosts.txt \
      --compliance PCI-DSS \
      --json \
      --check-revocation
```

**Monitoring Setup**:
```yaml
# Prometheus scrape config
scrape_configs:
  - job_name: 'ssl-certificates'
    static_configs:
      - targets: ['localhost:9117']
    scrape_interval: 60s
```

**Alerting**:
```yaml
# Prometheus alert rules
- alert: CertificateExpiringSoon
  expr: ssl_certificate_expiry_seconds < 86400 * 30
  labels:
    severity: warning
  annotations:
    summary: "Certificate expiring in < 30 days"
```

**Kubernetes Deployment**:
```bash
# Install cert-manager
kubectl apply -f examples/kubernetes/cert-manager-setup.yaml

# Check certificate status
kubectl get certificates -A
kubectl describe certificate example-com-tls
```

---

**Last Updated**: 2025-10-27
