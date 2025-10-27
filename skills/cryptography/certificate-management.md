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
curl https://get.acme.sh | sh

# Issue certificate (HTTP validation)
acme.sh --issue -d example.com -w /var/www/html

# Issue wildcard (DNS validation with Cloudflare)
export CF_Token="your-cloudflare-api-token"
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

**Last Updated**: 2025-10-27
