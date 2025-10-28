# Emergency Secret Rotation Runbook

## Overview

**Purpose**: Emergency rotation procedure for compromised secrets
**SLA**: Complete rotation within 1 hour of detection
**Scope**: All production secrets (databases, API keys, certificates, tokens)

---

## Incident Detection

### Indicators of Compromise

- [ ] Secret found in public repository
- [ ] Unusual access patterns detected
- [ ] Security alert from monitoring system
- [ ] Third-party breach notification
- [ ] Insider threat suspicion
- [ ] Failed authentication spike
- [ ] Unexpected data access

### Initial Assessment (5 minutes)

1. **Identify compromised secret(s)**
   ```bash
   # List all secrets in system
   ./scripts/list-secrets.sh

   # Check secret usage logs
   ./scripts/check-secret-usage.sh <secret-name> --last-24h
   ```

2. **Determine blast radius**
   - What systems use this secret?
   - What data is accessible?
   - How many users/services affected?

3. **Classify severity**
   - **P0 Critical**: Production database, root credentials
   - **P1 High**: API keys, service accounts
   - **P2 Medium**: Read-only credentials, non-production
   - **P3 Low**: Development, test environments

---

## Emergency Response Team

### Roles and Responsibilities

| Role | Responsibilities | Contact |
|------|------------------|---------|
| **Incident Commander** | Coordinate response, make decisions | On-call manager |
| **Security Lead** | Assess impact, containment | Security team |
| **Operations Lead** | Execute rotation, verify systems | DevOps team |
| **Communications Lead** | Notify stakeholders, documentation | Product/Support |

### Communication Channels

```bash
# Create incident war room
slack --channel=#incident-$(date +%Y%m%d-%H%M) --topic="Secret Rotation: <secret-name>"

# Start incident bridge
zoom --meeting-id=emergency-rotation

# Page on-call
pagerduty trigger --service=security --severity=critical --summary="Secret compromised: <secret-name>"
```

---

## Rotation Procedures

### 1. Database Credentials (P0 - 30 minutes)

**PostgreSQL/MySQL**

```bash
# Step 1: Create new credentials
NEW_PASSWORD=$(openssl rand -base64 32)
echo "New password generated: ${NEW_PASSWORD:0:8}..."

# Step 2: Create temporary user (zero-downtime)
psql -h $DB_HOST -U postgres <<EOF
CREATE USER app_user_temp WITH PASSWORD '$NEW_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE myapp TO app_user_temp;
GRANT ALL ON ALL TABLES IN SCHEMA public TO app_user_temp;
EOF

# Step 3: Update application config (rolling restart)
kubectl set env deployment/app \
  DB_USER=app_user_temp \
  DB_PASSWORD=$NEW_PASSWORD

# Wait for rollout
kubectl rollout status deployment/app --timeout=5m

# Step 4: Verify application health
kubectl exec deployment/app -- curl -f http://localhost:8080/health

# Step 5: Rotate original user
psql -h $DB_HOST -U postgres <<EOF
ALTER USER app_user WITH PASSWORD '$NEW_PASSWORD';
EOF

# Step 6: Switch back to original user
kubectl set env deployment/app \
  DB_USER=app_user \
  DB_PASSWORD=$NEW_PASSWORD

kubectl rollout status deployment/app --timeout=5m

# Step 7: Clean up temporary user
psql -h $DB_HOST -U postgres -c "DROP USER app_user_temp;"

# Step 8: Update secret manager
aws secretsmanager update-secret \
  --secret-id prod/db/credentials \
  --secret-string "{\"username\":\"app_user\",\"password\":\"$NEW_PASSWORD\"}"

echo "✓ Database credentials rotated successfully"
```

**Verification Checklist**
- [ ] Application health checks passing
- [ ] Database connections stable
- [ ] No authentication errors in logs
- [ ] Old credentials invalidated
- [ ] Secret manager updated

---

### 2. API Keys (P1 - 15 minutes)

**Third-party API Keys (Stripe, Twilio, etc.)**

```bash
# Step 1: Generate new API key
# Via provider console or API
NEW_API_KEY=$(curl -X POST https://api.provider.com/v1/keys \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  | jq -r '.key')

echo "New API key: ${NEW_API_KEY:0:10}..."

# Step 2: Update application (immediate)
kubectl create secret generic api-keys \
  --from-literal=PROVIDER_API_KEY=$NEW_API_KEY \
  --dry-run=client -o yaml | kubectl apply -f -

# Step 3: Rolling restart
kubectl rollout restart deployment/app
kubectl rollout status deployment/app --timeout=5m

# Step 4: Verify integration
kubectl exec deployment/app -- \
  curl -f https://api.provider.com/v1/test \
  -H "Authorization: Bearer $NEW_API_KEY"

# Step 5: Revoke old key
curl -X DELETE https://api.provider.com/v1/keys/$OLD_KEY_ID \
  -H "Authorization: Bearer $ADMIN_TOKEN"

echo "✓ API key rotated successfully"
```

**Verification Checklist**
- [ ] New key working in production
- [ ] All service instances updated
- [ ] Old key revoked
- [ ] No API errors in logs
- [ ] Rate limits not exceeded

---

### 3. TLS Certificates (P0 - 20 minutes)

**Let's Encrypt / ACME**

```bash
# Step 1: Obtain new certificate
certbot certonly \
  --webroot -w /var/www/html \
  -d example.com -d www.example.com \
  --email security@example.com \
  --agree-tos \
  --non-interactive

# Step 2: Upload to load balancer
NEW_CERT_ARN=$(aws acm import-certificate \
  --certificate fileb:///etc/letsencrypt/live/example.com/fullchain.pem \
  --private-key fileb:///etc/letsencrypt/live/example.com/privkey.pem \
  --query 'CertificateArn' --output text)

echo "New certificate ARN: $NEW_CERT_ARN"

# Step 3: Update load balancer listener (zero-downtime)
aws elbv2 modify-listener \
  --listener-arn $LISTENER_ARN \
  --certificates CertificateArn=$NEW_CERT_ARN

# Step 4: Verify TLS
echo | openssl s_client -connect example.com:443 -servername example.com 2>/dev/null \
  | openssl x509 -noout -dates

# Step 5: Delete old certificate (after 5 min grace period)
sleep 300
aws acm delete-certificate --certificate-arn $OLD_CERT_ARN

echo "✓ Certificate rotated successfully"
```

**Verification Checklist**
- [ ] New certificate valid
- [ ] HTTPS traffic flowing
- [ ] No SSL errors
- [ ] Browser trust indicators present
- [ ] Old certificate removed

---

### 4. SSH Keys (P1 - 10 minutes)

**Server Access Keys**

```bash
# Step 1: Generate new keypair
ssh-keygen -t ed25519 -f /tmp/emergency_key -N "" -C "emergency-rotation-$(date +%Y%m%d)"

# Step 2: Deploy public key to all servers
ansible all -m authorized_key \
  -a "user=deploy key='{{ lookup('file', '/tmp/emergency_key.pub') }}' state=present"

# Step 3: Verify access with new key
ssh -i /tmp/emergency_key deploy@server1.example.com "echo 'Connection successful'"

# Step 4: Remove old key
OLD_KEY_FINGERPRINT="SHA256:abc123..."
ansible all -m authorized_key \
  -a "user=deploy key='{{ OLD_KEY_FINGERPRINT }}' state=absent"

# Step 5: Update key management system
vault kv put secret/ssh/deploy-key \
  private_key=@/tmp/emergency_key \
  public_key=@/tmp/emergency_key.pub

# Step 6: Secure cleanup
shred -vfz /tmp/emergency_key /tmp/emergency_key.pub

echo "✓ SSH keys rotated successfully"
```

**Verification Checklist**
- [ ] New key works on all servers
- [ ] Old key no longer works
- [ ] CI/CD pipelines updated
- [ ] Team members notified
- [ ] Key backup secured

---

## Automation Scripts

### Full Emergency Rotation Script

```bash
#!/bin/bash
# emergency-rotate.sh - Automated emergency rotation

set -euo pipefail

SECRET_TYPE=$1  # database|api-key|certificate|ssh-key
SECRET_NAME=$2

log() {
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" | tee -a /var/log/rotation.log
}

rotate_database() {
    log "Starting database rotation: $SECRET_NAME"

    # Generate new password
    NEW_PASS=$(openssl rand -base64 32)

    # Execute rotation
    python3 /opt/rotation/rotate_db.py \
        --secret-name "$SECRET_NAME" \
        --new-password "$NEW_PASS" \
        --zero-downtime

    log "Database rotation complete"
}

rotate_api_key() {
    log "Starting API key rotation: $SECRET_NAME"

    python3 /opt/rotation/rotate_api_key.py \
        --secret-name "$SECRET_NAME" \
        --provider auto-detect \
        --immediate

    log "API key rotation complete"
}

rotate_certificate() {
    log "Starting certificate rotation: $SECRET_NAME"

    python3 /opt/rotation/rotate_certificate.py \
        --domains "$SECRET_NAME" \
        --acme-provider letsencrypt \
        --upload-to-lb

    log "Certificate rotation complete"
}

rotate_ssh_key() {
    log "Starting SSH key rotation: $SECRET_NAME"

    python3 /opt/rotation/rotate_ssh_key.py \
        --key-name "$SECRET_NAME" \
        --deploy-all-servers \
        --remove-old

    log "SSH key rotation complete"
}

# Execute rotation based on type
case $SECRET_TYPE in
    database)
        rotate_database
        ;;
    api-key)
        rotate_api_key
        ;;
    certificate)
        rotate_certificate
        ;;
    ssh-key)
        rotate_ssh_key
        ;;
    *)
        log "ERROR: Unknown secret type: $SECRET_TYPE"
        exit 1
        ;;
esac

log "Emergency rotation complete: $SECRET_TYPE/$SECRET_NAME"
```

### Usage

```bash
# Rotate database credentials
./emergency-rotate.sh database prod-db-credentials

# Rotate API key
./emergency-rotate.sh api-key stripe-production

# Rotate certificate
./emergency-rotate.sh certificate example.com

# Rotate SSH key
./emergency-rotate.sh ssh-key deploy-key
```

---

## Post-Rotation

### Verification (15 minutes)

```bash
# Run comprehensive tests
./scripts/verify-rotation.sh --secret=$SECRET_NAME

# Check application health
kubectl get pods --all-namespaces
kubectl top nodes
kubectl logs -l app=myapp --tail=100 | grep -i error

# Verify metrics
curl -s http://prometheus:9090/api/v1/query?query='up{job="myapp"}' | jq '.data.result[].value[1]'

# Test critical user journeys
./scripts/e2e-tests.sh --env=production --critical-path-only
```

### Documentation

```markdown
## Incident Report: Secret Rotation

**Incident ID**: INC-2024-XXXX
**Date**: 2024-XX-XX
**Duration**: X hours
**Severity**: PX

### Summary
Brief description of what happened.

### Timeline
- 14:00 UTC - Compromise detected
- 14:05 UTC - Incident declared
- 14:10 UTC - Rotation started
- 14:45 UTC - Rotation complete
- 15:00 UTC - Verification complete

### Impact
- Services affected: X
- Users impacted: X
- Downtime: 0 minutes (zero-downtime rotation)

### Root Cause
What led to the compromise.

### Remediation
What was done to fix it.

### Follow-up Actions
- [ ] Review access logs
- [ ] Update rotation automation
- [ ] Team training on new procedures
- [ ] Implement additional monitoring
```

---

## Contact Information

### Emergency Contacts

- **Security Team**: security@example.com, Slack: #security
- **On-call Engineer**: PagerDuty escalation policy
- **DevOps Lead**: devops-lead@example.com
- **CTO**: cto@example.com (for P0 incidents)

### Escalation Path

1. **0-15 min**: On-call engineer + Security team
2. **15-30 min**: Add DevOps lead
3. **30-60 min**: Add CTO (P0 only)
4. **60+ min**: Executive notification

---

## Appendix

### Pre-rotation Checklist

- [ ] Incident declared and logged
- [ ] War room established
- [ ] Stakeholders notified
- [ ] Blast radius assessed
- [ ] Backup created
- [ ] Rollback plan ready

### Post-rotation Checklist

- [ ] All systems verified healthy
- [ ] Old credentials invalidated
- [ ] Secret manager updated
- [ ] Monitoring shows normal behavior
- [ ] Incident documentation complete
- [ ] Team debriefing scheduled
- [ ] Follow-up actions assigned

### Common Pitfalls

1. **Rotating too quickly without testing** - Always verify new credentials work before invalidating old ones
2. **Not updating all locations** - Check CI/CD, local dev, documentation
3. **Forgetting grace period** - Allow overlap for in-flight requests
4. **No verification** - Always test after rotation
5. **Poor communication** - Keep stakeholders informed

### Tools and Resources

- [Secret rotation scripts](https://github.com/example/rotation-scripts)
- [Monitoring dashboard](https://grafana.example.com/rotation)
- [Incident management](https://pagerduty.com/incidents)
- [Documentation](https://wiki.example.com/security/rotation)
